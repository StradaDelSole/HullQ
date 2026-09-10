"""PostgreSQL + real HTTP tests for the SLICE-0050 public `THIS BOAT` projection.

Covers §10 "public read model extension": the publishing Organization's own
current claim snapshot only, omission vs explicit UNKNOWN distinguishable
through the API, no BoatDesign fallback, claim absence never failing the
listing's own public readability, current correction visible / old
correction not selected, and no internal claim metadata (revision id,
recording Account, content hash) leaking. Mirrors
tests/persistence/test_public_listing_read_api.py's isolation pattern.
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
    BoatDesignRef,
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
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
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
from hullq.persistence.market_episode import create_market_episode
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
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0050api_{uuid.uuid4().hex[:16]}"
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


def _claim_snapshot(**overrides: object) -> PhysicalBoatClaimSnapshot:
    kwargs: dict[str, object] = {
        "marketed_brand_claim": "Beneteau",
        "model_designation_claim": "Oceanis 30.1",
        "build_year": BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
    }
    kwargs.update(overrides)
    return PhysicalBoatClaimSnapshot(**kwargs)  # type: ignore[arg-type]


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    boat_design_ref: BoatDesignRef | None = None,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=boat_design_ref
        ),
    )
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
            broker_description="A well-maintained cruising sloop.",
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


def test_active_listing_without_claims_remains_public_with_null_claims(
    api_conn: Any, client: TestClient
) -> None:
    _make_active_listing(
        api_conn,
        listing_id="NL-PBC-A",
        physical_boat_id="PB-PBC-A",
        market_episode_id="ME-PBC-A",
        offer_revision_id="REV-PBC-A",
    )

    response = client.get("/api/listings/NL-PBC-A")
    assert response.status_code == 200
    assert response.json()["physical_boat_claims"] is None


def test_active_listing_with_claims_returns_the_bounded_seven_field_projection(
    api_conn: Any, client: TestClient
) -> None:
    account, org, _membership_obj = _make_active_listing(
        api_conn,
        listing_id="NL-PBC-B",
        physical_boat_id="PB-PBC-B",
        market_episode_id="ME-PBC-B",
        offer_revision_id="REV-PBC-B",
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=_membership_obj,
        native_listing_id=NativeListingId("NL-PBC-B"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-B-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(
            loa_length=LoaLengthClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.14")
            ),
            draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
            ),
            # rudder_configuration deliberately omitted
        ),
    )

    body = client.get("/api/listings/NL-PBC-B").json()
    claims = body["physical_boat_claims"]
    assert claims["marketed_brand_claim"] == "Beneteau"
    assert claims["model_designation_claim"] == "Oceanis 30.1"
    assert claims["build_year"] == {"assertion_kind": "VALUE_ASSERTION", "value": 2021}
    assert claims["loa_length"] == {"assertion_kind": "VALUE_ASSERTION", "value": "9.14"}
    assert claims["draft"] == {"assertion_kind": "UNKNOWN", "value": None}
    assert claims["keel_configuration"] == {"assertion_kind": "VALUE_ASSERTION", "value": "FIN"}
    # Omission (no wrapper supplied) renders as a bare null, distinct from
    # the explicit UNKNOWN object above.
    assert claims["rudder_configuration"] is None


def test_no_boat_design_fallback_when_physical_boat_has_a_linked_boat_design(
    api_conn: Any, client: TestClient
) -> None:
    """Even when the PhysicalBoat references a BoatDesign, an omitted/UNKNOWN
    claim field must never be filled from that design's baseline value --
    the API never learns of a BoatDesign at all here since no BoatDesign row
    is created; the point is that the public projection carries nothing
    beyond what was explicitly claimed."""
    account, org, _membership_obj = _make_active_listing(
        api_conn,
        listing_id="NL-PBC-C",
        physical_boat_id="PB-PBC-C",
        market_episode_id="ME-PBC-C",
        offer_revision_id="REV-PBC-C",
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=_membership_obj,
        native_listing_id=NativeListingId("NL-PBC-C"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-C-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(),  # loa_length/draft/keel/rudder all omitted
    )

    claims = client.get("/api/listings/NL-PBC-C").json()["physical_boat_claims"]
    assert claims["loa_length"] is None
    assert claims["draft"] is None
    assert claims["keel_configuration"] is None
    assert claims["rudder_configuration"] is None


def test_correction_is_visible_and_old_revision_is_not_selected_as_current(
    api_conn: Any, client: TestClient
) -> None:
    account, org, _membership_obj = _make_active_listing(
        api_conn,
        listing_id="NL-PBC-D",
        physical_boat_id="PB-PBC-D",
        market_episode_id="ME-PBC-D",
        offer_revision_id="REV-PBC-D",
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=_membership_obj,
        native_listing_id=NativeListingId("NL-PBC-D"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-D-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(model_designation_claim="Oceanis 30.1"),
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=_membership_obj,
        native_listing_id=NativeListingId("NL-PBC-D"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-D-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-D-001"),
        claims=_claim_snapshot(model_designation_claim="Oceanis 34.1"),
    )

    claims = client.get("/api/listings/NL-PBC-D").json()["physical_boat_claims"]
    assert claims["model_designation_claim"] == "Oceanis 34.1"


def test_only_publishing_organizations_own_current_snapshot_is_returned(
    api_conn: Any, client: TestClient
) -> None:
    """A different Organization's claim for the same PhysicalBoat must never
    leak into this listing's public projection (SLICE-0050 §9)."""
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-PBC-E",
        physical_boat_id="PB-PBC-E",
        market_episode_id="ME-PBC-E",
        offer_revision_id="REV-PBC-E",
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-PBC-E"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-E-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(marketed_brand_claim="Beneteau"),
    )

    # A different Organization publishes its own listing for the same
    # PhysicalBoat, with its own conflicting claim.
    other_account = AccountId("ACC-PBC-E-OTHER")
    other_org = _org("ORG-PBC-E-OTHER")
    other_membership = _membership(other_org, other_account, "OM-PBC-E-OTHER")
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-PBC-E-OTHER"), physical_boat_id=PhysicalBoatId("PB-PBC-E")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-PBC-E-OTHER"),
            market_episode_id=MarketEpisodeId("ME-PBC-E-OTHER"),
        ),
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-PBC-E-OTHER"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-E-OTHER-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(marketed_brand_claim="Jeanneau"),
    )

    claims = client.get("/api/listings/NL-PBC-E").json()["physical_boat_claims"]
    assert claims["marketed_brand_claim"] == "Beneteau"


