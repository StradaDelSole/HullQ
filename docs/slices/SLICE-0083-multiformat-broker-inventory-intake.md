# SLICE-0083 — Multi-format Broker Inventory Intake (CSV / Excel / JSON / NautiX XML)

**ID:** SLICE-0083  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker-first marketplace — low-friction, professionally credible inventory onboarding  
**Depends on:** Owner-accepted SLICE-0061 (private professional drafts), -0067 (atomic promotion), -0069 (public eligibility), -0072 (inventory edits), -0082 (confirmed design association), D26 accepted import decision and post-0082 reassessment  
**Blocks:** normal broker bulk inventory onboarding without one-off manual retyping for common documented source formats

## Objective

One **Organization-authorized, explicitly confirmed, durable import of a bounded professional inventory file into the *existing private* ProfessionalListingDraft workflow**, with a shared staging/mapping/validation/duplicate/error UI and alternate parsers for the common available structured formats. Native NautiX **1.4** `adverts.xml` support is part of this first importer, not deferred solely for a CSV-only prototype.

**Owner selection, 2026-10-12:** “wenn möglich nautix gleich mit integrieren. bitte alles entsprechend vorbereiten das wir die slice schnellst möglich starten können. grundsätzlich gilt: broker müssen alle gängigen formate nutzen können”. Interpret “all common formats” as the **documented supported-format registry below**, not a physically impossible promise of arbitrary XML, opaque proprietary CRMs or future formats. The adapter boundary must be extensible without a second import truth system.

## User-visible outcome

A permitted broker opens the existing Organization Broker Workspace, uploads a local file in a declared supported type, sees the detected format and source identity, selects an applicable worksheet where needed, maps incoming fields to HullQ's existing strict draft keys, sees every row's **VALID / INVALID / CONFLICT_REVIEW / ALREADY_IMPORTED** status with its reason and unmapped field warnings, explicitly confirms one staged batch, and receives one or more private existing-format `ProfessionalListingDraft` records. They can open/edit those drafts in the **existing UI**; no created row becomes a NativeListing, PhysicalBoat, MarketEpisode, public listing, technical Search match or independently asserted verified BoatDesign association. A repeated upload of the same source data returns the same underlying draft outcome, not duplicates.

### Support matrix — delivered in this slice, not merely planned

| Format | Recognizer + bounded parser | Result | Common interoperability policy |
|---|---|---|---|
| **CSV** `.csv` | UTF-8 (optional BOM), deterministic delimiter/quote/header handling; also document limited legacy encoding/dialect cases when actually tested | explicit mapped draft rows | No silent wrong decimal/locale parsing, formula execution, hidden trimming or Excel reinterpretation |
| **TSV** `.tsv` | tab-separated, same normalized staging vocabulary | same | Tabs/newlines/quoted fields correctly bounded |
| **Excel XLSX** `.xlsx` | explicit worksheet choice, safe typed cells/formula rejection or clear unsupported status | same | formula/macro execution prohibited |
| **Legacy Excel XLS** `.xls` | bounded binary workbook adapter; legacy decoding/precision edge cases are validated or classified | same | supported, not a silent “export it yourself” fallback |
| **Excel Binary XLSB** `.xlsb` | safe bounded workbook adapter | same | explicitly tested or fail closed if unparseable |
| **OpenDocument ODS** `.ods` | bounded spreadsheet adapter | same | standard office suites beyond Excel included |
| **Structured JSON** `.json` | UTF-8 JSON array or documented `{listings:[...]}` profile; strict top-level/row keys | same | no arbitrary remote URL/body fetching |
| **NautiX 1.4 XML** `.xml` | exact recognized namespace/version plus official advert/account structure, schema-aware validation against documented version | same | only authorized owned broker `adverts.xml` uploads, not claims of active Nautic Network partnership |

