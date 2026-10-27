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
    BuildYearClaim,
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
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
