"""Unit tests for hullq.search.configuration — SLICE-0035 (+ REVIEW amendment).

Covers:
- ConfigurationProjection fail-closed .get_numeric()/.get_categorical() and
  defensive copy of both mappings
- ConfigurationIdentity required fields and applied_option_ids de-dup
- DesignConfigurationSet: non-empty configurations, design_id consistency,
  unique configuration_id, option_constraints validation (requires/excludes)
- adversarial checklist Q6: an invalid/unresolved option dependency
  combination is rejected at construction, never silently ignored
- REVIEW amendment Finding 2: configuration_space_complete is a genuine bool
  (never coerced), configurations/requires/excludes are defensively
  materialized to immutable types before validation so a caller mutating its
  own source collection after construction cannot alter what was validated,
  and option_constraints/variant_constraints mapping keys must match the
  constraint's own id
- REVIEW amendment Finding 3: NamedVariantConstraint enforces
  requires/excludes for a ResolvedConfiguration's named_variant_id, mirroring
  OptionConstraint, never invented for an unconstrained variant
- REVIEW amendment second round, remaining blocker 2: no identifier
  collection (applied_option_ids, requires_option_ids, excludes_option_ids)
  can be bypassed by supplying a bare str/bytes (which would otherwise
  explode character-by-character), a non-string element, or duplicates that
  frozenset materialization would silently hide
- REVIEW amendment second round, remaining blocker 1: OptionConstraint/
  NamedVariantConstraint.applicability (reusing ValueQualification) — a
  CONFIRMED option/variant participates normally; NOT_APPLICABLE or any
  unresolved applicability rejects any configuration referencing it, and
  unresolved (non-NOT_APPLICABLE) applicability additionally rejects
  configuration_space_complete=True on the same set
"""

from __future__ import annotations

import pytest

from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    NamedVariantConstraint,
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


# ---------------------------------------------------------------------------
# REVIEW amendment Finding 2 — runtime-closed truth-authorizing controls
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_complete", [1, 0, "true", "false", None, 1.0])
def test_configuration_space_complete_rejects_non_bool(bad_complete: object) -> None:
    with pytest.raises(ValueError, match="configuration_space_complete must be an actual bool"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_baseline_configuration(),),
            configuration_space_complete=bad_complete,  # type: ignore[arg-type]
        )


@pytest.mark.parametrize("good_complete", [True, False])
def test_configuration_space_complete_accepts_genuine_bool(good_complete: bool) -> None:
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_baseline_configuration(),),
        configuration_space_complete=good_complete,
    )
    assert config_set.configuration_space_complete is good_complete


def test_mutating_source_configurations_list_after_construction_is_inert() -> None:
    source_list = [_baseline_configuration()]
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=source_list,
        configuration_space_complete=True,  # type: ignore[arg-type]
    )
    extra = _configuration_with_options()
    source_list.append(extra)
    assert len(config_set.configurations) == 1
    assert config_set.configurations[0].identity.configuration_id == "cfg-baseline"


def test_mutating_source_requires_set_after_constructing_option_constraint_is_inert() -> None:
    source_requires = {"OPT-A"}
    constraint = OptionConstraint(option_id="OPT-B", requires_option_ids=source_requires)
    source_requires.add("OPT-Z")
    assert constraint.requires_option_ids == frozenset({"OPT-A"})


def test_mutating_source_excludes_set_after_constructing_option_constraint_is_inert() -> None:
    source_excludes = {"OPT-DEEP"}
    constraint = OptionConstraint(option_id="OPT-SHALLOW", excludes_option_ids=source_excludes)
    source_excludes.add("OPT-OTHER")
    assert constraint.excludes_option_ids == frozenset({"OPT-DEEP"})


def test_mutation_after_option_constraint_construction_cannot_relax_validation() -> None:
    # If mutation leaked through, adding "OPT-A" to the excludes set after
    # construction could turn a currently-valid configuration invalid (or
    # vice versa) without re-validation ever running. It must not.
    source_excludes: set[str] = set()
    constraint = OptionConstraint(option_id="OPT-B", excludes_option_ids=source_excludes)
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_options("OPT-A", "OPT-B"),),
        configuration_space_complete=True,
        option_constraints={"OPT-B": constraint},
    )
    source_excludes.add("OPT-A")
    # Already-validated set is unaffected by the post-hoc mutation attempt.
    assert config_set.configurations[0].identity.applied_option_ids == ("OPT-A", "OPT-B")


