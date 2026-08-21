# SLICE-0015 — Acceptance Closure

**ID:** SLICE-0015  
**Final status:** DONE  
**Accepted:** 2026-08-21  
**Implementation PR:** #31  
**Accepted implementation head:** `022bec43318025bdeb92608bb2fb0445650f081d`  
**Merge commit:** `d87490c6103676935768ba57ed41e665225731b8`  
**Stage-2 Gate G3 recommendation:** `G3_PASS`

## Acceptance result

SLICE-0015 is explicitly accepted by the project owner and closed as `DONE`.

The accepted slice hardens the retained 50-design benchmark failure paths, applies the fixed pre-committed Stage-2 G3 scorecard, and produces a technical `G3_PASS` with no remaining independent-review blocker.

Stage 2 Gate G3 is therefore passed. This authorizes preparation of the next bounded Stage-3 slice; it does **not** by itself authorize unbounded broad ingestion, query/API/frontend work, or automatic expansion beyond the next accepted slice contract.

## Final accepted evidence

Exact accepted implementation head:

`022bec43318025bdeb92608bb2fb0445650f081d`

GitHub Actions CI run **#189** (`32468991110`) passed on that exact head.

Verified CI jobs:

- PostgreSQL 18 database integration: PASS;
- benchmark runner: PASS;
- benchmark result-schema validation: PASS;
- benchmark artifact upload: PASS;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS.

Retained benchmark artifact:

- artifact ID: `9441784787`;
- name: `benchmark-outputs`;
- digest: `sha256:5f7048b86d2590509e764356283631c960c91988d2961d14e0d270e17b9ed588`;
- exact head: `022bec43318025bdeb92608bb2fb0445650f081d`.

Implementation-agent final local report before acceptance:

- full suite: **1277 passed, 164 skipped**;
- repository validator: PASS;
- Ruff check / format check: CLEAN;
- strict mypy on the touched gate code: CLEAN;
- coverage: **93.66%**.

## Final benchmark / G3 result

The accepted real benchmark remained unchanged and clean:

- total benchmark cases: **50**;
- materialized: **50/50**;
- first-pass imported: **50/50**;
- first-pass conflicts/errors: **0**;
- semantic readback mismatches: **0**;
- exact re-import `ALREADY_IMPORTED`: **50/50**;
- re-import conflicts/errors: **0**;
- fresh-schema imported: **50/50**;
- fresh-schema semantic mismatches/errors: **0**;
- recommendation: **G3_PASS**.

Binding thresholds remained pre-committed and unchanged:

- mechanical materialization: `>=65%`;
- cannot-materialize-without-invention: `<=10%`;
- review-required: `<=35%`.

Binding failure-class semantics are:

- `CONTRACT_GAP` → `BLOCKED`;
- `VALIDATION_FAILURE` → `HARDEN_FIRST` regardless of percentage;
- `INSUFFICIENT_RETAINED_FACT` → rate-based and may remain G3-positive within the `<=10%` cannot-materialize threshold.

## What SLICE-0015 added

The accepted slice materially strengthened the benchmark before Stage-3 scaling:

1. `CANNOT_MATERIALIZE` is classified before gate recommendation rather than automatically implying architecture `BLOCKED`.
2. Negative-path tests prove review-required, insufficient-retained-fact, validation-failure, true contract-gap, semantic-mismatch, idempotency/conflict, and SailboatData-contamination behavior.
3. The gate applies the fixed scale thresholds and zero-tolerance correctness metrics through one shared decision function.
4. Any unresolved `VALIDATION_FAILURE` forces `HARDEN_FIRST`, while sparse retained evidence remains rate-based.
5. Fresh-database semantic equality requires both complete fresh import of materialized bundles and zero semantic mismatches.
6. Unexpected persistence errors include first-pass, re-import and fresh-run failures.
7. The machine-readable scorecard distinguishes direct runtime evidence, verified structural invariants and genuinely unmeasured metrics.
8. Human-readable reporting is data-driven and remains truthful for legitimate partial-materialization `G3_PASS` states as well as the current 50/50 result.
9. Project-owner acceptance remains distinct from the technical `G3_PASS` recommendation.

## Interpretation limits carried forward

G3 passage proves the accepted benchmark/research/persistence boundary is sufficiently hardened to begin controlled Stage-3 work. It does not prove that unknown-design discovery, identity admission or broad production research will achieve the same 50/50 automation result.

In particular, the accepted PostgreSQL schema from SLICE-0013 persists `ResearchEvidenceBundle`, `ResearchObservation` and `FieldEvidence`; it intentionally does **not** yet provide canonical `BoatModel` / `BoatDesign` entity persistence. The accepted identity runtime is likewise a pure contract/runtime boundary and explicitly contains no persistence or network resolution.

That distinction must remain visible before the first broad identity bootstrap.

## Next boundary

The next bounded step is:

`SLICE-0016 — Stage-3 Canonical Identity Persistence & Bootstrap Admission Contract`

SLICE-0016 must close the missing canonical identity persistence/admission boundary before HullQ executes a controlled ~1,000-design canonical bootstrap.

It must preserve accepted Brand / Organization / BoatModel / BoatDesign identity semantics, stable opaque HullQ IDs, explicit ambiguity/review behavior, provenance, and fail-closed no-fuzzy/no-invention rules.

The controlled ~1,000-design bootstrap remains the immediate Stage-3 milestone after this prerequisite boundary is accepted; it is not executed merely by closing SLICE-0015.