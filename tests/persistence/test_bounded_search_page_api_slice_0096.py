"""PostgreSQL + real HTTP tests for the SLICE-0096 bounded `page_after`/
`page_size` public Search HTTP contract
(`GET /api/search/{locale}` and `GET /api/search/{locale}/power`).

Mirrors `tests/persistence/test_search_sensitivity_api.py`'s real-database +
real-`TestClient` fixture style. Covers the normative contract's navigation-
parameter admission rules (`specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md`
§2):

- `page_after`/`page_size` are rejected on a BASE (no active requirement)
  request;
- a cursor accompanying a non-canonical technical query fails closed (400)
  rather than silently discarding it on a 308 redirect;
- malformed/duplicate/out-of-range `page_size` and duplicate/empty
  `page_after` fail closed;
- a genuine multi-page round trip through real HTTP recovers the same
  confirmed matches a single unbounded page would, with
  `evaluation_state`/`next_cursor` consistent at every step;
- a tampered, cross-query-bound or cross-domain (Sail cursor on the Power
  route) cursor fails closed with 400, never a silently "successful" page.
"""

from __future__ import annotations

import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import patch
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
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    VesselCategory,
    VesselCategoryClaim,
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
from hullq.persistence.broker_identity import seed_marketplace_organization
from hullq.persistence.market_episode import create_market_episode
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.security.search_page_cursor import SearchPageCursorDomain, mint_search_page_cursor

VA = AssertionKind.VALUE_ASSERTION


def _as_of() -> datetime:
    return datetime.now(UTC)


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
    schema_name = f"hullq_s0096api_{uuid.uuid4().hex[:16]}"
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


def _attach_ready_cover_image(
    conn: Any, *, listing_id: str, org: MarketplaceOrganization, account: AccountId
) -> None:
    with conn.transaction():
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [account.value],
            )
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
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _seed_sail_claim_only_match(conn: Any, listing_id: str) -> None:
    """One claim-only, publisher-owned-SAIL, shallow-draft ACTIVE candidate
    -- always a confirmed `draft_max<=1.60` match, never requiring any
    BoatDesign/FieldResolution admission."""
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")
    physical_boat_id = f"PB-{listing_id}"
    market_episode_id = f"ME-{listing_id}"

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic SLICE-0096 API fixture listing.",
            asking_price_amount=Decimal("90000.00"),
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
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
            draft=DraftClaim(assertion_kind=VA, value=Decimal("1.10")),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result


def _seed_power_claim_only_match(conn: Any, listing_id: str) -> None:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")
    physical_boat_id = f"PB-{listing_id}"
    market_episode_id = f"ME-{listing_id}"

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic SLICE-0096 API fixture listing.",
            asking_price_amount=Decimal("90000.00"),
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
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result


# ---------------------------------------------------------------------------
# Navigation-parameter admission rules
# ---------------------------------------------------------------------------


def test_page_after_on_base_request_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en", params={"page_after": "anything"})
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_search_request"


def test_page_size_on_base_request_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en", params={"page_size": "20"})
    assert response.status_code == 400


@pytest.mark.parametrize(
    "page_size",
    [
        "0",
        "51",
        "-1",
        "abc",
        "1.5",
        "01",
        pytest.param("9" * 5000, id="5000-digit-overlong"),
    ],
)
def test_malformed_page_size_is_400(client: TestClient, page_size: str) -> None:
    response = client.get("/api/search/en", params={"draft_max": "1.60", "page_size": page_size})
    assert response.status_code == 400


def test_overlong_page_size_on_power_route_is_400(client: TestClient) -> None:
    # SLICE-0096 independent review round 2 Finding F1: the shared
    # `_parse_page_params` bound applies identically on the Power route --
    # a 5000-digit value must never reach `int(...)` (which would otherwise
    # raise an unhandled `ValueError` once past CPython's integer-string-
    # conversion digit limit) on this surface either.
    response = client.get(
        "/api/search/en/power", params={"power_drive": "SHAFT", "page_size": "9" * 5000}
    )
    assert response.status_code == 400


def test_overlong_page_after_on_sail_is_400(client: TestClient) -> None:
    # Finding F1: a `page_after` far longer than any real minted cursor
    # must fail closed on length alone, before `verify_search_page_cursor`
    # ever attempts to base64/HMAC/JSON-decode it.
    response = client.get("/api/search/en", params={"draft_max": "1.6", "page_after": "a" * 5000})
    assert response.status_code == 400


