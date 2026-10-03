"""SLICE-0078 holistic adversarial security test suite.

Exercises the real FastAPI app (`hullq.api.app.create_app`) over Starlette's
`TestClient` against the actual accepted buyer/broker HTTP flows, per
`docs/governance/SECURITY_HARDENING_GATE.md`'s required adversarial E2E
proof (a scanner-only pass is explicitly insufficient).

This file deliberately does not re-derive the extensive per-feature
cross-tenant/CSRF coverage already present in `test_broker_workspace_
access_api.py`, `test_media_gallery_api.py`, `test_broker_lead_operations_
api.py`, `test_broker_sale_outcome_api.py` and similar files. It instead
adds:

1. a holistic cross-tenant sweep spanning every org-scoped read surface in
   one proof, covering both IDOR shapes -- "foreign organization_id in the
   path" and "own organization_id + another Organization's nested resource
   id" -- in one place, mirroring
   `docs/validation/SECURITY_ATTACK_SURFACE_MATRIX_2026-10.md`;
2. coverage for the three controls newly added in this slice (bounded
   abuse-rate protection, baseline security response headers, logout CSRF);
3. session-forgery/tamper/expiry/revocation adversarial proof at the live
   route level (not only the lower-level token unit tests);
4. input/media adversarial payloads (SQL-injection-shaped text, a
   decompression-bomb image, a forged Content-Type) run through the live
   routes rather than only the lower-level domain/unit functions.
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from PIL import Image
from starlette.testclient import TestClient

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.buyer_lead import SubmissionOperationId
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
    update_membership_state,
)
from hullq.persistence.buyer_lead import create_buyer_lead
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
from hullq.security.oidc import AuthProviderConfig
from hullq.security.session_token import mint_session_token
from hullq.storage.object_storage import InMemoryObjectStorage

_SECRET = b"9" * 32
_WEB_ORIGIN = "http://web.test"

_MEDIA_GALLERY_CSRF = "marketplace-media-gallery-v1"
_BUYER_LEAD_CSRF = "marketplace-buyer-lead-v1"
_LOGOUT_CSRF = "broker-logout-v1"


# ---------------------------------------------------------------------------
# Schema-isolated harness -- mirrors test_media_gallery_api.py/
# test_buyer_lead_api.py's identical pattern.
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
    schema_name = f"hullq_s0078api_{uuid.uuid4().hex[:16]}"
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
        preview_signing_secret=b"0" * 32,
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
        object_storage=InMemoryObjectStorage(),
    )
    test_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
    try:
        yield test_client
    finally:
        test_client.close()


def _dummy_auth_config() -> AuthProviderConfig:
    # `/api/auth/login` never calls the issuer over the network -- it only
    # builds a redirect URL from this config -- so a syntactically valid
    # but otherwise inert provider is sufficient to exercise the route's
    # normal (non-error) path for the rate-limiting tests below.
    return AuthProviderConfig(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        authorize_endpoint="https://issuer.test/authorize",
        token_endpoint="https://issuer.test/token",
        jwks_uri="https://issuer.test/.well-known/jwks.json",
        client_id="dummy-client",
        client_secret="dummy-secret",
    )


def _ensure_account(conn: Any, account_id: str) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING", [account_id]
        )


def _session_cookie(account_id: str, *, mfa: bool = True, secret: bytes = _SECRET) -> str:
    identity = AuthenticatedIdentity(
        provider=Provider.AUTH0,
        issuer="https://issuer.test/",
        subject=f"subject-{account_id}",
        auth_time=datetime.now(UTC),
        mfa_satisfied=mfa,
    )
    minted = mint_session_token(identity, AccountId(account_id), secret=secret)
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


def _create_listing(
    api_url: str,
    *,
    listing_id: str,
    org_id: str,
    account_id: str,
    membership_id: str,
    physical_boat_id: str,
    market_episode_id: str,
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
            id=OrganizationMembershipId(membership_id),
            account_id=account,
            organization_id=org.id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
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
        conn.commit()
    finally:
        conn.close()


def _publish_listing(
    api_url: str, *, listing_id: str, org_id: str, account_id: str, membership_id: str
) -> None:
    """Give an already-created listing an offer/claim/cover image and
    transition it DRAFT -> ACTIVE -- buyer-lead creation requires an ACTIVE
    listing (mirrors `test_buyer_lead_api.py`/`test_broker_lead_operations_
    api.py`'s identical publish fixture)."""
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
            revision_id=PhysicalBoatClaimRevisionId(f"CLAIM-{listing_id}"),
            expected_current_revision_id=None,
            claims=PhysicalBoatClaimSnapshot(
                marketed_brand_claim="Beneteau",
                model_designation_claim="Oceanis 30.1",
                build_year=BuildYearClaim(AssertionKind.VALUE_ASSERTION, 2020),
            ),
        )
        with conn.transaction():
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
            set_cover(
                conn,
                native_listing_id=NativeListingId(listing_id),
                owner_organization_id=org.id,
                media_placement_id=placement_result.media_placement_id,
                expected_version=placement_result.gallery_version,
            )
        result = publish_native_listing(
            conn,
            account_id=account,
            candidate_organization=org,
            membership=membership,
            native_listing_id=NativeListingId(listing_id),
        )
        assert result.status.value == "transitioned", result
        conn.commit()
    finally:
        conn.close()


