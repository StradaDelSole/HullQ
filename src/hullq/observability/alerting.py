"""Actionable operator alert delivery — SLICE-0079.

Implements `docs/governance/PRODUCTION_READINESS_GATE.md` §3's "actionable
alert delivery for failures that require operator intervention" using one
generic outbound webhook POST rather than a dedicated paging SaaS the
near-zero-budget architecture (`docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
§23) does not justify yet. The payload is deliberately compatible with both
a Slack incoming webhook (`text`) and a Discord webhook (`content`) so the
solo operator can point `HULLQ_ALERT_WEBHOOK_URL` at either free destination
without any HullQ code change.

An unconfigured webhook is a deployment-time operational gap, not a reason
for a caller to crash: `send_alert` returns `False` rather than raising when
no URL is configured. A *configured* webhook that actually fails to accept
delivery raises `AlertDeliveryError` so a caller (the health-monitor script,
the exception handler) can decide to also log loudly rather than the
failure being silent -- the gate's "no silent critical failure mode" rule.
"""

from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from typing import Any

__all__ = [
    "HULLQ_ALERT_WEBHOOK_URL_ENV",
    "AlertDeliveryError",
    "AlertEvent",
    "get_alert_webhook_url",
    "send_alert",
]

HULLQ_ALERT_WEBHOOK_URL_ENV = "HULLQ_ALERT_WEBHOOK_URL"


class AlertDeliveryError(RuntimeError):
    """The configured alert webhook could not be reached or rejected delivery."""


@dataclass(frozen=True, slots=True)
class AlertEvent:
    """One actionable operator alert.

    *severity* is a free-form short label (`"CRITICAL"`, `"WARNING"`) --
    this module does not prescribe a fixed taxonomy; callers (the
    health-monitor script, the exception handler) choose it.
    """

    severity: str
    source: str
    message: str
    occurred_at: datetime

    def to_webhook_payload(self) -> dict[str, Any]:
        text = f"[{self.severity}] {self.source}: {self.message} ({self.occurred_at.isoformat()})"
        return {
            # Slack incoming-webhook shape.
            "text": text,
            # Discord webhook shape. Both keys are always present; each
            # provider's webhook endpoint reads only the key it understands
            # and ignores the other.
            "content": text,
            "severity": self.severity,
            "source": self.source,
            "message": self.message,
            "occurred_at": self.occurred_at.isoformat(),
        }


def get_alert_webhook_url() -> str | None:
    """Return `HULLQ_ALERT_WEBHOOK_URL`, or `None` when unset/empty.

    Never raises: an unconfigured alert destination is valid during local
    development and during a strictly internal production-data phase with
    no externally-relied-upon alerting yet.
    """
    raw = os.environ.get(HULLQ_ALERT_WEBHOOK_URL_ENV, "").strip()
    return raw or None


def send_alert(
    event: AlertEvent,
    *,
    webhook_url: str | None = None,
    http_post: Callable[..., Any] | None = None,
) -> bool:
    """POST *event* to the configured operator alert webhook.

    *webhook_url* overrides the environment (used by tests/the retained
    proof). *http_post* overrides the real outbound HTTP call (used by
    tests to avoid real network I/O); defaults to `httpx.post`.

    Returns `False` when no webhook is configured. Returns `True` on an
    HTTP 2xx response. Raises `AlertDeliveryError` on a non-2xx response or
    a transport failure.
    """
    resolved_url = webhook_url if webhook_url is not None else get_alert_webhook_url()
    if resolved_url is None:
        return False

    if http_post is None:
        import httpx

        http_post = httpx.post

    try:
        response = http_post(resolved_url, json=event.to_webhook_payload(), timeout=10.0)
    except Exception as exc:
        raise AlertDeliveryError(
            f"alert webhook POST to configured destination failed: {type(exc).__name__}"
        ) from exc

    status_code = getattr(response, "status_code", None)
    if status_code is None or not (200 <= status_code < 300):
        raise AlertDeliveryError(f"alert webhook returned unexpected status {status_code!r}")
    return True
