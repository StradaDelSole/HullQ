# HullQ — Broker Workspace Access Contract v0.1

**Status:** READINESS CONTRACT for SLICE-0053 when merged  
**Owning slice:** SLICE-0053 — Authenticated Broker Workspace Access Boundary  
**Product requirements:** `REQ-BROKER-001`, `REQ-BROKER-014`, `REQ-BROKER-015`  
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

This contract establishes who the professional user is and which HullQ Organization contexts that user may access. It does **not** implement broker listing CRUD, media, leads, sales, analytics, onboarding invitations or payments.

## 2. Hard conceptual separation

These concepts remain distinct:

```text
Authentication = did the configured identity provider authenticate this subject?
Identity       = which immutable HullQ Account does that external identity map to?
Membership     = which HullQ Organization(s) is that Account a member of?
Authorization  = may that Account access this requested Organization context/action?
Verification   = what professional/organization claims have HullQ accepted?
```

No implementation may collapse these into one provider role/claim.

## 3. Auth0 boundary

The selected initial provider is:

```text
Auth0 Public Cloud
EU tenant
```

Auth0 is authentication-only.

Auth0 is authoritative only for provider authentication evidence required by the configured OIDC/OAuth flow. HullQ MUST NOT use Auth0 roles, Organizations, app metadata or email as authoritative HullQ marketplace authorization truth.

FastAPI/HullQ PostgreSQL remains authoritative for:

- HullQ Account identity;
- Organization identity;
- OrganizationMembership state;
- HullQ marketplace roles;
- publishing eligibility;
- tenant access;
- listing ownership/authorization when those actions exist;
- verification/moderation/entitlements when later implemented.

No Auth0 Management API dependency is required for SLICE-0053.

## 4. External identity mapping

HullQ owns an immutable Account identifier independent of Auth0.

The mapping is conceptually:

```text
(provider, issuer, subject)
→ AuthIdentity
→ HullQ AccountId
```

Requirements:

1. provider is explicit and currently only the accepted Auth0 provider is admitted;
2. issuer must equal the configured accepted Auth0 issuer after the implementation's exact canonical comparison rules;
3. subject must come from a successfully validated provider token/session, never from browser form/query input;
4. `(provider, issuer, subject)` is unique;
5. one AuthIdentity maps to exactly one HullQ Account;
6. email is never the immutable account key and MUST NOT auto-link two external identities;
7. a first successfully authenticated unknown identity may create exactly one new HullQ Account + AuthIdentity mapping, atomically and retry/concurrency safely;
8. future explicit account-linking/multiple-provider UX is out of scope, but persistence must not prohibit multiple AuthIdentity rows referencing one HullQ Account later.

The HullQ Account ID must be an immutable HullQ-generated UUID represented in the existing `AccountId` boundary. The exact UUID generation version is an implementation detail provided it is non-semantic, unique and immutable.

## 5. Durable marketplace actor directory

SLICE-0053 adds the minimum PostgreSQL actor directory needed for authenticated workspace authorization.

Required durable concepts:

```text
Account
AuthIdentity
MarketplaceOrganization
OrganizationMembership
OrganizationMembershipRole
```

The durable Organization and Membership records must be compatible with the existing SLICE-0041 domain vocabulary:

```text
ProfessionalCategory
OrganizationPublishingEligibility
MembershipState
MembershipRole
```

The persistence model MUST support:

- multiple OrganizationMemberships for one Account;
- multiple Accounts in one Organization;
- multiple roles on one membership;
- ACTIVE and INACTIVE membership states;
- Organization professional category and publishing-eligibility state;
- stable immutable IDs;
- database uniqueness/foreign-key constraints sufficient to prevent dangling membership/role rows and duplicate logical identity mappings.

No broker office hierarchy, invitation system, external verification workflow or co-brokerage relation is introduced.

### 5.1 Existing marketplace records

Existing `native_listings.created_by_account_id` and `native_listings.publishing_organization_id` predate the actor directory and contain historical/synthetic IDs in accepted tests/fixtures.

SLICE-0053 MUST NOT break accepted historical data or require an unsafe global backfill merely to add actor persistence. New actor-directory tables may therefore be introduced without retroactively adding fail-prone foreign keys to all existing marketplace rows in this slice.

