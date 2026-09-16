"""Owner-direct listing draft application orchestration — SLICE-0054.

Thin orchestration over `hullq.domain.owner_direct_draft` (payload
validation) and `hullq.persistence.owner_direct_draft` (durable state):
translates a signed `SessionClaims` and a raw JSON-decoded request body into
one deterministic outcome FastAPI can render.

Ownership always derives from `session.account_id` (contract §3): none of
these functions accept or consult a caller-supplied owner/account identity.
Every write is wrapped in `with conn.transaction():`, mirroring the accepted
SLICE-0053 `hullq.application.broker_callback` commit convention.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.owner_direct_draft import (
    EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD,
    InvalidOwnerDirectDraftPayloadError,
    OwnerDirectListingDraftId,
    parse_owner_direct_draft_payload,
)
from hullq.persistence.owner_direct_draft import (
    OwnerDirectListingDraftRecord,
    OwnerDirectListingDraftUpdateOutcome,
    create_owner_direct_draft,
    fetch_owner_direct_draft,
    list_owner_direct_drafts,
    update_owner_direct_draft,
)
from hullq.security.session_token import SessionClaims

__all__ = [
    "CreateOwnerDirectDraftOutcome",
    "CreateOwnerDirectDraftResult",
    "GetOwnerDirectDraftOutcome",
    "GetOwnerDirectDraftResult",
    "UpdateOwnerDirectDraftOutcome",
    "UpdateOwnerDirectDraftResult",
    "create_owner_direct_draft_for_account",
    "get_owner_direct_draft_for_account",
    "list_owner_direct_drafts_for_account",
    "record_to_public_dict",
    "update_owner_direct_draft_for_account",
]


def record_to_public_dict(record: OwnerDirectListingDraftRecord) -> dict[str, Any]:
    """The one wire shape used by list/create/read/update responses alike.

    Bounded payload fields are flattened alongside `draft_id`/`version`/
    timestamps -- draft input keys only (contract §6), never implying
    resolved marketplace truth.
    """
    body: dict[str, Any] = {
        "draft_id": record.draft_id.value,
        "version": record.version,
        "created_at": record.created_at.isoformat(),
        "updated_at": record.updated_at.isoformat(),
    }
    body.update(record.payload.to_wire_dict())
    return body


def list_owner_direct_drafts_for_account(
    conn: Any, session: SessionClaims
) -> list[OwnerDirectListingDraftRecord]:
    """List only the signed session's own drafts (contract §3/§8)."""
    return list_owner_direct_drafts(conn, owner_account_id=session.account_id)


class CreateOwnerDirectDraftOutcome(StrEnum):
    CREATED = "CREATED"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"


@dataclass(frozen=True)
class CreateOwnerDirectDraftResult:
    outcome: CreateOwnerDirectDraftOutcome
    record: OwnerDirectListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is CreateOwnerDirectDraftOutcome.CREATED and self.record is None:
            raise ValueError("A CREATED result must carry the new record")
        if self.outcome is not CreateOwnerDirectDraftOutcome.CREATED and self.record is not None:
            raise ValueError("Only a CREATED result may carry a record")


def create_owner_direct_draft_for_account(
    conn: Any, session: SessionClaims, raw_initial_payload: Any
) -> CreateOwnerDirectDraftResult:
    """Create one draft owned by the signed session's Account.

    *raw_initial_payload* is optional: `None` (no request body) is treated
    identically to an explicit empty object (contract §6.1). An invalid
    payload writes zero rows.
    """
    try:
        payload = (
            EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD
            if raw_initial_payload is None
            else parse_owner_direct_draft_payload(raw_initial_payload)
        )
    except InvalidOwnerDirectDraftPayloadError:
        return CreateOwnerDirectDraftResult(outcome=CreateOwnerDirectDraftOutcome.INVALID_PAYLOAD)

    with conn.transaction():
        record = create_owner_direct_draft(
            conn, owner_account_id=session.account_id, payload=payload
        )
    return CreateOwnerDirectDraftResult(
        outcome=CreateOwnerDirectDraftOutcome.CREATED, record=record
    )