def test_overlong_page_after_on_power_is_400(client: TestClient) -> None:
    response = client.get(
        "/api/search/en/power", params={"power_drive": "SHAFT", "page_after": "a" * 5000}
    )
    assert response.status_code == 400


def test_a_genuinely_minted_cursor_for_the_heaviest_active_requirement_stays_valid() -> None:
    # Finding F1: `_MAX_PAGE_AFTER_LENGTH` must never reject a cursor this
    # server itself minted -- measured directly against the heaviest
    # realistic combination of active Sail criteria (every accepted key
    # active at once), which produces the longest `query_identity` this
    # cursor's payload can ever carry.
    from hullq.api.app import _MAX_PAGE_AFTER_LENGTH
    from hullq.application.search_read import build_canonical_search_path

    query_identity = build_canonical_search_path(
        "en",
        draft_max=Decimal("1.60"),
        keel_configuration="FIN_WITH_BULB",
        loa_min=Decimal("10.00"),
        loa_max=Decimal("15.00"),
        rudder_configuration="TRANSOM_HUNG",
        hull_configuration="CATAMARAN",
        cockpit_position="MULTIPLE",
        deck_saloon="PILOTHOUSE",
        beam_min=Decimal("3.20"),
        beam_max=Decimal("4.40"),
        hull_material="GRP_FIBERGLASS",
    )
    cursor = mint_search_page_cursor(
        domain=SearchPageCursorDomain.SAIL,
        query_identity=query_identity,
        page_size=50,
        last_native_listing_id="NL-00000000000000000000000000000000",
        secret=_SECRET,
    )
    assert len(cursor) <= _MAX_PAGE_AFTER_LENGTH, (
        f"a genuinely minted cursor ({len(cursor)} chars) must stay under "
        f"the {_MAX_PAGE_AFTER_LENGTH}-char bound"
    )


def test_duplicate_page_size_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en?draft_max=1.60&page_size=10&page_size=20")
    assert response.status_code == 400


def test_duplicate_page_after_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en?draft_max=1.60&page_after=a&page_after=b")
    assert response.status_code == 400


def test_empty_page_after_is_400(client: TestClient) -> None:
    response = client.get("/api/search/en?draft_max=1.60&page_after=")
    assert response.status_code == 400


def test_cursor_with_noncanonical_query_is_400_not_redirect(client: TestClient) -> None:
    # draft_max=1.600 is valid but non-canonical (trailing zero) -- without a
    # cursor this would 308; with a cursor present it must fail closed
    # instead of discarding/rebinding the cursor across the redirect.
    response = client.get("/api/search/en", params={"draft_max": "1.600", "page_after": "anything"})
    assert response.status_code == 400
    # Confirm the ordinary (no cursor) case is indeed still a 308, proving
    # the 400 above is specifically the cursor+redirect interaction.
    redirect_response = client.get(
        "/api/search/en", params={"draft_max": "1.600"}, follow_redirects=False
    )
    assert redirect_response.status_code == 308


# ---------------------------------------------------------------------------
# Genuine multi-page HTTP round trip
# ---------------------------------------------------------------------------


def test_sail_multi_page_http_round_trip_recovers_all_matches(
    client: TestClient, api_conn: Any
) -> None:
    listing_ids = [f"NL-0096API-SAIL-{i:04d}" for i in range(1, 4)]
    for listing_id in listing_ids:
        _seed_sail_claim_only_match(api_conn, listing_id)

    seen: list[str] = []
    next_cursor: str | None = None
    for _ in range(10):
        params: dict[str, str] = {"draft_max": "1.6", "page_size": "1"}
        if next_cursor is not None:
            params["page_after"] = next_cursor
        response = client.get("/api/search/en", params=params)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["page_size"] == 1
        assert body["evaluation_state"] in ("PARTIAL", "COMPLETE")
        matches = [m["native_listing_id"] for m in body["publisher_claim_matches"]]
        seen.extend(matches)
        if body["evaluation_state"] == "COMPLETE":
            assert body["next_cursor"] is None
            break
        assert body["next_cursor"] is not None
        next_cursor = body["next_cursor"]
    else:
        raise AssertionError("did not complete within 10 pages")

    assert sorted(seen) == sorted(listing_ids)
    assert len(seen) == len(set(seen))


