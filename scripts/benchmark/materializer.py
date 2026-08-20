"""Deterministic benchmark bundle materializer — SLICE-0014.

Materializes ResearchEvidenceBundle for all 50 retained benchmark cases using
field-/claim-level observations derived from retained HullQ evidence:

  Waves 01-02: field-level observations auto-migrated from committed legacy JSONL
  exports (research/benchmark/legacy-observations/). Each JSONL row where
  evidence_tier != "research" becomes a ResearchObservation with independently
  derived EvidenceType, ClaimSemantics and ObservationApplicability. No SailboatData
  field values are admitted.

  Waves 03-06: field-/claim-level facts from committed wave summary artifacts,
  embedded as Python data structures. No new web research.

No network access. No SailboatData field values. All IDs and fingerprints are
deterministic across repeated runs.

Returns dict[case_id, MaterializationResult].
"""

from __future__ import annotations

import base64
import gzip
import json
from dataclasses import dataclass
from dataclasses import field as dc_field
from pathlib import Path
from typing import Any

from hullq.domain.provenance import (
    ClaimSemantics,
    ConfidenceLevel,
    EvidenceType,
    ObservationApplicability,
    ProducerKind,
    ProducerMetadata,
    RawObservation,
    RawObservationKind,
    ResearchContext,
    SourceLocator,
)
from hullq.research.jobs import ResearchTarget
from hullq.research.observations import (
    ReferenceCheckOutcome,
    ReferenceCrosscheck,
    ResearchEvidenceBundle,
    ResearchObservation,
    UnresolvedFinding,
    UnresolvedFindingSeverity,
)

MANIFEST_PATH = (
    Path(__file__).resolve().parents[2] / "research" / "benchmark" / "persistence" / "manifest.json"
)
_LEGACY_DIR = Path(__file__).resolve().parents[2] / "research" / "benchmark" / "legacy-observations"

BUNDLE_VERSION = "0014-v1"
ACTIVITY_ID = "benchmark-0014-materialization"
REFERENCE_SOURCE_ID = "sailboatdata-post-hoc-qa"

_PRODUCER = ProducerMetadata(
    kind=ProducerKind.DETERMINISTIC_TOOL,
    identifier="hullq-benchmark-materializer",
    version=BUNDLE_VERSION,
    model=None,
    prompt_or_rule_version=None,
)

_OBSERVED_AT = "2026-08-20T00:00:00Z"
_NULL_LOCATOR = SourceLocator(
    page=None, section=None, anchor=None, table=None, figure=None, record_key=None
)
_RESEARCH_CONTEXT = ResearchContext(research_job_id=None, activity_id=ACTIVITY_ID)

# Design ID (JSONL) → benchmark case ID
_DESIGN_TO_CASE: dict[str, str] = {
    "BENCH-HR36": "B01-001",
    "BENCH-WESTERLY-CENTAUR": "B01-002",
    "BENCH-RM1180": "B01-003",
    "BENCH-NAJAD34": "B01-004",
    "BENCH-J24": "B01-005",
    "BENCH-DRAGONFLY32": "B02-001",
    "BENCH-OVNI370": "B02-002",
    "BENCH-GARCIA45": "B02-003",
    "BENCH-BOREAL442": "B02-004",
    "BENCH-IP349": "B02-005",
    "BENCH-CORSAIR880": "B02-006",
    "BENCH-LAGOON42-2016": "B02-007",
    "BENCH-NAUTICAT33-331": "B02-008",
    "BENCH-CATALINA316": "B02-009",
    "BENCH-SO410": "B02-010",
    "BENCH-CATANA-OCEAN": "B02-011",
    "BENCH-POGO1": "B02-012",
}

# Cases with conflict_unresolved=1 per BENCHMARK-50-classification.csv
_CONFLICT_CASES: frozenset[str] = frozenset(
    {
        "B01-001",
        "B01-002",
        "B01-004",
        "B02-001",
        "B02-007",
        "B02-011",
        "B03-002",
        "B03-003",
        "B03-005",
        "B03-007",
        "B04-002",
        "B04-003",
        "B04-005",
        "B04-006",
        "B04-007",
        "B05-001",
        "B05-004",
        "B05-005",
        "B06-002",
        "B06-005",
    }
)

# Outcome severity ranking (higher = more severe / informative)
_OUTCOME_RANK: dict[ReferenceCheckOutcome, int] = {
    ReferenceCheckOutcome.CONFLICT: 7,
    ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED: 6,
    ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE: 5,
    ReferenceCheckOutcome.PARTIAL_MATCH: 4,
    ReferenceCheckOutcome.REFERENCE_INCOMPLETE: 3,
    ReferenceCheckOutcome.NO_REFERENCE_RECORD_FOUND: 2,
    ReferenceCheckOutcome.MATCH: 1,
    ReferenceCheckOutcome.NOT_CHECKED: 0,
}

# W01 evidence statuses that produce an UnresolvedFinding from the observation row itself
_W01_FINDING_STATUSES: frozenset[str] = frozenset(
    {"source_internal_conflict", "needs_generation_boundary"}
)

# W02 evidence statuses that produce an UnresolvedFinding from the observation row itself
_W02_FINDING_STATUSES: frozenset[str] = frozenset(
    {"conflicting_secondary_evidence", "requires_identity_resolution"}
)

# Fields that indicate identity/chronology claims
_IDENTITY_FIELDS: frozenset[str] = frozenset(
    {
        "production_start",
        "production_end",
        "first_delivery",
        "units_built",
        "lineage",
        "variant_history",
        "transition_year",
        "successor_model",
        "original_model",
        "original_designer",
        "named_variant",
        "identity_note",
    }
)

# ---------------------------------------------------------------------------
# MaterializationResult
# ---------------------------------------------------------------------------


@dataclass
class MaterializationResult:
    """Outcome of attempting to materialize one benchmark case."""

    case_id: str
    status: str  # "MATERIALIZED" | "REVIEW_REQUIRED" | "CANNOT_MATERIALIZE"
    bundle: ResearchEvidenceBundle | None
    review_reasons: list[str] = dc_field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _bundle_id(case_id: str) -> str:
    return f"hullq-benchmark-{case_id.lower()}"


def _obs_id(bid: str, idx: int) -> str:
    return f"{bid}-obs-{idx:04d}"


def _finding_id(bid: str, idx: int) -> str:
    return f"{bid}-finding-{idx:04d}"


def _crosscheck_id(bid: str) -> str:
    return f"{bid}-cc-0000"


def _make_app(
    *,
    first_year: int | None = None,
    last_year: int | None = None,
    hull_number_from: str | None = None,
    hull_number_to: str | None = None,
    market_or_region: str | None = None,
    named_variant_hint: str | None = None,
    design_option_hints: tuple[str, ...] | None = None,
    operating_state_hint: str | None = None,
    individual_hull_or_listing_ref: str | None = None,
    unknown_or_unbounded: bool = True,
) -> ObservationApplicability:
    return ObservationApplicability(
        first_year=first_year,
        last_year=last_year,
        hull_number_from=hull_number_from,
        hull_number_to=hull_number_to,
        market_or_region=market_or_region,
        named_variant_hint=named_variant_hint,
        design_option_hints=design_option_hints,
        operating_state_hint=operating_state_hint,
        individual_hull_or_listing_ref=individual_hull_or_listing_ref,
        unknown_or_unbounded=unknown_or_unbounded,
    )


_UNBOUNDED = _make_app()


def _map_confidence(raw: str | None) -> ConfidenceLevel:
    if raw is None:
        return ConfidenceLevel.UNKNOWN
    s = raw.lower().strip()
    if s in ("high", "medium-high"):
        return ConfidenceLevel.HIGH
    if s in ("medium",):
        return ConfidenceLevel.MEDIUM
    if s in ("low", "low-medium"):
        return ConfidenceLevel.LOW
    return ConfidenceLevel.UNKNOWN


