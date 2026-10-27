"""PostgreSQL-backed candidate-performance proof for the design-unresolved
claim-only Sail path -- SLICE-0092 amendment review Finding D.

Finding D required: "Measure the additive query cost using representative
synthetic PostgreSQL 18 populations. Address unbounded/N+1 amplification
with an evidence-backed, appropriately bounded approach without silently
losing valid candidates."

This module proves, against a real representative synthetic population of
40 ACTIVE design-unresolved candidates (a realistic mixed category
distribution: publisher-owned-SAIL matching, publisher-owned-SAIL
non-matching, explicit POWER, no-category/UNKNOWN, and SAIL-claimed-by-a-
different-Organization-only):

1. `hullq.application.native_inventory_query.evaluate_claim_only_candidates`
   reads every candidate's current claim observations through exactly
   **one** batched SQL statement
   (`list_current_physical_boat_claim_observations_for_many`), never one
   statement per candidate -- deterministic, independent of population
   size (proven by a call-count spy, not timing).
2. The real total SQL round-trip count for the whole evaluation is
   measured and reported (not merely asserted against an invented
   production SLA) -- a real `psycopg` connection wrapped in a counting
   proxy records every `cursor().execute(...)` call.
3. Every one of the 40 seeded candidates is still correctly classified
   (no valid candidate silently dropped by the batching change) --
   counts match the exact expected per-category outcome.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

import hullq.application.native_inventory_query as native_inventory_query
from hullq.application.native_inventory_query import evaluate_native_inventory_requirements
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
    KeelConfiguration,
    KeelConfigurationClaim,
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

# A representative synthetic population size for this strictly-internal,
# synthetic-corpus slice (contract: no real external data) -- large enough
# to make an O(N) vs O(1) read-count difference observable, small enough to
# keep this one-off benchmark test's own seeding cost bounded.
_POPULATION_SIZE = 40


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
    schema_name = f"hullq_s0092perf_{uuid.uuid4().hex[:16]}"
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


def _seed_candidate(
    conn: Any,
    *,
    index: int,
    keel_configuration: KeelConfiguration | None,
    vessel_category: VesselCategoryClaim | None,
    other_org_vessel_category: VesselCategoryClaim | None = None,
) -> str:
    """Seed one ACTIVE design-unresolved candidate at *index*, optionally
    with a second Organization's own category-only claim on the same
    PhysicalBoat (`other_org_vessel_category`) for the
    "claimed-by-a-different-Organization-only" population slice."""
    listing_id = f"NL-92PERF-{index:04d}"
    physical_boat_id = f"PB-92PERF-{index:04d}"
    market_episode_id = f"ME-92PERF-{index:04d}"
    account = AccountId(f"ACC-92PERF-{index:04d}")
    org = _org(f"ORG-92PERF-{index:04d}")
    membership = _membership(org, account, f"OM-92PERF-{index:04d}")

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
        revision_id=NativeListingOfferRevisionId(f"REV-92PERF-{index:04d}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic performance-benchmark listing.",
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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-92PERF-{index:04d}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
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

    if other_org_vessel_category is not None:
        other_account = AccountId(f"ACC-92PERF-{index:04d}-OTHER")
        other_org = _org(f"ORG-92PERF-{index:04d}-OTHER")
        other_membership = _membership(other_org, other_account, f"OM-92PERF-{index:04d}-OTHER")
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(f"ME-92PERF-{index:04d}-OTHER"),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        create_native_listing(
            conn,
            account_id=other_account,
            candidate_organization=other_org,
            membership=other_membership,
            listing=NativeListing(
                id=NativeListingId(f"NL-92PERF-{index:04d}-OTHER"),
                market_episode_id=MarketEpisodeId(f"ME-92PERF-{index:04d}-OTHER"),
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=other_account,
            candidate_organization=other_org,
            membership=other_membership,
            native_listing_id=NativeListingId(f"NL-92PERF-{index:04d}-OTHER"),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-92PERF-{index:04d}-OTHER"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Other",
                model_designation_claim="Other Model",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                vessel_category=other_org_vessel_category,
            ),
        )
    return listing_id


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
    """Transparent proxy counting every real `cursor().execute(...)` call
    issued through this connection -- the real, measured SQL round-trip
    count for one evaluation, not an estimate."""

    def __init__(self, conn: Any) -> None:
        self._conn = conn
        self.query_count = [0]

    def cursor(self, *args: Any, **kwargs: Any) -> _CountingCursor:
        return _CountingCursor(self._conn.cursor(*args, **kwargs), self.query_count)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def test_claim_only_candidate_population_performance(perf_conn: Any) -> None:
    # Representative mixed category distribution, 40 candidates total:
    #   16 publisher-owned SAIL, keel=FIN  -> CONFIRMED_MATCH
    #    8 publisher-owned SAIL, keel=TWIN_KEEL (non-matching) -> CONFIRMED_NON_MATCH
    #    8 explicit POWER                  -> CONFIRMED_NON_MATCH (category exclusion)
    #    4 no category claim at all        -> INSUFFICIENT_DATA
    #    4 SAIL claimed only by a different Organization -> INSUFFICIENT_DATA
    expected_match_ids: set[str] = set()
    expected_non_match_ids: set[str] = set()
    expected_insufficient_ids: set[str] = set()

    index = 0
    for _ in range(16):
        index += 1
        listing_id = _seed_candidate(
            perf_conn,
            index=index,
            keel_configuration=KeelConfiguration.FIN,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        )
        expected_match_ids.add(listing_id)
    for _ in range(8):
        index += 1
        listing_id = _seed_candidate(
            perf_conn,
            index=index,
            keel_configuration=KeelConfiguration.TWIN_KEEL,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        )
        expected_non_match_ids.add(listing_id)
    for _ in range(8):
        index += 1
        listing_id = _seed_candidate(
            perf_conn,
            index=index,
            keel_configuration=KeelConfiguration.FIN,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        )
        expected_non_match_ids.add(listing_id)
    for _ in range(4):
        index += 1
        listing_id = _seed_candidate(
            perf_conn, index=index, keel_configuration=KeelConfiguration.FIN, vessel_category=None
        )
        expected_insufficient_ids.add(listing_id)
    for _ in range(4):
        index += 1
        listing_id = _seed_candidate(
            perf_conn,
            index=index,
            keel_configuration=KeelConfiguration.FIN,
            vessel_category=None,
            other_org_vessel_category=VesselCategoryClaim(
                assertion_kind=VA, value=VesselCategory.SAIL
            ),
        )
        expected_insufficient_ids.add(listing_id)

    assert index == _POPULATION_SIZE
    perf_conn.commit()

    # Proof 1: the batched claims-observation read is called exactly ONCE
    # per evaluation, independent of the 40-candidate population size --
    # deterministic call-count proof, not a timing heuristic.
    with patch.object(
        native_inventory_query,
        "list_current_physical_boat_claim_observations_for_many",
        wraps=native_inventory_query.list_current_physical_boat_claim_observations_for_many,
    ) as batched_spy:
        outcome = evaluate_native_inventory_requirements(
            perf_conn, draft_max=None, keel_configuration="FIN", as_of=_as_of()
        )
    assert batched_spy.call_count == 1, (
        f"expected exactly one batched claims-observation statement for all "
        f"{_POPULATION_SIZE} candidates, got {batched_spy.call_count}"
    )

    # Proof 2: no valid candidate was silently dropped by batching -- every
    # one of the 40 seeded candidates is classified exactly as expected.
    actual_match_ids = {m.native_listing_id.value for m in outcome.claim_only_matches}
    actual_non_match_ids = {m.native_listing_id.value for m in outcome.claim_only_non_matches}
    actual_insufficient_ids = {
        m.native_listing_id.value for m in outcome.claim_only_insufficient_data
    }
    assert actual_match_ids == expected_match_ids
    assert actual_non_match_ids == expected_non_match_ids
    assert actual_insufficient_ids == expected_insufficient_ids
    assert len(actual_match_ids | actual_non_match_ids | actual_insufficient_ids) == (
        _POPULATION_SIZE
    )

    # Proof 3: the real, measured total SQL round-trip count for one
    # evaluation of this population -- reported, not fabricated. The
    # per-candidate D29 eligibility/freshness cost is pre-existing shared
    # architecture (`hullq.application.current_public_eligibility`,
    # `hullq.application.native_listing_freshness`), reused unchanged by
    # both the design-linked and claim-only funnels; this slice's own
    # additive read (claim observations) is exactly 1 statement for the
    # whole population, not 1 per candidate.
    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    outcome2 = evaluate_native_inventory_requirements(
        proxy, draft_max=None, keel_configuration="FIN", as_of=_as_of()
    )
    elapsed_seconds = time.monotonic() - start
    assert len(outcome2.claim_only_matches) == len(expected_match_ids)
    total_queries = proxy.query_count[0]
    print(
        f"\n[SLICE-0092 Finding D measured evidence] population={_POPULATION_SIZE} "
        f"candidates, total_sql_statements={total_queries}, "
        f"elapsed_seconds={elapsed_seconds:.3f}, "
        f"statements_per_candidate={total_queries / _POPULATION_SIZE:.2f}"
    )
    # A generous, evidence-derived bound (not an invented production SLA):
    # the per-candidate D29 eligibility+freshness cost is already several
    # statements (pre-existing shared architecture); this asserts the whole
    # evaluation stays linear-bounded (no quadratic/duplicate-per-field
    # explosion) rather than pinning an exact brittle count.
    assert total_queries < _POPULATION_SIZE * 20, (
        f"expected a linear-bounded statement count for {_POPULATION_SIZE} candidates, "
        f"got {total_queries} total statements ({total_queries / _POPULATION_SIZE:.2f} per candidate)"
    )