def test_power_single_page_http_round_trip(client: TestClient, api_conn: Any) -> None:
    _seed_power_claim_only_match(api_conn, "NL-0096API-PWR-0001")
    response = client.get("/api/search/en/power", params={"power_drive": "SHAFT"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["evaluation_state"] == "COMPLETE"
    assert body["next_cursor"] is None
    assert [m["native_listing_id"] for m in body["publisher_claim_matches"]] == [
        "NL-0096API-PWR-0001"
    ]


# ---------------------------------------------------------------------------
# Cursor tamper / cross-query / cross-domain failure closure
# ---------------------------------------------------------------------------


def test_tampered_cursor_is_400(client: TestClient, api_conn: Any) -> None:
    _seed_sail_claim_only_match(api_conn, "NL-0096API-TAMPER-0001")
    response = client.get(
        "/api/search/en", params={"draft_max": "1.6", "page_after": "not-a-real-cursor"}
    )
    assert response.status_code == 400


def test_cursor_bound_to_different_query_is_400(client: TestClient, api_conn: Any) -> None:
    for listing_id in ("NL-0096API-XQ-0001", "NL-0096API-XQ-0002"):
        _seed_sail_claim_only_match(api_conn, listing_id)

    first = client.get("/api/search/en", params={"draft_max": "1.6", "page_size": "1"})
    assert first.status_code == 200
    cursor = first.json()["next_cursor"]
    assert cursor is not None

    # Reusing the SAME cursor against a DIFFERENT draft_max query must fail
    # closed -- the cursor's query_identity binding no longer matches.
    reused = client.get(
        "/api/search/en", params={"draft_max": "2", "page_size": "1", "page_after": cursor}
    )
    assert reused.status_code == 400


def test_cursor_minted_for_sail_rejected_on_power_route(client: TestClient, api_conn: Any) -> None:
    _seed_power_claim_only_match(api_conn, "NL-0096API-XDOM-0001")
    sail_cursor = mint_search_page_cursor(
        domain=SearchPageCursorDomain.SAIL,
        query_identity="/en/power/search?power_drive=SHAFT",
        page_size=20,
        last_native_listing_id="NL-0096API-XDOM-0001",
        secret=_SECRET,
    )
    response = client.get(
        "/api/search/en/power",
        params={"power_drive": "SHAFT", "page_after": sail_cursor},
    )
    assert response.status_code == 400


# ---------------------------------------------------------------------------
# Independent review Finding A: prove the complete public HTTP request path
# never invokes the old unbounded evaluation functions, real end-to-end,
# at 0/40/200 and a larger sparse/negative-heavy population. A patched
# function that fires raises immediately through `TestClient` (default
# `raise_server_exceptions=True`), failing the test with a clear traceback
# rather than merely a silently-passing call count.
# ---------------------------------------------------------------------------


def _seed_sail_claim_only(conn: Any, *, index: int, draft: str, category: VesselCategory) -> str:
    listing_id = f"NL-0096API-BOUND-{index:05d}"
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")
    physical_boat_id = f"PB-{listing_id}"
    market_episode_id = f"ME-{listing_id}"

    create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
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
        revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
        expected_current_revision_id=None,
        offer=NativeListingOfferSnapshot(
            asking_price_mode=AskingPriceMode.AMOUNT,
            location_country="FR",
            broker_description="Synthetic SLICE-0096 bounded-evaluation fixture listing.",
            asking_price_amount=Decimal("90000.00"),
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
            marketed_brand_claim="Unbranded",
            model_designation_claim="Synthetic",
            build_year=BuildYearClaim(assertion_kind=VA, value=2015),
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=category),
            draft=DraftClaim(assertion_kind=VA, value=Decimal(draft)),
        ),
    )
    _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
    result = publish_native_listing(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
    )
    assert result.status.value == "transitioned", result
    return listing_id


def _seed_sail_mixed_population(conn: Any, population_size: int) -> None:
    for index in range(1, population_size + 1):
        # Alternate shallow (confirmed match)/deep (non-match) draft, all
        # SAIL -- never a single CONFIRMED_MATCH when queried on a field
        # (e.g. keel_configuration) none of them have claimed at all.
        draft = "1.10" if index % 2 == 0 else "1.90"
        _seed_sail_claim_only(conn, index=index, draft=draft, category=VesselCategory.SAIL)
    if population_size:
        conn.commit()


