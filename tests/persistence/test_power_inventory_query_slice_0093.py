"""PostgreSQL-backed Power drive-configuration Search integration tests -- SLICE-0093.

Proves the first Power hard technical criterion
(`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`) end to end
through `hullq.application.power_inventory_query.evaluate_power_drive_requirement`:
the mandatory minimum positive (a currently-public-eligible, design-unresolved
POWER PhysicalBoat with a publisher-owned current POD claim), category
isolation (SAIL/UNKNOWN never becomes a Power positive, another
Organization's POWER claim never lends the publisher eligibility), the
bounded v0.6 SHAFT/OUTBOARD design-linked bridge (and v0.6 `other` staying
INSUFFICIENT_DATA, never guessed), and D29 current-public eligibility
suppression.

Each test runs against its own disposable PostgreSQL schema, mirroring
`tests/persistence/test_native_inventory_query_vessel_category_slice_0091.py`'s
isolation pattern (deliberately duplicated minimal seeding boilerplate rather
than cross-importing between test modules -- established repo convention).
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

from hullq.application.power_inventory_query import evaluate_power_drive_requirement
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
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
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
from hullq.search.power_drive_design_bridge import lookup_power_drive_canonical_value

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
def pwr_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0093pwr_{uuid.uuid4().hex[:16]}"
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
def pwr_conn(pwr_url: str) -> Generator[Any]:
    conn = psycopg.connect(pwr_url)
    try:
        yield conn
    finally:
        conn.close()


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


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str | None,
    vessel_category: VesselCategoryClaim | None,
    power_drive_configuration: PowerDriveConfigurationClaim | None,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id),
            boat_design_ref=BoatDesignRef(boat_design_id) if boat_design_id is not None else None,
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
            broker_description="A well-maintained motor yacht.",
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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Swift Trawler 35",
            build_year=BuildYearClaim(assertion_kind=VA, value=2020),
            vessel_category=vessel_category,
            power_drive_configuration=power_drive_configuration,
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


def _write_second_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    vessel_category: VesselCategoryClaim | None,
    power_drive_configuration: PowerDriveConfigurationClaim | None,
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
            marketed_brand_claim="Beneteau",
            model_designation_claim="Swift Trawler 35",
            build_year=BuildYearClaim(assertion_kind=VA, value=2020),
            vessel_category=vessel_category,
            power_drive_configuration=power_drive_configuration,
        ),
    )
    assert result.status.value in ("created", "revised"), result
    conn.commit()


def _result_classes(conn: Any, *, power_drive: str) -> tuple[set[str], set[str], set[str]]:
    outcome = evaluate_power_drive_requirement(conn, power_drive=power_drive, as_of=_as_of())
    matches = {m.native_listing_id.value for m in outcome.claim_only_matches} | {
        m.native_listing_id.value for m in outcome.design_linked_matches
    }
    non_matches = {m.native_listing_id.value for m in outcome.claim_only_non_matches} | {
        m.native_listing_id.value for m in outcome.design_linked_non_matches
    }
    insufficient = {m.native_listing_id.value for m in outcome.claim_only_insufficient_data} | {
        m.native_listing_id.value for m in outcome.design_linked_insufficient_data
    }
    return matches, non_matches, insufficient


# ---------------------------------------------------------------------------
# Mandatory minimum positive (contract "Objective"): design-unresolved POWER
# boat, publisher-owned current POD claim.
# ---------------------------------------------------------------------------


def test_design_unresolved_power_pod_claim_is_confirmed_match(pwr_conn: Any) -> None:
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-POD",
        physical_boat_id="PB-93-POD",
        market_episode_id="ME-93-POD",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.POD
        ),
    )
    matches, _, _ = _result_classes(pwr_conn, power_drive="POD")
    assert "NL-93-POD" in matches

    outcome = evaluate_power_drive_requirement(pwr_conn, power_drive="POD", as_of=_as_of())
    match = next(m for m in outcome.claim_only_matches if m.native_listing_id.value == "NL-93-POD")
    assert match.source_basis.value == "PUBLISHER_CLAIM"

    # The corresponding wrong token is an evidenced nonmatch, not a positive.
    wrong_matches, wrong_non_matches, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-POD" not in wrong_matches
    assert "NL-93-POD" in wrong_non_matches


@pytest.mark.parametrize("token", ["SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"])
def test_every_public_token_becomes_exactly_one_positive(pwr_conn: Any, token: str) -> None:
    listing_id = f"NL-93-TOK-{token}"
    _make_active_listing(
        pwr_conn,
        listing_id=listing_id,
        physical_boat_id=f"PB-93-TOK-{token}",
        market_episode_id=f"ME-93-TOK-{token}",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration(token)
        ),
    )
    matches, _, _ = _result_classes(pwr_conn, power_drive=token)
    assert listing_id in matches


# ---------------------------------------------------------------------------
# Category isolation: explicit SAIL/UNKNOWN never becomes a Power positive.
# ---------------------------------------------------------------------------


def test_explicit_sail_category_never_becomes_power_positive(pwr_conn: Any) -> None:
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-SAIL",
        physical_boat_id="PB-93-SAIL",
        market_episode_id="ME-93-SAIL",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.POD
        ),
    )
    matches, non_matches, _ = _result_classes(pwr_conn, power_drive="POD")
    assert "NL-93-SAIL" not in matches
    assert "NL-93-SAIL" in non_matches


def test_missing_category_is_insufficient_not_confirmed_or_excluded(pwr_conn: Any) -> None:
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-UNK",
        physical_boat_id="PB-93-UNK",
        market_episode_id="ME-93-UNK",
        boat_design_id=None,
        vessel_category=None,
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.POD
        ),
    )
    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="POD")
    assert "NL-93-UNK" not in matches
    assert "NL-93-UNK" not in non_matches
    assert "NL-93-UNK" in insufficient


def test_mixed_and_other_and_unknown_drive_never_confirm(pwr_conn: Any) -> None:
    for token, claim in (
        (
            "MIXED",
            PowerDriveConfigurationClaim(assertion_kind=VA, value=PowerDriveConfiguration.MIXED),
        ),
        (
            "OTHER",
            PowerDriveConfigurationClaim(assertion_kind=VA, value=PowerDriveConfiguration.OTHER),
        ),
        ("UNKNOWN", PowerDriveConfigurationClaim(assertion_kind=UNK)),
    ):
        listing_id = f"NL-93-{token}"
        _make_active_listing(
            pwr_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-93-{token}",
            market_episode_id=f"ME-93-{token}",
            boat_design_id=None,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=claim,
        )
    for token in ("SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"):
        matches, _, _ = _result_classes(pwr_conn, power_drive=token)
        assert "NL-93-MIXED" not in matches
        assert "NL-93-OTHER" not in matches
        assert "NL-93-UNKNOWN" not in matches


def test_mixed_drive_is_insufficient_data_for_every_token_never_a_confirmed_exclusion(
    pwr_conn: Any,
) -> None:
    """Review amendment Finding A (BLOCKER): a current `VALUE_ASSERTION(MIXED)`
    claim does not prove the absence of any single accepted drive type --
    the contract's own words are "even if the vessel uses one of the
    types". Every one of the five public tokens must be `INSUFFICIENT_DATA`
    for a MIXED listing, never a false `CONFIRMED_NON_MATCH`."""
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-MIXEDALL",
        physical_boat_id="PB-93-MIXEDALL",
        market_episode_id="ME-93-MIXEDALL",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.MIXED
        ),
    )
    for token in ("SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"):
        matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive=token)
        assert "NL-93-MIXEDALL" not in matches
        assert "NL-93-MIXEDALL" not in non_matches, (
            f"MIXED must never become a confirmed exclusion for {token}"
        )
        assert "NL-93-MIXEDALL" in insufficient


def test_other_drive_is_a_genuine_confirmed_exclusion_for_every_token(pwr_conn: Any) -> None:
    """`OTHER` denotes a confirmed single (if uncatalogued) drive -- unlike
    `MIXED`, it is a genuine `CONFIRMED_NON_MATCH` for every one of the five
    public tokens (identical treatment to `HullMaterial.OTHER`/
    `KeelConfiguration.OTHER` elsewhere in this codebase)."""
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-OTHERALL",
        physical_boat_id="PB-93-OTHERALL",
        market_episode_id="ME-93-OTHERALL",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.OTHER
        ),
    )
    for token in ("SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"):
        matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive=token)
        assert "NL-93-OTHERALL" not in matches
        assert "NL-93-OTHERALL" in non_matches
        assert "NL-93-OTHERALL" not in insufficient


def test_single_drive_token_is_a_genuine_confirmed_exclusion_for_every_other_token(
    pwr_conn: Any,
) -> None:
    """Preserve genuine confirmed negatives for single-drive values (review
    amendment Finding A): a publisher-confirmed SHAFT must be a real
    `CONFIRMED_NON_MATCH` for every one of the other four tokens, not
    merely 'not a match'."""
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-SHAFTONLY",
        physical_boat_id="PB-93-SHAFTONLY",
        market_episode_id="ME-93-SHAFTONLY",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    for token in ("STERNDRIVE", "POD", "WATERJET", "OUTBOARD"):
        matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive=token)
        assert "NL-93-SHAFTONLY" not in matches
        assert "NL-93-SHAFTONLY" in non_matches
        assert "NL-93-SHAFTONLY" not in insufficient


# ---------------------------------------------------------------------------
# Another Organization's POWER claim cannot lend the publisher eligibility.
# ---------------------------------------------------------------------------


def test_other_organization_only_power_category_does_not_admit(pwr_conn: Any) -> None:
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-XORG",
        physical_boat_id="PB-93-XORG",
        market_episode_id="ME-93-XORG",
        boat_design_id=None,
        vessel_category=None,
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    # A different Organization asserts POWER about the same PhysicalBoat --
    # never a real production path, but exercises the exact fail-closed
    # cross-Organization-identity guard directly at the persistence layer.
    other_org = _org("ORG-93-XORG-OTHER")
    other_account = AccountId("ACC-93-XORG-OTHER")
    with pwr_conn.transaction():
        with pwr_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [other_account.value],
            )
        seed_marketplace_organization(pwr_conn, other_org)
    with pwr_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, vessel_category_assertion_kind, "
            "vessel_category_value, previous_claim_revision_id, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)",
            [
                "PBCREV-93-XORG-OTHER",
                "PB-93-XORG",
                other_org.id.value,
                other_account.value,
                "Other Brand",
                "Other Model",
                "VALUE_ASSERTION",
                2020,
                "VALUE_ASSERTION",
                "POWER",
                "0" * 64,
            ],
        )
        cur.execute(
            "INSERT INTO physical_boat_claim_heads ("
            "physical_boat_id, claiming_organization_id, current_claim_revision_id"
            ") VALUES (%s, %s, %s)",
            ["PB-93-XORG", other_org.id.value, "PBCREV-93-XORG-OTHER"],
        )
    pwr_conn.commit()

    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-XORG" not in matches
    assert "NL-93-XORG" not in non_matches
    assert "NL-93-XORG" in insufficient


# ---------------------------------------------------------------------------
# Review amendment Finding D: conflicting current drive assertions across
# two Organizations for the same PhysicalBoat -- both agree on POWER
# category (so category admission succeeds), but disagree on the current
# drive. Neither token can be confirmed or excluded; the field must fail
# closed to INSUFFICIENT_DATA, never pick a side.
# ---------------------------------------------------------------------------


def test_cross_organization_conflicting_current_drive_fails_closed(pwr_conn: Any) -> None:
    _account, _pub_org, _membership = _make_active_listing(
        pwr_conn,
        listing_id="NL-93-XDRV",
        physical_boat_id="PB-93-XDRV",
        market_episode_id="ME-93-XDRV",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    other_org = _org("ORG-93-XDRV-OTHER")
    other_account = AccountId("ACC-93-XDRV-OTHER")
    with pwr_conn.transaction():
        with pwr_conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [other_account.value],
            )
        seed_marketplace_organization(pwr_conn, other_org)
    with pwr_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, vessel_category_assertion_kind, "
            "vessel_category_value, power_drive_configuration_assertion_kind, "
            "power_drive_configuration_value, previous_claim_revision_id, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)",
            [
                "PBCREV-93-XDRV-OTHER",
                "PB-93-XDRV",
                other_org.id.value,
                other_account.value,
                "Other Brand",
                "Other Model",
                "VALUE_ASSERTION",
                2020,
                "VALUE_ASSERTION",
                "POWER",
                "VALUE_ASSERTION",
                "POD",
                "0" * 64,
            ],
        )
        cur.execute(
            "INSERT INTO physical_boat_claim_heads ("
            "physical_boat_id, claiming_organization_id, current_claim_revision_id"
            ") VALUES (%s, %s, %s)",
            ["PB-93-XDRV", other_org.id.value, "PBCREV-93-XDRV-OTHER"],
        )
    pwr_conn.commit()

    # Both Organizations agree on POWER (no category conflict -- the
    # publisher-owned admission precondition succeeds), but SHAFT vs POD is
    # a genuine same-PhysicalBoat cross-Organization contradiction on the
    # technical field itself: neither token may be confirmed or excluded.
    for token in ("SHAFT", "POD"):
        matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive=token)
        assert "NL-93-XDRV" not in matches
        assert "NL-93-XDRV" not in non_matches, (
            f"a cross-Organization drive contradiction must never resolve to a confirmed "
            f"exclusion for {token}"
        )
        assert "NL-93-XDRV" in insufficient


def _seed_other_org_power_claim(
    conn: Any,
    *,
    physical_boat_id: str,
    org_suffix: str,
    category_value: str,
    drive_value: str,
) -> None:
    """Raw-insert a second claiming Organization's current claim for an
    already-seeded PhysicalBoat -- the same pattern
    `test_cross_organization_conflicting_current_drive_fails_closed` already
    uses, factored out so Finding H's MIXED-specific cross-Organization
    cases don't duplicate it a third/fourth time."""
    other_org = _org(f"ORG-{org_suffix}")
    other_account = AccountId(f"ACC-{org_suffix}")
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [other_account.value],
            )
        seed_marketplace_organization(conn, other_org)
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, vessel_category_assertion_kind, "
            "vessel_category_value, power_drive_configuration_assertion_kind, "
            "power_drive_configuration_value, previous_claim_revision_id, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)",
            [
                f"PBCREV-{org_suffix}",
                physical_boat_id,
                other_org.id.value,
                other_account.value,
                "Other Brand",
                "Other Model",
                "VALUE_ASSERTION",
                2020,
                "VALUE_ASSERTION",
                category_value,
                "VALUE_ASSERTION",
                drive_value,
                "0" * 64,
            ],
        )
        cur.execute(
            "INSERT INTO physical_boat_claim_heads ("
            "physical_boat_id, claiming_organization_id, current_claim_revision_id"
            ") VALUES (%s, %s, %s)",
            [physical_boat_id, other_org.id.value, f"PBCREV-{org_suffix}"],
        )
    conn.commit()


