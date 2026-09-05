"""SLICE-0047 MarketEpisode persistence + NativeListing linkage owner-inspection.

Executes real PostgreSQL/Alembic behavior to demonstrate the durable
identity/linkage segment required by SLICE-0047:

    PhysicalBoat -> MarketEpisode -> NativeListing creation envelope

including MarketEpisode creation with exact typed readback, idempotent
retry, fail-closed collision semantics, fail-closed unknown-PhysicalBoat
creation, unresolved (NULL) NativeListing creation, NativeListing creation
linked to a real MarketEpisode with exact typed linked readback, fail-closed
unknown-MarketEpisode NativeListing creation, and the absence of any
post-creation mutable attach/detach API or table.

Run: uv run python scripts/inspect_market_episode_linkage.py

Requires HULLQ_TEST_DATABASE_URL to point at a local PostgreSQL 18 instance.
Runs against its own freshly created/dropped disposable PostgreSQL *schema*
(isolated via the connection ``options=-c search_path=...`` parameter), then
brings that schema from genuinely empty to the SLICE-0047 Alembic head
(SLICE-0042 baseline + physical_boat_identity + market_episode_linkage).
"""

from __future__ import annotations

import dataclasses
import sys
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg

from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
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
from hullq.persistence.connection import HULLQ_TEST_DATABASE_URL_ENV
from hullq.persistence.market_episode import (
    MarketEpisodeCreationStatus,
    MarketEpisodeRecord,
    create_market_episode,
    fetch_market_episode,
)
from hullq.persistence.native_listing import (
    NativeListingCreationStatus,
    create_native_listing,
    fetch_native_listing,
)
from hullq.persistence.physical_boat import create_physical_boat

_PHYSICAL_BOAT_ID = "PB-0047-001"
_EPISODE_ID = "ME-0047-001"
_ORG_ID = "ORG-0047"
_ACCOUNT_ID = "ACCOUNT-0047"

# The exact minimal column set the SLICE-0047 contract authorizes for
# market_episodes. Any additional column (lifecycle/status/freshness/
# seller/price/observation/continuity/dedup) would fail this structural
# check.
_EXPECTED_MARKET_EPISODE_COLUMNS = {"market_episode_id", "physical_boat_id", "created_at"}


def _base_url() -> str:
    import os

    url = os.environ.get(HULLQ_TEST_DATABASE_URL_ENV, "").strip()
    if not url:
        print(
            f"{HULLQ_TEST_DATABASE_URL_ENV} is not set. Point it at a disposable "
            "local PostgreSQL 18 instance, e.g.\n"
            f'  {HULLQ_TEST_DATABASE_URL_ENV}="postgresql://hullq_test:hullq_test@localhost:5432/hullq_test"',
            file=sys.stderr,
        )
        raise SystemExit(1)
    return url


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


def _row_count(conn: psycopg.Connection, table: str, id_column: str, id_value: str) -> int:
    with conn.cursor() as cur:
        cur.execute(f"SELECT COUNT(*) FROM {table} WHERE {id_column} = %s", [id_value])
        return int(cur.fetchone()[0])


def _actual_columns(conn: psycopg.Connection, table: str) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = %s",
            [table],
        )
        return {row[0] for row in cur.fetchall()}


def _table_names(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        )
        return {row[0] for row in cur.fetchall()}


