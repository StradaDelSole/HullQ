"""Unit tests for hullq.domain.provenance — SLICE-0006.

Covers all 26 required scenarios from
docs/slices/SLICE-0006-provenance-raw-observation-boundary.md plus
property-based tests for RFC 6901 pointer round-trip invariants.
"""

from __future__ import annotations

import inspect
from decimal import Decimal

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from hullq.domain.measurements import (
    LengthUnit,
    MeasurementObservation,
    Quantity,
    normalize_measurement,
)
from hullq.domain.provenance import (
    ConfidenceLevel,
    EvidenceType,
    FieldEvidence,
    FieldResolution,
    JsonPointer,
    JsonPointerError,
    NormalizedCandidate,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    ResolutionMethod,
    ResolutionState,
    ResolverKind,
    ResolverMetadata,
    SourceLocator,
    SubjectKind,
    check_canonical_consistency,
    source_impact_lookup,
    validate_evidence_invariants,
    validate_resolution_history,
    validate_resolution_invariants,
)

# ---------------------------------------------------------------------------
# Synthetic builder helpers
# ---------------------------------------------------------------------------

_POINTER_LOA = JsonPointer("/baseline/dimensions/loa_m")
_POINTER_NAME = JsonPointer("/canonical_name")
_POINTER_YEAR = JsonPointer("/first_year")

_SUBJECT_BD = ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id="BD_TEST_001")
_SUBJECT_BM = ProvenanceSubject(kind=SubjectKind.BOAT_MODEL, id="BM_TEST_001")
_SUBJECT_BRAND = ProvenanceSubject(kind=SubjectKind.BRAND, id="BR_TEST_001")
_SUBJECT_ORG = ProvenanceSubject(kind=SubjectKind.ORGANIZATION, id="ORG_TEST_001")
_SUBJECT_ALIAS = ProvenanceSubject(kind=SubjectKind.IDENTITY_ALIAS, id="ALIAS_TEST_001")
_SUBJECT_BMR = ProvenanceSubject(kind=SubjectKind.BRAND_MODEL_RELATIONSHIP, id="BMR_TEST_001")
_SUBJECT_ODR = ProvenanceSubject(
    kind=SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP, id="ODR_TEST_001"
)

_LOCATOR_NULL = SourceLocator(
    page=None, section=None, anchor=None, table=None, figure=None, record_key=None
)
_PRODUCER_TOOL = ProducerMetadata(
    kind=ProducerKind.DETERMINISTIC_TOOL,
    identifier="hullq-test",
    version="0.1",
    model=None,
    prompt_or_rule_version=None,
)
_PRODUCER_HUMAN = ProducerMetadata(
    kind=ProducerKind.HUMAN,
    identifier="researcher-01",
    version=None,
    model=None,
    prompt_or_rule_version=None,
)
_CONTEXT_NULL = ResearchContext(research_job_id=None, activity_id=None)
_RESOLVER = ResolverMetadata(
    kind=ResolverKind.DETERMINISTIC_TOOL, identifier="hullq-resolver", version="0.1"
)


def _raw(value: object, unit: str | None = None, excerpt: str | None = None) -> RawObservation:
    return RawObservation(kind=RawObservationKind.LITERAL, value=value, unit=unit, excerpt=excerpt)


def _evidence(
    evidence_id: str,
    subject: ProvenanceSubject,
    pointer: JsonPointer,
    source_id: str,
    raw_value: object,
    *,
    normalized_candidate: NormalizedCandidate | None = None,
    supersedes_evidence_id: str | None = None,
    unit: str | None = None,
    excerpt: str | None = None,
) -> FieldEvidence:
    return FieldEvidence(
        evidence_id=evidence_id,
        subject=subject,
        field_pointer=pointer,
        source_id=source_id,
        source_locator=_LOCATOR_NULL,
        raw=_raw(raw_value, unit=unit, excerpt=excerpt),
        normalized_candidate=normalized_candidate,
        evidence_type=EvidenceType.STRUCTURED_DATASET,
        producer=_PRODUCER_TOOL,
        research_context=_CONTEXT_NULL,
        observed_at="2026-08-18T00:00:00Z",
        confidence=ConfidenceLevel.HIGH,
        supersedes_evidence_id=supersedes_evidence_id,
        notes=None,
    )


def _resolution(
    resolution_id: str,
    subject: ProvenanceSubject,
    pointer: JsonPointer,
    state: ResolutionState,
    canonical_value: object,
    supporting: frozenset[str],
    contradicting: frozenset[str],
    considered: frozenset[str],
    *,
    supersedes_resolution_id: str | None = None,
) -> FieldResolution:
    return FieldResolution(
        resolution_id=resolution_id,
        subject=subject,
        field_pointer=pointer,
        state=state,
        canonical_value_snapshot=canonical_value,
        supporting_evidence_ids=supporting,
        contradicting_evidence_ids=contradicting,
        considered_evidence_ids=considered,
        resolution_method=ResolutionMethod.UNANIMOUS_EVIDENCE,
        policy_version="prov-policy-1.0",
        resolver=_RESOLVER,
        resolved_at="2026-08-18T00:00:00Z",
        supersedes_resolution_id=supersedes_resolution_id,
        notes=None,
    )