def _seed_lead(api_url: str, *, listing_id: str, lead_name: str, lead_message: str) -> str:
    conn = psycopg.connect(api_url)
    try:
        result = create_buyer_lead(
            conn,
            submission_operation_id=SubmissionOperationId(f"OP-{listing_id}"),
            native_listing_id=NativeListingId(listing_id),
            account_id=None,
            buyer_name=lead_name,
            buyer_email="buyer@example.com",
            buyer_message=lead_message,
            as_of=datetime.now(UTC),
        )
        conn.commit()
        assert result.status.value == "created", result
        assert result.lead_id is not None
        return result.lead_id.value
    finally:
        conn.close()


def _csrf(value: str) -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": value}


def _jpeg_bytes(
    size: tuple[int, int] = (40, 30), color: tuple[int, int, int] = (10, 20, 30)
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _decompression_bomb_png_bytes() -> bytes:
    # Small on the wire (a huge solid-color PNG compresses extremely well)
    # but declares an enormous pixel count -- the exact adversarial shape
    # `hullq.media.image_processing`'s bounded-pixel-count-before-full-
    # decode check exists to reject (mirrors
    # `test_image_processing_unit.py::test_oversized_pixel_count_rejected`,
    # run here through the live authenticated upload route instead of the
    # bare domain function).
    buf = io.BytesIO()
    Image.new("RGB", (9000, 9000), (5, 5, 5)).save(buf, format="PNG")
    return buf.getvalue()


# ---------------------------------------------------------------------------
# 1. Holistic cross-tenant IDOR sweep
# ---------------------------------------------------------------------------


class TestCrossTenantHolisticSweep:
    """SECURITY_ATTACK_SURFACE_MATRIX row: cross-Organization attacker."""

    def test_foreign_organization_id_denied_across_every_org_scoped_read_surface(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-A", account_id="ACC-SEC-A", membership_id="MEM-SEC-A"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-B", account_id="ACC-SEC-B", membership_id="MEM-SEC-B"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-A",
            org_id="ORG-SEC-A",
            account_id="ACC-SEC-A",
            membership_id="MEM-SEC-A",
            physical_boat_id="PB-SEC-A",
            market_episode_id="ME-SEC-A",
        )
        _log_in(client, "ACC-SEC-B")  # B's own valid, MFA-satisfied session

        foreign_org = "ORG-SEC-A"
        foreign_listing = "NL-SEC-A"
        every_org_scoped_read_path = [
            f"/api/broker/organizations/{foreign_org}",
            f"/api/broker/organizations/{foreign_org}/inventory",
            f"/api/broker/organizations/{foreign_org}/performance",
            f"/api/broker/organizations/{foreign_org}/leads",
            f"/api/broker/organizations/{foreign_org}/leads/counts",
            f"/api/broker/organizations/{foreign_org}/notification-config",
            f"/api/broker/organizations/{foreign_org}/media/library",
            f"/api/broker/organizations/{foreign_org}/drafts",
            f"/api/broker/organizations/{foreign_org}/inventory/{foreign_listing}/edit",
            f"/api/broker/organizations/{foreign_org}/inventory/{foreign_listing}/sale-outcome",
            f"/api/broker/organizations/{foreign_org}/inventory/{foreign_listing}/media",
        ]
        for path in every_org_scoped_read_path:
            response = client.get(path)
            assert response.status_code == 404, f"{path} -> {response.status_code}"

    def test_own_organization_id_with_foreign_media_asset_id_denied(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-C", account_id="ACC-SEC-C", membership_id="MEM-SEC-C"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-D", account_id="ACC-SEC-D", membership_id="MEM-SEC-D"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-C",
            org_id="ORG-SEC-C",
            account_id="ACC-SEC-C",
            membership_id="MEM-SEC-C",
            physical_boat_id="PB-SEC-C",
            market_episode_id="ME-SEC-C",
        )

        _log_in(client, "ACC-SEC-C")
        uploaded = client.post(
            "/api/broker/organizations/ORG-SEC-C/inventory/NL-SEC-C/media/images",
            content=_jpeg_bytes(),
            headers={**_csrf(_MEDIA_GALLERY_CSRF), "X-HullQ-Rights-Confirmed": "true"},
        )
        assert uploaded.status_code == 201, uploaded.text
        foreign_asset_id = uploaded.json()["media_asset_id"]
        client.cookies.clear()

        # The sharper IDOR shape: the attacker's OWN org id, paired with
        # another Organization's nested asset id -- not merely an unknown
        # top-level org id.
        _log_in(client, "ACC-SEC-D")
        response = client.get(
            f"/api/broker/organizations/ORG-SEC-D/media/assets/{foreign_asset_id}"
        )
        assert response.status_code == 404

    def test_own_organization_id_with_foreign_lead_id_denied(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-E", account_id="ACC-SEC-E", membership_id="MEM-SEC-E"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-F", account_id="ACC-SEC-F", membership_id="MEM-SEC-F"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-E",
            org_id="ORG-SEC-E",
            account_id="ACC-SEC-E",
            membership_id="MEM-SEC-E",
            physical_boat_id="PB-SEC-E",
            market_episode_id="ME-SEC-E",
        )
        _publish_listing(
            api_url,
            listing_id="NL-SEC-E",
            org_id="ORG-SEC-E",
            account_id="ACC-SEC-E",
            membership_id="MEM-SEC-E",
        )
        foreign_lead_id = _seed_lead(
            api_url, listing_id="NL-SEC-E", lead_name="Buyer E", lead_message="Interested."
        )

        _log_in(client, "ACC-SEC-F")
        response = client.get(f"/api/broker/organizations/ORG-SEC-F/leads/{foreign_lead_id}")
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# 2. Session/MFA/revocation adversarial proof
# ---------------------------------------------------------------------------


class TestSessionAdversarial:
    def test_tampered_signature_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-G", account_id="ACC-SEC-G", membership_id="MEM-SEC-G"
        )
        cookie = _session_cookie("ACC-SEC-G")
        payload_part, signature_part = cookie.split(".")
        flipped_char = "A" if signature_part[-1] != "A" else "B"
        tampered = f"{payload_part}.{signature_part[:-1]}{flipped_char}"
        client.cookies.set("hullq_session", tampered, domain="api.test")
        response = client.get("/api/broker/context")
        assert response.status_code == 401

    def test_wrong_secret_signature_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-H", account_id="ACC-SEC-H", membership_id="MEM-SEC-H"
        )
        forged = _session_cookie("ACC-SEC-H", secret=b"X" * 32)
        client.cookies.set("hullq_session", forged, domain="api.test")
        response = client.get("/api/broker/context")
        assert response.status_code == 401

    def test_expired_token_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-I", account_id="ACC-SEC-I", membership_id="MEM-SEC-I"
        )
        identity = AuthenticatedIdentity(
            provider=Provider.AUTH0,
            issuer="https://issuer.test/",
            subject="subject-ACC-SEC-I",
            auth_time=datetime.now(UTC) - timedelta(hours=2),
            mfa_satisfied=True,
        )
        minted = mint_session_token(
            identity,
            AccountId("ACC-SEC-I"),
            secret=_SECRET,
            ttl_seconds=60,
            now=datetime.now(UTC) - timedelta(hours=1),
        )
        client.cookies.set("hullq_session", minted.token, domain="api.test")
        response = client.get("/api/broker/context")
        assert response.status_code == 401

    def test_revoked_membership_denies_the_very_next_request_on_the_same_session(
        self, client: TestClient, api_url: str
    ) -> None:
        # Contract §9/§D: Organization/role is never embedded in the
        # session token precisely so a revoked membership cannot outlive
        # the already-issued session cookie.
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-J", account_id="ACC-SEC-J", membership_id="MEM-SEC-J"
        )
        _log_in(client, "ACC-SEC-J")
        before = client.get("/api/broker/organizations/ORG-SEC-J")
        assert before.status_code == 200

        conn = psycopg.connect(api_url)
        try:
            update_membership_state(
                conn, OrganizationMembershipId("MEM-SEC-J"), MembershipState.INACTIVE
            )
            conn.commit()
        finally:
            conn.close()

        after = client.get("/api/broker/organizations/ORG-SEC-J")
        assert after.status_code == 404

    def test_mfa_required_role_blocked_without_mfa_evidence(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-K", account_id="ACC-SEC-K", membership_id="MEM-SEC-K"
        )
        _log_in(client, "ACC-SEC-K", mfa=False)
        response = client.post(
            "/api/broker/organizations/ORG-SEC-K/drafts",
            json={},
            headers=_csrf("professional-listing-draft-v1"),
        )
        assert response.status_code == 403
        assert response.json()["error"] == "mfa_required"