def _map_evidence_type(tier: str, source_name: str) -> EvidenceType:
    name = source_name.lower()
    # Source-name classification first
    if "manual" in name:
        return EvidenceType.MANUAL
    if any(
        k in name
        for k in (
            "class",
            "association",
            "owners",
            "club",
            "verband",
            "klassenverein",
            "htcca",
            "co32",
        )
    ):
        return EvidenceType.CLASS_OR_OWNER_ASSOCIATION
    # Narrative press / community sources
    if any(
        k in name
        for k in (
            "practical boat owner",
            "pbo",
            "yachting monthly",
            "sailing magazine",
            "practical sailor",
            "good old boat",
            "cruising world",
            "canadian boating",
            "wavetrain",
        )
    ):
        return EvidenceType.NARRATIVE_TEXT
    # Broker / historical listing
    if any(k in name for k in ("de valk", "devalk", "boatshed", "lucas", "yachtsnet")):
        return EvidenceType.NARRATIVE_TEXT
    # Community forums
    if any(
        k in name
        for k in (
            "forum",
            "discussion",
            "ybw",
            "sailboatowners",
            "ericsonyachts",
            "macgregorsailors",
        )
    ):
        return EvidenceType.NARRATIVE_TEXT
    # Tier A defaults to manufacturer
    if tier == "A":
        return EvidenceType.MANUFACTURER_SPECIFICATION
    # Tier A/B, B, C → narrative
    return EvidenceType.NARRATIVE_TEXT


def _map_claim_semantics(field: str, basis: str | None) -> ClaimSemantics:
    basis_lower = (basis or "").lower()
    if field in _IDENTITY_FIELDS:
        return ClaimSemantics.IDENTITY_OR_CHRONOLOGY_CLAIM
    if field in ("research_note", "appendage_claim", "rudder_claim"):
        return ClaimSemantics.NOMINAL_DESIGN_VALUE
    if any(k in basis_lower for k in ("orc", "certificate", "measurement trim", "orc certificate")):
        return ClaimSemantics.MEASUREMENT_CERTIFICATE_VALUE
    if any(
        k in basis_lower
        for k in ("board up", "boards up", "keel up", "board down", "boards down", "keel down")
    ):
        return ClaimSemantics.OPERATING_STATE_VALUE
    if "individual" in basis_lower:
        return ClaimSemantics.INDIVIDUAL_HULL_VALUE
    if any(k in basis_lower for k in ("optional", "option ")):
        return ClaimSemantics.FACTORY_OPTION_VALUE
    return ClaimSemantics.NOMINAL_DESIGN_VALUE


def _map_applicability(basis: str | None) -> ObservationApplicability:
    b = (basis or "").lower().strip()
    # Operating states
    if "board up" in b or "boards up" in b:
        return _make_app(operating_state_hint="board_up", unknown_or_unbounded=False)
    if "board down" in b or "boards down" in b:
        return _make_app(operating_state_hint="board_down", unknown_or_unbounded=False)
    if "keel up" in b:
        return _make_app(operating_state_hint="keel_up", unknown_or_unbounded=False)
    if "keel down" in b:
        return _make_app(operating_state_hint="keel_down", unknown_or_unbounded=False)
    # Named variants — check common patterns
    for short, hint in (
        ("mk i", "Mk I"),
        ("mk ii", "Mk II"),
        ("mk iii", "Mk III"),
        ("mk iv", "Mk IV"),
        ("mk1", "Mk I"),
        ("mk2", "Mk II"),
        ("mk3", "Mk III"),
        ("mk4", "Mk IV"),
        ("mk 1", "Mk I"),
        ("mk 2", "Mk II"),
        ("mk 3", "Mk III"),
        ("mk 4", "Mk IV"),
    ):
        if short in b:
            return _make_app(named_variant_hint=hint, unknown_or_unbounded=False)
    for kw, hint in (
        ("touring", "Touring"),
        ("evolution", "Evolution"),
        ("elite", "Elite"),
    ):
        if b == kw or b.startswith(kw + " "):
            return _make_app(named_variant_hint=hint, unknown_or_unbounded=False)
    # Design option hints
    if "twin keel" in b or "bilge keel" in b:
        return _make_app(design_option_hints=("twin_keel",), unknown_or_unbounded=False)
    if "standard keel" in b or "single keel" in b:
        return _make_app(design_option_hints=("standard_keel",), unknown_or_unbounded=False)
    if "shallow keel" in b:
        return _make_app(design_option_hints=("shallow_keel",), unknown_or_unbounded=False)
    if "deep keel" in b:
        return _make_app(design_option_hints=("deep_keel",), unknown_or_unbounded=False)
    if "tandem keel" in b:
        return _make_app(design_option_hints=("tandem_keel",), unknown_or_unbounded=False)
    if "lifting keel" in b:
        return _make_app(design_option_hints=("lifting_keel",), unknown_or_unbounded=False)
    # Individual hull / listing
    if "individual" in b:
        return _make_app(
            individual_hull_or_listing_ref="individual_hull", unknown_or_unbounded=True
        )
    # Default: unknown / unbounded
    return _UNBOUNDED


def _cc_to_outcome(cc: str | None) -> ReferenceCheckOutcome:
    if not cc:
        return ReferenceCheckOutcome.NOT_CHECKED
    c = cc.lower()
    # Exact-match shortcuts
    if c in (
        "match",
        "compatible",
        "comparable",
        "broad_taxonomy_match",
        "match_component",
        "match_as_ballast",
        "match_as_variant",
        "match_for_mki_only",
    ):
        return ReferenceCheckOutcome.MATCH
    # Conflict variants (check before partial)
    if "conflict_or_basis_difference" in c:
        return ReferenceCheckOutcome.CONFLICT
    if "conflict" in c and "not_used" not in c and "near_conflict" not in c:
        return ReferenceCheckOutcome.CONFLICT
    if "near_conflict" in c:
        return ReferenceCheckOutcome.CONFLICT
    # Identity disambiguation
    if "identity_disambiguation" in c:
        return ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED
    # Definition / basis difference
    if any(
        k in c
        for k in (
            "not_same_basis",
            "basis_difference",
            "definition_difference",
            "different_length",
            "different_basis",
            "basis_or_version",
            "reference_uses_different",
        )
    ):
        return ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE
    # Partial match
    if any(
        k in c
        for k in (
            "partial",
            "near_match",
            "variant_specific",
            "component_difference",
            "partial_secondary",
            "reference_first_built_mismatch",
            "reference_notes_changes",
            "partial_reference",
            "partial_generation",
        )
    ):
        return ReferenceCheckOutcome.PARTIAL_MATCH
    # No reference record
    if any(k in c for k in ("not_represented", "not_found", "no_reference_record")):
        return ReferenceCheckOutcome.NO_REFERENCE_RECORD_FOUND
    # Reference incomplete
    if "reference_incomplete" in c or "reference_scalar_is_incomplete" in c:
        return ReferenceCheckOutcome.REFERENCE_INCOMPLETE
    # NOT_CHECKED covers: not_used_for_resolution, not_used_as_canonical,
    # comparison_only, reference_flattens_or_differs, definition_difference (partial)
    return ReferenceCheckOutcome.NOT_CHECKED


def _worst_outcome(outcomes: list[ReferenceCheckOutcome]) -> ReferenceCheckOutcome:
    if not outcomes:
        return ReferenceCheckOutcome.NOT_CHECKED
    return max(outcomes, key=lambda o: _OUTCOME_RANK.get(o, 0))


# ---------------------------------------------------------------------------
# Legacy JSONL decode (W01 / W02)
# ---------------------------------------------------------------------------

_JSONL_CACHE: dict[int, list[dict[str, Any]]] = {}


