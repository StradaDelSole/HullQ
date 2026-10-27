"""Single-statement coherent VesselCategory read -- SLICE-0091 amendment Finding F.

Independent review Finding F: `hullq.application.vessel_category_resolution`
previously issued the design-side current-assertion read and the concrete
per-Organization current-claims read as two *separate* SQL statements, and
only wrapped them in its own `REPEATABLE READ` transaction when the caller's
connection happened to be `IDLE` on entry. Both public Sail Search
entrypoints (`hullq.application.inventory_search`,
`hullq.application.native_inventory_query`) already run inventory/
eligibility/design SQL before ever reaching the category resolver, so in
practice the connection is essentially never `IDLE` there -- the isolation-
level guard never actually engaged for the paths that matter, and a
concurrent revision landing between the two statements could still combine a
stale design assertion with a newer (or vice versa) concrete claim set.

This module closes that window structurally rather than by relying on
isolation level at all: both reads are folded into **one SQL statement**
(two CTEs, combined into a single result row via `to_jsonb`/`jsonb_agg`).
PostgreSQL guarantees every row a single statement produces is visible
against one consistent snapshot of the database, taken when that statement
begins -- true under READ COMMITTED (a fresh per-statement snapshot) and
under REPEATABLE READ (the transaction's fixed snapshot) alike. There is no
remaining two-statement tear window to protect against, so the caller's
transaction/isolation state no longer matters for this guarantee.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from hullq.domain.physical_boat_claims import AssertionKind, VesselCategory, VesselCategoryClaim
from hullq.domain.physical_boat_claims import PhysicalBoatClaimRevisionId as _ClaimRevisionId
from hullq.domain.provenance import ResolverKind, ResolverMetadata
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    ConcreteVesselCategoryEvidence,
    DesignVesselCategoryAssertion,
    DesignVesselCategoryEvidence,
)

__all__ = ["VesselCategorySnapshot", "fetch_vessel_category_snapshot"]

# NULL = NULL is never TRUE in SQL, so a NULL *boat_design_id* parameter
# (the design-unresolved PhysicalBoat case) naturally yields zero design
# rows -- no separate conditional branch required.
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
           r.vessel_category_assertion_kind, r.vessel_category_value
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
class VesselCategorySnapshot:
    """One torn-free read of both VesselCategory source planes for one
    PhysicalBoat, taken from a single PostgreSQL statement snapshot."""

    design_evidence: DesignVesselCategoryEvidence | None
    concrete_evidence: tuple[ConcreteVesselCategoryEvidence, ...]


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


def _concrete_evidence_from_json(
    raw: list[dict[str, Any]],
) -> tuple[ConcreteVesselCategoryEvidence, ...]:
    evidence = []
    for row in raw:
        kind = row["vessel_category_assertion_kind"]
        value = row["vessel_category_value"]
        claim = (
            VesselCategoryClaim(
                assertion_kind=AssertionKind(kind),
                value=VesselCategory(value) if value is not None else None,
            )
            if kind is not None
            else None
        )
        evidence.append(
            ConcreteVesselCategoryEvidence(
                claiming_organization_id=MarketplaceOrganizationId(row["claiming_organization_id"]),
                revision_id=_ClaimRevisionId(row["claim_revision_id"]),
                recorded_by_account_id=AccountId(row["recorded_by_account_id"]),
                recorded_at=_parse_recorded_at(row["claim_recorded_at"]),
                claim=claim,
            )
        )
    return tuple(evidence)


def fetch_vessel_category_snapshot(
    conn: Any, *, physical_boat_id: Any, boat_design_id: str | None
) -> VesselCategorySnapshot:
    """One torn-free read of both VesselCategory source planes.

    *physical_boat_id* is a `hullq.domain.market_identity.PhysicalBoatId`;
    *boat_design_id* is the plain string id (or `None` for a design-
    unresolved PhysicalBoat). A single `cur.execute()` call -- see this
    module's docstring for why that alone is sufficient to guarantee
    coherence regardless of the caller's transaction/isolation state.
    """
    with conn.cursor() as cur:
        cur.execute(
            _QUERY, {"boat_design_id": boat_design_id, "physical_boat_id": physical_boat_id.value}
        )
        design_json, concrete_json = cur.fetchone()
    return VesselCategorySnapshot(
        design_evidence=_design_evidence_from_json(design_json),
        concrete_evidence=_concrete_evidence_from_json(concrete_json),
    )
