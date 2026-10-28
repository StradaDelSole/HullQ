"""SLICE-0094 independent-review amendment Finding A — real browser proof
that the Power Search form's actual GET submission omits an untouched
`power_drive`/`power_engine_count` control entirely, across all five
locales.

Starts two real local HTTP server processes (real `uvicorn` FastAPI, not an
in-process TestClient, and the built Astro/Node SSR web package) against a
disposable, migrated-but-empty PostgreSQL 18 schema -- no seeded listing is
required, because this proof is about the *request URL the browser itself
constructs* on submit, never Search truth/matching (that is proven
separately against real seeded PostgreSQL by
`tests/persistence/test_power_engine_count_slice_0094.py` and
`tests/persistence/test_power_engine_count_api_slice_0094.py`). Mirrors
`scripts/inspect_broker_inventory_export.py`'s identical process-
orchestration shape, bounded to exactly this one proof.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_power_search_form.py
"""

from __future__ import annotations

import base64
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)


def _base_db_url() -> str:
    url = os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip()
    if not url:
        print("HULLQ_TEST_DATABASE_URL is not set.", file=sys.stderr)
        raise SystemExit(1)
    return url


def _with_search_path(base_url: str, schema_name: str) -> str:
    parts = urlsplit(base_url)
    option = quote(f"-c search_path={schema_name}", safe="")
    query = f"{parts.query}&options={option}" if parts.query else f"options={option}"
    return urlunsplit(parts._replace(query=query))


def _create_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


def _drop_schema(base_url: str, schema_name: str) -> None:
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')
    finally:
        conn.close()


def _free_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind((host, 0))
        return int(probe.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except urllib.error.HTTPError:
            return True
        except _HTTP_PROBE_TRANSIENT_ERRORS:
            time.sleep(0.2)
    return False


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0094_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    with log_path.open("wb") as log_file:
        proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "hullq.api.app:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(api_port),
                "--no-access-log",
                "--log-level",
                "warning",
            ],
            cwd=REPO_ROOT,
            env=env,
            stdout=log_file,
            stderr=subprocess.STDOUT,
        )
    return proc, log_path


def _stop_process(proc: subprocess.Popen[bytes] | None) -> None:
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0094form_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )

        url = _with_search_path(base_url, schema_name)
        print("POWER SEARCH FORM OMISSION PROOF (SLICE-0094 amendment, Finding A)\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head (empty schema, no seeded data) -> OK")

        api_port = _free_port()
        web_port = _free_port()
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        preview_secret = os.urandom(32)

        api_proc, api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=base64.urlsafe_b64encode(preview_secret).decode("ascii"),
        )
        api_ready = _wait_for_http(f"{api_base}/api/search/en/power")
        ok &= api_ready
        print(f"1. FastAPI serving (real uvicorn process) -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print(
                api_log_path.read_text(encoding="utf-8", errors="replace")[-4000:], file=sys.stderr
            )

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        web_log_path = Path(tempfile.mkstemp(prefix="hullq_s0094_web_", suffix=".log")[1])
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )
        web_ready = _wait_for_http(f"{web_base}/en/power/search")
        ok &= web_ready
        print(
            f"2. Astro SSR serving (real built Node process) -> {'OK' if web_ready else 'FAIL'}\n"
        )

        if not ok:
            print("POWER SEARCH FORM OMISSION PROOF RESULT -> FAIL")
            return 1

        playwright_proc = subprocess.run(
            [
                "node",
                str(WEB_DIR / "scripts" / "inspect_power_search_form_playwright.mjs"),
                "--web-base",
                web_base,
            ],
            cwd=WEB_DIR,
            capture_output=True,
            text=True,
            timeout=180,
        )
        print(playwright_proc.stdout, end="")
        if playwright_proc.stderr:
            print(playwright_proc.stderr, file=sys.stderr, end="")
        browser_ui_ok = playwright_proc.returncode == 0
        ok &= browser_ui_ok
        print(
            f"3. Real headless-browser form-submission exercise, all five locales -> "
            f"{'OK' if browser_ui_ok else 'FAIL'}\n"
        )

        print("POWER SEARCH FORM OMISSION PROOF RESULT ->", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
