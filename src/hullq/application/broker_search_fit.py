"""Broker-facing authorized single-target hypothetical DRAFT Search-fit preview — SLICE-0084.

Implements REQ-BROKER-026/MVP-BROKER-010: given exactly one authorized
Organization-owned, lifecycle-`DRAFT` NativeListing and a bounded, explicitly
synthetic scenario (`draft_max`/`keel_configuration`, extended SLICE-0085 to
`loa_min`/`loa_max`/`rudder_configuration`), produce the same
`CONFIRMED_MATCH`/`CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` technical result
the accepted public Search kernel would produce for the identical facts --
read-only, never inserted into public Search, never evaluated against the
pre-promotion `ProfessionalListingDraft`.

This module introduces **no second Search truth engine**. Query
construction, design/configuration eligibility and concrete PhysicalBoat
claim classification all reuse the exact same bounded primitives the public
multi-candidate funnel (`hullq.application.native_inventory_query`) already
calls:

    hullq.application.native_inventory_query.build_mixed_requirement_query
    hullq.application.native_inventory_query.run_mixed_boat_design_configuration_query
    hullq.application.native_inventory_query.build_configuration_evidence
    hullq.application.native_inventory_query.classify_concrete_candidate

The only genuinely new responsibility here is resolving one *authorized,
owned* NativeListing's own NativeListing -> MarketEpisode -> PhysicalBoat
chain directly (never through `hullq.persistence.inventory_search.
list_active_design_linked_listings`, which enumerates only currently public
ACTIVE candidates and would silently omit a lifecycle-DRAFT target), and
mapping an authorization/lifecycle/chain-integrity failure to its own
mechanically distinct, non-enumerating outcome.

Authorization reuses the exact accepted SLICE-0053 Organization workspace/
MFA boundary (`hullq.application.broker_workspace_read.
get_organization_workspace_result`) -- mirrors `hullq.application.
inventory_editing`'s identical `_authorize_editor_actor` pattern -- plus an
explicit current-membership PUBLISHER-role check this preview's own contract
requires (`specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md` REQ-BROKER-026: "a
mere guessed Organization or user-supplied account ID has no standing";
Required Behavior §C: "Organization-scoped with current ACTIVE matching
Membership and PUBLISHER plus MFA"). `evaluate_organization_workspace_
authorization` already guarantees an `AUTHORIZED` outcome's membership is
ACTIVE, so only the PUBLISHER-role membership itself still needs checking
here -- never a second membership-state/MFA re-decision.

`NATIVE_LISTING_NOT_FOUND`/`ORGANIZATION_MISMATCH` collapse to the identical
`LISTING_NOT_FOUND` outcome -- a foreign listing's existence is never
distinguishable from an unknown one once the Organization boundary itself
has already succeeded (mirrors `hullq.application.inventory_editing`/
`hullq.application.design_association`).

Mechanical invariants §C (stale/concurrent-state; independent review
Finding A, PR #342): every read needed to assemble a would-be `OK`
result -- authorization, lifecycle, the NativeListing -> MarketEpisode ->
PhysicalBoat chain, design evaluation and concrete claim classification --
runs inside one explicit `REPEATABLE READ` PostgreSQL transaction, mirroring
`hullq.application.search_sensitivity`'s identical discipline: under the
default `READ COMMITTED` isolation, several independent statements could
each see the latest committed state independently, so an interleaved role/
lifecycle/claim change landing mid-evaluation could produce a result that
never existed in any single consistent database state. `REPEATABLE READ`
fixes one MVCC snapshot at the first statement of the transaction and holds
it for every later statement in that same transaction. Immediately after
that snapshot transaction closes, both authorization and lifecycle are
rechecked once more from deliberately fresh statements against the
now-current committed state -- an Organization membership revoked, its
PUBLISHER role removed, or a DRAFT->ACTIVE/WITHDRAWN transition occurring
while the snapshot read was in flight is therefore never silently used to
legitimize a stale `OK` result; it fails closed to the same typed denial/
`NOT_PREVIEWABLE` outcome a request arriving after the change would get.
This is the accepted "single transaction snapshot ... or equivalent bounded
recheck" strategy (contract §C) applied to the *entire* read, not only
lifecycle -- not a held row lock or any write: the preview performs zero
writes, so there is no mutation to serialize against.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.broker_workspace_read import (
    OrganizationWorkspaceOutcome,
    get_organization_workspace_result,
)
from hullq.application.native_inventory_query import (
    ConfigurationEvidence,
    SearchCriterionEvidence,
    build_configuration_evidence,
    build_mixed_requirement_query,
    classify_concrete_candidate,
    run_mixed_boat_design_configuration_query,
)
from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId, MembershipRole
from hullq.domain.vessel_category import VesselCategoryExclusionEvidence
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.search.configuration_engine import DesignQueryEvaluation
from hullq.search.criteria_registry import (
    BEAM_DEFINITION,
    BEAM_MAX_PARAM_KEY,
    BEAM_MIN_PARAM_KEY,
    COCKPIT_POSITION_DEFINITION,
    COCKPIT_POSITION_PARAM_KEY,
    DECK_SALOON_DEFINITION,
    DECK_SALOON_PARAM_KEY,
    DRAFT_MAX_DEFINITION,
    DRAFT_MAX_PARAM_KEY,
    HULL_CONFIGURATION_DEFINITION,
    HULL_CONFIGURATION_PARAM_KEY,
    HULL_MATERIAL_DEFINITION,
    HULL_MATERIAL_PARAM_KEY,
    KEEL_CONFIGURATION_DEFINITION,
    KEEL_CONFIGURATION_PARAM_KEY,
    LOA_DEFINITION,
    LOA_MAX_PARAM_KEY,
    LOA_MIN_PARAM_KEY,
    RUDDER_CONFIGURATION_DEFINITION,
    RUDDER_CONFIGURATION_PARAM_KEY,
    SUPPORTED_PARAM_KEYS,
    parse_categorical_param,
    parse_numeric_param,
)
from hullq.search.types import ResultClass, TruthState
from hullq.security.session_token import SessionClaims

__all__ = [
    "InvalidSearchFitScenarioError",
    "SearchFitBlocker",
    "SearchFitOutcome",
    "SearchFitResult",
    "SearchFitView",
    "evaluate_organization_listing_search_fit",
    "parse_search_fit_scenario",
]

_DRAFT_MAX_KEY = DRAFT_MAX_PARAM_KEY
_KEEL_CONFIGURATION_KEY = KEEL_CONFIGURATION_PARAM_KEY
_LOA_MIN_KEY = LOA_MIN_PARAM_KEY
_LOA_MAX_KEY = LOA_MAX_PARAM_KEY
_RUDDER_CONFIGURATION_KEY = RUDDER_CONFIGURATION_PARAM_KEY
_HULL_CONFIGURATION_KEY = HULL_CONFIGURATION_PARAM_KEY
_COCKPIT_POSITION_KEY = COCKPIT_POSITION_PARAM_KEY
_DECK_SALOON_KEY = DECK_SALOON_PARAM_KEY
_BEAM_MIN_KEY = BEAM_MIN_PARAM_KEY
_BEAM_MAX_KEY = BEAM_MAX_PARAM_KEY
_HULL_MATERIAL_KEY = HULL_MATERIAL_PARAM_KEY
_ALLOWED_SCENARIO_KEYS = SUPPORTED_PARAM_KEYS


class InvalidSearchFitScenarioError(ValueError):
    """Raised when the raw Search-fit scenario query parameters fail the
    bounded lexical/vocabulary envelope (Required Behavior §A/§2)."""


@dataclass(frozen=True, slots=True)
class SearchFitScenario:
    """The bounded, parsed Search-fit scenario (SLICE-0085: extends the
    original `draft_max`/`keel_configuration` pair to the full accepted
    multi-criterion whitelist)."""

    draft_max: Decimal | None = None
    keel_configuration: str | None = None
    loa_min: Decimal | None = None
    loa_max: Decimal | None = None
    rudder_configuration: str | None = None
    hull_configuration: str | None = None
    cockpit_position: str | None = None
    deck_saloon: str | None = None
    beam_min: Decimal | None = None
    beam_max: Decimal | None = None
    hull_material: str | None = None


def _parse_single_valued(
    label: str, raw_values: Sequence[str], parsed: tuple[Any, bool] | None
) -> Any:
    """Shared "exactly-once, canonical-or-fail-closed" rule every scenario
    criterion follows (review amendment Finding C: driven by
    `hullq.search.criteria_registry.parse_numeric_param`/
    `parse_categorical_param`'s shared `(value, is_single_canonical) | None`
    convention). Unlike the public canonical-URL surface, this private
    preview has no redirect identity -- ANY non-single-canonical input
    (duplicate, even of an identical value, or a non-canonical spelling)
    fails closed directly, never silently normalized.
    """
    if parsed is None:
        raise InvalidSearchFitScenarioError(f"{label} is not a supported/valid value")
    value, is_single_canonical = parsed
    if value is None:
        return None
    if len(raw_values) > 1:
        raise InvalidSearchFitScenarioError(f"{label} must be supplied exactly once")
    if not is_single_canonical:
        raise InvalidSearchFitScenarioError(f"{label} {raw_values[0]!r} is not in canonical form")
    return value


def parse_search_fit_scenario(query_params: Mapping[str, Sequence[str]]) -> SearchFitScenario:
    """Parse the bounded multi-criterion scenario, or raise.

    *query_params* maps each raw query key to every raw value it carried
    (preserving duplicates), independent of any HTTP framework -- mirrors
    `hullq.application.search_read.evaluate_search_request`'s own calling
    convention. Reuses the exact public per-value validation
    (`hullq.search.criteria_registry.parse_numeric_param`/
    `parse_categorical_param`, driven by each `CriterionDefinition`'s own
    `parse_value`/`allowed_values` -- so an unauthorized value such as
    `LONG_KEEL` is never silently accepted merely because it is valid
    `PhysicalBoat` claim vocabulary). Unlike the public canonical-URL Search
    surface, this is a private single-target JSON preview with no
    canonical-URL identity to redirect to -- a non-canonical spelling, any
    duplicate (even of an identical value), an unknown parameter key, an
    invalid `loa_min > loa_max` range or an entirely empty scenario all fail
    closed directly as `InvalidSearchFitScenarioError` (Required Behavior
    §A/§2).
    """
    unknown_keys = set(query_params) - _ALLOWED_SCENARIO_KEYS
    if unknown_keys:
        raise InvalidSearchFitScenarioError(
            f"unsupported scenario parameter(s): {sorted(unknown_keys)}"
        )

    draft_raw_values = list(query_params.get(_DRAFT_MAX_KEY, ()))
    keel_raw_values = list(query_params.get(_KEEL_CONFIGURATION_KEY, ()))
    loa_min_raw_values = list(query_params.get(_LOA_MIN_KEY, ()))
    loa_max_raw_values = list(query_params.get(_LOA_MAX_KEY, ()))
    rudder_raw_values = list(query_params.get(_RUDDER_CONFIGURATION_KEY, ()))
    hull_raw_values = list(query_params.get(_HULL_CONFIGURATION_KEY, ()))
    cockpit_raw_values = list(query_params.get(_COCKPIT_POSITION_KEY, ()))
    deck_saloon_raw_values = list(query_params.get(_DECK_SALOON_KEY, ()))
    beam_min_raw_values = list(query_params.get(_BEAM_MIN_KEY, ()))
    beam_max_raw_values = list(query_params.get(_BEAM_MAX_KEY, ()))
    hull_material_raw_values = list(query_params.get(_HULL_MATERIAL_KEY, ()))
    if not (
        draft_raw_values
        or keel_raw_values
        or loa_min_raw_values
        or loa_max_raw_values
        or rudder_raw_values
        or hull_raw_values
        or cockpit_raw_values
        or deck_saloon_raw_values
        or beam_min_raw_values
        or beam_max_raw_values
        or hull_material_raw_values
    ):
        raise InvalidSearchFitScenarioError("at least one scenario criterion is required")

    draft_max = _parse_single_valued(
        _DRAFT_MAX_KEY,
        draft_raw_values,
        parse_numeric_param(DRAFT_MAX_DEFINITION, draft_raw_values),
    )
    keel_configuration = _parse_single_valued(
        _KEEL_CONFIGURATION_KEY,
        keel_raw_values,
        parse_categorical_param(KEEL_CONFIGURATION_DEFINITION, keel_raw_values),
    )
    loa_min = _parse_single_valued(
        _LOA_MIN_KEY, loa_min_raw_values, parse_numeric_param(LOA_DEFINITION, loa_min_raw_values)
    )
    loa_max = _parse_single_valued(
        _LOA_MAX_KEY, loa_max_raw_values, parse_numeric_param(LOA_DEFINITION, loa_max_raw_values)
    )
    if loa_min is not None and loa_max is not None and loa_min > loa_max:
        raise InvalidSearchFitScenarioError(f"loa_min ({loa_min}) must be <= loa_max ({loa_max})")
    rudder_configuration = _parse_single_valued(
        _RUDDER_CONFIGURATION_KEY,
        rudder_raw_values,
        parse_categorical_param(RUDDER_CONFIGURATION_DEFINITION, rudder_raw_values),
    )
    hull_configuration = _parse_single_valued(
        _HULL_CONFIGURATION_KEY,
        hull_raw_values,
        parse_categorical_param(HULL_CONFIGURATION_DEFINITION, hull_raw_values),
    )
    cockpit_position = _parse_single_valued(
        _COCKPIT_POSITION_KEY,
        cockpit_raw_values,
        parse_categorical_param(COCKPIT_POSITION_DEFINITION, cockpit_raw_values),
    )
    deck_saloon = _parse_single_valued(
        _DECK_SALOON_KEY,
        deck_saloon_raw_values,
        parse_categorical_param(DECK_SALOON_DEFINITION, deck_saloon_raw_values),
    )
    beam_min = _parse_single_valued(
        _BEAM_MIN_KEY,
        beam_min_raw_values,
        parse_numeric_param(BEAM_DEFINITION, beam_min_raw_values),
    )
    beam_max = _parse_single_valued(
        _BEAM_MAX_KEY,
        beam_max_raw_values,
        parse_numeric_param(BEAM_DEFINITION, beam_max_raw_values),
    )
    if beam_min is not None and beam_max is not None and beam_min > beam_max:
        raise InvalidSearchFitScenarioError(
            f"beam_min ({beam_min}) must be <= beam_max ({beam_max})"
        )
    hull_material = _parse_single_valued(
        _HULL_MATERIAL_KEY,
        hull_material_raw_values,
        parse_categorical_param(HULL_MATERIAL_DEFINITION, hull_material_raw_values),
    )

    return SearchFitScenario(
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        beam_min=beam_min,
        beam_max=beam_max,
        hull_material=hull_material,
    )


class SearchFitOutcome(StrEnum):
    """Mechanically distinct outcomes. Never a bare boolean or a false
    `OK`-shaped result for a denied/invalid/not-previewable/faulted attempt."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_SCENARIO = "INVALID_SCENARIO"
    NOT_PREVIEWABLE = "NOT_PREVIEWABLE"
    CHAIN_INTEGRITY_FAULT = "CHAIN_INTEGRITY_FAULT"
    OK = "OK"


