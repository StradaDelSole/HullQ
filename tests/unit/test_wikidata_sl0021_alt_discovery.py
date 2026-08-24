"""Unit tests for the SLICE-0021 pure-logic alternative Wikidata discovery
measurement module (``hullq.bootstrap.wikidata_sl0021_alt_discovery``).

All tests are offline and deterministic: no network access occurs anywhere in
this file. Covers the controlling slice's reproducibility requirements:

- exactly four fixed routes, byte-identical query text, deterministic digests;
- hard-pinned historical 1,829 / accepted 1,770 universes;
- current-R0 drift is measured independently of alternative-route incremental
  yield (never added together);
- incremental yield is computed against CURRENT R0, never merely the
  historical 1,829 set;
- hard sample caps (<=75/route, <=200 global), deterministic numeric-QID
  selection;
- identity-signal matching is exact-only: no internal-whitespace collapsing,
  punctuation rewriting, prefix manipulation, token reordering or fuzzy match
  can ever manufacture a signal;
- R3 membership never authorizes canonical admission (no such capability
  exists in this module at all).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from hullq.bootstrap.wikidata_sl0021_alt_discovery import (
    ACCEPTED_AUTO_ADMIT_COUNT,
    R0,
    R1,
    R2,
    R3,
    RETAINED_DIRECT_DISCOVERY_COUNT,
    ROUTE_HARD_LIMIT,
    ROUTES,
    SAMPLE_CAP_GLOBAL,
    SAMPLE_CAP_PER_ROUTE,
    AcceptedIdentity,
    IdentitySignalCategory,
    ImmutableInputIntegrityError,
    RouteDisposition,
    SampleCompletenessError,
    build_accepted_label_index,
    build_accepted_universe,
    build_discovery_probe_document,
    build_route_record,
    build_sampled_candidates_document,
    classify_identity_signal,
    compute_cross_route_overlap,
    compute_incremental_yield,
    compute_query_sha256,
    compute_r0_drift,
    determine_route_disposition,
    load_and_fingerprint_immutable_inputs,
    normalize_exact,
    qid_list_digest,
    qid_sort_key,
    select_entity_detail_sample,
    verify_immutable_inputs_self_consistency,
    verify_route_record_self_consistency,
    verify_sample_entity_detail_completeness,
    verify_sampled_candidates_self_consistency,
)

ROOT = Path(__file__).resolve().parents[2]
SL0021_DIR = ROOT / "research" / "bootstrap" / "wikidata" / "sl0021-alt-discovery"


# ---------------------------------------------------------------------------
# Fixed routes
# ---------------------------------------------------------------------------


def test_exactly_four_fixed_routes() -> None:
    assert len(ROUTES) == 4
    assert [r.route_id for r in ROUTES] == [
        "current_direct_control",
        "sailboat_class_closure",
        "legacy_sailboat_class_closure",
        "misclassified_sailboat_class_description",
    ]


def test_route_query_text_matches_controlling_slice_document() -> None:
    assert R0.query_text == (
        "SELECT DISTINCT ?item WHERE {\n"
        "  ?item wdt:P31 wd:Q106179098 .\n"
        "}\n"
        "ORDER BY ?item\n"
        "LIMIT 3000\n"
    )
    assert "wdt:P31/wdt:P279* wd:Q106179098" in R1.query_text
    assert "wdt:P31/wdt:P279* wd:Q57303455" in R2.query_text
    assert "wdt:P31 wd:Q1075310" in R3.query_text
    assert 'CONTAINS(?desc, "sailboat class")' in R3.query_text
    for route in ROUTES:
        assert "SELECT DISTINCT" in route.query_text
        assert "ORDER BY ?item" in route.query_text
        assert "LIMIT 3000" in route.query_text


def test_query_sha256_is_deterministic_and_route_specific() -> None:
    assert compute_query_sha256(R0) == compute_query_sha256(R0)
    digests = {compute_query_sha256(r) for r in ROUTES}
    assert len(digests) == 4


def test_qid_sort_key_is_numeric_not_lexicographic() -> None:
    ordered = sorted(["Q10", "Q9", "Q2", "Q100"], key=qid_sort_key)
    assert ordered == ["Q2", "Q9", "Q10", "Q100"]


def test_qid_list_digest_is_order_sensitive_and_deterministic() -> None:
    assert qid_list_digest(["Q1", "Q2"]) == qid_list_digest(["Q1", "Q2"])
    assert qid_list_digest(["Q1", "Q2"]) != qid_list_digest(["Q2", "Q1"])


# ---------------------------------------------------------------------------
# Route record construction
# ---------------------------------------------------------------------------


def test_build_route_record_basic_fields() -> None:
    record = build_route_record(
        R0, ["Q1", "Q2"], acquired_at="2026-08-24T00:00:00+00:00", http_request_count=1
    )
    assert record["route_id"] == "current_direct_control"
    assert record["result_count"] == 2
    assert record["possibly_truncated"] is False
    assert record["hard_limit"] == ROUTE_HARD_LIMIT
    assert record["qids"] == ["Q1", "Q2"]


def test_build_route_record_possibly_truncated_at_hard_limit() -> None:
    qids = [f"Q{i}" for i in range(1, ROUTE_HARD_LIMIT + 1)]
    record = build_route_record(
        R0, qids, acquired_at="2026-08-24T00:00:00+00:00", http_request_count=1
    )
    assert record["result_count"] == ROUTE_HARD_LIMIT
    assert record["possibly_truncated"] is True


def test_build_route_record_rejects_duplicate_qid() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        build_route_record(
            R0, ["Q1", "Q1"], acquired_at="2026-08-24T00:00:00+00:00", http_request_count=1
        )


def test_build_route_record_rejects_result_exceeding_hard_limit() -> None:
    qids = [f"Q{i}" for i in range(1, ROUTE_HARD_LIMIT + 2)]
    with pytest.raises(ValueError, match="exceeding the hard limit"):
        build_route_record(R0, qids, acquired_at="2026-08-24T00:00:00+00:00", http_request_count=1)


def test_build_route_record_r3_retains_item_descriptions() -> None:
    record = build_route_record(
        R3,
        ["Q5", "Q3"],
        acquired_at="2026-08-24T00:00:00+00:00",
        http_request_count=1,
        item_descriptions={"Q5": "a sailboat class", "Q3": "another sailboat class"},
    )
    assert record["item_descriptions"] == {"Q3": "another sailboat class", "Q5": "a sailboat class"}


def test_build_route_record_without_item_descriptions_omits_field() -> None:
    record = build_route_record(
        R0, ["Q1"], acquired_at="2026-08-24T00:00:00+00:00", http_request_count=1
    )
    assert "item_descriptions" not in record


# ---------------------------------------------------------------------------
# Immutable input loading/fingerprinting — real accepted artifacts
# ---------------------------------------------------------------------------


def test_load_and_fingerprint_immutable_inputs_against_real_accepted_artifacts() -> None:
    universe = load_and_fingerprint_immutable_inputs()
    assert len(universe.retained_direct_discovery_qids) == RETAINED_DIRECT_DISCOVERY_COUNT == 1829
    assert len(universe.accepted_auto_admit_identities) == ACCEPTED_AUTO_ADMIT_COUNT == 1770
    assert universe.accepted_auto_admit_qids <= universe.retained_direct_discovery_qids


def test_load_and_fingerprint_immutable_inputs_fails_closed_on_sl0017_tamper(
    tmp_path: Path,
) -> None:
    real_sl0017 = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"
    real_sl0018 = ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"
    tampered = tmp_path / "manifest.json"
    tampered.write_text(real_sl0017.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ImmutableInputIntegrityError, match="SLICE-0017"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=tampered, sl0018_manifest_path=real_sl0018
        )


def test_load_and_fingerprint_immutable_inputs_fails_closed_on_sl0018_tamper(
    tmp_path: Path,
) -> None:
    real_sl0017 = ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json"
    real_sl0018 = ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json"
    tampered = tmp_path / "manifest.json"
    tampered.write_text(real_sl0018.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ImmutableInputIntegrityError, match="SLICE-0018"):
        load_and_fingerprint_immutable_inputs(
            sl0017_manifest_path=real_sl0017, sl0018_manifest_path=tampered
        )


def test_build_accepted_universe_synthetic_no_integrity_enforcement() -> None:
    identities = (AcceptedIdentity(qid="Q1", label="Foo", aliases=("Foo Alias",)),)
    universe = build_accepted_universe(
        retained_direct_discovery_qids=frozenset({"Q1", "Q2"}),
        accepted_auto_admit_identities=identities,
    )
    assert universe.accepted_auto_admit_qids == frozenset({"Q1"})
    assert universe.retained_direct_discovery_qids == frozenset({"Q1", "Q2"})


# ---------------------------------------------------------------------------
# R0 drift measurement — separate from alternative-route incremental yield
# ---------------------------------------------------------------------------


def test_compute_r0_drift_measures_present_absent_new() -> None:
    retained = frozenset({"Q1", "Q2", "Q3"})
    current = ["Q2", "Q3", "Q4"]
    drift = compute_r0_drift(retained, current)
    assert drift.retained_direct_count == 3
    assert drift.current_direct_count == 3
    assert drift.retained_direct_still_present_count == 2
    assert drift.retained_direct_absent_now_count == 1
    assert drift.retained_direct_absent_now_qids == ("Q1",)
    assert drift.new_current_direct_since_sl0018_count == 1
    assert drift.new_current_direct_since_sl0018_qids == ("Q4",)


def test_compute_r0_drift_zero_drift() -> None:
    retained = frozenset({"Q1", "Q2"})
    drift = compute_r0_drift(retained, ["Q1", "Q2"])
    assert drift.retained_direct_absent_now_count == 0
    assert drift.new_current_direct_since_sl0018_count == 0


def test_incremental_yield_independent_of_retained_historical_set() -> None:
    """Incremental yield is computed strictly against CURRENT R0 — the
    function does not even accept the historical retained set as an input,
    so drift and incremental yield can never be conflated by construction.
    """
    current_r0 = ["Q1", "Q2"]
    route_qids = ["Q1", "Q2", "Q3", "Q4"]
    incremental = compute_incremental_yield(route_qids, current_r0)
    assert incremental == frozenset({"Q3", "Q4"})
    # Changing what the "historical retained" universe would have been (not
    # even passed in) cannot affect this result.
    assert compute_incremental_yield(route_qids, current_r0) == incremental


# ---------------------------------------------------------------------------
# Cross-route overlap
# ---------------------------------------------------------------------------


def test_compute_cross_route_overlap() -> None:
    incremental = {
        "R1": frozenset({"Q1", "Q2", "Q3"}),
        "R2": frozenset({"Q2", "Q3", "Q4"}),
        "R3": frozenset({"Q3", "Q5"}),
    }
    overlap = compute_cross_route_overlap(incremental)
    assert overlap.pairwise[("R1", "R2")] == frozenset({"Q2", "Q3"})
    assert overlap.pairwise[("R1", "R3")] == frozenset({"Q3"})
    assert overlap.pairwise[("R2", "R3")] == frozenset({"Q3"})
    assert overlap.total_union == frozenset({"Q1", "Q2", "Q3", "Q4", "Q5"})
    assert overlap.unique_contribution["R1"] == frozenset({"Q1"})
    assert overlap.unique_contribution["R2"] == frozenset({"Q4"})
    assert overlap.unique_contribution["R3"] == frozenset({"Q5"})


def test_compute_cross_route_overlap_no_overlap() -> None:
    incremental = {"R1": frozenset({"Q1"}), "R2": frozenset({"Q2"}), "R3": frozenset()}
    overlap = compute_cross_route_overlap(incremental)
    assert overlap.pairwise[("R1", "R2")] == frozenset()
    assert overlap.unique_contribution["R1"] == frozenset({"Q1"})
    assert overlap.unique_contribution["R3"] == frozenset()


# ---------------------------------------------------------------------------
# Sample selection — hard caps, deterministic numeric order
# ---------------------------------------------------------------------------


def test_sample_selection_caps_per_route_at_75() -> None:
    many = frozenset(f"Q{i}" for i in range(1, 101))
    incremental = {"R1": many, "R2": frozenset(), "R3": frozenset()}
    sample = select_entity_detail_sample(incremental)
    assert len(sample.per_route_pre_global_cap["R1"]) == SAMPLE_CAP_PER_ROUTE == 75
    assert sample.per_route_pre_global_cap["R1"] == tuple(f"Q{i}" for i in range(1, 76))


def test_sample_selection_caps_global_at_200() -> None:
    r1 = frozenset(f"Q{i}" for i in range(1, 76))
    r2 = frozenset(f"Q{i}" for i in range(1000, 1075))
    r3 = frozenset(f"Q{i}" for i in range(2000, 2075))
    incremental = {"R1": r1, "R2": r2, "R3": r3}
    sample = select_entity_detail_sample(incremental)
    assert len(sample.selected_qids) == SAMPLE_CAP_GLOBAL == 200
    # deterministic ascending numeric order
    assert [qid_sort_key(q) for q in sample.selected_qids] == sorted(
        qid_sort_key(q) for q in sample.selected_qids
    )


def test_sample_selection_route_membership_uses_full_incremental_set() -> None:
    """A QID beyond one route's own 75-cap can still be sampled via another
    route's cap; its recorded route membership must reflect the FULL
    incremental set for every route, not only the capped subset.
    """
    # Q200 is the 101st-smallest QID in R1's incremental set (beyond the
    # 75-cap) but is also incremental for R2 (within R2's cap), so it must be
    # selected and its membership must include R1 too.
    r1 = frozenset([f"Q{i}" for i in range(1, 101)] + ["Q200"])
    r2 = frozenset({"Q200"})
    incremental = {"R1": r1, "R2": r2, "R3": frozenset()}
    sample = select_entity_detail_sample(incremental)
    assert "Q200" in sample.selected_qids
    assert "Q200" in sample.route_membership["R1"]
    assert "Q200" in sample.route_membership["R2"]


def test_sample_selection_empty_input() -> None:
    sample = select_entity_detail_sample({"R1": frozenset(), "R2": frozenset(), "R3": frozenset()})
    assert sample.selected_qids == ()


# ---------------------------------------------------------------------------
# Exact-only identity-signal classification — no fuzzy/heuristic matching
# ---------------------------------------------------------------------------


def test_normalize_exact_trims_and_casefolds_only() -> None:
    assert normalize_exact("  Foo Bar  ") == "foo bar"
    assert normalize_exact("FOO BAR") == normalize_exact("foo bar")


def test_normalize_exact_does_not_collapse_internal_whitespace() -> None:
    assert normalize_exact("Foo  Bar") != normalize_exact("Foo Bar")


def test_normalize_exact_does_not_strip_punctuation() -> None:
    assert normalize_exact("Foo-Bar") != normalize_exact("Foo Bar")


_ACCEPTED = (
    AcceptedIdentity(qid="Q100", label="Sunfast 32", aliases=("Sun Fast 32",)),
    AcceptedIdentity(qid="Q101", label="Contessa 32", aliases=()),
    AcceptedIdentity(qid="Q102", label="Ambiguous Class", aliases=()),
    AcceptedIdentity(qid="Q103", label="ambiguous class", aliases=()),
)


def test_classify_identity_signal_accepted_qid_overlap() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, owners = classify_identity_signal(
        "Q100",
        "Something Else Entirely",
        (),
        accepted_qids=frozenset({"Q100", "Q101", "Q102", "Q103"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.ACCEPTED_QID_OVERLAP
    assert owners == ("Q100",)


def test_classify_identity_signal_exact_label_match_other_qid() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, owners = classify_identity_signal(
        "Q999",
        "  sunfast 32  ",
        (),
        accepted_qids=frozenset({"Q100", "Q101", "Q102", "Q103"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.EXACT_IDENTITY_SIGNAL_OTHER_QID
    assert owners == ("Q100",)


def test_classify_identity_signal_exact_alias_match() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, owners = classify_identity_signal(
        "Q999",
        "Sun Fast 32",
        (),
        accepted_qids=frozenset({"Q100"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.EXACT_IDENTITY_SIGNAL_OTHER_QID
    assert owners == ("Q100",)


def test_classify_identity_signal_unresolved_when_two_owners_share_normalized_label() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, owners = classify_identity_signal(
        "Q999",
        "Ambiguous Class",
        (),
        accepted_qids=frozenset({"Q102", "Q103"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.UNRESOLVED_EXACT_IDENTITY_SIGNAL
    assert owners == ("Q102", "Q103")


def test_classify_identity_signal_no_signal() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, owners = classify_identity_signal(
        "Q999",
        "Completely Novel Boat",
        (),
        accepted_qids=frozenset({"Q100"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL
    assert owners == ()


def test_classify_identity_signal_no_signal_when_label_none() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, owners = classify_identity_signal(
        "Q999", None, (), accepted_qids=frozenset(), accepted_label_index=index
    )
    assert category == IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL
    assert owners == ()


def test_classify_identity_signal_internal_whitespace_cannot_manufacture_match() -> None:
    """'Sun  Fast 32' (double space) must NOT match 'Sun Fast 32' (single
    space): internal-whitespace collapsing is forbidden normalization.
    """
    index = build_accepted_label_index(_ACCEPTED)
    category, _ = classify_identity_signal(
        "Q999",
        "Sun  Fast 32",
        (),
        accepted_qids=frozenset({"Q100"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL


def test_classify_identity_signal_prefix_manipulation_cannot_manufacture_match() -> None:
    """Manufacturer-prefix insertion/stripping must not create a signal:
    'Beneteau Contessa 32' must NOT match accepted label 'Contessa 32'.
    """
    index = build_accepted_label_index(_ACCEPTED)
    category, _ = classify_identity_signal(
        "Q999",
        "Beneteau Contessa 32",
        (),
        accepted_qids=frozenset({"Q101"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL


def test_classify_identity_signal_punctuation_rewriting_cannot_manufacture_match() -> None:
    index = build_accepted_label_index(_ACCEPTED)
    category, _ = classify_identity_signal(
        "Q999",
        "Contessa-32",
        (),
        accepted_qids=frozenset({"Q101"}),
        accepted_label_index=index,
    )
    assert category == IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL


# ---------------------------------------------------------------------------
# Route disposition — evidence-derived recommendation only
# ---------------------------------------------------------------------------


def test_disposition_no_incremental_yield() -> None:
    assert (
        determine_route_disposition(0, [IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL])
        == RouteDisposition.NO_INCREMENTAL_YIELD
    )
    assert determine_route_disposition(0, []) == RouteDisposition.NO_INCREMENTAL_YIELD


def test_disposition_research_only_when_all_sampled_are_accepted_overlap() -> None:
    categories = [
        IdentitySignalCategory.ACCEPTED_QID_OVERLAP,
        IdentitySignalCategory.ACCEPTED_QID_OVERLAP,
    ]
    assert determine_route_disposition(5, categories) == RouteDisposition.RESEARCH_ONLY_SIGNAL


def test_disposition_followup_candidate_when_any_novel_signal_present() -> None:
    categories = [
        IdentitySignalCategory.ACCEPTED_QID_OVERLAP,
        IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL,
    ]
    assert (
        determine_route_disposition(5, categories) == RouteDisposition.FOLLOWUP_DISCOVERY_CANDIDATE
    )


# ---------------------------------------------------------------------------
# Document assembly + schema validation
# ---------------------------------------------------------------------------


def _make_universe() -> object:
    return build_accepted_universe(
        retained_direct_discovery_qids=frozenset({"Q1", "Q2"}),
        accepted_auto_admit_identities=(AcceptedIdentity(qid="Q1", label="Foo", aliases=()),),
        sl0017_manifest_path="research/bootstrap/wikidata/manifest.json",
        sl0017_sha256="a" * 64,
        sl0018_manifest_path="research/bootstrap/wikidata/sl0018-2500/manifest.json",
        sl0018_sha256="b" * 64,
    )


def test_build_discovery_probe_document_validates_against_schema() -> None:
    universe = _make_universe()
    acquired_at = "2026-08-24T00:00:00+00:00"
    route_records = {
        key: build_route_record(route, ["Q1"], acquired_at=acquired_at, http_request_count=1)
        for key, route in zip(("R0", "R1", "R2", "R3"), ROUTES, strict=True)
    }
    incremental = {"R1": frozenset(), "R2": frozenset(), "R3": frozenset()}
    overlap = compute_cross_route_overlap(incremental)
    drift = compute_r0_drift(frozenset({"Q1"}), ["Q1"])
    doc = build_discovery_probe_document(
        generated_at=acquired_at,
        source_id="SRC_WIKIDATA_API_2026",
        rights_gate={"automated_ingestion": "allowed", "bulk_bootstrap": "allowed"},
        accepted_universe=universe,  # type: ignore[arg-type]
        route_records=route_records,
        drift=drift,
        incremental_by_route=incremental,
        cross_route_overlap=overlap,
    )
    schema = json.loads((SL0021_DIR / "discovery_probe_schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)


def test_build_discovery_probe_document_rejects_wrong_route_keys() -> None:
    universe = _make_universe()
    with pytest.raises(ValueError, match="route_records"):
        build_discovery_probe_document(
            generated_at="2026-08-24T00:00:00+00:00",
            source_id="SRC_WIKIDATA_API_2026",
            rights_gate={"automated_ingestion": "allowed", "bulk_bootstrap": "allowed"},
            accepted_universe=universe,  # type: ignore[arg-type]
            route_records={"R0": {}},
            drift=compute_r0_drift(frozenset(), []),
            incremental_by_route={"R1": frozenset(), "R2": frozenset(), "R3": frozenset()},
            cross_route_overlap=compute_cross_route_overlap(
                {"R1": frozenset(), "R2": frozenset(), "R3": frozenset()}
            ),
        )


def test_build_sampled_candidates_document_validates_against_schema_and_r3_notice() -> None:
    universe = _make_universe()
    sample = select_entity_detail_sample(
        {"R1": frozenset({"Q9"}), "R2": frozenset(), "R3": frozenset({"Q9"})}
    )
    candidate_rows = [
        {
            "qid": "Q9",
            "route_membership": ["R1", "R3"],
            "label": "Some Boat",
            "aliases": [],
            "description_en": "a sailboat class",
            "p31_qids": ["Q1075310"],
            "p279_qids": [],
            "p176_qids": [],
            "p287_qids": [],
            "identity_signal_category": str(IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL),
            "identity_signal_owner_qids": [],
        }
    ]
    doc = build_sampled_candidates_document(
        generated_at="2026-08-24T00:00:00+00:00",
        accepted_universe=universe,  # type: ignore[arg-type]
        sample=sample,
        candidate_rows=candidate_rows,
        route_dispositions={
            "R1": str(RouteDisposition.FOLLOWUP_DISCOVERY_CANDIDATE),
            "R2": str(RouteDisposition.NO_INCREMENTAL_YIELD),
            "R3": str(RouteDisposition.FOLLOWUP_DISCOVERY_CANDIDATE),
        },
    )
    schema = json.loads((SL0021_DIR / "sampled_candidates_schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(instance=doc, schema=schema)
    assert doc["category_totals"]["no_exact_identity_signal"] == 1
    # R3 membership never authorizes canonical admission: the fail-closed
    # notice is always present regardless of the measured disposition, and
    # this document has no field or capability that mints/mutates a
    # canonical HullQ row.
    assert "never directly authorizes canonical admission" in doc["r3_fail_closed_notice"]
    assert "boat_model_id" not in json.dumps(doc)


def test_build_sampled_candidates_document_rejects_wrong_disposition_keys() -> None:
    universe = _make_universe()
    sample = select_entity_detail_sample({"R1": frozenset(), "R2": frozenset(), "R3": frozenset()})
    with pytest.raises(ValueError, match="route_dispositions"):
        build_sampled_candidates_document(
            generated_at="2026-08-24T00:00:00+00:00",
            accepted_universe=universe,  # type: ignore[arg-type]
            sample=sample,
            candidate_rows=[],
            route_dispositions={"R1": "x"},
        )


# ---------------------------------------------------------------------------
# AMENDMENT (independent review round 1): hardened offline self-consistency
# and fail-closed live-run completeness checks. These prove every retained
# summary field is independently recomputed from the document's own raw
# facts — a tampered summary field must never silently validate itself.
# ---------------------------------------------------------------------------

_ACQUIRED_AT = "2026-08-24T00:00:00+00:00"


def test_verify_route_record_self_consistency_passes_on_untampered_record() -> None:
    record = build_route_record(R1, ["Q1", "Q2"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    assert verify_route_record_self_consistency("R1", record) == []


def test_verify_route_record_self_consistency_detects_tampered_qid_list_digest() -> None:
    record = build_route_record(R0, ["Q1", "Q2"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["qid_list_digest"] = "0" * 64
    mismatches = verify_route_record_self_consistency("R0", record)
    assert any("qid_list_digest" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_result_count() -> None:
    record = build_route_record(R0, ["Q1", "Q2"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["result_count"] = 999
    mismatches = verify_route_record_self_consistency("R0", record)
    assert any("result_count" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_route_id() -> None:
    record = build_route_record(R0, ["Q1"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["route_id"] = "some_other_route_id"
    mismatches = verify_route_record_self_consistency("R0", record)
    assert any("route_id" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_version() -> None:
    record = build_route_record(R1, ["Q1"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["version"] = "SLICE-0021-R1-v2-fake"
    mismatches = verify_route_record_self_consistency("R1", record)
    assert any(".version=" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_query_text() -> None:
    record = build_route_record(R2, ["Q1"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["query_text"] = "SELECT DISTINCT ?item WHERE { ?item wdt:P31 wd:Q999999 . }"
    mismatches = verify_route_record_self_consistency("R2", record)
    assert any("query_text" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_query_sha256() -> None:
    record = build_route_record(R3, ["Q1"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["query_sha256"] = "f" * 64
    mismatches = verify_route_record_self_consistency("R3", record)
    assert any("query_sha256" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_possibly_truncated() -> None:
    record = build_route_record(R0, ["Q1"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["possibly_truncated"] = True
    mismatches = verify_route_record_self_consistency("R0", record)
    assert any("possibly_truncated" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_tampered_hard_limit() -> None:
    record = build_route_record(R0, ["Q1"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["hard_limit"] = 5000
    mismatches = verify_route_record_self_consistency("R0", record)
    assert any("hard_limit" in m for m in mismatches)


def test_verify_route_record_self_consistency_detects_duplicate_qids_in_raw_dict() -> None:
    """Even a hand-crafted dict (bypassing build_route_record's own dedup
    guard) must be independently caught by the self-consistency recompute.
    """
    record = build_route_record(R0, ["Q1", "Q2"], acquired_at=_ACQUIRED_AT, http_request_count=1)
    record["qids"] = ["Q1", "Q1", "Q2"]
    mismatches = verify_route_record_self_consistency("R0", record)
    assert any("duplicate" in m for m in mismatches)


def test_verify_route_record_self_consistency_unknown_route_key() -> None:
    assert verify_route_record_self_consistency("R99", {}) == ["unknown route key 'R99'"]


# ---------------------------------------------------------------------------
# verify_immutable_inputs_self_consistency
# ---------------------------------------------------------------------------


def _immutable_inputs_doc(universe: Any) -> dict[str, Any]:
    u = universe
    return {
        "sl0017_manifest": {"path": u.sl0017_manifest_path, "sha256": u.sl0017_sha256},
        "sl0018_manifest": {"path": u.sl0018_manifest_path, "sha256": u.sl0018_sha256},
        "retained_direct_discovery_count": len(u.retained_direct_discovery_qids),
        "accepted_auto_admit_count": len(u.accepted_auto_admit_identities),
    }


def test_verify_immutable_inputs_self_consistency_passes_on_real_accepted_artifacts() -> None:
    universe = load_and_fingerprint_immutable_inputs()
    doc = _immutable_inputs_doc(universe)
    assert verify_immutable_inputs_self_consistency(doc, universe) == []


def test_verify_immutable_inputs_self_consistency_detects_sl0017_sha256_reference_mismatch() -> (
    None
):
    universe = load_and_fingerprint_immutable_inputs()
    doc = _immutable_inputs_doc(universe)
    doc["sl0017_manifest"]["sha256"] = "0" * 64
    mismatches = verify_immutable_inputs_self_consistency(doc, universe)
    assert any("sl0017_manifest.sha256" in m for m in mismatches)


def test_verify_immutable_inputs_self_consistency_detects_sl0018_sha256_reference_mismatch() -> (
    None
):
    universe = load_and_fingerprint_immutable_inputs()
    doc = _immutable_inputs_doc(universe)
    doc["sl0018_manifest"]["sha256"] = "0" * 64
    mismatches = verify_immutable_inputs_self_consistency(doc, universe)
    assert any("sl0018_manifest.sha256" in m for m in mismatches)


def test_verify_immutable_inputs_self_consistency_detects_direct_discovery_count_reference_mismatch() -> (
    None
):
    universe = load_and_fingerprint_immutable_inputs()
    doc = _immutable_inputs_doc(universe)
    doc["retained_direct_discovery_count"] = 1
    mismatches = verify_immutable_inputs_self_consistency(doc, universe)
    assert any("retained_direct_discovery_count" in m for m in mismatches)


def test_verify_immutable_inputs_self_consistency_detects_auto_admit_count_reference_mismatch() -> (
    None
):
    universe = load_and_fingerprint_immutable_inputs()
    doc = _immutable_inputs_doc(universe)
    doc["accepted_auto_admit_count"] = 1
    mismatches = verify_immutable_inputs_self_consistency(doc, universe)
    assert any("accepted_auto_admit_count" in m for m in mismatches)


def test_verify_immutable_inputs_self_consistency_detects_undersized_synthetic_universe() -> None:
    """Defense-in-depth: even if a caller supplies an AcceptedUniverse that
    bypassed the fail-closed loader (e.g. a bug elsewhere), a universe whose
    own counts do not equal the accepted 1,829/1,770 constants is flagged.
    """
    small_universe = build_accepted_universe(
        retained_direct_discovery_qids=frozenset({"Q1", "Q2"}),
        accepted_auto_admit_identities=(AcceptedIdentity(qid="Q1", label="Foo", aliases=()),),
    )
    doc = _immutable_inputs_doc(small_universe)
    mismatches = verify_immutable_inputs_self_consistency(doc, small_universe)
    assert any(f"!= accepted constant {RETAINED_DIRECT_DISCOVERY_COUNT}" in m for m in mismatches)
    assert any(f"!= accepted constant {ACCEPTED_AUTO_ADMIT_COUNT}" in m for m in mismatches)


# ---------------------------------------------------------------------------
# verify_sampled_candidates_self_consistency
# ---------------------------------------------------------------------------


def _consistent_sampled_doc() -> tuple[dict[str, Any], dict[str, frozenset[str]]]:
    incremental_by_route = {
        "R1": frozenset({"Q1", "Q2"}),
        "R2": frozenset({"Q2"}),
        "R3": frozenset(),
    }
    sample = select_entity_detail_sample(incremental_by_route)
    candidates = [
        {
            "qid": qid,
            "route_membership": sorted(
                rid for rid in ("R1", "R2", "R3") if qid in incremental_by_route[rid]
            ),
            "identity_signal_category": str(IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL),
        }
        for qid in sample.selected_qids
    ]
    category_totals = {str(c): 0 for c in IdentitySignalCategory}
    for c in candidates:
        category_totals[c["identity_signal_category"]] += 1
    doc = {
        "selection": {
            "selected_qids": list(sample.selected_qids),
            "selected_count": len(sample.selected_qids),
        },
        "candidates": candidates,
        "category_totals": category_totals,
    }
    return doc, incremental_by_route


def test_verify_sampled_candidates_self_consistency_passes_on_consistent_doc() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    assert verify_sampled_candidates_self_consistency(doc, incremental_by_route) == []


def test_verify_sampled_candidates_self_consistency_detects_wrong_selected_count() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    doc["selection"]["selected_count"] = 999
    mismatches = verify_sampled_candidates_self_consistency(doc, incremental_by_route)
    assert any("selected_count" in m for m in mismatches)


def test_verify_sampled_candidates_self_consistency_detects_missing_candidate_row() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    doc["candidates"] = doc["candidates"][1:]
    mismatches = verify_sampled_candidates_self_consistency(doc, incremental_by_route)
    assert any("missing selected QID" in m for m in mismatches)


def test_verify_sampled_candidates_self_consistency_detects_extra_candidate_row() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    doc["candidates"].append(
        {
            "qid": "Q999",
            "route_membership": [],
            "identity_signal_category": str(IdentitySignalCategory.NO_EXACT_IDENTITY_SIGNAL),
        }
    )
    mismatches = verify_sampled_candidates_self_consistency(doc, incremental_by_route)
    assert any("unexpected QID" in m for m in mismatches)


def test_verify_sampled_candidates_self_consistency_detects_duplicate_candidate_row() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    doc["candidates"].append(dict(doc["candidates"][0]))
    mismatches = verify_sampled_candidates_self_consistency(doc, incremental_by_route)
    assert any("duplicate" in m for m in mismatches)


def test_verify_sampled_candidates_self_consistency_detects_wrong_route_membership() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    doc["candidates"][0]["route_membership"] = ["R3"]
    mismatches = verify_sampled_candidates_self_consistency(doc, incremental_by_route)
    assert any("route_membership" in m for m in mismatches)


def test_verify_sampled_candidates_self_consistency_detects_wrong_category_totals() -> None:
    doc, incremental_by_route = _consistent_sampled_doc()
    doc["category_totals"]["no_exact_identity_signal"] = 999
    mismatches = verify_sampled_candidates_self_consistency(doc, incremental_by_route)
    assert any("category_totals" in m for m in mismatches)


# ---------------------------------------------------------------------------
# verify_sample_entity_detail_completeness / SampleCompletenessError
# ---------------------------------------------------------------------------


def test_verify_sample_entity_detail_completeness_passes_on_exact_match() -> None:
    verify_sample_entity_detail_completeness(["Q1", "Q2"], ["Q1", "Q2"])


def test_verify_sample_entity_detail_completeness_passes_on_empty() -> None:
    verify_sample_entity_detail_completeness([], [])


def test_verify_sample_entity_detail_completeness_raises_on_missing_qid() -> None:
    with pytest.raises(SampleCompletenessError, match="missing"):
        verify_sample_entity_detail_completeness(["Q1", "Q2"], ["Q1"])


def test_verify_sample_entity_detail_completeness_raises_on_unexpected_qid() -> None:
    with pytest.raises(SampleCompletenessError, match="unexpected"):
        verify_sample_entity_detail_completeness(["Q1"], ["Q1", "Q2"])


def test_verify_sample_entity_detail_completeness_raises_on_duplicate_qid() -> None:
    with pytest.raises(SampleCompletenessError, match="duplicates"):
        verify_sample_entity_detail_completeness(["Q1", "Q2"], ["Q1", "Q1", "Q2"])


def test_verify_sample_entity_detail_completeness_does_not_modify_retained_facts() -> None:
    """The check is purely a read-only comparison; it must never mutate its
    inputs (the retained live QID/entity facts must remain unchanged even
    when this check is exercised repeatedly).
    """
    selected = ["Q1", "Q2"]
    fetched = ["Q1", "Q2"]
    verify_sample_entity_detail_completeness(selected, fetched)
    assert selected == ["Q1", "Q2"]
    assert fetched == ["Q1", "Q2"]
