"""PostgreSQL-backed candidate-performance proof for the combined Power
drive+engine-count query -- SLICE-0094 independent-review amendment
Finding C.

The READY contract requires a retained real PostgreSQL 18 performance/
EXPLAIN benchmark for the new *combined* Power query, not merely a re-run
of the unmodified SLICE-0093 single-criterion numbers (which
`tests/persistence/test_power_inventory_query_performance_slice_0093.py`
already retains, unchanged). Two separate, honestly-labeled measurements,
mirroring that file's identical methodology:

1. The design-UNRESOLVED (claim-only) plane at 0/40/200, combined
   `power_drive=SHAFT&power_engine_count=2` -- proving the batched
   claim-observation read (`list_current_physical_boat_claim_observations_for_many`)
   is still called at most ONCE per evaluation regardless of population
   size: SLICE-0094 added a field to the *same* already-batched claim row,
   never a second per-criterion read, so this plane's O(1)/batched
   character is structurally unaffected by the second criterion.
2. The design-LINKED plane at 0/10, combined query -- explicitly measuring
   and reporting the ADDITIONAL per-design cost the combined criterion
   introduces: `evaluate_power_design_linked_candidates` now calls
   `run_mixed_boat_design_configuration_query`, which invokes each ACTIVE
   `CriterionDefinition.design_set_builder` once per design (two calls --
   one per criterion -- for a combined query, vs. one for the unmodified
   single-criterion SLICE-0093 path) before merging. This plane was
   already honestly O(N)/per-candidate in SLICE-0093; this file measures
   the real, concrete delta the second criterion adds on top of that,
   never claiming the combined path becomes O(1).

A full 0/40/200 design-linked population is not attempted here, for the
identical reason SLICE-0093's own performance proof gives: each candidate
requires a real admitted BoatDesign FieldResolution (now for *two* fields),
making a 200-candidate population prohibitively slow to seed for this
bounded internal synthetic proof. The pre-real-data/pilot production-scale
STOP (issue #355) remains explicitly OPEN regardless of either measurement.

Amendment Round 2, Finding C2: the controlling
`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` "Executable acceptance
proof" section requires "Real 0/40/200 mixed Sail+Power synthetic
inventory and PostgreSQL EXPLAIN/statement count evidence" -- Round 1's
file already seeded a genuinely mixed Sail+Power population
(`_seed_claim_only_population`'s POWER-match/POWER-non-match/SAIL split)
but only ever ran the combined query against it. This round adds a direct
count-only/drive-only/combined comparison against the IDENTICAL seeded
population (never three separately-seeded populations), plus EXPLAIN
evidence for the count-only and drive-only shapes (combined's own EXPLAIN
was already retained) -- completing the contract's three-way comparison
requirement. Issue #355 remains explicitly OPEN regardless.

Mirrors `test_power_inventory_query_performance_slice_0093.py`'s own
disposable-schema isolation and measurement-helper pattern (deliberately
duplicated rather than cross-imported -- established repo convention).
"""

from __future__ import annotations

import json
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application import power_inventory_query
from hullq.application.power_inventory_query import evaluate_power_requirement
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
from hullq.search.power_drive_design_bridge import lookup_power_drive_canonical_value
from hullq.search.power_engine_count_design_bridge import (
    lookup_power_engine_count_canonical_value,
)

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

VA = AssertionKind.VALUE_ASSERTION

