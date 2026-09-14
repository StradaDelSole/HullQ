# HullQ — Broker Workspace Access Contract v0.1

**Status:** READINESS CONTRACT for SLICE-0053 when merged  
**Owning slice:** SLICE-0053 — Authenticated Broker Workspace Access Boundary  
**Direct requirements:** `REQ-BROKER-014`, `REQ-BROKER-015`  
**Broader product context:** `REQ-BROKER-001` remains a workstream-level requirement and is not completed by this slice alone  
**Architecture:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§10–11  
**Launch gate:** `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md` §1

## 1. Capability boundary

SLICE-0053 implements exactly one capability:

```text
external authenticated broker identity
→ stable HullQ Account identity
→ durable HullQ OrganizationMembership truth
→ server-side tenant/role authorization
→ protected Broker Workspace landing
```

This establishes who the professional user is and which HullQ Organization contexts that user may access. It does not implement listing CRUD, media, leads, sales, analytics, onboarding invitations or payments.

## 2. Hard conceptual separation

```text
Authentication = did the configured identity provider authenticate this subject?
Identity       = which immutable HullQ Account does that identity map to?
Membership     = which HullQ Organization(s) is that Account a member of?
Authorization  = may that Account access this Organization context/action?
Verification   = what professional/organization claims has HullQ accepted?
```

No provider role/claim may collapse these concepts.

## 3. Auth0 boundary

Selected provider:

```text
Auth0 Public Cloud
EU tenant
```

Auth0 is authentication-only. It is not authoritative for HullQ Organizations, membership, marketplace roles, publishing eligibility, listing ownership, verification, moderation or entitlements.

HullQ PostgreSQL/domain state is authoritative for those concepts. No Auth0 Management API dependency is required for SLICE-0053.

## 4. External identity mapping

HullQ owns an immutable Account UUID independent of Auth0:

```text
(provider, issuer, subject)
→ AuthIdentity
→ HullQ AccountId
```

Requirements:

1. provider is explicit and currently only the accepted Auth0 provider is admitted;
2. issuer must equal the configured accepted issuer;
3. subject comes only from successfully validated provider authentication evidence;
4. `(provider, issuer, subject)` is unique;
5. one AuthIdentity maps to exactly one HullQ Account;
6. email is never the immutable identity key and never auto-links identities;
7. first successful unknown identity login may atomically create one Account + AuthIdentity mapping;
8. retry/concurrent first-login attempts converge on one mapping/account;
9. persistence must permit multiple AuthIdentity rows to reference one Account later, although explicit account-linking UX is out of scope.

The Account ID is a HullQ-generated immutable UUID represented through the existing `AccountId` boundary. Exact UUID version is an implementation detail if it remains non-semantic and unique.

## 5. Durable marketplace actor directory

Minimum durable concepts:

```text
Account
AuthIdentity
MarketplaceOrganization
OrganizationMembership
OrganizationMembershipRole
```

Organization/Membership state must remain compatible with the existing SLICE-0041 vocabulary:

```text
ProfessionalCategory
OrganizationPublishingEligibility
MembershipState
MembershipRole
```

Persistence must support multiple Organizations per Account, multiple Accounts per Organization and multiple roles per membership, with stable IDs, ACTIVE/INACTIVE membership state and constraints preventing dangling or duplicate logical records.

No office hierarchy, invitation system, external verification workflow or co-brokerage relation is introduced.

### 5.1 Existing marketplace rows

Existing `native_listings.created_by_account_id` and `native_listings.publishing_organization_id` predate the actor directory and contain accepted historical/synthetic identifiers.

SLICE-0053 must not break accepted data by retroactively imposing unsafe foreign keys/backfills. New actor tables may therefore be introduced without forcing all existing marketplace rows to resolve into the new directory. A future FK/backfill change requires its own compatibility evidence.

## 6. Authentication protocol and token handling

The browser login path uses Auth0's supported server-side regular-web-application authorization-code flow. Exact maintained library choice is implementation detail; required security properties are not.

Required properties:

- authorization-code login;
- state validation;
- OIDC nonce validation where an ID token is consumed;
- exact issuer and correct audience/client validation;
- signature and expiry/time validation;
- algorithm allowlisting; never accept `none`;
- provider key/JWKS handling suitable for rotation;
- no committed Auth0 secrets/tokens;
- no provider token in browser `localStorage`/`sessionStorage` or ordinary client-side JavaScript;
- authenticated session cookies are `HttpOnly`, `Secure` in production and have explicit SameSite policy;
- local logout removes the HullQ browser session.

Astro may own browser redirect/session presentation. FastAPI remains the sole application/domain authorization boundary.

## 7. FastAPI authentication adapter

Protected broker API reads must validate provider authentication before any broker data is returned. Application/domain code consumes a provider-neutral authentication context, conceptually including:

```text
provider
issuer
subject
auth_time where available
validated MFA evidence where required
```

Raw provider roles/Organizations/app metadata are never HullQ authorization inputs.

Malformed, expired, wrong-issuer, wrong-audience, unsigned or otherwise inadmissible authentication fails closed.

