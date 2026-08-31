# SLICE-0037 — Acceptance closure

**Slice:** SLICE-0037  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #110  
**Accepted implementation HEAD:** `5687ff380a79af1a9329d381f074be95893a717f`  
**Implementation merge commit:** `b89b8bb81cb74d39a3e6bbeba444667ae89fbdb2`  
**Owner acceptance:** explicitly recorded 2026-08-31

## Accepted scope

SLICE-0037 establishes the first real, provenance-backed, non-fixture BoatDesign path through the existing HullQ configuration-aware Search kernel using BENETEAU Oceanis 30.1.

Accepted retained/runtime-facing artifacts include:

- `research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md`
- `research/benchmark/waves/sl0037-oceanis-30-1/source_retrieval_log.json`
- `research/benchmark/waves/sl0037-oceanis-30-1/oceanis_30_1_projection.v1.json`
- `scripts/search_oceanis_30_1.py`
- `tests/unit/test_search_oceanis_30_1.py`

The accepted real configuration set contains three factory-supported keel configurations: deep fixed keel, shallow fixed keel and performance/hydraulic swing keel. `DesignConfigurationSet.is_fixture=False` and `configuration_space_complete=False` remain explicit.

The retained pilot admits exactly eight independently authorized numeric Search facts and zero categorical Search facts. Admission is fail-closed before Search materialization: design/configuration identity, empty `applied_option_ids`, exact values, resolved state, direct-vs-derived classification, closed `scope_id`, configuration evidence and exact fact evidence sets are independently checked against a pilot-specific code-side oracle rather than self-authorized by the retained JSON.

The bounded source-rights record positively supports the accepted pilot use for SRC-1/SRC-5 (BENETEAU) and SRC-6 (Finot-Conq) under conditional, non-recurring pilot clearance. SRC-4 remains excluded because its domain's robots.txt disallows automated access. Bulk bootstrap and recurring automated ingestion are not claimed.

## Search result proof

The unchanged locked Q1-Q10 shapes run through the existing `hullq.search.configuration_engine` produce:

- `CONFIRMED_MATCH`: Q1, Q2, Q10
- `INSUFFICIENT_DATA`: Q3-Q9
- `CONFIRMED_NON_MATCH`: none

Required configuration-sensitive proof:

- Q10 (`Draft <= 1.60 m`)
- deep-keel configuration: FALSE (`1.85 m`)
- shallow-keel configuration: TRUE (`1.30 m`)
- retractable/hydraulic-swing configuration: UNKNOWN
- exact `matching_configuration_ids`: `("oceanis-30-1-shallow-keel",)`

`FALSE_CONFIRMED_RESULT = 0` remained satisfied.

## Review history

- `707bb6805e61d5de06afb767a176aa5ff15ffb44` — review `5067543634`: CHANGES REQUIRED for retained-artifact self-authorization and incomplete source-access/rights gating.
- `be7e3dba44b09d4645e963f20bb9c79bd549bff7` — review `5068222791`: CHANGES REQUIRED for unclosed `applied_option_ids`, direct-vs-derived and scope admission semantics.
- `5687ff380a79af1a9329d381f074be95893a717f` — review `5068830314`: ACCEPT.

The amendments closed value/evidence/completeness self-authorization, source-access disposition, exact configuration identity, option-id injection, direct-vs-derived lineage, machine-checkable configuration scope and exact evidence-set authorization without changing Search semantics or production Search code.

## Exact-head gates

On accepted HEAD `5687ff380a79af1a9329d381f074be95893a717f`:

- CI run `33413186516`: SUCCESS.
- Manufacturer artifact reproducibility run `33413186533`: SUCCESS.

## Merge verification

PR #110 was merged with expected-head protection against the accepted exact HEAD.

Canonical `main` moved to merge commit `b89b8bb81cb74d39a3e6bbeba444667ae89fbdb2`, whose parents are:

- prior `main`: `7985b7acb6f1976ce59da7f58b2a0013deb06876`
- accepted SLICE-0037 HEAD: `5687ff380a79af1a9329d381f074be95893a717f`

## Retained boundaries and product consequence

SLICE-0037 did not modify production `src/hullq/search/**`, did not add PostgreSQL persistence/read-model work, FastAPI/public HTTP endpoints, frontend/SEO work, market listings, listing deduplication, monitoring/auth/pricing, a generic BENETEAU adapter or a general MTE runtime.

The previously binding product guardrail is now satisfied: at least one real BoatDesign is searchable through the existing Search kernel. The project may now make the next bounded architecture/product decision. In particular, a subsequent product-facing step may connect a confirmed BoatDesign/configuration result to real sales listings while preserving listing-level configuration uncertainty and source-access constraints; that work is not part of SLICE-0037.
