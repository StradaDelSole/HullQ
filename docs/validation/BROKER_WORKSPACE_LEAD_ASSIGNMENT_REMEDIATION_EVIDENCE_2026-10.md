# Broker Lead Assignment Discoverability Remediation Evidence — 2026-10

**Slice:** SLICE-0077 — Broker Lead Assignment Discoverability Remediation
**Normative contract:** `specs/BROKER_LEAD_ASSIGNMENT_DISCOVERABILITY_CONTRACT.v0.1.md`
**Normative protocol (revalidation methodology):**
`specs/BROKER_WORKSPACE_LAUNCH_VALIDATION_PROTOCOL.v0.1.md`
**Prior blocking evidence:** `docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md`
(Task 5), `docs/validation/BROKER_WORKSPACE_LAUNCH_GATE_EVIDENCE_2026-10.md` (Finding 1)
**Candidate commit under test:** `2c30664` on `slice/0077-broker-lead-assignment-discoverability`
**Run date:** 2026-10-02

This document does not itself change `BROKER_WORKSPACE_LAUNCH_GATE_STATUS`. Per the slice's
status handoff rule and contract §8, it records evidence only; any transition remains subject
to independent exact-head review and explicit Project Owner acceptance.

## 1. What changed

1. `src/hullq/persistence/broker_identity.py`: added
   `fetch_active_members_for_organization` — a bounded (hard `LIMIT`, see the Amendment note
   at the end of this document), tenant-scoped, state-filtered read of current ACTIVE
   memberships for one exact Organization (not account-scoped, unlike the pre-existing
   `fetch_active_memberships_for_account`).
2. `src/hullq/application/lead_operations.py`: added `get_lead_assignment_candidates`,
   reusing the exact same `get_organization_workspace_result` auth/MFA boundary every other
   Lead operation already uses. Each candidate carries `account_id`, current `roles`, and a
   deterministic non-deceptive `label` derived only from those two facts (contract §3 — no
   fabricated email/personal-name/provider-profile identity).
3. `src/hullq/api/app.py`: added
   `GET /api/broker/organizations/{organization_id}/leads/assignment-candidates`, inheriting
   the existing `/api/broker/*` private/no-store/noindex response-header policy automatically.
4. `web/src/lib/brokerLeadOpsApi.ts` + the Lead detail Astro page: the free-text
   "Assign to Account ID" input is replaced with a `<select>` populated from the new
   candidate projection; empty-candidate state renders an explicit non-crashing message
   instead of an unusable control. The existing POST handler, mutation call, version-conflict
   handling, and authoritative re-read are unchanged.

The existing assignment mutation (`set_assignment` /
`hullq.persistence.lead_operations.set_lead_assignment`) was not modified: it already
re-derives current membership fresh at mutation time and already rejects a non-ACTIVE/foreign
assignee. The picker is convenience/read state only, per contract §2.

## 2. Focused test evidence

`tests/persistence/test_broker_identity_persistence.py` (`TestActiveMembersForOrganization`):
only-ACTIVE-same-Organization-members returned (ACTIVE/INACTIVE/foreign-Organization all seeded
together); zero-members returns `[]` not an error; deactivation removes a member from the next
read.

`tests/persistence/test_broker_lead_operations_api.py` (new SLICE-0077 section): unauthenticated
candidate read rejected (401); unknown/foreign Organization share the identical non-enumerating
404 shape; MFA boundary preserved for a privileged role (403 `mfa_required`); candidates exclude
INACTIVE and foreign members while correctly surfacing roles/label; a membership deactivated
between the candidate read and the assignment POST still fails closed (422
`assignee_not_active_member`); a historical assignee that later goes INACTIVE is not rewritten
on re-read and is absent from the next candidate list.

Result: `47 passed` (both files; existing SLICE-0053/0071 tests in the same files unaffected).

```text
uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/run_pytest_local.py \
  tests/persistence/test_broker_identity_persistence.py tests/persistence/test_broker_lead_operations_api.py -q
```

