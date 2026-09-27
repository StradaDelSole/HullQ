"""FastAPI integration tests for SLICE-0068 marketplace mixed-media gallery.

Uses a directly minted session token (mirrors `test_broker_inventory_
lifecycle_api.py`'s identical pattern) and the deterministic
`InMemoryObjectStorage` fake (contract §17: "live Cloudflare credentials are
not required in ordinary CI") injected into `create_app`.

Covers contract §3 (authorization/CSRF/non-enumeration), §6 (image ingestion/
rejection), §8 (ordering/cover), §9 (same-Organization reuse/cross-
Organization denial), §10 (YouTube), §12 (retirement) and §17's required
proof matrix.
"""

from __future__ import annotations

import io
import os
import uuid
from collections.abc import Generator
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from PIL import Image
from starlette.testclient import TestClient

from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import MAX_IMAGE_UPLOAD_BYTES, MAX_SOURCE_REFERENCE_LENGTH
from hullq.domain.native_listing_offer import AskingPriceMode, NativeListingOfferSnapshot
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
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.native_listing_lifecycle import publish_native_listing
from hullq.persistence.native_listing_offer import (
    NativeListingOfferRevisionId,
    write_native_listing_offer_revision,
)
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.session_token import mint_session_token
from hullq.storage.object_storage import InMemoryObjectStorage

_SECRET = b"8" * 32
_WEB_ORIGIN = "http://web.test"
_CSRF_HEADER_VALUE = "marketplace-media-gallery-v1"


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
    schema_name = f"hullq_s0068api_{uuid.uuid4().hex[:16]}"
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
def object_storage() -> InMemoryObjectStorage:
    return InMemoryObjectStorage()


