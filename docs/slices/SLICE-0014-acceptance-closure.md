# SLICE-0014 — Acceptance Closure

**ID:** SLICE-0014  
**Final status:** DONE  
**Accepted:** 2026-08-21  
**Implementation PR:** #29  
**Accepted implementation head:** `98d2e38e42254bba17279945551d53c17b869f5e`  
**Merge commit:** `71100b50052ed7c2910b096e36b8a5402f757191`  
**Benchmark recommendation:** `G3_CANDIDATE`

## Acceptance result

SLICE-0014 is explicitly accepted by the project owner and closed as `DONE`.

The accepted slice proves that the retained 50-design stress corpus can be materialized into the accepted SLICE-0012 research semantics and persisted through the SLICE-0013 PostgreSQL path deterministically and losslessly at the benchmark boundary.

This is a **G3 candidate result**, not a declaration that Stage-2 Gate G3 has passed and not an authorization for the 1,000-design bootstrap.

## Final measured benchmark result

Exact accepted implementation head:

`98d2e38e42254bba17279945551d53c17b869f5e`

GitHub Actions CI run **#178** (`32457026920`) passed on that exact head.

Measured PostgreSQL benchmark result:

- total benchmark cases: **50**;
- materialized: **50/50**;
- review required during retained-fixture materialization: **0**;
- cannot materialize: **0**;
- first-pass imported: **50/50**;
- first-pass conflicts: **0**;
- first-pass errors: **0**;
- exact re-import `ALREADY_IMPORTED`: **50/50**;
- re-import conflicts/errors: **0**;
- semantic readback mismatches: **0**;
- fresh-schema imported: **50/50**;
- fresh-schema semantic mismatches: **0**;
- recommendation: **G3_CANDIDATE**.

Environment and CI evidence:

- PostgreSQL **18.6**;
- Python **3.14.7**;
- PostgreSQL persistence integration tests: **162 passed**;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- benchmark runner: PASS;
- benchmark result-schema validation: PASS;
- benchmark artifact upload: PASS;
- implementation-agent unit report: **987 passed**;
- reported coverage: **93.59%**.

Retained CI artifact:

- artifact ID: `9437591681`;
- name: `benchmark-outputs`;
- digest: `sha256:de4e6ec1e2b020b3758e5066441d3d068676bf298c0b1707c86b6b7098308f79`;
- contains `BENCHMARK-RESULT.json` and `BENCHMARK-REPORT.md`.

## What the benchmark now actually proves

The final accepted implementation verifies more than simple row persistence:

- retained field-/claim-level benchmark observations are materialized instead of flattened to one narrative blob per case;
- raw observations, normalized candidates, EvidenceType, ClaimSemantics and applicability remain distinct;
- unresolved findings and post-hoc reference crosschecks remain structurally separate;
- field identity is retained losslessly via `field_label:<field>`;
- `intended_field_pointer` is populated only through an explicit allowlist of true BoatDesign-v0.4 one-to-one canonical paths;
- unsupported or ambiguous fields retain `intended_field_pointer=None` rather than receiving guessed mappings;
- semantic roundtrip comparison covers the complete persisted `ResearchObservation` surface plus complete `UnresolvedFinding` and `ReferenceCrosscheck` semantics;
- exact re-import is idempotent;
- a genuinely fresh isolated PostgreSQL schema reproduces the same semantic outcomes;
- benchmark result/failure output is schema-validated;
- cost/reviewer timing is reported as `NOT_MEASURED` where not directly observable;
- SailboatData values do not enter HullQ evidence, fixtures or canonical candidate values.

## Review corrections incorporated before acceptance

The independent review cycle materially hardened the slice before acceptance:

1. **Real benchmark semantics** — replaced summary-level TEXT_FRAGMENT-only materialization with retained field-/claim-level observations.
2. **Fresh database proof** — changed the second run from an empty-data reuse to a fresh isolated schema with migrations applied from zero.
3. **Measured runner execution** — CI now executes the real benchmark runner against PostgreSQL 18 and retains machine-readable and human-readable artifacts.
4. **Fail-closed claim/evidence semantics** — unknown claim roles no longer default to nominal design values; source authority tier no longer implies manufacturer document type.
5. **Derived materialization metrics** — materialization/review counts come from actual conversion outcomes rather than predetermined constants.
6. **Full semantic comparator** — one reusable comparator is shared by runner and tests and covers complete persisted observation/finding/crosscheck semantics.
7. **Field identity retention** — original retained field names survive persistence even where no canonical field mapping exists.
8. **Evidence-type overclaim prevention** — generic terms such as `specification` / `tech spec` do not establish manufacturer authorship.
9. **Result/failure contract cleanup** — grouped failure classes, explicit `NOT_MEASURED` cost fields and reachable hardening/blocking outcomes are represented.
10. **Canonical pointer correction** — flat pointers such as `/loa` were replaced by real BoatDesign-v0.4 paths such as `/baseline/dimensions/loa_m`; non-1:1 mappings remain unset.

## Interpretation limits

The final `50/50` result must not be presented as a production research-automation rate.

The benchmark begins with **pre-curated retained HullQ research evidence**. It proves the deterministic materialization/persistence boundary for that corpus. It does not yet measure the full production path:

```text
unknown design
→ source discovery
→ rights/access check
→ acquisition
→ extraction
→ normalization
→ review
→ identity/canonical handling
→ persistence
```

Accordingly:

- `50/50 materialized` is strong evidence for the accepted research/persistence contracts;
- it is not evidence that 100% of the broader sailboat universe can be researched automatically;
- review minutes are not inferred from a benchmark that required no review decisions during fixture materialization;
- execution throughput is diagnostic and not a production SLO.

## Carry-forward hardening note

A non-blocking latent issue remains appropriate for SLICE-0015 hardening:

`CANNOT_MATERIALIZE` must not automatically imply `BLOCKED` for every implementation exception. `BLOCKED` is reserved for a classified recurring representational/contract insufficiency; ordinary validation/materialization failures should be classified and normally drive `HARDEN_FIRST` unless they prove the accepted contracts cannot represent retained reality.

This did not affect the accepted SLICE-0014 result because `cannot_materialize=0`.

## Next boundary

The next bounded step is:

`SLICE-0015 — Benchmark Hardening and Stage-2 Gate G3`

SLICE-0015 must use the pre-committed G3 scorecard and must not move thresholds after seeing results.

It may harden failure classification, negative-path proof and gate evidence. It must not begin broad production ingestion, the 1,000-design bootstrap, query/API/frontend work or new unbounded web acquisition.