_CLAIM_ONLY_POPULATION_SIZES = (0, 40, 200)
_DESIGN_LINKED_POPULATION_SIZES = (0, 10)


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
    schema_name = f"hullq_s0094perf_{uuid.uuid4().hex[:16]}"
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
    conn: Any,
    *,
    index: int,
    vessel_category: VesselCategoryClaim | None,
    power_drive_configuration: PowerDriveConfigurationClaim | None,
    power_engine_count: PowerEngineCountClaim | None,
    other_org_vessel_category: VesselCategoryClaim | None = None,
) -> str:
    listing_id = f"NL-94PERF-{index:04d}"
    physical_boat_id = f"PB-94PERF-{index:04d}"
    market_episode_id = f"ME-94PERF-{index:04d}"
    account = AccountId(f"ACC-94PERF-{index:04d}")
    org = _org(f"ORG-94PERF-{index:04d}")
    membership = _membership(org, account, f"OM-94PERF-{index:04d}")

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
        revision_id=NativeListingOfferRevisionId(f"REV-94PERF-{index:04d}"),
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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-94PERF-{index:04d}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
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

    if other_org_vessel_category is not None:
        other_account = AccountId(f"ACC-94PERF-{index:04d}-OTHER")
        other_org = _org(f"ORG-94PERF-{index:04d}-OTHER")
        other_membership = _membership(other_org, other_account, f"OM-94PERF-{index:04d}-OTHER")
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(f"ME-94PERF-{index:04d}-OTHER"),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        create_native_listing(
            conn,
            account_id=other_account,
            candidate_organization=other_org,
            membership=other_membership,
            listing=NativeListing(
                id=NativeListingId(f"NL-94PERF-{index:04d}-OTHER"),
                market_episode_id=MarketEpisodeId(f"ME-94PERF-{index:04d}-OTHER"),
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=other_account,
            candidate_organization=other_org,
            membership=other_membership,
            native_listing_id=NativeListingId(f"NL-94PERF-{index:04d}-OTHER"),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-94PERF-{index:04d}-OTHER"),
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


class _CapturingCursor:
    def __init__(self, inner: Any, captured: list[tuple[str, Any]]) -> None:
        self._inner = inner
        self._captured = captured

    def __enter__(self) -> _CapturingCursor:
        self._inner.__enter__()
        return self

    def __exit__(self, *exc_info: Any) -> None:
        self._inner.__exit__(*exc_info)

    def execute(self, query: Any, params: Any = None, *args: Any, **kwargs: Any) -> Any:
        self._captured.append((query, params))
        return self._inner.execute(query, params, *args, **kwargs)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._inner, name)


class _CapturingConnProxy:
    def __init__(self, conn: Any) -> None:
        self._conn = conn
        self.captured: list[tuple[str, Any]] = []

    def cursor(self, *args: Any, **kwargs: Any) -> _CapturingCursor:
        return _CapturingCursor(self._conn.cursor(*args, **kwargs), self.captured)

    def __getattr__(self, name: str) -> Any:
        return getattr(self._conn, name)


def _explain_analyze_buffers(conn: Any, query: str, params: Any) -> str:
    """Real PostgreSQL 18 `EXPLAIN (ANALYZE, BUFFERS)` for one captured
    `(query, params)` pair, replayed on the same connection/schema the
    population was actually seeded on -- genuine measured planner/execution
    evidence, never a hand-written or imagined plan."""
    with conn.cursor() as cur:
        cur.execute(f"EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT) {query}", params)
        return "\n".join(row[0] for row in cur.fetchall())


# ---------------------------------------------------------------------------
# 1. Design-unresolved (claim-only) plane -- 0/40/200, combined query,
#    still bounded/batched (SLICE-0094 added a field to the same already-
#    batched claim row, never a second per-criterion read).
# ---------------------------------------------------------------------------


def _seed_claim_only_population(
    conn: Any, population_size: int
) -> tuple[set[str], set[str], set[str]]:
    """40% publisher-owned POWER+SHAFT+count=2 -> CONFIRMED_MATCH; 20%
    publisher-owned POWER+SHAFT+count=1 (drive matches, count does not)
    -> CONFIRMED_NON_MATCH; 20% publisher-owned SAIL -> CONFIRMED_NON_MATCH
    (category exclusion); 10% no category claim at all -> INSUFFICIENT_DATA;
    10% POWER claimed only by a different Organization -> INSUFFICIENT_DATA."""
    expected_match_ids: set[str] = set()
    expected_non_match_ids: set[str] = set()
    expected_insufficient_ids: set[str] = set()
    if population_size == 0:
        return expected_match_ids, expected_non_match_ids, expected_insufficient_ids

    match_count = round(population_size * 0.4)
    non_match_count_count = round(population_size * 0.2)
    non_match_sail_count = round(population_size * 0.2)
    insufficient_no_category_count = round(population_size * 0.1)
    insufficient_other_org_count = population_size - (
        match_count + non_match_count_count + non_match_sail_count + insufficient_no_category_count
    )

    index = 0
    for _ in range(match_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
        )
        expected_match_ids.add(listing_id)
    for _ in range(non_match_count_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=1),
        )
        expected_non_match_ids.add(listing_id)
    for _ in range(non_match_sail_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            power_drive_configuration=None,
            power_engine_count=None,
        )
        expected_non_match_ids.add(listing_id)
    for _ in range(insufficient_no_category_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=None,
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
        )
        expected_insufficient_ids.add(listing_id)
    for _ in range(insufficient_other_org_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=None,
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
            other_org_vessel_category=VesselCategoryClaim(
                assertion_kind=VA, value=VesselCategory.POWER
            ),
        )
        expected_insufficient_ids.add(listing_id)

    assert index == population_size
    conn.commit()
    return expected_match_ids, expected_non_match_ids, expected_insufficient_ids


