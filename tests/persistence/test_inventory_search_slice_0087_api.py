"""PostgreSQL + real HTTP tests for the SLICE-0087 `beam_min`/`beam_max`/
`hull_material` extension of the `/api/search/{locale}` HTTP contract.

Mirrors `tests/persistence/test_inventory_search_slice_0086_api.py`'s HTTP
contract coverage (200 result, 308 canonical redirect, 400 invalid) for the
two new facets, alone and combined with all nine previously accepted
criteria together.
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
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BeamClaim,
    BuildYearClaim,
    CockpitPosition,
    CockpitPositionClaim,
    DeckSaloon,
    DeckSaloonClaim,
    DraftClaim,
    HullConfiguration,
    HullConfigurationClaim,
    HullMaterial,
    HullMaterialClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    RudderConfiguration,
    RudderConfigurationClaim,
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
from hullq.search.beam_design_bridge import BEAM_FIELD_POINTER, lookup_beam_canonical_value
from hullq.search.cockpit_design_bridge import lookup_cockpit_position_canonical_value
from hullq.search.deck_saloon_design_bridge import lookup_deck_saloon_canonical_value
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.hull_design_bridge import lookup_hull_configuration_canonical_value
from hullq.search.hull_material_design_bridge import (
    HULL_MATERIAL_FIELD_POINTER,
    lookup_hull_material_canonical_value,
)
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value
from hullq.search.loa_design_bridge import LOA_FIELD_POINTER, lookup_loa_canonical_value
from hullq.search.rudder_design_bridge import lookup_rudder_canonical_value

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
    schema_name = f"hullq_s0087api_{uuid.uuid4().hex[:16]}"
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

_DESIGN_ID = "BD-0087-MULTI-API"


def _insert_boat_design(conn: Any) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            ["BM-0087-MULTI-API", "Model BM-0087-MULTI-API", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "dimensions": {"draft_max_m": 1.30, "loa_m": 10.50, "beam_m": 3.80},
                "configuration": {"hull_configuration": "catamaran"},
                "appendages": {"keel_type": "fin", "rudder_support": "skeg"},
                "deck": {"cockpit_position": "center", "deck_saloon": "deck_saloon"},
                "construction": {"hull_material": "grp_fiberglass"},
            }
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [
                _DESIGN_ID,
                "BM-0087-MULTI-API",
                "{}",
                "[]",
                baseline_json,
                "[]",
                "[]",
                "{}",
                "1" * 64,
            ],
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
            broker_description="A well-maintained cruising catamaran.",
            asking_price_amount=Decimal("250000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-PLACEHOLDER-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Lagoon",
            model_designation_claim="42",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019),
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


@pytest.fixture()
def seeded(api_conn: Any) -> dict[str, Any]:
    """One CATAMARAN/CENTER-cockpit/DECK_SALOON, FIN-keeled/skeg-rudder,
    1.30 m-draft/10.50 m-LOA/3.80 m-beam/GRP_FIBERGLASS-hull design-eligible
    ACTIVE listing whose own concrete PhysicalBoat claims match every field,
    combining every originally accepted criterion with both SLICE-0087
    facets."""
    _insert_boat_design(api_conn)
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value="fin",
        resolution_id="FR-0087-KEEL-API",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    admit_resolved_draft_max(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.30"),
        resolution_id="FR-0087-DRAFT-API",
    )
    admit_resolved_draft_max(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=LOA_FIELD_POINTER,
        value=Decimal("10.50"),
        resolution_id="FR-0087-LOA-API",
        fetch_canonical_value=lookup_loa_canonical_value,
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer="/baseline/appendages/rudder_support",
        value="skeg",
        resolution_id="FR-0087-RUDDER-API",
        fetch_canonical_value=lookup_rudder_canonical_value,
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer="/baseline/configuration/hull_configuration",
        value="catamaran",
        resolution_id="FR-0087-HULLCFG-API",
        fetch_canonical_value=lookup_hull_configuration_canonical_value,
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer="/baseline/deck/cockpit_position",
        value="center",
        resolution_id="FR-0087-COCKPITPOS-API",
        fetch_canonical_value=lookup_cockpit_position_canonical_value,
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer="/baseline/deck/deck_saloon",
        value="deck_saloon",
        resolution_id="FR-0087-DECKSALOON-API",
        fetch_canonical_value=lookup_deck_saloon_canonical_value,
    )
    admit_resolved_draft_max(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=BEAM_FIELD_POINTER,
        value=Decimal("3.80"),
        resolution_id="FR-0087-BEAM-API",
        fetch_canonical_value=lookup_beam_canonical_value,
    )
    admit_resolved_categorical_field(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=HULL_MATERIAL_FIELD_POINTER,
        value="grp_fiberglass",
        resolution_id="FR-0087-HULLMAT-API",
        fetch_canonical_value=lookup_hull_material_canonical_value,
    )

    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-0087-MULTI-API",
        physical_boat_id="PB-0087-MULTI-API",
        market_episode_id="ME-0087-MULTI-API",
    )
    result = write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0087-MULTI-API"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-0087-MULTI-API"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId(
            "PBCREV-PLACEHOLDER-NL-0087-MULTI-API"
        ),
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Lagoon",
            model_designation_claim="42",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019),
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.30")),
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
            ),
            loa_length=LoaLengthClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("10.50")
            ),
            rudder_configuration=RudderConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration.SKEG_HUNG
            ),
            hull_configuration=HullConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullConfiguration.CATAMARAN
            ),
            cockpit_position=CockpitPositionClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=CockpitPosition.CENTER
            ),
            deck_saloon=DeckSaloonClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=DeckSaloon.DECK_SALOON
            ),
            beam=BeamClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("3.80")),
            hull_material=HullMaterialClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullMaterial.GRP_FIBERGLASS
            ),
        ),
    )
    assert result.status.value in ("created", "revised"), result
    return {}


# ---------------------------------------------------------------------------
# HTTP contract tests
# ---------------------------------------------------------------------------


def test_beam_range_only_result_200(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get("/api/search/en?beam_max=4.4&beam_min=3.2")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {"beam_max": "4.4", "beam_min": "3.2"}
    assert body["confirmed_match_count"] == 1
    assert body["confirmed_matches"][0]["native_listing_id"] == "NL-0087-MULTI-API"


def test_hull_material_only_result_200(client: TestClient, seeded: dict[str, Any]) -> None:
    response = client.get("/api/search/en?hull_material=GRP_FIBERGLASS")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {"hull_material": "GRP_FIBERGLASS"}
    assert body["confirmed_match_count"] == 1


def test_hull_material_wrong_value_200_with_zero_matches(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """The real concrete/design truth is GRP_FIBERGLASS, never STEEL --
    never merged or treated as entailing one another."""
    response = client.get("/api/search/en?hull_material=STEEL")
    assert response.status_code == 200
    body = response.json()
    assert body["confirmed_match_count"] == 0


def test_all_eleven_criteria_combined_result_200(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get(
        "/api/search/en"
        "?beam_max=4.4&beam_min=3.2&cockpit_position=CENTER&deck_saloon=DECK_SALOON"
        "&draft_max=1.6&hull_configuration=CATAMARAN&hull_material=GRP_FIBERGLASS"
        "&keel_configuration=FIN&loa_max=11&loa_min=10&rudder_configuration=SKEG_HUNG"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {
        "beam_max": "4.4",
        "beam_min": "3.2",
        "cockpit_position": "CENTER",
        "deck_saloon": "DECK_SALOON",
        "draft_max": "1.6",
        "hull_configuration": "CATAMARAN",
        "hull_material": "GRP_FIBERGLASS",
        "keel_configuration": "FIN",
        "loa_max": "11",
        "loa_min": "10",
        "rudder_configuration": "SKEG_HUNG",
    }
    assert body["confirmed_match_count"] == 1
    fields = {ce["field"] for ce in body["confirmed_matches"][0]["criterion_evidence"]}
    assert fields == {
        "beam_m",
        "cockpit_position",
        "deck_saloon",
        "draft_max_m",
        "hull_configuration",
        "hull_material",
        "keel_configuration",
        "loa_m",
        "rudder_configuration",
    }


def test_invalid_hull_material_value_400(client: TestClient) -> None:
    # FERROCEMENT is a valid PhysicalBoat claim token but never an accepted
    # public Search value in this slice.
    response = client.get("/api/search/de?hull_material=FERROCEMENT", follow_redirects=False)
    assert response.status_code == 400


def test_invalid_beam_min_greater_than_max_400(client: TestClient) -> None:
    response = client.get("/api/search/de?beam_min=4.5&beam_max=3.2", follow_redirects=False)
    assert response.status_code == 400


def test_duplicate_identical_hull_material_308(client: TestClient) -> None:
    response = client.get(
        "/api/search/de?hull_material=WOOD&hull_material=WOOD", follow_redirects=False
    )
    assert response.status_code == 308
    assert response.headers["location"] == "/de/search?hull_material=WOOD"


def test_eleven_keys_out_of_order_308_to_canonical_order(client: TestClient) -> None:
    response = client.get(
        "/api/search/de"
        "?rudder_configuration=SKEG_HUNG&loa_min=10&loa_max=11&keel_configuration=FIN"
        "&hull_material=WOOD&draft_max=1.6&hull_configuration=CATAMARAN"
        "&cockpit_position=CENTER&deck_saloon=DECK_SALOON&beam_min=3.2&beam_max=4.4",
        follow_redirects=False,
    )
    assert response.status_code == 308
    assert response.headers["location"] == (
        "/de/search?beam_max=4.4&beam_min=3.2&cockpit_position=CENTER&deck_saloon=DECK_SALOON"
        "&draft_max=1.6&hull_configuration=CATAMARAN&hull_material=WOOD&keel_configuration=FIN"
        "&loa_max=11&loa_min=10&rudder_configuration=SKEG_HUNG"
    )
