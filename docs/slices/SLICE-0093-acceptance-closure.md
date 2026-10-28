# SLICE-0093 — Owner Acceptance Closure

**Status:** OWNER_ACCEPTED — IMPLEMENTATION; Owner-local FINISH pending  
**Type:** IMPLEMENTATION  
**Capability:** First category-isolated, source-qualified Power hard technical Search dimension — current principal drive arrangement  
**Controlling READY:** docs/slices/SLICE-0093-power-drive-configuration-ready.md (merged READY PR #389)  
**Normative contract:** specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md  
**Implementation PR:** [#390](https://github.com/StradaDelSole/HullQ/pull/390)  
**Independent review and Owner-accepted exact HEAD:** 4b9060e7fce7ebb7a7893c87890571210f94d825  
**Implementation squash merge on main:** c38a60d821a6e9a88fba023a0008a36a3dcd51e1  
**Owner acceptance:** Explicit “akzeptiert” on 2026-10-28 (Europe/Vienna), after exact-HEAD independent reviewer disposition [OWNER ACCEPTANCE READY](https://github.com/StradaDelSole/HullQ/pull/390#pullrequestreview-5680875357), recorded in the [PR conversation](https://github.com/StradaDelSole/HullQ/pull/390#issuecomment-6466143231); implementation merge followed that approval.  
**Previous accepted baseline:** SLICE-0092 Owner-accepted and Owner-local FINISH SUCCESS; SLICE-0091 qualified VesselCategory foundation; SLICE-0090 accepted source-rights architecture.  
**Next slice:** NOT SELECTED; do not start automatically.  
**Unchanged hard STOPs:** [#355](https://github.com/StradaDelSole/HullQ/issues/355) real external upload/pilot, runtime and CR-05 Search scale; [#366](https://github.com/StradaDelSole/HullQ/issues/366) joint Sail+Power product release; [#372](https://github.com/StradaDelSole/HullQ/issues/372) remaining Power specialist dimensions, corpus, source rights and broker/buyer parity.

## Accepted one-capability result

SLICE-0093 implements the first Power-domain source-qualified native technical criterion, current propulsion **drive arrangement**, using exactly the public five-token whitelist **SHAFT, STERNDRIVE, POD, WATERJET, OUTBOARD**. It is Power ordinal 1 and global accepted technical ordinal **10** (nine Sail + one Power). No additional Power engine/fuel, speed/range/consumption, second criterion, external importer/exporter or production release was authorized.

1. One optional typed PhysicalBoat drive assertion participates in the existing publishing Organization's immutable current claim revision, current actor/authorization and broker editor form. A broker's unrelated save preserves the drive; stale, invalid, foreign-Organization and unauthorized edits cannot mutate it. The public Search claim source is explicitly PUBLISHER_CLAIM, never independent inspection.
2. Power Search uses its own exact /api/search/{locale}/power endpoint and five internal, noindex Astro SSR /{locale}/power/search routes (en/de/fr/pt/es). The original Sail request/DTO/route and all nine Sail criteria remain unchanged. The buyer receives separate design-linked versus design-unresolved publisher-claim match sections, criterion evidence, current-public eligibility and source limitations.
3. The first new Power CriterionDefinition reuses the accepted categorical leaf, projection, configuration, current-claim qualification and MUST/AND evaluation kernel. Neither a new independent Power scorer nor an inferred category/drive mapping was added.
4. Positive publisher admission requires both the publishing Organization's **own current VALUE_ASSERTION(POWER)** category and its own **specific current drive assertion in the same current revision**. Another Organization or design-level category assertion cannot substitute for the publisher's claim. Contradictory category or drive observations fail closed. The design-linked path uses a **single PostgreSQL MVCC snapshot** for design category, all current Organization categories and current drive evidence; it cannot splice category and drive from different concurrent revisions.
5. Genuine BoatDesign v0.6 FieldResolution/NamedVariant evidence can only map qualified factory **shaft → SHAFT** and **outboard → OUTBOARD**. The unsupported factory vocabulary other, unknown and saildrive is not promoted to POD, WATERJET or STERNDRIVE. Current publisher installation/refit truth remains separate from factory design facts; unsupported/missing source is nonconfirmed.
6. Single-drive MIXED/UNKNOWN/OTHER cases and disagreements do not produce false positive Power matches or inappropriate proven exclusion. Publisher MIXED is insufficient as one exact drive; other-current-Organization MIXED remains visible to conflict qualification. No Power-positive for SAIL/MOTORSAILER/UNKNOWN/CONFLICT category.
7. The existing Sail-only NautiX exporter now fails closed on known POWER, MOTORSAILER or conflicting source-resolved category instead of incorrectly emitting sail-yacht, preserving admitted ordinary Sail and legacy-unknown compatibility. This is **not** Power-format import/export support.
8. Power SSR/API enforces strict response/request agreement. BASE is exactly locale plus null active_requirement, with **no result-surface extras**; RESULT has well-typed nested evidence, arrays and safe nonnegative integer counts. A malformed/truncated, wrong-locale, wrong-token, duplicate/invalid/unknown-query HTTP-200 is a 502 recovery/error condition, **not** an invented empty valid Search result. Genuine BASE and genuine empty RESULT remain valid.

## Independent exact-HEAD review trail

| Review HEAD | Material findings and disposition |
|---|---|
| e2b25e253975aa7ff419d1c895cd8b7a76aee527 | A: MIXED negative classification, B: unsafe NautiX source-category gate, C: retained PG/FastAPI/built-SSR broker inspector missing, D: concurrency and scale evidence, E: HTTP 200 silent malformed-body acceptance, F: Ruff formatting remote CI failure. REVIEW. |
| e74fc90a809ad44aa93bd2c66f39faa334bd6d6a | A/B/F closed; G: design-linked multi-statement category/drive MVCC tear, H: other-Org MIXED hidden, I: inspector PASS not aggregating prefill step, J: response validator too lenient, K: missing query plan evidence. REVIEW. |
| daff0f6f9965753a288bfe93ba27456eb4823975 | G/H/I/K closed; final J narrowed to BASE extra-field, noninteger RESULT counts and ambiguous request query. REVIEW. |
| **4b9060e7fce7ebb7a7893c87890571210f94d825** | **Final J closed**. Independently identified design-linked publisher category-ownership gap closed through common admission precondition and four new real-PG regression cases. Independent exact-HEAD review: [OWNER ACCEPTANCE READY](https://github.com/StradaDelSole/HullQ/pull/390#pullrequestreview-5680875357), followed by explicit Owner acceptance. |

**Adversarial evidence:** Real PostgreSQL 18 tests for publisher ownership, category absent/retracted/other-Organization-only, positive own-category+drive current revision, two-connection revision change, D29/freshness and search exclusions; cross-Org MIXED; exact design evidence vs current installation; genuine NautiX preflight and admitted Sail fallback. A retained [17-step inspector](../../scripts/inspect_slice_0093_power_drive_search.py) exercises real PG18 + FastAPI + built Astro SSR via authorized OIDC cookie-jar HTTP, editor save/readback/unrelated edit/invalid/stale/foreign failures, real buyer HTML/labels and five locales/noindex. Agent reported PASS; reviewer inspected assertions but **did not independently execute the local inspector**. It is **not browser JavaScript automation**.

**Reported local validation for final amendment:** focused persistence Power query 29 passed; aggregate Power domain 72 passed; Node web test run 581 passed, zero failures; Astro check zero errors; full-tree Ruff format/check clean; mypy clean; repository validator PASS. These figures are implementation-agent reports unless independently covered by the remote CI below.

## Verified exact-HEAD remote gates

| Gate | Verified outcome for 4b9060e7fce7ebb7a7893c87890571210f94d825 |
|---|---|
| [Full CI run 40665966345](https://github.com/StradaDelSole/HullQ/actions/runs/40665966345) | **SUCCESS — all six**: Ubuntu Quality, Windows Quality, PostgreSQL18 Integration, Historical Replay, Web Quality, Dependency Audit |
| [Manufacturer reproducibility run 40665966269](https://github.com/StradaDelSole/HullQ/actions/runs/40665966269) | **SUCCESS — Ubuntu and Windows** |
| [Deploy workflow run 40665966265](https://github.com/StradaDelSole/HullQ/actions/runs/40665966265) | **SUCCESS for applicable namespace/build checks; GHCR pushes and production deployment SKIPPED**. Not a production rollout. |

**Synthetic performance evidence:** Full claim-only Power Search with 0/40/200 synthetic ACTIVE candidates measured **2/169/809 SQL statements**, respectively; design-linked 0/10 measured **2/98 statements**. PostgreSQL18 EXPLAIN (ANALYZE, BUFFERS) evidence exists for batched claim reads and coherent design-linked category/drive snapshot. These are internal synthetic observations, not hosted Neon-scale throughput, bounded result enumeration, or production SLAs. **O(N) Search amplification remains**, with pre-external-data/pilot CR-05 gating under #355.

## Decision / implementation and remaining gates

**DECIDED_AND_IMPLEMENTED:** One Power drive hard criterion with accepted current publisher category/drive qualification, five-token parser and five locale Power buyer routes, broker claim/editor, distinct source evidence, shared categorical evaluator, bounded genuine v0.6 design bridge, D29, strict HTTP error discipline, Sail-safe NautiX guard and unchanged nine Sail criteria.

**DECIDED_NOT_YET_IMPLEMENTED:** Further Power specialist technical dimensions and operational-point conditions, complete Power model corpus/variant rights, Power broker Search-fit and buyer/broker parity, broader category-correct Power NautiX export/import, other owner-direct and marketplace readiness obligations (#372).

**EXPLICITLY_DEFERRED:** New BoatDesign v0.7 source schema and unmapped factory drive vocabulary, external unlicensed model or listing imports, production provider procurement, real external inventory, production pilot/indexation, generic dual-domain browse, XLSB export (#362).

**GENUINELY_OPEN:** Future Motorsailer cross-domain rules and source-rights-qualified new Power taxonomy/corpus; no automatic choice made by this closure.

**CONFLICT_OR_REGRESSION:** Review findings A–K and publisher category ownership were reconciled and closed for the exact accepted HEAD; **no permission** to relax current-claim truth, Sail isolation, commercial-neutral organic matching or pre-pilot gates.

**Production Readiness:** IN_PROGRESS. **Production Launch Pack:** NOT_STARTED. **External broker/owner-direct production data:** NOT_PRESENT. **External pilot/public production launch:** NOT_STARTED. Joint Sail+Power release #366 still OPEN. The acceptance of one Power dimension is **not** Power/Sail product parity or launch readiness.

## Canonical closure / Owner-local FINISH boundary

PROJECT_STATE_ACCEPTED_SLICE: **0093**  
PROJECT_STATE_QUEUE_SLICE: **0094 — NOT SELECTED / NOT READY**  
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: **10 — Sail 9 / Power 1**  
PRODUCTION_READINESS_GATE_STATUS: **IN_PROGRESS**  
PRODUCTION_LAUNCH_PACK_PHASE: **NOT_STARTED**

This separately reviewed **docs-only Owner acceptance closure** advances the canonical marker and criterion count **only after** the Owner-accepted implementation has been merged. Closure requires its own exact-HEAD independent review, all-six GitHub CI, Manufacturer reproducibility and applicable Deploy workflow verification, followed by squash merge. **Only after the closure merges** does the Project Owner run the unchanged local FINISH_SLICE.bat with slice number **0093**. This document does not claim local FINISH success in advance. No future slice is selected automatically.
