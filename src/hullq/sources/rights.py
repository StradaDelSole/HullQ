"""Source-rights gate — SLICE-0007.

Implements the deterministic, fail-closed source-use decision gate required
by ADR-0005, SOURCE_RIGHTS_POLICY.v0.1.md and REQ-RESEARCH-005 through -009.

Core invariants:
- Access is not reuse; they are checked independently (SR-001).
- Clearance is use-specific across seven named uses (SR-002).
- Production, bulk, automation and redistribution fail closed for
  unknown/unassessed/review/prohibited/unresolved-conditional states (SR-003).
- Conditional clearance is never automatically allowed by this gate.
- Underlying permission prohibitions override use-specific clearance (rule 5).
- Obligations remain machine-visible in all gate outcomes (REQ-RESEARCH-009).
- Source prestige, license name, and public accessibility do not grant rights.
- No network acquisition is performed; no source-authority ranking is applied.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

__all__ = [
    "DecisionOutcome",
    "DecisionReason",
    "ExtractionBudget",
    "JobRouting",
    "ObligationSummary",
    "SourceUsageMetrics",
    "SourceUse",
    "SourceUseDecision",
    "check_source_use",
    "route_research_job",
]


class SourceUse(StrEnum):
    """Seven HullQ use-specific clearance keys matching SOURCE_SCHEMA.v0.2 clearance vocabulary."""

    RESEARCH_REFERENCE = "research_reference"
    RESEARCH_LEAD = "research_lead"
    IDENTITY_SEED = "identity_seed"
    PRODUCTION_VALUE = "production_value"
    BULK_BOOTSTRAP = "bulk_bootstrap"
    AUTOMATED_INGESTION = "automated_ingestion"
    ARTIFACT_REDISTRIBUTION = "artifact_redistribution"


class DecisionOutcome(StrEnum):
    ALLOWED = "allowed"
    BLOCKED = "blocked"
    LEGAL_REVIEW_REQUIRED = "legal_review_required"
    CONDITIONAL = "conditional"
    UNKNOWN_UNASSESSED = "unknown_unassessed"


class DecisionReason(StrEnum):
    """Machine-readable reason codes for gate decisions.

    Callers and tests MUST use these codes to decide behavior; they must not
    parse human-readable prose to determine the outcome.
    """

    CLEARANCE_ALLOWED = "clearance_allowed"
    CLEARANCE_PROHIBITED = "clearance_prohibited"
    CLEARANCE_LEGAL_REVIEW_REQUIRED = "clearance_legal_review_required"
    CLEARANCE_CONDITIONAL = "clearance_conditional"
    CLEARANCE_UNKNOWN = "clearance_unknown"
    SOURCE_UNASSESSED = "source_unassessed"
    AUTOMATED_ACCESS_PROHIBITED = "automated_access_prohibited"
    AUTOMATED_ACCESS_UNKNOWN = "automated_access_unknown"
    AUTOMATED_ACCESS_CONDITIONAL = "automated_access_conditional"
    PERMISSION_CONFLICT_STORE_CANONICAL = "permission_conflict_store_canonical"
    PERMISSION_CONFLICT_BULK_INGEST = "permission_conflict_bulk_ingest"
    PERMISSION_CONFLICT_AUTOMATED_EXTRACT = "permission_conflict_automated_extract"
    PERMISSION_CONFLICT_REDISTRIBUTE = "permission_conflict_redistribute"
    PERMISSION_CONFLICT_COMMERCIAL = "permission_conflict_commercial"
    EXTRACTION_THRESHOLD_EXCEEDED = "extraction_threshold_exceeded"
    MISSING_TELEMETRY_CONTEXT = "missing_telemetry_context"
    SHARE_ALIKE_UNRESOLVED = "share_alike_unresolved"


@dataclass(frozen=True)
class ObligationSummary:
    """Machine-addressable obligations extracted from the Source Rights Profile."""

    attribution_required: str
    share_alike: str
    notice_required: str
    attribution_instructions: str | None
    other_conditions: tuple[str, ...]


@dataclass(frozen=True)
class SourceUseDecision:
    """Deterministic, immutable result of a source-use gate evaluation."""

    source_id: str
    use: SourceUse
    outcome: DecisionOutcome
    reasons: frozenset[DecisionReason]
    obligations: ObligationSummary | None


@dataclass(frozen=True)
class SourceUsageMetrics:
    """Persistence-agnostic telemetry aggregate for one source (REQ-RESEARCH-008).

    Values must be non-negative. Attributable by stable source_id.
    """

    source_id: str
    retrieval_count: int
    extracted_record_count: int

    def __post_init__(self) -> None:
        if self.retrieval_count < 0:
            raise ValueError("SourceUsageMetrics.retrieval_count must be non-negative")
        if self.extracted_record_count < 0:
            raise ValueError("SourceUsageMetrics.extracted_record_count must be non-negative")

    def add(self, retrieval_delta: int = 0, extracted_delta: int = 0) -> SourceUsageMetrics:
        """Return a new SourceUsageMetrics with incremented counts.

        Both deltas must be non-negative.
        """
        if retrieval_delta < 0 or extracted_delta < 0:
            raise ValueError("SourceUsageMetrics.add() deltas must be non-negative")
        return SourceUsageMetrics(
            source_id=self.source_id,
            retrieval_count=self.retrieval_count + retrieval_delta,
            extracted_record_count=self.extracted_record_count + extracted_delta,
        )


@dataclass(frozen=True)
class ExtractionBudget:
    """Caller-configured extraction limit for non-bulk-cleared automated research.

    Thresholds are caller-supplied; no numeric default is invented here.
    At-or-above the limit is treated as exceeded (fail-closed boundary).
    """

    retrieval_limit: int | None
    extracted_record_limit: int | None

    def within_limits(self, metrics: SourceUsageMetrics) -> bool:
        """Return True if current metrics are strictly below both configured limits."""
        if self.retrieval_limit is not None and metrics.retrieval_count >= self.retrieval_limit:
            return False
        return not (
            self.extracted_record_limit is not None
            and metrics.extracted_record_count >= self.extracted_record_limit
        )


class JobRouting(StrEnum):
    """Routing decision for a ResearchJob based on a source-use gate outcome."""

    CONTINUE = "continue"
    NEEDS_REVIEW = "needs_review"
    BLOCKED = "blocked"


# Uses that must fail closed when clearance/assessment is not confirmed allowed.
_HIGH_RISK_USES: frozenset[SourceUse] = frozenset(
    {
        SourceUse.PRODUCTION_VALUE,
        SourceUse.BULK_BOOTSTRAP,
        SourceUse.AUTOMATED_INGESTION,
        SourceUse.ARTIFACT_REDISTRIBUTION,
    }
)

# Clearance states that never produce an ALLOWED outcome.
_NON_ALLOW_CLEARANCE_OUTCOMES: dict[str, DecisionOutcome] = {
    "prohibited": DecisionOutcome.BLOCKED,
    "legal_review_required": DecisionOutcome.LEGAL_REVIEW_REQUIRED,
    "conditional": DecisionOutcome.CONDITIONAL,
    "unknown": DecisionOutcome.UNKNOWN_UNASSESSED,
}

_NON_ALLOW_CLEARANCE_REASONS: dict[str, DecisionReason] = {
    "prohibited": DecisionReason.CLEARANCE_PROHIBITED,
    "legal_review_required": DecisionReason.CLEARANCE_LEGAL_REVIEW_REQUIRED,
    "conditional": DecisionReason.CLEARANCE_CONDITIONAL,
    "unknown": DecisionReason.CLEARANCE_UNKNOWN,
}


def _build_obligation_summary(obligations_raw: dict[str, Any]) -> ObligationSummary:
    other: list[str] = obligations_raw.get("other_conditions") or []
    return ObligationSummary(
        attribution_required=obligations_raw["attribution_required"],
        share_alike=obligations_raw["share_alike"],
        notice_required=obligations_raw["notice_required"],
        attribution_instructions=obligations_raw.get("attribution_instructions"),
        other_conditions=tuple(other),
    )


def check_source_use(
    source: dict[str, Any],
    use: SourceUse,
    metrics: SourceUsageMetrics | None = None,
    budget: ExtractionBudget | None = None,
) -> SourceUseDecision:
    """Deterministic, fail-closed gate for one source-use combination.

    ``source`` must be a schema-valid Source record dict (per SOURCE_SCHEMA.v0.2).
    ``metrics`` and ``budget`` are required for AUTOMATED_INGESTION when the
    source is not bulk-cleared; their absence fails closed (REQ-RESEARCH-008).

    Returns a SourceUseDecision with machine-readable outcome and reason codes.
    Never grants permission from license name, publisher identity, public
    accessibility, or source prestige alone.
    """
    source_id: str = source["source_id"]
    rights: dict[str, Any] = source["rights"]
    clearance: dict[str, Any] = rights["clearance"]
    permissions: dict[str, Any] = rights["permissions"]
    access: dict[str, Any] = rights["access"]
    obligations_raw: dict[str, Any] = rights["obligations"]
    assessment_status: str = rights["assessment_status"]

    reasons: set[DecisionReason] = set()
    obligations = _build_obligation_summary(obligations_raw)

    def _block(reason: DecisionReason) -> SourceUseDecision:
        reasons.add(reason)
        return SourceUseDecision(
            source_id=source_id,
            use=use,
            outcome=DecisionOutcome.BLOCKED,
            reasons=frozenset(reasons),
            obligations=obligations,
        )

    def _non_allow(outcome: DecisionOutcome, reason: DecisionReason) -> SourceUseDecision:
        reasons.add(reason)
        return SourceUseDecision(
            source_id=source_id,
            use=use,
            outcome=outcome,
            reasons=frozenset(reasons),
            obligations=obligations,
        )

    # Rule: unassessed sources fail closed for high-risk uses (SR-003).
    if assessment_status == "unassessed" and use in _HIGH_RISK_USES:
        return _non_allow(DecisionOutcome.UNKNOWN_UNASSESSED, DecisionReason.SOURCE_UNASSESSED)

    clearance_value: str = clearance[use.value]

    # --- AUTOMATED_INGESTION: independent access check (SR-001) ---
    if use == SourceUse.AUTOMATED_INGESTION:
        automated_access: str = access["automated_access"]

        if automated_access == "prohibited":
            return _block(DecisionReason.AUTOMATED_ACCESS_PROHIBITED)

        # Clearance check before resolving access ambiguity.
        if clearance_value in _NON_ALLOW_CLEARANCE_OUTCOMES:
            return _non_allow(
                _NON_ALLOW_CLEARANCE_OUTCOMES[clearance_value],
                _NON_ALLOW_CLEARANCE_REASONS[clearance_value],
            )

        # Clearance is "allowed" — now check access state.
        if automated_access == "unknown":
            return _non_allow(
                DecisionOutcome.UNKNOWN_UNASSESSED,
                DecisionReason.AUTOMATED_ACCESS_UNKNOWN,
            )
        if automated_access == "conditional":
            # Remains non-allow until the reviewed Source expresses an allowed
            # state for the concrete approved access method.
            return _non_allow(
                DecisionOutcome.CONDITIONAL,
                DecisionReason.AUTOMATED_ACCESS_CONDITIONAL,
            )
        # automated_access == "allowed" — proceed to telemetry + permission checks.

        # Telemetry check for non-bulk-cleared sources (REQ-RESEARCH-008).
        is_bulk_cleared: bool = clearance.get("bulk_bootstrap") == "allowed"
        if not is_bulk_cleared:
            if metrics is None or budget is None:
                return _block(DecisionReason.MISSING_TELEMETRY_CONTEXT)
            if not budget.within_limits(metrics):
                return _block(DecisionReason.EXTRACTION_THRESHOLD_EXCEEDED)

        # Permission conflict: automated_extract prohibited (rule 5).
        if permissions.get("automated_extract") == "prohibited":
            return _block(DecisionReason.PERMISSION_CONFLICT_AUTOMATED_EXTRACT)

        reasons.add(DecisionReason.CLEARANCE_ALLOWED)
        return SourceUseDecision(
            source_id=source_id,
            use=use,
            outcome=DecisionOutcome.ALLOWED,
            reasons=frozenset(reasons),
            obligations=obligations,
        )

    # --- All other uses: clearance check ---
    if clearance_value in _NON_ALLOW_CLEARANCE_OUTCOMES:
        return _non_allow(
            _NON_ALLOW_CLEARANCE_OUTCOMES[clearance_value],
            _NON_ALLOW_CLEARANCE_REASONS[clearance_value],
        )

    # Clearance is "allowed" — check incompatible permission prohibitions (rule 5).
    assert clearance_value == "allowed"

    if use == SourceUse.PRODUCTION_VALUE:
        if permissions.get("store_canonical_values") == "prohibited":
            reasons.add(DecisionReason.PERMISSION_CONFLICT_STORE_CANONICAL)
        if permissions.get("commercial_use") == "prohibited":
            reasons.add(DecisionReason.PERMISSION_CONFLICT_COMMERCIAL)

    elif use == SourceUse.BULK_BOOTSTRAP:
        if permissions.get("bulk_ingest") == "prohibited":
            reasons.add(DecisionReason.PERMISSION_CONFLICT_BULK_INGEST)
        if permissions.get("commercial_use") == "prohibited":
            reasons.add(DecisionReason.PERMISSION_CONFLICT_COMMERCIAL)
        # Share-alike unresolved blocks bulk use.
        if obligations_raw.get("share_alike") in {"yes", "unknown"}:
            reasons.add(DecisionReason.SHARE_ALIKE_UNRESOLVED)

    elif use == SourceUse.ARTIFACT_REDISTRIBUTION:
        if permissions.get("redistribute_source_material") == "prohibited":
            reasons.add(DecisionReason.PERMISSION_CONFLICT_REDISTRIBUTE)
        # Share-alike unresolved blocks redistribution.
        if obligations_raw.get("share_alike") in {"yes", "unknown"}:
            reasons.add(DecisionReason.SHARE_ALIKE_UNRESOLVED)

    if reasons:
        return SourceUseDecision(
            source_id=source_id,
            use=use,
            outcome=DecisionOutcome.BLOCKED,
            reasons=frozenset(reasons),
            obligations=obligations,
        )

    reasons.add(DecisionReason.CLEARANCE_ALLOWED)
    return SourceUseDecision(
        source_id=source_id,
        use=use,
        outcome=DecisionOutcome.ALLOWED,
        reasons=frozenset(reasons),
        obligations=obligations,
    )


def route_research_job(decision: SourceUseDecision) -> JobRouting:
    """Map a source-use gate outcome to a ResearchJob routing action.

    ALLOWED → CONTINUE; BLOCKED → BLOCKED; all other outcomes → NEEDS_REVIEW.
    The job is never marked complete here; factual extraction, provenance,
    normalization and validation happen later (rule 10 / REQ-RESEARCH-002).
    """
    if decision.outcome == DecisionOutcome.ALLOWED:
        return JobRouting.CONTINUE
    if decision.outcome == DecisionOutcome.BLOCKED:
        return JobRouting.BLOCKED
    return JobRouting.NEEDS_REVIEW
