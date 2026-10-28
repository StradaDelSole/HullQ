"""BoatDesign/configuration `power_engine_count` eligibility bridge — SLICE-0094.

The Power-domain criterion-#2 adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design eligibility) — see that module's docstring for the
mandatory second-criterion abstraction rationale this bridge reuses
unchanged (identical to `hullq.search.power_drive_design_bridge`'s own
reuse for criterion #1). This module owns only what is genuinely
`power_engine_count`-specific: the two bounded BoatDesign field pointers it
qualifies.

    BoatDesign      /baseline/propulsion/engine_count
    NamedVariant    /overrides/propulsion/engine_count

Design-side source is BoatDesign v0.6 `propulsion.engine_count`
(`specs/BOAT_DESIGN_SCHEMA.v0.6.json` `$defs.propulsion_shape.engine_count`:
integer or null, minimum 0). Unlike `power_drive_design_bridge`'s taxonomy
mapping, `engine_count` needs no `taxonomy_map` -- it is an exact `Decimal`
comparison (`decode_decimal_for_qualification`, the identical decode every
other numeric criterion already uses), never a categorical remap. A raw
`engine_count` of `0`/`null`/an unresolved FieldResolution simply fails
closed to `MISSING` via the shared `qualify_canonical_field` mechanism --
never guessed, and never a false affirmative (the public Search whitelist
is 1-8, so an unsupported `0` is always a genuine, non-false non-match
against any requested token, not a confirmed exclusion manufactured by this
module).

A qualifying factory `engine_count` is never, by itself, a current
*installed* count -- a separately qualified current `PhysicalBoatClaims
.power_engine_count` claim is always required too
(`hullq.application.power_inventory_query`'s own concrete-claim
classification, reused unchanged from the Sail/0093 kernel). This module
answers only "what does BoatDesign/NamedVariant qualify", never "what is
currently installed".

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, any other
propulsion attribute, or any mapping beyond this one exact field.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    decode_decimal_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import DesignConfigurationSet

__all__ = [
    "POWER_ENGINE_COUNT_FIELD_PROJECTION_SPEC",
    "POWER_ENGINE_COUNT_PROJECTION_FIELD",
    "PROPULSION_ENGINE_COUNT_FIELD_POINTER",
    "PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER",
    "build_boat_design_power_engine_count_configuration_set",
    "lookup_power_engine_count_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the `NumericLeafCriterion` it is evaluated against.
POWER_ENGINE_COUNT_PROJECTION_FIELD: Final = "power_engine_count"

#: The exact two bounded field meanings SLICE-0094 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
PROPULSION_ENGINE_COUNT_FIELD_POINTER: Final = "/baseline/propulsion/engine_count"
PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER: Final = "/overrides/propulsion/engine_count"

#: This criterion's shared-bridge field-projection contract.
POWER_ENGINE_COUNT_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=POWER_ENGINE_COUNT_PROJECTION_FIELD,
    section_key="propulsion",
    field_key="engine_count",
    baseline_pointer=PROPULSION_ENGINE_COUNT_FIELD_POINTER,
    override_pointer=PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0094's `power_engine_count` criterion, hard-
#: bounded to exactly the two field meanings this module's docstring
#: authorizes -- see `hullq.search.boat_design_field_bridge
#: .make_bounded_canonical_value_lookup`.
lookup_power_engine_count_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({PROPULSION_ENGINE_COUNT_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({PROPULSION_ENGINE_COUNT_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_power_engine_count_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `power_engine_count`
    for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge
    .build_boat_design_configuration_set` -- see that function's docstring
    for the baseline/NamedVariant projection rules.
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (POWER_ENGINE_COUNT_FIELD_PROJECTION_SPEC,)
    )
