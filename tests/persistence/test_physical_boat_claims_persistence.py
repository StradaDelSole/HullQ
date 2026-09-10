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
