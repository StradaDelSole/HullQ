"""Professional listing draft persistence — SLICE-0061.

Implements `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md` §6/§7:
durable create/list/read/update of one private pre-market professional draft
aggregate, scoped server-side to `owner_organization_id` on every query
(never trusting a caller-supplied owner) -- mirroring
`hullq.persistence.owner_direct_draft`'s identical discipline, scoped by
Organization instead of Account.

Every read query filters by `(professional_listing_draft_id,
owner_organization_id)` together, in one statement -- a foreign-Organization
draft and an unknown draft therefore return the identical `None`/zero-rows
result by construction, not by a later post-hoc collapsing step (contract
§3.3/§7).

`update_professional_listing_draft`'s version check and mutation are one
atomic `UPDATE ... WHERE version = expected_version` statement (contract
§7): the version comparison and the write happen inside PostgreSQL's own row
evaluation, never via a separate pre-read followed by an unconditional
write. A zero-row update result is then classified (NOT_FOUND vs
VERSION_CONFLICT) by a follow-up diagnostic read that itself stays scoped to
`(professional_listing_draft_id, owner_organization_id)`, so a foreign draft
is still never distinguishable from an unknown one even in the conflict-
classification path.

`list_professional_listing_drafts_page`'s ordering is fixed: `updated_at
DESC, professional_listing_draft_id ASC` (contract §7/§9). Because the
primary sort key sorts descending while the tie-break sorts ascending,
continuation cannot use a simple tuple comparison and instead uses the
explicit two-branch predicate below, mirroring
`hullq.persistence.native_listing_inventory`'s identical `created_at DESC,
native_listing_id ASC` technique.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.listing_draft_payload import ListingDraftPayload, parse_listing_draft_payload
from hullq.domain.market_identity import NativeListingId
from hullq.domain.professional_listing_draft import (
    ProfessionalDraftPromotionState,
    ProfessionalListingDraftId,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "ProfessionalListingDraftLockedRow",
    "ProfessionalListingDraftRecord",
    "ProfessionalListingDraftSortKey",
    "ProfessionalListingDraftUpdateOutcome",
    "ProfessionalListingDraftUpdateResult",
    "create_professional_listing_draft",
    "fetch_professional_listing_draft",
    "list_professional_listing_drafts_page",
    "lock_professional_listing_draft_for_promotion",
    "mark_professional_listing_draft_promoted",
    "update_professional_listing_draft",
]


@dataclass(frozen=True)
class ProfessionalListingDraftRecord:
    """Exact typed readback of one persisted professional draft."""

    draft_id: ProfessionalListingDraftId
    owner_organization_id: MarketplaceOrganizationId
    created_by_account_id: AccountId
    broker_listing_reference: str | None
    broker_description: str | None
    payload: ListingDraftPayload
    version: int
    created_at: datetime
    updated_at: datetime
    promotion_state: ProfessionalDraftPromotionState = ProfessionalDraftPromotionState.EDITABLE
    promoted_native_listing_id: NativeListingId | None = None
    promoted_at: datetime | None = None


@dataclass(frozen=True)
class ProfessionalListingDraftSortKey:
    """The exact deterministic keyset continuation position (contract §7/§9)."""

    updated_at: datetime
    draft_id: ProfessionalListingDraftId


class ProfessionalListingDraftUpdateOutcome(StrEnum):
    """Mechanically distinct update outcomes.

    `NOT_FOUND` deliberately collapses "no such draft_id" and "draft_id
    exists but is owned by a different Organization" into one identical
    outcome (contract §3.3/§7): callers must never be able to use this
    update path as a draft_id/ownership existence oracle.
    """

    UPDATED = "UPDATED"
    NOT_FOUND = "NOT_FOUND"
    VERSION_CONFLICT = "VERSION_CONFLICT"
    PROMOTED_IMMUTABLE = "PROMOTED_IMMUTABLE"


@dataclass(frozen=True)
class ProfessionalListingDraftUpdateResult:
    outcome: ProfessionalListingDraftUpdateOutcome
    record: ProfessionalListingDraftRecord | None = None

    def __post_init__(self) -> None:
        if self.outcome is ProfessionalListingDraftUpdateOutcome.UPDATED and self.record is None:
            raise ValueError("An UPDATED result must carry the new ProfessionalListingDraftRecord")
        if (
            self.outcome is not ProfessionalListingDraftUpdateOutcome.UPDATED
            and self.record is not None
        ):
            raise ValueError("Only an UPDATED result may carry a ProfessionalListingDraftRecord")


_INSERT_DRAFT = """
INSERT INTO professional_listing_drafts
    (professional_listing_draft_id, owner_organization_id, created_by_account_id,
     broker_listing_reference, broker_description, payload, version)
