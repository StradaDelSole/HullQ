# SLICE-0053 — Authenticated Broker Workspace Access Boundary

**ID:** SLICE-0053  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** first external-professional Broker Workspace vertical  
**Depends on:** SLICE-0041, SLICE-0042, accepted Auth0/HullQ identity architecture, accepted Broker Workspace product direction/governance, SLICE-0052 closure  
**Blocks:** honest self-service broker inventory workflow, tenant-safe leads/assignment, launch-gate section 1 completion

## Objective

Implement exactly one visible production capability:

```text
Auth0-authenticated external identity
→ durable provider-agnostic HullQ Account
→ durable HullQ OrganizationMembership + roles
→ server-side tenant authorization
→ protected Broker Workspace landing
```

The slice turns the already accepted authentication/account architecture into a real browser-visible professional access boundary without expanding into listing CRUD, media, leads or sales.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
Authentication adapter, durable actor identity, membership authorization, MFA gating and the minimal protected Broker Workspace page are vertical parts of one capability: authenticated professional workspace access.

**VISIBLE-RESULT CHECK:** PASS  
The retained PostgreSQL 18 → FastAPI → Astro proof must visibly demonstrate unauthenticated denial, stable first-login Account mapping, no-membership denial, authorized Organization workspace access, cross-Organization denial and privileged-role MFA enforcement.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
HullQ now has a trustworthy buyer Search/listing path through SLICE-0052, while the accepted second core product surface—the Broker Workspace—still lacks external authenticated self-service. Building the access/tenant boundary now unlocks later inventory and lead workflows without temporary operator-only identity shortcuts.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Current repository code contains SLICE-0041 runtime eligibility types/evaluator but no durable Account/AuthIdentity/Organization/Membership actor directory, no Auth0 integration, no broker session/MFA boundary and no broker Astro route. This slice implements accepted-but-unimplemented architecture rather than duplicating existing behavior.

**TRIGGER GATES CHECK:** PASS  
Architecture/current-state reconciliation is PASS; production readiness is NOT_TRIGGERED; this slice adds no technical native Search criterion; workflow reassessment is NOT_DUE; Broker Workspace Launch Gate remains NOT_READY and is not changed to PASS by this slice alone.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0052_REASSESSMENT_2026-09-14.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§10–11; `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`; `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/OPEN_QUESTIONS.md` OQ-014; accepted SLICE-0041 and SLICE-0052 records.  
**Production implementation checked:** `src/hullq/domain/publishing_eligibility.py`; current persistence/migrations; `src/hullq/api/app.py`; current `web/src/pages/` tree; current security helpers.  
**Already implemented / not re-decided:** Auth0 provider selection and authentication-only boundary; FastAPI sole application/domain API boundary; Astro web layer; runtime Account/Organization/Membership/role eligibility vocabulary; professional publisher domain evaluator; PostgreSQL/Alembic baseline; current NativeListing ownership IDs.  
**Exact remaining gap:** no durable external-identity→HullQ-Account mapping, no persisted actor directory/memberships, no authenticated provider adapter/session, no server-side tenant authorization surface and no protected broker workspace.  
**Accepted-but-unimplemented obligations:** OQ-014 authenticated account architecture; durable HullQ Account/Organization/Membership role truth; server-side tenant isolation; MFA for publishing-capable/Owner/Admin broker memberships; launch-gate section 1.  
**Material classifications:** access boundary = `DECIDED_NOT_YET_IMPLEMENTED`; SLICE-0041 eligibility vocabulary/evaluator = `DECIDED_AND_IMPLEMENTED`; listing editor/media/leads/sales/payments = `EXPLICITLY_DEFERRED`; broad/indexable SEO remains `GENUINELY_OPEN` but unrelated; `CONFLICT_OR_REGRESSION` = none.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** NOT_DUE

This slice uses synthetic/test professional identities and disposable/local PostgreSQL state for acceptance. It does not introduce real external broker production data, start a real broker pilot or activate public production launch.

## Broker Mandatory Capability Register check

The register was explicitly inspected before selection.

Current due state:

```text
no REQ-BROKER-022..029 item is DUE
REQ-BROKER-030 is IMPLEMENTED
sale/outcome remains PENDING
```

SLICE-0053 does not mark any mandatory-register item IMPLEMENTED merely by creating the access boundary.

In particular:

- REQ-BROKER-023 broker identity/branding remains PENDING until the actual broker/listing/media surfaces satisfy its evidence requirement;
- REQ-BROKER-024 connectivity-resilient draft recovery remains PENDING until the later listing workflow owns recoverable drafts;
- both remain mandatory before Broker Workspace Launch Gate PASS.

The selected access boundary is prerequisite infrastructure for those visible broker capabilities, but the slice remains product-visible through the protected workspace landing and is not foundation-only.

## Why this slice exists now

After SLICE-0052, the buyer side can discover and trust current inventory, but the provider side still has no external professional access path.

