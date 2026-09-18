# SLICE-0056 — Public Multi-Criterion Direct Search Browser Completion

**ID:** SLICE-0056  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Public buyer Direct Search — browser/API contract completion  
**Depends on:** SLICE-0055 owner-accepted / DONE; post-SLICE-0055 reconciliation completed  
**Blocks:** post-SLICE-0056 mandatory workflow reassessment before SLICE-0057 readiness; later BuyerRequirements/explainability work that depends on a truthful public two-criterion Search surface

## Objective

Deliver exactly one visible corrective capability:

> A buyer can use the canonical public HullQ Search page to search by `draft_max`, by `keel_configuration`, or by both together, and the SSR browser result faithfully renders the already-accepted FastAPI Search state/evidence without inventing a second Search engine.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
This slice closes one browser/API contract gap: the public Direct Search surface must represent the already accepted two-criterion Search capability.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can open a locale Search page, choose draft and/or keel requirements, submit, observe the canonical URL, and inspect confirmed results/evidence in the rendered browser page.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is the smallest user-visible correction to a known accepted Search regression. It preserves strict truth, FastAPI as the sole application/domain API boundary, server-rendered public Search, deterministic URL state, noindex Search routes, organic Search commercial independence and one-capability slicing. It does not add a criterion or speculative buyer/seller infrastructure.

**REPOSITORY RECONCILIATION CHECK:** PASS  
SLICE-0055 already decided and implemented keel-only/mixed native Search semantics and typed application evidence. Canonical FastAPI supports the accepted sparse `active_requirement` and multi-criterion result shape, while the current Astro/TypeScript Search adapter/form/renderer remain SLICE-0051 draft-only. The exact remaining work is browser contract completion, not Search-semantic redesign.

**TRIGGER GATES CHECK:** PASS  
Production Readiness remains `NOT_TRIGGERED`; this slice adds no technical native Search criterion; technical criterion count remains 2; Search abstraction comparison/third-copy guards are not applicable; workflow reassessment remains `NOT_DUE` during execution and becomes `DUE` only through the acceptance closure if SLICE-0056 is owner-accepted.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0055_REASSESSMENT_2026-09-18.md`; `docs/slices/SLICE-0055-second-technical-native-search-keel.md`; `docs/slices/SLICE-0055-acceptance-closure.md`; `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md`; `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; OQ-018 public Search URL/canonical/indexability/invalid-request decisions; `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`; post-0051 trigger/production-readiness governance.  
**Production implementation checked:** `src/hullq/api/app.py`; `src/hullq/application/search_read.py`; `src/hullq/application/native_inventory_query.py`; `web/src/components/SearchPageBody.astro`; `web/src/lib/searchApi.ts`; `web/src/lib/searchPageData.ts`; `web/src/lib/searchText.ts`; locale Search routes; web Search tests; `tests/persistence/test_inventory_search_draft_max_api.py`; `tests/persistence/test_inventory_search_keel_api.py`; `scripts/inspect_first_native_inventory_search.py`.  
**Already implemented / not re-decided:** exact `draft_max`; six-value `keel_configuration`; keel-only and mixed FastAPI evaluation; hard MUST/AND and three-valued truth; typed 0055 design/configuration + concrete evidence; freshness gating; locale-prefixed SSR Search routes; deterministic query-parameter state; backend-owned canonicalization/400/308; public noindex Search class; commercial independence.  
**Exact remaining gap:** the canonical web adapter/form/renderer still model only `active_requirement.draft_max` and `resolved_draft_m`, expose no keel control, and therefore cannot faithfully submit/render the accepted keel-only or mixed Search response shape.  
**Accepted-but-unimplemented obligations:** this slice owns the corrective public browser projection of the accepted two-criterion Direct Search. BuyerRequirements, sensitivity/`Why no match?`, individualized non-match explainability, Saved Search, criterion #3+, broker Search intelligence, owner-direct publication and pending Broker Workspace commitments remain explicitly deferred to their existing future triggers/capability selection.  
**Material classifications:** `DECIDED_AND_IMPLEMENTED` for the Search/API truth and OQ-018 browser architecture; `CONFLICT_OR_REGRESSION` for the stale public Astro/TypeScript projection; `DECIDED_NOT_YET_IMPLEMENTED` for the corrective browser completion; `EXPLICITLY_DEFERRED` for the named broader buyer/seller/Search capabilities.

