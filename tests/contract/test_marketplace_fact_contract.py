"""Mechanical/adversarial verification for the SLICE-0044 Gate-1 marketplace
fact/field contract.

`specs/MARKETPLACE_FACT_CONTRACT.v0.1.md` /
`specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json` /
`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` together define a bounded Gate-1
field registry: every field classifies subject, allowed assertion kinds,
presentation, search use, requiredness, delivery phase and claim risk class as
independent axes, without collapsing UNKNOWN/ABSENT/NO_KNOWN_HISTORY_DECLARED,
without letting phase and risk share one enum, and without letting a
Design-reference value silently become PhysicalBoat/listing truth.

This is a DESIGN_RESEARCH contract with NO production persistence/runtime: this
module loads the registry JSON directly (there is no `src/` loader module for
it, deliberately). Any function that *applies* the contract's resolution/
supersession/conditional-price/extraction semantics to synthetic input (the
same-authority-correction resolver, the cross-source conflict resolver, the
price validator, the illustrative extraction stub) is explicitly TEST-ONLY,
defined in this file, and never exported from or reachable through `src/`.

Independence: the expected field-id set, the expected sensitive-field set and
the expected narrative-field set are hardcoded here rather than derived from
the registry under test, so a tampered/expanded registry cannot silently
authorize its own review.
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pytest
from jsonschema import ValidationError

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
REGISTRY_PATH = SPECS / "MARKETPLACE_FIELD_REGISTRY.v0.1.json"
SCHEMA_NAME = "MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json"


def _load_registry(path: Path = REGISTRY_PATH) -> dict[str, Any]:
    raw: object = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"Registry root must be a JSON object, got {type(raw).__name__}")
    return raw


_REGISTRY = _load_registry()
_CONTRACTS = ContractRegistry.from_directory(SPECS)
_FIELDS: dict[str, dict[str, Any]] = _REGISTRY["fields"]

# ---------------------------------------------------------------------------
# Independent expectation tables -- hand-authored, never read from the
# registry under test.
# ---------------------------------------------------------------------------

_EXPECTED_LISTING_OFFER_FIELDS = {
    "listing_offer.asking_price_mode",
    "listing_offer.asking_price_amount",
    "listing_offer.currency",
    "listing_offer.location_country",
    "listing_offer.location_region",
    "listing_offer.broker_summary",
    "listing_offer.broker_description",
    "listing_offer.known_history_narrative",
    "listing_offer.vat_tax_status_claim",
}

_EXPECTED_PHYSICAL_BOAT_IDENTITY_FIELDS = {
    "physical_boat.marketed_brand_claim",
    "physical_boat.builder_claim",
    "physical_boat.model_designation_claim",
    "physical_boat.boat_name",
    "physical_boat.build_year",
    "physical_boat.hin_cin_claim",
}

_EXPECTED_PHYSICAL_BOAT_TECHNICAL_FIELDS = {
    "physical_boat.loa_length",
    "physical_boat.beam",
    "physical_boat.draft",
    "physical_boat.displacement",
    "physical_boat.hull_material",
    "physical_boat.keel_configuration",
    "physical_boat.rudder_configuration",
    "physical_boat.rig_configuration",
    "physical_boat.engine_make",
    "physical_boat.engine_model",
    "physical_boat.engine_power",
    "physical_boat.engine_hours",
    "physical_boat.fuel_type",
    "physical_boat.cabins",
    "physical_boat.berths",
    "physical_boat.heads",
}

_EXPECTED_PHYSICAL_BOAT_HISTORY_FIELDS = {
    "physical_boat.refit_events",
    "physical_boat.known_previous_owner_count",
    "physical_boat.broad_use_history",
    "physical_boat.grounding_history",
    "physical_boat.major_damage_history",
    "physical_boat.osmosis_treatment_history",
    "physical_boat.last_survey_date_claim",
}

_EXPECTED_ALL_FIELDS = (
    _EXPECTED_LISTING_OFFER_FIELDS
    | _EXPECTED_PHYSICAL_BOAT_IDENTITY_FIELDS
    | _EXPECTED_PHYSICAL_BOAT_TECHNICAL_FIELDS
    | _EXPECTED_PHYSICAL_BOAT_HISTORY_FIELDS
)

_EXPECTED_SENSITIVE_FIELDS = {
    "listing_offer.vat_tax_status_claim",
    "physical_boat.hin_cin_claim",
    "physical_boat.grounding_history",
    "physical_boat.major_damage_history",
    "physical_boat.osmosis_treatment_history",
    "physical_boat.last_survey_date_claim",
}

_EXPECTED_LATER_FIELDS = {
    "physical_boat.grounding_history",
    "physical_boat.major_damage_history",
    "physical_boat.osmosis_treatment_history",
    "physical_boat.last_survey_date_claim",
}

_EXPECTED_NARRATIVE_FIELDS = {
    "listing_offer.broker_summary",
    "listing_offer.broker_description",
    "listing_offer.known_history_narrative",
}

_EXPECTED_ASSERTION_KINDS = frozenset(
    {
        "VALUE_ASSERTION",
        "PRESENT",
        "ABSENT",
        "NO_KNOWN_HISTORY_DECLARED",
        "UNKNOWN",
        "NOT_APPLICABLE",
    }
)


# ---------------------------------------------------------------------------
# Structural validity: the registry is exhaustive against the fixed v0.1
# field inventory (not a self-authorizing fixture) and schema-valid.
# ---------------------------------------------------------------------------


def test_registry_is_schema_valid() -> None:
    _CONTRACTS.validator_by_name(SCHEMA_NAME).validate(_REGISTRY)


def test_registry_field_set_exactly_matches_the_independent_bounded_inventory() -> None:
    assert set(_FIELDS) == _EXPECTED_ALL_FIELDS
    assert len(_FIELDS) == 38


def test_a_tampered_registry_with_an_extra_field_would_fail_the_bounded_check() -> None:
    mutated = set(_FIELDS) | {"physical_boat.__synthetic_extra_field__"}
    assert mutated != _EXPECTED_ALL_FIELDS


def test_a_tampered_registry_missing_a_field_would_fail_the_bounded_check() -> None:
    mutated = set(_FIELDS) - {"physical_boat.build_year"}
    assert mutated != _EXPECTED_ALL_FIELDS


def test_no_field_uses_the_design_reference_subject() -> None:
    # DESIGN_REFERENCE is a reference/source scope, never a registry field
    # subject (MARKETPLACE_FACT_CONTRACT.v0.1 section 3.1 / section 10).
    assert "DESIGN_REFERENCE" not in _REGISTRY["subjects"]
    for field_id, entry in _FIELDS.items():
        assert entry["subject"] in {"PHYSICAL_BOAT", "LISTING_OFFER"}, field_id


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_LISTING_OFFER_FIELDS))
def test_listing_offer_fields_have_the_listing_offer_subject(field_id: str) -> None:
    assert _FIELDS[field_id]["subject"] == "LISTING_OFFER"


@pytest.mark.parametrize(
    "field_id",
    sorted(_EXPECTED_PHYSICAL_BOAT_IDENTITY_FIELDS)
    + sorted(_EXPECTED_PHYSICAL_BOAT_TECHNICAL_FIELDS)
    + sorted(_EXPECTED_PHYSICAL_BOAT_HISTORY_FIELDS),
)
def test_physical_boat_fields_have_the_physical_boat_subject(field_id: str) -> None:
    assert _FIELDS[field_id]["subject"] == "PHYSICAL_BOAT"


# ---------------------------------------------------------------------------
# Registry integrity rule 1-2: every field declares subject + non-empty
# allowed assertion kinds, drawn only from the closed set.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_ALL_FIELDS))
def test_every_field_declares_a_subject(field_id: str) -> None:
    assert _FIELDS[field_id]["subject"]


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_ALL_FIELDS))
def test_every_field_declares_at_least_one_allowed_assertion_kind(field_id: str) -> None:
    kinds = _FIELDS[field_id]["allowed_assertion_kinds"]
    assert kinds
    assert set(kinds) <= _EXPECTED_ASSERTION_KINDS


# ---------------------------------------------------------------------------
# Registry integrity rule 3: ABSENT, NO_KNOWN_HISTORY_DECLARED and UNKNOWN
# never collapse -- they are always three independently-addressable tokens
# in the closed assertion-kind vocabulary, and no field's declared subset
# conflates them by construction (each is opted into independently).
# ---------------------------------------------------------------------------


def test_absent_no_known_history_declared_and_unknown_are_three_distinct_tokens() -> None:
    assert len({"ABSENT", "NO_KNOWN_HISTORY_DECLARED", "UNKNOWN"}) == 3
    assert _EXPECTED_ASSERTION_KINDS.issuperset({"ABSENT", "NO_KNOWN_HISTORY_DECLARED", "UNKNOWN"})


def test_grounding_history_allows_unknown_and_no_known_history_declared_but_not_absent() -> None:
    # Grounding is history-sensitive: silence cannot become proven absence, so
    # ABSENT (a current bounded-state claim) is deliberately not offered.
    kinds = set(_FIELDS["physical_boat.grounding_history"]["allowed_assertion_kinds"])
    assert kinds == {"VALUE_ASSERTION", "NO_KNOWN_HISTORY_DECLARED", "UNKNOWN"}
    assert "ABSENT" not in kinds


def test_engine_make_allows_absent_for_equipment_state_not_no_known_history_declared() -> None:
    # Equipment presence/absence is a current bounded-state claim, distinct
    # from a historical no-known-history declaration.
    kinds = set(_FIELDS["physical_boat.engine_make"]["allowed_assertion_kinds"])
    assert "ABSENT" in kinds
    assert "NO_KNOWN_HISTORY_DECLARED" not in kinds


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_LATER_FIELDS))
def test_every_later_sensitive_history_field_allows_unknown_and_no_known_history(
    field_id: str,
) -> None:
    kinds = set(_FIELDS[field_id]["allowed_assertion_kinds"])
    assert "UNKNOWN" in kinds
    assert "NO_KNOWN_HISTORY_DECLARED" in kinds


# ---------------------------------------------------------------------------
# Registry integrity rule 4: delivery phase and claim risk class are
# mechanically independent axes -- proved by a field that combines a non-LATER
# phase with SENSITIVE risk (no SENSITIVE_LATER shortcut exists).
# ---------------------------------------------------------------------------


def test_delivery_phase_and_claim_risk_class_are_stored_as_separate_keys() -> None:
    for field_id, entry in _FIELDS.items():
        assert "delivery_phase" in entry, field_id
        assert "claim_risk_class" in entry, field_id
        assert entry["delivery_phase"] != entry["claim_risk_class"]


def test_vat_tax_status_claim_proves_gate_1_optional_and_sensitive_coexist() -> None:
    entry = _FIELDS["listing_offer.vat_tax_status_claim"]
    assert entry["delivery_phase"] == "GATE_1_OPTIONAL"
    assert entry["claim_risk_class"] == "SENSITIVE"


def test_not_every_sensitive_field_is_later() -> None:
    sensitive_phases = {
        entry["delivery_phase"]
        for fid, entry in _FIELDS.items()
        if fid in _EXPECTED_SENSITIVE_FIELDS
    }
    assert sensitive_phases == {"GATE_1_OPTIONAL", "LATER"}


def test_not_every_later_field_is_sensitive_and_vice_versa_is_not_assumed() -> None:
    # LATER fields in v0.1 happen to all be SENSITIVE (deferred history
    # exemplars), but the axes remain independently stored/settable; this
    # locks the current v0.1 composition without asserting a structural rule
    # that phase implies risk.
    later_field_ids = {fid for fid, entry in _FIELDS.items() if entry["delivery_phase"] == "LATER"}
    assert later_field_ids == _EXPECTED_LATER_FIELDS
    assert all(_FIELDS[fid]["claim_risk_class"] == "SENSITIVE" for fid in later_field_ids)


# ---------------------------------------------------------------------------
# Registry integrity rule 5: CONDITIONAL requiredness always carries a
# machine-readable condition; REQUIRED_RESPONSE/OPTIONAL never do.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_ALL_FIELDS))
def test_conditional_requiredness_always_has_a_condition_and_others_never_do(
    field_id: str,
) -> None:
    requiredness = _FIELDS[field_id]["requiredness"]
    if requiredness["kind"] == "CONDITIONAL":
        assert requiredness["condition"] is not None
        assert requiredness["condition"]["depends_on_field"] in _FIELDS
    else:
        assert requiredness["condition"] is None


def test_price_amount_and_currency_are_the_only_conditional_fields() -> None:
    conditional = {
        fid for fid, entry in _FIELDS.items() if entry["requiredness"]["kind"] == "CONDITIONAL"
    }
    assert conditional == {"listing_offer.asking_price_amount", "listing_offer.currency"}


@pytest.mark.parametrize(
    "field_id", ["listing_offer.asking_price_amount", "listing_offer.currency"]
)
def test_conditional_price_fields_depend_on_price_mode_equal_amount(field_id: str) -> None:
    condition = _FIELDS[field_id]["requiredness"]["condition"]
    assert condition == {
        "depends_on_field": "listing_offer.asking_price_mode",
        "when_value": "AMOUNT",
        "required_when_true": True,
    }


# ---------------------------------------------------------------------------
# Registry integrity rule 6-7: every SENSITIVE field is DISPLAY_ONLY and
# carries an attributed/non-verified presentation policy (contract section 4
# / section 11 extend this to every SENSITIVE field, not only PUBLIC ones).
# ---------------------------------------------------------------------------


def test_sensitive_field_set_matches_the_independent_expectation() -> None:
    sensitive = {fid for fid, entry in _FIELDS.items() if entry["claim_risk_class"] == "SENSITIVE"}
    assert sensitive == _EXPECTED_SENSITIVE_FIELDS
    assert len(sensitive) == 6


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_SENSITIVE_FIELDS))
def test_every_sensitive_field_is_display_only(field_id: str) -> None:
    assert _FIELDS[field_id]["search_use"] == "DISPLAY_ONLY"


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_SENSITIVE_FIELDS))
def test_every_sensitive_field_has_an_attributed_non_verified_presentation_policy(
    field_id: str,
) -> None:
    policy = _FIELDS[field_id]["presentation_policy"]
    assert policy is not None
    assert policy["forbids_unqualified_assertion"] is True
    assert policy["requires_attribution"] is True
    assert policy["requires_last_confirmed_disclosure"] is True
    assert policy["requires_verification_status_disclosure"] is True
    assert policy["verification_status_default"] == "NONE"
    assert policy["template_hint"]


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_ALL_FIELDS - _EXPECTED_SENSITIVE_FIELDS))
def test_no_non_sensitive_field_carries_a_presentation_policy(field_id: str) -> None:
    assert _FIELDS[field_id]["presentation_policy"] is None


def test_a_tampered_sensitive_field_marked_searchable_would_fail_schema_validation() -> None:
    mutated = json.loads(json.dumps(_REGISTRY))
    mutated["fields"]["listing_offer.vat_tax_status_claim"]["search_use"] = "SEARCHABLE"
    with pytest.raises(ValidationError):
        _CONTRACTS.validator_by_name(SCHEMA_NAME).validate(mutated)


def test_a_sensitive_field_without_a_presentation_policy_fails_schema_validation() -> None:
    mutated = json.loads(json.dumps(_REGISTRY))
    mutated["fields"]["physical_boat.hin_cin_claim"]["presentation_policy"] = None
    with pytest.raises(ValidationError):
        _CONTRACTS.validator_by_name(SCHEMA_NAME).validate(mutated)


def test_forbidden_unqualified_wording_is_not_the_template_hint_for_any_sensitive_field() -> None:
    forbidden = {"VAT: PAID", "Grounding: NO", "Damage history: NONE", "HIN/CIN: VERIFIED"}
    for field_id in _EXPECTED_SENSITIVE_FIELDS:
        hint = _FIELDS[field_id]["presentation_policy"]["template_hint"]
        assert hint not in forbidden
        assert "verification: none" in hint.lower() or "verification" in hint.lower()


# ---------------------------------------------------------------------------
# Registry integrity rule 8: free-text narrative fields are DISPLAY_ONLY and
# never structured-search truth.
# ---------------------------------------------------------------------------


def test_narrative_field_set_matches_the_independent_expectation() -> None:
    free_text = {
        fid for fid, entry in _FIELDS.items() if entry["value_type"]["data_type"] == "free_text"
    }
    # grounding/damage/osmosis history are also modeled as free_text but are
    # LATER/SENSITIVE claim fields, not the three narrative-only fields.
    narrative_only = free_text - _EXPECTED_LATER_FIELDS
    assert narrative_only == _EXPECTED_NARRATIVE_FIELDS


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_NARRATIVE_FIELDS))
def test_every_narrative_field_is_display_only(field_id: str) -> None:
    assert _FIELDS[field_id]["search_use"] == "DISPLAY_ONLY"
    assert _FIELDS[field_id]["value_type"]["data_type"] == "free_text"


# ---------------------------------------------------------------------------
# Registry integrity rule 9: previous-owner count is not searchable and
# carries no identity payload.
# ---------------------------------------------------------------------------


def test_previous_owner_count_is_display_only_not_searchable() -> None:
    entry = _FIELDS["physical_boat.known_previous_owner_count"]
    assert entry["search_use"] == "DISPLAY_ONLY"
    assert "name" not in entry["topic"].lower()


def test_previous_owner_count_notes_explicitly_forbid_owner_identity_and_quality_score() -> None:
    notes = _FIELDS["physical_boat.known_previous_owner_count"]["notes"] or ""
    assert "name" in notes.lower() or "identifier" in notes.lower()
    assert "quality score" in notes.lower()


# ---------------------------------------------------------------------------
# Registry integrity rule 10: declared documentation availability never
# implies attachment, review or verification.
# ---------------------------------------------------------------------------


def test_declared_documentation_availability_is_a_closed_three_state_set() -> None:
    descriptor = _REGISTRY["event_structures"]["refit_event_v0_1"][
        "supporting_documentation_declared_available"
    ]
    assert set(descriptor["values"]) == {"YES", "NO", "UNKNOWN"}
    for forbidden_state in ("ATTACHED", "REVIEWED", "VERIFIED"):
        assert forbidden_state not in descriptor["values"]


# ---------------------------------------------------------------------------
# Registry integrity rule 11: Design reference values never auto-fill a
# missing PhysicalBoat value. TEST-ONLY reference lookup function proves the
# property adversarially: mutating the design reference never changes the
# PhysicalBoat lookup result.
# ---------------------------------------------------------------------------


def _physical_boat_value(
    field: str,
    physical_observations: dict[str, str],
    design_reference_values: dict[str, str],
) -> str:
    """TEST-ONLY reference lookup. Deliberately never reads
    ``design_reference_values`` -- the parameter exists only so adversarial
    tests can prove mutating it has zero effect on the result."""
    return physical_observations.get(field, "UNKNOWN")


def test_missing_physical_boat_draft_remains_unknown_despite_a_design_reference_value() -> None:
    design_reference = {"draft": "1.65"}
    result = _physical_boat_value("draft", {}, design_reference)
    assert result == "UNKNOWN"


def test_mutating_the_design_reference_value_never_changes_the_physical_boat_result() -> None:
    baseline = _physical_boat_value("draft", {}, {"draft": "1.65"})
    mutated = _physical_boat_value("draft", {}, {"draft": "9.99"})
    absent = _physical_boat_value("draft", {}, {})
    assert baseline == mutated == absent == "UNKNOWN"


def test_an_explicit_physical_boat_observation_is_used_and_still_ignores_design() -> None:
    result = _physical_boat_value("draft", {"draft": "1.70"}, {"draft": "1.65"})
    assert result == "1.70"


# ---------------------------------------------------------------------------
# Registry integrity rule 12: numeric searchable technical fields declare
# normalized type/unit semantics.
# ---------------------------------------------------------------------------


_NUMERIC_DATA_TYPES = {"decimal", "integer"}


@pytest.mark.parametrize(
    "field_id",
    sorted(
        fid
        for fid, entry in _FIELDS.items()
        if entry["search_use"] == "SEARCHABLE"
        and entry["value_type"]["data_type"] in _NUMERIC_DATA_TYPES
    ),
)
def test_every_numeric_searchable_field_declares_a_unit_system(field_id: str) -> None:
    value_type = _FIELDS[field_id]["value_type"]
    assert value_type["unit_system"] is not None, field_id


def test_a_numeric_field_missing_unit_system_is_still_schema_valid_shape_wise() -> None:
    mutated = json.loads(json.dumps(_REGISTRY))
    mutated["fields"]["physical_boat.draft"]["value_type"]["unit_system"] = None
    # unit_system: null is still schema-valid shape-wise (nullable), so the
    # contract-level unit-semantics rule is enforced by the dedicated test
    # above, not by the JSON Schema alone; this test documents that boundary
    # rather than asserting a schema-level rejection.
    _CONTRACTS.validator_by_name(SCHEMA_NAME).validate(mutated)
    value_type = mutated["fields"]["physical_boat.draft"]["value_type"]
    assert value_type["unit_system"] is None


# ---------------------------------------------------------------------------
# Registry integrity rule 13: REQUIRED_RESPONSE never forces a guessed value
# where UNKNOWN is legitimate -- allows_unknown_response is internally
# consistent with the declared allowed_assertion_kinds for every field.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_ALL_FIELDS))
def test_allows_unknown_response_is_consistent_with_allowed_assertion_kinds(
    field_id: str,
) -> None:
    entry = _FIELDS[field_id]
    allows_unknown = entry["requiredness"]["allows_unknown_response"]
    unknown_is_allowed_kind = "UNKNOWN" in entry["allowed_assertion_kinds"]
    assert allows_unknown == unknown_is_allowed_kind, field_id


def test_build_year_is_required_response_with_unknown_explicitly_allowed() -> None:
    entry = _FIELDS["physical_boat.build_year"]
    assert entry["requiredness"]["kind"] == "REQUIRED_RESPONSE"
    assert entry["requiredness"]["allows_unknown_response"] is True
    assert "UNKNOWN" in entry["allowed_assertion_kinds"]


def test_a_mutation_that_breaks_the_allows_unknown_consistency_would_be_caught() -> None:
    entry = _FIELDS["physical_boat.build_year"]
    tampered_allows_unknown = not entry["requiredness"]["allows_unknown_response"]
    unknown_is_allowed_kind = "UNKNOWN" in entry["allowed_assertion_kinds"]
    assert tampered_allows_unknown != unknown_is_allowed_kind


# ---------------------------------------------------------------------------
# Registry integrity rule 14-15: conditional price requiredness. TEST-ONLY
# reference validator over price_mode/amount/currency.
# ---------------------------------------------------------------------------


def _validate_price(price_mode: str, amount: float | None, currency: str | None) -> bool:
    """TEST-ONLY reference implementation of the price conditional-
    requiredness lock (MARKETPLACE_FACT_CONTRACT.v0.1 section 3.8)."""
    if price_mode == "AMOUNT":
        return amount is not None and currency is not None
    if price_mode == "POA":
        return amount is None
    raise ValueError(f"unrecognized price_mode {price_mode!r}")


@pytest.mark.parametrize(
    ("price_mode", "amount", "currency", "expected_valid"),
    [
        ("AMOUNT", None, "EUR", False),
        ("AMOUNT", 150000.0, None, False),
        ("AMOUNT", 150000.0, "EUR", True),
        ("POA", None, None, True),
        ("POA", 150000.0, None, False),
    ],
)
def test_conditional_price_requiredness_matches_the_locked_truth_table(
    price_mode: str, amount: float | None, currency: str | None, expected_valid: bool
) -> None:
    assert _validate_price(price_mode, amount, currency) is expected_valid


def test_price_mode_values_are_exactly_amount_and_poa() -> None:
    assert set(_FIELDS["listing_offer.asking_price_mode"]["value_type"]["values"]) == {
        "AMOUNT",
        "POA",
    }


# ---------------------------------------------------------------------------
# Registry integrity rule 16: Brand and Builder remain distinct fields.
# ---------------------------------------------------------------------------


def test_brand_and_builder_are_two_distinct_fields_with_different_requiredness() -> None:
    brand = _FIELDS["physical_boat.marketed_brand_claim"]
    builder = _FIELDS["physical_boat.builder_claim"]
    assert brand["topic"] != builder["topic"]
    assert brand["requiredness"]["kind"] == "REQUIRED_RESPONSE"
    assert builder["requiredness"]["kind"] == "OPTIONAL"


def test_raw_brand_and_model_claims_are_distinct_from_any_resolved_design_identity() -> None:
    for field_id in (
        "physical_boat.marketed_brand_claim",
        "physical_boat.model_designation_claim",
    ):
        notes = (_FIELDS[field_id]["notes"] or "").lower()
        assert "boatdesign" in notes


# ---------------------------------------------------------------------------
# Registry integrity rule 17 / correction & supersession semantics: TEST-ONLY
# reference resolution engine over a set of observations for one fact topic.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Observation:
    observation_id: str
    claim_authority: str
    value: str
    supersedes_observation_id: str | None = None


@dataclass(frozen=True)
class _ResolutionResult:
    state: str  # "RESOLVED" | "CONFLICT" | "UNRESOLVED"
    value: str | None


def _resolve_fact_topic(observations: list[_Observation]) -> _ResolutionResult:
    """TEST-ONLY reference resolver implementing MARKETPLACE_FACT_CONTRACT.v0.1
    section 6: same-authority explicit supersession is non-destructive and
    becomes that authority's current statement; cross-source disagreement
    without a shared, authorized supersession chain is CONFLICT; a
    contradictory later observation from the *same* authority that is not
    explicitly marked as a correction is also CONFLICT, never silent
    "latest wins". Grouping by claim_authority is what makes cross-source
    supersession structurally impossible: an observation's
    supersedes_observation_id is only ever resolved against observations
    already in its own authority's group.
    """
    if not observations:
        return _ResolutionResult(state="UNRESOLVED", value=None)

    by_authority: dict[str, list[_Observation]] = defaultdict(list)
    for observation in observations:
        by_authority[observation.claim_authority].append(observation)

    current_value_by_authority: dict[str, str] = {}
    for _authority, own_observations in by_authority.items():
        superseded_ids = {
            o.supersedes_observation_id for o in own_observations if o.supersedes_observation_id
        }
        current = [o for o in own_observations if o.observation_id not in superseded_ids]
        distinct_current_values = {o.value for o in current}
        if len(distinct_current_values) != 1:
            # Either an unauthorized same-authority contradiction, or an
            # authority whose every observation was (impossibly) superseded.
            return _ResolutionResult(state="CONFLICT", value=None)
        current_value_by_authority[_authority] = next(iter(distinct_current_values))

    distinct_cross_source_values = set(current_value_by_authority.values())
    if len(distinct_cross_source_values) == 1:
        return _ResolutionResult(state="RESOLVED", value=next(iter(distinct_cross_source_values)))
    return _ResolutionResult(state="CONFLICT", value=None)


def test_empty_observation_set_is_unresolved() -> None:
    assert _resolve_fact_topic([]) == _ResolutionResult(state="UNRESOLVED", value=None)


def test_single_source_single_observation_resolves() -> None:
    observations = [_Observation("O-1", "ORG-A", "standing rigging replaced 2021")]
    assert _resolve_fact_topic(observations) == _ResolutionResult(
        state="RESOLVED", value="standing rigging replaced 2021"
    )


def test_cross_source_disagreement_without_resolution_is_conflict() -> None:
    # Org A: standing rigging replaced 2021; Org B: standing rigging replaced
    # 2022 -> CONFLICT, and a later source never wins merely by being newer.
    observations = [
        _Observation("O-1", "ORG-A", "standing rigging replaced 2021"),
        _Observation("O-2", "ORG-B", "standing rigging replaced 2022"),
    ]
    result = _resolve_fact_topic(observations)
    assert result.state == "CONFLICT"
    assert result.value is None


def test_same_authority_explicit_supersession_is_non_destructive_correction() -> None:
    # Org A #1: 2021; Org A #2 explicitly supersedes #1 -> 2022.
    observations = [
        _Observation("A-1", "ORG-A", "2021"),
        _Observation("A-2", "ORG-A", "2022", supersedes_observation_id="A-1"),
    ]
    result = _resolve_fact_topic(observations)
    assert result == _ResolutionResult(state="RESOLVED", value="2022")
    # #1 remains present in the input/audit trail; the resolver did not
    # delete or mutate it.
    assert observations[0].value == "2021"


def test_a_different_organization_cannot_use_supersession_to_erase_org_as_claim() -> None:
    # Org B declares supersedes_observation_id pointing at Org A's
    # observation. Because resolution groups strictly by claim_authority,
    # Org B's declaration has zero effect on Org A's current statement.
    observations = [
        _Observation("A-1", "ORG-A", "2021"),
        _Observation("B-1", "ORG-B", "2022", supersedes_observation_id="A-1"),
    ]
    result = _resolve_fact_topic(observations)
    # Org A still contributes "2021" and Org B contributes "2022" as two
    # live, disagreeing current statements -> CONFLICT, not a B-wins outcome.
    assert result.state == "CONFLICT"


def test_same_source_contradiction_without_explicit_correction_stays_conflict() -> None:
    # Org A makes two observations that disagree, with no supersedes link at
    # all -- no silent "latest wins".
    observations = [
        _Observation("A-1", "ORG-A", "2021"),
        _Observation("A-2", "ORG-A", "2022"),
    ]
    result = _resolve_fact_topic(observations)
    assert result.state == "CONFLICT"


def test_a_correction_chain_of_two_still_resolves_after_a_third_agreeing_source() -> None:
    observations = [
        _Observation("A-1", "ORG-A", "2021"),
        _Observation("A-2", "ORG-A", "2022", supersedes_observation_id="A-1"),
        _Observation("B-1", "ORG-B", "2022"),
    ]
    result = _resolve_fact_topic(observations)
    assert result == _ResolutionResult(state="RESOLVED", value="2022")


# ---------------------------------------------------------------------------
# Hard future-search semantics: UNKNOWN/UNRESOLVED/CONFLICT never satisfy a
# hard Required predicate, and CONFLICT is never opportunistically matched.
# ---------------------------------------------------------------------------


def _satisfies_hard_required(resolution: _ResolutionResult, required_value: str) -> bool:
    """TEST-ONLY reference predicate for MARKETPLACE_FACT_CONTRACT.v0.1
    section 5."""
    return resolution.state == "RESOLVED" and resolution.value == required_value


def test_conflict_never_satisfies_a_hard_required_predicate_even_when_a_value_matches() -> None:
    # One of the two conflicting observations happens to match the buyer
    # query; CONFLICT must still not be selected to manufacture a match.
    observations = [
        _Observation("A-1", "ORG-A", "2021"),
        _Observation("B-1", "ORG-B", "2022"),
    ]
    resolution = _resolve_fact_topic(observations)
    assert _satisfies_hard_required(resolution, "2021") is False
    assert _satisfies_hard_required(resolution, "2022") is False


def test_unresolved_never_satisfies_a_hard_required_predicate() -> None:
    resolution = _resolve_fact_topic([])
    assert resolution.state == "UNRESOLVED"
    assert _satisfies_hard_required(resolution, "anything") is False


def test_no_known_history_declared_never_satisfies_a_proven_never_occurred_predicate() -> None:
    # A NO_KNOWN_HISTORY_DECLARED assertion is not modeled as a resolvable
    # value at all in this reference model -- it never becomes the
    # RESOLVED-compatible value a hard "never grounded" filter would require.
    resolution = _ResolutionResult(state="RESOLVED", value="NO_KNOWN_HISTORY_DECLARED")
    assert _satisfies_hard_required(resolution, "PROVEN_NEVER_GROUNDED") is False


# ---------------------------------------------------------------------------
# Free-text extraction: suggestion-only, never auto-promoted, extraction
# confidence is not truth confidence. TEST-ONLY illustrative stub.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _ExtractionCandidate:
    source_text: str
    candidate_value: str
    timing_precision: str  # "EXACT" | "APPROXIMATE" | "UNKNOWN"
    extraction_confidence: str  # "high" | "medium" | "low" | "unknown"
    truth_confirmed: bool


def _extract_refit_candidate(text: str) -> _ExtractionCandidate:
    """TEST-ONLY illustrative extraction stub. Never ships under `src/`; exists
    only to prove that a vague temporal phrase cannot be auto-promoted into an
    exact year or an auto-confirmed truth claim, regardless of how confident
    the (stub) extractor is in its own text interpretation."""
    return _ExtractionCandidate(
        source_text=text,
        candidate_value="standing rigging replacement",
        timing_precision="APPROXIMATE",
        extraction_confidence="medium",
        truth_confirmed=False,
    )


def test_vague_extraction_text_never_becomes_an_exact_year_claim() -> None:
    candidate = _extract_refit_candidate("Rigging was done by the previous owner a few years ago.")
    assert candidate.timing_precision != "EXACT"
    assert candidate.timing_precision == "APPROXIMATE"


def test_extraction_confidence_never_implies_truth_confirmation() -> None:
    candidate = _extract_refit_candidate("Rigging was done by the previous owner a few years ago.")
    assert candidate.extraction_confidence in {"high", "medium", "low", "unknown"}
    # Confidence is about text interpretation only; it never confirms truth.
    assert candidate.truth_confirmed is False


# ---------------------------------------------------------------------------
# Free-text rules: broker_description requiredness never forces the
# structured-search axis; a well-formed text answer alone cannot satisfy a
# technical Required filter because it is DISPLAY_ONLY.
# ---------------------------------------------------------------------------


def test_broker_description_is_required_response_but_never_searchable() -> None:
    entry = _FIELDS["listing_offer.broker_description"]
    assert entry["requiredness"]["kind"] == "REQUIRED_RESPONSE"
    assert entry["search_use"] == "DISPLAY_ONLY"


# ---------------------------------------------------------------------------
# Refit event structure: exact minimum shape, no document upload path.
# ---------------------------------------------------------------------------


def test_refit_event_structure_has_exactly_the_locked_minimum_fields() -> None:
    structure = _REGISTRY["event_structures"]["refit_event_v0_1"]
    assert set(structure) == {
        "event_kind",
        "category",
        "topic",
        "action",
        "timing",
        "description",
        "supporting_documentation_declared_available",
    }


def test_refit_events_field_references_the_refit_event_structure() -> None:
    assert _FIELDS["physical_boat.refit_events"]["event_structure_ref"] == "refit_event_v0_1"


@pytest.mark.parametrize("field_id", sorted(_EXPECTED_ALL_FIELDS - {"physical_boat.refit_events"}))
def test_only_refit_events_references_an_event_structure(field_id: str) -> None:
    assert _FIELDS[field_id]["event_structure_ref"] is None


def test_refit_event_description_is_optional() -> None:
    description = _REGISTRY["event_structures"]["refit_event_v0_1"]["description"]
    assert description["required"] is False


# ---------------------------------------------------------------------------
# Refit category: closed Gate-1 vocabulary, not free text (readiness fix #2).
# ---------------------------------------------------------------------------

_EXPECTED_REFIT_CATEGORIES = frozenset(
    {
        "RIGGING",
        "SAILS",
        "ENGINE_PROPULSION",
        "ELECTRICAL_ENERGY",
        "NAVIGATION",
        "HULL",
        "DECK",
        "PLUMBING",
        "HVAC_COMFORT",
        "INTERIOR",
        "SAFETY",
        "OTHER",
    }
)


def test_refit_category_is_a_closed_bounded_vocabulary_matching_the_independent_set() -> None:
    category = _REGISTRY["event_structures"]["refit_event_v0_1"]["category"]
    assert category["data_type"] == "categorical"
    assert category["values"] is not None
    assert set(category["values"]) == _EXPECTED_REFIT_CATEGORIES
    assert len(category["values"]) == len(set(category["values"]))


def _validate_refit_category(category: str) -> bool:
    """TEST-ONLY reference validator: a refit category must be drawn from the
    closed Gate-1 vocabulary declared in the registry, never free text."""
    return category in _EXPECTED_REFIT_CATEGORIES


@pytest.mark.parametrize("category", sorted(_EXPECTED_REFIT_CATEGORIES))
def test_every_registered_category_token_is_accepted(category: str) -> None:
    assert _validate_refit_category(category) is True


@pytest.mark.parametrize("category", ["PAINT_JOB", "rigging", "GALLEY", ""])
def test_an_out_of_vocabulary_category_is_rejected(category: str) -> None:
    assert _validate_refit_category(category) is False


def test_a_tampered_category_registry_missing_a_token_would_be_caught() -> None:
    category = _REGISTRY["event_structures"]["refit_event_v0_1"]["category"]
    tampered = set(category["values"]) - {"SAFETY"}
    assert tampered != _EXPECTED_REFIT_CATEGORIES


# ---------------------------------------------------------------------------
# Refit timing: structured precision + the actual temporal payload, not a
# bare precision token (readiness fix #1).
# ---------------------------------------------------------------------------


def test_refit_event_timing_is_a_structured_shape_not_a_bare_token() -> None:
    timing = _REGISTRY["event_structures"]["refit_event_v0_1"]["timing"]
    assert timing["data_type"] == "timing_structure"
    assert timing["values"] is None
    assert set(timing["components"]) == {
        "precision",
        "exact_year",
        "exact_date",
        "approximate_period",
    }


def test_refit_timing_precision_component_supports_exact_approximate_and_unknown() -> None:
    precision = _REGISTRY["event_structures"]["refit_event_v0_1"]["timing"]["components"][
        "precision"
    ]
    assert set(precision["values"]) == {"EXACT", "APPROXIMATE", "UNKNOWN"}


def test_a_scalar_timing_field_would_fail_schema_validation() -> None:
    # Guards against silently reverting to the pre-amendment bare-token shape:
    # a scalar (non-object) components value is schema-invalid for
    # data_type=timing_structure.
    mutated = json.loads(json.dumps(_REGISTRY))
    mutated["event_structures"]["refit_event_v0_1"]["timing"]["components"] = None
    with pytest.raises(ValidationError):
        _CONTRACTS.validator_by_name(SCHEMA_NAME).validate(mutated)


@dataclass(frozen=True)
class _RefitTiming:
    precision: str
    exact_year: int | None = None
    exact_date: str | None = None
    approximate_period: str | None = None


def _is_valid_iso_calendar_date(value: str) -> bool:
    """TEST-ONLY: True only for a real, parseable ISO 8601 calendar date --
    not merely any string (rejects malformed/impossible dates like
    "2022-13-40" or "not-a-date")."""
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_refit_timing(timing: _RefitTiming) -> bool:
    """TEST-ONLY reference validator implementing MARKETPLACE_FACT_CONTRACT.v0.1
    section 9: the actual temporal payload must match its declared precision.
    EXACT requires exactly one of exact_year/exact_date (never neither, never
    both), and a supplied exact_date must be a genuine ISO calendar date.
    APPROXIMATE requires a non-empty, non-whitespace-only approximate_period.
    No precision may carry another precision's payload or a fabricated value."""
    exact_year = timing.exact_year
    exact_date = timing.exact_date
    approximate_period = timing.approximate_period

    if timing.precision == "EXACT":
        if approximate_period is not None:
            return False
        if (exact_year is None) == (exact_date is None):
            # Both True (neither supplied) or both False (both supplied) are
            # invalid; exactly one of the two must be non-null.
            return False
        return exact_date is None or _is_valid_iso_calendar_date(exact_date)

    if timing.precision == "APPROXIMATE":
        if exact_year is not None or exact_date is not None:
            return False
        return approximate_period is not None and bool(approximate_period.strip())

    if timing.precision == "UNKNOWN":
        return exact_year is None and exact_date is None and approximate_period is None

    raise ValueError(f"unrecognized precision {timing.precision!r}")


