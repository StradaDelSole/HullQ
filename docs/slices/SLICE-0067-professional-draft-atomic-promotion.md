# SLICE-0067 — Professional Draft → Atomic Marketplace Promotion

**ID:** SLICE-0067  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker launch-critical professional inventory creation  
**Depends on:** accepted SLICE-0061–0066 professional draft/workspace/input alignment plus accepted SLICE-0043–0050 marketplace persistence primitives  
**Blocks:** later media/gallery and canonical PublicationReadiness for normal broker-created inventory

## Objective

Deliver exactly one coherent user-visible capability:

> An authorized professional publisher can promote one exact promotion-ready ProfessionalListingDraft into exactly one real NativeListing in lifecycle DRAFT, with a fresh PhysicalBoat, fresh MarketEpisode, initial publishing-Organization PhysicalBoat claim and initial offer, atomically and retry-safely.

This is one vertical capability across persistence/domain/application/API/browser layers. It is intentionally larger than recent micro-slices because the material semantics are already owner-decided and the remaining work is safe composition.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One outcome only: ProfessionalListingDraft → durable marketplace NativeListing DRAFT promotion. PhysicalBoat/MarketEpisode/claim/offer/draft-state work are inseparable parts of that one atomic outcome, not independent product features.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can create/fill a professional draft, see server-owned PromotionReadiness, click Promote/Create listing, observe the draft become immutable PROMOTED, and see exactly one new lifecycle-DRAFT NativeListing in the existing Organization inventory. Exact retry returns the same NativeListing.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is the immediate next edge in the accepted Broker Launch Execution Focus. Promotion precedes media because accepted D13 attaches media to real NativeListing state, and precedes publication because D03/D06 require promotion to yield DRAFT rather than ACTIVE.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical `origin/main` after accepted 0066, the 2026-09-26 D01–D29 workflow decisions, broker-launch focus, Broker Workspace Launch Gate/register, professional workspace/assertion contracts, NativeListing/PhysicalBoat/MarketEpisode/offer/claim/lifecycle persistence, actor authorization, migrations and retained tests/proofs were checked. No promotion path already exists.

**TRIGGER GATES CHECK:** PASS  
0067 uses only synthetic/internal test data, adds no Search criterion, starts no external broker pilot, paid plan or public launch, and does not trigger Production Readiness.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0066-acceptance-closure.md`; `docs/POST_SLICE_0066_REASSESSMENT_2026-09-27.md`; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D01–D09/D18–D22; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`; professional draft/workspace/assertion contracts; Market Identity and NativeListing persistence contracts; Marketplace field/offer/PhysicalBoat claim contracts; Broker Workspace requirements/gates/register; owner-direct direction/requirements; post-0051 trigger gates and production readiness.

**Production implementation checked:** professional draft domain/application/persistence/API/Astro/recovery; `physical_boat.py`; `market_episode.py`; `native_listing.py`; `native_listing_offer.py`; `physical_boat_claims.py`; `native_listing_lifecycle.py`; broker actor/workspace/lifecycle application code; migrations through current Alembic head `c58f2a1d9e64`; relevant persistence/unit/API/retained vertical tests.

**Already implemented / not re-decided:** runtime-distinct marketplace identities; durable PhysicalBoat/MarketEpisode/NativeListing; DRAFT initial lifecycle default; offer and PhysicalBoat claim immutable revision/head models; professional draft ownership/versioning/recovery and D07 input shapes; MFA/PUBLISHER workspace auth; publishing eligibility; public listing/inventory read surfaces; exact two Search criteria; no production/pilot trigger.

**Exact remaining gap:** no endpoint/application/domain/persistence transaction turns a ProfessionalListingDraft into marketplace state; drafts have no EDITABLE/PROMOTED provenance state; existing public persistence writers each own independent transactions and therefore cannot simply be sequenced to satisfy D03 atomicity; resolved same-Organization MarketEpisode uniqueness is not yet race-safe in PostgreSQL.