@pytest.mark.parametrize("population_size", _CLAIM_ONLY_POPULATION_SIZES)
def test_claim_only_combined_power_population_performance(
    perf_conn: Any, population_size: int
) -> None:
    expected_match_ids, expected_non_match_ids, expected_insufficient_ids = (
        _seed_claim_only_population(perf_conn, population_size)
    )
    any_candidates = bool(expected_match_ids or expected_non_match_ids or expected_insufficient_ids)

    # Proof 1: the batched claims-observation read is still called at most
    # ONCE per evaluation, independent of population size -- SLICE-0094
    # added a column to the SAME already-batched row, never a second
    # per-criterion statement.
    from unittest.mock import patch

    with patch.object(
        power_inventory_query,
        "list_current_physical_boat_claim_observations_for_many",
        wraps=power_inventory_query.list_current_physical_boat_claim_observations_for_many,
    ) as batched_spy:
        outcome = evaluate_power_requirement(
            perf_conn, power_drive="SHAFT", power_engine_count=Decimal(2), as_of=_as_of()
        )
    expected_batched_calls = 1 if any_candidates else 0
    assert batched_spy.call_count == expected_batched_calls, (
        f"expected {expected_batched_calls} batched claims-observation statement(s) for "
        f"{population_size} candidates, got {batched_spy.call_count}"
    )

    # Proof 2: no valid candidate silently dropped.
    actual_match_ids = {m.native_listing_id.value for m in outcome.claim_only_matches}
    actual_non_match_ids = {m.native_listing_id.value for m in outcome.claim_only_non_matches}
    actual_insufficient_ids = {
        m.native_listing_id.value for m in outcome.claim_only_insufficient_data
    }
    assert actual_match_ids == expected_match_ids
    assert actual_non_match_ids == expected_non_match_ids
    assert actual_insufficient_ids == expected_insufficient_ids
    assert len(actual_match_ids | actual_non_match_ids | actual_insufficient_ids) == population_size

    # Proof 3: real, measured total SQL round-trip count + elapsed time for
    # the COMBINED query, directly comparable to SLICE-0093's own retained
    # single-criterion numbers at the same population sizes.
    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    outcome2 = evaluate_power_requirement(
        proxy, power_drive="SHAFT", power_engine_count=Decimal(2), as_of=_as_of()
    )
    elapsed_seconds = time.monotonic() - start
    assert len(outcome2.claim_only_matches) == len(expected_match_ids)
    total_queries = proxy.query_count[0]
    print(
        f"\n[SLICE-0094 Finding C claim-only COMBINED measured evidence] "
        f"population={population_size} candidates, total_sql_statements={total_queries}, "
        f"elapsed_seconds={elapsed_seconds:.3f}, "
        f"statements_per_candidate={(total_queries / population_size) if population_size else 0:.2f}"
    )
    if population_size == 0:
        assert total_queries < 5, (
            f"expected a small constant statement count for an empty population, "
            f"got {total_queries}"
        )
    else:
        assert total_queries < population_size * 12, (
            f"expected a linear-bounded statement count for {population_size} candidates, "
            f"got {total_queries} total statements "
            f"({total_queries / population_size:.2f} per candidate)"
        )