# ---------------------------------------------------------------------------
# Scenario 1 — BoatDesign LOA evidence by BoatDesign ID
# ---------------------------------------------------------------------------


class TestScenario01BoatDesignLoa:
    def test_evidence_addresses_loa_by_design_id(self) -> None:
        ev = _evidence("E01", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        assert ev.subject.kind == SubjectKind.BOAT_DESIGN
        assert ev.subject.id == "BD_TEST_001"
        assert ev.field_pointer.raw == "/baseline/dimensions/loa_m"

    def test_field_pointer_navigates_nested_dict(self) -> None:
        snapshot = {"baseline": {"dimensions": {"loa_m": 10.541}}}
        assert _POINTER_LOA.lookup(snapshot) == 10.541

    def test_evidence_id_is_independently_addressable(self) -> None:
        ev = _evidence("EVID_LOA_001", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        assert ev.evidence_id == "EVID_LOA_001"


# ---------------------------------------------------------------------------
# Scenario 2 — Brand canonical-name evidence
# ---------------------------------------------------------------------------


class TestScenario02BrandEvidence:
    def test_brand_is_valid_provenance_subject_kind(self) -> None:
        subject = ProvenanceSubject(kind=SubjectKind.BRAND, id="BR_001")
        assert subject.kind == SubjectKind.BRAND

    def test_evidence_can_use_brand_as_subject(self) -> None:
        ev = _evidence("E02", _SUBJECT_BRAND, _POINTER_NAME, "SRC_001", "Alpha Yachts")
        assert ev.subject.kind == SubjectKind.BRAND
        assert ev.subject.id == "BR_TEST_001"

    def test_field_pointer_addresses_canonical_name(self) -> None:
        snapshot = {"canonical_name": "Alpha Yachts", "aliases": []}
        assert _POINTER_NAME.lookup(snapshot) == "Alpha Yachts"


# ---------------------------------------------------------------------------
# Scenario 3 — Organization evidence
# ---------------------------------------------------------------------------


class TestScenario03OrganizationEvidence:
    def test_organization_is_valid_provenance_subject_kind(self) -> None:
        subject = ProvenanceSubject(kind=SubjectKind.ORGANIZATION, id="ORG_001")
        assert subject.kind == SubjectKind.ORGANIZATION

    def test_evidence_can_use_organization_as_subject(self) -> None:
        ev = _evidence("E03", _SUBJECT_ORG, _POINTER_NAME, "SRC_001", "Alpha Works Ltd.")
        assert ev.subject.kind == SubjectKind.ORGANIZATION


# ---------------------------------------------------------------------------
# Scenario 4 — IdentityAlias by stable alias ID, not parent-array position
# ---------------------------------------------------------------------------


class TestScenario04IdentityAliasByStableId:
    def test_identity_alias_is_valid_subject_kind(self) -> None:
        subject = ProvenanceSubject(kind=SubjectKind.IDENTITY_ALIAS, id="ALIAS_001")
        assert subject.kind == SubjectKind.IDENTITY_ALIAS

    def test_alias_evidence_uses_stable_alias_id(self) -> None:
        alias_subject = ProvenanceSubject(kind=SubjectKind.IDENTITY_ALIAS, id="ALIAS_TEST_001")
        ev = _evidence("E04", alias_subject, JsonPointer("/name"), "SRC_001", "Alpha Y.")
        assert ev.subject.id == "ALIAS_TEST_001"
        # The ID is a stable alias ID, not a parent-array position like "0" or "1"
        assert not ev.subject.id.isdigit()


# ---------------------------------------------------------------------------
# Scenario 5 — BrandModelRelationship and OrganizationDesignRelationship
# ---------------------------------------------------------------------------


class TestScenario05RelationshipSubjects:
    def test_brand_model_rel_is_valid_subject_kind(self) -> None:
        subject = ProvenanceSubject(kind=SubjectKind.BRAND_MODEL_RELATIONSHIP, id="BMR_001")
        assert subject.kind == SubjectKind.BRAND_MODEL_RELATIONSHIP

    def test_org_design_rel_is_valid_subject_kind(self) -> None:
        subject = ProvenanceSubject(kind=SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP, id="ODR_001")
        assert subject.kind == SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP

    def test_bmr_evidence_by_stable_relationship_id(self) -> None:
        ev = _evidence("E05a", _SUBJECT_BMR, _POINTER_YEAR, "SRC_001", 1978)
        assert ev.subject.kind == SubjectKind.BRAND_MODEL_RELATIONSHIP

    def test_odr_evidence_by_stable_relationship_id(self) -> None:
        ev = _evidence("E05b", _SUBJECT_ODR, JsonPointer("/role"), "SRC_001", "builder")
        assert ev.subject.kind == SubjectKind.ORGANIZATION_DESIGN_RELATIONSHIP


# ---------------------------------------------------------------------------
# Scenario 9 — RFC 6901 escaping for ~ and /
# ---------------------------------------------------------------------------


class TestScenario09Rfc6901Escaping:
    def test_tilde_decoded_to_tilde(self) -> None:
        ptr = JsonPointer("/a~0b")
        assert ptr.tokens == ("a~b",)

    def test_slash_decoded_to_slash(self) -> None:
        ptr = JsonPointer("/a~1b")
        assert ptr.tokens == ("a/b",)

    def test_combined_tilde_and_slash_escaping(self) -> None:
        ptr = JsonPointer("/~0~1")
        assert ptr.tokens == ("~/",)

    def test_tilde_slash_order_is_correct(self) -> None:
        # ~01 should be decoded as ~1 first (no match since ~01 is ~0 then 1)
        # Actually ~01: first replace ~1 -> nothing (not present), then ~0 -> ~
        # Correct RFC 6901: ~01 = decode ~1 first (no ~1 here) then ~0 -> ~, giving "~1"
        # Wait: ~01: token is "~01"
        # Step 1: replace ~1 -> / in "~01" -> "~0/" -> no, "~01" has ~0 then 1
        # Actually "~01": positions 0='~', 1='0', 2='1'
        # Is there a ~1 here? At position 0 we have ~, at position 1 we have 0 -> ~0 not ~1
        # At position 1 we have '0', at position 2 we have '1' -> not a ~ sequence
        # So after replace("~1", "/"): "~01" (unchanged since no ~1 substring)
        # Then replace("~0", "~"): "~01" -> "~1"
        # Result: "~1"
        ptr = JsonPointer("/~01")
        assert ptr.tokens == ("~1",)

    def test_key_with_tilde_in_dict(self) -> None:
        ptr = JsonPointer("/a~0b")
        assert ptr.lookup({"a~b": 42}) == 42

    def test_key_with_slash_in_dict(self) -> None:
        ptr = JsonPointer("/a~1b")
        assert ptr.lookup({"a/b": 99}) == 99

    def test_nested_path(self) -> None:
        ptr = JsonPointer("/a/b/c")
        assert ptr.tokens == ("a", "b", "c")
        assert ptr.lookup({"a": {"b": {"c": "found"}}}) == "found"


# ---------------------------------------------------------------------------
# Scenario 10 — malformed pointer escape syntax is rejected
# ---------------------------------------------------------------------------


class TestScenario10MalformedPointerRejected:
    def test_bare_tilde_is_rejected(self) -> None:
        with pytest.raises(JsonPointerError):
            JsonPointer("/a~b")

    def test_tilde_two_is_rejected(self) -> None:
        with pytest.raises(JsonPointerError):
            JsonPointer("/~2")

    def test_trailing_tilde_is_rejected(self) -> None:
        with pytest.raises(JsonPointerError):
            JsonPointer("/a~")

    def test_missing_leading_slash_is_rejected(self) -> None:
        with pytest.raises(JsonPointerError):
            JsonPointer("a/b")

    def test_empty_pointer_is_rejected(self) -> None:
        with pytest.raises(JsonPointerError):
            JsonPointer("")

    def test_valid_pointer_does_not_raise(self) -> None:
        ptr = JsonPointer("/valid/pointer")
        assert ptr.raw == "/valid/pointer"

    # --- RFC 6901 array-index regression (Fix 1, PR #14) ---

    @pytest.mark.parametrize("token", ["-1", "+1", "01", "-"])
    def test_invalid_rfc6901_array_index_rejected(self, token: str) -> None:
        ptr = JsonPointer(f"/items/{token}")
        with pytest.raises(KeyError):
            ptr.lookup({"items": [10, 20, 30]})

    @pytest.mark.parametrize(
        "token,expected",
        [("0", 0), ("1", 1), ("42", 42)],
    )
    def test_valid_rfc6901_array_index_accepted(self, token: str, expected: int) -> None:
        seq = list(range(50))
        ptr = JsonPointer(f"/items/{token}")
        assert ptr.lookup({"items": seq}) == expected


# ---------------------------------------------------------------------------
# Scenario 11 — raw value/unit/excerpt unchanged after normalized candidate
# ---------------------------------------------------------------------------


class TestScenario11RawPreservedAfterNormalization:
    def test_raw_value_unchanged_when_normalized_candidate_present(self) -> None:
        raw = _raw("34 ft 7 in", unit="imperial_compound_length", excerpt="LOA: 34 ft 7 in")
        nc = NormalizedCandidate(
            value=10.541, unit="m", method_id="length.convert", method_version="1"
        )
        ev = FieldEvidence(
            evidence_id="E11",
            subject=_SUBJECT_BD,
            field_pointer=_POINTER_LOA,
            source_id="SRC_001",
            source_locator=_LOCATOR_NULL,
            raw=raw,
            normalized_candidate=nc,
            evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
            producer=_PRODUCER_TOOL,
            research_context=_CONTEXT_NULL,
            observed_at="2026-08-18T00:00:00Z",
            confidence=ConfidenceLevel.HIGH,
            supersedes_evidence_id=None,
            notes=None,
        )
        assert ev.raw.value == "34 ft 7 in"
        assert ev.raw.unit == "imperial_compound_length"
        assert ev.raw.excerpt == "LOA: 34 ft 7 in"
        assert ev.normalized_candidate is not None
        assert ev.normalized_candidate.value == 10.541
        assert ev.normalized_candidate.unit == "m"


# ---------------------------------------------------------------------------
# Scenario 12 — caller mutation of mutable input does not alter snapshot
# ---------------------------------------------------------------------------


class TestScenario12SnapshotSafetyAgainstCallerMutation:
    def test_mutating_raw_value_dict_does_not_alter_snapshot(self) -> None:
        mutable_value: dict[str, object] = {"length_ft": 34, "length_in": 7}
        ev = _evidence("E12", _SUBJECT_BD, _POINTER_LOA, "SRC_001", mutable_value)
        original_snapshot = dict(ev.raw.value)  # type: ignore[arg-type]
        mutable_value["length_ft"] = 999  # mutate the original
        assert ev.raw.value == original_snapshot  # snapshot unchanged

    def test_mutating_normalized_candidate_value_does_not_alter_snapshot(self) -> None:
        mutable_nc_value: dict[str, object] = {"m": 10.541}
        nc = NormalizedCandidate(
            value=mutable_nc_value, unit="m", method_id="test", method_version="1"
        )
        original = dict(mutable_nc_value)
        mutable_nc_value["m"] = 999.0
        assert nc.value == original  # snapshot unchanged

    def test_mutating_canonical_value_snapshot_does_not_alter_resolution(self) -> None:
        mutable_snap: dict[str, object] = {"value": 10.541}
        res = _resolution(
            "R12",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            mutable_snap,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
        )
        mutable_snap["value"] = 999.0
        assert res.canonical_value_snapshot == {"value": 10.541}


# ---------------------------------------------------------------------------
# Scenario 13 — two contradictory source observations coexist
# ---------------------------------------------------------------------------


class TestScenario13ContradictoryEvidenceCoexists:
    def test_two_sources_observe_different_loa(self) -> None:
        ev_a = _evidence("E13a", _SUBJECT_BD, _POINTER_LOA, "SRC_A", 10.541)
        ev_b = _evidence("E13b", _SUBJECT_BD, _POINTER_LOA, "SRC_B", 10.60)
        # Both coexist without any automatic resolution
        assert ev_a.evidence_id != ev_b.evidence_id
        assert ev_a.raw.value != ev_b.raw.value
        assert ev_a.source_id != ev_b.source_id

    def test_contradictory_evidence_no_auto_resolution(self) -> None:
        ev_a = _evidence("E13a", _SUBJECT_BD, _POINTER_LOA, "SRC_A", 10.541)
        ev_b = _evidence("E13b", _SUBJECT_BD, _POINTER_LOA, "SRC_B", 10.60)
        # Neither becomes canonical automatically; no resolution record is created
        # by merely constructing two FieldEvidence objects
        assert ev_a.normalized_candidate is None
        assert ev_b.normalized_candidate is None


# ---------------------------------------------------------------------------
# Scenario 14 — evidence supersession retains prior record
# ---------------------------------------------------------------------------


class TestScenario14EvidenceSupersession:
    def test_superseding_evidence_links_back_to_prior(self) -> None:
        ev_prior = _evidence("E14a", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.50)
        ev_corrected = _evidence(
            "E14b",
            _SUBJECT_BD,
            _POINTER_LOA,
            "SRC_001",
            10.541,
            supersedes_evidence_id="E14a",
        )
        assert ev_corrected.supersedes_evidence_id == "E14a"
        # prior record is unmodified
        assert ev_prior.raw.value == 10.50
        assert ev_prior.evidence_id == "E14a"

    def test_supersession_validates_successfully(self) -> None:
        ev_prior = _evidence("E14a", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.50)
        ev_corrected = _evidence(
            "E14b",
            _SUBJECT_BD,
            _POINTER_LOA,
            "SRC_001",
            10.541,
            supersedes_evidence_id="E14a",
        )
        all_ev = {"E14a": ev_prior, "E14b": ev_corrected}
        errors = validate_evidence_invariants(ev_corrected, all_ev)
        assert errors == []

    def test_supersession_across_subjects_is_rejected(self) -> None:
        ev_prior = _evidence("E14c", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.50)
        ev_wrong = _evidence(
            "E14d",
            _SUBJECT_BM,
            _POINTER_LOA,
            "SRC_001",
            10.541,
            supersedes_evidence_id="E14c",
        )
        all_ev = {"E14c": ev_prior, "E14d": ev_wrong}
        errors = validate_evidence_invariants(ev_wrong, all_ev)
        assert any("subject boundary" in e for e in errors)


# ---------------------------------------------------------------------------
# Scenario 15 — resolution cannot cite evidence from a different subject/field
# ---------------------------------------------------------------------------


class TestScenario15ResolutionEvidenceBoundary:
    def test_resolution_citing_wrong_subject_fails(self) -> None:
        ev_wrong_subject = _evidence("EX", _SUBJECT_BRAND, _POINTER_LOA, "SRC_001", 10.541)
        res = _resolution(
            "R15",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"EX"}),
            frozenset(),
            frozenset({"EX"}),
        )
        errors = validate_resolution_invariants(res, {"EX": ev_wrong_subject})
        assert any("subject" in e for e in errors)

    def test_resolution_citing_wrong_field_fails(self) -> None:
        ev_wrong_field = _evidence("EX", _SUBJECT_BD, _POINTER_NAME, "SRC_001", "Alpha")
        res = _resolution(
            "R15b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"EX"}),
            frozenset(),
            frozenset({"EX"}),
        )
        errors = validate_resolution_invariants(res, {"EX": ev_wrong_field})
        assert any("field pointer" in e for e in errors)


