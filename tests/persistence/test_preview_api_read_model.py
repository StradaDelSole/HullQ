"""PostgreSQL + real HTTP tests for the SLICE-0048 preview read model/API.

Covers §6/§11 "API/read model": explicit current-head use, every failure
case collapsing to the identical not-found response, decimal losslessness,
omission/assertion distinctions, VAT qualification/attribution, and that no
internal metadata is exposed. Each test runs against its own disposable
PostgreSQL schema, mirroring the SLICE-0045/0048 integration test isolation
pattern.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.application.listing_intake import ListingIntakeRequest, run_listing_intake
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    AssertionKind,
    KnownHistoryNarrativeClaim,
    LocationRegionClaim,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
    VatTaxStatusClaim,
    VatTaxStatusValue,
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
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.preview_token import mint_preview_token

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
    schema_name = f"hullq_s0048api_{uuid.uuid4().hex[:16]}"
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


_SECRET = os.urandom(32)


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


def _full_request(**overrides: object) -> ListingIntakeRequest:
    account = AccountId("ACC-API-T")
    org = _org("ORG-API-T")
    membership = _membership(org, account, "OM-API-T")
    base = ListingIntakeRequest(
        account_id=account,
        organization=org,
        membership=membership,
        physical_boat_id=PhysicalBoatId("PB-API-T"),
        boat_design_ref=None,
        market_episode_id=MarketEpisodeId("ME-API-T"),
        native_listing_id=NativeListingId("NL-API-T"),
        broker_listing_reference=None,
        offer_revision_id=NativeListingOfferRevisionId("REV-API-T"),
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
            location_region=LocationRegionClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value="Brittany"
            ),
            known_history_narrative=KnownHistoryNarrativeClaim(
                assertion_kind=AssertionKind.NO_KNOWN_HISTORY_DECLARED
            ),
            vat_tax_status_claim=VatTaxStatusClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=VatTaxStatusValue.VAT_PAID
            ),
        ),
    )
    import dataclasses

    return dataclasses.replace(base, **overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_valid_token_returns_expected_public_projection(api_conn: Any, client: TestClient) -> None:
    request = _full_request()
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None

    response = client.get(f"/api/_preview/listings/{result.preview_token}")
    assert response.status_code == 200
    body = response.json()

    assert body["asking_price_mode"] == "AMOUNT"
    assert body["asking_price_amount"] == "125000.00"
    assert body["currency"] == "EUR"
    assert body["location_country"] == "FR"
    assert body["location_region"] == {"assertion_kind": "VALUE_ASSERTION", "value": "Brittany"}
    assert body["broker_summary"] is None  # omitted in this fixture, distinct from any assertion
    assert body["broker_description"] == "A well-maintained cruising sloop."
    assert body["known_history_narrative"] == {
        "assertion_kind": "NO_KNOWN_HISTORY_DECLARED",
        "value": None,
    }
    assert body["vat_tax_status_claim"] == {
        "assertion_kind": "VALUE_ASSERTION",
        "value": "VAT_PAID",
    }
    assert body["publishing_organization_id"] == "ORG-API-T"
    assert body["hullq_vat_verification_status"] == "NONE"
    assert "offer_recorded_at" in body
    assert "preview_expires_at" in body


def test_response_headers_are_private_no_store_no_referrer_noindex(
    api_conn: Any, client: TestClient
) -> None:
    request = _full_request()
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None

    response = client.get(f"/api/_preview/listings/{result.preview_token}")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["x-robots-tag"] == "noindex, nofollow, noarchive"


def test_no_internal_metadata_is_exposed(api_conn: Any, client: TestClient) -> None:
    request = _full_request()
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None

    body = client.get(f"/api/_preview/listings/{result.preview_token}").json()
    forbidden_keys = {
        "created_by_account_id",
        "recorded_by_account_id",
        "revision_id",
        "offer_revision_id",
        "content_hash",
        "native_listing_id",
        "market_episode_id",
        "physical_boat_id",
    }
    assert forbidden_keys.isdisjoint(body.keys())


def test_asking_price_amount_is_lossless_decimal_string_never_float(
    api_conn: Any, client: TestClient
) -> None:
    request = _full_request(
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Precision price test.",
            asking_price_amount=Decimal("99999.10"),
            currency="EUR",
        )
    )
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None

    body = client.get(f"/api/_preview/listings/{result.preview_token}").json()
    # A binary float would corrupt/round this value (e.g. to "99999.1" losing
    # the trailing zero, or to a repeating-binary approximation); the exact
    # decimal string must survive untouched.
    assert body["asking_price_amount"] == "99999.10"
    assert isinstance(body["asking_price_amount"], str)


def test_poa_mode_has_no_amount_or_currency(api_conn: Any, client: TestClient) -> None:
    request = _full_request(
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.POA,
            location_country="FR",
            broker_description="Price on application test.",
        )
    )
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None

    body = client.get(f"/api/_preview/listings/{result.preview_token}").json()
    assert body["asking_price_mode"] == "POA"
    assert body["asking_price_amount"] is None
    assert body["currency"] is None


def test_tampered_token_is_not_found(api_conn: Any, client: TestClient) -> None:
    request = _full_request()
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None
    tampered = result.preview_token[:-1] + ("A" if result.preview_token[-1] != "A" else "B")

    response = client.get(f"/api/_preview/listings/{tampered}")
    assert response.status_code == 404


def test_malformed_token_is_not_found(client: TestClient) -> None:
    response = client.get("/api/_preview/listings/not-a-real-token")
    assert response.status_code == 404


def test_junk_character_injected_token_is_not_found(api_conn: Any, client: TestClient) -> None:
    """AMEND regression (PR #156, review 5123788117, finding 2).

    `base64.urlsafe_b64decode`'s default lax mode silently discards
    characters outside the base64 alphabet, so a non-canonical alias of a
    valid token (junk spliced into an otherwise-valid segment) could decode
    to the identical bytes as the original and verify successfully. Such an
    alias must resolve to the same not-found response as any other invalid
    token -- never succeed.
    """
    request = _full_request()
    result = run_listing_intake(api_conn, request=request, preview_signing_secret=_SECRET)
    assert result.preview_token is not None
    payload_part, signature_part = result.preview_token.split(".")
    tampered = payload_part[:4] + "!!!!" + payload_part[4:] + "." + signature_part

    response = client.get(f"/api/_preview/listings/{quote(tampered, safe='')}")
    assert response.status_code == 404


def test_wrong_secret_token_is_not_found(api_conn: Any, client: TestClient) -> None:
    other_secret = os.urandom(32)
    minted = mint_preview_token(NativeListingId("NL-API-T"), secret=other_secret)
    response = client.get(f"/api/_preview/listings/{minted.token}")
    assert response.status_code == 404


def test_valid_token_for_nonexistent_listing_is_not_found(client: TestClient) -> None:
    minted = mint_preview_token(NativeListingId("NL-NEVER-CREATED"), secret=_SECRET)
    response = client.get(f"/api/_preview/listings/{minted.token}")
    assert response.status_code == 404


def test_unresolved_market_episode_link_is_not_previewable(
    api_conn: Any, client: TestClient
) -> None:
    account = AccountId("ACC-UNRESOLVED")
    org = _org("ORG-UNRESOLVED")
    membership = _membership(org, account, "OM-UNRESOLVED")
    # A NativeListing with market_episode_id left NULL (unresolved).
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId("NL-UNRESOLVED")),
    )
    minted = mint_preview_token(NativeListingId("NL-UNRESOLVED"), secret=_SECRET)
    response = client.get(f"/api/_preview/listings/{minted.token}")
    assert response.status_code == 404


def test_no_current_offer_is_not_previewable(api_conn: Any, client: TestClient) -> None:
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
    # No offer revision written -- there is no current LISTING_OFFER head.
    minted = mint_preview_token(NativeListingId("NL-NOOFFER"), secret=_SECRET)
    response = client.get(f"/api/_preview/listings/{minted.token}")
    assert response.status_code == 404
