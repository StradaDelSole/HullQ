"""BoatDesign/configuration `draft_max` eligibility bridge — SLICE-0051.

The smallest bounded adapter from a persisted canonical BoatDesign record
(BOAT_DESIGN_SCHEMA.v0.5/v0.6-shaped, as returned by
`hullq.persistence.identity_readback.fetch_boat_design`) to the existing,
unchanged `hullq.search.configuration` / `hullq.search.configuration_engine`
kernel, projecting exactly one numeric field: the design/configuration's own
`baseline.dimensions.draft_max_m` (optionally overridden per
`named_variants[].overrides.dimensions.draft_max_m`).

This module answers only "which designs/configurations could satisfy
`draft <= draft_max`" (slice Required Behavior §D: "design/configuration
evaluation alone never confirms a concrete listed yacht"). It never expands
`design_options` combinations (SLICE-0035's configuration boundary
deliberately does not invent option-combination expansion) and never claims
`configuration_space_complete=True`: this bridge has not established that
every materially possible configuration is represented, only that the
baseline plus every declared NamedVariant is. That conservative `False` only
ever costs a design a `CONFIRMED_NON_MATCH` classification it does not need
here -- SLICE-0051 only ever consumes a design-level `CONFIRMED_MATCH` result
(see `compatible_boat_design_ids`), so `CONFIRMED_NON_MATCH` vs
`INSUFFICIENT_DATA` at the design level makes no difference to the bounded
vertical this slice ships.

A `baseline.dimensions.draft_max_m` (or override) of `null`/absent is treated
as `ValueQualification.MISSING`, exactly like the accepted
`ResolutionState.UNKNOWN` mapping elsewhere in this package: canonical
persistence itself represents "resolved" here (SLICE-0016), so a present
numeric value is `CONFIRMED` and an absent one is `MISSING` -- never a
confirmed non-match and never a fabricated value.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import run_configuration_query
from hullq.search.criteria import NumericLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind, ValueQualification
from hullq.search.values import QualifiedNumericValue, is_finite_real_number

__all__ = [
    "DRAFT_MAX_PROJECTION_FIELD",
    "build_boat_design_draft_configuration_set",
    "compatible_boat_design_ids",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the single `NumericLeafCriterion` it evaluates against.
DRAFT_MAX_PROJECTION_FIELD: Final = "draft_max_m"


def _qualify_draft_max(raw_value: Any) -> QualifiedNumericValue:
    if raw_value is None or not is_finite_real_number(raw_value) or raw_value <= 0:
        return QualifiedNumericValue(value=None, qualification=ValueQualification.MISSING)
    return QualifiedNumericValue(value=float(raw_value), qualification=ValueQualification.CONFIRMED)


def build_boat_design_draft_configuration_set(boat_design: Mapping[str, Any]) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `draft_max_m` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. One
    `ResolvedConfiguration` is emitted for the unmodified baseline plus one
    per `named_variants[]` entry (using that variant's own
    `overrides.dimensions.draft_max_m` when explicitly present, else
    inheriting the baseline value) -- never a `design_options` combination.
    """
    design_id = boat_design["id"]
    baseline_dimensions = ((boat_design.get("baseline") or {}).get("dimensions")) or {}
    baseline_draft_max = baseline_dimensions.get("draft_max_m")

    configurations = [
        ResolvedConfiguration(
            identity=ConfigurationIdentity(
                configuration_id=f"{design_id}::baseline",
                boat_design_id=design_id,
            ),
            projection=ConfigurationProjection(
                numeric_values={DRAFT_MAX_PROJECTION_FIELD: _qualify_draft_max(baseline_draft_max)}
            ),
        )
    ]

    for variant in boat_design.get("named_variants") or []:
        variant_id = variant["id"]
        override_dimensions = ((variant.get("overrides") or {}).get("dimensions")) or {}
        raw_value = override_dimensions.get("draft_max_m", baseline_draft_max)
        configurations.append(
            ResolvedConfiguration(
                identity=ConfigurationIdentity(
                    configuration_id=f"{design_id}::{variant_id}",
                    boat_design_id=design_id,
                    named_variant_id=variant_id,
                ),
                projection=ConfigurationProjection(
                    numeric_values={DRAFT_MAX_PROJECTION_FIELD: _qualify_draft_max(raw_value)}
                ),
            )
        )

    return DesignConfigurationSet(
        design_id=design_id,
        configurations=tuple(configurations),
        configuration_space_complete=False,
        is_fixture=False,
    )


def compatible_boat_design_ids(
    draft_max: float, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for `draft_max`.

    *draft_max* is a plain `float` here -- this design-level eligibility
    check is the accepted legacy float-based Search kernel path (slice item
    B: only the concrete PhysicalBoat comparison must be exact-Decimal); the
    caller is responsible for converting its own exact-Decimal requirement
    once, at this one boundary, never repeatedly. A `CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA` design-level result is simply not included -- neither
    ever admits a design's PhysicalBoats to the concrete evaluation funnel.
    """
    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return frozenset()

    configuration_sets = tuple(build_boat_design_draft_configuration_set(bd) for bd in boat_designs)
    query = MixedAndQuery(
        criteria=(
            NumericLeafCriterion(
                field=DRAFT_MAX_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=draft_max,
            ),
        )
    )
    outcome = run_configuration_query(query, configuration_sets)
    return frozenset(evaluation.design_id for evaluation in outcome.confirmed_matches)
