"""PostgreSQL-backed freshness gating tests for the native-inventory Search
candidate path — SLICE-0052 contract §7.2.

Covers: a STALE ACTIVE candidate is excluded before any technical `draft_max`
classification and is never counted as `insufficient_data_count` (its
exclusion is inventory freshness, not missing technical truth); a
DUE_FOR_CONFIRMATION candidate remains CONFIRMED_MATCH-eligible and carries
its freshness status/effective `last_confirmed_at`; and design/configuration/
Decimal/PhysicalBoat-contradiction semantics from SLICE-0051 are otherwise
unaffected. Mirrors
`tests/persistence/test_inventory_search_classification.py`'s real
FieldResolution admission pattern (no monkeypatching of design eligibility).
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest

from hullq.application.inventory_search import evaluate_draft_max_requirement
from hullq.domain.market_identity import (
    BoatDesignRef,
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.native_listing_freshness import FreshnessStatus
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
)
from hullq.domain.provenance import SubjectKind
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
from hullq.persistence.native_listing_lifecycle import (
    list_publication_transitions,
    publish_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER

from ._field_resolution_support import admit_resolved_draft_max

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_inventory_search_classification.py)
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
    schema_name = f"hullq_s0052fresh_{uuid.uuid4().hex[:16]}"
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


_DESIGN_ID = "BD-0052-FRESH"
_DESIGN_BASELINE_DRAFT_MAX_M = Decimal("1.60")


@pytest.fixture(autouse=True)
def _admit_design_via_real_field_resolution(api_conn: Any) -> None:
    with api_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            ["BM-0052-FRESH", "Model BM-0052-FRESH", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [
                _DESIGN_ID,
                "BM-0052-FRESH",
                "{}",
                "[]",
                json.dumps({"dimensions": {"draft_max_m": float(_DESIGN_BASELINE_DRAFT_MAX_M)}}),
                "[]",
                "[]",
                "{}",
                "1" * 64,
            ],
        )
    api_conn.commit()

    admit_resolved_draft_max(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=_DESIGN_ID,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=_DESIGN_BASELINE_DRAFT_MAX_M,
        resolution_id="FR-0052-FRESH-BASELINE",
    )


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


def _publish_confirmed_candidate(conn: Any, *, listing_id: str) -> None:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(f"PB-{listing_id}"), boat_design_ref=BoatDesignRef(_DESIGN_ID)
        ),
    )
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
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Test 1.6",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
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


def test_confirmed_candidate_is_a_match_with_freshness_metadata(api_conn: Any) -> None:
    _publish_confirmed_candidate(api_conn, listing_id="NL-0052F-CONFIRMED")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-0052F-CONFIRMED"))
    confirmed_at = transitions[0].occurred_at

    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"), as_of=confirmed_at)
    assert outcome.confirmed_match_count == 1
    match = outcome.confirmed_matches[0]
    assert match.freshness_status is FreshnessStatus.CONFIRMED
    assert match.last_confirmed_at == confirmed_at
    assert outcome.insufficient_data_count == 0
    assert outcome.confirmed_non_match_count == 0


def test_due_for_confirmation_candidate_remains_a_match_with_due_metadata(api_conn: Any) -> None:
    _publish_confirmed_candidate(api_conn, listing_id="NL-0052F-DUE")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-0052F-DUE"))
    confirmed_at = transitions[0].occurred_at

    outcome = evaluate_draft_max_requirement(
        api_conn, Decimal("1.6"), as_of=confirmed_at + timedelta(days=30)
    )
    assert outcome.confirmed_match_count == 1
    match = outcome.confirmed_matches[0]
    assert match.freshness_status is FreshnessStatus.DUE_FOR_CONFIRMATION
    assert match.last_confirmed_at == confirmed_at
    assert outcome.insufficient_data_count == 0
    assert outcome.confirmed_non_match_count == 0


def test_stale_candidate_is_excluded_and_never_counted_as_insufficient_data(
    api_conn: Any,
) -> None:
    _publish_confirmed_candidate(api_conn, listing_id="NL-0052F-STALE")
    api_conn.commit()
    transitions = list_publication_transitions(api_conn, NativeListingId("NL-0052F-STALE"))
    confirmed_at = transitions[0].occurred_at

    outcome = evaluate_draft_max_requirement(
        api_conn, Decimal("1.6"), as_of=confirmed_at + timedelta(days=37)
    )
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_match_count == 0
    # Freshness exclusion is inventory staleness, never technical
    # INSUFFICIENT_DATA or CONFIRMED_NON_MATCH -- both must stay zero.
    assert outcome.insufficient_data_count == 0
    assert outcome.confirmed_non_match_count == 0


def test_unknown_candidate_with_no_admissible_evidence_is_excluded(api_conn: Any) -> None:
    """An ACTIVE, design-linked, draft-claimed candidate whose lifecycle
    became ACTIVE with no recorded publication-transition evidence resolves
    UNKNOWN and must be excluded exactly like STALE -- never counted as
    insufficient technical data."""
    account = AccountId("ACC-0052F-UNKNOWN")
    org = _org("ORG-0052F-UNKNOWN")
    membership = _membership(org, account, "OM-0052F-UNKNOWN")
    create_physical_boat(
        api_conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId("PB-0052F-UNKNOWN"), boat_design_ref=BoatDesignRef(_DESIGN_ID)
        ),
    )
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-0052F-UNKNOWN"),
            physical_boat_id=PhysicalBoatId("PB-0052F-UNKNOWN"),
        ),
    )
    create_native_listing(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId("NL-0052F-UNKNOWN"),
            market_episode_id=MarketEpisodeId("ME-0052F-UNKNOWN"),
        ),
    )
    write_native_listing_offer_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0052F-UNKNOWN"),
        revision_id=NativeListingOfferRevisionId("REV-0052F-UNKNOWN"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    write_physical_boat_claim_revision(
        api_conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId("NL-0052F-UNKNOWN"),
        revision_id=PhysicalBoatClaimRevisionId("PBCREV-0052F-UNKNOWN"),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Test 1.6",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
        ),
    )
    with api_conn.cursor() as cur:
        cur.execute(
            "UPDATE native_listings SET lifecycle_state = 'ACTIVE' WHERE native_listing_id = %s",
            ["NL-0052F-UNKNOWN"],
        )
    api_conn.commit()

    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"), as_of=datetime.now(UTC))
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 0
    assert outcome.confirmed_non_match_count == 0
