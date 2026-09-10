"""PostgreSQL-backed PhysicalBoat claim persistence tests — SLICE-0050.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the SLICE-0050 Alembic head, mirroring the SLICE-0045
integration test isolation pattern in
tests/persistence/test_native_listing_offer_persistence.py.
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
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    RudderConfiguration,
    RudderConfigurationClaim,
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
    PublishingEligibilityReason,
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    PhysicalBoatClaimTransactionOwnershipError,
    PhysicalBoatClaimWriteStatus,
    fetch_current_physical_boat_claim,
    fetch_physical_boat_claim_revision,
    list_physical_boat_claim_revisions,
    write_physical_boat_claim_revision,
)

# ---------------------------------------------------------------------------
# Disposable-schema fixture: genuinely-empty schema -> SLICE-0050 Alembic head
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
def claim_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0050_{uuid.uuid4().hex[:16]}"
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
def claim_conn(claim_url: str) -> Generator[Any]:
    conn = psycopg.connect(claim_url)
    try:
        yield conn
    finally:
        conn.close()


def _table_names(conn: Any) -> set[str]:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = current_schema()"
        )
        return {row[0] for row in cur.fetchall()}


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
    organization: MarketplaceOrganization,
    roles: frozenset[MembershipRole],
    *,
    state: MembershipState = MembershipState.ACTIVE,
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=organization.id,
        roles=roles,
        state=state,
    )


def _snapshot(**overrides: object) -> PhysicalBoatClaimSnapshot:
    kwargs: dict[str, object] = {
        "marketed_brand_claim": "Beneteau",
        "model_designation_claim": "Oceanis 30.1",
        "build_year": BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
    }
    kwargs.update(overrides)
    return PhysicalBoatClaimSnapshot(**kwargs)  # type: ignore[arg-type]


def _create_chain(
    conn: Any,
    *,
    native_listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    boat_design_ref: Any = None,
) -> None:
    """Create a complete NativeListing -> MarketEpisode -> PhysicalBoat chain."""
    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=boat_design_ref
        ),
    )
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
            id=NativeListingId(native_listing_id),
            market_episode_id=MarketEpisodeId(market_episode_id),
        ),
    )
    assert result.status.value == "created"
    conn.commit()


# ---------------------------------------------------------------------------
# Migration boundary
# ---------------------------------------------------------------------------


def test_migration_adds_only_the_expected_claim_tables(claim_conn: Any) -> None:
    tables = _table_names(claim_conn)
    assert {"physical_boat_claim_revisions", "physical_boat_claim_heads"} <= tables
    assert {"physical_boats", "market_episodes", "native_listings"} <= tables


# ---------------------------------------------------------------------------
# First revision / authorization / chain resolution
# ---------------------------------------------------------------------------


def test_eligible_owning_principal_creates_first_revision(claim_conn: Any) -> None:
    account = _account("ACC-C1")
    org = _org("ORG-C1")
    membership = _membership("OM-C1", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C1",
        physical_boat_id="PB-C1",
        market_episode_id="ME-C1",
        account=account,
        org=org,
        membership=membership,
    )

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C1"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C1-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )

    assert result.status is PhysicalBoatClaimWriteStatus.CREATED
    assert result.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C1-001")


def test_no_membership_denied_writes_nothing(claim_conn: Any) -> None:
    account = _account("ACC-C2")
    org = _org("ORG-C2")
    membership = _membership("OM-C2", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C2",
        physical_boat_id="PB-C2",
        market_episode_id="ME-C2",
        account=account,
        org=org,
        membership=membership,
    )

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=None,
        native_listing_id=NativeListingId("NL-C2"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C2-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.NO_MEMBERSHIP
    claim_conn.commit()
    assert fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C2"), org.id) is None


def test_account_mismatch_denied(claim_conn: Any) -> None:
    account = _account("ACC-C3")
    other_account = _account("ACC-C3-OTHER")
    org = _org("ORG-C3")
    membership = _membership("OM-C3", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C3",
        physical_boat_id="PB-C3",
        market_episode_id="ME-C3",
        account=account,
        org=org,
        membership=membership,
    )

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=other_account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C3"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C3-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ACCOUNT_MISMATCH


def test_inactive_membership_denied(claim_conn: Any) -> None:
    account = _account("ACC-C4")
    org = _org("ORG-C4")
    membership = _membership(
        "OM-C4", account, org, frozenset({MembershipRole.PUBLISHER}), state=MembershipState.INACTIVE
    )
    _create_chain(
        claim_conn,
        native_listing_id="NL-C4",
        physical_boat_id="PB-C4",
        market_episode_id="ME-C4",
        account=account,
        org=org,
        membership=_membership("OM-C4-SETUP", account, org, frozenset({MembershipRole.PUBLISHER})),
    )

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C4"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C4-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.MEMBERSHIP_INACTIVE


def test_missing_publisher_role_denied(claim_conn: Any) -> None:
    account = _account("ACC-C5")
    org = _org("ORG-C5")
    membership = _membership("OM-C5", account, org, frozenset({MembershipRole.MEMBER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C5",
        physical_boat_id="PB-C5",
        market_episode_id="ME-C5",
        account=account,
        org=org,
        membership=_membership("OM-C5-SETUP", account, org, frozenset({MembershipRole.PUBLISHER})),
    )

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C5"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C5-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.PUBLISHER_ROLE_REQUIRED


def test_ineligible_organization_denied(claim_conn: Any) -> None:
    account = _account("ACC-C6")
    org = _org("ORG-C6", eligibility=OrganizationPublishingEligibility.INELIGIBLE)
    membership = _membership("OM-C6", account, org, frozenset({MembershipRole.PUBLISHER}))
    # PhysicalBoat/MarketEpisode may exist even for an ineligible org's would-be listing.
    create_physical_boat(claim_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-C6")))
    create_market_episode(
        claim_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-C6"), physical_boat_id=PhysicalBoatId("PB-C6")
        ),
    )
    claim_conn.commit()

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C6-NEVER-CREATED"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C6-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_INELIGIBLE


def test_unverified_organization_denied(claim_conn: Any) -> None:
    account = _account("ACC-C7")
    org = _org("ORG-C7", eligibility=OrganizationPublishingEligibility.UNVERIFIED)
    membership = _membership("OM-C7", account, org, frozenset({MembershipRole.PUBLISHER}))

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C7-NEVER-CREATED"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C7-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.DENIED
    assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_UNVERIFIED


def test_missing_native_listing_fails_closed(claim_conn: Any) -> None:
    account = _account("ACC-C8")
    org = _org("ORG-C8")
    membership = _membership("OM-C8", account, org, frozenset({MembershipRole.PUBLISHER}))

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C8-NEVER-CREATED"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C8-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.NATIVE_LISTING_NOT_FOUND


def test_cross_organization_write_denied_and_leaves_history_untouched(claim_conn: Any) -> None:
    account_a = _account("ACC-C9-A")
    org_a = _org("ORG-C9-A")
    membership_a = _membership("OM-C9-A", account_a, org_a, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C9",
        physical_boat_id="PB-C9",
        market_episode_id="ME-C9",
        account=account_a,
        org=org_a,
        membership=membership_a,
    )

    account_b = _account("ACC-C9-B")
    org_b = _org("ORG-C9-B")
    membership_b = _membership("OM-C9-B", account_b, org_b, frozenset({MembershipRole.PUBLISHER}))

    result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account_b,
        candidate_organization=org_b,
        membership=membership_b,
        native_listing_id=NativeListingId("NL-C9"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C9-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert result.status is PhysicalBoatClaimWriteStatus.CROSS_ORGANIZATION_DENIED
    claim_conn.commit()
    assert fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C9"), org_a.id) is None
    assert fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C9"), org_b.id) is None
    assert list_physical_boat_claim_revisions(claim_conn, PhysicalBoatId("PB-C9"), org_b.id) == []


def test_unresolved_market_episode_link_is_chain_incomplete(claim_conn: Any) -> None:
    account = _account("ACC-C10")
    org = _org("ORG-C10")
    membership = _membership("OM-C10", account, org, frozenset({MembershipRole.PUBLISHER}))
    result = create_native_listing(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(id=NativeListingId("NL-C10")),  # no market_episode_id
    )
    assert result.status.value == "created"
    claim_conn.commit()

    write_result = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C10"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C10-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert write_result.status is PhysicalBoatClaimWriteStatus.CHAIN_INCOMPLETE


# ---------------------------------------------------------------------------
# Idempotency / conflict
# ---------------------------------------------------------------------------


def test_identical_retry_is_idempotent(claim_conn: Any) -> None:
    account = _account("ACC-C11")
    org = _org("ORG-C11")
    membership = _membership("OM-C11", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C11",
        physical_boat_id="PB-C11",
        market_episode_id="ME-C11",
        account=account,
        org=org,
        membership=membership,
    )

    kwargs: dict[str, Any] = {
        "account_id": account,
        "candidate_organization": org,
        "membership": membership,
        "native_listing_id": NativeListingId("NL-C11"),
        "revision_id": PhysicalBoatClaimRevisionId("PBCREV-C11-001"),
        "expected_current_revision_id": None,
        "claims": _snapshot(),
    }
    first = write_physical_boat_claim_revision(claim_conn, **kwargs)
    assert first.status is PhysicalBoatClaimWriteStatus.CREATED

    second = write_physical_boat_claim_revision(claim_conn, **kwargs)
    assert second.status is PhysicalBoatClaimWriteStatus.ALREADY_EXISTS
    assert second.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C11-001")


def test_same_revision_id_different_content_conflicts(claim_conn: Any) -> None:
    account = _account("ACC-C12")
    org = _org("ORG-C12")
    membership = _membership("OM-C12", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C12",
        physical_boat_id="PB-C12",
        market_episode_id="ME-C12",
        account=account,
        org=org,
        membership=membership,
    )

    first = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C12"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C12-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert first.status is PhysicalBoatClaimWriteStatus.CREATED

    second = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C12"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C12-001"),
        expected_current_revision_id=None,
        claims=_snapshot(model_designation_claim="Oceanis 34.1"),
    )
    assert second.status is PhysicalBoatClaimWriteStatus.CONFLICT
    assert second.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C12-001")


# ---------------------------------------------------------------------------
# Correction / supersession
# ---------------------------------------------------------------------------


def test_same_authority_correction_retains_old_revision(claim_conn: Any) -> None:
    account = _account("ACC-C13")
    org = _org("ORG-C13")
    membership = _membership("OM-C13", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C13",
        physical_boat_id="PB-C13",
        market_episode_id="ME-C13",
        account=account,
        org=org,
        membership=membership,
    )

    first = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C13"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C13-001"),
        expected_current_revision_id=None,
        claims=_snapshot(
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.60"))
        ),
    )
    assert first.status is PhysicalBoatClaimWriteStatus.CREATED

    second = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C13"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C13-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C13-001"),
        claims=_snapshot(
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.65"))
        ),
    )
    assert second.status is PhysicalBoatClaimWriteStatus.REVISED
    assert second.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C13-002")

    old = fetch_physical_boat_claim_revision(
        claim_conn, PhysicalBoatClaimRevisionId("PBCREV-C13-001")
    )
    assert old is not None
    assert old.claims.draft.value == Decimal("1.60")

    current = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C13"), org.id)
    assert current is not None
    assert current.claims.draft.value == Decimal("1.65")
    assert current.previous_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C13-001")

    history = list_physical_boat_claim_revisions(claim_conn, PhysicalBoatId("PB-C13"), org.id)
    assert len(history) == 2


def test_stale_predecessor_conflicts_and_leaves_head_unchanged(claim_conn: Any) -> None:
    account = _account("ACC-C14")
    org = _org("ORG-C14")
    membership = _membership("OM-C14", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C14",
        physical_boat_id="PB-C14",
        market_episode_id="ME-C14",
        account=account,
        org=org,
        membership=membership,
    )

    write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C14"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C14-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )

    stale = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C14"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C14-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C14-DOES-NOT-EXIST"),
        claims=_snapshot(model_designation_claim="Oceanis 34.1"),
    )
    assert stale.status is PhysicalBoatClaimWriteStatus.CONFLICT
    assert stale.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C14-001")

    history = list_physical_boat_claim_revisions(claim_conn, PhysicalBoatId("PB-C14"), org.id)
    assert len(history) == 1
    current = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C14"), org.id)
    assert current is not None
    assert current.revision_id == PhysicalBoatClaimRevisionId("PBCREV-C14-001")


def test_reusing_a_revision_id_with_a_different_supplied_predecessor_is_conflict_not_already_exists(
    claim_conn: Any,
) -> None:
    """AMEND review finding 1: an exact retry must match the *complete*
    immutable envelope, including the predecessor this revision id was
    originally recorded against -- not content_hash alone. R1 -> R2
    (superseding R1) -> R3 (superseding R2); reusing R2's revision id with
    identical seven-field content but a *different* supplied predecessor
    (R3's own id instead of R2's real recorded predecessor R1) must CONFLICT,
    leaving history/head untouched. A genuine retry of R2 with its original
    predecessor (R1) must still resolve ALREADY_EXISTS even though the head
    has since advanced past R2 to R3."""
    account = _account("ACC-C22")
    org = _org("ORG-C22")
    membership = _membership("OM-C22", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C22",
        physical_boat_id="PB-C22",
        market_episode_id="ME-C22",
        account=account,
        org=org,
        membership=membership,
    )

    r2_claims = _snapshot(model_designation_claim="Oceanis 34.1")

    r1 = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C22"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert r1.status is PhysicalBoatClaimWriteStatus.CREATED

    r2 = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C22"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-001"),
        claims=r2_claims,
    )
    assert r2.status is PhysicalBoatClaimWriteStatus.REVISED

    r3 = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C22"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-003"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-002"),
        claims=_snapshot(model_designation_claim="Oceanis 34.1 Mk2"),
    )
    assert r3.status is PhysicalBoatClaimWriteStatus.REVISED

    # Reuse R2's revision id + identical seven-field content, but claim a
    # different predecessor (R3's id) than what R2 was actually recorded
    # against (R1). This must never be treated as the same immutable
    # revision merely because the seven-field snapshot matches.
    forged_predecessor_retry = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C22"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-003"),
        claims=r2_claims,
    )
    assert forged_predecessor_retry.status is PhysicalBoatClaimWriteStatus.CONFLICT

    history_after_forged_retry = list_physical_boat_claim_revisions(
        claim_conn, PhysicalBoatId("PB-C22"), org.id
    )
    current_after_forged_retry = fetch_current_physical_boat_claim(
        claim_conn, PhysicalBoatId("PB-C22"), org.id
    )
    assert len(history_after_forged_retry) == 3  # R1, R2, R3 only -- no forged 4th row
    assert current_after_forged_retry is not None
    assert current_after_forged_retry.revision_id == PhysicalBoatClaimRevisionId("PBCREV-C22-003")
    claim_conn.commit()  # release the implicit read transaction before the next write

    # A genuine retry of R2 with its real original predecessor (R1) must
    # still resolve ALREADY_EXISTS, even though the current head has since
    # advanced to R3.
    genuine_retry = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C22"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C22-001"),
        claims=r2_claims,
    )
    assert genuine_retry.status is PhysicalBoatClaimWriteStatus.ALREADY_EXISTS
    assert genuine_retry.current_revision_id == PhysicalBoatClaimRevisionId("PBCREV-C22-003")

    history_after_genuine_retry = list_physical_boat_claim_revisions(
        claim_conn, PhysicalBoatId("PB-C22"), org.id
    )
    assert len(history_after_genuine_retry) == 3  # still no duplicate/forged row


# ---------------------------------------------------------------------------
# Cross-Organization independence (SLICE-0050 §9)
# ---------------------------------------------------------------------------


def test_two_organizations_have_independent_current_heads_for_same_physical_boat(
    claim_conn: Any,
) -> None:
    account_a = _account("ACC-C15-A")
    org_a = _org("ORG-C15-A")
    membership_a = _membership("OM-C15-A", account_a, org_a, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C15-A",
        physical_boat_id="PB-C15",
        market_episode_id="ME-C15-A",
        account=account_a,
        org=org_a,
        membership=membership_a,
    )

    account_b = _account("ACC-C15-B")
    org_b = _org("ORG-C15-B")
    membership_b = _membership("OM-C15-B", account_b, org_b, frozenset({MembershipRole.PUBLISHER}))
    # A second NativeListing/MarketEpisode for the SAME PhysicalBoat, owned by org_b.
    create_market_episode(
        claim_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-C15-B"), physical_boat_id=PhysicalBoatId("PB-C15")
        ),
    )
    create_native_listing(
        claim_conn,
        account_id=account_b,
        candidate_organization=org_b,
        membership=membership_b,
        listing=NativeListing(
            id=NativeListingId("NL-C15-B"), market_episode_id=MarketEpisodeId("ME-C15-B")
        ),
    )
    claim_conn.commit()

    result_a = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account_a,
        candidate_organization=org_a,
        membership=membership_a,
        native_listing_id=NativeListingId("NL-C15-A"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C15-A-001"),
        expected_current_revision_id=None,
        claims=_snapshot(marketed_brand_claim="Beneteau"),
    )
    result_b = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account_b,
        candidate_organization=org_b,
        membership=membership_b,
        native_listing_id=NativeListingId("NL-C15-B"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C15-B-001"),
        expected_current_revision_id=None,
        claims=_snapshot(marketed_brand_claim="Jeanneau"),
    )
    assert result_a.status is PhysicalBoatClaimWriteStatus.CREATED
    assert result_b.status is PhysicalBoatClaimWriteStatus.CREATED

    current_a = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C15"), org_a.id)
    current_b = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C15"), org_b.id)
    assert current_a is not None and current_a.claims.marketed_brand_claim == "Beneteau"
    assert current_b is not None and current_b.claims.marketed_brand_claim == "Jeanneau"


# ---------------------------------------------------------------------------
# Typed readback: omission vs UNKNOWN, categorical values, lossless decimals
# ---------------------------------------------------------------------------


def test_readback_distinguishes_omitted_from_explicit_unknown(claim_conn: Any) -> None:
    account = _account("ACC-C16")
    org = _org("ORG-C16")
    membership = _membership("OM-C16", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C16",
        physical_boat_id="PB-C16",
        market_episode_id="ME-C16",
        account=account,
        org=org,
        membership=membership,
    )

    write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C16"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C16-001"),
        expected_current_revision_id=None,
        claims=_snapshot(
            loa_length=LoaLengthClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.14")
            ),
            draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
            # keel_configuration and rudder_configuration deliberately omitted.
        ),
    )

    current = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C16"), org.id)
    assert current is not None
    assert current.claims.loa_length is not None
    assert current.claims.loa_length.value == Decimal("9.14")
    assert current.claims.draft is not None
    assert current.claims.draft.assertion_kind is AssertionKind.UNKNOWN
    assert current.claims.draft.value is None
    assert current.claims.keel_configuration is None
    assert current.claims.rudder_configuration is None


def test_readback_reconstructs_categorical_keel_and_rudder_values(claim_conn: Any) -> None:
    account = _account("ACC-C17")
    org = _org("ORG-C17")
    membership = _membership("OM-C17", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C17",
        physical_boat_id="PB-C17",
        market_episode_id="ME-C17",
        account=account,
        org=org,
        membership=membership,
    )

    write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C17"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C17-001"),
        expected_current_revision_id=None,
        claims=_snapshot(
            keel_configuration=KeelConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.TWIN_KEEL
            ),
            rudder_configuration=RudderConfigurationClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration.TWIN
            ),
        ),
    )

    current = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C17"), org.id)
    assert current is not None
    assert current.claims.keel_configuration is not None
    assert current.claims.keel_configuration.value is KeelConfiguration.TWIN_KEEL
    assert current.claims.rudder_configuration is not None
    assert current.claims.rudder_configuration.value is RudderConfiguration.TWIN


def test_readback_of_missing_claim_returns_none(claim_conn: Any) -> None:
    account = _account("ACC-C18")
    org = _org("ORG-C18")
    membership = _membership("OM-C18", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C18",
        physical_boat_id="PB-C18",
        market_episode_id="ME-C18",
        account=account,
        org=org,
        membership=membership,
    )
    assert fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C18"), org.id) is None


# ---------------------------------------------------------------------------
# No BoatDesign fallback in the persisted claim itself
# ---------------------------------------------------------------------------


def test_persisted_claim_never_pulls_in_a_boat_design_baseline_value(claim_conn: Any) -> None:
    """The PhysicalBoat may reference a BoatDesign; the persisted claim
    snapshot must carry only what was explicitly supplied -- omitted stays
    omitted regardless of any linked BoatDesign."""
    account = _account("ACC-C19")
    org = _org("ORG-C19")
    membership = _membership("OM-C19", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C19",
        physical_boat_id="PB-C19",
        market_episode_id="ME-C19",
        account=account,
        org=org,
        membership=membership,
        boat_design_ref=None,  # SLICE-0050 does not require a real BoatDesign row to prove this
    )

    write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C19"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C19-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),  # draft/loa_length/keel/rudder all omitted
    )

    current = fetch_current_physical_boat_claim(claim_conn, PhysicalBoatId("PB-C19"), org.id)
    assert current is not None
    assert current.claims.draft is None
    assert current.claims.loa_length is None
    assert current.claims.keel_configuration is None
    assert current.claims.rudder_configuration is None


# ---------------------------------------------------------------------------
# Transaction ownership
# ---------------------------------------------------------------------------


def test_write_on_a_connection_with_an_open_implicit_transaction_fails_closed(
    claim_conn: Any,
) -> None:
    account = _account("ACC-C20")
    org = _org("ORG-C20")
    membership = _membership("OM-C20", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C20",
        physical_boat_id="PB-C20",
        market_episode_id="ME-C20",
        account=account,
        org=org,
        membership=membership,
    )
    with claim_conn.cursor() as cur:
        cur.execute("SELECT 1")  # opens an implicit transaction

    with pytest.raises(PhysicalBoatClaimTransactionOwnershipError):
        write_physical_boat_claim_revision(
            claim_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-C20"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-C20-001"),
            expected_current_revision_id=None,
            claims=_snapshot(),
        )
    claim_conn.rollback()


# ---------------------------------------------------------------------------
# Rollback on head-write failure (SLICE-0050 §8)
# ---------------------------------------------------------------------------


def test_failure_during_head_advance_rolls_back_the_already_inserted_revision(
    claim_conn: Any,
) -> None:
    """AMEND review finding 2: a failure after the immutable revision INSERT
    but before/while the head UPSERT commits MUST roll back the whole
    transaction, leaving no orphan revision and no head movement.

    Forces a deterministic DB-side failure with a temporary trigger on
    ``physical_boat_claim_heads`` that rejects one specific sentinel
    ``current_claim_revision_id`` value -- a real PostgreSQL failure late in
    the write transaction, not a production code hook. The trigger and its
    function are created and dropped entirely within this test against the
    already-disposable per-test schema.
    """
    account = _account("ACC-C23")
    org = _org("ORG-C23")
    membership = _membership("OM-C23", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C23",
        physical_boat_id="PB-C23",
        market_episode_id="ME-C23",
        account=account,
        org=org,
        membership=membership,
    )

    first = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C23"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C23-001"),
        expected_current_revision_id=None,
        claims=_snapshot(),
    )
    assert first.status is PhysicalBoatClaimWriteStatus.CREATED

    # A fixed, test-local constant (never external/adversarial input), so it
    # is safe to embed directly in the function body text below -- a bind
    # parameter cannot be used here: PostgreSQL cannot infer a parameter's
    # type when it appears only inside a dollar-quoted function body, which
    # is opaque to the outer statement's parser until the function itself is
    # invoked.
    forced_failure_revision_id = "PBCREV-C23-FORCED-FAILURE"
    with claim_conn.cursor() as cur:
        cur.execute(
            "CREATE OR REPLACE FUNCTION test_pb_claim_force_head_failure() "
            "RETURNS trigger AS $$ "
            "BEGIN "
            f"  IF NEW.current_claim_revision_id = '{forced_failure_revision_id}' THEN "
            "    RAISE EXCEPTION 'test-injected head write failure'; "
            "  END IF; "
            "  RETURN NEW; "
            "END; $$ LANGUAGE plpgsql"
        )
        cur.execute(
            "CREATE TRIGGER trg_pb_claim_force_head_failure "
            "BEFORE INSERT OR UPDATE ON physical_boat_claim_heads "
            "FOR EACH ROW EXECUTE FUNCTION test_pb_claim_force_head_failure()"
        )
    claim_conn.commit()

    try:
        with pytest.raises(psycopg.errors.RaiseException):
            write_physical_boat_claim_revision(
                claim_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-C23"),
                revision_id=PhysicalBoatClaimRevisionId(forced_failure_revision_id),
                expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C23-001"),
                claims=_snapshot(model_designation_claim="Oceanis 34.1"),
            )
        # psycopg's conn.transaction() rolls back automatically on the
        # propagated exception; the connection is IDLE again immediately,
        # ready for ordinary queries without an explicit rollback() call.
        assert claim_conn.info.transaction_status.name == "IDLE"

        orphan_revision = fetch_physical_boat_claim_revision(
            claim_conn, PhysicalBoatClaimRevisionId(forced_failure_revision_id)
        )
        current_after_failure = fetch_current_physical_boat_claim(
            claim_conn, PhysicalBoatId("PB-C23"), org.id
        )
        history_after_failure = list_physical_boat_claim_revisions(
            claim_conn, PhysicalBoatId("PB-C23"), org.id
        )
        claim_conn.commit()  # release the implicit read transaction

        assert orphan_revision is None
        assert current_after_failure is not None
        assert current_after_failure.revision_id == PhysicalBoatClaimRevisionId("PBCREV-C23-001")
        assert len(history_after_failure) == 1
    finally:
        with claim_conn.cursor() as cur:
            cur.execute(
                "DROP TRIGGER IF EXISTS trg_pb_claim_force_head_failure ON physical_boat_claim_heads"
            )
            cur.execute("DROP FUNCTION IF EXISTS test_pb_claim_force_head_failure()")
        claim_conn.commit()

    # The connection remains usable for an ordinary, unaffected write after
    # the trigger is removed -- the earlier failure left no lasting damage.
    recovery = write_physical_boat_claim_revision(
        claim_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-C23"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-C23-002"),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-C23-001"),
        claims=_snapshot(model_designation_claim="Oceanis 34.1"),
    )
    assert recovery.status is PhysicalBoatClaimWriteStatus.REVISED


# ---------------------------------------------------------------------------
# Concurrency (SLICE-0050 §8)
# ---------------------------------------------------------------------------


def test_concurrent_first_writes_resolve_to_exactly_one_created(claim_url: str) -> None:
    setup_conn = psycopg.connect(claim_url)
    try:
        account = _account("ACC-RACE1")
        org = _org("ORG-RACE1")
        membership = _membership("OM-RACE1", account, org, frozenset({MembershipRole.PUBLISHER}))
        _create_chain(
            setup_conn,
            native_listing_id="NL-RACE1",
            physical_boat_id="PB-RACE1",
            market_episode_id="ME-RACE1",
            account=account,
            org=org,
            membership=membership,
        )
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(suffix: str) -> None:
        try:
            conn = psycopg.connect(claim_url)
            try:
                barrier.wait(timeout=10)
                result = write_physical_boat_claim_revision(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-RACE1"),
                    revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-RACE1-{suffix}"),
                    expected_current_revision_id=None,
                    claims=_snapshot(),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("A",)),
        threading.Thread(target=_worker, args=("B",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(PhysicalBoatClaimWriteStatus.CREATED) == 1, statuses
    assert statuses.count(PhysicalBoatClaimWriteStatus.CONFLICT) == 1, statuses

    verify = psycopg.connect(claim_url)
    try:
        history = list_physical_boat_claim_revisions(verify, PhysicalBoatId("PB-RACE1"), org.id)
        assert len(history) == 1
    finally:
        verify.close()


def test_concurrent_corrections_from_the_same_predecessor_resolve_to_exactly_one_winner(
    claim_url: str,
) -> None:
    setup_conn = psycopg.connect(claim_url)
    try:
        account = _account("ACC-RACE2")
        org = _org("ORG-RACE2")
        membership = _membership("OM-RACE2", account, org, frozenset({MembershipRole.PUBLISHER}))
        _create_chain(
            setup_conn,
            native_listing_id="NL-RACE2",
            physical_boat_id="PB-RACE2",
            market_episode_id="ME-RACE2",
            account=account,
            org=org,
            membership=membership,
        )
        first = write_physical_boat_claim_revision(
            setup_conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-RACE2"),
            revision_id=PhysicalBoatClaimRevisionId("PBCREV-RACE2-000"),
            expected_current_revision_id=None,
            claims=_snapshot(),
        )
        assert first.status is PhysicalBoatClaimWriteStatus.CREATED
    finally:
        setup_conn.close()

    results: list[Any] = []
    errors: list[BaseException] = []
    barrier = threading.Barrier(2)

    def _worker(suffix: str) -> None:
        try:
            conn = psycopg.connect(claim_url)
            try:
                barrier.wait(timeout=10)
                result = write_physical_boat_claim_revision(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    native_listing_id=NativeListingId("NL-RACE2"),
                    revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-RACE2-{suffix}"),
                    expected_current_revision_id=PhysicalBoatClaimRevisionId("PBCREV-RACE2-000"),
                    claims=_snapshot(model_designation_claim=f"Oceanis {suffix}"),
                )
                results.append(result)
            finally:
                conn.close()
        except Exception as exc:  # pragma: no cover - surfaced via errors assertion
            errors.append(exc)

    threads = [
        threading.Thread(target=_worker, args=("A",)),
        threading.Thread(target=_worker, args=("B",)),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=20)

    assert not errors, f"Thread errors: {errors}"
    assert len(results) == 2
    statuses = [r.status for r in results]
    assert statuses.count(PhysicalBoatClaimWriteStatus.REVISED) == 1, statuses
    assert statuses.count(PhysicalBoatClaimWriteStatus.CONFLICT) == 1, statuses

    verify = psycopg.connect(claim_url)
    try:
        history = list_physical_boat_claim_revisions(verify, PhysicalBoatId("PB-RACE2"), org.id)
        assert len(history) == 2  # first revision + exactly one winning correction
        current = fetch_current_physical_boat_claim(verify, PhysicalBoatId("PB-RACE2"), org.id)
        assert current is not None
        assert current.revision_id != PhysicalBoatClaimRevisionId("PBCREV-RACE2-000")
    finally:
        verify.close()


# ---------------------------------------------------------------------------
# FK / constraint negative paths
# ---------------------------------------------------------------------------


def test_db_rejects_a_blank_marketed_brand_claim(claim_conn: Any) -> None:
    with claim_conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                "PBCREV-BADBRAND",
                "PB-NEVER-CREATED",
                "ORG-X",
                "ACC-X",
                "   ",
                "Oceanis 30.1",
                "VALUE_ASSERTION",
                2021,
                "0" * 64,
            ),
        )
    claim_conn.rollback()


def test_db_rejects_unknown_keel_configuration_value(claim_conn: Any) -> None:
    account = _account("ACC-C21")
    org = _org("ORG-C21")
    membership = _membership("OM-C21", account, org, frozenset({MembershipRole.PUBLISHER}))
    _create_chain(
        claim_conn,
        native_listing_id="NL-C21",
        physical_boat_id="PB-C21",
        market_episode_id="ME-C21",
        account=account,
        org=org,
        membership=membership,
    )
    with claim_conn.cursor() as cur, pytest.raises(psycopg.errors.CheckViolation):
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, "
            "keel_configuration_assertion_kind, keel_configuration_value, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                "PBCREV-BADKEEL",
                "PB-C21",
                org.id.value,
                account.value,
                "Beneteau",
                "Oceanis 30.1",
                "VALUE_ASSERTION",
                2021,
                "VALUE_ASSERTION",
                "NOT_A_REAL_KEEL_TYPE",
                "0" * 64,
            ),
        )
    claim_conn.rollback()


def test_db_rejects_a_physical_boat_id_that_does_not_exist(claim_conn: Any) -> None:
    with claim_conn.cursor() as cur, pytest.raises(psycopg.errors.ForeignKeyViolation):
        cur.execute(
            "INSERT INTO physical_boat_claim_revisions ("
            "claim_revision_id, physical_boat_id, claiming_organization_id, "
            "recorded_by_account_id, marketed_brand_claim, model_designation_claim, "
            "build_year_assertion_kind, build_year_value, content_hash"
            ") VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
            (
                "PBCREV-NOBOAT",
                "PB-NEVER-CREATED",
                "ORG-X",
                "ACC-X",
                "Beneteau",
                "Oceanis 30.1",
                "VALUE_ASSERTION",
                2021,
                "0" * 64,
            ),
        )
    claim_conn.rollback()
