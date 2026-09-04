"""SLICE-0044 Gate-1 marketplace fact/field contract owner-inspection.

Deterministic, offline demonstration that
`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` satisfies
`specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json` and the adversarial
semantics required by `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`: independent
subject/assertion-kind/presentation/search/requiredness/phase/risk
classification, UNKNOWN vs ABSENT vs NO_KNOWN_HISTORY_DECLARED distinctness,
no Design -> PhysicalBoat auto-projection, CONFLICT never satisfying hard
search, non-destructive same-authority correction, cross-source overwrite
rejection, documentation-declared-available independence from attachment/
verification, mandatory sensitive presentation policy, free-text
non-promotion, and conditional price requiredness.

This is a DESIGN_RESEARCH contract with no production persistence/runtime:
this script loads the registry JSON directly and evaluates the same kind of
TEST-ONLY reference logic used in
`tests/contract/test_marketplace_fact_contract.py`. No `src/hullq` module is
imported; nothing here is shipped as production inference/resolution code.

Run: uv run python scripts/inspect_marketplace_field_contract.py
"""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
REGISTRY_PATH = SPECS / "MARKETPLACE_FIELD_REGISTRY.v0.1.json"
SCHEMA_NAME = "MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json"


def _load_registry() -> dict[str, Any]:
    raw: object = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise TypeError(f"Registry root must be a JSON object, got {type(raw).__name__}")
    return raw


@dataclass(frozen=True)
class _Observation:
    observation_id: str
    claim_authority: str
    value: str
    supersedes_observation_id: str | None = None


@dataclass(frozen=True)
class _ResolutionResult:
    state: str
    value: str | None


def _resolve_fact_topic(observations: list[_Observation]) -> _ResolutionResult:
    """TEST-ONLY reference resolver; see the equivalent, independently
    written implementation in tests/contract/test_marketplace_fact_contract.py
    for the full explanation of the grouping-by-authority mechanism."""
    if not observations:
        return _ResolutionResult(state="UNRESOLVED", value=None)
    by_authority: dict[str, list[_Observation]] = defaultdict(list)
    for observation in observations:
        by_authority[observation.claim_authority].append(observation)
    current_value_by_authority: dict[str, str] = {}
    for _authority, own_observations in by_authority.items():
        superseded_ids = {
            o.supersedes_observation_id for o in own_observations if o.supersedes_observation_id
        }
        current = [o for o in own_observations if o.observation_id not in superseded_ids]
        distinct_current_values = {o.value for o in current}
        if len(distinct_current_values) != 1:
            return _ResolutionResult(state="CONFLICT", value=None)
        current_value_by_authority[_authority] = next(iter(distinct_current_values))
    distinct_cross_source_values = set(current_value_by_authority.values())
    if len(distinct_cross_source_values) == 1:
        return _ResolutionResult(state="RESOLVED", value=next(iter(distinct_cross_source_values)))
    return _ResolutionResult(state="CONFLICT", value=None)


def _satisfies_hard_required(resolution: _ResolutionResult, required_value: str) -> bool:
    return resolution.state == "RESOLVED" and resolution.value == required_value


def _validate_price(price_mode: str, amount: float | None, currency: str | None) -> bool:
    if price_mode == "AMOUNT":
        return amount is not None and currency is not None
    if price_mode == "POA":
        return amount is None
    raise ValueError(f"unrecognized price_mode {price_mode!r}")


def _physical_boat_value(
    field: str, physical_observations: dict[str, str], design_reference_values: dict[str, str]
) -> str:
    return physical_observations.get(field, "UNKNOWN")


@dataclass(frozen=True)
class _RefitTiming:
    precision: str
    exact_year: int | None = None
    exact_date: str | None = None
    approximate_period: str | None = None


def _is_valid_iso_calendar_date(value: str) -> bool:
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _validate_refit_timing(timing: _RefitTiming) -> bool:
    exact_year = timing.exact_year
    exact_date = timing.exact_date
    approximate_period = timing.approximate_period

    if timing.precision == "EXACT":
        if approximate_period is not None:
            return False
        if (exact_year is None) == (exact_date is None):
            return False
        return exact_date is None or _is_valid_iso_calendar_date(exact_date)

    if timing.precision == "APPROXIMATE":
        if exact_year is not None or exact_date is not None:
            return False
        return approximate_period is not None and bool(approximate_period.strip())

    if timing.precision == "UNKNOWN":
        return exact_year is None and exact_date is None and approximate_period is None

    raise ValueError(f"unrecognized precision {timing.precision!r}")


