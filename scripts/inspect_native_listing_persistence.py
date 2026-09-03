"""SLICE-0043 NativeListing persistence owner-inspection.

Executes real PostgreSQL/Alembic behavior to demonstrate the durable
NativeListing creation capability required by SLICE-0043: authorized
creation, exact typed readback, idempotent retry, fail-closed conflict on a
reused NativeListingId with a changed envelope, denied/cross-Organization
creation writing zero rows, the transaction-ownership guarantee behind
"CREATED implies durably committed", and the absence of any BoatDesign-fact
projection or listing lifecycle/publication state.

Run: uv run python scripts/inspect_native_listing_persistence.py

Requires HULLQ_TEST_DATABASE_URL to point at a local PostgreSQL 18 instance.
Runs against its own freshly created/dropped disposable PostgreSQL *schema*
(isolated via the connection ``options=-c search_path=...`` parameter), then
brings that schema from genuinely empty to the SLICE-0043 Alembic head
(SLICE-0042 baseline + the native_listing_persistence revision).
"""

from __future__ import annotations

import dataclasses
import sys
import uuid
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
from psycopg.pq import TransactionStatus

from hullq.domain.market_identity import NativeListing, NativeListingId
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
from hullq.persistence.native_listing import (
    NativeListingCreationStatus,
    NativeListingRecord,
    NativeListingTransactionOwnershipError,
    create_native_listing,
    fetch_native_listing,
)

_LISTING_ID = "NL-0043-001"
_ORG_A_ID = "ORG-A"
_ORG_B_ID = "ORG-B"
_ACCOUNT_A_ID = "ACCOUNT-A"
_BROKER_REFERENCE = "BROKER-REF-42"

# The exact minimal column set the SLICE-0043 contract authorizes. Any
# additional column (e.g. a lifecycle/status/price/location field) would
# fail this structural check.
_EXPECTED_COLUMNS = {
    "native_listing_id",
    "publishing_organization_id",
    "created_by_account_id",
    "market_episode_id",
    "broker_listing_reference",
    "content_hash",
    "created_at",
}


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


def _row_count(conn: psycopg.Connection, native_listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listings WHERE native_listing_id = %s",
            [native_listing_id],
        )
        return int(cur.fetchone()[0])


def _actual_columns(conn: psycopg.Connection) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_schema = current_schema() AND table_name = 'native_listings'"
        )
        return {row[0] for row in cur.fetchall()}


def _transaction_ownership_scenario(url: str) -> bool:
    """Demonstrates the "CREATED implies durably committed" guarantee.

    Two sub-checks, both against real PostgreSQL connections:

    1. A connection that already has an open transaction (opened here by an
       ordinary readback SELECT, exactly as a caller composing "check, then
       create" on one connection would do) must be rejected before any write
       is attempted — rather than silently returning CREATED for a row that
       is only durable once the caller's own pre-existing transaction is
       later committed.
    2. On a normal IDLE connection, a CREATED result must already be durably
       visible from a completely separate, freshly opened connection, with
       no explicit commit() call by the original caller at all.
    """
    account = AccountId("ACCOUNT-TXN")
    org = MarketplaceOrganization(
        id=MarketplaceOrganizationId("ORG-TXN"),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )
    membership = OrganizationMembership(
        id=OrganizationMembershipId("OM-TXN"),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )

    # -- 1. non-IDLE connection must fail closed before any write ----------
    non_idle_conn = psycopg.connect(url)
    try:
        rejected_listing_id = "NL-0043-TXN-REJECTED"
        fetch_native_listing(non_idle_conn, NativeListingId(rejected_listing_id))
        opened_implicit_txn = non_idle_conn.info.transaction_status != TransactionStatus.IDLE

        rejected = False
        try:
            create_native_listing(
                non_idle_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                listing=NativeListing(id=NativeListingId(rejected_listing_id)),
            )
        except NativeListingTransactionOwnershipError:
            rejected = True
        non_idle_conn.rollback()
        rows_written = _row_count(non_idle_conn, rejected_listing_id)
    finally:
        non_idle_conn.close()

    fail_closed_ok = opened_implicit_txn and rejected and rows_written == 0
    print(
        "implicit-transaction connection create -> "
        f"{'REJECTED' if rejected else 'NOT REJECTED (unsafe)'}"
    )
    print(f"rows written by rejected attempt        -> {rows_written}")

    # -- 2. IDLE-connection CREATED must be durable without a caller commit -
    durable_listing_id = "NL-0043-TXN-DURABLE"
    writer_conn = psycopg.connect(url)
    try:
        was_idle = writer_conn.info.transaction_status == TransactionStatus.IDLE
        result = create_native_listing(
            writer_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(id=NativeListingId(durable_listing_id)),
        )
        created_ok = result.status is NativeListingCreationStatus.CREATED
        # No writer_conn.commit() call — durability must not depend on it.
    finally:
        writer_conn.close()

    reader_conn = psycopg.connect(url)
    try:
        visible_from_other_connection = (
            fetch_native_listing(reader_conn, NativeListingId(durable_listing_id)) is not None
        )
    finally:
        reader_conn.close()

    durable_ok = was_idle and created_ok and visible_from_other_connection
    print(
        "durable creation visible from a separate connection -> "
        f"{'YES' if visible_from_other_connection else 'NO'}\n"
    )

    return fail_closed_ok and durable_ok