## Trigger gates

**Production readiness gate:** NOT_TRIGGERED  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** NOT_DUE  

Evidence:

- accepted technical native Search criteria count is already `2`; this slice changes no Search criterion semantics or count;
- implementation consumes the existing 0055 API/evidence contract rather than adding another field bridge/truth path;
- no real external broker/owner-direct production data, production pilot or public production launch is introduced;
- organic Search eligibility, match classification and ordering remain independent of payment/verification/commercial value;
- if this slice is later owner-accepted, its **acceptance closure** must change canonical workflow reassessment state from `NOT_DUE` to `DUE`; implementation must not pre-accept that governance transition.

## Why this slice exists

SLICE-0055 was accepted as a visible buyer capability, but its implementation updated the production application/API path without updating the canonical public Astro Search adapter/form/renderer from the earlier SLICE-0051 draft-only contract.

The current mismatch is concrete:

```text
FastAPI 0055:
active_requirement = draft_max? + keel_configuration?
confirmed keel/mixed match = criterion_evidence + design_configuration_evidence + freshness

Astro 0051:
activeRequirement = { draft_max }
confirmed match = resolved_draft_m + freshness
form = draft_max only
```

Leaving that mismatch in place would make Direct Search semantics depend on whether the buyer uses the API or the canonical browser surface. This slice closes that regression before additional Search breadth or buyer decision tools are added.

## Controlling artifacts

- Requirement IDs: accepted SLICE-0055 capability/evidence obligations; OQ-018 public Search decisions
- Specifications: `specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md`; `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`
- Accepted architecture: `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`; current Astro/FastAPI rebaseline
- Public Search decisions: `docs/OQ_018_PUBLIC_SEARCH_URL_STATE_DECISION_2026-09-11.md`; `docs/OQ_018_SEARCH_CANONICAL_IDENTITY_DECISION_2026-09-11.md`; `docs/OQ_018_SEARCH_INDEXABILITY_AND_SEO_READINESS_DECISION_2026-09-11.md`; `docs/OQ_018_SEARCH_INVALID_REQUEST_RECOVERY_DECISION_2026-09-11.md`
- Product direction: `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`; `docs/PRODUCT_SUCCESS_CUSTOMER_PRIORITY_2026-09-11.md`
- Broker mandatory register: `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`
- Owner-direct direction: `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`; `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`

## In scope

- update the public web Search TypeScript contract to represent sparse `draft_max` and/or `keel_configuration` active requirements returned by FastAPI;
- preserve the legacy draft-only result shape without changing its accepted semantics;
- faithfully model the existing 0055 keel/mixed confirmed-match shape, including concrete typed criterion evidence needed for truthful buyer rendering;
- add an exact canonical `keel_configuration` form control using only the six accepted public values;
- allow draft-only, keel-only and draft+keel submissions from every supported locale route;
- render the active requirements actually applied by FastAPI, not inferred browser-side;
- render confirmed matches without assuming `resolved_draft_m` exists on keel/mixed results;
- for keel/mixed confirmed results, show the safely observed concrete criterion value(s) from the existing API evidence with clear buyer-facing wording;
- preserve the accepted freshness label/note behavior;
- preserve the clearly separate insufficient-data count/state without calling those listings matches;
- preserve FastAPI-owned canonicalization, invalid-request and redirect behavior;
- preserve public Search `noindex` and existing canonical-link behavior;
- add browser/web tests plus a real retained FastAPI + built Astro SSR proof for keel-only and mixed Search, while retaining the existing draft-only proof.

## Explicitly out of scope

