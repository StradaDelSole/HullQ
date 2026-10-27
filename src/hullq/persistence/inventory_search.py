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
    "list_active_design_linked_listings",
    "list_active_design_unresolved_listings",
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
