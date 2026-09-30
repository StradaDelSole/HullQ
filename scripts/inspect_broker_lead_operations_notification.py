"""SLICE-0071 owner-visible end-to-end proof — real PostgreSQL + real HTTP.

Executes the broker Lead operations + durable email notification vertical
against a real, disposable PostgreSQL schema and real local HTTP servers
(FastAPI + built Astro/Node SSR), per
`specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md` §17:

    1. accepted SLICE-0070 Lead appears in correct Organization inbox
    2. foreign Organization cannot enumerate/read it
    3. broker opens detail with source/listing context
    4. assign/status/note/read workflow persists
    5. OWNER/ADMIN configures notification recipient; PUBLISHER-only cannot
    6. one durable notification intent per Lead
    7. test email adapter receives one HullQ-authored notification with
       dashboard deep-link and UNVERIFIED label
    8. retryable delivery failure preserves Lead and later succeeds without
       duplicate committed delivery
    9. no recipient produces visible Lead plus explicit no-recipient state
    10. listing withdrawal does not remove historical Lead
    11. acquisition/discovery provenance is UNKNOWN when absent
    12. follow-up due/overdue filtering and dashboard counts are correct
    13. structured contact attempts append to timeline without implying
        buyer response
    14. closing requires a bounded close reason, no SaleOutcome/lifecycle
        change
    15. listing/Search/public truth unchanged

Items 1-4 and 10 are driven through real HTTP against the built Astro pages
(broker inbox/detail/notifications, including real form-POST mutations) and
FastAPI underneath. The delivery worker (items 6-9) is exercised via direct
in-process calls against the *same* live PostgreSQL schema -- contract §14:
it is deliberately "not a public unauthenticated business endpoint", so
calling the production application function directly is the correct
integration point, not a shortcut. Items 11-15 are verified similarly.

Requires ``HULLQ_TEST_DATABASE_URL`` (a local PostgreSQL instance) and a
pre-built Astro web package (``cd web && npm ci && npm run build``).

Run: uv run python scripts/inspect_broker_lead_operations_notification.py
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
import urllib.parse
import urllib.request
import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from _publication_readiness_fixture import attach_d22_minimum_cover_image

from hullq.application.lead_notification_delivery import (
    DeliverySendOutcome,
    DeliverySendResult,
    DeterministicLocalNotificationAdapter,
    WorkerRunOutcome,
    run_delivery_worker_once,
)
from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.buyer_lead import LeadId, SubmissionOperationId
from hullq.domain.lead_operations import LeadCloseReason
from hullq.domain.lead_provenance import DiscoverySurface
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.persistence.buyer_lead import create_buyer_lead
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.lead_notification import fetch_organization_notification_config
from hullq.persistence.lead_operations import (
    fetch_lead_detail,
    fetch_organization_lead_counts,
    set_lead_follow_up_due_at,
)
from hullq.persistence.lead_provenance import fetch_lead_acquisition_provenance
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
from hullq.security.discovery_surface_signing import mint_discovery_surface_token
from hullq.security.session_token import mint_session_token

REPO_ROOT = Path(__file__).resolve().parents[1]
WEB_DIR = REPO_ROOT / "web"
WEB_ENTRYPOINT = WEB_DIR / "dist" / "server" / "entry.mjs"

_SESSION_SECRET = os.urandom(32)


def _base_db_url() -> str:
    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(f"{HULLQ_TEST_DATABASE_URL_ENV} is not set.", file=sys.stderr)
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


def _http_get(url: str, *, cookie: str | None = None) -> tuple[int, bytes]:
    headers = {"Cookie": cookie} if cookie else {}
    request = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _http_post_form(
    url: str, fields: dict[str, str], *, cookie: str, origin: str
) -> tuple[int, bytes]:
    body = urllib.parse.urlencode(fields).encode("ascii")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Cookie": cookie,
            "Origin": origin,
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read()


def _session_cookie(account_id: str) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=True,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SESSION_SECRET)
    return f"hullq_session={minted.token}"


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _publish_listing(
    conn: Any, *, listing_id: str, account: AccountId, org: MarketplaceOrganization
) -> None:
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-owner-{listing_id}"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-{listing_id}")))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(f"ME-{listing_id}"),
            physical_boat_id=PhysicalBoatId(f"PB-{listing_id}"),
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
    conn.commit()
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result


def _create_lead(conn: Any, *, listing_id: str, op_suffix: str) -> str:
    result = create_buyer_lead(
        conn,
        submission_operation_id=SubmissionOperationId(f"OP-{listing_id}-{op_suffix}"),
        native_listing_id=NativeListingId(listing_id),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=datetime.now(UTC),
    )
    conn.commit()
    assert result.status.value == "created", result
    assert result.lead_id is not None
    return result.lead_id.value


def main() -> int:
    if not WEB_ENTRYPOINT.exists():
        print(f"{WEB_ENTRYPOINT} does not exist. Build the web package first.", file=sys.stderr)
        return 1

    base_url = _base_db_url()
    schema_name = f"hullq_s0071e2e_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)

    log_dir = Path(tempfile.mkdtemp(prefix="hullq_s0071_e2e_"))
    api_proc: subprocess.Popen[bytes] | None = None
    web_proc: subprocess.Popen[bytes] | None = None
    ok = True

    try:
        url = _with_search_path(base_url, schema_name)
        print("BROKER LEAD OPERATIONS + NOTIFICATION\n")

        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)
        print("Alembic upgraded to current head -> OK\n")

        org_a = _org("ORG-0071-A")
        org_b = _org("ORG-0071-B")
        org_c = _org("ORG-0071-C")
        owner_account = AccountId("ACC-0071-OWNER")
        publisher_only_account = AccountId("ACC-0071-PUBLISHER-ONLY")
        foreign_account = AccountId("ACC-0071-FOREIGN")

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                for account_value in (
                    owner_account.value,
                    foreign_account.value,
                    publisher_only_account.value,
                ):
                    cur.execute(
                        "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        [account_value],
                    )
            conn.commit()

            _publish_listing(conn, listing_id="NL-0071-A", account=owner_account, org=org_a)
            lead_id = _create_lead(conn, listing_id="NL-0071-A", op_suffix="1")

            seed_marketplace_organization(conn, org_b)
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0071-B"),
                    account_id=foreign_account,
                    organization_id=org_b.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0071-A-OWNER"),
                    account_id=owner_account,
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER, MembershipRole.OWNER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            seed_organization_membership(
                conn,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0071-A-PUB"),
                    account_id=publisher_only_account,
                    organization_id=org_a.id,
                    roles=frozenset({MembershipRole.PUBLISHER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn.commit()
        finally:
            conn.close()
        print("Org/membership/listing/Lead fixtures seeded -> OK\n")

        api_port = _free_port()
        web_port = _free_port()
        web_base = f"http://127.0.0.1:{web_port}"

        # SLICE-0071 independent-review Finding B: FastAPI's search route
        # (TECHNICAL_SEARCH) and Astro's own trusted shortlist/compare
        # resolution routes (`web/src/lib/discoverySurfaceSigning.ts`) mint
        # discovery-surface tokens under the *same* shared secret -- both
        # processes must be given the identical value below.
        shared_signing_secret_bytes = os.urandom(32)
        shared_preview_signing_secret = base64.urlsafe_b64encode(
            shared_signing_secret_bytes
        ).decode("ascii")

        api_env = dict(os.environ)
        api_env["HULLQ_DATABASE_URL"] = url
        api_env["HULLQ_PREVIEW_SIGNING_SECRET"] = shared_preview_signing_secret
        api_env["HULLQ_SESSION_SIGNING_SECRET"] = base64.urlsafe_b64encode(_SESSION_SECRET).decode(
            "ascii"
        )
        api_env["HULLQ_SESSION_COOKIE_SECURE"] = "false"
        api_env["HULLQ_WEB_ORIGIN"] = web_base

        api_log = (log_dir / "api.log").open("wb")
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
        api_ready = _wait_for_http(f"{api_base}/api/broker/context")
        ok &= api_ready
        print(f"FastAPI serving -> {'OK' if api_ready else 'FAIL'}")

        web_env = dict(os.environ)
        web_env["HULLQ_API_BASE_URL"] = api_base
        web_env["HOST"] = "127.0.0.1"
        web_env["PORT"] = str(web_port)
        # Same secret FastAPI holds -- see the Finding B comment above.
        web_env["HULLQ_PREVIEW_SIGNING_SECRET"] = shared_preview_signing_secret
        web_log = (log_dir / "web.log").open("wb")
        web_proc = subprocess.Popen(
            ["node", "./dist/server/entry.mjs"],
            cwd=WEB_DIR,
            env=web_env,
            stdout=web_log,
            stderr=subprocess.STDOUT,
        )
        web_ready = _wait_for_http(f"{web_base}/broker/organizations/{org_a.id.value}/leads")
        ok &= web_ready
        print(f"Astro SSR serving -> {'OK' if web_ready else 'FAIL'}\n")
        if not ok:
            return 1

        owner_cookie = _session_cookie(owner_account.value)
        foreign_cookie = _session_cookie(foreign_account.value)
        publisher_only_cookie = _session_cookie(publisher_only_account.value)

        # 1. accepted SLICE-0070 Lead appears in correct Organization inbox.
        inbox_status, inbox_body = _http_get(
            f"{web_base}/broker/organizations/{org_a.id.value}/leads", cookie=owner_cookie
        )
        step1_ok = (
            inbox_status == 200 and lead_id.encode() in inbox_body and b"Jane Buyer" in inbox_body
        )
        ok &= step1_ok
        print(f"1. Lead appears in correct Organization inbox -> {'OK' if step1_ok else 'FAIL'}")

        # 2. foreign Organization cannot enumerate/read it.
        foreign_status, _ = _http_get(
            f"{web_base}/broker/organizations/{org_a.id.value}/leads/{lead_id}",
            cookie=foreign_cookie,
        )
        step2_ok = foreign_status == 404
        ok &= step2_ok
        print(
            f"2. foreign Organization membership cannot read the Lead -> {'OK' if step2_ok else 'FAIL'}"
        )

        # 3. broker opens detail with source/listing context.
        detail_status, detail_body = _http_get(
            f"{web_base}/broker/organizations/{org_a.id.value}/leads/{lead_id}", cookie=owner_cookie
        )
        step3_ok = (
            detail_status == 200
            and b"NL-0071-A" in detail_body
            and b"HULLQ_PUBLIC_LISTING_CONTACT" in detail_body
            and b"UNVERIFIED" in detail_body
        )
        ok &= step3_ok
        print(
            f"3. broker opens detail with source/listing context -> {'OK' if step3_ok else 'FAIL'}"
        )

        # 4. assign/status/note/read/contact-attempt/follow-up workflow persists,
        #    all through real Astro form-POSTs (contract §4/§6/§7/§8/§8A).
        detail_url = f"{web_base}/broker/organizations/{org_a.id.value}/leads/{lead_id}"

        def _current_version() -> int:
            conn2 = psycopg.connect(url)
            try:
                record = fetch_lead_detail(conn2, LeadId(lead_id))
                assert record is not None
                return record.operational_state.version
            finally:
                conn2.close()

        _http_post_form(detail_url, {"action": "mark_read"}, cookie=owner_cookie, origin=web_base)
        assign_status, _ = _http_post_form(
            detail_url,
            {
                "action": "assign",
                "assignee_account_id": owner_account.value,
                "expected_version": "0",
            },
            cookie=owner_cookie,
            origin=web_base,
        )
        status_status, _ = _http_post_form(
            detail_url,
            {
                "action": "set_status",
                "status": "IN_PROGRESS",
                "expected_version": str(_current_version()),
            },
            cookie=owner_cookie,
            origin=web_base,
        )
        note_status, _ = _http_post_form(
            detail_url,
            {"action": "add_note", "text": "Called the buyer, left a voicemail."},
            cookie=owner_cookie,
            origin=web_base,
        )
        contact_status, _ = _http_post_form(
            detail_url,
            {"action": "add_contact_attempt", "channel": "PHONE", "note": "No answer."},
            cookie=owner_cookie,
            origin=web_base,
        )
        follow_up_due = (datetime.now(UTC) + timedelta(days=1)).isoformat()
        follow_up_status, _ = _http_post_form(
            detail_url,
            {
                "action": "set_follow_up",
                "due_at": follow_up_due,
                "expected_version": str(_current_version()),
            },
            cookie=owner_cookie,
            origin=web_base,
        )
        final_status, final_body = _http_get(detail_url, cookie=owner_cookie)
        step4_ok = (
            all(
                s == 200
                for s in (
                    assign_status,
                    status_status,
                    note_status,
                    contact_status,
                    follow_up_status,
                    final_status,
                )
            )
            and b"IN_PROGRESS" in final_body
            and b"Called the buyer" in final_body
            and b"CONTACT_ATTEMPT" in final_body
            and b"Read" in final_body
        )
        ok &= step4_ok
        print(
            f"4. assign/status/note/read/contact-attempt/follow-up workflow persists -> {'OK' if step4_ok else 'FAIL'}"
        )

        # 13. structured contact attempt never implies buyer response.
        conn3 = psycopg.connect(url)
        try:
            record = fetch_lead_detail(conn3, LeadId(lead_id))
            assert record is not None
            step13_ok = record.contact_email_verification_state.value == "UNVERIFIED"
        finally:
            conn3.close()
        ok &= step13_ok
        print(
            f"13. contact attempt never implies buyer response/verification -> {'OK' if step13_ok else 'FAIL'}"
        )

        # 5. OWNER/ADMIN configures notification recipient; PUBLISHER-only cannot.
        notif_url = f"{web_base}/broker/organizations/{org_a.id.value}/notifications"
        owner_set_status, owner_set_body = _http_post_form(
            notif_url,
            {"notification_email": "broker@example.com", "expected_version": "0"},
            cookie=owner_cookie,
            origin=web_base,
        )
        publisher_set_status, publisher_set_body = _http_post_form(
            notif_url,
            {"notification_email": "sneaky@example.com", "expected_version": "0"},
            cookie=publisher_only_cookie,
            origin=web_base,
        )
        step5_ok = (
            owner_set_status == 200
            and b"Saved" in owner_set_body
            and publisher_set_status == 200
            and b"Only an OWNER or ADMIN" in publisher_set_body
        )
        ok &= step5_ok
        print(
            f"5. OWNER can configure recipient; PUBLISHER-only is denied -> {'OK' if step5_ok else 'FAIL'}"
        )

        conn4 = psycopg.connect(url)
        try:
            config = fetch_organization_notification_config(conn4, org_a.id)
            step5b_ok = config.notification_email == "broker@example.com"
        finally:
            conn4.close()
        ok &= step5b_ok
        print(
            f"5b. durable recipient config reflects only the OWNER's change -> {'OK' if step5b_ok else 'FAIL'}\n"
        )

        # 6/7. one durable notification intent per Lead; adapter receives one
        # HullQ-authored notification with dashboard deep-link + UNVERIFIED.
        conn5 = psycopg.connect(url)
        try:
            with conn5.cursor() as cur:
                cur.execute(
                    "SELECT COUNT(*) FROM lead_notification_outbox WHERE lead_id = %s", [lead_id]
                )
                (outbox_count,) = cur.fetchone()
            step6_ok = outbox_count == 1
            ok &= step6_ok
            print(
                f"6. exactly one durable notification intent for the Lead -> {'OK' if step6_ok else 'FAIL'}"
            )

            adapter = DeterministicLocalNotificationAdapter()
            worker_result = run_delivery_worker_once(
                conn5,
                adapter=adapter,
                worker_id="e2e-worker",
                as_of=datetime.now(UTC),
                web_base_url=web_base,
            )
            step7_ok = (
                worker_result.outcome is WorkerRunOutcome.DELIVERED
                and len(adapter.sent) == 1
                and adapter.sent[0].to_email == "broker@example.com"
                and "UNVERIFIED" in adapter.sent[0].body
                and f"/leads/{lead_id}" in adapter.sent[0].body
            )
            ok &= step7_ok
            print(
                f"7. adapter receives one notification with deep-link + UNVERIFIED -> {'OK' if step7_ok else 'FAIL'}\n"
            )
        finally:
            conn5.close()

        # 8. retryable delivery failure preserves the Lead and later succeeds.
        conn6 = psycopg.connect(url)
        try:
            lead_id_2 = _create_lead(conn6, listing_id="NL-0071-A", op_suffix="2")
            adapter2 = DeterministicLocalNotificationAdapter()
            adapter2.queue_outcome(
                DeliverySendResult(
                    outcome=DeliverySendOutcome.RETRYABLE_ERROR, error_text="smtp timeout"
                )
            )
            first_run = run_delivery_worker_once(
                conn6,
                adapter=adapter2,
                worker_id="e2e-worker",
                as_of=datetime.now(UTC),
                web_base_url=web_base,
            )
            lead_after_failure = fetch_lead_detail(conn6, LeadId(lead_id_2))
            later = datetime.now(UTC) + timedelta(seconds=1000)
            second_run = run_delivery_worker_once(
                conn6, adapter=adapter2, worker_id="e2e-worker", as_of=later, web_base_url=web_base
            )
            step8_ok = (
                first_run.outcome is WorkerRunOutcome.RETRYABLE_FAILURE
                and lead_after_failure is not None
                and second_run.outcome is WorkerRunOutcome.DELIVERED
                and len(adapter2.sent) == 2
            )
        finally:
            conn6.close()
        ok &= step8_ok
        print(
            f"8. retryable failure preserves Lead, later succeeds without duplicate delivery -> {'OK' if step8_ok else 'FAIL'}"
        )

        # 9. no recipient produces visible Lead plus explicit no-recipient state.
        conn7 = psycopg.connect(url)
        try:
            _publish_listing(conn7, listing_id="NL-0071-C", account=owner_account, org=org_c)
            lead_id_3 = _create_lead(conn7, listing_id="NL-0071-C", op_suffix="1")
            seed_organization_membership(
                conn7,
                OrganizationMembership(
                    id=OrganizationMembershipId("OM-0071-C"),
                    account_id=owner_account,
                    organization_id=org_c.id,
                    roles=frozenset({MembershipRole.PUBLISHER, MembershipRole.OWNER}),
                    state=MembershipState.ACTIVE,
                ),
            )
            conn7.commit()
            no_recipient_adapter = DeterministicLocalNotificationAdapter()
            no_recipient_run = run_delivery_worker_once(
                conn7,
                adapter=no_recipient_adapter,
                worker_id="e2e-worker",
                as_of=datetime.now(UTC),
                web_base_url=web_base,
            )
        finally:
            conn7.close()
        no_recipient_page_status, no_recipient_page_body = _http_get(
            f"{web_base}/broker/organizations/{org_c.id.value}/leads/{lead_id_3}",
            cookie=owner_cookie,
        )
        step9_ok = (
            no_recipient_run.outcome is WorkerRunOutcome.NO_RECIPIENT_CONFIGURED
            and no_recipient_adapter.sent == []
            and no_recipient_page_status == 200
            and b"NO_RECIPIENT_CONFIGURED" in no_recipient_page_body
        )
        ok &= step9_ok
        print(
            f"9. no-recipient Lead stays visible with explicit no-recipient state -> {'OK' if step9_ok else 'FAIL'}\n"
        )

        # 11. acquisition/discovery provenance is UNKNOWN when absent.
        conn8 = psycopg.connect(url)
        try:
            provenance = fetch_lead_acquisition_provenance(conn8, LeadId(lead_id))
            step11_ok = (
                provenance is not None
                and provenance.acquisition_channel.value == "UNKNOWN"
                and provenance.discovery_surface.value == "UNKNOWN"
            )
        finally:
            conn8.close()
        ok &= step11_ok
        print(
            f"11. acquisition/discovery provenance is UNKNOWN when absent -> {'OK' if step11_ok else 'FAIL'}"
        )

        # 11b. Finding A/B amendment: at least one non-UNKNOWN acquisition
        # case and one non-UNKNOWN discovery-surface case through the
        # *real* buyer-facing flow -- the actual Astro contact proxy (never
        # a direct persistence call), carrying bounded UTM evidence exactly
        # as `buyerLeadForm.ts` would construct it, plus a genuine signed
        # discovery token obtained from Astro's own trusted
        # `/api/shortlist/resolve` route (the exact same production path
        # `web/src/lib/shortlistPageRuntime.ts` uses) -- never the removed,
        # insecure `discovery_surface_context` query parameter on FastAPI's
        # public listing route (Finding B).
        conn11b = psycopg.connect(url)
        try:
            _publish_listing(conn11b, listing_id="NL-0071-D", account=owner_account, org=org_a)
        finally:
            conn11b.close()

        shortlist_resolve_payload = json.dumps({"listing_ids": ["NL-0071-D"]}).encode("utf-8")
        shortlist_resolve_request = urllib.request.Request(
            f"{web_base}/api/shortlist/resolve",
            data=shortlist_resolve_payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(shortlist_resolve_payload)),
            },
        )
        try:
            with urllib.request.urlopen(shortlist_resolve_request, timeout=10) as response:
                shortlist_resolve_body = json.loads(response.read())
        except urllib.error.HTTPError:
            shortlist_resolve_body = {}
        shortlist_items = shortlist_resolve_body.get("items", [])
        discovery_token = (
            shortlist_items[0].get("data", {}).get("discovery_token")
            if shortlist_items and shortlist_items[0].get("state") == "available"
            else None
        )

        # Finding B negative proof: the same listing, hit directly against
        # FastAPI's public route with the now-removed parameter, must never
        # yield an authoritative token.
        direct_param_status, direct_param_body = _http_get(
            f"{api_base}/api/listings/NL-0071-D?discovery_surface_context=SHORTLIST"
        )
        step11a_ok = direct_param_status == 200 and "discovery_token" not in json.loads(
            direct_param_body
        )
        ok &= step11a_ok
        print(
            "11a. public discovery_surface_context parameter no longer mints "
            f"an authoritative token -> {'OK' if step11a_ok else 'FAIL'}"
        )

        contact_payload = json.dumps(
            {
                "submission_operation_id": "OP-0071-D-REAL-FLOW",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
                "utm_source": "google",
                "utm_medium": "cpc",
                "utm_campaign": "summer-sale",
                "discovery_token": discovery_token,
            }
        ).encode("utf-8")
        contact_request = urllib.request.Request(
            f"{web_base}/listings/NL-0071-D/contact",
            data=contact_payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(contact_payload)),
                # A real browser's same-origin fetch() always carries this;
                # Astro's contact proxy only forwards an Origin it actually
                # received (never substitutes a trusted one), and FastAPI's
                # CSRF boundary requires an exact match.
                "Origin": web_base,
            },
        )
        try:
            with urllib.request.urlopen(contact_request, timeout=10) as response:
                real_flow_status, real_flow_body = response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            real_flow_status, real_flow_body = exc.code, {}

        conn11c = psycopg.connect(url)
        try:
            real_flow_provenance = (
                fetch_lead_acquisition_provenance(conn11c, LeadId(real_flow_body["lead_id"]))
                if "lead_id" in real_flow_body
                else None
            )
        finally:
            conn11c.close()
        step11b_ok = (
            discovery_token is not None
            and real_flow_status in (200, 201)
            and real_flow_provenance is not None
            and real_flow_provenance.acquisition_channel.value == "PAID_SEARCH"
            and real_flow_provenance.discovery_surface.value == "SHORTLIST"
        )
        ok &= step11b_ok
        print(
            "11b. real buyer-facing flow (Astro proxy) persists non-UNKNOWN "
            f"PAID_SEARCH acquisition + SHORTLIST discovery -> {'OK' if step11b_ok else 'FAIL'}\n"
        )

        # 11c. Finding C negative proof: a spoofed same-origin Referer header
        # alone must never cause the listing page to mint/persist an
        # authoritative INTERNAL_BROWSE (or any other) token -- any direct
        # HTTP client can send an arbitrary Referer with no real browser
        # navigation at all. No `?ds=` token is supplied on either request.
        conn11c_fixture = psycopg.connect(url)
        try:
            _publish_listing(
                conn11c_fixture, listing_id="NL-0071-E", account=owner_account, org=org_a
            )
        finally:
            conn11c_fixture.close()

        spoofed_referer = f"{web_base}/broker/organizations/{org_a.id.value}/leads"
        spoofed_referer_request = urllib.request.Request(
            f"{web_base}/listings/NL-0071-E", headers={"Referer": spoofed_referer}
        )
        try:
            with urllib.request.urlopen(spoofed_referer_request, timeout=10) as response:
                spoofed_status, spoofed_body = response.status, response.read()
        except urllib.error.HTTPError as exc:
            spoofed_status, spoofed_body = exc.code, exc.read()
        step11c_page_ok = spoofed_status == 200 and b'data-discovery-token="' not in spoofed_body

        no_token_contact_payload = json.dumps(
            {
                "submission_operation_id": "OP-0071-E-SPOOFED-REFERER",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
            }
        ).encode("utf-8")
        no_token_contact_request = urllib.request.Request(
            f"{web_base}/listings/NL-0071-E/contact",
            data=no_token_contact_payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(no_token_contact_payload)),
                "Origin": web_base,
                # The same spoofed Referer, this time on the actual contact
                # submission -- FastAPI's contact route never reads Referer
                # for discovery purposes at all, so this must have zero
                # bearing on the persisted result.
                "Referer": spoofed_referer,
            },
        )
        try:
            with urllib.request.urlopen(no_token_contact_request, timeout=10) as response:
                no_token_status, no_token_body = response.status, json.loads(response.read())
        except urllib.error.HTTPError as exc:
            no_token_status, no_token_body = exc.code, {}
        conn11c_check = psycopg.connect(url)
        try:
            no_token_provenance = (
                fetch_lead_acquisition_provenance(conn11c_check, LeadId(no_token_body["lead_id"]))
                if "lead_id" in no_token_body
                else None
            )
        finally:
            conn11c_check.close()
        step11c_ok = (
            step11c_page_ok
            and no_token_status in (200, 201)
            and no_token_provenance is not None
            and no_token_provenance.discovery_surface.value == "UNKNOWN"
        )
        ok &= step11c_ok
        print(
            "11c. a spoofed same-origin Referer alone never mints/persists "
            f"INTERNAL_BROWSE -- resolves UNKNOWN instead -> {'OK' if step11c_ok else 'FAIL'}"
        )

        # 11d. Finding C positive proof: a genuine trusted mint of
        # INTERNAL_BROWSE (the same shared-secret mechanism every trusted
        # HullQ surface uses to mint SHORTLIST/COMPARE/TECHNICAL_SEARCH
        # tokens) does persist through the real contact flow. No concrete
        # production page currently mints INTERNAL_BROWSE in this slice (a
        # disclosed scope boundary -- see the amendment report); this proves
        # the mechanism itself genuinely supports it for whichever trusted
        # surface adopts it next, while step 11c proves an unauthenticated
        # Referer can never forge the same outcome.
        conn11d_fixture = psycopg.connect(url)
        try:
            _publish_listing(
                conn11d_fixture, listing_id="NL-0071-F", account=owner_account, org=org_a
            )
        finally:
            conn11d_fixture.close()

        genuine_internal_browse_token = mint_discovery_surface_token(
            DiscoverySurface.INTERNAL_BROWSE, "NL-0071-F", secret=shared_signing_secret_bytes
        )
        internal_browse_contact_payload = json.dumps(
            {
                "submission_operation_id": "OP-0071-F-INTERNAL-BROWSE",
                "name": "Jane Buyer",
                "email": "jane@example.com",
                "message": "Interested in this boat.",
                "discovery_token": genuine_internal_browse_token,
            }
        ).encode("utf-8")
        internal_browse_contact_request = urllib.request.Request(
            f"{web_base}/listings/NL-0071-F/contact",
            data=internal_browse_contact_payload,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Content-Length": str(len(internal_browse_contact_payload)),
                "Origin": web_base,
            },
        )
        try:
            with urllib.request.urlopen(internal_browse_contact_request, timeout=10) as response:
                internal_browse_status, internal_browse_body = (
                    response.status,
                    json.loads(response.read()),
                )
        except urllib.error.HTTPError as exc:
            internal_browse_status, internal_browse_body = exc.code, {}
        conn11d_check = psycopg.connect(url)
        try:
            internal_browse_provenance = (
                fetch_lead_acquisition_provenance(
                    conn11d_check, LeadId(internal_browse_body["lead_id"])
                )
                if "lead_id" in internal_browse_body
                else None
            )
        finally:
            conn11d_check.close()
        step11d_ok = (
            internal_browse_status in (200, 201)
            and internal_browse_provenance is not None
            and internal_browse_provenance.discovery_surface.value == "INTERNAL_BROWSE"
        )
        ok &= step11d_ok
        print(
            "11d. a genuine trusted mint persists INTERNAL_BROWSE through the "
            f"real contact flow -> {'OK' if step11d_ok else 'FAIL'}\n"
        )

        # 12. follow-up due/overdue filtering and dashboard counts are correct.
        conn9 = psycopg.connect(url)
        try:
            now = datetime.now(UTC)
            not_yet_due_counts = fetch_organization_lead_counts(conn9, org_a.id, as_of=now)
            not_yet_due_ok = (
                not_yet_due_counts.follow_up_due == 0 and not_yet_due_counts.follow_up_overdue == 0
            )
            conn9.commit()  # end the read's implicit transaction before the write below.

            past_due_result = set_lead_follow_up_due_at(
                conn9,
                LeadId(lead_id),
                due_at=now - timedelta(hours=1),
                actor_account_id=owner_account,
                expected_version=_current_version(),
                as_of=now,
            )
            assert past_due_result.updated, past_due_result
            overdue_counts = fetch_organization_lead_counts(conn9, org_a.id, as_of=now)
            overdue_ok = overdue_counts.follow_up_due == 1 and overdue_counts.follow_up_overdue == 1
        finally:
            conn9.close()
        follow_up_inbox_status, follow_up_inbox_body = _http_get(
            f"{web_base}/broker/organizations/{org_a.id.value}/leads?follow_up_due=true",
            cookie=owner_cookie,
        )
        step12_ok = (
            not_yet_due_ok
            and overdue_ok
            and follow_up_inbox_status == 200
            and lead_id.encode() in follow_up_inbox_body
        )
        ok &= step12_ok
        print(
            f"12. follow-up due/overdue filtering and dashboard counts are correct -> {'OK' if step12_ok else 'FAIL'}"
        )

        # 14. closing requires a bounded close reason; no lifecycle change.
        version_before_rejected_close = _current_version()
        close_no_reason_status, _close_no_reason_body = _http_post_form(
            detail_url,
            {"action": "close", "expected_version": str(version_before_rejected_close)},
            cookie=owner_cookie,
            origin=web_base,
        )
        # A rejected close (missing close_reason) must never advance the
        # optimistic-concurrency version -- the mutation itself never ran.
        step14_rejected_ok = (
            close_no_reason_status == 200 and _current_version() == version_before_rejected_close
        )
        close_status, _ = _http_post_form(
            detail_url,
            {
                "action": "close",
                "close_reason": "NOT_INTERESTED",
                "expected_version": str(_current_version()),
            },
            cookie=owner_cookie,
            origin=web_base,
        )
        conn10 = psycopg.connect(url)
        try:
            record_after_close = fetch_lead_detail(conn10, LeadId(lead_id))
            assert record_after_close is not None
            step14_ok = (
                step14_rejected_ok
                and close_status == 200
                and record_after_close.operational_state.close_reason
                is LeadCloseReason.NOT_INTERESTED
                and record_after_close.operational_state.operational_status.value == "CLOSED"
            )
        finally:
            conn10.close()
        ok &= step14_ok
        print(
            f"14. closing requires a bounded close reason, no lifecycle change -> {'OK' if step14_ok else 'FAIL'}\n"
        )

        # 10. listing withdrawal does not remove historical Lead.
        withdraw_conn = psycopg.connect(url)
        try:
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-owner-NL-0071-A"),
                account_id=owner_account,
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            withdraw_result = withdraw_native_listing(
                withdraw_conn,
                account_id=owner_account,
                candidate_organization=org_a,
                membership=membership_a,
                native_listing_id=NativeListingId("NL-0071-A"),
            )
            assert withdraw_result.status.value == "transitioned", withdraw_result
            withdraw_conn.commit()
        finally:
            withdraw_conn.close()

        after_withdraw_status, after_withdraw_body = _http_get(detail_url, cookie=owner_cookie)
        step10_ok = (
            after_withdraw_status == 200
            and b"NL-0071-A" in after_withdraw_body
            and b"Jane Buyer" in after_withdraw_body
        )
        ok &= step10_ok
        print(
            f"10. listing withdrawal does not remove historical Lead -> {'OK' if step10_ok else 'FAIL'}"
        )

        # 15. Search/listing/public truth unchanged by any of the above.
        public_status, _ = _http_get(f"{web_base}/listings/NL-0071-A")
        step15_ok = public_status == 404  # withdrawn listing correctly no longer publicly visible
        ok &= step15_ok
        print(
            f"15. public listing truth reflects only its own withdrawal, nothing Lead-driven -> {'OK' if step15_ok else 'FAIL'}"
        )

        print(f"\nBROKER LEAD OPERATIONS + NOTIFICATION RESULT -> {'PASS' if ok else 'FAIL'}")
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
