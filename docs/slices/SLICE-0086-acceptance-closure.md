# SLICE-0086 — Acceptance Closure

**Status:** OWNER_ACCEPTED
**Slice type:** IMPLEMENTATION / HIGH_RISK FIRST-LEVEL SAILING-VESSEL DISCOVERY
**Implementation PR:** #349 (https://github.com/StradaDelSole/HullQ/pull/349)
**Accepted exact implementation branch HEAD:** `4337463fde821e8fd5da78e1db718f43d776ccc6`
**Implementation squash-merge on main:** `a2bb532a5a7b7d15a51caf71c82c46763796f6f4`
**Independent final exact-HEAD implementation review:** **ACCEPT**, PR #349 comment `6193304146`; earlier findings A–E all closed
**Project Owner acceptance:** explicitly **“0086 akzeptiert”**, 2026-10-15 (Europe/Vienna), after independent exact-HEAD ACCEPT and external gates; recorded in PR #349 comment `6193339724` before implementation merge
**Primary contract:** `docs/slices/SLICE-0086-first-level-sailing-vessel-discovery.md` (READY by independently reviewed PR #347); governing `docs/POST_SLICE_0085_FIRST_LEVEL_SAILING_VESSEL_DISCOVERY_REASSESSMENT_2026-10-14.md` and Owner-confirmed classifications/evidence rules.

## Accepted capability — first-level vessel structure

SLICE-0086 adds **three** new independent and combinable hard technical public Search dimensions, raising the accepted total **4 → 7**, through the already-accepted finite typed registry / FieldResolution / NamedVariant / common MUST-AND configuration kernel and independently current PhysicalBoat publisher claim qualification:

| Newly accepted dimension | Public positive hard-filter values | Optional current concrete PhysicalBoat `VALUE_ASSERTION` values |
|---|---|---|
| `hull_configuration` | `MONOHULL`, `CATAMARAN`, `TRIMARAN` | `MONOHULL`, `CATAMARAN`, `TRIMARAN`, `OTHER` |
| `cockpit_position` | `AFT`, `CENTER`, `FORWARD`, `MULTIPLE` | `AFT`, `CENTER`, `FORWARD`, `MULTIPLE`, `OTHER` |
| `deck_saloon` | `DECK_SALOON`, `PILOTHOUSE` | `NONE`, `DECK_SALOON`, `PILOTHOUSE` |

Each concrete field also has separately meaningful explicit `UNKNOWN` and omitted-wrapper states; `ABSENT` is not allowed. `OTHER` and `NONE` remain **claim-only**, not public positive filter tokens. A separately qualified BoatDesign `deck_saloon=none` is known absence, internally represented as a CONFIRMED `NONE` sentinel that contributes a typed non-match against positive deck filters; it is not missing/UNKNOWN and cannot be requested directly by the buyer.

Hull form is eligible from BoatDesign v0.5/v0.6; cockpit/deck facets require v0.6 qualified facts and do not fabricate missing v0.5 values. Separately qualified contradictory hull counts reject incompatible MONOHULL/CATAMARAN/TRIMARAN facts. Confirmed `cockpit_count=0` and `MULTIPLE` with separately confirmed `cockpit_count=1` fail closed; `MULTIPLE` requires distinct physical cockpits, not split zones in one cockpit. No blanket ban exists on unusual legitimate combinations such as CENTER+DECK_SALOON. Deck Saloon and Pilothouse are distinct single-value classifications; genuinely overlapping ambiguous source claims do not justify guessing.

No upstream marketplace/import tag, boat name, brochure phrase or photograph automatically promotes into qualified BoatDesign or independently asserted *current* PhysicalBoat truth. Even a qualified design value never manufactures an actual boat claim. The public Search requires same applicable named configuration and real current publisher claim, cross-Organization non-conflict, current-public D29/freshness/eligibility, and typed proven truth for **every** active hard leaf; false/unknown never becomes a confirmed match. The public form presents hull/cockpit/deck first and retains the four previously accepted details (`draft_max`, `keel_configuration`, `loa` min/max as ONE, `rudder_configuration`). URL keys total eight but count as seven distinct dimensions. Design/configuration and actual offered-boat evidence appear separately in English, German, French, Portuguese and Spanish. The broker's authenticated PUBLISHER/MFA-owned claim editor writes/reopens these fields through the existing immutable revision path, with old-revision retry content hashes preserved; read-only single-target DRAFT Search-fit supports the same three filters, not public buyer demand.

Accepted technical Search criteria now are exactly:
```text
1 draft_max
2 keel_configuration
3 loa (loa_min and/or loa_max, one dimension)
4 rudder_configuration
5 hull_configuration
6 cockpit_position
7 deck_saloon
```
`LONG_KEEL` remains public-search UNSUPPORTED, regardless of its historical concrete claim token. Additional motorsailer, traditional, classic, commercial sailing craft type/legal-use/certification facets are neither synthesized nor excluded as an admission category. New facets active disable rather than miscompute legacy draft/keel-only buyer sensitivity, retaining original-only sensitivity. Shortlist/Compare, signed discovery attribution, D29, source rights, private roles and organic non-commercial Search independence are preserved.

## Implementation and retained proof

- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`, `src/hullq/domain/physical_boat_claims.py`, `src/hullq/domain/inventory_edit_request.py`, `src/hullq/persistence/physical_boat_claims.py` and migration `alembic/versions/b2c6f94a0d31_sailing_vessel_hull_cockpit_deck_claims.py`: three bounded optional actual-boat claim pairs; database checks; transactionally safe immutable revisions and pre-0086 exact retry compatibility.
- `src/hullq/search/hull_design_bridge.py`, `cockpit_design_bridge.py`, `deck_saloon_design_bridge.py` plus shared `criteria_registry.py`, `native_inventory_query.py`, `search_read.py`, `broker_search_fit.py` and `api/app.py`: independent design fact qualification, cross-field consistency, single configuration and independent same-boat/current cross-Organization claim truth, bounded whitelisted parsing, public/private parity and previous-four nonregression.
- `web/src/components/SearchPageBody.astro`, `web/src/lib/searchApi.ts`, `searchPageData.ts`, `searchText.ts`, `brokerSearchFitApi.ts` and existing Broker inventory editor: first-level controls, truthful applied/current offered-boat vs design configuration evidence, five locales, canonical URLs and private Search-fit/claim editing.
- Unit, contract, live PostgreSQL-18 persistence, HTTP and Web/Astro regression suites. Retained `scripts/inspect_slice_0086_technical_search.py` executable inspector constructs disposable PostgreSQL state, runs actual FastAPI and **built Astro SSR**; verifies draft broker Search-fit, real claim save/reopen, publish, new facets alone/combined, all five locale canonical links and classified evidence, qualified NONE and invalid MULTIPLE negative paths, invalid 400 and noncanonical 308. The implementer reported the inspector locally **PASS**; the independent reviewer inspected its code/assertions but did not claim to have personally re-executed it.

## Independent review and amendments

| Finding | Initial issue | Verified closure |
|---|---|---|
| A — HIGH | Qualified design `deck_saloon=none` collapsed to MISSING/UNKNOWN | Internal-only known `NONE` sentinel, categorical typed FALSE for positive deck requests; NamedVariant inheritance/override negative tests. |
| B — HIGH | Public `MULTIPLE` could confirm with qualified `cockpit_count=1` | Count-one contradiction fails closed; count 0/1/2/unqualified and NamedVariant override tests. |
| C — MAJOR acceptance proof | Original implementation had API/PG/Web tests but no retained executed built SSR vertical proof | Added script `inspect_slice_0086_technical_search.py` with actual two-sided real PostgreSQL/FastAPI/built SSR checks; implementer reported local PASS. |
| D — MAJOR | Public Search rendered concrete evidence but omitted the separate qualified design/configuration evidence it already received | Buyer page now displays per-configuration and per-leaf design truth separately, with all five locales; inspector asserts visible output. |
| E — CI BLOCKER | Ruff formatting gate failed on Ubuntu and Windows after A–D amendments | Exactly three changed files reformatted with no semantic delta; final exact-HEAD CI PASS. |

Review sequence: first review on `6402dfdaf11f6e09d4faa97c34a9c2f7cea459c3`, findings A–D comment `6191429785`; first amendment `2f547cb8762099eb85a047fba5250780eec4febb`, A–D content closure and Finding E comment `6192826406`; final format-only amendment `4337463fde821e8fd5da78e1db718f43d776ccc6`, final independent ACCEPT comment `6193304146`. All findings A–E are CLOSED at the exact accepted final head.

## Exact accepted implementation HEAD verification

| Gate | Result |
|---|---|
| GitHub CI run `38742683649` | **SUCCESS**: Ubuntu/Windows quality, PostgreSQL18 DB integration, Astro/Node, dependency audit and historical replay |
| Manufacturer artifact reproducibility run `38742684089` | **SUCCESS**: Ubuntu and Windows |
| Deploy workflow run `38742683559` | **SUCCESS** image builds without push; actual GHCR pushes and production VPS deploy **SKIPPED** |
| Implementer final format amendment | `ruff format --check .`, `ruff check .`, `mypy src` PASS; targeted live PG-backed bridge tests **34 passed** |
| Independent review | **ACCEPT**, PR #349 comment `6193304146` at `4337463fde821e8fd5da78e1db718f43d776ccc6` |
| Owner acceptance | **ACCEPTED**, “0086 akzeptiert” 2026-10-15; recorded as PR #349 comment `6193339724` |

No real external inventory data, broker/owner pilot, commercial launch, paid tier, new provider or production deploy was authorized or performed.

## Decision / Implementation Reconciliation

**DECIDED_AND_IMPLEMENTED:** Seven accepted positive public hard technical native-inventory Search dimensions (`draft_max`, `keel_configuration`, `loa`, `rudder_configuration`, plus first-level `hull_configuration`, `cockpit_position`, `deck_saloon`), shared finite Buyer/Broker typed registry, qualified BoatDesign/NamedVariant and independently claimed current real PhysicalBoat, complete corresponding broker claim editing and private illustrative Search-fit; retained current rights/evidence/freshness/current-public guards. The canonical accepted-count marker is advanced **4 → 7 by this formal acceptance closure**, not implementation/readiness.

**DECIDED_NOT_YET_IMPLEMENTED:** Broader qualified technical fields (beam, displacement, rig, hull material and others), buyer Saved Search/alerts/account persistence, buyer sensitivity outside original criteria, broker export/periodic reports, owner-direct publication, Trust & Safety/privacy/legal, production/provider operational prerequisites. No next slice is automatically selected.

**EXPLICITLY_DEFERRED:** Public search token `LONG_KEEL`, imported-label autoconfirmation, public `OTHER` hull/cockpit or public `NONE` deck query, model/brand/photo-inferred actual-boat facts, independent salon vs protected indoor-helm boolean axes, motorsailer/traditional/commercial certification/type filters, unlimited empty-form browse, commercial influence on organic match/ranking, any real production data/pilot/public release without applicable gate PASS.

**GENUINELY_OPEN:** Which post-0086 capability best accelerates the next real user-visible product proof while satisfying the remaining broker launch, owner-direct/trust/privacy and production/data-operations gates; evidence-backed long-keel taxonomy; optional future independent layout axes. Explicit Owner prioritization and post-0086 reconciliation/readiness are mandatory for the next primary slice.

**CONFLICT_OR_REGRESSION:** All A–E findings CLOSED on accepted exact HEAD; no independently identified remaining code review issue. No claim that known taxonomy gaps or deliberately unavailable buyer sensitivity are implemented.

## Accepted state, gates and next workflow action

```text
PROJECT_STATE_ACCEPTED_SLICE: 0086
PROJECT_STATE_QUEUE_SLICE: 0087 — UNSELECTED (not READY)
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 7
LONG_KEEL_PUBLIC_SEARCH: UNSUPPORTED
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

The public NativeListing and current technical Search paths can already be exercised against synthetic/review data; the first **externally visible real** listing still requires the separate applicable real provider, production data, security/abuse and Production Readiness evidence. Its remaining slice distance is **not determined** by completing three more search filters and must be reassessed before selection; no pilot/public launch is inferred from this acceptance.

SLICE-0086 was explicitly Owner-accepted, independently reviewed and merged before this **separate documentation-only acceptance closure**. The reviewer must examine the exact closure HEAD, verify its atomic count/state/update and observe final closure CI and manufacturer reproducibility before merging this document to canonical main. **The Owner may run `FINISH_SLICE.bat` for `0086` only after that separate closure merge is verified.** The local FINISH has not been observed and is not asserted. No `START_SLICE.bat` for 0087 is released or authorized here.
