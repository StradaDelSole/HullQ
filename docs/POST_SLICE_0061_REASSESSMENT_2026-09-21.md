# HullQ — Post-SLICE-0061 Product / Repository Reassessment

**Date:** 2026-09-21  
**Status:** RECONCILED EXECUTION SELECTION  
**Canonical base inspected:** `96b84fc3950a6576f283a2304e1bb8afc95accf8`  
**Selected next slice:** SLICE-0062 — Professional Draft Connectivity Recovery

## 1. Reassessment result

Select **SLICE-0062 — Professional Draft Connectivity Recovery**.

SLICE-0061 closed the private professional draft-foundation gap:

```text
authenticated Account
→ current Organization/Membership/MFA authorization
→ current ACTIVE matching membership + PUBLISHER
→ Organization-owned ProfessionalListingDraft
→ create / list / reopen / read / update
→ optimistic versioning
→ private / not public
```

The highest-leverage clean continuation is now the launch-baseline requirement already locked as **REQ-BROKER-024**:

> ordinary connectivity interruption must not silently destroy recent broker draft work.

The accepted server draft is necessary but not sufficient for this requirement. Today, edits made in the browser after the last successful server save exist only in the form. A network failure during save/navigation can therefore destroy recent unsaved input.

0062 adds one bounded browser recovery layer over the existing 0061 server draft. It does not create a second source of truth, does not weaken optimistic concurrency, and does not create marketplace identities.

## 2. Decision / implementation reconciliation

### DECIDED_AND_IMPLEMENTED

Already decided and implemented; do not reopen:

- Auth0-compatible authentication is authentication-only;
- HullQ Account, Organization, Membership, roles and authorization remain PostgreSQL/domain truth;
- current Organization/Membership truth is re-read for Broker Workspace requests;
- privileged broker roles retain accepted MFA semantics;
- professional draft list/read/create/update requires the exact current matching ACTIVE membership with `PUBLISHER`;
- `ProfessionalListingDraftId != OwnerDirectListingDraftId != NativeListingId != PhysicalBoatId != MarketEpisodeId`;
- professional drafts are private Organization-owned pre-market state;
- creator Account is audit metadata only;
- partial server drafts are durably persisted in PostgreSQL;
- server updates use optimistic `expected_version` concurrency;
- stale server writes conflict and do not overwrite;
- draft browser/API surfaces are private/no-store/noindex;
- browser writes use the accepted same-origin + fixed non-simple-header CSRF boundary;
- private draft authoring does not require public Organization publishing eligibility;
- public NativeListing publishing eligibility remains a separate later marketplace gate;
- draft operations create no PhysicalBoat/MarketEpisode/NativeListing/offer/lifecycle/freshness/Search truth;
- owner-direct and professional drafts share the accepted common draft field semantics;
- FastAPI/domain/persistence remain authoritative; Astro/browser state is not domain truth;
- technical native Search criterion count remains exactly two;
- organic Search commercial independence remains mandatory.

### DECIDED_NOT_YET_IMPLEMENTED

Accepted requirements already require:

- REQ-BROKER-024 connectivity-resilient draft/recovery behavior;
- later professional draft-to-marketplace promotion;
- later professional publish/withdraw/reconfirm/edit workflows;
- REQ-BROKER-023 broker identity/branding baseline;
- media, leads, outcome, analytics and other launch/product commitments.

The selected 0062 subset is:

> while editing one existing authorized professional draft, preserve recent unsaved form input in a bounded browser-local recovery envelope scoped to the current HullQ Account + Organization + ProfessionalListingDraft + base server version, and recover it after ordinary connectivity interruption without silently overwriting newer server state.

### EXPLICITLY_DEFERRED

Remain outside SLICE-0062:

- creation of PhysicalBoat/MarketEpisode/NativeListing from a draft;
- professional draft promotion/publication;
- NativeListing edit/publish/withdraw/reconfirm controls;
- server background autosave;
- generalized offline-first operation;
- multi-device synchronization;
- collaborative merge/conflict resolution;
- media;
- broker branding/profile completion;
- duplicate/clone/relist;
- Search-fit diagnostics;
- inventory export/import;
- Organization/staff admin;
- leads/contact/CRM;
- sale outcomes;
- analytics/reporting;
- payments;
- owner-direct publication;
- buyer persistence/Saved Search;
- third Search criterion;
- production pilot/public launch.

### GENUINELY_OPEN

Remain open after 0062:

