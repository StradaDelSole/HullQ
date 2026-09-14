"""SLICE-0048 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed first-visible-listing vertical against a real,
disposable PostgreSQL 18 schema and real local HTTP servers (FastAPI +
built Astro/Node SSR), per SLICE-0048 §10:

    1. Alembic to single current head
    2. create/ensure PhysicalBoat/MarketEpisode/NativeListing/current offer
       head through the real operator intake orchestration (real SLICE-0041
       evaluator, no authorized=true bypass)
    3. generate a finite signed preview capability
    4. serve FastAPI with token-safe logging
    5. serve the built Astro SSR page with token-safe logging
    6. fetch the preview page over real HTTP and assert:
       - success and visible persisted content
       - noindex/no-store/no-referrer protections
       - a tampered token reveals no listing
       - a malicious HTML-like broker value renders escaped/inert
       - captured ordinary API/web/application logs contain neither the
         preview token nor the signing secret

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance) and a
pre-built Astro web package (``uv run`` this only after
``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_first_visible_listing_preview.py
"""

from __future__ import annotations

import os
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

from hullq.application.listing_intake import (
    ListingIntakeOutcome,
    ListingIntakeRequest,
    run_listing_intake,
)
from hullq.domain.market_identity import (
    MarketEpisodeId,
    NativeListingId,
    PhysicalBoatId,
)
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
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
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.market_episode import fetch_market_episode
from hullq.persistence.native_listing import fetch_native_listing
from hullq.persistence.native_listing_offer import fetch_current_native_listing_offer
from hullq.persistence.physical_boat import fetch_physical_boat

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_ACCOUNT_ID = "ACC-0048-E2E"
_ORG_ID = "ORG-0048-E2E"
_PHYSICAL_BOAT_ID = "PB-0048-E2E-001"
_MARKET_EPISODE_ID = "ME-0048-E2E-001"
_NATIVE_LISTING_ID = "NL-0048-E2E-001"
_OFFER_REVISION_ID = "REV-0048-E2E-001"
_MALICIOUS_BROKER_TEXT = "<script>alert('xss')</script>"


def _base_db_url() -> str:
    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL 18 instance.",
            file=sys.stderr,
        )
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


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _wait_for_http(url: str, *, timeout_seconds: float = 15.0) -> bool:
    """Poll *url* until the server accepts connections and returns any HTTP response.

    A non-2xx response (e.g. 404 for a bogus health-check token) still counts
    as "ready" -- only a connection failure means the server isn't up yet.
    """
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


def _http_get(url: str) -> tuple[int, dict[str, str], bytes]:
    request = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, dict(response.headers), response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, dict(exc.headers or {}), exc.read()


