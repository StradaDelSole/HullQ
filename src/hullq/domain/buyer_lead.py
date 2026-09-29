"""Durable buyer contact / Lead identity and bounded input validation — SLICE-0070.

Implements `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md` §4/§6/§7/§8:
runtime-distinct `LeadId`/`SubmissionOperationId` identity kinds (mirroring
`hullq.domain.market_identity`'s `_require_kind` discipline), the explicit
forward-compatible contact-email verification vocabulary (never a bare
boolean -- contract §7: "a later verification capability can transition
using evidence rather than reinterpret historical rows"), and the bounded
buyer-supplied name/email/message/submission-operation-id normalizers
(contract §8).

Pure value objects and normalization only -- no persistence/network access.
The email check here is deliberately a bounded syntactic check "valid enough
for contact routing" (contract §8), not full RFC 5322 grammar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum

__all__ = [
    "MAX_BUYER_EMAIL_LENGTH",
    "MAX_BUYER_MESSAGE_LENGTH",
    "MAX_BUYER_NAME_LENGTH",
    "MAX_SUBMISSION_OPERATION_ID_LENGTH",
    "ContactEmailVerificationState",
    "LeadId",
    "LeadSourceChannel",
    "SubmissionOperationId",
    "normalize_buyer_email",
    "normalize_buyer_message",
    "normalize_buyer_name",
    "normalize_submission_operation_id",
]


@dataclass(frozen=True)
class LeadId:
    """Identifies one durable buyer contact Lead.

    Independent from NativeListingId, OrganizationId and AccountId (contract
    §4). Always server-minted at creation -- never client-supplied.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("LeadId.value must be non-empty")