**Single spreadsheet library candidate:** `python-calamine` 0.7.x, for CPython 3.14, XLS/XLSX/XLSB/ODS; test on Ubuntu/Windows and lock the exact dependency version in repo. Only add a second parser dependency if indispensable to correctly validate the NautiX v1.4 XSD and XML security and it passes focused dependency/CI review; this is a HIGH_RISK multi-format parser slice, not reason for unmanaged additional libraries. Pure-Python CSV/TSV/JSON remain stdlib. Do not use Pandas/LibreOffice shell-outs to parse uploads, and never execute workbook macros or formulae. Reject macro-enabled `.xlsm`/raw ZIP, archive-bombs and unknown formats with an actionable **UNSUPPORTED_FORMAT** result (these are not silently claimed supported).

**Version authority:** `https://nautix.nautic-network.org/` explicitly lists **NautiX 1.4, last modified 9 July 2026**, official XSD `https://nautix.nautic-network.org/v1.4/NautiX.xsd`; `https://www.nautic-network.org/documentation` describes `adverts.xml`, required advert ID/type/purpose/status/modified, account token, inactive/active semantics, source images/checksums. Pin exact schema version and immutable integrity evidence in repo/retained test fixtures; do **not** download mutable XSD or XML from an untrusted URL during production import, accept arbitrary DTD/entity expansion, loosen a failed XSD validity test silently, or claim complete NautiX conformance based solely on simple XML parsing.

**NautiX scope:** import `advert type=boat purpose=sale` records within HullQ's currently accepted *sailboat* supply domain. Other boat types, rentals, moorings, engines/trailers and unrecognized/unsupported combinations receive explicit unsupported per-row explanations; avoid silently coercing them to yachts. `status=inactive` is a **source status**, not HullQ authorization to auto-withdraw a live listing. An inactive existing source mapping is flagged `CONFLICT_REVIEW` (or clear separate NO_CREATE action) and cannot create or mutate a public offer. Media URLs/order/checksums, source descriptions and detail fields beyond the accepted draft schema remain **untrusted staged source evidence** with per-field mapped/unmapped report, not verified yacht claims or public media. NautiX v1.4 optional `accounts.xml`, `status.xml` in development and Push are **not required** for a broker-owned file upload; namespace/account-token/source keys must be supported for an `adverts.xml` containing one or multiple accounts only when current Organization ownership of each account is explicitly attested, otherwise fail closed.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
All parsers return the same bounded normalized staged row and participate in **one** protected Upload→Preview→Map→Validate→Explicit Confirm→Private Draft outcome. File-format adapters aren't independently useful product capabilities; no second draft model or new Search algorithm. Continuous feed sync, provider entitlement, automatic withdrawals, active listing update/reconciliation and media acquisition constitute separate independent capabilities and are explicitly excluded.

**VISIBLE-RESULT CHECK:** PASS  
Owner signs into a disposable authorized broker workspace, imports representative CSV, XLS/XLSX, XLSB, ODS, JSON and NautiX v1.4 files through built Astro SSR UI backed by FastAPI/PostgreSQL 18, sees per-row mapped/errors and confirmed private drafts, opens an imported draft in the accepted editor; immediate exact replay reports ALREADY_IMPORTED, without duplicate records. Negative cases remain visible, with no public listing created.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
D26 explicitly decides `ImportBatchId`, `ImportRowId`, one staging/mapping step, source identity `(Organization + ImportSource + SourceRecordKey)` and the outcomes `CREATE_NEW_DRAFT`, `ALREADY_IMPORTED`, `CONFLICT_REVIEW`, `INVALID`. `REQ-BROKER-027` and `MVP-BROKER-011` require a structured bulk intake before scaled onboarding. The Owner's multi-format selection satisfies this as a single adapter-family intake rather than competing marketplaces. Reuse existing `ProfessionalListingDraft` parser/write/auth and D01–D09/D18/D19; never promote or invent an exact BoatDesign association from a source model name.

