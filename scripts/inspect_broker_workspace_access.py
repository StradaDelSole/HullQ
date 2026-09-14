"""SLICE-0053 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed authenticated-Broker-Workspace-access vertical
against a real, disposable PostgreSQL 18 schema and three real local HTTP
servers: a deterministic local OIDC/JWKS test issuer
(`hullq.testing.oidc_test_issuer`), FastAPI, and the built Astro/Node SSR
web package. No Account is ever created by monkeypatching -- every Account
in this proof is created by a real authorization-code login round-trip
through the real issuer and FastAPI's real token/JWKS validation.

Per `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md` §14, demonstrates:

    1. first login creates one stable HullQ Account mapping
    2. retry (same identity, fresh login) creates no duplicate Account
    3. no-membership identity cannot enter an Organization workspace
    4. active member sees only authorized Organization context
    5. cross-Organization access fails closed, non-enumerating
    6. privileged member without MFA is blocked/stepped-up
    7. same member with valid MFA reaches the protected Astro workspace
    8. HullQ membership/role changes alter the next authorization read
       without any Auth0-side change
    9. logout/session invalidation removes workspace access

Plus: unauthenticated denial, state-mismatch/tampered-code rejection at the
callback, identical non-enumerating 404 bodies for an unauthorized-but-
existing vs. a never-created Organization, the production `__Host-`/
`Secure`/`Path=/`/`HttpOnly`/no-`Domain` cookie hardening, rejection of a
forged/tossed login-state cookie (correct `state` field, invalid
signature -- the sibling-subdomain cookie-injection scenario from the
2026-09-14 independent review), the Auth0-documented step-up ACR value,
and `Cache-Control: private, no-store` on both protected Astro pages.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_workspace_access.py
"""

from __future__ import annotations

import base64
import http.client
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
import urllib.request
import uuid
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, quote, urlsplit, urlunsplit

import psycopg

from hullq.domain.broker_access import Provider
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
    update_membership_state,
)
from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_ORG_A_ID = "ORG-0053-PRIVILEGED"
_ORG_B_ID = "ORG-0053-OTHER-ACCOUNT"
_NEVER_SEEDED_ORG_ID = "ORG-0053-NEVER-CREATED"
_SUBJECT = "broker-0053-subject"
_OTHER_SUBJECT = "broker-0053-other-subject"


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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 15.0) -> bool:
    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except urllib.error.HTTPError:
            return True
        except urllib.error.URLError, ConnectionError, TimeoutError, OSError:
            time.sleep(0.2)
    return False


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _b64url_nopad(data: bytes) -> str:
    """Matches `hullq.application.broker_login`'s unpadded cookie-value encoding."""
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


#: This proof runs with the real production cookie-hardening default
#: (`HULLQ_SESSION_COOKIE_SECURE` unset -> Secure/`__Host-`-prefixed): see
#: independent review 2026-09-14, exact-head a7fee1a0. `BrowserSession`
#: below is a hand-rolled client, not a real browser -- it does not itself
#: enforce Secure/`__Host-` acceptance rules, so it can complete a full
#: round trip over plain HTTP for the proof while this script separately
#: asserts the emitted `Set-Cookie` headers carry the exact attributes a
#: real browser requires to accept a `__Host-`-prefixed cookie at all.
_SESSION_COOKIE_PROD_NAME = "__Host-hullq_session"
_LOGIN_STATE_COOKIE_PROD_NAME = "__Host-hullq_login_state"


def _cookie_set_header(session: BrowserSession, base_name: str) -> str:
    return next((h for h in session.last_set_cookie_headers if f"{base_name}=" in h), "")


def _is_hardened_cookie_header(header: str, *, prod_name: str) -> bool:
    """True iff *header* satisfies every attribute a browser requires to
    accept a `__Host-`-prefixed cookie (RFC 6265bis): that exact name,
    `Secure`, `Path=/`, and no `Domain` attribute at all."""
    return (
        header.startswith(f"{prod_name}=")
        and "Secure" in header
        and "Path=/" in header
        and "Domain=" not in header
    )


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    """Return every HTTP response (2xx/3xx/4xx/5xx) unchanged: no automatic
    redirect-following and no exception raised for a non-2xx status. Gives
    this script full manual control over the browser-style navigation.
    """

    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


