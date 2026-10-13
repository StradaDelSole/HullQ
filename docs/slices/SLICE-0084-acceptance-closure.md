# SLICE-0084 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / HIGH_RISK BROKER PRE-PUBLICATION TECHNICAL SEARCH-FIT  
**Implementation PR:** #342  
**Accepted exact implementation branch HEAD:** `cc1ac2cbc0285d0ebdd1f8a8ea1a7eb2ae9b007e`  
**Implementation squash-merge on main:** `f761eef805dbca575def5c62409d9357701b1eb9`  
**Independent final exact-HEAD review:** ACCEPT, review `5505223829` on PR #342  
**Project Owner acceptance:** explicitly stated **“0084 akzeptiert”** on 2026-10-13, after independent ACCEPT, before implementation merge  
**Primary implementation contract:** `docs/slices/SLICE-0084-broker-prepublication-search-fit.md` (READY via PR #340; pre-handoff quality amendment PR #341)  
**Owner-priority authority for following work:** `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md` (PR #338) and tracking issue #339

## Accepted capability

An authorized current Organization **PUBLISHER** with required MFA can use the existing private Broker Workspace inventory editor to run a **read-only, illustrative (not real-buyer-demand) Search-fit preview** for one Organization-owned, already promoted, lifecycle-`DRAFT` NativeListing. Brokers select one or both **already accepted** technical hard requirements, `draft_max` and `keel_configuration`, and receive typed `CONFIRMED_MATCH`, `CONFIRMED_NON_MATCH` or `INSUFFICIENT_DATA` outcomes with design/configuration and concrete PhysicalBoat criterion evidence, reasons, actual/current values where qualified, and links to existing editor surfaces for missing information.

The preview runs an authorized *single-target hypothetical DRAFT* evaluation and **does not** enumerate the existing buyer-facing ACTIVE/current-public Search candidates, publish/change listings, write claims, mint canonical BoatDesign links, create demand signals, make a listing publicly eligible or grant buyer visibility. Actual buyer Search continues to require its own D29 eligibility and other accepted rules. Pre-promotion ProfessionalListingDraft or imported source rows remain out of scope; no third public technical criterion is created. `LONG_KEEL` remains outside the accepted public `keel_configuration` vocabulary pending separate Owner-governed taxonomy reconciliation.

## Accepted implementation and retained proof

- `src/hullq/application/broker_search_fit.py`: single-target Organization/PUBLISHER/MFA/lifecycle/chain admission and fail-closed typed outcomes; shared qualified design/configuration/concrete-claim evaluation; explicit PostgreSQL `REPEATABLE READ` snapshot of authoritative inputs plus fresh post-snapshot current Membership/role/MFA and lifecycle rechecks. Snapshot-consistent evidence for an interleaved claim edit is permitted as a historical request-time evaluation, not a persistent or public truth assertion.
- `src/hullq/application/native_inventory_query.py`: extracted and reused bounded `build_mixed_requirement_query`, `build_configuration_evidence`, `classify_concrete_candidate`; public native Search and private preview share one accepted deterministic truth engine. Accepted public candidate/current-public filter remains unchanged.
- `src/hullq/api/app.py`: scoped broker GET route with typed non-enumerating 401/403/404, malformed 400, lifecycle 409, integrity 503 and typed evidence serialization using existing public Search serializers; inherited private `no-store`/`noindex` headers.
- `web/src/lib/brokerSearchFitApi.ts` and `web/src/lib/__tests__/brokerSearchFitApi.test.ts`: typed defensive API client and 14 reported frontend API tests; malformed/transport bodies cannot invent match.
- `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`: existing Broker editor gains illustrative GET-form, exact supported input vocabulary, duplicate/ambiguous query rejection, concrete and design/configuration per-criterion evidence with reasons/explanations and existing editor navigation. Escapes untrusted text, remains private no-store/noindex.
- `tests/persistence/test_broker_search_fit_api.py` and `tests/persistence/test_broker_search_fit_concurrency.py`: 19 core real PostgreSQL/FastAPI scenarios plus four concrete threading/interleaving regressions (role revocation, membership deactivation, publish transition and claim edit); expanded pre/post multi-table no-write fingerprint. The dangling canonical BoatDesignRef integrity case is simulated within a disposable test schema after deliberately disabling its otherwise-protecting FK, never in normal production flow.
- `scripts/inspect_broker_search_fit.py`: retained disposable PostgreSQL 18 + real FastAPI + built Astro SSR inspection of DRAFT hypothetical match, design-level false/unresolved leaf explanations, duplicate-parameter rejection, missing design blocker, claim edit/recheck, cross-Org/MFA/unsupported taxonomy fail-closed behavior, ordinary publication and public technical Search equivalence. Proof is synthetic, not a real external broker pilot.

## Independent review and amendment

**First reviewed branch HEAD:** `1d3eedd49fb05c7b9b792e7c7bdc88ec8cfbf74c`, one implementation commit. The reviewer recorded `AMENDMENT REQUIRED` on PR #342 (review `5504494678`) for three bounded findings:

| Finding | First-review issue | Accepted amendment closure |
|---|---|---|
| **A — HIGH** | Authorization and DRAFT lifecycle checked only before a multi-statement read (lifecycle checked again, but not current Membership/PUBLISHER); torn concurrent state possible. | All evaluation reads from one PostgreSQL `REPEATABLE READ` snapshot; fresh current authorization + lifecycle rechecks before returning `OK`; four real PostgreSQL concurrent mutation tests with fail-closed denial and consistent claim snapshot. |
| **B — MEDIUM** | API carried accepted per-criterion design/configuration reasons and technical evidence, but private SSR rendered too little to explain design-level nonmatches/unknowns. | UI renders requested criteria, config/leaf truth, reason, explanation and qualified observed values for design and actual yacht, across result classes; retained real SSR positive/false/unqualified evidence proof. |
| **C — MEDIUM** | Astro `URLSearchParams.get` silently collapsed duplicate scenario values before the backend's duplicate-rejection boundary. | Astro `getAll` detects ambiguous repeated keys and returns a visible invalid scenario instead of a match; retained SSR negative proof. |

**Final accepted exact branch HEAD:** `cc1ac2cbc0285d0ebdd1f8a8ea1a7eb2ae9b007e`; one targeted amendment commit, **all three findings CLOSED**, no remaining blocking finding in the independently reviewed accepted scope. The Owner's amended first-handoff quality instructions yielded extensive tests at first submission, but did not eliminate an amendment. No automatic attribution/quantified productivity claim is made; a single amendment round was sufficient here, versus two in SLICE-0082.

## Verification — accepted exact HEAD only

| Gate | Outcome |
|---|---|
| Remote GitHub CI run **38413657278** | **SUCCESS** — Ubuntu/Windows, PostgreSQL 18 full suite and retained HTTP verticals, Web/Astro, historical PostgreSQL replay, dependency audit |
| Manufacturer artifact reproducibility run **38413656553** | **SUCCESS** — Ubuntu and Windows |
| PR Deploy workflow run **38413657002** | **SUCCESS** — API/Web image builds; production push/deploy SKIPPED |
| Implementer-reported local | Ruff check/format, mypy (165 files), repository validator, 126 relevant Python tests, 444 Web tests, web check/build, real PostgreSQL/FastAPI/built-Astro retained inspection PASS |
| Independent source and exact-HEAD remote review | **ACCEPT**, PR #342 review `5505223829`; independent reviewer **did not rerun** local end-to-end script outside CI |

Remote image builds and synthetic integration are not evidence of an external deployment or an external live broker pilot. No new paid provider, account, storage or production database is activated.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED:** `MVP-BROKER-010` and `REQ-BROKER-026` within their accepted bounded representative **pre-publication** Search-fit scope. The existing source-truthful broker draft→promotion→NativeListing→manually associated canonical BoatDesign→concrete physical claim→Search pipeline remains accepted. Only the two current public hard technical criteria (`draft_max`, `keel_configuration`) exist after this slice. Mixed-supply/owner-direct public Search neutrality preserved.

**DECIDED_NOT_YET_IMPLEMENTED:** additional native Buyer Search hard filters and coverage (first LOA, then rudder/skeg; separate `LONG_KEEL`/full-keel vocabulary reconciliation; subsequently beam/displacement/rig/hull-material and other qualified fields); broker inventory export (`MVP-BROKER-009`, `REQ-BROKER-022`), periodic Broker reporting beyond SLICE-0075 factual snapshots (`MVP-BROKER-008`, `REQ-BROKER-028`), volume-triggered Search exclusion/aggregate demand insights (`REQ-BROKER-025/029`), and other buyer/owner-direct/trust/comms/ops/privacy/legal requirements at their accepted triggers. Accepted 0083 import remains implemented separately.

**EXPLICITLY_DEFERRED:** real customer/third-party production data, external pilot, paid broker launch, public production deployment, automatic publishing, automatic BoatDesign association, pre-promotion draft Search-fit, buyer-usage demand claims, Search ranking/payment changes, uncontrolled extra criteria or data inferences.

**GENUINELY_OPEN:** exact next technical hard-criterion/LOA readiness contract, end-to-end design-to-concrete claim mappings and later slice decomposition; numeric SLICE-0085 is **UNSELECTED** pending fresh post-0084 reconciliation and reviewed readiness. The Owner's prioritized *wave* is accepted and binding, but no future criterion contract/extra hard filter is implicitly authorized.

**CONFLICT_OR_REGRESSION:** no unresolved review findings or accepted Search/kernel regression. Original transient concurrency, rendered explanation and duplicate-param gaps were addressed before Owner acceptance and merge.

## Production/queue boundary and required following priority

```text
PROJECT_STATE_ACCEPTED_SLICE: 0084
PROJECT_STATE_QUEUE_SLICE: 0085
SLICE-0085: UNSELECTED — reassessment/readiness required
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

**Next development priority is not generic/optional work.** The Owner explicitly directed that, *after accepted 0084*, HullQ prioritize technical native Buyer Search expansion, beginning with qualified **LOA** and then **rudder/skeg**, alongside a separately reviewed existing-keel `LONG_KEEL` taxonomy/claim-mapping gap. The controlling post-0083 decision PR #338 / `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md` and tracking issue #339 remain operative. At the mandatory **post-0084 Decision/Implementation Reconciliation**, review LOA feasibility and applicable Gate 3 (`COMMON STRUCTURE GENERALIZED / REUSED` or `STRUCTURALLY DISTINCT — NO THIRD COPY`), testable Design/FieldResolution/current PhysicalBoat truth and already-accepted gates; require explicit Owner decision for any evidence-supported priority exception. **Do not preselect any later slice or start 0085 during this closure.**

The Production Launch Pack remains `NOT_STARTED`; Production Readiness remains `IN_PROGRESS`. SLICE-0084 did **not** activate a new production-data or launch gate. After this **docs-only Owner Acceptance Closure PR** passes its own independent exact-HEAD review, GitHub CI and manufacturer reproducibility and merges to canonical `main`, the Project Owner may execute **`FINISH_SLICE.bat` for 0084**, never before. 
