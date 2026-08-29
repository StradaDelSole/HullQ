# SLICE-0033 — Search kernel first product vertical

**ID:** SLICE-0033  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Product Track A — first trustworthy search vertical  
**Depends on:** SLICE-0032 accepted / DONE; accepted `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`  
**Blocks:** first internal FastAPI/search UI preview and practical OQ-009 benchmark

## Objective

Implement the smallest trustworthy HullQ search kernel that can evaluate serializable numeric technical MUST criteria over canonical BoatDesign-style data and return separately classified confirmed matches, confirmed non-matches and insufficient-data records with criterion-level explanations.

This is the first Product Track increment after the execution pivot. It deliberately does not attempt to build the whole search product.

## Why this slice exists

HullQ now moves Product Validation and Continuous Data Expansion in parallel. The accepted 1,770-BoatModel identity/evidence foundation is useful, but normalized research evidence is not automatically canonical searchable truth. The first product increment therefore needs a real deterministic query engine without pretending provisional/evidence-only fields are valid matches.

This slice implements only the minimum subset explicitly permitted by `SEARCH_QUERY_SEMANTICS.v0.1.md` and creates an executable local demonstration. It does not wait for every advanced search feature, public SEO decision or broad BoatDesign promotion campaign.

## Controlling artifacts

- Requirement IDs: REQ-PROD-001, REQ-PROD-005, REQ-DATA-001, REQ-DATA-005, REQ-DATA-008, REQ-PROV-005, REQ-SEARCH-001 through REQ-SEARCH-006 as applicable to the implemented subset.
- Normative specification: `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`.
- Existing contracts: `specs/BOAT_DESIGN_SCHEMA.v0.4.json`, `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`, `specs/DERIVED_METRICS_SPEC.v1.0.md` only where needed to distinguish qualified from provisional values.
- Accepted architecture: ADR-0010 / PostgreSQL-first application stack; no dedicated search engine without measured need.
- Relevant open questions deliberately not resolved here: OQ-018 public SEO surface, OQ-020 market geography, OQ-014 auth, OQ-015 public API/versioning, OQ-005 listing dedup, OQ-006 alert cadence.

`specs/SEARCH_QUERY_SEMANTICS.v0.1.md` is the accepted OQ-009 D1–D10 decision output. If `specs/REQUIREMENTS.md` or `docs/governance/OPEN_QUESTIONS.md` still contains stale OQ-009 `BLOCKED`/`OPEN` metadata, reconcile that metadata in this slice before implementing behavior; do not reopen or reinterpret the accepted semantics.

## In scope

1. Reconcile stale OQ-009 metadata in the requirements/open-question register so repo truth reflects the accepted search-semantics spec.
2. Add a small `hullq.search` domain package with explicit typed contracts for:
   - leaf numeric criterion;
   - MUST requirement strength for the implemented subset;
   - explicit AND query expression;
   - criterion truth state TRUE/FALSE/UNKNOWN;
   - query result class CONFIRMED_MATCH/CONFIRMED_NON_MATCH/INSUFFICIENT_DATA;
   - reason codes needed by the implemented subset;
   - criterion-level explanation metadata.
3. Implement deterministic numeric minimum/maximum/range evaluation with inclusive boundaries.
4. Compare only canonicalized/canonical-unit values. No display-rounded comparison and no hidden epsilon.
5. Implement fail-closed value qualification so missing, unresolved-conflict and provisional values cannot confirm either inclusion or exclusion.
6. Aggregate multiple MUST numeric leaves with explicit AND semantics.
7. Return separate collections/counts for confirmed matches and insufficient-data records. Confirmed non-matches may be retained for explainability/debugging but MUST NOT appear in the primary match set.
8. Provide deterministic serialization/deserialization (plain JSON-compatible mapping is sufficient; do not create a large persistence subsystem) for the implemented query subset.
9. Add a persistence-neutral search projection/input type so future PostgreSQL/FastAPI layers do not need to evaluate raw research artifacts directly.
10. Add a small executable local demonstration/test fixture showing a technical query such as LOA range + max draft + beam range over several BoatDesign-style projections and visibly producing all three outcome classes.
11. Add focused unit/property tests and any minimal contract fixtures required.

## Explicitly out of scope

- FastAPI endpoints or public HTTP API design.
- Astro/React frontend or public routing.
- OQ-018 SEO/indexability/canonical URL rules.
- PostgreSQL search-index tuning, PostGIS, pg_trgm or dedicated search engine introduction.
- Full OR/NOT public query support.
- PREFER ranking implementation.
- Full ResolvedConfiguration expansion/option search implementation beyond keeping the input boundary compatible with later configuration-aware evaluation.
- Market listing search, geography, monitoring, alerts, auth, pricing, marketplace features or broker functionality.
- Promotion of the 1,770 normalized research-evidence BoatModels into canonical BoatDesign technical values.
- Using normalized research evidence, `computed_provisional`, SailboatData or any other provisional/reference value as a confirmed match shortcut.

