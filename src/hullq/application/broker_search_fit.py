"""Broker-facing authorized single-target hypothetical DRAFT Search-fit preview — SLICE-0084.

Implements REQ-BROKER-026/MVP-BROKER-010: given exactly one authorized
Organization-owned, lifecycle-`DRAFT` NativeListing and a bounded, explicitly
synthetic `draft_max`/`keel_configuration` scenario, produce the same
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
    hullq.search.boat_design_field_bridge.run_boat_design_configuration_query
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

Mechanical invariants §C (stale/concurrent-state): lifecycle is read once
before any technical evaluation and re-read once more immediately before
returning a would-be `OK` result; an interleaved publish/withdraw between
the two reads returns `NOT_PREVIEWABLE` rather than a DRAFT-labelled result
assembled from two different state moments. This is the accepted "equivalent
bounded recheck" strategy (contract §C), not a held transaction/row lock --
the preview performs zero writes, so there is no mutation to serialize
against.
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
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId, MembershipRole
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.search.boat_design_field_bridge import run_boat_design_configuration_query
from hullq.search.configuration_engine import DesignQueryEvaluation
from hullq.search.draft_max_design_bridge import DRAFT_MAX_PROJECTION_FIELD
from hullq.search.draft_max_request import (
    DraftMaxSyntaxError,
    canonical_draft_max_str,
    parse_draft_max_decimal,
)
from hullq.search.keel_design_bridge import (
    KEEL_CONFIGURATION_PROJECTION_FIELD,
    SEARCH_KEEL_CONFIGURATION_VALUES,
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

_DRAFT_MAX_KEY = "draft_max"
_KEEL_CONFIGURATION_KEY = "keel_configuration"
_ALLOWED_SCENARIO_KEYS = frozenset({_DRAFT_MAX_KEY, _KEEL_CONFIGURATION_KEY})


class InvalidSearchFitScenarioError(ValueError):
    """Raised when the raw Search-fit scenario query parameters fail the
    bounded lexical/vocabulary envelope (Required Behavior §A/§2)."""


def parse_search_fit_scenario(
    query_params: Mapping[str, Sequence[str]],
) -> tuple[Decimal | None, str | None]:
    """Parse the bounded `draft_max`/`keel_configuration` scenario, or raise.

    *query_params* maps each raw query key to every raw value it carried
    (preserving duplicates), independent of any HTTP framework -- mirrors
    `hullq.application.search_read.evaluate_search_request`'s own calling
    convention. Reuses the exact public v0.1 per-value validation (`hullq.
    search.draft_max_request.parse_draft_max_decimal`'s bounded lexical
    envelope; `hullq.search.keel_design_bridge.
    SEARCH_KEEL_CONFIGURATION_VALUES` exact-set membership, so an
    unauthorized value such as `LONG_KEEL` is never silently accepted merely
    because it is valid `PhysicalBoat` claim vocabulary). Unlike the public
    canonical-URL Search surface, this is a private single-target JSON
    preview with no canonical-URL identity to redirect to -- a non-canonical
    `draft_max` spelling, any duplicate (even of an identical value), an
    unknown parameter key, a third criterion or an entirely empty scenario
    all fail closed directly as `InvalidSearchFitScenarioError` (Required
    Behavior §A/§2).
    """
    unknown_keys = set(query_params) - _ALLOWED_SCENARIO_KEYS
    if unknown_keys:
        raise InvalidSearchFitScenarioError(
            f"unsupported scenario parameter(s): {sorted(unknown_keys)}"
        )

    draft_raw_values = list(query_params.get(_DRAFT_MAX_KEY, ()))
    keel_raw_values = list(query_params.get(_KEEL_CONFIGURATION_KEY, ()))
    if not draft_raw_values and not keel_raw_values:
        raise InvalidSearchFitScenarioError(
            "at least one of draft_max/keel_configuration is required"
        )

    draft_max: Decimal | None = None
    if draft_raw_values:
        if len(draft_raw_values) > 1:
            raise InvalidSearchFitScenarioError("draft_max must be supplied exactly once")
        raw = draft_raw_values[0]
        try:
            draft_max = parse_draft_max_decimal(raw)
        except DraftMaxSyntaxError as exc:
            raise InvalidSearchFitScenarioError(str(exc)) from exc
        if raw != canonical_draft_max_str(draft_max):
            raise InvalidSearchFitScenarioError(f"draft_max {raw!r} is not in canonical form")

    keel_configuration: str | None = None
    if keel_raw_values:
        if len(keel_raw_values) > 1:
            raise InvalidSearchFitScenarioError("keel_configuration must be supplied exactly once")
        raw = keel_raw_values[0]
        if raw not in SEARCH_KEEL_CONFIGURATION_VALUES:
            raise InvalidSearchFitScenarioError(
                f"keel_configuration {raw!r} is not a supported public value"
            )
        keel_configuration = raw

    return draft_max, keel_configuration


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
    `KEEL_CONFIGURATION_UNCONFIRMED` to the existing 0072 claim editor."""

    BOATDESIGN_NOT_LINKED = "BOATDESIGN_NOT_LINKED"
    BOATDESIGN_CONFIGURATION_UNRESOLVED = "BOATDESIGN_CONFIGURATION_UNRESOLVED"
    CONCRETE_DRAFT_UNCONFIRMED = "CONCRETE_DRAFT_UNCONFIRMED"
    KEEL_CONFIGURATION_UNCONFIRMED = "KEEL_CONFIGURATION_UNCONFIRMED"


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
    """

    native_listing_id: str
    draft_max: Decimal | None
    keel_configuration: str | None
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation | None
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
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
    for evidence in concrete_criterion_evidence:
        if evidence.evaluation.truth is not TruthState.UNKNOWN:
            continue
        if evidence.criterion.field == DRAFT_MAX_PROJECTION_FIELD:
            blockers.append(SearchFitBlocker.CONCRETE_DRAFT_UNCONFIRMED)
        elif evidence.criterion.field == KEEL_CONFIGURATION_PROJECTION_FIELD:
            blockers.append(SearchFitBlocker.KEEL_CONFIGURATION_UNCONFIRMED)
    return tuple(blockers)


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
    one bounded synthetic `draft_max`/`keel_configuration` scenario.

    *as_of* is accepted for calling-convention parity with every other
    SLICE-0051+ Search/eligibility evaluator in this codebase; this preview
    does not itself consult D29 current-public-eligibility or freshness --
    lifecycle alone (never ACTIVE/WITHDRAWN) gates whether a hypothetical
    DRAFT preview may run at all (Required Behavior §B/§C).
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
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

    try:
        draft_max, keel_configuration = parse_search_fit_scenario(query_params)
    except InvalidSearchFitScenarioError as exc:
        return SearchFitResult(outcome=SearchFitOutcome.INVALID_SCENARIO, invalid_reason=str(exc))

    native_listing_id = NativeListingId(native_listing_id_value)
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
        # MarketEpisode -- a promoted DRAFT target missing one is a broken
        # identity chain, not an ordinary recoverable editing gap.
        return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)
    market_episode_record = fetch_market_episode(conn, market_episode_id)
    if market_episode_record is None:
        return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)
    physical_boat_id = market_episode_record.market_episode.physical_boat_id
    physical_boat_record = fetch_physical_boat(conn, physical_boat_id)
    if physical_boat_record is None:
        return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)

    query, specs = build_mixed_requirement_query(
        draft_max=draft_max, keel_configuration=keel_configuration
    )
    boat_design_ref = physical_boat_record.physical_boat.boat_design_ref

    if boat_design_ref is None:
        view = SearchFitView(
            native_listing_id=native_listing_id.value,
            draft_max=draft_max,
            keel_configuration=keel_configuration,
            result_class=ResultClass.INSUFFICIENT_DATA,
            design_evaluation=None,
            design_configuration_evidence=(),
            concrete_criterion_evidence=(),
            blockers=(SearchFitBlocker.BOATDESIGN_NOT_LINKED,),
        )
    else:
        raw_design = fetch_boat_design(conn, boat_design_ref.value)
        if raw_design is None:
            # Dangling BoatDesignRef: a stored link to a non-existent
            # canonical design is a data-integrity error, never an
            # inferred/guessed design (Required Behavior §B).
            return SearchFitResult(outcome=SearchFitOutcome.CHAIN_INTEGRITY_FAULT)

        design_result = run_boat_design_configuration_query(conn, query, [raw_design], specs)
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

        if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
            result_class, concrete_evidence = classify_concrete_candidate(
                conn,
                native_listing_id=native_listing_id,
                publishing_organization_id=organization_id,
                physical_boat_id=physical_boat_id,
                boat_design_id=boat_design_ref.value,
                query=query,
                draft_active=draft_max is not None,
                keel_active=keel_configuration is not None,
            )
        else:
            # Design/configuration eligibility never admitted this design to
            # the concrete funnel (Required Behavior §B) -- classified
            # directly from the design-level result, fail-closed, without
            # ever consulting the concrete PhysicalBoat claim.
            result_class = design_evaluation.result_class
            concrete_evidence = ()

        view = SearchFitView(
            native_listing_id=native_listing_id.value,
            draft_max=draft_max,
            keel_configuration=keel_configuration,
            result_class=result_class,
            design_evaluation=design_evaluation,
            design_configuration_evidence=design_configuration_evidence,
            concrete_criterion_evidence=concrete_evidence,
            blockers=_derive_blockers(result_class, concrete_evidence),
        )

    # Mechanical invariants §C: never let an interleaved publish/withdraw
    # leave a DRAFT-labelled result assembled from two different state
    # moments -- the bounded recheck the contract accepts in place of a
    # held read lock for this read-only, zero-write preview.
    recheck_lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    if recheck_lifecycle_state is not NativeListingLifecycleState.DRAFT:
        return SearchFitResult(outcome=SearchFitOutcome.NOT_PREVIEWABLE)

    return SearchFitResult(outcome=SearchFitOutcome.OK, view=view)
