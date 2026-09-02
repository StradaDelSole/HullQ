# HullQ Architecture Rebaseline — Trust-First Native Listing Market

**Date:** 2026-09-02  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** all post-SLICE-0039 architecture and implementation planning  

## 1. Purpose

This document freezes the current HullQ product/architecture direction after the native-listing-market pivot, the Boats Group/YachtWorld complaint review, the private-seller policy decision, an independent architecture review, and the owner decisions on frontend, database, authentication, deployment, security and redundancy.

Where an older planning document conflicts with this file, the newer explicit decision in this file controls once merged.

All non-conflicting strict-truth, provenance, fail-closed, configuration-scope, explicit `UNKNOWN`, source/media-rights, ONE-CAPABILITY, VISIBLE-RESULT, slice-isolation and exact-head review rules remain in force.

---

## 2. Product direction

HullQ will build a **native, broker-first sailboat listing/discovery market** on top of HullQ's deterministic, provenance-aware and configuration-aware technical Search system.

The intended buyer loop is:

```text
technical requirements
→ deterministic BoatDesign/configuration evaluation
→ native professional inventory
→ physical-boat/listing truth
→ Saved Search
→ monitoring
→ alerts
→ broker contact / qualified lead
```

Native HullQ professional inventory is the strategic market foundation.

Authorized external marketplace/API/feed observations may supplement coverage, but HullQ's viability must not depend on a single external marketplace or on unauthorized scraping.

HullQ is initially a listing/discovery/lead platform, not a transaction platform. The initial scope excludes:

- escrow;
- boat-purchase payment settlement;
- ownership transfer;
- closing execution;
- brokerage execution by HullQ.

---

## 3. Truth and identity boundaries

The marketplace pivot does not weaken HullQ's truth architecture.

Fundamental invariant:

```text
DESIGN / CONFIGURATION TRUTH
≠
PHYSICAL BOAT / LISTING TRUTH
```

Canonical technical knowledge about a BoatDesign or Configuration does not prove the corresponding fact for a specific physical boat.

Broker/seller claims about a physical boat are evidence/observations and do not silently become canonical truth.

Existing semantic invariants remain controlling:

```text
UNKNOWN ≠ FALSE
UNKNOWN ≠ TRUE
CONFLICT ≠ RESOLVED
AMBIGUOUS ≠ RESOLVED
NEAR MISS ≠ CONFIRMED MATCH
```

Hard requirements remain hard. Missing evidence may not be guessed, probabilistically promoted or silently defaulted.

The marketplace domain must keep the following concepts distinct:

```text
BoatDesign / canonical technical identity
        │
        ▼
PhysicalBoat / MarketVessel
        │
        ▼
MarketEpisode
        │
        ├───────────────┐
        ▼               ▼
NativeListing     ExternalMarketObservation
        │
        ▼
ListingSnapshot / ListingEvent
```

A physical boat is not a listing. One physical boat may have multiple listing appearances and multiple market episodes over time.

### 3.1 MarketEpisode

`MarketEpisode` is retained as a first-class concept because lifetime physical-vessel history and one continuous sale episode are different facts.

Episode continuity must be evidence-based.

Do **not** define a universal rule such as `gap < 14 days = same episode`.

Instead future episode resolution should be able to represent:

```text
SAME
NEW
UNRESOLVED
```

Potential evidence may include:

- explicit sold/withdrawn/relisted signals;
- seller/broker change;
- listing/source identity;
- price state;
- physical-vessel identity;
- time gap;
- source health/outage evidence;
- observations on other sources.

Time gap is a signal, not sole truth.

Deep MarketEpisode analytics may be deferred until later.

---

## 4. Dedup / physical-vessel identity

Deduplication is a Day-1 domain requirement, not a later UI convenience.

The same boat may appear simultaneously on:

```text
broker website
YachtWorld
Boat24
HullQ Native Listing
```

These may represent one `PhysicalBoat`, but HullQ must never force a merge without sufficient evidence.

False merge can be worse than unresolved duplication.

Future physical-vessel identity tests must include at least these edge cases:

1. **Rename/re-registration:** the same physical yacht returns years later under a new name or registration.
2. **Sister ships:** two same-model/same-year boats in the same harbor with similar specs remain distinct unless evidence proves identity.

