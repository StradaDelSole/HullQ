# SLICE-0077 — Broker Lead Assignment Discoverability Remediation

**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Broker Workspace Launch Gate remediation  
**Depends on:** SLICE-0076 owner-accepted / DONE  
**Normative contract:** `specs/BROKER_LEAD_ASSIGNMENT_DISCOVERABILITY_CONTRACT.v0.1.md`

## Capability

Deliver one coherent remediation:

```text
authorized Organization ACTIVE-member candidates
→ visible Lead assignee picker
→ existing authoritative assignment mutation
→ focused Task-5 revalidation
```

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One blocker from accepted SLICE-0076 evidence is removed and revalidated.

**VISIBLE-RESULT CHECK:** PASS  
A broker can assign a Lead from a visible selectable candidate list without knowing an opaque AccountId.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is the accepted REMEDIATION_REQUIRED blocker preventing Broker Workspace Launch Gate PASS.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Existing Account/Organization/Membership truth and Lead assignment mutation are reused; no second identity or membership model is created.

**TRIGGER GATES CHECK:** PASS  
No external pilot, public launch, paid activation or Search criterion is introduced.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
SLICE-0076 delivered MVP-BROKER-013 evidence but found this launch blocker. MVP-PROD-012 Security Hardening remains independently DUE before pilot. Closing the known product blocker first yields the coherent surface required for the later holistic hardening pass.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED:** Organization auth/MFA, current membership truth, Lead assignment mutation with active-member validation, SLICE-0076 validation evidence.  
**DECIDED_NOT_YET_IMPLEMENTED:** assignment-candidate read projection, picker UI, focused Task-5 revalidation, possible later Launch Gate PASS transition; Security Hardening remains separate.  
**EXPLICITLY_DEFERRED:** membership admin/profile identity, free-text Lead search, media reorder, catalog-assisted drafting, external pilot, paid/public launch, Search changes.  
**GENUINELY_OPEN:** implementation-local projection shape and non-deceptive label using existing truth.  
**CONFLICT_OR_REGRESSION:** none.

## Required implementation

1. add a bounded persistence read for current ACTIVE memberships of one exact Organization;
2. add an authorized application/API read projection for Lead assignment candidates, reusing Broker Workspace auth/MFA/non-enumeration;
3. expose candidates to the Lead detail browser surface;
4. replace free-text assignee AccountId entry with a select/picker;
5. preserve current assignment/unassign/version-conflict behavior;
6. preserve mutation-time current ACTIVE-member validation;
7. preserve historical assigned AccountId if the member later becomes inactive;
8. extend focused tests and the accepted 0076 real-stack harness to prove the blocker is closed.

## Mandatory constraints

- no email-as-identity;
- no fabricated personal/member display data;
- no Auth0 role/Organization claim authorization;
- no client-authoritative membership;
- no foreign/inactive candidates;
- no membership-administration API/UI;
- no cross-Organization enumeration;
- no production pilot;
- no unrelated UX remediation.

## Required validation

Focused tests must cover candidate projection tenancy/state/auth/MFA and assignment races.

Retained real PostgreSQL + local OIDC/JWKS + FastAPI + built Astro proof must demonstrate the corrected broker Task 5 through visible surfaces only.

The validation harness must fail if assignment again requires manual/opaque identifier knowledge.

## Acceptance criteria

- [ ] active same-Organization members appear as assignment candidates;
- [ ] inactive members do not appear;
- [ ] foreign members do not appear;
- [ ] unauthorized/unknown Organization access remains non-enumerating;
- [ ] MFA boundary remains unchanged;
- [ ] browser has no free-text opaque AccountId requirement for assignment;
- [ ] candidate selection submits exact AccountId and assignment succeeds;
- [ ] authoritative re-read renders the assigned AccountId;
- [ ] membership deactivation between candidate read and mutation fails closed;
- [ ] an existing inactive historical assignee is not silently rewritten;
- [ ] focused Task 5 completes without operator/API/SQL assistance;
- [ ] retained evidence explicitly closes or preserves the SLICE-0076 blocker;
- [ ] no production application scope outside this remediation changes;
- [ ] focused local validation + repository validation pass;
- [ ] exact pushed HEAD remote CI + Manufacturer artifact reproducibility pass.

## Expected touch points

- `src/hullq/persistence/broker_identity.py`
- bounded broker application/API read projection
- `web/src/pages/broker/organizations/[organization_id]/leads/[lead_id].astro`
- corresponding API/web/persistence tests
- `scripts/validate_broker_workspace_launch_readiness.py`
- focused validation evidence / slice status

## Stop conditions

Stop and report instead of broadening scope if:

- a human-readable member label requires creating a new Account profile/email identity model;
- assignment requires membership administration rather than read-only projection;
- remediation reveals a new cross-tenant/auth/security defect;
- a new product/domain decision is required;
- unrelated 0076 findings would need implementation.

## Status handoff

Agent may recommend `REVIEW` or `BLOCKED`; must not mark DONE or start another slice.

Initial implementation prompt comes only from `START_SLICE.bat` after readiness review/gates/merge.
