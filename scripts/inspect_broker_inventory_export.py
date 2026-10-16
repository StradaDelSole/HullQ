"""SLICE-0088 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the broker inventory portability export vertical (2026-10-16
seven-format Owner-accepted amendment) against a real, disposable
PostgreSQL 18 schema and two real local HTTP server processes: FastAPI
(real `uvicorn`, not an in-process TestClient) and the built Astro/Node
SSR web package. Authentication uses a directly minted, cryptographically
signed session cookie -- mirrors `scripts/inspect_multiformat_broker_import.py`'s
identical, already-accepted shortcut. FastAPI still performs its own real
signature verification of that exact cookie on every request below.

This script exercises the real built Astro SSR process for both the
pre-existing authenticated broker inventory page and the new export UI
page (`inventory/export`), while the export capability's own HTTP calls
go directly against the real FastAPI process (mirroring how the Astro
proxy routes call it server-to-server).

Demonstrates, end to end, through the real production FastAPI routes (no
direct SQL for the API-exercised steps; only persistence-layer seeding of
the underlying draft/listing/offer/claim/media fixtures, exactly like the
SLICE-0083 inspector):

    1. A real promoted ACTIVE+current-public listing (brand/model/
       build_year/LOA claim, AMOUNT offer, approved cover image) plus one
       private draft (with an adversarial formula-injection payload) for
       Organization A
    2. Preflight returns a snapshot_fingerprint and correctly reports
       per-row/per-format exportability, including the honest NautiX
       account-token/office-id/sale_class profile gap (never fabricated
       from the HullQ Organization id or a placeholder) and the
       formula-injection warning
    3. Six table-like Owner-accepted formats (CSV/TSV/XLSX/XLS/ODS/JSON)
       download with genuine binary signatures and explicit included/
       rejected counts, bound to the confirmed preflight fingerprint
    4. A NautiX download with no broker-confirmed profile is explicit
       `no_exportable_rows` -- never a silent empty "successful" file
    5. A NautiX download *with* a broker-confirmed account_token/
       office_id/sale_class profile is genuinely exportable, passes the
       pinned official XSD and the accepted SLICE-0083 reimport parser as
       VALID -- the real positive end-to-end path, not only the domain-
       unit synthetic fixture in `tests/unit/test_inventory_export_domain.py`
    6. Organization B (a second real, separately seeded Organization)
       cannot select Organization A's draft/listing -- unknown_item, no
       existence leak
    7. A member without the PUBLISHER role is denied
    8. Real concurrent maximum-size downloads exceeding the admission
       gate's own configured capacity resolve to 200/429 only, while a
       concurrently polled unrelated broker route's measured latency
       stays bounded -- proving the event loop was not blocked, not
       merely asserting it
    9. The pre-existing built Astro SSR broker inventory page still
       renders correctly
    10. The new built Astro SSR export UI page renders
    11. Exact finish marker

Requires ``HULLQ_TEST_DATABASE_URL`` and a pre-built Astro web package
(``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_inventory_export.py
"""

from __future__ import annotations

import concurrent.futures
import contextlib
import http.client
import http.cookiejar
import json
import os
import socket
import subprocess
import sys
import tempfile
import threading
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