def test_option_constraints_mapping_key_must_match_option_id() -> None:
    constraint = OptionConstraint(option_id="OPT-B")
    with pytest.raises(ValueError, match="does not match"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_options("OPT-B"),),
            configuration_space_complete=True,
            option_constraints={"OPT-WRONG-KEY": constraint},
        )


# ---------------------------------------------------------------------------
# REVIEW amendment Finding 3 — NamedVariant dependency/applicability
# ---------------------------------------------------------------------------


def test_named_variant_constraint_requires_variant_id() -> None:
    with pytest.raises(ValueError, match="variant_id"):
        NamedVariantConstraint(variant_id="")


def test_named_variant_constraint_rejects_overlapping_requires_and_excludes() -> None:
    with pytest.raises(ValueError, match="cannot both require and exclude"):
        NamedVariantConstraint(
            variant_id="VARIANT-CENTER-COCKPIT",
            requires_option_ids=frozenset({"OPT-X"}),
            excludes_option_ids=frozenset({"OPT-X"}),
        )


def _configuration_with_variant(variant_id: str | None, *option_ids: str) -> ResolvedConfiguration:
    return ResolvedConfiguration(
        identity=ConfigurationIdentity(
            configuration_id="cfg-with-variant",
            boat_design_id="design-1",
            named_variant_id=variant_id,
            applied_option_ids=option_ids,
        ),
        projection=ConfigurationProjection(),
    )


def test_variant_missing_required_companion_option_is_rejected() -> None:
    # VARIANT-CC requires OPT-WHEEL-STEERING, but this configuration doesn't apply it.
    constraints = {
        "VARIANT-CC": NamedVariantConstraint(
            variant_id="VARIANT-CC", requires_option_ids=frozenset({"OPT-WHEEL-STEERING"})
        )
    }
    with pytest.raises(ValueError, match="without its required companion option"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_variant("VARIANT-CC"),),
            configuration_space_complete=True,
            variant_constraints=constraints,
        )


def test_variant_with_required_companion_option_is_accepted() -> None:
    constraints = {
        "VARIANT-CC": NamedVariantConstraint(
            variant_id="VARIANT-CC", requires_option_ids=frozenset({"OPT-WHEEL-STEERING"})
        )
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_variant("VARIANT-CC", "OPT-WHEEL-STEERING"),),
        configuration_space_complete=True,
        variant_constraints=constraints,
    )
    assert config_set.configurations[0].identity.named_variant_id == "VARIANT-CC"


def test_variant_with_excluded_option_combination_is_rejected() -> None:
    constraints = {
        "VARIANT-CC": NamedVariantConstraint(
            variant_id="VARIANT-CC", excludes_option_ids=frozenset({"OPT-TILLER"})
        )
    }
    with pytest.raises(ValueError, match="alongside excluded option"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_variant("VARIANT-CC", "OPT-TILLER"),),
            configuration_space_complete=True,
            variant_constraints=constraints,
        )


def test_configuration_referencing_unconstrained_variant_is_unaffected() -> None:
    # A variant id with no entry in variant_constraints is not validated —
    # only explicitly supplied constraints are enforced (never invented).
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_variant("VARIANT-UNCONSTRAINED"),),
        configuration_space_complete=True,
    )
    assert config_set.configurations[0].identity.named_variant_id == "VARIANT-UNCONSTRAINED"


def test_configuration_with_no_variant_is_unaffected_by_variant_constraints() -> None:
    constraints = {
        "VARIANT-CC": NamedVariantConstraint(
            variant_id="VARIANT-CC", requires_option_ids=frozenset({"OPT-WHEEL-STEERING"})
        )
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_variant(None),),
        configuration_space_complete=True,
        variant_constraints=constraints,
    )
    assert config_set.configurations[0].identity.named_variant_id is None