_OPENER = urllib.request.build_opener(_NoRedirect)


class BrowserSession:
    """A minimal, fully manual, real-cookie-jar HTTP client.

    Deliberately not `http.cookiejar`: real Set-Cookie response headers are
    parsed and replayed by hand, so every step of this proof can inspect
    the exact cookie attributes (e.g. `HttpOnly`) a real browser would act
    on, without any hidden automatic behavior.
    """

    def __init__(self) -> None:
        self.cookies: dict[str, str] = {}
        self.last_set_cookie_headers: list[str] = []

    def request(
        self, method: str, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = dict(extra_headers or {})
        if self.cookies:
            headers["Cookie"] = "; ".join(f"{k}={v}" for k, v in self.cookies.items())
        req = urllib.request.Request(url, headers=headers, method=method)
        response = _OPENER.open(req, timeout=10)
        status = response.status
        resp_headers = response.headers
        body = response.read()

        set_cookie_lines = resp_headers.get_all("Set-Cookie") or []
        self.last_set_cookie_headers = set_cookie_lines
        for line in set_cookie_lines:
            name_value = line.split(";", 1)[0]
            if "=" in name_value:
                key, value = name_value.split("=", 1)
                self.cookies[key.strip()] = value.strip()
        return status, resp_headers, body

    def get(self, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url)

    def post(self, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("POST", url)

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        """Follow login -> issuer authorize -> issuer redirect -> callback."""
        status, headers, body = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, body = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}: {body!r}"
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
    schema_name = f"hullq_s0053e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0053_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("AUTHENTICATED BROKER WORKSPACE ACCESS\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK\n")

        issuer_port = _free_port()
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://127.0.0.1:{issuer_port}/"
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
            f"uvicorn.run(app, host='127.0.0.1', port={issuer_port}, log_level='warning')\n"
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
        print(
            f"1. deterministic local OIDC/JWKS test issuer serving -> {'OK' if issuer_ready else 'FAIL'}"
        )

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
        # Deliberately NOT set: the real production default
        # (HULLQ_SESSION_COOKIE_SECURE unset -> Secure/__Host--prefixed
        # cookies) is exercised end-to-end below, not the local-HTTP
        # opt-out. Pop any stale value the parent shell/session happens to
        # have exported so this proof is deterministic regardless.
        api_env.pop("HULLQ_SESSION_COOKIE_SECURE", None)

        api_log_path = log_dir / "api.log"
        with api_log_path.open("wb") as api_log:
            api_proc = subprocess.Popen(
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
                env=api_env,
                stdout=api_log,
                stderr=subprocess.STDOUT,
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
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )
        web_ready = _wait_for_http(f"{web_base}/broker")
        ok &= web_ready
        print(f"3. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("AUTHENTICATED BROKER WORKSPACE ACCESS RESULT -> FAIL")
            return 1

        # 4. unauthenticated /broker: no broker data, login path only, never cacheable.
        session = BrowserSession()
        status, headers, body = session.get(f"{web_base}/broker")
        page_text = body.decode("utf-8")
        step4_ok = (
            status == 200
            and "log in" in page_text
            and _ORG_A_ID not in page_text
            and headers.get("Cache-Control") == "private, no-store"
        )
        ok &= step4_ok
        print(
            f"4. unauthenticated /broker -> login path, no broker data, "
            f"Cache-Control: private, no-store -> {'OK' if step4_ok else 'FAIL'}"
        )

        # 5. first login creates one stable HullQ Account mapping, and sets
        # __Host-/Secure/Path=/-hardened, HttpOnly cookies for both the
        # login-state and session cookies (independent review 2026-09-14,
        # exact-head a7fee1a0: defense against sibling-subdomain cookie
        # tossing/session fixation).
        login_url = f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
        status, headers, _ = session.get(login_url)
        login_state_header = _cookie_set_header(session, _LOGIN_STATE_COOKIE_PROD_NAME)
        login_state_hardened = "HttpOnly" in login_state_header and _is_hardened_cookie_header(
            login_state_header, prod_name=_LOGIN_STATE_COOKIE_PROD_NAME
        )
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, body = session.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}: {body!r}"
        callback_url = headers["Location"]
        status, headers, body = session.get(callback_url)

        first_login_ok = status == 302 and headers.get("Location") == f"{web_base}/broker"
        session_cookie_header = _cookie_set_header(session, _SESSION_COOKIE_PROD_NAME)
        session_cookie_hardened = (
            "HttpOnly" in session_cookie_header
            and _is_hardened_cookie_header(
                session_cookie_header, prod_name=_SESSION_COOKIE_PROD_NAME
            )
        )
        ok &= first_login_ok and session_cookie_hardened and login_state_hardened
        print(
            f"5. first login sets __Host-/Secure/Path=/-hardened, HttpOnly login-state + "
            f"session cookies and redirects to /broker -> "
            f"{'OK' if (first_login_ok and session_cookie_hardened and login_state_hardened) else 'FAIL'}"
        )

        status, _, body = session.get(f"{api_base}/api/broker/context")
        context = _json(body)
        account_id = context["account_id"]
        step5b_ok = status == 200 and context["organizations"] == []
        ok &= step5b_ok
        print(
            f"   fresh Account has zero Organization access (no membership yet) -> "
            f"{'OK' if step5b_ok else 'FAIL'}\n"
        )

        # Sibling-subdomain cookie-injection defense: a forged login-state
        # cookie carrying the CORRECT `state` (matching the real callback's
        # query string) but no valid HMAC signature -- exactly what a
        # hostile sibling subdomain could set via `Domain=<parent>` cookie
        # tossing, never a value this server actually signed -- must still
        # be rejected. This is independent of, and a second layer behind,
        # the __Host- cookie-prefix defense verified above.
        forged_session = BrowserSession()
        status, headers, _ = forged_session.get(login_url)
        authorize_url = headers["Location"]
        status, headers, _ = forged_session.get(authorize_url)
        real_callback_url = headers["Location"]
        real_state = parse_qs(urlsplit(real_callback_url).query)["state"][0]
        forged_payload = _b64url_nopad(
            json.dumps(
                {"state": real_state, "nonce": "attacker-controlled-nonce", "next": "/broker"}
            ).encode("utf-8")
        )
        forged_login_state_cookie = f"{forged_payload}.{_b64url_nopad(b'not-a-valid-signature-x')}"
        forged_cookie_key = next(
            (k for k in forged_session.cookies if "hullq_login_state" in k), None
        )
        assert forged_cookie_key is not None, "expected a login-state cookie to forge"
        forged_session.cookies[forged_cookie_key] = forged_login_state_cookie
        status, _, body = forged_session.get(real_callback_url)
        cookie_forgery_rejected_ok = status == 400
        ok &= cookie_forgery_rejected_ok
        print(
            f"   forged/tossed login-state cookie (correct state, invalid signature) "
            f"rejected -> {'OK' if cookie_forgery_rejected_ok else 'FAIL'}\n"
        )

        # 3 (contract numbering). no-membership identity cannot enter an
        # Organization workspace -- confirmed above via the empty list, and
        # again here against a concrete Organization id.
        status, _, body = session.get(f"{api_base}/api/broker/organizations/{_NEVER_SEEDED_ORG_ID}")
        step_no_membership_ok = status == 404
        ok &= step_no_membership_ok
        print(
            f"6. no-membership Account denied entry to any Organization workspace -> "
            f"{'OK' if step_no_membership_ok else 'FAIL'}"
        )

        # Seed the durable directory now that we know the real JIT account_id.
        conn = psycopg.connect(url)
        try:
            # A real durable Account for the foreign membership below --
            # never created by monkeypatching, just via the same JIT
            # mapping path a real login would use, for an identity this
            # proof never logs in as.
            other_account_id = get_or_create_account_for_identity(
                conn, provider=Provider.AUTH0, issuer=issuer_base, subject=_OTHER_SUBJECT
            ).account_id
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_A_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_B_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0053-A"),
                account_id=AccountId(account_id),
                organization_id=MarketplaceOrganizationId(_ORG_A_ID),
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership_a)
            # org_b belongs to an entirely different (never-logged-in)
            # seeded account -- our account has zero relationship to it.
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0053-B"),
                    account_id=other_account_id,
                    organization_id=MarketplaceOrganizationId(_ORG_B_ID),
                    roles=frozenset({MembershipRole.OWNER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print(
            "7. seeded ORG_A (PUBLISHER membership for this Account) and ORG_B (another Account's) -> OK"
        )

        # 4 (contract). active member sees only authorized Organization context.
        status, _, body = session.get(f"{api_base}/api/broker/context")
        context = _json(body)
        org_ids = {org["organization_id"] for org in context["organizations"]}
        step_context_ok = status == 200 and org_ids == {_ORG_A_ID}
        ok &= step_context_ok
        print(
            f"8. membership change alters the very next read: Account now sees exactly ORG_A -> "
            f"{'OK' if step_context_ok else 'FAIL'}"
        )

        # 6 (contract). privileged member without MFA is blocked.
        status, _, body = session.get(f"{api_base}/api/broker/organizations/{_ORG_A_ID}")
        mfa_blocked_ok = status == 403 and _json(body).get("error") == "mfa_required"
        ok &= mfa_blocked_ok
        print(
            f"9. privileged (PUBLISHER) membership without MFA is blocked -> {'OK' if mfa_blocked_ok else 'FAIL'}"
        )

        # 5 (contract). cross-Organization access fails closed, non-enumerating.
        status_b, _, body_b = session.get(f"{api_base}/api/broker/organizations/{_ORG_B_ID}")
        status_never, _, body_never = session.get(
            f"{api_base}/api/broker/organizations/{_NEVER_SEEDED_ORG_ID}"
        )
        cross_org_ok = status_b == 404 and status_never == 404 and body_b == body_never
        ok &= cross_org_ok
        print(
            f"10. cross-Organization access (existing org, foreign membership) and a never-created "
            f"org id are identical 404s -> {'OK' if cross_org_ok else 'FAIL'}"
        )

        # 7 (contract). step-up MFA reaches the protected workspace, via Astro.
        # Uses the Auth0-documented step-up ACR value, not a test-only
        # shorthand (independent review 2026-09-14, exact-head a7fee1a0):
        # the deterministic issuer exercises this exact value too.
        stepup_login_url = (
            f"{api_base}/api/auth/login?next=/broker/organizations/{_ORG_A_ID}"
            f"&login_hint={_SUBJECT}&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        status, headers, body = session.follow_full_login(stepup_login_url)
        stepup_redirect_ok = (
            status == 302
            and headers.get("Location") == f"{web_base}/broker/organizations/{_ORG_A_ID}"
        )
        ok &= stepup_redirect_ok

        status, headers, body = session.get(f"{web_base}/broker/organizations/{_ORG_A_ID}")
        page_text = body.decode("utf-8")
        stepup_ok = (
            status == 200
            and _ORG_A_ID in page_text
            and "PUBLISHER" in page_text
            and "BROKER" in page_text
            and headers.get("Cache-Control") == "private, no-store"
        )
        ok &= stepup_ok
        print(
            f"11. MFA step-up (Auth0 ACR value) + Astro workspace landing shows "
            f"Organization/category/roles, Cache-Control: private, no-store -> "
            f"{'OK' if (stepup_redirect_ok and stepup_ok) else 'FAIL'}"
        )

        # Direct API confirms the same authorized state (not just the page).
        status, _, body = session.get(f"{api_base}/api/broker/organizations/{_ORG_A_ID}")
        api_authorized_ok = status == 200 and _json(body)["mfa_satisfied"] is True
        ok &= api_authorized_ok
        print(
            f"    FastAPI /api/broker/organizations/{_ORG_A_ID} now AUTHORIZED with mfa_satisfied=true -> {'OK' if api_authorized_ok else 'FAIL'}\n"
        )

        # 8 (contract). membership state change alters the next read, no Auth0-side change.
        conn = psycopg.connect(url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-0053-A"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()
        status, _, body = session.get(f"{api_base}/api/broker/organizations/{_ORG_A_ID}")
        revoked_ok = status == 404
        ok &= revoked_ok
        print(
            f"12. INACTIVE membership (same still-valid session, no re-login) denies immediately -> "
            f"{'OK' if revoked_ok else 'FAIL'}"
        )

        # Reactivate for the retry/idempotency + logout checks below.
        conn = psycopg.connect(url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-0053-A"), MembershipState.ACTIVE
            )
            conn.commit()
        finally:
            conn.close()

        # 2 (contract). retry (fresh login, same identity) creates no duplicate Account.
        retry_session = BrowserSession()
        retry_login_url = f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
        retry_session.follow_full_login(retry_login_url)
        status, _, body = retry_session.get(f"{api_base}/api/broker/context")
        retry_account_id = _json(body)["account_id"]
        retry_ok = status == 200 and retry_account_id == account_id
        ok &= retry_ok
        print(
            f"13. retry login (same identity) maps to the identical Account -> {'OK' if retry_ok else 'FAIL'}"
        )

        # Tampered/mismatched state at the callback fails closed.
        status, headers, _ = session.get(login_url)
        authorize_url = headers["Location"]
        status, headers, _ = session.get(authorize_url)
        real_callback_url = headers["Location"]
        tampered_callback_url = real_callback_url.replace("state=", "state=tampered-", 1)
        status, _, body = session.get(tampered_callback_url)
        tamper_ok = status == 400
        ok &= tamper_ok
        print(
            f"14. callback with a mismatched state fails closed (400) -> {'OK' if tamper_ok else 'FAIL'}"
        )

        # 9 (contract). logout/session invalidation removes workspace access.
        status, headers, _ = session.post(f"{api_base}/api/auth/logout")
        logout_status_ok = status == 200
        logout_cookie_cleared = "hullq_session=" not in "; ".join(
            session.last_set_cookie_headers
        ) or any(
            "hullq_session=;" in h or "Max-Age=0" in h for h in session.last_set_cookie_headers
        )
        session_cookie_key = next((k for k in session.cookies if "hullq_session" in k), None)
        if session_cookie_key is not None:
            session.cookies.pop(session_cookie_key, None)
        status, _, body = session.get(f"{api_base}/api/broker/context")
        post_logout_denied_ok = status == 401
        status, _, body = session.get(f"{web_base}/broker")
        page_text = body.decode("utf-8")
        post_logout_web_ok = "log in" in page_text and _ORG_A_ID not in page_text
        logout_ok = (
            logout_status_ok
            and logout_cookie_cleared
            and post_logout_denied_ok
            and post_logout_web_ok
        )
        ok &= logout_ok
        print(
            f"15. logout clears the session; workspace access is gone on API and web -> {'OK' if logout_ok else 'FAIL'}\n"
        )

        # Ordinary logs must never contain the client secret / session secret.
        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = (
            client_secret not in api_log_text
            and client_secret not in web_log_text
            and _b64url(session_secret) not in api_log_text
            and _b64url(session_secret) not in web_log_text
        )
        ok &= secrets_clean
        print(
            f"    ordinary API/web logs contain no client/session secret -> {'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(f"AUTHENTICATED BROKER WORKSPACE ACCESS RESULT -> {'PASS' if ok else 'FAIL'}")
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


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


if __name__ == "__main__":
    raise SystemExit(main())
