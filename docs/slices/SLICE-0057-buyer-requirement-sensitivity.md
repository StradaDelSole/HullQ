# SLICE-0057 — Buyer Requirement Sensitivity

**ID:** SLICE-0057  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Buyer Decision Tools — one-change factual Direct Search sensitivity  
**Depends on:** SLICE-0056 owner-accepted / acceptance-closed; post-SLICE-0056 workflow reassessment owner-accepted / `PASS`; SLICE-0055 typed Search evidence foundation  
**Blocks:** later broader Buyer Requirements / explainability / sensitivity capabilities only; no later slice is automatically authorized

## Objective

Deliver exactly one public buyer capability:

> From one valid current HullQ Direct Search, the buyer explicitly chooses exactly one currently active hard criterion and supplies one replacement value; HullQ evaluates the current and alternative requirements through the same accepted Search truth and shows the factual confirmed-result-set delta, with insufficient data kept separate and an exact canonical link to apply the buyer-selected alternative.

No recommendation, score, automatic relaxation, persistence or new Search criterion is introduced.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: buyer-authored one-criterion sensitivity on the existing Direct Search.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can execute a normal public Search, submit a different value for one active criterion, and visibly inspect the current-vs-alternative confirmed-match delta, insufficient-data counts and the canonical alternative Search link in the built Astro UI.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The capability exposes HullQ's deterministic truth/evidence distinction before signup, directly advances the accepted pre-Gate-1 buyer-value objective, and remains one bounded public interaction. It does not add generic foundations, persistence, external providers or monetization.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Canonical decisions, accepted closures and current Search/API/web implementation were inspected before selection. The capability is accepted-but-unimplemented, not a re-decision of Search semantics.

**TRIGGER GATES CHECK:** PASS  
Workflow reassessment is canonical `PASS`; Production Readiness remains `NOT_TRIGGERED`; this slice adds no Search criterion and no real external production data/pilot/launch.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PRODUCT_EXECUTION_PLAN.md`; `docs/PRODUCT_UX_PRINCIPLES.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/POST_SLICE_0055_REASSESSMENT_2026-09-18.md`; `docs/POST_SLICE_0056_REASSESSMENT_2026-09-18.md`; `docs/POST_SLICE_0056_WORKFLOW_REASSESSMENT_2026-09-18.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; SLICE-0051/0055/0056 contracts and acceptance closures; OQ-018 Search URL/canonicalization decisions; Search/SEO architecture.

**Production implementation checked:** `src/hullq/application/search_read.py`; `src/hullq/application/inventory_search.py`; `src/hullq/application/native_inventory_query.py`; `src/hullq/api/app.py`; `web/src/components/SearchPageBody.astro`; `web/src/lib/searchApi.ts`; `web/src/lib/searchPageData.ts`; `web/src/lib/searchText.ts`; current Search tests and retained PostgreSQL/FastAPI/Astro proof.

**Already implemented / not re-decided:** two accepted hard Direct Search criteria; exact draft Decimal semantics; six-value keel vocabulary; mixed hard AND; Search truth/evidence; result-class separation; current public Search GET request/canonicalization contract; locale set; noindex Search page class; typed 0055 evidence; faithful 0056 browser projection; commercial Search independence.

**Exact remaining gap:** no public buyer surface currently lets the buyer replace one active hard requirement with one explicitly supplied alternative and inspect the factual confirmed-result-set delta through the same Search truth.

