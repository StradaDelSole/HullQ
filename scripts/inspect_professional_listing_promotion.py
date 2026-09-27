"""SLICE-0067 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the committed professional-draft-atomic-promotion vertical against a
real, disposable PostgreSQL 18 schema and real local HTTP servers (a
deterministic local OIDC/JWKS test issuer, FastAPI, and the built Astro/Node
SSR web package) -- mirroring `scripts/inspect_professional_publication_
input_alignment.py`'s identical real browser-style login discipline.

Per `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`, demonstrates:

    1. create + fill a professional draft to PromotionReadiness via the
       built Astro edit page, showing the server-owned readiness reasons
       shrink to zero as the required fields are supplied
    2. independent exact-head review Finding B: a failed promotion attempt
       (stale expected_version) never claims/clears promoted browser-local
       recovery state and leaves the draft EDITABLE, unmutated
    3. promote via the Astro "Create listing" action -> real FastAPI
       promotion transaction -> the SAME response re-renders the immutable
       PROMOTED state (no redirect, so the recovery-clear script runs
       deterministically on this exact response, contract §12), showing
       the resulting NativeListingId, DRAFT/not-public wording and a link
       (not a forced navigation) to the Organization inventory
    4. exact retry (same expected_version) re-renders the identical
       immutable state (ALREADY_PROMOTED) with the same NativeListingId and
       zero additional durable rows
    5. reopening the promoted draft shows immutable provenance and no
       editable Save/Promote controls; a direct FastAPI PUT against it is
       rejected as promoted_immutable with zero mutation
    6. the promoted NativeListing is not reachable through the public
       listing read route (DRAFT is never public)
    7. D09: a second NativeListing for the same Organization + resolved
       MarketEpisode is rejected at the low-level persistence boundary;
       a different Organization may still use the same MarketEpisode
    8. representative failure-injection rollback: an injected failure deep
       in the promotion transaction leaves zero PhysicalBoat/MarketEpisode/
       NativeListing/claim/offer rows and the draft still EDITABLE at its
       original version
    9. exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_professional_listing_promotion.py
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

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_SUBJECT_A = "promotion-0067-subject-a"
_SESSION_COOKIE_NAME = "hullq_session"
_ORG_A_ID = "ORG-0067-A"
_CSRF_HEADER_VALUE = "professional-listing-draft-v1"

_MARKETPLACE_TABLES = (
    "physical_boats",
    "market_episodes",
    "native_listings",
    "native_listing_offer_revisions",
    "native_listing_offer_heads",
    "native_listing_publication_transitions",
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


def _table_counts(url: str) -> dict[str, int]:
    conn = psycopg.connect(url)
    try:
        counts: dict[str, int] = {}
        with conn.cursor() as cur:
            for table in _MARKETPLACE_TABLES:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                row = cur.fetchone()
                assert row is not None
                counts[table] = row[0]
        return counts
    finally:
        conn.close()


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
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
    schema_name = f"hullq_s0067e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0067_e2e_"))
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
        from hullq.persistence.native_listing import (
            NativeListingCreationStatus,
            create_native_listing,
        )
        from hullq.persistence.physical_boat import create_physical_boat
        from hullq.persistence.professional_listing_draft import (
            fetch_professional_listing_draft,
        )
        from hullq.persistence.professional_listing_promotion import (
            promote_professional_listing_draft,
        )
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("PROFESSIONAL DRAFT ATOMIC PROMOTION\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK\n")

        issuer_host = "127.0.0.1"
        issuer_port = _free_port(issuer_host)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{issuer_host}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-promotion-e2e-client"
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
            print("PROFESSIONAL DRAFT ATOMIC PROMOTION RESULT -> FAIL")
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
                    id=OrganizationMembershipId("OM-0067-A"),
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

        # 1. create a draft, then fill it to PromotionReadiness.
        status, headers, _ = session_a.post_form(f"{web_base}{drafts_path_a}", {}, origin=web_base)
        create_ok = status == 303 and headers.get("Location", "").startswith(f"{drafts_path_a}/")
        ok &= create_ok
        draft_path = headers.get("Location", "")
        draft_id = draft_path.rsplit("/", 1)[-1]
        print(f"6. ORG_A creates a draft -> {'OK' if create_ok else 'FAIL'} (draft_id={draft_id})")

        api_drafts_path_a = f"{api_base}/api/broker/organizations/{_ORG_A_ID}/drafts"

        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        not_ready_before = _json(body)["promotion_readiness"]
        step7_ok = (
            not_ready_before["ready"] is False
            and "MISSING_MARKETED_BRAND" in not_ready_before["reasons"]
        )
        ok &= step7_ok
        print(
            f"7. empty draft shows server-owned PromotionReadiness NOT_READY with reasons -> "
            f"{'OK' if step7_ok else 'FAIL'}"
        )

        description_text = "A lovely, well-maintained cruising sloop with recent upgrades."
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {
                "intent": "save",
                "expected_version": "1",
                "physical_boat.marketed_brand_claim": "Beneteau",
                "physical_boat.model_designation_claim": "Oceanis 30.1",
                "physical_boat.build_year.assertion_kind": "VALUE_ASSERTION",
                "physical_boat.build_year": "2021",
                "listing_offer.asking_price_mode": "AMOUNT",
                "listing_offer.asking_price_amount": "125000",
                "listing_offer.currency": "EUR",
                "listing_offer.location_country": "FR",
                "listing_offer.broker_description": description_text,
            },
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        save_ok = status == 200 and "ready to promote" in page_text
        ok &= save_ok
        print(f"8. ORG_A fills the draft to PromotionReadiness -> {'OK' if save_ok else 'FAIL'}\n")

        # 8b. Independent exact-head review Finding B item 5: a failed
        # promotion attempt (here, a stale expected_version) must NOT clear
        # browser-local recovery -- the rendered response must not carry
        # the promoted recovery-clear marker, and the draft must remain
        # EDITABLE, unmutated.
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {"intent": "promote", "expected_version": "999"},
            origin=web_base,
        )
        failed_page_text = body.decode("utf-8")
        step8b_ok = (
            status == 200
            and "Please reload before promoting" in failed_page_text
            and 'data-promoted="1"' not in failed_page_text
        )
        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        step8b_state_ok = _json(body)["promotion_state"] == "EDITABLE"
        ok &= step8b_ok and step8b_state_ok
        print(
            f"8b. a failed promotion attempt (stale expected_version) never clears/claims "
            f"promoted recovery state, draft remains EDITABLE -> "
            f"{'OK' if (step8b_ok and step8b_state_ok) else 'FAIL'}\n"
        )

        before_marketplace_counts = _table_counts(url)

        # 2. promote via the Astro "Create listing" action. Independent
        # exact-head review Finding B: successful promotion no longer
        # redirects away -- it re-renders THIS same response as the
        # immutable PROMOTED state (so the client-side recovery-clear
        # script deterministically runs on this exact response, contract
        # §12), and only links to (never force-navigates to) the
        # Organization inventory surface.
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {"intent": "promote", "expected_version": "2"},
            origin=web_base,
        )
        page_text = body.decode("utf-8")
        promote_rendered_ok = (
            status == 200
            and "Promotion succeeded." in page_text
            and "Promoted." in page_text
            and "DRAFT" in page_text
            and "not public" in page_text
            and f'href="/broker/organizations/{_ORG_A_ID}/inventory"' in page_text
            and 'data-promoted="1"' in page_text
        )
        match = re.search(r"<code>([^<]+)</code>", page_text)
        native_listing_id = match.group(1) if match else None
        after_promote_counts = _table_counts(url)
        promote_wrote_rows_ok = all(
            after_promote_counts[table] == before_marketplace_counts[table] + 1
            for table in (
                "physical_boats",
                "market_episodes",
                "native_listings",
                "native_listing_offer_revisions",
                "native_listing_offer_heads",
                "physical_boat_claim_revisions",
                "physical_boat_claim_heads",
            )
        )
        ok &= promote_rendered_ok and promote_wrote_rows_ok
        print(
            f"9. successful promotion re-renders the immutable PROMOTED state in the same "
            f"response (no redirect), showing the resulting NativeListingId, DRAFT/not-public "
            f"wording, an inventory link and the recovery banner's promoted marker (so the "
            f"browser-local recovery envelope is cleared deterministically), and creates "
            f"exactly one PhysicalBoat/MarketEpisode/NativeListing/claim/offer head each -> "
            f"{'OK' if (promote_rendered_ok and promote_wrote_rows_ok) else 'FAIL'} "
            f"(native_listing_id={native_listing_id})"
        )

        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        promoted_record = _json(body)
        step9b_ok = (
            promoted_record["promotion_state"] == "PROMOTED"
            and promoted_record.get("promoted_native_listing_id") == native_listing_id
            and promoted_record["version"] == 2
        )
        ok &= step9b_ok
        print(
            f"10. direct FastAPI reopen of the draft shows identical immutable provenance, "
            f"frozen version -> {'OK' if step9b_ok else 'FAIL'}\n"
        )

        status, _, body = session_a.get(
            f"{api_base}/api/broker/organizations/{_ORG_A_ID}/inventory"
        )
        inventory = _json(body)
        matching = [
            item for item in inventory["items"] if item["native_listing_id"] == native_listing_id
        ]
        step10_ok = len(matching) == 1 and matching[0]["lifecycle_state"] == "DRAFT"
        ok &= step10_ok
        print(
            f"11. the resulting NativeListing appears in Organization inventory as lifecycle "
            f"DRAFT -> {'OK' if step10_ok else 'FAIL'}"
        )

        status, _, _ = session_a.get(f"{api_base}/api/listings/{native_listing_id}")
        step11_ok = status == 404
        ok &= step11_ok
        print(f"12. the DRAFT listing is not public/current -> {'OK' if step11_ok else 'FAIL'}\n")

        # 3. exact retry (ALREADY_PROMOTED) also re-renders the identical
        # immutable state in the same response -- zero additional rows, and
        # the recovery-clear marker is present again (idempotent, not
        # merely a one-time effect of the original promotion).
        after_first_promotion_counts = _table_counts(url)
        status, headers, body = session_a.post_form(
            f"{web_base}{draft_path}",
            {"intent": "promote", "expected_version": "2"},
            origin=web_base,
        )
        retry_page_text = body.decode("utf-8")
        retry_match = re.search(r"<code>([^<]+)</code>", retry_page_text)
        retry_native_listing_id = retry_match.group(1) if retry_match else None
        retry_ok = (
            status == 200
            and retry_native_listing_id == native_listing_id
            and 'data-promoted="1"' in retry_page_text
        )
        after_retry_counts = _table_counts(url)
        step12_ok = retry_ok and after_retry_counts == after_first_promotion_counts
        ok &= step12_ok
        print(
            f"13. exact retry (same expected_version) re-renders the identical immutable state "
            f"(same NativeListingId, recovery-clear marker present), zero additional durable "
            f"rows -> {'OK' if step12_ok else 'FAIL'}\n"
        )

        # 4. a direct FastAPI PUT against the promoted draft is rejected.
        status, _, _ = session_a.put_json(
            f"{api_drafts_path_a}/{draft_id}",
            {"expected_version": 2, "physical_boat.boat_name": "Sea Breeze"},
            extra_headers={"Origin": web_base, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
        )
        step13_ok = status == 409
        status, _, body = session_a.get(f"{api_drafts_path_a}/{draft_id}")
        step13b_ok = _json(body)["version"] == 2
        ok &= step13_ok and step13b_ok
        print(
            f"14. a further edit attempt against the promoted draft is rejected (409) with zero "
            f"mutation -> {'OK' if (step13_ok and step13b_ok) else 'FAIL'}\n"
        )

        # ------------------------------------------------------------------
        # Part B: D09 uniqueness + failure-injection rollback -- direct
        # persistence calls, mirroring the SLICE-0065 proof's identical
        # discipline for a capability with no dedicated new HTTP surface for
        # this part.
        # ------------------------------------------------------------------

        account_x = AccountId("ACC-0067-X")
        org_x = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-0067-X"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership_x = OrganizationMembership(
            id=OrganizationMembershipId("OM-0067-X"),
            account_id=account_x,
            organization_id=org_x.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        account_y = AccountId("ACC-0067-Y")
        org_y = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-0067-Y"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership_y = OrganizationMembership(
            id=OrganizationMembershipId("OM-0067-Y"),
            account_id=account_y,
            organization_id=org_y.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )

        conn = psycopg.connect(url)
        try:
            create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0067-D09")))
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0067-D09"),
                    physical_boat_id=PhysicalBoatId("PB-0067-D09"),
                ),
            )
            first_listing = create_native_listing(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                listing=NativeListing(
                    id=NativeListingId("NL-0067-D09-X1"),
                    market_episode_id=MarketEpisodeId("ME-0067-D09"),
                ),
            )
            second_same_org = create_native_listing(
                conn,
                account_id=account_x,
                candidate_organization=org_x,
                membership=membership_x,
                listing=NativeListing(
                    id=NativeListingId("NL-0067-D09-X2"),
                    market_episode_id=MarketEpisodeId("ME-0067-D09"),
                ),
            )
            third_different_org = create_native_listing(
                conn,
                account_id=account_y,
                candidate_organization=org_y,
                membership=membership_y,
                listing=NativeListing(
                    id=NativeListingId("NL-0067-D09-Y1"),
                    market_episode_id=MarketEpisodeId("ME-0067-D09"),
                ),
            )
            step14_ok = (
                first_listing.status is NativeListingCreationStatus.CREATED
                and second_same_org.status
                is NativeListingCreationStatus.ORGANIZATION_EPISODE_CONFLICT
                and third_different_org.status is NativeListingCreationStatus.CREATED
            )
            ok &= step14_ok
            print(
                f"15. D09: same-Organization second listing for the same resolved episode is "
                f"rejected; a different Organization remains allowed -> "
                f"{'OK' if step14_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        # 7. representative failure-injection rollback proof.
        import hullq.persistence.professional_listing_promotion as promotion_module

        conn = psycopg.connect(url)
        try:
            org_z = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-0067-Z"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            seed_marketplace_organization(conn, org_z)
            account_z = AccountId("ACC-0067-Z")
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [account_z.value],
                )
            conn.commit()
            membership_z = OrganizationMembership(
                id=OrganizationMembershipId("OM-0067-Z"),
                account_id=account_z,
                organization_id=org_z.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            seed_organization_membership(conn, membership_z)
            conn.commit()

            from hullq.domain.listing_draft_payload import parse_listing_draft_payload
            from hullq.persistence.professional_listing_draft import (
                create_professional_listing_draft,
            )

            failure_draft = create_professional_listing_draft(
                conn,
                owner_organization_id=org_z.id,
                created_by_account_id=account_z,
                broker_listing_reference=None,
                broker_description="A well-kept example vessel.",
                payload=parse_listing_draft_payload(
                    {
                        "physical_boat.marketed_brand_claim": "Jeanneau",
                        "physical_boat.model_designation_claim": "Sun Odyssey 410",
                        "physical_boat.build_year": {
                            "assertion_kind": "VALUE_ASSERTION",
                            "value": 2019,
                        },
                        "listing_offer.asking_price_mode": "POA",
                        "listing_offer.location_country": "ES",
                    }
                ),
            )
            conn.commit()
            before_failure_counts = _table_counts(url)

            def _boom(*_args: Any, **_kwargs: Any) -> Any:
                raise RuntimeError("injected failure after NativeListing insert")

            original = promotion_module.write_physical_boat_claim_revision_row
            promotion_module.write_physical_boat_claim_revision_row = _boom  # type: ignore[assignment]
            try:
                try:
                    promote_professional_listing_draft(
                        conn,
                        account_id=account_z,
                        candidate_organization=org_z,
                        membership=membership_z,
                        draft_id=failure_draft.draft_id,
                        owner_organization_id=org_z.id,
                        expected_version=1,
                    )
                    injected_raised = False
                except RuntimeError:
                    injected_raised = True
            finally:
                promotion_module.write_physical_boat_claim_revision_row = original  # type: ignore[assignment]

            after_failure_counts = _table_counts(url)
            reread = fetch_professional_listing_draft(
                conn,
                draft_id=failure_draft.draft_id,
                owner_organization_id=org_z.id,
            )
            step15_ok = (
                injected_raised
                and after_failure_counts == before_failure_counts
                and reread is not None
                and reread.promotion_state.value == "EDITABLE"
                and reread.version == 1
            )
            ok &= step15_ok
            print(
                f"16. injected failure deep in the promotion transaction rolls back every write "
                f"(PhysicalBoat/MarketEpisode/NativeListing/claim/offer), draft stays EDITABLE "
                f"at its original version -> {'OK' if step15_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        print(
            "    non-regression of the existing professional-draft workspace/publication-input-"
            "alignment/inventory-lifecycle retained proofs is verified separately by also "
            "running scripts/inspect_professional_listing_draft_workspace.py, "
            "scripts/inspect_professional_publication_input_alignment.py and "
            "scripts/inspect_professional_inventory_lifecycle_controls.py -- not duplicated "
            "here.\n"
        )

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
            f"    ordinary API/web logs contain no client/session secret -> "
            f"{'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(f"PROFESSIONAL DRAFT ATOMIC PROMOTION RESULT -> {'PASS' if ok else 'FAIL'}")
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
