"""Independent encrypted database backup/restore — SLICE-0079.

Implements `docs/governance/PRODUCTION_READINESS_GATE.md` §2's "independent
encrypted off-database/off-provider backup" and "a tested restore proving
recoverability rather than backup existence alone" requirements, and
`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §21's hard rule: **a backup is
not proven until a restore is proven.**

Mechanism:

```text
pg_dump (custom format, same major version as the PostgreSQL 18
          production target)
  -> Fernet symmetric encryption (cryptography)
  -> ObjectStorage.put_object (caller-chosen backend/bucket/credentials --
     this module never decides a provider)
```

Restore reverses it: `ObjectStorage.get_object` -> Fernet decrypt ->
`pg_restore`. Neither direction ever writes a plaintext dump to a
caller-visible path outside one process-local temporary file that is always
removed afterward, and the encryption key never crosses this process
boundary unencrypted.

Per the architecture's credential-separation rule ("Separate app DB
credentials from backup DB credentials... Media credentials and backup
credentials must be separated"), production backup object storage SHOULD
use its own bucket/credentials, never the media `HULLQ_R2_*` ones -- see
`get_backup_r2_object_storage_config` below.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken

from hullq.storage.object_storage import ObjectStorage, R2ObjectStorage, R2ObjectStorageConfig

__all__ = [
    "HULLQ_BACKUP_ENCRYPTION_KEY_ENV",
    "HULLQ_BACKUP_R2_ACCESS_KEY_ID_ENV",
    "HULLQ_BACKUP_R2_ACCOUNT_ID_ENV",
    "HULLQ_BACKUP_R2_BUCKET_ENV",
    "HULLQ_BACKUP_R2_SECRET_ACCESS_KEY_ENV",
    "BackupError",
    "BackupResult",
    "RestoreResult",
    "create_encrypted_backup",
    "decrypt_bytes",
    "dump_database",
    "encrypt_bytes",
    "get_backup_encryption_key",
    "get_backup_r2_object_storage_config",
    "restore_database",
    "restore_encrypted_backup",
]

HULLQ_BACKUP_ENCRYPTION_KEY_ENV = "HULLQ_BACKUP_ENCRYPTION_KEY"
HULLQ_BACKUP_R2_ACCOUNT_ID_ENV = "HULLQ_BACKUP_R2_ACCOUNT_ID"
HULLQ_BACKUP_R2_ACCESS_KEY_ID_ENV = "HULLQ_BACKUP_R2_ACCESS_KEY_ID"
HULLQ_BACKUP_R2_SECRET_ACCESS_KEY_ENV = "HULLQ_BACKUP_R2_SECRET_ACCESS_KEY"
HULLQ_BACKUP_R2_BUCKET_ENV = "HULLQ_BACKUP_R2_BUCKET"

#: Bounded: a stuck pg_dump/pg_restore must not hang a backup/restore
#: operator run or CI job forever.
_SUBPROCESS_TIMEOUT_SECONDS = 600


class BackupError(RuntimeError):
    """A pg_dump/pg_restore/encryption/decryption step failed.

    Never constructed with the raw `database_url` (which carries
    credentials) in its message -- only the subprocess return code and a
    bounded stderr excerpt.
    """


@dataclass(frozen=True, slots=True)
class BackupResult:
    object_key: str
    size_bytes: int
    created_at: datetime


@dataclass(frozen=True, slots=True)
class RestoreResult:
    object_key: str
    restored_at: datetime


def get_backup_encryption_key() -> bytes:
    """Read and validate the Fernet backup-encryption key from the environment.

    Fails fast with `BackupError` when unset/empty/not a valid Fernet key --
    never silently generates or falls back to an insecure default.
    """
    raw = os.environ.get(HULLQ_BACKUP_ENCRYPTION_KEY_ENV, "").strip()
    if not raw:
        raise BackupError(f"{HULLQ_BACKUP_ENCRYPTION_KEY_ENV} is not set or empty")
    key = raw.encode("ascii")
    try:
        Fernet(key)
    except (ValueError, TypeError) as exc:
        raise BackupError(f"{HULLQ_BACKUP_ENCRYPTION_KEY_ENV} is not a valid Fernet key") from exc
    return key


def get_backup_r2_object_storage_config() -> R2ObjectStorageConfig:
    """Read backup-dedicated R2 configuration from the environment.

    Deliberately a *separate* set of environment variables from
    `hullq.storage.object_storage.get_r2_object_storage_config` (media) --
    the architecture requires backup credentials to never be the same
    credentials used for media or the application database.
    """
    values: dict[str, str] = {}
    for env_var in (
        HULLQ_BACKUP_R2_ACCOUNT_ID_ENV,
        HULLQ_BACKUP_R2_ACCESS_KEY_ID_ENV,
        HULLQ_BACKUP_R2_SECRET_ACCESS_KEY_ENV,
        HULLQ_BACKUP_R2_BUCKET_ENV,
    ):
        raw = os.environ.get(env_var, "").strip()
        if not raw:
            raise BackupError(f"{env_var} is not set or empty")
        values[env_var] = raw
    return R2ObjectStorageConfig(
        account_id=values[HULLQ_BACKUP_R2_ACCOUNT_ID_ENV],
        access_key_id=values[HULLQ_BACKUP_R2_ACCESS_KEY_ID_ENV],
        secret_access_key=values[HULLQ_BACKUP_R2_SECRET_ACCESS_KEY_ENV],
        bucket=values[HULLQ_BACKUP_R2_BUCKET_ENV],
    )


def get_backup_r2_object_storage() -> ObjectStorage:
    """Build the real R2-backed backup object store from the environment."""
    return R2ObjectStorage.from_config(get_backup_r2_object_storage_config())


def encrypt_bytes(data: bytes, *, key: bytes) -> bytes:
    return Fernet(key).encrypt(data)


def decrypt_bytes(token: bytes, *, key: bytes) -> bytes:
    try:
        return Fernet(key).decrypt(token)
    except InvalidToken as exc:
        raise BackupError("backup payload failed decryption (wrong key or corrupt object)") from exc


def dump_database(database_url: str, *, schema: str | None = None) -> bytes:
    """Run `pg_dump` in custom format and return the dump as bytes.

    *schema* restricts the dump to one schema (used by the disposable-
    resource restore proof so it never touches unrelated data sharing the
    same PostgreSQL instance); omitted, the entire database is dumped.
    """
    command = ["pg_dump", "--format=custom", "--no-owner", "--no-privileges"]
    if schema is not None:
        command.append(f"--schema={schema}")
    command.append(database_url)
    completed = subprocess.run(
        command,
        capture_output=True,
        timeout=_SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        stderr_excerpt = completed.stderr.decode("utf-8", errors="replace")[-2000:]
        raise BackupError(f"pg_dump failed (exit {completed.returncode}): {stderr_excerpt}")
    return completed.stdout


def restore_database(database_url: str, dump_bytes: bytes, *, clean: bool = True) -> None:
    """Restore a custom-format `pg_dump` byte stream via `pg_restore`.

    *clean* (default `True`) passes `--clean --if-exists` so restoring into
    a target that already has the dumped objects (e.g. the disposable
    before/after drill in the retained proof) drops and recreates them
    rather than failing on "already exists".
    """
    with tempfile.NamedTemporaryFile(suffix=".dump", delete=False) as handle:
        handle.write(dump_bytes)
        dump_path = Path(handle.name)
    try:
        command = ["pg_restore", "--no-owner", "--no-privileges"]
        if clean:
            command.extend(["--clean", "--if-exists"])
        command.extend(["--dbname", database_url, str(dump_path)])
        completed = subprocess.run(
            command,
            capture_output=True,
            timeout=_SUBPROCESS_TIMEOUT_SECONDS,
            check=False,
        )
        if completed.returncode != 0:
            stderr_excerpt = completed.stderr.decode("utf-8", errors="replace")[-2000:]
            raise BackupError(f"pg_restore failed (exit {completed.returncode}): {stderr_excerpt}")
    finally:
        dump_path.unlink(missing_ok=True)


def create_encrypted_backup(
    database_url: str,
    *,
    schema: str | None = None,
    encryption_key: bytes,
    object_storage: ObjectStorage,
    object_key: str,
) -> BackupResult:
    """Dump, encrypt and upload one backup. Returns its size and object key."""
    dump_bytes = dump_database(database_url, schema=schema)
    encrypted = encrypt_bytes(dump_bytes, key=encryption_key)
    object_storage.put_object(object_key, encrypted, content_type="application/octet-stream")
    return BackupResult(
        object_key=object_key, size_bytes=len(encrypted), created_at=datetime.now(UTC)
    )


def restore_encrypted_backup(
    database_url: str,
    *,
    encryption_key: bytes,
    object_storage: ObjectStorage,
    object_key: str,
    clean: bool = True,
) -> RestoreResult:
    """Download, decrypt and restore one backup identified by *object_key*."""
    encrypted = object_storage.get_object(object_key)
    dump_bytes = decrypt_bytes(encrypted, key=encryption_key)
    restore_database(database_url, dump_bytes, clean=clean)
    return RestoreResult(object_key=object_key, restored_at=datetime.now(UTC))
