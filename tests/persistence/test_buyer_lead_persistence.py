"""PostgreSQL-backed buyer contact / Lead creation persistence tests — SLICE-0070.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the current Alembic head, mirroring the SLICE-0052
`tests/persistence/test_native_listing_freshness_persistence.py` isolation
pattern. Covers `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md`
§17 items 1, 3-6, 9-12.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.buyer_lead import (
    ContactEmailVerificationState,
    SubmissionOperationId,
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
from hullq.persistence.buyer_lead import (
    BuyerLeadCreationStatus,
    BuyerLeadTransactionOwnershipError,
    create_buyer_lead,
    fetch_buyer_lead,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    fetch_lifecycle_state,
    publish_native_listing,
    withdraw_native_listing,
)
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
def lead_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0070_{uuid.uuid4().hex[:16]}"
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
def lead_conn(lead_url: str) -> Generator[Any]:
    conn = psycopg.connect(lead_url)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Domain fixtures -- mirrors test_public_listing_freshness_gating_api.py
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
    return account, org, membership


def _now() -> Any:
    from datetime import UTC, datetime

    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_submission_against_eligible_listing_creates_exactly_one_lead(
    lead_url: str, lead_conn: Any
) -> None:
    _account, org, _membership = _publish_listing(lead_conn, listing_id="NL-LEAD01")
    lead_conn.commit()

    result = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD01"),
        native_listing_id=NativeListingId("NL-LEAD01"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert result.status is BuyerLeadCreationStatus.CREATED
    assert result.lead_id is not None
    assert result.received_at is not None

    record = fetch_buyer_lead(lead_conn, result.lead_id)
    assert record is not None
    assert record.native_listing_id == NativeListingId("NL-LEAD01")
    assert record.publishing_organization_id == org.id
    assert record.account_id is None
    assert record.buyer_name == "Jane Buyer"
    assert record.buyer_email == "jane@example.com"
    assert record.buyer_message == "Interested in this boat."
    assert record.contact_email_verification_state is ContactEmailVerificationState.UNVERIFIED

    with lead_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buyer_leads WHERE native_listing_id = %s", ["NL-LEAD01"])
        assert cur.fetchone()[0] == 1


def test_authenticated_submission_records_optional_account_id_still_unverified(
    lead_url: str, lead_conn: Any
) -> None:
    _publish_listing(lead_conn, listing_id="NL-LEAD02")
    lead_conn.commit()

    buyer_account = AccountId("ACC-BUYER02")
    with lead_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
            [buyer_account.value],
        )
    lead_conn.commit()

    result = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD02"),
        native_listing_id=NativeListingId("NL-LEAD02"),
        account_id=buyer_account,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert result.status is BuyerLeadCreationStatus.CREATED
    assert result.lead_id is not None

    record = fetch_buyer_lead(lead_conn, result.lead_id)
    assert record is not None
    assert record.account_id == buyer_account
    assert record.contact_email_verification_state is ContactEmailVerificationState.UNVERIFIED


def test_missing_listing_is_listing_not_available(lead_url: str, lead_conn: Any) -> None:
    result = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD03"),
        native_listing_id=NativeListingId("NL-NEVER-EXISTED"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert result.status is BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE
    assert result.lead_id is None

    with lead_conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buyer_leads")
        assert cur.fetchone()[0] == 0


def test_draft_listing_is_listing_not_available(lead_url: str, lead_conn: Any) -> None:
    account = AccountId("ACC-LEAD04")
    org = _org("ORG-LEAD04")
    membership = _membership(org, account, "OM-LEAD04")
    create_physical_boat(lead_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-LEAD04")))
    create_market_episode(
        lead_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-LEAD04"), physical_boat_id=PhysicalBoatId("PB-LEAD04")
        ),
    )
    create_native_listing(
        lead_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-LEAD04"), market_episode_id=MarketEpisodeId("ME-LEAD04")
        ),
    )
    lead_conn.commit()

    result = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD04"),
        native_listing_id=NativeListingId("NL-LEAD04"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert result.status is BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE


def test_withdrawn_listing_is_listing_not_available_without_mutating_lifecycle(
    lead_url: str, lead_conn: Any
) -> None:
    from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState

    account, org, membership = _publish_listing(lead_conn, listing_id="NL-LEAD05")
    lead_conn.commit()
    withdraw_result = withdraw_native_listing(
        lead_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-LEAD05"),
    )
    assert withdraw_result.status.value == "transitioned", withdraw_result
    lead_conn.commit()

    result = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD05"),
        native_listing_id=NativeListingId("NL-LEAD05"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert result.status is BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE
    assert (
        fetch_lifecycle_state(lead_conn, NativeListingId("NL-LEAD05"))
        is NativeListingLifecycleState.WITHDRAWN
    )


def test_exact_retry_is_idempotent(lead_url: str, lead_conn: Any) -> None:
    _publish_listing(lead_conn, listing_id="NL-LEAD06")
    lead_conn.commit()

    kwargs: dict[str, Any] = {
        "submission_operation_id": SubmissionOperationId("OP-LEAD06"),
        "native_listing_id": NativeListingId("NL-LEAD06"),
        "account_id": None,
        "buyer_name": "Jane Buyer",
        "buyer_email": "jane@example.com",
        "buyer_message": "Interested in this boat.",
        "as_of": _now(),
    }
    first = create_buyer_lead(lead_conn, **kwargs)
    assert first.status is BuyerLeadCreationStatus.CREATED

    second = create_buyer_lead(lead_conn, **kwargs)
    assert second.status is BuyerLeadCreationStatus.ALREADY_EXISTS
    assert second.lead_id == first.lead_id
    assert second.received_at == first.received_at

    with lead_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM buyer_leads WHERE submission_operation_id = %s", ["OP-LEAD06"]
        )
        assert cur.fetchone()[0] == 1


def test_same_operation_id_different_envelope_conflicts_without_duplicate(
    lead_url: str, lead_conn: Any
) -> None:
    _publish_listing(lead_conn, listing_id="NL-LEAD07")
    lead_conn.commit()

    first = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD07"),
        native_listing_id=NativeListingId("NL-LEAD07"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="Interested in this boat.",
        as_of=_now(),
    )
    assert first.status is BuyerLeadCreationStatus.CREATED

    second = create_buyer_lead(
        lead_conn,
        submission_operation_id=SubmissionOperationId("OP-LEAD07"),
        native_listing_id=NativeListingId("NL-LEAD07"),
        account_id=None,
        buyer_name="Jane Buyer",
        buyer_email="jane@example.com",
        buyer_message="A completely different message.",
        as_of=_now(),
    )
    assert second.status is BuyerLeadCreationStatus.CONFLICT
    assert second.lead_id is None

    with lead_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM buyer_leads WHERE submission_operation_id = %s", ["OP-LEAD07"]
        )
        assert cur.fetchone()[0] == 1
        cur.execute("SELECT buyer_message FROM buyer_leads WHERE lead_id = %s", [first.lead_id.value])
        assert cur.fetchone()[0] == "Interested in this boat."


def test_transaction_ownership_error_when_conn_already_in_transaction(
    lead_url: str, lead_conn: Any
) -> None:
    _publish_listing(lead_conn, listing_id="NL-LEAD08")
    lead_conn.commit()
    with lead_conn.cursor() as cur:
        cur.execute("SELECT 1")

    with pytest.raises(BuyerLeadTransactionOwnershipError):
        create_buyer_lead(
            lead_conn,
            submission_operation_id=SubmissionOperationId("OP-LEAD08"),
            native_listing_id=NativeListingId("NL-LEAD08"),
            account_id=None,
            buyer_name="Jane Buyer",
            buyer_email="jane@example.com",
            buyer_message="Interested in this boat.",
            as_of=_now(),
        )
    lead_conn.rollback()


def test_fetch_buyer_lead_returns_none_for_unknown_lead_id(lead_url: str, lead_conn: Any) -> None:
    from hullq.domain.buyer_lead import LeadId

    assert fetch_buyer_lead(lead_conn, LeadId("LEAD-NEVER-CREATED")) is None


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency proof (contract §17 items 9-10)
# ---------------------------------------------------------------------------


def test_concurrent_duplicate_submissions_create_exactly_one_lead(lead_url: str) -> None:
    """Two threads racing the identical submission_operation_id + envelope
    must create exactly one durable Lead (contract §17 item 10)."""
    setup_conn = psycopg.connect(lead_url)
    try:
        _publish_listing(setup_conn, listing_id="NL-LEADRACE01")
        setup_conn.commit()
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(lead_url)
            try:
                barrier.wait(timeout=10)
                result = create_buyer_lead(
                    conn,
                    submission_operation_id=SubmissionOperationId("OP-LEADRACE01"),
                    native_listing_id=NativeListingId("NL-LEADRACE01"),
                    account_id=None,
                    buyer_name="Jane Buyer",
                    buyer_email="jane@example.com",
                    buyer_message="Interested in this boat.",
                    as_of=_now(),
                )
                results.append(result)
            finally:
                conn.close()
        except BaseException as exc:
            errors.append(exc)

    threads = [threading.Thread(target=_worker) for _ in range(2)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = sorted(r.status.value for r in results)
    assert statuses == ["already_exists", "created"], results
    lead_ids = {r.lead_id for r in results}
    assert len(lead_ids) == 1

    verify = psycopg.connect(lead_url)
    try:
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM buyer_leads WHERE submission_operation_id = %s",
                ["OP-LEADRACE01"],
            )
            assert cur.fetchone()[0] == 1
    finally:
        verify.close()


def test_concurrent_withdraw_and_lead_creation_never_creates_a_stale_lead(lead_url: str) -> None:
    """A Lead creation racing a concurrent withdraw for the identical listing
    must never durably create a Lead against a listing that is (or becomes,
    before this creation's own authoritative check) WITHDRAWN (contract §17
    item 9 / §12's row-lock serialization)."""
    setup_conn = psycopg.connect(lead_url)
    try:
        account, org, membership = _publish_listing(setup_conn, listing_id="NL-LEADRACE02")
        setup_conn.commit()
    finally:
        setup_conn.close()

    lead_results: list[Any] = []
    withdraw_results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _lead_worker() -> None:
        try:
            conn = psycopg.connect(lead_url)
            try:
                barrier.wait(timeout=10)
                result = create_buyer_lead(
                    conn,
                    submission_operation_id=SubmissionOperationId("OP-LEADRACE02"),
                    native_listing_id=NativeListingId("NL-LEADRACE02"),
                    account_id=None,
                    buyer_name="Jane Buyer",
                    buyer_email="jane@example.com",
                    buyer_message="Interested in this boat.",
                    as_of=_now(),
                )
                lead_results.append(result)
            finally:
                conn.close()
        except BaseException as exc:
            errors.append(exc)

    def _withdraw_worker() -> None:
        try:
            conn = psycopg.connect(lead_url)
            try:
                barrier.wait(timeout=10)
                result = withdraw_native_listing(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-LEADRACE02"),
                )
                withdraw_results.append(result)
            finally:
                conn.close()
        except BaseException as exc:
            errors.append(exc)

    threads = [
        threading.Thread(target=_lead_worker),
        threading.Thread(target=_withdraw_worker),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(lead_results) == 1
    assert len(withdraw_results) == 1
    assert withdraw_results[0].status.value == "transitioned"

    verify = psycopg.connect(lead_url)
    try:
        from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState

        assert (
            fetch_lifecycle_state(verify, NativeListingId("NL-LEADRACE02"))
            is NativeListingLifecycleState.WITHDRAWN
        )
        with verify.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM buyer_leads WHERE native_listing_id = %s",
                ["NL-LEADRACE02"],
            )
            lead_row_count = cur.fetchone()[0]
        # Whichever transaction won the row-lock race first, the outcome is
        # internally consistent: either the Lead genuinely committed before
        # the withdrawal could (CREATED, one durable row), or the withdrawal
        # committed first and the Lead's own fresh re-check correctly
        # observed WITHDRAWN (LISTING_NOT_AVAILABLE, zero rows). No other
        # combination is possible -- the row lock forbids interleaving.
        if lead_results[0].status is BuyerLeadCreationStatus.CREATED:
            assert lead_row_count == 1
        else:
            assert lead_results[0].status is BuyerLeadCreationStatus.LISTING_NOT_AVAILABLE
            assert lead_row_count == 0
    finally:
        verify.close()
