"""PostgreSQL + real HTTP tests for the SLICE-0051 Requirements -> Native
Inventory Search vertical.

Covers the full bounded funnel end to end against real persisted state:
BoatDesign/configuration eligibility (existential per design, including a
NamedVariant-only shallow-draft override), durable design-identity admission
to ACTIVE native inventory, the publishing Organization's current concrete
`physical_boat.draft` claim, the same-PhysicalBoat contradiction guard across
Organizations, and the resulting CONFIRMED_MATCH / CONFIRMED_NON_MATCH /
INSUFFICIENT_DATA classification -- plus the `/api/search/{locale}` HTTP
contract (200 base/result, 308 canonical redirect, 400 invalid, 404
unsupported locale). Mirrors
tests/persistence/test_public_listing_physical_boat_claims_api.py's
disposable-schema isolation pattern.
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

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
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
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
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_public_listing_physical_boat_claims_api.py)
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
    schema_name = f"hullq_s0051api_{uuid.uuid4().hex[:16]}"
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


@pytest.fixture()
def client(api_url: str) -> TestClient:
    from hullq.api.app import create_app

    app = create_app(database_url=api_url, preview_signing_secret=_SECRET)
    return TestClient(app)


# ---------------------------------------------------------------------------
# Domain/fixture helpers
# ---------------------------------------------------------------------------


def _insert_boat_design(
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    baseline_draft_max_m: float | None,
    named_variants: list[dict[str, Any]] | None = None,
) -> None:
    """Minimal direct-SQL admission of one BOAT_DESIGN_SCHEMA-shaped canonical
    BoatDesign row, projecting only `baseline.dimensions.draft_max_m` (and
    optional `named_variants[].overrides.dimensions.draft_max_m`) -- exactly
    what `hullq.search.draft_max_design_bridge` reads. Mirrors
    `scripts/inspect_first_buyer_critical_physical_boat_truth.py`'s
    `_insert_boat_design_with_leaky_baseline` pattern."""
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps({"dimensions": {"draft_max_m": baseline_draft_max_m}})
        variants_json = json.dumps(named_variants or [])
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, variants_json, "[]", "{}", "1" * 64],
        )
    conn.commit()


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


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    offer_revision_id: str,
    boat_design_ref: BoatDesignRef | None,
    publish: bool = True,
    reuse_physical_boat: bool = False,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    if not reuse_physical_boat:
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
    create_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        listing=NativeListing(
            id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
        ),
    )
    write_native_listing_offer_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=NativeListingOfferRevisionId(offer_revision_id),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="A well-maintained cruising sloop.",
            asking_price_amount=Decimal("125000.00"),
            currency="EUR",
        ),
    )
    if publish:
        publish_result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert publish_result.status.value == "transitioned", publish_result
    return account, org, membership


def _write_draft_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    draft: DraftClaim | None,
) -> None:
    write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(revision_id),
        expected_current_revision_id=None,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=draft,
        ),
    )


_SHALLOW_COMPATIBLE_DESIGN = "BD-0051-SHALLOW"
_TOO_DEEP_DESIGN = "BD-0051-DEEP"


@pytest.fixture()
def seeded(api_conn: Any) -> dict[str, Any]:
    """Seed the complete bounded scenario used by every RESULT-path test.

    draft_max under test is always 1.6 m.

        A: shallow-compatible design, publisher draft 1.40 -> CONFIRMED_MATCH
        B: shallow-compatible design, publisher draft 1.90 -> CONFIRMED_NON_MATCH
        C: shallow-compatible design, publisher draft omitted -> INSUFFICIENT_DATA
        D: shallow-compatible design, publisher draft UNKNOWN -> INSUFFICIENT_DATA
        E: shallow-compatible design, publisher draft 1.40 but another
           Organization's current claim for the SAME PhysicalBoatId states
           1.90 -> INSUFFICIENT_DATA (conflict)
        F: always-too-deep design (no shallow variant), publisher draft 1.00
           -> never confirmed (design-level not compatible)
        G: PhysicalBoat with NO BoatDesignRef, publisher draft 1.00 -> never
           confirmed (no durable applicable design identity)
        H: shallow-compatible design, DRAFT (unpublished) listing with
           publisher draft 1.00 -> never a public result
    """
    conn = api_conn
    _insert_boat_design(
        conn,
        _SHALLOW_COMPATIBLE_DESIGN,
        "BM-0051-SHALLOW",
        baseline_draft_max_m=1.85,
        named_variants=[{"id": "shallow-keel", "overrides": {"dimensions": {"draft_max_m": 1.30}}}],
    )
    _insert_boat_design(
        conn, _TOO_DEEP_DESIGN, "BM-0051-DEEP", baseline_draft_max_m=2.10, named_variants=[]
    )

    shallow_ref = BoatDesignRef(_SHALLOW_COMPATIBLE_DESIGN)
    deep_ref = BoatDesignRef(_TOO_DEEP_DESIGN)

    a = _make_active_listing(
        conn,
        listing_id="NL-0051-A",
        physical_boat_id="PB-0051-A",
        market_episode_id="ME-0051-A",
        offer_revision_id="REV-0051-A",
        boat_design_ref=shallow_ref,
    )
    _write_draft_claim(
        conn,
        account=a[0],
        org=a[1],
        membership=a[2],
        listing_id="NL-0051-A",
        revision_id="PBCREV-0051-A",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
    )

    b = _make_active_listing(
        conn,
        listing_id="NL-0051-B",
        physical_boat_id="PB-0051-B",
        market_episode_id="ME-0051-B",
        offer_revision_id="REV-0051-B",
        boat_design_ref=shallow_ref,
    )
    _write_draft_claim(
        conn,
        account=b[0],
        org=b[1],
        membership=b[2],
        listing_id="NL-0051-B",
        revision_id="PBCREV-0051-B",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")),
    )

    _make_active_listing(
        conn,
        listing_id="NL-0051-C",
        physical_boat_id="PB-0051-C",
        market_episode_id="ME-0051-C",
        offer_revision_id="REV-0051-C",
        boat_design_ref=shallow_ref,
    )
    # C: draft claim omitted entirely -- no write_physical_boat_claim_revision call.

    d = _make_active_listing(
        conn,
        listing_id="NL-0051-D",
        physical_boat_id="PB-0051-D",
        market_episode_id="ME-0051-D",
        offer_revision_id="REV-0051-D",
        boat_design_ref=shallow_ref,
    )
    _write_draft_claim(
        conn,
        account=d[0],
        org=d[1],
        membership=d[2],
        listing_id="NL-0051-D",
        revision_id="PBCREV-0051-D",
        draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
    )

    e = _make_active_listing(
        conn,
        listing_id="NL-0051-E",
        physical_boat_id="PB-0051-E",
        market_episode_id="ME-0051-E",
        offer_revision_id="REV-0051-E",
        boat_design_ref=shallow_ref,
    )
    _write_draft_claim(
        conn,
        account=e[0],
        org=e[1],
        membership=e[2],
        listing_id="NL-0051-E",
        revision_id="PBCREV-0051-E",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
    )
    # A second Organization publishes its own listing for the SAME
    # PhysicalBoatId with a conflicting current draft claim.
    e_other_account = AccountId("ACC-0051-E-OTHER")
    e_other_org = _org("ORG-0051-E-OTHER")
    e_other_membership = _membership(e_other_org, e_other_account, "OM-0051-E-OTHER")
    create_market_episode(
        conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-0051-E-OTHER"), physical_boat_id=PhysicalBoatId("PB-0051-E")
        ),
    )
    create_native_listing(
        conn,
        account_id=e_other_account,
        candidate_organization=e_other_org,
        membership=e_other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-0051-E-OTHER"),
            market_episode_id=MarketEpisodeId("ME-0051-E-OTHER"),
        ),
    )
    _write_draft_claim(
        conn,
        account=e_other_account,
        org=e_other_org,
        membership=e_other_membership,
        listing_id="NL-0051-E-OTHER",
        revision_id="PBCREV-0051-E-OTHER",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")),
    )

    f = _make_active_listing(
        conn,
        listing_id="NL-0051-F",
        physical_boat_id="PB-0051-F",
        market_episode_id="ME-0051-F",
        offer_revision_id="REV-0051-F",
        boat_design_ref=deep_ref,
    )
    _write_draft_claim(
        conn,
        account=f[0],
        org=f[1],
        membership=f[2],
        listing_id="NL-0051-F",
        revision_id="PBCREV-0051-F",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.00")),
    )

    g = _make_active_listing(
        conn,
        listing_id="NL-0051-G",
        physical_boat_id="PB-0051-G",
        market_episode_id="ME-0051-G",
        offer_revision_id="REV-0051-G",
        boat_design_ref=None,
    )
    _write_draft_claim(
        conn,
        account=g[0],
        org=g[1],
        membership=g[2],
        listing_id="NL-0051-G",
        revision_id="PBCREV-0051-G",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.00")),
    )

    h = _make_active_listing(
        conn,
        listing_id="NL-0051-H",
        physical_boat_id="PB-0051-H",
        market_episode_id="ME-0051-H",
        offer_revision_id="REV-0051-H",
        boat_design_ref=shallow_ref,
        publish=False,
    )
    _write_draft_claim(
        conn,
        account=h[0],
        org=h[1],
        membership=h[2],
        listing_id="NL-0051-H",
        revision_id="PBCREV-0051-H",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.00")),
    )

    return {}


# ---------------------------------------------------------------------------
# Application-layer tests
# ---------------------------------------------------------------------------


def test_evaluate_draft_max_requirement_is_always_empty_against_real_persisted_data(
    api_conn: Any, seeded: dict[str, Any]
) -> None:
    """Amendment review Finding 3: no accepted production per-field
    qualification/resolution source exists for `canonical_boat_designs`, so
    `compatible_boat_design_ids` always returns an empty set against real
    persisted BoatDesign data (see `hullq.search.draft_max_design_bridge`'s
    module docstring). This is proven here even though listing A's own
    concrete claim (1.40 m) would otherwise satisfy `draft_max=1.6` --
    design-level eligibility never opens the gate for it, so it is excluded
    like every other seeded listing, never landing in any surface."""
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_match_count == 0
    assert outcome.confirmed_non_match_count == 0
    assert outcome.insufficient_data_count == 0


# ---------------------------------------------------------------------------
# HTTP contract tests
# ---------------------------------------------------------------------------


def test_base_state_returns_200_with_no_active_requirement(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.get("/api/search/de")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] is None
    assert response.headers.get("x-robots-tag") == "noindex"


def test_canonical_result_is_honestly_empty_pending_finding_3_prerequisite(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """Mirrors the application-layer proof above through the real HTTP
    surface: zero confirmed/insufficient results, never a fabricated match,
    until the Finding 3 production qualification prerequisite is resolved."""
    response = client.get("/api/search/en?draft_max=1.6")
    assert response.status_code == 200
    body = response.json()
    assert body["active_requirement"] == {"draft_max": "1.6"}
    assert body["confirmed_match_count"] == 0
    assert body["confirmed_matches"] == []
    assert body["insufficient_data_count"] == 0


def test_noncanonical_value_redirects_308(client: TestClient) -> None:
    response = client.get("/api/search/de?draft_max=1.600", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "/de/search?draft_max=1.6"


def test_equal_duplicates_redirect_308(client: TestClient) -> None:
    response = client.get("/api/search/de?draft_max=1.6&draft_max=1.60", follow_redirects=False)
    assert response.status_code == 308
    assert response.headers["location"] == "/de/search?draft_max=1.6"


def test_conflicting_duplicates_400(client: TestClient) -> None:
    response = client.get("/api/search/de?draft_max=1.6&draft_max=1.7", follow_redirects=False)
    assert response.status_code == 400


def test_empty_value_400(client: TestClient) -> None:
    response = client.get("/api/search/de?draft_max=", follow_redirects=False)
    assert response.status_code == 400


def test_exponent_notation_400(client: TestClient) -> None:
    response = client.get("/api/search/de?draft_max=1e0", follow_redirects=False)
    assert response.status_code == 400


def test_unknown_parameter_400(client: TestClient) -> None:
    response = client.get("/api/search/de?foo=bar", follow_redirects=False)
    assert response.status_code == 400


def test_empty_nonsemantic_allowlist_utm_source_400(client: TestClient) -> None:
    response = client.get("/api/search/de?utm_source=x", follow_redirects=False)
    assert response.status_code == 400


def test_unsupported_locale_404(client: TestClient) -> None:
    response = client.get("/api/search/it?draft_max=1.6", follow_redirects=False)
    assert response.status_code == 404
