"""Durable broker-confirmed PhysicalBoat -> canonical BoatDesign first
association -- SLICE-0082 (amended per independent review Finding A,
2026-10-12: transaction-time authorization).

Two independent read/write surfaces:

- a bounded, exact-source canonical BoatDesign candidate projection, reused
  identically for the broker-facing selector search and for a single
  established link's readback context (never two independently maintained
  candidate-shape queries);
- one atomic, single-use, auditable NULL -> non-NULL first-time write to
  the existing SLICE-0046 `physical_boats.boat_design_ref` column.

`associate_physical_boat_design_for_listing` is the sole write entry point.
Required Behavior #3's "Authoritative server-side check must run before
lookup/write and again under transaction" is implemented literally: current
Organization membership, publishing eligibility and the NativeListing ->
MarketEpisode -> PhysicalBoat ownership chain are all re-read -- fresh, with
row-level locks on the membership and Organization rows -- *inside* the
one top-level transaction that performs the CAS write, never from values an
application-layer caller resolved earlier against a separate, already-closed
read transaction. This closes the check-then-act window a purely
application-layer pre-check would leave open: a concurrent membership
revocation or Organization eligibility change either committed before this
transaction's locked read (and is therefore seen and enforced) or is
blocked behind this transaction's lock until it concludes (and is therefore
applied strictly afterward) -- never silently skipped in between.

The write never relaxes `hullq.persistence.physical_boat.create_physical_boat`'s
immutable-create semantics and never reassigns/detaches an existing link: a
non-NULL stored `boat_design_ref` is read-only truth here. The row lock
acquired by `SELECT ... FOR UPDATE` on the target `physical_boats` row is
what actually serializes two concurrent first-association attempts for the
same PhysicalBoat -- the subsequent `UPDATE ... WHERE boat_design_ref IS
NULL` is kept as a defense-in-depth CAS predicate, mirroring every other
identity-write module in this package
(`hullq.persistence.physical_boat.create_physical_boat`,
`hullq.persistence.market_episode.create_market_episode`), never relied on
alone.

A cross-Organization "shared PhysicalBoat" (another Organization's own
NativeListing already resolves to the same PhysicalBoat through its own
MarketEpisode -- SLICE-0040 contract §4: one MarketEpisode may be
referenced by NativeListings from multiple distinct publishing
Organizations) is detected and denied *before* any mutation is attempted:
this module never lets one Organization's unilateral confirmation silently
decide shared real-yacht identity truth for another Organization's own
listing.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from hullq.domain.boat_design_association import (
    DesignCandidate,
    DesignConfirmationMethod,
    parse_generation_identity,
)
from hullq.domain.market_identity import BoatDesignRef, NativeListingId
from hullq.domain.publishing_eligibility import (
    AccountId,
    MarketplaceOrganizationId,
    PublishingEligibilityReason,
    PublishingEligibilityStatus,
    evaluate_native_listing_publishing_eligibility,
)
from hullq.persistence.broker_identity import (
    fetch_marketplace_organization,
    fetch_membership_for_account_and_organization,
)
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing

__all__ = [
    "BoatDesignAssociationTransactionOwnershipError",
    "DesignAssociationStatus",
    "DesignAssociationWriteResult",
    "associate_physical_boat_design_for_listing",
    "fetch_boat_design_candidate",
    "search_boat_design_candidates",
]


class BoatDesignAssociationTransactionOwnershipError(RuntimeError):
    """`associate_physical_boat_design_for_listing` cannot safely own a
    top-level transaction on *conn*.

    Mirrors `hullq.persistence.physical_boat.PhysicalBoatTransactionOwnershipError`:
    a LINKED result must always mean the row/audit event is already durably
    committed, independent of later caller action. That guarantee only
    holds when *conn* is IDLE. Call ``conn.commit()``/``conn.rollback()``
    first, or pass a freshly opened connection.
    """


# ---------------------------------------------------------------------------
# Candidate projection -- shared by selector search and single readback
# ---------------------------------------------------------------------------

_CANDIDATE_SELECT_BASE = """
SELECT cbd.id, cbd.boat_model_id, cbm.canonical_name, cbd.generation,
       cbm.first_built, cbm.last_built,
       COALESCE(
           array_agg(DISTINCT cb.canonical_name) FILTER (WHERE cb.canonical_name IS NOT NULL),
           ARRAY[]::text[]
       ) AS brand_names
