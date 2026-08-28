"""Unit tests for hullq.bootstrap.wikidata_sl0030_mass_unit_correction — SLICE-0030.

All tests are offline, deterministic, and use small synthetic fixtures rather
than the real 1,770-entity retained SLICE-0028 package (exercised separately
by the runner script's --replay/--verify modes against the committed
research/stage3/sl0030-wikidata-mass-unit-correction/ package).
"""

from __future__ import annotations

from typing import Any

import pytest

from hullq.bootstrap.wikidata_sl0030_mass_unit_correction import (
    FIXED_UNIT_QIDS,
    SL0030_ACTIVITY_ID,
    VERIFIED_MASS_UNIT_INSTANCE_QID,
    UnitEntitySnapshot,
    UnitIdentityValidationError,
    build_artifact_digests,
    build_coverage_before_after_document,
    build_sl0030_bundle,
    build_unit_qid_assessment_document,
    compute_before_after_coverage,
    count_mass_unit_qid_occurrences,
    validate_unit_qid_snapshots,
    verify_artifact_digests_self_consistency,
    verify_coverage_before_after_self_consistency,
    verify_unit_qid_assessment_self_consistency,
)
from hullq.domain.provenance import (
    ConfidenceLevel,
    EvidenceType,
    FieldEvidence,
    JsonPointer,
    NormalizedCandidate,
    ProducerKind,
    ProducerMetadata,
    ProvenanceSubject,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
    SubjectKind,
)
from hullq.sources.wikidata import (
    DEFAULT_UNIT_QID_MAP_VERSION,
    UNIT_QID_MAP_VERSION_SLICE0008,
    WikidataAdapter,
    WikidataAdapterConfig,
    WikidataEntityData,
)


def _mass_claim(amount: str, unit_qid: str, *, qualifier_qid: str = "Q5636358") -> dict[str, Any]:
    """A P2067 mass statement with a displacement (Q5636358) P642 qualifier
    by default — mass statements require a qualifier to route to a field at
    all, independent of unit-QID recognition."""
    return {
        "mainsnak": {
            "snaktype": "value",
            "datavalue": {
                "type": "quantity",
                "value": {"amount": amount, "unit": f"http://www.wikidata.org/entity/{unit_qid}"},
            },
        },
        "qualifiers": {
            "P642": [
                {
                    "snaktype": "value",
                    "datavalue": {"type": "wikibase-entityid", "value": {"id": qualifier_qid}},
                }
            ]
        },
    }


def _all_snapshots(
    overrides: dict[str, UnitEntitySnapshot] | None = None,
) -> tuple[UnitEntitySnapshot, ...]:
    overrides = overrides or {}
    defaults = {
        "Q11570": UnitEntitySnapshot("Q11570", "kilogram", "metric unit of mass", ("Q3647172",)),
        "Q41803": UnitEntitySnapshot("Q41803", "gram", "unit of mass", ("Q3647172",)),
        "Q191118": UnitEntitySnapshot("Q191118", "tonne", "metric unit of mass", ("Q3647172",)),
        "Q100995": UnitEntitySnapshot("Q100995", "pound", "unit of mass", ("Q3647172",)),
        "Q12152": UnitEntitySnapshot(
            "Q12152", "myocardial infarction", "heart condition", ("Q1931388",)
        ),
        "Q11369": UnitEntitySnapshot("Q11369", "molecule", "chemical substance", ("Q72070508",)),
        "Q37795": UnitEntitySnapshot(
            "Q37795", "Romanian Raven Shepherd Dog", "dog breed", ("Q39367",)
        ),
    }
    defaults.update(overrides)
    return tuple(defaults[qid] for qid in FIXED_UNIT_QIDS)


# ---------------------------------------------------------------------------
# count_mass_unit_qid_occurrences
# ---------------------------------------------------------------------------