**Accepted-but-unimplemented obligations:** D01/D02 fresh-identity promotion branch; D03 atomicity; D04 promoted immutable draft provenance; D05 exact-version idempotency; D06/D07 PromotionReadiness; D09 per-Organization resolved-episode uniqueness; D18 duplicate conflict at that uniqueness boundary. Existing-PhysicalBoat resolution/reconciliation branches, D19 operational broker-reference revisions, D20 episode-resolution revision authority, media, PublicationReadiness, leads, editing, outcomes/import/export/analytics/alerts remain later.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` existing draft/auth/identity/persistence/revision/lifecycle foundations; `DECIDED_NOT_YET_IMPLEMENTED` promotion/readiness/provenance/atomic composition/D09 uniqueness; `EXPLICITLY_DEFERRED` existing-identity reuse/relist/correction/D19/D20/media/publication/leads/editing/outcomes/import/export/analytics/alerts; `GENUINELY_OPEN` none blocking the fresh-identity promotion path; `CONFLICT_OR_REGRESSION` existing top-level-owning persistence writers cannot be naively composed atomically, draft schema lacks PROMOTED provenance, and older global-one-listing-per-episode wording/DB shape lacked D09 per-Organization clarification/enforcement.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

Broker Workspace Launch Gate remains `NOT_READY`. Broker self-service pilot and paid broker plan remain `NOT_STARTED`.

## Why this slice exists

After 0066, every minimum D07 response can be represented truthfully in ProfessionalListingDraft state.

The remaining missing edge is:

```text
ProfessionalListingDraft
→ marketplace identities/facts
```

Media cannot follow the accepted D13 architecture until a real NativeListing exists. Publishing must remain later because D03/D06 require promotion to create DRAFT only.

## Controlling artifacts

- Requirement IDs: `REQ-BROKER-001`, `REQ-BROKER-003`, `REQ-BROKER-004`, `REQ-BROKER-014`, `REQ-BROKER-015`, `REQ-BROKER-030`
- Primary specification: `specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md`
- Professional draft contract: `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- Assertion input contract: `specs/LISTING_ASSERTION_RESPONSE_CONTRACT.v0.1.md`
- Marketplace identity/persistence: `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md`
- Marketplace fact/field contracts and accepted offer/claim domain models
- Owner decisions: `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`
- Reassessment: `docs/POST_SLICE_0066_REASSESSMENT_2026-09-27.md`
- Broker launch focus: `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`
- Broker Workspace Launch Gate / Mandatory Capability Register
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Current owner-direct direction/requirements checked for mixed-supply non-regression
- Relevant open questions: NONE for the fresh-identity v0.1 promotion branch

## In scope

- canonical pure PromotionReadiness evaluator and bounded machine reason codes;
- professional draft durable `EDITABLE | PROMOTED` state;
- immutable `promoted_native_listing_id` / `promoted_at` provenance;
- explicit promoted-draft update rejection and promoted-state recovery guard;
- existing rows migrated to EDITABLE;
- ordinary draft list/update behavior adjusted so promoted drafts leave active editing flow;
- exact-version promotion request and retry result;
- server-generated random PhysicalBoatId/MarketEpisodeId/NativeListingId/revision IDs;
- fresh PhysicalBoat with NULL BoatDesignRef;
- fresh MarketEpisode;
- NativeListing creation in lifecycle DRAFT;
- initial publishing-Organization PhysicalBoat claim revision/head;
- initial NativeListing offer revision/head;
- one top-level promotion transaction with rollback of all writes on failure;
- safe refactor/extraction of transaction-scoped persistence internals where required, preserving existing standalone writer semantics;
- D09 PostgreSQL uniqueness for resolved `(publishing_organization_id, market_episode_id)`;
- deterministic low-level conflict classification for that uniqueness;
- FastAPI professional promote endpoint;
- professional Astro draft-editor promotion readiness/action/result behavior;
- recovery cleanup after successful promotion;
- Organization inventory shows the created DRAFT listing through the existing read path;
- focused unit/persistence/API/browser tests and retained real PostgreSQL/FastAPI/built-Astro proof.

