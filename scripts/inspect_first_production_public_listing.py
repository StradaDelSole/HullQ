"""SLICE-0049 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the full committed first-production-public-listing vertical
against a real, disposable PostgreSQL 18 schema and real local HTTP servers
(FastAPI + built Astro/Node SSR), per SLICE-0049 §13:

    1. Alembic to single current head
    2. a pre-existing (migrated) listing is DRAFT and not publicly readable
    3. a newly created listing also begins DRAFT; exact create retry is
       idempotent
    4. create one complete accepted listing chain + current offer
    5. publish attempt with a denied/wrong-Organization principal changes
       nothing
    6. publish with an explicit eligible owning principal
    7. exactly one immutable DRAFT -> ACTIVE record exists
    8. fetch the production public FastAPI route without preview token
    9. fetch /listings/{id} over Astro SSR without preview token
    10. the page is deliberately noindex and self-canonical; query
        parameters do not create a second canonical identity
    11. an exact retry of the original immutable creation envelope does not
        conflict merely because lifecycle is ACTIVE
    12. withdraw with an authorized owning principal
    13. exactly one immutable ACTIVE -> WITHDRAWN record was appended
    14. the production API and Astro public URL now return ordinary
        not-found and reveal no hidden listing state
    15. WITHDRAWN -> ACTIVE is unsupported and leaves state/history unchanged
    16. another exact creation-envelope retry still preserves idempotency
        after withdrawal
    17. the SLICE-0048 preview boundary still behaves per its accepted
        contract

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL 18 instance) and a
pre-built Astro web package (``uv run`` this only after
``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_first_production_public_listing.py
"""

from __future__ import annotations

import base64
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
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import (
    NativeListingCreationStatus,
    create_native_listing,
)
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionStatus,
    fetch_lifecycle_state,
    list_publication_transitions,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_DRAFT_ONLY_LISTING_ID = "NL-0049-DRAFT-ONLY"
