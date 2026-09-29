"""PostgreSQL-backed NativeListing lifecycle persistence tests — SLICE-0049.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0049 Alembic head, mirroring the SLICE-0043/
0045/0047 integration test isolation pattern.
"""

from __future__ import annotations

import threading
import time
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
from hullq.domain.media_gallery import MediaAssetId, MediaSourceKind
from hullq.domain.native_listing_lifecycle import (
    NativeListingLifecycleState,
    PublicationTransitionId,
)
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.publication_readiness import PublicationBlockerReason
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
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    RetireAssetOutcome,
    create_uploaded_image_placement,
    insert_approved_media_asset,
    retire_media_asset,
    set_cover,
)
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
    fetch_current_native_listing_offer,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)

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


def _ready_physical_boat_claim() -> PhysicalBoatClaimSnapshot:
    """SLICE-0069 D22-ready PhysicalBoat claim: bounded brand/model plus a
    valid build year -- the minimum required PhysicalBoat response set."""
    return PhysicalBoatClaimSnapshot(
        marketed_brand_claim="Beneteau",
        model_designation_claim="Oceanis 30.1",
        build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, 2020),
    )


def _ensure_account_row(conn: Any, account: AccountId) -> None:
    """`media_assets.uploaded_by_account_id` (unlike the SLICE-0043/45/50
    tables this file otherwise exercises) carries a real FK to `accounts` --
    insert the row this test's in-memory `AccountId` needs before attaching
    media, mirroring `test_broker_inventory_lifecycle_api.py`'s identical
    `_ensure_account` helper."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
            [account.value],
        )


def _attach_ready_cover_image(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization, account: AccountId
) -> tuple[str, str]:
    """Attach one approved, rights-declared IMAGE placement and set it as the
    explicit cover -- the SLICE-0069 D22 minimum required media state.

    `media_assets` carries real FKs to `accounts`/`marketplace_organizations`
    (unlike the SLICE-0043/45/50 tables this file otherwise exercises, which
    persist Organization/Account identity as plain unconstrained text) --
    both rows are idempotently seeded here first.
    """
    _ensure_account_row(conn, account)
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
    assert placement_result.media_placement_id is not None
    assert placement_result.gallery_version is not None
    cover_result = set_cover(
        conn,
        native_listing_id=NativeListingId(listing_id),
        owner_organization_id=org.id,
        media_placement_id=placement_result.media_placement_id,
        expected_version=placement_result.gallery_version,
    )
    assert cover_result.outcome.value == "SET", cover_result
    return asset.media_asset_id.value, placement_result.media_placement_id.value


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
) -> tuple[str, str]:
    """Create/reuse a full durable chain satisfying the SLICE-0069 canonical
    D22 PublicationReadiness rule set (episode/boat/offer/claim/media/cover).

    Returns the ``(media_asset_id, media_placement_id)`` of the attached
    cover image, for tests that need to mutate it afterward."""
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
    claim_result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
        expected_current_revision_id=None,
        claims=_ready_physical_boat_claim(),
    )
    assert claim_result.status.value in ("created", "already_exists"), claim_result
    return _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)


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
# Independent review amendment (Finding A):
# `MARKETPLACE_PUBLICATION_READINESS_CONTRACT.v0.1.md` SS18/22 required
# concurrency proofs -- offer revision, PhysicalBoat claim revision and
# readiness-relevant media mutation each racing a publish attempt, plus no
# deadlock with the accepted 0068 media lock order.
# ---------------------------------------------------------------------------


def _hold_native_listing_row_lock(
    url: str, listing_id: str, *, acquired: threading.Event, release: threading.Event
) -> None:
    """Open a real transaction and take the exact ``SELECT ... FOR UPDATE``
    lock every readiness-relevant writer (offer revision, PhysicalBoat claim
    revision, media cover/remove/retire -- see `hullq.persistence.
    publication_readiness` module docstring) and `publish_native_listing`
    itself all take on this same `native_listings` row. A deterministic
    stand-in for "some readiness-relevant transaction is currently in
    flight", used to prove a concurrent publish attempt genuinely blocks on
    that row lock rather than reading through it -- without duplicating any
    writer's own business logic."""
    conn = psycopg.connect(url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT native_listing_id FROM native_listings WHERE native_listing_id = %s FOR UPDATE",
                [listing_id],
            )
        acquired.set()
        release.wait(timeout=10)
    finally:
        conn.rollback()
        conn.close()


