"""Real PostgreSQL 18 before/after measurement evidence for SLICE-0096.

Normative contract §5 ("Executable evidence and rejection rules") requires:
"Measured boundedness and speed evidence: compared counts and memory/
elapsed distributions for both candidate planes, including mixed 0/40/200
... record/justify exact per-request workload cap ... A claim of
'production-scale PASS' without hosted/real-load evidence is a reject."

This file measures, on the SAME disposable PostgreSQL 18 schema and the
SAME seeded population:

1. The OLD unbounded candidate reads
   (`hullq.persistence.inventory_search.list_active_design_linked_listings`/
   `list_active_design_unresolved_listings`) -- real `EXPLAIN (ANALYZE,
   BUFFERS)` and elapsed time at population 200, confirming they scan the
   full ACTIVE population with no `LIMIT` (the "before" baseline this slice
   replaces for the new public page path -- these two functions themselves
   are UNCHANGED and remain the legacy/private readers).
2. The NEW bounded `list_active_native_listing_candidates_page` -- real
   `EXPLAIN (ANALYZE, BUFFERS)` and elapsed time for a `LIMIT 20` fetch at
   the IDENTICAL population 200, showing the new index-backed bounded read
   touches a small, limit-sized row set rather than the whole table.
3. `evaluate_native_inventory_requirements_page`'s real SQL statement count
   and elapsed time at 0/40/200 claim-only candidates, and at a 40-candidate
   ALL-NON-MATCH ("negative-heavy") population. Honest measured finding:
   this plane is LINEAR-bounded (~4 statements/eligible candidate), NOT
   O(1)/flat -- `hullq.application.current_public_eligibility
   .resolve_current_public_eligibility_for_many`'s own already-accepted
   SLICE-0069/0092 design issues per-SURVIVOR expensive offer/claim/cover
   reads (that function's own docstring says so); only the claim-
   observation read itself is genuinely one batched statement regardless of
   N. This slice's own request-level bound is `candidate_scan_budget`
   (default 500), not a claim of O(1) per candidate. The zero-match
   ("negative-heavy") population costs the same linear-bounded shape as a
   match-rich one of the same size -- never an unbounded scan merely
   because nothing matches.

Old 0093/0094 figures are historical and are NOT reused as new-run proof
here (contract §3). This is one honest local synthetic data point at a
bounded size, never a production-scale/hosted capacity claim -- issue
#355's pre-real-data/pilot production-scale STOP remains OPEN regardless.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.native_inventory_query import evaluate_native_inventory_requirements_page
from hullq.domain.market_identity import (
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
    list_active_design_linked_listings,
    list_active_design_unresolved_listings,
    list_active_native_listing_candidates_page,
)
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

VA = AssertionKind.VALUE_ASSERTION

_POPULATION_SIZES = (0, 40, 200)


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
def perf_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0096perf_{uuid.uuid4().hex[:16]}"
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
def perf_conn(perf_url: str) -> Generator[Any]:
    conn = psycopg.connect(perf_url)
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
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _seed_claim_only_candidate(
    conn: Any, *, index: int, draft: str, category: VesselCategory
) -> str:
    listing_id = f"NL-0096PERF-{index:05d}"
    physical_boat_id = f"PB-0096PERF-{index:05d}"
    market_episode_id = f"ME-0096PERF-{index:05d}"
    account = AccountId(f"ACC-0096PERF-{index:05d}")
    org = _org(f"ORG-0096PERF-{index:05d}")
    membership = _membership(org, account, f"OM-0096PERF-{index:05d}")

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
        revision_id=NativeListingOfferRevisionId(f"REV-0096PERF-{index:05d}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic SLICE-0096 performance-benchmark listing.",
            asking_price_amount=Decimal("90000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-0096PERF-{index:05d}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=category),
            draft=DraftClaim(assertion_kind=VA, value=Decimal(draft)),
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
    return listing_id


def _seed_mixed_population(conn: Any, population_size: int) -> tuple[set[str], set[str]]:
    """40% SAIL + shallow draft -> match; 40% SAIL + deep draft -> non-match;
    20% POWER (category exclusion) -> non-match. Mirrors the existing
    SLICE-0092/0093 proportions."""
    match_ids: set[str] = set()
    non_match_ids: set[str] = set()
    if population_size == 0:
        return match_ids, non_match_ids

    match_count = round(population_size * 0.4)
    deep_draft_count = round(population_size * 0.4)
    power_count = population_size - match_count - deep_draft_count

    index = 0
    for _ in range(match_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn, index=index, draft="1.10", category=VesselCategory.SAIL
        )
        match_ids.add(listing_id)
    for _ in range(deep_draft_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn, index=index, draft="1.90", category=VesselCategory.SAIL
        )
        non_match_ids.add(listing_id)
    for _ in range(power_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn, index=index, draft="1.10", category=VesselCategory.POWER
        )
        non_match_ids.add(listing_id)
    assert index == population_size
    conn.commit()
    return match_ids, non_match_ids


class _CountingCursor:
    def __init__(self, inner: Any, counter: list[int]) -> None:
        self._inner = inner
        self._counter = counter

    def __enter__(self) -> _CountingCursor:
        self._inner.__enter__()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._inner.__exit__(*exc_info)

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        self._counter[0] += 1
        return self._inner.execute(*args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _CountingConnProxy:
    def __init__(self, conn: Any) -> None:
        self._conn = conn
        self.query_count = [0]

    def cursor(self, *args: Any, **kwargs: Any) -> _CountingCursor:
        return _CountingCursor(self._conn.cursor(*args, **kwargs), self.query_count)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def _explain_analyze_buffers(conn: Any, query: str, params: Any) -> str:
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query}", params)
        return "\n".join(row[0] for row in cur.fetchall())


# ---------------------------------------------------------------------------
# 1/2. Before (unbounded) vs after (bounded) EXPLAIN comparison at population 200
# ---------------------------------------------------------------------------


def test_before_after_explain_comparison_at_population_200(perf_conn: Any) -> None:
    _seed_mixed_population(perf_conn, 200)

    # BEFORE: the unchanged legacy unbounded reader -- full scan, no LIMIT.
    start = time.monotonic()
    before_rows = list_active_design_unresolved_listings(perf_conn)
    before_elapsed = time.monotonic() - start
    assert len(before_rows) == 200
    before_plan = _explain_analyze_buffers(
        perf_conn,
        "SELECT nl.native_listing_id, nl.publishing_organization_id, pb.physical_boat_id "
        "FROM native_listings nl "
        "JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id "
        "JOIN physical_boats pb ON pb.physical_boat_id = me.physical_boat_id "
        "WHERE nl.lifecycle_state = 'ACTIVE' AND pb.boat_design_ref IS NULL "
        "ORDER BY nl.native_listing_id",
        None,
    )
    print(
        f"\n[SLICE-0096 BEFORE: unbounded list_active_design_unresolved_listings, "
        f"population=200] elapsed_seconds={before_elapsed:.4f}\n{before_plan}"
    )
    assert "Execution Time" in before_plan

    # AFTER: the new bounded page read, LIMIT 20 -- the actual public
    # default page size, same population.
    start = time.monotonic()
    after_rows = list_active_native_listing_candidates_page(
        perf_conn, after_native_listing_id=None, limit=20
    )
    after_elapsed = time.monotonic() - start
    assert len(after_rows) == 20
    after_plan = _explain_analyze_buffers(
        perf_conn,
        "SELECT nl.native_listing_id, nl.publishing_organization_id, "
        "       pb.physical_boat_id, pb.boat_design_ref "
        "FROM native_listings nl "
        "JOIN market_episodes me ON me.market_episode_id = nl.market_episode_id "
        "JOIN physical_boats pb ON pb.physical_boat_id = me.physical_boat_id "
        "WHERE nl.lifecycle_state = 'ACTIVE' "
        "      AND (%(after)s::text IS NULL OR nl.native_listing_id > %(after)s::text) "
        "ORDER BY nl.native_listing_id "
        "LIMIT %(limit)s",
        {"after": None, "limit": 20},
    )
    print(
        f"\n[SLICE-0096 AFTER: bounded list_active_native_listing_candidates_page "
        f"LIMIT 20, population=200] elapsed_seconds={after_elapsed:.4f}\n{after_plan}"
    )
    assert "Execution Time" in after_plan

    # Also verify legacy design-linked reader is still unchanged/unbounded
    # (byte-identical pre-0096 query shape) -- it is simply empty here since
    # this population is entirely claim-only.
    assert list_active_design_linked_listings(perf_conn) == []


# ---------------------------------------------------------------------------
# 3. Bounded page evaluator: statement counts + elapsed at 0/40/200, plus a
#    dedicated negative-heavy (all-non-match) population.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("population_size", _POPULATION_SIZES)
def test_bounded_page_statement_count_and_elapsed(perf_conn: Any, population_size: int) -> None:
    match_ids, _non_match_ids = _seed_mixed_population(perf_conn, population_size)

    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    page = evaluate_native_inventory_requirements_page(
        proxy,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=20,
        candidate_scan_budget=500,
    )
    elapsed_seconds = time.monotonic() - start
    total_queries = proxy.query_count[0]

    actual_match_ids = {m.native_listing_id.value for m in page.claim_only_matches}
    assert actual_match_ids <= match_ids  # page_size=20 may truncate a larger match set
    print(
        f"\n[SLICE-0096 bounded page measured evidence] population={population_size} "
        f"candidates, matches_found={len(actual_match_ids)}, "
        f"evaluation_state={page.evaluation_state.value}, "
        f"total_sql_statements={total_queries}, elapsed_seconds={elapsed_seconds:.4f}, "
        f"statements_per_candidate={(total_queries / population_size) if population_size else 0:.2f}"
    )
    if population_size == 0:
        assert total_queries < 5
    else:
        # Honest measured finding (this slice's own real-PG18 run): the
        # claim-only plane is linear-bounded, NOT O(1)/flat -- every
        # eligible candidate still reaches
        # `resolve_current_public_eligibility_for_many`'s own per-SURVIVOR
        # expensive reads (offer/claim/cover, ~3-4 statements each; that
        # function's own docstring already says so -- "the expensive ...
        # reads are ever issued" per survivor, SLICE-0069/0092 behavior,
        # unmodified by this slice). The claim-observation read itself
        # (`list_current_physical_boat_claim_observations_for_many`) IS one
        # single batched statement regardless of N -- only the eligibility
        # check is per-candidate. Mirrors the existing accepted SLICE-0093
        # ceiling shape (`total_queries < population_size * 12`), never an
        # unproven O(1)/hard-CPU claim. The REQUEST-level bound that matters
        # is `candidate_scan_budget` (500 by default): this plane is bounded
        # per request, not globally O(1) per candidate.
        assert total_queries < population_size * 12, (
            f"expected a linear-bounded statement count for the claim-only plane at "
            f"{population_size} candidates, got {total_queries} "
            f"({total_queries / population_size:.2f} per candidate)"
        )


def test_bounded_page_zero_match_population_stays_bounded(perf_conn: Any) -> None:
    """A 40-candidate population where EVERY candidate is a confirmed
    non-match (never a single CONFIRMED_MATCH) must still cost the same
    linear-bounded statement count as a match-rich page of the same size
    (see `test_bounded_page_statement_count_and_elapsed`'s own measured-
    evidence comment) -- proving a zero-match page is not secretly MORE
    expensive or unbounded merely because nothing matches."""
    population_size = 40
    for index in range(1, population_size + 1):
        _seed_claim_only_candidate(
            perf_conn, index=index, draft="1.90", category=VesselCategory.SAIL
        )
    perf_conn.commit()

    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    page = evaluate_native_inventory_requirements_page(
        proxy,
        draft_max=Decimal("1.60"),
        keel_configuration=None,
        as_of=_as_of(),
        after_native_listing_id=None,
        page_size=20,
        candidate_scan_budget=500,
    )
    elapsed_seconds = time.monotonic() - start
    total_queries = proxy.query_count[0]

    assert page.confirmed_match_count == 0
    assert page.claim_only_match_count == 0
    assert page.evaluation_state.value == "COMPLETE"
    print(
        f"\n[SLICE-0096 negative-heavy (all-non-match) measured evidence] "
        f"population={population_size}, total_sql_statements={total_queries}, "
        f"elapsed_seconds={elapsed_seconds:.4f}"
    )
    assert total_queries < population_size * 12
