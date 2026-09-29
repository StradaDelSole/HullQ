# SLICE-0070 — Acceptance Closure

**ID:** SLICE-0070  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #268  
**Accepted implementation HEAD:** `47932d250119e85f033b50a1a0c2814fc661102d`  
**Implementation merge commit:** `2d62ca0188e8d112ce1609af6fae9e1553c1c981`  
**Independent exact-head ACCEPT review:** 2026-09-29  
**Owner acceptance:** explicitly recorded 2026-09-29

## Accepted capability

SLICE-0070 closes the first durable buyer→broker contact step:

```text
currently public-eligible NativeListing
→ anonymous or authenticated buyer contact
→ authoritative D29 recheck
→ durable first-class Lead
→ listing / publishing-Organization / source attribution
→ explicit UNVERIFIED contact-email state
→ deterministic buyer-visible result
```

## Accepted implementation behavior

- buyer contact does not require a HullQ Account;
- bounded name, email and message are required;
- authenticated AccountId is optional attribution only;
- contact email is persisted explicitly as `UNVERIFIED`;
- login, delivery or broker action never imply verification;
- LeadId is server-minted and independent from listing/Organization/Account identity;
- submission-operation identity provides retry-safe idempotency;
- exact retry returns the original durable Lead even after later listing withdrawal/suppression;
- conflicting reuse of the same operation identity returns deterministic conflict;
- only genuinely new operations proceed to current D29 eligibility;
- NativeListing target and publishing Organization are resolved server-side;
- missing/DRAFT/WITHDRAWN/ACTIVE-suppressed targets remain non-enumerating `LISTING_NOT_AVAILABLE`;
- Lead creation is one PostgreSQL transaction;
- concurrent duplicate submissions create exactly one Lead;
- stale-current-public races serialize through the accepted NativeListing row-lock boundary;
- buyer-controlled strings are bounded and validated;
- raw IP/User-Agent and unrelated request metadata are not persisted as Lead truth;
- the public contact POST uses same-origin/non-simple-header CSRF protection and bounded body size;
- the public listing page exposes the contact form and deterministic success/error states;
- private/internal Lead readback exists for proof only; no public Lead lookup was introduced;
- Lead creation does not mutate lifecycle, freshness, offer, claim, media, current-public eligibility or Search truth;
- technical native Search criteria remain exactly 2.

## Independent review and amendment

Initial implementation HEAD `0f7e4b7826c9867754dd2e97fff1ee19b56fc1f5` implemented the full contact vertical, but independent review required two corrections:

1. retry resolution had to occur before current D29 re-evaluation so an already-created Lead remained retry-resolvable after later listing state changes;
2. the explicit transaction-rollback and non-mutation proof requirements had to be added.

Amendment HEAD `47932d250119e85f033b50a1a0c2814fc661102d` closed both findings.

Accepted added proofs include:

- create → withdraw → exact retry returns the same Lead;
- create → withdraw → changed envelope conflicts;
- new operation after withdraw remains unavailable;
- concurrent identical first submissions still create one row;
- deterministic real-PostgreSQL mid-transaction failure leaves zero partial Leads;
- before/after snapshots prove Lead creation leaves lifecycle/publication transitions/freshness/current offer/current claim/gallery/current-public eligibility unchanged.

No material implementation finding remains.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- D32 anonymous-capable durable buyer contact / Lead creation
- durable LeadId and retry-safe submission identity
- server-derived listing / publishing-Organization attribution
- optional AccountId attribution
- explicit UNVERIFIED contact-email state
- authoritative current D29 eligibility recheck
- bounded/non-enumerating public contact API
- public listing contact form
- real PostgreSQL duplicate/stale-public/rollback proofs
- Lead-creation non-mutation proof
- technical native Search criteria remain exactly 2

DECIDED_NOT_YET_IMPLEMENTED
- D33 Broker Workspace Lead operating surface
- durable Lead notification/outbox + email notification delivery
- buyer contact email verification evidence/token flow
- broker assignment/status/notes/timeline/follow-up
- post-promotion inventory editing
- D20/D21 MarketEpisode correction authority
- sale/outcome flow
- structured bulk onboarding/import
- analytics/performance reporting
- price-change alerts
- payments/entitlements

EXPLICITLY_DEFERRED
- phone/SMS verification
- CAPTCHA/provider selection
- Lead scoring/ranking
- cross-Organization Lead transfer
- production pilot/public launch in this slice

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

## Email-verification commitment

`BUYER_CONTACT_EMAIL_VERIFICATION_STATUS = PENDING` remains a hard governance commitment.

Before the first real external production buyer-contact flow is exposed/relied upon, or before HullQ represents/uses a buyer contact email as verified/trusted, explicit verification evidence/state transition must be implemented.

SLICE-0070 intentionally does not send email or implement verification tokens.

## D33 follow-up direction

Accepted D33 remains binding but unimplemented:

```text
durable Lead
→ authoritative Broker Workspace Lead inbox/detail/operations
+ durable notification/outbox intent
→ retryable HullQ email notification with dashboard deep-link
```

Email is auxiliary notification only. Broker Workspace remains the authoritative Lead system. Notification failure must never lose or roll back the Lead.

## Exact-head verification

Remote verification on accepted HEAD `47932d250119e85f033b50a1a0c2814fc661102d`:

```text
CI run 36583323164 → SUCCESS
Manufacturer artifact reproducibility run 36583323023 → SUCCESS
```

Independent exact-head implementation review: **ACCEPT**, review ID `5354175205`.

Implementation-agent final validation recorded:

```text
repository validator: PASS
ruff check / format-check: PASS
mypy: PASS (130 files)
PostgreSQL-backed Python suite: 5748 passed / 3 skipped / 0 failed
web tests: 326 passed
web build: PASS
retained FastAPI + built Astro + PostgreSQL Lead proof: PASS
```

PR #268 merged the exact accepted implementation to `main` as `2d62ca0188e8d112ce1609af6fae9e1553c1c981`.

## Trigger-gate state after acceptance

```text
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_STATUS: PASS
BUYER_CONTACT_EMAIL_VERIFICATION_STATUS: PENDING

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

0070 starts no real external buyer traffic, pilot, paid plan or public production launch.

## Broker launch execution checkpoint

```text
BROKER CREATES
→ BROKER ADDS MEDIA
→ BROKER PUBLISHES
→ BUYER CONTACTS      [implemented through SLICE-0070]
→ BROKER HANDLES LEAD [next directional step under D33]
→ BROKER EDITS / MAINTAINS INVENTORY
→ BROKER CLOSES / RECORDS OUTCOME
```

The next reassessment must evaluate the shortest safe implementation of the D33 Broker Lead operating surface plus notification direction. This closure does not itself preselect or authorize SLICE-0071.

## PROJECT_STATE freshness closure

```text
PROJECT_STATE_ACCEPTED_SLICE: 0070
PROJECT_STATE_QUEUE_SLICE:    0071
```

SLICE-0071 is **UNSELECTED** until fresh post-0070 reassessment completes.

## Closure decision

```text
SLICE-0070 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0070
PROJECT_STATE_QUEUE_SLICE = 0071
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
BUYER_CONTACT_EMAIL_VERIFICATION_STATUS = PENDING
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. `FINISH_SLICE.bat` may run only after this closure PR passes independent exact-head closure review, remote gates and guarded merge.
