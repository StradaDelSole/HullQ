#!/usr/bin/env python3
"""SLICE-0020 bounded identity-pilot overlap computation.

Deterministic, repository-local, exact/unambiguous-first overlap check between
the 100 source-presented model identities supplied by the ChatGPT-led external
research pass and the accepted SLICE-0017/0018 union of AUTO_ADMIT BoatModel
candidates (1,770 records). No fuzzy matching, no manufacturer-prefix
insertion/removal, no token reordering, no punctuation rewriting, no
generation collapsing. Matching is case-insensitive with surrounding-whitespace
trimming only -- internal whitespace is never collapsed or otherwise
normalized, per SLICE-0020's bounded identity-yield pilot rules.

This script performs no external research and reads only already-accepted
repository artifacts (research/bootstrap/wikidata/manifest.json and
research/bootstrap/wikidata/sl0018-2500/manifest.json) plus the pilot model
names captured in archive_identity_pilot_input.py in this directory.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from archive_identity_pilot_input import SOURCES

ROOT = Path(__file__).resolve().parents[3]
MANIFESTS = [
    ROOT / "research" / "bootstrap" / "wikidata" / "manifest.json",
    ROOT / "research" / "bootstrap" / "wikidata" / "sl0018-2500" / "manifest.json",
]
OUT = Path(__file__).resolve().parent / "archive_identity_pilot.json"

EXPECTED_UNION_COUNT = 1770
EXPECTED_SOURCE_COUNT = 10
EXPECTED_PER_SOURCE_COUNT = 10
EXPECTED_TOTAL_COUNT = 100


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def normalize(value: str) -> str:
    """Case-insensitive with surrounding-whitespace trimming only.

    Internal whitespace is deliberately NOT collapsed or otherwise touched:
    "First  26" (double internal space) must remain distinct from "First 26"
    under this slice's exact-match rule.
    """

    return value.strip().casefold()


def build_accepted_universe() -> tuple[dict[str, dict[str, Any]], dict[str, set[str]]]:
    """Return (hullq_id -> candidate record, normalized_key -> set of matching hullq_ids)."""

    accepted_by_id: dict[str, dict[str, Any]] = {}
    for manifest_path in MANIFESTS:
        manifest = load_json(manifest_path)
        for candidate in manifest["candidates"]:
            if candidate.get("decision") != "auto_admit":
                continue
            hullq_id = candidate["hullq_id"]
            if hullq_id is None:
                continue
            accepted_by_id[hullq_id] = candidate

    assert len(accepted_by_id) == EXPECTED_UNION_COUNT, (
        "accepted SLICE-0017/0018 AUTO_ADMIT union changed: "
        f"expected {EXPECTED_UNION_COUNT}, got {len(accepted_by_id)}"
    )

    key_index: dict[str, set[str]] = {}
    for hullq_id, candidate in accepted_by_id.items():
        label = candidate.get("preferred_label")
        if isinstance(label, str) and label:
            key_index.setdefault(normalize(label), set()).add(hullq_id)
        for alias in candidate.get("aliases", []):
            if isinstance(alias, str) and alias:
                key_index.setdefault(normalize(alias), set()).add(hullq_id)

    return accepted_by_id, key_index


def classify(
    name: str,
    accepted_by_id: dict[str, dict[str, Any]],
    key_index: dict[str, set[str]],
) -> dict[str, Any]:
    matched_ids = key_index.get(normalize(name), set())

    if not matched_ids:
        return {
            "classification": "no_exact_overlap_signal",
            "matched_hullq_ids": [],
            "matched_preferred_labels": [],
        }

    matched_labels = sorted(
        {
            accepted_by_id[hid]["preferred_label"]
            for hid in matched_ids
            if accepted_by_id[hid].get("preferred_label")
        }
    )

    if len(matched_ids) == 1:
        return {
            "classification": "exact_overlap",
            "matched_hullq_ids": sorted(matched_ids),
            "matched_preferred_labels": matched_labels,
        }

    return {
        "classification": "unresolved_possible_overlap",
        "matched_hullq_ids": sorted(matched_ids),
        "matched_preferred_labels": matched_labels,
    }


def main() -> None:
    assert len(SOURCES) == EXPECTED_SOURCE_COUNT, (
        f"expected {EXPECTED_SOURCE_COUNT} sources, got {len(SOURCES)}"
    )

    accepted_by_id, key_index = build_accepted_universe()

    records: list[dict[str, Any]] = []
    per_source_summaries: list[dict[str, Any]] = []
    totals = {"exact_overlap": 0, "no_exact_overlap_signal": 0, "unresolved_possible_overlap": 0}

    for source in SOURCES:
        model_identities = source["model_identities"]
        assert len(model_identities) == EXPECTED_PER_SOURCE_COUNT, (
            f"{source['source_key']}: expected {EXPECTED_PER_SOURCE_COUNT} identities, "
            f"got {len(model_identities)}"
        )

        source_counts = {
            "exact_overlap": 0,
            "no_exact_overlap_signal": 0,
            "unresolved_possible_overlap": 0,
        }

        for identity in model_identities:
            name = identity["model_name"]
            result = classify(name, accepted_by_id, key_index)
            record = {
                "source_key": source["source_key"],
                "source_display_name": source["source_display_name"],
                "model_name": name,
                "source_surface": identity["source_surface"],
                "discriminating_context": identity["discriminating_context"],
                **result,
            }
            records.append(record)
            source_counts[result["classification"]] += 1
            totals[result["classification"]] += 1

        per_source_summaries.append(
            {
                "source_key": source["source_key"],
                "source_display_name": source["source_display_name"],
                "retained_count": len(model_identities),
                "exact_overlap_count": source_counts["exact_overlap"],
                "no_exact_overlap_signal_count": source_counts["no_exact_overlap_signal"],
                "unresolved_possible_overlap_count": source_counts["unresolved_possible_overlap"],
            }
        )

    total_retained = len(records)
    assert total_retained == EXPECTED_TOTAL_COUNT, (
        f"expected {EXPECTED_TOTAL_COUNT} total retained identities, got {total_retained}"
    )
    assert total_retained == sum(totals.values())

    result = {
        "pilot_version": "0020-identity-pilot-v1",
        "slice_id": "SLICE-0020",
        "generated_at": "2026-08-24T00:00:00Z",
        "method": (
            "Bounded, research-only identity-yield pilot. Exact/unambiguous-first overlap "
            "only: a match counts when a source-presented model name equals (case-insensitive "
            "with surrounding-whitespace trimming only -- internal whitespace is never "
            "collapsed or otherwise normalized) an accepted SLICE-0017/0018 AUTO_ADMIT "
            "candidate's preferred_label or an already-recorded alias. No fuzzy matching, "
            "manufacturer-prefix insertion/removal, token reordering, punctuation rewriting or "
            "generation collapsing was performed. A name whose exact-match signal resolves to "
            "more than one distinct accepted identity is unresolved_possible_overlap, never "
            "forced to a single match."
        ),
        "no_exact_overlap_signal_definition": (
            "no_exact_overlap_signal means only that no exact/unambiguous overlap signal was "
            "found against the accepted comparison universe under this slice's exact-match "
            "rules. It does NOT mean the model identity is globally novel, safe for canonical "
            "admission, proof that no matching HullQ BoatModel exists, or permission to mint or "
            "create a canonical identity."
        ),
        "accepted_universe": {
            "auto_admit_hullq_id_count": len(accepted_by_id),
            "expected_canonical_boatmodel_count": EXPECTED_UNION_COUNT,
            "manifest_paths": [
                str(path.relative_to(ROOT)).replace("\\", "/") for path in MANIFESTS
            ],
        },
        "pilot_bounds": {
            "source_count": len(SOURCES),
            "per_source_cap": 20,
            "per_source_retained": EXPECTED_PER_SOURCE_COUNT,
            "total_cap": 200,
            "total_retained": total_retained,
        },
        "totals": {
            "retained": total_retained,
            "exact_overlap": totals["exact_overlap"],
            "no_exact_overlap_signal": totals["no_exact_overlap_signal"],
            "unresolved_possible_overlap": totals["unresolved_possible_overlap"],
        },
        "per_source": per_source_summaries,
        "records": records,
    }

    OUT.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    print("SLICE-0020 bounded identity-pilot overlap computation complete")
    print(f"accepted_auto_admit_hullq_ids={len(accepted_by_id)}")
    print(f"sources={len(SOURCES)} total_retained={total_retained}")
    print(
        "exact_overlap={exact} no_exact_overlap_signal={new} "
        "unresolved_possible_overlap={possible}".format(
            exact=totals["exact_overlap"],
            new=totals["no_exact_overlap_signal"],
            possible=totals["unresolved_possible_overlap"],
        )
    )


if __name__ == "__main__":
    main()