FROM canonical_boat_designs cbd
JOIN canonical_boat_models cbm ON cbm.id = cbd.boat_model_id
LEFT JOIN canonical_brand_model_relationships cbmr ON cbmr.boat_model_id = cbm.id
LEFT JOIN canonical_brands cb ON cb.id = cbmr.brand_id
"""

_CANDIDATE_GROUP_BY = (
    "GROUP BY cbd.id, cbd.boat_model_id, cbm.canonical_name, cbd.generation, "
    "cbm.first_built, cbm.last_built"
)


def _row_to_candidate(row: tuple[Any, ...]) -> DesignCandidate:
    (
        design_id,
        boat_model_id,
        canonical_model_name,
        generation,
        first_built,
        last_built,
        brand_names,
    ) = row
    return DesignCandidate(
        boat_design_ref=BoatDesignRef(design_id),
        boat_model_id=boat_model_id,
        canonical_model_name=canonical_model_name,
        generation=parse_generation_identity(generation),
        brand_names=tuple(brand_names or ()),
        first_built=first_built,
        last_built=last_built,
    )


def _escape_like(term: str) -> str:
    """Escape LIKE/ILIKE metacharacters so *term* is matched literally.

    A search term is a way to locate candidates, never a user-controlled SQL
    wildcard fragment (Required Behavior #1: "no ... user-controlled SQL
    fragment")."""
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_boat_design_candidates(
    conn: Any, query: str, *, limit: int = 20
) -> list[DesignCandidate]:
    """Bounded exact-source candidate search, deterministically ordered.

    An empty *query* returns the first *limit* candidates in the same
    deterministic order, never an unfiltered/unbounded catalog dump. *limit*
    is clamped to ``[1, 20]`` regardless of the caller-supplied value
    (Required Behavior #1: "server-defined max 20 results per query").
    """
    bounded_limit = min(max(limit, 1), 20)
    with conn.cursor() as cur:
        if query:
            pattern = f"%{_escape_like(query)}%"
            cur.execute(
                f"{_CANDIDATE_SELECT_BASE} "
                "WHERE cbm.canonical_name ILIKE %s ESCAPE '\\' "
                "OR cb.canonical_name ILIKE %s ESCAPE '\\' "
                f"{_CANDIDATE_GROUP_BY} "
                "ORDER BY cbm.canonical_name, cbd.id LIMIT %s",
                [pattern, pattern, bounded_limit],
            )
        else:
            cur.execute(
                f"{_CANDIDATE_SELECT_BASE} "
                f"{_CANDIDATE_GROUP_BY} "
                "ORDER BY cbm.canonical_name, cbd.id LIMIT %s",
                [bounded_limit],
            )
        rows = cur.fetchall()
    return [_row_to_candidate(row) for row in rows]


def fetch_boat_design_candidate(
    conn: Any, boat_design_ref: BoatDesignRef
) -> DesignCandidate | None:
    """Exact single-identity readback, in the identical projection shape the
    selector search uses -- never a second, differently-shaped query for the
    same underlying canonical identity."""
    if not isinstance(boat_design_ref, BoatDesignRef):
        raise TypeError(
            f"boat_design_ref must be a BoatDesignRef, got {type(boat_design_ref).__name__}"
        )
    with conn.cursor() as cur:
        cur.execute(
            f"{_CANDIDATE_SELECT_BASE} WHERE cbd.id = %s {_CANDIDATE_GROUP_BY}",
            [boat_design_ref.value],
        )
        row = cur.fetchone()
    if row is None:
        return None
    return _row_to_candidate(row)


# ---------------------------------------------------------------------------
# Atomic first-time association write
# ---------------------------------------------------------------------------


class DesignAssociationStatus(StrEnum):
    """Mechanically distinct outcomes. Never a bare boolean."""

    LINKED = "linked"
    ALREADY_LINKED = "already_linked"
    CONFLICT = "conflict"
    DESIGN_NOT_FOUND = "design_not_found"
    PHYSICAL_BOAT_NOT_FOUND = "physical_boat_not_found"
    SHARED_BOAT_CONFLICT = "shared_boat_conflict"
    #: SLICE-0082 amendment Finding A: the fresh, transaction-scoped
    #: membership/Organization-eligibility re-evaluation denied the request.
    DENIED = "denied"
    #: SLICE-0082 amendment Finding A: the fresh, transaction-scoped
    #: NativeListing ownership re-check found it unknown or foreign.
    LISTING_NOT_FOUND = "listing_not_found"
    #: SLICE-0082 amendment Finding A: the fresh, transaction-scoped
    #: NativeListing -> MarketEpisode -> PhysicalBoat chain re-check found a
    #: broken/incomplete link.
    CHAIN_INCOMPLETE = "chain_incomplete"


_STATUSES_CARRYING_STORED_REF = frozenset(
    {
        DesignAssociationStatus.LINKED,
        DesignAssociationStatus.ALREADY_LINKED,
        DesignAssociationStatus.CONFLICT,
    }
)


@dataclass(frozen=True)
class DesignAssociationWriteResult:
    """Deterministic result of one `associate_physical_boat_design_for_listing`
    call.

    `stored_boat_design_ref` is populated for LINKED/ALREADY_LINKED/CONFLICT
    only: the exact durable current value after this call returns (the
    newly-written value for LINKED, the pre-existing value for the other
    two) -- never the caller's requested value when that differs from what
    is actually stored. `denial_reason` is populated for DENIED only, and is
    always the real SLICE-0041 reason the fresh transaction-scoped
    eligibility re-evaluation produced.
    """

    status: DesignAssociationStatus
    stored_boat_design_ref: BoatDesignRef | None = None
    denial_reason: PublishingEligibilityReason | None = None

    def __post_init__(self) -> None:
        if self.status in _STATUSES_CARRYING_STORED_REF:
            if self.stored_boat_design_ref is None:
                raise ValueError(
                    f"A {self.status.value.upper()} result must carry stored_boat_design_ref"
                )
        elif self.stored_boat_design_ref is not None:
            raise ValueError(
                f"A {self.status.value.upper()} result must not carry stored_boat_design_ref"
            )

        if self.status is DesignAssociationStatus.DENIED:
            if self.denial_reason is None:
                raise ValueError("A DENIED result must carry an explicit denial_reason")
        elif self.denial_reason is not None:
            raise ValueError("Only a DENIED result may carry denial_reason")


_SELECT_FOR_UPDATE = (
    "SELECT boat_design_ref FROM physical_boats WHERE physical_boat_id = %s FOR UPDATE"
)

_SELECT_SHARED_BOAT_FOREIGN_LISTING = """
SELECT 1
FROM native_listings nl
JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id
WHERE me.physical_boat_id = %s AND nl.publishing_organization_id != %s
LIMIT 1
"""

_UPDATE_DESIGN_REF_CAS = (
    "UPDATE physical_boats SET boat_design_ref = %s "
    "WHERE physical_boat_id = %s AND boat_design_ref IS NULL"
)

_INSERT_AUDIT_EVENT = """
INSERT INTO boat_design_association_events
    (association_event_id, physical_boat_id, boat_design_ref, native_listing_id,
     confirming_organization_id, recorded_by_account_id, confirmation_method)
VALUES (%s, %s, %s, %s, %s, %s, %s)
"""


def associate_physical_boat_design_for_listing(
    conn: Any,
    *,
    account_id: AccountId,
    organization_id: MarketplaceOrganizationId,
    native_listing_id: NativeListingId,
    boat_design_ref: BoatDesignRef,
) -> DesignAssociationWriteResult:
    """Durably confirm *boat_design_ref* for the PhysicalBoat *native_listing_id*
    resolves to, iff it is currently unresolved and not shared with a
    foreign Organization -- with every authorization/ownership fact
    re-checked fresh, inside this one committing transaction (SLICE-0082
    amendment Finding A; see this module's docstring).

    Authorization order, all inside the same transaction:

    1. lock + re-fetch the Organization and OrganizationMembership rows
       (`FOR UPDATE`) and re-evaluate the real SLICE-0041 publishing-
       eligibility decision against them -- DENIED fails closed with zero
       mutation;
    2. re-fetch the NativeListing and confirm it is still owned by
       *organization_id* -- unknown/foreign fails closed as
       LISTING_NOT_FOUND with zero mutation;
    3. re-resolve NativeListing -> MarketEpisode -> PhysicalBoat -- any
       broken link fails closed as CHAIN_INCOMPLETE with zero mutation;
    4. lock the resolved PhysicalBoat row (`FOR UPDATE`) and apply the
       identical CAS/shared-boat/audit logic as before.

    Race-safe: the `FOR UPDATE` locks above mean a concurrent membership
    revocation, Organization eligibility change, or second association
    attempt for the same PhysicalBoatId either committed strictly before
    this transaction's locked reads (and is therefore seen and enforced) or
    blocks behind this transaction's locks until it concludes (and is
    therefore applied strictly afterward) -- never silently skipped in
    between. Same caller or a later authorized actor re-sending the
    identical already-established target returns ALREADY_LINKED with zero
    additional mutation and zero additional audit rows; a different target
    returns CONFLICT, never silently overwriting the existing link.

    A requested *boat_design_ref* unknown to ``canonical_boat_designs``
    fails closed as DESIGN_NOT_FOUND (real foreign-key violation on the
    actually-attempted UPDATE) and writes zero rows.

    Raises BoatDesignAssociationTransactionOwnershipError, before any
    read/write is attempted, if *conn* already has an open transaction.
    """
    if not isinstance(account_id, AccountId):
        raise TypeError(f"account_id must be an AccountId, got {type(account_id).__name__}")
    if not isinstance(organization_id, MarketplaceOrganizationId):
        raise TypeError(
            "organization_id must be a MarketplaceOrganizationId, "
            f"got {type(organization_id).__name__}"
        )
    if not isinstance(native_listing_id, NativeListingId):
        raise TypeError(
            f"native_listing_id must be a NativeListingId, got {type(native_listing_id).__name__}"
        )
    if not isinstance(boat_design_ref, BoatDesignRef):
        raise TypeError(
            f"boat_design_ref must be a BoatDesignRef, got {type(boat_design_ref).__name__}"
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status != TransactionStatus.IDLE:
        raise BoatDesignAssociationTransactionOwnershipError(
            "conn already has an open transaction (transaction_status="
            f"{conn.info.transaction_status!r}); associate_physical_boat_design_for_listing() "
            "requires an IDLE connection so it can safely own and commit its own top-level "
            "transaction. Call conn.commit()/conn.rollback() first, or pass a freshly "
            "opened connection."
        )

    from psycopg.errors import ForeignKeyViolation  # deferred: no module-level psycopg dependency

    try:
        with conn.transaction(), conn.cursor() as cur:
            # 1. Fresh, locked membership/eligibility re-evaluation.
            organization = fetch_marketplace_organization(conn, organization_id, for_update=True)
            if organization is None:
                return DesignAssociationWriteResult(
                    status=DesignAssociationStatus.LISTING_NOT_FOUND
                )
            membership = fetch_membership_for_account_and_organization(
                conn, account_id, organization_id, for_update=True
            )
            decision = evaluate_native_listing_publishing_eligibility(
                account_id, organization, membership
            )
            if decision.status is PublishingEligibilityStatus.DENIED:
                assert decision.reason is not None
                return DesignAssociationWriteResult(
                    status=DesignAssociationStatus.DENIED, denial_reason=decision.reason
                )

            # 2/3. Fresh NativeListing -> MarketEpisode -> PhysicalBoat
            # ownership-chain re-resolution.
            listing_record = fetch_native_listing(conn, native_listing_id)
            if (
                listing_record is None
                or listing_record.publishing_organization_id != organization_id
            ):
                return DesignAssociationWriteResult(
                    status=DesignAssociationStatus.LISTING_NOT_FOUND
                )
            if listing_record.listing.market_episode_id is None:
                return DesignAssociationWriteResult(status=DesignAssociationStatus.CHAIN_INCOMPLETE)
            episode_record = fetch_market_episode(conn, listing_record.listing.market_episode_id)
            if episode_record is None:
                return DesignAssociationWriteResult(status=DesignAssociationStatus.CHAIN_INCOMPLETE)
            physical_boat_id = episode_record.market_episode.physical_boat_id

            # 4. Lock the resolved PhysicalBoat row and classify/write.
            cur.execute(_SELECT_FOR_UPDATE, [physical_boat_id.value])
            row = cur.fetchone()
            if row is None:
                return DesignAssociationWriteResult(
                    status=DesignAssociationStatus.PHYSICAL_BOAT_NOT_FOUND
                )
            stored_value = row[0]
            if stored_value is not None:
                if stored_value == boat_design_ref.value:
                    return DesignAssociationWriteResult(
                        status=DesignAssociationStatus.ALREADY_LINKED,
                        stored_boat_design_ref=BoatDesignRef(stored_value),
                    )
                return DesignAssociationWriteResult(
                    status=DesignAssociationStatus.CONFLICT,
                    stored_boat_design_ref=BoatDesignRef(stored_value),
                )

            cur.execute(
                _SELECT_SHARED_BOAT_FOREIGN_LISTING,
                [physical_boat_id.value, organization_id.value],
            )
            if cur.fetchone() is not None:
                return DesignAssociationWriteResult(
                    status=DesignAssociationStatus.SHARED_BOAT_CONFLICT
                )

            cur.execute(_UPDATE_DESIGN_REF_CAS, [boat_design_ref.value, physical_boat_id.value])
            assert cur.rowcount == 1, (
                "CAS predicate failed under an already-held FOR UPDATE row lock -- "
                "this must be unreachable"
            )

            cur.execute(
                _INSERT_AUDIT_EVENT,
                (
                    str(uuid.uuid4()),
                    physical_boat_id.value,
                    boat_design_ref.value,
                    native_listing_id.value,
                    organization_id.value,
                    account_id.value,
                    DesignConfirmationMethod.MANUAL_SELECTOR_CONFIRMATION.value,
                ),
            )
            return DesignAssociationWriteResult(
                status=DesignAssociationStatus.LINKED,
                stored_boat_design_ref=boat_design_ref,
            )
    except ForeignKeyViolation:
        return DesignAssociationWriteResult(status=DesignAssociationStatus.DESIGN_NOT_FOUND)
