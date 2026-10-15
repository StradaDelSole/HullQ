"""BoatDesign/configuration `beam` (overall beam) eligibility bridge — SLICE-0087.

The eighth criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design-eligibility evaluation) -- see that module's docstring
for the mandatory second-criterion (and, per SLICE-0085/0086/0087, every
later criterion) abstraction rationale. This module owns only what is
genuinely beam-specific: the two BoatDesign field pointers it qualifies.

    BoatDesign      /baseline/dimensions/beam_m
    NamedVariant    /overrides/dimensions/beam_m

Beam is **one** projected field (`beam_m`) shared by both the `beam_min` and
`beam_max` public query parameters -- never two separate FieldProjectionSpecs
for the same underlying design value (slice normative beam semantics: "Both
public keys count as ONE technical dimension"). A caller supplying one or
both bounds builds one or two `NumericLeafCriterion`s (`MINIMUM`/`MAXIMUM`)
against this single shared `BEAM_FIELD_PROJECTION_SPEC` -- mirrors
`hullq.search.loa_design_bridge` field-for-field.

Never inferred from `beam_waterline_m`, advertised width or a related design
(slice normative beam semantics: "no inferred beam from `beam_waterline_m`,
advertised width or a related design").

Mirrors `hullq.search.loa_design_bridge` exactly in structure (exact Decimal
decode, no taxonomy map, same bounded `FetchCanonicalValue` discipline).

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, or any
inferred beam from another dimension/marketing text.
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
    "BEAM_FIELD_POINTER",
    "BEAM_FIELD_PROJECTION_SPEC",
    "BEAM_OVERRIDE_FIELD_POINTER",
    "BEAM_PROJECTION_FIELD",
    "build_boat_design_beam_configuration_set",
    "compatible_boat_design_ids_for_beam",
    "lookup_beam_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and both the `beam_min`/`beam_max` `NumericLeafCriterion`s it
#: is evaluated against.
BEAM_PROJECTION_FIELD: Final = "beam_m"

#: The exact two bounded field meanings SLICE-0087 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
BEAM_FIELD_POINTER: Final = "/baseline/dimensions/beam_m"
BEAM_OVERRIDE_FIELD_POINTER: Final = "/overrides/dimensions/beam_m"

#: This criterion's shared-bridge field-projection contract (SLICE-0055 §6,
#: extended by SLICE-0085/0087). Exported so the mixed native-inventory
#: application funnel can combine it with the other criteria's own specs in
#: one query.
BEAM_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=BEAM_PROJECTION_FIELD,
    section_key="dimensions",
    field_key="beam_m",
    baseline_pointer=BEAM_FIELD_POINTER,
    override_pointer=BEAM_OVERRIDE_FIELD_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0087's `beam` criterion, hard-bounded to exactly
#: the two field meanings this module's docstring authorizes -- see
#: `hullq.search.boat_design_field_bridge.make_bounded_canonical_value_lookup`.
lookup_beam_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({BEAM_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({BEAM_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_beam_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `beam_m` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge.
    build_boat_design_configuration_set` -- see that function's docstring
    for the baseline/NamedVariant projection rules.
    """
    return build_boat_design_configuration_set(conn, boat_design, (BEAM_FIELD_PROJECTION_SPEC,))


def compatible_boat_design_ids_for_beam(
    conn: Any,
    *,
    beam_min: Decimal | None,
    beam_max: Decimal | None,
    boat_designs: Iterable[Mapping[str, Any]],
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for
    the supplied `beam_min`/`beam_max` bound(s).

    At least one of *beam_min*/*beam_max* must be supplied; both may be, in
    which case both resulting leaves are evaluated against the same
    deduplicated `BEAM_FIELD_PROJECTION_SPEC` (slice normative beam
    semantics). A `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` design-level
    result is simply not included -- neither ever admits a design's
    PhysicalBoats to the concrete evaluation funnel.
    """
    if beam_min is None and beam_max is None:
        raise ValueError("at least one of beam_min/beam_max must be supplied")
    criteria: list[NumericLeafCriterion] = []
    if beam_min is not None:
        criteria.append(
            NumericLeafCriterion(
                field=BEAM_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MINIMUM,
                threshold_min=beam_min,
            )
        )
    if beam_max is not None:
        criteria.append(
            NumericLeafCriterion(
                field=BEAM_PROJECTION_FIELD,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=beam_max,
            )
        )
    query = MixedAndQuery(criteria=tuple(criteria))
    return compatible_boat_design_ids_for_query(
        conn, query, boat_designs, (BEAM_FIELD_PROJECTION_SPEC,)
    )
