"""SLICE-0039 Seed Corpus Wave 1 real multi-design search — local owner-test command.

Builds the locked four-design Wave-1 `DesignConfigurationSet` cohort --
BENETEAU Oceanis 30.1 (SLICE-0037, reused unchanged), BAVARIA Cruiser 34,
Contessa 32 and Lagoon 42 -- from retained, provenance-backed, non-fixture
projections and runs the unchanged Q1/Q2/Q10 query shapes from
`fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json`
through the existing `hullq.search.configuration_engine` kernel.

This script does not duplicate the evaluator: all truth is computed by
`hullq.search.configuration_engine.run_configuration_query`. It only loads
the three new retained real projections (plus the unchanged Oceanis 30.1
loader from `scripts.search_oceanis_30_1`) and formats the kernel's own
output.

See `research/benchmark/waves/sl0039-seed-corpus-wave1/REPORT.md` for the
full research narrative and exact evidence basis for each new design.

Run: uv run python scripts/search_seed_corpus_wave1.py
"""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Final

ROOT = Path(__file__).resolve().parents[1]
# Direct script invocation (`uv run python scripts/search_seed_corpus_wave1.py`,
# this slice's own owner-test command) puts only `scripts/` itself on
# `sys.path`, not the repository root -- so `scripts.search_oceanis_30_1`
# would not otherwise resolve as a package import. Ensure the root is present
# before importing it, so the same import works both under direct invocation
# and under pytest (which already puts the root on the path when run via
# `python -m pytest`).
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from hullq.domain.provenance import ResolutionState  # noqa: E402
from hullq.search.configuration import (  # noqa: E402
    ConfigurationIdentity,
    ConfigurationProjection,
    DesignConfigurationSet,
    ResolvedConfiguration,
)
from hullq.search.configuration_engine import (  # noqa: E402
    ConfigurationSearchOutcome,
    DesignQueryEvaluation,
    run_configuration_query,
)
from hullq.search.query_mixed import MixedAndQuery  # noqa: E402
from hullq.search.values import from_resolution_state  # noqa: E402
from scripts.search_oceanis_30_1 import (  # noqa: E402
    load_locked_queries,
    load_oceanis_30_1_configuration_set,
)

WAVE_DIR = ROOT / "research" / "benchmark" / "waves" / "sl0039-seed-corpus-wave1"

BAVARIA_PROJECTION_PATH = WAVE_DIR / "bavaria_cruiser_34_projection.v1.json"
CONTESSA_PROJECTION_PATH = WAVE_DIR / "contessa_32_projection.v1.json"
LAGOON_PROJECTION_PATH = WAVE_DIR / "lagoon_42_projection.v1.json"

#: Only Q1, Q2 and Q10 are in scope for this slice (SLICE-0039 "Locked cohort
#: and queries" -- Q3-Q9 are explicitly out of scope; no new SECONDARY query
#: is authorized). The shapes themselves are loaded unchanged from the same
#: accepted fixture SLICE-0037 used, via `load_locked_queries`.
WAVE1_QUERY_IDS: Final[tuple[str, ...]] = ("Q1", "Q2", "Q10")


class SeedCorpusProjectionAdmissionError(ValueError):
    """Raised when a retained Wave-1 projection JSON fails independent admission."""


# ---------------------------------------------------------------------------
# Shared independent admission oracle -- SLICE-0039
#
# Mirrors SLICE-0037's `validate_oceanis_30_1_projection` boundary ("A
# retained artifact MUST NOT self-authorize its own CONFIRMED state"), but
# parameterized by one small, immutable, code-side-only `_DesignOracle` per
# design instead of three independent ~150-line copies of the same checks.
# This is deliberately still slice-local (contained entirely in this file,
# not exported, not database/config-driven, no plugin/registration
# mechanism) -- the slice explicitly forbids generalizing the SLICE-0037
# pilot validator into a large framework "unless an independently
# demonstrated blocker requires it"; sharing the *validation logic* while
# keeping every expected value hardcoded per design is the smallest
# mechanism that still satisfies Required Behavior B for three designs
# without literal triplication of the oracle body.
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _AuthorizedFact:
    value: float
    evidence_refs: frozenset[str]
    direct_or_derived: str
    scope_id: str


