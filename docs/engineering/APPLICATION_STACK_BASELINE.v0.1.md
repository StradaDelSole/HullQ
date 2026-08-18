# HullQ — Application Stack Baseline v0.1

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Controls:** OQ-008, OQ-011, OQ-012 / ADR-0010

## Purpose

Define HullQ's initial web/application/deployment baseline before persistence, API, frontend and account work begins. The baseline is deliberately optimized for a near-zero-budget side business: aside from the domain and the selected VPS, the initial architecture SHOULD NOT require recurring paid SaaS services.

The baseline chooses technologies and deployment boundaries. It does not define authentication/session semantics, alert cadence, the public HTTP API contract, or public SEO URL/indexing details; those remain governed by their dedicated open questions.

## Cost and operations guardrail

Initial fixed infrastructure is intentionally limited to:

- domain registration;
- one small Contabo Linux VPS.

Cloudflare's free services MAY be used for DNS/proxy/CDN/WAF/TLS and related edge protection. Cloudflare R2 MAY be used for backups or HullQ-owned artifacts when useful and economically appropriate.

Do not introduce a recurring paid managed service merely for convenience while the selected VPS can safely provide the required capability with acceptable maintenance. Conversely, do not preserve self-managed infrastructure once measured maintenance/risk materially exceeds the business value; migration remains an explicit future decision.

Operational KPI: **profit / human maintenance hour** remains more important than minimizing a mature system's hosting bill at all costs.

## Deployment target

### Current provider

- **Contabo VPS** is the selected initial hosting provider.

### Portability rule

Application code MUST target a conventional commodity Linux VPS rather than Contabo-specific application APIs. Contabo is the selected provider, not a domain/runtime dependency.

Initial deployment topology is expected to use simple containerized services, typically Docker Compose or an equivalently small deployment mechanism. Do not introduce Kubernetes or distributed orchestration without measured need.

Expected logical services when their slices arrive:

```text
Cloudflare edge
      |
      v
Contabo Linux VPS
      |
      +-- reverse proxy / TLS origin boundary (Caddy preferred baseline)
      +-- Astro web output / web service as required
      +-- FastAPI application API
      +-- PostgreSQL
      +-- background/scheduled worker when monitoring/research needs it
```

Exact container, network, firewall, backup and deployment automation belongs to later operational slices.

## Edge / public ingress

Cloudflare remains the preferred public edge layer for:

- DNS;
- proxy/CDN/cache;
- TLS/edge certificate handling;
- basic WAF/abuse protection;
- optional Turnstile or related anti-abuse controls if selected by the relevant security/auth slice;
- optional R2 storage for encrypted backups and HullQ-owned artifacts.

Cloudflare is **not** the canonical application runtime, production relational database, or domain-logic authority under this baseline.

## Backend

### Language/runtime

- CPython 3.14 remains the authoritative HullQ Python runtime.
- Accepted HullQ domain/research code under `src/hullq/` is reused by the application/backend rather than reimplemented in another language.

### HTTP application framework

- **FastAPI** is the selected application/backend framework when the HTTP API slice begins.
- The public/stable API surface and versioning remain governed by OQ-015 and MUST NOT be invented before that gate.

### Background work

Scheduled/long-running jobs such as monitoring, data refreshes, market ingestion and alert generation SHOULD run in the Python application/worker environment on the VPS when introduced. Do not force long-running work into request handlers.

No Redis/Celery/Temporal/Airflow/message broker is part of the initial baseline. Add one only after measured requirements justify it.

## Production persistence and search

- **PostgreSQL** is the selected initial production relational persistence technology.
- Domain/search semantics MUST remain independent of PostgreSQL/ORM-specific behavior.
- Storage access SHOULD remain behind repository/adapter boundaries so a future managed PostgreSQL or other deployment change does not redefine HullQ domain semantics.
- No dedicated Elasticsearch/OpenSearch/Meilisearch/Typesense service is selected initially.
- Technical filtering/search begins with PostgreSQL plus appropriate indexes/projections once query semantics are accepted.
- A dedicated search engine MAY be introduced later only after measured query/scale evidence demonstrates a real need.

The existing stdlib SQLite allowance from ADR-0009 remains limited to Stage-2 local/non-production research/job-control use; it is not the production application database.

## Web frontend

### Base framework/language

- **Astro** is the selected web framework.
- **TypeScript** is the default language for browser/web application code.
- Public/SEO-oriented pages SHOULD be static/server-rendered HTML with minimal client JavaScript, consistent with ADR-0007 and the later OQ-018 decision.

### React usage

React is **not** the whole-site architecture and HullQ MUST NOT default to a client-only React SPA.

React + TypeScript MAY be used as Astro islands where interaction/state complexity justifies it, expected examples including:

- technical search/filter UI;
- compare UI;
- saved-search management;
- account/dashboard UI;
- monitor/alert management.

Simple pages and interactions SHOULD remain Astro + TypeScript without React when React adds no material value.

### Explicit non-selections

- Flutter Web is not the primary public web frontend.
- Next.js is not the selected baseline.
- Strapi is not the HullQ application backend or canonical technical-data store.
- No CMS is required initially; editorial/static content may live in repository-managed Astro content/Markdown/MDX until a later business need justifies a CMS.

## Accounts, SavedQuery, Monitor and Alert

The architecture MUST support the already accepted separation:

```text
Search
  -> SavedQuery
  -> Monitor
  -> AlertEvent / Alert
```

User/account persistence will live in the production application persistence boundary when implemented. However:

- **OQ-014 remains deliberately unresolved** for authentication/session/security/privacy implementation;
- do not choose JWT vs server session, password/OAuth provider, auth library/service, email verification or reset mechanics before the dedicated auth/account decision;
- the eventual auth design MUST support the web product and later Flutter mobile clients without changing canonical HullQ query/monitor semantics;
- OQ-006 continues to govern monitor cadence/freshness/cache policy.

## Mobile

- Native mobile is deferred until the web MVP and recurring-use/monitoring value justify it.
- **Flutter** is the preferred later Android/iOS client technology.
- Flutter will consume the same accepted application/API boundary rather than duplicate domain rules.
- Responsive web/PWA behavior is the initial mobile-access path.

No Flutter implementation belongs in early web/backend slices unless an explicit later slice authorizes it.

## Backups and recoverability

Production PostgreSQL MUST have automated off-VPS backups before real production/user data is relied upon.

Preferred low-cost direction:

```text
PostgreSQL backup
  -> compress/encrypt
  -> Cloudflare R2 or another independently stored backup target
```

Exact backup frequency, retention, encryption, restore testing, secrets management and disaster-recovery procedures belong to an operational/release slice and MUST be tested rather than merely documented.

## Scaling path

Default order of response to real growth:

1. optimize indexes/queries and application behavior;
2. vertically resize the Contabo VPS if economically sensible;
3. split worker/web/database responsibilities only when measured load or operational risk justifies it;
4. move PostgreSQL or other components to managed services only when revenue/maintenance economics justify the recurring cost;
5. introduce a dedicated search service only after measured search requirements exceed PostgreSQL's practical role.

Do not pre-architect venture-scale distributed infrastructure.

## Deferred decisions explicitly preserved

- OQ-006 — alert cadence/freshness/cache policy;
- OQ-009 — unknown-data query semantics;
- OQ-014 — authentication/account/privacy implementation;
- OQ-015 — stable public HTTP API/versioning;
- OQ-016 — subscription limits/pricing;
- OQ-017 — durable price-history semantics/rights;
- OQ-018 — exact public SEO/search surface.

These are not implicitly solved by this stack baseline.
