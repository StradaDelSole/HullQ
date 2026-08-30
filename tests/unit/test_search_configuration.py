"""Unit tests for hullq.search.configuration — SLICE-0035.

Covers:
- ConfigurationProjection fail-closed .get_numeric()/.get_categorical() and
  defensive copy of both mappings
- ConfigurationIdentity required fields and applied_option_ids de-dup
- DesignConfigurationSet: non-empty configurations, design_id consistency,
  unique configuration_id, option_constraints validation (requires/excludes)
- adversarial checklist Q6: an invalid/unresolved option dependency
  combination is rejected at construction, never silently ignored
"""

from __future__ import annotations

import pytest

from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    OptionConstraint,
    ResolvedConfiguration,
)
from hullq.search.types import ValueQualification
from hullq.search.values import QualifiedCategoricalValue, QualifiedNumericValue

# ---------------------------------------------------------------------------
# ConfigurationProjection
# ---------------------------------------------------------------------------


def test_projection_get_numeric_fails_closed_to_missing() -> None:
    projection = ConfigurationProjection()
    result = projection.get_numeric("draft_max_m")
    assert result.qualification is ValueQualification.MISSING
    assert result.value is None


def test_projection_get_categorical_fails_closed_to_missing() -> None:
    projection = ConfigurationProjection()
    result = projection.get_categorical("rig.sailplan")
    assert result.qualification is ValueQualification.MISSING
    assert result.value is None


def test_projection_get_numeric_returns_stored_value() -> None:
    qv = QualifiedNumericValue(value=1.6, qualification=ValueQualification.CONFIRMED)
    projection = ConfigurationProjection(numeric_values={"draft_max_m": qv})
    assert projection.get_numeric("draft_max_m") is qv


def test_projection_get_categorical_returns_stored_value() -> None:
    qv = QualifiedCategoricalValue(value="fin", qualification=ValueQualification.CONFIRMED)
    projection = ConfigurationProjection(categorical_values={"appendages.keel_type": qv})
    assert projection.get_categorical("appendages.keel_type") is qv


def test_projection_mappings_are_copied_defensively() -> None:
    numeric_source: dict[str, QualifiedNumericValue] = {}
    categorical_source: dict[str, QualifiedCategoricalValue] = {}
    projection = ConfigurationProjection(
        numeric_values=numeric_source, categorical_values=categorical_source
    )
    numeric_source["draft_max_m"] = QualifiedNumericValue(
        value=1.5, qualification=ValueQualification.CONFIRMED
    )
    categorical_source["rig.sailplan"] = QualifiedCategoricalValue(
        value="cutter", qualification=ValueQualification.CONFIRMED
    )
    assert projection.get_numeric("draft_max_m").qualification is ValueQualification.MISSING
    assert projection.get_categorical("rig.sailplan").qualification is ValueQualification.MISSING


# ---------------------------------------------------------------------------
# ConfigurationIdentity
# ---------------------------------------------------------------------------


def test_identity_requires_configuration_id() -> None:
    with pytest.raises(ValueError, match="configuration_id"):
        ConfigurationIdentity(configuration_id="", boat_design_id="design-1")


def test_identity_requires_boat_design_id() -> None:
    with pytest.raises(ValueError, match="boat_design_id"):
        ConfigurationIdentity(configuration_id="cfg-1", boat_design_id="")


def test_identity_rejects_duplicate_applied_option_ids() -> None:
    with pytest.raises(ValueError, match="duplicates"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids=("OPT-A", "OPT-A"),
        )


def test_identity_defaults() -> None:
    identity = ConfigurationIdentity(configuration_id="cfg-1", boat_design_id="design-1")
    assert identity.named_variant_id is None
    assert identity.applied_option_ids == ()


# ---------------------------------------------------------------------------
# DesignConfigurationSet
# ---------------------------------------------------------------------------


def _baseline_configuration(design_id: str = "design-1") -> ResolvedConfiguration:
    return ResolvedConfiguration(
        identity=ConfigurationIdentity(configuration_id="cfg-baseline", boat_design_id=design_id),
        projection=ConfigurationProjection(),
    )