## Required behavior

### A. Numeric leaf truth

For a fully qualified value:

- inclusive minimum passes on equality;
- inclusive maximum passes on equality;
- inclusive range passes on either boundary;
- contradiction returns FALSE.

For missing/provisional/unresolved-conflict data:

- return UNKNOWN with the appropriate reason;
- never return FALSE solely because the value is unavailable;
- never return TRUE from provisional evidence.

### B. AND query truth

- any FALSE => CONFIRMED_NON_MATCH;
- all TRUE => CONFIRMED_MATCH;
- otherwise => INSUFFICIENT_DATA.

### C. Primary result boundary

- primary count/list contains only CONFIRMED_MATCH;
- insufficient-data records are separate;
- no helper may implement `criterion OR NULL` semantics.

### D. Determinism

Equivalent serialized query input and identical projection data produce identical truth/explanation output and stable deterministic ordering. Until an explicit sort exists, use a simple stable identity order; do not invent a quality/popularity/completeness score for confirmed matches.

### E. No false production-data claim

The local demo may use explicit test/fixture BoatDesign projections. It MUST label them as fixtures and MUST NOT claim that the current 1,770 evidence records are already canonical searchable BoatDesigns.

## Deliverables

- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` retained as controlling spec.
- stale OQ-009 metadata reconciled in `specs/REQUIREMENTS.md` and `docs/governance/OPEN_QUESTIONS.md` without changing the accepted D1–D10 semantics.
- `src/hullq/search/` minimal search kernel.
- focused tests under `tests/unit/` and/or `tests/contract/`.
- small local demo/fixture path, preferably under `scripts/` + `fixtures/search/`, without adding a frontend framework.

## Acceptance criteria

- [ ] OQ-009 is no longer shown as unresolved/blocking in repo metadata; the accepted search-semantics spec is referenced.
- [ ] Numeric MUST min/max/range boundaries are inclusive and deterministic.
- [ ] Missing, provisional and unresolved-conflict values yield UNKNOWN, never confirmed match/non-match solely from uncertainty.
- [ ] `computed_provisional` cannot confirm either inclusion or exclusion.
- [ ] Explicit AND aggregation implements FALSE-wins / all-TRUE-match / otherwise-UNKNOWN exactly.
- [ ] Primary match set/count contains CONFIRMED_MATCH only; insufficient-data output is separate.
- [ ] Criterion-level truth/reason/explanation is available in the evaluator result.
- [ ] Implemented query subset round-trips through a JSON-compatible serialized form without semantic drift.
- [ ] Stable ordering does not use hidden completeness, source prestige, popularity or generic quality score.
- [ ] Local demo/fixture visibly exercises confirmed match, confirmed non-match and insufficient-data outcomes.
- [ ] No canonical BoatModel/BoatDesign/FieldResolution mutation and no research-evidence promotion occurs in this slice.
- [ ] No FastAPI/Astro/public SEO/API decision is silently introduced.
- [ ] Ruff format/check, mypy strict, repository validator, full pytest/coverage >=90% pass.
- [ ] Exact-head CI passes on required platforms.

## Expected touch points

- `specs/REQUIREMENTS.md`
- `docs/governance/OPEN_QUESTIONS.md`
- `src/hullq/search/__init__.py`
- `src/hullq/search/...`
- `fixtures/search/...`
- `tests/unit/test_search_*.py`
- optional small `scripts/search_*.py`

Avoid persistence schema migrations unless a concrete unavoidable need appears; if so, stop and report instead of widening the slice.

## Validation

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run pytest
uv run coverage run -m pytest
uv run coverage report
uv run python scripts/validate_repository.py
```

Run the local search demo command added by the slice and report its three outcome classes.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation would require treating evidence-only/provisional values as confirmed search truth;
- the accepted search-semantics spec materially conflicts with another current normative spec after stale metadata is reconciled;
- a public API, public frontend/SEO route, auth, geography or listing-dedup decision becomes necessary to satisfy this slice;
- configuration semantics beyond the accepted spec are required for the minimal numeric vertical.

## Status handoff rule

The implementation agent may leave `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark the slice DONE or merge it.

## Required completion report

Use the standard structure in `docs/slices/SLICE_TEMPLATE.md`, concise but complete. In addition report:

- exact local demo query and summarized outcome counts;
- exact implemented reason codes;
- explicit confirmation that provisional/unknown data could not enter the confirmed-match set;
- explicit confirmation that the 1,770 evidence corpus was not relabeled canonical searchable data;
- exact final HEAD and exact-head remote CI state;
- no next slice started.