Any future migration that makes old listing actor columns formally reference the actor directory requires its own evidence-backed compatibility/backfill plan.

## 6. Authentication protocol and token handling

The browser login path must use Auth0's supported server-side regular-web-application authorization flow. Exact maintained library choice is an implementation detail; security properties are not.

Required properties:

- authorization-code based login;
- state validation against login CSRF;
- OIDC nonce validation where an ID token is used;
- exact configured issuer validation;
- correct audience/client validation for the token type being consumed;
- signature verification against trusted provider keys;
- expiry/time validation;
- algorithm allowlisting / no `none` acceptance;
- secure key rotation/JWKS handling appropriate to the selected maintained library;
- Auth0 secrets and tokens are never committed to the repository;
- provider tokens MUST NOT be stored in browser `localStorage`/`sessionStorage` or exposed to ordinary client-side JavaScript;
- browser session cookies carrying authenticated session state must be `HttpOnly`, `Secure` in production and use an explicit SameSite policy;
- logout invalidates the HullQ browser session; provider-global logout behavior beyond the accepted local application logout is not required here.

FastAPI remains the sole application/domain authorization boundary. Astro may own browser redirects/session presentation but MUST NOT become the source of Organization membership/role truth.

## 7. FastAPI authentication adapter

Protected Broker Workspace API reads must receive authenticated provider context through the accepted server boundary and must validate it before domain authorization.

The validated authentication context exposed to application/domain code must be provider-neutral and contain only facts required by this capability, conceptually including:

```text
provider
issuer
subject
authenticated_at / auth_time where available
MFA evidence where required
```

Raw token claims MUST NOT be treated directly as HullQ Organization roles.

An invalid, expired, wrong-issuer, wrong-audience, unsigned, malformed or otherwise inadmissible token/session fails closed before Account/Organization data is returned.

## 8. JIT HullQ Account mapping

On the first admissible authentication of an external identity that has no mapping:

```text
validated AuthIdentity key absent
→ create HullQ Account
→ create AuthIdentity mapping
→ commit atomically
```

Concurrent/retried first logins for the same `(provider, issuer, subject)` must converge on one mapping and one Account, not create duplicates.

A newly created Account has **no Organization authorization merely because it authenticated**. Without an ACTIVE HullQ OrganizationMembership it receives no Organization workspace context.

## 9. Organization membership authorization

Authorization uses current durable HullQ membership state, not provider claims.

Given authenticated Account `A` and requested Organization `O`:

```text
ACTIVE membership A -> O
→ Organization context may be authorized subject to MFA requirement below

missing membership
OR INACTIVE membership
→ denied
```

A user with membership in Organization A MUST NOT access Organization B merely by changing a URL, path ID, API argument or client state.

Unknown Organization and unauthorized Organization access should use a non-enumerating failure shape for the browser/API surface so the response does not unnecessarily reveal whether another tenant exists.

The workspace may display the Organization's current professional category, publishing eligibility and the authenticated membership's roles. Display does not itself grant a publish action.

## 10. Privileged broker MFA

Accepted broker security remains controlling:

```text
MembershipRole.PUBLISHER
MembershipRole.OWNER
MembershipRole.ADMIN
→ MFA required
```

For SLICE-0053, any selected Organization context in which the authenticated membership has one or more of those roles MUST fail closed unless the validated authentication context proves that the current authentication satisfies the configured MFA requirement.

Auth0 remains the authenticator; HullQ interprets only validated authentication-strength evidence. The implementation may normalize provider-specific MFA evidence into the provider-neutral authentication context, but MUST NOT infer MFA from a HullQ role, query parameter, ordinary cookie flag or client-side state.

If MFA evidence is absent for a privileged membership, the browser flow must either initiate the configured Auth0 MFA/step-up path or deny privileged workspace entry with a deterministic reauthentication path. A silent fallback to non-MFA privileged access is forbidden.

No high-risk action-specific step-up matrix is required because SLICE-0053 contains no ownership transfer, staff-role mutation, credential creation, mass deletion or similar high-risk write action.

## 11. Protected Broker Workspace web surface

SLICE-0053 must create a minimal real Broker Workspace access surface in Astro.

Required behavior:

