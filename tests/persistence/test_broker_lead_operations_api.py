"""FastAPI integration tests for SLICE-0071 broker Lead operations +
notification-recipient configuration.

Mirrors `test_broker_inventory_lifecycle_api.py`'s pattern: a directly
minted session token rather than a full OIDC round-trip. Covers contract
§2 (tenancy/auth/non-enumeration), §5/§6/§7/§8/§8A (operational mutations),
§9 (OWNER/ADMIN-gated notification config), §14 (CSRF) and §15 (membership
revocation observed fresh, cross-Organization access impossible).
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
from hullq.domain.buyer_lead import SubmissionOperationId
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
    update_membership_state,
)
from hullq.persistence.buyer_lead import create_buyer_lead
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing, withdraw_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.security.session_token import mint_session_token

_SECRET = b"7" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_NAME = "x-hullq-requested-with"
_CSRF_HEADER_VALUE = "broker-lead-operations-v1"


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
    schema_name = f"hullq_s0071api_{uuid.uuid4().hex[:16]}"
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
        cur.execute("INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id])
    conn.commit()


def _session_cookie(account_id: str, *, mfa: bool = True) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=mfa,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SECRET)
    return minted.token


def _log_in(client: TestClient, account_id: str, *, mfa: bool = True) -> None:
    client.cookies.set("hullq_session", _session_cookie(account_id, mfa=mfa), domain="api.test")


def _seed_membership(
    api_url: str,
    *,
    org_id: str,
    account_id: str,
    membership_id: str,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
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
                roles=roles,
                state=state,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _publish_listing_and_create_lead(api_url: str, *, listing_id: str, org_id: str) -> str:
    """Publish one complete NativeListing under *org_id* and durably create
    one buyer Lead against it (reusing the accepted SLICE-0070 creation
    path), returning the created `lead_id`."""
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(f"ACC-owner-{listing_id}")
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-owner-{listing_id}"),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        _ensure_account(conn, account.value)
        seed_marketplace_organization(conn, org)
        conn.commit()
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
        publish_result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert publish_result.status.value == "transitioned", publish_result

        lead_result = create_buyer_lead(
            conn,
            submission_operation_id=SubmissionOperationId(f"OP-{listing_id}"),
            native_listing_id=NativeListingId(listing_id),
            account_id=None,
            buyer_name="Jane Buyer",
            buyer_email="jane@example.com",
            buyer_message="Interested in this boat.",
            as_of=datetime.now(UTC),
        )
        conn.commit()
        assert lead_result.status.value == "created", lead_result
        assert lead_result.lead_id is not None
        return lead_result.lead_id.value
    finally:
        conn.close()


def _withdraw_listing(api_url: str, *, listing_id: str, org_id: str, account_id: str) -> None:
    conn = psycopg.connect(api_url)
    try:
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-owner-{listing_id}"),
            account_id=AccountId(account_id),
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        result = withdraw_native_listing(
            conn,
            account_id=AccountId(account_id),
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        conn.commit()
        assert result.status.value == "transitioned", result
    finally:
        conn.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, _CSRF_HEADER_NAME: _CSRF_HEADER_VALUE}


# ---------------------------------------------------------------------------
# Tenancy / auth (contract §2)
# ---------------------------------------------------------------------------


def test_unauthenticated_inbox_read_is_rejected(client: TestClient, api_url: str) -> None:
    _seed_membership(api_url, org_id="ORG-A", account_id="ACC-1", membership_id="OM-1")
    resp = client.get("/api/broker/organizations/ORG-A/leads")
    assert resp.status_code == 401


def test_foreign_and_unknown_organization_share_identical_not_found_shape(
    client: TestClient, api_url: str
) -> None:
    _seed_membership(api_url, org_id="ORG-A", account_id="ACC-1", membership_id="OM-1")
    _log_in(client, "ACC-1")
    unknown = client.get("/api/broker/organizations/ORG-UNKNOWN/leads")
    foreign = client.get("/api/broker/organizations/ORG-B/leads")
    assert unknown.status_code == 404
    assert foreign.status_code == 404
    assert unknown.json() == foreign.json()


def test_lead_belonging_to_foreign_organization_is_not_found(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LX1", org_id="ORG-X")
    _seed_membership(api_url, org_id="ORG-Y", account_id="ACC-2", membership_id="OM-2")
    _log_in(client, "ACC-2")
    resp = client.get(f"/api/broker/organizations/ORG-Y/leads/{lead_id}")
    assert resp.status_code == 404


def test_membership_revocation_is_observed_fresh(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LX2", org_id="ORG-Z")
    _seed_membership(api_url, org_id="ORG-Z", account_id="ACC-3", membership_id="OM-3")
    _log_in(client, "ACC-3")
    ok = client.get(f"/api/broker/organizations/ORG-Z/leads/{lead_id}")
    assert ok.status_code == 200

    conn = psycopg.connect(api_url)
    try:
        update_membership_state(conn, OrganizationMembershipId("OM-3"), MembershipState.INACTIVE)
        conn.commit()
    finally:
        conn.close()

    denied = client.get(f"/api/broker/organizations/ORG-Z/leads/{lead_id}")
    assert denied.status_code == 404


# ---------------------------------------------------------------------------
# Full operational happy path (contract §5/§6/§7/§8/§8A)
# ---------------------------------------------------------------------------


def test_full_lead_operations_happy_path(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LH1", org_id="ORG-H")
    _seed_membership(api_url, org_id="ORG-H", account_id="ACC-broker", membership_id="OM-H")
    _log_in(client, "ACC-broker")

    detail = client.get(f"/api/broker/organizations/ORG-H/leads/{lead_id}")
    assert detail.status_code == 200
    body = detail.json()
    assert body["operational_state"]["is_unread"] is True
    assert body["operational_state"]["operational_status"] == "NEW"
    assert body["contact_email_verification_state"] == "UNVERIFIED"
    assert body["notification_delivery"]["status"] == "PENDING"
    assert body["acquisition_provenance"]["acquisition_channel"] == "UNKNOWN"

    read_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/read", headers=_csrf_headers()
    )
    assert read_resp.status_code == 200

    assign_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/assignment",
        headers=_csrf_headers(),
        json={"assignee_account_id": "ACC-broker", "expected_version": 0},
    )
    assert assign_resp.status_code == 200
    version_after_assign = assign_resp.json()["operational_state"]["version"]

    status_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/status",
        headers=_csrf_headers(),
        json={"status": "IN_PROGRESS", "expected_version": version_after_assign},
    )
    assert status_resp.status_code == 200
    version_after_status = status_resp.json()["operational_state"]["version"]

    note_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/notes",
        headers=_csrf_headers(),
        json={"text": "Called the buyer, left a voicemail."},
    )
    assert note_resp.status_code == 200

    contact_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/contact-attempts",
        headers=_csrf_headers(),
        json={"channel": "PHONE", "note": "No answer."},
    )
    assert contact_resp.status_code == 200

    follow_up_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/follow-up",
        headers=_csrf_headers(),
        json={"due_at": "2030-01-01T00:00:00+00:00", "expected_version": version_after_status},
    )
    assert follow_up_resp.status_code == 200
    version_after_follow_up = follow_up_resp.json()["operational_state"]["version"]

    close_resp = client.post(
        f"/api/broker/organizations/ORG-H/leads/{lead_id}/close",
        headers=_csrf_headers(),
        json={"close_reason": "NOT_INTERESTED", "expected_version": version_after_follow_up},
    )
    assert close_resp.status_code == 200
    assert close_resp.json()["operational_state"]["operational_status"] == "CLOSED"

    final_detail = client.get(f"/api/broker/organizations/ORG-H/leads/{lead_id}")
    final_body = final_detail.json()
    assert final_body["operational_state"]["is_unread"] is False
    assert final_body["operational_state"]["assigned_account_id"] == "ACC-broker"
    assert final_body["operational_state"]["close_reason"] == "NOT_INTERESTED"
    event_types = [event["event_type"] for event in final_body["timeline"]]
    for expected in ("MARKED_READ", "ASSIGNED", "STATUS_CHANGED", "NOTE", "CONTACT_ATTEMPT", "FOLLOW_UP_SET", "CLOSED"):
        assert expected in event_types


def test_stale_version_conflicts_without_silent_overwrite(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LH2", org_id="ORG-H2")
    _seed_membership(api_url, org_id="ORG-H2", account_id="ACC-broker2", membership_id="OM-H2")
    _log_in(client, "ACC-broker2")

    stale = client.post(
        f"/api/broker/organizations/ORG-H2/leads/{lead_id}/status",
        headers=_csrf_headers(),
        json={"status": "IN_PROGRESS", "expected_version": 99},
    )
    assert stale.status_code == 409


def test_close_without_reason_is_invalid_input(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LH3", org_id="ORG-H3")
    _seed_membership(api_url, org_id="ORG-H3", account_id="ACC-broker3", membership_id="OM-H3")
    _log_in(client, "ACC-broker3")

    resp = client.post(
        f"/api/broker/organizations/ORG-H3/leads/{lead_id}/status",
        headers=_csrf_headers(),
        json={"status": "CLOSED", "expected_version": 0},
    )
    assert resp.status_code == 400


def test_csrf_is_required_for_mutations(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LH4", org_id="ORG-H4")
    _seed_membership(api_url, org_id="ORG-H4", account_id="ACC-broker4", membership_id="OM-H4")
    _log_in(client, "ACC-broker4")

    resp = client.post(f"/api/broker/organizations/ORG-H4/leads/{lead_id}/read")
    assert resp.status_code == 403


def test_withdrawing_listing_keeps_historical_lead_readable(client: TestClient, api_url: str) -> None:
    lead_id = _publish_listing_and_create_lead(api_url, listing_id="LH5", org_id="ORG-H5")
    _seed_membership(api_url, org_id="ORG-H5", account_id="ACC-broker5", membership_id="OM-H5")
    _log_in(client, "ACC-broker5")

    _withdraw_listing(api_url, listing_id="LH5", org_id="ORG-H5", account_id="ACC-owner-LH5")

    resp = client.get(f"/api/broker/organizations/ORG-H5/leads/{lead_id}")
    assert resp.status_code == 200
    assert resp.json()["lead_id"] == lead_id


# ---------------------------------------------------------------------------
# Notification recipient configuration — OWNER/ADMIN only (contract §9)
# ---------------------------------------------------------------------------


def test_publisher_only_cannot_set_notification_email(client: TestClient, api_url: str) -> None:
    _seed_membership(
        api_url,
        org_id="ORG-N1",
        account_id="ACC-pub",
        membership_id="OM-N1",
        roles=frozenset({MembershipRole.PUBLISHER}),
    )
    _log_in(client, "ACC-pub")
    resp = client.put(
        "/api/broker/organizations/ORG-N1/notification-config",
        headers=_csrf_headers(),
        json={"notification_email": "owner@example.com", "expected_version": 0},
    )
    assert resp.status_code == 403
    assert resp.json()["error"] == "role_required"


def test_owner_can_set_and_clear_notification_email(client: TestClient, api_url: str) -> None:
    _seed_membership(
        api_url,
        org_id="ORG-N2",
        account_id="ACC-owner",
        membership_id="OM-N2",
        roles=frozenset({MembershipRole.OWNER}),
    )
    _log_in(client, "ACC-owner")

    set_resp = client.put(
        "/api/broker/organizations/ORG-N2/notification-config",
        headers=_csrf_headers(),
        json={"notification_email": "owner@example.com", "expected_version": 0},
    )
    assert set_resp.status_code == 200
    assert set_resp.json()["notification_email"] == "owner@example.com"

    get_resp = client.get("/api/broker/organizations/ORG-N2/notification-config")
    assert get_resp.json()["notification_email"] == "owner@example.com"

    clear_resp = client.put(
        "/api/broker/organizations/ORG-N2/notification-config",
        headers=_csrf_headers(),
        json={"notification_email": None, "expected_version": 1},
    )
    assert clear_resp.status_code == 200
    assert clear_resp.json()["notification_email"] is None


def test_admin_can_set_notification_email(client: TestClient, api_url: str) -> None:
    _seed_membership(
        api_url,
        org_id="ORG-N3",
        account_id="ACC-admin",
        membership_id="OM-N3",
        roles=frozenset({MembershipRole.ADMIN}),
    )
    _log_in(client, "ACC-admin")
    resp = client.put(
        "/api/broker/organizations/ORG-N3/notification-config",
        headers=_csrf_headers(),
        json={"notification_email": "admin@example.com", "expected_version": 0},
    )
    assert resp.status_code == 200
