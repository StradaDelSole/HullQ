"""PostgreSQL + real HTTP tests for SLICE-0075 broker performance / funnel
snapshot telemetry + read surface.

Covers `specs/BROKER_PERFORMANCE_FUNNEL_SNAPSHOT_CONTRACT.v0.1.md` §12's
required retained proof items: a public-readable listing read records one
durable view event; retry of the same telemetry operation does not
double-count; private/broker-authenticated reads never create a view fact;
Organization A cannot read Organization B telemetry (including when both
Organizations' listings share the same underlying MarketEpisode); exact
view/Lead counts; first-CONTACT_ATTEMPT latency derivation and its explicit
unknown state when no contact attempt exists; a CLOSED Lead is never counted
as SOLD; an explicit SOLD outcome correctly reports known vs unknown Lead
source; and the browser-facing route surfaces explicit unknown states
without inventing zeros/conversions.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from starlette.testclient import TestClient

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.buyer_lead import LeadId, SubmissionOperationId
from hullq.domain.lead_operations import (
    LeadCloseReason,
    LeadContactAttemptChannel,
    LeadOperationalStatus,
)
from hullq.domain.lead_provenance import DiscoverySurface
from hullq.domain.listing_telemetry import ListingViewOperationId
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
from hullq.domain.sale_outcome import SaleOutcomeKind, SaleOutcomeRevisionId, SaleOutcomeSnapshot
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.persistence.buyer_lead import BuyerLeadCreationStatus, create_buyer_lead
from hullq.persistence.lead_operations import (
    append_lead_contact_attempt,
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
from hullq.persistence.native_listing_sale_outcome import close_native_listing_as_sold
from hullq.persistence.native_listing_view_event import (
    RecordListingViewStatus,
    record_public_listing_view,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.security.session_token import mint_session_token

_SECRET = b"5" * 32
_WEB_ORIGIN = "http://web.test"


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
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0075api_{uuid.uuid4().hex[:16]}"
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
def api_conn(api_url: str) -> Generator[Any]:
    conn = psycopg.connect(api_url)
    try:
        yield conn
    finally:
        conn.close()


@pytest.fixture()
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _ensure_account(conn: Any, account_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )


def _session_cookie(account_id: str) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=True,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SECRET)
    return minted.token


def _log_in(client: TestClient, account_id: str) -> None:
    client.cookies.set("hullq_session", _session_cookie(account_id), domain="api.test")


def _seed_org_and_membership(
    api_url: str, *, org_id: str, account_id: str, membership_id: str
) -> None:
    conn = psycopg.connect(api_url)
    try:
        _ensure_account(conn, account_id)
        seed_marketplace_organization(
            conn,
            MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=AccountId(account_id),
                organization_id=MarketplaceOrganizationId(org_id),
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _amount_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal("125000.00"),
        currency="EUR",
    )


def _ready_physical_boat_claim() -> PhysicalBoatClaimSnapshot:
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, 2020),
    )


def _attach_ready_cover_image(conn: Any, *, listing_id: str, org_id: str, account_id: str) -> None:
    asset = insert_approved_media_asset(
        conn,
        owner_organization_id=MarketplaceOrganizationId(org_id),
        uploaded_by_account_id=AccountId(account_id),
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
        owner_organization_id=MarketplaceOrganizationId(org_id),
        media_asset=asset,
    )
    assert placement_result.media_placement_id is not None
    cover_result = set_cover(
        conn,
        native_listing_id=NativeListingId(listing_id),
        owner_organization_id=MarketplaceOrganizationId(org_id),
        media_placement_id=placement_result.media_placement_id,
        expected_version=placement_result.gallery_version,
    )
    assert cover_result.outcome.value == "SET", cover_result


def _create_and_publish_listing(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
) -> None:
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(membership_id),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
        write_native_listing_offer_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=NativeListingOfferRevisionId(f"OFFER-{listing_id}"),
            expected_current_revision_id=None,
            offer=_amount_offer(),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
            expected_current_revision_id=None,
            claims=_ready_physical_boat_claim(),
        )
        _attach_ready_cover_image(conn, listing_id=listing_id, org_id=org_id, account_id=account_id)
        conn.commit()
        result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert result.status.value == "transitioned", result
        conn.commit()
    finally:
        conn.close()


def _create_lead(
    api_url: str,
    *,
    listing_id: str,
    submission_operation_id: str,
    discovery_surface: DiscoverySurface = DiscoverySurface.UNKNOWN,
    utm_source: str | None = None,
    utm_medium: str | None = None,
    utm_campaign: str | None = None,
) -> str:
    conn = psycopg.connect(api_url)
    try:
        result = create_buyer_lead(
            conn,
            submission_operation_id=SubmissionOperationId(submission_operation_id),
            native_listing_id=NativeListingId(listing_id),
            account_id=None,
            buyer_name="Jordan Buyer",
            buyer_email="jordan@example.com",
            buyer_message="Interested in this boat.",
            as_of=datetime.now(UTC),
            discovery_surface=discovery_surface,
            utm_source=utm_source,
            utm_medium=utm_medium,
            utm_campaign=utm_campaign,
        )
        assert result.status is BuyerLeadCreationStatus.CREATED, result
        assert result.lead_id is not None
        conn.commit()
        return result.lead_id.value
    finally:
        conn.close()


def _close_as_sold_directly(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    originating_lead_id: str | None = None,
) -> None:
    conn = psycopg.connect(api_url)
    try:
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-SOLD-{listing_id}"),
            account_id=AccountId(account_id),
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        result = close_native_listing_as_sold(
            conn,
            account_id=AccountId(account_id),
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=SaleOutcomeRevisionId(f"SOREV-{listing_id}"),
            expected_current_revision_id=None,
            outcome=SaleOutcomeSnapshot(
                kind=SaleOutcomeKind.SOLD,
                originating_lead_id=LeadId(originating_lead_id)
                if originating_lead_id is not None
                else None,
            ),
        )
        assert result.status.value == "created", result
        conn.commit()
    finally:
        conn.close()


def _backdate_sale_outcome_recorded_at(api_url: str, *, listing_id: str, days_ago: int) -> None:
    """Test-only: directly backdate a just-recorded SaleOutcome revision's
    own `recorded_at` so window-boundary semantics (Finding A) can be
    exercised deterministically, without needing to fabricate a server
    clock override for the whole app (which would also perturb freshness/
    public-eligibility evaluation elsewhere). Never used by production code
    -- `close_native_listing_as_sold` itself always writes a real `NOW()`.
    """
    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE native_listing_sale_outcome_revisions "
                "SET recorded_at = recorded_at - make_interval(days => %s) "
                "WHERE native_listing_id = %s",
                [days_ago, listing_id],
            )
        conn.commit()
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Direct persistence-level idempotency/conflict proof (items 1/2)
# ---------------------------------------------------------------------------


def test_record_public_listing_view_idempotent_retry_and_conflict(
    api_url: str, api_conn: Any
) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-IDEMP", account_id="ACC-IDEMP", membership_id="OM-IDEMP"
    )
    _create_and_publish_listing(
        api_url,
        listing_id="NL-IDEMP",
        org_id="ORG-IDEMP",
        account_id="ACC-IDEMP",
        membership_id="OM-IDEMP",
        physical_boat_id="PB-IDEMP",
        market_episode_id="ME-IDEMP",
    )
    operation_id = ListingViewOperationId(str(uuid.uuid4()))
    now = datetime.now(UTC)

    first = record_public_listing_view(
        api_conn,
        operation_id=operation_id,
        native_listing_id=NativeListingId("NL-IDEMP"),
        publishing_organization_id=MarketplaceOrganizationId("ORG-IDEMP"),
        occurred_at=now,
    )
    assert first.status is RecordListingViewStatus.RECORDED

    retry = record_public_listing_view(
        api_conn,
        operation_id=operation_id,
        native_listing_id=NativeListingId("NL-IDEMP"),
        publishing_organization_id=MarketplaceOrganizationId("ORG-IDEMP"),
        occurred_at=datetime.now(UTC),
    )
    assert retry.status is RecordListingViewStatus.ALREADY_RECORDED

    conflicting = record_public_listing_view(
        api_conn,
        operation_id=operation_id,
        native_listing_id=NativeListingId("NL-IDEMP"),
        publishing_organization_id=MarketplaceOrganizationId("ORG-OTHER"),
        occurred_at=datetime.now(UTC),
    )
    assert conflicting.status is RecordListingViewStatus.CONFLICT

    with api_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listing_view_events WHERE native_listing_id = %s",
            ["NL-IDEMP"],
        )
        assert cur.fetchone()[0] == 1


# ---------------------------------------------------------------------------
# Public route wiring: success-path-only counting (item 3)
# ---------------------------------------------------------------------------


def test_public_view_recorded_only_on_public_success_path(
    api_url: str, api_conn: Any, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-WIRE", account_id="ACC-WIRE", membership_id="OM-WIRE"
    )
    _create_and_publish_listing(
        api_url,
        listing_id="NL-WIRE",
        org_id="ORG-WIRE",
        account_id="ACC-WIRE",
        membership_id="OM-WIRE",
        physical_boat_id="PB-WIRE",
        market_episode_id="ME-WIRE",
    )

    def _view_count() -> int:
        with api_conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM native_listing_view_events WHERE native_listing_id = %s",
                ["NL-WIRE"],
            )
            return cur.fetchone()[0]

    # An authenticated broker inventory read (which internally reuses
    # get_public_listing_read_model for its own is_publicly_listed check)
    # must never itself create a view fact.
    _log_in(client, "ACC-WIRE")
    inv_response = client.get("/api/broker/organizations/ORG-WIRE/inventory")
    assert inv_response.status_code == 200
    assert _view_count() == 0

    # Three genuine public reads -> exactly three durable events.
    for _ in range(3):
        response = client.get("/api/listings/NL-WIRE")
        assert response.status_code == 200
    assert _view_count() == 3

    # A second broker inventory read still does not add to the count.
    inv_response_again = client.get("/api/broker/organizations/ORG-WIRE/inventory")
    assert inv_response_again.status_code == 200
    assert _view_count() == 3


def test_draft_listing_public_read_records_no_view(
    api_url: str, api_conn: Any, client: TestClient
) -> None:
    conn = psycopg.connect(api_url)
    try:
        account = AccountId("ACC-DRAFT")
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-DRAFT"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId("OM-DRAFT"),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-DRAFT")))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId("ME-DRAFT"), physical_boat_id=PhysicalBoatId("PB-DRAFT")
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId("NL-DRAFT"), market_episode_id=MarketEpisodeId("ME-DRAFT")
            ),
        )
        conn.commit()
    finally:
        conn.close()

    response = client.get("/api/listings/NL-DRAFT")
    assert response.status_code == 404

    with api_conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listing_view_events WHERE native_listing_id = %s",
            ["NL-DRAFT"],
        )
        assert cur.fetchone()[0] == 0


# ---------------------------------------------------------------------------
# Full funnel snapshot: counts, latency, source, SOLD linkage, isolation
# ---------------------------------------------------------------------------


def test_organization_performance_snapshot_full_funnel(
    api_url: str, api_conn: Any, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-FUNNEL", account_id="ACC-FUNNEL", membership_id="OM-FUNNEL"
    )

    # L1: two Leads -- one contacted (known latency) and closed, one never
    # contacted (unknown latency). Three observed public views.
    _create_and_publish_listing(
        api_url,
        listing_id="NL-FUNNEL-1",
        org_id="ORG-FUNNEL",
        account_id="ACC-FUNNEL",
        membership_id="OM-FUNNEL",
        physical_boat_id="PB-FUNNEL-1",
        market_episode_id="ME-FUNNEL-1",
    )
    for _ in range(3):
        assert client.get("/api/listings/NL-FUNNEL-1").status_code == 200

    lead_contacted_id = _create_lead(
        api_url, listing_id="NL-FUNNEL-1", submission_operation_id="SUB-CONTACTED"
    )
    # A second Lead on the same listing with no recorded contact attempt --
    # exercises the explicit unknown-latency state (not referenced by id).
    _create_lead(api_url, listing_id="NL-FUNNEL-1", submission_operation_id="SUB-UNCONTACTED")

    received_at_row = None
    with api_conn.cursor() as cur:
        cur.execute("SELECT received_at FROM buyer_leads WHERE lead_id = %s", [lead_contacted_id])
        received_at_row = cur.fetchone()[0]

    append_lead_contact_attempt(
        api_conn,
        LeadId(lead_contacted_id),
        actor_account_id=AccountId("ACC-FUNNEL"),
        channel=LeadContactAttemptChannel.EMAIL,
        note_text="Called the buyer.",
        as_of=received_at_row,
    )
    api_conn.commit()
    set_lead_operational_status(
        api_conn,
        LeadId(lead_contacted_id),
        new_status=LeadOperationalStatus.CLOSED,
        close_reason=LeadCloseReason.NOT_INTERESTED,
        actor_account_id=AccountId("ACC-FUNNEL"),
        expected_version=0,
        as_of=datetime.now(UTC),
    )
    api_conn.commit()

    # L2: SOLD with a known originating Lead.
    _create_and_publish_listing(
        api_url,
        listing_id="NL-FUNNEL-2",
        org_id="ORG-FUNNEL",
        account_id="ACC-FUNNEL",
        membership_id="OM-FUNNEL",
        physical_boat_id="PB-FUNNEL-2",
        market_episode_id="ME-FUNNEL-2",
    )
    assert client.get("/api/listings/NL-FUNNEL-2").status_code == 200
    lead_for_sale_id = _create_lead(
        api_url, listing_id="NL-FUNNEL-2", submission_operation_id="SUB-FOR-SALE"
    )
    _close_as_sold_directly(
        api_url,
        listing_id="NL-FUNNEL-2",
        org_id="ORG-FUNNEL",
        account_id="ACC-FUNNEL",
        originating_lead_id=lead_for_sale_id,
    )

    # L3: SOLD with no originating Lead -> unknown source.
    _create_and_publish_listing(
        api_url,
        listing_id="NL-FUNNEL-3",
        org_id="ORG-FUNNEL",
        account_id="ACC-FUNNEL",
        membership_id="OM-FUNNEL",
        physical_boat_id="PB-FUNNEL-3",
        market_episode_id="ME-FUNNEL-3",
    )
    _close_as_sold_directly(
        api_url, listing_id="NL-FUNNEL-3", org_id="ORG-FUNNEL", account_id="ACC-FUNNEL"
    )

    # A second Organization with its own listing/Lead/views -- must never
    # leak into ORG-FUNNEL's snapshot.
    _seed_org_and_membership(
        api_url, org_id="ORG-OTHER", account_id="ACC-OTHER", membership_id="OM-OTHER"
    )
    _create_and_publish_listing(
        api_url,
        listing_id="NL-OTHER-1",
        org_id="ORG-OTHER",
        account_id="ACC-OTHER",
        membership_id="OM-OTHER",
        physical_boat_id="PB-OTHER-1",
        market_episode_id="ME-OTHER-1",
    )
    assert client.get("/api/listings/NL-OTHER-1").status_code == 200
    _create_lead(api_url, listing_id="NL-OTHER-1", submission_operation_id="SUB-OTHER")

    _log_in(client, "ACC-FUNNEL")
    response = client.get("/api/broker/organizations/ORG-FUNNEL/performance?window=ALL_TIME")
    assert response.status_code == 200
    body = response.json()

    assert body["public_listing_views"] == 4  # 3 (L1) + 1 (L2); L3 has zero views
    assert body["leads_received"] == 3  # L1 x2 + L2 x1
    assert body["leads_contacted"] == 1
    assert body["leads_closed"] == 1
    assert body["sold_outcomes"] == 2
    assert body["sold_outcomes_with_known_source"] == 1
    assert body["sold_outcomes_with_unknown_source"] == 1
    assert body["first_contact_latency_known_count"] == 1
    assert body["first_contact_latency_unknown_count"] == 2
    assert body["median_first_contact_latency_seconds"] == 0.0

    listings_by_id = {item["native_listing_id"]: item for item in body["listings"]}
    assert "NL-OTHER-1" not in listings_by_id  # cross-Organization isolation

    l1 = listings_by_id["NL-FUNNEL-1"]
    assert l1["public_listing_views"] == 3
    assert l1["leads_received"] == 2
    assert l1["leads_contacted"] == 1
    assert l1["leads_closed"] == 1
    assert l1["first_contact_latency_known_count"] == 1
    assert l1["first_contact_latency_unknown_count"] == 1
    assert l1["sold_outcome_recorded_at"] is None  # never fabricated

    l2 = listings_by_id["NL-FUNNEL-2"]
    assert l2["sold_outcome_recorded_at"] is not None
    assert l2["sold_outcome_source_known"] is True

    l3 = listings_by_id["NL-FUNNEL-3"]
    assert l3["public_listing_views"] == 0
    assert l3["sold_outcome_recorded_at"] is not None
    assert l3["sold_outcome_source_known"] is False

    # Org B must never be able to read Org A's telemetry, including when
    # both sides publish into the same underlying MarketEpisode.
    _log_in(client, "ACC-OTHER")
    denied = client.get("/api/broker/organizations/ORG-FUNNEL/performance")
    assert denied.status_code == 404


def test_cross_organization_same_market_episode_isolation(api_url: str, client: TestClient) -> None:
    shared_episode_id = "ME-SHARED"
    shared_boat_id = "PB-SHARED"

    _seed_org_and_membership(
        api_url, org_id="ORG-SHARE-A", account_id="ACC-SHARE-A", membership_id="OM-SHARE-A"
    )
    _seed_org_and_membership(
        api_url, org_id="ORG-SHARE-B", account_id="ACC-SHARE-B", membership_id="OM-SHARE-B"
    )

    _create_and_publish_listing(
        api_url,
        listing_id="NL-SHARE-A",
        org_id="ORG-SHARE-A",
        account_id="ACC-SHARE-A",
        membership_id="OM-SHARE-A",
        physical_boat_id=shared_boat_id,
        market_episode_id=shared_episode_id,
    )
    _create_and_publish_listing(
        api_url,
        listing_id="NL-SHARE-B",
        org_id="ORG-SHARE-B",
        account_id="ACC-SHARE-B",
        membership_id="OM-SHARE-B",
        physical_boat_id=shared_boat_id,
        market_episode_id=shared_episode_id,
    )
    for _ in range(2):
        assert client.get("/api/listings/NL-SHARE-A").status_code == 200
    assert client.get("/api/listings/NL-SHARE-B").status_code == 200

    _log_in(client, "ACC-SHARE-A")
    response = client.get("/api/broker/organizations/ORG-SHARE-A/performance?window=ALL_TIME")
    assert response.status_code == 200
    body = response.json()
    assert body["public_listing_views"] == 2
    listing_ids = {item["native_listing_id"] for item in body["listings"]}
    assert listing_ids == {"NL-SHARE-A"}


# ---------------------------------------------------------------------------
# Finding A (independent review, exact-head c30e4ab): bounded-window SOLD
# semantics must agree between the Organization summary and the per-listing
# projection -- a current SOLD outcome recorded outside the selected window
# must never be reported as an in-window event, and must never be the sole
# reason a listing with no other in-window activity appears in a bounded
# (non-ALL_TIME) snapshot.
# ---------------------------------------------------------------------------


def test_sold_outcome_outside_window_excluded_from_bounded_snapshot(
    api_url: str, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-OLDSOLD", account_id="ACC-OLDSOLD", membership_id="OM-OLDSOLD"
    )

    # L-OLD-ONLY: no view, no Lead -- only a SOLD outcome recorded 30 days
    # ago. Must not appear at all in a 7-day window, and must not inflate
    # the 7-day summary's sold_outcomes count.
    _create_and_publish_listing(
        api_url,
        listing_id="NL-OLD-ONLY",
        org_id="ORG-OLDSOLD",
        account_id="ACC-OLDSOLD",
        membership_id="OM-OLDSOLD",
        physical_boat_id="PB-OLD-ONLY",
        market_episode_id="ME-OLD-ONLY",
    )
    _close_as_sold_directly(
        api_url, listing_id="NL-OLD-ONLY", org_id="ORG-OLDSOLD", account_id="ACC-OLDSOLD"
    )
    _backdate_sale_outcome_recorded_at(api_url, listing_id="NL-OLD-ONLY", days_ago=30)

    # L-ACTIVE-OLD-SOLD: one in-window view and one in-window Lead, but its
    # SOLD outcome was also recorded 30 days ago. Must still appear (due to
    # the in-window view/Lead), but its bounded SOLD fields must report
    # "not recorded in this window", not the stale SOLD fact.
    _create_and_publish_listing(
        api_url,
        listing_id="NL-ACTIVE-OLD-SOLD",
        org_id="ORG-OLDSOLD",
        account_id="ACC-OLDSOLD",
        membership_id="OM-OLDSOLD",
        physical_boat_id="PB-ACTIVE-OLD-SOLD",
        market_episode_id="ME-ACTIVE-OLD-SOLD",
    )
    assert client.get("/api/listings/NL-ACTIVE-OLD-SOLD").status_code == 200
    _create_lead(
        api_url, listing_id="NL-ACTIVE-OLD-SOLD", submission_operation_id="SUB-OLD-SOLD-LEAD"
    )
    _close_as_sold_directly(
        api_url, listing_id="NL-ACTIVE-OLD-SOLD", org_id="ORG-OLDSOLD", account_id="ACC-OLDSOLD"
    )
    _backdate_sale_outcome_recorded_at(api_url, listing_id="NL-ACTIVE-OLD-SOLD", days_ago=30)

    _log_in(client, "ACC-OLDSOLD")

    week = client.get("/api/broker/organizations/ORG-OLDSOLD/performance?window=LAST_7_DAYS")
    assert week.status_code == 200
    week_body = week.json()
    assert week_body["sold_outcomes"] == 0
    assert week_body["sold_outcomes_with_known_source"] == 0
    assert week_body["sold_outcomes_with_unknown_source"] == 0
    week_listings = {item["native_listing_id"]: item for item in week_body["listings"]}
    assert "NL-OLD-ONLY" not in week_listings
    active_old_sold = week_listings["NL-ACTIVE-OLD-SOLD"]
    assert active_old_sold["public_listing_views"] == 1
    assert active_old_sold["leads_received"] == 1
    assert active_old_sold["sold_outcome_recorded_at"] is None
    assert active_old_sold["sold_outcome_source_known"] is None

    all_time = client.get("/api/broker/organizations/ORG-OLDSOLD/performance?window=ALL_TIME")
    assert all_time.status_code == 200
    all_time_body = all_time.json()
    assert all_time_body["sold_outcomes"] == 2
    all_time_listings = {item["native_listing_id"]: item for item in all_time_body["listings"]}
    assert all_time_listings["NL-OLD-ONLY"]["sold_outcome_recorded_at"] is not None
    assert all_time_listings["NL-ACTIVE-OLD-SOLD"]["sold_outcome_recorded_at"] is not None


# ---------------------------------------------------------------------------
# Finding B (independent review, exact-head c30e4ab): discovery_surface is a
# second, mechanically independent evidence dimension from acquisition
# source, reused from the existing accepted SLICE-0071 Lead provenance model.
# ---------------------------------------------------------------------------


def test_discovery_source_breakdown_independent_of_acquisition_and_org_scoped(
    api_url: str, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-DISC", account_id="ACC-DISC", membership_id="OM-DISC"
    )
    _create_and_publish_listing(
        api_url,
        listing_id="NL-DISC",
        org_id="ORG-DISC",
        account_id="ACC-DISC",
        membership_id="OM-DISC",
        physical_boat_id="PB-DISC",
        market_episode_id="ME-DISC",
    )

    # A Lead with known discovery_surface (SHORTLIST) and a known but
    # *different* acquisition_channel (PAID_SEARCH, from utm_medium=cpc) --
    # proves the two dimensions are tracked independently, never one
    # inferred from the other.
    _create_lead(
        api_url,
        listing_id="NL-DISC",
        submission_operation_id="SUB-DISC-SHORTLIST",
        discovery_surface=DiscoverySurface.SHORTLIST,
        utm_source="newsletter",
        utm_medium="cpc",
        utm_campaign="spring-sale",
    )
    # A Lead with known discovery_surface (TECHNICAL_SEARCH) and no UTM
    # evidence at all -> acquisition stays UNKNOWN while discovery is known.
    _create_lead(
        api_url,
        listing_id="NL-DISC",
        submission_operation_id="SUB-DISC-SEARCH",
        discovery_surface=DiscoverySurface.TECHNICAL_SEARCH,
    )
    # A Lead with no discovery evidence at all -> explicit UNKNOWN, never a
    # guessed value.
    _create_lead(api_url, listing_id="NL-DISC", submission_operation_id="SUB-DISC-UNKNOWN")

    # A second Organization's Lead with its own distinct discovery evidence
    # must never leak into ORG-DISC's breakdown.
    _seed_org_and_membership(
        api_url, org_id="ORG-DISC-OTHER", account_id="ACC-DISC-OTHER", membership_id="OM-DISC-OTHER"
    )
    _create_and_publish_listing(
        api_url,
        listing_id="NL-DISC-OTHER",
        org_id="ORG-DISC-OTHER",
        account_id="ACC-DISC-OTHER",
        membership_id="OM-DISC-OTHER",
        physical_boat_id="PB-DISC-OTHER",
        market_episode_id="ME-DISC-OTHER",
    )
    _create_lead(
        api_url,
        listing_id="NL-DISC-OTHER",
        submission_operation_id="SUB-DISC-OTHER",
        discovery_surface=DiscoverySurface.COMPARE,
    )

    _log_in(client, "ACC-DISC")
    response = client.get("/api/broker/organizations/ORG-DISC/performance?window=ALL_TIME")
    assert response.status_code == 200
    body = response.json()

    assert body["discovery_source_breakdown"]["SHORTLIST"] == 1
    assert body["discovery_source_breakdown"]["TECHNICAL_SEARCH"] == 1
    assert body["discovery_source_breakdown"]["UNKNOWN"] == 1
    assert body["discovery_source_breakdown"].get("COMPARE", 0) == 0  # no cross-Org leakage

    assert body["acquisition_source_breakdown"]["PAID_SEARCH"] == 1
    assert body["acquisition_source_breakdown"]["UNKNOWN"] == 2

    # Mechanical independence: the SHORTLIST Lead is PAID_SEARCH, not the
    # TECHNICAL_SEARCH Lead -- one dimension is never derived from the other.
    assert sum(body["discovery_source_breakdown"].values()) == 3
    assert sum(body["acquisition_source_breakdown"].values()) == 3


# ---------------------------------------------------------------------------
# Route-level auth/validation outcomes
# ---------------------------------------------------------------------------


def test_performance_route_requires_authentication(client: TestClient) -> None:
    response = client.get("/api/broker/organizations/ORG-X/performance")
    assert response.status_code == 401


def test_performance_route_unknown_organization_is_not_found(
    api_url: str, client: TestClient
) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-KNOWN", account_id="ACC-KNOWN", membership_id="OM-KNOWN"
    )
    _log_in(client, "ACC-KNOWN")
    response = client.get("/api/broker/organizations/ORG-UNKNOWN/performance")
    assert response.status_code == 404


def test_performance_route_invalid_window_is_bounded_400(api_url: str, client: TestClient) -> None:
    _seed_org_and_membership(
        api_url, org_id="ORG-WIN", account_id="ACC-WIN", membership_id="OM-WIN"
    )
    _log_in(client, "ACC-WIN")
    response = client.get("/api/broker/organizations/ORG-WIN/performance?window=NEXT_CENTURY")
    assert response.status_code == 400
    assert response.json() == {"error": "invalid_window"}