- any change to Search truth semantics, configuration evaluation or PhysicalBoat contradiction rules;
- a third hard technical Search criterion;
- changing the accepted six-value public keel vocabulary;
- client-side reimplementation of Search canonicalization, query validation or truth classification;
- individualized non-match/insufficient listing disclosure or `Why no match?` sensitivity;
- BuyerRequirements / MUST-PREFER-DONT_CARE persistence or guided journey;
- recommendation, ranking, scoring, winner or fit percentage;
- shortlist/Compare/sharing;
- Saved Search/alerts/monitoring;
- broker aggregate Search intelligence / REQ-BROKER-025/029;
- owner-direct publication/admission/trust escalation;
- Broker Workspace listing/media/lead/payment expansion;
- broad/indexable SEO landing pages, sitemap or structured-data expansion;
- Production Readiness/pilot/deployment work.

## Required behavior

### A. Form and URL state

The locale Search form must expose:

```text
draft_max            optional exact-decimal text input
keel_configuration   optional canonical single-value selector
```

The keel selector values must be exactly:

```text
FIN
FIN_WITH_BULB
WING
CENTERBOARD
LIFTING_KEEL
TWIN_KEEL
```

The buyer may submit either criterion alone or both together. An empty form remains the base Search state.

The browser must submit ordinary query parameters and let FastAPI own validation/canonicalization. It must not normalize a non-canonical draft number or reinterpret an invalid keel value itself.

### B. Canonical / invalid protocol

Existing accepted protocol remains:

```text
valid canonical request      → 200
valid non-canonical request  → FastAPI 308 → browser reissues exact Location
invalid/ambiguous request    → 400 localized recovery; no Search result claim
backend/network unavailable  → unavailable state, not invalid/empty
```

Canonical query ordering and sparse parameter identity remain backend-owned.

### C. Active requirement rendering

For a canonical result, the page must render exactly the active requirement keys/values returned by FastAPI.

Supported states are:

```text
{ draft_max }
{ keel_configuration }
{ draft_max, keel_configuration }
```

No browser-side default criterion may silently appear.

### D. Confirmed-match rendering

Draft-only responses must preserve the accepted SLICE-0051/0052 buyer rendering and exact `resolved_draft_m` behavior.

Keel-only/mixed responses must use the existing 0055 typed evidence rather than re-running evaluation or parsing explanation text.

For every active criterion on a confirmed keel/mixed result, buyer-visible evidence must identify the safely observed concrete canonical value when present:

- numeric draft evidence remains a canonical decimal metre value;
- keel evidence remains one accepted canonical keel value.

A confirmed match with an active criterion must not be displayed with `undefined`, missing-value fabrication, or a value reconstructed from design-level truth when concrete evidence is absent.

This is confirmed-match evidence projection only; it is not the later individualized explainability/sensitivity feature.

### E. Insufficient data

The accepted separate `insufficient_data_count` remains visibly distinct from confirmed matches.

The page may explain at category level that missing/unknown/conflicting evidence prevented confirmation, but must not invent or expose a per-listing diagnosis that the API did not return on the public primary result surface.

### F. Freshness

Existing `CONFIRMED` versus `DUE_FOR_CONFIRMATION` rendering remains intact for all result shapes. STALE/UNKNOWN inventory remains excluded upstream as already accepted.

### G. Locale and SSR consistency

All supported locale Search routes use the same shared presentation/data contract and support all three active-requirement states. Technical parameter/value tokens remain language-neutral; buyer-facing prose is localized through the existing translation module.

No client-only JavaScript Search engine is introduced.

### H. Retained vertical proof

Add or extend a retained proof executed against:

```text
real PostgreSQL 18
→ canonical design/configuration + FieldResolution
→ concrete native listing/PhysicalBoat claims
→ FastAPI Search
→ built Astro SSR Search page
```

The proof must demonstrate at minimum:

1. draft-only browser behavior remains correct;
2. keel-only Search submitted/rendered through the public SSR surface;
3. draft+keel Search submitted/rendered through the public SSR surface;
4. canonical active-requirement text/values are visible;
5. confirmed result evidence shows the concrete keel value and, for mixed, both concrete criterion values;
6. insufficient-data content remains separate and is not promoted to a match;
7. canonical redirect and invalid-request behavior remain unchanged.

The retained proof must run in the normal remote CI path, not remain a local-only script.

## Deliverables

