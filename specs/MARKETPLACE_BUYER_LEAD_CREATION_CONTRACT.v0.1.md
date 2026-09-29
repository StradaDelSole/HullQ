# Marketplace Buyer Lead Creation Contract v0.1

**Status:** READY CANDIDATE  
**Owner:** SLICE-0070  
**Scope:** durable buyer contact / Lead creation from a currently public NativeListing

## 1. Purpose

Define the first durable buyer→broker contact boundary without building a broker CRM.

```text
currently public-eligible NativeListing
+ bounded buyer contact payload
→ authoritative current-public recheck
→ durable Lead
→ immutable listing / publishing-Organization / source attribution
→ explicit contact-email verification state
```

## 2. Separation of concerns

```text
Lead creation
!= broker Lead operating workflow
!= email delivery
!= email verification
!= buyer Account identity
!= sale/outcome
!= analytics
```

SLICE-0070 owns Lead creation only.

## 3. Buyer authentication boundary

A HullQ Account is **not required** to submit a contact request.

Required buyer-supplied fields:

- name;
- contact email;
- message.

If a valid HullQ buyer session is present, the resulting Lead may additionally carry that AccountId as attribution.

AccountId is optional attribution only. It does not:

- become the Lead identity;
- change listing/current-public eligibility;
- make the contact email verified;
- change Lead priority;
- change Search truth or ordering.

## 4. Lead identity and idempotency

Introduce a durable opaque `LeadId` independent from NativeListingId, OrganizationId and AccountId.

The browser/request supplies one bounded opaque submission-operation identity suitable for retry-safe creation.

For the same submission-operation identity:

- exact same immutable Lead envelope → idempotent existing result;
- materially different Lead envelope → deterministic conflict;
- no duplicate Lead row may be created.

The implementation may choose the exact UUID/value type consistent with existing HullQ identity patterns.

## 5. Authoritative listing target

The client supplies only the target NativeListing identity, never authoritative Organization ownership.

At Lead creation the server must:

1. resolve the NativeListing;
2. re-evaluate canonical D29 CurrentPublicEligibility at the request's current `as_of`;
3. derive the publishing Organization from authoritative NativeListing truth;
4. reject creation when the listing is missing or not currently public-eligible.

Missing, DRAFT, WITHDRAWN and ACTIVE-but-suppressed targets collapse to one non-enumerating public outcome.

A stale browser page or previously public listing never grants a capability to create a Lead after current-public eligibility is lost.

## 6. Durable Lead truth

A created Lead must durably preserve at least:

- LeadId;
- submission-operation identity;
- NativeListingId;
- publishing MarketplaceOrganizationId captured from authoritative listing truth;
- optional buyer AccountId when a valid session is present;
- bounded buyer name;
- bounded buyer contact email;
- explicit contact-email verification state;
- bounded buyer message;
- bounded source/channel attribution;
- received-at timestamp;
- retry/content fingerprint or equivalent state needed for deterministic idempotency.

The first source/channel is the public HullQ listing contact surface.

Do not store raw object-storage/media identity, Search ranking state, broker membership, client-supplied Organization identity or unnecessary authentication claims in the Lead.

## 7. Contact email verification state

Initial v0.1 Lead creation records buyer-supplied contact email as:

```text
UNVERIFIED
```

unless an explicit later accepted verification authority provides actual verification evidence.

A logged-in Account does not verify an arbitrary form email.

Delivery success, broker response, Lead handling or matching an Account profile must not silently become verification evidence.

The data model must preserve a forward-compatible explicit verification state so a later verification capability can transition using evidence rather than reinterpret historical rows.

### Mandatory follow-up

Email verification is `DECIDED_NOT_YET_IMPLEMENTED`, not optional backlog.

Repository trigger:

```text
before first real external production buyer-contact flow is exposed/relied upon
OR before HullQ represents/uses a buyer contact email as verified/trusted
→ BUYER_CONTACT_EMAIL_VERIFICATION_STATUS = IMPLEMENTED
```

SLICE-0070 itself does not implement email delivery/token verification.

## 8. Input validation and privacy

All buyer-controlled strings must be normalized/validated at the FastAPI/application boundary with explicit finite limits.

At minimum:

- name: non-blank, bounded;
- email: syntactically valid enough for contact routing, bounded, no control characters;
- message: non-blank, bounded, no control characters inappropriate for persisted text.

Do not infer identity/trust from free-form values.

The Lead record must not persist raw client IP, User-Agent or unrelated request headers as marketplace truth.

Any operational abuse metadata, if introduced later, belongs to a separate privacy/retention boundary.

## 9. Anonymous public mutation security

The public submission path must be same-origin bounded and fail closed.

