"""Validate HullQ repository contracts and governance invariants."""

from __future__ import annotations

import re
from pathlib import Path

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
SLICES = ROOT / "docs" / "slices"
PROJECT_STATE = ROOT / "docs" / "PROJECT_STATE.md"
POST_0051_TRIGGER_GATES = ROOT / "docs" / "governance" / "POST_0051_TRIGGER_GATES.md"
PRODUCTION_READINESS_GATE = ROOT / "docs" / "governance" / "PRODUCTION_READINESS_GATE.md"

_PROJECT_STATE_ACCEPTED_RE = re.compile(r"<!--\s*PROJECT_STATE_ACCEPTED_SLICE:\s*(\d{4})\s*-->")
_PROJECT_STATE_QUEUE_RE = re.compile(r"<!--\s*PROJECT_STATE_QUEUE_SLICE:\s*(\d{4})\s*-->")
_ACCEPTANCE_CLOSURE_RE = re.compile(r"^SLICE-(\d{4})-.*acceptance-closure\.md$")
_SLICE_TYPE_RE = re.compile(r"(?m)^\*\*Type:\*\*\s*([A-Z_]+)\s*$")
_SLICE_STATUS_RE = re.compile(r"(?m)^\*\*Status:\*\*\s*([A-Z_]+)\s*$")
_HANDOFF_STATUS_RE = re.compile(
    r"(?m)^\*\*Status set by this handoff:\*\*\s*`(REVIEW|BLOCKED)`(?:\s|$)"
)
_RECONCILIATION_SECTION_RE = re.compile(
    r"(?ms)^## Decision / implementation reconciliation[ \t]*\n(.*?)(?=^##[ \t]|\Z)"
)
_TRIGGER_GATES_SECTION_RE = re.compile(r"(?ms)^## Trigger gates[ \t]*\n(.*?)(?=^##[ \t]|\Z)")
_ARCHITECTURE_RECONCILIATION_RE = re.compile(
    r"<!--\s*POST_0051_ARCHITECTURE_RECONCILIATION:\s*(PASS|FAIL)\s*-->"
)
_TECHNICAL_SEARCH_CRITERIA_COUNT_RE = re.compile(
    r"<!--\s*TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT:\s*(\d+)\s*-->"
)
_WORKFLOW_REASSESSMENT_DUE_RE = re.compile(
    r"<!--\s*WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE:\s*(\d{4})\s*-->"
)
_WORKFLOW_REASSESSMENT_STATUS_RE = re.compile(
    r"<!--\s*WORKFLOW_REASSESSMENT_STATUS:\s*(NOT_DUE|DUE|PASS)\s*-->"
)
_PRODUCTION_READINESS_STATUS_RE = re.compile(
    r"<!--\s*PRODUCTION_READINESS_GATE_STATUS:\s*(NOT_TRIGGERED|IN_PROGRESS|PASS)\s*-->"
)
_EXTERNAL_BROKER_PRODUCTION_DATA_STATUS_RE = re.compile(
    r"<!--\s*EXTERNAL_BROKER_PRODUCTION_DATA_STATUS:\s*(NOT_PRESENT|ACTIVE)\s*-->"
)
_PRODUCTION_PILOT_STATUS_RE = re.compile(
    r"<!--\s*PRODUCTION_PILOT_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->"
)
_PUBLIC_PRODUCTION_LAUNCH_STATUS_RE = re.compile(
    r"<!--\s*PUBLIC_PRODUCTION_LAUNCH_STATUS:\s*(NOT_STARTED|ACTIVE)\s*-->"
)
_ALLOWED_SLICE_TYPES = frozenset({"BOOTSTRAP", "DESIGN_RESEARCH", "IMPLEMENTATION", "VALIDATION"})
_POST_0038_PRODUCT_CHECKS = (
    "ONE-CAPABILITY CHECK",
    "VISIBLE-RESULT CHECK",
    "PRODUCT EXECUTION PLAN ALIGNMENT",
)
_POST_0050_RECONCILIATION_CHECK = "REPOSITORY RECONCILIATION CHECK"
_POST_0051_TRIGGER_GATES_CHECK = "TRIGGER GATES CHECK"
_RECONCILIATION_EVIDENCE_LABELS = (
    "Accepted records checked",
    "Production implementation checked",
    "Already implemented / not re-decided",
    "Exact remaining gap",
    "Accepted-but-unimplemented obligations",
    "Material classifications",
)
_RECONCILIATION_CLASSIFICATIONS = (
    "DECIDED_AND_IMPLEMENTED",
    "DECIDED_NOT_YET_IMPLEMENTED",
    "EXPLICITLY_DEFERRED",
    "GENUINELY_OPEN",
    "CONFLICT_OR_REGRESSION",
)
_RECONCILIATION_PLACEHOLDER_VALUES = frozenset({"TODO", "TBD", "PLACEHOLDER"})
_TRIGGER_EVIDENCE_LABELS = (
    "Production readiness gate",
    "Adds technical native Search criterion",
    "Technical Search criterion ordinal",
    "Second-criterion bridge comparison",
    "Third-copy abstraction guard",
    "Workflow reassessment status",
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
    """Fail when PROJECT_STATE lags or leads the accepted slice closures."""
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


def _single_marker(*, text: str, pattern: re.Pattern[str], label: str) -> str:
    matches = pattern.findall(text)
    if len(matches) != 1:
        raise ValueError(f"{label} must appear exactly once as a machine-readable marker")
    return matches[0]


def trigger_gate_state_check(
    *,
    project_state: Path = PROJECT_STATE,
    trigger_gates: Path = POST_0051_TRIGGER_GATES,
    production_gate: Path = PRODUCTION_READINESS_GATE,
) -> tuple[str, int, str, str]:
    """Validate global post-0051 trigger state and production blocking rules."""
    if not trigger_gates.is_file():
        raise ValueError("Missing docs/governance/POST_0051_TRIGGER_GATES.md")
    if not production_gate.is_file():
        raise ValueError("Missing docs/governance/PRODUCTION_READINESS_GATE.md")

    trigger_text = trigger_gates.read_text(encoding="utf-8")
    production_text = production_gate.read_text(encoding="utf-8")
    accepted = declared_project_state_slice(project_state)

    architecture = _single_marker(
        text=trigger_text,
        pattern=_ARCHITECTURE_RECONCILIATION_RE,
        label="POST_0051_ARCHITECTURE_RECONCILIATION",
    )
    criteria_count_text = _single_marker(
        text=trigger_text,
        pattern=_TECHNICAL_SEARCH_CRITERIA_COUNT_RE,
        label="TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT",
    )
    criteria_count = int(criteria_count_text)
    if criteria_count < 1:
        raise ValueError("TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT must be at least 1 after SLICE-0051")

    due_after_text = _single_marker(
        text=trigger_text,
        pattern=_WORKFLOW_REASSESSMENT_DUE_RE,
        label="WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE",
    )
    due_after = int(due_after_text)
    if due_after != 56:
        raise ValueError(
            "WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE must remain 0056 unless an accepted "
            "governance change explicitly supersedes the five-slice trigger"
        )
    workflow = _single_marker(
        text=trigger_text,
        pattern=_WORKFLOW_REASSESSMENT_STATUS_RE,
        label="WORKFLOW_REASSESSMENT_STATUS",
    )

    production = _single_marker(
        text=production_text,
        pattern=_PRODUCTION_READINESS_STATUS_RE,
        label="PRODUCTION_READINESS_GATE_STATUS",
    )
    broker_data = _single_marker(
        text=production_text,
        pattern=_EXTERNAL_BROKER_PRODUCTION_DATA_STATUS_RE,
        label="EXTERNAL_BROKER_PRODUCTION_DATA_STATUS",
    )
    pilot = _single_marker(
        text=production_text,
        pattern=_PRODUCTION_PILOT_STATUS_RE,
        label="PRODUCTION_PILOT_STATUS",
    )
    launch = _single_marker(
        text=production_text,
        pattern=_PUBLIC_PRODUCTION_LAUNCH_STATUS_RE,
        label="PUBLIC_PRODUCTION_LAUNCH_STATUS",
    )

    if architecture != "PASS":
        raise ValueError(
            "Post-0051 architecture/current-state reconciliation is not PASS; "
            "SLICE-0052+ capability readiness is blocked"
        )

    if accepted >= due_after and workflow == "NOT_DUE":
        raise ValueError(
            f"Workflow reassessment became due after accepted SLICE-{due_after:04d}; "
            "WORKFLOW_REASSESSMENT_STATUS must be DUE or PASS"
        )

    production_data_active = broker_data == "ACTIVE" or pilot == "ACTIVE" or launch == "ACTIVE"
    if production_data_active and production != "PASS":
        raise ValueError(
            "External broker production data/pilot/public launch is ACTIVE but "
            "PRODUCTION_READINESS_GATE_STATUS is not PASS"
        )

    external_pilot_active = pilot == "ACTIVE" or launch == "ACTIVE"
    if external_pilot_active and workflow != "PASS":
        raise ValueError(
            "Production pilot/public launch is ACTIVE but the mandatory pre-pilot workflow "
            "reassessment is not PASS"
        )

    if production == "NOT_TRIGGERED" and production_data_active:
        raise ValueError(
            "Production readiness cannot remain NOT_TRIGGERED after production data starts"
        )

    return architecture, criteria_count, workflow, production


def _is_reconciliation_placeholder(value: str) -> bool:
    normalized = value.strip()
    return normalized.upper() in _RECONCILIATION_PLACEHOLDER_VALUES or (
        normalized.startswith("<") and normalized.endswith(">")
    )


def _reconciliation_section(*, queue: int, path: Path, text: str) -> str:
    match = _RECONCILIATION_SECTION_RE.search(text)
    if match is None:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must contain "
            "'## Decision / implementation reconciliation'"
        )
    return match.group(1)


