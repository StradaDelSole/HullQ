"""Owner-direct listing draft persistence — SLICE-0054.

Implements `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md` §5/§7:
durable create/list/read/update of one private pre-market draft aggregate,
scoped server-side to `owner_account_id` on every query (never trusting a
caller-supplied owner), plus atomic optimistic-concurrency update.

Every read query filters by `(draft_id, owner_account_id)` together, in one
statement -- a foreign draft and an unknown draft therefore return the
identical `None`/zero-rows result by construction, not by a later
post-hoc collapsing step (contract §3.5/§9).

`update_owner_direct_draft`'s version check and mutation are one atomic
`UPDATE ... WHERE version = expected_version` statement (contract §7): the
version comparison and the write happen inside PostgreSQL's own row
evaluation, never via a separate pre-read followed by an unconditional
write. A zero-row update result is then classified (NOT_FOUND vs
VERSION_CONFLICT) by a follow-up diagnostic read that itself stays scoped to
`(draft_id, owner_account_id)`, so a foreign draft is still never
distinguishable from an unknown one even in the conflict-classification path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.owner_direct_draft import (
    OwnerDirectDraftPayload,
    OwnerDirectListingDraftId,
    parse_owner_direct_draft_payload,
)
from hullq.domain.publishing_eligibility import AccountId

__all__ = [
    "OwnerDirectListingDraftRecord",
    "OwnerDirectListingDraftUpdateOutcome",
    "OwnerDirectListingDraftUpdateResult",
    "create_owner_direct_draft",
    "fetch_owner_direct_draft",
    "list_owner_direct_drafts",
    "update_owner_direct_draft",
]


@dataclass(frozen=True)
class OwnerDirectListingDraftRecord:
    """Exact typed readback of one persisted owner-direct draft."""

    draft_id: OwnerDirectListingDraftId
    owner_account_id: AccountId
    payload: OwnerDirectDraftPayload
    version: int
    created_at: datetime
    updated_at: datetime


class OwnerDirectListingDraftUpdateOutcome(StrEnum):
    """Mechanically distinct update outcomes.

    `NOT_FOUND` deliberately collapses "no such draft_id" and "draft_id
    exists but is owned by a different Account" into one identical outcome
    (contract §3.5/§9): callers must never be able to use this update path
    as a draft_id/ownership existence oracle.
    """

    UPDATED = "UPDATED"
    NOT_FOUND = "NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"


@dataclass(frozen=True)
class OwnerDirectListingDraftUpdateResult:
    outcome: OwnerDirectListingDraftUpdateOutcome
    record: OwnerDirectListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is OwnerDirectListingDraftUpdateOutcome.UPDATED and self.record is None:
            raise ValueError("An UPDATED result must carry the new OwnerDirectListingDraftRecord")
        if (
            self.outcome is not OwnerDirectListingDraftUpdateOutcome.UPDATED
            and self.record is not None
        ):
            raise ValueError("Only an UPDATED result may carry an OwnerDirectListingDraftRecord")


_INSERT_DRAFT = """
INSERT INTO owner_direct_listing_drafts (draft_id, owner_account_id, payload, version)
VALUES (%s, %s, %s::jsonb, 1)
RETURNING created_at, updated_at
"""

_SELECT_DRAFT_FOR_OWNER = """
SELECT draft_id, owner_account_id, payload, version, created_at, updated_at
FROM owner_direct_listing_drafts
WHERE draft_id = %s AND owner_account_id = %s
"""

_SELECT_DRAFTS_FOR_OWNER = """
SELECT draft_id, owner_account_id, payload, version, created_at, updated_at
FROM owner_direct_listing_drafts
WHERE owner_account_id = %s
ORDER BY updated_at DESC, draft_id ASC
"""

_UPDATE_DRAFT_IF_CURRENT_VERSION = """
UPDATE owner_direct_listing_drafts
SET payload = %s::jsonb, version = version + 1, updated_at = NOW()
WHERE draft_id = %s AND owner_account_id = %s AND version = %s
RETURNING payload, version, created_at, updated_at
"""

_SELECT_VERSION_FOR_OWNER = """
SELECT 1 FROM owner_direct_listing_drafts WHERE draft_id = %s AND owner_account_id = %s
"""


def _row_to_record(row: tuple[Any, ...]) -> OwnerDirectListingDraftRecord:
    draft_id_value, owner_account_id_value, payload_dict, version, created_at, updated_at = row
    return OwnerDirectListingDraftRecord(
        draft_id=OwnerDirectListingDraftId(draft_id_value),
        owner_account_id=AccountId(owner_account_id_value),
        payload=parse_owner_direct_draft_payload(payload_dict),
        version=version,
        created_at=created_at,
        updated_at=updated_at,
    )


def create_owner_direct_draft(
    conn: Any, *, owner_account_id: AccountId, payload: OwnerDirectDraftPayload
) -> OwnerDirectListingDraftRecord:
    """Durably create one new draft owned by *owner_account_id*, version 1.

    *payload* may be `EMPTY_OWNER_DIRECT_DRAFT_PAYLOAD` (contract §6.1: an
    empty newly-created draft is valid). The caller owns transaction commit.
    """
    import uuid

    if not isinstance(owner_account_id, AccountId):
        raise TypeError(
            f"owner_account_id must be an AccountId, got {type(owner_account_id).__name__}"
        )
    if not isinstance(payload, OwnerDirectDraftPayload):
        raise TypeError(f"payload must be an OwnerDirectDraftPayload, got {type(payload).__name__}")

    draft_id = OwnerDirectListingDraftId(str(uuid.uuid4()))
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_DRAFT,
            [draft_id.value, owner_account_id.value, json.dumps(payload.to_wire_dict())],
        )
        row = cur.fetchone()
    assert row is not None
    created_at, updated_at = row
    return OwnerDirectListingDraftRecord(
        draft_id=draft_id,
        owner_account_id=owner_account_id,
        payload=payload,
        version=1,
        created_at=created_at,
        updated_at=updated_at,
    )


def fetch_owner_direct_draft(
    conn: Any, *, draft_id: OwnerDirectListingDraftId, owner_account_id: AccountId
) -> OwnerDirectListingDraftRecord | None:
    """Read one draft, scoped to its owner. `None` for foreign or unknown draft_id alike."""
    if not isinstance(draft_id, OwnerDirectListingDraftId):
        raise TypeError(
            f"draft_id must be an OwnerDirectListingDraftId, got {type(draft_id).__name__}"
        )
    if not isinstance(owner_account_id, AccountId):
        raise TypeError(
            f"owner_account_id must be an AccountId, got {type(owner_account_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_DRAFT_FOR_OWNER, [draft_id.value, owner_account_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_owner_direct_drafts(
    conn: Any, *, owner_account_id: AccountId
) -> list[OwnerDirectListingDraftRecord]:
    """List only *owner_account_id*'s own drafts, newest `updated_at` first.

    `draft_id` is the stable tie-breaker (contract §8 "deterministic
    ordering ... with a stable tie-breaker").
    """
    if not isinstance(owner_account_id, AccountId):
        raise TypeError(
            f"owner_account_id must be an AccountId, got {type(owner_account_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_DRAFTS_FOR_OWNER, [owner_account_id.value])
        rows = cur.fetchall()
    return [_row_to_record(row) for row in rows]


def update_owner_direct_draft(
    conn: Any,
    *,
    draft_id: OwnerDirectListingDraftId,
    owner_account_id: AccountId,
    payload: OwnerDirectDraftPayload,
    expected_version: int,
) -> OwnerDirectListingDraftUpdateResult:
    """Atomically advance *draft_id* to *payload* iff its current version
    equals *expected_version* and it is owned by *owner_account_id*.

    A stale *expected_version* -> `VERSION_CONFLICT`, zero mutation
    (contract §7). A foreign or unknown *draft_id* -> `NOT_FOUND`, zero
    mutation, indistinguishable from each other. The caller owns
    transaction commit.
    """
    if not isinstance(draft_id, OwnerDirectListingDraftId):
        raise TypeError(
            f"draft_id must be an OwnerDirectListingDraftId, got {type(draft_id).__name__}"
        )
    if not isinstance(owner_account_id, AccountId):
        raise TypeError(
            f"owner_account_id must be an AccountId, got {type(owner_account_id).__name__}"
        )
    if not isinstance(payload, OwnerDirectDraftPayload):
        raise TypeError(f"payload must be an OwnerDirectDraftPayload, got {type(payload).__name__}")
    if not isinstance(expected_version, int) or isinstance(expected_version, bool):
        raise TypeError(f"expected_version must be an int, got {type(expected_version).__name__}")
    if expected_version <= 0:
        raise ValueError(f"expected_version must be positive, got {expected_version}")

    with conn.cursor() as cur:
        cur.execute(
            _UPDATE_DRAFT_IF_CURRENT_VERSION,
            [
                json.dumps(payload.to_wire_dict()),
                draft_id.value,
                owner_account_id.value,
                expected_version,
            ],
        )
        row = cur.fetchone()
        if row is not None:
            _payload_dict, new_version, created_at, updated_at = row
            record = OwnerDirectListingDraftRecord(
                draft_id=draft_id,
                owner_account_id=owner_account_id,
                payload=payload,
                version=new_version,
                created_at=created_at,
                updated_at=updated_at,
            )
            return OwnerDirectListingDraftUpdateResult(
                outcome=OwnerDirectListingDraftUpdateOutcome.UPDATED, record=record
            )

        cur.execute(_SELECT_VERSION_FOR_OWNER, [draft_id.value, owner_account_id.value])
        exists = cur.fetchone() is not None

    if exists:
        return OwnerDirectListingDraftUpdateResult(
            outcome=OwnerDirectListingDraftUpdateOutcome.VERSION_CONFLICT
        )
    return OwnerDirectListingDraftUpdateResult(
        outcome=OwnerDirectListingDraftUpdateOutcome.NOT_FOUND
    )