@pytest.fixture()
def client(
    api_url: str, object_storage: InMemoryObjectStorage, monkeypatch: pytest.MonkeyPatch
) -> Generator[TestClient]:
    from hullq.api.app import create_app

    monkeypatch.setenv("HULLQ_SESSION_COOKIE_SECURE", "false")
    app = create_app(
        database_url=api_url,
        preview_signing_secret=os.urandom(32),
        session_signing_secret=_SECRET,
        web_origin=_WEB_ORIGIN,
        object_storage=object_storage,
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


def _publish_listing(api_url: str, *, listing_id: str, org_id: str, account_id: str) -> None:
    """Give an already-created listing a current offer and transition it
    DRAFT -> ACTIVE, for Finding C's ACTIVE-lifecycle HTTP proof."""
    conn = psycopg.connect(api_url)
    try:
        account = AccountId(account_id)
        org = MarketplaceOrganization(
            id=MarketplaceOrganizationId(org_id),
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-PUBLISH-{listing_id}"),
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
        conn.commit()
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


def _csrf_headers() -> dict[str, str]:
    return {"Origin": _WEB_ORIGIN, "X-HullQ-Requested-With": _CSRF_HEADER_VALUE}


def _jpeg_bytes(
    size: tuple[int, int] = (64, 32), color: tuple[int, int, int] = (200, 10, 10)
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


def _upload_headers(
    *, rights_confirmed: bool = True, source_reference: str | None = None
) -> dict[str, str]:
    headers = _csrf_headers()
    headers["X-HullQ-Rights-Confirmed"] = "true" if rights_confirmed else "false"
    if source_reference is not None:
        headers["X-HullQ-Source-Reference"] = source_reference
    return headers


def _gallery_path(org_id: str, listing_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/inventory/{listing_id}/media"


def _images_path(org_id: str, listing_id: str) -> str:
    return f"{_gallery_path(org_id, listing_id)}/images"


def _reuse_path(org_id: str, listing_id: str) -> str:
    return f"{_gallery_path(org_id, listing_id)}/reuse"


def _youtube_path(org_id: str, listing_id: str) -> str:
    return f"{_gallery_path(org_id, listing_id)}/youtube"


def _reorder_path(org_id: str, listing_id: str) -> str:
    return f"{_gallery_path(org_id, listing_id)}/reorder"


def _cover_path(org_id: str, listing_id: str) -> str:
    return f"{_gallery_path(org_id, listing_id)}/cover"


def _remove_path(org_id: str, listing_id: str, placement_id: str) -> str:
    return f"{_gallery_path(org_id, listing_id)}/placements/{placement_id}/remove"


def _library_path(org_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/media/library"


def _asset_bytes_path(org_id: str, asset_id: str) -> str:
    return f"/api/broker/organizations/{org_id}/media/assets/{asset_id}"


def _retire_path(org_id: str, asset_id: str) -> str:
    return f"{_asset_bytes_path(org_id, asset_id)}/retire"


def _upload_one(
    client: TestClient,
    org_id: str,
    listing_id: str,
    *,
    rights_confirmed: bool = True,
    body: bytes | None = None,
    source_reference: str | None = None,
) -> Any:
    return client.post(
        _images_path(org_id, listing_id),
        content=body if body is not None else _jpeg_bytes(),
        headers=_upload_headers(
            rights_confirmed=rights_confirmed, source_reference=source_reference
        ),
    )


# ---------------------------------------------------------------------------
# Gallery read
# ---------------------------------------------------------------------------


class TestGalleryRead:
    def test_unauthenticated_is_blocked(self, client: TestClient) -> None:
        response = client.get(_gallery_path("ORG-X", "NL-X"))
        assert response.status_code == 401

    def test_unknown_organization_is_not_found(self, client: TestClient) -> None:
        _log_in(client, "ACC-GR-1")
        response = client.get(_gallery_path("ORG-GR-NEVER", "NL-X"))
        assert response.status_code == 404

    def test_mfa_required(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-GR-MFA", account_id="ACC-GR-MFA", membership_id="OM-GR-MFA"
        )
        _log_in(client, "ACC-GR-MFA", mfa=False)
        response = client.get(_gallery_path("ORG-GR-MFA", "NL-X"))
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}

    def test_missing_publisher_role(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-GR-NOPUB",
            account_id="ACC-GR-NOPUB",
            membership_id="OM-GR-NOPUB",
            roles=frozenset({MembershipRole.MEMBER}),
        )
        _log_in(client, "ACC-GR-NOPUB", mfa=False)
        response = client.get(_gallery_path("ORG-GR-NOPUB", "NL-X"))
        assert response.status_code == 403
        assert response.json() == {"error": "publisher_role_required"}

    def test_foreign_and_unknown_listing_share_identical_not_found_shape(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-GR-VICTIM", account_id="ACC-GR-VICTIM", membership_id="OM-GR-V"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-GR-ATTACKER", account_id="ACC-GR-ATTACKER", membership_id="OM-GR-A"
        )
        _create_listing(
            api_url,
            listing_id="NL-GR-VICTIM",
            org_id="ORG-GR-VICTIM",
            account_id="ACC-GR-VICTIM",
            membership_id="OM-GR-V",
            physical_boat_id="PB-GR-VICTIM",
            market_episode_id="ME-GR-VICTIM",
        )
        _log_in(client, "ACC-GR-ATTACKER")
        foreign = client.get(_gallery_path("ORG-GR-ATTACKER", "NL-GR-VICTIM"))
        unknown = client.get(_gallery_path("ORG-GR-ATTACKER", "NL-NEVER-CREATED"))
        assert foreign.status_code == unknown.status_code == 404
        assert foreign.content == unknown.content

    def test_empty_gallery_reads_as_zero_version_no_cover(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-GR-EMPTY", account_id="ACC-GR-EMPTY", membership_id="OM-GR-E"
        )
        _create_listing(
            api_url,
            listing_id="NL-GR-EMPTY",
            org_id="ORG-GR-EMPTY",
            account_id="ACC-GR-EMPTY",
            membership_id="OM-GR-E",
            physical_boat_id="PB-GR-EMPTY",
            market_episode_id="ME-GR-EMPTY",
        )
        _log_in(client, "ACC-GR-EMPTY")
        response = client.get(_gallery_path("ORG-GR-EMPTY", "NL-GR-EMPTY"))
        assert response.status_code == 200
        body = response.json()
        assert body == {
            "native_listing_id": "NL-GR-EMPTY",
            "gallery_version": 0,
            "cover_placement_id": None,
            "placements": [],
        }


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------


class TestUploadImage:
    def test_unauthenticated_is_blocked(self, client: TestClient) -> None:
        response = client.post(_images_path("ORG-X", "NL-X"), content=_jpeg_bytes())
        assert response.status_code == 401

    def test_missing_csrf_fails_closed(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-CSRF", account_id="ACC-UP-CSRF", membership_id="OM-UP-CSRF"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-CSRF",
            org_id="ORG-UP-CSRF",
            account_id="ACC-UP-CSRF",
            membership_id="OM-UP-CSRF",
            physical_boat_id="PB-UP-CSRF",
            market_episode_id="ME-UP-CSRF",
        )
        _log_in(client, "ACC-UP-CSRF")
        response = client.post(_images_path("ORG-UP-CSRF", "NL-UP-CSRF"), content=_jpeg_bytes())
        assert response.status_code == 403
        gallery = client.get(_gallery_path("ORG-UP-CSRF", "NL-UP-CSRF"))
        assert gallery.json()["placements"] == []

    def test_wrong_csrf_header_value_fails_closed(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-CSRF2", account_id="ACC-UP-CSRF2", membership_id="OM-UP-CSRF2"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-CSRF2",
            org_id="ORG-UP-CSRF2",
            account_id="ACC-UP-CSRF2",
            membership_id="OM-UP-CSRF2",
            physical_boat_id="PB-UP-CSRF2",
            market_episode_id="ME-UP-CSRF2",
        )
        _log_in(client, "ACC-UP-CSRF2")
        response = client.post(
            _images_path("ORG-UP-CSRF2", "NL-UP-CSRF2"),
            content=_jpeg_bytes(),
            headers={
                "Origin": _WEB_ORIGIN,
                "X-HullQ-Requested-With": "professional-listing-draft-v1",
            },
        )
        assert response.status_code == 403

    def test_mfa_required_writes_nothing(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-MFA", account_id="ACC-UP-MFA", membership_id="OM-UP-MFA"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-MFA",
            org_id="ORG-UP-MFA",
            account_id="ACC-UP-MFA",
            membership_id="OM-UP-MFA",
            physical_boat_id="PB-UP-MFA",
            market_episode_id="ME-UP-MFA",
        )
        _log_in(client, "ACC-UP-MFA", mfa=False)
        response = _upload_one(client, "ORG-UP-MFA", "NL-UP-MFA")
        assert response.status_code == 403
        assert response.json() == {"error": "mfa_required"}

    def test_foreign_listing_upload_is_not_found_and_writes_nothing(
        self, client: TestClient, api_url: str, object_storage: InMemoryObjectStorage
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-VICTIM", account_id="ACC-UP-VICTIM", membership_id="OM-UP-V"
        )
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-ATTACKER", account_id="ACC-UP-ATTACKER", membership_id="OM-UP-A"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-VICTIM",
            org_id="ORG-UP-VICTIM",
            account_id="ACC-UP-VICTIM",
            membership_id="OM-UP-V",
            physical_boat_id="PB-UP-VICTIM",
            market_episode_id="ME-UP-VICTIM",
        )
        _log_in(client, "ACC-UP-ATTACKER")
        response = _upload_one(client, "ORG-UP-ATTACKER", "NL-UP-VICTIM")
        assert response.status_code == 404

    def test_valid_jpeg_upload_with_rights_confirmed_is_created_and_public_usable(
        self, client: TestClient, api_url: str, object_storage: InMemoryObjectStorage
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-OK", account_id="ACC-UP-OK", membership_id="OM-UP-OK"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-OK",
            org_id="ORG-UP-OK",
            account_id="ACC-UP-OK",
            membership_id="OM-UP-OK",
            physical_boat_id="PB-UP-OK",
            market_episode_id="ME-UP-OK",
        )
        _log_in(client, "ACC-UP-OK")
        response = _upload_one(client, "ORG-UP-OK", "NL-UP-OK", rights_confirmed=True)
        assert response.status_code == 201
        body = response.json()
        assert body["outcome"] == "CREATED"
        assert body["gallery_version"] == 1

        gallery = client.get(_gallery_path("ORG-UP-OK", "NL-UP-OK")).json()
        assert len(gallery["placements"]) == 1
        placement = gallery["placements"][0]
        assert placement["kind"] == "IMAGE"
        asset = placement["media_asset"]
        assert asset["processing_state"] == "APPROVED"
        assert asset["rights_state"] == "DECLARED"
        assert asset["is_public_usable"] is True
        assert asset["mime_type"] == "image/jpeg"

    def test_upload_without_rights_confirmation_is_never_public_usable(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url,
            org_id="ORG-UP-NORIGHTS",
            account_id="ACC-UP-NORIGHTS",
            membership_id="OM-UP-NR",
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-NORIGHTS",
            org_id="ORG-UP-NORIGHTS",
            account_id="ACC-UP-NORIGHTS",
            membership_id="OM-UP-NR",
            physical_boat_id="PB-UP-NORIGHTS",
            market_episode_id="ME-UP-NORIGHTS",
        )
        _log_in(client, "ACC-UP-NORIGHTS")
        response = _upload_one(client, "ORG-UP-NORIGHTS", "NL-UP-NORIGHTS", rights_confirmed=False)
        assert response.status_code == 201
        gallery = client.get(_gallery_path("ORG-UP-NORIGHTS", "NL-UP-NORIGHTS")).json()
        asset = gallery["placements"][0]["media_asset"]
        assert asset["rights_state"] == "UNKNOWN"
        assert asset["is_public_usable"] is False

    def test_malformed_upload_is_rejected_and_creates_no_placement(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-BAD", account_id="ACC-UP-BAD", membership_id="OM-UP-BAD"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-BAD",
            org_id="ORG-UP-BAD",
            account_id="ACC-UP-BAD",
            membership_id="OM-UP-BAD",
            physical_boat_id="PB-UP-BAD",
            market_episode_id="ME-UP-BAD",
        )
        _log_in(client, "ACC-UP-BAD")
        response = _upload_one(client, "ORG-UP-BAD", "NL-UP-BAD", body=b"not an image at all")
        assert response.status_code == 422
        body = response.json()
        assert body["outcome"] == "REJECTED"
        assert body["reason"] == "UNSUPPORTED_OR_MALFORMED"
        gallery = client.get(_gallery_path("ORG-UP-BAD", "NL-UP-BAD")).json()
        assert gallery["placements"] == []
        assert gallery["gallery_version"] == 0

    def test_oversized_upload_is_rejected_with_413(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-HUGE", account_id="ACC-UP-HUGE", membership_id="OM-UP-HUGE"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-HUGE",
            org_id="ORG-UP-HUGE",
            account_id="ACC-UP-HUGE",
            membership_id="OM-UP-HUGE",
            physical_boat_id="PB-UP-HUGE",
            market_episode_id="ME-UP-HUGE",
        )
        _log_in(client, "ACC-UP-HUGE")
        oversized = b"\x00" * (MAX_IMAGE_UPLOAD_BYTES + 1)
        response = _upload_one(client, "ORG-UP-HUGE", "NL-UP-HUGE", body=oversized)
        assert response.status_code == 413

    def test_multi_file_partial_failure_preserves_successful_items(
        self, client: TestClient, api_url: str
    ) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-UP-MULTI", account_id="ACC-UP-MULTI", membership_id="OM-UP-MULTI"
        )
        _create_listing(
            api_url,
            listing_id="NL-UP-MULTI",
            org_id="ORG-UP-MULTI",
            account_id="ACC-UP-MULTI",
            membership_id="OM-UP-MULTI",
            physical_boat_id="PB-UP-MULTI",
            market_episode_id="ME-UP-MULTI",
        )
        _log_in(client, "ACC-UP-MULTI")
        first = _upload_one(client, "ORG-UP-MULTI", "NL-UP-MULTI")
        second = _upload_one(client, "ORG-UP-MULTI", "NL-UP-MULTI", body=b"garbage")
        third = _upload_one(client, "ORG-UP-MULTI", "NL-UP-MULTI")
        assert first.status_code == 201
        assert second.status_code == 422
        assert third.status_code == 201
        gallery = client.get(_gallery_path("ORG-UP-MULTI", "NL-UP-MULTI")).json()
        assert len(gallery["placements"]) == 2
        assert gallery["gallery_version"] == 2


# ---------------------------------------------------------------------------
# Same-organization reuse / cross-organization denial
# ---------------------------------------------------------------------------


class TestReuse:
    def _setup_two_listings_same_org(self, api_url: str, suffix: str) -> tuple[str, str, str]:
        org_id, account_id, membership_id = f"ORG-RU{suffix}", f"ACC-RU{suffix}", f"OM-RU{suffix}"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        for tag in ("A", "B"):
            _create_listing(
                api_url,
                listing_id=f"NL-RU{suffix}-{tag}",
                org_id=org_id,
                account_id=account_id,
                membership_id=membership_id,
                physical_boat_id=f"PB-RU{suffix}-{tag}",
                market_episode_id=f"ME-RU{suffix}-{tag}",
            )
        return org_id, account_id, membership_id

    def test_same_org_reuse_succeeds(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, _ = self._setup_two_listings_same_org(api_url, "1")
        _log_in(client, account_id)
        upload = _upload_one(client, org_id, "NL-RU1-A")
        asset_id = upload.json()["media_asset_id"]
        response = client.post(
            _reuse_path(org_id, "NL-RU1-B"),
            json={"media_asset_id": asset_id},
            headers=_csrf_headers(),
        )
        assert response.status_code == 201
        gallery_b = client.get(_gallery_path(org_id, "NL-RU1-B")).json()
        assert gallery_b["placements"][0]["media_asset"]["media_asset_id"] == asset_id

    def test_cross_organization_reuse_denied(self, client: TestClient, api_url: str) -> None:
        org_a, account_a, _ = self._setup_two_listings_same_org(api_url, "2A")
        org_b, account_b, _ = self._setup_two_listings_same_org(api_url, "2B")
        _log_in(client, account_a)
        upload = _upload_one(client, org_a, "NL-RU2A-A")
        asset_id = upload.json()["media_asset_id"]

        _log_in(client, account_b)
        response = client.post(
            _reuse_path(org_b, "NL-RU2B-A"),
            json={"media_asset_id": asset_id},
            headers=_csrf_headers(),
        )
        assert response.status_code == 404
        assert response.json() == {"error": "asset_not_found"}


# ---------------------------------------------------------------------------
# YouTube
# ---------------------------------------------------------------------------


class TestYoutube:
    def test_valid_url_is_created(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-YT-OK", account_id="ACC-YT-OK", membership_id="OM-YT-OK"
        )
        _create_listing(
            api_url,
            listing_id="NL-YT-OK",
            org_id="ORG-YT-OK",
            account_id="ACC-YT-OK",
            membership_id="OM-YT-OK",
            physical_boat_id="PB-YT-OK",
            market_episode_id="ME-YT-OK",
        )
        _log_in(client, "ACC-YT-OK")
        response = client.post(
            _youtube_path("ORG-YT-OK", "NL-YT-OK"),
            json={"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"},
            headers=_csrf_headers(),
        )
        assert response.status_code == 201
        gallery = client.get(_gallery_path("ORG-YT-OK", "NL-YT-OK")).json()
        placement = gallery["placements"][0]
        assert placement["kind"] == "YOUTUBE"
        assert placement["youtube_video_id"] == "dQw4w9WgXcQ"

    def test_arbitrary_embed_html_rejected(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-YT-BAD", account_id="ACC-YT-BAD", membership_id="OM-YT-BAD"
        )
        _create_listing(
            api_url,
            listing_id="NL-YT-BAD",
            org_id="ORG-YT-BAD",
            account_id="ACC-YT-BAD",
            membership_id="OM-YT-BAD",
            physical_boat_id="PB-YT-BAD",
            market_episode_id="ME-YT-BAD",
        )
        _log_in(client, "ACC-YT-BAD")
        response = client.post(
            _youtube_path("ORG-YT-BAD", "NL-YT-BAD"),
            json={"url": '<iframe src="https://www.youtube.com/embed/dQw4w9WgXcQ"></iframe>'},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_youtube_url"}
        gallery = client.get(_gallery_path("ORG-YT-BAD", "NL-YT-BAD")).json()
        assert gallery["placements"] == []


# ---------------------------------------------------------------------------
# Reorder / Cover / Remove
# ---------------------------------------------------------------------------


class TestReorderCoverRemove:
    def _setup_gallery_with_two_images(
        self, client: TestClient, api_url: str, suffix: str
    ) -> tuple[str, str, list[str]]:
        org_id, account_id, membership_id = f"ORG-RC{suffix}", f"ACC-RC{suffix}", f"OM-RC{suffix}"
        listing_id = f"NL-RC{suffix}"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id=f"PB-RC{suffix}",
            market_episode_id=f"ME-RC{suffix}",
        )
        _log_in(client, account_id)
        placement_ids = []
        for _ in range(2):
            upload = _upload_one(client, org_id, listing_id)
            placement_ids.append(upload.json()["media_placement_id"])
        return org_id, listing_id, placement_ids

    def test_reorder_success(self, client: TestClient, api_url: str) -> None:
        org_id, listing_id, placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "1"
        )
        response = client.post(
            _reorder_path(org_id, listing_id),
            json={"expected_version": 2, "placement_ids": list(reversed(placement_ids))},
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "REORDERED"
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert [p["media_placement_id"] for p in gallery["placements"]] == list(
            reversed(placement_ids)
        )

    def test_reorder_stale_version_conflicts(self, client: TestClient, api_url: str) -> None:
        org_id, listing_id, placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "2"
        )
        response = client.post(
            _reorder_path(org_id, listing_id),
            json={"expected_version": 1, "placement_ids": placement_ids},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "version_conflict"}

    def test_reorder_invalid_payload(self, client: TestClient, api_url: str) -> None:
        org_id, listing_id, _placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "3"
        )
        response = client.post(
            _reorder_path(org_id, listing_id),
            json={"expected_version": "not-an-int", "placement_ids": []},
            headers=_csrf_headers(),
        )
        assert response.status_code == 400

    def test_set_and_clear_cover(self, client: TestClient, api_url: str) -> None:
        org_id, listing_id, placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "4"
        )
        set_response = client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 2, "media_placement_id": placement_ids[0]},
            headers=_csrf_headers(),
        )
        assert set_response.status_code == 200
        assert set_response.json()["outcome"] == "SET"
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert gallery["cover_placement_id"] == placement_ids[0]

        clear_response = client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 3, "media_placement_id": None},
            headers=_csrf_headers(),
        )
        assert clear_response.status_code == 200
        assert clear_response.json()["outcome"] == "CLEARED"
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert gallery["cover_placement_id"] is None

    def test_cover_on_non_public_usable_image_is_invalid(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, membership_id = "ORG-RC5", "ACC-RC5", "OM-RC5"
        listing_id = "NL-RC5"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-RC5",
            market_episode_id="ME-RC5",
        )
        _log_in(client, account_id)
        upload = _upload_one(client, org_id, listing_id, rights_confirmed=False)
        placement_id = upload.json()["media_placement_id"]
        response = client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 1, "media_placement_id": placement_id},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "invalid_cover"}

    def test_remove_placement_that_is_cover_clears_cover(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, listing_id, placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "6"
        )
        client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 2, "media_placement_id": placement_ids[0]},
            headers=_csrf_headers(),
        )
        remove_response = client.post(
            _remove_path(org_id, listing_id, placement_ids[0]),
            json={"expected_version": 3},
            headers=_csrf_headers(),
        )
        assert remove_response.status_code == 200
        assert remove_response.json()["outcome"] == "REMOVED"
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert gallery["cover_placement_id"] is None
        assert len(gallery["placements"]) == 1

    def test_remove_unknown_placement_is_not_found(self, client: TestClient, api_url: str) -> None:
        org_id, listing_id, _placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "7"
        )
        response = client.post(
            _remove_path(org_id, listing_id, str(uuid.uuid4())),
            json={"expected_version": 2},
            headers=_csrf_headers(),
        )
        assert response.status_code == 404
        assert response.json() == {"error": "placement_not_found"}

    def test_remove_with_stale_version_conflicts(self, client: TestClient, api_url: str) -> None:
        org_id, listing_id, placement_ids = self._setup_gallery_with_two_images(
            client, api_url, "8"
        )
        response = client.post(
            _remove_path(org_id, listing_id, placement_ids[0]),
            json={"expected_version": 1},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "version_conflict"}


