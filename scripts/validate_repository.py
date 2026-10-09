"""Validate HullQ repository contracts and governance invariants."""

from __future__ import annotations

import json
import re
from pathlib import Path

from hullq.contracts import ContractRegistry

ROOT = Path(__file__).resolve().parents[1]
SPECS = ROOT / "specs"
SLICES = ROOT / "docs" / "slices"
PROJECT_STATE = ROOT / "docs" / "PROJECT_STATE.md"
POST_0051_TRIGGER_GATES = ROOT / "docs" / "governance" / "POST_0051_TRIGGER_GATES.md"
PRODUCTION_READINESS_GATE = ROOT / "docs" / "governance" / "PRODUCTION_READINESS_GATE.md"
CLAUDE_SETTINGS = ROOT / ".claude" / "settings.json"
CLAUDE_COMMAND_GUARD = ROOT / "scripts" / "workflow" / "claude_command_guard.py"
CLAUDE_DIAG = ROOT / "scripts" / "workflow" / "claude_diag.py"

_PROJECT_STATE_ACCEPTED_RE = re.compile(r"<!--\s*PROJECT_STATE_ACCEPTED_SLICE:\s*(\d{4})\s*-->")
_PROJECT_STATE_QUEUE_RE = re.compile(r"<!--\s*PROJECT_STATE_QUEUE_SLICE:\s*(\d{4})\s*-->")
_PRODUCTION_LAUNCH_PACK_PHASE_RE = re.compile(
    r"<!--\s*PRODUCTION_LAUNCH_PACK_PHASE:\s*(NOT_STARTED|[1-7])\s*-->"
)
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
_MECHANICAL_INVARIANTS_SECTION_RE = re.compile(
    r"(?ms)^## Mechanical invariants / failure modes[ \t]*\n(.*?)(?=^##[ \t]|\Z)"
)
_PRODUCTION_PHASE_TRANSITION_SECTION_RE = re.compile(
    r"(?ms)^## Production phase transition check[ \t]*\n(.*?)(?=^##[ \t]|\Z)"
)
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
_POST_0079_MECHANICAL_INVARIANTS_CHECK = "MECHANICAL INVARIANTS / FAILURE MODES CHECK"
_POST_0079_PRODUCTION_LAUNCH_PACK_CHECK = "PRODUCTION LAUNCH PACK CHECK"
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
_MECHANICAL_EVIDENCE_LABELS = (
    "Risk classification",
    "Why this classification",
    "Must-never-change invariant",
    "Durable source of truth / loss boundary",
    "Retry / replay / partial-failure behavior",
    "Absence-vs-error / fail-closed behavior",
    "Executable adversarial proof",
    "Slice sizing assessment",
)
_MECHANICAL_BARE_PLACEHOLDERS = frozenset(
    {"TODO", "TBD", "PLACEHOLDER", "N/A", "NA", "NOT_APPLICABLE", "NOT APPLICABLE"}
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


def claude_approval_autonomy_check(
    *,
    settings_path: Path = CLAUDE_SETTINGS,
    guard_path: Path = CLAUDE_COMMAND_GUARD,
    diag_path: Path = CLAUDE_DIAG,
) -> None:
    """Require the shared mechanical guard that prevents routine approval stalls."""

    if not settings_path.is_file():
        raise ValueError("Missing project-level .claude/settings.json")
    if not guard_path.is_file():
        raise ValueError("Missing scripts/workflow/claude_command_guard.py")
    if not diag_path.is_file():
        raise ValueError("Missing scripts/workflow/claude_diag.py")

    try:
        settings = json.loads(settings_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(".claude/settings.json is not valid JSON") from exc

    permissions = settings.get("permissions")
    if not isinstance(permissions, dict):
        raise ValueError(".claude/settings.json must define a permissions object")
    if permissions.get("defaultMode") != "acceptEdits":
        raise ValueError("Claude shared defaultMode must remain acceptEdits")
    if permissions.get("disableBypassPermissionsMode") != "disable":
        raise ValueError("Claude bypass-permissions mode must remain disabled")

    allow = permissions.get("allow")
    if not isinstance(allow, list):
        raise ValueError("Claude shared permissions.allow must be a list")
    required_allow = {
        "Read",
        "Glob",
        "Grep",
        "Bash(uv *)",
        "PowerShell(uv *)",
        "Bash(npm ci *)",
        "PowerShell(npm ci *)",
    }
    missing_allow = sorted(required_allow.difference(allow))
    if missing_allow:
        raise ValueError(
            "Claude approval-autonomy allow rules are incomplete: " + ", ".join(missing_allow)
        )

    hooks = settings.get("hooks")
    if not isinstance(hooks, dict):
        raise ValueError(".claude/settings.json must define shared Claude hooks")

    expected_args = [
        "run",
        "--no-project",
        "--python",
        "3.14",
        "python",
        "${CLAUDE_PROJECT_DIR}/scripts/workflow/claude_command_guard.py",
    ]
    for event in ("PreToolUse", "PermissionRequest"):
        groups = hooks.get(event)
        if not isinstance(groups, list):
            raise ValueError(f"Claude shared hooks must define {event}")
        matching_group = next(
            (
                group
                for group in groups
                if isinstance(group, dict) and group.get("matcher") == "Bash|PowerShell"
            ),
            None,
        )
        if matching_group is None:
            raise ValueError(f"Claude {event} must match Bash|PowerShell")

        handlers = matching_group.get("hooks")
        if not isinstance(handlers, list):
            raise ValueError(f"Claude {event} Bash|PowerShell group must define handlers")
        has_guard = any(
            isinstance(handler, dict)
            and handler.get("type") == "command"
            and handler.get("command") == "uv"
            and handler.get("args") == expected_args
            for handler in handlers
        )
        if not has_guard:
            raise ValueError(
                f"Claude {event} must execute the shared claude_command_guard.py via uv"
            )


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


def declared_production_launch_pack_phase(project_state: Path = PROJECT_STATE) -> str:
    """Read the canonical completed production launch-pack phase."""
    text = project_state.read_text(encoding="utf-8")
    matches = _PRODUCTION_LAUNCH_PACK_PHASE_RE.findall(text)
    if len(matches) != 1:
        raise ValueError(
            "docs/PROJECT_STATE.md must contain exactly one PRODUCTION_LAUNCH_PACK_PHASE marker"
        )
    return matches[0]


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
        raise ValueError(
            "TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT must be at least 1 after SLICE-0051"
        )

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
        if ordinal != "NOT_APPLICABLE" or second != "NOT_APPLICABLE" or third != "NOT_APPLICABLE":
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


def _mechanical_invariants_section(*, queue: int, path: Path, text: str) -> str:
    match = _MECHANICAL_INVARIANTS_SECTION_RE.search(text)
    if match is None:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must contain "
            "'## Mechanical invariants / failure modes'"
        )
    return match.group(1)


def _mechanical_evidence_value(*, queue: int, path: Path, section: str, label: str) -> str:
    pattern = re.compile(rf"(?m)^\*\*{re.escape(label)}:\*\*[ \t]*(\S[^\r\n]*)[ \t]*$")
    match = pattern.search(section)
    if match is None:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must contain a non-empty "
            f"'**{label}:** <evidence>' line in its mechanical-invariants section"
        )
    value = match.group(1).strip()
    if _is_reconciliation_placeholder(value):
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} has placeholder rather than "
            f"mechanical-invariant evidence after '**{label}:**'"
        )
    return value


