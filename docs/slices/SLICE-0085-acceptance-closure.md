# SLICE-0085 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / HIGH_RISK BOUNDED MULTI-CRITERIA TECHNICAL BUYER SEARCH  
**Implementation PR:** #345  
**Accepted exact implementation branch HEAD:** `12388b18e526ac5ac1e5d9747538fff99f511518`  
**Implementation squash-merge on main:** `c006016466d6a90c9c7ff083eaa3a0b0ba03c282`  
**Independent final exact-HEAD review:** **ACCEPT**, review `5510329645` on PR #345  
**Project Owner acceptance:** explicitly **“akzeptiere 0085”** on 2026-10-14 (Europe/Vienna), after independent ACCEPT and final exact-HEAD gates; acceptance precedes implementation merge  
**Primary contract:** `docs/slices/SLICE-0085-multicriteria-technical-search-foundation.md` (READY via PR #344); controlling post-0084 Owner bundling strategy `docs/POST_SLICE_0084_MULTICRITERIA_SEARCH_REASSESSMENT_2026-10-13.md`, tracker issue #339.

## Accepted capability and boundaries

SLICE-0085 extends the previously accepted two native public Buyer Search **hard technical dimensions** to **four**, counting semantic dimensions and **not** URL query keys, lower/upper operators or private preview modes:

1. `draft_max` — prior accepted exact maximum draft in metres.
2. `keel_configuration` — prior accepted six-value public keel taxonomy unchanged.
3. `loa` — **one newly accepted dimension** with `loa_min` and/or `loa_max` inclusive exact-Decimal metres. Both bounds use one qualified `BoatDesign.dimensions.loa_m`/NamedVariant projection and independently qualifying current `PhysicalBoat.loa_length` claim.
4. `rudder_configuration` — **one newly accepted categorical dimension**, with a conservative generation-aware v0.5/v0.6 interpretation of qualified design facts and current `PhysicalBoat.rudder_configuration` claim. The accepted public requested values are `SKEG_HUNG`, `TRANSOM_HUNG`, `SPADE` and `TWIN`, but **not every design generation can confirm every value**. v0.6 `rudder_support=free` is never automatically `SPADE`; unresolved/skeg/transom/count overlaps and conflicting/absent evidence are `UNKNOWN`/insufficient, not a confirmed match. The actual publisher's concrete facts are required independently from canonical BoatDesign truth.

All supported hard leaves compose via the existing single **MUST/AND** kernel against the same eligible BoatDesign/NamedVariant configuration and the actual currently asserted physical boat; confirmed FALSE and UNKNOWN never yield a confirmed public match. Same-PhysicalBoat cross-Organization claims remain qualified using one consistent PostgreSQL observation snapshot. Buyer public Search uses D29/current-public eligibility (DRAFT excluded), canonical query order, noindex, typed evidence and multilingual EN/DE/FR/PT/ES rendering. Private broker Search-fit mirrors the new dimensions on a *single authorized Organization-owned lifecycle-DRAFT* target using the already accepted MFA/PUBLISHER/consistent snapshot/post-snapshot authorization boundary, with read-only illustrative results **not buyer demand**. Accepted pure `draft_max` legacy output, older keel combinations, shortlist/Compare/discovery token and other product rights remain respected.

A static **typed `CriterionDefinition` registry** controls criterion IDs, operator shapes, whitelisted canonical parameter keys, exact numeric parsing/canonicalization or bounded categorical values, generation-specific design-set adapters and current concrete claim accessors. Both public/private request parsing and one common design/claim evaluation pipeline consume these definitions. No user-supplied dynamic JSON path, arbitrary schema Search field, general DSL, extra data model or new persistence is admitted.

**`LONG_KEEL` remains explicitly NOT SUPPORTED by public `keel_configuration`.** Full/modified-full/long-fin design categories were not independently proven equivalent to the accepted concrete `LONG_KEEL` value, so the READY contract's conservative fallback was exercised. `LONG_KEEL` adds **zero** technical Search dimensions and is not counted or exposed; its separate taxonomy/claim-mapping decision stays OPEN for an evidence-backed subsequent reassessment.

**Buyer Requirement Sensitivity limitation:** previous accepted draft/keel-only change comparisons still work. With any new LOA/rudder criterion active, the UI visibly indicates sensitivity is unavailable, instead of silently dropping new hard constraints and inventing misleading comparative counts. No extension to arbitrary sensitivity criteria was authorized.

## Implementation and retained proof

- `src/hullq/search/criteria_registry.py`: fixed typed whitelisted definitions, criteria-specific parsing/canonicalization, exact allowed token sets, design/variant builder and concrete publisher read adapter.
- `src/hullq/search/loa_request.py`, `loa_design_bridge.py`, `rudder_design_bridge.py`: bounded LOA parser (raw length at most 20 before Decimal creation), exact LOA FieldResolution and v0.5/v0.6 conservative raw-field qualified rudder derivation; no `SPADE` inference from v0.6 'free'.
- `src/hullq/application/native_inventory_query.py` and `src/hullq/persistence/physical_boat_claims.py`: common multi-criterion query/evidence/classification path, per-criterion definition-driven DesignConfigurationSet merged by exact configuration identity and current multi-field PhysicalBoat claims observed in one PostgreSQL snapshot; truth engine itself retained.
- `src/hullq/application/search_read.py`, `broker_search_fit.py`, `src/hullq/api/app.py`: accepted canonical/duplicate handling, private scenario validation, one typed public/private truth/serializer with eligibility and authorization preserved.
- Public Astro Search/TS clients/texts across five languages and existing private Broker inventory editor: LOA bounds, categorical rudder and per-criterion rendered observed/design evidence; invalid/ambiguous request handling; original-only sensitivity UI preserved, mixed/new sensitivity visibly unavailable.
- New focused unit/integration/HTTP/SSR tests and `scripts/inspect_multicriteria_technical_search.py`: disposable real PostgreSQL18 + actual FastAPI + **built Astro SSR** script verifies private five-leaf DRAFT preview with real design/concrete values, denied/invalid scenarios, real publish, public LOA/rudder/multi-leaf matches, oversize request 400 and noncanonical 308, **all five localized public URLs and rendered LOA/rudder evidence**, and sensitivity safety/legacy behavior. Real external pilot not exercised or implied.

## Independent review and two amendment rounds

The implementation first reached review at `bb42269a4cfb37acb487c6fd4bd4ae1e69b79314`. Independent first review `5509076907` on PR #345 required:

| Finding | Initial gap | Closed behavior/proof |
|---|---|---|
| A — **HIGH** | SLICE-0057 sensitivity forms on mixed old/new Search would omit new active constraints, yielding misleading but valid count deltas. | Forms gated to original-only criteria; truthful localized unavailable notice for any LOA/rudder-active Search; tested built SSR/old-only nonregression. |
| B — **MEDIUM** | LOA input had no explicit bound before Decimal parsing. | Maximum 20-character raw LOA lexical envelope; public/private negative and unit tests; other existing numeric syntax unchanged. |
| C — **MEDIUM** | Initial `criteria_registry` held mostly URL key strings; insufficient reusable typed wiring. | Real frozen/typed definitions consumed by public/private parsers, design-set merge and concrete claim qualification; bounded operators/values and no arbitrary field resolver. |
| D — **MAJOR ACCEPTANCE PROOF** | No retained real PostgreSQL18+FastAPI+built Astro SSR proof for new complete Buyer/Broker paths. | Executable end-to-end inspector added, independently inspected, reported executed PASS. |

First amendment HEAD `6bfae4e372c87dc3048b3739fc7bcfa60437d579`. Follow-up review `5509994284` recognized production fixes but required (C) parity test against **actual TypeScript export**, not a duplicate Python literal list, and (D) real SSR evidence and canonical links across **all five locales**, plus rendered design/concrete technical values rather than only hit counts. Second, narrowly scoped amendment HEAD `12388b18e526ac5ac1e5d9747538fff99f511518` changed only `tests/unit/test_criteria_registry_parity.py` and `scripts/inspect_multicriteria_technical_search.py`. Those tests now read actual `web/src/lib/searchApi.ts` exported arrays, include deliberate extra/missing value mismatch fixtures and exercise EN/DE/FR/PT/ES real SSR canonical/observed evidence. All four original findings and both final acceptance-proof gaps were declared CLOSED after independent source review at exact final HEAD: **ACCEPT**, review `5510329645`. There is no known unresolved material review finding; no claim that the independent reviewer locally re-executed the implementer's inspector is made.

## Exact accepted HEAD verification

| Gate | Result |
|---|---|
| Remote GitHub CI `38470580863` | **SUCCESS**: Ubuntu/Windows quality, full PostgreSQL 18 integration, Web/Astro, historical replay and dependency audit |
| Manufacturer artifact reproducibility `38470580811` | **SUCCESS**: Ubuntu and Windows |
| PR Deploy workflow `38470580697` | **SUCCESS**: API/Web image builds; production push and actual VPS deploy **SKIPPED** |
| Implementer-reported local final amendment | mypy and Ruff clean, repository validator PASS, targeted **84** unit tests PASS, retained PostgreSQL18/FastAPI/built Astro SSR inspector all steps PASS; last amendment changed only two evidence/test files |
| Independent final review | PR #345 review `5510329645`, **ACCEPT** on exact branch HEAD `12388b18e526ac5ac1e5d9747538fff99f511518` |

No new provider, paid cost, live data, pilot or public deployment was created by the PR image-build workflow.

## Decision / Implementation Reconciliation

**DECIDED_AND_IMPLEMENTED:** Public native technical hard criteria **4** (previous `draft_max`/six-value `keel_configuration`; newly `loa` min/max/range and bounded `rudder_configuration`), finite typed criterion registry shared across qualified Buyer Search and private authorized synthetic broker Search-fit; accepted evidence/freshness/eligibility/publisher and cross-Organization truth boundaries. The first multi-criteria Search bundle is delivered and closed; marker `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` must change from 2 to **4** only in this formal acceptance closure.

**DECIDED_NOT_YET_IMPLEMENTED:** Additional genuinely distinct qualified Search dimensions (beam, displacement, rig, hull material, ballast and further BoatDesign/concrete claim data); buyer sensitivity comparisons with new criteria, buyer persisted requirements/alerts, broker export and periodic reporting, owner-direct public admission, Trust & Safety, legal/privacy/operations and production provider verification. There is no automatic next Search bundle or numeric slice selection.

**EXPLICITLY_DEFERRED:** `LONG_KEEL`/full/modified-full/long-fin public taxonomy equivalence without independent mapping truth, automatic claim derivation, decomposed independent rudder properties or blanket v0.6 `free` → `SPADE`, arbitrary schema field activation, real customer/third-party broker data/pilot/public launch, paid ranking or removal of current-public eligibility.

**GENUINELY_OPEN:** evidence-backed long-keel taxonomy/claim bridge, which next bounded criterion bundle to choose after mandatory post-0085 reconciliation, and the cost/prioritization against outstanding Owner/MVP/legal/broker/production obligations. SLICE-0086 remains **UNSELECTED** here.

**CONFLICT_OR_REGRESSION:** all original review findings A–D and final two evidence gaps CLOSED at accepted exact HEAD. No accepted Search-regression or authorization-gap finding is outstanding; the unsupported long-keel and disabled sensitivity-for-new-filters are explicit product limitations, not silently complete features.

## Resulting accepted boundary / safe next step

```text
PROJECT_STATE_ACCEPTED_SLICE: 0085
PROJECT_STATE_QUEUE_SLICE: 0086
SLICE-0086: UNSELECTED — post-0085 reconciliation and independent readiness required
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 4
LONG_KEEL_PUBLIC_SEARCH: UNSUPPORTED — independently justified taxonomy decision pending
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

SLICE-0085 was **explicitly accepted by the Project Owner**, implemented on its isolated branch, independently exact-HEAD reviewed, remotely gated and implementation-squash-merged before this separate **docs-only acceptance-closure** PR. The next selected capability cannot be implied merely because one technical wave is complete. After independent exact-HEAD docs-only closure review, CI and manufacturer reproducibility PASS and this closure's squash-merge to canonical main, the Project Owner may run local `FINISH_SLICE.bat` for `0085`. The local FINISH has **not** yet been observed and is not asserted here. Do not run `START_SLICE.bat` for 0086 until the post-0085 reconciliation and separately reviewed READY contract have been merged and expressly released.
