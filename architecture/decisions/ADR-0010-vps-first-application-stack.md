# ADR-0010 — VPS-First Application Stack

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Decisions:** OQ-008, OQ-011, OQ-012

## Context

HullQ is a near-zero-budget side business. The project owner is willing to pay for the domain and one small VPS, but the initial product should avoid a collection of recurring paid SaaS dependencies. At the same time, the architecture must support a real commercial product with technical search, a large canonical sailboat universe, accounts, SavedQuery/Monitor/Alert workflows, background jobs, market ingestion, later mobile clients and SEO-oriented public pages.

Earlier possibilities included Cloudflare Workers/D1, managed PostgreSQL, Cloud Run, Vercel, Strapi and other combinations. Those are technically viable, but an edge-database-first launch would introduce a second application/runtime model and likely require a later migration to Python/PostgreSQL once background jobs, monitoring and richer application behavior arrive.

The accepted Python domain/research baseline is already CPython 3.14. HullQ therefore benefits from keeping canonical business/domain behavior in Python and using a conventional relational production store from the beginning.

## Decision

Adopt `docs/engineering/APPLICATION_STACK_BASELINE.v0.1.md` as HullQ's initial application/deployment baseline.

### Hosting and ingress

1. **Contabo VPS** is the selected initial hosting provider.
2. Application code targets a conventional commodity Linux VPS and MUST NOT depend on Contabo-specific application APIs.
3. Cloudflare is the preferred public edge for DNS, proxy/CDN/cache, TLS and basic WAF/abuse protection.
4. Cloudflare R2 may be used for off-VPS backups and HullQ-owned artifacts when appropriate.
5. Initial deployment should remain simple, with Docker Compose or equivalent small-host orchestration and Caddy as the preferred reverse-proxy baseline when deployment work begins.

### Backend

6. CPython 3.14 remains the authoritative domain/application runtime.
7. **FastAPI** is the selected HTTP application framework when OQ-015/API implementation is reached.
8. HullQ domain logic MUST be reused from the Python core rather than reimplemented in TypeScript, frontend code or another backend framework.
9. Long-running/scheduled work belongs in a Python worker/background execution boundary rather than HTTP request handlers.
10. No broker/distributed scheduler is part of the initial baseline without measured need.

### Persistence/search

11. **PostgreSQL** is the selected initial production persistence technology.
12. The existing SQLite allowance remains non-production Stage-2 tooling only.
13. No dedicated search engine is selected initially; technical filtering/search begins with PostgreSQL and suitable indexes/projections after query semantics are accepted.
14. Domain/query semantics MUST remain independent of PostgreSQL/ORM-specific behavior so the storage deployment can evolve without redefining HullQ.

### Web frontend

15. **Astro** is the selected web framework.
16. **TypeScript** is the default language for web/browser application code.
17. Public/SEO-oriented pages should remain static/server-rendered HTML with minimal client JavaScript.
18. **React + TypeScript may be used selectively as Astro islands** for sufficiently stateful UI such as technical search, compare, saved-search, account/dashboard and monitor management.
19. HullQ MUST NOT default to a client-only React SPA.
20. Flutter Web and Next.js are not the selected public-web baseline.
21. Strapi is not the canonical HullQ backend/data store and no CMS is required initially.

### Accounts/alerts/mobile

22. SavedQuery, Monitor and Alert remain separate product/domain concepts and must fit the application persistence/API architecture.
23. **OQ-014 remains deliberately open/deferred**: this ADR does not choose session/JWT strategy, auth library/provider, password/OAuth details, email verification/reset or privacy implementation.
24. OQ-006 continues to control alert cadence/freshness policy.
25. Responsive web/PWA is the initial mobile access path.
26. **Flutter is the preferred later Android/iOS client**, consuming the same accepted HTTP/API boundary once native mobile is justified.

## Rationale

This choice trades approximately one small VPS bill for a materially simpler long-term system:

- one authoritative Python business-logic runtime;
- one conventional PostgreSQL production store;
- unrestricted background/scheduled jobs within VPS capacity;
- straightforward account/SavedQuery/Monitor/Alert persistence;
- strong SEO through Astro/static-first HTML;
- TypeScript where browser safety/tooling matters;
- React only where component/state complexity earns its cost;
- Cloudflare still provides high-value free edge services without becoming the application/database runtime;
- a later Flutter client can reuse the same API instead of creating parallel domain logic.

The current provider is concrete for operational simplicity, while the application remains portable to another Linux VPS or managed infrastructure if economics change.

## Consequences

### Positive

- avoids an intentional D1-to-PostgreSQL and edge-runtime-to-Python migration path;
- keeps the current CPython 3.14 core relevant to the production backend;
- background jobs and monitoring are not constrained by edge request CPU/runtime limits;
- accounts, saved searches and alerts fit naturally into one relational model;
- no paid managed DB/auth/backend service is required at launch;
- deployment remains understandable for a solo project;
- public web/SEO does not require a JavaScript-heavy SPA;
- future provider migration remains possible.

### Costs / risks

- HullQ is responsible for VPS patching, PostgreSQL operations, backups, restore testing, secrets and basic service monitoring;
- a single VPS is initially a single availability domain;
- production deployment requires disciplined firewall/origin configuration and off-host backups;
- some managed-service conveniences are intentionally deferred;
- PostgreSQL/search performance must be measured before introducing specialist search infrastructure.

These costs are accepted because the initial project budget is intentionally close to zero and the architecture is expected to remain small until real traction exists.

## Alternatives considered

### Cloudflare Workers + D1 as full application runtime

Rejected as the primary baseline. It remains useful for edge services, but would create a TypeScript/D1 product runtime alongside the Python research/domain runtime and likely increase later migration work once long-running monitoring/research/application jobs mature.

### Managed Postgres + serverless backend

Technically attractive but rejected as the required initial baseline because recurring provider spend/vendor sprawl is not justified before product revenue.

### Strapi-first backend

Rejected. HullQ's canonical technical data, provenance, query semantics and monitoring are application/domain concerns rather than CMS content modelling. A CMS can be reconsidered only if real editorial workflow later requires one.

### Full React/Next.js web application

Rejected as the default public-web architecture. HullQ needs many crawlable, content-like BoatModel/BoatDesign/discovery pages; Astro with selective React islands better fits a static-first/SEO-first product while preserving rich interactive UI where required.

### Flutter for web and mobile from one UI codebase

Rejected for the public web. Native Flutter remains a later mobile preference; the SEO/public site uses standard HTML-oriented web technology.

## Deferred decisions preserved

This ADR explicitly does **not** resolve:

- OQ-006 alert cadence/freshness/cache policy;
- OQ-009 unknown-data query semantics;
- OQ-014 authentication/account/privacy implementation;
- OQ-015 public HTTP API contract/versioning;
- OQ-016 subscription pricing/limits;
- OQ-017 historical price intelligence retention;
- OQ-018 exact public URL/indexing/rendering/structured-data rules.

## Acceptance evidence

- project owner explicitly accepted the stack on 2026-08-18;
- project owner explicitly selected Contabo as the initial VPS provider;
- the chosen stack satisfies the accepted zero/near-zero recurring-budget constraint while keeping canonical domain logic provider-independent;
- the existing SLICE-0003 contract runtime remains compatible because it is local Python infrastructure with no persistence/frontend/deployment assumptions.
