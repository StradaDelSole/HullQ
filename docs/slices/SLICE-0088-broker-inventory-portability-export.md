# SLICE-0088 — Broker Inventory Portability & Syndication-Ready Export Foundation

**ID:** SLICE-0088  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker-first marketplace — portable authored inventory and independently broker-controlled channels  
**Depends on:** Owner-accepted SLICE-0061/0067/0072/0082/0083/0087, protected Organization/PUBLISHER/MFA broker workspace; D11/D14/D19/D26/D27/D29; post-SLICE-0087 Owner-selected reconciliation.  
**Blocks:** `REQ-BROKER-022`/`MVP-BROKER-009` — brokers cannot retrieve a portable authoritative snapshot of their own HullQ-maintained listing inventory in standard machine-usable files.

## Objective

**One self-service, Organization-authorized, bounded and deterministic broker inventory export**: select authorized private draft and/or promoted NativeListing inventory, preview source field completeness/provenance/loss under a documented target format, then download a correctly serialized, importable representation. **All eight families supported by accepted SLICE-0083 inbound are the declared outbound target:** CSV, TSV, XLSX, legacy XLS, XLSB, ODS, structured JSON, and pinned NautiX **1.4** `adverts.xml`. Genuine target-format correctness is required; file extension renaming and unproven writers are prohibited.

**Owner selection (2026-10-15):** Make HullQ a place where a broker can **first author and manage** its own yacht listings and then **export** to other vendors' import tools, when those vendors actually support and authorize that broker's account/file/feed. This initial slice implements **downloadable portability**, not YachtWorld/BoatWizard publication, generic syndication, live feeds, remote API integration, push acknowledgements or cross-platform synchronization. External-feed access requires a separate actual provider agreement and target-specific mapping. Related evidence: `docs/POST_SLICE_0087_BROKER_EXPORT_REASSESSMENT_2026-10-15.md` and `docs/research/BOATS_GROUP_EU_BROKER_FEATURE_BENCHMARK_2026-10-15.md`.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
A single `Select → Preview/validate → Download` workflow for the broker's own inventory. Eight serializers are alternative outputs of the same typed bounded export snapshot and shared selection/authorization/mapping pipeline, not separate independent products. Batch format conversion is justified by the Owner-approved 0083 import symmetry and portability objective. NautiX is an output serializer only; adding feed distribution, marketing performance reporting or external portal connectors would fail this check.

**VISIBLE-RESULT CHECK:** PASS  
With authorized disposable broker Organization data, Owner can open broker inventory, select own private draft/complete published sample(s), choose CSV/TSV/XLSX/XLS/XLSB/ODS/JSON/NautiX, inspect selected/omitted/unsupported fields and per-listing readiness, download each genuine format, then immediately **re-import** each via the accepted SLICE-0083 parser into a separate disposable test Organization's private drafts (without creating public state). NautiX `adverts.xml` additionally passes the **pinned official v1.4 XSD**, real import parser and target application-specific mandatory field check. Not claim that YachtWorld accepted the upload.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The post-0087 Owner prioritizes `REQ-BROKER-022` no-lock-in portability before further search breadth; accepted broker-first + future owner-direct mixed-supply positioning and D27 publisher immutability remain unchanged. Export remains on the broker's own authorized supply, not a new merchant/feed marketplace or ownership transfer. Completeness guidance supports download truth without a second paid/organic Listing Optimizer or ranking algorithm. No first-real-listing/launch authorization.

**REPOSITORY RECONCILIATION CHECK:** PASS  
D26 and 0083 implement **source import only**, not read/export; the existing broker inventory read `src/hullq/application/broker_inventory_read.py` returns a bounded presentation page, not a complete portable immutable export snapshot. Existing `src/hullq/domain/import_intake.py` enumerates the eight formats but `python-calamine` is a **reader**, not a writer; `xlsxwriter` supports XLSX output only. Existing professional draft/promotion/current NativeListing offer/claims/media are independent authoritative records. D14 limits media reuse rights; D29 ACTIVE != public-eligible; a cross-Organization claimed PhysicalBoat or external broker association is not sufficient authorization to export another Organization's listing. `REQ-BROKER-022`/`MVP-BROKER-009` still PENDING. See section below.