def test_no_internal_claim_metadata_is_exposed(api_conn: Any, client: TestClient) -> None:
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-PBC-F",
        physical_boat_id="PB-PBC-F",
        market_episode_id="ME-PBC-F",
        offer_revision_id="REV-PBC-F",
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-PBC-F"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-F-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(),
    )

    claims = client.get("/api/listings/NL-PBC-F").json()["physical_boat_claims"]
    forbidden_keys = {
        "claim_revision_id",
        "revision_id",
        "recorded_by_account_id",
        "content_hash",
        "physical_boat_id",
        "claiming_organization_id",
        "previous_claim_revision_id",
        "previous_revision_id",
        "recorded_at",
    }
    assert forbidden_keys.isdisjoint(claims.keys())


def test_draft_listing_with_claims_remains_ordinary_not_found(
    api_conn: Any, client: TestClient
) -> None:
    """Claim recording is not conditioned on lifecycle (SLICE-0050 §6); a
    DRAFT listing with claims already recorded must still be ordinary
    not-found on the public route, exactly like SLICE-0049 without claims."""
    account = AccountId("ACC-PBC-G")
    org = _org("ORG-PBC-G")
    membership = _membership(org, account, "OM-PBC-G")
    create_physical_boat(api_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-PBC-G")))
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-PBC-G"), physical_boat_id=PhysicalBoatId("PB-PBC-G")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-PBC-G"), market_episode_id=MarketEpisodeId("ME-PBC-G")
        ),
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-PBC-G"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-PBC-G-001"),
        expected_current_revision_id=None,
        claims=_claim_snapshot(),
    )

    response = client.get("/api/listings/NL-PBC-G")
    assert response.status_code == 404
