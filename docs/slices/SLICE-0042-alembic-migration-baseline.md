# SLICE-0042 — Alembic Migration Baseline

**ID:** SLICE-0042  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Native Marketplace Foundation — post-rebaseline database migration boundary  
**Depends on:** SLICE-0041 owner-accepted / DONE; 2026-09-02 Architecture Rebaseline accepted/merged  
**Blocks:** first post-rebaseline marketplace schema migration, including NativeListing persistence

## Objective

Deliver exactly one inspectable infrastructure capability required by the accepted architecture:

> **A HullQ PostgreSQL 18 database at the currently accepted legacy schema (`001_initial_schema` + `002_canonical_identity_schema`) can be deterministically and safely placed under Alembic revision control, without replaying/destructively rewriting that accepted schema or altering existing application data; all future schema migrations must then start from the Alembic baseline rather than extend the legacy SQL migration sequence.**

This slice establishes the migration ownership boundary only. It does not create a NativeListing table or any other marketplace table.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: establish and verify the post-rebaseline Alembic migration baseline for the existing PostgreSQL schema.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one PostgreSQL-backed command against local PostgreSQL 18 and visibly prove fresh-bootstrap adoption, existing-database adoption, idempotent re-run and fail-closed rejection of an unsafe/unknown baseline state.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted post-SLICE-0039 sequencing places NativeListing persistence next, but the higher-precedence Architecture Rebaseline explicitly requires Alembic for database migrations. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md` permits bounded reordering when a real dependency requires it. This slice closes that prerequisite without pulling NativeListing persistence or other marketplace behavior forward.

## Why this slice exists

HullQ currently has an accepted historical lightweight SQL migration runner from SLICE-0013:

```text
src/hullq/persistence/migrations.py
src/hullq/persistence/sql/001_initial_schema.sql
src/hullq/persistence/sql/002_canonical_identity_schema.sql
```

That runner predates the 2026-09-02 Architecture Rebaseline.

The controlling rebaseline now requires:

```text
Alembic
+ versioned/reviewable migrations
+ explicit migration visibility
+ compatibility-conscious rollout
```

The next planned marketplace capability requires the first new application schema after that decision. Extending the legacy directory with `003_*.sql` would therefore violate the newer controlling architecture.

Rewriting already-accepted historical migrations is also unnecessary and risky. The narrow transition is:

```text
legacy 001 + 002 = immutable historical bootstrap boundary
                    ↓
          verified Alembic baseline
                    ↓
