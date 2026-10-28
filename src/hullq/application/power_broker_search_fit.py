"""Broker-facing authorized single-target hypothetical DRAFT Power
Search-fit preview — SLICE-0095.

Implements `specs/POWER_BROKER_SEARCH_FIT_CONTRACT.v0.1.md`: given exactly
one authorized Organization-owned, lifecycle-`DRAFT` NativeListing and a
bounded scenario (`power_drive`/`power_engine_count`, either alone or
combined as MUST-AND), produce the same `CONFIRMED_MATCH`/
`CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` technical result the accepted
public Power Buyer Search kernel (`hullq.application.power_inventory_query`)
would produce for the identical facts -- read-only, never inserted into
public Search.

This module is the Power-domain structural counterpart of SLICE-0084's
`hullq.application.broker_search_fit`, not a mutation of it: the Sail-only
`/search-fit` endpoint, its parser and its result semantics are entirely
unchanged (contract Required Behavior §1). It introduces **no second Power
Search truth engine** -- every technical classification reuses the exact
accepted SLICE-0093/0094 primitives unchanged:

    hullq.application.power_inventory_query.build_power_query
    hullq.application.power_inventory_query.resolve_power_category_admission
    hullq.application.power_inventory_query
        .resolve_power_claim_only_category_from_observations
    hullq.application.power_inventory_query
        .downgrade_mixed_non_match_to_insufficient_data
    hullq.application.native_inventory_query.classify_claim_only_candidate
    hullq.application.native_inventory_query.classify_concrete_candidate
    hullq.application.native_inventory_query
        .run_mixed_boat_design_configuration_query
    hullq.application.native_inventory_query.build_configuration_evidence
    hullq.persistence.power_category_drive_snapshot
        .fetch_power_category_drive_snapshot

The only genuinely new responsibility here is resolving one *authorized,
owned* NativeListing's own NativeListing -> MarketEpisode -> PhysicalBoat
chain directly -- identical to `broker_search_fit`'s own chain resolution,
never through `hullq.persistence.inventory_search
.list_active_design_linked_listings`/`list_active_design_unresolved_listings`,
which enumerate only currently public ACTIVE candidates and would either
silently omit a lifecycle-DRAFT target or (worse) test D29/public eligibility
nobody asked this preview to test (contract §1: "Existing D29/public
eligibility must remain authoritative when the listing is eventually
published").

Design-unresolved treatment differs deliberately from the Sail preview
(contract §"Eligibility, current source, design and MVCC"): a missing
BoatDesign link is a legitimate **claim-only** evaluation path here, not a
blocker -- "Missing linked design is a legitimate claim-only path, not
inherently a missing-data blocker". A genuinely matching design-unresolved
offering can return `CONFIRMED_MATCH` with `source_basis=PUBLISHER_CLAIM`,
so unlike `broker_search_fit.SearchFitView`, this module's view never
carries a `BOATDESIGN_NOT_LINKED`-shaped blocker at all.

Authorization and the bounded scenario-parameter "exactly-once,
canonical-or-fail-closed" rule reuse
`hullq.application.broker_search_fit_support` directly -- the identical
generic logic SLICE-0084's own `_authorize_actor`/`_parse_single_valued`
originated, extracted so this Power preview never re-implements it
(Required Behavior §2).

Mechanical invariants §C (stale/concurrent-state; same discipline SLICE-0084
established): every read needed to assemble a would-be `OK` result --
authorization, lifecycle, the NativeListing -> MarketEpisode -> PhysicalBoat
chain, category admission and technical classification -- runs inside one
explicit `REPEATABLE READ` PostgreSQL transaction. Immediately after that
snapshot transaction closes, both authorization and lifecycle are rechecked
once more from deliberately fresh statements against the now-current
committed state, so a concurrent revocation, role removal or
DRAFT->ACTIVE/WITHDRAWN transition landing mid-evaluation never legitimizes
a stale `OK` result.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.broker_search_fit_support import (
    BrokerActorAuthorizationOutcome,
    evaluate_broker_actor_authorization,
    parse_single_valued_scenario_param,
)
from hullq.application.native_inventory_query import (
    ConfigurationEvidence,
    PublisherClaimSourceBasis,
    SearchCriterionEvidence,
    build_configuration_evidence,
    classify_claim_only_candidate,
    classify_concrete_candidate,
    run_mixed_boat_design_configuration_query,
)
from hullq.application.power_inventory_query import (
    PowerCategoryExclusionEvidence,
    build_power_query,
    downgrade_mixed_non_match_to_insufficient_data,
    resolve_power_category_admission,
    resolve_power_claim_only_category_from_observations,
)
from hullq.domain.market_identity import NativeListingId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
from hullq.domain.vessel_category import resolve_vessel_category
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.physical_boat import fetch_physical_boat
from hullq.persistence.physical_boat_claims import list_current_physical_boat_claim_observations
from hullq.persistence.power_category_drive_snapshot import fetch_power_category_drive_snapshot
from hullq.search.configuration_engine import DesignQueryEvaluation
from hullq.search.power_criteria_registry import (
    POWER_DRIVE_CONFIGURATION_DEFINITION,
    POWER_DRIVE_PARAM_KEY,
    POWER_ENGINE_COUNT_DEFINITION,
    POWER_ENGINE_COUNT_PARAM_KEY,
    SUPPORTED_POWER_PARAM_KEYS,
    parse_categorical_param,
    parse_numeric_param,
)
from hullq.search.types import ResultClass, TruthState
from hullq.security.session_token import SessionClaims

__all__ = [
    "InvalidPowerSearchFitScenarioError",
    "PowerSearchFitBlocker",
    "PowerSearchFitOutcome",
    "PowerSearchFitResult",
    "PowerSearchFitView",
    "evaluate_organization_listing_power_search_fit",
    "parse_power_search_fit_scenario",
]


class InvalidPowerSearchFitScenarioError(ValueError):
    """Raised when the raw Power Search-fit scenario query parameters fail
    the bounded lexical/vocabulary envelope (contract "Input and result
    contract")."""


@dataclass(frozen=True, slots=True)
class PowerSearchFitScenario:
    """The bounded, parsed Power Search-fit scenario -- `power_drive` and/or
    `power_engine_count`, mirroring `hullq.application.broker_search_fit
    .SearchFitScenario`'s identical shape for the Power domain's own two
    accepted criteria."""

    power_drive: str | None = None
    power_engine_count: Decimal | None = None


def parse_power_search_fit_scenario(
    query_params: Mapping[str, Sequence[str]],
) -> PowerSearchFitScenario:
    """Parse the bounded two-criterion Power scenario, or raise.

    *query_params* maps each raw query key to every raw value it carried
    (preserving duplicates), independent of any HTTP framework -- mirrors
    `hullq.application.broker_search_fit.parse_search_fit_scenario`'s
    identical calling convention. Reuses the exact public per-value
    validation (`hullq.search.power_criteria_registry.parse_categorical_param`/
    `parse_numeric_param`), so an unsupported value is never silently
    accepted merely because it is valid `PhysicalBoat` claim vocabulary (a
    current claim of 9-32 engines, or `MIXED`/`OTHER` drive, remains real
    claim vocabulary but is never an accepted scenario *input*). Unlike the
    public canonical-URL Power Search surface, this is a private
    single-target JSON preview with no canonical-URL identity to redirect
    to -- a non-canonical spelling, any duplicate (even of an identical
    value), an unknown parameter key, or an entirely empty scenario all fail
    closed directly as `InvalidPowerSearchFitScenarioError`.
    """
    unknown_keys = set(query_params) - SUPPORTED_POWER_PARAM_KEYS
    if unknown_keys:
        raise InvalidPowerSearchFitScenarioError(
            f"unsupported scenario parameter(s): {sorted(unknown_keys)}"
        )

    drive_raw_values = list(query_params.get(POWER_DRIVE_PARAM_KEY, ()))
    count_raw_values = list(query_params.get(POWER_ENGINE_COUNT_PARAM_KEY, ()))
    if not (drive_raw_values or count_raw_values):
        raise InvalidPowerSearchFitScenarioError("at least one scenario criterion is required")

    power_drive = parse_single_valued_scenario_param(
        POWER_DRIVE_PARAM_KEY,
        drive_raw_values,
        parse_categorical_param(POWER_DRIVE_CONFIGURATION_DEFINITION, drive_raw_values),
        error_type=InvalidPowerSearchFitScenarioError,
    )
    power_engine_count = parse_single_valued_scenario_param(
        POWER_ENGINE_COUNT_PARAM_KEY,
        count_raw_values,
        parse_numeric_param(POWER_ENGINE_COUNT_DEFINITION, count_raw_values),
        error_type=InvalidPowerSearchFitScenarioError,
    )
    return PowerSearchFitScenario(power_drive=power_drive, power_engine_count=power_engine_count)


class PowerSearchFitOutcome(StrEnum):
    """Mechanically distinct outcomes -- identical member set to
    `hullq.application.broker_search_fit.SearchFitOutcome`, a structurally
    separate type (never a shared/aliased enum: Sail and Power previews
    must never be interchangeable at a call site)."""

    ORG_NOT_FOUND_OR_DENIED = "ORG_NOT_FOUND_OR_DENIED"
    MFA_REQUIRED = "MFA_REQUIRED"
    PUBLISHER_ROLE_REQUIRED = "PUBLISHER_ROLE_REQUIRED"
    LISTING_NOT_FOUND = "LISTING_NOT_FOUND"
    INVALID_SCENARIO = "INVALID_SCENARIO"
    NOT_PREVIEWABLE = "NOT_PREVIEWABLE"
    CHAIN_INTEGRITY_FAULT = "CHAIN_INTEGRITY_FAULT"
    OK = "OK"


class PowerSearchFitBlocker(StrEnum):
    """Deterministic, actionable `INSUFFICIENT_DATA` blockers. Each maps to
    an existing broker editing surface: `BOATDESIGN_CONFIGURATION_UNRESOLVED`
    to the existing design selector, `POWER_CATEGORY_UNCONFIRMED`/
    `POWER_DRIVE_UNCONFIRMED`/`POWER_ENGINE_COUNT_UNCONFIRMED` to the
    existing claim editor.

    Deliberately NO `BOATDESIGN_NOT_LINKED` member (contrast
    `hullq.application.broker_search_fit.SearchFitBlocker`): a
    design-unresolved PhysicalBoat is a legitimate claim-only evaluation
    path for Power, never a blocker by itself (contract: "Missing linked
    design is a legitimate claim-only path, not inherently a missing-data
    blocker").
    """

    BOATDESIGN_CONFIGURATION_UNRESOLVED = "BOATDESIGN_CONFIGURATION_UNRESOLVED"
    POWER_CATEGORY_UNCONFIRMED = "POWER_CATEGORY_UNCONFIRMED"
    POWER_DRIVE_UNCONFIRMED = "POWER_DRIVE_UNCONFIRMED"
    POWER_ENGINE_COUNT_UNCONFIRMED = "POWER_ENGINE_COUNT_UNCONFIRMED"


@dataclass(frozen=True)
class PowerSearchFitView:
    """One evaluated hypothetical DRAFT Power Search-fit preview.

    `design_evaluation` is `None` only for a design-unresolved PhysicalBoat
    (there is no BoatDesign to evaluate at all -- never a blocker by
    itself, unlike the Sail preview's identically-named field). Otherwise
    it is the complete, unmodified `DesignQueryEvaluation` for this
    listing's linked BoatDesign. `criterion_evidence` carries the concrete
    publisher-claim classification -- for a design-unresolved listing, this
    is the claim-only evaluation itself; for a design-linked listing, it is
    populated only once the design level is itself a `CONFIRMED_MATCH`
    (design/configuration eligibility alone never confirms a concrete
    listed yacht).

    `vessel_category_exclusion` is populated only when the Power category
    admission precondition itself produced an explicit SAIL/MOTORSAILER/
    CONFLICT `CONFIRMED_NON_MATCH` exclusion -- `None` in every other case,
    including the merely-insufficient (missing/UNKNOWN/design-only/
    other-Organization-only) admission outcome, which is `INSUFFICIENT_DATA`
    with a `POWER_CATEGORY_UNCONFIRMED` blocker instead.
    """

    native_listing_id: str
    power_drive: str | None
    power_engine_count: Decimal | None
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation | None
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    criterion_evidence: tuple[SearchCriterionEvidence, ...]
    vessel_category_exclusion: PowerCategoryExclusionEvidence | None
    blockers: tuple[PowerSearchFitBlocker, ...]
    #: `PUBLISHER_CLAIM` exactly when `design_evaluation is None` (a
    #: design-unresolved claim-only evaluation -- contract: "explicit
    #: source_basis=PUBLISHER_CLAIM ... Design-unresolved must NOT display
    #: 'independently verified'"); `None` for a design-linked evaluation,
    #: mirroring `hullq.application.power_inventory_query
    #: .PowerDesignLinkedMatch`'s own lack of a `source_basis` field --
    #: design-linked evidence already carries its provenance via
    #: `design_evaluation`/`design_configuration_evidence` being present.
    source_basis: PublisherClaimSourceBasis | None


@dataclass(frozen=True)
class PowerSearchFitResult:
    outcome: PowerSearchFitOutcome
    view: PowerSearchFitView | None = None
    invalid_reason: str | None = None

    def __post_init__(self) -> None:
        if self.outcome is PowerSearchFitOutcome.OK:
            if self.view is None:
                raise ValueError("An OK Power Search-fit result must carry a view")
        elif self.view is not None:
            raise ValueError("Only an OK Power Search-fit result may carry a view")

        if self.outcome is PowerSearchFitOutcome.INVALID_SCENARIO:
            if self.invalid_reason is None:
                raise ValueError("An INVALID_SCENARIO result must carry invalid_reason")
        elif self.invalid_reason is not None:
            raise ValueError("Only an INVALID_SCENARIO result may carry invalid_reason")


def _derive_field_blockers(
    result_class: ResultClass, criterion_evidence: tuple[SearchCriterionEvidence, ...]
) -> tuple[PowerSearchFitBlocker, ...]:
    """Map an `INSUFFICIENT_DATA` per-field classification to its actionable
    blocker(s) -- called only once category admission has already succeeded
    and a technical classification (claim-only or concrete) actually ran;
    callers handle the category-admission-itself-insufficient and
    design-eligibility-itself-insufficient cases directly, since neither has
    any `criterion_evidence` to inspect."""
    if result_class is not ResultClass.INSUFFICIENT_DATA:
        return ()
    blockers: list[PowerSearchFitBlocker] = []
    seen: set[PowerSearchFitBlocker] = set()
    for evidence in criterion_evidence:
        if evidence.evaluation.truth is not TruthState.UNKNOWN:
            continue
        blocker: PowerSearchFitBlocker | None = None
        if evidence.criterion.field == POWER_DRIVE_CONFIGURATION_DEFINITION.projection_field:
            blocker = PowerSearchFitBlocker.POWER_DRIVE_UNCONFIRMED
        elif evidence.criterion.field == POWER_ENGINE_COUNT_DEFINITION.projection_field:
            blocker = PowerSearchFitBlocker.POWER_ENGINE_COUNT_UNCONFIRMED
        if blocker is not None and blocker not in seen:
            seen.add(blocker)
            blockers.append(blocker)
    return tuple(blockers)


def _authorize_actor(
    conn: Any, session: SessionClaims, organization_id: MarketplaceOrganizationId
) -> PowerSearchFitResult | None:
    """Evaluate the current workspace + PUBLISHER-role authorization
    boundary via the shared `hullq.application.broker_search_fit_support`
    helper, mapping its generic outcome onto this module's own typed
    `PowerSearchFitResult` -- never a second, independently maintained
    authorization decision (see module docstring)."""
    outcome = evaluate_broker_actor_authorization(conn, session, organization_id)
    if outcome is BrokerActorAuthorizationOutcome.ORG_NOT_FOUND_OR_DENIED:
        return PowerSearchFitResult(outcome=PowerSearchFitOutcome.ORG_NOT_FOUND_OR_DENIED)
    if outcome is BrokerActorAuthorizationOutcome.MFA_REQUIRED:
        return PowerSearchFitResult(outcome=PowerSearchFitOutcome.MFA_REQUIRED)
    if outcome is BrokerActorAuthorizationOutcome.PUBLISHER_ROLE_REQUIRED:
        return PowerSearchFitResult(outcome=PowerSearchFitOutcome.PUBLISHER_ROLE_REQUIRED)
    return None


def evaluate_organization_listing_power_search_fit(
    conn: Any,
    session: SessionClaims,
    organization_id_value: str,
    native_listing_id_value: str,
    query_params: Mapping[str, Sequence[str]],
    *,
    as_of: datetime,
) -> PowerSearchFitResult:
    """Evaluate one authorized, owned, lifecycle-DRAFT NativeListing against
    one bounded synthetic Power scenario (`power_drive`/`power_engine_count`,
    either alone or combined as MUST-AND).

    *as_of* is accepted for calling-convention parity with every other
    SLICE-0051+ Search/eligibility evaluator in this codebase; this preview
    does not itself consult D29 current-public-eligibility or freshness --
    lifecycle alone (never ACTIVE/WITHDRAWN) gates whether a hypothetical
    DRAFT preview may run at all.

    *conn* must be IDLE (no prior statement issued) when this function
    receives it -- it opens its own top-level `REPEATABLE READ` transaction
    for the snapshot read (see this module's docstring).
    """
    organization_id = MarketplaceOrganizationId(organization_id_value)
    native_listing_id = NativeListingId(native_listing_id_value)

    try:
        scenario = parse_power_search_fit_scenario(query_params)
    except InvalidPowerSearchFitScenarioError as exc:
        return PowerSearchFitResult(
            outcome=PowerSearchFitOutcome.INVALID_SCENARIO, invalid_reason=str(exc)
        )

    # build_power_query re-validates membership/shape defensively but never
    # re-parses -- the bounded public grammar was already enforced above.
    query, active_definitions = build_power_query(
        power_drive=scenario.power_drive, power_engine_count=scenario.power_engine_count
    )

    with conn.transaction():
        conn.execute("SET TRANSACTION ISOLATION LEVEL REPEATABLE READ")

        denial = _authorize_actor(conn, session, organization_id)
        if denial is not None:
            return denial

        listing_record = fetch_native_listing(conn, native_listing_id)
        if listing_record is None or listing_record.publishing_organization_id != organization_id:
            return PowerSearchFitResult(outcome=PowerSearchFitOutcome.LISTING_NOT_FOUND)

        lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
        assert lifecycle_state is not None  # the listing was just confirmed to exist, above
        if lifecycle_state is not NativeListingLifecycleState.DRAFT:
            return PowerSearchFitResult(outcome=PowerSearchFitOutcome.NOT_PREVIEWABLE)

        market_episode_id = listing_record.listing.market_episode_id
        if market_episode_id is None:
            # A listing that completed 0067 promotion always carries a
            # MarketEpisode -- a promoted DRAFT target missing one is a
            # broken identity chain, not an ordinary recoverable editing gap.
            return PowerSearchFitResult(outcome=PowerSearchFitOutcome.CHAIN_INTEGRITY_FAULT)
        market_episode_record = fetch_market_episode(conn, market_episode_id)
        if market_episode_record is None:
            return PowerSearchFitResult(outcome=PowerSearchFitOutcome.CHAIN_INTEGRITY_FAULT)
        physical_boat_id = market_episode_record.market_episode.physical_boat_id
        physical_boat_record = fetch_physical_boat(conn, physical_boat_id)
        if physical_boat_record is None:
            return PowerSearchFitResult(outcome=PowerSearchFitOutcome.CHAIN_INTEGRITY_FAULT)

        boat_design_ref = physical_boat_record.physical_boat.boat_design_ref

        design_evaluation: DesignQueryEvaluation | None
        design_configuration_evidence: tuple[ConfigurationEvidence, ...]
        criterion_evidence: tuple[SearchCriterionEvidence, ...]
        vessel_category_exclusion: PowerCategoryExclusionEvidence | None
        blockers: tuple[PowerSearchFitBlocker, ...]

        if boat_design_ref is None:
            # Design-unresolved: a legitimate claim-only evaluation, never a
            # blocker by itself (contract "Eligibility, current source,
            # design and MVCC" -- see module docstring).
            design_evaluation = None
            design_configuration_evidence = ()

            observations = list_current_physical_boat_claim_observations(conn, physical_boat_id)
            category_resolution = resolve_power_claim_only_category_from_observations(observations)
            admitted, exclusion = resolve_power_category_admission(
                category_resolution, organization_id
            )
            if exclusion is not None:
                result_class = ResultClass.CONFIRMED_NON_MATCH
                criterion_evidence = ()
                vessel_category_exclusion = exclusion
                blockers = ()
            elif not admitted:
                result_class = ResultClass.INSUFFICIENT_DATA
                criterion_evidence = ()
                vessel_category_exclusion = None
                blockers = (PowerSearchFitBlocker.POWER_CATEGORY_UNCONFIRMED,)
            else:
                result_class, criterion_evidence = classify_claim_only_candidate(
                    observations,
                    publishing_organization_id=organization_id,
                    query=query,
                    active_definitions=active_definitions,
                )
                result_class, criterion_evidence = downgrade_mixed_non_match_to_insufficient_data(
                    result_class, criterion_evidence
                )
                vessel_category_exclusion = None
                blockers = _derive_field_blockers(result_class, criterion_evidence)
        else:
            raw_design = fetch_boat_design(conn, boat_design_ref.value)
            if raw_design is None:
                # Dangling BoatDesignRef: a stored link to a non-existent
                # canonical design is a data-integrity error, never an
                # inferred/guessed design.
                return PowerSearchFitResult(outcome=PowerSearchFitOutcome.CHAIN_INTEGRITY_FAULT)

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

            if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
                # Review Finding G discipline (SLICE-0093): category
                # admission and the concrete drive/count classification
                # must be read from the same PostgreSQL snapshot --
                # `fetch_power_category_drive_snapshot` folds both into one
                # statement, never two separately-timed reads.
                snapshot = fetch_power_category_drive_snapshot(
                    conn,
                    physical_boat_id=physical_boat_id,
                    boat_design_id=boat_design_ref.value,
                )
                category_resolution = resolve_vessel_category(
                    design_evidence=snapshot.design_evidence,
                    concrete_evidence=snapshot.concrete_evidence,
                )
                admitted, exclusion = resolve_power_category_admission(
                    category_resolution, organization_id
                )
                if admitted:
                    result_class, criterion_evidence = classify_concrete_candidate(
                        conn,
                        native_listing_id=native_listing_id,
                        publishing_organization_id=organization_id,
                        physical_boat_id=physical_boat_id,
                        boat_design_id=boat_design_ref.value,
                        query=query,
                        active_definitions=active_definitions,
                        observations=snapshot.observations,
                    )
                    result_class, criterion_evidence = (
                        downgrade_mixed_non_match_to_insufficient_data(
                            result_class, criterion_evidence
                        )
                    )
                    vessel_category_exclusion = None
                    blockers = _derive_field_blockers(result_class, criterion_evidence)
                elif exclusion is not None:
                    result_class = ResultClass.CONFIRMED_NON_MATCH
                    criterion_evidence = ()
                    vessel_category_exclusion = exclusion
                    blockers = ()
                else:
                    result_class = ResultClass.INSUFFICIENT_DATA
                    criterion_evidence = ()
                    vessel_category_exclusion = None
                    blockers = (PowerSearchFitBlocker.POWER_CATEGORY_UNCONFIRMED,)
            else:
                # Design/configuration eligibility never admitted this
                # design to the concrete funnel -- classified directly from
                # the design-level result, fail-closed, without ever
                # consulting the concrete claim.
                result_class = design_evaluation.result_class
                criterion_evidence = ()
                vessel_category_exclusion = None
                blockers = (
                    (PowerSearchFitBlocker.BOATDESIGN_CONFIGURATION_UNRESOLVED,)
                    if result_class is ResultClass.INSUFFICIENT_DATA
                    else ()
                )

        view = PowerSearchFitView(
            native_listing_id=native_listing_id.value,
            power_drive=scenario.power_drive,
            power_engine_count=scenario.power_engine_count,
            result_class=result_class,
            design_evaluation=design_evaluation,
            design_configuration_evidence=design_configuration_evidence,
            criterion_evidence=criterion_evidence,
            vessel_category_exclusion=vessel_category_exclusion,
            blockers=blockers,
            source_basis=(
                PublisherClaimSourceBasis.PUBLISHER_CLAIM if boat_design_ref is None else None
            ),
        )
    # The snapshot transaction above committed trivially (read-only) on
    # normal exit, including every early-return branch -- mirrors
    # `hullq.application.broker_search_fit`'s identical convention.

    # A completely fresh, independent recheck -- new statements against the
    # now-current committed state, never the snapshot above -- so an
    # interleaved revoke/role-change/publish/withdraw during evaluation is
    # caught here, not silently used to legitimize a stale OK.
    recheck_denial = _authorize_actor(conn, session, organization_id)
    if recheck_denial is not None:
        return recheck_denial

    # Independent review amendment Finding C (round 1): the contract's own
    # words are "independently recheck current role/MFA authorization and
    # listing ownership/lifecycle with fresh statements" -- re-fetching
    # only lifecycle (as the original SLICE-0084 Sail recheck does) silently
    # assumes the listing's owning Organization can never change out from
    # under an in-flight evaluation. That assumption happens to hold today
    # -- `hullq.persistence.native_listing` never issues an `UPDATE
    # native_listings SET publishing_organization_id = ...` anywhere in
    # this codebase; the only mutable column on that table is
    # `lifecycle_state` (`hullq.persistence.native_listing_lifecycle
    # ._apply_transition`) -- but this preview re-fetches the full
    # NativeListing record and re-verifies its `publishing_organization_id`
    # explicitly rather than silently relying on that invariant never being
    # violated by a future change elsewhere in the codebase. A foreign or
    # now-missing listing identity collapses to the identical
    # non-enumerating `LISTING_NOT_FOUND` the snapshot phase itself already
    # uses for the same condition -- never a distinguishable outcome that
    # could confirm a listing's prior existence/ownership to an
    # unauthorized caller.
    recheck_listing_record = fetch_native_listing(conn, native_listing_id)
    if (
        recheck_listing_record is None
        or recheck_listing_record.publishing_organization_id != organization_id
    ):
        return PowerSearchFitResult(outcome=PowerSearchFitOutcome.LISTING_NOT_FOUND)

    recheck_lifecycle_state = fetch_lifecycle_state(conn, native_listing_id)
    if recheck_lifecycle_state is not NativeListingLifecycleState.DRAFT:
        return PowerSearchFitResult(outcome=PowerSearchFitOutcome.NOT_PREVIEWABLE)

    return PowerSearchFitResult(outcome=PowerSearchFitOutcome.OK, view=view)
