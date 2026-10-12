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

Demonstrates, with one real Account holding real Organization memberships:

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
    6. PR #327 review finding C: a Populated Organization with a real
       published NativeListing, six real buyer Leads against it and one
       real EDITABLE (not-ready) draft -- reached through a thin local
       reverse proxy placed in front of the real FastAPI backend that lets
       every route through unchanged EXCEPT this Organization's own
       performance route, which it answers with a deliberately malformed
       200 JSON body (the real defect PR #327 review finding A fixed).
       Proves, against the real stack: a genuinely nonzero/bounded Leads
       preview (5 of 6, with the true 6-count still shown by the separate
       counts endpoint), the true published listing in Inventory, the
       ordinary EDITABLE draft's own not-ready readiness (never "Ready to
       promote"), and the injected real Performance failure rendering as
       "unavailable" without the page crashing or any other panel losing
       its real data. Finding B's core fix -- a PROMOTED draft must never
       be labeled "Ready to promote" -- is proven at the unit level
       (`brokerDashboardPresentation.test.ts`): FastAPI's own drafts LIST
       query is itself filtered to EDITABLE rows only
       (`professional_listing_draft.py`'s `_SELECT_FIRST_PAGE`), so this
       composed panel can never actually receive a real PROMOTED row to
       exercise end-to-end.

Bounded-request-size (page_size: 5 forwarded to each client) is a
structural property of `[organization_id].astro`'s source (also exercised
indirectly by scenario 6's 6-Lead truncation above) and the dashboard's
zero-mutation GET is likewise structural (no POST handler exists on this
page) -- neither is separately re-exercised here. Each underlying read
service's own domain correctness (lead counts, promotion readiness,
inventory lifecycle, performance aggregation) is already proven by its own
accepted slice's retained proof/tests; this script does not re-prove those.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_workspace_dashboard.py
"""

from __future__ import annotations

import base64
import http.client
import http.cookiejar
import http.server
import json
import os
import secrets
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

import psycopg

from hullq.domain.broker_access import Provider
from hullq.domain.buyer_lead import SubmissionOperationId
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import MediaSourceKind
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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    get_or_create_account_for_identity,
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.persistence.buyer_lead import create_buyer_lead
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_ORG_NOPUB_ID = "ORG-0081-MEMBER-ONLY"
_ORG_PUB_ID = "ORG-0081-PUBLISHER"
_ORG_FOREIGN_ID = "ORG-0081-FOREIGN"
_ORG_POPULATED_ID = "ORG-0081-POPULATED"
_NEVER_SEEDED_ORG_ID = "ORG-0081-NEVER-CREATED"
_SUBJECT = "broker-0081-subject"
_FOREIGN_SUBJECT = "broker-0081-foreign-subject"
_POPULATED_LISTING_ID = "NL-0081-POPULATED-1"
_POPULATED_LEAD_COUNT = 6

_DRAFT_CSRF_HEADER_NAME = "X-HullQ-Requested-With"
_DRAFT_CSRF_HEADER_VALUE = "professional-listing-draft-v1"


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
        except urllib.error.URLError, ConnectionError, TimeoutError, OSError:
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

    def request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        json_body: Any = None,
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        data = json.dumps(json_body).encode("utf-8") if json_body is not None else None
        req = urllib.request.Request(url, data=data, headers=dict(headers or {}), method=method)
        response = self._opener.open(req, timeout=10)
        status = response.status
        resp_headers = response.headers
        body = response.read()
        return status, resp_headers, body

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        status, headers, _ = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, _ = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}"
        callback_url = headers["Location"]
        return self.get(callback_url)


class _FaultInjectingProxyHandler(http.server.BaseHTTPRequestHandler):
    """Forwards every GET to the real FastAPI backend unchanged, except one
    exact path (`intercept_path`, no query string), which it answers
    locally with a 200 response carrying a deliberately malformed/
    unparsable JSON body -- a real, injected partial-dependency failure for
    one Organization's one panel, placed between the real built Astro SSR
    process and the real FastAPI process (PR #327 review finding C)."""

    api_base: str = ""
    intercept_path: str = ""

    def do_GET(self) -> None:  # noqa: N802 (BaseHTTPRequestHandler naming)
        request_path = urllib.parse.urlsplit(self.path).path
        if request_path == self.intercept_path:
            body = b'{"window": "LAST_30_DAYS", "public_listing_views": '
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        forwarded = urllib.request.Request(f"{self.api_base}{self.path}", method="GET")
        cookie = self.headers.get("Cookie")
        if cookie:
            forwarded.add_header("Cookie", cookie)
        try:
            with urllib.request.urlopen(forwarded, timeout=10) as upstream:
                self._relay(upstream.status, upstream.headers, upstream.read())
        except urllib.error.HTTPError as err:
            self._relay(err.code, err.headers, err.read())

    def _relay(self, status: int, headers: Any, body: bytes) -> None:
        self.send_response(status)
        for key, value in headers.items():
            if key.lower() in ("transfer-encoding", "connection", "content-length"):
                continue
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        pass


def _seed_populated_organization_with_listing_and_leads(
    url: str, *, org_id: str, listing_id: str, lead_count: int
) -> None:
    """Publish one complete, real NativeListing under *org_id* and durably
    create *lead_count* real buyer Leads against it -- reusing exactly the
    accepted SLICE-0053/-0060/-0067/-0070 persistence write paths (mirrors
    `tests/persistence/test_broker_lead_operations_api.py`'s
    `_publish_listing_and_create_lead` helper), so the dashboard's Leads and
    Inventory panels have real, nonzero, source-truthful data to compose
    (PR #327 review finding C)."""
    conn = psycopg.connect(url)
    try:
        writer_account = AccountId(f"ACC-writer-{listing_id}")
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-writer-{listing_id}"),
            account_id=writer_account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [writer_account.value],
            )
        conn.commit()
        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-{listing_id}"))
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(f"ME-{listing_id}"),
                physical_boat_id=PhysicalBoatId(f"PB-{listing_id}"),
            ),
        )
        create_native_listing(
            conn,
            account_id=writer_account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id),
                market_episode_id=MarketEpisodeId(f"ME-{listing_id}"),
            ),
        )
        write_native_listing_offer_revision(
            conn,
            account_id=writer_account,
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
            account_id=writer_account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 30.1",
                build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            ),
        )
        with conn.transaction():
            asset = insert_approved_media_asset(
                conn,
                owner_organization_id=org.id,
                uploaded_by_account_id=writer_account,
                rights_declared=True,
                source_kind=MediaSourceKind.BROKER_UPLOAD,
                source_reference=None,
                original_object_key=f"original/{listing_id}",
                derivative_object_key=f"derivative/{listing_id}",
                content_hash=f"hash-{listing_id}",
                mime_type="image/jpeg",
                width=800,
                height=600,
                byte_size=12345,
            )
            placement_result = create_uploaded_image_placement(
                conn,
                native_listing_id=NativeListingId(listing_id),
                owner_organization_id=org.id,
                media_asset=asset,
            )
            set_cover(
                conn,
                native_listing_id=NativeListingId(listing_id),
                owner_organization_id=org.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=placement_result.gallery_version,
            )
        publish_result = publish_native_listing(
            conn,
            account_id=writer_account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert publish_result.status.value == "transitioned", publish_result

        for i in range(lead_count):
            lead_result = create_buyer_lead(
                conn,
                submission_operation_id=SubmissionOperationId(f"OP-{listing_id}-{i}"),
                native_listing_id=NativeListingId(listing_id),
                account_id=None,
                buyer_name=f"Buyer-{i}",
                buyer_email=f"buyer{i}@example.com",
                buyer_message="Interested in this boat.",
                as_of=datetime.now(UTC),
            )
            assert lead_result.status.value == "created", lead_result
        conn.commit()
    finally:
        conn.close()


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
    proxy_server: http.server.ThreadingHTTPServer | None = None
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

        # A thin real reverse proxy sits between the built Astro SSR process
        # and the real FastAPI process: every route is forwarded unchanged
        # except one Organization's own performance route, which is
        # answered locally with a malformed 200 body (PR #327 review
        # finding C's real injected partial-dependency failure). Astro's
        # own internal server-to-server panel/context calls are the only
        # thing routed through this proxy -- this script's own direct calls
        # below (login, draft creation) still talk to the real FastAPI port.
        _FaultInjectingProxyHandler.api_base = api_base
        _FaultInjectingProxyHandler.intercept_path = (
            f"/api/broker/organizations/{_ORG_POPULATED_ID}/performance"
        )
        proxy_port = _free_port()
        proxy_server = http.server.ThreadingHTTPServer(
            ("127.0.0.1", proxy_port), _FaultInjectingProxyHandler
        )
        proxy_thread = threading.Thread(target=proxy_server.serve_forever, daemon=True)
        proxy_thread.start()
        proxy_base = f"http://127.0.0.1:{proxy_port}"

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = proxy_base
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
            seed_marketplace_organization(
                conn,
                MarketplaceOrganization(
                    id=MarketplaceOrganizationId(_ORG_POPULATED_ID),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0081-POPULATED"),
                    account_id=AccountId(account_id),
                    organization_id=MarketplaceOrganizationId(_ORG_POPULATED_ID),
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
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
        print(
            f"   ORG_NOPUB's page never leaks ORG_PUB's id -> {'OK' if no_cross_leak_ok else 'FAIL'}\n"
        )

        # 8. foreign Organization and a never-created Organization id remain
        # identical, non-enumerating 404s on this composed page.
        status_foreign, _, body_foreign = session.get(
            f"{web_base}/broker/organizations/{_ORG_FOREIGN_ID}"
        )
        status_never, _, body_never = session.get(
            f"{web_base}/broker/organizations/{_NEVER_SEEDED_ORG_ID}"
        )
        cross_org_ok = status_foreign == 404 and status_never == 404 and body_foreign == body_never
        ok &= cross_org_ok
        print(
            f"8. foreign Organization and a never-created Organization id are identical, "
            f"non-enumerating 404s (no panel data) -> {'OK' if cross_org_ok else 'FAIL'}\n"
        )

        # 9. PR #327 review finding C: a real populated Organization, with
        # the real performance endpoint intercepted by the fault-injecting
        # proxy. Seed a real published NativeListing + 6 real buyer Leads.
        _seed_populated_organization_with_listing_and_leads(
            url,
            org_id=_ORG_POPULATED_ID,
            listing_id=_POPULATED_LISTING_ID,
            lead_count=_POPULATED_LEAD_COUNT,
        )

        def _draft_csrf_headers() -> dict[str, str]:
            return {
                "Origin": web_base,
                _DRAFT_CSRF_HEADER_NAME: _DRAFT_CSRF_HEADER_VALUE,
                "Content-Type": "application/json",
            }

        drafts_path = f"{api_base}/api/broker/organizations/{_ORG_POPULATED_ID}/drafts"

        # One EDITABLE draft, deliberately left unfilled -- ordinary
        # not-ready readiness must be preserved (review finding B's second
        # half: "preserve ordinary editable readiness"). Note: FastAPI's
        # drafts LIST query (`list_professional_listing_drafts_page` /
        # `_SELECT_FIRST_PAGE` in `professional_listing_draft.py`) is itself
        # filtered to `promotion_state = 'EDITABLE'` only -- a real PROMOTED
        # draft can never be returned by this list endpoint at all, so this
        # exact composed panel can never actually receive one to mislabel.
        # Finding B's core fix (never call `draftReadinessLabel` on a
        # PROMOTED draft, regardless of what endpoint might one day supply
        # one) is instead proven directly at the unit level in
        # `brokerDashboardPresentation.test.ts` (`draftPanelStatusLabel`:
        # PROMOTED+ready, PROMOTED+not-ready, PROMOTED without an id).
        status, _, body = session.request(
            "POST", drafts_path, headers=_draft_csrf_headers(), json_body={}
        )
        editable_draft_ok = 200 <= status < 300
        ok &= editable_draft_ok
        print(
            f"9. seeded Populated Organization: real published listing + {_POPULATED_LEAD_COUNT} real "
            f"Leads, one real EDITABLE draft -> {'OK' if editable_draft_ok else 'FAIL'}"
        )

        status, headers, body = session.get(f"{web_base}/broker/organizations/{_ORG_POPULATED_ID}")
        page_text = body.decode("utf-8")

        no_crash_ok = status == 200
        performance_unavailable_ok = (
            "Temporarily unavailable. Please try again." in page_text
            and "Public listing views observed:" not in page_text
        )
        leads_bounded_ok = (
            "New / unread: 6" in page_text
            and "Unassigned: 6" in page_text
            and "Recent leads (sample, up to 5):" in page_text
            and page_text.count("Buyer-") == 5
        )
        inventory_ok = _POPULATED_LISTING_ID in page_text and "ACTIVE" in page_text
        drafts_editable_shown_ok = (
            "Not ready:" in page_text
            and "MISSING_MARKETED_BRAND" in page_text
            and "Ready to promote" not in page_text
        )
        populated_ok = (
            no_crash_ok
            and performance_unavailable_ok
            and leads_bounded_ok
            and inventory_ok
            and drafts_editable_shown_ok
        )
        ok &= populated_ok
        print(
            f"10. Populated Organization through the fault-injecting proxy: page still 200 "
            f"despite the injected malformed Performance body -> {'OK' if no_crash_ok else 'FAIL'}\n"
            f"    Performance panel shows the distinct unavailable text, no invented zero -> "
            f"{'OK' if performance_unavailable_ok else 'FAIL'}\n"
            f"    Leads panel: true 6-count shown by the counts endpoint, exactly 5 of 6 Leads "
            f"previewed, labeled as a sample -> {'OK' if leads_bounded_ok else 'FAIL'}\n"
            f"    Inventory panel shows the real published listing -> {'OK' if inventory_ok else 'FAIL'}\n"
            f"    Drafts panel: the ordinary EDITABLE draft's own not-ready readiness still shows, "
            f"never 'Ready to promote' -> {'OK' if drafts_editable_shown_ok else 'FAIL'}\n"
        )

        print(f"BROKER WORKSPACE OPERATIONAL DASHBOARD RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        if proxy_server is not None:
            proxy_server.shutdown()
            proxy_server.server_close()
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