def _wait_until_backend_blocked_on_lock(
    url: str, backend_pid: int, *, timeout: float = 10.0
) -> None:
    """Bounded condition-poll of PostgreSQL's own
    `pg_stat_activity.wait_event_type` confirming *backend_pid* is genuinely
    waiting to acquire a lock -- deterministic proof of blocking behavior,
    not a fixed-timing guess about how long blocking takes."""
    admin = psycopg.connect(url)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            with admin.cursor() as cur:
                cur.execute(
                    "SELECT wait_event_type FROM pg_stat_activity WHERE pid = %s", [backend_pid]
                )
                row = cur.fetchone()
            if row is not None and row[0] == "Lock":
                return
            time.sleep(0.02)
    finally:
        admin.close()
    pytest.fail(f"backend {backend_pid} never entered a Lock wait state within {timeout}s")


def test_publish_blocks_on_an_in_flight_readiness_relevant_transaction_and_resolves_after_release(
    lifecycle_url: str,
) -> None:
    """SS18/22: publish must serialize on the same `native_listings` row
    every offer-revision, PhysicalBoat-claim-revision and readiness-relevant
    media mutation already locks -- it cannot read through an in-flight
    change. This holds that exact row lock open on one connection, proves a
    real `publish_native_listing` call on a second, independent connection
    genuinely blocks (observed via PostgreSQL's own lock-wait state, not
    timing), then releases the hold and proves publish resolves to exactly
    one coherent TRANSITIONED result afterward."""
    setup_conn = psycopg.connect(lifecycle_url)
    try:
        account = _account("ACC-LOCKPROOF")
        org = _org("ORG-LOCKPROOF")
        membership = _membership("OM-LOCKPROOF", account, org)
        _create_complete_listing(
            setup_conn,
            listing_id="NL-LOCKPROOF",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-LOCKPROOF",
            market_episode_id="ME-LOCKPROOF",
            offer_revision_id="REV-LOCKPROOF",
        )
        setup_conn.commit()
    finally:
        setup_conn.close()

    acquired = threading.Event()
    release = threading.Event()
    holder = threading.Thread(
        target=_hold_native_listing_row_lock,
        args=(lifecycle_url, "NL-LOCKPROOF"),
        kwargs={"acquired": acquired, "release": release},
    )
    holder.start()
    assert acquired.wait(timeout=10), "lock holder never acquired the row lock"

    publish_conn = psycopg.connect(lifecycle_url)
    backend_pid = publish_conn.info.backend_pid
    publish_results: list[Any] = []
    publish_errors: list[BaseException] = []

    def _publish() -> None:
        try:
            publish_results.append(
                publish_native_listing(
                    publish_conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-LOCKPROOF"),
                )
            )
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            publish_errors.append(exc)

    publisher = threading.Thread(target=_publish)
    publisher.start()

    _wait_until_backend_blocked_on_lock(lifecycle_url, backend_pid)
    assert publish_results == [], "publish returned before the held lock was released"

    release.set()
    holder.join(timeout=10)
    publisher.join(timeout=10)
    assert not holder.is_alive(), "lock holder thread did not finish -- possible deadlock"
    assert not publisher.is_alive(), "publisher thread did not finish -- possible deadlock"
    publish_conn.close()

    assert not publish_errors, f"publish thread errors: {publish_errors}"
    assert len(publish_results) == 1
    assert publish_results[0].status is LifecycleTransitionStatus.TRANSITIONED, publish_results[0]

    verify = psycopg.connect(lifecycle_url)
    try:
        assert fetch_lifecycle_state(verify, NativeListingId("NL-LOCKPROOF")) is (
            NativeListingLifecycleState.ACTIVE
        )
        assert len(list_publication_transitions(verify, NativeListingId("NL-LOCKPROOF"))) == 1
    finally:
        verify.close()


