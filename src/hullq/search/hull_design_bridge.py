"""BoatDesign/configuration `hull_configuration` eligibility bridge — SLICE-0086.

The fifth criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics (see that
module's docstring for the mandatory second-criterion abstraction
rationale, already applied by `hullq.search.keel_design_bridge`/
`hullq.search.rudder_design_bridge`). Unlike `keel_configuration` (a single
qualified field under a single taxonomy/decode rule), `hull_configuration`
requires one additional cross-field consistency check: BOTH BoatDesign v0.5
and v0.6 carry `configuration.hull_configuration` AND `configuration.
hull_count` at the identical pointer (slice normative hull-form semantics:
"v0.5: /baseline/configuration/hull_configuration, NamedVariant /overrides/
configuration/hull_configuration; v0.6 same pointers"), and the two fields
MUST agree when both are independently qualified -- a design confirmed
`catamaran` with a confirmed `hull_count` other than 2 is an internally
inconsistent payload and MUST NOT produce a positive match (slice normative
hull-form semantics: "`hull_count` where separately qualified and
incompatible ... MUST fail closed, never prove a contradictory category").
A design confirmed only on `hull_configuration`, with `hull_count` itself
unqualified/missing, is NOT penalized -- `hull_count` is never fabricated as
mandatory evidence (same slice text: "Missing/unknown count does not
fabricate count and does not silently reject an otherwise independently
fully qualified hull form").

## Normative v0.1 mapping

    monohull  -> MONOHULL   (expects hull_count == 1 when hull_count is itself qualified)
    catamaran -> CATAMARAN  (expects hull_count == 2 when hull_count is itself qualified)
    trimaran  -> TRIMARAN   (expects hull_count == 3 when hull_count is itself qualified)
    other, unknown -> no mapping (MISSING)

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, or any
mapping beyond the explicit table above -- a different combination requires
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
    "HULL_CONFIGURATION_PROJECTION_FIELD",
    "SEARCH_HULL_CONFIGURATION_VALUES",
    "build_boat_design_hull_configuration_set",
    "compatible_boat_design_ids_for_hull_configuration",
    "lookup_hull_configuration_canonical_value",
]

#: The public, opaque projection field name the derived (count-checked)
#: category is exposed as.
HULL_CONFIGURATION_PROJECTION_FIELD: Final = "hull_configuration"

#: The exact accepted public v0.1 `hull_configuration` query values (slice
#: normative hull-form semantics). `OTHER` is a valid PhysicalBoat claim
#: token but never a verified public Search category.
SEARCH_HULL_CONFIGURATION_VALUES: Final[frozenset[str]] = frozenset(
    {"MONOHULL", "CATAMARAN", "TRIMARAN"}
)

# ---------------------------------------------------------------------------
# Raw sub-fields: baseline.configuration.hull_configuration / .hull_count --
# the identical pointer pair for both v0.5 and v0.6 (this module's docstring).
# ---------------------------------------------------------------------------

_HULL_CONFIGURATION_FIELD: Final = "_hull_configuration_raw"
HULL_CONFIGURATION_FIELD_POINTER: Final = "/baseline/configuration/hull_configuration"
HULL_CONFIGURATION_OVERRIDE_FIELD_POINTER: Final = "/overrides/configuration/hull_configuration"

_HULL_COUNT_FIELD: Final = "_hull_count_raw"
_HULL_COUNT_POINTER: Final = "/baseline/configuration/hull_count"
_HULL_COUNT_OVERRIDE_POINTER: Final = "/overrides/configuration/hull_count"

#: Identity taxonomy map covering every legitimate BOAT_DESIGN_SCHEMA
#: `hull_configuration` enum token, deliberately EXCLUDING `"unknown"` (see
#: `hullq.search.rudder_design_bridge`'s identical rationale: a raw decoded
#: value with no taxonomy_map entry fails closed to MISSING via the shared
#: bridge's `_qualify_and_map`, but the reserved sentinel "unknown" must
#: never reach `QualifiedCategoricalValue` construction at all).
_HULL_CONFIGURATION_TO_SEARCH: Final[dict[str, str]] = {
    "monohull": "MONOHULL",
    "catamaran": "CATAMARAN",
    "trimaran": "TRIMARAN",
}

#: Expected `hull_count` for each mapped category -- the cross-field
#: consistency check this module's docstring requires.
_EXPECTED_HULL_COUNT: Final[dict[str, int]] = {"MONOHULL": 1, "CATAMARAN": 2, "TRIMARAN": 3}

_HULL_CONFIGURATION_SPEC: Final = FieldProjectionSpec(
    projection_field=_HULL_CONFIGURATION_FIELD,
    section_key="configuration",
    field_key="hull_configuration",
    baseline_pointer=HULL_CONFIGURATION_FIELD_POINTER,
    override_pointer=HULL_CONFIGURATION_OVERRIDE_FIELD_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=_HULL_CONFIGURATION_TO_SEARCH,
)
_HULL_COUNT_SPEC: Final = FieldProjectionSpec(
    projection_field=_HULL_COUNT_FIELD,
    section_key="configuration",
    field_key="hull_count",
    baseline_pointer=_HULL_COUNT_POINTER,
    override_pointer=_HULL_COUNT_OVERRIDE_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

_ALL_RAW_SPECS: Final = (_HULL_CONFIGURATION_SPEC, _HULL_COUNT_SPEC)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0086's `hull_configuration` criterion,
#: hard-bounded to exactly the two raw field meanings this module's
#: docstring authorizes.
lookup_hull_configuration_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({HULL_CONFIGURATION_FIELD_POINTER, _HULL_COUNT_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset(
            {HULL_CONFIGURATION_OVERRIDE_FIELD_POINTER, _HULL_COUNT_OVERRIDE_POINTER}
        ),
    }
)


def _derive_hull_configuration(projection: ConfigurationProjection) -> QualifiedCategoricalValue:
    """Derive the (count-checked) public `hull_configuration` value for one
    resolved configuration's raw sub-field projection -- see this module's
    docstring for the exact conservative rule.
    """
    mapped = projection.get_categorical(_HULL_CONFIGURATION_FIELD)
    if mapped.qualification is not ValueQualification.CONFIRMED:
        return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)
    assert mapped.value is not None
    expected_count = _EXPECTED_HULL_COUNT[mapped.value]

    count = projection.get_numeric(_HULL_COUNT_FIELD)
    if count.qualification is ValueQualification.CONFIRMED and count.value != expected_count:
        # Internally inconsistent payload (confirmed hull_configuration
        # contradicted by a confirmed, incompatible hull_count) -- never
        # silently resolved by picking one side.
        return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)
    return mapped


def build_boat_design_hull_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting the derived (count-
    checked) `hull_configuration` for *boat_design*.

    Projects both raw sub-fields through the ordinary shared bridge (so each
    keeps its own independent FieldResolution qualification), then replaces
    each resulting configuration's projection with just the one derived
    `hull_configuration` categorical field -- `hull_count` is an internal
    derivation detail, never exposed to a `CategoricalLeafCriterion`
    directly.
    """
    raw_set = build_boat_design_configuration_set(conn, boat_design, _ALL_RAW_SPECS)
    derived_configurations = tuple(
        ResolvedConfiguration(
            identity=configuration.identity,
            projection=ConfigurationProjection(
                categorical_values={
                    HULL_CONFIGURATION_PROJECTION_FIELD: _derive_hull_configuration(
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


def compatible_boat_design_ids_for_hull_configuration(
    conn: Any, hull_configuration: str, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for
    `hull_configuration`.

    *hull_configuration* must already be one of
    `SEARCH_HULL_CONFIGURATION_VALUES` -- never a raw BoatDesign
    `hull_configuration` spelling. A `CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA` design-level result is simply not included.
    """
    if hull_configuration not in SEARCH_HULL_CONFIGURATION_VALUES:
        raise ValueError(
            f"hull_configuration must be one of {sorted(SEARCH_HULL_CONFIGURATION_VALUES)}; "
            f"got {hull_configuration!r}"
        )
    boat_designs = tuple(boat_designs)
    query = MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(
                field=HULL_CONFIGURATION_PROJECTION_FIELD, equals=hull_configuration
            ),
        )
    )
    design_configuration_sets = tuple(
        build_boat_design_hull_configuration_set(conn, bd) for bd in boat_designs
    )
    outcome = run_configuration_query(query, design_configuration_sets)
    return frozenset(evaluation.design_id for evaluation in outcome.confirmed_matches)
