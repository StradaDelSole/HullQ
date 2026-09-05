"""Validate HullQ repository contracts and governance invariants."""

from __future__ import annotations

import re
from pathlib import Path

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
SLICES = ROOT / "docs" / "slices"
PROJECT_STATE = ROOT / "docs" / "PROJECT_STATE.md"

_PROJECT_STATE_ACCEPTED_RE = re.compile(
    r"<!--\s*PROJECT_STATE_ACCEPTED_SLICE:\s*(\d{4})\s*-->"
)
_ACCEPTANCE_CLOSURE_RE = re.compile(r"^SLICE-(\d{4})-.*acceptance-closure\.md$")


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


def latest_acceptance_closure_slice(slices_dir: Path = SLICES) -> int:
    """Return the highest slice number represented by an acceptance closure."""
    accepted: list[int] = []
    for path in slices_dir.glob("SLICE-*-acceptance-closure.md"):
        match = _ACCEPTANCE_CLOSURE_RE.fullmatch(path.name)
        if match is not None:
            accepted.append(int(match.group(1)))

    if not accepted:
        raise ValueError("No SLICE-XXXX-acceptance-closure.md files found")
    return max(accepted)


def declared_project_state_slice(project_state: Path = PROJECT_STATE) -> int:
    """Read the machine-readable latest-accepted marker from PROJECT_STATE."""
    text = project_state.read_text(encoding="utf-8")
    matches = _PROJECT_STATE_ACCEPTED_RE.findall(text)
    if len(matches) != 1:
        raise ValueError(
            "docs/PROJECT_STATE.md must contain exactly one "
            "PROJECT_STATE_ACCEPTED_SLICE marker"
        )
    return int(matches[0])


def project_state_freshness_check(
    *, slices_dir: Path = SLICES, project_state: Path = PROJECT_STATE
) -> tuple[int, int]:
    """Fail when PROJECT_STATE lags or leads the accepted slice closures.

    The acceptance-closure files are durable evidence of project-owner accepted
    slices. A closure that advances the highest accepted slice therefore must
    update PROJECT_STATE in the same change; otherwise repository validation
    fails and CI blocks the stale state from becoming canonical.
    """
    latest = latest_acceptance_closure_slice(slices_dir)
    declared = declared_project_state_slice(project_state)
    if declared != latest:
        raise ValueError(
            "PROJECT_STATE is stale/inconsistent: "
            f"marker declares SLICE-{declared:04d}, "
            f"latest acceptance closure is SLICE-{latest:04d}. "
            "Update docs/PROJECT_STATE.md in the acceptance-closure change."
        )
    return declared, latest


def main() -> None:
    registry = ContractRegistry.from_directory(SPECS)
    req_count, acceptance_count = requirements_check()
    no_active_drafts_check()
    state_slice, _ = project_state_freshness_check()
    print(f"active schemas: {len(registry.schema_names)}")
    print(f"requirements: {req_count}")
    print(f"acceptance criteria: {acceptance_count}")
    print(f"project state accepted through: SLICE-{state_slice:04d}")
    print("repository governance validation: PASS")


if __name__ == "__main__":
    main()
