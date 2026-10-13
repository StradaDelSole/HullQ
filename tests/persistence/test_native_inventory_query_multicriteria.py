"""PostgreSQL-backed end-to-end tests for the SLICE-0085 LOA/rudder extension
of the mixed native inventory Search funnel
(`hullq.application.native_inventory_query`).

Mirrors `tests/persistence/test_native_inventory_query.py`'s end-to-end shape
(real FieldResolution-admitted design eligibility -> ACTIVE native inventory
admission -> concrete PhysicalBoat claim classification), exercising the two
new criteria alone, combined with the two originally accepted criteria, and
the same-PhysicalBoat cross-Organization contradiction guard for each new
concrete claim field.
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
    DraftClaim,
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
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.loa_design_bridge import LOA_FIELD_POINTER, lookup_loa_canonical_value
from hullq.search.rudder_design_bridge import lookup_rudder_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_native_inventory_query.py)
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
    schema_name = f"hullq_s0085niq_{uuid.uuid4().hex[:16]}"
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
    baseline_loa_m: float,
    baseline_rudder_support: str | None = None,
    baseline_draft_max_m: float = 1.30,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "dimensions": {"draft_max_m": baseline_draft_max_m, "loa_m": baseline_loa_m},
                "appendages": {"rudder_support": baseline_rudder_support},
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


def _admit_design_loa(conn: Any, design_id: str, *, loa_m: Decimal) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=LOA_FIELD_POINTER,
        value=loa_m,
        resolution_id=f"FR-LOA-{design_id}",
        fetch_canonical_value=lookup_loa_canonical_value,
    )


def _admit_design_draft(conn: Any, design_id: str, *, draft_max_m: Decimal) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=draft_max_m,
        resolution_id=f"FR-DRAFT-{design_id}",
    )


def _admit_design_rudder_support(conn: Any, design_id: str, *, support: str) -> None:
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/appendages/rudder_support",
        value=support,
        resolution_id=f"FR-RUDDER-{design_id}",
        fetch_canonical_value=lookup_rudder_canonical_value,
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
    reuse_physical_boat: bool = False,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    if not reuse_physical_boat:
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
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
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
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
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
    draft: DraftClaim | None = None,
    loa_length: LoaLengthClaim | None = None,
    rudder_configuration: RudderConfigurationClaim | None = None,
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
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=draft,
            loa_length=loa_length,
            rudder_configuration=rudder_configuration,
        ),
    )
    assert result.status.value in ("created", "revised"), result


def _loa_value(value: str) -> LoaLengthClaim:
    return LoaLengthClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal(value))


def _rudder_value(value: str) -> RudderConfigurationClaim:
    return RudderConfigurationClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration(value)
    )


# ---------------------------------------------------------------------------
# LOA-only
# ---------------------------------------------------------------------------


def test_loa_only_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQM-1", "BM-NIQM-1", baseline_loa_m=10.50)
    _admit_design_loa(api_conn, "BD-NIQM-1", loa_m=Decimal("10.50"))
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-NIQM-1",
        physical_boat_id="PB-NIQM-1",
        market_episode_id="ME-NIQM-1",
        boat_design_id="BD-NIQM-1",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-NIQM-1",
        revision_id="REV-LOA-1",
        loa_length=_loa_value("10.50"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration=None, loa_min=Decimal("10"), as_of=_as_of()
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQM-1"}
    evidence = outcome.confirmed_matches[0].concrete_criterion_evidence[0]
    assert evidence.criterion.field == "loa_m"
    assert evidence.observed_value == Decimal("10.50")


def test_loa_range_concrete_value_outside_range_is_confirmed_non_match(api_conn: Any) -> None:
    """The DESIGN's own loa_m (12.00) satisfies the query range [10, 15], so
    the design level is a CONFIRMED_MATCH and the concrete funnel runs; the
    publisher's actual concrete loa_length (20.00) does not satisfy it ->
    CONFIRMED_NON_MATCH at the listing level (never a false design-truth
    shortcut -- design truth alone never confirms a concrete boat)."""
    _insert_boat_design(api_conn, "BD-NIQM-2", "BM-NIQM-2", baseline_loa_m=12.00)
    _admit_design_loa(api_conn, "BD-NIQM-2", loa_m=Decimal("12.00"))
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-NIQM-2",
        physical_boat_id="PB-NIQM-2",
        market_episode_id="ME-NIQM-2",
        boat_design_id="BD-NIQM-2",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-NIQM-2",
        revision_id="REV-LOA-2",
        loa_length=_loa_value("20.00"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=None,
        keel_configuration=None,
        loa_min=Decimal("10"),
        loa_max=Decimal("15"),
        as_of=_as_of(),
    )
    assert outcome.confirmed_matches == ()
    assert {m.native_listing_id.value for m in outcome.confirmed_non_matches} == {"NL-NIQM-2"}


def test_loa_cross_organization_conflict_is_insufficient_data(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-NIQM-3", "BM-NIQM-3", baseline_loa_m=10.50)
    _admit_design_loa(api_conn, "BD-NIQM-3", loa_m=Decimal("10.50"))
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-NIQM-3",
        physical_boat_id="PB-NIQM-3",
        market_episode_id="ME-NIQM-3",
        boat_design_id="BD-NIQM-3",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-NIQM-3",
        revision_id="REV-LOA-3A",
        loa_length=_loa_value("10.50"),
    )
    # A second Organization, publishing a SECOND NativeListing/MarketEpisode
    # against the SAME PhysicalBoatId, claims a materially different
    # loa_length -- the same-boat cross-Organization contradiction guard
    # must downgrade the publisher's own otherwise-confirmed value to
    # MISSING, never silently trusting the publisher alone (mirrors
    # `tests/persistence/test_native_inventory_query.py::
    # test_cross_organization_keel_contradiction_blocks_confirmed_match`).
    other_account = AccountId("ACC-NIQM-3-OTHER")
    other_org = _org("ORG-NIQM-3-OTHER")
    other_membership = _membership(other_org, other_account, "OM-NIQM-3-OTHER")
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-NIQM-3-OTHER"), physical_boat_id=PhysicalBoatId("PB-NIQM-3")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-NIQM-3-OTHER"),
            market_episode_id=MarketEpisodeId("ME-NIQM-3-OTHER"),
        ),
    )
    _write_claim(
        api_conn,
        account=other_account,
        org=other_org,
        membership=other_membership,
        listing_id="NL-NIQM-3-OTHER",
        revision_id="REV-LOA-3B",
        loa_length=_loa_value("11.00"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn, draft_max=None, keel_configuration=None, loa_min=Decimal("10"), as_of=_as_of()
    )
    assert outcome.confirmed_matches == ()
    assert {m.native_listing_id.value for m in outcome.insufficient_data} == {"NL-NIQM-3"}


# ---------------------------------------------------------------------------
# Rudder-only (v0.6 skeg support)
# ---------------------------------------------------------------------------


def test_rudder_only_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn, "BD-NIQM-4", "BM-NIQM-4", baseline_loa_m=10.0, baseline_rudder_support="skeg"
    )
    _admit_design_rudder_support(api_conn, "BD-NIQM-4", support="skeg")
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-NIQM-4",
        physical_boat_id="PB-NIQM-4",
        market_episode_id="ME-NIQM-4",
        boat_design_id="BD-NIQM-4",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-NIQM-4",
        revision_id="REV-RUDDER-1",
        rudder_configuration=_rudder_value("SKEG_HUNG"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=None,
        keel_configuration=None,
        rudder_configuration="SKEG_HUNG",
        as_of=_as_of(),
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQM-4"}


def test_rudder_only_confirmed_non_match(api_conn: Any) -> None:
    """The DESIGN's own rudder_support=skeg derives SKEG_HUNG, which satisfies
    the query (design level CONFIRMED_MATCH); the publisher's actual concrete
    rudder_configuration claim ("TRANSOM_HUNG") disagrees -> CONFIRMED_NON_MATCH
    at the listing level."""
    _insert_boat_design(
        api_conn, "BD-NIQM-5", "BM-NIQM-5", baseline_loa_m=10.0, baseline_rudder_support="skeg"
    )
    _admit_design_rudder_support(api_conn, "BD-NIQM-5", support="skeg")
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-NIQM-5",
        physical_boat_id="PB-NIQM-5",
        market_episode_id="ME-NIQM-5",
        boat_design_id="BD-NIQM-5",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-NIQM-5",
        revision_id="REV-RUDDER-2",
        rudder_configuration=_rudder_value("TRANSOM_HUNG"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=None,
        keel_configuration=None,
        rudder_configuration="SKEG_HUNG",
        as_of=_as_of(),
    )
    assert outcome.confirmed_matches == ()
    assert {m.native_listing_id.value for m in outcome.confirmed_non_matches} == {"NL-NIQM-5"}


# ---------------------------------------------------------------------------
# Mixed: draft_max AND loa AND rudder_configuration, all on one configuration
# ---------------------------------------------------------------------------


def test_mixed_draft_loa_rudder_all_confirmed(api_conn: Any) -> None:
    _insert_boat_design(
        api_conn,
        "BD-NIQM-6",
        "BM-NIQM-6",
        baseline_loa_m=10.50,
        baseline_rudder_support="skeg",
        baseline_draft_max_m=1.30,
    )
    _admit_design_draft(api_conn, "BD-NIQM-6", draft_max_m=Decimal("1.30"))
    _admit_design_loa(api_conn, "BD-NIQM-6", loa_m=Decimal("10.50"))
    _admit_design_rudder_support(api_conn, "BD-NIQM-6", support="skeg")
    account, org, membership = _make_active_listing(
        api_conn,
        listing_id="NL-NIQM-6",
        physical_boat_id="PB-NIQM-6",
        market_episode_id="ME-NIQM-6",
        boat_design_id="BD-NIQM-6",
    )
    _write_claim(
        api_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id="NL-NIQM-6",
        revision_id="REV-MIXED-1",
        draft=_draft_value("1.30"),
        loa_length=_loa_value("10.50"),
        rudder_configuration=_rudder_value("SKEG_HUNG"),
    )
    outcome = evaluate_native_inventory_requirements(
        api_conn,
        draft_max=Decimal("1.50"),
        keel_configuration=None,
        loa_min=Decimal("10"),
        loa_max=Decimal("11"),
        rudder_configuration="SKEG_HUNG",
        as_of=_as_of(),
    )
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-NIQM-6"}
    match = outcome.confirmed_matches[0]
    fields = {e.criterion.field for e in match.concrete_criterion_evidence}
    assert fields == {"draft_max_m", "loa_m", "rudder_configuration"}
    # Every criterion evaluated against the exact same resolved baseline
    # configuration (one shared ConfigurationProjection, SLICE-0085 merge).
    assert match.design_evaluation.matching_configuration_ids == ("BD-NIQM-6::baseline",)


def _draft_value(value: str) -> DraftClaim:
    return DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal(value))