- exact later professional draft-to-marketplace promotion transaction;
- how promotion becomes lossless for fields not yet represented by current marketplace writers;
- later NativeListing edit/clone/relist semantics;
- whether a later richer offline/collaborative model supersedes this bounded local recovery mechanism;
- eventual human-readable Organization profile/branding model;
- buyer Free/Pro continuity semantics.

### CONFLICT_OR_REGRESSION

No blocking conflict exists on canonical main.

One current-state constraint materially affects sequencing:

- the 0061 draft contains `physical_boat.boat_name`, while the accepted current SLICE-0050 concrete-yacht claim writer does not yet persist that field;
- a real `NativeListingOfferSnapshot` requires `listing_offer.broker_description`, while the 0061 draft payload does not yet contain that required offer field.

Therefore selecting immediate draft-to-marketplace promotion would either drop accepted draft input, invent placeholder marketplace data, or combine promotion with additional field-contract/persistence expansion. None is appropriate as an implicit next step.

This is not a permanent blocker on promotion. It is the reason 0062 should close the already-mandatory, now-cleanly-implementable recovery capability first.

## 3. Existing implementation foundation

0061 already provides:

- authenticated private professional draft collection/edit pages;
- exact current Account/Organization authorization;
- `PUBLISHER` authoring-role gate;
- Organization ownership and cross-Organization isolation;
- server-side durable partial drafts;
- optimistic versions;
- explicit stale-write conflict;
- same-origin CSRF defense;
- bounded validation;
- private/no-store/noindex;
- deterministic retained PostgreSQL + FastAPI + built-Astro proof.

The 0061 edit form is therefore the correct surface to protect. 0062 must not create a separate draft model.

## 4. Selected v0.1 recovery architecture

### 4.1 Recovery scope

A local recovery envelope is valid only for the exact tuple:

```text
current HullQ AccountId
+ owner OrganizationId
+ ProfessionalListingDraftId
+ base server draft version
```

The implementation may use an opaque equivalent, but an envelope from a different Account, Organization or draft must never be auto-applied.

### 4.2 Storage role

Browser-local recovery is a **temporary unsaved-input buffer only**.

Hard:

```text
local recovery != server draft
local recovery != marketplace truth
local recovery != authorization
```

PostgreSQL/FastAPI remain authoritative for durable draft state, authorization and version conflict.

### 4.3 Stored content

The local envelope may contain only:

- the bounded professional draft form values already editable by 0061;
- `broker_listing_reference`;
- the base server draft version;
- recovery-scope identifiers/metadata;
- a client timestamp and schema/version marker needed for bounded expiry/compatibility.

It must never contain:

- HullQ session cookies;
- OIDC/Auth0 tokens;
- MFA material;
- CSRF secrets;
- database credentials;
- unrelated broker/account data.

### 4.4 Retention

Unsaved local recovery is short-lived.

v0.1 maximum age:

```text
24 hours
```

Expired or malformed recovery entries are ignored and removed.

A successful durable server save clears the matching local recovery envelope.

### 4.5 Capture

While an authorized draft edit page is active:

- meaningful input/change events update the local recovery envelope;
- debouncing is allowed;
- pending state must be flushed before explicit save/page-hide where browser APIs allow it;
- a storage failure/quota/privacy-mode failure must not break ordinary server-side draft editing.

If local recovery cannot be written, the page must not falsely claim recovery protection is active.

### 4.6 Restore with unchanged server version

When an authorized draft page loads and a valid non-expired matching recovery envelope has:

```text
recovery.base_version == current_server_version
```

the browser may restore those unsaved values into form controls and must visibly tell the broker that unsaved local changes were recovered.

Restore changes the form only. It performs no server mutation until the broker explicitly saves.

### 4.7 Newer server version / concurrency safety

When:

```text
recovery.base_version < current_server_version
```

the recovery copy is stale relative to server truth.

Hard:

- do not silently auto-apply it;
- do not silently submit it;
- show a clear recovery conflict state;
- allow an explicit user choice to discard the local copy or restore it into the form for review;
- even after explicit local restore, the next server save must use the **current** server version and remain subject to the accepted server validator/authorization/concurrency boundary.

0062 does not implement field-level merge.

A malformed/future-version envelope or an impossible `base_version > current_server_version` fails closed and is not auto-applied.

### 4.8 Save outcomes

- successful server save -> clear matching local recovery;
- server version conflict -> keep recovery available; never overwrite automatically;
- validation failure -> keep recovery available so the broker can correct input;
- transient network/service failure -> keep recovery available;
- authorization loss -> local data never grants access and must not bypass the now-failed server authorization.

### 4.9 Retry model

There is no infinite/background retry queue.

