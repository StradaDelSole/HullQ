"""Validate HullQ repository contracts and governance invariants."""

from __future__ import annotations

import re
from pathlib import Path

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"


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
    registry = ContractRegistry.from_directory(SPECS)
    req_count, acceptance_count = requirements_check()
    no_active_drafts_check()
    print(f"active schemas: {len(registry.schema_names)}")
    print(f"requirements: {req_count}")
    print(f"acceptance criteria: {acceptance_count}")
    print("repository governance validation: PASS")


if __name__ == "__main__":
    main()