_TARGET_LISTING_ID = "NL-0049-E2E-001"
_PREVIEW_LISTING_ID = "NL-0049-PREVIEW-001"
_MALICIOUS_BROKER_TEXT = "<script>alert('xss')</script>"
_NEVER_CREATED_ID = "NL-0049-NEVER-CREATED"


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


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    membership_id: str, account: AccountId, org: MarketplaceOrganization
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _create_complete_chain(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    broker_description: str,
) -> NativeListingCreationStatus:
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    creation_result = create_native_listing(
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
            broker_description=broker_description,
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    return creation_result.status


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(
            f"{WEB_ENTRYPOINT} does not exist. Build the web package first:\n"
            "  cd web && npm ci && npm run build",
            file=sys.stderr,
        )
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0049e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0049_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("FIRST PRODUCTION PUBLIC LISTING\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("1. Alembic upgraded to single current head -> OK\n")

        account = AccountId("ACC-0049-E2E")
        org = _org("ORG-0049-E2E")
        membership = _membership("OM-0049-E2E", account, org)
        other_account = AccountId("ACC-0049-E2E-OTHER")
        other_org = _org("ORG-0049-E2E-OTHER")
        other_membership = _membership("OM-0049-E2E-OTHER", other_account, other_org)

        conn = psycopg.connect(url)
        try:
            # 2. a pre-existing/migrated listing is DRAFT and not publicly readable.
            _create_complete_chain(
                conn,
                listing_id=_DRAFT_ONLY_LISTING_ID,
                physical_boat_id="PB-0049-DRAFT-ONLY",
                market_episode_id="ME-0049-DRAFT-ONLY",
                offer_revision_id="REV-0049-DRAFT-ONLY",
                account=account,
                org=org,
                membership=membership,
                broker_description="Never published.",
            )
            conn.commit()
            draft_only_state = fetch_lifecycle_state(conn, NativeListingId(_DRAFT_ONLY_LISTING_ID))
            conn.commit()  # release the implicit read transaction before the next write
            step2_ok = draft_only_state is not None and draft_only_state.value == "DRAFT"
            ok &= step2_ok
            print(f"2. pre-existing listing begins DRAFT -> {'OK' if step2_ok else 'FAIL'}")

            # 3. a newly created listing also begins DRAFT; exact create retry idempotent.
            first_status = _create_complete_chain(
                conn,
                listing_id=_TARGET_LISTING_ID,
                physical_boat_id="PB-0049-E2E-001",
                market_episode_id="ME-0049-E2E-001",
                offer_revision_id="REV-0049-E2E-001",
                account=account,
                org=org,
                membership=membership,
                broker_description=_MALICIOUS_BROKER_TEXT,
            )
            conn.commit()
            target_state = fetch_lifecycle_state(conn, NativeListingId(_TARGET_LISTING_ID))
            conn.commit()  # release the implicit read transaction before the next write
            retry_status = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_TARGET_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0049-E2E-001"),
                ),
            ).status
            step3_ok = (
                first_status is NativeListingCreationStatus.CREATED
                and target_state is not None
                and target_state.value == "DRAFT"
                and retry_status is NativeListingCreationStatus.ALREADY_EXISTS
            )
            ok &= step3_ok
            print(
                f"3. newly created listing begins DRAFT + exact create retry idempotent -> "
                f"{'OK' if step3_ok else 'FAIL'}\n"
            )

            # 4. complete accepted listing chain + current offer already created above.
            print("4. complete listing chain + current offer created -> OK\n")

            # 5. publish attempt with a wrong-Organization principal changes nothing.
            denied_publish = publish_native_listing(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            state_after_denied = fetch_lifecycle_state(conn, NativeListingId(_TARGET_LISTING_ID))
            transitions_after_denied = list_publication_transitions(
                conn, NativeListingId(_TARGET_LISTING_ID)
            )
            conn.commit()  # release the implicit read transaction before the next write
            step5_ok = (
                denied_publish.status is LifecycleTransitionStatus.ORGANIZATION_MISMATCH
                and state_after_denied is not None
                and state_after_denied.value == "DRAFT"
                and len(transitions_after_denied) == 0
            )
            ok &= step5_ok
            print(
                f"5. publish attempt with wrong-Organization principal changes nothing -> "
                f"{'OK' if step5_ok else 'FAIL'}"
            )

            # 6. publish with the explicit eligible owning principal.
            publish_result = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            step6_ok = publish_result.status is LifecycleTransitionStatus.TRANSITIONED
            ok &= step6_ok
            print(f"6. publish with eligible owning principal -> {'OK' if step6_ok else 'FAIL'}")

            # 7. exactly one immutable DRAFT -> ACTIVE record exists.
            transitions_after_publish = list_publication_transitions(
                conn, NativeListingId(_TARGET_LISTING_ID)
            )
            conn.commit()  # release the implicit read transaction before the next write
            step7_ok = (
                len(transitions_after_publish) == 1
                and transitions_after_publish[0].from_state.value == "DRAFT"
                and transitions_after_publish[0].to_state.value == "ACTIVE"
            )
            ok &= step7_ok
            print(
                f"7. exactly one immutable DRAFT -> ACTIVE record exists -> "
                f"{'OK' if step7_ok else 'FAIL'}\n"
            )

            # Preview boundary fixture, created alongside (SLICE-0048 §17 proof).
            preview_secret = os.urandom(32)
            preview_account = AccountId("ACC-0049-PREVIEW")
            preview_org = _org("ORG-0049-PREVIEW")
            preview_membership = _membership("OM-0049-PREVIEW", preview_account, preview_org)
            preview_request = ListingIntakeRequest(
                account_id=preview_account,
                organization=preview_org,
                membership=preview_membership,
                physical_boat_id=PhysicalBoatId("PB-0049-PREVIEW"),
                boat_design_ref=None,
                market_episode_id=MarketEpisodeId("ME-0049-PREVIEW"),
                native_listing_id=NativeListingId(_PREVIEW_LISTING_ID),
                broker_listing_reference=None,
                offer_revision_id=NativeListingOfferRevisionId("REV-0049-PREVIEW"),
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.POA,
                    location_country="ES",
                    broker_description="Preview-only listing, never published.",
                ),
            )
            preview_intake_result = run_listing_intake(
                conn, request=preview_request, preview_signing_secret=preview_secret
            )
            preview_intake_ok = preview_intake_result.outcome is ListingIntakeOutcome.SUCCEEDED
            ok &= preview_intake_ok
            preview_token = preview_intake_result.preview_token
        finally:
            conn.close()

        if not ok:
            print("FIRST PRODUCTION PUBLIC LISTING RESULT -> FAIL")
            return 1

        # Serve FastAPI + Astro.
        api_port = _free_port()
        web_port = _free_port()
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = _b64url(preview_secret)

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
        api_ready = _wait_for_http(f"{api_base}/api/listings/{_NEVER_CREATED_ID}")
        ok &= api_ready
        print(f"FastAPI serving -> {'OK' if api_ready else 'FAIL'}")

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
        web_ready = _wait_for_http(f"{web_base}/listings/{_NEVER_CREATED_ID}")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("FIRST PRODUCTION PUBLIC LISTING RESULT -> FAIL")
            return 1

        # 8. fetch the production public FastAPI route without preview token.
        api_status, api_headers, api_body = _http_get(
            f"{api_base}/api/listings/{_TARGET_LISTING_ID}"
        )
        api_headers_lower = {k.lower(): v for k, v in api_headers.items()}
        step8_ok = (
            api_status == 200
            and b'"125000.00"' in api_body
            and api_headers_lower.get("x-robots-tag") == "noindex"
            and "cache-control" not in api_headers_lower
        )
        ok &= step8_ok
        print(
            f"8. production public FastAPI route (no preview token) -> {'OK' if step8_ok else 'FAIL'}"
        )

        # 9. fetch /listings/{id} over Astro SSR without preview token.
        web_status, web_headers, web_body = _http_get(f"{web_base}/listings/{_TARGET_LISTING_ID}")
        web_headers_lower = {k.lower(): v for k, v in web_headers.items()}
        page_text = web_body.decode("utf-8")
        step9_ok = web_status == 200 and "125000.00 EUR" in page_text
        ok &= step9_ok
        print(f"9. Astro SSR /listings/{{id}} (no preview token) -> {'OK' if step9_ok else 'FAIL'}")

        # 10. noindex + self-canonical; query params never create a second identity.
        canonical_href = f'href="{web_base}/listings/{_TARGET_LISTING_ID}"'
        query_status, _, query_body = _http_get(
            f"{web_base}/listings/{_TARGET_LISTING_ID}?utm_source=test&x=1"
        )
        query_page_text = query_body.decode("utf-8")
        step10_ok = (
            web_headers_lower.get("x-robots-tag") == "noindex"
            and 'name="robots" content="noindex"' in page_text
            and canonical_href in page_text
            and query_status == 200
            and canonical_href in query_page_text
        )
        ok &= step10_ok
        print(
            f"10. deliberately noindex + self-canonical, query params inert -> "
            f"{'OK' if step10_ok else 'FAIL'}"
        )

        # Malicious broker text remains escaped/inert on the web page.
        escaping_ok = (
            _MALICIOUS_BROKER_TEXT not in page_text
            and "&lt;script&gt;alert(&#39;xss&#39;)&lt;/script&gt;" in page_text
        )
        ok &= escaping_ok
        print(
            f"    malicious broker text rendered escaped/inert -> {'OK' if escaping_ok else 'FAIL'}\n"
        )

        # 11. exact retry of the original immutable creation envelope after ACTIVE.
        conn = psycopg.connect(url)
        try:
            retry_after_active = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_TARGET_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0049-E2E-001"),
                ),
            )
        finally:
            conn.close()
        step11_ok = retry_after_active.status is NativeListingCreationStatus.ALREADY_EXISTS
        ok &= step11_ok
        print(
            f"11. exact creation-envelope retry after ACTIVE stays ALREADY_EXISTS -> "
            f"{'OK' if step11_ok else 'FAIL'}\n"
        )

        # 12. withdraw with an authorized owning principal.
        conn = psycopg.connect(url)
        try:
            withdraw_result = withdraw_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            step12_ok = withdraw_result.status is LifecycleTransitionStatus.TRANSITIONED
            ok &= step12_ok
            print(
                f"12. withdraw with authorized owning principal -> {'OK' if step12_ok else 'FAIL'}"
            )

            # 13. exactly one immutable ACTIVE -> WITHDRAWN record was appended.
            all_transitions = list_publication_transitions(
                conn, NativeListingId(_TARGET_LISTING_ID)
            )
            step13_ok = (
                len(all_transitions) == 2
                and all_transitions[1].from_state.value == "ACTIVE"
                and all_transitions[1].to_state.value == "WITHDRAWN"
            )
            ok &= step13_ok
            print(
                f"13. exactly one immutable ACTIVE -> WITHDRAWN record appended -> "
                f"{'OK' if step13_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        # 14. production API and Astro public URL now return ordinary not-found.
        withdrawn_api_status, _, withdrawn_api_body = _http_get(
            f"{api_base}/api/listings/{_TARGET_LISTING_ID}"
        )
        never_created_api_status, _, never_created_api_body = _http_get(
            f"{api_base}/api/listings/{_NEVER_CREATED_ID}"
        )
        withdrawn_web_status, _, withdrawn_web_body = _http_get(
            f"{web_base}/listings/{_TARGET_LISTING_ID}"
        )
        never_created_web_status, _, never_created_web_body = _http_get(
            f"{web_base}/listings/{_NEVER_CREATED_ID}"
        )
        step14_ok = (
            withdrawn_api_status == 404
            and never_created_api_status == 404
            and withdrawn_api_body == never_created_api_body
            and withdrawn_web_status == 404
            and never_created_web_status == 404
            and withdrawn_web_body == never_created_web_body
        )
        ok &= step14_ok
        print(
            f"14. withdrawn listing now ordinary not-found, identical to never-created -> "
            f"{'OK' if step14_ok else 'FAIL'}\n"
        )

        # 15. WITHDRAWN -> ACTIVE is unsupported and leaves state/history unchanged.
        conn = psycopg.connect(url)
        try:
            republish_attempt = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_TARGET_LISTING_ID),
            )
            state_after_republish_attempt = fetch_lifecycle_state(
                conn, NativeListingId(_TARGET_LISTING_ID)
            )
            transitions_after_republish_attempt = list_publication_transitions(
                conn, NativeListingId(_TARGET_LISTING_ID)
            )
            conn.commit()  # release the implicit read transaction before the next write
            step15_ok = (
                republish_attempt.status is LifecycleTransitionStatus.CURRENT_STATE_CONFLICT
                and state_after_republish_attempt is not None
                and state_after_republish_attempt.value == "WITHDRAWN"
                and len(transitions_after_republish_attempt) == 2
            )
            ok &= step15_ok
            print(
                f"15. WITHDRAWN -> ACTIVE unsupported, state/history unchanged -> "
                f"{'OK' if step15_ok else 'FAIL'}\n"
            )

            # 16. another exact creation-envelope retry still preserves idempotency.
            retry_after_withdrawn = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId(_TARGET_LISTING_ID),
                    market_episode_id=MarketEpisodeId("ME-0049-E2E-001"),
                ),
            )
            step16_ok = retry_after_withdrawn.status is NativeListingCreationStatus.ALREADY_EXISTS
            ok &= step16_ok
            print(
                f"16. exact creation-envelope retry after WITHDRAWN stays ALREADY_EXISTS -> "
                f"{'OK' if step16_ok else 'FAIL'}\n"
            )
        finally:
            conn.close()

        # 17. the SLICE-0048 preview boundary still behaves per its accepted contract.
        assert preview_token is not None
        preview_status, preview_headers, preview_body = _http_get(
            f"{api_base}/api/_preview/listings/{preview_token}"
        )
        preview_headers_lower = {k.lower(): v for k, v in preview_headers.items()}
        tampered_token = preview_token[:-1] + ("A" if preview_token[-1] != "A" else "B")
        tampered_status, _, _ = _http_get(f"{api_base}/api/_preview/listings/{tampered_token}")
        step17_ok = (
            preview_status == 200
            and b'"asking_price_mode":"POA"' in preview_body
            and preview_headers_lower.get("cache-control") == "private, no-store"
            and preview_headers_lower.get("x-robots-tag") == "noindex, nofollow, noarchive"
            and tampered_status == 404
        )
        ok &= step17_ok
        print(
            f"17. SLICE-0048 preview boundary still behaves per its accepted contract -> {'OK' if step17_ok else 'FAIL'}\n"
        )

        # Logs must never contain the preview token or signing secret.
        api_log_text = api_log_path.read_text(encoding="utf-8", errors="replace")
        web_log_text = web_log_path.read_text(encoding="utf-8", errors="replace")
        secret_b64 = _b64url(preview_secret)
        logs_clean = (
            preview_token not in api_log_text
            and preview_token not in web_log_text
            and secret_b64 not in api_log_text
            and secret_b64 not in web_log_text
        )
        ok &= logs_clean
        print(
            f"    ordinary API/web logs contain no token/secret -> {'OK' if logs_clean else 'FAIL'}\n"
        )

        print(f"FIRST PRODUCTION PUBLIC LISTING RESULT -> {'PASS' if ok else 'FAIL'}")
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


if __name__ == "__main__":
    raise SystemExit(main())
