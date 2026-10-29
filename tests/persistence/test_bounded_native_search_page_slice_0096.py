"""PostgreSQL-backed end-to-end tests for the SLICE-0096 bounded, paginated
native technical Search retrieval.

Covers the HIGH_RISK mechanical invariants the normative contract
(`specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md`) and READY
slice require:

1. `hullq.persistence.inventory_search.list_active_native_listing_candidates_page`
   merges BOTH source planes in one global `NativeListingId` order, honors
   its bounded `limit`, and `active_native_listing_candidate_exists_after`
   is a correct O(1) existence proof.
2. Full-traversal equivalence: paging through
   `evaluate_native_inventory_requirements_page`/`evaluate_power_requirement_page`
   recovers EXACTLY the same confirmed-match identity set as the existing,
   already-reviewed unbounded evaluators, for Sail pure-draft, Sail mixed
   (draft+keel), Power drive-only and Power combined (drive+count).
3. PARTIAL/COMPLETE state-machine correctness: a zero-match page still
   advances the cursor and reports PARTIAL; the exact-fill ("final batch
   happens to fill the page exactly") ambiguity is resolved by the O(1)
   lookahead, never a guess; page_size validation (1/20/50 valid, 0/51
   invalid).
4. A listing withdrawn between two pages of the same traversal never
   leaks a stale confirmed match on the later page.

Candidate seeding deliberately reuses the same minimal
physical_boat/market_episode/native_listing/offer/cover/publish envelope
`tests/persistence/test_native_inventory_query.py` and
`tests/persistence/test_power_inventory_query_performance_slice_0093.py`
already establish -- this file focuses on the NEW bounded/paging layer, not
re-proving per-criterion technical truth the existing non-paginated test
suite already covers in depth.
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
from hullq.application.native_inventory_query import (
    SearchPageEvaluationState,
    evaluate_native_inventory_requirements,
    evaluate_native_inventory_requirements_page,
)
from hullq.application.power_inventory_query import (
    evaluate_power_drive_requirement,
    evaluate_power_requirement,
    evaluate_power_requirement_page,
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
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
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
from hullq.persistence.inventory_search import (
    active_native_listing_candidate_exists_after,
    list_active_native_listing_candidates_page,
)
from hullq.persistence.market_episode import create_market_episode, fetch_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing, fetch_native_listing
from hullq.persistence.native_listing_lifecycle import (
    publish_native_listing,
    withdraw_native_listing,
)
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
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

VA = AssertionKind.VALUE_ASSERTION

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
def page_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0096page_{uuid.uuid4().hex[:16]}"
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
def page_conn(page_url: str) -> Generator[Any]:
    conn = psycopg.connect(page_url)
    try:
        yield conn
    finally:
        conn.close()


def _as_of() -> datetime:
    return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Domain/fixture helpers (mirrors test_native_inventory_query.py /
# test_power_inventory_query_performance_slice_0093.py)
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
    initial_claims: PhysicalBoatClaimSnapshot | None = None,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    """Create one ACTIVE candidate (design-linked when *boat_design_id* is
    not `None`, design-unresolved/claim-only otherwise) with the minimum
    D29-eligible envelope. *initial_claims* lets a caller seed the
    publisher's own claim in the same revision `publish_native_listing`
    requires to exist, rather than a separate post-publish revision --
    `None` (the default) means NO claim beyond the mandatory brand/model/
    build_year placeholder, which is deliberately insufficient for every
    category/criterion (used for the always-`INSUFFICIENT_DATA` filler
    candidates below).
    """
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
            broker_description="Synthetic SLICE-0096 bounded-page fixture listing.",
            asking_price_amount=Decimal("90000.00"),
            currency="EUR",
        ),
    )
    claims = initial_claims or PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Unbranded",
        model_designation_claim="Synthetic Model",
        build_year=BuildYearClaim(assertion_kind=VA, value=2015),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
        expected_current_revision_id=None,
        claims=claims,
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
    claims: PhysicalBoatClaimSnapshot,
) -> None:
    expected_current_revision_id = _current_claim_revision_id(conn, listing_id=listing_id, org=org)
    conn.commit()
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}-R2"),
        expected_current_revision_id=expected_current_revision_id,
        claims=claims,
    )
    assert result.status.value in ("created", "revised"), result


def _insert_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    baseline_keel_type: str,
    baseline_draft_max_m: float,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "dimensions": {"draft_max_m": baseline_draft_max_m},
                "appendages": {"keel_type": baseline_keel_type},
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


def _admit_design_keel_and_draft(
    conn: Any, design_id: str, *, keel_type: str, draft_max_m: Decimal
) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=draft_max_m,
        resolution_id=f"FR-DRAFT-{design_id}",
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value=keel_type,
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )


# ---------------------------------------------------------------------------
# 1. Persistence layer: bounded merged-plane candidate page
# ---------------------------------------------------------------------------


def test_bounded_page_merges_both_planes_in_global_order(page_conn: Any) -> None:
    """Design-linked and claim-only candidates interleaved by NativeListingId
    must come back from ONE bounded query in exactly that global order, each
    correctly tagged by `boat_design_ref` presence -- never two independently
    paginated planes concatenated."""
    design_id, model_id = "BD-0096-MERGE", "BM-0096-MERGE"
    _insert_boat_design(
        page_conn, design_id, model_id, baseline_keel_type="fin", baseline_draft_max_m=1.3
    )
    _admit_design_keel_and_draft(page_conn, design_id, keel_type="fin", draft_max_m=Decimal("1.30"))

    expected_design_linked: set[str] = set()
    expected_claim_only: set[str] = set()
    # Odd-indexed ids are design-linked, even-indexed are claim-only --
    # interleaved by construction, lexicographic native_listing_id order
    # matches creation index order (zero-padded).
    for index in range(1, 9):
        listing_id = f"NL-0096-MERGE-{index:04d}"
        is_design_linked = index % 2 == 1
        _make_active_listing(
            page_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-0096-MERGE-{index:04d}",
            market_episode_id=f"ME-0096-MERGE-{index:04d}",
            boat_design_id=design_id if is_design_linked else None,
        )
        if is_design_linked:
            expected_design_linked.add(listing_id)
        else:
            expected_claim_only.add(listing_id)

    full_batch = list_active_native_listing_candidates_page(
        page_conn, after_native_listing_id=None, limit=100
    )
    assert [c.native_listing_id.value for c in full_batch] == sorted(
        expected_design_linked | expected_claim_only
    )
    for candidate in full_batch:
        if candidate.native_listing_id.value in expected_design_linked:
            assert candidate.boat_design_ref is not None
            assert candidate.boat_design_ref.value == design_id
        else:
            assert candidate.boat_design_ref is None

    # Bounded traversal in small pages recovers the identical full set with
    # no gaps/duplicates.
    traversed: list[str] = []
    after: str | None = None
    for _ in range(20):
        page = list_active_native_listing_candidates_page(
            page_conn, after_native_listing_id=after, limit=3
        )
        if not page:
            break
        traversed.extend(c.native_listing_id.value for c in page)
        after = page[-1].native_listing_id.value
    assert traversed == [c.native_listing_id.value for c in full_batch]
    assert len(traversed) == len(set(traversed))


def test_candidate_exists_after_is_correct_bounded_existence_proof(page_conn: Any) -> None:
    for index in range(1, 4):
        _make_active_listing(
            page_conn,
            listing_id=f"NL-0096-EXISTS-{index:04d}",
            physical_boat_id=f"PB-0096-EXISTS-{index:04d}",
            market_episode_id=f"ME-0096-EXISTS-{index:04d}",
            boat_design_id=None,
        )
    assert active_native_listing_candidate_exists_after(page_conn, "NL-0096-EXISTS-0001") is True
    assert active_native_listing_candidate_exists_after(page_conn, "NL-0096-EXISTS-0002") is True
    assert active_native_listing_candidate_exists_after(page_conn, "NL-0096-EXISTS-0003") is False
    # A sentinel far beyond every real id also correctly reports no more rows.
    assert active_native_listing_candidate_exists_after(page_conn, "NL-0096-EXISTS-9999") is False


# ---------------------------------------------------------------------------
# 2. Full-traversal equivalence vs the existing unbounded reference
#    evaluators -- Sail pure-draft, Sail mixed, Power drive-only, Power
#    combined.
# ---------------------------------------------------------------------------


def _traverse_all_sail_pages(
    conn: Any,
    *,
    draft_max: Decimal | None,
    keel_configuration: str | None,
    page_size: int,
    candidate_scan_budget: int,
) -> tuple[set[str], set[str], list[str]]:
    """Page through the entire bounded traversal, returning
    (design_linked_match_ids, claim_only_match_ids, evaluation_states_seen)."""
    design_linked_ids: set[str] = set()
    claim_only_ids: set[str] = set()
    states: list[str] = []
    after: str | None = None
    for _ in range(200):
        page = evaluate_native_inventory_requirements_page(
            conn,
            draft_max=draft_max,
            keel_configuration=keel_configuration,
            as_of=_as_of(),
            after_native_listing_id=after,
            page_size=page_size,
            candidate_scan_budget=candidate_scan_budget,
        )
        states.append(page.evaluation_state.value)
        for match in page.confirmed_matches:
            assert match.native_listing_id.value not in design_linked_ids, (
                "duplicate confirmed match"
            )
            design_linked_ids.add(match.native_listing_id.value)
        for match in page.claim_only_matches:
            assert match.native_listing_id.value not in claim_only_ids, "duplicate claim-only match"
            claim_only_ids.add(match.native_listing_id.value)
        if page.evaluation_state is SearchPageEvaluationState.COMPLETE:
            break
        after = page.next_after_native_listing_id
    else:
        raise AssertionError("traversal did not complete within 200 pages")
    return design_linked_ids, claim_only_ids, states


def test_sail_pure_draft_bounded_traversal_matches_unbounded_reference(page_conn: Any) -> None:
    design_id, model_id = "BD-0096-DRAFT", "BM-0096-DRAFT"
    _insert_boat_design(
        page_conn, design_id, model_id, baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(page_conn, design_id, keel_type="fin", draft_max_m=Decimal("1.30"))

    # Design-linked: #1/#2 shallow enough (match), #3 too deep (non-match).
    for index, draft in ((1, "1.10"), (2, "1.20"), (3, "1.90")):
        listing_id = f"NL-0096-DRAFT-DL-{index:04d}"
        account, org, membership = _make_active_listing(
            page_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-0096-DRAFT-DL-{index:04d}",
            market_episode_id=f"ME-0096-DRAFT-DL-{index:04d}",
            boat_design_id=design_id,
        )
        _revise_claim(
            page_conn,
            account=account,
            org=org,
            membership=membership,
            listing_id=listing_id,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Synthetic",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                draft=DraftClaim(assertion_kind=VA, value=Decimal(draft)),
            ),
        )

    # Claim-only (design-UNRESOLVED): publisher-owned SAIL + shallow draft (match).
    listing_id = "NL-0096-DRAFT-CO-0001"
    account, org, membership = _make_active_listing(
        page_conn,
        listing_id=listing_id,
        physical_boat_id="PB-0096-DRAFT-CO-0001",
        market_episode_id="ME-0096-DRAFT-CO-0001",
        boat_design_id=None,
    )
    _revise_claim(
        page_conn,
        account=account,
        org=org,
        membership=membership,
        listing_id=listing_id,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            draft=DraftClaim(assertion_kind=VA, value=Decimal("1.00")),
        ),
    )
    # Insufficient-data filler candidate (no claim at all beyond placeholder).
    _make_active_listing(
        page_conn,
        listing_id="NL-0096-DRAFT-FILLER-0001",
        physical_boat_id="PB-0096-DRAFT-FILLER-0001",
        market_episode_id="ME-0096-DRAFT-FILLER-0001",
        boat_design_id=None,
    )

    reference = evaluate_draft_max_requirement(page_conn, Decimal("1.60"), as_of=_as_of())
    expected_design_linked = {m.native_listing_id.value for m in reference.confirmed_matches}
    expected_claim_only = {m.native_listing_id.value for m in reference.claim_only_matches}
    assert expected_design_linked == {"NL-0096-DRAFT-DL-0001", "NL-0096-DRAFT-DL-0002"}
    assert expected_claim_only == {"NL-0096-DRAFT-CO-0001"}

    # Tiny budgets force a genuinely multi-page traversal.
    design_linked_ids, claim_only_ids, states = _traverse_all_sail_pages(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        page_size=1,
        candidate_scan_budget=2,
    )
    assert design_linked_ids == expected_design_linked
    assert claim_only_ids == expected_claim_only
    assert states[-1] == "COMPLETE"
    assert states.count("PARTIAL") >= 1, "a tiny budget over 5 candidates must genuinely page"


def test_sail_mixed_draft_keel_bounded_traversal_matches_unbounded_reference(
    page_conn: Any,
) -> None:
    design_id, model_id = "BD-0096-MIXED", "BM-0096-MIXED"
    _insert_boat_design(
        page_conn, design_id, model_id, baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(page_conn, design_id, keel_type="fin", draft_max_m=Decimal("1.30"))

    def _seed(index: int, *, draft: str, keel: str) -> None:
        listing_id = f"NL-0096-MIXED-{index:04d}"
        account, org, membership = _make_active_listing(
            page_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-0096-MIXED-{index:04d}",
            market_episode_id=f"ME-0096-MIXED-{index:04d}",
            boat_design_id=design_id,
        )
        _revise_claim(
            page_conn,
            account=account,
            org=org,
            membership=membership,
            listing_id=listing_id,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Synthetic",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                draft=DraftClaim(assertion_kind=VA, value=Decimal(draft)),
                keel_configuration=KeelConfigurationClaim(
                    assertion_kind=VA, value=KeelConfiguration(keel)
                ),
            ),
        )

    _seed(1, draft="1.10", keel="FIN")  # joint match
    _seed(2, draft="1.10", keel="WING")  # keel FALSE -> non-match
    _seed(3, draft="1.90", keel="FIN")  # draft FALSE -> non-match
    _seed(4, draft="1.20", keel="FIN")  # joint match

    reference = evaluate_native_inventory_requirements(
        page_conn, draft_max=Decimal("1.60"), keel_configuration="FIN", as_of=_as_of()
    )
    expected = {m.native_listing_id.value for m in reference.confirmed_matches}
    assert expected == {"NL-0096-MIXED-0001", "NL-0096-MIXED-0004"}

    design_linked_ids, claim_only_ids, states = _traverse_all_sail_pages(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration="FIN",
        page_size=1,
        candidate_scan_budget=3,
    )
    assert design_linked_ids == expected
    assert claim_only_ids == set()
    assert states[-1] == "COMPLETE"


def _traverse_all_power_pages(
    conn: Any,
    *,
    power_drive: str | None,
    power_engine_count: Decimal | None,
    page_size: int,
    candidate_scan_budget: int,
) -> tuple[set[str], set[str], list[str]]:
    design_linked_ids: set[str] = set()
    claim_only_ids: set[str] = set()
    states: list[str] = []
    after: str | None = None
    for _ in range(200):
        page = evaluate_power_requirement_page(
            conn,
            power_drive=power_drive,
            power_engine_count=power_engine_count,
            as_of=_as_of(),
            after_native_listing_id=after,
            page_size=page_size,
            candidate_scan_budget=candidate_scan_budget,
        )
        states.append(page.evaluation_state.value)
        for match in page.design_linked_matches:
            assert match.native_listing_id.value not in design_linked_ids
            design_linked_ids.add(match.native_listing_id.value)
        for match in page.claim_only_matches:
            assert match.native_listing_id.value not in claim_only_ids
            claim_only_ids.add(match.native_listing_id.value)
        if page.evaluation_state is SearchPageEvaluationState.COMPLETE:
            break
        after = page.next_after_native_listing_id
    else:
        raise AssertionError("Power traversal did not complete within 200 pages")
    return design_linked_ids, claim_only_ids, states


def test_power_drive_only_bounded_traversal_matches_unbounded_reference(page_conn: Any) -> None:
    def _seed_claim_only(
        index: int, *, drive: PowerDriveConfiguration | None, category: VesselCategory | None
    ) -> str:
        listing_id = f"NL-0096-PWRD-{index:04d}"
        _make_active_listing(
            page_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-0096-PWRD-{index:04d}",
            market_episode_id=f"ME-0096-PWRD-{index:04d}",
            boat_design_id=None,
            initial_claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Synthetic",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                vessel_category=(
                    VesselCategoryClaim(assertion_kind=VA, value=category)
                    if category is not None
                    else None
                ),
                power_drive_configuration=(
                    PowerDriveConfigurationClaim(assertion_kind=VA, value=drive)
                    if drive is not None
                    else None
                ),
            ),
        )
        return listing_id

    match_id = _seed_claim_only(
        1, drive=PowerDriveConfiguration.SHAFT, category=VesselCategory.POWER
    )
    _seed_claim_only(
        2, drive=PowerDriveConfiguration.POD, category=VesselCategory.POWER
    )  # non-match
    _seed_claim_only(
        3, drive=PowerDriveConfiguration.SHAFT, category=VesselCategory.SAIL
    )  # excluded
    _seed_claim_only(4, drive=None, category=None)  # insufficient

    reference = evaluate_power_drive_requirement(page_conn, power_drive="SHAFT", as_of=_as_of())
    expected = {m.native_listing_id.value for m in reference.claim_only_matches}
    assert expected == {match_id}

    design_linked_ids, claim_only_ids, states = _traverse_all_power_pages(
        page_conn,
        power_drive="SHAFT",
        power_engine_count=None,
        page_size=1,
        candidate_scan_budget=2,
    )
    assert claim_only_ids == expected
    assert design_linked_ids == set()
    assert states[-1] == "COMPLETE"


def test_power_combined_drive_and_count_bounded_traversal_matches_unbounded_reference(
    page_conn: Any,
) -> None:
    """Combined `power_drive` + `power_engine_count` on the claim-only
    (design-UNRESOLVED) plane -- this never requires a design-level
    `power_engine_count` FieldResolution admission at all (unlike a
    design-linked match, which the design-linked test above already covers
    for the single-criterion case), so it isolates the MUST-AND combination
    itself.
    """

    def _seed_claim_only(index: int, *, engine_count: int | None, drive_matches: bool) -> str:
        listing_id = f"NL-0096-PWRC-{index:04d}"
        _make_active_listing(
            page_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-0096-PWRC-{index:04d}",
            market_episode_id=f"ME-0096-PWRC-{index:04d}",
            boat_design_id=None,
            initial_claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Synthetic",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
                power_drive_configuration=PowerDriveConfigurationClaim(
                    assertion_kind=VA,
                    value=PowerDriveConfiguration.SHAFT
                    if drive_matches
                    else PowerDriveConfiguration.POD,
                ),
                power_engine_count=(
                    PowerEngineCountClaim(assertion_kind=VA, value=engine_count)
                    if engine_count is not None
                    else None
                ),
            ),
        )
        return listing_id

    match_id = _seed_claim_only(1, engine_count=2, drive_matches=True)
    _seed_claim_only(2, engine_count=1, drive_matches=True)  # count FALSE -> non-match
    _seed_claim_only(3, engine_count=2, drive_matches=False)  # drive FALSE -> non-match

    reference = evaluate_power_requirement(
        page_conn, power_drive="SHAFT", power_engine_count=Decimal("2"), as_of=_as_of()
    )
    expected = {m.native_listing_id.value for m in reference.claim_only_matches}
    assert expected == {match_id}

    design_linked_ids, claim_only_ids, states = _traverse_all_power_pages(
        page_conn,
        power_drive="SHAFT",
        power_engine_count=Decimal("2"),
        page_size=1,
        candidate_scan_budget=1,
    )
    assert claim_only_ids == expected
    assert design_linked_ids == set()
    assert states[-1] == "COMPLETE"


# ---------------------------------------------------------------------------
# 3. PARTIAL/COMPLETE state-machine correctness
# ---------------------------------------------------------------------------


def test_zero_match_page_is_partial_and_advances_cursor(page_conn: Any) -> None:
    """A bounded scan whose entire batch is INSUFFICIENT_DATA (zero matches)
    must still report PARTIAL with a cursor that advances -- never a false
    empty-COMPLETE, and never a non-advancing loop."""
    for index in range(1, 6):
        _make_active_listing(
            page_conn,
            listing_id=f"NL-0096-ZERO-{index:04d}",
            physical_boat_id=f"PB-0096-ZERO-{index:04d}",
            market_episode_id=f"ME-0096-ZERO-{index:04d}",
            boat_design_id=None,
        )

    page1 = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=20,
        candidate_scan_budget=2,
    )
    assert page1.confirmed_match_count == 0
    assert page1.claim_only_match_count == 0
    assert page1.claim_only_insufficient_data_count == 2
    assert page1.evaluation_state is SearchPageEvaluationState.PARTIAL
    assert page1.next_after_native_listing_id == "NL-0096-ZERO-0002"

    page2 = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=page1.next_after_native_listing_id,
        page_size=20,
        candidate_scan_budget=2,
    )
    assert page2.evaluation_state is SearchPageEvaluationState.PARTIAL
    assert page2.next_after_native_listing_id == "NL-0096-ZERO-0004"

    page3 = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=page2.next_after_native_listing_id,
        page_size=20,
        candidate_scan_budget=2,
    )
    assert page3.evaluation_state is SearchPageEvaluationState.COMPLETE
    assert page3.next_after_native_listing_id is None


def test_exact_fill_batch_triggers_lookahead_before_declaring_complete(page_conn: Any) -> None:
    """When the fetched batch exactly fills candidate_scan_budget and every
    row is evaluated, COMPLETE may only be declared after the O(1) existence
    lookahead proves no further candidate exists -- never inferred merely
    from 'the batch size equaled the limit'."""
    for index in range(1, 6):
        _make_active_listing(
            page_conn,
            listing_id=f"NL-0096-FILL-{index:04d}",
            physical_boat_id=f"PB-0096-FILL-{index:04d}",
            market_episode_id=f"ME-0096-FILL-{index:04d}",
            boat_design_id=None,
        )

    # Exactly 5 ACTIVE candidates, budget=5: batch fills the limit exactly
    # and nothing remains beyond it -> COMPLETE, proven by lookahead.
    page = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=20,
        candidate_scan_budget=5,
    )
    assert page.evaluation_state is SearchPageEvaluationState.COMPLETE
    assert page.next_after_native_listing_id is None

    # Add a 6th candidate beyond the first 5 -- the identical budget=5 fetch
    # now exact-fills again, but this time one more genuinely exists.
    # evaluate_native_inventory_requirements_page's own reads leave *page_conn*
    # mid-transaction (psycopg autocommit=False); the persistence writers
    # below require IDLE so they can safely own their own top-level
    # transaction.
    page_conn.commit()
    _make_active_listing(
        page_conn,
        listing_id="NL-0096-FILL-0006",
        physical_boat_id="PB-0096-FILL-0006",
        market_episode_id="ME-0096-FILL-0006",
        boat_design_id=None,
    )
    page_again = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=20,
        candidate_scan_budget=5,
    )
    assert page_again.evaluation_state is SearchPageEvaluationState.PARTIAL
    assert page_again.next_after_native_listing_id == "NL-0096-FILL-0005"

    final_page = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=page_again.next_after_native_listing_id,
        page_size=20,
        candidate_scan_budget=5,
    )
    assert final_page.evaluation_state is SearchPageEvaluationState.COMPLETE
    assert final_page.next_after_native_listing_id is None


@pytest.mark.parametrize("page_size", [1, 20, 50])
def test_valid_page_sizes_accepted(page_conn: Any, page_size: int) -> None:
    _make_active_listing(
        page_conn,
        listing_id="NL-0096-PSIZE-0001",
        physical_boat_id="PB-0096-PSIZE-0001",
        market_episode_id="ME-0096-PSIZE-0001",
        boat_design_id=None,
    )
    page = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=page_size,
        candidate_scan_budget=max(page_size, 10),
    )
    assert page.evaluation_state is SearchPageEvaluationState.COMPLETE


@pytest.mark.parametrize("page_size", [0, 51, -1])
def test_invalid_page_sizes_rejected(page_conn: Any, page_size: int) -> None:
    with pytest.raises(ValueError):
        evaluate_native_inventory_requirements_page(
            page_conn,
            draft_max=Decimal("1.60"),
            keel_configuration=None,
            as_of=_as_of(),
            after_native_listing_id=None,
            page_size=page_size,
        )


# ---------------------------------------------------------------------------
# 4. Concurrent withdrawal between pages never leaks a stale match
# ---------------------------------------------------------------------------


def test_withdrawn_listing_between_pages_never_leaks_stale_match(page_conn: Any) -> None:
    design_id, model_id = "BD-0096-WITHDRAW", "BM-0096-WITHDRAW"
    _insert_boat_design(
        page_conn, design_id, model_id, baseline_keel_type="fin", baseline_draft_max_m=1.30
    )
    _admit_design_keel_and_draft(page_conn, design_id, keel_type="fin", draft_max_m=Decimal("1.30"))

    accounts: dict[str, tuple[Any, Any, Any]] = {}
    for index in (1, 2):
        listing_id = f"NL-0096-WITHDRAW-{index:04d}"
        account, org, membership = _make_active_listing(
            page_conn,
            listing_id=listing_id,
            physical_boat_id=f"PB-0096-WITHDRAW-{index:04d}",
            market_episode_id=f"ME-0096-WITHDRAW-{index:04d}",
            boat_design_id=design_id,
        )
        accounts[listing_id] = (account, org, membership)
        _revise_claim(
            page_conn,
            account=account,
            org=org,
            membership=membership,
            listing_id=listing_id,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Synthetic",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                draft=DraftClaim(assertion_kind=VA, value=Decimal("1.10")),
            ),
        )

    page1 = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=1,
        candidate_scan_budget=1,
    )
    assert [m.native_listing_id.value for m in page1.confirmed_matches] == ["NL-0096-WITHDRAW-0001"]
    assert page1.evaluation_state is SearchPageEvaluationState.PARTIAL

    # Withdraw the SECOND listing (not yet seen) before fetching page 2.
    account2, org2, membership2 = accounts["NL-0096-WITHDRAW-0002"]
    page_conn.commit()
    withdraw_result = withdraw_native_listing(
        page_conn,
        account_id=account2,
        candidate_organization=org2,
        membership=membership2,
        native_listing_id=NativeListingId("NL-0096-WITHDRAW-0002"),
    )
    assert withdraw_result.status.value == "transitioned", withdraw_result

    page2 = evaluate_native_inventory_requirements_page(
        page_conn,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=page1.next_after_native_listing_id,
        page_size=1,
        candidate_scan_budget=1,
    )
    assert page2.confirmed_matches == ()
    assert page2.evaluation_state is SearchPageEvaluationState.COMPLETE