# ---------------------------------------------------------------------------
# Retirement
# ---------------------------------------------------------------------------


class TestRetireAsset:
    def test_retire_own_asset_then_reuse_denied(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, membership_id = "ORG-RT1", "ACC-RT1", "OM-RT1"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        for tag in ("A", "B"):
            _create_listing(
                api_url,
                listing_id=f"NL-RT1-{tag}",
                org_id=org_id,
                account_id=account_id,
                membership_id=membership_id,
                physical_boat_id=f"PB-RT1-{tag}",
                market_episode_id=f"ME-RT1-{tag}",
            )
        _log_in(client, account_id)
        upload = _upload_one(client, org_id, "NL-RT1-A")
        asset_id = upload.json()["media_asset_id"]

        retire_response = client.post(_retire_path(org_id, asset_id), headers=_csrf_headers())
        assert retire_response.status_code == 200
        assert retire_response.json() == {"outcome": "RETIRED"}

        reuse_response = client.post(
            _reuse_path(org_id, "NL-RT1-B"),
            json={"media_asset_id": asset_id},
            headers=_csrf_headers(),
        )
        assert reuse_response.status_code == 404

    def test_retire_twice_is_conflict(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, membership_id = "ORG-RT2", "ACC-RT2", "OM-RT2"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-RT2",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-RT2",
            market_episode_id="ME-RT2",
        )
        _log_in(client, account_id)
        upload = _upload_one(client, org_id, "NL-RT2")
        asset_id = upload.json()["media_asset_id"]
        first = client.post(_retire_path(org_id, asset_id), headers=_csrf_headers())
        second = client.post(_retire_path(org_id, asset_id), headers=_csrf_headers())
        assert first.status_code == 200
        assert second.status_code == 409
        assert second.json() == {"error": "already_retired"}

    def test_retire_unknown_asset_is_not_found(self, client: TestClient, api_url: str) -> None:
        _seed_org_and_membership(
            api_url, org_id="ORG-RT3", account_id="ACC-RT3", membership_id="OM-RT3"
        )
        _log_in(client, "ACC-RT3")
        response = client.post(_retire_path("ORG-RT3", str(uuid.uuid4())), headers=_csrf_headers())
        assert response.status_code == 404
        assert response.json() == {"error": "asset_not_found"}


# ---------------------------------------------------------------------------
# Media library
# ---------------------------------------------------------------------------


class TestMediaLibrary:
    def test_library_is_organization_scoped(self, client: TestClient, api_url: str) -> None:
        org_a, account_a, membership_a = "ORG-LIB-A", "ACC-LIB-A", "OM-LIB-A"
        org_b, account_b, membership_b = "ORG-LIB-B", "ACC-LIB-B", "OM-LIB-B"
        _seed_org_and_membership(
            api_url, org_id=org_a, account_id=account_a, membership_id=membership_a
        )
        _seed_org_and_membership(
            api_url, org_id=org_b, account_id=account_b, membership_id=membership_b
        )
        _create_listing(
            api_url,
            listing_id="NL-LIB-A",
            org_id=org_a,
            account_id=account_a,
            membership_id=membership_a,
            physical_boat_id="PB-LIB-A",
            market_episode_id="ME-LIB-A",
        )
        _log_in(client, account_a)
        _upload_one(client, org_a, "NL-LIB-A")

        library_a = client.get(_library_path(org_a))
        assert library_a.status_code == 200
        assert len(library_a.json()["assets"]) == 1

        _log_in(client, account_b)
        library_b = client.get(_library_path(org_b))
        assert library_b.status_code == 200
        assert library_b.json()["assets"] == []


# ---------------------------------------------------------------------------
# Broker asset-bytes preview
# ---------------------------------------------------------------------------


class TestAssetBytesPreview:
    def test_own_asset_bytes_are_served(self, client: TestClient, api_url: str) -> None:
        org_id, account_id, membership_id = "ORG-AB1", "ACC-AB1", "OM-AB1"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-AB1",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-AB1",
            market_episode_id="ME-AB1",
        )
        _log_in(client, account_id)
        upload = _upload_one(client, org_id, "NL-AB1")
        asset_id = upload.json()["media_asset_id"]

        response = client.get(_asset_bytes_path(org_id, asset_id))
        assert response.status_code == 200
        assert response.headers["content-type"] == "image/jpeg"
        assert len(response.content) > 0

    def test_foreign_organization_asset_is_not_found(
        self, client: TestClient, api_url: str
    ) -> None:
        org_a, account_a, membership_a = "ORG-AB2A", "ACC-AB2A", "OM-AB2A"
        org_b, account_b, membership_b = "ORG-AB2B", "ACC-AB2B", "OM-AB2B"
        _seed_org_and_membership(
            api_url, org_id=org_a, account_id=account_a, membership_id=membership_a
        )
        _seed_org_and_membership(
            api_url, org_id=org_b, account_id=account_b, membership_id=membership_b
        )
        _create_listing(
            api_url,
            listing_id="NL-AB2A",
            org_id=org_a,
            account_id=account_a,
            membership_id=membership_a,
            physical_boat_id="PB-AB2A",
            market_episode_id="ME-AB2A",
        )
        _log_in(client, account_a)
        upload = _upload_one(client, org_a, "NL-AB2A")
        asset_id = upload.json()["media_asset_id"]

        _log_in(client, account_b)
        response = client.get(_asset_bytes_path(org_b, asset_id))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Independent review Finding A: original/quarantine vs. derivative separation
