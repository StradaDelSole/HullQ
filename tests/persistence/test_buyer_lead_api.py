"""FastAPI integration tests for SLICE-0070 durable buyer contact / Lead creation.

Uses a directly minted session token (mirrors `test_media_gallery_api.py`'s
identical pattern) for the optional-attribution cases. Covers
`specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md` §17's required
proof matrix items 1-8, 11-13.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.buyer_lead import LeadId
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
from hullq.persistence.buyer_lead import fetch_buyer_lead
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import (
    list_publication_transitions,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.security.session_token import mint_session_token

_SECRET = b"7" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "marketplace-buyer-lead-v1"


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
    schema_name = f"hullq_s0070api_{uuid.uuid4().hex[:16]}"
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
        preview_signing_secret=b"0" * 32,
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


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


def _valid_body(**overrides: Any) -> dict[str, Any]:
    body: dict[str, Any] = {
        "submission_operation_id": "OP-1",
        "name": "Jane Buyer",
        "email": "jane@example.com",
        "message": "Interested in this boat.",
    }
    body.update(overrides)
    return body


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


def _lead_count(conn: Any) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT COUNT(*) FROM buyer_leads")
        return cur.fetchone()[0]


# ---------------------------------------------------------------------------
# CSRF / transport-shape boundary
# ---------------------------------------------------------------------------


def test_missing_csrf_header_is_rejected_403(client: TestClient, api_conn: Any) -> None:
    resp = client.post(
        "/api/listings/NL-NEVER/contact",
        json=_valid_body(),
        headers={"Origin": _WEB_ORIGIN},
    )
    assert resp.status_code == 403
    assert _lead_count(api_conn) == 0


def test_wrong_origin_is_rejected_403(client: TestClient, api_conn: Any) -> None:
    resp = client.post(
        "/api/listings/NL-NEVER/contact",
        json=_valid_body(),
        headers={"Origin": "http://evil.test", "X-HullQ-Requested-With": _CSRF_HEADER_VALUE},
    )
    assert resp.status_code == 403
    assert _lead_count(api_conn) == 0


def test_oversized_content_length_is_rejected_413(client: TestClient, api_conn: Any) -> None:
    huge_message = "x" * 25_000
    resp = client.post(
        "/api/listings/NL-NEVER/contact",
        json=_valid_body(message=huge_message),
        headers=_csrf_headers(),
    )
    assert resp.status_code == 413
    assert _lead_count(api_conn) == 0


def test_non_object_json_body_is_invalid_input(client: TestClient, api_conn: Any) -> None:
    resp = client.post(
        "/api/listings/NL-NEVER/contact", json=["not", "an", "object"], headers=_csrf_headers()
    )
    assert resp.status_code == 400
    assert resp.json()["error"] == "invalid_input"
    assert _lead_count(api_conn) == 0


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"email": "not-an-email"},
        {"message": ""},
        {"submission_operation_id": ""},
        {"name": None},
    ],
)
def test_invalid_field_produces_zero_mutation(
    client: TestClient, api_conn: Any, overrides: dict[str, Any]
) -> None:
    resp = client.post(
        "/api/listings/NL-NEVER/contact", json=_valid_body(**overrides), headers=_csrf_headers()
    )
    assert resp.status_code == 400
    assert resp.json() == {"error": "invalid_input"}
    assert _lead_count(api_conn) == 0


# ---------------------------------------------------------------------------
# Creation / attribution / idempotency
# ---------------------------------------------------------------------------


def test_anonymous_valid_submission_creates_exactly_one_lead(
    client: TestClient, api_url: str, api_conn: Any
) -> None:
    _publish_listing(api_conn, listing_id="NL-API01")
    api_conn.commit()

    resp = client.post(
        "/api/listings/NL-API01/contact", json=_valid_body(), headers=_csrf_headers()
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "CREATED"
    assert isinstance(body["lead_id"], str) and body["lead_id"]
    assert set(body.keys()) == {"status", "lead_id", "received_at"}

    verify = psycopg.connect(api_url)
    try:
        record = fetch_buyer_lead(verify, LeadId(body["lead_id"]))
        assert record is not None
        assert record.account_id is None
        assert record.buyer_email == "jane@example.com"
        assert record.contact_email_verification_state.value == "UNVERIFIED"
        assert _lead_count(verify) == 1
    finally:
        verify.close()


def test_authenticated_submission_records_account_id_still_unverified(
    client: TestClient, api_url: str, api_conn: Any
) -> None:
    _publish_listing(api_conn, listing_id="NL-API02")
    with api_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
            ["ACC-BUYER02"],
        )
    api_conn.commit()

    _log_in(client, "ACC-BUYER02")
    resp = client.post(
        "/api/listings/NL-API02/contact", json=_valid_body(), headers=_csrf_headers()
    )
    assert resp.status_code == 201
    body = resp.json()

    verify = psycopg.connect(api_url)
    try:
        record = fetch_buyer_lead(verify, LeadId(body["lead_id"]))
        assert record is not None
        assert record.account_id == AccountId("ACC-BUYER02")
        assert record.contact_email_verification_state.value == "UNVERIFIED"
    finally:
        verify.close()


def test_client_supplied_organization_field_is_ignored(
    client: TestClient, api_url: str, api_conn: Any
) -> None:
    _account, org, _membership = _publish_listing(api_conn, listing_id="NL-API03")
    api_conn.commit()

    resp = client.post(
        "/api/listings/NL-API03/contact",
        json=_valid_body(publishing_organization_id="ORG-SPOOFED", organization_id="ORG-SPOOFED"),
        headers=_csrf_headers(),
    )
    assert resp.status_code == 201
    body = resp.json()

    verify = psycopg.connect(api_url)
    try:
        record = fetch_buyer_lead(verify, LeadId(body["lead_id"]))
        assert record is not None
        assert record.publishing_organization_id == org.id
        assert record.publishing_organization_id != MarketplaceOrganizationId("ORG-SPOOFED")
    finally:
        verify.close()


def test_exact_retry_is_idempotent_over_http(client: TestClient, api_conn: Any) -> None:
    _publish_listing(api_conn, listing_id="NL-API04")
    api_conn.commit()

    body = _valid_body(submission_operation_id="OP-API04")
    first = client.post("/api/listings/NL-API04/contact", json=body, headers=_csrf_headers())
    assert first.status_code == 201
    second = client.post("/api/listings/NL-API04/contact", json=body, headers=_csrf_headers())
    assert second.status_code == 200
    assert second.json()["status"] == "ALREADY_EXISTS"
    assert second.json()["lead_id"] == first.json()["lead_id"]
    assert _lead_count(api_conn) == 1


def test_same_operation_id_different_envelope_is_submission_conflict(
    client: TestClient, api_conn: Any
) -> None:
    _publish_listing(api_conn, listing_id="NL-API05")
    api_conn.commit()

    first = client.post(
        "/api/listings/NL-API05/contact",
        json=_valid_body(submission_operation_id="OP-API05"),
        headers=_csrf_headers(),
    )
    assert first.status_code == 201
    second = client.post(
        "/api/listings/NL-API05/contact",
        json=_valid_body(submission_operation_id="OP-API05", message="A different message."),
        headers=_csrf_headers(),
    )
    assert second.status_code == 409
    assert second.json() == {"error": "submission_conflict"}
    assert _lead_count(api_conn) == 1


# ---------------------------------------------------------------------------
# Non-enumerating listing-not-available boundary (contract §5/§10)
# ---------------------------------------------------------------------------


def test_missing_listing_is_listing_not_available(client: TestClient, api_conn: Any) -> None:
    resp = client.post(
        "/api/listings/NL-NEVER-EXISTED/contact", json=_valid_body(), headers=_csrf_headers()
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "listing_not_available"}
    assert _lead_count(api_conn) == 0


def test_draft_listing_is_listing_not_available(client: TestClient, api_conn: Any) -> None:
    account = AccountId("ACC-API06")
    org = _org("ORG-API06")
    membership = _membership(org, account, "OM-API06")
    create_physical_boat(api_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-API06")))
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-API06"), physical_boat_id=PhysicalBoatId("PB-API06")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-API06"), market_episode_id=MarketEpisodeId("ME-API06")
        ),
    )
    api_conn.commit()

    resp = client.post(
        "/api/listings/NL-API06/contact", json=_valid_body(), headers=_csrf_headers()
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "listing_not_available"}
    assert _lead_count(api_conn) == 0


def test_withdrawn_listing_is_listing_not_available(client: TestClient, api_conn: Any) -> None:
    account, org, membership = _publish_listing(api_conn, listing_id="NL-API07")
    api_conn.commit()
    withdraw_result = withdraw_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-API07"),
    )
    assert withdraw_result.status.value == "transitioned", withdraw_result
    api_conn.commit()

    resp = client.post(
        "/api/listings/NL-API07/contact", json=_valid_body(), headers=_csrf_headers()
    )
    assert resp.status_code == 404
    assert resp.json() == {"error": "listing_not_available"}
    assert _lead_count(api_conn) == 0


def test_active_but_stale_listing_is_listing_not_available(
    api_url: str, api_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    _publish_listing(api_conn, listing_id="NL-API08")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-API08"))
    confirmed_at = transitions[0].occurred_at

    app = create_app(
        database_url=api_url,
        preview_signing_secret=b"0" * 32,
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
        freshness_as_of_override=confirmed_at + timedelta(days=37),
    )
    stale_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        resp = stale_client.post(
            "/api/listings/NL-API08/contact", json=_valid_body(), headers=_csrf_headers()
        )
        assert resp.status_code == 404
        assert resp.json() == {"error": "listing_not_available"}
    finally:
        stale_client.close()
    assert _lead_count(api_conn) == 0
