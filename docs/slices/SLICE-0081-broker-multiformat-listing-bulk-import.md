# SLICE-0081 — Broker Multi-Format Listing Bulk Import

**ID:** SLICE-0081
**Type:** IMPLEMENTATION
**Status:** READY
**Stage:** broker product expansion / efficient inventory onboarding
**Depends on:** SLICE-0080 Owner-accepted/DONE; existing SLICE-0061/0067/0072 professional draft, promotion and inventory flows; accepted 2026-10-12 Owner direction to prioritize building missing product capabilities over further provider purchasing/provisioning
**Blocks:** REQ-BROKER-027 scaled broker onboarding commitment, subject to independently verified implementation and acceptance

## Objective

One authorized professional broker can upload an existing inventory file in CSV, XLSX, JSON or XML format, review a bounded row-by-row field mapping and validation preview, and explicitly import selected valid rows as ordinary Organization-owned `ProfessionalListingDraft` records through HullQ's existing draft semantics — without creating marketplace identities, automatically publishing, or overwriting existing work.

## Plain-language capability

A brokerage with dozens of existing listings does **not** retype every boat by hand. In its own Broker Workspace the user uploads a file, selects how source columns map to the accepted draft fields, sees which rows can be imported and which need correction, confirms the import, and gets direct links to the created drafts. The same workflow supports four common file shapes. Imported drafts subsequently follow the existing human-reviewed edit → promotion → media → publish path.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS
One end-to-end user-visible outcome: multi-format inventory-file onboarding into professional draft state. Format-specific decoders, canonical field mapping, bounded durable preview/commit, API/browser surfaces and proof are inseparable layers of this import outcome; there is no general feed-sync, Search, identity-reconciliation or publication subsystem in scope.

**VISIBLE-RESULT CHECK:** PASS
The Owner can upload representative CSV, XLSX, JSON and XML files in the broker UI, see identical normalized rows and actionable row errors, confirm a small valid subset and open the resulting drafts. Re-import and failure demonstrations prove no accidental duplicates or partial marketplace publication.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS
`docs/PRODUCT_EXECUTION_PLAN.md` and `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md` explicitly favor structured import after the now-implemented coherent broker create→publish→lead→operate path. Vertical cross-layer sizing is permitted. No new Search criterion, no new production provider and no external production data.

**REPOSITORY RECONCILIATION CHECK:** PASS
The `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` identifies `MVP-BROKER-011` as PENDING and the Mandatory Capability Register identifies `REQ-BROKER-027` as PENDING. `src/hullq/persistence/importer.py` imports **research evidence**, while `identity_importer.py` admits **canonical research identities**; neither is an Organization-authorized broker-listing file uploader. Existing `professional_listing_draft.py` already supplies a validated nine-key payload, Organization scoping, optimistic version and atomic draft creation; the API and Astro broker draft pages provide the browser/auth foundation. No equivalent CSV/XLSX/JSON/XML staging, mapping, preview and batch draft-creation surface was found.