# ---------------------------------------------------------------------------


class TestOriginalDerivativeSeparation:
    def test_approved_upload_stores_two_distinct_keys_in_object_storage(
        self, client: TestClient, api_url: str, object_storage: InMemoryObjectStorage
    ) -> None:
        org_id, account_id, membership_id = "ORG-OD1", "ACC-OD1", "OM-OD1"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-OD1",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-OD1",
            market_episode_id="ME-OD1",
        )
        _log_in(client, account_id)
        raw_bytes = _jpeg_bytes()
        response = _upload_one(client, org_id, "NL-OD1", body=raw_bytes)
        assert response.status_code == 201

        gallery = client.get(_gallery_path(org_id, "NL-OD1")).json()
        asset_id = gallery["placements"][0]["media_asset"]["media_asset_id"]

        # The derivative served through the private broker preview route is
        # the safely-re-encoded JPEG -- never byte-identical to the raw
        # upload (contract §6.6: always re-encoded).
        preview = client.get(_asset_bytes_path(org_id, asset_id))
        assert preview.status_code == 200
        derivative_bytes = preview.content
        assert derivative_bytes != raw_bytes

        # The private/quarantine original is durably stored too, under a
        # distinct key never exposed by any route -- verified directly
        # against the injected fake store (contract: "no direct public
        # route for originals is introduced").
        original_keys = list(object_storage.keys_with_prefix("media/original/"))
        derivative_keys = list(object_storage.keys_with_prefix("media/derivative/"))
        assert len(original_keys) == 1
        assert len(derivative_keys) == 1
        assert original_keys[0] != derivative_keys[0]
        assert object_storage.get_object(original_keys[0]) == raw_bytes
        assert object_storage.get_object(derivative_keys[0]) == derivative_bytes

    def test_rejected_upload_still_quarantines_the_original(
        self, client: TestClient, api_url: str, object_storage: InMemoryObjectStorage
    ) -> None:
        org_id, account_id, membership_id = "ORG-OD2", "ACC-OD2", "OM-OD2"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-OD2",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-OD2",
            market_episode_id="ME-OD2",
        )
        _log_in(client, account_id)
        garbage = b"not an image at all, just plain bytes"
        response = _upload_one(client, org_id, "NL-OD2", body=garbage)
        assert response.status_code == 422

        # Contract §6: quarantine storage is the first ingestion step,
        # before any accept/reject decision -- a rejected upload's original
        # is still durably stored, and no derivative was ever created.
        original_keys = list(object_storage.keys_with_prefix("media/original/"))
        derivative_keys = list(object_storage.keys_with_prefix("media/derivative/"))
        assert len(original_keys) == 1
        assert derivative_keys == []
        assert object_storage.get_object(original_keys[0]) == garbage

    def test_broker_preview_route_never_serves_an_original_key(
        self, client: TestClient, api_url: str, object_storage: InMemoryObjectStorage
    ) -> None:
        """Defense in depth: even if an attacker somehow learned an
        `original_object_key` value, the broker preview route only ever
        looks up assets by `media_asset_id` and always resolves the
        derivative -- there is no route parameterized by a raw object key
        at all."""
        org_id, account_id, membership_id = "ORG-OD3", "ACC-OD3", "OM-OD3"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-OD3",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-OD3",
            market_episode_id="ME-OD3",
        )
        _log_in(client, account_id)
        _upload_one(client, org_id, "NL-OD3")
        original_keys = list(object_storage.keys_with_prefix("media/original/"))
        assert len(original_keys) == 1
        # There is no route that accepts an object key directly -- attempting
        # to use one as if it were a media_asset_id is simply not found.
        response = client.get(_asset_bytes_path(org_id, original_keys[0]))
        assert response.status_code == 404


