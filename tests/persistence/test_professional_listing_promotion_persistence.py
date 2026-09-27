"""PostgreSQL integration tests for
hullq.persistence.professional_listing_promotion — SLICE-0067.

Covers `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §7/§8/§9/§11:
the one atomic promotion transaction against a real PostgreSQL 18 schema --
successful fresh-identity promotion, exact-version idempotency, stale-version
conflict, NOT_READY/DENIED zero-mutation, D09 duplicate-episode mapping and
representative failure-injection rollback proofs.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.domain.listing_draft_payload import parse_listing_draft_payload
from hullq.domain.professional_listing_draft import (
    ProfessionalDraftPromotionState,
    ProfessionalListingDraftId,
)
from hullq.domain.promotion_readiness import PromotionReadinessReason
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
from hullq.persistence.professional_listing_draft import create_professional_listing_draft
from hullq.persistence.professional_listing_promotion import (
    ProfessionalListingPromotionStatus,
    ProfessionalListingPromotionTransactionOwnershipError,
    promote_professional_listing_draft,
)

_READY_PAYLOAD = {
    "physical_boat.marketed_brand_claim": "Beneteau",
    "physical_boat.model_designation_claim": "Oceanis 30.1",
    "physical_boat.build_year": {"assertion_kind": "VALUE_ASSERTION", "value": 2021},
    "listing_offer.asking_price_mode": "AMOUNT",
    "listing_offer.asking_price_amount": "125000",
    "listing_offer.currency": "EUR",
    "listing_offer.location_country": "FR",
}
_READY_BROKER_DESCRIPTION = "A lovely, well-maintained cruising sloop."


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
def promotion_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0067_{uuid.uuid4().hex[:16]}"
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
def conn(promotion_url: str) -> Generator[Any]:
    connection = psycopg.connect(promotion_url)
    try:
        yield connection
    finally:
        connection.close()


def _seed_account(conn: Any, account_id: AccountId) -> None:
    with conn.cursor() as cur:
        cur.execute("INSERT INTO accounts (account_id) VALUES (%s)", [account_id.value])
    conn.commit()


def _seed_organization(
    conn: Any,
    organization_id: MarketplaceOrganizationId,
    *,
    eligibility: str = "ELIGIBLE",
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO marketplace_organizations "
            "(organization_id, professional_category, publishing_eligibility, public_display_name) "
            "VALUES (%s, %s, %s, %s)",
            [organization_id.value, "BROKER", eligibility, organization_id.value],
        )
    conn.commit()


def _org(value: str, *, eligibility: OrganizationPublishingEligibility) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=eligibility,
    )


def _membership(
    membership_id: str,
    account: AccountId,
    organization: MarketplaceOrganization,
    roles: frozenset[MembershipRole],
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=organization.id,
        roles=roles,
        state=MembershipState.ACTIVE,
    )


def _row_counts(conn: Any) -> dict[str, int]:
    tables = (
        "physical_boats",
        "market_episodes",
        "native_listings",
        "native_listing_offer_revisions",
        "native_listing_offer_heads",
        "physical_boat_claim_revisions",
        "physical_boat_claim_heads",
    )
    counts: dict[str, int] = {}
    with conn.cursor() as cur:
        for table in tables:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            row = cur.fetchone()
            assert row is not None
            counts[table] = row[0]
    # Read-only, but leaves an implicit open transaction under psycopg's
    # default autocommit=False -- every caller that follows this with
    # promote_professional_listing_draft() (which requires an IDLE conn)
    # relies on this commit to end it.
    conn.commit()
    return counts


def _create_ready_draft(
    conn: Any,
    org_id: MarketplaceOrganizationId,
    account_id: AccountId,
    *,
    broker_listing_reference: str | None = None,
) -> ProfessionalListingDraftId:
    record = create_professional_listing_draft(
        conn,
        owner_organization_id=org_id,
        created_by_account_id=account_id,
        broker_listing_reference=broker_listing_reference,
        broker_description=_READY_BROKER_DESCRIPTION,
        payload=parse_listing_draft_payload(_READY_PAYLOAD),
    )
    conn.commit()
    return record.draft_id


class TestSuccessfulPromotion:
    def test_promotes_ready_draft_and_creates_complete_chain(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-1")
        org_id = MarketplaceOrganizationId("ORG-PROMO-1")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-1", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account, broker_listing_reference="REF-1")

        result = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )

        assert result.status is ProfessionalListingPromotionStatus.PROMOTED
        assert result.native_listing_id is not None
        native_listing_id = result.native_listing_id.value

        with conn.cursor() as cur:
            cur.execute(
                "SELECT boat_design_ref FROM physical_boats pb "
                "JOIN market_episodes me ON me.physical_boat_id = pb.physical_boat_id "
                "JOIN native_listings nl ON nl.market_episode_id = me.market_episode_id "
                "WHERE nl.native_listing_id = %s",
                [native_listing_id],
            )
            (boat_design_ref,) = cur.fetchone()
            assert boat_design_ref is None

            cur.execute(
                "SELECT publishing_organization_id, created_by_account_id, "
                "broker_listing_reference, lifecycle_state "
                "FROM native_listings WHERE native_listing_id = %s",
                [native_listing_id],
            )
            pub_org, creator, broker_ref, lifecycle_state = cur.fetchone()
            assert pub_org == org_id.value
            assert creator == account.value
            assert broker_ref == "REF-1"
            assert lifecycle_state == "DRAFT"

            cur.execute(
                "SELECT marketed_brand_claim, model_designation_claim, build_year_value, "
                "boat_name_assertion_kind "
                "FROM physical_boat_claim_revisions WHERE claiming_organization_id = %s",
                [org_id.value],
            )
            brand, model, build_year, boat_name_kind = cur.fetchone()
            assert brand == "Beneteau"
            assert model == "Oceanis 30.1"
            assert build_year == 2021
            assert boat_name_kind is None

            cur.execute(
                "SELECT asking_price_mode, asking_price_amount, currency, location_country, "
                "broker_description "
                "FROM native_listing_offer_revisions WHERE native_listing_id = %s",
                [native_listing_id],
            )
            mode, amount, currency, country, description = cur.fetchone()
            assert mode == "AMOUNT"
            assert str(amount) == "125000"
            assert currency == "EUR"
            assert country == "FR"
            assert description == _READY_BROKER_DESCRIPTION

            cur.execute(
                "SELECT native_listing_publication_transitions.to_state "
                "FROM native_listing_publication_transitions"
            )
            assert cur.fetchall() == []

            cur.execute(
                "SELECT promotion_state, promoted_native_listing_id, promoted_at, version "
                "FROM professional_listing_drafts WHERE professional_listing_draft_id = %s",
                [draft_id.value],
            )
            state, promoted_native_listing_id, promoted_at, version = cur.fetchone()
            assert state == "PROMOTED"
            assert promoted_native_listing_id == native_listing_id
            assert promoted_at is not None
            assert version == 1  # frozen -- promotion never increments version

    def test_exact_retry_returns_same_native_listing_id_with_zero_additional_writes(
        self, conn: Any
    ) -> None:
        account = AccountId("ACC-PROMO-2")
        org_id = MarketplaceOrganizationId("ORG-PROMO-2")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-2", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account)

        first = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )
        assert first.status is ProfessionalListingPromotionStatus.PROMOTED
        before = _row_counts(conn)

        retry = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )
        after = _row_counts(conn)

        assert retry.status is ProfessionalListingPromotionStatus.ALREADY_PROMOTED
        assert retry.native_listing_id == first.native_listing_id
        assert after == before

    def test_promoted_retry_with_mismatched_version_is_version_conflict(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-3")
        org_id = MarketplaceOrganizationId("ORG-PROMO-3")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-3", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account)

        first = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )
        assert first.status is ProfessionalListingPromotionStatus.PROMOTED

        stale = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=2,
        )
        assert stale.status is ProfessionalListingPromotionStatus.VERSION_CONFLICT
        assert stale.native_listing_id is None


class TestZeroMutationOutcomes:
    def test_draft_not_found_for_unknown_draft(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-4")
        org_id = MarketplaceOrganizationId("ORG-PROMO-4")
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-4", account, org, frozenset({MembershipRole.PUBLISHER}))

        result = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=ProfessionalListingDraftId(str(uuid.uuid4())),
            owner_organization_id=org_id,
            expected_version=1,
        )
        assert result.status is ProfessionalListingPromotionStatus.DRAFT_NOT_FOUND

    def test_stale_expected_version_on_editable_draft_is_zero_mutation(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-5")
        org_id = MarketplaceOrganizationId("ORG-PROMO-5")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-5", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account)
        before = _row_counts(conn)

        result = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=999,
        )
        assert result.status is ProfessionalListingPromotionStatus.VERSION_CONFLICT
        assert _row_counts(conn) == before

    def test_not_ready_incomplete_draft_is_zero_mutation(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-6")
        org_id = MarketplaceOrganizationId("ORG-PROMO-6")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-6", account, org, frozenset({MembershipRole.PUBLISHER}))
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=org_id,
            created_by_account_id=account,
            broker_listing_reference=None,
            payload=parse_listing_draft_payload({}),
        )
        conn.commit()
        before = _row_counts(conn)

        result = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=record.draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )
        assert result.status is ProfessionalListingPromotionStatus.NOT_READY
        assert PromotionReadinessReason.MISSING_MARKETED_BRAND in result.reasons
        assert _row_counts(conn) == before

    def test_denied_ineligible_organization_is_zero_mutation(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-7")
        org_id = MarketplaceOrganizationId("ORG-PROMO-7")
        _seed_account(conn, account)
        _seed_organization(conn, org_id, eligibility="UNVERIFIED")
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.UNVERIFIED)
        membership = _membership("OM-PROMO-7", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account)
        before = _row_counts(conn)

        result = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )
        assert result.status is ProfessionalListingPromotionStatus.DENIED
        assert result.denial_reason is PublishingEligibilityReason.ORGANIZATION_UNVERIFIED
        assert _row_counts(conn) == before

        with conn.cursor() as cur:
            cur.execute(
                "SELECT promotion_state FROM professional_listing_drafts "
                "WHERE professional_listing_draft_id = %s",
                [draft_id.value],
            )
            (state,) = cur.fetchone()
            assert state == ProfessionalDraftPromotionState.EDITABLE.value


class TestTransactionOwnership:
    def test_open_transaction_on_conn_raises_before_any_read(self, conn: Any) -> None:
        account = AccountId("ACC-PROMO-8")
        org_id = MarketplaceOrganizationId("ORG-PROMO-8")
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-8", account, org, frozenset({MembershipRole.PUBLISHER}))

        with conn.cursor() as cur:
            cur.execute("SELECT 1")  # leaves an implicit open transaction

        with pytest.raises(ProfessionalListingPromotionTransactionOwnershipError):
            promote_professional_listing_draft(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                draft_id=ProfessionalListingDraftId(str(uuid.uuid4())),
                owner_organization_id=org_id,
                expected_version=1,
            )


class TestFailureInjectionRollback:
    def test_failure_after_identity_rows_exist_rolls_back_everything(
        self, conn: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Injects a failure after PhysicalBoat/MarketEpisode/NativeListing
        rows already exist uncommitted in the transaction (after the
        NativeListing insert, before the claim write) -- contract §8 requires
        the whole attempt to roll back, including those identity rows."""
        import hullq.persistence.professional_listing_promotion as promotion_module

        account = AccountId("ACC-PROMO-9")
        org_id = MarketplaceOrganizationId("ORG-PROMO-9")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-9", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account)
        before = _row_counts(conn)

        def _boom(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("injected failure after NativeListing insert")

        monkeypatch.setattr(promotion_module, "write_physical_boat_claim_revision_row", _boom)

        with pytest.raises(RuntimeError, match="injected failure"):
            promotion_module.promote_professional_listing_draft(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                draft_id=draft_id,
                owner_organization_id=org_id,
                expected_version=1,
            )

        assert _row_counts(conn) == before
        with conn.cursor() as cur:
            cur.execute(
                "SELECT promotion_state, version FROM professional_listing_drafts "
                "WHERE professional_listing_draft_id = %s",
                [draft_id.value],
            )
            state, version = cur.fetchone()
            assert state == "EDITABLE"
            assert version == 1

    def test_failure_after_initial_fact_writes_rolls_back_everything(
        self, conn: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Injects a failure after the initial claim + offer head writes
        already exist uncommitted (right before marking the draft PROMOTED)
        -- the whole attempt, including those fact/head rows, must still roll
        back together."""
        import hullq.persistence.professional_listing_promotion as promotion_module

        account = AccountId("ACC-PROMO-10")
        org_id = MarketplaceOrganizationId("ORG-PROMO-10")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-10", account, org, frozenset({MembershipRole.PUBLISHER}))
        draft_id = _create_ready_draft(conn, org_id, account)
        before = _row_counts(conn)

        def _boom(*args: Any, **kwargs: Any) -> Any:
            raise RuntimeError("injected failure before marking promoted")

        monkeypatch.setattr(promotion_module, "mark_professional_listing_draft_promoted", _boom)

        with pytest.raises(RuntimeError, match="injected failure"):
            promotion_module.promote_professional_listing_draft(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                draft_id=draft_id,
                owner_organization_id=org_id,
                expected_version=1,
            )

        assert _row_counts(conn) == before
        with conn.cursor() as cur:
            cur.execute(
                "SELECT promotion_state, version FROM professional_listing_drafts "
                "WHERE professional_listing_draft_id = %s",
                [draft_id.value],
            )
            state, version = cur.fetchone()
            assert state == "EDITABLE"
            assert version == 1


class TestDuplicateEpisodeMapping:
    def test_d09_collision_maps_to_duplicate_episode_with_zero_mutation(
        self, conn: Any, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Forces the fresh-mint PhysicalBoatId/MarketEpisodeId pair to
        collide with an already-resolved (org, episode) pair for this same
        Organization (practically unreachable in real UUID-random
        operation, but the low-level classification this exercises is
        contract §11's required deterministic mapping, not merely a
        happy-path detail). Both the pre-existing PhysicalBoat/MarketEpisode
        and the forced first/second mints use identical real `uuid.UUID`
        values, so `insert_physical_boat_row`/`insert_market_episode_row`
        each resolve as ALREADY_EXISTS (matching stored envelope), and the
        NativeListing insert is what then hits the real D09 unique index."""
        import hullq.persistence.professional_listing_promotion as promotion_module
        from hullq.domain.market_identity import (
            MarketEpisode,
            MarketEpisodeId,
            NativeListing,
            NativeListingId,
            PhysicalBoat,
            PhysicalBoatId,
        )
        from hullq.persistence.market_episode import create_market_episode
        from hullq.persistence.native_listing import create_native_listing
        from hullq.persistence.physical_boat import create_physical_boat

        account = AccountId("ACC-PROMO-11")
        org_id = MarketplaceOrganizationId("ORG-PROMO-11")
        _seed_account(conn, account)
        _seed_organization(conn, org_id)
        org = _org(org_id.value, eligibility=OrganizationPublishingEligibility.ELIGIBLE)
        membership = _membership("OM-PROMO-11", account, org, frozenset({MembershipRole.PUBLISHER}))

        existing_physical_boat_uuid = uuid.uuid4()
        existing_episode_uuid = uuid.uuid4()
        create_physical_boat(
            conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(str(existing_physical_boat_uuid)))
        )
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(str(existing_episode_uuid)),
                physical_boat_id=PhysicalBoatId(str(existing_physical_boat_uuid)),
            ),
        )
        create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(str(uuid.uuid4())),
                market_episode_id=MarketEpisodeId(str(existing_episode_uuid)),
            ),
        )

        draft_id = _create_ready_draft(conn, org_id, account)
        before = _row_counts(conn)

        # The promotion transaction mints exactly five fresh identities, in
        # this fixed order: PhysicalBoatId, MarketEpisodeId, NativeListingId,
        # PhysicalBoatClaimRevisionId, NativeListingOfferRevisionId. Forcing
        # the first two to reuse the pre-existing PhysicalBoatId/
        # MarketEpisodeId pair reproduces the D09 collision deterministically
        # (both resolve ALREADY_EXISTS; the NativeListing insert is what then
        # violates the unique index).
        forced = iter(
            [
                existing_physical_boat_uuid,
                existing_episode_uuid,
                uuid.uuid4(),
                uuid.uuid4(),
                uuid.uuid4(),
            ]
        )
        monkeypatch.setattr(promotion_module.uuid, "uuid4", lambda: next(forced))

        result = promote_professional_listing_draft(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            draft_id=draft_id,
            owner_organization_id=org_id,
            expected_version=1,
        )

        assert result.status is ProfessionalListingPromotionStatus.DUPLICATE_EPISODE
        assert _row_counts(conn) == before
        with conn.cursor() as cur:
            cur.execute(
                "SELECT promotion_state, version FROM professional_listing_drafts "
                "WHERE professional_listing_draft_id = %s",
                [draft_id.value],
            )
            state, version = cur.fetchone()
            assert state == "EDITABLE"
            assert version == 1
