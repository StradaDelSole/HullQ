"""PostgreSQL-backed broker Lead notification/outbox persistence tests —
SLICE-0071.

Covers `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`
§9/§10/§12/§15: atomic notification-intent creation, idempotent retry, the
claim/retry worker's concurrency guarantees, and OWNER/ADMIN-gated
notification-recipient configuration's optimistic concurrency.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.lead_notification_delivery import (
    DeliverySendOutcome,
    DeliverySendResult,
    DeterministicLocalNotificationAdapter,
    WorkerRunOutcome,
    run_delivery_worker_once,
)
from hullq.domain.buyer_lead import SubmissionOperationId
from hullq.domain.lead_notification import NotificationDeliveryStatus
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
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.buyer_lead import create_buyer_lead
from hullq.persistence.lead_notification import (
    fetch_notification_outbox_by_lead,
    fetch_organization_notification_config,
    set_organization_notification_email,
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

# ---------------------------------------------------------------------------
# Disposable-schema fixture
# ---------------------------------------------------------------------------


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


@pytest.fixture()
def notif_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0071n_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


@pytest.fixture()
def notif_conn(notif_url: str) -> Generator[Any]:
    conn = psycopg.connect(notif_url)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    org: MarketplaceOrganization, account: AccountId, membership_id: str
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _attach_ready_cover_image(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization, account: AccountId
) -> None:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [account.value],
            )
        seed_marketplace_organization(conn, org)
        asset = insert_approved_media_asset(
            conn,
            owner_organization_id=org.id,
            uploaded_by_account_id=account,
            rights_declared=True,
            source_kind=MediaSourceKind.BROKER_UPLOAD,
            source_reference=None,
            original_object_key=f"original/{listing_id}",
            derivative_object_key=f"derivative/{listing_id}",
            content_hash=f"hash-{listing_id}",
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
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _publish_listing(conn: Any, *, listing_id: str) -> MarketplaceOrganization:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return org


def _now() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Atomicity / idempotency (contract §10/§15)
# ---------------------------------------------------------------------------


def test_lead_creation_atomically_creates_exactly_one_notification_intent(notif_conn: Any) -> None:
    _publish_listing(notif_conn, listing_id="N1")
    result = create_buyer_lead(
        notif_conn,
        submission_operation_id=SubmissionOperationId("OP-N1-A"),
        native_listing_id=NativeListingId("N1"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested.",
        as_of=_now(),
    )
    notif_conn.commit()
    assert result.status.value == "created"
    assert result.lead_id is not None

    outbox = fetch_notification_outbox_by_lead(notif_conn, result.lead_id)
    assert outbox is not None
    assert outbox.status is NotificationDeliveryStatus.PENDING
    assert outbox.buyer_email == "jane@example.com"


def test_exact_retry_never_creates_a_second_notification_intent(notif_conn: Any) -> None:
    _publish_listing(notif_conn, listing_id="N2")
    kwargs = {
        "submission_operation_id": SubmissionOperationId("OP-N2-A"),
        "native_listing_id": NativeListingId("N2"),
        "account_id": None,
        "buyer_name": "Jane Buyer",
        "buyer_email": "jane@example.com",
        "buyer_message": "Interested.",
    }
    first = create_buyer_lead(notif_conn, **kwargs, as_of=_now())
    notif_conn.commit()
    second = create_buyer_lead(notif_conn, **kwargs, as_of=_now())
    notif_conn.commit()

    assert first.status.value == "created"
    assert second.status.value == "already_exists"
    assert first.lead_id == second.lead_id

    with notif_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM lead_notification_outbox WHERE lead_id = %s",
            [first.lead_id.value],
        )
        (count,) = cur.fetchone()
    assert count == 1


def test_concurrent_duplicate_submission_creates_one_lead_and_one_intent(notif_url: str) -> None:
    conn = psycopg.connect(notif_url)
    try:
        _publish_listing(conn, listing_id="N3")
    finally:
        conn.close()

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _submit() -> None:
        thread_conn = psycopg.connect(notif_url)
        try:
            barrier.wait()
            result = create_buyer_lead(
                thread_conn,
                submission_operation_id=SubmissionOperationId("OP-N3-RACE"),
                native_listing_id=NativeListingId("N3"),
                account_id=None,
                buyer_name="Jane Buyer",
                buyer_email="jane@example.com",
                buyer_message="Interested.",
                as_of=_now(),
            )
            thread_conn.commit()
            with lock:
                outcomes.append(result.status.value)
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=_submit) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["already_exists", "created"]

    verify_conn = psycopg.connect(notif_url)
    try:
        with verify_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM buyer_leads")
            (lead_count,) = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM lead_notification_outbox")
            (outbox_count,) = cur.fetchone()
    finally:
        verify_conn.close()
    assert lead_count == 1
    assert outbox_count == 1


# ---------------------------------------------------------------------------
# Delivery worker (contract §11/§12/§15)
# ---------------------------------------------------------------------------


def _create_lead_with_recipient(
    conn: Any, *, listing_id: str, recipient: str | None
) -> MarketplaceOrganizationId:
    org = _publish_listing(conn, listing_id=listing_id)
    if recipient is not None:
        set_organization_notification_email(
            conn,
            org.id,
            notification_email=recipient,
            updated_by_account_id=AccountId(f"ACC-owner-{listing_id}"),
            expected_version=0,
        )
        conn.commit()
    result = create_buyer_lead(
        conn,
        submission_operation_id=SubmissionOperationId(f"OP-{listing_id}"),
        native_listing_id=NativeListingId(listing_id),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested.",
        as_of=_now(),
    )
    conn.commit()
    assert result.status.value == "created"
    return org.id


def test_worker_delivers_and_is_idempotent_terminal(notif_conn: Any) -> None:
    _create_lead_with_recipient(notif_conn, listing_id="N4", recipient="broker@example.com")
    adapter = DeterministicLocalNotificationAdapter()

    first_run = run_delivery_worker_once(
        notif_conn, adapter=adapter, worker_id="w1", as_of=_now(), web_base_url="http://web.test"
    )
    assert first_run.outcome is WorkerRunOutcome.DELIVERED
    assert len(adapter.sent) == 1
    assert adapter.sent[0].to_email == "broker@example.com"

    second_run = run_delivery_worker_once(
        notif_conn, adapter=adapter, worker_id="w1", as_of=_now(), web_base_url="http://web.test"
    )
    assert second_run.outcome is WorkerRunOutcome.NO_ITEM_CLAIMED
    assert len(adapter.sent) == 1


def test_worker_records_no_recipient_configured_without_losing_lead(notif_conn: Any) -> None:
    _create_lead_with_recipient(notif_conn, listing_id="N5", recipient=None)
    adapter = DeterministicLocalNotificationAdapter()

    run_result = run_delivery_worker_once(
        notif_conn, adapter=adapter, worker_id="w1", as_of=_now(), web_base_url="http://web.test"
    )
    assert run_result.outcome is WorkerRunOutcome.NO_RECIPIENT_CONFIGURED
    assert adapter.sent == []

    with notif_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buyer_leads")
        (lead_count,) = cur.fetchone()
    assert lead_count == 1


def test_retryable_failure_does_not_affect_lead_and_later_succeeds(notif_conn: Any) -> None:
    _create_lead_with_recipient(notif_conn, listing_id="N6", recipient="broker@example.com")
    adapter = DeterministicLocalNotificationAdapter()
    adapter.queue_outcome(
        DeliverySendResult(outcome=DeliverySendOutcome.RETRYABLE_ERROR, error_text="smtp timeout")
    )

    failing_run = run_delivery_worker_once(
        notif_conn, adapter=adapter, worker_id="w1", as_of=_now(), web_base_url="http://web.test"
    )
    assert failing_run.outcome is WorkerRunOutcome.RETRYABLE_FAILURE

    with notif_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buyer_leads")
        (lead_count,) = cur.fetchone()
    assert lead_count == 1

    later = _now() + timedelta(seconds=1000)
    retry_run = run_delivery_worker_once(
        notif_conn, adapter=adapter, worker_id="w1", as_of=later, web_base_url="http://web.test"
    )
    assert retry_run.outcome is WorkerRunOutcome.DELIVERED
    assert len(adapter.sent) == 2


def test_concurrent_workers_never_claim_the_same_item(notif_url: str) -> None:
    conn = psycopg.connect(notif_url)
    try:
        _create_lead_with_recipient(conn, listing_id="N7", recipient="broker@example.com")
    finally:
        conn.close()

    barrier = threading.Barrier(2)
    outcomes: list[str] = []
    lock = threading.Lock()

    def _run(worker_id: str) -> None:
        thread_conn = psycopg.connect(notif_url)
        try:
            adapter = DeterministicLocalNotificationAdapter()
            barrier.wait()
            result = run_delivery_worker_once(
                thread_conn,
                adapter=adapter,
                worker_id=worker_id,
                as_of=_now(),
                web_base_url="http://web.test",
            )
            with lock:
                outcomes.append(result.outcome.value)
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=_run, args=(f"w{i}",)) for i in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(outcomes) == ["DELIVERED", "NO_ITEM_CLAIMED"]

    verify_conn = psycopg.connect(notif_url)
    try:
        with verify_conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM lead_notification_delivery_attempts")
            (attempt_count,) = cur.fetchone()
    finally:
        verify_conn.close()
    assert attempt_count == 1


# ---------------------------------------------------------------------------
# Notification-recipient configuration — optimistic concurrency (contract §9)
# ---------------------------------------------------------------------------


def test_notification_config_defaults_absent_then_set_with_version_check(notif_conn: Any) -> None:
    org = _publish_listing(notif_conn, listing_id="N8")
    default = fetch_organization_notification_config(notif_conn, org.id)
    assert default.notification_email is None
    assert default.version == 0

    stale = set_organization_notification_email(
        notif_conn,
        org.id,
        notification_email="owner@example.com",
        updated_by_account_id=AccountId("ACC-owner"),
        expected_version=9,
    )
    assert not stale.updated

    fresh = set_organization_notification_email(
        notif_conn,
        org.id,
        notification_email="owner@example.com",
        updated_by_account_id=AccountId("ACC-owner"),
        expected_version=0,
    )
    assert fresh.updated
    assert fresh.current.notification_email == "owner@example.com"
    assert fresh.current.version == 1

    cleared = set_organization_notification_email(
        notif_conn,
        org.id,
        notification_email=None,
        updated_by_account_id=AccountId("ACC-owner"),
        expected_version=1,
    )
    assert cleared.updated
    assert cleared.current.notification_email is None
