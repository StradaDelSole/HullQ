"""SLICE-0081 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the Organization workspace operational dashboard's one genuinely
new behavior against a real, disposable PostgreSQL 18 schema and three real
local HTTP servers: a deterministic local OIDC/JWKS test issuer, FastAPI,
and the built Astro/Node SSR web package. The dashboard itself introduces no
new domain truth -- it only composes four already-accepted, already-tested
read services (Lead counts/inbox, listing drafts, inventory, performance) on
one page. The one thing no existing proof already covers is that
composition's HIGH_RISK invariant (SLICE-0081 contract "Must-never-change
invariant" / "Retry / replay / partial-failure behavior"): one panel's
denial must never cascade into, or be disguised as, another panel's
successful-empty state.

Demonstrates, with one real Account holding two real Organization
memberships:

    1. a MEMBER-only (non-PUBLISHER) Organization: the Drafts panel renders
       the distinct "not authorized" denial, never "no drafts yet" -- while
       the independently-authorized Leads/Inventory/Performance panels on
       the SAME page render their own genuine, distinct empty-but-ok state.
    2. a PUBLISHER Organization (reached via real MFA step-up): the Drafts
       panel instead renders its own genuine empty-ok state, proving the
       denial above was role-specific, not a general implementation defect.
    3. a foreign Organization (owned by an entirely different Account) and
       a never-created Organization id remain identical, non-enumerating
       404s on this same composed page -- no panel is fetched/rendered for
       either case.
    4. the authorized dashboard still carries Cache-Control: private,
       no-store and X-Robots-Tag: noindex.
    5. neither Organization's dashboard body ever contains the other
       Organization's id.

Bounded-request-size (page_size: 5 forwarded to each client) and the
dashboard's zero-mutation GET are structural properties of
`[organization_id].astro`'s source and are not re-exercised at runtime here.
Each underlying read service's own domain correctness (lead counts,
promotion readiness, inventory lifecycle, performance aggregation) is
already proven by its own accepted slice's retained proof/tests; this
script does not re-prove those.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_workspace_dashboard.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any

import psycopg

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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    get_or_create_account_for_identity,
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.domain.broker_access import Provider
from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_ORG_NOPUB_ID = "ORG-0081-MEMBER-ONLY"
_ORG_PUB_ID = "ORG-0081-PUBLISHER"
_ORG_FOREIGN_ID = "ORG-0081-FOREIGN"
_NEVER_SEEDED_ORG_ID = "ORG-0081-NEVER-CREATED"
_SUBJECT = "broker-0081-subject"
_FOREIGN_SUBJECT = "broker-0081-foreign-subject"


def _base_db_url() -> str:
    url = os.environ.get("HULLQ_TEST_DATABASE_URL", "").strip()
    if not url:
        print("HULLQ_TEST_DATABASE_URL is not set.", file=sys.stderr)
        raise SystemExit(1)
    return url


def _with_search_path(base_url: str, schema_name: str) -> str:
    from urllib.parse import quote, urlsplit, urlunsplit

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
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    """A real, standards-compliant cookie-jar HTTP client (mirrors
    `inspect_broker_workspace_access.py`'s identical rationale)."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )

    def get(self, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        req = urllib.request.Request(url, method="GET")
        response = self._opener.open(req, timeout=10)
        status = response.status
        headers = response.headers
        body = response.read()
        return status, headers, body

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        status, headers, _ = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, _ = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}"
        callback_url = headers["Location"]
        return self.get(callback_url)


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0081e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0081_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("BROKER WORKSPACE OPERATIONAL DASHBOARD -- PANEL ISOLATION PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK\n")

        _ISSUER_HOST = "127.0.0.2"
        issuer_port = _free_port(_ISSUER_HOST)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{_ISSUER_HOST}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-e2e-client"
        client_secret = secrets.token_urlsafe(24)
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        issuer_code = (
            "import uvicorn\n"
            "from hullq.testing.oidc_test_issuer import create_test_issuer_app\n"
            f"app = create_test_issuer_app(issuer={issuer_base!r}, client_id={client_id!r}, "
            f"client_secret={client_secret!r}, redirect_uri={redirect_uri!r})\n"
            f"uvicorn.run(app, host={_ISSUER_HOST!r}, port={issuer_port}, log_level='warning')\n"
        )
        issuer_log_path = log_dir / "issuer.log"
        with issuer_log_path.open("wb") as issuer_log:
            issuer_proc = subprocess.Popen(
                [sys.executable, "-c", issuer_code],
                cwd=REPO_ROOT,
                stdout=issuer_log,
                stderr=subprocess.STDOUT,
            )
        issuer_ready = _wait_for_http(f"{issuer_base}.well-known/jwks.json")
        ok &= issuer_ready
        print(f"1. deterministic local OIDC/JWKS test issuer serving -> {'OK' if issuer_ready else 'FAIL'}")

        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = _b64url(preview_secret)
        api_env["HULLQ_SESSION_SIGNING_SECRET"] = _b64url(session_secret)
        api_env["HULLQ_AUTH_ISSUER"] = issuer_base
        api_env["HULLQ_AUTH_AUTHORIZE_URL"] = f"{issuer_base}authorize"
        api_env["HULLQ_AUTH_TOKEN_URL"] = f"{issuer_base}token"
        api_env["HULLQ_AUTH_JWKS_URL"] = f"{issuer_base}.well-known/jwks.json"
        api_env["HULLQ_AUTH_CLIENT_ID"] = client_id
        api_env["HULLQ_AUTH_CLIENT_SECRET"] = client_secret
        api_env["HULLQ_AUTH_REDIRECT_URI"] = redirect_uri
        api_env["HULLQ_WEB_BASE_URL"] = web_base
        api_env["HULLQ_WEB_ORIGIN"] = web_base
        api_env["HULLQ_SESSION_COOKIE_SECURE"] = "false"

        api_log_path = log_dir / "api.log"
        with api_log_path.open("wb") as api_log:
            api_proc = subprocess.Popen(
                [
                    sys.executable, "-m", "uvicorn", "hullq.api.app:create_app", "--factory",
                    "--host", "127.0.0.1", "--port", str(api_port),
                    "--no-access-log", "--log-level", "warning",
                ],
                cwd=REPO_ROOT, env=api_env, stdout=api_log, stderr=subprocess.STDOUT,
            )
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
        ok &= api_ready
        print(f"2. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        web_log_path = log_dir / "web.log"
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR, env=web_env, stdout=web_log, stderr=subprocess.STDOUT,
            )
        web_ready = _wait_for_http(f"{web_base}/broker")
        ok &= web_ready
        print(f"3. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("BROKER WORKSPACE OPERATIONAL DASHBOARD RESULT -> FAIL")
            return 1

        # One real login for the primary Account (no step-up yet: ORG_NOPUB
        # below only ever needs a MEMBER-role membership, which is not in
        # PRIVILEGED_MFA_ROLES).
        session = BrowserSession()
        login_url = f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
        session.follow_full_login(login_url)
        status, _, body = session.get(f"{api_base}/api/broker/context")
        account_id = json.loads(body)["account_id"]
        print(f"4. real login established one Account ({account_id}) -> OK\n")

        conn = psycopg.connect(url)
        try:
            foreign_account_id = get_or_create_account_for_identity(
                conn, provider=Provider.AUTH0, issuer=issuer_base, subject=_FOREIGN_SUBJECT
            ).account_id
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_NOPUB_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_PUB_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_FOREIGN_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0081-NOPUB"),
                    account_id=AccountId(account_id),
                    organization_id=MarketplaceOrganizationId(_ORG_NOPUB_ID),
                    roles=frozenset({MembershipRole.MEMBER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0081-PUB"),
                    account_id=AccountId(account_id),
                    organization_id=MarketplaceOrganizationId(_ORG_PUB_ID),
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            # ORG_FOREIGN belongs to an entirely different Account -- our
            # Account has zero relationship to it.
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0081-FOREIGN"),
                    account_id=foreign_account_id,
                    organization_id=MarketplaceOrganizationId(_ORG_FOREIGN_ID),
                    roles=frozenset({MembershipRole.OWNER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print(
            "5. seeded ORG_NOPUB (MEMBER-only, no MFA needed), ORG_PUB (PUBLISHER), "
            "ORG_FOREIGN (another Account's) -> OK\n"
        )

        # 6. MEMBER-only Organization: Drafts panel is a distinct denial,
        # never "no drafts yet"; Leads/Inventory/Performance independently
        # render their own genuine empty-ok state on the SAME response.
        status, headers, body = session.get(f"{web_base}/broker/organizations/{_ORG_NOPUB_ID}")
        page_text = body.decode("utf-8")
        drafts_denied_ok = (
            "does not include permission to view this section" in page_text
            and "This Organization has no drafts yet." not in page_text
        )
        other_panels_ok_empty = (
            "No leads yet." in page_text
            and "This Organization has no listings yet." in page_text
            and "Public listing views observed: 0" in page_text
        )
        headers_ok = (
            headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        nopub_ok = status == 200 and drafts_denied_ok and other_panels_ok_empty and headers_ok
        ok &= nopub_ok
        print(
            f"6. MEMBER-only Organization: Drafts panel denied distinctly from empty, "
            f"while Leads/Inventory/Performance independently render their own "
            f"genuine empty-ok state; headers preserved -> {'OK' if nopub_ok else 'FAIL'}"
        )

        # 7. PUBLISHER Organization (reached via real MFA step-up): Drafts
        # panel instead renders its own genuine empty-ok state -- proving
        # step 6's denial was role-specific, not a general defect.
        stepup_login_url = (
            f"{api_base}/api/auth/login?next=/broker/organizations/{_ORG_PUB_ID}"
            f"&login_hint={_SUBJECT}&acr_values={urllib.parse.quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session.follow_full_login(stepup_login_url)
        status, headers, body = session.get(f"{web_base}/broker/organizations/{_ORG_PUB_ID}")
        page_text = body.decode("utf-8")
        pub_ok = (
            status == 200
            and "This Organization has no drafts yet." in page_text
            and "does not include permission to view this section" not in page_text
            and _ORG_NOPUB_ID not in page_text
        )
        ok &= pub_ok
        print(
            f"7. PUBLISHER Organization (MFA step-up): Drafts panel is its own genuine "
            f"empty-ok state, and never leaks ORG_NOPUB's id -> {'OK' if pub_ok else 'FAIL'}"
        )

        # ORG_NOPUB's own page must likewise never leak ORG_PUB's id.
        status, _, body = session.get(f"{web_base}/broker/organizations/{_ORG_NOPUB_ID}")
        page_text = body.decode("utf-8")
        no_cross_leak_ok = _ORG_PUB_ID not in page_text
        ok &= no_cross_leak_ok
        print(f"   ORG_NOPUB's page never leaks ORG_PUB's id -> {'OK' if no_cross_leak_ok else 'FAIL'}\n")

        # 8. foreign Organization and a never-created Organization id remain
        # identical, non-enumerating 404s on this composed page.
        status_foreign, _, body_foreign = session.get(f"{web_base}/broker/organizations/{_ORG_FOREIGN_ID}")
        status_never, _, body_never = session.get(f"{web_base}/broker/organizations/{_NEVER_SEEDED_ORG_ID}")
        cross_org_ok = (
            status_foreign == 404
            and status_never == 404
            and body_foreign == body_never
        )
        ok &= cross_org_ok
        print(
            f"8. foreign Organization and a never-created Organization id are identical, "
            f"non-enumerating 404s (no panel data) -> {'OK' if cross_org_ok else 'FAIL'}\n"
        )

        print(f"BROKER WORKSPACE OPERATIONAL DASHBOARD RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