@pytest.mark.parametrize("population_size", [0, 40, 200])
def test_sail_bounded_endpoint_never_calls_old_unbounded_evaluators(
    client: TestClient, api_conn: Any, population_size: int
) -> None:
    import hullq.application.native_inventory_query as native_inventory_query_module
    import hullq.application.search_read as search_read_module

    _seed_sail_mixed_population(api_conn, population_size)

    def _forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "old unbounded Sail evaluator must never be called from a bounded page request"
        )

    with (
        patch.object(search_read_module, "evaluate_draft_max_requirement", side_effect=_forbidden),
        patch.object(
            search_read_module, "evaluate_native_inventory_requirements", side_effect=_forbidden
        ),
        patch.object(
            native_inventory_query_module,
            "evaluate_native_inventory_requirements",
            side_effect=_forbidden,
        ),
    ):
        # (a) a query with real matches among the population (even-indexed
        # candidates are shallow-draft matches for draft_max=1.6).
        match_response = client.get(
            "/api/search/en", params={"draft_max": "1.6", "page_size": "20"}
        )
        assert match_response.status_code == 200, match_response.text

        # (b) a query matching NOTHING in this population at all (none of
        # these candidates ever claimed a keel_configuration) -- the
        # sparse/negative-heavy, zero-match PARTIAL/COMPLETE case.
        zero_match_response = client.get(
            "/api/search/en", params={"keel_configuration": "FIN", "page_size": "20"}
        )
        assert zero_match_response.status_code == 200, zero_match_response.text
        assert zero_match_response.json()["confirmed_match_count"] == 0


def _seed_power_mixed_population(conn: Any, population_size: int) -> None:
    for index in range(1, population_size + 1):
        listing_id = f"NL-0096API-PBOUND-{index:05d}"
        account = AccountId(f"ACC-{listing_id}")
        org = _org(f"ORG-{listing_id}")
        membership = _membership(org, account, f"OM-{listing_id}")
        physical_boat_id = f"PB-{listing_id}"
        market_episode_id = f"ME-{listing_id}"
        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(market_episode_id),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
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
            revision_id=NativeListingOfferRevisionId(f"REV-{listing_id}"),
            expected_current_revision_id=None,
            offer=NativeListingOfferSnapshot(
                asking_price_mode=AskingPriceMode.AMOUNT,
                location_country="FR",
                broker_description="Synthetic SLICE-0096 bounded-evaluation fixture listing.",
                asking_price_amount=Decimal("90000.00"),
                currency="EUR",
            ),
        )
        # Alternate SHAFT (match for power_drive=SHAFT)/POD (non-match),
        # all publisher-owned POWER.
        drive = PowerDriveConfiguration.SHAFT if index % 2 == 0 else PowerDriveConfiguration.POD
        write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Unbranded",
                model_designation_claim="Synthetic",
                build_year=BuildYearClaim(assertion_kind=VA, value=2015),
                vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
                power_drive_configuration=PowerDriveConfigurationClaim(
                    assertion_kind=VA, value=drive
                ),
            ),
        )
        _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
        result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert result.status.value == "transitioned", result
    if population_size:
        conn.commit()


