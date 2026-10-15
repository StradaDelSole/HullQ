"""PostgreSQL-backed end-to-end tests for the SLICE-0086 hull_configuration/
cockpit_position/deck_saloon extension of the mixed native inventory Search
funnel (`hullq.application.native_inventory_query`).

Mirrors `tests/persistence/test_native_inventory_query_multicriteria.py`'s
end-to-end shape (real FieldResolution-admitted design eligibility -> ACTIVE
native inventory admission -> concrete PhysicalBoat claim classification),
exercising: all three new facets combined on one confirmed listing (proving
there is no arbitrary CENTER+DECK_SALOON rejection), a new facet mixed with
an originally accepted criterion (keel_configuration), and the same-boat
cross-Organization contradiction guard for a new concrete claim field.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.native_inventory_query import evaluate_native_inventory_requirements
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
    BuildYearClaim,
    CockpitPosition,
    CockpitPositionClaim,
    DeckSaloon,
    DeckSaloonClaim,
    HullConfiguration,
    HullConfigurationClaim,
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
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.market_episode import create_market_episode, fetch_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing, fetch_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)
from hullq.search.cockpit_design_bridge import lookup_cockpit_position_canonical_value
from hullq.search.deck_saloon_design_bridge import lookup_deck_saloon_canonical_value
from hullq.search.hull_design_bridge import lookup_hull_configuration_canonical_value
from hullq.search.keel_design_bridge import lookup_keel_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_native_inventory_query_multicriteria.py)
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
    schema_name = f"hullq_s0086niq_{uuid.uuid4().hex[:16]}"
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


def _as_of() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Domain/fixture helpers
# ---------------------------------------------------------------------------


def _insert_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    keel_type: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "configuration": {"hull_configuration": hull_configuration},
                "appendages": {"keel_type": keel_type},
                "deck": {"cockpit_position": cockpit_position, "deck_saloon": deck_saloon},
            }
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


def _admit_design_hull_configuration(conn: Any, design_id: str, *, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/configuration/hull_configuration",
        value=value,
        resolution_id=f"FR-HULLCFG-{design_id}",
        fetch_canonical_value=lookup_hull_configuration_canonical_value,
    )


def _admit_design_cockpit_position(conn: Any, design_id: str, *, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/deck/cockpit_position",
        value=value,
        resolution_id=f"FR-COCKPITPOS-{design_id}",
        fetch_canonical_value=lookup_cockpit_position_canonical_value,
    )


def _admit_design_deck_saloon(conn: Any, design_id: str, *, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/deck/deck_saloon",
        value=value,
        resolution_id=f"FR-DECKSALOON-{design_id}",
        fetch_canonical_value=lookup_deck_saloon_canonical_value,
    )


def _admit_design_keel_type(conn: Any, design_id: str, *, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/keel_type",
        value=value,
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )


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


def _current_claim_revision_id(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization
) -> PhysicalBoatClaimRevisionId | None:
    listing_record = fetch_native_listing(conn, NativeListingId(listing_id))
    assert listing_record is not None
    assert listing_record.listing.market_episode_id is not None
    episode_record = fetch_market_episode(conn, listing_record.listing.market_episode_id)
    assert episode_record is not None
    claim_record = fetch_current_physical_boat_claim(
        conn, episode_record.market_episode.physical_boat_id, org.id
    )
    return claim_record.revision_id if claim_record is not None else None


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(boat_design_id)
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


def _write_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    keel_configuration: KeelConfigurationClaim | None = None,
    hull_configuration: HullConfigurationClaim | None = None,
    cockpit_position: CockpitPositionClaim | None = None,
    deck_saloon: DeckSaloonClaim | None = None,
) -> None:
    expected_current_revision_id = _current_claim_revision_id(conn, listing_id=listing_id, org=org)
    conn.commit()
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(revision_id),
        expected_current_revision_id=expected_current_revision_id,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Lagoon",
            model_designation_claim="42",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019),
            keel_configuration=keel_configuration,
            hull_configuration=hull_configuration,
            cockpit_position=cockpit_position,
            deck_saloon=deck_saloon,
        ),
    )
    assert result.status.value in ("created", "revised"), result


# ---------------------------------------------------------------------------
# All three new facets combined -- no arbitrary CENTER+DECK_SALOON rejection
# ---------------------------------------------------------------------------


def test_hull_cockpit_deck_saloon_combined_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn,
        "BD-S86-1",
        "BM-S86-1",
        hull_configuration="catamaran",
        cockpit_position="center",
        deck_saloon="deck_saloon",
    )
    _admit_design_hull_configuration(api_conn, "BD-S86-1", value="catamaran")
    _admit_design_cockpit_position(api_conn, "BD-S86-1", value="center")
    _admit_design_deck_saloon(api_conn, "BD-S86-1", value="deck_saloon")
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-S86-1",
        physical_boat_id="PB-S86-1",
        market_episode_id="ME-S86-1",
        boat_design_id="BD-S86-1",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-S86-1",
        revision_id="REV-S86-1",
        hull_configuration=HullConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullConfiguration.CATAMARAN
        ),
        cockpit_position=CockpitPositionClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=CockpitPosition.CENTER
        ),
        deck_saloon=DeckSaloonClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=DeckSaloon.DECK_SALOON
        ),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=None,
        keel_configuration=None,
        hull_configuration="CATAMARAN",
        cockpit_position="CENTER",
        deck_saloon="DECK_SALOON",
        as_of=_as_of(),
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-S86-1"}


# ---------------------------------------------------------------------------
# A new facet mixed with an originally accepted criterion
# ---------------------------------------------------------------------------


def test_hull_configuration_mixed_with_keel_configuration(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn, "BD-S86-2", "BM-S86-2", keel_type="fin", hull_configuration="monohull"
    )
    _admit_design_keel_type(api_conn, "BD-S86-2", value="fin")
    _admit_design_hull_configuration(api_conn, "BD-S86-2", value="monohull")
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-S86-2",
        physical_boat_id="PB-S86-2",
        market_episode_id="ME-S86-2",
        boat_design_id="BD-S86-2",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-S86-2",
        revision_id="REV-S86-2",
        keel_configuration=KeelConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
        ),
        hull_configuration=HullConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullConfiguration.MONOHULL
        ),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=None,
        keel_configuration="FIN",
        hull_configuration="MONOHULL",
        as_of=_as_of(),
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-S86-2"}

    # The design/concrete truth is MONOHULL, never CATAMARAN -- a mixed
    # query asking for the wrong hull form on the same keel must not match.
    non_match_outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=None,
        keel_configuration="FIN",
        hull_configuration="CATAMARAN",
        as_of=_as_of(),
    )
    assert non_match_outcome.confirmed_matches == ()


# ---------------------------------------------------------------------------
# Same-PhysicalBoat cross-Organization contradiction guard
# ---------------------------------------------------------------------------


def test_cockpit_position_cross_organization_conflict_is_insufficient_data(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-S86-3", "BM-S86-3", cockpit_position="aft")
    _admit_design_cockpit_position(api_conn, "BD-S86-3", value="aft")
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-S86-3",
        physical_boat_id="PB-S86-3",
        market_episode_id="ME-S86-3",
        boat_design_id="BD-S86-3",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-S86-3",
        revision_id="REV-S86-3A",
        cockpit_position=CockpitPositionClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=CockpitPosition.AFT
        ),
    )

    # A second Organization, publishing a SECOND NativeListing/MarketEpisode
    # against the SAME PhysicalBoatId, claims a materially different
    # cockpit_position -- the same-boat cross-Organization contradiction
    # guard must downgrade the publisher's own otherwise-confirmed value to
    # MISSING, never silently trusting the publisher alone.
    other_account = AccountId("ACC-S86-3-OTHER")
    other_org = _org("ORG-S86-3-OTHER")
    other_membership = _membership(other_org, other_account, "OM-S86-3-OTHER")
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-S86-3-OTHER"), physical_boat_id=PhysicalBoatId("PB-S86-3")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-S86-3-OTHER"),
            market_episode_id=MarketEpisodeId("ME-S86-3-OTHER"),
        ),
    )
    conn_result = write_physical_boat_claim_revision(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-S86-3-OTHER"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-S86-3-OTHER"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Lagoon",
            model_designation_claim="42",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2019),
            cockpit_position=CockpitPositionClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=CockpitPosition.FORWARD
            ),
        ),
    )
    assert conn_result.status.value == "created", conn_result

    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration=None, cockpit_position="AFT", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert {m.native_listing_id.value for m in outcome.insufficient_data} == {"NL-S86-3"}