**TRIGGER GATES CHECK:** PASS
Structured import is mandatory **before scaled broker onboarding**, but not a prerequisite to first bounded broker pilot. This is a development capability with synthetic/internal fixtures only; production gate remains IN_PROGRESS. No production pilot/data/launch or paid plan is enabled.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS
Selected entry: `MVP-BROKER-011` / `REQ-BROKER-027`. Other PENDING items (broker export, Search-fit, periodic reporting; owner-direct publishing/media/leads; buyer accounts/alerts; abuse/trust, support, legal, admin and email) remain PENDING under their current trigger rules. No new entries are asserted IMPLEMENTED at readiness. Structured inventory import offers high acquisition value now that the underlying professional lifecycle works; it does not waive higher-risk safety gates at actual launch.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0080_REASSESSMENT_2026-10-09.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md` REQ-BROKER-027; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.
**Production implementation checked:** `src/hullq/persistence/professional_listing_draft.py`; `src/hullq/application/professional_listing_draft.py`; `src/hullq/domain/listing_draft_payload.py`; `src/hullq/api/app.py`; `web/src/lib/professionalDraftApi.ts`; `web/src/pages/broker/organizations/[organization_id]/drafts/index.astro`; existing research/canonical `src/hullq/persistence/importer.py` and `identity_importer.py`; draft/promotion/media ownership flow described by accepted SLICE-0061/0067/0068/0069/0072.
**Already implemented / not re-decided:** Professional draft creation/update, `owner_organization_id` and role/MFA requirements, broker reference and description, nine-key canonical partial draft payload, distinct UNKNOWN/omitted/value build-year response, optimistic versioning, stable professional promotion → marketplace identities, media/public eligibility, native listing editing. No source row or external broker identifier becomes BoatDesign/PhysicalBoat/MarketEpisode/NativeListing identity.
**Exact remaining gap:** Authorized broker cannot upload structured multi-listing files, map their source columns to the canonical draft keys, review bounded validation errors or commit a batch of independent ordinary drafts from one confirmation.
**Accepted-but-unimplemented obligations:** `REQ-BROKER-027` /`MVP-BROKER-011` through this slice; separate still-pending broker portability/export `REQ-BROKER-022`, Search-fit `026`, scheduled reporting `028`, Owner-Direct and buyer capabilities remain owned by future capability selection at their existing triggers. Future auto-feed sync and website integration are explicitly not assumed.
**Material classifications:** `DECIDED_AND_IMPLEMENTED` existing professional draft→promotion→publish architecture and bounded broker workspace; `DECIDED_NOT_YET_IMPLEMENTED` multi-format bulk import / REQ-BROKER-027; `EXPLICITLY_DEFERRED` provider provisioning, live feeds/API integrations, media-in-file, owner-direct import, new identity reconciliation, bulk active-listing edits, auto-publication and all other register items under their triggers; `CONFLICT_OR_REGRESSION` the historical post-0080 **priority selection** for production account work is superseded **only as an execution priority** by the Owner's 2026-10-12 instruction to build product capabilities now, not by an assertion that production safety gates are complete.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE
**Launch-pack phase after this slice:** NOT_APPLICABLE
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE

This is repository implementation with local/synthetic fixtures. No provider account/DB/VPS is provisioned, no real external user data entered, and no operational production phase is advanced. `PRODUCTION_LAUNCH_PACK_PHASE` stays `NOT_STARTED`. The Phase-1 provider work is deferred in priority, **not declared complete or canceled**.

## Trigger gates

**Production readiness gate:** IN_PROGRESS
**Adds technical native Search criterion:** NO
**Technical Search criterion ordinal:** NOT_APPLICABLE
**Second-criterion bridge comparison:** NOT_APPLICABLE
**Third-copy abstraction guard:** NOT_APPLICABLE
**Workflow reassessment status:** PASS

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK
**Why this classification:** Untrusted files, authenticated multi-tenant bulk mutation, durable staging and retry/replay can create duplicate or cross-tenant draft records or silently turn guessed imported values into durable asserted truth.
**Must-never-change invariant:** Import never creates/edits PhysicalBoat, MarketEpisode, NativeListing, claims, media, publication or Search truth. Only an explicit authorized broker confirmation of strictly validated rows creates fresh `ProfessionalListingDraft` records with canonical accepted fields. An unsupported, missing, ambiguous, blank, formula, unparsed or error-bearing field never becomes an asserted known value by inference; omission remains omission and explicit UNKNOWN retains its accepted structure. Upload/preview alone never creates a draft.
**Durable source of truth / loss boundary:** PostgreSQL owns Organization-scoped import-batch identity, immutable normalized preview/mapping/row digest, per-row validation/selection and committed row→draft mapping. Application memory, temp uploads, local browser storage and replaceable host are not authority. No raw source files, credentials or personal-data-bearing import payloads go to CI logs. Staged data have a bounded retention/cleanup policy; successful draft data persist under their existing authority.
**Retry / replay / partial-failure behavior:** Every commit has stable Organization+batch and row identity and is idempotent; exact repeated commit returns the same draft IDs with no extra rows. Reupload of byte-identical content within the same Organization is detected as an existing batch rather than silently duplicating drafts; content changes require new preview/confirmation. A batch confirmation is atomic for its selected valid row set: zero partial draft creations on parse/validation/DB/authorization failure. Concurrent confirms cannot create duplicate drafts; stale previews/mapping/version/selection fail explicitly without rewriting already created drafts. Different Organizations never share staging, source reference, idempotency state or created draft.
**Absence-vs-error / fail-closed behavior:** Foreign and nonexistent import batch are indistinguishable for ordinary access; missing/invalid MFA, Publisher role, selected source columns, corrupt/oversized payload, unsupported encoding, invalid JSON/XML/XLSX/CSV, DB timeout or staging-state lookup error never fall back to an empty/clean preview or permit commit. Source `broker_listing_reference` is not a global boat identity; repeated references and potential existing Organization duplicates require visible warning/error and **no implicit upsert, merge or rewrite**.
**Executable adversarial proof:** Exercise all four format decoders with equivalent rows and malformed/edge fixtures; unauthenticated/foreign-org/non-publisher/MFA failures; CSV formula-injection and encoding variants; XLSX ZIP expansion limits, formulas, hidden sheets/external links and large workbook; XML DTD/entity/oversized nesting/invalid encoding; JSON nesting/duplicate keys and sizes; source header collisions/duplicate mapped target columns; omitted vs UNKNOWN vs asserted values; malicious strings; row/batch/file size bounds; stale mapping/selection, duplicate upload, concurrent double-commit and partial DB failure with no partial drafts; direct DB proof of zero marketplace identities/claims/public truth; process restart before commit and exact committed draft-id replay; no credentials or raw uploaded content in logs.
**Slice sizing assessment:** COHERENT — one normalized import-preview-confirm pipeline with four bounded parsing adapters; no independent feed scheduler, marketplace-publication mechanism or second product/domain policy. If implementation reveals a separate identity/dedup authority, source-credential feed ingestion, or a second external dependency/framework is unavoidable, stop and propose a split rather than broadening the slice.

## Why this slice exists

The 2026-10-09 post-0080 reconciliation prioritized Production Launch Pack Phase 1 because a **small broker-only pilot** has a technically coherent core path. On 2026-10-12 the Project Owner explicitly redirected effort to substantial missing **product** capability before further provider setup, citing multi-format listing upload and incomplete broker/private-seller functionality. This is a legitimate later prioritization decision, not a reversal of Phase-1 or security gates. Broker bulk import is specifically accepted in the September broker-execution focus, remains PENDING in the registers, and removes manual inventory-entry friction for acquiring brokerage supply.

## Controlling artifacts

- Normative: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md` REQ-BROKER-027; `src/hullq/domain/listing_draft_payload.py` accepted finite nine-key input; `src/hullq/domain/professional_listing_draft.py` accepted professional request shape.
- Product/execution: `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`.
- Gates: `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`.
- Current implementation: `src/hullq/persistence/professional_listing_draft.py`; `src/hullq/application/professional_listing_draft.py`; `src/hullq/domain/listing_draft_payload.py`; `src/hullq/api/app.py`; `web/src/lib/professionalDraftApi.ts`; `web/src/pages/broker/organizations/[organization_id]/drafts/index.astro`; `alembic/versions/`; existing draft/API/browser/ownership tests.

