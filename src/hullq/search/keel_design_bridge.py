"""BoatDesign/configuration `keel_configuration` eligibility bridge — SLICE-0055.

The criterion-#2 adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (canonical
subject lookup, FieldResolution qualification, baseline/NamedVariant
projection, design-eligibility evaluation) — see that module's docstring for
the mandatory second-criterion abstraction rationale. This module owns only
what is genuinely `keel_configuration`-specific:

    the two BoatDesign field pointers this criterion qualifies
        BoatDesign      /baseline/appendages/keel_type
        NamedVariant    /overrides/appendages/keel_type

    the normative v0.1 BoatDesign keel_type -> Search/PhysicalBoat
    keel_configuration taxonomy mapping
    (specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md §4)

Design-side source is BoatDesign v0.6 `appendages.keel_type`
(`hullq.domain.configuration.KeelType`'s lowercase vocabulary). Search/
PhysicalBoat-side vocabulary is `hullq.domain.physical_boat_claims.
KeelConfiguration`'s upper-case vocabulary. The two are intentionally not
interchangeable (contract §4): only the six explicitly authorized mappings
below are ever applied, and every other BoatDesign `keel_type` value (`full`,
`modified_full`, `long_fin`, `bilge`, `daggerboard`, `swing`, `shoal`,
`other`, `unknown`) has no v0.1 mapping and fails closed -- the shared
bridge's `FieldProjectionSpec.taxonomy_map` mechanism (never string
similarity or ad-hoc inference) enforces this uniformly.

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, or any
mapping beyond the explicit v0.1 table -- adding `LONG_KEEL`/`bilge` or any
other equivalence requires its own reviewed semantic decision (contract §4).
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
    "BOAT_DESIGN_KEEL_TYPE_TO_SEARCH_KEEL_CONFIGURATION",
    "KEEL_CONFIGURATION_FIELD_PROJECTION_SPEC",
    "KEEL_CONFIGURATION_PROJECTION_FIELD",
    "KEEL_TYPE_FIELD_POINTER",
    "KEEL_TYPE_OVERRIDE_FIELD_POINTER",
    "SEARCH_KEEL_CONFIGURATION_VALUES",
    "build_boat_design_keel_configuration_set",
    "compatible_boat_design_ids_for_keel",
    "lookup_keel_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the `CategoricalLeafCriterion` it is evaluated against.
KEEL_CONFIGURATION_PROJECTION_FIELD: Final = "keel_configuration"

#: The exact two bounded field meanings SLICE-0055 Search consumption is
#: allowed to qualify -- see this module's docstring. Never broadened.
KEEL_TYPE_FIELD_POINTER: Final = "/baseline/appendages/keel_type"
KEEL_TYPE_OVERRIDE_FIELD_POINTER: Final = "/overrides/appendages/keel_type"

#: Normative v0.1 mapping table
#: (TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md §4). Every
#: BoatDesign `keel_type` not listed here has no authorized v0.1 mapping.
BOAT_DESIGN_KEEL_TYPE_TO_SEARCH_KEEL_CONFIGURATION: Final[dict[str, str]] = {
    "fin": "FIN",
    "wing": "WING",
    "bulb": "FIN_WITH_BULB",
    "centerboard": "CENTERBOARD",
    "lifting": "LIFTING_KEEL",
    "twin": "TWIN_KEEL",
}

#: The exact accepted public v0.1 `keel_configuration` query values --
#: `LONG_KEEL` and `OTHER` remain valid PhysicalBoat claim vocabulary but are
#: not public v0.1 Search values (contract §4).
SEARCH_KEEL_CONFIGURATION_VALUES: Final[frozenset[str]] = frozenset(
    BOAT_DESIGN_KEEL_TYPE_TO_SEARCH_KEEL_CONFIGURATION.values()
)

#: This criterion's shared-bridge field-projection contract (SLICE-0055 §6).
#: Exported so the mixed native-inventory application funnel can combine it
#: with `hullq.search.draft_max_design_bridge`'s own spec in one query.
KEEL_CONFIGURATION_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=KEEL_CONFIGURATION_PROJECTION_FIELD,
    section_key="appendages",
    field_key="keel_type",
    baseline_pointer=KEEL_TYPE_FIELD_POINTER,
    override_pointer=KEEL_TYPE_OVERRIDE_FIELD_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=BOAT_DESIGN_KEEL_TYPE_TO_SEARCH_KEEL_CONFIGURATION,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0055's `keel_configuration` criterion, hard-bounded
#: to exactly the two field meanings this module's docstring authorizes -- see
#: `hullq.search.boat_design_field_bridge.make_bounded_canonical_value_lookup`.
lookup_keel_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({KEEL_TYPE_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({KEEL_TYPE_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_keel_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `keel_configuration` for *boat_design*.

    *boat_design* is the BOAT_DESIGN_SCHEMA-shaped dict returned by
    `hullq.persistence.identity_readback.fetch_boat_design`. Thin adapter
    over the shared `hullq.search.boat_design_field_bridge.
    build_boat_design_configuration_set` -- see that function's docstring for
    the baseline/NamedVariant projection rules, and this module's docstring
    for the v0.1 taxonomy-mapping fail-closed rule.
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (KEEL_CONFIGURATION_FIELD_PROJECTION_SPEC,)
    )


def compatible_boat_design_ids_for_keel(
    conn: Any, keel_configuration: str, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for `keel_configuration`.

    *keel_configuration* must already be one of `SEARCH_KEEL_CONFIGURATION_VALUES`
    -- never a raw BoatDesign `keel_type` spelling. A `CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA` design-level result is simply not included -- neither
    ever admits a design's PhysicalBoats to the concrete evaluation funnel.
    """
    if keel_configuration not in SEARCH_KEEL_CONFIGURATION_VALUES:
        raise ValueError(
            f"keel_configuration must be one of {sorted(SEARCH_KEEL_CONFIGURATION_VALUES)}; "
            f"got {keel_configuration!r}"
        )
    query = MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(
                field=KEEL_CONFIGURATION_PROJECTION_FIELD, equals=keel_configuration
            ),
        )
    )
    return compatible_boat_design_ids_for_query(
        conn, query, boat_designs, (KEEL_CONFIGURATION_FIELD_PROJECTION_SPEC,)
    )