def test_design_configuration_set_requires_design_id() -> None:
    # A valid per-configuration boat_design_id is used so the empty
    # top-level design_id check itself is what is being exercised, rather
    # than tripping ConfigurationIdentity's own boat_design_id validation.
    with pytest.raises(ValueError, match="design_id must be non-empty"):
        DesignConfigurationSet(
            design_id="",
            configurations=(_baseline_configuration(design_id="design-1"),),
            configuration_space_complete=True,
        )


def test_design_configuration_set_requires_non_empty_configurations() -> None:
    with pytest.raises(ValueError, match="configurations must be non-empty"):
        DesignConfigurationSet(
            design_id="design-1", configurations=(), configuration_space_complete=True
        )


def test_design_configuration_set_rejects_mismatched_design_id() -> None:
    with pytest.raises(ValueError, match="boat_design_id"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_baseline_configuration(design_id="design-OTHER"),),
            configuration_space_complete=True,
        )


def test_design_configuration_set_rejects_duplicate_configuration_id() -> None:
    dup = ResolvedConfiguration(
        identity=ConfigurationIdentity(configuration_id="cfg-baseline", boat_design_id="design-1"),
        projection=ConfigurationProjection(),
    )
    with pytest.raises(ValueError, match="Duplicate configuration_id"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_baseline_configuration(), dup),
            configuration_space_complete=True,
        )


def test_design_configuration_set_accepts_valid_input() -> None:
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_baseline_configuration(),),
        configuration_space_complete=True,
    )
    assert config_set.configurations[0].identity.configuration_id == "cfg-baseline"
    assert config_set.is_fixture is False


# ---------------------------------------------------------------------------
# OptionConstraint validation — adversarial checklist Q6
# ---------------------------------------------------------------------------


def test_option_constraint_requires_option_id() -> None:
    with pytest.raises(ValueError, match="option_id"):
        OptionConstraint(option_id="")


def test_option_constraint_rejects_overlapping_requires_and_excludes() -> None:
    with pytest.raises(ValueError, match="cannot both require and exclude"):
        OptionConstraint(
            option_id="OPT-SHALLOW-DRAFT",
            requires_option_ids=frozenset({"OPT-X"}),
            excludes_option_ids=frozenset({"OPT-X"}),
        )


def _configuration_with_options(*option_ids: str) -> ResolvedConfiguration:
    return ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id="cfg-with-options",
            boat_design_id="design-1",
            applied_option_ids=option_ids,
        ),
        projection=ConfigurationProjection(),
    )


def test_configuration_missing_required_companion_option_is_rejected() -> None:
    # OPT-B requires OPT-A, but this configuration applies OPT-B alone.
    constraints = {
        "OPT-B": OptionConstraint(option_id="OPT-B", requires_option_ids=frozenset({"OPT-A"}))
    }
    with pytest.raises(ValueError, match="without its required companion option"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_options("OPT-B"),),
            configuration_space_complete=True,
            option_constraints=constraints,
        )


def test_configuration_with_required_companion_option_is_accepted() -> None:
    constraints = {
        "OPT-B": OptionConstraint(option_id="OPT-B", requires_option_ids=frozenset({"OPT-A"}))
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_options("OPT-A", "OPT-B"),),
        configuration_space_complete=True,
        option_constraints=constraints,
    )
    assert config_set.configurations[0].identity.applied_option_ids == ("OPT-A", "OPT-B")


def test_configuration_with_excluded_option_combination_is_rejected() -> None:
    # OPT-SHALLOW excludes OPT-DEEP; a configuration combining both is invalid.
    constraints = {
        "OPT-SHALLOW": OptionConstraint(
            option_id="OPT-SHALLOW", excludes_option_ids=frozenset({"OPT-DEEP"})
        )
    }
    with pytest.raises(ValueError, match="alongside excluded option"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_options("OPT-SHALLOW", "OPT-DEEP"),),
            configuration_space_complete=True,
            option_constraints=constraints,
        )


def test_configuration_referencing_unconstrained_option_is_unaffected() -> None:
    # An option id with no entry in option_constraints is not validated —
    # only explicitly supplied constraints are enforced (never invented).
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_options("OPT-UNCONSTRAINED"),),
        configuration_space_complete=True,
    )
    assert config_set.configurations[0].identity.applied_option_ids == ("OPT-UNCONSTRAINED",)