# ---------------------------------------------------------------------------
# Review amendment Finding H (BLOCKER): another Organization's current
# MIXED drive claim is genuine contradicting source evidence when the
# publisher asserts a single drive type -- it must never be silently
# disregarded/masked. Both directions (publisher single-token vs. other-org
# MIXED, and the reverse) must fail closed to INSUFFICIENT_DATA for every
# disputed token; a publisher-only MIXED claim with no other Organization at
# all keeps the ordinary Finding A "not a confirmed exclusion" treatment.
# ---------------------------------------------------------------------------


def test_publisher_shaft_versus_other_organization_mixed_fails_closed(pwr_conn: Any) -> None:
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-HMIX1",
        physical_boat_id="PB-93-HMIX1",
        market_episode_id="ME-93-HMIX1",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    _seed_other_org_power_claim(
        pwr_conn,
        physical_boat_id="PB-93-HMIX1",
        org_suffix="93-HMIX1-OTHER",
        category_value="POWER",
        drive_value="MIXED",
    )
    # A single-token publisher claim contested by another Organization's
    # current MIXED claim is a genuine same-PhysicalBoat contradiction on
    # the technical field: SHAFT may not be confirmed (the other
    # Organization's current evidence does not agree it is purely SHAFT).
    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-HMIX1" not in matches, (
        "another Organization's current MIXED claim must not be silently disregarded when "
        "the publisher asserts a single drive type"
    )
    assert "NL-93-HMIX1" not in non_matches
    assert "NL-93-HMIX1" in insufficient