def _decode_legacy_jsonl(wave_num: int) -> list[dict[str, Any]]:
    if wave_num in _JSONL_CACHE:
        return _JSONL_CACHE[wave_num]
    b64_path = _LEGACY_DIR / f"WAVE-{wave_num:02d}-observations.jsonl.gz.b64"
    raw = base64.b64decode(b64_path.read_bytes())
    lines = gzip.decompress(raw).decode("utf-8").strip().split("\n")
    rows = [json.loads(ln) for ln in lines if ln.strip()]
    _JSONL_CACHE[wave_num] = rows
    return rows


# ---------------------------------------------------------------------------
# Build bundle from observation rows (W01 / W02 shared)
# ---------------------------------------------------------------------------


def _row_source_url(row: dict[str, Any]) -> str:
    url = row.get("source_url") or ""
    if url:
        return url
    name: str = row.get("source_name", "unknown-source")
    return "hullq-benchmark-source-" + name.lower().replace(" ", "-")[:60]


def _row_raw_value(row: dict[str, Any]) -> Any:
    # W01 uses "value", W02 uses "raw_or_normalized_value"
    for key in ("value", "raw_or_normalized_value"):
        if key in row:
            return row[key]
    return None


def _row_crosscheck_string(row: dict[str, Any]) -> str | None:
    # W01: sailboatdata_crosscheck is a string
    if "sailboatdata_crosscheck" in row:
        v = row["sailboatdata_crosscheck"]
        return str(v) if v is not None else None
    # W02: reference_crosscheck is a dict
    cc = row.get("reference_crosscheck")
    if isinstance(cc, dict):
        return cc.get("result")
    return None


def _build_legacy_bundle(
    case_id: str,
    rows: list[dict[str, Any]],
    research_target: ResearchTarget,
    finding_statuses: frozenset[str],
    wave: int,
) -> ResearchEvidenceBundle:
    bid = _bundle_id(case_id)
    observations: list[ResearchObservation] = []
    findings: list[UnresolvedFinding] = []
    all_cc_outcomes: list[ReferenceCheckOutcome] = []
    obs_idx = 0
    finding_idx = 0

    for row in rows:
        tier = row.get("evidence_tier", "")
        field = row.get("field", "")
        status = row.get("evidence_status", "supported")
        basis = row.get("basis_or_state") or row.get("basis") or ""
        raw_val = _row_raw_value(row)
        unit = row.get("unit")
        source_url = _row_source_url(row)
        source_name = row.get("source_name", "")
        notes = row.get("notes")
        confidence_str = row.get("confidence")
        cc_str = _row_crosscheck_string(row)
        cc_outcome = _cc_to_outcome(cc_str)
        all_cc_outcomes.append(cc_outcome)

        # Determine raw observation kind
        if isinstance(raw_val, (int, float)):
            kind = RawObservationKind.LITERAL
        else:
            kind = RawObservationKind.TEXT_FRAGMENT

        # Skip research-tier rows from observations; handle findings below
        if tier == "research":
            # Create finding if outcome is CONFLICT or status is BLOCKING
            is_conflict_cc = cc_outcome == ReferenceCheckOutcome.CONFLICT
            is_priority_status = status in (
                "priority_research_conflict",
                "requires_identity_resolution",
            )
            if is_conflict_cc or is_priority_status:
                findings.append(
                    UnresolvedFinding(
                        finding_id=_finding_id(bid, finding_idx),
                        topic="conflict_or_unresolved_evidence",
                        description=(
                            f"Research note for {field}: {status}. "
                            f"Reference crosscheck outcome: {cc_str or 'not_checked'}."
                        ),
                        related_observation_ids=frozenset(),
                        severity=UnresolvedFindingSeverity.REVIEW,
                    )
                )
                finding_idx += 1
            continue

        # Create observation from non-research rows
        oid = _obs_id(bid, obs_idx)
        obs_idx += 1

        observation = ResearchObservation(
            observation_id=oid,
            research_target=research_target,
            source_id=source_url,
            source_locator=_NULL_LOCATOR,
            raw=RawObservation(
                kind=kind,
                value=raw_val,
                unit=unit,
                excerpt=None,
            ),
            normalized_candidate=None,
            evidence_type=_map_evidence_type(tier, source_name),
            claim_semantics=_map_claim_semantics(field, basis),
            applicability=_map_applicability(basis),
            producer=_PRODUCER,
            research_context=_RESEARCH_CONTEXT,
            observed_at=_OBSERVED_AT,
            confidence=_map_confidence(confidence_str),
            supersedes_observation_id=None,
            intended_subject_kind_hint=None,
            intended_field_pointer=None,
            notes=notes,
        )
        observations.append(observation)

        # Create finding from evidence_status of non-research rows
        if status in finding_statuses:
            findings.append(
                UnresolvedFinding(
                    finding_id=_finding_id(bid, finding_idx),
                    topic="conflict_or_unresolved_evidence",
                    description=(
                        f"Observation {oid} field={field}: evidence_status={status!r}. "
                        f"Reference crosscheck: {cc_str or 'not_checked'}."
                    ),
                    related_observation_ids=frozenset({oid}),
                    severity=(
                        UnresolvedFindingSeverity.BLOCKING
                        if status == "source_internal_conflict"
                        else UnresolvedFindingSeverity.REVIEW
                    ),
                )
            )
            finding_idx += 1

    # Fallback: conflict case with no findings yet → derive from worst cc conflict
    if case_id in _CONFLICT_CASES and not findings:
        conflict_obs_ids = frozenset(o.observation_id for o in observations)
        findings.append(
            UnresolvedFinding(
                finding_id=_finding_id(bid, finding_idx),
                topic="conflict_or_unresolved_evidence",
                description=(
                    f"Reference crosscheck conflict for {case_id}: aggregate SailboatData "
                    f"comparison shows worst outcome "
                    f"{_worst_outcome(all_cc_outcomes).value}. "
                    f"Classification flag conflict_unresolved=1."
                ),
                related_observation_ids=conflict_obs_ids,
                severity=UnresolvedFindingSeverity.REVIEW,
            )
        )

    # Aggregate crosscheck
    aggregate_outcome = _worst_outcome(all_cc_outcomes)
    crosscheck = ReferenceCrosscheck(
        crosscheck_id=_crosscheck_id(bid),
        reference_source_id=REFERENCE_SOURCE_ID,
        topic_or_field=None,
        outcome=aggregate_outcome,
        notes=f"Wave {wave:02d} aggregate post-hoc QA crosscheck; worst outcome: {aggregate_outcome.value}.",
    )

    return ResearchEvidenceBundle(
        bundle_id=bid,
        bundle_version=BUNDLE_VERSION,
        research_target=research_target,
        research_job_id=None,
        activity_id=ACTIVITY_ID,
        observations=tuple(observations),
        unresolved_findings=tuple(findings),
        promoted_evidence=(),
        reference_crosschecks=(crosscheck,),
    )


# ---------------------------------------------------------------------------
# Embedded W03-W06 fact data
# ---------------------------------------------------------------------------
# Each entry: list of fact dicts; each fact has:
#   source_url, source_name, field, value, unit, basis, tier, confidence
# Optional: kind ("literal"|"text_fragment") — auto-detected if omitted.

