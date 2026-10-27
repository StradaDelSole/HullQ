"""Explicit Sail/Power/Motorsailer vessel category resolution -- SLICE-0091.

Implements the scoped foundation selected by
`docs/slices/SLICE-0091-vessel-category-foundation.md` §A/§B: one explicit,
source-qualified and deterministic category contract for canonical design
and concrete offered boats, independent of (and never a technical hard
Search criterion alongside) the nine accepted Sail criteria.

Two independent source planes, mirroring the existing design/concrete
separation already used for every other PhysicalBoat fact:

    DesignVesselCategoryAssertion  -- canonical BoatDesign-level category,
        only when established by authorized catalog/design evidence
        (`hullq.persistence.boat_design_category`).
    VesselCategoryClaim            -- the publisher's own concrete PhysicalBoat
        category claim (`hullq.domain.physical_boat_claims`), already wired
        into the existing immutable claim-revision machinery.

`resolve_vessel_category` is the single pure function that combines both
planes (plus every claiming Organization's current concrete claim for the
same PhysicalBoat -- the existing SLICE-0051 §G same-PhysicalBoat
cross-Organization contradiction guard, generalized to this field) into one
deterministic `VesselCategoryResolution`. It never infers a category from a
display name, hull shape, rig text, engine count, model name, keel or
marketing label -- its only inputs are already-typed, already-sourced
assertions. `CONFLICT` and `UNKNOWN` are resolution-time outcomes only: they
are never accepted as a publisher-input value and never promoted to a
positive `VesselCategory` by any heuristic. No second Search truth kernel is
introduced -- this module has no persistence, ORM, CriterionDefinition or
MUST/AND evaluation of its own; it is consulted as a fail-closed pre-filter
by `hullq.application.vessel_category_resolution` / the native inventory
Search funnel, never as a tenth technical criterion.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from hullq.domain.physical_boat_claims import (
    AssertionKind,
    PhysicalBoatClaimRevisionId,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.provenance import ResolverMetadata
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId

__all__ = [
    "BoatDesignCategoryAssertionId",
    "ConcreteVesselCategoryEvidence",
    "DesignVesselCategoryAssertion",
    "DesignVesselCategoryEvidence",
    "VesselCategoryExclusionEvidence",
    "VesselCategoryResolution",
    "VesselCategoryResolutionReason",
    "VesselCategoryResolutionResult",
    "resolve_vessel_category",
]


def _require_kind(value: object, kind: type, field_label: str) -> None:
    """Fail closed when *value* is not an instance of the required *kind*.

    Mirrors the equivalent helper in `hullq.domain.physical_boat_claims` and
    `hullq.domain.market_identity`.
    """
    if not isinstance(value, kind):
        raise TypeError(f"{field_label} must be a {kind.__name__}, got {type(value).__name__}")


@dataclass(frozen=True)
class BoatDesignCategoryAssertionId:
    """Identifies one immutable BoatDesign category assertion revision.

    Not interchangeable with `PhysicalBoatClaimRevisionId` or any other
    accepted identity kind, even when the raw text value collides.
    """

    value: str

    def __post_init__(self) -> None:
        if not self.value:
            raise ValueError("BoatDesignCategoryAssertionId.value must be non-empty")


#: Identical two-state shape to the concrete `VesselCategoryClaim` --
#: no `ABSENT`, no `NOT_APPLICABLE`. A BoatDesign's category is either
#: positively established by authorized catalog/design evidence or
#: explicitly `UNKNOWN`; it is never "absent" the way, say, a boat name can
#: genuinely not exist.
_DESIGN_VESSEL_CATEGORY_ALLOWED = frozenset({AssertionKind.VALUE_ASSERTION, AssertionKind.UNKNOWN})


def _validate_design_assertion(assertion_kind: AssertionKind, value: VesselCategory | None) -> None:
    _require_kind(assertion_kind, AssertionKind, "DesignVesselCategoryAssertion.assertion_kind")
    if assertion_kind not in _DESIGN_VESSEL_CATEGORY_ALLOWED:
        allowed = sorted(k.value for k in _DESIGN_VESSEL_CATEGORY_ALLOWED)
        raise ValueError(
            f"DesignVesselCategoryAssertion.assertion_kind must be one of {allowed}, "
            f"got {assertion_kind.value!r}"
        )
    if assertion_kind is AssertionKind.VALUE_ASSERTION:
        if value is None:
            raise ValueError(
                "DesignVesselCategoryAssertion.value is required when "
                "assertion_kind is VALUE_ASSERTION"
            )
        _require_kind(value, VesselCategory, "DesignVesselCategoryAssertion.value")
    elif value is not None:
        raise ValueError(
            f"DesignVesselCategoryAssertion.value must be None when "
            f"assertion_kind is {assertion_kind.value}"
        )


@dataclass(frozen=True)
class DesignVesselCategoryAssertion:
    """The canonical BoatDesign-level category assertion -- SLICE-0091 §B.

    Structurally mirrors `VesselCategoryClaim` (`VALUE_ASSERTION(VesselCategory)`
    or explicit `UNKNOWN`) but is a distinct, never-interchangeable type: it
    represents authorized catalog/design evidence about the *design*, never
    a publisher's statement about one concrete vessel. Linking a design to a
    PhysicalBoat does not silently produce a current concrete assertion, and
    a current concrete assertion never backfills or overwrites this plane.
    """

    assertion_kind: AssertionKind
    value: VesselCategory | None = None

    def __post_init__(self) -> None:
        _validate_design_assertion(self.assertion_kind, self.value)


@dataclass(frozen=True)
class DesignVesselCategoryEvidence:
    """The exact persisted design-plane assertion backing one resolution --
    amendment review Finding C. Retains the assertion's own durable identity,
    issuer and recorded time so "which record, asserted by whom, when" is
    always answerable from the resolution result alone, without a second
    lookup against `hullq.persistence.boat_design_category`.
    """

    assertion_id: BoatDesignCategoryAssertionId
    boat_design_id: str
    assertion: DesignVesselCategoryAssertion
    issuer: ResolverMetadata
    recorded_at: datetime
    previous_assertion_id: BoatDesignCategoryAssertionId | None

    def __post_init__(self) -> None:
        _require_kind(
            self.assertion_id,
            BoatDesignCategoryAssertionId,
            "DesignVesselCategoryEvidence.assertion_id",
        )
        _require_kind(
            self.assertion, DesignVesselCategoryAssertion, "DesignVesselCategoryEvidence.assertion"
        )
        _require_kind(self.issuer, ResolverMetadata, "DesignVesselCategoryEvidence.issuer")
        if self.previous_assertion_id is not None:
            _require_kind(
                self.previous_assertion_id,
                BoatDesignCategoryAssertionId,
                "DesignVesselCategoryEvidence.previous_assertion_id",
            )


@dataclass(frozen=True)
class ConcreteVesselCategoryEvidence:
    """One claiming Organization's current concrete-plane observation
    backing one resolution -- amendment review Finding C. `claim` is `None`
    when that Organization's current claim snapshot omits `vessel_category`
    entirely -- mechanically distinct from an explicit `UNKNOWN`
    `VesselCategoryClaim`, exactly like every other optional PhysicalBoat
    claim field. `revision_id`/`recorded_by_account_id`/`recorded_at`
    identify the exact current claim revision this observation came from, so
    a cross-Organization `CONFLICT` can always name which current source
    disagrees and when it was recorded -- never only an anonymous value.

    Intended for authorized internal consumption only (the inspectable
    readback this slice's contract requires): never serialize the full
    tuple of these to any public/buyer-facing surface, since
    `claiming_organization_id` identifies a real, potentially competing
    Organization.
    """

    claiming_organization_id: MarketplaceOrganizationId
    revision_id: PhysicalBoatClaimRevisionId
    recorded_by_account_id: AccountId
    recorded_at: datetime
    claim: VesselCategoryClaim | None

    def __post_init__(self) -> None:
        _require_kind(
            self.claiming_organization_id,
            MarketplaceOrganizationId,
            "ConcreteVesselCategoryEvidence.claiming_organization_id",
        )
        _require_kind(
            self.revision_id,
            PhysicalBoatClaimRevisionId,
            "ConcreteVesselCategoryEvidence.revision_id",
        )
        _require_kind(
            self.recorded_by_account_id,
            AccountId,
            "ConcreteVesselCategoryEvidence.recorded_by_account_id",
        )
        if self.claim is not None:
            _require_kind(self.claim, VesselCategoryClaim, "ConcreteVesselCategoryEvidence.claim")


class VesselCategoryResolution(StrEnum):
    """The resolved current category state for one PhysicalBoat -- SLICE-0091 §A.

    `SAIL`/`POWER`/`MOTORSAILER` here mean "the resolution process arrived at
    this positive value", not "a source directly asserted this resolution
    value" (sources only ever assert a `VesselCategory`, never a
    `VesselCategoryResolution`). `UNKNOWN` means no reliable selected
    category could be determined. `CONFLICT` means an unresolved, material
    contradiction across the authorized current sources -- a resolution
    outcome only, never a publisher-input enum value and never a fifth
    `AssertionKind`.
    """

    SAIL = "SAIL"
    POWER = "POWER"
    MOTORSAILER = "MOTORSAILER"
    UNKNOWN = "UNKNOWN"
    CONFLICT = "CONFLICT"


class VesselCategoryResolutionReason(StrEnum):
    """Why `resolve_vessel_category` reached its result -- the exact
    precedence/resolution matrix required by SLICE-0091 §B, made inspectable
    rather than left implicit in control flow."""

    #: Neither the design plane nor any claiming Organization has ever
    #: recorded any category assertion for this PhysicalBoat at all.
    NO_EVIDENCE = "NO_EVIDENCE"
    #: At least one plane carries an explicit `UNKNOWN`, and neither plane
    #: carries a positive value.
    BOTH_UNKNOWN = "BOTH_UNKNOWN"
    #: The design plane carries a positive value; the concrete plane is
    #: either entirely unestablished or explicitly `UNKNOWN`.
    DESIGN_ONLY = "DESIGN_ONLY"
    #: The concrete plane carries one single agreed-upon positive value
    #: (across every claiming Organization); the design plane is either
    #: unresolved (no design link / no design evidence) or explicitly
    #: `UNKNOWN`.
    CONCRETE_ONLY = "CONCRETE_ONLY"
    #: Both planes carry a positive value and they agree.
    SOURCES_AGREE = "SOURCES_AGREE"
    #: Both planes carry a positive value and they disagree.
    DESIGN_CONCRETE_DISAGREEMENT = "DESIGN_CONCRETE_DISAGREEMENT"
    #: Two or more claiming Organizations currently assert different
    #: positive concrete values for the same PhysicalBoat (SLICE-0051 §G's
    #: same-PhysicalBoat contradiction guard, generalized to this field).
    #: Takes precedence over every design-plane comparison: the concrete
    #: plane is already internally contradictory.
    CROSS_ORGANIZATION_DISAGREEMENT = "CROSS_ORGANIZATION_DISAGREEMENT"


_POSITIVE_REASONS = frozenset(
    {
        VesselCategoryResolutionReason.DESIGN_ONLY,
        VesselCategoryResolutionReason.CONCRETE_ONLY,
        VesselCategoryResolutionReason.SOURCES_AGREE,
    }
)
_UNKNOWN_REASONS = frozenset(
    {
        VesselCategoryResolutionReason.NO_EVIDENCE,
        VesselCategoryResolutionReason.BOTH_UNKNOWN,
    }
)
_CONFLICT_REASONS = frozenset(
    {
        VesselCategoryResolutionReason.DESIGN_CONCRETE_DISAGREEMENT,
        VesselCategoryResolutionReason.CROSS_ORGANIZATION_DISAGREEMENT,
    }
)


@dataclass(frozen=True)
class VesselCategoryResolutionResult:
    """Deterministic, inspectable result of one `resolve_vessel_category` call.

    Amendment review Finding C: retains the full typed evidence bundle
    (never collapsed to bare values) so a caller/inspector can see exactly
    *which record*, asserted by whom and when, produced `resolution` --
    without reading raw SQL. `design_evidence` is the design plane's current
    assertion record (`None` when the design plane has never recorded one at
    all). `concrete_evidence` is every claiming Organization's current
    observation (one entry per Organization that has ever recorded *any*
    current claim snapshot for this PhysicalBoat, `claim=None` when that
    snapshot omits `vessel_category`). `design_value`/`concrete_values`
    remain available as derived read-only views for callers that only need
    the bare resolved values.
    """

    resolution: VesselCategoryResolution
    reason: VesselCategoryResolutionReason
    design_evidence: DesignVesselCategoryEvidence | None
    concrete_evidence: tuple[ConcreteVesselCategoryEvidence, ...]

    def __post_init__(self) -> None:
        _require_kind(
            self.resolution, VesselCategoryResolution, "VesselCategoryResolutionResult.resolution"
        )
        _require_kind(
            self.reason, VesselCategoryResolutionReason, "VesselCategoryResolutionResult.reason"
        )
        if self.design_evidence is not None:
            _require_kind(
                self.design_evidence,
                DesignVesselCategoryEvidence,
                "VesselCategoryResolutionResult.design_evidence",
            )
        if not isinstance(self.concrete_evidence, tuple):
            raise TypeError(
                "VesselCategoryResolutionResult.concrete_evidence must be a tuple, got "
                f"{type(self.concrete_evidence).__name__}"
            )
        for entry in self.concrete_evidence:
            _require_kind(
                entry,
                ConcreteVesselCategoryEvidence,
                "VesselCategoryResolutionResult.concrete_evidence item",
            )
        if self.reason in _POSITIVE_REASONS:
            if self.resolution is VesselCategoryResolution.CONFLICT or self.resolution is (
                VesselCategoryResolution.UNKNOWN
            ):
                raise ValueError(
                    f"reason {self.reason.value!r} requires a positive resolution, "
                    f"got {self.resolution.value!r}"
                )
        elif self.reason in _UNKNOWN_REASONS:
            if self.resolution is not VesselCategoryResolution.UNKNOWN:
                raise ValueError(
                    f"reason {self.reason.value!r} requires resolution UNKNOWN, "
                    f"got {self.resolution.value!r}"
                )
        elif (
            self.reason in _CONFLICT_REASONS
            and self.resolution is not VesselCategoryResolution.CONFLICT
        ):
            raise ValueError(
                f"reason {self.reason.value!r} requires resolution CONFLICT, "
                f"got {self.resolution.value!r}"
            )

    @property
    def design_value(self) -> VesselCategory | None:
        """The design plane's positive value, or `None` when the design
        plane is unresolved/`UNKNOWN`. Derived from `design_evidence`."""
        if self.design_evidence is None:
            return None
        assertion = self.design_evidence.assertion
        if assertion.assertion_kind is AssertionKind.VALUE_ASSERTION:
            return assertion.value
        return None

    @property
    def concrete_values(self) -> frozenset[VesselCategory]:
        """Every distinct positive value currently asserted by *any*
        claiming Organization (empty when none; exactly one element on
        agreement; two or more only under `CROSS_ORGANIZATION_DISAGREEMENT`).
        Derived from `concrete_evidence`."""
        return frozenset(
            entry.claim.value
            for entry in self.concrete_evidence
            if entry.claim is not None
            and entry.claim.assertion_kind is AssertionKind.VALUE_ASSERTION
        )

    @property
    def is_explicitly_non_sail_or_conflicted(self) -> bool:
        """True iff this PhysicalBoat is explicitly `POWER`/`MOTORSAILER`/
        `CONFLICT` -- the exact fail-closed exclusion condition SLICE-0091 §C
        requires for the existing Sail-only technical Search funnel.
        `UNKNOWN` (including every legacy null-category row) is deliberately
        excluded from this predicate: it must never be treated as a Sail
        exclusion, or legacy Sail-eligible inventory would silently
        disappear from the existing nine-criterion matches."""
        return self.resolution in (
            VesselCategoryResolution.POWER,
            VesselCategoryResolution.MOTORSAILER,
            VesselCategoryResolution.CONFLICT,
        )


@dataclass(frozen=True)
class VesselCategoryExclusionEvidence:
    """Bounded, cross-Organization-identity-free record of why a candidate
    was excluded from the existing Sail-only technical Search funnel by the
    SLICE-0091 §C category pre-filter -- amendment review Finding I.

    Before this type existed, `hullq.application.native_inventory_query`/
    `hullq.application.broker_search_fit` discarded `category_resolution`
    entirely once `is_explicitly_non_sail_or_conflicted` was `True`: a
    `CONFIRMED_NON_MATCH` produced by this pre-filter was mechanically
    indistinguishable from an ordinary nine-criterion technical mismatch,
    with zero retained evidence explaining why.

    Carries only the resolved `VesselCategoryResolution`/
    `VesselCategoryResolutionReason` enum members -- no Organization id, no
    Account id, no claim/assertion identity or raw source value. This is
    deliberately a strict subset of `VesselCategoryResolutionResult`, whose
    own `concrete_evidence` can name a *different* claiming Organization
    under `CROSS_ORGANIZATION_DISAGREEMENT` and must never be serialized
    that broadly (see its docstring). An enum-only pair is safe to retain on
    any `NativeInventoryCandidateEvaluation`/`SearchFitView`, including a
    future more-public-facing surface, without that risk.
    """

    resolution: VesselCategoryResolution
    reason: VesselCategoryResolutionReason

    def __post_init__(self) -> None:
        _require_kind(
            self.resolution, VesselCategoryResolution, "VesselCategoryExclusionEvidence.resolution"
        )
        _require_kind(
            self.reason, VesselCategoryResolutionReason, "VesselCategoryExclusionEvidence.reason"
        )
        if self.resolution not in (
            VesselCategoryResolution.POWER,
            VesselCategoryResolution.MOTORSAILER,
            VesselCategoryResolution.CONFLICT,
        ):
            raise ValueError(
                "VesselCategoryExclusionEvidence.resolution must be an explicit non-Sail/"
                f"conflicted resolution (POWER/MOTORSAILER/CONFLICT), got {self.resolution.value!r}"
            )


def _extract_positive_values(
    concrete_evidence: tuple[ConcreteVesselCategoryEvidence, ...],
) -> frozenset[VesselCategory]:
    values: set[VesselCategory] = set()
    for entry in concrete_evidence:
        if not isinstance(entry, ConcreteVesselCategoryEvidence):
            raise TypeError(
                "concrete_evidence items must each be a ConcreteVesselCategoryEvidence, got "
                f"{type(entry).__name__}"
            )
        claim = entry.claim
        if claim is None:
            continue
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert claim.value is not None
            values.add(claim.value)
    return frozenset(values)


def resolve_vessel_category(
    *,
    design_evidence: DesignVesselCategoryEvidence | None,
    concrete_evidence: tuple[ConcreteVesselCategoryEvidence, ...],
) -> VesselCategoryResolutionResult:
    """Deterministically resolve one PhysicalBoat's current `VesselCategory`.

    *design_evidence* is the current design-plane assertion record (`None`
    when the PhysicalBoat is design-unresolved or the design plane has never
    recorded one at all -- mechanically identical treatment to an explicit
    `UNKNOWN` assertion for the purpose of this resolution, since neither
    carries a positive value). *concrete_evidence* is every claiming
    Organization's current `vessel_category` observation for this
    PhysicalBoat (an entry's `claim` is `None` when that Organization's
    current claim omits the field entirely -- mechanically identical to an
    explicit `UNKNOWN` claim here, for the same reason; an Organization with
    no current claim at all simply has no entry).

    Amendment review Finding C: the full typed evidence (design assertion
    id/issuer/recorded time; concrete Organization id/revision id/recorded-
    by/recorded time) is retained verbatim in the returned result rather
    than collapsed to bare values -- this function's own combinatorial logic
    below still only *reads* each entry's `assertion`/`claim`, never
    inventing or discarding evidence.

    Precedence (SLICE-0091 §B, in the exact order applied):

    1. Two or more claiming Organizations currently assert different
       positive values -> `CONFLICT` / `CROSS_ORGANIZATION_DISAGREEMENT`
       (the concrete plane is already internally contradictory; the design
       plane is not even consulted).
    2. Neither plane carries a positive value -> `UNKNOWN` /
       `NO_EVIDENCE` (truly no assertion anywhere) or `BOTH_UNKNOWN` (at
       least one explicit `UNKNOWN` assertion exists).
    3. Exactly one plane carries a positive value -> that value /
       `DESIGN_ONLY` or `CONCRETE_ONLY`.
    4. Both planes carry a positive value and agree -> that value /
       `SOURCES_AGREE`.
    5. Both planes carry a positive value and disagree -> `CONFLICT` /
       `DESIGN_CONCRETE_DISAGREEMENT` -- never a best-effort pick of either
       source, and never silently overwritten.

    Never infers a value from anything other than the already-typed,
    already-sourced assertions passed in -- no display-name/hull-shape/
    rig-text/engine-count/model-name/keel/marketing-label heuristic.
    """
    if design_evidence is not None and not isinstance(
        design_evidence, DesignVesselCategoryEvidence
    ):
        raise TypeError(
            "design_evidence must be a DesignVesselCategoryEvidence or None, got "
            f"{type(design_evidence).__name__}"
        )
    if not isinstance(concrete_evidence, tuple):
        raise TypeError(
            f"concrete_evidence must be a tuple, got {type(concrete_evidence).__name__}"
        )

    design_assertion = design_evidence.assertion if design_evidence is not None else None
    design_value: VesselCategory | None = None
    if (
        design_assertion is not None
        and design_assertion.assertion_kind is AssertionKind.VALUE_ASSERTION
    ):
        design_value = design_assertion.value

    concrete_values = _extract_positive_values(concrete_evidence)

    if len(concrete_values) > 1:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution.CONFLICT,
            reason=VesselCategoryResolutionReason.CROSS_ORGANIZATION_DISAGREEMENT,
            design_evidence=design_evidence,
            concrete_evidence=concrete_evidence,
        )

    concrete_value = next(iter(concrete_values), None)

    if design_value is None and concrete_value is None:
        has_any_evidence = design_evidence is not None or any(
            entry.claim is not None for entry in concrete_evidence
        )
        reason = (
            VesselCategoryResolutionReason.BOTH_UNKNOWN
            if has_any_evidence
            else VesselCategoryResolutionReason.NO_EVIDENCE
        )
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution.UNKNOWN,
            reason=reason,
            design_evidence=design_evidence,
            concrete_evidence=concrete_evidence,
        )

    if design_value is not None and concrete_value is None:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution(design_value.value),
            reason=VesselCategoryResolutionReason.DESIGN_ONLY,
            design_evidence=design_evidence,
            concrete_evidence=concrete_evidence,
        )

    if design_value is None and concrete_value is not None:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution(concrete_value.value),
            reason=VesselCategoryResolutionReason.CONCRETE_ONLY,
            design_evidence=design_evidence,
            concrete_evidence=concrete_evidence,
        )

    assert design_value is not None and concrete_value is not None
    if design_value == concrete_value:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution(design_value.value),
            reason=VesselCategoryResolutionReason.SOURCES_AGREE,
            design_evidence=design_evidence,
            concrete_evidence=concrete_evidence,
        )

    return VesselCategoryResolutionResult(
        resolution=VesselCategoryResolution.CONFLICT,
        reason=VesselCategoryResolutionReason.DESIGN_CONCRETE_DISAGREEMENT,
        design_evidence=design_evidence,
        concrete_evidence=concrete_evidence,
    )
