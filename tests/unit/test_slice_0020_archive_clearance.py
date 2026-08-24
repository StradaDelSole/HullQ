"""Reproducibility and invariant proof for the SLICE-0020 archive-clearance package.

Offline and deterministic: no web/network calls, no external research performed
here. Executes the retained generator chain in-process (build_clearance_data ->
compute_overlap) against the committed inputs and asserts the regenerated
structured outputs are byte-identical (modulo line-ending style) to what is
committed in the repository. Also pins the exact bounded-pilot/clearance
totals required by SLICE-0020's acceptance criteria so a future edit cannot
silently drift the fixed-sample size, the accepted comparison universe, the
classification totals, or the exact-match-only overlap semantics.
"""

from __future__ import annotations

import importlib.util
import json
import sys
import types
from pathlib import Path

import jsonschema
import pytest

ARCHIVE_CLEARANCE = (
    Path(__file__).resolve().parents[2] / "research" / "manufacturers" / "archive_clearance"
)


def _load_module(name: str, path: Path) -> types.ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def archive_clearance_path_prefix():
    """compute_overlap.py imports the sibling archive_identity_pilot_input module by
    bare name, which only resolves when this directory is on sys.path."""
    inserted = str(ARCHIVE_CLEARANCE) not in sys.path
    if inserted:
        sys.path.insert(0, str(ARCHIVE_CLEARANCE))
    yield
    if inserted:
        sys.path.remove(str(ARCHIVE_CLEARANCE))


ARTIFACTS = [
    ARCHIVE_CLEARANCE / "archive_source_clearance.json",
    ARCHIVE_CLEARANCE / "archive_identity_pilot.json",
]