@pytest.mark.parametrize(
    ("timing", "expected_valid"),
    [
        # EXACT: exactly one of exact_year/exact_date, never neither/both.
        (_RefitTiming(precision="EXACT"), False),
        (_RefitTiming(precision="EXACT", exact_year=2022), True),
        (_RefitTiming(precision="EXACT", exact_date="2022-05-01"), True),
        (_RefitTiming(precision="EXACT", exact_year=2022, exact_date="2022-05-01"), False),
        (_RefitTiming(precision="EXACT", exact_date="2022-13-40"), False),
        (_RefitTiming(precision="EXACT", exact_date="not-a-date"), False),
        (
            _RefitTiming(precision="EXACT", exact_year=2022, approximate_period="early 2020s"),
            False,
        ),
        # APPROXIMATE: non-empty, non-whitespace-only period; no exact payload.
        (_RefitTiming(precision="APPROXIMATE"), False),
        (_RefitTiming(precision="APPROXIMATE", approximate_period=""), False),
        (_RefitTiming(precision="APPROXIMATE", approximate_period="   "), False),
        (_RefitTiming(precision="APPROXIMATE", approximate_period="early 2020s"), True),
        (_RefitTiming(precision="APPROXIMATE", exact_year=2022), False),
        # UNKNOWN: no payload at all, of any kind.
        (_RefitTiming(precision="UNKNOWN"), True),
        (_RefitTiming(precision="UNKNOWN", exact_year=2022), False),
        (_RefitTiming(precision="UNKNOWN", exact_date="2022-05-01"), False),
        (_RefitTiming(precision="UNKNOWN", approximate_period="early 2020s"), False),
    ],
)
def test_refit_timing_validity_matches_the_locked_truth_table(
    timing: _RefitTiming, expected_valid: bool
) -> None:
    assert _validate_refit_timing(timing) is expected_valid


