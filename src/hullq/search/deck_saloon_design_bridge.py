"""BoatDesign/configuration `deck_saloon` eligibility bridge — SLICE-0086.

The seventh criterion adapter over the shared
`hullq.search.boat_design_field_bridge` production mechanics — the simplest
of the three SLICE-0086 facets: a single qualified field under a single
taxonomy-mapping rule, mirroring `hullq.search.keel_design_bridge`'s shape
exactly. `deck_saloon` exists only in BOAT_DESIGN_SCHEMA v0.6
(`deck.deck_saloon`); v0.5 has no `deck` section at all, so a v0.5 design's
`baseline.get("deck")` is simply absent and the shared bridge's ordinary
section/field lookup already yields `MISSING` with no version-conditional
logic needed here (slice: "v0.5 missing/unknown design stays UNKNOWN").

    BoatDesign      /baseline/deck/deck_saloon
    NamedVariant    /overrides/deck/deck_saloon

Normative mapping (slice "Public accepted candidate facet #7 — deck
saloon / pilothouse"):

    deck_saloon -> DECK_SALOON
    pilothouse  -> PILOTHOUSE
    none, unknown -> no mapping (MISSING)

`none` is deliberately excluded from the taxonomy map (not mapped to a
Search-side "NONE" sentinel): the accepted public vocabulary for this
criterion is `DECK_SALOON`/`PILOTHOUSE` only (a public `NONE` filter is
explicitly deferred), and every other categorical bridge in this codebase
(`keel_design_bridge`) follows the identical "unmapped raw value -> MISSING"
rule for a legitimate-but-unsupported-as-a-search-value raw token, never a
bespoke non-match sentinel. `DECK_SALOON` and `PILOTHOUSE` are never merged
or treated as entailing one another.

Does not implement: BuyerRequirements, PREFER/DONT_CARE, ranking, a public
`NONE` filter, or any mapping beyond the explicit rules above.
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
    "BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON",
    "DECK_SALOON_FIELD_POINTER",
    "DECK_SALOON_FIELD_PROJECTION_SPEC",
    "DECK_SALOON_OVERRIDE_FIELD_POINTER",
    "DECK_SALOON_PROJECTION_FIELD",
    "SEARCH_DECK_SALOON_VALUES",
    "build_boat_design_deck_saloon_configuration_set",
    "compatible_boat_design_ids_for_deck_saloon",
    "lookup_deck_saloon_canonical_value",
]

#: Opaque projection field name shared by every `ResolvedConfiguration` this
#: bridge builds and the `CategoricalLeafCriterion` it is evaluated against.
DECK_SALOON_PROJECTION_FIELD: Final = "deck_saloon"

#: The exact bounded field meaning SLICE-0086 Search consumption is allowed
#: to qualify for this criterion.
DECK_SALOON_FIELD_POINTER: Final = "/baseline/deck/deck_saloon"
DECK_SALOON_OVERRIDE_FIELD_POINTER: Final = "/overrides/deck/deck_saloon"

#: Normative v0.1 mapping. `none`/`unknown` have no authorized v0.1 mapping
#: and fail closed to MISSING (this module's docstring).
BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON: Final[dict[str, str]] = {
    "deck_saloon": "DECK_SALOON",
    "pilothouse": "PILOTHOUSE",
}

#: The exact accepted public v0.1 `deck_saloon` query values.
SEARCH_DECK_SALOON_VALUES: Final[frozenset[str]] = frozenset(
    BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON.values()
)

#: This criterion's shared-bridge field-projection contract.
DECK_SALOON_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=DECK_SALOON_PROJECTION_FIELD,
    section_key="deck",
    field_key="deck_saloon",
    baseline_pointer=DECK_SALOON_FIELD_POINTER,
    override_pointer=DECK_SALOON_OVERRIDE_FIELD_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON,
)

#: The only accepted `hullq.persistence.field_resolution.FetchCanonicalValue`
#: implementation for SLICE-0086's `deck_saloon` criterion, hard-bounded to
#: exactly the one field meaning this module's docstring authorizes.
lookup_deck_saloon_canonical_value = make_bounded_canonical_value_lookup(
    {
        SubjectKind.BOAT_DESIGN: frozenset({DECK_SALOON_FIELD_POINTER}),
        SubjectKind.NAMED_VARIANT: frozenset({DECK_SALOON_OVERRIDE_FIELD_POINTER}),
    }
)


def build_boat_design_deck_saloon_configuration_set(
    conn: Any, boat_design: Mapping[str, Any]
) -> DesignConfigurationSet:
    """Build a `DesignConfigurationSet` projecting only `deck_saloon` for
    *boat_design*. Thin adapter over the shared
    `hullq.search.boat_design_field_bridge.build_boat_design_configuration_set`.
    """
    return build_boat_design_configuration_set(
        conn, boat_design, (DECK_SALOON_FIELD_PROJECTION_SPEC,)
    )


def compatible_boat_design_ids_for_deck_saloon(
    conn: Any, deck_saloon: str, boat_designs: Iterable[Mapping[str, Any]]
) -> frozenset[str]:
    """Return the `design_id`s that are a design-level `CONFIRMED_MATCH` for `deck_saloon`.

    *deck_saloon* must already be one of `SEARCH_DECK_SALOON_VALUES` -- never
    a raw BoatDesign `deck_saloon` spelling. A `CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA` design-level result is simply not included.
    """
    if deck_saloon not in SEARCH_DECK_SALOON_VALUES:
        raise ValueError(
            f"deck_saloon must be one of {sorted(SEARCH_DECK_SALOON_VALUES)}; got {deck_saloon!r}"
        )
    query = MixedAndQuery(
        criteria=(CategoricalLeafCriterion(field=DECK_SALOON_PROJECTION_FIELD, equals=deck_saloon),)
    )
    return compatible_boat_design_ids_for_query(
        conn, query, boat_designs, (DECK_SALOON_FIELD_PROJECTION_SPEC,)
    )
