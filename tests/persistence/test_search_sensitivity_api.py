"""PostgreSQL + real HTTP tests for the SLICE-0057 buyer-requirement-
sensitivity `/api/search/{locale}/sensitivity` HTTP contract.

Mirrors `tests/persistence/test_inventory_search_keel_api.py`'s real-database
fixture style. Two BoatDesigns (one FIN-keeled, one TWIN_KEEL-keeled, both
draft_max_m=1.30) back three ACTIVE listings so the delta tests can exercise
a genuine same-total/different-membership case through a real
`keel_configuration` swap (contract §8/§16 point 5): the FIN design's own
resolved `keel_type` (`fin`) does not equal a `TWIN_KEEL` query's requested
value and vice versa, so changing `keel_configuration` from `FIN` to
`TWIN_KEEL` swaps which single listing is confirmed rather than merely
adding/removing one from a shared pool -- proving
`newly_confirmed_match_count`/`no_longer_confirmed_match_count` are real set
differences, not `max(0, alternative_total - current_total)` arithmetic
(contract §8's hard requirement).

Independent review Finding 4 (2026-09-19): a resolved-but-different keel
value does NOT classify as design-level `CONFIRMED_NON_MATCH` in this
repository today -- `hullq.search.boat_design_field_bridge.
build_boat_design_configuration_set` always builds an incomplete
configuration space (`configuration_space_complete=False`), and
`hullq.search.configuration_engine.evaluate_design_configuration_set` only
returns `CONFIRMED_NON_MATCH` when the configuration space is complete AND
every configuration is a confirmed FALSE. A design-level FALSE with an
incomplete configuration space therefore falls into `INSUFFICIENT_DATA`
instead (accepted, pre-existing SLICE-0051/0055 kernel behavior; SLICE-0057
does not change it -- see `_TWIN_DESIGN_ID`'s own module-level comment in
`scripts/inspect_first_native_inventory_search.py` for the same correction).
The same-total/different-membership *confirmed*-set proof below remains
unaffected by this correction; only the insufficient-data explanation
changes.

Independent review amendment (2026-09-19, Findings 2/3) adds:

- a real-FastAPI proof (not merely a TypeScript-mocked one) that a present-
  but-empty `current_keel_configuration` value is rejected with 400 rather
  than silently narrowed to a draft-only comparison (Finding 2);
- malformed/unknown request-body-shape 400 coverage, an all-five-locales
  acceptance check, and a genuine backend/database-failure 5xx proof using a
  real `TestClient(..., raise_server_exceptions=False)` boundary against an
  unreachable database (Finding 3, contract §11/§17);
- a direct real-PostgreSQL proof that the current/alternative pair shares
  one coherent `REPEATABLE READ` snapshot -- a concurrent write committed by
  a second connection between the two halves must never be observed by the
  alternative evaluation (Finding 3, contract §7);
- a direct proof that the sensitivity operation writes no HullQ persistence
  state (Finding 3, contract §5 "persists nothing").
"""

from __future__ import annotations

import json
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from fastapi.testclient import TestClient

from hullq.application import search_sensitivity as search_sensitivity_module
from hullq.application.search_sensitivity import (
    SensitivityOutcomeKind,
    evaluate_requirement_sensitivity,
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
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BuildYearClaim,
    DraftClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
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
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import write_physical_boat_claim_revision
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

# ---------------------------------------------------------------------------
# Disposable-schema fixture (mirrors test_inventory_search_keel_api.py)
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
    schema_name = f"hullq_s0057api_{uuid.uuid4().hex[:16]}"
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

_FIN_DESIGN_ID = "BD-0057-SENS-FIN"
_TWIN_DESIGN_ID = "BD-0057-SENS-TWIN"
_FIN_LISTING_ID = "NL-0057-SENS-FIN"
_TWIN_LISTING_ID = "NL-0057-SENS-TWIN"
_INSUFFICIENT_LISTING_ID = "NL-0057-SENS-INSUFFICIENT"


def _insert_boat_design(conn: Any, design_id: str, *, keel_type: str) -> None:
    model_id = f"BM-{design_id}"
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {"dimensions": {"draft_max_m": 1.30}, "appendages": {"keel_type": keel_type}}
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, "[]", "[]", "{}", "1" * 64],
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


