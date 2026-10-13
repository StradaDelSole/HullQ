# SLICE-0084 — Broker Pre-publication Technical Search-fit Preview

**ID:** SLICE-0084  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker-first marketplace — truth-preserving technical Search-fit for an owned pre-publication listing  
**Depends on:** Owner-accepted SLICE-0051, -0055, -0056 (deterministic public technical Search and typed evidence), -0053 (professional access), -0067 (private Draft→DRAFT NativeListing promotion), -0069 (publication/current-public eligibility), -0072 (inventory edit), -0082 (explicit canonical BoatDesign association), -0083 (private structured inventory intake), post-0083 Owner-selected Search-fit priority (PR #338).  
**Blocks:** REQ-BROKER-026/MVP-BROKER-010 missing broker-visible representative technical Search-fit explanation before publication.

## Objective

Deliver **one read-only, authorized Broker Workspace Search-fit preview** on an Organization-owned, *promoted but still lifecycle-DRAFT* NativeListing. The broker selects one or both currently accepted technical requirements (`draft_max`, `keel_configuration`) as **clearly synthetic/representative, not real buyer demand** and receives a truthful **CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA** technical result, current structured criterion/configuration/concrete-boat evidence and practical missing-data guidance. Publication readiness is shown as a separate existing status; this preview never publishes or changes evidence.

This is the Owner-selected 0084 capability, not a new Search criterion, personalized ranking, saved Search, missing-data auto-fill, pre-promotion ProfessionalListingDraft evaluator, market demand analytics or public Search eligibility override.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
Single broker workflow: on the existing post-promotion listing editor, run one scoped, read-only technical scenario preview and see *why* the listing does/does not satisfy it. Input/UI/API/one-target evaluation are inseparable. No new user-facing unrelated capability, persisted metric, automatic fix or domain policy.

**VISIBLE-RESULT CHECK:** PASS  
Using disposable synthetic broker Organization/Publisher/MFA credentials, the Owner opens a lifecycle-DRAFT listing in the built Astro SSR inventory editor, chooses a draft limit and/or existing keel value, runs Search-fit, sees each requirement and design/concrete reason, changes a concrete PhysicalBoat claim through the existing editor and sees a freshly evaluated result. An unlinked BoatDesign shows actionable INSUFFICIENT_DATA rather than a match. No public Search result or marketplace mutation is created.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Directly closes the already accepted REQ-BROKER-026 / MVP-BROKER-010 broker→Search bridge; one coherent product-visible improvement ahead of the separately Owner-prioritized subsequent LOA and rudder/skeg criteria. Existing Search truth and owner-direct commercial neutrality are unchanged. Structured import remains a private draft intake; 0084 begins only after ordinary promotion.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current `origin/main` after PR #338 is `a7595ccbde8e61d97581e9667298df6854badd1d`. Public technical Search evaluates ONLY currently public, ACTIVE, design-linked candidates via `list_active_design_linked_listings` and `resolve_current_public_eligibility`; directly calling it for a lifecycle-DRAFT target would silently omit that target. The private Broker Workspace inventory detail already exposes publication readiness, and the 0082 design-association read exposes an explicit resolved/unresolved link, but **no single-listing hypothetical deterministic technical Search-fit result or actionable per-criterion preview exists**. No accepted policy is reopened.

**TRIGGER GATES CHECK:** PASS  
`POST_0051_ARCHITECTURE_RECONCILIATION=PASS`; `PRODUCTION_READINESS_GATE_STATUS=IN_PROGRESS`; `WORKFLOW_REASSESSMENT_STATUS=PASS`; accepted hard technical criterion count exactly **2**. This is an internal/synthetic-only read capability; no real external data, pilot, public launch, provider provisioning, new criterion or Search abstraction trigger is activated. Organic results never depend on payment.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
`MVP-BROKER-010` and `REQ-BROKER-026` are PENDING before implementation; successful accepted closure may advance them, not this readiness. `MVP-BROKER-009`/`REQ-BROKER-022` export, `MVP-BROKER-008`/`REQ-BROKER-028` periodic reports, buyer saved Search/alerts, owner-direct admission/media/leads, buyer email validation/anti-abuse, operator onboarding/privacy/support/legal, runtime/Cloudflare topology and other external Production Readiness work remain mandatory according to their own triggers. Search-fit is highest near-term product leverage because it converts the already implemented Broker→canonical design→Search path into broker-visible diagnostic feedback, without a new prerequisite to internal synthetic testing. Subsequent native criterion expansion remains the Owner's controlling development priority (PR #338 / issue #339).

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS

## Decision / implementation reconciliation

**Accepted records checked:** `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md`; `docs/PROJECT_STATE.md`; `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md` §17; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md` REQ-BROKER-026; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`; `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md`; `docs/PRODUCT_UX_PRINCIPLES.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `docs/slices/SLICE-0082-acceptance-closure.md`; `docs/slices/SLICE-0083-acceptance-closure.md`.
**Production implementation checked:** `src/hullq/application/native_inventory_query.py` (`evaluate_native_inventory_requirements`, `_classify_candidate`, `_build_configuration_evidence`); `src/hullq/search/boat_design_field_bridge.py`, `draft_max_design_bridge.py`, `keel_design_bridge.py`, `configuration_engine.py`, `query_mixed.py`; `src/hullq/persistence/inventory_search.py`; `src/hullq/application/inventory_editing.py` (`get_inventory_edit_detail`, authorization and D22 preflight); `src/hullq/application/design_association.py` (`get_organization_listing_design_association`); `src/hullq/domain/physical_boat_claims.py`; `src/hullq/persistence/physical_boat_claims.py`; `src/hullq/api/app.py` broker edit/design and public Search routes; `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`, `web/src/lib/inventoryEditingApi.ts`, `web/src/lib/designAssociationApi.ts`; accepted current HTTP/PostgreSQL public Search and broker access tests.
**Already implemented / not re-decided:** Two accepted deterministic MUST/AND technical Search criteria; `CONFIRMED_MATCH`/`CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` typed per-criterion/configuration/concrete evidence; publisher current PhysicalBoat claim and cross-Organization conflict qualification; canonical BoatDesign/NamedVariant FieldResolution bridge; publication-readiness/current-public gates; Organization-scoped Broker Workspace MFA access; explicit first BoatDesign association; separate private ProfessionalListingDraft stage.
**Exact remaining gap:** An authorized broker with an owned lifecycle-DRAFT NativeListing has no read-only, one-target *hypothetical* technical fit preview or actionable unknown/nonmatch explanation before publication, because accepted buyer Search enumerates only currently public ACTIVE inventory.
**Accepted-but-unimplemented obligations:** REQ-BROKER-026/MVP-BROKER-010 owned by 0084; broker export and periodic reports, buyer/owner-direct/trust/operations/production work tracked by existing register triggers; LOA/rudder/skeg/long-keel future Search expansion owned by Owner decision PR #338 and tracking issue #339, not 0084.
**Material classifications:** DECIDED_AND_IMPLEMENTED existing kernel, qualified evidence, broker ownership and listing chain; DECIDED_NOT_YET_IMPLEMENTED broker preview and later criteria; EXPLICITLY_DEFERRED hypothetical evaluation of pre-promotion draft, live demand analytics, Search expansion, paid/production activities; GENUINELY_OPEN specific later technical criterion contracts only, not the already selected Search-fit outcome.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  

0084 requires no provider account, real external customer record or production environment. The Production Launch Pack remains NOT_STARTED and Production Readiness IN_PROGRESS; test only on synthetic/disposable data.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  

The marker `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` MUST remain 2. Search-fit is a distinct read-only broker projection of the two accepted criteria, **not** admission of a third criterion, a Search ranking adjustment or a replacement for D29 public eligibility.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** Search truth/provenance and configuration applicability, tenant-scoped unpublished inventory, PUBLISHER authorization/MFA, read-side error/absence differentiation, DRAFT-versus-ACTIVE lifecycle, cross-Organization claim conflicts and potential misleading public Search promises. A fail-open preview could falsely claim a vessel meets a hard requirement or expose a private competitor listing.

**Must-never-change invariant:** For a given currently owned lifecycle-DRAFT NativeListing and accepted requirement input, an 0084 confirmed match is possible **only** if the same accepted BoatDesign/FieldResolution/qualified configuration and independent concrete PhysicalBoat claim predicates would confirm the hard criteria in the public Search truth engine. `UNKNOWN`/missing/unsupported mapping/conflict never becomes a confirmed match. `DRAFT` is evaluated solely as an explicit technical **what-if**; it is NEVER included in public Search or deemed publishable by this diagnostic. Any technical classification is independent of payment, revenue and brand. The preview performs **zero** market/claim/design/lead writes.

**Durable source of truth / loss boundary:** Authoritative Organization+ACTIVE Membership/MFA, NativeListing lifecycle/ownership, MarketEpisode→PhysicalBoat chain, stored BoatDesignRef, immutable current claim revision/readback, other permitted current observations, canonical BoatDesign and qualified FieldResolution all come from the existing PostgreSQL truth stores. The preview is *ephemeral* and never persisted or cached as evidence. There is no new table, migration, scheduled worker, cache, customer-data telemetry or implied verification authority; replacing the API/browser loses only the disposable query and result.

**Retry / replay / partial-failure behavior:** A repeated GET of identical accepted parameters, with unchanged authoritative state, produces the same reasoned technical result; response is read-only. A claim edit, design link, membership revocation, lifecycle transition or FieldResolution change requires a new authoritative evaluation, not a stale browser-cache answer. A concurrent transition DRAFT→ACTIVE or role revocation must not leave a valid-looking prepublication result from an invalid snapshot: recheck lifecycle and authorization on authoritative read, report a typed state-changed/not-previewable outcome and provide a refresh action. A DB/service error never yields a misleading negative or zero result.

**Absence-vs-error / fail-closed behavior:** Unknown/foreign listing IDs share the same non-enumerating not-found outcome. Missing confirmed `boat_design_ref` or missing/unresolved concrete claim produces **INSUFFICIENT_DATA** plus a reason such as `BOATDESIGN_NOT_LINKED`, `CONCRETE_DRAFT_UNCONFIRMED` or `KEEL_CONFIGURATION_UNCONFIRMED`; it never changes the stored design/claim. Design FieldResolution not qualified, variant applicability unresolved, incompatible design/concrete evidence and cross-Organization conflicts retain their true native search classifications/reasons; do not invent a numeric, keel or boat-design equivalence. A *dangling* stored design reference, broken MarketEpisode/PhysicalBoat chain, DB timeout or serialization failure is an **error/integrity fault**, not a confirmed unknown value. An already ACTIVE/WITHDRAWN listing is **NOT_PREVIEWABLE**, not a valid hypothetical DRAFT. Missing session, inactive/foreign Organization access or MFA denial remain distinct from service failures and never serialize another Organization's data. In particular, a missing public-result candidate due solely to D29 not being ACTIVE/eligible is **not** technical CONFIRMED_NON_MATCH.

**Executable adversarial proof:** Real PostgreSQL 18, FastAPI and built Astro SSR with synthetic signed sessions and current broker Organization memberships must prove: (1) a lifecycle-DRAFT, design-linked listing with qualified design and concrete fields produces match/nonmatch/unknown for draft, keel and their conjunction using the same leaf truth/reasons as the accepted Search kernel; (2) previously accepted public Search still excludes it while DRAFT; (3) after controlled existing publish transition, the same truthful facts give an equivalent public technical classification, with independent public-eligibility gating; (4) unlinked BoatDesign and missing/UNKNOWN concrete claims yield actionable INSUFFICIENT_DATA, unsupported long-keel remains unsupported, unresolved variants and contradictory cross-Organization claims never confirm; (5) changed claim or design state refreshes evidence and never rewrites anything through preview; (6) wrong Org/unknown listing, viewer or revoked PUBLISHER, no MFA, malformed/oversize/unsupported scenario inputs, stale lifecycle, missing chain, dangling design and induced DB failure are non-leaking/fail-closed; (7) all responses/private SSR no-store, noindex, escaped and no direct/indirect mutation; (8) existing Search/Publication/Design Association/Inventory tests remain green. Retain executable real API+SSR+DB proof, not only mocked UI/unit tests.

**Slice sizing assessment:** COHERENT  
One bounded broker-visible read flow uses existing authenticated inventory context and qualified kernel. Shared extraction of *already existing* criterion qualification/evaluation helpers is permitted only to prevent a third technical truth path; never refactor unrelated public Search/identity semantics or implement more criteria in this slice. If a second normative engine, broad query redesign or new canonically authoritative yacht fact system seems necessary, stop and split.

## Why this slice exists

Professional inventory import, editing, explicit design association and existing public technical Search are implemented. Brokers still cannot see whether a planned listing will satisfy representative buyer technical constraints **before** activating it, or which missing/uncertain concrete claims block confidence. This is a previously accepted mandatory broker product bridge with a verifiable read-only outcome. After 0084, the Owner-approved priority is to add LOA, then rudder/skeg and other criteria (tracked under issue #339), not to expand this slice opportunistically.

## Controlling artifacts

- Normative: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md` REQ-BROKER-026; `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`; `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md`.
- Owner execution: `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md`, `docs/PRODUCT_EXECUTION_PLAN.md`, `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`, `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md` §17; `docs/PRODUCT_UX_PRINCIPLES.md`.
- Governance: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`, `POST_0051_TRIGGER_GATES.md`, `PRODUCTION_READINESS_GATE.md`, `OVERALL_MVP_CAPABILITY_REGISTER.md`, `BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; accepted owner-direct mixed-supply/Search neutrality.
- Existing code/truth: `src/hullq/application/native_inventory_query.py`, `src/hullq/search/boat_design_field_bridge.py`, `src/hullq/search/configuration_engine.py`, `src/hullq/domain/physical_boat_claims.py`, `src/hullq/application/inventory_editing.py`, `src/hullq/application/design_association.py`, `src/hullq/api/app.py`, existing broker inventory editor/API clients, existing PostgreSQL/Search/authorization tests and relevant accepted 0082/0083 closures.

## In scope

1. **Scoped target:** exactly one authorized Organization-owned NativeListing with lifecycle `DRAFT` (after explicit accepted 0067 promotion); enforce existing signed account/current Organization and PUBLISHER/MFA boundaries. Other organizations' or unknown listing IDs are non-enumerating. Expose no private prepublication information through public endpoints.
2. **Read-only broker scenario:** a bounded input consisting of `draft_max` as accepted positive finite exact SI Decimal metres, `keel_configuration` as accepted public Search enumerated value, or both (MUST/AND). Provide representative default examples or a clear UI form allowing the broker to enter these two existing criteria; always label scenarios `Illustrative only / not actual buyer demand`. Reject empty, malformed, duplicate/ambiguous, excessively long, noncanonical or third-criterion requests with an explicit validation error. No persisted scenario, exposure counter or demand analytics.
3. **Reuse qualified evaluation:** create an **authorized single-target hypothetical DRAFT adapter** that reads one existing listing chain plus canonical BoatDesign, FieldResolution, safe named variants and independent concrete boat claims. Reuse `FieldProjectionSpec`/shared `run_boat_design_configuration_query`, the accepted `MixedAndQuery` kernel, `_build_configuration_evidence` and `_classify_candidate` semantics (extract/reuse bounded pure helpers if necessary) so technical classification is genuinely the same as public native Search; do NOT call public `list_active_design_linked_listings` or D29 public-eligibility filter and misinterpret its DRAFT exclusion as a non-match. No separate truth resolver.
4. **Truthful structured output:** one selected target and exact input requirements, typed aggregate technical status (`CONFIRMED_MATCH`, `CONFIRMED_NON_MATCH`, `INSUFFICIENT_DATA`), existing per-criterion/BoatDesign configuration/PhysicalBoat observation reason/evidence where available, explicit unlinked/unresolved/missing blockers and plain-language next actions (e.g. confirm correct canonical model, confirm actual yacht draft, resolve contradictory claims). Return a distinguishable `NOT_PREVIEWABLE` for non-DRAFT states and service-integrity error for corrupted chain/dangling references; do not return fabricated evidence or show foreign Organization observations.
5. **Publication context kept separate:** existing D22 publication readiness may be displayed next to technical fit, using its current authority. `CONFIRMED_MATCH` answers ONLY the hypothetical technical criteria; it is not an assertion of D22 publishability, D29 eligibility, current ACTIVE status, visibility, expected buyer demand, sale authority or HullQ verification.
6. **Private product surface:** small SSR-safe bounded Search-fit area integrated into the existing Organization-owned inventory edit page, or an adjacent private no-store/noindex broker page linked from it if necessary for clear UX. Typed API client/server result semantics, strict escaped display, clear errors, forward-compatible but bounded response. Zero persistence/schema changes anticipated.
7. **Focused and full proof:** exact same scenario with a controlled synthetic DRAFT versus the accepted public Search after normal publish (eligible conditions separately proven); real FastAPI/PG18/built Astro read and negative tests. Retain a reproducible inspection script or equivalent artifact.

## Explicitly out of scope

- Evaluating pre-promotion `ProfessionalListingDraft` or imported source rows, automatically filling missing fields, suggesting a BoatDesign or linking it, editing/publishing/reconfirming/withdrawing listings, or creating new rights/evidence.
- Changing the two accepted hard technical Search criteria, supporting `LONG_KEEL`/full keel, adding LOA/rudder/skeg, new saved-search/personalized recommendations, public candidate ranking, market demand/usage instrumentation or source-to-buyer attribution.
- Re-evaluating broker eligibility or freshness as a *technical* pass/fail; no automatic D22/D29 override or bypass and no new seller/owner-direct Search advantages.
- Persistent result caches or Search-fit analytics/notifications, cross-Organization comparative browsing, full inventory bulk diagnostics, arbitrary Boolean query authoring, uncontrolled user-supplied field paths, model/spec guessing, historical snapshot reconstruction or new migrations.
- Any real third-party production listing data, external pilot, provider changes or launch.

## Required behavior

### A. Allowed inputs and response boundary

The broker explicitly chooses one or both of the two supported filters; request validation must mirror the public v0.1 semantics, including exact Decimal canonicalization and exact case-sensitive `SEARCH_KEEL_CONFIGURATION_VALUES`. Do not silently accept `LONG_KEEL` because the PhysicalBoat claim enum includes it. Frontend rendering may preserve form values but must never persist them into a broker listing or use them to change existing Search data. Prefer a read-only, bounded GET/API query and private GET SSR form; if POST is necessary, preserve accepted same-origin/CSRF semantics and verify zero writes.

The response must be a single-target typed shape, not a public Search list. It must show an input identifier and per-criterion typed evidence, distinguish design-level versus actual-boat status, and include deterministic actionable missing/conflicting-field descriptions based on known reason codes. An actual `INSUFFICIENT_DATA` state may not be silently converted to `CONFIRMED_NON_MATCH` merely to fit a frontend convenience branch. Unknown and foreign IDs must not reveal presence, title, brand, design, source identity or observed claims.

### B. Single-target evaluation without public admission

Under authenticated read, resolve Organization/listing ownership, lifecycle and exact MarketEpisode→PhysicalBoat. Resolve confirmed design link and evidence only for that boat; read the same current permitted observation snapshot used by native public Search. Treat absent design link as `INSUFFICIENT_DATA` with explicit prerequisite, not a synthetic design result. A stored link to a non-existent canonical design or broken identity chain is a data-integrity error; do not infer design from marketed model text.

For linked canonical design, pass the same supported `FieldProjectionSpec` and `MixedAndQuery` through the shared `run_boat_design_configuration_query` and accepted FieldResolution constraints; use the existing configuration evidence structures. Where design-level result is confirmed match, evaluate concrete claims with the same existing cross-Organization conflict and publisher ownership qualification as public Search. Do not claim confirmed match from design alone. Where design-level result is not confirmed, retain its native result class with design evidence and do not invent concrete evidence (mirrors current accepted public evaluation ordering). Do not expose a foreign Organization's raw claim values or membership identity in the result.

The preview may be technically confirmed despite lifecycle DRAFT or D22 not-ready, but must be labelled hypothetical and **never** inserted into public results or classified D29 ELIGIBLE on that basis. No write whatsoever — including no claim/offer revision, link, eligibility/audit event, lead, or SourceRecordKey mapping.

### C. Authorized read and stale truth

Read permission is Organization-scoped with current ACTIVE matching Membership and PUBLISHER plus MFA; a mere guessed Organization or user-supplied account ID has no standing. Use the existing signed session and same-host browser auth proxy. Preserve 401 no session, 403 MFA, 404 for unknown/foreign/not-currently-authorized Organization/listing (consistent with current private surfaces), typed scenario validation errors and 409/clear `NOT_PREVIEWABLE` for already ACTIVE/WITHDRAWN or changed-state race. A 503/typed service error is not a technical result.

No stale saved preview is authoritative. Evaluate current revisions and lifecycle under a consistent read strategy (single transaction snapshot or equivalent bounded recheck), and return `NOT_PREVIEWABLE` if an interleaved publish/withdraw occurs; avoid a misleading DRAFT-labelled result of two different state moments. This is a **read-only** operation — row locks or transactions may be used for consistency only if justified; cannot mutate or hold heavyweight locks unnecessarily. Explicit time/range/resource bounds required.

### D. Browser usability

The broker can run the preview from the existing edit flow without exposing a public URL, can see the two exact conditions and their units/accepted keel options, and can understand `CONFIRMED_MATCH` versus `CONFIRMED_NON_MATCH` versus `INSUFFICIENT_DATA`. Missing `boat_design_ref` points to the existing manual 0082 design selector; missing draft/keel concrete claims point to the existing 0072 claim editor; after correction the preview re-evaluates. Non-DRAFT listing shows explanation but not a valid Search-fit. The UI must never show `0 matches` after API/DB failure and must not make a scenario appear to represent live buyer usage. Render server-provided untrusted labels and messages as escaped plain text with private `Cache-Control: no-store` and `noindex`.

## Deliverables

- Dedicated bounded server-side Search-fit orchestration (preferred `src/hullq/application/broker_search_fit.py`) reusing the accepted kernel and existing persistence; extracting one common candidate/concrete evidence helper from `native_inventory_query.py` allowed if strictly needed to ensure evaluation parity.
- One Organization/MFA/PUBLISHER-scoped read-only FastAPI route with typed status/errors; tests include 401/403/404/409/service and non-leak behavior.
- Typed Astro SSR/form and `web/src/lib/` client wiring on existing broker inventory editor or adjacent private page.
- Focused unit, real PostgreSQL integration, real-HTTP FastAPI, built Astro SSR, and regression/adversarial tests; retained synthetic proof entrypoint.
- Updated appropriate narrow documentation explaining representative scenario limitations and broker next actions; accepted existing normative Search and count untouched.

## Acceptance criteria

- [ ] Authenticated, current PUBLISHER/MFA actor sees a lifecycle-DRAFT owned NativeListing Search-fit preview on the real Broker Workspace; unauthorized/foreign or pre-promotion private Draft cannot be evaluated.
- [ ] One or both current hard criteria accepted with exact public semantics; invalid/empty/unsupported `LONG_KEEL` inputs fail closed; no third criterion, query alias or ranking change.
- [ ] Fully qualified canonical design + current concrete boat facts classify `CONFIRMED_MATCH`/`CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA` exactly as the accepted public kernel for each criterion alone and mixed MUST/AND, including typed reason/evidence and appropriately limited suggested next actions.
- [ ] Unlinked design, incomplete design FieldResolution/variant, missing/UNKNOWN concrete claim, contradictory foreign observation and unsupported mappings never generate a confirmed match; dangling/broken identity and service faults never masquerade as confirmed missing evidence.
- [ ] Publication readiness is distinguishable from hypothetical technical result; preview of DRAFT remains excluded from current public Search, while a legitimately published/current-eligible version of equivalent synthetic facts yields the same technical truth through the public Search path.
- [ ] Preview causes **zero writes** to listing, lifecycle, offer, PhysicalBoat claims, BoatDesign association, import, provenance, Lead, Search/public-index or event state; retry/refresh/revocation/state-race tested, no stale authoritative frontend answer.
- [ ] Private UI is legible, clearly labels synthetic scenarios, has actionable links to existing claim/design editing, accurately renders errors and has no-store/noindex/escaping protections.
- [ ] Real PostgreSQL 18 + FastAPI + built Astro SSR proof retained and runnable with disposable fixtures; verified foreign Org, revoked membership, no MFA, invalid values, inconsistent chain and service failures, with no side effects.
- [ ] Existing SLICE-0051/-0055/-0056 Search; -0069 Publication; -0072 Inventory; -0082 design association; -0083 import regressions pass; review proves no duplicate Search truth engine.
- [ ] Repository validation, Python ruff/mypy/tests and web tests/check/build pass; exact final implementation HEAD remote Ubuntu/Windows/PG18/web CI + manufacturer reproducibility successful, reviewed independently; Owner acceptance precedes implementation merge and separate closure.
- [ ] Only Owner-accepted implementation closure, if complete, advances `MVP-BROKER-010` and `REQ_BROKER_026_STATUS` from PENDING to IMPLEMENTED. `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` remains **2**; next post-slice reassessment explicitly prioritizes the search expansion wave (LOA first candidate, then rudder/skeg and long keel).

## Expected touch points

`src/hullq/application/native_inventory_query.py` / a small shared evaluation helper; `src/hullq/application/broker_search_fit.py`; `src/hullq/api/app.py`; `web/src/lib/brokerSearchFitApi.ts`; `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro` (or an adjacent private SSR page); `tests/unit/`, `tests/persistence/`, `web/src/lib/__tests__/`; one retained synthetic `scripts/inspect_broker_search_fit.py`. Exact files may change if real code inspection proves a safer existing seam. No Alembic schema or new independent field-resolver path anticipated.

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
# Execute retained REAL PostgreSQL 18 + FastAPI + built Astro SSR
# broker-owned synthetic DRAFT Search-fit flow and adversarial negatives.
# Verify exact implementation HEAD CI, Windows/Linux, PG18 and manufacturer reproducibility.
```

## Stop conditions

- Implementing the preview requires any third current public technical Search criterion, unapproved `LONG_KEEL` mapping, synthetic "real buyer demand" claim, new Search ranking/payment semantics or a second incompatible truth engine.
- Need to guess a BoatDesign identity or PhysicalBoat concrete claim from raw listing/import fields; stop and surface as missing evidence.
- Cannot preserve cross-Organization observation qualification, configuration-specific FieldResolution, DRAFT/non-public separation, or typed error-versus-UNKNOWN distinction.
- A broader refactor, new subscription, cron, migration, new database or external broker production data appears necessary; stop/reassess separate prerequisite, never silently add it.
- True authorized read of a DRAFT requires a concurrency-inconsistent snapshot or non-scoped production Query: address via narrow read strategy, do not expose unpublished data in public Search.
- A mandatory trigger in `POST_0051_TRIGGER_GATES.md`, owner-direct mixed-supply rights/privacy or Production Readiness is newly activated and not PASS; stop and report.
- The one-capability/visible-result test fails or new domain semantics become required without Owner approval.

## Implementation handoff

This file is a **READY contract only once the docs-only readiness PR passes independent exact-HEAD review, GitHub CI/manufacturer reproducibility and merges to `main`**. The Project Owner then runs the normal `START_SLICE.bat` for 0084 in the ordinary HullQ checkout. Claude Code implements only this slice in the isolated worktree/branch, and returns `REVIEW` plus actual exact HEAD and evidence; Claude must not mark DONE, merge or begin 0085. Independent technical review, bounded same-branch amendments, exact-head gates, explicit Owner Acceptance, implementation merge, separately reviewed/merged acceptance closure, then local `FINISH_SLICE.bat` follow in their established order.

The post-0084 expansion priority from PR #338 / issue #339 remains binding; no later slice number or criterion mapping is preapproved by 0084 readiness.
