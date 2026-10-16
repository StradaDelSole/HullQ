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

    def test_revoked_membership_is_denied(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-REVOKED",
            account_id="ACC-EXP-REVOKED",
            membership_id="MEM-EXP-REVOKED",
            state=MembershipState.INACTIVE,
        )
        _log_in(client, "ACC-EXP-REVOKED")
        response = client.post(
            "/api/broker/organizations/ORG-EXP-REVOKED/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": []},
            headers=_EXPORT_CSRF_HEADER,
        )
        # Contract: a revoked (INACTIVE) membership and no membership at all
        # are indistinguishable -- no existence oracle.
        assert response.status_code == 404

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
        preflight_body = preflight.json()
        fingerprint = preflight_body["snapshot_fingerprint"]
        assert isinstance(fingerprint, str) and fingerprint
        rows = preflight_body["rows"]
        assert len(rows) == 2
        draft_row, listing_row = rows[0], rows[1]
        # Required Behavior: "Return stable listing identifiers ... in the
        # preview" -- the broker must be able to tell which row is which.
        assert draft_row["export_id"] == f"ORG-EXP-FULL:draft:{draft_id}"
        assert draft_row["source_kind"] == "PRIVATE_DRAFT"
        assert listing_row["export_id"] == "ORG-EXP-FULL:listing:LIST-EXP-FULL"
        assert listing_row["source_kind"] == "PROMOTED_LISTING"
        assert draft_row["formats"]["NAUTIX"]["exportable"] is False
        # Without a broker-confirmed NautixExportProfile, sale_class AND
        # the destination account_token/office_id are all honestly absent
        # -- never fabricated from the HullQ Organization id or a
        # placeholder (independent review amendment, 2026-10-16).
        assert listing_row["formats"]["NAUTIX"]["exportable"] is False
        listing_nautix_reasons = listing_row["formats"]["NAUTIX"]["reasons"]
        assert any("sale_class" in r for r in listing_nautix_reasons)
        assert any("account.token" in r for r in listing_nautix_reasons)
        assert any("office_id" in r for r in listing_nautix_reasons)
        assert any("formula-injection" in w for w in draft_row["formats"]["CSV"]["warnings"])

        for fmt, magic in (
            ("CSV", b"export_id"),
            ("TSV", b"export_id"),
            ("JSON", b'{"listings"'),
            ("XLSX", b"PK"),
            ("XLS", b"\xd0\xcf\x11\xe0"),
            ("ODS", b"PK"),
        ):
            download = client.post(
                "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
                json={**selection, "format": fmt, "expected_snapshot_fingerprint": fingerprint},
                headers=_EXPORT_CSRF_HEADER,
            )
            assert download.status_code == 200, (fmt, download.text)
            assert download.content.startswith(magic), fmt
            assert "attachment" in download.headers["content-disposition"]
            assert "no-store" in download.headers["cache-control"]
            assert download.headers["x-hullq-export-included-count"] == "2"
            assert download.headers["x-hullq-export-rejected-count"] == "0"
            if fmt in ("CSV", "TSV"):
                assert b",=2+2" not in download.content
                assert b"'=2+2" in download.content

        # Without a profile, *no* row is NautiX-exportable -- Required
        # Behavior: never a successful complete download that silently
        # skips every selected listing.
        no_profile_nautix = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
            json={**selection, "format": "NAUTIX", "expected_snapshot_fingerprint": fingerprint},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert no_profile_nautix.status_code == 422
        assert no_profile_nautix.json()["error"] == "no_exportable_rows"

        # With a broker-confirmed profile, the listing (never the private
        # draft) becomes genuinely NautiX-exportable -- the real positive
        # end-to-end path, not just the domain-unit synthetic fixture. The
        # profile itself is bound into the snapshot fingerprint (it
        # populates export-relevant row fields), so a fresh preflight
        # observation *with* this exact profile is required first --
        # reusing the no-profile fingerprint would correctly be rejected
        # as stale.
        nautix_profile = {
            "account_token": "BROKER-ACCT-REAL-1",
            "office_id": "OFFICE-REAL-1",
            "sale_classes": {"LIST-EXP-FULL": "used"},
        }
        profiled_preflight = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/preflight",
            json={**selection, "nautix_profile": nautix_profile},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert profiled_preflight.status_code == 200, profiled_preflight.text
        profiled_fingerprint = profiled_preflight.json()["snapshot_fingerprint"]
        assert isinstance(profiled_fingerprint, str) and profiled_fingerprint
        assert profiled_fingerprint != fingerprint
        with_profile_nautix = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
            json={
                **selection,
                "format": "NAUTIX",
                "nautix_profile": nautix_profile,
                "expected_snapshot_fingerprint": profiled_fingerprint,
            },
            headers=_EXPORT_CSRF_HEADER,
        )
        assert with_profile_nautix.status_code == 200, with_profile_nautix.text
        assert with_profile_nautix.content.startswith(b"<?xml")
        assert with_profile_nautix.headers["x-hullq-export-included-count"] == "1"
        assert with_profile_nautix.headers["x-hullq-export-rejected-count"] == "1"
        root = parse_and_validate_nautix(with_profile_nautix.content)
        mapped = map_nautix_adverts_to_rows(
            root, attested_account_tokens=frozenset({"BROKER-ACCT-REAL-1"})
        )
        assert len(mapped) == 1
        assert mapped[0].classification.value == "VALID", mapped[0].reasons

        # An invalid sale_class value is rejected closed, not silently
        # dropped.
        bad_profile = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
            json={
                **selection,
                "format": "NAUTIX",
                "nautix_profile": {**nautix_profile, "sale_classes": {"LIST-EXP-FULL": "mint"}},
                # Invalid-profile rejection happens before the fingerprint
                # comparison (see get_export_download) -- any non-empty
                # value satisfies the mandatory-fingerprint precondition so
                # this test isolates the profile-validation failure.
                "expected_snapshot_fingerprint": profiled_fingerprint,
            },
            headers=_EXPORT_CSRF_HEADER,
        )
        assert bad_profile.status_code == 400
        assert bad_profile.json()["error"] == "invalid_nautix_profile"

        # A stale fingerprint (the data changed since this preflight) is
        # rejected closed rather than silently downloading current data
        # under cover of an old confirmation.
        stale_download = client.post(
            "/api/broker/organizations/ORG-EXP-FULL/inventory/export/download",
            json={
                **selection,
                "format": "CSV",
                "expected_snapshot_fingerprint": "not-the-real-one",
            },
            headers=_EXPORT_CSRF_HEADER,
        )
        assert stale_download.status_code == 409
        assert stale_download.json()["error"] == "stale_selection"

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


