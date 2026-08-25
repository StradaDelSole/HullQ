"""SLICE-0025 Stage-3.2 breadth-sufficiency / Stage-3.3 parallel-entry
decision runner.

Two modes:

``--assemble``
    Fully offline given only already-retained SLICE-0018/0020/0021/0022/0023/
    0024 accepted artifacts: reproduces the fixed accepted evidence boundary,
    evaluates the four known breadth-path candidates and the parallel-
    readiness conditions, applies the precommitted decision rule via
    ``hullq.bootstrap.sl0025_breadth_enrichment_entry_decision``, and writes
    ``decision_input.json``, ``decision_result.json``, ``REPORT.md`` and
    ``ARTIFACT-DIGESTS.json`` under
    ``research/stage3/sl0025-breadth-enrichment-entry/``.

``--verify``
    Fully offline (zero network access): reloads every already-retained
    document, re-reproduces the accepted boundary from the retained
    SLICE-0018/0020/0021/0022/0023/0024 artifacts, and recomputes every
    structurally-derivable field purely from each document's own retained
    raw facts, plus the artifact digests. This is what normal CI runs.

Usage::

    uv run python scripts/bootstrap/sl0025_breadth_enrichment_entry_decision_runner.py --assemble
    uv run python scripts/bootstrap/sl0025_breadth_enrichment_entry_decision_runner.py --verify
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

SL0025_DIR = ROOT / "research" / "stage3" / "sl0025-breadth-enrichment-entry"
DECISION_INPUT_PATH = SL0025_DIR / "decision_input.json"
DECISION_INPUT_SCHEMA_PATH = SL0025_DIR / "decision_input_schema.json"
DECISION_RESULT_PATH = SL0025_DIR / "decision_result.json"
DECISION_RESULT_SCHEMA_PATH = SL0025_DIR / "decision_result_schema.json"
REPORT_PATH = SL0025_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0025_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0025_DIR / "ARTIFACT-DIGESTS.schema.json"

GENERATED_AT = "2026-08-25T00:00:00+00:00"


def _write_json_lf(path: Path, data: Any) -> None:
    """Write JSON with a guaranteed LF-only trailing-newline byte layout,
    independent of platform newline translation, so retained artifacts are
    byte-stable across Windows/Linux CI."""
    path.write_bytes((json.dumps(data, indent=2) + "\n").encode("utf-8"))


def _write_text_lf(path: Path, text: str) -> None:
    path.write_bytes(text.encode("utf-8"))


def _validate_schema(instance: dict[str, Any], schema_path: Path, *, label: str) -> None:
    if not schema_path.exists():
        return
    import jsonschema

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    jsonschema.validate(instance=instance, schema=schema)
    print(f"{label} schema validation: PASS", flush=True)


# ---------------------------------------------------------------------------
# Assemble
# ---------------------------------------------------------------------------


def run_assemble() -> None:
    from hullq.bootstrap.sl0025_breadth_enrichment_entry_decision import (
        build_decision_input_document,
        build_decision_result_document,
        build_known_breadth_path_candidates,
        load_reproduced_boundary,
    )

    reproduced = load_reproduced_boundary()
    candidates = build_known_breadth_path_candidates(reproduced)
    decision_input = build_decision_input_document(
        generated_at=GENERATED_AT, reproduced=reproduced, candidates=candidates
    )
    decision_result = build_decision_result_document(
        generated_at=GENERATED_AT, decision_input=decision_input
    )

    _validate_schema(decision_input, DECISION_INPUT_SCHEMA_PATH, label="decision_input")
    _validate_schema(decision_result, DECISION_RESULT_SCHEMA_PATH, label="decision_result")

    SL0025_DIR.mkdir(parents=True, exist_ok=True)
    _write_json_lf(DECISION_INPUT_PATH, decision_input)
    _write_json_lf(DECISION_RESULT_PATH, decision_result)

    report = _build_report(decision_input, decision_result)
    _write_text_lf(REPORT_PATH, report)

    digest_files = [
        "decision_input.json",
        "decision_input_schema.json",
        "decision_result.json",
        "decision_result_schema.json",
        "REPORT.md",
    ]
    digests = {}
    for name in digest_files:
        path = SL0025_DIR / name
        digests[name] = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    artifact_digests = {
        "schema_version": "sl0025-artifact-digests-v1",
        "generated_at": GENERATED_AT,
        "excludes_self": "ARTIFACT-DIGESTS.json",
        "digests": digests,
    }
    _validate_schema(artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="artifact_digests")
    _write_json_lf(ARTIFACT_DIGESTS_PATH, artifact_digests)

    print(f"Wrote {DECISION_INPUT_PATH}")
    print(f"Wrote {DECISION_RESULT_PATH}")
    print(f"Wrote {REPORT_PATH}")
    print(f"Wrote {ARTIFACT_DIGESTS_PATH}")
    print(f"decision: {decision_result['decision']}")


def _build_report(decision_input: dict[str, Any], decision_result: dict[str, Any]) -> str:
    reproduced = decision_input["reproduced_accepted_boundary"]
    lines = [
        "# HullQ SLICE-0025 Stage-3.2 Breadth Sufficiency / Stage-3.3 Parallel-Entry Decision Report",
        "",
        f"**Generated at:** {decision_result['generated_at']}  ",
        "**Type:** VALIDATION -- reproduces only already-accepted evidence, no new external "
        "research, no canonical mutation",
        "",
        "## Fixed accepted evidence boundary (reproduced from retained artifacts)",
        "",
    ]
    for key, value in reproduced.items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        f"- boundary mismatches: **{len(decision_result['boundary_mismatches'])}**",
        "",
        "## Known breadth-path candidates (rule 2)",
        "",
    ]
    for candidate in decision_input["known_breadth_path_candidates"]:
        lines.append(f"### `{candidate['name']}` ({candidate['source_slices']})")
        lines.append("")
        lines.append(f"- qualifies: **{candidate['qualifies']}**")
        lines.append(f"- already_executed: {candidate['already_executed']}")
        lines.append(f"- production_bulk_cleared: {candidate['production_bulk_cleared']}")
        lines.append(
            f"- materially_different_from_sl0018: {candidate['materially_different_from_sl0018']}"
        )
        lines.append(f"- likely_incremental_yield: {candidate['likely_incremental_yield']}")
        lines.append(
            f"- requires_full_wikimedia_campaign: {candidate['requires_full_wikimedia_campaign']}"
        )
        lines.append(
            "- requires_upstream_governance_decision: "
            f"{candidate['requires_upstream_governance_decision']}"
        )
        lines.append(f"- rationale: {candidate['rationale']}")
        lines.append("")
    lines += [
        "## Parallel-readiness conditions (rule 3)",
        "",
    ]
    readiness = decision_result["parallel_readiness_conditions"]
    if readiness is not None:
        for key, value in readiness.items():
            lines.append(f"- `{key}`: {value}")
    else:
        lines.append("- not evaluated (rule 1 or rule 2 already resolved the decision)")
    lines += [
        "",
        "## Decision (precommitted, mechanical rule)",
        "",
        f"- **{decision_result['decision']}**",
        "",
        "## Interpretation",
        "",
    ]
    for key, value in decision_result["interpretation"].items():
        lines.append(f"- `{key}`: {value}")
    lines += [
        "",
        "## Scope confirmation",
        "",
        "- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified "
        "or deleted.",
        "- No HullQ ID was minted.",
        "- No new external web/search/Wikidata/Wikipedia/manufacturer research was performed.",
        "- No source-rights decision was made or changed.",
        "- Stage 3.2 remains open regardless of the decision above.",
        "- This decision does not itself authorize Stage-3.4 critical-field enrichment, derived "
        "metrics expansion, query engine, API, frontend, SEO runtime, marketplace, accounts, "
        "alerts or price-history work.",
        "- SLICE-0026 was not created or started.",
        "",
    ]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------


def run_verify() -> None:
    from hullq.bootstrap.sl0025_breadth_enrichment_entry_decision import (
        evaluate_boundary_consistency,
        load_reproduced_boundary,
        verify_artifact_digests_self_consistency,
        verify_decision_result_self_consistency,
    )

    problems: list[str] = []

    reproduced = load_reproduced_boundary()
    live_mismatches = evaluate_boundary_consistency(reproduced)
    if live_mismatches:
        problems.extend(f"live re-reproduction: {m}" for m in live_mismatches)
    print(
        "live accepted-boundary re-reproduction: PASS" if not live_mismatches else "DRIFT DETECTED",
        flush=True,
    )

    decision_input = json.loads(DECISION_INPUT_PATH.read_bytes().decode("utf-8"))
    _validate_schema(decision_input, DECISION_INPUT_SCHEMA_PATH, label="decision_input")
    if decision_input["reproduced_accepted_boundary"] != reproduced:
        problems.append(
            "retained decision_input.reproduced_accepted_boundary != live re-reproduction"
        )

    decision_result = json.loads(DECISION_RESULT_PATH.read_bytes().decode("utf-8"))
    _validate_schema(decision_result, DECISION_RESULT_SCHEMA_PATH, label="decision_result")
    problems.extend(
        verify_decision_result_self_consistency(
            decision_input=decision_input, decision_result=decision_result
        )
    )

    print(f"decision: {decision_result['decision']}", flush=True)

    artifact_digests = json.loads(ARTIFACT_DIGESTS_PATH.read_bytes().decode("utf-8"))
    _validate_schema(artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="artifact_digests")
    problems.extend(
        verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0025_DIR
        )
    )

    if problems:
        print("VERIFICATION FAILED:", flush=True)
        for p in problems:
            print(f"  - {p}", flush=True)
        raise SystemExit(1)

    print("SLICE-0025 offline verification: PASS", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--assemble", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()

    if args.assemble:
        run_assemble()
    elif args.verify:
        run_verify()


if __name__ == "__main__":
    main()
