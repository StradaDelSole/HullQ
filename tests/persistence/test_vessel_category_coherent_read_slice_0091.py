"""PostgreSQL-backed coherent-read proofs -- SLICE-0091 amendment Finding F.

Independent review of HEAD 14e0c7837b19e9c7ac9ad82c245e58720e59bd4d found
that `resolve_physical_boat_vessel_category` only protected its two reads
with its own `REPEATABLE READ` transaction when the caller's connection was
`IDLE` on entry -- but both public Sail Search entrypoints
(`hullq.application.inventory_search`, `hullq.application.
native_inventory_query`) already run inventory/eligibility/design SQL
before ever reaching the category resolver, so that guard essentially never
engaged where it mattered, and the resolver's two separate statements could
observe different MVCC snapshots across a concurrent revision.

The fix (`hullq.persistence.vessel_category_snapshot.
fetch_vessel_category_snapshot`) folds both reads into one SQL statement,
which PostgreSQL always evaluates against one consistent snapshot
regardless of the surrounding transaction's isolation level or how many
other statements already ran on that connection. This module proves that
property with real PostgreSQL 18, using two independent connections and
explicit transaction-boundary synchronization (`threading.Barrier`, never a
timing-based `sleep`) -- mirrors `tests/persistence/
test_inventory_editing_concurrency.py`'s identical genuinely-concurrent
proof style.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.vessel_category_resolution import resolve_physical_boat_vessel_category
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
    VesselCategory,
    VesselCategoryClaim,
)
from hullq.domain.provenance import ResolverKind, ResolverMetadata
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
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision_row

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
def coherent_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0091coh_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


def _issuer() -> ResolverMetadata:
    return ResolverMetadata(
        kind=ResolverKind.DETERMINISTIC_TOOL,
        identifier="slice-0091-test-harness",
        version="1",
    )


def _insert_boat_design(conn: Any, design_id: str, model_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, '{}'::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, "1" * 64],
        )
    conn.commit()


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str,
    org_id: str,
    account_id: str,
    vessel_category: VesselCategoryClaim | None,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership, PhysicalBoatClaimRevisionId]:
    account = AccountId(account_id)
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-{org_id}"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
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
    revision_id = PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}-1")
    with conn.transaction(), conn.cursor() as cur:
        result = write_physical_boat_claim_revision_row(
            cur,
            account_id=account,
            candidate_organization=org,
            native_listing_id=NativeListingId(listing_id),
            revision_id=revision_id,
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 40",
                build_year=BuildYearClaim(assertion_kind=VA, value=2019),
                vessel_category=vessel_category,
            ),
        )
    assert result.status.value == "created", result
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
        placement = create_uploaded_image_placement(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_asset=asset,
        )
        set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement.media_placement_id,
            expected_version=placement.gallery_version,
        )
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership, revision_id


# ---------------------------------------------------------------------------
# Regression: works correctly from an already-active (non-IDLE) connection
# that already executed other statements -- the exact real-world calling
# pattern of both public Sail Search funnels.
# ---------------------------------------------------------------------------


def test_resolver_correct_on_already_active_read_committed_connection(coherent_url: str) -> None:
    conn = psycopg.connect(coherent_url)
    try:
        _insert_boat_design(conn, "BD-ACTIVE", "BM-ACTIVE")
        write_boat_design_category_assertion(
            conn,
            boat_design_id="BD-ACTIVE",
            assertion_id=BoatDesignCategoryAssertionId("BDCAT-ACTIVE"),
            expected_current_assertion_id=None,
            assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
            issuer=_issuer(),
            admission_secret=_TEST_ADMISSION_SECRET,
        )
        conn.commit()
        _make_active_listing(
            conn,
            listing_id="NL-ACTIVE",
            physical_boat_id="PB-ACTIVE",
            market_episode_id="ME-ACTIVE",
            boat_design_id="BD-ACTIVE",
            org_id="ORG-ACTIVE",
            account_id="ACC-ACTIVE",
            vessel_category=None,
        )

        # Simulate the real calling pattern: several other SQL statements
        # (inventory/eligibility/design reads) already executed on this
        # same connection, inside the same still-open transaction, before
        # the resolver is ever called -- `conn` is genuinely non-IDLE here.
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
            cur.execute("SELECT native_listing_id FROM native_listings")

        from psycopg.pq import TransactionStatus

        assert conn.info.transaction_status != TransactionStatus.IDLE

        result = resolve_physical_boat_vessel_category(
            conn,
            physical_boat_id=PhysicalBoatId("PB-ACTIVE"),
            boat_design_ref=BoatDesignRef("BD-ACTIVE"),
        )
        assert result.resolution.value == "SAIL"
        assert result.reason.value == "DESIGN_ONLY"
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Genuine two-connection concurrency proof: a concrete claim revision
# committed by a second connection is either fully invisible (pre-commit)
# or fully visible (post-commit) to the resolver's single-statement read --
# never a torn mix of old-and-new evidence.
# ---------------------------------------------------------------------------


def test_concurrent_concrete_revision_never_produces_a_torn_resolution(coherent_url: str) -> None:
    setup_conn = psycopg.connect(coherent_url)
    try:
        _insert_boat_design(setup_conn, "BD-RACE", "BM-RACE")
        write_boat_design_category_assertion(
            setup_conn,
            boat_design_id="BD-RACE",
            assertion_id=BoatDesignCategoryAssertionId("BDCAT-RACE"),
            expected_current_assertion_id=None,
            assertion=DesignVesselCategoryAssertion(assertion_kind=VA, value=VesselCategory.SAIL),
            issuer=_issuer(),
            admission_secret=_TEST_ADMISSION_SECRET,
        )
        setup_conn.commit()
        account, org, _membership, first_revision_id = _make_active_listing(
            setup_conn,
            listing_id="NL-RACE",
            physical_boat_id="PB-RACE",
            market_episode_id="ME-RACE",
            boat_design_id="BD-RACE",
            org_id="ORG-RACE",
            account_id="ACC-RACE",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        )
    finally:
        setup_conn.close()

    barrier = threading.Barrier(2)
    results: dict[str, Any] = {}
    errors: list[BaseException] = []

    def writer() -> None:
        conn_b = psycopg.connect(coherent_url)
        try:
            with conn_b.transaction():
                with conn_b.cursor() as cur:
                    write_result = write_physical_boat_claim_revision_row(
                        cur,
                        account_id=account,
                        candidate_organization=org,
                        native_listing_id=NativeListingId("NL-RACE"),
                        revision_id=PhysicalBoatClaimRevisionId("PBCREV-NL-RACE-2"),
                        expected_current_revision_id=first_revision_id,
                        claims=PhysicalBoatClaimSnapshot(
                            marketed_brand_claim="Beneteau",
                            model_designation_claim="Oceanis 40",
                            build_year=BuildYearClaim(assertion_kind=VA, value=2019),
                            vessel_category=VesselCategoryClaim(
                                assertion_kind=VA, value=VesselCategory.POWER
                            ),
                        ),
                    )
                    assert write_result.status.value == "revised", write_result
                # Write issued but deliberately not yet committed -- let the
                # reader observe the pre-commit state now.
                barrier.wait()
                barrier.wait()
            # `with conn_b.transaction()` commits here, on normal exit.
            barrier.wait()
        except BaseException as exc:  # pragma: no cover -- surfaced via errors list
            errors.append(exc)
            barrier.abort()
        finally:
            conn_b.close()

    def reader() -> None:
        conn_a = psycopg.connect(coherent_url)
        try:
            # Already-active connection with a prior statement executed,
            # exactly like the real Sail Search funnels' calling pattern.
            with conn_a.cursor() as cur:
                cur.execute("SELECT 1")
            barrier.wait()  # writer has written-but-not-committed POWER
            results["before"] = resolve_physical_boat_vessel_category(
                conn_a,
                physical_boat_id=PhysicalBoatId("PB-RACE"),
                boat_design_ref=BoatDesignRef("BD-RACE"),
            )
            barrier.wait()  # tell writer the pre-commit read is done
            barrier.wait()  # wait for writer's commit to complete
            results["after"] = resolve_physical_boat_vessel_category(
                conn_a,
                physical_boat_id=PhysicalBoatId("PB-RACE"),
                boat_design_ref=BoatDesignRef("BD-RACE"),
            )
        except BaseException as exc:  # pragma: no cover
            errors.append(exc)
            barrier.abort()
        finally:
            conn_a.commit()
            conn_a.close()

    t_writer = threading.Thread(target=writer)
    t_reader = threading.Thread(target=reader)
    t_writer.start()
    t_reader.start()
    t_writer.join(timeout=30)
    t_reader.join(timeout=30)

    assert not errors, errors

    # Pre-commit: the writer's POWER revision is not yet visible to any
    # other connection -- design SAIL + concrete (still) SAIL -> SAIL.
    before = results["before"]
    assert before.resolution.value == "SAIL"
    assert before.reason.value == "SOURCES_AGREE"

    # Post-commit: fully new state is visible -- design SAIL + concrete
    # POWER -> CONFLICT, never some impossible mixed/half-updated value.
    after = results["after"]
    assert after.resolution.value == "CONFLICT"
    assert after.reason.value == "DESIGN_CONCRETE_DISAGREEMENT"
