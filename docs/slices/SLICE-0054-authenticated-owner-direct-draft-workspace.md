# SLICE-0054 — Authenticated Owner-Direct Listing Draft Workspace

**ID:** SLICE-0054  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Owner-Direct Marketplace — first private seller write surface  
**Depends on:** SLICE-0053 owner-accepted / DONE; 2026-09-14 owner-direct marketplace rebaseline merged  
**Blocks:** later owner-direct publication/trust-gate admission capability

## Objective

Deliver exactly one visible capability:

> **An authenticated HullQ Account can create, save, list, reopen and update its own private owner-direct sailboat-sale draft in the browser, while another Account cannot read or modify it and the draft never becomes marketplace inventory.**

The draft is private mutable workspace state, not a `NativeListing`.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
The slice is one vertical capability: authenticated owner-direct draft creation/save/reopen/update. PostgreSQL, FastAPI and Astro changes are implementation layers of that same visible capability, not separate features.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can authenticate as an Account with no professional Organization membership, open `/sell/direct`, create a draft, enter bounded boat/offer information, save it, reload/reopen it and observe the durable values. A second Account demonstrably cannot access it.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The 2026-09-14 owner-direct rebaseline requires a distinct private seller write boundary without faking professional eligibility. A private pre-market draft is the smallest useful seller surface that honors the pivot without prematurely implementing publication, verification, fraud escalation or representation-conflict logic.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current SLICE-0041/0043/0045/0049 professional publishing, persistence, offer and lifecycle paths plus SLICE-0053 generic Account/session code were inspected. Existing `NativeListing` persistence is intentionally professional and is not generalized in this slice. The accepted marketplace field registry was inspected for a bounded set of reusable neutral draft-input keys.

**TRIGGER GATES CHECK:** PASS  
The Production Readiness gate is not triggered; the slice adds no technical Search criterion; workflow reassessment is not due; no Broker Workspace mandatory capability is currently `DUE`. Pending Broker Launch Gate commitments remain pending and are not dropped or falsely marked implemented.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md`; `specs/OWNER_DIRECT_DRAFT_CONTRACT.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md`; `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; Broker Workspace Launch Gate and Mandatory Capability Register.  
**Production implementation checked:** `src/hullq/security/session_token.py`; `src/hullq/application/broker_login.py`; `src/hullq/persistence/broker_identity.py`; `src/hullq/domain/publishing_eligibility.py`; `src/hullq/persistence/native_listing.py`; `src/hullq/persistence/native_listing_lifecycle.py`; `src/hullq/application/listing_intake.py`; current FastAPI auth/broker routes; current Astro broker API boundary.  
**Already implemented / not re-decided:** durable provider-agnostic HullQ Account; Auth0-compatible login/session; professional Organization/Membership authorization; professional NativeListing persistence/lifecycle; public listing/Search truth; marketplace field registry; broker privileged-role MFA semantics.  
**Exact remaining gap:** an Account with zero professional memberships has no distinct, durable, private owner-direct workspace in which to preserve sale-listing work before later publication eligibility exists.  
**Accepted-but-unimplemented obligations:** owner-direct write path required by `REQ-PRIVATE-022`; broader owner-direct publication/trust/fraud/representation requirements remain accepted but explicitly outside this slice; Broker `REQ-BROKER-023/024/025/026/027/028/029` and sale-outcome obligations remain pending under their existing triggers.  
**Material classifications:** `DECIDED_AND_IMPLEMENTED` for Account/session and professional marketplace paths; `DECIDED_NOT_YET_IMPLEMENTED` for owner-direct draft/write lane and later private publication controls; `EXPLICITLY_DEFERRED` for verification/fraud/representation/referral/media/publication capabilities outside this slice.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** NOT_DUE

Evidence:

- no real external marketplace production data/pilot/public launch is introduced by this implementation slice;
- accepted technical native Search criteria count remains 1;
- owner-direct draft data is private workspace state and cannot enter current public listing/Search paths;
- Broker Workspace mandatory commitments remain OPEN/PENDING under their existing launch/scale/search-volume triggers.

## Why this slice exists

The owner-direct pivot is product direction only until a real private seller can begin work in HullQ.

The current implementation cannot safely satisfy that by reusing `NativeListing`:

```text
current NativeListing
→ non-null publishing_organization_id
→ professional Organization eligibility
→ professional membership authorization
```

Making that Organization nullable or fabricating a private-seller Organization would silently widen proven professional semantics across persistence, lifecycle, offer revisions, public reads and Search.

A dedicated pre-market draft avoids that regression and creates a useful visible seller lane immediately:

```text
HullQ Account
→ private draft
→ save/reopen
```

Later publication remains a separate explicit admission step:

```text
private draft
→ phone + right-to-list attestation + anti-abuse / applicable escalation
→ future marketplace admission
```

The latter is not implemented here.

## Controlling artifacts