_W03W06_FACTS: dict[str, list[dict[str, Any]]] = {
    "B03-001": [
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "production_start",
            "value": 1980,
            "unit": "year",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "production_end",
            "value": 1991,
            "unit": "year",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "units_built",
            "value": 255,
            "unit": "count",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "loa",
            "value": 12.93,
            "unit": "m",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "lwl",
            "value": 10.5,
            "unit": "m",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "beam",
            "value": 3.78,
            "unit": "m",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "draft",
            "value": 2.05,
            "unit": "m",
            "basis": "standard keel",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "displacement",
            "value": 11500.0,
            "unit": "kg",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "keel_weight",
            "value": 4500.0,
            "unit": "kg",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-42-e/",
            "source_name": "Hallberg-Rassy Club catalogue",
            "field": "rig_types",
            "value": "ketch and sloop rigs both documented",
            "unit": None,
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B03-002": [
        {
            "source_url": "https://www.beneteau.com/oceanis-2005-2014/oceanis-37",
            "source_name": "BENETEAU heritage page",
            "field": "loa",
            "value": 11.48,
            "unit": "m",
            "basis": "BENETEAU specification",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.beneteau.com/oceanis-2005-2014/oceanis-37",
            "source_name": "BENETEAU heritage page",
            "field": "beam",
            "value": 3.92,
            "unit": "m",
            "basis": "BENETEAU specification",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.beneteau.com/oceanis-2005-2014/oceanis-37",
            "source_name": "BENETEAU heritage page",
            "field": "displacement",
            "value": 6515.0,
            "unit": "kg",
            "basis": "Lightship Displacement",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.beneteau.com/oceanis-2005-2014/oceanis-37",
            "source_name": "BENETEAU heritage page",
            "field": "air_draft",
            "value": 16.65,
            "unit": "m",
            "basis": "BENETEAU specification",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B03-003": [
        {
            "source_url": "https://www.rustleryachts.com/keel-design-explained/",
            "source_name": "Rustler Yachts keel-design article",
            "field": "rudder_type",
            "value": "keel-hung rudder",
            "unit": None,
            "basis": "builder explicit description",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.rustleryachts.com/keel-design-explained/",
            "source_name": "Rustler Yachts keel-design article",
            "field": "keel_type",
            "value": "traditional long keel with cutaway forefoot",
            "unit": None,
            "basis": "builder explicit description",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.devalk.nl/",
            "source_name": "De Valk historical Rustler 36 listing",
            "field": "loa",
            "value": 10.78,
            "unit": "m",
            "basis": "individual boat",
            "tier": "B",
            "confidence": "medium",
        },
        {
            "source_url": "https://www.devalk.nl/",
            "source_name": "De Valk historical Rustler 36 listing",
            "field": "beam",
            "value": 3.35,
            "unit": "m",
            "basis": "individual boat",
            "tier": "B",
            "confidence": "medium",
        },
        {
            "source_url": "https://www.devalk.nl/",
            "source_name": "De Valk historical Rustler 36 listing",
            "field": "draft",
            "value": 1.75,
            "unit": "m",
            "basis": "individual boat",
            "tier": "B",
            "confidence": "medium",
        },
        {
            "source_url": "https://www.devalk.nl/",
            "source_name": "De Valk historical Rustler 36 listing",
            "field": "displacement",
            "value": 7500.0,
            "unit": "kg",
            "basis": "individual boat",
            "tier": "B",
            "confidence": "medium",
        },
        {
            "source_url": "https://www.devalk.nl/",
            "source_name": "De Valk historical Rustler 36 listing",
            "field": "ballast",
            "value": 3600.0,
            "unit": "kg",
            "basis": "individual boat",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B03-004": [
        {
            "source_url": "https://goodoldboat.com/seafarer-26/",
            "source_name": "Good Old Boat technical article",
            "field": "production_start",
            "value": 1977,
            "unit": "year",
            "basis": "McCurdy and Rhodes generation",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://goodoldboat.com/seafarer-26/",
            "source_name": "Good Old Boat technical article",
            "field": "production_end",
            "value": 1985,
            "unit": "year",
            "basis": "McCurdy and Rhodes generation",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://goodoldboat.com/seafarer-26/",
            "source_name": "Good Old Boat technical article",
            "field": "keel_type",
            "value": "fin keel",
            "unit": None,
            "basis": "Good Old Boat description",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://goodoldboat.com/seafarer-26/",
            "source_name": "Good Old Boat technical article",
            "field": "displacement",
            "value": 4600.0,
            "unit": "lb",
            "basis": "Good Old Boat description",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://goodoldboat.com/seafarer-26/",
            "source_name": "Good Old Boat technical article",
            "field": "rudder_type",
            "value": "partial skeg with bottom bearing",
            "unit": None,
            "basis": "Good Old Boat explicit description",
            "tier": "B",
            "confidence": "high",
        },
    ],
    "B03-005": [
        {
            "source_url": "https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual",
            "source_name": "Southerly 110 owner's manual",
            "field": "loa",
            "value": 10.82,
            "unit": "m",
            "basis": "Southerly 110 owner's manual",
            "tier": "A",
            "confidence": "medium",
        },
        {
            "source_url": "https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual",
            "source_name": "Southerly 110 owner's manual",
            "field": "lwl",
            "value": 9.22,
            "unit": "m",
            "basis": "Southerly 110 owner's manual",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual",
            "source_name": "Southerly 110 owner's manual",
            "field": "beam",
            "value": 3.57,
            "unit": "m",
            "basis": "Southerly 110 owner's manual",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual",
            "source_name": "Southerly 110 owner's manual",
            "field": "draft_min",
            "value": 0.71,
            "unit": "m",
            "basis": "keel up",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual",
            "source_name": "Southerly 110 owner's manual",
            "field": "draft_max",
            "value": 2.18,
            "unit": "m",
            "basis": "keel down",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual",
            "source_name": "Southerly 110 owner's manual",
            "field": "rudder_count",
            "value": "twin rudders as standard",
            "unit": None,
            "basis": "owner's manual explicit statement",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B03-006": [
        {
            "source_url": "https://www.jeremyrogers.co.uk/contessa32-specification/",
            "source_name": "Jeremy Rogers Contessa 32 specification",
            "field": "ballast_type",
            "value": "encapsulated lead ballast",
            "unit": None,
            "basis": "current new-build specification",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.jeremyrogers.co.uk/contessa32-specification/",
            "source_name": "Jeremy Rogers Contessa 32 specification",
            "field": "rudder_attachment",
            "value": "two bronze bearings and stainless lower attachment plate at base of skeg",
            "unit": None,
            "basis": "current new-build specification",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.co32.org/racing/class-rules",
            "source_name": "Contessa 32 Class Association class rules",
            "field": "class_rules_authority",
            "value": "class rules are authoritative constraints not automatically nominal production values",
            "unit": None,
            "basis": "class rules",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B03-007": [
        {
            "source_url": "https://amel.fr/en/the-amel-story/",
            "source_name": "AMEL official history",
            "field": "production_identity",
            "value": "AMEL official history distinguishes Super Maramu 2000 from preceding Super Maramu with explicit production chronology",
            "unit": None,
            "basis": "AMEL official builder history",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.manualslib.com/products/Amel-Super-Maramu-2000-8825620.html",
            "source_name": "AMEL Super Maramu 2000 manual archive",
            "field": "manual_reference",
            "value": "owner-manual material provides preferred route for deeper systems and technical facts",
            "unit": None,
            "basis": "manual archive index",
            "tier": "A",
            "confidence": "medium",
        },
    ],
    "B03-008": [
        {
            "source_url": "https://www.moodyowners.org/Moody_Archives/17_boat.htm",
            "source_name": "Moody Owners archive Mk I",
            "field": "production_identity_mki",
            "value": "Moody 33 Mk I production period and count in owners archive; broadly same principal dimensions as Mk II",
            "unit": None,
            "basis": "Moody Owners archive",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.moodyowners.org/Moody_Archives/18_boat.htm",
            "source_name": "Moody Owners archive Mk II",
            "field": "production_identity_mkii",
            "value": "Moody 33 Mk II production period; Mk II changes concentrate on accommodation and cockpit not new underwater hull",
            "unit": None,
            "basis": "Moody Owners archive",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.moodyowners.info/threads/moody-33-mk1-vs-mk2.22269/",
            "source_name": "Moody Owners technical discussion",
            "field": "sail_area_definition",
            "value": "multiple sail-area definitions: rating/foretriangle-style area versus actual larger headsail plus main area",
            "unit": None,
            "basis": "owner technical discussion",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B04-001": [
        {
            "source_url": "https://www.yachtsnet.co.uk/archives/sadler-34/sadler-34.htm",
            "source_name": "Yachtsnet Sadler 34 archive",
            "field": "keel_options",
            "value": "deep fin, shallow fin and bilge/twin-keel forms documented; small number with centreboards inside shallow fins",
            "unit": None,
            "basis": "Yachtsnet archive",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.lucasyachting.co.uk/sadler-and-starlight/sadler-34-yacht/",
            "source_name": "Lucas Yachting Sadler archive",
            "field": "keel_option_count",
            "value": "four keel options documented; full-depth skeg-supported rudder",
            "unit": None,
            "basis": "Lucas Yachting",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.lucasyachting.co.uk/sadler-and-starlight/sadler-34-yacht/",
            "source_name": "Lucas Yachting Sadler archive",
            "field": "rudder_type",
            "value": "full-depth skeg-supported rudder",
            "unit": None,
            "basis": "Lucas Yachting description",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.yachtsnet.co.uk/archives/sadler-34/sadler-34.htm",
            "source_name": "Yachtsnet Sadler 34 archive",
            "field": "variant_note",
            "value": "34SE is an equipment/fitout upgrade using the same hull and rig",
            "unit": None,
            "basis": "Yachtsnet archive",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B04-002": [
        {
            "source_url": "https://www.albin-vega.de/die-albin-vega/",
            "source_name": "Deutsche Vega-Klassenvereinigung",
            "field": "production_chronology",
            "value": "class-association material distinguishes design/prototype/production chronology",
            "unit": None,
            "basis": "class association",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://albinvega.directory/library/",
            "source_name": "Albin Vega document library",
            "field": "sail_area_components",
            "value": "main and jib component areas listed separately not as one generic sail-area basis",
            "unit": None,
            "basis": "class document library",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://albinvegaforsale.wordpress.com/hull-deck/",
            "source_name": "Albin Vega owner construction description",
            "field": "keel_type",
            "value": "encapsulated shallow/long fin form; rudder attachment to aft keel region",
            "unit": None,
            "basis": "owner construction description",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B04-003": [
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-35-rasmus/",
            "source_name": "HR Club catalogue HR 35 Rasmus",
            "field": "production_start",
            "value": 1967,
            "unit": "year",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-35-rasmus/",
            "source_name": "HR Club catalogue HR 35 Rasmus",
            "field": "production_end",
            "value": 1978,
            "unit": "year",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-35-rasmus/",
            "source_name": "HR Club catalogue HR 35 Rasmus",
            "field": "units_built",
            "value": 760,
            "unit": "count",
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-35-rasmus/",
            "source_name": "HR Club catalogue HR 35 Rasmus",
            "field": "keel_type",
            "value": "long/full-bilged keel plus skeg-hung rudder",
            "unit": None,
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B04-004": [
        {
            "source_url": "https://www.seabear.uk/about-sea-bear-the-boat/",
            "source_name": "Vancouver 27 owner lineage account",
            "field": "lineage",
            "value": "Robert Harris original design with intertwined North American and British production history; separated from later Vancouver 28",
            "unit": None,
            "basis": "owner lineage account",
            "tier": "B",
            "confidence": "medium",
        },
        {
            "source_url": "https://portsmouth.boatshed.com/vancouver_27-boat-247111.html",
            "source_name": "Boatshed historical hull record",
            "field": "keel_type",
            "value": "long-keel form; structural skeg integrated with hull/keel extension",
            "unit": None,
            "basis": "historical hull record",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B04-005": [
        {
            "source_url": "https://sailingmagazine.net/article-1785-f-27.html",
            "source_name": "SAILING Magazine F-27 retrospective",
            "field": "units_built",
            "value": 450,
            "unit": "count",
            "basis": "specialist history approximate",
            "tier": "B",
            "confidence": "medium",
        },
        {
            "source_url": "https://sailingmagazine.net/article-1785-f-27.html",
            "source_name": "SAILING Magazine F-27 retrospective",
            "field": "folded_geometry_note",
            "value": "folded geometry is inherent to Farrier folding system not a cosmetic transport note",
            "unit": None,
            "basis": "SAILING retrospective",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://www.multihull.nl/multihulls/used-multihulls/F-27%20General/CorsairF27History.html",
            "source_name": "Farrier history",
            "field": "production_identity",
            "value": "Ian Farrier design mid-1980s production; named F-27 Sport Cruiser and later Corsair F-27",
            "unit": None,
            "basis": "Farrier history",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://www.practical-sailor.com/sailboat-reviews/f-27/",
            "source_name": "Practical Sailor F-27 review",
            "field": "displacement_note",
            "value": "secondary sources show some mass drift across publications",
            "unit": None,
            "basis": "Practical Sailor",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B04-006": [
        {
            "source_url": "https://sailingmagazine.net/article-permalink-554.html",
            "source_name": "SAILING Magazine Snowgoose 37 review",
            "field": "keel_type_baseline",
            "value": "earlier Snowgoose 37 with molded stub keels and lighter baseline",
            "unit": None,
            "basis": "SAILING Magazine review",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://www.svb.de/ownersclub/snowgoose-37-elite.html",
            "source_name": "SVB Snowgoose 37 Elite metadata",
            "field": "elite_identity",
            "value": "Snowgoose 37 Elite is materially wider and evolved not a harmless marketing suffix",
            "unit": None,
            "basis": "SVB Elite metadata",
            "tier": "B",
            "confidence": "high",
        },
    ],
    "B04-007": [
        {
            "source_url": "https://wiki.westerly-owners.co.uk/index.php?title=Konsort",
            "source_name": "Westerly Owners Association Wiki",
            "field": "keel_options",
            "value": "fin, twin and lifting keel variants documented",
            "unit": None,
            "basis": "WOA wiki",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://wiki.westerly-owners.co.uk/index.php?title=Konsort",
            "source_name": "Westerly Owners Association Wiki",
            "field": "rudder_type",
            "value": "transom-hung rudder confirmed",
            "unit": None,
            "basis": "WOA wiki and Yachting Monthly",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://yachtsnet.co.uk/archives/westerly-konsort/konsort.htm",
            "source_name": "Yachtsnet Westerly Konsort archive",
            "field": "production_count_note",
            "value": "WOA and Yachtsnet provide broadly consistent production history while differing in exact published count phrasing",
            "unit": None,
            "basis": "Yachtsnet archive",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B04-008": [
        {
            "source_url": "https://htcca.co.uk/ht-26-27/",
            "source_name": "HTCCA model history",
            "field": "generation_sequence",
            "value": "Mk1, Mk2, Mk2A (new hull mould, longer keels, central nacelle), Mk3 (new deck mould), and later New 27/HT27 generation changes documented",
            "unit": None,
            "basis": "HTCCA model history",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://htcca.co.uk/ht-description/",
            "source_name": "HTCCA technical description",
            "field": "multihull_dimensions",
            "value": "New 27 data includes multihull dimensions/mass and separated sail components",
            "unit": None,
            "basis": "HTCCA technical description",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-001": [
        {
            "source_url": "https://www.mycbc.ca/macgregor-buying-guide/?print=print",
            "source_name": "MacGregor Yacht Club of BC buying guide",
            "field": "model_family_distinction",
            "value": "D/S 26 Classic family sharply distinguished from later 26X/26M powersailers; D=daggerboard S=swing centreboard X=CB powersailer M=daggerboard powersailer with rotating mast and twin rudders",
            "unit": None,
            "basis": "MYCBC buying guide",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://www.practical-sailor.com/sailboat-reviews/macgregor-26m-used-boat-review/",
            "source_name": "Practical Sailor 26M lineage review",
            "field": "transition_year_note",
            "value": "independent sources give slightly different transition-year chronologies",
            "unit": None,
            "basis": "Practical Sailor",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B05-002": [
        {
            "source_url": "https://www.beneteau.com/newsroom-actualite/1977-2022-story-firsts",
            "source_name": "BENETEAU First history",
            "field": "lineage",
            "value": "BENETEAU identifies early Jean Berret First 35, later First 35S5, and much later Farr-designed First 35 generation",
            "unit": None,
            "basis": "BENETEAU official lineage",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.beneteau.com/first-1988-1992/first-35s5",
            "source_name": "BENETEAU First 35S5 heritage",
            "field": "variant_note",
            "value": "Carbon Edition is more plausibly a variant inside later generation than an unrelated hull",
            "unit": None,
            "basis": "BENETEAU heritage page",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-003": [
        {
            "source_url": "https://www.moodyowners.org/moody-boat-archive/",
            "source_name": "Moody Owners archive",
            "field": "lineage",
            "value": "archive explicitly separates 1980s Moody 36/36S/36DS from later 1990s Moody 36; later boat is Bill Dixon design with own production run and multiple keel configurations",
            "unit": None,
            "basis": "Moody Owners archive",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-004": [
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-352/",
            "source_name": "HR Club catalogue HR 352",
            "field": "mass_unit_issue",
            "value": "catalogue visibly contains malformed mass-unit presentation which must be preserved/flagged rather than blindly parsed",
            "unit": None,
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://oldshop.hallberg-rassy.com/contents/en-us/p3718_Rudder-Hallberg-Rassy-352.html",
            "source_name": "Hallberg-Rassy parts archive rudder",
            "field": "rudder_configuration",
            "value": "all 352s use the same rudder configuration; Enderlein rudder-skeg bearing",
            "unit": None,
            "basis": "HR parts archive",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-005": [
        {
            "source_url": "https://www.classicswan.org/swan_36.php",
            "source_name": "S&S Swan Association Swan 36",
            "field": "appendage_type",
            "value": "original Swan 36 is early S&S design with separated fin keel and skeg-hung rudder",
            "unit": None,
            "basis": "S&S Swan Association",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.nautorswan.com/yachts/models/clubswan36/",
            "source_name": "Nautor Swan ClubSwan 36 heritage",
            "field": "lineage_conflict",
            "value": "Nautor deliberately connects modern ClubSwan 36 to old Swan 36 as brand heritage not technical identity; radically different Juan Kouyoumdjian race design",
            "unit": None,
            "basis": "Nautor Swan heritage page",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-006": [
        {
            "source_url": "https://www.catalina36.org/about/history",
            "source_name": "Catalina 36/375 Association history",
            "field": "generation_transition",
            "value": "hull-number/year transition evidence for Mk II; underwater hull remained same; Mk II concentrated on stern/cockpit deck and interior changes",
            "unit": None,
            "basis": "Association history",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.catalina36.org/members/encyclopedias/c36-mki-specs",
            "source_name": "Catalina 36 Mk I specs",
            "field": "keel_options",
            "value": "Mk I and Mk II spec pages retain same core principal dimensions and keel-option pairs",
            "unit": None,
            "basis": "Association spec pages",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-007": [
        {
            "source_url": "https://dehler.com/de/geschichte/",
            "source_name": "Dehler history",
            "field": "lineage",
            "value": "Dehler identifies original 1980s Dehler 34, separate 2004-2009 model and current successor generation; current model invokes original as lineage/marketing context with own hull dimensions",
            "unit": None,
            "basis": "Dehler official history",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B05-008": [
        {
            "source_url": "https://goodoldboat.com/hunter-legend-37/",
            "source_name": "Good Old Boat Hunter Legend 37",
            "field": "lineage",
            "value": "owners material separates Hunter 37, Hunter 37 Legend, later 37.5 Legend and descendants; Legend is identity-critical context not decorative text",
            "unit": None,
            "basis": "Good Old Boat",
            "tier": "B",
            "confidence": "high",
        },
    ],
    "B06-001": [
        {
            "source_url": "https://www.ghcarchives.com/the-yachts/c-and-c-35-mk-ii",
            "source_name": "Great Lakes C&C design archive",
            "field": "lineage",
            "value": "original design traces through Redwing 35 / C&C 35; substantial 1973 Mk II redesign changed sheer/afterbody, rudder form, ballast/sail-plan and deck/cockpit geometry",
            "unit": None,
            "basis": "Great Lakes archive",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B06-002": [
        {
            "source_url": "https://hr-club.net/hr-catalogue/hr-312-mk-i/",
            "source_name": "HR Club catalogue HR 312 Mk I",
            "field": "generation_boundary",
            "value": "Mk II from mid-1980s; same core hull and rig; Mk II changes focus on superstructure cockpit interior and headroom",
            "unit": None,
            "basis": "HR Club catalogue",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.boat24.com/at/blog/hallberg-rassy-312/",
            "source_name": "Boat24 HR 312 article",
            "field": "mass_unit_issue",
            "value": "HR Club shows suspicious malformed mass-unit rendering reinforcing a source-family parsing problem",
            "unit": None,
            "basis": "Boat24 article",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B06-003": [
        {
            "source_url": "https://manualzz.com/doc/59388526/etap-32s-owner-s-manual",
            "source_name": "ETAP 32s owner's manual",
            "field": "draft_standard",
            "value": "standard and shallow/tandem keel configurations expose different draft, displacement and keel weight",
            "unit": None,
            "basis": "owner's manual standard configuration",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://manualzz.com/doc/59388526/etap-32s-owner-s-manual",
            "source_name": "ETAP 32s owner's manual",
            "field": "mass_basis",
            "value": "owner's manual also distinguishes net versus fully-loaded mass basis",
            "unit": None,
            "basis": "owner's manual",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.cruisingworld.com/sailboats/etap-32s-0/",
            "source_name": "Cruising World ETAP 32s",
            "field": "keel_type_tandem",
            "value": "tandem keel option: fore/aft foils joined at the bottom",
            "unit": None,
            "basis": "tandem keel option",
            "tier": "B",
            "confidence": "high",
        },
    ],
    "B06-004": [
        {
            "source_url": "https://pearson35.com/design-manuals/",
            "source_name": "Pearson 35 owner/design archive",
            "field": "applicability_warning",
            "value": "archive explicitly warns measurements apply to documented model year and may not represent full production run",
            "unit": None,
            "basis": "Pearson 35 archive explicit warning",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://pearson35.com/design-manuals/",
            "source_name": "Pearson 35 owner/design archive",
            "field": "draft_board_up",
            "value": "centerboard up draft state preserved",
            "unit": None,
            "basis": "board up",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://pearson35.com/design-manuals/",
            "source_name": "Pearson 35 owner/design archive",
            "field": "displacement_basis",
            "value": "Pearson-published lightship displacement distinct from separately constructed loaded figure",
            "unit": None,
            "basis": "Pearson 35 archive",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B06-005": [
        {
            "source_url": "https://www.practical-sailor.com/sailboat-reviews/ericson-35/",
            "source_name": "Practical Sailor Ericson 35",
            "field": "lineage",
            "value": "Practical Sailor distinguishes early CCA-style long-keel/attached-rudder boat, later Bruce King fin/spade design and another larger replacement generation; factory shoal/short-rig options exist inside later generations",
            "unit": None,
            "basis": "Practical Sailor",
            "tier": "B",
            "confidence": "high",
        },
        {
            "source_url": "https://ericsonyachts.org/ie/threads/e35-vs-e35-mkii-vs-e35mkiii-help.7909/",
            "source_name": "EricsonYachts owner discussion",
            "field": "lineage_uncertainty",
            "value": "experienced owners independently describe successive redesigns but differ in how directly II to III should be described as evolutionary lineage",
            "unit": None,
            "basis": "owner community discussion",
            "tier": "B",
            "confidence": "medium",
        },
    ],
    "B06-006": [
        {
            "source_url": "https://www.practical-sailor.com/sailboat-reviews/bristol-35-5c/",
            "source_name": "Practical Sailor Bristol 35.5C",
            "field": "suffix_semantics",
            "value": "Ted Hood centerboard cruiser; C suffix encodes configuration rather than a wholly unrelated hull",
            "unit": None,
            "basis": "Practical Sailor",
            "tier": "B",
            "confidence": "high",
        },
    ],
    "B06-007": [
        {
            "source_url": "https://manualzz.com/doc/23718176/gemini-105mc-catamaran-owner-s-manual",
            "source_name": "Gemini 105Mc owner's manual",
            "field": "board_configuration",
            "value": "one centerboard installed in each hull; pivoting/kick-up design; valid sailing procedures include both boards, leeward-only board or no boards depending on conditions",
            "unit": None,
            "basis": "owner's manual",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://manualzz.com/doc/23718176/gemini-105mc-catamaran-owner-s-manual",
            "source_name": "Gemini 105Mc owner's manual",
            "field": "rudder_count",
            "value": 2,
            "unit": "count",
            "basis": "twin spade rudders",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B06-008": [
        {
            "source_url": "https://jboats.com/j105-tech-specs",
            "source_name": "J/Boats J/105 tech specs",
            "field": "nominal_specs",
            "value": "J/Boats publishes nominal design geometry mass and sail information",
            "unit": None,
            "basis": "J/Boats nominal specification",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://j105.org/rules/",
            "source_name": "J/105 Class Association rules",
            "field": "class_rule_semantics",
            "value": "class association rules encode compliance limits, permitted variation, geometry and measurement procedure rather than automatically nominal production values",
            "unit": None,
            "basis": "class rules",
            "tier": "A",
            "confidence": "high",
        },
    ],
    "B06-009": [
        {
            "source_url": "https://www.emanualonline.com/marines/boats/bavaria/38/bavaria-38-2002-2003-owners-manual-emo-488088",
            "source_name": "Bavaria 38 owner's manual",
            "field": "keel_configuration",
            "value": "normal-keel versus lead-keel configurations expose different draft, ballast and ready-for-sailing mass",
            "unit": None,
            "basis": "owner's manual",
            "tier": "A",
            "confidence": "high",
        },
        {
            "source_url": "https://www.emanualonline.com/marines/boats/bavaria/38/bavaria-38-2002-2003-owners-manual-emo-488088",
            "source_name": "Bavaria 38 owner's manual",
            "field": "mass_basis",
            "value": "distinguishes empty-yacht mass from fully-equipped/crew mass",
            "unit": None,
            "basis": "owner's manual",
            "tier": "A",
            "confidence": "high",
        },
    ],
}

# Per-case aggregate crosscheck for W03-W06
_W03W06_CROSSCHECK: dict[str, tuple[ReferenceCheckOutcome, str]] = {
    "B03-001": (
        ReferenceCheckOutcome.NO_REFERENCE_RECORD_FOUND,
        "No reliable direct reference record located during this pass.",
    ),
    "B03-002": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Partial; configuration/basis coverage differs. No reference values retained.",
    ),
    "B03-003": (
        ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "Taxonomy conflict/partial match; reference wording less compatible with builder's keel-hung statement. No reference values retained.",
    ),
    "B03-004": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong ordinary-field agreement but taxonomy loses the more precise partial-skeg relationship.",
    ),
    "B03-005": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Partial; geometry broadly compatible but appendage relationship is incomplete and mass conflict remains unresolved.",
    ),
    "B03-006": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Partial/era difference. No reference values retained.",
    ),
    "B03-007": (
        ReferenceCheckOutcome.CONFLICT,
        "Chronology conflict with builder history. Only the conflict outcome is retained; reference dates are not stored.",
    ),
    "B03-008": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Partial/definition-compatible. No reference sail-area value retained.",
    ),
    "B04-001": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong baseline agreement but materially incomplete option coverage. No reference values retained.",
    ),
    "B04-002": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong ordinary-field agreement but chronology/draft differences remain research questions. Only outcome retained.",
    ),
    "B04-003": (
        ReferenceCheckOutcome.IDENTITY_DISAMBIGUATION_REQUIRED,
        "Identity/duplicate conflict: competing reference identities around Rasmus 35 / Hallberg-Rassy 35. No competing reference field values retained.",
    ),
    "B04-004": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Broadly compatible identity/keel family; extra reference-only details not admitted as evidence.",
    ),
    "B04-005": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong ordinary-field agreement; reference notes also expose folded-beam ambiguity. No reference values retained.",
    ),
    "B04-006": (
        ReferenceCheckOutcome.DEFINITION_OR_BASIS_DIFFERENCE,
        "Reference database also separates Snowgoose 37 from Snowgoose 37 Elite. No reference dimensions/mass retained.",
    ),
    "B04-007": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Partial/incomplete; reference foregrounds less of the configuration space and disagrees on some scalar metadata. No reference values retained.",
    ),
    "B04-008": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Broadly consistent generation distinctions; outcome only retained.",
    ),
    "B05-001": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Structurally useful and mostly consistent in separating D/S/X/M, while production-count applicability remains imperfect. Outcome only retained.",
    ),
    "B05-002": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Separate reference identities broadly validate the independent generation split, but synthetic reference suffixes are not canonical HullQ names.",
    ),
    "B05-003": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Structurally agrees on an earlier/later split. No reference values retained.",
    ),
    "B05-004": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong dimensional/count/chronology agreement and a mass-unit interpretation difference. Only outcome retained; reference mass values not stored.",
    ),
    "B05-005": (
        ReferenceCheckOutcome.CONFLICT,
        "Production-count conflict exists for the original model. Only the conflict outcome is retained.",
    ),
    "B05-006": (
        ReferenceCheckOutcome.MATCH,
        "Strongly consistent with the same-hull/rig interpretation. Outcome only retained.",
    ),
    "B05-007": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Reference separates multiple Dehler 34 generations and confirms the identity problem. Outcome only retained.",
    ),
    "B05-008": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Structural identity split agrees. No reference values retained.",
    ),
    "B06-001": (
        ReferenceCheckOutcome.MATCH,
        "Strong structural agreement on the split/redesign. No reference scalar values retained.",
    ),
    "B06-002": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong same-hull/sail-plan agreement. No reference values retained.",
    ),
    "B06-003": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Partial/strong option recognition but less semantic depth than the independent evidence. No reference values retained.",
    ),
    "B06-004": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong baseline compatibility but broader whole-run scope. No reference values retained.",
    ),
    "B06-005": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Strong structural confirmation of separate identities. No reference values retained.",
    ),
    "B06-006": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Compatible configuration interpretation. No reference board values retained.",
    ),
    "B06-007": (
        ReferenceCheckOutcome.MATCH,
        "Strong broad-identity/geometry compatibility. No reference dimensions retained.",
    ),
    "B06-008": (
        ReferenceCheckOutcome.MATCH,
        "Ordinary-field agreement; benchmark issue is semantic not numeric. No reference values retained.",
    ),
    "B06-009": (
        ReferenceCheckOutcome.PARTIAL_MATCH,
        "Matching reference identity structurally compatible; separate neighboring records reinforce need for identity disambiguation.",
    ),
}