def test_unrecognized_precision_fails_closed_not_open() -> None:
    with pytest.raises(ValueError):
        _validate_refit_timing(_RefitTiming(precision="SOMEDAY"))


def test_iso_calendar_date_helper_accepts_real_dates_and_rejects_malformed_ones() -> None:
    assert _is_valid_iso_calendar_date("2022-05-01") is True
    assert _is_valid_iso_calendar_date("2022-13-40") is False
    assert _is_valid_iso_calendar_date("not-a-date") is False


# ---------------------------------------------------------------------------
# broad_use_history: bounded, duplicate-free multi-value set (readiness fix
# #3). UNKNOWN carries no values payload; equal sets in different member
# order do not manufacture a false CONFLICT.
# ---------------------------------------------------------------------------

_EXPECTED_USE_HISTORY_VALUES = frozenset(
    {"PRIVATE", "CHARTER", "SAILING_SCHOOL", "RACING", "LIVEABOARD", "COMMERCIAL"}
)


def test_broad_use_history_has_multi_cardinality_and_the_independent_vocabulary() -> None:
    value_type = _FIELDS["physical_boat.broad_use_history"]["value_type"]
    assert value_type["cardinality"] == "MULTI"
    assert value_type["values"] is not None
    assert set(value_type["values"]) == _EXPECTED_USE_HISTORY_VALUES