**REPOSITORY RECONCILIATION CHECK:** PASS  
After `FINISH_SLICE.bat 0082`, `main` at `48d131f5c39d69494b53c9338841be7ebb2858c1` contains accepted draft create/update, promotion, postpromotion inventory and first confirmed design association, but **no** Organization upload/staged ImportBatch or ImportRow persistence/controller/routes, no common file adapter, and no import-specific idempotent mapping. D26 is an accepted unimplemented decision, not a request to invent import identity semantics.

**TRIGGER GATES CHECK:** PASS  
Existing trigger gate is `PRODUCTION_READINESS_GATE_STATUS=IN_PROGRESS`; buyer/pilot/external production data still NOT_STARTED/NOT_PRESENT. This slice operates with **synthetic disposable** broker data only. Existing accepted technical Search count stays 2; accepted `POST_0051_ARCHITECTURE_RECONCILIATION=PASS`; workflow reassessment `PASS`. No provider provisioning or third-party live source use is authorized.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
`MVP-BROKER-011`/`REQ-BROKER-027` remain PENDING at readiness; if fully implemented and accepted, status may advance only through 0083 closure. `MVP-BROKER-014` 0082 association remains IMPLEMENTED without reopening it. Search-fit (`MVP-BROKER-010`), export (009), periodic reports (008 partial), operator onboarding, actual worker, client-IP/IO/abuse/privacy and external pilot blockers all remain separate and governed by their own trigger. Product-first import has greater immediate broker acquisition leverage than an unrelated infrastructure refactor, but a real external pilot still requires all applicable production gates PASS.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

## Decision / implementation reconciliation

**Accepted records checked:** `docs/POST_SLICE_0082_IMPORT_REASSESSMENT_2026-10-12.md`; `docs/PROJECT_STATE.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/PRODUCT_UX_PRINCIPLES.md` where importer links to marketplace Search; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D01–D09/D18/D19/**D26**/D29; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`; `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `docs/slices/SLICE-0082-acceptance-closure.md`; official NautiX 1.4 pages/XSD listed above.
**Production implementation checked:** `src/hullq/domain/listing_draft_payload.py`, `domain/professional_listing_draft.py`, `application/professional_listing_draft.py`, `persistence/professional_listing_draft.py`, `persistence/professional_listing_promotion.py`, `application/design_association.py`, `persistence/boat_design_association.py`, `src/hullq/api/app.py`, `web/src/pages/broker/organizations/[organization_id]/drafts/index.astro`, current draft/auth/promotion/design-association tests, Alembic head `d8f3b61a9c74`, `pyproject.toml` and `uv.lock`; no structured import batch/row mapper, upload or common adapter exists.
**Already implemented / not re-decided:** Server-owned organization private draft identities; exact authenticated Organization/PUBLISHER/MFA; manual draft payload validation/authoring/version semantics; atomic promotion and no-publication-as-side-effect; 0082 manual first canonical design link; CurrentPublicEligibility and strict two-criterion Search.
**Exact remaining gap:** Broker cannot import a bounded source inventory file in common formats through a reviewable, durable, idempotent staging and mapping process into existing private professional drafts. This single missing user workflow is owned by 0083.
**Accepted-but-unimplemented obligations:** D26 ImportBatch/ImportRow and source mapping, `REQ-BROKER-027`/`MVP-BROKER-011`, now selected for readiness; other open mandatory broker/buyer/privacy/ops/prod/communications work remains under existing trigger gates, not within 0083.
**Material classifications:** `DECIDED_AND_IMPLEMENTED` accepted draft/promotion/association/security/Search; `DECIDED_NOT_YET_IMPLEMENTED` D26 and structured mapping multi-format intake; `EXPLICITLY_DEFERRED` remote continuous feeds, arbitrary proprietary adapters and active inventory reconciliation; `GENUINELY_OPEN` versioned future feed updates/withdrawal policy only when a later recurring-feed slice is selected; `CONFLICT_OR_REGRESSION` NONE observed after 0082 closure.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  

Static file upload implementation in a disposable development/test broker Organization does not begin external data intake/production use and does not provision an external provider. All production launch-pack/provider/data gates remain unchanged.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  

