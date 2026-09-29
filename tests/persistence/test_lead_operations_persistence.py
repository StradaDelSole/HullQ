"""PostgreSQL-backed broker Lead operations persistence tests — SLICE-0071.

Each test runs against its own disposable PostgreSQL schema, brought from
genuinely empty to the current Alembic head, mirroring the SLICE-0070
`tests/persistence/test_buyer_lead_persistence.py` isolation pattern. Covers
`specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md` §5/§6/§7/§8/
§8A/§15 (operational-state defaults, assignment/status/follow-up optimistic
concurrency, notes/contact-attempt append, inbox pagination/filters,
counts).
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

from hullq.domain.buyer_lead import LeadId, SubmissionOperationId
from hullq.domain.lead_operations import (
    LeadCloseReason,
    LeadContactAttemptChannel,
    LeadOperationalStatus,
)
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
from hullq.persistence.lead_operations import (
    LeadInboxSortKey,
    append_lead_contact_attempt,
    append_lead_note,
    fetch_lead_detail,
    fetch_lead_operational_state,
    fetch_lead_timeline,
    fetch_organization_lead_counts,
    fetch_organization_lead_inbox_page,
    mark_lead_read,
    set_lead_assignment,
    set_lead_follow_up_due_at,
    set_lead_operational_status,
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
def lead_ops_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0071_{uuid.uuid4().hex[:16]}"
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
def lead_ops_conn(lead_ops_url: str) -> Generator[Any]:
    conn = psycopg.connect(lead_ops_url)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Domain fixtures -- mirrors test_buyer_lead_persistence.py
# ---------------------------------------------------------------------------


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(org: MarketplaceOrganization, account: AccountId, membership_id: str) -> OrganizationMembership:
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
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account.value]
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


def _publish_listing(
    conn: Any, *, listing_id: str
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

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
    return account, org, membership


def _now() -> datetime:
    return datetime.now(UTC)


def _create_lead_for_listing(conn: Any, *, listing_id: str, buyer_suffix: str) -> LeadId:
    result = create_buyer_lead(
        conn,
        submission_operation_id=SubmissionOperationId(f"OP-{listing_id}-{buyer_suffix}"),
        native_listing_id=NativeListingId(listing_id),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert result.status.value == "created", result
    conn.commit()
    assert result.lead_id is not None
    return result.lead_id


def _create_lead(conn: Any, *, listing_id: str, buyer_suffix: str) -> tuple[LeadId, MarketplaceOrganization]:
    _account, org, _membership = _publish_listing(conn, listing_id=listing_id)
    lead_id = _create_lead_for_listing(conn, listing_id=listing_id, buyer_suffix=buyer_suffix)
    return lead_id, org


# ---------------------------------------------------------------------------
# Operational-state defaults + mark-read idempotency
# ---------------------------------------------------------------------------


def test_operational_state_defaults_to_new_unread_with_no_row(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L1", buyer_suffix="A")
    state = fetch_lead_operational_state(lead_ops_conn, lead_id)
    assert state.operational_status is LeadOperationalStatus.NEW
    assert state.is_unread is True
    assert state.assigned_account_id is None
    assert state.follow_up_due_at is None
    assert state.version == 0


def test_mark_read_is_idempotent_and_logs_exactly_one_event(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L2", buyer_suffix="A")
    actor = AccountId("ACC-broker-1")
    mark_lead_read(lead_ops_conn, lead_id, actor_account_id=actor, as_of=_now())
    lead_ops_conn.commit()
    mark_lead_read(lead_ops_conn, lead_id, actor_account_id=actor, as_of=_now())
    lead_ops_conn.commit()

    state = fetch_lead_operational_state(lead_ops_conn, lead_id)
    assert state.is_unread is False

    timeline = fetch_lead_timeline(lead_ops_conn, lead_id)
    read_events = [event for event in timeline if event.event_type.value == "MARKED_READ"]
    assert len(read_events) == 1


def test_concurrent_mark_read_logs_exactly_one_event(lead_ops_url: str) -> None:
    conn = psycopg.connect(lead_ops_url)
    try:
        lead_id, _org = _create_lead(conn, listing_id="L2C", buyer_suffix="A")
    finally:
        conn.close()

    actor = AccountId("ACC-broker-race")
    barrier = threading.Barrier(2)
    errors: list[Exception] = []

    def _mark() -> None:
        thread_conn = psycopg.connect(lead_ops_url)
        try:
            barrier.wait()
            mark_lead_read(thread_conn, lead_id, actor_account_id=actor, as_of=_now())
            thread_conn.commit()
        except Exception as exc:  # noqa: BLE001
            errors.append(exc)
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=_mark) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert not errors

    verify_conn = psycopg.connect(lead_ops_url)
    try:
        timeline = fetch_lead_timeline(verify_conn, lead_id)
    finally:
        verify_conn.close()
    read_events = [event for event in timeline if event.event_type.value == "MARKED_READ"]
    assert len(read_events) == 1


# ---------------------------------------------------------------------------
# Assignment — optimistic concurrency (contract §7/§15)
# ---------------------------------------------------------------------------


def test_assignment_requires_matching_version(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L3", buyer_suffix="A")
    actor = AccountId("ACC-broker-2")

    stale = set_lead_assignment(
        lead_ops_conn,
        lead_id,
        assignee_account_id=actor,
        actor_account_id=actor,
        expected_version=5,
        as_of=_now(),
    )
    lead_ops_conn.commit()
    assert not stale.updated
    assert stale.current.version == 0

    fresh = set_lead_assignment(
        lead_ops_conn,
        lead_id,
        assignee_account_id=actor,
        actor_account_id=actor,
        expected_version=0,
        as_of=_now(),
    )
    lead_ops_conn.commit()
    assert fresh.updated
    assert fresh.current.assigned_account_id == actor
    assert fresh.current.version == 1


def test_concurrent_assignment_only_one_wins(lead_ops_url: str) -> None:
    conn = psycopg.connect(lead_ops_url)
    try:
        lead_id, _org = _create_lead(conn, listing_id="L3C", buyer_suffix="A")
    finally:
        conn.close()

    actor_a = AccountId("ACC-race-a")
    actor_b = AccountId("ACC-race-b")
    barrier = threading.Barrier(2)
    results: list[bool] = []
    lock = threading.Lock()

    def _assign(actor: AccountId) -> None:
        thread_conn = psycopg.connect(lead_ops_url)
        try:
            barrier.wait()
            result = set_lead_assignment(
                thread_conn,
                lead_id,
                assignee_account_id=actor,
                actor_account_id=actor,
                expected_version=0,
                as_of=_now(),
            )
            thread_conn.commit()
            with lock:
                results.append(result.updated)
        finally:
            thread_conn.close()

    threads = [threading.Thread(target=_assign, args=(actor,)) for actor in (actor_a, actor_b)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False, True]

    verify_conn = psycopg.connect(lead_ops_url)
    try:
        state = fetch_lead_operational_state(verify_conn, lead_id)
    finally:
        verify_conn.close()
    assert state.version == 1
    assert state.assigned_account_id in (actor_a, actor_b)


# ---------------------------------------------------------------------------
# Status / close reason (contract §5/§8A)
# ---------------------------------------------------------------------------


def test_close_requires_reason_and_records_timeline(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L4", buyer_suffix="A")
    actor = AccountId("ACC-broker-3")

    with pytest.raises(ValueError):
        set_lead_operational_status(
            lead_ops_conn,
            lead_id,
            new_status=LeadOperationalStatus.CLOSED,
            close_reason=None,
            actor_account_id=actor,
            expected_version=0,
            as_of=_now(),
        )

    result = set_lead_operational_status(
        lead_ops_conn,
        lead_id,
        new_status=LeadOperationalStatus.CLOSED,
        close_reason=LeadCloseReason.NOT_INTERESTED,
        actor_account_id=actor,
        expected_version=0,
        as_of=_now(),
    )
    lead_ops_conn.commit()
    assert result.updated
    assert result.current.operational_status is LeadOperationalStatus.CLOSED
    assert result.current.close_reason is LeadCloseReason.NOT_INTERESTED

    timeline = fetch_lead_timeline(lead_ops_conn, lead_id)
    closed_events = [event for event in timeline if event.event_type.value == "CLOSED"]
    assert len(closed_events) == 1
    assert closed_events[0].close_reason is LeadCloseReason.NOT_INTERESTED


def test_closing_never_touches_lead_envelope(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L4B", buyer_suffix="A")
    before = fetch_lead_detail(lead_ops_conn, lead_id)
    assert before is not None
    set_lead_operational_status(
        lead_ops_conn,
        lead_id,
        new_status=LeadOperationalStatus.CLOSED,
        close_reason=LeadCloseReason.DUPLICATE,
        actor_account_id=AccountId("ACC-broker-4"),
        expected_version=0,
        as_of=_now(),
    )
    lead_ops_conn.commit()
    after = fetch_lead_detail(lead_ops_conn, lead_id)
    assert after is not None
    assert after.buyer_name == before.buyer_name
    assert after.buyer_email == before.buyer_email
    assert after.buyer_message == before.buyer_message
    assert after.contact_email_verification_state == before.contact_email_verification_state


# ---------------------------------------------------------------------------
# Follow-up (contract §8A)
# ---------------------------------------------------------------------------


def test_follow_up_set_change_clear(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L5", buyer_suffix="A")
    actor = AccountId("ACC-broker-5")
    due = _now() + timedelta(days=1)

    set_result = set_lead_follow_up_due_at(
        lead_ops_conn, lead_id, due_at=due, actor_account_id=actor, expected_version=0, as_of=_now()
    )
    lead_ops_conn.commit()
    assert set_result.updated
    assert set_result.current.follow_up_due_at is not None

    clear_result = set_lead_follow_up_due_at(
        lead_ops_conn,
        lead_id,
        due_at=None,
        actor_account_id=actor,
        expected_version=set_result.current.version,
        as_of=_now(),
    )
    lead_ops_conn.commit()
    assert clear_result.updated
    assert clear_result.current.follow_up_due_at is None

    timeline = fetch_lead_timeline(lead_ops_conn, lead_id)
    event_types = {event.event_type.value for event in timeline}
    assert "FOLLOW_UP_SET" in event_types
    assert "FOLLOW_UP_CLEARED" in event_types


# ---------------------------------------------------------------------------
# Notes / contact attempts — append-only (contract §8/§8A)
# ---------------------------------------------------------------------------


def test_notes_and_contact_attempts_append_without_implying_buyer_response(lead_ops_conn: Any) -> None:
    lead_id, _org = _create_lead(lead_ops_conn, listing_id="L6", buyer_suffix="A")
    actor = AccountId("ACC-broker-6")

    append_lead_note(lead_ops_conn, lead_id, actor_account_id=actor, note_text="Called once.", as_of=_now())
    append_lead_contact_attempt(
        lead_ops_conn,
        lead_id,
        actor_account_id=actor,
        channel=LeadContactAttemptChannel.PHONE,
        note_text="No answer.",
        as_of=_now(),
    )
    lead_ops_conn.commit()

    timeline = fetch_lead_timeline(lead_ops_conn, lead_id)
    note_events = [e for e in timeline if e.event_type.value == "NOTE"]
    contact_events = [e for e in timeline if e.event_type.value == "CONTACT_ATTEMPT"]
    assert len(note_events) == 1
    assert len(contact_events) == 1
    assert contact_events[0].contact_channel is LeadContactAttemptChannel.PHONE

    # Contract §8A: a contact attempt is broker action only -- operational
    # status/buyer verification remain untouched.
    state = fetch_lead_operational_state(lead_ops_conn, lead_id)
    assert state.operational_status is LeadOperationalStatus.NEW
    lead = fetch_lead_detail(lead_ops_conn, lead_id)
    assert lead is not None
    assert lead.contact_email_verification_state.value == "UNVERIFIED"


# ---------------------------------------------------------------------------
# Organization-scoped inbox pagination + filters + counts (contract §3)
# ---------------------------------------------------------------------------


def test_inbox_page_is_organization_scoped_and_paginated(lead_ops_conn: Any) -> None:
    lead_a, org = _create_lead(lead_ops_conn, listing_id="L7A", buyer_suffix="A")
    # A second, unrelated Organization/Lead must never appear.
    _create_lead(lead_ops_conn, listing_id="L7B", buyer_suffix="A")
    # A second Lead against *org*'s own listing must appear alongside lead_a.
    lead_a2 = _create_lead_for_listing(lead_ops_conn, listing_id="L7A", buyer_suffix="B")

    page = fetch_organization_lead_inbox_page(lead_ops_conn, org.id, limit=10, after=None)
    assert {row.lead_id for row in page} == {lead_a, lead_a2}


def test_inbox_filters_unread_and_status(lead_ops_conn: Any) -> None:
    lead_id, org = _create_lead(lead_ops_conn, listing_id="L8", buyer_suffix="A")

    unread_page = fetch_organization_lead_inbox_page(
        lead_ops_conn, org.id, limit=10, after=None, unread_only=True
    )
    assert [row.lead_id for row in unread_page] == [lead_id]

    mark_lead_read(lead_ops_conn, lead_id, actor_account_id=AccountId("ACC-x"), as_of=_now())
    lead_ops_conn.commit()

    unread_page_after = fetch_organization_lead_inbox_page(
        lead_ops_conn, org.id, limit=10, after=None, unread_only=True
    )
    assert unread_page_after == []

    new_status_page = fetch_organization_lead_inbox_page(
        lead_ops_conn, org.id, limit=10, after=None, status_filter=LeadOperationalStatus.NEW
    )
    assert [row.lead_id for row in new_status_page] == [lead_id]


def test_organization_counts_reflect_unread_unassigned_and_follow_up(lead_ops_conn: Any) -> None:
    lead_id, org = _create_lead(lead_ops_conn, listing_id="L9", buyer_suffix="A")
    as_of = _now()
    counts = fetch_organization_lead_counts(lead_ops_conn, org.id, as_of=as_of)
    assert counts.new_unread == 1
    assert counts.unassigned == 1
    assert counts.follow_up_due == 0
    assert counts.follow_up_overdue == 0

    set_lead_follow_up_due_at(
        lead_ops_conn,
        lead_id,
        due_at=as_of - timedelta(hours=1),
        actor_account_id=AccountId("ACC-y"),
        expected_version=0,
        as_of=as_of,
    )
    lead_ops_conn.commit()

    later_counts = fetch_organization_lead_counts(lead_ops_conn, org.id, as_of=as_of)
    assert later_counts.follow_up_due == 1
    assert later_counts.follow_up_overdue == 1


def test_inbox_keyset_cursor_continues_deterministically(lead_ops_conn: Any) -> None:
    lead_1, org = _create_lead(lead_ops_conn, listing_id="L10A", buyer_suffix="A")
    lead_2 = _create_lead_for_listing(lead_ops_conn, listing_id="L10A", buyer_suffix="B")

    first_page = fetch_organization_lead_inbox_page(lead_ops_conn, org.id, limit=1, after=None)
    assert len(first_page) == 1
    after_key = LeadInboxSortKey(received_at=first_page[0].received_at, lead_id=first_page[0].lead_id)
    second_page = fetch_organization_lead_inbox_page(lead_ops_conn, org.id, limit=1, after=after_key)
    assert len(second_page) == 1
    assert {first_page[0].lead_id, second_page[0].lead_id} == {lead_1, lead_2}

    third_page = fetch_organization_lead_inbox_page(
        lead_ops_conn,
        org.id,
        limit=1,
        after=LeadInboxSortKey(received_at=second_page[0].received_at, lead_id=second_page[0].lead_id),
    )
    assert third_page == []
