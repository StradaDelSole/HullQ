# SLICE-0071 — Broker Lead Operating Surface + Durable Email Notification

**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker launch path — broker handles Lead  
**Depends on:** SLICE-0070 owner-accepted / DONE  
**Normative contract:** `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`

## Capability

Deliver one coherent broker outcome:

```text
durable Lead
→ authorized Organization inbox/detail
→ assignment/status/read/notes/follow-up history
+ durable notification/outbox
→ retryable HullQ email notification
→ dashboard deep-link
```

Broker Workspace is authoritative; email is notification only.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One broker-facing “receive and handle a Lead” vertical.

**VISIBLE-RESULT CHECK:** PASS  
A broker can see, open and operate the Lead in Broker Workspace, and the notification pipeline has durable observable delivery state.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is step E immediately after accepted SLICE-0070 step D.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current `main`, D33/D34/D35, Broker Workspace Launch Gate, mandatory register, existing Lead creation and Broker Workspace auth were reconciled. No competing Lead-operations or notification model exists.

**TRIGGER GATES CHECK:** PASS  
No Search criterion, external broker pilot, paid plan, public production launch or production email-provider activation is introduced.

## Decision / implementation reconciliation

**Accepted records checked:** docs/PROJECT_STATE.md; docs/slices/SLICE-0070-acceptance-closure.md; docs/POST_SLICE_0070_REASSESSMENT_2026-09-29.md; docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md (D33/D34); docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md; docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md; docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md; docs/governance/POST_0051_TRIGGER_GATES.md.  
**Production implementation checked:** current buyer Lead domain/persistence/application/FastAPI/Astro implementation; current Broker Workspace Organization authorization/membership/MFA and inventory web/API patterns; current PostgreSQL migration and private mutation patterns.  
**Already implemented / not re-decided:** SLICE-0070 immutable durable Lead envelope/idempotency/D29 creation gate; current MarketplaceOrganization ownership; current OrganizationMembership roles/state; existing Broker Workspace session/MFA authorization; buyer email remains explicitly UNVERIFIED.  
**Exact remaining gap:** durable Leads exist but the publishing Organization has no Lead inbox/detail/operational workflow, no explicit notification-recipient configuration, no durable outbox/delivery state and no HullQ email notification boundary.  
**Accepted-but-unimplemented obligations:** D33 authoritative Broker Lead operations; D34 OWNER/ADMIN notification routing; D35 provider-neutral notification/CRM signal ownership; durable notification/outbox + retryable delivery; buyer-contact email verification remains mandatory later and production-provider activation remains later Production Readiness work.  
**Material classifications:** DECIDED_AND_IMPLEMENTED foundations; DECIDED_NOT_YET_IMPLEMENTED 0071 scope and mandatory later verification/provider work; EXPLICITLY_DEFERRED generalized CRM/multi-recipient/SMS/scoring/cross-Organization transfer; GENUINELY_OPEN implementation-local factoring; CONFLICT_OR_REGRESSION none.


### DECIDED_AND_IMPLEMENTED

- durable Lead creation and immutable buyer/listing/Organization/source attribution;
- explicit buyer-email UNVERIFIED state;
- current OrganizationMembership and Broker Workspace auth/MFA foundations;
- Organization-owned inventory workspace;
- buyer contact retry/concurrency guarantees.

### DECIDED_NOT_YET_IMPLEMENTED — owned by 0071

- Organization Lead inbox/queue and unread indication;
- Lead detail;
- assignment to current ACTIVE same-Organization membership;
- bounded broker operational status;
- append-only notes/timeline and follow-up visibility;
- Organization primary Lead-notification email configuration;
- OWNER/ADMIN-only notification routing mutation;
- durable notification/outbox state;
- provider-agnostic retryable email delivery;
- test/local delivery adapter and retained end-to-end proof.

### DECIDED_NOT_YET_IMPLEMENTED — mandatory later

- production email-provider activation/credentials/observability;
- buyer-contact email verification;
- post-promotion inventory editing;
- sale/outcome workflow;
- structured bulk onboarding;
- broker engagement reporting.

### EXPLICITLY_DEFERRED

- multi-recipient routing beyond one primary address;
- SMS/phone notification;
- full CRM automation;
- lead scoring;
- cross-Organization Lead transfer;
- buyer-visible messaging;
- provider-specific production integration;
- analytics/reporting;
- inventory editing.

### GENUINELY_OPEN

Implementation-local schema/module names, exact UI composition, bounded page/note limits, exact optimistic-concurrency token shape, internal worker entrypoint and local test adapter.

### CONFLICT_OR_REGRESSION

None found.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Buyer contact email verification:** PENDING  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY

## Mandatory invariants

1. Broker Workspace remains Lead source of truth.
2. Email-only handling is insufficient.
3. Cross-Organization Lead access/mutation is non-enumerating and impossible.
4. Current membership truth is rechecked on every private request.
5. Notification routing comes from explicit HullQ Organization configuration, never Auth0/buyer email.
6. Only current ACTIVE OWNER/ADMIN can change notification address.
7. Assignment target is current ACTIVE member of same Organization.
8. Lead operational status is distinct from listing lifecycle and delivery state.
9. Notes are append-only broker history and never overwrite buyer message.
10. Lead creation + required outbox intent is atomic/idempotent.
11. Email failure never loses/hides/rolls back Lead.
12. Buyer contact email remains UNVERIFIED unless a later verification capability changes it with evidence.
13. External production email provider is not activated in this slice.
14. Listing/Search/public truth remains untouched.
15. Notification/provider identities and telemetry remain transport/workflow metadata; they never redefine Lead identity, buyer intent, Lead quality or Search/listing truth.
16. The outbox/delivery and timeline foundations remain extensible for later provider telemetry and CRM events without implementing those later capabilities in 0071.

## Scope

Implementation may span:

- Lead operational domain/value types;
- PostgreSQL migrations for workflow/timeline/config/outbox;
- Lead inbox/detail persistence/application projections;
- authorized broker mutations;
- notification-recipient configuration;
- delivery port + deterministic local/test adapter;
- retry/claim delivery worker/application service;
- FastAPI routes;
- Astro Broker Workspace pages;
- real PostgreSQL concurrency tests;
- retained FastAPI + built Astro + PostgreSQL vertical proof.

## Readiness stop conditions

Stop for reassessment if implementation requires:

- changing SLICE-0070 immutable Lead truth;
- using Auth0 email as notification routing authority;
- weakening fresh OrganizationMembership authorization;
- a production email vendor as domain authority;
- buyer email verification semantics;
- generalized CRM/sales/outcome semantics;
- Search/listing lifecycle changes.

## Acceptance

Independent exact-head review must verify tenancy/auth, operational concurrency, atomic notification intent, retry delivery behavior, privacy/verification separation and the retained vertical proof.

Owner Acceptance remains mandatory before merge.

Initial implementation prompt must come only from `START_SLICE.bat` after readiness review, remote gates and readiness merge.