**Accepted-but-unimplemented obligations:** owner-accepted one-requirement-at-a-time Requirement Sensitivity / `Why no match?` direction in `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; no recommendation/auto-optimization; anonymous discovery remains available before signup.

**Material classifications:** `DECIDED_AND_IMPLEMENTED` for current Direct Search/truth/canonicalization; `DECIDED_NOT_YET_IMPLEMENTED` for one-change buyer sensitivity; `EXPLICITLY_DEFERRED` for persisted BuyerRequirements, auto-relaxation, multi-criterion optimization, scoring, Shortlist/Compare/Saved Search and broader SEO; no blocking `GENUINELY_OPEN` point; no `CONFLICT_OR_REGRESSION`.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  

Evidence:

- canonical `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` remains `2`;
- SLICE-0057 only re-evaluates already accepted criteria with a buyer-supplied replacement value;
- no new FieldResolution/criterion bridge is introduced;
- no external broker/owner-direct production data is used;
- no production pilot/public launch starts;
- Search eligibility/classification/order remain commercially independent.

## Why this slice exists

SLICE-0055 preserved typed evidence for current multi-criterion Search outcomes. SLICE-0056 completed the browser projection so buyers can actually use `draft_max`, `keel_configuration` or both.

The next highest-leverage accepted buyer gap is not another criterion. It is exposing the factual consequence of a buyer-controlled requirement change.

The accepted Product UX baseline requires a concise `why`/evidence path. The accepted post-0054 buyer direction already defines one-change sensitivity as deterministic decision support, explicitly not recommendation.

This slice therefore turns already retained Search truth into a visible decision-support interaction before signup.

## Controlling artifacts

- Requirement IDs: accepted buyer Requirement Sensitivity direction in `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `REQ-PRIVATE-003` commercial Search independence where Search is affected
- Specification: `specs/BUYER_REQUIREMENT_SENSITIVITY_CONTRACT.v0.1.md`
- Search application contracts: accepted SLICE-0051, SLICE-0055 and SLICE-0056
- Public UX: `docs/PRODUCT_UX_PRINCIPLES.md`
- Search/SEO architecture: `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`
- OQ-018 accepted Search request/canonicalization decisions
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`
- Current owner-direct/private-seller direction: `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`
- Current owner-direct/private-seller requirements: `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`
- Current selection record: `docs/POST_SLICE_0056_REASSESSMENT_2026-09-18.md`
- Workflow reassessment: `docs/POST_SLICE_0056_WORKFLOW_REASSESSMENT_2026-09-18.md`
- Relevant open questions: broader BuyerRequirements identity/schema/lifecycle, Saved Search persistence, Shortlist and multi-change decision tools remain intentionally out of scope and do not block this slice

## In scope

- one buyer-authored replacement value for exactly one currently active `draft_max` or `keel_configuration`;
- current and alternative evaluation through the existing production Search truth;
- same explicit `as_of` and one coherent PostgreSQL snapshot/equivalent for both halves;
- factual set-difference counts based on stable confirmed `NativeListingId` membership;
- separate current/alternative insufficient-data counts;
- exact backend-owned canonical alternative Direct Search path;
- one read-only FastAPI sensitivity endpoint;
- public locale-aware native-POST sensitivity interaction for `en/de/fr/pt/es`;
- factual localized rendering;
- retained real PostgreSQL 18 -> FastAPI -> built Astro SSR proof;
- normal CI wiring for that proof.

## Explicitly out of scope

- a third Search criterion;
- adding/removing criteria through sensitivity;
- automatic suggested values;
- automatic "relax this" behavior;
- multi-criterion changes;
- optimization/recommendation;
- scores, winners, fit percentages, hidden preference weights;
- BuyerRequirements persistence/schema/lifecycle;
- MUST_HAVE/PREFER/DONT_CARE authoring;
- Shortlist/Compare/sharing;
- Saved Search/Monitor/alerts;
- buyer account/signup work;
- buyer-history/telemetry persistence;
- broker Search diagnostics/aggregate intelligence;
- seller/broker monetization effects;
- owner-direct publication/admission;
- Broker Workspace expansion;
- broad/indexable SEO;
- new sitemap/hreflang taxonomy;
- real external production data/pilot/launch.

## Required behavior

### A. Current Search remains authoritative

The ordinary accepted public Search remains:

```text
/{locale}/search
GET /api/search/{locale}
```

SLICE-0057 MUST NOT change its accepted query grammar, 400/308 rules, canonical ordering, result truth, noindex status or locale behavior.

### B. Sensitivity is buyer initiated

The Search page exposes sensitivity only when a valid RESULT state has one or both current active criteria.

The buyer explicitly supplies the proposed replacement.

HullQ does not prefill a "better" alternative, recommend a relaxation or select a criterion to change.

### C. Exactly one active criterion changes

The request names exactly one of:

```text
draft_max
keel_configuration
```

and that criterion must already be active in the current Search.

Every other active criterion remains semantically identical.

Changing an inactive criterion fails closed as an invalid sensitivity request.

### D. Existing parsing/canonicalization is reused

FastAPI/application code reuses the existing exact Decimal parser/canonical formatter and exact accepted keel vocabulary.

Astro/TypeScript transports raw values only.

No second parser or fuzzy mapping is introduced in the web layer.

### E. One Search truth evaluated twice

The application evaluates current and alternative requirements through the same accepted Search evaluation.

No copied criterion truth, bespoke SQL eligibility predicate, TypeScript evaluator or explanation-text parsing.

### F. Coherent comparison snapshot

Both evaluations use:

- the same explicit timezone-aware `as_of`;
- one coherent PostgreSQL transaction/snapshot or an equivalently strong proven boundary.

The sensitivity result must describe one coherent inventory state.

### G. Delta is stable-ID set difference

Compute:

```text
newly confirmed
= alternative confirmed NativeListingIds - current confirmed NativeListingIds