def test_count_mass_unit_qid_occurrences_counts_only_recognized_uris() -> None:
    entities = [
        WikidataEntityData(
            qid="Q1",
            label="A",
            aliases=[],
            raw_claims={"P2067": [_mass_claim("+4500", "Q100995"), _mass_claim("+5", "Q191118")]},
        ),
        WikidataEntityData(
            qid="Q2",
            label="B",
            aliases=[],
            raw_claims={"P2067": [_mass_claim("+9999", "Q100995")]},
        ),
        WikidataEntityData(qid="Q3", label="C", aliases=[], raw_claims={}),
    ]
    counts = count_mass_unit_qid_occurrences(entities)
    assert counts["Q100995"] == 2
    assert counts["Q191118"] == 1
    assert counts["Q11570"] == 0
    assert counts["Q12152"] == 0
    assert counts["Q11369"] == 0
    assert counts["Q37795"] == 0
    assert counts["Q41803"] == 0


def test_count_mass_unit_qid_occurrences_ignores_non_mass_properties() -> None:
    entities = [
        WikidataEntityData(
            qid="Q1",
            label="A",
            aliases=[],
            raw_claims={"P2043": [_mass_claim("+4.2", "Q100995")]},  # wrong property (P2043=length)
        )
    ]
    counts = count_mass_unit_qid_occurrences(entities)
    assert all(v == 0 for v in counts.values())


# ---------------------------------------------------------------------------
# unit_qid_assessment build/verify roundtrip
# ---------------------------------------------------------------------------


def test_unit_qid_assessment_classification_and_intended_unit() -> None:
    doc = build_unit_qid_assessment_document(
        generated_at="2026-01-01T00:00:00Z",
        verified_at="2026-01-01T00:00:00Z",
        snapshots=_all_snapshots(),
        occurrence_counts={"Q11570": 224, "Q191118": 1, "Q100995": 794},
    )
    rows = {row["qid"]: row for row in doc["assessed_units"]}
    assert rows["Q11570"]["classification"] == "correct_existing_mapping"
    assert rows["Q11570"]["intended_hullq_unit"] == "MassUnit.KILOGRAM"
    for qid, unit in (
        ("Q41803", "MassUnit.GRAM"),
        ("Q191118", "MassUnit.METRIC_TONNE"),
        ("Q100995", "MassUnit.POUND"),
    ):
        assert rows[qid]["classification"] == "corrected_positively_verified_mapping"
        assert rows[qid]["intended_hullq_unit"] == unit
    for qid in ("Q12152", "Q11369", "Q37795"):
        assert rows[qid]["classification"] == "incorrect_legacy_mapping"
        assert rows[qid]["intended_hullq_unit"] is None
        assert rows[qid]["occurs_in_sl0028_retained_raw_claims"] is False
        assert rows[qid]["observed_retained_statement_count"] == 0
        assert rows[qid]["verified_is_unit_of_mass"] is False
    for qid in ("Q11570", "Q41803", "Q191118", "Q100995"):
        assert rows[qid]["verified_is_unit_of_mass"] is True
        assert rows[qid]["verified_unit_of_mass_instance_qid"] == VERIFIED_MASS_UNIT_INSTANCE_QID
    assert rows["Q100995"]["occurs_in_sl0028_retained_raw_claims"] is True
    assert rows["Q100995"]["observed_retained_statement_count"] == 794


def test_unit_qid_assessment_requires_exactly_the_fixed_qid_set() -> None:
    incomplete = _all_snapshots()[:-1]
    with pytest.raises(ValueError, match="FIXED_UNIT_QIDS"):
        build_unit_qid_assessment_document(
            generated_at="2026-01-01T00:00:00Z",
            verified_at="2026-01-01T00:00:00Z",
            snapshots=incomplete,
            occurrence_counts={},
        )


# ---------------------------------------------------------------------------
# Fail-closed identity validation (independent-review requirement)
# ---------------------------------------------------------------------------


def test_validate_unit_qid_snapshots_passes_for_consistent_evidence() -> None:
    validate_unit_qid_snapshots(_all_snapshots())  # must not raise