def main() -> int:
    base_url = _base_url()
    schema_name = f"hullq_s0047_{uuid.uuid4().hex[:16]}"
    _create_schema(base_url, schema_name)
    url = _with_search_path(base_url, schema_name)

    try:
        baseline = prepare_alembic_baseline(url)
        if not baseline.accepted:
            print(f"Alembic baseline preparation failed: {baseline.reason}", file=sys.stderr)
            return 1
        alembic_upgrade_head(url)

        conn = psycopg.connect(url)
        try:
            print("MARKET EPISODE LINKAGE\n")
            ok = True

            # -- PhysicalBoat create/read --------------------------------
            boat = PhysicalBoat(id=PhysicalBoatId(_PHYSICAL_BOAT_ID))
            boat_result = create_physical_boat(conn, physical_boat=boat)
            conn.commit()
            ok &= boat_result.status.value == "created"
            print(f"PhysicalBoat create             -> {boat_result.status.value.upper()}")

            # -- MarketEpisode create/read --------------------------------
            episode = MarketEpisode(
                id=MarketEpisodeId(_EPISODE_ID), physical_boat_id=PhysicalBoatId(_PHYSICAL_BOAT_ID)
            )
            episode_result = create_market_episode(conn, market_episode=episode)
            episode_record = fetch_market_episode(conn, episode.id)
            conn.commit()
            readback_exact = episode_record is not None and episode_record.market_episode == episode
            ok &= episode_result.status is MarketEpisodeCreationStatus.CREATED and readback_exact
            print(f"MarketEpisode create             -> {episode_result.status.value.upper()}")
            print(
                f"MarketEpisode readback            -> {'EXACT' if readback_exact else 'MISMATCH'}\n"
            )

            # -- MarketEpisode identical retry -----------------------------
            retry = create_market_episode(conn, market_episode=episode)
            row_count_after_retry = _row_count(
                conn, "market_episodes", "market_episode_id", _EPISODE_ID
            )
            conn.commit()
            ok &= (
                retry.status is MarketEpisodeCreationStatus.ALREADY_EXISTS
                and row_count_after_retry == 1
            )
            print(f"MarketEpisode identical retry     -> {retry.status.value.upper()}")
            print(f"row count after retry             -> {row_count_after_retry}\n")

            # -- MarketEpisode collision ------------------------------------
            other_boat = PhysicalBoat(id=PhysicalBoatId("PB-0047-OTHER"))
            create_physical_boat(conn, physical_boat=other_boat)
            conn.commit()
            collision = create_market_episode(
                conn,
                market_episode=MarketEpisode(id=episode.id, physical_boat_id=other_boat.id),
            )
            after_collision = fetch_market_episode(conn, episode.id)
            conn.commit()
            collision_ok = (
                collision.status is MarketEpisodeCreationStatus.CONFLICT
                and after_collision is not None
                and after_collision.market_episode.physical_boat_id
                == PhysicalBoatId(_PHYSICAL_BOAT_ID)
            )
            ok &= collision_ok
            print(
                f"MarketEpisode collision (diff PhysicalBoat) -> {collision.status.value.upper()}"
            )
            print(
                f"original episode unchanged                  -> {'YES' if collision_ok else 'NO'}\n"
            )

            # -- unknown PhysicalBoat fail-closed -----------------------------
            unknown_boat_result = create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-0047-UNKNOWN-BOAT"),
                    physical_boat_id=PhysicalBoatId("PB-0047-UNKNOWN"),
                ),
            )
            unknown_boat_rows = _row_count(
                conn, "market_episodes", "market_episode_id", "ME-0047-UNKNOWN-BOAT"
            )
            conn.commit()  # end the row-count readback's implicit transaction
            ok &= (
                unknown_boat_result.status is MarketEpisodeCreationStatus.PHYSICAL_BOAT_NOT_FOUND
                and unknown_boat_rows == 0
            )
            print(
                "MarketEpisode + unknown PhysicalBoat -> "
                f"{unknown_boat_result.status.value.upper()}"
            )
            print(f"rows written                          -> {unknown_boat_rows}\n")

            # -- NativeListing unresolved creation ---------------------------
            account = AccountId(_ACCOUNT_ID)
            org = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-0047"),
                account_id=account,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            unresolved_listing = NativeListing(id=NativeListingId("NL-0047-UNRESOLVED"))
            unresolved_result = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=unresolved_listing,
            )
            unresolved_record = fetch_native_listing(conn, unresolved_listing.id)
            conn.commit()
            ok &= (
                unresolved_result.status is NativeListingCreationStatus.CREATED
                and unresolved_record is not None
                and unresolved_record.listing.market_episode_id is None
            )
            print(f"NativeListing unresolved creation -> {unresolved_result.status.value.upper()}")
            print(
                "unresolved link preserved         -> "
                f"{'YES' if unresolved_record is not None and unresolved_record.listing.market_episode_id is None else 'NO'}\n"
            )

            # -- NativeListing linked to real MarketEpisode -------------------
            linked_listing = NativeListing(
                id=NativeListingId("NL-0047-LINKED"), market_episode_id=episode.id
            )
            linked_result = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=linked_listing,
            )
            linked_record = fetch_native_listing(conn, linked_listing.id)
            conn.commit()
            linked_readback_exact = (
                linked_record is not None and linked_record.listing.market_episode_id == episode.id
            )
            ok &= (
                linked_result.status is NativeListingCreationStatus.CREATED
                and linked_readback_exact
            )
            print(f"NativeListing linked creation      -> {linked_result.status.value.upper()}")
            print(
                f"typed linked readback              -> {'EXACT' if linked_readback_exact else 'MISMATCH'}\n"
            )

            # -- unknown MarketEpisode fail-closed ------------------------------
            unknown_episode_result = create_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(
                    id=NativeListingId("NL-0047-UNKNOWN-EPISODE"),
                    market_episode_id=MarketEpisodeId("ME-0047-DOES-NOT-EXIST"),
                ),
            )
            unknown_episode_rows = _row_count(
                conn, "native_listings", "native_listing_id", "NL-0047-UNKNOWN-EPISODE"
            )
            ok &= (
                unknown_episode_result.status
                is NativeListingCreationStatus.MARKET_EPISODE_NOT_FOUND
                and unknown_episode_rows == 0
            )
            print(
                "NativeListing + unknown MarketEpisode -> "
                f"{unknown_episode_result.status.value.upper()}"
            )
            print(f"rows written                           -> {unknown_episode_rows}\n")

            # -- no post-creation mutable attach API/table ---------------------
            tables = _table_names(conn)
            no_attach_table = not any("attach" in t for t in tables)
            import hullq.persistence.native_listing as native_listing_mod

            no_attach_function = not hasattr(
                native_listing_mod, "attach_native_listing_to_market_episode"
            )
            no_attach_ok = no_attach_table and no_attach_function
            ok &= no_attach_ok
            print(
                f"no post-creation mutable attach API/table -> {'CONFIRMED' if no_attach_ok else 'FAILED'}\n"
            )

            # -- scope/truth regression: minimal envelope only ------------------
            record_fields = {f.name for f in dataclasses.fields(MarketEpisodeRecord)}
            no_extra_facts = record_fields == {"market_episode", "created_at"}
            actual_columns = _actual_columns(conn, "market_episodes")
            no_scope_creep_columns = actual_columns == _EXPECTED_MARKET_EPISODE_COLUMNS
            ok &= no_extra_facts and no_scope_creep_columns
            print(f"RECORD TYPE MINIMAL ENVELOPE ONLY -> {'YES' if no_extra_facts else 'NO'}")
            print(
                f"NO LIFECYCLE/PRICE/SELLER/DEDUP COLUMNS -> {'YES' if no_scope_creep_columns else 'NO'}"
            )
            print(f"MARKET EPISODE LINKAGE RESULT -> {'PASS' if ok else 'FAIL'}")

            return 0 if ok else 1
        finally:
            conn.close()
    finally:
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