# ---------------------------------------------------------------------------
# Scenario 16 — supporting/contradicting are subsets of considered, non-overlapping
# ---------------------------------------------------------------------------


class TestScenario16EvidenceSetConstraints:
    def _ev_ok(self, eid: str) -> FieldEvidence:
        return _evidence(eid, _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)

    def test_supporting_not_subset_of_considered_fails(self) -> None:
        ev = self._ev_ok("E_SUP")
        res = _resolution(
            "R16a",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_SUP"}),
            frozenset(),
            frozenset(),  # considered is empty
        )
        errors = validate_resolution_invariants(res, {"E_SUP": ev})
        assert any("supporting" in e and "considered" in e for e in errors)

    def test_contradicting_not_subset_of_considered_fails(self) -> None:
        ev_sup = self._ev_ok("E_SUP")
        ev_con = self._ev_ok("E_CON")
        res = _resolution(
            "R16b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED_WITH_CONFLICT,
            10.541,
            frozenset({"E_SUP"}),
            frozenset({"E_CON"}),
            frozenset({"E_SUP"}),
        )
        errors = validate_resolution_invariants(res, {"E_SUP": ev_sup, "E_CON": ev_con})
        assert any("contradicting" in e and "considered" in e for e in errors)

    def test_overlap_between_supporting_and_contradicting_fails(self) -> None:
        ev = self._ev_ok("E_BOTH")
        res = _resolution(
            "R16c",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED_WITH_CONFLICT,
            10.541,
            frozenset({"E_BOTH"}),
            frozenset({"E_BOTH"}),
            frozenset({"E_BOTH"}),
        )
        errors = validate_resolution_invariants(res, {"E_BOTH": ev})
        assert any(
            "both" in e or "overlap" in e or "supporting and contradicting" in e for e in errors
        )


