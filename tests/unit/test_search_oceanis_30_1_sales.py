"""Unit tests for scripts/search_oceanis_30_1_sales.py — SLICE-0038.

Covers the primary slice's required tests plus the binding pre-start
aggregator addendum's required adversarial additions
(`docs/slices/SLICE-0038-prestart-aggregator-addendum.md`). All tests run
offline against the retained real (trimmed) 2026-08-31 Owning sample or
small inline synthetic listing dicts — no network access, matching "CI must
not depend on live network availability."
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import jsonschema
import pytest

from hullq.search.types import TruthState
from hullq.search.values import ValueQualification
from scripts.search_oceanis_30_1 import DEEP_KEEL, RETRACTABLE_KEEL, SHALLOW_KEEL
from scripts.search_oceanis_30_1_sales import (
    EXPECTED_DESIGN_ID,
    RETAINED_SAMPLE_PATH,
    AssessedOffer,
    RegressionError,
    admit_boat_design_identity,
    assess_candidate,
    load_owning_candidates_offline,
    main,
    normalize_listing,
    qualify_listing_draft,
    run_design_search_first,
    run_owner_test,
)

MARKET_LISTING_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2] / "specs" / "MARKET_LISTING_SCHEMA.v0.1.json"
)


@pytest.fixture(scope="module")
def market_listing_schema() -> dict[str, Any]:
    return json.loads(MARKET_LISTING_SCHEMA_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def retained_candidates() -> list[dict[str, Any]]:
    candidates, _metadata = load_owning_candidates_offline()
    return candidates


def _listing(**overrides: Any) -> dict[str, Any]:
    """A minimal synthetic Owning-shaped listing for adversarial draft tests."""
    base: dict[str, Any] = {
        "id": "lst_TEST",
        "slug": "beneteau-oceanis-30-1-test",
        "title": "Beneteau Oceanis 30.1",
        "price": {"amount": 100000, "currency": "EUR", "negotiable": True},
        "location": {"country": "FR", "city": "La Rochelle", "shipping": False},
        "seller": {"name": "Owning Marketplace", "type": "agent"},
        "attributes": {"brand": "beneteau", "model": "Oceanis 30.1"},
        "boat_specs": None,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# Required Behavior A — SLICE-0037 Q10 path is actually invoked
# ---------------------------------------------------------------------------


def test_design_search_first_reproduces_accepted_slice_0037_result() -> None:
    proof = run_design_search_first()
    assert proof.is_fixture is False
    assert proof.evaluation.design_id == EXPECTED_DESIGN_ID
    assert proof.evaluation.result_class.value == "CONFIRMED_MATCH"
    assert tuple(proof.evaluation.matching_configuration_ids) == (SHALLOW_KEEL,)
    truths = {ce.configuration_id: ce.truth for ce in proof.evaluation.configuration_evaluations}
    assert truths[DEEP_KEEL] is TruthState.FALSE
    assert truths[RETRACTABLE_KEEL] is TruthState.UNKNOWN
    assert truths[SHALLOW_KEEL] is TruthState.TRUE
    assert proof.draft_criterion.field == "draft_max_m"
    assert proof.draft_criterion.threshold_max == 1.60


def test_design_search_first_regression_error_on_tampered_outcome(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A hypothetical future regression in the Search kernel must stop, not be papered over."""
    import scripts.search_oceanis_30_1_sales as module

    # Simulate a regressed matching_configuration_ids by monkeypatching the
    # outcome the real kernel call returns, without touching the kernel itself.
    real_run = module.run_configuration_query

    class _TamperedEvaluation:
        def __init__(self, real_eval: Any) -> None:
            self.design_id = real_eval.design_id
            self.result_class = real_eval.result_class
            self.matching_configuration_ids = ()  # tampered: drop the real match
            self.configuration_evaluations = real_eval.configuration_evaluations

    class _TamperedOutcome:
        def __init__(self, real_outcome: Any) -> None:
            tampered = tuple(_TamperedEvaluation(e) for e in real_outcome.confirmed_matches)
            self.confirmed_matches = tampered
            self.confirmed_non_matches = real_outcome.confirmed_non_matches
            self.insufficient_data = real_outcome.insufficient_data

    def _tampered_run_configuration_query(query: Any, design_sets: Any) -> Any:
        return _TamperedOutcome(real_run(query, design_sets))

    monkeypatch.setattr(module, "run_configuration_query", _tampered_run_configuration_query)
    with pytest.raises(RegressionError, match="matching_configuration_ids regressed"):
        run_design_search_first()