def test_claim_only_combined_batched_observations_query_plan_evidence(perf_conn: Any) -> None:
    """Real PostgreSQL 18 `EXPLAIN (ANALYZE, BUFFERS)` for the
    representative batched claim-observation statement, combined query, at
    the largest claim-only population this slice measures (200
    candidates)."""
    population_size = 200
    _seed_claim_only_population(perf_conn, population_size)

    proxy = _CapturingConnProxy(perf_conn)
    evaluate_power_requirement(
        proxy, power_drive="SHAFT", power_engine_count=Decimal(2), as_of=_as_of()
    )

    batched_calls = [
        (query, params)
        for query, params in proxy.captured
        if "physical_boat_claim_heads" in query and "= ANY(%s)" in query
    ]
    assert len(batched_calls) == 1, (
        f"expected exactly one batched claim-observation statement for {population_size} "
        f"candidates, captured {len(batched_calls)}"
    )
    query, params = batched_calls[0]
    plan = _explain_analyze_buffers(perf_conn, query, params)
    print(
        f"\n[SLICE-0094 Finding C claim-only COMBINED batched-observations EXPLAIN, "
        f"population={population_size}]\n{plan}"
    )
    assert "Execution Time" in plan


# ---------------------------------------------------------------------------
# Amendment Round 2, Finding C2: the controlling
# `specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` "Executable acceptance
# proof" section requires a retained "Real 0/40/200 mixed Sail+Power
# synthetic inventory and PostgreSQL EXPLAIN/statement count evidence" --
# not merely the combined query alone, but a genuine count-only/drive-only/
# combined COMPARISON against the *same* seeded mixed population (the
# `_seed_claim_only_population` above already mixes POWER-match,
# POWER-non-match, SAIL and insufficient-data candidates together). This
# directly answers the Round 1 gap: the old SLICE-0093 drive-only benchmark
# was a *separate* population/file, never a same-population comparison.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("population_size", _CLAIM_ONLY_POPULATION_SIZES)
def test_claim_only_count_only_drive_only_combined_comparison_same_mixed_population(
    perf_conn: Any, population_size: int
) -> None:
    """Round 2 Finding C2: run count-only, drive-only and combined queries
    against the IDENTICAL seeded mixed Sail+Power population, reporting
    real matched/non-matched/insufficient counts and statement counts for
    each -- never three separately-seeded populations that could hide a
    population-shape difference as if it were a query-shape difference.

    Expected retained-match-evidence shape on this fixture's exact 40/20/20
    split: count-only (`power_engine_count=2`) matches only the 40%
    SHAFT+count=2 group; drive-only (`power_drive=SHAFT`) matches BOTH the
    40% SHAFT+count=2 group AND the 20% SHAFT+count=1 group (count is
    irrelevant to a pure drive query); combined matches only their
    intersection, the same 40% group both narrower queries agree on.
    """
    _seed_claim_only_population(perf_conn, population_size)
    match_count = round(population_size * 0.4)
    non_match_drive_still_matches_count = round(population_size * 0.2)

    results: dict[str, tuple[int, int]] = {}
    for label, kwargs in (
        ("count-only", {"power_drive": None, "power_engine_count": Decimal(2)}),
        ("drive-only", {"power_drive": "SHAFT", "power_engine_count": None}),
        ("combined", {"power_drive": "SHAFT", "power_engine_count": Decimal(2)}),
    ):
        proxy = _CountingConnProxy(perf_conn)
        outcome = evaluate_power_requirement(proxy, as_of=_as_of(), **kwargs)
        results[label] = (len(outcome.claim_only_matches), proxy.query_count[0])

    if population_size == 0:
        expected_matches = {"count-only": 0, "drive-only": 0, "combined": 0}
    else:
        expected_matches = {
            "count-only": match_count,
            "drive-only": match_count + non_match_drive_still_matches_count,
            "combined": match_count,
        }
    for label, expected_count in expected_matches.items():
        actual_count, statements = results[label]
        assert actual_count == expected_count, (
            f"{label} query against the {population_size}-candidate mixed population: "
            f"expected {expected_count} matches, got {actual_count}"
        )
        print(
            f"\n[SLICE-0094 Finding C2 same-population comparison] population={population_size}, "
            f"query={label}, matches={actual_count}, total_sql_statements={statements}"
        )
    # The retained evidence itself: drive-only is strictly the broader
    # query on this fixture (it also accepts the count-mismatched group),
    # so it must never match FEWER listings than the narrower count-only
    # or combined queries against the identical population.
    if population_size > 0:
        assert results["drive-only"][0] >= results["count-only"][0]
        assert results["drive-only"][0] >= results["combined"][0]
        assert results["combined"][0] == results["count-only"][0]


