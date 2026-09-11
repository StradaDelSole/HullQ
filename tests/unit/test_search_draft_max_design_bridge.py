"""Unit tests for hullq.search.draft_max_design_bridge — SLICE-0051 (+ amendment review).

Covers the BOAT_DESIGN_SCHEMA-shaped-dict adapter's structural behavior
(baseline + named_variant projection shape, never a `design_options`
combination, never `configuration_space_complete=True`) and
`compatible_boat_design_ids`'s existential design-level eligibility check.

Post-amendment-review (Finding 3): `_qualify_draft_max` always returns
`MISSING` regardless of the raw persisted value, because no accepted
production per-field qualification/resolution source exists for
`canonical_boat_designs` (see the module's own docstring for the full
reconciliation against `SEARCH_QUERY_SEMANTICS.v0.1.md` §3 and
`PROVENANCE_AND_QUALITY.md`). Every test below reflects that fail-closed
reality rather than the pre-amendment (incorrect) CONFIRMED-from-raw-JSON
behavior. Finding 4 coverage: a NamedVariant with an unresolved
`requires_option_ids` dependency is excluded from the configuration set
entirely.
"""

from __future__ import annotations

from decimal import Decimal

import pytest

from hullq.search.draft_max_design_bridge import (
    DRAFT_MAX_PROJECTION_FIELD,
    build_boat_design_draft_configuration_set,
    compatible_boat_design_ids,
)
from hullq.search.types import ValueQualification


def _design(
    design_id: str,
    *,
    baseline_draft_max_m: float | None,
    named_variants: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": design_id,
        "baseline": {"dimensions": {"draft_max_m": baseline_draft_max_m}},
        "named_variants": named_variants or [],
    }


# ---------------------------------------------------------------------------
# Finding 3: raw persisted BoatDesign JSON never self-authorizes CONFIRMED
# ---------------------------------------------------------------------------


def test_baseline_present_positive_value_is_still_missing_not_confirmed() -> None:
    """A present, well-formed, positive baseline draft_max_m value MUST NOT
    become CONFIRMED merely because it exists in persisted JSON -- no
    accepted per-field qualification/resolution source exists to authorize
    that (Finding 3)."""
    design = _design("BD-1", baseline_draft_max_m=1.3)
    config_set = build_boat_design_draft_configuration_set(design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


def test_baseline_null_draft_is_also_missing() -> None:
    design = _design("BD-2", baseline_draft_max_m=None)
    config_set = build_boat_design_draft_configuration_set(design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


def test_named_variant_override_is_also_missing_regardless_of_raw_value() -> None:
    design = _design(
        "BD-3",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "shallow-keel", "overrides": {"dimensions": {"draft_max_m": 1.30}}}],
    )
    config_set = build_boat_design_draft_configuration_set(design)
    by_id = {c.identity.configuration_id: c for c in config_set.configurations}
    for config in by_id.values():
        qualified = config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
        assert qualified.qualification is ValueQualification.MISSING


def test_compatible_boat_design_ids_is_always_empty_against_real_persisted_shape() -> None:
    """Even an objectively shallow-draft-compatible design (baseline too
    deep, but a NamedVariant override well within the requirement) must
    never become design-level CONFIRMED_MATCH from raw persisted JSON alone
    -- this is the direct, exact behavior Finding 3 requires until an
    accepted production qualification source exists."""
    obviously_shallow_looking = _design(
        "BD-SHALLOW",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "shallow-keel", "overrides": {"dimensions": {"draft_max_m": 1.30}}}],
    )
    compatible = compatible_boat_design_ids(Decimal("1.6"), [obviously_shallow_looking])
    assert compatible == frozenset()


# ---------------------------------------------------------------------------
# Finding 4: unresolved NamedVariant option dependency
# ---------------------------------------------------------------------------


