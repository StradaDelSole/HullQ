# HullQ Professional Listing Draft Recovery Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0062 — Professional Draft Connectivity Recovery  
**Controlling product direction:** `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`  
**Broker requirements:** `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`  
**Draft foundation:** `specs/PROFESSIONAL_LISTING_WORKSPACE_CONTRACT.v0.1.md`  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This contract defines exactly one capability:

> protect recent unsaved browser input for an existing authorized professional listing draft against ordinary connectivity interruption, without turning browser storage into server truth or weakening optimistic concurrency.

It implements the bounded v0.1 form of REQ-BROKER-024.

It does not define generalized offline-first behavior, background synchronization, cross-device continuity, publication, marketplace promotion or NativeListing edit.

## 2. Fundamental truth boundary

```text
browser recovery buffer
!= ProfessionalListingDraft durable truth
!= marketplace truth
!= authorization
```

The durable authoritative draft remains the PostgreSQL-backed 0061 `ProfessionalListingDraft`.

FastAPI/domain/persistence remain authoritative for:

- current Account/Organization/Membership/role/MFA authorization;
- draft ownership and visibility;
- field validation;
- optimistic versioning;
- durable mutation.

A local recovery buffer can repopulate form controls only. It cannot authorize, persist or publish anything by itself.

## 3. Scope

v0.1 applies only to the existing protected professional draft edit surface:

```text
/broker/organizations/{organization_id}/drafts/{draft_id}
```

A durable server draft MUST already exist.

v0.1 does not create an offline draft before server draft creation and does not add recovery to owner-direct drafts.

## 4. Recovery identity / namespace

Every locally stored recovery envelope MUST be scoped to the exact current:

```text
AccountId
MarketplaceOrganizationId
ProfessionalListingDraftId
```

and MUST carry the server draft version on which the unsaved edits were based.

The storage key or envelope may use an opaque representation, but:

- a different Account MUST NOT auto-load the recovery;
- a different Organization MUST NOT auto-load the recovery;
- a different draft MUST NOT auto-load the recovery.

The current AccountId MAY be obtained through the already-accepted private Broker Context API. It is recovery scoping metadata only and MUST NOT be treated as authorization evidence.

## 5. Recovery envelope

The browser-local envelope MUST be schema/versioned and bounded.

Conceptually:

```text
recovery_schema = "professional-listing-draft-recovery-v1"
account_id
organization_id
draft_id
base_version
captured_at
form_values
```

`form_values` MUST be limited to the currently accepted professional-draft form vocabulary: the original 0061 fields plus the later SLICE-0064 professional-only offer-input extension.

- `broker_listing_reference`;
- `physical_boat.marketed_brand_claim`;
- `physical_boat.model_designation_claim`;
- `physical_boat.build_year`;
- `physical_boat.boat_name`;
- `listing_offer.asking_price_mode`;
- `listing_offer.asking_price_amount`;
- `listing_offer.currency`;
- `listing_offer.location_country`;
- `listing_offer.location_region`;
- `listing_offer.broker_description` (SLICE-0064 professional-only offer input).

The SLICE-0064 description field is professional-only and does not amend OwnerDirectListingDraft. Browser storage is allowed to preserve form-string representation before server normalization/validation because it is only a recovery buffer. On real Save, the existing Astro/FastAPI path remains authoritative.

The envelope MUST NOT contain session cookies, OIDC/Auth0 tokens, MFA material, credential material, database secrets or unrelated workspace data.

## 6. Storage and retention

v0.1 uses bounded same-origin browser storage appropriate to recovery across page reload/navigation interruption.

The recovery lifetime is:

```text
24 hours maximum from captured_at
```

A matching entry older than 24 hours MUST NOT be restored and SHOULD be removed immediately when encountered.

Malformed JSON, unknown schema versions, invalid identifiers, non-integer/non-positive `base_version`, invalid timestamps or otherwise malformed envelopes MUST fail closed: no restore and removal where possible.

