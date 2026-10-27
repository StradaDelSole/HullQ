"""SLICE-0091 amendment Finding E proof -- real PostgreSQL + real HTTP +
real built Astro SSR broker editor page.

Independent review on PR #384, Finding E: the backend-only PG/HTTP
roundtrip tests covering `physical_boat.vessel_category` construct a
compliant JSON payload by hand and never exercise the actual broker-facing
`web/src/pages/broker/.../inventory/[native_listing_id]/edit.astro` page,
which (before this amendment) never read a `vessel_category` field from its
own `<form>` at all. Because that page's "Save claim" action always
resubmits the *entire* current claim snapshot (never a partial patch), the
missing field meant an ordinary, unrelated edit through the real page
silently erased an already-saved vessel category. This script drives that
exact real page -- a real same-origin browser `<form method="POST">`
submission, through a real built Astro/Node SSR server and a real FastAPI
backend against a real disposable PostgreSQL 18 schema -- mirroring
`scripts/inspect_professional_inventory_editing.py`'s identical real
browser-style login/session discipline (no Account/membership fact is ever
injected outside the signed session).

Demonstrates:

    1. the real editor's "PhysicalBoat claim" form offers a vessel category
       field and starts with no category assigned
    2. a real browser form POST sets the vessel category (SAIL); the
       authoritative current claim head reflects it
    3. a second, *unrelated* real browser form POST (changing only
       `boat_name`, repeating every other current field exactly as the
       real form would) leaves the vessel category untouched -- the exact
       Finding E regression
    4. a real browser form POST carrying a stale
       `expected_current_revision_id` is rejected (re-rendered with the
       "changed since you loaded the page" outcome, zero mutation)
    5. a real browser form POST carrying a forbidden/invalid vessel
       category value is rejected (re-rendered with the invalid-payload
       outcome, zero mutation)
    6. finishes with the required PASS marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_slice_0091_vessel_category_editor.py
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

_SUBJECT_A = "vessel-category-0091-subject-a"
_ORG_A_ID = "ORG-0091-EDITOR-A"
_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"


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
    support -- mirrors
    `scripts/inspect_professional_inventory_editing.py`'s identical
    `BrowserSession`."""

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


def _edit_page_path(org_id: str, listing_id: str) -> str:
    return f"/broker/organizations/{org_id}/inventory/{listing_id}/edit"


def _form_block(page_text: str, heading: str) -> str:
    """Extract the `<form>...</form>` block immediately following *heading*
    (e.g. `<h2>PhysicalBoat claim</h2>`) -- mirrors
    `scripts/inspect_professional_inventory_editing.py`'s identical
    single-block-extraction technique."""
    idx = page_text.index(heading)
    start = page_text.index("<form", idx)
    end = page_text.index("</form>", start) + len("</form>")
    return page_text[start:end]


