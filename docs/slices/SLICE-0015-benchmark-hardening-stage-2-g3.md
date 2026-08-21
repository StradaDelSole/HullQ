# SLICE-0015 — Benchmark Hardening and Stage-2 Gate G3

**ID:** SLICE-0015  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 2.15 — benchmark hardening and Stage-2 G3 decision  
**Depends on:** SLICE-0014 accepted / DONE  
**Blocks:** controlled 1,000-design identity bootstrap experiment

## Objective

Harden the accepted SLICE-0014 benchmark path only where measured/reviewed evidence requires it, then make the bounded Stage-2 Gate G3 decision using the **pre-committed scorecard**.

This slice exists to prevent goalpost movement after seeing the 50-design benchmark result.

It does **not** perform the 1,000-design bootstrap itself.

Target flow:

```text
accepted SLICE-0014 benchmark path
        ↓
negative-path / failure-class hardening
        ↓
re-run accepted 50-design benchmark
        ↓
apply fixed G3 scorecard
        ↓
G3 PASS / HARDEN FIRST / BLOCKED recommendation
        ↓
owner acceptance required before any broader bootstrap
```

## Controlling evidence

Use only the accepted repository state after SLICE-0014, especially:

- `docs/slices/SLICE-0014-acceptance-closure.md`;
- `docs/slices/SLICE-0014-controlled-benchmark-through-postgresql.md`;
- `research/benchmark/persistence/manifest.json`;
- `research/benchmark/persistence/result_schema.json`;
- accepted benchmark runner/materializer/comparator;
- accepted SLICE-0012 research semantics;
- accepted SLICE-0013 PostgreSQL persistence/import semantics;
- exact SLICE-0014 accepted implementation head `98d2e38e42254bba17279945551d53c17b869f5e`;
- exact accepted CI #178 result.

No new web research is required to complete this slice.

## Pre-committed G3 scorecard — binding

Do not change these thresholds after seeing results.

### Zero-tolerance correctness gates

The following must be perfect:

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

Any violation is a correctness failure regardless of aggregate benchmark percentage.

### Scale/review gates

| Metric | Green / strong | Yellow / acceptable | Red / harden | Stop / architecture problem |
|---|---:|---:|---:|---:|
| 50 cases mechanically materializable | >=80% | 65–79% | 50–64% | <50% |
| Cannot materialize without invention | 0–5% | 6–10% | 11–20% | >20% |
| Review-required cases | <=20% | 21–35% | 36–50% | >50% |
| Median review time / reviewed case* | <=3 min | >3–7 min | >7–15 min | >15 min |
| Avg human effort / all designs* | <=1.5 min | >1.5–3 min | >3–6 min | >6 min |

`*` Only where directly and reliably measurable. `NOT_MEASURED` is preferable to fabricated precision.

### G3 candidate/pass interpretation

A G3-positive recommendation requires:

```text
ALL correctness gates = perfect
AND
mechanical materialization >=65%
AND
cannot-materialize-without-invention <=10%
AND
no newly discovered fundamental contract hole
AND
review burden appears bounded/measurable where applicable
```

The accepted SLICE-0014 result is already `G3_CANDIDATE`; this slice determines whether the hardened evidence supports Stage-2 G3 passage.

## Critical distinction: contract gap vs retained-evidence gap

Do not conflate these:

### A. Contract/architecture failure

The accepted research/persistence contracts cannot faithfully represent a recurring retained fact class without invention or loss.

Examples:

- recurring applicability dimension has no representable form;
- recurring source/claim semantics cannot be retained without false classification;
- immutable identity model necessarily collapses distinct retained facts.

This may support `BLOCKED`.

### B. Insufficient retained fact

An old retained artifact simply lacks enough detail to classify or map a particular fact safely.

This is not by itself an architecture failure.

It should be classified as something like:

`INSUFFICIENT_RETAINED_FACT`

and should normally contribute to review/hardening metrics rather than automatically forcing `BLOCKED`.

