"""BoatDesign/configuration `loa` (length overall) eligibility bridge — SLICE-0085.

The third criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design-eligibility evaluation) -- see that module's docstring
for the mandatory second-criterion (and, per SLICE-0085, third/fourth
criterion) abstraction rationale. This module owns only what is genuinely
LOA-specific: the two BoatDesign field pointers it qualifies.

    BoatDesign      /baseline/dimensions/loa_m
    NamedVariant    /overrides/dimensions/loa_m

LOA is **one** projected field (`loa_m`) shared by both the `loa_min` and
`loa_max` public query parameters -- never two separate FieldProjectionSpecs
for the same underlying design value (slice normative LOA semantics:
"deduplicate this projection spec safely, retaining both requested
comparisons and their evidence"). A caller supplying one or both bounds
builds one or two `NumericLeafCriterion`s (`MINIMUM`/`MAXIMUM`) against this
single shared `LOA_FIELD_PROJECTION_SPEC` -- see
`hullq.application.native_inventory_query.build_mixed_requirement_query`.

Mirrors `hullq.search.draft_max_design_bridge` exactly in structure (exact
Decimal decode, no taxonomy map, same bounded `FetchCanonicalValue`
discipline).

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, or any
inferred length from another dimension/marketing text.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    compatible_boat_design_ids_for_query,
    decode_decimal_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import DesignConfigurationSet
from hullq.search.criteria import NumericLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import NumericComparisonKind

__all__ = [
    "LOA_FIELD_POINTER",
    "LOA_FIELD_PROJECTION_SPEC",
    "LOA_OVERRIDE_FIELD_POINTER",
    "LOA_PROJECTION_FIELD",
    "build_boat_design_loa_configuration_set",
    "compatible_boat_design_ids_for_loa",
    "lookup_loa_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and both the `loa_min`/`loa_max` `NumericLeafCriterion`s it
#: is evaluated against.
LOA_PROJECTION_FIELD: Final = "loa_m"

#: The exact two bounded field meanings SLICE-0085 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
LOA_FIELD_POINTER: Final = "/baseline/dimensions/loa_m"
LOA_OVERRIDE_FIELD_POINTER: Final = "/overrides/dimensions/loa_m"

#: This criterion's shared-bridge field-projection contract (SLICE-0055 §6,
#: extended by SLICE-0085). Exported so the mixed native-inventory
#: application funnel can combine it with the other criteria's own specs in
#: one query.
LOA_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=LOA_PROJECTION_FIELD,
    section_key="dimensions",
    field_key="loa_m",
    baseline_pointer=LOA_FIELD_POINTER,
    override_pointer=LOA_OVERRIDE_FIELD_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0085's `loa` criterion, hard-bounded to exactly
#: the two field meanings this module's docstring authorizes -- see
#: `hullq.search.boat_design_field_bridge.make_bounded_canonical_value_lookup`.
lookup_loa_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({LOA_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({LOA_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_loa_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `loa_m` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge.
    build_boat_design_configuration_set` -- see that function's docstring
    for the baseline/NamedVariant projection rules.
    """
    return build_boat_design_configuration_set(conn, boat_design, (LOA_FIELD_PROJECTION_SPEC,))


def compatible_boat_design_ids_for_loa(
    conn: Any,
    *,
    loa_min: Decimal | None,
    loa_max: Decimal | None,
    boat_designs: Iterable[Mapping[str, Any]],
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for
    the supplied `loa_min`/`loa_max` bound(s).

    At least one of *loa_min*/*loa_max* must be supplied; both may be, in
    which case both resulting leaves are evaluated against the same
    deduplicated `LOA_FIELD_PROJECTION_SPEC` (slice normative LOA semantics).
    A `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` design-level result is
    simply not included -- neither ever admits a design's PhysicalBoats to
    the concrete evaluation funnel.
    """
    if loa_min is None and loa_max is None:
        raise ValueError("at least one of loa_min/loa_max must be supplied")
    criteria: list[NumericLeafCriterion] = []
    if loa_min is not None:
        criteria.append(
            NumericLeafCriterion(
                field=LOA_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MINIMUM,
                threshold_min=loa_min,
            )
        )
    if loa_max is not None:
        criteria.append(
            NumericLeafCriterion(
                field=LOA_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=loa_max,
            )
        )
    query = MixedAndQuery(criteria=tuple(criteria))
    return compatible_boat_design_ids_for_query(
        conn, query, boat_designs, (LOA_FIELD_PROJECTION_SPEC,)
    )
