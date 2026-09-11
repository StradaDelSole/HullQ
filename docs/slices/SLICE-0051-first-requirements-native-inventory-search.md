# SLICE-0051 — First production Requirements → Native Inventory Search vertical

**ID:** SLICE-0051  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Native marketplace / buyer search  
**Base main:** `ff2566a84e00b69e607757292c813d0132811d8c`  
**Depends on:** accepted SLICE-0038, SLICE-0049 and SLICE-0050 behavior; accepted 2026-09-11 marketplace-search resolution/evidence-set decisions; bounded OQ-018 Search decisions; `docs/SLICE_0051_CAPABILITY_SELECTION_2026-09-11.md`; `docs/SLICE_0051_DRAFT_MAX_VERTICAL_DECISION_2026-09-11.md`  
**Blocks:** later Saved Search / monitoring / alert work that needs a production native-inventory technical Search surface  

## Objective

Deliver exactly one buyer-visible production capability:

> A buyer can express one hard maximum-draft requirement through the public locale-prefixed Search surface, and HullQ deterministically carries that requirement through BoatDesign/configuration eligibility and ACTIVE native professional inventory to concrete PhysicalBoat draft truth, returning only confirmed concrete-boat fits in the primary result set while keeping insufficient/conflicting evidence explicit and linking each confirmed result to its existing public NativeListing page.

The only public buyer requirement in this slice is:

```text
draft_max=<exact decimal metres>
```

Canonical example:

```text
/de/search?draft_max=1.6
```

The bounded vertical is:

```text
buyer draft_max
→ deterministic BoatDesign/configuration Search
→ potentially compatible designs/configurations
→ durable design identity admission to ACTIVE native inventory
→ NativeListing → MarketEpisode → PhysicalBoat
→ publishing Organization's current physical_boat.draft claim
→ same-PhysicalBoat current-observation contradiction guard
→ concrete listing qualification
→ CONFIRMED_MATCH primary results
   + separate INSUFFICIENT_DATA explanation where applicable
→ /listings/{NativeListingId}
```

This slice MUST NOT turn a matching design/configuration into a confirmed concrete-yacht match without admissible concrete PhysicalBoat evidence.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
Exactly one buyer-visible capability is delivered: hard `draft_max` Requirements → ACTIVE Native Inventory Search. No second public criterion, Saved Search, ranking product or broker workspace is included.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can open the locale-prefixed Search route against real persisted PostgreSQL-backed native inventory, enter/encode a maximum draft, inspect confirmed versus insufficient-data behavior, follow a result to the existing public listing page, and run a retained end-to-end proof.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is the selected post-SLICE-0050 continuation of the accepted buyer loop and implements the minimum production native-inventory bridge inside the buyer-facing vertical rather than inserting a separate foundation-only slice. It preserves the accepted strict-truth, broker-first supply, Astro/FastAPI/PostgreSQL and no-second-search-backend boundaries.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical `origin/main` at readiness base `ff2566a84e00b69e607757292c813d0132811d8c` was reconciled against accepted Search, marketplace-fact, architecture, workflow, OQ-018 and slice records plus the existing production Search kernel, native-listing/public-read path, PhysicalBoat claim model/persistence and retained SLICE-0038 pilot implementation.

## Decision / implementation reconciliation

