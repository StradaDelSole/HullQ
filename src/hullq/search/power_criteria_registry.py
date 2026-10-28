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

from hullq.domain.physical_boat_claims import AssertionKind
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
    """Plain passthrough read of the current `power_drive_configuration`
    claim -- identical shape to every other Sail `_read_*_claim` accessor
    (e.g. `hullq.search.criteria_registry._read_keel_claim`): reports
    exactly what the current claim asserts (including `VALUE_ASSERTION`
    `MIXED`/`OTHER`), with no Power-specific reinterpretation.

    Review amendment Finding H (BLOCKER): an earlier revision reinterpreted
    every `VALUE_ASSERTION(MIXED)` claim as `UNKNOWN` *here*, at the shared
    per-observation read boundary used uniformly for the publisher's own
    claim **and** every other current claiming Organization's claim
    (`hullq.application.native_inventory_query._qualify_claims_against_definitions`
    builds its `cross_organization_values` set from this same accessor).
    That silently erased another Organization's current contradictory
    `MIXED` claim from the cross-Organization contradiction check, so a
    publisher asserting a single drive type (e.g. `SHAFT`) while a
    different Organization currently claims `MIXED` for the same
    PhysicalBoat was treated as agreeing evidence instead of the fail-closed
    contradiction it actually is.

    "A current `MIXED` claim never proves the absence of any single accepted
    drive type" (contract: "even if the vessel uses one of the types") is a
    *result-level* semantic, not a claim-read-level one -- it is now applied
    only to the publisher's own already-qualified `CONFIRMED_NON_MATCH`
    outcome, in `hullq.application.power_inventory_query
    ._downgrade_mixed_non_match_to_insufficient_data`, strictly after
    `_qualify_claims_against_definitions` has already run its ordinary
    cross-Organization contradiction guard against the true, unmasked claim
    values. `OTHER` is unaffected either way: it denotes a confirmed,
    single (if uncatalogued) drive, so ordinary categorical equality already
    yields the correct `CONFIRMED_NON_MATCH`, identical treatment to
    `HullMaterial.OTHER`/`KeelConfiguration.OTHER` elsewhere in this
    codebase.
    """
    claim = observation.power_drive_configuration
    if claim is None:
        return None
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