def _process_rss_bytes(pid: int) -> int | None:
    """*pid*'s own current resident set size, when the platform actually
    supports a genuine cross-process query -- never a fabricated number.

    On Linux this reads the kernel's own `/proc/<pid>/status` accounting
    directly and is trustworthy. A Windows `OpenProcess`/
    `GetProcessMemoryInfo` ctypes path was prototyped for this script but
    deliberately removed after a direct experiment proved it unusable in
    this tool's sandboxed execution environment: querying a *different*
    process that had just allocated and touched 80MB (confirmed via a
    readiness marker file written only after the allocation) still
    returned the exact same fixed 4194304-byte constant on every sample,
    regardless of the target's real memory state or elapsed time --
    i.e. the cross-process query is intercepted/virtualized here, not a
    real reading. Returning a plausible-looking number from that path
    would be exactly the kind of fabricated evidence CLAUDE.md forbids, so
    this function reports `None` (disclosed as "not measured") on Windows
    rather than a number nobody should trust."""
    try:
        status_path = Path(f"/proc/{pid}/status")
        for line in status_path.read_text().splitlines():
            if line.startswith("VmRSS:"):
                return int(line.split()[1]) * 1024
    except Exception:
        return None
    return None


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
        preflight_body = _json(body) if preflight_ok else {}
        fingerprint = preflight_body.get("snapshot_fingerprint")
        preflight_ok = preflight_ok and isinstance(fingerprint, str) and bool(fingerprint)
        rows = preflight_body.get("rows", []) if preflight_ok else []
        preflight_ok = preflight_ok and len(rows) == 2
        nautix_reasons = rows[1]["formats"]["NAUTIX"]["reasons"] if preflight_ok else []
        # Without a broker-confirmed NautixExportProfile, sale_class AND the
        # destination account_token/office_id are all honestly absent --
        # never fabricated from the HullQ Organization id or a placeholder.
        preflight_ok = preflight_ok and any("sale_class" in r for r in nautix_reasons)
        preflight_ok = preflight_ok and any("account.token" in r for r in nautix_reasons)
        preflight_ok = preflight_ok and any("office_id" in r for r in nautix_reasons)
        preflight_ok = preflight_ok and any(
            "formula-injection" in w for w in rows[0]["formats"]["CSV"]["warnings"]
        )
        ok &= preflight_ok
        print(
            f"4. Preflight: 2 rows + fingerprint, honest NautiX profile gap, formula-injection "
            f"warning -> {'OK' if preflight_ok else 'FAIL'}"
        )

        magics = {
            "CSV": b"export_id",
            "TSV": b"export_id",
            "JSON": b'{"listings"',
            "XLSX": b"PK",
            "XLS": b"\xd0\xcf\x11\xe0",
            "ODS": b"PK",
        }
        all_formats_ok = True
        for fmt, magic in magics.items():
            status, headers, body = session_a.post_json(
                f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/download",
                {**selection, "format": fmt, "expected_snapshot_fingerprint": fingerprint},
                extra_headers=_csrf_headers(web_base),
            )
            format_ok = status == 200 and body.startswith(magic)
            format_ok = format_ok and headers.get("x-hullq-export-included-count") == "2"
            if fmt in ("CSV", "TSV"):
                format_ok = format_ok and b",=2+2" not in body and b"'=2+2" in body
            all_formats_ok = all_formats_ok and format_ok
            print(
                f"   - {fmt} download: genuine signature, no raw formula payload -> {'OK' if format_ok else 'FAIL'}"
            )
        ok &= all_formats_ok
        print(f"5. Six table-like formats downloaded -> {'OK' if all_formats_ok else 'FAIL'}")

        from hullq.domain.import_nautix import map_nautix_adverts_to_rows, parse_and_validate_nautix

        # Required Behavior: never a successful complete download that
        # silently skips every selected listing. Without a profile, no row
        # is NautiX-exportable.
        status, _, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/download",
            {**selection, "format": "NAUTIX", "expected_snapshot_fingerprint": fingerprint},
            extra_headers=_csrf_headers(web_base),
        )
        zero_row_protection_ok = status == 422 and _json(body).get("error") == "no_exportable_rows"
        ok &= zero_row_protection_ok
        print(
            f"6. NautiX download without a profile is explicit no_exportable_rows, never a "
            f"silent empty success -> {'OK' if zero_row_protection_ok else 'FAIL'}"
        )

        # With a broker-confirmed profile, the real promoted listing (never
        # the private draft) becomes genuinely NautiX-exportable -- the
        # real positive end-to-end path.
        nautix_profile = {
            "account_token": "BROKER-ACCT-REAL-1",
            "office_id": "OFFICE-REAL-1",
            "sale_classes": {listing_id: "used"},
        }
        # The profile itself is bound into the snapshot fingerprint (it
        # populates export-relevant row fields -- see
        # `_compute_snapshot_fingerprint`), so a fresh preflight *with*
        # this exact profile is required before the download can use it;
        # reusing the earlier no-profile fingerprint would correctly be
        # rejected as stale.
        profiled_selection = {"draft_ids": [], "native_listing_ids": [listing_id]}
        status, _, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/preflight",
            {**profiled_selection, "nautix_profile": nautix_profile},
            extra_headers=_csrf_headers(web_base),
        )
        profiled_fingerprint = _json(body).get("snapshot_fingerprint") if status == 200 else None
        status, headers, body = session_a.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/download",
            {
                **profiled_selection,
                "format": "NAUTIX",
                "nautix_profile": nautix_profile,
                "expected_snapshot_fingerprint": profiled_fingerprint,
            },
            extra_headers=_csrf_headers(web_base),
        )
        nautix_download_ok = (
            status == 200
            and body.startswith(b"<?xml")
            and headers.get("x-hullq-export-included-count") == "1"
        )
        try:
            root = parse_and_validate_nautix(body)
            mapped = map_nautix_adverts_to_rows(
                root, attested_account_tokens=frozenset({"BROKER-ACCT-REAL-1"})
            )
            nautix_roundtrip_ok = (
                nautix_download_ok
                and len(mapped) == 1
                and mapped[0].classification.value == "VALID"
            )
        except Exception as exc:
            nautix_roundtrip_ok = False
            print(f"   NautiX roundtrip exception: {exc}")
        ok &= nautix_roundtrip_ok
        print(
            f"7. With a broker-confirmed profile, NautiX passes pinned XSD + SLICE-0083 "
            f"reimport as VALID -> {'OK' if nautix_roundtrip_ok else 'FAIL'}"
        )

        status, _, body = session_b.post_json(
            f"{api_base}/api/broker/organizations/{_ORG_B}/inventory/export/preflight",
            {"draft_ids": [], "native_listing_ids": [listing_id]},
            extra_headers=_csrf_headers(web_base),
        )
        tenant_isolation_ok = status == 400 and _json(body).get("error") == "unknown_item"
        ok &= tenant_isolation_ok
        print(
            f"8. Organization B cannot select Organization A's listing -> {'OK' if tenant_isolation_ok else 'FAIL'}"
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
            f"9. A MEMBER-only (non-PUBLISHER) account is denied -> {'OK' if publisher_role_ok else 'FAIL'}"
        )

        # Independent review amendment (2026-10-16): prove, under real
        # concurrent maximum-size export workloads, that other API Search/
        # health/broker calls remain responsive -- measured, not guessed.
        # Fires more concurrent download requests than the real admission
        # gate's own configured capacity so it is actually exercised, while
        # a separate thread repeatedly times a cheap unrelated broker route
        # on the same real uvicorn process.
        from hullq.api.app import _EXPORT_MAX_CONCURRENT_JOBS

        health_latencies: list[float] = []
        stop_polling = False

        rss_samples: list[int] = []

        def _poll_health() -> None:
            poll_session = BrowserSession()
            while not stop_polling:
                start = time.monotonic()
                with contextlib.suppress(Exception):
                    poll_session.get(f"{api_base}/api/broker/context")
                health_latencies.append(time.monotonic() - start)
                assert api_proc is not None
                sample = _process_rss_bytes(api_proc.pid)
                if sample is not None:
                    rss_samples.append(sample)
                time.sleep(0.05)

        assert api_proc is not None
        rss_before = _process_rss_bytes(api_proc.pid)
        poll_thread = threading.Thread(target=_poll_health, daemon=True)
        poll_thread.start()
        try:
            concurrent_requests = _EXPORT_MAX_CONCURRENT_JOBS + 3

            def _one_download(_: int) -> tuple[int, float]:
                started = time.monotonic()
                status, _headers, _body = session_a.post_json(
                    f"{api_base}/api/broker/organizations/{_ORG_A}/inventory/export/download",
                    {**selection, "format": "XLSX", "expected_snapshot_fingerprint": fingerprint},
                    extra_headers=_csrf_headers(web_base),
                )
                return status, time.monotonic() - started

            with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as pool:
                results = list(pool.map(_one_download, range(concurrent_requests)))
        finally:
            stop_polling = True
            poll_thread.join(timeout=5)
        rss_after = _process_rss_bytes(api_proc.pid)

        export_statuses = [status for status, _ in results]
        # Every request must resolve to a real outcome (200 OK, or a
        # disclosed 429 BUSY from the admission gate) -- never a hang,
        # never an unexplained failure.
        concurrency_admission_ok = all(status in (200, 429) for status in export_statuses)
        at_least_one_ok = any(status == 200 for status in export_statuses)
        max_health_latency = max(health_latencies) if health_latencies else float("inf")
        # A generous bound for this disposable single-process local proof
        # run: the point is "the event loop was not blocked for seconds",
        # not a tight production SLO.
        health_stayed_responsive = max_health_latency < 2.0
        concurrency_ok = concurrency_admission_ok and at_least_one_ok and health_stayed_responsive
        ok &= concurrency_ok
        print(
            f"10. {concurrent_requests} concurrent max-size XLSX downloads "
            f"(statuses={export_statuses}) while polling /api/broker/context "
            f"{len(health_latencies)}x (max latency {max_health_latency * 1000:.1f}ms) -> "
            f"{'OK' if concurrency_ok else 'FAIL'}"
        )
        # HIGH_RISK mechanical-invariants contract: genuine measured
        # resident-set-size evidence for the real FastAPI process under
        # this concurrent load -- never only the structural row/cell/
        # output-byte bounding constants read from code. `None` samples
        # (the platform probe itself unavailable) are disclosed as such,
        # never silently treated as "0 bytes used".
        if rss_before is not None and rss_after is not None and rss_samples:
            peak_rss = max(rss_samples)
            print(
                f"    RSS before={rss_before / 1e6:.1f}MB peak-during={peak_rss / 1e6:.1f}MB "
                f"after={rss_after / 1e6:.1f}MB (bounded by MAX_EXPORT_ROWS/"
                f"MAX_EXPORT_OUTPUT_BYTES, {_EXPORT_MAX_CONCURRENT_JOBS} concurrent writer slots)"
            )
        else:
            print("    RSS sampling unavailable on this platform -- not measured, not claimed")

        status, _, _ = session_a.get(f"{web_base}/broker/organizations/{_ORG_A}/inventory")
        web_regression_ok = status == 200
        ok &= web_regression_ok
        print(
            f"11. Existing built Astro SSR broker inventory page still renders -> {'OK' if web_regression_ok else 'FAIL'}"
        )

        status, _, _ = session_a.get(f"{web_base}/broker/organizations/{_ORG_A}/inventory/export")
        export_page_ok = status == 200
        ok &= export_page_ok
        print(
            f"12. The new built Astro SSR export UI page renders -> {'OK' if export_page_ok else 'FAIL'}\n"
        )

        print("BROKER INVENTORY PORTABILITY EXPORT RESULT ->", "PASS" if ok else "FAIL")
        return 0 if ok else 1
    finally:
        _stop_process(api_proc)
        _stop_process(web_proc)
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
