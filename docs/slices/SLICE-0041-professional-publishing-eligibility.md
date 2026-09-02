# SLICE-0041 — Professional Publishing Eligibility

**ID:** SLICE-0041  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Native Marketplace Foundation — professional publishing authorization boundary  
**Depends on:** SLICE-0040 owner-accepted / DONE; 2026-09-02 Architecture Rebaseline accepted/merged; `docs/PRIVATE_SELLER_POLICY_2026-09-02.md` controlling for public/private supply  
**Blocks:** later NativeListing creation/persistence, broker inventory intake and server-side publishing authorization

## Objective

Deliver exactly one inspectable domain capability:

> **Given a HullQ Account, an explicit candidate publishing-principal Organization and the relevant OrganizationMembership, deterministically decide whether that Account is eligible to publish a public NativeListing on behalf of that Organization — with private/consumer-only accounts, wrong-organization memberships, inactive memberships, insufficient roles and non-eligible professional Organizations failing closed.**

This slice answers only **who may act as the professional publishing principal**. It does not create a listing, persist marketplace actors, integrate Auth0, verify a broker externally, enforce MFA, or expose an API/UI.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: deterministic professional NativeListing publishing-eligibility evaluation for an explicit Account + Organization principal.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one deterministic offline command and inspect allowed and denied publishing scenarios, including consumer-only denial and cross-Organization isolation.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted marketplace rebaseline requires the professional publishing-principal authorization boundary before public NativeListing creation. SLICE-0041 stops before persistence, actual listing creation, Auth0, MFA enforcement, feeds, lifecycle, freshness, media, leads, referrals or UI.

## Why this slice exists

The controlling marketplace rule is:

> Every publicly published `NativeListing` must have an eligible professional Organization as its publishing principal.

And:

> A private consumer account must not receive the capability to publish a public `NativeListing`.

This is a domain authorization rule, not a frontend-only restriction.

At the same time, HullQ must not encode a simplistic permanent `PRIVATE_ACCOUNT` versus `BROKER_ACCOUNT` identity split. The same human Account may use HullQ privately and may also legitimately act for one or more professional Organizations.

Therefore publishing eligibility is evaluated against an **explicit Organization principal and explicit OrganizationMembership**, conceptually:

```text
Account
  + OrganizationMembership
  + candidate professional Organization
        ↓
NativeListingPublishingEligibility
        ↓
ALLOWED or DENIED(reason)
```

No qualifying professional relationship means no public-listing publishing capability.

## Controlling artifacts

Apply the post-SLICE-0039 precedence where relevant:

1. `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
2. `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`;
3. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
4. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
5. `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`;
6. accepted SLICE-0040 contract `specs/MARKET_IDENTITY_CONTRACT.v0.1.md` where NativeListing identity terminology is relevant;
7. non-conflicting older artifacts.

Retain strict truth, fail-closed authorization, tenant isolation, ONE-CAPABILITY, VISIBLE-RESULT, slice isolation and exact-head review rules.

Existing `src/hullq/domain/identity.py` Brand/Organization objects represent canonical technical/industry identity semantics. Do not mutate or overload those semantics merely to implement marketplace Account/Organization authorization.

## Locked semantic boundary

### 1. Account identity

SLICE-0041 may introduce the smallest HullQ-owned `AccountId` runtime value needed to evaluate authorization.

It represents the HullQ Account identity, not an Auth0 subject, email address or login token.

This slice does not implement:

- `AuthIdentity` mapping;
- Auth0;
- email verification;
- login/session handling;
- account persistence.

Do not use email as an immutable identity key.

### 2. Marketplace Organization principal

Publishing eligibility is evaluated for one **explicit candidate Organization principal**.

The principal must be represented by a HullQ-owned marketplace Organization identity that remains distinct from Account identity and from SLICE-0040 market identities.

For this capability, professional category may be limited to the accepted public-supply classes:

```text
BROKER
DEALER
OTHER_ELIGIBLE_PROFESSIONAL
```

Do not infer category from an Organization name, email domain, website, string pattern or Auth0 metadata.

### 3. Professional Organization eligibility state

The slice must represent whether a candidate Organization has already been adjudicated as eligible for public professional supply.

Minimum fail-closed states:

```text
ELIGIBLE
INELIGIBLE
UNVERIFIED
```

Only `ELIGIBLE` may satisfy this slice's Organization-side gate.

`UNVERIFIED` is not equivalent to eligible.

This slice **does not define how professional verification is performed**. No company-registry lookup, license check, KYC/KYB workflow, manual-admin UI, third-party verification API or moderation process is authorized here.

The state is an explicit domain input to the decision, not something this slice discovers.

### 4. OrganizationMembership

A membership binds exactly:

```text
AccountId
→ MarketplaceOrganizationId
→ MembershipRole
→ MembershipState
```

Minimum membership state:

```text
ACTIVE
INACTIVE
```

Only `ACTIVE` memberships may authorize publishing.

Minimum role vocabulary for this boundary:

```text
OWNER
ADMIN
PUBLISHER
MEMBER
```

Publishing-capable roles are exactly:

```text
OWNER
ADMIN
PUBLISHER
```

`MEMBER` does not carry NativeListing publishing eligibility.

This role vocabulary is intentionally narrow. Do not build a generic RBAC framework, permission inheritance system or custom-role editor.

### 5. Private / consumer-only accounts

Do not create a global permanent `PRIVATE` account class merely to enforce the Phase-1 supply rule.

Instead:

> An Account with no qualifying active membership in the explicit eligible professional Organization principal is denied public NativeListing publishing eligibility.

This correctly handles both:

- a normal consumer-only user with no professional membership → denied;
- the same human using HullQ privately but also holding an authorized role in an eligible broker Organization → may be eligible **only when acting explicitly for that Organization**.

A private-sale intention remains a future/separate `BrokerageRequest` path and must not be converted into a NativeListing by this slice.

### 6. Explicit principal and tenant isolation

Authorization is always evaluated against the exact Organization principal requested for the action.

A membership in Organization A must never authorize publishing on behalf of Organization B.

Hard invariant:

```text
membership.organization_id
MUST equal
candidate_publishing_principal.id
```

Matching role names or identical raw ID text in different identity kinds do not bypass this rule.

The same Account MAY have valid memberships in multiple Organizations, but each principal is evaluated independently.

### 7. Decision result

Implement a deterministic result that exposes:

```text
ALLOWED
or
DENIED + explicit reason
```

The result must not be a bare boolean because fail-closed denial reason is part of the owner-visible trust boundary and later server-side auditability.

Minimum deterministic denial reasons should distinguish at least:

```text
NO_MEMBERSHIP
ACCOUNT_MISMATCH
ORGANIZATION_MISMATCH
MEMBERSHIP_INACTIVE
ROLE_NOT_PUBLISHING_CAPABLE
ORGANIZATION_INELIGIBLE
ORGANIZATION_UNVERIFIED
```

Equivalent concise naming is acceptable if these cases remain mechanically distinct.

Do not add ranking, trust scoring or probability.

## Required behavior A — runtime-distinct actor identities

Use the smallest immutable runtime-distinct identity values necessary for this capability, normally including:

```text
AccountId
MarketplaceOrganizationId
OrganizationMembershipId
```

They must not be interchangeable plain strings at runtime.

Wrong-kind IDs passed into relationship objects must fail closed at construction time.

Do not modify SLICE-0040's accepted identity classes merely to reuse a generic ID bag.

## Required behavior B — deterministic publishing decision

Provide one pure deterministic decision function/value boundary equivalent to:

```text
evaluate_native_listing_publishing_eligibility(
    account_id,
    candidate_organization,
    membership | None,
) -> PublishingEligibilityDecision
```

`ALLOWED` requires all of:

```text
membership exists
AND membership.account_id == account_id
AND membership.organization_id == candidate_organization.id
AND membership.state == ACTIVE
AND membership.role in {OWNER, ADMIN, PUBLISHER}
AND candidate_organization.professional_category is accepted
AND candidate_organization.publishing_eligibility == ELIGIBLE
```

Every other case is `DENIED` with a deterministic reason.

Do not silently search across unrelated memberships inside the decision merely to find one that permits the action. The candidate principal and membership under evaluation must remain explicit and auditable.

A small helper may evaluate a supplied collection only if it preserves exact principal matching and does not hide ambiguity; such a helper is not required.

## Required behavior C — consumer-only fail closed

A synthetic consumer Account with no OrganizationMembership must deterministically return denial.

This proves the Phase-1 rule in executable domain logic without creating a separate permanent consumer identity class.

No fallback may:

- create an unpublished NativeListing;
- create a public FSBO listing;
- auto-enroll the Account into a professional Organization;
- reinterpret a `BrokerageRequest` as a listing.

## Required behavior D — cross-Organization isolation

Focused adversarial behavior is mandatory:

```text
Account X is PUBLISHER in Organization A
candidate principal = Organization B
→ DENIED ORGANIZATION_MISMATCH
```

Also prove:

```text
Account X is OWNER/ADMIN/PUBLISHER in eligible Organization A
candidate principal = Organization A
→ ALLOWED
```

and:

```text
Account X membership object belongs to Account Y
→ DENIED ACCOUNT_MISMATCH
```

No Organization identifier may be taken from client-facing claims and trusted without domain comparison; actual transport/token handling remains out of scope.

## Required behavior E — verification and MFA remain separate

This slice evaluates **domain publishing eligibility**, not the complete runtime security ceremony for an eventual publish action.

The accepted architecture still requires MFA for publishing-capable broker accounts. SLICE-0041 must not weaken or supersede that rule.

However this slice must **not** implement:

- Auth0 MFA;
- Passkeys/WebAuthn;
- TOTP;
- step-up authentication;
- session age checks.

Later server-side publish execution will need both the accepted domain eligibility result and the applicable authentication/MFA security gate.

An `ALLOWED` result here therefore means:

> the Account is domain-eligible to act as publisher for this Organization principal,

not:

> a NativeListing has been created/published or every runtime security check has passed.

## Normative contract deliverable

Because this is a security-sensitive domain authorization boundary, implementation must add a compact normative contract:

```text
specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md
```

It must define only the locked semantics in this slice.

Do not expand it into:

- Auth0 integration;
- professional verification procedure;
- generic RBAC;
- listing persistence/lifecycle;
- MFA implementation;
- entitlements/pricing;
- BrokerageRequest/referral logic.

Contract, code and tests must agree atomically.

## Minimal owner-test surface

Provide one deterministic offline command, normally:

```text
uv run python scripts/inspect_publishing_eligibility.py
```

It must use synthetic/local domain objects only and visibly execute representative cases equivalent to:

```text
PROFESSIONAL PUBLISHING ELIGIBILITY