@dataclass(frozen=True)
class SubmissionOperationId:
    """The bounded opaque submission-operation identity the client supplies
    for retry-safe Lead creation (contract §4). Distinct from `LeadId`: this
    is the caller-controlled idempotency key, never the Lead's own identity.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("SubmissionOperationId.value must be non-empty")


class ContactEmailVerificationState(StrEnum):
    """Explicit, forward-compatible verification vocabulary (contract §7).

    v0.1 Lead creation only ever assigns `UNVERIFIED` -- login, delivery
    success, broker response or Lead handling must never silently become
    verification evidence. A later accepted verification capability adds its
    own real evidence-based transition; this enum exists now so that future
    capability never needs to reinterpret historical rows.
    """

    UNVERIFIED = "UNVERIFIED"


class LeadSourceChannel(StrEnum):
    """Bounded source/channel attribution (contract §6/§13).

    v0.1 has exactly one accepted source: the public HullQ listing contact
    surface. Future Search/campaign attribution may extend this vocabulary
    without changing Lead identity (contract §13).
    """

    HULLQ_PUBLIC_LISTING_CONTACT = "HULLQ_PUBLIC_LISTING_CONTACT"


#: Bounded per contract §8. Generous enough for a real buyer's full name
#: while still rejecting unbounded input.
MAX_BUYER_NAME_LENGTH = 200

#: RFC 5321 §4.5.3.1.3's overall maximum mailbox length.
MAX_BUYER_EMAIL_LENGTH = 320

#: Bounded per contract §8. Generous enough for a genuine buyer inquiry
#: while still rejecting unbounded input.
MAX_BUYER_MESSAGE_LENGTH = 5000

#: Bounded per contract §4's "one bounded opaque submission-operation
#: identity" -- generous enough for a client-generated UUID/ULID-shaped
#: value.
MAX_SUBMISSION_OPERATION_ID_LENGTH = 200

#: A bounded syntactic check "valid enough for contact routing" (contract
#: §8), not full RFC 5322 grammar: exactly one "@", a non-empty local part,
#: and a domain part containing at least one ".", with no embedded
#: whitespace.
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _reject_control_characters(text: str, *, allow_newline: bool) -> None:
    """Fail closed on any Unicode "Cc" control character.

    When *allow_newline* is set, `\\n` and `\\t` are exempted -- contract
    §8's "no control characters inappropriate for persisted text" for the
    free-form buyer message, which must still accept ordinary line breaks.
    """
    for char in text:
        if allow_newline and char in ("\n", "\t"):
            continue
        if unicodedata.category(char) == "Cc":
            raise ValueError("text must not contain control characters")


def normalize_buyer_name(raw: object) -> str:
    """Trim and validate a bounded, non-blank, single-line buyer name.

    Raises `TypeError`/`ValueError` for anything that cannot be safely
    persisted: non-`str` input, empty/whitespace-only text, control
    characters, or text exceeding `MAX_BUYER_NAME_LENGTH`.
    """
    if not isinstance(raw, str):
        raise TypeError(f"buyer name must be a str, got {type(raw).__name__}")
    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("buyer name must not be empty or whitespace-only")
    if len(trimmed) > MAX_BUYER_NAME_LENGTH:
        raise ValueError(
            f"buyer name must be at most {MAX_BUYER_NAME_LENGTH} characters, got {len(trimmed)}"
        )
    _reject_control_characters(trimmed, allow_newline=False)
    return trimmed


def normalize_buyer_email(raw: object) -> str:
    """Trim and validate a bounded, syntactically-valid-enough contact email.

    Raises `TypeError`/`ValueError` for non-`str` input, empty/whitespace-
    only text, control characters, text exceeding `MAX_BUYER_EMAIL_LENGTH`,
    or a value that does not match the bounded contact-routing shape.
    """
    if not isinstance(raw, str):
        raise TypeError(f"buyer email must be a str, got {type(raw).__name__}")
    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("buyer email must not be empty or whitespace-only")
    if len(trimmed) > MAX_BUYER_EMAIL_LENGTH:
        raise ValueError(
            f"buyer email must be at most {MAX_BUYER_EMAIL_LENGTH} characters, got {len(trimmed)}"
        )
    _reject_control_characters(trimmed, allow_newline=False)
    if not _EMAIL_RE.fullmatch(trimmed):
        raise ValueError("buyer email is not syntactically valid")
    return trimmed


def normalize_buyer_message(raw: object) -> str:
    """Trim and validate a bounded, non-blank buyer message.

    Line endings are normalized to `\\n` before validation. Raises
    `TypeError`/`ValueError` for non-`str` input, empty/whitespace-only
    text, control characters other than newline/tab, or text exceeding
    `MAX_BUYER_MESSAGE_LENGTH`.
    """
    if not isinstance(raw, str):
        raise TypeError(f"buyer message must be a str, got {type(raw).__name__}")
    normalized_newlines = raw.replace("\r\n", "\n").replace("\r", "\n")
    trimmed = normalized_newlines.strip()
    if not trimmed:
        raise ValueError("buyer message must not be empty or whitespace-only")
    if len(trimmed) > MAX_BUYER_MESSAGE_LENGTH:
        raise ValueError(
            f"buyer message must be at most {MAX_BUYER_MESSAGE_LENGTH} characters, "
            f"got {len(trimmed)}"
        )
    _reject_control_characters(trimmed, allow_newline=True)
    return trimmed


def normalize_submission_operation_id(raw: object) -> str:
    """Trim and validate the bounded opaque submission-operation identity.

    Raises `TypeError`/`ValueError` for non-`str` input, empty/whitespace-
    only text, control characters, or text exceeding
    `MAX_SUBMISSION_OPERATION_ID_LENGTH`.
    """
    if not isinstance(raw, str):
        raise TypeError(f"submission_operation_id must be a str, got {type(raw).__name__}")
    trimmed = raw.strip()
    if not trimmed:
        raise ValueError("submission_operation_id must not be empty or whitespace-only")
    if len(trimmed) > MAX_SUBMISSION_OPERATION_ID_LENGTH:
        raise ValueError(
            "submission_operation_id must be at most "
            f"{MAX_SUBMISSION_OPERATION_ID_LENGTH} characters, got {len(trimmed)}"
        )
    _reject_control_characters(trimmed, allow_newline=False)
    return trimmed
