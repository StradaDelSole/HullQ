# SLICE-0087 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / HIGH_RISK QUALIFIED BEAM & HULL-MATERIAL BUYER SEARCH  
**Implementation PR:** #352 (https://github.com/StradaDelSole/HullQ/pull/352)  
**Owner-accepted exact final implementation branch HEAD:** `88c8baa3e8451f9b0afaca776766b1f5a450f354`  
**Implementation squash-merge on main:** `e6d30f1671e6834d097068a7318a4d84c8f96e04`  
**Independent final implementation review:** **ACCEPT** at exact final HEAD; PR #352 comment `6202278022`; initial findings A/B documented in PR #352 comment `6200576826`, both CLOSED in the final amendment.  
**Project Owner acceptance:** explicit **“0087 akzeptiert”**, 2026-10-15 (Europe/Vienna), *after* independent ACCEPT and verified final exact-HEAD CI/manufacturer; recorded before implementation merge in PR #352 comment `6202366086`.  
**Primary READY contract:** `docs/slices/SLICE-0087-qualified-beam-hull-material-search.md`; governing reconciliation `docs/POST_SLICE_0086_BEAM_HULL_MATERIAL_REASSESSMENT_2026-10-15.md`; READY docs PR #351.

## Accepted capability — two qualified technical Search dimensions

SLICE-0087 delivers two **additional independent public hard technical** criteria across the existing shared public Buyer Search + authorized private illustrative Broker Search-fit. The Owner-accepted native Search dimension count advances **7 → 9 in this separately reviewed formal closure**, not in readiness or the implementation merge.

| New technical criterion | Public hard request | Independently current concrete PhysicalBoat claim |
|---|---|---|
| **#8 beam (overall breadth / maximum width)** | `beam_min` and/or `beam_max`: inclusive, exact positive finite `Decimal` metres, **ONE semantic dimension** even with two URL keys | optional `physical_boat.beam` VALUE_ASSERTION (positive Decimal metres), explicit UNKNOWN, or omitted wrapper |
| **#9 hull_material** | exactly one of `GRP_FIBERGLASS`, `STEEL`, `ALUMINUM`, `WOOD` | optional `physical_boat.hull_material`: VALUE_ASSERTION of the existing **seven** concrete registry values (the four plus `FERROCEMENT`, `CARBON_COMPOSITE`, `OTHER`); explicit UNKNOWN, or omitted wrapper |

The public hull-material mapping is deliberately narrower than valid actual offered-boat claim vocabulary. Exact, source-qualified BoatDesign v0.5/v0.6 `grp_fiberglass`→`GRP_FIBERGLASS`, `steel`→`STEEL`, `aluminium`→`ALUMINUM`, and `wood`→`WOOD` are the **only** positive design→public mappings. Neither `wood_composite`→`WOOD` nor `carbon`→`CARBON_COMPOSITE`, unknown/other/ferrocement or marketing/import labels are inferred. Claim-only tokens cannot be used as public Search filters in 0087.

Both facets share the **single accepted qualified evaluation kernel**. A confirmed buyer result must satisfy all selected hard leaves on the **same** applicable, qualified BoatDesign/NamedVariant configuration *and* on an independently and currently asserted nonconflicting actual PhysicalBoat publisher observation. No cross-configuration assembly, competing-Organization false confirmation, unqualified FieldResolution, old-version guessed material, DRAFT/current-public D29 bypass, paid/rank influence, or claim manufacturing from listing text/import tags is permitted. Optional omission remains distinct from explicit UNKNOWN and positive VALUE_ASSERTION; invalid/duplicate/noncanonical query cases retain typed failure or canonical 308 behavior.

The authenticated MFA/current-PUBLISHER-authorized broker can save and reopen the two facts via the existing immutable PhysicalBoat revision/head and authorized editor, with old exact retry fingerprints preserved, and preview the same criterion evaluation **read-only** for one owned promoted lifecycle-DRAFT listing. These previews remain illustrative, not real buyer demand. Buyer controls, canonical links, design-versus-actual evidence and error states use the accepted EN/DE/FR/PT/ES public surfaces. Original draft/keel-only buyer sensitivity remains available, but any beam/material or prior added criterion suppresses unsupported comparison rather than weakening constraints.