def test_validate_unit_qid_snapshots_rejects_supported_qid_missing_mass_unit_p31() -> None:
    """Q41803 (gram) is expected to verify as a mass unit. If the live P31
    evidence does NOT include VERIFIED_MASS_UNIT_INSTANCE_QID, this is a
    contradictory response and must fail closed rather than being silently
    classified corrected_positively_verified_mapping."""
    contradictory = _all_snapshots(
        {"Q41803": UnitEntitySnapshot("Q41803", "gram", "unit of mass", ("Q208469",))}
    )
    with pytest.raises(UnitIdentityValidationError, match="Q41803"):
        validate_unit_qid_snapshots(contradictory)


def test_validate_unit_qid_snapshots_rejects_rejected_qid_with_mass_unit_p31() -> None:
    """Q12152 is expected to NOT verify as a mass unit. If a live response
    unexpectedly carried the mass-unit P31 claim, this contradicts the
    incorrect_legacy_mapping classification and must fail closed rather than
    being silently accepted."""
    contradictory = _all_snapshots(
        {
            "Q12152": UnitEntitySnapshot(
                "Q12152",
                "myocardial infarction",
                "heart condition",
                (VERIFIED_MASS_UNIT_INSTANCE_QID,),
            )
        }
    )
    with pytest.raises(UnitIdentityValidationError, match="Q12152"):
        validate_unit_qid_snapshots(contradictory)


def test_build_unit_qid_assessment_document_refuses_to_build_on_contradictory_evidence() -> None:
    """build_unit_qid_assessment_document must never return a document when
    the fail-closed identity check fails — the caller (--identity-check)
    relies on this to refuse writing a contradictory assessment."""
    contradictory = _all_snapshots(
        {"Q100995": UnitEntitySnapshot("Q100995", "pound", "unit of mass", ("Q82047057",))}
    )
    with pytest.raises(UnitIdentityValidationError, match="Q100995"):
        build_unit_qid_assessment_document(
            generated_at="2026-01-01T00:00:00Z",
            verified_at="2026-01-01T00:00:00Z",
            snapshots=contradictory,
            occurrence_counts={},
        )


def test_verify_unit_qid_assessment_self_consistency_fails_closed_on_tampered_p31_evidence() -> (
    None
):
    """If a retained raw_entity_snapshots entry is altered so its P31
    evidence no longer supports the QID's classification, offline
    verification must report a problem (via the same fail-closed validator),
    never silently pass."""
    entities: list[WikidataEntityData] = []
    doc = build_unit_qid_assessment_document(
        generated_at="2026-01-01T00:00:00Z",
        verified_at="2026-01-01T00:00:00Z",
        snapshots=_all_snapshots(),
        occurrence_counts=count_mass_unit_qid_occurrences(entities),
    )
    tampered = dict(doc)
    tampered["raw_entity_snapshots"] = [
        {**row, "p31_qids": ["Q208469"]} if row["qid"] == "Q41803" else row
        for row in doc["raw_entity_snapshots"]
    ]
    problems = verify_unit_qid_assessment_self_consistency(
        sl0028_entities=entities, document=tampered
    )
    assert problems != []
    assert any("Q41803" in p for p in problems)


def test_verify_unit_qid_assessment_self_consistency_passes_for_matching_document() -> None:
    entities = [
        WikidataEntityData(
            qid="Q1", label="A", aliases=[], raw_claims={"P2067": [_mass_claim("+2490", "Q100995")]}
        )
    ]
    doc = build_unit_qid_assessment_document(
        generated_at="2026-01-01T00:00:00Z",
        verified_at="2026-01-01T00:00:00Z",
        snapshots=_all_snapshots(),
        occurrence_counts=count_mass_unit_qid_occurrences(entities),
    )
    problems = verify_unit_qid_assessment_self_consistency(sl0028_entities=entities, document=doc)
    assert problems == []


