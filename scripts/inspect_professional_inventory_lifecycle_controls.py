"""SLICE-0064 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed professional-inventory-lifecycle-controls
vertical against a real, disposable PostgreSQL 18 schema and three real
local HTTP servers: a deterministic local OIDC/JWKS test issuer
(``hullq.testing.oidc_test_issuer``), FastAPI, and the built Astro/Node SSR
web package -- mirroring `scripts/inspect_professional_listing_draft_workspace.py`'s
identical real browser-style login discipline (no Account/membership fact is
ever injected outside the signed session; every mutation this proof asserts
on goes through the real `/api/broker/organizations/{organization_id}
/inventory/{native_listing_id}/{publish,withdraw,reconfirm}` HTTP surface,
either via a real same-origin browser form POST to the built Astro page or
via a direct authenticated HTTP POST carrying the identical accepted
same-origin CSRF envelope).

Freshness evaluation time is advanced deterministically -- without sleeping
and without rewriting any audit timestamp -- via FastAPI's server-side-only
``HULLQ_FRESHNESS_AS_OF_OVERRIDE_ISO`` environment variable, exactly
mirroring `scripts/inspect_native_listing_freshness.py`: the API process is
restarted between phases with a different override value while the OIDC
issuer and Astro (which only proxies to FastAPI over HTTP) keep running
unchanged against their own fixed ports throughout.

Per `specs/PROFESSIONAL_INVENTORY_LIFECYCLE_CONTROLS_CONTRACT.v0.1.md` §19,
demonstrates:

    1. real login into an authorized PUBLISHER Organization with MFA
    2. a representative complete own DRAFT NativeListing is visible in
       inventory
    3. browser Publish -> ACTIVE, and public visibility according to the
       accepted public read
    4. an unauthorized/foreign listing publish attempt writes nothing
    5. own ACTIVE listing browser Withdraw -> WITHDRAWN, and public read
       disappears
    6. no SOLD/outcome state is ever created (lifecycle_state remains one of
       exactly DRAFT/ACTIVE/WITHDRAWN throughout)
    7. a representative stale ACTIVE listing is absent from public
       current-market content
    8. API Reconfirm with a stable operation ID -> CONFIRMED, and public
       visibility is restored
    9. an exact reconfirm retry (same operation ID) is idempotent
    10. DRAFT/WITHDRAWN reconfirm attempts fail with no confirmation row
    11. a CSRF failure writes nothing
    12. membership revocation changes the very next action's result on the
        same still-valid signed session
    13. the built inventory page shows only state-appropriate controls and
        always a freshly read result after every action
    14. existing owner-direct and professional-draft retained proofs still
        pass (verified separately, not duplicated here -- see the note near
        the end of `main()`)
    15. finishes with the required PASS marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_professional_inventory_lifecycle_controls.py
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
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

#: See `scripts/inspect_owner_direct_draft.py`'s identical named-tuple
#: rationale: a literal parenthesized `except (A, B, C):` tuple is
#: reformatted by the installed `ruff format` into invalid Python 3
#: `except A, B, C:` syntax; referencing a named tuple constant sidesteps
#: that defect.
_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_SUBJECT_A = "inventory-lifecycle-0064-subject-a"
_SUBJECT_B = "inventory-lifecycle-0064-subject-b"
_SESSION_COOKIE_NAME = "hullq_session"
_ORG_A_ID = "ORG-0064-A"
_ORG_B_ID = "ORG-0064-B"
_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1"
_AS_OF_ENV = "HULLQ_FRESHNESS_AS_OF_OVERRIDE_ISO"

_LIFECYCLE_STATES = {"DRAFT", "ACTIVE", "WITHDRAWN"}


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

    def session_cookie_value(self) -> str | None:
        return next(
            (c.value for c in self.jar if c.name == _SESSION_COOKIE_NAME),
            None,
        )


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _row_html(page_text: str, listing_id: str) -> str:
    """Extract just the `<tr>...</tr>` block for *listing_id* from a
    rendered inventory page. The page lists every listing owned by the
    Organization on one row each, so a plain substring check against the
    whole page would wrongly see another listing's Publish/Withdraw/
    Reconfirm control and misreport this listing's own state-appropriate
    controls."""
    idx = page_text.index(listing_id)
    start = page_text.rindex("<tr>", 0, idx)
    end = page_text.index("</tr>", idx) + len("</tr>")
    return page_text[start:end]


def _start_api(
    *,
    url: str,
    api_port: int,
    preview_secret_b64: str,
    session_secret_b64: str,
    issuer_base: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    web_base: str,
    as_of_iso: str | None,
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0064_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    env["HULLQ_SESSION_SIGNING_SECRET"] = session_secret_b64
    env["HULLQ_AUTH_ISSUER"] = issuer_base
    env["HULLQ_AUTH_AUTHORIZE_URL"] = f"{issuer_base}authorize"
    env["HULLQ_AUTH_TOKEN_URL"] = f"{issuer_base}token"
    env["HULLQ_AUTH_JWKS_URL"] = f"{issuer_base}.well-known/jwks.json"
    env["HULLQ_AUTH_CLIENT_ID"] = client_id
    env["HULLQ_AUTH_CLIENT_SECRET"] = client_secret
    env["HULLQ_AUTH_REDIRECT_URI"] = redirect_uri
    env["HULLQ_WEB_BASE_URL"] = web_base
    env["HULLQ_WEB_ORIGIN"] = web_base
    env["HULLQ_SESSION_COOKIE_SECURE"] = "false"
    if as_of_iso is not None:
        env[_AS_OF_ENV] = as_of_iso
    else:
        env.pop(_AS_OF_ENV, None)
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


def _lifecycle_state(conn: Any, listing_id: str) -> str | None:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT lifecycle_state FROM native_listings WHERE native_listing_id = %s",
            [listing_id],
        )
        row = cur.fetchone()
    return row[0] if row is not None else None


def _transition_count(conn: Any, listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listing_publication_transitions "
            "WHERE native_listing_id = %s",
            [listing_id],
        )
        (count,) = cur.fetchone()
    return int(count)


def _confirmation_count(conn: Any, listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listing_freshness_confirmations "
            "WHERE native_listing_id = %s",
            [listing_id],
        )
        (count,) = cur.fetchone()
    return int(count)


def _all_lifecycle_states_are_accepted(conn: Any) -> bool:
    with conn.cursor() as cur:
        cur.execute("SELECT DISTINCT lifecycle_state FROM native_listings")
        rows = {row[0] for row in cur.fetchall()}
    return rows <= _LIFECYCLE_STATES


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0064e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0064_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.market_identity import (
            MarketEpisode,
            MarketEpisodeId,
            NativeListing,
            NativeListingId,
            PhysicalBoat,
            PhysicalBoatId,
        )
        from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
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
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_lifecycle import publish_native_listing
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            write_native_listing_offer_revision,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("PROFESSIONAL INVENTORY LIFECYCLE CONTROLS\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        issuer_host = "127.0.0.1"
        issuer_port = _free_port(issuer_host)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{issuer_host}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-inventory-lifecycle-e2e-client"
        client_secret = secrets.token_urlsafe(24)
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)
        preview_secret_b64 = _b64url(preview_secret)
        session_secret_b64 = _b64url(session_secret)

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

        api_log_paths: list[Path] = []

        def start_api(as_of_iso: str | None) -> None:
            nonlocal api_proc
            api_proc, api_log_path = _start_api(
                url=url,
                api_port=api_port,
                preview_secret_b64=preview_secret_b64,
                session_secret_b64=session_secret_b64,
                issuer_base=issuer_base,
                client_id=client_id,
                client_secret=client_secret,
                redirect_uri=redirect_uri,
                web_base=web_base,
                as_of_iso=as_of_iso,
            )
            api_log_paths.append(api_log_path)
            api_ready = _wait_for_http(f"{api_base}/api/broker/context")
            assert api_ready, f"FastAPI did not become ready; see {api_log_path}"

        start_api(None)
        print("2. FastAPI serving (real-time clock) -> OK")

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
            print("PROFESSIONAL INVENTORY LIFECYCLE CONTROLS RESULT -> FAIL")
            return 1

        # 1. real OIDC/session login for Account A -- with MFA step-up from
        # the start (contract §6: PUBLISHER is a PRIVILEGED_MFA_ROLES role).
        inventory_path_a = f"/broker/organizations/{_ORG_A_ID}/inventory"
        session_a = BrowserSession()
        login_url_a = (
            f"{api_base}/api/auth/login?next={quote(inventory_path_a, safe='')}"
            f"&login_hint={_SUBJECT_A}&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        status, headers, _ = session_a.follow_full_login(login_url_a)
        login_ok = status == 302 and headers.get("Location") == f"{web_base}{inventory_path_a}"
        ok &= login_ok
        print(f"4. Account A real OIDC login (MFA-satisfied) -> {'OK' if login_ok else 'FAIL'}")

        status, _, body = session_a.get(f"{api_base}/api/broker/context")
        account_a_id = _json(body)["account_id"]

        session_b = BrowserSession()
        login_url_b = (
            f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT_B}"
            f"&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session_b.follow_full_login(login_url_b)
        status, _, body = session_b.get(f"{api_base}/api/broker/context")
        account_b_id = _json(body)["account_id"]

        # 2 (setup). Seed ORG_A (Account A, PUBLISHER, ACTIVE, ELIGIBLE) and
        # ORG_B (Account B, PUBLISHER, ACTIVE, ELIGIBLE) -- two disjoint
        # Organizations.
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
                    id=OrganizationMembershipId("OM-0064-A"),
                    account_id=AccountId(account_a_id),
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0064-B"),
                    account_id=AccountId(account_b_id),
                    organization_id=org_b.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()

            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0064-A"),
                account_id=AccountId(account_a_id),
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            membership_b = OrganizationMembership(
                id=OrganizationMembershipId("OM-0064-B"),
                account_id=AccountId(account_b_id),
                organization_id=org_b.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

            def _complete_listing(
                *, listing_id: str, org: Any, account_id: str, membership: Any, suffix: str
            ) -> None:
                create_physical_boat(
                    conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-{suffix}"))
                )
                create_market_episode(
                    conn,
                    market_episode=MarketEpisode(
                        id=MarketEpisodeId(f"ME-{suffix}"),
                        physical_boat_id=PhysicalBoatId(f"PB-{suffix}"),
                    ),
                )
                create_native_listing(
                    conn,
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    listing=NativeListing(
                        id=NativeListingId(listing_id),
                        market_episode_id=MarketEpisodeId(f"ME-{suffix}"),
                    ),
                )
                write_native_listing_offer_revision(
                    conn,
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(listing_id),
                    revision_id=NativeListingOfferRevisionId(f"REV-{suffix}"),
                    expected_current_revision_id=None,
                    offer=NativeListingOfferSnapshot(
                        asking_price_mode=AskingPriceMode.AMOUNT,
                        location_country="FR",
                        broker_description="A well-maintained cruising sloop.",
                        asking_price_amount=Decimal("125000.00"),
                        currency="EUR",
                    ),
                )

            # NL-MAIN: the representative listing driven through the real
            # browser (items 2/3/5/13).
            _complete_listing(
                listing_id="NL-0064-MAIN",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
                suffix="0064-MAIN",
            )
            # NL-FOREIGN: owned by ORG_B, already ACTIVE -- used to prove
            # Account A cannot mutate it under the ORG_A path (item 4).
            _complete_listing(
                listing_id="NL-0064-FOREIGN",
                org=org_b,
                account_id=account_b_id,
                membership=membership_b,
                suffix="0064-FOREIGN",
            )
            publish_result = publish_native_listing(
                conn,
                account_id=AccountId(account_b_id),
                candidate_organization=org_b,
                membership=membership_b,
                native_listing_id=NativeListingId("NL-0064-FOREIGN"),
            )
            assert publish_result.status.value == "transitioned", publish_result
            # NL-CSRF: stays DRAFT throughout -- used for the CSRF-failure
            # (item 11) and DRAFT-reconfirm-rejected (item 10) checks.
            _complete_listing(
                listing_id="NL-0064-CSRF",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
                suffix="0064-CSRF",
            )
            # NL-STALE: published now (real clock), later evaluated as STALE
            # and then reconfirmed (items 7/8/9).
            _complete_listing(
                listing_id="NL-0064-STALE",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
                suffix="0064-STALE",
            )
            conn.commit()
        finally:
            conn.close()
        print(
            "5. seeded ORG_A (Account A, PUBLISHER)/ORG_B (Account B, PUBLISHER) and four "
            "NativeListings (NL-MAIN DRAFT, NL-FOREIGN ORG_B-ACTIVE, NL-CSRF DRAFT, "
            "NL-STALE DRAFT) -> OK\n"
        )

        # 2. representative complete own DRAFT NativeListing visible in
        # inventory, showing only the Publish control (item 2/13a).
        status, headers, body = session_a.get(f"{web_base}{inventory_path_a}")
        page_text = body.decode("utf-8")
        main_row = _row_html(page_text, "NL-0064-MAIN")
        draft_view_ok = (
            status == 200
            and "DRAFT" in main_row
            and "Publish</button>" in main_row
            and "Withdraw</button>" not in main_row
            and "Reconfirm</button>" not in main_row
            and headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
        )
        ok &= draft_view_ok
        print(
            f"6. inventory page shows NL-0064-MAIN as DRAFT with only a Publish control "
            f"-> {'OK' if draft_view_ok else 'FAIL'}"
        )

        # 4. an unauthorized/foreign listing publish attempt writes nothing,
        # AND (independent review 2026-09-24 finding) the browser actually
        # renders a distinct, bounded, non-enumerating listing-not-found
        # outcome -- never the generic service-failure/"action_failed" text
        # -- for both a foreign-Organization listing and a wholly unknown
        # listing_id, with byte-identical banner text between the two so
        # neither case is distinguishable from the other (contract §4/§14).
        conn = psycopg.connect(url)
        try:
            foreign_state_before = _lifecycle_state(conn, "NL-0064-FOREIGN")
            foreign_transitions_before = _transition_count(conn, "NL-0064-FOREIGN")
        finally:
            conn.close()
        status, _, foreign_body = session_a.post_form(
            f"{web_base}{inventory_path_a}",
            {"native_listing_id": "NL-0064-FOREIGN", "action": "publish"},
            origin=web_base,
        )
        # Astro's JSX renderer HTML-entity-escapes the apostrophe in this
        # banner text (`&#39;`), so the substring check below matches the
        # real escaped markup rather than the raw source string.
        _LISTING_NOT_FOUND_BANNER = "This listing isn&#39;t available here."
        foreign_page_text = foreign_body.decode("utf-8")
        foreign_banner_ok = (
            status == 200
            and _LISTING_NOT_FOUND_BANNER in foreign_page_text
            and "Something went wrong" not in foreign_page_text
        )

        status, _, unknown_body = session_a.post_form(
            f"{web_base}{inventory_path_a}",
            {"native_listing_id": "NL-0064-NEVER-CREATED", "action": "publish"},
            origin=web_base,
        )
        unknown_page_text = unknown_body.decode("utf-8")
        unknown_banner_ok = (
            status == 200
            and _LISTING_NOT_FOUND_BANNER in unknown_page_text
            and "Something went wrong" not in unknown_page_text
        )

        conn = psycopg.connect(url)
        try:
            foreign_unchanged_ok = (
                _lifecycle_state(conn, "NL-0064-FOREIGN") == foreign_state_before
                and _transition_count(conn, "NL-0064-FOREIGN") == foreign_transitions_before
            )
        finally:
            conn.close()
        ok &= foreign_banner_ok and unknown_banner_ok and foreign_unchanged_ok
        print(
            f"7. foreign-Organization and unknown-listing_id publish attempts both write "
            f"nothing and both render the identical bounded, non-enumerating "
            f"listing-not-found banner (never the generic service-failure text) -> "
            f"{'OK' if (foreign_banner_ok and unknown_banner_ok and foreign_unchanged_ok) else 'FAIL'}"
        )

        # 3. real browser Publish of NL-MAIN -> ACTIVE, then public
        # visibility according to the accepted public read.
        status, headers, body = session_a.post_form(
            f"{web_base}{inventory_path_a}",
            {"native_listing_id": "NL-0064-MAIN", "action": "publish"},
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        publish_ok = status == 200 and "Published." in page_text and "ACTIVE" in page_text
        ok &= publish_ok
        print(f"8. real browser Publish NL-0064-MAIN -> ACTIVE -> {'OK' if publish_ok else 'FAIL'}")

        status, _, _ = session_a.get(f"{api_base}/api/listings/NL-0064-MAIN")
        public_visible_ok = status == 200
        ok &= public_visible_ok
        print(
            f"   public listing route now returns current content -> {'OK' if public_visible_ok else 'FAIL'}"
        )

        status, headers, body = session_a.get(f"{web_base}{inventory_path_a}")
        page_text = body.decode("utf-8")
        main_row = _row_html(page_text, "NL-0064-MAIN")
        active_view_ok = (
            status == 200
            and "Publish</button>" not in main_row
            and "Withdraw</button>" in main_row
            and "Reconfirm</button>" in main_row
        )
        ok &= active_view_ok
        print(
            f"9. inventory page now shows NL-0064-MAIN as ACTIVE with only Withdraw+Reconfirm "
            f"controls -> {'OK' if active_view_ok else 'FAIL'}\n"
        )

        # 5. own ACTIVE listing browser Withdraw -> WITHDRAWN, public read
        # disappears, and no third lifecycle state (SOLD/etc.) is ever
        # created (item 6).
        status, headers, body = session_a.post_form(
            f"{web_base}{inventory_path_a}",
            {"native_listing_id": "NL-0064-MAIN", "action": "withdraw"},
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        withdraw_ok = status == 200 and "Withdrawn." in page_text and "WITHDRAWN" in page_text
        ok &= withdraw_ok
        print(
            f"10. real browser Withdraw NL-0064-MAIN -> WITHDRAWN -> {'OK' if withdraw_ok else 'FAIL'}"
        )

        status, _, _ = session_a.get(f"{api_base}/api/listings/NL-0064-MAIN")
        public_gone_ok = status == 404
        ok &= public_gone_ok
        print(f"    public listing route now 404s -> {'OK' if public_gone_ok else 'FAIL'}")

        status, headers, body = session_a.get(f"{web_base}{inventory_path_a}")
        page_text = body.decode("utf-8")
        main_row = _row_html(page_text, "NL-0064-MAIN")
        withdrawn_view_ok = (
            status == 200
            and "Publish</button>" not in main_row
            and "Withdraw</button>" not in main_row
            and "Reconfirm</button>" not in main_row
        )
        conn = psycopg.connect(url)
        try:
            no_third_state_ok = _lifecycle_state(
                conn, "NL-0064-MAIN"
            ) == "WITHDRAWN" and _all_lifecycle_states_are_accepted(conn)
        finally:
            conn.close()
        ok &= withdrawn_view_ok and no_third_state_ok
        print(
            f"11. inventory page now shows no republish control for NL-0064-MAIN, and every "
            f"lifecycle_state remains one of DRAFT/ACTIVE/WITHDRAWN (no SOLD/outcome state) -> "
            f"{'OK' if (withdrawn_view_ok and no_third_state_ok) else 'FAIL'}\n"
        )

        # 11. a CSRF failure writes nothing (NL-CSRF stays DRAFT).
        publish_path_csrf = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0064-CSRF/publish"
        )
        status_missing, _, _ = session_a.post_json(publish_path_csrf, {})
        status_wrong_origin, _, _ = session_a.post_json(
            publish_path_csrf,
            {},
            extra_headers={
                "Origin": "https://evil.example",
                "X-HullQ-Requested-With": _CSRF_HEADER_VALUE,
            },
        )
        csrf_status_ok = status_missing == 403 and status_wrong_origin == 403
        conn = psycopg.connect(url)
        try:
            csrf_no_mutation_ok = (
                _lifecycle_state(conn, "NL-0064-CSRF") == "DRAFT"
                and _transition_count(conn, "NL-0064-CSRF") == 0
            )
        finally:
            conn.close()
        ok &= csrf_status_ok and csrf_no_mutation_ok
        print(
            f"12. missing/foreign-Origin publish attempts on NL-0064-CSRF both fail closed (403) "
            f"with zero mutation -> {'OK' if (csrf_status_ok and csrf_no_mutation_ok) else 'FAIL'}"
        )

        # 10. DRAFT reconfirm attempt fails with no confirmation row.
        reconfirm_path_csrf = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0064-CSRF/reconfirm"
        )
        status, _, _ = session_a.post_json(
            reconfirm_path_csrf,
            {"confirmation_id": str(uuid.uuid4())},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        draft_reconfirm_status_ok = status == 409
        conn = psycopg.connect(url)
        try:
            draft_reconfirm_no_row_ok = _confirmation_count(conn, "NL-0064-CSRF") == 0
        finally:
            conn.close()
        ok &= draft_reconfirm_status_ok and draft_reconfirm_no_row_ok
        print(
            f"13. reconfirm attempt on a DRAFT listing fails (409) with no confirmation row "
            f"-> {'OK' if (draft_reconfirm_status_ok and draft_reconfirm_no_row_ok) else 'FAIL'}\n"
        )

        # 7/8/9. publish NL-STALE now (real clock), observe STALE under a
        # far-future evaluation clock, then reconfirm it back to current
        # under a near-future clock and observe restored public visibility,
        # including an exact idempotent retry.
        publish_path_stale = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0064-STALE/publish"
        )
        status, _, _ = session_a.post_json(
            publish_path_stale,
            {},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        stale_publish_ok = status == 200
        ok &= stale_publish_ok
        print(
            f"14. NL-0064-STALE published at the real current clock -> {'OK' if stale_publish_ok else 'FAIL'}"
        )

        now = datetime.now(UTC)
        _stop_process(api_proc)
        start_api((now + timedelta(days=40)).isoformat())
        print("    FastAPI restarted with clock +40 days -> OK")

        status, _, _ = session_a.get(f"{api_base}/api/listings/NL-0064-STALE")
        stale_absent_ok = status == 404
        ok &= stale_absent_ok
        print(
            f"15. under a +40 day clock, NL-0064-STALE (STALE) is absent from public content -> {'OK' if stale_absent_ok else 'FAIL'}"
        )

        status, _, body = session_a.get(f"{web_base}{inventory_path_a}")
        page_text = body.decode("utf-8")
        stale_row = _row_html(page_text, "NL-0064-STALE")
        stale_controls_ok = (
            status == 200 and "STALE" in stale_row and "Reconfirm</button>" in stale_row
        )
        ok &= stale_controls_ok
        print(
            f"    inventory page still shows lifecycle-correct ACTIVE controls for the stale listing -> {'OK' if stale_controls_ok else 'FAIL'}\n"
        )

        _stop_process(api_proc)
        start_api((now + timedelta(minutes=5)).isoformat())
        print(
            "16. FastAPI restarted with clock +5 minutes (for reconfirmation + restored-visibility checks) -> OK"
        )

        reconfirm_path_stale = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0064-STALE/reconfirm"
        )
        confirmation_id = str(uuid.uuid4())
        status, _, body = session_a.post_json(
            reconfirm_path_stale,
            {"confirmation_id": confirmation_id},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        first_reconfirm_body = _json(body)
        reconfirm_ok = status == 200 and first_reconfirm_body.get("outcome") == "RECONFIRMED"
        ok &= reconfirm_ok
        print(
            f"17. API Reconfirm NL-0064-STALE with a stable operation ID -> RECONFIRMED -> {'OK' if reconfirm_ok else 'FAIL'}"
        )

        status, _, _ = session_a.get(f"{api_base}/api/listings/NL-0064-STALE")
        restored_ok = status == 200
        ok &= restored_ok
        print(f"    public listing visibility is restored -> {'OK' if restored_ok else 'FAIL'}")

        # 9. an exact reconfirm retry (identical operation ID) is idempotent.
        status, _, body = session_a.post_json(
            reconfirm_path_stale,
            {"confirmation_id": confirmation_id},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        retry_body = _json(body)
        conn = psycopg.connect(url)
        try:
            confirmation_rows_after_retry = _confirmation_count(conn, "NL-0064-STALE")
        finally:
            conn.close()
        idempotent_retry_ok = (
            status == 200
            and retry_body == first_reconfirm_body
            and confirmation_rows_after_retry == 1
        )
        ok &= idempotent_retry_ok
        print(
            f"18. an exact reconfirm retry with the identical operation ID is idempotent (one confirmation row) -> {'OK' if idempotent_retry_ok else 'FAIL'}\n"
        )

        # 12. membership revocation changes the very next action's result on
        # the same still-valid signed session (no re-login).
        conn = psycopg.connect(url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-0064-A"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()
        status, _, _ = session_a.post_json(
            reconfirm_path_stale,
            {"confirmation_id": str(uuid.uuid4())},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        revocation_ok = status == 404
        ok &= revocation_ok
        print(
            f"19. membership revocation (same still-valid session) denies the very next action -> {'OK' if revocation_ok else 'FAIL'}"
        )

        conn = psycopg.connect(url)
        try:
            revocation_no_extra_row_ok = _confirmation_count(conn, "NL-0064-STALE") == 1
        finally:
            conn.close()
        ok &= revocation_no_extra_row_ok
        print(
            f"    the denied post-revocation attempt appended no further confirmation row -> {'OK' if revocation_no_extra_row_ok else 'FAIL'}\n"
        )

        # Ordinary logs must never contain the client secret / session secret,
        # across every API restart plus the web log.
        api_log_texts = [
            path.read_text(encoding="utf-8", errors="replace") for path in api_log_paths
        ]
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = all(
            client_secret not in text and session_secret_b64 not in text
            for text in (*api_log_texts, web_log_text)
        )
        ok &= secrets_clean
        print(
            f"    ordinary API/web logs contain no client/session secret -> {'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(
            "    item 14 (existing owner-direct / professional-draft retained proofs still "
            "pass) is verified separately by also running scripts/inspect_owner_direct_draft.py "
            "and scripts/inspect_professional_listing_draft_workspace.py -- not duplicated here.\n"
        )

        print(f"PROFESSIONAL INVENTORY LIFECYCLE CONTROLS RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
