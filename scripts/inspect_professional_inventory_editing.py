"""SLICE-0072 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the `specs/PROFESSIONAL_INVENTORY_EDITING_CONTRACT.v0.1.md` §16
retained vertical against a real, disposable PostgreSQL 18 schema and three
real local HTTP servers: a deterministic local OIDC/JWKS test issuer
(``hullq.testing.oidc_test_issuer``), FastAPI, and the built Astro/Node SSR
web package -- mirrors `scripts/inspect_professional_inventory_lifecycle_controls.py`'s
identical real browser-style login discipline (no Account/membership fact is
ever injected outside the signed session).

Per contract §16, demonstrates:

    1. authorized broker opens existing promoted listing editor
    2. current offer/claim fields and revision identities come from
       authoritative current heads
    3. broker changes asking price and saves a new immutable offer revision
       (real same-origin browser form POST)
    4. public listing reflects the new current offer without lifecycle
       rewrite
    5. broker changes a concrete-yacht claim (keel_configuration) and saves
       a new immutable claim revision (real same-origin browser form POST)
    6. Search/public truth reads the new current claim through the existing
       accepted paths
    7. stale offer mutation is rejected (409) without overwrite
    8. stale claim mutation is rejected (409) without overwrite
    9. foreign Organization access remains non-enumerating (404, zero
       mutation)
    10. DRAFT / ACTIVE / WITHDRAWN lifecycle remains mechanically separate
        under editing (no implicit publish/republish)
    11. an ACTIVE edit that would violate a hard candidate-head
        current-public invariant rolls back atomically (422, zero mutation)
    12. media state is unchanged by every offer/claim edit above
    13. Lead state is unchanged by every offer/claim edit above
    14. the technical native Search criterion count remains exactly 2
        (draft_max, keel_configuration -- no third criterion is accepted)
    15. finishes with the required PASS marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_professional_inventory_editing.py
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
from datetime import UTC, datetime
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

_SUBJECT_A = "inventory-editing-0072-subject-a"
_SESSION_COOKIE_NAME = "hullq_session"
_ORG_A_ID = "ORG-0072-A"
_ORG_B_ID = "ORG-0072-B"
_ACCOUNT_B_ID = "ACC-0072-B"
_CSRF_HEADER_VALUE = "professional-inventory-editing-v1"

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
    support -- mirrors
    `scripts/inspect_professional_inventory_lifecycle_controls.py`'s
    identical `BrowserSession`."""

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


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _csrf_headers(web_base: str) -> dict[str, str]:
    return {"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _edit_page_path(org_id: str, listing_id: str) -> str:
    return f"/broker/organizations/{org_id}/inventory/{listing_id}/edit"


def _form_block(page_text: str, heading: str) -> str:
    """Extract the `<form>...</form>` block immediately following *heading*
    (e.g. `<h2>Offer</h2>`) -- mirrors
    `inspect_professional_inventory_lifecycle_controls.py`'s `_row_html`'s
    identical single-block-extraction technique, applied to a named form
    section rather than a table row."""
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
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0072_api_", suffix=".log")[1])
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
    schema_name = f"hullq_s0072e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0072_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from _publication_readiness_fixture import attach_d22_minimum_cover_image

        from hullq.domain.buyer_lead import SubmissionOperationId
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
            KeelConfiguration,
            KeelConfigurationClaim,
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
        from hullq.persistence.buyer_lead import create_buyer_lead, fetch_buyer_lead
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.media_gallery import fetch_gallery_state
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_lifecycle import (
            publish_native_listing,
            withdraw_native_listing,
        )
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            fetch_current_native_listing_offer,
            list_native_listing_offer_revisions,
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
        print("PROFESSIONAL INVENTORY EDITING\n")

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

        client_id = "hullq-inventory-editing-e2e-client"
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
            print("PROFESSIONAL INVENTORY EDITING RESULT -> FAIL")
            return 1

        # Real OIDC/session login for Account A, MFA-satisfied from the
        # start (PUBLISHER is a PRIVILEGED_MFA_ROLES role).
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

        # Seed ORG_A (Account A, PUBLISHER)/ORG_B (Account B, PUBLISHER) and
        # five representative NativeListings.
        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [_ACCOUNT_B_ID],
                )
            conn.commit()

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
                    id=OrganizationMembershipId("OM-0072-A"),
                    account_id=AccountId(account_a_id),
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0072-B"),
                    account_id=AccountId(_ACCOUNT_B_ID),
                    organization_id=org_b.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()

            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-0072-A"),
                account_id=AccountId(account_a_id),
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            membership_b = OrganizationMembership(
                id=OrganizationMembershipId("OM-0072-B"),
                account_id=AccountId(_ACCOUNT_B_ID),
                organization_id=org_b.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

            def _complete_listing(
                *,
                listing_id: str,
                physical_boat_id: str,
                market_episode_id: str,
                org: Any,
                account_id: str,
                membership: Any,
                keel: KeelConfiguration | None,
            ) -> None:
                create_physical_boat(
                    conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id))
                )
                create_market_episode(
                    conn,
                    market_episode=MarketEpisode(
                        id=MarketEpisodeId(market_episode_id),
                        physical_boat_id=PhysicalBoatId(physical_boat_id),
                    ),
                )
                create_native_listing(
                    conn,
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    listing=NativeListing(
                        id=NativeListingId(listing_id),
                        market_episode_id=MarketEpisodeId(market_episode_id),
                    ),
                )
                write_native_listing_offer_revision(
                    conn,
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(listing_id),
                    revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
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
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(listing_id),
                    revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
                    expected_current_revision_id=None,
                    claims=PhysicalBoatClaimSnapshot(
                        marketed_brand_claim="Beneteau",
                        model_designation_claim="Oceanis 30.1",
                        build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, 2020),
                        keel_configuration=(
                            KeelConfigurationClaim(AssertionKind.VALUE_ASSERTION, keel)
                            if keel is not None
                            else None
                        ),
                    ),
                )

            def _publish(*, listing_id: str, org: Any, account_id: str, membership: Any) -> None:
                attach_d22_minimum_cover_image(
                    conn, listing_id=listing_id, account=AccountId(account_id), org=org
                )
                conn.commit()  # release the implicit transaction before the top-level-owning publish
                result = publish_native_listing(
                    conn,
                    account_id=AccountId(account_id),
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(listing_id),
                )
                assert result.status.value == "transitioned", result

            # NL-MAIN: the representative listing driven through the real
            # browser for items 1-6/12/13 -- published ACTIVE, keel FIN.
            _complete_listing(
                listing_id="NL-0072-MAIN",
                physical_boat_id="PB-0072-MAIN",
                market_episode_id="ME-0072-MAIN",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
                keel=KeelConfiguration.FIN,
            )
            _publish(
                listing_id="NL-0072-MAIN", org=org_a, account_id=account_a_id, membership=membership_a
            )

            # NL-FOREIGN: owned by ORG_B, ACTIVE -- proves Account A cannot
            # read/edit it under the ORG_A path (item 9).
            _complete_listing(
                listing_id="NL-0072-FOREIGN",
                physical_boat_id="PB-0072-FOREIGN",
                market_episode_id="ME-0072-FOREIGN",
                org=org_b,
                account_id=_ACCOUNT_B_ID,
                membership=membership_b,
                keel=None,
            )
            _publish(
                listing_id="NL-0072-FOREIGN",
                org=org_b,
                account_id=_ACCOUNT_B_ID,
                membership=membership_b,
            )

            # NL-DRAFT: owned by ORG_A, stays DRAFT throughout -- proves an
            # offer edit never implicitly publishes it (item 10).
            _complete_listing(
                listing_id="NL-0072-DRAFT",
                physical_boat_id="PB-0072-DRAFT",
                market_episode_id="ME-0072-DRAFT",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
                keel=None,
            )

            # NL-WITHDRAWN: owned by ORG_A, published then withdrawn --
            # proves an offer edit never implicitly republishes it (item 10).
            _complete_listing(
                listing_id="NL-0072-WITHDRAWN",
                physical_boat_id="PB-0072-WITHDRAWN",
                market_episode_id="ME-0072-WITHDRAWN",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
                keel=None,
            )
            _publish(
                listing_id="NL-0072-WITHDRAWN",
                org=org_a,
                account_id=account_a_id,
                membership=membership_a,
            )
            conn.commit()
            withdraw_result = withdraw_native_listing(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0072-WITHDRAWN"),
            )
            assert withdraw_result.status.value == "transitioned", withdraw_result

            # NL-INVARIANT: owned by ORG_A, offer only (no MarketEpisode
            # link), lifecycle forced directly to ACTIVE -- a defensive
            # chain-incomplete + ACTIVE combination unreachable through any
            # normal flow, used to prove the atomic ACTIVE-invariant
            # rollback (item 11).
            create_native_listing(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(id=NativeListingId("NL-0072-INVARIANT")),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=AccountId(account_a_id),
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0072-INVARIANT"),
                revision_id=NativeListingOfferRevisionId("REV-NL-0072-INVARIANT"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    ["NL-0072-INVARIANT"],
                )
            conn.commit()

            # Baseline Lead against NL-MAIN, created while it is genuinely
            # D29-ELIGIBLE -- the fixed point items 12/13 compare against.
            lead_result = create_buyer_lead(
                conn,
                submission_operation_id=SubmissionOperationId("OP-0072-LEAD-1"),
                native_listing_id=NativeListingId("NL-0072-MAIN"),
                account_id=None,
                buyer_name="Jamie Buyer",
                buyer_email="jamie@example.test",
                buyer_message="Interested in this boat, please contact me.",
                as_of=datetime.now(UTC),
            )
            assert lead_result.status.value == "created", lead_result
            lead_id = lead_result.lead_id
            assert lead_id is not None
        finally:
            conn.close()
        print(
            "5. seeded ORG_A (Account A, PUBLISHER)/ORG_B (Account B, PUBLISHER); "
            "NL-MAIN (ORG_A, ACTIVE, keel FIN), NL-FOREIGN (ORG_B, ACTIVE), "
            "NL-DRAFT (ORG_A, DRAFT), NL-WITHDRAWN (ORG_A, WITHDRAWN), "
            "NL-INVARIANT (ORG_A, ACTIVE, broken chain); one Lead on NL-MAIN -> OK\n"
        )

        # Baseline media/Lead snapshots for NL-MAIN (items 12/13), taken
        # once, before any offer/claim edit below.
        conn = psycopg.connect(url)
        try:
            gallery_before = fetch_gallery_state(conn, NativeListingId("NL-0072-MAIN"))
            gallery_snapshot_before = (
                gallery_before.gallery_version,
                gallery_before.cover_placement_id,
                tuple(p.media_placement_id for p in gallery_before.placements),
            )
            lead_before = fetch_buyer_lead(conn, lead_id)
            assert lead_before is not None
        finally:
            conn.close()

        # 1/2. Account A opens NL-0072-MAIN's editor through the real
        # browser; the current offer/claim revision identities rendered
        # there are compared against the authoritative current heads read
        # directly from PostgreSQL.
        status, headers, body = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0072-MAIN')}")
        page_text = body.decode("utf-8")
        offer_form = _form_block(page_text, "<h2>Offer</h2>")
        claim_form = _form_block(page_text, "<h2>PhysicalBoat claim</h2>")
        page_offer_expected = _hidden_field_value(offer_form, "expected_current_revision_id")
        page_claim_expected = _hidden_field_value(claim_form, "expected_current_revision_id")

        conn = psycopg.connect(url)
        try:
            db_offer_before = fetch_current_native_listing_offer(conn, NativeListingId("NL-0072-MAIN"))
            db_claim_before = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0072-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
            )
        finally:
            conn.close()
        assert db_offer_before is not None
        assert db_claim_before is not None

        open_editor_ok = (
            status == 200
            and headers.get("Cache-Control") == "private, no-store"
            and headers.get("X-Robots-Tag") == "noindex"
            and "125000.00" in offer_form
            and page_offer_expected == db_offer_before.revision_id.value
            and page_claim_expected == db_claim_before.revision_id.value
        )
        ok &= open_editor_ok
        print(
            f"6. Account A opens the real editor for NL-0072-MAIN; rendered offer/claim revision "
            f"identities exactly match the authoritative current heads read from PostgreSQL -> "
            f"{'OK' if open_editor_ok else 'FAIL'}"
        )

        # public listing price/claim before the edits (items 4/6 baseline).
        status, _, body = session_a.get(f"{api_base}/api/listings/NL-0072-MAIN")
        public_listing_before = _json(body)
        public_price_before = public_listing_before["asking_price_amount"]
        public_keel_before = public_listing_before["physical_boat_claims"]["keel_configuration"][
            "value"
        ]

        # 3. Real browser Save offer: change the asking price.
        offer_revision_id_1 = _hidden_field_value(offer_form, "revision_id")
        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0072-MAIN')}",
            {
                "action": "save_offer",
                "revision_id": offer_revision_id_1,
                "expected_current_revision_id": page_offer_expected,
                "asking_price_mode": "AMOUNT",
                "asking_price_amount": "139000.00",
                "currency": "EUR",
                "location_country": "FR",
                "broker_description": "A well-maintained cruising sloop.",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        offer_save_ok = status == 200 and "Saved." in page_text and "139000.00" in page_text
        ok &= offer_save_ok
        print(
            f"7. real browser Save offer on NL-0072-MAIN changes the asking price -> "
            f"{'OK' if offer_save_ok else 'FAIL'}"
        )

        conn = psycopg.connect(url)
        try:
            offer_after_price_edit = fetch_current_native_listing_offer(
                conn, NativeListingId("NL-0072-MAIN")
            )
            offer_revision_count_after_price_edit = len(
                list_native_listing_offer_revisions(conn, NativeListingId("NL-0072-MAIN"))
            )
            lifecycle_after_price_edit = _lifecycle_state(conn, "NL-0072-MAIN")
            transitions_after_price_edit = _transition_count(conn, "NL-0072-MAIN")
        finally:
            conn.close()
        assert offer_after_price_edit is not None
        new_revision_immutable_ok = (
            offer_after_price_edit.revision_id.value != db_offer_before.revision_id.value
            and offer_revision_count_after_price_edit == 2
        )
        ok &= new_revision_immutable_ok
        print(
            f"   a new immutable offer revision was created (2 revisions on record, prior head "
            f"retained) -> {'OK' if new_revision_immutable_ok else 'FAIL'}"
        )

        # 4. Public listing reflects the new current offer, with zero
        # lifecycle rewrite.
        status, _, body = session_a.get(f"{api_base}/api/listings/NL-0072-MAIN")
        public_price_after = _json(body)["asking_price_amount"]
        public_reflects_new_offer_ok = (
            status == 200
            and public_price_before == "125000.00"
            and public_price_after == "139000.00"
            and lifecycle_after_price_edit == "ACTIVE"
            and transitions_after_price_edit == 1  # only the original publish transition
        )
        ok &= public_reflects_new_offer_ok
        print(
            f"8. public listing now reflects the new current offer (125000.00 -> 139000.00) with "
            f"zero lifecycle rewrite (still ACTIVE, exactly 1 transition) -> "
            f"{'OK' if public_reflects_new_offer_ok else 'FAIL'}\n"
        )

        # 5. Real browser Save claim: change keel_configuration FIN -> LONG_KEEL.
        # Re-GET the editor first: every save mints a fresh page-load
        # revision_id (contract §5 idempotency identity), exactly like a
        # real browser reloading before its next edit.
        status, _, body = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0072-MAIN')}")
        page_text = body.decode("utf-8")
        claim_form = _form_block(page_text, "<h2>PhysicalBoat claim</h2>")
        claim_revision_id_1 = _hidden_field_value(claim_form, "revision_id")
        claim_expected_1 = _hidden_field_value(claim_form, "expected_current_revision_id")
        assert claim_expected_1 == db_claim_before.revision_id.value

        status, _, body = session_a.post_form(
            f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0072-MAIN')}",
            {
                "action": "save_claim",
                "revision_id": claim_revision_id_1,
                "expected_current_revision_id": claim_expected_1,
                "marketed_brand_claim": "Beneteau",
                "model_designation_claim": "Oceanis 30.1",
                "build_year_kind": "VALUE_ASSERTION",
                "build_year_value": "2020",
                "keel_configuration_kind": "VALUE_ASSERTION",
                "keel_configuration_value": "LONG_KEEL",
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        claim_save_ok = status == 200 and "Saved." in page_text and "LONG_KEEL" in page_text
        ok &= claim_save_ok
        print(
            f"9. real browser Save claim on NL-0072-MAIN changes keel_configuration FIN -> "
            f"LONG_KEEL -> {'OK' if claim_save_ok else 'FAIL'}"
        )

        conn = psycopg.connect(url)
        try:
            claim_after_edit = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0072-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            claim_revision_count_after_edit = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0072-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_edit is not None
        claim_immutable_ok = (
            claim_after_edit.revision_id.value != db_claim_before.revision_id.value
            and claim_revision_count_after_edit == 2
            and claim_after_edit.claims.keel_configuration is not None
            and claim_after_edit.claims.keel_configuration.value is KeelConfiguration.LONG_KEEL
        )
        ok &= claim_immutable_ok
        print(
            f"   a new immutable claim revision was created (2 revisions on record, prior head "
            f"retained) -> {'OK' if claim_immutable_ok else 'FAIL'}\n"
        )

        # 6. Search/public truth reads the new current claim through the
        # existing accepted paths -- verified here via the accepted public
        # listing read model's own `physical_boat_claims` projection
        # (`hullq.application.public_listing_read`), which reads the current
        # claim head through the identical
        # `fetch_current_physical_boat_claim` path Search itself uses; a
        # confirmed-match Search proof additionally requires a resolved
        # BoatDesign/FieldResolution admission for design-level candidate
        # eligibility (`hullq.application.native_inventory_query`), which is
        # unrelated to this slice's own change and is exercised end to end
        # by `scripts/inspect_first_native_inventory_search.py`.
        status, _, body = session_a.get(f"{api_base}/api/listings/NL-0072-MAIN")
        public_listing_after = _json(body)
        public_keel_after = public_listing_after["physical_boat_claims"]["keel_configuration"][
            "value"
        ]
        public_reflects_new_claim_ok = (
            status == 200 and public_keel_before == "FIN" and public_keel_after == "LONG_KEEL"
        )
        ok &= public_reflects_new_claim_ok
        print(
            f"10. public listing truth now reflects the new current claim (keel_configuration "
            f"FIN -> LONG_KEEL) through the existing accepted public read path -> "
            f"{'OK' if public_reflects_new_claim_ok else 'FAIL'}"
        )

        # 14. Technical native Search criterion count remains exactly 2:
        # both accepted criteria still function, and a third/unknown
        # technical parameter is rejected (400), never silently accepted.
        draft_status, _, _ = session_a.get(f"{web_base}/en/search?draft_max=1.6")
        unknown_status, _, _ = session_a.get(
            f"{web_base}/en/search?draft_max=1.6&keel_configuration=FIN&beam_max=2.0"
        )
        criterion_count_ok = draft_status == 200 and unknown_status == 400
        ok &= criterion_count_ok
        print(
            f"    technical native Search criterion count remains exactly 2 (draft_max=1.6 -> 200; "
            f"an unrecognized third technical parameter -> 400, never silently accepted) -> "
            f"{'OK' if criterion_count_ok else 'FAIL'}\n"
        )

        # 7/8. Stale offer/claim mutations are rejected without overwrite --
        # replay the *original* pre-edit revision ids as the (now stale)
        # expected_current_revision_id via the direct authenticated JSON API.
        offer_path = f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0072-MAIN/offer"
        stale_offer_status, _, stale_offer_body = session_a.post_json(
            offer_path,
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": db_offer_before.revision_id.value,
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "199999.00",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
                "listing_offer.broker_description": "Attempted stale overwrite.",
            },
            extra_headers=_csrf_headers(web_base),
        )
        stale_offer_outcome = _json(stale_offer_body)
        conn = psycopg.connect(url)
        try:
            offer_after_stale_attempt = fetch_current_native_listing_offer(
                conn, NativeListingId("NL-0072-MAIN")
            )
            offer_revision_count_after_stale_attempt = len(
                list_native_listing_offer_revisions(conn, NativeListingId("NL-0072-MAIN"))
            )
        finally:
            conn.close()
        assert offer_after_stale_attempt is not None
        stale_offer_ok = (
            stale_offer_status == 409
            and stale_offer_outcome.get("outcome") == "STALE_VERSION"
            and offer_after_stale_attempt.revision_id.value == offer_after_price_edit.revision_id.value
            and offer_revision_count_after_stale_attempt == offer_revision_count_after_price_edit
        )
        ok &= stale_offer_ok
        print(
            f"11. a stale offer mutation (replaying the original pre-edit revision id) is rejected "
            f"(409 STALE_VERSION) with zero overwrite (current head and revision count unchanged) "
            f"-> {'OK' if stale_offer_ok else 'FAIL'}"
        )

        claim_path = f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0072-MAIN/claim"
        stale_claim_status, _, stale_claim_body = session_a.post_json(
            claim_path,
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": db_claim_before.revision_id.value,
                "physical_boat.marketed_brand_claim": "Beneteau",
                "physical_boat.model_designation_claim": "Oceanis 30.1",
                "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2020},
                "physical_boat.keel_configuration": {
                    "assertion_kind": "VALUE_ASSERTION",
                    "value": "WING",
                },
            },
            extra_headers=_csrf_headers(web_base),
        )
        stale_claim_outcome = _json(stale_claim_body)
        conn = psycopg.connect(url)
        try:
            claim_after_stale_attempt = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId("PB-0072-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
            )
            claim_revision_count_after_stale_attempt = len(
                list_physical_boat_claim_revisions(
                    conn, PhysicalBoatId("PB-0072-MAIN"), MarketplaceOrganizationId(_ORG_A_ID)
                )
            )
        finally:
            conn.close()
        assert claim_after_stale_attempt is not None
        stale_claim_ok = (
            stale_claim_status == 409
            and stale_claim_outcome.get("outcome") == "STALE_VERSION"
            and claim_after_stale_attempt.revision_id.value == claim_after_edit.revision_id.value
            and claim_revision_count_after_stale_attempt == claim_revision_count_after_edit
        )
        ok &= stale_claim_ok
        print(
            f"12. a stale claim mutation (replaying the original pre-edit revision id) is rejected "
            f"(409 STALE_VERSION) with zero overwrite (current head and revision count unchanged) "
            f"-> {'OK' if stale_claim_ok else 'FAIL'}\n"
        )

        # 9. Foreign Organization access remains non-enumerating.
        status, _, _ = session_a.get(f"{web_base}{_edit_page_path(_ORG_A_ID, 'NL-0072-FOREIGN')}")
        foreign_read_not_found_ok = status == 404
        foreign_offer_path = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0072-FOREIGN/offer"
        )
        status, _, _ = session_a.post_json(
            foreign_offer_path,
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": "REV-NL-0072-FOREIGN",
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "1.00",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
                "listing_offer.broker_description": "Attempted cross-Organization edit.",
            },
            extra_headers=_csrf_headers(web_base),
        )
        foreign_write_not_found_ok = status == 404
        conn = psycopg.connect(url)
        try:
            foreign_offer_unchanged = fetch_current_native_listing_offer(
                conn, NativeListingId("NL-0072-FOREIGN")
            )
        finally:
            conn.close()
        assert foreign_offer_unchanged is not None
        foreign_unchanged_ok = foreign_offer_unchanged.revision_id.value == "REV-NL-0072-FOREIGN"
        foreign_ok = foreign_read_not_found_ok and foreign_write_not_found_ok and foreign_unchanged_ok
        ok &= foreign_ok
        print(
            f"13. Account A's read and write attempts against ORG_B-owned NL-0072-FOREIGN under "
            f"the ORG_A path both 404 non-enumeratingly, with zero mutation -> "
            f"{'OK' if foreign_ok else 'FAIL'}\n"
        )

        # 10. DRAFT/ACTIVE/WITHDRAWN lifecycle remains mechanically separate
        # under editing.
        draft_offer_path = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0072-DRAFT/offer"
        )
        status, _, _ = session_a.post_json(
            draft_offer_path,
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": "REV-NL-0072-DRAFT",
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "130000.00",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
                "listing_offer.broker_description": "Updated while still a draft.",
            },
            extra_headers=_csrf_headers(web_base),
        )
        draft_edit_saved_ok = status == 200
        conn = psycopg.connect(url)
        try:
            draft_lifecycle_after_edit = _lifecycle_state(conn, "NL-0072-DRAFT")
        finally:
            conn.close()
        draft_stays_draft_ok = draft_lifecycle_after_edit == "DRAFT"

        withdrawn_offer_path = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0072-WITHDRAWN/offer"
        )
        status, _, _ = session_a.post_json(
            withdrawn_offer_path,
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": "REV-NL-0072-WITHDRAWN",
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "120000.00",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
                "listing_offer.broker_description": "Updated after withdrawal.",
            },
            extra_headers=_csrf_headers(web_base),
        )
        withdrawn_edit_saved_ok = status == 200
        status, _, _ = session_a.get(f"{api_base}/api/listings/NL-0072-WITHDRAWN")
        withdrawn_stays_nonpublic_ok = status == 404
        conn = psycopg.connect(url)
        try:
            withdrawn_lifecycle_after_edit = _lifecycle_state(conn, "NL-0072-WITHDRAWN")
            all_states_accepted_ok = _all_lifecycle_states_are_accepted(conn)
        finally:
            conn.close()
        withdrawn_stays_withdrawn_ok = withdrawn_lifecycle_after_edit == "WITHDRAWN"

        lifecycle_separation_ok = (
            draft_edit_saved_ok
            and draft_stays_draft_ok
            and withdrawn_edit_saved_ok
            and withdrawn_stays_withdrawn_ok
            and withdrawn_stays_nonpublic_ok
            and all_states_accepted_ok
        )
        ok &= lifecycle_separation_ok
        print(
            f"14. an offer edit on NL-0072-DRAFT never implicitly publishes it (stays DRAFT) and an "
            f"offer edit on NL-0072-WITHDRAWN never implicitly republishes it (stays WITHDRAWN, "
            f"public route still 404s); every lifecycle_state remains one of DRAFT/ACTIVE/WITHDRAWN "
            f"-> {'OK' if lifecycle_separation_ok else 'FAIL'}\n"
        )

        # 11. An ACTIVE edit that would violate a hard candidate-head
        # current-public invariant rolls back atomically.
        invariant_offer_path = (
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory/NL-0072-INVARIANT/offer"
        )
        status, _, body = session_a.post_json(
            invariant_offer_path,
            {
                "revision_id": str(uuid.uuid4()),
                "expected_current_revision_id": "REV-NL-0072-INVARIANT",
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "140000.00",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
                "listing_offer.broker_description": "Attempted edit on a broken-chain ACTIVE listing.",
            },
            extra_headers=_csrf_headers(web_base),
        )
        invariant_outcome = _json(body)
        conn = psycopg.connect(url)
        try:
            invariant_offer_after = fetch_current_native_listing_offer(
                conn, NativeListingId("NL-0072-INVARIANT")
            )
            invariant_revision_count_after = len(
                list_native_listing_offer_revisions(conn, NativeListingId("NL-0072-INVARIANT"))
            )
        finally:
            conn.close()
        assert invariant_offer_after is not None
        active_invariant_rollback_ok = (
            status == 422
            and invariant_outcome.get("outcome") == "ACTIVE_INVARIANT_VIOLATION"
            and "MARKET_EPISODE_UNRESOLVED" in invariant_outcome.get("blockers", [])
            and invariant_offer_after.revision_id.value == "REV-NL-0072-INVARIANT"
            and invariant_revision_count_after == 1
        )
        ok &= active_invariant_rollback_ok
        print(
            f"15. an offer edit on the ACTIVE-but-chain-broken NL-0072-INVARIANT fails atomically "
            f"(422 ACTIVE_INVARIANT_VIOLATION, MARKET_EPISODE_UNRESOLVED) leaving the prior offer "
            f"head and revision count unchanged (no partial write) -> "
            f"{'OK' if active_invariant_rollback_ok else 'FAIL'}\n"
        )

        # 12/13. Media/Lead state on NL-0072-MAIN is unchanged by every
        # offer/claim edit above.
        conn = psycopg.connect(url)
        try:
            gallery_after = fetch_gallery_state(conn, NativeListingId("NL-0072-MAIN"))
            gallery_snapshot_after = (
                gallery_after.gallery_version,
                gallery_after.cover_placement_id,
                tuple(p.media_placement_id for p in gallery_after.placements),
            )
            lead_after = fetch_buyer_lead(conn, lead_id)
        finally:
            conn.close()
        assert lead_after is not None
        media_unchanged_ok = gallery_snapshot_after == gallery_snapshot_before
        lead_unchanged_ok = lead_after == lead_before
        ok &= media_unchanged_ok and lead_unchanged_ok
        print(
            f"16. media gallery state (version/cover/placements) on NL-0072-MAIN is byte-identical "
            f"before and after every offer/claim edit -> {'OK' if media_unchanged_ok else 'FAIL'}"
        )
        print(
            f"    the Lead created against NL-0072-MAIN is byte-identical before and after every "
            f"offer/claim edit -> {'OK' if lead_unchanged_ok else 'FAIL'}\n"
        )

        # Ordinary logs must never contain the client/session secret.
        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = all(
            client_secret not in text and session_secret_b64 not in text
            for text in (api_log_text, web_log_text)
        )
        ok &= secrets_clean
        print(f"    ordinary API/web logs contain no client/session secret -> {'OK' if secrets_clean else 'FAIL'}\n")

        print(f"PROFESSIONAL INVENTORY EDITING RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
