from pathlib import Path

import pytest

from scripts.validate_repository import (
    declared_project_queue_slice,
    declared_project_state_slice,
    latest_acceptance_closure_slice,
    project_state_freshness_check,
    queue_slice_startability_check,
)


def _write_state(path: Path, slice_number: str, queue_number: str | None = None) -> None:
    queue = queue_number or f"{int(slice_number) + 1:04d}"
    path.write_text(
        "# state\n"
        f"<!-- PROJECT_STATE_ACCEPTED_SLICE: {slice_number} -->\n"
        f"<!-- PROJECT_STATE_QUEUE_SLICE: {queue} -->\n",
        encoding="utf-8",
    )


def _ready_slice_text(*, slice_type: str = "IMPLEMENTATION", status: str = "READY") -> str:
    return (
        "# slice\n"
        f"**Type:** {slice_type}\n"
        f"**Status:** {status}\n"
        "**ONE-CAPABILITY CHECK:** PASS\n"
        "**VISIBLE-RESULT CHECK:** PASS\n"
        "**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS\n"
    )


def _reconciled_ready_slice_text(*, status: str = "READY") -> str:
    return (
        _ready_slice_text(status=status)
        + "**REPOSITORY RECONCILIATION CHECK:** PASS\n"
        + "\n## Decision / implementation reconciliation\n"
        + "\n**Accepted records checked:** docs/accepted.md\n"
        + "**Production implementation checked:** src/current.py; tests/unit/test_current.py\n"
        + "**Already implemented / not re-decided:** existing behavior\n"
        + "**Exact remaining gap:** one bounded capability\n"
        + "**Accepted-but-unimplemented obligations:** NONE\n"
        + "**Material classifications:** DECIDED_AND_IMPLEMENTED; GENUINELY_OPEN\n"
    )


def _handoff_slice_text(status: str) -> str:
    return _ready_slice_text(status=status) + f"**Status set by this handoff:** `{status}`\n"


def test_latest_acceptance_closure_slice_uses_highest_number(tmp_path: Path) -> None:
    (tmp_path / "SLICE-0044-acceptance-closure.md").write_text("x", encoding="utf-8")
    (tmp_path / "SLICE-0045-acceptance-closure.md").write_text("x", encoding="utf-8")
    (tmp_path / "SLICE-0046-physical-boat-identity-persistence.md").write_text(
        "not accepted", encoding="utf-8"
    )

    assert latest_acceptance_closure_slice(tmp_path) == 45


def test_declared_project_state_slice_requires_exactly_one_marker(tmp_path: Path) -> None:
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0045")
    assert declared_project_state_slice(state) == 45

    state.write_text("# no marker\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one"):
        declared_project_state_slice(state)


def test_declared_project_queue_slice_requires_exactly_one_marker(tmp_path: Path) -> None:
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0045", "0046")
    assert declared_project_queue_slice(state) == 46

    state.write_text("# no queue marker\n", encoding="utf-8")
    with pytest.raises(ValueError, match="exactly one"):
        declared_project_queue_slice(state)