Implementation must use the repository's accepted public mutation protections appropriate to an anonymous browser POST, including:

- accepted Origin/same-origin validation;
- non-simple request/header or equivalent CSRF boundary where applicable;
- strict JSON/body size limits;
- no client authority over Organization attribution;
- no secret/internal error detail in public responses.

Vendor CAPTCHA and production edge rate limiting are not required for this internal/synthetic slice, but the endpoint must not make them architecturally impossible.

Real public buyer-contact exposure remains blocked by Production Readiness and the email-verification trigger.

## 10. Public API outcomes

The public creation boundary must expose a small deterministic result vocabulary including at least:

- CREATED or accepted/idempotent equivalent;
- LISTING_NOT_AVAILABLE;
- INVALID_INPUT;
- SUBMISSION_CONFLICT;
- bounded service failure behavior.

The implementation may collapse exact retry into CREATED/ALREADY_EXISTS or expose a distinct idempotent status, provided retries are safe and non-enumerating behavior is preserved.

Do not expose whether a suppressed listing exists, Organization internals, buyer Account internals, or persistence details.

## 11. Buyer-visible surface

The currently public listing page gains a bounded contact form.

Minimum UX:

- name;
- email;
- message;
- submit;
- visible success state;
- visible invalid-input state;
- visible listing-no-longer-available state;
- visible retry-safe service failure state.

The form must not imply the email is verified.

No broker inbox UI is part of this slice.

## 12. Persistence and transactionality

Lead creation must be one PostgreSQL transaction.

The current-public eligibility check and Lead insertion must not permit a stale-public race that creates a Lead for a listing whose public eligibility was already invalidated before the authoritative creation decision.

Exact locking/serialization may reuse existing NativeListing/current-public authorities. Do not introduce a second listing eligibility definition.

If the accepted current-public model cannot provide a safe creation boundary without a new material global locking policy, stop for reassessment.

## 13. Attribution

At creation, capture attribution that is actually known rather than reconstructing it later.

Required v0.1 attribution:

- target NativeListingId;
- publishing OrganizationId;
- source channel = HullQ public listing contact;
- received-at.

Optional authenticated AccountId is captured when available.

Do not fabricate campaign/Search context that the request does not actually carry.

Future Search/campaign attribution may extend Lead source context without changing Lead identity.

## 14. Readback / proof boundary

0070 must include a private/internal persistence readback sufficient for automated tests and retained proof to verify the exact created Lead.

This does not authorize the Broker Workspace Lead inbox/detail surface.

No public Lead lookup endpoint is required or permitted merely for proof.

## 15. Search and marketplace truth independence

Lead creation must not affect:

- technical Search eligibility;
- match classification;
- organic ordering;
- PublicationReadiness;
- CurrentPublicEligibility;
- NativeListing lifecycle/freshness;
- PhysicalBoat/MarketEpisode truth.

Accepted technical native Search criterion count remains exactly 2.

## 16. Abuse / production boundary

0070 uses synthetic/internal proof.

It does not activate:

- external buyer production traffic;
- Production Readiness PASS;
- Broker Workspace Launch Gate PASS;
- paid broker plan;
- public production launch.

Before real external use, applicable production edge abuse/rate controls and the email-verification trigger must be satisfied.

## 17. Required proof matrix

Automated tests must prove at least:

1. anonymous valid submission creates exactly one durable Lead;
2. authenticated submission records optional AccountId without changing email state from UNVERIFIED;
3. client cannot choose/override publishing Organization attribution;
4. DRAFT/WITHDRAWN/missing/ACTIVE-suppressed targets all fail through the bounded listing-not-available outcome;
5. exact retry is idempotent;
6. same operation identity with different envelope conflicts and creates no duplicate;
7. invalid name/email/message produces zero mutation;
8. public response leaks no internal Organization/auth/persistence detail;
9. current-public loss before authoritative creation prevents Lead creation;
10. concurrent duplicate submissions create exactly one Lead;
11. transaction failure leaves no partial Lead;
12. Lead creation does not mutate lifecycle/freshness/offer/claim/media/Search truth;
13. buyer-facing Astro form succeeds end-to-end through FastAPI/PostgreSQL;
14. repository validator/ruff/mypy/full PostgreSQL suite/web check/build/tests remain green.

## 18. Explicit non-goals

Not in SLICE-0070:

- broker Lead inbox/detail;
- assignment;
- status/stage;
- notes/timeline;
- broker response tracking;
- outbound email notification;
- email verification delivery/token flow;
- phone verification;
- CAPTCHA vendor;
- sale/outcome;
- analytics/reporting;
- lead scoring/ranking;
- lead transfer between Organizations;
- post-promotion listing editing;
- Search criterion changes;
- production launch/pilot.