**Accepted records checked:** `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`; `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`; `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md`; `docs/MARKETPLACE_SEARCH_CLAIM_RESOLUTION_2026-09-11.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`; `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`; `docs/SLICE_0051_CAPABILITY_SELECTION_2026-09-11.md`; `docs/SLICE_0051_DRAFT_MAX_VERTICAL_DECISION_2026-09-11.md`; the bounded OQ-018 Search decision records dated 2026-09-11; and accepted SLICE-0038, SLICE-0049 and SLICE-0050 closure records.  
**Production implementation checked:** `src/hullq/search/types.py`, `criteria.py`, `query.py`, `query_mixed.py`, `engine.py`, `values.py`, `configuration.py`, `configuration_engine.py`; `scripts/search_oceanis_30_1_sales.py` and `tests/unit/test_search_oceanis_30_1_sales.py`; `src/hullq/domain/physical_boat_claims.py`; `src/hullq/persistence/physical_boat_claims.py`; `alembic/versions/9c2e6b4a1d80_physical_boat_claim_facts.py`; `src/hullq/application/public_listing_read.py`; `src/hullq/api/app.py`; the existing Astro public-listing surface under `web/src/pages/listings`; and the corresponding accepted unit/persistence/API/web tests.  
**Already implemented / not re-decided:** deterministic three-valued Search semantics and configuration-aware design evaluation; `CONFIRMED_MATCH`/`CONFIRMED_NON_MATCH`/`INSUFFICIENT_DATA`; hard-Required UNKNOWN behavior; stable marketplace identities and ACTIVE NativeListing public lifecycle; durable NativeListing→MarketEpisode→PhysicalBoat linkage; exact Decimal `physical_boat.draft` broker claims with omitted-vs-UNKNOWN distinction; no BoatDesign fallback into PhysicalBoat truth; and the accepted public Search route/canonicalization/locale/rendering/noindex rules.  
**Exact remaining gap:** one production bridge for exactly `draft_max` from the accepted public Search facade through existing deterministic design/configuration Search to ACTIVE native listings, then through current publisher PhysicalBoat draft evidence plus the accepted same-PhysicalBoat contradiction guard, exact listing qualification, buyer-visible SSR results and existing public-listing next action.  
**Accepted-but-unimplemented obligations:** SLICE-0051 owns the accepted Option-B same-PhysicalBoat contradiction guard and Option-C resolution-vs-verification behavior for `physical_boat.draft`; the bounded OQ-018 public Search facade/HTTP/canonical/noindex/SSR behavior; and the smallest exact-Decimal adapter/refactor needed to prevent binary-float drift in this vertical. Broader criteria, a global fact resolver, independent verification, indexable SEO landing pages, Saved Search/alerts and generic all-field native search remain explicitly deferred.  
**Material classifications:** `DECIDED_AND_IMPLEMENTED`; `DECIDED_NOT_YET_IMPLEMENTED`; `EXPLICITLY_DEFERRED`.  

There is no material product/domain/Search-semantic question left for the implementation agent to decide inside this slice. If implementation reveals an actual contradiction among controlling artifacts, stop rather than inventing new semantics.

## Why this slice exists

SLICE-0049 made one real NativeListing production-public. SLICE-0050 then made the concrete yacht materially more truthful by adding seven durable broker-declared PhysicalBoat claim fields, including exact-Decimal draft, without allowing BoatDesign fallback.

HullQ still cannot perform its central marketplace task in production:

```text
I require a yacht with draft <= X
→ show me the actual native boats that are confirmed to satisfy it
```

The accepted SLICE-0038 pilot already proved why a generic design match is insufficient: a BoatDesign may offer a shallow-draft configuration while the particular yacht for sale may be the deeper variant, may have unknown draft, or may carry conflicting concrete evidence.

SLICE-0051 therefore closes the first production buyer-facing loop across both truth levels:

```text
DESIGN / CONFIGURATION POSSIBILITY
!=
CONCRETE PHYSICAL BOAT CONFIRMATION
```

This is intentionally narrower than a broad marketplace filter system. The goal is to prove a differentiated HullQ buyer experience on real native inventory with one technically important requirement before multiplying public criteria.

## Controlling artifacts

Implementation MUST preserve, and must not silently reinterpret, at least:

- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`;
- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`;
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`;
- `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md`;
- `docs/MARKETPLACE_SEARCH_CLAIM_RESOLUTION_2026-09-11.md`;
- `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`;
- `docs/PRODUCT_UX_PRINCIPLES.md`;
- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`;
- `docs/engineering/AI_SLICE_WORKFLOW.md`;
- `docs/SLICE_0051_CAPABILITY_SELECTION_2026-09-11.md`;
- `docs/SLICE_0051_DRAFT_MAX_VERTICAL_DECISION_2026-09-11.md`;
- accepted SLICE-0038, SLICE-0049 and SLICE-0050 contracts/closures;
- the bounded OQ-018 decision records listed below.

### Bounded OQ-018 decisions controlling this slice

- `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_QUERY_PARAMETER_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_PARAMETER_ORDERING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NUMERIC_CANONICALIZATION_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_SPARSE_CANONICAL_STATE_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_UNKNOWN_PARAMETER_POLICY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_DUPLICATE_SINGLE_VALUE_POLICY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_INVALID_REQUEST_RECOVERY_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NONCANONICAL_REDIRECT_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_NONSEMANTIC_ALLOWLIST_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_INDEXABILITY_AND_SEO_READINESS_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_BARE_AND_UNSUPPORTED_LOCALE_ROUTING_DECISION_2026-09-11.md`;
- `docs/OQ_018_SEARCH_RENDERING_BOUNDARY_DECISION_2026-09-11.md`.

