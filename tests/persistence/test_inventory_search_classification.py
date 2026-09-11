"""PostgreSQL-backed regression tests for the concrete-listing classification
funnel in `hullq.application.inventory_search` — SLICE-0051 amendment review.

Amendment review Finding 3 established that `compatible_boat_design_ids`
must always return an empty set against real persisted BoatDesign data (no
accepted production per-field qualification/resolution source exists yet).
That leaves the *downstream* concrete-listing classification stages --
publisher-claim resolution, the same-PhysicalBoat contradiction guard,
exact-Decimal comparison (Finding 2) and single-query snapshot consistency
(Finding 5) -- structurally correct and independently tested, but otherwise
unreachable through the real design gate today.

Every test in this module monkeypatches
`hullq.application.inventory_search.compatible_boat_design_ids` to admit an
explicit design id, standing in for a future accepted qualification source,
so these downstream stages can be proven correct against real PostgreSQL 18
now and remain ready for when Finding 3's prerequisite is resolved. This is
never done in `tests/persistence/test_inventory_search_draft_max_api.py`,
which proves the real, unmodified, currently-fail-closed production
behavior.
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

import hullq.application.inventory_search as inventory_search_module
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
from hullq.persistence import physical_boat_claims as physical_boat_claims_module
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
# Disposable-schema fixture (mirrors test_inventory_search_draft_max_api.py)
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
    schema_name = f"hullq_s0051cls_{uuid.uuid4().hex[:16]}"
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


# ---------------------------------------------------------------------------
# Domain/fixture helpers
# ---------------------------------------------------------------------------

_DESIGN_ID = "BD-0051-CLS"


@pytest.fixture(autouse=True)
def _admit_design_via_stand_in_qualification_source(
    api_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Stand in for a future accepted BoatDesign qualification/resolution
    source (Finding 3): always admits `_DESIGN_ID` as design-level
    CONFIRMED_MATCH, regardless of `draft_max`, so these tests exercise only
    the downstream concrete-listing funnel. A dummy `canonical_boat_designs`
    row is still required to satisfy `physical_boats.boat_design_ref`'s real
    foreign key."""
    with api_conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
            "VALUES (%s, %s, %s)",
            ["BM-0051-CLS", "Model BM-0051-CLS", "0" * 64],
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [
                _DESIGN_ID,
                "BM-0051-CLS",
                "{}",
                "[]",
                json.dumps({"dimensions": {"draft_max_m": None}}),
                "[]",
                "[]",
                "{}",
                "1" * 64,
            ],
        )
    api_conn.commit()

    def _stand_in_compatible_ids(draft_max: Decimal, boat_designs: Any) -> frozenset[str]:
        return frozenset({_DESIGN_ID})

    monkeypatch.setattr(
        inventory_search_module, "compatible_boat_design_ids", _stand_in_compatible_ids
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


def _make_active_listing(
    conn: Any,
    *,
    listing_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    reuse_physical_boat: bool = False,
) -> tuple[AccountId, MarketplaceOrganization, OrganizationMembership]:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    if not reuse_physical_boat:
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(_DESIGN_ID)
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


def _write_draft_claim(
    conn: Any,
    *,
    account: AccountId,
    org: MarketplaceOrganization,
    membership: OrganizationMembership,
    listing_id: str,
    revision_id: str,
    draft: DraftClaim | None,
    expected_current_revision_id: PhysicalBoatClaimRevisionId | None = None,
) -> None:
    result = write_physical_boat_claim_revision(
        conn,
        account_id=account,
        candidate_organization=org,
        membership=membership,
        native_listing_id=NativeListingId(listing_id),
        revision_id=PhysicalBoatClaimRevisionId(revision_id),
        expected_current_revision_id=expected_current_revision_id,
        claims=PhysicalBoatClaimSnapshot(
            marketed_brand_claim="Beneteau",
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=draft,
        ),
    )
    assert result.status.value in ("created", "revised"), result


# ---------------------------------------------------------------------------
# Findings 2 / concrete classification
# ---------------------------------------------------------------------------


def test_confirmed_match_on_inclusive_exact_decimal_boundary(api_conn: Any) -> None:
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-EXACT",
        physical_boat_id="PB-CLS-EXACT",
        market_episode_id="ME-CLS-EXACT",
    )
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-EXACT",
        revision_id="REV-EXACT",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.60")),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-CLS-EXACT"}
    assert outcome.confirmed_matches[0].resolved_draft_m == Decimal("1.60")


def test_confirmed_non_match_above_threshold(api_conn: Any) -> None:
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-DEEP",
        physical_boat_id="PB-CLS-DEEP",
        market_episode_id="ME-CLS-DEEP",
    )
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-DEEP",
        revision_id="REV-DEEP",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert outcome.confirmed_matches == ()
    assert outcome.confirmed_non_match_count == 1
    assert outcome.insufficient_data_count == 0


def test_omitted_draft_is_insufficient_data(api_conn: Any) -> None:
    _make_active_listing(
        api_conn,
        listing_id="NL-CLS-OMIT",
        physical_boat_id="PB-CLS-OMIT",
        market_episode_id="ME-CLS-OMIT",
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 1


def test_unknown_draft_is_insufficient_data(api_conn: Any) -> None:
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-UNK",
        physical_boat_id="PB-CLS-UNK",
        market_episode_id="ME-CLS-UNK",
    )
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-UNK",
        revision_id="REV-UNK",
        draft=DraftClaim(assertion_kind=AssertionKind.UNKNOWN),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 1


