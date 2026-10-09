"""Contract §16 partial-storage/database-failure proof for SLICE-0068's
mixed-media gallery upload path (independent review, second amendment).

Exercises `hullq.application.media_gallery.upload_image_for_organization`
directly (not through FastAPI/HTTP) against a real PostgreSQL schema, with a
deliberately failing `ObjectStorage` double and a monkeypatched persistence
call, proving:

- an original-store failure leaves zero database trace and never attempts
  the derivative write;
- a derivative-store failure (after the original succeeded) leaves zero
  database trace -- the durable quarantine object is not retroactively
  deleted, but no row claims it as an asset;
- a database failure after both object writes succeed leaves zero database
  trace, but honestly does NOT claim the already-durable storage objects
  vanish -- they become clearly namespaced, unreferenced objects eligible
  for later GC (contract §16 explicitly permits this for v0.1);
- a retry after any such failure produces a clean, uncorrupted gallery
  state (no stale position/version left over from the failed attempt).
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta
from typing import Any
from urllib.parse import quote, urlsplit, urlunsplit

import psycopg
import pytest
from PIL import Image

from hullq.application.media_gallery import (
    ReuseAssetOutcome,
    UploadImageOutcome,
    reuse_asset_for_organization,
    upload_image_for_organization,
)
from hullq.domain.broker_access import AuthenticatedIdentity, Provider
from hullq.domain.market_identity import (
    MarketEpisode,
    MarketEpisodeId,
    NativeListing,
    NativeListingId,
    PhysicalBoat,
    PhysicalBoatId,
)
from hullq.domain.media_gallery import MediaAssetId, MediaBackupProviderKind
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
from hullq.persistence.media_gallery import fetch_gallery_state, fetch_media_asset
from hullq.persistence.native_listing import create_native_listing
from hullq.persistence.physical_boat import create_physical_boat
from hullq.security.session_token import SessionClaims
from hullq.storage.object_storage import InMemoryObjectStorage

_ORIGINAL_KEY_PREFIX = "media/original/"
_DERIVATIVE_KEY_PREFIX = "media/derivative/"


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
    schema_name = f"hullq_s0068partial_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        url = _with_search_path(db_url, schema_name)
        baseline = prepare_alembic_baseline(url)
        assert baseline.accepted, baseline.reason
        alembic_upgrade_head(url)
        yield url
    finally:
        _drop_schema(db_url, schema_name)


def _seed_org_account_membership_and_listing(
    api_url: str, suffix: str
) -> tuple[MarketplaceOrganizationId, AccountId, NativeListingId]:
    org_id = MarketplaceOrganizationId(f"ORG-PF{suffix}")
    account_id = AccountId(f"ACC-PF{suffix}")
    listing_id = NativeListingId(f"NL-PF{suffix}")
    conn = psycopg.connect(api_url)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO accounts (account_id) VALUES (%s) ON CONFLICT DO NOTHING",
                [account_id.value],
            )
        conn.commit()
        org = MarketplaceOrganization(
            id=org_id,
            professional_category=ProfessionalCategory.BROKER,
            publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
        )
        seed_marketplace_organization(conn, org)
        membership = OrganizationMembership(
            id=OrganizationMembershipId(f"OM-PF{suffix}"),
            account_id=account_id,
            organization_id=org_id,
            roles=frozenset({MembershipRole.PUBLISHER}),
            state=MembershipState.ACTIVE,
        )
        seed_organization_membership(conn, membership)
        conn.commit()
        create_physical_boat(conn, physical_boat=PhysicalBoat(id=PhysicalBoatId(f"PB-PF{suffix}")))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(
                id=MarketEpisodeId(f"ME-PF{suffix}"),
                physical_boat_id=PhysicalBoatId(f"PB-PF{suffix}"),
            ),
        )
        create_native_listing(
            conn,
            account_id=account_id,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(
                id=listing_id, market_episode_id=MarketEpisodeId(f"ME-PF{suffix}")
            ),
        )
        conn.commit()
    finally:
        conn.close()
    return org_id, account_id, listing_id


def _session(account_id: AccountId) -> SessionClaims:
    return SessionClaims(
        account_id=account_id,
        identity=AuthenticatedIdentity(
            provider=Provider.AUTH0,
            issuer="https://issuer.test/",
            subject=f"subject-{account_id.value}",
            auth_time=datetime.now(UTC),
            mfa_satisfied=True,
        ),
        issued_at=datetime.now(UTC),
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )


def _jpeg_bytes(
    size: tuple[int, int] = (64, 32), color: tuple[int, int, int] = (200, 10, 10)
) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", size, color).save(buf, format="JPEG")
    return buf.getvalue()


class _StorageWriteError(RuntimeError):
    """Simulated object-storage failure for these partial-failure proofs."""


class _SelectivelyFailingObjectStorage:
    """Wraps a real `InMemoryObjectStorage`, failing exactly the one write
    whose key starts with *fail_key_prefix* -- everything else behaves
    exactly like the real fake, including the durable writes that already
    completed before the failure point."""

    def __init__(self, delegate: InMemoryObjectStorage, *, fail_key_prefix: str) -> None:
        self.delegate = delegate
        self._fail_key_prefix = fail_key_prefix
        self.attempted_keys: list[str] = []

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        self.attempted_keys.append(key)
        if key.startswith(self._fail_key_prefix):
            raise _StorageWriteError(f"simulated storage failure for {key}")
        self.delegate.put_object(key, data, content_type=content_type)

    def get_object(self, key: str) -> bytes:
        return self.delegate.get_object(key)

    def delete_object(self, key: str) -> None:
        self.delegate.delete_object(key)


class TestPartialStorageFailure:
    """Independent review (second amendment): contract §16 re-check --
    'partial storage/database failures never promote missing/unprocessed
    bytes to public truth', proved against real failure injection rather
    than only asserted in a docstring."""

    def test_original_store_failure_leaves_zero_database_trace(self, api_url: str) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "1")
        storage = _SelectivelyFailingObjectStorage(
            InMemoryObjectStorage(), fail_key_prefix=_ORIGINAL_KEY_PREFIX
        )
        conn = psycopg.connect(api_url)
        try:
            with pytest.raises(_StorageWriteError):
                upload_image_for_organization(
                    conn,
                    _session(account_id),
                    org_id.value,
                    listing_id.value,
                    raw_bytes=_jpeg_bytes(),
                    rights_confirmed=True,
                    object_storage=storage,
                    backup_object_storage=InMemoryObjectStorage(),
                )
            assert storage.attempted_keys == [storage.attempted_keys[0]]
            assert storage.attempted_keys[0].startswith(_ORIGINAL_KEY_PREFIX)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM media_assets WHERE owner_organization_id = %s",
                    [org_id.value],
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == 0
        finally:
            conn.close()

    def test_derivative_store_failure_leaves_zero_database_trace(self, api_url: str) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "2")
        delegate = InMemoryObjectStorage()
        storage = _SelectivelyFailingObjectStorage(delegate, fail_key_prefix=_DERIVATIVE_KEY_PREFIX)
        conn = psycopg.connect(api_url)
        try:
            with pytest.raises(_StorageWriteError):
                upload_image_for_organization(
                    conn,
                    _session(account_id),
                    org_id.value,
                    listing_id.value,
                    raw_bytes=_jpeg_bytes(),
                    rights_confirmed=True,
                    object_storage=storage,
                    backup_object_storage=InMemoryObjectStorage(),
                )
            # The original was durably written before processing/derivative
            # storage was ever attempted -- this is honestly not a
            # zero-storage-trace outcome (contract §16 explicitly permits
            # leaving it as a clearly-namespaced, unreferenced GC candidate).
            assert len(delegate.keys_with_prefix(_ORIGINAL_KEY_PREFIX)) == 1
            assert len(delegate.keys_with_prefix(_DERIVATIVE_KEY_PREFIX)) == 0
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM media_assets WHERE owner_organization_id = %s",
                    [org_id.value],
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == 0
        finally:
            conn.close()

    def test_db_failure_after_object_writes_leaves_zero_database_trace(
        self, api_url: str, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "3")
        storage = InMemoryObjectStorage()

        def _boom(*_args: Any, **_kwargs: Any) -> None:
            raise RuntimeError("simulated database failure")

        monkeypatch.setattr("hullq.application.media_gallery.insert_approved_media_asset", _boom)

        conn = psycopg.connect(api_url)
        try:
            with pytest.raises(RuntimeError, match="simulated database failure"):
                upload_image_for_organization(
                    conn,
                    _session(account_id),
                    org_id.value,
                    listing_id.value,
                    raw_bytes=_jpeg_bytes(),
                    rights_confirmed=True,
                    object_storage=storage,
                    backup_object_storage=InMemoryObjectStorage(),
                )
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM media_assets WHERE owner_organization_id = %s",
                    [org_id.value],
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == 0
                cur.execute(
                    "SELECT count(*) FROM media_placements mp "
                    "JOIN native_listings nl ON nl.native_listing_id = mp.native_listing_id "
                    "WHERE nl.native_listing_id = %s",
                    [listing_id.value],
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == 0
            # Honest acknowledgment (contract §16, v0.1 explicitly acceptable):
            # both object-storage writes already durably completed before the
            # database failure and are NOT synchronously rolled back -- they
            # remain as clearly namespaced, unreferenced objects, never
            # claimed by any database row, left for later GC.
            assert len(storage.keys_with_prefix(_ORIGINAL_KEY_PREFIX)) == 1
            assert len(storage.keys_with_prefix(_DERIVATIVE_KEY_PREFIX)) == 1
        finally:
            conn.close()

    def test_retry_after_failure_produces_clean_gallery_state(self, api_url: str) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "4")
        failing_storage = _SelectivelyFailingObjectStorage(
            InMemoryObjectStorage(), fail_key_prefix=_ORIGINAL_KEY_PREFIX
        )
        conn = psycopg.connect(api_url)
        try:
            with pytest.raises(_StorageWriteError):
                upload_image_for_organization(
                    conn,
                    _session(account_id),
                    org_id.value,
                    listing_id.value,
                    raw_bytes=_jpeg_bytes(),
                    rights_confirmed=True,
                    object_storage=failing_storage,
                    backup_object_storage=InMemoryObjectStorage(),
                )

            working_storage = InMemoryObjectStorage()
            result = upload_image_for_organization(
                conn,
                _session(account_id),
                org_id.value,
                listing_id.value,
                raw_bytes=_jpeg_bytes(),
                rights_confirmed=True,
                object_storage=working_storage,
                backup_object_storage=InMemoryObjectStorage(),
            )
            assert result.outcome is UploadImageOutcome.CREATED
            assert result.gallery_version == 1

            gallery = fetch_gallery_state(conn, listing_id)
            assert gallery.gallery_version == 1
            assert len(gallery.placements) == 1
            assert gallery.placements[0].position == 0
        finally:
            conn.close()


def _seed_second_listing_same_org(
    api_url: str, *, org: MarketplaceOrganization, account_id: AccountId, suffix: str
) -> NativeListingId:
    """A second NativeListing owned by the identical Organization, for the
    same-Organization reuse proof below (contract §9)."""
    listing_id = NativeListingId(f"NL-PF{suffix}")
    physical_boat_id = PhysicalBoatId(f"PB-PF{suffix}")
    market_episode_id = MarketEpisodeId(f"ME-PF{suffix}")
    membership = OrganizationMembership(
        id=OrganizationMembershipId(f"OM-PF{suffix}"),
        account_id=account_id,
        organization_id=org.id,
        roles=frozenset({MembershipRole.PUBLISHER}),
        state=MembershipState.ACTIVE,
    )
    conn = psycopg.connect(api_url)
    try:
        create_physical_boat(conn, physical_boat=PhysicalBoat(id=physical_boat_id))
        create_market_episode(
            conn,
            market_episode=MarketEpisode(id=market_episode_id, physical_boat_id=physical_boat_id),
        )
        create_native_listing(
            conn,
            account_id=account_id,
            candidate_organization=org,
            membership=membership,
            listing=NativeListing(id=listing_id, market_episode_id=market_episode_id),
        )
        conn.commit()
    finally:
        conn.close()
    return listing_id


def _org_for(org_id: MarketplaceOrganizationId) -> MarketplaceOrganization:
    return MarketplaceOrganization(
        id=org_id,
        professional_category=ProfessionalCategory.BROKER,
        publishing_eligibility=OrganizationPublishingEligibility.ELIGIBLE,
    )


class TestIndependentOriginalCopyRedundancy:
    """SLICE-0080 (`specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md`
    §14 acceptance proof matrix) at the application-orchestration level --
    the same real-failure-injection discipline as `TestPartialStorageFailure`
    above, extended to the required independent B2 write."""

    def test_backup_write_failure_after_primary_success_leaves_zero_database_trace(
        self, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "5")
        primary_storage = InMemoryObjectStorage()
        failing_backup = _SelectivelyFailingObjectStorage(
            InMemoryObjectStorage(), fail_key_prefix=_ORIGINAL_KEY_PREFIX
        )
        conn = psycopg.connect(api_url)
        try:
            with pytest.raises(_StorageWriteError):
                upload_image_for_organization(
                    conn,
                    _session(account_id),
                    org_id.value,
                    listing_id.value,
                    raw_bytes=_jpeg_bytes(),
                    rights_confirmed=True,
                    object_storage=primary_storage,
                    backup_object_storage=failing_backup,
                )
            # The primary original is already durably written -- an honest
            # orphan (contract §6) -- but the independent copy never
            # succeeded, and image processing/derivative/database work must
            # never have been reached.
            assert len(primary_storage.keys_with_prefix(_ORIGINAL_KEY_PREFIX)) == 1
            assert len(primary_storage.keys_with_prefix(_DERIVATIVE_KEY_PREFIX)) == 0
            assert failing_backup.attempted_keys == [failing_backup.attempted_keys[0]]
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count(*) FROM media_assets WHERE owner_organization_id = %s",
                    [org_id.value],
                )
                row = cur.fetchone()
                assert row is not None
                assert row[0] == 0
        finally:
            conn.close()

    def test_retry_after_backup_failure_produces_clean_gallery_state(self, api_url: str) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "6")
        failing_backup = _SelectivelyFailingObjectStorage(
            InMemoryObjectStorage(), fail_key_prefix=_ORIGINAL_KEY_PREFIX
        )
        conn = psycopg.connect(api_url)
        try:
            with pytest.raises(_StorageWriteError):
                upload_image_for_organization(
                    conn,
                    _session(account_id),
                    org_id.value,
                    listing_id.value,
                    raw_bytes=_jpeg_bytes(),
                    rights_confirmed=True,
                    object_storage=InMemoryObjectStorage(),
                    backup_object_storage=failing_backup,
                )

            result = upload_image_for_organization(
                conn,
                _session(account_id),
                org_id.value,
                listing_id.value,
                raw_bytes=_jpeg_bytes(),
                rights_confirmed=True,
                object_storage=InMemoryObjectStorage(),
                backup_object_storage=InMemoryObjectStorage(),
            )
            assert result.outcome is UploadImageOutcome.CREATED
            assert result.gallery_version == 1

            gallery = fetch_gallery_state(conn, listing_id)
            assert gallery.gallery_version == 1
            assert len(gallery.placements) == 1
        finally:
            conn.close()

    def test_dual_success_approved_upload_records_established_redundancy(
        self, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "7")
        primary_storage = InMemoryObjectStorage()
        backup_storage = InMemoryObjectStorage()
        conn = psycopg.connect(api_url)
        try:
            raw_bytes = _jpeg_bytes()
            result = upload_image_for_organization(
                conn,
                _session(account_id),
                org_id.value,
                listing_id.value,
                raw_bytes=raw_bytes,
                rights_confirmed=True,
                object_storage=primary_storage,
                backup_object_storage=backup_storage,
            )
            assert result.outcome is UploadImageOutcome.CREATED
            assert result.media_asset_id is not None

            asset = fetch_media_asset(conn, MediaAssetId(result.media_asset_id))
            assert asset is not None
            assert asset.has_established_backup
            assert asset.backup_provider is MediaBackupProviderKind.BACKBLAZE_B2
            assert asset.backup_object_key == asset.original_object_key
            assert asset.backup_established_at is not None

            # The independent copy holds byte-identical content under the
            # identical opaque key (contract §4: same key, both roles).
            assert backup_storage.get_object(asset.backup_object_key) == raw_bytes
        finally:
            conn.close()

    def test_dual_success_rejected_upload_retains_established_redundancy(
        self, api_url: str
    ) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "8")
        conn = psycopg.connect(api_url)
        try:
            result = upload_image_for_organization(
                conn,
                _session(account_id),
                org_id.value,
                listing_id.value,
                raw_bytes=b"not an image at all, just plain bytes",
                rights_confirmed=True,
                object_storage=InMemoryObjectStorage(),
                backup_object_storage=InMemoryObjectStorage(),
            )
            assert result.outcome is UploadImageOutcome.REJECTED

            with conn.cursor() as cur:
                cur.execute(
                    "SELECT backup_provider, backup_object_key, backup_established_at "
                    "FROM media_assets WHERE owner_organization_id = %s",
                    [org_id.value],
                )
                row = cur.fetchone()
                assert row is not None
                backup_provider, backup_object_key, backup_established_at = row
                assert backup_provider == "BACKBLAZE_B2"
                assert backup_object_key is not None
                assert backup_established_at is not None
        finally:
            conn.close()

    def test_same_organization_reuse_creates_no_second_backup_copy(self, api_url: str) -> None:
        org_id, account_id, listing_id = _seed_org_account_membership_and_listing(api_url, "9")
        org = _org_for(org_id)
        second_listing_id = _seed_second_listing_same_org(
            api_url, org=org, account_id=account_id, suffix="9b"
        )
        primary_storage = InMemoryObjectStorage()
        backup_storage = InMemoryObjectStorage()
        conn = psycopg.connect(api_url)
        try:
            upload_result = upload_image_for_organization(
                conn,
                _session(account_id),
                org_id.value,
                listing_id.value,
                raw_bytes=_jpeg_bytes(),
                rights_confirmed=True,
                object_storage=primary_storage,
                backup_object_storage=backup_storage,
            )
            assert upload_result.outcome is UploadImageOutcome.CREATED
            assert upload_result.media_asset_id is not None
            backup_keys_after_upload = backup_storage.keys_with_prefix(_ORIGINAL_KEY_PREFIX)
            assert len(backup_keys_after_upload) == 1

            reuse_result = reuse_asset_for_organization(
                conn,
                _session(account_id),
                org_id.value,
                second_listing_id.value,
                upload_result.media_asset_id,
            )
            assert reuse_result.outcome is ReuseAssetOutcome.CREATED

            # Reuse never touches object storage at all -- the backup store
            # must hold exactly the same one key as before (contract §8:
            # "same-Organization MediaAsset reuse ... MUST NOT create a
            # second backup copy").
            assert backup_storage.keys_with_prefix(_ORIGINAL_KEY_PREFIX) == backup_keys_after_upload
        finally:
            conn.close()
