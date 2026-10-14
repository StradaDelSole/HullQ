"""BoatDesign/configuration `cockpit_position` eligibility bridge — SLICE-0086.

The sixth criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics.
`cockpit_position` exists only in BOAT_DESIGN_SCHEMA v0.6
(`deck.cockpit_position`) -- v0.5 has no `deck` section at all, so a v0.5
design's `baseline.get("deck")` is simply absent and the shared bridge's
ordinary section/field lookup already yields `MISSING` with no
version-conditional logic needed here (slice: "v0.5 missing/unknown design
stays UNKNOWN" / "older designs remain design UNKNOWN for this facet").

    BoatDesign      /baseline/deck/cockpit_position
    NamedVariant    /overrides/deck/cockpit_position
    BoatDesign      /baseline/deck/cockpit_count
    NamedVariant    /overrides/deck/cockpit_count

Normative mapping (slice "Public accepted candidate facet #6 — cockpit
position"):

    aft      -> AFT
    center   -> CENTER
    forward  -> FORWARD
    multiple -> MULTIPLE
    other, unknown -> no mapping (MISSING)

A confirmed `cockpit_position` is additionally cross-checked against a
separately confirmed `cockpit_count`: `cockpit_count == 0` together with a
confirmed non-unknown position is contradictory (BOAT_DESIGN_SCHEMA.v0.6
itself requires `cockpit_count=0` to pair with `cockpit_position=unknown`,
but this bridge does not rely solely on schema validation of old persisted
payloads -- slice: "avoid relying solely on schema validation of old
persisted payloads") and fails closed to `MISSING`, never a confirmed
positive match. A missing/unqualified `cockpit_count` never blocks an
otherwise independently qualified `cockpit_position`.

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, `helm_type`/
`helm_count`, or any mapping beyond the explicit rules above.
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
    "COCKPIT_POSITION_PROJECTION_FIELD",
    "SEARCH_COCKPIT_POSITION_VALUES",
    "build_boat_design_cockpit_position_set",
    "compatible_boat_design_ids_for_cockpit_position",
    "lookup_cockpit_position_canonical_value",
]

#: The public, opaque projection field name every `CategoricalLeafCriterion`
#: evaluating `cockpit_position` addresses.
COCKPIT_POSITION_PROJECTION_FIELD: Final = "cockpit_position"

#: The exact accepted public v0.1 `cockpit_position` query values (slice
#: normative cockpit semantics). `OTHER` is a valid PhysicalBoat claim token
#: but never a verified public Search category.
SEARCH_COCKPIT_POSITION_VALUES: Final[frozenset[str]] = frozenset(
    {"AFT", "CENTER", "FORWARD", "MULTIPLE"}
)

_COCKPIT_POSITION_FIELD: Final = "_cockpit_position_raw"
_COCKPIT_POSITION_POINTER: Final = "/baseline/deck/cockpit_position"
_COCKPIT_POSITION_OVERRIDE_POINTER: Final = "/overrides/deck/cockpit_position"

_COCKPIT_COUNT_FIELD: Final = "_cockpit_count_raw"
_COCKPIT_COUNT_POINTER: Final = "/baseline/deck/cockpit_count"
_COCKPIT_COUNT_OVERRIDE_POINTER: Final = "/overrides/deck/cockpit_count"

#: Normative v0.1 mapping. Every BOAT_DESIGN_SCHEMA.v0.6 `cockpit_position`
#: not listed here (`other`, `unknown`) has no authorized v0.1 mapping and
#: fails closed to MISSING.
_BOAT_DESIGN_COCKPIT_POSITION_TO_SEARCH: Final[dict[str, str]] = {
    "aft": "AFT",
    "center": "CENTER",
    "forward": "FORWARD",
    "multiple": "MULTIPLE",
}

_COCKPIT_POSITION_SPEC: Final = FieldProjectionSpec(
    projection_field=_COCKPIT_POSITION_FIELD,
    section_key="deck",
    field_key="cockpit_position",
    baseline_pointer=_COCKPIT_POSITION_POINTER,
    override_pointer=_COCKPIT_POSITION_OVERRIDE_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=_BOAT_DESIGN_COCKPIT_POSITION_TO_SEARCH,
)
_COCKPIT_COUNT_SPEC: Final = FieldProjectionSpec(
    projection_field=_COCKPIT_COUNT_FIELD,
    section_key="deck",
    field_key="cockpit_count",
    baseline_pointer=_COCKPIT_COUNT_POINTER,
    override_pointer=_COCKPIT_COUNT_OVERRIDE_POINTER,
    decode=decode_decimal_for_qualification,
    is_numeric=True,
)

_ALL_RAW_SPECS: Final = (_COCKPIT_POSITION_SPEC, _COCKPIT_COUNT_SPEC)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0086's `cockpit_position` criterion,
#: hard-bounded to exactly the two raw field meanings this module's
#: docstring authorizes.
lookup_cockpit_position_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({_COCKPIT_POSITION_POINTER, _COCKPIT_COUNT_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset(
            {_COCKPIT_POSITION_OVERRIDE_POINTER, _COCKPIT_COUNT_OVERRIDE_POINTER}
        ),
    }
)


def _derive_cockpit_position(projection: ConfigurationProjection) -> QualifiedCategoricalValue:
    mapped = projection.get_categorical(_COCKPIT_POSITION_FIELD)
    if mapped.qualification is not ValueQualification.CONFIRMED:
        return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)
    assert mapped.value is not None
    count = projection.get_numeric(_COCKPIT_COUNT_FIELD)
    if count.qualification is ValueQualification.CONFIRMED and count.value == 0:
        # A confirmed non-unknown cockpit position together with a confirmed
        # cockpit_count of zero is contradictory -- never a confirmed
        # positive match.
        return QualifiedCategoricalValue(value=None, qualification=ValueQualification.MISSING)
    return QualifiedCategoricalValue(value=mapped.value, qualification=ValueQualification.CONFIRMED)


def build_boat_design_cockpit_position_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting the derived
    `cockpit_position` for *boat_design*, applying the cockpit-count
    consistency check (this module's docstring).
    """
    raw_set = build_boat_design_configuration_set(conn, boat_design, _ALL_RAW_SPECS)
    derived_configurations = tuple(
        ResolvedConfiguration(
            identity=configuration.identity,
            projection=ConfigurationProjection(
                categorical_values={
                    COCKPIT_POSITION_PROJECTION_FIELD: _derive_cockpit_position(
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


def compatible_boat_design_ids_for_cockpit_position(
    conn: Any, cockpit_position: str, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for
    `cockpit_position`.

    *cockpit_position* must already be one of `SEARCH_COCKPIT_POSITION_VALUES`
    -- never a raw BoatDesign spelling. A `CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA` design-level result is simply not included.
    """
    if cockpit_position not in SEARCH_COCKPIT_POSITION_VALUES:
        raise ValueError(
            f"cockpit_position must be one of {sorted(SEARCH_COCKPIT_POSITION_VALUES)}; "
            f"got {cockpit_position!r}"
        )
    boat_designs = tuple(boat_designs)
    query = MixedAndQuery(
        criteria=(
            CategoricalLeafCriterion(
                field=COCKPIT_POSITION_PROJECTION_FIELD, equals=cockpit_position
            ),
        )
    )
    design_configuration_sets = tuple(
        build_boat_design_cockpit_position_set(conn, bd) for bd in boat_designs
    )
    outcome = run_configuration_query(query, design_configuration_sets)
    return frozenset(evaluation.design_id for evaluation in outcome.confirmed_matches)
