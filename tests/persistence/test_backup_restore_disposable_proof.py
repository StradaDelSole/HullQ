"""SLICE-0079 executable backup/restore disaster-recovery proof.

`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §21: "A backup is not proven
until a restore is proven." This test runs the real `pg_dump`/`pg_restore`
client tools (not a mock) against a disposable, throwaway PostgreSQL schema
-- never production data -- and genuinely destroys the schema's contents
between backup and restore (`DROP SCHEMA ... CASCADE` then an empty
`CREATE SCHEMA`) to prove actual recoverability rather than merely that a
backup file was produced.

Uses `InMemoryObjectStorage` as the off-database object-storage target
(contract pattern already established by `hullq.storage.object_storage`
for the equivalent media boundary): the mechanism under test is
dump -> encrypt -> store -> retrieve -> decrypt -> restore, independent of
which concrete object-storage backend eventually receives the encrypted
bytes in production (R2, per `get_backup_r2_object_storage_config`).
"""

from __future__ import annotations

import uuid
from collections.abc import Generator

import psycopg
import pytest
from cryptography.fernet import Fernet

from hullq.ops.backup_restore import (
    BackupError,
    create_encrypted_backup,
    get_backup_encryption_key,
    restore_encrypted_backup,
)
from hullq.storage.object_storage import InMemoryObjectStorage


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


def _recreate_empty_schema(base_url: str, schema_name: str) -> None:
    """Simulate data loss: destroy every object in *schema_name*, keeping the
    (now empty) schema itself -- `pg_restore` of a `--schema`-scoped dump
    recreates tables/data but not the schema container."""
    conn = psycopg.connect(base_url, autocommit=True)
    try:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA "{schema_name}" CASCADE')
            cur.execute(f'CREATE SCHEMA "{schema_name}"')
    finally:
        conn.close()


@pytest.fixture()
def disposable_schema(db_url: str) -> Generator[str]:
    schema_name = f"hullq_s0079backup_{uuid.uuid4().hex[:16]}"
    _create_schema(db_url, schema_name)
    try:
        yield schema_name
    finally:
        _drop_schema(db_url, schema_name)


def test_encrypted_backup_and_restore_recovers_destroyed_schema_data(
    db_url: str, disposable_schema: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("HULLQ_BACKUP_ENCRYPTION_KEY", Fernet.generate_key().decode("ascii"))
    encryption_key = get_backup_encryption_key()

    seed_conn = psycopg.connect(db_url, options=f"-c search_path={disposable_schema}")
    try:
        with seed_conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE backup_proof_items (id serial PRIMARY KEY, label text NOT NULL)"
            )
            cur.execute(
                "INSERT INTO backup_proof_items (label) VALUES (%s), (%s), (%s)",
                ("alpha", "bravo", "charlie"),
            )
        seed_conn.commit()
    finally:
        seed_conn.close()

    object_storage = InMemoryObjectStorage()
    object_key = f"backups/{disposable_schema}/proof.enc"

    backup_result = create_encrypted_backup(
        db_url,
        schema=disposable_schema,
        encryption_key=encryption_key,
        object_storage=object_storage,
        object_key=object_key,
    )
    assert backup_result.size_bytes > 0
    assert object_storage.contains(object_key)

    # Genuinely destroy the schema's data -- this is the step that makes
    # the subsequent restore a real recoverability proof rather than a
    # no-op "restore over identical data".
    _recreate_empty_schema(db_url, disposable_schema)

    verify_conn = psycopg.connect(db_url, options=f"-c search_path={disposable_schema}")
    try:
        with verify_conn.cursor() as cur:
            cur.execute("SELECT to_regclass(%s)", (f"{disposable_schema}.backup_proof_items",))
            assert cur.fetchone()[0] is None, "table must actually be gone before restore"
    finally:
        verify_conn.close()

    restore_result = restore_encrypted_backup(
        db_url,
        encryption_key=encryption_key,
        object_storage=object_storage,
        object_key=object_key,
    )
    assert restore_result.object_key == object_key

    readback_conn = psycopg.connect(db_url, options=f"-c search_path={disposable_schema}")
    try:
        with readback_conn.cursor() as cur:
            cur.execute("SELECT label FROM backup_proof_items ORDER BY id")
            rows = [row[0] for row in cur.fetchall()]
    finally:
        readback_conn.close()
    assert rows == ["alpha", "bravo", "charlie"]


def test_restore_rejects_backup_decrypted_with_the_wrong_key(
    db_url: str, disposable_schema: str
) -> None:
    correct_key = Fernet.generate_key()
    wrong_key = Fernet.generate_key()

    seed_conn = psycopg.connect(db_url, options=f"-c search_path={disposable_schema}")
    try:
        with seed_conn.cursor() as cur:
            cur.execute("CREATE TABLE backup_proof_wrong_key (id serial PRIMARY KEY)")
        seed_conn.commit()
    finally:
        seed_conn.close()

    object_storage = InMemoryObjectStorage()
    object_key = f"backups/{disposable_schema}/wrong-key-proof.enc"
    create_encrypted_backup(
        db_url,
        schema=disposable_schema,
        encryption_key=correct_key,
        object_storage=object_storage,
        object_key=object_key,
    )

    with pytest.raises(BackupError):
        restore_encrypted_backup(
            db_url,
            encryption_key=wrong_key,
            object_storage=object_storage,
            object_key=object_key,
        )
