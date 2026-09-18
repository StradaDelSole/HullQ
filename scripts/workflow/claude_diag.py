"""Approval-free diagnostic helpers for Claude Code in HullQ.

This module centralizes recurring local diagnostics that otherwise tempt an
agent to build shell pipelines, environment-prefix assignments, or PowerShell
expressions that trigger permission prompts.

It never prints secret-bearing environment-variable values.
"""

from __future__ import annotations

import argparse
import os
import socket
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
_LOCAL_TEST_DB_URL = "postgresql://hullq_test:hullq_test@localhost:5432/hullq_test"


def env_status(name: str) -> int:
    print(f"{name}={'SET' if os.environ.get(name) else 'UNSET'}")
    return 0


def tcp_check(host: str, port: int, timeout: float) -> int:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            pass
    except OSError as exc:
        print(f"UNREACHABLE {host}:{port}: {type(exc).__name__}")
        return 1
    print(f"REACHABLE {host}:{port}")
    return 0


def latest_temp_dir(prefix: str) -> int:
    base = Path(tempfile.gettempdir())
    matches = [path for path in base.glob(f"{prefix}*") if path.is_dir()]
    if not matches:
        print("NONE")
        return 1
    latest = max(matches, key=lambda path: path.stat().st_mtime)
    print(latest)
    return 0


def run_local_test_db(script: str, args: list[str]) -> int:
    candidate = (ROOT / script).resolve()
    scripts_root = (ROOT / "scripts").resolve()

    if scripts_root not in candidate.parents or candidate.suffix != ".py" or not candidate.is_file():
        print("Refusing to run a path outside repository scripts/*.py", file=sys.stderr)
        return 2

    env = os.environ.copy()
    env["HULLQ_TEST_DATABASE_URL"] = _LOCAL_TEST_DB_URL
    completed = subprocess.run(
        [sys.executable, str(candidate), *args],
        cwd=ROOT,
        env=env,
        check=False,
    )
    return completed.returncode


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    env_parser = subparsers.add_parser("env-status")
    env_parser.add_argument("name")

    tcp_parser = subparsers.add_parser("tcp-check")
    tcp_parser.add_argument("host")
    tcp_parser.add_argument("port", type=int)
    tcp_parser.add_argument("--timeout", type=float, default=2.0)

    temp_parser = subparsers.add_parser("latest-temp-dir")
    temp_parser.add_argument("prefix")

    db_parser = subparsers.add_parser("run-local-test-db")
    db_parser.add_argument("script")
    db_parser.add_argument("args", nargs=argparse.REMAINDER)

    return parser


def main() -> int:
    args = build_parser().parse_args()

    if args.command == "env-status":
        return env_status(args.name)
    if args.command == "tcp-check":
        return tcp_check(args.host, args.port, args.timeout)
    if args.command == "latest-temp-dir":
        return latest_temp_dir(args.prefix)
    if args.command == "run-local-test-db":
        return run_local_test_db(args.script, args.args)

    raise AssertionError(f"Unhandled command: {args.command}")


if __name__ == "__main__":
    raise SystemExit(main())
