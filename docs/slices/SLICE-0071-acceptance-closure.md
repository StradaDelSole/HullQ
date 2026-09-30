# SLICE-0071 — Acceptance Closure

**ID:** SLICE-0071  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #273  
**Accepted implementation HEAD:** `2dc838bfdf8759c8a13ad5d1e875a82558b31cbf`  
**Implementation merge commit:** `b8b3a4ae1f937e80a3a29b8e883ca1289975f1b5`  
**Independent exact-head ACCEPT review:** 2026-09-30  
**Owner acceptance:** explicitly recorded 2026-09-30

## Accepted capability

SLICE-0071 closes the first usable Broker Lead operating loop:

```text
durable Lead
→ authorized Organization inbox/detail
→ unread/read + assignment + status
→ append-only notes/timeline
→ follow-up due/overdue
→ structured contact-attempt logging
→ bounded operational close reason
+ durable notification/outbox
→ retryable provider-neutral HullQ email notification
→ Broker Workspace deep-link
```

It also adds bounded factual Lead provenance:

```text
ACQUISITION
how the visit/session reached HullQ
+
DISCOVERY
which HullQ-owned surface led to the contacted listing
```

Broker Workspace remains authoritative. Email remains auxiliary notification only.

## Accepted implementation behavior

- Organization-scoped Lead inbox/detail are private, no-store/noindex and reuse existing Broker Workspace session/current-membership/MFA authorization;
- cross-Organization/unknown Lead access remains non-enumerating;
- assignment is limited to current ACTIVE membership in the same Organization;
- Lead operational status is separate from listing lifecycle and notification delivery state;
- accepted statuses remain `NEW`, `IN_PROGRESS`, `WAITING_FOR_BUYER`, `CLOSED`;
- closing requires a bounded operational close reason and never creates/infer SaleOutcome;
- append-only notes and structured contact attempts never overwrite the buyer message and never imply buyer response/interest;
- follow-up due date/time is durable, clearable and visible through due/overdue queue behavior;
- factual queue/dashboard counts include new/unread, unassigned, due and overdue;
- one Organization primary notification email is configurable only by current ACTIVE OWNER/ADMIN;
- PUBLISHER-only membership cannot mutate notification routing;
- Lead creation and required notification intent are atomic/idempotent;
- notification failure never loses, hides or rolls back the Lead;
- durable outbox/delivery-attempt state preserves Lead → notification → delivery-attempt correlation;
- deterministic local/test delivery adapter proves provider-neutral delivery behavior;
- no production email provider is activated in this slice;
- buyer contact email remains explicitly `UNVERIFIED`;
- acquisition provenance supports bounded UTM source/medium/campaign and optional term/content when actually evidenced;
- acquisition and discovery remain separate dimensions;
- no fingerprinting, raw-IP persistence, third-party behavioral tracking, cross-device stitching or arbitrary full URL/query-string storage was introduced;
- missing/untrusted provenance resolves to `UNKNOWN`, never guessed;
- TECHNICAL_SEARCH provenance is minted from the authoritative Search result path;
- SHORTLIST/COMPARE provenance is purpose-bound to the corresponding HullQ resolution surface;
- spoofable Referer evidence alone cannot produce authoritative INTERNAL_BROWSE;
- no concrete production INTERNAL_BROWSE emitting surface exists yet; therefore ordinary unsupported paths truthfully remain `UNKNOWN`;
- discovery signing is fail-closed/optional and cannot become a public-listing availability dependency;
- listing/Search/public truth and technical Search criterion count remain unchanged at exactly 2.

## Independent review and amendments

Initial implementation HEAD `8b0adcc5421d5c425827004434265889162aad12` implemented the full Lead operations/notification vertical but independent review found that acquisition/discovery provenance scaffolding was not wired through the real buyer-facing flow.

Amendment HEAD `bad2c51817b466983311182316309dcdfa85a3ed` wired UTM and discovery tokens end-to-end, but independent review found that public query parameters could still control which discovery surface HullQ signed.

Amendment HEAD `3a2591d1bbdc1732b4218b9a759390e6cbc70d71` removed that public FastAPI minting control, but independent review found two further material issues: spoofable Referer-only INTERNAL_BROWSE authority and a public-listing availability regression caused by discovery signing becoming a hard runtime dependency. Exact-head CI was also red.

Final amendment HEAD `2dc838bfdf8759c8a13ad5d1e875a82558b31cbf` closed all findings:

1. real buyer contact now carries bounded UTM evidence when present;
2. discovery tokens are finite, listing-bound, purpose-separated and HMAC-signed;
3. public listing reads no longer accept discovery-surface mint controls;
4. TECHNICAL_SEARCH is minted only by the actual Search path;
5. SHORTLIST and COMPARE are minted by separate purpose-bound Astro server routes;
6. Referer-based authoritative minting was removed entirely;
7. absent trusted discovery evidence remains UNKNOWN;
8. discovery signing fails closed to no token when the shared secret is absent/malformed, preserving public listing availability;
9. exact retry remains provenance-idempotent;
10. exact CI formatting scope was restored.

No material implementation finding remains.

## Decision / implementation reconciliation at acceptance