Broader future OQ-018 work such as deliberately indexable SEO landing-page taxonomy, sitemap expansion and structured-data strategy remains outside SLICE-0051 except for preserving the accepted future seam.

## Readiness-derived implementation rules

The final OQ-018 rendering record states that the exact smallest 0051 field/query vertical was the only remaining material Owner decision. That decision is now durably resolved by `docs/SLICE_0051_DRAFT_MAX_VERTICAL_DECISION_2026-09-11.md`.

The following bounded details are therefore fixed here as conservative implementation derivations, not new product semantics and not delegated to the implementation agent.

### Base Search state

A canonical locale-prefixed base route with no active buyer criterion, for example:

```text
/de/search
```

returns `200`, remains `noindex`, and server-renders the localized Search form/instructions. It MUST NOT execute design/inventory result evaluation and MUST NOT present an unconstrained all-inventory result set/count in SLICE-0051.

Reason: the selected capability is one explicit hard `draft_max` requirement and the existing Search query contract requires a non-empty criterion set. Treating absence of a buyer requirement as an implicit all-inventory query would invent additional Search behavior not selected for this slice.

This does not prohibit a future separately accepted browse/all-inventory capability.

### Conservative `draft_max` lexical envelope

For SLICE-0051 the accepted inbound technical value grammar is deliberately narrow:

```regex
^[0-9]+(?:\.[0-9]+)?$
```

Then parse directly to exact Decimal semantics and require the value to be finite and `> 0`.

This accepts already-recorded non-canonical examples such as `01.60`, `1.600`, `10.0` and `10.000`, which then canonicalize without rounding.

The first vertical rejects rather than guesses broader spellings, including:

- leading `+` or `-` signs;
- comma decimal separators in URLs;
- exponent/scientific notation;
- grouping separators;
- leading/trailing whitespace;
- a terminal decimal dot such as `1.`;
- empty values;
- non-finite spellings.

Localized UI may still display locale-appropriate decimal formatting, but it must submit/navigate through the accepted language-neutral exact technical representation.

Broader numeric input syntax may be introduced later only through an explicit compatible contract; it is not silently generalized here.

## In scope

### A. Exactly one public buyer requirement

Support only:

```text
draft_max=<positive finite exact decimal metres>
```

Semantics:

```text
Requirement strength: REQUIRED
Comparison: concrete draft <= draft_max
Boundary: inclusive
Tolerance: none
Technical unit: metres
```

No implicit epsilon, fuzzy comparison, locale-dependent numeric meaning or hidden unit conversion is permitted.

### B. Exact decimal boundary

The public URL value MUST be parsed into an exact decimal semantic value without an intermediate binary-float conversion that can change accepted value/comparison semantics.

For concrete PhysicalBoat qualification, comparison MUST be exact Decimal-to-Decimal or an equivalently lossless exact representation.

The historical Search v0.1/v0.2 JSON parsers' `float` conversion is accepted legacy behavior but is not permission to weaken this vertical. If the existing design/configuration Search path cannot be reused without precision drift, implement the smallest bounded adapter/refactor necessary and cover it with regression tests. Do not use this slice to modernize unrelated Search criteria.

Canonical numeric examples:

```text
1.600  → 1.6
01.60  → 1.6
10.0   → 10
10.000 → 10
```

Canonical values use ASCII `.`, no grouping, no exponent notation, no unnecessary leading/trailing zeros and no semantic rounding.

### C. Public Search URL / HTTP contract

Public Search routes:

```text
/en/search
/de/search
/fr/search
/pt/search
/es/search
```

Locale affects presentation only. `draft_max` and its meaning remain language-neutral.

Canonical state is sparse:

```text
/de/search                  # no active draft requirement
/de/search?draft_max=1.6    # canonical active requirement
```

Required externally observable cases:

```text
/search
→ 308 /en/search

/search?draft_max=1.6
→ 308 /en/search?draft_max=1.6

/de/search?draft_max=1.600
→ 308 /de/search?draft_max=1.6

/de/search?draft_max=1.6&draft_max=1.60
→ 308 /de/search?draft_max=1.6

/de/search?draft_max=1.6&draft_max=1.7
→ 400, no Search evaluation

/de/search?draft_max=
→ 400, no Search evaluation

/de/search?draft_max=1e0
→ 400, no Search evaluation in the bounded 0051 lexical envelope

/de/search?foo=bar
→ 400, no Search evaluation

/de/search?utm_source=x
→ 400, no Search evaluation because the accepted initial non-semantic allowlist is empty

/it/search?draft_max=1.6
→ 404, no Search evaluation
```

Invalid/ambiguous state receives a localized buyer-friendly 400 recovery response and MUST NOT be partially evaluated. Valid non-canonical state uses one `308 Permanent Redirect` to its exact canonical URL where the accepted rules permit direct composition.

Bare `/search` remains a deterministic English entry point and MUST NOT use `Accept-Language`, cookies, session, geography or account state to choose locale. Invalid state on the bare route does not gain validity through locale routing.

### D. Deterministic design/configuration evaluation

Use the accepted Search semantics/configuration behavior to determine BoatDesign/configuration candidates that can satisfy `draft <= draft_max`.

Hard boundaries:

- no second Search semantic model;
- no opaque quality/confidence score;
- no hidden source-trust ranking;
- no fuzzy tolerance;
- no criterion beyond `draft_max`;
- design/configuration evaluation alone never confirms a concrete listed yacht.

The existing Search kernel may be adapted only as needed for exact semantics in this bounded vertical.

### E. Production native-inventory bridge

Bridge eligible design/configuration candidates into real persisted inventory through existing durable identities:

```text
BoatDesignRef
↔ PhysicalBoat optional BoatDesignRef
← MarketEpisode
← NativeListing
```

Only complete public `ACTIVE` NativeListings admitted under accepted SLICE-0049 lifecycle semantics may become buyer-visible Search results.

A listing whose concrete PhysicalBoat cannot be durably associated with the applicable design identity MUST NOT become a confirmed match through fuzzy inference. `DRAFT`, `WITHDRAWN`, incomplete, missing or otherwise non-public listings MUST NOT leak into public Search results.

### F. Concrete PhysicalBoat draft candidate

For each eligible listing, the candidate concrete value is only the publishing Organization's current `physical_boat.draft` claim for that same durable PhysicalBoat.

```text
publisher current VALUE_ASSERTION(Decimal)
→ candidate concrete value

publisher draft omitted
→ insufficient concrete evidence

publisher current UNKNOWN
→ insufficient concrete evidence
```

Another Organization's current claim MUST NOT silently replace the publisher's claim. BoatDesign/configuration draft MUST NOT backfill omitted/UNKNOWN concrete PhysicalBoat draft.

### G. Same-PhysicalBoat contradiction guard

Implement the accepted bounded Option-B guard for exactly `physical_boat.draft`:

```text
publisher current concrete draft
+ all relevant current admissible observations
  for physical_boat.draft
  on the same PhysicalBoatId
→ conflict check
```

Rules:

- semantically equivalent current concrete values do not conflict;
- contradictory current concrete value → `CONFLICT`;
- omitted/UNKNOWN observations do not manufacture a contradiction;
- superseded revisions from the same authority are history, not current contradictory observations;
- another Organization may block a confirmed match through conflict but may not overwrite the publisher's displayed claim;
- no latest-source, majority, source-priority, listing-owner-wins or hidden-confidence winner;
- this is a listing-evaluation guard, not a global PhysicalBoat fact resolver.

### H. Listing-level qualification

```text
resolved publisher concrete draft <= draft_max
+ no contradictory current admissible observation
→ CONFIRMED_MATCH

resolved publisher concrete draft > draft_max
+ no contradictory current admissible observation
→ CONFIRMED_NON_MATCH

publisher draft omitted
or publisher draft UNKNOWN
or evidence UNRESOLVED
or evidence CONFLICT
→ INSUFFICIENT_DATA
```

Only `CONFIRMED_MATCH` belongs to the primary result set/count.

`INSUFFICIENT_DATA` MUST be mechanically and visually separate from confirmed matches. It may appear as a secondary buyer-helpful section/count but MUST NOT be included in the confirmed count or presented as a match.

`CONFIRMED_NON_MATCH` need not be shown as a buyer result card but its deterministic classification must be tested.