`REQ_BROKER_027_STATUS: PENDING` and `SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED` remain unchanged until implementation passes independent Owner acceptance and closure. Technical native Search criteria remain exactly 2.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** Untrusted binary/text/XML input, third-party source identities and permissions, durable batch/source-row records, replay-safe multi-row draft writes, potential accidental second NativeListing/source truth, exposed private brokerage inventory, media SSRF risk and staging-state integrity. This is one deliberately multi-adapter, single-outcome importer; not a low-risk parser script.

**Must-never-change invariant:** Every confirmed import result is an existing **Organization-owned private ProfessionalListingDraft** (never a NativeListing), backed by one durable ImportRow/source identity. `(Organization, ImportSource, SourceRecordKey)` is an import-identity mapping only, NEVER `broker_listing_reference`, `PhysicalBoatId`, `MarketEpisodeId`, `BoatDesignRef`, HIN, or yacht identity. A repeated or concurrent import of the same mapped source cannot silently create duplicate drafts or modify a promoted/active listing. An unknown, unsupported or ambiguous mapping cannot become verified yacht fact. Promotion/readiness/association are separate existing functions, and a malicious file cannot create a public/searchable listing.

**Durable source of truth / loss boundary:** PostgreSQL owns Organization-scoped `ImportBatchId`, `ImportRowId`, selected source-format/version, filename/content digest, strict per-column mapping/schema version, immutable normalized source key, raw row digest, row classification, validation results, operator-confirmation actor/time and (when created) exact `ProfessionalListingDraftId` via FK/transactionally enforced unique mapping. Keep bounded source evidence for explicit retention or safe disposal; do **not** persist arbitrary unbounded original uploaded spreadsheets, raw third-party personal data, secrets or asset downloads into long-lived DB rows. If staging bytes are ephemeral, durable selected mapping/row outcomes must suffice to explain results and replay already completed operations; a lost upload before confirmation must fail with `STAGING_EXPIRED/REUPLOAD_REQUIRED`, never fabricate rows. No authority resides solely in Astro, memory, browser, temporary disk or client-provided IDs. Server makes all identifiers and status. An aborted/failed row cannot be classified `CREATED` unless its draft and source mapping committed together.

**Retry / replay / partial-failure behavior:** Two-phase server-staged preview then explicit confirmation with bounded per-file size, row count, columns, cell size, worksheets, parser depth/CPU/memory and number of retained staging batches per Organization. Confirm must carry server-issued scoped version/digest/expected batch state; a changed map/changed uploaded file/revoked role/stale browser state causes typed conflict, never silent remapping or a new draft. Use durable unique Organization/source/sourcekey constraints, safe transactional reservation/CAS/row locks and per-row atomicity. Same exact file and same import source/keys with unchanged mapped payload gives ALREADY_IMPORTED and stable draft ID; changed source record after an existing import produces `CONFLICT_REVIEW` with a safe explanation (no overwriting existing draft or promoted inventory); duplicates *within one source file* are detected and cannot silently split into two drafts. Partial success is truthful and safe to resume, with exact row results and zero phantom success; batch-level crash midway returns durable created/failed statuses, not an all-or-nothing fiction. Idempotency is per source record and exact mapping, not merely global SHA of a CSV filename.

**Absence-vs-error / fail-closed behavior:** Empty file/empty worksheet means confirmed zero rows only when parser success; malformed Excel, encrypted/password workbook, formula lacking trustworthy value, malformed NautiX, unknown namespace or version, XML DTD/entities, encoding error, duplicate headers, payload exhaustion, DB timeout, source-account unauthorized, ambiguous mapping, unsupported NautiX advert type/status, untrusted URL, unknown external design or service error never become default empty rows/zero imported. Return actionable `INVALID`/`CONFLICT_REVIEW`/`UNSUPPORTED_FORMAT`/`BATCH_UNAVAILABLE` distinctions. Never trust filename extension or MIME alone; verify magic/content within strict upper bounds. HTML escaping and private no-store/noindex for all raw incoming strings and error text. NautiX `inactive`/missing adverts are **not** authorization to withdraw or delete an existing HullQ listing. An imported media URL is retained as an inert reference only (if rights/retention permit); no HTTP requests/downloads or arbitrary embed execution in 0083.