## 8. JIT Account mapping

First admissible unknown external identity:

```text
validated AuthIdentity absent
→ create HullQ Account
→ create AuthIdentity mapping
→ atomic commit
```

A new Account gains no Organization access by authenticating. Without an ACTIVE HullQ OrganizationMembership, it has no Organization workspace context.

## 9. Organization authorization

Given authenticated Account `A` and requested Organization `O`:

```text
ACTIVE membership A → O
→ Organization context may be authorized subject to MFA below

missing membership OR INACTIVE membership
→ denied
```

Membership/role truth is read from current HullQ state. A stale provider/session claim cannot preserve revoked tenant rights.

Changing a URL, path ID, API argument or client state cannot grant cross-Organization access. Unknown and unauthorized Organization access use a non-enumerating failure shape.

The workspace may display Organization ID, professional category, publishing eligibility and current membership roles. Display is not a publish action.

## 10. Privileged broker MFA

Accepted security policy remains:

```text
PUBLISHER
OWNER
ADMIN
→ MFA required
```

Any selected Organization membership containing one or more of those roles fails closed unless validated authentication context proves the configured MFA requirement was satisfied.

MFA is provider authentication-strength evidence, not a HullQ role-derived boolean. It must not be inferred from query parameters, ordinary cookies or client-side state.

If MFA evidence is absent, the browser flow must trigger the configured Auth0 reauthentication/step-up path or deterministically deny privileged workspace entry. Silent non-MFA fallback is forbidden.

No action-specific high-risk step-up matrix is required because this slice has no staff-role mutation, ownership transfer, mass deletion or credential-management write action.

## 11. Protected Astro Broker Workspace

Minimum browser behavior:

```text
unauthenticated /broker
→ login path; no broker data rendered

authenticated Account with zero active memberships
→ safe no-Organization-access state

authenticated Account with active memberships
→ show only authorized Organization choices/context

selected authorized Organization
→ protected workspace landing showing Organization ID,
   professional category / publishing eligibility,
   membership roles

selected unauthorized Organization
→ non-enumerating denial/not-found response
```

The exact Organization-scoped route may be chosen during implementation, but Organization context must be explicit rather than inferred from mutable browser state.

## 12. FastAPI/Web boundary

Astro obtains account/membership/Organization context through FastAPI/application services. It must not query PostgreSQL directly or duplicate tenant authorization in TypeScript.

The minimum protected read model may include current Account ID, authorized active Organization contexts, current membership roles and Organization professional/publishing-eligibility state.

No general public account API is introduced.

## 13. Failure and privacy behavior

At minimum test:

- malformed/expired/wrong-issuer/wrong-audience authentication;
- first-login identity race;
- no membership;
- inactive membership;
- cross-Organization access;
- membership/role change between requests;
- privileged membership without MFA;
- privileged membership with validated MFA;
- logout/session invalidation.

Never log raw access tokens, refresh tokens, ID tokens, authorization codes, client secrets or session secrets. Tests use synthetic identities/secrets.

## 14. Deterministic retained proof

Remote CI must not depend on live Auth0 credentials or a real external broker.

Proof path:

```text
local deterministic OIDC/JWKS test issuer
→ real browser-style authorization/session boundary
→ real FastAPI token/authentication validation
→ real PostgreSQL 18 actor state
→ real FastAPI tenant authorization
→ built Astro Broker Workspace rendering
```

The local issuer must exercise the same issuer/audience/signature/expiry/MFA normalization boundary as the Auth0 adapter. It may not bypass authentication by monkeypatching an Account directly into application code.

The proof demonstrates:

1. first login creates one stable HullQ Account mapping;
2. retry/concurrent same-identity login creates no duplicate Account;
3. no-membership identity cannot enter an Organization workspace;
4. active member sees only authorized Organization context;
5. cross-Organization access fails closed;
6. privileged member without MFA is blocked/stepped-up;
7. same member with valid MFA reaches the protected Astro workspace;
8. HullQ membership/role changes alter the next authorization read without changing Auth0 roles;
9. logout/session invalidation removes workspace access.

A manually configured real Auth0 EU development-tenant smoke path may be included, but live secrets are not required for deterministic CI and must never be committed.

## 15. Expected persistence shape

Equivalent normalized names are acceptable if semantics remain identical:

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

## 16. Explicit non-goals

No listing create/edit/publish UI/API; no Organization self-service/invitations/staff admin; no media; no connectivity-resilient listing drafts; no broker-branding completion; no leads/attribution/CRM; no commercial/sale outcome; no Search-fit/exclusion/demand analytics; no bulk import; no inventory export; no Saved Search/alerts; no payments/entitlements; no broad SEO; no production rollout or real broker pilot.

## 17. Acceptance summary

The exact implementation head must prove:

```text
Auth0-compatible validated authentication
!= HullQ identity
!= HullQ membership
!= HullQ authorization
```

and one protected broker web path must work end to end with durable HullQ-owned actor/tenant truth, cross-Organization isolation and privileged-role MFA enforcement.