## Required hardening item from SLICE-0014

Correct the latent recommendation/failure-class behavior so that:

- `CANNOT_MATERIALIZE` does **not** automatically mean `BLOCKED` for every exception;
- the failure is classified first;
- `BLOCKED` is reserved for a classified representational/contract insufficiency;
- ordinary validation/materialization/runtime defects drive `HARDEN_FIRST` unless they establish a contract gap;
- normal unknown/pre-canonical evidence never becomes `BLOCKED` merely because it remains unresolved.

Prefer explicit deterministic failure classes over exception-string inference.

## Required negative-path proof

Add bounded tests/fixtures that prove the benchmark harness fails honestly.

At minimum cover:

1. **Review-required retained fact**
   - cannot be converted safely without a human decision;
   - classified as review required;
   - not silently materialized with guessed semantics.

2. **Insufficient retained fact**
   - enough to identify the topic but not enough for faithful mapping;
   - classified `INSUFFICIENT_RETAINED_FACT` or equivalent;
   - does not automatically imply architecture `BLOCKED`.

3. **Validation/materialization defect**
   - invalid bundle/materialized object fails closed;
   - contributes to `HARDEN_FIRST` / failure metrics;
   - cannot be reported as success.

4. **True representational contract gap**
   - use the smallest synthetic benchmark-only fixture needed to prove the decision path;
   - must be explicitly synthetic;
   - must demonstrate that `BLOCKED` is reachable only for a classified contract insufficiency.

5. **Semantic readback mismatch**
   - deliberate mismatch must be detected by the canonical semantic comparator;
   - zero-mismatch result cannot be produced if persisted semantics differ.

6. **Idempotency/conflict failure**
   - exact re-import success criteria cannot be satisfied when immutable semantic content changes.

7. **SailboatData contamination guard**
   - existing zero-tolerance protection remains active;
   - no field values from SailboatData enter retained research/evidence fixtures.

Do not turn these fixtures into a generic production ingestion framework.

## Benchmark re-run

After hardening, re-run the exact accepted 50-design corpus through:

```text
materialization
→ accepted validation
→ PostgreSQL 18 import
→ semantic readback
→ exact re-import
→ fresh-schema rerun
→ result-schema validation
```

Do not change corpus membership to improve metrics.

Do not remove hard cases.

Do not add easy cases to dilute rates.

## Human-review measurement

The current retained benchmark produced zero review-required materialization cases.

Do not invent review-time estimates to populate the scorecard.

If this slice's real hardening/re-evaluation produces actual review-required cases and reviewer time can be directly observed, record it.

Otherwise retain `NOT_MEASURED` with a reason.

The scorecard explicitly permits unmeasured reviewer timing when the benchmark does not produce a valid timing sample.

## Throughput interpretation

Keep measured PostgreSQL execution timing as diagnostic evidence only.

Do not create an arbitrary boats-per-second G3 threshold.

At this stage the likely scale bottlenecks are research ambiguity, identity/applicability resolution and human review rather than PostgreSQL write throughput.

## Required output

Produce:

- hardened deterministic failure classification;
- focused negative-path tests;
- exact 50-case benchmark re-run;
- machine-readable benchmark result;
- concise G3 decision report;
- explicit comparison against every binding scorecard gate;
- explicit recommendation:

```text
G3_PASS
HARDEN_FIRST
BLOCKED
```

If the existing result schema currently uses `G3_CANDIDATE`, version/extend the benchmark/gate report cleanly rather than mutating historical retained artifacts ambiguously.

The final gate report must distinguish:

```text
measured fact
vs
interpretation
vs
gate decision
vs
next authorized action
```

## G3 decision semantics

### G3_PASS

Use only when:

- every zero-tolerance correctness gate is perfect;
- fixed minimum materialization/review thresholds are met;
- no recurring contract hole is exposed;
- failure classification is honest and deterministic;
- exact 50-case re-run remains reproducible;
- independent review finds no blocker;
- project owner explicitly accepts the slice.

