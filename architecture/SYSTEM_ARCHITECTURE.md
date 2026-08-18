# HullQ — System Architecture

**Status:** ACTIVE logical + accepted initial application/deployment architecture  
**Application stack:** ADR-0010 / `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md`

## Principle

HullQ is a technical query/search layer over a mostly static sailboat-design universe and, where access permits, external market inventory. Domain boundaries are intentionally more stable than framework choices.

The initial implementation is deliberately optimized for a near-zero-budget side business: one Contabo Linux VPS plus the domain are the only expected fixed infrastructure costs at launch. Cloudflare remains the preferred edge layer. The application must remain portable to another commodity Linux VPS or managed infrastructure without redefining HullQ domain semantics.

## Logical components

```text
[Web / Search UI]
        |
        v
[HullQ Application/API Boundary]
   |                    |
   v                    v
[Design Domain]      [User / Monitoring Domain]
 BoatModel             Search
 BoatDesign             SavedQuery
 NamedVariant           Monitor
 DesignOption           Alert
 ResolvedConfiguration  SubscriptionEntitlement
   |
   v
[Technical Query Engine]
   |
   +----------------------------+
   |                            |
   v                            v
[Design results]       [Market Search Orchestrator]
                                |
                                +--> [Source Adapter A]
                                +--> [Source Adapter B]
                                +--> [Deep-link/partner paths]
                                |
                                v
                         [Normalize / Identity Match]
                                |
                                v
                         [Permitted cache/history]
```

Separately:

```text
[Research Queue]
→ [Independent Research Pipeline]
→ [Source / Evidence / Field Resolution]
→ [Validation / Conflict Review]
→ [Canonical Design Domain]
```

## Accepted initial technology/deployment baseline

OQ-008, OQ-011 and OQ-012 are resolved by ADR-0010.

```text
                         Internet
                            |
                      Cloudflare edge
                  DNS / CDN / WAF / TLS
                            |
                            v
                     Contabo Linux VPS
                            |
                 reverse proxy (Caddy baseline)
                            |
             +--------------+---------------+
             |                              |
             v                              v
        Astro web                      FastAPI API
        TypeScript                     CPython 3.14
        React islands                       |
        only where useful                   |
             |                              |
             +--------------+---------------+
                            v
                        PostgreSQL
                            |
                 background/scheduled worker
                            |
                 optional off-VPS R2 storage
```

### Web

- Astro is the selected framework.
- TypeScript is the default browser/web language.
- Public/SEO-oriented pages should be normal static/server-rendered HTML with minimal client JavaScript.
- React is not the whole-site architecture; React + TypeScript is used selectively as Astro islands for sufficiently stateful UI such as search, compare, saved-search/account/dashboard and monitor management.
- No client-only React SPA is the baseline.
- Flutter Web and Next.js are not the selected public-web baseline.
- No CMS is required initially; Strapi is not the HullQ backend or technical-data store.

Exact public page taxonomy, URL grammar, faceted-index policy, rendering/canonicalization/sitemap behavior and structured-data mapping still require OQ-018 before public frontend implementation.

### Backend

- CPython 3.14 remains the authoritative HullQ domain/application runtime.
- FastAPI is the selected HTTP application framework when the API slice begins.
- Canonical domain/query/research rules live in the Python core and must not be duplicated in TypeScript or frontend state.
- Scheduled/long-running jobs belong in a Python worker/background boundary rather than request handlers.
- No Redis/Celery/Temporal/Airflow/message broker is part of the initial baseline without measured need.

The actual stable HTTP API/versioning/OpenAPI boundary remains governed by OQ-015.

### Production persistence and search

- PostgreSQL is the accepted initial production relational store.
- Existing stdlib SQLite remains limited to non-production Stage-2 local research/job-control use.
- Technical search/filtering begins with PostgreSQL plus appropriate indexes/projections after OQ-009 query semantics are accepted.
- No dedicated Elasticsearch/OpenSearch/Meilisearch/Typesense service is part of the initial architecture.
- Specialist search infrastructure may be introduced later only from measured need.
- Domain/search semantics remain storage-independent; PostgreSQL is persistence technology, not semantic authority.

### Hosting / operations

- Contabo is the chosen initial VPS provider.
- HullQ targets a conventional commodity Linux VPS and must not depend on Contabo-specific application APIs.
- Cloudflare remains preferred for public DNS/proxy/CDN/cache/TLS/basic WAF and may provide Turnstile/R2 where later slices select them.
- Simple Docker Compose or equivalent small-host orchestration is preferred when deployment work begins; Kubernetes is explicitly out of baseline scope.
- PostgreSQL must have automated off-VPS backups before production/user data is relied upon. R2 is the preferred low-cost direction, but exact backup/restore/encryption/retention procedures belong to an operations slice.