A browser storage API failure, quota error, disabled storage mode or security exception MUST NOT break the ordinary server-backed draft workflow.

If recovery cannot be maintained, the UI MUST NOT falsely tell the user that local recovery is active.

## 7. Capture behavior

Once an authorized edit page has rendered:

- meaningful form input/change MUST update the local recovery envelope;
- implementation MAY debounce writes for efficiency;
- explicit form submit MUST ensure the latest form state has been captured before navigation;
- page-hide/unload SHOULD flush pending recovery where the platform allows it without blocking navigation;
- local capture MUST NOT call FastAPI or mutate server state.

No hidden background server autosave is introduced by this contract.

## 8. Restore decision

Let:

```text
R = valid matching local recovery envelope
S = current authorized server draft
```

### 8.1 No recovery

If no valid non-expired matching `R` exists, render normal server state.

### 8.2 Same base version

If:

```text
R.base_version == S.version
```

then the browser MAY automatically restore `R.form_values` into the form.

When it does, it MUST visibly state that unsaved local changes were recovered.

This is form restoration only. Server state remains unchanged until explicit Save.

### 8.3 Server advanced

If:

```text
R.base_version < S.version
```

then:

- MUST NOT automatically apply the local values;
- MUST NOT automatically submit them;
- MUST visibly report that a newer server draft exists;
- MUST offer an explicit way to discard the local recovery;
- MAY offer an explicit "restore local copy for review" action.

If the user explicitly restores the stale local copy into the form, the form remains unsaved. Any later Save MUST use the page's current server version and therefore remains subject to the existing server-side validation/authorization/concurrency contract.

No field-level merge algorithm is authorized.

### 8.4 Impossible/future base version

If:

```text
R.base_version > S.version
```

the envelope MUST be treated as invalid/corrupt for v0.1 and MUST NOT auto-restore.

## 9. Save / failure behavior

### Successful save

After the existing server save succeeds and the authoritative draft is re-read at the resulting version, the matching local recovery envelope MUST be cleared.

### Version conflict

If FastAPI returns the accepted stale-version conflict:

- local recovery MUST remain available;
- server truth MUST remain displayed/authoritative;
- no automatic overwrite is allowed.

### Validation failure

If server validation fails, local recovery SHOULD remain available so the user can correct the form.

### Network/service failure

If the save attempt fails because the request/response path is unavailable, local recovery MUST remain available.

### Authorization failure/revocation

A local recovery envelope never preserves authorization.

If the current server request is no longer authorized, local content MUST NOT bypass or substitute for the failed authorization boundary.

## 10. Retry / synchronization model

0062 intentionally has no persistent retry queue and no infinite automatic retry.

The accepted synchronization model is:

```text
local unsaved capture
→ connectivity interruption
→ authorized page becomes available again
→ bounded restore decision against current server version
→ explicit user Save
→ existing FastAPI validation + optimistic concurrency
```

The existing Save action remains the only server mutation in scope.

## 11. Security / privacy

Recovery code MUST:

- use form-control values, never `innerHTML` or executable string injection, when restoring text;
- never store the HttpOnly session cookie or auth material;
- never grant access from local storage content;
- remain scoped to HullQ's same-origin private broker surface;
- preserve `Cache-Control: private, no-store` and `X-Robots-Tag: noindex`;
- fail safely if browser storage is unavailable;
- not introduce permissive credentialed CORS.

The local recovery buffer is client-side convenience state and MUST NOT be logged to analytics/telemetry by this slice.

## 12. UI behavior

The edit page MUST provide an understandable recovery state.

At minimum, the user can distinguish:

```text
normal server-backed draft
local recovery available/active
unsaved local changes recovered
newer server version exists; local copy not auto-applied
local recovery unavailable
```

The UI MUST NOT claim that locally recovered input is saved to HullQ until a real server save succeeds.

## 13. Existing boundaries preserved

