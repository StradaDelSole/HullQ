from __future__ import annotations

import subprocess
from pathlib import Path

from scripts.workflow import historical_replay_scope as hrs


def test_is_relevant_path_matches_bootstrap_research_tree() -> None:
    assert hrs.is_relevant_path("research/bootstrap/wikidata/manifest.json")
    assert hrs.is_relevant_path("scripts/bootstrap/wikidata_tier0_runner.py")
    assert hrs.is_relevant_path("src/hullq/bootstrap/wikidata_tier0.py")
    assert hrs.is_relevant_path("src/hullq/persistence/identity_importer.py")
    assert hrs.is_relevant_path("src/hullq/persistence/sql/002_canonical_identity_schema.sql")
    assert hrs.is_relevant_path("tests/persistence/test_wikidata_tier0_bootstrap_integration.py")
    assert hrs.is_relevant_path("tests/persistence/conftest.py")
    assert hrs.is_relevant_path("uv.lock")
    assert hrs.is_relevant_path("pyproject.toml")


def test_is_relevant_path_rejects_unrelated_product_change() -> None:
    assert not hrs.is_relevant_path("src/hullq/api/routes/public_listing.py")
    assert not hrs.is_relevant_path("web/src/pages/index.astro")
    assert not hrs.is_relevant_path("docs/slices/SLICE-0074-example.md")


def test_is_relevant_path_normalizes_windows_separators() -> None:
    assert hrs.is_relevant_path("research\\bootstrap\\wikidata\\manifest.json")


def test_decide_always_relevant_for_schedule_and_push_and_dispatch() -> None:
    for event in ("schedule", "workflow_dispatch", "push"):
        relevant, reason = hrs.decide(event=event, base="", head="deadbeef")
        assert relevant is True
        assert event in reason


def test_decide_fails_open_when_shas_missing() -> None:
    relevant, reason = hrs.decide(event="pull_request", base="", head="deadbeef")
    assert relevant is True
    assert "undeterminable" in reason


def test_decide_fails_open_on_all_zero_base_sha() -> None:
    relevant, _reason = hrs.decide(event="pull_request", base="0" * 40, head="deadbeef")
    assert relevant is True


def test_decide_uses_real_git_diff_for_relevant_change(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    base = _commit(tmp_path, "unrelated.txt", "one")
    (tmp_path / "research").mkdir()
    (tmp_path / "research" / "bootstrap").mkdir()
    head = _commit(tmp_path, "research/bootstrap/manifest.json", "{}")

    relevant, reason = hrs.decide_in(repo=tmp_path, event="pull_request", base=base, head=head)
    assert relevant is True
    assert "research/bootstrap/manifest.json" in reason


def test_decide_uses_real_git_diff_for_irrelevant_change(tmp_path: Path) -> None:
    _init_repo(tmp_path)
    base = _commit(tmp_path, "unrelated.txt", "one")
    head = _commit(tmp_path, "unrelated.txt", "two")

    relevant, reason = hrs.decide_in(repo=tmp_path, event="pull_request", base=base, head=head)
    assert relevant is False
    assert reason == "no relevant path changed"


def _init_repo(repo: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.com"], cwd=repo, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repo, check=True)


def _commit(repo: Path, relative_path: str, content: str) -> str:
    path = repo / relative_path
    path.write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", relative_path], cwd=repo, check=True)
    subprocess.run(["git", "commit", "-q", "-m", f"add {relative_path}"], cwd=repo, check=True)
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, capture_output=True, text=True, check=True
    )
    return result.stdout.strip()
