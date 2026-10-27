"""PostgreSQL-backed integration tests for the design-unresolved claim-only
Sail candidate path -- SLICE-0092.

Covers the exact SLICE-0090 hard-case corpus scenarios this slice's
Deliverables name (`docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`):

- FIX-0090-08 (design-unresolved but typed, issuer-owned current claim):
  a `PhysicalBoat.boat_design_ref IS NULL` listing with a complete,
  publisher-owned, explicit SAIL claim set becomes a `CONFIRMED_MATCH`
  through the new claim-only path, with `source_basis=PUBLISHER_CLAIM`,
  through both the pure `draft_max` and mixed nine-criterion entrypoints.
- FIX-0090-09 / FIX-0090-13 (retraction/current-snapshot authority): the
  current claim-revision snapshot is re-derived on every evaluation; a
  retraction after an earlier confirmed match is reflected immediately.
- FIX-0090-11 (unknown category / category conflict): a missing/UNKNOWN
  category, or a cross-Organization category conflict, is excluded from a
  confirmed claim-only Sail match -- never resolved toward SAIL.
- Contract §A publisher-ownership rule: a SAIL claim asserted only by a
  *different* Organization than the listing's own publisher never admits
  the listing -- "Another Organization's category assertion cannot lend
  the publisher its Sail eligibility."
- Regression boundary (FIX-0090-08's "existing design-linked path must
  remain completely unaffected"): a design-linked confirmed match coexisting
  with a claim-only candidate is unaffected by the new path.

Mirrors `tests/persistence/test_native_inventory_query_vessel_category_slice_0091.py`'s
disposable-schema/fixture pattern; deliberately duplicates the minimal
seeding boilerplate rather than cross-importing between test modules
(established repo convention).
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
from fastapi.testclient import TestClient

from hullq.application.inventory_search import evaluate_draft_max_requirement
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
    VesselCategory,
    VesselCategoryClaim,
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
from hullq.domain.vessel_category import VesselCategoryResolution, VesselCategoryResolutionReason
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
    write_physical_boat_claim_revision_row,
)
from hullq.search.keel_design_bridge import lookup_keel_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field

VA = AssertionKind.VALUE_ASSERTION
UNK = AssertionKind.UNKNOWN


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
def claim_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0092co_{uuid.uuid4().hex[:16]}"
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
def claim_conn(claim_url: str) -> Generator[Any]:
    conn = psycopg.connect(claim_url)
    try:
        yield conn
    finally:
        conn.close()


_SECRET = b"0" * 32


@pytest.fixture()
def client(claim_url: str) -> TestClient:
    from hullq.api.app import create_app

    app = create_app(database_url=claim_url, preview_signing_secret=_SECRET)
    return TestClient(app)


def _as_of() -> datetime:
    return datetime.now(UTC)


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


def _make_design_unresolved_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    draft: Decimal | None = None,
    keel_configuration: KeelConfiguration | None = None,
    vessel_category: VesselCategoryClaim | None = None,
    loa_length: Decimal | None = None,
    rudder_configuration: RudderConfiguration | None = None,
    hull_configuration: HullConfiguration | None = None,
    cockpit_position: CockpitPosition | None = None,
    deck_saloon: DeckSaloon | None = None,
    beam: Decimal | None = None,
    hull_material: HullMaterial | None = None,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    """SLICE-0092: a published, ACTIVE, D29-eligible NativeListing whose
    PhysicalBoat carries NO `boat_design_ref` at all -- the exact new
    candidate shape `list_active_design_unresolved_listings` enumerates.
    """
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id), boat_design_ref=None)
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
            broker_description="A well-maintained cruising boat with no matched design record.",
            asking_price_amount=Decimal("95000.00"),
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
            model_designation_claim="Unmatched Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            draft=DraftClaim(assertion_kind=VA, value=draft) if draft is not None else None,
            keel_configuration=(
                KeelConfigurationClaim(assertion_kind=VA, value=keel_configuration)
                if keel_configuration is not None
                else None
            ),
            vessel_category=vessel_category,
            loa_length=(
                LoaLengthClaim(assertion_kind=VA, value=loa_length)
                if loa_length is not None
                else None
            ),
            rudder_configuration=(
                RudderConfigurationClaim(assertion_kind=VA, value=rudder_configuration)
                if rudder_configuration is not None
                else None
            ),
            hull_configuration=(
                HullConfigurationClaim(assertion_kind=VA, value=hull_configuration)
                if hull_configuration is not None
                else None
            ),
            cockpit_position=(
                CockpitPositionClaim(assertion_kind=VA, value=cockpit_position)
                if cockpit_position is not None
                else None
            ),
            deck_saloon=(
                DeckSaloonClaim(assertion_kind=VA, value=deck_saloon)
                if deck_saloon is not None
                else None
            ),
            beam=BeamClaim(assertion_kind=VA, value=beam) if beam is not None else None,
            hull_material=(
                HullMaterialClaim(assertion_kind=VA, value=hull_material)
                if hull_material is not None
                else None
            ),
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


def _revise_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    draft: Decimal | None = None,
    keel_configuration: KeelConfiguration | None = None,
    vessel_category: VesselCategoryClaim | None = None,
    loa_length: Decimal | None = None,
    rudder_configuration: RudderConfiguration | None = None,
    hull_configuration: HullConfiguration | None = None,
    cockpit_position: CockpitPosition | None = None,
    deck_saloon: DeckSaloon | None = None,
    beam: Decimal | None = None,
    hull_material: HullMaterial | None = None,
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
            marketed_brand_claim="Unbranded",
            model_designation_claim="Unmatched Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            draft=DraftClaim(assertion_kind=VA, value=draft) if draft is not None else None,
            keel_configuration=(
                KeelConfigurationClaim(assertion_kind=VA, value=keel_configuration)
                if keel_configuration is not None
                else None
            ),
            vessel_category=vessel_category,
            loa_length=(
                LoaLengthClaim(assertion_kind=VA, value=loa_length)
                if loa_length is not None
                else None
            ),
            rudder_configuration=(
                RudderConfigurationClaim(assertion_kind=VA, value=rudder_configuration)
                if rudder_configuration is not None
                else None
            ),
            hull_configuration=(
                HullConfigurationClaim(assertion_kind=VA, value=hull_configuration)
                if hull_configuration is not None
                else None
            ),
            cockpit_position=(
                CockpitPositionClaim(assertion_kind=VA, value=cockpit_position)
                if cockpit_position is not None
                else None
            ),
            deck_saloon=(
                DeckSaloonClaim(assertion_kind=VA, value=deck_saloon)
                if deck_saloon is not None
                else None
            ),
            beam=BeamClaim(assertion_kind=VA, value=beam) if beam is not None else None,
            hull_material=(
                HullMaterialClaim(assertion_kind=VA, value=hull_material)
                if hull_material is not None
                else None
            ),
        ),
    )
    assert result.status.value in ("created", "revised"), result
    conn.commit()


# ---------------------------------------------------------------------------
# FIX-0090-08: design-unresolved, publisher-owned SAIL, complete claims
# ---------------------------------------------------------------------------


def test_design_unresolved_sail_claim_confirms_via_mixed_keel_criterion(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-MIX",
        physical_boat_id="PB-92-MIX",
        market_episode_id="ME-92-MIX",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()  # design-linked surface untouched
    claim_match_ids = {m.native_listing_id.value for m in outcome.claim_only_matches}
    assert claim_match_ids == {"NL-92-MIX"}
    match = outcome.claim_only_matches[0]
    assert match.vessel_category_exclusion is None
    keel_evidence = next(
        e for e in match.criterion_evidence if e.criterion.field == "keel_configuration"
    )
    assert keel_evidence.observed_value == "FIN"


def test_design_unresolved_sail_claim_confirms_via_pure_draft_max(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-DRAFT",
        physical_boat_id="PB-92-DRAFT",
        market_episode_id="ME-92-DRAFT",
        draft=Decimal("1.40"),
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome = evaluate_draft_max_requirement(claim_conn, Decimal("1.6"), as_of=_as_of())
    assert outcome.confirmed_matches == ()  # design-linked surface untouched
    claim_match_ids = {m.native_listing_id.value for m in outcome.claim_only_matches}
    assert claim_match_ids == {"NL-92-DRAFT"}


def test_design_unresolved_sail_claim_api_serialization(
    claim_conn: Any, client: TestClient
) -> None:
    """The public FastAPI route returns the new claim-only candidate with
    `source_basis=PUBLISHER_CLAIM` and no `design_evaluation` key -- the
    exact public-surface proof the slice's VISIBLE-RESULT CHECK requires.
    """
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-API",
        physical_boat_id="PB-92-API",
        market_episode_id="ME-92-API",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    response = client.get("/api/search/en", params={"keel_configuration": "FIN"})
    assert response.status_code == 200
    body = response.json()
    publisher_matches = body["publisher_claim_matches"]
    assert len(publisher_matches) == 1
    match = publisher_matches[0]
    assert match["native_listing_id"] == "NL-92-API"
    assert match["source_basis"] == "PUBLISHER_CLAIM"
    assert "design_evaluation" not in match
    assert "design_configuration_evidence" not in match
    assert body["publisher_claim_match_count"] == 1
    # The confirmed-match (design-linked) surface is completely unaffected.
    assert body["confirmed_matches"] == []
    assert body["confirmed_match_count"] == 0


# ---------------------------------------------------------------------------
# FIX-0090-11a: no category claim at all -> insufficient, never confirmed
# ---------------------------------------------------------------------------


def test_design_unresolved_missing_category_is_insufficient_never_confirmed(
    claim_conn: Any,
) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-UNK",
        physical_boat_id="PB-92-UNK",
        market_episode_id="ME-92-UNK",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=None,
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.claim_only_matches == ()
    insufficient_ids = {m.native_listing_id.value for m in outcome.claim_only_insufficient_data}
    assert insufficient_ids == {"NL-92-UNK"}
    entry = outcome.claim_only_insufficient_data[0]
    assert entry.vessel_category_exclusion is None
    assert entry.criterion_evidence == ()


def test_design_unresolved_explicit_unknown_category_is_insufficient(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-EXPUNK",
        physical_boat_id="PB-92-EXPUNK",
        market_episode_id="ME-92-EXPUNK",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=UNK, value=None),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.claim_only_matches == ()
    assert {m.native_listing_id.value for m in outcome.claim_only_insufficient_data} == {
        "NL-92-EXPUNK"
    }


# ---------------------------------------------------------------------------
# FIX-0090-11b analog + contract §A: explicit POWER excludes outright
# ---------------------------------------------------------------------------


def test_design_unresolved_power_category_is_confirmed_non_match(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-PWR",
        physical_boat_id="PB-92-PWR",
        market_episode_id="ME-92-PWR",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.claim_only_matches == ()
    non_match = next(
        m for m in outcome.claim_only_non_matches if m.native_listing_id.value == "NL-92-PWR"
    )
    assert non_match.vessel_category_exclusion is not None
    assert non_match.vessel_category_exclusion.resolution is VesselCategoryResolution.POWER


# ---------------------------------------------------------------------------
# Contract §A: a DIFFERENT Organization's SAIL claim never lends eligibility
# ---------------------------------------------------------------------------


def test_design_unresolved_other_organization_sail_claim_not_enough(claim_conn: Any) -> None:
    """The publishing Organization itself has NO category claim at all; a
    second Organization (via a second NativeListing/MarketEpisode over the
    SAME PhysicalBoatId) asserts SAIL. The resolved overall category is SAIL
    (CONCRETE_ONLY), but the publisher never asserted it -- contract §A:
    "Another Organization's category assertion cannot lend the publisher
    its Sail eligibility." Must stay INSUFFICIENT_DATA, never CONFIRMED_MATCH.
    """
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-OTHERORG",
        physical_boat_id="PB-92-OTHERORG",
        market_episode_id="ME-92-OTHERORG",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=None,
    )

    other_account = AccountId("ACC-92-OTHERORG-2")
    other_org = _org("ORG-92-OTHERORG-2")
    other_membership = _membership(other_org, other_account, "OM-92-OTHERORG-2")
    create_market_episode(
        claim_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-92-OTHERORG-2"),
            physical_boat_id=PhysicalBoatId("PB-92-OTHERORG"),
        ),
    )
    create_native_listing(
        claim_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-92-OTHERORG-2"),
            market_episode_id=MarketEpisodeId("ME-92-OTHERORG-2"),
        ),
    )
    write_physical_boat_claim_revision(
        claim_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-92-OTHERORG-2"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-92-OTHERORG-2"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Other",
            model_designation_claim="Other Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        ),
    )
    claim_conn.commit()

    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.claim_only_matches == ()
    assert "NL-92-OTHERORG" in {
        m.native_listing_id.value for m in outcome.claim_only_insufficient_data
    }


def test_design_unresolved_cross_organization_category_conflict_excluded(claim_conn: Any) -> None:
    """Both Organizations assert a positive category for the same
    PhysicalBoatId, but disagree -> CONFLICT, never resolved toward either
    side (FIX-0090-11b analog, cross-Organization variant)."""
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-XCONF",
        physical_boat_id="PB-92-XCONF",
        market_episode_id="ME-92-XCONF",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )

    other_account = AccountId("ACC-92-XCONF-2")
    other_org = _org("ORG-92-XCONF-2")
    other_membership = _membership(other_org, other_account, "OM-92-XCONF-2")
    create_market_episode(
        claim_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-92-XCONF-2"), physical_boat_id=PhysicalBoatId("PB-92-XCONF")
        ),
    )
    create_native_listing(
        claim_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-92-XCONF-2"), market_episode_id=MarketEpisodeId("ME-92-XCONF-2")
        ),
    )
    write_physical_boat_claim_revision(
        claim_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-92-XCONF-2"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-92-XCONF-2"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Other",
            model_designation_claim="Other Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        ),
    )
    claim_conn.commit()

    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert outcome.claim_only_matches == ()
    non_match = next(
        m for m in outcome.claim_only_non_matches if m.native_listing_id.value == "NL-92-XCONF"
    )
    assert non_match.vessel_category_exclusion is not None
    assert non_match.vessel_category_exclusion.resolution is VesselCategoryResolution.CONFLICT
    assert (
        non_match.vessel_category_exclusion.reason
        is VesselCategoryResolutionReason.CROSS_ORGANIZATION_DISAGREEMENT
    )


# ---------------------------------------------------------------------------
# FIX-0090-09 / FIX-0090-13: current-snapshot authority, retraction
# ---------------------------------------------------------------------------


def test_design_unresolved_retraction_removes_confirmed_match(claim_conn: Any) -> None:
    account, org, membership = _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-RETR",
        physical_boat_id="PB-92-RETR",
        market_episode_id="ME-92-RETR",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome_before = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert {m.native_listing_id.value for m in outcome_before.claim_only_matches} == {"NL-92-RETR"}

    # Publisher retracts the qualifying keel claim to UNKNOWN without
    # changing lifecycle state -- mirrors FIX-0090-13's listing-level
    # retraction-after-publication invariant.
    _revise_claim(
        claim_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-92-RETR",
        revision_id="PBCREV-92-RETR-2",
        keel_configuration=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )

    outcome_after = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert "NL-92-RETR" not in {m.native_listing_id.value for m in outcome_after.claim_only_matches}
    assert "NL-92-RETR" in {
        m.native_listing_id.value for m in outcome_after.claim_only_insufficient_data
    }


# ---------------------------------------------------------------------------
# Regression boundary: design-linked results stay byte-for-byte unchanged
# ---------------------------------------------------------------------------


def test_design_linked_confirmed_match_unaffected_by_claim_only_candidate(
    claim_conn: Any,
) -> None:
    design_id = "BD-92-REG"
    model_id = "BM-92-REG"
    with claim_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"appendages": {"keel_type": "fin"}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    claim_conn.commit()

    admit_resolved_categorical_field(
        claim_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/keel_type",
        value="fin",
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )

    account = AccountId("ACC-92-REG-LINKED")
    org = _org("ORG-92-REG-LINKED")
    membership = _membership(org, account, "OM-92-REG-LINKED")
    create_physical_boat(
        claim_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-92-REG-LINKED"), boat_design_ref=BoatDesignRef(design_id)
        ),
    )
    create_market_episode(
        claim_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-92-REG-LINKED"),
            physical_boat_id=PhysicalBoatId("PB-92-REG-LINKED"),
        ),
    )
    create_native_listing(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-92-REG-LINKED"),
            market_episode_id=MarketEpisodeId("ME-92-REG-LINKED"),
        ),
    )
    write_native_listing_offer_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-92-REG-LINKED"),
        revision_id=NativeListingOfferRevisionId("REV-92-REG-LINKED"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising boat.",
            asking_price_amount=Decimal("180000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-92-REG-LINKED"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-92-REG-LINKED"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 40",
            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=VA, value=KeelConfiguration.FIN
            ),
        ),
    )
    _attach_ready_cover_image(claim_conn, listing_id="NL-92-REG-LINKED", org=org, account=account)
    publish_result = publish_native_listing(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-92-REG-LINKED"),
    )
    assert publish_result.status.value == "transitioned", publish_result

    # Coexisting claim-only candidate, also keel=FIN, also confirmed.
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-REG-CLAIMONLY",
        physical_boat_id="PB-92-REG-CLAIMONLY",
        market_episode_id="ME-92-REG-CLAIMONLY",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )

    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-92-REG-LINKED"}
    assert {m.native_listing_id.value for m in outcome.claim_only_matches} == {
        "NL-92-REG-CLAIMONLY"
    }


# ---------------------------------------------------------------------------
# Amendment (independent review PR #387, Finding B): genuine multi-leaf
# MUST/AND proof on ONE current publisher revision -- TRUE/FALSE/UNKNOWN
# combinations across two active criteria (draft_max + keel_configuration),
# not merely one criterion at a time.
# ---------------------------------------------------------------------------


def test_claim_only_multi_leaf_and_true_true_confirms(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-AND-TT",
        physical_boat_id="PB-92-AND-TT",
        market_episode_id="ME-92-AND-TT",
        draft=Decimal("1.40"),
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=Decimal("1.60"), keel_configuration="FIN", as_of=_as_of()
    )
    assert "NL-92-AND-TT" in {m.native_listing_id.value for m in outcome.claim_only_matches}


def test_claim_only_multi_leaf_and_true_false_is_non_match(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-AND-TF",
        physical_boat_id="PB-92-AND-TF",
        market_episode_id="ME-92-AND-TF",
        draft=Decimal("1.40"),  # draft_max<=1.60 -> TRUE
        keel_configuration=KeelConfiguration.TWIN_KEEL,  # != FIN -> FALSE
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=Decimal("1.60"), keel_configuration="FIN", as_of=_as_of()
    )
    assert "NL-92-AND-TF" in {m.native_listing_id.value for m in outcome.claim_only_non_matches}
    assert "NL-92-AND-TF" not in {m.native_listing_id.value for m in outcome.claim_only_matches}


def test_claim_only_multi_leaf_and_false_wins_over_unknown(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-AND-FU",
        physical_boat_id="PB-92-AND-FU",
        market_episode_id="ME-92-AND-FU",
        draft=Decimal("2.00"),  # draft_max<=1.60 -> FALSE
        # keel_configuration omitted entirely -> UNKNOWN
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=Decimal("1.60"), keel_configuration="FIN", as_of=_as_of()
    )
    # A confirmed FALSE on one leaf must win over an UNKNOWN on the other --
    # never silently upgraded to INSUFFICIENT_DATA.
    assert "NL-92-AND-FU" in {m.native_listing_id.value for m in outcome.claim_only_non_matches}


def test_claim_only_multi_leaf_and_true_unknown_is_insufficient(claim_conn: Any) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-AND-TU",
        physical_boat_id="PB-92-AND-TU",
        market_episode_id="ME-92-AND-TU",
        draft=Decimal("1.40"),  # draft_max<=1.60 -> TRUE
        # keel_configuration omitted entirely -> UNKNOWN
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=Decimal("1.60"), keel_configuration="FIN", as_of=_as_of()
    )
    # No confirmed FALSE anywhere, one UNKNOWN -> INSUFFICIENT_DATA, never a
    # guessed TRUE and never silently promoted to CONFIRMED_NON_MATCH.
    assert "NL-92-AND-TU" in {
        m.native_listing_id.value for m in outcome.claim_only_insufficient_data
    }
    assert "NL-92-AND-TU" not in {m.native_listing_id.value for m in outcome.claim_only_matches}
    assert "NL-92-AND-TU" not in {m.native_listing_id.value for m in outcome.claim_only_non_matches}


# ---------------------------------------------------------------------------
# Amendment (Finding B): parametrized executable per-field threshold proof
# for all nine accepted Sail dimensions, each exercised in isolation
# (correct value -> CONFIRMED_MATCH, wrong value -> CONFIRMED_NON_MATCH,
# omitted field -> INSUFFICIENT_DATA) through the identical shared
# evaluator -- one reusable fixture/assertion shape, not nine independently
# written scorers.
# ---------------------------------------------------------------------------

_NINE_FIELD_CASES = [
    pytest.param(
        {"draft": Decimal("1.40")},
        {"draft_max": Decimal("1.60")},
        {"draft_max": Decimal("1.00")},
        id="draft_max",
    ),
    pytest.param(
        {"keel_configuration": KeelConfiguration.FIN},
        {"keel_configuration": "FIN"},
        {"keel_configuration": "TWIN_KEEL"},
        id="keel_configuration",
    ),
    pytest.param(
        {"loa_length": Decimal("12.00")},
        {"loa_max": Decimal("15.00")},
        {"loa_max": Decimal("10.00")},
        id="loa",
    ),
    pytest.param(
        {"rudder_configuration": RudderConfiguration.SPADE},
        {"rudder_configuration": "SPADE"},
        {"rudder_configuration": "TWIN"},
        id="rudder_configuration",
    ),
    pytest.param(
        {"hull_configuration": HullConfiguration.MONOHULL},
        {"hull_configuration": "MONOHULL"},
        {"hull_configuration": "CATAMARAN"},
        id="hull_configuration",
    ),
    pytest.param(
        {"cockpit_position": CockpitPosition.AFT},
        {"cockpit_position": "AFT"},
        {"cockpit_position": "FORWARD"},
        id="cockpit_position",
    ),
    pytest.param(
        {"deck_saloon": DeckSaloon.DECK_SALOON},
        {"deck_saloon": "DECK_SALOON"},
        {"deck_saloon": "PILOTHOUSE"},
        id="deck_saloon",
    ),
    pytest.param(
        {"beam": Decimal("4.00")},
        {"beam_max": Decimal("4.50")},
        {"beam_max": Decimal("3.00")},
        id="beam",
    ),
    pytest.param(
        {"hull_material": HullMaterial.GRP_FIBERGLASS},
        {"hull_material": "GRP_FIBERGLASS"},
        {"hull_material": "STEEL"},
        id="hull_material",
    ),
]

_EMPTY_REQUIREMENT_KWARGS: dict[str, Any] = {
    "draft_max": None,
    "keel_configuration": None,
    "loa_min": None,
    "loa_max": None,
    "rudder_configuration": None,
    "hull_configuration": None,
    "cockpit_position": None,
    "deck_saloon": None,
    "beam_min": None,
    "beam_max": None,
    "hull_material": None,
}


@pytest.mark.parametrize("listing_kwargs,correct_query,wrong_query", _NINE_FIELD_CASES)
def test_all_nine_sail_fields_claim_only_threshold_proof(
    claim_conn: Any,
    listing_kwargs: dict[str, Any],
    correct_query: dict[str, Any],
    wrong_query: dict[str, Any],
) -> None:
    field_id = next(iter(listing_kwargs))
    suffix = field_id.upper().replace("_", "")[:10]
    listing_id = f"NL-92-F9-{suffix}"
    physical_boat_id = f"PB-92-F9-{suffix}"
    market_episode_id = f"ME-92-F9-{suffix}"
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id=listing_id,
        physical_boat_id=physical_boat_id,
        market_episode_id=market_episode_id,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        **listing_kwargs,
    )

    correct_params = dict(_EMPTY_REQUIREMENT_KWARGS)
    correct_params.update(correct_query)
    outcome_correct = evaluate_native_inventory_requirements(
        claim_conn, as_of=_as_of(), **correct_params
    )
    assert listing_id in {m.native_listing_id.value for m in outcome_correct.claim_only_matches}

    wrong_params = dict(_EMPTY_REQUIREMENT_KWARGS)
    wrong_params.update(wrong_query)
    outcome_wrong = evaluate_native_inventory_requirements(
        claim_conn, as_of=_as_of(), **wrong_params
    )
    assert listing_id in {m.native_listing_id.value for m in outcome_wrong.claim_only_non_matches}
    assert listing_id not in {m.native_listing_id.value for m in outcome_wrong.claim_only_matches}

    # A read leaves the connection non-IDLE; the next write needs IDLE.
    claim_conn.commit()

    # Omission proof: a separate, otherwise-identical SAIL-admitted listing
    # that never asserted this exact field at all is INSUFFICIENT_DATA when
    # queried on it, never a guessed match/non-match.
    omitted_listing_id = f"{listing_id}-OM"
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id=omitted_listing_id,
        physical_boat_id=f"{physical_boat_id}-OM",
        market_episode_id=f"{market_episode_id}-OM",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome_omitted = evaluate_native_inventory_requirements(
        claim_conn, as_of=_as_of(), **correct_params
    )
    assert omitted_listing_id in {
        m.native_listing_id.value for m in outcome_omitted.claim_only_insufficient_data
    }


# ---------------------------------------------------------------------------
# Amendment (Finding B): D29 current-public-eligibility suppression for the
# new claim-only path -- a real persisted ORGANIZATION_NOT_ELIGIBLE
# suppression (not a fabricated fact) excludes the candidate from every
# claim-only result surface outright, exactly like the design-linked funnel.
# ---------------------------------------------------------------------------


def test_claim_only_d29_suppressed_organization_excludes_entirely(claim_conn: Any) -> None:
    _account, org, _membership = _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-D29",
        physical_boat_id="PB-92-D29",
        market_episode_id="ME-92-D29",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    outcome_before = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert "NL-92-D29" in {m.native_listing_id.value for m in outcome_before.claim_only_matches}

    # Real, persisted suppression: the publishing Organization's own
    # eligibility flips to non-ELIGIBLE after publish (idempotent upsert,
    # `hullq.persistence.broker_identity.seed_marketplace_organization`) --
    # D29's `ORGANIZATION_NOT_ELIGIBLE` reason, not a hand-simulated fact.
    suppressed_org = MarketplaceOrganization(
        id=org.id,
        professional_category=org.professional_category,
        publishing_eligibility=OrganizationPublishingEligibility.UNVERIFIED,
    )
    seed_marketplace_organization(claim_conn, suppressed_org)
    claim_conn.commit()

    outcome_after = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    all_ids_after = (
        {m.native_listing_id.value for m in outcome_after.claim_only_matches}
        | {m.native_listing_id.value for m in outcome_after.claim_only_non_matches}
        | {m.native_listing_id.value for m in outcome_after.claim_only_insufficient_data}
    )
    assert "NL-92-D29" not in all_ids_after


# ---------------------------------------------------------------------------
# Amendment (Finding B): two real PostgreSQL connections -- a writer
# changing BOTH category and a technical field together in one new
# revision, held open (uncommitted) while a separate reader connection
# evaluates Search -- proving category and selected fields can never be
# combined from two different revisions (contract §E coherent snapshot).
# ---------------------------------------------------------------------------


def test_claim_only_two_connection_concurrent_revision_never_sees_hybrid_state(
    claim_url: str, claim_conn: Any
) -> None:
    account, org, _membership = _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-CONC",
        physical_boat_id="PB-92-CONC",
        market_episode_id="ME-92-CONC",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    current_revision_id = _current_claim_revision_id(claim_conn, listing_id="NL-92-CONC", org=org)
    claim_conn.commit()
    assert current_revision_id is not None

    outcome_before = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert "NL-92-CONC" in {m.native_listing_id.value for m in outcome_before.claim_only_matches}

    writer_conn = psycopg.connect(claim_url)
    try:
        with writer_conn.transaction(), writer_conn.cursor() as cur:
            write_physical_boat_claim_revision_row(
                cur,
                account_id=account,
                candidate_organization=org,
                native_listing_id=NativeListingId("NL-92-CONC"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-92-CONC-2"),
                expected_current_revision_id=current_revision_id,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Unbranded",
                    model_designation_claim="Unmatched Model",
                    build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                    keel_configuration=KeelConfigurationClaim(
                        assertion_kind=VA, value=KeelConfiguration.TWIN_KEEL
                    ),
                    vessel_category=VesselCategoryClaim(
                        assertion_kind=VA, value=VesselCategory.POWER
                    ),
                ),
            )

            # Reader: a SEPARATE real connection, while the writer's
            # transaction above is still open/uncommitted. Under PostgreSQL's
            # default READ COMMITTED isolation it must see only the OLD,
            # fully committed revision (FIN/SAIL) -- never a torn mix of the
            # new keel with the old category or vice versa.
            reader_conn = psycopg.connect(claim_url)
            try:
                outcome_during = evaluate_native_inventory_requirements(
                    reader_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
                )
                assert "NL-92-CONC" in {
                    m.native_listing_id.value for m in outcome_during.claim_only_matches
                }
            finally:
                reader_conn.close()
        # `with writer_conn.transaction():` commits here on clean exit.
    finally:
        writer_conn.close()

    # After commit, the fully new revision (POWER + TWIN_KEEL) is visible
    # atomically -- never a torn combination.
    outcome_after = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    assert "NL-92-CONC" not in {m.native_listing_id.value for m in outcome_after.claim_only_matches}
    non_match = next(
        m for m in outcome_after.claim_only_non_matches if m.native_listing_id.value == "NL-92-CONC"
    )
    assert non_match.vessel_category_exclusion is not None
    assert non_match.vessel_category_exclusion.resolution is VesselCategoryResolution.POWER


# ---------------------------------------------------------------------------
# Amendment (independent review PR #387, Finding C): typed internal
# provenance retained on PublisherClaimCandidateEvaluation, and strict
# public-surface non-leakage.
# ---------------------------------------------------------------------------


def test_source_evidence_retains_publisher_revision_provenance(claim_conn: Any) -> None:
    account, org, _membership = _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-PROV",
        physical_boat_id="PB-92-PROV",
        market_episode_id="ME-92-PROV",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    expected_revision_id = _current_claim_revision_id(claim_conn, listing_id="NL-92-PROV", org=org)
    claim_conn.commit()

    outcome = evaluate_native_inventory_requirements(
        claim_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    match = next(m for m in outcome.claim_only_matches if m.native_listing_id.value == "NL-92-PROV")
    assert match.source_basis.value == "PUBLISHER_CLAIM"
    assert match.source_evidence is not None
    assert match.source_evidence.revision_id == expected_revision_id
    assert match.source_evidence.recorded_by_account_id == account
    assert match.source_evidence.category_claim is not None
    assert match.source_evidence.category_claim.value is VesselCategory.SAIL


def test_public_api_never_leaks_internal_source_evidence(
    claim_conn: Any, client: TestClient
) -> None:
    _make_design_unresolved_active_listing(
        claim_conn,
        listing_id="NL-92-NOLEAK",
        physical_boat_id="PB-92-NOLEAK",
        market_episode_id="ME-92-NOLEAK",
        keel_configuration=KeelConfiguration.FIN,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
    )
    response = client.get("/api/search/en", params={"keel_configuration": "FIN"})
    assert response.status_code == 200
    body = response.json()
    match = next(
        m for m in body["publisher_claim_matches"] if m["native_listing_id"] == "NL-92-NOLEAK"
    )
    assert set(match.keys()) == {
        "native_listing_id",
        "publishing_organization_id",
        "freshness_status",
        "last_confirmed_at",
        "source_basis",
        "criterion_evidence",
        "discovery_token",
    }
    assert "source_evidence" not in match
    assert "recorded_by_account_id" not in match
    assert "revision_id" not in match
