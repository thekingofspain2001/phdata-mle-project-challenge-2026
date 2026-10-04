"""FastAPI application serving home price predictions."""

import math
import os
import time
from collections.abc import Mapping, Sequence
from typing import TYPE_CHECKING, cast
from uuid import uuid4

import structlog
from asgi_correlation_id import CorrelationIdMiddleware, correlation_id
from fastapi import FastAPI, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
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


@app.exception_handler(RequestValidationError)
async def validation_exception(_request: Request, exc: RequestValidationError) -> JSONResponse:
    """Answer 422 without crashing on a non-finite input.

    FastAPI echoes the offending value into detail[].input, and Starlette's
    JSONResponse renders with allow_nan=False - so rejecting Infinity or NaN
    turns the 422 itself into a 500. Replace non-finite floats with null so
    the error survives serialization.
    """

    def scrub(value: object) -> object:
        if isinstance(value, float) and not math.isfinite(value):
            return None
        if isinstance(value, Mapping):
            mapping = cast("Mapping[object, object]", value)
            return {str(k): scrub(v) for k, v in mapping.items()}
        if isinstance(value, Sequence) and not isinstance(value, str | bytes):
            items = cast("Sequence[object]", value)
            return [scrub(v) for v in items]
        return value

    errors = exc.errors()
    # A 422 is the one v2 outcome with no domain event: without this, a
    # rejected payload logs only the middleware's status_code and gives no
    # field name or reason to grep on.
    log.warning(
        "validation_failed",
        fields=[f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in errors],
    )
    return JSONResponse(
        status_code=422,
        content={"detail": jsonable_encoder(scrub(errors))},
        headers={"X-Request-ID": correlation_id.get() or ""},
    )


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
    # Import string, not the app object: workers>1 requires it (uvicorn docs).
    # Starting here also means this process runs setup_logging(), so the
    # supervisor's own startup/shutdown lines are JSON like the workers'.
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, workers=int(os.getenv("WEB_CONCURRENCY", os.cpu_count() or 1)))  # noqa: S104 - container entrypoint must bind all interfaces