class SearchFitBlocker(StrEnum):
    """Deterministic, actionable `INSUFFICIENT_DATA` blockers (Required
    Behavior §D). Each maps to exactly one existing broker editing surface:
    `BOATDESIGN_NOT_LINKED`/`BOATDESIGN_CONFIGURATION_UNRESOLVED` to the
    existing 0082 design selector, `CONCRETE_DRAFT_UNCONFIRMED`/
    `KEEL_CONFIGURATION_UNCONFIRMED`/`LOA_UNCONFIRMED` (SLICE-0085)/
    `RUDDER_CONFIGURATION_UNCONFIRMED` (SLICE-0085)/`HULL_CONFIGURATION_
    UNCONFIRMED`/`COCKPIT_POSITION_UNCONFIRMED`/`DECK_SALOON_UNCONFIRMED`
    (SLICE-0086)/`BEAM_UNCONFIRMED`/`HULL_MATERIAL_UNCONFIRMED` (SLICE-0087)
    to the existing 0072 claim editor."""

    BOATDESIGN_NOT_LINKED = "BOATDESIGN_NOT_LINKED"
    BOATDESIGN_CONFIGURATION_UNRESOLVED = "BOATDESIGN_CONFIGURATION_UNRESOLVED"
    CONCRETE_DRAFT_UNCONFIRMED = "CONCRETE_DRAFT_UNCONFIRMED"
    KEEL_CONFIGURATION_UNCONFIRMED = "KEEL_CONFIGURATION_UNCONFIRMED"
    LOA_UNCONFIRMED = "LOA_UNCONFIRMED"
    RUDDER_CONFIGURATION_UNCONFIRMED = "RUDDER_CONFIGURATION_UNCONFIRMED"
    HULL_CONFIGURATION_UNCONFIRMED = "HULL_CONFIGURATION_UNCONFIRMED"
    COCKPIT_POSITION_UNCONFIRMED = "COCKPIT_POSITION_UNCONFIRMED"
    DECK_SALOON_UNCONFIRMED = "DECK_SALOON_UNCONFIRMED"
    BEAM_UNCONFIRMED = "BEAM_UNCONFIRMED"
    HULL_MATERIAL_UNCONFIRMED = "HULL_MATERIAL_UNCONFIRMED"


