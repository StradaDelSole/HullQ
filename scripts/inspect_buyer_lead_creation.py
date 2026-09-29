"""SLICE-0070 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the durable buyer contact / Lead creation vertical against a real,
disposable PostgreSQL schema and real local HTTP servers (FastAPI + built
Astro/Node SSR), per `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md`
§17:

    1. Alembic upgrade to current head
    2. create + publish one currently-public-eligible NativeListing
    3. FastAPI + built Astro serving over real HTTP
    4. the public Astro listing page renders the bounded buyer contact form
    5. an anonymous valid submission through the same-origin Astro proxy
       durably creates exactly one Lead, readable back with UNVERIFIED
       contact-email state and the listing's real publishing Organization
    6. an exact retry (identical submission-operation identity + envelope)
       is idempotent -- no duplicate row
    7. the same operation identity with a materially different envelope
       conflicts -- still no duplicate row
    8. invalid input produces zero mutation
    9. FastAPI's own CSRF boundary rejects a direct cross-origin POST,
       independent of the Astro proxy
    10. withdrawing the listing then removes both the public page's contact
        form and the contact route's availability -- the bounded
        non-enumerating listing-not-available outcome, without creating a
        Lead
    11. Finding A (independent review amendment, exact-head
        0f7e4b7826c9867754dd2e97fff1ee19b56fc1f5): an exact retry of the
        already-created Lead's own submission-operation identity still
        resolves to that same Lead after the listing has since become
        unavailable -- contract §4's idempotent-retry guarantee is
        independent of current listing state

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL instance) and a
pre-built Astro web package (``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_buyer_lead_creation.py
"""

from __future__ import annotations

import base64
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
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from _publication_readiness_fixture import attach_d22_minimum_cover_image

from hullq.domain.buyer_lead import LeadId
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
from hullq.persistence.buyer_lead import fetch_buyer_lead
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_LISTING_ID = "NL-0070-E2E-001"
_NEVER_CREATED_ID = "NL-0070-NEVER-CREATED"


def _base_db_url() -> str:
    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL instance.",
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
        except (urllib.error.URLError, ConnectionError, TimeoutError, OSError):
            time.sleep(0.2)
    return False


def _http_get(url: str) -> tuple[int, bytes]:
    try:
        with urllib.request.urlopen(url, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _http_post_json(
    url: str, payload: dict[str, Any], *, origin: str, csrf_header_value: str
) -> tuple[int, dict[str, Any]]:
    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/json",
            "Origin": origin,
            "X-HullQ-Requested-With": csrf_header_value,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read())
    except urllib.error.HTTPError as exc:
        raw = exc.read()
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {}


