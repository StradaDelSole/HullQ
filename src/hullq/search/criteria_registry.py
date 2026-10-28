"""Static whitelisted public multi-criterion Search registry — SLICE-0085.

Review amendment (Finding C): the original module shipped only a param-key
string table. This is the actual bounded typed registry the READY contract's
"Shared foundation" constraint 1 requires: each accepted criterion's stable
identifier, unit/allowed-token vocabulary, public parameter key(s) and
canonical ordering, numeric operator shape, design/variant adapter
(`design_set_builder`), concrete publisher claim accessor (`read_claim`),
and parse/canonicalize functions, in one `CriterionDefinition` per criterion.

This is genuinely consumed, not merely descriptive:
`hullq.application.native_inventory_query.classify_concrete_candidate`
reads every active `CriterionDefinition.read_claim` in one shared loop
instead of one hand-duplicated per-criterion block, and
`run_mixed_boat_design_configuration_query` calls every active
`design_set_builder` and merges their results, instead of threading a
separate `FieldProjectionSpec` list past a `rudder`-only special case. The
public (`hullq.application.search_read`) and private
(`hullq.application.broker_search_fit`) HTTP boundaries both parse their raw
query values through this module's `parse_numeric_param`/
`parse_categorical_param`, driven by `parse_value`/`canonicalize_value`/
`allowed_values` -- so the one-time taxonomy/grammar decision for each
criterion lives in exactly one typed declaration, not reimplemented at each
HTTP surface.

What is deliberately NOT unified here, with the exact reason recorded
(contract: "if some components must remain type-specific, record the exact
constraint"):

- Canonical-URL *assembly* (`hullq.application.search_read.
  build_canonical_search_path`) stays keyed by the individual public
  parameter name, not by `CriterionDefinition`, because `loa_min`/`loa_max`
  are two independently-held request values sharing ONE definition/
  projection field -- a single "render this definition's value" function
  would need its own second per-key indirection that buys nothing over the
  five-way explicit assembly already there.
- The query-leaf *count* a criterion contributes (`loa` becomes one or two
  `NumericLeafCriterion`s; every other criterion contributes exactly one
  leaf) stays in `hullq.application.native_inventory_query.
  build_mixed_requirement_query`, which already receives each criterion's
  already-parsed value(s) directly -- generalizing leaf *construction*
  itself behind the registry would require encoding "how many leaves, from
  which named inputs" per criterion, which is exactly the kind of
  general-purpose query-compiler abstraction the READY contract explicitly
  forbids ("do not introduce a general-purpose DSL").
- The TypeScript/Astro presentation layer (labels, placeholders, option
  lists in `web/src/lib/searchText.ts`) cannot import this Python module --
  a cross-language constraint, not a design choice. The exact bounded
  vocabulary (`allowed_values` below) is the single source of truth the TS
  constants (`SEARCH_KEEL_CONFIGURATION_VALUES`, etc.) must keep mirroring;
  `tests/unit/test_criteria_registry_parity.py` cross-checks this.

A registry entry is never a database field scan, a raw JSON field pointer, a
user-controlled path, or a dynamically-registered plugin: every entry below
is a fixed, reviewed, compile-time constant, and `design_set_builder`/
`read_claim`/`parse_value`/`canonicalize_value` are references to existing,
already-reviewed functions in each criterion's own bridge module -- this
module introduces no new truth/parsing logic of its own, only the shared
declaration and the two small generic consumption loops described above.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from typing import Any, Final

from hullq.domain.physical_boat_claims import AssertionKind
from hullq.persistence.physical_boat_claims import CurrentPhysicalBoatClaimObservation
from hullq.search.beam_design_bridge import BEAM_PROJECTION_FIELD as _BEAM_PROJECTION_FIELD
from hullq.search.beam_design_bridge import build_boat_design_beam_configuration_set
from hullq.search.beam_request import canonical_beam_str, parse_beam_decimal
from hullq.search.cockpit_design_bridge import (
    COCKPIT_POSITION_PROJECTION_FIELD as _COCKPIT_POSITION_PROJECTION_FIELD,
)
from hullq.search.cockpit_design_bridge import (
    SEARCH_COCKPIT_POSITION_VALUES,
    build_boat_design_cockpit_position_set,
)
from hullq.search.configuration import DesignConfigurationSet
from hullq.search.deck_saloon_design_bridge import (
    DECK_SALOON_PROJECTION_FIELD as _DECK_SALOON_PROJECTION_FIELD,
)
from hullq.search.deck_saloon_design_bridge import (
    SEARCH_DECK_SALOON_VALUES,
    build_boat_design_deck_saloon_configuration_set,
)
from hullq.search.draft_max_design_bridge import (
    DRAFT_MAX_PROJECTION_FIELD as _DRAFT_MAX_PROJECTION_FIELD,
)
from hullq.search.draft_max_design_bridge import build_boat_design_draft_configuration_set
from hullq.search.draft_max_request import canonical_draft_max_str, parse_draft_max_decimal
from hullq.search.hull_design_bridge import (
    HULL_CONFIGURATION_PROJECTION_FIELD as _HULL_CONFIGURATION_PROJECTION_FIELD,
)
from hullq.search.hull_design_bridge import (
    SEARCH_HULL_CONFIGURATION_VALUES,
    build_boat_design_hull_configuration_set,
)
from hullq.search.hull_material_design_bridge import (
    HULL_MATERIAL_PROJECTION_FIELD as _HULL_MATERIAL_PROJECTION_FIELD,
)
from hullq.search.hull_material_design_bridge import (
    SEARCH_HULL_MATERIAL_VALUES,
    build_boat_design_hull_material_configuration_set,
)
from hullq.search.keel_design_bridge import (
    KEEL_CONFIGURATION_PROJECTION_FIELD as _KEEL_CONFIGURATION_PROJECTION_FIELD,
)
from hullq.search.keel_design_bridge import (
    SEARCH_KEEL_CONFIGURATION_VALUES,
    build_boat_design_keel_configuration_set,
)
from hullq.search.loa_design_bridge import LOA_PROJECTION_FIELD as _LOA_PROJECTION_FIELD
from hullq.search.loa_design_bridge import build_boat_design_loa_configuration_set
from hullq.search.loa_request import canonical_loa_str, parse_loa_decimal
from hullq.search.rudder_design_bridge import (
    RUDDER_CONFIGURATION_PROJECTION_FIELD as _RUDDER_CONFIGURATION_PROJECTION_FIELD,
)
from hullq.search.rudder_design_bridge import (
    SEARCH_RUDDER_CONFIGURATION_VALUES,
    build_boat_design_rudder_configuration_set,
)

__all__ = [
    "BEAM_DEFINITION",
    "BEAM_MAX_PARAM_KEY",
    "BEAM_MIN_PARAM_KEY",
    "CANONICAL_PARAM_KEY_ORDER",
    "COCKPIT_POSITION_DEFINITION",
    "COCKPIT_POSITION_PARAM_KEY",
    "CRITERION_DEFINITIONS",
    "DECK_SALOON_DEFINITION",
    "DECK_SALOON_PARAM_KEY",
    "DRAFT_MAX_DEFINITION",
    "DRAFT_MAX_PARAM_KEY",
    "HULL_CONFIGURATION_DEFINITION",
    "HULL_CONFIGURATION_PARAM_KEY",
    "HULL_MATERIAL_DEFINITION",
    "HULL_MATERIAL_PARAM_KEY",
    "KEEL_CONFIGURATION_DEFINITION",
    "KEEL_CONFIGURATION_PARAM_KEY",
    "LOA_DEFINITION",
    "LOA_MAX_PARAM_KEY",
    "LOA_MIN_PARAM_KEY",
    "RUDDER_CONFIGURATION_DEFINITION",
    "RUDDER_CONFIGURATION_PARAM_KEY",
    "SUPPORTED_PARAM_KEYS",
    "CriterionDefinition",
    "CriterionKind",
    "parse_categorical_param",
    "parse_numeric_param",
]

#: Stable public query-parameter keys. These are the exact strings used in
#: public canonical Search URLs, the private broker Search-fit scenario and
#: the typed FastAPI/TS boundary -- never renamed without an accepted
#: canonical-URL migration decision.
DRAFT_MAX_PARAM_KEY: Final = "draft_max"
KEEL_CONFIGURATION_PARAM_KEY: Final = "keel_configuration"
LOA_MIN_PARAM_KEY: Final = "loa_min"
LOA_MAX_PARAM_KEY: Final = "loa_max"
RUDDER_CONFIGURATION_PARAM_KEY: Final = "rudder_configuration"
#: SLICE-0086 candidate facets #5-#7.
HULL_CONFIGURATION_PARAM_KEY: Final = "hull_configuration"
COCKPIT_POSITION_PARAM_KEY: Final = "cockpit_position"
DECK_SALOON_PARAM_KEY: Final = "deck_saloon"
#: SLICE-0087 facets #8-#9.
BEAM_MIN_PARAM_KEY: Final = "beam_min"
BEAM_MAX_PARAM_KEY: Final = "beam_max"
HULL_MATERIAL_PARAM_KEY: Final = "hull_material"

#: The complete bounded whitelist. Any query-parameter key outside this set
#: is INVALID, never silently ignored (the accepted zero-non-semantic-
#: allowlist policy, `docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`,
#: extended to every criterion this slice adds).
SUPPORTED_PARAM_KEYS: Final[frozenset[str]] = frozenset(
    {
        DRAFT_MAX_PARAM_KEY,
        KEEL_CONFIGURATION_PARAM_KEY,
        LOA_MIN_PARAM_KEY,
        LOA_MAX_PARAM_KEY,
        RUDDER_CONFIGURATION_PARAM_KEY,
        HULL_CONFIGURATION_PARAM_KEY,
        COCKPIT_POSITION_PARAM_KEY,
        DECK_SALOON_PARAM_KEY,
        BEAM_MIN_PARAM_KEY,
        BEAM_MAX_PARAM_KEY,
        HULL_MATERIAL_PARAM_KEY,
    }
)

#: The one accepted canonical key ordering (slice normative LOA semantics:
#: "Public canonical key order is the accepted lexicographic policy, not UI
#: display order"). Plain lexicographic sort of `SUPPORTED_PARAM_KEYS` --
#: asserted below so this constant can never silently drift from that rule.
CANONICAL_PARAM_KEY_ORDER: Final[tuple[str, ...]] = (
    BEAM_MAX_PARAM_KEY,
    BEAM_MIN_PARAM_KEY,
    COCKPIT_POSITION_PARAM_KEY,
    DECK_SALOON_PARAM_KEY,
    DRAFT_MAX_PARAM_KEY,
    HULL_CONFIGURATION_PARAM_KEY,
    HULL_MATERIAL_PARAM_KEY,
    KEEL_CONFIGURATION_PARAM_KEY,
    LOA_MAX_PARAM_KEY,
    LOA_MIN_PARAM_KEY,
    RUDDER_CONFIGURATION_PARAM_KEY,
)

assert tuple(sorted(SUPPORTED_PARAM_KEYS)) == CANONICAL_PARAM_KEY_ORDER, (
    "CANONICAL_PARAM_KEY_ORDER must stay exactly the lexicographic sort of "
    "SUPPORTED_PARAM_KEYS -- see this module's docstring"
)


class CriterionKind(StrEnum):
    """The four accepted operator shapes -- never a generic/open-ended
    operator vocabulary. `NUMERIC_MAXIMUM_ONLY` (draft_max) and
    `NUMERIC_MIN_MAX` (loa) both project an exact `Decimal` bound;
    `NUMERIC_EXACT` (SLICE-0094 `power_engine_count`) projects an exact
    `Decimal` equality value from one public parameter key (an existing
    numeric `RANGE` comparison with `threshold_min == threshold_max`, never
    a new scorer); `CATEGORICAL` (keel_configuration, rudder_configuration)
    projects an exact-match string from `allowed_values`. Only
    `is_categorical` (`self.kind is CriterionKind.CATEGORICAL`) is ever
    consulted by generic application code
    (`hullq.application.native_inventory_query
    ._qualify_claims_against_definitions`) -- the numeric sub-kinds are
    documentary/self-descriptive only; the actual `NumericComparisonKind`
    (MINIMUM/MAXIMUM/RANGE) a caller builds is always decided explicitly at
    its own query-construction call site, never dispatched from this enum."""

    NUMERIC_MAXIMUM_ONLY = "NUMERIC_MAXIMUM_ONLY"
    NUMERIC_MIN_MAX = "NUMERIC_MIN_MAX"
    NUMERIC_EXACT = "NUMERIC_EXACT"
    CATEGORICAL = "CATEGORICAL"


#: `(assertion_kind, confirmed_value_or_None)` for one Organization's current
#: claim on this criterion's own field, or `None` when that Organization's
#: current claim snapshot omits the field entirely -- mirrors
#: `hullq.persistence.physical_boat_claims.CurrentPhysicalBoatClaimObservation`'s
#: own per-field optionality. `confirmed_value_or_None` is non-`None` only
#: when `assertion_kind is AssertionKind.VALUE_ASSERTION` (never a value
#: alongside `UNKNOWN`).
ClaimReadResult = tuple[AssertionKind, Any] | None
ClaimReader = Callable[[CurrentPhysicalBoatClaimObservation], ClaimReadResult]
DesignSetBuilder = Callable[[Any, Mapping[str, Any]], DesignConfigurationSet]


@dataclass(frozen=True, slots=True)
class CriterionDefinition:
    """One criterion's complete static wiring (READY contract's "Shared
    foundation" constraint 1): stable identifier, operator shape, public
    parameter key(s), bounded allowed-token vocabulary (categorical only),
    the design/variant `DesignConfigurationSet` adapter, the concrete
    publisher claim accessor, and (numeric only) the parse/canonicalize
    functions.

    `design_set_builder` and `read_claim` are the two pieces of genuinely
    shared *behavior* this registry carries (see module docstring): every
    criterion's `design_set_builder` has the identical
    `(conn, boat_design) -> DesignConfigurationSet` shape regardless of
    whether its own projection comes from a single `FieldProjectionSpec`
    (draft_max/keel_configuration/loa) or a generation-aware derived value
    (rudder_configuration) -- `hullq.application.native_inventory_query.
    run_mixed_boat_design_configuration_query` calls every active
    definition's builder uniformly and merges the results. `read_claim` has
    the identical `(observation) -> (assertion_kind, value) | None` shape
    for every criterion regardless of whether the underlying claim wraps a
    `Decimal` or an enum -- `classify_concrete_candidate` reads every active
    definition's claim in one shared loop instead of duplicating the same
    fail-closed cross-Organization qualification per field.
    """

    criterion_id: str
    kind: CriterionKind
    param_keys: tuple[str, ...]
    projection_field: str
    allowed_values: frozenset[str] | None
    design_set_builder: DesignSetBuilder
    read_claim: ClaimReader
    parse_value: Callable[[str], Decimal] | None = None
    canonicalize_value: Callable[[Decimal], str] | None = None

    def __post_init__(self) -> None:
        is_categorical = self.kind is CriterionKind.CATEGORICAL
        if is_categorical:
            if self.allowed_values is None:
                raise ValueError(
                    f"{self.criterion_id}: CATEGORICAL criteria require allowed_values"
                )
            if self.parse_value is not None or self.canonicalize_value is not None:
                raise ValueError(
                    f"{self.criterion_id}: CATEGORICAL criteria must not carry "
                    "parse_value/canonicalize_value"
                )
        else:
            if self.allowed_values is not None:
                raise ValueError(
                    f"{self.criterion_id}: numeric criteria must not carry allowed_values"
                )
            if self.parse_value is None or self.canonicalize_value is None:
                raise ValueError(
                    f"{self.criterion_id}: numeric criteria require parse_value/canonicalize_value"
                )


# ---------------------------------------------------------------------------
# Concrete claim accessors -- the "concrete publisher accessor" the READY
# contract's registry requires. Each reads one claim field's current
# (assertion_kind, confirmed_value) from one Organization's observation,
# with identical fail-closed shape regardless of the underlying claim type.
# ---------------------------------------------------------------------------


def _read_draft_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.draft
    if claim is None:
        return None
    value = claim.value if claim.assertion_kind is AssertionKind.VALUE_ASSERTION else None
    return claim.assertion_kind, value


def _read_keel_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.keel_configuration
    if claim is None:
        return None
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


def _read_loa_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.loa_length
    if claim is None:
        return None
    value = claim.value if claim.assertion_kind is AssertionKind.VALUE_ASSERTION else None
    return claim.assertion_kind, value


def _read_rudder_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.rudder_configuration
    if claim is None:
        return None
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


def _read_hull_configuration_claim(
    observation: CurrentPhysicalBoatClaimObservation,
) -> ClaimReadResult:
    claim = observation.hull_configuration
    if claim is None:
        return None
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


def _read_cockpit_position_claim(
    observation: CurrentPhysicalBoatClaimObservation,
) -> ClaimReadResult:
    claim = observation.cockpit_position
    if claim is None:
        return None
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


def _read_deck_saloon_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.deck_saloon
    if claim is None:
        return None
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


def _read_beam_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.beam
    if claim is None:
        return None
    value = claim.value if claim.assertion_kind is AssertionKind.VALUE_ASSERTION else None
    return claim.assertion_kind, value


def _read_hull_material_claim(observation: CurrentPhysicalBoatClaimObservation) -> ClaimReadResult:
    claim = observation.hull_material
    if claim is None:
        return None
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


# ---------------------------------------------------------------------------
# The four originally accepted criterion definitions, plus the three
# SLICE-0086 candidate facets (hull_configuration/cockpit_position/
# deck_saloon) and the two SLICE-0087 facets (beam/hull_material)
# ---------------------------------------------------------------------------

DRAFT_MAX_DEFINITION: Final = CriterionDefinition(
    criterion_id="draft_max",
    kind=CriterionKind.NUMERIC_MAXIMUM_ONLY,
    param_keys=(DRAFT_MAX_PARAM_KEY,),
    projection_field=_DRAFT_MAX_PROJECTION_FIELD,
    allowed_values=None,
    design_set_builder=build_boat_design_draft_configuration_set,
    read_claim=_read_draft_claim,
    parse_value=parse_draft_max_decimal,
    canonicalize_value=canonical_draft_max_str,
)

KEEL_CONFIGURATION_DEFINITION: Final = CriterionDefinition(
    criterion_id="keel_configuration",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(KEEL_CONFIGURATION_PARAM_KEY,),
    projection_field=_KEEL_CONFIGURATION_PROJECTION_FIELD,
    allowed_values=SEARCH_KEEL_CONFIGURATION_VALUES,
    design_set_builder=build_boat_design_keel_configuration_set,
    read_claim=_read_keel_claim,
)

#: LOA's own public parameter keys, in the accepted canonical order (loa_max
#: before loa_min) -- both share this ONE definition/projection field
#: (`loa_m`); which of the two bounds is active is decided by the caller,
#: never by this registry (see module docstring).
LOA_DEFINITION: Final = CriterionDefinition(
    criterion_id="loa",
    kind=CriterionKind.NUMERIC_MIN_MAX,
    param_keys=(LOA_MAX_PARAM_KEY, LOA_MIN_PARAM_KEY),
    projection_field=_LOA_PROJECTION_FIELD,
    allowed_values=None,
    design_set_builder=build_boat_design_loa_configuration_set,
    read_claim=_read_loa_claim,
    parse_value=parse_loa_decimal,
    canonicalize_value=canonical_loa_str,
)

RUDDER_CONFIGURATION_DEFINITION: Final = CriterionDefinition(
    criterion_id="rudder_configuration",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(RUDDER_CONFIGURATION_PARAM_KEY,),
    projection_field=_RUDDER_CONFIGURATION_PROJECTION_FIELD,
    allowed_values=SEARCH_RUDDER_CONFIGURATION_VALUES,
    design_set_builder=build_boat_design_rudder_configuration_set,
    read_claim=_read_rudder_claim,
)

#: SLICE-0086 candidate facet #5.
HULL_CONFIGURATION_DEFINITION: Final = CriterionDefinition(
    criterion_id="hull_configuration",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(HULL_CONFIGURATION_PARAM_KEY,),
    projection_field=_HULL_CONFIGURATION_PROJECTION_FIELD,
    allowed_values=SEARCH_HULL_CONFIGURATION_VALUES,
    design_set_builder=build_boat_design_hull_configuration_set,
    read_claim=_read_hull_configuration_claim,
)

#: SLICE-0086 candidate facet #6.
COCKPIT_POSITION_DEFINITION: Final = CriterionDefinition(
    criterion_id="cockpit_position",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(COCKPIT_POSITION_PARAM_KEY,),
    projection_field=_COCKPIT_POSITION_PROJECTION_FIELD,
    allowed_values=SEARCH_COCKPIT_POSITION_VALUES,
    design_set_builder=build_boat_design_cockpit_position_set,
    read_claim=_read_cockpit_position_claim,
)

#: SLICE-0086 candidate facet #7.
DECK_SALOON_DEFINITION: Final = CriterionDefinition(
    criterion_id="deck_saloon",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(DECK_SALOON_PARAM_KEY,),
    projection_field=_DECK_SALOON_PROJECTION_FIELD,
    allowed_values=SEARCH_DECK_SALOON_VALUES,
    design_set_builder=build_boat_design_deck_saloon_configuration_set,
    read_claim=_read_deck_saloon_claim,
)

#: SLICE-0087 facet #8. Both public parameter keys share this ONE
#: definition/projection field (`beam_m`) -- see `hullq.search.
#: beam_design_bridge`'s module docstring.
BEAM_DEFINITION: Final = CriterionDefinition(
    criterion_id="beam",
    kind=CriterionKind.NUMERIC_MIN_MAX,
    param_keys=(BEAM_MAX_PARAM_KEY, BEAM_MIN_PARAM_KEY),
    projection_field=_BEAM_PROJECTION_FIELD,
    allowed_values=None,
    design_set_builder=build_boat_design_beam_configuration_set,
    read_claim=_read_beam_claim,
    parse_value=parse_beam_decimal,
    canonicalize_value=canonical_beam_str,
)

#: SLICE-0087 facet #9.
HULL_MATERIAL_DEFINITION: Final = CriterionDefinition(
    criterion_id="hull_material",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(HULL_MATERIAL_PARAM_KEY,),
    projection_field=_HULL_MATERIAL_PROJECTION_FIELD,
    allowed_values=SEARCH_HULL_MATERIAL_VALUES,
    design_set_builder=build_boat_design_hull_material_configuration_set,
    read_claim=_read_hull_material_claim,
)

#: Every accepted criterion, in the exact order its PARAM_KEY(s) first
#: appear in `CANONICAL_PARAM_KEY_ORDER`.
CRITERION_DEFINITIONS: Final[tuple[CriterionDefinition, ...]] = (
    BEAM_DEFINITION,
    COCKPIT_POSITION_DEFINITION,
    DECK_SALOON_DEFINITION,
    DRAFT_MAX_DEFINITION,
    HULL_CONFIGURATION_DEFINITION,
    HULL_MATERIAL_DEFINITION,
    KEEL_CONFIGURATION_DEFINITION,
    LOA_DEFINITION,
    RUDDER_CONFIGURATION_DEFINITION,
)

assert {key for d in CRITERION_DEFINITIONS for key in d.param_keys} == SUPPORTED_PARAM_KEYS, (
    "Every CriterionDefinition.param_keys entry must appear in SUPPORTED_PARAM_KEYS and vice versa"
)


# ---------------------------------------------------------------------------
# Shared parsing helpers -- consumed by both the public
# (hullq.application.search_read) and private
# (hullq.application.broker_search_fit) HTTP boundaries, replacing what were
# four near-duplicated per-criterion parsing blocks with two generic ones.
# ---------------------------------------------------------------------------


def parse_categorical_param(
    definition: CriterionDefinition, raw_values: Sequence[str]
) -> tuple[str | None, bool] | None:
    """Parse one CATEGORICAL criterion's raw query values.

    Returns `None` for any invalid input (unsupported value, or conflicting
    duplicates); `(None, True)` when *raw_values* is empty (not supplied);
    otherwise `(value, is_single_canonical)` where `is_single_canonical` is
    `False` for any duplicate -- even of an identical value -- so the caller
    can decide its own surface-appropriate response (public: 308 redirect;
    private Search-fit: fail closed directly, no canonical-URL identity to
    redirect to). Never fuzzy-matched/case-folded: exact membership in
    `definition.allowed_values` only.
    """
    if not raw_values:
        return (None, True)
    assert definition.allowed_values is not None
    for raw in raw_values:
        if raw not in definition.allowed_values:
            return None
    if len(set(raw_values)) > 1:
        return None
    return (raw_values[0], len(raw_values) == 1)


def parse_numeric_param(
    definition: CriterionDefinition, raw_values: Sequence[str]
) -> tuple[Decimal | None, bool] | None:
    """Parse one NUMERIC criterion's raw query values.

    Mirrors `parse_categorical_param`'s return convention. Uses
    `definition.parse_value`/`canonicalize_value` -- the one place each
    numeric criterion's own bounded lexical grammar and canonical
    serialization is invoked, never re-implemented per caller.
    """
    if not raw_values:
        return (None, True)
    assert definition.parse_value is not None and definition.canonicalize_value is not None
    parsed: list[Decimal] = []
    for raw in raw_values:
        try:
            parsed.append(definition.parse_value(raw))
        except ValueError:
            return None
    if len(set(parsed)) > 1:
        return None
    value = parsed[0]
    is_single_canonical = len(raw_values) == 1 and raw_values[0] == definition.canonicalize_value(
        value
    )
    return (value, is_single_canonical)
