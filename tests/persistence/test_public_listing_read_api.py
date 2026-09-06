"""PostgreSQL + real HTTP tests for the SLICE-0049 public listing read model/API.

Covers §8/§9 "public FastAPI read boundary": ACTIVE-only visibility,
DRAFT/WITHDRAWN/missing/incomplete collapsing to the identical not-found
response, no preview token required, noindex response header, and no
internal metadata leakage. Mirrors the SLICE-0048
tests/persistence/test_preview_api_read_model.py isolation pattern.
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
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0049api_{uuid.uuid4().hex[:16]}"
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


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    broker_description: str = "A well-maintained cruising sloop.",
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

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
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_active_listing_returns_expected_public_projection(
    api_conn: Any, client: TestClient
) -> None:
    _make_active_listing(
        api_conn,
        listing_id="NL-PUB-A",
        physical_boat_id="PB-PUB-A",
        market_episode_id="ME-PUB-A",
        offer_revision_id="REV-PUB-A",
    )

    response = client.get("/api/listings/NL-PUB-A")
    assert response.status_code == 200
    body = response.json()

    assert body["asking_price_mode"] == "AMOUNT"
    assert body["asking_price_amount"] == "125000.00"
    assert body["currency"] == "EUR"
    assert body["location_country"] == "FR"
    assert body["broker_description"] == "A well-maintained cruising sloop."
    assert body["publishing_organization_id"] == "ORG-NL-PUB-A"
    assert body["hullq_vat_verification_status"] == "NONE"
    assert "offer_recorded_at" in body
    assert "preview_expires_at" not in body


def test_active_listing_response_has_noindex_header_and_no_preview_confidentiality(
    api_conn: Any, client: TestClient
) -> None:
    _make_active_listing(
        api_conn,
        listing_id="NL-PUB-B",
        physical_boat_id="PB-PUB-B",
        market_episode_id="ME-PUB-B",
        offer_revision_id="REV-PUB-B",
    )

    response = client.get("/api/listings/NL-PUB-B")
    assert response.headers["x-robots-tag"] == "noindex"
    # SLICE-0049 §12: the public route must not copy the preview route's
    # bearer-capability confidentiality headers.
    assert "cache-control" not in {k.lower() for k in response.headers}
    assert "referrer-policy" not in {k.lower() for k in response.headers}


def test_preview_route_still_carries_its_own_confidentiality_headers(client: TestClient) -> None:
    """Adding the public route must not weaken the accepted SLICE-0048
    preview surface's own response headers."""
    response = client.get("/api/_preview/listings/not-a-real-token")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


def test_no_internal_metadata_is_exposed(api_conn: Any, client: TestClient) -> None:
    _make_active_listing(
        api_conn,
        listing_id="NL-PUB-C",
        physical_boat_id="PB-PUB-C",
        market_episode_id="ME-PUB-C",
        offer_revision_id="REV-PUB-C",
    )

    body = client.get("/api/listings/NL-PUB-C").json()
    forbidden_keys = {
        "created_by_account_id",
        "recorded_by_account_id",
        "revision_id",
        "offer_revision_id",
        "content_hash",
        "native_listing_id",
        "market_episode_id",
        "physical_boat_id",
        "lifecycle_state",
        "publication_transition_id",
    }
    assert forbidden_keys.isdisjoint(body.keys())


def test_malicious_broker_text_is_returned_verbatim_by_the_api_json(
    api_conn: Any, client: TestClient
) -> None:
    """The API is a JSON boundary, not an HTML boundary: escaping happens at
    the Astro/web presentation layer, not here. This asserts the API does
    not itself mutate/strip broker text."""
    malicious_text = "<script>alert('xss')</script>"
    _make_active_listing(
        api_conn,
        listing_id="NL-PUB-D",
        physical_boat_id="PB-PUB-D",
        market_episode_id="ME-PUB-D",
        offer_revision_id="REV-PUB-D",
        broker_description=malicious_text,
    )

    body = client.get("/api/listings/NL-PUB-D").json()
    assert body["broker_description"] == malicious_text


def test_draft_listing_is_externally_not_found(api_conn: Any, client: TestClient) -> None:
    account = AccountId("ACC-DRAFT")
    org = _org("ORG-DRAFT")
    membership = _membership(org, account, "OM-DRAFT")
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId("NL-DRAFT")),
    )

    response = client.get("/api/listings/NL-DRAFT")
    assert response.status_code == 404


def test_withdrawn_listing_is_externally_not_found(api_conn: Any, client: TestClient) -> None:
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-WITHDRAWN",
        physical_boat_id="PB-WITHDRAWN",
        market_episode_id="ME-WITHDRAWN",
        offer_revision_id="REV-WITHDRAWN",
    )
    withdraw_result = withdraw_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-WITHDRAWN"),
    )
    assert withdraw_result.status.value == "transitioned"

    response = client.get("/api/listings/NL-WITHDRAWN")
    assert response.status_code == 404


def test_missing_listing_is_externally_not_found(client: TestClient) -> None:
    response = client.get("/api/listings/NL-NEVER-CREATED")
    assert response.status_code == 404


def test_incomplete_active_chain_is_not_reachable_because_publish_itself_fails_closed(
    api_conn: Any, client: TestClient
) -> None:
    """An incomplete listing can never reach ACTIVE at all (publish requires
    completeness), so it is already covered by the DRAFT not-found case --
    this test only re-confirms the same not-found response for a listing
    with a MarketEpisode link but no current offer (still DRAFT)."""
    account = AccountId("ACC-NOOFFER")
    org = _org("ORG-NOOFFER")
    membership = _membership(org, account, "OM-NOOFFER")
    create_physical_boat(api_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-NOOFFER")))
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-NOOFFER"), physical_boat_id=PhysicalBoatId("PB-NOOFFER")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-NOOFFER"), market_episode_id=MarketEpisodeId("ME-NOOFFER")
        ),
    )

    response = client.get("/api/listings/NL-NOOFFER")
    assert response.status_code == 404
