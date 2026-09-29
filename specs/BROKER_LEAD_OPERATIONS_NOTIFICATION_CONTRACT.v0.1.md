# Broker Lead Operations + Notification Contract v0.1

**Status:** READY CANDIDATE  
**Owner:** SLICE-0071

## 1. Purpose

Deliver the first usable broker-side Lead operating loop after SLICE-0070:

```text
durable Lead
→ Organization-scoped inbox/detail
→ assignment/status/notes/follow-up
+ durable notification intent
→ retryable HullQ email notification
```

Broker Workspace is authoritative. Email is auxiliary notification only.

## 2. Authorization and tenancy

Every Broker Lead read/mutation requires a valid HullQ session and fresh current ACTIVE OrganizationMembership for the Lead's publishing MarketplaceOrganization.

Cross-Organization/unknown Lead access must collapse to the same non-enumerating outcome.

Lead recipient configuration is Organization-level administration. Only current ACTIVE members with `OWNER` or `ADMIN` may create/change/clear the primary Lead-notification email. `PUBLISHER` alone may not alter notification routing.

Assignment may target only a current ACTIVE member of the same Organization. Assignment does not transfer Lead ownership.

## 3. Lead inbox

Provide a private/no-store/noindex Organization-scoped Broker Workspace inbox.

Minimum projection:

- LeadId;
- NativeListingId plus bounded listing display context;
- buyer name;
- buyer contact email;
- buyer email verification state;
- received-at;
- operational status;
- assigned AccountId/member if any;
- unread/new state;
- source channel;
- bounded acquisition provenance when known;
- bounded HullQ discovery provenance when known;
- follow-up due/overdue state;
- last activity / last contact-attempt context.

Use stable deterministic keyset pagination. No cross-Organization counts or existence leaks.

## 4. Lead detail

Lead detail exposes the accepted immutable Lead envelope plus current operational state and bounded timeline.

Minimum:

- buyer name/email/verification state/message;
- listing/source/Organization attribution;
- received-at;
- current assignment;
- current operational status;
- notes/timeline;
- notification delivery summary;
- acquisition/discovery provenance when known;
- current follow-up due state;
- structured contact-attempt history;
- close reason when CLOSED;
- public listing link only when currently public-readable, without mutating historical Lead attribution.

An historical Lead remains readable to its authorized Organization after listing withdrawal/suppression.

## 5. Operational state

Introduce a bounded broker-operational status distinct from listing lifecycle and notification delivery.

v0.1 values:

```text
NEW
IN_PROGRESS
WAITING_FOR_BUYER
CLOSED
```

Creation starts at `NEW`.

Transitions must be explicit, authorized, durable and auditable. Status never changes listing lifecycle, CurrentPublicEligibility, Search truth or buyer email verification state.

## 6. Unread/new semantics

Lead creation begins unread/new for the Organization.

Opening Lead detail may explicitly mark read, or a dedicated mark-read mutation may be used. The implementation must choose one deterministic server-authoritative rule and prove concurrent/retry behavior.

Unread state is Organization-workflow metadata, not buyer truth.

## 7. Assignment

Assignment is optional.

Allowed target:

```text
current ACTIVE OrganizationMembership in the same MarketplaceOrganization
```

Persist stable AccountId and/or Membership identity consistent with existing membership truth. A revoked/deactivated assignee remains historical attribution but is no longer selectable for new assignment.

Unassign is allowed.

Assignment mutation requires authorized Broker Workspace access and must use optimistic concurrency or equivalent no-silent-overwrite semantics.

## 8. Notes / timeline

Broker notes are append-only timeline events for the Organization.

Each note preserves:

- author AccountId;
- OrganizationId;
- created-at;
- bounded note text.

Notes cannot edit buyer-supplied immutable Lead message or verification state.

Timeline also records operational status/assignment/read mutations sufficiently to reconstruct broker handling history.

No buyer-visible note surface is part of v0.1.


## 8A. Follow-up, contact attempts and bounded close

The launch-bounded Broker Lead workflow must support the ordinary daily handling loop, not merely inbox/read/status.

### Follow-up

A Lead may carry an optional current follow-up due date/time. Setting, changing and clearing follow-up is authorized Organization workflow state and must be durable, auditable and concurrency-safe.

Inbox/work-queue projections must make due and overdue follow-ups visible and filterable. Follow-up does not itself change operational status.

### Contact attempts

An authorized broker may append a structured contact-attempt event with:

- actor AccountId;
- occurred-at;
- bounded contact channel;
- optional bounded note.

The initial channel vocabulary must be bounded; EMAIL, PHONE, MESSAGING and OTHER are sufficient semantics.

A contact attempt records broker action only. It does not prove buyer receipt, buyer response or buyer interest.

Lead detail/inbox may expose derived last-activity and last-contact-attempt values from authoritative workflow events.

### Close reason

Transitioning a Lead to CLOSED requires a bounded operational close reason. Initial semantics must distinguish at least NOT_INTERESTED, UNREACHABLE, BOAT_UNAVAILABLE, DUPLICATE and OTHER or equivalent bounded labels.

Close reason is Lead workflow metadata. It must never create/infer SaleOutcome, sold status, listing lifecycle mutation or canonical buyer-intent truth.


## 8B. Lead acquisition and discovery provenance

Authorized brokers must be able to see factual provenance for how a Lead reached HullQ and how it reached the contacted listing when that evidence exists.

Keep two dimensions distinct:

1. **Acquisition provenance** — how the visit/session entered HullQ.
2. **Discovery provenance** — which HullQ surface/path led to the contacted NativeListing.

Minimum bounded acquisition semantics should distinguish DIRECT, ORGANIC_SEARCH, PAID_SEARCH/PAID_CAMPAIGN, REFERRAL, SOCIAL where evidence exists, OTHER and UNKNOWN. Validated bounded campaign identifiers such as UTM source/medium/campaign and optional UTM term/content may be preserved when actually supplied.

Minimum discovery semantics should distinguish DIRECT_LISTING, TECHNICAL_SEARCH, INTERNAL_BROWSE, SHORTLIST, COMPARE and UNKNOWN, with later HullQ surfaces extensible without replacing the model.

Where technically available, preserve first-touch acquisition separately from lead-submission/latest-touch discovery context. Do not collapse them into one ambiguous source string.

Attribution is evidence, never inference-by-guess. Absence is UNKNOWN. The implementation must not add fingerprinting, third-party tracking, raw-IP persistence, cross-device stitching, unbounded browsing-history collection or arbitrary full-referrer/query-string storage.

The existing accepted immutable Lead envelope remains authoritative and unchanged. 0071 may persist a separate immutable Lead-linked acquisition/discovery provenance record or equivalent append-only creation-time evidence. Exact schema factoring is implementation-local. Exact retry of the same Lead submission must not create conflicting duplicate attribution records.

Acquisition/discovery provenance must not change Lead eligibility, operational status, buyer email verification, Search/listing/public truth or any future Lead score.

## 9. Notification recipient configuration

Each MarketplaceOrganization may have at most one primary Lead-notification email address in v0.1.

The address:

- is bounded and syntactically validated;
- is Organization configuration/transport metadata, not Organization identity;
- does not become verified buyer/broker identity evidence;
- is mutable only by current ACTIVE OWNER/ADMIN;
- may be cleared;
- affects future notification delivery attempts only.

Do not source this value from Auth0/session claims.

## 10. Durable outbox semantics

A newly CREATED Lead must create its notification intent atomically with Lead creation whenever the accepted notification pipeline requires an event.

Exact retry / ALREADY_EXISTS must not create a duplicate notification intent.

The outbox row must carry enough immutable rendering context/identity to deliver safely while keeping the Lead as authoritative source.

Delivery states distinguish at least:

```text
PENDING
DELIVERED
FAILED_RETRYABLE
FAILED_TERMINAL
NO_RECIPIENT_CONFIGURED
```

No-recipient Lead creation still succeeds and remains visible in Broker Workspace.

Email delivery failure never rolls back, deletes or hides the Lead.

## 11. Email delivery boundary

Email is sent by HullQ, never by impersonating the buyer.

Minimum message content:

- “new HullQ lead” context;
- target listing/boat display context;
- buyer name;
- buyer contact email plus explicit VERIFIED/UNVERIFIED label;
- bounded message excerpt or full bounded message if safe;
- direct authenticated Broker Workspace Lead-detail link.

No internal IDs beyond those needed in the authenticated link, authorization details, persistence errors or secrets may leak.

Provider integration is behind an application port/interface. A deterministic local/test adapter is sufficient for 0071 acceptance. External production provider credentials/activation remain Production Readiness work.

## 12. Retry / worker semantics

Delivery claims one outbox item safely, records attempts, and prevents uncontrolled duplicate sending.

Required behavior:

- DELIVERED is terminal/idempotent;
- FAILED_RETRYABLE may become PENDING/claimed again under bounded retry policy;
- FAILED_TERMINAL is not auto-retried;
- concurrent workers cannot both own/send the same attempt;
- crashes before delivery-result commit leave a recoverable deterministic state.

Exact scheduling/backoff values are implementation-local.


## 12A. Notification identity, telemetry and future CRM extensibility

HullQ owns the semantic identities used for Lead notification and workflow history. The implementation must preserve stable correlation from:

```text
Lead
→ durable notification intent
→ delivery attempt(s)
→ optional provider message identifier
```

Exact schema/type names remain implementation-local. Provider identifiers are transport metadata only.

0071 does not need production-provider webhooks or open/click ingestion. However, its outbox/delivery and timeline foundations must not require replacement when later provider adapters add normalized delivery, delay, bounce, complaint or engagement events.

Notification transport/engagement must remain distinct from Lead workflow and buyer intent. A delivered/opened/clicked notification cannot itself change Lead operational status, buyer email verification state, Lead quality or Search/listing truth. Authenticated Broker Workspace actions remain the authoritative broker-workflow evidence.

The deterministic local/test adapter may expose only the delivery outcomes needed for 0071 acceptance. Production-provider activation, provider webhook ingestion, bounce/complaint processing, open/click telemetry, inbound email/reply relay and generalized CRM analytics remain later capabilities.

## 13. Privacy and email verification

Buyer email remains exactly the SLICE-0070 contact value and verification state. 0071 must not transition `UNVERIFIED` to verified.

`BUYER_CONTACT_EMAIL_VERIFICATION_STATUS = PENDING` remains unchanged.

Broker notification recipient email and buyer contact email are separate concepts.

## 14. APIs / browser surface

At minimum:

- Organization Lead inbox read;
- Organization Lead detail read;
- authorized assignment/status/read/note mutations;
- authorized follow-up set/change/clear mutation;
- authorized structured contact-attempt append mutation;
- bounded close-reason mutation when closing;
- OWNER/ADMIN notification-recipient read/update;
- internal delivery-worker operation that is not a public unauthenticated business endpoint.

Browser surfaces remain private/no-store/noindex and use existing session/MFA/CSRF patterns appropriate to each mutation.

## 15. Concurrency

Tests must prove:

- duplicate buyer submission creates one Lead + one notification intent;
- Lead creation commit cannot leave Lead without required outbox intent;
- notification failure does not affect Lead;
- concurrent delivery workers do not produce uncontrolled duplicate delivery;
- concurrent assignment/status mutations do not silently overwrite each other;
- cross-Organization access/mutation remains impossible;
- membership revocation is observed fresh.

## 16. Independence invariants

Broker Lead operations/notification must not mutate:

- NativeListing lifecycle/freshness;
- offer/PhysicalBoat claim/media truth;
- PublicationReadiness/CurrentPublicEligibility;
- Search eligibility/classification/order;
- buyer contact email verification state.

## 17. Required retained proof

Real PostgreSQL + FastAPI + built Astro proof must demonstrate:

1. accepted SLICE-0070 Lead appears in correct Organization inbox;
2. foreign Organization cannot enumerate/read it;
3. broker opens detail with source/listing context;
4. assign/status/note/read workflow persists;
5. OWNER/ADMIN configures notification recipient; PUBLISHER-only cannot;
6. one durable notification intent per Lead;
7. test email adapter receives one HullQ-authored notification with dashboard deep-link and UNVERIFIED label;
8. retryable delivery failure preserves Lead and later succeeds without duplicate committed delivery;
9. no recipient produces visible Lead plus explicit no-recipient notification state;
10. listing withdrawal does not remove historical Lead;
11. acquisition/discovery provenance is shown when evidenced and UNKNOWN when absent, without fingerprinting/raw-IP persistence;
12. follow-up due/overdue filtering and dashboard counts are correct;
13. structured contact attempts append to timeline without implying buyer response;
14. closing requires a bounded close reason and creates no SaleOutcome/listing lifecycle change;
15. listing/Search/public truth unchanged.

## 18. Non-goals

- external production email vendor activation;
- buyer email verification;
- SMS/phone notification;
- full CRM automation;
- lead scoring;
- cross-Organization Lead transfer;
- buyer-facing broker replies/messages;
- sale/outcome;
- inventory editing;
- generalized analytics/reporting beyond the launch work-queue/dashboard factual counts;
- Search changes.