def test_variant_with_requires_option_ids_is_excluded_entirely() -> None:
    """A variant this adapter cannot validly resolve (it never applies any
    DesignOption) must not appear in the configuration set at all -- not as
    a phantom resolved configuration, confirmed or otherwise."""
    design = _design(
        "BD-4",
        baseline_draft_max_m=1.85,
        named_variants=[
            {
                "id": "shallow-keel-needs-option",
                "overrides": {"dimensions": {"draft_max_m": 1.30}},
                "requires_option_ids": ["OPT-PERFORMANCE-PACKAGE"],
            },
            {"id": "shallow-keel-standalone", "overrides": {"dimensions": {"draft_max_m": 1.30}}},
        ],
    )
    config_set = build_boat_design_draft_configuration_set(design)
    configuration_ids = {c.identity.configuration_id for c in config_set.configurations}
    assert "BD-4::shallow-keel-needs-option" not in configuration_ids
    assert "BD-4::shallow-keel-standalone" in configuration_ids
    assert "BD-4::baseline" in configuration_ids
    assert len(config_set.configurations) == 2


def test_variant_with_empty_requires_option_ids_is_not_excluded() -> None:
    design = _design(
        "BD-5",
        baseline_draft_max_m=1.85,
        named_variants=[
            {
                "id": "shallow-keel",
                "overrides": {"dimensions": {"draft_max_m": 1.30}},
                "requires_option_ids": [],
            }
        ],
    )
    config_set = build_boat_design_draft_configuration_set(design)
    configuration_ids = {c.identity.configuration_id for c in config_set.configurations}
    assert "BD-5::shallow-keel" in configuration_ids


def test_unresolved_variant_dependency_cannot_authorize_a_confirmed_design_match() -> None:
    """Even disregarding Finding 3 entirely, a variant whose required option
    is absent/unresolved must never be able to create a confirmed design
    match on its own -- proven here by excluding it from the configuration
    set regardless of what its own draft_max_m override would otherwise
    imply."""
    design_only_compatible_via_dependent_variant = _design(
        "BD-6",
        baseline_draft_max_m=2.5,  # always too deep on its own
        named_variants=[
            {
                "id": "only-shallow-option",
                "overrides": {"dimensions": {"draft_max_m": 1.0}},
                "requires_option_ids": ["OPT-SHALLOW-DRAFT-PACKAGE"],
            }
        ],
    )
    config_set = build_boat_design_draft_configuration_set(
        design_only_compatible_via_dependent_variant
    )
    # Only the (too-deep) baseline configuration remains.
    assert len(config_set.configurations) == 1
    assert config_set.configurations[0].identity.configuration_id == "BD-6::baseline"


# ---------------------------------------------------------------------------
# Structural adapter behavior (unaffected by Findings 3/4)
# ---------------------------------------------------------------------------


def test_configuration_space_is_never_claimed_complete() -> None:
    design = _design("BD-7", baseline_draft_max_m=1.3)
    config_set = build_boat_design_draft_configuration_set(design)
    assert config_set.configuration_space_complete is False


def test_named_variant_inherits_baseline_when_override_key_absent() -> None:
    design = _design(
        "BD-8",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "no-override-variant", "overrides": {"dimensions": {}}}],
    )
    config_set = build_boat_design_draft_configuration_set(design)
    assert len(config_set.configurations) == 2  # baseline + inherited variant


# ---------------------------------------------------------------------------
# Finding 2: exact-Decimal threshold, never coerced to float
# ---------------------------------------------------------------------------


def test_compatible_boat_design_ids_requires_a_decimal_threshold() -> None:
    design = _design("BD-9", baseline_draft_max_m=1.3)
    with pytest.raises(TypeError):
        compatible_boat_design_ids(1.6, [design])  # type: ignore[arg-type]


def test_compatible_boat_design_ids_accepts_extreme_precision_decimal_without_error() -> None:
    """An arbitrary-precision Decimal threshold must not raise/overflow even
    though (per Finding 3) it can never produce a confirmed match today."""
    design = _design("BD-10", baseline_draft_max_m=1.3)
    result = compatible_boat_design_ids(Decimal("1.10000000000000000000000000000001"), [design])
    assert result == frozenset()


def test_compatible_boat_design_ids_empty_input_is_empty_output() -> None:
    assert compatible_boat_design_ids(Decimal("1.6"), []) == frozenset()
