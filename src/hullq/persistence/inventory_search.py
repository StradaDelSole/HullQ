"""Smallest ACTIVE native-inventory candidate enumeration — SLICE-0051.

Exactly the persistence support the bounded Requirements -> Native Inventory
Search vertical needs (slice Deliverables: "smallest persistence/query
support needed to enumerate ACTIVE native listings and current
same-PhysicalBoat draft observations without a generic fact resolver"):

    every complete, public ACTIVE NativeListing whose PhysicalBoat carries a
    durable BoatDesignRef

This is not a general Search/query repository (mirrors the SLICE-0016
`identity_readback` module's own disclaimer). A PhysicalBoat with no
BoatDesignRef is not returned at all -- slice Required Behavior §3: "concrete
shallow draft without durable applicable design identity -> never confirmed
through fuzzy inference" -- so such a listing never reaches the application
funnel and can never become a confirmed match via identity guesswork.

SLICE-0092 adds `list_active_design_unresolved_listings`, the exact mirror
query for the opposite set (`boat_design_ref IS NULL`) -- a **new, separate**
read never touching `list_active_design_linked_listings` or its SQL, per that
slice's field-proof policy §A ("new separately named ... read ... never
modify `list_active_design_linked_listings` or its accepted SQL"). This is
still not a general Search/query repository: it enumerates candidate
identity only -- no technical field, category or eligibility truth is
decided here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hullq.domain.market_identity import BoatDesignRef, NativeListingId, PhysicalBoatId
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId

__all__ = [
    "ActiveDesignLinkedListing",
    "ActiveDesignUnresolvedListing",
    "ActiveNativeListingCandidate",
    "active_native_listing_candidate_exists_after",
    "list_active_design_linked_listings",
    "list_active_design_unresolved_listings",
    "list_active_native_listing_candidates_page",
]


@dataclass(frozen=True, slots=True)
class ActiveDesignLinkedListing:
    """One ACTIVE NativeListing whose durable chain resolves to a design-linked PhysicalBoat."""

    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    physical_boat_id: PhysicalBoatId
    boat_design_ref: BoatDesignRef


_SELECT_ACTIVE_DESIGN_LINKED_LISTINGS = """
SELECT nl.native_listing_id, nl.publishing_organization_id,
       pb.physical_boat_id, pb.boat_design_ref
FROM native_listings nl
JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id
JOIN physical_boats pb ON pb.physical_boat_id = me.physical_boat_id
WHERE nl.lifecycle_state = 'ACTIVE' AND pb.boat_design_ref IS NOT NULL
ORDER BY nl.native_listing_id
"""


def list_active_design_linked_listings(conn: Any) -> list[ActiveDesignLinkedListing]:
    """Every ACTIVE NativeListing whose chain resolves to a design-linked PhysicalBoat.

    Ordered by `NativeListingId` for deterministic downstream processing.
    `DRAFT`/`WITHDRAWN` listings and any PhysicalBoat without a
    `boat_design_ref` are excluded by the query itself, never filtered after
    the fact.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_ACTIVE_DESIGN_LINKED_LISTINGS)
        rows = cur.fetchall()
    return [
        ActiveDesignLinkedListing(
            native_listing_id=NativeListingId(native_listing_id),
            publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id),
            physical_boat_id=PhysicalBoatId(physical_boat_id),
            boat_design_ref=BoatDesignRef(boat_design_ref),
        )
        for native_listing_id, publishing_organization_id, physical_boat_id, boat_design_ref in rows
    ]


@dataclass(frozen=True, slots=True)
class ActiveDesignUnresolvedListing:
    """One ACTIVE NativeListing whose durable chain resolves to a PhysicalBoat
    with NO BoatDesignRef at all -- SLICE-0092. There is no `boat_design_ref`
    field here (unlike `ActiveDesignLinkedListing`): a design-unresolved
    candidate never carries one, by construction of the query below."""

    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    physical_boat_id: PhysicalBoatId


_SELECT_ACTIVE_DESIGN_UNRESOLVED_LISTINGS = """
SELECT nl.native_listing_id, nl.publishing_organization_id, pb.physical_boat_id
FROM native_listings nl
JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id
JOIN physical_boats pb ON pb.physical_boat_id = me.physical_boat_id
WHERE nl.lifecycle_state = 'ACTIVE' AND pb.boat_design_ref IS NULL
ORDER BY nl.native_listing_id
"""


def list_active_design_unresolved_listings(conn: Any) -> list[ActiveDesignUnresolvedListing]:
    """Every ACTIVE NativeListing whose chain resolves to a design-UNRESOLVED
    PhysicalBoat (`boat_design_ref IS NULL`) -- SLICE-0092 field-proof policy
    §A. The exact mirror-image predicate of
    `list_active_design_linked_listings`'s own `IS NOT NULL`; the two queries
    together are therefore mutually exclusive and jointly exhaustive over
    every ACTIVE NativeListing's PhysicalBoat. `DRAFT`/`WITHDRAWN` listings
    are excluded by the query itself, never filtered after the fact, exactly
    like the design-linked reader.
    """
    with conn.cursor() as cur:
        cur.execute(_SELECT_ACTIVE_DESIGN_UNRESOLVED_LISTINGS)
        rows = cur.fetchall()
    return [
        ActiveDesignUnresolvedListing(
            native_listing_id=NativeListingId(native_listing_id),
            publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id),
            physical_boat_id=PhysicalBoatId(physical_boat_id),
        )
        for native_listing_id, publishing_organization_id, physical_boat_id in rows
    ]


