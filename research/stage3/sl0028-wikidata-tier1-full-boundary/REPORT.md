# HullQ SLICE-0028 Full-Boundary Wikidata Tier-1 Evidence Rollout Report

**Linkage generated_at:** 2026-08-26T22:55:43.659507+00:00  
**Evidence manifest generated_at:** 2026-08-26T22:56:24.134482+00:00  
**Acquired at:** 2026-08-26T21:52:06.805656+00:00  
**Source:** SRC_WIKIDATA_API_2026

## SCOPE

Full-boundary evidence acquisition, normalization, coverage and persistence rollout only. Does not create/mutate canonical BoatModel identity, does not mint or infer a BoatDesign generation, does not create a FieldResolution, and does not claim any BoatModel is fully Tier-1 searchable merely because source evidence exists.

## IDENTITY BOUNDARY (reproduced, fail-closed)

- canonical BoatModels: **1770** (must equal 1,770)
- historical QID -> HullQ-ID mappings: **1772** (must equal 1,772)
- baseline manifest sha256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`
- delta manifest sha256: `41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`

## HISTORICAL REGISTRY RECONCILIATION (1,772 vs 1,770)

- historical registry count: **1772**
- canonical AUTO_ADMIT QID -> BoatModel linkage count: **1770**
- non-canonical historical/reserved mappings excluded from acquisition: **2**

| reserved QID | reserved HullQ ID | decision | reason codes |
|---|---|---|---|
| Q109650429 | `BM_WDT0_6221328c32fe4b43b113c0ffc5e0bec9` | review_required | name_collision |
| Q2461915 | `BM_WDT0_25df3c46ed4c45c292c817cf4b7eb0b3` | review_required | name_collision |

The accepted SLICE-0017+0018 identity implementation distinguishes the full historical QID -> HullQ-ID registry (every QID ever given a real minted/reserved HullQ ID) from the canonical AUTO_ADMIT linkage (every QID currently addressing a real canonical BoatModel row). Each reserved entry below carries a real, never-reminted HullQ ID, but no canonical BoatModel row was ever created for it (current decision is not AUTO_ADMIT) -- it is excluded from SLICE-0028 acquisition because it does not address a canonical BoatModel. historical_registry_count == canonical_auto_admit_linkage_count + non_canonical_reserved_count.

## FULL-BOUNDARY LINKAGE

- linked BoatModels: **1770**
- distinct request QIDs: **1770**
- ordering: ascending canonical HullQ BoatModel ID over the combined SLICE-0017+0018 AUTO_ADMIT QID->HullQ-ID universe; each BoatModel's own accepted QIDs ascending
- no discovery request was issued; only the accepted linkage-derived QIDs were fetched

## REQUEST / RECORD COUNTS

- requested QID count: **1770**
- fetched entity count: **1770**
- acquisition failure count: **0**
- HTTP requests attributed to SRC_WIKIDATA_API_2026: **36**

## ALLOWED FIELD POINTERS

- `/baseline/dimensions/loa_m`
- `/baseline/dimensions/lwl_m`
- `/baseline/dimensions/beam_m`
- `/baseline/dimensions/draft_min_m`
- `/baseline/dimensions/displacement_kg`

## PER-FIELD COVERAGE

Four mutually exclusive, exhaustive states per field. source_qid_level counts sum to 1770 for every field; boat_model_level counts sum to 1770 for every field.

### source-QID level

| field | normalized_candidate_present | source_statement_present | unsupported_or_malformed | no_usable_value |
|---|---|---|---|---|
| loa | 888 | 0 | 227 | 655 |
| lwl | 848 | 0 | 227 | 695 |
| beam | 891 | 1 | 0 | 878 |
| draft | 691 | 0 | 11 | 1068 |
| displacement | 66 | 792 | 155 | 757 |

### canonical-BoatModel level (strongest-available-evidence precedence)

| field | normalized_candidate_present | source_statement_present | unsupported_or_malformed | no_usable_value |
|---|---|---|---|---|
| loa | 888 | 0 | 227 | 655 |
| lwl | 848 | 0 | 227 | 695 |
| beam | 891 | 1 | 0 | 878 |
| draft | 691 | 0 | 11 | 1068 |
| displacement | 66 | 792 | 155 | 757 |

## CANDIDATE-MULTIPLICITY / VALUE-DISAGREEMENT DIAGNOSTICS

Flagged (BoatModel, field) cases: **42**. Diagnostic only — no canonical value is chosen and no case is silently resolved.

## BASIC_SEARCHABLE_EVIDENCE_PRECURSOR (non-canonical diagnostic)

- qualifying BoatModels: **607** / 1770 (34.2938%)
- This is NOT CAL-01 D2 basic-searchable coverage and MUST NOT be reported as launch-readiness coverage. No canonical BoatDesign, FieldResolution or searchable technical value has been created or decided. Source-evidence diagnostic only, intended to inform the still-pending CAL-01 D2b threshold decision.

## GLOBAL EXTRACTION QUALITY (all properties the adapter extracts, not decomposed per field)

- malformed_statement_count: **0**
- unsupported_qualifier_count: **451**

## POSTGRESQL PERSISTENCE EVIDENCE — LOCAL (this implementation session)

Evidence below was measured locally by running `scripts/bootstrap/wikidata_sl0028_full_boundary_evidence_runner.py --persist` against a real PostgreSQL instance during implementation. Remote GitHub Actions CI independently re-runs the same step at the exact pushed head and is the authoritative external verification.

- PostgreSQL version: `PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit`
- bundles imported (first pass): 1770
- bundles already-present (first pass): 0
- bundles conflict (first pass): 0
- readback mismatches: 0
- re-import (idempotency) already_imported: 1770
- re-import conflict: 0
- canonical_boat_models row count after both passes: 0 (must be 0)
- canonical_boat_designs row count after both passes: 0 (must be 0)

### RESULT: zero-mutation and idempotency proof clear (local): **True**

## SCOPE CONFIRMATION

- No discovery/SPARQL request was made; only the linkage-derived accepted QIDs were fetched.
- No canonical BoatModel/BoatDesign row was created or mutated.
- No FieldResolution was created.
- Existing Wikidata adapter extraction and SLICE-0004 normalization were reused, not reimplemented.
- `basic_searchable_evidence_precursor` is explicitly non-canonical and is not CAL-01 D2 basic-searchable coverage.
- SLICE-0029 was not created or started.

