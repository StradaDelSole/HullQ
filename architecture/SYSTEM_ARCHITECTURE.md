# HullQ — System Architecture

**Status:** ACTIVE CURRENT ARCHITECTURE  
**Current infrastructure/application rebaseline:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`  
**Current marketplace-supply rebaseline:** `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`  
**Application stack history:** ADR-0010 / `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md` remain historical baseline records; where they conflict with later accepted rebaselines, the later accepted decision controls.  
**Post-0051 execution gates:** `docs/governance/POST_0051_TRIGGER_GATES.md` and `docs/governance/PRODUCTION_READINESS_GATE.md`

## Principle

HullQ is a native **broker-first mixed-supply** sailboat listing and technical-discovery marketplace built on deterministic, provenance-aware and configuration-aware Search.

Professional broker/dealer inventory remains strategically central, but bounded owner-direct/private seller inventory is now accepted product direction. The previous broker-only/current-FSBO-out-of-scope statement is superseded by the 2026-09-14 owner-direct product direction.

Domain/truth boundaries are deliberately more stable than deployment providers or framework details. Current production architecture follows the accepted 2026-09-02 infrastructure/application rebaseline, the 2026-09-14 owner-direct product direction and later accepted slice closures; older baselines are not authority where they conflict.

## Current product/application topology

```text
                         Internet
                            |
                      Cloudflare edge
                DNS / CDN / WAF / TLS
                            |
                            v
                 replaceable Linux app host
                         Caddy origin
                            |
             +--------------+---------------+
             |                              |
             v                              v
        Astro web                      FastAPI API
        TypeScript                     CPython 3.14
        React islands                       |
        where justified                     |
             +--------------+---------------+
                            |
                            v
              DigitalOcean Managed PostgreSQL 18
                         FRA1
                            |
                 background/scheduled Python worker