@pytest.mark.parametrize("population_size", [0, 40, 200])
def test_power_bounded_endpoint_never_calls_old_unbounded_evaluators(
    client: TestClient, api_conn: Any, population_size: int
) -> None:
    import hullq.application.power_inventory_query as power_inventory_query_module
    import hullq.application.power_search_read as power_search_read_module

    _seed_power_mixed_population(api_conn, population_size)

    def _forbidden(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError(
            "old unbounded Power evaluator must never be called from a bounded page request"
        )

    with (
        patch.object(
            power_search_read_module, "evaluate_power_requirement", side_effect=_forbidden
        ),
        patch.object(
            power_inventory_query_module, "evaluate_power_drive_requirement", side_effect=_forbidden
        ),
    ):
        match_response = client.get(
            "/api/search/en/power", params={"power_drive": "SHAFT", "page_size": "20"}
        )
        assert match_response.status_code == 200, match_response.text

        # power_engine_count none of these candidates ever claimed --
        # zero-match PARTIAL/COMPLETE case.
        zero_match_response = client.get(
            "/api/search/en/power", params={"power_engine_count": "7", "page_size": "20"}
        )
        assert zero_match_response.status_code == 200, zero_match_response.text
        assert zero_match_response.json()["design_linked_match_count"] == 0


def test_complete_http_request_sql_statement_count_is_bounded(
    client: TestClient, api_conn: Any
) -> None:
    """Finding A: SQL counts/candidate bounds for the COMPLETE HTTP request
    path, not only the isolated new page-evaluator helper -- patches the
    app's own `open_connection` to return a statement-counting proxy around
    the SAME real connection a genuine request would open."""
    import hullq.api.app as app_module

    _seed_sail_mixed_population(api_conn, 200)

    class _CountingCursor:
        def __init__(self, inner: Any, counter: list[int]) -> None:
            self._inner = inner
            self._counter = counter

        def __enter__(self) -> _CountingCursor:
            self._inner.__enter__()
            return self

        def __exit__(self, *exc_info: Any) -> None:
            self._inner.__exit__(*exc_info)

        def execute(self, *args: Any, **kwargs: Any) -> Any:
            self._counter[0] += 1
            return self._inner.execute(*args, **kwargs)

        def __getattr__(self, name: str) -> Any:
            return getattr(self._inner, name)

    class _CountingConnProxy:
        def __init__(self, conn: Any, counter: list[int]) -> None:
            self._conn = conn
            self._counter = counter

        def cursor(self, *args: Any, **kwargs: Any) -> _CountingCursor:
            return _CountingCursor(self._conn.cursor(*args, **kwargs), self._counter)

        def close(self) -> None:
            # The request opens its OWN connection via `open_connection` --
            # a separate connection from the `api_conn` fixture's -- so this
            # must actually release it, never a no-op (a no-op here would
            # leak a real idle-in-transaction backend for the rest of this
            # test session, exactly the class of incident Finding E's own
            # tests guard against).
            self._conn.close()

        def __getattr__(self, name: str) -> Any:
            return getattr(self._conn, name)

    counter = [0]
    real_open_connection = app_module.open_connection

    def _counting_open_connection(url: str, **kwargs: Any) -> Any:
        return _CountingConnProxy(real_open_connection(url, **kwargs), counter)

    with patch.object(app_module, "open_connection", side_effect=_counting_open_connection):
        response = client.get("/api/search/en", params={"draft_max": "1.6", "page_size": "20"})
    assert response.status_code == 200, response.text
    print(
        f"\n[SLICE-0096 Finding A complete-HTTP-request measured evidence] "
        f"population=200, total_sql_statements={counter[0]}"
    )
    # Linear-bounded (mirrors the already-measured claim-only plane shape),
    # never scaling unboundedly with an untouched population beyond this
    # request's own candidate_scan_budget-capped page.
    assert counter[0] < 200 * 12, (
        f"expected a bounded statement count for one complete HTTP request, got {counter[0]}"
    )


# ---------------------------------------------------------------------------
# SLICE-0096 independent review Finding E: a real end-to-end proof that the
# public bounded Search request path actually enforces a server-side
# statement deadline and cleanly releases its connection on expiry -- never
# a hang, never an opaque 500, and never a leaked idle-in-transaction
# backend for a later request to block on (see
# `tests/persistence/test_connection_statement_timeout_slice_0096.py` for
# the equivalent proof at the `open_connection` primitive level; this test
# proves the same thing through the real FastAPI handler, including its
# `except psycopg.errors.QueryCanceled` recovery path).
# ---------------------------------------------------------------------------


def test_search_request_returns_503_and_releases_its_connection_when_the_statement_timeout_fires(
    client: TestClient, api_conn: Any
) -> None:
    import hullq.api.app as app_module

    real_open_connection = app_module.open_connection
    opened_backend_pids: list[int] = []

    def _pid_capturing_open_connection(url: str, **kwargs: Any) -> Any:
        conn = real_open_connection(url, **kwargs)
        opened_backend_pids.append(conn.info.backend_pid)
        return conn

    real_evaluator = app_module.evaluate_draft_max_requirement_page

    def _artificially_slow_evaluator(conn: Any, *args: Any, **kwargs: Any) -> Any:
        # Forces the REAL connection this request opened to spend real wall
        # time against the REAL database, so the real `statement_timeout`
        # this request bound to it can be observed actually firing --
        # never a faked Search outcome.
        conn.execute("SELECT pg_sleep(2)")
        return real_evaluator(conn, *args, **kwargs)

    with (
        patch.object(app_module, "_SEARCH_PAGE_STATEMENT_TIMEOUT_MS", 200),
        patch.object(app_module, "open_connection", side_effect=_pid_capturing_open_connection),
        patch.object(
            app_module,
            "evaluate_draft_max_requirement_page",
            side_effect=_artificially_slow_evaluator,
        ),
    ):
        response = client.get("/api/search/en", params={"draft_max": "1.6"})

    assert response.status_code == 503, response.text
    assert response.json() == {"error": "search_timed_out"}
    assert len(opened_backend_pids) == 1, opened_backend_pids
    (opened_pid,) = opened_backend_pids

    # SLICE-0096 Finding E: check the EXACT backend pid this request's own
    # connection used -- never a database-wide "any idle-in-transaction
    # session" count, which would also see OTHER concurrently running
    # tests' own, entirely legitimate, in-flight transactions under
    # `pytest -n auto` parallel execution (observed causing a false
    # failure under CI's real parallel shard run).
    with api_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE pid = %(pid)s", {"pid": opened_pid}
        )
        (still_present,) = cur.fetchone()
    assert still_present == 0, (
        f"backend pid {opened_pid} (opened for the timed-out request) is still "
        "visible in pg_stat_activity -- the connection must be fully released"
    )


