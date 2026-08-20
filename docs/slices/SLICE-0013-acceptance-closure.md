# SLICE-0013 — Acceptance Closure

**ID:** SLICE-0013  
**Final status:** DONE  
**Accepted:** 2026-08-20  
**Implementation PR:** #27  
**Accepted implementation head:** `2da1ad19717707f3ec48c0ebfd6925d5e2fee043`  
**Merge commit:** `2b8417beeb848507ba0f97c49bbd0f37d647c438`

## Acceptance result

SLICE-0013 is explicitly accepted by the project owner and closed as `DONE`.

The accepted implementation establishes HullQ's first physical PostgreSQL persistence boundary:

- PostgreSQL 18 migration-created schema from an empty database;
- environment-driven PostgreSQL configuration with no committed secrets or import-time connection side effects;
- immutable versioned `ResearchEvidenceBundle` persistence;
- globally stable immutable `ResearchObservation` identity;
- globally stable immutable `FieldEvidence` v0.3 identity;
- explicit bundle↔observation and bundle↔evidence membership tables;
- lossless persistence of raw observations, normalized candidates, claim semantics and applicability;
- structurally separate reference-crosscheck persistence with no evidence IDs;
- deterministic semantic fingerprints;
- atomic transactional import;
- idempotent exact re-import behavior;
- fail-closed immutable-identity collision behavior;
- race-safe PostgreSQL-native `ON CONFLICT` import semantics;
- order-insensitive bundle fingerprinting consistent with unordered membership persistence;
- minimal semantic readback/round-trip support;
- dedicated real PostgreSQL 18 CI integration coverage.

## Verified gates

Final independently reviewed head:

`2da1ad19717707f3ec48c0ebfd6925d5e2fee043`

GitHub Actions CI run **#166** passed on that exact documentation-only final head:

- Ubuntu quality: PASS;
- Windows quality: PASS;
- PostgreSQL 18 integration: PASS;
- dependency audit: PASS;
- repository contract validation: PASS;
- Ruff check: PASS;
- Ruff format check: PASS;
- strict mypy: PASS;
- tests with branch coverage: PASS;
- coverage enforcement: PASS.

The last technical exact head before documentation-only cleanup, `5cd9f9283dd927013925c0b2f66a756cfc27d52e`, passed CI run **#165**, including **37/37** real PostgreSQL persistence integration tests against PostgreSQL **18.6**.

Final implementation-agent local report:

- 949 unit tests passed;
- 93.55% overall coverage;
- 95.73% persistence-module coverage;
- Ruff/format: clean;
- strict mypy: clean;
- repository validator: PASS;
- pip-audit: no known vulnerabilities.

## Review corrections incorporated before acceptance

Independent review identified and verified fixes for:

1. **Global immutable FieldEvidence identity** — `evidence_id` is globally stable rather than bundle-scoped, with a separate bundle-membership relation.
2. **Race-safe import semantics** — check-then-insert paths were replaced by PostgreSQL-native conflict-safe insertion and hash verification.
3. **Order-insensitive bundle fingerprinting** — collection order no longer creates false semantic conflicts where persistence membership is unordered.
4. **Migration-baseline cleanup** — the unreleased intermediate migration was removed and the final global-evidence structure folded directly into `001_initial_schema.sql`.
5. **Real concurrency proof** — four integration tests use separate PostgreSQL connections synchronized by `threading.Barrier`, covering identical concurrent bundle imports, shared global observations, shared global evidence and conflicting immutable identities with rollback.

## Standing data-governance result

The persistence layer preserves the accepted SLICE-0012 policy:

```text
independent HullQ research
→ ResearchObservation / ResearchEvidenceBundle
→ explicit caller-supplied promotion when identity is resolved
→ immutable FieldEvidence
→ later FieldResolution boundary
```

No fuzzy identity resolution, automatic canonical subject creation, automatic promotion or automatic FieldResolution is performed by the importer.

SailboatData remains post-hoc reference comparison only. Crosschecks are stored separately and may not become HullQ evidence or provide fallback field values.

## Next boundary

SLICE-0013 unblocks controlled benchmark execution through the real persistence path.

The next bounded step is `SLICE-0014 — Controlled 50-Design Benchmark Through PostgreSQL`.

SLICE-0014 must reuse the existing controlled benchmark corpus and retained HullQ research artifacts. It is a measurement/hardening exercise, not authorization for broad web acquisition, broad ingestion, query/API/frontend work or the 1,000-design bootstrap.
