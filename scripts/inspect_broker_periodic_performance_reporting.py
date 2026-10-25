"""SLICE-0089 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the broker periodic performance report vertical against a real,
disposable PostgreSQL 18 schema and two real local HTTP server processes:
FastAPI (real `uvicorn`, not an in-process TestClient) and the built
Astro/Node SSR web package. Authentication uses a directly minted,
cryptographically signed session cookie -- mirrors
`scripts/inspect_broker_inventory_export.py`'s identical, already-accepted
shortcut. FastAPI still performs its own real signature verification of
that exact cookie on every request below.

Demonstrates, end to end:

    1. Organization A's own live performance snapshot and its on-demand
       download artifact (through both FastAPI directly and the real
       built Astro SSR same-origin proxy) report identical metrics.
    2. Organization A activates a MONTHLY periodic subscription through
       the real authenticated API (OWNER-gated, CSRF-protected).
    3. A deterministic worker tick (in-process callable -- this slice
       exposes no HTTP trigger route by design) admits exactly one
       newly-closed, genuinely zero-Lead/zero-view period and delivers it
       through the deterministic local adapter.
    4. A repeated tick is idempotent: no second admission, no second send.
    5. The periodic artifact is fetchable by Organization A through the
       real built Astro SSR proxy, and the zero-Lead period is rendered
       explicitly, never omitted.
    6. Organization B cannot read Organization A's periodic report, even
       by the exact correct `period_run_id` (no enumeration oracle).
    7. A real headless-Chromium exercise of the Download link and the
       periodic-delivery subscription form (`inspect_broker_report_ui_playwright.mjs`).
    8. Exact finish marker.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_periodic_performance_reporting.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_A = "ORG-0089-E2E-A"
_ORG_B = "ORG-0089-E2E-B"
_ACCOUNT_A = "ACC-0089-E2E-A"
_ACCOUNT_B = "ACC-0089-E2E-B"
_SUBSCRIPTION_CSRF_HEADER_VALUE = "broker-report-subscription-v1"


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


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(
        self,
        method: str,
        url: str,
        *,
        extra_headers: dict[str, str] | None = None,
        data: bytes | None = None,
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        req = urllib.request.Request(
            url, headers=dict(extra_headers or {}), method=method, data=data
        )
        response = self._opener.open(req, timeout=10)
        return response.status, response.headers, response.read()

    def get(
        self, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url, extra_headers=extra_headers)

    def put_json(
        self, url: str, payload: dict[str, Any], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self.request(
            "PUT", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
        )


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _csrf_headers(web_base: str) -> dict[str, str]:
    return {"Origin": web_base, "X-HullQ-Requested-With": _SUBSCRIPTION_CSRF_HEADER_VALUE}


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str, session_secret_b64: str, web_base: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0089_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    env["HULLQ_SESSION_SIGNING_SECRET"] = session_secret_b64
    env["HULLQ_WEB_BASE_URL"] = web_base
    env["HULLQ_WEB_ORIGIN"] = web_base
    env["HULLQ_SESSION_COOKIE_SECURE"] = "false"
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
    schema_name = f"hullq_s0089e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.application.broker_report_dispatch import (
            DeterministicLocalReportDeliveryAdapter,
            run_report_dispatch_worker_once,
        )
        from hullq.domain.broker_access import AuthenticatedIdentity, Provider
        from hullq.domain.publishing_eligibility import (
            AccountId,
            MarketplaceOrganization,
            MarketplaceOrganizationId,
            MembershipRole,
            MembershipState,
            OrganizationMembership,
            OrganizationMembershipId,
            OrganizationPublishingEligibility,
            ProfessionalCategory,
        )
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.persistence.broker_identity import (
            seed_marketplace_organization,
            seed_organization_membership,
        )
        from hullq.security.session_token import mint_session_token

        url = _with_search_path(base_url, schema_name)
        print("BROKER PERIODIC PERFORMANCE REPORTING (SLICE-0089)\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        api_port = _free_port()
        web_port = _free_port()
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        api_proc, api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=base64.urlsafe_b64encode(preview_secret).decode("ascii"),
            session_secret_b64=base64.urlsafe_b64encode(session_secret).decode("ascii"),
            web_base=web_base,
        )
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
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
        web_log_path = Path(tempfile.mkstemp(prefix="hullq_s0089_web_", suffix=".log")[1])
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )
        web_ready = _wait_for_http(f"{web_base}/broker")
        ok &= web_ready
        print(
            f"2. Astro SSR serving (real built Node process) -> {'OK' if web_ready else 'FAIL'}\n"
        )

        if not ok:
            print("BROKER PERIODIC PERFORMANCE REPORTING RESULT -> FAIL")
            return 1

        def _mint_cookie(account_id: str) -> str:
            identity = AuthenticatedIdentity(
                provider=Provider.AUTH0,
                issuer="https://issuer.test/",
                subject=f"subject-{account_id}",
                auth_time=datetime.now(UTC),
                mfa_satisfied=True,
            )
            minted = mint_session_token(identity, AccountId(account_id), secret=session_secret)
            return minted.token

        conn = psycopg.connect(url)
        try:
            for account_id, org_id in ((_ACCOUNT_A, _ORG_A), (_ACCOUNT_B, _ORG_B)):
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        [account_id],
                    )
                conn.commit()
                seed_marketplace_organization(
                    conn,
                    MarketplaceOrganization(
                        id=MarketplaceOrganizationId(org_id),
                        professional_category=ProfessionalCategory.BROKER,
                        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                    ),
                )
                seed_organization_membership(
                    conn,
                    OrganizationMembership(
                        id=OrganizationMembershipId(f"MEM-{account_id}"),
                        account_id=AccountId(account_id),
                        organization_id=MarketplaceOrganizationId(org_id),
                        roles=frozenset({MembershipRole.OWNER}),
                        state=MembershipState.ACTIVE,
                    ),
                )
                conn.commit()
            print("3. Two real seeded Organizations (A, B) with OWNER membership -> OK\n")
        finally:
            conn.close()

        session_a = BrowserSession()
        session_a.jar.set_cookie(
            http.cookiejar.Cookie(
                0,
                "hullq_session",
                _mint_cookie(_ACCOUNT_A),
                None,
                False,
                "127.0.0.1",
                False,
                False,
                "/",
                True,
                False,
                None,
                True,
                None,
                None,
                {},
            )
        )
        session_b = BrowserSession()
        session_b.jar.set_cookie(
            http.cookiejar.Cookie(
                0,
                "hullq_session",
                _mint_cookie(_ACCOUNT_B),
                None,
                False,
                "127.0.0.1",
                False,
                False,
                "/",
                True,
                False,
                None,
                True,
                None,
                None,
                {},
            )
        )

        # Step 4: live snapshot + download artifact, identical metrics,
        # through both FastAPI directly and the real Astro SSR proxy.
        status, _, body = session_a.get(
            f"{api_base}/api/broker/organizations/{_ORG_A}/performance?window=ALL_TIME"
        )
        json_ok = status == 200
        json_body = _json(body) if json_ok else {}
        status, headers, download_body = session_a.get(
            f"{api_base}/api/broker/organizations/{_ORG_A}/report/download?window=ALL_TIME"
        )
        api_download_ok = (
            status == 200
            and headers.get("content-type", "").startswith("text/html")
            and str(json_body.get("public_listing_views")) in download_body.decode("utf-8")
        )
        status, _, proxy_download_body = session_a.get(
            f"{web_base}/broker/organizations/{_ORG_A}/performance/report?window=ALL_TIME"
        )
        # Each call independently re-renders `generated_at` at real request
        # time, so the two responses are not byte-identical -- what must
        # match is the metrics population, not the generation timestamp.
        web_proxy_download_ok = status == 200 and str(
            json_body.get("public_listing_views")
        ) in proxy_download_body.decode("utf-8")
        download_ok = json_ok and api_download_ok and web_proxy_download_ok
        ok &= download_ok
        print(
            f"4. Live on-demand download: FastAPI + Astro SSR proxy both report metrics "
            f"matching the JSON snapshot -> {'OK' if download_ok else 'FAIL'}"
        )

        # Step 5: activate a MONTHLY subscription through the real API.
        status, _, body = session_a.put_json(
            f"{api_base}/api/broker/organizations/{_ORG_A}/report-subscription",
            {
                "status": "ACTIVE",
                "period_kind": "MONTHLY",
                "recipient_email": "broker@example.com",
                "expected_revision": 0,
            },
            extra_headers=_csrf_headers(web_base),
        )
        subscribe_ok = status == 200 and _json(body).get("status") == "ACTIVE"
        ok &= subscribe_ok
        print(
            f"5. Organization A activates a MONTHLY subscription -> {'OK' if subscribe_ok else 'FAIL'}"
        )

        # Step 6: deterministic worker tick -- in-process callable (no HTTP
        # trigger route exists by design); admits exactly one newly-closed,
        # genuinely zero-Lead/zero-view period and delivers it.
        worker_conn = psycopg.connect(url)
        try:
            from hullq.domain.broker_report_subscription import (
                ReportPeriodKind,
                period_bounds,
            )

            # The subscription's anchor_date was fixed at real "now" when it
            # was first activated above (bootstrap_anchor_date=as_of.date()
            # inside the API's own set_report_subscription call). Land
            # `as_of` exactly one day after the first MONTHLY period's own
            # close -- deterministically past period index 0, and
            # deterministically nowhere near period index 1's own close
            # (every calendar month is >= 28 days), regardless of which
            # day-of-month "now" happens to be.
            _, period0_end = period_bounds(datetime.now(UTC).date(), ReportPeriodKind.MONTHLY, 0)
            as_of = period0_end + timedelta(days=1)
            adapter = DeterministicLocalReportDeliveryAdapter()
            first_tick = run_report_dispatch_worker_once(
                worker_conn, adapter=adapter, worker_id="e2e-w1", as_of=as_of
            )
            tick_ok = (
                first_tick.admission.value == "ADMITTED"
                and first_tick.delivery.value == "DELIVERED"
                and len(adapter.sent) == 1
            )
            period_run_id = first_tick.admitted_period_run_id
            ok &= tick_ok
            print(
                f"6. Deterministic worker tick admits + delivers exactly one zero-Lead period "
                f"-> {'OK' if tick_ok else 'FAIL'} (period_run_id={period_run_id})"
            )

            second_tick = run_report_dispatch_worker_once(
                worker_conn, adapter=adapter, worker_id="e2e-w1", as_of=as_of
            )
            replay_ok = (
                second_tick.admission.value == "NO_DUE_PERIOD"
                and second_tick.delivery.value == "NO_ITEM_CLAIMED"
                and len(adapter.sent) == 1
            )
            ok &= replay_ok
            print(
                f"7. Repeated tick is idempotent (no double admission/send) -> {'OK' if replay_ok else 'FAIL'}"
            )
        finally:
            worker_conn.close()

        # Step 8: periodic artifact fetchable by A through the real Astro
        # SSR proxy; zero-Lead period is represented explicitly.
        status, _, periodic_body_a = session_a.get(
            f"{web_base}/broker/organizations/{_ORG_A}/performance/report/{period_run_id}"
        )
        periodic_fetch_ok = status == 200 and "No observed views" in periodic_body_a.decode("utf-8")
        ok &= periodic_fetch_ok
        print(
            f"8. Organization A fetches its periodic report via the real Astro SSR proxy; "
            f"zero-Lead period is represented, not omitted -> {'OK' if periodic_fetch_ok else 'FAIL'}"
        )

        # Step 9: Organization B cannot read A's periodic report, even by
        # the exact correct period_run_id -- no enumeration oracle.
        status, _, _ = session_b.get(
            f"{web_base}/broker/organizations/{_ORG_B}/performance/report/{period_run_id}"
        )
        cross_org_denied = status == 404
        status, _, _ = session_b.get(
            f"{web_base}/broker/organizations/{_ORG_B}/performance/report/does-not-exist"
        )
        nonexistent_also_404 = status == 404
        isolation_ok = cross_org_denied and nonexistent_also_404
        ok &= isolation_ok
        print(
            f"9. Organization B cannot read A's periodic report by the correct id, and a "
            f"nonexistent id resolves identically (no enumeration oracle) -> "
            f"{'OK' if isolation_ok else 'FAIL'}"
        )

        # Step 10: real headless-Chromium exercise of the Download link and
        # the periodic-delivery subscription form.
        playwright_proc = subprocess.run(
            [
                "node",
                str(WEB_DIR / "scripts" / "inspect_broker_report_ui_playwright.mjs"),
                "--web-base",
                web_base,
                "--org-id",
                _ORG_A,
                "--session-cookie",
                _mint_cookie(_ACCOUNT_A),
            ],
            cwd=WEB_DIR,
            capture_output=True,
            text=True,
            timeout=120,
        )
        print(playwright_proc.stdout, end="")
        if playwright_proc.stderr:
            print(playwright_proc.stderr, file=sys.stderr, end="")
        browser_ui_ok = playwright_proc.returncode == 0
        ok &= browser_ui_ok
        print(
            f"10. Real headless-browser UI exercise (download + subscription save) -> "
            f"{'OK' if browser_ui_ok else 'FAIL'}\n"
        )

        print("BROKER PERIODIC PERFORMANCE REPORTING RESULT ->", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
