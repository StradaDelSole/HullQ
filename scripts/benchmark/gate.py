"""Pure G3 gate evaluator — SLICE-0015.

Extracted so both runner.py and the test suite call the SAME decision function,
preventing logic divergence between production and test code.

All threshold constants are pre-committed and must not change after results are observed.
"""

from __future__ import annotations

import dataclasses
from typing import Any

# ---------------------------------------------------------------------------
# Pre-committed G3 thresholds — do not change after results are known
# ---------------------------------------------------------------------------

G3_MATERIALIZATION_MIN_PCT: float = 65.0  # mechanical materialization: >= this value
G3_CANNOT_MAX_PCT: float = 10.0  # cannot-materialize-without-invention: <= this value
G3_REVIEW_MAX_PCT: float = 35.0  # review-required cases: <= this value

# Sentinel strings for non-runtime-measurable scorecard fields
GUARD_VERIFIED = "GUARD_VERIFIED"
NOT_MEASURED = "NOT_MEASURED"


@dataclasses.dataclass(frozen=True)
class GateMetricResult:
    """Evaluation of one binding G3 scorecard metric."""

    name: str
    measured: int | float | str
    threshold: str
    status: str  # "PASS" | "FAIL" | "NOT_MEASURED"
    evidence_basis: str  # "DIRECT_RUNTIME" | "VERIFIED_INVARIANT" | "NOT_MEASURED"


@dataclasses.dataclass(frozen=True)
class G3GateResult:
    """Complete G3 scorecard evaluation from a single evaluate_g3_gate() call."""

    recommendation: str  # "G3_PASS" | "HARDEN_FIRST" | "BLOCKED"
    rationale: str
    scorecard: tuple[GateMetricResult, ...]
    all_correctness_pass: bool
    materialization_pct: float
    cannot_pct: float
    review_pct: float
    contract_gap_count: int

    def scorecard_as_dicts(self) -> list[dict[str, Any]]:
        return [dataclasses.asdict(m) for m in self.scorecard]


