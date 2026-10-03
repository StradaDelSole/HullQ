# Production Backup / Restore Runbook — SLICE-0079

**Status:** operational runbook, required output of SLICE-0079.
**Controlling gate:** `docs/governance/PRODUCTION_READINESS_GATE.md` §2.
**Hard rule:** *"A backup is not proven until a restore is proven"* (`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §21).

## 1. Mechanism

```text
pg_dump --format=custom [--schema=S] <HULLQ_DATABASE_URL>
  -> Fernet symmetric encryption (hullq.ops.backup_restore, cryptography)
  -> ObjectStorage.put_object  (Cloudflare R2, backup-dedicated bucket)
```

Restore reverses it exactly: `get_object` -> Fernet decrypt -> `pg_restore --clean --if-exists`.
Implementation: `src/hullq/ops/backup_restore.py`. CLIs: `scripts/ops/backup_database.py`,
`scripts/ops/restore_database.py`.

### Credential separation (architecture §21/§22)

Backup object storage uses its **own** R2 bucket and credentials
(`HULLQ_BACKUP_R2_*`), never the media bucket (`HULLQ_R2_*`) or the
application database role. Create a dedicated R2 API token scoped to only
the backup bucket.

## 2. RTO / RPO

```text
RPO (Recovery Point Objective): 24 hours
  — a scheduled daily backup (cron, §4) plus DigitalOcean Managed
    PostgreSQL's own continuous WAL-based PITR (provider backup, retained
    independently of the mechanism in this runbook) bounds real data loss
    to well under 24h in practice; this runbook's encrypted off-provider
    copy is the independence guarantee, not the primary RPO driver.

RTO (Recovery Time Objective): 2 hours for a solo operator
  — download + decrypt + pg_restore of the full database is the dominant
    cost; §5 measures the real wall-clock time for this slice's disposable
    proof as a lower bound (seconds, for a near-empty schema) and this
    number is a deliberately conservative upper bound pending a real
    production-sized restore-drill measurement once real data exists.
```

Retention direction (architecture §21): **7 daily + 4 weekly** encrypted
backups retained in the R2 backup bucket. Configure this as an R2
lifecycle rule on the backup bucket (object expiration by key prefix/age)
rather than application-level pruning logic — this is bucket
configuration, not HullQ code.

## 3. PostgreSQL HA state (explicit, per the gate's hard rule)

```text
POSTGRESQL_HA_STATUS = NOT_ACTIVE
NO REAL EXTERNAL BUYER EXPOSURE UNTIL HA REQUIREMENT IS SATISFIED
```

Automatic failover with at least one standby is **not** active as of this
slice. Per `docs/governance/PRODUCTION_READINESS_GATE.md` §2 and
`docs/governance/POST_0051_TRIGGER_GATES.md` Gate 2, this is only
acceptable for a strictly internal production-data phase with no real
external buyer exposure; it is a hard blocker before any real external
inventory is exposed to real external buyers, independent of this gate's
own PASS/FAIL status.

## 4. Generating the encryption key and scheduling backups

```bash
# One-time, store the output only in the VPS .env (never in the repository):
uv run python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Cron, on the VPS (the ops checkout, not inside Docker — see the deploy
runbook §1):

```cron
# Daily at 02:00 UTC
0 2 * * * cd /opt/hullq-ops && uv run python scripts/ops/backup_database.py >> /var/log/hullq-backup.log 2>&1
```

## 5. Restore procedure (disaster recovery)

```bash
cd /opt/hullq-ops
uv run python scripts/ops/restore_database.py --object-key backups/full-database/<timestamp>.dump.enc
```

Defaults to restoring into `HULLQ_DATABASE_URL`. **Always** restore into a
disposable/staging target first to verify the backup before pointing it at
the real production database during an actual incident, unless the
production database is already lost (in which case there is nothing left
to protect by staging first).

## 6. Executable restore-drill proof performed for this slice (2026-10-03)

`tests/persistence/test_backup_restore_disposable_proof.py`, run against the
real local PostgreSQL 18 test database with the real `pg_dump`/`pg_restore`
18.6 client binaries (no mocks):

```text
1. seed a disposable schema with 3 known rows
2. create_encrypted_backup(schema=..., encryption_key=<real Fernet key>,
   object_storage=InMemoryObjectStorage(), object_key=...)
   -> backup_result.size_bytes > 0  [PASS]
3. DROP SCHEMA ... CASCADE; CREATE SCHEMA ...  (genuinely destroy the data)
4. SELECT to_regclass(...) -> NULL                          [confirmed: table is actually gone]
5. restore_encrypted_backup(...)  -> restore_result returned without error
6. SELECT label FROM backup_proof_items ORDER BY id
   -> ['alpha', 'bravo', 'charlie']                          [PASS: exact original data recovered]
7. (separate test) restore with the WRONG Fernet key -> raises BackupError, never silently
   returns corrupt/garbage data                              [PASS]
```

Both tests pass: `2 passed` (see the slice completion report for the exact
command). This is a real backup-then-destroy-then-restore cycle against
disposable PostgreSQL resources, satisfying "a tested restore proving
recoverability rather than backup existence alone." It does **not** by
itself prove the real Cloudflare R2 backup bucket (that requires real R2
credentials this slice does not have); `InMemoryObjectStorage` stands in
for the `ObjectStorage` boundary exactly as `hullq.storage.object_storage`'s
own contract already establishes for the equivalent media path (§17: "live
Cloudflare credentials are not required in ordinary CI"). **Residual**: the
first real restore drill against the actual R2 backup bucket is an
operational task for whoever configures `HULLQ_BACKUP_R2_*` for the first
time — run §5 against a disposable staging database immediately after.