VALUES (%s, %s, %s, %s, %s, %s::jsonb, 1)
RETURNING created_at, updated_at
"""

_DRAFT_COLUMNS = (
    "professional_listing_draft_id, owner_organization_id, created_by_account_id, "
    "broker_listing_reference, broker_description, payload, version, created_at, updated_at, "
    "promotion_state, promoted_native_listing_id, promoted_at"
)

_SELECT_DRAFT_FOR_ORG = f"""
SELECT {_DRAFT_COLUMNS}
FROM professional_listing_drafts
WHERE professional_listing_draft_id = %s AND owner_organization_id = %s
"""

_SELECT_FIRST_PAGE = f"""
SELECT {_DRAFT_COLUMNS}
FROM professional_listing_drafts
WHERE owner_organization_id = %s AND promotion_state = 'EDITABLE'
ORDER BY updated_at DESC, professional_listing_draft_id ASC
LIMIT %s
"""

# updated_at sorts DESC while professional_listing_draft_id tie-breaks ASC,
# so a plain tuple comparison cannot express "strictly after the last
# accepted sort key" -- this explicit two-branch predicate does: either a
# strictly earlier updated_at, or the identical updated_at with a strictly
# greater professional_listing_draft_id.
_SELECT_NEXT_PAGE = f"""
SELECT {_DRAFT_COLUMNS}
FROM professional_listing_drafts
WHERE owner_organization_id = %s AND promotion_state = 'EDITABLE'
  AND (updated_at < %s OR (updated_at = %s AND professional_listing_draft_id > %s))
ORDER BY updated_at DESC, professional_listing_draft_id ASC
LIMIT %s
"""

_UPDATE_DRAFT_IF_CURRENT_VERSION = """
UPDATE professional_listing_drafts
SET broker_listing_reference = %s, broker_description = %s, payload = %s::jsonb,
    version = version + 1, updated_at = NOW()
WHERE professional_listing_draft_id = %s AND owner_organization_id = %s AND version = %s
  AND promotion_state = 'EDITABLE'
RETURNING created_by_account_id, payload, version, created_at, updated_at
"""

_SELECT_STATE_FOR_ORG = """
SELECT promotion_state FROM professional_listing_drafts
WHERE professional_listing_draft_id = %s AND owner_organization_id = %s
"""

_SELECT_DRAFT_FOR_UPDATE = f"""
SELECT {_DRAFT_COLUMNS}
FROM professional_listing_drafts
WHERE professional_listing_draft_id = %s AND owner_organization_id = %s
FOR UPDATE
"""

_MARK_DRAFT_PROMOTED = """
UPDATE professional_listing_drafts
SET promotion_state = 'PROMOTED', promoted_native_listing_id = %s, promoted_at = NOW()
WHERE professional_listing_draft_id = %s AND owner_organization_id = %s
  AND version = %s AND promotion_state = 'EDITABLE'