no longer confirmed
= current confirmed NativeListingIds - alternative confirmed NativeListingIds
```

Do not derive those values from total-count subtraction.

A same-total/different-membership case must be covered by tests or retained proof.

### H. UNKNOWN / insufficient remains separate

Current and alternative `INSUFFICIENT_DATA` counts are rendered separately.

They never contribute to confirmed-match or newly-confirmed counts.

No wording converts unknown evidence into negative truth.

### I. Same-value proposal is factual zero delta

If the buyer proposes a value that canonicalizes to the current value, the request succeeds with a deterministic zero result-set delta.

Do not invent an error or advice.

### J. Canonical apply link belongs to FastAPI

The result includes the exact canonical alternative Direct Search path.

Python/FastAPI owns its locale, sparse state, Decimal canonicalization and parameter order.

Astro/TypeScript renders the returned path; it must not independently rebuild it for sensitivity.

### K. Transport does not expand Search URL identity

Use:

```text
POST /api/search/{locale}/sensitivity
POST /{locale}/search/sensitivity
```

for the read-only comparison interaction.

The sensitivity POST page is noindex and is not a new indexable/canonical Search identity.

Do not add sensitivity parameters to the accepted Direct Search GET grammar.

### L. Error distinction

At minimum:

```text
unsupported locale       -> 404
malformed/tampered input -> 400
backend/database failure -> unavailable/5xx
```

A backend failure is not rendered as invalid input or zero results.

### M. Five-locale factual UI

All five accepted Search locales render equivalent sensitivity semantics.

Copy must remain factual and decision-neutral.

Do not use recommendation language such as `recommended`, `best`, `optimal`, `should` or `relax this`.

### N. No persistence or account requirement

Sensitivity writes no database/user state and requires no buyer account.

It must not create BuyerRequirements, Saved Search, Monitor, Shortlist or telemetry records.

### O. Search commercial independence

No seller/broker payment, verification fee, referral value, ad value, subscription or expected HullQ revenue affects either half of the sensitivity evaluation or its delta.

## Deliverables

1. one application sensitivity service with typed request/result semantics;
2. FastAPI `POST /api/search/{locale}/sensitivity`;
3. public Search-page one-change sensitivity forms for active criteria;
4. locale sensitivity SSR page(s) forwarding raw values to FastAPI and rendering only its result;
5. backend-owned canonical alternative Search path;
6. focused application/API/web tests;
7. retained real PostgreSQL 18 -> FastAPI -> built Astro sensitivity proof;
8. CI execution of the retained proof;
9. primary slice document handoff to `REVIEW` only after implementation validation.

## Acceptance criteria

- [ ] A valid current `draft_max` Search accepts a buyer-authored alternative draft and reports factual set delta.
- [ ] A valid current `keel_configuration` Search accepts a buyer-authored alternative keel and reports factual set delta.
- [ ] A mixed Search can change draft while preserving keel exactly.
- [ ] A mixed Search can change keel while preserving draft exactly.
- [ ] The changed criterion must already be active.
- [ ] Same-value proposal returns deterministic zero delta.
- [ ] Current and alternative evaluations use the same accepted Search truth.
- [ ] Current and alternative evaluations use the same `as_of` and coherent DB snapshot/equivalent.
- [ ] Newly-confirmed/no-longer-confirmed are stable-ID set differences, not total-count arithmetic.
- [ ] A same-total/different-membership case proves the set-difference rule.
- [ ] Current/alternative insufficient-data counts remain separate from confirmed matches.
- [ ] FastAPI returns the exact canonical alternative Direct Search path.
- [ ] Astro/TypeScript does not implement Search truth/canonicalization.
- [ ] Search GET query grammar and 400/308 behavior remain unchanged.
- [ ] Sensitivity POST surface is noindex and creates no sitemap/hreflang/indexable permutation.
- [ ] Invalid draft/keel/tampered changed-criterion inputs fail 400 with no sensitivity claim.
- [ ] Unsupported locale fails 404.
- [ ] Backend/database failure is unavailable/5xx, not invalid/zero.
- [ ] All five locales render factual decision-neutral sensitivity copy.
- [ ] No recommendation/score/winner/automatic-relaxation semantics are introduced.
- [ ] No buyer account/persistence is introduced.
- [ ] Organic Search commercial independence remains unchanged.
- [ ] Real PostgreSQL 18 + FastAPI + built Astro proof ends with `BUYER REQUIREMENT SENSITIVITY RESULT -> PASS`.
- [ ] Retained proof runs in normal remote CI.
- [ ] Required repository validation, lint, type-check, Python tests, web tests/check/build all pass.
- [ ] Exact implementation HEAD receives independent review and explicit Owner Acceptance before merge.

## Expected touch points

Expected, not mandatory if an equivalent smaller implementation is proved:

- `src/hullq/application/search_sensitivity.py` (new bounded service);
- `src/hullq/application/search_read.py` only if a shared canonical-path/evaluation helper is safely extracted rather than duplicated;
- `src/hullq/api/app.py`;
- `tests/unit/test_search_sensitivity.py`;
- focused Search/API persistence tests;
- `web/src/components/SearchPageBody.astro`;
- `web/src/components/SearchSensitivityBody.astro` or equivalent shared renderer;
- `web/src/lib/searchSensitivityApi.ts`;
- `web/src/lib/searchText.ts`;
- `web/src/pages/{en,de,fr,pt,es}/search/sensitivity.astro`;
- focused web tests;
- `scripts/inspect_buyer_requirement_sensitivity.py` or a bounded extension of the retained native-inventory Search proof;
- `.github/workflows/ci.yml` only to wire a new retained proof if required.

No Alembic migration is expected.

## Validation

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python -m pytest
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
uv run python scripts/inspect_buyer_requirement_sensitivity.py
```

