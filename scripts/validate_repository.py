"""Validate HullQ repository contracts and governance invariants."""

from __future__ import annotations

import json
import re
from pathlib import Path

from jsonschema import Draft202012Validator
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"


def load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def active_schemas() -> dict[str, dict[str, object]]:
    schemas: dict[str, dict[str, object]] = {}
    for path in sorted(SPECS.glob("*_SCHEMA*.json")):
        schema = load_json(path)
        if not isinstance(schema, dict):
            raise TypeError(f"Schema must be an object: {path}")
        Draft202012Validator.check_schema(schema)
        schema_id = schema.get("$id")
        if isinstance(schema_id, str):
            schemas[schema_id] = schema
    return schemas


def schema_registry(schemas: dict[str, dict[str, object]]) -> Registry:
    registry = Registry()
    for uri, schema in schemas.items():
        registry = registry.with_resource(uri, Resource.from_contents(schema))
    return registry


def requirements_check() -> tuple[int, int]:
    text = (SPECS / "REQUIREMENTS.md").read_text(encoding="utf-8")
    ids = re.findall(r"^### (REQ-[A-Z]+-\d{3})\b", text, re.MULTILINE)
    acceptances = re.findall(r"^\*\*Acceptance:\*\*", text, re.MULTILINE)
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate requirement IDs detected")
    if len(ids) != len(acceptances):
        raise ValueError(
            f"Requirement/acceptance mismatch: {len(ids)} requirements, "
            f"{len(acceptances)} acceptance criteria"
        )
    return len(ids), len(acceptances)


def no_active_drafts_check() -> None:
    drafts = sorted(p.relative_to(ROOT) for p in SPECS.glob("*DRAFT*"))
    if drafts:
        raise ValueError(f"Draft artifacts are present in active specs/: {drafts}")


def main() -> None:
    schemas = active_schemas()
    _ = schema_registry(schemas)
    req_count, acceptance_count = requirements_check()
    no_active_drafts_check()
    print(f"active schemas: {len(schemas)}")
    print(f"requirements: {req_count}")
    print(f"acceptance criteria: {acceptance_count}")
    print("repository governance validation: PASS")


if __name__ == "__main__":
    main()