The accepted architecture already requires:

```text
Auth0 authentication-only
→ HullQ Account UUID
→ HullQ OrganizationMembership
→ HullQ roles/authorization in PostgreSQL
```

The current repository stops before that persistence/runtime boundary. Building broker listing forms first would require temporary identity/tenant shortcuts that would immediately conflict with the accepted architecture.

Compared with alternatives:

- lead persistence/attribution is valuable but needs a durable receiving Organization/account boundary;
- listing create/edit/resume is more directly operational but should not be built atop temporary operator identities;
- a second technical Search criterion broadens the already-visible buyer side while the provider side remains inaccessible;
- Saved Search/monitoring is important but lower current leverage than opening the professional supply-side product surface.

## Controlling contract

Primary contract:

```text
specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md
```

Existing product requirements especially owned by this slice:

```text
REQ-BROKER-001
REQ-BROKER-014
REQ-BROKER-015
```

This slice also advances—but does not by itself complete—the Broker Workspace Launch Gate §1 evidence.

## In scope

- Auth0 Public Cloud EU compatible browser authentication integration using the accepted authentication-only boundary.
- Provider-neutral validated authentication context in FastAPI/application code.
- Durable HullQ `Account` persistence.
- Durable `AuthIdentity` mapping from exact provider/issuer/subject to HullQ Account.
- JIT first-login Account/AuthIdentity creation with idempotent/concurrency-safe behavior and no email auto-linking.
- Durable marketplace Organization persistence compatible with existing `ProfessionalCategory` / `OrganizationPublishingEligibility` vocabulary.
- Durable OrganizationMembership persistence compatible with existing `MembershipState` / `MembershipRole` vocabulary.
- Multiple Organizations per Account, multiple Accounts per Organization, multiple roles per membership.
- Server-side FastAPI membership/tenant authorization.
- Explicit cross-Organization adversarial denial.
- MFA requirement for memberships containing PUBLISHER, OWNER or ADMIN roles using validated authentication-strength evidence.
- Minimal Astro `/broker` access surface and explicit Organization-scoped protected landing.
- Safe no-membership state.
- Local logout/session invalidation.
- Alembic migration(s) required for the bounded actor directory.
- Persistence/application/API/web tests.
- Retained real PostgreSQL 18 + FastAPI + built Astro vertical proof using a deterministic local OIDC/JWKS test issuer so CI needs no live Auth0 secret.
- Optional manually runnable real Auth0 EU development-tenant smoke path when credentials are supplied outside the repository.

## Explicitly out of scope

- Listing create/edit/publish/withdraw/reconfirm broker UI/API.
- Self-service Organization creation, invitations, membership administration or ownership transfer.
- External broker verification/adjudication workflow.
- Media.
- Broker identity/branding requirement completion on public listing/media surfaces.
- Connectivity-resilient listing drafts.
- Leads/contact requests, attribution, assignment, notes or CRM.
- Commercial/deal pipeline, sale/outcome, achieved sale price or Days-on-Market workflow.
- Search-fit diagnostics, Search exclusion reporting or demand analytics.
- Bulk import, inventory export/portability.
- Saved Search, alerts or price intelligence.
- Payment/subscription/entitlements.
- Broad/indexable SEO.
- Production deployment/HA/observability or real external broker pilot.
- Auth0 Organizations/roles/app_metadata as HullQ authorization truth.
- Auth0 Management API as a dependency for marketplace authorization.

## Required behavior

### A. Auth provider does not own HullQ authorization

Successful Auth0 authentication establishes provider identity evidence only.

No Auth0 role, Organization, app metadata, email or client-side value may grant HullQ Organization access.

### B. Stable HullQ Account mapping

A validated `(provider, issuer, subject)` maps to one immutable HullQ Account.

First authenticated use may create the Account + AuthIdentity atomically. Retry/concurrent first login converges on the same account. Email is never used to merge identities.

### C. Durable actor truth

Account, AuthIdentity, Organization, Membership and MembershipRole state is durable in PostgreSQL and read through persistence/application boundaries.

The migration must not invalidate existing historical/synthetic NativeListing account/Organization IDs by adding unsafe retroactive FKs.

### D. Current membership determines access

For each protected Organization request, authorization uses current HullQ membership state.

Missing/inactive membership denies access. Role/membership changes take effect on the next authoritative read; stale provider claims cannot preserve old tenant rights.

### E. Tenant isolation

Changing an Organization path/query/API identifier cannot grant access to another tenant. Unknown and unauthorized Organization access uses a non-enumerating failure shape.

### F. MFA for privileged memberships

Any ACTIVE selected membership containing `PUBLISHER`, `OWNER` or `ADMIN` requires validated MFA authentication evidence.

Without evidence, privileged workspace entry fails closed or triggers configured reauthentication/step-up. `MEMBER` alone does not manufacture a publishing capability.

### G. Browser/session safety