def test_variant_constraint_is_not_applied_to_a_different_variant() -> None:
    # A constraint keyed to VARIANT-CC must never leak onto VARIANT-OTHER.
    constraints = {
        "VARIANT-CC": NamedVariantConstraint(
            variant_id="VARIANT-CC", requires_option_ids=frozenset({"OPT-WHEEL-STEERING"})
        )
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_variant("VARIANT-OTHER"),),
        configuration_space_complete=True,
        variant_constraints=constraints,
    )
    assert config_set.configurations[0].identity.named_variant_id == "VARIANT-OTHER"


def test_variant_constraints_mapping_key_must_match_variant_id() -> None:
    constraint = NamedVariantConstraint(variant_id="VARIANT-CC")
    with pytest.raises(ValueError, match="does not match"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_variant("VARIANT-CC"),),
            configuration_space_complete=True,
            variant_constraints={"VARIANT-WRONG-KEY": constraint},
        )


def test_mutating_source_requires_set_after_constructing_variant_constraint_is_inert() -> None:
    source_requires = {"OPT-A"}
    constraint = NamedVariantConstraint(
        variant_id="VARIANT-CC", requires_option_ids=source_requires
    )
    source_requires.add("OPT-Z")
    assert constraint.requires_option_ids == frozenset({"OPT-A"})


# ---------------------------------------------------------------------------
# REVIEW amendment (second round) — remaining blocker 2: runtime identifier
# collection validation, closing the bare-str/bytes iteration bypass
# ---------------------------------------------------------------------------


def test_applied_option_ids_rejects_bare_string() -> None:
    # "OPT-B" is itself iterable; without this guard it would silently
    # become ("O", "P", "T", "-", "B").
    with pytest.raises(ValueError, match="not a bare str"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids="OPT-B",  # type: ignore[arg-type]
        )


def test_applied_option_ids_rejects_non_iterable() -> None:
    with pytest.raises(ValueError, match="must be an iterable of string identifiers"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids=123,  # type: ignore[arg-type]
        )


def test_applied_option_ids_rejects_bare_bytes() -> None:
    with pytest.raises(ValueError, match="not a bare bytes"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids=b"OPT-A",  # type: ignore[arg-type]
        )


def test_applied_option_ids_rejects_non_string_element() -> None:
    with pytest.raises(ValueError, match="must be non-empty strings"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids=(1, 2),  # type: ignore[arg-type]
        )


def test_applied_option_ids_rejects_none_element() -> None:
    with pytest.raises(ValueError, match="must be non-empty strings"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids=(None,),  # type: ignore[arg-type]
        )


def test_applied_option_ids_rejects_empty_string_element() -> None:
    with pytest.raises(ValueError, match="must be non-empty strings"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            applied_option_ids=("OPT-A", ""),
        )


def test_named_variant_id_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        ConfigurationIdentity(
            configuration_id="cfg-1",
            boat_design_id="design-1",
            named_variant_id=123,  # type: ignore[arg-type]
        )


def test_configuration_id_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        ConfigurationIdentity(configuration_id=123, boat_design_id="design-1")  # type: ignore[arg-type]


def test_boat_design_id_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        ConfigurationIdentity(configuration_id="cfg-1", boat_design_id=123)  # type: ignore[arg-type]


def test_design_configuration_set_design_id_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        DesignConfigurationSet(
            design_id=123,  # type: ignore[arg-type]
            configurations=(_baseline_configuration(),),
            configuration_space_complete=True,
        )


def test_option_constraint_option_id_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        OptionConstraint(option_id=123)  # type: ignore[arg-type]


def test_named_variant_constraint_variant_id_rejects_non_string() -> None:
    with pytest.raises(ValueError, match="must be non-empty"):
        NamedVariantConstraint(variant_id=123)  # type: ignore[arg-type]


def test_option_constraint_requires_option_ids_rejects_bare_string() -> None:
    with pytest.raises(ValueError, match="not a bare str"):
        OptionConstraint(option_id="OPT-A", requires_option_ids="OPT-A")  # type: ignore[arg-type]