class GetOwnerDirectDraftOutcome(StrEnum):
    FOUND = "FOUND"
    NOT_FOUND = "NOT_FOUND"


@dataclass(frozen=True)
class GetOwnerDirectDraftResult:
    outcome: GetOwnerDirectDraftOutcome
    record: OwnerDirectListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is GetOwnerDirectDraftOutcome.FOUND and self.record is None:
            raise ValueError("A FOUND result must carry a record")
        if self.outcome is not GetOwnerDirectDraftOutcome.FOUND and self.record is not None:
            raise ValueError("Only a FOUND result may carry a record")


def get_owner_direct_draft_for_account(
    conn: Any, session: SessionClaims, draft_id_value: str
) -> GetOwnerDirectDraftResult:
    """Read one draft, scoped to the signed session's Account (contract §3/§8)."""
    record = fetch_owner_direct_draft(
        conn,
        draft_id=OwnerDirectListingDraftId(draft_id_value),
        owner_account_id=session.account_id,
    )
    if record is None:
        return GetOwnerDirectDraftResult(outcome=GetOwnerDirectDraftOutcome.NOT_FOUND)
    return GetOwnerDirectDraftResult(outcome=GetOwnerDirectDraftOutcome.FOUND, record=record)


class UpdateOwnerDirectDraftOutcome(StrEnum):
    UPDATED = "UPDATED"
    NOT_FOUND = "NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    INVALID_PAYLOAD = "INVALID_PAYLOAD"


@dataclass(frozen=True)
class UpdateOwnerDirectDraftResult:
    outcome: UpdateOwnerDirectDraftOutcome
    record: OwnerDirectListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is UpdateOwnerDirectDraftOutcome.UPDATED and self.record is None:
            raise ValueError("An UPDATED result must carry the new record")
        if self.outcome is not UpdateOwnerDirectDraftOutcome.UPDATED and self.record is not None:
            raise ValueError("Only an UPDATED result may carry a record")


def update_owner_direct_draft_for_account(
    conn: Any, session: SessionClaims, draft_id_value: str, raw_body: Any
) -> UpdateOwnerDirectDraftResult:
    """Update one draft's full bounded payload iff `expected_version` matches.

    *raw_body* must be a JSON object carrying `expected_version` (a
    positive int) plus the bounded contract §6 payload keys; any other
    shape is `INVALID_PAYLOAD` (400), writing zero rows -- exactly like an
    unknown/invalid payload key or value.
    """
    if not isinstance(raw_body, dict):
        return UpdateOwnerDirectDraftResult(outcome=UpdateOwnerDirectDraftOutcome.INVALID_PAYLOAD)

    body = dict(raw_body)
    expected_version = body.pop("expected_version", None)
    if (
        not isinstance(expected_version, int)
        or isinstance(expected_version, bool)
        or expected_version <= 0
    ):
        return UpdateOwnerDirectDraftResult(outcome=UpdateOwnerDirectDraftOutcome.INVALID_PAYLOAD)

    try:
        payload = parse_owner_direct_draft_payload(body)
    except InvalidOwnerDirectDraftPayloadError:
        return UpdateOwnerDirectDraftResult(outcome=UpdateOwnerDirectDraftOutcome.INVALID_PAYLOAD)

    with conn.transaction():
        result = update_owner_direct_draft(
            conn,
            draft_id=OwnerDirectListingDraftId(draft_id_value),
            owner_account_id=session.account_id,
            payload=payload,
            expected_version=expected_version,
        )

    if result.outcome is OwnerDirectListingDraftUpdateOutcome.UPDATED:
        assert result.record is not None
        return UpdateOwnerDirectDraftResult(
            outcome=UpdateOwnerDirectDraftOutcome.UPDATED, record=result.record
        )
    if result.outcome is OwnerDirectListingDraftUpdateOutcome.VERSION_CONFLICT:
        return UpdateOwnerDirectDraftResult(outcome=UpdateOwnerDirectDraftOutcome.VERSION_CONFLICT)
    return UpdateOwnerDirectDraftResult(outcome=UpdateOwnerDirectDraftOutcome.NOT_FOUND)
