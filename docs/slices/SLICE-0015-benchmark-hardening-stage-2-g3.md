# SLICE-0015 — Benchmark Hardening and Stage-2 Gate G3

**ID:** SLICE-0015  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 2.15 — benchmark hardening and Stage-2 G3 decision  
**Depends on:** SLICE-0014 accepted / DONE  
**Blocks:** controlled 1,000-design identity bootstrap experiment

## Objective

Harden the accepted SLICE-0014 benchmark path only where measured evidence requires it, then make the bounded Stage-2 Gate G3 decision using the **pre-committed scorecard**. Thresholds must not move after seeing results.

SLICE-0015 does **not** perform the 1,000-design bootstrap.

```text
accepted SLICE-0014 benchmark path
→ negative-path / failure-class hardening
→ exact 50-case benchmark re-run
→ fixed G3 scorecard
→ G3_PASS / HARDEN_FIRST / BLOCKED technical recommendation
→ independent review
→ project-owner acceptance before operational G3 / broader bootstrap
```

## Controlling evidence

Use the accepted repository state after SLICE-0014, especially:

- `docs/slices/SLICE-0014-acceptance-closure.md`;
- `docs/slices/SLICE-0014-controlled-benchmark-through-postgresql.md`;
- `research/benchmark/persistence/manifest.json`;
- `research/benchmark/persistence/result_schema.json`;
- accepted benchmark runner/materializer/semantic comparator;
- accepted SLICE-0012 research semantics;
- accepted SLICE-0013 PostgreSQL persistence/import semantics;
- accepted SLICE-0014 head `98d2e38e42254bba17279945551d53c17b869f5e` and CI #178.

No new web research is required.

## Binding G3 scorecard

### Zero-tolerance correctness

| Metric | Required |
|---|---:|
| Readback semantic mismatches | 0 |
| Nondeterministic semantic output | 0 |
| Unexpected persistence errors | 0 |
| Duplicate/membership anomalies | 0 |
| Exact re-import idempotency | 100% |
| Fresh-DB semantic equality | 100% |
| Invented / force-resolved values | 0 |
| SailboatData values entering HullQ evidence | 0 |

Any violation is a correctness failure regardless of aggregate percentages.

### Scale / review thresholds

| Metric | Green / strong | Yellow / acceptable | Red / harden | Stop / architecture problem |
|---|---:|---:|---:|---:|
| 50 cases mechanically materializable | >=80% | 65–79% | 50–64% | <50% |
| Cannot materialize without invention | 0–5% | 6–10% | 11–20% | >20% |
| Review-required cases | <=20% | 21–35% | 36–50% | >50% |
| Median review time / reviewed case* | <=3 min | >3–7 min | >7–15 min | >15 min |
| Avg human effort / all designs* | <=1.5 min | >1.5–3 min | >3–6 min | >6 min |

`*` Only where directly and reliably measurable. Use `NOT_MEASURED` rather than fabricated precision.

A G3-positive technical recommendation requires:

```text
ALL correctness gates perfect
AND mechanical materialization >=65%
AND cannot-materialize-without-invention <=10%
AND no newly discovered fundamental contract hole
AND review burden bounded/measurable where applicable
```

SLICE-0014 produced `G3_CANDIDATE`; SLICE-0015 decides whether the hardened evidence supports a technical `G3_PASS` recommendation.

## Contract gap vs retained-evidence gap

Do not conflate these.

**Contract/architecture failure:** accepted contracts cannot faithfully represent a recurring retained fact class without invention or loss. This may support `BLOCKED`.

**Insufficient retained fact:** an old retained artifact lacks enough detail for safe classification/mapping. Classify it as `INSUFFICIENT_RETAINED_FACT` or equivalent. This is not by itself an architecture failure.

## Required hardening from SLICE-0014

Correct the latent recommendation behavior so that:

- `CANNOT_MATERIALIZE` does not automatically mean `BLOCKED`;
- each failure is classified first;
- `BLOCKED` is reserved for a genuine representational/contract insufficiency;
- ordinary validation/materialization/runtime defects drive `HARDEN_FIRST` unless they establish a contract gap;
- normal unknown/pre-canonical evidence never becomes `BLOCKED` merely because it remains unresolved;
- deterministic failure classes are preferred over exception-string inference.

## Required negative-path proof

Add bounded benchmark-only tests/fixtures proving honest failure behavior for at least:

1. **Review-required retained fact** — unsafe conversion requires review; no guessed semantics.
2. **Insufficient retained fact** — classified explicitly; does not automatically imply `BLOCKED`.
3. **Validation/materialization defect** — fails closed and contributes to hardening/failure metrics.
4. **True representational contract gap** — smallest clearly synthetic fixture proves `BLOCKED` is reachable only for contract insufficiency.
5. **Semantic readback mismatch** — deliberate mismatch is detected by the canonical comparator.
6. **Idempotency/conflict failure** — changed immutable semantic content cannot masquerade as exact re-import success.
7. **SailboatData contamination guard** — existing zero-tolerance protection remains active; no SailboatData field values enter HullQ research/evidence fixtures.

