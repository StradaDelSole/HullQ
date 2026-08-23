#!/usr/bin/env python3
"""Mark the retained SLICE-0019 20-entity source-yield sample in registry.json."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parent
REGISTRY = ROOT / "registry.json"
SCHEMA = ROOT / "registry_schema.json"
STUDY = ROOT / "source_yield_study.json"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    registry = load_json(REGISTRY)
    schema = load_json(SCHEMA)
    study = load_json(STUDY)

    assert isinstance(registry, dict)
    assert isinstance(schema, dict)
    assert isinstance(study, dict)

    records = registry["records"]
    entities = study["entities"]
    assert isinstance(records, list)
    assert isinstance(entities, list)
    assert len(entities) == 20, f"source-yield sample must contain 20 entities, got {len(entities)}"

    sample_names = [entity["preferred_display_name"] for entity in entities]
    assert len(sample_names) == len(set(sample_names)), "duplicate source-yield sample name"

    by_name = {record["preferred_display_name"]: record for record in records}
    missing = sorted(set(sample_names) - set(by_name))
    assert not missing, f"source-yield sample names missing from registry: {missing}"

    for record in records:
        record["source_yield_sample"] = record["preferred_display_name"] in sample_names

    selected = [record for record in records if record["source_yield_sample"]]
    assert len(selected) == 20
    for record in selected:
        assert record["research_status"] == "verified", (
            f"sample record is not verified: {record['preferred_display_name']}"
        )
        assert {"manufacturer", "yard"} & set(record["entity_kind"]), (
            f"sample record is not a manufacturer/yard: {record['preferred_display_name']}"
        )

    jsonschema.validate(instance=registry, schema=schema)

    statuses = Counter(record["research_status"] for record in records)
    floor = sum(
        1
        for record in records
        if record["research_status"] == "verified"
        and {"manufacturer", "yard"} & set(record["entity_kind"])
    )

    assert len(records) == 136
    assert statuses == Counter({"verified": 129, "excluded": 6, "needs_review": 1})
    assert floor == 121

    REGISTRY.write_text(
        json.dumps(registry, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("registry.json source-yield sample finalized")
    print("sample_count=20")
    print(f"records={len(records)} verified={statuses['verified']} floor={floor}")
    print("schema_valid=true")


if __name__ == "__main__":
    main()
