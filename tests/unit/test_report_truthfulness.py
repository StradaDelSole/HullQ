"""Report truthfulness tests — SLICE-0015 third correction round.

Proves that _write_report() generates only factually correct statements for
both partial-materialization G3_PASS (49/50) and full-materialization G3_PASS
(50/50).

These are the binding report-generation semantics:
  - If materialized < total_cases, the report must reflect actual counts and
    must NOT claim all cases materialized.
  - If materialized == total_cases, the report may accurately state that all
    cases materialized.
  - The report must always state the technical G3_PASS recommendation.
  - Project-owner acceptance / no-bootstrap language must be intact.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))

from benchmark.gate import evaluate_g3_gate  # noqa: E402
from benchmark.runner import _write_report  # noqa: E402


def _minimal_result_doc(
    *,
    total_cases: int,
    materialized: int,
    review_required: int,
    validation_failure_count: int = 0,
    insufficient_retained_fact_count: int = 0,
    contract_gap_count: int = 0,
) -> dict[str, Any]:
    """Build a minimal result_doc for report-truthfulness testing.

    Uses evaluate_g3_gate() to derive the real recommendation and scorecard so
    the result_doc is internally consistent (same gate function as runner.py).
    """
    cannot_materialize = (
        validation_failure_count + insufficient_retained_fact_count + contract_gap_count
    )
    gate_result = evaluate_g3_gate(
        total_cases=total_cases,
        materialized=materialized,
        review_required=review_required,
        contract_gap_count=contract_gap_count,
        validation_failure_count=validation_failure_count,
        insufficient_retained_fact_count=insufficient_retained_fact_count,
        first_pass_imported=materialized,
        reimport_already_imported=materialized,
        fresh_run_imported=materialized,
        readback_mismatches=0,
        fresh_run_semantic_mismatches=0,
    )
    return {
        "schema_version": "0015-v1",
        "benchmark_version": "test",
        "run_timestamp": "2026-01-01T00:00:00Z",
        "git_sha": "test-sha",
        "environment": {
            "python_version": "3.14.0",
            "postgresql_version": "18.0",
        },
        "corpus_materialization": {
            "total_cases": total_cases,
            "materialized": materialized,
            "review_required": review_required,
            "cannot_materialize": cannot_materialize,
            "review_required_reasons": {},
            "contract_gap_count": contract_gap_count,
            "validation_failure_count": validation_failure_count,
            "insufficient_retained_fact_count": insufficient_retained_fact_count,
        },
        "persistence": {
            "valid_bundles_submitted": materialized,
            "first_pass_imported": materialized,
            "first_pass_conflict": 0,
            "first_pass_error": 0,
            "reimport_already_imported": materialized,
            "reimport_conflict": 0,
            "reimport_error": 0,
            "readback_mismatches": 0,
            "fresh_run_imported": materialized,
            "fresh_run_semantic_mismatches": 0,
            "fresh_run_error": 0,
        },
        "promotion_applicability": {
            "eligible_for_promotion": 0,
            "pre_canonical_unresolved": materialized,
            "promotion_blocked_by_conflict": 0,
        },
        "throughput": {
            "wall_clock_import_seconds": "NOT_MEASURED",
            "reimport_seconds": "NOT_MEASURED",
            "cases_per_second": "NOT_MEASURED",
        },
        "human_review_burden": {
            "review_required_cases": review_required,
            "review_decisions_required": review_required + cannot_materialize,
            "elapsed_reviewer_minutes": "NOT_MEASURED",
        },
        "recommendation": gate_result.recommendation,
        "recommendation_rationale": gate_result.rationale,
        "automation_rate_disclaimer": "",
        "g3_scorecard": gate_result.scorecard_as_dicts(),
    }


# ---------------------------------------------------------------------------
# Case A — partial-materialization G3_PASS (49/50 + 1 INSUFFICIENT_RETAINED_FACT)
# ---------------------------------------------------------------------------


def test_write_report_partial_materialization_g3_pass_is_truthful(tmp_path: Path) -> None:
    """Case A: 49/50 with 1 INSUFFICIENT_RETAINED_FACT → G3_PASS report must not claim 50/50.

    The report:
    - must NOT contain a false claim equivalent to 'All 50 benchmark cases materialized';
    - must reflect the actual 49/50 materialization state;
    - must clearly state technical G3_PASS;
    - must retain project-owner acceptance / no-bootstrap language.
    """
    result_doc = _minimal_result_doc(
        total_cases=50,
        materialized=49,
        review_required=0,
        insufficient_retained_fact_count=1,
        validation_failure_count=0,
        contract_gap_count=0,
    )
    assert result_doc["recommendation"] == "G3_PASS", (
        f"Gate must produce G3_PASS for 49/50 + 1 INSUFFICIENT_RETAINED_FACT (2% ≤ 10%); "
        f"got {result_doc['recommendation']!r}. Rationale: {result_doc['recommendation_rationale']}"
    )

    report_path = tmp_path / "partial-g3-pass-report.md"
    _write_report(result_doc, report_path)
    report_text = report_path.read_text(encoding="utf-8")

    # The false claim must not appear
    assert "All 50 benchmark cases materialized" not in report_text, (
        "Report falsely claims all 50 cases materialized when only 49/50 did.\n"
        f"Report excerpt:\n{report_text[:600]}"
    )

    # The actual materialized count must appear
    assert "49" in report_text, (
        "Report must reflect the actual materialized count (49) for a 49/50 case.\n"
        f"Report excerpt:\n{report_text[:600]}"
    )

    # G3_PASS must be stated
    assert "G3_PASS" in report_text, (
        "Report must state the technical G3_PASS recommendation.\n"
        f"Report excerpt:\n{report_text[:600]}"
    )

    # Project-owner acceptance language must remain intact
    assert "project-owner acceptance" in report_text, (
        "Report must retain project-owner acceptance language.\n"
        f"Report excerpt:\n{report_text[:600]}"
    )

    # No-bootstrap language must remain intact
    assert "bootstrap" in report_text.lower(), (
        f"Report must retain no-bootstrap language.\nReport excerpt:\n{report_text[:600]}"
    )


# ---------------------------------------------------------------------------
# Case B — full 50/50 G3_PASS
# ---------------------------------------------------------------------------


def test_write_report_full_50_50_g3_pass_may_state_all_materialized(tmp_path: Path) -> None:
    """Case B: 50/50 → G3_PASS report may accurately state all 50 cases materialized.

    When materialized == total_cases, the all-N-cases-materialized statement is truthful
    and is permitted (though not required).  The report must still state G3_PASS and
    retain acceptance / no-bootstrap language.
    """
    result_doc = _minimal_result_doc(
        total_cases=50,
        materialized=50,
        review_required=0,
        validation_failure_count=0,
        insufficient_retained_fact_count=0,
        contract_gap_count=0,
    )
    assert result_doc["recommendation"] == "G3_PASS"

    report_path = tmp_path / "full-g3-pass-report.md"
    _write_report(result_doc, report_path)
    report_text = report_path.read_text(encoding="utf-8")

    # For 50/50 the all-50 statement is truthful — verify a count appears
    assert "50" in report_text, "Report for a 50/50 run must mention the count 50."
    assert "G3_PASS" in report_text, "Report must state the G3_PASS recommendation."
    assert "project-owner acceptance" in report_text
    assert "bootstrap" in report_text.lower()
