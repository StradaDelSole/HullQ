from pathlib import Path

import pytest

from scripts.validate_repository import (
    _validate_trigger_gate_evidence,
    trigger_gate_state_check,
)


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def _project_state(tmp_path: Path, accepted: int) -> Path:
    return _write(
        tmp_path / "PROJECT_STATE.md",
        f"<!-- PROJECT_STATE_ACCEPTED_SLICE: {accepted:04d} -->\n"
        f"<!-- PROJECT_STATE_QUEUE_SLICE: {accepted + 1:04d} -->\n",
    )


def _trigger_gates(tmp_path: Path, *, workflow: str = "NOT_DUE", count: int = 1) -> Path:
    return _write(
        tmp_path / "POST_0051_TRIGGER_GATES.md",
        "<!-- POST_0051_ARCHITECTURE_RECONCILIATION: PASS -->\n"
        f"<!-- TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: {count} -->\n"
        "<!-- WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056 -->\n"
        f"<!-- WORKFLOW_REASSESSMENT_STATUS: {workflow} -->\n",
    )


def _production_gate(
    tmp_path: Path,
    *,
    gate: str = "NOT_TRIGGERED",
    broker_data: str = "NOT_PRESENT",
    pilot: str = "NOT_STARTED",
    launch: str = "NOT_STARTED",
) -> Path:
    return _write(
        tmp_path / "PRODUCTION_READINESS_GATE.md",
        f"<!-- PRODUCTION_READINESS_GATE_STATUS: {gate} -->\n"
        f"<!-- EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: {broker_data} -->\n"
        f"<!-- PRODUCTION_PILOT_STATUS: {pilot} -->\n"
        f"<!-- PUBLIC_PRODUCTION_LAUNCH_STATUS: {launch} -->\n",
    )


def test_workflow_reassessment_cannot_remain_not_due_after_slice_0056(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="must be DUE or PASS"):
        trigger_gate_state_check(
            project_state=_project_state(tmp_path, 56),
            trigger_gates=_trigger_gates(tmp_path, workflow="NOT_DUE"),
            production_gate=_production_gate(tmp_path),
        )


def test_workflow_reassessment_due_is_valid_between_0056_and_0057_readiness(
    tmp_path: Path,
) -> None:
    state = trigger_gate_state_check(
        project_state=_project_state(tmp_path, 56),
        trigger_gates=_trigger_gates(tmp_path, workflow="DUE"),
        production_gate=_production_gate(tmp_path),
    )
    assert state == ("PASS", 1, "DUE", "NOT_TRIGGERED")


def test_workflow_reassessment_pass_allows_post_0056_state(tmp_path: Path) -> None:
    state = trigger_gate_state_check(
        project_state=_project_state(tmp_path, 56),
        trigger_gates=_trigger_gates(tmp_path, workflow="PASS"),
        production_gate=_production_gate(tmp_path),
    )
    assert state == ("PASS", 1, "PASS", "NOT_TRIGGERED")


def test_broker_production_data_cannot_start_without_readiness_pass(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="External broker production data"):
        trigger_gate_state_check(
            project_state=_project_state(tmp_path, 51),
            trigger_gates=_trigger_gates(tmp_path),
            production_gate=_production_gate(tmp_path, gate="IN_PROGRESS", broker_data="ACTIVE"),
        )


def test_internal_broker_production_data_does_not_force_workflow_review_before_pilot(
    tmp_path: Path,
) -> None:
    state = trigger_gate_state_check(
        project_state=_project_state(tmp_path, 51),
        trigger_gates=_trigger_gates(tmp_path, workflow="NOT_DUE"),
        production_gate=_production_gate(tmp_path, gate="PASS", broker_data="ACTIVE"),
    )
    assert state == ("PASS", 1, "NOT_DUE", "PASS")


def test_external_production_cannot_start_without_production_gate_pass(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="External broker production data"):
        trigger_gate_state_check(
            project_state=_project_state(tmp_path, 51),
            trigger_gates=_trigger_gates(tmp_path, workflow="PASS"),
            production_gate=_production_gate(tmp_path, gate="IN_PROGRESS", pilot="ACTIVE"),
        )