## Core domain entities

Stable conceptual entities include:

- BoatModel
- BoatDesign
- NamedVariant
- DesignOption
- ResolvedConfiguration (derived)
- Source
- FieldEvidence / FieldResolution / DerivationRecord
- ResearchJob
- Search
- SavedQuery
- Monitor
- Alert
- SubscriptionEntitlement
- MarketListing
- SourcePlatform

Additional deployment/persistence entities MUST be introduced only when their governing slice/decision is accepted.

## Design database

The design universe is mostly static and follows the accepted broad-coverage / progressive-depth strategy. Identity semantics are governed by `specs/IDENTITY_MODEL.v0.1.md` / ADR-0004.

BoatModel is the commercial lineage; BoatDesign is the technical production generation; independent factory choices are DesignOptions; NamedVariants are not automatically generations. Variant-sensitive search operates on derived ResolvedConfigurations rather than mutating canonical baselines.

## Provenance boundary

Canonical searchable values remain separate from source evidence under accepted OQ-004 / ADR-0006. `FieldEvidence` records source observations, `FieldResolution` records canonical decisions, and `DerivationRecord` records calculated/inherited lineage. Direct source claims must not be confused with derived values: ResolvedConfiguration values and ratios require derivation lineage, not fabricated source evidence.

## Search and SEO architecture

Search Architecture and SEO are first-class product architecture under ADR-0007 and `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`. The interactive technical-query surface and the public organic-discovery surface share canonical domain data but are not identical: arbitrary filter combinations MUST NOT automatically become an unbounded indexable URL space.

OQ-018 still gates the exact public URL grammar, indexable page taxonomy, faceted crawl/index policy, rendering strategy, canonicalization/sitemaps and structured-data mapping. Astro was selected partly because it supports the static-first/crawlable HTML direction; the framework choice does not itself resolve OQ-018.

## Accounts, saved queries and alerts

The application architecture explicitly supports:

```text
Search
  -> SavedQuery
  -> Monitor
  -> Alert
```

SavedQuery is persisted independently from Monitor. A user may save a query without monitoring it; subscription entitlement may later control monitoring capacity/frequency without changing query semantics.

Authentication/account/session/privacy implementation is **deliberately deferred to OQ-014**. ADR-0010 does not choose JWT vs server sessions, auth library/provider, password/OAuth mechanics, email verification/reset or privacy details. The eventual auth design must support the web product and later Flutter clients.

OQ-006 controls monitor/alert cadence, freshness and cache policy.

## Mobile

Responsive web/PWA is the initial mobile-access path. Flutter is the preferred later Android/iOS client technology once recurring monitoring/alert use justifies native apps. Flutter consumes the same accepted API boundary; it must not become a second implementation of HullQ domain/query semantics.

## Market access

No marketplace access method is assumed. OQ-013 must document official API/feed/partner/deep-link/automation, display and storage constraints per source before a production adapter is built.

The historical 15–60 minute cache idea is only a hypothesis. OQ-006 controls actual freshness/cadence/cache policy, and each source's rights/access terms may impose stricter rules.

## Market history / price intelligence

Pro price intelligence is a product direction, not yet a persistence permission. OQ-017 must define what observations HullQ may lawfully retain, how asking-price snapshots and listing lifecycle are represented, and how trends are computed. A disappeared listing MUST NOT be interpreted as a completed sale without supporting evidence.

## Source health

For integrations that exist, use exception-oriented monitoring such as:

- last successful run;
- error state;
- result count anomaly;
- latency;
- schema/parse failures;
- rights/access status change.

The business goal is minimal unplanned maintenance, so maintenance minutes per source are a first-class operational metric.

## Alert execution

A Monitor evaluates a persisted technical SavedQuery. It may resolve matching BoatDesign/ResolvedConfiguration candidates and then evaluate supported market sources. Alerts are events produced by Monitors; they are not the same object as SavedQuery state.

Background market logic must resolve listing identity only to the highest evidence-supported precision and must not invent generation/configuration specificity.

## Boundary guardrail

Do not add social, ownership-log, weather, route-planning, financing, insurance-comparison or generic boating-app domains to the early architecture unless a later accepted product-scope decision explicitly does so.
