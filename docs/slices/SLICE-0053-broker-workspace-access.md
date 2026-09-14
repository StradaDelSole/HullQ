# SLICE-0053 — Authenticated Broker Workspace Access Boundary

**ID:** SLICE-0053  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** first external-professional Broker Workspace vertical  
**Depends on:** SLICE-0041, SLICE-0042, accepted Auth0/HullQ identity architecture, accepted Broker Workspace direction/governance, SLICE-0052 closure  
**Blocks:** honest self-service broker inventory workflow, tenant-safe leads/assignment, launch-gate section 1 completion

## Objective

Implement exactly one visible capability:

```text
Auth0-authenticated external identity
→ durable provider-agnostic HullQ Account
→ durable HullQ OrganizationMembership + roles
→ server-side tenant authorization
→ protected Broker Workspace landing
```

The slice turns accepted authentication/account architecture into a browser-visible professional access boundary without expanding into listing CRUD, media, leads or sales.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
Authentication adapter, durable actor identity, membership authorization, MFA gating and the minimal protected Broker Workspace page are necessary vertical parts of one capability: authenticated professional workspace access.

**VISIBLE-RESULT CHECK:** PASS  
The retained PostgreSQL 18 → FastAPI → Astro proof must visibly demonstrate unauthenticated denial, stable first-login Account mapping, no-membership denial, authorized Organization workspace access, cross-Organization denial and privileged-role MFA enforcement.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
HullQ now has a trustworthy buyer Search/listing path through SLICE-0052 while the accepted second core surface—the Broker Workspace—still lacks external authenticated self-service. Building the access/tenant boundary now unlocks later inventory and lead workflows without temporary operator-only identity shortcuts.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current code contains SLICE-0041 runtime eligibility types/evaluator but no durable Account/AuthIdentity/Organization/Membership actor directory, Auth0 integration, broker session/MFA boundary or broker Astro route. This slice implements accepted-but-unimplemented architecture rather than duplicating existing behavior.