**Executable adversarial proof:** Real PostgreSQL 18 + FastAPI + built Astro SSR, with signed synthetic broker session and real Organization/MFA/PUBLISHER membership:
1. Upload each supported format family and each distinct spreadsheet extension with a representative truthful fixture, map (manual for CSV/TSV/Excel/JSON; strict NautiX mapping) and confirm one valid private draft; read it in existing draft editor; verify no new PhysicalBoat/MarketEpisode/NativeListing/media or Search candidate.
2. Complete multi-row mixed valid/invalid/duplicate import; verify stable per-row reason, partial commit correctness, retry and atomic row/source-mapping referential integrity after new DB connection and app process restart where feasible.
3. NautiX 1.4 XSD-valid sale sailboat fixture with advert id/account token/modified/source status and POA or normal asking price; reject unsupported type/purpose, inactive as no-create/review, wrong namespace, unknown schema, XXE/DOCTYPE/entity, deep XML bomb, inconsistent/missing required data and multi-account cross-Organization records. Compare parsing against pinned XSD or recognized v1.4 equivalent validation evidence; never silently normalize invalid data to accepted draft fact.
4. CSV formula-injection text, UTF-8 BOM, semicolon dialect and commas in quoted strings; XLS/XLSX/XLSB/ODS formula/macros/encryption/corrupt/archive bomb; JSON duplicate keys/oversize/invalid UTF-8; spreadsheet date/float precision & price currency; wrong field types and missing required response; all fail safely and produce no unauthorized draft or third-party data leakage.
5. Repeated exact import, changed source row with unchanged key, concurrent same-key confirmation, two distinct Organizations same source key, same batch confirmation from two sessions, stale mapping version, malicious client-supplied Org, revoked PUBLISHER mid-commit, no MFA, unknown/foreign batch/source, CSRF/referer/origin failure, failing DB transaction mid-batch, retry after lost response, induced parser/service fault.
6. Built Astro SSR preview and result pages show authoritative row counts and errors; frontend faults never fabricate `0 imported` for unavailable batches, expose a foreign row or bypass existing private-draft authority. Verify old SLICE-0061/0067/0069/0072/0082 tests and full remote Ubuntu/Windows/PostgreSQL/web CI plus reproducibility.
7. Exact imported `broker_listing_reference` is provenance/metadata only. Similar yacht names/boat builder/source records never auto-associate PhysicalBoat/BoatDesign, and a NautiX advert `inactive` or absent row never auto-withdraws/edits published inventory.

**Slice sizing assessment:** COHERENT  
One user-visible protected multi-format upload→preview/map→confirm→private draft capability. A shared parser contract and one source-mapping state machine are indispensable to protect every supported format identically. No feed scheduling/network access or active marketplace reconciliation. If a first attempt needs multiple independently authoritative import/update engines or a provider integration, stop and split rather than change accepted D26/ownership/security rules.

## Why this slice exists

A broker with 30–300 existing listings should not have to re-enter every vessel. Post-0082 HullQ has the honest normal professional path to canonical technical Search, but no structured file intake. An integrated CSV/Excel/JSON/NautiX 1.4 on-ramp advances broker acquisition; subsequent recurring CRM/partner XML/API sync can reuse the **same** explicit source identity, staging validation and truth boundaries without claiming delivery now.

## Controlling artifacts

