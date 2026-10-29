"""PostgreSQL + real HTTP tests for the SLICE-0096 bounded `page_after`/
`page_size` public Search HTTP contract
(`GET /api/search/{locale}` and `GET /api/search/{locale}/power`).

Mirrors `tests/persistence/test_search_sensitivity_api.py`'s real-database +
real-`TestClient` fixture style. Covers the normative contract's navigation-
parameter admission rules (`specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md`
§2):

- `page_after`/`page_size` are rejected on a BASE (no active requirement)
  request;
- a cursor accompanying a non-canonical technical query fails closed (400)
  rather than silently discarding it on a 308 redirect;
- malformed/duplicate/out-of-range `page_size` and duplicate/empty
  `page_after` fail closed;
- a genuine multi-page round trip through real HTTP recovers the same
  confirmed matches a single unbounded page would, with
  `evaluation_state`/`next_cursor` consistent at every step;
- a tampered, cross-query-bound or cross-domain (Sail cursor on the Power
  route) cursor fails closed with 400, never a silently "successful" page.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

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
    DraftClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    VesselCategory,
    VesselCategoryClaim,
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
from hullq.security.search_page_cursor import SearchPageCursorDomain, mint_search_page_cursor

VA = AssertionKind.VALUE_ASSERTION


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
    schema_name = f"hullq_s0096api_{uuid.uuid4().hex[:16]}"
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


_SECRET = b"0" * 32


@pytest.fixture()
def client(api_url: str) -> TestClient:
    from hullq.api.app import create_app

    app = create_app(database_url=api_url, preview_signing_secret=_SECRET)
    return TestClient(app)


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
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _seed_sail_claim_only_match(conn: Any, listing_id: str) -> None:
    """One claim-only, publisher-owned-SAIL, shallow-draft ACTIVE candidate
    -- always a confirmed `draft_max<=1.60` match, never requiring any
    BoatDesign/FieldResolution admission."""
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")
    physical_boat_id = f"PB-{listing_id}"
    market_episode_id = f"ME-{listing_id}"

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
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
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic SLICE-0096 API fixture listing.",
            asking_price_amount=Decimal("90000.00"),
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
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            draft=DraftClaim(assertion_kind=VA, value=Decimal("1.10")),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result


def _seed_power_claim_only_match(conn: Any, listing_id: str) -> None:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")
    physical_boat_id = f"PB-{listing_id}"
    market_episode_id = f"ME-{listing_id}"

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
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
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic SLICE-0096 API fixture listing.",
            asking_price_amount=Decimal("90000.00"),
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
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result


# ---------------------------------------------------------------------------
# Navigation-parameter admission rules
# ---------------------------------------------------------------------------


def test_page_after_on_base_request_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en", params={"page_after": "anything"})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_search_request"


def test_page_size_on_base_request_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en", params={"page_size": "20"})
    assert response.status_code == 400


@pytest.mark.parametrize("page_size", ["0", "51", "-1", "abc", "1.5", "01"])
def test_malformed_page_size_is_400(client: TestClient, page_size: str) -> None:
    response = client.get("/api/search/en", params={"draft_max": "1.60", "page_size": page_size})
    assert response.status_code == 400


def test_duplicate_page_size_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en?draft_max=1.60&page_size=10&page_size=20")
    assert response.status_code == 400


def test_duplicate_page_after_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en?draft_max=1.60&page_after=a&page_after=b")
    assert response.status_code == 400


def test_empty_page_after_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en?draft_max=1.60&page_after=")
    assert response.status_code == 400


def test_cursor_with_noncanonical_query_is_400_not_redirect(client: TestClient) -> None:
    # draft_max=1.600 is valid but non-canonical (trailing zero) -- without a
    # cursor this would 308; with a cursor present it must fail closed
    # instead of discarding/rebinding the cursor across the redirect.
    response = client.get("/api/search/en", params={"draft_max": "1.600", "page_after": "anything"})
    assert response.status_code == 400
    # Confirm the ordinary (no cursor) case is indeed still a 308, proving
    # the 400 above is specifically the cursor+redirect interaction.
    redirect_response = client.get(
        "/api/search/en", params={"draft_max": "1.600"}, follow_redirects=False
    )
    assert redirect_response.status_code == 308


# ---------------------------------------------------------------------------
# Genuine multi-page HTTP round trip
# ---------------------------------------------------------------------------


def test_sail_multi_page_http_round_trip_recovers_all_matches(
    client: TestClient, api_conn: Any
) -> None:
    listing_ids = [f"NL-0096API-SAIL-{i:04d}" for i in range(1, 4)]
    for listing_id in listing_ids:
        _seed_sail_claim_only_match(api_conn, listing_id)

    seen: list[str] = []
    next_cursor: str | None = None
    for _ in range(10):
        params: dict[str, str] = {"draft_max": "1.6", "page_size": "1"}
        if next_cursor is not None:
            params["page_after"] = next_cursor
        response = client.get("/api/search/en", params=params)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["page_size"] == 1
        assert body["evaluation_state"] in ("PARTIAL", "COMPLETE")
        matches = [m["native_listing_id"] for m in body["publisher_claim_matches"]]
        seen.extend(matches)
        if body["evaluation_state"] == "COMPLETE":
            assert body["next_cursor"] is None
            break
        assert body["next_cursor"] is not None
        next_cursor = body["next_cursor"]
    else:
        raise AssertionError("did not complete within 10 pages")

    assert sorted(seen) == sorted(listing_ids)
    assert len(seen) == len(set(seen))


def test_power_single_page_http_round_trip(client: TestClient, api_conn: Any) -> None:
    _seed_power_claim_only_match(api_conn, "NL-0096API-PWR-0001")
    response = client.get("/api/search/en/power", params={"power_drive": "SHAFT"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evaluation_state"] == "COMPLETE"
    assert body["next_cursor"] is None
    assert [m["native_listing_id"] for m in body["publisher_claim_matches"]] == [
        "NL-0096API-PWR-0001"
    ]


# ---------------------------------------------------------------------------
# Cursor tamper / cross-query / cross-domain failure closure
# ---------------------------------------------------------------------------


def test_tampered_cursor_is_400(client: TestClient, api_conn: Any) -> None:
    _seed_sail_claim_only_match(api_conn, "NL-0096API-TAMPER-0001")
    response = client.get(
        "/api/search/en", params={"draft_max": "1.6", "page_after": "not-a-real-cursor"}
    )
    assert response.status_code == 400


def test_cursor_bound_to_different_query_is_400(client: TestClient, api_conn: Any) -> None:
    for listing_id in ("NL-0096API-XQ-0001", "NL-0096API-XQ-0002"):
        _seed_sail_claim_only_match(api_conn, listing_id)

    first = client.get("/api/search/en", params={"draft_max": "1.6", "page_size": "1"})
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor is not None

    # Reusing the SAME cursor against a DIFFERENT draft_max query must fail
    # closed -- the cursor's query_identity binding no longer matches.
    reused = client.get(
        "/api/search/en", params={"draft_max": "2", "page_size": "1", "page_after": cursor}
    )
    assert reused.status_code == 400


def test_cursor_minted_for_sail_rejected_on_power_route(client: TestClient, api_conn: Any) -> None:
    _seed_power_claim_only_match(api_conn, "NL-0096API-XDOM-0001")
    sail_cursor = mint_search_page_cursor(
        domain=SearchPageCursorDomain.SAIL,
        query_identity="/en/power/search?power_drive=SHAFT",
        page_size=20,
        last_native_listing_id="NL-0096API-XDOM-0001",
        secret=_SECRET,
    )
    response = client.get(
        "/api/search/en/power",
        params={"power_drive": "SHAFT", "page_after": sail_cursor},
    )
    assert response.status_code == 400