all future schema migrations = Alembic revisions
```

SLICE-0042 establishes that boundary and nothing beyond it.

## Controlling artifacts

Apply post-SLICE-0039 precedence:

1. `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`, especially PostgreSQL and Database Migrations sections;
2. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
3. `docs/PRODUCT_EXECUTION_PLAN.md` where non-conflicting;
4. `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md` where non-conflicting;
5. accepted existing persistence implementation from SLICE-0013 and later persistence slices.

Operational workflow remains controlled by:

- `CLAUDE.md`;
- `docs/engineering/AI_SLICE_WORKFLOW.md`;
- `docs/slices/SLICE_TEMPLATE.md`.

Do not reinterpret or rewrite the accepted research/canonical persistence semantics in the existing SQL migrations.

## Locked semantic boundary

### 1. Historical legacy migrations remain immutable history

The existing files:

```text
001_initial_schema.sql
002_canonical_identity_schema.sql
```

remain the accepted historical bootstrap definition.

SLICE-0042 must not:

- renumber them;
- rewrite their schema semantics;
- squash them into a new historical meaning;
- add a new `003_*.sql` migration to the legacy runner;
- silently delete the legacy migration tracking table.

The existing lightweight runner may remain only as the bounded historical bootstrap mechanism needed to construct the pre-Alembic schema on a genuinely empty development/test database.

After the Alembic baseline is established, no new application schema change may be added to the legacy sequence.

### 2. Alembic becomes authoritative for future schema evolution

Introduce the smallest conventional Alembic environment necessary for HullQ.

The accepted baseline revision represents:

```text
legacy migration 001 applied
AND
legacy migration 002 applied
```

The baseline revision itself must not invent a third schema change.

It is a transition marker from accepted legacy schema history to future Alembic history.

Future migrations, beginning with the later NativeListing persistence slice, must depend on this Alembic baseline revision.

### 3. No ORM architecture expansion

Alembic/SQLAlchemy may be introduced only as migration tooling required by Alembic.

This slice does **not** authorize:

- SQLAlchemy ORM domain models;
- replacing psycopg application persistence with ORM repositories;
- ORM-driven domain semantics;
- generic repository frameworks;
- FastAPI/database session architecture.

Existing domain semantics remain independent of migration tooling.

### 4. Database URLs and credentials

No database credential may be committed.

Alembic and the owner/test tooling must obtain database URLs from existing HullQ environment-driven configuration or a narrowly equivalent environment-variable boundary.

For local/integration validation, use `HULLQ_TEST_DATABASE_URL` where appropriate.

`alembic.ini` or equivalent configuration must not contain a real username/password/connection secret.

### 5. Safe adoption states

The transition must distinguish safe and unsafe states rather than blindly stamp any database.

At minimum support these deterministic states:

#### A. genuinely empty database

A database with no HullQ application schema may be bootstrapped through the accepted legacy `001` + `002` migrations, verified, and then stamped at the Alembic baseline.

#### B. accepted legacy database

A database already carrying the accepted legacy migration state may be verified and stamped at the Alembic baseline **without replaying the legacy schema** and without changing application data.

#### C. already-baselined database

A database already stamped at the expected Alembic baseline must be accepted idempotently without schema/data mutation.

#### D. unsafe / unknown state

A database must fail closed rather than be stamped when its state is materially inconsistent with the accepted transition boundary, including examples such as:

- only one of the required legacy migrations is recorded/applied;
- a required accepted legacy relation is absent;
- an unexpected later legacy migration ID exists;
- Alembic reports a revision different from the expected baseline/head for this slice;
- migration metadata and structural state materially disagree.

Do not repair, drop, reset or force-stamp an unsafe database automatically.

### 6. Existing application data must survive adoption

On an already-valid legacy database, adopting the Alembic baseline is a metadata/control-plane transition only.

Hard invariant:

> **No accepted application row may be inserted, updated or deleted merely because the database is being adopted into Alembic revision control.**

Tests must prove preserved representative existing data across the transition.

### 7. Baseline verification must be explicit

Do not trust `hullq_schema_migrations` alone.

Before stamping an existing legacy database, verify both:

```text
expected legacy migration history
AND
minimum structural evidence of the accepted 001/002 schema
```

Exact implementation is left to the slice, but the verification must be deterministic and testable.

It must not attempt a full semantic reconstruction of every historical schema detail.

### 8. Migration ownership after 0042

After successful baseline adoption:

```text
legacy SQL migration runner
= frozen historical bootstrap only

Alembic
= authoritative future schema-evolution mechanism
```

A test or repository guard must make accidental addition/use of a post-002 legacy SQL migration fail visibly.

## Required behavior A — conventional Alembic environment

Add a minimal conventional Alembic environment compatible with the repository and PostgreSQL 18.

Normally this includes:

```text
alembic.ini
alembic/
  env.py
  script.py.mako
  versions/
    <revision>_legacy_002_baseline.py
```

Exact revision ID/name may differ, but the baseline meaning must be unambiguous.

No autogeneration metadata model is required by this slice.

If `target_metadata = None` is appropriate because HullQ is not adopting SQLAlchemy ORM models, that is acceptable.

## Required behavior B — safe baseline preparation

Provide one narrow programmatic/script boundary that can prepare the current database for Alembic safely.

Conceptually:

```text
prepare_alembic_baseline(database_url)
→ FRESH_BOOTSTRAPPED_AND_STAMPED
  | LEGACY_VERIFIED_AND_STAMPED
  | ALREADY_BASELINED
  | REJECTED_UNSAFE_STATE(reason)
