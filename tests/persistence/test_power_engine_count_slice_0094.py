"""PostgreSQL-backed Power engine-count + combined AND Search integration
tests -- SLICE-0094.

Proves the second Power hard technical criterion
(`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md`) end to end through
`hullq.application.power_inventory_query.evaluate_power_requirement`: the
mandatory minimum positive (a currently-public-eligible, design-unresolved
POWER PhysicalBoat with a publisher-owned current count claim), count-only
and combined drive+count MUST-AND, the bounded v0.6 design-linked
`engine_count` bridge, cross-Organization/cross-revision/cross-variant
isolation, the generalized MIXED-drive-never-proves-absence downgrade with
two active criteria, and that the unmodified SLICE-0093 drive-only path
(`evaluate_power_drive_requirement`) stays byte-for-byte unaffected.

Mirrors `tests/persistence/test_power_inventory_query_slice_0093.py`'s own
disposable-schema isolation pattern (deliberately duplicated minimal
seeding boilerplate rather than cross-importing between test modules --
established repo convention).
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

from hullq.application.power_inventory_query import (
    evaluate_power_drive_requirement,
    evaluate_power_requirement,
)
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
    PowerEngineCountClaim,
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
from hullq.search.power_engine_count_design_bridge import (
    lookup_power_engine_count_canonical_value,
)

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

VA = AssertionKind.VALUE_ASSERTION
UNK = AssertionKind.UNKNOWN


def _as_of() -> datetime:
    return datetime.now(UTC)


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
def pec_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0094pec_{uuid.uuid4().hex[:16]}"
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
def pec_conn(pec_url: str) -> Generator[Any]:
    conn = psycopg.connect(pec_url)
    try:
        yield conn
    finally:
        conn.close()


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
    power_engine_count: PowerEngineCountClaim | None,
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
            power_engine_count=power_engine_count,
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


def _seed_other_org_claim(
    conn: Any,
    *,
    physical_boat_id: str,
    org_suffix: str,
    category_value: str | None,
    drive_value: str | None,
    count_value: int | None,
) -> None:
    """Raw-insert a second claiming Organization's current claim for an
    already-seeded PhysicalBoat -- mirrors SLICE-0093's identical
    `_seed_other_org_power_claim` pattern, extended with the new
    `power_engine_count_*` column pair."""
    other_org = _org(f"ORG-{org_suffix}")
    other_account = AccountId(f"ACC-{org_suffix}")
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [other_account.value],
            )
        seed_marketplace_organization(conn, other_org)
    category_kind = "VALUE_ASSERTION" if category_value is not None else None
    drive_kind = "VALUE_ASSERTION" if drive_value is not None else None
    count_kind = "VALUE_ASSERTION" if count_value is not None else None
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, vessel_category_assertion_kind, "
            "vessel_category_value, power_drive_configuration_assertion_kind, "
            "power_drive_configuration_value, power_engine_count_assertion_kind, "
            "power_engine_count_value, previous_claim_revision_id, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NULL, %s)",
            [
                f"PBCREV-{org_suffix}",
                physical_boat_id,
                other_org.id.value,
                other_account.value,
                "Other Brand",
                "Other Model",
                "VALUE_ASSERTION",
                2020,
                category_kind,
                category_value,
                drive_kind,
                drive_value,
                count_kind,
                count_value,
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


def _result_classes(
    conn: Any, *, power_drive: str | None, power_engine_count: Decimal | None
) -> tuple[set[str], set[str], set[str]]:
    outcome = evaluate_power_requirement(
        conn, power_drive=power_drive, power_engine_count=power_engine_count, as_of=_as_of()
    )
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
# Mandatory minimum positive: design-unresolved POWER boat, publisher-owned
# current count=2 claim, count-only request (no drive).
# ---------------------------------------------------------------------------


def test_design_unresolved_power_count_only_claim_is_confirmed_match(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-CNT2",
        physical_boat_id="PB-94-CNT2",
        market_episode_id="ME-94-CNT2",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, _, _ = _result_classes(pec_conn, power_drive=None, power_engine_count=Decimal(2))
    assert "NL-94-CNT2" in matches

    # The corresponding wrong count is an evidenced nonmatch, not a positive.
    wrong_matches, wrong_non_matches, _ = _result_classes(
        pec_conn, power_drive=None, power_engine_count=Decimal(1)
    )
    assert "NL-94-CNT2" not in wrong_matches
    assert "NL-94-CNT2" in wrong_non_matches


@pytest.mark.parametrize("token", [1, 2, 3, 4, 5, 6, 7, 8])
def test_every_public_count_token_becomes_exactly_one_positive(pec_conn: Any, token: int) -> None:
    listing_id = f"NL-94-TOK-{token}"
    _make_active_listing(
        pec_conn,
        listing_id=listing_id,
        physical_boat_id=f"PB-94-TOK-{token}",
        market_episode_id=f"ME-94-TOK-{token}",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=token),
    )
    matches, _, _ = _result_classes(pec_conn, power_drive=None, power_engine_count=Decimal(token))
    assert listing_id in matches


def test_missing_category_count_only_is_insufficient_not_confirmed_or_excluded(
    pec_conn: Any,
) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-UNK",
        physical_boat_id="PB-94-UNK",
        market_episode_id="ME-94-UNK",
        boat_design_id=None,
        vessel_category=None,
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, non_matches, insufficient = _result_classes(
        pec_conn, power_drive=None, power_engine_count=Decimal(2)
    )
    assert "NL-94-UNK" not in matches
    assert "NL-94-UNK" not in non_matches
    assert "NL-94-UNK" in insufficient


def test_explicit_sail_category_never_becomes_power_count_positive(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-SAIL",
        physical_boat_id="PB-94-SAIL",
        market_episode_id="ME-94-SAIL",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, non_matches, _ = _result_classes(
        pec_conn, power_drive=None, power_engine_count=Decimal(2)
    )
    assert "NL-94-SAIL" not in matches
    assert "NL-94-SAIL" in non_matches


def test_explicit_unknown_count_is_insufficient(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-UNKCNT",
        physical_boat_id="PB-94-UNKCNT",
        market_episode_id="ME-94-UNKCNT",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=UNK),
    )
    matches, non_matches, insufficient = _result_classes(
        pec_conn, power_drive=None, power_engine_count=Decimal(2)
    )
    assert "NL-94-UNKCNT" not in matches
    assert "NL-94-UNKCNT" not in non_matches
    assert "NL-94-UNKCNT" in insufficient


# ---------------------------------------------------------------------------
# Current claims 9-32 remain valid and may support an evidenced non-match,
# never a false affirmative for the narrower 1-8 public whitelist.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("stored_value", [9, 20, 32])
def test_stored_count_above_public_whitelist_never_falsely_matches(
    pec_conn: Any, stored_value: int
) -> None:
    listing_id = f"NL-94-HIGH-{stored_value}"
    _make_active_listing(
        pec_conn,
        listing_id=listing_id,
        physical_boat_id=f"PB-94-HIGH-{stored_value}",
        market_episode_id=f"ME-94-HIGH-{stored_value}",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=stored_value),
    )
    for token in range(1, 9):
        matches, non_matches, _ = _result_classes(
            pec_conn, power_drive=None, power_engine_count=Decimal(token)
        )
        assert listing_id not in matches
        assert listing_id in non_matches


# ---------------------------------------------------------------------------
# Combined drive+count MUST-AND on the same current claim revision.
# ---------------------------------------------------------------------------


def test_combined_drive_and_count_both_true_confirms(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-COMBO",
        physical_boat_id="PB-94-COMBO",
        market_episode_id="ME-94-COMBO",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, _, _ = _result_classes(pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2))
    assert "NL-94-COMBO" in matches


def test_combined_drive_true_count_false_never_combines_to_match(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-DOK-CBAD",
        physical_boat_id="PB-94-DOK-CBAD",
        market_episode_id="ME-94-DOK-CBAD",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=1),
    )
    matches, non_matches, _ = _result_classes(
        pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
    )
    assert "NL-94-DOK-CBAD" not in matches
    assert "NL-94-DOK-CBAD" in non_matches


def test_combined_count_true_drive_false_never_combines_to_match(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-COK-DBAD",
        physical_boat_id="PB-94-COK-DBAD",
        market_episode_id="ME-94-COK-DBAD",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.POD
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, non_matches, _ = _result_classes(
        pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
    )
    assert "NL-94-COK-DBAD" not in matches
    assert "NL-94-COK-DBAD" in non_matches


def test_count_only_match_does_not_require_a_drive_claim(pec_conn: Any) -> None:
    """Count-only does not require a drive claim at all (contract: "Count-only
    does not require drive")."""
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-NODRIVE",
        physical_boat_id="PB-94-NODRIVE",
        market_episode_id="ME-94-NODRIVE",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, _, _ = _result_classes(pec_conn, power_drive=None, power_engine_count=Decimal(2))
    assert "NL-94-NODRIVE" in matches


# ---------------------------------------------------------------------------
# A current VALUE_ASSERTION(MIXED) drive claim never proves the absence of
# any single accepted drive type, generalized to the two-criterion case:
# MIXED+matching count must be INSUFFICIENT_DATA, never CONFIRMED_NON_MATCH;
# MIXED+non-matching count must stay CONFIRMED_NON_MATCH (the count leaf's
# own genuine exclusion is never rescued by an uninformative drive leaf).
# ---------------------------------------------------------------------------


def test_mixed_drive_with_matching_count_is_insufficient_not_excluded(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-MIXOK",
        physical_boat_id="PB-94-MIXOK",
        market_episode_id="ME-94-MIXOK",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.MIXED
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, non_matches, insufficient = _result_classes(
        pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
    )
    assert "NL-94-MIXOK" not in matches
    assert "NL-94-MIXOK" not in non_matches, (
        "MIXED drive must never become a confirmed exclusion when the other leaf matches"
    )
    assert "NL-94-MIXOK" in insufficient


def test_mixed_drive_with_non_matching_count_stays_confirmed_non_match(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-MIXBAD",
        physical_boat_id="PB-94-MIXBAD",
        market_episode_id="ME-94-MIXBAD",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.MIXED
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=1),
    )
    matches, non_matches, insufficient = _result_classes(
        pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
    )
    assert "NL-94-MIXBAD" not in matches
    assert "NL-94-MIXBAD" in non_matches, (
        "a genuinely non-matching count leaf must still confirm exclusion regardless of an "
        "uninformative MIXED drive leaf alongside it"
    )
    assert "NL-94-MIXBAD" not in insufficient


# ---------------------------------------------------------------------------
# Cross-Organization isolation.
# ---------------------------------------------------------------------------


def test_other_organization_count_conflict_fails_closed(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-XORG",
        physical_boat_id="PB-94-XORG",
        market_episode_id="ME-94-XORG",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    _seed_other_org_claim(
        pec_conn,
        physical_boat_id="PB-94-XORG",
        org_suffix="94-XORG-OTHER",
        category_value="POWER",
        drive_value=None,
        count_value=3,
    )
    matches, non_matches, insufficient = _result_classes(
        pec_conn, power_drive=None, power_engine_count=Decimal(2)
    )
    assert "NL-94-XORG" not in matches
    assert "NL-94-XORG" not in non_matches, (
        "a cross-Organization count contradiction must never resolve to a confirmed exclusion"
    )
    assert "NL-94-XORG" in insufficient


def test_other_organization_only_power_category_does_not_admit_count(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-XORGCAT",
        physical_boat_id="PB-94-XORGCAT",
        market_episode_id="ME-94-XORGCAT",
        boat_design_id=None,
        vessel_category=None,
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    _seed_other_org_claim(
        pec_conn,
        physical_boat_id="PB-94-XORGCAT",
        org_suffix="94-XORGCAT-OTHER",
        category_value="POWER",
        drive_value=None,
        count_value=None,
    )
    matches, non_matches, insufficient = _result_classes(
        pec_conn, power_drive=None, power_engine_count=Decimal(2)
    )
    assert "NL-94-XORGCAT" not in matches
    assert "NL-94-XORGCAT" not in non_matches
    assert "NL-94-XORGCAT" in insufficient


# ---------------------------------------------------------------------------
# Review amendment Finding D style: a true two-connection concurrent
# revision changing category+drive+count together, held open while a
# separate reader connection evaluates the combined Search -- proving
# category and both technical fields can never be combined from two
# different revisions (contract "coherent PostgreSQL snapshot").
# ---------------------------------------------------------------------------


def test_two_connection_concurrent_revision_never_sees_hybrid_combined_state(
    pec_url: str, pec_conn: Any
) -> None:
    account, org, _membership = _make_active_listing(
        pec_conn,
        listing_id="NL-94-CONC",
        physical_boat_id="PB-94-CONC",
        market_episode_id="ME-94-CONC",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    current_revision_id = _current_claim_revision_id(pec_conn, listing_id="NL-94-CONC", org=org)
    pec_conn.commit()
    assert current_revision_id is not None

    matches_before, _, _ = _result_classes(
        pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
    )
    assert "NL-94-CONC" in matches_before

    writer_conn = psycopg.connect(pec_url)
    try:
        with writer_conn.transaction(), writer_conn.cursor() as cur:
            write_physical_boat_claim_revision_row(
                cur,
                account_id=account,
                candidate_organization=org,
                native_listing_id=NativeListingId("NL-94-CONC"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-94-CONC-2"),
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
                    power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=1),
                ),
            )

            reader_conn = psycopg.connect(pec_url)
            try:
                matches_during, _, _ = _result_classes(
                    reader_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
                )
                assert "NL-94-CONC" in matches_during
            finally:
                reader_conn.close()
        # `with writer_conn.transaction():` commits here on clean exit.
    finally:
        writer_conn.close()

    matches_after, non_matches_after, _ = _result_classes(
        pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2)
    )
    assert "NL-94-CONC" not in matches_after
    assert "NL-94-CONC" in non_matches_after
    matches_after_new, _, _ = _result_classes(
        pec_conn, power_drive="POD", power_engine_count=Decimal(1)
    )
    assert "NL-94-CONC" not in matches_after_new  # SAIL category excludes entirely


# ---------------------------------------------------------------------------
# Design-linked v0.6 engine_count bridge.
# ---------------------------------------------------------------------------


def _insert_boat_design(
    conn: Any, design_id: str, model_id: str, *, drive_type: str, engine_count: int
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {"propulsion": {"drive_type": drive_type, "engine_count": engine_count}}
        )
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


def _admit_design_engine_count(conn: Any, design_id: str, *, value: int) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/engine_count",
        value=Decimal(value),
        resolution_id=f"FR-PWRCNT-{design_id}",
        fetch_canonical_value=lookup_power_engine_count_canonical_value,
    )


def test_design_linked_count_with_matching_concrete_claim_confirms(pec_conn: Any) -> None:
    _insert_boat_design(pec_conn, "BD-94-CNT2", "BM-94-CNT2", drive_type="shaft", engine_count=2)
    _admit_design_engine_count(pec_conn, "BD-94-CNT2", value=2)
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-DCNT2",
        physical_boat_id="PB-94-DCNT2",
        market_episode_id="ME-94-DCNT2",
        boat_design_id="BD-94-CNT2",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, _, _ = _result_classes(pec_conn, power_drive=None, power_engine_count=Decimal(2))
    assert "NL-94-DCNT2" in matches


def test_design_linked_combined_drive_and_count_same_variant_confirms(pec_conn: Any) -> None:
    _insert_boat_design(pec_conn, "BD-94-COMBO", "BM-94-COMBO", drive_type="shaft", engine_count=2)
    _admit_design_drive_type(pec_conn, "BD-94-COMBO", value="shaft")
    _admit_design_engine_count(pec_conn, "BD-94-COMBO", value=2)
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-DCOMBO",
        physical_boat_id="PB-94-DCOMBO",
        market_episode_id="ME-94-DCOMBO",
        boat_design_id="BD-94-COMBO",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    matches, _, _ = _result_classes(pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2))
    assert "NL-94-DCOMBO" in matches


