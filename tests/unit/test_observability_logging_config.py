"""SLICE-0079 structured JSON logging unit tests."""

from __future__ import annotations

import json
import logging

import pytest

from hullq.observability.logging_config import JsonLogFormatter, configure_logging, get_logger


def _make_record(
    *, level: int = logging.INFO, message: str = "hello", extra: dict[str, object] | None = None
) -> logging.LogRecord:
    record = logging.LogRecord(
        name="hullq.test",
        level=level,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )
    for key, value in (extra or {}).items():
        setattr(record, key, value)
    return record


def test_json_log_formatter_emits_valid_json_with_required_fields() -> None:
    record = _make_record(message="something happened")
    line = JsonLogFormatter().format(record)
    payload = json.loads(line)
    assert payload["level"] == "INFO"
    assert payload["logger"] == "hullq.test"
    assert payload["message"] == "something happened"
    assert "timestamp" in payload


def test_json_log_formatter_promotes_known_extra_fields() -> None:
    record = _make_record(
        extra={
            "request_id": "abc-123",
            "method": "GET",
            "path": "/healthz",
            "status_code": 200,
            "duration_ms": 1.5,
        }
    )
    payload = json.loads(JsonLogFormatter().format(record))
    assert payload["request_id"] == "abc-123"
    assert payload["method"] == "GET"
    assert payload["path"] == "/healthz"
    assert payload["status_code"] == 200
    assert payload["duration_ms"] == 1.5


def test_json_log_formatter_omits_absent_extra_fields() -> None:
    record = _make_record()
    payload = json.loads(JsonLogFormatter().format(record))
    assert "request_id" not in payload
    assert "status_code" not in payload


def test_json_log_formatter_includes_exception_traceback() -> None:
    try:
        raise ValueError("boom")
    except ValueError:
        import sys

        exc_info = sys.exc_info()
    record = _make_record(level=logging.ERROR, message="unhandled_exception")
    record.exc_info = exc_info
    payload = json.loads(JsonLogFormatter().format(record))
    assert "ValueError: boom" in payload["exception"]


def test_configure_logging_is_idempotent() -> None:
    logger_name = "hullq.test_idempotent"
    logger = configure_logging(logger_name=logger_name)
    handler_count_after_first_call = len(logger.handlers)
    configure_logging(logger_name=logger_name)
    assert len(logger.handlers) == handler_count_after_first_call
    assert handler_count_after_first_call == 1
    assert logger.propagate is False


def test_get_logger_returns_named_logger_without_forcing_configuration() -> None:
    logger = get_logger("hullq.test_unconfigured_name")
    assert logger.name == "hullq.test_unconfigured_name"


@pytest.mark.parametrize("level", [logging.DEBUG, logging.WARNING])
def test_configure_logging_applies_requested_level(level: int) -> None:
    logger = configure_logging(logger_name="hullq.test_level", level=level)
    assert logger.level == level
