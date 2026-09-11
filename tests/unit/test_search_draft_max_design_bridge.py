"""Unit tests for hullq.search.draft_max_design_bridge — SLICE-0051.

Covers the BOAT_DESIGN_SCHEMA-shaped-dict adapter (baseline + named_variant
override projection of exactly `draft_max_m`, never a design_options
combination, never `configuration_space_complete=True`) and
`compatible_boat_design_ids`'s existential design-level eligibility check,
mirroring the SLICE-0038 lesson that a shallow-draft configuration does not
by itself confirm a concrete listed yacht (that remains
hullq.application.inventory_search's job, not this module's).
"""

from __future__ import annotations

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


def test_build_configuration_set_projects_baseline_draft_max() -> None:
    design = _design("BD-1", baseline_draft_max_m=1.3)
    config_set = build_boat_design_draft_configuration_set(design)
    assert config_set.design_id == "BD-1"
    assert config_set.configuration_space_complete is False
    assert len(config_set.configurations) == 1
    projection = config_set.configurations[0].projection
    qualified = projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == 1.3


def test_baseline_null_draft_is_missing_not_a_confirmed_zero() -> None:
    design = _design("BD-2", baseline_draft_max_m=None)
    config_set = build_boat_design_draft_configuration_set(design)
    qualified = config_set.configurations[0].projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


def test_named_variant_override_produces_its_own_configuration() -> None:
    design = _design(
        "BD-3",
        baseline_draft_max_m=1.85,
        named_variants=[
            {
                "id": "shallow-keel",
                "overrides": {"dimensions": {"draft_max_m": 1.30}},
            },
            {
                "id": "no-override-variant",
                "overrides": {"dimensions": {}},
            },
        ],
    )
    config_set = build_boat_design_draft_configuration_set(design)
    assert len(config_set.configurations) == 3  # baseline + 2 variants

    by_id = {c.identity.configuration_id: c for c in config_set.configurations}
    baseline_config = by_id["BD-3::baseline"]
    shallow_config = by_id["BD-3::shallow-keel"]
    inherited_config = by_id["BD-3::no-override-variant"]

    assert baseline_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD).value == 1.85
    assert shallow_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD).value == 1.30
    # No override key present at all -> inherits the baseline value.
    assert inherited_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD).value == 1.85
    assert shallow_config.identity.named_variant_id == "shallow-keel"


def test_variant_override_explicit_null_clears_to_missing() -> None:
    design = _design(
        "BD-4",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "operator-adjustable", "overrides": {"dimensions": {"draft_max_m": None}}}],
    )
    config_set = build_boat_design_draft_configuration_set(design)
    variant_config = next(
        c for c in config_set.configurations if c.identity.configuration_id == "BD-4::operator-adjustable"
    )
    qualified = variant_config.projection.get_numeric(DRAFT_MAX_PROJECTION_FIELD)
    assert qualified.qualification is ValueQualification.MISSING


def test_compatible_boat_design_ids_is_existential_per_design() -> None:
    shallow_compatible = _design(
        "BD-SHALLOW",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "shallow-keel", "overrides": {"dimensions": {"draft_max_m": 1.30}}}],
    )
    always_too_deep = _design("BD-DEEP", baseline_draft_max_m=2.10)
    unknown_draft = _design("BD-UNKNOWN", baseline_draft_max_m=None)

    compatible = compatible_boat_design_ids(
        1.60, [shallow_compatible, always_too_deep, unknown_draft]
    )
    assert compatible == frozenset({"BD-SHALLOW"})


def test_compatible_boat_design_ids_empty_input_is_empty_output() -> None:
    assert compatible_boat_design_ids(1.6, []) == frozenset()