@dataclass(frozen=True, slots=True)
class ActiveNativeListingCandidate:
    """One ACTIVE NativeListing candidate from the bounded, merged-plane page
    read below -- SLICE-0096.

    `boat_design_ref` is `None` for a design-UNRESOLVED candidate (the exact
    same partition `list_active_design_unresolved_listings` enumerates) and
    set for a design-linked candidate (the exact same partition
    `list_active_design_linked_listings` enumerates). Both planes are
    mutually exclusive and jointly exhaustive over the same `pb.boat_design_ref
    IS [NOT] NULL` predicate those two legacy readers already use -- this
    type merely carries both outcomes from ONE bounded query instead of two
    separately unbounded ones, so a caller can split the already-fetched
    bounded batch by this field without a second SQL statement.
    """

    native_listing_id: NativeListingId
    publishing_organization_id: MarketplaceOrganizationId
    physical_boat_id: PhysicalBoatId
    boat_design_ref: BoatDesignRef | None


_SELECT_ACTIVE_NATIVE_LISTING_CANDIDATES_PAGE = """
SELECT nl.native_listing_id, nl.publishing_organization_id,
       pb.physical_boat_id, pb.boat_design_ref
FROM native_listings nl
JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id
JOIN physical_boats pb ON pb.physical_boat_id = me.physical_boat_id
WHERE nl.lifecycle_state = 'ACTIVE'
      AND (%(after)s::text IS NULL OR nl.native_listing_id > %(after)s::text)
ORDER BY nl.native_listing_id
LIMIT %(limit)s
"""

_SELECT_ACTIVE_NATIVE_LISTING_CANDIDATE_EXISTS_AFTER = """
SELECT 1
FROM native_listings nl
JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id
JOIN physical_boats pb ON pb.physical_boat_id = me.physical_boat_id
WHERE nl.lifecycle_state = 'ACTIVE' AND nl.native_listing_id > %(after)s
LIMIT 1
"""


def list_active_native_listing_candidates_page(
    conn: Any, *, after_native_listing_id: str | None, limit: int
) -> list[ActiveNativeListingCandidate]:
    """One bounded page of ACTIVE NativeListing candidates, globally ordered
    by `NativeListingId` across BOTH the design-linked and design-unresolved
    planes in a single query -- SLICE-0096's "one global, monotonically
    increasing NativeListing identity cursor ... across both source planes"
    requirement (READY contract §1/§2).

    This is the one new bounded alternative to calling
    `list_active_design_linked_listings`/`list_active_design_unresolved_listings`
    (both still unbounded `SELECT`s with no `LIMIT`, preserved byte-for-byte
    unchanged for their existing legacy/private callers -- contract §3: "new
    paged reads may be separate helpers and must not silently change
    non-public broker diagnostics"). Ordering by the shared `native_listing_id`
    PRIMARY KEY column directly means a candidate's design-linked/
    design-unresolved partition (`boat_design_ref IS [NOT] NULL`) never
    needs its own independent cursor space to merge: both planes already
    share one physical ordering, so splitting the returned batch by
    `boat_design_ref is None` after the fact can never duplicate or skip an
    identity relative to a single-plane-at-a-time traversal.

    *after_native_listing_id* is the last candidate identity already
    evaluated by a previous page (`None` for the first page of a traversal --
    never a sentinel string). *limit* bounds the exact number of candidate
    rows this one SQL statement may return (the enforceable per-request
    candidate-scan budget, contract §3); the caller still must not loop this
    function to "keep fetching" within one request -- that would reintroduce
    the unbounded risk this function exists to remove.

    Rows exactly matching `limit` do not by themselves prove more rows
    exist beyond the batch -- `active_native_listing_candidate_exists_after`
    below is the bounded O(1) proof for that exact-fill ambiguity.
    """
    if limit <= 0:
        raise ValueError(f"limit must be positive; got {limit}")
    with conn.cursor() as cur:
        cur.execute(
            _SELECT_ACTIVE_NATIVE_LISTING_CANDIDATES_PAGE,
            {"after": after_native_listing_id, "limit": limit},
        )
        rows = cur.fetchall()
    return [
        ActiveNativeListingCandidate(
            native_listing_id=NativeListingId(native_listing_id),
            publishing_organization_id=MarketplaceOrganizationId(publishing_organization_id),
            physical_boat_id=PhysicalBoatId(physical_boat_id),
            boat_design_ref=(
                BoatDesignRef(boat_design_ref) if boat_design_ref is not None else None
            ),
        )
        for native_listing_id, publishing_organization_id, physical_boat_id, boat_design_ref in rows
    ]


def active_native_listing_candidate_exists_after(conn: Any, after_native_listing_id: str) -> bool:
    """Bounded `O(1)` existence proof: is there at least one further ACTIVE
    candidate strictly after *after_native_listing_id* in the identical
    global order `list_active_native_listing_candidates_page` uses?

    SLICE-0096 contract §1's "look-ahead or equivalent bounded exhaustion
    proof ... required before announcing COMPLETE when the final batch
    happens to fill the page exactly" -- a single indexed `LIMIT 1`
    existence check, never a second full page fetch and never a claim of
    completeness inferred merely from "the last batch was smaller than the
    requested limit" alone in the exact-fill case.
    """
    with conn.cursor() as cur:
        cur.execute(
            _SELECT_ACTIVE_NATIVE_LISTING_CANDIDATE_EXISTS_AFTER,
            {"after": after_native_listing_id},
        )
        return cur.fetchone() is not None
