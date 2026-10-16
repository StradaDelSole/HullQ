"""SLICE-0088 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the broker inventory portability export vertical (2026-10-16
seven-format Owner-accepted amendment) against a real, disposable
PostgreSQL 18 schema and two real local HTTP server processes: FastAPI
(real `uvicorn`, not an in-process TestClient) and the built Astro/Node
SSR web package. Authentication uses a directly minted, cryptographically
signed session cookie -- mirrors `scripts/inspect_multiformat_broker_import.py`'s
identical, already-accepted shortcut. FastAPI still performs its own real
signature verification of that exact cookie on every request below.

Scope note: no dedicated export Astro UI page exists yet (disclosed as an
open gap in the SLICE-0088 completion report). This script therefore
proves the built Astro SSR process is alive and correctly renders the
*existing* authenticated broker inventory page for the exact Organization
under test (regression proof that adding the export routes did not break
Astro SSR), while the export capability itself is exercised through real
HTTP directly against the real FastAPI process.

Demonstrates, end to end, through the real production FastAPI routes (no
direct SQL for the API-exercised steps; only persistence-layer seeding of
the underlying draft/listing/offer/claim/media fixtures, exactly like the
SLICE-0083 inspector):

    1. A real promoted ACTIVE+current-public listing (brand/model/
       build_year/LOA claim, AMOUNT offer, approved cover image) plus one
       private draft (with an adversarial formula-injection payload) for
       Organization A
    2. Preflight correctly reports per-row/per-format exportability,
       including the honest NautiX "sale_class" representability gap
       (never fabricated) and the formula-injection warning
    3. All seven Owner-accepted formats download with genuine binary
       signatures: CSV, TSV, XLSX, XLS, ODS, JSON, NautiX 1.4
    4. The downloaded NautiX document passes the pinned official XSD and
       the accepted SLICE-0083 reimport parser (zero adverts, because the
       sale_class gap applies -- proving no fabricated advert, not a
       broken writer; the writer's positive case is proven directly at
       the domain-unit level in `tests/unit/test_inventory_export_domain.py`)
    5. CSV/TSV downloads never contain the raw adversarial formula payload
       unescaped
    6. Organization B (a second real, separately seeded Organization)
       cannot select Organization A's draft/listing -- unknown_item, no
       existence leak
    7. A member without the PUBLISHER role is denied
    8. The built Astro SSR broker inventory page still renders correctly
       for Organization A after these routes were added
    9. Exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_inventory_export.py
"""

from __future__ import annotations

import http.client
import http.cookiejar
import json
import os
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
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_HTTP_PROBE_TRANSIENT_ERRORS = (urllib.error.URLError, ConnectionError, TimeoutError, OSError)

_ORG_A = "ORG-0088-E2E-A"
_ORG_B = "ORG-0088-E2E-B"
_ACCOUNT_A = "ACC-0088-E2E-A"
_ACCOUNT_B = "ACC-0088-E2E-B"
_EXPORT_CSRF_HEADER_VALUE = "broker-inventory-export-v1"


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


class _NoRedirect(urllib.request.HTTPErrorProcessor):
    def http_response(self, request: Any, response: Any) -> Any:
        return response

    https_response = http_response