@dataclass(frozen=True, slots=True)
class _DesignOracle:
    design_id: str
    configuration_space_complete: bool
    configuration_ids: frozenset[str]
    named_variant_ids: dict[str, str | None]
    allowed_evidence_source_ids: frozenset[str]
    configuration_evidence_refs: dict[str, frozenset[str]]
    authorized_numeric_facts: dict[tuple[str, str], _AuthorizedFact]
    authorized_categorical_facts: dict[tuple[str, str], _AuthorizedFact]


BAVARIA_STANDARD: Final = "bavaria-cruiser-34-standard-draft"
BAVARIA_SHOAL: Final = "bavaria-cruiser-34-shoal-draft-option"

BAVARIA_ORACLE: Final = _DesignOracle(
    design_id="bavaria-cruiser-34",
    configuration_space_complete=False,
    configuration_ids=frozenset({BAVARIA_STANDARD, BAVARIA_SHOAL}),
    named_variant_ids={
        BAVARIA_STANDARD: "standard-draft",
        BAVARIA_SHOAL: "shoal-draft-option",
    },
    allowed_evidence_source_ids=frozenset({"BAV-1"}),
    configuration_evidence_refs={
        BAVARIA_STANDARD: frozenset({"BAV-1"}),
        BAVARIA_SHOAL: frozenset({"BAV-1"}),
    },
    authorized_numeric_facts={
        (BAVARIA_STANDARD, "loa_m"): _AuthorizedFact(
            9.99, frozenset({"BAV-1"}), "direct", "design_wide"
        ),
        (BAVARIA_STANDARD, "beam_m"): _AuthorizedFact(
            3.42, frozenset({"BAV-1"}), "direct", "design_wide"
        ),
        (BAVARIA_STANDARD, "draft_max_m"): _AuthorizedFact(
            2.04, frozenset({"BAV-1"}), "direct", "standard_draft"
        ),
        (BAVARIA_SHOAL, "loa_m"): _AuthorizedFact(
            9.99, frozenset({"BAV-1"}), "direct", "design_wide"
        ),
        (BAVARIA_SHOAL, "beam_m"): _AuthorizedFact(
            3.42, frozenset({"BAV-1"}), "direct", "design_wide"
        ),
        (BAVARIA_SHOAL, "draft_max_m"): _AuthorizedFact(
            1.58, frozenset({"BAV-1"}), "direct", "shoal_draft_option"
        ),
    },
    authorized_categorical_facts={},
)

CONTESSA_BASELINE: Final = "contessa-32-baseline"

CONTESSA_ORACLE: Final = _DesignOracle(
    design_id="contessa-32",
    configuration_space_complete=False,
    configuration_ids=frozenset({CONTESSA_BASELINE}),
    named_variant_ids={CONTESSA_BASELINE: None},
    allowed_evidence_source_ids=frozenset({"CON-1", "CON-2", "CON-3", "CON-4", "CON-5"}),
    configuration_evidence_refs={CONTESSA_BASELINE: frozenset({"CON-1", "CON-2"})},
    # Deliberately empty: zero numeric/categorical facts are independently
    # authorized for Contessa 32 in this wave -- any field present in the
    # retained JSON at all, in any state, is rejected (see
    # `_validate_projection`'s "not in the independently authorized fact
    # set" branch).
    authorized_numeric_facts={},
    authorized_categorical_facts={},
)

LAGOON_STANDARD: Final = "lagoon-42-standard"

