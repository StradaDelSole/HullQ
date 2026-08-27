"""SLICE-0029 primary-source BoatDesign applicability & conditional-clearance pilot — runner.

The bounded manual official-Catalina research (<=25 retrievals) that grounds this
pilot was performed interactively during implementation and is retained as data in
``research/stage3/sl0029-primary-source-boatdesign-applicability/``. This runner does
**not** perform any network acquisition itself; it only builds/verifies the
deterministic parts of the retained package (see
``hullq.bootstrap.wikidata_sl0029_boatdesign_applicability_pilot`` module docstring).

Modes
-----
``--verify``
    Fully offline, no network access. Loads every retained SLICE-0029 document plus
    the reused SLICE-0028 ``linkage.json`` / ``evidence_manifest.json`` and
    ``research/manufacturers/overlap_result.json``; validates each retained document
    against its own JSON Schema (and the embedded Source record additionally against
    ``specs/SOURCE_SCHEMA.v0.2.json``); recomputes and compares the pilot identity
    boundary, the retrieval-log ceiling/consistency, the source-use gate decisions
    (through the unmodified ``hullq.sources.rights.check_source_use``), every
    field-applicability cross-reference against the reused SLICE-0028 evidence, the
    final deterministic recommendation, and the retained-package artifact digests.
    This is the command CI runs.

``--build-digests``
    Offline. Recomputes ``ARTIFACT-DIGESTS.json`` from the current bytes of every
    other retained package file. Run this once after the retained JSON/REPORT.md
    documents reach their final content, then re-run ``--verify``.

Example:
    uv run python scripts/bootstrap/wikidata_sl0029_boatdesign_applicability_pilot_runner.py --build-digests
    uv run python scripts/bootstrap/wikidata_sl0029_boatdesign_applicability_pilot_runner.py --verify
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
SL0029_DIR = ROOT / "research" / "stage3" / "sl0029-primary-source-boatdesign-applicability"
SL0028_DIR = ROOT / "research" / "stage3" / "sl0028-wikidata-tier1-full-boundary"

IDENTITY_BOUNDARY_PATH = SL0029_DIR / "pilot_identity_boundary.json"
IDENTITY_BOUNDARY_SCHEMA_PATH = SL0029_DIR / "pilot_identity_boundary_schema.json"
RETRIEVAL_LOG_PATH = SL0029_DIR / "source_retrieval_log.json"
RETRIEVAL_LOG_SCHEMA_PATH = SL0029_DIR / "source_retrieval_log_schema.json"
CLEARANCE_PATH = SL0029_DIR / "source_clearance_assessment.json"
CLEARANCE_SCHEMA_PATH = SL0029_DIR / "source_clearance_assessment_schema.json"
BOATDESIGN_PATH = SL0029_DIR / "boatdesign_applicability.json"
BOATDESIGN_SCHEMA_PATH = SL0029_DIR / "boatdesign_applicability_schema.json"
FIELD_APPLICABILITY_PATH = SL0029_DIR / "wikidata_candidate_applicability.json"
FIELD_APPLICABILITY_SCHEMA_PATH = SL0029_DIR / "wikidata_candidate_applicability_schema.json"
REPORT_PATH = SL0029_DIR / "REPORT.md"
ARTIFACT_DIGESTS_PATH = SL0029_DIR / "ARTIFACT-DIGESTS.json"
ARTIFACT_DIGESTS_SCHEMA_PATH = SL0029_DIR / "artifact_digests_schema.json"

SOURCE_SCHEMA_PATH = ROOT / "specs" / "SOURCE_SCHEMA.v0.2.json"
OBSERVATION_APPLICABILITY_SCHEMA_PATH = (
    ROOT / "specs" / "OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json"
)

LINKAGE_PATH = SL0028_DIR / "linkage.json"
EVIDENCE_MANIFEST_PATH = SL0028_DIR / "evidence_manifest.json"
OVERLAP_RESULT_PATH = ROOT / "research" / "manufacturers" / "overlap_result.json"


def _write_text_lf(path: Path, text: str) -> None:
    """Write *text* as UTF-8 bytes with no newline translation, so a locally
    computed digest matches the digest of the LF-normalized bytes git stores."""
    path.write_bytes(text.encode("utf-8"))


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_schema(instance: Any, schema_path: Path, *, label: str) -> list[str]:
    if not schema_path.exists():
        return [f"required schema not found: {schema_path}"]
    import jsonschema

    schema = _load(schema_path)
    try:
        jsonschema.validate(instance=instance, schema=schema)
    except jsonschema.exceptions.ValidationError as exc:
        return [f"{label} failed schema validation: {exc.message} (path={list(exc.absolute_path)})"]
    print(f"{label} schema validation: PASS", flush=True)
    return []


def _validate_applicability_scopes(
    *, boatdesign: Any, field_applicability: Any, label_prefix: str
) -> list[str]:
    """Validate every retained ``applicability_scope`` object -- one per boat_model in
    boatdesign_applicability.json, one per field in wikidata_candidate_applicability.json
    -- against the real ``specs/OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json`` file."""
    problems: list[str] = []
    for model in boatdesign.get("boat_models", []):
        problems += _validate_schema(
            model["applicability_scope"],
            OBSERVATION_APPLICABILITY_SCHEMA_PATH,
            label=f"{label_prefix} boatdesign_applicability[{model['qid']}].applicability_scope",
        )
    for model in field_applicability.get("boat_models", []):
        for field in model.get("fields", []):
            problems += _validate_schema(
                field["applicability_scope"],
                OBSERVATION_APPLICABILITY_SCHEMA_PATH,
                label=(
                    f"{label_prefix} wikidata_candidate_applicability[{model['qid']}]"
                    f"[{field['field_pointer']}].applicability_scope"
                ),
            )
    return problems


def run_verify() -> None:
    from hullq.bootstrap import wikidata_sl0029_boatdesign_applicability_pilot as sl0029

    problems: list[str] = []
    print(
        "HullQ SLICE-0029 Primary-Source BoatDesign Applicability Pilot — VERIFY "
        "(offline, no network access)",
        flush=True,
    )

    linkage_document = _load(LINKAGE_PATH)
    overlap_result = _load(OVERLAP_RESULT_PATH)
    evidence_manifest = _load(EVIDENCE_MANIFEST_PATH)

    identity_boundary = _load(IDENTITY_BOUNDARY_PATH)
    problems += _validate_schema(
        identity_boundary, IDENTITY_BOUNDARY_SCHEMA_PATH, label="pilot_identity_boundary"
    )
    problems += sl0029.verify_pilot_identity_boundary_self_consistency(
        identity_boundary, linkage_document=linkage_document, overlap_result=overlap_result
    )
    print(
        f"  identity boundary: {len(identity_boundary['pilot_boat_models'])} pilot "
        "BoatModels reproduced from the accepted SLICE-0028 boundary",
        flush=True,
    )

    retrieval_log = _load(RETRIEVAL_LOG_PATH)
    problems += _validate_schema(
        retrieval_log, RETRIEVAL_LOG_SCHEMA_PATH, label="source_retrieval_log"
    )
    problems += sl0029.validate_source_retrieval_log(retrieval_log)
    print(
        f"  retrieval log: {retrieval_log['retrieval_count']} / {sl0029.RETRIEVAL_CEILING} "
        "bounded retrievals",
        flush=True,
    )

    clearance = _load(CLEARANCE_PATH)
    problems += _validate_schema(
        clearance, CLEARANCE_SCHEMA_PATH, label="source_clearance_assessment"
    )
    problems += _validate_schema(
        clearance["source_record"],
        SOURCE_SCHEMA_PATH,
        label="source_clearance_assessment.source_record (against specs/SOURCE_SCHEMA.v0.2.json)",
    )
    problems += sl0029.verify_source_clearance_assessment_self_consistency(
        clearance, pilot_identity_boundary=identity_boundary
    )
    gate = clearance["source_use_gate_decisions"]["decisions"]
    print(
        "  source-use gate (recomputed via hullq.sources.rights.check_source_use): "
        f"identity_seed={gate['identity_seed']['outcome']} "
        f"production_value={gate['production_value']['outcome']} "
        f"bulk_bootstrap={gate['bulk_bootstrap']['outcome']} "
        f"automated_ingestion={gate['automated_ingestion']['outcome']} "
        f"artifact_redistribution={gate['artifact_redistribution']['outcome']}",
        flush=True,
    )

    boatdesign = _load(BOATDESIGN_PATH)
    problems += _validate_schema(
        boatdesign, BOATDESIGN_SCHEMA_PATH, label="boatdesign_applicability"
    )
    problems += sl0029.validate_boatdesign_applicability(
        boatdesign, pilot_identity_boundary=identity_boundary
    )

    field_applicability = _load(FIELD_APPLICABILITY_PATH)
    problems += _validate_schema(
        field_applicability,
        FIELD_APPLICABILITY_SCHEMA_PATH,
        label="wikidata_candidate_applicability",
    )
    problems += sl0029.validate_wikidata_candidate_applicability(
        field_applicability,
        pilot_identity_boundary=identity_boundary,
        evidence_manifest=evidence_manifest,
    )
    problems += _validate_applicability_scopes(
        boatdesign=boatdesign, field_applicability=field_applicability, label_prefix="  "
    )

    recommendation = sl0029.compute_recommendation(
        source_use_gate_decisions=gate,
        boatdesign_applicability=boatdesign,
        wikidata_candidate_applicability=field_applicability,
    )
    print(f"  recomputed deterministic recommendation: {recommendation}", flush=True)

    if REPORT_PATH.exists():
        report_text = REPORT_PATH.read_text(encoding="utf-8")
        if recommendation not in report_text:
            problems.append(
                f"recomputed recommendation {recommendation!r} not found verbatim in REPORT.md"
            )
    else:
        problems.append(f"REPORT.md not found at {REPORT_PATH}")

    if ARTIFACT_DIGESTS_PATH.exists():
        artifact_digests = _load(ARTIFACT_DIGESTS_PATH)
        problems += _validate_schema(
            artifact_digests, ARTIFACT_DIGESTS_SCHEMA_PATH, label="ARTIFACT-DIGESTS"
        )
        problems += sl0029.verify_artifact_digests_self_consistency(
            artifact_digests=artifact_digests, package_dir=SL0029_DIR
        )
    else:
        problems.append(f"ARTIFACT-DIGESTS.json not found at {ARTIFACT_DIGESTS_PATH}")

    if problems:
        print("VERIFY: FAIL", flush=True)
        for p in problems:
            print(f"  - {p}", flush=True)
        raise SystemExit(1)
    print("VERIFY: PASS", flush=True)


def run_build_digests() -> None:
    from hullq.bootstrap import wikidata_sl0029_boatdesign_applicability_pilot as sl0029

    document = sl0029.build_artifact_digests(
        generated_at=datetime.now(tz=UTC).isoformat(), package_dir=SL0029_DIR
    )
    _write_text_lf(ARTIFACT_DIGESTS_PATH, json.dumps(document, indent=2) + "\n")
    print(f"ARTIFACT-DIGESTS.json written to: {ARTIFACT_DIGESTS_PATH}", flush=True)
    for name, digest in document["digests"].items():
        print(f"  {name}: {digest}", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--verify", action="store_true")
    mode.add_argument("--build-digests", action="store_true")
    args = parser.parse_args()

    if args.verify:
        run_verify()
    elif args.build_digests:
        run_build_digests()


if __name__ == "__main__":
    main()
