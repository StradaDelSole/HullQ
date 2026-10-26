"""Domain unit tests for SLICE-0091 vessel category resolution.

Proves the deterministic precedence matrix of
`hullq.domain.vessel_category.resolve_vessel_category` without any
database: every named case from the SLICE-0091 contract §B (no-design,
either-source UNKNOWN, same-source agreement, design-vs-concrete conflict,
competing current publisher/supported claims, retraction) plus the
fail-closed `VesselCategoryResolutionResult.is_explicitly_non_sail_or_
conflicted` predicate the Search exclusion gate relies on.
"""

from __future__ import annotations

import pytest

from hullq.domain.physical_boat_claims import AssertionKind, VesselCategory, VesselCategoryClaim
from hullq.domain.vessel_category import (
    DesignVesselCategoryAssertion,
    VesselCategoryResolution,
    VesselCategoryResolutionReason,
    resolve_vessel_category,
)

VA = AssertionKind.VALUE_ASSERTION
UNK = AssertionKind.UNKNOWN


def _design(value: VesselCategory | None = None) -> DesignVesselCategoryAssertion:
    if value is None:
        return DesignVesselCategoryAssertion(assertion_kind=UNK, value=None)
    return DesignVesselCategoryAssertion(assertion_kind=VA, value=value)


def _claim(value: VesselCategory | None = None) -> VesselCategoryClaim:
    if value is None:
        return VesselCategoryClaim(assertion_kind=UNK, value=None)
    return VesselCategoryClaim(assertion_kind=VA, value=value)


# ---------------------------------------------------------------------------
# No evidence at all / legacy null category -- never silently SAIL
# ---------------------------------------------------------------------------


def test_no_design_and_no_concrete_evidence_resolves_unknown_no_evidence() -> None:
    result = resolve_vessel_category(design_assertion=None, concrete_claims_by_organization={})
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.reason is VesselCategoryResolutionReason.NO_EVIDENCE
    assert result.is_explicitly_non_sail_or_conflicted is False


def test_legacy_null_category_never_falls_under_the_exclusion_predicate() -> None:
    """A pre-0091 row (no design assertion, no concrete claim recorded by
    any Organization) must behave identically to UNKNOWN -- never excluded
    from the existing Sail funnel (SLICE-0091 §C)."""
    result = resolve_vessel_category(
        design_assertion=None, concrete_claims_by_organization={"ORG-A": None}
    )
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.is_explicitly_non_sail_or_conflicted is False


# ---------------------------------------------------------------------------
# Either-source explicit UNKNOWN
# ---------------------------------------------------------------------------


def test_both_sources_explicitly_unknown_resolves_unknown_both_unknown() -> None:
    result = resolve_vessel_category(
        design_assertion=_design(None), concrete_claims_by_organization={"ORG-A": _claim(None)}
    )
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.reason is VesselCategoryResolutionReason.BOTH_UNKNOWN


def test_design_unknown_concrete_omitted_resolves_unknown_both_unknown() -> None:
    result = resolve_vessel_category(design_assertion=_design(None), concrete_claims_by_organization={})
    assert result.resolution is VesselCategoryResolution.UNKNOWN
    assert result.reason is VesselCategoryResolutionReason.BOTH_UNKNOWN


# ---------------------------------------------------------------------------
# Exactly one plane positive
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("category", list(VesselCategory))
def test_design_only_positive_resolves_to_design_value(category: VesselCategory) -> None:
    result = resolve_vessel_category(
        design_assertion=_design(category), concrete_claims_by_organization={}
    )
    assert result.resolution.value == category.value
    assert result.reason is VesselCategoryResolutionReason.DESIGN_ONLY
    assert result.design_value is category
    assert result.concrete_values == frozenset()


@pytest.mark.parametrize("category", list(VesselCategory))
def test_concrete_only_positive_resolves_to_concrete_value(category: VesselCategory) -> None:
    result = resolve_vessel_category(
        design_assertion=None, concrete_claims_by_organization={"ORG-A": _claim(category)}
    )
    assert result.resolution.value == category.value
    assert result.reason is VesselCategoryResolutionReason.CONCRETE_ONLY
    assert result.concrete_values == frozenset({category})


def test_design_unknown_concrete_positive_resolves_concrete_only() -> None:
    result = resolve_vessel_category(
        design_assertion=_design(None),
        concrete_claims_by_organization={"ORG-A": _claim(VesselCategory.MOTORSAILER)},
    )
    assert result.resolution is VesselCategoryResolution.MOTORSAILER
    assert result.reason is VesselCategoryResolutionReason.CONCRETE_ONLY