def _validate_reconciliation_evidence(*, queue: int, path: Path, section: str) -> None:
    for label in _RECONCILIATION_EVIDENCE_LABELS:
        pattern = re.compile(rf"(?m)^\*\*{re.escape(label)}:\*\*[ \t]*(\S[^\r\n]*)[ \t]*$")
        match = pattern.search(section)
        if match is None:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} must contain a non-empty "
                f"'**{label}:** <evidence>' reconciliation line"
            )
        if _is_reconciliation_placeholder(match.group(1)):
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} has placeholder rather than "
                f"repository-backed evidence after '**{label}:**'"
            )

    classifications_pattern = re.compile(
        r"(?m)^\*\*Material classifications:\*\*[ \t]*[^\r\n]*\b(?:"
        + "|".join(re.escape(value) for value in _RECONCILIATION_CLASSIFICATIONS)
        + r")\b[^\r\n]*$"
    )
    if classifications_pattern.search(section) is None:
        allowed = ", ".join(_RECONCILIATION_CLASSIFICATIONS)
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must name at least one accepted "
            f"reconciliation classification after '**Material classifications:**'; allowed: {allowed}"
        )


def _trigger_gates_section(*, queue: int, path: Path, text: str) -> str:
    match = _TRIGGER_GATES_SECTION_RE.search(text)
    if match is None:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must contain '## Trigger gates'"
        )
    return match.group(1)