The existing explicit Save action remains the server synchronization action. After connectivity returns, the broker reviews/restores the local copy and explicitly saves.

This is connectivity resilience, not an offline-first synchronization platform.

## 5. Why 0062 is selected over other gaps

### A. REQ-BROKER-024 connectivity-resilient draft recovery — SELECTED

It is a hard launch/pilot baseline commitment and is now directly implementable because 0061 finally provides the server draft/edit surface and optimistic version boundary it requires.

It can be delivered without new marketplace identity, migration or public-state decisions.

### B. Professional draft-to-marketplace promotion

High future leverage, but not the cleanest next bounded step. Current draft and marketplace persistence are not yet losslessly aligned for all already-accepted draft input and required offer data. Promotion should be specified after that mismatch is reconciled rather than inventing placeholder or lossy mappings.

### C. REQ-BROKER-023 branding

Also mandatory before Launch Gate PASS, but recovery protects the broker's primary daily creation workflow and has the stronger immediate dependency fit after 0061.

### D. Lead/contact persistence

Launch-critical, but supply creation remains incomplete and currently has a concrete data-loss risk during ordinary network interruption.

### E. Owner-direct publication/admission

Still requires its separate trust/admission path and remains broader than this professional continuation.

### F. Buyer account continuity / Saved Search

Accepted future value, but does not close the current professional launch-baseline defect.

### G. Third Search criterion

Still lower leverage and subject to the accepted third-copy abstraction guard.

## 6. Product success checks

### Broker

A broker can type unsaved changes into an existing professional draft, suffer an ordinary connectivity interruption during save/navigation, return to the same authorized draft, and recover recent input without HullQ silently overwriting newer server work.

### Buyer

No buyer/public behavior changes. Recovery state never enters Search/public truth.

### Advantage

This directly supports the accepted broker-product principle that brokers should not lose work or need to re-enter information.

### Success evidence

Representative automated proof must simulate at least:

1. unsaved input captured locally at server version N;
2. network/save interruption so no durable server mutation occurs;
3. reload/reopen with server still at N -> local values recover visibly;
4. successful retry save -> server advances once and local recovery clears;
5. a different server writer advances to N+1 -> old local recovery is not auto-applied;
6. explicit stale-recovery restore remains a form-only action until an explicit save;
7. different Account/Organization/draft recovery never auto-applies;
8. expired/malformed recovery is discarded.

### Quality

Server-side auth, Organization isolation, PUBLISHER/MFA checks, CSRF, validation and optimistic concurrency remain unchanged and authoritative.

## 7. Broker Mandatory Capability Register check

Canonical register before 0062 remains:

```text
BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN
BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN
BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING

REQ_BROKER_022_STATUS: PENDING
REQ_BROKER_023_STATUS: PENDING
REQ_BROKER_024_STATUS: PENDING
REQ_BROKER_025_STATUS: PENDING
REQ_BROKER_026_STATUS: PENDING
REQ_BROKER_027_STATUS: PENDING
REQ_BROKER_028_STATUS: PENDING
REQ_BROKER_029_STATUS: PENDING
REQ_BROKER_030_STATUS: IMPLEMENTED
```

No trigger changed after 0061.

If 0062 is implemented, independently accepted, owner-accepted and canonically closed, its acceptance closure may advance:

```text
REQ_BROKER_024_STATUS: IMPLEMENTED
```

REQ-BROKER-023 remains PENDING and the Broker Workspace Launch Gate remains NOT_READY.

## 8. Trigger gates

Canonical state remains:

```text
POST_0051_ARCHITECTURE_RECONCILIATION: PASS
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT: 2
WORKFLOW_REASSESSMENT_DUE_AFTER_SLICE: 0056
WORKFLOW_REASSESSMENT_STATUS: PASS

PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED
EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT
EXTERNAL_OWNER_DIRECT_PRODUCTION_DATA_STATUS: NOT_PRESENT
PRODUCTION_PILOT_STATUS: NOT_STARTED
PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED

BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY
BROKER_SELF_SERVICE_PILOT_STATUS: NOT_STARTED
PAID_BROKER_PLAN_STATUS: NOT_STARTED
```

0062:

- adds no technical Search criterion;
- uses internal/synthetic test data only;
- introduces no external production data;
- starts no broker pilot;
- activates no paid plan;
- causes no public launch.

## 9. Decision

**Selected execution obligation:** `SLICE-0062 — Professional Draft Connectivity Recovery`.

Readiness proceeds on `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`.

Implementation may not start until the readiness package is independently exact-head reviewed, required remote gates are green and the readiness PR is merged to canonical `main`.