def _validate_mechanical_invariant_evidence(
    *, queue: int, path: Path, section: str, check_value: str
) -> None:
    values = {
        label: _mechanical_evidence_value(queue=queue, path=path, section=section, label=label)
        for label in _MECHANICAL_EVIDENCE_LABELS
    }

    risk = values["Risk classification"]
    if risk not in {"HIGH_RISK", "ORDINARY"}:
        raise ValueError(
            f"SLICE-{queue:04d} Risk classification must be HIGH_RISK or ORDINARY, got {risk!r}"
        )

    sizing = values["Slice sizing assessment"]
    if sizing not in {"COHERENT", "SPLIT_REQUIRED"}:
        raise ValueError(
            f"SLICE-{queue:04d} Slice sizing assessment must be COHERENT or SPLIT_REQUIRED, "
            f"got {sizing!r}"
        )
    if sizing == "SPLIT_REQUIRED":
        raise ValueError(
            f"SLICE-{queue:04d} cannot become startable while its mechanical readiness "
            "assessment says SPLIT_REQUIRED"
        )

    if check_value not in {"PASS", "NOT_APPLICABLE"}:
        raise ValueError(
            f"SLICE-{queue:04d} {_POST_0079_MECHANICAL_INVARIANTS_CHECK} must be PASS or "
            f"NOT_APPLICABLE, got {check_value!r}"
        )
    if risk == "HIGH_RISK" and check_value != "PASS":
        raise ValueError(
            f"SLICE-{queue:04d} is HIGH_RISK and therefore requires "
            f"'**{_POST_0079_MECHANICAL_INVARIANTS_CHECK}:** PASS'"
        )

    if risk == "HIGH_RISK":
        for label in (
            "Why this classification",
            "Must-never-change invariant",
            "Durable source of truth / loss boundary",
            "Retry / replay / partial-failure behavior",
            "Absence-vs-error / fail-closed behavior",
            "Executable adversarial proof",
        ):
            if values[label].upper() in _MECHANICAL_BARE_PLACEHOLDERS:
                raise ValueError(
                    f"SLICE-{queue:04d} HIGH_RISK mechanical evidence after '**{label}:**' "
                    "must be concrete, not a bare placeholder/not-applicable value"
                )