# Explicit finding description for W03-W06 conflict cases
_W03W06_FINDING: dict[str, str] = {
    "B03-002": "Individual-hull mass values differ from builder Lightship Displacement; mass scope and basis require review before canonical resolution. Primary page incompleteness documented.",
    "B03-003": "Highly authoritative appendage taxonomy (keel-hung rudder, traditional long keel) versus hull-specific individual-hull numeric evidence must remain separate evidence classes.",
    "B03-005": "Mass and ballast observations differ among hull-specific and secondary records; swing-keel state, fixed grounding structure, twin-rudder count and protective-skeg relationship are separate facts requiring basis review.",
    "B03-007": "Related but distinct production identities (Super Maramu vs Super Maramu 2000) plus chronology verification conflict with builder chronology.",
    "B04-002": "Chronology-event semantics and chronology/draft differences remain research questions despite strong ordinary-field agreement.",
    "B04-003": "Competing reference identities around 'Rasmus 35' and 'Hallberg-Rassy 35'; string similarity is insufficient to select one; identity/duplicate conflict confirmed in reference.",
    "B04-005": "Sailing/folded geometry state, board state and historical naming must coexist without duplicate identity or hidden displacement scalar; secondary sources show mass drift.",
    "B04-006": "Model/evolution identity must be resolved before projecting a late individual hull onto the original Snowgoose 37 baseline; Elite is materially wider/evolved not a marketing suffix.",
    "B04-007": "Production count and displacement conflict among reputable sources (WOA, Yachtsnet) need review; lifting keel configuration changes both draft state and ballast simultaneously.",
    "B05-001": "MacGregor 26 is a model family with materially different hull/use/board/rudder/rig semantics across D/S/X/M variants; suffix syntax alone cannot decide the lineage relationship.",
    "B05-004": "HR Club catalogue contains malformed mass-unit presentation for the HR 352; source quality and observation validity are distinct; malformed units must be preserved/flagged not silently parsed.",
    "B05-005": "Production-count conflict for the original Swan 36 model; marketing heritage (Nautor connects ClubSwan 36 to original Swan 36) must remain separate from technical BoatDesign lineage.",
    "B06-002": "HR Club HR 312 catalogue repeats systematic malformed mass-unit presentation defect seen in HR 352; authoritative source family can repeat presentation problems.",
    "B06-005": "Same builder and model number reused across technically distinct Ericson 35 generations (CCA long keel, Bruce King fin/spade, larger replacement); even the lineage relation between generations can itself remain uncertain evidence.",
}


