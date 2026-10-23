# SLICE-0088 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / BROKER INVENTORY PORTABILITY EXPORT  
**Implementation PR:** [#368](https://github.com/StradaDelSole/HullQ/pull/368)  
**Last independently reviewed implementation code HEAD:** `167e79e6779461873d51963933537ceb6f3a27d4` (Round 3, previous blocking semaphore Finding A CLOSED)  
**Final reconciled implementation HEAD:** `5dbcccd61d5be8bbc5b448444d778b96ee5a0541` (only Pillow/Certifi + odfpy lockfile conflict reconciliation, both parent commits preserved)  
**Implementation squash-merge on main:** `4cb5ec3ca03190575df1f8e753668c89d6d597f4`  
**Project Owner acceptance:** explicit “ok akzeptiert go” on 2026-10-23 (Europe/Vienna), after independent code ACCEPT; documented on PR #368 in [Owner acceptance record](https://github.com/StradaDelSole/HullQ/pull/368#issuecomment-6374057733).  
**Controlling contract:** `docs/slices/SLICE-0088-broker-inventory-portability-export.md` and its Owner-accepted 2026-10-16 seven-format feasibility amendment.

## Accepted capability — truthful seven-format portable broker export

SLICE-0088 closes **`REQ-BROKER-022` and `MVP-BROKER-009`** in the specifically authorized portable-file-download scope. Authorized, currently MFA/current-PUBLISHER, Organization-scoped brokers may select their own private ProfessionalListingDrafts and/or promoted NativeListings, inspect completeness/provenance/rights/loss and per-format eligibility, then explicitly download one bounded authoritative export file. A private draft excluded from a NautiX output is disclosed as NOT exportable, never silently represented as an exported advert.

| Owner-accepted genuine output | Boundary |
|---|---|
| CSV and TSV | Structured text with spreadsheet formula-injection hardening |
| XLSX and legacy XLS | Genuine respective spreadsheet writers / file signatures |
| ODS | Genuine OpenDocument writer / validated re-import |
| Structured JSON | Typed portable data representation |
| NautiX 1.4 `adverts.xml` | Pinned XML profile, explicitly supplied destination account/office/sale class, mandatory fields, pinned XSD / importer proof |

**XLSB export is explicitly deferred, not implemented:** Issue [#362](https://github.com/StradaDelSole/HullQ/issues/362) records the unsolved viable, vetted writer alternative. The existing 0083 XLSB **import** remains supported. Seven outbound formats were expressly accepted by the Owner; earlier eight-format readiness language is superseded, not silently delivered.

**Not included:** YachtWorld/BoatWizard feeds, actual external provider integration/agreement/import acceptance, live portal push, syndication, callbacks, synchronization, seller-contact or lead bulk export, co-brokerage rights, paid feature parity, or any production/pilot data path.

## Implementation safeguards and proof

- `src/hullq/domain/inventory_export.py` and `src/hullq/application/inventory_export.py`: one bounded typed snapshot, truthful output mapping, current authorization and source ownership, explicit unknown/omission/rights evidence, deterministic row identity and format preflight, export byte/row limits.
- `src/hullq/api/app.py`: bounded body input and dedicated export executor admission before heavy database and serialization work; completed background jobs retain semaphore admission even if awaiting HTTP task is cancelled. The final Round-3 implementation binds release to the underlying `concurrent.futures.Future`, not the cancellable asyncio wrapper.
- Current PostgreSQL `REPEATABLE READ`, `READ ONLY` snapshot and post-snapshot authority checks; mandatory complete `expected_snapshot_fingerprint` plus `STALE_SELECTION` rejection if relevant source fields change between preview and download.
- Astro broker export page / same-origin API proxies: authenticated selection, per-format warnings, mandatory preview confirmation, disabled stale downloads. The `previewGeneration` counter prevents a late prior HTTP preview from reactivating Download after any selection/format/NautiX-profile change.
- Seven actual serializers, formula-injection protection, mandatory target-field rejection, neutral filenames, no external exporter push/write side effects, no private PII or cross-tenant inventory.
- Retained inspector `scripts/inspect_broker_inventory_export.py` against disposable real PostgreSQL 18 + FastAPI + built Astro SSR, with pinned NautiX XSD and genuine 0083 re-import and a Playwright real-browser script. Implementer reported all thirteen steps and **14/14** browser checks PASS, including actual downloaded XML bytes; independent reviewer checked source/test assertions but did **not** claim personally rerunning that complete inspector.

## Independent review / exact-HEAD gates

| Gate | Verified result |
|---|---|
| Independent code review, Round 3 | **ACCEPT** on `167e79e...`, [PR #368 review comment](https://github.com/StradaDelSole/HullQ/pull/368#issuecomment-6352560907); previous Round-2 cancellation Finding A CLOSED by five deterministic tests |
| Final reconciliation | Two-parent merge `5dbcccd...` adds only approved main Security PR #370's Pillow 13.0.0 + Certifi 2026.10.19 to existing export writer dependencies, no export behavior changed |
| GitHub CI [run 40018867760](https://github.com/StradaDelSole/HullQ/actions/runs/40018867760) | **SUCCESS** — dependency audit, Ubuntu/Windows quality, PostgreSQL 18 complete DB integration/coverage, Astro web quality and historical replay all pass |
| Manufacturer reproducibility [run 40018869140](https://github.com/StradaDelSole/HullQ/actions/runs/40018869140) | **SUCCESS** — Ubuntu/Windows |
| Deploy workflow [run 40018867736](https://github.com/StradaDelSole/HullQ/actions/runs/40018867736) | **SUCCESS build-only**, no production push/deploy claim |
| Owner | **ACCEPTED** — “ok akzeptiert go” 2026-10-23 |
| Implementation PR | **MERGED** — PR #368 squash `4cb5ec3ca03190575df1f8e753668c89d6d597f4` |

Security baseline Issue [#369](https://github.com/StradaDelSole/HullQ/issues/369) was separately fixed by Owner-accepted Security PR #370, already merged before the final 0088 reconciliation; CI audit is **green**, not waived.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED:** `REQ-BROKER-022` / `MVP-BROKER-009` outbound broker-controlled file portability in seven truthful formats, exact Organization/MFA/PUBLISHER permissions, read-only single-snapshot source data, explicit preview and per-target truth, bounded off-event-loop generation, stale-confirmation and spreadsheet/formula safeguards.

**EXPLICITLY_DEFERRED:** XLSB export writer feasibility (#362); vendor-controlled external feeds/integration, real YachtWorld or other portal acceptance and live syndication. Existing inbound XLSB parser remains implemented.

**DECIDED_NOT_YET_IMPLEMENTED:** Periodic broker engagement reporting (`REQ-BROKER-028` / `MVP-BROKER-008`), volume-triggered broker demand/exclusion analytics, owner-direct admission and trust/safety, buyer persistence/Saved Search, full Power-and-Sail buyer/product capabilities for public launch, production-ready providers and operator runbooks; all remain separately gated.

**CONFLICT_OR_REGRESSION:** Two successive independent review rounds exposed and then closed the executor cancellation and stale-preview races. Round-3 tests A–E cover real-worker cancellation, cancel-before-start, completion, worker error and running parallelism. Dependency reconciliation carried no export source change and exact-HEAD external CI/manufacturer are green. No residual 0088 implementation blocker found.

## Unchanged release gates and next action

```text
PROJECT_STATE_ACCEPTED_SLICE: 0088
PROJECT_STATE_QUEUE_SLICE: 0089 — UNSELECTED / NOT READY
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
REQ_BROKER_022_STATUS: IMPLEMENTED
MVP-BROKER-009: IMPLEMENTED
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

The accepted BROKER Workspace **product** launch gate is not an authorization for **real external broker uploads**: the operational pre-pilot STOP captured in issue [#355](https://github.com/StradaDelSole/HullQ/issues/355) and real PostgreSQL HA/standby, provider, security, rights, restore and other Production Launch Pack proofs remain mandatory. Nine existing Buyer Search dimensions are unchanged. No unilateral selection/START of SLICE-0089.

This is the **separate documentation-only Owner acceptance closure** following implementation PR #368. Independently review this closure's exact HEAD, machine markers, capability transitions, CI and reproducibility, then merge its PR. **Only after the closure PR is merged** should the Owner run local `FINISH_SLICE.bat` and enter `0088`. Its success has not yet been observed.