Auth callback/state/nonce/issuer/audience/signature/expiry validation must fail closed. Provider/session secrets and tokens are never exposed to ordinary browser JavaScript storage. Local logout invalidates the HullQ session.

### H. FastAPI remains semantic owner

Astro renders and owns browser navigation/session presentation but fetches current account/membership/Organization context through FastAPI. It never queries PostgreSQL directly and never reimplements tenant authorization.

### I. Visible workspace behavior

Minimum browser states:

```text
unauthenticated
→ no workspace data; login path

authenticated + zero active memberships
→ no Organization access state

authenticated + active membership
→ authorized Organization choice/context only

cross-Organization request
→ denied without tenant leakage

privileged membership without MFA
→ blocked/step-up

privileged membership with MFA
→ Organization workspace landing
```

### J. Deterministic proof

CI uses a local deterministic OIDC/JWKS issuer and real token validation, not a direct Account monkeypatch. The proof runs against PostgreSQL 18, FastAPI and built Astro.

## Expected persistence shape

Exact SQL names may follow repository conventions, but the migration must represent at least:

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

The implementation may choose equivalent normalized constraints if they preserve all contract semantics.

## Deliverables

- implementation of `specs/BROKER_WORKSPACE_ACCESS_CONTRACT.v0.1.md`;
- forward Alembic actor-directory migration(s);
- durable actor persistence/read models;
- AuthIdentity JIT mapping service;
- validated Auth0-compatible authentication adapter;
- server-side Organization authorization service;
- MFA authentication-strength normalization/enforcement for privileged memberships;
- minimum protected FastAPI broker-context endpoint(s);
- Astro broker login/session/callback/logout surface and protected Broker Workspace landing;
- adversarial tenant/MFA/token tests;
- `scripts/inspect_broker_workspace_access.py` or equivalently named retained real vertical proof;
- CI integration of the retained proof.

## Acceptance criteria

- [ ] Auth0 remains authentication-only; no Auth0 role/Organization/app metadata/email becomes HullQ authorization truth.
- [ ] Validated provider identity maps through durable AuthIdentity to immutable HullQ Account UUID.
- [ ] First-login JIT mapping is atomic, idempotent and concurrency-safe.
- [ ] Email never auto-links or merges HullQ Accounts.
- [ ] Durable Organization/Membership/roles support many-to-many account↔organization membership and multiple roles.
- [ ] Existing accepted NativeListing historical/synthetic actor IDs remain migration-compatible; no unsafe global FK backfill is introduced.
- [ ] Invalid/expired/wrong-issuer/wrong-audience/unsigned/malformed authentication evidence fails closed before broker data is returned.
- [ ] Auth flow validates state and OIDC nonce where applicable and keeps provider/session secrets out of browser JS storage.
- [ ] FastAPI is the sole tenant/role authorization owner; Astro has no direct PostgreSQL authorization path.
- [ ] Account with no ACTIVE membership gets no Organization workspace access.
- [ ] ACTIVE member can see/select only authorized Organization contexts.
- [ ] Cross-Organization URL/API manipulation is denied with non-enumerating behavior.
- [ ] Current membership/role changes affect subsequent authorization without changing Auth0 roles/metadata.
- [ ] PUBLISHER/OWNER/ADMIN membership requires validated MFA evidence; missing MFA cannot silently enter privileged workspace.
- [ ] Minimal `/broker` browser surface and an Organization-scoped landing are visible end to end.
- [ ] Local logout/session invalidation removes workspace access.
- [ ] Retained PostgreSQL18→FastAPI→Astro proof uses real token validation through deterministic local OIDC/JWKS fixtures and demonstrates all required visible states.
- [ ] CI does not require committed/live Auth0 credentials; optional real Auth0 EU development-tenant smoke remains secret/config driven.
- [ ] No listing CRUD, media, lead, sales, analytics, bulk import/export, Search expansion, payment or production-pilot capability is introduced.
- [ ] Mandatory Capability Register states remain unchanged unless separately proven; in particular REQ-BROKER-023/024 remain PENDING.
- [ ] `uv run python scripts/validate_repository.py`, Ruff, `mypy src`, full tests/coverage, web check/build/tests and PostgreSQL-18 CI pass on exact implementation head.
- [ ] Remote exact-head CI and independent review are clean before Project Owner acceptance.

## Stop conditions

Stop and return to readiness/Owner review rather than inventing semantics if implementation reveals that the capability would require any of these:

- using Auth0 roles/Organizations/app metadata as HullQ authorization truth;
- choosing a different authentication provider;
- weakening MFA policy for privileged broker memberships;
- adding self-service Organization/membership administration;
- adding broker listing mutation or lead/sales scope;
- changing public-supply broker-only policy;
- a production/live-broker trigger that would require Production Readiness Gate activation;
- migration/backfill that could invalidate accepted existing NativeListing actor IDs without a reviewed compatibility decision.
