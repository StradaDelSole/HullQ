"""Durable NativeListing publication lifecycle persistence — SLICE-0049.

Given an already-persisted, complete SLICE-0043/0045/0046/0047 NativeListing
chain, evaluate the real accepted SLICE-0041 eligibility boundary and,
only when every applicable condition holds, atomically move the listing
through exactly one of the two authorized lifecycle transitions:

    DRAFT -> ACTIVE       (publish_native_listing)
    ACTIVE -> WITHDRAWN   (withdraw_native_listing)

Lifecycle state lives as an added column on the existing SLICE-0043
``native_listings`` table (``lifecycle_state``), deliberately outside the
accepted 0043 immutable creation envelope: it is never referenced by
``create_native_listing``'s content hash, idempotency or collision
semantics, so an exact retry of the original immutable creation request
remains accepted/idempotent no matter how lifecycle later changes.

Every successful transition atomically appends one immutable, append-only
``native_listing_publication_transitions`` audit row in the same database
transaction as the current-state change -- a successful transition with no
audit record, or an audit record with no matching state change, is
impossible by construction. A denied, cross-Organization, missing,
incomplete or stale-state transition request writes nothing and appends no
audit row.

Concurrency safety reuses the same ``SELECT ... FOR UPDATE`` row-lock
pattern already accepted for offer-revision writes
(``hullq.persistence.native_listing_offer``): the lock on the target
``native_listings`` row serializes every concurrent lifecycle attempt for
that NativeListingId, so at most one competing request can ever observe
the expected ``from_state`` and apply a transition; every other concurrent
or later-stale attempt re-reads the already-updated current state and fails
closed as ``CURRENT_STATE_CONFLICT`` with zero mutation and zero audit
rows.

Publication completeness (SLICE-0049 §7) is checked only for
``DRAFT -> ACTIVE``: the durable chain must already resolve NativeListing ->
non-null MarketEpisode -> existing PhysicalBoat -> explicit current
LISTING_OFFER head, using the same accepted persistence fetch functions
already used by SLICE-0048's previewable-read predicate (deliberately not
imported from the application layer, to avoid a persistence-module
dependency on application code).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any

from hullq.domain.market_identity import MarketEpisodeId, NativeListingId
from hullq.domain.native_listing_lifecycle import (
    NativeListingLifecycleState,
    PublicationTransitionId,
)
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganization,
    MarketplaceOrganizationId,
    OrganizationMembership,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat import fetch_physical_boat

__all__ = [
    "LifecycleTransitionResult",
    "LifecycleTransitionStatus",
    "NativeListingLifecycleTransactionOwnershipError",
    "PublicationTransitionRecord",
    "fetch_lifecycle_state",
    "list_publication_transitions",
    "publish_native_listing",
    "withdraw_native_listing",
]


class NativeListingLifecycleTransactionOwnershipError(RuntimeError):
    """A lifecycle transition cannot safely own a top-level transaction on *conn*.

    Mirrors `hullq.persistence.native_listing_offer.NativeListingOfferTransactionOwnershipError`:
    a TRANSITIONED result must always mean the new lifecycle state and its
    audit row are already durably committed together, independent of later
    caller action. That guarantee only holds when *conn* is IDLE (no
    transaction already open), since psycopg's ``conn.transaction()``
    otherwise silently degrades to a nested SAVEPOINT. Call
    ``conn.commit()``/``conn.rollback()`` first, or pass a freshly opened
    connection.
    """


class LifecycleTransitionStatus(StrEnum):
    """Mechanically distinct transition outcomes. Never a bare boolean."""

    TRANSITIONED = "transitioned"
    NATIVE_LISTING_NOT_FOUND = "native_listing_not_found"
    INCOMPLETE_LISTING = "incomplete_listing"
    DENIED = "denied"
    ORGANIZATION_MISMATCH = "organization_mismatch"
    CURRENT_STATE_CONFLICT = "current_state_conflict"


@dataclass(frozen=True)
class LifecycleTransitionResult:
    """Deterministic result of one publish/withdraw attempt.

    `DENIED` always carries the real SLICE-0041 denial reason. `TRANSITIONED`
    always carries the newly appended immutable `transition_id`. No other
    status carries either.
    """

    status: LifecycleTransitionStatus
    denial_reason: PublishingEligibilityReason | None = None
    transition_id: PublicationTransitionId | None = None

    def __post_init__(self) -> None:
        if self.status is LifecycleTransitionStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED lifecycle result must carry an explicit denial reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED lifecycle result may carry a denial reason")

        if self.status is LifecycleTransitionStatus.TRANSITIONED:
            if self.transition_id is None:
                raise ValueError("A TRANSITIONED lifecycle result must carry a transition_id")
        elif self.transition_id is not None:
            raise ValueError("Only a TRANSITIONED lifecycle result may carry a transition_id")


@dataclass(frozen=True)
class PublicationTransitionRecord:
    """Exact typed readback of one immutable publication-transition row."""

    transition_id: PublicationTransitionId
    native_listing_id: NativeListingId
    from_state: NativeListingLifecycleState
    to_state: NativeListingLifecycleState
    actor_account_id: AccountId
    publishing_organization_id: MarketplaceOrganizationId
    occurred_at: datetime


# ---------------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------------

_SELECT_LISTING_FOR_UPDATE = (
    "SELECT publishing_organization_id, lifecycle_state, market_episode_id "
    "FROM native_listings WHERE native_listing_id = %s FOR UPDATE"
)

_SELECT_LIFECYCLE_STATE = "SELECT lifecycle_state FROM native_listings WHERE native_listing_id = %s"

_UPDATE_LIFECYCLE_STATE = (
    "UPDATE native_listings SET lifecycle_state = %s WHERE native_listing_id = %s"
)

_INSERT_TRANSITION = """
INSERT INTO native_listing_publication_transitions (
    publication_transition_id, native_listing_id, from_state, to_state,
    actor_account_id, publishing_organization_id
) VALUES (%s, %s, %s, %s, %s, %s)
"""

_SELECT_TRANSITIONS = (
    "SELECT publication_transition_id, native_listing_id, from_state, to_state, "
    "actor_account_id, publishing_organization_id, occurred_at "
    "FROM native_listing_publication_transitions WHERE native_listing_id = %s "
    "ORDER BY occurred_at ASC, publication_transition_id ASC"
)


# ---------------------------------------------------------------------------
# Readback
# ---------------------------------------------------------------------------


def fetch_lifecycle_state(
    conn: Any, native_listing_id: NativeListingId
) -> NativeListingLifecycleState | None:
    """Exact current lifecycle state for *native_listing_id*, or `None` if missing.

    `None` covers both "this NativeListingId was never created" and any
    other absence -- callers must not treat `None` as evidence of a
    particular reason.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_LIFECYCLE_STATE, [native_listing_id.value])
        row = cur.fetchone()
    if row is None:
        return None
    return NativeListingLifecycleState(row[0])


