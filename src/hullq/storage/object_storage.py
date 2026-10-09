"""Object-storage boundary — SLICE-0068; SLICE-0080 adds Backblaze B2.

Implements `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §5/§11: Cloudflare
R2 Standard is the primary marketplace-media object store, accessed
only through this S3-compatible boundary using server-owned opaque object
keys -- never a caller-supplied filename or a provider URL as identity.

SLICE-0080 (`specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md` §2/§11/
§12) adds Backblaze B2 as the one accepted independent-original-copy
provider, consumed through the identical S3-compatible boundary. `R2Object
Storage` and `B2ObjectStorage` are deliberately two distinct adapter classes
built from two distinct, independently-validated config loaders (`get_r2_
object_storage_config` reads `HULLQ_R2_*`; `get_b2_object_storage_config`
reads `HULLQ_MEDIA_BACKUP_B2_*`) so the ordinary production configuration
path has no code path that could resolve both storage roles from one R2
configuration by accident (contract §12). Both share the same underlying
boto3 S3-compatible request/error-mapping plumbing (`_s3_put_object`/`_s3_
get_object`/`_s3_delete_object` below) because that plumbing is provider-
agnostic -- the contract explicitly permits factoring shared S3-client code
as long as no second media domain model is created and the domain never
depends on boto3/provider URLs (contract §12).

`ObjectStorage` is the one interface every caller (application orchestration,
tests) depends on. `InMemoryObjectStorage` is the deterministic local fake
required by contract §17 ("retained local/fake S3-compatible proof is
deterministic; live Cloudflare credentials are not required in ordinary
CI") -- SLICE-0080 reuses the identical fake for the independent B2 role in
tests; no live Backblaze credentials are required in ordinary CI either
(`specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_CONTRACT.v0.1.md` §11). Application
hosts remain stateless: neither adapter ever writes media bytes to local
disk.
"""

from __future__ import annotations

import os
import threading
from typing import Any, Protocol