@pytest.mark.parametrize(
    "field_id", sorted(_EXPECTED_ALL_FIELDS - {"physical_boat.broad_use_history"})
)
def test_every_other_field_has_single_cardinality(field_id: str) -> None:
    assert _FIELDS[field_id]["value_type"]["cardinality"] == "SINGLE"


def test_a_multi_field_without_a_values_vocabulary_would_fail_schema_validation() -> None:
    mutated = json.loads(json.dumps(_REGISTRY))
    mutated["fields"]["physical_boat.broad_use_history"]["value_type"]["values"] = None
    with pytest.raises(ValidationError):
        _CONTRACTS.validator_by_name(SCHEMA_NAME).validate(mutated)


def _validate_broad_use_history(assertion_kind: str, values: list[str] | None) -> bool:
    """TEST-ONLY reference validator implementing
    MARKETPLACE_FACT_CONTRACT.v0.1 section 10.4: UNKNOWN carries no values
    payload at all; a VALUE_ASSERTION carries a non-empty, duplicate-free
    subset of the closed vocabulary. An empty declared set is invalid, not a
    synonym for UNKNOWN."""
    if assertion_kind == "UNKNOWN":
        return values is None
    if assertion_kind == "VALUE_ASSERTION":
        if not values:
            return False
        if len(values) != len(set(values)):
            return False
        return set(values) <= _EXPECTED_USE_HISTORY_VALUES
    raise ValueError(f"unrecognized assertion_kind {assertion_kind!r}")


