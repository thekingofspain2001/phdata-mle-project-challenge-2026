"""FastAPI application serving home price predictions."""

import time
from typing import TYPE_CHECKING
from uuid import uuid4

import structlog
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.endpoints import router as api_router
from api.endpoints_v2 import router_v2 as api_router_v2
from api.lifespan import lifespan
from logger_config import setup_logging

setup_logging()  # uvicorn logs "Started server process" before lifespan runs

if TYPE_CHECKING:
    from starlette.middleware.base import RequestResponseEndpoint

app = FastAPI(lifespan=lifespan)

log = structlog.get_logger("api")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID"],  # browser JS must be allowed to read the ID
)

app.include_router(api_router)
app.include_router(api_router_v2)


def log_request_end(request: Request, status_code: int, started: float) -> None:
    """Emit the end-of-transaction entry, tagged with the correlation ID."""
    log.info(
        "request",
        method=request.method,
        path=request.url.path,
        status_code=status_code,
        duration_ms=round((time.perf_counter() - started) * 1000, 2),
    )


@app.middleware("http")
async def log_request(request: Request, call_next: RequestResponseEndpoint) -> Response:
    """Time the request; an unhandled exception escapes as a 500 and is logged as one."""
    started = time.perf_counter()
    try:
        response = await call_next(request)
    except Exception:
        log_request_end(request, 500, started)
        raise
    log_request_end(request, response.status_code, started)
    return response


def audit_item(item_id: int) -> None:
    """Nested helper: the correlation ID reaches it from context, no plumbing."""
    log.info("item_audit", item_id=item_id)


@app.get("/items/{item_id}")
async def read_item(item_id: int) -> dict[str, int]:
    """Sample route proving the request ID propagates into nested calls."""
    audit_item(item_id)
    return {"item_id": item_id}


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception) -> JSONResponse:
    """Log the captured exception with its traceback, then answer 500."""
    log.error("unhandled_exception", method=request.method, path=request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
        headers={"X-Request-ID": correlation_id.get() or ""},
    )


# Added last so it wraps everything: the ID is bound before any log runs.
app.add_middleware(CorrelationIdMiddleware, header_name="X-Request-ID", generator=lambda: str(uuid4()))

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000)