@dataclass(frozen=True)
class SearchFitView:
    """One evaluated hypothetical DRAFT Search-fit preview.

    `design_evaluation` is `None` only when `boat_design_ref` itself is
    unresolved (`blockers == (BOATDESIGN_NOT_LINKED,)`) -- the design/
    configuration funnel was never reached at all, mirroring `hullq.
    application.native_inventory_query`'s own dangling/absent-link
    treatment. Otherwise it is the complete, unmodified `DesignQueryEvaluation`
    for this listing's linked BoatDesign, present even when `result_class`
    is `CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` at the design level.
    `concrete_criterion_evidence` is populated only when the design level is
    itself a `CONFIRMED_MATCH` (Required Behavior §B): design/configuration
    eligibility alone never confirms a concrete listed yacht.

    `vessel_category_exclusion` is populated only when the SLICE-0091 §C
    category pre-filter itself produced this `CONFIRMED_NON_MATCH` -- `None`
    in every other case. Amendment review Finding I: without this, a broker
    previewing their own DRAFT listing against this exact pre-filter saw a
    bare `CONFIRMED_NON_MATCH` mechanically indistinguishable from an
    ordinary technical mismatch, with zero explanation. Deliberately the
    bounded, cross-Organization-identity-free `VesselCategoryExclusionEvidence`
    (see that type's docstring) -- never the full resolution result, even
    though this preview is already scoped to the owning broker's own
    listing, since the full result's `concrete_evidence` can still name a
    *different* claiming Organization under `CROSS_ORGANIZATION_DISAGREEMENT`.
    """

    native_listing_id: str
    draft_max: Decimal | None
    keel_configuration: str | None
    loa_min: Decimal | None
    loa_max: Decimal | None
    rudder_configuration: str | None
    hull_configuration: str | None
    cockpit_position: str | None
    deck_saloon: str | None
    beam_min: Decimal | None
    beam_max: Decimal | None
    hull_material: str | None
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation | None
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
    vessel_category_exclusion: VesselCategoryExclusionEvidence | None
    blockers: tuple[SearchFitBlocker, ...]