def _hidden_field_value(form_html: str, field_name: str) -> str:
    """Extract the `value="..."` of the hidden `<input name="field_name">`
    inside *form_html*, tolerant of Astro's multi-line/attribute-order
    rendering of a JSX-expression `value` attribute."""
    pattern = re.compile(r'name="' + re.escape(field_name) + r'"[\s\S]*?value="([^"]*)"')
    match = pattern.search(form_html)
    assert match is not None, f"hidden field {field_name!r} not found in form block"
    return match.group(1)


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
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0091_editor_api_", suffix=".log")[1])
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
    schema_name = f"hullq_s0091editor_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0091_editor_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from decimal import Decimal

        from hullq.domain.market_identity import (
            MarketEpisode,
            MarketEpisodeId,
            NativeListing,
            NativeListingId,
            PhysicalBoat,
            PhysicalBoatId,
        )
        from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
        from hullq.domain.physical_boat_claims import (
            AssertionKind,
            BuildYearClaim,
            PhysicalBoatClaimRevisionId,
            PhysicalBoatClaimSnapshot,
        )
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
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            write_native_listing_offer_revision,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.persistence.physical_boat_claims import (
            fetch_current_physical_boat_claim,
            list_physical_boat_claim_revisions,
            write_physical_boat_claim_revision,
        )
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0091 AMENDMENT FINDING E: REAL BROKER EDITOR VESSEL CATEGORY\n")

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

        client_id = "hullq-vessel-category-editor-e2e-client"
        client_secret = secrets.token_urlsafe(24)
        preview_secret_b64 = _b64url(os.urandom(32))
        session_secret_b64 = _b64url(os.urandom(32))

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
            print("SLICE-0091 AMENDMENT FINDING E RESULT -> FAIL")
            return 1

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

        conn = psycopg.connect(url)
        try:
            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_a)
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0091-EDITOR-A"),
                account_id=AccountId(account_a_id),
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership_a)
            conn.commit()

            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0091-EDITOR"))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0091-EDITOR"),
                    physical_boat_id=PhysicalBoatId("PB-0091-EDITOR"),
                ),
            )
            create_native_listing(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(
                    id=NativeListingId("NL-0091-EDITOR"),
                    market_episode_id=MarketEpisodeId("ME-0091-EDITOR"),
                ),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0091-EDITOR"),
                revision_id=NativeListingOfferRevisionId("REV-0091-EDITOR"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0091-EDITOR"),
                revision_id=PhysicalBoatClaimRevisionId("CLAIM-0091-EDITOR-1"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2020
                    ),
                ),
            )
            conn.commit()

            db_claim_before = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert db_claim_before is not None
        no_category_yet_ok = db_claim_before.claims.vessel_category is None
        ok &= no_category_yet_ok
        print(
            "5. seeded ORG_A/NL-0091-EDITOR with a claim that has no vessel category yet -> "
            f"{'OK' if no_category_yet_ok else 'FAIL'}\n"
        )

        # 1. Real editor GET: the real "PhysicalBoat claim" form offers a
        # vessel category field and starts unset.
        status, _, body = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0091-EDITOR')}")
        page_text = body.decode("utf-8")
        claim_form = _form_block(page_text, '<h2 id="claim-editor">PhysicalBoat claim</h2>')
        has_category_field_ok = (
            status == 200
            and 'name="vessel_category_kind"' in claim_form
            and 'name="vessel_category_value"' in claim_form
        )
        ok &= has_category_field_ok
        print(
            f"6. the real editor's PhysicalBoat claim form offers a vessel category field -> "
            f"{'OK' if has_category_field_ok else 'FAIL'}"
        )
        claim_revision_id_1 = _hidden_field_value(claim_form, "revision_id")
        claim_expected_1 = _hidden_field_value(claim_form, "expected_current_revision_id")
        assert claim_expected_1 == db_claim_before.revision_id.value

        # 2. Real browser Save claim: set vessel category to SAIL.
        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0091-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": claim_revision_id_1,
                "expected_current_revision_id": claim_expected_1,
                "marketed_brand_claim": "Beneteau",
                "model_designation_claim": "Oceanis 30.1",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2020",
                "vessel_category_kind": "VALUE_ASSERTION",
                "vessel_category_value": "SAIL",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        set_category_saved_ok = status == 200 and "Saved." in page_text
        ok &= set_category_saved_ok

        conn = psycopg.connect(url)
        try:
            claim_after_set = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert claim_after_set is not None
        set_category_ok = (
            claim_after_set.claims.vessel_category is not None
            and claim_after_set.claims.vessel_category.value.value == "SAIL"
        )
        ok &= set_category_ok
        print(
            f"7. a real browser form POST sets the vessel category to SAIL; the authoritative "
            f"current claim head reflects it -> {'OK' if (set_category_saved_ok and set_category_ok) else 'FAIL'}\n"
        )

        # 3. Re-GET (fresh revision ids), then an *unrelated* real browser
        # form POST: only boat_name changes; every other current field
        # (including vessel_category, exactly as the real form currently
        # renders it) is repeated unchanged -- the exact Finding E
        # regression this amendment fixes.
        status, _, body = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0091-EDITOR')}")
        page_text = body.decode("utf-8")
        claim_form = _form_block(page_text, '<h2 id="claim-editor">PhysicalBoat claim</h2>')
        category_prefilled_ok = (
            'value="SAIL"\n' in claim_form or 'value="SAIL"' in claim_form
        ) and "selected" in claim_form
        claim_revision_id_2 = _hidden_field_value(claim_form, "revision_id")
        claim_expected_2 = _hidden_field_value(claim_form, "expected_current_revision_id")
        assert claim_expected_2 == claim_after_set.revision_id.value

        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0091-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": claim_revision_id_2,
                "expected_current_revision_id": claim_expected_2,
                "marketed_brand_claim": "Beneteau",
                "model_designation_claim": "Oceanis 30.1",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2020",
                "vessel_category_kind": "VALUE_ASSERTION",
                "vessel_category_value": "SAIL",
                "boat_name_kind": "VALUE_ASSERTION",
                "boat_name_value": "Serenity",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        unrelated_edit_saved_ok = (
            status == 200 and "Saved." in page_text and "Serenity" in page_text
        )

        conn = psycopg.connect(url)
        try:
            claim_after_unrelated_edit = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert claim_after_unrelated_edit is not None
        category_preserved_ok = (
            claim_after_unrelated_edit.claims.vessel_category is not None
            and claim_after_unrelated_edit.claims.vessel_category.value.value == "SAIL"
            and claim_after_unrelated_edit.claims.boat_name is not None
            and claim_after_unrelated_edit.claims.boat_name.value == "Serenity"
        )
        ok &= unrelated_edit_saved_ok and category_preserved_ok
        print(
            f"8. the real editor pre-fills the vessel category field from the current claim -> "
            f"{'OK' if category_prefilled_ok else 'FAIL'}"
        )
        print(
            f"9. an unrelated real browser form POST (boat_name only) leaves the vessel category "
            f"untouched (still SAIL) -- the exact Finding E regression -> "
            f"{'OK' if (unrelated_edit_saved_ok and category_preserved_ok) else 'FAIL'}\n"
        )

        # 4. Stale revision: replay the original (now stale) expected
        # revision id via a real browser form POST.
        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0091-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": claim_expected_1,
                "marketed_brand_claim": "Beneteau",
                "model_designation_claim": "Oceanis 30.1",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2020",
                "vessel_category_kind": "VALUE_ASSERTION",
                "vessel_category_value": "POWER",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        stale_rendered_ok = status == 200 and "changed since you loaded the page" in page_text
        if not stale_rendered_ok:
            print(f"DEBUG stale status={status}", file=sys.stderr)
            idx = page_text.find("claim-editor")
            print(f"DEBUG stale claim_section={page_text[idx : idx + 800]!r}", file=sys.stderr)

        conn = psycopg.connect(url)
        try:
            claim_after_stale_attempt = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            claim_revision_count = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_stale_attempt is not None
        stale_no_mutation_ok = (
            claim_after_stale_attempt.revision_id.value
            == claim_after_unrelated_edit.revision_id.value
            and claim_revision_count == 3
            and claim_after_stale_attempt.claims.vessel_category is not None
            and claim_after_stale_attempt.claims.vessel_category.value.value == "SAIL"
        )
        ok &= stale_rendered_ok and stale_no_mutation_ok
        print(
            f"10. a real browser form POST carrying a stale expected_current_revision_id is "
            f"rejected (re-rendered, zero mutation; still SAIL, 3 revisions on record) -> "
            f"{'OK' if (stale_rendered_ok and stale_no_mutation_ok) else 'FAIL'}"
        )

        # 5. Forbidden input: an invalid vessel category value.
        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0091-EDITOR')}",
            {
                "action": "save_claim",
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": claim_after_unrelated_edit.revision_id.value,
                "marketed_brand_claim": "Beneteau",
                "model_designation_claim": "Oceanis 30.1",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2020",
                "vessel_category_kind": "VALUE_ASSERTION",
                "vessel_category_value": "GALLEON",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        forbidden_rendered_ok = status == 200 and "couldn&#39;t be saved" in page_text
        if not forbidden_rendered_ok:
            print(f"DEBUG forbidden status={status}", file=sys.stderr)
            idx = page_text.find("claim-editor")
            print(f"DEBUG forbidden claim_section={page_text[idx : idx + 800]!r}", file=sys.stderr)

        conn = psycopg.connect(url)
        try:
            claim_after_forbidden_attempt = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            claim_revision_count_final = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0091-EDITOR"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_forbidden_attempt is not None
        forbidden_no_mutation_ok = (
            claim_after_forbidden_attempt.revision_id.value
            == claim_after_unrelated_edit.revision_id.value
            and claim_revision_count_final == 3
            and claim_after_forbidden_attempt.claims.vessel_category is not None
            and claim_after_forbidden_attempt.claims.vessel_category.value.value == "SAIL"
        )
        ok &= forbidden_rendered_ok and forbidden_no_mutation_ok
        print(
            f"11. a real browser form POST carrying a forbidden vessel category value "
            f'("GALLEON") is rejected (re-rendered, zero mutation; still SAIL, 3 revisions on '
            f"record) -> {'OK' if (forbidden_rendered_ok and forbidden_no_mutation_ok) else 'FAIL'}\n"
        )

        # Ordinary logs must never contain the client/session secret.
        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = all(
            client_secret not in text and session_secret_b64 not in text
            for text in (api_log_text, web_log_text)
        )
        ok &= secrets_clean
        print(
            f"    ordinary API/web logs contain no client/session secret -> "
            f"{'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(f"SLICE-0091 AMENDMENT FINDING E RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