# ---------------------------------------------------------------------------
# Independent review Finding B: D14 provenance at the HTTP boundary
# ---------------------------------------------------------------------------


class TestSourceReferenceHttp:
    def test_upload_with_source_reference_is_persisted_and_readable(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, membership_id = "ORG-SR1", "ACC-SR1", "OM-SR1"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-SR1",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-SR1",
            market_episode_id="ME-SR1",
        )
        _log_in(client, account_id)
        response = _upload_one(
            client, org_id, "NL-SR1", source_reference="Photographed by ACME Yacht Photography"
        )
        assert response.status_code == 201
        gallery = client.get(_gallery_path(org_id, "NL-SR1")).json()
        asset = gallery["placements"][0]["media_asset"]
        assert asset["source_kind"] == "BROKER_UPLOAD"
        assert asset["source_reference"] == "Photographed by ACME Yacht Photography"

    def test_upload_without_source_reference_leaves_it_null(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, membership_id = "ORG-SR2", "ACC-SR2", "OM-SR2"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-SR2",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-SR2",
            market_episode_id="ME-SR2",
        )
        _log_in(client, account_id)
        response = _upload_one(client, org_id, "NL-SR2")
        assert response.status_code == 201
        gallery = client.get(_gallery_path(org_id, "NL-SR2")).json()
        asset = gallery["placements"][0]["media_asset"]
        assert asset["source_kind"] == "BROKER_UPLOAD"
        assert asset["source_reference"] is None

    def test_oversized_source_reference_is_rejected_and_writes_nothing(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, membership_id = "ORG-SR3", "ACC-SR3", "OM-SR3"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id="NL-SR3",
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-SR3",
            market_episode_id="ME-SR3",
        )
        _log_in(client, account_id)
        too_long = "x" * (MAX_SOURCE_REFERENCE_LENGTH + 1)
        response = _upload_one(client, org_id, "NL-SR3", source_reference=too_long)
        assert response.status_code == 400
        assert response.json() == {"error": "invalid_source_reference"}
        gallery = client.get(_gallery_path(org_id, "NL-SR3")).json()
        assert gallery["placements"] == []