@dataclass(frozen=True)
class SearchFitResult:
    outcome: SearchFitOutcome
    view: SearchFitView | None = None
    invalid_reason: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is SearchFitOutcome.OK:
            if self.view is None:
                raise ValueError("An OK Search-fit result must carry a view")
        elif self.view is not None:
            raise ValueError("Only an OK Search-fit result may carry a view")

        if self.outcome is SearchFitOutcome.INVALID_SCENARIO:
            if self.invalid_reason is None:
                raise ValueError("An INVALID_SCENARIO result must carry invalid_reason")
        elif self.invalid_reason is not None:
            raise ValueError("Only an INVALID_SCENARIO result may carry invalid_reason")


def _derive_blockers(
    result_class: ResultClass, concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
) -> tuple[SearchFitBlocker, ...]:
    """Map an `INSUFFICIENT_DATA` classification to its actionable, existing-
    editor-scoped blocker(s); `CONFIRMED_MATCH`/`CONFIRMED_NON_MATCH` never
    carry a blocker (a true positive needs no fix, and a true negative's
    "fix" would be inventing a different answer, not editing data)."""
    if result_class is not ResultClass.INSUFFICIENT_DATA:
        return ()
    if not concrete_criterion_evidence:
        # Design/configuration eligibility itself never admitted this design
        # to the concrete PhysicalBoat claim funnel (Required Behavior §C) --
        # a broker cannot directly edit BoatDesign FieldResolution, only
        # confirm the correct canonical model/variant is linked.
        return (SearchFitBlocker.BOATDESIGN_CONFIGURATION_UNRESOLVED,)
    blockers: list[SearchFitBlocker] = []
    seen: set[SearchFitBlocker] = set()
    for evidence in concrete_criterion_evidence:
        if evidence.evaluation.truth is not TruthState.UNKNOWN:
            continue
        blocker: SearchFitBlocker | None = None
        if evidence.criterion.field == DRAFT_MAX_DEFINITION.projection_field:
            blocker = SearchFitBlocker.CONCRETE_DRAFT_UNCONFIRMED
        elif evidence.criterion.field == KEEL_CONFIGURATION_DEFINITION.projection_field:
            blocker = SearchFitBlocker.KEEL_CONFIGURATION_UNCONFIRMED
        elif evidence.criterion.field == LOA_DEFINITION.projection_field:
            blocker = SearchFitBlocker.LOA_UNCONFIRMED
        elif evidence.criterion.field == RUDDER_CONFIGURATION_DEFINITION.projection_field:
            blocker = SearchFitBlocker.RUDDER_CONFIGURATION_UNCONFIRMED
        elif evidence.criterion.field == HULL_CONFIGURATION_DEFINITION.projection_field:
            blocker = SearchFitBlocker.HULL_CONFIGURATION_UNCONFIRMED
        elif evidence.criterion.field == COCKPIT_POSITION_DEFINITION.projection_field:
            blocker = SearchFitBlocker.COCKPIT_POSITION_UNCONFIRMED
        elif evidence.criterion.field == DECK_SALOON_DEFINITION.projection_field:
            blocker = SearchFitBlocker.DECK_SALOON_UNCONFIRMED
        elif evidence.criterion.field == BEAM_DEFINITION.projection_field:
            blocker = SearchFitBlocker.BEAM_UNCONFIRMED
        elif evidence.criterion.field == HULL_MATERIAL_DEFINITION.projection_field:
            blocker = SearchFitBlocker.HULL_MATERIAL_UNCONFIRMED
        if blocker is not None and blocker not in seen:
            # LOA may contribute two leaves (loa_min/loa_max) against the
            # same field -- a single actionable blocker, never duplicated.
            seen.add(blocker)
            blockers.append(blocker)
    return tuple(blockers)