0062 MUST NOT change:

- ProfessionalListingDraft ownership;
- PUBLISHER/MFA/current-membership authorization;
- draft payload validation rules;
- draft optimistic version semantics;
- CSRF mechanism;
- public NativeListing publishing eligibility;
- NativeListing lifecycle;
- owner-direct behavior;
- Search semantics;
- marketplace identity/truth.

No database migration is expected or authorized for the recovery buffer itself.

## 14. Tests

At minimum cover:

### Scope/isolation

- same Account + Organization + draft finds its entry;
- different Account does not auto-load it;
- different Organization does not auto-load it;
- different draft does not auto-load it.

### Envelope validation

- valid schema/version;
- malformed JSON;
- unknown recovery schema;
- invalid/missing base version;
- invalid timestamp;
- expired >24h entry removed/not restored;
- browser storage read/write/remove exceptions do not break server workflow.

### Capture

- field change snapshots all bounded editable values;
- latest values replace older local snapshot;
- explicit submit flushes latest state before navigation;
- no auth/session material is present.

### Recovery decision

- same server version -> recoverable/auto-restored form state + visible notice;
- newer server version -> no auto-restore;
- explicit stale-copy restore is form-only;
- discard removes local recovery;
- local base version greater than server -> fail closed.

### Save outcomes

- successful server save clears matching local recovery;
- version conflict retains local recovery;
- validation failure retains local recovery;
- simulated network/service failure retains local recovery.

### Server non-regression

Existing 0061 authorization, CSRF, tenant-isolation, validation, optimistic-concurrency and non-promotion tests/proofs remain green.

## 15. Representative connectivity-loss proof

The accepted proof for this slice MUST include a deterministic simulated connectivity interruption.

At minimum:

1. load an authorized professional draft at server version N;
2. change multiple form fields without a successful server save;
3. prove the bounded local recovery envelope contains those changes at base version N;
4. simulate the save/network path failing so PostgreSQL remains at N;
5. reopen/reconstruct the edit state with server still at N;
6. prove the unsaved values are restored and visibly identified as local recovered changes;
7. retry the ordinary save successfully;
8. prove PostgreSQL advances exactly once and the local recovery entry is cleared;
9. separately advance server state to N+1 before recovery;
10. prove the stale local N copy is not automatically applied or submitted.

A focused deterministic browser-state/unit harness is acceptable for the client storage/network interruption portion if the retained real PostgreSQL/FastAPI/built-Astro proof also verifies the actual protected edit page wiring and server non-regression. The verification report MUST disclose if no graphical/headless browser engine was used.

## 16. Governance effect

Before 0062 acceptance:

```text
REQ_BROKER_024_STATUS = PENDING
```

Only after exact-head implementation review, successful required gates, explicit Project Owner acceptance and canonical acceptance closure may the register advance to:

```text
REQ_BROKER_024_STATUS = IMPLEMENTED
```

REQ-BROKER-023 remains PENDING and the Broker Workspace Launch Gate remains `NOT_READY`.

## 17. Explicitly deferred

Not part of v0.1 / SLICE-0062:

- draft-to-marketplace promotion;
- NativeListing create/edit/publication controls;
- owner-direct recovery;
- background server autosave;
- offline draft creation before server identity exists;
- generalized offline-first operation;
- multi-device sync;
- collaborative/field-level merge;
- Service Worker/PWA requirement;
- media;
- branding/profile completion;
- Search-fit diagnostics;
- inventory portability/import;
- leads/CRM;
- outcomes/analytics;
- payments;
- production pilot/launch.

## 18. Acceptance summary

Accepted v0.1 boundary:

```text
authorized existing ProfessionalListingDraft
+ current server version
+ current browser form edits
→ short-lived Account/Organization/Draft-scoped local recovery
→ connectivity interruption does not silently destroy recent input
→ current server version controls safe restore behavior
→ explicit Save remains the only server mutation
```