def test_publisher_mixed_versus_other_organization_shaft_fails_closed(pwr_conn: Any) -> None:
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-HMIX2",
        physical_boat_id="PB-93-HMIX2",
        market_episode_id="ME-93-HMIX2",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.MIXED
        ),
    )
    _seed_other_org_power_claim(
        pwr_conn,
        physical_boat_id="PB-93-HMIX2",
        org_suffix="93-HMIX2-OTHER",
        category_value="POWER",
        drive_value="SHAFT",
    )
    # Reverse combination: the publisher's own claim is MIXED, but another
    # Organization currently claims a single token (SHAFT) for the same
    # PhysicalBoat -- still a genuine cross-Organization contradiction, not
    # the publisher-only-MIXED case Finding A's downgrade covers.
    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-HMIX2" not in matches
    assert "NL-93-HMIX2" not in non_matches
    assert "NL-93-HMIX2" in insufficient


def test_publisher_mixed_with_no_other_organization_is_still_insufficient_not_excluded(
    pwr_conn: Any,
) -> None:
    """Nonconflicting control: a publisher-only current MIXED claim, with no
    other Organization claiming this PhysicalBoat at all, keeps the
    ordinary Finding A result-level downgrade (INSUFFICIENT_DATA, never a
    false CONFIRMED_NON_MATCH) -- Finding H's cross-Organization guard fix
    must not regress this already-accepted single-claimant case."""
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-HMIX3",
        physical_boat_id="PB-93-HMIX3",
        market_episode_id="ME-93-HMIX3",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.MIXED
        ),
    )
    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-HMIX3" not in matches
    assert "NL-93-HMIX3" not in non_matches
    assert "NL-93-HMIX3" in insufficient


