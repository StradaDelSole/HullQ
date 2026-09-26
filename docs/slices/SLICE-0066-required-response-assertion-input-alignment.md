# SLICE-0066 — Required-Response / Assertion Input Alignment

**ID:** SLICE-0066  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Shared seller draft truth-input alignment before professional promotion  
**Depends on:** SLICE-0054 owner-direct drafts; SLICE-0061 professional drafts; SLICE-0062 professional recovery; SLICE-0065 publication-input alignment  
**Blocks:** later professional draft promotion readiness/materialization; no later slice is automatically authorized

## Objective

Deliver exactly one capability:

> Make the existing shared draft field `physical_boat.build_year` capable of representing an explicit truthful REQUIRED_RESPONSE of either VALUE_ASSERTION(year) or UNKNOWN while preserving omission as unanswered and preserving legacy integer draft compatibility.

No marketplace promotion, fact creation or publication occurs.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: align one existing shared draft field's response semantics with its already-accepted Marketplace REQUIRED_RESPONSE/UNKNOWN model.

**VISIBLE-RESULT CHECK:** PASS  
In both owner-direct and professional draft editors, the Project Owner can save/reopen a concrete build year, explicitly mark build year unknown, or leave it unanswered; API/readback makes UNKNOWN mechanically distinct from omission and legacy integer drafts remain readable.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Broker Launch Gate create/publish work cannot proceed truthfully while a required marketplace response supports UNKNOWN but the pre-market draft accepts only integer-or-omitted. The slice removes that blocker without creating marketplace truth.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical post-0065 state, both draft contracts, shared parser/serializer, professional recovery, Marketplace field registry, PhysicalBoat BuildYearClaim, relevant draft application/persistence/API/web/tests, Broker Workspace direction/gates and the owner-accepted 2026-09-26 workflow decisions were checked.

**TRIGGER GATES CHECK:** PASS  
0066 adds no Search criterion, production data, broker pilot, paid plan or public launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0065-acceptance-closure.md`; `docs/POST_SLICE_0065_REASSESSMENT_2026-09-26.md`; `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`; `specs/LISTING_DRAFT_ASSERTION_RESPONSE_CONTRACT.v0.1.md`; `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; Broker Workspace/production/post-0051 gate records.

**Production implementation checked:** `src/hullq/domain/listing_draft_payload.py`; owner-direct/professional draft domain/application/persistence/API code; both Astro draft editors; professional recovery implementation; `src/hullq/domain/physical_boat_claims.py` BuildYearClaim; relevant owner-direct/professional draft domain/persistence/API/web/recovery tests and migrations.

**Already implemented / not re-decided:** exact nine common draft keys; private incomplete-draft semantics; shared channel-neutral common parser/serializer; owner-direct Account ownership; professional Organization/MFA/PUBLISHER authorization; optimistic versioning; professional local recovery isolation/version/expiry rules; Marketplace build-year REQUIRED_RESPONSE with VALUE_ASSERTION/UNKNOWN; PhysicalBoat BuildYearClaim VALUE_ASSERTION/UNKNOWN; SLICE-0065 broker_description/boat_name alignment; no implicit promotion.

**Exact remaining gap:** common draft `physical_boat.build_year` is currently `int | None`: omission and concrete integer exist, but explicit UNKNOWN cannot be authored/persisted/read back. A later promotion therefore cannot distinguish unanswered from an explicit truthful unknown response.

**Accepted-but-unimplemented obligations:** D17 shared draft build-year assertion response; later PROMOTION_READY evaluator; atomic professional promotion/materialization; media/PublicatonReadiness; offer/listing editing; lead/outcome/analytics/import/export/alert obligations remain separate.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` existing draft/auth/concurrency/recovery/registry/BuildYearClaim boundaries; `DECIDED_NOT_YET_IMPLEMENTED` D17 structured build-year response and later promotion chain; `EXPLICITLY_DEFERRED` promotion, identity allocation, claim/offer materialization, publication, media, editing, leads, outcomes, analytics, import/export, Search-fit and alerts; `GENUINELY_OPEN` none blocking this slice; `CONFLICT_OR_REGRESSION` current integer-only draft value shape and old contract wording are narrower than the accepted UNKNOWN-capable required-response direction and are the bounded gap this slice resolves.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS

## Why this slice exists

Current repository truth:

```text
Draft:
physical_boat.build_year = integer | OMITTED

