"""PostgreSQL-backed SLICE-0048 listing-intake orchestration tests.

Each test runs against its own disposable PostgreSQL *schema*, brought from
genuinely empty to the current Alembic head, mirroring the SLICE-0043/0045
integration test isolation pattern in
tests/persistence/test_native_listing_offer_persistence.py.
"""

from __future__ import annotations

import dataclasses
import os
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.listing_intake import (
    ListingIntakeOutcome,
    ListingIntakeRequest,
    run_listing_intake,
)
from hullq.domain.market_identity import (
    BoatDesignRef,
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
from hullq.persistence.native_listing_offer import (
    NativeListingOfferWriteStatus,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.preview_token import verify_and_decode_preview_token

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
def intake_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0048_{uuid.uuid4().hex[:16]}"
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
def intake_conn(intake_url: str) -> Generator[Any]:
    conn = psycopg.connect(intake_url)
    try:
        yield conn
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------

_SECRET = os.urandom(32)


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
    org: MarketplaceOrganization,
    account: AccountId,
    *,
    membership_id: str = "OM-0048-T",
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


def _amount_offer(**overrides: object) -> NativeListingOfferSnapshot:
    kwargs: dict[str, object] = {
        "asking_price_mode": AskingPriceMode.AMOUNT,
        "location_country": "FR",
        "broker_description": "A well-maintained cruising sloop.",
        "asking_price_amount": Decimal("125000.00"),
        "currency": "EUR",
    }
    kwargs.update(overrides)
    return NativeListingOfferSnapshot(**kwargs)  # type: ignore[arg-type]


def _base_request(**overrides: object) -> ListingIntakeRequest:
    account = AccountId("ACC-0048-T")
    org = _org("ORG-0048-T")
    membership = _membership(org, account)
    base = ListingIntakeRequest(
        account_id=account,
        organization=org,
        membership=membership,
        physical_boat_id=PhysicalBoatId("PB-0048-T"),
        boat_design_ref=None,
        market_episode_id=MarketEpisodeId("ME-0048-T"),
        native_listing_id=NativeListingId("NL-0048-T"),
        broker_listing_reference=None,
        offer_revision_id=NativeListingOfferRevisionId("REV-0048-T"),
        offer=_amount_offer(),
    )
    return dataclasses.replace(base, **overrides)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_happy_path_creates_full_chain_and_mints_valid_token(intake_conn: Any) -> None:
    request = _base_request()
    result = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)

    assert result.outcome is ListingIntakeOutcome.SUCCEEDED
    assert result.physical_boat.status.value == "created"
    assert result.market_episode is not None and result.market_episode.status.value == "created"
    assert result.native_listing is not None and result.native_listing.status.value == "created"
    assert result.offer is not None and result.offer.status.value == "created"
    assert result.preview_token is not None
    assert result.preview_token_expires_at is not None

    claims = verify_and_decode_preview_token(result.preview_token, secret=_SECRET)
    assert claims.native_listing_id == request.native_listing_id


def test_exact_retry_is_idempotent_and_continues_safely(intake_conn: Any) -> None:
    request = _base_request()
    first = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)
    assert first.outcome is ListingIntakeOutcome.SUCCEEDED

    second = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)
    assert second.outcome is ListingIntakeOutcome.SUCCEEDED
    assert second.physical_boat.status.value == "already_exists"
    assert (
        second.market_episode is not None and second.market_episode.status.value == "already_exists"
    )
    assert (
        second.native_listing is not None and second.native_listing.status.value == "already_exists"
    )
    assert second.offer is not None and second.offer.status.value == "already_exists"
    # A token is minted on every successful call, even an idempotent retry
    # (two mints for the same listing within the same wall-clock second are
    # byte-identical since minting is deterministic and stateless -- that is
    # not a defect, so this only checks the claim, not token inequality).
    assert second.preview_token is not None
    claims = verify_and_decode_preview_token(second.preview_token, secret=_SECRET)
    assert claims.native_listing_id == request.native_listing_id