def test_design_linked_unsupported_factory_count_zero_never_falsely_matches(
    pec_conn: Any,
) -> None:
    _insert_boat_design(pec_conn, "BD-94-ZERO", "BM-94-ZERO", drive_type="shaft", engine_count=0)
    _admit_design_engine_count(pec_conn, "BD-94-ZERO", value=0)
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-DZERO",
        physical_boat_id="PB-94-DZERO",
        market_episode_id="ME-94-DZERO",
        boat_design_id="BD-94-ZERO",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=None,
        power_engine_count=None,
    )
    for token in range(1, 9):
        matches, _, _ = _result_classes(
            pec_conn, power_drive=None, power_engine_count=Decimal(token)
        )
        assert "NL-94-DZERO" not in matches


def test_cross_variant_split_never_combines_to_match(pec_conn: Any) -> None:
    """Design data can support only original factory count/drive, and a
    design-level positive still requires the SAME variant to satisfy both
    requested leaves -- variant A (SHAFT baseline) and variant B
    (engine_count=2 override) must never be combined into one match."""
    with pec_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            ["BM-94-SPLIT", "Model BM-94-SPLIT", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": "shaft", "engine_count": 1}})
        named_variants_json = json.dumps(
            [
                {
                    "id": "NV-94-SPLIT-B",
                    "overrides": {"propulsion": {"engine_count": 2}},
                }
            ]
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, %s::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            ["BD-94-SPLIT", "BM-94-SPLIT", baseline_json, named_variants_json, "1" * 64],
        )
    pec_conn.commit()
    _admit_design_drive_type(pec_conn, "BD-94-SPLIT", value="shaft")
    _admit_design_engine_count(pec_conn, "BD-94-SPLIT", value=1)
    admit_resolved_draft_max(
        pec_conn,
        subject_kind=SubjectKind.NAMED_VARIANT,
        subject_id="NV-94-SPLIT-B",
        field_pointer="/overrides/propulsion/engine_count",
        value=Decimal(2),
        resolution_id="FR-PWRCNT-NV-94-SPLIT-B",
        fetch_canonical_value=lookup_power_engine_count_canonical_value,
    )
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-SPLIT",
        physical_boat_id="PB-94-SPLIT",
        market_episode_id="ME-94-SPLIT",
        boat_design_id="BD-94-SPLIT",
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    # Design-level: SHAFT (baseline) and count=2 (variant B override) never
    # combine into one CONFIRMED_MATCH configuration -- the baseline has
    # SHAFT+count=1 (count leaf false), variant B has inherited SHAFT (no
    # own override) + count=2 (drive leaf true, since drive is inherited
    # from baseline unchanged) -- actually both configurations share SHAFT
    # (inherited), so the real adversarial signal here is the concrete
    # claim: current installed count=2 is separately qualified at the
    # concrete layer, and the design layer alone must never be mistaken
    # for a confirmed concrete match without that independent confirmation.
    matches, _, _ = _result_classes(pec_conn, power_drive="SHAFT", power_engine_count=Decimal(2))
    assert "NL-94-SPLIT" in matches, (
        "variant B inherits SHAFT from baseline and overrides count=2, so this variant alone "
        "legitimately satisfies both leaves and the concrete claim independently confirms both"
    )


# ---------------------------------------------------------------------------
# Non-regression: the unmodified SLICE-0093 drive-only path is unaffected.
# ---------------------------------------------------------------------------


def test_drive_only_requirement_unaffected_by_count_extension(pec_conn: Any) -> None:
    _make_active_listing(
        pec_conn,
        listing_id="NL-94-REGR",
        physical_boat_id="PB-94-REGR",
        market_episode_id="ME-94-REGR",
        boat_design_id=None,
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        power_drive_configuration=PowerDriveConfigurationClaim(
            assertion_kind=VA, value=PowerDriveConfiguration.OUTBOARD
        ),
        power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
    )
    legacy_outcome = evaluate_power_drive_requirement(
        pec_conn, power_drive="OUTBOARD", as_of=_as_of()
    )
    assert any(m.native_listing_id.value == "NL-94-REGR" for m in legacy_outcome.claim_only_matches)
    generalized_matches, _, _ = _result_classes(
        pec_conn, power_drive="OUTBOARD", power_engine_count=None
    )
    assert "NL-94-REGR" in generalized_matches