- Requirement IDs: `REQ-PRIVATE-022` primary; supporting `REQ-PRIVATE-001`, `REQ-PRIVATE-003`, `REQ-PRIVATE-005`, `REQ-PRIVATE-012`, `REQ-PRIVATE-023`, `REQ-PRIVATE-024`
- Specifications: `specs/OWNER_DIRECT_DRAFT_CONTRACT.v0.1.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`; `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`; existing NativeListing contracts as non-regression boundaries
- Accepted ADRs / architecture: `architecture/SYSTEM_ARCHITECTURE.md`; accepted 2026-09-02 architecture rebaseline where not superseded
- Governance / research protocols: `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; Broker Workspace Launch Gate / Mandatory Capability Register
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md`
- Current owner-direct direction: `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`
- Relevant open questions: none that block this bounded private-draft capability

## In scope

1. One dedicated durable `OwnerDirectListingDraft` persistence boundary tied to HullQ `AccountId`.
2. Server-generated opaque `OwnerDirectListingDraftId`, distinct from all marketplace identity IDs.
3. Finite v0.1 draft payload exactly as defined by `OWNER_DIRECT_DRAFT_CONTRACT.v0.1`.
4. Incomplete draft save/reopen.
5. Atomic optimistic concurrency/version conflict protection.
6. FastAPI owner-direct draft list/create/read/update endpoints.
7. Server-side account ownership enforcement and non-enumerating foreign/unknown draft behavior.
8. Explicit CSRF defense for state-changing cookie-authenticated draft writes.
9. Bounded extension of the login `next` allowlist for `/sell/direct...` only.
10. Astro `/sell/direct` private draft index/start surface.
11. Astro `/sell/direct/{draft_id}` private edit/save/reopen surface.
12. Private/no-store/noindex response behavior.
13. PostgreSQL 18 retained end-to-end proof from local OIDC login through built Astro/FastAPI to durable draft readback.
14. Non-regression proof that draft operations create no marketplace identities/listing/offer facts and do not alter professional Broker Workspace behavior.

## Explicitly out of scope

- owner-direct public publication/admission;
- phone verification;
- right-to-list attestation;
- anti-abuse/fraud scoring or escalation engine;
- ID/selfie/liveness verification;
- Sale Authority verification/badges;
- PhysicalBoat/MarketEpisode/representation-conflict resolution for private sellers;
- generalization of NativeListing publishing principal;
- changes to professional publishing eligibility;
- changes to Broker Workspace roles/MFA;
- owner-direct Search eligibility/ranking;
- technical Search criterion changes;
- media/photos/document uploads;
- narrative-field redesign;
- broker referral flow;
- private-to-broker handoff;
- payments/subscriptions/verification monetization;
- escrow/transaction handling;
- delete/archive workflow;
- offline mode, autosave or a generic draft framework;
- broad SEO/indexable seller pages;
- SLICE-0055 selection or implementation.

## Required behavior

### A. Draft identity is pre-market only

The implementation MUST enforce:

```text
OwnerDirectListingDraftId
!= NativeListingId
!= PhysicalBoatId
!= MarketEpisodeId
```

No draft operation may write `physical_boats`, `market_episodes`, `native_listings`, NativeListing offer/fact revisions or Search state.

### B. Generic Account auth, not professional membership

An authenticated HullQ Account with zero Organizations/memberships MUST be able to use the draft workspace.

Ownership always derives from the signed session's `AccountId`. A payload/URL field cannot nominate a different owner.

Professional broker access behavior remains unchanged.

### C. Private ownership and enumeration resistance

- no/invalid session -> 401/API unauthenticated browser state;
- own draft -> accessible;
- foreign draft and unknown draft -> same 404 behavior;
- list returns only own drafts;
- Organization membership grants no cross-account access.

### D. Bounded payload

Only the keys and validation defined in `OWNER_DIRECT_DRAFT_CONTRACT.v0.1` are accepted.

Unknown keys fail closed. Incomplete drafts remain valid. No missing value is guessed or synthesized.

### E. Save conflict protection

Every update supplies `expected_version` and atomically advances version only if current. Stale update -> 409, zero mutation.

### F. Login return path

The existing signed login-state safe-next logic is extended only to `/sell/direct` and its child paths while retaining `/broker` behavior and rejecting external/open redirects.

### G. Browser write security

POST/PUT owner-direct draft mutations require both:

- exact accepted HullQ browser `Origin`;
- fixed non-simple HullQ request header per the draft contract.

Missing/mismatched CSRF evidence fails 403 before mutation. No permissive credentialed CORS is introduced.

### H. Browser UX

`/sell/direct` lets an authenticated Account see its own drafts and start one.

`/sell/direct/{draft_id}` lets the owner edit and save the bounded draft fields.

Both clearly display `Draft — not public` or equivalent. There is no Publish action and no implication of verification or Search exposure.

### I. Cache/indexation/privacy

