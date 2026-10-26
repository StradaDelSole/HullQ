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

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

from hullq.domain.physical_boat_claims import AssertionKind, VesselCategory, VesselCategoryClaim

__all__ = [
    "BoatDesignCategoryAssertionId",
    "DesignVesselCategoryAssertion",
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

    Every input retained verbatim (never collapsed away) so a caller/
    inspector can see exactly which evidence produced `resolution` without
    reading raw SQL: `design_value` is the design plane's positive value
    (`None` when the design plane is unresolved/`UNKNOWN`);
    `concrete_values` is the frozenset of every distinct positive value
    currently asserted by *any* claiming Organization (empty when none;
    exactly one element on agreement; two or more only under
    `CROSS_ORGANIZATION_DISAGREEMENT`).
    """

    resolution: VesselCategoryResolution
    reason: VesselCategoryResolutionReason
    design_value: VesselCategory | None
    concrete_values: frozenset[VesselCategory]

    def __post_init__(self) -> None:
        _require_kind(self.resolution, VesselCategoryResolution, "VesselCategoryResolutionResult.resolution")
        _require_kind(
            self.reason, VesselCategoryResolutionReason, "VesselCategoryResolutionResult.reason"
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
        elif self.reason in _CONFLICT_REASONS:
            if self.resolution is not VesselCategoryResolution.CONFLICT:
                raise ValueError(
                    f"reason {self.reason.value!r} requires resolution CONFLICT, "
                    f"got {self.resolution.value!r}"
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


def _extract_positive_values(
    concrete_claims_by_organization: Mapping[str, VesselCategoryClaim | None],
) -> frozenset[VesselCategory]:
    values: set[VesselCategory] = set()
    for claim in concrete_claims_by_organization.values():
        if claim is None:
            continue
        if not isinstance(claim, VesselCategoryClaim):
            raise TypeError(
                "concrete_claims_by_organization values must each be a "
                f"VesselCategoryClaim or None, got {type(claim).__name__}"
            )
        if claim.assertion_kind is AssertionKind.VALUE_ASSERTION:
            assert claim.value is not None
            values.add(claim.value)
    return frozenset(values)


def resolve_vessel_category(
    *,
    design_assertion: DesignVesselCategoryAssertion | None,
    concrete_claims_by_organization: Mapping[str, VesselCategoryClaim | None],
) -> VesselCategoryResolutionResult:
    """Deterministically resolve one PhysicalBoat's current `VesselCategory`.

    *design_assertion* is the current design-plane assertion (`None` when the
    PhysicalBoat is design-unresolved or the design plane has never recorded
    one at all -- mechanically identical treatment to an explicit `UNKNOWN`
    assertion for the purpose of this resolution, since neither carries a
    positive value). *concrete_claims_by_organization* is every claiming
    Organization's current `vessel_category` observation for this
    PhysicalBoat (`None` for an Organization with no current claim, or whose
    current claim omits the field entirely -- both mechanically identical to
    an explicit `UNKNOWN` claim here, for the same reason).

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
    if design_assertion is not None and not isinstance(
        design_assertion, DesignVesselCategoryAssertion
    ):
        raise TypeError(
            "design_assertion must be a DesignVesselCategoryAssertion or None, got "
            f"{type(design_assertion).__name__}"
        )

    design_value: VesselCategory | None = None
    if (
        design_assertion is not None
        and design_assertion.assertion_kind is AssertionKind.VALUE_ASSERTION
    ):
        design_value = design_assertion.value

    concrete_values = _extract_positive_values(concrete_claims_by_organization)

    if len(concrete_values) > 1:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution.CONFLICT,
            reason=VesselCategoryResolutionReason.CROSS_ORGANIZATION_DISAGREEMENT,
            design_value=design_value,
            concrete_values=concrete_values,
        )

    concrete_value = next(iter(concrete_values), None)

    if design_value is None and concrete_value is None:
        has_any_evidence = design_assertion is not None or any(
            claim is not None for claim in concrete_claims_by_organization.values()
        )
        reason = (
            VesselCategoryResolutionReason.BOTH_UNKNOWN
            if has_any_evidence
            else VesselCategoryResolutionReason.NO_EVIDENCE
        )
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution.UNKNOWN,
            reason=reason,
            design_value=design_value,
            concrete_values=concrete_values,
        )

    if design_value is not None and concrete_value is None:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution(design_value.value),
            reason=VesselCategoryResolutionReason.DESIGN_ONLY,
            design_value=design_value,
            concrete_values=concrete_values,
        )

    if design_value is None and concrete_value is not None:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution(concrete_value.value),
            reason=VesselCategoryResolutionReason.CONCRETE_ONLY,
            design_value=design_value,
            concrete_values=concrete_values,
        )

    assert design_value is not None and concrete_value is not None
    if design_value == concrete_value:
        return VesselCategoryResolutionResult(
            resolution=VesselCategoryResolution(design_value.value),
            reason=VesselCategoryResolutionReason.SOURCES_AGREE,
            design_value=design_value,
            concrete_values=concrete_values,
        )

    return VesselCategoryResolutionResult(
        resolution=VesselCategoryResolution.CONFLICT,
        reason=VesselCategoryResolutionReason.DESIGN_CONCRETE_DISAGREEMENT,
        design_value=design_value,
        concrete_values=concrete_values,
    )
