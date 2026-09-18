"""PostgreSQL + real HTTP tests for the SLICE-0055 `keel_configuration`
criterion #2 `/api/search/{locale}` HTTP contract.

Mirrors `tests/persistence/test_inventory_search_draft_max_api.py`'s HTTP
contract coverage (200 result, 308 canonical redirect, 400 invalid) for the
new `keel_configuration` query parameter, alone and combined with the
existing `draft_max`.
"""

from __future__ import annotations

import json
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
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.provenance import SubjectKind
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
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

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
    schema_name = f"hullq_s0055api_{uuid.uuid4().hex[:16]}"
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
# Domain/fixture helpers
# ---------------------------------------------------------------------------

_DESIGN_ID = "BD-0055-KEEL-API"


def _insert_boat_design(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            ["BM-0055-KEEL-API", "Model BM-0055-KEEL-API", "0" * 64],
        )
        baseline_json = json.dumps(
            {"dimensions": {"draft_max_m": 1.30}, "appendages": {"keel_type": "fin"}}
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [_DESIGN_ID, "BM-0055-KEEL-API", "{}", "[]", baseline_json, "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


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
    conn: Any, *, listing_id: str, physical_boat_id: str, market_episode_id: str
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(_DESIGN_ID)
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
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership


@pytest.fixture()
def seeded(api_conn: Any) -> dict[str, Any]:
    """One FIN-keeled, 1.30 m-draft design-eligible ACTIVE listing whose own
    concrete PhysicalBoat claims keel_configuration=FIN and draft=1.40."""
    _insert_boat_design(api_conn)
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="fin",
        resolution_id="FR-0055-KEEL-API",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    admit_resolved_draft_max(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.30"),
        resolution_id="FR-0055-DRAFT-API",
    )

    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-0055-KEEL-API",
        physical_boat_id="PB-0055-KEEL-API",
        market_episode_id="ME-0055-KEEL-API",
    )
    result = write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0055-KEEL-API"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-0055-KEEL-API"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
            ),
        ),
    )
    assert result.status.value in ("created", "revised"), result
    return {}


# ---------------------------------------------------------------------------
# HTTP contract tests
# ---------------------------------------------------------------------------


def test_keel_only_result_200(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get("/api/search/en?keel_configuration=FIN")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {"keel_configuration": "FIN"}
    assert body["confirmed_match_count"] == 1
    match = body["confirmed_matches"][0]
    assert match["native_listing_id"] == "NL-0055-KEEL-API"
    assert match["design_evaluation"]["result_class"] == "CONFIRMED_MATCH"
    assert match["design_evaluation"]["matching_configuration_ids"] == [
        "BD-0055-KEEL-API::baseline"
    ]
    assert match["criterion_evidence"][0]["field"] == "keel_configuration"
    assert match["criterion_evidence"][0]["observed_value"] == "FIN"


def test_mixed_draft_and_keel_result_200(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get("/api/search/en?draft_max=1.6&keel_configuration=FIN")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {"draft_max": "1.6", "keel_configuration": "FIN"}
    assert body["confirmed_match_count"] == 1
    fields = {ce["field"] for ce in body["confirmed_matches"][0]["criterion_evidence"]}
    assert fields == {"draft_max_m", "keel_configuration"}


def test_keel_only_non_matching_value_is_200_with_zero_matches(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get("/api/search/en?keel_configuration=WING")
    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_match_count"] == 0
    assert body["confirmed_matches"] == []


def test_invalid_keel_configuration_value_400(client: TestClient) -> None:
    response = client.get("/api/search/de?keel_configuration=LONG_KEEL", follow_redirects=False)
    assert response.status_code == 400


def test_conflicting_keel_configuration_duplicates_400(client: TestClient) -> None:
    response = client.get(
        "/api/search/de?keel_configuration=FIN&keel_configuration=WING", follow_redirects=False
    )
    assert response.status_code == 400


def test_duplicate_equal_keel_configuration_308(client: TestClient) -> None:
    response = client.get(
        "/api/search/de?keel_configuration=FIN&keel_configuration=FIN", follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"] == "/de/search?keel_configuration=FIN"


def test_mixed_noncanonical_draft_308_preserves_keel(client: TestClient) -> None:
    response = client.get(
        "/api/search/de?draft_max=1.600&keel_configuration=FIN", follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"] == "/de/search?draft_max=1.6&keel_configuration=FIN"


def test_keel_search_response_is_noindex(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get("/api/search/en?keel_configuration=FIN")
    assert response.headers.get("x-robots-tag") == "noindex"