Marketplace registry:
physical_boat.build_year = REQUIRED_RESPONSE
                         = VALUE_ASSERTION(year) | UNKNOWN

PhysicalBoat claim domain:
BuildYearClaim = VALUE_ASSERTION(year) | UNKNOWN
```

Treating omitted draft input as UNKNOWN would invent a response. Requiring a year would force guessing. Promotion must therefore remain blocked until draft input can explicitly distinguish all required states.

## Controlling artifacts

- Requirement IDs: `REQ-BROKER-002`, `REQ-BROKER-003`, `REQ-BROKER-004`
- Specifications: `specs/LISTING_DRAFT_ASSERTION_RESPONSE_CONTRACT.v0.1.md`; `specs/OWNER_DIRECT_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- Accepted owner decisions: `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md` D16/D17
- Reassessment: `docs/POST_SLICE_0065_REASSESSMENT_2026-09-26.md`
- Broker direction / Launch Gate / mandatory register
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Architecture rebaseline: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Owner-direct direction/requirements remain controlling where applicable.

## In scope

- one small typed shared draft assertion-response primitive sufficient for build year;
- `physical_boat.build_year` canonical structured VALUE_ASSERTION/UNKNOWN parser/serializer behavior;
- mechanically distinct omission;
- strict structured-object validation;
- legacy bare-integer ingress/persistence compatibility;
- canonical structured serialization for API/readback/new writes;
- both OwnerDirectListingDraft and ProfessionalListingDraft paths through the same shared primitive;
- both existing draft edit UIs exposing unanswered / known year / explicit unknown;
- professional local recovery preserving those three form states without changing recovery authority;
- focused unit/API/persistence/UI/recovery tests;
- retained real PostgreSQL draft round-trip proof where applicable;
- repository validation/lint/type/web checks and remote CI;
- REVIEW handoff only.

## Explicitly out of scope

- adding/removing/renaming common draft keys;
- changing any common field other than build_year to an assertion object;
- changing Marketplace field-registry build-year semantics;
- changing BoatNameClaim or broker_description semantics;
- PROMOTION_READY evaluator;
- ProfessionalListingDraft -> PhysicalBoat/MarketEpisode/NativeListing promotion;
- marketplace ID allocation/resolution/dedup;
- PhysicalBoat claim revision creation from draft;
- offer revision creation from draft;
- NativeListing creation/publication;
- media/gallery;
- offer/listing editing;
- republish/relist/clone;
- episode-resolution authority;
- sale outcomes;
- leads/CRM;
- analytics;
- import/export;
- Search/Search-fit;
- buyer alerts;
- payments;
- production pilot/public launch.

## Required behavior

### A. Key count and channels

`ACCEPTED_DRAFT_PAYLOAD_KEYS` remains exactly nine.

Owner-direct and professional drafts continue to use the same shared common parser/serializer; no channel-specific build-year validator may diverge.

### B. Canonical VALUE_ASSERTION

Accepted/canonical wire:

```json
{"physical_boat.build_year":{"assertion_kind":"VALUE_ASSERTION","value":1987}}
```

The year retains existing integer/not-bool semantics. No new arbitrary year range is invented.

### C. Canonical UNKNOWN

Accepted/canonical wire:

```json
{"physical_boat.build_year":{"assertion_kind":"UNKNOWN"}}
```

UNKNOWN forbids a `value` member.

### D. Omission

Absence of `physical_boat.build_year` remains unanswered/incomplete draft state.

Omission MUST NOT normalize to UNKNOWN.

JSON null is not omission and fails closed.

### E. Strict shape

Unknown assertion kinds, missing required object members, forbidden `value` on UNKNOWN, absent `value` on VALUE_ASSERTION and extra members fail the request closed with zero mutation.

### F. Legacy compatibility

Historical/request form:

```json
{"physical_boat.build_year":1987}
```

remains accepted/readable and normalizes internally to VALUE_ASSERTION(1987).

API/read serializer and successful new/update persistence use canonical structured form. Existing stored JSONB need not be bulk migrated solely for readability.

### G. Browser editing

Both draft editors visibly distinguish:

```text
not answered
known year
unknown
```

Blank input does not mean UNKNOWN. Selecting UNKNOWN sends no year value.

### H. Professional recovery

Recovery preserves the three build-year form states under all existing same-version/stale/expiry/storage-failure rules using the bounded recovery-only string control `physical_boat.build_year.assertion_kind` plus the existing year-value field. The control accepts only `""`, `VALUE_ASSERTION` or `UNKNOWN`, is not a tenth draft API key and never becomes server/marketplace truth.

### I. No promotion

Saving or reading any build-year response in either draft channel creates zero PhysicalBoat, claim revision, MarketEpisode, NativeListing, offer, lifecycle, freshness or Search mutation.

## Deliverables

- shared typed draft assertion-response implementation for build_year;
- updated common draft parser/serializer;
- both draft application/API/persistence paths remain compatible;
- owner-direct and professional Astro editing support;
- professional recovery support;
- focused tests, including legacy persisted integer compatibility;
- retained inspection/proof where useful;
- completion report with exact HEAD and remote-gate state.

## Acceptance criteria

- [ ] Shared common key count remains exactly 9.
- [ ] Both channels use one common build-year parser/serializer.
- [ ] Omitted build_year remains omitted and serializes with no key.
- [ ] Structured VALUE_ASSERTION(year) is accepted and canonicalized.
- [ ] Structured UNKNOWN is accepted and canonicalized.
- [ ] OMITTED != UNKNOWN != VALUE_ASSERTION is mechanically tested.
- [ ] Legacy bare integer requests remain accepted as VALUE_ASSERTION compatibility input.
- [ ] Legacy bare integer persisted JSONB rows remain readable without bulk migration.
- [ ] Canonical API/readback for a legacy integer is the structured VALUE_ASSERTION form.
- [ ] Successful new/update persistence writes canonical structured build-year JSON.
- [ ] bool, null, invalid assertion kind, missing/extra members and UNKNOWN-with-value fail closed.
- [ ] Owner-direct create/read/update/browser behavior supports known/unknown/unanswered year.
- [ ] Professional create/read/update/browser behavior supports known/unknown/unanswered year.
- [ ] Professional local recovery preserves known/unknown/unanswered state and stale isolation.
- [ ] Existing broker_description, boat_name, asking-price and all other shared-key semantics remain unchanged.
- [ ] No database schema migration is introduced unless implementation discovers a repository-proven necessity and stops for review.
- [ ] Draft save/read creates zero marketplace truth/state.
- [ ] Search criteria remain exactly two.
- [ ] Broker Workspace Launch Gate remains NOT_READY.
- [ ] repository validation, Python formatting/lint/type/tests, web check/test/build pass.
- [ ] relevant PostgreSQL/FastAPI/Astro retained proof passes.
- [ ] exact implementation HEAD receives independent review and required remote CI.
- [ ] explicit Project Owner acceptance occurs before implementation merge.

## Expected touch points

- `src/hullq/domain/listing_draft_payload.py`
- owner-direct/professional draft domain/application/persistence/API code only as required by shared serialization
- `web/src/pages/sell/direct/[draft_id].astro`
- `web/src/pages/broker/organizations/[organization_id]/drafts/[draft_id].astro`
- `web/src/lib/professionalDraftRecovery.ts`
- focused owner-direct/professional/recovery tests
- optional retained proof script if needed
- no Alembic migration expected

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

Run the repository's approved local PostgreSQL proof path for affected owner-direct/professional persistence/API behavior. Remote CI must pass on the exact final implementation HEAD.

## Stop conditions

Stop and report rather than inventing policy if:

- implementation needs a tenth common draft key;
- owner-direct and professional build-year semantics would diverge;
- omission would have to be inferred as UNKNOWN;
- legacy integer drafts cannot remain readable without destructive/bulk rewriting;
- implementation appears to require an Alembic/schema migration for a reason not established by this readiness record;
- implementation requires PROMOTION_READY or marketplace promotion;
- PhysicalBoat/MarketEpisode/NativeListing/offer/claim creation is needed;
- a non-build-year field would need generalized assertion semantics;
- Search semantics or technical criterion count changes;
- scope reaches media, editing, leads, outcomes, analytics, import/export, alerts, payments or launch.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, successful remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.