# ---------------------------------------------------------------------------
# Retained-sample parsing / normalization
# ---------------------------------------------------------------------------


def test_retained_sample_loads_ten_real_candidates(
    retained_candidates: list[dict[str, Any]],
) -> None:
    assert len(retained_candidates) == 10


def test_retained_sample_has_no_images_description_or_contact_data(
    retained_candidates: list[dict[str, Any]],
) -> None:
    for raw in retained_candidates:
        assert "images" not in raw
        assert "description" not in raw
        assert "long_description" not in raw
        assert "tags" not in raw


def test_canonical_listings_validate_against_market_listing_schema(
    retained_candidates: list[dict[str, Any]], market_listing_schema: dict[str, Any]
) -> None:
    for raw in retained_candidates:
        canonical = normalize_listing(raw, observed_at="2026-08-31T21:33:49Z")
        jsonschema.validate(instance=canonical, schema=market_listing_schema)


def test_canonical_listing_url_always_points_at_owning_never_upstream_portal(
    retained_candidates: list[dict[str, Any]],
) -> None:
    """Addendum requirement 6: upstream attribution never authorizes fetching it.

    Retained sample results deliberately keep only `boat_specs.source.portals`
    (portal names), never `original_urls`; independently, every canonical
    `url` this pilot produces must stay on the Owning domain.
    """
    for raw in retained_candidates:
        assert "original_urls" not in ((raw.get("boat_specs") or {}).get("source") or {})
        canonical = normalize_listing(raw, observed_at="2026-08-31T21:33:49Z")
        assert canonical["url"].startswith("https://owning.pro/")


def test_retained_sample_identity_admission_matches_manual_audit(
    retained_candidates: list[dict[str, Any]],
) -> None:
    """Real observed 2026-08-31 split: 7 identity-admitted, 3 unresolved.

    The three unresolved candidates genuinely lack a structured brand/model
    attribute (native Owning listings with no `boat_specs` scrape mirror and
    no `attributes.model`) even though their free-text `title` names the
    model — this pilot does not parse title for identity (Required Behavior D
    / avoids generic free-text entity resolution).
    """
    admitted = 0
    unresolved = 0
    for raw in retained_candidates:
        canonical = normalize_listing(raw, observed_at="2026-08-31T21:33:49Z")
        if canonical["matched_boat_design_id"] == EXPECTED_DESIGN_ID:
            admitted += 1
        else:
            assert canonical["matched_boat_design_id"] is None
            unresolved += 1
    assert admitted == 7
    assert unresolved == 3


# ---------------------------------------------------------------------------
# Required Behavior D — exact BoatDesign identity admission
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [
        ("Beneteau", "Oceanis 30.1"),
        ("BENETEAU", "OCEANIS 30.1"),
        ("beneteau", "oceanis301"),
        ("beneteau", "Oceanis 30 1"),
        ("Beneteau", "Beneteau Oceanis 301"),
        ("Beneteau", "Beneteau OCEANIS 301"),
        ("Bénéteau", "Oceanis 30.1"),  # accented brand normalizes
    ],
)
def test_identity_positive_controls_admit_the_design(manufacturer: str, model: str) -> None:
    assert admit_boat_design_identity(manufacturer, model) == EXPECTED_DESIGN_ID


