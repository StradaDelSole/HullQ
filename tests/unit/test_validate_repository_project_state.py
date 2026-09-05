from pathlib import Path

import pytest

from scripts.validate_repository import (
    declared_project_state_slice,
    latest_acceptance_closure_slice,
    project_state_freshness_check,
)


def _write_state(path: Path, slice_number: str) -> None:
    path.write_text(
        f"# state\n<!-- PROJECT_STATE_ACCEPTED_SLICE: {slice_number} -->\n",
        encoding="utf-8",
    )


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
