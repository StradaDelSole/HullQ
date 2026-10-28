"""SLICE-0095 owner-visible end-to-end proof — real PostgreSQL 18 + real
FastAPI + real built Astro SSR.

The READY contract requires a retained inspector exercising real
PostgreSQL18 + FastAPI + **built Astro SSR** against an ordinary
authenticated broker session: a Power design-unresolved (claim-only)
positive, a design-linked positive, a negative/insufficient outcome with
actionable sources, the original Sail broker preview's non-regression on
the same page, and that the private lifecycle-DRAFT preview never leaks
into the public Power Buyer Search. This script drives the real built
broker `.../inventory/[native_listing_id]/edit` page through authenticated,
same-origin HTTP requests (`urllib` plus a standards-compliant cookie jar
for the real OIDC/session login, mirroring
`scripts/inspect_slice_0093_power_drive_search.py`'s identical discipline)
against a real local OIDC test issuer, a real FastAPI backend and a real
built Astro/Node SSR server, over a real disposable PostgreSQL 18 schema --
this is HTTP-level request/form-GET evidence, not a genuine automated
browser (no JS execution, no DOM rendering, no Playwright/Selenium-style
page automation).

Seeds, all under one authenticated broker Organization/account, all
lifecycle-DRAFT (never published):

    1. NL-0095-INSP-CLAIM: design-unresolved, publisher-owned POWER +
       SHAFT + 2-engine claim -- combined `psf_power_drive=SHAFT&
       psf_power_engine_count=2` resolves CONFIRMED_MATCH,
       source_basis=PUBLISHER_CLAIM.
    2. NL-0095-INSP-LINKED: design-linked (BoatDesign v0.6
       `propulsion.drive_type=shaft`/`engine_count=2`, real admitted
       FieldResolution) with a matching concrete SHAFT+2 claim --
       CONFIRMED_MATCH with real design_evaluation evidence, no
       publisher-claim disclaimer.
    3. NL-0095-INSP-SAIL: design-unresolved, explicit SAIL category --
       CONFIRMED_NON_MATCH with vessel_category_exclusion, never a false
       Power positive.

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``npm ci --prefix web && npm run build --prefix web``).

Run: uv run python scripts/inspect_slice_0095_power_broker_search_fit.py
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
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_ID = "ORG-0095-INSP"


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


def _http_get(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    """A real, standards-compliant cookie-jar HTTP client -- HTTP-level
    request/form evidence only, never a genuine automated browser."""

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
        return response.status, response.headers, response.read()

    def get(
        self, url: str, *, extra_headers: dict[str, str] | None = None
    ) -> tuple[int, http.client.HTTPMessage, bytes]:
        return self.request("GET", url, extra_headers=extra_headers)

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


def _seed(conn: Any, *, account_id: str) -> None:
    from hullq.domain.market_identity import (
        BoatDesignRef,
        MarketEpisode,
        MarketEpisodeId,
        NativeListing,
        NativeListingId,
        PhysicalBoat,
        PhysicalBoatId,
    )
    from hullq.domain.physical_boat_claims import (
        AssertionKind,
        BuildYearClaim,
        PhysicalBoatClaimRevisionId,
        PhysicalBoatClaimSnapshot,
        PowerDriveConfiguration,
        PowerDriveConfigurationClaim,
        PowerEngineCountClaim,
        VesselCategory,
        VesselCategoryClaim,
    )
    from hullq.domain.provenance import SubjectKind
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
    from hullq.persistence.broker_identity import (
        seed_marketplace_organization,
        seed_organization_membership,
    )
    from hullq.persistence.market_episode import create_market_episode
    from hullq.persistence.native_listing import create_native_listing
    from hullq.persistence.physical_boat import create_physical_boat
    from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
    from hullq.search.power_drive_design_bridge import lookup_power_drive_canonical_value
    from hullq.search.power_engine_count_design_bridge import (
        lookup_power_engine_count_canonical_value,
    )

    sys.path.insert(0, str(REPO_ROOT / "tests" / "persistence"))
    from _field_resolution_support import (  # type: ignore[import-not-found]
        admit_resolved_categorical_field,
        admit_resolved_draft_max,
    )

    VA = AssertionKind.VALUE_ASSERTION
    account = AccountId(account_id)
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId(_ORG_ID),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )
    seed_marketplace_organization(conn, org)
    membership = OrganizationMembership(
        id=OrganizationMembershipId("OM-0095-INSP"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    seed_organization_membership(conn, membership)
    conn.commit()

    def _draft_listing(
        listing_id: str,
        physical_boat_id: str,
        market_episode_id: str,
        *,
        boat_design_id: str | None,
        vessel_category: VesselCategoryClaim | None,
        power_drive_configuration: PowerDriveConfigurationClaim | None,
        power_engine_count: PowerEngineCountClaim | None,
    ) -> None:
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id),
                boat_design_ref=BoatDesignRef(boat_design_id) if boat_design_id else None,
            ),
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
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Jeanneau",
                model_designation_claim="Merry Fisher 895",
                build_year=BuildYearClaim(assertion_kind=VA, value=2021),
                vessel_category=vessel_category,
                power_drive_configuration=power_drive_configuration,
                power_engine_count=power_engine_count,
            ),
        )
        conn.commit()

    # 1. design-unresolved, publisher-owned POWER + SHAFT + 2 claim.
    _draft_listing(
        "NL-0095-INSP-CLAIM",
        "PB-0095-INSP-CLAIM",
        "ME-0095-INSP-CLAIM",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )

    # 2. design-linked, v0.6 shaft+count2 FieldResolution + matching claim.
    design_id = "BD-0095-INSP-LINKED"
    model_id = "BM-0095-INSP-LINKED"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": "shaft", "engine_count": 2}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/drive_type",
        value="shaft",
        resolution_id=f"FR-PWRDRV-{design_id}",
        fetch_canonical_value=lookup_power_drive_canonical_value,
    )
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/engine_count",
        value=Decimal(2),
        resolution_id=f"FR-PWRCNT-{design_id}",
        fetch_canonical_value=lookup_power_engine_count_canonical_value,
    )
    _draft_listing(
        "NL-0095-INSP-LINKED",
        "PB-0095-INSP-LINKED",
        "ME-0095-INSP-LINKED",
        boat_design_id=design_id,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )

    # 3. design-unresolved, explicit SAIL -- never a Power positive.
    _draft_listing(
        "NL-0095-INSP-SAIL",
        "PB-0095-INSP-SAIL",
        "ME-0095-INSP-SAIL",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        power_drive_configuration=None,
        power_engine_count=None,
    )


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
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0095_insp_api_", suffix=".log")[1])
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
    sys.stdout.reconfigure(line_buffering=True)
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  npm ci --prefix web && npm run build --prefix web",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0095insp_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0095_insp_"))
    issuer_proc: subprocess.Popen[bytes] | None = None
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.market_identity import PhysicalBoatId
        from hullq.domain.publishing_eligibility import MarketplaceOrganizationId
        from hullq.persistence.alembic_baseline import (
            alembic_upgrade_head,
            prepare_alembic_baseline,
        )
        from hullq.persistence.physical_boat_claims import fetch_current_physical_boat_claim
        from hullq.security.oidc import AUTH0_MFA_STEP_UP_ACR_VALUE

        url = _with_search_path(base_url, schema_name)
        print("SLICE-0095 POWER BROKER PREPUBLICATION SEARCH-FIT PROOF\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic migrated to current head -> OK\n")

        issuer_host = "127.0.0.1"
        issuer_port = _free_port(issuer_host)
        api_port = _free_port()
        web_port = _free_port()
        issuer_base = f"http://{issuer_host}:{issuer_port}/"
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        redirect_uri = f"{api_base}/api/auth/callback"

        client_id = "hullq-power-broker-fit-0095-e2e-client"
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
        api_ready = _wait_for_http(f"{api_base}/api/search/en/power")
        ok &= api_ready
        print(f"2. FastAPI serving -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print("---- api.log ----", file=sys.stderr)
            print(api_log_path.read_text(encoding="utf-8", errors="replace"), file=sys.stderr)

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
        inventory_path = f"/broker/organizations/{_ORG_ID}/inventory"
        web_ready = _wait_for_http(f"{web_base}{inventory_path}")
        ok &= web_ready
        print(f"3. Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("SLICE-0095 PROOF RESULT -> FAIL")
            return 1

        session = BrowserSession()
        login_url = (
            f"{api_base}/api/auth/login?next={quote(inventory_path, safe='')}"
            f"&login_hint=power-broker-fit-0095-subject"
            f"&acr_values={quote(AUTH0_MFA_STEP_UP_ACR_VALUE, safe='')}"
        )
        status, headers, _ = session.follow_full_login(login_url)
        login_ok = status == 302 and headers.get("Location") == f"{web_base}{inventory_path}"
        ok &= login_ok
        print(f"4. real OIDC login (MFA-satisfied) -> {'OK' if login_ok else 'FAIL'}")

        status, _, body = session.get(f"{api_base}/api/broker/context")
        account_id = _json(body)["account_id"]

        conn = psycopg.connect(url)
        try:
            _seed(conn, account_id=account_id)
            print(
                "5. seeded NL-0095-INSP-CLAIM (claim-only POWER+SHAFT+2), "
                "NL-0095-INSP-LINKED (design-linked shaft+2), "
                "NL-0095-INSP-SAIL (explicit SAIL), all lifecycle-DRAFT -> OK\n"
            )
            fingerprint_before = {
                listing_id: fetch_current_physical_boat_claim(
                    conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(_ORG_ID)
                ).revision_id.value
                for listing_id, physical_boat_id in (
                    ("NL-0095-INSP-CLAIM", "PB-0095-INSP-CLAIM"),
                    ("NL-0095-INSP-LINKED", "PB-0095-INSP-LINKED"),
                    ("NL-0095-INSP-SAIL", "PB-0095-INSP-SAIL"),
                )
            }
        finally:
            conn.close()

        def _get_edit_page(listing_id: str, query: dict[str, str] | list[tuple[str, str]]) -> str:
            qs = urlencode(query)
            status, headers, body = session.get(
                f"{web_base}{_edit_page_path(_ORG_ID, listing_id)}?{qs}"
            )
            noindex_ok = headers.get("x-robots-tag") == "noindex"
            no_store_ok = "no-store" in headers.get("cache-control", "")
            assert status == 200, f"expected 200, got {status}"
            assert noindex_ok, "private editor page must carry X-Robots-Tag: noindex"
            assert no_store_ok, "private editor page must carry Cache-Control: no-store"
            return body.decode("utf-8")

        def _power_section(page_text: str) -> str:
            """Independent review amendment Finding B: slice out only the
            Power Search-fit section's own rendered output -- the Sail
            section renders a structurally identical "Result: <strong>..."
            fragment, so checking the whole page for that substring proves
            nothing specific about the Power section alone."""
            start = page_text.index("<h2>Power Search-fit preview</h2>")
            end = page_text.index("<h2>Sale / outcome</h2>", start)
            return page_text[start:end]

        # --- Claim-only combined positive ---------------------------------
        page_text = _get_edit_page(
            "NL-0095-INSP-CLAIM", {"psf_power_drive": "SHAFT", "psf_power_engine_count": "2"}
        )
        claim_ok = (
            "Power Search-fit preview" in page_text
            and "CONFIRMED_MATCH" in page_text
            and "publisher-claimed, not independently verified" in page_text
        )
        ok &= claim_ok
        print(
            "6. GET edit?psf_power_drive=SHAFT&psf_power_engine_count=2 on claim-only listing: "
            f"CONFIRMED_MATCH, publisher-claim disclaimer -> {'OK' if claim_ok else 'FAIL'}"
        )

        # --- Design-linked combined positive ------------------------------
        page_text = _get_edit_page(
            "NL-0095-INSP-LINKED", {"psf_power_drive": "SHAFT", "psf_power_engine_count": "2"}
        )
        linked_ok = (
            "CONFIRMED_MATCH" in page_text
            and "Canonical design result" in page_text
            and "publisher-claimed, not independently verified" not in page_text
        )
        ok &= linked_ok
        print(
            "7. GET edit?psf_power_drive=SHAFT&psf_power_engine_count=2 on design-linked listing: "
            f"CONFIRMED_MATCH with real design evidence, no publisher-claim disclaimer -> "
            f"{'OK' if linked_ok else 'FAIL'}"
        )

        # --- SAIL exclusion never a false positive ------------------------
        page_text = _get_edit_page("NL-0095-INSP-SAIL", {"psf_power_drive": "SHAFT"})
        sail_ok = "CONFIRMED_NON_MATCH" in page_text and "SAIL" in page_text
        ok &= sail_ok
        print(
            f"8. GET edit?psf_power_drive=SHAFT on explicit-SAIL listing: CONFIRMED_NON_MATCH "
            f"with category exclusion shown -> {'OK' if sail_ok else 'FAIL'}"
        )

        # --- Insufficient/negative with actionable source -----------------
        page_text = _get_edit_page("NL-0095-INSP-CLAIM", {"psf_power_engine_count": "5"})
        insufficient_ok = "CONFIRMED_NON_MATCH" in page_text or (
            "INSUFFICIENT_DATA" in page_text and "PhysicalBoat claim" in page_text
        )
        ok &= insufficient_ok
        print(
            "9. GET edit?psf_power_engine_count=5 (mismatched count) on claim-only listing: "
            f"non-match/insufficient with actionable source link -> {'OK' if insufficient_ok else 'FAIL'}"
        )

        # --- Sail legacy control non-regression on the same page ----------
        page_text = _get_edit_page("NL-0095-INSP-CLAIM", {"sf_draft_max": "1.5"})
        sail_legacy_ok = (
            "Search-fit preview" in page_text
            # The Sail blocker renders through `searchFitBlockerText`'s
            # human-readable mapping, never the raw `BOATDESIGN_NOT_LINKED`
            # enum code.
            and "No canonical design is linked yet" in page_text
            and "Power Search-fit preview" in page_text
        )
        ok &= sail_legacy_ok
        print(
            "10. GET edit?sf_draft_max=1.5 (original Sail preview) on the SAME page: Sail "
            f"section still renders its own unaffected result -> {'OK' if sail_legacy_ok else 'FAIL'}\n"
        )

        # --- Finding B: clearing both controls must yield no preview, never
        # the backend's correct INVALID_SCENARIO surfaced as a broker-facing
        # error for an action that submitted nothing meaningful -------------
        page_text = _get_edit_page(
            "NL-0095-INSP-CLAIM", {"psf_power_drive": "", "psf_power_engine_count": ""}
        )
        both_blank_section = _power_section(page_text)
        both_blank_ok = (
            "Result:" not in both_blank_section and "isn&#39;t valid" not in both_blank_section
        )
        ok &= both_blank_ok
        print(
            "11. GET edit?psf_power_drive=&psf_power_engine_count= (both cleared, the real "
            "default form submission): no preview rendered, no invalid-scenario error -> "
            f"{'OK' if both_blank_ok else 'FAIL'}"
        )

        page_text = _get_edit_page("NL-0095-INSP-CLAIM", {"psf_power_drive": ""})
        single_blank_ok = "Result:" not in _power_section(page_text)
        ok &= single_blank_ok
        print(
            "12. GET edit?psf_power_drive= alone (single present-but-blank key, direct URL): "
            f"no preview rendered -> {'OK' if single_blank_ok else 'FAIL'}"
        )

        page_text = _get_edit_page("NL-0095-INSP-CLAIM", {"psf_power_drive": "SHAFT"})
        drive_only_ok = "Result:" in _power_section(
            page_text
        ) and "CONFIRMED_MATCH" in _power_section(page_text)
        ok &= drive_only_ok
        print(
            f"13. GET edit?psf_power_drive=SHAFT alone: preview runs (CONFIRMED_MATCH) -> "
            f"{'OK' if drive_only_ok else 'FAIL'}"
        )

        page_text = _get_edit_page("NL-0095-INSP-CLAIM", {"psf_power_engine_count": "2"})
        count_only_ok = "Result:" in _power_section(
            page_text
        ) and "CONFIRMED_MATCH" in _power_section(page_text)
        ok &= count_only_ok
        print(
            f"14. GET edit?psf_power_engine_count=2 alone: preview runs (CONFIRMED_MATCH) -> "
            f"{'OK' if count_only_ok else 'FAIL'}"
        )

        page_text = _get_edit_page(
            "NL-0095-INSP-CLAIM", [("psf_power_drive", "SHAFT"), ("psf_power_drive", "SHAFT")]
        )
        duplicate_section = _power_section(page_text)
        duplicate_ok = "duplicate/ambiguous parameter was submitted" in duplicate_section
        ok &= duplicate_ok
        print(
            "15. GET edit?psf_power_drive=SHAFT&psf_power_drive=SHAFT (duplicate, even identical "
            f"values): rejected as ambiguous, never silently collapsed -> {'OK' if duplicate_ok else 'FAIL'}\n"
        )

        # --- Zero writes ----------------------------------------------------
        conn = psycopg.connect(url)
        try:
            fingerprint_after = {
                listing_id: fetch_current_physical_boat_claim(
                    conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(_ORG_ID)
                ).revision_id.value
                for listing_id, physical_boat_id in (
                    ("NL-0095-INSP-CLAIM", "PB-0095-INSP-CLAIM"),
                    ("NL-0095-INSP-LINKED", "PB-0095-INSP-LINKED"),
                    ("NL-0095-INSP-SAIL", "PB-0095-INSP-SAIL"),
                )
            }
        finally:
            conn.close()
        zero_writes_ok = fingerprint_before == fingerprint_after
        ok &= zero_writes_ok
        print(
            f"16. every preview GET above caused zero writes -> {'OK' if zero_writes_ok else 'FAIL'}"
        )

        # --- Public Power Buyer Search never sees the DRAFT previews ------
        api_status, _, api_body = _http_get(
            f"{api_base}/api/search/en/power?power_drive=SHAFT&power_engine_count=2"
        )
        api_json = _json(api_body)
        seen_ids = {
            m["native_listing_id"]
            for m in api_json.get("design_linked_matches", [])
            + api_json.get("publisher_claim_matches", [])
        }
        public_leak_ok = api_status == 200 and not (
            seen_ids & {"NL-0095-INSP-CLAIM", "NL-0095-INSP-LINKED", "NL-0095-INSP-SAIL"}
        )
        ok &= public_leak_ok
        print(
            "17. GET /api/search/en/power?power_drive=SHAFT&power_engine_count=2: none of this "
            f"slice's lifecycle-DRAFT listings leak into public Power Buyer Search -> "
            f"{'OK' if public_leak_ok else 'FAIL'}\n"
        )

        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secrets_clean = all(
            client_secret not in text and session_secret_b64 not in text
            for text in (api_log_text, web_log_text)
        )
        ok &= secrets_clean
        print(
            f"    ordinary API/web logs contain no client/session secret -> {'OK' if secrets_clean else 'FAIL'}\n"
        )

        print(f"SLICE-0095 POWER BROKER SEARCH-FIT PROOF RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (issuer_proc, api_proc, web_proc):
            _stop_process(proc)
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
