# SLICE-0038 — Acceptance closure

**Slice:** SLICE-0038  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #117  
**Accepted implementation HEAD:** `d42bf5cf00ed29871e839b212d7e749a00c98b23`  
**Implementation merge commit:** `b1239fe4b00c5fe38d7cc544da7e6d7030b1b79c`  
**Owner acceptance:** explicitly recorded 2026-09-01

## Accepted scope

SLICE-0038 establishes the first real HullQ end-to-end product loop from an unchanged configuration-aware technical Search result to current real sales offers through one bounded market source, while preserving exact BoatDesign identity and listing-level physical-boat uncertainty.

Accepted retained/runtime-facing artifacts include:

- `research/market/sl0038-owning-oceanis-30-1/REPORT.md`
- `research/market/sl0038-owning-oceanis-30-1/owning_source_access_record.json`
- `research/market/sl0038-owning-oceanis-30-1/owning_oceanis_30_1_sample.v1.json`
- `scripts/search_oceanis_30_1_sales.py`
- `tests/unit/test_search_oceanis_30_1_sales.py`

No production `src/hullq/**` code was changed.

## End-to-end proof

The accepted owner-test path is:

```text
Q10: Draft <= 1.60 m
→ unchanged SLICE-0037 real Oceanis 30.1 Search
→ CONFIRMED_MATCH
→ matching design configuration: oceanis-30-1-shallow-keel
→ Owning.pro public read API
→ current real candidate listings
→ independent exact BoatDesign identity admission
→ listing-level TRUE / FALSE / UNKNOWN assessment
```

On the retained 2026-08-31 live result:

- Owning candidates received: 10.
- Identity-admitted Oceanis 30.1 offers: 7.
- Identity-unresolved candidates: 3.
- Listing-level TRUE: 0.
- Listing-level FALSE: 0.
- Listing-level UNKNOWN: 7.

All seven admitted offers remained `UNKNOWN` because no live candidate exposed an admissible structured listing-specific draft observation. This is an accepted fail-closed product result, not a defect: the existence of a matching factory configuration at design level was never promoted into truth about the physical offered boat.

The accepted implementation also rejects nonphysical/malformed draft values, preserves conflicts as UNKNOWN, does not infer configuration from keel terminology, and never treats upstream portal attribution as permission to fetch the upstream source.

## Identity amendment and review history

- `b52f4fd94e6144961e967f5095bd1133d54acbfc` — independent exact-head review found one blocker: conflicting structured identity observations from `attributes` and `boat_specs` could be silently collapsed instead of failing closed.
- `d42bf5cf00ed29871e839b212d7e749a00c98b23` — amendment made structured brand/model admission conflict-aware without adding fuzzy/general entity resolution; conflicting brand/model observations now remain unresolved, while missing-field and normalization-equivalent duplicate observations still admit. Three focused regression tests were added.
- Final independent review result on `d42bf5cf00ed29871e839b212d7e749a00c98b23`: ACCEPT, no remaining blocker.

## Exact-head validation gates

On accepted HEAD `d42bf5cf00ed29871e839b212d7e749a00c98b23`:

- full local suite reported `3373 passed / 217 skipped`;
- CI run `33452659613`: SUCCESS;
- Manufacturer artifact reproducibility run `33452659599`: SUCCESS.

## Source-access boundary

Owning.pro was the only live market source used. The bounded source-access record supports this one non-recurring local pilot on affirmative public API/developer/agent surfaces, while explicitly not granting recurring polling, bulk bootstrap, full-market mirroring, longitudinal history, source-material redistribution or general production ingestion.

Owning exposed upstream portal attribution including YachtWorld, Boat24 and Ancasta. No upstream portal was fetched for enrichment.

OQ-013 therefore remains unresolved globally; SLICE-0038 does not establish a general market-access permission or production adapter authorization.

## Merge verification

PR #117 was merged with expected-head protection against accepted HEAD `d42bf5cf00ed29871e839b212d7e749a00c98b23`.

Canonical `main` moved to merge commit `b1239fe4b00c5fe38d7cc544da7e6d7030b1b79c`, whose parents are:

- prior `main`: `ff4cc9dd3e4761b31ffffa4aeeaf9bc5b5186845`
- accepted SLICE-0038 HEAD: `d42bf5cf00ed29871e839b212d7e749a00c98b23`

## Retained boundaries and product consequence

SLICE-0038 did not implement multi-source aggregation, cross-platform physical-listing deduplication, recurring monitoring/alerts, market-history persistence, PostgreSQL market persistence, a public API/frontend, generic fuzzy identity resolution, generic listing-NLP extraction, or a production market-adapter framework.

The first real design-to-market product loop is now proven. From completion of SLICE-0038 onward, `docs/PRODUCT_EXECUTION_PLAN.md` controls execution sequencing. This closure does not authorize or start the next slice; subsequent work must follow the accepted post-0038 plan and its product-validation gates.
