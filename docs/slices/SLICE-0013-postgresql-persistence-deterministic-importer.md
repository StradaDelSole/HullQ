# SLICE-0013 — PostgreSQL Persistence and Deterministic ResearchEvidenceBundle Importer

**ID:** SLICE-0013  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 2.13 — first physical persistence boundary  
**Depends on:** SLICE-0012 accepted / DONE  
**Blocks:** benchmark-through-database measurement slice

**Authorization:** READY after explicit project-owner acceptance of SLICE-0012, successful merge of PR #24, and canonical merge commit `db68e53ddc9cfe4aa53caa3ba900dc6a3daa7324`.

## Objective

Introduce HullQ's first real PostgreSQL persistence boundary without expanding into broad ingestion or canonical identity automation.

This slice must provide:

1. a reproducible PostgreSQL schema/migration baseline;
2. durable lossless persistence for accepted SLICE-0012 research/evidence contracts;
3. one deterministic transactional importer for `ResearchEvidenceBundle`;
4. explicit idempotency/conflict behavior;
5. a real PostgreSQL integration-test path in CI.

The importer is a persistence boundary, not a reasoning engine.

```text
validated ResearchEvidenceBundle
        ↓
deterministic content fingerprint
        ↓
transactional PostgreSQL import
        ↓
immutable persisted research/evidence records
        ↓
round-trip/readback verification

NO fuzzy identity resolution
NO automatic canonical subject creation
NO automatic FieldResolution
NO web acquisition
NO broad benchmark execution
```

## Controlling accepted artifacts

Preserve the accepted semantics of:

