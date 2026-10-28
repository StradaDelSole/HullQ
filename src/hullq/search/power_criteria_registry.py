"""Static whitelisted Power-domain Search criterion registry — SLICE-0093.

The Power-domain counterpart of `hullq.search.criteria_registry`, bounded to
exactly the one accepted Power hard technical criterion
(`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`):
`power_drive_configuration`. This is a deliberately **separate** registry
module, not an eleventh entry merged into the Sail `CRITERION_DEFINITIONS`
tuple -- the slice contract requires "a separate Power-only buyer request
parser" that "does not widen Sail parser to accept Power keys". It reuses
the identical shared `CriterionDefinition`/`CriterionKind`/
`parse_categorical_param` shape and the identical
`hullq.search.configuration_engine.evaluate_projection`/
`evaluate_configuration` MUST/AND truth kernel the Sail registry already
established (Trigger Gates "Second-criterion bridge comparison" /
"Third-copy abstraction guard": COMMON STRUCTURE GENERALIZED / REUSED, not a
third copy) -- only the category-specific field decoder/projection
(`hullq.search.power_drive_design_bridge`) and this distinct Power
param-key/vocabulary are new.

A registry entry is never a database field scan, a raw JSON field pointer, a
user-controlled path, or a dynamically-registered plugin: this is a fixed,
reviewed, compile-time constant, exactly like `hullq.search.criteria_registry`.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from hullq.domain.physical_boat_claims import AssertionKind, PowerDriveConfiguration
from hullq.persistence.physical_boat_claims import CurrentPhysicalBoatClaimObservation
from hullq.search.criteria_registry import (
    ClaimReadResult,
    CriterionDefinition,
    CriterionKind,
    parse_categorical_param,
)
from hullq.search.power_drive_design_bridge import (
    POWER_DRIVE_CONFIGURATION_PROJECTION_FIELD as _POWER_DRIVE_CONFIGURATION_PROJECTION_FIELD,
)
from hullq.search.power_drive_design_bridge import (
    build_boat_design_power_drive_configuration_set,
)

__all__ = [
    "POWER_DRIVE_CONFIGURATION_DEFINITION",
    "POWER_DRIVE_PARAM_KEY",
    "SEARCH_POWER_DRIVE_VALUES",
    "active_power_definitions",
    "parse_categorical_param",
]

#: The one accepted public Power query-parameter key
#: (`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md` "Request /
#: query contract"): `GET /api/search/{locale}/power?power_drive=TOKEN`.
POWER_DRIVE_PARAM_KEY: Final = "power_drive"

#: The exact accepted public five-token exact whitelist (contract "One field,
#: one meaning"). A current publisher's durable claim may additionally
#: represent `MIXED`/`OTHER`/`UNKNOWN` as truthful but never an affirmative
#: filter match -- those three are real `hullq.domain.physical_boat_claims
#: .PowerDriveConfiguration` claim values but never public Search filter
#: tokens.
SEARCH_POWER_DRIVE_VALUES: Final[frozenset[str]] = frozenset(
    {"SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"}
)


def _read_power_drive_configuration_claim(
    observation: CurrentPhysicalBoatClaimObservation,
) -> ClaimReadResult:
    """Review amendment Finding A: a current `VALUE_ASSERTION(MIXED)` claim
    does not prove the absence of any single accepted drive type -- the
    normative contract's own words are "even if the vessel uses one of the
    types". Reading it as a confirmed categorical scalar `"MIXED"` would let
    the shared `evaluate_categorical_leaf` string-compare it against every
    one of the five public tokens and produce a false `CONFIRMED_NON_MATCH`
    via ordinary `!=` inequality -- exactly the unsupported confirmed
    negative the review identified. Reading it instead as `UNKNOWN` (never
    persisted this way, only read this way for Search classification) makes
    the shared fail-closed qualification (`_qualify_claim_field`) treat
    every one of the five tokens as `MISSING` -> `INSUFFICIENT_DATA`,
    identical bounded treatment to an explicit `UNKNOWN` claim -- never a
    proven exclusion.

    `OTHER` is deliberately NOT special-cased here: it denotes a confirmed,
    single (if uncatalogued) drive -- the publisher would have used the
    real token if the boat had one of the five, so `OTHER` genuinely is not
    any of them. Ordinary categorical equality already yields the correct
    `CONFIRMED_NON_MATCH` for every one of the five tokens, identical
    treatment to `HullMaterial.OTHER`/`KeelConfiguration.OTHER` elsewhere in
    this codebase -- no override needed or wanted.

    This Power-specific accessor is the only place this interpretation
    applies; it does not touch `hullq.search.criteria_registry`'s generic
    `_qualify_claim_field`/`evaluate_categorical_leaf` or any accepted Sail
    categorical field, which keep their own unmodified fail-closed equality
    semantics.
    """
    claim = observation.power_drive_configuration
    if claim is None:
        return None
    if (
        claim.assertion_kind is AssertionKind.VALUE_ASSERTION
        and claim.value is PowerDriveConfiguration.MIXED
    ):
        return (AssertionKind.UNKNOWN, None)
    value = (
        claim.value.value
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION and claim.value is not None
        else None
    )
    return claim.assertion_kind, value


#: The one accepted Power `CriterionDefinition` -- Power domain ordinal 1,
#: global accepted native technical criterion ordinal 10 (9 Sail + 1 Power,
#: advanced only by the separately reviewed Owner-accepted closure, never in
#: this READY/implementation branch). Reuses the identical
#: `CategoricalLeafCriterion`/`evaluate_projection`/`evaluate_configuration`
#: MUST/AND kernel the Sail registry's own categorical criteria already use
#: -- no new Power ad hoc evaluator.
POWER_DRIVE_CONFIGURATION_DEFINITION: Final = CriterionDefinition(
    criterion_id="power_drive_configuration",
    kind=CriterionKind.CATEGORICAL,
    param_keys=(POWER_DRIVE_PARAM_KEY,),
    projection_field=_POWER_DRIVE_CONFIGURATION_PROJECTION_FIELD,
    allowed_values=SEARCH_POWER_DRIVE_VALUES,
    design_set_builder=build_boat_design_power_drive_configuration_set,
    read_claim=_read_power_drive_configuration_claim,
)


def active_power_definitions() -> Sequence[CriterionDefinition]:
    """The exactly-one active Power `CriterionDefinition` -- kept as a
    function (not a bare tuple constant) so application callers that
    generalize over "active definitions" read identically to the Sail
    funnel's own `active_definitions: Sequence[CriterionDefinition]` shape,
    without implying a second, independently-sized Power criterion list
    exists yet."""
    return (POWER_DRIVE_CONFIGURATION_DEFINITION,)
