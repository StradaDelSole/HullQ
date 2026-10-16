"""FastAPI integration tests for the SLICE-0088 broker inventory export routes.

Mirrors `test_broker_inventory_read_api.py`'s exact schema-isolation and
session-minting conventions. Covers the seven Owner-accepted formats
(CSV/TSV/XLSX/XLS/ODS/JSON/NautiX 1.4) end-to-end through the real HTTP
routes against a real PostgreSQL 18 instance: genuine format bytes,
NautiX pinned-XSD validation and 0083 reimport, tenant isolation,
PUBLISHER-role/MFA/CSRF enforcement, and formula-injection escaping.
"""

from __future__ import annotations

import os
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
from hullq.domain.import_nautix import map_nautix_adverts_to_rows, parse_and_validate_nautix
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
    LoaLengthClaim,
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
from hullq.persistence.broker_identity import (
    seed_marketplace_organization,
    seed_organization_membership,
)
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
from hullq.persistence.professional_listing_draft import create_professional_listing_draft
from hullq.security.session_token import mint_session_token

_SECRET = b"7" * 32
_WEB_ORIGIN = "http://web.test"
_EXPORT_CSRF_HEADER = {
    "Origin": _WEB_ORIGIN,
    "x-hullq-requested-with": "broker-inventory-export-v1",
}


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
    schema_name = f"hullq_s0088api_{uuid.uuid4().hex[:16]}"
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
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_base_url="http://api.test",
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


def _org_domain(org_id: str) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=MarketplaceOrganizationId(org_id),
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


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
        seed_marketplace_organization(conn, _org_domain(org_id))
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


def _membership_domain(membership_id: str, account_id: str, org_id: str) -> OrganizationMembership:
    return OrganizationMembership(
        id=OrganizationMembershipId(membership_id),
        account_id=AccountId(account_id),
        organization_id=MarketplaceOrganizationId(org_id),
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
            content_hash="d8e8fca2dc0f896fd7cb4cb0031ba249",
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
        assert placement_result.media_placement_id is not None
        assert placement_result.gallery_version is not None
        cover_result = set_cover(
            conn,
            native_listing_id=NativeListingId(listing_id),
            owner_organization_id=org.id,
            media_placement_id=placement_result.media_placement_id,
            expected_version=placement_result.gallery_version,
        )
        assert cover_result.outcome.value == "SET", cover_result


def _seed_full_active_listing(
    api_url: str,
    *,
    listing_id: str,
    account_id: str,
    org_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
) -> None:
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = _org_domain(org_id)
        membership = _membership_domain(membership_id, account_id, org_id)

        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(physical_boat_id)))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(market_episode_id),
                physical_boat_id=PhysicalBoatId(physical_boat_id),
            ),
        )
        result = create_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=NativeListingId(listing_id), market_episode_id=MarketEpisodeId(market_episode_id)
            ),
            broker_listing_reference="REF-EXPORT-1",
        )
        assert result.status.value in ("created", "already_exists"), result

        offer_result = write_native_listing_offer_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=NativeListingOfferRevisionId(f"OFFER-{listing_id}"),
            expected_current_revision_id=None,
            offer=NativeListingOfferSnapshot(
                asking_price_mode=AskingPriceMode.AMOUNT,
                location_country="FR",
                broker_description="A well-maintained cruising sloop = great value",
                asking_price_amount=Decimal("125000.00"),
                currency="EUR",
            ),
        )
        assert offer_result.status.value in ("created", "already_exists"), offer_result

        claim_result = write_physical_boat_claim_revision(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
            revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 30.1",
                build_year=BuildYearClaim(assertion_kind=AssertionKind.VALUE_ASSERTION, value=2021),
                loa_length=LoaLengthClaim(
                    assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("9.13")
                ),
            ),
        )
        assert claim_result.status.value in ("created", "already_exists"), claim_result

        _attach_ready_cover_image(conn, listing_id=listing_id, org=org, account=account)
        conn.commit()

        publish_result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert publish_result.status.value == "transitioned", publish_result
    finally:
        conn.close()