### I. Buyer-facing explanation and next action

The SSR result must let a buyer understand, without database vocabulary:

```text
what requirement was applied
why a confirmed boat qualifies
what concrete draft HullQ used
that the value is broker-declared unless separately verified
whether evidence is missing/conflicting
why insufficient evidence is not called a match
what action is available next
```

Confirmed results link to the existing stable public identity:

```text
/listings/{NativeListingId}
```

Do not invent a second listing URL grammar or copy Search parameters onto the listing URL as if they altered listing identity.

### J. Rendering and application boundary

Astro owns public web/presentation and server-renders meaningful Search/result HTML.

FastAPI remains the sole application/domain/Search semantic boundary. It owns accepted parameter semantics, exact Decimal parsing/canonical state, invalid/duplicate handling, claim resolution, inventory qualification and result classification.

Astro MUST NOT:

- access PostgreSQL directly for Search truth;
- reimplement Python Search/domain rules;
- independently resolve claims;
- independently classify results.

React, if used at all, is bounded progressive enhancement only. Direct canonical Search requests must return meaningful initial HTML without requiring a browser-side second semantic evaluation.

### K. Language behavior

Public presentation supports the five mandatory languages:

```text
EN / DE / FR / PT / ES
```

Technical parameter names, IDs, Decimal meaning, provenance and Search semantics remain language-neutral. Switching locale preserves the active canonical technical Search state.

### L. SEO behavior for this slice

All locale-prefixed Search surfaces are public/usable but `noindex`.

A canonical 200 Search page MUST identify itself through the exact accepted canonical Search URL state rather than canonicalizing a constrained Search to the unconstrained base route. `noindex` must be mechanically testable. No Search-result sitemap expansion is authorized.

No mandatory `hreflang` expansion is introduced for these noindex Search pages in SLICE-0051. If locale-alternate metadata is emitted, it MUST map only semantically equivalent canonical Search states across `{en,de,fr,pt,es}` and MUST NOT invent additional Search semantics.

Implementation must preserve the later SEO seam: deterministic locale routes, canonical URL ownership, SSR/crawlable architecture, explicit route-class indexability and separation between buyer Search URLs and future deliberate indexable landing pages.

## Explicitly out of scope

- `draft_min`;
- `loa_min` / `loa_max`;
- build-year criteria;
- keel/rudder criteria;
- any other public SLICE-0050 claim criterion;
- generic all-field native-inventory Search infrastructure;
- OR/NOT expansion or new ranking semantics;
- Saved Search, monitoring or alerts;
- price-history/price-change intelligence;
- recommendation/personalization scoring;
- global cross-Organization PhysicalBoat fact resolution;
- independent survey/document verification;
- Auth0 broker workspace/forms;
- media upload/storage;
- new listing lifecycle/freshness/staleness semantics;
- browse/all-inventory result behavior for an unconstrained base Search route;
- indexable SEO landing pages, Search sitemaps or broad structured-data expansion;
- marketing/tracking query-parameter acceptance;
- a dedicated external search engine or second backend;
- broad refactoring of historical Search numeric contracts unrelated to exact correctness of this vertical.

## Required behavior

### 1. Request-state separation

The application boundary must distinguish:

- canonical base Search with no active criterion → 200 SSR form/instructions, no Search result evaluation;
- one valid active `draft_max` criterion → evaluate the bounded vertical;
- valid but non-canonical syntax → 308 canonical redirect;
- invalid/ambiguous input → 400 localized recovery, no evaluation;
- unsupported locale → 404, no evaluation.

### 2. Truth-preserving candidate funnel

Make these boundaries explicit in code/tests rather than collapsing semantics into one opaque SQL predicate:

```text
requirement parse/canonicalize
→ design/configuration eligibility
→ durable native-inventory identity admission
→ current publisher concrete claim
→ current same-PhysicalBoat contradiction guard
→ listing truth classification
```

An efficient query plan is allowed, but semantic stages and tests must remain reviewable.

### 3. No false confirmation from missing concrete truth

At minimum prove:

- shallow-compatible design + publisher concrete shallow draft → confirmed match;
- shallow-compatible design + publisher concrete deeper draft → confirmed non-match;
- shallow-compatible design + publisher draft omitted → insufficient data;
- shallow-compatible design + publisher draft UNKNOWN → insufficient data;
- shallow-compatible design + contradictory current same-PhysicalBoat draft → conflict/insufficient data;
- shallow-compatible design + only another Organization's shallow claim and no publisher draft → insufficient data, not substitution;
- design/configuration match alone with no concrete draft → never confirmed;
- concrete shallow draft without durable applicable design identity → never confirmed through fuzzy inference;
- non-ACTIVE listing → never public result.

### 4. Provenance and verification stay separate

A confirmed match based on broker-declared draft may be `RESOLVED` for this evaluation context but remains broker-declared and not independently verified unless another accepted capability established verification.

### 5. Stable public next action

Confirmed rows/cards link only to `/listings/{NativeListingId}` and preserve existing public-listing route semantics.

## Deliverables

- exact-Decimal public Search request/canonicalization adapter for `draft_max`;
- production application/domain service for this single Requirements → Native Inventory Search vertical;
- smallest persistence/query support needed to enumerate ACTIVE native listings and current same-PhysicalBoat draft observations without a generic fact resolver;
- FastAPI Search endpoint on the existing application boundary;
- Astro SSR locale-prefixed Search surface for EN/DE/FR/PT/ES;
- buyer-visible confirmed-match and insufficient-data presentation with existing listing links;
- localized 400 recovery plus required 308/404 behavior;
- tests for lexical grammar, canonicalization, Decimal exactness, design/config gating, ACTIVE inventory admission, claim resolution, contradiction guard, API and SSR behavior;
- retained real PostgreSQL/API/web proof demonstrating the first production native-inventory Search vertical end to end;
- normal slice handoff updates only; no acceptance closure or next-slice work.

## Acceptance criteria

- [ ] `/en/search`, `/de/search`, `/fr/search`, `/pt/search`, `/es/search` exist as SSR Search surfaces with language-neutral technical semantics.
- [ ] A locale-prefixed base Search route returns 200/noindex localized form/instructions and executes no result evaluation until `draft_max` is active.
- [ ] `/search` returns the accepted deterministic 308 to `/en/search` while preserving supported valid Search state; unsupported locale-prefixed Search returns real 404 with no evaluation.
- [ ] `draft_max` accepts only the bounded ASCII decimal lexical envelope, parses directly to exact Decimal semantics, requires `> 0`, and rejects broader ambiguous spellings fail-closed.
- [ ] Canonical numeric serialization is exact/deterministic; accepted non-canonical equivalent decimals redirect 308 to one canonical identity.
- [ ] Invalid/ambiguous/unknown/disallowed query parameters return 400 with localized correction guidance and zero Search evaluation.
- [ ] Equal duplicate singleton `draft_max` values normalize/collapse by canonical redirect; conflicting duplicates fail closed with 400.
- [ ] URL parsing and concrete PhysicalBoat draft comparison introduce no binary-float precision loss or semantic rounding.
- [ ] Existing deterministic configuration-aware Search behavior is reused/preserved; no second Search semantic engine is introduced.
- [ ] Only complete public `ACTIVE` NativeListings from the accepted durable identity chain are eligible for public result exposure.
- [ ] Design/configuration compatibility alone never creates a confirmed concrete-yacht match.
- [ ] The publishing Organization's current `physical_boat.draft` claim is the listing candidate; no other Organization silently substitutes its value.
- [ ] Same-PhysicalBoat contradictory current concrete draft evidence produces conflict and blocks `CONFIRMED_MATCH`; equivalent corroboration does not conflict; UNKNOWN/omission does not manufacture conflict.
- [ ] Omitted, UNKNOWN, UNRESOLVED and CONFLICT concrete evidence produce `INSUFFICIENT_DATA`, never a hard match.
- [ ] Concrete draft `<= draft_max` resolves to `CONFIRMED_MATCH`; concrete draft `> draft_max` resolves to `CONFIRMED_NON_MATCH`; comparison is inclusive with no hidden tolerance.
- [ ] Only `CONFIRMED_MATCH` is included in the primary result set/count; insufficient data is mechanically and visually distinct.
- [ ] Buyer-visible results explain applied requirement and concrete evidence status clearly enough to distinguish broker-declared confirmation from missing/conflicting evidence.
- [ ] Confirmed links use only `/listings/{NativeListingId}`.
- [ ] Astro SSR returns meaningful Search/result HTML; FastAPI remains the sole Search/application/domain semantic boundary; web performs no direct PostgreSQL access or semantic reimplementation.
- [ ] Every Search surface is `noindex`; canonical constrained state is not collapsed to the base route; no Search-result sitemap/indexable-facet expansion is introduced.
- [ ] Existing SLICE-0038/0049/0050 truth, lifecycle, public-listing and claim regressions remain green.
- [ ] PostgreSQL integration coverage proves ACTIVE filtering, current-head observation behavior and contradiction handling on real PostgreSQL 18.
- [ ] A retained owner-visible proof runs the real PostgreSQL → FastAPI → Astro path and demonstrates at least one confirmed match plus insufficient/conflict behavior without fixture-only semantic shortcuts.
- [ ] `python scripts/validate_repository.py` passes on the final implementation head.
- [ ] Required Python lint/type/test gates and web build/test gates pass locally on the implementation head.
- [ ] Required remote CI and manufacturer-artifact reproducibility gates are observed green on the exact implementation head before acceptance.