def _row_to_transition_record(row: tuple[Any, ...]) -> PublicationTransitionRecord:
    (
        transition_id,
        native_listing_id,
        from_state,
        to_state,
        actor_account_id,
        publishing_organization_id,
        occurred_at,
    ) = row
    return PublicationTransitionRecord(
        transition_id=PublicationTransitionId(transition_id),
        native_listing_id=NativeListingId(native_listing_id),
        from_state=NativeListingLifecycleState(from_state),
        to_state=NativeListingLifecycleState(to_state),
        actor_account_id=AccountId(actor_account_id),
        publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id),
        occurred_at=occurred_at,
    )


def list_publication_transitions(
    conn: Any, native_listing_id: NativeListingId
) -> list[PublicationTransitionRecord]:
    """Exact typed readback of the immutable transition history for one NativeListing.

    Ordered by `occurred_at` for display/audit convenience only.
    """
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(_SELECT_TRANSITIONS, [native_listing_id.value])
        rows = cur.fetchall()
    return [_row_to_transition_record(row) for row in rows]


# ---------------------------------------------------------------------------
# Publication completeness (SLICE-0049 §7)
# ---------------------------------------------------------------------------


def _publication_completeness_satisfied(
    conn: Any, native_listing_id: NativeListingId, market_episode_id_value: str | None
) -> bool:
    """Apply the exact SLICE-0049 §7 fail-closed publication completeness predicate.

    NativeListing existence and its owning MarketplaceOrganization identity
    are already established by the caller before this is invoked; this
    checks only the remaining chain: non-null MarketEpisode link ->
    existing MarketEpisode -> existing PhysicalBoat -> explicit current
    LISTING_OFFER head.
    """
    if market_episode_id_value is None:
        return False
    market_episode_record = fetch_market_episode(conn, MarketEpisodeId(market_episode_id_value))
    if market_episode_record is None:
        return False
    physical_boat_record = fetch_physical_boat(
        conn, market_episode_record.market_episode.physical_boat_id
    )
    if physical_boat_record is None:
        return False
    offer_record = fetch_current_native_listing_offer(conn, native_listing_id)
    return offer_record is not None