Quality measurement should consider both false merges and false splits/unresolved duplicates.

---

## 5. Broker-only public supply

Phase-1 public HullQ supply is strictly:

```text
BROKER / DEALER / ELIGIBLE PROFESSIONAL ORGANIZATION ONLY
```

A private consumer account must not receive the capability to publish a public `NativeListing`.

This is a domain authorization rule, not only a UI choice.

Invariant:

> Every publicly published `NativeListing` must have an eligible professional Organization as its publishing principal.

Strategic reasons include:

- avoid direct channel conflict with the brokers whose inventory HullQ needs;
- avoid reproducing the documented YachtWorld private-seller/broker trust conflict;
- reduce fraud/identity/ownership/moderation burden from public FSBO supply;
- preserve a professional accountability layer while still treating broker claims as evidence rather than unquestioned truth;
- avoid unnecessary trader/private-seller regulatory and disclosure complexity in Phase 1.

HullQ will not introduce public FSBO listing monetization in Phase 1.

---

## 6. Private-owner referral channel

Private owners are handled through a separate domain aggregate such as:

```text
BrokerageRequest
```

not through a hidden or unpublished `NativeListing`.

Conceptual flow:

```text
private owner
→ BrokerageRequest
→ deterministic eligible-broker shortlist
→ broker responses
→ owner chooses broker
→ possible brokerage mandate
```

Initial shortlist eligibility should be based on transparent factual criteria:

```text
service/geographic area
AND
vessel specialization
AND
accepted deal segment
```

Deal segment may include accepted vessel length and value ranges.

Initial response window direction: approximately **two business days**, not a blind literal 48-hour timer across weekends.

Meaningful broker response states may include:

```text
INTERESTED
DECLINED
NEED_MORE_INFORMATION
```

Opening an email is not a response.

### 6.1 Referral exhaustion

A request must have an explicit terminal state when no eligible/interested broker remains:

```text
EXHAUSTED
```

The owner must receive an honest status and may be offered actions such as:

```text
REQUEST_UPDATE
RETRY_LATER
CLOSE_REQUEST
```

HullQ must not silently drop the request and must not turn it into a public FSBO listing as a fallback.

### 6.2 Referral gaming

A broker clicking `INTERESTED` must not automatically earn a positive performance signal.

Future referral quality may include a lightweight outcome loop such as:

```text
broker INTERESTED
→ owner later confirms whether contact was actually established
→ optional confirmation whether the broker was selected
```

These are internal referral-quality signals, not public broker shaming.

### 6.3 Referral ranking vs buyer search ranking

Hard separation:

```text
seller-referral broker ordering
≠
organic buyer listing/search relevance
```

Referral behavior must never improve organic buyer-search ranking.

The referral rule should be publicly documented and non-pay-to-win.

The architecture boundary is pre-Gate-1. Full referral automation may remain a later bounded capability.

---

## 7. Known future actor: co-brokerage

Co-brokerage / buyer-broker vs seller-broker relationships are a known later domain extension.

Do not implement them Pre-Gate-1, but do not hard-code the lead model so that one listing broker must forever be the only professional relationship in a transaction.

Status: **DEFERRED, KNOWN EXTENSION**.

---

## 8. Listing lifecycle and freshness

Lifecycle and freshness are different state dimensions.

Invariant:

```text
ListingLifecycleStatus
≠
ListingFreshnessStatus
```

Illustrative lifecycle states:

```text
DRAFT
ACTIVE
WITHDRAWN
SOLD
ARCHIVED
```

Illustrative freshness states:

```text
CONFIRMED
DUE_FOR_CONFIRMATION
STALE
UNKNOWN
```

Hard truth rules:

```text
STALE ≠ SOLD
DISAPPEARED ≠ SOLD
ACTIVE does not imply CURRENTLY CONFIRMED
```

For manual native broker listings, the initial policy direction is a configurable confirmation TTL around **30 days** plus a grace period around **7 days**.

A listing that remains unconfirmed after the applicable policy may be removed/suppressed from normal current-market results without destroying its history and without inventing `SOLD`.