- `docs/POST_SLICE_0082_IMPORT_REASSESSMENT_2026-10-12.md` plus official NautiX v1.4 published documentation/XSD noted above.
- `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D01–D09/D18/D19/**D26**/D29.
- `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`, `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`, `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`, accepted Draft/Promotion/identity contracts.
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`, `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`, `docs/governance/POST_0051_TRIGGER_GATES.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`.
- `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`, `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`, accepted 0061/0067/0069/0072/0082 closures.
- Current `src/hullq/domain/listing_draft_payload.py`, `domain/professional_listing_draft.py`, `application/professional_listing_draft.py`, `persistence/professional_listing_draft.py`, `persistence/professional_listing_promotion.py`, `application/design_association.py`, `api/app.py`, and Broker Workspace drafts routes.

## In scope

1. Add durable, Organization-scoped ImportSource and `ImportBatchId`/`ImportRowId` with unique normalized source key per D26, bounded staged row/readback and explicit per-row outcome. No duplicative marketplace state. Add only migrations essential for this flow, with canonical single Alembic head and tested upgrade.
2. One authenticated Broker Workspace upload→preview/map/validate→explicit confirm UI and thin typed FastAPI endpoints, existing non-enumerating Org access/MFA/PUBLISHER/CSRF boundaries, no-store/noindex and bounded concurrency/upload content lengths; map against exactly the accepted private ProfessionalListingDraft keys/metadata, not new owner-direct keys or arbitrary physical-boat claim mutations.
3. Supported formats in matrix above, with safe, versioned parsers, deterministic normalization, per-format provenance and per-source field mapping. Workbook worksheet choice and column matching are explicit; no implicit guessing when two columns can mean different authoritative fields. Prices and unit formats must be explicit; no guessed VAT/price/date/model year/concrete-yacht facts. Unsupported fields remain documented as `UNMAPPED` in per-row preview and never secretly dropped with success messaging.
4. NautiX `adverts.xml` v1.4 upload adapter: namespace/schema recognition, safe XML parser (no external network/XXE), required attributes and supported purpose/type, `status=inactive` no-create/review, account token + advert id composite source identity, price/POA and country mapping, media inert references only. The source profile is a broker-attested owned/export-authorized file. Explicitly disallow chaining third-party portal feeds and silently copying provider assets.
5. Atomic imported draft + durable source mapping commit per row, stale batch/version and source replay protection, clear ALREADY_IMPORTED and CONFLICT_REVIEW classification for existing/promoted source records. A new or corrected source file never edits/replaces published inventory without a future accepted reconciliation contract.
6. Document minimum canonical import templates for CSV/TSV/JSON and at least two NautiX v1.4 representative fixtures (valid and fail-closed), per-format limitations/error codes, source rights/retention, and the future provider-specific adapter extension seam. The user can see the exact list of accepted formats on the upload UI.
7. All HIGH_RISK adversarial, real-stack, source/provenance and full regression proof above, with actual fresh PostgreSQL instances, and no assumption that a file extension is safe proof.

## Explicitly out of scope

- Recurring NautiX live feed URLs, Nautic Network membership/partner status, `accounts.xml` cross-portal account ingestion, `status.xml`, NautiX Push/webhooks, OAuth/CRM/DMS APIs, live broker website scraping, general OpenMarine/BoatWizard/YachtWorld proprietary XML/CSV semantic adapters without representative actual format contracts.
- Arbitrary unknown XML/XLSM and macro-enabled workbook execution, PDF/Word/exposé extraction, OCR, ZIP package import, automated third-party media downloads or source image storage/publication; import media lifecycle remains D13–D15/D24 via existing user-controlled media workflow.
- Automatic new BoatDesign creation/association, physical yacht dedup/relink, current NativeListing edit/withdrawal or inactive-feed destructive reconciliation, new Search criteria, public publication, offer/PhysicalBoat revisions outside existing manual edit path, owner-direct uploads.
- Production provider provisioning, real external broker/owner data, live data feed, actual paid broker onboarding or production pilot; accepted Production Readiness gates remain binding.

## Required behavior

