"""SLICE-0063 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed publishing-Organization-public-identity vertical
against a real, disposable PostgreSQL 18 schema and real local HTTP servers
(a deterministic local OIDC/JWKS test issuer, FastAPI, and the built
Astro/Node SSR web package). No Account is ever created by monkeypatching --
the Broker Workspace Account in this proof is created by a real
authorization-code login round-trip through the real issuer and FastAPI's
real token/JWKS validation, exactly like `scripts/inspect_broker_workspace_access.py`.

Per `specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md` §14,
demonstrates:

    1. migrate/seed an eligible MarketplaceOrganization with a
       human-readable display name
    2. render an authorized Broker Workspace Organization surface and
       verify that name (both /broker and /broker/organizations/{id})
    3. create/reuse a public ACTIVE current listing for that Organization
    4. omit VAT/tax claim in that case
    5. fetch FastAPI public listing and prove exact Organization ID +
       display name
    6. fetch built Astro public listing and prove the display name is
       visibly rendered despite absent VAT claim
    7. use a safe malicious-text fixture and prove it is escaped/inert
    8. update only the Organization display name
    9. prove the same NativeListing ID/URL now renders the new display
       name with no listing mutation/lifecycle transition/offer revision
    10. prove a legacy/unresolved publishing Organization ID remains
        publicly readable and uses exact ID fallback
    11. prove DRAFT/WITHDRAWN/unknown public-read behavior remains
        unchanged

The Broker Workspace Account holds a `PUBLISHER` membership on
ORG_DISPLAY (needed to publish that Organization's listing below), which
requires the same MFA step-up already proven end-to-end by
`scripts/inspect_broker_workspace_access.py`; this proof re-runs that
step-up only far enough to reach the Organization workspace page and
confirm the display name renders there -- SLICE-0063 does not change
authorization/MFA behavior at all, so it does not re-prove MFA gating
itself.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_publishing_organization_public_identity.py
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
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

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
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
    update_marketplace_organization_display_name,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    list_publication_transitions,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_ORG_DISPLAY_ID = "ORG-0063-DISPLAY"
_ORG_DISPLAY_NAME = "Ocean Yachts Brokerage, Inc."
_ORG_DISPLAY_RENAMED = "Renamed Ocean Yachts Brokerage LLC"
_ORG_MALICIOUS_ID = "ORG-0063-MALICIOUS"
_ORG_MALICIOUS_NAME = "<script>alert('xss')</script>"
_ORG_LEGACY_ID = "ORG-0063-LEGACY-UNRESOLVED"
_SUBJECT = "broker-0063-subject"

_LISTING_DISPLAY_ID = "NL-0063-DISPLAY"
_LISTING_MALICIOUS_ID = "NL-0063-MALICIOUS"
_LISTING_LEGACY_ID = "NL-0063-LEGACY"
_LISTING_DRAFT_ONLY_ID = "NL-0063-DRAFT-ONLY"


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
    `scripts/inspect_broker_workspace_access.py`'s `BrowserSession`)."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(self, method: str, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        req = urllib.request.Request(url, method=method)
        response = self._opener.open(req, timeout=10)
        status = response.status
        resp_headers = response.headers
        body = response.read()
        return status, resp_headers, body

    def get(self, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url)

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        status, headers, _ = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, body = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}: {body!r}"
        callback_url = headers["Location"]
        return self.get(callback_url)


def _http_get(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _org(org_id: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _create_and_publish_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    """Complete accepted chain + current offer (deliberately no VAT/tax
    claim) + publish. Never sets `vat_tax_status_claim` (contract §8/§14
    item 4: at least one representative case must omit it)."""
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
        ),
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=NativeListingOfferRevisionId(offer_revision_id),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("99000.00"),
            currency="EUR",
        ),
    )
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0063e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0063_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("PUBLISHING ORGANIZATION PUBLIC IDENTITY\n")

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

        client_id = "hullq-s0063-client"
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
            print("PUBLISHING ORGANIZATION PUBLIC IDENTITY RESULT -> FAIL")
            return 1

        # Real OIDC login first (contract requires no monkeypatched
        # Account): the resulting HullQ AccountId is only known after this
        # round-trip, so memberships/listings below are seeded against the
        # exact real account_id, exactly like
        # `scripts/inspect_broker_workspace_access.py`.
        session = BrowserSession()
        login_url = f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
        status, headers, _ = session.follow_full_login(login_url)
        login_ok = status == 302 and headers.get("Location") == f"{web_base}/broker"
        ok &= login_ok
        print(f"1. real OIDC login round-trip -> {'OK' if login_ok else 'FAIL'}")

        status, _, body = session.get(f"{api_base}/api/broker/context")
        account_id_value = json.loads(body.decode("utf-8"))["account_id"]
        account = AccountId(account_id_value)

        # migrate/seed an eligible MarketplaceOrganization with a
        # human-readable display name, plus the malicious-text and legacy
        # (never-seeded) fixtures used later.
        org_display = MarketplaceOrganization(
            id=MarketplaceOrganizationId(_ORG_DISPLAY_ID),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            public_display_name=_ORG_DISPLAY_NAME,
        )
        org_malicious = MarketplaceOrganization(
            id=MarketplaceOrganizationId(_ORG_MALICIOUS_ID),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            public_display_name=_ORG_MALICIOUS_NAME,
        )
        org_legacy = _org(_ORG_LEGACY_ID)  # deliberately never seeded below

        conn = psycopg.connect(url)
        try:
            seed_marketplace_organization(conn, org_display)
            seed_marketplace_organization(conn, org_malicious)
            membership_display = OrganizationMembership(
                id=OrganizationMembershipId("OM-0063-DISPLAY"),
                account_id=account,
                organization_id=org_display.id,
                roles=frozenset({MembershipRole.PUBLISHER}),  # needed to publish below
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership_display)
            membership_malicious = OrganizationMembership(
                id=OrganizationMembershipId("OM-0063-MALICIOUS"),
                account_id=account,
                organization_id=org_malicious.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            membership_legacy = OrganizationMembership(
                id=OrganizationMembershipId("OM-0063-LEGACY"),
                account_id=account,
                organization_id=org_legacy.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            conn.commit()  # release the implicit read/write transaction before create_physical_boat

            # one public ACTIVE current listing for the display-name
            # Organization, with no VAT/tax claim.
            _create_and_publish_listing(
                conn,
                listing_id=_LISTING_DISPLAY_ID,
                physical_boat_id="PB-0063-DISPLAY",
                market_episode_id="ME-0063-DISPLAY",
                offer_revision_id="REV-0063-DISPLAY",
                account=account,
                org=org_display,
                membership=membership_display,
            )
            # Malicious-display-name Organization's own published listing.
            _create_and_publish_listing(
                conn,
                listing_id=_LISTING_MALICIOUS_ID,
                physical_boat_id="PB-0063-MALICIOUS",
                market_episode_id="ME-0063-MALICIOUS",
                offer_revision_id="REV-0063-MALICIOUS",
                account=account,
                org=org_malicious,
                membership=membership_malicious,
            )
            # Legacy/unresolved Organization's own published listing --
            # org_legacy is never written to marketplace_organizations.
            _create_and_publish_listing(
                conn,
                listing_id=_LISTING_LEGACY_ID,
                physical_boat_id="PB-0063-LEGACY",
                market_episode_id="ME-0063-LEGACY",
                offer_revision_id="REV-0063-LEGACY",
                account=account,
                org=org_legacy,
                membership=membership_legacy,
            )
            # A DRAFT-only listing (never published) for the not-found proof.
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0063-DRAFT-ONLY"))
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_display,
                membership=membership_display,
                listing=NativeListing(id=NativeListingId(_LISTING_DRAFT_ONLY_ID)),
            )
            conn.commit()
        finally:
            conn.close()
        print(
            "2. seeded ORG_DISPLAY (human display name), ORG_MALICIOUS "
            "(script-tag display name), and a never-seeded legacy Organization; "
            "published one listing per Organization (owned by the real logged-in "
            "Account) with no VAT/tax claim -> OK\n"
        )

        # render both Broker Workspace surfaces -- verify the display name.
        status, _, body = session.get(f"{web_base}/broker")
        list_page_text = body.decode("utf-8")
        list_page_ok = (
            status == 200
            and _ORG_DISPLAY_NAME in list_page_text
            and _ORG_DISPLAY_ID in list_page_text
        )
        ok &= list_page_ok
        print(
            f"3. Astro /broker chooser visibly renders the Organization display name -> "
            f"{'OK' if list_page_ok else 'FAIL'}"
        )

        # PUBLISHER is a privileged role (PRIVILEGED_MFA_ROLES): the single
        # Organization workspace page requires the same MFA step-up
        # already proven end-to-end by
        # `scripts/inspect_broker_workspace_access.py` -- this proof
        # re-runs it only far enough to reach the page and check the
        # display name renders there, not to re-prove MFA gating itself.
        stepup_login_url = (
            f"{api_base}/api/auth/login?next=/broker/organizations/{_ORG_DISPLAY_ID}"
            f"&login_hint={_SUBJECT}&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session.follow_full_login(stepup_login_url)

        status, _, body = session.get(f"{web_base}/broker/organizations/{_ORG_DISPLAY_ID}")
        org_page_text = body.decode("utf-8")
        org_page_ok = status == 200 and _ORG_DISPLAY_NAME in org_page_text
        ok &= org_page_ok
        print(
            f"   Astro Organization workspace visibly renders the display name -> "
            f"{'OK' if org_page_ok else 'FAIL'}"
        )

        status, _, body = session.get(f"{api_base}/api/broker/context")
        context = json.loads(body.decode("utf-8"))
        context_ok = status == 200 and any(
            o["organization_id"] == _ORG_DISPLAY_ID
            and o["public_display_name"] == _ORG_DISPLAY_NAME
            for o in context["organizations"]
        )
        ok &= context_ok
        print(
            f"   FastAPI /api/broker/context carries the same display name -> {'OK' if context_ok else 'FAIL'}\n"
        )

        # FastAPI public listing: exact Organization ID + display name.
        api_status, _api_headers, api_body = _http_get(
            f"{api_base}/api/listings/{_LISTING_DISPLAY_ID}"
        )
        api_payload = json.loads(api_body.decode("utf-8"))
        step5_ok = (
            api_status == 200
            and api_payload["vat_tax_status_claim"] is None
            and api_payload["publishing_organization_id"] == _ORG_DISPLAY_ID
            and api_payload["publishing_organization_display_name"] == _ORG_DISPLAY_NAME
        )
        ok &= step5_ok
        print(
            f"4. FastAPI public listing exposes exact Organization ID + display name, "
            f"VAT claim absent -> {'OK' if step5_ok else 'FAIL'}"
        )

        # built Astro public listing: display name rendered despite no VAT claim.
        web_status, _, web_body = _http_get(f"{web_base}/listings/{_LISTING_DISPLAY_ID}")
        web_text = web_body.decode("utf-8")
        step6_ok = (
            web_status == 200
            and f"Listed by {_ORG_DISPLAY_NAME}" in web_text
            and "VAT/tax status" not in web_text
        )
        ok &= step6_ok
        print(
            f"5. built Astro public listing visibly renders 'Listed by {{name}}' with no "
            f"VAT block present -> {'OK' if step6_ok else 'FAIL'}\n"
        )

        # malicious display-name fixture is escaped/inert.
        web_status, _, web_body = _http_get(f"{web_base}/listings/{_LISTING_MALICIOUS_ID}")
        malicious_text = web_body.decode("utf-8")
        step7_ok = (
            web_status == 200
            and _ORG_MALICIOUS_NAME not in malicious_text
            and "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in malicious_text
        )
        ok &= step7_ok
        print(
            f"6. malicious script-tag display name renders escaped/inert -> {'OK' if step7_ok else 'FAIL'}\n"
        )

        # update only the display name; same listing/ID/URL now shows the
        # new name, with no lifecycle transition or offer revision.
        transitions_before = None
        conn = psycopg.connect(url)
        try:
            transitions_before = list_publication_transitions(
                conn, NativeListingId(_LISTING_DISPLAY_ID)
            )
        finally:
            conn.close()

        conn = psycopg.connect(url)
        try:
            update_marketplace_organization_display_name(conn, org_display.id, _ORG_DISPLAY_RENAMED)
            conn.commit()
        finally:
            conn.close()

        conn = psycopg.connect(url)
        try:
            transitions_after = list_publication_transitions(
                conn, NativeListingId(_LISTING_DISPLAY_ID)
            )
        finally:
            conn.close()

        renamed_api_status, _, renamed_api_body = _http_get(
            f"{api_base}/api/listings/{_LISTING_DISPLAY_ID}"
        )
        renamed_payload = json.loads(renamed_api_body.decode("utf-8"))
        renamed_web_status, _, renamed_web_body = _http_get(
            f"{web_base}/listings/{_LISTING_DISPLAY_ID}"
        )
        renamed_web_text = renamed_web_body.decode("utf-8")
        step89_ok = (
            renamed_api_status == 200
            and renamed_payload["publishing_organization_display_name"] == _ORG_DISPLAY_RENAMED
            and renamed_payload["publishing_organization_id"] == _ORG_DISPLAY_ID
            and renamed_payload["asking_price_amount"] == api_payload["asking_price_amount"]
            and renamed_payload["offer_recorded_at"] == api_payload["offer_recorded_at"]
            and renamed_web_status == 200
            and f"Listed by {_ORG_DISPLAY_RENAMED}" in renamed_web_text
            and transitions_after == transitions_before
            and len(transitions_after) == 1
        )
        ok &= step89_ok
        print(
            f"7. display-name-only update: same listing ID/URL now renders the new name, "
            f"identical offer/no new lifecycle transition -> {'OK' if step89_ok else 'FAIL'}\n"
        )

        # legacy/unresolved Organization: exact-ID fallback, still readable.
        legacy_api_status, _, legacy_api_body = _http_get(
            f"{api_base}/api/listings/{_LISTING_LEGACY_ID}"
        )
        legacy_payload = json.loads(legacy_api_body.decode("utf-8"))
        legacy_web_status, _, legacy_web_body = _http_get(
            f"{web_base}/listings/{_LISTING_LEGACY_ID}"
        )
        legacy_web_text = legacy_web_body.decode("utf-8")
        step10_ok = (
            legacy_api_status == 200
            and legacy_payload["publishing_organization_id"] == _ORG_LEGACY_ID
            and legacy_payload["publishing_organization_display_name"] == _ORG_LEGACY_ID
            and legacy_web_status == 200
            and f"Listed by {_ORG_LEGACY_ID}" in legacy_web_text
        )
        ok &= step10_ok
        print(
            f"8. legacy/unresolved publishing Organization (no actor-directory row) stays "
            f"publicly readable, exact-ID fallback -> {'OK' if step10_ok else 'FAIL'}\n"
        )

        # DRAFT/WITHDRAWN/unknown public-read behavior unchanged.
        draft_status, _, _ = _http_get(f"{api_base}/api/listings/{_LISTING_DRAFT_ONLY_ID}")
        unknown_status, _, _ = _http_get(f"{api_base}/api/listings/NL-0063-NEVER-CREATED")

        conn = psycopg.connect(url)
        try:
            withdraw_result = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_malicious,
                membership=membership_malicious,
                native_listing_id=NativeListingId(_LISTING_MALICIOUS_ID),
            )
            assert withdraw_result.status.value == "transitioned", withdraw_result
            conn.commit()
        finally:
            conn.close()
        withdrawn_status, _, _ = _http_get(f"{api_base}/api/listings/{_LISTING_MALICIOUS_ID}")

        step11_ok = draft_status == 404 and unknown_status == 404 and withdrawn_status == 404
        ok &= step11_ok
        print(
            f"9. DRAFT-only, never-created and now-WITHDRAWN listings all remain ordinary "
            f"not-found -> {'OK' if step11_ok else 'FAIL'}\n"
        )

        # Ordinary logs must never contain the client/session secret.
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

        print(f"PUBLISHING ORGANIZATION PUBLIC IDENTITY RESULT -> {'PASS' if ok else 'FAIL'}")
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