def evaluate_g3_gate(
    *,
    total_cases: int,
    materialized: int,
    review_required: int,
    cannot_materialize: int,
    contract_gap_count: int,
    first_pass_imported: int,
    reimport_already_imported: int,
    fresh_run_imported: int,
    readback_mismatches: int,
    fresh_run_semantic_mismatches: int,
    first_pass_conflict: int = 0,
    first_pass_error: int = 0,
    reimport_conflict: int = 0,
    reimport_error: int = 0,
) -> G3GateResult:
    """Evaluate the Stage-2 Gate G3 scorecard against pre-committed thresholds.

    Pure function — no side effects. Call this from runner.py and from tests.

    Gate priority (first failing gate determines recommendation):
      1. CONTRACT_GAP count > 0 → BLOCKED.
      2. Any zero-tolerance correctness violation → HARDEN_FIRST.
      3. Mechanical materialization < 65% → HARDEN_FIRST.
      4. Cannot-materialize-without-invention > 10% → HARDEN_FIRST.
      5. Review-required > 35% → HARDEN_FIRST.
      6. All gates satisfied → G3_PASS.
    """
    # --- Rate calculations (percentage against total_cases) ---
    mat_pct = 100.0 * materialized / total_cases if total_cases > 0 else 0.0
    cannot_pct = 100.0 * cannot_materialize / total_cases if total_cases > 0 else 0.0
    review_pct = 100.0 * review_required / total_cases if total_cases > 0 else 0.0

    unexpected_errors = first_pass_error + reimport_error
    membership_anomalies = first_pass_conflict + reimport_conflict

    # --- Zero-tolerance correctness gates ---
    reimport_fraction = f"{reimport_already_imported}/{materialized}" if materialized > 0 else "N/A"
    fresh_fraction = f"{fresh_run_imported}/{materialized}" if materialized > 0 else "N/A"

    correctness_gates: list[GateMetricResult] = [
        GateMetricResult(
            name="readback_semantic_mismatches",
            measured=readback_mismatches,
            threshold="= 0",
            status="PASS" if readback_mismatches == 0 else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="nondeterministic_semantic_output",
            measured=fresh_run_semantic_mismatches,
            threshold="= 0",
            status="PASS" if fresh_run_semantic_mismatches == 0 else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="unexpected_persistence_errors",
            measured=unexpected_errors,
            threshold="= 0",
            status="PASS" if unexpected_errors == 0 else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="duplicate_membership_anomalies",
            measured=membership_anomalies,
            threshold="= 0",
            status="PASS" if membership_anomalies == 0 else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="exact_reimport_idempotency",
            measured=reimport_fraction,
            threshold="= 100%",
            status="PASS" if reimport_already_imported == materialized else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="fresh_db_semantic_equality",
            measured=fresh_fraction,
            threshold="= 100%",
            status="PASS" if fresh_run_imported == materialized else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="invented_force_resolved_values",
            measured=GUARD_VERIFIED,
            threshold="= 0",
            status="PASS",
            evidence_basis="VERIFIED_INVARIANT",
        ),
        GateMetricResult(
            name="sailboatdata_value_contamination",
            measured=GUARD_VERIFIED,
            threshold="= 0",
            status="PASS",
            evidence_basis="VERIFIED_INVARIANT",
        ),
    ]

    all_correctness_pass = all(g.status == "PASS" for g in correctness_gates)

    # --- Scale / review gates ---
    scale_gates: list[GateMetricResult] = [
        GateMetricResult(
            name="mechanical_materialization_pct",
            measured=round(mat_pct, 1),
            threshold=f">= {G3_MATERIALIZATION_MIN_PCT}%",
            status="PASS" if mat_pct >= G3_MATERIALIZATION_MIN_PCT else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="cannot_materialize_without_invention_pct",
            measured=round(cannot_pct, 1),
            threshold=f"<= {G3_CANNOT_MAX_PCT}%",
            status="PASS" if cannot_pct <= G3_CANNOT_MAX_PCT else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="review_required_pct",
            measured=round(review_pct, 1),
            threshold=f"<= {G3_REVIEW_MAX_PCT}%",
            status="PASS" if review_pct <= G3_REVIEW_MAX_PCT else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
        GateMetricResult(
            name="median_reviewer_time_per_case_min",
            measured=NOT_MEASURED,
            threshold="<= 3 min (where directly measurable)",
            status=NOT_MEASURED,
            evidence_basis=NOT_MEASURED,
        ),
        GateMetricResult(
            name="avg_human_effort_per_design_min",
            measured=NOT_MEASURED,
            threshold="<= 1.5 min (where directly measurable)",
            status=NOT_MEASURED,
            evidence_basis=NOT_MEASURED,
        ),
        GateMetricResult(
            name="contract_gap_count",
            measured=contract_gap_count,
            threshold="= 0",
            status="PASS" if contract_gap_count == 0 else "FAIL",
            evidence_basis="DIRECT_RUNTIME",
        ),
    ]

    scorecard = tuple(correctness_gates + scale_gates)

    # --- Recommendation derivation (priority-ordered) ---
    if contract_gap_count > 0:
        recommendation = "BLOCKED"
        rationale = (
            f"BLOCKED: {contract_gap_count} CONTRACT_GAP failure(s) — accepted domain "
            f"contracts cannot faithfully represent retained benchmark reality for those cases. "
            f"Materialization={materialized}/{total_cases} ({mat_pct:.1f}%), "
            f"cannot_materialize={cannot_materialize} ({cannot_pct:.1f}%), "
            f"readback_mismatches={readback_mismatches}, "
            f"fresh_semantic_mismatches={fresh_run_semantic_mismatches}."
        )
    elif not all_correctness_pass:
        failing = [g.name for g in correctness_gates if g.status == "FAIL"]
        recommendation = "HARDEN_FIRST"
        rationale = (
            f"HARDEN_FIRST: zero-tolerance correctness gate(s) failed: {failing}. "
            f"Materialization={materialized}/{total_cases} ({mat_pct:.1f}%), "
            f"readback_mismatches={readback_mismatches}, "
            f"fresh_semantic_mismatches={fresh_run_semantic_mismatches}."
        )
    elif mat_pct < G3_MATERIALIZATION_MIN_PCT:
        recommendation = "HARDEN_FIRST"
        rationale = (
            f"HARDEN_FIRST: mechanical materialization {mat_pct:.1f}% "
            f"< {G3_MATERIALIZATION_MIN_PCT}% threshold. "
            f"Materialized={materialized}/{total_cases}. "
            f"Cannot-materialize={cannot_materialize} ({cannot_pct:.1f}%)."
        )
    elif cannot_pct > G3_CANNOT_MAX_PCT:
        recommendation = "HARDEN_FIRST"
        rationale = (
            f"HARDEN_FIRST: cannot-materialize-without-invention {cannot_pct:.1f}% "
            f"> {G3_CANNOT_MAX_PCT}% threshold. "
            f"Cannot_materialize={cannot_materialize}/{total_cases}."
        )
    elif review_pct > G3_REVIEW_MAX_PCT:
        recommendation = "HARDEN_FIRST"
        rationale = (
            f"HARDEN_FIRST: review-required {review_pct:.1f}% "
            f"> {G3_REVIEW_MAX_PCT}% threshold. "
            f"Review_required={review_required}/{total_cases}."
        )
    else:
        recommendation = "G3_PASS"
        rationale = (
            f"G3_PASS: all zero-tolerance correctness gates satisfied. "
            f"Mechanical materialization={materialized}/{total_cases} ({mat_pct:.1f}%, "
            f">= {G3_MATERIALIZATION_MIN_PCT}%). "
            f"Cannot-materialize-without-invention={cannot_materialize} ({cannot_pct:.1f}%, "
            f"<= {G3_CANNOT_MAX_PCT}%). "
            f"Review-required={review_required} ({review_pct:.1f}%, "
            f"<= {G3_REVIEW_MAX_PCT}%). "
            f"No fundamental CONTRACT_GAP discovered. "
            f"Reviewer timing: NOT_MEASURED (benchmark uses pre-curated retained evidence). "
            f"Technical G3_PASS recommendation only — project-owner acceptance required "
            f"before operational G3 passage. No broader bootstrap is authorized."
        )

    return G3GateResult(
        recommendation=recommendation,
        rationale=rationale,
        scorecard=scorecard,
        all_correctness_pass=all_correctness_pass,
        materialization_pct=mat_pct,
        cannot_pct=cannot_pct,
        review_pct=review_pct,
        contract_gap_count=contract_gap_count,
    )