For authoritative feeds, successful feed presence can refresh freshness. Sudden source disappearance must be treated according to source/feed semantics and source-health evidence, not automatically as sold.

The domain rule is fixed now; the full Freshness capability must remain its own bounded slice rather than being folded into the first marketplace slice.

---

## 9. Leads as a trust boundary

A buyer lead is a security-sensitive marketplace object, not merely an outgoing email.

The architecture should support a persistent `Lead` / `ContactRequest` concept with information such as:

- buyer/account reference;
- target listing;
- broker Organization;
- source attribution;
- message;
- delivery/view/response state;
- safety/moderation state;
- audit history.

Avoid building a full messenger initially.

Preferred initial direction:

```text
verified buyer
→ ContactRequest
→ validation / rate limits / safety checks
→ broker sees lead in HullQ
→ broker accepts / responds / declines / flags
→ direct contact may continue outside HullQ
```

### 9.1 Staged contact disclosure

For privacy and scam reduction, full personal contact data should not necessarily be exposed immediately on lead creation.

Preferred direction:

```text
ContactRequest created
→ broker sees verified HullQ identity indicators + message
→ broker accepts contact
→ appropriate direct contact details released
```

HullQ must not use staged disclosure to trap users in an internal messenger. After accepted contact, direct off-platform communication is allowed.

Lead origin/acceptance timestamps preserve attribution.

Potential initial safety controls include:

- verified account before contact;
- rate limiting;
- spam/fraud controls;
- block/neutralize URLs in initial contact where appropriate;
- no arbitrary attachments initially;
- report/flag capability.

Do not create a single opaque global trust score.

---

## 10. Authentication, identity, verification and authorization

Keep these concepts separate:

```text
Authentication = who logged in?
Identity       = which HullQ account is this?
Verification   = what claims are verified?
Authorization  = what may the account do?
```

### 10.1 Auth provider

Selected initial provider:

```text
Auth0 Public Cloud
EU tenant
```

Auth0 is **authentication-only**.

Auth0 is not authoritative for:

- HullQ Organizations;
- broker status;
- Organization membership;
- listing ownership;
- publishing eligibility;
- marketplace roles;
- referral eligibility;
- pricing entitlements;
- verification state;
- moderation state.

### 10.2 HullQ-owned account identity

HullQ uses its own immutable Account UUID and provider-agnostic external identity mapping.

Conceptually:

```text
(provider / issuer, subject)
→ AuthIdentity
→ HullQ Account UUID
```

Domain tables reference HullQ UUIDs, not Auth0 subjects.

Email is a verified attribute, not the immutable identity key.

This preserves provider portability and enables future multiple identities per HullQ account.

### 10.3 Organization authorization

Conceptual ownership path:

```text
Account
→ OrganizationMembership
→ BrokerOrganization
→ NativeListing
```

Authorization must be enforced server-side in FastAPI/domain code.

Cross-organization/tenant isolation requires explicit adversarial tests.

---

## 11. Broker security

Publishing-capable broker accounts and Organization Owner/Admin accounts require MFA.

Preferred phishing-resistant method:

```text
Passkeys / WebAuthn
```

TOTP may be an acceptable fallback. SMS is not the preferred primary second factor.

High-risk capabilities should require fresh/step-up authentication **when those capabilities exist**, including examples such as:

- ownership transfer;
- staff-role changes;
- API/feed credential creation;
- mass inventory deletion;
- security/recovery changes.

Do not prematurely implement a huge step-up matrix for actions that do not yet exist, but retain the security policy.

---

## 12. Search / calibration remains controlling

The marketplace pivot does not replace the Search Product Contract.

Existing required semantics remain in force:

- hard `Required` constraints remain hard;
- `Prefer` is distinct;
- accepted OR/AND/exclusion semantics remain explicit;
- configuration awareness remains mandatory;
- near misses remain structurally separate from confirmed matches;
- `UNKNOWN` and `CONFLICT` remain first-class.

The frozen Representative Query Acceptance Suite remains non-compensating:

```text
44 / 44 required
```

A failed required query blocks that launch candidate. Do not swap, weaken or remove failing queries merely to create a PASS.

---

## 13. Corpus / market coverage