## Explicitly out of scope

- client-supplied or automatically resolved existing PhysicalBoatId/MarketEpisodeId/NativeListingId;
- fuzzy dedup/merge;
- BoatDesignRef resolution/linkage or design-to-physical fact copying;
- existing-PhysicalBoat D08 reconciliation branches;
- relist/republish/clone/duplicate-draft workflows;
- D19 revisioned current operational broker reference;
- D20 post-creation episode-resolution authority/correction;
- media/gallery;
- PublicationReadiness or publication/ACTIVE transition;
- freshness confirmation;
- marketplace edit after promotion;
- leads/CRM;
- sale/outcome;
- import/export;
- analytics/insights;
- Search-fit diagnostics;
- buyer alerts;
- payments/entitlements;
- owner-direct publication;
- new Search criterion or Search ranking change;
- production pilot/public launch.

## Required behavior

### A. PromotionReadiness

Use exactly one domain evaluator for preflight/browser display and authoritative mutation-time evaluation.

Required reasons are the bounded vocabulary from the promotion contract.

Ready means all D07 required responses are present and price state is marketplace-consistent.

POA + currency is NOT_READY; do not silently discard currency.

### B. Draft state/provenance

- pre-existing/new drafts are EDITABLE;
- active draft list returns only EDITABLE;
- update is permitted only for EDITABLE; a concurrent/later update against PROMOTED returns a distinct PROMOTED_IMMUTABLE-equivalent conflict with zero mutation;
- browser-local recovery is never applied to PROMOTED, even at the same frozen version, and is best-effort removed;
- promotion locks the exact draft row and requires exact positive expected version;
- successful promotion freezes content/version and marks PROMOTED;
- version does not increment on promotion;
- PROMOTED stores one immutable resulting NativeListingId and promoted_at;
- direct own read may explain the promoted result but cannot mutate it;
- no reactivation path.

### C. Fresh identity allocation

The promote request contains no marketplace identity/resolution input.

Every first successful v0.1 promotion mints fresh server-owned IDs:

```text
PhysicalBoatId
MarketEpisodeId
NativeListingId
PhysicalBoatClaimRevisionId
NativeListingOfferRevisionId
```

No BoatDesignRef is synthesized.

### D. Atomic transaction

The complete D03 chain is one PostgreSQL transaction.

Existing public persistence functions' top-level durable-commit guarantees remain unchanged.

Do not implement promotion as sequential independent commits.

Failure-injection tests must prove rollback after representative intermediate stages, including after identity rows exist in the uncommitted transaction and after at least one initial fact/head write.

### E. Claim mapping

Initial Organization claim contains only draft-backed concrete-yacht truth:

- brand;
- model;
- build-year VALUE_ASSERTION or UNKNOWN;
- optional boat-name VALUE_ASSERTION.

Other PhysicalBoat claims remain omitted.

### F. Offer mapping

Initial offer contains:

- mode;
- amount/currency iff AMOUNT;
- country;
- optional region as VALUE_ASSERTION;
- broker description.

Other offer claims remain omitted.

### G. NativeListing / lifecycle

- exact selected Organization is immutable publisher;
- authenticated promoting Account is creation actor;
- exact draft broker reference is immutable creation provenance when present;
- new MarketEpisode link is resolved at creation;
- lifecycle is DRAFT;
- zero publication-transition rows;
- zero freshness-confirmation rows;
- public listing surface does not expose the DRAFT listing as current/public.

### H. Retry/concurrency

- stale expected version -> VERSION_CONFLICT, zero mutation;
- exact retry after PROMOTED with the frozen exact version -> ALREADY_PROMOTED + same NativeListingId;
- PROMOTED + mismatched expected version -> VERSION_CONFLICT, zero mutation;
- concurrent exact promotions serialize on draft and create exactly one marketplace chain;
- exact retry creates no new IDs/revisions/heads.