Do not turn these fixtures into a generic production ingestion framework.

## Exact benchmark re-run

After hardening, run the unchanged accepted 50-design corpus through:

```text
materialization
→ accepted validation
→ PostgreSQL 18 import
→ full semantic readback
→ exact re-import
→ fresh-schema rerun
→ result/gate schema validation
```

Do not remove hard cases, change membership, or add easy cases to improve rates.

## Review burden and throughput

The accepted benchmark produced zero review-required materialization cases. Do not invent review-time estimates. If real review timing is not directly observable in this slice, retain `NOT_MEASURED` with reason.

PostgreSQL timing remains diagnostic evidence only. Do not create an arbitrary boats-per-second G3 threshold; research ambiguity, identity/applicability and human review are more likely scale bottlenecks.

## Required output

Produce:

- deterministic failure classification;
- focused negative-path tests;
- exact 50-case benchmark re-run;
- machine-readable benchmark result/gate artifact;
- concise G3 decision report evaluating **every binding scorecard metric**;
- one technical recommendation:

```text
G3_PASS
HARDEN_FIRST
BLOCKED
```

If the existing result schema uses `G3_CANDIDATE`, version/extend the gate output cleanly rather than ambiguously rewriting historical retained artifacts.

The report must distinguish measured fact, interpretation, gate decision and next authorized action.

## Decision semantics

### G3_PASS

Technical recommendation only when:

- every zero-tolerance correctness gate is perfect;
- fixed minimum materialization/review thresholds are met;
- no recurring contract hole is exposed;
- failure classification is honest and deterministic;
- exact 50-case re-run remains reproducible;
- independent review finds no blocker.

A technical agent may recommend `G3_PASS` once those conditions are satisfied. The slice is not `DONE`, G3 is not operationally passed, and no broader bootstrap is authorized until the project owner explicitly accepts the slice.

### HARDEN_FIRST

Use when correctness remains intact but scale/review thresholds or a repairable recurring implementation gap require further work. Examples include mechanical materialization below 65%, review-required above 35%, or unreliable negative-path classification.

### BLOCKED

Use when accepted architecture/contracts cannot faithfully represent multiple recurring benchmark fact classes, or deterministic persistence correctness cannot be achieved without redesign. Do not use `BLOCKED` for ordinary unknowns, sparse retained evidence or expected pre-canonical states.

## Explicitly out of scope

Do not implement:

- 1,000-design bootstrap;
- new broad source discovery/acquisition or crawler/bulk web ingestion;
- SailboatData extraction;
- fuzzy canonical identity resolution or automatic BoatDesign creation;
- automatic FieldResolution;
- query engine / OQ-009 implementation;
- FastAPI/public API;
- Astro frontend;
- auth/accounts;
- marketplace/listing adapters;
- saved search/monitoring or price history;
- SEO/public-page implementation;
- Redis/message broker/search engine/Kubernetes/distributed workers;
- HullQ Design Watch implementation.

## Expected touch points

Prefer only:

- `scripts/benchmark/`;
- focused `tests/unit/` benchmark tests;
- focused `tests/persistence/` benchmark integration tests;
- `research/benchmark/persistence/` result/gate schema/report where needed;
- smallest CI adjustment required to retain G3 evidence;
- this slice completion report.

Do not change production domain/persistence contracts unless negative-path evidence demonstrates a genuine accepted-contract defect. If it does, stop and report it rather than opportunistically redesigning inside this slice.

## Acceptance criteria

- [ ] pre-committed thresholds used unchanged;
- [ ] zero-tolerance correctness gates perfect;
- [ ] `CANNOT_MATERIALIZE` does not automatically imply `BLOCKED`;
- [ ] true contract insufficiency has an explicit reachable `BLOCKED` path;
- [ ] review-required / insufficient-retained-fact paths fail closed without invention;
- [ ] deliberate semantic mismatch is detected;
- [ ] changed immutable content cannot masquerade as idempotent success;
- [ ] SailboatData value contamination remains zero;
- [ ] exact 50-design membership unchanged;
- [ ] real PostgreSQL 18 import/re-import/fresh-schema behavior is deterministic;
- [ ] result/gate artifacts retained and schema-validated;
- [ ] reviewer/cost timing remains `NOT_MEASURED` where not observable;
- [ ] G3 report evaluates every binding scorecard metric;
- [ ] no broad ingestion/query/API/frontend/marketplace scope introduced;
- [ ] Ubuntu/Windows quality, PostgreSQL integration, dependency audit, Ruff, format, strict mypy and coverage gates green;
- [ ] independent master review has no unresolved blocker;
- [ ] explicit project-owner acceptance occurs before `DONE` / operational G3 passage.

## Status handoff rule

SLICE-0015 is `READY` only because SLICE-0014 has explicit project-owner acceptance and PR #29 is merged as `71100b50052ed7c2910b096e36b8a5402f757191`.

Start it only through the normal isolated `START_SLICE.bat` workflow after the closure/readiness PR containing this contract is merged to `main`.

The implementation agent MAY set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark SLICE-0015 `DONE`.

