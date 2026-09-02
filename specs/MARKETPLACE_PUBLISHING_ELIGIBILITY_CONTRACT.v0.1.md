# HullQ Marketplace Publishing Eligibility Contract v0.1

**Status:** ACCEPTED
**Decision:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`, `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`, codified for implementation by SLICE-0041
**Supersedes:** none (new contract)
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This specification defines the domain decision boundary that answers exactly
one question:

> Given a HullQ Account, an explicit candidate professional Organization
> principal and the relevant OrganizationMembership, is that Account
> eligible to publish a public `NativeListing` on behalf of that
> Organization?

It defines the authorization decision only. It does not define how a
professional Organization is verified in the real world, Auth0/AuthIdentity
mapping, MFA/session/step-up authentication, `NativeListing`
creation/persistence, generic RBAC, entitlements/pricing, or
`BrokerageRequest`/referral semantics. Those remain governed separately.

## 2. Identity kinds

Each of the following is an independent, opaque, non-empty identity value.
Two identity values of different kinds MUST NOT be considered equal or
interchangeable even when their underlying raw text is identical.

### 2.1 AccountId

Identifies one HullQ Account. Represents HullQ Account identity only — not
an Auth0 subject, email address or login token. Email MUST NOT be used as an
identity key.

### 2.2 MarketplaceOrganizationId

Identifies one HullQ-owned marketplace Organization principal. Distinct from
Account identity and from SLICE-0040 market identity kinds
(`PhysicalBoatId`, `MarketEpisodeId`, `NativeListingId`,
`ExternalMarketObservationId`, `BoatDesignRef`).

### 2.3 OrganizationMembershipId

Identifies one `OrganizationMembership` record binding an Account to a
marketplace Organization.

## 3. Domain records

### 3.1 MarketplaceOrganization

- MUST have a `MarketplaceOrganizationId`.
- MUST have an explicit `professional_category`, one of:

  ```text
  BROKER
  DEALER
  OTHER_PROFESSIONAL
  ```

  The category MUST NOT be inferred from an Organization name, email
  domain, website or Auth0 metadata.

- MUST have an explicit `publishing_eligibility` state, one of:

  ```text
  ELIGIBLE
  INELIGIBLE
  UNVERIFIED
  ```

  Only `ELIGIBLE` satisfies the Organization-side gate. `UNVERIFIED` MUST
  NOT be treated as eligible. This contract does not define how the state
  is adjudicated (no registry lookup, license check, KYC/KYB workflow or
  moderation process); the state is an explicit input to the decision.

### 3.2 OrganizationMembership

Binds exactly:

```text
AccountId -> MarketplaceOrganizationId -> roles (set of MembershipRole) -> MembershipState
```

- MUST have an `OrganizationMembershipId`, `AccountId` and
  `MarketplaceOrganizationId`.
- MUST have an explicit `state`, one of:

  ```text
  ACTIVE
  INACTIVE
  ```

  Only `ACTIVE` memberships may authorize publishing.

- MUST have an explicit non-mutually-exclusive `roles` set drawn from:

  ```text
  OWNER
  ADMIN
  PUBLISHER
  MEMBER
  ```

  Roles MAY coexist on one membership (e.g. `OWNER` + `PUBLISHER`).
  `OWNER` and `ADMIN` MUST NOT imply `PUBLISHER`.

## 4. Decision

### 4.1 Result shape

The decision MUST expose `ALLOWED` or `DENIED` with an explicit reason. A
bare boolean is insufficient because the denial reason is part of the
owner-visible trust boundary and later server-side auditability.

Deterministic denial reasons, mechanically distinct:

```text
NO_MEMBERSHIP
ACCOUNT_MISMATCH
ORGANIZATION_MISMATCH
MEMBERSHIP_INACTIVE
PUBLISHER_ROLE_REQUIRED
ORGANIZATION_INELIGIBLE
ORGANIZATION_UNVERIFIED
```

No ranking, trust scoring or probability is defined.

### 4.2 Evaluation

`evaluate_native_listing_publishing_eligibility(account_id,
candidate_organization, membership)` is a pure, deterministic function.

`ALLOWED` requires all of:

```text
membership is not None
AND membership.account_id == account_id
AND membership.organization_id == candidate_organization.id
AND membership.state == ACTIVE
AND PUBLISHER in membership.roles
AND candidate_organization.professional_category is one of the accepted classes
AND candidate_organization.publishing_eligibility == ELIGIBLE
```

Every other case is `DENIED` with a deterministic reason distinguishing at
least the cases in §4.1.

### 4.3 Explicit principal, no ambiguity search

Authorization MUST always be evaluated against the exact
`MarketplaceOrganizationId` requested for the action
(`candidate_organization.id`). A membership in Organization A MUST NOT
authorize publishing on behalf of Organization B, regardless of matching
role names or identical raw ID text in different identity kinds.

The evaluator MUST NOT silently search across unrelated memberships to find
one that permits the action; the candidate principal and membership under
evaluation remain explicit.

## 5. Invariants

- Equal raw text across `AccountId`, `MarketplaceOrganizationId` and
  `OrganizationMembershipId` MUST NOT make the identities equal or
  interchangeable.
- A relationship field typed for one identity kind MUST reject a value of
  any other identity kind at construction time (fail closed), not only at
  static type-check time.
- A consumer Account with no `OrganizationMembership` MUST deterministically
  receive `DENIED(NO_MEMBERSHIP)`.
- An `OrganizationMembership` belonging to a different `AccountId` than the
  one being evaluated MUST deterministically receive
  `DENIED(ACCOUNT_MISMATCH)`.
- The same Account MAY hold independent, valid memberships in multiple
  Organizations; each candidate principal MUST be evaluated independently
  without cross-tenant leakage.
- `ALLOWED` documents domain eligibility only. It does not assert that MFA,
  authentication, or actual publication has occurred. Runtime security
  ceremony (Auth0 MFA, passkeys/WebAuthn, TOTP, step-up authentication,
  session age checks) remains governed separately and is not weakened or
  superseded by this contract.

## 6. Non-goals

This contract explicitly excludes, and no implementation under it may add:

- `NativeListing` creation, mutation or persistence;
- PostgreSQL schemas/migrations/repositories, FastAPI endpoints, Astro/React
  UI;
- Auth0 integration, `AuthIdentity` mapping, email verification, login/
  session handling, account persistence;
- MFA/Passkeys/WebAuthn/TOTP/step-up authentication implementation;
- professional broker/dealer verification workflow, company registry/KYC/
  KYB integration, admin verification UI, or any moderation process;
- generic RBAC framework or custom-role editor;
- listing lifecycle/freshness, media, leads/contact requests, referrals,
  `BrokerageRequest` implementation;
- feed/API/CSV inventory intake, Saved Search/monitoring/alerts, pricing/
  entitlements, co-brokerage, transaction/escrow/closing.