## In scope

1. Organization-scoped Broker Workspace upload entry point and accessible import preview/results with actionable row errors, explicit confirmation and links to resulting drafts. Keep ordinary create/edit/lead workflows unchanged.
2. Four explicit supported input contracts:
   - CSV (UTF-8 with optional BOM; explicit delimiter choice for comma/semicolon/tab), one header row;
   - XLSX (single explicitly selected visible worksheet; text/number cells only, no macros or formula evaluation);
   - JSON (flat array of records or `{"listings":[...]}`, bounded scalar fields, no duplicate object keys);
   - XML (documented root `<listings>` with direct `<listing>` children and simple scalar child elements; no DTD/entities/external resources).
   Legacy XLS, arbitrary website exports, PDF, untrusted URLs and vendor-specific nested feeds are not silently claimed as supported.
3. Canonical import normalization and deliberate source-column→target mapping for `broker_listing_reference`, `broker_description` and the existing nine dotted draft-payload keys. Duplicated target mappings, unknown mapped targets and invalid values fail preview; unmapped source fields are reported, never treated as imported.
4. Strict upload/content/row/column/decompressed-data/cell/depth bounds, schema validation using existing professional-draft validators, useful per-row error report and zero mutation in preview.
5. Durable staged preview with digest, bounded TTL, selected-row confirmation, atomic/idempotent batch→fresh professional draft persistence, owner/role/MFA checks and no implicit upsert. A successful import may yield not-yet-promotion-ready drafts, which the broker edits normally.
6. One bounded XLSX reading dependency **at most**, only if repository-supported; no automatic scheduler or separate feed framework. CSV/JSON/XML use bounded standard-library decoding with explicit XML entity/DTD rejection.
7. Focused unit/contract, real PostgreSQL persistence/concurrency/migration, API auth/CSRF/rate-limit, and built Astro workflow proofs; follow the existing reduced-context exact-head CI discipline.

## Explicitly out of scope

- Automatic publication, promotion, active-inventory overwrite, seller-direct import, cross-Organization merge/dedup, boat-design inference, media URL fetching, downloading/uploading broker website files, scraping, continuous XML/feed synchronization, proprietary YachtWorld/CRM connector, purchase of external services or real external production data.
- Making broker export/portability (REQ-BROKER-022) or periodic reporting (REQ-BROKER-028) look implemented through an import feature.
- Independent new dashboard capability, global style redesign, payments, admin support tools, public launch or production phase advancement. These remain candidate subsequent product slices.

## Required behavior

