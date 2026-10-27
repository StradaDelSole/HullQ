# SLICE-0092 — Owner Acceptance Closure

**Status:** OWNER_ACCEPTED — IMPLEMENTATION; Owner-local FINISH pending  
**Capability:** Qualified technical Sail discovery for ACTIVE design-unresolved broker listings, with typed `PUBLISHER_CLAIM` provenance and current D29 eligibility  
**Controlling READY contract:** `docs/slices/SLICE-0092-qualified-design-unresolved-search.md` (docs-only READY PR #386)  
**Implementation PR:** [#387](https://github.com/StradaDelSole/HullQ/pull/387)  
**Independently reviewed and Owner-accepted exact implementation HEAD:** `441d6ec27b9a284321a946fa3cc4e348f77f1035`  
**Implementation squash merge on main:** `c2425232967a8223b64b3a677cbad2c83c2e2336`  
**Owner acceptance:** Explicit “akzeptiert” on 2026-10-27 (Europe/Vienna), after independent exact-HEAD review and remote six-job CI/manufacturer reproducibility verified SUCCESS. Implementation merge followed Owner approval.  
**Prerequisite:** Owner-accepted, locally FINISHED SLICE-0091 (category foundation), SLICE-0090 architecture §4 row B.  
**Future blockers remain:** [#355](https://github.com/StradaDelSole/HullQ/issues/355) pre-real-data upload/pilot and CR-05 scaled Search; [#366](https://github.com/StradaDelSole/HullQ/issues/366) joint Sail+Power external release; [#372](https://github.com/StradaDelSole/HullQ/issues/372) future Power specialist criteria and parity; [#363](https://github.com/StradaDelSole/HullQ/issues/363) local one-click browser follow-up.

## Accepted one-capability product result

SLICE-0092 adds a distinct, qualified **design-unresolved** (`PhysicalBoat.boat_design_ref IS NULL`) **ACTIVE** NativeListing candidate path alongside, not in place of, accepted design-linked Sail Search:

1. `src/hullq/persistence/inventory_search.py` supplies the separate, additive design-unresolved enumeration. The accepted design-linked candidate SQL and nine hard Sail dimensions remain unchanged.
2. `src/hullq/search/configuration_engine.py` factors a common projection/leaf-MUST/AND evaluator reused by the existing `evaluate_configuration` and the new claim-only path. No fake BoatDesign/ConfigurationIdentity, independent scorer, or invented manufacturer/design verification.
3. `src/hullq/application/native_inventory_query.py` qualifies each new candidate from **the publishing Organization's own current authenticated revision**, containing a positive `VALUE_ASSERTION(SAIL)` category and all selected current typed technical claims. Current conflicting other-Organization facts, insufficient/unknown category, retracted/missing/unsupported fields, and POWER/MOTORSAILER/CONFLICT do not yield confirmed Sail matches. Category and technical assertions use one coherent PostgreSQL claim-observation snapshot. Pure `draft_max` and mixed nine-criterion paths reuse the same implementation.
4. `PublisherClaimCandidateEvaluation` includes typed `source_basis=PUBLISHER_CLAIM` and internal `PublisherClaimSourceEvidence` with claiming revision ID, current author/account, timestamp and publisher category assertion. Authorized internal auditing retains these facts; the public DTO never exposes competing Organizations' or private accounts' revision details.
5. FastAPI Search returns separate `publisher_claim_matches` / count alongside existing design-linked matches, with discovery tokens, freshness and criterion evidence but **without `design_evaluation`**. Astro Search renders the clear, distinct broker-source section and disclaimer in all five current locales (en/de/fr/pt/es), with actual listing links and without suggesting independently verified design facts.
6. The `search_sensitivity.py` current/alternative/newly/no-longer claim-only comparison is kept **separate** from unchanged design-linked counts, shown truthfully on public API and Astro sensitivity UI. The zero-design-plus-one-claim-only state does not falsely say there are no matches.
7. Current-public D29/freshness remains mandatory. `resolve_current_public_eligibility_for_many` first fetches inexpensive candidate facts in batched SQL statements and evaluates obvious suppressions fail-closed. For surviving candidates it gathers the full unchanged offer/claim/cover facts and delegates to the **same** pure `evaluate_current_public_eligibility` rule as the legacy single-id resolver. Claim observations are read in one batched PostgreSQL statement. The legacy single-id D29 and existing design-linked search caller code are unchanged.
8. The narrowly targeted lock update changes `msgpack==1.2.1` to `msgpack==1.2.4`, resolving the dependency-audit report of `CVE-2026-114613` without suppression.

No Power technical search, motorsailer cross-domain matching, new criterion, external importer, owner-direct self-attestation admission, external broker data or pilot was implemented. The accepted **nine** Sail technical criteria remain exactly nine.

## Independent review trail / amendments

| Independently reviewed exact HEAD | Findings / decision |
|---|---|
| `5ce856accdf4fb8a880779b33af12524ff1c8e48` | A: sensitivity excluded broker-claim family; B: insufficient multi-leaf/negative PG proof; C: typed revision/issuer evidence missing from internal result; D: unbounded linear N+1 candidate cost. |
| `efa0f1e2bcf7c8a733110556fa7c1003746ec890` | A–C closed. Batched claim observations partly improved D, but 523 statements for 40 candidates remained. E: exact-HEAD dependency audit exposed `msgpack 1.2.1` CVE requiring a secure lockfile update. |
| `441d6ec27b9a284321a946fa3cc4e348f77f1035` | A–C and E closed. D accepted for **synthetic internal slice only** after batched D29/freshness + claim observation, measured scaling and equivalence tests. Residual production-scale risk explicitly retained in #355 (no external data/pilot GO). Independent review: READY FOR OWNER ACCEPTANCE. |

**Verified technical/adversarial proof:** Actual persisted PostgreSQL 18 tests of TRUE/TRUE, TRUE/FALSE, FALSE/UNKNOWN and TRUE/UNKNOWN multi-criterion MUST/AND outcomes; correct/wrong/omitted field assertions for all nine accepted Sail criteria; D29 suppressed Organization; current publisher category ownership and cross-Organization conflicts; concurrent two-connection current revision change; exact internal provenance and absence of private fields from public payload. Retained inspector `scripts/inspect_slice_0092_claim_only_search.py` drives real PostgreSQL+FastAPI+built Astro SSR via HTTP in six scenarios, including zero design matches plus a claim-only match. No claim of browser automation with JavaScript execution is made.

**D29 and performance evidence:** `tests/persistence/test_current_public_eligibility_for_many_slice_0092.py` compares new bulk vs. existing single-id status on valid real persisted scenarios and proven reachable suppression axes; some bulk suppression-reason sets are intentionally subsets but never elevate suppressed listings into ELIGIBLE, and the claim-only Search consumes **status**, not partial suppression-reason sets. Synthetic local PostgreSQL measurements:

| ACTIVE design-unresolved candidate count | Total SQL statements (one complete Search) | Local elapsed |
|---:|---:|---:|
| 0 | 2 | 0.001s |
| 40 | 169 | 0.091s |
| 200 | 809 | 0.389s |

Claim-observation and inexpensive D29 reads are batched, but **the full search still has O(N) per-survivor offer/media reads and unbounded ACTIVE enumeration**. These measurements are local synthetic evidence, not hosted Neon/production SLA, load test, max-result guarantee, or pilot readiness. The residual production Search batching, workload limits, paging, timeout/proxy/rate-limit behavior, hosted throughput and realistic large-population plan/index work are explicitly tracked under **issue #355, CR-05**. That issue remains OPEN and an external-data/pilot STOP. No additional production readiness claim is authorized by acceptance of this slice.

## Exact accepted-HEAD remote verification

| Gate | Exact-HEAD result |
|---|---|
| [CI run 40558375210](https://github.com/StradaDelSole/HullQ/actions/runs/40558375210) | **SUCCESS, all six**: Ubuntu and Windows Quality, PostgreSQL-18 DB Integration, Historical PostgreSQL Replay, Astro/Node Web Quality, Dependency Audit |
| [Manufacturer artifact reproducibility run 40558375215](https://github.com/StradaDelSole/HullQ/actions/runs/40558375215) | **SUCCESS** |
| [Deploy workflow run 40558375223](https://github.com/StradaDelSole/HullQ/actions/runs/40558375223) | **SUCCESS as a workflow check**, **not evidence of actual production deployment** |

The implementation agent reported local `uv run mypy src` (186 files), Ruff lint/format, repository governance validator, focused PG18 D29 equivalence and Search/sensitivity suites, `uv sync --locked --all-groups`, `uv run pip-audit` and the six-step real PG/FastAPI/Astro SSR inspector PASS. These are implementation-agent-executed local checks; the independent reviewer verified source, tests and remote exact-HEAD evidence and did **not** claim a separate local replay.

## Scope and governance reconciliation

- **DECIDED_AND_IMPLEMENTED:** Qualified first-party publishing-Organization current-claim Sail match for ACTIVE design-unresolved PhysicalBoat; current source/revision evidence and protected public truth label; both existing Sail Direct Search funnels and Buyer sensitivity parity; shared criterion evaluator; D29/broker/freshness controls; additive batched read path; isolated security dependency fix.
- **DECIDED_NOT_YET_IMPLEMENTED:** Full native Power technical search/Buyer and Broker parity, unresolved design technical search-fit for DRAFT broker listings, Motorsailer dual-domain policy, new conditional Power equipment/operating-point source-qualified facts, and Power NautiX import/export under #372.
- **EXPLICITLY_DEFERRED / STOP:** Production data / broker uploads, third-party source rights, professional hosted-scale Search optimization/limits and parallel request abuse handling #355, joint Sail+Power external pilot/launch #366, production providers/retention/support/onboarding, Launch Pack, owner-direct trust, buyer alerts, #363 local browser workflow. No external source ingestion permissions inferred.
- **Production readiness:** `IN_PROGRESS`. **Launch Pack:** `NOT_STARTED`. **Real external broker production data:** `NOT_PRESENT`. **Production pilot / public launch:** `NOT_STARTED`.

## Canonical state / Owner-local FINISH

```text
PROJECT_STATE_ACCEPTED_SLICE: 0092
PROJECT_STATE_QUEUE_SLICE: 0093 — NOT SELECTED / NOT READY
SLICE_0092_TYPE: IMPLEMENTATION
SLICE_0092_RESULT: OWNER_ACCEPTED_QUALIFIED_DESIGN_UNRESOLVED_SEARCH
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

This is a separate **docs-only Owner acceptance closure**, not another implementation slice. It requires independent exact-HEAD docs review, its **own** all-six-job GitHub CI and manufacturer reproducibility plus Deploy workflow success, and squash merge to `main`. Only after the closure is independently verified and merged does the Owner run the unchanged local `FINISH_SLICE.bat`, selecting `0092`. This document must not claim local FINISH success beforehand. No SLICE-0093 implementation may auto-start.