An implementation agent MUST NOT check a criterion it has not actually verified. Remote/external criteria remain unchecked until their exact-head results have been observed.

## Expected touch points

Expected areas include, but are not permission for unrelated changes:

```text
src/hullq/search/
src/hullq/application/
src/hullq/persistence/
src/hullq/api/app.py
web/src/pages/
web/src/lib/
tests/unit/
tests/persistence/
tests/integration/ or existing API/web test locations
scripts/                    # bounded retained proof only
docs/slices/SLICE-0051-first-requirements-native-inventory-search.md
```

A new migration is NOT expected merely for this read/search vertical. If a schema change is genuinely required for correctness rather than convenience/performance, stop and report the concrete need before inventing durable semantics.

## Validation

Use repository-defined canonical environments/commands. At minimum report the applicable equivalents of:

```bash
python scripts/validate_repository.py
ruff check .
mypy src
pytest
npm --prefix web test
npm --prefix web run build
```

Run focused 0051 unit/persistence/API/web suites and the retained owner-visible PostgreSQL → FastAPI → Astro proof explicitly in addition to broad regression tests. Do not invent substitute CI commands when repository workflows already define canonical gates; remote required checks remain external evidence.

## Stop conditions

Stop and report instead of inventing a solution when:

- a controlling accepted decision is absent on the actual slice base or materially contradicts another controlling artifact;
- implementation would require a second Search semantic model or second business-logic backend;
- exact `draft_max` semantics cannot be preserved without a broader Search-contract change outside this bounded vertical;
- the contradiction guard would require a global fact-resolution policy beyond accepted Option B;
- a required durable identity link would need fuzzy inference or new identity semantics;
- implementation would have to weaken `UNKNOWN`, `UNRESOLVED`, `CONFLICT`, provenance or verification semantics for friendlier results;
- implementation requires accepting another public Search criterion;
- a new persistent schema is required for product semantics not already accepted;
- source-rights, privacy, authorization or accepted broker-first supply policy would be violated;
- implementation requires scope outside this slice.

## Status handoff rule

The implementation agent may set this primary slice document to `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark it `DONE`.

Successful handoff normally sets:

```text
**Status:** REVIEW
**Status set by this handoff:** `REVIEW`
```

`DONE` requires verified acceptance criteria, exact-head external gates, independent review and explicit Project Owner acceptance under the canonical HullQ workflow.

## Required completion report

Use this structure exactly at the end of the assigned slice.

### Slice

- Slice ID: `SLICE-0051`
- Recommended slice state: `REVIEW` | `BLOCKED`
- Scope completed: `YES` | `NO`
- Exact final branch HEAD SHA:

### Product execution checks

- ONE-CAPABILITY CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`
- VISIBLE-RESULT CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`
- PRODUCT EXECUTION PLAN ALIGNMENT: `PASS` | `FAIL` | `NOT APPLICABLE`
- REPOSITORY RECONCILIATION CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`

### Changes

- Changed files:
- Requirements implemented or researched:
- Tests/fixtures added or updated:

### Validation

- Local validation: `PASS` | `FAIL` | `PARTIAL` | `NOT APPLICABLE`
- Commands run:
- Results:

### External verification

- Remote CI: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`
- Other external gates: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`

### Findings

- Unresolved findings:
- Spec/ADR ambiguities:
- Scope deviations:

### Follow-up

- Recommended next action:

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.
