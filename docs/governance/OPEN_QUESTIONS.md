# HullQ — Open Questions Register

**Status:** ACTIVE

This register is canonical for unresolved project decisions. Existing legacy `D-*` identifiers are preserved as aliases until resolved.

| ID | Legacy | Question | Status | Gate | Decision output |
|---|---|---|---|---|---|
| OQ-001 | D-001 | Exact derived-ratio methodology, units, rounding, applicability and missing-data behavior | DECIDED | Before ratio implementation | `specs/DERIVED_METRICS_SPEC.v1.0.md` + ADR-0008 + schemas + golden tests |
| OQ-002 | D-002 | Taxonomy refinements required after benchmark evidence | DEFERRED | Benchmark exit | new taxonomy version if needed |
| OQ-003 | D-003 | Model vs generation vs variant identity boundary | DECIDED | Before broad canonical ingestion | `specs/IDENTITY_MODEL.v0.1.md` + ADR-0004 |
| OQ-004 | D-004 | Persistence shape for field-level provenance/evidence | DECIDED | Before persistence implementation | `specs/PROVENANCE_MODEL.v0.1.md` + FieldEvidence/FieldResolution/Derivation contracts + ADR-0006 |
| OQ-005 | D-005 | Cross-platform physical-listing deduplication identity | DEFERRED | Before multi-source normalized listing UI | dedup spec + test corpus |
| OQ-006 | D-006 | Alert cadence, freshness and cache TTL policy | DEFERRED | Before automated alerts | alert/freshness spec |
| OQ-007 | D-007 | Required source licensing/rights metadata | DECIDED | Before open-data bootstrap ingestion | `specs/SOURCE_SCHEMA.v0.2.json` + `specs/SOURCE_RIGHTS_POLICY.v0.1.md` + ADR-0005 |
| OQ-008 | D-008 | Final frontend technology | DECIDED | Before frontend implementation | ADR-0010 + later accepted 2026-09-02 rebaseline: Astro + TypeScript; selective React islands only where interaction justifies them |
| OQ-009 | — | Persisted/derived coverage tiers and unknown-data search semantics | DECIDED | Before query engine implementation | `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` (D1-D10, accepted 2026-08-28/29) + `src/hullq/search/` (SLICE-0033) + tests |
| OQ-010 | — | Python/data-pipeline runtime, dependency and tooling baseline | DECIDED | Before first pipeline code | `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md` + ADR-0009; repository bootstrap follows as Stage 0.3 |
| OQ-011 | — | Application/backend architecture and whether Strapi remains appropriate | DECIDED | Before application backend implementation | ADR-0010 + later accepted rebaseline: CPython 3.14/FastAPI modular monolith; Strapi not selected |
| OQ-012 | — | Database/search persistence technology and indexing strategy | DECIDED | Before production persistence/query implementation | PostgreSQL 18; production target DigitalOcean Managed PostgreSQL 18 FRA1; no dedicated search engine until measured need |
| OQ-013 | — | Market-source access matrix: official API/feed/partner/deep-link/caching/display rights per target platform | RESEARCHING | Before any production external adapter | source-access register + per-source decision |
| OQ-014 | — | Authentication/account architecture and privacy/security baseline | DECIDED | Before authenticated account/broker capability implementation; production controls also gate real external broker data/use | `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§10–11, `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`, and `docs/governance/PRODUCTION_READINESS_GATE.md`: Auth0 Public Cloud EU is authentication-only; HullQ owns Account/Organization/Membership/role/authorization truth in PostgreSQL; privileged broker publishing requires MFA; implementation remains capability-scoped |
| OQ-015 | — | Stable public API boundary and API-description format/version | DEFERRED | Before exposing public HTTP API | API ADR + OpenAPI contract |
| OQ-016 | — | Final subscription pricing, entitlement limits and alert-frequency differentiation | DEFERRED | Before paid subscription launch | accepted subscription/pricing spec + experiments |
| OQ-017 | — | Historical market-observation / price-intelligence persistence, lifecycle semantics and source-retention permissions | DEFERRED | Before storing longitudinal listing-price history or shipping Pro price intelligence | market-history/price-intelligence spec + source-rights constraints + tests |
| OQ-018 | — | Broad/indexable public search/SEO surface details: indexable page taxonomy, broad URL grammar, faceted-navigation crawl/index policy, sitemap/hreflang strategy and broad structured-data mapping | OPEN | Before broad/indexable organic-discovery implementation; does not block already accepted bounded `noindex` listing/Search surfaces | accepted Search/SEO surface spec + tests/SEO release checks; bounded page classes remain governed by their accepted slice/page-class contracts |
| OQ-019 | — | Whether/when the accepted distributed contracts need a consolidated persistence-neutral logical entity/relationship model before production persistence work | DEFERRED | Re-evaluate before physical persistence schema work if implementation evidence shows value | logical model/ADR only if needed; not a pre-domain-code gate |

## Current execution interpretation

Execution order is controlled by the higher-precedence post-SLICE-0039 product/architecture records, especially:

- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`;
- `docs/governance/POST_0051_TRIGGER_GATES.md`;
- `docs/governance/PRODUCTION_READINESS_GATE.md`;
- current `docs/PROJECT_STATE.md`.

This register records unresolved decisions; it is not a second competing roadmap. Historical immediate-order prose that predates the native-listing pivot is not controlling where it conflicts with those later accepted records.

## Current dispositions that must not be reopened accidentally

### OQ-014 — authentication/account architecture

The 2026-09-02 owner-accepted rebaseline superseded the earlier ADR-0010-era statement that auth provider/session architecture was wholly unselected.

Accepted architecture now includes:

```text
Auth0 Public Cloud / EU tenant
= authentication-only provider

HullQ PostgreSQL/domain state
= Account IDs, Organizations, Memberships, roles,
  listing ownership, verification and authorization
```

Publishing-capable broker and Organization Owner/Admin accounts require MFA, preferably passkeys/WebAuthn where supported. High-risk actions require fresh/step-up authentication when those actions exist.

This decision being accepted does **not** mean the authenticated broker workspace, persisted actor directory, sessions/UI integration or all privacy/operations work is already implemented. Those are `DECIDED_NOT_YET_IMPLEMENTED` obligations to be owned by bounded future capabilities or the Production Readiness Gate, not reasons to reopen OQ-014 as a provider-selection question.

### OQ-018 — broad/indexable Search/SEO surface

OQ-018 remains genuinely open only for the broad/indexable organic-discovery system. It does not retroactively invalidate the accepted bounded public surfaces already implemented by SLICE-0049/0051:

```text
/listings/{NativeListingId}
/{locale}/search
```

Those page classes are deliberately `noindex` and have their own accepted URL/canonicalization semantics.

Before broad/indexable organic discovery is implemented, OQ-018 must still resolve the remaining taxonomy/crawl/index/sitemap/hreflang/structured-data decisions. See `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`.