If the implementation chooses a bounded extension of an existing retained proof rather than the named new script, run/report that exact retained proof command instead.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementing sensitivity requires a new Search criterion or changes accepted criterion semantics;
- current/alternative evaluation cannot reuse the accepted Search truth and would require a second evaluator;
- a second browser/TypeScript canonicalization engine appears necessary;
- the capability requires persisted BuyerRequirements/account state;
- implementation starts suggesting values, recommending a criterion change or optimizing multiple changes;
- sensitivity requires changing the accepted Direct Search GET URL grammar/indexability boundary;
- a coherent current/alternative DB snapshot cannot be established without a broader architecture change;
- a production-data/pilot/launch trigger changes;
- source-rights/provenance/identity/owner-direct commercial-independence rules would be weakened;
- scope expands into Shortlist, Compare, Saved Search, alerts, broker analytics or another deferred capability.

## Status handoff rule

Claude may set the slice to `REVIEW` or `BLOCKED` with the matching explicit handoff line, but MUST NOT mark it `DONE`.

A clean implementation still requires independent exact-head review, remote gates and explicit Project Owner acceptance.

## Required completion report

Use the exact structure required by `docs/slices/SLICE_TEMPLATE.md`.

Do not include a next-slice proposal.

Do not start SLICE-0058.