```text
unauthenticated /broker
→ login path; no broker data rendered

authenticated Account with zero active memberships
→ safe no-Organization-access state

authenticated Account with one or more active memberships
→ show only that Account's authorized Organization choices/context

selected authorized Organization
→ protected workspace landing showing stable Organization ID,
   professional category/publishing eligibility,
   current membership roles

selected unauthorized Organization
→ non-enumerating denial/not-found response
```

The exact route layout may be `/broker` plus an Organization-scoped route chosen during implementation, but it must preserve explicit Organization context rather than silently guessing tenant identity from a mutable browser value.

The surface is intentionally minimal. It is not yet the listing editor/dashboard promised by later Broker Workspace slices.

## 12. API boundary

The visible Astro workspace must obtain current account/membership/organization context through FastAPI/application services, not by direct PostgreSQL access and not by duplicating authorization logic in TypeScript.

FastAPI must expose the minimum authenticated read model necessary for the workspace, such as:

- current HullQ Account ID;
- authorized active Organization contexts;
- current roles for each membership;
- current Organization professional category / publishing eligibility;
- enough authentication-strength state to explain a required MFA step-up without exposing raw secrets/tokens.

No general public account API is introduced.

## 13. Failure / privacy behavior

The capability must fail closed and avoid account/tenant enumeration.

At minimum test:

- malformed token/session;
- expired token;
- wrong issuer;
- wrong audience;
- unknown external identity first-login race;
- no membership;
- inactive membership;
- cross-Organization access;
- role set changes between requests;
- privileged role without MFA;
- privileged role with valid MFA context;
- logout/session invalidation.

Do not log raw access tokens, refresh tokens, ID tokens, authorization codes, client secrets or session secrets. Test fixtures must use synthetic identities and secrets.

## 14. Deterministic testing and retained proof

Remote CI MUST NOT depend on live Auth0 credentials or a real external broker.

The accepted proof strategy is:

```text
local deterministic OIDC/JWKS test issuer
→ real browser-style authorization/session boundary
→ real FastAPI token validation/authentication adapter
→ real PostgreSQL 18 Account/AuthIdentity/Organization/Membership state
→ real FastAPI authorization
→ built Astro Broker Workspace rendering
```

The local issuer/fixture must exercise the same configured issuer/audience/signature/expiry/MFA normalization boundaries used by the Auth0 adapter; it may not bypass authentication by monkeypatching an authorized Account directly into the application layer.

The retained proof must demonstrate at least:

1. first external identity login creates one stable HullQ Account mapping;
2. retry/concurrent same-identity login does not create a second Account;
3. no-membership login cannot enter an Organization workspace;
4. active member sees only its Organization context;
5. cross-Organization access fails closed;
6. privileged membership without MFA is blocked/stepped-up;
7. privileged membership with valid MFA context reaches the protected Astro workspace;
8. changing HullQ membership/role state changes authorization on the next authoritative read without changing Auth0 roles;
9. logout/session invalidation removes workspace access.

A separately configured manual smoke test against a real Auth0 EU development tenant may be provided, but live provider secrets are not required for deterministic CI and must never be committed.

## 15. Explicit non-goals

SLICE-0053 MUST NOT implement:

- listing create/edit/publish/withdraw/reconfirm UI or APIs;
- broker onboarding invitations or self-service Organization creation;
- Organization ownership transfer/staff administration;
- media upload/storage;
- connectivity-resilient listing draft recovery;
- broker logos/watermarks capability completion;
- leads/contact requests;
- lead attribution, assignment or CRM workflow;
- commercial/deal pipeline or sale/outcome model;
- Search-fit diagnostics;
- Search exclusion/demand analytics;
- CSV/bulk inventory import;
- inventory export;
- Saved Search/alerts;
- payment/subscription/entitlement state;
- broad SEO/indexable surfaces;
- production rollout, real broker pilot or Production Readiness Gate activation.

## 16. Acceptance summary

SLICE-0053 is accepted only when the exact implementation head proves:

```text
Auth0-compatible validated authentication
!= HullQ identity
!= HullQ membership
!= HullQ authorization
```

and one real protected broker web path works end to end with durable HullQ-owned actor/tenant truth and adversarial cross-Organization/MFA tests.