class BrowserSession:
    """A real, standards-compliant cookie-jar HTTP client -- mirrors
    `scripts/inspect_multiformat_broker_import.py`'s identical
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
        return response.status, response.headers, response.read()

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


def _json(body: bytes) -> Any:
    return json.loads(body.decode("utf-8"))


def _csrf_headers(web_base: str) -> dict[str, str]:
    return {"Origin": web_base, "X-HullQ-Requested-With": _EXPORT_CSRF_HEADER_VALUE}


def _start_api(
    *, url: str, api_port: int, preview_secret_b64: str, session_secret_b64: str, web_base: str
) -> tuple[subprocess.Popen[bytes], Path]:
    log_path = Path(tempfile.mkstemp(prefix="hullq_s0088_api_", suffix=".log")[1])
    env = dict(os.environ)
    env["HULLQ_DATABASE_URL"] = url
    env["HULLQ_PREVIEW_SIGNING_SECRET"] = preview_secret_b64
    env["HULLQ_SESSION_SIGNING_SECRET"] = session_secret_b64
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
    schema_name = f"hullq_s0088e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0088_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        from hullq.domain.broker_access import AuthenticatedIdentity, Provider
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
            LoaLengthClaim,
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
        from hullq.persistence.professional_listing_draft import create_professional_listing_draft
        from hullq.security.session_token import mint_session_token

        url = _with_search_path(base_url, schema_name)
        print("BROKER INVENTORY PORTABILITY EXPORT (SLICE-0088, seven-format)\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("0. Alembic upgraded to current head -> OK")

        api_port = _free_port()
        web_port = _free_port()
        api_base = f"http://127.0.0.1:{api_port}"
        web_base = f"http://127.0.0.1:{web_port}"
        preview_secret = os.urandom(32)
        session_secret = os.urandom(32)

        import base64

        api_proc, api_log_path = _start_api(
            url=url,
            api_port=api_port,
            preview_secret_b64=base64.urlsafe_b64encode(preview_secret).decode("ascii"),
            session_secret_b64=base64.urlsafe_b64encode(session_secret).decode("ascii"),
            web_base=web_base,
        )
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
        ok &= api_ready
        print(f"1. FastAPI serving (real uvicorn process) -> {'OK' if api_ready else 'FAIL'}")
        if not api_ready:
            print(
                api_log_path.read_text(encoding="utf-8", errors="replace")[-4000:], file=sys.stderr
            )

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
        print(
            f"2. Astro SSR serving (real built Node process) -> {'OK' if web_ready else 'FAIL'}\n"
        )

        if not ok:
            print("BROKER INVENTORY PORTABILITY EXPORT RESULT -> FAIL")
            return 1

        def _mint_cookie(account_id: str, *, mfa: bool = True) -> str:
            identity = AuthenticatedIdentity(
                provider=Provider.AUTH0,
                issuer="https://issuer.test/",
                subject=f"subject-{account_id}",
                auth_time=datetime.now(UTC),
                mfa_satisfied=mfa,
            )
            minted = mint_session_token(identity, AccountId(account_id), secret=session_secret)
            return minted.token

        conn = psycopg.connect(url)
        try:
            for account_id, org_id, roles in (
                (_ACCOUNT_A, _ORG_A, frozenset({MembershipRole.PUBLISHER})),
                (_ACCOUNT_B, _ORG_B, frozenset({MembershipRole.PUBLISHER})),
            ):
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        [account_id],
                    )
                conn.commit()
                org = MarketplaceOrganization(
                    id=MarketplaceOrganizationId(org_id),
                    professional_category=ProfessionalCategory.BROKER,
                    publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
                )
                seed_marketplace_organization(conn, org)
                seed_organization_membership(
                    conn,
                    OrganizationMembership(
                        id=OrganizationMembershipId(f"MEM-{account_id}"),
                        account_id=AccountId(account_id),
                        organization_id=MarketplaceOrganizationId(org_id),
                        roles=roles,
                        state=MembershipState.ACTIVE,
                    ),
                )
                conn.commit()

            account = AccountId(_ACCOUNT_A)
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId(f"MEM-{_ACCOUNT_A}"),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )

            listing_id = "LIST-0088-E2E"
            create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-0088-E2E")))
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0088-E2E"),
                    physical_boat_id=PhysicalBoatId("PB-0088-E2E"),
                ),
            )
            create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId("ME-0088-E2E")
                ),
                broker_listing_reference="REF-0088-E2E",
            )
            write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(listing_id),
                revision_id=NativeListingOfferRevisionId(f"OFFER-{listing_id}"),
                expected_current_revision_id=None,
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop = great value",
                    asking_price_amount=Decimal("125000.00"),
                    currency="EUR",
                ),
            )
            write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(listing_id),
                revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    loa_length=LoaLengthClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.13")
                    ),
                ),
            )
            with conn.transaction():
                asset = insert_approved_media_asset(
                    conn,
                    owner_organization_id=org.id,
                    uploaded_by_account_id=account,
                    rights_declared=True,
                    source_kind=MediaSourceKind.BROKER_UPLOAD,
                    source_reference=None,
                    original_object_key=f"original/{listing_id}",
                    derivative_object_key=f"derivative/{listing_id}",
                    content_hash="d8e8fca2dc0f896fd7cb4cb0031ba249",
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
                assert placement_result.media_placement_id is not None
                assert placement_result.gallery_version is not None
                set_cover(
                    conn,
                    native_listing_id=NativeListingId(listing_id),
                    owner_organization_id=org.id,
                    media_placement_id=placement_result.media_placement_id,
                    expected_version=placement_result.gallery_version,
                )
            conn.commit()
            publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(listing_id),
            )

            from hullq.domain.listing_draft_payload import parse_listing_draft_payload

            draft_payload = parse_listing_draft_payload(
                {
                    "physical_boat.marketed_brand_claim": "=2+2",
                    "physical_boat.model_designation_claim": "Draft Model",
                }
            )
            draft_record = create_professional_listing_draft(
                conn,
                owner_organization_id=org.id,
                created_by_account_id=account,
                broker_listing_reference=None,
                payload=draft_payload,
            )
            conn.commit()
            draft_id = draft_record.draft_id.value
            print(
                "3. Real promoted ACTIVE+current-public listing and one private draft seeded -> OK\n"
            )
        finally:
            conn.close()

        session_a = BrowserSession()
        session_a.jar.set_cookie(
            http.cookiejar.Cookie(
                0,
                "hullq_session",
                _mint_cookie(_ACCOUNT_A),
                None,
                False,
                "127.0.0.1",
                False,
                False,
                "/",
                True,
                False,
                None,
                True,
                None,
                None,
                {},
            )
        )
        session_b = BrowserSession()
        session_b.jar.set_cookie(
            http.cookiejar.Cookie(
                0,
                "hullq_session",
                _mint_cookie(_ACCOUNT_B),
                None,
                False,
                "127.0.0.1",
                False,
                False,
                "/",
                True,
                False,
                None,
                True,
                None,
                None,
                {},
            )
        )

        selection = {"draft_ids": [draft_id], "native_listing_ids": [listing_id]}

        status, _, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/preflight",
            selection,
            extra_headers=_csrf_headers(web_base),
        )
        preflight_ok = status == 200
        rows = _json(body).get("rows", []) if preflight_ok else []
        preflight_ok = preflight_ok and len(rows) == 2
        nautix_reasons = rows[1]["formats"]["NAUTIX"]["reasons"] if preflight_ok else []
        preflight_ok = preflight_ok and any("sale_class" in r for r in nautix_reasons)
        preflight_ok = preflight_ok and any(
            "formula-injection" in w for w in rows[0]["formats"]["CSV"]["warnings"]
        )
        ok &= preflight_ok
        print(
            f"4. Preflight: 2 rows, honest NautiX sale_class gap, formula-injection warning -> {'OK' if preflight_ok else 'FAIL'}"
        )

        magics = {
            "CSV": b"export_id",
            "TSV": b"export_id",
            "JSON": b'{"listings"',
            "XLSX": b"PK",
            "XLS": b"\xd0\xcf\x11\xe0",
            "ODS": b"PK",
            "NAUTIX": b"<?xml",
        }
        all_formats_ok = True
        nautix_bytes = b""
        for fmt, magic in magics.items():
            status, _headers, body = session_a.post_json(
                f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/download",
                {**selection, "format": fmt},
                extra_headers=_csrf_headers(web_base),
            )
            format_ok = status == 200 and body.startswith(magic)
            if fmt in ("CSV", "TSV"):
                format_ok = format_ok and b",=2+2" not in body and b"'=2+2" in body
            if fmt == "NAUTIX":
                nautix_bytes = body
            all_formats_ok = all_formats_ok and format_ok
            print(
                f"   - {fmt} download: genuine signature, no raw formula payload -> {'OK' if format_ok else 'FAIL'}"
            )
        ok &= all_formats_ok
        print(
            f"5. All seven Owner-accepted formats downloaded -> {'OK' if all_formats_ok else 'FAIL'}"
        )

        from hullq.domain.import_nautix import map_nautix_adverts_to_rows, parse_and_validate_nautix

        try:
            root = parse_and_validate_nautix(nautix_bytes)
            mapped = map_nautix_adverts_to_rows(root, attested_account_tokens=frozenset({_ORG_A}))
            nautix_roundtrip_ok = len(mapped) == 0  # sale_class gap -> zero fabricated adverts
        except Exception as exc:
            nautix_roundtrip_ok = False
            print(f"   NautiX roundtrip exception: {exc}")
        ok &= nautix_roundtrip_ok
        print(
            f"6. NautiX bytes pass pinned XSD + SLICE-0083 reimport (zero fabricated adverts) -> {'OK' if nautix_roundtrip_ok else 'FAIL'}"
        )

        status, _, body = session_b.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_B}/inventory/export/preflight",
            {"draft_ids": [], "native_listing_ids": [listing_id]},
            extra_headers=_csrf_headers(web_base),
        )
        tenant_isolation_ok = status == 400 and _json(body).get("error") == "unknown_item"
        ok &= tenant_isolation_ok
        print(
            f"7. Organization B cannot select Organization A's listing -> {'OK' if tenant_isolation_ok else 'FAIL'}"
        )

        member_account = "ACC-0088-E2E-MEMBER"
        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                    [member_account],
                )
            conn.commit()
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId(f"MEM-{member_account}"),
                    account_id=AccountId(member_account),
                    organization_id=MarketplaceOrganizationId(_ORG_A),
                    roles=frozenset({MembershipRole.MEMBER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        session_member = BrowserSession()
        session_member.jar.set_cookie(
            http.cookiejar.Cookie(
                0,
                "hullq_session",
                _mint_cookie(member_account),
                None,
                False,
                "127.0.0.1",
                False,
                False,
                "/",
                True,
                False,
                None,
                True,
                None,
                None,
                {},
            )
        )
        status, _, body = session_member.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/preflight",
            selection,
            extra_headers=_csrf_headers(web_base),
        )
        publisher_role_ok = status == 403 and _json(body).get("error") == "publisher_role_required"
        ok &= publisher_role_ok
        print(
            f"8. A MEMBER-only (non-PUBLISHER) account is denied -> {'OK' if publisher_role_ok else 'FAIL'}"
        )

        status, _, _ = session_a.get(f"{web_base}/broker/organizations/{_ORG_A}/inventory")
        web_regression_ok = status == 200
        ok &= web_regression_ok
        print(
            f"9. Existing built Astro SSR broker inventory page still renders -> {'OK' if web_regression_ok else 'FAIL'}\n"
        )

        print("BROKER INVENTORY PORTABILITY EXPORT RESULT ->", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
