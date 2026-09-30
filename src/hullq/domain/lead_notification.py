"""Broker Lead notification recipient/outbox vocabulary — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§9/§10/§12/§12A: the bounded notification-recipient email vocabulary and the
durable outbox delivery-state vocabulary. Notification transport/engagement
is transport/workflow metadata only -- it never redefines Lead identity,
buyer intent, Lead quality or Search/listing truth (contract §12A).

Pure value objects/normalizers only -- no persistence/network access.
"""

from __future__ import annotations

import re
import unicodedata
from enum import StrEnum

__all__ = [
    "MAX_NOTIFICATION_EMAIL_LENGTH",
    "NotificationDeliveryStatus",
    "normalize_notification_recipient_email",
]


class NotificationDeliveryStatus(StrEnum):
    """Bounded outbox delivery-state vocabulary (contract §10).

    `DELIVERED` is terminal/idempotent; `FAILED_RETRYABLE` may return to
    `PENDING` under bounded retry policy; `FAILED_TERMINAL` is never
    auto-retried; `NO_RECIPIENT_CONFIGURED` never rolls back the Lead
    (contract §10: "No-recipient Lead creation still succeeds").
    """

    PENDING = "PENDING"
    DELIVERED = "DELIVERED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_TERMINAL = "FAILED_TERMINAL"
    NO_RECIPIENT_CONFIGURED = "NO_RECIPIENT_CONFIGURED"


#: RFC 5321 §4.5.3.1.3's overall maximum mailbox length -- mirrors
#: `hullq.domain.buyer_lead.MAX_BUYER_EMAIL_LENGTH`.
MAX_NOTIFICATION_EMAIL_LENGTH = 320

#: Bounded syntactic check identical in spirit to
#: `hullq.domain.buyer_lead._EMAIL_RE` -- "valid enough for contact
#: routing", not full RFC 5322 grammar.
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def normalize_notification_recipient_email(raw: object) -> str:
    """Trim and validate a bounded, syntactically-valid-enough Organization
    Lead-notification recipient email (contract §9).

    Raises `TypeError`/`ValueError` for non-`str` input, empty/whitespace-
    only text, control characters, text exceeding
    `MAX_NOTIFICATION_EMAIL_LENGTH`, or a value that does not match the
    bounded contact-routing shape. Clearing the address entirely is a
    separate explicit caller decision (passing `None` through the
    persistence layer), not expressed by this normalizer.
    """
    if not isinstance(raw, str):
        raise TypeError(f"notification email must be a str, got {type(raw).__name__}")
    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("notification email must not be empty or whitespace-only")
    if len(trimmed) > MAX_NOTIFICATION_EMAIL_LENGTH:
        raise ValueError(
            "notification email must be at most "
            f"{MAX_NOTIFICATION_EMAIL_LENGTH} characters, got {len(trimmed)}"
        )
    for char in trimmed:
        if unicodedata.category(char) == "Cc":
            raise ValueError("notification email must not contain control characters")
    if not _EMAIL_RE.fullmatch(trimmed):
        raise ValueError("notification email is not syntactically valid")
    return trimmed
