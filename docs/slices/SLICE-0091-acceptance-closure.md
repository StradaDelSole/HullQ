# SLICE-0091 — Owner Acceptance Closure

**Status:** OWNER_ACCEPTED — IMPLEMENTATION; Owner-local FINISH pending  
**Capability:** Explicit Sail+Power Vessel Category Foundation, including source-qualified current design/concrete evidence, safe legacy Sail admission and internal inspectable category resolution  
**Implementation PR:** [#384](https://github.com/StradaDelSole/HullQ/pull/384)  
**Independently reviewed and Owner-accepted branch HEAD:** `ec3fbef167812a18df60b521a8261e3f0bd8cd59`  
**Implementation squash merge on main:** `b707c8ebf00a7e40f849e49f60490327583eb74a`  
**Owner acceptance:** Explicit “akzeptiert” on 2026-10-27 (Europe/Vienna), after the independent exact-HEAD review and all remote CI/manufacturer gates were verified SUCCESS; implementation PR merged after this approval.  
**Controlling contract:** `docs/slices/SLICE-0091-vessel-category-foundation.md`; accepted SLICE-0090 research `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md`; joint Sail+Power decision [#366](https://github.com/StradaDelSole/HullQ/issues/366), ongoing implementation tracker [#372](https://github.com/StradaDelSole/HullQ/issues/372), and pre-external-data STOP [#355](https://github.com/StradaDelSole/HullQ/issues/355).

## Accepted implementation — narrow category foundation only

- `src/hullq/domain/physical_boat_claims.py`, `src/hullq/persistence/physical_boat_claims.py`, `src/hullq/domain/vessel_category.py`: typed positive `SAIL`/`POWER`/`MOTORSAILER` input and `UNKNOWN`/`CONFLICT` resolution; no category inference from marketing labels or unverified attributes. Existing durable Organization-owned immutable concrete claim revision/head model extended additively; absence/explicit UNKNOWN/retraction and current cross-Organization disagreement are not conflated.
- `src/hullq/persistence/boat_design_category.py` plus `alembic/versions/e91a4c7d0f3b_vessel_category_foundation.py`: independent canonical design-side immutable category assertions/current heads, optimistic revision/idempotency/parent-identity protection, source/issuer evidence. Design category write requires a configured `HULLQ_CATALOG_ADMISSION_SECRET`, fails closed when absent/wrong, and uses `hmac.compare_digest`; issuer metadata alone is audit-only, **not independent rights verification** or permission to ingest third-party data.
- `src/hullq/persistence/vessel_category_snapshot.py` and `src/hullq/application/vessel_category_resolution.py`: one PostgreSQL statement collects both design/concrete current source planes within the same statement-MVCC snapshot, including when a caller already has an active `READ COMMITTED` transaction. Typed internal resolution evidence preserves design assertion/issuer/revision plus current Organization assertion/revision/time identity; full cross-Organization evidence is **not** serialized to public users.
- `src/hullq/application/inventory_search.py`, `src/hullq/application/native_inventory_query.py`, `src/hullq/application/broker_search_fit.py`: explicit `POWER`/`MOTORSAILER`/`CONFLICT` cannot yield confirmed Sail match in either pure `draft_max` or shared mixed-criteria Sail funnels, or authorized broker search-fit; legacy no-category UNKNOWN rows retain accepted historical Sail behavior. Bounded `VesselCategoryExclusionEvidence` shows reason without other tenants' identifiers.
- `src/hullq/domain/inventory_edit_request.py`, `src/hullq/application/inventory_editing.py`, `src/hullq/api/app.py`, and `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`: category claim parsing, authorized existing revisioned broker edit/readback/SSR form round-trip, no silent deletion when other claim fields are edited, explicit invalid/stale rejection. No public Power listing/editor or new technical criterion introduced.
- Synthetic unit/real PostgreSQL 18/API/native-query/Search-fit coverage and `scripts/inspect_slice_0091_vessel_category.py` plus `scripts/inspect_slice_0091_vessel_category_editor.py`; the latter uses **authenticated cookie-jar HTTP form POSTs to the built Astro SSR page**, not browser automation or Playwright.

## Independent review and amendments

The independent reviewer checked every pushed exact implementation HEAD and required corrections on the **same** implementation branch:

| Reviewed HEAD | Review result |
|---|---|
| `c28bbdd3b4ed8979816f81e8ab5a902199a9724f` | A–D: pure-draft Sail Search bypass, broker edit gap, missing source-specific resolution evidence and unqualified design issuer |
| `14e0c7837b19e9c7ac9ad82c245e58720e59bd4d` | E–I: real Astro form round-trip, existing-transaction MVCC torn read, self-asserted issuer identifier, Ruff formatting, category-exclusion explanation |
| `01b4b44a952762ac8d0916d7e470ed7cbb4fe9bf` | J: three `mypy` errors and imprecise “real browser” test-evidence description |
| `ec3fbef167812a18df60b521a8261e3f0bd8cd59` | Independent exact-HEAD review **PASS**, A–J closed, ready for explicit Owner acceptance |

The final amendment changed exactly four files (three typed source corrections and inspector wording). No `Any`/type-ignore weakening or extra Search criterion was added. Owner independently accepted the full slice **after** exact-HEAD remote gates were green.

## Exact accepted-HEAD CI and external verification

| Required remote gate | Verified |
|---|---|
| [CI 40495278901](https://github.com/StradaDelSole/HullQ/actions/runs/40495278901) | **SUCCESS**, all six: dependency audit, PostgreSQL 18 DB integration, historical PostgreSQL 18 replay, web Astro/Node quality, Windows quality, Ubuntu quality |
| [Manufacturer artifact reproducibility 40495278884](https://github.com/StradaDelSole/HullQ/actions/runs/40495278884) | **SUCCESS** |
| [Deploy workflow 40495278986](https://github.com/StradaDelSole/HullQ/actions/runs/40495278986) | **SUCCESS** workflow only; **NOT** evidence that production was deployed |

The implementation agent reported local `uv run mypy src`, Ruff format/lint, `scripts/validate_repository.py`, 3,956 unit tests, 84 targeted PostgreSQL 18 tests, the synthetic 0091 category inspector and 11 HTTP SSR editor checks PASS. These are **implementer-reported local runs**; the independent reviewer confirmed exact source diffs, remote gates and test shape, but did not claim a separate local replay.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED:** 0091 category foundation, typed two-plane current assertion/resolution/provenance, conservative all-existing-Sail-path admission, authorized broker form round-trip; all preexisting **nine** Sail technical hard criteria, shared MUST/AND evaluator and D29 publication checks preserved. A category admission predicate **does not count as** a tenth technical criterion.

**DECIDED_NOT_YET_IMPLEMENTED:** Real independent Power technical Search and Buyer/Broker specialist parity; design-unresolved native technical Search admission, source-rights-qualified installed equipment/operating-condition facts and Power NautiX import/export. Motorsailer future dual-domain criterion matching policy remains GENUINELY OPEN.

**EXPLICITLY DEFERRED / STOP:** External Sail+Power product pilot and public joint launch per [#366](https://github.com/StradaDelSole/HullQ/issues/366); external-data/source rights and pre-real-upload safety gate [#355](https://github.com/StradaDelSole/HullQ/issues/355); real third-party catalog/source admission, buyer Saved Search/alerts, owner-direct seller trust, operational provider rollout and production Launch Pack. Issue #372 remains OPEN for later slices. No external broker/customer production data was added and no source acquisition permission is implied.

## State transition / Owner local action

```text
PROJECT_STATE_ACCEPTED_SLICE: 0091
PROJECT_STATE_QUEUE_SLICE: 0092 — NOT SELECTED / NOT READY
SLICE_0091_TYPE: IMPLEMENTATION
SLICE_0091_RESULT: OWNER_ACCEPTED_VESSEL_CATEGORY_FOUNDATION
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 9
PRODUCTION_READINESS_GATE_STATUS: IN_PROGRESS
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED
```

This is a separate **docs-only** acceptance closure (not another product implementation), to be independently reviewed and merged after its **own** exact-HEAD CI/manufacturer reproducibility. Only after that closure merge does the Owner run unchanged local `FINISH_SLICE.bat` selecting `0091`. The subsequent slice is **not selected**; no new implementation may auto-start.
