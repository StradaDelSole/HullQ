"""SLICE-0072 real-PostgreSQL genuinely concurrent-write proofs.

Contract §15: "concurrent edits produce one accepted current head and
deterministic conflict for stale competitors." Uses independent psycopg
connections plus a `threading.Barrier` for genuine parallel execution --
mirrors `test_native_listing_offer_persistence.py`'s identical
`test_concurrent_conflicting_revisions_resolve_deterministically` proof.

That existing SLICE-0045/0050 proof already exercises the row-locking
primitive (`write_native_listing_offer_revision_row`/
`write_physical_boat_claim_revision_row`) directly. This module instead
drives the exact SLICE-0072 application-facing entry points
(`hullq.persistence.inventory_editing.edit_native_listing_offer`/
`edit_physical_boat_claim`), which wrap that identical primitive inside
their own `with conn.transaction():` plus (for an ACTIVE listing only) an
additional in-transaction D29 candidate-head re-check -- this proves the
0072 wrapper does not reintroduce a race the underlying primitive already
closed, rather than merely assuming the wrapper "inherits" that guarantee.

A DRAFT-lifecycle listing is used for both races below: the `SELECT ...
FOR UPDATE` row lock on `native_listings` that serializes the two
competitors is taken unconditionally, before the lifecycle_state branch
that decides whether the extra D29 re-check runs at all -- so DRAFT vs.
ACTIVE cannot change the race-serialization semantics under test here. The
ACTIVE-only D29 re-check's own *correctness* (atomic rollback on a hard
invariant violation) is a separate, already-covered single-mutation proof
(`test_broker_inventory_editing_api.py::TestOfferSave::
test_active_invariant_violation_leaves_prior_head_unchanged`), not a
concurrency concern.
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

from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_offer import (
    AskingPriceMode,
    NativeListingOfferRevisionId,
    NativeListingOfferSnapshot,
)
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.persistence.inventory_editing import (
    ClaimEditStatus,
    InventoryEditTransactionOwnershipError,
    OfferEditStatus,
    edit_native_listing_offer,
    edit_physical_boat_claim,
)
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_offer import (
    fetch_current_native_listing_offer,
    list_native_listing_offer_revisions,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    list_physical_boat_claim_revisions,
)

_LISTING_ID = "NL-CONC-0072"
_ORG_ID = "ORG-CONC-0072"
_ACCOUNT_ID = "ACC-CONC-0072"
_MEMBERSHIP_ID = "OM-CONC-0072"
_PHYSICAL_BOAT_ID = "PB-CONC-0072"
_MARKET_EPISODE_ID = "ME-CONC-0072"


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
def editing_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0072conc_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


def _amount_offer(*, price: str) -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal(price),
        currency="EUR",
    )


def _claim(*, build_year: int) -> PhysicalBoatClaimSnapshot:
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, build_year),
    )


def _seed_promoted_draft_listing(
    editing_url: str,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    """A DRAFT NativeListing with an existing current offer/claim -- the
    exact shape SLICE-0072's editor operates on, minus the D22 cover-image
    fixture (irrelevant to a DRAFT-lifecycle concurrency race)."""
    conn = psycopg.connect(editing_url)
    try:
        account = AccountId(_ACCOUNT_ID)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(_ORG_ID),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(_MEMBERSHIP_ID),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [_ACCOUNT_ID],
            )
        seed_marketplace_organization(conn, org)
        seed_organization_membership(conn, membership)
        conn.commit()

        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(_PHYSICAL_BOAT_ID)))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(_MARKET_EPISODE_ID),
                physical_boat_id=PhysicalBoatId(_PHYSICAL_BOAT_ID),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(_LISTING_ID),
                market_episode_id=MarketEpisodeId(_MARKET_EPISODE_ID),
            ),
        )
        offer_result = edit_native_listing_offer(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(_LISTING_ID),
            revision_id=NativeListingOfferRevisionId("REV-CONC-0072-INITIAL"),
            expected_current_revision_id=None,
            offer=_amount_offer(price="125000.00"),
        )
        assert offer_result.status is OfferEditStatus.REVISED, offer_result

        claim_result = edit_physical_boat_claim(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(_LISTING_ID),
            revision_id=PhysicalBoatClaimRevisionId("CLAIM-CONC-0072-INITIAL"),
            expected_current_revision_id=None,
            claims=_claim(build_year=2020),
        )
        assert claim_result.status is ClaimEditStatus.REVISED, claim_result
        return account, org, membership
    finally:
        conn.close()


def test_concurrent_offer_edits_from_same_expected_revision(editing_url: str) -> None:
    """Two independent-connection offer edits racing from the identical
    `expected_current_revision_id` must resolve as exactly one REVISED
    (becoming the sole new current head) and one CONFLICT (fails closed,
    writes nothing) -- never two successful writes, never a lost update."""
    account, org, membership = _seed_promoted_draft_listing(editing_url)

    setup_conn = psycopg.connect(editing_url)
    try:
        current_before = fetch_current_native_listing_offer(
            setup_conn, NativeListingId(_LISTING_ID)
        )
    finally:
        setup_conn.close()
    assert current_before is not None
    expected = current_before.revision_id

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(suffix: str, price: str) -> None:
        try:
            conn = psycopg.connect(editing_url)
            try:
                barrier.wait(timeout=10)
                result = edit_native_listing_offer(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(_LISTING_ID),
                    revision_id=NativeListingOfferRevisionId(f"REV-CONC-0072-{suffix}"),
                    expected_current_revision_id=expected,
                    offer=_amount_offer(price=price),
                )
                results.append(result)
            finally:
                conn.close()
        except BaseException as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("A", "130000.00")),
        threading.Thread(target=_worker, args=("B", "131000.00")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(OfferEditStatus.REVISED) == 1, statuses
    assert statuses.count(OfferEditStatus.CONFLICT) == 1, statuses

    winner = next(r for r in results if r.status is OfferEditStatus.REVISED)
    loser = next(r for r in results if r.status is OfferEditStatus.CONFLICT)
    # The stale competitor's CONFLICT result reports the real winning head,
    # never its own never-written candidate.
    assert loser.current_revision_id == winner.current_revision_id

    verify = psycopg.connect(editing_url)
    try:
        current_after = fetch_current_native_listing_offer(verify, NativeListingId(_LISTING_ID))
        history = list_native_listing_offer_revisions(verify, NativeListingId(_LISTING_ID))
    finally:
        verify.close()
    assert current_after is not None
    # Exactly one accepted current head -- the winner's, never the loser's.
    assert current_after.revision_id == winner.current_revision_id
    # No lost update, no duplicate accepted current head: immutable history
    # carries exactly the pre-existing revision plus the one winner -- the
    # loser's candidate revision was never inserted at all.
    assert len(history) == 2, history
    history_ids = {r.revision_id.value for r in history}
    assert history_ids == {"REV-CONC-0072-INITIAL", winner.current_revision_id.value}


def test_concurrent_claim_edits_from_same_expected_revision(editing_url: str) -> None:
    """Two independent-connection PhysicalBoat claim edits racing from the
    identical `expected_current_revision_id` must resolve as exactly one
    REVISED and one CONFLICT -- never two successful writes, never a lost
    update."""
    account, org, membership = _seed_promoted_draft_listing(editing_url)

    setup_conn = psycopg.connect(editing_url)
    try:
        current_before = fetch_current_physical_boat_claim(
            setup_conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), MarketplaceOrganizationId(_ORG_ID)
        )
    finally:
        setup_conn.close()
    assert current_before is not None
    expected = current_before.revision_id

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(suffix: str, build_year: int) -> None:
        try:
            conn = psycopg.connect(editing_url)
            try:
                barrier.wait(timeout=10)
                result = edit_physical_boat_claim(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId(_LISTING_ID),
                    revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-CONC-0072-{suffix}"),
                    expected_current_revision_id=expected,
                    claims=_claim(build_year=build_year),
                )
                results.append(result)
            finally:
                conn.close()
        except BaseException as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("A", 2021)),
        threading.Thread(target=_worker, args=("B", 2022)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(ClaimEditStatus.REVISED) == 1, statuses
    assert statuses.count(ClaimEditStatus.CONFLICT) == 1, statuses

    winner = next(r for r in results if r.status is ClaimEditStatus.REVISED)
    loser = next(r for r in results if r.status is ClaimEditStatus.CONFLICT)
    assert loser.current_revision_id == winner.current_revision_id

    verify = psycopg.connect(editing_url)
    try:
        current_after = fetch_current_physical_boat_claim(
            verify, PhysicalBoatId(_PHYSICAL_BOAT_ID), MarketplaceOrganizationId(_ORG_ID)
        )
        history = list_physical_boat_claim_revisions(
            verify, PhysicalBoatId(_PHYSICAL_BOAT_ID), MarketplaceOrganizationId(_ORG_ID)
        )
    finally:
        verify.close()
    assert current_after is not None
    assert current_after.revision_id == winner.current_revision_id
    assert len(history) == 2, history
    history_ids = {r.revision_id.value for r in history}
    assert history_ids == {"CLAIM-CONC-0072-INITIAL", winner.current_revision_id.value}


# ---------------------------------------------------------------------------
# Transaction ownership -- a REVISED result must always mean durable
# ---------------------------------------------------------------------------


def test_offer_edit_on_a_connection_with_an_open_transaction_fails_closed(
    editing_url: str,
) -> None:
    """Mirrors `test_native_listing_offer_persistence.py`'s identical
    `test_write_on_a_connection_with_an_open_implicit_transaction_fails_closed`:
    a plain read leaves *conn* with an open implicit transaction (psycopg's
    default `autocommit=False`); calling `edit_native_listing_offer` on that
    same connection, without an intervening `commit()`/`rollback()`, must
    raise before attempting any write rather than silently degrading to a
    nested savepoint."""
    account, org, membership = _seed_promoted_draft_listing(editing_url)

    conn = psycopg.connect(editing_url)
    try:
        current = fetch_current_native_listing_offer(conn, NativeListingId(_LISTING_ID))
        assert current is not None
        with pytest.raises(InventoryEditTransactionOwnershipError):
            edit_native_listing_offer(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=NativeListingOfferRevisionId("REV-CONC-0072-TXN"),
                expected_current_revision_id=current.revision_id,
                offer=_amount_offer(price="150000.00"),
            )
    finally:
        conn.rollback()
        conn.close()


def test_claim_edit_on_a_connection_with_an_open_transaction_fails_closed(
    editing_url: str,
) -> None:
    account, org, membership = _seed_promoted_draft_listing(editing_url)

    conn = psycopg.connect(editing_url)
    try:
        current = fetch_current_physical_boat_claim(
            conn, PhysicalBoatId(_PHYSICAL_BOAT_ID), MarketplaceOrganizationId(_ORG_ID)
        )
        assert current is not None
        with pytest.raises(InventoryEditTransactionOwnershipError):
            edit_physical_boat_claim(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(_LISTING_ID),
                revision_id=PhysicalBoatClaimRevisionId("CLAIM-CONC-0072-TXN"),
                expected_current_revision_id=current.revision_id,
                claims=_claim(build_year=2025),
            )
    finally:
        conn.rollback()
        conn.close()
