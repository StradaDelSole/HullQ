"""PostgreSQL-backed NativeListing freshness/reconfirmation persistence tests — SLICE-0052.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the current Alembic head, mirroring the SLICE-0049
`tests/persistence/test_native_listing_lifecycle_persistence.py` isolation
pattern.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Generator
from datetime import timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.native_listing_freshness import (
    is_current_market_eligible,
    resolve_current_freshness,
)
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import FreshnessConfirmationId, FreshnessStatus
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
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
    PublishingEligibilityReason,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_freshness import (
    NativeListingFreshnessTransactionOwnershipError,
    ReconfirmationStatus,
    fetch_effective_confirmed_at,
    reconfirm_native_listing,
)
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionStatus,
    list_publication_transitions,
    publish_native_listing,
    withdraw_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat

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
def freshness_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0052_{uuid.uuid4().hex[:16]}"
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
def freshness_conn(freshness_url: str) -> Generator[Any]:
    conn = psycopg.connect(freshness_url)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------


def _account(value: str) -> AccountId:
    return AccountId(value)


def _org(
    value: str,
    *,
    category: ProfessionalCategory = ProfessionalCategory.BROKER,
    eligibility: OrganizationPublishingEligibility = OrganizationPublishingEligibility.ELIGIBLE,
) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=category,
        publishing_eligibility=eligibility,
    )


def _membership(
    membership_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=roles,
        state=state,
    )


def _amount_offer() -> NativeListingOfferSnapshot:
    return NativeListingOfferSnapshot(
        asking_price_mode=AskingPriceMode.AMOUNT,
        location_country="FR",
        broker_description="A well-maintained cruising sloop.",
        asking_price_amount=Decimal("125000.00"),
        currency="EUR",
    )


def _create_and_publish_listing(
    conn: Any,
    *,
    listing_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
) -> None:
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    create_result = create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
        ),
    )
    assert create_result.status.value in ("created", "already_exists"), create_result
    offer_result = write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=NativeListingOfferRevisionId(offer_revision_id),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    assert offer_result.status.value in ("created", "already_exists"), offer_result
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status is LifecycleTransitionStatus.TRANSITIONED, publish_result


def _confirmation_row_count(conn: Any, native_listing_id: str) -> int:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT COUNT(*) FROM native_listing_freshness_confirmations "
            "WHERE native_listing_id = %s",
            [native_listing_id],
        )
        (count,) = cur.fetchone()
    return int(count)


# ---------------------------------------------------------------------------
# fetch_effective_confirmed_at
# ---------------------------------------------------------------------------


def test_fetch_effective_confirmed_at_is_none_before_publication(freshness_conn: Any) -> None:
    account = _account("ACC-DRAFTONLY")
    org = _org("ORG-DRAFTONLY")
    membership = _membership("OM-DRAFTONLY", account, org)
    create_native_listing(
        freshness_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId("NL-DRAFTONLY")),
    )
    freshness_conn.commit()

    assert fetch_effective_confirmed_at(freshness_conn, NativeListingId("NL-DRAFTONLY")) is None


def test_fetch_effective_confirmed_at_derives_from_publication_transition(
    freshness_conn: Any,
) -> None:
    account = _account("ACC-PUB0052")
    org = _org("ORG-PUB0052")
    membership = _membership("OM-PUB0052", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-PUB0052",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-PUB0052",
        market_episode_id="ME-PUB0052",
        offer_revision_id="REV-PUB0052",
    )
    freshness_conn.commit()

    transitions = list_publication_transitions(freshness_conn, NativeListingId("NL-PUB0052"))
    assert len(transitions) == 1

    effective = fetch_effective_confirmed_at(freshness_conn, NativeListingId("NL-PUB0052"))
    assert effective == transitions[0].occurred_at


def test_resolve_current_freshness_boundaries_from_real_persisted_evidence(
    freshness_conn: Any,
) -> None:
    """Real publication evidence + explicit synthetic `as_of` boundaries
    (contract §8): the same persisted evidence classifies CONFIRMED at
    +29d, DUE_FOR_CONFIRMATION at exactly +30d, and STALE at exactly +37d,
    without sleeping or rewriting the audit timestamp."""
    account = _account("ACC-BOUND")
    org = _org("ORG-BOUND")
    membership = _membership("OM-BOUND", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-BOUND",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-BOUND",
        market_episode_id="ME-BOUND",
        offer_revision_id="REV-BOUND",
    )
    freshness_conn.commit()

    confirmed_at = fetch_effective_confirmed_at(freshness_conn, NativeListingId("NL-BOUND"))
    assert confirmed_at is not None

    just_before = resolve_current_freshness(
        freshness_conn, NativeListingId("NL-BOUND"), as_of=confirmed_at + timedelta(days=29)
    )
    assert just_before.status is FreshnessStatus.CONFIRMED
    assert is_current_market_eligible(just_before.status)

    exactly_due = resolve_current_freshness(
        freshness_conn, NativeListingId("NL-BOUND"), as_of=confirmed_at + timedelta(days=30)
    )
    assert exactly_due.status is FreshnessStatus.DUE_FOR_CONFIRMATION
    assert is_current_market_eligible(exactly_due.status)

    exactly_stale = resolve_current_freshness(
        freshness_conn, NativeListingId("NL-BOUND"), as_of=confirmed_at + timedelta(days=37)
    )
    assert exactly_stale.status is FreshnessStatus.STALE
    assert not is_current_market_eligible(exactly_stale.status)
    assert exactly_stale.last_confirmed_at == confirmed_at


# ---------------------------------------------------------------------------
# reconfirm_native_listing — authorization / preconditions
# ---------------------------------------------------------------------------


def test_reconfirm_succeeds_for_active_listing_with_eligible_owning_principal(
    freshness_conn: Any,
) -> None:
    account = _account("ACC-RECONF")
    org = _org("ORG-RECONF")
    membership = _membership("OM-RECONF", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-RECONF",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-RECONF",
        market_episode_id="ME-RECONF",
        offer_revision_id="REV-RECONF",
    )
    freshness_conn.commit()

    result = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=FreshnessConfirmationId("FC-RECONF-1"),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-RECONF"),
    )
    assert result.status is ReconfirmationStatus.RECONFIRMED
    assert result.occurred_at is not None

    effective = fetch_effective_confirmed_at(freshness_conn, NativeListingId("NL-RECONF"))
    assert effective == result.occurred_at


def test_reconfirm_denied_without_membership_writes_zero_rows(freshness_conn: Any) -> None:
    account = _account("ACC-NOMEM")
    org = _org("ORG-NOMEM")
    membership = _membership("OM-NOMEM", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-NOMEM",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-NOMEM",
        market_episode_id="ME-NOMEM",
        offer_revision_id="REV-NOMEM",
    )
    freshness_conn.commit()

    result = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=FreshnessConfirmationId("FC-NOMEM-1"),
        account_id=account,
        candidate_organization=org,
        membership=None,
        native_listing_id=NativeListingId("NL-NOMEM"),
    )
    assert result.status is ReconfirmationStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP
    assert _confirmation_row_count(freshness_conn, "NL-NOMEM") == 0


def test_reconfirm_fails_cross_organization_writes_zero_rows(freshness_conn: Any) -> None:
    account = _account("ACC-XORG")
    org = _org("ORG-XORG")
    membership = _membership("OM-XORG", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-XORG",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-XORG",
        market_episode_id="ME-XORG",
        offer_revision_id="REV-XORG",
    )
    freshness_conn.commit()

    other_account = _account("ACC-XORG-OTHER")
    other_org = _org("ORG-XORG-OTHER")
    other_membership = _membership("OM-XORG-OTHER", other_account, other_org)

    result = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=FreshnessConfirmationId("FC-XORG-1"),
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-XORG"),
    )
    assert result.status is ReconfirmationStatus.ORGANIZATION_MISMATCH
    assert _confirmation_row_count(freshness_conn, "NL-XORG") == 0


def test_reconfirm_fails_for_draft_listing_writes_zero_rows(freshness_conn: Any) -> None:
    account = _account("ACC-DRAFTRC")
    org = _org("ORG-DRAFTRC")
    membership = _membership("OM-DRAFTRC", account, org)
    create_native_listing(
        freshness_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId("NL-DRAFTRC")),
    )
    freshness_conn.commit()

    result = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=FreshnessConfirmationId("FC-DRAFTRC-1"),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DRAFTRC"),
    )
    assert result.status is ReconfirmationStatus.NOT_ACTIVE
    assert _confirmation_row_count(freshness_conn, "NL-DRAFTRC") == 0


def test_reconfirm_fails_for_withdrawn_listing_writes_zero_rows(freshness_conn: Any) -> None:
    account = _account("ACC-WD")
    org = _org("ORG-WD")
    membership = _membership("OM-WD", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-WD",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-WD",
        market_episode_id="ME-WD",
        offer_revision_id="REV-WD",
    )
    withdraw_result = withdraw_native_listing(
        freshness_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-WD"),
    )
    assert withdraw_result.status is LifecycleTransitionStatus.TRANSITIONED
    freshness_conn.commit()

    result = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=FreshnessConfirmationId("FC-WD-1"),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-WD"),
    )
    assert result.status is ReconfirmationStatus.NOT_ACTIVE
    assert _confirmation_row_count(freshness_conn, "NL-WD") == 0

    # STALE/UNKNOWN suppression never invents SOLD/WITHDRAWN -- and here the
    # reverse also holds: a real WITHDRAWN listing never gains a
    # confirmation event through this path.
    assert (
        fetch_effective_confirmed_at(freshness_conn, NativeListingId("NL-WD")) is not None
    )  # the original publish evidence remains, untouched


def test_reconfirm_fails_for_missing_listing(freshness_conn: Any) -> None:
    account = _account("ACC-MISSING")
    org = _org("ORG-MISSING")
    membership = _membership("OM-MISSING", account, org)

    result = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=FreshnessConfirmationId("FC-MISSING-1"),
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-NEVER-CREATED-0052"),
    )
    assert result.status is ReconfirmationStatus.NATIVE_LISTING_NOT_FOUND


# ---------------------------------------------------------------------------
# Idempotency / conflict
# ---------------------------------------------------------------------------


def test_exact_reconfirmation_retry_is_idempotent(freshness_conn: Any) -> None:
    account = _account("ACC-RETRY52")
    org = _org("ORG-RETRY52")
    membership = _membership("OM-RETRY52", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-RETRY52",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-RETRY52",
        market_episode_id="ME-RETRY52",
        offer_revision_id="REV-RETRY52",
    )
    freshness_conn.commit()

    confirmation_id = FreshnessConfirmationId("FC-RETRY52-1")
    first = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=confirmation_id,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-RETRY52"),
    )
    assert first.status is ReconfirmationStatus.RECONFIRMED

    retry = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=confirmation_id,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-RETRY52"),
    )
    assert retry.status is ReconfirmationStatus.ALREADY_EXISTS
    assert retry.occurred_at == first.occurred_at
    assert _confirmation_row_count(freshness_conn, "NL-RETRY52") == 1


def test_conflicting_confirmation_id_reuse_fails_closed(freshness_conn: Any) -> None:
    account = _account("ACC-CONFLICT52")
    org = _org("ORG-CONFLICT52")
    membership = _membership("OM-CONFLICT52", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-CONFLICT52",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-CONFLICT52",
        market_episode_id="ME-CONFLICT52",
        offer_revision_id="REV-CONFLICT52",
    )
    freshness_conn.commit()

    confirmation_id = FreshnessConfirmationId("FC-CONFLICT52-1")
    first = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=confirmation_id,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-CONFLICT52"),
    )
    assert first.status is ReconfirmationStatus.RECONFIRMED

    # A different Account attempts to reuse the exact same confirmation_id
    # for the exact same listing -- the envelope differs (actor_account_id),
    # so this must fail closed as CONFLICT, never silently accepted and
    # never overwriting the original row.
    other_account = _account("ACC-CONFLICT52-OTHER")
    other_membership = _membership("OM-CONFLICT52-OTHER", other_account, org)
    conflicting = reconfirm_native_listing(
        freshness_conn,
        confirmation_id=confirmation_id,
        account_id=other_account,
        candidate_organization=org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-CONFLICT52"),
    )
    assert conflicting.status is ReconfirmationStatus.CONFLICT
    assert _confirmation_row_count(freshness_conn, "NL-CONFLICT52") == 1

    effective = fetch_effective_confirmed_at(freshness_conn, NativeListingId("NL-CONFLICT52"))
    assert effective == first.occurred_at


# ---------------------------------------------------------------------------
# Transaction ownership
# ---------------------------------------------------------------------------


def test_reconfirm_requires_idle_connection(freshness_conn: Any) -> None:
    account = _account("ACC-TXN52")
    org = _org("ORG-TXN52")
    membership = _membership("OM-TXN52", account, org)
    _create_and_publish_listing(
        freshness_conn,
        listing_id="NL-TXN52",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-TXN52",
        market_episode_id="ME-TXN52",
        offer_revision_id="REV-TXN52",
    )
    freshness_conn.commit()

    with freshness_conn.cursor() as cur:
        cur.execute("SELECT 1")  # opens an implicit transaction, never committed

    with pytest.raises(NativeListingFreshnessTransactionOwnershipError):
        reconfirm_native_listing(
            freshness_conn,
            confirmation_id=FreshnessConfirmationId("FC-TXN52-1"),
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-TXN52"),
        )


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency
# ---------------------------------------------------------------------------


def test_concurrent_reconfirmations_with_distinct_ids_both_succeed(freshness_url: str) -> None:
    """Two concurrent, genuinely distinct reconfirmation events for the same
    listing must both durably succeed without corrupting each other or the
    lifecycle state (contract §6)."""
    setup_conn = psycopg.connect(freshness_url)
    try:
        account = _account("ACC-CRACE52")
        org = _org("ORG-CRACE52")
        membership = _membership("OM-CRACE52", account, org)
        _create_and_publish_listing(
            setup_conn,
            listing_id="NL-CRACE52",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-CRACE52",
            market_episode_id="ME-CRACE52",
            offer_revision_id="REV-CRACE52",
        )
        setup_conn.commit()
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(confirmation_id_value: str) -> None:
        try:
            conn = psycopg.connect(freshness_url)
            try:
                barrier.wait(timeout=10)
                result = reconfirm_native_listing(
                    conn,
                    confirmation_id=FreshnessConfirmationId(confirmation_id_value),
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-CRACE52"),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("FC-CRACE52-A",)),
        threading.Thread(target=_worker, args=("FC-CRACE52-B",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    assert all(r.status is ReconfirmationStatus.RECONFIRMED for r in results), results

    verify = psycopg.connect(freshness_url)
    try:
        assert _confirmation_row_count(verify, "NL-CRACE52") == 2
        from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
        from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state

        assert (
            fetch_lifecycle_state(verify, NativeListingId("NL-CRACE52"))
            is NativeListingLifecycleState.ACTIVE
        )
    finally:
        verify.close()