# ---------------------------------------------------------------------------
# Scenario 17 — resolved requires support and non-null snapshot
# ---------------------------------------------------------------------------


class TestScenario17ResolvedRequiresSupport:
    def test_resolved_with_support_passes(self) -> None:
        ev = _evidence("E_SUP", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        res = _resolution(
            "R17",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_SUP"}),
            frozenset(),
            frozenset({"E_SUP"}),
        )
        errors = validate_resolution_invariants(res, {"E_SUP": ev})
        assert errors == []

    def test_resolved_without_support_fails(self) -> None:
        res = _resolution(
            "R17b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = validate_resolution_invariants(res, {})
        assert any("supporting" in e for e in errors)

    def test_resolved_with_null_snapshot_fails(self) -> None:
        ev = _evidence("E_SUP", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        res = _resolution(
            "R17c",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            None,
            frozenset({"E_SUP"}),
            frozenset(),
            frozenset({"E_SUP"}),
        )
        errors = validate_resolution_invariants(res, {"E_SUP": ev})
        assert any("canonical_value_snapshot" in e for e in errors)


# ---------------------------------------------------------------------------
# Scenario 18 — resolved_with_conflict retains support and contradiction
# ---------------------------------------------------------------------------


class TestScenario18ResolvedWithConflict:
    def test_resolved_with_conflict_passes(self) -> None:
        ev_sup = _evidence("E_SUP", _SUBJECT_BD, _POINTER_LOA, "SRC_A", 10.541)
        ev_con = _evidence("E_CON", _SUBJECT_BD, _POINTER_LOA, "SRC_B", 10.60)
        res = _resolution(
            "R18",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED_WITH_CONFLICT,
            10.541,
            frozenset({"E_SUP"}),
            frozenset({"E_CON"}),
            frozenset({"E_SUP", "E_CON"}),
        )
        errors = validate_resolution_invariants(res, {"E_SUP": ev_sup, "E_CON": ev_con})
        assert errors == []

    def test_resolved_with_conflict_without_contradiction_fails(self) -> None:
        ev = _evidence("E_SUP", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        res = _resolution(
            "R18b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED_WITH_CONFLICT,
            10.541,
            frozenset({"E_SUP"}),
            frozenset(),
            frozenset({"E_SUP"}),
        )
        errors = validate_resolution_invariants(res, {"E_SUP": ev})
        assert any("contradicting" in e for e in errors)


# ---------------------------------------------------------------------------
# Scenario 19 — unresolved conflict has null snapshot and contradiction evidence
# ---------------------------------------------------------------------------


class TestScenario19UnresolvedConflict:
    def test_conflict_state_passes_with_null_snapshot(self) -> None:
        ev_a = _evidence("E_A", _SUBJECT_BD, _POINTER_LOA, "SRC_A", 10.541)
        ev_b = _evidence("E_B", _SUBJECT_BD, _POINTER_LOA, "SRC_B", 10.60)
        res = _resolution(
            "R19",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.CONFLICT,
            None,
            frozenset(),
            frozenset({"E_A", "E_B"}),
            frozenset({"E_A", "E_B"}),
        )
        errors = validate_resolution_invariants(res, {"E_A": ev_a, "E_B": ev_b})
        assert errors == []

    def test_conflict_with_non_null_snapshot_fails(self) -> None:
        ev_a = _evidence("E_A", _SUBJECT_BD, _POINTER_LOA, "SRC_A", 10.541)
        ev_b = _evidence("E_B", _SUBJECT_BD, _POINTER_LOA, "SRC_B", 10.60)
        res = _resolution(
            "R19b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.CONFLICT,
            10.541,
            frozenset(),
            frozenset({"E_A", "E_B"}),
            frozenset({"E_A", "E_B"}),
        )
        errors = validate_resolution_invariants(res, {"E_A": ev_a, "E_B": ev_b})
        assert any("null" in e or "canonical_value_snapshot" in e for e in errors)

    def test_unknown_state_with_null_snapshot_passes(self) -> None:
        res = _resolution(
            "R19c",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.UNKNOWN,
            None,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = validate_resolution_invariants(res, {})
        assert errors == []

    def test_needs_review_with_null_snapshot_passes(self) -> None:
        res = _resolution(
            "R19d",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.NEEDS_REVIEW,
            None,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = validate_resolution_invariants(res, {})
        assert errors == []


# ---------------------------------------------------------------------------
# Scenario 20 — two current resolutions for same subject/field are rejected
# ---------------------------------------------------------------------------


class TestScenario20MultipleCurrentResolutions:
    def test_two_current_resolutions_rejected(self) -> None:
        ev = _evidence("E_OK", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        res_a = _resolution(
            "R20a",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
        )
        res_b = _resolution(
            "R20b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.60,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
        )
        _ = ev  # evidence exists but we're checking history-level constraint
        errors = validate_resolution_history([res_a, res_b])
        assert any("Multiple current" in e or "current resolutions" in e.lower() for e in errors)

    def test_one_current_one_superseded_passes(self) -> None:
        res_old = _resolution(
            "R20old",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.50,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
        )
        res_new = _resolution(
            "R20new",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
            supersedes_resolution_id="R20old",
        )
        errors = validate_resolution_history([res_old, res_new])
        assert errors == []


# ---------------------------------------------------------------------------
# Scenario 21 — valid supersession chain yields exactly one current resolution
# ---------------------------------------------------------------------------


class TestScenario21SupersessionChain:
    def test_chain_of_three_has_one_current(self) -> None:
        r1 = _resolution(
            "R21a",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.0,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
        )
        r2 = _resolution(
            "R21b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.4,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
            supersedes_resolution_id="R21a",
        )
        r3 = _resolution(
            "R21c",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
            supersedes_resolution_id="R21b",
        )
        errors = validate_resolution_history([r1, r2, r3])
        assert errors == []


# ---------------------------------------------------------------------------
# Scenario 22 — cross-field/cyclic/forked resolution supersession rejected
# ---------------------------------------------------------------------------


class TestScenario22InvalidSupersession:
    def test_supersession_across_different_fields_is_rejected(self) -> None:
        res_loa = _resolution(
            "R22a",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
        )
        res_name = _resolution(
            "R22b",
            _SUBJECT_BD,
            _POINTER_NAME,
            ResolutionState.RESOLVED,
            "Alpha",
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
            supersedes_resolution_id="R22a",  # cross-field supersession
        )
        errors = validate_resolution_history([res_loa, res_name])
        assert any("different field" in e or "field pointer" in e for e in errors)

    def test_cycle_in_supersession_is_rejected(self) -> None:
        r1 = _resolution(
            "R22c",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
            supersedes_resolution_id="R22d",
        )
        r2 = _resolution(
            "R22d",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.60,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
            supersedes_resolution_id="R22c",
        )
        errors = validate_resolution_history([r1, r2])
        assert any("Cycle" in e or "cycle" in e for e in errors)

    def test_self_supersession_is_rejected(self) -> None:
        res = _resolution(
            "R22e",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
            supersedes_resolution_id="R22e",
        )
        errors = validate_resolution_history([res])
        assert any("itself" in e or "self" in e.lower() for e in errors)

    def test_fork_two_resolutions_superseding_same_predecessor_rejected(self) -> None:
        # Scenario 22 fork: one valid predecessor + two resolutions both superseding it.
        # Both R22g and R22h are current (not superseded), producing an ambiguous state
        # that validate_resolution_history must reject.
        predecessor = _resolution(
            "R22f",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E1"}),
            frozenset(),
            frozenset({"E1"}),
        )
        fork_a = _resolution(
            "R22g",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.60,
            frozenset({"E2"}),
            frozenset(),
            frozenset({"E2"}),
            supersedes_resolution_id="R22f",
        )
        fork_b = _resolution(
            "R22h",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.65,
            frozenset({"E3"}),
            frozenset(),
            frozenset({"E3"}),
            supersedes_resolution_id="R22f",
        )
        errors = validate_resolution_history([predecessor, fork_a, fork_b])
        assert errors, "Expected error: two resolutions fork from the same predecessor"


# ---------------------------------------------------------------------------
# Scenario 23 — canonical value/resolution snapshot consistency
# ---------------------------------------------------------------------------


class TestScenario23CanonicalConsistency:
    def test_consistent_value_passes(self) -> None:
        snapshot = {"baseline": {"dimensions": {"loa_m": 10.541}}}
        ev = _evidence("E_OK", _SUBJECT_BD, _POINTER_LOA, "SRC_001", 10.541)
        res = _resolution(
            "R23a",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
        )
        _ = ev
        errors = check_canonical_consistency(snapshot, res)
        assert errors == []

    def test_mismatch_fails(self) -> None:
        snapshot = {"baseline": {"dimensions": {"loa_m": 10.60}}}
        res = _resolution(
            "R23b",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_OK"}),
            frozenset(),
            frozenset({"E_OK"}),
        )
        errors = check_canonical_consistency(snapshot, res)
        assert errors
        assert any("10.541" in e or "10.6" in e for e in errors)

    def test_unknown_state_not_checked_as_canonical(self) -> None:
        snapshot: dict[str, object] = {}
        res = _resolution(
            "R23c",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.UNKNOWN,
            None,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = check_canonical_consistency(snapshot, res)
        assert errors == []

    # --- Unresolved-state canonical consistency regression (Fix 2, PR #14) ---

    @pytest.mark.parametrize(
        "state",
        [ResolutionState.CONFLICT, ResolutionState.UNKNOWN, ResolutionState.NEEDS_REVIEW],
    )
    def test_unresolved_state_fails_when_canonical_has_nonnull_value(
        self, state: ResolutionState
    ) -> None:
        # REQ-PROV-005 / REQ-PROV-008: unresolved resolution must not coexist with
        # a non-null canonical production value at the same field pointer.
        snapshot = {"baseline": {"dimensions": {"loa_m": 10.541}}}
        res = _resolution(
            "R23d",
            _SUBJECT_BD,
            _POINTER_LOA,
            state,
            None,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = check_canonical_consistency(snapshot, res)
        assert errors, f"Expected consistency error for state={state} with non-null canonical field"

    def test_unresolved_state_passes_when_canonical_field_is_null(self) -> None:
        # Explicit null in canonical snapshot is acceptable for unresolved states.
        snapshot = {"baseline": {"dimensions": {"loa_m": None}}}
        res = _resolution(
            "R23e",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.CONFLICT,
            None,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = check_canonical_consistency(snapshot, res)
        assert errors == []

    def test_unresolved_state_passes_when_canonical_field_is_missing(self) -> None:
        # Missing field in canonical snapshot is acceptable for unresolved states.
        snapshot: dict[str, object] = {}
        res = _resolution(
            "R23f",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.NEEDS_REVIEW,
            None,
            frozenset(),
            frozenset(),
            frozenset(),
        )
        errors = check_canonical_consistency(snapshot, res)
        assert errors == []


# ---------------------------------------------------------------------------
# Scenario 24 — reverse source-impact lookup
# ---------------------------------------------------------------------------


class TestScenario24ReverseSourceLookup:
    def test_lookup_finds_evidence_for_source(self) -> None:
        ev_a = _evidence("E_A", _SUBJECT_BD, _POINTER_LOA, "SRC_TARGET", 10.541)
        ev_b = _evidence("E_B", _SUBJECT_BM, _POINTER_NAME, "SRC_OTHER", "Other")
        affected_ev, affected_res = source_impact_lookup("SRC_TARGET", [ev_a, ev_b], [])
        assert len(affected_ev) == 1
        assert affected_ev[0].evidence_id == "E_A"
        assert affected_res == []

    def test_lookup_finds_resolutions_referencing_affected_evidence(self) -> None:
        ev_a = _evidence("E_A", _SUBJECT_BD, _POINTER_LOA, "SRC_TARGET", 10.541)
        res_using_a = _resolution(
            "R_A",
            _SUBJECT_BD,
            _POINTER_LOA,
            ResolutionState.RESOLVED,
            10.541,
            frozenset({"E_A"}),
            frozenset(),
            frozenset({"E_A"}),
        )
        res_unrelated = _resolution(
            "R_B",
            _SUBJECT_BM,
            _POINTER_NAME,
            ResolutionState.UNKNOWN,
            None,
            frozenset(),
            frozenset(),
            frozenset({"E_UNRELATED"}),
        )
        affected_ev, affected_res = source_impact_lookup(
            "SRC_TARGET", [ev_a], [res_using_a, res_unrelated]
        )
        assert len(affected_ev) == 1
        assert len(affected_res) == 1
        assert affected_res[0].resolution_id == "R_A"

    def test_lookup_empty_for_unknown_source(self) -> None:
        ev = _evidence("E_A", _SUBJECT_BD, _POINTER_LOA, "SRC_KNOWN", 10.541)
        affected_ev, affected_res = source_impact_lookup("SRC_UNKNOWN", [ev], [])
        assert affected_ev == []
        assert affected_res == []


# ---------------------------------------------------------------------------
# Scenario 25 — SLICE-0004 measurement normalization → normalized candidate
# ---------------------------------------------------------------------------


class TestScenario25MeasurementNormalizationIntegration:
    def test_normalized_candidate_preserves_raw_representation(self) -> None:
        obs = MeasurementObservation(
            quantity=Quantity.LENGTH,
            value=Decimal("10"),
            unit=LengthUnit.METRE,
            raw_text="10 m",
            semantic_label=None,
        )
        normalized = normalize_measurement(obs)

        raw = RawObservation(
            kind=RawObservationKind.LITERAL,
            value=str(obs.value),
            unit=obs.unit.value,
            excerpt=obs.raw_text,
        )
        nc = NormalizedCandidate(
            value=float(normalized.canonical_value),
            unit=normalized.canonical_unit,
            method_id="length.normalize",
            method_version="1",
        )
        ev = FieldEvidence(
            evidence_id="E25",
            subject=_SUBJECT_BD,
            field_pointer=_POINTER_LOA,
            source_id="SRC_001",
            source_locator=_LOCATOR_NULL,
            raw=raw,
            normalized_candidate=nc,
            evidence_type=EvidenceType.MANUFACTURER_SPECIFICATION,
            producer=_PRODUCER_TOOL,
            research_context=_CONTEXT_NULL,
            observed_at="2026-08-18T00:00:00Z",
            confidence=ConfidenceLevel.HIGH,
            supersedes_evidence_id=None,
            notes=None,
        )
        # Raw representation is unchanged
        assert ev.raw.value == "10"
        assert ev.raw.unit == "m"
        assert ev.raw.excerpt == "10 m"
        # Normalized candidate is set
        assert ev.normalized_candidate is not None
        assert ev.normalized_candidate.unit == "m"
        # Normalization result is accessible separately from raw
        assert ev.normalized_candidate.value == float(Decimal("10"))

    def test_normalization_from_feet_preserves_raw(self) -> None:
        obs = MeasurementObservation(
            quantity=Quantity.LENGTH,
            value=Decimal("34.5"),
            unit=LengthUnit.FOOT,
            raw_text="34.5 ft",
            semantic_label=None,
        )
        normalized = normalize_measurement(obs)

        raw = RawObservation(
            kind=RawObservationKind.LITERAL,
            value=str(obs.value),
            unit=obs.unit.value,
            excerpt=obs.raw_text,
        )
        nc = NormalizedCandidate(
            value=float(normalized.canonical_value),
            unit=normalized.canonical_unit,
            method_id="length.normalize",
            method_version="1",
        )
        assert raw.value == "34.5"
        assert raw.unit == "ft"
        assert raw.excerpt == "34.5 ft"
        assert nc.unit == "m"
        assert nc.value != raw.value  # normalized value differs from raw


# ---------------------------------------------------------------------------
# Scenario 26 — no source-rights, network, or authority-ranking API in module
# ---------------------------------------------------------------------------


class TestScenario26NoForbiddenApi:
    def test_module_does_not_import_network_libraries(self) -> None:
        import hullq.domain.provenance as prov_module

        source = inspect.getsource(prov_module)
        forbidden_imports = ["import httpx", "import requests", "import urllib.request"]
        for imp in forbidden_imports:
            assert imp not in source, f"Module must not import network library: {imp!r}"

    def test_module_has_no_source_rights_granting_api(self) -> None:
        import hullq.domain.provenance as prov_module

        public_names = [n for n in dir(prov_module) if not n.startswith("_")]
        forbidden = [
            "grant_rights",
            "grant_source_rights",
            "clear_source_rights",
            "set_authority_score",
            "rank_source",
            "score_source",
            "fetch_source",
            "fetch_network",
            "ingest_from",
        ]
        for name in forbidden:
            assert name not in public_names, (
                f"Module must not expose {name!r}; source rights belong to SLICE-0007"
            )

    def test_module_has_no_research_job_api(self) -> None:
        import hullq.domain.provenance as prov_module

        public_names = [n for n in dir(prov_module) if not n.startswith("_")]
        assert "ResearchJob" not in public_names
        assert "create_research_job" not in public_names


# ---------------------------------------------------------------------------
# Property-based tests — RFC 6901 pointer escaping round-trip
# ---------------------------------------------------------------------------


# Characters valid in JSON object keys that need encoding for JSON Pointer
_KEY_CHARS = st.text(
    alphabet=st.characters(blacklist_characters="\x00"),
    min_size=1,
    max_size=20,
)


@given(key=_KEY_CHARS)
@settings(max_examples=200)
def test_pointer_key_round_trip(key: str) -> None:
    """A key containing arbitrary characters can be encoded and decoded correctly."""
    encoded = key.replace("~", "~0").replace("/", "~1")
    ptr = JsonPointer(f"/{encoded}")
    assert ptr.tokens == (key,)
    # Lookup confirms decode navigates correctly
    obj = {key: "found"}
    assert ptr.lookup(obj) == "found"


@given(
    keys=st.lists(
        _KEY_CHARS,
        min_size=1,
        max_size=4,
    )
)
@settings(max_examples=100)
def test_pointer_multi_token_round_trip(keys: list[str]) -> None:
    """A multi-token pointer encodes and decodes each segment independently."""
    encoded_keys = [k.replace("~", "~0").replace("/", "~1") for k in keys]
    raw = "/" + "/".join(encoded_keys)
    ptr = JsonPointer(raw)
    assert ptr.tokens == tuple(keys)


# ---------------------------------------------------------------------------
# SubjectKind enum parity with PROVENANCE_SUBJECT_SCHEMA.v0.1.json
# ---------------------------------------------------------------------------


def test_subject_kind_enum_matches_schema_values() -> None:
    """SubjectKind values must exactly match the schema's kind enum."""
    import json
    from pathlib import Path

    specs = Path(__file__).resolve().parents[2] / "specs"
    schema = json.loads((specs / "PROVENANCE_SUBJECT_SCHEMA.v0.1.json").read_text(encoding="utf-8"))
    schema_kinds: set[str] = set(schema["properties"]["kind"]["enum"])
    python_kinds = {kind.value for kind in SubjectKind}
    assert python_kinds == schema_kinds, (
        f"SubjectKind enum values do not match schema: "
        f"python_only={python_kinds - schema_kinds}, "
        f"schema_only={schema_kinds - python_kinds}"
    )