The old approximately 20–30-design Gate-1 seed ceiling is superseded.

Principle:

> **Coverage, not arbitrary design count.**

The existing approximately 1,700 identity-resolved/canonical designs remain a legitimate enrichment target where scalable processing is practical.

Track separately:

- Catalog Coverage;
- Active-Market Coverage.

Do not invent a percentage before a defensible denominator exists.

---

## 14. Buyer Launch Inventory Readiness Gate

External Buyer Validation must not begin while results are materially determined by missing HullQ inventory rather than the actual target market.

Do not invent a round-number launch threshold before real broker feeds establish a denominator.

Before external Gate 1, define the Target Pilot Market and assess at least:

- independent participating broker Organizations;
- active confirmed listings;
- geographic/vessel-category diversity;
- canonical BoatDesign mapping rate;
- freshness rate;
- coverage of representative buyer cases;
- HullQ inventory coverage against a meaningful market reference/sample where available.

Hard gate principle:

> **External Buyer Validation must not start while missing HullQ inventory materially dominates the observed search outcome.**

The quantitative threshold must be calibrated using real initial supply data and locked before external Gate 1.

This does not block SLICE-0040.

---

## 15. External source rights

External source rights/admission governance remains fail-closed.

Existing conceptual states such as:

```text
AVAILABLE / PARTNER_REQUIRED / UNVERIFIED / UNAVAILABLE
```

and:

```text
ALLOWED / CONDITIONAL / UNKNOWN / BLOCKED
```

remain valid where applicable.

Core rule:

> **Rights UNKNOWN → fail closed.**

Technical scrapeability is not permission.

Preferred external access paths include authorized APIs, partner feeds, direct broker inventory, CRM/DMS feeds, syndication and explicitly authorized recurring access.

---

## 16. Professional supply / portability

HullQ must not require professional suppliers to recreate all inventory manually.

Progressive intake direction:

```text
manual listing
→ CSV bulk import
→ XML / JSON / API feed
→ broker inventory feed
→ CRM/DMS integration
→ syndication destination
```

Do not build all paths at once.

Broker marketplace guardrails:

- broker branding is supported;
- no forced exclusivity;
- multihoming is allowed;
- easy in / easy out;
- reasonable data portability;
- lead attribution is core;
- moderation is explainable;
- organic technical relevance is not pay-to-win.

Sponsored placement, if ever introduced, must remain clearly separate from organic relevance.

---

## 17. Pricing is reopened

The old fixed `Free / Plus / Pro` structure is no longer controlling after the native-marketplace pivot.

Individual concepts may survive, but packaging/pricing must be revalidated across the changed marketplace.

Current commercial actor model:

```text
Buyer
Broker / Dealer / Professional Supply
Private Owner as Referral Source (not public seller)
Professional/Data Customer (possible later)
```

Do not monetize private owners through public FSBO listing fees in Phase 1.

Early broker inventory may rationally be free/very low-friction because inventory itself creates marketplace value.

Buyer Search should not be intentionally made bad to force payment.

Potential future paid value may include monitoring scale, advanced market intelligence, professional analytics/workflow and API/data access.

Architecture rule:

> Avoid hard-coded plan-name business logic.

Prefer generic capabilities/entitlements that commercial packaging can map to later.

Gate 1 may test willingness-to-pay hypotheses, but no previous Free/Plus/Pro package or price is controlling.

Separate Product Pull from Pay Pull.

---

## 18. Web/backend stack

Owner-accepted target:

```text
Astro
+ React for interactive surfaces
+ FastAPI / Python modular monolith
```

FastAPI remains the sole application/domain API boundary.

Desired separation:

```text
Astro/React = presentation
FastAPI = application/domain/API
PostgreSQL = durable application truth
```

Do not duplicate domain rules in a second frontend backend.

No microservices, Kubernetes, Kafka or distributed architecture by default.

Potential logical modules may include catalog, market, identity, authorization, trust/safety, leads, monitoring, media, moderation and audit while remaining a modular monolith.

---

## 19. PostgreSQL / production database

Development:

```text
Local PostgreSQL 18
```

Production target:

```text
DigitalOcean Managed PostgreSQL 18
FRA1
Standard Edition
```

