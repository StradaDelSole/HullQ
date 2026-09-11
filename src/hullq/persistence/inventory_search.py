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
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hullq.domain.market_identity import BoatDesignRef, NativeListingId, PhysicalBoatId
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId

__all__ = ["ActiveDesignLinkedListing", "list_active_design_linked_listings"]


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