def _trigger_evidence_value(*, queue: int, path: Path, section: str, label: str) -> str:
    pattern = re.compile(rf"(?m)^\*\*{re.escape(label)}:\*\*[ \t]*(\S[^\r\n]*)[ \t]*$")
    match = pattern.search(section)
    if match is None:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must contain a non-empty "
            f"'**{label}:** <value>' trigger-gate line"
        )
    value = match.group(1).strip()
    if _is_reconciliation_placeholder(value):
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} has placeholder rather than "
            f"trigger-gate evidence after '**{label}:**'"
        )
    return value


def _validate_trigger_gate_evidence(
    *,
    queue: int,
    path: Path,
    section: str,
    criteria_count: int,
    workflow_status: str,
    production_status: str,
) -> None:
    values = {
        label: _trigger_evidence_value(queue=queue, path=path, section=section, label=label)
        for label in _TRIGGER_EVIDENCE_LABELS
    }

    production_value = values["Production readiness gate"]
    if production_value not in {"NOT_TRIGGERED", "IN_PROGRESS", "PASS"}:
        raise ValueError(
            f"SLICE-{queue:04d} has invalid Production readiness gate value {production_value!r}"
        )
    if production_value != production_status:
        raise ValueError(
            f"SLICE-{queue:04d} production readiness evidence {production_value!r} does not "
            f"match canonical status {production_status!r}"
        )

    adds = values["Adds technical native Search criterion"]
    ordinal = values["Technical Search criterion ordinal"]
    second = values["Second-criterion bridge comparison"]
    third = values["Third-copy abstraction guard"]
    readiness_workflow = values["Workflow reassessment status"]

    if readiness_workflow != workflow_status:
        raise ValueError(
            f"SLICE-{queue:04d} workflow reassessment evidence {readiness_workflow!r} does not "
            f"match canonical status {workflow_status!r}"
        )
    if queue >= 57 and workflow_status == "DUE":
        raise ValueError(
            f"SLICE-{queue:04d} cannot become startable while workflow reassessment is DUE"
        )

    if adds == "NO":
        if (
            ordinal != "NOT_APPLICABLE"
            or second != "NOT_APPLICABLE"
            or third != "NOT_APPLICABLE"
        ):
            raise ValueError(
                f"SLICE-{queue:04d} does not add a technical native Search criterion; "
                "ordinal/comparison/third-copy guard must all be NOT_APPLICABLE"
            )
        return

    if adds != "YES":
        raise ValueError(
            f"SLICE-{queue:04d} 'Adds technical native Search criterion' must be YES or NO"
        )

    if not ordinal.isdigit():
        raise ValueError(
            f"SLICE-{queue:04d} technical Search criterion ordinal must be an integer "
            "when addition is YES"
        )
    ordinal_number = int(ordinal)
    expected = criteria_count + 1
    if ordinal_number != expected:
        raise ValueError(
            f"SLICE-{queue:04d} criterion ordinal {ordinal_number} does not follow accepted "
            f"criterion count {criteria_count}; expected {expected}"
        )

    if ordinal_number >= 2 and second != "PASS":
        raise ValueError(
            f"SLICE-{queue:04d} criterion #{ordinal_number} requires "
            "'**Second-criterion bridge comparison:** PASS'"
        )

    if ordinal_number >= 3:
        if third != "PASS":
            raise ValueError(
                f"SLICE-{queue:04d} criterion #{ordinal_number} requires "
                "'**Third-copy abstraction guard:** PASS'"
            )
    elif third != "NOT_APPLICABLE":
        raise ValueError(
            f"SLICE-{queue:04d} criterion #{ordinal_number} must use "
            "'**Third-copy abstraction guard:** NOT_APPLICABLE'"
        )