Draft APIs/pages use private/no-store. Pages are noindex. Session tokens and private payloads do not leak to browser-readable auth state, public URLs or error/log output.

## Deliverables

- Alembic migration for the dedicated owner-direct draft table;
- domain/application/persistence implementation for bounded draft create/list/read/update and optimistic versioning;
- FastAPI routes and CSRF enforcement;
- safe login-next extension;
- Astro owner-direct draft index/edit surfaces and bounded API adapter/proxy as needed without duplicating domain semantics;
- unit/persistence/API/web tests;
- retained PostgreSQL 18 + local OIDC/JWKS + built Astro vertical proof;
- any minimal docs/code comments required to keep the professional-vs-owner-direct boundary explicit.

## Acceptance criteria

- [ ] A real authenticated HullQ Account with no professional membership can open the owner-direct draft workspace.
- [ ] The Account can create a private empty/partial draft and receive a stable opaque draft ID/version.
- [ ] The Account can save valid bounded draft fields and reopen/read exactly the persisted values from PostgreSQL.
- [ ] The Account's draft index returns only that Account's drafts in deterministic order.
- [ ] Updating with the current version atomically advances the version.
- [ ] Updating with a stale expected version returns 409 and leaves the newer data unchanged.
- [ ] A second authenticated Account cannot read or modify the first Account's draft; foreign and unknown IDs have the same direct-object 404 behavior.
- [ ] Missing/tampered/expired session fails closed.
- [ ] Cross-origin or missing-required-header mutation fails 403 before any write.
- [ ] `/api/auth/login?next=/sell/direct...` preserves only allowed internal seller paths; open-redirect adversarial cases remain rejected.
- [ ] `/broker...` login-next and Broker Workspace authorization/MFA regressions remain green.
- [ ] Draft pages visibly state that the object is not public and expose no Publish action.
- [ ] Draft page/API responses are private/no-store and page responses noindex.
- [ ] Draft operations create zero PhysicalBoat, MarketEpisode, NativeListing, NativeListing offer/fact revision or Search-side marketplace records.
- [ ] Full repository contract validation, formatting, lint, type checks and required tests pass locally.
- [ ] PostgreSQL 18 retained end-to-end proof passes using a local deterministic OIDC/JWKS issuer and built Astro surface.
- [ ] Required GitHub Actions CI jobs pass on the exact implementation head.
- [ ] Manufacturer artifact reproducibility passes on the exact implementation head.

## Expected touch points

Expected only as justified by implementation:

```text
migrations/versions/<0054 owner direct draft migration>.py
src/hullq/domain/owner_direct_draft.py
src/hullq/persistence/owner_direct_draft.py
src/hullq/application/owner_direct_draft.py
src/hullq/application/broker_login.py        # bounded safe-next extension only
src/hullq/api/app.py
web/src/lib/ownerDirectDraftApi.ts
web/src/pages/sell/direct/index.astro
web/src/pages/sell/direct/[draft_id].astro
scripts/inspect_owner_direct_draft.py
tests/unit/...
tests/persistence/...
web/src/lib/__tests__/...
```

Equivalent names are acceptable if they preserve the contract. Do not refactor unrelated broker/listing architecture merely to improve naming.

## Validation

Implementation handoff must run the repository's normal full validation plus focused tests and the retained SLICE-0054 proof. At minimum:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src tests scripts
uv run pytest

cd web
npm ci
npm run check
npm run build
npm test
```

The retained proof must run against PostgreSQL 18 and exercise the real FastAPI/auth/session/persistence/built-Astro path specified by `OWNER_DIRECT_DRAFT_CONTRACT.v0.1`.

## Stop conditions

Stop and report `BLOCKED` rather than inventing behavior if:

- implementation requires making a private seller a fake professional Organization/member;
- the existing `native_listings` professional principal must be made nullable/generalized to complete this slice;
- implementation requires creating PhysicalBoat/MarketEpisode/NativeListing during draft save;
- phone/attestation/fraud/verification/publication semantics are required to make the private draft function;
- a required write cannot be protected from cross-account access or CSRF without a material auth/session redesign beyond this slice;
- the bounded field contract proves incompatible with useful incomplete draft save;
- a post-0051 trigger gate becomes due during implementation;
- scope expands into media, referral, Search, publication or a generic drafting framework.

## Status handoff rule

The implementation/research agent may recommend or set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, explicit Project Owner acceptance and closure through the project workflow.

A successful implementation handoff therefore ends in `REVIEW` and does not start SLICE-0055.

## Required completion report

Use the standard structure in `docs/slices/SLICE_TEMPLATE.md`, including the exact final implementation branch HEAD SHA, local validation, remote CI/Manufacturer state, unresolved findings and the agent declarations.

The report must explicitly confirm:

- no work outside SLICE-0054 was started;
- no acceptance criterion was marked passed without verification;
- SLICE-0055 was not selected or started;
- the agent has NOT marked SLICE-0054 `DONE`.