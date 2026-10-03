"""SLICE-0079 operator alert-webhook delivery unit tests."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from hullq.observability.alerting import (
    HULLQ_ALERT_WEBHOOK_URL_ENV,
    AlertDeliveryError,
    AlertEvent,
    get_alert_webhook_url,
    send_alert,
)

_EVENT = AlertEvent(
    severity="CRITICAL",
    source="readiness-monitor",
    message="database unreachable",
    occurred_at=datetime(2026, 10, 3, 12, 0, 0, tzinfo=UTC),
)


class _FakeResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code


def test_get_alert_webhook_url_returns_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HULLQ_ALERT_WEBHOOK_URL_ENV, raising=False)
    assert get_alert_webhook_url() is None


def test_get_alert_webhook_url_returns_none_when_blank(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HULLQ_ALERT_WEBHOOK_URL_ENV, "   ")
    assert get_alert_webhook_url() is None


def test_get_alert_webhook_url_returns_configured_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(HULLQ_ALERT_WEBHOOK_URL_ENV, "https://hooks.example/alert")
    assert get_alert_webhook_url() == "https://hooks.example/alert"


def test_alert_event_payload_is_slack_and_discord_compatible() -> None:
    payload = _EVENT.to_webhook_payload()
    assert payload["text"] == payload["content"]
    assert "CRITICAL" in payload["text"]
    assert "readiness-monitor" in payload["text"]
    assert "database unreachable" in payload["text"]
    assert payload["severity"] == "CRITICAL"
    assert payload["occurred_at"] == "2026-10-03T12:00:00+00:00"


def test_send_alert_returns_false_when_unconfigured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(HULLQ_ALERT_WEBHOOK_URL_ENV, raising=False)
    assert send_alert(_EVENT) is False


def test_send_alert_posts_to_configured_webhook_and_returns_true() -> None:
    calls: list[dict[str, Any]] = []

    def _fake_post(url: str, *, json: dict[str, Any], timeout: float) -> _FakeResponse:
        calls.append({"url": url, "json": json, "timeout": timeout})
        return _FakeResponse(200)

    result = send_alert(_EVENT, webhook_url="https://hooks.example/alert", http_post=_fake_post)
    assert result is True
    assert len(calls) == 1
    assert calls[0]["url"] == "https://hooks.example/alert"
    assert calls[0]["json"]["message"] == "database unreachable"


def test_send_alert_raises_on_non_2xx_response() -> None:
    def _fake_post(url: str, *, json: dict[str, Any], timeout: float) -> _FakeResponse:
        return _FakeResponse(500)

    with pytest.raises(AlertDeliveryError):
        send_alert(_EVENT, webhook_url="https://hooks.example/alert", http_post=_fake_post)


def test_send_alert_raises_on_transport_failure() -> None:
    def _fake_post(url: str, *, json: dict[str, Any], timeout: float) -> _FakeResponse:
        raise ConnectionError("network unreachable")

    with pytest.raises(AlertDeliveryError):
        send_alert(_EVENT, webhook_url="https://hooks.example/alert", http_post=_fake_post)