- `specs/RESEARCH_EVIDENCE_BUNDLE_SCHEMA.v0.1.json`;
- `specs/RESEARCH_OBSERVATION_SCHEMA.v0.1.json`;
- `specs/OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json`;
- `specs/CLAIM_SEMANTICS_SCHEMA.v0.1.json`;
- `specs/FIELD_EVIDENCE_SCHEMA.v0.3.json`;
- `specs/FIELD_EVIDENCE_SCHEMA.v0.2.json` as immutable historical contract;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.2.json`;
- `specs/PROVENANCE_SUBJECT_SCHEMA.v0.1.json`;
- `src/hullq/research/observations.py`;
- `src/hullq/domain/provenance.py`;
- accepted ResearchJob/source-rights semantics;
- SLICE-0012 acceptance closure.

The JSON/domain contracts remain semantic truth. The relational schema is a persistence projection and MUST NOT silently redefine those contracts.

## PostgreSQL baseline

Target PostgreSQL major version: **18**.

The project owner's current local installation is PostgreSQL 18.6, but no developer password, local database name or machine-specific configuration belongs in the repository.

Requirements:

- database connection comes from environment/configuration, never committed secrets;
- no manual production schema creation instructions as a substitute for migrations;
- schema must be created from an empty PostgreSQL database through repository-controlled migrations;
- migrations must be deterministic and version controlled;
- CI must exercise a real PostgreSQL 18 instance;
- no PostgreSQL extension should be required unless this slice proves it necessary. Prefer core PostgreSQL features only.

Preferred implementation direction is a thin persistence layer using PostgreSQL-native semantics, `psycopg` and a standard migration mechanism. If SQLAlchemy/Alembic is used, keep domain contracts independent from ORM state and prefer explicit/Core-style persistence over active-record domain coupling.

Any new dependency must be locked in `uv.lock` and justified by the bounded persistence need.

## In scope

### 1. Migration framework and initial schema

Add the smallest migration framework needed to create and evolve HullQ's database reproducibly.

The initial schema must persist the accepted research handoff without flattening its semantics.

At minimum support durable records for:

- versioned ResearchEvidenceBundle identity/snapshot;
- ResearchTarget snapshot;
- ResearchObservation;
- ObservationApplicability;
- unresolved/review findings;
- reference crosschecks as a separate non-provenance structure;
- optional successor FieldEvidence v0.3 already present in a bundle;
- bundle↔observation and bundle↔evidence membership where needed.

Do not create broad speculative tables for future product features.

### 2. Immutable/versioned bundle identity

A bundle is versioned. Persistence identity must preserve at least:

```text
bundle_id
bundle_version
```

Required semantics:

- `(bundle_id, bundle_version)` is an immutable imported bundle version;
- the exact same bundle version imported again with semantically identical content is idempotent/no-op;
- the same `(bundle_id, bundle_version)` with different content MUST fail closed as a conflict;
- a later explicit bundle version may coexist with an earlier version;
- importer MUST NOT silently update an already persisted immutable bundle version.

Use deterministic canonical serialization/fingerprinting so idempotency does not depend on JSON key ordering or Python object identity.

### 3. Stable ResearchObservation persistence

ResearchObservation IDs are caller-supplied stable identities.

Required semantics:

- the same `observation_id` with the same persisted semantic snapshot may be reused/referenced without mutation;
- the same `observation_id` with materially different content MUST fail closed;
- correction history uses accepted supersession/new-observation semantics rather than overwrite;
- one observation may be associated with more than one bundle if the contracts allow it, without duplicating contradictory mutable copies;
- raw observation and normalized candidate remain distinct;
- claim semantics, applicability, source locator, producer, research context, confidence, timestamps, hints and notes survive round trip.

A global observation table plus explicit bundle membership is acceptable and preferred over silently cloning mutable observations per bundle.

### 4. Applicability persistence

All accepted applicability dimensions must survive database round trip without widening scope:

- first/last year;
- hull/build number bounds;
- market/region;
- named-variant hint;
- design-option hints;
- operating-state hint;
- individual hull/listing/build reference;
- explicit unknown/unbounded state.

Null remains unknown/not asserted, never `global` or `all production`.

Database constraints should enforce simple structural invariants where practical, but domain validation remains authoritative. Do not invent SQL-only business semantics that differ from runtime/schema validation.

### 5. FieldEvidence v0.3 persistence

Persist optional already-promoted `FieldEvidence v0.3` losslessly when present in a bundle.

Requirements:

- stable `evidence_id` identity;
- typed subject snapshot (`subject_kind`, `subject_id` or equivalent accepted representation);
- field pointer;
- source/raw/normalized/provenance properties;
- claim semantics;
- applicability;
- supersession/current accepted evidence semantics where represented by the contract.

This slice MUST NOT resolve ResearchObservation into FieldEvidence automatically.

If canonical subject tables do not yet exist, do not invent them merely to satisfy a foreign key. Persist the accepted typed subject identity safely and defer broader canonical-entity persistence to a later bounded slice.

### 6. Reference crosschecks remain outside evidence

Reference crosschecks require their own persistence structure.

Rules:

- no `evidence_id` is created for a crosscheck;
- no foreign-key path may make a crosscheck satisfy FieldResolution supporting/contradicting evidence references;
- SailboatData field values are not stored;
- retain only accepted reference identity/source label, topic/field, outcome/anomaly class and bounded qualitative notes;
- importer cannot promote or transform a crosscheck into ResearchObservation or FieldEvidence.

### 7. Deterministic importer

Add one explicit importer entry point similar to:

```text
import_research_evidence_bundle(connection/session, bundle)
    -> ImportResult
