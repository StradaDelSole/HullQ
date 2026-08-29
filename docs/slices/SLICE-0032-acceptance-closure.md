# SLICE-0032 — Acceptance Closure

**ID:** SLICE-0032  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Final independent-review verdict:** ACCEPT — implementation plus two bounded fail-closed amendment rounds reviewed; no blocking or material findings remain  

## Effective implementation state

SLICE-0032 was implemented and amended on PR #94:

- implementation PR: #94 — `SLICE-0032: sequential positive-control BoatDesign applicability pilot`;
- initial reviewed head: `03a5056a1e380a230a3682b594465882d95b3393`;
- first independent review: review `5052565060`, verdict **CHANGES REQUIRED**;
- first amendment head: `ac3188e540927e5baa4e98ca306fed5a7d0cb4c6`;
- second independent review: review `5058020519`, verdict **CHANGES REQUIRED**;
- final amendment head: `24b7b9f89f3263d8a062d5903049c1578a2f9dae`;
- final independent review: review `5058294233`, verdict **ACCEPT**;
- implementation merge commit: `bcf29441d8f6fa9d947ac9a759931bf40be303c2`;
- exact-head CI: run `33254744559`, SUCCESS;
- exact-head Manufacturer artifact reproducibility: run `33254744572`, SUCCESS.

The effective SLICE-0032 state for Project Owner acceptance is therefore main at merge commit `bcf29441d8f6fa9d947ac9a759931bf40be303c2`.

## Objective and result

SLICE-0032 executed the bounded, sequential, stop-on-first-positive BoatDesign applicability pilot over the fixed SLICE-0031 rank-1..3 candidates:

```text
rank 1  Q104861437  Buzzards Bay 14  BM_WDT0_003ba28d4cd143d68c28e57899a3ed73
rank 2  Q104829866  Suspens          BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb
rank 3  Q60521258   Hunter 340       BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60
```

Final retained candidate outcomes:

```text
rank 1  ATTEMPTED  APPLICABILITY_EVIDENCE_INSUFFICIENT  4 retrievals
rank 2  ATTEMPTED  RIGHTS_CLEARANCE_BLOCKED             2 retrievals
rank 3  ATTEMPTED  RIGHTS_CLEARANCE_BLOCKED             1 retrieval
```

Total retrievals: `7`.

Final top-level result:

```text
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

`successful_rank` is `null`.

This is a valid negative pilot result under the fixed contract. No rights, identity, generation, configuration, applicability or technical-value rule was weakened to force a positive result.

## Rank-1 evidence boundary

For Buzzards Bay 14, bounded manual use of the official current-builder source was cleared for the exact pilot `identity_seed` / `production_value` use under SR-6.6, while broader automated/bulk/redistribution uses remain non-allow unless separately cleared.

The official current-builder values do not safely establish that the retained Wikidata technical candidates apply to one bounded BoatDesign generation/configuration. The retained evidence therefore remains `APPLICABILITY_EVIDENCE_INSUFFICIENT`.

The open research observation remains that the Wikidata figures appear to correspond to the original wood design while the current builder publishes figures for its fiberglass adaptation. This observation does not create a canonical BoatDesign or canonical technical value.

## First amendment round

The first independent review found three blockers.

### 1. Rights-evidence truthfulness

The original retained rank-1 rights evidence contained false factual claims about the current builder site: it incorrectly described the page set and failed to record the visible copyright footer accurately.

The amendment re-checked the same retained source bytes and corrected the evidence to the actually observed facts. The bounded-manual SR-6.6 outcome remained unchanged, but the justification became truthful and auditable.

### 2. SLICE-0032 verifier absent from exact-head CI

The amendment added the dedicated offline SLICE-0032 verifier to the PostgreSQL 18 CI job immediately after the SLICE-0031 verifier.

### 3. Attempt status incorrectly modeled as candidate result

`NOT_ATTEMPTED_AFTER_SUCCESS` was removed from candidate-result vocabulary and represented as a separate attempt status.

The final contract is:

```text
CandidateOutcome:
- READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
- RIGHTS_CLEARANCE_BLOCKED
- APPLICABILITY_EVIDENCE_INSUFFICIENT

