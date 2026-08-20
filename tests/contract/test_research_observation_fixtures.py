"""Contract tests for SLICE-0012 benchmark-derived JSON fixtures.

Validates the JSON fixtures under fixtures/research_observations/ against the
new SLICE-0012 schemas and exercises benchmark-derived cases.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hullq.contracts import ContractRegistry
from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    JsonPointer,
    NormalizedCandidate,
    ObservationApplicability,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    PromotionError,
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchObservation,
    promote_to_field_evidence,
)

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "specs"
FIXTURES = ROOT / "fixtures" / "research_observations"

_REGISTRY = ContractRegistry.from_directory(SPECS)


def _load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


# ---------------------------------------------------------------------------
# Benchmark fixture: Pearson 35 — 1979 applicability
# ---------------------------------------------------------------------------


def test_fixture_pearson35_validates_against_schema() -> None:
    fix = _load(FIXTURES / "valid" / "obs_pearson35_1979_applicability.json")
    _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json").validate(fix)


def test_fixture_pearson35_applicability_is_1979() -> None:
    fix = _load(FIXTURES / "valid" / "obs_pearson35_1979_applicability.json")
    assert isinstance(fix, dict)
    app = fix["applicability"]
    assert isinstance(app, dict)
    assert app["first_year"] == 1979
    assert app["last_year"] == 1979
    assert app["unknown_or_unbounded"] is False


def test_fixture_pearson35_has_nominal_claim() -> None:
    fix = _load(FIXTURES / "valid" / "obs_pearson35_1979_applicability.json")
    assert isinstance(fix, dict)
    assert fix["claim_semantics"] == "nominal_design_value"


# ---------------------------------------------------------------------------
# Benchmark fixture: J/105 — class rule constraint
# ---------------------------------------------------------------------------


def test_fixture_j105_class_rule_validates_against_schema() -> None:
    fix = _load(FIXTURES / "valid" / "obs_j105_class_rule.json")
    _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json").validate(fix)


def test_fixture_j105_claim_is_class_rule_not_nominal() -> None:
    fix = _load(FIXTURES / "valid" / "obs_j105_class_rule.json")
    assert isinstance(fix, dict)
    assert fix["claim_semantics"] == "class_rule_constraint"
    assert fix["claim_semantics"] != "nominal_design_value"


def test_fixture_j105_evidence_type_is_class_association() -> None:
    fix = _load(FIXTURES / "valid" / "obs_j105_class_rule.json")
    assert isinstance(fix, dict)
    assert fix["evidence_type"] == "class_or_owner_association"


# ---------------------------------------------------------------------------
# Benchmark fixture: Gemini 105Mc — operating state without DesignOption
# ---------------------------------------------------------------------------


def test_fixture_gemini_board_state_validates_against_schema() -> None:
    fix = _load(FIXTURES / "valid" / "obs_gemini105mc_board_state.json")
    _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json").validate(fix)


def test_fixture_gemini_board_state_claim_is_operating_state() -> None:
    fix = _load(FIXTURES / "valid" / "obs_gemini105mc_board_state.json")
    assert isinstance(fix, dict)
    assert fix["claim_semantics"] == "operating_state_value"


def test_fixture_gemini_board_state_has_state_hint_no_design_option() -> None:
    fix = _load(FIXTURES / "valid" / "obs_gemini105mc_board_state.json")
    assert isinstance(fix, dict)
    app = fix["applicability"]
    assert isinstance(app, dict)
    # B06-007: centerboard deployment state, not mast-down; no DesignOption ID invented
    assert app["operating_state_hint"] == "leeward_board_only_deployed"
    assert app["design_option_hints"] is None
    assert app["individual_hull_or_listing_ref"] is None


# ---------------------------------------------------------------------------
# Benchmark fixture: Bavaria 38 — broker individual hull
# ---------------------------------------------------------------------------


def test_fixture_broker_individual_hull_validates_against_schema() -> None:
    fix = _load(FIXTURES / "valid" / "obs_broker_individual_hull.json")
    _REGISTRY.validator_by_name("RESEARCH_OBSERVATION_SCHEMA.v0.1.json").validate(fix)


def test_fixture_broker_claim_is_individual_hull() -> None:
    fix = _load(FIXTURES / "valid" / "obs_broker_individual_hull.json")
    assert isinstance(fix, dict)
    assert fix["claim_semantics"] == "individual_hull_value"


def test_fixture_broker_has_individual_hull_ref() -> None:
    fix = _load(FIXTURES / "valid" / "obs_broker_individual_hull.json")
    assert isinstance(fix, dict)
    app = fix["applicability"]
    assert isinstance(app, dict)
    assert app["individual_hull_or_listing_ref"] == "LISTING-2024-DE-001"


# ---------------------------------------------------------------------------
# Benchmark fixture: Catalina 316 unresolved identity bundle
# ---------------------------------------------------------------------------


def test_fixture_bundle_unresolved_validates_against_schema() -> None:
    fix = _load(FIXTURES / "valid" / "bundle_unresolved_identity.json")
    _REGISTRY.validator_by_name("RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json").validate(fix)


def test_fixture_bundle_has_null_manufacturer() -> None:
    fix = _load(FIXTURES / "valid" / "bundle_unresolved_identity.json")
    assert isinstance(fix, dict)
    assert fix["research_target"]["manufacturer"] is None


def test_fixture_bundle_crosscheck_outcome_is_definition_difference() -> None:
    fix = _load(FIXTURES / "valid" / "bundle_unresolved_identity.json")
    assert isinstance(fix, dict)
    crosschecks = fix["reference_crosschecks"]
    assert len(crosschecks) == 1
    assert crosschecks[0]["outcome"] == "definition_or_basis_difference"


def test_fixture_bundle_has_no_promoted_evidence_yet() -> None:
    fix = _load(FIXTURES / "valid" / "bundle_unresolved_identity.json")
    assert isinstance(fix, dict)
    assert fix["promoted_evidence"] == []


# ---------------------------------------------------------------------------
# Runtime: explicit promotion of a pre-canonical observation
# ---------------------------------------------------------------------------


def _make_observation_from_fixture(path: Path) -> ResearchObservation:
    fix = _load(path)
    assert isinstance(fix, dict)
    raw_obs = fix["observation"]["raw"]
    app = fix["applicability"]
    hints_raw = app["design_option_hints"]
    hints = tuple(hints_raw) if hints_raw is not None else None
    intended_fp_str: object = fix.get("intended_field_pointer")
    intended_fp = JsonPointer(str(intended_fp_str)) if isinstance(intended_fp_str, str) else None
    intended_sk_str: object = fix.get("intended_subject_kind_hint")
    intended_sk = SubjectKind(str(intended_sk_str)) if isinstance(intended_sk_str, str) else None
    norm_cand_raw = fix["observation"].get("normalized_candidate")
    norm_cand = None
    if norm_cand_raw is not None:
        norm_cand = NormalizedCandidate(
            value=norm_cand_raw["value"],
            unit=norm_cand_raw["unit"],
            method_id=norm_cand_raw["method_id"],
            method_version=norm_cand_raw["method_version"],
        )
    prod = fix["producer"]
    rt = fix["research_target"]
    sl = fix["source_locator"]
    return ResearchObservation(
        observation_id=str(fix["observation_id"]),
        research_target=ResearchTarget(
            manufacturer=rt["manufacturer"],
            model=str(rt["model"]),
            first_built=rt["first_built"],
        ),
        source_id=str(fix["source_id"]),
        source_locator=SourceLocator(
            page=sl["page"],
            section=sl["section"],
            anchor=sl["anchor"],
            table=sl["table"],
            figure=sl["figure"],
            record_key=sl["record_key"],
        ),
        raw=RawObservation(
            kind=RawObservationKind(str(raw_obs["kind"])),
            value=raw_obs["value"],
            unit=raw_obs["unit"],
            excerpt=raw_obs["excerpt"],
        ),
        normalized_candidate=norm_cand,
        evidence_type=EvidenceType(str(fix["evidence_type"])),
        claim_semantics=ClaimSemantics(str(fix["claim_semantics"])),
        applicability=ObservationApplicability(
            first_year=app["first_year"],
            last_year=app["last_year"],
            hull_number_from=app["hull_number_from"],
            hull_number_to=app["hull_number_to"],
            market_or_region=app["market_or_region"],
            named_variant_hint=app["named_variant_hint"],
            design_option_hints=hints,
            operating_state_hint=app["operating_state_hint"],
            individual_hull_or_listing_ref=app["individual_hull_or_listing_ref"],
            unknown_or_unbounded=bool(app["unknown_or_unbounded"]),
        ),
        producer=ProducerMetadata(
            kind=ProducerKind(str(prod["kind"])),
            identifier=str(prod["identifier"]),
            version=prod["version"],
            model=prod["model"],
            prompt_or_rule_version=prod["prompt_or_rule_version"],
        ),
        research_context=ResearchContext(
            research_job_id=fix["research_context"]["research_job_id"],
            activity_id=fix["research_context"]["activity_id"],
        ),
        observed_at=str(fix["observed_at"]),
        confidence=ConfidenceLevel(str(fix["confidence"])),
        supersedes_observation_id=fix["supersedes_observation_id"],
        intended_subject_kind_hint=intended_sk,
        intended_field_pointer=intended_fp,
        notes=fix["notes"],
    )


def test_promote_pearson35_observation_to_field_evidence() -> None:
    obs = _make_observation_from_fixture(
        FIXTURES / "valid" / "obs_pearson35_1979_applicability.json"
    )
    subject = ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="BD-PEARSON35-001")
    v3 = promote_to_field_evidence(obs, subject, "EVID-PEARSON35-LOA-001", JsonPointer("/loa_m"))
    assert v3.evidence_id == "EVID-PEARSON35-LOA-001"
    assert v3.subject == subject
    assert v3.claim_semantics == ClaimSemantics.NOMINAL_DESIGN_VALUE
    assert v3.applicability.first_year == 1979
    assert v3.applicability.last_year == 1979
    assert v3.raw.value == "35'0\""


def test_promote_fails_on_wrong_field_pointer() -> None:
    obs = _make_observation_from_fixture(
        FIXTURES / "valid" / "obs_pearson35_1979_applicability.json"
    )
    subject = ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="BD-PEARSON35-001")
    with pytest.raises(PromotionError, match="intended_field_pointer"):
        promote_to_field_evidence(obs, subject, "EVID-001", JsonPointer("/displacement_kg"))


def test_promote_fails_on_wrong_subject_kind() -> None:
    obs = _make_observation_from_fixture(
        FIXTURES / "valid" / "obs_pearson35_1979_applicability.json"
    )
    wrong_subject = ProvenanceSubject(kind=SubjectKind.BRAND, id="BRAND-001")
    with pytest.raises(PromotionError, match="intended_subject_kind_hint"):
        promote_to_field_evidence(obs, wrong_subject, "EVID-001", JsonPointer("/loa_m"))


# ---------------------------------------------------------------------------
# Reference crosscheck structurally outside evidence provenance
# ---------------------------------------------------------------------------


def test_bundle_crosscheck_has_no_evidence_id_field() -> None:
    cc = ReferenceCrosscheck(
        crosscheck_id="CC-SAILBOATDATA",
        reference_source_id="sailboatdata-reference",
        topic_or_field="/loa_m",
        outcome=ReferenceCheckOutcome.MATCH,
        notes=None,
    )
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(ReferenceCrosscheck)}
    assert "evidence_id" not in field_names
    assert "observation_id" not in field_names
    assert cc.crosscheck_id == "CC-SAILBOATDATA"
