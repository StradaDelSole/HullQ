# SLICE-0082 — Broker Listing → Canonical BoatDesign Association

**ID:** SLICE-0082  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker-first marketplace — connect actual broker inventory to accepted technical buyer Search  
**Depends on:** Owner-accepted SLICE-0067 (draft promotion), -0069 (publication/current-public eligibility), -0072 (inventory editing), -0081 (workspace), accepted identity/Search contracts and post-0081 reassessment  
**Blocks:** real professional listing inventory entering accepted design-dependent native technical Search without script-seeded design associations

## Objective

Allow an authorized broker to make **one explicitly confirmed, durable and auditable first-time association** of an existing Organization-controlled NativeListing's underlying PhysicalBoat with an existing canonical BoatDesign, including listings previously promoted without a design link. Thereafter the ordinary accepted two-criterion Search can discover a genuinely eligible broker-created listing **without artificial direct database association or special-case Search logic**.

## Plain-language capability

A broker creates and promotes a listing normally. On the authorized listing inventory/editor screen the broker can search a bounded set of **existing** HullQ BoatDesign identities, inspect the exact model identity, explicitly confirm the correct design, and save that identity association with audit evidence. If the broker cannot confirm a design, the listing stays **Unresolved** (still publishable when independently publication-ready, but cannot appear as a confirmed technical design match). If an active listing's required concrete-yacht evidence and canonical design/configuration criteria actually satisfy the buyer's search, its exact NativeListing appears in the existing technical Search. The broker sees whether the link is established or absent and no design's technical facts are silently copied into yacht claims.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One inseparable end-user outcome: link already-created authorized professional marketplace inventory to a verified existing canonical design so the existing native technical Search can evaluate it. A bounded design selector, guarded mutation, status readback, lineage/audit and one end-to-end Search proof are necessary layers of the same capability. No new general editor, Search criterion, import engine, bulk catalog ingestion, recommendation/auto-resolution, broad operator admin, notification service or runtime hardening.