AttemptStatus:
- ATTEMPTED
- NOT_ATTEMPTED_AFTER_SUCCESS
```

An unattempted candidate has no candidate result, zero retrievals and no attempted-only rights/applicability evidence row.

## Second amendment round

The stricter re-review found three additional fail-closed verifier gaps.

### 1. Exact SR-6.6 condition set pinned in code

The final verifier independently requires exactly these six normative SR-6.6 condition identifiers, each exactly once:

```text
lawfully_publicly_accessible
reused_element_is_discrete_factual_value_not_expressive_content
provenance_recorded
no_identified_source_term_prohibits_the_chosen_method
not_systematic_or_bulk_database_extraction
no_automated_extraction_unless_separately_cleared
```

The fixed policy reference is:

```text
specs/SOURCE_RIGHTS_POLICY.v0.1.md#6.6
```

Missing, renamed, duplicate, extra or invented condition sets fail closed and cannot mechanically derive `allowed`.

### 2. READY requires the same applicability scope

A `SAFE_FOR_LATER_DESIGN_PROMOTION` field can contribute to READY only when its structured applicability scope is exactly the same bounded scope as the established BoatDesign applicability scope.

Two independently bounded but different scopes do not qualify. No fuzzy overlap, subset, merge or inferred compatibility semantics were introduced.

### 3. Attempted-only rows are unique and identity-pinned

For the attempted-only evidence documents, the verifier now:

- rejects duplicate candidate ranks;
- requires exactly one row for each attempted rank;
- requires zero rows for not-attempted ranks;
- pins `(candidate_rank, qid, hullq_id)` to the fixed candidate sequence;
- avoids silent dictionary overwrite of duplicate rows.

Positive-stop-path tests confirm that ranks after the first READY candidate carry zero retrievals and zero attempted-only evidence.

## Rights wording boundary

The final retained evidence uses observation-bounded wording for `robots.txt`: HTTP 404 at the standard path means no robots.txt restriction was observed there. It does not imply broad automated-ingestion permission.

`automated_ingestion`, `bulk_bootstrap` and `artifact_redistribution` remain non-allow unless separately cleared.

## Canonical mutation boundary

SLICE-0032 creates or mutates zero canonical:

- BoatModel;
- BoatDesign;
- DesignOption / NamedVariant;
- FieldResolution;
- canonical technical value.

The slice only retains bounded research, applicability classifications, source-rights evidence and deterministic verification artifacts.

## Retained package

The retained package is under:

`research/stage3/sl0032-positive-control-boatdesign-applicability/`

It contains the fixed candidates, corrected candidate evidence, retrieval log, source-clearance assessment, BoatDesign applicability findings, five-field applicability findings, result, schemas, report and digest manifest.

The offline verifier rebuilds the fixed SLICE-0028/0030/0031 predecessor state, verifies the fixed candidate sequence, re-derives corrected evidence, validates the SLICE-0032 contract and checks retained artifact digests.

## Validation evidence

Final implementation-agent validation reported:

- `--replay`: PASS;
- `--verify`: PASS;
- Ruff format/lint: PASS;
- mypy strict: PASS;
- full tests: **2,244 passed / 217 skipped**;
- repo-wide coverage: **90.99%** (>=90% gate);
- SLICE-0032 module coverage: **93.18%**;
- repository governance validator: PASS.

Independent exact-head remote verification on final head `24b7b9f89f3263d8a062d5903049c1578a2f9dae` confirmed:

- CI run `33254744559`: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - dependency audit: SUCCESS;
  - PostgreSQL 18 db integration: SUCCESS;
  - dedicated `Offline-verify SLICE-0032 retained sequential positive-control pilot package reproduces deterministically (no network)` step: SUCCESS;
- Manufacturer artifact reproducibility run `33254744572`: SUCCESS on Ubuntu and Windows.

## Independent adversarial review result

The final independent review explicitly covered:

- contract matrix against the controlling SLICE-0032 requirements;
- exact-head implementation and retained artifacts;
- adversarial verifier review;
- tamper/counterexample paths;
- fixed thresholds/identities/states;
- cross-document coherence;
- exact-head CI and Manufacturer reproducibility.

The key review question was applied directly: whether a false retained artifact could alter verification parameters or create a self-consistent false positive. After the two amendment rounds, no remaining blocking path was found within the SLICE-0032 contract.

## Audit trail

- controlling contract: `docs/slices/SLICE-0032-sequential-positive-control-boatdesign-applicability-pilot.md`;
- PR #94 initial head: `03a5056a1e380a230a3682b594465882d95b3393`;
- first independent review: `5052565060` — CHANGES REQUIRED;
- first amendment head: `ac3188e540927e5baa4e98ca306fed5a7d0cb4c6`;
- second independent review: `5058020519` — CHANGES REQUIRED;
- final amendment head: `24b7b9f89f3263d8a062d5903049c1578a2f9dae`;
- final independent review: `5058294233` — ACCEPT;
- final exact-head CI: `33254744559`, SUCCESS;
- final exact-head Manufacturer: `33254744572`, SUCCESS;
- implementation merge: `bcf29441d8f6fa9d947ac9a759931bf40be303c2`;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records independent acceptance of SLICE-0032. It does not itself mark the slice DONE and does not authorize SLICE-0033 or any other next implementation step.

Explicit Project Owner acceptance is required next. After Owner acceptance, SLICE-0032 may be treated DONE and cleaned up with the normal finish workflow. No next slice is auto-started.