Also verified clean: `ruff check .`, `ruff format --check .`, `mypy src`,
`scripts/validate_repository.py`, and the web package's `astro check` (0 errors/warnings/hints
across 108 files).

## 3. Revalidation harness (Task 5) — real PostgreSQL + real HTTP

`scripts/validate_broker_workspace_launch_readiness.py` Task 5 was rewritten to discover a
candidate from the rendered `<select name="assignee_account_id">` picker rather than assuming
or already knowing an AccountId, and extended to exercise the fail-closed/historical-assignee
proofs contract §7 requires. Untimed setup now also seeds a second current-ACTIVE
same-Organization member, an INACTIVE same-Organization member, and an ACTIVE member of a
separate Organization, so the picker's tenancy/state filtering is actually exercised rather than
only ever offering the signed-in broker.

Reproduce:

```text
uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/validate_broker_workspace_launch_readiness.py
```

(requires the web package built first: `npm ci --prefix web && npm run build --prefix web`.)

**Retained interaction path (exact, from the retained run):**

```text
POST .../leads/<id> (action=mark_read)                                    -> 200 "Done."; now Read
GET  .../leads/<id>                                                        -> 200 (rendered picker)
  discovered 2 assignment candidate(s) from the rendered <select>
  present: signed-in broker's own AccountId, second ACTIVE member's AccountId
  absent:  INACTIVE same-Organization member, ACTIVE foreign-Organization member
POST .../leads/<id> (action=assign, assignee_account_id=<discovered candidate>)
                                                                             -> 200 "Done."; Assigned: <id>
POST .../leads/<id> (action=assign, assignee_account_id=<second candidate>) -> 200 "Done."; Assigned: <2nd>
  [out-of-band: second candidate's membership deactivated -- simulates a concurrent admin
   action, not the timed broker-participant using a DB shortcut to complete their own task]
GET  .../leads/<id>                                                        -> 200
  "Assigned: <2nd>" still rendered (historical assignee not silently rewritten)
  <2nd> absent from the candidate picker (no longer offered for a *new* assignment)
POST .../leads/<id> (action=assign, assignee_account_id=<2nd>, stale resubmission)
                                                                             -> 200
  rendered: "That Account is not a current active member of this Organization."
  "Assigned: <2nd>" unchanged (rejected mutation did not alter stored state)
POST .../leads/<id> (action=assign, assignee_account_id=<own AccountId>)    -> 200 "Done."
POST .../leads/<id> (action=set_status, IN_PROGRESS)                       -> 200 "Done."
POST .../leads/<id> (action=set_follow_up, overdue due_at)                 -> 200 "Done."
POST .../leads/<id> (action=add_note)                                     -> 200 "Done."; visible
POST .../leads/<id> (action=add_contact_attempt, PHONE)                   -> 200 "Done."; visible
GET  .../leads?follow_up_due=true                                          -> 200 (Lead re-found)
```

**Outcome: TASK_5 = PASS** (duration 4.22s this run; every sub-step completed through
browser-visible surfaces only — no direct FastAPI call, no direct SQL used by the
participant, no operator/admin shortcut).

**Full harness result this run:**

```text
TASK_1  PASS
TASK_2  PASS
TASK_3  PASS
TASK_4  PASS
TASK_5  PASS   (was BLOCKING_DEFICIENCY under SLICE-0076)
TASK_6  PASS
OBS_7   PASS (untimed)

SLICE-0076 TASK_5 blocking deficiency -> CLOSED
HARNESS RESULT -> PASS
```

## 4. Contract §9 required retained proof — checklist

- exact Organization A active members projected: **yes** (own + second member, both offered).
- Organization B/foreign members absent: **yes** (foreign-Organization member never offered;
  also covered by a dedicated API test).
- inactive member absent: **yes** (seeded INACTIVE member never offered; also covered by a
  dedicated API test).
