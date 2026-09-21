# SLICE-0062 — Professional Draft Connectivity Recovery

**ID:** SLICE-0062  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Status set by this handoff:** `REVIEW`  
**Stage:** Broker Workspace — connectivity-resilient professional draft editing  
**Depends on:** SLICE-0053 Broker Workspace access; SLICE-0061 Professional Listing Draft Workspace; accepted optimistic-version/CSRF/private-surface boundaries  
**Blocks:** no later slice automatically; closes one mandatory launch-baseline commitment only after accepted implementation/closure

## Objective

Deliver exactly one professional capability:

> Recent unsaved input on an existing authorized ProfessionalListingDraft survives ordinary connectivity interruption through bounded browser-local recovery, while PostgreSQL/FastAPI remain the only authoritative draft truth and newer server versions are never silently overwritten.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: connectivity-resilient recovery for the existing professional draft edit workflow.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can edit a professional draft, interrupt the save/network path, reopen the same draft and see recent unsaved values recovered; a newer server version prevents silent auto-restore/overwrite; a successful retry save clears the local recovery state.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
REQ-BROKER-024 is an accepted launch/pilot baseline commitment. 0061 established the server draft/version surface required to implement it cleanly. 0062 prevents daily broker work from being lost without expanding into generalized offline sync.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current Broker Workspace auth/MFA/current-membership roles, 0061 professional draft ownership/version/CSRF/browser behavior, owner-direct shared-field semantics, mandatory broker register, Broker Workspace Launch Gate, NativeListing intake/persistence/publishing boundaries and current marketplace field writers were inspected.

**TRIGGER GATES CHECK:** PASS  
Production Readiness remains `NOT_TRIGGERED`; Broker Workspace Launch Gate remains `NOT_READY`; workflow reassessment remains `PASS`; 0062 adds no Search criterion, external production data, pilot, paid plan or public launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0061_REASSESSMENT_2026-09-21.md`; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`; `docs/slices/SLICE-0061-acceptance-closure.md`; `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`; `specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`.

**Production implementation checked:** `web/src/pages/broker/organizations/[organization_id]/drafts/[draft_id].astro`; `web/src/lib/professionalDraftApi.ts`; `web/src/lib/brokerApi.ts`; `src/hullq/application/professional_listing_draft.py`; `src/hullq/persistence/professional_listing_draft.py`; `src/hullq/api/app.py`; listing intake/lifecycle/offer/PhysicalBoat-claim writers; tests and retained proofs.

**Already implemented / not re-decided:** current Account/Organization/Membership/PUBLISHER/MFA authorization; Organization-owned professional draft; server partial-draft persistence; optimistic version conflicts; accepted CSRF; private/no-store/noindex; marketplace non-promotion; FastAPI/PostgreSQL authority.

**Exact remaining gap:** recent form edits made after the last successful server save can be lost when ordinary connectivity interruption prevents a save/navigation from completing.

**Accepted-but-unimplemented obligations:** REQ-BROKER-024 explicitly requires recoverable local/equivalent client-side draft behavior in addition to server persistence. 0062 implements only this bounded recovery layer.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` server draft/auth/version boundaries; `DECIDED_NOT_YET_IMPLEMENTED` REQ-BROKER-024 local recovery; `EXPLICITLY_DEFERRED` promotion/publication/media/branding/leads/analytics/offline-first; `GENUINELY_OPEN` later lossless promotion and richer sync architecture; `CONFLICT_OR_REGRESSION` none found.

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

The current workflow is:

```text
server draft version N
→ broker types additional edits in browser
→ network/save failure
→ unsaved edits may disappear
```

Server persistence alone does not satisfy REQ-BROKER-024 because the loss occurs before the server receives a valid save.

0062 adds the smallest client-side recovery buffer needed to close that gap while preserving server truth and optimistic concurrency.

## Controlling artifacts

- Normative contract: `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`
- Professional draft contract: `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`
- Broker requirements: `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`
- Broker product direction: `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`
- Broker mandatory register: `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`
- Broker launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`

## In scope

- browser-local recovery for existing professional draft edit page only;
- Account + Organization + ProfessionalListingDraft scoping;
- base server version in recovery envelope;
- exact bounded 0061 form-value capture;
- 24-hour maximum local recovery age;
- fail-closed malformed/expired entry handling;
- recovery after simulated network/save interruption;
- same-version safe form restoration;
- visible "recovered unsaved changes" state;
- newer-server-version conflict state with no silent auto-restore;
- explicit stale-copy restore-for-review and discard behavior;
- local recovery clear after successful durable server save;
- retention after network/conflict/validation failure;
- graceful browser-storage-unavailable state;
- no auth/session material in local storage;
- focused TypeScript/browser-state tests;
- real protected Astro/FastAPI/PostgreSQL non-regression proof/wiring;
- preservation of all 0061 auth/tenant/CSRF/version/non-promotion behavior.

## Explicitly out of scope

- PhysicalBoat/MarketEpisode/NativeListing creation;
- draft promotion/publication;
- NativeListing edit/publish/withdraw/reconfirm;
- owner-direct recovery;
- background server autosave;
- generalized offline-first/PWA/Service Worker;
- multi-device synchronization;
- collaborative field merge;
- media;
- broker branding/profile completion;
- duplicate/clone/relist;
- Search-fit diagnostics;
- inventory export/import;
- leads/contact/CRM;
- sale outcomes;
- analytics/reporting;
- payments;
- third Search criterion;
- production pilot/public launch.

