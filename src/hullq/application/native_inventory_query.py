"""Requirements -> Native Inventory Search vertical, generalized to criterion #2 — SLICE-0055.

`hullq.application.inventory_search.evaluate_draft_max_requirement` (SLICE-0051)
remains unchanged and is still used, unmodified, for a pure `draft_max`
request (Required Behavior/contract §8: "A request containing only draft_max
MUST retain accepted SLICE-0051 behavior"). This module is the new bounded
funnel for a request that involves `keel_configuration`, alone or combined
with `draft_max`:

    exact-Decimal draft_max and/or canonical keel_configuration requirement
    -> deterministic BoatDesign/configuration eligibility, merged across
       every active criterion on the same configuration identity
       (hullq.search.boat_design_field_bridge.run_boat_design_configuration_query)
    -> durable design identity admission to ACTIVE, current native inventory
       (hullq.persistence.inventory_search, hullq.application.native_listing_freshness --
        both reused unchanged)
    -> publishing Organization's current concrete PhysicalBoat claim(s) for
       every active field, read from one consistent snapshot
       (hullq.persistence.physical_boat_claims.list_current_physical_boat_claim_observations)
    -> listing-level CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA,
       evaluated by reusing the same MUST-AND kernel primitives
       (hullq.search.configuration_engine.evaluate_configuration) that
       already classify design-level eligibility -- never a bespoke
       hand-rolled combination of per-field if/else branches.

Design/configuration eligibility only establishes possible eligibility
(Required Behavior §C); a concrete listing is confirmed only after the
PUBLISHER's own current PhysicalBoat claim(s) independently confirm every
active criterion -- never backfilled from BoatDesign/configuration truth.

## Evidence preservation (contract §6/§7, amendment Finding 1)

Unlike SLICE-0051's `DraftMaxSearchOutcome` (which counts non-match/
insufficient-data listings but does not identify them), this module's
`NativeInventorySearchOutcome` retains full typed evidence for all three
result classes:

- `NativeInventorySearchOutcome.query` is the exact `MixedAndQuery` that was
  evaluated, so every candidate's requested criterion value/comparison
  (`NumericLeafCriterion`/`CategoricalLeafCriterion`, already typed) is
  recoverable without re-running Search truth;
- `NativeInventoryCandidateEvaluation.design_evaluation` is the *complete,
  unmodified* `hullq.search.configuration_engine.DesignQueryEvaluation` for
  the candidate's BoatDesign -- never collapsed to a bare confirmed/not-
  confirmed boolean. It carries `matching_configuration_ids` (the exact
  resolved BoatDesign/NamedVariant configuration identity/identities that
  admitted the design, per Required Behavior §D) and the full per-
  configuration `configuration_evaluations` (each itself a per-criterion
  `CriterionEvaluation`), including for a design that is `INSUFFICIENT_DATA`
  (e.g. an unsupported keel taxonomy mapping) or a `CONFIRMED_NON_MATCH` --
  such a design's listings are classified accordingly and *this* evidence is
  attached, rather than the listing silently disappearing from every result
  surface;
- `NativeInventoryCandidateEvaluation.design_configuration_evidence` closes
  the second amendment's Finding 1 gap: `design_evaluation` alone carries
  each evaluated configuration's `CriterionEvaluation` (typed truth/reason)
  but not the BoatDesign/NamedVariant canonical value that was actually
  qualified and compared to produce it -- `evaluate_configuration` reads
  that value from `ResolvedConfiguration.projection` but does not return it,
  and the `DesignConfigurationSet`/`ResolvedConfiguration` objects
  themselves go out of scope once `run_configuration_query` returns. This
  module retains them (via `hullq.search.boat_design_field_bridge.
  run_boat_design_configuration_query`'s `configurations_by_id`) and pairs
  each of `design_evaluation.configuration_evaluations`' own per-criterion
  `CriterionEvaluation` with the exact requested criterion and the safely
  resolved/observed canonical value used, one `ConfigurationEvidence` per
  evaluated BoatDesign/NamedVariant configuration -- present for every
  design result class (match, non-match, insufficient alike), never only
  for the configurations that matched;
- `NativeInventoryCandidateEvaluation.concrete_criterion_evidence` is the
  concrete PhysicalBoat-level evidence, kept separate from the design-level
  evidence above (contract §7 point 6). Each `SearchCriterionEvidence` pairs
  the exact requested `NumericLeafCriterion`/`CategoricalLeafCriterion`, the
  unmodified `CriterionEvaluation` (typed truth + reason code), and the
  safely observed/resolved concrete canonical value when one exists (never
  encoded only inside `CriterionEvaluation.explanation` text) -- mirroring
  the typed `resolved_draft_m` field SLICE-0051's own
  `DraftMaxConfirmedMatch` already carried, generalized to both criteria and
  to the non-match/insufficient classes SLICE-0051 only counted.

No second Search truth engine is introduced and the established
`hullq.search.configuration_engine` kernel types
(`ConfigurationEvaluation`/`DesignQueryEvaluation`/`ConfigurationSearchOutcome`)
are never modified. `SearchCriterionEvidence`/`ConfigurationEvidence` are
bounded typed wrappers reused for both the design-side and concrete-side
evidence, adding only the one piece of information the kernel types do not
carry (the resolved/observed value) -- never re-derived from
`CriterionEvaluation.explanation` text.
"""

from __future__ import annotations

import time
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Any

from hullq.application.current_public_eligibility import (
    resolve_current_public_eligibility,
    resolve_current_public_eligibility_for_many,
)
from hullq.application.native_listing_freshness import CurrentFreshness, resolve_current_freshness
from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
from hullq.domain.current_public_eligibility import CurrentPublicEligibilityStatus
from hullq.domain.market_identity import NativeListingId, PhysicalBoatId
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    PhysicalBoatClaimRevisionId,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.domain.vessel_category import (
    ConcreteVesselCategoryEvidence,
    VesselCategoryExclusionEvidence,
    VesselCategoryResolution,
    VesselCategoryResolutionResult,
    resolve_vessel_category,
)
from hullq.persistence.identity_readback import fetch_boat_design
from hullq.persistence.inventory_search import (
    ActiveDesignUnresolvedListing,
    ActiveNativeListingCandidate,
    active_native_listing_candidate_exists_after,
    list_active_design_linked_listings,
    list_active_design_unresolved_listings,
    list_active_native_listing_candidates_page,
)
from hullq.persistence.physical_boat_claims import (
    CurrentPhysicalBoatClaimObservation,
    list_current_physical_boat_claim_observations,
    list_current_physical_boat_claim_observations_for_many,
)
from hullq.search.boat_design_field_bridge import BoatDesignConfigurationQueryResult
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (
    ConfigurationEvaluation,
    ConfigurationSearchOutcome,
    DesignQueryEvaluation,
    evaluate_configuration,
    evaluate_projection,
    run_configuration_query,
)
from hullq.search.criteria import (
    CategoricalLeafCriterion,
    CriterionEvaluation,
    NumericLeafCriterion,
)
from hullq.search.criteria_registry import (
    BEAM_DEFINITION,
    COCKPIT_POSITION_DEFINITION,
    DECK_SALOON_DEFINITION,
    DRAFT_MAX_DEFINITION,
    HULL_CONFIGURATION_DEFINITION,
    HULL_MATERIAL_DEFINITION,
    KEEL_CONFIGURATION_DEFINITION,
    LOA_DEFINITION,
    RUDDER_CONFIGURATION_DEFINITION,
    CriterionDefinition,
    CriterionKind,
)
from hullq.search.query_mixed import MixedAndQuery, MixedLeafCriterion
from hullq.search.types import NumericComparisonKind, ResultClass, TruthState, ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

__all__ = [
    "ConfigurationEvidence",
    "NativeInventoryCandidateEvaluation",
    "NativeInventorySearchOutcome",
    "NativeInventorySearchResultPage",
    "PublisherClaimCandidateEvaluation",
    "PublisherClaimSourceBasis",
    "PublisherClaimSourceEvidence",
    "SearchCriterionEvidence",
    "SearchPageEvaluationState",
    "build_configuration_evidence",
    "build_mixed_requirement_query",
    "classify_claim_only_candidate",
    "classify_claim_only_page_candidate",
    "classify_concrete_candidate",
    "evaluate_claim_only_candidates",
    "evaluate_native_inventory_requirements",
    "evaluate_native_inventory_requirements_page",
    "run_mixed_boat_design_configuration_query",
]

#: Enforceable per-request candidate-scan budget for the new bounded public
#: page path (contract §3: "Each HTTP request has explicit finite
#: server-side caps for candidate IDs fetched"). Deliberately much larger
#: than the hard page-size ceiling (50) so an ordinary sparse/negative-heavy
#: population still has a realistic chance of filling one page, while
#: remaining a fixed, test-asserted, non-configurable-per-request ceiling --
#: never a hidden "keep fetching until N matches" loop (this bounds exactly
#: ONE `list_active_native_listing_candidates_page` SQL call per page
#: request). Shared by the Power-domain bounded page evaluator
#: (`hullq.application.power_inventory_query`) so both domains are capped
#: identically.
DEFAULT_CANDIDATE_SCAN_BUDGET = 500

#: SLICE-0096 independent review round 2 Finding E2: a real
#: `statement_timeout` (`hullq.api.app._SEARCH_PAGE_STATEMENT_TIMEOUT_MS`)
#: bounds any ONE SQL statement, but a bounded page may still issue many
#: individually-fast statements in sequence -- one `fetch_boat_design` per
#: DISTINCT BoatDesign among the scanned candidates, plus one
#: classification (itself 1+ statements) per scanned candidate, up to
#: `DEFAULT_CANDIDATE_SCAN_BUDGET` of them. No single statement ever
#: exceeding its own timeout therefore does not, by itself, bound this
#: function's own total wall-clock time. This is the ONE place that does:
#: checked cooperatively at the top of every per-design/per-candidate loop
#: iteration in `evaluate_native_inventory_requirements_page` (below),
#: `hullq.application.power_inventory_query.evaluate_power_requirement_page`
#: and `hullq.application.inventory_search.evaluate_draft_max_requirement_page`
#: -- all three share this one constant/exception/helper so a future fourth
#: bounded evaluator cannot silently omit the check.
DEFAULT_REQUEST_DEADLINE_SECONDS = 8.0


