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
| OQ-008 | D-008 | Final frontend technology | OPEN | Before frontend implementation | ADR + repo toolchain |
| OQ-009 | — | Persisted/derived coverage tiers and unknown-data search semantics | OPEN | Before query engine implementation | search semantics spec + tests |
| OQ-010 | — | Python/data-pipeline runtime, dependency and tooling baseline | DECIDED | Before first pipeline code | `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md` + ADR-0009; repository bootstrap follows as Stage 0.3 |
| OQ-011 | — | Application/backend architecture and whether Strapi remains appropriate | OPEN | Before application backend implementation | ADR |
| OQ-012 | — | Database/search persistence technology and indexing strategy | OPEN | Before production persistence/query implementation | ADR + migration contract, informed by accepted contracts, source/benchmark evidence and measured access patterns |
| OQ-013 | — | Market-source access matrix: official API/feed/partner/deep-link/caching/display rights per target platform | RESEARCHING | Before any production adapter | source-access register + per-source decision |
| OQ-014 | — | Authentication/account implementation and privacy baseline | DEFERRED | Before accounts | security/privacy spec + ADR if external provider chosen |
| OQ-015 | — | Stable public API boundary and API-description format/version | DEFERRED | Before exposing public HTTP API | API ADR + OpenAPI contract |
| OQ-016 | — | Final subscription pricing, entitlement limits and alert-frequency differentiation | DEFERRED | Before paid subscription launch | accepted subscription/pricing spec + experiments |
| OQ-017 | — | Historical market-observation / price-intelligence persistence, lifecycle semantics and source-retention permissions | DEFERRED | Before storing longitudinal listing-price history or shipping Pro price intelligence | market-history/price-intelligence spec + source-rights constraints + tests |
| OQ-018 | — | Public search/SEO surface details: indexable page taxonomy, URL grammar, faceted-navigation crawl/index policy, rendering strategy, canonicalization/sitemaps and structured-data mapping | OPEN | Before public frontend/search-surface implementation | accepted Search/SEO surface spec + tests/SEO release checks; framework-specific consequences may be captured in frontend ADR |
| OQ-019 | — | Whether/when the accepted distributed contracts need a consolidated persistence-neutral logical entity/relationship model before production persistence work | DEFERRED | Re-evaluate before OQ-012 / production persistence if implementation evidence shows value | logical model/ADR only if needed; not a pre-domain-code gate |

## Immediate execution order

The next work SHOULD proceed in this order:

1. close repository bootstrap via `SLICE-0001` (`uv.lock` + first green locked CI);
2. execute `SLICE-0002` to research the **actual independent sailboat-design data sources** and manually study a representative 20–30-design seed sample;
3. refine Stage-2 contract/runtime and normalization slices from the real source evidence;
4. implement and then measure the 50–100-design benchmark;
5. resolve `OQ-009` unknown-data search semantics before query-engine code.

The design-data source research in SLICE-0002 is intentionally not represented as a single OQ: it is evidence-gathering work across multiple candidate sources governed by the already accepted OQ-007 source-rights model. Any genuine unresolved semantic/legal/architecture question discovered by that research must become an explicit OQ rather than being solved silently.

`OQ-019` is no longer a pre-code gate. The production persistence/search decision remains OQ-012 and should be informed by actual source/benchmark evidence and measured access patterns.

`OQ-018` must be resolved before the public frontend/search surface is implemented; it does not block the research pipeline.

`OQ-013` market-access research runs in parallel because it is commercially important but does not block design-data construction.