def test_physical_boat_conflict_stops_before_any_later_stage(intake_conn: Any) -> None:
    request = _base_request()
    first = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)
    assert first.outcome is ListingIntakeOutcome.SUCCEEDED

    # Same PhysicalBoatId, but a different requested BoatDesignRef: resolved
    # purely from the stored row, so this is CONFLICT, not a foreign-key error.
    conflicting = _base_request(boat_design_ref=BoatDesignRef("BD-DOES-NOT-MATTER"))

    result = run_listing_intake(intake_conn, request=conflicting, preview_signing_secret=_SECRET)
    assert result.outcome is ListingIntakeOutcome.PHYSICAL_BOAT_FAILED
    assert result.physical_boat.status.value == "conflict"
    assert result.market_episode is None
    assert result.native_listing is None
    assert result.offer is None
    assert result.preview_token is None


def test_physical_boat_design_not_found_fails_closed(intake_conn: Any) -> None:
    request = _base_request(
        physical_boat_id=PhysicalBoatId("PB-0048-NEWDESIGN"),
        boat_design_ref=BoatDesignRef("BD-UNKNOWN-DESIGN"),
    )
    result = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)
    assert result.outcome is ListingIntakeOutcome.PHYSICAL_BOAT_FAILED
    assert result.physical_boat.status.value == "design_not_found"
    assert result.preview_token is None


def test_market_episode_conflict_stops_before_native_listing_stage(intake_conn: Any) -> None:
    # Directly establish MarketEpisode ME-CONFLICT bound to PhysicalBoat PB-A.
    create_physical_boat(intake_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-A")))
    create_market_episode(
        intake_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-CONFLICT"), physical_boat_id=PhysicalBoatId("PB-A")
        ),
    )

    # Intake attempts to reuse ME-CONFLICT but bind it to a different PhysicalBoat.
    request = _base_request(
        physical_boat_id=PhysicalBoatId("PB-B"), market_episode_id=MarketEpisodeId("ME-CONFLICT")
    )
    result = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)

    assert result.outcome is ListingIntakeOutcome.MARKET_EPISODE_FAILED
    assert result.physical_boat.status.value == "created"  # PB-B was created fine
    assert result.market_episode is not None and result.market_episode.status.value == "conflict"
    assert result.native_listing is None
    assert result.offer is None
    assert result.preview_token is None


def test_denied_publisher_stops_at_native_listing_stage(intake_conn: Any) -> None:
    account = AccountId("ACC-DENIED")
    ineligible_org = _org(
        "ORG-INELIGIBLE", eligibility=OrganizationPublishingEligibility.INELIGIBLE
    )
    membership = _membership(ineligible_org, account, membership_id="OM-DENIED")

    request = _base_request(
        account_id=account,
        organization=ineligible_org,
        membership=membership,
        physical_boat_id=PhysicalBoatId("PB-DENIED"),
        market_episode_id=MarketEpisodeId("ME-DENIED"),
        native_listing_id=NativeListingId("NL-DENIED"),
    )
    result = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)

    assert result.outcome is ListingIntakeOutcome.NATIVE_LISTING_FAILED
    assert result.physical_boat.status.value == "created"
    assert result.market_episode is not None and result.market_episode.status.value == "created"
    assert result.native_listing is not None
    assert result.native_listing.status.value == "denied"
    assert (
        result.native_listing.denial_reason is PublishingEligibilityReason.ORGANIZATION_INELIGIBLE
    )
    assert result.offer is None
    assert result.preview_token is None