class SearchRequestDeadlineExceeded(RuntimeError):
    """Raised when a bounded page evaluator's cumulative wall-clock time
    exceeds its own request-level deadline, independent of any single SQL
    statement's own `statement_timeout`. `hullq.api.app`'s request handlers
    catch this exactly like `psycopg.errors.QueryCanceled`, producing the
    same controlled 503 -- never an unhandled 500, and never a silently
    truncated/smaller-than-requested page presented as a genuine result.
    """


def check_request_deadline(deadline: float) -> None:
    """Raise `SearchRequestDeadlineExceeded` if the monotonic *deadline*
    (an absolute `time.monotonic()` value, as returned by
    `time.monotonic() + DEFAULT_REQUEST_DEADLINE_SECONDS`) has passed."""
    if time.monotonic() > deadline:
        raise SearchRequestDeadlineExceeded(
            "bounded Search page evaluation exceeded its request-level deadline"
        )


@dataclass(frozen=True, slots=True)
class SearchCriterionEvidence:
    """Typed per-criterion concrete evidence (contract §6/§7, Finding 1).

    Pairs the exact requested leaf criterion (already typed with its own
    field/comparison/thresholds or `equals` value) with the unmodified
    `CriterionEvaluation` result (typed truth + reason code) and, when one
    exists, the safely observed/resolved concrete canonical value -- e.g. the
    publisher's own current `draft` (`Decimal`) or `keel_configuration`
    (`str`) claim. `observed_value` is `None` whenever `evaluation.truth` is
    not derived from a `CONFIRMED` qualified value (missing/UNKNOWN/
    unresolved-conflict evidence never fabricates an observed value).
    """

    criterion: MixedLeafCriterion
    evaluation: CriterionEvaluation
    observed_value: Decimal | str | None


@dataclass(frozen=True, slots=True)
class ConfigurationEvidence:
    """One resolved BoatDesign/NamedVariant configuration's typed evidence
    (contract §7, second amendment Finding 1).

    `configuration_id`/`boat_design_id`/`named_variant_id` are the exact
    resolved configuration identity `hullq.search.configuration.
    ConfigurationIdentity` already carries (`named_variant_id` is `None`
    for the baseline configuration). `truth` is this configuration's own
    aggregate `hullq.search.configuration_engine.ConfigurationEvaluation.truth`.
    `criterion_evidence` pairs each requested criterion with its
    per-criterion `CriterionEvaluation` and the safely resolved/observed
    BoatDesign/NamedVariant canonical value actually used for that
    evaluation (from the exact `ResolvedConfiguration.projection` that was
    evaluated) -- never fabricated, and never re-derived from
    `CriterionEvaluation.explanation` text.
    """

    configuration_id: str
    boat_design_id: str
    named_variant_id: str | None
    truth: TruthState
    criterion_evidence: tuple[SearchCriterionEvidence, ...]


@dataclass(frozen=True, slots=True)
class NativeInventoryCandidateEvaluation:
    """One concrete candidate's classification plus full typed evidence.

    `design_evaluation` is the complete, unmodified design-level
    `DesignQueryEvaluation` for this candidate's BoatDesign -- present even
    when `result_class` is `CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` at the
    design level, in which case `concrete_criterion_evidence` is empty
    because the concrete PhysicalBoat claim was never consulted (design/
    configuration eligibility never admitted the design to the concrete
    funnel at all -- Required Behavior §C). When the design *is* a design-
    level `CONFIRMED_MATCH`, `concrete_criterion_evidence` carries the
    concrete classification's own per-criterion evidence, and `result_class`
    reflects that concrete classification, not the design-level one.

    `design_configuration_evidence` is always populated, one
    `ConfigurationEvidence` per entry in
    `design_evaluation.configuration_evaluations` (baseline and every
    evaluated NamedVariant alike, regardless of which one(s) matched) --
    the typed BoatDesign/NamedVariant observed-value evidence
    `design_evaluation` alone cannot recover (second amendment Finding 1).

    `vessel_category_exclusion` is populated only when the SLICE-0091 §C
    category pre-filter itself produced this `CONFIRMED_NON_MATCH` (the
    design level was a `CONFIRMED_MATCH` but the resolved vessel category is
    explicitly `POWER`/`MOTORSAILER`/`CONFLICT`) -- `None` in every other
    case, including an ordinary nine-criterion technical non-match/
    insufficient-data result and a design/configuration-level exclusion.
    Amendment review Finding I: without this, such a candidate was
    mechanically indistinguishable from an ordinary technical mismatch, with
    zero retained evidence explaining why. Deliberately the bounded,
    cross-Organization-identity-free `VesselCategoryExclusionEvidence`, never
    the full `VesselCategoryResolutionResult` (see that type's docstring).
    """

    native_listing_id: NativeListingId
    result_class: ResultClass
    design_evaluation: DesignQueryEvaluation
    design_configuration_evidence: tuple[ConfigurationEvidence, ...]
    concrete_criterion_evidence: tuple[SearchCriterionEvidence, ...]
    vessel_category_exclusion: VesselCategoryExclusionEvidence | None
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None


class PublisherClaimSourceBasis(StrEnum):
    """The one accepted source-basis discriminator for a claim-only match --
    amendment review Finding C. A single, fixed member deliberately (no open
    vocabulary): a claim-only match's evidence is *always*
    `PUBLISHER_CLAIM`, never independently design-verified. The public
    serializer (`hullq.api.app._serialize_claim_only_match`) reads this
    typed field rather than writing an independent literal string that
    could silently drift from the internal type."""

    PUBLISHER_CLAIM = "PUBLISHER_CLAIM"


@dataclass(frozen=True, slots=True)
class PublisherClaimSourceEvidence:
    """Internal-only, auditable provenance for the current publisher
    observation backing one claim-only candidate -- amendment review
    Finding C: "retain the exact publisher's current claim revision, actor,
    timestamp, positive category evidence ... in the internal result".

    `revision_id`/`recorded_by_account_id`/`recorded_at` identify the exact
    current `PhysicalBoatClaimRevision` this candidate's category admission
    **and** every one of its technical-criterion evaluations were drawn
    from -- not merely the category field's own provenance, the whole
    single-query observation's (SLICE-0092 contract §E coherent-snapshot
    requirement: category and fields always come from this same revision).
    `category_claim` is the publishing Organization's own current
    `VesselCategoryClaim` (`None` only when that Organization's current
    observation omits the field entirely -- mechanically distinct from an
    explicit `UNKNOWN` claim, exactly like every other optional PhysicalBoat
    claim field in this codebase).

    Intended for authorized internal/audit consumption only. The public
    API/SSR surface discloses only the fixed `PublisherClaimSourceBasis`
    literal (via `PublisherClaimCandidateEvaluation.source_basis`) --
    `hullq.api.app._serialize_claim_only_match` never reads this type's
    `revision_id`/`recorded_by_account_id` (contract §D: "public DTO/SSR may
    disclose only safe publisher/source-type ... never ... private raw
    provenance").
    """

    revision_id: PhysicalBoatClaimRevisionId
    recorded_by_account_id: AccountId
    recorded_at: datetime
    category_claim: VesselCategoryClaim | None


@dataclass(frozen=True, slots=True)
class PublisherClaimCandidateEvaluation:
    """One design-unresolved candidate's claim-only classification -- SLICE-0092.

    Distinct from `NativeInventoryCandidateEvaluation`: there is no
    `DesignQueryEvaluation`/`ConfigurationEvidence` at all (there is no
    BoatDesign to evaluate -- contract §C/§D: never wrapped in a fake
    `ConfigurationIdentity` or an invented `boat_design_id`). Every match
    here is `source_basis = PUBLISHER_CLAIM` by construction: the publishing
    Organization's own current claim-revision statement, never independently
    design-verified (contract §D). Built exclusively by
    `classify_claim_only_candidate`/`evaluate_claim_only_candidates` below,
    reusing the identical per-field qualification and MUST/AND truth kernel
    `classify_concrete_candidate` uses for the design-linked path.

    `vessel_category_exclusion` is populated only when the publisher-owned
    SAIL admission precondition (contract §A: "the publishing Organization
    itself ... has an explicit current VALUE_ASSERTION(SAIL) category
    claim") failed because the resolved category is explicitly
    POWER/MOTORSAILER/CONFLICT (`result_class` is then `CONFIRMED_NON_MATCH`).
    A missing/UNKNOWN category, or a positive SAIL resolution contributed
    only by a *different* claiming Organization, is `None` here instead --
    `result_class` is `INSUFFICIENT_DATA` in that case, never
    `CONFIRMED_NON_MATCH`, since `VesselCategoryExclusionEvidence` itself only
    accepts an explicit non-Sail/conflicted resolution (see its own
    docstring) and "not yet established as the publisher's own SAIL claim"
    is a materially different, weaker fact than "explicitly excluded".
    `criterion_evidence` is empty whenever category admission itself did not
    succeed -- the concrete per-field claims are never even consulted.

    `source_basis` is always `PublisherClaimSourceBasis.PUBLISHER_CLAIM`
    (amendment review Finding C: a typed field the public serializer binds
    to, rather than an independently-written literal). `source_evidence` is
    the retained internal-only provenance (`None` only when the publishing
    Organization has no current claim-observation row at all for this
    PhysicalBoat -- distinct from every other field-level "omitted" case).
    """

    native_listing_id: NativeListingId
    result_class: ResultClass
    criterion_evidence: tuple[SearchCriterionEvidence, ...]
    vessel_category_exclusion: VesselCategoryExclusionEvidence | None
    publishing_organization_id: MarketplaceOrganizationId
    freshness_status: FreshnessStatus
    last_confirmed_at: datetime | None
    source_basis: PublisherClaimSourceBasis
    source_evidence: PublisherClaimSourceEvidence | None


