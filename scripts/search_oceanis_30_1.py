"""SLICE-0037 Oceanis 30.1 real-search pilot — local owner-test command.

Loads the retained, provenance-backed, non-fixture BENETEAU Oceanis 30.1
projection from
`research/benchmark/waves/sl0037-oceanis-30-1/oceanis_30_1_projection.v1.json`
(see that directory's `source_retrieval_log.json` for the bounded authoritative
source basis and `REPORT.md` for the full research narrative), builds a real
`hullq.search.configuration.DesignConfigurationSet` with `is_fixture=False`,
and runs the unchanged locked Q1-Q10 query shapes from
`fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json`
through the existing `hullq.search.configuration_engine` kernel.

This script does not duplicate the evaluator: all truth is computed by
`hullq.search.configuration_engine.run_configuration_query`. It only loads the
retained real projection and formats the kernel's own output.

Run: uv run python scripts/search_oceanis_30_1.py
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

from hullq.domain.provenance import ResolutionState
from hullq.search.configuration import (
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (
    ConfigurationSearchOutcome,
    DesignQueryEvaluation,
    run_configuration_query,
)
from hullq.search.query_mixed import MixedAndQuery, mixed_query_from_json_dict
from hullq.search.values import (
    QualifiedCategoricalValue,
    QualifiedNumericValue,
    from_resolution_state,
    from_resolution_state_categorical,
)

ROOT = Path(__file__).resolve().parents[1]
PROJECTION_PATH = (
    ROOT
    / "research"
    / "benchmark"
    / "waves"
    / "sl0037-oceanis-30-1"
    / "oceanis_30_1_projection.v1.json"
)
QUERIES_FIXTURE = (
    ROOT / "fixtures" / "search" / "query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json"
)


# ---------------------------------------------------------------------------
# Independent pilot admission oracle — REVIEW amendment (review 5067543634)
#
# SLICE-0037 Required Behavior A: "A retained artifact MUST NOT self-authorize
# its own CONFIRMED state." Everything below is a small, immutable,
# code/test-side reviewed description of exactly what independent review
# accepted for this one design. Every literal is hardcoded here; nothing here
# is read from `oceanis_30_1_projection.v1.json`. That file is edited freely
# as an ordinary research artifact; this oracle is not. A change to the
# retained JSON's values, evidence refs, configuration identities, or
# completeness flag can therefore never by itself authorize a different
# Search-admitted fact -- it can only cause `validate_oceanis_30_1_projection`
# to fail closed. This is deliberately scoped to this one pilot design; it is
# not a generic ingestion/admission framework (slice stop condition).
# ---------------------------------------------------------------------------

EXPECTED_DESIGN_ID: Final = "beneteau-oceanis-30-1"

DEEP_KEEL: Final = "oceanis-30-1-deep-keel"
SHALLOW_KEEL: Final = "oceanis-30-1-shallow-keel"
RETRACTABLE_KEEL: Final = "oceanis-30-1-retractable-keel"

EXPECTED_CONFIGURATION_IDS: Final[frozenset[str]] = frozenset(
    {DEEP_KEEL, SHALLOW_KEEL, RETRACTABLE_KEEL}
)

EXPECTED_NAMED_VARIANT_IDS: Final[dict[str, str]] = {
    DEEP_KEEL: "deep-draft-keel",
    SHALLOW_KEEL: "shallow-draft-keel",
    RETRACTABLE_KEEL: "performance-draft-hydraulic-swing-keel",
}

# No DesignOption is reviewed/authorized for this pilot -- every
# ConfigurationIdentity.applied_option_ids is independently required to be
# exactly empty. This module never infers or invents a DesignOption id.
EXPECTED_APPLIED_OPTION_IDS: Final[dict[str, tuple[str, ...]]] = {
    DEEP_KEEL: (),
    SHALLOW_KEEL: (),
    RETRACTABLE_KEEL: (),
}

# Only these three retained source documents (source_retrieval_log.json
# SRC-1/SRC-5/SRC-6) were independently reviewed and cleared to authorize a
# confirmed Search fact for this pilot. SRC-4 (pro.beneteauusa.com) is
# excluded by construction -- it is not a member of this set, deliberately,
# not merely absent by omission -- and any reference to it, or to any other
# unrecognized source id, is rejected below regardless of what
# `source_retrieval_log.json` separately claims.
ALLOWED_EVIDENCE_SOURCE_IDS: Final[frozenset[str]] = frozenset({"SRC-1", "SRC-5", "SRC-6"})

# Evidence establishing each configuration's own factory-supported *identity*
# (not any field's value) -- SRC-1's "There are 3 ballasts available ... Deep
# draft / Shallow draft / Performance draft (hydraulic swing keel)".
EXPECTED_CONFIGURATION_EVIDENCE_REFS: Final[dict[str, frozenset[str]]] = {
    DEEP_KEEL: frozenset({"SRC-1"}),
    SHALLOW_KEEL: frozenset({"SRC-1"}),
    RETRACTABLE_KEEL: frozenset({"SRC-1"}),
}


# Closed, pilot-specific scope vocabulary. "design_wide" means the fact does
# not vary by keel option; the two "*_fixed_keel" tokens bind a fact to
# exactly one of the two factory-named fixed-draft configurations. This is a
# machine-checked closed set, not a place for free-form prose -- REPORT.md's
# human-readable `scope` explanation remains for audit only and is never
# itself the authorizing mechanism.
_SCOPE_DESIGN_WIDE: Final = "design_wide"
_SCOPE_DEEP_FIXED_KEEL: Final = "deep_fixed_keel"
_SCOPE_SHALLOW_FIXED_KEEL: Final = "shallow_fixed_keel"


@dataclass(frozen=True, slots=True)
class _AuthorizedFact:
    value: float
    evidence_refs: frozenset[str]
    direct_or_derived: str
    scope_id: str


# The complete, closed set of Search facts this pilot's independent review
# authorizes, keyed by (configuration_id, field_name). A numeric or
# categorical field present in the retained JSON for a configuration that is
# NOT a key here is rejected outright, regardless of its value, state or
# evidence -- this is what makes an "unsupported new resolved field" or a
# "retractable draft promoted to resolved" adversarial edit fail closed.
# `evidence_refs` is the exact required set (not merely a minimum subset):
# an unrelated allowed source present alongside the genuinely required one(s)
# does not, by itself, authorize a fact whose evidence set no longer matches
# exactly. Every one of these eight facts is `direct_or_derived="direct"`;
# SLICE-0037 authorizes zero derived facts.
_AUTHORIZED_NUMERIC_FACTS: Final[dict[tuple[str, str], _AuthorizedFact]] = {
    (DEEP_KEEL, "loa_m"): _AuthorizedFact(
        9.53, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_DESIGN_WIDE
    ),
    (DEEP_KEEL, "beam_m"): _AuthorizedFact(
        2.99, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_DESIGN_WIDE
    ),
    (DEEP_KEEL, "draft_max_m"): _AuthorizedFact(
        1.85, frozenset({"SRC-6"}), "direct", _SCOPE_DEEP_FIXED_KEEL
    ),
    (SHALLOW_KEEL, "loa_m"): _AuthorizedFact(
        9.53, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_DESIGN_WIDE
    ),
    (SHALLOW_KEEL, "beam_m"): _AuthorizedFact(
        2.99, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_DESIGN_WIDE
    ),
    (SHALLOW_KEEL, "draft_max_m"): _AuthorizedFact(
        1.30, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_SHALLOW_FIXED_KEEL
    ),
    (RETRACTABLE_KEEL, "loa_m"): _AuthorizedFact(
        9.53, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_DESIGN_WIDE
    ),
    (RETRACTABLE_KEEL, "beam_m"): _AuthorizedFact(
        2.99, frozenset({"SRC-1", "SRC-6"}), "direct", _SCOPE_DESIGN_WIDE
    ),
    # Deliberately no (RETRACTABLE_KEEL, "draft_max_m") entry: no single
    # factory-resolved draft value is independently authorized for the
    # operator-adjustable configuration (REPORT.md section 3). Any such field
    # appearing in the retained JSON at all, in any state, is rejected.
}

# No categorical Search field is independently authorized for any
# configuration in this pilot (rig/keel-shape/rudder-support/cockpit-position
# all remain unresolved -- REPORT.md section 5). Left intentionally empty so
# that any categorical field present in the retained JSON is rejected.
_AUTHORIZED_CATEGORICAL_FACTS: Final[dict[tuple[str, str], _AuthorizedFact]] = {}


class OceanisProjectionAdmissionError(ValueError):
    """Raised when the retained projection JSON fails independent admission."""


def validate_oceanis_30_1_projection(payload: dict[str, Any]) -> None:
    """Independently authorize *payload* before it may become Search input.

    Every check below compares *payload* against the hardcoded oracle above
    -- never against the payload's own claims about itself (its own
    `configuration_basis` prose, its own declared completeness, or its own
    field list). A payload that is internally self-consistent but disagrees
    with the oracle on any single point is rejected, even where the
    disagreement would not change any Q1-Q10 Search result (e.g. a draft
    value edited to a still-same-threshold-side number).
    """
    design_id = payload.get("design_id")
    if design_id != EXPECTED_DESIGN_ID:
        raise OceanisProjectionAdmissionError(
            f"design_id {design_id!r} does not match the independently authorized "
            f"{EXPECTED_DESIGN_ID!r}"
        )

    complete = payload.get("configuration_space_complete")
    if complete is not False:
        raise OceanisProjectionAdmissionError(
            f"configuration_space_complete must be exactly False (independently "
            f"required -- completeness was never established for this pilot); "
            f"got {complete!r}"
        )

    configs = payload.get("configurations")
    if not isinstance(configs, list):
        raise OceanisProjectionAdmissionError("configurations must be a list")

    seen_ids: set[str] = set()
    for config_data in configs:
        if not isinstance(config_data, dict):
            raise OceanisProjectionAdmissionError("each configuration entry must be an object")
        config_id = config_data.get("configuration_id")
        if config_id in seen_ids:
            raise OceanisProjectionAdmissionError(f"duplicate configuration_id {config_id!r}")
        if isinstance(config_id, str):
            seen_ids.add(config_id)
        _validate_one_configuration(config_id, config_data)

    if seen_ids != EXPECTED_CONFIGURATION_IDS:
        raise OceanisProjectionAdmissionError(
            f"configuration_id set {sorted(seen_ids)} does not match the independently "
            f"authorized set {sorted(EXPECTED_CONFIGURATION_IDS)} -- no unexpected/missing "
            f"configuration is accepted merely because the retained JSON contains it"
        )


def _validate_one_configuration(config_id: object, config_data: dict[str, Any]) -> None:
    if config_id not in EXPECTED_CONFIGURATION_IDS:
        raise OceanisProjectionAdmissionError(
            f"configuration_id {config_id!r} is not in the independently authorized set "
            f"{sorted(EXPECTED_CONFIGURATION_IDS)}"
        )
    assert isinstance(config_id, str)

    named_variant_id = config_data.get("named_variant_id")
    expected_variant = EXPECTED_NAMED_VARIANT_IDS[config_id]
    if named_variant_id != expected_variant:
        raise OceanisProjectionAdmissionError(
            f"{config_id}: named_variant_id {named_variant_id!r} does not match the "
            f"independently authorized {expected_variant!r}"
        )

    applied_option_ids = config_data.get("applied_option_ids")
    if not isinstance(applied_option_ids, list):
        raise OceanisProjectionAdmissionError(
            f"{config_id}: applied_option_ids must be a list; got "
            f"{applied_option_ids!r} ({type(applied_option_ids).__name__})"
        )
    expected_options = EXPECTED_APPLIED_OPTION_IDS[config_id]
    if tuple(applied_option_ids) != expected_options:
        raise OceanisProjectionAdmissionError(
            f"{config_id}: applied_option_ids {applied_option_ids!r} does not match the "
            f"independently authorized {expected_options!r} -- no DesignOption is reviewed/"
            f"authorized for this pilot"
        )

    config_evidence = _validate_evidence_refs(
        config_id, "configuration_evidence_refs", config_data.get("configuration_evidence_refs")
    )
    required_config_evidence = EXPECTED_CONFIGURATION_EVIDENCE_REFS[config_id]
    if not required_config_evidence.issubset(config_evidence):
        raise OceanisProjectionAdmissionError(
            f"{config_id}: configuration_evidence_refs {sorted(config_evidence)} does not "
            f"include the independently required {sorted(required_config_evidence)}"
        )

    _validate_configuration_fields(
        config_id,
        "numeric_fields",
        config_data.get("numeric_fields", {}),
        _AUTHORIZED_NUMERIC_FACTS,
    )
    _validate_configuration_fields(
        config_id,
        "categorical_fields",
        config_data.get("categorical_fields", {}),
        _AUTHORIZED_CATEGORICAL_FACTS,
    )


def _validate_evidence_refs(config_id: str, label: str, raw: object) -> frozenset[str]:
    if not isinstance(raw, list) or not raw:
        raise OceanisProjectionAdmissionError(f"{config_id}: {label} must be a non-empty list")
    refs = frozenset(raw)
    if len(refs) != len(raw):
        raise OceanisProjectionAdmissionError(f"{config_id}: {label} must not contain duplicates")
    unknown = refs - ALLOWED_EVIDENCE_SOURCE_IDS
    if unknown:
        raise OceanisProjectionAdmissionError(
            f"{config_id}: {label} references source id(s) {sorted(unknown)} not in the "
            f"independently authorized evidence source set {sorted(ALLOWED_EVIDENCE_SOURCE_IDS)} "
            f"(SRC-4 and any unrecognized id are always rejected here, regardless of what "
            f"source_retrieval_log.json separately claims)"
        )
    return refs


def _validate_configuration_fields(
    config_id: str,
    label: str,
    fields: object,
    authorized: dict[tuple[str, str], _AuthorizedFact],
) -> None:
    if not isinstance(fields, dict):
        raise OceanisProjectionAdmissionError(f"{config_id}: {label} must be an object")
    for field_name, field_data in fields.items():
        fact = authorized.get((config_id, field_name))
        if fact is None:
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name} is not in the independently authorized "
                f"fact set for this configuration -- present in the retained JSON but not "
                f"reviewed/accepted"
            )
        if not isinstance(field_data, dict):
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name} must be an object"
            )
        if field_data.get("state") != "resolved":
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name} has state {field_data.get('state')!r}; the "
                f"independently authorized fact requires exactly 'resolved'"
            )
        value = field_data.get("value")
        if value != fact.value:
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name} value {value!r} does not match the "
                f"independently authorized value {fact.value!r} -- a changed value is rejected "
                f"even if it would not change any Q1-Q10 Search result"
            )
        direct_or_derived = field_data.get("direct_or_derived")
        if direct_or_derived != fact.direct_or_derived:
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name}.direct_or_derived {direct_or_derived!r} does "
                f"not match the independently authorized {fact.direct_or_derived!r} -- SLICE-0037 "
                f"authorizes zero derived facts"
            )
        scope_id = field_data.get("scope_id")
        if scope_id != fact.scope_id:
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name}.scope_id {scope_id!r} does not match the "
                f"independently authorized {fact.scope_id!r}"
            )
        refs = _validate_evidence_refs(
            config_id, f"{label}.{field_name}.evidence_refs", field_data.get("evidence_refs")
        )
        if refs != fact.evidence_refs:
            raise OceanisProjectionAdmissionError(
                f"{config_id}: {label}.{field_name}.evidence_refs {sorted(refs)} does not "
                f"exactly match the independently authorized set {sorted(fact.evidence_refs)} -- "
                f"an unrelated allowed source present alongside (or in place of) the genuinely "
                f"required source(s) does not authorize this fact"
            )


def _numeric_field(field_data: dict[str, Any]) -> QualifiedNumericValue:
    state = ResolutionState(field_data["state"])
    return from_resolution_state(state, field_data.get("value"))


def _categorical_field(field_data: dict[str, Any]) -> QualifiedCategoricalValue:
    state = ResolutionState(field_data["state"])
    return from_resolution_state_categorical(state, field_data.get("value"))


def load_oceanis_30_1_configuration_set(
    path: Path = PROJECTION_PATH,
) -> DesignConfigurationSet:
    """Load the retained real Oceanis 30.1 projection. `is_fixture=False`.

    `validate_oceanis_30_1_projection` runs first and independently
    authorizes *payload* against the hardcoded pilot oracle before any of it
    is materialized into Search input (SLICE-0037 Required Behavior A: "A
    retained artifact MUST NOT self-authorize its own CONFIRMED state") --
    this function itself never decides what to trust based on the payload's
    own claims. Only `numeric_fields`/`categorical_fields` entries actually
    present in the retained package (and now independently authorized) are
    projected; every field the research deliberately left unresolved (see
    the package's `fields_deliberately_left_unresolved_*` sections) is simply
    absent here, which `ConfigurationProjection.get_*` already treats as
    MISSING -- never as a confirmed value or a confirmed non-match.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    validate_oceanis_30_1_projection(payload)
    configurations = []
    for config_data in payload["configurations"]:
        numeric_values = {
            field_name: _numeric_field(field_data)
            for field_name, field_data in config_data.get("numeric_fields", {}).items()
        }
        categorical_values = {
            field_name: _categorical_field(field_data)
            for field_name, field_data in config_data.get("categorical_fields", {}).items()
        }
        configurations.append(
            ResolvedConfiguration(
                identity=ConfigurationIdentity(
                    configuration_id=config_data["configuration_id"],
                    boat_design_id=payload["design_id"],
                    named_variant_id=config_data.get("named_variant_id"),
                    applied_option_ids=tuple(config_data.get("applied_option_ids", ())),
                ),
                projection=ConfigurationProjection(
                    numeric_values=numeric_values, categorical_values=categorical_values
                ),
            )
        )
    return DesignConfigurationSet(
        design_id=payload["design_id"],
        configurations=tuple(configurations),
        configuration_space_complete=payload["configuration_space_complete"],
        is_fixture=False,
    )


def load_locked_queries(path: Path = QUERIES_FIXTURE) -> list[tuple[str, str, str, MixedAndQuery]]:
    """Load the exact locked Q1-Q10 (query_id, role, description, MixedAndQuery) shapes."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return [
        (
            entry["query_id"],
            entry["role"],
            entry["description"],
            mixed_query_from_json_dict(entry["query"]),
        )
        for entry in payload["queries"]
    ]


def _single_evaluation(outcome: ConfigurationSearchOutcome) -> DesignQueryEvaluation:
    all_evaluations = (
        outcome.confirmed_matches + outcome.confirmed_non_matches + outcome.insufficient_data
    )
    assert len(all_evaluations) == 1, "exactly one design (Oceanis 30.1) was queried"
    return all_evaluations[0]


def _print_result(
    query_id: str, role: str, description: str, evaluation: DesignQueryEvaluation
) -> None:
    reason = f" reason={evaluation.reason.value}" if evaluation.reason is not None else ""
    print(f"\n{query_id} [{role}] — {description}")
    print(f"  result_class={evaluation.result_class.value}{reason}")
    for config_eval in evaluation.configuration_evaluations:
        print(f"    configuration={config_eval.configuration_id} truth={config_eval.truth.value}")
        for criterion_eval in config_eval.criterion_evaluations:
            criterion_reason = (
                f" reason={criterion_eval.reason.value}"
                if criterion_eval.reason is not None
                else ""
            )
            print(
                f"        {criterion_eval.field}: {criterion_eval.truth.value}{criterion_reason} "
                f"({criterion_eval.explanation})"
            )
    if evaluation.matching_configuration_ids:
        print(f"  matching_configuration_ids={list(evaluation.matching_configuration_ids)}")


def main() -> dict[str, DesignQueryEvaluation]:
    print(
        "SLICE-0037 Oceanis 30.1 real-search pilot — REAL, provenance-backed "
        "BENETEAU Oceanis 30.1 projection (is_fixture=False), NOT synthetic fixture data.\n"
        "See research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md for the full "
        "bounded authoritative-source research basis.\n"
    )
    config_set = load_oceanis_30_1_configuration_set()
    queries = load_locked_queries()
    results: dict[str, DesignQueryEvaluation] = {}
    for query_id, role, description, query in queries:
        outcome = run_configuration_query(query, [config_set])
        evaluation = _single_evaluation(outcome)
        results[query_id] = evaluation
        _print_result(query_id, role, description, evaluation)

    match_ids = sorted(
        qid for qid, ev in results.items() if ev.result_class.value == "CONFIRMED_MATCH"
    )
    non_match_ids = sorted(
        qid for qid, ev in results.items() if ev.result_class.value == "CONFIRMED_NON_MATCH"
    )
    insufficient_ids = sorted(
        qid for qid, ev in results.items() if ev.result_class.value == "INSUFFICIENT_DATA"
    )
    print("\nSummary:")
    print(f"  CONFIRMED_MATCH: {match_ids}")
    print(f"  CONFIRMED_NON_MATCH: {non_match_ids}")
    print(f"  INSUFFICIENT_DATA: {insufficient_ids}")
    return results


if __name__ == "__main__":
    main()