def test_cross_organization_conflict_is_insufficient_data(api_conn: Any) -> None:
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-CONF",
        physical_boat_id="PB-CLS-CONF",
        market_episode_id="ME-CLS-CONF",
    )
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-CONF",
        revision_id="REV-CONF",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
    )
    other_account = AccountId("ACC-CLS-CONF-OTHER")
    other_org = _org("ORG-CLS-CONF-OTHER")
    other_membership = _membership(other_org, other_account, "OM-CLS-CONF-OTHER")
    create_market_episode(
        api_conn,
        market_episode=MarketEpisode(
            id=MarketEpisodeId("ME-CLS-CONF-OTHER"), physical_boat_id=PhysicalBoatId("PB-CLS-CONF")
        ),
    )
    create_native_listing(
        api_conn,
        account_id=other_account,
        candidate_organization=other_org,
        membership=other_membership,
        listing=NativeListing(
            id=NativeListingId("NL-CLS-CONF-OTHER"),
            market_episode_id=MarketEpisodeId("ME-CLS-CONF-OTHER"),
        ),
    )
    _write_draft_claim(
        api_conn,
        account=other_account,
        org=other_org,
        membership=other_membership,
        listing_id="NL-CLS-CONF-OTHER",
        revision_id="REV-CONF-OTHER",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")),
    )
    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert outcome.confirmed_matches == ()
    assert outcome.insufficient_data_count == 1


def test_extreme_precision_decimal_threshold_no_float_drift(api_conn: Any) -> None:
    """Finding 2: a Decimal threshold that would misround under an
    intermediate float conversion must still compare exactly."""
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-PREC",
        physical_boat_id="PB-CLS-PREC",
        market_episode_id="ME-CLS-PREC",
    )
    exact_draft = Decimal("1.10000000000000000000001")
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-PREC",
        revision_id="REV-PREC",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=exact_draft),
    )
    outcome = evaluate_draft_max_requirement(api_conn, exact_draft)
    assert {m.native_listing_id.value for m in outcome.confirmed_matches} == {"NL-CLS-PREC"}
    assert outcome.confirmed_matches[0].resolved_draft_m == exact_draft


# ---------------------------------------------------------------------------
# Finding 5: single-query snapshot consistency
# ---------------------------------------------------------------------------


def test_classification_reads_current_observations_exactly_once_per_candidate(
    api_conn: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The publisher's own current claim and the cross-Organization
    contradiction-guard observation set must be resolved from exactly one
    call to `list_current_draft_observations_for_physical_boat` per
    candidate -- one SQL statement, therefore one consistent PostgreSQL MVCC
    snapshot for both, rather than two separate queries that a concurrent
    claim revision could tear between."""
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-SNAP",
        physical_boat_id="PB-CLS-SNAP",
        market_episode_id="ME-CLS-SNAP",
    )
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-SNAP",
        revision_id="REV-SNAP",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
    )

    call_count = 0
    real_fn = physical_boat_claims_module.list_current_draft_observations_for_physical_boat

    def _counting_wrapper(conn: Any, physical_boat_id: Any) -> Any:
        nonlocal call_count
        call_count += 1
        return real_fn(conn, physical_boat_id)

    monkeypatch.setattr(
        inventory_search_module,
        "list_current_draft_observations_for_physical_boat",
        _counting_wrapper,
    )

    outcome = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    assert outcome.confirmed_match_count == 1
    assert call_count == 1, (
        "expected exactly one snapshot-consistent read per candidate; "
        f"got {call_count} calls, which would allow a torn read across separate statements"
    )


def test_sequential_revisions_are_never_mixed_old_and_new(api_conn: Any) -> None:
    """Not a true concurrency race (PostgreSQL's own single-statement MVCC
    snapshot guarantee, exercised by the single-query fix, is what actually
    prevents tearing within one evaluation) -- this proves the weaker but
    directly testable sequential property: consecutive evaluations across a
    claim revision never combine an old publisher value with a new
    observation set or vice versa."""
    listing = _make_active_listing(
        api_conn,
        listing_id="NL-CLS-SEQ",
        physical_boat_id="PB-CLS-SEQ",
        market_episode_id="ME-CLS-SEQ",
    )
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-SEQ",
        revision_id="REV-SEQ-1",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
    )
    api_conn.commit()
    first = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    api_conn.commit()  # leave conn IDLE before the next write requires it
    assert {m.native_listing_id.value for m in first.confirmed_matches} == {"NL-CLS-SEQ"}
    assert first.confirmed_matches[0].resolved_draft_m == Decimal("1.40")

    # Revise the publisher's own claim to a now-non-matching value.
    _write_draft_claim(
        api_conn,
        account=listing[0],
        org=listing[1],
        membership=listing[2],
        listing_id="NL-CLS-SEQ",
        revision_id="REV-SEQ-2",
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.90")),
        expected_current_revision_id=PhysicalBoatClaimRevisionId("REV-SEQ-1"),
    )
    api_conn.commit()
    second = evaluate_draft_max_requirement(api_conn, Decimal("1.6"))
    # The new evaluation must reflect ONLY the new value -- never a mix of
    # the old CONFIRMED_MATCH classification with the new resolved value,
    # or vice versa.
    assert second.confirmed_matches == ()
    assert second.confirmed_non_match_count == 1