@dataclass(frozen=True, slots=True)
class NativeInventorySearchOutcome:
    """Separated result surfaces for one mixed requirement evaluation.

    `confirmed_matches` is the only primary result set. Unlike SLICE-0051's
    `DraftMaxSearchOutcome`, `confirmed_non_matches`/`insufficient_data` are
    full listings carrying typed design- and concrete-level evidence, not
    bare counts (Required Behavior §G). `query` is the exact evaluated
    `MixedAndQuery`, carrying every active criterion's own requested
    value/comparison.

    SLICE-0092: `claim_only_matches`/`claim_only_non_matches`/
    `claim_only_insufficient_data` are the entirely separate, additive
    design-unresolved publisher-claim result surfaces (contract §D: "claim-
    only and design-linked results are discriminable"). They are never
    merged into `confirmed_matches` and never affect `confirmed_match_count`/
    `confirmed_non_match_count`/`insufficient_data_count` -- existing
    design-linked counts/sets are byte-for-byte unchanged by this slice.
    """

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
    query: MixedAndQuery
    confirmed_matches: tuple[NativeInventoryCandidateEvaluation, ...]
    confirmed_non_matches: tuple[NativeInventoryCandidateEvaluation, ...]
    insufficient_data: tuple[NativeInventoryCandidateEvaluation, ...]
    claim_only_matches: tuple[PublisherClaimCandidateEvaluation, ...] = ()
    claim_only_non_matches: tuple[PublisherClaimCandidateEvaluation, ...] = ()
    claim_only_insufficient_data: tuple[PublisherClaimCandidateEvaluation, ...] = ()

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def confirmed_non_match_count(self) -> int:
        return len(self.confirmed_non_matches)

    @property
    def insufficient_data_count(self) -> int:
        return len(self.insufficient_data)

    @property
    def claim_only_match_count(self) -> int:
        return len(self.claim_only_matches)


class SearchPageEvaluationState(StrEnum):
    """The exactly two accepted bounded-page outcomes -- SLICE-0096 READY
    contract §1/§2. `PARTIAL` means unchecked ACTIVE candidates may remain
    (even when this exact page carries zero matches: "a bounded scan may
    return zero matches with PARTIAL"); `COMPLETE` means boundedly PROVEN
    exhausted (every ACTIVE candidate after the traversal's start has now
    been examined). Shared verbatim by the Power-domain bounded page
    evaluator -- never a second, independently spelled pair of literals."""

    PARTIAL = "PARTIAL"
    COMPLETE = "COMPLETE"


@dataclass(frozen=True, slots=True)
class NativeInventorySearchResultPage:
    """One bounded page of the Sail mixed-requirement vertical -- SLICE-0096.

    Unlike `NativeInventorySearchOutcome` (the full, unbounded, pre-0096
    evaluation retained for the private broker Search-fit/sensitivity
    callers), this type is strictly page-local: `confirmed_matches`/
    `claim_only_matches` are only the matches found within THIS page's
    bounded candidate scan (never a global running total), and
    `design_linked_insufficient_data_count`/`claim_only_insufficient_data_count`
    are page-local counts, never an invented global total (contract §2:
    "page-local counts, no invented global totals"). `confirmed_non_matches`/
    non-match evidence are deliberately not retained here at all -- the
    existing public API never serialized them either (only a count), and a
    non-match carries no actionable buyer value on a bounded page.

    The two insufficient-data counts are kept SEPARATE, mirroring the
    pre-0096 public API exactly: `NativeInventorySearchOutcome
    .insufficient_data_count` (serialized as the public `insufficient_data_count`
    field) only ever counted the design-linked plane -- the claim-only
    plane's own `claim_only_insufficient_data` was never exposed as a count
    at all. Collapsing both planes into one combined number here would
    silently change that field's existing meaning for every pre-0096
    caller/test.

    The `__post_init__` invariant below is the contract's own hard rule,
    enforced at construction so no call site can accidentically violate it:
    "A PARTIAL response MUST have a valid next_cursor; a COMPLETE response
    MUST NOT have one." `next_after_native_listing_id` is the raw internal
    cursor value (the last candidate identity actually evaluated) -- the
    caller (the FastAPI route) is responsible for minting the actual opaque,
    signed public `next_cursor` token from it
    (`hullq.security.search_page_cursor.mint_search_page_cursor`); this
    application-layer type never embeds signing concerns.
    """

    query: MixedAndQuery
    evaluation_state: SearchPageEvaluationState
    next_after_native_listing_id: str | None
    confirmed_matches: tuple[NativeInventoryCandidateEvaluation, ...]
    claim_only_matches: tuple[PublisherClaimCandidateEvaluation, ...]
    design_linked_insufficient_data_count: int
    claim_only_insufficient_data_count: int

    def __post_init__(self) -> None:
        is_partial = self.evaluation_state is SearchPageEvaluationState.PARTIAL
        if is_partial and self.next_after_native_listing_id is None:
            raise ValueError("A PARTIAL page must carry next_after_native_listing_id")
        if not is_partial and self.next_after_native_listing_id is not None:
            raise ValueError("A COMPLETE page must not carry next_after_native_listing_id")

    @property
    def confirmed_match_count(self) -> int:
        return len(self.confirmed_matches)

    @property
    def claim_only_match_count(self) -> int:
        return len(self.claim_only_matches)


def _qualify_claim_field(
    *,
    publisher_assertion_kind: AssertionKind | None,
    publisher_value: Any,
    cross_organization_values: set[Any],
) -> tuple[ValueQualification, Any]:
    """Fail-closed concrete-claim qualification shared by draft/keel (contract §3).

    Missing/omitted or explicit `UNKNOWN` publisher claim -> `MISSING`
    (never guessed). More than one distinct current value across every
    claiming Organization for this PhysicalBoatId (the same-PhysicalBoat
    contradiction guard, SLICE-0051 §G / contract §3) -> `MISSING`. Otherwise
    the publisher's own current value is `CONFIRMED` -- never backfilled
    from BoatDesign/configuration truth.
    """
    if publisher_assertion_kind is None or publisher_assertion_kind is AssertionKind.UNKNOWN:
        return (ValueQualification.MISSING, None)
    if len(cross_organization_values) > 1:
        return (ValueQualification.MISSING, None)
    return (ValueQualification.CONFIRMED, publisher_value)


def _observed_projection_value(
    resolved_configuration: ResolvedConfiguration, criterion: MixedLeafCriterion
) -> Decimal | str | None:
    """The safely resolved/observed BoatDesign/NamedVariant canonical value
    *criterion* was actually compared against in *resolved_configuration*,
    or `None` when that field's qualification is not `CONFIRMED` -- read
    directly from `ResolvedConfiguration.projection` (never fabricated, and
    independent of `CriterionEvaluation.explanation` text).
    """
    if isinstance(criterion, NumericLeafCriterion):
        qualified_numeric = resolved_configuration.projection.get_numeric(criterion.field)
        if qualified_numeric.qualification is not ValueQualification.CONFIRMED:
            return None
        # Every SLICE-0055 numeric FieldProjectionSpec decodes via
        # decode_decimal_for_qualification, which QualifiedNumericValue
        # preserves as an exact Decimal, never coerced to float -- see that
        # class's docstring.
        assert isinstance(qualified_numeric.value, Decimal)
        return qualified_numeric.value
    qualified_categorical = resolved_configuration.projection.get_categorical(criterion.field)
    if qualified_categorical.qualification is not ValueQualification.CONFIRMED:
        return None
    assert qualified_categorical.value is not None
    return qualified_categorical.value


def build_configuration_evidence(
    query: MixedAndQuery,
    configuration_evaluation: ConfigurationEvaluation,
    resolved_configuration: ResolvedConfiguration,
) -> ConfigurationEvidence:
    """Build one `ConfigurationEvidence` for *resolved_configuration* (second
    amendment Finding 1): pairs each of `query.criteria`, in order, with its
    `configuration_evaluation.criterion_evaluations` counterpart (the same
    order `hullq.search.configuration_engine.evaluate_configuration` used to
    produce them) and the safely resolved/observed canonical value read from
    `resolved_configuration.projection` -- the exact `ResolvedConfiguration`
    `build_boat_design_configuration_set` built and `run_configuration_query`
    evaluated, never re-derived from `CriterionEvaluation.explanation`.
    """
    criterion_evidence = tuple(
        SearchCriterionEvidence(
            criterion=criterion,
            evaluation=criterion_evaluation,
            observed_value=_observed_projection_value(resolved_configuration, criterion),
        )
        for criterion, criterion_evaluation in zip(
            query.criteria, configuration_evaluation.criterion_evaluations, strict=True
        )
    )
    identity = resolved_configuration.identity
    return ConfigurationEvidence(
        configuration_id=identity.configuration_id,
        boat_design_id=identity.boat_design_id,
        named_variant_id=identity.named_variant_id,
        truth=configuration_evaluation.truth,
        criterion_evidence=criterion_evidence,
    )


def _qualify_claims_against_definitions(
    observations: Sequence[CurrentPhysicalBoatClaimObservation],
    *,
    publishing_organization_id: MarketplaceOrganizationId,
    active_definitions: Sequence[CriterionDefinition],
) -> tuple[ConfigurationProjection, dict[str, Decimal | str | None]]:
    """Qualify every active criterion's concrete claim field from *observations*
    (already a single-query, single-PhysicalBoat observation set) into one
    `ConfigurationProjection` plus the safely observed/resolved value per
    projection field.

    Factored out of `classify_concrete_candidate` (SLICE-0092) so the new
    design-unresolved claim-only path (`classify_claim_only_candidate`,
    below) can reuse the *identical* per-field same-PhysicalBoat
    cross-Organization qualification (Review amendment Finding C's "concrete
    publisher accessor" loop) without duplicating it -- the only difference
    between the two callers is what each does with the resulting
    `ConfigurationProjection` afterwards (design-linked: wrap in a real
    `ConfigurationIdentity`/`ResolvedConfiguration`; claim-only: evaluate the
    bare projection directly via `evaluate_projection`, contract §C exact
    implementation boundary).
    """
    publisher_observation = next(
        (obs for obs in observations if obs.claiming_organization_id == publishing_organization_id),
        None,
    )

    numeric_values: dict[str, QualifiedNumericValue] = {}
    categorical_values: dict[str, QualifiedCategoricalValue] = {}
    observed_by_field: dict[str, Decimal | str | None] = {}

    for definition in active_definitions:
        publisher_entry = (
            definition.read_claim(publisher_observation)
            if publisher_observation is not None
            else None
        )
        cross_organization_values = {
            entry[1]
            for obs in observations
            if (entry := definition.read_claim(obs)) is not None
            and entry[0] is AssertionKind.VALUE_ASSERTION
        }
        qualification, value = _qualify_claim_field(
            publisher_assertion_kind=publisher_entry[0] if publisher_entry is not None else None,
            publisher_value=publisher_entry[1] if publisher_entry is not None else None,
            cross_organization_values=cross_organization_values,
        )
        is_confirmed = qualification is ValueQualification.CONFIRMED
        resolved_value = value if is_confirmed else None
        if definition.kind is CriterionKind.CATEGORICAL:
            categorical_values[definition.projection_field] = QualifiedCategoricalValue(
                value=resolved_value, qualification=qualification
            )
        else:
            numeric_values[definition.projection_field] = QualifiedNumericValue(
                value=resolved_value, qualification=qualification
            )
        observed_by_field[definition.projection_field] = resolved_value

    projection = ConfigurationProjection(
        numeric_values=numeric_values, categorical_values=categorical_values
    )
    return projection, observed_by_field