def test_concurrent_offer_revision_and_publish_resolve_to_one_coherent_result(
    lifecycle_url: str,
) -> None:
    """A concurrent *valid* offer-revision write and a publish attempt must
    serialize on the shared `native_listings` row lock. The typed
    `NativeListingOfferSnapshot` construction guarantee means an existing
    revision is always D22-valid, so no ordering can turn READY into
    BLOCKED here -- the property under test is that both operations complete
    without error/deadlock, publish transitions exactly once, and the
    durable offer head coherently reflects the new revision regardless of
    which operation PostgreSQL happened to run first."""
    setup_conn = psycopg.connect(lifecycle_url)
    try:
        account = _account("ACC-OFFERRACE")
        org = _org("ORG-OFFERRACE")
        membership = _membership("OM-OFFERRACE", account, org)
        _create_complete_listing(
            setup_conn,
            listing_id="NL-OFFERRACE",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-OFFERRACE",
            market_episode_id="ME-OFFERRACE",
            offer_revision_id="REV-OFFERRACE",
        )
        setup_conn.commit()
    finally:
        setup_conn.close()

    barrier = threading.Barrier(2)
    offer_results: list[Any] = []
    publish_results: list[Any] = []
    errors: list[BaseException] = []

    def _write_offer() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                offer_results.append(
                    write_native_listing_offer_revision(
                        conn,
                        account_id=account,
                        candidate_organization=org,
                        membership=membership,
                        native_listing_id=NativeListingId("NL-OFFERRACE"),
                        revision_id=NativeListingOfferRevisionId("REV-OFFERRACE-2"),
                        expected_current_revision_id=NativeListingOfferRevisionId("REV-OFFERRACE"),
                        offer=_amount_offer(),
                    )
                )
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    def _publish() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                publish_results.append(
                    publish_native_listing(
                        conn,
                        account_id=account,
                        candidate_organization=org,
                        membership=membership,
                        native_listing_id=NativeListingId("NL-OFFERRACE"),
                    )
                )
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [threading.Thread(target=_write_offer), threading.Thread(target=_publish)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert not any(t.is_alive() for t in threads), "a thread did not finish -- possible deadlock"
    assert len(offer_results) == 1
    assert len(publish_results) == 1
    assert offer_results[0].status.value == "revised", offer_results[0]
    assert publish_results[0].status is LifecycleTransitionStatus.TRANSITIONED, publish_results[0]

    verify = psycopg.connect(lifecycle_url)
    try:
        assert fetch_lifecycle_state(verify, NativeListingId("NL-OFFERRACE")) is (
            NativeListingLifecycleState.ACTIVE
        )
        assert len(list_publication_transitions(verify, NativeListingId("NL-OFFERRACE"))) == 1
        current_offer = fetch_current_native_listing_offer(verify, NativeListingId("NL-OFFERRACE"))
        assert current_offer is not None
        assert current_offer.revision_id.value == "REV-OFFERRACE-2"
    finally:
        verify.close()


def test_concurrent_physical_boat_claim_revision_and_publish_resolve_to_one_coherent_result(
    lifecycle_url: str,
) -> None:
    """The PhysicalBoat-claim analogue of the offer-revision race above: the
    typed `PhysicalBoatClaimSnapshot` construction guarantee means an
    existing revision is always D22-valid, so this proves atomic
    serialization and a coherent final claim head, not a readiness flip."""
    setup_conn = psycopg.connect(lifecycle_url)
    try:
        account = _account("ACC-CLAIMRACE")
        org = _org("ORG-CLAIMRACE")
        membership = _membership("OM-CLAIMRACE", account, org)
        _create_complete_listing(
            setup_conn,
            listing_id="NL-CLAIMRACE",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-CLAIMRACE",
            market_episode_id="ME-CLAIMRACE",
            offer_revision_id="REV-CLAIMRACE",
        )
        setup_conn.commit()
    finally:
        setup_conn.close()

    barrier = threading.Barrier(2)
    claim_results: list[Any] = []
    publish_results: list[Any] = []
    errors: list[BaseException] = []

    def _write_claim() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                claim_results.append(
                    write_physical_boat_claim_revision(
                        conn,
                        account_id=account,
                        candidate_organization=org,
                        membership=membership,
                        native_listing_id=NativeListingId("NL-CLAIMRACE"),
                        revision_id=PhysicalBoatClaimRevisionId("CLAIM-NL-CLAIMRACE-2"),
                        expected_current_revision_id=PhysicalBoatClaimRevisionId(
                            "CLAIM-NL-CLAIMRACE"
                        ),
                        claims=_ready_physical_boat_claim(),
                    )
                )
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    def _publish() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                publish_results.append(
                    publish_native_listing(
                        conn,
                        account_id=account,
                        candidate_organization=org,
                        membership=membership,
                        native_listing_id=NativeListingId("NL-CLAIMRACE"),
                    )
                )
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [threading.Thread(target=_write_claim), threading.Thread(target=_publish)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert not any(t.is_alive() for t in threads), "a thread did not finish -- possible deadlock"
    assert len(claim_results) == 1
    assert len(publish_results) == 1
    assert claim_results[0].status.value == "revised", claim_results[0]
    assert publish_results[0].status is LifecycleTransitionStatus.TRANSITIONED, publish_results[0]

    verify = psycopg.connect(lifecycle_url)
    try:
        assert fetch_lifecycle_state(verify, NativeListingId("NL-CLAIMRACE")) is (
            NativeListingLifecycleState.ACTIVE
        )
        assert len(list_publication_transitions(verify, NativeListingId("NL-CLAIMRACE"))) == 1
        current_claim = fetch_current_physical_boat_claim(
            verify, PhysicalBoatId("PB-CLAIMRACE"), org.id
        )
        assert current_claim is not None
        assert current_claim.revision_id.value == "CLAIM-NL-CLAIMRACE-2"
    finally:
        verify.close()


def test_cover_image_retirement_before_publish_leaves_the_draft_blocked_on_authoritative_recheck(
    lifecycle_conn: Any,
) -> None:
    """Independent review Finding A, writer-first ordering: retiring the
    listing's only cover image before a publish attempt must leave publish
    BLOCKED on its own authoritative in-transaction re-evaluation -- a stale
    advisory preflight (or no preflight at all) is never a capability
    token."""
    account = _account("ACC-MEDIAFIRST")
    org = _org("ORG-MEDIAFIRST")
    membership = _membership("OM-MEDIAFIRST", account, org)
    media_asset_id, _media_placement_id = _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-MEDIAFIRST",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-MEDIAFIRST",
        market_episode_id="ME-MEDIAFIRST",
        offer_revision_id="REV-MEDIAFIRST",
    )
    lifecycle_conn.commit()

    with lifecycle_conn.transaction():
        outcome = retire_media_asset(
            lifecycle_conn,
            media_asset_id=MediaAssetId(media_asset_id),
            owner_organization_id=org.id,
        )
    assert outcome is RetireAssetOutcome.RETIRED, outcome

    result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-MEDIAFIRST"),
    )
    assert result.status is LifecycleTransitionStatus.INCOMPLETE_LISTING, result
    assert result.blockers == frozenset(
        {PublicationBlockerReason.NO_PUBLIC_USABLE_IMAGE, PublicationBlockerReason.COVER_MISSING}
    ), result.blockers

    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-MEDIAFIRST")) is (
        NativeListingLifecycleState.DRAFT
    )


