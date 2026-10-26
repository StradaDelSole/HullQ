"""Application-level `VesselCategory` resolution -- SLICE-0091.

Combines the two independent source planes
(`hullq.persistence.boat_design_category`'s design-side current assertion
and `hullq.persistence.physical_boat_claims`'s concrete per-Organization
current claims) into one deterministic, inspectable
`hullq.domain.vessel_category.VesselCategoryResolutionResult`, reusing
`hullq.domain.vessel_category.resolve_vessel_category` as the single pure
combination step. No second Search truth engine and no new technical
`CriterionDefinition` are introduced here -- this is the bounded internal
readback/inspector surface plus the fail-closed pre-filter the existing
nine-criterion Sail funnel consults (`hullq.application.native_inventory_query`),
never a tenth technical criterion.
"""

from __future__ import annotations

from typing import Any

from hullq.domain.market_identity import BoatDesignRef, PhysicalBoatId
from hullq.domain.vessel_category import VesselCategoryResolutionResult, resolve_vessel_category
from hullq.persistence.boat_design_category import fetch_current_boat_design_category_assertion
from hullq.persistence.physical_boat_claims import list_current_physical_boat_claim_observations

__all__ = ["resolve_physical_boat_vessel_category"]


def resolve_physical_boat_vessel_category(
    conn: Any, *, physical_boat_id: PhysicalBoatId, boat_design_ref: BoatDesignRef | None
) -> VesselCategoryResolutionResult:
    """Resolve the current `VesselCategory` for one PhysicalBoat from real
    persisted state.

    *boat_design_ref* is `None` for a design-unresolved PhysicalBoat (the
    design plane then contributes no evidence at all -- mechanically
    identical treatment to a design that has never recorded a category
    assertion). Reads both planes from their own independent current-head
    readback (never a joined query that would blur which plane each byte of
    evidence came from) and reuses `resolve_vessel_category` as the only
    combination step -- the same pure function a unit test exercises
    without any database at all.
    """
    if not isinstance(physical_boat_id, PhysicalBoatId):
        raise TypeError(
            f"physical_boat_id must be a PhysicalBoatId, got {type(physical_boat_id).__name__}"
        )
    if boat_design_ref is not None and not isinstance(boat_design_ref, BoatDesignRef):
        raise TypeError(
            f"boat_design_ref must be a BoatDesignRef or None, got {type(boat_design_ref).__name__}"
        )

    design_record = (
        fetch_current_boat_design_category_assertion(conn, boat_design_ref.value)
        if boat_design_ref is not None
        else None
    )
    design_assertion = design_record.assertion if design_record is not None else None

    observations = list_current_physical_boat_claim_observations(conn, physical_boat_id)
    concrete_claims_by_organization = {
        observation.claiming_organization_id.value: observation.vessel_category
        for observation in observations
    }

    return resolve_vessel_category(
        design_assertion=design_assertion,
        concrete_claims_by_organization=concrete_claims_by_organization,
    )