# ---------------------------------------------------------------------------
# Independent review Finding C: ACTIVE listing last-valid-image/cover
# protection at the HTTP boundary
# ---------------------------------------------------------------------------


class TestActiveListingProtectionHttp:
    def _active_listing_with_one_cover_image(
        self, client: TestClient, api_url: str, suffix: str
    ) -> tuple[str, str, str]:
        org_id, account_id, membership_id = (
            f"ORG-ALH{suffix}",
            f"ACC-ALH{suffix}",
            f"OM-ALH{suffix}",
        )
        listing_id = f"NL-ALH{suffix}"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id=f"PB-ALH{suffix}",
            market_episode_id=f"ME-ALH{suffix}",
        )
        _log_in(client, account_id)
        upload = _upload_one(client, org_id, listing_id)
        placement_id = upload.json()["media_placement_id"]
        cover_response = client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 1, "media_placement_id": placement_id},
            headers=_csrf_headers(),
        )
        assert cover_response.status_code == 200
        _publish_listing(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)
        return org_id, listing_id, placement_id

    def test_remove_last_valid_image_on_active_listing_is_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, listing_id, placement_id = self._active_listing_with_one_cover_image(
            client, api_url, "1"
        )
        response = client.post(
            _remove_path(org_id, listing_id, placement_id),
            json={"expected_version": 2},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "active_listing_conflict"}
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert len(gallery["placements"]) == 1

    def test_clear_cover_on_active_listing_is_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, listing_id, placement_id = self._active_listing_with_one_cover_image(
            client, api_url, "2"
        )
        response = client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 2, "media_placement_id": None},
            headers=_csrf_headers(),
        )
        assert response.status_code == 409
        assert response.json() == {"error": "active_listing_conflict"}
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert gallery["cover_placement_id"] == placement_id

    def test_retire_last_valid_image_asset_on_active_listing_is_conflict(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, listing_id, _placement_id = self._active_listing_with_one_cover_image(
            client, api_url, "3"
        )
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        asset_id = gallery["placements"][0]["media_asset"]["media_asset_id"]
        response = client.post(_retire_path(org_id, asset_id), headers=_csrf_headers())
        assert response.status_code == 409
        assert response.json() == {"error": "active_listing_conflict"}

    def test_safe_removal_with_two_valid_images_remains_allowed(
        self, client: TestClient, api_url: str
    ) -> None:
        org_id, account_id, membership_id = "ORG-ALH4", "ACC-ALH4", "OM-ALH4"
        listing_id = "NL-ALH4"
        _seed_org_and_membership(
            api_url, org_id=org_id, account_id=account_id, membership_id=membership_id
        )
        _create_listing(
            api_url,
            listing_id=listing_id,
            org_id=org_id,
            account_id=account_id,
            membership_id=membership_id,
            physical_boat_id="PB-ALH4",
            market_episode_id="ME-ALH4",
        )
        _log_in(client, account_id)
        first_upload = _upload_one(client, org_id, listing_id)
        second_upload = _upload_one(client, org_id, listing_id)
        first_placement_id = first_upload.json()["media_placement_id"]
        second_placement_id = second_upload.json()["media_placement_id"]
        client.post(
            _cover_path(org_id, listing_id),
            json={"expected_version": 2, "media_placement_id": first_placement_id},
            headers=_csrf_headers(),
        )
        _publish_listing(api_url, listing_id=listing_id, org_id=org_id, account_id=account_id)

        response = client.post(
            _remove_path(org_id, listing_id, second_placement_id),
            json={"expected_version": 3},
            headers=_csrf_headers(),
        )
        assert response.status_code == 200
        assert response.json()["outcome"] == "REMOVED"
        gallery = client.get(_gallery_path(org_id, listing_id)).json()
        assert len(gallery["placements"]) == 1
        assert gallery["cover_placement_id"] == first_placement_id