def test_publisher_shaft_versus_other_organization_shaft_is_a_nonconflicting_confirmed_match(
    pwr_conn: Any,
) -> None:
    """Nonconflicting control: two Organizations agreeing on the identical
    single token must still confirm -- Finding H's fix must not turn
    ordinary agreement into a false contradiction."""
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-HMIX4",
        physical_boat_id="PB-93-HMIX4",
        market_episode_id="ME-93-HMIX4",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    _seed_other_org_power_claim(
        pwr_conn,
        physical_boat_id="PB-93-HMIX4",
        org_suffix="93-HMIX4-OTHER",
        category_value="POWER",
        drive_value="SHAFT",
    )
    matches, _, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-HMIX4" in matches


# ---------------------------------------------------------------------------
# Review amendment Finding D: a true two-connection concurrent revision --
# a writer changing both category and drive together in one new revision,
# held open (uncommitted) while a separate reader connection evaluates
# Search -- proving category and the technical drive field can never be
# combined from two different revisions (contract §E coherent snapshot).
# ---------------------------------------------------------------------------


def test_two_connection_concurrent_revision_never_sees_hybrid_state(
    pwr_url: str, pwr_conn: Any
) -> None:
    account, org, _membership = _make_active_listing(
        pwr_conn,
        listing_id="NL-93-CONC",
        physical_boat_id="PB-93-CONC",
        market_episode_id="ME-93-CONC",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    current_revision_id = _current_claim_revision_id(pwr_conn, listing_id="NL-93-CONC", org=org)
    pwr_conn.commit()
    assert current_revision_id is not None

    matches_before, _, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-CONC" in matches_before

    writer_conn = psycopg.connect(pwr_url)
    try:
        with writer_conn.transaction(), writer_conn.cursor() as cur:
            write_physical_boat_claim_revision_row(
                cur,
                account_id=account,
                candidate_organization=org,
                native_listing_id=NativeListingId("NL-93-CONC"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-93-CONC-2"),
                expected_current_revision_id=current_revision_id,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Unbranded",
                    model_designation_claim="Unmatched Model",
                    build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                    vessel_category=VesselCategoryClaim(
                        assertion_kind=VA, value=VesselCategory.SAIL
                    ),
                    power_drive_configuration=PowerDriveConfigurationClaim(
                        assertion_kind=VA, value=PowerDriveConfiguration.POD
                    ),
                ),
            )

            # Reader: a SEPARATE real connection, while the writer's
            # transaction above is still open/uncommitted. Under
            # PostgreSQL's default READ COMMITTED isolation it must see
            # only the OLD, fully committed revision (POWER/SHAFT) --
            # never a torn mix of the new drive with the old category or
            # vice versa.
            reader_conn = psycopg.connect(pwr_url)
            try:
                matches_during, _, _ = _result_classes(reader_conn, power_drive="SHAFT")
                assert "NL-93-CONC" in matches_during
            finally:
                reader_conn.close()
        # `with writer_conn.transaction():` commits here on clean exit.
    finally:
        writer_conn.close()

    # After commit, the fully new revision (SAIL + POD) is visible
    # atomically -- the listing is now explicitly excluded from Power
    # entirely (SAIL category), never a torn SHAFT-match/POWER-category
    # hybrid and never a lingering stale SHAFT match.
    matches_after, non_matches_after, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-CONC" not in matches_after
    assert "NL-93-CONC" in non_matches_after
    matches_after_pod, _, _ = _result_classes(pwr_conn, power_drive="POD")
    assert "NL-93-CONC" not in matches_after_pod


# ---------------------------------------------------------------------------
# Design-linked v0.6 bridge: shaft/outboard qualify, "other" never guessed.
# ---------------------------------------------------------------------------


def _insert_boat_design(conn: Any, design_id: str, model_id: str, *, drive_type: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": drive_type}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()


def _admit_design_drive_type(conn: Any, design_id: str, *, value: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/drive_type",
        value=value,
        resolution_id=f"FR-PWRDRV-{design_id}",
        fetch_canonical_value=lookup_power_drive_canonical_value,
    )


def test_design_linked_shaft_with_matching_concrete_claim_confirms(pwr_conn: Any) -> None:
    _insert_boat_design(pwr_conn, "BD-93-SHAFT", "BM-93-SHAFT", drive_type="shaft")
    _admit_design_drive_type(pwr_conn, "BD-93-SHAFT", value="shaft")
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-DSHAFT",
        physical_boat_id="PB-93-DSHAFT",
        market_episode_id="ME-93-DSHAFT",
        boat_design_id="BD-93-SHAFT",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    matches, _, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-DSHAFT" in matches


def test_design_linked_other_drive_type_is_insufficient_never_guessed(pwr_conn: Any) -> None:
    _insert_boat_design(pwr_conn, "BD-93-OTH", "BM-93-OTH", drive_type="other")
    _admit_design_drive_type(pwr_conn, "BD-93-OTH", value="other")
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-DOTH",
        physical_boat_id="PB-93-DOTH",
        market_episode_id="ME-93-DOTH",
        boat_design_id="BD-93-OTH",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.STERNDRIVE
        ),
    )
    for token in ("SHAFT", "STERNDRIVE", "POD", "WATERJET", "OUTBOARD"):
        matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive=token)
        assert "NL-93-DOTH" not in matches
        assert "NL-93-DOTH" not in non_matches
        assert "NL-93-DOTH" in insufficient