@pytest.mark.parametrize(
    ("assertion_kind", "values", "expected_valid"),
    [
        ("UNKNOWN", None, True),
        ("UNKNOWN", ["PRIVATE"], False),
        ("VALUE_ASSERTION", ["PRIVATE"], True),
        ("VALUE_ASSERTION", ["CHARTER", "PRIVATE"], True),
        ("VALUE_ASSERTION", ["RACING", "PRIVATE"], True),
        ("VALUE_ASSERTION", ["PRIVATE", "PRIVATE"], False),
        ("VALUE_ASSERTION", [], False),
        ("VALUE_ASSERTION", ["SOMETHING_ELSE"], False),
    ],
)
def test_broad_use_history_validity_matches_the_locked_truth_table(
    assertion_kind: str, values: list[str] | None, expected_valid: bool
) -> None:
    assert _validate_broad_use_history(assertion_kind, values) is expected_valid


@dataclass(frozen=True)
class _UseHistoryObservation:
    observation_id: str
    claim_authority: str
    assertion_kind: str  # "VALUE_ASSERTION" | "UNKNOWN"
    values: frozenset[str] | None = None
    supersedes_observation_id: str | None = None


@dataclass(frozen=True)
class _UseHistoryResolution:
    known_positive_uses: frozenset[str]
    by_authority: dict[str, frozenset[str] | None]