LAGOON_ORACLE: Final = _DesignOracle(
    design_id="lagoon-42",
    # REVIEW amendment: independent review correctly rejected the original
    # submission's `True` here -- absence of a stated second keel/draft
    # option on one product page does not prove the factory-relevant
    # configuration space is exhaustive, and even the strongest additional
    # evidence obtained (LAG-3, the official RCD-2 Owner's Manual) remains an
    # absence-of-mention, not an affirmative completeness statement. See
    # research/benchmark/waves/sl0039-seed-corpus-wave1/lagoon_42_projection.v1.json's
    # `configuration_space_complete_basis` for the full reasoning. The
    # oracle fixes this exact boolean in both directions: a tampered edit
    # back to `True` fails admission exactly like a tampered edit away from
    # `False` would for Bavaria/Contessa.
    configuration_space_complete=False,
    configuration_ids=frozenset({LAGOON_STANDARD}),
    named_variant_ids={LAGOON_STANDARD: None},
    allowed_evidence_source_ids=frozenset({"LAG-1", "LAG-2", "LAG-3"}),
    configuration_evidence_refs={LAGOON_STANDARD: frozenset({"LAG-1", "LAG-2", "LAG-3"})},
    authorized_numeric_facts={
        # REVIEW amendment: 12.92 m is LAG-3's "L.O.A (Lmax): standard"
        # figure; the previously authorized 13.22 m was LAG-1's unqualified
        # "Length overall", which LAG-3 reveals to be the spinnaker-pole-
        # inclusive maximum, not the standard LOA. Does not change any
        # Q1/Q2/Q10 result (12.92 m still exceeds both range upper bounds).
        (LAGOON_STANDARD, "loa_m"): _AuthorizedFact(
            12.92, frozenset({"LAG-3"}), "direct", "design_wide"
        ),
        (LAGOON_STANDARD, "beam_m"): _AuthorizedFact(
            7.68, frozenset({"LAG-1", "LAG-2", "LAG-3"}), "direct", "design_wide"
        ),
        (LAGOON_STANDARD, "draft_max_m"): _AuthorizedFact(
            1.26, frozenset({"LAG-1", "LAG-2", "LAG-3"}), "direct", "design_wide"
        ),
    },
    authorized_categorical_facts={},
)


def _validate_projection(payload: dict[str, Any], oracle: _DesignOracle) -> None:
    """Independently authorize *payload* against *oracle* before it may become Search input.

    Every check compares *payload* against the hardcoded oracle -- never
    against the payload's own claims about itself. Mirrors
    `scripts.search_oceanis_30_1.validate_oceanis_30_1_projection`.
    """
    design_id = payload.get("design_id")
    if design_id != oracle.design_id:
        raise SeedCorpusProjectionAdmissionError(
            f"design_id {design_id!r} does not match the independently authorized "
            f"{oracle.design_id!r}"
        )

    complete = payload.get("configuration_space_complete")
    if complete is not oracle.configuration_space_complete:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}: configuration_space_complete must be exactly "
            f"{oracle.configuration_space_complete!r} (independently required); got {complete!r}"
        )

    configs = payload.get("configurations")
    if not isinstance(configs, list):
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}: configurations must be a list"
        )

    seen_ids: set[str] = set()
    for config_data in configs:
        if not isinstance(config_data, dict):
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}: each configuration entry must be an object"
            )
        config_id = config_data.get("configuration_id")
        if config_id in seen_ids:
            raise SeedCorpusProjectionAdmissionError(f"duplicate configuration_id {config_id!r}")
        if isinstance(config_id, str):
            seen_ids.add(config_id)
        _validate_one_configuration(config_id, config_data, oracle)

    if seen_ids != oracle.configuration_ids:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}: configuration_id set {sorted(seen_ids)} does not match the "
            f"independently authorized set {sorted(oracle.configuration_ids)} -- no unexpected/"
            f"missing configuration is accepted merely because the retained JSON contains it"
        )


def _validate_one_configuration(
    config_id: object, config_data: dict[str, Any], oracle: _DesignOracle
) -> None:
    if config_id not in oracle.configuration_ids:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}: configuration_id {config_id!r} is not in the independently "
            f"authorized set {sorted(oracle.configuration_ids)}"
        )
    assert isinstance(config_id, str)

    named_variant_id = config_data.get("named_variant_id")
    expected_variant = oracle.named_variant_ids[config_id]
    if named_variant_id != expected_variant:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: named_variant_id {named_variant_id!r} does not "
            f"match the independently authorized {expected_variant!r}"
        )

    applied_option_ids = config_data.get("applied_option_ids")
    if not isinstance(applied_option_ids, list):
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: applied_option_ids must be a list; got "
            f"{applied_option_ids!r} ({type(applied_option_ids).__name__})"
        )
    if applied_option_ids != []:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: applied_option_ids {applied_option_ids!r} does not "
            f"match the independently authorized empty list -- no DesignOption is reviewed/"
            f"authorized for this wave"
        )

    config_evidence = _validate_evidence_refs(
        oracle,
        config_id,
        "configuration_evidence_refs",
        config_data.get("configuration_evidence_refs"),
    )
    required_config_evidence = oracle.configuration_evidence_refs[config_id]
    if not required_config_evidence.issubset(config_evidence):
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: configuration_evidence_refs "
            f"{sorted(config_evidence)} does not include the independently required "
            f"{sorted(required_config_evidence)}"
        )

    _validate_configuration_fields(
        oracle, config_id, "numeric_fields", config_data.get("numeric_fields", {})
    )
    _validate_configuration_fields(
        oracle, config_id, "categorical_fields", config_data.get("categorical_fields", {})
    )