def classify_concrete_candidate(
    conn: Any,
    *,
    native_listing_id: NativeListingId,
    publishing_organization_id: MarketplaceOrganizationId,
    physical_boat_id: PhysicalBoatId,
    boat_design_id: str,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
    observations: Sequence[CurrentPhysicalBoatClaimObservation] | None = None,
) -> tuple[ResultClass, tuple[SearchCriterionEvidence, ...]]:
    """Classify one design-eligible, currently-fresh candidate's concrete
    PhysicalBoat claims.

    Reads every active field's current cross-Organization observation set
    from one call to `list_current_physical_boat_claim_observations` (one
    SQL statement, therefore one consistent PostgreSQL MVCC snapshot across
    every active criterion -- mirrors the SLICE-0051 Finding 5 rationale),
    then reuses the exact same `evaluate_configuration` MUST-AND kernel

    SLICE-0093 review amendment (Finding G): *observations* may be supplied
    by a caller that has already read this PhysicalBoat's current claim
    observations as part of one larger coherent snapshot -- e.g. folded
    together with a design-category read in the same SQL statement
    (`hullq.persistence.power_category_drive_snapshot
    .fetch_power_category_drive_snapshot`). Passing it here avoids a
    second, separately-timed SQL statement that could observe a different
    current revision than the one the caller's own snapshot already
    established (closing exactly the admission-vs-classification MVCC race
    window a two-statement read would otherwise open). `None` -- every
    existing Sail caller -- preserves the exact previous behavior: fetch
    fresh via `list_current_physical_boat_claim_observations`.
    already used for design-level eligibility to combine the active
    criteria's concrete truth: any confirmed FALSE prevents a confirmed
    joint match; unresolved evidence never becomes TRUE (Required
    Behavior §B).

    Review amendment (Finding C): *active_definitions* replaces four
    previously hand-duplicated per-criterion boolean flags/blocks. Every
    `hullq.search.criteria_registry.CriterionDefinition.read_claim` has the
    identical `(observation) -> (assertion_kind, value) | None` shape, so
    the same-PhysicalBoat cross-Organization qualification
    (`_qualify_claim_field`, shared via `_qualify_claims_against_definitions`
    since SLICE-0092) now runs in one shared loop over whichever
    definitions are active, rather than one copy-pasted block per
    criterion -- this is the registry's "concrete publisher accessor"
    being genuinely consumed, not merely declared.

    Returns typed `SearchCriterionEvidence` (requested criterion + typed
    evaluation + safely observed concrete value), not bare
    `CriterionEvaluation`, so the observed value is preserved through the
    application boundary rather than existing only inside
    `CriterionEvaluation.explanation` text (Finding 1).

    Takes the resolved identity fields directly (rather than an
    `ActiveDesignLinkedListing`) so both the public bulk native-inventory
    funnel (`evaluate_native_inventory_requirements`, below) and SLICE-0084's
    authorized single-target hypothetical DRAFT preview
    (`hullq.application.broker_search_fit`) call the identical concrete
    classification kernel -- never a second, independently maintained
    concrete-claim truth path.
    """
    resolved_observations = (
        observations
        if observations is not None
        else list_current_physical_boat_claim_observations(conn, physical_boat_id)
    )
    projection, observed_by_field = _qualify_claims_against_definitions(
        resolved_observations,
        publishing_organization_id=publishing_organization_id,
        active_definitions=active_definitions,
    )
    pseudo_configuration = ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id=native_listing_id.value,
            boat_design_id=boat_design_id,
        ),
        projection=projection,
    )
    evaluation = evaluate_configuration(query, pseudo_configuration)
    if evaluation.truth is TruthState.TRUE:
        result_class = ResultClass.CONFIRMED_MATCH
    elif evaluation.truth is TruthState.FALSE:
        result_class = ResultClass.CONFIRMED_NON_MATCH
    else:
        result_class = ResultClass.INSUFFICIENT_DATA

    # `evaluate_configuration` evaluates `query.criteria` in that exact order
    # (hullq.search.configuration_engine.evaluate_configuration), so pairing
    # by position is safe and avoids re-deriving field identity by string
    # matching.
    evidence = tuple(
        SearchCriterionEvidence(
            criterion=criterion,
            evaluation=criterion_evaluation,
            observed_value=observed_by_field.get(criterion.field),
        )
        for criterion, criterion_evaluation in zip(
            query.criteria, evaluation.criterion_evaluations, strict=True
        )
    )
    return result_class, evidence


def classify_claim_only_candidate(
    observations: Sequence[CurrentPhysicalBoatClaimObservation],
    *,
    publishing_organization_id: MarketplaceOrganizationId,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
) -> tuple[ResultClass, tuple[SearchCriterionEvidence, ...]]:
    """Classify one already category-admitted, design-UNRESOLVED candidate's
    publisher-claim evidence -- SLICE-0092.

    Mirrors `classify_concrete_candidate` exactly, down to reusing the
    identical `_qualify_claims_against_definitions` per-field qualification
    -- the only difference is what happens afterwards: there is no
    BoatDesign, so this never constructs a `ConfigurationIdentity`/
    `ResolvedConfiguration` (which would require an invented
    `boat_design_id`). Instead it evaluates the bare `ConfigurationProjection`
    directly via `hullq.search.configuration_engine.evaluate_projection` --
    the identical leaf-evaluation + MUST/AND-reduce kernel
    `evaluate_configuration` itself calls, factored out for exactly this
    reuse (contract §C exact implementation boundary). No second,
    independently maintained comparator is introduced.

    Takes the already-fetched *observations* directly (contract §E: "Both
    category and constrained technical fields must refer to the same
    publisher's coherent current claim revision") -- the caller
    (`evaluate_claim_only_candidates`) reads them from the SAME single
    `list_current_physical_boat_claim_observations` call it also uses for
    the category-admission precondition, so both decisions are drawn from
    one coherent PostgreSQL statement per PhysicalBoat, never two separate
    reads that could straddle a concurrent revision write.

    Callers are responsible for the category-admission precondition
    (contract §A: publisher-owned, nonconflicted, explicit SAIL) *before*
    calling this -- see `_resolve_claim_only_category_admission` and
    `evaluate_claim_only_candidates` below. This function performs no
    category check itself; it only evaluates the requested technical
    criteria.
    """
    projection, observed_by_field = _qualify_claims_against_definitions(
        observations,
        publishing_organization_id=publishing_organization_id,
        active_definitions=active_definitions,
    )
    truth, criterion_evaluations = evaluate_projection(query, projection)
    if truth is TruthState.TRUE:
        result_class = ResultClass.CONFIRMED_MATCH
    elif truth is TruthState.FALSE:
        result_class = ResultClass.CONFIRMED_NON_MATCH
    else:
        result_class = ResultClass.INSUFFICIENT_DATA

    evidence = tuple(
        SearchCriterionEvidence(
            criterion=criterion,
            evaluation=criterion_evaluation,
            observed_value=observed_by_field.get(criterion.field),
        )
        for criterion, criterion_evaluation in zip(
            query.criteria, criterion_evaluations, strict=True
        )
    )
    return result_class, evidence


def _resolve_claim_only_category_from_observations(
    observations: Sequence[CurrentPhysicalBoatClaimObservation],
) -> VesselCategoryResolutionResult:
    """Resolve the current `VesselCategory` directly from an already-fetched
    *observations* set (SLICE-0092 contract §E coherent-snapshot requirement)
    rather than issuing a second, independent SQL read
    (`hullq.application.vessel_category_resolution.
    resolve_physical_boat_vessel_category`) the way the design-linked path
    does. `design_evidence` is always `None`: the design plane never
    contributes for a design-unresolved PhysicalBoat (mechanically identical
    treatment to calling the resolver with `boat_design_ref=None`). Reuses
    the exact same pure `hullq.domain.vessel_category.resolve_vessel_category`
    combination step -- no second category-resolution rule.
    """
    concrete_evidence = tuple(
        ConcreteVesselCategoryEvidence(
            claiming_organization_id=obs.claiming_organization_id,
            revision_id=obs.revision_id,
            recorded_by_account_id=obs.recorded_by_account_id,
            recorded_at=obs.recorded_at,
            claim=obs.vessel_category,
        )
        for obs in observations
    )
    return resolve_vessel_category(design_evidence=None, concrete_evidence=concrete_evidence)


def _resolve_claim_only_category_admission(
    category_resolution: VesselCategoryResolutionResult,
    publishing_organization_id: MarketplaceOrganizationId,
) -> tuple[bool, VesselCategoryExclusionEvidence | None]:
    """SLICE-0092 contract §A: a claim-only candidate is admitted to the new
    Sail path iff the overall resolution is `SAIL` **and** the publishing
    Organization itself (never merely another current claimant) carries an
    explicit current `VALUE_ASSERTION(SAIL)` claim in `category_resolution.
    concrete_evidence` -- "Another Organization's category assertion cannot
    lend the publisher its Sail eligibility." The design plane is
    irrelevant here by construction: callers always resolve with
    `design_evidence=None` for a design-unresolved PhysicalBoat.

    Returns `(admitted, exclusion_evidence)`. `exclusion_evidence` is
    populated only when the resolution is explicitly POWER/MOTORSAILER/
    CONFLICT (`category_resolution.is_explicitly_non_sail_or_conflicted`) --
    the bounded, enum-only `VesselCategoryExclusionEvidence` SLICE-0091
    already defined for exactly this purpose, reused unchanged. A missing/
    UNKNOWN category, or a SAIL resolution contributed only by a different
    Organization, is `(False, None)`: not an explicit exclusion, merely not
    (yet) a publisher-owned admission -- the caller classifies that as
    `INSUFFICIENT_DATA`, never `CONFIRMED_NON_MATCH`.
    """
    exclusion = (
        VesselCategoryExclusionEvidence(
            resolution=category_resolution.resolution, reason=category_resolution.reason
        )
        if category_resolution.is_explicitly_non_sail_or_conflicted
        else None
    )
    if category_resolution.resolution is not VesselCategoryResolution.SAIL:
        return False, exclusion
    publisher_entry = next(
        (
            entry
            for entry in category_resolution.concrete_evidence
            if entry.claiming_organization_id == publishing_organization_id
        ),
        None,
    )
    publisher_owns_sail = (
        publisher_entry is not None
        and publisher_entry.claim is not None
        and publisher_entry.claim.assertion_kind is AssertionKind.VALUE_ASSERTION
        and publisher_entry.claim.value is VesselCategory.SAIL
    )
    return publisher_owns_sail, exclusion