def _run_intake(conn: Any, secret: bytes) -> Any:
    account = AccountId(_ACCOUNT_ID)
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId(_ORG_ID),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    membership = OrganizationMembership(
        id=OrganizationMembershipId("OM-0048-E2E"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    request = ListingIntakeRequest(
        account_id=account,
        organization=org,
        membership=membership,
        physical_boat_id=PhysicalBoatId(_PHYSICAL_BOAT_ID),
        boat_design_ref=None,  # prefer BoatDesignRef = NONE per SLICE-0048 §10.2
        market_episode_id=MarketEpisodeId(_MARKET_EPISODE_ID),
        native_listing_id=NativeListingId(_NATIVE_LISTING_ID),
        broker_listing_reference=None,
        offer_revision_id=NativeListingOfferRevisionId(_OFFER_REVISION_ID),
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description=_MALICIOUS_BROKER_TEXT,
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    return run_listing_intake(conn, request=request, preview_signing_secret=secret)


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0048e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0048_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None

    try:
        url = _with_search_path(base_url, schema_name)
        print("FIRST VISIBLE LISTING PREVIEW\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("1. Alembic upgraded to single current head -> OK\n")

        secret = os.urandom(32)

        conn = psycopg.connect(url)
        try:
            intake_result = _run_intake(conn, secret)
        finally:
            conn.close()

        ok = intake_result.outcome is ListingIntakeOutcome.SUCCEEDED
        print(f"2/3. operator intake -> {intake_result.outcome.value.upper()}")
        print(f"     preview token minted -> {'YES' if intake_result.preview_token else 'NO'}\n")
        if not ok or intake_result.preview_token is None:
            print("FIRST VISIBLE LISTING PREVIEW RESULT -> FAIL")
            return 1
        preview_token = intake_result.preview_token

        # 4. prove durable PhysicalBoat/MarketEpisode/NativeListing/current offer head
        conn = psycopg.connect(url)
        try:
            physical_boat_record = fetch_physical_boat(conn, PhysicalBoatId(_PHYSICAL_BOAT_ID))
            market_episode_record = fetch_market_episode(conn, MarketEpisodeId(_MARKET_EPISODE_ID))
            native_listing_record = fetch_native_listing(conn, NativeListingId(_NATIVE_LISTING_ID))
            offer_record = fetch_current_native_listing_offer(
                conn, NativeListingId(_NATIVE_LISTING_ID)
            )
            conn.commit()
        finally:
            conn.close()

        durable_chain_ok = (
            physical_boat_record is not None
            and market_episode_record is not None
            and native_listing_record is not None
            and native_listing_record.listing.market_episode_id
            == MarketEpisodeId(_MARKET_EPISODE_ID)
            and offer_record is not None
            and offer_record.offer.broker_description == _MALICIOUS_BROKER_TEXT
        )
        ok &= durable_chain_ok
        print(
            f"4. durable PhysicalBoat/MarketEpisode/NativeListing/offer head -> {'OK' if durable_chain_ok else 'FAIL'}\n"
        )

        # 6/7. serve FastAPI + Astro with token-safe logging
        api_port = _free_port()
        web_port = _free_port()
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = _b64url(secret)

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

        api_base = f"http://127.0.0.1:{api_port}"
        api_ready = _wait_for_http(
            f"{api_base}/api/_preview/listings/health-check-not-a-real-token"
        )
        print(f"6. FastAPI serving (token-safe logging) -> {'OK' if api_ready else 'FAIL'}")
        ok &= api_ready

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        with web_log_path.open("wb") as web_log:
            web_proc = subprocess.Popen(
                ["node", "./dist/server/entry.mjs"],
                cwd=WEB_DIR,
                env=web_env,
                stdout=web_log,
                stderr=subprocess.STDOUT,
            )

        web_base = f"http://127.0.0.1:{web_port}"
        web_ready = _wait_for_http(f"{web_base}/_preview/listings/health-check-not-a-real-token")
        print(f"7. Astro SSR serving (token-safe logging) -> {'OK' if web_ready else 'FAIL'}\n")
        ok &= web_ready

        if not ok:
            print("FIRST VISIBLE LISTING PREVIEW RESULT -> FAIL")
            return 1

        # 8/9. fetch preview page over HTTP and assert visible persisted content
        status, headers, body = _http_get(f"{web_base}/_preview/listings/{preview_token}")
        page_text = body.decode("utf-8")
        visible_content_ok = (
            status == 200 and "125000.00 EUR" in page_text and "HullQ listing preview" in page_text
        )
        ok &= visible_content_ok
        print(
            f"8/9. real HTTP fetch + visible persisted content -> {'OK' if visible_content_ok else 'FAIL'} (status={status})"
        )

        # 10. assert noindex / no-store / no-referrer protections
        headers_lower = {k.lower(): v for k, v in headers.items()}
        protections_ok = (
            headers_lower.get("cache-control") == "private, no-store"
            and headers_lower.get("referrer-policy") == "no-referrer"
            and headers_lower.get("x-robots-tag") == "noindex, nofollow, noarchive"
            and 'name="robots" content="noindex, nofollow, noarchive"' in page_text
        )
        ok &= protections_ok
        print(
            f"10. noindex/no-store/no-referrer protections -> {'OK' if protections_ok else 'FAIL'}"
        )

        # 11. assert tampered token reveals no listing
        tampered = preview_token[:-1] + ("A" if preview_token[-1] != "A" else "B")
        tampered_status, _, _ = _http_get(f"{web_base}/_preview/listings/{tampered}")
        tamper_ok = tampered_status == 404
        ok &= tamper_ok
        print(
            f"11. tampered token reveals no listing -> {'OK' if tamper_ok else 'FAIL'} (status={tampered_status})"
        )

        # 12. assert malicious HTML-like broker value remains inert/escaped
        escaping_ok = (
            _MALICIOUS_BROKER_TEXT not in page_text
            and "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in page_text
        )
        ok &= escaping_ok
        print(
            f"12. malicious broker text rendered escaped/inert -> {'OK' if escaping_ok else 'FAIL'}"
        )

        # 13. assert captured logs contain neither the token nor the secret
        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secret_b64 = _b64url(secret)
        logs_clean = (
            preview_token not in api_log_text
            and preview_token not in web_log_text
            and secret_b64 not in api_log_text
            and secret_b64 not in web_log_text
        )
        ok &= logs_clean
        print(
            f"13. ordinary API/web logs contain no token/secret -> {'OK' if logs_clean else 'FAIL'}\n"
        )

        print(f"FIRST VISIBLE LISTING PREVIEW RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        for proc in (api_proc, web_proc):
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    proc.kill()
        _drop_schema(base_url, schema_name)
        shutil.rmtree(log_dir, ignore_errors=True)


def _b64url(data: bytes) -> str:
    import base64

    return base64.urlsafe_b64encode(data).decode("ascii")


if __name__ == "__main__":
    raise SystemExit(main())