```

Exact API naming may follow repository conventions.

Importer responsibilities:

1. require an already valid/validated bundle or validate deterministically before writes;
2. compute deterministic semantic fingerprints;
3. begin one database transaction;
4. check immutable bundle/observation/evidence identity collisions;
5. insert/link all bundle children;
6. commit only if the complete import succeeds;
7. rollback fully on any conflict or persistence error;
8. return explicit deterministic result status.

Suggested bounded result states:

```text
IMPORTED
ALREADY_IMPORTED
CONFLICT
```

Do not hide conflicts behind last-write-wins upserts.

### 8. Transaction and concurrency safety

Use PostgreSQL constraints plus transactional code so duplicate/concurrent imports cannot produce partial or contradictory state.

At minimum:

- unique/primary constraints encode immutable identities;
- child failure rolls back the whole new bundle import;
- repeated import cannot duplicate membership rows;
- conflict detection is deterministic;
- no autocommit sequence may expose half an imported bundle.

A full distributed locking system is out of scope.

### 9. Round-trip/read boundary

Provide the smallest read/reconstruction support needed to prove persistence fidelity.

At minimum one persisted bundle must be reconstructable or semantically comparable to the accepted input snapshot so tests can prove that:

- raw values survive;
- normalized candidates survive;
- applicability survives;
- claim semantics survive;
- unresolved findings survive;
- reference crosschecks remain separate;
- optional promoted FieldEvidence survives.

Do not build a general query/search repository API in this slice.

### 10. Database configuration

Use explicit environment configuration such as one database URL setting. Exact naming may follow project conventions; prefer a HullQ-specific name such as:

```text
HULLQ_DATABASE_URL
```

Integration tests may use a distinct variable such as `HULLQ_TEST_DATABASE_URL` if useful.

Rules:

- no secrets in source control;
- no machine-specific paths;
- importing modules must not connect to PostgreSQL as a side effect;
- connection creation is explicit;
- tests must not target a developer's arbitrary production/default database.

## Persistence-shape guidance

Use relational columns for stable identity/filtering/integrity keys and PostgreSQL `jsonb` where the accepted contract is nested and premature decomposition would create drift.

Good candidates for relational columns include:

- bundle ID/version;
- observation/evidence IDs;
- subject kind/ID;
- source ID;
- field pointer;
- evidence/claim type;
- observed timestamp;
- key foreign relationships;
- deterministic content hash.

Nested snapshots such as source locators, raw observation shapes, normalized candidates, producer metadata and applicability may use `jsonb` where that preserves accepted semantics more safely than speculative normalization.

Do not optimize schema for future public search in this slice. Search-specific indexes belong later after query semantics are measured.

## Explicitly out of scope

Do not implement:

- fuzzy or automatic BoatModel/BoatDesign identity resolution;
- automatic creation of canonical Brand/Organization/BoatDesign records from ResearchTarget text;
- automatic ResearchObservation → FieldEvidence promotion;
- automatic FieldResolution/canonical-value selection;
- broad canonical BoatModel/BoatDesign relational persistence unless strictly required by an accepted field already being persisted;
- broad ingestion or crawling;
- new web source adapters;
- SailboatData extraction or SailboatData field-value persistence;
- execution/import of all 50 benchmark designs as a production benchmark run;
- benchmark automation/review/cost measurement itself;
- query engine or OQ-009 resolution;
- FastAPI/public HTTP API;
- Astro frontend;
- auth/accounts;
- listing/marketplace ingestion;
- saved search/monitoring;
- price history;
- SEO/public page implementation;
- Redis, message broker, Elasticsearch/OpenSearch, Kubernetes or distributed job infrastructure.

If implementation would require one of these, stop and report rather than widening scope.

## Required tests

Cover at least:

1. migrations create the schema from an empty PostgreSQL 18 database;
2. applying migrations to current head twice is safe/no-op through normal migration tooling;
3. a valid unresolved/pre-canonical bundle imports without canonical BoatDesign identity;
4. import is atomic;
5. exact repeated import returns idempotent `ALREADY_IMPORTED` or equivalent and creates no duplicates;
6. same `(bundle_id, bundle_version)` with changed content fails closed;
7. same `observation_id` with changed semantic content fails closed;
8. a later bundle version can coexist with the earlier immutable version;
9. observation membership is not duplicated;
10. raw observation round-trips losslessly at semantic JSON level;
11. normalized candidate remains separate from raw;
12. all applicability dimensions round-trip without widening null scope;
13. claim semantics round-trip exactly;
14. observation timestamp remains distinct from applicability;
15. individual-hull scope remains individual-hull scope;
16. class-rule claim remains class-rule claim;
17. operating-state claim remains representable without a DesignOption ID;
18. unresolved findings round-trip;
19. reference crosschecks persist without evidence IDs and cannot become FieldEvidence;
20. no SailboatData field values are introduced in persistence fixtures/tests;
21. optional FieldEvidence v0.3 round-trips with claim/applicability intact;
22. importer does not perform identity resolution or promotion;
23. child conflict/error rolls back the complete new bundle transaction;
24. database configuration has no import-time network/connection side effect;
25. pure/unit tests remain runnable without a local PostgreSQL server;
26. dedicated PostgreSQL integration tests run against real PostgreSQL 18 in remote CI;
27. all existing tests remain green;
28. repository validator, Ruff, formatting, strict mypy, branch coverage >=90% and dependency audit pass.

Do not use SQLite as proof of PostgreSQL behavior for the integration acceptance criteria.

## CI requirements

Keep existing Ubuntu/Windows quality jobs green.

Add the smallest dedicated PostgreSQL integration path needed for this slice, preferably an Ubuntu CI job with a PostgreSQL 18 service container.

The dedicated DB job must at least:

```text
checkout
→ install locked environment
→ start PostgreSQL 18
→ migrate empty test DB to head
→ run persistence/integration tests
```

No external paid service or long-lived cloud database is required.

## Expected touch points

Prefer a bounded set such as:

- `pyproject.toml` / `uv.lock` for required DB/migration dependencies;
- migration configuration + initial migration files;
- `src/hullq/persistence/` for connection/schema/import/read boundaries;
- focused unit tests;
- dedicated PostgreSQL integration tests;
- CI workflow update for PostgreSQL integration;
- compact SLICE-0012 bundle fixtures reused without changing their semantic facts;
- SLICE-0013 completion report.

Avoid changes to identity/configuration/derived-metric domain modules unless a hard persistence contradiction is found. Report such a contradiction rather than redesigning the domain inside this slice.

## Acceptance criteria

- [ ] PostgreSQL 18 schema is reproducibly migration-created from empty database;
- [ ] no developer secret/manual local schema is required;
- [ ] accepted ResearchEvidenceBundle semantics persist losslessly;
- [ ] pre-canonical targets/observations do not require canonical BoatDesign IDs;
- [ ] bundle versions and observation identities are immutable/fail-closed;
- [ ] exact repeated import is deterministic and idempotent;
- [ ] changed content under an existing immutable identity is rejected, never overwritten;
- [ ] import is transactional/atomic;
- [ ] crosschecks remain structurally outside HullQ evidence/provenance;
- [ ] optional FieldEvidence v0.3 persists without automatic promotion/resolution;
- [ ] round-trip tests prove raw/normalized/claim/applicability fidelity;
- [ ] a real PostgreSQL 18 CI integration job passes;
- [ ] existing Linux/Windows quality gates remain green;
- [ ] no broad ingestion, identity resolver, auto-resolution, query/API/frontend or SailboatData-value persistence is introduced.

## Status handoff rule

SLICE-0013 is `READY` only after SLICE-0012 owner acceptance and merge are canonical on `main`.

Start it only through the normal isolated `START_SLICE.bat` workflow.

The implementation agent MAY set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark SLICE-0013 `DONE`.

`DONE` requires verified local gates, the real PostgreSQL remote integration gate, independent master review and explicit project-owner acceptance.

The implementation agent MUST NOT automatically begin the next benchmark-execution/measurement slice.

After SLICE-0013 acceptance, the intended next bounded step is to run the same controlled benchmark corpus through the importer/database path and measure actual automation, review, idempotency, throughput and cost behavior before broad design-universe ingestion is authorized.

---

## Completion Report

**Report version:** 2 — incorporates fixes for three blocking independent-review findings (PR #27).

### Slice

- Slice ID: `SLICE-0013`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Changes

- Changed files (cumulative across both implementation rounds):
  - `pyproject.toml` — added `psycopg[binary]>=3.2,<4` dependency; added mypy override for psycopg
  - `uv.lock` — added psycopg 3.3.4, psycopg-binary 3.3.4, tzdata 2026.3
  - `.github/workflows/ci.yml` — added `db-integration` job with PostgreSQL 18 service container
  - `src/hullq/persistence/fingerprint.py` — **Finding 3 fix**: sort all collections (observations, evidence, crosschecks, findings) by per-element fingerprint before hashing bundle; order-insensitive
  - `src/hullq/persistence/schema.py` — **Finding 1 fix**: `evidence_row_params` signature simplified to `(ev, content_hash)` — bundle identity removed (18 params, not 20)
  - `src/hullq/persistence/importer.py` — **Finding 1+2 fix**: `_insert_evidence` uses global `research_evidence` table + `bundle_evidence_members` link; all inserts race-safe via `ON CONFLICT DO NOTHING` + rowcount check
  - `src/hullq/persistence/readback.py` — **Finding 1 fix**: `fetch_evidence(conn, evidence_id)` queries global `research_evidence` table (no bundle args); `fetch_bundle_snapshot` uses `bundle_evidence_members`
  - `tests/persistence/conftest.py` — TRUNCATE list updated to include `research_evidence`, `bundle_evidence_members`
  - `tests/persistence/test_persistence_integration.py` — existing tests updated; 5 new integration tests added (Finding 1: global evidence identity; Finding 3: reordered content idempotency)
  - `tests/unit/test_persistence_mocked_db.py` — updated for new `evidence_row_params` signature, new `_insert_observation` semantics (INSERT-first), new `fetch_evidence` signature
  - `docs/slices/SLICE-0013-postgresql-persistence-deterministic-importer.md` — status IN_PROGRESS → REVIEW; completion report added; v2 update with finding fixes
- New files (from initial implementation):
  - `src/hullq/persistence/__init__.py` — public API exports
  - `src/hullq/persistence/_types.py` — `ImportStatus`, `ImportResult`, `PersistenceConflictError`
  - `src/hullq/persistence/connection.py` — `get_database_url`, `open_connection`
  - `src/hullq/persistence/migrations.py` — lightweight numbered-SQL migration runner
  - `src/hullq/persistence/sql/001_initial_schema.sql` — initial schema: `research_bundles`, `research_observations`, `bundle_observation_members`, `bundle_unresolved_findings`, `bundle_reference_crosschecks` (no evidence table here — see 002)
  - `src/hullq/persistence/sql/002_global_evidence_table.sql` — **Finding 1 fix**: creates `research_evidence` (global PK=`evidence_id`) and `bundle_evidence_members`; drops `bundle_promoted_evidence`
  - `tests/persistence/__init__.py` — empty
  - `tests/persistence/conftest.py` — auto-skip when `HULLQ_TEST_DATABASE_URL` not set; `migrated_conn`/`clean_conn` fixtures
  - `tests/unit/test_persistence_connection.py` — 7 connection config unit tests
  - `tests/unit/test_persistence_fingerprint.py` — 28 fingerprint unit tests
  - `tests/unit/test_persistence_importer_unit.py` — 16 importer unit tests (mock cursor)
  - `tests/unit/test_persistence_schema.py` — 18 schema serialization unit tests
  - `tests/unit/test_persistence_mocked_db.py` — 48 mock-based unit tests for migrations, importer, and readback

### Review findings addressed

**Finding 1 — FieldEvidence global immutable identity:**
- Created `src/hullq/persistence/sql/002_global_evidence_table.sql` adding `research_evidence` (PK=`evidence_id`) + `bundle_evidence_members` link table, and dropping `bundle_promoted_evidence`.
- `_insert_evidence` now inserts to global `research_evidence` then adds a `bundle_evidence_members` row. Same evidence_id + same content is reusable across bundles; same evidence_id + different content → CONFLICT.
- `fetch_evidence` simplified to `(conn, evidence_id)` — queries global table directly.
- New integration tests: `test_evidence_global_identity_same_content_reusable_across_bundles`, `test_evidence_global_identity_different_content_fails_closed`.

**Finding 2 — Race-safe INSERT paths:**
- All INSERT statements use `ON CONFLICT ... DO NOTHING`; after each insert `cur.rowcount` is checked. rowcount==0 means DO NOTHING fired, triggering a hash-verification SELECT. rowcount==1 means new row — no SELECT needed.
- Eliminated all check-then-insert patterns. No last-write-wins. Conflicting immutable identities fail closed.

**Finding 3 — Order-insensitive bundle fingerprint:**
- `fingerprint_bundle` now sorts observations, evidence, crosschecks, and findings collections by per-element fingerprint before computing the bundle hash.
- New integration tests: `test_reordered_observations_gives_already_imported`, `test_reordered_evidence_gives_already_imported`.

### Validation

- Local validation: `PASS`
- Commands run (v2 run after finding fixes):
  - `uv run ruff check .` → All checks passed
  - `uv run ruff format --check .` → All checks passed
  - `uv run mypy src` → Success: no issues found in 25 source files
  - `uv run coverage run -m pytest tests/unit/ -v` → **949 passed**, 0 failed, 0 skipped
  - `uv run coverage report --fail-under=90` → **93.55%** overall, **95.73%** persistence module — ≥90% threshold met (exit 0)
  - `uv run python scripts/validate_repository.py` → repository governance validation: PASS
  - `uv run pip-audit` → No known vulnerabilities found
- Results:
  - All 949 unit tests pass; 34 integration tests correctly skip without `HULLQ_TEST_DATABASE_URL` (29 original + 5 new finding-coverage tests)
  - 93.55% combined branch/statement coverage (threshold 90%)
  - `bundle_reference_crosschecks` has no `evidence_id` column — enforced at schema level and verified by structural unit test
  - `bundle_promoted_evidence` replaced by `research_evidence` + `bundle_evidence_members` — verified by schema assertion test

### External verification

- Remote CI: `NOT VERIFIED` — awaiting GitHub CI run on the updated branch head
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none (three blocking findings from independent review fully addressed)
- Spec/ADR ambiguities: none
- Scope deviations:
  - Added `tests/unit/test_persistence_mocked_db.py` beyond the expected touch points in the slice. This was necessary to achieve ≥90% branch coverage without a PostgreSQL server in the quality CI job. The mock-based tests exercise `apply_migrations`, `import_research_evidence_bundle`, `_insert_observation`, all `_from_jsonb` readback helpers, and `fetch_bundle_snapshot` with `MagicMock` connections. No production behavior was changed; the additional file is purely additive test infrastructure.
  - Fixed an over-broad skip condition in `tests/persistence/conftest.py` (`"persistence" in fspath` → `/tests/persistence/` path check) that was incorrectly skipping `tests/unit/test_persistence_*.py` files in the quality CI job.
  - Added `src/hullq/persistence/sql/002_global_evidence_table.sql` migration to fix Finding 1; not in the original expected touch points but required by the review fix.

### Follow-up

- Recommended next action: project-owner reviews updated PR, observes remote CI results (`db-integration` job with PostgreSQL 18 service container), and accepts or returns findings. After DONE, the next bounded step is the benchmark-through-database measurement slice.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.
- Remote CI results (`db-integration` job) have NOT been observed and are recorded as `NOT VERIFIED`.