__all__ = [
    "HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV",
    "HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV",
    "HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV",
    "HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV",
    "HULLQ_MEDIA_BACKUP_B2_REGION_ENV",
    "HULLQ_R2_ACCESS_KEY_ID_ENV",
    "HULLQ_R2_ACCOUNT_ID_ENV",
    "HULLQ_R2_BUCKET_ENV",
    "HULLQ_R2_SECRET_ACCESS_KEY_ENV",
    "B2ObjectStorage",
    "B2ObjectStorageConfig",
    "InMemoryObjectStorage",
    "ObjectNotFoundError",
    "ObjectStorage",
    "ObjectStorageConfigError",
    "R2ObjectStorage",
    "R2ObjectStorageConfig",
    "get_b2_object_storage_config",
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

    def keys_with_prefix(self, prefix: str) -> tuple[str, ...]:
        """Test-only convenience: every currently-stored key starting with
        *prefix* (e.g. distinguishing original/quarantine keys from
        derivative keys by their key-prefix convention)."""
        with self._lock:
            return tuple(key for key in self._objects if key.startswith(prefix))


class ObjectStorageConfigError(RuntimeError):
    """Object-storage configuration is missing/invalid, or a provider
    request failed in a way that must never leak credentials/raw SDK detail.

    Raised before any storage operation is attempted when configuration is
    missing, or raised in place of a provider's raw exception when a request
    fails. There is no insecure/hard-coded fallback bucket or credential for
    either Cloudflare R2 or Backblaze B2 (SLICE-0080).
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


def _build_s3_client(
    *, endpoint_url: str, region_name: str, access_key_id: str, secret_access_key: str
) -> Any:
    """Shared boto3 S3-compatible client construction (contract §12: "may
    factor shared S3-client plumbing to avoid duplicate provider code").
    Used by both `R2ObjectStorage.from_config` and `B2ObjectStorage.
    from_config` -- the only difference between providers is which
    *endpoint_url*/*region_name*/credentials are resolved, never this
    construction logic itself."""
    import boto3  # deferred: no module-level network/SDK dependency
    from botocore.config import Config as BotoConfig

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key_id,
        aws_secret_access_key=secret_access_key,
        region_name=region_name,
        config=BotoConfig(signature_version="s3v4"),
    )


def _s3_put_object(client: Any, bucket: str, key: str, data: bytes, *, content_type: str) -> None:
    if not key:
        raise ValueError("key must be non-empty")
    client.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)


def _s3_get_object(client: Any, bucket: str, key: str, *, provider_label: str) -> bytes:
    from botocore.exceptions import ClientError  # deferred: no module-level SDK dependency

    try:
        response = client.get_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code", "")
        if error_code in ("NoSuchKey", "404"):
            raise ObjectNotFoundError(key) from None
        # Never propagate botocore's raw exception (it may embed request
        # parameters); surface only the opaque key and error code (contract
        # §13/§7: a dependency error -- auth/network/timeout/unknown -- must
        # never be mistaken for confirmed absence, and must never leak
        # credentials/raw SDK detail).
        raise ObjectStorageConfigError(
            f"{provider_label} get_object failed ({error_code}) for key"
        ) from None
    body = response["Body"].read()
    assert isinstance(body, bytes)
    return body


def _s3_delete_object(client: Any, bucket: str, key: str) -> None:
    client.delete_object(Bucket=bucket, Key=key)


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
        client = _build_s3_client(
            endpoint_url=config.endpoint_url,
            # R2 has no regions; "auto" is Cloudflare's documented value.
            region_name="auto",
            access_key_id=config.access_key_id,
            secret_access_key=config.secret_access_key,
        )
        return cls(client=client, bucket=config.bucket)

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        _s3_put_object(self._client, self._bucket, key, data, content_type=content_type)

    def get_object(self, key: str) -> bytes:
        return _s3_get_object(self._client, self._bucket, key, provider_label="R2")

    def delete_object(self, key: str) -> None:
        _s3_delete_object(self._client, self._bucket, key)


HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV = "HULLQ_MEDIA_BACKUP_B2_ENDPOINT"
HULLQ_MEDIA_BACKUP_B2_REGION_ENV = "HULLQ_MEDIA_BACKUP_B2_REGION"
HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV = "HULLQ_MEDIA_BACKUP_B2_KEY_ID"
HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV = "HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY"
HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV = "HULLQ_MEDIA_BACKUP_B2_BUCKET"


class B2ObjectStorageConfig:
    """Resolved, validated Backblaze B2 independent-original-copy connection
    configuration (SLICE-0080; `specs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_
    CONTRACT.v0.1.md` §11).

    Unlike `R2ObjectStorageConfig`, *endpoint*/*region* are taken verbatim
    from the environment rather than derived from an account id -- contract
    §11: "the exact S3 endpoint/cluster suffix is runtime configuration
    obtained from Backblaze and MUST NOT be hardcoded in domain logic."
    Holds credentials only -- never logged or included in any exception
    message raised by `B2ObjectStorage` below.
    """

    __slots__ = ("application_key", "bucket", "endpoint", "key_id", "region")

    def __init__(
        self, *, endpoint: str, region: str, key_id: str, application_key: str, bucket: str
    ) -> None:
        self.endpoint = endpoint
        self.region = region
        self.key_id = key_id
        self.application_key = application_key
        self.bucket = bucket

    @property
    def endpoint_url(self) -> str:
        """Named identically to `R2ObjectStorageConfig.endpoint_url` so the
        two configs can be compared structurally by callers that must
        refuse to let primary and independent-original roles resolve to the
        same endpoint (contract §12)."""
        return self.endpoint

    def __repr__(self) -> str:  # pragma: no cover - defensive redaction only
        # Deliberately never includes key_id/application_key: a stray
        # repr()/log call must never leak credentials (contract §13).
        return (
            f"B2ObjectStorageConfig(bucket={self.bucket!r}, endpoint={self.endpoint!r}, "
            f"region={self.region!r}, key_id=<redacted>)"
        )


def get_b2_object_storage_config() -> B2ObjectStorageConfig:
    """Read and validate Backblaze B2 independent-original-copy connection
    configuration from the environment.

    Fails fast with `ObjectStorageConfigError` when any required variable is
    unset or empty -- mirrors `get_r2_object_storage_config`'s identical
    fail-fast discipline, using the separate `HULLQ_MEDIA_BACKUP_B2_*` names
    (contract §11: "separate from Cloudflare R2 credentials"). Never falls
    back to a default bucket/endpoint/region/credential.
    """
    values: dict[str, str] = {}
    for env_var in (
        HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV,
        HULLQ_MEDIA_BACKUP_B2_REGION_ENV,
        HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV,
        HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV,
        HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV,
    ):
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            raise ObjectStorageConfigError(f"{env_var} is not set or empty")
        values[env_var] = raw
    return B2ObjectStorageConfig(
        endpoint=values[HULLQ_MEDIA_BACKUP_B2_ENDPOINT_ENV],
        region=values[HULLQ_MEDIA_BACKUP_B2_REGION_ENV],
        key_id=values[HULLQ_MEDIA_BACKUP_B2_KEY_ID_ENV],
        application_key=values[HULLQ_MEDIA_BACKUP_B2_APPLICATION_KEY_ENV],
        bucket=values[HULLQ_MEDIA_BACKUP_B2_BUCKET_ENV],
    )


class B2ObjectStorage:
    """Real Backblaze B2 adapter behind the identical S3-compatible boundary
    (SLICE-0080) -- the one accepted independent-original-copy provider
    (`docs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_PROVIDER_DECISION_2026-10-09.md`).

    A distinct class from `R2ObjectStorage` (contract §12: the application/
    FastAPI wiring must distinguish primary from independent-original
    storage explicitly; "passing the same resolved Cloudflare R2 store for
    both roles is not a valid production configuration") even though both
    share the provider-agnostic S3 request plumbing above. *client* may be
    injected (a real `boto3` S3 client, or a test double); production code
    should normally use `B2ObjectStorage.from_config`.
    """

    def __init__(self, *, client: Any, bucket: str) -> None:
        if not bucket:
            raise ValueError("bucket must be non-empty")
        self._client = client
        self._bucket = bucket

    @classmethod
    def from_config(cls, config: B2ObjectStorageConfig) -> B2ObjectStorage:
        client = _build_s3_client(
            endpoint_url=config.endpoint,
            region_name=config.region,
            access_key_id=config.key_id,
            secret_access_key=config.application_key,
        )
        return cls(client=client, bucket=config.bucket)

    def put_object(self, key: str, data: bytes, *, content_type: str) -> None:
        _s3_put_object(self._client, self._bucket, key, data, content_type=content_type)

    def get_object(self, key: str) -> bytes:
        return _s3_get_object(self._client, self._bucket, key, provider_label="B2")

    def delete_object(self, key: str) -> None:
        _s3_delete_object(self._client, self._bucket, key)