def _authorize_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> SearchFitResult | None:
    """Evaluate the current workspace + PUBLISHER-role authorization boundary
    (Required Behavior §C), returning `None` when authorized to proceed or
    the exact denial `SearchFitResult` otherwise.

    Called twice by `evaluate_organization_listing_search_fit` -- once from
    inside the bounded `REPEATABLE READ` snapshot the rest of the evaluation
    reads from, and once more immediately after that snapshot closes, from a
    deliberately fresh statement against the now-current committed state
    (independent review Finding A, PR #342): an Organization membership
    revoked, or its PUBLISHER role removed, while the first evaluation was
    in flight is caught by the second call rather than silently legitimizing
    a stale authorization decision. A module-level function (not inlined) so
    both call sites -- and a test harness pausing/monkeypatching exactly the
    second call to inject a real concurrent mutation -- share the identical
    authorization logic.
    """
    workspace_result = get_organization_workspace_result(conn, session, organization_id)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.NOT_FOUND_OR_DENIED:
        return SearchFitResult(outcome=SearchFitOutcome.ORG_NOT_FOUND_OR_DENIED)
    if workspace_result.outcome is OrganizationWorkspaceOutcome.MFA_REQUIRED:
        return SearchFitResult(outcome=SearchFitOutcome.MFA_REQUIRED)
    assert workspace_result.context is not None

    # `evaluate_organization_workspace_authorization` already guarantees an
    # AUTHORIZED outcome's membership is current and ACTIVE -- only the
    # PUBLISHER-role requirement this preview's own contract adds (Required
    # Behavior §C) still needs checking, from the same authorized read.
    if MembershipRole.PUBLISHER.value not in workspace_result.context.roles:
        return SearchFitResult(outcome=SearchFitOutcome.PUBLISHER_ROLE_REQUIRED)
    return None