Auth: Auth0 Public Cloud, EU tenant, authentication-only
Media / independent backups: Cloudflare R2 direction where applicable
Images: CI-built immutable containers -> GHCR -> versioned Docker Compose deploy
```

FastAPI is the sole application/domain API boundary. Astro owns SSR/presentation and must not access PostgreSQL directly or duplicate HullQ Search/domain semantics. React is used only for sufficiently interactive Astro islands; it is not the whole-site architecture.

The initial deployment control plane is deliberately small: CI-built immutable Docker images, GHCR, versioned Docker Compose, controlled deploy/health-check/rollback and replaceable app hosts. Coolify, Dokploy, Kubernetes, Swarm, service mesh and a second business-logic backend are not part of the accepted initial architecture.

## Durable-state boundary

Critical durable production state must not depend on the application host.

```text
application truth  -> DigitalOcean Managed PostgreSQL 18 FRA1
identity/authn      -> Auth0 EU for authentication only
HullQ authorization -> PostgreSQL/domain state
media               -> object storage when introduced
DB recovery         -> provider backup/PITR + independent encrypted logical backup
code/images         -> Git + GHCR
```

Application hosts should be stateless/replaceable enough that loss of a host does not lose canonical application data.

### PostgreSQL availability / recoverability

Local development uses PostgreSQL 18.

A small single-node DigitalOcean Managed PostgreSQL instance is acceptable for hosted internal/pre-Gate-1 work. The previously accepted hard redundancy trigger was framed around real external broker production inventory. After the 2026-09-14 mixed-supply pivot, no owner-direct production path may exploit that broker-specific wording as a loophole: before real external marketplace inventory is made available to real external buyers, the applicable Production Readiness/HA boundary must be explicitly reconciled for the supply type being launched.

Provider backup alone is insufficient. Production recoverability also requires an independent encrypted backup, with Cloudflare R2 EU the accepted direction unless superseded, plus tested restore. A backup is not proven until restore is proven.

The operational evidence and release blocker are centralized in `docs/governance/PRODUCTION_READINESS_GATE.md`.

## Authentication / identity / authorization

Keep these concepts distinct:

```text
Authentication       = who authenticated?
HullQ identity       = which immutable HullQ Account is this?
Verification         = which claims are verified?
Authorization        = what may the account/organization/person do?
Sale authority       = what evidence supports the right to offer this vessel?
```

Accepted authentication provider:

```text
Auth0 Public Cloud
EU tenant
authentication-only
```

HullQ owns its Account IDs, Organizations, Memberships, roles, listing ownership, publishing eligibility, verification state and authorization in PostgreSQL/domain state. Domain tables use HullQ-owned IDs rather than Auth0 subjects as business identity.

Publishing-capable broker accounts and Organization Owner/Admin accounts require MFA, preferably phishing-resistant passkeys/WebAuthn where supported. High-risk actions require step-up authentication when those actions exist. Authorization is enforced server-side in FastAPI/domain code.

Owner-direct identity/trust is a separate future boundary, not a reuse of professional membership roles. The accepted direction distinguishes phone reachability, strong identity verification, right-to-list attestation and documentary sale-authority verification. Private sellers must not be seeded as fake brokers/Organizations merely to pass the current professional authorization path.

If strong private-seller ID-document/selfie/liveness verification is later implemented, prefer a provider-bounded/data-minimizing design: raw identity/biometric artifacts should remain outside ordinary HullQ storage where feasible, while HullQ stores only the bounded result/reference/method/timestamp and necessary normalized attributes justified by the owning capability/legal basis.

## Core truth and identity boundaries

Hard marketplace identity boundary:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

Relationships:

```text
PhysicalBoat -> optional BoatDesignRef
MarketEpisode -> PhysicalBoatId
NativeListing -> optional MarketEpisodeId
ExternalMarketObservation -> optional MarketEpisodeId
```

Hard truth rule:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

A BoatDesign/configuration can establish technical eligibility without establishing a fact about an offered physical yacht. Broker/seller physical-boat claims are concrete evidence/claims and do not become canonical design truth.

Seller trust also does not become vessel truth:

```text
PHONE VERIFIED
IDENTITY VERIFIED
RIGHT-TO-LIST ATTESTED
SALE AUTHORITY VERIFIED
!= technical-field confirmation
```

Existing fail-closed semantics remain controlling:

```text
UNKNOWN != FALSE
UNKNOWN != TRUE
CONFLICT != RESOLVED
AMBIGUOUS != RESOLVED
NEAR MISS != CONFIRMED MATCH
```

## Design / provenance domain

Stable conceptual entities include:

- BoatModel;
- BoatDesign;
- NamedVariant;
- DesignOption;
- ResolvedConfiguration;
- Source;
- FieldEvidence;
- FieldResolution;
- DerivationRecord.

Canonical searchable values remain separate from source evidence under accepted OQ-004 / ADR-0006 semantics. `FieldEvidence` records source observations, `FieldResolution` records canonical decisions, and `DerivationRecord` records calculated/inherited lineage.

SLICE-0051 added durable versioned/current FieldResolution persistence for the bounded native technical-Search path. It did not authorize a global all-field resolver/backfill.

## Marketplace domain

Accepted marketplace concepts include:

- Account;
- professional Organization;
- OrganizationMembership;
- private seller identity/trust state when implemented;
- PhysicalBoat;
- MarketEpisode;
- representation / sale-authority context when implemented;
- NativeListing;
- listing offer-fact revisions;
- concrete PhysicalBoat claim revisions;
- later ContactRequest/Lead, SavedQuery, Monitor and Alert when their capabilities are selected.

Current accepted supply direction is:

```text
broker/dealer/eligible-professional supply
+
bounded owner-direct/private seller supply
```

A private seller ultimately chooses owner-direct self-listing or an explicit broker-referral path. Referral is opt-in and commercial arrangements must not buy shortlist preference.

### Implemented versus accepted future supply path

Accepted implementation through SLICE-0053 remains professional-only on the write side. Current `NativeListing` creation/publishing authorization is not silently widened by this product-direction change.

Owner-direct publishing needs an explicit bounded application/domain/persistence/API surface under a selected future capability. It must reuse the stable marketplace identities/truth rules without bypassing professional authorization boundaries.

Normal future owner-direct publication is directed toward a proportionate baseline:

```text
HullQ account
+ verified phone reachability
+ explicit right-to-list attestation
+ baseline anti-abuse checks
```

Strong ID verification, mandatory vessel-document upload or physical boat challenge are not universal publication prerequisites. Risk/dispute evidence may trigger stronger identity or documentary sale-authority verification.

### Representation conflict

Do not solve professional-vs-owner-direct overlap with a permanent `one NativeListing per PhysicalBoat` shortcut.

Representation conflict belongs around:

```text
PhysicalBoat
-> MarketEpisode
-> representation / sale-authority context
-> one or more NativeListings only where semantically legitimate
```

Future implementation must distinguish active mandate, ended mandate, legitimate multi-representation where allowed, identity uncertainty and disputed authority. No automatic destructive overwrite/delete is implied by the pivot.

Current NativeListing public lifecycle is intentionally only:

```text
DRAFT -> ACTIVE -> WITHDRAWN
```

Sale/outcome remains a separate explicit future concept; a stale/withdrawn/disappeared listing is never silently SOLD.

## Search

Search remains deterministic, truth-preserving and now explicitly **commercially independent**.

The organic Search invariants are:

```text
commercial consideration MUST NOT affect:
- organic eligibility
- match classification
- organic ordering
```

Broker/private-seller subscription tier, verification payment, referral economics, affiliate value, advertising relationship or other HullQ revenue opportunity is not an organic Search input.

Payment may fund a real verification/inspection/document-processing service. It may not buy `CONFIRMED`, Search eligibility or organic position. Equivalent admissible evidence must resolve equivalently regardless of who paid to produce/process it.

The currently implemented accepted buyer flow remains professional-supply-specific:

```text
technical requirements
-> deterministic BoatDesign/configuration evaluation
-> ACTIVE native professional inventory
-> NativeListing -> MarketEpisode -> PhysicalBoat
-> publishing Organization's concrete current claims
-> contradiction guard
-> CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA
```

The owner-direct pivot does not silently add private inventory to that path. A future owner-direct Search bridge must preserve the same truth semantics while using the correct seller/representation authority.

Hard requirements are non-compensating. Missing evidence cannot be guessed into a match.

The first production native-inventory criterion is exactly `draft_max`. Further technical criteria are governed by `docs/governance/POST_0051_TRIGGER_GATES.md`: criterion #2 must explicitly compare its bridge/path with SLICE-0051; criterion #3+ cannot create a third structural copy without passing the abstraction guard.

PostgreSQL remains the initial Search persistence/query technology. No Elasticsearch/OpenSearch/Meilisearch/Typesense service is selected without measured need.

## Search / SEO architecture

Search architecture and SEO are product architecture, not later marketing.

Interactive technical Search and indexable organic-discovery surfaces remain distinct. Arbitrary faceted combinations must not automatically become indexable URLs. Public Search/listing routes built through SLICE-0051 are deliberately bounded/noindex and do not themselves authorize broad SEO indexation.

`architecture/SEARCH_AND_SEO_ARCHITECTURE.md` controls the stable principles. Any still-open broad/indexable public-surface taxonomy, sitemap/hreflang, structured-data and promoted landing-page decisions remain gated until explicitly resolved; existing public noindex surfaces are not invalid merely because those broader decisions remain deferred.

The owner-direct Search-commercial-independence invariant applies to every later Search/SEO surface: organic technical truth/discovery must never become a paid seller-positioning channel.

## Accounts, saved queries and alerts

The product architecture retains:

```text
Search
  -> SavedQuery
  -> Monitor
  -> Alert
