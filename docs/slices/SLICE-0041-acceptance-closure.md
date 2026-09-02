# SLICE-0041 — Acceptance closure

**Slice:** SLICE-0041  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #130  
**Accepted implementation HEAD:** `66c16da44696fb2f11d83886be6de953362d5237`  
**Implementation merge commit:** `703fda23e7bd393c6d6117eda475284ab0eec0e6`  
**Owner acceptance:** explicitly recorded 2026-09-02

## Accepted scope

SLICE-0041 establishes the executable professional NativeListing publishing-eligibility boundary required by the accepted 2026-09-02 Architecture Rebaseline and Private Seller Policy.

The accepted decision evaluates one explicit principal relationship:

```text
AccountId
+ OrganizationMembership
+ candidate MarketplaceOrganization
→ ALLOWED
or DENIED(reason)
```

The public-supply rule remains fail-closed: a consumer/no-membership Account cannot obtain public NativeListing publishing eligibility, and a membership in one Organization cannot authorize another Organization principal.

## Accepted artifacts

- `specs/MARKETPLACE_PUBLISHING_ELIGIBILITY_CONTRACT.v0.1.md`
- `src/hullq/domain/publishing_eligibility.py`
- `tests/unit/test_publishing_eligibility.py`
- `scripts/inspect_publishing_eligibility.py`
- `docs/slices/SLICE-0041-professional-publishing-eligibility.md`

The implementation introduces runtime-distinct `AccountId`, `MarketplaceOrganizationId` and `OrganizationMembershipId` value objects plus the smallest immutable domain records/vocabularies needed for the decision.

## Accepted authorization semantics

Professional category is explicit:

```text
BROKER
DEALER
OTHER_PROFESSIONAL
```

Organization publishing eligibility is separate and fail-closed:

```text
ELIGIBLE
INELIGIBLE
UNVERIFIED
```

Only `ELIGIBLE` satisfies the Organization-side gate. This slice does not define how that adjudicated state is established in the real world.

Membership roles are composable:

```text
OWNER
ADMIN
PUBLISHER
MEMBER
```

Hard least-privilege rule:

```text
PUBLISHER must be explicitly present
```

Therefore `OWNER`, `ADMIN` or `MEMBER` alone do not imply publishing permission. `OWNER+PUBLISHER` and `ADMIN+PUBLISHER` may satisfy the role gate when every other condition also passes.

An `ALLOWED` decision means domain eligibility only. It does not claim that authentication, MFA, step-up security or actual NativeListing publication has occurred.

## Deterministic denial boundary

The accepted evaluator exposes a structured decision rather than a bare boolean and distinguishes:

```text
NO_MEMBERSHIP
ACCOUNT_MISMATCH
ORGANIZATION_MISMATCH
MEMBERSHIP_INACTIVE
PUBLISHER_ROLE_REQUIRED
ORGANIZATION_INELIGIBLE
ORGANIZATION_UNVERIFIED
```

The evaluator operates only on the explicit Account, candidate Organization and supplied membership. It does not search unrelated memberships for an authorization path and does not infer professional status from email, names, domains or Auth0 metadata.

## Exact-head review

Independent review was performed on exact implementation HEAD:

```text
66c16da44696fb2f11d83886be6de953362d5237
```

Final review verdict: **ACCEPT**.

No blocker, high or medium finding remained. Review verified:

- runtime-distinct actor identity kinds;
- explicit candidate Organization principal;
- consumer/no-membership fail-closed denial;
- explicit `PUBLISHER` role requirement;
- `OWNER` / `ADMIN` alone do not imply publishing permission;
- `UNVERIFIED` and `INELIGIBLE` Organizations are denied;
- account mismatch and cross-Organization membership fail closed;
- deterministic denial reasons are preserved;
- `ALLOWED` remains domain eligibility only;
- no NativeListing creation/persistence, Auth0, MFA, broker-verification, lifecycle, freshness, media, lead, referral or UI scope creep.

## Exact-head validation gates

On accepted HEAD `66c16da44696fb2f11d83886be6de953362d5237`:

- owner inspection: `ELIGIBILITY RESULT: PASS` across all 11 representative scenarios;
- full local suite: `3481 passed / 217 skipped`;
- project coverage: `91.94%` (new publishing-eligibility module 100%);
- ruff format/check: PASS;
- mypy: PASS;
- repository validation: PASS;
- CI run `33669506043`: SUCCESS;
  - quality / Ubuntu: SUCCESS;
  - quality / Windows: SUCCESS;
  - dependency audit: SUCCESS;
  - PostgreSQL 18 DB integration: SUCCESS;
- Manufacturer artifact reproducibility run `33669506015`: SUCCESS;
  - Ubuntu reproduction: SUCCESS;
  - Windows reproduction: SUCCESS.

The primary slice file intentionally retains the remote-CI acceptance checkbox as not locally verified because the workflow forbids creating an extra commit solely to record already-observed remote CI. This closure is the exact-head acceptance record.

## Merge verification

PR #130 was merged with expected-head protection against accepted implementation HEAD `66c16da44696fb2f11d83886be6de953362d5237`.

Canonical implementation merge commit:

```text
703fda23e7bd393c6d6117eda475284ab0eec0e6
```

## Retained scope boundaries

SLICE-0041 does **not** implement or authorize:

- NativeListing creation, mutation or persistence;
- PostgreSQL marketplace actor/listing schema or migrations;
- FastAPI endpoints or frontend UI;
- Auth0 / AuthIdentity mapping;
- MFA, passkeys, TOTP or step-up authentication;
- real-world professional Organization verification/KYB/KYC process;
- generic RBAC/custom-role administration;
- listing lifecycle or freshness;
- media ingestion;
- leads/contact routing;
- `BrokerageRequest` or seller-referral workflow;
- feed/API/CSV inventory intake;
- pricing/entitlements;
- co-brokerage;
- transaction, escrow or closing scope.

## Operational result

SLICE-0041 is owner-accepted and operationally complete under the HullQ slice workflow.

This closure does not create, authorize or start SLICE-0042. The next slice requires a separate readiness contract under the controlling Architecture Rebaseline, ONE-CAPABILITY and VISIBLE-RESULT rules.