@pytest.mark.parametrize(
    ("manufacturer", "model"),
    [
        ("Beneteau", "Oceanis 30"),
        ("Beneteau", "Oceanis 31"),
        ("Beneteau", "Oceanis 300"),
        ("Beneteau", "Oceanis 34.1"),
        ("Beneteau", "Oceanis 38.1"),
        ("Beneteau", "First 30"),
        ("Jeanneau", "Oceanis 30.1"),  # right model text, wrong brand
        ("Beneteau", None),
        (None, "Oceanis 30.1"),
        ("Beneteau", ""),
    ],
)
def test_identity_near_neighbors_are_rejected(manufacturer: str | None, model: str | None) -> None:
    assert admit_boat_design_identity(manufacturer, model) is None


def test_search_return_membership_alone_does_not_authorize_identity() -> None:
    """A listing present in the Oceanis-30.1-targeted candidate set is still

    independently checked — being *returned by* the query is never itself
    evidence of identity (Required Behavior D).
    """
    near_neighbor_in_results = _listing(attributes={"brand": "beneteau", "model": "Oceanis 31"})
    canonical = normalize_listing(near_neighbor_in_results, observed_at="2026-08-31T00:00:00Z")
    assert canonical["matched_boat_design_id"] is None


# ---------------------------------------------------------------------------
# Required Behavior E — listing-level configuration assessment
# ---------------------------------------------------------------------------


def test_no_draft_evidence_yields_unknown() -> None:
    qualified, _evidence = qualify_listing_draft(
        _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1"})
    )
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


def test_unambiguous_shallow_draft_yields_true() -> None:
    listing = _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 1.30})
    qualified, _evidence = qualify_listing_draft(listing)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == 1.30


def test_unambiguous_deep_draft_yields_false_side_value() -> None:
    listing = _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 1.88})
    qualified, _evidence = qualify_listing_draft(listing)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == 1.88


def test_end_to_end_true_and_false_via_evaluate_numeric_leaf() -> None:
    proof = run_design_search_first()
    shallow = assess_candidate(
        _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 1.30}),
        observed_at="2026-08-31T00:00:00Z",
        draft_criterion=proof.draft_criterion,
    )
    deep = assess_candidate(
        _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 1.88}),
        observed_at="2026-08-31T00:00:00Z",
        draft_criterion=proof.draft_criterion,
    )
    assert isinstance(shallow, AssessedOffer)
    assert shallow.truth is TruthState.TRUE
    assert isinstance(deep, AssessedOffer)
    assert deep.truth is TruthState.FALSE


def test_no_evidence_listing_never_inherits_design_level_true() -> None:
    """Addendum requirement 2/3: design-level Q10 match must never leak

    into a listing that carries no evidence of its own, even though the
    confirmed design has a Q10-matching shallow configuration.
    """
    proof = run_design_search_first()
    assert proof.evaluation.result_class.value == "CONFIRMED_MATCH"  # design IS a match
    listing_without_evidence = _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1"})
    result = assess_candidate(
        listing_without_evidence,
        observed_at="2026-08-31T00:00:00Z",
        draft_criterion=proof.draft_criterion,
    )
    assert isinstance(result, AssessedOffer)
    assert result.truth is TruthState.UNKNOWN


# ---------------------------------------------------------------------------
# Addendum — nonphysical/placeholder draft must fail closed
# ---------------------------------------------------------------------------


def test_zero_draft_never_becomes_true() -> None:
    qualified, _evidence = qualify_listing_draft(
        _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 0})
    )
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


def test_negative_draft_yields_unknown() -> None:
    qualified, _evidence = qualify_listing_draft(
        _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": -1.3})
    )
    assert qualified.qualification is ValueQualification.MISSING


@pytest.mark.parametrize(
    "malformed", [True, False, math.nan, math.inf, -math.inf, "1.3", [1.3], {}]
)
def test_malformed_nonfinite_boolean_values_fail_closed(malformed: Any) -> None:
    qualified, _evidence = qualify_listing_draft(
        _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": malformed})
    )
    assert qualified.qualification is ValueQualification.MISSING
    assert qualified.value is None


