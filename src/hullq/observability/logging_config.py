"""Structured JSON application logging — SLICE-0079.

Implements `docs/governance/PRODUCTION_READINESS_GATE.md` §3's "structured
application logs sufficient to correlate failures across public web/API/
background work" requirement with one dependency-free JSON-lines stdout
formatter, deliberately not a third-party APM SDK the gate does not mandate
("exact provider/tooling is not predetermined by this gate"). A production
host's container runtime/log collector reads these JSON lines from stdout;
no file-based log state is written, preserving the accepted stateless/
replaceable application-host assumption
(`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §23).

Every record carries a UTC timestamp, level, logger name and message, plus
whichever of `request_id`/`method`/`path`/`status_code`/`duration_ms` the
caller attached via `extra=...` -- never none of them silently dropped, and
never raising merely because a particular record omits one.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

__all__ = ["HULLQ_LOGGER_NAME", "JsonLogFormatter", "configure_logging", "get_logger"]

HULLQ_LOGGER_NAME = "hullq"

#: Extra `LogRecord` attributes this formatter promotes to top-level JSON
#: keys when present (contract: correlate one request/background operation
#: across multiple log lines). Never required -- a record missing all of
#: them still formats correctly as a plain structured log line.
_PROMOTED_EXTRA_FIELDS = ("request_id", "method", "path", "status_code", "duration_ms")

_configured_loggers: set[str] = set()


class JsonLogFormatter(logging.Formatter):
    """Renders one `LogRecord` as a single-line JSON object."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        for field in _PROMOTED_EXTRA_FIELDS:
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        if record.exc_info is not None:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, default=str)


def configure_logging(
    *, logger_name: str = HULLQ_LOGGER_NAME, level: int = logging.INFO
) -> logging.Logger:
    """Idempotently attach one stdout JSON handler to *logger_name*.

    Safe to call repeatedly (the FastAPI app factory, CLI ops scripts and
    the worker entry point may each call this independently): only the
    first call for a given *logger_name* attaches a handler, so output is
    never duplicated. `propagate` is disabled so this logger's records are
    never also emitted by a parent/root handler the deployment environment
    might separately configure.
    """
    logger = logging.getLogger(logger_name)
    if logger_name not in _configured_loggers:
        handler = logging.StreamHandler(stream=sys.stdout)
        handler.setFormatter(JsonLogFormatter())
        logger.addHandler(handler)
        logger.propagate = False
        _configured_loggers.add(logger_name)
    logger.setLevel(level)
    return logger


def get_logger(name: str = HULLQ_LOGGER_NAME) -> logging.Logger:
    """Return the named logger, without implicitly configuring handlers.

    Callers that need output should call `configure_logging()` once at
    process startup (the FastAPI app factory and ops CLI entry points do
    this); library/application code should just call `get_logger(__name__)`
    and log.
    """
    return logging.getLogger(name)