### I. D09 uniqueness

Database enforces:

```text
UNIQUE (publishing_organization_id, market_episode_id)
WHERE market_episode_id IS NOT NULL
```

Migration validates current rows and fails closed on historical duplicates.

Different Organizations may use the same MarketEpisode.

Low-level NativeListing creation returns deterministic Organization+MarketEpisode conflict rather than leaking UniqueViolation.

Promotion maps it to DUPLICATE_EPISODE and leaves draft EDITABLE with zero writes from the failed attempt.

### J. Authorization / tenant isolation

Promotion reuses current session/Organization/MFA boundary and re-applies real publishing eligibility.

Foreign/unknown draft remains non-enumerating.

Denied/ineligible promotion writes zero marketplace state and leaves draft EDITABLE.

### K. Browser write security and result

Promotion reuses the accepted professional same-origin CSRF boundary: trusted exact Origin plus `X-HullQ-Requested-With: professional-listing-draft-v1`. Missing/foreign Origin or missing/wrong header fails before mutation.

Professional draft editor:

- displays server-derived readiness/missing reasons;
- exposes promotion action when content-ready;
- sends exact version only;
- on success clears recovery for that draft/version and directs user to the resulting Organization inventory/listing context;
- labels resulting listing DRAFT/not public;
- reopening promoted draft shows immutable result/provenance, not editable controls.

## Deliverables

- one Alembic migration descending from current head `c58f2a1d9e64`;
- PromotionReadiness domain model/evaluator;
- promotion application/persistence orchestration;
- safe transaction-scoped persistence composition;
- professional draft promotion state/provenance persistence;
- D09 unique index/constraint + deterministic low-level classification;
- FastAPI endpoint/status mapping;
- professional Astro/API promotion UI integration;
- focused tests and retained proof;
- slice completion report with exact HEAD and remote gate state.

## Acceptance criteria

