"""SLICE-0060 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed authenticated-professional-inventory-overview
vertical against a real, disposable PostgreSQL 18 schema and three real
local HTTP servers: a deterministic local OIDC/JWKS test issuer
(`hullq.testing.oidc_test_issuer`), FastAPI, and the built Astro/Node SSR
web package -- mirroring `scripts/inspect_broker_workspace_access.py`'s real
browser-style login discipline (no Account is ever created by
monkeypatching).

Per `specs/PROFESSIONAL_INVENTORY_OVERVIEW_CONTRACT.v0.1.md` §15, demonstrates:

    1. one authenticated Account with an authorized Organization (ORG_A)
    2. a second Organization (ORG_B) not authorized to that Account
    3. ORG_A owns representative DRAFT, ACTIVE and WITHDRAWN NativeListings
       spanning two keyset pages (page_size=2)
    4. ORG_B owns a listing that never appears in ORG_A's inventory
    5. keyset continuation returns deterministic, non-overlapping pages and
       never escapes the Organization filter
    6. lifecycle/offer/freshness facts are current and exact
    7. a public link exists only for the item the accepted current public
       read actually resolves
    8. unauthenticated, MFA-required and revoked-membership access all fail
       closed
    9. an authorized zero-listing Organization is distinct from unauthorized/
       service failure
    10. the supporting Organization/sort-key index exists after migration
    11. finishes with the required PASS marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_professional_inventory_overview.py
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
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from hullq.domain.broker_access import Provider
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
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
    get_or_create_account_for_identity,
    seed_marketplace_organization,
    seed_organization_membership,
    update_membership_state,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_freshness import reconfirm_native_listing
from hullq.persistence.native_listing_lifecycle import (
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

_ORG_A_ID = "ORG-0060-A"
_ORG_B_ID = "ORG-0060-B"
_ORG_EMPTY_ID = "ORG-0060-EMPTY"
_NEVER_SEEDED_ORG_ID = "ORG-0060-NEVER-CREATED"
_SUBJECT = "inv-0060-subject"
_OTHER_SUBJECT = "inv-0060-other-subject"


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
    """A real, standards-compliant cookie-jar HTTP client (see
    `scripts/inspect_broker_workspace_access.py` for the full rationale)."""

    def __init__(self) -> None:
        self.jar = http.cookiejar.CookieJar()
        self._opener = urllib.request.build_opener(
            _NoRedirect, urllib.request.HTTPCookieProcessor(self.jar)
        )

    def request(
        self, method: str, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        req = urllib.request.Request(url, headers=dict(extra_headers or {}), method=method)
        response = self._opener.open(req, timeout=10)
        status = response.status
        resp_headers = response.headers
        body = response.read()
        return status, resp_headers, body

    def get(self, url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url)

    def follow_full_login(self, login_url: str) -> tuple[int, http.client.HTTPMessage, bytes]:
        status, headers, body = self.get(login_url)
        assert status == 302, f"expected 302 from /api/auth/login, got {status}"
        authorize_url = headers["Location"]
        status, headers, body = self.get(authorize_url)
        assert status == 302, f"expected 302 from issuer /authorize, got {status}: {body!r}"
        callback_url = headers["Location"]
        return self.get(callback_url)


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    membership_id: str, account: AccountId, org: MarketplaceOrganization, *, role: MembershipRole
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({role}),
        state=MembershipState.ACTIVE,
    )


def _set_created_at(conn: Any, *, listing_id: str, created_at: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "UPDATE native_listings SET created_at = %s WHERE native_listing_id = %s",
            (created_at, listing_id),
        )


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0060e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0060_e2e_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("PROFESSIONAL INVENTORY OVERVIEW\n")

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
                    ("ix_native_listings_org_created_id", "native_listings"),
                )
                index_ok = cur.fetchone() is not None
        finally:
            index_conn.close()
        ok &= index_ok
        print(
            f"   supporting (publishing_organization_id, created_at, native_listing_id) "
            f"index exists -> {'OK' if index_ok else 'FAIL'}\n"
        )

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
            print("PROFESSIONAL INVENTORY OVERVIEW RESULT -> FAIL")
            return 1

        # 4. unauthenticated inventory read is denied.
        session = BrowserSession()
        status, _, _ = session.get(f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory")
        step4_ok = status == 401
        ok &= step4_ok
        print(f"4. unauthenticated inventory read denied (401) -> {'OK' if step4_ok else 'FAIL'}")

        # Real login (JIT Account creation, no monkeypatching).
        login_url = f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
        status, _, body = session.follow_full_login(login_url)
        assert status == 302, f"expected 302 from callback, got {status}: {body!r}"
        status, _, body = session.get(f"{api_base}/api/broker/context")
        account_id = _json(body)["account_id"]
        print(f"5. real OIDC login creates one stable Account ({account_id}) -> OK")

        conn = psycopg.connect(url)
        try:
            other_account_id = get_or_create_account_for_identity(
                conn, provider=Provider.AUTH0, issuer=issuer_base, subject=_OTHER_SUBJECT
            ).account_id
            org_a = _org(_ORG_A_ID)
            org_b = _org(_ORG_B_ID)
            org_empty = _org(_ORG_EMPTY_ID)
            seed_marketplace_organization(conn, org_a)
            seed_marketplace_organization(conn, org_b)
            seed_marketplace_organization(conn, org_empty)

            account = AccountId(account_id)
            membership_a = _membership("OM-0060-A", account, org_a, role=MembershipRole.PUBLISHER)
            membership_empty = _membership(
                "OM-0060-EMPTY", account, org_empty, role=MembershipRole.MEMBER
            )
            membership_b_other = _membership(
                "OM-0060-B-OTHER", other_account_id, org_b, role=MembershipRole.PUBLISHER
            )
            seed_organization_membership(conn, membership_a)
            seed_organization_membership(conn, membership_empty)
            seed_organization_membership(conn, membership_b_other)
            conn.commit()

            # ORG_A: DRAFT, ACTIVE (complete + fresh + publicly readable),
            # WITHDRAWN -- three representative listings across two pages
            # once queried with page_size=2.
            draft_result = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(id=NativeListingId("NL-0060-DRAFT")),
            )
            assert draft_result.status.value in ("created", "already_exists"), draft_result
            conn.commit()

            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0060-ACTIVE"))
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0060-ACTIVE"),
                    physical_boat_id=PhysicalBoatId("PB-0060-ACTIVE"),
                ),
            )
            active_create = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(
                    id=NativeListingId("NL-0060-ACTIVE"),
                    market_episode_id=MarketEpisodeId("ME-0060-ACTIVE"),
                ),
                broker_listing_reference="REF-0060-ACTIVE",
            )
            assert active_create.status.value in ("created", "already_exists"), active_create
            active_offer = write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0060-ACTIVE"),
                revision_id=NativeListingOfferRevisionId("REV-0060-ACTIVE"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
            assert active_offer.status.value in ("created", "already_exists"), active_offer
            conn.commit()
            active_publish = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0060-ACTIVE"),
            )
            assert active_publish.status.value == "transitioned", active_publish
            active_reconfirm = reconfirm_native_listing(
                conn,
                confirmation_id=FreshnessConfirmationId("CONF-0060-ACTIVE"),
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0060-ACTIVE"),
            )
            assert active_reconfirm.status.value == "reconfirmed", active_reconfirm

            create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0060-WD")))
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0060-WD"), physical_boat_id=PhysicalBoatId("PB-0060-WD")
                ),
            )
            wd_create = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                listing=NativeListing(
                    id=NativeListingId("NL-0060-WD"),
                    market_episode_id=MarketEpisodeId("ME-0060-WD"),
                ),
            )
            assert wd_create.status.value in ("created", "already_exists"), wd_create
            wd_offer = write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0060-WD"),
                revision_id=NativeListingOfferRevisionId("REV-0060-WD"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.POA,
                    location_country="FR",
                    broker_description="Price on application.",
                ),
            )
            assert wd_offer.status.value in ("created", "already_exists"), wd_offer
            conn.commit()
            wd_publish = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0060-WD"),
            )
            assert wd_publish.status.value == "transitioned", wd_publish
            wd_withdraw = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0060-WD"),
            )
            assert wd_withdraw.status.value == "transitioned", wd_withdraw

            # ORG_B: one listing owned by a different (never-logged-in-here)
            # Account -- must never appear in ORG_A's inventory.
            other_result = create_native_listing(
                conn,
                account_id=other_account_id,
                candidate_organization=org_b,
                membership=membership_b_other,
                listing=NativeListing(id=NativeListingId("NL-0060-FOREIGN")),
            )
            assert other_result.status.value in ("created", "already_exists"), other_result

            # Explicit deterministic created_at spacing: WITHDRAWN newest,
            # then ACTIVE, then DRAFT oldest.
            base = datetime(2026, 1, 1, tzinfo=UTC)
            _set_created_at(conn, listing_id="NL-0060-DRAFT", created_at=base)
            _set_created_at(conn, listing_id="NL-0060-ACTIVE", created_at=base + timedelta(days=1))
            _set_created_at(conn, listing_id="NL-0060-WD", created_at=base + timedelta(days=2))
            conn.commit()
        finally:
            conn.close()
        print("6. seeded ORG_A (DRAFT/ACTIVE/WITHDRAWN), ORG_B (foreign listing), ORG_EMPTY -> OK")

        # 7. privileged (PUBLISHER) membership without MFA is blocked.
        status, _, body = session.get(f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory")
        step7_ok = status == 403 and _json(body).get("error") == "mfa_required"
        ok &= step7_ok
        print(f"7. privileged membership without MFA blocked -> {'OK' if step7_ok else 'FAIL'}")

        # 8. cross-Organization / never-created Organization are identical, non-enumerating 404s.
        status_b, _, body_b = session.get(
            f"{api_base}/api/broker/organizations/{_ORG_B_ID}/inventory"
        )
        status_never, _, body_never = session.get(
            f"{api_base}/api/broker/organizations/{_NEVER_SEEDED_ORG_ID}/inventory"
        )
        step8_ok = status_b == 404 and status_never == 404 and body_b == body_never
        ok &= step8_ok
        print(
            f"8. unauthorized-existing and never-created Organization inventory reads "
            f"are identical 404s -> {'OK' if step8_ok else 'FAIL'}\n"
        )

        # MFA step-up.
        stepup_login_url = (
            f"{api_base}/api/auth/login?next=/broker&login_hint={_SUBJECT}"
            f"&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        session.follow_full_login(stepup_login_url)

        # 9. authorized, zero-listing Organization renders ordinary empty inventory.
        status, _, body = session.get(
            f"{api_base}/api/broker/organizations/{_ORG_EMPTY_ID}/inventory"
        )
        step9_ok = status == 200 and _json(body) == {"items": []}
        ok &= step9_ok
        print(
            f"9. authorized zero-listing Organization is ordinary empty inventory, "
            f"not an error -> {'OK' if step9_ok else 'FAIL'}"
        )

        # 10/11/12: deterministic order + keyset pagination + no cross-org leak.
        page1_status, _, page1_body = session.get(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory?page_size=2"
        )
        page1 = _json(page1_body)
        page1_ids = [item["native_listing_id"] for item in page1["items"]]
        step10_ok = (
            page1_status == 200
            and page1_ids == ["NL-0060-WD", "NL-0060-ACTIVE"]
            and "next_cursor" in page1
        )
        ok &= step10_ok
        print(
            f"10. deterministic created_at DESC order, first page (size=2) -> "
            f"{'OK' if step10_ok else 'FAIL'}"
        )

        page2_status, _, page2_body = session.get(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory"
            f"?page_size=2&cursor={page1['next_cursor']}"
        )
        page2 = _json(page2_body)
        page2_ids = [item["native_listing_id"] for item in page2["items"]]
        step11_ok = (
            page2_status == 200 and page2_ids == ["NL-0060-DRAFT"] and "next_cursor" not in page2
        )
        ok &= step11_ok
        print(
            f"11. keyset continuation returns the remaining page, no next_cursor -> "
            f"{'OK' if step11_ok else 'FAIL'}"
        )

        all_ids = page1_ids + page2_ids
        step12_ok = len(all_ids) == len(set(all_ids)) and "NL-0060-FOREIGN" not in all_ids
        ok &= step12_ok
        print(
            f"12. no duplicate rows across pages, ORG_B's listing never appears -> "
            f"{'OK' if step12_ok else 'FAIL'}\n"
        )

        # 13. malformed cursor fails closed as a bounded client error.
        status, _, _ = session.get(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory?cursor=not-a-real-cursor!!"
        )
        step13_ok = status == 400
        ok &= step13_ok
        print(f"13. malformed cursor fails closed (400) -> {'OK' if step13_ok else 'FAIL'}")

        # 14. exact lifecycle/offer/freshness/public-link facts.
        by_id = {item["native_listing_id"]: item for item in page1["items"] + page2["items"]}
        active_item = by_id["NL-0060-ACTIVE"]
        draft_item = by_id["NL-0060-DRAFT"]
        wd_item = by_id["NL-0060-WD"]
        step14_ok = (
            active_item["lifecycle_state"] == "ACTIVE"
            and active_item["offer"] == {"kind": "AMOUNT", "amount": "125000.00", "currency": "EUR"}
            and active_item["freshness_status"] == "CONFIRMED"
            and active_item["is_publicly_listed"] is True
            and draft_item["lifecycle_state"] == "DRAFT"
            and draft_item["offer"]
            == {"kind": "NO_CURRENT_OFFER", "amount": None, "currency": None}
            and draft_item["freshness_status"] == "UNKNOWN"
            and draft_item["is_publicly_listed"] is False
            and wd_item["lifecycle_state"] == "WITHDRAWN"
            and wd_item["lifecycle_state"] != "SOLD"
            and wd_item["offer"] == {"kind": "POA", "amount": None, "currency": None}
            and wd_item["is_publicly_listed"] is False
        )
        ok &= step14_ok
        print(
            f"14. exact lifecycle/offer/freshness facts + public link only for the "
            f"eligible ACTIVE item -> {'OK' if step14_ok else 'FAIL'}\n"
        )

        # 15. revoked membership fails closed immediately, no re-login.
        conn = psycopg.connect(url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-0060-A"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()
        status, _, _ = session.get(f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory")
        step15_ok = status == 404
        ok &= step15_ok
        print(
            f"15. revoked membership (same still-valid session) denies immediately -> "
            f"{'OK' if step15_ok else 'FAIL'}"
        )
        conn = psycopg.connect(url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("OM-0060-A"), MembershipState.ACTIVE
            )
            conn.commit()
        finally:
            conn.close()

        # 16. built Astro SSR inventory page: private/no-store/noindex + factual rendering.
        web_status, web_headers, web_body = session.get(
            f"{web_base}/broker/organizations/{_ORG_A_ID}/inventory"
        )
        page_text = web_body.decode("utf-8")
        step16_ok = (
            web_status == 200
            and "NL-0060-ACTIVE" in page_text
            and "ACTIVE" in page_text
            and "View public listing" in page_text
            and f"/listings/{quote('NL-0060-ACTIVE')}" in page_text
            and "NL-0060-FOREIGN" not in page_text
            and web_headers.get("Cache-Control") == "private, no-store"
            and web_headers.get("X-Robots-Tag") == "noindex"
        )
        ok &= step16_ok
        print(
            f"16. built Astro SSR inventory page renders factual state, "
            f"private/no-store/noindex -> {'OK' if step16_ok else 'FAIL'}\n"
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

        print(f"PROFESSIONAL INVENTORY OVERVIEW RESULT -> {'PASS' if ok else 'FAIL'}")
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