```text
DECIDED_AND_IMPLEMENTED
- D33 authoritative Broker Workspace Lead operating surface
- D34 one primary Organization notification email with OWNER/ADMIN mutation
- D35 provider-neutral notification identity / telemetry ownership
- D36 launch-bounded mini-CRM workflow + acquisition/discovery provenance
- Organization-scoped Lead inbox/detail
- unread/read state
- assignment to ACTIVE same-Organization membership
- bounded operational status
- append-only notes/timeline
- follow-up due/overdue state
- structured contact-attempt events
- bounded operational close reason
- factual queue/dashboard counts
- durable notification/outbox + delivery attempts
- retryable provider-neutral delivery port/worker
- deterministic local/test delivery adapter
- UTM acquisition provenance
- TECHNICAL_SEARCH / SHORTLIST / COMPARE discovery provenance paths
- evidence-only UNKNOWN fallback
- Search/listing/public truth unchanged
- technical native Search criteria remain exactly 2

DECIDED_NOT_YET_IMPLEMENTED
- production email-provider activation/credentials/observability
- buyer-contact email verification evidence/state transition
- a concrete production INTERNAL_BROWSE emitting UI surface
- post-promotion inventory editing
- sale/outcome workflow
- structured bulk onboarding/import
- broader broker engagement/performance reporting
- inventory portability/export
- Search exclusion explainability
- pre-publication Search-fit diagnostics
- privacy-safe aggregate demand insights
- price-change alerts
- payments/entitlements

EXPLICITLY_DEFERRED
- multi-recipient notification routing
- SMS/phone notification
- full CRM automation
- lead scoring/ranking
- cross-Organization Lead transfer
- buyer-visible messaging
- provider-specific production integration
- generalized analytics beyond accepted factual queue counts
- cross-device attribution / behavioral tracking

CONFLICT_OR_REGRESSION
- none remain on the accepted exact head
```

## Provenance semantics at acceptance

Accepted provenance remains deliberately factual and bounded.

```text
ACQUISITION
= captured evidence for how the visit/session reached HullQ

DISCOVERY
= captured first-party evidence for the HullQ surface used in this interaction
```

SHORTLIST / COMPARE do **not** mean durable verified historical buyer-interest membership. They mean the listing was resolved through the corresponding HullQ surface for this interaction.

No provenance field is allowed to alter:

- Lead eligibility;
- buyer email verification;
- Lead quality/scoring;
- listing lifecycle;
- Search eligibility/classification/ordering;
- public listing truth.

## Exact-head verification

Remote verification on accepted HEAD `2dc838bfdf8759c8a13ad5d1e875a82558b31cbf`:

```text
CI run 36663613762 → SUCCESS
Manufacturer artifact reproducibility run 36663613714 → SUCCESS
```

Independent exact-head implementation review: **ACCEPT**, review ID `5364772619`.

Implementation-agent final validation recorded:

```text
repository validator: PASS
uv run ruff format --check .: PASS
uv run ruff check .: PASS
mypy: PASS (139 source files)
PostgreSQL-backed Python suite: 5812 passed / 3 skipped / 0 failed
web tests: 345 passed / 0 failed
Astro check: 0 errors/warnings/hints
web build: PASS
SLICE-0049 retained public-listing proof: PASS
SLICE-0071 retained Lead operations/notification proof: PASS
```

PR #273 merged the exact accepted implementation to `main` as `b8b3a4ae1f937e80a3a29b8e883ca1289975f1b5`.

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

No real external broker/buyer production traffic, production pilot, paid plan or public production launch begins in 0071.

The buyer-contact email verification trigger remains binding before the first real external production buyer-contact flow is exposed/relied upon or before HullQ represents an entered buyer email as verified/trusted.

## Broker launch execution checkpoint

```text
BROKER CREATES               [implemented]
→ BROKER ADDS MEDIA          [implemented]
→ BROKER PUBLISHES           [implemented]
→ BUYER CONTACTS             [implemented]
→ BROKER HANDLES LEAD        [implemented through SLICE-0071]
→ BROKER EDITS / MAINTAINS INVENTORY
→ BROKER CLOSES / RECORDS OUTCOME
```

The Broker Workspace Launch Gate remains NOT_READY. Post-promotion inventory editing, launch-level performance/source-to-outcome analytics, usability/competitive benchmark evidence and other remaining gate requirements must still be reconciled.

## PROJECT_STATE freshness closure

```text
PROJECT_STATE_ACCEPTED_SLICE: 0071
PROJECT_STATE_QUEUE_SLICE:    0072
```

SLICE-0072 is **UNSELECTED** until fresh post-SLICE-0071 reassessment completes.

## Closure decision

```text
SLICE-0071 = OWNER_ACCEPTED
PROJECT_STATE_ACCEPTED_SLICE = 0071
PROJECT_STATE_QUEUE_SLICE = 0072
TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT = 2
BUYER_CONTACT_EMAIL_VERIFICATION_STATUS = PENDING
PRODUCTION_READINESS_GATE_STATUS = NOT_TRIGGERED
BROKER_WORKSPACE_LAUNCH_GATE_STATUS = NOT_READY
```

Implementation is merged. `FINISH_SLICE.bat` may run only after this closure PR passes independent exact-head closure review, required remote gates and guarded merge.