**TRIGGER GATES CHECK:** PASS  
Architecture/current-state reconciliation is PASS; production readiness is NOT_TRIGGERED; this slice adds no technical native Search criterion; workflow reassessment is NOT_DUE; Broker Workspace Launch Gate remains NOT_READY and is not changed to PASS by this slice alone.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0052_REASSESSMENT_2026-09-14.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§10–11; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/OPEN_QUESTIONS.md` OQ-014; accepted SLICE-0041 and SLICE-0052 records.  
**Production implementation checked:** `src/hullq/domain/publishing_eligibility.py`; current persistence/migrations; `src/hullq/api/app.py`; current `web/src/pages/` tree; current security helpers.  
**Already implemented / not re-decided:** Auth0 provider selection/authentication-only boundary; FastAPI sole application/domain API boundary; Astro web layer; runtime Account/Organization/Membership/role eligibility vocabulary; professional publisher domain evaluator; PostgreSQL/Alembic baseline; current NativeListing ownership IDs.  
**Exact remaining gap:** no durable external-identity→HullQ-Account mapping, persisted actor directory/memberships, authenticated provider adapter/session, server-side tenant authorization surface or protected broker workspace.  
**Accepted-but-unimplemented obligations:** OQ-014 authenticated account architecture; durable HullQ Account/Organization/Membership role truth; server-side tenant isolation; MFA for publishing-capable/Owner/Admin broker memberships; launch-gate section 1.  
**Material classifications:** access boundary = `DECIDED_NOT_YET_IMPLEMENTED`; SLICE-0041 eligibility vocabulary/evaluator = `DECIDED_AND_IMPLEMENTED`; listing editor/media/leads/sales/payments = `EXPLICITLY_DEFERRED`; broad/indexable SEO remains `GENUINELY_OPEN` but unrelated; `CONFLICT_OR_REGRESSION` = none.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** NOT_DUE

Acceptance uses synthetic/test professional identities and disposable/local PostgreSQL state. This slice does not introduce real external broker production data, start a real broker pilot or activate public production launch.

## Broker Mandatory Capability Register check

The register was explicitly inspected before selection.

```text
no REQ-BROKER-022..029 item is DUE
REQ-BROKER-030 is IMPLEMENTED
sale/outcome remains PENDING
```

SLICE-0053 does not mark any mandatory-register item IMPLEMENTED merely by creating access.

- REQ-BROKER-023 broker identity/branding remains PENDING until actual broker/listing/media surfaces satisfy it.
- REQ-BROKER-024 connectivity-resilient draft recovery remains PENDING until the later listing workflow owns recoverable drafts.
- both remain mandatory before Broker Workspace Launch Gate PASS.

The access boundary is prerequisite infrastructure for these visible broker capabilities, but the slice remains product-visible through the protected workspace landing and is not foundation-only.

## Why this slice exists now

After SLICE-0052, the buyer side can discover and trust current inventory, but the provider side still has no external professional access path.

Accepted architecture already requires:

```text
Auth0 authentication-only
→ HullQ Account UUID
→ HullQ OrganizationMembership
→ HullQ roles/authorization in PostgreSQL
```

Building broker listing forms first would require temporary identity/tenant shortcuts that immediately conflict with accepted architecture.

Alternatives were lower leverage now:

- lead persistence/attribution needs a durable receiving Organization/account boundary;
- listing create/edit/resume should not be built on temporary operator identities;
- a second technical Search criterion broadens the already-working buyer side while provider-side access remains absent;
- Saved Search/monitoring is important but lower current leverage than opening the professional supply-side boundary.

## Controlling contract and requirements

Primary contract:

```text
specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md
```

Direct requirements owned by this slice:

```text
REQ-BROKER-014 — Organization/team context is first-class
REQ-BROKER-015 — authentication does not own authorization truth
```

`REQ-BROKER-001` is broader Broker Workspace product context and remains incomplete after this slice; 0053 must not mark the overall Broker Workspace complete or launch-ready.

This slice advances—but does not by itself complete—Broker Workspace Launch Gate §1 evidence.

## In scope

- Auth0 Public Cloud EU compatible browser authentication using the accepted authentication-only boundary.
- Provider-neutral validated authentication context in FastAPI/application code.
- Durable HullQ Account persistence.
- Durable AuthIdentity mapping from exact provider/issuer/subject to HullQ Account.
- JIT first-login Account/AuthIdentity creation with idempotent/concurrency-safe behavior and no email auto-linking.
- Durable marketplace Organization persistence compatible with `ProfessionalCategory` / `OrganizationPublishingEligibility`.
- Durable OrganizationMembership persistence compatible with `MembershipState` / `MembershipRole`.
- Multiple Organizations per Account, multiple Accounts per Organization, multiple roles per membership.
- Server-side FastAPI membership/tenant authorization and adversarial cross-Organization denial.
- MFA requirement for PUBLISHER, OWNER or ADMIN memberships from validated authentication-strength evidence.
- Minimal Astro `/broker` access surface and explicit Organization-scoped protected landing.
- Safe no-membership state and local logout/session invalidation.
- Alembic migration(s) for the bounded actor directory.
- Persistence/application/API/web tests.
- Retained real PostgreSQL 18 + FastAPI + built Astro proof using deterministic local OIDC/JWKS test issuer; no live Auth0 secret in CI.
- Optional manually runnable real Auth0 EU development-tenant smoke path when credentials are supplied outside the repository.

## Explicitly out of scope

- Listing create/edit/publish/withdraw/reconfirm broker UI/API.
- Self-service Organization creation, invitations, membership administration or ownership transfer.
- External broker verification/adjudication workflow.
- Media or public broker-branding completion.
- Connectivity-resilient listing drafts.
- Leads/contact requests, attribution, assignment, notes or CRM.
- Commercial/deal pipeline, sale/outcome or Days-on-Market workflow.
- Search-fit diagnostics, Search exclusion reporting or demand analytics.
- Bulk import or inventory export/portability.
- Saved Search, alerts or price intelligence.
- Payment/subscription/entitlements.
- Broad/indexable SEO.
- Production deployment/HA/observability or real external broker pilot.
- Auth0 Organizations/roles/app metadata as HullQ authorization truth.
- Auth0 Management API as marketplace authorization dependency.

## Required behavior

### A. Provider auth does not own HullQ authorization

Successful Auth0 authentication establishes provider identity evidence only. No Auth0 role, Organization, app metadata, email or client-side value may grant HullQ Organization access.

### B. Stable HullQ Account mapping

Validated `(provider, issuer, subject)` maps to one immutable HullQ Account. First authenticated use may create Account + AuthIdentity atomically. Retry/concurrent first login converges on the same account. Email never merges identities.

### C. Durable actor truth

Account, AuthIdentity, Organization, Membership and roles are durable PostgreSQL state. Migration must not invalidate existing historical/synthetic NativeListing actor IDs through unsafe retroactive FKs.

### D. Current membership determines access

Each protected Organization request uses current HullQ membership state. Missing/inactive membership denies. Membership/role changes affect the next authoritative read; stale provider claims cannot preserve rights.

### E. Tenant isolation

Organization path/query/API manipulation cannot grant another tenant. Unknown and unauthorized Organization access use a non-enumerating failure shape.

### F. MFA for privileged memberships

ACTIVE memberships containing PUBLISHER, OWNER or ADMIN require validated MFA evidence. Without it, workspace entry fails closed or triggers configured reauthentication/step-up.

### G. Browser/session safety

Auth callback/state/nonce/issuer/audience/signature/expiry validation fails closed. Provider/session secrets and tokens are not exposed to ordinary browser JavaScript storage. Local logout removes the HullQ session.

### H. FastAPI remains semantic owner

Astro owns browser presentation/navigation but fetches account/membership/Organization context through FastAPI. It never queries PostgreSQL directly or reimplements tenant authorization.

### I. Visible workspace states

```text
unauthenticated
→ no workspace data; login path

