# SLICE-0014 — Controlled 50-Design Benchmark Through PostgreSQL

**ID:** SLICE-0014  
**Type:** DESIGN_RESEARCH  
**Status:** REVIEW  
**Stage:** 2.14 — persistence-path benchmark execution and measurement  
**Depends on:** SLICE-0013 accepted / DONE  
**Blocks:** benchmark hardening / Stage-2 Gate G3 decision

## Objective

Run the **same controlled 50-design benchmark corpus** already retained from SLICE-0011 through the accepted SLICE-0012 research-bundle semantics and the real SLICE-0013 PostgreSQL persistence/import path.

This slice answers a different question from the original web benchmark:

> Can HullQ represent and persist the difficult benchmark cases deterministically, repeatedly and cheaply enough to justify moving toward broader design-universe ingestion?

The target flow is:

```text
retained SLICE-0011 benchmark evidence
        ↓
mechanical benchmark-only ResearchEvidenceBundle materialization
        ↓
validation against accepted SLICE-0012 contracts
        ↓
SLICE-0013 deterministic PostgreSQL importer
        ↓
readback + idempotent re-run
        ↓
measured automation/review/throughput/conflict results
```

No new production ingestion architecture is authorized by this slice.

## Controlling inputs

Use the accepted repository state after SLICE-0013 and the retained benchmark artifacts, especially:

- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`;
- `research/benchmark/BENCHMARK-50-classification.csv`;
- `research/benchmark/BENCHMARK-50-analysis.md`;
- `research/benchmark/BENCHMARK-50-closure-review.md`;
- `research/benchmark/waves/WAVE-01-summary.md` through `WAVE-06-summary.md`;
- accepted SLICE-0012 schemas/runtime for `ResearchObservation`, claim semantics, applicability, `ResearchEvidenceBundle` and explicit promotion;
- accepted SLICE-0013 persistence/import/readback boundary.

Historical/legacy benchmark notes may be consulted only to recover facts already retained by HullQ. They do not override accepted closure/review corrections.

## Hard source rule

This slice is **not a new web-research slice**.

Do not browse, crawl or acquire new source data merely to make a benchmark case complete.

For each benchmark case:

- mechanically transcribe only retained HullQ benchmark facts that can be represented faithfully;
- preserve ambiguity, unknowns, basis differences, generation/configuration applicability and unresolved findings;
- if a retained fact cannot be represented without interpretation or invention, record that as review-required rather than silently filling it;
- synthetic benchmark scaffolding must be clearly identified as synthetic and must never masquerade as historical source/research provenance.

SailboatData remains outcome-only post-hoc reference QA. No SailboatData field value may enter a `ResearchObservation`, `FieldEvidence`, benchmark fixture value, fallback value or canonical resolution.

## Benchmark identity

The benchmark population remains the exact 50 deliberately difficult design cases already closed under SLICE-0011.

Do not add easy cases to improve rates and do not replace difficult cases.

If the retained ledger exposes a material identity ambiguity, preserve the benchmark case as the retained research target rather than inventing a canonical BoatDesign identity.

The benchmark harness may use deterministic **benchmark-local IDs** for fixture/runner addressing. Such IDs are not production canonical BoatDesign IDs.

## Required implementation shape

Keep benchmark execution separate from production domain semantics.

A bounded shape is preferred, for example:

```text
research/benchmark/persistence/
    manifest / benchmark-only fixtures / result report

scripts/benchmark/
    deterministic materialization + runner
