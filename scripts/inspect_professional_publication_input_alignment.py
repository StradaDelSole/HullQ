"""SLICE-0065 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the committed professional-publication-input-alignment vertical
against a real, disposable PostgreSQL 18 schema and real local HTTP servers
(a deterministic local OIDC/JWKS test issuer, FastAPI, and the built Astro/
Node SSR web package) -- mirroring `scripts/inspect_professional_listing_
draft_workspace.py`'s identical real browser-style login discipline for the
professional-draft portion, and `scripts/inspect_first_buyer_critical_
physical_boat_truth.py`'s identical direct-persistence-call discipline for
the PhysicalBoat claim portion (SLICE-0065 does not add an HTTP route for
claim writes; none existed before this slice either).

Per `specs/PROFESSIONAL_PUBLICATION_INPUT_ALIGNMENT_CONTRACT.v0.1.md` §13,
demonstrates:

    1. create/update/reopen a professional draft containing broker_description
    2. broker edit page visibly renders/reuses the value
    3. local recovery wiring includes the new field without auth leakage
    4. owner-direct retained proof remains unchanged/green (verified
       separately by also running scripts/inspect_owner_direct_draft.py --
       not duplicated here)
    5. write/read a PhysicalBoat claim revision with boat-name VALUE_ASSERTION
    6. write/read explicit ABSENT and UNKNOWN cases
    7. prove Organization-isolated current heads remain independent
    8. prove professional draft saves create no PhysicalBoat/MarketEpisode/
       NativeListing/offer/claim/publication state
    9. exact retry compatibility for a pre-migration seven-field claim
       revision
    10. run retained professional draft, PhysicalBoat-claim and SLICE-0064
        lifecycle non-regression proofs (verified separately by the existing
        pytest suite and scripts/inspect_professional_listing_draft_
        workspace.py / scripts/inspect_professional_inventory_lifecycle_
        controls.py -- not duplicated here)
    11. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_professional_publication_input_alignment.py
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

_SUBJECT_A = "publication-input-alignment-0065-subject-a"
_SESSION_COOKIE_NAME = "hullq_session"
_ORG_A_ID = "ORG-0065-A"
_CSRF_HEADER_VALUE = "professional-listing-draft-v1"

#: Mirrors the identical rationale in `scripts/inspect_professional_listing_
#: draft_workspace.py`: the current-schema table set that carries
#: marketplace identity/inventory, NativeListing offer revision/fact,
#: PhysicalBoat claim, and durable public Search-affecting NativeListing
#: state.
_NON_PROMOTION_TABLES = (
    "physical_boats",
    "market_episodes",
    "native_listings",
    "native_listing_offer_revisions",
    "native_listing_offer_heads",
    "native_listing_publication_transitions",
    "native_listing_freshness_confirmations",
    "physical_boat_claim_revisions",
    "physical_boat_claim_heads",
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
    redirect-following and no exception raised for a non-2xx status."""

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
        return response.status, response.headers, response.read()

    def get(
        self, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url, extra_headers=extra_headers)

    def post_form(
        self, url: str, fields: dict[str, str], *, origin: str
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/x-www-form-urlencoded", "Origin": origin}
        return self.request(
            "POST", url, extra_headers=headers, data=urlencode(fields).encode("utf-8")
        )

    def put_json(
        self, url: str, payload: dict[str, Any], *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        headers = {"Content-Type": "application/json", **(extra_headers or {})}
        return self.request(
            "PUT", url, extra_headers=headers, data=json.dumps(payload).encode("utf-8")
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
    schema_name = f"hullq_s0065e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0065_e2e_"))
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
            BoatNameClaim,
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
        from hullq.persistence.fingerprint import fingerprint_dict
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.native_listing_offer import (
            NativeListingOfferRevisionId,
            write_native_listing_offer_revision,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.persistence.physical_boat_claims import (
            PhysicalBoatClaimWriteStatus,
            fetch_current_physical_boat_claim,
            list_physical_boat_claim_revisions,
            write_physical_boat_claim_revision,
        )
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("PROFESSIONAL PUBLICATION INPUT ALIGNMENT\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK\n")

        before_non_promotion_counts = _non_promotion_table_counts(url)

        # ------------------------------------------------------------------
        # Part A: professional-draft broker_description, end to end through
        # real OIDC login + FastAPI + built Astro.
        # ------------------------------------------------------------------

        issuer_host = "127.0.0.1"
        issuer_port = _free_port(issuer_host)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{issuer_host}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-publication-input-alignment-e2e-client"
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
            print("PROFESSIONAL PUBLICATION INPUT ALIGNMENT RESULT -> FAIL")
            return 1

        drafts_path_a = f"/broker/organizations/{_ORG_A_ID}/drafts"

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
            f"4. Account A real OIDC login (MFA-satisfied) -> {'OK' if login_redirect_ok else 'FAIL'}"
        )

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
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0065-A"),
                    account_id=AccountId(account_a_id),
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print("5. seeded ORG_A (Account A, PUBLISHER) -> OK\n")

        # 1. create a draft, then update it with broker_description.
        status, headers, _ = session_a.post_form(f"{web_base}{drafts_path_a}", {}, origin=web_base)
        create_redirect_ok = status == 303 and headers.get("Location", "").startswith(
            f"{drafts_path_a}/"
        )
        ok &= create_redirect_ok
        draft_path = headers.get("Location", "")
        draft_id = draft_path.rsplit("/", 1)[-1]
        print(
            f"6. ORG_A creates a draft -> {'OK' if create_redirect_ok else 'FAIL'} (draft_id={draft_id})"
        )

        description_text = "A lovely, well-maintained cruising sloop with recent upgrades."
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {
                "expected_version": "1",
                "physical_boat.boat_name": "Sea Breeze",
                "listing_offer.broker_description": description_text,
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        save_ok = status == 200 and "Saved." in page_text and description_text in page_text
        ok &= save_ok
        print(f"7. ORG_A saves listing_offer.broker_description -> {'OK' if save_ok else 'FAIL'}")

        # reopen (Astro) + reopen (FastAPI direct) -- exact durable round-trip.
        status, _, body = session_a.get(f"{web_base}{draft_path}")
        page_text = body.decode("utf-8")
        reload_ok = status == 200 and description_text in page_text and "Version: 2" in page_text

        api_drafts_path_a = f"{api_base}/api/broker/organizations/{_ORG_A_ID}/drafts"
        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        api_record = _json(body)
        api_durable_ok = (
            status == 200
            and api_record["version"] == 2
            and api_record["listing_offer.broker_description"] == description_text
        )
        ok &= reload_ok and api_durable_ok
        print(
            f"8. reload/reopen (Astro edit page + direct FastAPI read) returns the exact durable "
            f"broker_description value -> {'OK' if (reload_ok and api_durable_ok) else 'FAIL'}\n"
        )

        # 2/3. recovery wiring includes the new field, no session leakage.
        recovery_wiring_ok = (
            'name="listing_offer.broker_description"' in page_text
            and 'id="draft-recovery-banner"' in page_text
            and f'data-account-id="{account_a_id}"' in page_text
            and f'data-organization-id="{_ORG_A_ID}"' in page_text
            and f'data-draft-id="{draft_id}"' in page_text
        )
        session_cookie_value = next(
            (cookie.value for cookie in session_a.jar if cookie.name == _SESSION_COOKIE_NAME), None
        )
        recovery_no_leak_ok = (
            session_cookie_value is not None and session_cookie_value not in page_text
        )
        ok &= recovery_wiring_ok and recovery_no_leak_ok
        print(
            f"9. built edit page's recovery form carries the new "
            f"listing_offer.broker_description control under the exact "
            f"Account/Organization/draft scope, with no session-cookie leakage -> "
            f"{'OK' if (recovery_wiring_ok and recovery_no_leak_ok) else 'FAIL'}\n"
        )

        # whitespace-only description is rejected without mutation. Hits the
        # FastAPI JSON boundary directly (not the Astro form POST), which
        # trims blank fields to omission client-side before ever reaching
        # FastAPI -- exactly like every other bounded text field on this
        # form (contract §4.1's trim/non-empty rule is enforced at the
        # professional-draft write boundary, i.e. FastAPI/domain, not by the
        # browser's own pre-submission trimming).
        status, _, _ = session_a.put_json(
            f"{api_drafts_path_a}/{draft_id}",
            {"expected_version": 2, "listing_offer.broker_description": "   "},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        rejects_blank_ok = status == 400
        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        still_v2_ok = _json(body)["version"] == 2
        ok &= rejects_blank_ok and still_v2_ok
        print(
            f"10. whitespace-only broker_description is rejected (400) without mutation "
            f"(still v2) -> {'OK' if (rejects_blank_ok and still_v2_ok) else 'FAIL'}\n"
        )

        # 8 (contract §13 item 8): professional draft saves create zero
        # marketplace truth rows/state.
        after_draft_counts = _non_promotion_table_counts(url)
        no_marketplace_state_from_draft_ok = before_non_promotion_counts == after_draft_counts
        ok &= no_marketplace_state_from_draft_ok
        print(
            f"11. professional draft create/save/reject created zero marketplace truth rows "
            f"-> {'OK' if no_marketplace_state_from_draft_ok else 'FAIL'} "
            f"({before_non_promotion_counts} -> {after_draft_counts})\n"
        )

        # ------------------------------------------------------------------
        # Part B: PhysicalBoat boat-name claims -- direct persistence calls,
        # mirroring scripts/inspect_first_buyer_critical_physical_boat_truth.py
        # (SLICE-0065 adds no new HTTP claim-write route; none existed
        # before this slice either).
        # ------------------------------------------------------------------

        def _org(value: str) -> MarketplaceOrganization:
            return MarketplaceOrganization(
                id=MarketplaceOrganizationId(value),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )

        def _membership(
            membership_id: str, account: Any, org: MarketplaceOrganization
        ) -> OrganizationMembership:
            return OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

        account_x = AccountId("ACC-0065-X")
        org_x = _org("ORG-0065-X")
        membership_x = _membership("OM-0065-X", account_x, org_x)
        account_y = AccountId("ACC-0065-Y")
        org_y = _org("ORG-0065-Y")
        membership_y = _membership("OM-0065-Y", account_y, org_y)

        physical_boat_id = "PB-0065-X"

        conn = psycopg.connect(url)
        try:
            create_physical_boat(
                conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id))
            )

            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0065-X"),
                    physical_boat_id=PhysicalBoatId(physical_boat_id),
                ),
            )
            create_native_listing(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                listing=NativeListing(
                    id=NativeListingId("NL-0065-X"), market_episode_id=MarketEpisodeId("ME-0065-X")
                ),
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                native_listing_id=NativeListingId("NL-0065-X"),
                revision_id=NativeListingOfferRevisionId("REV-0065-X"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop.",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )

            # A second Organization's own NativeListing/offer for the SAME
            # PhysicalBoat, so Organization-isolated current heads can be
            # proven independent (item 7).
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0065-Y"),
                    physical_boat_id=PhysicalBoatId(physical_boat_id),
                ),
            )
            create_native_listing(
                conn,
                account_id=account_y,
                candidate_organization=org_y,
                membership=membership_y,
                listing=NativeListing(
                    id=NativeListingId("NL-0065-Y"), market_episode_id=MarketEpisodeId("ME-0065-Y")
                ),
            )

            def _base_claims(**overrides: Any) -> PhysicalBoatClaimSnapshot:
                kwargs: dict[str, Any] = {
                    "marketed_brand_claim": "Beneteau",
                    "model_designation_claim": "Oceanis 30.1",
                    "build_year": BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                }
                kwargs.update(overrides)
                return PhysicalBoatClaimSnapshot(**kwargs)

            # 5. VALUE_ASSERTION write/read.
            value_assertion_result = write_physical_boat_claim_revision(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                native_listing_id=NativeListingId("NL-0065-X"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0065-X-001"),
                expected_current_revision_id=None,
                claims=_base_claims(
                    boat_name=BoatNameClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value="Sea Breeze"
                    )
                ),
            )
            conn.commit()
            current_x = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId(physical_boat_id), org_x.id
            )
            conn.commit()
            step5_ok = (
                value_assertion_result.status is PhysicalBoatClaimWriteStatus.CREATED
                and current_x is not None
                and current_x.claims.boat_name is not None
                and current_x.claims.boat_name.assertion_kind is AssertionKind.VALUE_ASSERTION
                and current_x.claims.boat_name.value == "Sea Breeze"
            )
            ok &= step5_ok
            print(f"12. boat_name VALUE_ASSERTION write/read -> {'OK' if step5_ok else 'FAIL'}")

            # 6. explicit ABSENT and UNKNOWN, via a same-authority correction.
            absent_result = write_physical_boat_claim_revision(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                native_listing_id=NativeListingId("NL-0065-X"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0065-X-002"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-0065-X-001"),
                claims=_base_claims(boat_name=BoatNameClaim(assertion_kind=AssertionKind.ABSENT)),
            )
            conn.commit()
            current_after_absent = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId(physical_boat_id), org_x.id
            )
            conn.commit()
            step6a_ok = (
                absent_result.status is PhysicalBoatClaimWriteStatus.REVISED
                and current_after_absent is not None
                and current_after_absent.claims.boat_name is not None
                and current_after_absent.claims.boat_name.assertion_kind is AssertionKind.ABSENT
                and current_after_absent.claims.boat_name.value is None
            )

            unknown_result = write_physical_boat_claim_revision(
                conn,
                account_id=account_y,
                candidate_organization=org_y,
                membership=membership_y,
                native_listing_id=NativeListingId("NL-0065-Y"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0065-Y-001"),
                expected_current_revision_id=None,
                claims=_base_claims(
                    marketed_brand_claim="Jeanneau",
                    boat_name=BoatNameClaim(assertion_kind=AssertionKind.UNKNOWN),
                ),
            )
            conn.commit()
            current_y = fetch_current_physical_boat_claim(
                conn, PhysicalBoatId(physical_boat_id), org_y.id
            )
            conn.commit()
            step6b_ok = (
                unknown_result.status is PhysicalBoatClaimWriteStatus.CREATED
                and current_y is not None
                and current_y.claims.boat_name is not None
                and current_y.claims.boat_name.assertion_kind is AssertionKind.UNKNOWN
                and current_y.claims.boat_name.value is None
            )
            ok &= step6a_ok and step6b_ok
            print(
                f"13. boat_name explicit ABSENT (ORG_X correction) and explicit UNKNOWN (ORG_Y) "
                f"write/read -> {'OK' if (step6a_ok and step6b_ok) else 'FAIL'}"
            )

            # 7. Organization-isolated current heads remain independent: the
            # same PhysicalBoat's two claiming Organizations disagree
            # (ABSENT vs UNKNOWN vs differing brand) with zero cross-talk.
            step7_ok = (
                current_after_absent is not None
                and current_y is not None
                and current_after_absent.claims.marketed_brand_claim == "Beneteau"
                and current_y.claims.marketed_brand_claim == "Jeanneau"
                and current_after_absent.claims.boat_name.assertion_kind is AssertionKind.ABSENT
                and current_y.claims.boat_name.assertion_kind is AssertionKind.UNKNOWN
            )
            ok &= step7_ok
            print(
                f"14. Organization-isolated current heads for the same PhysicalBoat remain "
                f"fully independent -> {'OK' if step7_ok else 'FAIL'}\n"
            )

            # 9. exact retry compatibility for a pre-migration seven-field
            # claim revision: insert a row using the exact pre-0065
            # fingerprint envelope shape (no "boat_name" key at all), then
            # retry it through the current write path with boat_name
            # omitted -- must resolve ALREADY_EXISTS, never CONFLICT.
            create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0065-PRE")))
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0065-PRE"),
                    physical_boat_id=PhysicalBoatId("PB-0065-PRE"),
                ),
            )
            create_native_listing(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                listing=NativeListing(
                    id=NativeListingId("NL-0065-PRE"),
                    market_episode_id=MarketEpisodeId("ME-0065-PRE"),
                ),
            )
            conn.commit()

            pre_0065_envelope = {
                "physical_boat_id": "PB-0065-PRE",
                "claiming_organization_id": org_x.id.value,
                "recorded_by_account_id": account_x.value,
                "marketed_brand_claim": "Beneteau",
                "model_designation_claim": "Oceanis 30.1",
                "build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2021},
                "loa_length": None,
                "draft": None,
                "keel_configuration": None,
                "rudder_configuration": None,
            }
            pre_0065_hash = fingerprint_dict(pre_0065_envelope)
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO physical_boat_claim_revisions ("
                    "claim_revision_id, physical_boat_id, claiming_organization_id, "
                    "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
                    "build_year_assertion_kind, build_year_value, previous_claim_revision_id, "
                    "content_hash"
                    ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (
                        "PBCREV-0065-PRE-001",
                        "PB-0065-PRE",
                        org_x.id.value,
                        account_x.value,
                        "Beneteau",
                        "Oceanis 30.1",
                        "VALUE_ASSERTION",
                        2021,
                        None,
                        pre_0065_hash,
                    ),
                )
                cur.execute(
                    "INSERT INTO physical_boat_claim_heads "
                    "(physical_boat_id, claiming_organization_id, current_claim_revision_id) "
                    "VALUES (%s, %s, %s)",
                    ("PB-0065-PRE", org_x.id.value, "PBCREV-0065-PRE-001"),
                )
            conn.commit()

            pre_migration_retry = write_physical_boat_claim_revision(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                native_listing_id=NativeListingId("NL-0065-PRE"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-0065-PRE-001"),
                expected_current_revision_id=None,
                claims=_base_claims(),  # boat_name omitted, exactly like the pre-0065 row
            )
            conn.commit()
            history_pre = list_physical_boat_claim_revisions(
                conn, PhysicalBoatId("PB-0065-PRE"), org_x.id
            )
            conn.commit()
            step9_ok = (
                pre_migration_retry.status is PhysicalBoatClaimWriteStatus.ALREADY_EXISTS
                and pre_migration_retry.current_revision_id
                == PhysicalBoatClaimRevisionId("PBCREV-0065-PRE-001")
                and len(history_pre) == 1
            )
            ok &= step9_ok
            print(
                f"15. exact retry of a pre-migration seven-field claim revision (boat_name omitted "
                f"on both sides) remains ALREADY_EXISTS, never CONFLICT -> {'OK' if step9_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        # 8 (repeat over the full Part B activity too): claim writes never
        # touch professional_listing_drafts, and no NativeListing was ever
        # published/promoted from a draft.
        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT to_state FROM native_listing_publication_transitions")
                any_publication_transition = cur.fetchall()
        finally:
            conn.close()
        step8b_ok = any_publication_transition == []
        ok &= step8b_ok
        print(
            f"16. zero NativeListing publication transitions occurred anywhere in this proof "
            f"(claim recording is not publication) -> {'OK' if step8b_ok else 'FAIL'}\n"
        )

        print(
            "    item 4 (existing owner-direct retained proof still passes) and item 10 "
            "(existing professional-draft/PhysicalBoat-claim/SLICE-0064-lifecycle non-regression) "
            "are verified separately by the existing pytest suite and by also running "
            "scripts/inspect_owner_direct_draft.py, "
            "scripts/inspect_professional_listing_draft_workspace.py and "
            "scripts/inspect_professional_inventory_lifecycle_controls.py -- not duplicated here.\n"
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

        print(f"PROFESSIONAL PUBLICATION INPUT ALIGNMENT RESULT -> {'PASS' if ok else 'FAIL'}")
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