- [ ] PromotionReadiness uses exactly one server-owned evaluator.
- [ ] Required D07 fields and deterministic reason codes are tested.
- [ ] POA + currency is NOT_READY and never silently normalized.
- [ ] Existing professional drafts migrate to EDITABLE.
- [ ] New drafts start EDITABLE.
- [ ] Active draft list excludes PROMOTED.
- [ ] Ordinary update rejects PROMOTED with a distinct immutable/promoted conflict outcome and zero mutation.
- [ ] Same-version stale recovery does not restore/apply to a PROMOTED draft and is best-effort cleared.
- [ ] Promotion request accepts exactly one positive-integer `expected_version` key; booleans/null/strings/floats/non-positive values/extra keys fail with zero mutation, and marketplace IDs are never accepted.
- [ ] Exact current EDITABLE version + READY + authorized/eligible can promote.
- [ ] Stale expected version returns conflict and writes zero rows.
- [ ] Promotion mints server-owned fresh PhysicalBoat/MarketEpisode/NativeListing/revision identities.
- [ ] PhysicalBoat has NULL BoatDesignRef.
- [ ] MarketEpisode links exactly to new PhysicalBoat.
- [ ] NativeListing links exactly to new MarketEpisode and selected Organization.
- [ ] NativeListing lifecycle starts DRAFT.
- [ ] No publication transition/freshness event is created.
- [ ] Initial PhysicalBoat claim mapping is exact and no BoatDesign fact is copied.
- [ ] Initial offer mapping is exact.
- [ ] Source draft becomes PROMOTED only in the same successful transaction.
- [ ] Promotion leaves draft content version unchanged/frozen.
- [ ] PROMOTED stores immutable NativeListing result link and promoted_at.
- [ ] PostgreSQL enforces promotion-state validity/nullability pairing, FK integrity for promoted_native_listing_id, and uniqueness of a non-null promoted NativeListing provenance link.
- [ ] Exact retry at the frozen promoted version returns same NativeListingId with zero additional writes.
- [ ] PROMOTED retry with a mismatched expected version returns VERSION_CONFLICT and reveals no alternate-version result.
- [ ] Exact-version ALREADY_PROMOTED retry still returns immutable provenance after later publishing-eligibility loss, provided current workspace/MFA/PUBLISHER authorization still permits access; it performs zero marketplace writes.
- [ ] Concurrent exact promotion attempts create exactly one marketplace chain.
- [ ] Representative injected failures roll back PhysicalBoat, MarketEpisode, NativeListing, claim/head, offer/head and draft-state writes together.
- [ ] D09 resolved `(organization, episode)` uniqueness is database-enforced.
- [ ] Same Organization + same resolved episode with another NativeListing is deterministic conflict.
- [ ] Different Organization + same resolved episode remains allowed.
- [ ] Multiple unresolved NativeListings with NULL market_episode_id remain allowed.
- [ ] broker_listing_reference is not used as identity/dedup key.
- [ ] Existing standalone persistence writer commit/idempotency behavior remains regression-tested.
- [ ] foreign/unknown draft remains non-enumerating.
- [ ] MFA/publishing denial leaves draft EDITABLE and writes zero marketplace state.
- [ ] Promotion browser POST enforces the accepted professional Origin + non-simple-header CSRF boundary.
- [ ] Browser shows readiness/action and promoted immutable result safely.
- [ ] Successful browser promotion surfaces the new DRAFT listing in Organization inventory.
- [ ] DRAFT promoted listing is not public/current on the public listing surface.
- [ ] owner-direct behavior remains unchanged.
- [ ] technical native Search criterion count remains exactly 2.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] repository validation, ruff format/check, mypy, full pytest pass.
- [ ] web npm ci/check/test/build pass.
- [ ] retained real PostgreSQL/FastAPI/built-Astro promotion proof passes.
- [ ] exact implementation HEAD receives independent review and required remote CI.
- [ ] explicit Project Owner acceptance occurs before implementation merge.

## Expected touch points

Likely:

- new promotion domain/application/persistence module(s);
- `src/hullq/persistence/professional_listing_draft.py`;
- transaction-safe internals in existing PhysicalBoat/MarketEpisode/NativeListing/offer/claim persistence modules as necessary;
- `src/hullq/api/app.py`;
- professional draft Astro/API/recovery integration;
- one Alembic migration after `c58f2a1d9e64`;
- focused unit/persistence/API/web tests;
- retained professional listing draft/promotion inspection proof;
- exact-head migration assertion where repository tests require it.

No generic repository/UoW framework should be introduced.

## Validation

At minimum:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python -m pytest
npm ci --prefix web
npm run check --prefix web
npm run test --prefix web
npm run build --prefix web
```

Run the repository-approved disposable PostgreSQL 18 + FastAPI + built-Astro retained proof for the full professional draft → promotion → Organization inventory path.

Remote CI and Manufacturer artifact reproducibility must pass on the exact final implementation HEAD.

## Stop conditions

Stop and report instead of inventing policy if:

- implementation requires accepting a client-supplied PhysicalBoatId/MarketEpisodeId/NativeListingId;
- a fuzzy yacht/episode resolver or BoatDesign-to-PhysicalBoat truth projection appears necessary;
- D03 cannot be implemented as one top-level transaction without changing an accepted standalone persistence guarantee;
- a migration would need silently to merge/delete/null existing duplicate listings;
- implementation needs D19 operational broker-reference editing or D20 episode correction to make the fresh-identity path work;
- promotion would have to make a listing ACTIVE/public or attach media;
- owner-direct publication becomes necessary;
- Search semantics/criterion count would change;
- real external production data/pilot would be introduced;
- a new material product/domain/identity/authorization decision not covered by accepted D01–D09/D18 appears.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, successful remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.