def test_claim_only_count_only_and_drive_only_batched_observations_query_plan_evidence(
    perf_conn: Any,
) -> None:
    """Round 2 Finding C2: real PostgreSQL 18 `EXPLAIN (ANALYZE, BUFFERS)`
    for the representative batched claim-observation statement under the
    count-only and drive-only query shapes too (combined is already proven
    above) -- at the same 200-candidate mixed population, completing the
    three-way EXPLAIN/statement-count comparison the contract requires."""
    population_size = 200
    _seed_claim_only_population(perf_conn, population_size)

    for label, kwargs in (
        ("count-only", {"power_drive": None, "power_engine_count": Decimal(2)}),
        ("drive-only", {"power_drive": "SHAFT", "power_engine_count": None}),
    ):
        proxy = _CapturingConnProxy(perf_conn)
        evaluate_power_requirement(proxy, as_of=_as_of(), **kwargs)
        batched_calls = [
            (query, params)
            for query, params in proxy.captured
            if "physical_boat_claim_heads" in query and "= ANY(%s)" in query
        ]
        assert len(batched_calls) == 1, (
            f"{label}: expected exactly one batched claim-observation statement for "
            f"{population_size} candidates, captured {len(batched_calls)}"
        )
        query, params = batched_calls[0]
        plan = _explain_analyze_buffers(perf_conn, query, params)
        print(
            f"\n[SLICE-0094 Finding C2 {label} batched-observations EXPLAIN, "
            f"population={population_size}]\n{plan}"
        )
        assert "Execution Time" in plan


# ---------------------------------------------------------------------------
# 2. Design-linked plane -- 0/10, combined query. Explicitly measures the
#    ADDITIONAL per-design cost the second criterion introduces on top of
#    SLICE-0093's own already-accepted O(N)/per-candidate shape.
# ---------------------------------------------------------------------------


def _insert_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": "shaft", "engine_count": 2}})
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()