```

or an equivalently small structure.

Do not build a generic ingestion framework, crawler or job-distribution system.

The benchmark runner must consume the accepted production validation/persistence APIs rather than reimplementing importer behavior.

## Required benchmark manifest

Create one deterministic machine-readable manifest representing exactly the 50 retained benchmark cases.

Each case must include enough metadata to trace it back to the accepted benchmark corpus, including at minimum:

- stable benchmark case ID;
- displayed manufacturer/model/design label as retained;
- wave;
- retained stress-classification flags or reference to the classification row;
- retained artifact references used to materialize the case;
- materialization status;
- review-required reason(s), when applicable.

The manifest itself must not invent technical sailboat values.

## Bundle materialization

Materialize a valid `ResearchEvidenceBundle` for every benchmark case where the retained artifacts support one without invention.

A case may contain:

- pre-canonical `ResearchObservation` objects;
- explicit applicability;
- unresolved findings;
- reference-crosscheck outcomes;
- optional already-promoted `FieldEvidence` only where the benchmark input explicitly supplies a stable subject for the harness.

Do **not** force all 50 cases into promoted `FieldEvidence` merely to improve a metric.

Do not perform fuzzy identity resolution or automatic promotion.

If a benchmark-local synthetic `ProvenanceSubject` is used solely to exercise the promotion/persistence path, it must be clearly marked as benchmark scaffolding and must not be represented as a production canonical identity.

## Database execution

Run the benchmark against a clean PostgreSQL 18 database created through the accepted migration path.

Required phases:

```text
empty PostgreSQL 18 DB
→ apply migrations
→ import benchmark cases
→ read back persisted state
→ import the exact same benchmark again
→ verify deterministic idempotency
→ run a second fresh-database execution
→ compare deterministic semantic outcomes
```

The runner must not depend on the project owner's local database name/password or manually prepared schema.

Use `HULLQ_TEST_DATABASE_URL` or a benchmark-specific test URL derived from the accepted environment-driven pattern.

## Mandatory measurements

Produce a machine-readable result artifact and concise human-readable report covering at least:

### Corpus/materialization

- total benchmark cases: expected **50**;
- bundles materialized automatically/mechanically;
- cases requiring human review before valid materialization;
- cases that cannot be materialized from retained evidence without invention;
- reasons for review/materialization failure grouped by problem class.

### Persistence

- valid bundles submitted;
- first-pass `IMPORTED` count;
- first-pass `CONFLICT` count;
- persistence errors outside expected `CONFLICT` semantics;
- exact re-run `ALREADY_IMPORTED` count;
- unexpected duplicate/membership anomalies;
- readback mismatches;
- fresh-run semantic/fingerprint mismatches.

### Promotion applicability

- cases/observations eligible for explicit promotion from retained benchmark input;
- cases remaining pre-canonical/unresolved;
- any promotion blocked by subject/field contradiction;
- no success-rate penalty for honestly remaining pre-canonical.

### Human-review burden

Measure actual review effort for the benchmark-materialization step:

- number of review-required cases;
- number of review decisions;
- elapsed reviewer minutes where directly observable;
- median/mean reviewer minutes per reviewed case where the sample is sufficient.

Do not fabricate timing. If review time cannot be measured reliably, report `NOT_MEASURED` and why.

### Throughput

On at least one documented environment, record:

- wall-clock import time for the materialized corpus;
- cases/bundles per second or equivalent;
- repeat-run time;
- database version;
- Python version;
- exact git SHA.

Performance numbers are diagnostic benchmark evidence, not production SLOs.

### Cost

Record only directly observable cost/usage data.

If API/token/compute cost is not available from the execution environment, report cost as `NOT_MEASURED`; do not estimate fictional precision from subscription-plan pricing.

The primary cost proxy in this slice is human-review burden plus measured execution time.

## Determinism requirements

The benchmark result must be reproducible at semantic level.

At minimum:

- same retained input + same code produces the same bundle semantic fingerprints;
- exact second import is idempotent;
- a fresh database run yields the same semantic import/readback outcomes;
- benchmark-local generated IDs must be deterministic, not random per run;
- timestamps that are inherently run-specific must not be included in semantic equality checks unless the accepted contract makes them semantic input.

Do not mutate accepted benchmark facts merely to obtain deterministic output.

## Failure classification

Every non-success must be classified rather than hidden.

Suggested classes:

```text
MATERIALIZATION_REVIEW_REQUIRED
INSUFFICIENT_RETAINED_FACT
IDENTITY_AMBIGUITY
APPLICABILITY_AMBIGUITY
BASIS_DEFINITION_AMBIGUITY
VALIDATION_FAILURE
IMMUTABLE_IDENTITY_CONFLICT
READBACK_MISMATCH
NONDETERMINISTIC_OUTPUT
UNEXPECTED_PERSISTENCE_ERROR
```

Extend only if real benchmark evidence requires another materially distinct class.

## Required tests

Add focused tests proving at least:

1. benchmark manifest contains exactly 50 unique retained case IDs;
2. case membership matches the accepted 50-design benchmark ledger/classification;
3. manifest/materialization uses no network access;
4. no SailboatData field values are introduced;
5. synthetic benchmark scaffolding is explicitly distinguishable from retained facts;
6. deterministic benchmark-local IDs/fingerprints are stable across repeated materialization;
7. every materialized bundle validates under accepted contracts;
8. all materialized bundles can be imported into an empty real PostgreSQL 18 database unless explicitly classified as an expected benchmark failure;
9. exact re-import returns deterministic idempotent outcomes;
10. fresh-database second run yields the same semantic outcomes;
11. readback preserves raw/normalized/claim/applicability semantics for representative hard cases;
12. unresolved/pre-canonical cases remain unresolved/pre-canonical without forced BoatDesign creation;
13. optional promotion happens only with an explicit supplied subject and never via fuzzy lookup;
14. conflicts/errors do not leave partial losing bundle state;
15. benchmark metric generation is deterministic apart from explicitly non-semantic runtime measurements;
16. existing Ubuntu/Windows quality gates remain green;
17. real PostgreSQL 18 integration gate remains green;
18. repository validator, Ruff, format, strict mypy, coverage threshold and dependency audit remain green.

## Required output

At completion, produce at minimum:

- deterministic 50-case benchmark manifest;
- benchmark-only materialization fixtures or equivalent traceable input representation;
- deterministic benchmark runner;
- machine-readable result output/schema;
- concise benchmark report summarizing measured rates and failure classes;
- explicit recommendation for the next bounded step based on measured evidence.

The report must distinguish:

```text
measured fact
vs
benchmark interpretation
vs
recommended next action
```

## Decision gate

SLICE-0014 does **not** automatically authorize broad ingestion.

Its result must support one of these recommendations:

```text
A. HARDEN FIRST
   material persistence/materialization defects remain