def test_design_linked_sail_category_excludes_despite_shaft_mapping(pwr_conn: Any) -> None:
    _insert_boat_design(pwr_conn, "BD-93-DSAIL", "BM-93-DSAIL", drive_type="shaft")
    _admit_design_drive_type(pwr_conn, "BD-93-DSAIL", value="shaft")
    _make_active_listing(
        pwr_conn,
        listing_id="NL-93-DSAIL",
        physical_boat_id="PB-93-DSAIL",
        market_episode_id="ME-93-DSAIL",
        boat_design_id="BD-93-DSAIL",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    matches, non_matches, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-DSAIL" not in matches
    assert "NL-93-DSAIL" in non_matches


# ---------------------------------------------------------------------------
# Review amendment Finding G (BLOCKER): the design-linked plane's category
# admission and drive classification must be drawn from one coherent
# PostgreSQL snapshot -- a two-statement sequence (resolve category, then
# separately re-read claims to classify drive) could otherwise combine a
# pre-commit category with a post-commit drive (or vice versa) across a
# concurrent revision, producing a false CONFIRMED_MATCH the current
# committed state never actually supports.
# ---------------------------------------------------------------------------


def test_design_linked_two_connection_concurrent_revision_never_sees_hybrid_state(
    pwr_url: str, pwr_conn: Any
) -> None:
    _insert_boat_design(pwr_conn, "BD-93-GCONC", "BM-93-GCONC", drive_type="shaft")
    _admit_design_drive_type(pwr_conn, "BD-93-GCONC", value="shaft")
    account, org, _membership = _make_active_listing(
        pwr_conn,
        listing_id="NL-93-GCONC",
        physical_boat_id="PB-93-GCONC",
        market_episode_id="ME-93-GCONC",
        boat_design_id="BD-93-GCONC",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
    )
    current_revision_id = _current_claim_revision_id(pwr_conn, listing_id="NL-93-GCONC", org=org)
    pwr_conn.commit()
    assert current_revision_id is not None

    matches_before, _, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-GCONC" in matches_before

    writer_conn = psycopg.connect(pwr_url)
    try:
        with writer_conn.transaction(), writer_conn.cursor() as cur:
            write_physical_boat_claim_revision_row(
                cur,
                account_id=account,
                candidate_organization=org,
                native_listing_id=NativeListingId("NL-93-GCONC"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-93-GCONC-2"),
                expected_current_revision_id=current_revision_id,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Unbranded",
                    model_designation_claim="Unmatched Model",
                    build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                    vessel_category=VesselCategoryClaim(
                        assertion_kind=VA, value=VesselCategory.SAIL
                    ),
                    power_drive_configuration=PowerDriveConfigurationClaim(
                        assertion_kind=VA, value=PowerDriveConfiguration.POD
                    ),
                ),
            )

            # Reader: a SEPARATE real connection, while the writer's
            # transaction above (new revision: SAIL category + POD drive)
            # is still open/uncommitted. The design-linked evaluator must
            # read category admission and drive classification from one
            # single combined snapshot (`fetch_power_category_drive_snapshot`)
            # -- under READ COMMITTED it sees only the OLD, fully committed
            # revision (POWER category + SHAFT drive) for *both* fields,
            # never a torn combination of the new drive with the old
            # category or vice versa.
            reader_conn = psycopg.connect(pwr_url)
            try:
                matches_during, non_matches_during, _ = _result_classes(
                    reader_conn, power_drive="SHAFT"
                )
                assert "NL-93-GCONC" in matches_during
                assert "NL-93-GCONC" not in non_matches_during
                matches_during_pod, _, _ = _result_classes(reader_conn, power_drive="POD")
                assert "NL-93-GCONC" not in matches_during_pod
            finally:
                reader_conn.close()
        # `with writer_conn.transaction():` commits here on clean exit.
    finally:
        writer_conn.close()

    # After commit, the fully new revision (SAIL + POD) is visible
    # atomically: SAIL category now excludes the listing from Power
    # entirely, regardless of the design-side shaft mapping.
    matches_after, non_matches_after, _ = _result_classes(pwr_conn, power_drive="SHAFT")
    assert "NL-93-GCONC" not in matches_after
    assert "NL-93-GCONC" in non_matches_after
    matches_after_pod, _, _ = _result_classes(pwr_conn, power_drive="POD")
    assert "NL-93-GCONC" not in matches_after_pod


# ---------------------------------------------------------------------------
# D29: a withdrawn/non-public listing is suppressed outright, never a match.
# ---------------------------------------------------------------------------


def test_withdrawn_listing_is_suppressed_from_every_result_surface(pwr_conn: Any) -> None:
    from hullq.persistence.native_listing_lifecycle import withdraw_native_listing

    account, org, membership = _make_active_listing(
        pwr_conn,
        listing_id="NL-93-WD",
        physical_boat_id="PB-93-WD",
        market_episode_id="ME-93-WD",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.WATERJET
        ),
    )
    withdraw_result = withdraw_native_listing(
        pwr_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-93-WD"),
    )
    assert withdraw_result.status.value == "transitioned", withdraw_result
    pwr_conn.commit()

    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="WATERJET")
    assert "NL-93-WD" not in matches
    assert "NL-93-WD" not in non_matches
    assert "NL-93-WD" not in insufficient


# ---------------------------------------------------------------------------
# Revision replacement: a later retraction removes the earlier match.
# ---------------------------------------------------------------------------


def test_retracting_current_drive_removes_earlier_match(pwr_conn: Any) -> None:
    account, org, membership = _make_active_listing(
        pwr_conn,
        listing_id="NL-93-RETR",
        physical_boat_id="PB-93-RETR",
        market_episode_id="ME-93-RETR",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.OUTBOARD
        ),
    )
    matches, _, _ = _result_classes(pwr_conn, power_drive="OUTBOARD")
    assert "NL-93-RETR" in matches

    _write_second_claim(
        pwr_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-93-RETR",
        revision_id="PBCREV-93-RETR-2",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(assertion_kind=UNK),
    )
    matches, non_matches, insufficient = _result_classes(pwr_conn, power_drive="OUTBOARD")
    assert "NL-93-RETR" not in matches
    assert "NL-93-RETR" not in non_matches
    assert "NL-93-RETR" in insufficient
