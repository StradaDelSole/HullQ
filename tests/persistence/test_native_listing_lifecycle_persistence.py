"""PostgreSQL-backed NativeListing lifecycle persistence tests — SLICE-0049.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0049 Alembic head, mirroring the SLICE-0043/
0045/0047 integration test isolation pattern.
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
from hullq.domain.native_listing_lifecycle import (
    NativeListingLifecycleState,
    PublicationTransitionId,
)
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
from hullq.persistence.native_listing import (
    NativeListingCreationStatus,
    create_native_listing,
    fetch_native_listing,
)
from hullq.persistence.native_listing_lifecycle import (
    LifecycleTransitionStatus,
    NativeListingLifecycleTransactionOwnershipError,
    fetch_lifecycle_state,
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
# Disposable-schema fixture: genuinely-empty schema -> SLICE-0049 Alembic head
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
def lifecycle_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0049_{uuid.uuid4().hex[:16]}"
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
def lifecycle_conn(lifecycle_url: str) -> Generator[Any]:
    conn = psycopg.connect(lifecycle_url)
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


def _create_complete_listing(
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
    """Create/reuse a full durable chain satisfying the §7 completeness predicate."""
    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(market_episode_id), physical_boat_id=PhysicalBoatId(physical_boat_id)
        ),
    )
    result = create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
        ),
    )
    assert result.status in (
        NativeListingCreationStatus.CREATED,
        NativeListingCreationStatus.ALREADY_EXISTS,
    ), result
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


def _create_incomplete_listing(
    conn: Any,
    *,
    listing_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
) -> None:
    """Create a durable NativeListing with no MarketEpisode link and no offer."""
    result = create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId(listing_id)),
    )
    assert result.status in (
        NativeListingCreationStatus.CREATED,
        NativeListingCreationStatus.ALREADY_EXISTS,
    ), result


# ---------------------------------------------------------------------------
# Migration / DRAFT default
# ---------------------------------------------------------------------------


def test_newly_created_listing_begins_draft(lifecycle_conn: Any) -> None:
    account = _account("ACC-NEW")
    org = _org("ORG-NEW")
    membership = _membership("OM-NEW", account, org)
    _create_incomplete_listing(
        lifecycle_conn, listing_id="NL-NEW", account=account, org=org, membership=membership
    )
    lifecycle_conn.commit()

    state = fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-NEW"))
    assert state is NativeListingLifecycleState.DRAFT


def test_pre_existing_listing_from_before_the_lifecycle_migration_begins_draft(
    db_url: str,
) -> None:
    """Simulates a listing durably created before this migration existed:
    insert a native_listings row while the schema is still pinned at the
    pre-0049 Alembic revision (so ``lifecycle_state`` does not exist yet),
    then upgrade to head. The ``ALTER TABLE ... ADD COLUMN ... DEFAULT
    'DRAFT'`` backfill must apply to that pre-existing row exactly as it
    does to a brand-new row, never leaving it implicitly ACTIVE/public."""
    from alembic import command
    from hullq.persistence.alembic_baseline import alembic_config

    schema_name = f"hullq_s0049pre_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        command.upgrade(alembic_config(url), "4c9a0dcc98bb")  # pre-0049 head

        conn = psycopg.connect(url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO native_listings "
                    "(native_listing_id, publishing_organization_id, created_by_account_id, "
                    " content_hash) VALUES (%s, %s, %s, %s)",
                    ("NL-PRE", "ORG-PRE", "ACC-PRE", "0" * 64),
                )
            conn.commit()

            command.upgrade(alembic_config(url), "head")

            state = fetch_lifecycle_state(conn, NativeListingId("NL-PRE"))
            assert state is NativeListingLifecycleState.DRAFT
        finally:
            conn.close()
    finally:
        _drop_schema(db_url, schema_name)


def test_missing_listing_has_no_lifecycle_state(lifecycle_conn: Any) -> None:
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-NEVER-CREATED")) is None


def test_exact_creation_retry_remains_already_exists_after_lifecycle_becomes_active(
    lifecycle_url: str,
) -> None:
    """0043 immutable creation idempotency must survive a later lifecycle
    change untouched -- lifecycle is outside the accepted content hash."""
    conn = psycopg.connect(lifecycle_url)
    try:
        account = _account("ACC-RETRY")
        org = _org("ORG-RETRY")
        membership = _membership("OM-RETRY", account, org)
        _create_complete_listing(
            conn,
            listing_id="NL-RETRY",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-RETRY",
            market_episode_id="ME-RETRY",
            offer_revision_id="REV-RETRY",
        )
        conn.commit()

        publish_result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-RETRY"),
        )
        assert publish_result.status is LifecycleTransitionStatus.TRANSITIONED

        # Exact retry of the original immutable creation envelope.
        retry_result = create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId("NL-RETRY"), market_episode_id=MarketEpisodeId("ME-RETRY")
            ),
        )
        assert retry_result.status is NativeListingCreationStatus.ALREADY_EXISTS

        record = fetch_native_listing(conn, NativeListingId("NL-RETRY"))
        assert record is not None
        assert record.publishing_organization_id == org.id
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Publish (DRAFT -> ACTIVE)
# ---------------------------------------------------------------------------


def test_publish_succeeds_for_a_complete_listing_with_eligible_owning_principal(
    lifecycle_conn: Any,
) -> None:
    account = _account("ACC-PUB")
    org = _org("ORG-PUB")
    membership = _membership("OM-PUB", account, org)
    _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-PUB",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-PUB",
        market_episode_id="ME-PUB",
        offer_revision_id="REV-PUB",
    )
    lifecycle_conn.commit()

    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-PUB"),
    )

    assert result.status is LifecycleTransitionStatus.TRANSITIONED
    assert isinstance(result.transition_id, PublicationTransitionId)

    state = fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-PUB"))
    assert state is NativeListingLifecycleState.ACTIVE

    transitions = list_publication_transitions(lifecycle_conn, NativeListingId("NL-PUB"))
    assert len(transitions) == 1
    assert transitions[0].from_state is NativeListingLifecycleState.DRAFT
    assert transitions[0].to_state is NativeListingLifecycleState.ACTIVE
    assert transitions[0].actor_account_id == account
    assert transitions[0].publishing_organization_id == org.id
    assert transitions[0].transition_id == result.transition_id


def test_publish_fails_closed_for_an_incomplete_listing(lifecycle_conn: Any) -> None:
    account = _account("ACC-INC")
    org = _org("ORG-INC")
    membership = _membership("OM-INC", account, org)
    _create_incomplete_listing(
        lifecycle_conn, listing_id="NL-INC", account=account, org=org, membership=membership
    )
    lifecycle_conn.commit()

    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-INC"),
    )

    assert result.status is LifecycleTransitionStatus.INCOMPLETE_LISTING
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-INC")) is (
        NativeListingLifecycleState.DRAFT
    )
    assert list_publication_transitions(lifecycle_conn, NativeListingId("NL-INC")) == []


def test_publish_fails_closed_for_missing_listing(lifecycle_conn: Any) -> None:
    account = _account("ACC-MISS")
    org = _org("ORG-MISS")
    membership = _membership("OM-MISS", account, org)

    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-NEVER-CREATED-2"),
    )

    assert result.status is LifecycleTransitionStatus.NATIVE_LISTING_NOT_FOUND


def test_publish_denied_for_wrong_organization_leaves_state_and_history_unchanged(
    lifecycle_conn: Any,
) -> None:
    account = _account("ACC-WRONG")
    owning_org = _org("ORG-OWNER")
    other_org = _org("ORG-OTHER")
    owning_membership = _membership("OM-OWNER", account, owning_org)
    other_membership = _membership("OM-OTHER", account, other_org)
    _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-WRONG",
        account=account,
        org=owning_org,
        membership=owning_membership,
        physical_boat_id="PB-WRONG",
        market_episode_id="ME-WRONG",
        offer_revision_id="REV-WRONG",
    )
    lifecycle_conn.commit()

    # Eligible within ORG-OTHER, but ORG-OTHER does not own this listing.
    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-WRONG"),
    )

    assert result.status is LifecycleTransitionStatus.ORGANIZATION_MISMATCH
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-WRONG")) is (
        NativeListingLifecycleState.DRAFT
    )
    assert list_publication_transitions(lifecycle_conn, NativeListingId("NL-WRONG")) == []


@pytest.mark.parametrize(
    ("membership_factory", "expected_reason"),
    [
        (lambda acc, org: None, PublishingEligibilityReason.NO_MEMBERSHIP),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-ACCOUNT-MISMATCH"),
                account_id=AccountId("ACC-SOMEONE-ELSE"),
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            ),
            PublishingEligibilityReason.ACCOUNT_MISMATCH,
        ),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-NOROLE"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.ACTIVE,
            ),
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        ),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-INACTIVE"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.INACTIVE,
            ),
            PublishingEligibilityReason.MEMBERSHIP_INACTIVE,
        ),
    ],
)
def test_publish_denied_authorization_matrix_leaves_state_and_history_unchanged(
    lifecycle_conn: Any, membership_factory: Any, expected_reason: PublishingEligibilityReason
) -> None:
    account = _account("ACC-MATRIX")
    org = _org("ORG-MATRIX")
    creation_membership = _membership("OM-CREATE", account, org)
    _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-MATRIX",
        account=account,
        org=org,
        membership=creation_membership,
        physical_boat_id="PB-MATRIX",
        market_episode_id="ME-MATRIX",
        offer_revision_id="REV-MATRIX",
    )
    lifecycle_conn.commit()

    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership_factory(account, org),
        native_listing_id=NativeListingId("NL-MATRIX"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED
    assert result.denial_reason is expected_reason
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-MATRIX")) is (
        NativeListingLifecycleState.DRAFT
    )
    assert list_publication_transitions(lifecycle_conn, NativeListingId("NL-MATRIX")) == []


@pytest.mark.parametrize(
    ("eligibility", "expected_reason"),
    [
        (
            OrganizationPublishingEligibility.INELIGIBLE,
            PublishingEligibilityReason.ORGANIZATION_INELIGIBLE,
        ),
        (
            OrganizationPublishingEligibility.UNVERIFIED,
            PublishingEligibilityReason.ORGANIZATION_UNVERIFIED,
        ),
    ],
)
def test_publish_denied_for_ineligible_or_unverified_organization(
    lifecycle_conn: Any, eligibility: OrganizationPublishingEligibility, expected_reason: Any
) -> None:
    account = _account("ACC-ORGSTATE")
    eligible_org = _org("ORG-ORGSTATE")
    membership = _membership("OM-ORGSTATE", account, eligible_org)
    _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-ORGSTATE",
        account=account,
        org=eligible_org,
        membership=membership,
        physical_boat_id="PB-ORGSTATE",
        market_episode_id="ME-ORGSTATE",
        offer_revision_id="REV-ORGSTATE",
    )
    lifecycle_conn.commit()

    # Same Organization identity, now re-evaluated with a degraded eligibility
    # state -- proves the Organization-side gate is re-checked at transition
    # time, not only at NativeListing creation time.
    degraded_org = _org("ORG-ORGSTATE", eligibility=eligibility)
    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=degraded_org,
        membership=membership,
        native_listing_id=NativeListingId("NL-ORGSTATE"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED
    assert result.denial_reason is expected_reason


# ---------------------------------------------------------------------------
# Withdraw (ACTIVE -> WITHDRAWN)
# ---------------------------------------------------------------------------


def _published(
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
    _create_complete_listing(
        conn,
        listing_id=listing_id,
        account=account,
        org=org,
        membership=membership,
        physical_boat_id=physical_boat_id,
        market_episode_id=market_episode_id,
        offer_revision_id=offer_revision_id,
    )
    conn.commit()
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status is LifecycleTransitionStatus.TRANSITIONED


def test_withdraw_succeeds_for_active_listing_with_eligible_owning_principal(
    lifecycle_conn: Any,
) -> None:
    account = _account("ACC-WD")
    org = _org("ORG-WD")
    membership = _membership("OM-WD", account, org)
    _published(
        lifecycle_conn,
        listing_id="NL-WD",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-WD",
        market_episode_id="ME-WD",
        offer_revision_id="REV-WD",
    )

    result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-WD"),
    )

    assert result.status is LifecycleTransitionStatus.TRANSITIONED
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-WD")) is (
        NativeListingLifecycleState.WITHDRAWN
    )
    transitions = list_publication_transitions(lifecycle_conn, NativeListingId("NL-WD"))
    assert len(transitions) == 2
    assert transitions[1].from_state is NativeListingLifecycleState.ACTIVE
    assert transitions[1].to_state is NativeListingLifecycleState.WITHDRAWN


def test_withdraw_denied_for_wrong_organization_leaves_state_and_history_unchanged(
    lifecycle_conn: Any,
) -> None:
    account = _account("ACC-WDW")
    owning_org = _org("ORG-WDOWNER")
    other_org = _org("ORG-WDOTHER")
    owning_membership = _membership("OM-WDOWNER", account, owning_org)
    other_membership = _membership("OM-WDOTHER", account, other_org)
    _published(
        lifecycle_conn,
        listing_id="NL-WDW",
        account=account,
        org=owning_org,
        membership=owning_membership,
        physical_boat_id="PB-WDW",
        market_episode_id="ME-WDW",
        offer_revision_id="REV-WDW",
    )

    result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=other_org,
        membership=other_membership,
        native_listing_id=NativeListingId("NL-WDW"),
    )

    assert result.status is LifecycleTransitionStatus.ORGANIZATION_MISMATCH
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-WDW")) is (
        NativeListingLifecycleState.ACTIVE
    )
    assert len(list_publication_transitions(lifecycle_conn, NativeListingId("NL-WDW"))) == 1


@pytest.mark.parametrize(
    ("membership_factory", "expected_reason"),
    [
        (lambda acc, org: None, PublishingEligibilityReason.NO_MEMBERSHIP),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-WD-ACCOUNT-MISMATCH"),
                account_id=AccountId("ACC-WD-SOMEONE-ELSE"),
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            ),
            PublishingEligibilityReason.ACCOUNT_MISMATCH,
        ),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-WD-NOROLE"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.MEMBER}),
                state=MembershipState.ACTIVE,
            ),
            PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED,
        ),
        (
            lambda acc, org: OrganizationMembership(
                id=OrganizationMembershipId("OM-WD-INACTIVE"),
                account_id=acc,
                organization_id=org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.INACTIVE,
            ),
            PublishingEligibilityReason.MEMBERSHIP_INACTIVE,
        ),
    ],
)
def test_withdraw_denied_authorization_matrix_leaves_state_and_history_unchanged(
    lifecycle_conn: Any, membership_factory: Any, expected_reason: PublishingEligibilityReason
) -> None:
    account = _account("ACC-WDMATRIX")
    org = _org("ORG-WDMATRIX")
    creation_membership = _membership("OM-WDCREATE", account, org)
    _published(
        lifecycle_conn,
        listing_id="NL-WDMATRIX",
        account=account,
        org=org,
        membership=creation_membership,
        physical_boat_id="PB-WDMATRIX",
        market_episode_id="ME-WDMATRIX",
        offer_revision_id="REV-WDMATRIX",
    )

    result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership_factory(account, org),
        native_listing_id=NativeListingId("NL-WDMATRIX"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED
    assert result.denial_reason is expected_reason
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-WDMATRIX")) is (
        NativeListingLifecycleState.ACTIVE
    )
    # Exactly the original publish transition -- the denied withdraw attempt
    # appends no additional audit row.
    assert len(list_publication_transitions(lifecycle_conn, NativeListingId("NL-WDMATRIX"))) == 1


@pytest.mark.parametrize(
    ("eligibility", "expected_reason"),
    [
        (
            OrganizationPublishingEligibility.INELIGIBLE,
            PublishingEligibilityReason.ORGANIZATION_INELIGIBLE,
        ),
        (
            OrganizationPublishingEligibility.UNVERIFIED,
            PublishingEligibilityReason.ORGANIZATION_UNVERIFIED,
        ),
    ],
)
def test_withdraw_denied_for_ineligible_or_unverified_organization(
    lifecycle_conn: Any, eligibility: OrganizationPublishingEligibility, expected_reason: Any
) -> None:
    account = _account("ACC-WDORGSTATE")
    eligible_org = _org("ORG-WDORGSTATE")
    membership = _membership("OM-WDORGSTATE", account, eligible_org)
    _published(
        lifecycle_conn,
        listing_id="NL-WDORGSTATE",
        account=account,
        org=eligible_org,
        membership=membership,
        physical_boat_id="PB-WDORGSTATE",
        market_episode_id="ME-WDORGSTATE",
        offer_revision_id="REV-WDORGSTATE",
    )

    # Same Organization identity, now re-evaluated with a degraded eligibility
    # state -- proves the Organization-side gate is re-checked at withdraw
    # time too, not only at publish/creation time.
    degraded_org = _org("ORG-WDORGSTATE", eligibility=eligibility)
    result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=degraded_org,
        membership=membership,
        native_listing_id=NativeListingId("NL-WDORGSTATE"),
    )

    assert result.status is LifecycleTransitionStatus.DENIED
    assert result.denial_reason is expected_reason
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-WDORGSTATE")) is (
        NativeListingLifecycleState.ACTIVE
    )
    assert len(list_publication_transitions(lifecycle_conn, NativeListingId("NL-WDORGSTATE"))) == 1


def test_withdraw_of_never_created_listing_not_found(lifecycle_conn: Any) -> None:
    account = _account("ACC-WDNF")
    org = _org("ORG-WDNF")
    membership = _membership("OM-WDNF", account, org)

    result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-WDNF-NEVER-CREATED"),
    )

    assert result.status is LifecycleTransitionStatus.NATIVE_LISTING_NOT_FOUND


# ---------------------------------------------------------------------------
# Unsupported/stale transitions
# ---------------------------------------------------------------------------


def test_withdraw_of_draft_listing_is_unsupported_current_state_conflict(
    lifecycle_conn: Any,
) -> None:
    account = _account("ACC-DW")
    org = _org("ORG-DW")
    membership = _membership("OM-DW", account, org)
    _create_incomplete_listing(
        lifecycle_conn, listing_id="NL-DW", account=account, org=org, membership=membership
    )
    lifecycle_conn.commit()

    result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DW"),
    )

    assert result.status is LifecycleTransitionStatus.CURRENT_STATE_CONFLICT
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-DW")) is (
        NativeListingLifecycleState.DRAFT
    )
    assert list_publication_transitions(lifecycle_conn, NativeListingId("NL-DW")) == []


def test_republish_of_withdrawn_listing_is_unsupported(lifecycle_conn: Any) -> None:
    account = _account("ACC-REPUB")
    org = _org("ORG-REPUB")
    membership = _membership("OM-REPUB", account, org)
    _published(
        lifecycle_conn,
        listing_id="NL-REPUB",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-REPUB",
        market_episode_id="ME-REPUB",
        offer_revision_id="REV-REPUB",
    )
    withdraw_result = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-REPUB"),
    )
    assert withdraw_result.status is LifecycleTransitionStatus.TRANSITIONED

    republish_result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-REPUB"),
    )

    assert republish_result.status is LifecycleTransitionStatus.CURRENT_STATE_CONFLICT
    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-REPUB")) is (
        NativeListingLifecycleState.WITHDRAWN
    )
    assert len(list_publication_transitions(lifecycle_conn, NativeListingId("NL-REPUB"))) == 2


def test_double_publish_of_already_active_listing_is_unsupported(lifecycle_conn: Any) -> None:
    account = _account("ACC-DBLPUB")
    org = _org("ORG-DBLPUB")
    membership = _membership("OM-DBLPUB", account, org)
    _published(
        lifecycle_conn,
        listing_id="NL-DBLPUB",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-DBLPUB",
        market_episode_id="ME-DBLPUB",
        offer_revision_id="REV-DBLPUB",
    )

    second_publish = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DBLPUB"),
    )

    assert second_publish.status is LifecycleTransitionStatus.CURRENT_STATE_CONFLICT
    assert len(list_publication_transitions(lifecycle_conn, NativeListingId("NL-DBLPUB"))) == 1


def test_double_withdraw_of_already_withdrawn_listing_is_unsupported(lifecycle_conn: Any) -> None:
    account = _account("ACC-DBLWD")
    org = _org("ORG-DBLWD")
    membership = _membership("OM-DBLWD", account, org)
    _published(
        lifecycle_conn,
        listing_id="NL-DBLWD",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-DBLWD",
        market_episode_id="ME-DBLWD",
        offer_revision_id="REV-DBLWD",
    )
    first_withdraw = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DBLWD"),
    )
    assert first_withdraw.status is LifecycleTransitionStatus.TRANSITIONED

    second_withdraw = withdraw_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-DBLWD"),
    )

    assert second_withdraw.status is LifecycleTransitionStatus.CURRENT_STATE_CONFLICT
    # Two total: the publish from `_published()` plus the one successful
    # withdraw above -- the denied second withdraw appends no third record.
    assert len(list_publication_transitions(lifecycle_conn, NativeListingId("NL-DBLWD"))) == 2


# ---------------------------------------------------------------------------
# Transaction ownership
# ---------------------------------------------------------------------------


def test_publish_raises_on_a_non_idle_connection(lifecycle_conn: Any) -> None:
    account = _account("ACC-TXN")
    org = _org("ORG-TXN")
    membership = _membership("OM-TXN", account, org)
    _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-TXN",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-TXN",
        market_episode_id="ME-TXN",
        offer_revision_id="REV-TXN",
    )
    # Open an implicit transaction on lifecycle_conn via a plain readback
    # (never committed/rolled back), exactly as a caller composing
    # "check, then transition" on one connection would naturally do.
    pre_check = fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-TXN"))
    assert pre_check is NativeListingLifecycleState.DRAFT
    from psycopg.pq import TransactionStatus

    assert lifecycle_conn.info.transaction_status != TransactionStatus.IDLE

    with pytest.raises(NativeListingLifecycleTransactionOwnershipError):
        publish_native_listing(
            lifecycle_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-TXN"),
        )


# ---------------------------------------------------------------------------
# Real PostgreSQL concurrency
# ---------------------------------------------------------------------------


def test_concurrent_publish_attempts_apply_exactly_once(lifecycle_url: str) -> None:
    """Two concurrent DRAFT -> ACTIVE attempts for the same listing must
    resolve as exactly one TRANSITIONED and one CURRENT_STATE_CONFLICT, with
    exactly one matching immutable publication record and a final ACTIVE
    state."""
    setup_conn = psycopg.connect(lifecycle_url)
    try:
        account = _account("ACC-CRACE")
        org = _org("ORG-CRACE")
        membership = _membership("OM-CRACE", account, org)
        _create_complete_listing(
            setup_conn,
            listing_id="NL-CRACE",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-CRACE",
            market_episode_id="ME-CRACE",
            offer_revision_id="REV-CRACE",
        )
        setup_conn.commit()
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                result = publish_native_listing(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-CRACE"),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [threading.Thread(target=_worker), threading.Thread(target=_worker)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(LifecycleTransitionStatus.TRANSITIONED) == 1, statuses
    assert statuses.count(LifecycleTransitionStatus.CURRENT_STATE_CONFLICT) == 1, statuses

    verify = psycopg.connect(lifecycle_url)
    try:
        assert fetch_lifecycle_state(verify, NativeListingId("NL-CRACE")) is (
            NativeListingLifecycleState.ACTIVE
        )
        transitions = list_publication_transitions(verify, NativeListingId("NL-CRACE"))
        assert len(transitions) == 1
    finally:
        verify.close()


# ---------------------------------------------------------------------------
# Atomic rollback / lifecycle CHECK constraint
# ---------------------------------------------------------------------------


def test_transition_rolls_back_atomically_when_the_audit_insert_fails(
    lifecycle_conn: Any, lifecycle_url: str
) -> None:
    """Inject a real PostgreSQL failure between the lifecycle UPDATE and the
    publication-transition INSERT -- both inside the same
    ``with conn.transaction()`` block in ``_apply_transition`` -- via a
    temporary CHECK constraint on the audit table that only this test's
    NativeListingId violates. Production code is not touched or weakened;
    the failure is injected purely through a schema object scoped to this
    test's disposable schema.

    The whole transaction must roll back: the lifecycle UPDATE that already
    ran earlier in the same transaction must be undone too, and no
    unmatched/partial audit row may exist."""
    account = _account("ACC-ROLLBACK")
    org = _org("ORG-ROLLBACK")
    membership = _membership("OM-ROLLBACK", account, org)
    _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-ROLLBACK",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-ROLLBACK",
        market_episode_id="ME-ROLLBACK",
        offer_revision_id="REV-ROLLBACK",
    )
    with lifecycle_conn.cursor() as cur:
        cur.execute(
            "ALTER TABLE native_listing_publication_transitions "
            "ADD CONSTRAINT test_fail_inject_rollback "
            "CHECK (native_listing_id <> 'NL-ROLLBACK')"
        )
    lifecycle_conn.commit()

    with pytest.raises(psycopg.errors.CheckViolation):
        publish_native_listing(
            lifecycle_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-ROLLBACK"),
        )
    # psycopg's `with conn.transaction()` already issued the ROLLBACK as part
    # of propagating the exception; this is a defensive no-op if so.
    lifecycle_conn.rollback()

    verify = psycopg.connect(lifecycle_url)
    try:
        state = fetch_lifecycle_state(verify, NativeListingId("NL-ROLLBACK"))
        assert state is NativeListingLifecycleState.DRAFT
        assert list_publication_transitions(verify, NativeListingId("NL-ROLLBACK")) == []
    finally:
        verify.close()


def test_lifecycle_state_check_constraint_rejects_invalid_value(
    lifecycle_conn: Any, lifecycle_url: str
) -> None:
    """The ``native_listings_lifecycle_state_valid`` CHECK constraint added
    by the SLICE-0049 migration must reject any value outside
    DRAFT/ACTIVE/WITHDRAWN at the database level -- not merely at the Python
    enum layer -- and must leave the durable valid value untouched."""
    account = _account("ACC-CHECK")
    org = _org("ORG-CHECK")
    membership = _membership("OM-CHECK", account, org)
    _create_incomplete_listing(
        lifecycle_conn, listing_id="NL-CHECK", account=account, org=org, membership=membership
    )
    lifecycle_conn.commit()

    with pytest.raises(psycopg.errors.CheckViolation), lifecycle_conn.cursor() as cur:
        cur.execute(
            "UPDATE native_listings SET lifecycle_state = %s WHERE native_listing_id = %s",
            ("BOGUS", "NL-CHECK"),
        )
    lifecycle_conn.rollback()

    verify = psycopg.connect(lifecycle_url)
    try:
        state = fetch_lifecycle_state(verify, NativeListingId("NL-CHECK"))
        assert state is NativeListingLifecycleState.DRAFT
    finally:
        verify.close()