def _build_w3w6_bundle(
    case_id: str,
    facts: list[dict[str, Any]],
    research_target: ResearchTarget,
    wave: int,
) -> ResearchEvidenceBundle:
    bid = _bundle_id(case_id)
    observations: list[ResearchObservation] = []
    findings: list[UnresolvedFinding] = []

    for obs_idx, fact in enumerate(facts):
        raw_val = fact["value"]
        unit = fact.get("unit")
        basis = fact.get("basis", "")
        tier = fact.get("tier", "B")
        source_url = fact["source_url"]
        source_name = fact["source_name"]
        confidence_str = fact.get("confidence", "medium")
        field = fact.get("field", "observation")
        notes = fact.get("notes")

        if isinstance(raw_val, (int, float)):
            kind = RawObservationKind.LITERAL
        else:
            kind = RawObservationKind.TEXT_FRAGMENT

        oid = _obs_id(bid, obs_idx)
        observations.append(
            ResearchObservation(
                observation_id=oid,
                research_target=research_target,
                source_id=source_url,
                source_locator=_NULL_LOCATOR,
                raw=RawObservation(kind=kind, value=raw_val, unit=unit, excerpt=None),
                normalized_candidate=None,
                evidence_type=_map_evidence_type(tier, source_name),
                claim_semantics=_map_claim_semantics(field, basis),
                applicability=_map_applicability(basis),
                producer=_PRODUCER,
                research_context=_RESEARCH_CONTEXT,
                observed_at=_OBSERVED_AT,
                confidence=_map_confidence(confidence_str),
                supersedes_observation_id=None,
                intended_subject_kind_hint=None,
                intended_field_pointer=None,
                notes=notes,
            )
        )

    # Add finding for conflict cases
    if case_id in _CONFLICT_CASES:
        desc = _W03W06_FINDING.get(
            case_id,
            f"Retained conflict or unresolved question for {case_id} (wave {wave}).",
        )
        findings.append(
            UnresolvedFinding(
                finding_id=_finding_id(bid, 0),
                topic="conflict_or_unresolved_evidence",
                description=desc,
                related_observation_ids=frozenset(o.observation_id for o in observations),
                severity=UnresolvedFindingSeverity.REVIEW,
            )
        )

    crosscheck_outcome, crosscheck_notes = _W03W06_CROSSCHECK.get(
        case_id,
        (ReferenceCheckOutcome.NOT_CHECKED, "No crosscheck data available for this case."),
    )
    crosscheck = ReferenceCrosscheck(
        crosscheck_id=_crosscheck_id(bid),
        reference_source_id=REFERENCE_SOURCE_ID,
        topic_or_field=None,
        outcome=crosscheck_outcome,
        notes=crosscheck_notes,
    )

    return ResearchEvidenceBundle(
        bundle_id=bid,
        bundle_version=BUNDLE_VERSION,
        research_target=research_target,
        research_job_id=None,
        activity_id=ACTIVITY_ID,
        observations=tuple(observations),
        unresolved_findings=tuple(findings),
        promoted_evidence=(),
        reference_crosschecks=(crosscheck,),
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def load_manifest() -> dict[str, Any]:
    result: dict[str, Any] = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return result


def materialize_all() -> dict[str, MaterializationResult]:
    """Materialize all 50 benchmark bundles deterministically.

    Returns a dict mapping benchmark case ID to MaterializationResult.
    All 50 cases are expected to produce status=MATERIALIZED from retained
    evidence without invention.
    """
    manifest = load_manifest()
    results: dict[str, MaterializationResult] = {}

    # Build a lookup from case_id to manifest entry
    case_meta: dict[str, dict[str, Any]] = {c["benchmark_case_id"]: c for c in manifest["cases"]}

    # --- W01 rows grouped by design_id ---
    w01_rows = _decode_legacy_jsonl(1)
    w01_by_design: dict[str, list[dict[str, Any]]] = {}
    for row in w01_rows:
        w01_by_design.setdefault(row["design_id"], []).append(row)

    # --- W02 rows grouped by design_id ---
    w02_rows = _decode_legacy_jsonl(2)
    w02_by_design: dict[str, list[dict[str, Any]]] = {}
    for row in w02_rows:
        w02_by_design.setdefault(row["design_id"], []).append(row)

    # Materialize W01 cases (B01-*)
    for design_id, case_id in _DESIGN_TO_CASE.items():
        meta = case_meta[case_id]
        rt = ResearchTarget(
            manufacturer=meta["manufacturer"],
            model=meta["model"],
            first_built=meta.get("first_built"),
        )
        wave = meta["wave"]
        if wave == 1:
            rows = w01_by_design.get(design_id, [])
            finding_statuses = _W01_FINDING_STATUSES
        else:
            rows = w02_by_design.get(design_id, [])
            finding_statuses = _W02_FINDING_STATUSES

        bundle = _build_legacy_bundle(case_id, rows, rt, finding_statuses, wave)
        results[case_id] = MaterializationResult(
            case_id=case_id,
            status="MATERIALIZED",
            bundle=bundle,
        )

    # Materialize W03-W06 cases
    for case_id, facts in _W03W06_FACTS.items():
        meta = case_meta[case_id]
        rt = ResearchTarget(
            manufacturer=meta["manufacturer"],
            model=meta["model"],
            first_built=meta.get("first_built"),
        )
        wave = meta["wave"]
        bundle = _build_w3w6_bundle(case_id, facts, rt, wave)
        results[case_id] = MaterializationResult(
            case_id=case_id,
            status="MATERIALIZED",
            bundle=bundle,
        )

    return results