eligible broker OWNER                 -> ALLOWED
eligible dealer ADMIN                 -> ALLOWED
eligible professional PUBLISHER       -> ALLOWED
consumer with no membership           -> DENIED: NO_MEMBERSHIP
eligible org MEMBER role              -> DENIED: ROLE_NOT_PUBLISHING_CAPABLE
inactive broker PUBLISHER membership  -> DENIED: MEMBERSHIP_INACTIVE
unverified broker organization        -> DENIED: ORGANIZATION_UNVERIFIED
ineligible organization               -> DENIED: ORGANIZATION_INELIGIBLE
publisher in Org A acting for Org B   -> DENIED: ORGANIZATION_MISMATCH
membership for another Account        -> DENIED: ACCOUNT_MISMATCH

PRIVATE/CONSUMER FSBO PUBLISHING: DENIED
CROSS-ORGANIZATION ISOLATION: PASS
ELIGIBILITY RESULT: PASS
```

Exact labels may differ, but the cases and meanings must remain inspectable.

The script must execute the real evaluator and verify expected results. It may not print hard-coded PASS output without assertions/checks.

## Required tests

Focused tests must cover at least:

- AccountId, MarketplaceOrganizationId and OrganizationMembershipId reject empty identifiers;
- actor identity kinds remain runtime-distinct and wrong-kind constructor references fail closed;
- accepted professional categories are explicit and not inferred from names/strings;
- ELIGIBLE / INELIGIBLE / UNVERIFIED remain distinct;
- consumer Account with no membership is denied;
- active OWNER in an eligible professional Organization is allowed;
- active ADMIN in an eligible professional Organization is allowed;
- active PUBLISHER in an eligible professional Organization is allowed;
- active MEMBER is denied;
- inactive OWNER/ADMIN/PUBLISHER is denied;
- UNVERIFIED Organization is denied;
- INELIGIBLE Organization is denied;
- wrong Account on a membership is denied with ACCOUNT_MISMATCH-equivalent reason;
- membership for Organization A cannot authorize candidate Organization B;
- one Account may independently evaluate valid memberships for two different eligible Organizations without cross-tenant leakage;
- denial result exposes deterministic reason rather than only `False`;
- evaluation does not inspect Auth0 claims, email domain or Organization name to infer eligibility;
- no NativeListing creation/persistence or BrokerageRequest fallback exists;
- owner-test is deterministic and offline;
- existing SLICE-0040 market identity and prior identity/search tests remain green.

## In scope

- compact normative publishing-eligibility contract;
- smallest immutable Account/marketplace-Organization/membership domain primitives needed for the decision;
- explicit professional category and adjudicated eligibility state;
- narrow membership role/state vocabulary;
- deterministic `ALLOWED` / `DENIED(reason)` evaluator;
- cross-Organization fail-closed checks;
- deterministic offline owner-test;
- focused tests;
- only minimal package-export changes if existing conventions require them.

## Explicitly out of scope

- NativeListing creation or mutation;
- PostgreSQL schemas/migrations/repositories;
- FastAPI/API endpoints;
- Astro/React UI;
- Auth0 integration;
- AuthIdentity mapping;
- MFA/Passkeys/TOTP implementation;
- professional broker/dealer verification workflow;
- company registry / KYC / KYB integrations;
- admin verification UI;
- generic RBAC framework or custom roles;
- listing ownership persistence;
- listing lifecycle/freshness;
- media;
- leads/contact requests;
- `BrokerageRequest` / referral implementation;
- feed/API/CSV inventory intake;
- Saved Search/monitoring/alerts;
- pricing/entitlements;
- moderation workflows;
- co-brokerage;
- transaction/escrow/closing;
- SLICE-0042 or later work.

## Deliverables

Expected bounded deliverables:

1. `specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md`;
2. one small domain module, normally `src/hullq/domain/publishing_eligibility.py`;
3. focused tests, normally `tests/unit/test_publishing_eligibility.py`;
4. `scripts/inspect_publishing_eligibility.py`;
5. this primary slice document moved to `REVIEW` on successful handoff.

Do not create persistence/API/auth/frontend scaffolding as placeholders.

## Acceptance criteria

- [ ] Product execution checks remain `PASS` with no scope widening.
- [ ] Compact normative publishing-eligibility contract exists without adjacent feature semantics.
- [ ] AccountId, MarketplaceOrganizationId and OrganizationMembershipId are runtime-distinct identity kinds.
- [ ] Candidate publishing principal is explicit; authorization is never global/account-only.
- [ ] Professional category is explicit and limited to accepted public-supply categories.
- [ ] Organization publishing eligibility distinguishes ELIGIBLE / INELIGIBLE / UNVERIFIED and fails closed unless ELIGIBLE.
- [ ] OrganizationMembership binds exact Account, Organization, role and active/inactive state.
- [ ] Exactly OWNER / ADMIN / PUBLISHER roles are publishing-capable for this boundary; MEMBER is not.
- [ ] Consumer-only Account with no qualifying membership is denied.
- [ ] Wrong-account membership is denied.
- [ ] Cross-Organization membership cannot authorize another principal.
- [ ] Active publishing-capable membership in an eligible professional Organization is allowed for that explicit principal.
- [ ] Denial returns an explicit deterministic reason.
- [ ] No Auth0/email/name-string inference determines professional eligibility.
- [ ] `ALLOWED` is documented as domain eligibility only and does not claim MFA/authentication or actual publication has occurred.
- [ ] No NativeListing creation/persistence, broker verification, Auth0, MFA, lifecycle, freshness, media, lead, referral or UI work is started.
- [ ] Owner command exercises real domain code and visibly proves consumer denial and cross-Organization isolation.
- [ ] Owner command is deterministic/offline and requires no credentials/network.
- [ ] Repository validation, ruff, mypy and full test suite pass; project coverage remains >=90%.
- [ ] Exact-head CI and Manufacturer artifact reproducibility are green before review acceptance where applicable.
- [ ] No SLICE-0042 or later work starts automatically.

## Expected touch points

Expected implementation paths are limited to:

- `docs/slices/SLICE-0041-professional-publishing-eligibility.md`;
- `specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md`;
- `src/hullq/domain/publishing_eligibility.py`;
- `tests/unit/test_publishing_eligibility.py` and/or one narrowly justified contract test;
- `scripts/inspect_publishing_eligibility.py`;
- `src/hullq/domain/__init__.py` only if existing conventions require a minimal export.

If implementation requires modifying SLICE-0040 market identity semantics, existing Brand/Organization identity semantics, persistence, Search or authentication code, STOP and report the concrete blocker before widening scope.

## Validation

```text
uv run python scripts/inspect_publishing_eligibility.py
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
```

## Stop conditions

Stop and report rather than inventing policy when:

- a higher-precedence accepted artifact materially contradicts this authorization boundary;
- implementing the capability requires deciding how HullQ verifies a broker/dealer/professional in the real world;
- Auth0/MFA/session state becomes necessary merely to represent domain eligibility;
- a generic RBAC/entitlement framework appears necessary;
- actual NativeListing creation/persistence is required to demonstrate the decision;
- passing the slice would require treating UNVERIFIED as eligible;
- membership in one Organization would have to authorize another Organization;
- scope pressure pulls professional verification, persistence, lifecycle, Freshness, media, feeds, leads, referrals or UI into SLICE-0041.

## Status handoff rule

The implementation agent may recommend/set `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, explicit Project Owner acceptance and closure under `CLAUDE.md`.

A successful implementation handoff therefore normally leaves SLICE-0041 in `REVIEW`.

## Required completion report

Use the exact structure in `docs/slices/SLICE_TEMPLATE.md`. Include exact final branch HEAD, actual validation results, remote verification state and unresolved findings. Do not start the next slice.