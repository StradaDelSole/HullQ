from __future__ import annotations

import os
import subprocess
from pathlib import Path

from scripts.workflow import claude_diag


def test_env_status_never_prints_secret_value(capsys, monkeypatch) -> None:
    monkeypatch.setenv("HULLQ_TEST_DATABASE_URL", "secret-value")
    assert claude_diag.env_status("HULLQ_TEST_DATABASE_URL") == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == "HULLQ_TEST_DATABASE_URL=SET"
    assert "secret-value" not in captured.out


def test_latest_temp_dir_returns_newest_matching_directory(
    tmp_path: Path,
    capsys,
    monkeypatch,
) -> None:
    older = tmp_path / "hullq_s0051_e2e_old"
    newer = tmp_path / "hullq_s0051_e2e_new"
    older.mkdir()
    newer.mkdir()
    os.utime(older, (1, 1))
    os.utime(newer, (2, 2))
    monkeypatch.setattr(claude_diag.tempfile, "gettempdir", lambda: str(tmp_path))

    assert claude_diag.latest_temp_dir("hullq_s0051_e2e_") == 0
    captured = capsys.readouterr()
    assert captured.out.strip() == str(newer)


def test_run_local_test_db_injects_db_url_without_mutating_parent_env(monkeypatch) -> None:
    observed: dict[str, object] = {}

    def fake_run(command, *, cwd, env, check):
        observed["command"] = command
        observed["cwd"] = cwd
        observed["env"] = env
        observed["check"] = check
        return subprocess.CompletedProcess(command, 0)

    script = claude_diag.ROOT / "scripts" / "validate_repository.py"
    monkeypatch.delenv("HULLQ_TEST_DATABASE_URL", raising=False)
    monkeypatch.setattr(claude_diag.subprocess, "run", fake_run)

    relative = str(script.relative_to(claude_diag.ROOT))
    assert claude_diag.run_local_test_db(relative, []) == 0
    assert "HULLQ_TEST_DATABASE_URL" not in os.environ
    env = observed["env"]
    assert isinstance(env, dict)
    assert env["HULLQ_TEST_DATABASE_URL"] == claude_diag._LOCAL_TEST_DB_URL


def test_run_local_api_uses_fixed_local_test_env_and_timeout(monkeypatch, capsys) -> None:
    observed: dict[str, object] = {}

    def fake_run(command, *, cwd, env, check, timeout):
        observed["command"] = command
        observed["cwd"] = cwd
        observed["env"] = env
        observed["check"] = check
        observed["timeout"] = timeout
        raise subprocess.TimeoutExpired(command, timeout)

    monkeypatch.setattr(claude_diag.subprocess, "run", fake_run)

    assert claude_diag.run_local_api("127.0.0.1", 18123, 6.0) == 0
    env = observed["env"]
    assert isinstance(env, dict)
    assert env["HULLQ_DATABASE_URL"] == claude_diag._LOCAL_TEST_DB_URL
    assert env["HULLQ_PREVIEW_SIGNING_SECRET"] == claude_diag._LOCAL_PREVIEW_SIGNING_SECRET
    assert observed["timeout"] == 6.0

    captured = capsys.readouterr()
    assert "LOCAL_API_STAYED_UP 127.0.0.1:18123 for 6s" in captured.out
    assert claude_diag._LOCAL_TEST_DB_URL not in captured.out
    assert claude_diag._LOCAL_PREVIEW_SIGNING_SECRET not in captured.out