def _seed_private_draft(api_url: str, *, account_id: str, org_id: str) -> str:
    """Returns the server-generated draft_id."""
    conn = psycopg.connect(api_url)
    try:
        from hullq.domain.listing_draft_payload import parse_listing_draft_payload

        payload = parse_listing_draft_payload(
            {
                # Adversarial formula-injection payload -- must be escaped,
                # never executed, in every table-format download.
                "physical_boat.marketed_brand_claim": "=2+2",
                "physical_boat.model_designation_claim": "Draft Model",
            }
        )
        record = create_professional_listing_draft(
            conn,
            owner_organization_id=MarketplaceOrganizationId(org_id),
            created_by_account_id=AccountId(account_id),
            broker_listing_reference=None,
            payload=payload,
        )
        conn.commit()
        return record.draft_id.value
    finally:
        conn.close()


class TestInventoryExportAuthorizationBoundary:
    def test_unauthenticated_preflight_is_denied(self, client: TestClient) -> None:
        response = client.post(
            "/api/broker/organizations/ORG-EXP-UNAUTH/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 401

    def test_missing_csrf_header_is_denied(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-CSRF", account_id="ACC-EXP-CSRF", membership_id="MEM-EXP-CSRF"
        )
        _log_in(client, "ACC-EXP-CSRF")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-CSRF/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
        )
        assert response.status_code == 403

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-EXP-NEVER")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-NEVER-CREATED/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 404

    def test_member_without_publisher_role_is_denied(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-MEMBER",
            account_id="ACC-EXP-MEMBER",
            membership_id="MEM-EXP-MEMBER",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _log_in(client, "ACC-EXP-MEMBER")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-MEMBER/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 403
        assert response.json()["error"] == "publisher_role_required"

    def test_mfa_required_for_publisher(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-MFA", account_id="ACC-EXP-MFA", membership_id="MEM-EXP-MFA"
        )
        _log_in(client, "ACC-EXP-MFA", mfa=False)
        response = client.post(
            "/api/broker/organizations/ORG-EXP-MFA/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 403
        assert response.json()["error"] == "mfa_required"

    def test_empty_selection_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-EMPTY",
            account_id="ACC-EXP-EMPTY",
            membership_id="MEM-EXP-EMPTY",
        )
        _log_in(client, "ACC-EXP-EMPTY")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-EMPTY/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 400
        assert response.json()["error"] == "empty_selection"

    def test_oversize_selection_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-OVERSIZE",
            account_id="ACC-EXP-OVERSIZE",
            membership_id="MEM-EXP-OVERSIZE",
        )
        _log_in(client, "ACC-EXP-OVERSIZE")
        from hullq.domain.inventory_export import MAX_EXPORT_ROWS

        oversized_ids = [f"DRAFT-{i}" for i in range(MAX_EXPORT_ROWS + 1)]
        response = client.post(
            "/api/broker/organizations/ORG-EXP-OVERSIZE/inventory/export/preflight",
            json={"draft_ids": oversized_ids, "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 400
        assert response.json()["error"] == "oversize_selection"

    def test_foreign_organization_listing_is_unknown_item(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-A1", account_id="ACC-EXP-A1", membership_id="MEM-EXP-A1"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-B1", account_id="ACC-EXP-B1", membership_id="MEM-EXP-B1"
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-A1",
            account_id="ACC-EXP-A1",
            org_id="ORG-EXP-A1",
            membership_id="MEM-EXP-A1",
            physical_boat_id="PB-EXP-A1",
            market_episode_id="ME-EXP-A1",
        )
        _log_in(client, "ACC-EXP-B1")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-B1/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": ["LIST-EXP-A1"]},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 400
        assert response.json()["error"] == "unknown_item"


class TestInventoryExportFormats:
    def test_full_listing_and_draft_preflight_and_all_seven_formats(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-FULL", account_id="ACC-EXP-FULL", membership_id="MEM-EXP-FULL"
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-FULL",
            account_id="ACC-EXP-FULL",
            org_id="ORG-EXP-FULL",
            membership_id="MEM-EXP-FULL",
            physical_boat_id="PB-EXP-FULL",
            market_episode_id="ME-EXP-FULL",
        )
        draft_id = _seed_private_draft(api_url, account_id="ACC-EXP-FULL", org_id="ORG-EXP-FULL")
        _log_in(client, "ACC-EXP-FULL")

        selection = {"draft_ids": [draft_id], "native_listing_ids": ["LIST-EXP-FULL"]}

        preflight = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/preflight",
            json=selection,
            headers=_EXPORT_CSRF_HEADER,
        )
        assert preflight.status_code == 200, preflight.text
        rows = preflight.json()["rows"]
        assert len(rows) == 2
        draft_row, listing_row = rows[0], rows[1]
        assert draft_row["formats"]["NAUTIX"]["exportable"] is False
        # NautiX representability gap (by design, documented in
        # hullq.domain.inventory_export's module docstring): HullQ's
        # draft/offer schema has no new/used sale_class field, so even a
        # fully-populated real promoted listing is honestly NOT_EXPORTABLE
        # for NautiX -- never fabricated. Every *other* NautiX-mandatory
        # field (title/model/LOA/price/currency/location/photo) is present
        # on this fixture, so sale_class must be the only reported reason.
        assert listing_row["formats"]["NAUTIX"]["exportable"] is False
        assert listing_row["formats"]["NAUTIX"]["reasons"] == [
            "sale_data.sale_class: HullQ's draft/offer schema does not currently capture a "
            "new/used sale classification for this listing (never fabricated)"
        ]
        assert any("formula-injection" in w for w in draft_row["formats"]["CSV"]["warnings"])

        for fmt, magic in (
            ("CSV", b"export_id"),
            ("TSV", b"export_id"),
            ("JSON", b'{"listings"'),
            ("XLSX", b"PK"),
            ("XLS", b"\xd0\xcf\x11\xe0"),
            ("ODS", b"PK"),
            ("NAUTIX", b"<?xml"),
        ):
            download = client.post(
                "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
                json={**selection, "format": fmt},
                headers=_EXPORT_CSRF_HEADER,
            )
            assert download.status_code == 200, (fmt, download.text)
            assert download.content.startswith(magic), fmt
            assert "attachment" in download.headers["content-disposition"]
            assert "no-store" in download.headers["cache-control"]
            if fmt in ("CSV", "TSV"):
                assert b",=2+2" not in download.content
                assert b"'=2+2" in download.content

        # No row in this selection is actually NautiX-exportable (the
        # sale_class gap above applies to every real row), so the genuine,
        # pinned-XSD-valid document correctly contains zero <advert>
        # elements -- proving the writer never fabricates an advert for a
        # NOT_EXPORTABLE row, not that any real row succeeded. The direct
        # domain-level unit tests (test_inventory_export_domain.py) prove
        # the positive case against a hypothetically complete synthetic row.
        nautix_download = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
            json={**selection, "format": "NAUTIX"},
            headers=_EXPORT_CSRF_HEADER,
        )
        root = parse_and_validate_nautix(nautix_download.content)
        mapped = map_nautix_adverts_to_rows(
            root, attested_account_tokens=frozenset({"ORG-EXP-FULL"})
        )
        assert len(mapped) == 0

    def test_invalid_format_is_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-BADFMT",
            account_id="ACC-EXP-BADFMT",
            membership_id="MEM-EXP-BADFMT",
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-BADFMT",
            account_id="ACC-EXP-BADFMT",
            org_id="ORG-EXP-BADFMT",
            membership_id="MEM-EXP-BADFMT",
            physical_boat_id="PB-EXP-BADFMT",
            market_episode_id="ME-EXP-BADFMT",
        )
        _log_in(client, "ACC-EXP-BADFMT")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-BADFMT/inventory/export/download",
            json={"draft_ids": [], "native_listing_ids": ["LIST-EXP-BADFMT"], "format": "XLSB"},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert response.status_code == 400
        assert response.json()["error"] == "invalid_format"