def test_option_constraint_excludes_option_ids_rejects_bare_string_bypass() -> None:
    # The literal adversarial example from the review: excludes_option_ids="OPT-B"
    # must not silently become {"O", "P", "T", "-", "B"}, which would fail to
    # intersect an applied_option_ids containing the real string "OPT-B" and
    # let a forbidden combination pass validation.
    with pytest.raises(ValueError, match="not a bare str"):
        OptionConstraint(option_id="OPT-A", excludes_option_ids="OPT-B")  # type: ignore[arg-type]


def test_bare_string_exclusion_bypass_can_no_longer_admit_a_forbidden_combination() -> None:
    # End-to-end proof: constructing the malformed constraint itself now
    # fails closed before it could ever be attached to a DesignConfigurationSet
    # and silently admit a configuration containing the real "OPT-B" id.
    with pytest.raises(ValueError, match="not a bare str"):
        OptionConstraint(option_id="OPT-A", excludes_option_ids="OPT-B")  # type: ignore[arg-type]


def test_option_constraint_requires_option_ids_rejects_non_string_element() -> None:
    with pytest.raises(ValueError, match="must be non-empty strings"):
        OptionConstraint(option_id="OPT-A", requires_option_ids=frozenset({1, 2}))  # type: ignore[arg-type]


def test_option_constraint_requires_option_ids_rejects_duplicate_via_list() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        OptionConstraint(option_id="OPT-A", requires_option_ids=["OPT-B", "OPT-B"])  # type: ignore[arg-type]


def test_named_variant_constraint_requires_option_ids_rejects_bare_string() -> None:
    with pytest.raises(ValueError, match="not a bare str"):
        NamedVariantConstraint(variant_id="VARIANT-A", requires_option_ids="OPT-A")  # type: ignore[arg-type]


def test_named_variant_constraint_excludes_option_ids_rejects_duplicate_via_list() -> None:
    with pytest.raises(ValueError, match="must not contain duplicates"):
        NamedVariantConstraint(
            variant_id="VARIANT-A",
            excludes_option_ids=["OPT-B", "OPT-B"],  # type: ignore[arg-type]
        )


# ---------------------------------------------------------------------------
# REVIEW amendment (second round) — remaining blocker 1: explicit applicability
# ---------------------------------------------------------------------------


def test_option_constraint_applicability_defaults_to_confirmed() -> None:
    constraint = OptionConstraint(option_id="OPT-A")
    assert constraint.applicability is ValueQualification.CONFIRMED


def test_option_constraint_applicability_rejects_non_value_qualification() -> None:
    with pytest.raises(ValueError, match="applicability must be a ValueQualification member"):
        OptionConstraint(option_id="OPT-A", applicability="confirmed")  # type: ignore[arg-type]


def test_confirmed_applicable_named_variant_is_accepted() -> None:
    constraints = {
        "VARIANT-CC": NamedVariantConstraint(
            variant_id="VARIANT-CC", applicability=ValueQualification.CONFIRMED
        )
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_variant("VARIANT-CC"),),
        configuration_space_complete=True,
        variant_constraints=constraints,
    )
    assert config_set.configurations[0].identity.named_variant_id == "VARIANT-CC"


def test_confirmed_applicable_design_option_is_accepted() -> None:
    constraints = {
        "OPT-A": OptionConstraint(option_id="OPT-A", applicability=ValueQualification.CONFIRMED)
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_options("OPT-A"),),
        configuration_space_complete=True,
        option_constraints=constraints,
    )
    assert config_set.configurations[0].identity.applied_option_ids == ("OPT-A",)


def test_not_applicable_named_variant_cannot_be_used_as_resolved_configuration() -> None:
    constraints = {
        "VARIANT-GAFF": NamedVariantConstraint(
            variant_id="VARIANT-GAFF", applicability=ValueQualification.NOT_APPLICABLE
        )
    }
    with pytest.raises(ValueError, match="not CONFIRMED"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_variant("VARIANT-GAFF"),),
            configuration_space_complete=True,
            variant_constraints=constraints,
        )


