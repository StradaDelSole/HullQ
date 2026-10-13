"""BoatDesign/configuration `rudder_configuration` eligibility bridge — SLICE-0085.

The fourth criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics. Unlike
`draft_max`/`keel_configuration`/`loa` (each a single qualified field under a
single taxonomy/decode rule), `rudder_configuration` requires a
**generation-aware bounded adapter** (slice Shared-foundation constraint 1):
a genuine v0.5 BoatDesign records rudder facts as one flat
`configuration.rudder_type` enum, while a genuine v0.6 BoatDesign decomposes
them into three independent `appendages.rudder_support` /
`rudder_position` / `rudder_count` fields. This module projects every
contributing raw sub-field through the ordinary shared bridge (so each one
gets its own FieldResolution qualification, never bypassed), then derives
the single flattened public `rudder_configuration` category from whichever
generation's sub-fields are actually populated -- conservatively, per the
exact mapping rules below. A design carrying fields from *neither* generation
(or an ambiguous/conflicting combination) yields `MISSING`, never a guess.

## v0.5 mapping (`baseline.configuration.rudder_type` + `.rudder_count`)

    skeg_hung, partial_skeg -> SKEG_HUNG   (both definitionally skeg-supported)
    transom_hung            -> TRANSOM_HUNG
    spade                   -> SPADE
    twin                    -> TWIN, but ONLY when the design's own
                               `rudder_count` is not confirmed to a value
                               other than 2 -- an internally inconsistent
                               v0.5 payload (mirrors
                               `docs/engineering/BOAT_DESIGN_V05_TO_V06_MAPPING.md`
                               §3.2's identical `RudderCountMappingConflict`
                               conservatism) is never silently resolved by
                               picking one side.
    keel_hung, other, unknown -> no mapping (MISSING)

## v0.6 mapping (`baseline.appendages.rudder_support`/`rudder_position`/`rudder_count`)

Each contributing field is independently qualified; a flattened category is
derived only when exactly one of the following three independent conditions
is confirmed TRUE for this configuration -- `rudder_support=free` alone
never proves `SPADE` (slice normative rudder semantics: "no other bare
property automatically proves that compound label"), so **v0.6 never derives
`SPADE`** at all, only via the v0.5 path above:

    rudder_support == "skeg"                                -> SKEG_HUNG
    rudder_position == "transom" AND rudder_support == "transom" -> TRANSOM_HUNG
    rudder_count == 2                                        -> TWIN

If more than one of these three conditions is independently confirmed at
once (e.g. `rudder_support=skeg` AND `rudder_count=2`), the flattened
category is genuinely ambiguous -- a single boat cannot be claimed as two
different coarse enum values -- and this module fails closed to `MISSING`
rather than guessing a favorite (slice normative rudder semantics: "Any
unresolved overlap between multiple possible coarse enum labels ... ->
INSUFFICIENT_DATA for that flattened category instead of guessing one").

Neither generation's derivation ever infers `rudder_balance`, which stays
independent per slice normative rudder semantics.

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, or any
mapping beyond the explicit rules above -- a different combination requires
its own reviewed semantic decision.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Final

from hullq.domain.provenance import SubjectKind
from hullq.search.boat_design_field_bridge import (
    FieldProjectionSpec,
    build_boat_design_configuration_set,
    decode_categorical_string_for_qualification,
    decode_decimal_for_qualification,
    make_bounded_canonical_value_lookup,
)
from hullq.search.configuration import (
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import run_configuration_query
from hullq.search.criteria import CategoricalLeafCriterion
from hullq.search.query_mixed import MixedAndQuery
from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedCategoricalValue

__all__ = [
    "RUDDER_CONFIGURATION_PROJECTION_FIELD",
    "SEARCH_RUDDER_CONFIGURATION_VALUES",
    "build_boat_design_rudder_configuration_set",
    "compatible_boat_design_ids_for_rudder",
    "lookup_rudder_canonical_value",
]

#: The public, opaque projection field name the derived flattened category is
#: exposed as -- the same name every `CategoricalLeafCriterion` evaluating
#: `rudder_configuration` addresses.
RUDDER_CONFIGURATION_PROJECTION_FIELD: Final = "rudder_configuration"

#: The exact accepted public v0.1 `rudder_configuration` query values (slice
#: normative rudder semantics). `OTHER` is a valid PhysicalBoat claim token
#: but never a verified public Search category.
SEARCH_RUDDER_CONFIGURATION_VALUES: Final[frozenset[str]] = frozenset(
    {"SKEG_HUNG", "TRANSOM_HUNG", "SPADE", "TWIN"}
)

# ---------------------------------------------------------------------------
# v0.5 raw sub-fields: baseline.configuration.rudder_type / .rudder_count
# ---------------------------------------------------------------------------

_RUDDER_TYPE_V05_FIELD: Final = "_rudder_type_v05"
_RUDDER_TYPE_V05_POINTER: Final = "/baseline/configuration/rudder_type"
_RUDDER_TYPE_V05_OVERRIDE_POINTER: Final = "/overrides/configuration/rudder_type"

_RUDDER_COUNT_V05_FIELD: Final = "_rudder_count_v05"
_RUDDER_COUNT_V05_POINTER: Final = "/baseline/configuration/rudder_count"
_RUDDER_COUNT_V05_OVERRIDE_POINTER: Final = "/overrides/configuration/rudder_count"

# ---------------------------------------------------------------------------
# v0.6 raw sub-fields: baseline.appendages.rudder_support / .rudder_position / .rudder_count
# ---------------------------------------------------------------------------

_RUDDER_SUPPORT_V06_FIELD: Final = "_rudder_support_v06"
_RUDDER_SUPPORT_V06_POINTER: Final = "/baseline/appendages/rudder_support"
_RUDDER_SUPPORT_V06_OVERRIDE_POINTER: Final = "/overrides/appendages/rudder_support"

_RUDDER_POSITION_V06_FIELD: Final = "_rudder_position_v06"
_RUDDER_POSITION_V06_POINTER: Final = "/baseline/appendages/rudder_position"
_RUDDER_POSITION_V06_OVERRIDE_POINTER: Final = "/overrides/appendages/rudder_position"

_RUDDER_COUNT_V06_FIELD: Final = "_rudder_count_v06"
_RUDDER_COUNT_V06_POINTER: Final = "/baseline/appendages/rudder_count"
_RUDDER_COUNT_V06_OVERRIDE_POINTER: Final = "/overrides/appendages/rudder_count"

#: Identity taxonomy maps covering every legitimate BOAT_DESIGN_SCHEMA enum
#: token for each raw sub-field, deliberately EXCLUDING the schema's own
#: `"unknown"` sentinel. Without this, a raw `decode_categorical_string_for_
#: qualification` value flows straight through `_qualify_and_map` to
#: `QualifiedCategoricalValue` with no taxonomy_map to intercept it -- and
#: `QualifiedCategoricalValue.__post_init__` hard-rejects (`ValueError`) a
#: `CONFIRMED` value equal to the reserved sentinel `"unknown"`
#: (`hullq.search.values.RESERVED_CATEGORICAL_SENTINELS`), since confirming
#: "the value is unknown" is a contradiction in terms. Every other
#: `FieldProjectionSpec` in this codebase that decodes an unmapped raw
#: schema enum (draft_max, loa) is numeric and therefore immune; every
#: categorical one (keel) already had a taxonomy_map for a different reason
#: (the Search-vocabulary remap) that happened to also absorb "unknown" as a
#: side effect. This module's own derivation logic (`_derive_rudder_
#: configuration`) already handles every *other* legitimate token
#: (`keel_hung`/`other`/`free`/etc.) correctly as a fail-closed MISSING --
#: only the sentinel itself needs interception before construction.
_RUDDER_TYPE_V05_IDENTITY_MAP: Final[dict[str, str]] = {
    value: value
    for value in (
        "keel_hung",
        "skeg_hung",
        "partial_skeg",
        "spade",
        "transom_hung",
        "twin",
        "other",
    )
}
_RUDDER_SUPPORT_V06_IDENTITY_MAP: Final[dict[str, str]] = {
    value: value for value in ("keel", "skeg", "free", "transom", "other")
}
_RUDDER_POSITION_V06_IDENTITY_MAP: Final[dict[str, str]] = {
    value: value for value in ("transom", "underhull", "other")
}

_RUDDER_TYPE_V05_SPEC: Final = FieldProjectionSpec(
    projection_field=_RUDDER_TYPE_V05_FIELD,
    section_key="configuration",
    field_key="rudder_type",
    baseline_pointer=_RUDDER_TYPE_V05_POINTER,
    override_pointer=_RUDDER_TYPE_V05_OVERRIDE_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=_RUDDER_TYPE_V05_IDENTITY_MAP,
)
_RUDDER_COUNT_V05_SPEC: Final = FieldProjectionSpec(
    projection_field=_RUDDER_COUNT_V05_FIELD,
    section_key="configuration",
    field_key="rudder_count",
    baseline_pointer=_RUDDER_COUNT_V05_POINTER,
    override_pointer=_RUDDER_COUNT_V05_OVERRIDE_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)
_RUDDER_SUPPORT_V06_SPEC: Final = FieldProjectionSpec(
    projection_field=_RUDDER_SUPPORT_V06_FIELD,
    section_key="appendages",
    field_key="rudder_support",
    baseline_pointer=_RUDDER_SUPPORT_V06_POINTER,
    override_pointer=_RUDDER_SUPPORT_V06_OVERRIDE_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=_RUDDER_SUPPORT_V06_IDENTITY_MAP,
)
_RUDDER_POSITION_V06_SPEC: Final = FieldProjectionSpec(
    projection_field=_RUDDER_POSITION_V06_FIELD,
    section_key="appendages",
    field_key="rudder_position",
    baseline_pointer=_RUDDER_POSITION_V06_POINTER,
    override_pointer=_RUDDER_POSITION_V06_OVERRIDE_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=_RUDDER_POSITION_V06_IDENTITY_MAP,
)
_RUDDER_COUNT_V06_SPEC: Final = FieldProjectionSpec(
    projection_field=_RUDDER_COUNT_V06_FIELD,
    section_key="appendages",
    field_key="rudder_count",
    baseline_pointer=_RUDDER_COUNT_V06_POINTER,
    override_pointer=_RUDDER_COUNT_V06_OVERRIDE_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

_ALL_RAW_SPECS: Final = (
    _RUDDER_TYPE_V05_SPEC,
    _RUDDER_COUNT_V05_SPEC,
    _RUDDER_SUPPORT_V06_SPEC,
    _RUDDER_POSITION_V06_SPEC,
    _RUDDER_COUNT_V06_SPEC,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0085's `rudder_configuration` criterion,
#: hard-bounded to exactly the five raw field meanings this module's
#: docstring authorizes.
lookup_rudder_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset(
            {
                _RUDDER_TYPE_V05_POINTER,
                _RUDDER_COUNT_V05_POINTER,
                _RUDDER_SUPPORT_V06_POINTER,
                _RUDDER_POSITION_V06_POINTER,
                _RUDDER_COUNT_V06_POINTER,
            }
        ),
        SubjectKind.NAMED_VARIANT: frozenset(
            {
                _RUDDER_TYPE_V05_OVERRIDE_POINTER,
                _RUDDER_COUNT_V05_OVERRIDE_POINTER,
                _RUDDER_SUPPORT_V06_OVERRIDE_POINTER,
                _RUDDER_POSITION_V06_OVERRIDE_POINTER,
                _RUDDER_COUNT_V06_OVERRIDE_POINTER,
            }
        ),
    }
)

#: v0.5 `rudder_type` values that unconditionally map (contract conservative
#: table) -- `twin` is handled separately because it additionally depends on
#: `rudder_count` agreement.
_V05_UNCONDITIONAL_MAP: Final[dict[str, str]] = {
    "skeg_hung": "SKEG_HUNG",
    "partial_skeg": "SKEG_HUNG",
    "transom_hung": "TRANSOM_HUNG",
    "spade": "SPADE",
}


def _derive_rudder_configuration(projection: ConfigurationProjection) -> QualifiedCategoricalValue:
    """Derive the flattened public `rudder_configuration` value for one
    resolved configuration's raw sub-field projection -- see this module's
    docstring for the exact conservative v0.5/v0.6 rules.
    """
    v05_type = projection.get_categorical(_RUDDER_TYPE_V05_FIELD)
    if v05_type.qualification is ValueQualification.CONFIRMED:
        raw = v05_type.value
        assert raw is not None
        mapped = _V05_UNCONDITIONAL_MAP.get(raw)
        if mapped is not None:
            return QualifiedCategoricalValue(
                value=mapped, qualification=ValueQualification.CONFIRMED
            )
        if raw == "twin":
            v05_count = projection.get_numeric(_RUDDER_COUNT_V05_FIELD)
            if v05_count.qualification is ValueQualification.CONFIRMED and v05_count.value != 2:
                # Internally inconsistent v0.5 payload (rudder_type=twin but
                # a confirmed count other than 2) -- never silently resolved
                # by picking one side.
                return QualifiedCategoricalValue(
                    value=None, qualification=ValueQualification.MISSING
                )
            return QualifiedCategoricalValue(
                value="TWIN", qualification=ValueQualification.CONFIRMED
            )
        # keel_hung/other/unknown: no authorized v0.1 mapping.
        return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)

    # v0.6 path -- independent sub-fields, each may support at most one
    # candidate category; more than one simultaneously confirmed candidate
    # is a genuine ambiguous overlap, never resolved by guessing.
    support = projection.get_categorical(_RUDDER_SUPPORT_V06_FIELD)
    position = projection.get_categorical(_RUDDER_POSITION_V06_FIELD)
    count = projection.get_numeric(_RUDDER_COUNT_V06_FIELD)

    candidates: set[str] = set()
    if support.qualification is ValueQualification.CONFIRMED and support.value == "skeg":
        candidates.add("SKEG_HUNG")
    if (
        position.qualification is ValueQualification.CONFIRMED
        and position.value == "transom"
        and support.qualification is ValueQualification.CONFIRMED
        and support.value == "transom"
    ):
        candidates.add("TRANSOM_HUNG")
    if count.qualification is ValueQualification.CONFIRMED and count.value == 2:
        candidates.add("TWIN")

    if len(candidates) == 1:
        return QualifiedCategoricalValue(
            value=next(iter(candidates)), qualification=ValueQualification.CONFIRMED
        )
    return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)


def build_boat_design_rudder_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting the derived
    `rudder_configuration` for *boat_design*.

    Projects every raw v0.5/v0.6 sub-field through the ordinary shared
    bridge (so each keeps its own independent FieldResolution
    qualification), then replaces each resulting configuration's projection
    with just the one derived `rudder_configuration` categorical field --
    the raw sub-fields are an internal derivation detail, never exposed to a
    `CategoricalLeafCriterion` directly.
    """
    raw_set = build_boat_design_configuration_set(conn, boat_design, _ALL_RAW_SPECS)
    derived_configurations = tuple(
        ResolvedConfiguration(
            identity=configuration.identity,
            projection=ConfigurationProjection(
                categorical_values={
                    RUDDER_CONFIGURATION_PROJECTION_FIELD: _derive_rudder_configuration(
                        configuration.projection
                    )
                }
            ),
        )
        for configuration in raw_set.configurations
    )
    return DesignConfigurationSet(
        design_id=raw_set.design_id,
        configurations=derived_configurations,
        configuration_space_complete=raw_set.configuration_space_complete,
        option_constraints=raw_set.option_constraints,
        variant_constraints=raw_set.variant_constraints,
        is_fixture=raw_set.is_fixture,
    )


def compatible_boat_design_ids_for_rudder(
    conn: Any, rudder_configuration: str, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for
    `rudder_configuration`.

    *rudder_configuration* must already be one of
    `SEARCH_RUDDER_CONFIGURATION_VALUES` -- never a raw BoatDesign field
    spelling. A `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` design-level
    result is simply not included.
    """
    if rudder_configuration not in SEARCH_RUDDER_CONFIGURATION_VALUES:
        raise ValueError(
            f"rudder_configuration must be one of {sorted(SEARCH_RUDDER_CONFIGURATION_VALUES)}; "
            f"got {rudder_configuration!r}"
        )
    boat_designs = tuple(boat_designs)
    query = MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(
                field=RUDDER_CONFIGURATION_PROJECTION_FIELD, equals=rudder_configuration
            ),
        )
    )
    design_configuration_sets = tuple(
        build_boat_design_rudder_configuration_set(conn, bd) for bd in boat_designs
    )
    outcome = run_configuration_query(query, design_configuration_sets)
    return frozenset(evaluation.design_id for evaluation in outcome.confirmed_matches)