def queue_slice_startability_check(
    *, slices_dir: Path = SLICES, project_state: Path = PROJECT_STATE
) -> tuple[int, str | None]:
    """Validate the queued slice across readiness and implementation handoff."""
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
            pattern = re.compile(rf"(?m)^\*\*{re.escape(check)}:\*\*[ \t]*PASS[ \t]*$")
            if pattern.search(text) is None:
                raise ValueError(
                    f"SLICE-{queue:04d} queue document {path.name} must contain "
                    f"'**{check}:** PASS'"
                )

    if queue >= 51:
        reconciliation_pattern = re.compile(
            rf"(?m)^\*\*{re.escape(_POST_0050_RECONCILIATION_CHECK)}:\*\*[ \t]*PASS[ \t]*$"
        )
        if reconciliation_pattern.search(text) is None:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} must contain "
                f"'**{_POST_0050_RECONCILIATION_CHECK}:** PASS'"
            )
        section = _reconciliation_section(queue=queue, path=path, text=text)
        _validate_reconciliation_evidence(queue=queue, path=path, section=section)

    if queue >= 52:
        architecture, criteria_count, workflow_status, production_status = trigger_gate_state_check(
            project_state=project_state
        )
        if architecture != "PASS":
            raise ValueError(
                f"SLICE-{queue:04d} cannot become startable before architecture "
                "reconciliation PASS"
            )
        trigger_pattern = re.compile(
            rf"(?m)^\*\*{re.escape(_POST_0051_TRIGGER_GATES_CHECK)}:\*\*[ \t]*PASS[ \t]*$"
        )
        if trigger_pattern.search(text) is None:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} must contain "
                f"'**{_POST_0051_TRIGGER_GATES_CHECK}:** PASS'"
            )
        trigger_section = _trigger_gates_section(queue=queue, path=path, text=text)
        _validate_trigger_gate_evidence(
            queue=queue,
            path=path,
            section=trigger_section,
            criteria_count=criteria_count,
            workflow_status=workflow_status,
            production_status=production_status,
        )

    return queue, path.name


def main() -> None:
    registry = ContractRegistry.from_directory(SPECS)
    req_count, acceptance_count = requirements_check()
    no_active_drafts_check()
    state_slice, _ = project_state_freshness_check()
    architecture, criteria_count, workflow_status, production_status = trigger_gate_state_check()
    queue_slice, queue_file = queue_slice_startability_check()
    print(f"active schemas: {len(registry.schema_names)}")
    print(f"requirements: {req_count}")
    print(f"acceptance criteria: {acceptance_count}")
    print(f"project state accepted through: SLICE-{state_slice:04d}")
    print(f"post-0051 architecture reconciliation: {architecture}")
    print(f"accepted technical native Search criteria: {criteria_count}")
    print(f"workflow reassessment: {workflow_status}")
    print(f"production readiness gate: {production_status}")
    if queue_file is None:
        print(f"queue readiness document: not yet present for SLICE-{queue_slice:04d}")
    else:
        print(f"queue contract valid: SLICE-{queue_slice:04d} ({queue_file})")
    print("repository governance validation: PASS")


if __name__ == "__main__":
    main()