# ---------------------------------------------------------------------------
# Same-source agreement
# ---------------------------------------------------------------------------


def test_design_and_concrete_agree_resolves_to_shared_value() -> None:
    result = resolve_vessel_category(
        design_assertion=_design(VesselCategory.SAIL),
        concrete_claims_by_organization={
            "ORG-A": _claim(VesselCategory.SAIL),
            "ORG-B": _claim(VesselCategory.SAIL),
        },
    )
    assert result.resolution is VesselCategoryResolution.SAIL
    assert result.reason is VesselCategoryResolutionReason.SOURCES_AGREE
    assert result.is_explicitly_non_sail_or_conflicted is False


# ---------------------------------------------------------------------------
# Design-vs-concrete conflict -- never a best-effort pick
# ---------------------------------------------------------------------------


def test_design_sail_concrete_power_resolves_conflict_never_a_guess() -> None:
    result = resolve_vessel_category(
        design_assertion=_design(VesselCategory.SAIL),
        concrete_claims_by_organization={"ORG-A": _claim(VesselCategory.POWER)},
    )
    assert result.resolution is VesselCategoryResolution.CONFLICT
    assert result.reason is VesselCategoryResolutionReason.DESIGN_CONCRETE_DISAGREEMENT
    assert result.design_value is VesselCategory.SAIL
    assert result.concrete_values == frozenset({VesselCategory.POWER})
    assert result.is_explicitly_non_sail_or_conflicted is True


# ---------------------------------------------------------------------------
# Competing current publisher/supported claims (cross-Organization)
# ---------------------------------------------------------------------------


def test_two_organizations_disagree_resolves_conflict_regardless_of_design() -> None:
    """Cross-Organization disagreement is CONFLICT even when the design
    plane agrees with one of the two competing claims -- the concrete plane
    is already internally contradictory and is never tie-broken by the
    design plane."""
    result = resolve_vessel_category(
        design_assertion=_design(VesselCategory.SAIL),
        concrete_claims_by_organization={
            "ORG-A": _claim(VesselCategory.SAIL),
            "ORG-B": _claim(VesselCategory.POWER),
        },
    )
    assert result.resolution is VesselCategoryResolution.CONFLICT
    assert result.reason is VesselCategoryResolutionReason.CROSS_ORGANIZATION_DISAGREEMENT
    assert result.concrete_values == frozenset({VesselCategory.SAIL, VesselCategory.POWER})
    assert result.is_explicitly_non_sail_or_conflicted is True


# ---------------------------------------------------------------------------
# Retraction -- modeled as the caller feeding a later, different current
# assertion; the pure resolver has no history of its own to retract.
# ---------------------------------------------------------------------------


def test_retraction_to_unknown_is_observed_as_an_ordinary_unknown_input() -> None:
    before = resolve_vessel_category(
        design_assertion=None,
        concrete_claims_by_organization={"ORG-A": _claim(VesselCategory.SAIL)},
    )
    assert before.resolution is VesselCategoryResolution.SAIL

    after = resolve_vessel_category(
        design_assertion=None, concrete_claims_by_organization={"ORG-A": _claim(None)}
    )
    assert after.resolution is VesselCategoryResolution.UNKNOWN
    assert after.reason is VesselCategoryResolutionReason.BOTH_UNKNOWN


# ---------------------------------------------------------------------------
# Type safety at the boundary
# ---------------------------------------------------------------------------


def test_rejects_non_claim_values_in_concrete_mapping() -> None:
    with pytest.raises(TypeError):
        resolve_vessel_category(
            design_assertion=None, concrete_claims_by_organization={"ORG-A": "SAIL"}  # type: ignore[dict-item]
        )


def test_rejects_wrong_type_for_design_assertion() -> None:
    with pytest.raises(TypeError):
        resolve_vessel_category(
            design_assertion="SAIL",  # type: ignore[arg-type]
            concrete_claims_by_organization={},
        )


def test_design_assertion_rejects_conflict_as_input_value() -> None:
    """CONFLICT is a resolution outcome only -- it is structurally
    impossible to construct a DesignVesselCategoryAssertion carrying it,
    since VesselCategory itself has no CONFLICT member."""
    with pytest.raises((TypeError, ValueError)):
        DesignVesselCategoryAssertion(assertion_kind=VA, value="CONFLICT")  # type: ignore[arg-type]