1. **Known format / unknown semantics:** format registry must correctly distinguish known parser + known profile, incompatible/no profile, and corrupt format. Include actual supported extensions and truthful HTML labels. No promise that arbitrary JSON/XML uses a universal schema.
2. **Source authority:** Broker Org chooses a bounded `ImportSource` logical namespace; NautiX account token within an authorized uploaded source identifies the export account, not a HullQ Organization role grant. SourceRecordKey is normalized per source and unique within Org/source; IDs may not be dropped/recycled; no mapping to broker reference or yacht identity.
3. **No duplicate truth:** genuine D26 outcomes; same record/same mapped data already imported returns ALREADY_IMPORTED plus the same draft; changed or disputed row returns CONFLICT_REVIEW and never edits promoted/ACTIVE listing. Concurrency and crash proof required.
4. **Validate before mutate:** all rows get precise classification before confirmation; confirmation rechecks exact staged mapping/row status, current PUBLISHER/MFA and Draft invariants, and fails closed on stale/invalid/foreign batch. Partial valid rows are importable with visible count, invalid rows remain untouched; no fake total success.
5. **NautiX version correctness:** validate v1.4 where supported, preserve external advert/account IDs, `modified`, `status`, media metadata only as inert staging, never treat stale or inactive source as a reason to delete, and never invent unsupported boat/feature truths. If XSD-invalid source cannot safely classify its records, fail whole document validation with useful error, not a partial invisible normalization.
6. **Staging retention:** bounded lifetime and privacy-safe deletion for unconfirmed uploads; retained provenance sufficient for auditing accepted imports and resolving ALREADY_IMPORTED. Protect source personal/private notes and untrusted vendor media URLs; no source file exposed to other Organizations.
7. **Future compatibility:** adapters map into a single canonical staged record version; later approved feed synchronizers must reuse the same unique source maps, never reinterpret an existing `source_record_key` or silently change draft identity.

## Deliverables

- `src/hullq/domain/` imported-row model + format profile registry / strict mapper, typed outcomes.
- `src/hullq/persistence/` bounded staging/source/batch/row durable state with migration, unique idempotency constraints, concurrency/audit and private Draft FK.
- `src/hullq/application/` authorized upload/preview/confirm orchestration and format parsers, including real NautiX v1.4 validation.
- `src/hullq/api/app.py` scoped authorized endpoints and `web/src/lib/` typed client plus Broker Workspace `/imports` or similar SSR routes.
- Canonical CSV/TSV/JSON template/docs, representative binary spreadsheet fixtures and NautiX 1.4 fixture/XSD integrity notes, row-level validation help.
- Adversarial unit/persistence/API/web plus one retained real PostgreSQL 18 + FastAPI + built Astro SSR inspection script covering every file type and real private Draft UI; updated package lock if approved spreadsheet/XML parser deps required.

## Acceptance criteria