def test_verify_unit_qid_assessment_self_consistency_detects_tampering() -> None:
    entities = [
        WikidataEntityData(
            qid="Q1", label="A", aliases=[], raw_claims={"P2067": [_mass_claim("+2490", "Q100995")]}
        )
    ]
    doc = build_unit_qid_assessment_document(
        generated_at="2026-01-01T00:00:00Z",
        verified_at="2026-01-01T00:00:00Z",
        snapshots=_all_snapshots(),
        occurrence_counts=count_mass_unit_qid_occurrences(entities),
    )
    tampered = dict(doc)
    tampered["assessed_units"] = [
        {**row, "observed_retained_statement_count": 0} if row["qid"] == "Q100995" else row
        for row in doc["assessed_units"]
    ]
    problems = verify_unit_qid_assessment_self_consistency(
        sl0028_entities=entities, document=tampered
    )
    assert problems != []


# ---------------------------------------------------------------------------
# coverage_before_after build/verify roundtrip
# ---------------------------------------------------------------------------


def _extract_before_after(
    entities: list[WikidataEntityData],
) -> tuple[list[FieldEvidence], list[FieldEvidence]]:
    source = {"source_id": "SRC_WIKIDATA_API_2026"}
    config = WikidataAdapterConfig(user_agent="HullQ/0.1 (test@example.com)")
    import httpx

    with httpx.Client() as client:
        adapter = WikidataAdapter(source=source, config=config, http_client=client)
        before, _ = adapter.extract_field_evidence(
            entities,
            "2026-01-01T00:00:00Z",
            requested_qid_count=len(entities),
            unit_map_version=UNIT_QID_MAP_VERSION_SLICE0008,
        )
        after, _ = adapter.extract_field_evidence(
            entities,
            "2026-01-01T00:00:00Z",
            requested_qid_count=len(entities),
            unit_map_version=DEFAULT_UNIT_QID_MAP_VERSION,
        )
    return before, after


def test_coverage_before_after_shows_displacement_delta_only() -> None:
    entities = [
        WikidataEntityData(
            qid="Q1", label="A", aliases=[], raw_claims={"P2067": [_mass_claim("+2490", "Q100995")]}
        ),
        WikidataEntityData(
            qid="Q2",
            label="B",
            aliases=[],
            raw_claims={
                "P2043": [
                    {
                        "mainsnak": {
                            "snaktype": "value",
                            "datavalue": {
                                "type": "quantity",
                                "value": {
                                    "amount": "+9.5",
                                    "unit": "http://www.wikidata.org/entity/Q11573",
                                },
                            },
                        },
                        "qualifiers": {
                            "P642": [
                                {
                                    "snaktype": "value",
                                    "datavalue": {
                                        "type": "wikibase-entityid",
                                        "value": {"id": "Q2358152"},
                                    },
                                }
                            ]
                        },
                    }
                ]
            },
        ),
    ]
    before, after = _extract_before_after(entities)
    before_counts, after_counts = compute_before_after_coverage(entities, before, after)
    doc = build_coverage_before_after_document(
        generated_at="2026-01-01T00:00:00Z",
        qid_count=len(entities),
        before_counts=before_counts,
        after_counts=after_counts,
    )
    assert doc["displacement_normalized_candidate_delta"] == 1
    assert doc["non_displacement_fields_unchanged"] is True
    assert doc["fields"]["loa"]["before"] == doc["fields"]["loa"]["after"]
    assert (
        doc["fields"]["displacement"]["before"]["normalized_candidate_present"]
        != doc["fields"]["displacement"]["after"]["normalized_candidate_present"]
    )

    problems = verify_coverage_before_after_self_consistency(
        entities=entities, full_evidence_before=before, full_evidence_after=after, document=doc
    )
    assert problems == []


def test_verify_coverage_before_after_detects_tampering() -> None:
    entities = [
        WikidataEntityData(
            qid="Q1", label="A", aliases=[], raw_claims={"P2067": [_mass_claim("+2490", "Q100995")]}
        )
    ]
    before, after = _extract_before_after(entities)
    before_counts, after_counts = compute_before_after_coverage(entities, before, after)
    doc = build_coverage_before_after_document(
        generated_at="2026-01-01T00:00:00Z",
        qid_count=len(entities),
        before_counts=before_counts,
        after_counts=after_counts,
    )
    tampered = dict(doc)
    tampered["displacement_normalized_candidate_delta"] = 999
    problems = verify_coverage_before_after_self_consistency(
        entities=entities, full_evidence_before=before, full_evidence_after=after, document=tampered
    )
    assert problems != []