def _seed_design_linked_candidate(conn: Any, *, index: int) -> str:
    design_id = f"BD-94PERF-{index:04d}"
    model_id = f"BM-94PERF-{index:04d}"
    listing_id = f"NL-94PERFD-{index:04d}"
    physical_boat_id = f"PB-94PERFD-{index:04d}"
    market_episode_id = f"ME-94PERFD-{index:04d}"
    account = AccountId(f"ACC-94PERFD-{index:04d}")
    org = _org(f"ORG-94PERFD-{index:04d}")
    membership = _membership(org, account, f"OM-94PERFD-{index:04d}")

    _insert_boat_design(conn, design_id, model_id)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/drive_type",
        value="shaft",
        resolution_id=f"FR-94PERFD-DRV-{index:04d}",
        fetch_canonical_value=lookup_power_drive_canonical_value,
    )
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/engine_count",
        value=Decimal(2),
        resolution_id=f"FR-94PERFD-CNT-{index:04d}",
        fetch_canonical_value=lookup_power_engine_count_canonical_value,
    )
    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(design_id)
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
        revision_id=NativeListingOfferRevisionId(f"REV-94PERFD-{index:04d}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic design-linked performance-benchmark listing.",
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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-94PERFD-{index:04d}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic Design-Linked Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
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


@pytest.mark.parametrize("population_size", _DESIGN_LINKED_POPULATION_SIZES)
def test_design_linked_combined_power_population_performance(
    perf_conn: Any, population_size: int
) -> None:
    expected_match_ids = {
        _seed_design_linked_candidate(perf_conn, index=i) for i in range(1, population_size + 1)
    }
    if population_size:
        perf_conn.commit()

    # Measure the COMBINED query's total statement count.
    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    outcome = evaluate_power_requirement(
        proxy, power_drive="SHAFT", power_engine_count=Decimal(2), as_of=_as_of()
    )
    elapsed_seconds = time.monotonic() - start
    actual_match_ids = {m.native_listing_id.value for m in outcome.design_linked_matches}
    assert actual_match_ids == expected_match_ids
    combined_total_queries = proxy.query_count[0]

    # Measure the SAME population's unmodified SLICE-0093 drive-only
    # statement count, for a direct, real (not estimated) delta -- the
    # concrete "additional per-design work introduced by the combined
    # criterion" the independent review asked for.
    from hullq.application.power_inventory_query import evaluate_power_drive_requirement

    drive_only_proxy = _CountingConnProxy(perf_conn)
    evaluate_power_drive_requirement(drive_only_proxy, power_drive="SHAFT", as_of=_as_of())
    drive_only_total_queries = drive_only_proxy.query_count[0]

    print(
        f"\n[SLICE-0094 Finding C design-linked COMBINED measured evidence] "
        f"population={population_size} candidates, "
        f"combined_total_sql_statements={combined_total_queries}, "
        f"drive_only_total_sql_statements={drive_only_total_queries}, "
        f"additional_statements_from_second_criterion="
        f"{combined_total_queries - drive_only_total_queries}, "
        f"elapsed_seconds={elapsed_seconds:.3f}, "
        f"statements_per_candidate="
        f"{(combined_total_queries / population_size) if population_size else 0:.2f} -- this "
        "plane remains explicitly O(N)/per-candidate (unchanged from SLICE-0093); the combined "
        "query's own `run_mixed_boat_design_configuration_query` calls each active criterion's "
        "design_set_builder once per design (two calls instead of one) before merging, so the "
        "measured delta above is the genuine, bounded per-design cost the second criterion adds "
        "-- never claimed to be free, and never claimed to make this plane O(1). Issue #355's "
        "pre-real-data/pilot production-scale STOP remains OPEN regardless of these synthetic "
        "numbers."
    )
    if population_size == 0:
        assert combined_total_queries < 5
    else:
        # Linear-bounded (never quadratic): a generous per-candidate
        # ceiling, not an invented production SLA. Allow headroom above
        # SLICE-0093's own ceiling since the combined query does genuinely
        # more per-design work.
        assert combined_total_queries < population_size * 24, (
            f"expected a linear-bounded statement count for {population_size} design-linked "
            f"candidates, got {combined_total_queries} total statements "
            f"({combined_total_queries / population_size:.2f} per candidate)"
        )
        # The combined query must never be CHEAPER than the drive-only
        # query against the identical population/connection (it does
        # strictly more work: two design_set_builder calls per design
        # instead of one, plus the same per-candidate concrete
        # classification) -- a lower count here would indicate the second
        # criterion's design-side evaluation was silently skipped.
        assert combined_total_queries >= drive_only_total_queries, (
            f"the combined query ({combined_total_queries} statements) must never be cheaper "
            f"than the unmodified drive-only query ({drive_only_total_queries} statements) "
            f"against the identical {population_size}-candidate population"
        )


def test_design_linked_combined_category_drive_count_snapshot_query_plan_evidence(
    perf_conn: Any,
) -> None:
    """Real PostgreSQL 18 `EXPLAIN (ANALYZE, BUFFERS)` plan for the
    representative per-candidate combined category+drive+count snapshot
    statement (`fetch_power_category_drive_snapshot`, now also projecting
    `power_engine_count_*`) at this slice's design-linked population (10
    candidates)."""
    population_size = 10
    for i in range(1, population_size + 1):
        _seed_design_linked_candidate(perf_conn, index=i)
    perf_conn.commit()

    proxy = _CapturingConnProxy(perf_conn)
    evaluate_power_requirement(
        proxy, power_drive="SHAFT", power_engine_count=Decimal(2), as_of=_as_of()
    )

    snapshot_calls = [
        (query, params)
        for query, params in proxy.captured
        if "boat_design_category_assertion_heads" in query
        and "power_drive_configuration_assertion_kind" in query
        and "power_engine_count_assertion_kind" in query
    ]
    assert len(snapshot_calls) == population_size, (
        f"expected exactly one combined category+drive+count snapshot statement per candidate "
        f"({population_size} candidates), captured {len(snapshot_calls)}"
    )
    query, params = snapshot_calls[0]
    plan = _explain_analyze_buffers(perf_conn, query, params)
    print(
        f"\n[SLICE-0094 Finding C design-linked combined category+drive+count-snapshot EXPLAIN, "
        f"one of {population_size} per-candidate statements]\n{plan}"
    )
    assert "Execution Time" in plan
