"""Structured JSON logging for the app and Uvicorn, emitted on stdout.

One `ProcessorFormatter` renders both worlds: structlog events and stdlib
records (uvicorn, uvicorn.error, uvicorn.access) end up on stdout as the same
single-line JSON, sharing the request's ``correlation_id``.
"""

from __future__ import annotations

import logging
import sys
from typing import TYPE_CHECKING, Any, cast

import structlog
from asgi_correlation_id import correlation_id
from structlog.contextvars import merge_contextvars
from structlog.processors import JSONRenderer, TimeStamper
from structlog.stdlib import PositionalArgumentsFormatter, ProcessorFormatter, add_log_level, add_logger_name

if TYPE_CHECKING:
    from structlog.types import EventDict, Processor, WrappedLogger

LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access")
ACCESS_LOGGER = "uvicorn.access"
# Uvicorn logs access as '%s - "%s %s HTTP/%s" %d' (client, method, path, version, status).
ACCESS_ARG_COUNT = 5


def add_correlation_id(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Bind the current request's correlation ID; null outside a request."""
    _ = logger, method_name
    event_dict["correlation_id"] = correlation_id.get()
    return event_dict


def uvicorn_access_fields(logger: WrappedLogger, method_name: str, event_dict: EventDict) -> EventDict:
    """Explode Uvicorn's positional access-log args into named fields."""
    _ = logger, method_name
    record = event_dict.get("_record")
    raw_args = cast("tuple[Any, ...] | None", event_dict.get("positional_args"))
    if isinstance(record, logging.LogRecord) and record.name == ACCESS_LOGGER and raw_args is not None and len(raw_args) == ACCESS_ARG_COUNT:
        client_ip, method, path, _http_version, status_code = raw_args
        event_dict.update(
            client_ip=client_ip,
            method=method,
            path=path,
            status_code=status_code,
        )
    return event_dict


SHARED_PROCESSORS: list[Processor] = [
    merge_contextvars,
    add_correlation_id,
    add_logger_name,
    add_log_level,
    TimeStamper(fmt="iso"),
    structlog.processors.format_exc_info,
    uvicorn_access_fields,
]


def setup_logging(level: int = logging.INFO) -> None:
    """Route every logger to one JSON stdout handler; call on app startup."""
    # pass_foreign_args + use_get_message=False hands us the raw args tuple
    # before the formatter clears record.args; PositionalArgumentsFormatter
    # then renders the message and drops the key.
    formatter = ProcessorFormatter(
        foreign_pre_chain=SHARED_PROCESSORS,
        processors=[
            *SHARED_PROCESSORS,
            PositionalArgumentsFormatter(),
            ProcessorFormatter.remove_processors_meta,
            JSONRenderer(),
        ],
        pass_foreign_args=True,
        use_get_message=False,
    )
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers = [handler]
    root.setLevel(level)
    for name in LOGGERS:
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers = [handler]
        uvicorn_logger.setLevel(level)
        uvicorn_logger.propagate = False

    structlog.configure(
        processors=[*SHARED_PROCESSORS, ProcessorFormatter.wrap_for_formatter],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