def test_not_applicable_design_option_cannot_be_used_as_resolved_configuration() -> None:
    constraints = {
        "OPT-DISCONTINUED": OptionConstraint(
            option_id="OPT-DISCONTINUED", applicability=ValueQualification.NOT_APPLICABLE
        )
    }
    with pytest.raises(ValueError, match="not CONFIRMED"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_options("OPT-DISCONTINUED"),),
            configuration_space_complete=True,
            option_constraints=constraints,
        )


@pytest.mark.parametrize(
    "unresolved",
    [
        ValueQualification.MISSING,
        ValueQualification.UNRESOLVED_CONFLICT,
        ValueQualification.PROVISIONAL,
        ValueQualification.APPLICABILITY_UNKNOWN,
    ],
)
def test_applicability_unknown_named_variant_cannot_authorize_true_or_false(
    unresolved: ValueQualification,
) -> None:
    constraints = {
        "VARIANT-X": NamedVariantConstraint(variant_id="VARIANT-X", applicability=unresolved)
    }
    with pytest.raises(ValueError, match="not CONFIRMED"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_variant("VARIANT-X"),),
            configuration_space_complete=False,
            variant_constraints=constraints,
        )


@pytest.mark.parametrize(
    "unresolved",
    [
        ValueQualification.MISSING,
        ValueQualification.UNRESOLVED_CONFLICT,
        ValueQualification.PROVISIONAL,
        ValueQualification.APPLICABILITY_UNKNOWN,
    ],
)
def test_applicability_unknown_design_option_cannot_authorize_true_or_false(
    unresolved: ValueQualification,
) -> None:
    constraints = {"OPT-X": OptionConstraint(option_id="OPT-X", applicability=unresolved)}
    with pytest.raises(ValueError, match="not CONFIRMED"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_configuration_with_options("OPT-X"),),
            configuration_space_complete=False,
            option_constraints=constraints,
        )


def test_unresolved_applicability_cannot_coexist_with_complete_space() -> None:
    # The disputed option is not referenced by any configuration in the set
    # at all — proving this is a set-wide guarantee, not merely a per-
    # configuration rejection.
    constraints = {
        "OPT-UNRESEARCHED": OptionConstraint(
            option_id="OPT-UNRESEARCHED", applicability=ValueQualification.APPLICABILITY_UNKNOWN
        )
    }
    with pytest.raises(ValueError, match="configuration_space_complete cannot be True"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_baseline_configuration(),),
            configuration_space_complete=True,
            option_constraints=constraints,
        )


def test_unresolved_variant_applicability_cannot_coexist_with_complete_space() -> None:
    constraints = {
        "VARIANT-UNRESEARCHED": NamedVariantConstraint(
            variant_id="VARIANT-UNRESEARCHED", applicability=ValueQualification.UNRESOLVED_CONFLICT
        )
    }
    with pytest.raises(ValueError, match="configuration_space_complete cannot be True"):
        DesignConfigurationSet(
            design_id="design-1",
            configurations=(_baseline_configuration(),),
            configuration_space_complete=True,
            variant_constraints=constraints,
        )


def test_not_applicable_does_not_force_incomplete_space() -> None:
    # NOT_APPLICABLE is a confirmed negative, not an uncertainty — it must
    # not trigger the same completeness lock as a genuinely unresolved state.
    constraints = {
        "OPT-DISCONTINUED": OptionConstraint(
            option_id="OPT-DISCONTINUED", applicability=ValueQualification.NOT_APPLICABLE
        )
    }
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_baseline_configuration(),),
        configuration_space_complete=True,
        option_constraints=constraints,
    )
    assert config_set.configuration_space_complete is True


def test_unconstrained_option_or_variant_never_receives_an_applicability_judgment() -> None:
    # No applicability state is ever inferred merely from a constraint's
    # absence: an unconstrained option/variant is unaffected regardless of
    # configuration_space_complete.
    config_set = DesignConfigurationSet(
        design_id="design-1",
        configurations=(_configuration_with_options("OPT-NEVER-MENTIONED"),),
        configuration_space_complete=True,
    )
    assert config_set.configurations[0].identity.applied_option_ids == ("OPT-NEVER-MENTIONED",)