def _validate_evidence_refs(
    oracle: _DesignOracle, config_id: str, label: str, raw: object
) -> frozenset[str]:
    if not isinstance(raw, list) or not raw:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: {label} must be a non-empty list"
        )
    refs = frozenset(raw)
    if len(refs) != len(raw):
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: {label} must not contain duplicates"
        )
    unknown = refs - oracle.allowed_evidence_source_ids
    if unknown:
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: {label} references source id(s) {sorted(unknown)} "
            f"not in the independently authorized evidence source set "
            f"{sorted(oracle.allowed_evidence_source_ids)}"
        )
    return refs


def _validate_configuration_fields(
    oracle: _DesignOracle, config_id: str, label: str, fields: object
) -> None:
    if not isinstance(fields, dict):
        raise SeedCorpusProjectionAdmissionError(
            f"{oracle.design_id}/{config_id}: {label} must be an object"
        )
    authorized = (
        oracle.authorized_numeric_facts
        if label == "numeric_fields"
        else oracle.authorized_categorical_facts
    )
    for field_name, field_data in fields.items():
        fact = authorized.get((config_id, field_name))
        if fact is None:
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name} is not in the "
                f"independently authorized fact set for this configuration -- present in the "
                f"retained JSON but not reviewed/accepted"
            )
        if not isinstance(field_data, dict):
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name} must be an object"
            )
        if field_data.get("state") != "resolved":
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name} has state "
                f"{field_data.get('state')!r}; the independently authorized fact requires "
                f"exactly 'resolved'"
            )
        value = field_data.get("value")
        if value != fact.value:
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name} value {value!r} does not "
                f"match the independently authorized value {fact.value!r}"
            )
        direct_or_derived = field_data.get("direct_or_derived")
        if direct_or_derived != fact.direct_or_derived:
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name}.direct_or_derived "
                f"{direct_or_derived!r} does not match the independently authorized "
                f"{fact.direct_or_derived!r}"
            )
        scope_id = field_data.get("scope_id")
        if scope_id != fact.scope_id:
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name}.scope_id {scope_id!r} "
                f"does not match the independently authorized {fact.scope_id!r}"
            )
        refs = _validate_evidence_refs(
            oracle,
            config_id,
            f"{label}.{field_name}.evidence_refs",
            field_data.get("evidence_refs"),
        )
        if refs != fact.evidence_refs:
            raise SeedCorpusProjectionAdmissionError(
                f"{oracle.design_id}/{config_id}: {label}.{field_name}.evidence_refs "
                f"{sorted(refs)} does not exactly match the independently authorized set "
                f"{sorted(fact.evidence_refs)}"
            )


def _load_configuration_set(path: Path, oracle: _DesignOracle) -> DesignConfigurationSet:
    """Load one retained Wave-1 projection JSON as a real (`is_fixture=False`) input.

    `_validate_projection` runs first and independently authorizes *payload*
    against *oracle* before any of it is materialized into Search input.
    """
    payload = json.loads(path.read_text(encoding="utf-8"))
    _validate_projection(payload, oracle)
    configurations = []
    for config_data in payload["configurations"]:
        numeric_values = {
            field_name: from_resolution_state(
                ResolutionState(field_data["state"]), field_data.get("value")
            )
            for field_name, field_data in config_data.get("numeric_fields", {}).items()
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
                    numeric_values=numeric_values, categorical_values={}
                ),
            )
        )
    return DesignConfigurationSet(
        design_id=payload["design_id"],
        configurations=tuple(configurations),
        configuration_space_complete=payload["configuration_space_complete"],
        is_fixture=False,
    )


def load_bavaria_cruiser_34_configuration_set(
    path: Path = BAVARIA_PROJECTION_PATH,
) -> DesignConfigurationSet:
    return _load_configuration_set(path, BAVARIA_ORACLE)