**VISIBLE-RESULT CHECK:** PASS  
Using the built Astro Broker Workspace backed by real disposable PostgreSQL and FastAPI, the Owner can promote a standard professional draft, explicitly associate its NativeListing with an existing canonical BoatDesign through the inventory screen, independently complete required publication and concrete facts through existing controls, and see that exact active listing in ordinary technical Search. Refresh proves persisted association. Existing design-linked listings remain correct.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted broker-first vertical is Broker→Draft→NativeListing→Buyer technical Search→Contact→Broker Operations. Current broker Draft Promotion already produces an unlinked PhysicalBoat deliberately. `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D07 permits a **confirmed** BoatDesignRef and says a missing ref is not a promotion/publication blocker. `specs/MARKET_IDENTITY_CONTRACT.v0.1.md` preserves BoatDesign vs concrete-yacht identity. A new **separate post-promotion identity association** does not modify SLICE-0067's required unlinked fresh-identity atomic promotion. Existing Search truth and seller commercial neutrality remain unchanged.

**REPOSITORY RECONCILIATION CHECK:** PASS  
`persistence/professional_listing_promotion.py` inserts the new PhysicalBoat with `boat_design_ref=None`; `persistence/inventory_search.py` selects only `pb.boat_design_ref IS NOT NULL`. `persistence/physical_boat.py` provides immutable create/read but no post-create confirmed attach action. `application/inventory_editing.py`, `api/app.py` and `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro` provide the existing Organization/MFA/authorization and status/read/update surface but no design selection/association. `persistence/identity_readback.py` fetches individual canonical designs, not a bounded broker design-selector endpoint. A normal broker-created searchable association cannot be made. Script-seeded intake was not normal broker flow.

**TRIGGER GATES CHECK:** PASS  
No new Search criterion; canonical accepted count remains 2. Publication and Search eligibility are separate from the association; seller payments never affect them. Local synthetic-data development does not activate Production Readiness (still `IN_PROGRESS`), external data, pilot, launch or Production Launch Pack (still `NOT_STARTED`). The Owner's product-first priority governs execution order only.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
New explicit `MVP-BROKER-014` is DUE and owned by this readiness; implementation outcome remains pending until reviewed/accepted. `MVP-BROKER-010`/`REQ-BROKER-026` Search-fit diagnostics and `MVP-BROKER-011`/`REQ-BROKER-027` import remain separate PENDING commitments, with export and periodic reporting likewise unchanged. Higher-risk CR-01/02/03/07/16 and buyer verification, privacy/retention, admin and production infrastructure are required **before applicable real external pilot/user data**, not prerequisites for this disposable-data code implementation. All remain explicitly tracked in the post-0081 reassessment. Do not relabel past broker/security gates or new production readiness as PASS based on this slice.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS  

## Decision / implementation reconciliation

**Accepted records checked:** `docs/POST_SLICE_0081_REASSESSMENT_2026-10-12.md`; `docs/PROJECT_STATE.md`; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D01/D07/D08/D09/D11; `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `docs/DATABASE_COVERAGE_STRATEGY.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; accepted SLICE-0067/0069/0072/0081 closures.
**Production implementation checked:** `src/hullq/persistence/professional_listing_promotion.py`; `src/hullq/persistence/physical_boat.py`; `src/hullq/persistence/inventory_search.py`; `src/hullq/application/native_inventory_query.py`; `src/hullq/persistence/identity_readback.py`; `src/hullq/application/inventory_editing.py`; `src/hullq/persistence/inventory_editing.py`; `src/hullq/domain/market_identity.py`; `src/hullq/domain/listing_draft_payload.py`; `src/hullq/api/app.py`; `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`; existing draft/promotion and publication SSR/API, current identity/search/inventory/edit tests, and migration schema shape.
**Already implemented / not re-decided:** PhysicalBoat/BoatDesign separation; canonical design FK; explicit NULL design allowed; immutable create semantics; separately authorized broker draft promotion, inventory claim editing and publication; current-public/freshness gate; two existing technical Search criteria with fail-closed listing evidence; Organization/PUBLISHER/current MFA/CSRF; no owner-direct broker-role bypass.
**Exact remaining gap:** Existing promoted NativeListings cannot be explicitly associated with an existing canonical BoatDesign by an authorized broker; Search's design-linked candidate enumeration therefore excludes normal broker-created inventory regardless of its own accurate claims.
**Accepted-but-unimplemented obligations:** A durable first confirmed design association from broker-inventory workflow (D07-permitted and still omitted after 0067), the registered `MVP-BROKER-014` gap now owned by SLICE-0082; all other open MVP/mandatory product and production obligations stay under their own scopes and triggers.
**Material classifications:** `DECIDED_AND_IMPLEMENTED` accepted identities, promotion, publication, Search and inventory edit; `DECIDED_NOT_YET_IMPLEMENTED` authorized confirmed first-time design association plus audit/proof; `EXPLICITLY_DEFERRED` fuzzy auto-link, already-linked correction, existing PhysicalBoat dedup, Search-fit, import, broad design universe import, multi-Organization link arbitration, production/pilot integrations; `GENUINELY_OPEN` future policy for wrong already-established link or canonical design-record replacement, not silently decided here; `CONFLICT_OR_REGRESSION` product-vertical gap between intentionally unlinked 0067 promotion and search's hard durable-link condition, with no existing code regression established.

## Production phase transition check

**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE  

No providers, production data, new accounts, paid resources, real personal data, production pilot or launch operations in this implementation; canonical launch-pack phase remains `NOT_STARTED`.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  

The existing technical native Search count remains 2 and its matching semantics are unchanged. Security/Launch Gate prior ACCEPT scopes remain intact, with external pilot still blocked by independent Production Readiness and all applicable triggered requirements.

## Mechanical invariants / failure modes

**Risk classification:** HIGH_RISK  
**Why this classification:** The operation first mutates durable shared PhysicalBoat→canonical BoatDesign identity, which can change what an ACTIVE listing can qualify for in public Search. A wrong/unauthorized, silently overwritten or cross-Organization-linked ref would corrupt real yacht identity and buyer match trust.
**Must-never-change invariant:** A broker-selected design is only a **confirmed association assertion**, never a verified technical claim about the individual boat. `NULL → existing exact BoatDesignRef` may be performed once for an otherwise unlinked broker-controlled PhysicalBoat; a non-NULL existing link must never be silently replaced, detached, guessed by fuzzy matching or treated as absent. Repeated exact same request is read-only `ALREADY_LINKED` (no second audit event); different-design replay yields explicit immutable conflict. Existing `create_physical_boat` must retain immutable create/retry semantics. PhysicalBoatId, MarketEpisodeId, NativeListingId and broker claim revisions remain untouched.
**Durable source of truth / loss boundary:** `physical_boats.boat_design_ref` (FK to `canonical_boat_designs`) remains sole current association truth. One dedicated durable provenance/audit event records actor Account, controlling Organization, PhysicalBoat, target BoatDesign, linked NativeListing, recorded timestamp and explicit confirmation method; unique first-association guarantee and exact one-to-one audit-to-association atomicity. No event or current FK claim may be held only in Astro, memory, browser storage, log text or an external provider. Crash/host loss after PostgreSQL COMMIT preserves both, crash before COMMIT preserves neither.
**Retry / replay / partial-failure behavior:** The authorized POST uses a stable operation ID/expected-unlinked-state precondition; transactional row locking or `UPDATE ... WHERE boat_design_ref IS NULL` CAS establishes one winner. Concurrent same/different-design submissions serialize; identical acknowledged retries never mint another audit event; stale browser version, changed listing→PhysicalBoat chain, existing link, invalid/unknown target, failed FK or audit insert, authorization revoked mid-flight, database loss and ambiguous HTTP-after-commit retry cannot silently overwrite any identity or create split audit truth. If source/target identity changes between display and write, recompute authority inside the transaction and fail closed. An unrelated Organization's listing or third-party observation may share a PhysicalBoat under accepted market identity: **do not permit a single broker to mutate that shared global link by unilateral assertion**; deny/defer such cases to a separate authorized reconciliation, and prove the shared-boat case.
**Absence-vs-error / fail-closed behavior:** `UNRESOLVED` is only the authoritative SQL NULL. Unknown/nonexistent design, DB read timeout, malformed selector response, insufficient canonical identity, ambiguous model/generation, tenant/role/MFA denial, shared-boat conflict and error do not become a valid `BoatDesignRef`. Bounded selector shows exact canonical id + contextual brand/model/generation/year if genuinely recorded; never auto-select by brand/model string, and never mint canonical design data from broker claims. Foreign and nonexistent listing IDs use identical existing non-enumerating response semantics; private candidate/identity context never leaks across organizations. No new public read/write identity oracle.
**Executable adversarial proof:** Real PostgreSQL 18 + FastAPI + built Astro SSR over the actual signed-in Broker Workspace: ordinary professional draft creation→promotion→in-inventory design selection/explicit confirmation→existing claim/offer/media publication controls→ordinary public technical Search for `draft_max` and/or `keel_configuration` finds that exact authorized ACTIVE NativeListing when design and concrete claims support a CONFIRMED_MATCH. Seed only *canonical* BoatDesign records and necessary authenticator fixtures, never direct-update the PhysicalBoat association in the happy path; do not claim that unseeded canonical catalog coverage is solved. Also prove no link→excluded but independent exact public listing still works, wrong design→CONFIRMED_NON_MATCH or INSUFFICIENT_DATA, stale/disallowed/MFA/foreign/unknown targets, invalid/ambiguous design choices, no silent derive from identical model name, exact retries, conflicting concurrent attempts, audit rollback, database failures, different Organization/shared PhysicalBoat, withdrawn/freshness/public suppression, and no extra technical Search criterion. Re-run accepted SLICE-0067 promotion, SLICE-0069 publication and SLICE-0072 inventory editing regressions, plus web client/SSR checks.
**Slice sizing assessment:** COHERENT  

A bounded selector is necessary to pick a true canonical record; transactional first association is the single write; readback and current native Search are the visible consequence. Production runtime, operator onboarding, mass data enrichment, Search-fit simulation, correction/remediation and import remain independent later capabilities. If an implementation requires changing the atomic draft promotion or broad cross-Organization physical-identity reconciliation, STOP for another readiness decision rather than bundle it.

## Why this slice exists

SLICE-0081 delivered a broker daily operations dashboard, but a normal broker-produced NativeListing remains design-unresolved after the accepted 0067 promotion. Existing native technical Search intentionally excludes unlinked PhysicalBoats. The Owner received the 2026-10-12 external code review, accepted its priority implication and explicitly directed `ok go` for this readiness. Connecting broker-controlled real listing inventory to the existing design-aware Search is a stronger near-term first visible product result than an unconnected Search-fit simulation, broad refactor, more broker dashboards or early bulk import.

## Controlling artifacts

- `docs/POST_SLICE_0081_REASSESSMENT_2026-10-12.md`; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` (D01/D07/D09/D11); `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`.
- `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `docs/DATABASE_COVERAGE_STRATEGY.md`.
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`.
- `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; accepted SLICE-0067/0069/0072/0081 closures.
- Current production modules: `persistence/physical_boat.py`, `persistence/professional_listing_promotion.py`, `persistence/identity_readback.py`, `persistence/inventory_search.py`, `application/native_inventory_query.py`, `application/inventory_editing.py`, `persistence/inventory_editing.py`, `api/app.py`, `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro`.

## In scope

1. Add **bounded, exact-source canonical BoatDesign selection** to an authorized Organization inventory context, with deterministic server-side result limits, safe input parsing, no fuzzy auto-join and truthful absence/error/ambiguity representation. A search term is a way to locate *candidates*, not evidence of a confirmed identity.
2. Add exactly one **post-promotion first-association** write to `physical_boats.boat_design_ref` with current Organization/MFA/PUBLISHER authorization and listing→episode→PhysicalBoat provenance rechecked inside the transaction; protect shared/global PhysicalBoat ownership and immutable existing links.
3. Add durable per-link confirmation evidence and immutable audit event, transactionally inseparable from link write; bound operation-ID/expected-state handling and replay/concurrency semantics to an unlinked→linked transition.
4. Add broker-facing detail/readback for current link, explicit confirmation and obvious unresolved/linked/stale/conflict/error states in or directly adjacent to the existing authorized inventory edit page. Do not invent a Search-fit score, popularity estimate or synthetic buyer demand.
5. Prove end-to-end the **ordinary professional** broker route through existing promotion, inventory/current-public controls and native Search with canonical design and concrete claim evidence, including negative cases in high-risk failure model.

## Explicitly out of scope

- Changing `ProfessionalListingDraft` payload keys or accepted SLICE-0067 atomic promotion semantics; this slice works on existing promoted NativeListings.
- New Search criteria #3+, Search scoring/ranking/eligibility, public listing bypass, synthesized boat/design fact, fuzzy matching, automatic identity assignment, broad canonical catalog import/enrichment, multi-Organization identity arbitration, wrong-link reassign/detach/deletion, seller/owner-direct association UI.
- The full REQ-BROKER-026 pre-publication Search-fit diagnostic; technical claim-field additions to draft authoring; Search exclusion volume analytics; structured CSV/feed import; per-broker export; periodic report delivery.
- New Auth0, buyer account, operator onboarding, production notification worker/provider, proxy runtime, DB pooling or image CDN work. These remain independently tracked pre-pilot/scale gaps, not waived.

## Required behavior

1. Only exact existing canonical BoatDesign identities may be selected. Read is bounded by server-defined max 20 results per query and deterministic stable ordering (including id), with no unlimited list, unbounded wildcard or user-controlled SQL fragment. The UI shows enough recorded context to distinguish lookalike generations; missing brand/years are labeled unknown instead of guessed. Large universe search can be basic without a new ranking/recommendation engine.
2. Selection is *manual explicit confirmation*: current user sees exact design identity and explicitly attests that it describes the concrete boat's model; this **does not verify** the boat's actual keel, rudder, draft, year or configuration. Unresolved remains allowed for listings even after public publication; never make `BoatDesignRef` a D22 publication blocker.
3. Authorization: exact ACTIVE membership with accepted publisher role, MFA/current session, Organization ownership of exact NativeListing; same non-enumerating behavior for foreign/unknown listing. Authoritative server-side check must run before lookup/write and again under transaction for the association. No cross-Organization association through a shared physical-boat chain; fail closed if other Organization inventory or external observation materially shares the boat and a unilateral global edit would change third-party truth.
4. Design-reference first-link update and immutable audit event commit atomically with FK enforced; transaction-safe row lock/CAS and operation replay semantics. Same actor or later authorized actor re-sending the exact established link returns distinct already-linked success with no audit duplication; different linked target conflicts; no reassign/removal in 0082.
5. The broker inventory page shows `UNRESOLVED` when FK is actually NULL, `LINKED` with the recorded canonical identity when established, `NOT_FOUND_OR_DENIED` / `MFA_REQUIRED` / `PUBLISHER_ROLE_REQUIRED` / `CONFLICT` / `SERVICE_UNAVAILABLE` separately when applicable. Always render escaped text, private no-store/noindex, preserve existing CSRF and failure status.
6. Canonical Search remains unchanged at exactly two criteria. Confirmed Search appearance requires all previously accepted design and concrete-claim tests and CurrentPublicEligibility/freshness/visibility. A link alone does not guarantee results or upgrade UNKNOWN.
7. Nonlinked listing remains visible through existing exact public route when otherwise eligible; a linked but unqualified/withdrawn/suppressed listing must never be forced into Search by design choice. All prior publication/claim/offer/version invariants remain.
8. When no canonical model exists, remain unresolved and provide a truthful explanation or safe follow-up (e.g. no match/needs review), without secretly creating a canonical design or inventing exact catalog size.

## Deliverables

- Bounded authenticated catalog candidate read projection and typed domain/request/result semantics.
- PostgreSQL transactional, audited, single-use first-time PhysicalBoat→BoatDesign association, migration and safeguards as required.
- Broker Organization-scoped FastAPI read/write with accepted CSRF/session/MFA/role/non-enumeration behavior.
- Broker-facing selector and link status/actions integrated into existing inventory UI without a second editor architecture.
- Unit/domain/persistence/API tests for all classification, replay and authorization outcomes and real PostgreSQL end-to-end Astro SSR proof of the buyer Search discovery result.
- Updated documentation/governance statuses **only at accepted implementation closure**, not by premature readiness claim.

## Acceptance criteria

- [ ] Normal authenticated authorized broker creates/promotes a listing in the real app; no direct SQL insertion or manual linking of the PhysicalBoat. Browser selection from an existing canonical model, explicit confirmation and durable link succeed.
- [ ] After authorized ordinary claim/offer/media/publish steps, the **same NativeListingId** is a CONFIRMED_MATCH for a supported technical Search requirement exactly when existing truth warrants it; no fake relevance/ranking, unchanged 2-criterion vocabulary.
- [ ] Refresh/browser restart and app/host restart preserve durable link and one audit event; no browser-local authority.
- [ ] Pre-existing unlinked listings (DRAFT or ACTIVE) are supported without changing 0067 promotion; unresolved stays truthful and independently publication-ready where allowed.
- [ ] Different canonical identities with similar names cannot be inferred/merged without deliberate exact selection; unavailable catalog/search lookup fails closed.
- [ ] Unknown/foreign Org/listing, MFA missing, PUBLISHER missing, revoked membership, invalid/ambiguous design and shared boat are denied without identity or provenance disclosure.
- [ ] Same-target exact retry after lost HTTP response is idempotent; different-target/stale/concurrent attempts never overwrite first link or fabricate extra audit events.
- [ ] Rollback/failing FK/audit write causes no partially linked row or orphan audit record; host/process/crash loss cannot divide committed truth.
- [ ] Existing public listing and current Search suppression, withdrawal, stale and concrete claim UNKNOWN rules remain unchanged; unrelated Organization/model identities untouched.
- [ ] All relevant unit, migration, persistence, API, Astro SSR, existing 0067/0069/0072 regression and main web check/build tests PASS; repository validation PASS; remote CI (Ubuntu/Windows/PostgreSQL 18/Web) and manufacturer reproducibility observed on exact implementation HEAD before Owner acceptance.
- [ ] High-risk adversarial self-review and independent exact-HEAD review traverse each named mechanical failure case; external/pilot/prod gate claims stay unchanged.

## Expected touch points

`src/hullq/domain/` (bounded association/confirmation result), `src/hullq/application/` (broker authorization/orchestration), `src/hullq/persistence/` (bounded design read and atomic link+audit), `src/hullq/api/app.py` (scoped read/write), `web/src/lib/` (typed API client), `web/src/pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/edit.astro` (selector/readback), one additive PostgreSQL migration and focused unit/persistence/API/web tests, one real SSR/HTTP retained inspection script. Existing unrelated broker workflow paths should remain unchanged.

## Validation

```bash
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv run python scripts/validate_repository.py
uv run pytest -q tests/unit/ tests/persistence/   # use repo's actual shard/db-test conventions
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
# Execute and retain a real PostgreSQL 18 + FastAPI + built Astro SSR
# create/promote→explicit association→normal publish→technical Search proof.
# Re-run scoped existing SLICE-0067/0069/0072 verification and CI matrices.
```

Do not claim validation success until actually executed. If broad test commands differ from supported repository scripts, use their canonical variants and report exact commands/results. Real provider/live broker data are not part of the acceptance evidence for this internal implementation.

## Stop conditions

- A safe canonical BoatDesign selector cannot distinguish identities from existing durable canonical evidence, or an exact supported design does not exist (remain `UNRESOLVED`, do not mint/guess).
- The implementation would need to relax the accepted immutable `create_physical_boat` operation or change atomic draft promotion to make first association work (raise a decision/review conflict).
- Shared PhysicalBoat or foreign Organization ownership cannot be distinguished safely; do not mutate global design identity unilaterally.
- A later replacement/correction of an established `BoatDesignRef` appears necessary (separate policy decision; never overwrite).
- Existing atomic audit, rollback/idempotence/stale/version, tenant/MFA, CurrentPublicEligibility or Search semantics cannot be preserved.
- A required proof can only pass by manually injecting design links into the tested broker-owned PhysicalBoat rather than through the real broker flow.
- Material independent capability (bulk import, catalog enrichment, novel Search match engine, general provider ops) is required; pause for proper slice decomposition.
- Any trigger-gate, owner-direct or provenance conflict arises without an accepted governing rule.

## Status handoff rule

The implementation agent sets `**Status:** REVIEW` and matching `**Status set by this handoff:** \`REVIEW\`` on the same primary document only at the implementation completion handoff. It must not mark `DONE`, merge, close the slice, or launch a subsequent slice. Review and explicit Project Owner acceptance remain mandatory before the separate acceptance closure and local `FINISH_SLICE.bat` of 0082.
