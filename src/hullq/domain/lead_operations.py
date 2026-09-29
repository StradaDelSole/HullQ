"""Broker Lead operational workflow vocabulary — SLICE-0071.

Implements `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§5/§7/§8/§8A: the bounded operational-status/assignment/note/follow-up/
contact-attempt/close-reason vocabulary layered on top of the SLICE-0070
immutable Lead envelope (`hullq.domain.buyer_lead`). This module never
redefines Lead identity, buyer intent or listing/Search truth (contract §5:
"Status never changes listing lifecycle, CurrentPublicEligibility, Search
truth or buyer email verification state") -- it is broker-workflow metadata
only.

Pure value objects/normalizers and bounded vocabularies only -- no
persistence/network access.
"""

from __future__ import annotations

import unicodedata
from enum import StrEnum

__all__ = [
    "MAX_LEAD_NOTE_LENGTH",
    "LeadCloseReason",
    "LeadContactAttemptChannel",
    "LeadOperationalStatus",
    "LeadTimelineEventType",
    "normalize_lead_note_text",
]


class LeadOperationalStatus(StrEnum):
    """Bounded broker-operational status (contract §5 v0.1 values).

    Distinct from listing lifecycle and notification delivery state. Creation
    always starts at `NEW` (contract §5).
    """

    NEW = "NEW"
    IN_PROGRESS = "IN_PROGRESS"
    WAITING_FOR_BUYER = "WAITING_FOR_BUYER"
    CLOSED = "CLOSED"


class LeadCloseReason(StrEnum):
    """Bounded close-reason vocabulary (contract §8A).

    Required exactly when transitioning to `LeadOperationalStatus.CLOSED`.
    Workflow metadata only -- never SaleOutcome/sold-status evidence.
    """

    NOT_INTERESTED = "NOT_INTERESTED"
    UNREACHABLE = "UNREACHABLE"
    BOAT_UNAVAILABLE = "BOAT_UNAVAILABLE"
    DUPLICATE = "DUPLICATE"
    OTHER = "OTHER"


class LeadContactAttemptChannel(StrEnum):
    """Bounded contact-attempt channel vocabulary (contract §8A).

    Records broker action only -- never buyer receipt/response/interest.
    """

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    MESSAGING = "MESSAGING"
    OTHER = "OTHER"


class LeadTimelineEventType(StrEnum):
    """Mechanically distinct append-only timeline event kinds (contract §8).

    Sufficient to reconstruct broker handling history: status/assignment/
    read mutations, notes, follow-up changes, contact attempts and closure.
    """

    NOTE = "NOTE"
    STATUS_CHANGED = "STATUS_CHANGED"
    ASSIGNED = "ASSIGNED"
    UNASSIGNED = "UNASSIGNED"
    MARKED_READ = "MARKED_READ"
    FOLLOW_UP_SET = "FOLLOW_UP_SET"
    FOLLOW_UP_CLEARED = "FOLLOW_UP_CLEARED"
    CONTACT_ATTEMPT = "CONTACT_ATTEMPT"
    CLOSED = "CLOSED"


#: Bounded per contract §8's "bounded note text" -- generous enough for a
#: genuine broker handling note while still rejecting unbounded input.
MAX_LEAD_NOTE_LENGTH = 4000


def _reject_control_characters(text: str) -> None:
    for char in text:
        if char in ("\n", "\t"):
            continue
        if unicodedata.category(char) == "Cc":
            raise ValueError("text must not contain control characters")


def normalize_lead_note_text(raw: object) -> str:
    """Trim and validate one bounded, non-blank broker note/contact-attempt
    comment.

    Raises `TypeError`/`ValueError` for non-`str` input, empty/whitespace-
    only text, disallowed control characters, or text exceeding
    `MAX_LEAD_NOTE_LENGTH`. Mirrors
    `hullq.domain.buyer_lead.normalize_buyer_message`'s discipline, applied
    here to broker-authored (not buyer-authored) text.
    """
    if not isinstance(raw, str):
        raise TypeError(f"note text must be a str, got {type(raw).__name__}")
    normalized_newlines = raw.replace("\r\n", "\n").replace("\r", "\n")
    trimmed = normalized_newlines.strip()
    if not trimmed:
        raise ValueError("note text must not be empty or whitespace-only")
    if len(trimmed) > MAX_LEAD_NOTE_LENGTH:
        raise ValueError(
            f"note text must be at most {MAX_LEAD_NOTE_LENGTH} characters, got {len(trimmed)}"
        )
    _reject_control_characters(trimmed)
    return trimmed
