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

    deck_saloon -> DECK_SALOON   (public filter value)
    pilothouse  -> PILOTHOUSE    (public filter value)
    none        -> internal-only NONE sentinel (never a public filter value)
    unknown     -> no mapping (MISSING)

PR #349 independent-review Finding A: a genuinely qualified, source-backed
`none` is a *known* fact (the design positively does not have a deck saloon/
pilothouse) and must not collapse to the same `MISSING` an unqualified or
`unknown` value produces -- the slice's own normative text requires `NONE`
to remain "a confirmed positive claim of absence ... mechanically distinct
... from an explicit UNKNOWN assertion", and that distinction is preserved
here on the design side too, not only on the concrete-claim side. `none`
therefore DOES get a taxonomy-map entry, to the internal-only sentinel
`_DECK_SALOON_NONE_SENTINEL` ("NONE") -- never a member of
`SEARCH_DECK_SALOON_VALUES`, never accepted by
`compatible_boat_design_ids_for_deck_saloon`/any public parser's
`allowed_values`. Because the ordinary categorical MUST-AND evaluator
(`hullq.search.criteria.evaluate_categorical_leaf`) compares a `CONFIRMED`
projected value against the *requested* `DECK_SALOON`/`PILOTHOUSE` value by
plain string equality, a confirmed `"NONE"` projection naturally and
correctly evaluates FALSE (a true, typed non-match) against either
requested public category, with no bespoke non-match branch and no second
evaluator -- exactly "Concrete DeckSaloon.NONE already yields an exact FALSE
against requested positive categories; keep that" (Finding A), now mirrored
on the design side. `unknown` keeps no taxonomy-map entry at all and still
fails closed to `MISSING` (never confused with the confirmed-known-absence
case). `DECK_SALOON` and `PILOTHOUSE` are never merged or treated as
entailing one another.

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
    "DECK_SALOON_NONE_SENTINEL",
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

#: Normative v0.1 PUBLIC mapping -- the only two tokens the public Search
#: filter accepts (`SEARCH_DECK_SALOON_VALUES` below is derived from exactly
#: this dict, so it can never silently widen). `none` is deliberately NOT a
#: member here: it is a real, independently qualifiable design value (see
#: `_BOAT_DESIGN_DECK_SALOON_TO_INTERNAL` below) but never a public filter
#: token (slice: "a public NONE filter is explicitly deferred").
BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON: Final[dict[str, str]] = {
    "deck_saloon": "DECK_SALOON",
    "pilothouse": "PILOTHOUSE",
}

#: The exact accepted public v0.1 `deck_saloon` query values -- explicit and
#: bounded to the PUBLIC map above, so adding the internal NONE sentinel
#: below can never accidentally widen this set.
SEARCH_DECK_SALOON_VALUES: Final[frozenset[str]] = frozenset(
    BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON.values()
)

#: Internal-only sentinel for a qualified, positively-asserted absence of a
#: deck saloon/pilothouse (PR #349 review Finding A). Never a member of
#: `SEARCH_DECK_SALOON_VALUES`, never returned by `allowed_values`/accepted
#: by any public or broker-facing parser -- it exists solely as the
#: `QualifiedCategoricalValue.value` a CONFIRMED `none` design fact projects
#: to, so the ordinary categorical MUST-AND evaluator can correctly classify
#: it as a confirmed non-match against a requested `DECK_SALOON`/
#: `PILOTHOUSE` value, rather than collapsing it into the same `MISSING` an
#: `unknown`/unqualified value produces.
DECK_SALOON_NONE_SENTINEL: Final = "NONE"

#: The full internal taxonomy this bridge's `FieldProjectionSpec` actually
#: qualifies against -- every public value plus the internal NONE sentinel.
#: `unknown` is deliberately absent from this dict too (no entry => fails
#: closed to MISSING via the shared bridge's `_qualify_and_map`, exactly
#: like every other unmapped raw token in this codebase).
_BOAT_DESIGN_DECK_SALOON_TO_INTERNAL: Final[dict[str, str]] = {
    **BOAT_DESIGN_DECK_SALOON_TO_SEARCH_DECK_SALOON,
    "none": DECK_SALOON_NONE_SENTINEL,
}

#: This criterion's shared-bridge field-projection contract. Uses the full
#: internal taxonomy (including the NONE sentinel), not the public-only map
#: -- the public/private boundary is enforced separately by
#: `SEARCH_DECK_SALOON_VALUES`/`compatible_boat_design_ids_for_deck_saloon`,
#: never by narrowing what this bridge can qualify.
DECK_SALOON_FIELD_PROJECTION_SPEC: Final = FieldProjectionSpec(
    projection_field=DECK_SALOON_PROJECTION_FIELD,
    section_key="deck",
    field_key="deck_saloon",
    baseline_pointer=DECK_SALOON_FIELD_POINTER,
    override_pointer=DECK_SALOON_OVERRIDE_FIELD_POINTER,
    decode=decode_categorical_string_for_qualification,
    is_numeric=False,
    taxonomy_map=_BOAT_DESIGN_DECK_SALOON_TO_INTERNAL,
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
    a raw BoatDesign `deck_saloon` spelling and never the internal
    `DECK_SALOON_NONE_SENTINEL`. A `CONFIRMED_NON_MATCH` or
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