def _b64url(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii")


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


def _publish_listing(
    conn: Any, *, listing_id: str, account: AccountId, org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-{listing_id}")))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(f"ME-{listing_id}"), physical_boat_id=PhysicalBoatId(f"PB-{listing_id}")
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(f"ME-{listing_id}")
        ),
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account,
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
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, 2020),
        ),
    )
    attach_d22_minimum_cover_image(conn, listing_id=listing_id, account=account, org=org)
    conn.commit()  # release the transaction attach_d22_minimum_cover_image left open
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
    schema_name = f"hullq_s0070e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0070_e2e_"))
    api_log_path = log_dir / "api.log"
    web_log_path = log_dir / "web.log"
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("DURABLE BUYER CONTACT / LEAD CREATION\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("1. Alembic upgraded to current head -> OK\n")

        account = AccountId("ACC-0070-E2E")
        org = _org("ORG-0070-E2E")
        membership = _membership("OM-0070-E2E", account, org)

        conn = psycopg.connect(url)
        try:
            _publish_listing(conn, listing_id=_LISTING_ID, account=account, org=org, membership=membership)
            conn.commit()
        finally:
            conn.close()
        print("2. currently-public-eligible NativeListing created + published -> OK\n")

        # Serve FastAPI + Astro.
        api_port = _free_port()
        web_port = _free_port()
        web_base = f"http://127.0.0.1:{web_port}"

        preview_secret = os.urandom(32)
        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = _b64url(preview_secret)
        api_env["HULLQ_WEB_ORIGIN"] = web_base

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

        web_ready = _wait_for_http(f"{web_base}/listings/{_NEVER_CREATED_ID}")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")

        if not ok:
            print("DURABLE BUYER CONTACT / LEAD CREATION RESULT -> FAIL")
            return 1

        # 4. the public listing page renders the bounded contact form.
        page_status, page_body = _http_get(f"{web_base}/listings/{_LISTING_ID}")
        step4_ok = page_status == 200 and b"data-buyer-contact-form" in page_body
        ok &= step4_ok
        print(f"4. public listing page renders the bounded contact form -> {'OK' if step4_ok else 'FAIL'}")

        contact_url = f"{web_base}/listings/{_LISTING_ID}/contact"

        # 5. anonymous valid submission through the Astro proxy.
        created_status, created_body = _http_post_json(
            contact_url,
            {
                "submission_operation_id": "OP-0070-E2E-1",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
            },
            origin=web_base,
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        step5_ok = created_status == 201 and created_body.get("status") == "CREATED"
        ok &= step5_ok
        print(f"5. anonymous valid submission via Astro proxy -> {'OK' if step5_ok else 'FAIL'}")

        lead_id_value = created_body.get("lead_id")
        verify_conn = psycopg.connect(url)
        try:
            record = fetch_buyer_lead(verify_conn, LeadId(lead_id_value)) if lead_id_value else None
            step5b_ok = (
                record is not None
                and record.publishing_organization_id == org.id
                and record.contact_email_verification_state.value == "UNVERIFIED"
                and record.account_id is None
            )
            ok &= step5b_ok
            print(
                "5b. readback: UNVERIFIED email + real publishing Organization + no "
                f"AccountId -> {'OK' if step5b_ok else 'FAIL'}\n"
            )
        finally:
            verify_conn.close()

        # 6. exact retry is idempotent.
        retry_status, retry_body = _http_post_json(
            contact_url,
            {
                "submission_operation_id": "OP-0070-E2E-1",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
            },
            origin=web_base,
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        step6_ok = (
            retry_status == 200
            and retry_body.get("status") == "ALREADY_EXISTS"
            and retry_body.get("lead_id") == lead_id_value
        )
        ok &= step6_ok
        print(f"6. exact retry is idempotent (same lead_id) -> {'OK' if step6_ok else 'FAIL'}")

        # 7. same operation id, different envelope -> conflict.
        conflict_status, conflict_body = _http_post_json(
            contact_url,
            {
                "submission_operation_id": "OP-0070-E2E-1",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "A completely different message.",
            },
            origin=web_base,
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        step7_ok = conflict_status == 409 and conflict_body.get("error") == "submission_conflict"
        ok &= step7_ok
        print(f"7. conflicting reuse of the same operation id -> {'OK' if step7_ok else 'FAIL'}")

        # 8. invalid input -> zero mutation.
        invalid_status, invalid_body = _http_post_json(
            contact_url,
            {"submission_operation_id": "OP-0070-E2E-2", "name": "", "email": "jane@example.com", "message": "Hi"},
            origin=web_base,
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        step8_ok = invalid_status == 400 and invalid_body.get("error") == "invalid_input"
        ok &= step8_ok
        print(f"8. invalid input produces zero mutation -> {'OK' if step8_ok else 'FAIL'}")

        verify_conn = psycopg.connect(url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM buyer_leads WHERE native_listing_id = %s", [_LISTING_ID]
                )
                lead_count = cur.fetchone()[0]
            step8b_ok = lead_count == 1
            ok &= step8b_ok
            print(f"   exactly one durable Lead row exists -> {'OK' if step8b_ok else 'FAIL'}\n")
        finally:
            verify_conn.close()

        # 9. FastAPI's own CSRF boundary, independent of the Astro proxy.
        direct_api_contact_url = f"{api_base}/api/listings/{_LISTING_ID}/contact"
        wrong_origin_status, _wrong_origin_body = _http_post_json(
            direct_api_contact_url,
            {
                "submission_operation_id": "OP-0070-E2E-3",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
            },
            origin="http://evil.test",
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        step9_ok = wrong_origin_status == 403
        ok &= step9_ok
        print(f"9. FastAPI rejects a wrong-Origin direct POST -> {'OK' if step9_ok else 'FAIL'}\n")

        # 10. withdraw the listing: contact route + public page both fail closed.
        withdraw_conn = psycopg.connect(url)
        try:
            withdraw_result = withdraw_native_listing(
                withdraw_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
            )
            assert withdraw_result.status.value == "transitioned", withdraw_result
            withdraw_conn.commit()
        finally:
            withdraw_conn.close()

        after_withdraw_status, after_withdraw_body = _http_post_json(
            contact_url,
            {
                "submission_operation_id": "OP-0070-E2E-4",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
            },
            origin=web_base,
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        after_withdraw_page_status, after_withdraw_page_body = _http_get(
            f"{web_base}/listings/{_LISTING_ID}"
        )
        step10_ok = (
            after_withdraw_status == 404
            and after_withdraw_body.get("error") == "listing_not_available"
            and after_withdraw_page_status == 404
            and b"data-buyer-contact-form" not in after_withdraw_page_body
        )
        ok &= step10_ok
        print(
            "10. withdrawn listing: contact route + public page both fail closed, "
            f"no Lead created -> {'OK' if step10_ok else 'FAIL'}"
        )

        verify_conn = psycopg.connect(url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM buyer_leads WHERE native_listing_id = %s", [_LISTING_ID]
                )
                final_lead_count = cur.fetchone()[0]
            step10b_ok = final_lead_count == 1
            ok &= step10b_ok
            print(f"    still exactly one durable Lead row -> {'OK' if step10b_ok else 'FAIL'}\n")
        finally:
            verify_conn.close()

        # 11. Finding A: an exact retry of the ORIGINAL (already-created)
        # operation must still resolve to the existing Lead even after the
        # listing has since become unavailable -- contract §4's idempotent-
        # retry guarantee is independent of current listing state.
        retry_after_withdraw_status, retry_after_withdraw_body = _http_post_json(
            contact_url,
            {
                "submission_operation_id": "OP-0070-E2E-1",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
            },
            origin=web_base,
            csrf_header_value="marketplace-buyer-lead-v1",
        )
        step11_ok = (
            retry_after_withdraw_status == 200
            and retry_after_withdraw_body.get("status") == "ALREADY_EXISTS"
            and retry_after_withdraw_body.get("lead_id") == lead_id_value
        )
        ok &= step11_ok
        print(
            "11. exact retry of the already-created Lead still resolves after "
            f"withdrawal (Finding A) -> {'OK' if step11_ok else 'FAIL'}"
        )

        verify_conn = psycopg.connect(url)
        try:
            with verify_conn.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM buyer_leads WHERE native_listing_id = %s", [_LISTING_ID]
                )
                after_retry_lead_count = cur.fetchone()[0]
            step11b_ok = after_retry_lead_count == 1
            ok &= step11b_ok
            print(f"    still exactly one durable Lead row -> {'OK' if step11b_ok else 'FAIL'}\n")
        finally:
            verify_conn.close()

        print(f"DURABLE BUYER CONTACT / LEAD CREATION RESULT -> {'PASS' if ok else 'FAIL'}")
        return 0 if ok else 1
    finally:
        if api_proc is not None:
            api_proc.terminate()
            try:
                api_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_proc.kill()
        if web_proc is not None:
            web_proc.terminate()
            try:
                web_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                web_proc.kill()
        _drop_schema(base_url, schema_name)
        print(f"\nLogs retained at: {log_dir}")


if __name__ == "__main__":
    raise SystemExit(main())