`DONE` requires verified gates, independent review, an explicit gate recommendation and explicit project-owner acceptance.

The agent MUST NOT automatically begin the 1,000-design bootstrap or any later slice.

---

## Completion report (second correction round — head a3b3234)

**Status:** REVIEW  
**Branch:** `slice/0015-benchmark-hardening-stage-2-g3`  
**Head commit:** `a3b3234`  
**PR:** #31  
**Previous reviewed head:** `d5d760a` (CI #184 PASS)  
**Remote CI for new head:** NOT VERIFIED (push just completed; CI #185 in progress)

### What changed in this round (second correction)

Addresses independent review #4991372937 (two acceptance blockers):

**BLOCKER 1 — VALIDATION_FAILURE must force HARDEN_FIRST regardless of percentage:**
- `scripts/benchmark/gate.py`: Removed `cannot_materialize` parameter (now derived internally as `validation_failure_count + insufficient_retained_fact_count + contract_gap_count`). Added explicit `validation_failure_count`, `insufficient_retained_fact_count`, `fresh_run_error` parameters. Gate priority 2 fires on any `validation_failure_count > 0` → HARDEN_FIRST before rate gates are evaluated.
- `scripts/benchmark/runner.py`: Updated classification loop to populate `validation_failure_count` and `insufficient_retained_fact_count` separately; updated `evaluate_g3_gate()` call.

**BLOCKER 2 — Scorecard rows semantically accurate:**
- `fresh_db_semantic_equality`: PASS now requires BOTH `fresh_run_imported == materialized` AND `fresh_run_semantic_mismatches == 0`.
- `unexpected_persistence_errors`: Now includes `fresh_run_error` covering all import failures in the fresh-schema phase.
- `duplicate_membership_anomalies`: Changed to `measured=GUARD_VERIFIED, evidence_basis=VERIFIED_INVARIANT` — established by PostgreSQL integration tests, not a separate runtime counter.
- Schema (`result_schema.json`): `g3_scorecard` already required. Added `contract_gap_count`, `validation_failure_count`, `insufficient_retained_fact_count` to `corpus_materialization.required`. Added `fresh_run_error` as optional in `persistence`.

**Small cleanup:** Runner argparse description corrected from SLICE-0014 to SLICE-0015.

### Files changed

| File | Change |
|---|---|
| `scripts/benchmark/gate.py` | Rewritten: explicit failure-class params, derived cannot_materialize, gate 2 validation_failure, fixed scorecard rows |
| `scripts/benchmark/runner.py` | Updated: classification loop, fresh_error tracking, evaluate_g3_gate() call, argparse |
| `research/benchmark/persistence/result_schema.json` | Added failure-class counts to corpus_materialization.required; added fresh_run_error |
| `tests/unit/test_negative_path_hardening.py` | Updated all tests to use new params; 4 new gate semantics tests added (36 total) |

### Local validation

| Gate | Result |
|---|---|
| `test_negative_path_hardening.py` (36 tests) | 36/36 PASS |
| Full unit test suite | 1023/1023 PASS |
| Full test suite (unit + integration skipped) | 1275 passed, 164 skipped |
| Repository validator | PASS |
| `ruff check` benchmark + test file | CLEAN |
| `ruff format --check` benchmark + test file | CLEAN |
| `mypy --strict scripts/benchmark/gate.py` | CLEAN |
| Coverage (scripts/benchmark + src) | 93.59% |

### New tests added

1. `test_g3_gate_validation_failure_single_case_forces_harden_first` — 1 VALIDATION_FAILURE/50 (2% ≤ 10%) → HARDEN_FIRST; confirms gate 2 fires before rate gate.
2. `test_g3_gate_insufficient_retained_fact_within_threshold_is_pass` — 1 INSUFFICIENT_RETAINED_FACT/50 (2%) → G3_PASS; confirms rate-based treatment.
3. `test_g3_gate_fresh_db_semantic_equality_fails_on_mismatch` — import complete but `fresh_run_semantic_mismatches=1` → `fresh_db_semantic_equality` row FAIL.
4. `test_schema_validation_fails_if_g3_scorecard_omitted` — `jsonschema.validate` raises when `g3_scorecard` is absent.

### Thresholds unchanged

- Mechanical materialization: ≥ 65%
- Cannot-materialize-without-invention: ≤ 10%
- Review-required: ≤ 35%
- Corpus membership: exactly 50 cases (unchanged)

### Unresolved findings

None. All second-correction-round blockers addressed.

### Remote / external verification

Remote CI for head `a3b3234` is **NOT VERIFIED** at report time. CI #184 on `d5d760a` was verified PASS. The second correction round changes are non-semantic with respect to the 50-case benchmark run itself (gate logic only; no corpus change); CI outcome expected to match.

### Agent declaration

I am the implementation agent. I have applied all changes specified in independent review #4991372937. I have NOT marked this slice DONE. I have NOT started the 1,000-design bootstrap or any later slice. I have NOT merged to main. The slice remains in REVIEW pending remote CI verification and project-owner acceptance.