Nine accepted semantic dimensions are:

```text
1 draft_max
2 keel_configuration
3 loa (loa_min and/or loa_max; ONE dimension)
4 rudder_configuration
5 hull_configuration
6 cockpit_position
7 deck_saloon
8 beam (beam_min and/or beam_max; ONE dimension)
9 hull_material (GRP_FIBERGLASS/STEEL/ALUMINUM/WOOD public only)
```

Eleven public technical query parameter keys correspond to nine semantic hard dimensions. `LONG_KEEL` remains publicly unsupported; there are no new PREFER/OR, ranking, broader material, displacement, rig, buyer Saved Search, or new owner-direct/public launch permissions.

## Implementation and retained verification

- **Bounded domain/writer:** `src/hullq/domain/{physical_boat_claims,inventory_edit_request}.py`, `src/hullq/application/inventory_editing.py`; `BeamClaim` and `HullMaterialClaim`, exact-field parsing and omission/UNKNOWN states; old fields preserved.
- **Immutable persistence:** `src/hullq/persistence/physical_boat_claims.py` and additive migration `alembic/versions/c7d4a1e95f36_qualified_beam_hull_material_claims.py`; nullable optional assertion pairs, DB checks, exact pre-0087 retry fingerprints, transactional revisions and current-org observations.
- **Qualified shared Search:** `src/hullq/search/{beam_design_bridge,beam_request,hull_material_design_bridge,criteria_registry}.py`; existing typed `FieldProjectionSpec`/FieldResolution/NamedVariant projection + bounded material mapping; existing common MUST/AND evaluator. `src/hullq/application/{native_inventory_query,search_read,broker_search_fit}.py` and `src/hullq/api/app.py` add buyer/private requests, canonical links and evidence without a second Search engine.
- **Browser:** existing Astro buyer Search, broker edit/Search-fit and typed web clients in all five locales. Focused accessible labels were added for every new broker claim control during review amendment.
- **Evidence:** focused domain/DB/API/unit/web tests, old-snapshot/retry and invalid-value DB checks; retained `scripts/inspect_slice_0087_qualified_beam_hull_material.py` uses disposable **real PostgreSQL 18 + FastAPI + built Astro SSR**, qualified test designs/claims, real authorized save/reopen/publish, all four positive public material matches individually, negative `wood_composite`, legacy `keel_configuration=FIN` mixed with both new facets, explicit rendered design + actual evidence, five-language canonical SSR, 400/308, and accessible control-label association. Implementer reported an actually executed full inspector **PASS [SLICE-0087-DONE]**; independent reviewer inspected the runnable assertions and amendment, **did not claim personal re-execution**.

## Independent review and amendment history

| Finding | Initial evidence | Closure on final exact HEAD |
|---|---|---|
| **A — MAJOR / executable proof** | First retained built SSR inspector only showed GRP positive; four-material positive coverage and legacy+new browser combination required by READY were absent. | Same retained real PG18+FastAPI+built SSR inspector expanded for STEEL/ALUMINUM/WOOD distinct results + FIN keel AND beam/material per-leaf rendered evidence. Inspector's full-claim POST preserves original FIN claim across replacement. |
| **B — MAJOR / broker editor accessibility** | Four new claim controls had only group `<fieldset><legend>`, no per-control accessible status/value label. | Explicit unique `id` and matching `<label for>` on all four; retained actual built SSR markup proof tests one-to-one association and distinct labels. |

Review sequence: initial Claude handoff HEAD `ee3714d0c0b925d3b1ed59caded64d3800f7c1ac`, review **AMENDMENT REQUIRED** comment `6200576826` in PR #352; exactly two amended files in new HEAD `88c8baa3e8451f9b0afaca776766b1f5a450f354`; independent exact-HEAD **ACCEPT** comment `6202278022`. No further findings or unexpected implementation scope drift. Owner acceptance quote recorded before merge (comment `6202366086`).