## Required behavior

### A. Local state is never authoritative

Local recovery only restores form values. Server authorization, validation, durable persistence and optimistic versioning remain authoritative.

### B. Exact recovery scope

Recovery is scoped to the current Account + Organization + draft. Foreign Account/Organization/draft buffers never auto-apply.

### C. Bounded retention

Recovery expires after 24 hours maximum. Malformed/future schema/expired entries fail closed.

### D. Safe same-version restore

A valid matching local copy based on the current server version may repopulate the form and must be visibly identified as recovered unsaved work.

### E. Safe newer-server handling

If server version advanced since local capture, do not auto-restore or auto-submit. Show a clear conflict/recovery state and require explicit user action to restore for review or discard.

### F. Explicit Save remains synchronization

No background retry queue or background server autosave. Existing Save remains the server mutation path.

### G. Failure retention

Network/service failure, validation failure and version conflict must not silently destroy the local recovery copy.

### H. Successful save cleanup

A successful server save clears the matching local recovery envelope.

### I. Storage failure does not break drafting

If browser storage is unavailable, ordinary server draft editing still works and the UI does not falsely claim recovery is active.

### J. Security

Never store session/auth/MFA/credential material. Restore values through form-control APIs, never executable HTML insertion.

## Deliverables

1. bounded professional draft recovery state/envelope module;
2. browser wiring on the existing professional draft edit surface;
3. Account-scoped recovery namespace using accepted private Broker Context or equivalent;
4. visible normal/recovered/conflict/unavailable recovery states;
5. focused web tests with simulated connectivity failure;
6. retained real PostgreSQL/FastAPI/built-Astro proof/wiring demonstrating server non-regression;
7. CI execution of required tests/proof;
8. handoff to `REVIEW`, never `DONE`.

## Acceptance criteria

- [x] Recovery applies only to an existing authorized professional draft.
- [x] Recovery key/envelope is scoped to current Account + Organization + draft.
- [x] Different Account recovery never auto-applies.
- [x] Different Organization recovery never auto-applies.
- [x] Different draft recovery never auto-applies.
- [x] All editable 0061 form fields and broker reference are recoverable.
- [x] No session cookie/OIDC/MFA/credential material is stored.
- [x] Recovery expires after at most 24 hours.
- [x] Malformed/unknown-schema recovery fails closed.
- [x] Browser storage errors do not break server editing.
- [x] UI does not falsely claim recovery when storage is unavailable.
- [x] Local capture occurs before an explicit save navigation can lose current input.
- [x] Simulated network failure leaves PostgreSQL unchanged and local recovery intact.
- [x] Same-version reopen restores recent unsaved values visibly.
- [x] Restore never mutates server state until explicit Save.
- [x] Newer server version prevents silent auto-restore.
- [x] Stale local recovery can be explicitly discarded.
- [x] If stale-copy restore-for-review exists, it remains form-only until explicit Save.
- [x] Server version conflict retains local recovery and does not overwrite.
- [x] Validation failure retains local recovery.
- [x] Successful server save advances the accepted version exactly once and clears local recovery.
- [x] Existing PUBLISHER/MFA/current-membership/non-enumeration behavior is unchanged.
- [x] Existing CSRF defense is unchanged.
- [x] Existing professional-draft field validation is unchanged.
- [x] Existing marketplace non-promotion guarantee is unchanged.
- [x] Owner-direct behavior is unchanged.
- [x] Search criterion count remains exactly two.
- [x] REQ-BROKER-024 remains PENDING until implementation owner-acceptance closure.
- [x] REQ-BROKER-023 remains PENDING.
- [x] Broker Workspace Launch Gate remains NOT_READY.
- [x] Repository validation/lint/type-check/Python tests/web tests/check/build pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if a smaller equivalent implementation is proved:

- new `web/src/lib/professionalDraftRecovery.ts` or equivalent bounded recovery module;
- focused web tests for the recovery state machine/storage behavior;
- `web/src/pages/broker/organizations/[organization_id]/drafts/[draft_id].astro`;
- existing `web/src/lib/brokerApi.ts` may be reused to obtain current AccountId;
- existing 0061 retained proof may be extended, or one new bounded retained proof may be added;
- `.github/workflows/ci.yml` only if needed to wire a new retained proof.

No database migration is expected.

## Validation

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python -m pytest
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
```

Run/report the exact retained 0062 recovery proof command selected by implementation.

## Stop conditions

Stop and report instead of inventing a solution if:

- recovery requires a second server draft truth model;
- implementation weakens current optimistic concurrency;
- local recovery can bypass current Account/Organization/PUBLISHER/MFA authorization;
- session/auth/MFA secrets would need to enter browser storage;
- another Account/Organization/draft can auto-load the local copy;
- stale recovery is silently auto-applied over newer server state;
- implementation requires generalized offline-first/service-worker synchronization;
- scope expands into promotion/publication/media/branding/leads/analytics;
- a production-data/pilot/paid-plan/launch trigger changes.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED` with the matching explicit handoff line, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0063.
