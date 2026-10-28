"""Single-statement coherent VesselCategory + Power drive read -- SLICE-0093
review amendment Finding G.

Independent review Finding G (BLOCKER): the SLICE-0093 design-linked Power
funnel (`hullq.application.power_inventory_query
.evaluate_power_design_linked_candidates`) called
`resolve_physical_boat_vessel_category` (one SQL statement, reading the
design-side assertion plus the concrete per-Organization *category* claims)
and then separately called `classify_concrete_candidate` (a second,
independently-timed SQL statement, re-reading the concrete per-Organization
claims -- including the drive field) to confirm the drive. A concurrent
revision landing between those two statements could combine a category
admission taken from one revision with a drive confirmation taken from a
*different* revision of the same PhysicalBoat, producing a false
`CONFIRMED_MATCH` the current committed state never actually supports -- the
exact structural MVCC gap `hullq.persistence.vessel_category_snapshot`
(SLICE-0091 amendment Finding F) already closed for category-alone.

This module closes the Power-specific reopening of that gap the same way:
both the design-side category assertion and the concrete per-Organization
claims (category *and* drive together, in the same row) are folded into
**one** SQL statement. The concrete rows are decoded into both a
`ConcreteVesselCategoryEvidence` tuple (for `resolve_vessel_category`,
unchanged) and a `CurrentPhysicalBoatClaimObservation` tuple (for
`classify_concrete_candidate`'s optional pre-fetched *observations*
parameter) from that one read -- so category resolution and drive
classification are always drawn from the identical PostgreSQL snapshot,
never two separately-timed statements.

SLICE-0094 extends this same single statement a second time to also project
`power_engine_count_assertion_kind`/`power_engine_count_value` in the
identical `concrete` CTE row -- the READY contract's own words: "Existing
SLICE-0093 category-and-drive MVCC snapshot must be extended/coherently
reused for category+drive+count, not followed by independent claim reads."
Category, drive and count are therefore always read from exactly the same
current claim revision per claiming Organization, never three separately
timed statements.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.physical_boat_claims import (
    AssertionKind,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    PowerEngineCountClaim,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.physical_boat_claims import PhysicalBoatClaimRevisionId as _ClaimRevisionId
from hullq.domain.provenance import ResolverKind, ResolverMetadata
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    ConcreteVesselCategoryEvidence,
    DesignVesselCategoryAssertion,
    DesignVesselCategoryEvidence,
)
from hullq.persistence.physical_boat_claims import CurrentPhysicalBoatClaimObservation

__all__ = ["PowerCategoryDriveSnapshot", "fetch_power_category_drive_snapshot"]

# Identical design CTE to `hullq.persistence.vessel_category_snapshot`; the
# concrete CTE additionally projects the `power_drive_configuration_*`
# columns so one row carries both fields read at the same snapshot.
_QUERY = """
WITH design AS (
    SELECT a.assertion_id, a.boat_design_id, a.assertion_kind, a.category_value,
           a.issuer_kind, a.issuer_identifier, a.issuer_version,
           a.previous_assertion_id, a.recorded_at
    FROM boat_design_category_assertion_heads h
    JOIN boat_design_category_assertions a ON a.assertion_id = h.current_assertion_id
    WHERE h.boat_design_id = %(boat_design_id)s
),
concrete AS (
    SELECT h.claiming_organization_id, r.claim_revision_id, r.recorded_by_account_id,
           r.recorded_at AS claim_recorded_at,
           r.vessel_category_assertion_kind, r.vessel_category_value,
           r.power_drive_configuration_assertion_kind, r.power_drive_configuration_value,
           r.power_engine_count_assertion_kind, r.power_engine_count_value
    FROM physical_boat_claim_heads h
    JOIN physical_boat_claim_revisions r ON r.claim_revision_id = h.current_claim_revision_id
    WHERE h.physical_boat_id = %(physical_boat_id)s
)
SELECT
    (SELECT to_jsonb(design) FROM design) AS design_json,
    (
        SELECT COALESCE(jsonb_agg(concrete ORDER BY claiming_organization_id), '[]'::jsonb)
        FROM concrete
    ) AS concrete_json