def _make_listing(
    conn: Any,
    *,
    listing_id: str,
    design_id: str,
    draft: DraftClaim | None,
    keel: KeelConfigurationClaim | None,
) -> None:
    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")
    physical_boat_id = f"PB-{listing_id}"
    market_episode_id = f"ME-{listing_id}"

    create_physical_boat(
        conn,
        physical_boat=PhysicalBoat(
            id=PhysicalBoatId(physical_boat_id), boat_design_ref=BoatDesignRef(design_id)
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
            model_designation_claim="Oceanis 30.1",
            build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
            draft=draft,
            keel_configuration=keel,
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


@pytest.fixture()
def seeded(api_conn: Any) -> dict[str, Any]:
    """Two design-eligible ACTIVE listings (FIN keel / TWIN_KEEL keel, both
    1.40 m concrete draft on a 1.30 m-baseline design) plus one ACTIVE
    listing (on the FIN design) whose concrete draft AND keel claims are both
    omitted -- INSUFFICIENT_DATA for a `draft_max`-only or `keel_configuration
    =FIN`-only query (its own design is eligible but its concrete claim is
    missing), and *also* INSUFFICIENT_DATA (never a confirmed match) for
    `keel_configuration=TWIN_KEEL`: its FIN design resolves `keel_type=fin`,
    which is a confirmed mismatch against `TWIN_KEEL` -- this repository's
    design/configuration bridge always builds an incomplete configuration
    space, so a design-level mismatch alone lands in INSUFFICIENT_DATA,
    never CONFIRMED_NON_MATCH (this module's docstring, independent review
    Finding 4)."""
    _insert_boat_design(api_conn, _FIN_DESIGN_ID, keel_type="fin")
    _insert_boat_design(api_conn, _TWIN_DESIGN_ID, keel_type="twin")

    for design_id, resolution_prefix in (
        (_FIN_DESIGN_ID, "FIN"),
        (_TWIN_DESIGN_ID, "TWIN"),
    ):
        admit_resolved_draft_max(
            api_conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer=DRAFT_MAX_FIELD_POINTER,
            value=Decimal("1.30"),
            resolution_id=f"FR-0057-SENS-{resolution_prefix}-DRAFT",
        )
        admit_resolved_categorical_field(
            api_conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer=KEEL_TYPE_FIELD_POINTER,
            value="fin" if resolution_prefix == "FIN" else "twin",
            resolution_id=f"FR-0057-SENS-{resolution_prefix}-KEEL",
            fetch_canonical_value=lookup_keel_canonical_value,
        )

    _make_listing(
        api_conn,
        listing_id=_FIN_LISTING_ID,
        design_id=_FIN_DESIGN_ID,
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
        keel=KeelConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.FIN
        ),
    )
    _make_listing(
        api_conn,
        listing_id=_TWIN_LISTING_ID,
        design_id=_TWIN_DESIGN_ID,
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.40")),
        keel=KeelConfigurationClaim(
            assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration.TWIN_KEEL
        ),
    )
    _make_listing(
        api_conn,
        listing_id=_INSUFFICIENT_LISTING_ID,
        design_id=_FIN_DESIGN_ID,
        draft=None,
        keel=None,
    )
    return {}


def _post_sensitivity(
    client: TestClient,
    *,
    locale: str = "en",
    current: dict[str, str],
    criterion: str,
    value: str,
) -> Any:
    return client.post(
        f"/api/search/{locale}/sensitivity",
        json={"current": current, "change": {"criterion": criterion, "value": value}},
    )


# ---------------------------------------------------------------------------
# HTTP contract tests
# ---------------------------------------------------------------------------


def test_draft_max_sensitivity_changes_confirmed_set(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = _post_sensitivity(
        client, current={"draft_max": "1.6"}, criterion="draft_max", value="1.35"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_requirement"] == {"draft_max": "1.6"}
    assert body["alternative_requirement"] == {"draft_max": "1.35"}
    assert body["changed_criterion"] == "draft_max"
    # FIN (1.40 m) and TWIN (1.40 m) both confirm at 1.6 m but not at 1.35 m;
    # the omitted-draft listing stays insufficient at both thresholds.
    assert body["current_confirmed_match_count"] == 2
    assert body["alternative_confirmed_match_count"] == 0
    assert body["newly_confirmed_match_count"] == 0
    assert body["no_longer_confirmed_match_count"] == 2
    assert body["current_insufficient_data_count"] == 1
    assert body["alternative_insufficient_data_count"] == 1
    assert body["alternative_search_path"] == "/en/search?draft_max=1.35"


def test_keel_configuration_sensitivity_is_same_total_different_membership(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    # Contract §8/§16 point 5 hard requirement: newly_confirmed_match_count
    # != max(0, alternative_total - current_total). Here totals are equal
    # (1 and 1) while membership is completely different.
    response = _post_sensitivity(
        client,
        current={"keel_configuration": "FIN"},
        criterion="keel_configuration",
        value="TWIN_KEEL",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_requirement"] == {"keel_configuration": "FIN"}
    assert body["alternative_requirement"] == {"keel_configuration": "TWIN_KEEL"}
    assert body["current_confirmed_match_count"] == 1
    assert body["alternative_confirmed_match_count"] == 1
    assert body["newly_confirmed_match_count"] == 1
    assert body["no_longer_confirmed_match_count"] == 1
    assert body["alternative_search_path"] == "/en/search?keel_configuration=TWIN_KEEL"
    # Independent review Finding 4: the resolved-but-different-keel design
    # (TWIN under the current FIN query, FIN under the alternative TWIN_KEEL
    # query) lands in insufficient-data, never a silent non-match omitted
    # from every surface -- alongside the listing whose concrete claims are
    # entirely missing. Both counts equal 2 under either query.
    assert body["current_insufficient_data_count"] == 2
    assert body["alternative_insufficient_data_count"] == 2


def test_mixed_search_can_change_keel_while_preserving_draft(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = _post_sensitivity(
        client,
        current={"draft_max": "1.6", "keel_configuration": "FIN"},
        criterion="keel_configuration",
        value="TWIN_KEEL",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["current_requirement"] == {"draft_max": "1.6", "keel_configuration": "FIN"}
    assert body["alternative_requirement"] == {
        "draft_max": "1.6",
        "keel_configuration": "TWIN_KEEL",
    }
    assert body["current_confirmed_match_count"] == 1
    assert body["alternative_confirmed_match_count"] == 1
    assert (
        body["alternative_search_path"] == "/en/search?draft_max=1.6&keel_configuration=TWIN_KEEL"
    )


def test_mixed_search_can_change_draft_while_preserving_keel(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = _post_sensitivity(
        client,
        current={"draft_max": "1.6", "keel_configuration": "FIN"},
        criterion="draft_max",
        value="1.35",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["alternative_requirement"] == {"draft_max": "1.35", "keel_configuration": "FIN"}
    assert body["current_confirmed_match_count"] == 1
    assert body["alternative_confirmed_match_count"] == 0
    assert body["no_longer_confirmed_match_count"] == 1


def test_same_value_proposal_is_zero_delta(client: TestClient, seeded: dict[str, Any]) -> None:
    response = _post_sensitivity(
        client, current={"draft_max": "1.6"}, criterion="draft_max", value="1.60"
    )
    assert response.status_code == 200
    body = response.json()
    assert body["alternative_requirement"] == {"draft_max": "1.6"}
    assert body["current_confirmed_match_count"] == body["alternative_confirmed_match_count"]
    assert body["newly_confirmed_match_count"] == 0
    assert body["no_longer_confirmed_match_count"] == 0


def test_changed_criterion_not_active_is_400(client: TestClient, seeded: dict[str, Any]) -> None:
    response = _post_sensitivity(
        client, current={"draft_max": "1.6"}, criterion="keel_configuration", value="FIN"
    )
    assert response.status_code == 400
    body = response.json()
    assert body["error"] == "invalid_sensitivity_request"


def test_malformed_draft_replacement_is_400(client: TestClient, seeded: dict[str, Any]) -> None:
    response = _post_sensitivity(
        client, current={"draft_max": "1.6"}, criterion="draft_max", value="1e0"
    )
    assert response.status_code == 400


def test_unsupported_keel_replacement_is_400(client: TestClient, seeded: dict[str, Any]) -> None:
    response = _post_sensitivity(
        client,
        current={"keel_configuration": "FIN"},
        criterion="keel_configuration",
        value="LONG_KEEL",
    )
    assert response.status_code == 400


def test_unsupported_locale_is_404(client: TestClient, seeded: dict[str, Any]) -> None:
    response = _post_sensitivity(
        client, locale="it", current={"draft_max": "1.6"}, criterion="draft_max", value="1.7"
    )
    assert response.status_code == 404


def test_response_is_noindex(client: TestClient, seeded: dict[str, Any]) -> None:
    response = _post_sensitivity(
        client, current={"draft_max": "1.6"}, criterion="draft_max", value="1.35"
    )
    assert response.headers.get("x-robots-tag") == "noindex"


# ---------------------------------------------------------------------------
# Independent review amendment (2026-09-19)
# ---------------------------------------------------------------------------


def test_tampered_present_empty_current_value_is_400_not_narrowed(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    """Finding 2: a *present* but empty `current_keel_configuration` value
    (tampered/malformed current state -- the real Search page never renders
    a hidden field with an empty value for an active criterion) must be
    rejected with 400 by the real FastAPI boundary, never silently
    reinterpreted as "keel_configuration inactive" and evaluated as a
    narrower draft-only comparison."""
    response = client.post(
        "/api/search/en/sensitivity",
        json={
            "current": {"draft_max": "1.6", "keel_configuration": ""},
            "change": {"criterion": "draft_max", "value": "1.35"},
        },
    )
    assert response.status_code == 400
    assert response.json()["error"] == "invalid_sensitivity_request"


def test_malformed_body_not_an_object_is_400(client: TestClient, seeded: dict[str, Any]) -> None:
    """Finding 3: malformed/unknown request-body shape -> 400 (contract §11)."""
    response = client.post("/api/search/en/sensitivity", json=["not", "an", "object"])
    assert response.status_code == 400


def test_malformed_body_missing_change_key_is_400(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.post("/api/search/en/sensitivity", json={"current": {"draft_max": "1.6"}})
    assert response.status_code == 400


def test_malformed_body_current_not_an_object_is_400(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.post(
        "/api/search/en/sensitivity",
        json={"current": "not-an-object", "change": {"criterion": "draft_max", "value": "1.7"}},
    )
    assert response.status_code == 400


def test_malformed_body_unknown_top_level_key_is_400(
    client: TestClient, seeded: dict[str, Any]
) -> None:
    response = client.post(
        "/api/search/en/sensitivity",
        json={
            "current": {"draft_max": "1.6"},
            "change": {"criterion": "draft_max", "value": "1.7"},
            "extra": 1,
        },
    )
    assert response.status_code == 400


@pytest.mark.parametrize("locale", ["en", "de", "fr", "pt", "es"])
def test_all_five_supported_locales_are_accepted(
    client: TestClient, seeded: dict[str, Any], locale: str
) -> None:
    """Finding 3: every accepted public locale remains accepted by the
    sensitivity endpoint (contract §5/§17)."""
    response = _post_sensitivity(
        client,
        locale=locale,
        current={"keel_configuration": "FIN"},
        criterion="keel_configuration",
        value="TWIN_KEEL",
    )
    assert response.status_code == 200
    body = response.json()
    assert body["locale"] == locale
    assert body["alternative_search_path"] == f"/{locale}/search?keel_configuration=TWIN_KEEL"


def test_backend_database_failure_is_5xx_never_400_or_zero_result(
    seeded: dict[str, Any],
) -> None:
    """Finding 3: a genuine backend/database failure must surface as a real
    5xx response through the actual FastAPI route -- not merely something a
    browser-side TypeScript mock simulates. Builds a *separate* app instance
    pointed at an unreachable database (port 1: reserved, nothing listens
    there, a guaranteed immediate connection failure -- mirrors the existing
    web-layer test precedent for "an unreachable backend"), then uses
    `raise_server_exceptions=False` so Starlette's real unhandled-exception
    ServerErrorMiddleware response is observed as an actual HTTP response
    rather than re-raised in-process."""
    from hullq.api.app import create_app

    unreachable_app = create_app(
        database_url="postgresql://hullq_test:hullq_test@127.0.0.1:1/hullq_test",
        preview_signing_secret=_SECRET,
    )
    unreachable_client = TestClient(unreachable_app, raise_server_exceptions=False)
    response = _post_sensitivity(
        unreachable_client, current={"draft_max": "1.6"}, criterion="draft_max", value="1.7"
    )
    assert response.status_code >= 500
    assert response.status_code != 400
    # Never a fabricated empty/zero sensitivity result either.
    try:
        body = response.json()
    except ValueError:
        body = None
    if isinstance(body, dict):
        assert "current_confirmed_match_count" not in body


def test_current_and_alternative_share_one_repeatable_read_snapshot(
    api_conn: Any,
    api_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Finding 3 (contract §7): the current and alternative evaluation must
    run inside one coherent `REPEATABLE READ` snapshot, not two independent
    `READ COMMITTED` reads. A same-value proposal (current == alternative)
    is a deterministic zero delta *only if* both halves observe the exact
    same database state -- this test interposes a real committed write from
    a second connection between the current and alternative evaluation (by
    monkeypatching the one shared dispatch point,
    `hullq.application.search_read.evaluate_requirement_search_outcome`, as
    imported into `hullq.application.search_sensitivity`'s own namespace)
    and asserts the delta still comes out exactly zero -- proving the
    alternative evaluation, though it runs strictly *after* that concurrent
    commit, never observes it. A follow-up plain evaluation on a fresh
    connection then confirms the concurrent write really did commit (so
    this is not vacuously true because the write silently failed)."""
    design_id = "BD-0057-COHERENCE"
    listing_id = "NL-0057-COHERENCE"
    _insert_boat_design(api_conn, design_id, keel_type="fin")
    # _insert_boat_design always writes a fixed 1.30 m baseline draft --
    # match it exactly so write_field_resolution's Finding-7
    # canonical-consistency enforcement accepts this resolution.
    admit_resolved_draft_max(
        api_conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=Decimal("1.30"),
        resolution_id="FR-0057-COHERENCE-DRAFT",
    )
    _make_listing(
        api_conn,
        listing_id=listing_id,
        design_id=design_id,
        draft=DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("1.10")),
        keel=None,
    )

    account = AccountId(f"ACC-{listing_id}")
    org = _org(f"ORG-{listing_id}")
    membership = _membership(org, account, f"OM-{listing_id}")

    second_conn = psycopg.connect(api_url)
    original = search_sensitivity_module.evaluate_requirement_search_outcome
    calls: list[int] = []

    def _patched(conn: Any, **kwargs: Any) -> Any:
        calls.append(1)
        result = original(conn, **kwargs)
        if len(calls) == 1:
            # Runs after CURRENT is evaluated but before ALTERNATIVE is --
            # a real committed concurrent write via an independent
            # connection, exactly like a different buyer/broker action
            # landing mid-comparison.
            write_physical_boat_claim_revision(
                second_conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId(listing_id),
                revision_id=PhysicalBoatClaimRevisionId(f"PBCREV2-{listing_id}"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId(f"PBCREV-{listing_id}"),
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    draft=DraftClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("2.00")
                    ),
                    keel_configuration=None,
                ),
            )
        return result

    monkeypatch.setattr(search_sensitivity_module, "evaluate_requirement_search_outcome", _patched)

    try:
        outcome = evaluate_requirement_sensitivity(
            api_conn,
            locale="en",
            current={"draft_max": "1.6"},
            changed_criterion="draft_max",
            changed_value="1.6",
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
        )
    finally:
        second_conn.close()

    assert len(calls) == 2
    assert outcome.kind is SensitivityOutcomeKind.OK
    assert outcome.result is not None
    # If the alternative evaluation had observed the concurrent write, this
    # listing's draft would read 2.00 m > 1.6 m -- no longer confirmed --
    # producing a nonzero delta despite an identical current/alternative
    # requirement. REPEATABLE READ must hide it: the delta must stay zero.
    assert (
        outcome.result.current_confirmed_match_count
        == outcome.result.alternative_confirmed_match_count
    )
    assert outcome.result.newly_confirmed_match_count == 0
    assert outcome.result.no_longer_confirmed_match_count == 0

    # Vacuous-test guard: a fresh connection opened *after* the sensitivity
    # call must see the concurrent write actually landed.
    fresh_conn = psycopg.connect(api_url)
    try:
        fresh_outcome = evaluate_requirement_sensitivity(
            fresh_conn,
            locale="en",
            current={"draft_max": "1.6"},
            changed_criterion="draft_max",
            changed_value="1.6",
            as_of=datetime(2026, 1, 1, tzinfo=UTC),
        )
    finally:
        fresh_conn.close()
    assert fresh_outcome.result is not None
    assert fresh_outcome.result.current_confirmed_match_count == 0


def test_sensitivity_writes_no_persistence_state(
    client: TestClient, seeded: dict[str, Any], api_conn: Any
) -> None:
    """Finding 3 (contract §5: "persists nothing"): the sensitivity
    operation is read-only computation. Row counts across every table this
    read path touches must be identical before and after a real sensitivity
    request -- proving no BuyerRequirements/Saved Search/Monitor/Shortlist
    or any other durable state is created or mutated (contract §14)."""

    def _row_counts() -> tuple[int, int, int, int]:
        with api_conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM native_listings")
            native_listings = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM physical_boat_claim_revisions")
            claim_revisions = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM native_listing_offer_revisions")
            offer_revisions = cur.fetchone()[0]
            cur.execute("SELECT count(*) FROM field_resolutions")
            field_resolutions = cur.fetchone()[0]
        api_conn.commit()
        return native_listings, claim_revisions, offer_revisions, field_resolutions

    before = _row_counts()
    response = _post_sensitivity(
        client, current={"draft_max": "1.6"}, criterion="draft_max", value="1.35"
    )
    assert response.status_code == 200
    after = _row_counts()
    assert before == after
