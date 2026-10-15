"""BoatDesign/configuration `hull_material` eligibility bridge — SLICE-0087.

The ninth criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design-eligibility evaluation) -- see that module's docstring for
the mandatory second-criterion abstraction rationale, already applied by
`hullq.search.keel_design_bridge`/`hullq.search.rudder_design_bridge`. This
module owns only what is genuinely `hull_material`-specific:

    the two BoatDesign field pointers this criterion qualifies
        BoatDesign      /baseline/construction/hull_material
        NamedVariant    /overrides/construction/hull_material

    the normative v0.1 BoatDesign hull_material -> Search/PhysicalBoat
    hull_material taxonomy mapping
    (`docs/slices/SLICE-0087-qualified-beam-hull-material-search.md` §"Hull
    material")

Design-side source is BoatDesign v0.5/v0.6 `construction.hull_material`
(lowercase vocabulary: `grp_fiberglass`/`aluminium`/`steel`/`wood`/
`wood_composite`/`carbon`/`other`/`unknown`). Search/PhysicalBoat-side
vocabulary is `hullq.domain.physical_boat_claims.HullMaterial`'s upper-case
seven-value vocabulary, of which only four are ever accepted as a public
Search *filter* value (`SEARCH_HULL_MATERIAL_VALUES` below). The two
vocabularies are intentionally not interchangeable: only the four explicitly
authorized mappings below are ever applied, and every other BoatDesign
`hull_material` value (`wood_composite`, `carbon`, `other`, `unknown`) has no
v0.1 mapping and fails closed -- the shared bridge's
`FieldProjectionSpec.taxonomy_map` mechanism (never string similarity or
ad-hoc inference) enforces this uniformly. In particular `wood_composite` is
NOT the same as `wood`, and `carbon` is NOT silently treated as the more
specific actual-claim `CARBON_COMPOSITE` (slice normative hull-material
semantics).

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, OR groups,
free-text material search, or any mapping beyond the explicit four-row table
-- adding `FERROCEMENT`/`CARBON_COMPOSITE`/`OTHER` as a public filter value,
or mapping `wood_composite`/`carbon`, requires its own reviewed semantic
decision.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    compatible_boat_design_ids_for_query,
    decode_categorical_string_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import DesignConfigurationSet
from hullq.search.criteria import CategoricalLeafCriterion
from hullq.search.query_mixed import MixedAndQuery

__all__ = [
    "BOAT_DESIGN_HULL_MATERIAL_TO_SEARCH_HULL_MATERIAL",
    "HULL_MATERIAL_FIELD_POINTER",
    "HULL_MATERIAL_FIELD_PROJECTION_SPEC",
    "HULL_MATERIAL_OVERRIDE_FIELD_POINTER",
    "HULL_MATERIAL_PROJECTION_FIELD",
    "SEARCH_HULL_MATERIAL_VALUES",
    "build_boat_design_hull_material_configuration_set",
    "compatible_boat_design_ids_for_hull_material",
    "lookup_hull_material_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the `CategoricalLeafCriterion` it is evaluated against.
HULL_MATERIAL_PROJECTION_FIELD: Final = "hull_material"

#: The exact two bounded field meanings SLICE-0087 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
HULL_MATERIAL_FIELD_POINTER: Final = "/baseline/construction/hull_material"
HULL_MATERIAL_OVERRIDE_FIELD_POINTER: Final = "/overrides/construction/hull_material"

#: Normative v0.1 mapping table (slice §"Hull material" table). Every
#: BoatDesign `hull_material` not listed here has no authorized v0.1 mapping.
BOAT_DESIGN_HULL_MATERIAL_TO_SEARCH_HULL_MATERIAL: Final[dict[str, str]] = {
    "grp_fiberglass": "GRP_FIBERGLASS",
    "steel": "STEEL",
    "aluminium": "ALUMINUM",
    "wood": "WOOD",
}

#: The exact accepted public v0.1 `hull_material` query values --
#: `FERROCEMENT`/`CARBON_COMPOSITE`/`OTHER` remain valid PhysicalBoat claim
#: vocabulary but are not public v0.1 Search values in this slice.
SEARCH_HULL_MATERIAL_VALUES: Final[frozenset[str]] = frozenset(
    BOAT_DESIGN_HULL_MATERIAL_TO_SEARCH_HULL_MATERIAL.values()
)

#: This criterion's shared-bridge field-projection contract (SLICE-0055 §6).
#: Exported so the mixed native-inventory application funnel can combine it
#: with every other active criterion's own spec in one query.
HULL_MATERIAL_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=HULL_MATERIAL_PROJECTION_FIELD,
    section_key="construction",
    field_key="hull_material",
    baseline_pointer=HULL_MATERIAL_FIELD_POINTER,
    override_pointer=HULL_MATERIAL_OVERRIDE_FIELD_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=BOAT_DESIGN_HULL_MATERIAL_TO_SEARCH_HULL_MATERIAL,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0087's `hull_material` criterion, hard-bounded to
#: exactly the two field meanings this module's docstring authorizes -- see
#: `hullq.search.boat_design_field_bridge.make_bounded_canonical_value_lookup`.
lookup_hull_material_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({HULL_MATERIAL_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({HULL_MATERIAL_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_hull_material_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `hull_material` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge.
    build_boat_design_configuration_set` -- see that function's docstring for
    the baseline/NamedVariant projection rules, and this module's docstring
    for the v0.1 taxonomy-mapping fail-closed rule.
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (HULL_MATERIAL_FIELD_PROJECTION_SPEC,)
    )


def compatible_boat_design_ids_for_hull_material(
    conn: Any, hull_material: str, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for `hull_material`.

    *hull_material* must already be one of `SEARCH_HULL_MATERIAL_VALUES` --
    never a raw BoatDesign `hull_material` spelling. A `CONFIRMED_NON_MATCH`
    or `INSUFFICIENT_DATA` design-level result is simply not included --
    neither ever admits a design's PhysicalBoats to the concrete evaluation
    funnel.
    """
    if hull_material not in SEARCH_HULL_MATERIAL_VALUES:
        raise ValueError(
            f"hull_material must be one of {sorted(SEARCH_HULL_MATERIAL_VALUES)}; "
            f"got {hull_material!r}"
        )
    query = MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(field=HULL_MATERIAL_PROJECTION_FIELD, equals=hull_material),
        )
    )
    return compatible_boat_design_ids_for_query(
        conn, query, boat_designs, (HULL_MATERIAL_FIELD_PROJECTION_SPEC,)
    )