Approved extensions where needed:

- `postgis`;
- `pg_trgm`;
- `pgcrypto`.

`pgaudit` is **approved/available but not a mandatory Pre-Gate-1 baseline extension**. Activate it only when real audit/compliance/security requirements justify the operational cost.

Avoid provider-proprietary DB dependencies unless explicitly approved.

---

## 20. Database cost staging and HA trigger

Cost-conscious staging:

### Development

```text
local PostgreSQL 18
cloud DB cost = €0
```

### Hosted internal / Pre-Gate-1 validation

A small DigitalOcean Managed PostgreSQL single node is acceptable initially. Start small and scale only from measured load.

### Public real-broker production

Hard redundancy trigger:

> **Before the first real external broker production inventory is made available to real external buyers, PostgreSQL HA with at least one standby must be active.**

Do not postpone this based on a vague later "production maturity" feeling.

---

## 21. Database backup / recoverability

Provider backup alone is insufficient.

Required architecture:

```text
DigitalOcean Managed PostgreSQL
  ├→ provider backup / PITR
  └→ independent encrypted logical backup
        ↓
      Cloudflare R2 EU
```

Working retention direction:

```text
7 daily + 4 weekly
```

Critical rule:

> **A backup is not proven until a restore is proven.**

Regular restore tests are mandatory.

Separate app DB credentials from backup DB credentials and use least privilege.

---

## 22. Media architecture and redundancy

Primary media direction:

```text
Cloudflare R2 EU
```

Unsafe path is forbidden:

```text
browser upload → public object
```

Preferred processing boundary:

```text
upload
→ private quarantine
→ validate
→ decode
→ re-encode
→ strip EXIF/GPS
→ generate derivatives
→ publish approved output
```

Before real broker production, original broker media must have an **independent second copy at a different storage provider**.

Only original/source media requires mandatory provider-independent duplication; reproducible derivatives may be regenerated from preserved originals.

Provider-internal durability is valuable but is not the same as provider independence.

Retention/object-lock style protections should be considered for destructive-error resistance.

Media credentials and backup credentials must be separated.

---

## 23. Data security, redundancy and app-host philosophy

Owner priorities:

1. data security — super-high priority;
2. redundancy/recoverability — core requirement;
3. portability / low lock-in;
4. operational simplicity;
5. cost discipline.

Redundancy-ready architecture does not mean expensive active-active infrastructure everywhere on day one.

Critical production data must not exist only on the Contabo/application VPS.

Durable state is externalized:

- PostgreSQL → managed DB;
- media → object storage;
- auth → managed IdP;
- backups → independent storage;
- code/container images → Git/GHCR.

App hosts should be stateless/replaceable enough that a lost VPS can be rebuilt from known code/config/images.

Future compute redundancy should use a second app host at an independent provider when marketplace availability warrants it.

---

## 24. Deployment

Owner-accepted initial deployment:

```text
GitHub Actions
→ tests/security checks
→ immutable versioned container images
→ GHCR
→ controlled deployment
→ Docker Compose on replaceable app host
```

Do not use `latest` as production truth.

Do not build production dependencies on the production host.

Do not install Coolify or Dokploy as an initial production control plane.

They may be reconsidered only if later operational burden clearly justifies the additional privileged control plane.

No broad self-hosted CI runner is permitted on production hosts.

Production deployment should support known-version health checks and rollback.

When two app hosts exist, host-by-host deployment can provide rolling availability without introducing a large control plane.

---

## 25. Database migrations

Container rollback does not reverse destructive database migrations.

Use:

- Alembic;
- versioned/reviewable migrations;
- explicit migration visibility;
- compatibility-conscious rollout.

For risky live-schema changes prefer:

```text
expand
→ migrate/backfill
→ contract
```

---

## 26. Job/worker architecture

Initial direction:

```text
PostgreSQL outbox/job pattern
+ one Python worker
+ scheduler/cron where appropriate
```

No Redis, Celery, Kafka or Kubernetes by default.

Scheduled workloads may later include monitoring, stale checks, alerts, referral expiry, feed processing and maintenance.

Idempotency and observability are required.

---

## 27. DSGVO / incident response

