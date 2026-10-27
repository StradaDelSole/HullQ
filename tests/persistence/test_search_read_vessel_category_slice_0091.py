"""PostgreSQL-backed regression tests -- SLICE-0091 amendment Finding A.

Independent review of HEAD c28bbdd3b4ed8979816f81e8ab5a902199a9724f found
that `hullq.application.search_read.evaluate_requirement_search_outcome`
dispatches a *pure* `draft_max` request to the unmodified SLICE-0051
`hullq.application.inventory_search.evaluate_draft_max_requirement` funnel,
which never gained the SLICE-0091 category pre-filter the SLICE-0055+
`hullq.application.native_inventory_query` funnel got -- an explicit
POWER/MOTORSAILER/CONFLICT vessel could therefore still surface as a
confirmed Sail match through this second entrypoint. Proves the fix end to
end through the real accepted path, mirroring
`tests/persistence/test_inventory_search_draft_max_api.py`'s disposable-
schema/fixture pattern.
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

from hullq.application.inventory_search import evaluate_draft_max_requirement
from hullq.application.search_read import evaluate_requirement_search_outcome
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
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.provenance import ResolverKind, ResolverMetadata, SubjectKind
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
from hullq.domain.vessel_category import (
    BoatDesignCategoryAssertionId,
    DesignVesselCategoryAssertion,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.boat_design_category import (
    CATALOG_ADMISSION_SECRET_ENV_VAR,
    write_boat_design_category_assertion,
)
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
from hullq.search.draft_max_design_bridge import (
    DRAFT_MAX_FIELD_POINTER,
    lookup_draft_max_canonical_value,
)

from ._field_resolution_support import admit_resolved_draft_max

VA = AssertionKind.VALUE_ASSERTION
_TEST_ADMISSION_SECRET = "slice-0091-test-catalog-admission-secret"


@pytest.fixture(autouse=True)
def _configured_admission_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv(CATALOG_ADMISSION_SECRET_ENV_VAR, _TEST_ADMISSION_SECRET)


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
    schema_name = f"hullq_s0091sr_{uuid.uuid4().hex[:16]}"
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
# Domain/fixture helpers -- mirrors test_inventory_search_draft_max_api.py
# ---------------------------------------------------------------------------


def _insert_boat_design(conn: Any, design_id: str, model_id: str, *, draft_max_m: float) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"dimensions": {"draft_max_m": draft_max_m}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()
    # compatible_boat_design_ids requires an admitted, canonical-consistent
    # FieldResolution for draft_max_m -- a raw baseline value alone is
    # schema validity, not accepted Search truth (see
    # hullq.search.draft_max_design_bridge's module docstring).
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal(str(draft_max_m)),
        resolution_id=f"FR-DRAFTMAX-{design_id}",
        fetch_canonical_value=lookup_draft_max_canonical_value,
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
        set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )


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
    draft: Decimal,
    vessel_category: VesselCategoryClaim | None = None,
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
            broker_description="A well-maintained cruising boat.",
            asking_price_amount=Decimal("150000.00"),
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
            model_designation_claim="Oceanis 40",
            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
            draft=DraftClaim(assertion_kind=VA, value=draft),
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


def _issuer() -> ResolverMetadata:
    return ResolverMetadata(
        kind=ResolverKind.DETERMINISTIC_TOOL,
        identifier="slice-0091-test-harness",
        version="1",
    )


# ---------------------------------------------------------------------------
# Finding A: pure draft_max funnel must apply the same category pre-filter
# ---------------------------------------------------------------------------


def test_legacy_null_category_still_confirmed_match_pure_draft_max(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-91SR-LEG", "BM-91SR-LEG", draft_max_m=1.50)
    _make_active_listing(
        api_conn,
        listing_id="NL-91SR-LEG",
        physical_boat_id="PB-91SR-LEG",
        market_episode_id="ME-91SR-LEG",
        boat_design_id="BD-91SR-LEG",
        draft=Decimal("1.40"),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"), as_of=_as_of())
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-91SR-LEG"}


def test_explicit_concrete_power_excludes_pure_draft_max_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-91SR-PWR", "BM-91SR-PWR", draft_max_m=1.50)
    _make_active_listing(
        api_conn,
        listing_id="NL-91SR-PWR",
        physical_boat_id="PB-91SR-PWR",
        market_episode_id="ME-91SR-PWR",
        boat_design_id="BD-91SR-PWR",
        draft=Decimal("1.40"),
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"), as_of=_as_of())
    # Never a falsely confirmed Sail match -- the exact gap amendment
    # Finding A identified in this second (pure draft_max) Sail entrypoint.
    assert "NL-91SR-PWR" not in {m.native_listing_id.value for m in outcome.confirmed_matches}
    assert outcome.confirmed_non_match_count >= 1


def test_explicit_design_motorsailer_excludes_pure_draft_max_confirmed_match(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-91SR-MS", "BM-91SR-MS", draft_max_m=1.50)
    write_boat_design_category_assertion(
        api_conn,
        boat_design_id="BD-91SR-MS",
        assertion_id=BoatDesignCategoryAssertionId("BDCAT-91SR-MS"),
        expected_current_assertion_id=None,
        assertion=DesignVesselCategoryAssertion(
            assertion_kind=VA, value=VesselCategory.MOTORSAILER
        ),
        issuer=_issuer(),
        admission_secret=_TEST_ADMISSION_SECRET,
    )
    api_conn.commit()
    _make_active_listing(
        api_conn,
        listing_id="NL-91SR-MS",
        physical_boat_id="PB-91SR-MS",
        market_episode_id="ME-91SR-MS",
        boat_design_id="BD-91SR-MS",
        draft=Decimal("1.40"),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"), as_of=_as_of())
    assert "NL-91SR-MS" not in {m.native_listing_id.value for m in outcome.confirmed_matches}


# ---------------------------------------------------------------------------
# Finding A: the exact named dispatch point, search_read.
# evaluate_requirement_search_outcome, for a pure draft_max requirement
# ---------------------------------------------------------------------------


def test_search_read_dispatch_excludes_power_for_pure_draft_max(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-91SR-DISPATCH", "BM-91SR-DISPATCH", draft_max_m=1.50)
    _make_active_listing(
        api_conn,
        listing_id="NL-91SR-DISPATCH",
        physical_boat_id="PB-91SR-DISPATCH",
        market_episode_id="ME-91SR-DISPATCH",
        boat_design_id="BD-91SR-DISPATCH",
        draft=Decimal("1.40"),
        vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
    )
    search_outcome = evaluate_requirement_search_outcome(
        api_conn,
        draft_max=Decimal("1.6"),
        keel_configuration=None,
        as_of=_as_of(),
    )
    # evaluate_requirement_search_outcome for a pure draft_max request
    # returns the SLICE-0051 DraftMaxSearchOutcome type -- confirming the
    # exact entrypoint the independent review named is fixed.
    from hullq.application.inventory_search import DraftMaxSearchOutcome

    assert isinstance(search_outcome, DraftMaxSearchOutcome)
    assert "NL-91SR-DISPATCH" not in {
        m.native_listing_id.value for m in search_outcome.confirmed_matches
    }


def test_search_read_dispatch_still_confirms_legacy_sail(api_conn: Any) -> None:
    _insert_boat_design(api_conn, "BD-91SR-DISPATCHOK", "BM-91SR-DISPATCHOK", draft_max_m=1.50)
    _make_active_listing(
        api_conn,
        listing_id="NL-91SR-DISPATCHOK",
        physical_boat_id="PB-91SR-DISPATCHOK",
        market_episode_id="ME-91SR-DISPATCHOK",
        boat_design_id="BD-91SR-DISPATCHOK",
        draft=Decimal("1.40"),
    )
    search_outcome = evaluate_requirement_search_outcome(
        api_conn,
        draft_max=Decimal("1.6"),
        keel_configuration=None,
        as_of=_as_of(),
    )
    assert "NL-91SR-DISPATCHOK" in {
        m.native_listing_id.value for m in search_outcome.confirmed_matches
    }
