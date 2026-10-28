"""PostgreSQL-backed candidate-performance proof for the Power drive
criterion -- SLICE-0093 review amendment Finding D.

Review Finding D required genuine Power-specific measurement rather than
reusing SLICE-0092's claim-only numbers: "The Power design-linked path
still does candidate-by-candidate category reads and concrete evaluations
and enumerates all ACTIVE design-linked candidates, so 0092's claim-only
performance proof cannot be quoted as 0093 proof."

Two separate, honestly-labeled measurements:

1. The design-UNRESOLVED (claim-only) plane at representative sizes
   0/40/200, mirroring 0092's identical batched-read proof methodology
   (`resolve_current_public_eligibility_for_many` +
   `list_current_physical_boat_claim_observations_for_many`, each called a
   small constant number of times regardless of population size) -- proving
   this plane is bounded/batched, exactly like the Sail claim-only plane it
   reuses.
2. The design-LINKED plane at a smaller bounded size (0/10), explicitly
   documenting that this plane is genuinely O(N) per-candidate
   (`resolve_physical_boat_vessel_category` + `classify_concrete_candidate`
   once per design-level-CONFIRMED_MATCH candidate) -- identical cost shape
   to the already-accepted SLICE-0091 Sail design-linked funnel, not a new
   regression, but explicitly NOT O(1)/batched. A full 0/40/200 design-
   linked population is not attempted here (each candidate requires a real
   admitted BoatDesign FieldResolution, making a 200-candidate population
   prohibitively slow to seed for this bounded internal synthetic proof);
   the measured 10-candidate linear-cost evidence is reported honestly
   instead of a fabricated extrapolation. The pre-real-data/pilot
   production-scale STOP (issue #355) remains explicitly OPEN regardless of
   either measurement.
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

import hullq.application.power_inventory_query as power_inventory_query
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

from ._field_resolution_support import admit_resolved_categorical_field

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
    schema_name = f"hullq_s0093perf_{uuid.uuid4().hex[:16]}"
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
    other_org_vessel_category: VesselCategoryClaim | None = None,
) -> str:
    listing_id = f"NL-93PERF-{index:04d}"
    physical_boat_id = f"PB-93PERF-{index:04d}"
    market_episode_id = f"ME-93PERF-{index:04d}"
    account = AccountId(f"ACC-93PERF-{index:04d}")
    org = _org(f"ORG-93PERF-{index:04d}")
    membership = _membership(org, account, f"OM-93PERF-{index:04d}")

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
        revision_id=NativeListingOfferRevisionId(f"REV-93PERF-{index:04d}"),
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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-93PERF-{index:04d}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
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

    if other_org_vessel_category is not None:
        other_account = AccountId(f"ACC-93PERF-{index:04d}-OTHER")
        other_org = _org(f"ORG-93PERF-{index:04d}-OTHER")
        other_membership = _membership(other_org, other_account, f"OM-93PERF-{index:04d}-OTHER")
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(f"ME-93PERF-{index:04d}-OTHER"),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        create_native_listing(
            conn,
            account_id=other_account,
            candidate_organization=other_org,
            membership=other_membership,
            listing=NativeListing(
                id=NativeListingId(f"NL-93PERF-{index:04d}-OTHER"),
                market_episode_id=MarketEpisodeId(f"ME-93PERF-{index:04d}-OTHER"),
            ),
        )
        write_physical_boat_claim_revision(
            conn,
            account_id=other_account,
            candidate_organization=other_org,
            membership=other_membership,
            native_listing_id=NativeListingId(f"NL-93PERF-{index:04d}-OTHER"),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-93PERF-{index:04d}-OTHER"),
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


# ---------------------------------------------------------------------------
# 1. Design-unresolved (claim-only) plane -- 0/40/200, bounded/batched.
# ---------------------------------------------------------------------------


def _seed_claim_only_population(
    conn: Any, population_size: int
) -> tuple[set[str], set[str], set[str]]:
    """40% publisher-owned POWER+SHAFT -> CONFIRMED_MATCH; 20% publisher-
    owned POWER+POD -> CONFIRMED_NON_MATCH; 20% publisher-owned SAIL ->
    CONFIRMED_NON_MATCH (category exclusion); 10% no category claim at all
    -> INSUFFICIENT_DATA; 10% POWER claimed only by a different
    Organization -> INSUFFICIENT_DATA."""
    expected_match_ids: set[str] = set()
    expected_non_match_ids: set[str] = set()
    expected_insufficient_ids: set[str] = set()
    if population_size == 0:
        return expected_match_ids, expected_non_match_ids, expected_insufficient_ids

    match_count = round(population_size * 0.4)
    non_match_pod_count = round(population_size * 0.2)
    non_match_sail_count = round(population_size * 0.2)
    insufficient_no_category_count = round(population_size * 0.1)
    insufficient_other_org_count = population_size - (
        match_count + non_match_pod_count + non_match_sail_count + insufficient_no_category_count
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
        )
        expected_match_ids.add(listing_id)
    for _ in range(non_match_pod_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.POD
            ),
        )
        expected_non_match_ids.add(listing_id)
    for _ in range(non_match_sail_count):
        index += 1
        listing_id = _seed_claim_only_candidate(
            conn,
            index=index,
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            power_drive_configuration=None,
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
            other_org_vessel_category=VesselCategoryClaim(
                assertion_kind=VA, value=VesselCategory.POWER
            ),
        )
        expected_insufficient_ids.add(listing_id)

    assert index == population_size
    conn.commit()
    return expected_match_ids, expected_non_match_ids, expected_insufficient_ids


@pytest.mark.parametrize("population_size", _CLAIM_ONLY_POPULATION_SIZES)
def test_claim_only_power_population_performance(perf_conn: Any, population_size: int) -> None:
    expected_match_ids, expected_non_match_ids, expected_insufficient_ids = (
        _seed_claim_only_population(perf_conn, population_size)
    )
    any_candidates = bool(expected_match_ids or expected_non_match_ids or expected_insufficient_ids)

    # Proof 1: the batched claims-observation read is called at most ONCE
    # per evaluation, independent of population size.
    from unittest.mock import patch

    with patch.object(
        power_inventory_query,
        "list_current_physical_boat_claim_observations_for_many",
        wraps=power_inventory_query.list_current_physical_boat_claim_observations_for_many,
    ) as batched_spy:
        outcome = evaluate_power_drive_requirement(perf_conn, power_drive="SHAFT", as_of=_as_of())
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

    # Proof 3: real, measured total SQL round-trip count + elapsed time.
    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    outcome2 = evaluate_power_drive_requirement(proxy, power_drive="SHAFT", as_of=_as_of())
    elapsed_seconds = time.monotonic() - start
    assert len(outcome2.claim_only_matches) == len(expected_match_ids)
    total_queries = proxy.query_count[0]
    print(
        f"\n[SLICE-0093 Finding D claim-only measured evidence] population={population_size} "
        f"candidates, total_sql_statements={total_queries}, "
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


# ---------------------------------------------------------------------------
# 2. Design-linked plane -- 0/10, explicitly NOT O(1)/batched (identical
#    cost shape to the already-accepted SLICE-0091 Sail design-linked
#    funnel; #355 production-scale STOP stays open regardless).
# ---------------------------------------------------------------------------


def _insert_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"propulsion": {"drive_type": "shaft"}})
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
    design_id = f"BD-93PERF-{index:04d}"
    model_id = f"BM-93PERF-{index:04d}"
    listing_id = f"NL-93PERFD-{index:04d}"
    physical_boat_id = f"PB-93PERFD-{index:04d}"
    market_episode_id = f"ME-93PERFD-{index:04d}"
    account = AccountId(f"ACC-93PERFD-{index:04d}")
    org = _org(f"ORG-93PERFD-{index:04d}")
    membership = _membership(org, account, f"OM-93PERFD-{index:04d}")

    _insert_boat_design(conn, design_id, model_id)
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer="/baseline/propulsion/drive_type",
        value="shaft",
        resolution_id=f"FR-93PERFD-{index:04d}",
        fetch_canonical_value=lookup_power_drive_canonical_value,
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
        revision_id=NativeListingOfferRevisionId(f"REV-93PERFD-{index:04d}"),
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
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-93PERFD-{index:04d}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic Design-Linked Model",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
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
    return listing_id


@pytest.mark.parametrize("population_size", _DESIGN_LINKED_POPULATION_SIZES)
def test_design_linked_power_population_performance(perf_conn: Any, population_size: int) -> None:
    expected_match_ids = {
        _seed_design_linked_candidate(perf_conn, index=i) for i in range(1, population_size + 1)
    }
    if population_size:
        perf_conn.commit()

    proxy = _CountingConnProxy(perf_conn)
    start = time.monotonic()
    outcome = evaluate_power_drive_requirement(proxy, power_drive="SHAFT", as_of=_as_of())
    elapsed_seconds = time.monotonic() - start
    actual_match_ids = {m.native_listing_id.value for m in outcome.design_linked_matches}
    assert actual_match_ids == expected_match_ids
    total_queries = proxy.query_count[0]
    print(
        f"\n[SLICE-0093 Finding D design-linked measured evidence] population={population_size} "
        f"candidates, total_sql_statements={total_queries}, "
        f"elapsed_seconds={elapsed_seconds:.3f}, "
        f"statements_per_candidate={(total_queries / population_size) if population_size else 0:.2f} "
        "-- this plane is explicitly O(N)/per-candidate (resolve_physical_boat_vessel_category + "
        "classify_concrete_candidate once per design-level-CONFIRMED_MATCH candidate), identical "
        "cost shape to the already-accepted SLICE-0091 Sail design-linked funnel; issue #355 "
        "pre-real-data/pilot production-scale STOP remains OPEN."
    )
    if population_size == 0:
        assert total_queries < 5
    else:
        # Linear-bounded (never quadratic): a generous per-candidate
        # ceiling, not an invented production SLA.
        assert total_queries < population_size * 20, (
            f"expected a linear-bounded statement count for {population_size} design-linked "
            f"candidates, got {total_queries} total statements "
            f"({total_queries / population_size:.2f} per candidate)"
        )