def evaluate_claim_only_candidates(
    conn: Any,
    *,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
    as_of: datetime,
) -> tuple[
    tuple[PublisherClaimCandidateEvaluation, ...],
    tuple[PublisherClaimCandidateEvaluation, ...],
    tuple[PublisherClaimCandidateEvaluation, ...],
]:
    """Evaluate every ACTIVE, design-UNRESOLVED candidate's publisher-claim
    evidence against *query* -- SLICE-0092's new claim-only Sail path.
    Returns `(matches, non_matches, insufficient_data)`, each sorted by
    `NativeListingId` exactly like the design-linked funnel.

    Shared by both accepted Sail entrypoints (pure `draft_max` via
    `hullq.application.inventory_search.evaluate_draft_max_requirement`, and
    the mixed nine-criterion funnel via
    `evaluate_native_inventory_requirements` below) -- contract §F "wire this
    optional additive path through (i) pure draft_max ... (ii) mixed
    ... Sail entrypoints", one evaluation, never two independently
    maintained claim-only funnels.

    Amendment review (PR #387) Finding D: D29 current-public eligibility
    AND freshness for the **entire** candidate population are resolved
    through exactly one batched call,
    `hullq.application.current_public_eligibility.
    resolve_current_public_eligibility_for_many` -- a small constant number
    of `= ANY(%s)` statements covering every candidate's *cheap* facts
    (lifecycle/organization/episode/boat/freshness), with the expensive
    per-candidate reads (offer/claim/cover) issued only for candidates that
    survive every cheap check. This never weakens D29 (the identical pure
    `evaluate_current_public_eligibility` evaluator decides every survivor;
    an obviously-suppressed candidate's `status` is exactly as
    authoritative from the cheap facts alone, since any one reason already
    forces `SUPPRESSED`) and never drops a candidate from the population
    (every id gets an entry). The per-PhysicalBoat claim-observation read
    -- the other part of this new path this slice fully owns -- is
    separately batched across every *eligible* candidate into exactly one
    SQL statement (`list_current_physical_boat_claim_observations_for_many`).
    The category-admission precondition (contract §A) and the technical
    per-criterion evidence (contract §E: "one coherent PostgreSQL statement
    for each PhysicalBoat") still come from that identical per-PhysicalBoat
    observation list -- batching changes only how many statements fetch
    inputs, never which rows back which decision.
    """
    all_candidates = list_active_design_unresolved_listings(conn)
    if not all_candidates:
        return (), (), ()

    bulk_eligibility = resolve_current_public_eligibility_for_many(
        conn, [candidate.native_listing_id for candidate in all_candidates], as_of=as_of
    )
    eligible_candidates: list[tuple[ActiveDesignUnresolvedListing, CurrentFreshness]] = []
    for candidate in all_candidates:
        bulk_result = bulk_eligibility.get(candidate.native_listing_id.value)
        if (
            bulk_result is None
            or bulk_result.eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE
        ):
            continue
        eligible_candidates.append((candidate, bulk_result.freshness))
    if not eligible_candidates:
        return (), (), ()

    observations_by_boat = list_current_physical_boat_claim_observations_for_many(
        conn, [candidate.physical_boat_id for candidate, _ in eligible_candidates]
    )

    matches: list[PublisherClaimCandidateEvaluation] = []
    non_matches: list[PublisherClaimCandidateEvaluation] = []
    insufficient_data: list[PublisherClaimCandidateEvaluation] = []

    for candidate, freshness in eligible_candidates:
        observations = observations_by_boat[candidate.physical_boat_id]
        category_resolution = _resolve_claim_only_category_from_observations(observations)
        admitted, exclusion = _resolve_claim_only_category_admission(
            category_resolution, candidate.publishing_organization_id
        )

        # Amendment review Finding C: retain the publisher's own current
        # observation's revision/actor/time and positive category claim as
        # typed internal provenance, regardless of match/non-match/
        # insufficient classification -- `None` only when the publisher has
        # no current claim-observation row at all for this PhysicalBoat.
        publisher_observation = next(
            (
                obs
                for obs in observations
                if obs.claiming_organization_id == candidate.publishing_organization_id
            ),
            None,
        )
        source_evidence = (
            PublisherClaimSourceEvidence(
                revision_id=publisher_observation.revision_id,
                recorded_by_account_id=publisher_observation.recorded_by_account_id,
                recorded_at=publisher_observation.recorded_at,
                category_claim=publisher_observation.vessel_category,
            )
            if publisher_observation is not None
            else None
        )

        criterion_evidence: tuple[SearchCriterionEvidence, ...]
        if exclusion is not None:
            result_class = ResultClass.CONFIRMED_NON_MATCH
            criterion_evidence = ()
        elif not admitted:
            result_class = ResultClass.INSUFFICIENT_DATA
            criterion_evidence = ()
        else:
            result_class, criterion_evidence = classify_claim_only_candidate(
                observations,
                publishing_organization_id=candidate.publishing_organization_id,
                query=query,
                active_definitions=active_definitions,
            )

        evaluation = PublisherClaimCandidateEvaluation(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            criterion_evidence=criterion_evidence,
            vessel_category_exclusion=exclusion,
            publishing_organization_id=candidate.publishing_organization_id,
            freshness_status=freshness.status,
            last_confirmed_at=freshness.last_confirmed_at,
            source_basis=PublisherClaimSourceBasis.PUBLISHER_CLAIM,
            source_evidence=source_evidence,
        )
        if result_class is ResultClass.CONFIRMED_MATCH:
            matches.append(evaluation)
        elif result_class is ResultClass.CONFIRMED_NON_MATCH:
            non_matches.append(evaluation)
        else:
            insufficient_data.append(evaluation)

    matches.sort(key=lambda m: m.native_listing_id.value)
    non_matches.sort(key=lambda m: m.native_listing_id.value)
    insufficient_data.sort(key=lambda m: m.native_listing_id.value)
    return tuple(matches), tuple(non_matches), tuple(insufficient_data)


def build_mixed_requirement_query(
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    beam_min: Decimal | None = None,
    beam_max: Decimal | None = None,
    hull_material: str | None = None,
) -> tuple[MixedAndQuery, tuple[CriterionDefinition, ...]]:
    """Validate and build the bounded multi-criterion `MixedAndQuery` + the
    exact `hullq.search.criteria_registry.CriterionDefinition`s active in it.

    Shared by the public bulk native-inventory funnel
    (`evaluate_native_inventory_requirements`, below) and SLICE-0084's
    authorized single-target hypothetical DRAFT preview
    (`hullq.application.broker_search_fit`), so the MUST/AND query this
    bounded vertical evaluates is constructed in exactly one place -- never
    a second, independently maintained query-construction path for any of
    the accepted criteria.

    At least one criterion must be supplied. Every value must already be
    parsed/validated for public syntax by its own accepted parser (each
    `CriterionDefinition`'s own `parse_value`/`allowed_values`) -- none is
    re-parsed/re-validated here, only re-checked as a defensive invariant.

    Review amendment (Finding C): the returned `active_definitions` replaces
    the previous `(specs, rudder_active)` pair -- `run_mixed_boat_design_
    configuration_query` and `classify_concrete_candidate` both consume the
    SAME tuple directly, so "which criteria are active" is computed exactly
    once per request, not re-derived at each call site.
    """
    if (
        draft_max is None
        and keel_configuration is None
        and loa_min is None
        and loa_max is None
        and rudder_configuration is None
        and hull_configuration is None
        and cockpit_position is None
        and deck_saloon is None
        and beam_min is None
        and beam_max is None
        and hull_material is None
    ):
        raise ValueError("at least one criterion must be supplied")
    if draft_max is not None and (
        not isinstance(draft_max, Decimal) or not draft_max.is_finite() or draft_max <= 0
    ):
        raise ValueError(f"draft_max must be a positive finite Decimal; got {draft_max!r}")
    assert KEEL_CONFIGURATION_DEFINITION.allowed_values is not None
    if (
        keel_configuration is not None
        and keel_configuration not in KEEL_CONFIGURATION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"keel_configuration must be one of "
            f"{sorted(KEEL_CONFIGURATION_DEFINITION.allowed_values)}; got {keel_configuration!r}"
        )
    for label, bound in (("loa_min", loa_min), ("loa_max", loa_max)):
        if bound is not None and (
            not isinstance(bound, Decimal) or not bound.is_finite() or bound <= 0
        ):
            raise ValueError(f"{label} must be a positive finite Decimal; got {bound!r}")
    if loa_min is not None and loa_max is not None and loa_min > loa_max:
        raise ValueError(f"loa_min ({loa_min}) must be <= loa_max ({loa_max})")
    assert RUDDER_CONFIGURATION_DEFINITION.allowed_values is not None
    if (
        rudder_configuration is not None
        and rudder_configuration not in RUDDER_CONFIGURATION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"rudder_configuration must be one of "
            f"{sorted(RUDDER_CONFIGURATION_DEFINITION.allowed_values)}; got {rudder_configuration!r}"
        )
    assert HULL_CONFIGURATION_DEFINITION.allowed_values is not None
    if (
        hull_configuration is not None
        and hull_configuration not in HULL_CONFIGURATION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"hull_configuration must be one of "
            f"{sorted(HULL_CONFIGURATION_DEFINITION.allowed_values)}; got {hull_configuration!r}"
        )
    assert COCKPIT_POSITION_DEFINITION.allowed_values is not None
    if (
        cockpit_position is not None
        and cockpit_position not in COCKPIT_POSITION_DEFINITION.allowed_values
    ):
        raise ValueError(
            f"cockpit_position must be one of "
            f"{sorted(COCKPIT_POSITION_DEFINITION.allowed_values)}; got {cockpit_position!r}"
        )
    assert DECK_SALOON_DEFINITION.allowed_values is not None
    if deck_saloon is not None and deck_saloon not in DECK_SALOON_DEFINITION.allowed_values:
        raise ValueError(
            f"deck_saloon must be one of "
            f"{sorted(DECK_SALOON_DEFINITION.allowed_values)}; got {deck_saloon!r}"
        )
    for label, bound in (("beam_min", beam_min), ("beam_max", beam_max)):
        if bound is not None and (
            not isinstance(bound, Decimal) or not bound.is_finite() or bound <= 0
        ):
            raise ValueError(f"{label} must be a positive finite Decimal; got {bound!r}")
    if beam_min is not None and beam_max is not None and beam_min > beam_max:
        raise ValueError(f"beam_min ({beam_min}) must be <= beam_max ({beam_max})")
    assert HULL_MATERIAL_DEFINITION.allowed_values is not None
    if hull_material is not None and hull_material not in HULL_MATERIAL_DEFINITION.allowed_values:
        raise ValueError(
            f"hull_material must be one of "
            f"{sorted(HULL_MATERIAL_DEFINITION.allowed_values)}; got {hull_material!r}"
        )

    criteria: list[NumericLeafCriterion | CategoricalLeafCriterion] = []
    active_definitions: list[CriterionDefinition] = []
    if draft_max is not None:
        criteria.append(
            NumericLeafCriterion(
                field=DRAFT_MAX_DEFINITION.projection_field,
                comparison=NumericComparisonKind.MAXIMUM,
                threshold_max=draft_max,
            )
        )
        active_definitions.append(DRAFT_MAX_DEFINITION)
    if keel_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=KEEL_CONFIGURATION_DEFINITION.projection_field, equals=keel_configuration
            )
        )
        active_definitions.append(KEEL_CONFIGURATION_DEFINITION)
    if loa_min is not None or loa_max is not None:
        # SLICE-0085 normative LOA semantics: both bounds project against the
        # SAME deduplicated loa_m field, as two independent numeric leaves --
        # never a single RANGE leaf (which would merge their evidence into
        # one explanation) and never a duplicated design-side build.
        if loa_min is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=LOA_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MINIMUM,
                    threshold_min=loa_min,
                )
            )
        if loa_max is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=LOA_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MAXIMUM,
                    threshold_max=loa_max,
                )
            )
        active_definitions.append(LOA_DEFINITION)
    if rudder_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=RUDDER_CONFIGURATION_DEFINITION.projection_field, equals=rudder_configuration
            )
        )
        active_definitions.append(RUDDER_CONFIGURATION_DEFINITION)
    if hull_configuration is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=HULL_CONFIGURATION_DEFINITION.projection_field, equals=hull_configuration
            )
        )
        active_definitions.append(HULL_CONFIGURATION_DEFINITION)
    if cockpit_position is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=COCKPIT_POSITION_DEFINITION.projection_field, equals=cockpit_position
            )
        )
        active_definitions.append(COCKPIT_POSITION_DEFINITION)
    if deck_saloon is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=DECK_SALOON_DEFINITION.projection_field, equals=deck_saloon
            )
        )
        active_definitions.append(DECK_SALOON_DEFINITION)
    if beam_min is not None or beam_max is not None:
        # SLICE-0087 normative beam semantics: both bounds project against
        # the SAME deduplicated beam_m field, as two independent numeric
        # leaves -- mirrors LOA's identical rule.
        if beam_min is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=BEAM_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MINIMUM,
                    threshold_min=beam_min,
                )
            )
        if beam_max is not None:
            criteria.append(
                NumericLeafCriterion(
                    field=BEAM_DEFINITION.projection_field,
                    comparison=NumericComparisonKind.MAXIMUM,
                    threshold_max=beam_max,
                )
            )
        active_definitions.append(BEAM_DEFINITION)
    if hull_material is not None:
        criteria.append(
            CategoricalLeafCriterion(
                field=HULL_MATERIAL_DEFINITION.projection_field, equals=hull_material
            )
        )
        active_definitions.append(HULL_MATERIAL_DEFINITION)
    return MixedAndQuery(criteria=tuple(criteria)), tuple(active_definitions)


