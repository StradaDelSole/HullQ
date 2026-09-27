"""Object-storage boundary — SLICE-0068.

Implements `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §5/§11: Cloudflare
R2 Standard is the initial primary marketplace-media object store, accessed
only through this S3-compatible boundary using server-owned opaque object
keys -- never a caller-supplied filename or a provider URL as identity.

`ObjectStorage` is the one interface every caller (application orchestration,
tests) depends on. `R2ObjectStorage` is the real boto3-backed S3-compatible
adapter; `InMemoryObjectStorage` is the deterministic local fake required by
contract §17 ("retained local/fake S3-compatible proof is deterministic; live
Cloudflare credentials are not required in ordinary CI"). Application hosts
remain stateless: neither adapter ever writes media bytes to local disk.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Protocol

__all__ = [
    "HULLQ_R2_ACCESS_KEY_ID_ENV",
    "HULLQ_R2_ACCOUNT_ID_ENV",
    "HULLQ_R2_BUCKET_ENV",
    "HULLQ_R2_SECRET_ACCESS_KEY_ENV",
    "InMemoryObjectStorage",
    "ObjectNotFoundError",
    "ObjectStorage",
    "ObjectStorageConfigError",
    "R2ObjectStorage",
    "R2ObjectStorageConfig",
    "get_r2_object_storage_config",
]


class ObjectNotFoundError(KeyError):
    """*key* does not exist in the object store.

    Never carries the store's credentials or any provider-internal detail --
    only the opaque *key* that was requested.
    """


class ObjectStorage(Protocol):
    """The one storage boundary every caller depends on (contract §5).

    Every implementation MUST NOT persist media bytes to local host disk
    (contract §5: "Application hosts remain stateless and media bytes are
    not persisted on local host disk") and MUST treat *key* as opaque --
    never derived from or exposing a caller-supplied filename.
    """

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None: ...

    def get_object(self, key: str) -> bytes: ...

    def delete_object(self, key: str) -> None: ...


class InMemoryObjectStorage:
    """Deterministic in-memory fake S3-compatible store (contract §17).

    Used by tests and any local/dev deployment lacking real R2 credentials.
    Never touches a filesystem or network; not shared across processes.
    """

    def __init__(self) -> None:
        self._objects: dict[str, tuple[bytes, str]] = {}
        self._lock = threading.Lock()

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        if not key:
            raise ValueError("key must be non-empty")
        with self._lock:
            self._objects[key] = (data, content_type)

    def get_object(self, key: str) -> bytes:
        with self._lock:
            entry = self._objects.get(key)
        if entry is None:
            raise ObjectNotFoundError(key)
        return entry[0]

    def delete_object(self, key: str) -> None:
        with self._lock:
            self._objects.pop(key, None)

    def contains(self, key: str) -> bool:
        """Test-only convenience: whether *key* currently exists."""
        with self._lock:
            return key in self._objects


class ObjectStorageConfigError(RuntimeError):
    """R2 object-storage configuration is missing or invalid.

    Raised before any storage operation is attempted. There is no insecure/
    hard-coded fallback bucket or credential.
    """


HULLQ_R2_ACCOUNT_ID_ENV = "HULLQ_R2_ACCOUNT_ID"
HULLQ_R2_ACCESS_KEY_ID_ENV = "HULLQ_R2_ACCESS_KEY_ID"
HULLQ_R2_SECRET_ACCESS_KEY_ENV = "HULLQ_R2_SECRET_ACCESS_KEY"
HULLQ_R2_BUCKET_ENV = "HULLQ_R2_BUCKET"


class R2ObjectStorageConfig:
    """Resolved, validated Cloudflare R2 connection configuration.

    Holds the account id, credentials and bucket only -- never logged or
    included in any exception message raised by `R2ObjectStorage` below.
    """

    __slots__ = ("access_key_id", "account_id", "bucket", "secret_access_key")

    def __init__(
        self, *, account_id: str, access_key_id: str, secret_access_key: str, bucket: str
    ) -> None:
        self.account_id = account_id
        self.access_key_id = access_key_id
        self.secret_access_key = secret_access_key
        self.bucket = bucket

    @property
    def endpoint_url(self) -> str:
        return f"https://{self.account_id}.r2.cloudflarestorage.com"

    def __repr__(self) -> str:  # pragma: no cover - defensive redaction only
        # Deliberately never includes access_key_id/secret_access_key: a
        # stray repr()/log call must never leak credentials (contract §17:
        # "no credential leakage").
        return f"R2ObjectStorageConfig(bucket={self.bucket!r}, account_id=<redacted>)"


def get_r2_object_storage_config() -> R2ObjectStorageConfig:
    """Read and validate R2 connection configuration from the environment.

    Fails fast with `ObjectStorageConfigError` when any required variable is
    unset or empty. Never falls back to a default bucket/account/credential.
    """
    values: dict[str, str] = {}
    for env_var in (
        HULLQ_R2_ACCOUNT_ID_ENV,
        HULLQ_R2_ACCESS_KEY_ID_ENV,
        HULLQ_R2_SECRET_ACCESS_KEY_ENV,
        HULLQ_R2_BUCKET_ENV,
    ):
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            raise ObjectStorageConfigError(f"{env_var} is not set or empty")
        values[env_var] = raw
    return R2ObjectStorageConfig(
        account_id=values[HULLQ_R2_ACCOUNT_ID_ENV],
        access_key_id=values[HULLQ_R2_ACCESS_KEY_ID_ENV],
        secret_access_key=values[HULLQ_R2_SECRET_ACCESS_KEY_ENV],
        bucket=values[HULLQ_R2_BUCKET_ENV],
    )


class R2ObjectStorage:
    """Real Cloudflare R2 adapter behind the S3-compatible boundary.

    Uses `boto3`'s S3 client pointed at R2's S3-compatible endpoint
    (contract §5). *client* may be injected (a real `boto3` S3 client, or a
    test double) -- production code should normally use
    `R2ObjectStorage.from_config` instead of calling this constructor
    directly, so the real client is always built from validated
    `R2ObjectStorageConfig` rather than ad hoc arguments.
    """

    def __init__(self, *, client: Any, bucket: str) -> None:
        if not bucket:
            raise ValueError("bucket must be non-empty")
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_config(cls, config: R2ObjectStorageConfig) -> R2ObjectStorage:
        import boto3  # deferred: no module-level network/SDK dependency
        from botocore.config import Config as BotoConfig

        client = boto3.client(
            "s3",
            endpoint_url=config.endpoint_url,
            aws_access_key_id=config.access_key_id,
            aws_secret_access_key=config.secret_access_key,
            # R2 has no regions; "auto" is Cloudflare's documented value.
            region_name="auto",
            config=BotoConfig(signature_version="s3v4"),
        )
        return cls(client=client, bucket=config.bucket)

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        if not key:
            raise ValueError("key must be non-empty")
        self._client.put_object(Bucket=self._bucket, Key=key, Body=data, ContentType=content_type)

    def get_object(self, key: str) -> bytes:
        from botocore.exceptions import ClientError  # deferred: no module-level SDK dependency

        try:
            response = self._client.get_object(Bucket=self._bucket, Key=key)
        except ClientError as exc:
            error_code = exc.response.get("Error", {}).get("Code", "")
            if error_code in ("NoSuchKey", "404"):
                raise ObjectNotFoundError(key) from None
            # Never propagate botocore's raw exception (it may embed request
            # parameters); surface only the opaque key and error code.
            raise ObjectStorageConfigError(f"R2 get_object failed ({error_code}) for key") from None
        body = response["Body"].read()
        assert isinstance(body, bytes)
        return body

    def delete_object(self, key: str) -> None:
        self._client.delete_object(Bucket=self._bucket, Key=key)
