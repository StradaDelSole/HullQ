"""FastAPI integration tests for SLICE-0095 broker pre-publication Power
technical Search-fit preview
(`hullq.application.power_broker_search_fit`).

Mirrors `test_broker_search_fit_api.py`'s fixture/session-minting pattern
for the structurally separate Power preview.

Covers the slice's acceptance criteria: Organization/MFA/PUBLISHER
authorization and non-enumeration; bounded `power_drive`/
`power_engine_count` scenario validation; design-unresolved publisher-
claim-only truth (including a genuine claim-only `CONFIRMED_MATCH` with no
BoatDesign, explicit `source_basis=PUBLISHER_CLAIM`, missing/explicit-SAIL
category never producing a positive); design-linked truth reusing the
accepted SLICE-0093/0094 configuration/snapshot kernel; a dangling
BoatDesignRef failing closed as a service/integrity fault; `NOT_PREVIEWABLE`
for a non-DRAFT listing; zero writes; and non-regression of the original
Sail broker preview and the public Power Buyer Search.
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
from starlette.testclient import TestClient

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.market_identity import (
    BoatDesignRef,
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
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    PowerDriveConfiguration,
    PowerDriveConfigurationClaim,
    PowerEngineCountClaim,
    VesselCategory,
    VesselCategoryClaim,
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
from hullq.persistence.market_episode import create_market_episode, fetch_market_episode
from hullq.persistence.native_listing import create_native_listing, fetch_native_listing
from hullq.persistence.native_listing_lifecycle import fetch_lifecycle_state
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)
from hullq.search.power_drive_design_bridge import lookup_power_drive_canonical_value
from hullq.search.power_engine_count_design_bridge import lookup_power_engine_count_canonical_value
from hullq.security.session_token import mint_session_token

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"
VA = AssertionKind.VALUE_ASSERTION


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
    schema_name = f"hullq_s0095sf_{uuid.uuid4().hex[:16]}"
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
def client(api_url: str, monkeypatch: pytest.MonkeyPatch) -> Generator[TestClient]:
    import os

    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _ensure_account(conn: Any, account_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )


def _session_cookie(account_id: str, *, mfa: bool = True) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=mfa,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=_SECRET)
    return minted.token


def _log_in(client: TestClient, account_id: str, *, mfa: bool = True) -> None:
    client.cookies.set("hullq_session", _session_cookie(account_id, mfa=mfa), domain="api.test")


def _seed_org_and_membership(
    api_url: str,
    *,
    org_id: str,
    account_id: str,
    membership_id: str,
    roles: frozenset[MembershipRole] = frozenset({MembershipRole.PUBLISHER}),
    state: MembershipState = MembershipState.ACTIVE,
) -> None:
    conn = psycopg.connect(api_url)
    try:
        _ensure_account(conn, account_id)
        seed_marketplace_organization(
            conn,
            MarketplaceOrganization(
                id=MarketplaceOrganizationId(org_id),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            ),
        )
        seed_organization_membership(
            conn,
            OrganizationMembership(
                id=OrganizationMembershipId(membership_id),
                account_id=AccountId(account_id),
                organization_id=MarketplaceOrganizationId(org_id),
                roles=roles,
                state=state,
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _insert_boat_design(
    conn: Any, design_id: str, model_id: str, *, drive_type: str, engine_count: int | None
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {"propulsion": {"drive_type": drive_type, "engine_count": engine_count}}
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, '[]'::jsonb, "
            "'[]'::jsonb, '{}'::jsonb, %s)",
            [design_id, model_id, baseline_json, "1" * 64],
        )
    conn.commit()


def _admit_design_drive_and_count(
    conn: Any, design_id: str, *, drive_type: str | None, engine_count: int | None
) -> None:
    if drive_type is not None:
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer="/baseline/propulsion/drive_type",
            value=drive_type,
            resolution_id=f"FR-PWRDRV-{design_id}",
            fetch_canonical_value=lookup_power_drive_canonical_value,
        )
    if engine_count is not None:
        admit_resolved_draft_max(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer="/baseline/propulsion/engine_count",
            value=Decimal(engine_count),
            resolution_id=f"FR-PWRCNT-{design_id}",
            fetch_canonical_value=lookup_power_engine_count_canonical_value,
        )


def _create_draft_listing(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
    boat_design_id: str | None = None,
) -> None:
    """The exact shape SLICE-0067 promotion produces: a fresh,
    lifecycle-DRAFT NativeListing -> MarketEpisode -> PhysicalBoat chain,
    optionally with an already-linked `boat_design_ref`."""
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(membership_id),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        create_physical_boat(
            conn,
            physical_boat=PhysicalBoat(
                id=PhysicalBoatId(physical_boat_id),
                boat_design_ref=(
                    BoatDesignRef(boat_design_id) if boat_design_id is not None else None
                ),
            ),
        )
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
        conn.commit()
    finally:
        conn.close()


def _write_claim(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    revision_id: str,
    vessel_category: VesselCategoryClaim | None = None,
    power_drive_configuration: PowerDriveConfigurationClaim | None = None,
    power_engine_count: PowerEngineCountClaim | None = None,
) -> None:
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-{org_id}"),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        listing_record = fetch_native_listing(conn, NativeListingId(listing_id))
        assert listing_record is not None
        assert listing_record.listing.market_episode_id is not None
        episode_record = fetch_market_episode(conn, listing_record.listing.market_episode_id)
        assert episode_record is not None
        existing = fetch_current_physical_boat_claim(
            conn, episode_record.market_episode.physical_boat_id, org.id
        )
        expected_current_revision_id = existing.revision_id if existing is not None else None
        conn.commit()
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
                model_designation_claim="Swift Trawler 35",
                build_year=BuildYearClaim(assertion_kind=VA, value=2020),
                vessel_category=vessel_category,
                power_drive_configuration=power_drive_configuration,
                power_engine_count=power_engine_count,
            ),
        )
        assert result.status.value in ("created", "revised"), result
    finally:
        conn.close()


def _power_search_fit_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/power-search-fit"


def _capture_write_fingerprint(
    api_url: str, *, native_listing_id: str, physical_boat_id: str, organization_id: str
) -> dict[str, Any]:
    conn = psycopg.connect(api_url)
    try:
        lifecycle = fetch_lifecycle_state(conn, NativeListingId(native_listing_id))
        claim = fetch_current_physical_boat_claim(
            conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(organization_id)
        )
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM native_listing_publication_transitions")
            transition_count = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM physical_boat_claim_revisions WHERE physical_boat_id = %s",
                [physical_boat_id],
            )
            claim_revision_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM field_resolutions")
            field_resolution_count = cur.fetchone()[0]
    finally:
        conn.close()
    return {
        "lifecycle": lifecycle,
        "claim_revision_id": claim.revision_id if claim is not None else None,
        "transition_count": transition_count,
        "claim_revision_count": claim_revision_count,
        "field_resolution_count": field_resolution_count,
    }


# ---------------------------------------------------------------------------
# Authorization / privacy / non-enumeration
# ---------------------------------------------------------------------------


class TestPowerSearchFitAuthorization:
    def test_unauthenticated_is_blocked(self, client: TestClient) -> None:
        response = client.get(
            _power_search_fit_path("ORG-X", "NL-X"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-PSF-NEVER")
        response = client.get(
            _power_search_fit_path("ORG-PSF-NEVER", "NL-X"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 404

    def test_foreign_listing_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PSF-A", account_id="ACC-PSF-A", membership_id="OM-PSF-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-PSF-B", account_id="ACC-PSF-B", membership_id="OM-PSF-B"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-FOREIGN",
            org_id="ORG-PSF-B",
            account_id="ACC-PSF-B",
            membership_id="OM-PSF-B",
            physical_boat_id="PB-PSF-FOREIGN",
            market_episode_id="ME-PSF-FOREIGN",
        )
        _log_in(client, "ACC-PSF-A")
        response = client.get(
            _power_search_fit_path("ORG-PSF-A", "NL-PSF-FOREIGN"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 404

    def test_mfa_required_blocks_read(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PSF-MFA", account_id="ACC-PSF-MFA", membership_id="OM-PSF-MFA"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-MFA",
            org_id="ORG-PSF-MFA",
            account_id="ACC-PSF-MFA",
            membership_id="OM-PSF-MFA",
            physical_boat_id="PB-PSF-MFA",
            market_episode_id="ME-PSF-MFA",
        )
        _log_in(client, "ACC-PSF-MFA", mfa=False)
        response = client.get(
            _power_search_fit_path("ORG-PSF-MFA", "NL-PSF-MFA"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 403
        assert response.json()["error"] == "mfa_required"

    def test_publisher_role_required(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-NOPUB",
            account_id="ACC-PSF-NOPUB",
            membership_id="OM-PSF-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-NOPUB",
            org_id="ORG-PSF-NOPUB",
            account_id="ACC-PSF-NOPUB",
            membership_id="OM-PSF-NOPUB",
            physical_boat_id="PB-PSF-NOPUB",
            market_episode_id="ME-PSF-NOPUB",
        )
        _log_in(client, "ACC-PSF-NOPUB")
        response = client.get(
            _power_search_fit_path("ORG-PSF-NOPUB", "NL-PSF-NOPUB"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 403
        assert response.json()["reason"] == "PUBLISHER_ROLE_REQUIRED"


# ---------------------------------------------------------------------------
# Scenario validation
# ---------------------------------------------------------------------------


class TestPowerSearchFitScenarioValidation:
    def _setup(self, api_url: str, client: TestClient, suffix: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id=f"ORG-PSF-{suffix}",
            account_id=f"ACC-PSF-{suffix}",
            membership_id=f"OM-PSF-{suffix}",
        )
        _create_draft_listing(
            api_url,
            listing_id=f"NL-PSF-{suffix}",
            org_id=f"ORG-PSF-{suffix}",
            account_id=f"ACC-PSF-{suffix}",
            membership_id=f"OM-PSF-{suffix}",
            physical_boat_id=f"PB-PSF-{suffix}",
            market_episode_id=f"ME-PSF-{suffix}",
        )
        _log_in(client, f"ACC-PSF-{suffix}")

    def test_empty_scenario_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "EMPTY")
        response = client.get(_power_search_fit_path("ORG-PSF-EMPTY", "NL-PSF-EMPTY"))
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_scenario"

    def test_unsupported_drive_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "BADDRV")
        response = client.get(
            _power_search_fit_path("ORG-PSF-BADDRV", "NL-PSF-BADDRV"),
            params={"power_drive": "MIXED"},
        )
        assert response.status_code == 400

    def test_duplicate_power_drive_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "DUPE")
        response = client.get(
            _power_search_fit_path("ORG-PSF-DUPE", "NL-PSF-DUPE"),
            params=[("power_drive", "SHAFT"), ("power_drive", "SHAFT")],
        )
        assert response.status_code == 400

    def test_invalid_engine_count_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "CNT9")
        response = client.get(
            _power_search_fit_path("ORG-PSF-CNT9", "NL-PSF-CNT9"),
            params={"power_engine_count": "9"},
        )
        assert response.status_code == 400

    def test_unknown_parameter_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "UNKNOWNPARAM")
        response = client.get(
            _power_search_fit_path("ORG-PSF-UNKNOWNPARAM", "NL-PSF-UNKNOWNPARAM"),
            params={"displacement_kg": "5000"},
        )
        assert response.status_code == 400

    def test_sail_parameter_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "SAILPARAM")
        response = client.get(
            _power_search_fit_path("ORG-PSF-SAILPARAM", "NL-PSF-SAILPARAM"),
            params={"draft_max": "1.5"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Design-unresolved (claim-only) truth
# ---------------------------------------------------------------------------


class TestPowerSearchFitClaimOnlyTruth:
    def test_combined_match_with_no_boat_design(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-CLAIM",
            account_id="ACC-PSF-CLAIM",
            membership_id="OM-PSF-CLAIM",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-CLAIM",
            org_id="ORG-PSF-CLAIM",
            account_id="ACC-PSF-CLAIM",
            membership_id="OM-PSF-CLAIM",
            physical_boat_id="PB-PSF-CLAIM",
            market_episode_id="ME-PSF-CLAIM",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-CLAIM",
            org_id="ORG-PSF-CLAIM",
            account_id="ACC-PSF-CLAIM",
            revision_id="PBCREV-PSF-CLAIM",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
        )
        _log_in(client, "ACC-PSF-CLAIM")
        response = client.get(
            _power_search_fit_path("ORG-PSF-CLAIM", "NL-PSF-CLAIM"),
            params={"power_drive": "SHAFT", "power_engine_count": "2"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["domain"] == "POWER"
        assert body["result_class"] == "CONFIRMED_MATCH"
        assert body["blockers"] == []
        assert body["design_evaluation"] is None
        assert body["source_basis"] == "PUBLISHER_CLAIM"
        assert body["active_requirement"] == {"power_drive": "SHAFT", "power_engine_count": "2"}
        assert len(body["criterion_evidence"]) == 2

        # Mechanical invariant: lifecycle-DRAFT preview never leaks into the
        # accepted public technical Power Search while still DRAFT.
        public_search = client.get(
            "/api/search/en/power", params={"power_drive": "SHAFT", "power_engine_count": "2"}
        )
        assert public_search.status_code == 200
        assert public_search.json()["publisher_claim_match_count"] == 0

    def test_missing_power_category_is_insufficient_with_blocker(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-NOCAT",
            account_id="ACC-PSF-NOCAT",
            membership_id="OM-PSF-NOCAT",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-NOCAT",
            org_id="ORG-PSF-NOCAT",
            account_id="ACC-PSF-NOCAT",
            membership_id="OM-PSF-NOCAT",
            physical_boat_id="PB-PSF-NOCAT",
            market_episode_id="ME-PSF-NOCAT",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-NOCAT",
            org_id="ORG-PSF-NOCAT",
            account_id="ACC-PSF-NOCAT",
            revision_id="PBCREV-PSF-NOCAT",
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
        )
        _log_in(client, "ACC-PSF-NOCAT")
        response = client.get(
            _power_search_fit_path("ORG-PSF-NOCAT", "NL-PSF-NOCAT"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["POWER_CATEGORY_UNCONFIRMED"]
        assert body["criterion_evidence"] == []

    def test_sail_category_never_produces_positive(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-SAILCAT",
            account_id="ACC-PSF-SAILCAT",
            membership_id="OM-PSF-SAILCAT",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-SAILCAT",
            org_id="ORG-PSF-SAILCAT",
            account_id="ACC-PSF-SAILCAT",
            membership_id="OM-PSF-SAILCAT",
            physical_boat_id="PB-PSF-SAILCAT",
            market_episode_id="ME-PSF-SAILCAT",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-SAILCAT",
            org_id="ORG-PSF-SAILCAT",
            account_id="ACC-PSF-SAILCAT",
            revision_id="PBCREV-PSF-SAILCAT",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.SAIL),
        )
        _log_in(client, "ACC-PSF-SAILCAT")
        response = client.get(
            _power_search_fit_path("ORG-PSF-SAILCAT", "NL-PSF-SAILCAT"),
            params={"power_drive": "SHAFT"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_NON_MATCH"
        assert body["blockers"] == []
        assert body["vessel_category_exclusion"] == {
            "resolution": "SAIL",
            "reason": "CONCRETE_ONLY",
        }

    def test_engine_count_mismatch_is_confirmed_non_match(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-CNTNM",
            account_id="ACC-PSF-CNTNM",
            membership_id="OM-PSF-CNTNM",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-CNTNM",
            org_id="ORG-PSF-CNTNM",
            account_id="ACC-PSF-CNTNM",
            membership_id="OM-PSF-CNTNM",
            physical_boat_id="PB-PSF-CNTNM",
            market_episode_id="ME-PSF-CNTNM",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-CNTNM",
            org_id="ORG-PSF-CNTNM",
            account_id="ACC-PSF-CNTNM",
            revision_id="PBCREV-PSF-CNTNM",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=4),
        )
        _log_in(client, "ACC-PSF-CNTNM")
        response = client.get(
            _power_search_fit_path("ORG-PSF-CNTNM", "NL-PSF-CNTNM"),
            params={"power_engine_count": "2"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_NON_MATCH"
        assert body["blockers"] == []

    def test_mixed_drive_claim_is_insufficient_never_a_confirmed_exclusion(
        self, client: TestClient, api_url: str
    ) -> None:
        """Independent review amendment Finding D (round 1): a current
        `VALUE_ASSERTION(MIXED)` drive claim must never surface as a
        confirmed exclusion on the NEW private preview -- exercises
        `downgrade_mixed_non_match_to_insufficient_data` through the actual
        private evaluator, not only the already-accepted public buyer path
        (mirrors the contract's own words: "even if the vessel uses one of
        the types")."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-MIXED",
            account_id="ACC-PSF-MIXED",
            membership_id="OM-PSF-MIXED",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-MIXED",
            org_id="ORG-PSF-MIXED",
            account_id="ACC-PSF-MIXED",
            membership_id="OM-PSF-MIXED",
            physical_boat_id="PB-PSF-MIXED",
            market_episode_id="ME-PSF-MIXED",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-MIXED",
            org_id="ORG-PSF-MIXED",
            account_id="ACC-PSF-MIXED",
            revision_id="PBCREV-PSF-MIXED",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.MIXED
            ),
        )
        _log_in(client, "ACC-PSF-MIXED")
        response = client.get(
            _power_search_fit_path("ORG-PSF-MIXED", "NL-PSF-MIXED"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA", body
        assert body["blockers"] == ["POWER_DRIVE_UNCONFIRMED"]
        assert body["vessel_category_exclusion"] is None

    def test_cross_organization_drive_contradiction_is_insufficient(
        self, client: TestClient, api_url: str
    ) -> None:
        """Independent review amendment Finding D (round 1): source-
        conflicting current claims on the NEW private preview -- mirrors
        `test_broker_search_fit_api.py
        .test_cross_organization_contradiction_is_insufficient`'s identical
        fixture shape (a second claiming Organization through its own
        NativeListing -> new MarketEpisode -> the SAME shared PhysicalBoat),
        generalized to the Power drive field. A different claiming
        Organization's contradictory current drive claim for the same
        PhysicalBoat must never be silently treated as agreeing evidence."""
        _seed_org_and_membership(
            api_url, org_id="ORG-PSF-XORG", account_id="ACC-PSF-XORG", membership_id="OM-PSF-XORG"
        )
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-XORG-OTHER",
            account_id="ACC-PSF-XORG-OTHER",
            membership_id="OM-PSF-XORG-OTHER",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-XORG",
            org_id="ORG-PSF-XORG",
            account_id="ACC-PSF-XORG",
            membership_id="OM-PSF-XORG",
            physical_boat_id="PB-PSF-XORG",
            market_episode_id="ME-PSF-XORG",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-XORG",
            org_id="ORG-PSF-XORG",
            account_id="ACC-PSF-XORG",
            revision_id="PBCREV-PSF-XORG-A",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
        )
        # A different claiming Organization asserts a contradictory drive
        # for the SAME PhysicalBoat, through its own NativeListing -> new
        # MarketEpisode -> the shared PhysicalBoat -- the claim-write entry
        # point itself requires the candidate Organization to equal the
        # target listing's own publishing Organization, so it cannot be
        # written through NL-PSF-XORG directly.
        conn = psycopg.connect(api_url)
        try:
            other_account = AccountId("ACC-PSF-XORG-OTHER")
            other_org = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-PSF-XORG-OTHER"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            other_membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-PSF-XORG-OTHER"),
                account_id=other_account,
                organization_id=other_org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-PSF-XORG-OTHER"),
                    physical_boat_id=PhysicalBoatId("PB-PSF-XORG"),
                ),
            )
            create_native_listing(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                listing=NativeListing(
                    id=NativeListingId("NL-PSF-XORG-OTHER"),
                    market_episode_id=MarketEpisodeId("ME-PSF-XORG-OTHER"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        _write_claim(
            api_url,
            listing_id="NL-PSF-XORG-OTHER",
            org_id="ORG-PSF-XORG-OTHER",
            account_id="ACC-PSF-XORG-OTHER",
            revision_id="PBCREV-PSF-XORG-B",
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.OUTBOARD
            ),
        )
        _log_in(client, "ACC-PSF-XORG")
        response = client.get(
            _power_search_fit_path("ORG-PSF-XORG", "NL-PSF-XORG"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA", body
        assert body["blockers"] == ["POWER_DRIVE_UNCONFIRMED"]


# ---------------------------------------------------------------------------
# Design-linked truth
# ---------------------------------------------------------------------------


class TestPowerSearchFitDesignLinkedTruth:
    def test_design_linked_combined_match(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-DMATCH",
            account_id="ACC-PSF-DMATCH",
            membership_id="OM-PSF-DMATCH",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn, "BD-PSF-DMATCH", "BM-PSF-DMATCH", drive_type="shaft", engine_count=2
            )
            _admit_design_drive_and_count(conn, "BD-PSF-DMATCH", drive_type="shaft", engine_count=2)
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-DMATCH",
            org_id="ORG-PSF-DMATCH",
            account_id="ACC-PSF-DMATCH",
            membership_id="OM-PSF-DMATCH",
            physical_boat_id="PB-PSF-DMATCH",
            market_episode_id="ME-PSF-DMATCH",
            boat_design_id="BD-PSF-DMATCH",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-DMATCH",
            org_id="ORG-PSF-DMATCH",
            account_id="ACC-PSF-DMATCH",
            revision_id="PBCREV-PSF-DMATCH",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
        )
        _log_in(client, "ACC-PSF-DMATCH")
        response = client.get(
            _power_search_fit_path("ORG-PSF-DMATCH", "NL-PSF-DMATCH"),
            params={"power_drive": "SHAFT", "power_engine_count": "2"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_MATCH"
        assert body["blockers"] == []
        assert body["design_evaluation"] is not None
        assert body["design_evaluation"]["result_class"] == "CONFIRMED_MATCH"
        assert body["source_basis"] is None

    def test_design_eligible_missing_concrete_claims_is_insufficient(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-DMISS",
            account_id="ACC-PSF-DMISS",
            membership_id="OM-PSF-DMISS",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn, "BD-PSF-DMISS", "BM-PSF-DMISS", drive_type="shaft", engine_count=2
            )
            _admit_design_drive_and_count(conn, "BD-PSF-DMISS", drive_type="shaft", engine_count=2)
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-DMISS",
            org_id="ORG-PSF-DMISS",
            account_id="ACC-PSF-DMISS",
            membership_id="OM-PSF-DMISS",
            physical_boat_id="PB-PSF-DMISS",
            market_episode_id="ME-PSF-DMISS",
            boat_design_id="BD-PSF-DMISS",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-DMISS",
            org_id="ORG-PSF-DMISS",
            account_id="ACC-PSF-DMISS",
            revision_id="PBCREV-PSF-DMISS",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
        )
        _log_in(client, "ACC-PSF-DMISS")
        response = client.get(
            _power_search_fit_path("ORG-PSF-DMISS", "NL-PSF-DMISS"),
            params={"power_drive": "SHAFT", "power_engine_count": "2"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert set(body["blockers"]) == {
            "POWER_DRIVE_UNCONFIRMED",
            "POWER_ENGINE_COUNT_UNCONFIRMED",
        }

    def test_design_unresolved_configuration_is_insufficient_with_blocker(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-PSF-DTAX", account_id="ACC-PSF-DTAX", membership_id="OM-PSF-DTAX"
        )
        conn = psycopg.connect(api_url)
        try:
            # "jetdrive-v2" has no v0.6 BoatDesign-drive_type -> Search-drive
            # mapping -- fails closed to MISSING, never guessed.
            _insert_boat_design(
                conn, "BD-PSF-DTAX", "BM-PSF-DTAX", drive_type="jetdrive-v2", engine_count=None
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-DTAX",
            org_id="ORG-PSF-DTAX",
            account_id="ACC-PSF-DTAX",
            membership_id="OM-PSF-DTAX",
            physical_boat_id="PB-PSF-DTAX",
            market_episode_id="ME-PSF-DTAX",
            boat_design_id="BD-PSF-DTAX",
        )
        _log_in(client, "ACC-PSF-DTAX")
        response = client.get(
            _power_search_fit_path("ORG-PSF-DTAX", "NL-PSF-DTAX"), params={"power_drive": "SHAFT"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["BOATDESIGN_CONFIGURATION_UNRESOLVED"]
        assert body["criterion_evidence"] == []

    def test_dangling_boat_design_ref_is_chain_integrity_fault(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-DANGLE",
            account_id="ACC-PSF-DANGLE",
            membership_id="OM-PSF-DANGLE",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-DANGLE",
            org_id="ORG-PSF-DANGLE",
            account_id="ACC-PSF-DANGLE",
            membership_id="OM-PSF-DANGLE",
            physical_boat_id="PB-PSF-DANGLE",
            market_episode_id="ME-PSF-DANGLE",
        )
        # The real `fk_physical_boats_boat_design_ref` constraint makes a
        # genuinely dangling stored reference unreachable through the normal
        # write path (`create_physical_boat` fails closed to DESIGN_NOT_FOUND
        # instead of ever persisting it) -- simulate the orphaned-data
        # integrity fault this slice's mechanical invariants still require to
        # fail closed, by dropping the constraint in this disposable
        # per-test schema only (mirrors
        # `test_broker_search_fit_api.py`'s identical technique).
        conn = psycopg.connect(api_url)
        try:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE physical_boats DROP CONSTRAINT fk_physical_boats_boat_design_ref"
                )
                cur.execute(
                    "UPDATE physical_boats SET boat_design_ref = %s WHERE physical_boat_id = %s",
                    ["BD-PSF-DOES-NOT-EXIST", "PB-PSF-DANGLE"],
                )
        finally:
            conn.close()
        _log_in(client, "ACC-PSF-DANGLE")
        response = client.get(
            _power_search_fit_path("ORG-PSF-DANGLE", "NL-PSF-DANGLE"),
            params={"power_drive": "SHAFT"},
        )
        assert response.status_code == 503
        assert response.json()["error"] == "chain_integrity_fault"

    def test_same_named_variant_combined_positive_is_confirmed_match(
        self, client: TestClient, api_url: str
    ) -> None:
        """Independent review amendment Finding D (round 1): a genuine
        same-qualified-NamedVariant positive on the NEW private preview --
        mirrors `test_power_engine_count_slice_0094
        .test_variant_inheriting_drive_with_overridden_count_is_a_legitimate_match`'s
        identical fixture shape for the public buyer path. NamedVariant B
        inherits SHAFT from the baseline (no own drive override) and
        overrides only `engine_count` to 2 -- this ONE configuration's own
        resolved projection genuinely satisfies both requested leaves, and
        the publisher's current concrete claim (SHAFT + count=2)
        independently confirms both."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-NVPOS",
            account_id="ACC-PSF-NVPOS",
            membership_id="OM-PSF-NVPOS",
        )
        conn = psycopg.connect(api_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
                    "VALUES (%s, %s, %s)",
                    ["BM-PSF-NVPOS", "Model BM-PSF-NVPOS", "0" * 64],
                )
                baseline_json = json.dumps(
                    {"propulsion": {"drive_type": "shaft", "engine_count": 1}}
                )
                named_variants_json = json.dumps(
                    [{"id": "NV-PSF-NVPOS-B", "overrides": {"propulsion": {"engine_count": 2}}}]
                )
                cur.execute(
                    "INSERT INTO canonical_boat_designs "
                    "(id, boat_model_id, generation, designers, baseline, named_variants, "
                    " design_options, quality, content_hash) "
                    "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, %s::jsonb, "
                    "'[]'::jsonb, '{}'::jsonb, %s)",
                    ["BD-PSF-NVPOS", "BM-PSF-NVPOS", baseline_json, named_variants_json, "1" * 64],
                )
            conn.commit()
            admit_resolved_categorical_field(
                conn,
                subject_kind=SubjectKind.BOAT_DESIGN,
                subject_id="BD-PSF-NVPOS",
                field_pointer="/baseline/propulsion/drive_type",
                value="shaft",
                resolution_id="FR-PWRDRV-BD-PSF-NVPOS",
                fetch_canonical_value=lookup_power_drive_canonical_value,
            )
            admit_resolved_draft_max(
                conn,
                subject_kind=SubjectKind.BOAT_DESIGN,
                subject_id="BD-PSF-NVPOS",
                field_pointer="/baseline/propulsion/engine_count",
                value=Decimal(1),
                resolution_id="FR-PWRCNT-BD-PSF-NVPOS",
                fetch_canonical_value=lookup_power_engine_count_canonical_value,
            )
            admit_resolved_draft_max(
                conn,
                subject_kind=SubjectKind.NAMED_VARIANT,
                subject_id="NV-PSF-NVPOS-B",
                field_pointer="/overrides/propulsion/engine_count",
                value=Decimal(2),
                resolution_id="FR-PWRCNT-NV-PSF-NVPOS-B",
                fetch_canonical_value=lookup_power_engine_count_canonical_value,
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-NVPOS",
            org_id="ORG-PSF-NVPOS",
            account_id="ACC-PSF-NVPOS",
            membership_id="OM-PSF-NVPOS",
            physical_boat_id="PB-PSF-NVPOS",
            market_episode_id="ME-PSF-NVPOS",
            boat_design_id="BD-PSF-NVPOS",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-NVPOS",
            org_id="ORG-PSF-NVPOS",
            account_id="ACC-PSF-NVPOS",
            revision_id="PBCREV-PSF-NVPOS",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
        )
        _log_in(client, "ACC-PSF-NVPOS")
        response = client.get(
            _power_search_fit_path("ORG-PSF-NVPOS", "NL-PSF-NVPOS"),
            params={"power_drive": "SHAFT", "power_engine_count": "2"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_MATCH", body
        assert body["blockers"] == []
        assert body["design_evaluation"]["result_class"] == "CONFIRMED_MATCH"
        assert len(body["design_evaluation"]["matching_configuration_ids"]) >= 1

    def test_cross_variant_split_adversarial_never_matches(
        self, client: TestClient, api_url: str
    ) -> None:
        """Independent review amendment Finding D (round 1): the genuine
        adversarial cross-variant split on the NEW private preview --
        mirrors `test_power_engine_count_slice_0094
        .test_cross_variant_split_adversarial_neither_configuration_satisfies_both_never_matches`'s
        identical fixture. Baseline is SHAFT+count=1 (properly qualified);
        NamedVariant B overrides BOTH fields to OUTBOARD+count=2 (also
        properly qualified). Baseline alone satisfies drive but not count;
        variant B alone satisfies count but not drive -- neither single
        resolved configuration satisfies both requested leaves together.
        The publisher's current concrete claim is SHAFT+count=2, which
        taken ALONE would satisfy both -- the exact adversarial signal that
        a confirmed concrete claim must never promote a design level that
        is not itself a genuine CONFIRMED_MATCH ("design truth never
        silently becomes concrete truth"). Must be INSUFFICIENT_DATA with
        BOATDESIGN_CONFIGURATION_UNRESOLVED, never CONFIRMED_MATCH, and the
        concrete claim is never even consulted."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-NVADV",
            account_id="ACC-PSF-NVADV",
            membership_id="OM-PSF-NVADV",
        )
        conn = psycopg.connect(api_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) "
                    "VALUES (%s, %s, %s)",
                    ["BM-PSF-NVADV", "Model BM-PSF-NVADV", "0" * 64],
                )
                baseline_json = json.dumps(
                    {"propulsion": {"drive_type": "shaft", "engine_count": 1}}
                )
                named_variants_json = json.dumps(
                    [
                        {
                            "id": "NV-PSF-NVADV-B",
                            "overrides": {
                                "propulsion": {"drive_type": "outboard", "engine_count": 2}
                            },
                        }
                    ]
                )
                cur.execute(
                    "INSERT INTO canonical_boat_designs "
                    "(id, boat_model_id, generation, designers, baseline, named_variants, "
                    " design_options, quality, content_hash) "
                    "VALUES (%s, %s, '{}'::jsonb, '[]'::jsonb, %s::jsonb, %s::jsonb, "
                    "'[]'::jsonb, '{}'::jsonb, %s)",
                    ["BD-PSF-NVADV", "BM-PSF-NVADV", baseline_json, named_variants_json, "1" * 64],
                )
            conn.commit()
            admit_resolved_categorical_field(
                conn,
                subject_kind=SubjectKind.BOAT_DESIGN,
                subject_id="BD-PSF-NVADV",
                field_pointer="/baseline/propulsion/drive_type",
                value="shaft",
                resolution_id="FR-PWRDRV-BD-PSF-NVADV",
                fetch_canonical_value=lookup_power_drive_canonical_value,
            )
            admit_resolved_draft_max(
                conn,
                subject_kind=SubjectKind.BOAT_DESIGN,
                subject_id="BD-PSF-NVADV",
                field_pointer="/baseline/propulsion/engine_count",
                value=Decimal(1),
                resolution_id="FR-PWRCNT-BD-PSF-NVADV",
                fetch_canonical_value=lookup_power_engine_count_canonical_value,
            )
            admit_resolved_categorical_field(
                conn,
                subject_kind=SubjectKind.NAMED_VARIANT,
                subject_id="NV-PSF-NVADV-B",
                field_pointer="/overrides/propulsion/drive_type",
                value="outboard",
                resolution_id="FR-PWRDRV-NV-PSF-NVADV-B",
                fetch_canonical_value=lookup_power_drive_canonical_value,
            )
            admit_resolved_draft_max(
                conn,
                subject_kind=SubjectKind.NAMED_VARIANT,
                subject_id="NV-PSF-NVADV-B",
                field_pointer="/overrides/propulsion/engine_count",
                value=Decimal(2),
                resolution_id="FR-PWRCNT-NV-PSF-NVADV-B",
                fetch_canonical_value=lookup_power_engine_count_canonical_value,
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-NVADV",
            org_id="ORG-PSF-NVADV",
            account_id="ACC-PSF-NVADV",
            membership_id="OM-PSF-NVADV",
            physical_boat_id="PB-PSF-NVADV",
            market_episode_id="ME-PSF-NVADV",
            boat_design_id="BD-PSF-NVADV",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-NVADV",
            org_id="ORG-PSF-NVADV",
            account_id="ACC-PSF-NVADV",
            revision_id="PBCREV-PSF-NVADV",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
            power_engine_count=PowerEngineCountClaim(assertion_kind=VA, value=2),
        )
        _log_in(client, "ACC-PSF-NVADV")
        response = client.get(
            _power_search_fit_path("ORG-PSF-NVADV", "NL-PSF-NVADV"),
            params={"power_drive": "SHAFT", "power_engine_count": "2"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA", body
        assert body["blockers"] == ["BOATDESIGN_CONFIGURATION_UNRESOLVED"]
        assert body["criterion_evidence"] == []
        assert body["design_evaluation"]["result_class"] == "INSUFFICIENT_DATA"


# ---------------------------------------------------------------------------
# NOT_PREVIEWABLE / zero writes / Sail non-regression
# ---------------------------------------------------------------------------


class TestPowerSearchFitLifecycleAndRegression:
    def test_active_listing_is_not_previewable(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-ACTIVE",
            account_id="ACC-PSF-ACTIVE",
            membership_id="OM-PSF-ACTIVE",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-ACTIVE",
            org_id="ORG-PSF-ACTIVE",
            account_id="ACC-PSF-ACTIVE",
            membership_id="OM-PSF-ACTIVE",
            physical_boat_id="PB-PSF-ACTIVE",
            market_episode_id="ME-PSF-ACTIVE",
        )
        conn = psycopg.connect(api_url)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE native_listings SET lifecycle_state = 'ACTIVE' "
                    "WHERE native_listing_id = %s",
                    ["NL-PSF-ACTIVE"],
                )
            conn.commit()
        finally:
            conn.close()
        _log_in(client, "ACC-PSF-ACTIVE")
        response = client.get(
            _power_search_fit_path("ORG-PSF-ACTIVE", "NL-PSF-ACTIVE"),
            params={"power_drive": "SHAFT"},
        )
        assert response.status_code == 409
        assert response.json()["error"] == "not_previewable"

    def test_preview_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-NOWRITE",
            account_id="ACC-PSF-NOWRITE",
            membership_id="OM-PSF-NOWRITE",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-NOWRITE",
            org_id="ORG-PSF-NOWRITE",
            account_id="ACC-PSF-NOWRITE",
            membership_id="OM-PSF-NOWRITE",
            physical_boat_id="PB-PSF-NOWRITE",
            market_episode_id="ME-PSF-NOWRITE",
        )
        _write_claim(
            api_url,
            listing_id="NL-PSF-NOWRITE",
            org_id="ORG-PSF-NOWRITE",
            account_id="ACC-PSF-NOWRITE",
            revision_id="PBCREV-PSF-NOWRITE",
            vessel_category=VesselCategoryClaim(assertion_kind=VA, value=VesselCategory.POWER),
            power_drive_configuration=PowerDriveConfigurationClaim(
                assertion_kind=VA, value=PowerDriveConfiguration.SHAFT
            ),
        )
        before = _capture_write_fingerprint(
            api_url,
            native_listing_id="NL-PSF-NOWRITE",
            physical_boat_id="PB-PSF-NOWRITE",
            organization_id="ORG-PSF-NOWRITE",
        )
        _log_in(client, "ACC-PSF-NOWRITE")
        response = client.get(
            _power_search_fit_path("ORG-PSF-NOWRITE", "NL-PSF-NOWRITE"),
            params={"power_drive": "SHAFT"},
        )
        assert response.status_code == 200
        after = _capture_write_fingerprint(
            api_url,
            native_listing_id="NL-PSF-NOWRITE",
            physical_boat_id="PB-PSF-NOWRITE",
            organization_id="ORG-PSF-NOWRITE",
        )
        assert before == after

    def test_sail_broker_search_fit_still_works(self, client: TestClient, api_url: str) -> None:
        """Regression: the Sail-only `/search-fit` endpoint, its parser and
        its result semantics are untouched by this slice (contract Required
        Behavior §1)."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-PSF-SAILREG",
            account_id="ACC-PSF-SAILREG",
            membership_id="OM-PSF-SAILREG",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-PSF-SAILREG",
            org_id="ORG-PSF-SAILREG",
            account_id="ACC-PSF-SAILREG",
            membership_id="OM-PSF-SAILREG",
            physical_boat_id="PB-PSF-SAILREG",
            market_episode_id="ME-PSF-SAILREG",
        )
        _log_in(client, "ACC-PSF-SAILREG")
        sail_response = client.get(
            "/api/broker/organizations/ORG-PSF-SAILREG/inventory/NL-PSF-SAILREG/search-fit",
            params={"draft_max": "1.5"},
        )
        assert sail_response.status_code == 200
        assert sail_response.json()["result_class"] == "INSUFFICIENT_DATA"
        assert sail_response.json()["blockers"] == ["BOATDESIGN_NOT_LINKED"]

        # The Power endpoint on the SAME listing rejects Sail's own key.
        power_response = client.get(
            _power_search_fit_path("ORG-PSF-SAILREG", "NL-PSF-SAILREG"), params={"draft_max": "1.5"}
        )
        assert power_response.status_code == 400
