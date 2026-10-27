"""Domain unit tests for SLICE-0091 vessel category resolution.

Proves the deterministic precedence matrix of
`hullq.domain.vessel_category.resolve_vessel_category` without any
database: every named case from the SLICE-0091 contract §B (no-design,
either-source UNKNOWN, same-source agreement, design-vs-concrete conflict,
competing current publisher/supported claims, retraction) plus the
fail-closed `VesselCategoryResolutionResult.is_explicitly_non_sail_or_
conflicted` predicate the Search exclusion gate relies on.

Amendment review Finding C: also proves the full typed evidence bundle
(design assertion id/issuer/recorded time; concrete Organization id/
revision id/recorded-by/recorded time) is retained verbatim in the
resolution result, not collapsed to bare values.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from hullq.domain.physical_boat_claims import (
    AssertionKind,
    PhysicalBoatClaimRevisionId,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.provenance import ResolverKind, ResolverMetadata
from hullq.domain.publishing_eligibility import AccountId, MarketplaceOrganizationId
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    ConcreteVesselCategoryEvidence,
    DesignVesselCategoryAssertion,
    DesignVesselCategoryEvidence,
    VesselCategoryResolution,
    VesselCategoryResolutionReason,
    resolve_vessel_category,
)

VA = AssertionKind.VALUE_ASSERTION
UNK = AssertionKind.UNKNOWN
_AT = datetime(2026, 10, 27, 12, 0, 0, tzinfo=UTC)


def _design_assertion(value: VesselCategory | None = None) -> DesignVesselCategoryAssertion:
    if value is None:
        return DesignVesselCategoryAssertion(assertion_kind=UNK, value=None)
    return DesignVesselCategoryAssertion(assertion_kind=VA, value=value)


def _design_evidence(
    value: VesselCategory | None = None, *, assertion_id: str = "BDCAT-1"
) -> DesignVesselCategoryEvidence:
    return DesignVesselCategoryEvidence(
        assertion_id=BoatDesignCategoryAssertionId(assertion_id),
        boat_design_id="BD-1",
        assertion=_design_assertion(value),
        issuer=ResolverMetadata(
            kind=ResolverKind.DETERMINISTIC_TOOL,
            identifier="hullq-catalog-category-admission",
            version="1",
        ),
        recorded_at=_AT,
        previous_assertion_id=None,
    )


def _claim(value: VesselCategory | None = None) -> VesselCategoryClaim:
    if value is None:
        return VesselCategoryClaim(assertion_kind=UNK, value=None)
    return VesselCategoryClaim(assertion_kind=VA, value=value)


def _concrete_evidence(
    org_id: str, value: VesselCategory | None, *, omitted: bool = False
) -> ConcreteVesselCategoryEvidence:
    return ConcreteVesselCategoryEvidence(
        claiming_organization_id=MarketplaceOrganizationId(org_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{org_id}"),
        recorded_by_account_id=AccountId(f"ACC-{org_id}"),
        recorded_at=_AT,
        claim=None if omitted else _claim(value),
    )


# ---------------------------------------------------------------------------
# No evidence at all / legacy null category -- never silently SAIL
# ---------------------------------------------------------------------------


def test_no_design_and_no_concrete_evidence_resolves_unknown_no_evidence() -> None:
    result = resolve_vessel_category(design_evidence=None, concrete_evidence=())
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.reason is VesselCategoryResolutionReason.NO_EVIDENCE
    assert result.is_explicitly_non_sail_or_conflicted is False
    assert result.design_evidence is None
    assert result.concrete_evidence == ()
    assert result.design_value is None
    assert result.concrete_values == frozenset()


def test_legacy_null_category_never_falls_under_the_exclusion_predicate() -> None:
    """A pre-0091 row (no design assertion, a current claim that omits
    vessel_category entirely) must behave identically to UNKNOWN -- never
    excluded from the existing Sail funnel (SLICE-0091 §C)."""
    result = resolve_vessel_category(
        design_evidence=None, concrete_evidence=(_concrete_evidence("ORG-A", None, omitted=True),)
    )
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.is_explicitly_non_sail_or_conflicted is False


# ---------------------------------------------------------------------------
# Either-source explicit UNKNOWN
# ---------------------------------------------------------------------------


def test_both_sources_explicitly_unknown_resolves_unknown_both_unknown() -> None:
    result = resolve_vessel_category(
        design_evidence=_design_evidence(None),
        concrete_evidence=(_concrete_evidence("ORG-A", None),),
    )
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.reason is VesselCategoryResolutionReason.BOTH_UNKNOWN


def test_design_unknown_concrete_omitted_resolves_unknown_both_unknown() -> None:
    result = resolve_vessel_category(design_evidence=_design_evidence(None), concrete_evidence=())
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.reason is VesselCategoryResolutionReason.BOTH_UNKNOWN


# ---------------------------------------------------------------------------
# Exactly one plane positive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", list(VesselCategory))
def test_design_only_positive_resolves_to_design_value(category: VesselCategory) -> None:
    result = resolve_vessel_category(design_evidence=_design_evidence(category), concrete_evidence=())
    assert result.resolution.value == category.value
    assert result.reason is VesselCategoryResolutionReason.DESIGN_ONLY
    assert result.design_value is category
    assert result.concrete_values == frozenset()
    assert result.design_evidence is not None
    assert result.design_evidence.assertion.value is category


@pytest.mark.parametrize("category", list(VesselCategory))
def test_concrete_only_positive_resolves_to_concrete_value(category: VesselCategory) -> None:
    result = resolve_vessel_category(
        design_evidence=None, concrete_evidence=(_concrete_evidence("ORG-A", category),)
    )
    assert result.resolution.value == category.value
    assert result.reason is VesselCategoryResolutionReason.CONCRETE_ONLY
    assert result.concrete_values == frozenset({category})
    assert len(result.concrete_evidence) == 1
    assert result.concrete_evidence[0].claiming_organization_id == MarketplaceOrganizationId("ORG-A")


def test_design_unknown_concrete_positive_resolves_concrete_only() -> None:
    result = resolve_vessel_category(
        design_evidence=_design_evidence(None),
        concrete_evidence=(_concrete_evidence("ORG-A", VesselCategory.MOTORSAILER),),
    )
    assert result.resolution is VesselCategoryResolution.MOTORSAILER
    assert result.reason is VesselCategoryResolutionReason.CONCRETE_ONLY


# ---------------------------------------------------------------------------
# Same-source agreement
# ---------------------------------------------------------------------------


def test_design_and_concrete_agree_resolves_to_shared_value() -> None:
    result = resolve_vessel_category(
        design_evidence=_design_evidence(VesselCategory.SAIL),
        concrete_evidence=(
            _concrete_evidence("ORG-A", VesselCategory.SAIL),
            _concrete_evidence("ORG-B", VesselCategory.SAIL),
        ),
    )
    assert result.resolution is VesselCategoryResolution.SAIL
    assert result.reason is VesselCategoryResolutionReason.SOURCES_AGREE
    assert result.is_explicitly_non_sail_or_conflicted is False


# ---------------------------------------------------------------------------
# Design-vs-concrete conflict -- never a best-effort pick
# ---------------------------------------------------------------------------


def test_design_sail_concrete_power_resolves_conflict_never_a_guess() -> None:
    result = resolve_vessel_category(
        design_evidence=_design_evidence(VesselCategory.SAIL),
        concrete_evidence=(_concrete_evidence("ORG-A", VesselCategory.POWER),),
    )
    assert result.resolution is VesselCategoryResolution.CONFLICT
    assert result.reason is VesselCategoryResolutionReason.DESIGN_CONCRETE_DISAGREEMENT
    assert result.design_value is VesselCategory.SAIL
    assert result.concrete_values == frozenset({VesselCategory.POWER})
    assert result.is_explicitly_non_sail_or_conflicted is True
    # Finding C: evidence identity is recoverable from the result alone.
    assert result.design_evidence is not None
    assert result.design_evidence.assertion_id == BoatDesignCategoryAssertionId("BDCAT-1")
    assert result.concrete_evidence[0].claiming_organization_id == MarketplaceOrganizationId("ORG-A")
    assert result.concrete_evidence[0].revision_id == PhysicalBoatClaimRevisionId("PBCREV-ORG-A")


# ---------------------------------------------------------------------------
# Competing current publisher/supported claims (cross-Organization)
# ---------------------------------------------------------------------------


def test_two_organizations_disagree_resolves_conflict_regardless_of_design() -> None:
    """Cross-Organization disagreement is CONFLICT even when the design
    plane agrees with one of the two competing claims -- the concrete plane
    is already internally contradictory and is never tie-broken by the
    design plane."""
    result = resolve_vessel_category(
        design_evidence=_design_evidence(VesselCategory.SAIL),
        concrete_evidence=(
            _concrete_evidence("ORG-A", VesselCategory.SAIL),
            _concrete_evidence("ORG-B", VesselCategory.POWER),
        ),
    )
    assert result.resolution is VesselCategoryResolution.CONFLICT
    assert result.reason is VesselCategoryResolutionReason.CROSS_ORGANIZATION_DISAGREEMENT
    assert result.concrete_values == frozenset({VesselCategory.SAIL, VesselCategory.POWER})
    assert result.is_explicitly_non_sail_or_conflicted is True
    # Finding C: both disagreeing sources are individually identifiable.
    org_ids = {ev.claiming_organization_id.value for ev in result.concrete_evidence}
    assert org_ids == {"ORG-A", "ORG-B"}


# ---------------------------------------------------------------------------
# Retraction -- modeled as the caller feeding a later, different current
# assertion; the pure resolver has no history of its own to retract.
# ---------------------------------------------------------------------------


def test_retraction_to_unknown_is_observed_as_an_ordinary_unknown_input() -> None:
    before = resolve_vessel_category(
        design_evidence=None,
        concrete_evidence=(_concrete_evidence("ORG-A", VesselCategory.SAIL),),
    )
    assert before.resolution is VesselCategoryResolution.SAIL

    after = resolve_vessel_category(
        design_evidence=None, concrete_evidence=(_concrete_evidence("ORG-A", None),)
    )
    assert after.resolution is VesselCategoryResolution.UNKNOWN
    assert after.reason is VesselCategoryResolutionReason.BOTH_UNKNOWN


# ---------------------------------------------------------------------------
# Type safety at the boundary
# ---------------------------------------------------------------------------


def test_rejects_non_evidence_values_in_concrete_tuple() -> None:
    with pytest.raises(TypeError):
        resolve_vessel_category(
            design_evidence=None, concrete_evidence=("SAIL",)  # type: ignore[arg-type]
        )


def test_rejects_wrong_type_for_design_evidence() -> None:
    with pytest.raises(TypeError):
        resolve_vessel_category(
            design_evidence="SAIL",  # type: ignore[arg-type]
            concrete_evidence=(),
        )


def test_rejects_non_tuple_concrete_evidence() -> None:
    with pytest.raises(TypeError):
        resolve_vessel_category(
            design_evidence=None,
            concrete_evidence=[_concrete_evidence("ORG-A", VesselCategory.SAIL)],  # type: ignore[arg-type]
        )


def test_design_assertion_rejects_conflict_as_input_value() -> None:
    """CONFLICT is a resolution outcome only -- it is structurally
    impossible to construct a DesignVesselCategoryAssertion carrying it,
    since VesselCategory itself has no CONFLICT member."""
    with pytest.raises((TypeError, ValueError)):
        DesignVesselCategoryAssertion(assertion_kind=VA, value="CONFLICT")  # type: ignore[arg-type]