- updated web Search API/data TypeScript types/adapters;
- updated shared Search form/result renderer;
- localized Search copy for keel/mixed active requirements and confirmed evidence;
- regression tests for draft-only behavior;
- keel-only and mixed web tests;
- retained PostgreSQL + FastAPI + built Astro SSR proof wired into CI;
- no backend Search-semantic change unless a concrete adapter defect makes a minimal compatibility change necessary and the implementation report calls it out.

## Acceptance criteria

1. Browser Search form supports exact accepted keel values and permits draft-only, keel-only and mixed submission.
2. Keel-only canonical Search renders the correct active requirement and confirmed listing without `undefined`/draft-only assumptions.
3. Mixed canonical Search renders both active requirements and both concrete criterion values for a confirmed result.
4. Draft-only rendering remains behaviorally unchanged.
5. FastAPI remains the sole canonicalization/validation/truth owner; web code does not duplicate Search semantics.
6. Non-canonical valid URLs still 308 to the exact FastAPI canonical Location.
7. Invalid/ambiguous requests still render localized 400 recovery distinct from service unavailability.
8. Insufficient-data count/state remains separate from primary confirmed matches.
9. Freshness rendering remains correct for CONFIRMED and DUE_FOR_CONFIRMATION.
10. All supported locale routes use the shared multi-criterion contract/copy and remain `noindex`.
11. A real PostgreSQL + FastAPI + built Astro SSR retained proof covers draft-only, keel-only and mixed browser states and runs in remote CI.
12. No BuyerRequirements, sensitivity, ranking/recommendation, criterion #3, broker intelligence, owner-direct publication or broad SEO scope appears.
13. Repository validation, Python tests, web tests/check/build, typing/lint and remote CI pass.

## Expected touch points

- `web/src/components/SearchPageBody.astro`
- `web/src/lib/searchApi.ts`
- `web/src/lib/searchPageData.ts`
- `web/src/lib/searchText.ts`
- `web/src/lib/__tests__/searchApi.test.ts`
- `web/src/lib/__tests__/searchPageData.test.ts`
- `web/src/lib/__tests__/searchText.test.ts`
- additional focused web component/SSR tests if needed
- `scripts/inspect_first_native_inventory_search.py` or a bounded successor/extension for the retained two-criterion browser proof
- `.github/workflows/ci.yml` only as needed to wire the retained proof into remote CI
- existing locale Search page wrappers only if a shared-contract change requires it

Backend Search modules are not expected touch points unless independent implementation evidence proves a minimal compatibility defect. Any such change must preserve all accepted SLICE-0055 semantics and be explicitly reported.

## Validation

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest tests/
npm test --prefix web
npm run check --prefix web
npm run build --prefix web
```

The retained PostgreSQL/FastAPI/Astro proof must also pass locally when the required test database/environment is available and in remote CI.

## Stop conditions

Stop and report rather than inventing semantics if:

- the web correction would require changing accepted `draft_max` or `keel_configuration` truth semantics;
- implementation requires a new public keel vocabulary/mapping;
- a correct browser projection would require re-running Search truth outside FastAPI;
- existing API evidence is insufficient to render a confirmed criterion truthfully without a material API/domain-contract decision;
- an accepted OQ-018 URL/indexability rule would need to change;
- a Production Readiness trigger fires;
- scope expands into BuyerRequirements/sensitivity, criterion #3, owner-direct publication or Broker Workspace product work.

## Status handoff rule

The implementation agent may set `REVIEW` or `BLOCKED` as appropriate but MUST NOT mark this slice `DONE`.

On handoff, update the primary metadata status and add the matching canonical execution-handoff marker **as a real metadata line next to the header**, not only inside prose or a fenced example. Follow `docs/slices/SLICE_TEMPLATE.md` exactly.

`DONE` requires exact-head independent review, required remote checks and explicit Project Owner acceptance.

## Required completion report

Use the canonical `docs/slices/SLICE_TEMPLATE.md` completion-report structure.

Do not start SLICE-0057. After accepted SLICE-0056, the mandatory workflow reassessment becomes `DUE` and blocks SLICE-0057 readiness/start until separately completed and owner-accepted.
