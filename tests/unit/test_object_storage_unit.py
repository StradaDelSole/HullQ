"""Pure unit tests for SLICE-0068/SLICE-0080 object-storage boundary —
`hullq.storage.object_storage`.

No real network/R2/B2 dependency (contract §17 / redundancy contract §11:
"live ... credentials are not required in ordinary CI"): `InMemoryObjectStorage`
is exercised directly, and `R2ObjectStorage`/`B2ObjectStorage` are each
exercised against a mocked `boto3`-shaped client so their request
construction and error mapping are proven deterministically.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from botocore.exceptions import ClientError

from hullq.storage.object_storage import (
    HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV,
    HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV,
    HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV,
    HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV,
    HULLQ_MEDIA_BACKUP_B2_REGION_ENV,
    HULLQ_R2_ACCESS_KEY_ID_ENV,
    HULLQ_R2_ACCOUNT_ID_ENV,
    HULLQ_R2_BUCKET_ENV,
    HULLQ_R2_SECRET_ACCESS_KEY_ENV,
    B2ObjectStorage,
    B2ObjectStorageConfig,
    InMemoryObjectStorage,
    ObjectNotFoundError,
    ObjectStorageConfigError,
    R2ObjectStorage,
    R2ObjectStorageConfig,
    get_b2_object_storage_config,
    get_r2_object_storage_config,
)


class TestInMemoryObjectStorage:
    def test_put_then_get_round_trips_bytes(self) -> None:
        store = InMemoryObjectStorage()
        store.put_object("media/a.jpg", b"hello", content_type="image/jpeg")
        assert store.get_object("media/a.jpg") == b"hello"

    def test_get_missing_key_raises_not_found(self) -> None:
        store = InMemoryObjectStorage()
        with pytest.raises(ObjectNotFoundError):
            store.get_object("media/missing.jpg")

    def test_delete_is_idempotent(self) -> None:
        store = InMemoryObjectStorage()
        store.put_object("media/a.jpg", b"hello", content_type="image/jpeg")
        store.delete_object("media/a.jpg")
        store.delete_object("media/a.jpg")  # second delete: no error
        assert not store.contains("media/a.jpg")

    def test_empty_key_rejected(self) -> None:
        store = InMemoryObjectStorage()
        with pytest.raises(ValueError, match="non-empty"):
            store.put_object("", b"hello", content_type="image/jpeg")

    def test_distinct_instances_never_share_state(self) -> None:
        a = InMemoryObjectStorage()
        b = InMemoryObjectStorage()
        a.put_object("media/a.jpg", b"hello", content_type="image/jpeg")
        assert not b.contains("media/a.jpg")


class TestR2ObjectStorageConfig:
    def test_get_config_reads_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(HULLQ_R2_ACCOUNT_ID_ENV, "acct-1")
        monkeypatch.setenv(HULLQ_R2_ACCESS_KEY_ID_ENV, "key-1")
        monkeypatch.setenv(HULLQ_R2_SECRET_ACCESS_KEY_ENV, "secret-1")
        monkeypatch.setenv(HULLQ_R2_BUCKET_ENV, "bucket-1")
        config = get_r2_object_storage_config()
        assert config.account_id == "acct-1"
        assert config.bucket == "bucket-1"
        assert config.endpoint_url == "https://acct-1.r2.cloudflarestorage.com"

    @pytest.mark.parametrize(
        "missing_env",
        [
            HULLQ_R2_ACCOUNT_ID_ENV,
            HULLQ_R2_ACCESS_KEY_ID_ENV,
            HULLQ_R2_SECRET_ACCESS_KEY_ENV,
            HULLQ_R2_BUCKET_ENV,
        ],
    )
    def test_missing_any_variable_fails_fast(
        self, monkeypatch: pytest.MonkeyPatch, missing_env: str
    ) -> None:
        for env_var in (
            HULLQ_R2_ACCOUNT_ID_ENV,
            HULLQ_R2_ACCESS_KEY_ID_ENV,
            HULLQ_R2_SECRET_ACCESS_KEY_ENV,
            HULLQ_R2_BUCKET_ENV,
        ):
            monkeypatch.setenv(env_var, "" if env_var == missing_env else "x")
        with pytest.raises(ObjectStorageConfigError, match=missing_env):
            get_r2_object_storage_config()

    def test_repr_never_includes_credentials(self) -> None:
        config = R2ObjectStorageConfig(
            account_id="acct-1",
            access_key_id="SECRET-KEY-ID",
            secret_access_key="SUPER-SECRET-VALUE",
            bucket="bucket-1",
        )
        rendered = repr(config)
        assert "SECRET-KEY-ID" not in rendered
        assert "SUPER-SECRET-VALUE" not in rendered


def _client_error(code: str, message: str = "boom") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "GetObject")


class TestR2ObjectStorageAdapter:
    def test_put_object_calls_client_with_opaque_key_and_no_local_disk(self) -> None:
        client = MagicMock()
        storage = R2ObjectStorage(client=client, bucket="bucket-1")
        storage.put_object("media/xyz.jpg", b"bytes-here", content_type="image/jpeg")
        client.put_object.assert_called_once_with(
            Bucket="bucket-1", Key="media/xyz.jpg", Body=b"bytes-here", ContentType="image/jpeg"
        )

    def test_get_object_returns_body_bytes(self) -> None:
        client = MagicMock()
        body = MagicMock()
        body.read.return_value = b"the-bytes"
        client.get_object.return_value = {"Body": body}
        storage = R2ObjectStorage(client=client, bucket="bucket-1")
        assert storage.get_object("media/xyz.jpg") == b"the-bytes"
        client.get_object.assert_called_once_with(Bucket="bucket-1", Key="media/xyz.jpg")

    def test_get_object_missing_key_raises_not_found(self) -> None:
        client = MagicMock()
        client.get_object.side_effect = _client_error("NoSuchKey")
        storage = R2ObjectStorage(client=client, bucket="bucket-1")
        with pytest.raises(ObjectNotFoundError):
            storage.get_object("media/missing.jpg")

    def test_get_object_other_error_never_leaks_credentials(self) -> None:
        client = MagicMock()
        client.get_object.side_effect = _client_error(
            "InternalError", message="request failed for secret=SUPER-SECRET signature=abc123"
        )
        storage = R2ObjectStorage(client=client, bucket="bucket-1")
        with pytest.raises(ObjectStorageConfigError) as exc_info:
            storage.get_object("media/xyz.jpg")
        assert "SUPER-SECRET" not in str(exc_info.value)
        assert "InternalError" in str(exc_info.value)

    def test_delete_object_calls_client(self) -> None:
        client = MagicMock()
        storage = R2ObjectStorage(client=client, bucket="bucket-1")
        storage.delete_object("media/xyz.jpg")
        client.delete_object.assert_called_once_with(Bucket="bucket-1", Key="media/xyz.jpg")

    def test_empty_bucket_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            R2ObjectStorage(client=MagicMock(), bucket="")


# ---------------------------------------------------------------------------
# SLICE-0080: Backblaze B2 independent-original-copy boundary -- deliberately
# mirrors every `TestR2Object*` proof above (contract §11: "live Backblaze
# credentials are not required in ordinary CI" / §12: "a second, distinct
# adapter").
# ---------------------------------------------------------------------------


class TestB2ObjectStorageConfig:
    def test_get_config_reads_environment(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv(
            HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV, "https://s3.eu-central-003.backblazeb2.com"
        )
        monkeypatch.setenv(HULLQ_MEDIA_BACKUP_B2_REGION_ENV, "eu-central-003")
        monkeypatch.setenv(HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV, "key-1")
        monkeypatch.setenv(HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV, "app-key-1")
        monkeypatch.setenv(HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV, "bucket-1")
        config = get_b2_object_storage_config()
        assert config.endpoint == "https://s3.eu-central-003.backblazeb2.com"
        assert config.endpoint_url == config.endpoint
        assert config.region == "eu-central-003"
        assert config.bucket == "bucket-1"

    @pytest.mark.parametrize(
        "missing_env",
        [
            HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV,
            HULLQ_MEDIA_BACKUP_B2_REGION_ENV,
            HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV,
            HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV,
            HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV,
        ],
    )
    def test_missing_any_variable_fails_fast(
        self, monkeypatch: pytest.MonkeyPatch, missing_env: str
    ) -> None:
        for env_var in (
            HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV,
            HULLQ_MEDIA_BACKUP_B2_REGION_ENV,
            HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV,
            HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV,
            HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV,
        ):
            monkeypatch.setenv(env_var, "" if env_var == missing_env else "x")
        with pytest.raises(ObjectStorageConfigError, match=missing_env):
            get_b2_object_storage_config()

    def test_repr_never_includes_credentials(self) -> None:
        config = B2ObjectStorageConfig(
            endpoint="https://s3.eu-central-003.backblazeb2.com",
            region="eu-central-003",
            key_id="SECRET-KEY-ID",
            application_key="SUPER-SECRET-VALUE",
            bucket="bucket-1",
        )
        rendered = repr(config)
        assert "SECRET-KEY-ID" not in rendered
        assert "SUPER-SECRET-VALUE" not in rendered

    def test_endpoint_is_never_derived_or_hardcoded(self) -> None:
        """Contract §11: "MUST NOT be hardcoded in domain logic" -- unlike
        R2's account-id-derived `endpoint_url`, B2's is read back verbatim,
        whatever value configuration supplied."""
        config = B2ObjectStorageConfig(
            endpoint="https://s3.us-west-004.backblazeb2.com",
            region="us-west-004",
            key_id="k",
            application_key="s",
            bucket="b",
        )
        assert config.endpoint_url == "https://s3.us-west-004.backblazeb2.com"


def _b2_client_error(code: str, message: str = "boom") -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": message}}, "GetObject")


class TestB2ObjectStorageAdapter:
    def test_is_a_distinct_class_from_r2_object_storage(self) -> None:
        """Contract §12: "passing the same resolved Cloudflare R2 store for
        both roles is not a valid production configuration" -- structurally
        guaranteed here by construction: these are two different classes,
        never the same adapter instantiated twice."""
        assert B2ObjectStorage is not R2ObjectStorage
        assert not issubclass(B2ObjectStorage, R2ObjectStorage)
        assert not issubclass(R2ObjectStorage, B2ObjectStorage)

    def test_put_object_calls_client_with_opaque_key_and_no_local_disk(self) -> None:
        client = MagicMock()
        storage = B2ObjectStorage(client=client, bucket="backup-bucket-1")
        storage.put_object(
            "media/original/xyz", b"bytes-here", content_type="application/octet-stream"
        )
        client.put_object.assert_called_once_with(
            Bucket="backup-bucket-1",
            Key="media/original/xyz",
            Body=b"bytes-here",
            ContentType="application/octet-stream",
        )

    def test_get_object_returns_body_bytes(self) -> None:
        client = MagicMock()
        body = MagicMock()
        body.read.return_value = b"the-bytes"
        client.get_object.return_value = {"Body": body}
        storage = B2ObjectStorage(client=client, bucket="backup-bucket-1")
        assert storage.get_object("media/original/xyz") == b"the-bytes"
        client.get_object.assert_called_once_with(
            Bucket="backup-bucket-1", Key="media/original/xyz"
        )

    def test_get_object_missing_key_raises_not_found(self) -> None:
        client = MagicMock()
        client.get_object.side_effect = _b2_client_error("NoSuchKey")
        storage = B2ObjectStorage(client=client, bucket="backup-bucket-1")
        with pytest.raises(ObjectNotFoundError):
            storage.get_object("media/original/missing")

    def test_get_object_other_error_never_leaks_credentials(self) -> None:
        client = MagicMock()
        client.get_object.side_effect = _b2_client_error(
            "InternalError", message="request failed for keyId=SUPER-SECRET signature=abc123"
        )
        storage = B2ObjectStorage(client=client, bucket="backup-bucket-1")
        with pytest.raises(ObjectStorageConfigError) as exc_info:
            storage.get_object("media/original/xyz")
        assert "SUPER-SECRET" not in str(exc_info.value)
        assert "InternalError" in str(exc_info.value)
        # Distinguishable from an R2 failure in logs/evidence, without
        # leaking anything provider-internal beyond the bounded label.
        assert "B2" in str(exc_info.value)

    def test_delete_object_calls_client(self) -> None:
        client = MagicMock()
        storage = B2ObjectStorage(client=client, bucket="backup-bucket-1")
        storage.delete_object("media/original/xyz")
        client.delete_object.assert_called_once_with(
            Bucket="backup-bucket-1", Key="media/original/xyz"
        )

    def test_empty_bucket_rejected(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            B2ObjectStorage(client=MagicMock(), bucket="")