```

Equivalent naming is acceptable.

The function/script must:

1. inspect current database state;
2. bootstrap 001/002 only when the database is genuinely empty;
3. verify accepted legacy state before stamping an existing database;
4. stamp only the accepted baseline revision;
5. be idempotent;
6. fail closed on ambiguity/inconsistency;
7. never auto-drop/reset an unsafe schema.

A rejected result must expose an actionable deterministic reason rather than only a generic false boolean.

## Required behavior C — Alembic command compatibility

After successful preparation, standard Alembic inspection must report the expected revision.

At minimum prove an equivalent of:

```text
alembic current
alembic heads
alembic upgrade head
```

For SLICE-0042, `upgrade head` after baseline adoption must be a no-op with respect to application schema because no post-baseline schema migration exists yet.

## Required behavior D — frozen legacy boundary

Mechanically prove that new migration work cannot quietly continue via:

```text
src/hullq/persistence/sql/003_*.sql
```

A focused validation/test may enforce that the accepted legacy migration set ends at `002_canonical_identity_schema`.

Do not delete the old runner while fresh bootstrap still depends on it.

## Minimal owner-test surface

Provide one PostgreSQL-backed owner command, normally:

```text
uv run python scripts/inspect_alembic_migration_baseline.py
```

It may require `HULLQ_TEST_DATABASE_URL` and must clearly say so when absent.

The command must use a disposable/test database context and visibly prove representative transitions equivalent to:

```text
ALEMBIC MIGRATION BASELINE

fresh database
→ legacy 001/002 bootstrap verified
→ Alembic baseline stamped

existing accepted legacy database
→ legacy state verified
→ existing data preserved
→ Alembic baseline stamped

already-baselined database
→ idempotent

unsafe/partial legacy state
→ REJECTED (fail closed)

legacy post-002 migration guard
→ PASS

alembic current == expected baseline
alembic upgrade head == no application-schema change