# ---------------------------------------------------------------------------
# build_sl0030_bundle
# ---------------------------------------------------------------------------


def _make_evidence(qid: str, pointer: str) -> FieldEvidence:
    return FieldEvidence(
        evidence_id=f"WD-{qid}-P2067-idx0",
        subject=ProvenanceSubject(kind=SubjectKind.BOAT_DESIGN, id=qid),
        field_pointer=JsonPointer(pointer),
        source_id="SRC_WIKIDATA_API_2026",
        source_locator=SourceLocator(
            page=None,
            section=None,
            anchor=None,
            table=None,
            figure=None,
            record_key=f"{qid}/P2067/0",
        ),
        raw=RawObservation(
            kind=RawObservationKind.LITERAL, value={"amount": "+1"}, unit="Q100995", excerpt=None
        ),
        normalized_candidate=NormalizedCandidate(
            value=__import__("decimal").Decimal("1"),
            unit="kg",
            method_id="hullq-measurements-1.0",
            method_version="SLICE-0004-v1",
        ),
        evidence_type=EvidenceType.API_RECORD,
        producer=ProducerMetadata(
            kind=ProducerKind.DETERMINISTIC_TOOL,
            identifier="hullq-wikidata-adapter",
            version="test",
            model=None,
            prompt_or_rule_version=None,
        ),
        research_context=ResearchContext(research_job_id=None, activity_id=None),
        observed_at="2026-01-01T00:00:00Z",
        confidence=ConfidenceLevel.MEDIUM,
        supersedes_evidence_id=None,
        notes=None,
    )


def test_build_sl0030_bundle_uses_distinct_namespace() -> None:
    ev = _make_evidence("Q1", "/baseline/dimensions/displacement_kg")
    bundle = build_sl0030_bundle("Q1", "Test Yacht", [ev])
    assert bundle.bundle_id == "BUNDLE-SL0030-Q1"
    assert bundle.bundle_id != "BUNDLE-SL0028-Q1"
    assert bundle.activity_id == SL0030_ACTIVITY_ID
    assert len(bundle.promoted_evidence) == 1


def test_build_sl0030_bundle_rejects_subject_mismatch() -> None:
    ev = _make_evidence("Q2", "/baseline/dimensions/displacement_kg")
    with pytest.raises(ValueError, match="does not match requested QID"):
        build_sl0030_bundle("Q1", "Test Yacht", [ev])


def test_build_sl0030_bundle_rejects_disallowed_field_pointer() -> None:
    ev = _make_evidence("Q1", "/baseline/dimensions/ballast_kg")
    with pytest.raises(ValueError, match="not one of the five allowed"):
        build_sl0030_bundle("Q1", "Test Yacht", [ev])


# ---------------------------------------------------------------------------
# artifact digests
# ---------------------------------------------------------------------------


def test_artifact_digests_roundtrip_and_tamper_detection(tmp_path: Any) -> None:
    (tmp_path / "a.json").write_text('{"x":1}', encoding="utf-8")
    (tmp_path / "b.json").write_text('{"y":2}', encoding="utf-8")

    digests = build_artifact_digests(generated_at="2026-01-01T00:00:00Z", package_dir=tmp_path)
    assert set(digests["digests"]) == {"a.json", "b.json"}
    assert (
        verify_artifact_digests_self_consistency(artifact_digests=digests, package_dir=tmp_path)
        == []
    )

    (tmp_path / "a.json").write_text('{"x":999}', encoding="utf-8")
    problems = verify_artifact_digests_self_consistency(
        artifact_digests=digests, package_dir=tmp_path
    )
    assert problems != []
