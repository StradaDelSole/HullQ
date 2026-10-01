# Broker Lead Assignment Discoverability Contract v0.1

**Status:** ACCEPTED FOR SLICE-0077 READINESS  
**Scope:** remove the accepted SLICE-0076 Lead-assignment blocking deficiency without creating membership administration or a second identity model.

## 1. Objective

A representative authorized broker must be able to assign a Lead to a current ACTIVE member of the exact Organization using only ordinary Broker Workspace surfaces.

The browser must never require the broker to know or manually type an otherwise undiscoverable internal AccountId.

## 2. Existing truth reused

Authoritative truth remains:

```text
AccountId
+
MarketplaceOrganizationId
+
OrganizationMembership(state, roles)
```

The existing assignment mutation remains authoritative and must continue to re-check current Organization membership at write time.

The picker/projection is convenience/read state only. Seeing a candidate must never bypass mutation-time authorization/membership validation.

## 3. Assignment candidate projection

For an authenticated Account authorized to the exact Organization Lead workspace, expose a bounded list of current ACTIVE Organization memberships suitable for Lead assignment.

Each candidate must contain at least:

- exact `account_id`;
- current membership roles if useful for disambiguation/presentation.

Do not fabricate:

- email;
- personal name;
- Auth0 profile name;
- Organization role from provider claims.

If no accepted human-readable member identity exists, render a deterministic non-deceptive label based on available HullQ truth, while the submitted value remains the exact AccountId.

Inactive memberships must not be offered as new assignment candidates.

Foreign-Organization memberships must never appear.

## 4. Authorization and enumeration boundary

Candidate reads must reuse the accepted Broker Workspace Organization authorization/MFA boundary.

For unauthorized/unknown Organization access, preserve the existing non-enumerating external behavior.

No public/member-directory endpoint is introduced.

The candidate list is private, no-store and reachable only through the authenticated Organization workspace path.

## 5. Browser behavior

Replace the current free-text `Assign to Account ID` control with a selectable broker-visible candidate control.

Required behavior:

- current ACTIVE members appear as choices;
- the current broker can select a visible candidate without knowing an AccountId in advance;
- submit sends the selected exact AccountId;
- successful assignment is authoritatively re-read and rendered;
- stale version behavior remains unchanged;
- member becoming inactive between read and submit fails closed through the existing mutation semantics;
- existing Unassign remains available;
- empty/no-candidate state is explicit and non-crashing.

No client-side hidden mapping may become authorization truth.

## 6. Historical/current assigned state

If a Lead is already assigned to an AccountId that is no longer ACTIVE, the historical/current operational state must remain truthful.

The UI must not silently rewrite or drop that stored assigned AccountId merely because it is not in the new candidate list.

New reassignment may target only a currently eligible candidate. Unassign remains permitted according to existing rules.

## 7. Focused launch revalidation

Extend/reuse the accepted SLICE-0076 validation harness.

The corrected Task 5 must prove through browser-visible surfaces only:

1. open Lead detail;
2. discover at least one valid assignment candidate from rendered UI;
3. assign without direct SQL, direct FastAPI, devtools or operator assistance;
4. authoritative re-read shows the selected AccountId assigned;
5. status/follow-up/note/contact-attempt workflow still succeeds;
6. re-find the Lead through the accepted bounded inbox filter;
7. inactive candidate is not offered and/or mutation fails closed if membership changes before submit;
8. foreign Organization member is never offered.

The focused evidence must explicitly state whether the accepted SLICE-0076 blocking deficiency is CLOSED or remains OPEN.

## 8. Launch Gate consequence

SLICE-0077 may recommend reconsideration of:

```text
BROKER_WORKSPACE_LAUNCH_GATE_STATUS
```

only if the blocking deficiency is mechanically closed and no new launch-blocking deficiency is found.

Any transition to PASS still requires:

- exact-head independent review;
- explicit Project Owner acceptance;
- closure/governance update.

Even a later Broker Workspace Launch Gate PASS does **not** authorize an external broker pilot. The separate Security Hardening & Adversarial Validation gate remains mandatory before pilot activation.

## 9. Required retained proof

At minimum prove:

- exact Organization A active members projected;
- Organization B/foreign members absent;
- inactive member absent;
- unauthorized/unknown Organization candidate read remains non-enumerating;
- MFA requirement preserved;
- assignment candidate selection completes through Astro/browser path;
- assignment mutation persists and re-read confirms;
- stale/inactivated candidate cannot be assigned;
- current historical inactive assignee is not silently rewritten;
- no email/provider profile identity is invented or used as authorization;
- Task 5 focused validation passes end-to-end after remediation.

## 10. Non-goals

- Organization membership CRUD/admin UI;
- invitations;
- staff directory;
- new member display-name/email profile model;
- Auth0 organization/role authorization;
- Lead inbox free-text search;
- media reorder UX;
- draft catalog/typeahead;
- Security Hardening execution;
- external pilot;
- payments;
- Search changes.