def test_project_state_freshness_passes_when_marker_matches_latest_closure(
    tmp_path: Path,
) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    (slices / "SLICE-0045-acceptance-closure.md").write_text("x", encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0045")

    assert project_state_freshness_check(slices_dir=slices, project_state=state) == (45, 45)


def test_project_state_freshness_fails_when_new_closure_is_not_reflected(
    tmp_path: Path,
) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    (slices / "SLICE-0045-acceptance-closure.md").write_text("x", encoding="utf-8")
    (slices / "SLICE-0046-acceptance-closure.md").write_text("x", encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0045")

    with pytest.raises(ValueError, match="latest acceptance closure is SLICE-0046"):
        project_state_freshness_check(slices_dir=slices, project_state=state)


def test_queue_startability_allows_queue_before_readiness_document_exists(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    assert queue_slice_startability_check(slices_dir=slices, project_state=state) == (47, None)


def test_queue_startability_reproduces_0047_bad_type_header(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    slice_path = slices / "SLICE-0047-market-episode.md"
    slice_path.write_text(
        _ready_slice_text(slice_type="IMPLEMENTATION READINESS", status="READY_FOR_REVIEW"),
        encoding="utf-8",
    )
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    with pytest.raises(ValueError, match="expected exactly one primary"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_startability_rejects_transitional_readiness_status(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    slice_path = slices / "SLICE-0047-market-episode.md"
    slice_path.write_text(_ready_slice_text(status="READY_FOR_REVIEW"), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    with pytest.raises(ValueError, match="expected 'READY'"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_startability_rejects_review_without_matching_handoff_marker(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    slice_path = slices / "SLICE-0047-market-episode.md"
    slice_path.write_text(_ready_slice_text(status="REVIEW"), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    with pytest.raises(ValueError, match="lacks the matching implementation handoff marker"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_startability_allows_explicit_review_handoff(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0047-market-episode.md"
    (slices / filename).write_text(_handoff_slice_text("REVIEW"), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    assert queue_slice_startability_check(slices_dir=slices, project_state=state) == (47, filename)


def test_queue_startability_allows_explicit_blocked_handoff(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0047-market-episode.md"
    (slices / filename).write_text(_handoff_slice_text("BLOCKED"), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    assert queue_slice_startability_check(slices_dir=slices, project_state=state) == (47, filename)


def test_queue_startability_rejects_mismatched_handoff_marker(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    slice_path = slices / "SLICE-0047-market-episode.md"
    slice_path.write_text(
        _ready_slice_text(status="REVIEW") + "**Status set by this handoff:** `BLOCKED`\n",
        encoding="utf-8",
    )
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    with pytest.raises(ValueError, match="lacks the matching implementation handoff marker"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_startability_passes_for_exact_start_slice_contract(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0047-market-episode.md"
    (slices / filename).write_text(_ready_slice_text(), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0046", "0047")

    assert queue_slice_startability_check(slices_dir=slices, project_state=state) == (47, filename)


def test_queue_0051_rejects_missing_repository_reconciliation_check(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    (slices / filename).write_text(_ready_slice_text(), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    with pytest.raises(ValueError, match="REPOSITORY RECONCILIATION CHECK"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_0051_rejects_reconciliation_check_without_required_section(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    (slices / filename).write_text(
        _ready_slice_text() + "**REPOSITORY RECONCILIATION CHECK:** PASS\n",
        encoding="utf-8",
    )
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    with pytest.raises(ValueError, match="Decision / implementation reconciliation"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_0051_rejects_missing_reconciliation_evidence_line(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    text = _reconciled_ready_slice_text().replace(
        "**Exact remaining gap:** one bounded capability\n", ""
    )
    (slices / filename).write_text(text, encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    with pytest.raises(ValueError, match="Exact remaining gap"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_0051_rejects_empty_reconciliation_evidence_value(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    text = _reconciled_ready_slice_text().replace(
        "**Accepted records checked:** docs/accepted.md",
        "**Accepted records checked:**   ",
    )
    (slices / filename).write_text(text, encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    with pytest.raises(ValueError, match="Accepted records checked"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


@pytest.mark.parametrize("placeholder", ["TODO", "TBD", "PLACEHOLDER", "<specific records>"])
def test_queue_0051_rejects_placeholder_reconciliation_evidence(
    tmp_path: Path, placeholder: str
) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    text = _reconciled_ready_slice_text().replace(
        "**Accepted records checked:** docs/accepted.md",
        f"**Accepted records checked:** {placeholder}",
    )
    (slices / filename).write_text(text, encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    with pytest.raises(ValueError, match="placeholder rather than repository-backed evidence"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_0051_rejects_unknown_material_classification(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    text = _reconciled_ready_slice_text().replace(
        "DECIDED_AND_IMPLEMENTED; GENUINELY_OPEN",
        "MAYBE_ALREADY_DONE",
    )
    (slices / filename).write_text(text, encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    with pytest.raises(ValueError, match="accepted reconciliation classification"):
        queue_slice_startability_check(slices_dir=slices, project_state=state)


def test_queue_0051_passes_with_repository_reconciliation_contract(tmp_path: Path) -> None:
    slices = tmp_path / "slices"
    slices.mkdir()
    filename = "SLICE-0051-native-inventory-search.md"
    (slices / filename).write_text(_reconciled_ready_slice_text(), encoding="utf-8")
    state = tmp_path / "PROJECT_STATE.md"
    _write_state(state, "0050", "0051")

    assert queue_slice_startability_check(slices_dir=slices, project_state=state) == (51, filename)