**TRIGGER GATES CHECK:** PASS  
Canonical `POST_0051_ARCHITECTURE_RECONCILIATION=PASS`, `PRODUCTION_READINESS_GATE_STATUS=IN_PROGRESS`, `WORKFLOW_REASSESSMENT_STATUS=PASS`, `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT=9`. No technical hard Search criterion, source projection, current-public truth or organic ranking changes. Use synthetic/disposable data only, no real external provider inventory or live pilot; accepted Gate 2 Production Readiness not bypassed.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
This closes `MVP-BROKER-009` and `REQ-BROKER-022` only **after independently accepted implementation closure**, not through READY docs. Mandatory `MVP-BROKER-008`/`REQ-BROKER-028` periodic engagement reporting remains PENDING and separately required before paid/broad broker launch; Search Demand `REQ-BROKER-025/029` remains volume-triggered, buyer saved search/alerts, owner-direct admission/verification/trust, buyer-contact email verification and production provider/PITR/HA/ops remain open. Relative to continued technical Search, portability is an already-triggered commercial trust/onboarding constraint selected explicitly by the Owner. Production Launch Pack execution is independent and must not be indefinitely displaced by product extras.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/POST_SLICE_0087_BROKER_EXPORT_REASSESSMENT_2026-10-15.md`; accepted 0083/0087 contracts and closures; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D11/D14/D19/D26/D27/D29; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/governance/{DECISION_IMPLEMENTATION_RECONCILIATION,BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER,OVERALL_MVP_CAPABILITY_REGISTER,POST_0051_TRIGGER_GATES,PRODUCTION_READINESS_GATE}.md`; `docs/operations/PRODUCTION_LAUNCH_PACK.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; pinned NautiX 1.4 schema/provenance and research links.  
**Production implementation checked:** `src/hullq/domain/{import_intake,import_parsers,import_spreadsheet,import_nautix,professional_listing_draft}.py`; `src/hullq/application/{import_intake,broker_inventory_read,professional_listing_draft,inventory_editing}.py`; `src/hullq/persistence/{professional_listing_draft,physical_boat_claims,import_intake}.py`; `src/hullq/api/app.py`; existing authorized broker inventory/draft routes; `src/hullq/domain/nautix_schema/NautiX_v1.4.xsd`; `pyproject.toml`/`uv.lock`; accepted real PG18 and built Astro import inspector/tests. No accepted full inventory export serializer or read boundary exists.  
**Already implemented / not re-decided:** Organization-owned/current PUBLISHER/MFA private access; Private ProfessionalListingDraft; promotable/current NativeListing, immutable offer/PhysicalBoat claims, lifecycle and D29; media rights/provenance; D26 bounded multi-format inbound parser/staging; existing public technical Search count 9 and owner-direct rights separation.  
**Exact remaining gap:** A broker cannot selectively and safely **extract its own authoritative complete listings** into any of the documented formats with accurate missing/unsupported-field validation, tenant isolation, immutable snapshot consistency and portable binary/standard file bytes. An import parser is not an export writer.  
**Accepted-but-unimplemented obligations:** `REQ-BROKER-022` and `MVP-BROKER-009` are PENDING for the 0088 export; `REQ-BROKER-028` periodic broker engagement reports and relevant pilot/production/owner-direct/privacy/comms duties remain distinct as registered.  
**Material classifications:** `DECIDED_AND_IMPLEMENTED` authorized draft/promotion/current inventory/claims/media and eight inbound formats; `DECIDED_NOT_YET_IMPLEMENTED` broker-owned multi-format export and explicit portability/field-loss policy; `EXPLICITLY_DEFERRED` YachtWorld upload, external feeds/push/webhooks, bidirectional sync, foreign inventory rights, unlicensed market data, future generalized optimiser/score; `GENUINELY_OPEN` genuine production-safe XLS/XLSB/ODS writer dependency feasibility (must be established by executable review before claiming support), eventual destination-specific field maps/contracts; `CONFLICT_OR_REGRESSION` accepted ADR-0012 PlanetScale vs legacy DigitalOcean-only gate wording is documentary drift targeted in the same readiness PR, not an architecture re-decision.

## Production phase transition check

**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  
**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE

The offline downloaded file is produced only for an already authorized broker using disposable/owned test data; no external site integration, real production data, hosting provider, paid plan, pilot, release state, production notifications or launch-pack phase advances. No external upload occurs on HullQ's behalf.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

`REQ_BROKER_022_STATUS=PENDING`, `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT=9`, `PRODUCTION_LAUNCH_PACK_PHASE=NOT_STARTED`. Existing Search remains unchanged. Status change only in the future Owner-accepted formal implementation closure after proof; not in this READY PR.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** Bulk and binary/XML serializer output can leak private cross-tenant source records, reveal hidden identity, mishandle media rights, fabricate external publication status, trigger CSV/Excel formula injection, corrupt precision/Unicode/time zones, produce false feed compatibility or output a partial silently truncated inventory. Authorization can change during multi-page reads; current offer/claim revisions and listing lifecycle may race. These are identity, rights, snapshot and data-exfiltration failure modes, not superficial file downloads.  
**Must-never-change invariant:** A successful export contains ONLY explicitly selected inventory owned/published by the exact currently authorized Organization and only data that Organization is licensed to redistribute. External publisher IDs are not yacht IDs; import-source keys, foreign Organization inventory, raw applicant/person/support data, private/auth/media object secrets and third-party copyrighted sources are never exported by inference. Each output row and manifest is from one consistent authoritative source snapshot; an unusable/unsupported field or format is never silently represented as complete. An exported NautiX `active` status is **never** manufactured from a private draft or merely ACTIVE-but-not-current-public HullQ listing. An export never changes DB/listing/media/lead state and never claims external submission.  
**Durable source of truth / loss boundary:** PostgreSQL owns organization/membership/authorization, private ProfessionalListingDraft versions, current NativeListing/MarketEpisode/PhysicalBoat identities and claims/offer heads, media placement/rights/approval, source and publisher references. Read-only stream/export snapshot is disposable; replaceable host/cache loss must not create a false acknowledged feed, retained secret, partial mutation or fabricated "exported externally" state. Current state is recomputed/revalidated, no permanent unbounded export blob required.  
**Retry / replay / partial-failure behavior:** An identical authorized request against an unchanged immutable snapshot produces equivalent canonical field values/IDs/order and media selections; timestamps and byte-level ZIP metadata may vary only if documented. Revoked membership/MFA or cross-Organization selection fails with no bytes. Snapshot/concurrency race either locks/reads one consistent transaction view or fails clearly; no mixed old/new listing revisions. Output size/listing count/row/column/cell/decompression and time limits are deterministic. A serializer/IO failure yields explicit error and no partial successful file, successful-export claim or durable side effect; browsers do not treat a partial streamed response as validated artifact.  
**Absence-vs-error / fail-closed behavior:** Missing mandatory NautiX title/boat type/LOA/price/currency/location/status/photo right -> explicit per-row `NOT_EXPORTABLE` with reason, not a false default. Unknown/UNVERIFIED actual-boat field remains omitted or labelled unverified in appropriate generic profiles, not converted to verified truth. Missing NautiX required source ID is not resolved by inventing a vessel identity; stable broker export identity is scoped to owning listing. Source media transient failure/expired link/unknown rights -> reject media or target profile per hard requirement; not silent fallback to quarantine original. Permission/DB/network/parser/writer/corruption errors are failures, not empty inventory. A third-party portal feed or API rejection cannot be presented as successful publication.  
**Executable adversarial proof:** Real disposable PostgreSQL18 + FastAPI + **built Astro SSR** authorized broker `Select→Preview→Download` end-to-end. All eight genuine format bytes: CSV/TSV/XLSX/XLS/XLSB/ODS/JSON/pinned NautiX1.4. Validate file magic/actual content, decode and re-import through 0083 parsers; NautiX official pinned XSD and positive/negative completeness; genuine XLS/XLSB/ODS cross-platform writer/reader roundtrip using real fixtures and no formula execution. Prove two Organizations plus foreign/shared PhysicalBoat, PUBLISHER versus viewer/revoked/MFA and no enumeration, private draft vs promoted ACTIVE/withdrawn/current-public, revision/concurrent update, rights/unsafe media, PII exclusion, malicious CSV/Excel formulas and XML XXE, malformed/oversized selection, pagination overflow, loss/Unknown semantics, failed writer/no partial file, NautiX IDs/status/timezone/Unicode/price/media order. Preserve all prior import, media and lifecycle tests; no database mutations from any preview/download. The inspector MUST be actually executed, not just committed; CI must run full cross-platform tests.  
**Slice sizing assessment:** COHERENT

The eight format adapters are alternate serializations of one immutable Organization-owned, read-only inventory snapshot with one authorization, validation and download lifecycle. By contrast background portal publishing/synchronization, lead delivery or performance reporting have independent acceptance and failure domains and are expressly excluded. **XLS, XLSB, ODS writer feasibility is a hard gate:** do not treat an experimental package or extension rename as proof. Before declaring DONE, establish audited, pinned CPython 3.14-compatible Ubuntu/Windows writer support and independent roundtrip through current reader. If no production-safe writer exists, declare `BLOCKED` with exact dependency/format proof and request an explicit Owner-approved scope amendment; never mark an unsupported format delivered or silently downgrade to six of eight. Unsupported unrelated file families do not broaden scope.

## Post-0087 external v0.3 review — bounded export safety, not extra scope

The Owner-requested 2026-10-16 Claude LLM code review is independently reconciled in docs/POST_SLICE_0087_EXTERNAL_CODE_REVIEW_RECONCILIATION_2026-10-16.md and tracked in GitHub issue #355. It confirms that the existing SLICE-0083 asynchronous import route executes synchronous parsing and DB work on the single Uvicorn API event loop. SLICE-0088 MUST NOT introduce a similar blocking path for XLS/XLSB/ODS/JSON/NautiX serialization or DB snapshot creation. Keep the current request-stream limit where applicable; run expensive work via bounded worker dispatch or a correctly designed sync endpoint, limit concurrent jobs/connections/memory/output bytes, and prove under real HTTP load that other API Search/health/broker calls remain responsive. A bare async-to-sync declaration change to an upload route containing asynchronous request-body iteration is not a valid fix.

This is ONLY a safety proof for the already selected one export workflow, not authority to refactor/repair all existing import, proxy, notification, Cron, organization onboarding, Search or limiter components inside 0088. The external report's CR-01/02/03/07/16/18/19/20 high-risk production gaps remain separately binding pre-external-broker-upload/pilot stop/go conditions and are tracked in issue #355, even if 0088 export is later Owner-accepted. Production Readiness remains IN_PROGRESS and Launch Pack NOT_STARTED; synthetic-only 0088 implementation is not external production permission. Claiming numerical performance before running measurements is forbidden.

## Why this slice exists

Having 0083 inbound-only portability still forces a broker who authors inventory on HullQ to manually reenter it elsewhere. The Owner explicitly chose broad symmetric outbound format support as the next coherent broker-first feature, and `REQ-BROKER-022` is a hard pre-paid/broad-public Broker Workspace commitment. First real broker exposure still depends primarily on production/provider/HA and is not unlocked by this slice. Build the transferable single-source-of-truth **download**, not vendor integrations disguised as file converters.

## Controlling artifacts

- Normative specs: `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`, `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`, `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; pinned `src/hullq/domain/nautix_schema/NautiX_v1.4.xsd`.
- Decisions: D11/D14/D19/D26/D27/D29 in `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`; post-0087 selection and accepted 0083/0087 closures; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md` and accepted authorizations.
- Requirements: `REQ-BROKER-022`/`MVP-BROKER-009`; no change to `REQ-BROKER-028` or search count 9.
- Existing implementation/test references: modules and tests named in reconciliation above and `scripts/inspect_multiformat_broker_import.py`.
- Bounded open question: safe legacy .xls/.xlsb and ODS writer/re-import proof; no unspecified YachtWorld specification.

## In scope

1. **Exact Organization-scoped selection** of authorized draft and promoted listings from existing Broker Workspace, with bounded counts, deterministic order, single snapshot and clear inclusion status; never all tenants or imported foreign third-party owned records by default.
2. **Unified canonical export row** containing only owned-authorized listing offer/draft fields, explicit status, stable per-Organization per-listing export ID, optional broker reference, independent current declared PhysicalBoat facts, approved rights-cleared media derivative URLs only when supported; evidence/UNKNOWN/omitted states preserved or explicitly mapped with an omission report. No export of FieldResolution/raw supplier provenance as personally identifying evidence.
3. **Profile/format preflight** per selected listing: representable fields, required target fields missing, lossy conversions, private-draft exclusion from NautiX active, actual-boat verification qualifiers, exportable counts, row-level errors; explicit confirm/download. A factual checklist is permitted, NOT a standalone generic Listing Optimizer score or commercial ranking recommendation.
4. **Eight genuine writer adapters** behind one selected typed profile: CSV, TSV, XLSX, XLS, XLSB, ODS, structured JSON and NautiX v1.4 XSD-valid `adverts.xml`. The same typed selected rows feed all formats, with no metadata invented to satisfy a format. Stably order columns/rows; enforce max bytes, items, text length/precision/Unicode/timezone consistency. Use conservative, pinned and vetted writer libraries; one shared header/field schema for table outputs, json row objects compatible with 0083, NautiX exact schema projection.
5. **Broker-facing download** with appropriate authorization, no-store/noindex, content-type/disposition, neutral filenames, warnings and safe error handling. Preserve existing broker UI/roles/publication semantics; no external transport. Source->target mapping can be reused for later approved destination adapters without implementing a vendor-specific portal template today.
6. **Retained real vertical proof + security/format regression suite**, demonstrating actual UI and genuine parse/import/XSD roundtrip and fail-closed rights/tenant cases, not only unit serializer tests.

## Explicitly out of scope

Any remote YachtWorld/BoatWizard, boats.com, iNautia or other portal submission/API/feed, credentials, agreement, sync protocol, push delivery, off-platform status reconciliation, seller-contact export or leads/CRM bulk export, new billing tiers, competition pricing feeds/soldboats data, public anonymous endpoint/feed, automatic broker publication, owner-direct export beyond separately governed account rights, periodical report delivery, full Listing Optimizer score, generalized analytics, Search changes/ads, production launch or externally real broker tests.

## Required behavior / technical constraints

- Verify before encoding **current** Organization/Membership/PUBLISHER/MFA permissions, exact listing publisher/owner Organization and source redistribution rights. A shared PhysicalBoatId or source import mapping never confers rights; require current authorization at safe boundary, no cross-tenant existence oracle.
- Make a **single consistent PostgreSQL observation** across draft/offer/current PhysicalBoat claim/media/lifecycle states. Aggregate a deterministic snapshot in bounded memory (or well-defined safe stream with atomic error handling); **never** use the current inventory-page DTO as the authoritative full-field export model.
- Handle full two-way representability carefully: importing an external document and exporting it elsewhere does not mean HullQ owns its external platform media/content redistribution rights; source provenance/permission stays authoritative. No broker-specific platform upload promises and no use of restricted co-brokerage API material.
- Protect spreadsheet values against CSV formula injection and Excel interpretation; serializing an attacker-controlled string starting with `=`, `+`, `-`, `@` or control characters must not execute as a formula or corrupt numeric truth. Decide and test an explicit safe escape/reject policy with per-row warnings and importer roundtrip impact. XLS/XLSB/XLSX/ODS must be genuine binaries, not renamed XLSX or CSV; do not execute LibreOffice shell-outs on user data.
- NautiX 1.4 `adverts.xml` requires actual contract-valid broker account+advert IDs, `type=boat`, `purpose=sale`, correct `modified` and source `status`, valid allowed boat type, mandatory model/LOA/location/price-on-request handling and approved order/URL/checksum media. Incomplete/missing case is explicit rejected row, not invented required values. Validate output against **pinned actual XSD**, then reimport through 0083 `parse_and_validate_nautix`/domain mapper. `inactive` NautiX status for closed/sold/withdrawn must not imply remote withdrawal or mutation; document semantics.
- Distinguish **broker-authored exportable data** from canonical qualified BoatDesign-only facts and D29 current-public eligibility. Qualified design data does NOT become seller assertion; privacy/security/trust/verification claims do not copy into marketing fields.
- A disabled/unavailable writer must have clear blocked/unsupported status; never label a produced file as XLSB unless validated. New writer dependencies require lockfile, license, vulnerability and supply-chain scrutiny, CPython 3.14 and Ubuntu/Windows CI; if genuinely unable to meet an eight-format acceptance criterion, stop for explicit scope amendment rather than manufacture success.
- No new output persistence, cron, ingestion API, webhook or accidental CMS; repeated export has no durable side effects. No external service/account is contacted by the export itself.

## Deliverables

- Domain/application/persistence narrow export read model/selection/authorization/preflight + bounded selected-row snapshot; parsers/builders for actual 8 formats with a finite adapter/profile registry; NautiX v1.4 serializer validated by pinned schema.
- One protected API + broker UI select/preview/download result, including source and missing/loss/rights warnings and per-file totals. No public unauthenticated surfaces or external actions.
- Writer dependencies, reproducibility/format fixtures + contract tests and retained real PG18/FastAPI/**built Astro SSR** inspector; no unverified full-implementation claims.
- Relevant documentation clarifying exported vs imported fields and supported-format truth, tested destination profile limits and applicable required-field checks.

## Acceptance criteria

- [ ] Authorized broker can export self-owned private draft and current promoted listing data using one consistent read-only snapshot; foreign tenant, revoked/VIEWER/un-MFA or shared-PhysicalBoat cross-org access yields no file or existence leak.
- [ ] All eight **genuine** declared-format outputs tested (CSV/TSV/XLSX/XLS/XLSB/ODS/structured JSON/NautiX 1.4), with binary signatures/format sniffing, Unicode/price/decimal correctness and reimport through accepted 0083 parser; no renamed files. Any unproven writer is BLOCKED pending explicit Owner amendment and cannot count PASS.
- [ ] Per-listing field completeness/rights/omission/unsupported conversion report is visible before download, NautiX output passes pinned official schema and real mapped reimport for eligible fixtures, missing mandatory fields fail closed instead of fabricated defaults.
- [ ] Stable per-Organization listing export IDs, canonical order, exact required content / statuses, no cross-Organization authorship or publication claim; private draft NEVER becomes externally active NautiX `advert` and ACTIVE-but-D29-ineligible state never falsely exports as current-public.
- [ ] Formula-injection, malicious XML payload, oversized multi-row selection, bad/ambiguous media rights, stale/concurrent revisions, failed serialize, expired/invalid role/CSRF, unrelated private PII and full DB outage all demonstrate no data leak, no false complete file, no DB mutation.
- [ ] Real disposable **PostgreSQL 18 + FastAPI + built Astro SSR** runs actual authorized select/preview/download, every format re-read by 0083 and NautiX pinned XSD; five-locale public Search, current broker import/edit, media and claims, lead/outcome, production-state regressions green.
- [ ] With real concurrent maximum-sized authorized exports, existing API Search/health/broker calls remain responsive, and serialization, DB admission, output bytes and worker memory/time are bounded and measured (not guessed); no new single-worker event-loop blocking work.
- [ ] Changes stay within one broker export capability. No claims of YachtWorld compatibility absent vendor contract/profile; no live sync, server push, provider activation, external inventory/pilot/public launch, organic Search influence or technical criteria count change.
- [ ] Implementer completes adversarial self-review against invariant list, reports honest local/test/real external verification status, and hands off for independent exact-HEAD review, authoritative same-HEAD CI/repro and explicit Owner acceptance before implementation merge.

## Expected touch points

`src/hullq/domain/inventory_export.py`, `src/hullq/application/inventory_export.py`, `src/hullq/persistence/inventory_export.py` only if justified, `src/hullq/api/app.py`, `web/src/lib/brokerInventoryExportApi.ts`, broker inventory `.astro` and optional explicit exporter page, `src/hullq/domain/nautix_schema/` pinned XSD reuse (do not re-download/change standard), writer/fixture/tests in `tests/{unit,persistence}/` and `web/src/lib/__tests__/`, `scripts/inspect_broker_inventory_export.py`, `pyproject.toml`/`uv.lock` only for vetted writer dependencies. No competing inventory model, new media storage, extra live producer.

## Validation

```bash
uv run ruff check src/hullq tests scripts
uv run ruff format --check src/hullq tests scripts
uv run mypy src
uv run pytest tests/unit/test_import_intake_domain.py tests/unit/test_import_nautix_domain.py
uv run pytest tests/persistence/test_import_intake_api.py tests/persistence/test_broker_inventory_read_api.py
npm run check --prefix web
npm test --prefix web
npm run build --prefix web
# Execute the 0088 retained full-stack inspector with a disposable real PostgreSQL 18,
# actual FastAPI HTTP and the built Astro SSR. Run the exact new script actually created
# in implementation, and retain the command, fixtures and PASS/FAIL evidence.
# CI covers Ubuntu, Windows, PG18 integration, web quality, dependency audit and historical replay.
```

## Stop conditions

- Auth/rights/source ownership are missing or conflicting; cannot read one consistent current Org-scoped snapshot without cross-tenant leakage.
- An accepted target writer cannot safely produce/re-import genuine XLS/XLSB/ODS on CI-supported OS/Python. Do **not** release a weaker six-format implementation silently: report `BLOCKED`, actual feasibility evidence and proposed minimum scope amendment for explicit Owner approval.
- NautiX mandatory fields/assets cannot be derived from already accepted own listing data and would require fabricated values, unlicensed source media or changing the publication/identity model.
- A future YachtWorld feed/contract is treated as already agreed, or the proposed implementation sends data to external providers.
- Binary export writer blocks the single-worker API event loop or cannot limit concurrent CPU/RSS/database demand; report BLOCKED instead of releasing a potentially abusive export path.
- Repository hard gates or current-production phase would be weakened, additional independent product scope appears, or downstream non-export source data becomes mutable during download.
- Any required high-risk adversarial proof is only theoretical rather than actually run, or external CI status is reported as PASS before confirmation.

## Status handoff rule

Claude Code may set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` and must hand back its exact final branch HEAD and concise proof. **It must not mark 0088 DONE**. Independent ChatGPT exact-HEAD review + closed amendments, authoritative GitHub CI/manufacturer, explicit Project Owner acceptance, regular implementation PR merge, separate reviewed acceptance closure and Owner-local `FINISH_SLICE.bat 0088` remain mandatory. No 0089 is selected automatically.

## Required completion report

Use the exact `docs/slices/SLICE_TEMPLATE.md` **Required completion report** structure (Slice / Product execution checks / Changes / Validation / External verification / Findings / Follow-up / Agent declaration). Keep concise, do not misreport remote verification, and use the compact amendment completion report for any review-fix iteration.