"""


@dataclass(frozen=True)
class PowerCategoryDriveSnapshot:
    """One torn-free read of VesselCategory (design + concrete) *and* the
    concrete Power drive claims for one PhysicalBoat, from a single
    PostgreSQL statement snapshot.

    *observations* carries only `claiming_organization_id` /
    `vessel_category` / `power_drive_configuration` / `power_engine_count`
    populated (every other `CurrentPhysicalBoatClaimObservation` field is
    `None`) -- sufficient for `classify_concrete_candidate`'s
    `active_definitions` being exactly `(POWER_DRIVE_CONFIGURATION_DEFINITION,)`,
    `(POWER_ENGINE_COUNT_DEFINITION,)` or both, and for
    `_qualify_claims_against_definitions`'s same-PhysicalBoat
    cross-Organization check, which reads only the fields named by the
    active definitions it is given.
    """

    design_evidence: DesignVesselCategoryEvidence | None
    concrete_evidence: tuple[ConcreteVesselCategoryEvidence, ...]
    observations: tuple[CurrentPhysicalBoatClaimObservation, ...]


def _parse_recorded_at(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        return raw
    return datetime.fromisoformat(raw)


def _design_evidence_from_json(raw: dict[str, Any] | None) -> DesignVesselCategoryEvidence | None:
    if raw is None:
        return None
    category_value = raw["category_value"]
    assertion = DesignVesselCategoryAssertion(
        assertion_kind=AssertionKind(raw["assertion_kind"]),
        value=VesselCategory(category_value) if category_value is not None else None,
    )
    previous_assertion_id = raw["previous_assertion_id"]
    return DesignVesselCategoryEvidence(
        assertion_id=BoatDesignCategoryAssertionId(raw["assertion_id"]),
        boat_design_id=raw["boat_design_id"],
        assertion=assertion,
        issuer=ResolverMetadata(
            kind=ResolverKind(raw["issuer_kind"]),
            identifier=raw["issuer_identifier"],
            version=raw["issuer_version"],
        ),
        recorded_at=_parse_recorded_at(raw["recorded_at"]),
        previous_assertion_id=(
            BoatDesignCategoryAssertionId(previous_assertion_id)
            if previous_assertion_id is not None
            else None
        ),
    )


def _concrete_rows_from_json(
    raw: list[dict[str, Any]],
) -> tuple[
    tuple[ConcreteVesselCategoryEvidence, ...], tuple[CurrentPhysicalBoatClaimObservation, ...]
]:
    category_evidence: list[ConcreteVesselCategoryEvidence] = []
    observations: list[CurrentPhysicalBoatClaimObservation] = []
    for row in raw:
        claiming_organization_id = MarketplaceOrganizationId(row["claiming_organization_id"])
        revision_id = _ClaimRevisionId(row["claim_revision_id"])
        recorded_by_account_id = AccountId(row["recorded_by_account_id"])
        recorded_at = _parse_recorded_at(row["claim_recorded_at"])

        category_kind = row["vessel_category_assertion_kind"]
        category_value = row["vessel_category_value"]
        category_claim = (
            VesselCategoryClaim(
                assertion_kind=AssertionKind(category_kind),
                value=VesselCategory(category_value) if category_value is not None else None,
            )
            if category_kind is not None
            else None
        )
        category_evidence.append(
            ConcreteVesselCategoryEvidence(
                claiming_organization_id=claiming_organization_id,
                revision_id=revision_id,
                recorded_by_account_id=recorded_by_account_id,
                recorded_at=recorded_at,
                claim=category_claim,
            )
        )

        drive_kind = row["power_drive_configuration_assertion_kind"]
        drive_value = row["power_drive_configuration_value"]
        drive_claim = (
            PowerDriveConfigurationClaim(
                assertion_kind=AssertionKind(drive_kind),
                value=PowerDriveConfiguration(drive_value) if drive_value is not None else None,
            )
            if drive_kind is not None
            else None
        )

        count_kind = row["power_engine_count_assertion_kind"]
        count_value = row["power_engine_count_value"]
        count_claim = (
            PowerEngineCountClaim(assertion_kind=AssertionKind(count_kind), value=count_value)
            if count_kind is not None
            else None
        )

        observations.append(
            CurrentPhysicalBoatClaimObservation(
                claiming_organization_id=claiming_organization_id,
                revision_id=revision_id,
                recorded_by_account_id=recorded_by_account_id,
                recorded_at=recorded_at,
                draft=None,
                keel_configuration=None,
                loa_length=None,
                rudder_configuration=None,
                hull_configuration=None,
                cockpit_position=None,
                deck_saloon=None,
                beam=None,
                hull_material=None,
                vessel_category=category_claim,
                power_drive_configuration=drive_claim,
                power_engine_count=count_claim,
            )
        )
    return tuple(category_evidence), tuple(observations)


def fetch_power_category_drive_snapshot(
    conn: Any, *, physical_boat_id: Any, boat_design_id: str | None
) -> PowerCategoryDriveSnapshot:
    """One torn-free read of both VesselCategory source planes *and* every
    claiming Organization's current Power drive claim.

    *physical_boat_id* is a `hullq.domain.market_identity.PhysicalBoatId`;
    *boat_design_id* is the plain string id (or `None` for a
    design-unresolved PhysicalBoat). A single `cur.execute()` call -- see
    this module's docstring for why that alone is sufficient to guarantee
    coherence regardless of the caller's transaction/isolation state.
    """
    with conn.cursor() as cur:
        cur.execute(
            _QUERY, {"boat_design_id": boat_design_id, "physical_boat_id": physical_boat_id.value}
        )
        design_json, concrete_json = cur.fetchone()
    concrete_evidence, observations = _concrete_rows_from_json(concrete_json)
    return PowerCategoryDriveSnapshot(
        design_evidence=_design_evidence_from_json(design_json),
        concrete_evidence=concrete_evidence,
        observations=observations,
    )