def _normalize_newlines(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def test_generator_chain_reproduces_committed_artifacts(archive_clearance_path_prefix):
    before = {path: path.read_bytes() for path in ARTIFACTS}

    build_clearance_data = _load_module(
        "slice0020_build_clearance_data", ARCHIVE_CLEARANCE / "build_clearance_data.py"
    )
    build_clearance_data.main()

    compute_overlap = _load_module(
        "slice0020_compute_overlap", ARCHIVE_CLEARANCE / "compute_overlap.py"
    )
    compute_overlap.main()

    after = {path: path.read_bytes() for path in ARTIFACTS}

    for path in ARTIFACTS:
        assert _normalize_newlines(after[path]) == _normalize_newlines(before[path]), (
            f"{path.name} regenerated from the committed generator chain does not match the "
            "committed artifact (content, ignoring line-ending style)"
        )


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_clearance_data_validates_against_schema():
    schema = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance_schema.json")
    data = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance.json")
    jsonschema.validate(instance=data, schema=schema)


def test_pilot_data_validates_against_schema():
    schema = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot_schema.json")
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    jsonschema.validate(instance=data, schema=schema)


def test_exactly_ten_sources():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance.json")
    assert len(data["sources"]) == 10
    assert data["review_date"] == "2026-08-24"
    for source in data["sources"]:
        assert source["review_date"] == "2026-08-24"


def test_exactly_ten_identities_per_source_and_hundred_total():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    assert data["pilot_bounds"]["source_count"] == 10
    assert data["pilot_bounds"]["per_source_retained"] == 10
    assert data["pilot_bounds"]["total_retained"] == 100
    assert len(data["records"]) == 100
    assert len(data["per_source"]) == 10
    for summary in data["per_source"]:
        assert summary["retained_count"] == 10


def test_accepted_comparison_universe_exactly_1770():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    assert data["accepted_universe"]["auto_admit_hullq_id_count"] == 1770
    assert data["accepted_universe"]["expected_canonical_boatmodel_count"] == 1770


def test_classification_totals_match_contract_result():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance.json")
    adapter_ready = [s for s in data["sources"] if s["adapter_classification"] == "ADAPTER_READY"]
    research_only = [
        s
        for s in data["sources"]
        if s["adapter_classification"] == "RESEARCH_ONLY / REVIEW_REQUIRED"
    ]
    blocked = [s for s in data["sources"] if s["adapter_classification"] == "BLOCKED"]

    assert len(adapter_ready) == 0
    assert len(research_only) == 9
    assert len(blocked) == 1
    assert blocked[0]["source_key"] == "beneteau"


def test_no_source_classified_adapter_ready_without_passing_the_hardened_test():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance.json")
    for source in data["sources"]:
        decisions = source["use_specific_decisions"]
        test = source["adapter_ready_test"]

        assert test["identity_seed_allowed"] == (decisions["identity_seed"] == "allowed")
        assert test["automated_ingestion_allowed"] == (
            decisions["automated_ingestion"] == "allowed"
        )

        if source["adapter_classification"] == "ADAPTER_READY":
            assert test["result"] is True
            assert decisions["identity_seed"] == "allowed"
            assert decisions["automated_ingestion"] == "allowed"
        else:
            assert test["result"] is False
            assert (
                decisions["identity_seed"] != "allowed"
                or decisions["automated_ingestion"] != "allowed"
                or not test["bulk_bootstrap_allowed_or_bounded_conditions_documented"]
            )

        # SR-003 / SLICE-0020 fail-closed rule: conditional/legal_review_required/
        # prohibited/unknown identity_seed or automated_ingestion must never produce
        # ADAPTER_READY.
        if decisions["identity_seed"] in {
            "conditional",
            "legal_review_required",
            "prohibited",
            "unknown",
        }:
            assert source["adapter_classification"] != "ADAPTER_READY"
        if decisions["automated_ingestion"] in {
            "conditional",
            "legal_review_required",
            "prohibited",
            "unknown",
        }:
            assert source["adapter_classification"] != "ADAPTER_READY"


def test_beneteau_blocked_reason_is_explicit_terms_prohibition():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance.json")
    beneteau = next(s for s in data["sources"] if s["source_key"] == "beneteau")
    assert beneteau["systematic_use_status"] == "BLOCKED"
    assert beneteau["use_specific_decisions"]["automated_ingestion"] == "prohibited"
    assert beneteau["use_specific_decisions"]["bulk_bootstrap"] == "prohibited"
    assert (
        beneteau["automation_evidence"]["robots_or_api_status"] == "explicit_prohibition_via_terms"
    )


def test_unknown_or_ambiguous_rights_never_round_up_to_allowed():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_source_clearance.json")
    for source in data["sources"]:
        decisions = source["use_specific_decisions"]
        # Every source in this pilot's supplied research has automated_ingestion of
        # unknown or prohibited -- never allowed -- which is the fail-closed result
        # this slice is required to produce for the fixed sample.
        assert decisions["automated_ingestion"] in {"unknown", "prohibited"}
        assert decisions["bulk_bootstrap"] in {"legal_review_required", "prohibited"}


def test_no_bluewater_offshore_luxury_suitability_classification_fields():
    """HullQ must never introduce its own bluewater/offshore/luxury suitability
    classification. This checks the actual HullQ-authored classification
    surfaces (schema field names, and the identity-pilot's own
    discriminating_context/classification values) rather than scanning quoted
    third-party research prose: a supplied research finding may truthfully
    report that a manufacturer's own marketing describes itself as e.g.
    'luxury' (as SLICE-0019's registry.json already does for Oyster/Contest
    evidence quotes) without HullQ applying that as a suitability label."""

    forbidden = {"bluewater", "offshore", "luxury"}

    for schema_path in [
        ARCHIVE_CLEARANCE / "archive_source_clearance_schema.json",
        ARCHIVE_CLEARANCE / "archive_identity_pilot_schema.json",
    ]:
        schema_text = schema_path.read_text(encoding="utf-8").lower()
        for term in forbidden:
            assert term not in schema_text, (
                f"{schema_path.name} defines a forbidden field/enum {term!r}"
            )

    pilot = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    for record in pilot["records"]:
        context = record["discriminating_context"].lower()
        for term in forbidden:
            assert term not in context, (
                f"{record['source_key']}/{record['model_name']} discriminating_context "
                f"contains forbidden suitability term {term!r}"
            )


def test_overlap_aggregate_counts_equal_record_level_classifications():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    records = data["records"]

    counted = {"exact_overlap": 0, "no_exact_overlap_signal": 0, "unresolved_possible_overlap": 0}
    for record in records:
        counted[record["classification"]] += 1

    assert data["totals"]["exact_overlap"] == counted["exact_overlap"]
    assert data["totals"]["no_exact_overlap_signal"] == counted["no_exact_overlap_signal"]
    assert data["totals"]["unresolved_possible_overlap"] == counted["unresolved_possible_overlap"]

    for summary in data["per_source"]:
        source_records = [r for r in records if r["source_key"] == summary["source_key"]]
        assert len(source_records) == 10
        source_counted = {
            "exact_overlap": 0,
            "no_exact_overlap_signal": 0,
            "unresolved_possible_overlap": 0,
        }
        for record in source_records:
            source_counted[record["classification"]] += 1
        assert summary["exact_overlap_count"] == source_counted["exact_overlap"]
        assert summary["no_exact_overlap_signal_count"] == source_counted["no_exact_overlap_signal"]
        assert (
            summary["unresolved_possible_overlap_count"]
            == source_counted["unresolved_possible_overlap"]
        )


def test_known_regression_exact_overlaps_are_found():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    by_name = {(r["source_key"], r["model_name"]): r for r in data["records"]}

    expected_exact = [
        ("catalina_yachts", "Catalina 16.5"),
        ("catalina_yachts", "Catalina 18"),
        ("catalina_yachts", "Catalina 25"),
        ("catalina_yachts", "Catalina 27"),
        ("catalina_yachts", "Catalina 28"),
        ("pearson_yachts", "Pearson 26"),
        ("pearson_yachts", "Pearson 30"),
        ("pearson_yachts", "Pearson 303"),
        ("hallberg_rassy", "Hallberg-Rassy 40"),
    ]
    for key in expected_exact:
        assert by_name[key]["classification"] == "exact_overlap", key

    assert data["totals"]["exact_overlap"] == len(expected_exact)


def test_manufacturer_prefix_overlap_guard_not_upgraded():
    """'First 26' (as Bénéteau's archive presents it) MUST NOT be treated as a match
    for the accepted preferred label 'Beneteau First 26' merely by prefix insertion."""

    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    record = next(
        r
        for r in data["records"]
        if r["source_key"] == "beneteau" and r["model_name"] == "First 26"
    )
    assert record["classification"] == "no_exact_overlap_signal"
    assert record["matched_hullq_ids"] == []


def test_gs_abbreviation_not_expanded_to_grand_soleil():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    gs_records = [
        r
        for r in data["records"]
        if r["source_key"] == "cantiere_del_pardo_grand_soleil"
        and r["model_name"].startswith("GS ")
    ]
    assert len(gs_records) == 9
    for record in gs_records:
        assert not record["model_name"].startswith("Grand Soleil")


def test_westerly_model_names_have_no_inserted_manufacturer_prefix():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    westerly_records = [r for r in data["records"] if r["source_key"] == "westerly_marine"]
    assert len(westerly_records) == 10
    for record in westerly_records:
        assert not record["model_name"].lower().startswith("westerly")


def test_no_unresolved_possible_overlap_forced_to_exact_or_new():
    """This bounded pilot happened to find zero ambiguous cases; assert that fact
    explicitly so a future data change that introduces ambiguity is forced to
    re-examine classification rather than silently defaulting one way."""

    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    assert data["totals"]["unresolved_possible_overlap"] == 0


def test_identity_hazard_notes_are_preserved_not_silently_resolved():
    data = _load_json(ARCHIVE_CLEARANCE / "archive_identity_pilot.json")
    by_name = {(r["source_key"], r["model_name"]): r for r in data["records"]}

    elan_e3 = by_name[("elan", "Elan E3")]
    assert "hazard" in elan_e3["discriminating_context"].lower()

    first_32 = by_name[("beneteau", "First 32")]
    first_38 = by_name[("beneteau", "First 38")]
    assert "not independently confirmed" in first_32["discriminating_context"]
    assert "not independently confirmed" in first_38["discriminating_context"]
