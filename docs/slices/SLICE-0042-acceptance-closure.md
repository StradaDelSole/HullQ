# SLICE-0042 — Acceptance closure

**Slice:** SLICE-0042  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #133  
**Accepted implementation HEAD:** `6e01dd954ab463689fb9b5cd2dc1c3bff950e271`  
**Implementation merge commit:** `dd5b2a56ee3e4d82a79b5c72fa2cad12bec3f0e3`  
**Owner acceptance:** explicitly recorded 2026-09-03

## Accepted scope

SLICE-0042 establishes the bounded transition from HullQ's accepted historical SQL migration mechanism to Alembic as the authoritative mechanism for all future post-baseline schema evolution.

Accepted migration ownership boundary:

```text
legacy 001_initial_schema
+ legacy 002_canonical_identity_schema
= immutable historical bootstrap boundary
                    ↓
          verified Alembic baseline
                    ↓
all future schema migrations = Alembic revisions
```

The slice does not create NativeListing persistence or any new marketplace application schema beyond Alembic's own revision metadata.

## Accepted artifacts

- `alembic.ini`
- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/6f1c2a9d0001_legacy_002_baseline.py`
- `src/hullq/persistence/alembic_baseline.py`
- `tests/unit/test_alembic_baseline_offline.py`
- `tests/persistence/test_alembic_baseline_integration.py`
- `scripts/inspect_alembic_migration_baseline.py`
- `docs/slices/SLICE-0042-alembic-migration-baseline.md`
- dependency/lock updates required for Alembic/SQLAlchemy migration tooling

The accepted Alembic baseline revision is a no-op marker revision representing the already-accepted legacy state after migrations 001 and 002. It does not replay or redefine that schema.

## Accepted safe-adoption semantics

The accepted preparation boundary distinguishes these states:

```text
FRESH_BOOTSTRAPPED_AND_STAMPED
LEGACY_VERIFIED_AND_STAMPED
ALREADY_BASELINED
REJECTED_UNSAFE_STATE(reason)
```

Hard rules:

- a fresh bootstrap is allowed only when the target HullQ application schema is genuinely empty;
- any pre-existing table/relation blocks the fresh-bootstrap path unless the database already satisfies the explicitly verified accepted legacy/Alembic state;
- an accepted legacy database must be verified using both recorded migration history and structural evidence before stamping;
- adopting an accepted legacy database is a metadata/control-plane transition and must not mutate accepted application rows;
- already-baselined adoption is idempotent;
- partial, unknown, conflicting or unexpected states fail closed and are never automatically repaired, reset or force-stamped;
- the actual fresh-bootstrap path runs the frozen-legacy guard before any legacy migration can execute;
- post-002 legacy SQL migration continuation is prohibited;
- legacy 001/002 remain unchanged historical bootstrap artifacts.

## Alembic authority boundary

After SLICE-0042:

```text
legacy SQL migration runner
= frozen historical bootstrap for 001/002 only

Alembic
= authoritative future schema-evolution mechanism
```

No `003_*.sql` or later application migration may continue through the old migration runner.

Alembic/SQLAlchemy were introduced only as migration tooling. The slice does not introduce SQLAlchemy ORM domain models, generic repositories, application database sessions or an ORM rewrite of existing psycopg persistence.

## Independent exact-head review

Independent review was performed repeatedly after each implementation HEAD changed.

Initial implementation HEAD:

```text
771e390acfd56ef4680f993b24820c10f8de3ebf
```

Verdict: **AMEND**.

Two fail-closed defects were identified:

1. a non-empty unsafe schema could be misclassified as fresh because the emptiness check covered only a small representative table fingerprint;
2. the post-002 legacy migration guard existed but was not wired into the actual fresh-bootstrap preparation path.

First amended HEAD:

```text
cf07e3ae4cd3e5a04b9e22392656f0b6a878e3d6
```

Verdict: **AMEND**.

The 003+ guard defect was fixed, but the fresh-state check still only excluded relations known from legacy 001/002. An unknown/untracked application table could still be legitimized by a fresh bootstrap and baseline stamp.

Final accepted HEAD:

```text
6e01dd954ab463689fb9b5cd2dc1c3bff950e271
```

Final verdict: **ACCEPT**.

The final amendment changed fresh-state preflight so the fresh path is entered only when `current_schema()` contains no table/relation at all. A PostgreSQL regression test with an untracked table and existing row proves fail-closed rejection before migration/stamping and proves the pre-existing row remains unchanged.

No blocker, high or medium finding remained on the accepted exact HEAD.

## Exact-head validation gates

On accepted HEAD `6e01dd954ab463689fb9b5cd2dc1c3bff950e271`:

- owner inspection: `MIGRATION BASELINE RESULT: PASS`;
- full local suite: `3720 passed / 2 skipped`;
- project coverage: `93.08%`;
- new Alembic baseline module coverage: `95.29%`;
- ruff format/check: PASS;
- mypy: PASS;
- repository validation: PASS;
- CI run `33698542518`: SUCCESS;
  - quality / Ubuntu: SUCCESS;
  - quality / Windows: SUCCESS;
  - dependency audit: SUCCESS;
  - PostgreSQL 18 DB integration: SUCCESS;
- Manufacturer artifact reproducibility run `33698542477`: SUCCESS;
  - Ubuntu reproduction: SUCCESS;
  - Windows reproduction: SUCCESS.

The primary slice file intentionally retains the remote-CI acceptance checkbox as not locally verified because the workflow forbids creating an extra implementation commit solely to record already-observed remote CI. This closure is the exact-head acceptance record.

## Merge verification

PR #133 was merged with expected-head protection against accepted implementation HEAD `6e01dd954ab463689fb9b5cd2dc1c3bff950e271`.

Canonical implementation merge commit:

```text
dd5b2a56ee3e4d82a79b5c72fa2cad12bec3f0e3
```

## Retained scope boundaries

SLICE-0042 does **not** implement or authorize:

- NativeListing table/schema/repository;
- Account/Organization/Membership persistence;
- PhysicalBoat or MarketEpisode persistence;
- marketplace business DDL beyond Alembic's own version metadata;
- SQLAlchemy ORM domain models or generic repository/UoW architecture;
- FastAPI endpoints;
- Astro/React frontend;
- Auth0/MFA/session work;
- listing lifecycle/freshness;
- listing snapshots/events/price history;
- media ingestion;
- feeds/import adapters;
- dedup/identity resolution;
- Saved Search/monitoring/alerts;
- leads/contact requests;
- BrokerageRequest/referral flow;
- production managed-DB provisioning, backups or HA;
- SLICE-0043 or later work.

## Operational result

SLICE-0042 is owner-accepted and operationally complete under the HullQ slice workflow.

This closure does not create, authorize or start SLICE-0043. The next marketplace slice requires separate readiness under the controlling Architecture Rebaseline, ONE-CAPABILITY and VISIBLE-RESULT rules.