- unauthorized/unknown Organization candidate read remains non-enumerating: **yes** (API test:
  unknown and foreign Organization both 404 with an identical body).
- MFA requirement preserved: **yes** (API test: privileged role + unsatisfied MFA -> 403
  `mfa_required` on the candidate endpoint, same boundary as every other Lead route).
- assignment candidate selection completes through Astro/browser path: **yes** (harness Task 5).
- assignment mutation persists and re-read confirms: **yes** (harness Task 5; unchanged
  mutation/re-read discipline).
- stale/inactivated candidate cannot be assigned: **yes** (harness Task 5 + dedicated API test,
  both via the real mutation-time membership re-check, not a new check).
- current historical inactive assignee is not silently rewritten: **yes** (harness Task 5 +
  dedicated API test).
- no email/provider profile identity is invented or used as authorization: **yes** (candidate
  `label` is composed only from `account_id` + roles; no email/display-name field exists or is
  read from any provider claim).
- Task 5 focused validation passes end-to-end after remediation: **yes**.

## 5. Disposition

The SLICE-0076 Lead-handling `BLOCKING_DEFICIENCY` (Finding 1 in
`BROKER_WORKSPACE_LAUNCH_GATE_EVIDENCE_2026-10.md`) is **CLOSED** by this remediation, evidenced
by the focused tests in §2 and the real-stack browser-driven revalidation in §3. No new
cross-tenant/auth/security defect was found during remediation. No unrelated SLICE-0076 finding
(media reorder, Lead free-text search, draft-form catalog reuse) was touched, per this slice's
stop conditions.

This evidence supports reconsideration of `BROKER_WORKSPACE_LAUNCH_GATE_STATUS`, but does not
itself change it (contract §8): that requires independent exact-head review, explicit Project
Owner acceptance, and a governance-document update. `MVP-PROD-012` Security Hardening &
Adversarial Validation remains separately `DUE` and is unaffected by this remediation; it
remains mandatory before any real external broker self-service pilot regardless of this gate's
eventual status.

## Amendment note (2026-10-02) — Finding A: the projection was tenant/state-filtered but not bounded

Independent review of the first candidate head (`2c30664`) found that
`fetch_active_members_for_organization` correctly filtered by exact Organization and
`ACTIVE` state, but had no `LIMIT`/hard cap, so the contract §3 requirement to "expose a
**bounded** list" was not actually satisfied — an Organization with an unusually large
membership roster could receive an unbounded read.

**Fix:** added `MAX_LEAD_ASSIGNMENT_CANDIDATES = 100` (a conservative ceiling for a
broker-office assignee picker, chosen to comfortably exceed any realistic office roster while
still giving the read a hard, deterministic worst case) and a `LIMIT %s` clause, ordered
deterministically by `account_id`. The function keeps an optional `limit` keyword (clamped to
the module constant, mirroring `hullq.persistence.lead_operations.fetch_lead_timeline`'s
identical pattern) so tests can exercise truncation without seeding a hundred real rows; no
pagination/cursor was introduced — contract §10 excludes a staff directory, and nothing in
this remediation needs more than one bounded read.

New focused tests (`tests/persistence/test_broker_identity_persistence.py`,
`TestLeadAssignmentCandidateBound`): fewer-than-bound members all appear; more-than-bound
members return exactly the bound in deterministic, repeatable `account_id` order; a `limit`
override above the hard ceiling is clamped down, never bypassed; INACTIVE/foreign-Organization
noise rows never consume the bound. Re-ran: focused persistence/API tests (51 passed, up from
47), `ruff check .` / `ruff format --check .` / `mypy src` (clean), `scripts/validate_repository.py`
(PASS), and the real-stack `validate_broker_workspace_launch_readiness.py` harness (all tasks
PASS, `SLICE-0076 TASK_5 blocking deficiency -> CLOSED` unchanged). No mutation, auth/MFA,
non-enumeration, version-conflict or historical-assignee-preservation behavior was touched.
