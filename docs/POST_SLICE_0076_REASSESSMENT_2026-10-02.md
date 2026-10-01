# Post-SLICE-0076 Reassessment — 2026-10-02

**Status:** OWNER-DIRECTED / READY FOR SLICE DEFINITION  
**Canonical base:** `ee22cb1a572458e2224a071e285450b84a706f58`

## Context

SLICE-0076 is owner-accepted, merged, closed and locally finished.

The accepted Broker Workspace Launch Validation result is:

```text
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
DISPOSITION: REMEDIATION_REQUIRED
BLOCKING_DEFICIENCY: Lead assignment discoverability
```

The blocking finding is concrete: the Lead detail surface accepts an assignee `AccountId`, but no ordinary Broker Workspace surface exposes a usable Organization member picker or otherwise discoverable assignee identity.

## Fresh Decision / Implementation Reconciliation

### DECIDED_AND_IMPLEMENTED

- Broker Organization auth / Membership / MFA boundary;
- durable Lead identity, inbox/detail and operational state;
- server-authoritative Lead assignment mutation;
- assignment fail-closed unless the target Account currently has ACTIVE membership in the exact Organization;
- Task-5 validation evidence proving the current browser assignment control is not completable by a representative broker;
- representative usability evidence + competitive benchmark from SLICE-0076.

### DECIDED_NOT_YET_IMPLEMENTED

- broker-visible Organization-scoped active-member assignment candidate projection;
- browser-visible selectable Lead assignee control;
- focused revalidation proving Task 5 completes without operator/API assistance;
- resulting reconsideration of the Broker Workspace Launch Gate after the blocker is removed;
- Security Hardening & Adversarial Validation gate before any real external broker self-service pilot.

### EXPLICITLY DEFERRED

- Organization membership administration/invite/remove UI;
- new member profile/display-name/email identity model;
- general staff directory;
- Lead inbox free-text search;
- bulk/drag-and-drop media reorder;
- design/configuration catalog-assisted draft authoring;
- external real-broker pilot;
- paid broker activation;
- broad public launch;
- new Search criteria.

### GENUINELY OPEN

- implementation-local shape of the read-only assignment-candidate projection;
- exact browser label for AccountId-backed members, provided it does not invent unavailable human identity;
- final Broker Workspace Launch Gate disposition after focused revalidation and independent review.

### CONFLICT_OR_REGRESSION

None.

## Overall MVP Capability Register reconciliation

Status consequence of accepted SLICE-0076 evidence:

```text
MVP-BROKER-013 usability evidence + competitive benchmark
→ evidence delivered/accepted by SLICE-0076
→ launch gate nevertheless remains NOT_READY because validation found a blocking deficiency

MVP-PROD-012 holistic Security Hardening & Adversarial Validation
→ still DUE before first external broker self-service pilot
```

The Security Hardening Gate explicitly permits execution after launch-readiness/usability/benchmark work and requires a coherent attack surface. Fixing the one accepted launch blocker before the holistic security pass is therefore the shortest safe path.

No buyer/owner-direct/support/legal/payment/production trigger changes merely because this remediation is selected.

## Repository implementation reconciliation

Current persistence already has authoritative exact-member reads and the existing Lead assignment mutation already rejects a non-active/foreign assignee.

What does **not** exist is a read projection listing the exact Organization's ACTIVE memberships for the authorized broker UI.

Therefore the remediation does not require:

- a new Organization identity;
- email-as-identity;
- Auth0 role/organization claims;
- client-authoritative AccountId input;
- membership administration.

It requires one bounded server-authoritative read projection over existing OrganizationMembership truth, exposed only inside the already-authorized Organization Lead workflow.

## Selection

```text
SLICE-0077 — Broker Lead Assignment Discoverability Remediation
```

One coherent capability:

```text
current ACTIVE Organization memberships
→ authorized assignment-candidate projection
→ broker-visible assignee picker
→ existing server-authoritative assignment mutation
→ focused Task-5 revalidation
```

## Trigger gates

```text
PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
SECURITY_HARDENING_GATE_STATUS: DUE / NOT_STARTED
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS
```

No external pilot, paid activation, public launch or Search criterion is introduced.