```

SavedQuery is distinct from Monitor. Search should remain broadly open; persistence, monitoring and intelligence are preferred monetization surfaces. Actual account/saved-search/monitor capabilities are implemented only through selected slices.

## Monetization boundary

Professional/private-seller tools and services may be monetized without selling organic Search truth.

Current owner-direct direction:

```text
basic self-listing -> free baseline
verification/inspection/document processing -> optional paid service
broker referral economics -> possible later, after explicit seller opt-in
transaction/insurance/finance/title partner services -> possible later where useful/lawful
```

A separately labelled sponsored/featured advertising surface is deferred, not permanently prohibited. If later accepted, it must be mechanically and visually separate from organic results: it cannot alter organic eligibility/classification/ordering, replace an organic result, consume organic pagination positions or masquerade as an organic recommendation.

A future vetted escrow/transaction-safety partner is an optional product opportunity. HullQ becoming custodian of transaction funds is not implied and requires a separate owner-accepted regulatory/legal/architecture/business decision.

## Media

Primary media-storage direction is Cloudflare R2 EU when media is introduced.

Unsafe direct browser-upload-to-public-object flow is not accepted. Production media requires quarantine/validation/re-encoding/metadata stripping/derivatives before publication as specified by the accepted rebaseline. Before real external marketplace media is relied upon in production, backup/rights/privacy requirements must be reconciled for the applicable professional/private supply path rather than treating broker-only wording as a loophole.

Perceptual image hashing and external stolen-image matching are not assumed Day-1 owner-direct fraud capabilities; they require their own measured need/readiness.

## Deployment / operations

Accepted initial deployment path:

```text
GitHub Actions
-> tests/security checks
-> immutable versioned container images
-> GHCR
-> controlled deploy
-> versioned Docker Compose
-> known-version health check
-> rollback to previous known-good version
```

Do not use mutable `latest` as production truth. Do not build production dependencies on the production host. No broad self-hosted CI runner belongs on production hosts.

Background/scheduled work initially remains a Python worker/scheduler boundary. No Redis/Celery/Temporal/Airflow/Kafka is selected without measured need.

Production operational requirements are centralized in `docs/governance/PRODUCTION_READINESS_GATE.md` rather than scattered as soft future reminders. The first owner-direct production/pilot capability must explicitly reconcile any existing gate language that is broker-specific before activation.

## Mobile

Responsive web/PWA remains the initial mobile-access path. Flutter remains the preferred later Android/iOS client direction once recurring monitoring/alert value justifies native clients. A Flutter client consumes the same FastAPI boundary and must not reimplement HullQ domain/Search semantics.

## Post-0051 governance triggers

`docs/governance/POST_0051_TRIGGER_GATES.md` remains controlling for:

1. architecture/current-state reconciliation;
2. the production-readiness trigger;
3. technical native-Search abstraction comparison/third-copy protection;
4. mandatory workflow-overhead reassessment after SLICE-0056 or before the first real production pilot, whichever comes first.

From SLICE-0052 onward every readiness contract must carry `**TRIGGER GATES CHECK:** PASS`; repository validation and `START_SLICE` enforce the deterministic portions.

After the 2026-09-14 pivot, applicable readiness/reassessment must also inspect `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md` and may not rely on the superseded broker-only/FSBO-out-of-scope assumption.

## Boundary guardrail

Do not add social, ownership-log, weather, route-planning, generic boating-app or generalized financial-services domains to the early architecture unless a later accepted product-scope decision explicitly selects them.

Owner-direct transaction-support opportunities (for example vetted insurance/finance/title/escrow partners) do not authorize HullQ to become an insurer, lender, title authority or funds custodian without a separate explicit decision.