MIGRATION BASELINE RESULT: PASS
```

Exact output labels may differ, but the evidence must remain inspectable.

The script must execute real PostgreSQL/Alembic behavior; it may not print hard-coded PASS labels.

## Required tests

Focused unit/integration tests must cover at least:

- Alembic is installed/configured without committed DB secrets;
- baseline revision has exactly one clear meaning: accepted legacy state after 001 + 002;
- baseline revision introduces no marketplace/application DDL;
- fresh empty PostgreSQL 18 database can reach the Alembic baseline through the bounded historical bootstrap path;
- accepted pre-Alembic 001/002 database can be adopted without replaying destructive DDL;
- representative existing rows are unchanged after adoption;
- already-baselined database is idempotent;
- partial legacy state is rejected;
- missing required accepted legacy structure is rejected;
- unexpected post-002 legacy migration history is rejected;
- conflicting/unexpected Alembic revision state is rejected;
- no unsafe state is silently stamped;
- `alembic current` reports the expected baseline after adoption;
- `alembic upgrade head` is schema/data-neutral in this slice;
- post-002 legacy SQL migration files are prohibited by a deterministic guard;
- existing persistence/import/readback tests remain green;
- PostgreSQL 18 CI integration runs the new baseline/adoption tests.

## In scope

- Alembic dependency/configuration;
- minimal Alembic environment;
- one baseline revision representing accepted legacy 001/002 state;
- safe transition/adoption helper or equivalent narrow boundary;
- frozen-legacy migration guard;
- PostgreSQL 18 integration tests for fresh/existing/idempotent/unsafe states;
- deterministic PostgreSQL-backed owner inspection;
- compact normative transition contract if needed to keep implementation/tests aligned;
- minimal CI integration required to exercise the new PostgreSQL tests.

## Explicitly out of scope

- NativeListing table/schema/repository;
- Account/Organization/Membership persistence;
- PhysicalBoat/MarketEpisode persistence;
- any new marketplace DDL beyond Alembic's own version metadata;
- FastAPI endpoints;
- Astro/React frontend;
- Auth0/MFA/session work;
- generic SQLAlchemy ORM introduction;
- generic repository/UoW framework;
- listing lifecycle/freshness;
- listing snapshots/events/price history;
- media;
- feeds/import adapters;
- dedup/identity resolution;
- Saved Search/monitoring/alerts;
- leads/contact requests;
- BrokerageRequest/referral flow;
- production deployment/managed-DB provisioning/backups/HA;
- SLICE-0043 or later work.

## Deliverables

Expected bounded deliverables:

1. `alembic.ini` with no committed secret;
2. minimal `alembic/` environment and baseline revision;
3. Alembic dependency/lockfile update;
4. small baseline-adoption helper/module or equivalent;
5. focused unit + PostgreSQL integration tests;
6. `scripts/inspect_alembic_migration_baseline.py`;
7. optional compact `specs/DATABASE_MIGRATION_BASELINE.v0.1.md` if needed;
8. this primary slice document moved to `REVIEW` on successful handoff.

Do not create NativeListing persistence scaffolding as a placeholder.

## Acceptance criteria

- [x] Product execution checks remain `PASS` with no scope widening.
- [x] Alembic is the authoritative mechanism for every future post-baseline schema migration.
- [x] Existing legacy migrations 001/002 remain unchanged historical bootstrap artifacts.
- [x] No post-002 migration is added to the legacy SQL migration sequence.
- [x] Baseline revision represents accepted legacy state after 001 + 002 and adds no application/marketplace schema.
- [x] Fresh PostgreSQL 18 database can deterministically reach the baseline.
- [x] Existing accepted legacy PostgreSQL 18 database can be safely adopted without data loss/change.
- [x] Already-baselined database adoption is idempotent.
- [x] Partial/unknown/conflicting database state fails closed and is not automatically stamped/reset.
- [x] Verification uses both migration-history and structural evidence before stamping an existing database.
- [x] Standard Alembic current/heads/upgrade-head behavior is proven.
- [x] Repository guard prevents accidental future `003_*.sql` legacy migration continuation.
- [x] No SQLAlchemy ORM/domain rewrite is introduced.
- [x] No NativeListing or other marketplace DDL is introduced.
- [x] Owner command executes real PostgreSQL/Alembic transitions and reports `MIGRATION BASELINE RESULT: PASS` only when all required scenarios pass.
- [x] Repository validation, ruff, mypy and full test suite pass; project coverage remains >=90%.
- [ ] Exact-head CI, including PostgreSQL 18 integration, and Manufacturer artifact reproducibility are green before review acceptance where applicable. (NOT VERIFIED locally — requires remote observation on final HEAD)
- [x] No SLICE-0043 or later work starts automatically.

## Expected touch points

Expected, not mandatory exact paths:

- `pyproject.toml`;
- `uv.lock`;
- `alembic.ini`;
- `alembic/**`;
- `src/hullq/persistence/**` only as required for the transition helper/guard;
- `tests/**` for focused/unit/PostgreSQL integration coverage;
- `scripts/inspect_alembic_migration_baseline.py`;
- this slice document;
- CI workflow only if necessary to ensure PostgreSQL integration coverage actually executes.

Do not modify unrelated domain/search/marketplace modules.

## Validation

At handoff, run and summarize at minimum:

```text
uv run python scripts/inspect_alembic_migration_baseline.py
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
```

The PostgreSQL-backed owner/integration validation requires a disposable test database through `HULLQ_TEST_DATABASE_URL` or the repository's accepted equivalent.

Remote CI must be observed on the exact final HEAD before independent acceptance.

## Stop conditions

Stop and report `BLOCKED` rather than inventing a workaround when:

- the accepted 001/002 legacy schema cannot be safely identified without destructive assumptions;
- Alembic adoption would require silently rewriting accepted historical schema semantics;
- the proposed transition would mutate existing application data merely to establish migration metadata;
- a required database state is ambiguous and the only way forward is force-stamping/resetting;
- implementation requires NativeListing or other marketplace schema to prove the baseline;
- implementation would require a generic ORM/framework expansion beyond the migration prerequisite;
- controlling architecture artifacts materially conflict.

## Status handoff rule

Claude may recommend/set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark this slice `DONE`.

Independent review occurs after the pushed handoff. Any finding requiring code/doc changes returns to Claude on the same slice branch; the changed HEAD must be reviewed again from scratch for exact-head acceptance.

`DONE` requires verified acceptance criteria, required remote/external checks, independent exact-head review, explicit Project Owner acceptance and closure under the normal HullQ workflow.