def _validate_refit_category(category: str, allowed: frozenset[str]) -> bool:
    return category in allowed


def _validate_broad_use_history(
    assertion_kind: str, values: list[str] | None, allowed: frozenset[str]
) -> bool:
    if assertion_kind == "UNKNOWN":
        return values is None
    if assertion_kind == "VALUE_ASSERTION":
        if not values:
            return False
        if len(values) != len(set(values)):
            return False
        return set(values) <= allowed
    raise ValueError(f"unrecognized assertion_kind {assertion_kind!r}")


@dataclass(frozen=True)
class _UseHistoryObservation:
    observation_id: str
    claim_authority: str
    assertion_kind: str
    values: frozenset[str] | None = None
    supersedes_observation_id: str | None = None


@dataclass(frozen=True)
class _UseHistoryResolution:
    known_positive_uses: frozenset[str]
    by_authority: dict[str, frozenset[str] | None]


def _resolve_broad_use_history(
    observations: list[_UseHistoryObservation],
) -> _UseHistoryResolution:
    """TEST-ONLY open-world resolver; see the equivalent, independently
    written implementation in tests/contract/test_marketplace_fact_contract.py
    for the full explanation. Deliberately distinct from _resolve_fact_topic:
    there is no CONFLICT state here at all -- positive sets from different
    sources are additive, never competing, and the union is presentation
    convenience only, never a stronger jointly-verified fact."""
    by_authority_observations: dict[str, list[_UseHistoryObservation]] = defaultdict(list)
    for observation in observations:
        by_authority_observations[observation.claim_authority].append(observation)

    current_by_authority: dict[str, frozenset[str] | None] = {}
    aggregate: set[str] = set()
    for authority, own_observations in by_authority_observations.items():
        superseded_ids = {
            o.supersedes_observation_id for o in own_observations if o.supersedes_observation_id
        }
        current = [o for o in own_observations if o.observation_id not in superseded_ids]
        distinct_current = {(o.assertion_kind, o.values) for o in current}
        if len(distinct_current) != 1:
            continue
        assertion_kind, values = next(iter(distinct_current))
        if assertion_kind == "VALUE_ASSERTION":
            current_by_authority[authority] = values
            if values:
                aggregate |= values
        else:
            current_by_authority[authority] = None

    return _UseHistoryResolution(
        known_positive_uses=frozenset(aggregate), by_authority=current_by_authority
    )