- Upload only under an authenticated authorized Organization broker publisher using existing MFA/step-up and CSRF semantics. Bound upload before decoding; validate content structure (not extension alone), reject disguised/unsupported payloads, ZIP bombs, macro/external links, active content and XML entities. No formula execution, outbound fetch or arbitrary filesystem writes.
- Preview is read-only with respect to professional and marketplace objects. It shows parsed row number, the canonical mapping, mapped values/missing values, validation reasons, duplicate source references and an explicit count of unsupported fields.
- Map build-year response as omitted vs explicit UNKNOWN vs value assertion; never collapse absence to unknown or infer technical configuration facts. Never equate import source reference with HullQ authoritative boat identities.
- Confirm only validated explicitly selected rows, preserving the existing professional draft request parsing and authorization semantics; preserve `broker_listing_reference` and `broker_description` where mapped. The batch commit is durable, transactional and idempotent under concurrent requests.
- Successful preview/commit explains that drafts are **not public** and must pass existing edit/promotion/publication/media readiness. Return created draft links plus stable import batch status. Never store raw upload as public media or interpret embedded links as permission to fetch assets.
- Implement user-visible bounded error/retry behavior and cleanup of abandoned staged rows without erasing already accepted drafts or their source association.

## Deliverables

- Bounded multi-format decoder + canonical normalized mapping/validation module; tests across all supported formats.
- Migration(s), Organization-scoped durable staging, immutable batch/row provenance and committed draft-ID mapping; service/API endpoints for preview, status and confirm.
- Broker Workspace upload/field-mapping/preview/confirm/result surfaces; accessible failure and validation messages.
- Retained real PostgreSQL + FastAPI + built Astro proof, including duplicate/replay/authorization/zero-publication assertions. No real external provider use.

## Acceptance criteria

- [ ] One signed-in authorized broker can upload each of four fixtures, map fields, inspect identical normalized previews and import multiple chosen rows into editable Organization-owned professional drafts.
- [ ] Unmapped/invalid/colliding fields and malformed source rows display actionable row/column diagnostics; blank/omitted/UNKNOWN/value assertions remain distinct; no guessed values become canonical facts.
- [ ] Upload-only and preview have zero ProfessionalListingDraft/PhysicalBoat/MarketEpisode/NativeListing mutations; confirm creates **only** canonical editable drafts.
- [ ] No unauthorized user, unverified privileged actor, foreign Organization or stale/nonexistent batch can preview/commit or infer another tenant's imported content.
- [ ] Bounded parse/resource defenses proven against CSV/JSON/XML/XLSX hostile fixtures; no SSRF, unsafe XML entity, formula execution, outbound media acquisition or unbounded local storage.
- [ ] Identical reupload and duplicate/replayed/concurrent confirmations do not create duplicate drafts; transaction, restart and forced-failure tests prove atomicity and durable draft mapping.
- [ ] Existing ordinary professional draft authoring/promotion/publish/media/lead, owner-direct isolation, Search truth and broker lifecycle tests remain green.
- [ ] Browser user journey and real PostgreSQL + FastAPI retained proof PASS; exact-head GitHub CI/reproducibility PASS; independent exact-HEAD implementation review and explicit Owner acceptance recorded **before merge**.
- [ ] No Production Readiness/Launch Pack marker, provider spending or external production-data/pilot status changed.

## Expected touch points

`src/hullq/application/`, `src/hullq/persistence/` (new import modules using existing professional draft persistence), `src/hullq/domain/` only when necessary for canonical parsing, `src/hullq/api/app.py`, `alembic/versions/`, `web/src/lib/`, `web/src/pages/broker/organizations/[organization_id]/`, `tests/`, `web/src/lib/__tests__/`, `scripts/inspect_*.py`, and relevant validation tooling. Keep changes localized; do not modify unrelated marketplace semantics.

## Validation

- Python: `uv run pytest -q <affected import/draft/API tests>` (replace placeholder with real path names in execution report); real PostgreSQL via the repository's existing database-test diagnostic helper, migration up/down and parallel confirm proof.
- Web: `npm test --prefix web -- <affected import/broker tests>` and `npm run build --prefix web` where compatible with existing scripts.
- Execute retained integration proof on actual locally provisioned PostgreSQL 18 + FastAPI + built Astro, using only controlled test files/accounts; capture compact failure/success facts, not credentials or imported raw content.
- Existing repository validation scripts + exact pushed-HEAD CI and manufacturer-artifact reproducibility are the authoritative regression gates.
- If exact commands differ from current repository scripts, use the **actual** commands rather than claiming unrun commands passed.

## Stop conditions

Stop on a material contradiction in the accepted professional draft/identity contracts; if implementation needs new import-triggered marketplace identity allocation; if XML/vendor feed support would require broad source-sync policy, unaccepted licensing/privacy assumptions, a second independent external dependency or background worker; if format parsing cannot be safely bounded; or if a high-risk concurrency/integrity invariant cannot be proven. Return a precise smallest split/decision proposal, not a fail-open shortcut.

**Handoff:** readiness must be independently reviewed and merged before `START_SLICE.bat`; implementation is owned by the Claude Code slice worktree and receives independent exact-HEAD implementation review. This document does not itself authorize purchase, production data or skip the Owner acceptance/closure procedure.
