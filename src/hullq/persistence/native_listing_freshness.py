"""Durable NativeListing freshness evidence / reconfirmation persistence — SLICE-0052.

Given an already-persisted, complete SLICE-0049 NativeListing lifecycle
chain, this module provides:

    fetch_effective_confirmed_at  -- the latest admissible confirmation
                                      evidence timestamp (contract §4), read
                                      from immutable SLICE-0049 publication-
                                      transition history plus this slice's
                                      own reconfirmation-event table;
    reconfirm_native_listing      -- evaluate the real accepted SLICE-0041
                                      eligibility boundary plus the exact
                                      contract §5 ownership/lifecycle
                                      preconditions and, only when every
                                      condition holds, atomically append one
                                      immutable, retry-safe reconfirmation
                                      event.

No mutable "current freshness" row is introduced (contract §4.2): effective
freshness is always derived at read time from this immutable evidence plus
`hullq.domain.native_listing_freshness`'s policy/`as_of` boundary. Time
passage never writes anything through this module.

Concurrency safety reuses the same ``SELECT ... FOR UPDATE`` row-lock
pattern already accepted for lifecycle transitions
(``hullq.persistence.native_listing_lifecycle``): the lock on the target
``native_listings`` row serializes a reconfirmation attempt against any
concurrent lifecycle transition for the same NativeListingId, so a
reconfirmation can never durably succeed against a listing that has just
been withdrawn (or vice versa) without observing the other's effect first.
Idempotency/conflict resolution for the caller-supplied
``FreshnessConfirmationId`` itself is handled race-safely via
``INSERT ... ON CONFLICT DO NOTHING`` plus an exact envelope-fingerprint
comparison — the same pattern already accepted for SLICE-0043 NativeListing
creation (``hullq.persistence.native_listing``) — rather than a
check-then-insert race.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.fingerprint import fingerprint_dict

__all__ = [
    "NativeListingFreshnessTransactionOwnershipError",
    "ReconfirmationResult",
    "ReconfirmationStatus",
    "fetch_effective_confirmed_at",
    "reconfirm_native_listing",
]


class NativeListingFreshnessTransactionOwnershipError(RuntimeError):
    """A reconfirmation attempt cannot safely own a top-level transaction on *conn*.

    Mirrors
    `hullq.persistence.native_listing_lifecycle.NativeListingLifecycleTransactionOwnershipError`:
    a RECONFIRMED result must always mean the new immutable event is already
    durably committed, independent of later caller action. That guarantee
    only holds when *conn* is IDLE (no transaction already open), since
    psycopg's ``conn.transaction()`` otherwise silently degrades to a nested
    SAVEPOINT. Call ``conn.commit()``/``conn.rollback()`` first, or pass a
    freshly opened connection.
    """


class ReconfirmationStatus(StrEnum):
    """Mechanically distinct reconfirmation outcomes. Never a bare boolean."""

    RECONFIRMED = "reconfirmed"
    ALREADY_EXISTS = "already_exists"
    CONFLICT = "conflict"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"
    NOT_ACTIVE = "not_active"
    ORGANIZATION_MISMATCH = "organization_mismatch"
    DENIED = "denied"


@dataclass(frozen=True)
class ReconfirmationResult:
    """Deterministic result of one reconfirmation attempt.

    `DENIED` always carries the real SLICE-0041 denial reason. `RECONFIRMED`
    and `ALREADY_EXISTS` always carry the immutable event's real,
    system-recorded `occurred_at` (the original one, for `ALREADY_EXISTS` --
    an exact retry never manufactures a new timestamp). No other status
    carries either field.
    """

    status: ReconfirmationStatus
    denial_reason: PublishingEligibilityReason | None = None
    occurred_at: datetime | None = None

    def __post_init__(self) -> None:
        if self.status is ReconfirmationStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError(
                    "A DENIED reconfirmation result must carry an explicit denial reason"
                )
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED reconfirmation result may carry a denial reason")

        carries_occurred_at = self.status in (
            ReconfirmationStatus.RECONFIRMED,
            ReconfirmationStatus.ALREADY_EXISTS,
        )
        if carries_occurred_at:
            if self.occurred_at is None:
                raise ValueError(
                    f"A {self.status.value} reconfirmation result must carry occurred_at"
                )
        elif self.occurred_at is not None:
            raise ValueError(
                "Only a RECONFIRMED/ALREADY_EXISTS reconfirmation result may carry occurred_at"
            )


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_LISTING_FOR_UPDATE = (
    "SELECT publishing_organization_id, lifecycle_state "
    "FROM native_listings WHERE native_listing_id = %s FOR UPDATE"
)

_INSERT_CONFIRMATION = """
INSERT INTO native_listing_freshness_confirmations (
    freshness_confirmation_id, native_listing_id, actor_account_id,
    publishing_organization_id, envelope_content_hash
) VALUES (%s, %s, %s, %s, %s)
ON CONFLICT (freshness_confirmation_id) DO NOTHING
RETURNING occurred_at
"""

_SELECT_EXISTING_CONFIRMATION = (
    "SELECT envelope_content_hash, occurred_at "
    "FROM native_listing_freshness_confirmations WHERE freshness_confirmation_id = %s"
)

_SELECT_INITIAL_PUBLICATION_OCCURRED_AT = (
    "SELECT occurred_at FROM native_listing_publication_transitions "
    "WHERE native_listing_id = %s AND from_state = 'DRAFT' AND to_state = 'ACTIVE'"
)

_SELECT_LATEST_RECONFIRMATION_OCCURRED_AT = (
    "SELECT MAX(occurred_at) FROM native_listing_freshness_confirmations "
    "WHERE native_listing_id = %s"
)


def _envelope_fingerprint(
    native_listing_id: str, actor_account_id: str, publishing_organization_id: str
) -> str:
    """Fingerprint exactly the caller-controlled immutable envelope (contract §4.2).

    `occurred_at` is deliberately excluded: it is system-recorded, never
    caller-controlled, and must not participate in idempotency/conflict
    comparison, or an exact retry submitted a moment later than the original
    would wrongly appear to be a CONFLICT.
    """
    return fingerprint_dict(
        {
            "native_listing_id": native_listing_id,
            "actor_account_id": actor_account_id,
            "publishing_organization_id": publishing_organization_id,
        }
    )


def fetch_effective_confirmed_at(conn: Any, native_listing_id: NativeListingId) -> datetime | None:
    """The latest admissible confirmation timestamp for *native_listing_id*, or `None`.

    The effective confirmation time is the greatest of:

    1. the recorded `DRAFT -> ACTIVE` publication-transition `occurred_at`
       (contract §4.1's initial confirmation evidence -- at most one such
       transition can ever exist per listing, since `WITHDRAWN -> ACTIVE`
       republish is not an accepted lifecycle transition); and
    2. the latest immutable reconfirmation event's `occurred_at`
       (contract §4.2).

    Returns `None` when neither exists -- callers must resolve that to
    `FreshnessStatus.UNKNOWN`, never default it to "now".
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_INITIAL_PUBLICATION_OCCURRED_AT, [native_listing_id.value])
        publication_row = cur.fetchone()
        cur.execute(_SELECT_LATEST_RECONFIRMATION_OCCURRED_AT, [native_listing_id.value])
        reconfirmation_row = cur.fetchone()

    candidates: list[datetime] = []
    if publication_row is not None:
        candidates.append(publication_row[0])
    if reconfirmation_row is not None and reconfirmation_row[0] is not None:
        candidates.append(reconfirmation_row[0])
    if not candidates:
        return None
    return max(candidates)