B. G3 CANDIDATE
   pipeline is sufficiently deterministic and review burden is measurable;
   proceed to a dedicated hardening/G3 slice

C. BLOCKED
   accepted contracts are insufficient for the retained benchmark corpus
```

The implementation/research agent must not declare Stage-2 Gate G3 passed on its own.

## Explicitly out of scope

Do not implement:

- new broad web research/source discovery;
- crawlers or bulk source adapters;
- SailboatData extraction or value persistence;
- fuzzy/canonical BoatDesign identity resolver;
- automatic canonical entity creation;
- automatic FieldResolution;
- broad production ingestion;
- the 1,000-design bootstrap;
- query engine / OQ-009 implementation;
- FastAPI/public API;
- Astro frontend;
- auth/accounts;
- marketplace/listing ingestion;
- saved search/monitoring;
- price history;
- SEO/public page implementation;
- Redis/message broker/search engine/Kubernetes/distributed workers.

If the benchmark exposes a missing domain/persistence contract, record it and stop that path rather than silently widening scope.

## Expected touch points

Prefer a bounded set such as:

- `research/benchmark/persistence/` for manifest/fixtures/result report;
- `scripts/benchmark/` for deterministic benchmark materialization/execution;
- focused benchmark unit tests;
- focused PostgreSQL benchmark integration tests;
- smallest CI extension needed to prove the benchmark path;
- slice completion report.

Production persistence/domain modules should not change unless the benchmark demonstrates a concrete accepted-contract defect. If such a defect is found, report it rather than opportunistically redesigning the system inside this slice.

## Acceptance criteria

- [ ] exact accepted 50-case benchmark population is represented;
- [ ] no new web acquisition is required for benchmark completion;
- [ ] no SailboatData field value enters HullQ evidence or fixtures;
- [ ] retained facts vs synthetic scaffolding remain explicit;
- [ ] benchmark bundles/materialization are deterministic;
- [ ] real PostgreSQL 18 execution is reproducible;
- [ ] exact repeated import is idempotent;
- [ ] fresh-database rerun produces the same semantic outcomes;
- [ ] unknown/ambiguous cases remain honest rather than being force-resolved;
- [ ] actual review burden and throughput are measured where observable;
- [ ] unobservable cost/timing is marked `NOT_MEASURED`, never invented;
- [ ] result artifact clearly classifies every non-success;
- [ ] existing repository/quality/CI gates remain green;
- [ ] no broad ingestion/query/API/frontend/marketplace scope is introduced.

## Status handoff rule

SLICE-0014 is `READY` only because SLICE-0013 has explicit project-owner acceptance and PR #27 is merged as commit `2b8417beeb848507ba0f97c49bbd0f37d647c438`.

Start it only through the normal isolated `START_SLICE.bat` workflow after the closure/readiness PR containing this contract is merged to `main`.

The implementation/research agent MAY set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark SLICE-0014 `DONE`.

`DONE` requires verified local gates, real PostgreSQL remote CI where applicable, independent master review and explicit project-owner acceptance.

The agent MUST NOT automatically begin SLICE-0015 or the 1,000-design bootstrap.

---

## Completion report (Session 1 — superseded by Session 2 below)

### Slice (Session 1)

- Slice ID: `SLICE-0014`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Changes (Session 1)

**New files created:**

- `research/benchmark/persistence/manifest.json` — deterministic 50-case benchmark manifest
- `research/benchmark/persistence/result_schema.json` — JSON Schema 2020-12 for runner output artifact
- `scripts/benchmark/__init__.py` — package marker
- `scripts/benchmark/materializer.py` — initial materializer (one TEXT_FRAGMENT per design; superseded by Session 2 rewrite)
- `scripts/benchmark/runner.py` — CLI benchmark runner (hardcoded metrics; superseded by Session 2 fix)
- `tests/unit/test_benchmark_manifest.py` — 26 offline unit tests (updated in Session 2)
- `tests/persistence/test_benchmark_persistence.py` — PostgreSQL integration tests (updated in Session 2)

**Session 1 head:** `70d1a96bece8bd3bf921bb03dcf1876883792038`
**Session 1 CI #171:** PASS (quality Ubuntu/Windows, db-integration PostgreSQL 18, dependency audit)

---

## Completion report (Session 2 — review fixes)

### Slice

- Slice ID: `SLICE-0014`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Session 2 context

Independent review of PR #29 (head `70d1a96`) found 6 blocking issues. All 6 are addressed in this session's commit (`f9b5adb`).

### Changes (Session 2 — 5 files modified)

**`scripts/benchmark/materializer.py` — complete rewrite:**
- Added `MaterializationResult` dataclass with `case_id`, `status`, `bundle`, `review_reasons`.
- `materialize_all()` now returns `dict[str, MaterializationResult]` (was `dict[str, ResearchEvidenceBundle]`).
- W01/W02: field-level rows from committed legacy JSONL exports auto-migrated into real `ResearchObservation` objects. Each non-research-tier row becomes one observation with independently derived `EvidenceType`, `ClaimSemantics`, `ObservationApplicability`. Research-tier rows used only for finding creation.
- W03–W06: field-/claim-level retained facts from wave summary `.md` artifacts, embedded as Python data structures (`_W03W06_FACTS`, `_W03W06_CROSSCHECK`, `_W03W06_FINDING`). Explicit per-case crosscheck outcomes from wave summaries.
- Helpers: `_make_app()`, `_map_confidence()`, `_map_evidence_type()`, `_map_claim_semantics()`, `_map_applicability()`, `_cc_to_outcome()`, `_worst_outcome()`, `_decode_legacy_jsonl()`.
- Finding creation: evidence_status-based (W01/W02 non-research rows) + research-tier cc-based + conflict_unresolved fallback. All findings use `topic="conflict_or_unresolved_evidence"`.
- No SailboatData field values. No new web research. All 50 cases produce `status=MATERIALIZED`.

**`scripts/benchmark/runner.py` — real metrics + schema isolation:**
- Derives `materialized`/`review_required`/`cannot_materialize` counts from actual `MaterializationResult.status`.
- Extracts bundles from `MaterializationResult` for persistence phases.
- Phase 4 fresh-DB rerun uses schema isolation (`CREATE SCHEMA + SET search_path + apply_migrations from zero + DROP SCHEMA CASCADE`) instead of TRUNCATE on the already-migrated DB.
- `G3_CANDIDATE`/`HARDEN_FIRST` recommendation depends on `mat_count == total` in addition to all persistence phase metrics.
- Calls `_validate_result_json()` after writing output to validate against `result_schema.json`.

**`.github/workflows/ci.yml` — benchmark runner step added:**
- Added `Run benchmark runner against PostgreSQL 18` step executing `scripts/benchmark/runner.py`.
- Added `Validate benchmark result against schema` step using jsonschema to validate `BENCHMARK-RESULT.json` against `result_schema.json` and assert recommendation is in `{G3_CANDIDATE, HARDEN_FIRST, BLOCKED}`.

**`tests/unit/test_benchmark_manifest.py` — fixture and test updates:**
- `bundles` fixture updated: extracts `.bundle` from `MaterializationResult`.
- `test_bundle_ids_are_deterministic`, `test_bundle_fingerprints_are_stable`, `test_observation_ids_are_deterministic`: second `materialize_all()` call also extracts `.bundle`.
- Removed `test_observation_source_ids_use_benchmark_prefix` (real URLs won't share synthetic prefix).
- Removed `test_observation_notes_contain_benchmark_marker` (real observations carry source notes not markers).
- Added `test_observation_source_ids_are_non_empty` (all `source_id` fields must be non-empty).
- Added `test_materialization_all_50_materialized` (all 50 cases must have `status=MATERIALIZED`).

**`tests/persistence/test_benchmark_persistence.py` — fixture and test updates:**
- `benchmark_bundles` fixture updated: extracts `.bundle` from `MaterializationResult`.
- `fresh_db_results` fixture rewritten to use schema isolation (matches Phase 4 runner approach).
- Added `test_exhaustive_observation_semantic_readback` — parametrized over 4 representative cases (B01-001, B02-007, B04-003, B05-006), verifying every persisted `ResearchObservation` field against the original: `source_id`, `raw.kind`, `raw.value`, `raw.unit`, `evidence_type`, `claim_semantics`, all 10 `applicability` fields, `confidence`, `notes`.

**No production domain/persistence modules were changed.**

### Validation (Session 2)

- Local validation: `PASS`
- Commands run:
  ```
  uv run ruff format scripts/benchmark/ tests/unit/test_benchmark_manifest.py tests/persistence/test_benchmark_persistence.py
  uv run ruff check --fix scripts/benchmark/ tests/unit/test_benchmark_manifest.py tests/persistence/test_benchmark_persistence.py
  uv run mypy scripts/benchmark/materializer.py scripts/benchmark/runner.py --ignore-missing-imports
  uv run ruff format --check .
  uv run ruff check .
  uv run mypy src
  uv run pytest tests/unit/ -q
  ```
- Results:
  - ruff format: all files formatted or already formatted — PASS
  - ruff check (fix): 1 import-sort fixed, 0 remaining — PASS
  - ruff format --check .: 172 files already formatted — PASS
  - ruff check .: All checks passed — PASS
  - mypy src: Success, no issues found in 25 source files — PASS
  - mypy scripts: Success, no issues found in 2 source files — PASS
  - pytest tests/unit/: **975 passed** in 31.54s — PASS

### Measured benchmark result (local, offline materialization)

- Total benchmark cases: **50**
- Materialized automatically: **50** (`status=MATERIALIZED` for all 50)
- Review required: **0**
- Cannot materialize: **0**
- Review decisions required: **0** (no human review needed for materialization)
- Reviewer minutes: `NOT_MEASURED` (all cases materialized mechanically from retained evidence)

### External verification (Session 2)

- Remote CI #173 for head `d871d51` (pre-session-3 state): **VERIFIED PASS** — PostgreSQL 18.6, 158 persistence tests, benchmark runner, Ubuntu, Windows, dependency audit.

### External verification (Session 3 — review #4985913258 fixes)

- Remote CI for new head `ee84e6c`: `NOT VERIFIED` — pushed at time of report; CI must be observed post-push.
- Coverage threshold (90%): `NOT VERIFIED` — must be observed in CI run.

### Persistence results (local integration tests unavailable — no HULLQ_TEST_DATABASE_URL locally)

- Integration tests (`tests/persistence/`) skipped locally when `HULLQ_TEST_DATABASE_URL` is unset.
- All persistence outcomes (first_pass_imported, reimport_already_imported, fresh_run_imported, readback_mismatches, semantic_mismatches, recommendation) are `NOT VERIFIED` pending CI db-integration job.

### Session 3 local gate results

- ruff format: PASS (4 files reformatted)
- ruff check: PASS (All checks passed, after fix for I001/SIM102)
- mypy src: PASS (no issues in 25 source files)
- pytest tests/unit/: **979 passed** in 25.92s — PASS (4 new tests added)
- Coverage (src + scripts): 93.55%

### Scope deviations

- None. All changes within `scripts/benchmark/`, `tests/unit/`, `tests/persistence/`, `.github/workflows/ci.yml` touch points.
- No production domain/persistence modules modified.
- No new web research, no SailboatData field values, no fuzzy identity resolution, no automatic promotion, no SLICE-0015 started.

### Findings

- **Blocker 1 resolved (fail-closed semantics):** `_map_claim_semantics` now defaults to `ClaimSemantics.UNKNOWN`; uses `_FIELD_TO_CLAIM`, `_NOMINAL_DESIGN_FIELDS`, `_OTHER_CLAIM_FIELDS` lookup tables. `_map_evidence_type` removes tier-A fallback; classifies via source-name keywords only. B06-008 J/105 class rule fields produce `CLASS_RULE_CONSTRAINT`. Four focused unit tests added.
- **Blocker 2 resolved (materialization status):** `materialize_all` derives status from actual conversion outcome via try/except; a-priori `test_materialization_all_50_materialized` replaced with `test_materialization_status_derived_from_conversion`; runner `human_review_burden` uses real counts; `automation_rate_disclaimer` added to result doc.
- **Blocker 3 resolved (corpus-wide semantic readback):** `compare_observation_semantics()` reusable helper covers all semantic fields (source_id, raw, normalized_candidate, evidence_type, claim_semantics, all 10 applicability fields, producer, research_context, confidence, notes, intended_field_pointer). Runner Phase 2 and Phase 4 upgraded to full semantic comparison. `test_corpus_wide_semantic_readback_all_bundles` (50 bundles, first-pass schema) and `test_corpus_wide_semantic_readback_fresh_schema` (fresh DROP+CREATE schema) added to persistence tests.
- **Blocker 4 resolved (outputs + traceability):** `_validate_result_json` raises on failure (not just prints); Phase 4 uses `DROP SCHEMA IF EXISTS` before `CREATE SCHEMA`; same fix in `fresh_db_results` fixture; `_write_report()` generates `BENCHMARK-REPORT.md` with MEASURED FACT / INTERPRETATION / RECOMMENDED NEXT ACTION sections; `--report` and `--sha` CLI args added; `HULLQ_IMPL_SHA` env var support; CI uploads both `BENCHMARK-RESULT.json` and `BENCHMARK-REPORT.md` as artifacts.

### Benchmark recommendation

Cannot confirm `G3_CANDIDATE` until CI db-integration job runs with new head `ee84e6c` and persistence phase outcomes are observed. Local evidence (all 50 materialized, 979 unit tests pass, determinism proven) is consistent with `G3_CANDIDATE` if persistence phases also succeed. The actual recommendation will be in `BENCHMARK-RESULT.json` produced by CI and uploaded as an artifact.

### Follow-up

- Recommended next action: observe CI for new head `ee84e6c` on PR #29. If both quality and db-integration jobs (including benchmark runner and schema validation) pass, the slice is ready for independent acceptance review.
- Do NOT start SLICE-0015 or the 1,000-design bootstrap until this slice is explicitly accepted as `DONE` by the project owner.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.
- Remote CI for new head `ee84e6c` is `NOT VERIFIED` at time of this report.
