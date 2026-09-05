"""Validate HullQ repository contracts and governance invariants."""

from __future__ import annotations

import re
from pathlib import Path

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
SLICES = ROOT / "docs" / "slices"
PROJECT_STATE = ROOT / "docs" / "PROJECT_STATE.md"

_PROJECT_STATE_ACCEPTED_RE = re.compile(r"<!--\s*PROJECT_STATE_ACCEPTED_SLICE:\s*(\d{4})\s*-->")
_PROJECT_STATE_QUEUE_RE = re.compile(r"<!--\s*PROJECT_STATE_QUEUE_SLICE:\s*(\d{4})\s*-->")
_ACCEPTANCE_CLOSURE_RE = re.compile(r"^SLICE-(\d{4})-.*acceptance-closure\.md$")
_SLICE_TYPE_RE = re.compile(r"(?m)^\*\*Type:\*\*\s*([A-Z_]+)\s*$")
_SLICE_STATUS_RE = re.compile(r"(?m)^\*\*Status:\*\*\s*([A-Z_]+)\s*$")
_HANDOFF_STATUS_RE = re.compile(
    r"(?m)^\*\*Status set by this handoff:\*\*\s*`(REVIEW|BLOCKED)`(?:\s|$)"
)
_ALLOWED_SLICE_TYPES = frozenset({"BOOTSTRAP", "DESIGN_RESEARCH", "IMPLEMENTATION", "VALIDATION"})
_POST_0038_PRODUCT_CHECKS = (
    "ONE-CAPABILITY CHECK",
    "VISIBLE-RESULT CHECK",
    "PRODUCT EXECUTION PLAN ALIGNMENT",
)


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
            "docs/PROJECT_STATE.md must contain exactly one PROJECT_STATE_ACCEPTED_SLICE marker"
        )
    return int(matches[0])


def declared_project_queue_slice(project_state: Path = PROJECT_STATE) -> int:
    """Read the machine-readable current-queue marker from PROJECT_STATE."""
    text = project_state.read_text(encoding="utf-8")
    matches = _PROJECT_STATE_QUEUE_RE.findall(text)
    if len(matches) != 1:
        raise ValueError(
            "docs/PROJECT_STATE.md must contain exactly one PROJECT_STATE_QUEUE_SLICE marker"
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


def queue_slice_startability_check(
    *, slices_dir: Path = SLICES, project_state: Path = PROJECT_STATE
) -> tuple[int, str | None]:
    """Validate the queued slice across readiness and implementation handoff.

    Before execution, a queued primary document must be exactly START_SLICE-
    compatible: canonical Type, Status READY, and the post-0038 product checks.

    Once implementation has actually reached an agent handoff, that same queued
    document may legitimately move to REVIEW or BLOCKED before acceptance closure
    advances PROJECT_STATE to the next slice. To distinguish that execution state
    from a malformed readiness artifact, REVIEW/BLOCKED is allowed only when the
    document contains the matching explicit handoff marker line:

        **Status set by this handoff:** `REVIEW`
        **Status set by this handoff:** `BLOCKED`

    Transitional readiness values such as READY_FOR_REVIEW remain invalid.
    """
    queue = declared_project_queue_slice(project_state)
    candidates = sorted(
        path
        for path in slices_dir.glob(f"SLICE-{queue:04d}-*.md")
        if not path.name.endswith("-acceptance-closure.md")
    )
    if not candidates:
        return queue, None

    primary: list[tuple[Path, str, re.Match[str]]] = []
    for path in candidates:
        text = path.read_text(encoding="utf-8")
        type_match = _SLICE_TYPE_RE.search(text)
        if type_match is not None:
            primary.append((path, text, type_match))

    if len(primary) != 1:
        names = ", ".join(path.name for path in candidates)
        raise ValueError(
            f"SLICE-{queue:04d} queue is not START_SLICE-compatible: expected exactly one "
            "primary non-closure document with a '**Type:** <TOKEN>' header; "
            f"found {len(primary)}. Eligible files: {names}"
        )

    path, text, type_match = primary[0]
    slice_type = type_match.group(1)
    if slice_type not in _ALLOWED_SLICE_TYPES:
        allowed = ", ".join(sorted(_ALLOWED_SLICE_TYPES))
        raise ValueError(
            f"SLICE-{queue:04d} has unsupported Type {slice_type!r}; allowed values: {allowed}"
        )

    status_match = _SLICE_STATUS_RE.search(text)
    if status_match is None:
        raise ValueError(f"SLICE-{queue:04d} primary document must contain a **Status:** header")
    status = status_match.group(1)
    if status == "READY":
        pass
    elif status in {"REVIEW", "BLOCKED"}:
        handoff_match = _HANDOFF_STATUS_RE.search(text)
        if handoff_match is None or handoff_match.group(1) != status:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} is {status!r} but lacks the "
                f"matching implementation handoff marker '**Status set by this handoff:** `{status}`'"
            )
    else:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} is {status!r}; expected 'READY' "
            "before execution or an explicitly marked implementation handoff state REVIEW/BLOCKED"
        )

    if queue >= 39:
        for check in _POST_0038_PRODUCT_CHECKS:
            pattern = re.compile(rf"(?m)^\*\*{re.escape(check)}:\*\*\s*PASS\s*$")
            if pattern.search(text) is None:
                raise ValueError(
                    f"SLICE-{queue:04d} queue document {path.name} must contain '**{check}:** PASS'"
                )

    return queue, path.name


def main() -> None:
    registry = ContractRegistry.from_directory(SPECS)
    req_count, acceptance_count = requirements_check()
    no_active_drafts_check()
    state_slice, _ = project_state_freshness_check()
    queue_slice, queue_file = queue_slice_startability_check()
    print(f"active schemas: {len(registry.schema_names)}")
    print(f"requirements: {req_count}")
    print(f"acceptance criteria: {acceptance_count}")
    print(f"project state accepted through: SLICE-{state_slice:04d}")
    if queue_file is None:
        print(f"queue readiness document: not yet present for SLICE-{queue_slice:04d}")
    else:
        print(f"queue contract valid: SLICE-{queue_slice:04d} ({queue_file})")
    print("repository governance validation: PASS")


if __name__ == "__main__":
    main()