def load_contessa_32_configuration_set(
    path: Path = CONTESSA_PROJECTION_PATH,
) -> DesignConfigurationSet:
    return _load_configuration_set(path, CONTESSA_ORACLE)


def load_lagoon_42_configuration_set(path: Path = LAGOON_PROJECTION_PATH) -> DesignConfigurationSet:
    return _load_configuration_set(path, LAGOON_ORACLE)


def load_wave1_cohort() -> tuple[DesignConfigurationSet, ...]:
    """Build the exact locked four-design Wave-1 cohort.

    Oceanis 30.1 is reused unchanged from the accepted SLICE-0037 loader; the
    other three are the new real projections admitted above.
    """
    return (
        load_oceanis_30_1_configuration_set(),
        load_bavaria_cruiser_34_configuration_set(),
        load_contessa_32_configuration_set(),
        load_lagoon_42_configuration_set(),
    )


def load_wave1_queries() -> list[tuple[str, str, str, MixedAndQuery]]:
    """The unchanged Q1/Q2/Q10 shapes only, in that order (SLICE-0039 lock)."""
    all_queries = {q[0]: q for q in load_locked_queries()}
    return [all_queries[query_id] for query_id in WAVE1_QUERY_IDS]


def _print_design_evaluation(evaluation: DesignQueryEvaluation) -> None:
    reason = f" reason={evaluation.reason.value}" if evaluation.reason is not None else ""
    print(f"    {evaluation.design_id}: {evaluation.result_class.value}{reason}")
    for config_eval in evaluation.configuration_evaluations:
        print(
            f"        configuration={config_eval.configuration_id} truth={config_eval.truth.value}"
        )
    if evaluation.matching_configuration_ids:
        print(f"        matching_configuration_ids={list(evaluation.matching_configuration_ids)}")


def _print_query_outcome(
    query_id: str, description: str, outcome: ConfigurationSearchOutcome
) -> None:
    print(f"\n{query_id}  {description}")
    print("  corpus_size=4")
    print(f"  CONFIRMED_MATCH ({outcome.confirmed_match_count}):")
    for evaluation in outcome.confirmed_matches:
        _print_design_evaluation(evaluation)
    print(f"  CONFIRMED_NON_MATCH ({outcome.confirmed_non_match_count}):")
    for evaluation in outcome.confirmed_non_matches:
        _print_design_evaluation(evaluation)
    print(f"  INSUFFICIENT_DATA ({outcome.insufficient_data_count}):")
    for evaluation in outcome.insufficient_data:
        _print_design_evaluation(evaluation)


def main() -> dict[str, ConfigurationSearchOutcome]:
    print(
        "SEED CORPUS WAVE 1 -- 4 real BoatDesigns "
        "(BENETEAU Oceanis 30.1, BAVARIA Cruiser 34, Contessa 32, Lagoon 42)\n"
        "All four are is_fixture=False, independently admitted from retained evidence.\n"
        "See research/benchmark/waves/sl0039-seed-corpus-wave1/REPORT.md for the full "
        "research basis of the three new designs; the Oceanis 30.1 projection is reused "
        "unchanged from SLICE-0037."
    )
    cohort = load_wave1_cohort()
    queries = load_wave1_queries()
    results: dict[str, ConfigurationSearchOutcome] = {}
    for query_id, _role, description, query in queries:
        outcome = run_configuration_query(query, cohort)
        results[query_id] = outcome
        _print_query_outcome(query_id, description, outcome)

    print("\nSummary (design-level, per query):")
    for query_id in WAVE1_QUERY_IDS:
        outcome = results[query_id]
        match_ids = sorted(e.design_id for e in outcome.confirmed_matches)
        non_match_ids = sorted(e.design_id for e in outcome.confirmed_non_matches)
        insufficient_ids = sorted(e.design_id for e in outcome.insufficient_data)
        evaluable = outcome.confirmed_match_count + outcome.confirmed_non_match_count
        print(f"  {query_id}: evaluable={evaluable}/4")
        print(f"    CONFIRMED_MATCH: {match_ids}")
        print(f"    CONFIRMED_NON_MATCH: {non_match_ids}")
        print(f"    INSUFFICIENT_DATA: {insufficient_ids}")
    return results


if __name__ == "__main__":
    main()