RETURNING promoted_at
"""


def _row_to_record(row: tuple[Any, ...]) -> ProfessionalListingDraftRecord:
    (
        draft_id_value,
        owner_organization_id_value,
        created_by_account_id_value,
        broker_listing_reference,
        broker_description,
        payload_dict,
        version,
        created_at,
        updated_at,
        promotion_state_value,
        promoted_native_listing_id_value,
        promoted_at,
    ) = row
    return ProfessionalListingDraftRecord(
        draft_id=ProfessionalListingDraftId(draft_id_value),
        owner_organization_id=MarketplaceOrganizationId(owner_organization_id_value),
        created_by_account_id=AccountId(created_by_account_id_value),
        broker_listing_reference=broker_listing_reference,
        broker_description=broker_description,
        payload=parse_listing_draft_payload(payload_dict),
        version=version,
        created_at=created_at,
        updated_at=updated_at,
        promotion_state=ProfessionalDraftPromotionState(promotion_state_value),
        promoted_native_listing_id=(
            NativeListingId(promoted_native_listing_id_value)
            if promoted_native_listing_id_value is not None
            else None
        ),
        promoted_at=promoted_at,
    )


def create_professional_listing_draft(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    created_by_account_id: AccountId,
    broker_listing_reference: str | None,
    broker_description: str | None = None,
    payload: ListingDraftPayload,
) -> ProfessionalListingDraftRecord:
    """Durably create one new draft owned by *owner_organization_id*, version 1.

    *payload* may be `EMPTY_LISTING_DRAFT_PAYLOAD` (an empty newly-created
    draft is valid). *broker_description* is the SLICE-0065 professional-only
    `listing_offer.broker_description` input, stored outside *payload*
    exactly like *broker_listing_reference*. The caller owns transaction
    commit.
    """
    import uuid

    if not isinstance(owner_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "owner_organization_id must be a MarketplaceOrganizationId, "
            f"got {type(owner_organization_id).__name__}"
        )
    if not isinstance(created_by_account_id, AccountId):
        raise TypeError(
            f"created_by_account_id must be an AccountId, got {type(created_by_account_id).__name__}"
        )
    if broker_listing_reference is not None and not isinstance(broker_listing_reference, str):
        raise TypeError(
            "broker_listing_reference must be a str or None, "
            f"got {type(broker_listing_reference).__name__}"
        )
    if broker_description is not None and not isinstance(broker_description, str):
        raise TypeError(
            f"broker_description must be a str or None, got {type(broker_description).__name__}"
        )
    if not isinstance(payload, ListingDraftPayload):
        raise TypeError(f"payload must be a ListingDraftPayload, got {type(payload).__name__}")

    draft_id = ProfessionalListingDraftId(str(uuid.uuid4()))
    with conn.cursor() as cur:
        cur.execute(
            _INSERT_DRAFT,
            [
                draft_id.value,
                owner_organization_id.value,
                created_by_account_id.value,
                broker_listing_reference,
                broker_description,
                json.dumps(payload.to_wire_dict()),
            ],
        )
        row = cur.fetchone()
    assert row is not None
    created_at, updated_at = row
    return ProfessionalListingDraftRecord(
        draft_id=draft_id,
        owner_organization_id=owner_organization_id,
        created_by_account_id=created_by_account_id,
        broker_listing_reference=broker_listing_reference,
        broker_description=broker_description,
        payload=payload,
        version=1,
        created_at=created_at,
        updated_at=updated_at,
    )


def fetch_professional_listing_draft(
    conn: Any,
    *,
    draft_id: ProfessionalListingDraftId,
    owner_organization_id: MarketplaceOrganizationId,
) -> ProfessionalListingDraftRecord | None:
    """Read one draft, scoped to its owner Organization. `None` for a
    foreign or unknown draft_id alike."""
    if not isinstance(draft_id, ProfessionalListingDraftId):
        raise TypeError(
            f"draft_id must be a ProfessionalListingDraftId, got {type(draft_id).__name__}"
        )
    if not isinstance(owner_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "owner_organization_id must be a MarketplaceOrganizationId, "
            f"got {type(owner_organization_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_DRAFT_FOR_ORG, [draft_id.value, owner_organization_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_record(row)


def list_professional_listing_drafts_page(
    conn: Any,
    *,
    owner_organization_id: MarketplaceOrganizationId,
    limit: int,
    after: ProfessionalListingDraftSortKey | None,
) -> list[ProfessionalListingDraftRecord]:
    """Fetch up to *limit* rows owned by *owner_organization_id*,
    deterministically ordered `updated_at DESC, professional_listing_draft_id
    ASC`, continuing strictly after *after* when supplied.

    Never loads unbounded Organization draft state: *limit* always bounds
    this single query, and no total-count query is issued.
    """
    if not isinstance(owner_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "owner_organization_id must be a MarketplaceOrganizationId, "
            f"got {type(owner_organization_id).__name__}"
        )
    if after is not None and not isinstance(after, ProfessionalListingDraftSortKey):
        raise TypeError(
            f"after must be a ProfessionalListingDraftSortKey or None, got {type(after).__name__}"
        )
    if limit <= 0:
        raise ValueError("limit must be positive")

    with conn.cursor() as cur:
        if after is None:
            cur.execute(_SELECT_FIRST_PAGE, [owner_organization_id.value, limit])
        else:
            cur.execute(
                _SELECT_NEXT_PAGE,
                [
                    owner_organization_id.value,
                    after.updated_at,
                    after.updated_at,
                    after.draft_id.value,
                    limit,
                ],
            )
        rows = cur.fetchall()
    return [_row_to_record(row) for row in rows]


def update_professional_listing_draft(
    conn: Any,
    *,
    draft_id: ProfessionalListingDraftId,
    owner_organization_id: MarketplaceOrganizationId,
    broker_listing_reference: str | None,
    broker_description: str | None = None,
    payload: ListingDraftPayload,
    expected_version: int,
) -> ProfessionalListingDraftUpdateResult:
    """Atomically advance *draft_id* to *payload*/*broker_listing_reference*/
    *broker_description* iff its current version equals *expected_version*
    and it is owned by *owner_organization_id*.

    A stale *expected_version* -> `VERSION_CONFLICT`, zero mutation
    (contract §7). A foreign or unknown *draft_id* -> `NOT_FOUND`, zero
    mutation, indistinguishable from each other. The caller owns
    transaction commit.
    """
    if not isinstance(draft_id, ProfessionalListingDraftId):
        raise TypeError(
            f"draft_id must be a ProfessionalListingDraftId, got {type(draft_id).__name__}"
        )
    if not isinstance(owner_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "owner_organization_id must be a MarketplaceOrganizationId, "
            f"got {type(owner_organization_id).__name__}"
        )
    if broker_listing_reference is not None and not isinstance(broker_listing_reference, str):
        raise TypeError(
            "broker_listing_reference must be a str or None, "
            f"got {type(broker_listing_reference).__name__}"
        )
    if broker_description is not None and not isinstance(broker_description, str):
        raise TypeError(
            f"broker_description must be a str or None, got {type(broker_description).__name__}"
        )
    if not isinstance(payload, ListingDraftPayload):
        raise TypeError(f"payload must be a ListingDraftPayload, got {type(payload).__name__}")
    if not isinstance(expected_version, int) or isinstance(expected_version, bool):
        raise TypeError(f"expected_version must be an int, got {type(expected_version).__name__}")
    if expected_version <= 0:
        raise ValueError(f"expected_version must be positive, got {expected_version}")

    with conn.cursor() as cur:
        cur.execute(
            _UPDATE_DRAFT_IF_CURRENT_VERSION,
            [
                broker_listing_reference,
                broker_description,
                json.dumps(payload.to_wire_dict()),
                draft_id.value,
                owner_organization_id.value,
                expected_version,
            ],
        )
        row = cur.fetchone()
        if row is not None:
            created_by_account_id_value, _payload_dict, new_version, created_at, updated_at = row
            record = ProfessionalListingDraftRecord(
                draft_id=draft_id,
                owner_organization_id=owner_organization_id,
                created_by_account_id=AccountId(created_by_account_id_value),
                broker_listing_reference=broker_listing_reference,
                broker_description=broker_description,
                payload=payload,
                version=new_version,
                created_at=created_at,
                updated_at=updated_at,
            )
            return ProfessionalListingDraftUpdateResult(
                outcome=ProfessionalListingDraftUpdateOutcome.UPDATED, record=record
            )

        cur.execute(_SELECT_STATE_FOR_ORG, [draft_id.value, owner_organization_id.value])
        state_row = cur.fetchone()

    if state_row is None:
        return ProfessionalListingDraftUpdateResult(
            outcome=ProfessionalListingDraftUpdateOutcome.NOT_FOUND
        )
    if ProfessionalDraftPromotionState(state_row[0]) is ProfessionalDraftPromotionState.PROMOTED:
        return ProfessionalListingDraftUpdateResult(
            outcome=ProfessionalListingDraftUpdateOutcome.PROMOTED_IMMUTABLE
        )
    return ProfessionalListingDraftUpdateResult(
        outcome=ProfessionalListingDraftUpdateOutcome.VERSION_CONFLICT
    )


# ---------------------------------------------------------------------------
# SLICE-0067 promotion primitives -- these accept an already-open *cur*
# rather than *conn* and neither open nor commit any transaction: they are
# meant to run as internal steps of the one top-level promotion transaction
# `hullq.persistence.professional_listing_promotion` owns (contract §8/§9),
# never as a second independent commit.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ProfessionalListingDraftLockedRow(ProfessionalListingDraftRecord):
    """Marker alias: a `ProfessionalListingDraftRecord` read under
    `SELECT ... FOR UPDATE`, so the caller's transaction holds the row lock
    for its own duration. Carries no extra fields of its own."""


def lock_professional_listing_draft_for_promotion(
    cur: Any,
    *,
    draft_id: ProfessionalListingDraftId,
    owner_organization_id: MarketplaceOrganizationId,
) -> ProfessionalListingDraftLockedRow | None:
    """Lock and read one draft row for the duration of the caller's
    transaction, scoped to `(draft_id, owner_organization_id)` exactly like
    every other read in this module (contract §7: foreign/unknown draft_id
    stay indistinguishable). `None` for a foreign or unknown draft_id alike.
    """
    if not isinstance(draft_id, ProfessionalListingDraftId):
        raise TypeError(
            f"draft_id must be a ProfessionalListingDraftId, got {type(draft_id).__name__}"
        )
    if not isinstance(owner_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "owner_organization_id must be a MarketplaceOrganizationId, "
            f"got {type(owner_organization_id).__name__}"
        )
    cur.execute(_SELECT_DRAFT_FOR_UPDATE, [draft_id.value, owner_organization_id.value])
    row = cur.fetchone()
    if row is None:
        return None
    record = _row_to_record(row)
    return ProfessionalListingDraftLockedRow(
        draft_id=record.draft_id,
        owner_organization_id=record.owner_organization_id,
        created_by_account_id=record.created_by_account_id,
        broker_listing_reference=record.broker_listing_reference,
        broker_description=record.broker_description,
        payload=record.payload,
        version=record.version,
        created_at=record.created_at,
        updated_at=record.updated_at,
        promotion_state=record.promotion_state,
        promoted_native_listing_id=record.promoted_native_listing_id,
        promoted_at=record.promoted_at,
    )


def mark_professional_listing_draft_promoted(
    cur: Any,
    *,
    draft_id: ProfessionalListingDraftId,
    owner_organization_id: MarketplaceOrganizationId,
    expected_version: int,
    promoted_native_listing_id: NativeListingId,
) -> datetime | None:
    """Atomically flip the exact current EDITABLE version to PROMOTED,
    freezing the exact promoted content version (contract §5: version never
    increments on promotion) and storing the immutable provenance link.

    Returns the database-generated `promoted_at` on success, `None` if zero
    rows matched (the caller is expected to have already validated
    state/version under its own row lock immediately before calling this, so
    a `None` here indicates a caller-side invariant violation, not an
    ordinary outcome to branch on).
    """
    if not isinstance(draft_id, ProfessionalListingDraftId):
        raise TypeError(
            f"draft_id must be a ProfessionalListingDraftId, got {type(draft_id).__name__}"
        )
    if not isinstance(owner_organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "owner_organization_id must be a MarketplaceOrganizationId, "
            f"got {type(owner_organization_id).__name__}"
        )
    if not isinstance(promoted_native_listing_id, NativeListingId):
        raise TypeError(
            "promoted_native_listing_id must be a NativeListingId, "
            f"got {type(promoted_native_listing_id).__name__}"
        )
    if not isinstance(expected_version, int) or isinstance(expected_version, bool):
        raise TypeError(f"expected_version must be an int, got {type(expected_version).__name__}")
    if expected_version <= 0:
        raise ValueError(f"expected_version must be positive, got {expected_version}")

    cur.execute(
        _MARK_DRAFT_PROMOTED,
        [
            promoted_native_listing_id.value,
            draft_id.value,
            owner_organization_id.value,
            expected_version,
        ],
    )
    row = cur.fetchone()
    return row[0] if row is not None else None