# ---------------------------------------------------------------------------
# 3. CSRF/Origin adversarial proof, including the new logout channel
# ---------------------------------------------------------------------------


class TestCsrfAdversarial:
    def test_missing_origin_rejected_on_media_upload(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-L", account_id="ACC-SEC-L", membership_id="MEM-SEC-L"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-L",
            org_id="ORG-SEC-L",
            account_id="ACC-SEC-L",
            membership_id="MEM-SEC-L",
            physical_boat_id="PB-SEC-L",
            market_episode_id="ME-SEC-L",
        )
        _log_in(client, "ACC-SEC-L")
        response = client.post(
            "/api/broker/organizations/ORG-SEC-L/inventory/NL-SEC-L/media/images",
            content=_jpeg_bytes(),
            headers={
                "X-HullQ-Rights-Confirmed": "true",
                "X-HullQ-Requested-With": _MEDIA_GALLERY_CSRF,
            },
        )
        assert response.status_code == 403

    def test_forged_origin_rejected_on_media_upload(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-M", account_id="ACC-SEC-M", membership_id="MEM-SEC-M"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-M",
            org_id="ORG-SEC-M",
            account_id="ACC-SEC-M",
            membership_id="MEM-SEC-M",
            physical_boat_id="PB-SEC-M",
            market_episode_id="ME-SEC-M",
        )
        _log_in(client, "ACC-SEC-M")
        response = client.post(
            "/api/broker/organizations/ORG-SEC-M/inventory/NL-SEC-M/media/images",
            content=_jpeg_bytes(),
            headers={
                "Origin": "https://attacker.example",
                "X-HullQ-Requested-With": _MEDIA_GALLERY_CSRF,
                "X-HullQ-Rights-Confirmed": "true",
            },
        )
        assert response.status_code == 403

    def test_cross_channel_csrf_header_replay_rejected(
        self, client: TestClient, api_url: str
    ) -> None:
        # A valid CSRF header minted for one write channel must never be
        # honored by another channel's identical exact-Origin check.
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-N", account_id="ACC-SEC-N", membership_id="MEM-SEC-N"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-N",
            org_id="ORG-SEC-N",
            account_id="ACC-SEC-N",
            membership_id="MEM-SEC-N",
            physical_boat_id="PB-SEC-N",
            market_episode_id="ME-SEC-N",
        )
        _log_in(client, "ACC-SEC-N")
        response = client.post(
            "/api/broker/organizations/ORG-SEC-N/inventory/NL-SEC-N/media/images",
            content=_jpeg_bytes(),
            headers={**_csrf(_BUYER_LEAD_CSRF), "X-HullQ-Rights-Confirmed": "true"},
        )
        assert response.status_code == 403

    def test_logout_without_csrf_header_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-O", account_id="ACC-SEC-O", membership_id="MEM-SEC-O"
        )
        _log_in(client, "ACC-SEC-O")
        response = client.post("/api/auth/logout")
        assert response.status_code == 403
        # A session that a forged cross-site logout attempt could not
        # validate away must remain usable afterward.
        still_valid = client.get("/api/broker/organizations/ORG-SEC-O")
        assert still_valid.status_code == 200

    def test_logout_with_correct_csrf_header_succeeds_and_clears_session(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-P", account_id="ACC-SEC-P", membership_id="MEM-SEC-P"
        )
        _log_in(client, "ACC-SEC-P")
        response = client.post("/api/auth/logout", headers=_csrf(_LOGOUT_CSRF))
        assert response.status_code == 200
        assert response.json() == {"status": "logged_out"}
        after = client.get("/api/broker/organizations/ORG-SEC-P")
        assert after.status_code == 401


