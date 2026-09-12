# HullQ — System Architecture

**Status:** ACTIVE CURRENT ARCHITECTURE  
**Current rebaseline:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`  
**Application stack history:** ADR-0010 / `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md` remain historical baseline records; where they conflict with the accepted 2026-09-02 rebaseline, the rebaseline controls.  
**Post-0051 execution gates:** `docs/governance/POST_0051_TRIGGER_GATES.md` and `docs/governance/PRODUCTION_READINESS_GATE.md`

## Principle

HullQ is a native broker-first sailboat listing and technical-discovery marketplace built on deterministic, provenance-aware and configuration-aware Search.

Domain/truth boundaries are deliberately more stable than deployment providers or framework details. Current production architecture follows the accepted 2026-09-02 rebaseline and later accepted slice closures; older baselines are not authority where they conflict.

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

A small single-node DigitalOcean Managed PostgreSQL instance is acceptable for hosted internal/pre-Gate-1 work. The accepted hard redundancy trigger is:

> **Before the first real external broker production inventory is made available to real external buyers, production PostgreSQL must have automatic failover with at least one standby.**

Provider backup alone is insufficient. Production recoverability also requires an independent encrypted backup, with Cloudflare R2 EU the accepted direction unless superseded, plus tested restore. A backup is not proven until restore is proven.

The operational evidence and release blocker are centralized in `docs/governance/PRODUCTION_READINESS_GATE.md`.

## Authentication / identity / authorization

Keep these concepts distinct:

```text
Authentication = who authenticated?
HullQ identity = which immutable HullQ Account is this?
Verification   = which claims are verified?
Authorization  = what may the account/organization do?
```

Accepted authentication provider:

```text
Auth0 Public Cloud
EU tenant
authentication-only
```

HullQ owns its Account IDs, Organizations, Memberships, roles, listing ownership, publishing eligibility, verification state and authorization in PostgreSQL/domain state. Domain tables use HullQ-owned IDs rather than Auth0 subjects as business identity.

Publishing-capable broker accounts and Organization Owner/Admin accounts require MFA, preferably phishing-resistant passkeys/WebAuthn where supported. High-risk actions require step-up authentication when those actions exist. Authorization is enforced server-side in FastAPI/domain code.

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
- Organization;
- OrganizationMembership;
- PhysicalBoat;
- MarketEpisode;
- NativeListing;
- listing offer-fact revisions;
- concrete PhysicalBoat claim revisions;
- later ContactRequest/Lead, SavedQuery, Monitor and Alert when their capabilities are selected.

Phase-1 public supply remains broker/dealer/eligible-professional only. Private owners do not receive direct public FSBO publishing capability; a future owner-to-broker referral flow is a separate aggregate/capability.

Current NativeListing public lifecycle is intentionally only:

```text
DRAFT -> ACTIVE -> WITHDRAWN
```

`SOLD`, `ARCHIVED`, republish and freshness/staleness behavior remain future work until explicitly selected.

## Search

Search remains deterministic and truth-preserving.

The accepted buyer flow is:

```text
technical requirements
-> deterministic BoatDesign/configuration evaluation
-> ACTIVE native professional inventory
-> NativeListing -> MarketEpisode -> PhysicalBoat
-> publishing Organization's concrete current claims
-> contradiction guard
-> CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA
```

Hard requirements are non-compensating. Missing evidence cannot be guessed into a match.

The first production native-inventory criterion is exactly `draft_max`. Further technical criteria are governed by `docs/governance/POST_0051_TRIGGER_GATES.md`: criterion #2 must explicitly compare its bridge/path with SLICE-0051; criterion #3+ cannot create a third structural copy without passing the abstraction guard.

PostgreSQL remains the initial Search persistence/query technology. No Elasticsearch/OpenSearch/Meilisearch/Typesense service is selected without measured need.

## Search / SEO architecture

Search architecture and SEO are product architecture, not later marketing.

Interactive technical Search and indexable organic-discovery surfaces remain distinct. Arbitrary faceted combinations must not automatically become indexable URLs. Public Search/listing routes built through SLICE-0051 are deliberately bounded/noindex and do not themselves authorize broad SEO indexation.

`architecture/SEARCH_AND_SEO_ARCHITECTURE.md` controls the stable principles. Any still-open broad/indexable public-surface taxonomy, sitemap/hreflang, structured-data and promoted landing-page decisions remain gated until explicitly resolved; existing public noindex surfaces are not invalid merely because those broader decisions remain deferred.

## Accounts, saved queries and alerts

The product architecture retains:

```text
Search
  -> SavedQuery
  -> Monitor
  -> Alert
```

SavedQuery is distinct from Monitor. Search should remain broadly open; persistence, monitoring and intelligence are preferred monetization surfaces. Actual account/saved-search/monitor capabilities are implemented only through selected slices.

## Media

Primary media-storage direction is Cloudflare R2 EU when media is introduced.

Unsafe direct browser-upload-to-public-object flow is not accepted. Production media requires quarantine/validation/re-encoding/metadata stripping/derivatives before publication as specified by the accepted rebaseline. Before real broker production, original broker media requires an independent second copy at a different storage provider.

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

Production operational requirements are centralized in `docs/governance/PRODUCTION_READINESS_GATE.md` rather than scattered as soft future reminders.

## Mobile

Responsive web/PWA remains the initial mobile-access path. Flutter remains the preferred later Android/iOS client direction once recurring monitoring/alert value justifies native clients. A Flutter client consumes the same FastAPI boundary and must not reimplement HullQ domain/Search semantics.

## Post-0051 governance triggers

`docs/governance/POST_0051_TRIGGER_GATES.md` is controlling for:

1. current-architecture reconciliation before SLICE-0052 readiness;
2. the production-readiness trigger;
3. technical native-Search abstraction comparison/third-copy protection;
4. mandatory workflow-overhead reassessment after SLICE-0056 or before the first real production pilot, whichever comes first.

From SLICE-0052 onward every readiness contract must carry `**TRIGGER GATES CHECK:** PASS`; repository validation and `START_SLICE` enforce the deterministic portions.

## Boundary guardrail

Do not add social, ownership-log, weather, route-planning, financing, insurance-comparison or generic boating-app domains to the early architecture unless a later accepted product-scope decision explicitly selects them.