def _merge_configuration_sets(
    design_id: str, configuration_sets: Sequence[DesignConfigurationSet]
) -> DesignConfigurationSet:
    """Merge every active criterion's own `DesignConfigurationSet` for one
    design into a single combined set, by `configuration_id`.

    Review amendment (Finding C): generalizes the previous rudder-only
    special-case merge to every active `CriterionDefinition.design_set_
    builder` uniformly -- draft_max/keel_configuration/loa (ordinary
    `FieldProjectionSpec`-backed) and rudder_configuration (generation-aware
    derived) are merged by the exact same code path, never a second
    "ordinary vs. special" branch. Every builder enumerates the identical
    baseline + eligible-NamedVariant configuration set for the same
    `boat_design` (same exclusion of a variant with unresolved
    `requires_option_ids`), so their `configuration_id`s are always
    identical sets across all of *configuration_sets* -- a direct per-id
    lookup (never positional zipping) is safe. A single-element input is
    returned unchanged (no-op merge).
    """
    if len(configuration_sets) == 1:
        return configuration_sets[0]
    by_id_per_set = [
        {c.identity.configuration_id: c for c in s.configurations} for s in configuration_sets
    ]
    base_by_id = by_id_per_set[0]
    base_set = configuration_sets[0]
    merged_configurations = []
    for configuration_id, base_config in base_by_id.items():
        numeric_values: dict[str, Any] = dict(base_config.projection.numeric_values)
        categorical_values: dict[str, Any] = dict(base_config.projection.categorical_values)
        for other_by_id in by_id_per_set[1:]:
            other_config = other_by_id[configuration_id]
            numeric_values.update(other_config.projection.numeric_values)
            categorical_values.update(other_config.projection.categorical_values)
        merged_configurations.append(
            ResolvedConfiguration(
                identity=base_config.identity,
                projection=ConfigurationProjection(
                    numeric_values=numeric_values, categorical_values=categorical_values
                ),
            )
        )
    return DesignConfigurationSet(
        design_id=design_id,
        configurations=tuple(merged_configurations),
        configuration_space_complete=base_set.configuration_space_complete,
        option_constraints=base_set.option_constraints,
        variant_constraints=base_set.variant_constraints,
        is_fixture=base_set.is_fixture,
    )


def run_mixed_boat_design_configuration_query(
    conn: Any,
    query: MixedAndQuery,
    boat_designs: Iterable[Mapping[str, Any]],
    active_definitions: Sequence[CriterionDefinition],
) -> BoatDesignConfigurationQueryResult:
    """Evaluate *query* against every design's configuration set, merging
    every active criterion's own `design_set_builder` output (SLICE-0085,
    review amendment Finding C).

    Review amendment (Finding C): replaces the previous "ordinary
    `FieldProjectionSpec`-list fast path, with a rudder-only special merge"
    split -- every active definition's `design_set_builder` is called and
    merged uniformly via `_merge_configuration_sets`, regardless of whether
    its own projection is `FieldProjectionSpec`-backed or a generation-aware
    derived value. No second, independently maintained FieldResolution/
    configuration-evaluation kernel is introduced; `run_configuration_query`
    (the unmodified shared kernel) still does the actual truth evaluation.
    """
    boat_designs = tuple(boat_designs)
    if not boat_designs:
        return BoatDesignConfigurationQueryResult(
            outcome=ConfigurationSearchOutcome(
                confirmed_matches=(), confirmed_non_matches=(), insufficient_data=()
            ),
            configurations_by_id={},
        )
    merged_sets = tuple(
        _merge_configuration_sets(
            boat_design["id"],
            [definition.design_set_builder(conn, boat_design) for definition in active_definitions],
        )
        for boat_design in boat_designs
    )
    configurations_by_id = {
        configuration.identity.configuration_id: configuration
        for configuration_set in merged_sets
        for configuration in configuration_set.configurations
    }
    outcome = run_configuration_query(query, merged_sets)
    return BoatDesignConfigurationQueryResult(
        outcome=outcome, configurations_by_id=configurations_by_id
    )