def main() -> int:
    registry = _load_registry()
    contracts = ContractRegistry.from_directory(SPECS)
    fields: dict[str, dict[str, Any]] = registry["fields"]

    print("MARKETPLACE FACT CONTRACT\n")
    ok = True

    # -- schema validity ---------------------------------------------------
    schema_valid = True
    try:
        contracts.validator_by_name(SCHEMA_NAME).validate(registry)
    except Exception:
        schema_valid = False
    ok &= schema_valid

    # -- delivery phase / risk counts (real, not hard-coded) ----------------
    phase_counts: dict[str, int] = defaultdict(int)
    risk_counts: dict[str, int] = defaultdict(int)
    for entry in fields.values():
        phase_counts[entry["delivery_phase"]] += 1
        risk_counts[entry["claim_risk_class"]] += 1

    print(f"Gate-1 required          -> {phase_counts['GATE_1_REQUIRED']}")
    print(f"Gate-1 optional          -> {phase_counts['GATE_1_OPTIONAL']}")
    print(f"Later                    -> {phase_counts['LATER']}")
    print(f"Sensitive                -> {risk_counts['SENSITIVE']}\n")

    def _line(label: str, field_id: str, *, include_phase: bool = False) -> None:
        entry = fields[field_id]
        parts = [entry["subject"], entry["claim_risk_class"], entry["search_use"]]
        if include_phase:
            parts.append(entry["delivery_phase"])
        print(f"{label:<26} -> {' / '.join(parts)}")

    _line("price", "listing_offer.asking_price_mode")
    _line("broker description", "listing_offer.broker_description")
    _line("draft", "physical_boat.draft")
    _line("previous-owner count", "physical_boat.known_previous_owner_count")
    _line("refit events", "physical_boat.refit_events")
    _line("VAT/tax status", "listing_offer.vat_tax_status_claim", include_phase=True)
    _line("grounding history", "physical_boat.grounding_history", include_phase=True)
    print()

    # -- UNKNOWN vs ABSENT vs NO_KNOWN_HISTORY_DECLARED ---------------------
    grounding_kinds = set(fields["physical_boat.grounding_history"]["allowed_assertion_kinds"])
    engine_kinds = set(fields["physical_boat.engine_make"]["allowed_assertion_kinds"])
    unknown_vs_absent = "UNKNOWN" in engine_kinds and "ABSENT" in engine_kinds
    absent_vs_no_known_history = (
        "ABSENT" not in grounding_kinds
        and {
            "NO_KNOWN_HISTORY_DECLARED",
            "UNKNOWN",
        }
        <= grounding_kinds
    )
    ok &= unknown_vs_absent and absent_vs_no_known_history
    print(f"UNKNOWN vs ABSENT                    -> {'DISTINCT' if unknown_vs_absent else 'FAIL'}")
    print(
        "ABSENT vs NO_KNOWN_HISTORY_DECLARED -> "
        f"{'DISTINCT' if absent_vs_no_known_history else 'FAIL'}"
    )

    # -- design -> physical auto-projection ---------------------------------
    baseline = _physical_boat_value("draft", {}, {"draft": "1.65"})
    mutated = _physical_boat_value("draft", {}, {"draft": "9.99"})
    no_projection = baseline == "UNKNOWN" and mutated == "UNKNOWN"
    ok &= no_projection
    print(f"DESIGN -> PHYSICAL AUTO-PROJECTION   -> {'FORBIDDEN' if no_projection else 'FAIL'}")

    # -- conflict never satisfies hard search --------------------------------
    conflict_resolution = _resolve_fact_topic(
        [
            _Observation("A-1", "ORG-A", "2021"),
            _Observation("B-1", "ORG-B", "2022"),
        ]
    )
    conflict_blocked = (
        conflict_resolution.state == "CONFLICT"
        and not _satisfies_hard_required(conflict_resolution, "2021")
        and not _satisfies_hard_required(conflict_resolution, "2022")
    )
    ok &= conflict_blocked
    print(
        f"CONFLICT satisfies hard search       -> {'YES (FAIL)' if not conflict_blocked else 'NO'}"
    )

    # -- same-authority correction / cross-source overwrite ------------------
    correction = _resolve_fact_topic(
        [
            _Observation("A-1", "ORG-A", "2021"),
            _Observation("A-2", "ORG-A", "2022", supersedes_observation_id="A-1"),
        ]
    )
    correction_ok = correction == _ResolutionResult(state="RESOLVED", value="2022")
    cross_source_attempt = _resolve_fact_topic(
        [
            _Observation("A-1", "ORG-A", "2021"),
            _Observation("B-1", "ORG-B", "2022", supersedes_observation_id="A-1"),
        ]
    )
    cross_source_blocked = cross_source_attempt.state == "CONFLICT"
    ok &= correction_ok and cross_source_blocked
    print(
        "same-authority correction            -> "
        f"{'EXPLICIT SUPERSESSION' if correction_ok else 'FAIL'}"
    )
    print(
        f"cross-source overwrite               -> {'FORBIDDEN' if cross_source_blocked else 'FAIL'}"
    )

    # -- documentation declared available ------------------------------------
    doc_descriptor = registry["event_structures"]["refit_event_v0_1"][
        "supporting_documentation_declared_available"
    ]
    doc_states = set(doc_descriptor["values"])
    doc_independent = doc_states == {"YES", "NO", "UNKNOWN"} and not doc_states & {
        "ATTACHED",
        "REVIEWED",
        "VERIFIED",
    }
    ok &= doc_independent
    print(
        "document declared available          -> "
        f"{'NOT ATTACHED / NOT VERIFIED' if doc_independent else 'FAIL'}"
    )

    # -- refit timing: precision must match its actual temporal payload ------
    refit_timing_cases = [
        (_RefitTiming(precision="EXACT"), False),
        (_RefitTiming(precision="EXACT", exact_year=2022), True),
        (_RefitTiming(precision="EXACT", exact_date="2022-05-01"), True),
        (_RefitTiming(precision="EXACT", exact_year=2022, exact_date="2022-05-01"), False),
        (_RefitTiming(precision="EXACT", exact_date="2022-13-40"), False),
        (_RefitTiming(precision="APPROXIMATE"), False),
        (_RefitTiming(precision="APPROXIMATE", approximate_period="   "), False),
        (_RefitTiming(precision="APPROXIMATE", approximate_period="early 2020s"), True),
        (_RefitTiming(precision="UNKNOWN"), True),
        (_RefitTiming(precision="UNKNOWN", exact_year=2022), False),
    ]
    refit_timing_ok = all(
        _validate_refit_timing(timing) == expected for timing, expected in refit_timing_cases
    )
    ok &= refit_timing_ok
    print(f"refit timing payload matches precision -> {'PASS' if refit_timing_ok else 'FAIL'}")

    # -- refit category: closed Gate-1 vocabulary, not free text -------------
    refit_categories = frozenset(
        registry["event_structures"]["refit_event_v0_1"]["category"]["values"] or []
    )
    category_ok = _validate_refit_category(
        "RIGGING", refit_categories
    ) and not _validate_refit_category("PAINT_JOB", refit_categories)
    ok &= category_ok
    print(f"refit category vocabulary               -> {'BOUNDED' if category_ok else 'FAIL'}")

    # -- broad_use_history: bounded multi-value set, open-world resolution ---
    use_history_values = frozenset(
        fields["physical_boat.broad_use_history"]["value_type"]["values"] or []
    )
    use_history_valid_cases = _validate_broad_use_history(
        "UNKNOWN", None, use_history_values
    ) and _validate_broad_use_history("VALUE_ASSERTION", ["CHARTER", "PRIVATE"], use_history_values)
    use_history_invalid_cases = (
        not _validate_broad_use_history("UNKNOWN", ["PRIVATE"], use_history_values)
        and not _validate_broad_use_history(
            "VALUE_ASSERTION", ["PRIVATE", "PRIVATE"], use_history_values
        )
        and not _validate_broad_use_history("VALUE_ASSERTION", [], use_history_values)
    )
    not_conflict_subset = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation(
                "B-1", "ORG-B", "VALUE_ASSERTION", frozenset({"PRIVATE", "CHARTER"})
            ),
        ]
    ).known_positive_uses == frozenset({"PRIVATE", "CHARTER"})
    not_conflict_disjoint = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation("B-1", "ORG-B", "VALUE_ASSERTION", frozenset({"CHARTER"})),
        ]
    ).known_positive_uses == frozenset({"PRIVATE", "CHARTER"})
    unknown_does_not_erase = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "UNKNOWN", None),
            _UseHistoryObservation("B-1", "ORG-B", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
        ]
    ).known_positive_uses == frozenset({"PRIVATE"})
    supersession_ok = _resolve_broad_use_history(
        [
            _UseHistoryObservation("A-1", "ORG-A", "VALUE_ASSERTION", frozenset({"PRIVATE"})),
            _UseHistoryObservation(
                "A-2",
                "ORG-A",
                "VALUE_ASSERTION",
                frozenset({"PRIVATE", "CHARTER"}),
                supersedes_observation_id="A-1",
            ),
        ]
    ).by_authority == {"ORG-A": frozenset({"PRIVATE", "CHARTER"})}
    use_history_ok = (
        use_history_valid_cases
        and use_history_invalid_cases
        and not_conflict_subset
        and not_conflict_disjoint
        and unknown_does_not_erase
        and supersession_ok
    )
    ok &= use_history_ok
    print(f"broad_use_history open-world union      -> {'PASS' if use_history_ok else 'FAIL'}\n")

    # -- sensitive plain assertion forbidden ---------------------------------
    sensitive_fields = {
        fid: entry for fid, entry in fields.items() if entry["claim_risk_class"] == "SENSITIVE"
    }
    sensitive_ok = all(
        entry["search_use"] == "DISPLAY_ONLY" and entry["presentation_policy"] is not None
        for entry in sensitive_fields.values()
    )
    ok &= sensitive_ok
    print(f"sensitive plain assertion            -> {'FORBIDDEN' if sensitive_ok else 'FAIL'}")

    # -- free-text auto promotion forbidden ----------------------------------
    narrative_fields = {
        "listing_offer.broker_summary",
        "listing_offer.broker_description",
        "listing_offer.known_history_narrative",
    }
    free_text_ok = all(
        fields[fid]["search_use"] == "DISPLAY_ONLY"
        and fields[fid]["value_type"]["data_type"] == "free_text"
        for fid in narrative_fields
    )
    ok &= free_text_ok
    print(f"free-text auto promotion             -> {'FORBIDDEN' if free_text_ok else 'FAIL'}")

    # -- conditional price requiredness --------------------------------------
    price_truth_table = [
        (_validate_price("AMOUNT", None, "EUR"), False),
        (_validate_price("AMOUNT", 150000.0, None), False),
        (_validate_price("AMOUNT", 150000.0, "EUR"), True),
        (_validate_price("POA", None, None), True),
        (_validate_price("POA", 150000.0, None), False),
    ]
    price_ok = all(actual == expected for actual, expected in price_truth_table)
    ok &= price_ok
    print(f"conditional price requiredness       -> {'PASS' if price_ok else 'FAIL'}\n")

    print(f"MARKETPLACE FACT CONTRACT RESULT -> {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