def _production_phase_transition_section(*, queue: int, path: Path, text: str) -> str:
    match = _PRODUCTION_PHASE_TRANSITION_SECTION_RE.search(text)
    if match is None:
        raise ValueError(
            f"SLICE-{queue:04d} queue document {path.name} must contain "
            "'## Production phase transition check'"
        )
    return match.group(1)


def _validate_production_phase_transition(
    *, queue: int, path: Path, section: str, check_value: str, canonical_phase: str
) -> None:
    def value(label: str) -> str:
        pattern = re.compile(rf"(?m)^\*\*{re.escape(label)}:\*\*[ \t]*(\S[^\r\n]*)[ \t]*$")
        match = pattern.search(section)
        if match is None:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} must contain a non-empty "
                f"'**{label}:** <value>' line in its production phase transition section"
            )
        return match.group(1).strip()

    before = value("Launch-pack phase before this slice")
    after = value("Launch-pack phase after this slice")
    allowed_before = {"NOT_APPLICABLE", "NOT_STARTED", "1", "2", "3", "4", "5", "6", "7"}
    allowed_after = {"NOT_APPLICABLE", "1", "2", "3", "4", "5", "6", "7"}
    if before not in allowed_before:
        raise ValueError(f"SLICE-{queue:04d} has invalid launch-pack phase before value {before!r}")
    if after not in allowed_after:
        raise ValueError(f"SLICE-{queue:04d} has invalid launch-pack phase after value {after!r}")

    if before == "NOT_APPLICABLE" or after == "NOT_APPLICABLE":
        if before != "NOT_APPLICABLE" or after != "NOT_APPLICABLE":
            raise ValueError(
                f"SLICE-{queue:04d} launch-pack phases must both be NOT_APPLICABLE when "
                "the production launch pack does not apply"
            )
        if check_value != "NOT_APPLICABLE":
            raise ValueError(
                f"SLICE-{queue:04d} non-production slice must use "
                f"'**{_POST_0079_PRODUCTION_LAUNCH_PACK_CHECK}:** NOT_APPLICABLE'"
            )
        return

    if check_value != "PASS":
        raise ValueError(
            f"SLICE-{queue:04d} production-phase work requires "
            f"'**{_POST_0079_PRODUCTION_LAUNCH_PACK_CHECK}:** PASS'"
        )

    if before != canonical_phase:
        raise ValueError(
            f"SLICE-{queue:04d} launch-pack phase before {before!r} does not match canonical "
            f"PRODUCTION_LAUNCH_PACK_PHASE {canonical_phase!r} in docs/PROJECT_STATE.md"
        )

    before_number = 0 if before == "NOT_STARTED" else int(before)
    after_number = int(after)
    if after_number < before_number:
        raise ValueError(
            f"SLICE-{queue:04d} production launch phase cannot move backwards: {before} -> {after}"
        )
    if after_number > before_number + 1:
        raise ValueError(
            f"SLICE-{queue:04d} production launch phase cannot skip stages: "
            f"{before} -> {after}; follow docs/operations/PRODUCTION_LAUNCH_PACK.md"
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
                    f"SLICE-{queue:04d} queue document {path.name} must contain '**{check}:** PASS'"
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
                f"SLICE-{queue:04d} cannot become startable before architecture reconciliation PASS"
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

    if queue >= 80:
        launch_pattern = re.compile(
            rf"(?m)^\*\*{re.escape(_POST_0079_PRODUCTION_LAUNCH_PACK_CHECK)}:\*\*"
            r"[ \t]*(PASS|NOT_APPLICABLE)[ \t]*$"
        )
        launch_match = launch_pattern.search(text)
        if launch_match is None:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} must contain "
                f"'**{_POST_0079_PRODUCTION_LAUNCH_PACK_CHECK}:** PASS | NOT_APPLICABLE'"
            )
        transition_section = _production_phase_transition_section(queue=queue, path=path, text=text)
        _validate_production_phase_transition(
            queue=queue,
            path=path,
            section=transition_section,
            check_value=launch_match.group(1),
            canonical_phase=declared_production_launch_pack_phase(project_state),
        )
    if queue >= 80:
        mechanical_pattern = re.compile(
            rf"(?m)^\*\*{re.escape(_POST_0079_MECHANICAL_INVARIANTS_CHECK)}:\*\*"
            r"[ \t]*(PASS|NOT_APPLICABLE)[ \t]*$"
        )
        mechanical_match = mechanical_pattern.search(text)
        if mechanical_match is None:
            raise ValueError(
                f"SLICE-{queue:04d} queue document {path.name} must contain "
                f"'**{_POST_0079_MECHANICAL_INVARIANTS_CHECK}:** PASS | NOT_APPLICABLE'"
            )
        mechanical_section = _mechanical_invariants_section(queue=queue, path=path, text=text)
        _validate_mechanical_invariant_evidence(
            queue=queue,
            path=path,
            section=mechanical_section,
            check_value=mechanical_match.group(1),
        )

    return queue, path.name