def evaluate_native_inventory_requirements(
    conn: Any,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    beam_min: Decimal | None = None,
    beam_max: Decimal | None = None,
    hull_material: str | None = None,
    as_of: datetime,
) -> NativeInventorySearchOutcome:
    """Evaluate the bounded mixed vertical against real persisted state.

    At least one criterion must be supplied. Every value must already be
    parsed/validated for public syntax by its own accepted parser -- see
    `build_mixed_requirement_query`'s docstring for the exact list. None is
    re-parsed/re-validated for public syntax here.

    SLICE-0069 (supersedes the SLICE-0052 §7.2 freshness-only narrowing):
    every ACTIVE design-linked candidate is resolved against the canonical
    D29 CurrentPublicEligibility authority
    (`hullq.application.current_public_eligibility`) at the explicit *as_of*
    boundary before any technical classification. Current-public-ineligible
    candidates are excluded outright -- never counted as insufficient data.

    Finding 1 (amendment): a candidate whose BoatDesign is *not* a design-
    level `CONFIRMED_MATCH` is no longer silently dropped from every result
    surface. Its `DesignQueryEvaluation` (`CONFIRMED_NON_MATCH` or
    `INSUFFICIENT_DATA`, e.g. an unsupported keel taxonomy mapping) is
    attached and the listing is classified accordingly -- fail-closed,
    outside the primary confirmed-match set, but never erased from the
    application evidence. A candidate whose BoatDesign could not even be
    durably fetched (`hullq.persistence.identity_readback.fetch_boat_design`
    returns `None` -- a dangling `BoatDesignRef`, a distinct data-integrity
    condition from an evaluated-but-insufficient design) is excluded exactly
    as SLICE-0051's own funnel excludes it: there is no `DesignQueryEvaluation`
    to attach because the design was never evaluated at all.

    Finding 1 (second amendment): every candidate's
    `NativeInventoryCandidateEvaluation.design_configuration_evidence` is
    populated from `run_mixed_boat_design_configuration_query`'s
    `configurations_by_id`, so the safely resolved/observed BoatDesign/
    NamedVariant canonical value behind each design-side criterion
    evaluation remains typed and recoverable, not only the aggregate
    truth/reason `DesignQueryEvaluation` itself carries.
    """
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

    # SLICE-0092: the new design-unresolved claim-only Sail path is
    # evaluated unconditionally, independent of whether any design-linked
    # candidate exists at all -- it is an entirely separate candidate
    # enumeration (`list_active_design_unresolved_listings`), not a subset
    # or fallback of the design-linked one below.
    claim_only_matches, claim_only_non_matches, claim_only_insufficient_data = (
        evaluate_claim_only_candidates(
            conn, query=query, active_definitions=active_definitions, as_of=as_of
        )
    )

    def _empty() -> NativeInventorySearchOutcome:
        return NativeInventorySearchOutcome(
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
            query=query,
            confirmed_matches=(),
            confirmed_non_matches=(),
            insufficient_data=(),
            claim_only_matches=claim_only_matches,
            claim_only_non_matches=claim_only_non_matches,
            claim_only_insufficient_data=claim_only_insufficient_data,
        )

    all_candidates = list_active_design_linked_listings(conn)
    if not all_candidates:
        return _empty()

    current_candidates = []
    for candidate in all_candidates:
        eligibility = resolve_current_public_eligibility(
            conn, candidate.native_listing_id, as_of=as_of
        )
        if eligibility is None or eligibility.status is not CurrentPublicEligibilityStatus.ELIGIBLE:
            continue
        freshness = resolve_current_freshness(conn, candidate.native_listing_id, as_of=as_of)
        current_candidates.append((candidate, freshness))
    if not current_candidates:
        return _empty()

    distinct_design_ids = sorted({c.boat_design_ref.value for c, _ in current_candidates})
    boat_designs = []
    for design_id in distinct_design_ids:
        raw_design = fetch_boat_design(conn, design_id)
        if raw_design is not None:
            boat_designs.append(raw_design)

    design_result = run_mixed_boat_design_configuration_query(
        conn, query, boat_designs, active_definitions
    )
    design_evaluation_by_id: dict[str, DesignQueryEvaluation] = {
        evaluation.design_id: evaluation
        for evaluation in (
            design_result.outcome.confirmed_matches
            + design_result.outcome.confirmed_non_matches
            + design_result.outcome.insufficient_data
        )
    }

    confirmed_matches: list[NativeInventoryCandidateEvaluation] = []
    confirmed_non_matches: list[NativeInventoryCandidateEvaluation] = []
    insufficient_data: list[NativeInventoryCandidateEvaluation] = []

    for candidate, freshness in current_candidates:
        design_evaluation = design_evaluation_by_id.get(candidate.boat_design_ref.value)
        if design_evaluation is None:
            # Dangling BoatDesignRef (no durable canonical design to
            # evaluate at all) -- never a candidate, exactly like SLICE-0051.
            continue

        design_configuration_evidence = tuple(
            build_configuration_evidence(
                query,
                configuration_evaluation,
                design_result.configurations_by_id[configuration_evaluation.configuration_id],
            )
            for configuration_evaluation in design_evaluation.configuration_evaluations
        )

        # Explicit annotation: a bare `()` literal below would otherwise be
        # inferred as the empty-tuple type `tuple[()]`, conflicting with the
        # `tuple[SearchCriterionEvidence, ...]` `classify_concrete_candidate`
        # assigns in the sibling branch.
        concrete_evidence: tuple[SearchCriterionEvidence, ...]
        if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
            # SLICE-0091 §A/§C: category is an admission/type foundation,
            # not a tenth technical Sail criterion -- this fail-closed
            # pre-filter runs *before* the concrete nine-criterion
            # classification, never alongside it as a CriterionDefinition.
            # An explicit POWER/MOTORSAILER/CONFLICT resolution excludes the
            # candidate from a confirmed Sail match outright; UNKNOWN
            # (including every legacy null-category row) is deliberately
            # untouched, preserving exact pre-0091 Sail-only behavior.
            category_resolution = resolve_physical_boat_vessel_category(
                conn,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_ref=candidate.boat_design_ref,
            )
            if category_resolution.is_explicitly_non_sail_or_conflicted:
                result_class = ResultClass.CONFIRMED_NON_MATCH
                concrete_evidence = ()
                # Amendment Finding I: retain *why* -- bounded, enum-only,
                # never the full result (which can name a different
                # claiming Organization under CROSS_ORGANIZATION_DISAGREEMENT).
                vessel_category_exclusion = VesselCategoryExclusionEvidence(
                    resolution=category_resolution.resolution,
                    reason=category_resolution.reason,
                )
            else:
                result_class, concrete_evidence = classify_concrete_candidate(
                    conn,
                    native_listing_id=candidate.native_listing_id,
                    publishing_organization_id=candidate.publishing_organization_id,
                    physical_boat_id=candidate.physical_boat_id,
                    boat_design_id=candidate.boat_design_ref.value,
                    query=query,
                    active_definitions=active_definitions,
                )
                vessel_category_exclusion = None
        else:
            # Design/configuration eligibility never admitted this design to
            # the concrete funnel (Required Behavior §C) -- the listing is
            # classified directly from the design-level result, fail-closed,
            # without ever consulting the concrete PhysicalBoat claim.
            # Finding 1: this evidence is retained, not discarded.
            result_class = design_evaluation.result_class
            concrete_evidence = ()
            vessel_category_exclusion = None

        evaluation = NativeInventoryCandidateEvaluation(
            native_listing_id=candidate.native_listing_id,
            result_class=result_class,
            design_evaluation=design_evaluation,
            design_configuration_evidence=design_configuration_evidence,
            concrete_criterion_evidence=concrete_evidence,
            vessel_category_exclusion=vessel_category_exclusion,
            publishing_organization_id=candidate.publishing_organization_id,
            freshness_status=freshness.status,
            last_confirmed_at=freshness.last_confirmed_at,
        )
        if result_class is ResultClass.CONFIRMED_MATCH:
            confirmed_matches.append(evaluation)
        elif result_class is ResultClass.CONFIRMED_NON_MATCH:
            confirmed_non_matches.append(evaluation)
        else:
            insufficient_data.append(evaluation)

    confirmed_matches.sort(key=lambda m: m.native_listing_id.value)
    confirmed_non_matches.sort(key=lambda m: m.native_listing_id.value)
    insufficient_data.sort(key=lambda m: m.native_listing_id.value)

    return NativeInventorySearchOutcome(
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
        query=query,
        confirmed_matches=tuple(confirmed_matches),
        confirmed_non_matches=tuple(confirmed_non_matches),
        insufficient_data=tuple(insufficient_data),
        claim_only_matches=claim_only_matches,
        claim_only_non_matches=claim_only_non_matches,
        claim_only_insufficient_data=claim_only_insufficient_data,
    )


def _classify_design_linked_page_candidate(
    conn: Any,
    candidate: ActiveNativeListingCandidate,
    freshness: CurrentFreshness,
    *,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
    design_evaluation_by_id: Mapping[str, DesignQueryEvaluation],
    configurations_by_id: Mapping[str, ResolvedConfiguration],
) -> NativeInventoryCandidateEvaluation | None:
    """One design-linked candidate's classification for the bounded page
    path -- byte-identical decision logic to
    `evaluate_native_inventory_requirements`'s own per-candidate loop body,
    factored out so the bounded page evaluator below can call it from a
    single global-order walk. Returns `None` for a dangling `BoatDesignRef`
    (no `DesignQueryEvaluation` to attach) -- exactly like the unbounded
    funnel, this is never a confirmed candidate at all.
    """
    assert candidate.boat_design_ref is not None
    design_evaluation = design_evaluation_by_id.get(candidate.boat_design_ref.value)
    if design_evaluation is None:
        return None

    design_configuration_evidence = tuple(
        build_configuration_evidence(
            query,
            configuration_evaluation,
            configurations_by_id[configuration_evaluation.configuration_id],
        )
        for configuration_evaluation in design_evaluation.configuration_evaluations
    )

    concrete_evidence: tuple[SearchCriterionEvidence, ...]
    vessel_category_exclusion: VesselCategoryExclusionEvidence | None
    if design_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
        category_resolution = resolve_physical_boat_vessel_category(
            conn,
            physical_boat_id=candidate.physical_boat_id,
            boat_design_ref=candidate.boat_design_ref,
        )
        if category_resolution.is_explicitly_non_sail_or_conflicted:
            result_class = ResultClass.CONFIRMED_NON_MATCH
            concrete_evidence = ()
            vessel_category_exclusion = VesselCategoryExclusionEvidence(
                resolution=category_resolution.resolution, reason=category_resolution.reason
            )
        else:
            result_class, concrete_evidence = classify_concrete_candidate(
                conn,
                native_listing_id=candidate.native_listing_id,
                publishing_organization_id=candidate.publishing_organization_id,
                physical_boat_id=candidate.physical_boat_id,
                boat_design_id=candidate.boat_design_ref.value,
                query=query,
                active_definitions=active_definitions,
            )
            vessel_category_exclusion = None
    else:
        result_class = design_evaluation.result_class
        concrete_evidence = ()
        vessel_category_exclusion = None

    return NativeInventoryCandidateEvaluation(
        native_listing_id=candidate.native_listing_id,
        result_class=result_class,
        design_evaluation=design_evaluation,
        design_configuration_evidence=design_configuration_evidence,
        concrete_criterion_evidence=concrete_evidence,
        vessel_category_exclusion=vessel_category_exclusion,
        publishing_organization_id=candidate.publishing_organization_id,
        freshness_status=freshness.status,
        last_confirmed_at=freshness.last_confirmed_at,
    )


def classify_claim_only_page_candidate(
    candidate: ActiveNativeListingCandidate,
    freshness: CurrentFreshness,
    *,
    query: MixedAndQuery,
    active_definitions: Sequence[CriterionDefinition],
    observations: Sequence[CurrentPhysicalBoatClaimObservation],
) -> PublisherClaimCandidateEvaluation:
    """One design-unresolved candidate's classification for the bounded page
    path -- byte-identical decision logic to `evaluate_claim_only_candidates`'s
    own per-candidate loop body, factored out for the same reason as
    `_classify_design_linked_page_candidate` above.
    """
    assert candidate.boat_design_ref is None
    category_resolution = _resolve_claim_only_category_from_observations(observations)
    admitted, exclusion = _resolve_claim_only_category_admission(
        category_resolution, candidate.publishing_organization_id
    )

    publisher_observation = next(
        (
            obs
            for obs in observations
            if obs.claiming_organization_id == candidate.publishing_organization_id
        ),
        None,
    )
    source_evidence = (
        PublisherClaimSourceEvidence(
            revision_id=publisher_observation.revision_id,
            recorded_by_account_id=publisher_observation.recorded_by_account_id,
            recorded_at=publisher_observation.recorded_at,
            category_claim=publisher_observation.vessel_category,
        )
        if publisher_observation is not None
        else None
    )

    criterion_evidence: tuple[SearchCriterionEvidence, ...]
    if exclusion is not None:
        result_class = ResultClass.CONFIRMED_NON_MATCH
        criterion_evidence = ()
    elif not admitted:
        result_class = ResultClass.INSUFFICIENT_DATA
        criterion_evidence = ()
    else:
        result_class, criterion_evidence = classify_claim_only_candidate(
            observations,
            publishing_organization_id=candidate.publishing_organization_id,
            query=query,
            active_definitions=active_definitions,
        )

    return PublisherClaimCandidateEvaluation(
        native_listing_id=candidate.native_listing_id,
        result_class=result_class,
        criterion_evidence=criterion_evidence,
        vessel_category_exclusion=exclusion,
        publishing_organization_id=candidate.publishing_organization_id,
        freshness_status=freshness.status,
        last_confirmed_at=freshness.last_confirmed_at,
        source_basis=PublisherClaimSourceBasis.PUBLISHER_CLAIM,
        source_evidence=source_evidence,
    )