def _resolve_broad_use_history(
    observations: list[_UseHistoryObservation],
) -> _UseHistoryResolution:
    """TEST-ONLY reference resolver for the OPEN-WORLD, non-exclusive
    broad_use_history fact topic (MARKETPLACE_FACT_CONTRACT.v0.1 section
    10.4) -- deliberately distinct from the generic single-valued, equality-
    based _resolve_fact_topic used for every other fact topic in this file.

    Positive category declarations are additive, not competing, both ACROSS
    sources and WITHIN one source: two still-active observations from the
    same authority that declare different categories (e.g. {PRIVATE} and
    {CHARTER}, with no supersession link between them) are NOT a
    contradiction -- both are simultaneously true positive facts, so they
    are unioned into that authority's current set rather than being
    discarded as "ambiguous". Only an explicit supersedes_observation_id
    link retracts/replaces a prior observation; superseded observations are
    excluded from the union (a real correction, not an automatic merge with
    what it replaced). UNKNOWN contributes no category but never erases an
    already-active positive observation from the same authority. There is
    no CONFLICT state at all in this resolver's return type -- only a
    per-authority current view and a convenience cross-authority union.

    Cross-authority supersession is structurally impossible: an
    observation's supersedes_observation_id is only ever resolved against
    other observations already grouped under its own claim_authority, so a
    different Organization's observation can never retract another
    Organization's active claim.

    Each source's original observation remains independently present in
    ``observations`` (nothing here mutates or discards it), and
    ``by_authority`` exposes each authority's own current set separately
    from the ``known_positive_uses`` union -- both are presentation/
    resolution convenience only and must never be read as a stronger,
    jointly-verified fact than what each source individually asserted.
    """
    by_authority_observations: dict[str, list[_UseHistoryObservation]] = defaultdict(list)
    for observation in observations:
        by_authority_observations[observation.claim_authority].append(observation)

    current_by_authority: dict[str, frozenset[str] | None] = {}
    aggregate: set[str] = set()
    for authority, own_observations in by_authority_observations.items():
        superseded_ids = {
            o.supersedes_observation_id for o in own_observations if o.supersedes_observation_id
        }
        active = [o for o in own_observations if o.observation_id not in superseded_ids]

        authority_union: set[str] = set()
        has_positive = False
        for observation in active:
            if observation.assertion_kind == "VALUE_ASSERTION" and observation.values:
                authority_union |= observation.values
                has_positive = True
            # UNKNOWN (or a VALUE_ASSERTION with no values) contributes no
            # category and never erases another active observation's set.

        current_by_authority[authority] = frozenset(authority_union) if has_positive else None
        aggregate |= authority_union

    return _UseHistoryResolution(
        known_positive_uses=frozenset(aggregate), by_authority=current_by_authority
    )


