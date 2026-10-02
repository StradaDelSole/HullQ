# SLICE-0077 — Broker Lead Assignment Discoverability Remediation

**Type:** IMPLEMENTATION  
**Status:** REVIEW  
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

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0076-acceptance-closure.md`; `docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md`; `docs/validation/BROKER_WORKSPACE_LAUNCH_GATE_EVIDENCE_2026-10.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/SECURITY_HARDENING_GATE.md`; `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`.  
**Production implementation checked:** `src/hullq/domain/broker_access.py`; `src/hullq/persistence/broker_identity.py`; `src/hullq/application/broker_workspace_read.py`; `src/hullq/application/lead_operations.py`; `src/hullq/persistence/lead_operations.py`; Lead detail Astro surface; broker Lead API/web tests; SLICE-0076 launch-readiness harness.  
**Already implemented / not re-decided:** Organization auth/MFA and exact membership truth; non-enumerating Organization boundary; Lead operational state; existing assignment mutation with current ACTIVE same-Organization membership validation; SLICE-0076 validation evidence.  
**Exact remaining gap:** no authorized read projection exposes current ACTIVE members of the requested Organization to the Lead detail browser surface, so assignment requires an undiscoverable opaque AccountId.  
**Accepted-but-unimplemented obligations:** discoverable Lead assignment remediation; focused Task-5 revalidation; later Broker Workspace Launch Gate reconsideration; MVP-PROD-012 Security Hardening remains separately DUE before pilot.  
**Material classifications:** DECIDED_AND_IMPLEMENTED foundations above; DECIDED_NOT_YET_IMPLEMENTED assignment candidate projection/picker/revalidation; EXPLICITLY_DEFERRED membership admin/profile identity/free-text Lead search/media reorder/catalog-assisted drafting/external pilot/paid-public launch/Search changes; GENUINELY_OPEN implementation-local projection shape and non-deceptive label using existing truth; CONFLICT_OR_REGRESSION none.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** NOT_READY  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Security Hardening & Adversarial Validation gate:** DUE / NOT_STARTED

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

- [x] active same-Organization members appear as assignment candidates;
- [x] inactive members do not appear;
- [x] foreign members do not appear;
- [x] unauthorized/unknown Organization access remains non-enumerating;
- [x] MFA boundary remains unchanged;
- [x] browser has no free-text opaque AccountId requirement for assignment;
- [x] candidate selection submits exact AccountId and assignment succeeds;
- [x] authoritative re-read renders the assigned AccountId;
- [x] membership deactivation between candidate read and mutation fails closed;
- [x] an existing inactive historical assignee is not silently rewritten;
- [x] focused Task 5 completes without operator/API/SQL assistance;
- [x] retained evidence explicitly closes or preserves the SLICE-0076 blocker;
- [x] no production application scope outside this remediation changes;
- [x] focused local validation + repository validation pass;
- [ ] exact pushed HEAD remote CI + Manufacturer artifact reproducibility pass (NOT VERIFIED locally; requires observing GitHub Actions on the exact pushed HEAD).

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

## Completion report (2026-10-02)

### Slice

- Slice ID: `SLICE-0077`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`
- Exact final branch HEAD SHA: `a437101999ea30ba7f61ad56269ed4f383d7ff10`

### Product execution checks

- ONE-CAPABILITY CHECK: `PASS`
- VISIBLE-RESULT CHECK: `PASS`
- PRODUCT EXECUTION PLAN ALIGNMENT: `PASS`
- REPOSITORY RECONCILIATION CHECK: `PASS`
- TRIGGER GATES CHECK: `PASS`
- OVERALL MVP CAPABILITY REGISTER CHECK: `PASS`

### Changes

- Changed files: `src/hullq/persistence/broker_identity.py` (new `fetch_active_members_for_organization`); `src/hullq/application/lead_operations.py` (new `get_lead_assignment_candidates`, `LeadAssignmentCandidate(s)Result`); `src/hullq/api/app.py` (new `GET /api/broker/organizations/{organization_id}/leads/assignment-candidates`); `web/src/lib/brokerLeadOpsApi.ts` (new `fetchLeadAssignmentCandidates`); Lead detail Astro page (free-text `assignee_account_id` input replaced by a `<select>` picker, empty-candidate state handled explicitly); `scripts/validate_broker_workspace_launch_readiness.py` (Task 5 rewritten to discover a candidate from the rendered picker, plus fail-closed/historical-assignee race proof; untimed setup seeds a second ACTIVE member, an INACTIVE member and a foreign-Organization member); `tests/persistence/test_broker_identity_persistence.py`; `tests/persistence/test_broker_lead_operations_api.py`; new `docs/validation/BROKER_WORKSPACE_LEAD_ASSIGNMENT_REMEDIATION_EVIDENCE_2026-10.md`.
- Acceptance work completed: all 14 non-remote acceptance criteria above checked off, each backed by a focused test or the real-stack harness run (candidate tenancy/state/auth/MFA filtering; picker replaces free-text input; mutation/version-conflict/fail-closed/historical-preservation semantics unchanged; retained evidence states the SLICE-0076 blocker CLOSED).
- Tests/fixtures added or updated: 3 new persistence tests (`TestActiveMembersForOrganization`: active-only filtering, zero-members empty list, deactivation removes from next read); 6 new API tests (unauthenticated candidate read, foreign/unknown-org non-enumeration, MFA boundary, inactive/foreign exclusion, mutation-time fail-closed race, historical-assignee-not-rewritten); existing SLICE-0053/0071 tests in the same files unaffected.

### Validation

- Local validation: `PASS`
- Commands/results: `ruff check .` / `ruff format --check .` clean; `mypy src` clean; `scripts/validate_repository.py` PASS; focused pytest (`test_broker_identity_persistence.py` + `test_broker_lead_operations_api.py`, via `claude_diag.py run-local-test-db-compact`) 47 passed; web `astro check` 0 errors/warnings/hints across 108 files; real-stack `validate_broker_workspace_launch_readiness.py` (real PostgreSQL + local OIDC/JWKS + FastAPI + built Astro) — all of TASK_1–TASK_6 and OBSERVATION_7 PASS, explicit `SLICE-0076 TASK_5 blocking deficiency -> CLOSED`.

### External verification

- Remote CI: `NOT VERIFIED`
- Other external gates: `NOT VERIFIED` — Broker Workspace Launch Gate reconsideration requires independent exact-head review and explicit Project Owner acceptance; not performed by this slice.

### Findings

- Unresolved findings: none.
- Spec/ADR ambiguities: none.
- Scope deviations: none — SLICE-0076's other (non-blocking) findings (media reorder, Lead free-text search, draft-form catalog reuse) were not touched.

### Follow-up

- Recommended next action: independent exact-head review of `a437101999ea30ba7f61ad56269ed4f383d7ff10`; if accepted, Project Owner reconsideration of `BROKER_WORKSPACE_LAUNCH_GATE_STATUS` via a governance-document update (out of scope for this slice). `MVP-PROD-012` Security Hardening & Adversarial Validation remains separately `DUE` before any external broker self-service pilot, regardless of this gate's eventual status.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.
