"""PostgreSQL + real HTTP freshness gating tests for the public listing
route — SLICE-0052 contract §7.1.

Covers: ACTIVE+CONFIRMED and ACTIVE+DUE_FOR_CONFIRMATION remain visible
(with freshness metadata and a buyer-visible DUE distinction); ACTIVE+STALE
and ACTIVE+UNKNOWN collapse to the identical ordinary not-found response
used for DRAFT/WITHDRAWN, without mutating lifecycle; and a successful
reconfirmation restores visibility. Uses `create_app`'s
`freshness_as_of_override` (server-side-only, never client-controlled) to
evaluate the same persisted listing at exact synthetic times without
sleeping, per contract §8.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import FreshnessConfirmationId
from hullq.domain.native_listing_lifecycle import NativeListingLifecycleState
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
)
from hullq.persistence.alembic_baseline import alembic_upgrade_head, prepare_alembic_baseline
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_freshness import reconfirm_native_listing
from hullq.persistence.native_listing_lifecycle import (
    fetch_lifecycle_state,
    list_publication_transitions,
    publish_native_listing,
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
def api_url(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0052api_{uuid.uuid4().hex[:16]}"
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
def api_conn(api_url: str) -> Generator[Any]:
    conn = psycopg.connect(api_url)
    try:
        yield conn
    finally:
        conn.close()


_SECRET = b"0" * 32


def _client(api_url: str, *, as_of_override: Any = None) -> TestClient:
    from hullq.api.app import create_app

    app = create_app(
        database_url=api_url,
        preview_signing_secret=_SECRET,
        freshness_as_of_override=as_of_override,
    )
    return TestClient(app)


# ---------------------------------------------------------------------------
# Domain fixtures
# ---------------------------------------------------------------------------


def _org(value: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(value),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


def _membership(
    org: MarketplaceOrganization, account: AccountId, membership_id: str
) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=account,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )


def _publish_listing(
    conn: Any, *, listing_id: str
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-{listing_id}")))
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId(f"ME-{listing_id}"),
            physical_boat_id=PhysicalBoatId(f"PB-{listing_id}"),
        ),
    )
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(f"ME-{listing_id}")
        ),
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    publish_result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership


def test_freshly_published_listing_is_visible_confirmed(api_url: str, api_conn: Any) -> None:
    _publish_listing(api_conn, listing_id="NL-FRESH52")
    api_conn.commit()

    client = _client(api_url)  # no override -> real current time
    resp = client.get("/api/listings/NL-FRESH52")
    assert resp.status_code == 200
    body = resp.json()
    assert body["freshness_status"] == "CONFIRMED"
    assert body["last_confirmed_at"] is not None


def test_exact_30_day_boundary_is_visible_due_for_confirmation(api_url: str, api_conn: Any) -> None:
    _publish_listing(api_conn, listing_id="NL-DUE52")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-DUE52"))
    confirmed_at = transitions[0].occurred_at

    client = _client(api_url, as_of_override=confirmed_at + timedelta(days=30))
    resp = client.get("/api/listings/NL-DUE52")
    assert resp.status_code == 200
    body = resp.json()
    assert body["freshness_status"] == "DUE_FOR_CONFIRMATION"
    assert body["last_confirmed_at"] is not None


def test_exact_37_day_boundary_is_suppressed_without_changing_lifecycle(
    api_url: str, api_conn: Any
) -> None:
    _publish_listing(api_conn, listing_id="NL-STALE52")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-STALE52"))
    confirmed_at = transitions[0].occurred_at

    client = _client(api_url, as_of_override=confirmed_at + timedelta(days=37))
    resp = client.get("/api/listings/NL-STALE52")
    assert resp.status_code == 404

    assert (
        fetch_lifecycle_state(api_conn, NativeListingId("NL-STALE52"))
        is NativeListingLifecycleState.ACTIVE
    )


def test_active_listing_with_no_admissible_evidence_is_unknown_and_suppressed(
    api_url: str, api_conn: Any
) -> None:
    """Simulates a listing whose lifecycle became ACTIVE with no recorded
    publication-transition evidence (should not normally happen through the
    real accepted publish path, but contract §4.1 requires this to fail
    closed to UNKNOWN/suppressed rather than raising or inventing evidence)."""
    account = AccountId("ACC-UNKNOWN52")
    org = _org("ORG-UNKNOWN52")
    membership = _membership(org, account, "OM-UNKNOWN52")
    create_physical_boat(api_conn, physical_boat=PhysicalBoat(id=PhysicalBoatId("PB-UNKNOWN52")))
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-UNKNOWN52"), physical_boat_id=PhysicalBoatId("PB-UNKNOWN52")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-UNKNOWN52"), market_episode_id=MarketEpisodeId("ME-UNKNOWN52")
        ),
    )
    write_native_listing_offer_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-UNKNOWN52"),
        revision_id=NativeListingOfferRevisionId("REV-UNKNOWN52"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    # Force lifecycle to ACTIVE directly, bypassing publish_native_listing,
    # so no publication_transitions evidence row is ever written.
    with api_conn.cursor() as cur:
        cur.execute(
            "UPDATE native_listings SET lifecycle_state = 'ACTIVE' WHERE native_listing_id = %s",
            ["NL-UNKNOWN52"],
        )
    api_conn.commit()

    client = _client(api_url)
    resp = client.get("/api/listings/NL-UNKNOWN52")
    assert resp.status_code == 404
    assert (
        fetch_lifecycle_state(api_conn, NativeListingId("NL-UNKNOWN52"))
        is NativeListingLifecycleState.ACTIVE
    )


def test_reconfirmation_restores_visibility_after_stale(api_url: str, api_conn: Any) -> None:
    account, org, membership = _publish_listing(api_conn, listing_id="NL-RESTORE52")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-RESTORE52"))
    confirmed_at = transitions[0].occurred_at

    stale_client = _client(api_url, as_of_override=confirmed_at + timedelta(days=37))
    assert stale_client.get("/api/listings/NL-RESTORE52").status_code == 404

    reconfirm_conn = psycopg.connect(api_url)
    try:
        result = reconfirm_native_listing(
            reconfirm_conn,
            confirmation_id=FreshnessConfirmationId("FC-RESTORE52-1"),
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId("NL-RESTORE52"),
        )
        assert result.status.value == "reconfirmed", result
    finally:
        reconfirm_conn.close()

    restored_client = _client(api_url)  # real current time, right after reconfirmation
    resp = restored_client.get("/api/listings/NL-RESTORE52")
    assert resp.status_code == 200
    assert resp.json()["freshness_status"] == "CONFIRMED"

    assert (
        fetch_lifecycle_state(api_conn, NativeListingId("NL-RESTORE52"))
        is NativeListingLifecycleState.ACTIVE
    )