def test_org_a_private_org_b_private_charter_is_not_a_conflict() -> None:
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation(
                "B-1", "ORG-B", "VALUE_ASSERTION", frozenset({"PRIVATE", "CHARTER"})
            ),
        ]
    )
    # No CONFLICT state exists in this resolver's return type at all -- the
    # absence of any conflict signal is itself the proof.
    assert resolution.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})
    assert resolution.by_authority == {
        "ORG-A": frozenset({"PRIVATE"}),
        "ORG-B": frozenset({"PRIVATE", "CHARTER"}),
    }


def test_org_a_private_org_b_charter_is_not_a_conflict_merely_because_sets_differ() -> None:
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation("B-1", "ORG-B", "VALUE_ASSERTION", frozenset({"CHARTER"})),
        ]
    )
    assert resolution.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})
    assert resolution.by_authority == {
        "ORG-A": frozenset({"PRIVATE"}),
        "ORG-B": frozenset({"CHARTER"}),
    }


def test_same_categories_in_different_declaration_order_are_the_same_claim() -> None:
    resolution_a_first = _resolve_broad_use_history(
        [
            _UseHistoryObservation(
                "A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"CHARTER", "PRIVATE"})
            ),
        ]
    )
    resolution_b_first = _resolve_broad_use_history(
        [
            _UseHistoryObservation(
                "A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE", "CHARTER"})
            ),
        ]
    )
    assert resolution_a_first == resolution_b_first
    assert resolution_a_first.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})