Before real external broker/buyer personal data is handled in production, HullQ must have a concise documented security/privacy incident-response runbook.

The runbook should cover at least:

```text
detect
→ contain
→ preserve evidence
→ assess affected data
→ risk assessment
→ notification decision
→ authority notification where required
→ user/data-subject notification where required
→ remediation
→ postmortem
```

This is required operational governance, not an enterprise-SOC project.

Data architecture should also support appropriate retention, export, deletion, PII minimization and private-data protection from SSR/SEO/logging leakage.

---

## 28. Gate-1 philosophy

Gate 1 is a slim but functionally complete validation of the actual HullQ proposition, not a deliberately tiny technical demo.

Expected product loop:

```text
complete intended Search Product Contract
→ realistic BoatDesign coverage
→ browser Validation UI
→ native professional inventory
→ physical-boat/listing truth
→ Saved Search
→ monitoring
→ real alerts
→ credible monetization hypotheses
→ burn-in
→ external validation
```

Slim means minimal polish and unnecessary infrastructure, not removal of the core value loop.

---

## 29. ONE-CAPABILITY enforcement

The architecture may define several future domain rules at once, but implementation remains slice-bounded.

Do **not** turn SLICE-0040 into a broad marketplace foundation bundle.

Freshness, dedup, professional publishing eligibility, listing persistence, lifecycle, media, auth, leads and referrals should each be implemented in appropriately bounded capabilities as dependencies require.

A rule being architecturally known before SLICE-0040 does not mean it must be implemented inside SLICE-0040.

---

## 30. Proposed SLICE-0040 direction

No SLICE-0040 exists yet.

Current preferred first post-rebaseline capability:

> **Marketplace Identity / Truth Boundary**

Its purpose is to establish/prove that core marketplace identities cannot silently collapse into one another:

```text
BoatDesign
≠ PhysicalBoat
≠ MarketEpisode
≠ NativeListing
≠ ExternalMarketObservation
```

The exact executable acceptance criterion must be narrowed before slice creation.

Professional publishing eligibility should remain a separate capability if combining it would violate ONE-CAPABILITY.

Freshness and MarketEpisode resolution rules are architecturally defined in this rebaseline but must not be pulled into SLICE-0040 merely for convenience.

---

## 31. Explicit supersessions

The following older directions are superseded where they conflict:

### Marketplace deferred
Superseded. Native marketplace is now part of the product foundation.

### External marketplace access required for Gate 1
Superseded. External sources are optional authorized supplements.

### Public seller / private seller equivalent to broker supply
Superseded. Public Phase-1 supply is professional/broker-only; private owners use BrokerageRequest/referral.

### Old Free/Plus/Pro pricing
Superseded. Pricing is reopened.

### Arbitrary ~20–30 BoatDesign Gate-1 corpus
Superseded. Coverage is the governing concept.

### Simple temporary validation auth as final architecture
Superseded as architecture. Auth0 EU + HullQ-owned authorization is the selected target, although implementation may remain staged.

### `pgaudit` mandatory Pre-Gate-1
Not controlling. `pgaudit` is optional/deferred until justified.

---

## 32. Target architecture ≠ implemented state

This document is a target architecture / governance decision.

Do not pretend all components already exist.

In particular, do not assume that:

- Astro migration is already complete;
- Auth0 is already integrated;
- DigitalOcean production DB is already provisioned;
- HA is already active;
- R2 media quarantine already exists;
- second-provider media backup already exists;
- broker Organizations are implemented;
- NativeListing domain objects are implemented;
- the referral system exists.

Implementation must proceed through bounded reviewed slices.

---

## 33. Controlling one-sentence architecture

> **HullQ will be built as a buyer-first, provenance-aware, broker-only-public-supply sailboat listing/discovery marketplace with deterministic configuration-aware Search, strict physical-vessel/listing truth separation, monitoring and trust-first leads, using an Astro/React frontend, FastAPI modular monolith, PostgreSQL 18, managed and independently recoverable data infrastructure, Auth0 EU for authentication only, HullQ-owned authorization, mandatory privileged-broker MFA, safe media quarantine with provider-independent original-media redundancy, and deliberately low-complexity replaceable containerized app hosts.**