def test_publish_then_cover_image_retirement_is_rejected_by_the_active_media_invariant(
    lifecycle_conn: Any,
) -> None:
    """Independent review Finding A, publish-first ordering: once a listing
    is ACTIVE, retiring its only cover image must be rejected by the
    existing SLICE-0068 ACTIVE-listing media invariant
    (`RetireAssetOutcome.ACTIVE_LISTING_CONFLICT`) rather than silently
    leaving a public listing without its required image/cover."""
    account = _account("ACC-MEDIASECOND")
    org = _org("ORG-MEDIASECOND")
    membership = _membership("OM-MEDIASECOND", account, org)
    media_asset_id, _media_placement_id = _create_complete_listing(
        lifecycle_conn,
        listing_id="NL-MEDIASECOND",
        account=account,
        org=org,
        membership=membership,
        physical_boat_id="PB-MEDIASECOND",
        market_episode_id="ME-MEDIASECOND",
        offer_revision_id="REV-MEDIASECOND",
    )
    lifecycle_conn.commit()

    publish_result = publish_native_listing(
        lifecycle_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-MEDIASECOND"),
    )
    assert publish_result.status is LifecycleTransitionStatus.TRANSITIONED, publish_result

    with lifecycle_conn.transaction():
        outcome = retire_media_asset(
            lifecycle_conn,
            media_asset_id=MediaAssetId(media_asset_id),
            owner_organization_id=org.id,
        )
    assert outcome is RetireAssetOutcome.ACTIVE_LISTING_CONFLICT, outcome

    assert fetch_lifecycle_state(lifecycle_conn, NativeListingId("NL-MEDIASECOND")) is (
        NativeListingLifecycleState.ACTIVE
    )