def test_unknown_source_does_not_erase_a_positive_source_declaration() -> None:
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "UNKNOWN", None),
            _UseHistoryObservation("B-1", "ORG-B", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
        ]
    )
    assert resolution.known_positive_uses == frozenset({"PRIVATE"})
    assert resolution.by_authority == {"ORG-A": None, "ORG-B": frozenset({"PRIVATE"})}


def test_same_authority_explicit_supersession_replaces_that_authoritys_current_set() -> None:
    observations = [
        _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
        _UseHistoryObservation(
            "A-2",
            "ORG-A",
            "VALUE_ASSERTION",
            frozenset({"PRIVATE", "CHARTER"}),
            supersedes_observation_id="A-1",
        ),
    ]
    resolution = _resolve_broad_use_history(observations)
    assert resolution.by_authority == {"ORG-A": frozenset({"PRIVATE", "CHARTER"})}
    assert resolution.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})
    # The prior observation remains independently retained (audit/history),
    # not deleted or mutated by resolution.
    assert observations[0].values == frozenset({"PRIVATE"})


def test_same_authority_two_disjoint_positive_observations_without_supersession_union() -> None:
    # Required adversarial example 1: Org A #1 {PRIVATE}, Org A #2 {CHARTER},
    # no supersession -> Org A current positive set {PRIVATE, CHARTER}. Both
    # are simultaneously-true positive facts, not a contradiction.
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation("A-2", "ORG-A", "VALUE_ASSERTION", frozenset({"CHARTER"})),
        ]
    )
    assert resolution.by_authority == {"ORG-A": frozenset({"PRIVATE", "CHARTER"})}
    assert resolution.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})


def test_same_authority_overlapping_positive_observations_without_supersession_union() -> None:
    # Required adversarial example 2: Org A #1 {PRIVATE}, Org A #2
    # {PRIVATE, CHARTER}, no supersession -> {PRIVATE, CHARTER}; not
    # ambiguous, not conflict.
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation(
                "A-2", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE", "CHARTER"})
            ),
        ]
    )
    assert resolution.by_authority == {"ORG-A": frozenset({"PRIVATE", "CHARTER"})}
    assert resolution.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})


def test_same_authority_unknown_and_positive_both_active_retains_the_positive_claim() -> None:
    # Required adversarial example 3: Org A UNKNOWN, Org A {PRIVATE}, both
    # active -> {PRIVATE} retained (UNKNOWN never erases an active positive
    # observation from the same authority).
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "UNKNOWN", None),
            _UseHistoryObservation("A-2", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
        ]
    )
    assert resolution.by_authority == {"ORG-A": frozenset({"PRIVATE"})}
    assert resolution.known_positive_uses == frozenset({"PRIVATE"})


def test_same_authority_explicit_supersession_is_a_real_correction_not_an_automatic_union() -> None:
    # Required adversarial example 4: A-1 {PRIVATE}; A-2 {CHARTER} supersedes
    # A-1 -> current authority set is exactly {CHARTER}, reflecting the
    # explicit correction -- NOT {PRIVATE, CHARTER}, which would happen if
    # the superseded observation were incorrectly still unioned in.
    observations = [
        _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
        _UseHistoryObservation(
            "A-2",
            "ORG-A",
            "VALUE_ASSERTION",
            frozenset({"CHARTER"}),
            supersedes_observation_id="A-1",
        ),
    ]
    resolution = _resolve_broad_use_history(observations)
    assert resolution.by_authority == {"ORG-A": frozenset({"CHARTER"})}
    assert resolution.known_positive_uses == frozenset({"CHARTER"})
    # The superseded observation remains independently retained for
    # audit/history, not deleted or mutated by resolution.
    assert observations[0].values == frozenset({"PRIVATE"})


def test_cross_source_supersession_attempt_cannot_erase_another_authoritys_positive_claim() -> None:
    # Required adversarial example 5: Org B declares supersedes_observation_id
    # pointing at Org A's observation. Grouping is strictly per-authority, so
    # Org B's declaration has zero effect on Org A's active claim.
    resolution = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation(
                "B-1",
                "ORG-B",
                "VALUE_ASSERTION",
                frozenset({"CHARTER"}),
                supersedes_observation_id="A-1",
            ),
        ]
    )
    assert resolution.by_authority == {
        "ORG-A": frozenset({"PRIVATE"}),
        "ORG-B": frozenset({"CHARTER"}),
    }
    assert resolution.known_positive_uses == frozenset({"PRIVATE", "CHARTER"})


def test_the_union_is_presentation_convenience_not_a_stronger_verified_fact() -> None:
    # A category absent from the aggregate is not proven absent -- and the
    # aggregate never claims completeness. Demonstrated structurally: the
    # aggregate is derived only from what sources positively declared, with
    # per-authority provenance preserved separately in by_authority rather
    # than collapsed into the union.
    resolution = _resolve_broad_use_history(
        [_UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"}))]
    )
    assert "RACING" not in resolution.known_positive_uses
    assert resolution.by_authority["ORG-A"] == frozenset({"PRIVATE"})
    assert resolution.known_positive_uses is not resolution.by_authority["ORG-A"]


# ---------------------------------------------------------------------------
# Owner-inspection summary counts must derive from real registry data.
# ---------------------------------------------------------------------------


def test_delivery_phase_counts_sum_to_the_full_registry() -> None:
    counts = defaultdict(int)
    for entry in _FIELDS.values():
        counts[entry["delivery_phase"]] += 1
    assert sum(counts.values()) == 38
    assert counts["GATE_1_REQUIRED"] + counts["GATE_1_OPTIONAL"] + counts["LATER"] == 38
    assert counts["LATER"] == 4