def reconfirm_native_listing(
    conn: Any,
    *,
    confirmation_id: FreshnessConfirmationId,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
) -> ReconfirmationResult:
    """Apply one explicit reconfirmation iff every contract §5 condition holds.

    Evaluated in this exact order: (1) the real accepted SLICE-0041
    eligibility evaluator against *account_id*/*candidate_organization*/
    *membership* -- a DENIED decision touches the database not at all; (2)
    NativeListing existence; (3) candidate Organization == the listing's own
    publishing Organization; (4) current lifecycle == ACTIVE; (5) the
    caller-supplied *confirmation_id*'s retry-safe idempotency/conflict
    resolution. A failure at any step appends no confirmation row and
    mutates no lifecycle/listing fact.

    Raises NativeListingFreshnessTransactionOwnershipError, before any write
    is attempted, if *conn* already has an open transaction.
    """
    if not isinstance(confirmation_id, FreshnessConfirmationId):
        raise TypeError(
            f"confirmation_id must be a FreshnessConfirmationId, got {type(confirmation_id).__name__}"
        )
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )

    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return ReconfirmationResult(
            status=ReconfirmationStatus.DENIED, denial_reason=decision.reason
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise NativeListingFreshnessTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); a reconfirmation requires an IDLE "
            "connection so it can safely own and commit its own top-level transaction. "
            "Call conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    with conn.transaction(), conn.cursor() as cur:
        # Locks the target native_listings row for the duration of this
        # transaction, serializing this reconfirmation attempt against any
        # concurrent lifecycle transition for the same NativeListingId --
        # mirrors the FOR UPDATE pattern already accepted for
        # publish/withdraw.
        cur.execute(_SELECT_LISTING_FOR_UPDATE, [native_listing_id.value])
        row = cur.fetchone()
        if row is None:
            return ReconfirmationResult(status=ReconfirmationStatus.NATIVE_LISTING_NOT_FOUND)

        listing_organization_id, lifecycle_state_text = row
        if listing_organization_id != candidate_organization.id.value:
            return ReconfirmationResult(status=ReconfirmationStatus.ORGANIZATION_MISMATCH)

        if (
            NativeListingLifecycleState(lifecycle_state_text)
            is not NativeListingLifecycleState.ACTIVE
        ):
            return ReconfirmationResult(status=ReconfirmationStatus.NOT_ACTIVE)

        envelope_hash = _envelope_fingerprint(
            native_listing_id.value, account_id.value, candidate_organization.id.value
        )

        cur.execute(
            _INSERT_CONFIRMATION,
            (
                confirmation_id.value,
                native_listing_id.value,
                account_id.value,
                candidate_organization.id.value,
                envelope_hash,
            ),
        )
        inserted = cur.fetchone()
        if inserted is not None:
            return ReconfirmationResult(
                status=ReconfirmationStatus.RECONFIRMED, occurred_at=inserted[0]
            )

        # freshness_confirmation_id already exists (exact retry or a
        # conflicting reuse): compare the caller-controlled immutable
        # envelope only -- occurred_at is deliberately excluded (contract
        # §4.2) -- and never touch/rewrite the original row.
        cur.execute(_SELECT_EXISTING_CONFIRMATION, [confirmation_id.value])
        existing = cur.fetchone()
        assert existing is not None, "ON CONFLICT target row must exist"
        existing_envelope_hash, existing_occurred_at = existing
        if existing_envelope_hash == envelope_hash:
            return ReconfirmationResult(
                status=ReconfirmationStatus.ALREADY_EXISTS, occurred_at=existing_occurred_at
            )
        return ReconfirmationResult(status=ReconfirmationStatus.CONFLICT)