# ---------------------------------------------------------------------------
# 4. Bounded abuse-rate protection (new in this slice)
# ---------------------------------------------------------------------------


class TestRateLimitingAdversarial:
    def test_contact_route_blocks_after_its_bounded_window(
        self, client: TestClient, api_url: str
    ) -> None:
        body = {
            "submission_operation_id": "OP-RL",
            "name": "Spammer",
            "email": "spammer@example.com",
            "message": "x",
        }
        statuses = []
        for _ in range(6):
            response = client.post(
                "/api/listings/NL-RL-NEVER/contact",
                json=body,
                headers=_csrf(_BUYER_LEAD_CSRF),
            )
            statuses.append(response.status_code)
        # The limiter is 5/window; the target listing does not exist so
        # every allowed request resolves to 404 (listing_not_available) --
        # the 6th request must be rejected by the limiter before that
        # lookup even happens.
        assert statuses[:5] == [404] * 5
        assert statuses[5] == 429

    def test_media_upload_route_blocks_after_its_bounded_window(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-Q", account_id="ACC-SEC-Q", membership_id="MEM-SEC-Q"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-Q",
            org_id="ORG-SEC-Q",
            account_id="ACC-SEC-Q",
            membership_id="MEM-SEC-Q",
            physical_boat_id="PB-SEC-Q",
            market_episode_id="ME-SEC-Q",
        )
        _log_in(client, "ACC-SEC-Q")
        headers = {**_csrf(_MEDIA_GALLERY_CSRF), "X-HullQ-Rights-Confirmed": "true"}
        statuses = []
        for _ in range(31):
            response = client.post(
                "/api/broker/organizations/ORG-SEC-Q/inventory/NL-SEC-Q/media/images",
                content=b"not a real image, just garbage bytes",
                headers=headers,
            )
            statuses.append(response.status_code)
        assert 429 not in statuses[:30]
        assert statuses[30] == 429

    def test_login_route_blocks_after_its_bounded_window(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from hullq.api.app import create_app

        monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
        app = create_app(
            database_url=api_url,
            preview_signing_secret=b"0" * 32,
            session_signing_secret=_SECRET,
            web_origin=_WEB_ORIGIN,
            auth_provider_config=_dummy_auth_config(),
            auth_redirect_uri="http://api.test/api/auth/callback",
            web_base_url="http://api.test",
        )
        login_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
        try:
            statuses = [login_client.get("/api/auth/login").status_code for _ in range(21)]
        finally:
            login_client.close()
        assert statuses[:20] == [302] * 20
        assert statuses[20] == 429

    def test_rate_limit_keys_are_independent_across_route_categories(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from hullq.api.app import create_app

        # Exhausting the contact limiter must never affect the login
        # limiter's independent budget (SLICE-0078: one limiter instance
        # per route category).
        monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
        app = create_app(
            database_url=api_url,
            preview_signing_secret=b"0" * 32,
            session_signing_secret=_SECRET,
            web_origin=_WEB_ORIGIN,
            auth_provider_config=_dummy_auth_config(),
            auth_redirect_uri="http://api.test/api/auth/callback",
            web_base_url="http://api.test",
        )
        isolated_client = TestClient(app, base_url="http://api.test", follow_redirects=False)
        try:
            body = {
                "submission_operation_id": "OP-RL-ISOLATED",
                "name": "Spammer",
                "email": "spammer@example.com",
                "message": "x",
            }
            for _ in range(6):
                isolated_client.post(
                    "/api/listings/NL-RL-NEVER-2/contact",
                    json=body,
                    headers=_csrf(_BUYER_LEAD_CSRF),
                )
            login_response = isolated_client.get("/api/auth/login")
        finally:
            isolated_client.close()
        assert login_response.status_code == 302


# ---------------------------------------------------------------------------
# 5. Baseline security response headers (new in this slice)
# ---------------------------------------------------------------------------


class TestSecurityHeadersAdversarial:
    def test_baseline_headers_present_on_public_route(
        self, client: TestClient, api_url: str
    ) -> None:
        response = client.get("/api/listings/NL-HEADERS-NEVER")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("X-Frame-Options") == "DENY"
        assert (
            response.headers.get("Content-Security-Policy")
            == "default-src 'none'; frame-ancestors 'none'"
        )
        assert "Permissions-Policy" in response.headers

    def test_baseline_headers_present_on_authenticated_broker_route(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-R", account_id="ACC-SEC-R", membership_id="MEM-SEC-R"
        )
        _log_in(client, "ACC-SEC-R")
        response = client.get("/api/broker/organizations/ORG-SEC-R")
        assert response.headers.get("X-Content-Type-Options") == "nosniff"
        assert response.headers.get("Cache-Control") == "private, no-store"

    def test_hsts_absent_when_cookies_not_configured_secure(
        self, client: TestClient, api_url: str
    ) -> None:
        response = client.get("/api/listings/NL-HEADERS-NEVER-2")
        assert "Strict-Transport-Security" not in response.headers

    def test_hsts_present_once_cookies_are_configured_secure(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from hullq.api.app import create_app

        monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "true")
        app = create_app(
            database_url=api_url,
            preview_signing_secret=b"0" * 32,
            session_signing_secret=_SECRET,
            web_origin=_WEB_ORIGIN,
        )
        secure_client = TestClient(app, base_url="https://api.test", follow_redirects=False)
        try:
            response = secure_client.get("/api/listings/NL-HEADERS-NEVER-3")
            assert response.headers.get("Strict-Transport-Security") == (
                "max-age=63072000; includeSubDomains"
            )
        finally:
            secure_client.close()


# ---------------------------------------------------------------------------
# 6. Input/media abuse adversarial proof
# ---------------------------------------------------------------------------


class TestInputAndMediaAbuseAdversarial:
    def test_sql_injection_shaped_text_round_trips_literally_and_safely(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-S", account_id="ACC-SEC-S", membership_id="MEM-SEC-S"
        )
        _log_in(client, "ACC-SEC-S")
        created = client.post(
            "/api/broker/organizations/ORG-SEC-S/drafts",
            json={},
            headers=_csrf("professional-listing-draft-v1"),
        )
        assert created.status_code == 201, created.text
        draft_id = created.json()["draft_id"]

        injection_payload = "Robert'); DROP TABLE professional_listing_drafts; --"
        updated = client.put(
            f"/api/broker/organizations/ORG-SEC-S/drafts/{draft_id}",
            json={
                "expected_version": 1,
                "broker_listing_reference": injection_payload,
                "physical_boat.boat_name": f"1' OR '1'='1'; {injection_payload}",
            },
            headers=_csrf("professional-listing-draft-v1"),
        )
        assert updated.status_code == 200, updated.text
        assert updated.json()["broker_listing_reference"] == injection_payload

        # The payload's own table still exists and is queryable -- the
        # injected fragment was never executed as SQL.
        still_listable = client.get("/api/broker/organizations/ORG-SEC-S/drafts")
        assert still_listable.status_code == 200

    def test_malformed_json_body_rejected_cleanly(self, client: TestClient, api_url: str) -> None:
        response = client.post(
            "/api/listings/NL-MALFORMED/contact",
            content=b"{not valid json",
            headers={**_csrf(_BUYER_LEAD_CSRF), "Content-Type": "application/json"},
        )
        assert response.status_code == 400

    def test_non_object_json_body_rejected(self, client: TestClient, api_url: str) -> None:
        response = client.post(
            "/api/listings/NL-NONOBJECT/contact",
            json=["not", "an", "object"],
            headers=_csrf(_BUYER_LEAD_CSRF),
        )
        assert response.status_code == 400

    def test_oversized_declared_content_length_rejected_before_body_read(
        self, client: TestClient, api_url: str
    ) -> None:
        oversized_body = {
            "submission_operation_id": "OP-OVERSIZE",
            "name": "Jane",
            "email": "jane@example.com",
            "message": "ok",
            # A request-level padding field inflates total body size well
            # past the 20_000-byte bound while every recognized field stays
            # within its own individual max length -- isolates the
            # request-level Content-Length bound from per-field validation.
            "padding": "A" * 25_000,
        }
        response = client.post(
            "/api/listings/NL-OVERSIZE/contact",
            json=oversized_body,
            headers=_csrf(_BUYER_LEAD_CSRF),
        )
        assert response.status_code == 413

    def test_decompression_bomb_image_rejected_through_live_upload_route(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-T", account_id="ACC-SEC-T", membership_id="MEM-SEC-T"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-T",
            org_id="ORG-SEC-T",
            account_id="ACC-SEC-T",
            membership_id="MEM-SEC-T",
            physical_boat_id="PB-SEC-T",
            market_episode_id="ME-SEC-T",
        )
        _log_in(client, "ACC-SEC-T")
        response = client.post(
            "/api/broker/organizations/ORG-SEC-T/inventory/NL-SEC-T/media/images",
            content=_decompression_bomb_png_bytes(),
            headers={**_csrf(_MEDIA_GALLERY_CSRF), "X-HullQ-Rights-Confirmed": "true"},
        )
        assert response.status_code == 422
        assert response.json()["outcome"] == "REJECTED"

    def test_forged_bytes_claiming_to_be_an_image_rejected(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-SEC-U", account_id="ACC-SEC-U", membership_id="MEM-SEC-U"
        )
        _create_listing(
            api_url,
            listing_id="NL-SEC-U",
            org_id="ORG-SEC-U",
            account_id="ACC-SEC-U",
            membership_id="MEM-SEC-U",
            physical_boat_id="PB-SEC-U",
            market_episode_id="ME-SEC-U",
        )
        _log_in(client, "ACC-SEC-U")
        # The server never trusts a client-declared Content-Type; only the
        # real decoded bytes decide acceptance. No `Content-Type` header is
        # even sent here, and the payload is not a real image.
        response = client.post(
            "/api/broker/organizations/ORG-SEC-U/inventory/NL-SEC-U/media/images",
            content=b"<html><script>not an image</script></html>",
            headers={**_csrf(_MEDIA_GALLERY_CSRF), "X-HullQ-Rights-Confirmed": "true"},
        )
        assert response.status_code == 422
        assert response.json()["outcome"] == "REJECTED"