class TestInventoryExportStalenessOnRealDataChange:
    """Independent review Finding A: the snapshot fingerprint must bind
    *every* export-relevant field, not only identity/status/timestamp.
    Each test here confirms -- against the real database, not a synthetic
    domain-unit fixture -- that a genuine change of exactly one such field
    between preflight and download is rejected closed as
    `STALE_SELECTION`, never silently downloaded under the stale
    confirmation."""

    def _preflight_fingerprint(
        self, client: TestClient, org_id: str, selection: dict[str, Any]
    ) -> str:
        preflight = client.post(
            f"/api/broker/organizations/{org_id}/inventory/export/preflight",
            json=selection,
            headers=_EXPORT_CSRF_HEADER,
        )
        assert preflight.status_code == 200, preflight.text
        fingerprint = preflight.json()["snapshot_fingerprint"]
        assert isinstance(fingerprint, str) and fingerprint
        return fingerprint

    def test_offer_price_change_after_preflight_is_stale(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-PRICE",
            account_id="ACC-EXP-PRICE",
            membership_id="MEM-EXP-PRICE",
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-PRICE",
            account_id="ACC-EXP-PRICE",
            org_id="ORG-EXP-PRICE",
            membership_id="MEM-EXP-PRICE",
            physical_boat_id="PB-EXP-PRICE",
            market_episode_id="ME-EXP-PRICE",
        )
        _log_in(client, "ACC-EXP-PRICE")
        selection = {"draft_ids": [], "native_listing_ids": ["LIST-EXP-PRICE"]}
        fingerprint = self._preflight_fingerprint(client, "ORG-EXP-PRICE", selection)

        conn = psycopg.connect(api_url)
        try:
            account = AccountId("ACC-EXP-PRICE")
            org = _org_domain("ORG-EXP-PRICE")
            membership = _membership_domain("MEM-EXP-PRICE", "ACC-EXP-PRICE", "ORG-EXP-PRICE")
            offer_result = write_native_listing_offer_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("LIST-EXP-PRICE"),
                revision_id=NativeListingOfferRevisionId("OFFER-LIST-EXP-PRICE-2"),
                expected_current_revision_id=NativeListingOfferRevisionId("OFFER-LIST-EXP-PRICE"),
                offer=NativeListingOfferSnapshot(
                    asking_price_mode=AskingPriceMode.AMOUNT,
                    location_country="FR",
                    broker_description="A well-maintained cruising sloop = great value",
                    asking_price_amount=Decimal("99000.00"),
                    currency="EUR",
                ),
            )
            assert offer_result.status.value in ("created", "already_exists", "revised"), (
                offer_result
            )
            conn.commit()
        finally:
            conn.close()

        download = client.post(
            "/api/broker/organizations/ORG-EXP-PRICE/inventory/export/download",
            json={**selection, "format": "CSV", "expected_snapshot_fingerprint": fingerprint},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert download.status_code == 409, download.text
        assert download.json()["error"] == "stale_selection"

    def test_claim_change_after_preflight_is_stale(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-CLAIM",
            account_id="ACC-EXP-CLAIM",
            membership_id="MEM-EXP-CLAIM",
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-CLAIM",
            account_id="ACC-EXP-CLAIM",
            org_id="ORG-EXP-CLAIM",
            membership_id="MEM-EXP-CLAIM",
            physical_boat_id="PB-EXP-CLAIM",
            market_episode_id="ME-EXP-CLAIM",
        )
        _log_in(client, "ACC-EXP-CLAIM")
        selection = {"draft_ids": [], "native_listing_ids": ["LIST-EXP-CLAIM"]}
        fingerprint = self._preflight_fingerprint(client, "ORG-EXP-CLAIM", selection)

        conn = psycopg.connect(api_url)
        try:
            account = AccountId("ACC-EXP-CLAIM")
            org = _org_domain("ORG-EXP-CLAIM")
            membership = _membership_domain("MEM-EXP-CLAIM", "ACC-EXP-CLAIM", "ORG-EXP-CLAIM")
            claim_result = write_physical_boat_claim_revision(
                conn,
                account_id=account,
                candidate_organization=org,
                membership=membership,
                native_listing_id=NativeListingId("LIST-EXP-CLAIM"),
                revision_id=PhysicalBoatClaimRevisionId("CLAIM-LIST-EXP-CLAIM-2"),
                expected_current_revision_id=PhysicalBoatClaimRevisionId("CLAIM-LIST-EXP-CLAIM"),
                claims=PhysicalBoatClaimSnapshot(
                    marketed_brand_claim="Beneteau",
                    model_designation_claim="Oceanis 35.1",
                    build_year=BuildYearClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=2022
                    ),
                    loa_length=LoaLengthClaim(
                        assertion_kind=AssertionKind.VALUE_ASSERTION, value=Decimal("10.70")
                    ),
                ),
            )
            assert claim_result.status.value in ("created", "already_exists", "revised"), (
                claim_result
            )
            conn.commit()
        finally:
            conn.close()

        download = client.post(
            "/api/broker/organizations/ORG-EXP-CLAIM/inventory/export/download",
            json={**selection, "format": "CSV", "expected_snapshot_fingerprint": fingerprint},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert download.status_code == 409, download.text
        assert download.json()["error"] == "stale_selection"

    def test_media_change_after_preflight_is_stale(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-MEDIA",
            account_id="ACC-EXP-MEDIA",
            membership_id="MEM-EXP-MEDIA",
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-MEDIA",
            account_id="ACC-EXP-MEDIA",
            org_id="ORG-EXP-MEDIA",
            membership_id="MEM-EXP-MEDIA",
            physical_boat_id="PB-EXP-MEDIA",
            market_episode_id="ME-EXP-MEDIA",
        )
        _log_in(client, "ACC-EXP-MEDIA")
        selection = {"draft_ids": [], "native_listing_ids": ["LIST-EXP-MEDIA"]}
        fingerprint = self._preflight_fingerprint(client, "ORG-EXP-MEDIA", selection)

        conn = psycopg.connect(api_url)
        try:
            org = _org_domain("ORG-EXP-MEDIA")
            account = AccountId("ACC-EXP-MEDIA")
            with conn.transaction():
                asset = insert_approved_media_asset(
                    conn,
                    owner_organization_id=org.id,
                    uploaded_by_account_id=account,
                    rights_declared=True,
                    source_kind=MediaSourceKind.BROKER_UPLOAD,
                    source_reference=None,
                    original_object_key="original/LIST-EXP-MEDIA-2",
                    derivative_object_key="derivative/LIST-EXP-MEDIA-2",
                    content_hash="e4d909c290d0fb1ca068ffaddf22cbd0",
                    mime_type="image/jpeg",
                    width=800,
                    height=600,
                    byte_size=12345,
                )
                placement_result = create_uploaded_image_placement(
                    conn,
                    native_listing_id=NativeListingId("LIST-EXP-MEDIA"),
                    owner_organization_id=org.id,
                    media_asset=asset,
                )
                assert placement_result.media_placement_id is not None
            conn.commit()
        finally:
            conn.close()

        download = client.post(
            "/api/broker/organizations/ORG-EXP-MEDIA/inventory/export/download",
            json={**selection, "format": "CSV", "expected_snapshot_fingerprint": fingerprint},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert download.status_code == 409, download.text
        assert download.json()["error"] == "stale_selection"


class TestInventoryExportCrossOrganizationIsolation:
    """A `PhysicalBoat` may legitimately be referenced by more than one
    Organization's own `MarketEpisode` (independent review: a dedicated
    shared-PhysicalBoat negative fixture). Each Organization's own claim
    facts for that shared hull must never leak into the other's export --
    `fetch_current_physical_boat_claim` is scoped by `organization_id`, and
    this test proves that scoping holds through the real export route, not
    merely by code inspection."""

    def test_shared_physical_boat_claims_do_not_cross_tenant_boundary(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-SHARE-A", account_id="ACC-EXP-SHARE-A", membership_id="MEM-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-EXP-SHARE-B", account_id="ACC-EXP-SHARE-B", membership_id="MEM-B"
        )

        conn = psycopg.connect(api_url)
        try:
            shared_physical_boat_id = PhysicalBoatId("PB-SHARED")
            create_physical_boat(conn, physical_boat=PhysicalBoat(id=shared_physical_boat_id))
            conn.commit()
        finally:
            conn.close()

        for org_id, account_id, membership_id, listing_id, episode_id, brand in (
            (
                "ORG-EXP-SHARE-A",
                "ACC-EXP-SHARE-A",
                "MEM-A",
                "LIST-SHARE-A",
                "ME-SHARE-A",
                "Beneteau",
            ),
            (
                "ORG-EXP-SHARE-B",
                "ACC-EXP-SHARE-B",
                "MEM-B",
                "LIST-SHARE-B",
                "ME-SHARE-B",
                "Jeanneau",
            ),
        ):
            conn = psycopg.connect(api_url)
            try:
                account = AccountId(account_id)
                org = _org_domain(org_id)
                membership = _membership_domain(membership_id, account_id, org_id)
                create_market_episode(
                    conn,
                    market_episode=MarketEpisode(
                        id=MarketEpisodeId(episode_id), physical_boat_id=shared_physical_boat_id
                    ),
                )
                result = create_native_listing(
                    conn,
                    account_id=account,
                    candidate_organization=org,
                    membership=membership,
                    listing=NativeListing(
                        id=NativeListingId(listing_id),
                        market_episode_id=MarketEpisodeId(episode_id),
                    ),
                    broker_listing_reference="REF-SHARE",
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
                        broker_description="Shared hull, tenant-owned claim",
                        asking_price_amount=Decimal("50000.00"),
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
                        marketed_brand_claim=brand,
                        model_designation_claim="Shared Hull Model",
                        build_year=BuildYearClaim(
                            assertion_kind=AssertionKind.VALUE_ASSERTION, value=2020
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

        _log_in(client, "ACC-EXP-SHARE-A")
        preflight_a = client.post(
            "/api/broker/organizations/ORG-EXP-SHARE-A/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": ["LIST-SHARE-A"]},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert preflight_a.status_code == 200, preflight_a.text
        rows_a = preflight_a.json()["rows"]
        assert len(rows_a) == 1
        assert rows_a[0]["field_states"]["physical_boat.marketed_brand_claim"] == "PRESENT"

        fingerprint_a = preflight_a.json()["snapshot_fingerprint"]
        download_a = client.post(
            "/api/broker/organizations/ORG-EXP-SHARE-A/inventory/export/download",
            json={
                "draft_ids": [],
                "native_listing_ids": ["LIST-SHARE-A"],
                "format": "JSON",
                "expected_snapshot_fingerprint": fingerprint_a,
            },
            headers=_EXPORT_CSRF_HEADER,
        )
        assert download_a.status_code == 200, download_a.text
        assert b"Beneteau" in download_a.content
        assert b"Jeanneau" not in download_a.content

        # Org A must never be able to select/preview Org B's own listing
        # merely because the two listings' underlying hull is the same
        # PhysicalBoat -- the tenant boundary is the Organization, not the
        # hull.
        cross_preflight = client.post(
            "/api/broker/organizations/ORG-EXP-SHARE-A/inventory/export/preflight",
            json={"draft_ids": [], "native_listing_ids": ["LIST-SHARE-B"]},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert cross_preflight.status_code == 400
        assert cross_preflight.json()["error"] == "unknown_item"


class TestInventoryExportWriteAndDatabaseFailures:
    def test_write_failure_surfaces_as_export_write_failed(
        self, client: TestClient, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Induces a genuine writer failure via monkeypatch (there is no
        organic malformed-data path through the real, already-bounded/
        escaped writers) and confirms the real API route translates the
        domain `WRITE_FAILED` outcome to a real HTTP 500 `export_write_failed`
        response -- never a silently empty/truncated "successful" file."""
        _seed_org_and_membership(
            api_url,
            org_id="ORG-EXP-WRITEFAIL",
            account_id="ACC-EXP-WRITEFAIL",
            membership_id="MEM-EXP-WRITEFAIL",
        )
        _seed_full_active_listing(
            api_url,
            listing_id="LIST-EXP-WRITEFAIL",
            account_id="ACC-EXP-WRITEFAIL",
            org_id="ORG-EXP-WRITEFAIL",
            membership_id="MEM-EXP-WRITEFAIL",
            physical_boat_id="PB-EXP-WRITEFAIL",
            market_episode_id="ME-EXP-WRITEFAIL",
        )
        _log_in(client, "ACC-EXP-WRITEFAIL")
        selection = {"draft_ids": [], "native_listing_ids": ["LIST-EXP-WRITEFAIL"]}
        preflight = client.post(
            "/api/broker/organizations/ORG-EXP-WRITEFAIL/inventory/export/preflight",
            json=selection,
            headers=_EXPORT_CSRF_HEADER,
        )
        assert preflight.status_code == 200, preflight.text
        fingerprint = preflight.json()["snapshot_fingerprint"]

        from hullq.domain.inventory_export import ExportWriteError

        def _always_fail(*args: Any, **kwargs: Any) -> bytes:
            raise ExportWriteError("induced failure for test coverage")

        monkeypatch.setattr("hullq.application.inventory_export.write_csv", _always_fail)

        download = client.post(
            "/api/broker/organizations/ORG-EXP-WRITEFAIL/inventory/export/download",
            json={**selection, "format": "CSV", "expected_snapshot_fingerprint": fingerprint},
            headers=_EXPORT_CSRF_HEADER,
        )
        assert download.status_code == 500, download.text
        assert download.json()["error"] == "export_write_failed"

    def test_database_outage_fails_closed_not_fabricated_success(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Independent review: a genuine backend/database failure must
        surface as a real 5xx through the actual FastAPI route -- never a
        fabricated empty/zero/success result. Mirrors the existing
        `test_search_sensitivity_api.py` unreachable-database precedent:
        reserved port 1, nothing listens there, a guaranteed immediate
        connection failure."""
        monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
        from hullq.api.app import create_app

        unreachable_app = create_app(
            database_url="postgresql://hullq_test:hullq_test@127.0.0.1:1/hullq_test",
            preview_signing_secret=os.urandom(32),
            session_signing_secret=_SECRET,
            web_base_url="http://api.test",
            web_origin=_WEB_ORIGIN,
        )
        unreachable_client = TestClient(
            unreachable_app, base_url="http://api.test", raise_server_exceptions=False
        )
        try:
            unreachable_client.cookies.set(
                "hullq_session", _session_cookie("ACC-EXP-OUTAGE"), domain="api.test"
            )
            response = unreachable_client.post(
                "/api/broker/organizations/ORG-EXP-OUTAGE/inventory/export/preflight",
                json={"draft_ids": [], "native_listing_ids": []},
                headers=_EXPORT_CSRF_HEADER,
            )
            assert response.status_code >= 500
            assert response.status_code != 400
        finally:
            unreachable_client.close()
