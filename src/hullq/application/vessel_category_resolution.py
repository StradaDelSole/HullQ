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
Sail funnels consult (`hullq.application.native_inventory_query`,
`hullq.application.inventory_search`, `hullq.application.broker_search_fit`),
never a tenth technical criterion.

## Coherent snapshot, structurally (amendment review Finding F)

Amendment review Finding F: an earlier revision of this function issued the
two reads as separate statements and only wrapped them in its own
`REPEATABLE READ` transaction when the caller's connection happened to be
`IDLE` -- but both public Sail Search entrypoints already run inventory/
eligibility/design SQL before ever reaching this resolver, so that guard
essentially never engaged where it mattered. This function now delegates
both reads to `hullq.persistence.vessel_category_snapshot.
fetch_vessel_category_snapshot`, which folds them into **one** SQL
statement -- PostgreSQL guarantees a single statement's result is drawn from
one consistent snapshot regardless of the surrounding transaction's
isolation level, so there is no remaining two-statement tear window to
protect against and no isolation-level trick is needed here at all.
"""

from __future__ import annotations

from typing import Any

from hullq.domain.market_identity import BoatDesignRef, PhysicalBoatId
from hullq.domain.vessel_category import VesselCategoryResolutionResult, resolve_vessel_category
from hullq.persistence.vessel_category_snapshot import fetch_vessel_category_snapshot

__all__ = ["resolve_physical_boat_vessel_category"]


def resolve_physical_boat_vessel_category(
    conn: Any, *, physical_boat_id: PhysicalBoatId, boat_design_ref: BoatDesignRef | None
) -> VesselCategoryResolutionResult:
    """Resolve the current `VesselCategory` for one PhysicalBoat from real
    persisted state.

    *boat_design_ref* is `None` for a design-unresolved PhysicalBoat (the
    design plane then contributes no evidence at all -- mechanically
    identical treatment to a design that has never recorded a category
    assertion). Reads both planes from one single-statement, structurally
    torn-free snapshot (see this module's docstring) and reuses
    `resolve_vessel_category` as the only combination step -- the same pure
    function a unit test exercises without any database at all.
    """
    if not isinstance(physical_boat_id, PhysicalBoatId):
        raise TypeError(
            f"physical_boat_id must be a PhysicalBoatId, got {type(physical_boat_id).__name__}"
        )
    if boat_design_ref is not None and not isinstance(boat_design_ref, BoatDesignRef):
        raise TypeError(
            f"boat_design_ref must be a BoatDesignRef or None, got {type(boat_design_ref).__name__}"
        )

    snapshot = fetch_vessel_category_snapshot(
        conn,
        physical_boat_id=physical_boat_id,
        boat_design_id=boat_design_ref.value if boat_design_ref is not None else None,
    )
    return resolve_vessel_category(
        design_evidence=snapshot.design_evidence, concrete_evidence=snapshot.concrete_evidence
    )