def main() -> int:
    base_url = _base_url()
    schema_name = f"hullq_s0043_{uuid.uuid4().hex[:16]}"
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
            print("NATIVE LISTING PERSISTENCE\n")
            ok = True

            # -- eligible broker PUBLISHER creation + exact readback ---------
            account_a = AccountId(_ACCOUNT_A_ID)
            org_a = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_A_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            membership_a = OrganizationMembership(
                id=OrganizationMembershipId("OM-A"),
                account_id=account_a,
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            listing = NativeListing(id=NativeListingId(_LISTING_ID))

            create_result = create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=listing,
                broker_listing_reference=_BROKER_REFERENCE,
            )
            record = fetch_native_listing(conn, listing.id)
            # The readback above opened an implicit transaction on conn; end
            # it so the next create_native_listing() call below can again
            # safely own its own top-level transaction (see
            # NativeListingTransactionOwnershipError / the dedicated
            # transaction-ownership scenario further down).
            conn.commit()
            readback_exact = (
                record is not None
                and record.listing == listing
                and record.publishing_organization_id == org_a.id
                and record.created_by_account_id == account_a
                and record.broker_listing_reference == _BROKER_REFERENCE
                and record.created_at is not None
            )
            created_ok = create_result.status is NativeListingCreationStatus.CREATED
            ok &= created_ok and readback_exact
            print(f"eligible broker PUBLISHER -> {create_result.status.value.upper()}")
            print(f"listing id                 -> {_LISTING_ID}")
            print(f"publishing organization    -> {_ORG_A_ID}")
            print(f"created by                 -> {_ACCOUNT_A_ID}")
            print(
                "market episode             -> "
                f"{'UNRESOLVED' if record is not None and record.listing.market_episode_id is None else 'RESOLVED'}"
            )
            print(
                f"broker reference           -> {record.broker_listing_reference if record else None}"
            )
            print(f"readback                    -> {'EXACT' if readback_exact else 'MISMATCH'}\n")

            # -- identical retry: idempotent ----------------------------------
            assert record is not None
            first_created_at = record.created_at
            retry_result = create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=listing,
                broker_listing_reference=_BROKER_REFERENCE,
            )
            row_count_after_retry = _row_count(conn, _LISTING_ID)
            retry_record = fetch_native_listing(conn, listing.id)
            conn.commit()  # end the readback's implicit transaction (see above)
            created_at_preserved = (
                retry_record is not None and retry_record.created_at == first_created_at
            )
            retry_ok = (
                retry_result.status is NativeListingCreationStatus.ALREADY_EXISTS
                and row_count_after_retry == 1
                and created_at_preserved
            )
            ok &= retry_ok
            print(f"identical retry             -> {retry_result.status.value.upper()}")
            print(f"row count after retry       -> {row_count_after_retry}")
            print(f"created_at preserved        -> {'YES' if created_at_preserved else 'NO'}\n")

            # -- same id, changed envelope: conflict --------------------------
            conflict_result = create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_a,
                membership=membership_a,
                listing=listing,
                broker_listing_reference="BROKER-REF-CHANGED",
            )
            after_conflict = fetch_native_listing(conn, listing.id)
            conn.commit()  # end the readback's implicit transaction (see above)
            original_unchanged = (
                after_conflict is not None
                and after_conflict.broker_listing_reference == _BROKER_REFERENCE
            )
            conflict_ok = (
                conflict_result.status is NativeListingCreationStatus.CONFLICT
                and original_unchanged
            )
            ok &= conflict_ok
            print(f"same listing id, changed envelope -> {conflict_result.status.value.upper()}")
            print(f"original row unchanged            -> {'YES' if original_unchanged else 'NO'}\n")

            # -- OWNER-only denial ---------------------------------------------
            owner_membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-OWNER"),
                account_id=AccountId("ACCOUNT-OWNER"),
                organization_id=org_a.id,
                roles=frozenset({MembershipRole.OWNER}),
                state=MembershipState.ACTIVE,
            )
            owner_result = create_native_listing(
                conn,
                account_id=AccountId("ACCOUNT-OWNER"),
                candidate_organization=org_a,
                membership=owner_membership,
                listing=NativeListing(id=NativeListingId("NL-0043-OWNER-DENIED")),
            )
            owner_denied_ok = (
                owner_result.status is NativeListingCreationStatus.DENIED
                and owner_result.denial_reason is not None
                and owner_result.denial_reason.value == "PUBLISHER_ROLE_REQUIRED"
            )

            # -- cross-Organization denial --------------------------------------
            org_b = MarketplaceOrganization(
                id=MarketplaceOrganizationId(_ORG_B_ID),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            cross_org_result = create_native_listing(
                conn,
                account_id=account_a,
                candidate_organization=org_b,
                membership=membership_a,
                listing=NativeListing(id=NativeListingId("NL-0043-CROSSORG-DENIED")),
            )
            cross_org_denied_ok = (
                cross_org_result.status is NativeListingCreationStatus.DENIED
                and cross_org_result.denial_reason is not None
                and cross_org_result.denial_reason.value == "ORGANIZATION_MISMATCH"
            )

            denied_wrote_rows = (
                _row_count(conn, "NL-0043-OWNER-DENIED") > 0
                or _row_count(conn, "NL-0043-CROSSORG-DENIED") > 0
            )
            conn.commit()  # end the row-count readbacks' implicit transaction
            denial_ok = owner_denied_ok and cross_org_denied_ok and not denied_wrote_rows
            ok &= denial_ok
            print(
                "OWNER-only creation        -> "
                f"{owner_result.status.value.upper()}: {owner_result.denial_reason.value if owner_result.denial_reason else ''}"
            )
            print(
                "cross-org creation         -> "
                f"{cross_org_result.status.value.upper()}: "
                f"{cross_org_result.denial_reason.value if cross_org_result.denial_reason else ''}"
            )
            print(f"denied attempts wrote rows -> {'YES' if denied_wrote_rows else 'NO'}\n")

            # -- transaction ownership: CREATED must always mean durable -----
            transaction_ownership_ok = _transaction_ownership_scenario(url)
            ok &= transaction_ownership_ok

            # -- scope/truth regression: no design facts, no lifecycle state --
            record_fields = {f.name for f in dataclasses.fields(NativeListingRecord)}
            no_design_facts = record_fields == {
                "listing",
                "publishing_organization_id",
                "created_by_account_id",
                "broker_listing_reference",
                "created_at",
            }
            actual_columns = _actual_columns(conn)
            conn.commit()  # end the columns readback's implicit transaction
            no_lifecycle_columns = actual_columns == _EXPECTED_COLUMNS
            ok &= no_design_facts and no_lifecycle_columns
            print(f"DESIGN FACTS PROJECTED      -> {'NO' if no_design_facts else 'YES'}")
            print(f"PUBLICATION/LIFECYCLE SET   -> {'NO' if no_lifecycle_columns else 'YES'}")
            print(f"NATIVE LISTING RESULT       -> {'PASS' if ok else 'FAIL'}")

            return 0 if ok else 1
        finally:
            conn.close()
    finally:
        _drop_schema(base_url, schema_name)


if __name__ == "__main__":
    raise SystemExit(main())
