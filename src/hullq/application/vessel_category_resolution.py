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

## Coherent snapshot across two statements (amendment review concurrency finding)

This resolver issues two separate read statements (the design-side current
assertion, then the concrete per-Organization current claims). Under
PostgreSQL's default READ COMMITTED isolation, two statements in the same
transaction each take their *own* fresh snapshot, so a concurrent revision
committed between them could combine a stale design assertion with a newer
(or vice versa) concrete claim set -- a window neither read alone can see.
Mirrors `hullq.application.broker_search_fit`'s own identical "Finding A"
rationale: when *conn* is `IDLE` on entry, this function opens its own
`REPEATABLE READ` transaction so both reads share one consistent MVCC
snapshot, then lets it commit on normal exit (read-only, so committing is
harmless). When *conn* already has an open transaction (e.g. this resolver
is called from inside `broker_search_fit`'s own already-`REPEATABLE READ`
transaction), this function does *not* attempt to `SET TRANSACTION
ISOLATION LEVEL` -- PostgreSQL rejects that once a transaction has already
executed a statement -- and instead relies on the isolation level the
caller already established for its own, larger read.
"""

from __future__ import annotations

from typing import Any

from hullq.domain.market_identity import BoatDesignRef, PhysicalBoatId
from hullq.domain.vessel_category import (
    ConcreteVesselCategoryEvidence,
    DesignVesselCategoryEvidence,
    VesselCategoryResolutionResult,
    resolve_vessel_category,
)
from hullq.persistence.boat_design_category import fetch_current_boat_design_category_assertion
from hullq.persistence.physical_boat_claims import list_current_physical_boat_claim_observations

__all__ = ["resolve_physical_boat_vessel_category"]


def _resolve_within_current_snapshot(
    conn: Any, *, physical_boat_id: PhysicalBoatId, boat_design_ref: BoatDesignRef | None
) -> VesselCategoryResolutionResult:
    design_record = (
        fetch_current_boat_design_category_assertion(conn, boat_design_ref.value)
        if boat_design_ref is not None
        else None
    )
    design_evidence = (
        DesignVesselCategoryEvidence(
            assertion_id=design_record.assertion_id,
            boat_design_id=design_record.boat_design_id,
            assertion=design_record.assertion,
            issuer=design_record.issuer,
            recorded_at=design_record.recorded_at,
            previous_assertion_id=design_record.previous_assertion_id,
        )
        if design_record is not None
        else None
    )

    observations = list_current_physical_boat_claim_observations(conn, physical_boat_id)
    concrete_evidence = tuple(
        ConcreteVesselCategoryEvidence(
            claiming_organization_id=observation.claiming_organization_id,
            revision_id=observation.revision_id,
            recorded_by_account_id=observation.recorded_by_account_id,
            recorded_at=observation.recorded_at,
            claim=observation.vessel_category,
        )
        for observation in observations
    )

    return resolve_vessel_category(design_evidence=design_evidence, concrete_evidence=concrete_evidence)


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
    without any database at all. See this module's docstring for the
    snapshot-consistency guarantee across the two reads.
    """
    if not isinstance(physical_boat_id, PhysicalBoatId):
        raise TypeError(
            f"physical_boat_id must be a PhysicalBoatId, got {type(physical_boat_id).__name__}"
        )
    if boat_design_ref is not None and not isinstance(boat_design_ref, BoatDesignRef):
        raise TypeError(
            f"boat_design_ref must be a BoatDesignRef or None, got {type(boat_design_ref).__name__}"
        )

    from psycopg.pq import TransactionStatus  # deferred: no module-level psycopg dependency

    if conn.info.transaction_status == TransactionStatus.IDLE:
        with conn.transaction():
            conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")
            return _resolve_within_current_snapshot(
                conn, physical_boat_id=physical_boat_id, boat_design_ref=boat_design_ref
            )

    return _resolve_within_current_snapshot(
        conn, physical_boat_id=physical_boat_id, boat_design_ref=boat_design_ref
    )
