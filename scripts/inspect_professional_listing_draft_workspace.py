"""SLICE-0061 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed authenticated-professional-listing-draft-
workspace vertical against a real, disposable PostgreSQL 18 schema and three
real local HTTP servers: a deterministic local OIDC/JWKS test issuer
(`hullq.testing.oidc_test_issuer`), FastAPI, and the built Astro/Node SSR
web package -- mirroring `scripts/inspect_owner_direct_draft.py` and
`scripts/inspect_professional_inventory_overview.py`'s identical real
browser-style login discipline (no Account is ever created by
monkeypatching, no draft ownership is ever injected outside the signed
session, and every draft mutation in this proof goes through the real
`/broker/organizations/{organization_id}/drafts...` browser surface).

Per `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md` §14, demonstrates:

    1. real OIDC/session login for a workspace-authorized Account whose
       current membership contains PUBLISHER
    2. selected Organization (ORG_A) creates a private draft
    3. partial draft survives reload/list/read
    4. valid update increments version
    5. stale update returns conflict without overwriting
    6. a second Account/Organization (ORG_B) cannot observe or mutate the
       draft; foreign and unknown draft_id share the identical bounded
       not-found shape once the Organization access boundary itself
       succeeds
    7. membership/role revocation changes the next authorization result
    8. invalid CSRF request fails with no mutation
    9. draft pages are private/no-store/noindex and clearly not public
    10. marketplace truth row/state counts remain unchanged by draft work
    11. existing owner-direct retained proof still passes
    12. existing professional inventory retained proof still passes
    13. finishes with the required PASS marker

Independent exact-head review (2026-09-20, HEAD 0dcaadd) found that contract
§9's bounded pagination requirement was implemented end-to-end in FastAPI/
persistence but never actually reachable through the required
`/broker/organizations/{organization_id}/drafts` browser surface itself: the
page never read a `cursor` from its own query string and never rendered a
`next_cursor` continuation link, so drafts past the first default page (50)
were unreachable through the browser. This amendment adds one additional
proof item (16b, a distinct Organization ORG_C) demonstrating that the built
Astro collection page itself -- not merely the API/persistence layer -- can
traverse two bounded pages via cursor with no duplicate rows and no cross-
Organization leakage, plus that a malformed cursor still resolves to the
existing bounded browser invalid-cursor state.

Items 11 and 12 ("existing ... retained proof still passes") are verified
separately by also running `scripts/inspect_owner_direct_draft.py` and
`scripts/inspect_professional_inventory_overview.py` -- this script does not
embed or duplicate either proof (mirrors `inspect_owner_direct_draft.py`'s
identical treatment of item 13 in its own contract).

This proof runs the deterministic local cookie path
(`HULLQ_SESSION_COOKIE_SECURE=false`) exactly like
`scripts/inspect_broker_workspace_access.py`; see that script's module
docstring for why a real `http.cookiejar`-backed client is used instead of a
hand-rolled cookie replay.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_professional_listing_draft_workspace.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import json
import os
import re
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
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

#: See `scripts/inspect_owner_direct_draft.py`'s identical named-tuple
#: rationale: a literal parenthesized `except (A, B, C):` tuple is reformatted
#: by the installed `ruff format` into invalid Python 3 `except A, B, C:`
#: syntax; referencing a named tuple constant sidesteps that defect.
_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_SUBJECT_A = "professional-draft-0061-subject-a"
_SUBJECT_B = "professional-draft-0061-subject-b"
_SESSION_COOKIE_NAME = "hullq_session"
_ORG_A_ID = "ORG-0061-A"
_ORG_B_ID = "ORG-0061-B"
_ORG_C_ID = "ORG-0061-C"
_CSRF_HEADER_VALUE = "professional-listing-draft-v1"

#: Mirrors `scripts/inspect_owner_direct_draft.py`'s identical rationale:
#: the current-schema table set that carries marketplace identity/
#: inventory, NativeListing offer revision/fact, and durable public
#: Search-affecting NativeListing state.
_NON_PROMOTION_TABLES = (
    "physical_boats",
    "market_episodes",
    "native_listings",
    "native_listing_offer_revisions",
    "native_listing_offer_heads",
    "native_listing_publication_transitions",
    "native_listing_freshness_confirmations",
)


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


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def _non_promotion_table_counts(url: str) -> dict[str, int]:
    conn = psycopg.connect(url)
    try:
        counts: dict[str, int] = {}
        with conn.cursor() as cur:
            for table in _NON_PROMOTION_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                row = cur.fetchone()
                assert row is not None
                counts[table] = row[0]
        return counts
    finally:
        conn.close()


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    """Return every HTTP response (2xx/3xx/4xx/5xx) unchanged: no automatic
    redirect-following and no exception raised for a non-2xx status --
    mirrors `scripts/inspect_broker_workspace_access.py`'s identical class.
    """

    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    """A real, standards-compliant cookie-jar HTTP client with form-POST
    support. See `scripts/inspect_broker_workspace_access.py`'s
    `BrowserSession` docstring for why `http.cookiejar` is used rather than
    a hand-rolled cookie replay."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.last_set_cookie_headers: list[str] = []

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
        status = response.status
        resp_headers = response.headers
        body = response.read()
        self.last_set_cookie_headers = resp_headers.get_all("Set-Cookie") or []
        return status, resp_headers, body

    def get(
        self, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url, extra_headers=extra_headers)

    def post_json(
        self, url: str, payload: dict[str, Any], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self.request(
            "POST", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
        )

    def put_json(
        self, url: str, payload: dict[str, Any], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self.request(
            "PUT", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
        )

    def post_form(
        self, url: str, fields: dict[str, str], *, origin: str
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        """Simulates a real browser's same-origin HTML `<form method="POST">`
        submission to *url*: url-encoded body, and the `Origin` header a
        real browser attaches to every POST (urllib does not add this
        automatically, so it is supplied explicitly here)."""
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin}
        return self.request(
            "POST", url, extra_headers=headers, data=urlencode(fields).encode("utf-8")
        )

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        status, headers, body = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, body = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}: {body!r}"
        callback_url = headers["Location"]
        return self.get(callback_url)


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0061e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0061_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
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
            update_membership_state,
        )
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("AUTHENTICATED PROFESSIONAL LISTING DRAFT WORKSPACE\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        index_conn = psycopg.connect(url)
        try:
            with index_conn.cursor() as cur:
                cur.execute(
                    "SELECT 1 FROM pg_indexes WHERE indexname = %s AND tablename = %s",
                    (
                        "ix_professional_listing_drafts_org_updated_id",
                        "professional_listing_drafts",
                    ),
                )
                index_ok = cur.fetchone() is not None
        finally:
            index_conn.close()
        ok &= index_ok
        print(
            f"   supporting (owner_organization_id, updated_at, draft_id) index exists -> {'OK' if index_ok else 'FAIL'}\n"
        )

        before_non_promotion_counts = _non_promotion_table_counts(url)

        issuer_host = "127.0.0.1"
        issuer_port = _free_port(issuer_host)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{issuer_host}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-professional-draft-e2e-client"
        client_secret = secrets.token_urlsafe(24)
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        issuer_code = (
            "import uvicorn\n"
            "from hullq.testing.oidc_test_issuer import create_test_issuer_app\n"
            f"app = create_test_issuer_app(issuer={issuer_base!r}, client_id={client_id!r}, "
            f"client_secret={client_secret!r}, redirect_uri={redirect_uri!r})\n"
            f"uvicorn.run(app, host={issuer_host!r}, port={issuer_port}, log_level='warning')\n"
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
        # Contract §8: the one exact accepted browser Origin for both draft
        # channels' CSRF validation -- the Astro web surface's own origin.
        api_env["HULLQ_WEB_ORIGIN"] = web_base
        api_env["HULLQ_SESSION_COOKIE_SECURE"] = "false"

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
            print("PROFESSIONAL LISTING DRAFT WORKSPACE RESULT -> FAIL")
            return 1

        drafts_path_a = f"/broker/organizations/{_ORG_A_ID}/drafts"
        api_drafts_path_a = f"{api_base}/api/broker/organizations/{_ORG_A_ID}/drafts"

        # unauthenticated draft workspace: login path only, never cacheable.
        anon_session = BrowserSession()
        status, headers, body = anon_session.get(f"{web_base}{drafts_path_a}")
        page_text = body.decode("utf-8")
        step_anon_ok = (
            status == 200  # login path only, not an org-existence signal
            and "log in" in page_text
            and headers.get("Cache-Control") == "private, no-store"
        )
        ok &= step_anon_ok
        print(
            f"4. unauthenticated drafts workspace -> login path only, "
            f"Cache-Control: private, no-store -> {'OK' if step_anon_ok else 'FAIL'}"
        )

        # 1. real OIDC/session login for Account A -- with MFA step-up from
        # the start (contract §10: PUBLISHER is a PRIVILEGED_MFA_ROLES role).
        session_a = BrowserSession()
        login_url_a = (
            f"{api_base}/api/auth/login?next={quote(drafts_path_a, safe='')}"
            f"&login_hint={_SUBJECT_A}&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        status, headers, _ = session_a.follow_full_login(login_url_a)
        login_redirect_ok = (
            status == 302 and headers.get("Location") == f"{web_base}{drafts_path_a}"
        )
        ok &= login_redirect_ok
        print(
            f"5. Account A real OIDC login (MFA-satisfied) -> {'OK' if login_redirect_ok else 'FAIL'}"
        )

        status, _, body = session_a.get(f"{api_base}/api/broker/context")
        account_a_id = _json(body)["account_id"]

        # Account B also needs MFA-satisfied from login: it will hold a
        # PUBLISHER (PRIVILEGED_MFA_ROLES) membership on ORG_B below, and
        # this proof has Account B create its own ORG_B draft (item 6) to
        # exercise the cross-Organization-draft non-enumeration check.
        session_b = BrowserSession()
        login_url_b = (
            f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT_B}"
            f"&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session_b.follow_full_login(login_url_b)
        status, _, body = session_b.get(f"{api_base}/api/broker/context")
        account_b_id = _json(body)["account_id"]

        # 2 (setup). Seed ORG_A (Account A, PUBLISHER, ACTIVE) and ORG_B
        # (Account B, PUBLISHER, ACTIVE) -- two disjoint Organizations.
        conn = psycopg.connect(url)
        try:
            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            org_b = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_B_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_a)
            seed_marketplace_organization(conn, org_b)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0061-A"),
                    account_id=AccountId(account_a_id),
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0061-B"),
                    account_id=AccountId(account_b_id),
                    organization_id=org_b.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print("6. seeded ORG_A (Account A, PUBLISHER) and ORG_B (Account B, PUBLISHER) -> OK\n")

        # authenticated Account A reaches the drafts workspace.
        status, headers, body = session_a.get(f"{web_base}{drafts_path_a}")
        page_text = body.decode("utf-8")
        reaches_workspace_ok = (
            status == 200
            and "Start a draft" in page_text
            and "Draft" in page_text
            and "not public" in page_text
            and headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        ok &= reaches_workspace_ok
        print(
            f"7. authenticated PUBLISHER Account A reaches the ORG_A drafts workspace -> "
            f"{'OK' if reaches_workspace_ok else 'FAIL'}\n"
        )

        # 2. ORG_A creates a private draft via the real same-origin form
        # POST -> 303 redirect to the new draft's edit page.
        status, headers, _ = session_a.post_form(f"{web_base}{drafts_path_a}", {}, origin=web_base)
        create_redirect_ok = status == 303 and headers.get("Location", "").startswith(
            f"{drafts_path_a}/"
        )
        ok &= create_redirect_ok
        draft_path = headers.get("Location", "")
        draft_id = draft_path.rsplit("/", 1)[-1]
        print(
            f"8. ORG_A creates a draft via {drafts_path_a} -> {'OK' if create_redirect_ok else 'FAIL'} "
            f"(draft_id={draft_id})"
        )

        status, headers, body = session_a.get(f"{web_base}{draft_path}")
        page_text = body.decode("utf-8")
        edit_page_ok = (
            status == 200
            and "Version: 1" in page_text
            and "not public" in page_text
            and "Publish" not in page_text
            and headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        ok &= edit_page_ok
        print(
            f"9. new draft edit page shows version 1, no Publish action, private/no-store/noindex "
            f"-> {'OK' if edit_page_ok else 'FAIL'}\n"
        )

        # 3. ORG_A saves valid bounded values, including the professional
        # broker_listing_reference.
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {
                "expected_version": "1",
                "broker_listing_reference": "REF-0061-A",
                "physical_boat.boat_name": "Sea Breeze",
                "physical_boat.build_year": "2005",
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "129000.50",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        save_ok = status == 200 and "Saved." in page_text and "Version: 2" in page_text
        ok &= save_ok
        print(f"10. ORG_A saves bounded values -> {'OK' if save_ok else 'FAIL'}")

        # partial draft survives reload/list/read -- via the built Astro
        # surface and via FastAPI directly.
        status, _, body = session_a.get(f"{web_base}{draft_path}")
        page_text = body.decode("utf-8")
        reload_ok = (
            status == 200
            and "Sea Breeze" in page_text
            and "129000.50" in page_text
            and "REF-0061-A" in page_text
            and "Version: 2" in page_text
        )
        ok &= reload_ok

        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        api_record = _json(body)
        api_durable_ok = (
            status == 200
            and api_record["version"] == 2
            and api_record["physical_boat.boat_name"] == "Sea Breeze"
            and api_record["listing_offer.asking_price_amount"] == "129000.50"
            and api_record["broker_listing_reference"] == "REF-0061-A"
            and api_record["owner_organization_id"] == _ORG_A_ID
        )
        ok &= api_durable_ok

        status, _, body = session_a.get(api_drafts_path_a)
        list_body = _json(body)
        list_ok = status == 200 and [d["draft_id"] for d in list_body["drafts"]] == [draft_id]
        ok &= list_ok
        print(
            f"11. reload/reopen (Astro + direct FastAPI read + list) returns exact durable "
            f"PostgreSQL-saved values/version -> {'OK' if (reload_ok and api_durable_ok and list_ok) else 'FAIL'}\n"
        )

        # 4. ORG_A updates with the current version; version increments.
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {"expected_version": "2", "physical_boat.boat_name": "Sea Breeze II"},
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        second_update_ok = (
            status == 200 and "Sea Breeze II" in page_text and "Version: 3" in page_text
        )
        ok &= second_update_ok
        print(
            f"12. update with current version advances version 2 -> 3 -> {'OK' if second_update_ok else 'FAIL'}"
        )

        # 5. stale expected_version returns conflict, does not overwrite.
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {"expected_version": "2", "physical_boat.boat_name": "Stale Overwrite Attempt"},
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        stale_page_ok = status == 200 and "changed elsewhere" in page_text

        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        api_record = _json(body)
        stale_not_overwritten_ok = (
            api_record["version"] == 3 and api_record["physical_boat.boat_name"] == "Sea Breeze II"
        )
        ok &= stale_page_ok and stale_not_overwritten_ok
        print(
            f"13. stale expected_version is visibly rejected and does not overwrite "
            f"(still v3, 'Sea Breeze II') -> {'OK' if (stale_page_ok and stale_not_overwritten_ok) else 'FAIL'}\n"
        )

        # 6. Account B / ORG_B cannot observe or mutate ORG_A's draft.
        # (a) Account B has no ORG_A membership -> org-level non-enumerating 404.
        status_b_org, _, _ = session_b.get(f"{api_drafts_path_a}/{draft_id}")
        step6a_ok = status_b_org == 404
        ok &= step6a_ok

        # ORG_B creates its own draft, then Account A (authorized for
        # ORG_A) requests it under the ORG_A path -- the Organization
        # access boundary succeeds, but the draft itself belongs to a
        # different Organization, so it must be indistinguishable from a
        # wholly unknown draft_id under ORG_A (contract §3.3).
        status, headers, _ = session_b.post_form(
            f"{web_base}/broker/organizations/{_ORG_B_ID}/drafts", {}, origin=web_base
        )
        org_b_draft_id = headers.get("Location", "").rsplit("/", 1)[-1]

        foreign_org_draft = session_a.get(f"{api_drafts_path_a}/{org_b_draft_id}")
        unknown_draft = session_a.get(f"{api_drafts_path_a}/{uuid.uuid4()}")
        step6b_ok = (
            foreign_org_draft[0] == 404
            and unknown_draft[0] == 404
            and foreign_org_draft[2] == unknown_draft[2]
        )
        ok &= step6b_ok

        foreign_write = session_b.put_json(
            f"{api_drafts_path_a}/{draft_id}",
            {"expected_version": 3, "physical_boat.boat_name": "Hijacked"},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        step6c_ok = foreign_write[0] == 404

        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        still_a_ok = _json(body)["physical_boat.boat_name"] == "Sea Breeze II"
        ok &= step6c_ok and still_a_ok
        print(
            f"14. Account B/ORG_B: org-level denial, foreign-Organization-draft and unknown-draft "
            f"share identical 404, foreign write denied, ORG_A's draft unchanged -> "
            f"{'OK' if (step6a_ok and step6b_ok and step6c_ok and still_a_ok) else 'FAIL'}\n"
        )

        # 8. invalid CSRF request fails with no mutation (checked before
        # item 7's revocation, so Account A's authorization is still valid
        # and the CSRF failure is unambiguously the cause).
        status_missing, _, _ = session_a.post_json(api_drafts_path_a, {})
        status_wrong_origin, _, _ = session_a.post_json(
            api_drafts_path_a,
            {},
            extra_headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        csrf_ok = status_missing == 403 and status_wrong_origin == 403

        status, _, body = session_a.get(api_drafts_path_a)
        draft_count_after_csrf_attempts = len(_json(body)["drafts"])
        no_mutation_from_csrf_failure_ok = draft_count_after_csrf_attempts == 1
        ok &= csrf_ok and no_mutation_from_csrf_failure_ok
        print(
            f"15. missing-CSRF-header and cross-origin mutation both fail closed (403), "
            f"no draft created -> {'OK' if (csrf_ok and no_mutation_from_csrf_failure_ok) else 'FAIL'}\n"
        )

        # 9. draft pages/API responses remain private/no-store/noindex.
        status, headers, _ = session_a.get(f"{web_base}{draft_path}")
        page_noindex_ok = (
            headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        status, headers, _ = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        api_noindex_ok = (
            headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        ok &= page_noindex_ok and api_noindex_ok
        print(
            f"16. draft page and API responses are private/no-store/noindex -> "
            f"{'OK' if (page_noindex_ok and api_noindex_ok) else 'FAIL'}\n"
        )

        # 16b (2026-09-20 amendment, contract §9): the built Astro
        # collection surface itself -- not merely the API/persistence
        # layer -- must be able to traverse bounded pages via cursor. A
        # dedicated Organization (ORG_C) with 51 drafts (one more than the
        # 50-row default page size) is seeded directly through the
        # persistence layer for speed; every subsequent read below goes
        # through the real built Astro page.
        from hullq.domain.listing_draft_payload import EMPTY_LISTING_DRAFT_PAYLOAD
        from hullq.persistence.professional_listing_draft import (
            create_professional_listing_draft as _seed_professional_draft,
        )

        conn = psycopg.connect(url)
        try:
            org_c = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_C_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_c)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0061-C"),
                    account_id=AccountId(account_a_id),
                    organization_id=org_c.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()

            seeded_ids: list[str] = []
            base_updated_at = datetime(2026, 1, 1, tzinfo=UTC)
            for i in range(51):
                seeded_record = _seed_professional_draft(
                    conn,
                    owner_organization_id=org_c.id,
                    created_by_account_id=AccountId(account_a_id),
                    broker_listing_reference=None,
                    payload=EMPTY_LISTING_DRAFT_PAYLOAD,
                )
                conn.commit()
                seeded_ids.append(seeded_record.draft_id.value)
                with conn.cursor() as cur:
                    cur.execute(
                        "UPDATE professional_listing_drafts SET updated_at = %s "
                        "WHERE professional_listing_draft_id = %s",
                        (base_updated_at + timedelta(minutes=i), seeded_record.draft_id.value),
                    )
                conn.commit()
        finally:
            conn.close()

        drafts_path_c = f"/broker/organizations/{_ORG_C_ID}/drafts"
        draft_id_pattern = re.compile(rf"{re.escape(drafts_path_c)}/([0-9a-fA-F-]{{36}})")
        next_link_pattern = re.compile(rf'href="{re.escape(drafts_path_c)}\?cursor=([^"]+)"')

        page1_status, _, page1_body = session_a.get(f"{web_base}{drafts_path_c}")
        page1_text = page1_body.decode("utf-8")
        page1_ids = draft_id_pattern.findall(page1_text)
        page1_next_match = next_link_pattern.search(page1_text)
        page1_ok = page1_status == 200 and len(page1_ids) == 50 and page1_next_match is not None

        # The rendered "Next page" cursor must be exactly the same opaque
        # value FastAPI returned -- proving Astro forwards it unmodified
        # (contract: never decoded/reinterpreted in Astro).
        api_status, _, api_body = session_a.get(
            f"{api_base}/api/broker/organizations/{_ORG_C_ID}/drafts"
        )
        api_next_cursor = _json(api_body).get("next_cursor")
        rendered_cursor = page1_next_match.group(1) if page1_next_match else None
        cursor_unmodified_ok = (
            api_status == 200 and rendered_cursor is not None and rendered_cursor == api_next_cursor
        )

        page2_status, _, page2_body = session_a.get(
            f"{web_base}{drafts_path_c}?cursor={rendered_cursor}"
        )
        page2_text = page2_body.decode("utf-8")
        page2_ids = draft_id_pattern.findall(page2_text)
        page2_no_further_next_ok = next_link_pattern.search(page2_text) is None
        page2_ok = page2_status == 200 and len(page2_ids) == 1 and page2_no_further_next_ok

        all_page_ids = page1_ids + page2_ids
        no_duplicates_ok = len(all_page_ids) == len(set(all_page_ids))
        covers_all_seeded_ok = set(all_page_ids) == set(seeded_ids)
        no_cross_org_leak_ok = org_b_draft_id not in all_page_ids

        malformed_status, _, malformed_body = session_a.get(
            f"{web_base}{drafts_path_c}?cursor=not-a-real-cursor!!"
        )
        malformed_cursor_ok = (
            malformed_status == 400 and "Invalid draft list link" in malformed_body.decode("utf-8")
        )

        pagination_ok = (
            page1_ok
            and cursor_unmodified_ok
            and page2_ok
            and no_duplicates_ok
            and covers_all_seeded_ok
            and no_cross_org_leak_ok
            and malformed_cursor_ok
        )
        ok &= pagination_ok
        print(
            f"16b. built Astro collection surface itself traverses two bounded pages via an "
            f"unmodified cursor (50 + 1 drafts, no duplicates, no cross-Organization leakage), "
            f"and a malformed cursor still resolves to the bounded browser invalid-cursor state "
            f"-> {'OK' if pagination_ok else 'FAIL'}\n"
        )

        # 7. membership/role revocation changes the very next authorization
        # result, on the same still-valid signed session (no re-login).
        conn = psycopg.connect(url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-0061-A"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()
        status, _, _ = session_a.get(api_drafts_path_a)
        revocation_ok = status == 404
        ok &= revocation_ok
        print(
            f"17. membership revocation (same still-valid session) denies the next request -> "
            f"{'OK' if revocation_ok else 'FAIL'}\n"
        )

        # 10. no new row is created in any marketplace identity/inventory
        # table, any NativeListing offer revision/fact table, or any table
        # carrying durable public Search-affecting NativeListing state.
        after_non_promotion_counts = _non_promotion_table_counts(url)
        no_non_promotion_rows_ok = before_non_promotion_counts == after_non_promotion_counts
        ok &= no_non_promotion_rows_ok
        print(
            f"18. zero rows created in physical_boats/market_episodes/native_listings, "
            f"NativeListing offer revision/fact tables, or public Search-state tables -> "
            f"{'OK' if no_non_promotion_rows_ok else 'FAIL'} "
            f"({before_non_promotion_counts} -> {after_non_promotion_counts})\n"
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

        print(
            "    items 11/12 (existing owner-direct / professional inventory retained proofs "
            "still pass) are verified separately by also running "
            "scripts/inspect_owner_direct_draft.py and "
            "scripts/inspect_professional_inventory_overview.py -- not duplicated here.\n"
        )

        print(f"PROFESSIONAL LISTING DRAFT WORKSPACE RESULT -> {'PASS' if ok else 'FAIL'}")
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