# ---------------------------------------------------------------------------
# Transition
# ---------------------------------------------------------------------------


def _apply_transition(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
    from_state: NativeListingLifecycleState,
    to_state: NativeListingLifecycleState,
    require_publication_completeness: bool,
) -> LifecycleTransitionResult:
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )

    decision = evaluate_native_listing_publishing_eligibility(
        account_id, candidate_organization, membership
    )
    if decision.status is PublishingEligibilityStatus.DENIED:
        assert decision.reason is not None
        return LifecycleTransitionResult(
            status=LifecycleTransitionStatus.DENIED, denial_reason=decision.reason
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise NativeListingLifecycleTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); a lifecycle transition requires an IDLE "
            "connection so it can safely own and commit its own top-level transaction. Call "
            "conn.commit()/conn.rollback() first, or pass a freshly opened connection."
        )

    with conn.transaction(), conn.cursor() as cur:
        # Locks the target native_listings row for the duration of this
        # transaction, serializing every concurrent lifecycle attempt for
        # this NativeListingId -- mirrors the FOR UPDATE pattern already
        # accepted for offer-revision writes.
        cur.execute(_SELECT_LISTING_FOR_UPDATE, [native_listing_id.value])
        row = cur.fetchone()
        if row is None:
            return LifecycleTransitionResult(
                status=LifecycleTransitionStatus.NATIVE_LISTING_NOT_FOUND
            )

        listing_organization_id, current_state_text, market_episode_id_value = row
        if listing_organization_id != candidate_organization.id.value:
            return LifecycleTransitionResult(status=LifecycleTransitionStatus.ORGANIZATION_MISMATCH)

        current_state = NativeListingLifecycleState(current_state_text)
        if current_state is not from_state:
            return LifecycleTransitionResult(
                status=LifecycleTransitionStatus.CURRENT_STATE_CONFLICT
            )

        if require_publication_completeness and not _publication_completeness_satisfied(
            conn, native_listing_id, market_episode_id_value
        ):
            return LifecycleTransitionResult(status=LifecycleTransitionStatus.INCOMPLETE_LISTING)

        cur.execute(_UPDATE_LIFECYCLE_STATE, (to_state.value, native_listing_id.value))

        transition_id = PublicationTransitionId(str(uuid.uuid4()))
        cur.execute(
            _INSERT_TRANSITION,
            (
                transition_id.value,
                native_listing_id.value,
                from_state.value,
                to_state.value,
                account_id.value,
                candidate_organization.id.value,
            ),
        )
        return LifecycleTransitionResult(
            status=LifecycleTransitionStatus.TRANSITIONED, transition_id=transition_id
        )


def publish_native_listing(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
) -> LifecycleTransitionResult:
    """Apply `DRAFT -> ACTIVE` iff eligibility, ownership, current state and
    publication completeness (SLICE-0049 §7) all hold.

    Raises NativeListingLifecycleTransactionOwnershipError, before any write
    is attempted, if *conn* already has an open transaction.
    """
    return _apply_transition(
        conn,
        account_id=account_id,
        candidate_organization=candidate_organization,
        membership=membership,
        native_listing_id=native_listing_id,
        from_state=NativeListingLifecycleState.DRAFT,
        to_state=NativeListingLifecycleState.ACTIVE,
        require_publication_completeness=True,
    )


def withdraw_native_listing(
    conn: Any,
    *,
    account_id: AccountId,
    candidate_organization: MarketplaceOrganization,
    membership: OrganizationMembership | None,
    native_listing_id: NativeListingId,
) -> LifecycleTransitionResult:
    """Apply `ACTIVE -> WITHDRAWN` iff eligibility, ownership and current
    state all hold.

    Raises NativeListingLifecycleTransactionOwnershipError, before any write
    is attempted, if *conn* already has an open transaction.
    """
    return _apply_transition(
        conn,
        account_id=account_id,
        candidate_organization=candidate_organization,
        membership=membership,
        native_listing_id=native_listing_id,
        from_state=NativeListingLifecycleState.ACTIVE,
        to_state=NativeListingLifecycleState.WITHDRAWN,
        require_publication_completeness=False,
    )
