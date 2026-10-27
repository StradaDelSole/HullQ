"""FastAPI integration tests for SLICE-0084 broker pre-publication technical
Search-fit preview (`hullq.application.broker_search_fit`).

Mirrors `test_boat_design_association_api.py`'s fixture/session-minting
pattern: a directly minted session token rather than a full OIDC round-trip.

Covers the slice's acceptance criteria: Organization/MFA/PUBLISHER
authorization and non-enumeration; bounded scenario validation (empty,
unsupported `LONG_KEEL`, duplicate, non-canonical); truth parity with the
accepted public Search kernel for match/non-match/insufficient-data, alone
and mixed; unlinked-design and missing/unknown/contradictory concrete claim
blockers; `NOT_PREVIEWABLE` for a non-DRAFT listing; a dangling BoatDesignRef
failing closed as a service/integrity fault rather than a confirmed value;
zero writes; and the DRAFT-preview-vs-published-public-Search equivalence
the contract's executable adversarial proof requires.
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
from hullq.domain.media_gallery import MediaSourceKind
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
from hullq.domain.physical_boat_claims import (
    AssertionKind,
    BeamClaim,
    BuildYearClaim,
    CockpitPosition,
    CockpitPositionClaim,
    DeckSaloon,
    DeckSaloonClaim,
    DraftClaim,
    HullConfiguration,
    HullConfigurationClaim,
    HullMaterial,
    HullMaterialClaim,
    KeelConfiguration,
    KeelConfigurationClaim,
    LoaLengthClaim,
    PhysicalBoatClaimRevisionId,
    PhysicalBoatClaimSnapshot,
    RudderConfiguration,
    RudderConfigurationClaim,
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
from hullq.persistence.media_gallery import (
    create_uploaded_image_placement,
    insert_approved_media_asset,
    set_cover,
)
from hullq.persistence.native_listing import create_native_listing, fetch_native_listing
from hullq.persistence.native_listing_lifecycle import (
    fetch_lifecycle_state,
    publish_native_listing,
)
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.persistence.physical_boat_claims import (
    fetch_current_physical_boat_claim,
    write_physical_boat_claim_revision,
)
from hullq.search.beam_design_bridge import BEAM_FIELD_POINTER, lookup_beam_canonical_value
from hullq.search.cockpit_design_bridge import lookup_cockpit_position_canonical_value
from hullq.search.deck_saloon_design_bridge import lookup_deck_saloon_canonical_value
from hullq.search.draft_max_design_bridge import DRAFT_MAX_FIELD_POINTER
from hullq.search.hull_design_bridge import lookup_hull_configuration_canonical_value
from hullq.search.hull_material_design_bridge import (
    HULL_MATERIAL_FIELD_POINTER,
    lookup_hull_material_canonical_value,
)
from hullq.search.keel_design_bridge import KEEL_TYPE_FIELD_POINTER, lookup_keel_canonical_value
from hullq.search.loa_design_bridge import LOA_FIELD_POINTER, lookup_loa_canonical_value
from hullq.search.rudder_design_bridge import lookup_rudder_canonical_value
from hullq.security.session_token import mint_session_token

from ._field_resolution_support import admit_resolved_categorical_field, admit_resolved_draft_max

_SECRET = b"7" * 32
_WEB_ORIGIN = "http://web.test"


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
    schema_name = f"hullq_s0084sf_{uuid.uuid4().hex[:16]}"
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
    conn: Any,
    design_id: str,
    model_id: str,
    *,
    baseline_keel_type: str,
    baseline_draft_max_m: float = 1.30,
    baseline_loa_m: float | None = None,
    baseline_rudder_support: str | None = None,
    baseline_hull_configuration: str | None = None,
    baseline_cockpit_position: str | None = None,
    baseline_deck_saloon: str | None = None,
    baseline_beam_m: float | None = None,
    baseline_hull_material: str | None = None,
) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO canonical_boat_models (id, canonical_name, content_hash) VALUES (%s, %s, %s)",
            [model_id, f"Model {model_id}", "0" * 64],
        )
        baseline_json = json.dumps(
            {
                "dimensions": {
                    "draft_max_m": baseline_draft_max_m,
                    "loa_m": baseline_loa_m,
                    "beam_m": baseline_beam_m,
                },
                "configuration": {"hull_configuration": baseline_hull_configuration},
                "appendages": {
                    "keel_type": baseline_keel_type,
                    "rudder_support": baseline_rudder_support,
                },
                "deck": {
                    "cockpit_position": baseline_cockpit_position,
                    "deck_saloon": baseline_deck_saloon,
                },
                "construction": {"hull_material": baseline_hull_material},
            }
        )
        cur.execute(
            "INSERT INTO canonical_boat_designs "
            "(id, boat_model_id, generation, designers, baseline, named_variants, "
            " design_options, quality, content_hash) "
            "VALUES (%s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s::jsonb, %s)",
            [design_id, model_id, "{}", "[]", baseline_json, "[]", "[]", "{}", "1" * 64],
        )
    conn.commit()


def _admit_design_keel_and_draft(
    conn: Any,
    design_id: str,
    *,
    keel_type: str,
    draft_max_m: Decimal = Decimal("1.30"),
    loa_m: Decimal | None = None,
    rudder_support: str | None = None,
    hull_configuration: str | None = None,
    cockpit_position: str | None = None,
    deck_saloon: str | None = None,
    beam_m: Decimal | None = None,
    hull_material: str | None = None,
) -> None:
    admit_resolved_draft_max(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=DRAFT_MAX_FIELD_POINTER,
        value=draft_max_m,
        resolution_id=f"FR-DRAFT-{design_id}",
    )
    admit_resolved_categorical_field(
        conn,
        subject_kind=SubjectKind.BOAT_DESIGN,
        subject_id=design_id,
        field_pointer=KEEL_TYPE_FIELD_POINTER,
        value=keel_type,
        resolution_id=f"FR-KEEL-{design_id}",
        fetch_canonical_value=lookup_keel_canonical_value,
    )
    if loa_m is not None:
        admit_resolved_draft_max(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer=LOA_FIELD_POINTER,
            value=loa_m,
            resolution_id=f"FR-LOA-{design_id}",
            fetch_canonical_value=lookup_loa_canonical_value,
        )
    if rudder_support is not None:
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer="/baseline/appendages/rudder_support",
            value=rudder_support,
            resolution_id=f"FR-RUDDER-{design_id}",
            fetch_canonical_value=lookup_rudder_canonical_value,
        )
    if hull_configuration is not None:
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer="/baseline/configuration/hull_configuration",
            value=hull_configuration,
            resolution_id=f"FR-HULLCFG-{design_id}",
            fetch_canonical_value=lookup_hull_configuration_canonical_value,
        )
    if cockpit_position is not None:
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer="/baseline/deck/cockpit_position",
            value=cockpit_position,
            resolution_id=f"FR-COCKPITPOS-{design_id}",
            fetch_canonical_value=lookup_cockpit_position_canonical_value,
        )
    if deck_saloon is not None:
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer="/baseline/deck/deck_saloon",
            value=deck_saloon,
            resolution_id=f"FR-DECKSALOON-{design_id}",
            fetch_canonical_value=lookup_deck_saloon_canonical_value,
        )
    if beam_m is not None:
        admit_resolved_draft_max(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer=BEAM_FIELD_POINTER,
            value=beam_m,
            resolution_id=f"FR-BEAM-{design_id}",
            fetch_canonical_value=lookup_beam_canonical_value,
        )
    if hull_material is not None:
        admit_resolved_categorical_field(
            conn,
            subject_kind=SubjectKind.BOAT_DESIGN,
            subject_id=design_id,
            field_pointer=HULL_MATERIAL_FIELD_POINTER,
            value=hull_material,
            resolution_id=f"FR-HULLMAT-{design_id}",
            fetch_canonical_value=lookup_hull_material_canonical_value,
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
    """The exact shape SLICE-0067 promotion produces: a fresh, lifecycle-DRAFT
    NativeListing -> MarketEpisode -> PhysicalBoat chain, optionally with an
    already-linked `boat_design_ref` (never written through the 0082
    association endpoint itself -- that flow is out of this slice's scope)."""
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


def _keel_value(value: str) -> KeelConfigurationClaim:
    return KeelConfigurationClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=KeelConfiguration(value)
    )


