"""Unit tests for the SLICE-0023 pure-logic Wikimedia category identity-lead
measurement module (``hullq.bootstrap.wikimedia_sl0023_category_leads``).

All tests are offline and deterministic: no network access occurs anywhere in
this file. Covers the controlling slice's reproducibility requirements:

- accepted immutable 1,829/1,770/1,772/57 boundaries reproduce fail-closed
  against the real retained repository artifacts, and fail closed on tamper;
- fixed category hard caps are enforced fail-closed;
- cross-category duplicate page IDs and duplicate QIDs are measured, not
  silently dropped or double-counted;
- the four overlap categories are exact and mutually exclusive;
- the exact trim+casefold-only title-signal probe never fuzzy-matches;
- multi-category primary-stratum precedence is exactly
  ``Trimarans > Catamarans > Keelboats``;
- deterministic SHA256 sample selection is reproducible, per-stratum-capped,
  and never backfills from another stratum;
- the mechanical recommendation rule is applied exactly as precommitted;
- fixed request ceilings fail closed rather than exceed silently;
- every offline self-consistency verifier rejects a tampered retained field.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from hullq.bootstrap.wikidata_sl0021_alt_discovery import AcceptedIdentity, build_accepted_universe
from hullq.bootstrap.wikimedia_sl0023_category_leads import (
    ACCEPTED_ALTERNATIVE_UNION_COUNT,
    ACCEPTED_HISTORICAL_CROSSWALK_COUNT,
    ACCEPTED_SL0021_DISCOVERY_PROBE_GIT_BLOB_SHA1,
    ACCEPTED_SL0021_SAMPLED_CANDIDATES_GIT_BLOB_SHA1,
    CATAMARANS,
    CATEGORY_ROUTES,
    COMBINED_MEMBERSHIP_CAP,
    KEELBOATS,
    ROUTE_CATAMARANS,
    ROUTE_KEELBOATS,
    ROUTE_TRIMARANS,
    SAMPLE_CAP_BY_STRATUM,
    SAMPLE_TOTAL_CAP,
    STRATUM_PRECEDENCE,
    TOTAL_REQUEST_CEILING,
    TRIMARANS,
    WIKIDATA_REQUEST_CEILING,
    WIKIPEDIA_REQUEST_CEILING,
    CategoryCapExceededError,
    CategoryPage,
    ImmutableBoundaries,
    ImmutableBoundaryIntegrityError,
    OverlapCategory,
    QualityTag,
    Recommendation,
    RequestCeilingExceededError,
    SampleSelection,
    TitleSignalCategory,
    apply_qid_mapping,
    assign_primary_stratum,
    build_accepted_label_index,
    build_category_membership_record,
    build_discovery_manifest_document,
    build_incremental_by_stratum,
    build_quality_sample_document,
    build_request_ceiling_summary,
    build_unique_pages,
    canonical_page_url,
    categorize_overlap,
    classify_title_signal,
    compute_overlap_sets,
    compute_qid_categories,
    compute_qid_multiplicity,
    compute_qid_sha256,
    determine_recommendation,
    git_blob_sha1,
    load_and_verify_immutable_boundaries,
    reconstruct_unique_pages_from_manifest,
    select_deterministic_sample,
    verify_category_record_self_consistency,
    verify_discovery_manifest_derived_sets_self_consistency,
    verify_immutable_boundaries_reference_self_consistency,
    verify_quality_sample_self_consistency,
    verify_sample_selection_self_consistency,
    verify_title_signal_rows_self_consistency,
    verify_unique_pages_reconstruction_self_consistency,
)

ROOT = Path(__file__).resolve().parents[2]


def _synthetic_boundaries() -> ImmutableBoundaries:
    identities = (
        AcceptedIdentity(qid="Q100", label="Contessa 32", aliases=("Contessa Thirty-Two",)),
        AcceptedIdentity(qid="Q200", label="Dragon", aliases=()),
    )
    universe = build_accepted_universe(
        retained_direct_discovery_qids=frozenset({"Q100", "Q200", "Q300"}),
        accepted_auto_admit_identities=identities,
    )
    return ImmutableBoundaries(
        accepted_universe=universe,
        retained_historical_crosswalk_count=3,
        alternative_union_qids=frozenset({"Q400", "Q500"}),
        sl0021_discovery_probe_blob_sha1="a" * 40,
        sl0021_sampled_candidates_blob_sha1="b" * 40,
    )


# ---------------------------------------------------------------------------
# Fixed category routes / caps
# ---------------------------------------------------------------------------


def test_exactly_three_fixed_category_routes() -> None:
    assert [r.name for r in CATEGORY_ROUTES] == [KEELBOATS, CATAMARANS, TRIMARANS]
    assert ROUTE_KEELBOATS.hard_cap == 2000
    assert ROUTE_CATAMARANS.hard_cap == 250
    assert ROUTE_TRIMARANS.hard_cap == 200
    assert COMBINED_MEMBERSHIP_CAP == 2450


def test_stratum_precedence_is_trimarans_catamarans_keelboats() -> None:
    assert STRATUM_PRECEDENCE == (TRIMARANS, CATAMARANS, KEELBOATS)
    assert SAMPLE_CAP_BY_STRATUM == {TRIMARANS: 30, CATAMARANS: 30, KEELBOATS: 90}
    assert SAMPLE_TOTAL_CAP == 150
    assert sum(SAMPLE_CAP_BY_STRATUM.values()) == SAMPLE_TOTAL_CAP


def test_request_ceilings_are_fixed() -> None:
    assert WIKIPEDIA_REQUEST_CEILING == 75
    assert WIKIDATA_REQUEST_CEILING == 10
    assert TOTAL_REQUEST_CEILING == 85


# ---------------------------------------------------------------------------
# Immutable boundaries against the real retained repository artifacts
# ---------------------------------------------------------------------------


def test_load_and_verify_immutable_boundaries_against_real_accepted_artifacts() -> None:
    boundaries = load_and_verify_immutable_boundaries()
    assert len(boundaries.accepted_direct_qids) == 1829
    assert len(boundaries.accepted_universe.accepted_auto_admit_identities) == 1770
    assert (
        boundaries.retained_historical_crosswalk_count
        == ACCEPTED_HISTORICAL_CROSSWALK_COUNT
        == 1772
    )
    assert len(boundaries.alternative_union_qids) == ACCEPTED_ALTERNATIVE_UNION_COUNT == 57


def test_git_blob_sha1_matches_pinned_sl0021_blobs() -> None:
    discovery_probe = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "discovery_probe.json"
    )
    sampled_candidates = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "sampled_candidates.json"
    )
    assert (
        git_blob_sha1(discovery_probe.read_bytes()) == ACCEPTED_SL0021_DISCOVERY_PROBE_GIT_BLOB_SHA1
    )
    assert (
        git_blob_sha1(sampled_candidates.read_bytes())
        == ACCEPTED_SL0021_SAMPLED_CANDIDATES_GIT_BLOB_SHA1
    )


def test_load_and_verify_immutable_boundaries_fails_closed_on_sl0021_discovery_probe_tamper(
    tmp_path: Path,
) -> None:
    real = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "discovery_probe.json"
    )
    real_sampled = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "sampled_candidates.json"
    )
    tampered = tmp_path / "discovery_probe.json"
    tampered.write_text(real.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ImmutableBoundaryIntegrityError, match="discovery_probe"):
        load_and_verify_immutable_boundaries(
            discovery_probe_path=tampered, sampled_candidates_path=real_sampled
        )


def test_load_and_verify_immutable_boundaries_fails_closed_on_sl0021_sampled_candidates_tamper(
    tmp_path: Path,
) -> None:
    real = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "discovery_probe.json"
    )
    real_sampled = (
        ROOT
        / "research"
        / "bootstrap"
        / "wikidata"
        / "sl0021-alt-discovery"
        / "sampled_candidates.json"
    )
    tampered = tmp_path / "sampled_candidates.json"
    tampered.write_text(real_sampled.read_text(encoding="utf-8") + " ", encoding="utf-8")
    with pytest.raises(ImmutableBoundaryIntegrityError, match="sampled_candidates"):
        load_and_verify_immutable_boundaries(
            discovery_probe_path=real, sampled_candidates_path=tampered
        )


# ---------------------------------------------------------------------------
# Category membership record construction
# ---------------------------------------------------------------------------


def test_canonical_page_url_replaces_spaces_with_underscores() -> None:
    assert canonical_page_url("Contessa 32") == "https://en.wikipedia.org/wiki/Contessa_32"


def test_build_category_membership_record_basic_fields() -> None:
    pages = [
        CategoryPage(pageid=1, title="Alpha", ns=0),
        CategoryPage(pageid=2, title="Beta", ns=0),
    ]
    record = build_category_membership_record(
        ROUTE_KEELBOATS,
        pages,
        acquired_at="2026-08-25T00:00:00+00:00",
        request_count=1,
        continuation_count=0,
    )
    assert record["category"] == KEELBOATS
    assert record["member_count"] == 2
    assert record["complete"] is True
    assert record["members"][0]["canonical_url"] == "https://en.wikipedia.org/wiki/Alpha"


def test_build_category_membership_record_rejects_duplicate_pageid() -> None:
    pages = [
        CategoryPage(pageid=1, title="Alpha", ns=0),
        CategoryPage(pageid=1, title="Alpha", ns=0),
    ]
    with pytest.raises(ValueError, match="duplicate page id"):
        build_category_membership_record(
            ROUTE_KEELBOATS, pages, acquired_at="x", request_count=1, continuation_count=0
        )


def test_build_category_membership_record_fails_closed_over_hard_cap() -> None:
    pages = [
        CategoryPage(pageid=i, title=f"Page {i}", ns=0) for i in range(ROUTE_TRIMARANS.hard_cap + 1)
    ]
    with pytest.raises(CategoryCapExceededError):
        build_category_membership_record(
            ROUTE_TRIMARANS, pages, acquired_at="x", request_count=1, continuation_count=0
        )


# ---------------------------------------------------------------------------
# Unique-page consolidation + duplicate tracking
# ---------------------------------------------------------------------------


def _record(category: str, pages: list[CategoryPage]) -> dict[str, object]:
    return build_category_membership_record(
        next(r for r in CATEGORY_ROUTES if r.name == category),
        pages,
        acquired_at="x",
        request_count=1,
        continuation_count=0,
    )


def test_build_unique_pages_tracks_cross_category_duplicates() -> None:
    records = {
        KEELBOATS: _record(KEELBOATS, [CategoryPage(1, "Shared", 0), CategoryPage(2, "OnlyK", 0)]),
        CATAMARANS: _record(
            CATAMARANS, [CategoryPage(1, "Shared", 0), CategoryPage(3, "OnlyC", 0)]
        ),
        TRIMARANS: _record(TRIMARANS, [CategoryPage(4, "OnlyT", 0)]),
    }
    unique_pages = build_unique_pages(records)
    assert unique_pages[1]["categories"] == (CATAMARANS, KEELBOATS)
    assert unique_pages[2]["categories"] == (KEELBOATS,)
    assert len(unique_pages) == 4


def test_build_unique_pages_rejects_inconsistent_title_for_same_pageid() -> None:
    records = {
        KEELBOATS: _record(KEELBOATS, [CategoryPage(1, "TitleA", 0)]),
        CATAMARANS: _record(CATAMARANS, [CategoryPage(1, "TitleB", 0)]),
        TRIMARANS: _record(TRIMARANS, []),
    }
    with pytest.raises(ValueError, match="inconsistent titles"):
        build_unique_pages(records)


def test_apply_qid_mapping_leaves_unmapped_pages_as_none() -> None:
    unique_pages = {1: {"title": "A", "canonical_url": "u", "categories": (KEELBOATS,)}}
    mapped = apply_qid_mapping(unique_pages, {1: "Q1"})
    assert mapped[1]["qid"] == "Q1"
    mapped2 = apply_qid_mapping(unique_pages, {})
    assert mapped2[1]["qid"] is None


def test_compute_qid_multiplicity_groups_duplicate_qids() -> None:
    pages = {
        1: {"qid": "Q1"},
        2: {"qid": "Q1"},
        3: {"qid": "Q2"},
        4: {"qid": None},
    }
    multiplicity = compute_qid_multiplicity(pages)
    assert multiplicity == {"Q1": (1, 2), "Q2": (3,)}


# ---------------------------------------------------------------------------
# Overlap categorization
# ---------------------------------------------------------------------------


def test_categorize_overlap_four_categories() -> None:
    accepted = frozenset({"Q1"})
    alt = frozenset({"Q2"})
    assert categorize_overlap(None, accepted_direct_qids=accepted, alternative_union_qids=alt) is (
        OverlapCategory.NO_WIKIDATA_QID
    )
    assert categorize_overlap("Q1", accepted_direct_qids=accepted, alternative_union_qids=alt) is (
        OverlapCategory.ACCEPTED_DIRECT_QID_OVERLAP
    )
    assert categorize_overlap("Q2", accepted_direct_qids=accepted, alternative_union_qids=alt) is (
        OverlapCategory.RETAINED_ALTERNATIVE_QID_OVERLAP
    )
    assert categorize_overlap("Q3", accepted_direct_qids=accepted, alternative_union_qids=alt) is (
        OverlapCategory.INCREMENTAL_QID_LEAD
    )


def test_compute_overlap_sets_deduplicates_and_categorizes() -> None:
    multiplicity = {"Q1": (1,), "Q2": (2,), "Q3": (3, 4)}
    no_qid = frozenset({5, 6})
    sets = compute_overlap_sets(
        multiplicity,
        no_qid,
        accepted_direct_qids=frozenset({"Q1"}),
        alternative_union_qids=frozenset({"Q2"}),
    )
    assert sets.accepted_direct_qid_overlap == frozenset({"Q1"})
    assert sets.retained_alternative_qid_overlap == frozenset({"Q2"})
    assert sets.incremental_qid_lead == frozenset({"Q3"})
    assert sets.no_wikidata_qid_pageids == frozenset({5, 6})


# ---------------------------------------------------------------------------
# Multi-category primary-stratum assignment
# ---------------------------------------------------------------------------


def test_assign_primary_stratum_precedence() -> None:
    assert assign_primary_stratum(frozenset({KEELBOATS})) == KEELBOATS
    assert assign_primary_stratum(frozenset({KEELBOATS, CATAMARANS})) == CATAMARANS
    assert assign_primary_stratum(frozenset({KEELBOATS, CATAMARANS, TRIMARANS})) == TRIMARANS
    assert assign_primary_stratum(frozenset({TRIMARANS})) == TRIMARANS


def test_assign_primary_stratum_rejects_empty_membership() -> None:
    with pytest.raises(ValueError, match="no recognized"):
        assign_primary_stratum(frozenset())


def test_compute_qid_categories_unions_across_owning_pages() -> None:
    multiplicity = {"Q1": (1, 2)}
    unique_pages = {1: {"categories": (KEELBOATS,)}, 2: {"categories": (TRIMARANS,)}}
    assert compute_qid_categories("Q1", multiplicity, unique_pages) == frozenset(
        {KEELBOATS, TRIMARANS}
    )


def test_build_incremental_by_stratum_assigns_highest_precedence() -> None:
    multiplicity = {"Q1": (1,), "Q2": (2,)}
    unique_pages = {
        1: {"categories": (KEELBOATS, CATAMARANS)},
        2: {"categories": (KEELBOATS,)},
    }
    result = build_incremental_by_stratum(frozenset({"Q1", "Q2"}), multiplicity, unique_pages)
    assert result[CATAMARANS] == frozenset({"Q1"})
    assert result[KEELBOATS] == frozenset({"Q2"})
    assert result[TRIMARANS] == frozenset()


# ---------------------------------------------------------------------------
# Deterministic SHA256 sample selection
# ---------------------------------------------------------------------------


def test_compute_qid_sha256_is_deterministic() -> None:
    assert compute_qid_sha256("Q1") == compute_qid_sha256("Q1")
    assert compute_qid_sha256("Q1") != compute_qid_sha256("Q2")


def test_select_deterministic_sample_is_reproducible_and_capped() -> None:
    incremental_by_stratum = {
        TRIMARANS: frozenset(f"Q{i}" for i in range(1, 40)),
        CATAMARANS: frozenset(f"Q{i}" for i in range(100, 140)),
        KEELBOATS: frozenset(f"Q{i}" for i in range(1000, 1200)),
    }
    sample1 = select_deterministic_sample(incremental_by_stratum)
    sample2 = select_deterministic_sample(incremental_by_stratum)
    assert sample1 == sample2
    assert len(sample1.selected_by_stratum[TRIMARANS]) == 30
    assert len(sample1.selected_by_stratum[CATAMARANS]) == 30
    assert len(sample1.selected_by_stratum[KEELBOATS]) == 90
    assert len(sample1.selected_qids) == 150
    assert list(sample1.selected_qids) == sorted(sample1.selected_qids, key=lambda q: int(q[1:]))


def test_select_deterministic_sample_does_not_backfill_across_strata() -> None:
    incremental_by_stratum = {
        TRIMARANS: frozenset({"Q1", "Q2"}),
        CATAMARANS: frozenset(),
        KEELBOATS: frozenset(f"Q{i}" for i in range(1000, 1005)),
    }
    sample = select_deterministic_sample(incremental_by_stratum)
    assert len(sample.selected_qids) == 2 + 0 + 5
    assert sample.selected_by_stratum[CATAMARANS] == ()


# ---------------------------------------------------------------------------
# Exact-only title-signal probe
# ---------------------------------------------------------------------------


def test_classify_title_signal_exact_no_and_unresolved() -> None:
    index = build_accepted_label_index(
        (
            AcceptedIdentity(qid="Q1", label="Contessa 32", aliases=()),
            AcceptedIdentity(qid="Q2", label="Dragon", aliases=("Dragon", "International Dragon")),
        )
    )
    category, owners = classify_title_signal("Contessa 32", accepted_label_index=index)
    assert category is TitleSignalCategory.EXACT_SIGNAL_OTHER_QID
    assert owners == ("Q1",)

    category, owners = classify_title_signal("  contessa 32  ", accepted_label_index=index)
    assert category is TitleSignalCategory.EXACT_SIGNAL_OTHER_QID

    category, owners = classify_title_signal("Totally Unrelated", accepted_label_index=index)
    assert category is TitleSignalCategory.NO_EXACT_SIGNAL
    assert owners == ()

    index2 = build_accepted_label_index(
        (
            AcceptedIdentity(qid="Q1", label="Dragon", aliases=()),
            AcceptedIdentity(qid="Q2", label="Dragon", aliases=()),
        )
    )
    category, owners = classify_title_signal("Dragon", accepted_label_index=index2)
    assert category is TitleSignalCategory.UNRESOLVED_STRUCTURAL
    assert owners == ("Q1", "Q2")


def test_classify_title_signal_never_collapses_internal_whitespace() -> None:
    index = build_accepted_label_index(
        (AcceptedIdentity(qid="Q1", label="Con Tessa 32", aliases=()),)
    )
    category, _ = classify_title_signal("ConTessa 32", accepted_label_index=index)
    assert category is TitleSignalCategory.NO_EXACT_SIGNAL


# ---------------------------------------------------------------------------
# Mechanical recommendation rule
# ---------------------------------------------------------------------------


def test_determine_recommendation_rights_blocked_takes_precedence() -> None:
    rec = determine_recommendation(
        rights_access_ok=False,
        unique_incremental_count=1000,
        quality_tag_counts={str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD): 150},
    )
    assert rec is Recommendation.RIGHTS_OR_ACCESS_BLOCKED


def test_determine_recommendation_low_yield_below_100() -> None:
    rec = determine_recommendation(
        rights_access_ok=True, unique_incremental_count=99, quality_tag_counts={}
    )
    assert rec is Recommendation.LOW_INCREMENTAL_YIELD


def test_determine_recommendation_at_exactly_100_is_not_low_yield() -> None:
    rec = determine_recommendation(
        rights_access_ok=True,
        unique_incremental_count=100,
        quality_tag_counts={
            str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD): 75,
            str(QualityTag.OBVIOUS_OUT_OF_SCOPE): 75,
        },
    )
    assert rec is Recommendation.FOLLOWUP_VERIFICATION_CANDIDATE


def test_determine_recommendation_too_noisy_below_50_percent() -> None:
    rec = determine_recommendation(
        rights_access_ok=True,
        unique_incremental_count=200,
        quality_tag_counts={
            str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD): 74,
            str(QualityTag.OBVIOUS_OUT_OF_SCOPE): 76,
        },
    )
    assert rec is Recommendation.TOO_NOISY_FOR_FOLLOWUP


def test_determine_recommendation_ambiguous_never_counts_as_plausible() -> None:
    rec = determine_recommendation(
        rights_access_ok=True,
        unique_incremental_count=200,
        quality_tag_counts={
            str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD): 40,
            str(QualityTag.AMBIGUOUS): 60,
        },
    )
    assert rec is Recommendation.TOO_NOISY_FOR_FOLLOWUP


def test_determine_recommendation_followup_candidate_at_exactly_50_percent() -> None:
    rec = determine_recommendation(
        rights_access_ok=True,
        unique_incremental_count=200,
        quality_tag_counts={
            str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD): 75,
            str(QualityTag.OBVIOUS_OUT_OF_SCOPE): 75,
        },
    )
    assert rec is Recommendation.FOLLOWUP_VERIFICATION_CANDIDATE


# ---------------------------------------------------------------------------
# Request-ceiling enforcement
# ---------------------------------------------------------------------------


def test_build_request_ceiling_summary_within_bounds() -> None:
    summary = build_request_ceiling_summary(wikipedia_request_count=40, wikidata_request_count=3)
    assert summary["total_request_count"] == 43
    assert summary["wikipedia_request_ceiling"] == WIKIPEDIA_REQUEST_CEILING


def test_build_request_ceiling_summary_fails_closed_over_wikipedia_ceiling() -> None:
    with pytest.raises(RequestCeilingExceededError):
        build_request_ceiling_summary(wikipedia_request_count=76, wikidata_request_count=0)


def test_build_request_ceiling_summary_fails_closed_over_wikidata_ceiling() -> None:
    with pytest.raises(RequestCeilingExceededError):
        build_request_ceiling_summary(wikipedia_request_count=0, wikidata_request_count=11)


def test_wikipedia_and_wikidata_ceilings_sum_to_total_ceiling() -> None:
    # By construction WIKIPEDIA_REQUEST_CEILING + WIKIDATA_REQUEST_CEILING == TOTAL_REQUEST_CEILING,
    # so the combined total check in build_request_ceiling_summary is defense-in-depth: it can
    # never trigger independently of the two per-host checks already having passed.
    assert WIKIPEDIA_REQUEST_CEILING + WIKIDATA_REQUEST_CEILING == TOTAL_REQUEST_CEILING
    summary = build_request_ceiling_summary(
        wikipedia_request_count=WIKIPEDIA_REQUEST_CEILING,
        wikidata_request_count=WIKIDATA_REQUEST_CEILING,
    )
    assert summary["total_request_count"] == TOTAL_REQUEST_CEILING


# ---------------------------------------------------------------------------
# Document assembly + offline self-consistency verification (tamper tests)
# ---------------------------------------------------------------------------


def _build_minimal_discovery_manifest() -> tuple[dict[str, object], tuple]:  # type: ignore[type-arg]
    # Uses the REAL retained accepted boundaries (not a small synthetic universe):
    # verify_immutable_boundaries_reference_self_consistency independently re-asserts
    # the accepted 1,829/1,770/1,772/57 constants as defense-in-depth, so it can only
    # ever pass against the real accepted boundaries.
    boundaries = load_and_verify_immutable_boundaries()
    known_qid = next(iter(boundaries.accepted_direct_qids))
    # An identity whose exact label we can reuse as a page title to deterministically
    # produce an EXACT_SIGNAL_OTHER_QID title-signal row (used by the tamper test below).
    labeled_identity = boundaries.accepted_universe.accepted_auto_admit_identities[0]
    # Two synthetic QIDs guaranteed absent from both accepted retained sets.
    incremental_qid_1 = "Q900000001"
    incremental_qid_2 = "Q900000002"
    assert incremental_qid_1 not in boundaries.accepted_direct_qids
    assert incremental_qid_1 not in boundaries.alternative_union_qids
    assert incremental_qid_2 not in boundaries.accepted_direct_qids
    assert incremental_qid_2 not in boundaries.alternative_union_qids

    records = {
        KEELBOATS: _record(
            KEELBOATS,
            [CategoryPage(1, "Known Model", 0), CategoryPage(2, labeled_identity.label, 0)],
        ),
        CATAMARANS: _record(CATAMARANS, [CategoryPage(3, "Lead Two", 0)]),
        TRIMARANS: _record(TRIMARANS, []),
    }
    unique_pages = build_unique_pages(records)
    unique_pages = apply_qid_mapping(
        unique_pages, {1: known_qid, 2: incremental_qid_1, 3: incremental_qid_2}
    )
    multiplicity = compute_qid_multiplicity(unique_pages)
    no_qid = frozenset(pid for pid, info in unique_pages.items() if info.get("qid") is None)
    overlap_sets = compute_overlap_sets(
        multiplicity,
        no_qid,
        accepted_direct_qids=boundaries.accepted_direct_qids,
        alternative_union_qids=boundaries.alternative_union_qids,
    )
    accepted_label_index = build_accepted_label_index(
        boundaries.accepted_universe.accepted_auto_admit_identities
    )
    title_signal_rows = []
    for pid, info in sorted(unique_pages.items()):
        if info.get("qid") in overlap_sets.accepted_direct_qid_overlap:
            continue
        category, owners = classify_title_signal(
            info["title"], accepted_label_index=accepted_label_index
        )
        title_signal_rows.append(
            {
                "pageid": pid,
                "qid": info.get("qid"),
                "title": info["title"],
                "title_signal_category": str(category),
                "owner_qids": list(owners),
            }
        )
    incremental_by_stratum = build_incremental_by_stratum(
        overlap_sets.incremental_qid_lead, multiplicity, unique_pages
    )
    sample = select_deterministic_sample(incremental_by_stratum)
    request_ceiling_summary = build_request_ceiling_summary(
        wikipedia_request_count=5, wikidata_request_count=1
    )

    document = build_discovery_manifest_document(
        generated_at="2026-08-25T00:00:00+00:00",
        source_id="SRC_WIKIPEDIA_API_2026",
        rights_gate={"wikipedia_research_lead": "allowed"},
        boundaries=boundaries,
        category_records=records,
        unique_pages=unique_pages,
        qid_multiplicity=multiplicity,
        no_qid_pageids=no_qid,
        overlap_sets=overlap_sets,
        title_signal_rows=title_signal_rows,
        incremental_by_stratum=incremental_by_stratum,
        sample=sample,
        request_ceiling_summary=request_ceiling_summary,
    )
    return document, (
        boundaries,
        overlap_sets,
        incremental_by_stratum,
        sample,
        unique_pages,
        accepted_label_index,
    )


def test_build_and_verify_discovery_manifest_round_trip() -> None:
    document, bundle = _build_minimal_discovery_manifest()
    boundaries, overlap_sets, incremental_by_stratum, sample, unique_pages, accepted_label_index = (
        bundle
    )

    assert verify_immutable_boundaries_reference_self_consistency(document, boundaries) == []
    for name, record in document["categories"].items():
        assert verify_category_record_self_consistency(name, record) == []
    assert verify_unique_pages_reconstruction_self_consistency(document) == []
    assert (
        verify_discovery_manifest_derived_sets_self_consistency(
            document,
            overlap_sets=overlap_sets,
            incremental_by_stratum=incremental_by_stratum,
            sample=sample,
        )
        == []
    )
    assert verify_sample_selection_self_consistency(incremental_by_stratum, sample) == []
    assert (
        verify_title_signal_rows_self_consistency(
            document, unique_pages, overlap_sets, accepted_label_index
        )
        == []
    )

    reconstructed = reconstruct_unique_pages_from_manifest(document)
    assert reconstructed[2]["qid"] == "Q900000001"


def test_verify_immutable_boundaries_reference_rejects_tampered_count() -> None:
    document, bundle = _build_minimal_discovery_manifest()
    boundaries = bundle[0]
    document["immutable_boundaries"]["retained_historical_crosswalk_count"] = 9999
    mismatches = verify_immutable_boundaries_reference_self_consistency(document, boundaries)
    assert any("retained_historical_crosswalk_count" in m for m in mismatches)


def test_verify_category_record_rejects_tampered_member_count() -> None:
    document, _ = _build_minimal_discovery_manifest()
    document["categories"][KEELBOATS]["member_count"] = 999
    mismatches = verify_category_record_self_consistency(
        KEELBOATS, document["categories"][KEELBOATS]
    )
    assert any("member_count" in m for m in mismatches)


def test_verify_unique_pages_reconstruction_rejects_tampered_title() -> None:
    document, _ = _build_minimal_discovery_manifest()
    document["unique_pages"]["1"]["title"] = "Tampered Title"
    mismatches = verify_unique_pages_reconstruction_self_consistency(document)
    assert any("title" in m for m in mismatches)


def test_verify_discovery_manifest_derived_sets_rejects_tampered_overlap_qids() -> None:
    document, bundle = _build_minimal_discovery_manifest()
    _, overlap_sets, incremental_by_stratum, sample, _, _ = bundle
    document["overlap_sets"]["incremental_qid_lead"]["qids"] = ["Q999999"]
    mismatches = verify_discovery_manifest_derived_sets_self_consistency(
        document,
        overlap_sets=overlap_sets,
        incremental_by_stratum=incremental_by_stratum,
        sample=sample,
    )
    assert any("incremental_qid_lead" in m for m in mismatches)


def test_verify_title_signal_rows_rejects_tampered_category() -> None:
    document, bundle = _build_minimal_discovery_manifest()
    _, overlap_sets, _, _, unique_pages, accepted_label_index = bundle
    for row in document["title_signal"]["rows"]:
        row["title_signal_category"] = "no_exact_signal"
    mismatches = verify_title_signal_rows_self_consistency(
        document, unique_pages, overlap_sets, accepted_label_index
    )
    # At least the rows whose true category isn't no_exact_signal must be flagged,
    # or the totals block (recomputed from the true classification) must mismatch.
    assert mismatches


# ---------------------------------------------------------------------------
# Quality-sample document assembly
# ---------------------------------------------------------------------------


def test_build_quality_sample_document_requires_exact_selection_coverage() -> None:
    boundaries = _synthetic_boundaries()
    sample = SampleSelection(selected_by_stratum={TRIMARANS: ("Q900",)}, selected_qids=("Q900",))
    with pytest.raises(ValueError, match="does not exactly cover"):
        build_quality_sample_document(
            generated_at="x",
            boundaries=boundaries,
            sample=sample,
            wikidata_context_rows=[],
            quality_rows=[],
            rights_access_ok=True,
            unique_incremental_count=1,
        )


def test_build_quality_sample_document_rejects_invalid_tag() -> None:
    boundaries = _synthetic_boundaries()
    sample = SampleSelection(selected_by_stratum={TRIMARANS: ("Q900",)}, selected_qids=("Q900",))
    with pytest.raises(ValueError, match="invalid quality_tag"):
        build_quality_sample_document(
            generated_at="x",
            boundaries=boundaries,
            sample=sample,
            wikidata_context_rows=[],
            quality_rows=[{"qid": "Q900", "quality_tag": "not_a_real_tag", "rationale": "x"}],
            rights_access_ok=True,
            unique_incremental_count=1,
        )


def test_build_quality_sample_document_rejects_empty_rationale() -> None:
    boundaries = _synthetic_boundaries()
    sample = SampleSelection(selected_by_stratum={TRIMARANS: ("Q900",)}, selected_qids=("Q900",))
    with pytest.raises(ValueError, match="rationale"):
        build_quality_sample_document(
            generated_at="x",
            boundaries=boundaries,
            sample=sample,
            wikidata_context_rows=[],
            quality_rows=[
                {"qid": "Q900", "quality_tag": str(QualityTag.AMBIGUOUS), "rationale": "   "}
            ],
            rights_access_ok=True,
            unique_incremental_count=1,
        )


def test_build_and_verify_quality_sample_document_round_trip() -> None:
    boundaries = _synthetic_boundaries()
    sample = SampleSelection(
        selected_by_stratum={TRIMARANS: ("Q900", "Q901")}, selected_qids=("Q900", "Q901")
    )
    quality_rows = [
        {
            "qid": "Q900",
            "quality_tag": str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD),
            "rationale": "Named production sailboat class per retained description.",
        },
        {
            "qid": "Q901",
            "quality_tag": str(QualityTag.OBVIOUS_OUT_OF_SCOPE),
            "rationale": "Retained P31 indicates an individual vessel, not a class.",
        },
    ]
    document = build_quality_sample_document(
        generated_at="2026-08-25T00:00:00+00:00",
        boundaries=boundaries,
        sample=sample,
        wikidata_context_rows=[{"qid": "Q900"}, {"qid": "Q901"}],
        quality_rows=quality_rows,
        rights_access_ok=True,
        unique_incremental_count=150,
    )
    assert document["quality_tag_counts"][str(QualityTag.PLAUSIBLE_MODEL_OR_CLASS_LEAD)] == 1
    assert document["recommendation"] == str(Recommendation.FOLLOWUP_VERIFICATION_CANDIDATE)
    assert verify_quality_sample_self_consistency(document, unique_incremental_count=150) == []


def test_verify_quality_sample_rejects_tampered_recommendation() -> None:
    boundaries = _synthetic_boundaries()
    sample = SampleSelection(selected_by_stratum={TRIMARANS: ("Q900",)}, selected_qids=("Q900",))
    document = build_quality_sample_document(
        generated_at="x",
        boundaries=boundaries,
        sample=sample,
        wikidata_context_rows=[],
        quality_rows=[
            {"qid": "Q900", "quality_tag": str(QualityTag.AMBIGUOUS), "rationale": "unclear"}
        ],
        rights_access_ok=True,
        unique_incremental_count=50,
    )
    document["recommendation"] = str(Recommendation.FOLLOWUP_VERIFICATION_CANDIDATE)
    mismatches = verify_quality_sample_self_consistency(document, unique_incremental_count=50)
    assert any("recommendation" in m for m in mismatches)
