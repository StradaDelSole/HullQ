# SLICE-0083 — Acceptance Closure

**Status:** OWNER_ACCEPTED  
**Slice type:** IMPLEMENTATION / HIGH_RISK MULTI-FORMAT BROKER INVENTORY INTAKE  
**Implementation PR:** #335  
**Accepted exact implementation HEAD:** `30e518605ac5d4c08040c8cb9dfc22dfaac80ddf`  
**Implementation squash-merge on main:** `0dc065309aa73c07fcf8306db2fba8b0b206ac47`  
**Independent exact-head review:** ACCEPT on 2026-10-13 (PR #335, review 5497790941)  
**Project Owner acceptance:** explicitly stated "slice 0083 akzeptiert" on 2026-10-13  
**Primary contract:** `docs/slices/SLICE-0083-multiformat-broker-inventory-intake.md`

## Accepted capability

Organization-scoped, PUBLISHER/MFA/CSRF-authorized multi-format broker inventory intake. Brokers upload CSV (comma/semicolon), TSV, XLSX, XLS, XLSB, ODS, structured JSON or pinned NautiX 1.4 adverts.xml. Each file passes bounded parsing and staged preview/explicit column mapping where applicable, receives per-row validation and requires explicit confirmation to create existing **private ProfessionalListingDrafts**. NautiX is validated against the pinned official 1.4 XSD. No workbook macro/formula execution and no referenced-media network fetching are permitted.

D26 import batches/rows and the durable Organization + ImportSource + SourceRecordKey mapping enforce replay idempotency, ALREADY_IMPORTED/CONFLICT_REVIEW/INVALID outcomes, and a guarded one-time snapshot identity for files without stable row IDs. The importer never automatically creates or publishes a NativeListing, PhysicalBoat, MarketEpisode, BoatDesign association or buyer Search result. Live provider polling/synchronization, automatic withdrawal and active-listing updates remain outside scope.

## Implementation and proof

Implementation areas: `src/hullq/domain/import_intake.py`, `import_parsers.py`, `import_spreadsheet.py`, `import_nautix.py`; `src/hullq/application/import_intake.py`; `src/hullq/persistence/import_intake.py`; `src/hullq/api/app.py`; broker Astro import upload/list/batch pages and typed frontend API; Alembic import batch/source-mapping and snapshot-lineage revisions. The official NautiX 1.4 XSD, provenance, genuine XLSB/ODS fixtures, broker templates, unit/API/PostgreSQL tests, and `scripts/inspect_multiformat_broker_import.py` are retained.

Independent review first returned CHANGES_REQUIRED on branch HEAD `25fb152456fbadd88408e9b405725ddf4ab8e649`. Subsequent focused amendments closed: transaction-time membership/revocation validation; concurrent identity/snapshot lineage; NautiX year and POA correctness; genuine spreadsheet fixtures/formula handling; byte/advert/staging limits; stale confirmation; CSV dialect; retained full-stack evidence; the old hardcoded Alembic head regression; declared-format ZIP/macro bypass; and global retention/concurrent pending admission. Final exact HEAD `30e518605ac5d4c08040c8cb9dfc22dfaac80ddf` was independently accepted.

## Remote exact-HEAD gates

| Gate | Outcome |
|---|---|
| CI run 38329462428 | SUCCESS |
| PostgreSQL 18 full suite | 6,325 passed, 3 skipped; 90.46% coverage (90% minimum) |
| Ubuntu and Windows Python quality, Astro/Node web quality | SUCCESS |
| PostgreSQL historical bootstrap/replay and dependency audit | SUCCESS |
| Manufacturer reproducibility run 38329462377, Ubuntu and Windows | SUCCESS |
| PR Deploy run 38329462316 | API/Web image builds SUCCESS; production push/deploy skipped |

The implementing agent reported local checks, web tests/build and the retained 13-step real PostgreSQL/FastAPI/built-Astro synthetic inspection PASS. The independent reviewer inspected source/proof and verified the remote gates but did not independently rerun the local full-stack inspection. A green Docker build is not evidence of a deployed production system.

## Reconciliation and constraints

**DECIDED_AND_IMPLEMENTED:** D26 structured import of common local broker formats into current private drafts; MVP-BROKER-011 and REQ-BROKER-027 within this bounded intake scope. Auth, source rights, immutable mapping and protected confirmation retained.

**DECIDED_NOT_YET_IMPLEMENTED:** Broker export (MVP-BROKER-009 / REQ-BROKER-022), Search-fit (MVP-BROKER-010 / REQ-BROKER-026), periodic reporting (REQ-BROKER-028), recurring NautiX feed sync and live listing reconciliation. Other mixed-supply, buyer, safety, privacy, legal, operator and communications obligations stay governed by their existing triggers.

**EXPLICITLY_DEFERRED:** Real external broker production data, paid provisioning, pilot/public launch, automatic publication and new technical Search criteria.

**GENUINELY_OPEN:** SLICE-0084 capability is UNSELECTED pending fresh post-0083 Decision/Implementation Reconciliation and reviewed readiness.

**CONFLICT_OR_REGRESSION:** None accepted.

`scripts/ops/purge_expired_import_batches.py` implements a test-proven global cleanup entry point. Actual production cron scheduling, monitoring and live retention proof are still NOT VERIFIED; partially confirmed batches must remain auditable/recoverable. Production Readiness remains IN_PROGRESS and Production Launch Pack NOT_STARTED. No real external production data, external pilot, public launch or new technical Search criterion is authorized by this slice.

## Acceptance boundary

After this separately reviewed and merged docs-only closure: PROJECT_STATE_ACCEPTED_SLICE = 0083; PROJECT_STATE_QUEUE_SLICE = 0084 (UNSELECTED). The Project Owner reported `FINISH_SLICE.bat 0083` was run prematurely after implementation merge; local cleanup was successful, but this must not be mistaken for completion of the later closure merge. Do not run FINISH_SLICE again. Continue only with a fresh post-0083 reassessment after this closure.