def _draft_value(value: str) -> DraftClaim:
    return DraftClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal(value))


def _loa_value(value: str) -> LoaLengthClaim:
    return LoaLengthClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal(value))


def _rudder_value(value: str) -> RudderConfigurationClaim:
    return RudderConfigurationClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=RudderConfiguration(value)
    )


def _hull_value(value: str) -> HullConfigurationClaim:
    return HullConfigurationClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullConfiguration(value)
    )


def _cockpit_value(value: str) -> CockpitPositionClaim:
    return CockpitPositionClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=CockpitPosition(value)
    )


def _deck_saloon_value(value: str) -> DeckSaloonClaim:
    return DeckSaloonClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=DeckSaloon(value))


def _beam_value(value: Decimal) -> BeamClaim:
    return BeamClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=value)


def _hull_material_value(value: str) -> HullMaterialClaim:
    return HullMaterialClaim(
        assertion_kind=AssertionKind.VALUE_ASSERTION, value=HullMaterial(value)
    )


def _write_claim(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    revision_id: str,
    draft: DraftClaim | None = None,
    keel_configuration: KeelConfigurationClaim | None = None,
    loa_length: LoaLengthClaim | None = None,
    rudder_configuration: RudderConfigurationClaim | None = None,
    hull_configuration: HullConfigurationClaim | None = None,
    cockpit_position: CockpitPositionClaim | None = None,
    deck_saloon: DeckSaloonClaim | None = None,
    beam: BeamClaim | None = None,
    hull_material: HullMaterialClaim | None = None,
    vessel_category: VesselCategoryClaim | None = None,
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
                model_designation_claim="Oceanis 30.1",
                build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
                draft=draft,
                keel_configuration=keel_configuration,
                loa_length=loa_length,
                rudder_configuration=rudder_configuration,
                hull_configuration=hull_configuration,
                cockpit_position=cockpit_position,
                deck_saloon=deck_saloon,
                beam=beam,
                hull_material=hull_material,
                vessel_category=vessel_category,
            ),
        )
        assert result.status.value in ("created", "revised"), result
    finally:
        conn.close()


def _search_fit_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/search-fit"


def _capture_write_fingerprint(
    api_url: str, *, native_listing_id: str, physical_boat_id: str, organization_id: str
) -> dict[str, Any]:
    """Independent review proof-completeness note (PR #342): a bounded
    snapshot across every write destination this preview could conceivably
    touch -- not only the single current claim revision id the original
    test checked. Table row *counts* (not merely a single "current" head)
    so a superseding revision inserted alongside an unchanged head would
    still be detected."""
    conn = psycopg.connect(api_url)
    try:
        lifecycle = fetch_lifecycle_state(conn, NativeListingId(native_listing_id))
        claim = fetch_current_physical_boat_claim(
            conn, PhysicalBoatId(physical_boat_id), MarketplaceOrganizationId(organization_id)
        )
        with conn.cursor() as cur:
            cur.execute(
                "SELECT publishing_organization_id, market_episode_id FROM native_listings "
                "WHERE native_listing_id = %s",
                [native_listing_id],
            )
            listing_row = cur.fetchone()
            cur.execute(
                "SELECT boat_design_ref FROM physical_boats WHERE physical_boat_id = %s",
                [physical_boat_id],
            )
            design_ref_row = cur.fetchone()
            cur.execute("SELECT COUNT(*) FROM native_listing_publication_transitions")
            transition_count = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM physical_boat_claim_revisions WHERE physical_boat_id = %s",
                [physical_boat_id],
            )
            claim_revision_count = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM native_listing_offer_revisions WHERE native_listing_id = %s",
                [native_listing_id],
            )
            offer_revision_count = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM boat_design_association_events WHERE physical_boat_id = %s",
                [physical_boat_id],
            )
            design_association_event_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM buyer_leads")
            lead_count = cur.fetchone()[0]
            cur.execute("SELECT COUNT(*) FROM field_resolutions")
            field_resolution_count = cur.fetchone()[0]
    finally:
        conn.close()
    return {
        "lifecycle": lifecycle,
        "claim_revision_id": claim.revision_id if claim is not None else None,
        "listing_row": listing_row,
        "design_ref_row": design_ref_row,
        "transition_count": transition_count,
        "claim_revision_count": claim_revision_count,
        "offer_revision_count": offer_revision_count,
        "design_association_event_count": design_association_event_count,
        "lead_count": lead_count,
        "field_resolution_count": field_resolution_count,
    }


