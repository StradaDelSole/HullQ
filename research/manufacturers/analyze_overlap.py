#!/usr/bin/env python3
"""Measure conservative exact-label overlap with accepted SLICE-0017/0018 models."""

from __future__ import annotations

import json
from collections.abc import Iterator
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
MANUFACTURERS = ROOT / "research" / "manufacturers"
STUDY = MANUFACTURERS / "source_yield_study.json"
OUT = MANUFACTURERS / "overlap_result.json"
MANIFESTS = [
    ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json",
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json",
]


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def walk(value: Any) -> Iterator[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def accepted_candidates(path: Path) -> list[dict[str, Any]]:
    manifest = load_json(path)
    result: list[dict[str, Any]] = []
    for item in walk(manifest):
        if item.get("decision") != "auto_admit":
            continue
        label = item.get("preferred_label")
        qid = item.get("qid")
        if isinstance(label, str) and isinstance(qid, str):
            result.append(
                {
                    "qid": qid,
                    "preferred_label": label,
                    "aliases": [
                        alias for alias in item.get("aliases", []) if isinstance(alias, str)
                    ],
                    "manifest": str(path.relative_to(ROOT)).replace("\\", "/"),
                }
            )
    return result


def main() -> None:
    accepted_by_qid: dict[str, dict[str, Any]] = {}
    for manifest_path in MANIFESTS:
        for candidate in accepted_candidates(manifest_path):
            accepted_by_qid[candidate["qid"]] = candidate

    assert len(accepted_by_qid) == 1770, (
        "accepted SLICE-0017/0018 AUTO_ADMIT union changed: "
        f"expected 1770, got {len(accepted_by_qid)}"
    )

    accepted = list(accepted_by_qid.values())
    preferred_exact: dict[str, list[dict[str, Any]]] = {}
    preferred_casefold: dict[str, list[dict[str, Any]]] = {}
    alias_exact: dict[str, list[dict[str, Any]]] = {}

    for candidate in accepted:
        label = candidate["preferred_label"]
        preferred_exact.setdefault(label, []).append(candidate)
        preferred_casefold.setdefault(label.casefold(), []).append(candidate)
        for alias in candidate["aliases"]:
            alias_exact.setdefault(alias, []).append(candidate)

    study = load_json(STUDY)
    entities = study["entities"]
    assert len(entities) == 20

    exact: list[dict[str, Any]] = []
    possible: list[dict[str, Any]] = []
    new_candidates: list[dict[str, Any]] = []
    per_entity: list[dict[str, Any]] = []

    probe_count = 0
    for entity in entities:
        name = entity["preferred_display_name"]
        probes = entity["probe_model_names"]
        entity_exact = 0
        entity_possible = 0
        entity_new = 0
        probe_count += len(probes)

        for probe in probes:
            base = {"manufacturer_sample": name, "probe_model_name": probe}
            if probe in preferred_exact:
                matches = preferred_exact[probe]
                exact.append({**base, "accepted_matches": matches})
                entity_exact += 1
                continue

            hints: list[dict[str, Any]] = []
            hint_reason: list[str] = []
            if probe in alias_exact:
                hints.extend(alias_exact[probe])
                hint_reason.append("exact_alias_only")
            case_matches = preferred_casefold.get(probe.casefold(), [])
            if case_matches:
                hints.extend(case_matches)
                hint_reason.append("casefold_preferred_label_only")

            if hints:
                deduped = {hint["qid"]: hint for hint in hints}
                possible.append(
                    {
                        **base,
                        "reason": sorted(set(hint_reason)),
                        "possible_matches": list(deduped.values()),
                    }
                )
                entity_possible += 1
            else:
                new_candidates.append(base)
                entity_new += 1

        per_entity.append(
            {
                "preferred_display_name": name,
                "probe_count": len(probes),
                "exact_overlap_count": entity_exact,
                "unresolved_possible_overlap_count": entity_possible,
                "clearly_new_candidate_count": entity_new,
            }
        )

    assert probe_count == 57, f"expected 57 exact-label probes, got {probe_count}"
    assert probe_count == len(exact) + len(possible) + len(new_candidates)

    result = {
        "result_version": "0019-overlap-v1",
        "generated_at": "2026-08-23T01:30:00Z",
        "method": (
            "Bounded source-yield probe only. Exact overlap requires exact, case-sensitive "
            "equality between a source-derived probe_model_name and the preferred_label of "
            "an AUTO_ADMIT candidate in the accepted SLICE-0017/0018 manifests. Exact alias "
            "or case-only signals are retained as unresolved possible overlap and never counted "
            "as overlap. No fuzzy matching is performed."
        ),
        "interpretation_guardrail": (
            "clearly_new_candidate_count means absent from the accepted exact preferred-label "
            "set and from the retained alias/case-only hint sets within this bounded probe. It "
            "does not prove global novelty or authorize canonical admission."
        ),
        "accepted_universe": {
            "auto_admit_qid_count": len(accepted_by_qid),
            "expected_canonical_boatmodel_count": 1770,
            "manifest_paths": [
                str(path.relative_to(ROOT)).replace("\\", "/") for path in MANIFESTS
            ],
        },
        "probe_summary": {
            "sample_entity_count": len(entities),
            "probe_model_identity_count": probe_count,
            "exact_overlap_count": len(exact),
            "unresolved_possible_overlap_count": len(possible),
            "clearly_new_candidate_count": len(new_candidates),
        },
        "per_entity": per_entity,
        "exact_overlap": exact,
        "unresolved_possible_overlap": possible,
        "clearly_new_candidates": new_candidates,
    }

    OUT.write_bytes(
        (json.dumps(result, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    )
    summary = result["probe_summary"]
    print("SLICE-0019 exact-label overlap probe complete")
    print(f"accepted_auto_admit_qids={len(accepted_by_qid)}")
    print(f"probe_model_identities={probe_count}")
    print(
        "exact_overlap={exact} unresolved_possible={possible} clearly_new={new}".format(
            exact=summary["exact_overlap_count"],
            possible=summary["unresolved_possible_overlap_count"],
            new=summary["clearly_new_candidate_count"],
        )
    )


if __name__ == "__main__":
    main()