def main() -> None:
    registry = ContractRegistry.from_directory(SPECS)
    req_count, acceptance_count = requirements_check()
    no_active_drafts_check()
    claude_approval_autonomy_check()
    state_slice, _ = project_state_freshness_check()
    launch_phase = declared_production_launch_pack_phase()
    architecture, criteria_count, workflow_status, production_status = trigger_gate_state_check()
    queue_slice, queue_file = queue_slice_startability_check()
    print(f"active schemas: {len(registry.schema_names)}")
    print("claude approval-autonomy guard: PASS")
    print(f"requirements: {req_count}")
    print(f"acceptance criteria: {acceptance_count}")
    print(f"project state accepted through: SLICE-{state_slice:04d}")
    print(f"post-0051 architecture reconciliation: {architecture}")
    print(f"accepted technical native Search criteria: {criteria_count}")
    print(f"workflow reassessment: {workflow_status}")
    print(f"production readiness gate: {production_status}")
    print(f"production launch-pack phase: {launch_phase}")
    if queue_file is None:
        print(f"queue readiness document: not yet present for SLICE-{queue_slice:04d}")
    else:
        print(f"queue contract valid: SLICE-{queue_slice:04d} ({queue_file})")
    print("repository governance validation: PASS")


if __name__ == "__main__":
    main()