A technical agent may recommend `G3_PASS`, but the slice is not `DONE` and G3 is not operationally passed until project-owner acceptance.

### HARDEN_FIRST

Use when correctness remains intact but one or more scale/review thresholds require improvement, or a repairable recurring implementation gap remains.

Examples:

- mechanical materialization <65%;
- review-required >35%;
- recurring but repairable mapping/validation gaps;
- negative-path classification not yet reliable.

### BLOCKED

Use when the accepted architecture/contracts cannot faithfully represent multiple recurring benchmark fact classes, or deterministic persistence correctness cannot be achieved without redesign.

Do not use `BLOCKED` for ordinary unknowns, sparse retained evidence or expected pre-canonical states.

## Explicitly out of scope

Do not implement:

- the 1,000-design bootstrap;
- new broad source discovery/acquisition;
- crawlers/bulk web ingestion;
- SailboatData extraction;
- fuzzy canonical identity resolution;
- automatic canonical BoatDesign creation;
- automatic FieldResolution;
- query engine / OQ-009 implementation;
- FastAPI/public API;
- Astro frontend;
- auth/accounts;
- marketplace/listing adapters;
- saved search/monitoring;
- price-history pipeline;
- SEO/public page implementation;
- Redis/message broker/search engine/Kubernetes/distributed workers;
- HullQ Design Watch implementation.

## Expected touch points

Prefer a minimal set:

- `scripts/benchmark/`;
- `tests/unit/` benchmark tests;
- `tests/persistence/` benchmark integration tests;
- `research/benchmark/persistence/` result/gate schema/report where needed;
- smallest CI adjustment required to retain G3 evidence;
- this slice completion report.

Do not change production domain/persistence contracts unless the negative-path evidence demonstrates a genuine accepted-contract defect. If it does, stop and report the defect rather than opportunistically redesigning the architecture inside this slice.

## Acceptance criteria

- [ ] pre-committed G3 thresholds are used unchanged;
- [ ] zero-tolerance correctness gates remain perfect;
- [ ] `CANNOT_MATERIALIZE` failure classes are deterministic and do not automatically imply `BLOCKED`;
- [ ] true contract insufficiency has an explicit reachable `BLOCKED` path;
- [ ] review-required and insufficient-retained-fact paths fail closed without invention;
- [ ] deliberate semantic mismatch is detected;
- [ ] deliberate immutable-content change cannot masquerade as idempotent success;
- [ ] SailboatData value contamination remains zero;
- [ ] exact 50-design corpus membership remains unchanged;
- [ ] real PostgreSQL 18 first import passes for all valid materialized bundles;
- [ ] exact re-import behavior is deterministic;
- [ ] fresh-schema semantic equality is reproducible;
- [ ] result/gate artifacts are retained and schema-validated;
- [ ] reviewer/cost timing is `NOT_MEASURED` where not directly observable;
- [ ] G3 report evaluates every binding scorecard metric explicitly;
- [ ] no broad ingestion/query/API/frontend/marketplace scope is introduced;
- [ ] Ubuntu/Windows quality, PostgreSQL integration, dependency audit, Ruff, format, strict mypy and coverage gates remain green;
- [ ] independent master review has no unresolved blocker;
- [ ] explicit project-owner acceptance occurs before `DONE` / operational G3 passage.

## Status handoff rule

SLICE-0015 is `READY` only because SLICE-0014 has explicit project-owner acceptance and PR #29 is merged as commit `71100b50052ed7c2910b096e36b8a5402f757191`.

Start it only through the normal isolated `START_SLICE.bat` workflow after the closure/readiness PR containing this contract is merged to `main`.

The implementation agent MAY set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark SLICE-0015 `DONE`.

`DONE` requires verified gates, independent review, an explicit gate recommendation and explicit project-owner acceptance.

The agent MUST NOT automatically begin the 1,000-design bootstrap or any later slice.
