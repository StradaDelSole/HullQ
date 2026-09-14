# HullQ — Post-SLICE-0052 Capability Reassessment

**Date:** 2026-09-14  
**Status:** OWNER-ACCEPTED CAPABILITY SELECTION when merged  
**Accepted through:** explicit Project Owner approval of Option A in the post-SLICE-0052 reassessment  
**Selected next slice:** SLICE-0053 — Authenticated Broker Workspace Access Boundary

## 1. Reassessment basis

SLICE-0052 is owner-accepted and closed. Canonical `main` now provides the buyer-side path:

```text
technical Search
→ ACTIVE native professional inventory
→ evidence-backed freshness admission
→ trustworthy current listing
```

The next capability was reassessed against:

- `docs/PROJECT_STATE.md`;
- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§10–11;
- `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`;
- `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`;
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`;
- `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`;
- `docs/governance/OPEN_QUESTIONS.md`, especially OQ-014;
- accepted SLICE-0041 and SLICE-0052 implementation state;
- current production code, migrations and Astro route tree.

## 2. Repository reconciliation

### DECIDED_AND_IMPLEMENTED

Already implemented and not reopened:

- runtime-distinct HullQ `AccountId`, `MarketplaceOrganizationId`, `OrganizationMembershipId` types;
- professional Organization category / publishing-eligibility vocabulary;
- Membership state / role vocabulary;
- deterministic SLICE-0041 professional publishing-eligibility evaluator;
- FastAPI as sole application/domain API boundary;
- Astro + TypeScript as the web/presentation surface;
- PostgreSQL 18 + Alembic as production persistence/migration baseline;
- NativeListing ownership envelope currently stores publishing Organization ID and creating Account ID;
- buyer-side public listing/Search/freshness capabilities through SLICE-0052.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted architecture that is still absent from production code:

- Auth0 Public Cloud EU login/session integration;
- durable HullQ Account persistence;
- provider-agnostic `(provider/issuer, subject) -> AuthIdentity -> HullQ Account` mapping;
- durable marketplace Organization directory;
- durable OrganizationMembership / role persistence;
- server-side authenticated broker authorization from HullQ-owned PostgreSQL state;
- protected external Broker Workspace surface;
- MFA enforcement for publishing-capable and Organization Owner/Admin broker accounts.

The existing `src/hullq/domain/publishing_eligibility.py` explicitly states that SLICE-0041 did not persist marketplace actors, integrate Auth0, enforce MFA or expose API/UI. Current Alembic history contains no account/organization/membership actor-directory migration. Current Astro routes contain no broker workspace.

### EXPLICITLY_DEFERRED

Remain future bounded capabilities after the access boundary exists:

- broker listing create/edit/resume workflow;
- connectivity-resilient listing drafts (`REQ-BROKER-024`);
- broker branding/media (`REQ-BROKER-023` plus media workflow);
- leads, attribution, lead workflow and analytics;
- commercial/deal/sale outcome workflows;
- bulk onboarding/import;
- inventory export/portability;
- Search-fit diagnostics and later Search-exclusion/demand insights;
- payments/subscriptions/entitlements;
- production deployment/readiness work while its trigger remains inactive.

### GENUINELY_OPEN

No provider-selection question is open: OQ-014 is already DECIDED. Bounded implementation details may be chosen during SLICE-0053 only when they do not change the accepted provider/authentication/authorization boundary.

### CONFLICT_OR_REGRESSION

None found.

## 3. Mandatory Capability Register check

The mandatory register was explicitly inspected as required.

Current state:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING
REQ_BROKER_022_STATUS: PENDING
REQ_BROKER_023_STATUS: PENDING
REQ_BROKER_024_STATUS: PENDING
REQ_BROKER_025_STATUS: PENDING
REQ_BROKER_026_STATUS: PENDING
REQ_BROKER_027_STATUS: PENDING
REQ_BROKER_028_STATUS: PENDING
REQ_BROKER_029_STATUS: PENDING
REQ_BROKER_030_STATUS: IMPLEMENTED
```

No broker requirement is currently `DUE`. No trigger changed after SLICE-0052: scaled onboarding has not started, sufficient Search volume has not been declared, no broker pilot exists, and paid/public launch remains inactive.

REQ-BROKER-023 and REQ-BROKER-024 remain launch/pilot-baseline commitments, but implementing either before a real authenticated Organization/member workspace would invert the dependency order. SLICE-0053 therefore preserves them as mandatory `PENDING` commitments and creates the access/tenant boundary on which their later implementation depends.

## 4. Trigger gates

```text
architecture/current-state reconciliation: PASS
production readiness: NOT_TRIGGERED
external broker production data: NOT_PRESENT
production pilot: NOT_STARTED
public production launch: NOT_STARTED
broker workspace launch gate: NOT_READY
technical native Search criteria: 1
workflow reassessment: NOT_DUE
```

SLICE-0053 does not add a technical Search criterion and does not activate real external broker production data or a real external broker pilot. Production Readiness therefore remains NOT_TRIGGERED.

## 5. Alternatives considered

### Option A — Authenticated Broker Workspace Access Boundary — SELECTED

```text
Auth0 EU identity
→ HullQ-owned durable Account
→ durable Organization
→ durable Membership + roles
→ server-side HullQ authorization
→ protected Broker Workspace surface
```

This is the smallest capability that turns the already-accepted broker identity/authorization architecture into a visible, usable product boundary and unlocks later broker inventory/lead workflows without temporary operator-only ownership shortcuts.

### Option B — Lead / ContactRequest + attribution

High product value, but premature before a durable authenticated Organization/account ownership boundary exists for the receiving professional user.

### Option C — Broker listing create/edit/resume

High product value, but implementing it first would require temporary actor/authorization shortcuts that would immediately need replacement under the already accepted Auth0/HullQ identity architecture.

### Option D — second technical Search criterion

Would broaden the already-working buyer side while leaving the strategically equal provider-side Broker Workspace at effectively zero external self-service capability.

### Option E — Saved Search / monitoring

Important later buyer monetization surface, but lower current leverage than opening the professional supply-side access boundary.

## 6. Owner selection

The Project Owner explicitly selected Option A.

Selected capability:

> **SLICE-0053 — Authenticated Broker Workspace Access Boundary**

The capability must remain one vertical. It may include the persistence, provider-authentication adapter, server-side authorization and minimal protected Astro surface necessary to prove that one external authenticated identity maps to HullQ-owned tenant truth. It must not expand into listing CRUD, media, leads, sales, analytics or payments.

## 7. Expected visible product result

At completion, a browser-visible broker access path must prove all of these states:

```text
unauthenticated browser
→ cannot enter Broker Workspace

authenticated Auth0 identity with no HullQ OrganizationMembership
→ HullQ Account exists/mapping is stable
→ no Organization workspace access

authenticated identity with active HullQ membership
→ can see/select only its authorized Organization context

cross-Organization URL/API attempt
→ denied server-side without tenant-data leakage

publishing-capable / Owner / Admin membership without required MFA evidence
→ privileged workspace access fails closed / requires MFA

same privileged member with valid MFA authentication context
→ protected Organization workspace landing is available
```

No listing mutation is required in SLICE-0053.

## 8. Next workflow step

The selected capability still requires an exact readiness contract, independent readiness review, green remote gates and merge to canonical `main` before the Project Owner may run `START_SLICE.bat 0053`.