# ---------------------------------------------------------------------------
# SLICE-0096 independent review round 2 Finding E2: a real `statement_timeout`
# bounds any ONE SQL statement, but a bounded page may issue many
# individually-fast statements in sequence (one per scanned candidate, up to
# the candidate_scan_budget) whose cumulative total could still run far
# longer than any single statement's own timeout, with no single statement
# ever slow enough to trip `_SEARCH_PAGE_STATEMENT_TIMEOUT_MS`. These tests
# prove the separate, cumulative `request_deadline_seconds` budget
# (`hullq.application.native_inventory_query.check_request_deadline`) is
# real: it fires against a genuine population of REAL, individually-fast
# statements (never a `pg_sleep`-faked single slow one), the connection is
# still cleanly released, and the public HTTP path returns the same
# controlled 503.
# ---------------------------------------------------------------------------


def test_evaluator_raises_when_many_fast_statements_exceed_the_request_deadline(
    api_conn: Any,
) -> None:
    from hullq.application.native_inventory_query import (
        SearchRequestDeadlineExceeded,
        evaluate_native_inventory_requirements_page,
    )

    # A zero-match, never-early-stopping population (none of these
    # candidates ever claimed keel_configuration at all) forces a full
    # scan of every seeded candidate -- real measured evidence
    # (`tests/persistence/test_bounded_search_page_performance_slice_0096.py`)
    # shows a 200-candidate scan takes roughly 0.2s of real, individually-
    # fast statements; a 0.05s deadline is comfortably below that, with
    # ample margin for slower CI hardware.
    _seed_sail_mixed_population(api_conn, 200)

    with pytest.raises(Exception) as exc_info:
        evaluate_native_inventory_requirements_page(
            api_conn,
            draft_max=None,
            keel_configuration="FIN",
            as_of=_as_of(),
            after_native_listing_id=None,
            page_size=20,
            request_deadline_seconds=0.05,
        )
    assert isinstance(exc_info.value, SearchRequestDeadlineExceeded)


def test_search_request_returns_503_and_releases_its_connection_when_the_request_deadline_fires(
    client: TestClient, api_conn: Any
) -> None:
    import hullq.api.app as app_module

    real_open_connection = app_module.open_connection
    opened_backend_pids: list[int] = []

    def _pid_capturing_open_connection(url: str, **kwargs: Any) -> Any:
        conn = real_open_connection(url, **kwargs)
        opened_backend_pids.append(conn.info.backend_pid)
        return conn

    # Same zero-match, never-early-stopping population as the direct-
    # evaluator proof above, exercised through the real public HTTP route
    # this time -- no `pg_sleep`, no patched evaluator: every one of these
    # statements is genuinely fast on its own.
    _seed_sail_mixed_population(api_conn, 200)

    with (
        patch.object(app_module, "_SEARCH_PAGE_REQUEST_DEADLINE_SECONDS", 0.05),
        patch.object(app_module, "open_connection", side_effect=_pid_capturing_open_connection),
    ):
        response = client.get(
            "/api/search/en", params={"keel_configuration": "FIN", "page_size": "20"}
        )

    assert response.status_code == 503, response.text
    assert response.json() == {"error": "search_timed_out"}
    assert len(opened_backend_pids) == 1, opened_backend_pids
    (opened_pid,) = opened_backend_pids

    with api_conn.cursor() as cur:
        cur.execute(
            "SELECT count(*) FROM pg_stat_activity WHERE pid = %(pid)s", {"pid": opened_pid}
        )
        (still_present,) = cur.fetchone()
    assert still_present == 0, (
        f"backend pid {opened_pid} (opened for the deadline-exceeded request) is "
        "still visible in pg_stat_activity -- the connection must be fully released"
    )