def test_native_listing_collision_with_different_envelope(intake_conn: Any) -> None:
    request = _base_request(native_listing_id=NativeListingId("NL-COLLIDE"))
    first = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)
    assert first.outcome is ListingIntakeOutcome.SUCCEEDED

    # Reuse NL-COLLIDE but bind it to a different (freshly created) MarketEpisode.
    colliding = dataclasses.replace(
        request,
        physical_boat_id=PhysicalBoatId("PB-COLLIDE-2"),
        market_episode_id=MarketEpisodeId("ME-COLLIDE-2"),
        offer_revision_id=NativeListingOfferRevisionId("REV-COLLIDE-2"),
    )
    result = run_listing_intake(intake_conn, request=colliding, preview_signing_secret=_SECRET)

    assert result.outcome is ListingIntakeOutcome.NATIVE_LISTING_FAILED
    assert result.native_listing is not None
    assert result.native_listing.status.value == "conflict"
    assert result.native_listing.denial_reason is None
    assert result.offer is None
    assert result.preview_token is None


def test_different_existing_offer_head_stops_first_revision_only_intake(intake_conn: Any) -> None:
    account = AccountId("ACC-0048-T")
    org = _org("ORG-0048-T")
    membership = _membership(org, account)

    # Establish the full identity chain and a *first* offer revision directly,
    # bypassing the orchestration, under a revision id the intake will not reuse.
    create_physical_boat(intake_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-HEAD")))
    create_market_episode(
        intake_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-HEAD"), physical_boat_id=PhysicalBoatId("PB-HEAD")
        ),
    )
    create_native_listing(
        intake_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-HEAD"), market_episode_id=MarketEpisodeId("ME-HEAD")
        ),
    )
    prior_write = write_native_listing_offer_revision(
        intake_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-HEAD"),
        revision_id=NativeListingOfferRevisionId("REV-PRIOR"),
        expected_current_revision_id=None,
        offer=_amount_offer(),
    )
    assert prior_write.status is NativeListingOfferWriteStatus.CREATED

    # Now run full intake reusing the same identity chain (ALREADY_EXISTS for
    # stages 1-3) but a *different* first-revision offer_revision_id: the
    # orchestration's hard-coded expected_current_revision_id=None cannot
    # match the real existing head (REV-PRIOR).
    request = _base_request(
        physical_boat_id=PhysicalBoatId("PB-HEAD"),
        market_episode_id=MarketEpisodeId("ME-HEAD"),
        native_listing_id=NativeListingId("NL-HEAD"),
        offer_revision_id=NativeListingOfferRevisionId("REV-NEW-FIRST"),
    )
    result = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)

    assert result.outcome is ListingIntakeOutcome.OFFER_FAILED
    assert result.physical_boat.status.value == "already_exists"
    assert (
        result.market_episode is not None and result.market_episode.status.value == "already_exists"
    )
    assert (
        result.native_listing is not None and result.native_listing.status.value == "already_exists"
    )
    assert result.offer is not None
    assert result.offer.status is NativeListingOfferWriteStatus.CONFLICT
    assert result.offer.current_revision_id == NativeListingOfferRevisionId("REV-PRIOR")
    assert result.preview_token is None


def test_retry_after_partial_durable_progress_continues_safely(intake_conn: Any) -> None:
    request = _base_request(
        physical_boat_id=PhysicalBoatId("PB-PARTIAL"),
        market_episode_id=MarketEpisodeId("ME-PARTIAL"),
        native_listing_id=NativeListingId("NL-PARTIAL"),
    )

    # Simulate interruption after stage 1+2 only, driven directly (never via
    # run_listing_intake): this is valid durable partial progress, not
    # corruption.
    create_physical_boat(intake_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-PARTIAL")))
    create_market_episode(
        intake_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-PARTIAL"), physical_boat_id=PhysicalBoatId("PB-PARTIAL")
        ),
    )

    result = run_listing_intake(intake_conn, request=request, preview_signing_secret=_SECRET)

    assert result.outcome is ListingIntakeOutcome.SUCCEEDED
    assert result.physical_boat.status.value == "already_exists"
    assert (
        result.market_episode is not None and result.market_episode.status.value == "already_exists"
    )
    assert result.native_listing is not None and result.native_listing.status.value == "created"
    assert result.offer is not None and result.offer.status.value == "created"
    assert result.preview_token is not None