def test_concurrent_cover_image_retirement_and_publish_resolve_to_one_coherent_outcome_without_deadlock(
    lifecycle_url: str,
) -> None:
    """A concurrent retirement of the listing's only cover image and a
    publish attempt must serialize on the shared `native_listings` row lock
    (SS18: "no deadlock with accepted media lock order") and resolve to
    exactly one of the two valid orderings: either the retirement commits
    first and publish's own authoritative recheck then correctly reports
    BLOCKED, or publish commits first and the ACTIVE-listing media invariant
    then correctly rejects the retirement -- never a corrupted mix of both,
    and never a deadlock."""
    setup_conn = psycopg.connect(lifecycle_url)
    try:
        account = _account("ACC-MEDIARACE")
        org = _org("ORG-MEDIARACE")
        membership = _membership("OM-MEDIARACE", account, org)
        media_asset_id, _media_placement_id = _create_complete_listing(
            setup_conn,
            listing_id="NL-MEDIARACE",
            account=account,
            org=org,
            membership=membership,
            physical_boat_id="PB-MEDIARACE",
            market_episode_id="ME-MEDIARACE",
            offer_revision_id="REV-MEDIARACE",
        )
        setup_conn.commit()
    finally:
        setup_conn.close()

    barrier = threading.Barrier(2)
    retire_results: list[Any] = []
    publish_results: list[Any] = []
    errors: list[BaseException] = []

    def _retire() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                with conn.transaction():
                    outcome = retire_media_asset(
                        conn,
                        media_asset_id=MediaAssetId(media_asset_id),
                        owner_organization_id=org.id,
                    )
                retire_results.append(outcome)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    def _publish() -> None:
        try:
            conn = psycopg.connect(lifecycle_url)
            try:
                barrier.wait(timeout=10)
                publish_results.append(
                    publish_native_listing(
                        conn,
                        account_id=account,
                        candidate_organization=org,
                        membership=membership,
                        native_listing_id=NativeListingId("NL-MEDIARACE"),
                    )
                )
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [threading.Thread(target=_retire), threading.Thread(target=_publish)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert not any(t.is_alive() for t in threads), "a thread did not finish -- possible deadlock"
    assert len(retire_results) == 1
    assert len(publish_results) == 1

    verify = psycopg.connect(lifecycle_url)
    try:
        final_state = fetch_lifecycle_state(verify, NativeListingId("NL-MEDIARACE"))
        transitions = list_publication_transitions(verify, NativeListingId("NL-MEDIARACE"))
        if retire_results[0] is RetireAssetOutcome.RETIRED:
            # Retirement committed first: publish's own authoritative
            # recheck must have caught the resulting media loss.
            assert publish_results[0].status is LifecycleTransitionStatus.INCOMPLETE_LISTING, (
                publish_results[0]
            )
            assert PublicationBlockerReason.NO_PUBLIC_USABLE_IMAGE in publish_results[0].blockers, (
                publish_results[0].blockers
            )
            assert final_state is NativeListingLifecycleState.DRAFT
            assert len(transitions) == 0
        else:
            # Publish committed first: the ACTIVE-listing media invariant
            # must have rejected the retirement.
            assert retire_results[0] is RetireAssetOutcome.ACTIVE_LISTING_CONFLICT, retire_results[
                0
            ]
            assert publish_results[0].status is LifecycleTransitionStatus.TRANSITIONED, (
                publish_results[0]
            )
            assert final_state is NativeListingLifecycleState.ACTIVE
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