authenticated + zero active memberships
→ no Organization access state

authenticated + active membership
→ authorized Organization context only

cross-Organization request
→ denied without tenant leakage

privileged membership without MFA
→ blocked/step-up

privileged membership with MFA
→ Organization workspace landing
```

### J. Deterministic proof

CI uses a local deterministic OIDC/JWKS issuer and real token validation, not a direct Account monkeypatch. Proof runs against PostgreSQL 18, FastAPI and built Astro.

## Expected persistence shape

Equivalent normalized names are acceptable:

```text
accounts
  account_id PK
  created_at

auth_identities
  auth_identity_id PK
  account_id FK -> accounts
  provider
  issuer
  subject
  created_at
  UNIQUE(provider, issuer, subject)

marketplace_organizations
  organization_id PK
  professional_category
  publishing_eligibility
  created_at

organization_memberships
  membership_id PK
  account_id FK -> accounts
  organization_id FK -> marketplace_organizations
  state
  created_at

organization_membership_roles
  membership_id FK -> organization_memberships
  role
  UNIQUE(membership_id, role)
```

## Deliverables

- implementation of `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`;
- forward Alembic actor-directory migration(s);
- durable actor persistence/read models;
- AuthIdentity JIT mapping service;
- validated Auth0-compatible authentication adapter;
- server-side Organization authorization service;
- MFA authentication-strength normalization/enforcement for privileged memberships;
- minimum protected FastAPI broker-context endpoint(s);
- Astro login/session/callback/logout surface and protected Broker Workspace landing;
- adversarial tenant/MFA/token tests;
- `scripts/inspect_broker_workspace_access.py` or equivalent retained vertical proof;
- CI integration of the retained proof.

## Acceptance criteria

- [ ] Auth0 remains authentication-only; no Auth0 role/Organization/app metadata/email becomes HullQ authorization truth.
- [ ] Validated provider identity maps durably to immutable HullQ Account UUID.
- [ ] First-login mapping is atomic, idempotent and concurrency-safe; email never auto-links Accounts.
- [ ] Durable Organization/Membership/roles support many-to-many account↔organization membership and multiple roles.
- [ ] Existing accepted NativeListing historical/synthetic actor IDs remain migration-compatible; no unsafe global FK backfill.
- [ ] Invalid/expired/wrong-issuer/wrong-audience/unsigned/malformed authentication fails closed before broker data is returned.
- [ ] Auth flow validates state and OIDC nonce where applicable and keeps tokens/secrets out of browser JS storage.
- [ ] FastAPI is the sole tenant/role authorization owner; Astro has no direct PostgreSQL authorization path.
- [ ] Account with no ACTIVE membership gets no Organization workspace access.
- [ ] ACTIVE member sees/selects only authorized Organization contexts.
- [ ] Cross-Organization manipulation is denied with non-enumerating behavior.
- [ ] Current membership/role changes affect subsequent authorization without changing Auth0 roles/metadata.
- [ ] PUBLISHER/OWNER/ADMIN membership requires validated MFA evidence; missing MFA cannot silently enter privileged workspace.
- [ ] Minimal `/broker` surface and Organization-scoped landing are visible end to end.
- [ ] Local logout/session invalidation removes workspace access.
- [ ] Retained PostgreSQL18→FastAPI→Astro proof uses real token validation with deterministic local OIDC/JWKS fixture and demonstrates required states.
- [ ] CI needs no committed/live Auth0 credentials; optional real Auth0 EU development-tenant smoke remains secret/config driven.
- [ ] No listing CRUD, media, lead, sales, analytics, bulk import/export, Search expansion, payment or production-pilot capability is introduced.
- [ ] Mandatory Capability Register remains unchanged; REQ-BROKER-023/024 stay PENDING.
- [ ] `uv run python scripts/validate_repository.py`, Ruff, `mypy src`, full tests/coverage, web check/build/tests and PostgreSQL-18 CI pass on exact implementation head.
- [ ] Remote exact-head CI and independent review are clean before Project Owner acceptance.

## Stop conditions

Stop and return to readiness/Owner review instead of inventing semantics if implementation would require:

- Auth0 roles/Organizations/app metadata as HullQ authorization truth;
- a different authentication provider;
- weakened MFA policy for privileged broker memberships;
- self-service Organization/membership administration;
- broker listing mutation or lead/sales scope;
- changed broker-only public-supply policy;
- a production/live-broker trigger requiring Production Readiness Gate activation;
- a migration/backfill that could invalidate accepted existing NativeListing actor IDs without reviewed compatibility decision.