- [ ] Owner can select and upload **CSV, TSV, XLSX, XLS, XLSB, ODS, JSON and actual NautiX v1.4 XML** from authenticated Broker Workspace and obtain mapped row preview; each format is a tested functional path (not “architecture for later”).
- [ ] Canonical source and schema profile version shown honestly; unsupported proprietary XML, macro-enabled, encrypted, corrupt, oversize or remote-only formats show safe actionable errors with zero mutation.
- [ ] Rows with accepted mapping and explicit authorization create ordinary **private ProfessionalListingDrafts** via current source-of-truth code; same draft can be opened/edited with unchanged manual workflow. Draft mapping NEVER automatically promotes/publishes or associates canonical BoatDesign.
- [ ] Preview per-row status, error explanations, counts and unmapped fields are source-truthful; no invalid/stale/ambiguous source row becomes a guessed value or silent claimed success.
- [ ] D26 `ImportBatchId`, `ImportRowId`, `(Organization, ImportSource, SourceRecordKey)` mapping and four required outcome categories are durable/replay-safe and enforce unique cross-batch source mapping; altered existing source row is conflict, even if source draft was promoted.
- [ ] NautiX sample `adverts.xml` v1.4 passes explicit schema-aware validation; account+advert ID and source modified/status preserved; unsupported/invalid/XXE/DOCTYPE/inactive/malformed fail safely; valid mapped sailing advert produces same private draft path, no asset retrieval or partner-network assumptions.
- [ ] Same-batch two concurrent confirmations, revoked PUBLISHER, missing MFA, foreign Org/source/batch, stale mapping, crash/partial writes, duplicate source keys, changed content, DB/provider read failures and replay all fail closed with real PostgreSQL and HTTP tests.
- [ ] Large file, row/column/cell/worksheet, XML tree, workbook ZIP expansion, parser CPU/memory and staging retention bounds are explicitly enforced and negatively tested; HTML is escaped, no untrusted formula/macro execution, no media SSRF.
- [ ] Existing SLICE-0061/0067/0069/0072/0082 tests PASS; real end-to-end browser/SSR→FastAPI→PostgreSQL→existing private Draft editor PASS, plus no added listing/search/media side effects; no external data.
- [ ] `ruff`, `mypy`, `validate_repository.py`, Python tests, web build/check/tests and exact-HEAD remote Ubuntu/Windows/PostgreSQL 18/Web CI + manufacturer reproducibility PASS; all HIGH_RISK failures adversarially reviewed.
- [ ] If resulting implementation fully satisfies `REQ-BROKER-027`, the accepted implementation closure (not readiness) may mark `REQ_BROKER_027_STATUS` and `MVP-BROKER-011` IMPLEMENTED; `SCALED_BROKER_ONBOARDING_STATUS` stays NOT_STARTED until separately triggered/authorized.

## Validation

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/validate_repository.py
uv run pytest -q tests/unit/ tests/persistence/
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
# Implement and retain a real PostgreSQL 18 + FastAPI + built Astro SSR
# authenticated importer matrix, format negatives, replay and private-draft proof.
# Observe exact implementation HEAD GitHub Ubuntu/Windows/Web/PostgreSQL CI
# and manufacturer artifact reproducibility before Owner acceptance.
```

If the repository provides a different supported test sharding command, use that and report exact commands/results, not invented outcomes. The implementation agent must not claim the above tests are complete before they execute.

## Stop conditions

- A second source-of-truth import/draft model, independent per-format mapper DB or alternative promotion path seems necessary; stop and use the accepted shared staged row/D26 boundary.
- In order to accept a file, import must guess BoatDesign/PhysicalBoat identity, transform source claims into verified yacht configuration or change current promotion/0082 design-association/publish rules.
- NautiX v1.4 schema/content cannot be authenticated/validated safely, dynamic DTD/entity resolving is necessary, or a third-party portal feed/right cannot be attributed to the broker; fail closed rather than claim NautiX support.
- Any supported legacy format cannot be parsed safely within bounded resources; document the exact deficiency and stop for Owner review rather than falsely mark the acceptance matrix complete.
- A recurring network poll/Push, auto-withdraw, editable imported active inventory or cross-Organization automatic source authority is required; classify it as separate feature requiring new policy/readiness.
- Additional file-parser dependencies lack Python 3.14 wheels, reproducible locks, threat controls or bounded parsing; stop or choose a compatible single dependency with independent review.
- Any external real customer inventory, new production provider, paid account or pilot is required to test this slice; prohibit until Production Readiness is separately passed.
- New material policy/architecture conflict with D26, D18/D19, source rights or Organization access; stop and surface the exact governing rule.

## Implementation handoff

Claude Code implements **one** SLICE-0083 in its isolated branch/worktree after the merged READY contract is available to `START_SLICE.bat`. The agent may set the main contract to `**Status:** REVIEW` and its matching `**Status set by this handoff:** \`REVIEW\`` only after all owned changes/tests/evidence are pushed. It does **not** merge, set `DONE`, start 0084 or claim Owner acceptance. Independent exact-HEAD substantive review, amendments on the same branch if needed, exact-HEAD remote CI/manufacturer reproducibility and **explicit Owner acceptance** precede implementation merge; the separately reviewed closure and local `FINISH_SLICE.bat` follow.
