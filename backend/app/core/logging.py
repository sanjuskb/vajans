"""
VAJANS — Structured Logging
Uses structlog for JSON-formatted, correlation-id-aware logging.
"""

import logging
import sys
from typing import Any

import structlog
from app.core.settings import settings


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.LOG_FORMAT == "json":
        shared_processors.append(structlog.processors.JSONRenderer())
    else:
        shared_processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=shared_processors,
        wrapper_class=structlog.make_filtering_bound_logger(log_level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Also configure stdlib logging for third-party libraries
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=log_level,
    )


def get_logger(name: str = "vajans") -> structlog.BoundLogger:
    return structlog.get_logger(name)
