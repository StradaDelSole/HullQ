"""BoatDesign/configuration `power_drive_configuration` eligibility bridge — SLICE-0093.

The Power-domain criterion-#1 adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design eligibility) — see that module's docstring for the
mandatory second-criterion abstraction rationale this bridge reuses
unchanged. This module owns only what is genuinely
`power_drive_configuration`-specific:

    the two BoatDesign field pointers this criterion qualifies
        BoatDesign      /baseline/propulsion/drive_type
        NamedVariant    /overrides/propulsion/drive_type

    the normative v0.1 BoatDesign drive_type -> Search/PhysicalBoat
    power_drive_configuration taxonomy mapping
    (specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md,
    "Repository-discovered schema limitation")

Design-side source is BoatDesign v0.6 `propulsion.drive_type`
(`specs/BOAT_DESIGN_SCHEMA.v0.6.json` `$defs.propulsion_shape.drive_type`:
`shaft`/`saildrive`/`outboard`/`other`/`unknown`). Only `shaft` and
`outboard` have an authorized v0.1 mapping to a Power Search token
(`SHAFT`/`OUTBOARD`) -- `saildrive`/`other`/`unknown` have no v0.1 mapping
and fail closed via the shared bridge's `FieldProjectionSpec.taxonomy_map`
mechanism (never string similarity or ad-hoc inference). `STERNDRIVE`/`POD`/
`WATERJET` are therefore structurally **unavailable** from this design-side
bridge -- they are never derivable from v0.6's generic `other` token, and a
caller must report them `INSUFFICIENT_DATA` rather than invent a v0.7
migration (contract: "No v0.7 BoatDesign schema/migration is granted by this
criterion").

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, engine
count/make/model, energy source, or any mapping beyond the explicit v0.1
table.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    decode_categorical_string_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import DesignConfigurationSet

__all__ = [
    "BOAT_DESIGN_DRIVE_TYPE_TO_SEARCH_POWER_DRIVE",
    "POWER_DRIVE_CONFIGURATION_FIELD_PROJECTION_SPEC",
    "POWER_DRIVE_CONFIGURATION_PROJECTION_FIELD",
    "PROPULSION_DRIVE_TYPE_FIELD_POINTER",
    "PROPULSION_DRIVE_TYPE_OVERRIDE_FIELD_POINTER",
    "build_boat_design_power_drive_configuration_set",
    "lookup_power_drive_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the `CategoricalLeafCriterion` it is evaluated against.
POWER_DRIVE_CONFIGURATION_PROJECTION_FIELD: Final = "power_drive_configuration"

#: The exact two bounded field meanings SLICE-0093 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
PROPULSION_DRIVE_TYPE_FIELD_POINTER: Final = "/baseline/propulsion/drive_type"
PROPULSION_DRIVE_TYPE_OVERRIDE_FIELD_POINTER: Final = "/overrides/propulsion/drive_type"

#: Normative v0.1 mapping table
#: (`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`). Every
#: BoatDesign `drive_type` not listed here (`saildrive`, `other`, `unknown`)
#: has no authorized v0.1 mapping and fails closed to MISSING.
BOAT_DESIGN_DRIVE_TYPE_TO_SEARCH_POWER_DRIVE: Final[dict[str, str]] = {
    "shaft": "SHAFT",
    "outboard": "OUTBOARD",
}

#: This criterion's shared-bridge field-projection contract.
POWER_DRIVE_CONFIGURATION_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=POWER_DRIVE_CONFIGURATION_PROJECTION_FIELD,
    section_key="propulsion",
    field_key="drive_type",
    baseline_pointer=PROPULSION_DRIVE_TYPE_FIELD_POINTER,
    override_pointer=PROPULSION_DRIVE_TYPE_OVERRIDE_FIELD_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=BOAT_DESIGN_DRIVE_TYPE_TO_SEARCH_POWER_DRIVE,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0093's `power_drive_configuration` criterion,
#: hard-bounded to exactly the two field meanings this module's docstring
#: authorizes -- see `hullq.search.boat_design_field_bridge
#: .make_bounded_canonical_value_lookup`.
lookup_power_drive_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({PROPULSION_DRIVE_TYPE_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({PROPULSION_DRIVE_TYPE_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_power_drive_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only
    `power_drive_configuration` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge
    .build_boat_design_configuration_set` -- see that function's docstring
    for the baseline/NamedVariant projection rules, and this module's
    docstring for the v0.1 taxonomy-mapping fail-closed rule.
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (POWER_DRIVE_CONFIGURATION_FIELD_PROJECTION_SPEC,)
    )