# ---------------------------------------------------------------------------
# Authorization / privacy / non-enumeration
# ---------------------------------------------------------------------------


class TestSearchFitAuthorization:
    def test_unauthenticated_is_blocked(self, client: TestClient) -> None:
        response = client.get(_search_fit_path("ORG-X", "NL-X"), params={"draft_max": "1.5"})
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-SF-NEVER")
        response = client.get(_search_fit_path("ORG-SF-NEVER", "NL-X"), params={"draft_max": "1.5"})
        assert response.status_code == 404

    def test_foreign_listing_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-A", account_id="ACC-SF-A", membership_id="OM-SF-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-B", account_id="ACC-SF-B", membership_id="OM-SF-B"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-FOREIGN",
            org_id="ORG-SF-B",
            account_id="ACC-SF-B",
            membership_id="OM-SF-B",
            physical_boat_id="PB-SF-FOREIGN",
            market_episode_id="ME-SF-FOREIGN",
        )
        _log_in(client, "ACC-SF-A")
        response = client.get(
            _search_fit_path("ORG-SF-A", "NL-SF-FOREIGN"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 404

    def test_mfa_required_blocks_read(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-MFA", account_id="ACC-SF-MFA", membership_id="OM-SF-MFA"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-MFA",
            org_id="ORG-SF-MFA",
            account_id="ACC-SF-MFA",
            membership_id="OM-SF-MFA",
            physical_boat_id="PB-SF-MFA",
            market_episode_id="ME-SF-MFA",
        )
        _log_in(client, "ACC-SF-MFA", mfa=False)
        response = client.get(
            _search_fit_path("ORG-SF-MFA", "NL-SF-MFA"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 403
        assert response.json()["error"] == "mfa_required"

    def test_publisher_role_required(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-SF-NOPUB",
            account_id="ACC-SF-NOPUB",
            membership_id="OM-SF-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-NOPUB",
            org_id="ORG-SF-NOPUB",
            account_id="ACC-SF-NOPUB",
            membership_id="OM-SF-NOPUB",
            physical_boat_id="PB-SF-NOPUB",
            market_episode_id="ME-SF-NOPUB",
        )
        _log_in(client, "ACC-SF-NOPUB")
        response = client.get(
            _search_fit_path("ORG-SF-NOPUB", "NL-SF-NOPUB"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 403
        assert response.json()["reason"] == "PUBLISHER_ROLE_REQUIRED"


# ---------------------------------------------------------------------------
# Scenario validation
# ---------------------------------------------------------------------------


class TestSearchFitScenarioValidation:
    def _setup(self, api_url: str, client: TestClient, suffix: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id=f"ORG-SF-{suffix}",
            account_id=f"ACC-SF-{suffix}",
            membership_id=f"OM-SF-{suffix}",
        )
        _create_draft_listing(
            api_url,
            listing_id=f"NL-SF-{suffix}",
            org_id=f"ORG-SF-{suffix}",
            account_id=f"ACC-SF-{suffix}",
            membership_id=f"OM-SF-{suffix}",
            physical_boat_id=f"PB-SF-{suffix}",
            market_episode_id=f"ME-SF-{suffix}",
        )
        _log_in(client, f"ACC-SF-{suffix}")

    def test_empty_scenario_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "EMPTY")
        response = client.get(_search_fit_path("ORG-SF-EMPTY", "NL-SF-EMPTY"))
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_scenario"

    def test_unsupported_long_keel_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "LONGKEEL")
        response = client.get(
            _search_fit_path("ORG-SF-LONGKEEL", "NL-SF-LONGKEEL"),
            params={"keel_configuration": "LONG_KEEL"},
        )
        assert response.status_code == 400

    def test_duplicate_draft_max_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "DUPE")
        response = client.get(
            _search_fit_path("ORG-SF-DUPE", "NL-SF-DUPE"),
            params=[("draft_max", "1.5"), ("draft_max", "1.5")],
        )
        assert response.status_code == 400

    def test_noncanonical_draft_max_is_invalid(self, client: TestClient, api_url: str) -> None:
        self._setup(api_url, client, "NONCANON")
        response = client.get(
            _search_fit_path("ORG-SF-NONCANON", "NL-SF-NONCANON"),
            params={"draft_max": "01.50"},
        )
        assert response.status_code == 400

    def test_unknown_parameter_is_invalid(self, client: TestClient, api_url: str) -> None:
        # SLICE-0087: `beam_max` is now an accepted scenario key -- this
        # test's "unknown parameter" case is updated to a genuinely
        # unsupported key (not part of the accepted whitelist) so it still
        # proves the fail-closed unknown-key rejection it was written for.
        self._setup(api_url, client, "UNKNOWNPARAM")
        response = client.get(
            _search_fit_path("ORG-SF-UNKNOWNPARAM", "NL-SF-UNKNOWNPARAM"),
            params={"displacement_kg": "5000"},
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# Truth parity + blockers
# ---------------------------------------------------------------------------


class TestSearchFitTruthParity:
    def test_unlinked_design_is_insufficient_with_blocker(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-UNL", account_id="ACC-SF-UNL", membership_id="OM-SF-UNL"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-UNL",
            org_id="ORG-SF-UNL",
            account_id="ACC-SF-UNL",
            membership_id="OM-SF-UNL",
            physical_boat_id="PB-SF-UNL",
            market_episode_id="ME-SF-UNL",
        )
        _log_in(client, "ACC-SF-UNL")
        response = client.get(
            _search_fit_path("ORG-SF-UNL", "NL-SF-UNL"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["BOATDESIGN_NOT_LINKED"]
        assert body["design_evaluation"] is None

    def test_confirmed_match_mixed_draft_and_keel(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-MATCH", account_id="ACC-SF-MATCH", membership_id="OM-SF-MATCH"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-MATCH",
                "BM-SF-MATCH",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-MATCH", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-MATCH",
            org_id="ORG-SF-MATCH",
            account_id="ACC-SF-MATCH",
            membership_id="OM-SF-MATCH",
            physical_boat_id="PB-SF-MATCH",
            market_episode_id="ME-SF-MATCH",
            boat_design_id="BD-SF-MATCH",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-MATCH",
            org_id="ORG-SF-MATCH",
            account_id="ACC-SF-MATCH",
            revision_id="PBCREV-SF-MATCH",
            draft=_draft_value("1.20"),
            keel_configuration=_keel_value("FIN"),
        )
        _log_in(client, "ACC-SF-MATCH")
        response = client.get(
            _search_fit_path("ORG-SF-MATCH", "NL-SF-MATCH"),
            params={"draft_max": "1.5", "keel_configuration": "FIN"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_MATCH"
        assert body["blockers"] == []
        assert body["active_requirement"] == {"draft_max": "1.5", "keel_configuration": "FIN"}
        assert len(body["criterion_evidence"]) == 2

        # Mechanical invariant: lifecycle-DRAFT preview never leaks into the
        # accepted public technical Search while still DRAFT.
        public_search = client.get(
            "/api/search/en", params={"draft_max": "1.5", "keel_configuration": "FIN"}
        )
        assert public_search.status_code == 200
        assert public_search.json()["confirmed_match_count"] == 0

    def test_confirmed_non_match_draft_too_deep(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-NONM", account_id="ACC-SF-NONM", membership_id="OM-SF-NONM"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-NONM",
                "BM-SF-NONM",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-NONM", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-NONM",
            org_id="ORG-SF-NONM",
            account_id="ACC-SF-NONM",
            membership_id="OM-SF-NONM",
            physical_boat_id="PB-SF-NONM",
            market_episode_id="ME-SF-NONM",
            boat_design_id="BD-SF-NONM",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-NONM",
            org_id="ORG-SF-NONM",
            account_id="ACC-SF-NONM",
            revision_id="PBCREV-SF-NONM",
            draft=_draft_value("1.80"),
            keel_configuration=_keel_value("FIN"),
        )
        _log_in(client, "ACC-SF-NONM")
        response = client.get(
            _search_fit_path("ORG-SF-NONM", "NL-SF-NONM"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_NON_MATCH"
        assert body["blockers"] == []
        # SLICE-0091 amendment Finding I: an ordinary technical mismatch
        # never carries vessel category exclusion evidence.
        assert body["vessel_category_exclusion"] is None

    def test_confirmed_non_match_vessel_category_exclusion_carries_evidence(
        self, client: TestClient, api_url: str
    ) -> None:
        """SLICE-0091 amendment review Finding I: a `CONFIRMED_NON_MATCH`
        produced by the category pre-filter (never an ordinary nine-
        criterion technical mismatch) must retain *why*, bounded to the
        resolved enum values only -- no Organization/Account identity."""
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-CATX", account_id="ACC-SF-CATX", membership_id="OM-SF-CATX"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-CATX",
                "BM-SF-CATX",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-CATX", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-CATX",
            org_id="ORG-SF-CATX",
            account_id="ACC-SF-CATX",
            membership_id="OM-SF-CATX",
            physical_boat_id="PB-SF-CATX",
            market_episode_id="ME-SF-CATX",
            boat_design_id="BD-SF-CATX",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-CATX",
            org_id="ORG-SF-CATX",
            account_id="ACC-SF-CATX",
            revision_id="PBCREV-SF-CATX",
            draft=_draft_value("1.20"),
            keel_configuration=_keel_value("FIN"),
            vessel_category=VesselCategoryClaim(
                assertion_kind=AssertionKind.VALUE_ASSERTION, value=VesselCategory.POWER
            ),
        )
        _log_in(client, "ACC-SF-CATX")
        response = client.get(
            _search_fit_path("ORG-SF-CATX", "NL-SF-CATX"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_NON_MATCH"
        assert body["blockers"] == []
        assert body["vessel_category_exclusion"] == {
            "resolution": "POWER",
            "reason": "CONCRETE_ONLY",
        }

    def test_missing_concrete_claim_is_insufficient_with_blocker(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-MISS", account_id="ACC-SF-MISS", membership_id="OM-SF-MISS"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-MISS",
                "BM-SF-MISS",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-MISS", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-MISS",
            org_id="ORG-SF-MISS",
            account_id="ACC-SF-MISS",
            membership_id="OM-SF-MISS",
            physical_boat_id="PB-SF-MISS",
            market_episode_id="ME-SF-MISS",
            boat_design_id="BD-SF-MISS",
        )
        # No concrete claim written at all for this publishing Organization.
        _log_in(client, "ACC-SF-MISS")
        response = client.get(
            _search_fit_path("ORG-SF-MISS", "NL-SF-MISS"),
            params={"draft_max": "1.5", "keel_configuration": "FIN"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert set(body["blockers"]) == {
            "CONCRETE_DRAFT_UNCONFIRMED",
            "KEEL_CONFIGURATION_UNCONFIRMED",
        }

    def test_cross_organization_contradiction_is_insufficient(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-XORG", account_id="ACC-SF-XORG", membership_id="OM-SF-XORG"
        )
        _seed_org_and_membership(
            api_url,
            org_id="ORG-SF-XORG-OTHER",
            account_id="ACC-SF-XORG-OTHER",
            membership_id="OM-SF-XORG-OTHER",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-XORG",
                "BM-SF-XORG",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-XORG", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-XORG",
            org_id="ORG-SF-XORG",
            account_id="ACC-SF-XORG",
            membership_id="OM-SF-XORG",
            physical_boat_id="PB-SF-XORG",
            market_episode_id="ME-SF-XORG",
            boat_design_id="BD-SF-XORG",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-XORG",
            org_id="ORG-SF-XORG",
            account_id="ACC-SF-XORG",
            revision_id="PBCREV-SF-XORG-A",
            draft=_draft_value("1.20"),
        )
        # A different claiming Organization asserts a contradictory draft for
        # the *same* PhysicalBoat, through its own NativeListing -> new
        # MarketEpisode -> the shared PhysicalBoat (mirrors
        # `test_native_inventory_query.py`'s identical cross-Organization
        # contradiction fixture shape) -- the claim-write entry point itself
        # requires the candidate Organization to equal the target listing's
        # own publishing Organization, so it cannot be written through
        # NL-SF-XORG directly.
        conn = psycopg.connect(api_url)
        try:
            other_account = AccountId("ACC-SF-XORG-OTHER")
            other_org = MarketplaceOrganization(
                id=MarketplaceOrganizationId("ORG-SF-XORG-OTHER"),
                professional_category=ProfessionalCategory.BROKER,
                publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
            )
            other_membership = OrganizationMembership(
                id=OrganizationMembershipId("OM-SF-XORG-OTHER"),
                account_id=other_account,
                organization_id=other_org.id,
                roles=frozenset({MembershipRole.PUBLISHER}),
                state=MembershipState.ACTIVE,
            )
            create_market_episode(
                conn,
                market_episode=MarketEpisode(
                    id=MarketEpisodeId("ME-SF-XORG-OTHER"),
                    physical_boat_id=PhysicalBoatId("PB-SF-XORG"),
                ),
            )
            create_native_listing(
                conn,
                account_id=other_account,
                candidate_organization=other_org,
                membership=other_membership,
                listing=NativeListing(
                    id=NativeListingId("NL-SF-XORG-OTHER"),
                    market_episode_id=MarketEpisodeId("ME-SF-XORG-OTHER"),
                ),
            )
            conn.commit()
        finally:
            conn.close()
        _write_claim(
            api_url,
            listing_id="NL-SF-XORG-OTHER",
            org_id="ORG-SF-XORG-OTHER",
            account_id="ACC-SF-XORG-OTHER",
            revision_id="PBCREV-SF-XORG-B",
            draft=_draft_value("1.90"),
        )
        _log_in(client, "ACC-SF-XORG")
        response = client.get(
            _search_fit_path("ORG-SF-XORG", "NL-SF-XORG"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["CONCRETE_DRAFT_UNCONFIRMED"]

    def test_unsupported_keel_taxonomy_mapping_is_insufficient(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-TAX", account_id="ACC-SF-TAX", membership_id="OM-SF-TAX"
        )
        conn = psycopg.connect(api_url)
        try:
            # "bilge" has no v0.1 BoatDesign-keel_type -> Search-keel_configuration
            # mapping -- fails closed to MISSING, never guessed.
            _insert_boat_design(
                conn,
                "BD-SF-TAX",
                "BM-SF-TAX",
                baseline_keel_type="bilge",
                baseline_draft_max_m=1.30,
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-TAX",
            org_id="ORG-SF-TAX",
            account_id="ACC-SF-TAX",
            membership_id="OM-SF-TAX",
            physical_boat_id="PB-SF-TAX",
            market_episode_id="ME-SF-TAX",
            boat_design_id="BD-SF-TAX",
        )
        _log_in(client, "ACC-SF-TAX")
        response = client.get(
            _search_fit_path("ORG-SF-TAX", "NL-SF-TAX"), params={"keel_configuration": "FIN"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["BOATDESIGN_CONFIGURATION_UNRESOLVED"]
        assert body["criterion_evidence"] == []


# ---------------------------------------------------------------------------
# SLICE-0085: LOA + rudder_configuration truth parity through the identical
# bounded preview, reusing the exact same shared funnel as draft/keel above.
# ---------------------------------------------------------------------------


class TestSearchFitMulticriteriaTruthParity:
    def test_confirmed_match_all_five_criteria(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-MC5", account_id="ACC-SF-MC5", membership_id="OM-SF-MC5"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-MC5",
                "BM-SF-MC5",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
                baseline_loa_m=10.50,
                baseline_rudder_support="skeg",
            )
            _admit_design_keel_and_draft(
                conn,
                "BD-SF-MC5",
                keel_type="fin",
                draft_max_m=Decimal("1.30"),
                loa_m=Decimal("10.50"),
                rudder_support="skeg",
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-MC5",
            org_id="ORG-SF-MC5",
            account_id="ACC-SF-MC5",
            membership_id="OM-SF-MC5",
            physical_boat_id="PB-SF-MC5",
            market_episode_id="ME-SF-MC5",
            boat_design_id="BD-SF-MC5",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-MC5",
            org_id="ORG-SF-MC5",
            account_id="ACC-SF-MC5",
            revision_id="PBCREV-SF-MC5",
            draft=_draft_value("1.20"),
            keel_configuration=_keel_value("FIN"),
            loa_length=_loa_value("10.50"),
            rudder_configuration=_rudder_value("SKEG_HUNG"),
        )
        _log_in(client, "ACC-SF-MC5")
        response = client.get(
            _search_fit_path("ORG-SF-MC5", "NL-SF-MC5"),
            params={
                "draft_max": "1.5",
                "keel_configuration": "FIN",
                "loa_min": "10",
                "loa_max": "11",
                "rudder_configuration": "SKEG_HUNG",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_MATCH"
        assert body["blockers"] == []
        assert body["active_requirement"] == {
            "draft_max": "1.5",
            "keel_configuration": "FIN",
            "loa_min": "10",
            "loa_max": "11",
            "rudder_configuration": "SKEG_HUNG",
        }
        fields = {ce["field"] for ce in body["criterion_evidence"]}
        assert fields == {"draft_max_m", "keel_configuration", "loa_m", "rudder_configuration"}

        # Mechanical invariant: lifecycle-DRAFT preview never leaks into the
        # accepted public technical Search while still DRAFT.
        public_search = client.get(
            "/api/search/en",
            # Accepted canonical key order (draft_max, keel_configuration,
            # loa_max, loa_min, rudder_configuration) -- httpx serializes a
            # dict's params in insertion order, so this must already be
            # canonical to reach 200 directly rather than a 308 redirect.
            params={
                "draft_max": "1.5",
                "keel_configuration": "FIN",
                "loa_max": "11",
                "loa_min": "10",
                "rudder_configuration": "SKEG_HUNG",
            },
        )
        assert public_search.status_code == 200
        assert public_search.json()["confirmed_match_count"] == 0

    def test_loa_concrete_value_outside_range_is_confirmed_non_match(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-MC6", account_id="ACC-SF-MC6", membership_id="OM-SF-MC6"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn, "BD-SF-MC6", "BM-SF-MC6", baseline_keel_type="fin", baseline_loa_m=12.00
            )
            _admit_design_keel_and_draft(conn, "BD-SF-MC6", keel_type="fin", loa_m=Decimal("12.00"))
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-MC6",
            org_id="ORG-SF-MC6",
            account_id="ACC-SF-MC6",
            membership_id="OM-SF-MC6",
            physical_boat_id="PB-SF-MC6",
            market_episode_id="ME-SF-MC6",
            boat_design_id="BD-SF-MC6",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-MC6",
            org_id="ORG-SF-MC6",
            account_id="ACC-SF-MC6",
            revision_id="PBCREV-SF-MC6",
            loa_length=_loa_value("20.00"),
        )
        _log_in(client, "ACC-SF-MC6")
        response = client.get(
            _search_fit_path("ORG-SF-MC6", "NL-SF-MC6"),
            params={"loa_min": "10", "loa_max": "15"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_NON_MATCH"
        assert body["blockers"] == []


# ---------------------------------------------------------------------------
# NOT_PREVIEWABLE / chain integrity / zero writes
# ---------------------------------------------------------------------------


class TestSearchFitLifecycleAndIntegrity:
    def test_active_listing_is_not_previewable(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-SF-ACTIVE",
            account_id="ACC-SF-ACTIVE",
            membership_id="OM-SF-ACTIVE",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-ACTIVE",
                "BM-SF-ACTIVE",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-ACTIVE", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-ACTIVE",
            org_id="ORG-SF-ACTIVE",
            account_id="ACC-SF-ACTIVE",
            membership_id="OM-SF-ACTIVE",
            physical_boat_id="PB-SF-ACTIVE",
            market_episode_id="ME-SF-ACTIVE",
            boat_design_id="BD-SF-ACTIVE",
        )
        account = AccountId("ACC-SF-ACTIVE")
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId("ORG-SF-ACTIVE"),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId("OM-SF-ACTIVE"),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        conn = psycopg.connect(api_url)
        try:
            write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-SF-ACTIVE"),
                revision_id=NativeListingOfferRevisionId("REV-SF-ACTIVE"),
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
                native_listing_id=NativeListingId("NL-SF-ACTIVE"),
                revision_id=PhysicalBoatClaimRevisionId("PBCREV-SF-ACTIVE"),
                expected_current_revision_id=None,
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 30.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021
                    ),
                    draft=_draft_value("1.20"),
                    keel_configuration=_keel_value("FIN"),
                ),
            )
            with conn.transaction():
                with conn.cursor() as cur:
                    cur.execute(
                        "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                        [account.value],
                    )
                asset = insert_approved_media_asset(
                    conn,
                    owner_organization_id=org.id,
                    uploaded_by_account_id=account,
                    rights_declared=True,
                    source_kind=MediaSourceKind.BROKER_UPLOAD,
                    source_reference=None,
                    original_object_key="original/NL-SF-ACTIVE",
                    derivative_object_key="derivative/NL-SF-ACTIVE",
                    content_hash="hash-NL-SF-ACTIVE",
                    mime_type="image/jpeg",
                    width=800,
                    height=600,
                    byte_size=12345,
                )
                placement_result = create_uploaded_image_placement(
                    conn,
                    native_listing_id=NativeListingId("NL-SF-ACTIVE"),
                    owner_organization_id=org.id,
                    media_asset=asset,
                )
                assert placement_result.media_placement_id is not None
                assert placement_result.gallery_version is not None
                set_cover(
                    conn,
                    native_listing_id=NativeListingId("NL-SF-ACTIVE"),
                    owner_organization_id=org.id,
                    media_placement_id=placement_result.media_placement_id,
                    expected_version=placement_result.gallery_version,
                )
            publish_result = publish_native_listing(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("NL-SF-ACTIVE"),
            )
            assert publish_result.status.value == "transitioned", publish_result
        finally:
            conn.close()

        _log_in(client, "ACC-SF-ACTIVE")
        response = client.get(
            _search_fit_path("ORG-SF-ACTIVE", "NL-SF-ACTIVE"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 409
        assert response.json()["error"] == "not_previewable"

        # Required Behavior: the now-published listing's identical synthetic
        # facts yield the same technical truth through the public Search path.
        public_search = client.get("/api/search/en", params={"draft_max": "1.5"})
        assert public_search.status_code == 200
        matches = public_search.json()["confirmed_matches"]
        assert any(m["native_listing_id"] == "NL-SF-ACTIVE" for m in matches)

    def test_dangling_boat_design_ref_is_chain_integrity_fault(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-SF-DANGLE",
            account_id="ACC-SF-DANGLE",
            membership_id="OM-SF-DANGLE",
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-DANGLE",
            org_id="ORG-SF-DANGLE",
            account_id="ACC-SF-DANGLE",
            membership_id="OM-SF-DANGLE",
            physical_boat_id="PB-SF-DANGLE",
            market_episode_id="ME-SF-DANGLE",
        )
        # The real `fk_physical_boats_boat_design_ref` constraint makes a
        # genuinely dangling stored reference unreachable through the normal
        # write path (`create_physical_boat` fails closed to DESIGN_NOT_FOUND
        # instead of ever persisting it) -- simulate the orphaned-data
        # integrity fault this slice's mechanical invariants still require to
        # fail closed (e.g. a historical data-repair gap), by dropping the
        # constraint in this disposable per-test schema only.
        conn = psycopg.connect(api_url)
        try:
            with conn.transaction(), conn.cursor() as cur:
                cur.execute(
                    "ALTER TABLE physical_boats DROP CONSTRAINT fk_physical_boats_boat_design_ref"
                )
                cur.execute(
                    "UPDATE physical_boats SET boat_design_ref = %s WHERE physical_boat_id = %s",
                    ["BD-SF-DOES-NOT-EXIST", "PB-SF-DANGLE"],
                )
        finally:
            conn.close()
        _log_in(client, "ACC-SF-DANGLE")
        response = client.get(
            _search_fit_path("ORG-SF-DANGLE", "NL-SF-DANGLE"), params={"draft_max": "1.5"}
        )
        assert response.status_code == 503
        assert response.json()["error"] == "chain_integrity_fault"

    def test_preview_causes_zero_writes(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-SF-NOWRITE",
            account_id="ACC-SF-NOWRITE",
            membership_id="OM-SF-NOWRITE",
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-NOWRITE",
                "BM-SF-NOWRITE",
                baseline_keel_type="fin",
                baseline_draft_max_m=1.30,
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-NOWRITE", keel_type="fin", draft_max_m=Decimal("1.30")
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-NOWRITE",
            org_id="ORG-SF-NOWRITE",
            account_id="ACC-SF-NOWRITE",
            membership_id="OM-SF-NOWRITE",
            physical_boat_id="PB-SF-NOWRITE",
            market_episode_id="ME-SF-NOWRITE",
            boat_design_id="BD-SF-NOWRITE",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-NOWRITE",
            org_id="ORG-SF-NOWRITE",
            account_id="ACC-SF-NOWRITE",
            revision_id="PBCREV-SF-NOWRITE",
            draft=_draft_value("1.20"),
            keel_configuration=_keel_value("FIN"),
        )
        _log_in(client, "ACC-SF-NOWRITE")

        fingerprint_before = _capture_write_fingerprint(
            api_url,
            native_listing_id="NL-SF-NOWRITE",
            physical_boat_id="PB-SF-NOWRITE",
            organization_id="ORG-SF-NOWRITE",
        )

        # Repeated, idempotent GETs -- never a write, never a stale/changed
        # answer for unchanged authoritative state.
        for _ in range(2):
            response = client.get(
                _search_fit_path("ORG-SF-NOWRITE", "NL-SF-NOWRITE"),
                params={"draft_max": "1.5", "keel_configuration": "FIN"},
            )
            assert response.status_code == 200
            assert response.json()["result_class"] == "CONFIRMED_MATCH"

        fingerprint_after = _capture_write_fingerprint(
            api_url,
            native_listing_id="NL-SF-NOWRITE",
            physical_boat_id="PB-SF-NOWRITE",
            organization_id="ORG-SF-NOWRITE",
        )

        # Independent review proof-completeness note (PR #342): every
        # write destination this preview could conceivably touch --
        # lifecycle, the current claim head, the full claim revision
        # history count, the listing's own identity columns, the stored
        # design reference, publication-transition audit rows, offer
        # revisions, design-association audit events, buyer Leads and
        # FieldResolution admission -- is bit-for-bit unchanged.
        assert fingerprint_after == fingerprint_before


# ---------------------------------------------------------------------------
# SLICE-0086: hull_configuration / cockpit_position / deck_saloon scenario
# ---------------------------------------------------------------------------


class TestSearchFitSlice0086Facets:
    def test_confirmed_match_all_three_new_facets_combined(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-S86A", account_id="ACC-SF-S86A", membership_id="OM-SF-S86A"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-S86A",
                "BM-SF-S86A",
                baseline_keel_type="fin",
                baseline_hull_configuration="catamaran",
                baseline_cockpit_position="center",
                baseline_deck_saloon="deck_saloon",
            )
            _admit_design_keel_and_draft(
                conn,
                "BD-SF-S86A",
                keel_type="fin",
                hull_configuration="catamaran",
                cockpit_position="center",
                deck_saloon="deck_saloon",
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-S86A",
            org_id="ORG-SF-S86A",
            account_id="ACC-SF-S86A",
            membership_id="OM-SF-S86A",
            physical_boat_id="PB-SF-S86A",
            market_episode_id="ME-SF-S86A",
            boat_design_id="BD-SF-S86A",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-S86A",
            org_id="ORG-SF-S86A",
            account_id="ACC-SF-S86A",
            revision_id="PBCREV-SF-S86A",
            hull_configuration=_hull_value("CATAMARAN"),
            cockpit_position=_cockpit_value("CENTER"),
            deck_saloon=_deck_saloon_value("DECK_SALOON"),
        )
        _log_in(client, "ACC-SF-S86A")
        response = client.get(
            _search_fit_path("ORG-SF-S86A", "NL-SF-S86A"),
            params={
                "hull_configuration": "CATAMARAN",
                "cockpit_position": "CENTER",
                "deck_saloon": "DECK_SALOON",
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_MATCH"
        assert body["blockers"] == []
        assert body["active_requirement"] == {
            "cockpit_position": "CENTER",
            "deck_saloon": "DECK_SALOON",
            "hull_configuration": "CATAMARAN",
        }
        fields = {ce["field"] for ce in body["criterion_evidence"]}
        assert fields == {"cockpit_position", "deck_saloon", "hull_configuration"}

    def test_insufficient_data_produces_hull_configuration_unconfirmed_blocker(
        self, client: TestClient, api_url: str
    ) -> None:
        """The design side is CONFIRMED_MATCH for hull_configuration, but the
        broker's own concrete claim never confirms it -- INSUFFICIENT_DATA
        with the exact actionable blocker, never a false CONFIRMED_MATCH."""
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-S86B", account_id="ACC-SF-S86B", membership_id="OM-SF-S86B"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-S86B",
                "BM-SF-S86B",
                baseline_keel_type="fin",
                baseline_hull_configuration="catamaran",
            )
            _admit_design_keel_and_draft(
                conn, "BD-SF-S86B", keel_type="fin", hull_configuration="catamaran"
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-S86B",
            org_id="ORG-SF-S86B",
            account_id="ACC-SF-S86B",
            membership_id="OM-SF-S86B",
            physical_boat_id="PB-SF-S86B",
            market_episode_id="ME-SF-S86B",
            boat_design_id="BD-SF-S86B",
        )
        # Deliberately no _write_claim call for hull_configuration: the
        # broker's own concrete claim stays unconfirmed.
        _log_in(client, "ACC-SF-S86B")
        response = client.get(
            _search_fit_path("ORG-SF-S86B", "NL-SF-S86B"),
            params={"hull_configuration": "CATAMARAN"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["HULL_CONFIGURATION_UNCONFIRMED"]

    def test_invalid_deck_saloon_none_scenario_value_400(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-S86C", account_id="ACC-SF-S86C", membership_id="OM-SF-S86C"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-S86C",
            org_id="ORG-SF-S86C",
            account_id="ACC-SF-S86C",
            membership_id="OM-SF-S86C",
            physical_boat_id="PB-SF-S86C",
            market_episode_id="ME-SF-S86C",
        )
        _log_in(client, "ACC-SF-S86C")
        # NONE is a real claim value but never an accepted public Search-fit
        # scenario value.
        response = client.get(
            _search_fit_path("ORG-SF-S86C", "NL-SF-S86C"), params={"deck_saloon": "NONE"}
        )
        assert response.status_code == 400


# ---------------------------------------------------------------------------
# SLICE-0087: beam / hull_material
# ---------------------------------------------------------------------------


class TestSearchFitSlice0087Facets:
    def test_confirmed_match_beam_and_hull_material_combined(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-S87A", account_id="ACC-SF-S87A", membership_id="OM-SF-S87A"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-S87A",
                "BM-SF-S87A",
                baseline_keel_type="fin",
                baseline_beam_m=3.80,
                baseline_hull_material="grp_fiberglass",
            )
            _admit_design_keel_and_draft(
                conn,
                "BD-SF-S87A",
                keel_type="fin",
                beam_m=Decimal("3.80"),
                hull_material="grp_fiberglass",
            )
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-S87A",
            org_id="ORG-SF-S87A",
            account_id="ACC-SF-S87A",
            membership_id="OM-SF-S87A",
            physical_boat_id="PB-SF-S87A",
            market_episode_id="ME-SF-S87A",
            boat_design_id="BD-SF-S87A",
        )
        _write_claim(
            api_url,
            listing_id="NL-SF-S87A",
            org_id="ORG-SF-S87A",
            account_id="ACC-SF-S87A",
            revision_id="PBCREV-SF-S87A",
            beam=_beam_value(Decimal("3.80")),
            hull_material=_hull_material_value("GRP_FIBERGLASS"),
        )
        _log_in(client, "ACC-SF-S87A")
        response = client.get(
            _search_fit_path("ORG-SF-S87A", "NL-SF-S87A"),
            params={"beam_min": "3.2", "beam_max": "4.4", "hull_material": "GRP_FIBERGLASS"},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "CONFIRMED_MATCH"
        assert body["blockers"] == []
        assert body["active_requirement"] == {
            "beam_max": "4.4",
            "beam_min": "3.2",
            "hull_material": "GRP_FIBERGLASS",
        }
        fields = {ce["field"] for ce in body["criterion_evidence"]}
        assert fields == {"beam_m", "hull_material"}

    def test_insufficient_data_produces_hull_material_unconfirmed_blocker(
        self, client: TestClient, api_url: str
    ) -> None:
        """The design side is CONFIRMED_MATCH for hull_material, but the
        broker's own concrete claim never confirms it -- INSUFFICIENT_DATA
        with the exact actionable blocker, never a false CONFIRMED_MATCH."""
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-S87B", account_id="ACC-SF-S87B", membership_id="OM-SF-S87B"
        )
        conn = psycopg.connect(api_url)
        try:
            _insert_boat_design(
                conn,
                "BD-SF-S87B",
                "BM-SF-S87B",
                baseline_keel_type="fin",
                baseline_hull_material="steel",
            )
            _admit_design_keel_and_draft(conn, "BD-SF-S87B", keel_type="fin", hull_material="steel")
        finally:
            conn.close()
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-S87B",
            org_id="ORG-SF-S87B",
            account_id="ACC-SF-S87B",
            membership_id="OM-SF-S87B",
            physical_boat_id="PB-SF-S87B",
            market_episode_id="ME-SF-S87B",
            boat_design_id="BD-SF-S87B",
        )
        # Deliberately no _write_claim call for hull_material: the broker's
        # own concrete claim stays unconfirmed.
        _log_in(client, "ACC-SF-S87B")
        response = client.get(
            _search_fit_path("ORG-SF-S87B", "NL-SF-S87B"), params={"hull_material": "STEEL"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["result_class"] == "INSUFFICIENT_DATA"
        assert body["blockers"] == ["HULL_MATERIAL_UNCONFIRMED"]

    def test_invalid_hull_material_ferrocement_scenario_value_400(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SF-S87C", account_id="ACC-SF-S87C", membership_id="OM-SF-S87C"
        )
        _create_draft_listing(
            api_url,
            listing_id="NL-SF-S87C",
            org_id="ORG-SF-S87C",
            account_id="ACC-SF-S87C",
            membership_id="OM-SF-S87C",
            physical_boat_id="PB-SF-S87C",
            market_episode_id="ME-SF-S87C",
        )
        _log_in(client, "ACC-SF-S87C")
        # FERROCEMENT is a real claim value but never an accepted public
        # Search-fit scenario value.
        response = client.get(
            _search_fit_path("ORG-SF-S87C", "NL-SF-S87C"), params={"hull_material": "FERROCEMENT"}
        )
        assert response.status_code == 400