def test_external_production_also_requires_workflow_reassessment(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="mandatory pre-pilot workflow reassessment"):
        trigger_gate_state_check(
            project_state=_project_state(tmp_path, 51),
            trigger_gates=_trigger_gates(tmp_path, workflow="NOT_DUE"),
            production_gate=_production_gate(tmp_path, gate="PASS", pilot="ACTIVE"),
        )


def test_external_production_passes_only_when_both_gates_pass(tmp_path: Path) -> None:
    state = trigger_gate_state_check(
        project_state=_project_state(tmp_path, 51),
        trigger_gates=_trigger_gates(tmp_path, workflow="PASS"),
        production_gate=_production_gate(tmp_path, gate="PASS", pilot="ACTIVE"),
    )
    assert state == ("PASS", 1, "PASS", "PASS")


def _trigger_section(
    *,
    adds: str,
    ordinal: str,
    second: str,
    third: str,
    workflow: str = "NOT_DUE",
    production: str = "NOT_TRIGGERED",
) -> str:
    return (
        f"**Production readiness gate:** {production}\n"
        f"**Adds technical native Search criterion:** {adds}\n"
        f"**Technical Search criterion ordinal:** {ordinal}\n"
        f"**Second-criterion bridge comparison:** {second}\n"
        f"**Third-copy abstraction guard:** {third}\n"
        f"**Workflow reassessment status:** {workflow}\n"
    )


def _validate_search_trigger_section(
    *,
    queue: int,
    path: Path,
    section: str,
    criteria_count: int,
    workflow_status: str = "NOT_DUE",
    production_status: str = "NOT_TRIGGERED",
) -> None:
    _validate_trigger_gate_evidence(
        queue=queue,
        path=path,
        section=section,
        criteria_count=criteria_count,
        workflow_status=workflow_status,
        production_status=production_status,
    )


def test_readiness_must_copy_canonical_production_gate_status(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="does not match canonical status"):
        _validate_search_trigger_section(
            queue=52,
            path=tmp_path / "SLICE-0052-test.md",
            section=_trigger_section(
                adds="NO",
                ordinal="NOT_APPLICABLE",
                second="NOT_APPLICABLE",
                third="NOT_APPLICABLE",
                production="NOT_TRIGGERED",
            ),
            criteria_count=1,
            production_status="IN_PROGRESS",
        )


def test_due_workflow_blocks_slice_0057_readiness(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="workflow reassessment is DUE"):
        _validate_search_trigger_section(
            queue=57,
            path=tmp_path / "SLICE-0057-test.md",
            section=_trigger_section(
                adds="NO",
                ordinal="NOT_APPLICABLE",
                second="NOT_APPLICABLE",
                third="NOT_APPLICABLE",
                workflow="DUE",
            ),
            criteria_count=1,
            workflow_status="DUE",
        )


def test_second_search_criterion_requires_bridge_comparison(tmp_path: Path) -> None:
    path = tmp_path / "SLICE-0052-test.md"
    with pytest.raises(ValueError, match="Second-criterion bridge comparison"):
        _validate_search_trigger_section(
            queue=52,
            path=path,
            section=_trigger_section(
                adds="YES",
                ordinal="2",
                second="NOT_APPLICABLE",
                third="NOT_APPLICABLE",
            ),
            criteria_count=1,
        )


def test_second_search_criterion_passes_with_comparison(tmp_path: Path) -> None:
    _validate_search_trigger_section(
        queue=52,
        path=tmp_path / "SLICE-0052-test.md",
        section=_trigger_section(
            adds="YES",
            ordinal="2",
            second="PASS",
            third="NOT_APPLICABLE",
        ),
        criteria_count=1,
    )


def test_third_search_criterion_cannot_create_unreviewed_third_copy(tmp_path: Path) -> None:
    path = tmp_path / "SLICE-0053-test.md"
    with pytest.raises(ValueError, match="Third-copy abstraction guard"):
        _validate_search_trigger_section(
            queue=53,
            path=path,
            section=_trigger_section(
                adds="YES",
                ordinal="3",
                second="PASS",
                third="NOT_APPLICABLE",
            ),
            criteria_count=2,
        )


def test_third_search_criterion_passes_with_abstraction_guard(tmp_path: Path) -> None:
    _validate_search_trigger_section(
        queue=53,
        path=tmp_path / "SLICE-0053-test.md",
        section=_trigger_section(
            adds="YES",
            ordinal="3",
            second="PASS",
            third="PASS",
        ),
        criteria_count=2,
    )