## Exact final implementation HEAD external gates

| Gate | Verified result |
|---|---|
| GitHub CI run `38803674528` | **SUCCESS** — all six jobs: Ubuntu and Windows quality, PostgreSQL 18 DB integration, Astro/Node, dependency audit, historical replay |
| Manufacturer reproducibility run `38803674483` | **SUCCESS** — reproducible Ubuntu/Windows artifacts |
| Deploy workflow run `38803674514` | **SUCCESS** *build-only*: no GHCR push or real production VPS deploy authorized |
| Independent exact-HEAD review | **ACCEPT**, PR #352 comment `6202278022` at `88c8baa3...` |
| Project Owner | **ACCEPTED** — “0087 akzeptiert” 2026-10-15; PR comment `6202366086` |
| Implementation merge | **MERGED**, PR #352 squash `e6d30f1671e6834d097068a7318a4d84c8f96e04` |

## Decision / Implementation Reconciliation

**DECIDED_AND_IMPLEMENTED:** Exactly **nine** accepted public native technical hard dimensions; bounded two additional source-qualified design/current physical assertion filters, common same-configuration AND and per-Org fail-closed query, immutable actual boat claim authoring and private read-only broker Search-fit with persisted claims. The canonical acceptance count moves **7 → 9 in this closure**.

**DECIDED_NOT_YET_IMPLEMENTED:** Further qualified search fields (displacement/basis, rig, broader material variants and a justified long/full-keel mapping); buyer Saved Search/alerts, account persistence, broadened sensitivity, broker inventory export and periodic analytics delivery, owner-direct public publication and Trust & Safety/privacy/legal/support/admin, actual production provider evidence and external pilot.

**EXPLICITLY_DEFERRED:** False material aliases (`wood_composite` to wood or `carbon` to carbon composite), public `OTHER`/`FERROCEMENT`/`CARBON_COMPOSITE` hard material queries, automatic imported/modeled/photo claims, full/long keel evidence-free inference, OR/PREFER, paid organic influence, production data/launch without separate hard gates.

**GENUINELY_OPEN:** Post-0087 capability selection under the Owner's product/launch priorities and updated real first-listing critical-path comparison; additional source-justified taxonomy decisions. **No SLICE-0088 capability is preselected or authorized.**

**CONFLICT_OR_REGRESSION:** Both initial independent Findings A/B are closed on exact accepted HEAD. No other material source regression or unresolved review finding identified. Existing governance state/listing gates unchanged.

## State, gates and next action

```text
PROJECT_STATE_ACCEPTED_SLICE: 0087
PROJECT_STATE_QUEUE_SLICE: 0088 — UNSELECTED / NOT_READY
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
LONG_KEEL_PUBLIC_SEARCH: UNSUPPORTED
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

The first **real externally visible** buyer-facing listing is **not** authorized by completing these two Search filters. Its remaining slice count is not reliably estimable without actual provider-configuration/launch evidence; critical blocking steps include Production Readiness PASS, managed PostgreSQL/standby+automatic failover before real buyer exposure, relevant provider keys/backup/restore/observability and Launch Pack phases 1–5 as applicable. Broker export and periodic engagement reports remain independently required before paid/broad public broker launch. Implemented technical breadth must not become justification for indefinite launch delay.

This document is the **separate documentation-only formal acceptance closure** after implementation PR #352 merge and explicit Owner acceptance. The reviewer must examine its exact PR HEAD, atomic state/count/MVP updates and exact-head external CI/manufacturer reproducibility before merging it. **Only after this closure PR is reviewed and merged** should the Owner run `FINISH_SLICE.bat` for `0087`. The Owner's local FINISH has **not** been observed and is not asserted. No `START_SLICE.bat` for 0088 is authorized.