def evaluate_native_inventory_requirements_page(
    conn: Any,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    loa_min: Decimal | None = None,
    loa_max: Decimal | None = None,
    rudder_configuration: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    beam_min: Decimal | None = None,
    beam_max: Decimal | None = None,
    hull_material: str | None = None,
    as_of: datetime,
    after_native_listing_id: str | None,
    page_size: int,
    candidate_scan_budget: int = DEFAULT_CANDIDATE_SCAN_BUDGET,
    request_deadline_seconds: float = DEFAULT_REQUEST_DEADLINE_SECONDS,
) -> NativeInventorySearchResultPage:
    """Evaluate one bounded page of the Sail mixed-requirement vertical --
    SLICE-0096's new public entrypoint.

    Reads at most *candidate_scan_budget* ACTIVE candidates (one bounded SQL
    call, `hullq.persistence.inventory_search
    .list_active_native_listing_candidates_page`), globally ordered by
    `NativeListingId` across BOTH the design-linked and design-unresolved
    planes together (contract §2's "one global, monotonically increasing
    ... cursor"). Every fetched candidate is walked in that exact global
    order and classified using the IDENTICAL decision kernels the unbounded
    `evaluate_native_inventory_requirements`/`evaluate_claim_only_candidates`
    funnels already use (`_classify_design_linked_page_candidate`/
    `classify_claim_only_page_candidate` above, which are themselves
    byte-identical extractions of those funnels' own per-candidate logic) --
    never a second, independently maintained Search truth path.

    The walk stops as soon as the combined `confirmed_matches`/
    `claim_only_matches` count reaches *page_size*, or the fetched batch is
    exhausted, whichever comes first -- this is NOT a "keep fetching more
    candidates until page_size matches" loop (that is explicitly forbidden
    by contract §3): at most one bounded SQL page is ever fetched per call,
    and stopping early only skips evaluating ALREADY-FETCHED rows still held
    in memory from that one call. A D29-ineligible or dangling-BoatDesignRef
    candidate still advances the cursor (it was examined and excluded) but
    contributes no match/insufficient-data outcome, mirroring the unbounded
    funnels' identical exclusion rule.

    `evaluation_state`/`next_after_native_listing_id` are decided from three
    disjoint cases: (1) stopped early with unevaluated fetched rows still
    remaining -> `PARTIAL`, cursor = last EVALUATED candidate; (2) the fetch
    returned fewer rows than *candidate_scan_budget* (a genuine, provable
    end-of-table) and every fetched row was evaluated -> `COMPLETE`; (3) the
    fetch returned exactly *candidate_scan_budget* rows and every one was
    evaluated (the "final batch happens to fill the page exactly"
    ambiguity) -> one bounded O(1) existence lookahead
    (`active_native_listing_candidate_exists_after`) decides `COMPLETE` vs
    `PARTIAL` definitively, never a guess.
    """
    if not isinstance(page_size, int) or isinstance(page_size, bool) or not (1 <= page_size <= 50):
        raise ValueError(f"page_size must be an int in [1, 50]; got {page_size!r}")
    # candidate_scan_budget is an internal server-side safety cap, independent
    # of page_size -- a budget smaller than page_size is a legitimate (if
    # conservative) tuning choice, not an error: it simply means this page
    # may return fewer than page_size matches before PARTIAL, never a reason
    # to reject the request outright.
    if (
        not isinstance(candidate_scan_budget, int)
        or isinstance(candidate_scan_budget, bool)
        or (candidate_scan_budget < 1)
    ):
        raise ValueError(
            f"candidate_scan_budget must be a positive int; got {candidate_scan_budget!r}"
        )
    if (
        not isinstance(request_deadline_seconds, (int, float))
        or isinstance(request_deadline_seconds, bool)
        or request_deadline_seconds <= 0
    ):
        raise ValueError(
            f"request_deadline_seconds must be a positive number; got {request_deadline_seconds!r}"
        )

    # Finding E2: starts here so it covers the design-fetch loop and the
    # main per-candidate loop below -- the only two sites in this function
    # that issue a variable, population-dependent number of SQL statements.
    deadline = time.monotonic() + request_deadline_seconds

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

    batch = list_active_native_listing_candidates_page(
        conn, after_native_listing_id=after_native_listing_id, limit=candidate_scan_budget
    )
    if not batch:
        return NativeInventorySearchResultPage(
            query=query,
            evaluation_state=SearchPageEvaluationState.COMPLETE,
            next_after_native_listing_id=None,
            confirmed_matches=(),
            claim_only_matches=(),
            design_linked_insufficient_data_count=0,
            claim_only_insufficient_data_count=0,
        )

    bulk_eligibility = resolve_current_public_eligibility_for_many(
        conn, [candidate.native_listing_id for candidate in batch], as_of=as_of
    )
    eligible_by_id: dict[str, CurrentFreshness] = {}
    for candidate in batch:
        bulk_result = bulk_eligibility.get(candidate.native_listing_id.value)
        if (
            bulk_result is not None
            and bulk_result.eligibility.status is CurrentPublicEligibilityStatus.ELIGIBLE
        ):
            eligible_by_id[candidate.native_listing_id.value] = bulk_result.freshness

    design_linked_eligible = [
        candidate
        for candidate in batch
        if candidate.boat_design_ref is not None
        and candidate.native_listing_id.value in eligible_by_id
    ]
    claim_only_eligible = [
        candidate
        for candidate in batch
        if candidate.boat_design_ref is None and candidate.native_listing_id.value in eligible_by_id
    ]

    design_evaluation_by_id: dict[str, DesignQueryEvaluation] = {}
    configurations_by_id: Mapping[str, ResolvedConfiguration] = {}
    if design_linked_eligible:
        distinct_design_ids = sorted(
            {
                candidate.boat_design_ref.value
                for candidate in design_linked_eligible
                if candidate.boat_design_ref is not None
            }
        )
        boat_designs = []
        for design_id in distinct_design_ids:
            check_request_deadline(deadline)
            raw_design = fetch_boat_design(conn, design_id)
            if raw_design is not None:
                boat_designs.append(raw_design)
        design_result = run_mixed_boat_design_configuration_query(
            conn, query, boat_designs, active_definitions
        )
        design_evaluation_by_id = {
            evaluation.design_id: evaluation
            for evaluation in (
                design_result.outcome.confirmed_matches
                + design_result.outcome.confirmed_non_matches
                + design_result.outcome.insufficient_data
            )
        }
        configurations_by_id = design_result.configurations_by_id

    claim_only_observations_by_boat: dict[
        PhysicalBoatId, list[CurrentPhysicalBoatClaimObservation]
    ] = {}
    if claim_only_eligible:
        claim_only_observations_by_boat = list_current_physical_boat_claim_observations_for_many(
            conn, [candidate.physical_boat_id for candidate in claim_only_eligible]
        )

    confirmed_matches: list[NativeInventoryCandidateEvaluation] = []
    claim_only_matches: list[PublisherClaimCandidateEvaluation] = []
    design_linked_insufficient_data_count = 0
    claim_only_insufficient_data_count = 0
    last_examined_id: str | None = None
    exhausted_batch = True

    for index, candidate in enumerate(batch):
        check_request_deadline(deadline)
        last_examined_id = candidate.native_listing_id.value
        freshness = eligible_by_id.get(candidate.native_listing_id.value)
        if freshness is None:
            continue

        if candidate.boat_design_ref is not None:
            evaluation = _classify_design_linked_page_candidate(
                conn,
                candidate,
                freshness,
                query=query,
                active_definitions=active_definitions,
                design_evaluation_by_id=design_evaluation_by_id,
                configurations_by_id=configurations_by_id,
            )
            if evaluation is None:
                continue
            if evaluation.result_class is ResultClass.CONFIRMED_MATCH:
                confirmed_matches.append(evaluation)
            elif evaluation.result_class is ResultClass.INSUFFICIENT_DATA:
                design_linked_insufficient_data_count += 1
        else:
            observations = claim_only_observations_by_boat.get(candidate.physical_boat_id, [])
            claim_evaluation = classify_claim_only_page_candidate(
                candidate,
                freshness,
                query=query,
                active_definitions=active_definitions,
                observations=observations,
            )
            if claim_evaluation.result_class is ResultClass.CONFIRMED_MATCH:
                claim_only_matches.append(claim_evaluation)
            elif claim_evaluation.result_class is ResultClass.INSUFFICIENT_DATA:
                claim_only_insufficient_data_count += 1

        if len(confirmed_matches) + len(claim_only_matches) >= page_size:
            exhausted_batch = index == len(batch) - 1
            break

    assert last_examined_id is not None
    if exhausted_batch and len(batch) < candidate_scan_budget:
        evaluation_state = SearchPageEvaluationState.COMPLETE
        next_after_native_listing_id = None
    elif exhausted_batch:
        # Exact-fill ambiguity (contract §1: "Look-ahead or equivalent
        # bounded exhaustion proof is required ... when the final batch
        # happens to fill the page exactly") -- one bounded O(1) existence
        # check, never a guess.
        if active_native_listing_candidate_exists_after(conn, last_examined_id):
            evaluation_state = SearchPageEvaluationState.PARTIAL
            next_after_native_listing_id = last_examined_id
        else:
            evaluation_state = SearchPageEvaluationState.COMPLETE
            next_after_native_listing_id = None
    else:
        evaluation_state = SearchPageEvaluationState.PARTIAL
        next_after_native_listing_id = last_examined_id

    return NativeInventorySearchResultPage(
        query=query,
        evaluation_state=evaluation_state,
        next_after_native_listing_id=next_after_native_listing_id,
        confirmed_matches=tuple(confirmed_matches),
        claim_only_matches=tuple(claim_only_matches),
        design_linked_insufficient_data_count=design_linked_insufficient_data_count,
        claim_only_insufficient_data_count=claim_only_insufficient_data_count,
    )