def evaluate_organization_listing_search_fit(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    query_params: Mapping[str, Sequence[str]],
    *,
    as_of: datetime,
) -> SearchFitResult:
    """Evaluate one authorized, owned, lifecycle-DRAFT NativeListing against
    one bounded synthetic multi-criterion scenario (`draft_max`/
    `keel_configuration`/`loa_min`/`loa_max`/`rudder_configuration`,
    SLICE-0085).

    *as_of* is accepted for calling-convention parity with every other
    SLICE-0051+ Search/eligibility evaluator in this codebase; this preview
    does not itself consult D29 current-public-eligibility or freshness --
    lifecycle alone (never ACTIVE/WITHDRAWN) gates whether a hypothetical
    DRAFT preview may run at all (Required Behavior §B/§C).

    *conn* must be IDLE (no prior statement issued) when this function
    receives it -- it opens its own top-level `REPEATABLE READ` transaction
    for the snapshot read (see this module's docstring, independent review
    Finding A).
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    native_listing_id = NativeListingId(native_listing_id_value)

    try:
        scenario = parse_search_fit_scenario(query_params)
    except InvalidSearchFitScenarioError as exc:
        return SearchFitResult(outcome=SearchFitOutcome.INVALID_SCENARIO, invalid_reason=str(exc))
    draft_max = scenario.draft_max
    keel_configuration = scenario.keel_configuration
    loa_min = scenario.loa_min
    loa_max = scenario.loa_max
    rudder_configuration = scenario.rudder_configuration
    hull_configuration = scenario.hull_configuration
    cockpit_position = scenario.cockpit_position
    deck_saloon = scenario.deck_saloon
    beam_min = scenario.beam_min
    beam_max = scenario.beam_max
    hull_material = scenario.hull_material

    query, active_definitions = build_mixed_requirement_query(
        draft_max=draft_max,
        keel_configuration=keel_configuration,
        loa_min=loa_min,
        loa_max=loa_max,
        rudder_configuration=rudder_configuration,
        hull_configuration=hull_configuration,
        cockpit_position=cockpit_position,
        deck_saloon=deck_saloon,
        beam_min=beam_min,
        beam_max=beam_max,
        hull_material=hull_material,
    )

    # Finding A: every read needed to assemble a would-be OK result shares
    # one consistent MVCC snapshot, fixed at the first statement below.
    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

        denial = _authorize_actor(conn, session, organization_id)
        if denial is not None:
            return denial

        listing_record = fetch_native_listing(conn, native_listing_id)
        if listing_record is None or listing_record.publishing_organization_id != organization_id:
            return SearchFitResult(outcome=SearchFitOutcome.LISTING_NOT_FOUND)

        lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
        assert lifecycle_state is not None  # the listing was just confirmed to exist, above
        if lifecycle_state is not NativeListingLifecycleState.DRAFT:
            return SearchFitResult(outcome=SearchFitOutcome.NOT_PREVIEWABLE)

        market_episode_id = listing_record.listing.market_episode_id
        if market_episode_id is None:
            # A listing that completed 0067 promotion always carries a
            # MarketEpisode -- a promoted DRAFT target missing one is a
            # broken identity chain, not an ordinary recoverable editing gap.
            return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)
        market_episode_record = fetch_market_episode(conn, market_episode_id)
        if market_episode_record is None:
            return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)
        physical_boat_id = market_episode_record.market_episode.physical_boat_id
        physical_boat_record = fetch_physical_boat(conn, physical_boat_id)
        if physical_boat_record is None:
            return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)

        boat_design_ref = physical_boat_record.physical_boat.boat_design_ref

        if boat_design_ref is None:
            view = SearchFitView(
                native_listing_id=native_listing_id.value,
                draft_max=draft_max,
                keel_configuration=keel_configuration,
                loa_min=loa_min,
                loa_max=loa_max,
                rudder_configuration=rudder_configuration,
                hull_configuration=hull_configuration,
                cockpit_position=cockpit_position,
                deck_saloon=deck_saloon,
                beam_min=beam_min,
                beam_max=beam_max,
                hull_material=hull_material,
                result_class=ResultClass.INSUFFICIENT_DATA,
                design_evaluation=None,
                design_configuration_evidence=(),
                concrete_criterion_evidence=(),
                vessel_category_exclusion=None,
                blockers=(SearchFitBlocker.BOATDESIGN_NOT_LINKED,),
            )
        else:
            raw_design = fetch_boat_design(conn, boat_design_ref.value)
            if raw_design is None:
                # Dangling BoatDesignRef: a stored link to a non-existent
                # canonical design is a data-integrity error, never an
                # inferred/guessed design (Required Behavior §B).
                return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)

            design_result = run_mixed_boat_design_configuration_query(
                conn, query, [raw_design], active_definitions
            )
            design_evaluations = (
                design_result.outcome.confirmed_matches
                + design_result.outcome.confirmed_non_matches
                + design_result.outcome.insufficient_data
            )
            assert len(design_evaluations) == 1  # exactly one design was evaluated, above
            design_evaluation = design_evaluations[0]

            design_configuration_evidence = tuple(
                build_configuration_evidence(
                    query,
                    configuration_evaluation,
                    design_result.configurations_by_id[configuration_evaluation.configuration_id],
                )
                for configuration_evaluation in design_evaluation.configuration_evaluations
            )

            # Explicit annotation: a bare `()` literal below would otherwise
            # be inferred as the empty-tuple type `tuple[()]`, conflicting
            # with the `tuple[SearchCriterionEvidence, ...]`
            # `classify_concrete_candidate` assigns in the sibling branch.
            concrete_evidence: tuple[SearchCriterionEvidence, ...]
            if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
                # SLICE-0091 §A/§C: identical fail-closed category pre-filter
                # as the public native-inventory funnel
                # (`hullq.application.native_inventory_query.
                # evaluate_native_inventory_requirements`) -- this private
                # DRAFT preview must never show a broker a confirmed Sail
                # match for a vessel explicitly categorized POWER/
                # MOTORSAILER, or caught in an unresolved design/concrete
                # category CONFLICT.
                category_resolution = resolve_physical_boat_vessel_category(
                    conn, physical_boat_id=physical_boat_id, boat_design_ref=boat_design_ref
                )
                if category_resolution.is_explicitly_non_sail_or_conflicted:
                    result_class = ResultClass.CONFIRMED_NON_MATCH
                    concrete_evidence = ()
                    # Amendment Finding I: retain *why* -- bounded, enum-only,
                    # never the full result (which can name a different
                    # claiming Organization under
                    # CROSS_ORGANIZATION_DISAGREEMENT).
                    vessel_category_exclusion = VesselCategoryExclusionEvidence(
                        resolution=category_resolution.resolution,
                        reason=category_resolution.reason,
                    )
                else:
                    result_class, concrete_evidence = classify_concrete_candidate(
                        conn,
                        native_listing_id=native_listing_id,
                        publishing_organization_id=organization_id,
                        physical_boat_id=physical_boat_id,
                        boat_design_id=boat_design_ref.value,
                        query=query,
                        active_definitions=active_definitions,
                    )
                    vessel_category_exclusion = None
            else:
                # Design/configuration eligibility never admitted this
                # design to the concrete funnel (Required Behavior §B) --
                # classified directly from the design-level result, fail-
                # closed, without ever consulting the concrete claim.
                result_class = design_evaluation.result_class
                concrete_evidence = ()
                vessel_category_exclusion = None

            view = SearchFitView(
                native_listing_id=native_listing_id.value,
                draft_max=draft_max,
                keel_configuration=keel_configuration,
                loa_min=loa_min,
                loa_max=loa_max,
                rudder_configuration=rudder_configuration,
                hull_configuration=hull_configuration,
                cockpit_position=cockpit_position,
                deck_saloon=deck_saloon,
                beam_min=beam_min,
                beam_max=beam_max,
                hull_material=hull_material,
                result_class=result_class,
                design_evaluation=design_evaluation,
                design_configuration_evidence=design_configuration_evidence,
                concrete_criterion_evidence=concrete_evidence,
                vessel_category_exclusion=vessel_category_exclusion,
                blockers=_derive_blockers(result_class, concrete_evidence),
            )
    # The snapshot transaction above committed trivially (read-only) on
    # normal exit, including every early-return branch -- mirrors
    # `hullq.persistence.native_listing_lifecycle._apply_transition`'s
    # identical multiple-early-return-inside-`with conn.transaction():`
    # convention.

    # Finding A (second half): a completely fresh, independent recheck --
    # new statements against the now-current committed state, never the
    # snapshot above -- so an interleaved revoke/role-change/publish/
    # withdraw during evaluation is caught here, not silently used to
    # legitimize a stale OK.
    recheck_denial = _authorize_actor(conn, session, organization_id)
    if recheck_denial is not None:
        return recheck_denial
    recheck_lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    if recheck_lifecycle_state is not NativeListingLifecycleState.DRAFT:
        return SearchFitResult(outcome=SearchFitOutcome.NOT_PREVIEWABLE)

    return SearchFitResult(outcome=SearchFitOutcome.OK, view=view)
