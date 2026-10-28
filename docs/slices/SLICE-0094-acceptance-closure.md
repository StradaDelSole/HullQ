# SLICE-0094 — Owner Acceptance Closure

**Status:** OWNER_ACCEPTED — IMPLEMENTATION; formal docs-only closure record; Owner-local FINISH pending  
**Type:** IMPLEMENTATION  
**Capability:** Current installed principal propulsion engine count and genuine Power drive + count MUST/AND technical Search  
**Controlling READY:** `docs/slices/SLICE-0094-power-engine-count-ready.md` (independently reviewed and previously merged READY PR #392)  
**Normative contract:** `specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md`  
**Implementation PR:** [#393](https://github.com/StradaDelSole/HullQ/pull/393) — **MERGED**  
**Independent review and Owner-accepted exact implementation HEAD:** `76f542635d3d04ae9e8c4c05c8a704912f0ba3d4`  
**Implementation squash merge on main:** `9ac9705825bcc3bdab83a85c74f011eaf285d67a`  
**Owner acceptance:** Explicit “akzeptiert” on 2026-10-28 (Europe/Vienna), following independent exact-HEAD [READY FOR OWNER ACCEPTANCE review](https://github.com/StradaDelSole/HullQ/pull/393#pullrequestreview-5688152084). Squash merge followed Owner approval.  
**Previous accepted state:** SLICE-0093 Owner-accepted and Owner-local FINISH SUCCESS; first Power criterion `power_drive`; original nine Sail criteria unchanged.  
**Next slice:** NOT SELECTED; no implementation or START authorized automatically.  
**Hard STOPs unchanged:** [#355](https://github.com/StradaDelSole/HullQ/issues/355) pre-external-data/pilot Search scale; [#366](https://github.com/StradaDelSole/HullQ/issues/366) joint Sail+Power external release; [#372](https://github.com/StradaDelSole/HullQ/issues/372) further Power specialist/broker parity, source rights and corpus.

## One accepted, buyer-visible capability

SLICE-0094 adds **one** native Power hard technical criterion, exact count of **currently installed principal propulsion engines**, with selectable public tokens **1–8**, even though the publisher's typed current claim can faithfully persist values **1–32**. Buyers can search `power_engine_count` alone or combine it with the previously accepted `power_drive` five-token criterion under a **single true MUST/AND** query. The global accepted hard technical Search dimensions therefore advance **10 → 11** in this separate acceptance closure: **Sail 9 / Power 2**.

1. **Authoritative PhysicalBoat truth:** Optional `power_engine_count` belongs to the publishing Organization's existing immutable claim revision and is read/edited via the authorized broker listing editor. Omitted, UNKNOWN and VALUE_ASSERTION remain distinct. Unrelated edits preserve prior claims; current revision, actor/Organization ownership, type/bounds, retry and historical replay are guarded. A raw factory/design value cannot become current installed count by inference.
2. **Query semantics:** Power's second typed static `CriterionDefinition` reuses shared numeric RANGE(min=max) evaluation and the existing drive categorical criterion in the same `MixedAndQuery` and configuration/MUST-AND engine. A positive combined result requires **both leaves TRUE on one resolved design configuration** where design-linked, and **both current publisher-owned installed assertions from a coherent revision**. There is no union of independently matching variants and no copied separate Power scorer. Count-only does not require a drive assertion.
3. **Source qualification:** Qualified BoatDesign v0.6 `/baseline/propulsion/engine_count` and NamedVariant `/overrides/propulsion/engine_count` each require their own genuine FieldResolution to establish factory configuration facts, separate from an eligible current PhysicalBoat claim. Unsupported zero/null/unresolved/stale data fail closed; a current refit is not assumed equivalent to factory configuration. A real baseline and variant cannot be spliced into a fictitious matching configuration.
4. **Category, Organization, D29 and MVCC:** No Power positive without the publishing Organization's own explicit current POWER category and claimed requested technical facts. Cross-Organization contradiction, missing/retracted category, category SAIL/MOTORSAILER/CONFLICT, stale/unknown sources, or torn concurrent category+drive+count snapshots cannot create false positives. The design-linked category and physical claim observation is coherently snapshot-read, and design-unresolved claims remain separately labelled `PUBLISHER_CLAIM`.
5. **Buyer transport and browser:** `/api/search/{locale}/power` and `/{locale}/power/search` for en/de/fr/pt/es accept sparse count-only, drive-only, or combined exact values; canonical order is drive then count; absent form filters are **omitted** from GET rather than submitted as blank values. Strict 400/308/502, genuine empty RESULT vs transport error, noindex, D29 eligibility, real listing discovery token and escaped evidence remain intact. The buyer sees per-criterion requested condition, truth, source label, reason if non-null, and explanation for both design-qualified and publisher-asserted paths. Malformed or contradictory positive-match DTO leaves/configuration/truth/identity yield 502, never an invented match.
6. **Isolation:** Existing Sail nine hard dimensions, Sail API and sensitivity, SLICE-0093 Power drive-only behavior, the Sail-only NautiX guard, organic non-commercial match neutrality, and production/provider controls remain unchanged. The new criterion is not a production release or full Power broker parity.

## Independent exact-HEAD implementation review trail

| Independently reviewed HEAD | Decision / material findings |
|---|---|
| `647cf1fc529df9cda442d00dda88ea694d50589d` | A: form submitted omitted empty keys; B: no genuine cross-variant negative; C: missing 0/40/200 combined PG proof; D: per-leaf buyer evidence not rendered; E: factory zero wrongly qualified; F: wire evidence semantic shape too broad. [Review](https://github.com/StradaDelSole/HullQ/pull/393#pullrequestreview-5684260607): REVIEW. |
| `b2fa485c5d2e060fd7f09a78f6dfc24909ee6eb9` | A/B/E closed; C2: same mixed-population search-shape benchmark incomplete; D2: live SSR results/evidence proof and reason code missing; F2: absent/duplicate/contradictory evidence accepted. [Review](https://github.com/StradaDelSole/HullQ/pull/393#pullrequestreview-5686072394): REVIEW. |
| `51aeed9904ca0ae6f116718449813246af63796f` | D2 closed with seeded real PG18/uvicorn/built-Astro five-locale evidence proof; C2 advanced; G3: positive match could carry FALSE/UNKNOWN concrete criterion; C3: 0/40/200 lacked both Power candidate planes simultaneously. [Review](https://github.com/StradaDelSole/HullQ/pull/393#pullrequestreview-5687504598): REVIEW. |
| **`76f542635d3d04ae9e8c4c05c8a704912f0ba3d4`** | **G3/C3 closed**: positive leaves constrained TRUE, aggregate truth and matching config identities checked; real mixed 0/40/200 with Sail exclusions and both Power paths; prior A/B/D2/E/F2 closed. [Final independent review](https://github.com/StradaDelSole/HullQ/pull/393#pullrequestreview-5688152084): **READY FOR OWNER ACCEPTANCE**, followed by explicit Owner “akzeptiert”. |

### Executed proof retained in repository

- Real PostgreSQL18 persistence/API regression for current POWER claim, count-only/drive-only/both MUST/AND, scope and current revision, other-Organization conflicts, two-connection MVCC concurrency, design-linked same NamedVariant and adversarial split, FieldResolution stale/null/zero/unresolved and factory-vs-installed disagreement, historical migration/replay, unchanged Sail and broker Search-fit.
- `scripts/inspect_power_search_form.py` and `web/scripts/inspect_power_search_form_playwright.mjs` execute a real headless browser against actual uvicorn + built Astro SSR with migrated disposable PG18; **20/20** user-submission assertions (four filter cases × five locales). The browser requires JavaScript; the submission-time omission technique follows existing Sail. No independent non-JS functional-submission claim is made.
- `scripts/inspect_power_search_evidence_slice_0094.py` seeds real D29-eligible claim-only and design-qualified current Power listings; accesses actual FastAPI and built Astro SSR through HTTP and checks both result classes, actual source labels and localized non-null VALUE_MISSING reason across five locales × count-only/combined = **10/10** rendered-page cases.
- `tests/persistence/test_power_engine_count_performance_slice_0094.py` uses disposable real PG18 data. It retains 0/40/200 claim-only cohorts; additionally runs count-only, drive-only and combined search against **the same 0/40/200 mixed Sail + design-unresolved Power + fixed three qualified design-linked Power candidates** (zero has none), preserving exact match-ID partitions and real SQL statement counts. It retains `EXPLAIN (ANALYZE, BUFFERS)` of the batched-claim read and per-design coherent snapshot from a **single** mixed-plane 200-candidate evaluation, plus the separate 0/10 design-linked stress test. The 200-case has an O(N) full Search pattern; a fixed three-design sample does **not** establish hosted-scale behavior with many distinct designs. Pre-real-data CR-05 #355 remains a hard STOP.
- Final implementation agent reported: Ruff clean; mypy clean (193 src files); repository validator PASS with pre-closure count 10; Power PG18 regression **104 PASS**, Sail/platform regression **192 PASS**, Web Node **603 PASS**, Astro check 0 errors and build PASS; both named real E2E inspectors PASS. These local numbers are agent-reported, not an independent local rerun by reviewer.

### Independently verified accepted-HEAD GitHub workflows

| Gate | Exact implementation HEAD result |
|---|---|
| [CI run 40749129791](https://github.com/StradaDelSole/HullQ/actions/runs/40749129791) | **SUCCESS — all six**: Ubuntu and Windows Quality, PostgreSQL-18 DB Integration, Web Quality, Historical Replay, Dependency Audit |
| [Manufacturer reproducibility 40749129776](https://github.com/StradaDelSole/HullQ/actions/runs/40749129776) | **SUCCESS** — Ubuntu and Windows |
| [Deploy workflow 40749129879](https://github.com/StradaDelSole/HullQ/actions/runs/40749129879) | **SUCCESS for applicable build checks**; GHCR pushes and production deployment **SKIPPED**, not evidence of a production rollout |

## Decision / implementation reconciliation and explicit STOPs

**DECIDED_AND_IMPLEMENTED:** Publisher-owned installed principal engine count typed and revisioned; Power criterion #2 exact numeric Search and actual same-revision + same-design-configuration AND; authorized broker edit; five-locale Power API/buyer SSR; provenance and D29; fail-closed design and Organization boundaries; 400/308/502 contract and actual E2E/PG18 proof; nine Sail criteria unaffected.

**DECIDED_NOT_YET_IMPLEMENTED:** Power technical specialist expansion and equal-category Broker Search-fit, genuine Power model/motorization corpus with proven rights, condition-qualified speed/range/fuel/consumption, Motorsailer category policy, Power-specific NautiX import/export, public joint-category buyer browse, owner-direct trust and saved Search/alerts. Under #372 and existing overall MVP register.

**EXPLICITLY_DEFERRED / HARD STOP:** Actual external broker or owner-direct inventory production data, hosted/pilot Search-scale CR-05 and bounded runtime (#355), joint Sail+Power external release (#366), production/provider/HA/backup/support/legal/verification readiness, launch pack, broader Power schema v0.7, unsupported public count tokens 9–32, XLSB export (#362). Do not confuse technical internal acceptance with provider go-live.

**GENUINELY_OPEN:** Exact Motorsailer dual-domain policy, future source-rights-qualified factory Power corpus and additional canonical drive/engine field taxonomy, the best next separately approved slice.

**CONFLICT_OR_REGRESSION:** Initial independent review findings A–F, C2/D2/F2 and G3/C3 were addressed at the accepted exact HEAD. No false hybrid-variant or cross-revision match, no broker assertion portrayed as independent HullQ verification, no pricing influence on organic truth, no production-data or launch gate weakening.

**Production Readiness:** IN_PROGRESS. **Production Launch Pack:** NOT_STARTED. **External marketplace production data:** NOT_PRESENT. **Production pilot:** NOT_STARTED. **Public production launch:** NOT_STARTED. Issues #355/#366/#372 stay OPEN.

## Canonical closure / Owner-local FINISH boundary

```text
PROJECT_STATE_ACCEPTED_SLICE: 0094
PROJECT_STATE_QUEUE_SLICE: 0095 — NOT SELECTED / NOT READY
SLICE_0094_TYPE: IMPLEMENTATION
SLICE_0094_RESULT: OWNER_ACCEPTED_POWER_ENGINE_COUNT_AND_SAME_CONFIGURATION_AND
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 11 — Sail 9 / Power 2
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

This is a **separate docs-only Owner acceptance closure**, not another primary implementation slice. Per the Owner's binding 2026-10-28 workflow assignment, **ChatGPT project master/reviewer itself** must inspect and verify this docs-only closure on the exact HEAD (disclosing that its own authored docs receive a source-based self-review), check its **own** six-job GitHub CI, manufacturer reproducibility and applicable Deploy workflow to successful completion, correct any findings, and squash-merge the closure PR to `main`. **Do not delegate this review to Claude.** **Only after this closure is independently verified and merged** does the Project Owner run the unchanged local `FINISH_SLICE.bat`, entering **0094**. This document does not claim Owner-local FINISH before the Owner reports its result. No SLICE-0095 work is selected or started automatically.