def test_conflicting_observations_on_opposite_sides_of_threshold_yield_unknown() -> None:
    listing = _listing(
        attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 1.30},
        boat_specs={"specs": {"dimensions": {"draft_m": 1.90}}},
    )
    qualified, evidence = qualify_listing_draft(listing)
    assert qualified.qualification is ValueQualification.UNRESOLVED_CONFLICT
    assert "conflict" in evidence


def test_placeholder_zero_alongside_valid_value_does_not_block_the_valid_value() -> None:
    """Addendum requirement 5: an unrelated placeholder `0` must not manufacture

    truth, but it also must not silently swallow a genuinely admissible
    remaining observation.
    """
    listing = _listing(
        attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 0},
        boat_specs={"specs": {"dimensions": {"draft_m": 1.30}}},
    )
    qualified, evidence = qualify_listing_draft(listing)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == 1.30
    assert "rejected" in evidence


def test_identical_unambiguous_observations_remain_eligible() -> None:
    listing = _listing(
        attributes={"brand": "beneteau", "model": "Oceanis 30.1", "draft": 1.30},
        boat_specs={"specs": {"dimensions": {"draft_m": 1.30}}},
    )
    qualified, _evidence = qualify_listing_draft(listing)
    assert qualified.qualification is ValueQualification.CONFIRMED
    assert qualified.value == 1.30


def test_no_synonym_table_from_configuration_words() -> None:
    """Addendum requirement 7: none of deep/standard/short/shoal/shallow/lifting/swing

    may produce a configuration TRUE/FALSE merely by appearing in listing
    text — `qualify_listing_draft` never reads free text at all.
    """
    listing = _listing(attributes={"brand": "beneteau", "model": "Oceanis 30.1"})
    listing["title"] = (
        "Beneteau Oceanis 30.1 - deep standard shoal shallow lifting swing keel version"
    )
    qualified, _evidence = qualify_listing_draft(listing)
    assert qualified.qualification is ValueQualification.MISSING


# ---------------------------------------------------------------------------
# Zero-offer BLOCKED outcome
# ---------------------------------------------------------------------------


def test_zero_admitted_offers_is_blocked_not_fabricated(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import scripts.search_oceanis_30_1_sales as module

    def _empty_offline() -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return [], {
            "endpoint": "https://api.owning.pro/api/listings",
            "query_params": {},
            "accessed_at": "2026-08-31T00:00:00Z",
            "pagination": {"total": 0},
        }

    monkeypatch.setattr(module, "load_owning_candidates_offline", _empty_offline)
    exit_code = run_owner_test(live=False)
    assert exit_code == 1
    assert "BLOCKED" in capsys.readouterr().out


def test_zero_candidates_at_all_is_also_blocked(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    import scripts.search_oceanis_30_1_sales as module

    def _no_candidates() -> tuple[list[dict[str, Any]], dict[str, Any]]:
        return [], {
            "endpoint": "https://api.owning.pro/api/listings",
            "query_params": {},
            "accessed_at": "2026-08-31T00:00:00Z",
            "pagination": {"total": 0},
        }

    monkeypatch.setattr(module, "load_owning_candidates_offline", _no_candidates)
    exit_code = main([])
    assert exit_code == 1
    assert "BLOCKED" in capsys.readouterr().out


def test_offline_default_run_succeeds_and_reproduces_real_split(
    capsys: pytest.CaptureFixture[str],
) -> None:
    exit_code = main([])
    out = capsys.readouterr().out
    assert exit_code == 0
    assert "identity_admitted_offers=7" in out
    assert "identity_unresolved_candidates=3" in out
    assert "TRUE=0 FALSE=0 UNKNOWN=7" in out
    assert "DESIGN MATCH: Oceanis 30.1 has a Q10-matching factory configuration" in out
    assert "LISTING CONFIG: independently assessed from this physical listing only" in out


def test_retained_sample_path_exists() -> None:
    assert RETAINED_SAMPLE_PATH.exists()
