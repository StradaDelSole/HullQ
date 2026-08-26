# HullQ SLICE-0026 Bounded Wikidata Tier-1 Enrichment Evidence Pilot Report

**Selection generated_at:** 2026-08-26T13:37:04.912490+00:00  
**Evidence manifest generated_at:** 2026-08-26T14:43:29.192720+00:00  
**Acquired at:** 2026-08-26T14:43:26.965654+00:00  
**Source:** SRC_WIKIDATA_API_2026

## SCOPE

Evidence-path pilot only. Does not create/mutate canonical BoatModel identity, does not mint or infer a BoatDesign generation, does not create a FieldResolution, and does not claim these BoatModels are fully Tier-1 searchable.

## IDENTITY BOUNDARY (reproduced, fail-closed)

- canonical BoatModels: **1770** (must equal 1,770)
- historical QID -> HullQ-ID mappings: **1772** (must equal 1,772)
- baseline manifest sha256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`
- delta manifest sha256: `41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`

## PILOT SELECTION (100 BoatModels)

- ordering: ascending canonical HullQ BoatModel ID over the combined SLICE-0017+0018 AUTO_ADMIT QID->HullQ-ID universe; first pilot_size taken
- no discovery request was issued; only the selected accepted QIDs were fetched

## REQUEST / RECORD COUNTS

- requested QID count: **100**
- fetched entity count: **100**
- HTTP requests attributed to SRC_WIKIDATA_API_2026: **2**

## ALLOWED FIELD POINTERS

- `/baseline/dimensions/loa_m`
- `/baseline/dimensions/lwl_m`
- `/baseline/dimensions/beam_m`
- `/baseline/dimensions/draft_min_m`
- `/baseline/dimensions/displacement_kg`

## PER-FIELD COVERAGE

Four mutually exclusive, exhaustive states per (BoatModel, field); counts sum to the pilot size for every field.

| field | normalized_candidate_present | source_statement_present | unsupported_or_malformed | no_usable_value |
|---|---|---|---|---|
| loa | 0 | 0 | 64 | 36 |
| lwl | 0 | 0 | 64 | 36 |
| beam | 41 | 0 | 0 | 59 |
| draft | 0 | 0 | 29 | 71 |
| displacement | 0 | 0 | 51 | 49 |

**Note on `unsupported_or_malformed` for LOA/LWL and displacement:** these two field pairs share one raw Wikidata property (P2043 for LOA/LWL, P2067 for displacement/ballast), disambiguated only by a P642 qualifier. A statement whose qualifier value matches neither sibling field is counted as unsupported/malformed against BOTH sibling fields (a conservative upper bound), because the adapter's public outputs do not attribute an unmatched shared-property statement to only one of the two fields without reimplementing qualifier parsing. See `hullq.bootstrap.wikidata_sl0026_tier1_enrichment_pilot.classify_entity_field_coverage`.

## GLOBAL EXTRACTION QUALITY (all properties the adapter extracts, not decomposed per field)

- malformed_statement_count: **0**
- unsupported_qualifier_count: **182**

## POSTGRESQL PERSISTENCE EVIDENCE — LOCAL (this implementation session)

Evidence below was measured locally by running `scripts/bootstrap/wikidata_sl0026_tier1_enrichment_pilot_runner.py --persist` against a real PostgreSQL instance during implementation. Remote GitHub Actions CI independently re-runs the same step at the exact pushed head and is the authoritative external verification.

- PostgreSQL version: `PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit`
- bundles imported (first pass): 100
- bundles already-present (first pass): 0
- bundles conflict (first pass): 0
- readback mismatches: 0
- re-import (idempotency) already_imported: 100
- re-import conflict: 0
- canonical_boat_models row count after both passes: 0 (must be 0 — SLICE-0026 never imports a canonical identity admission)
- canonical_boat_designs row count after both passes: 0 (must be 0)

### RESULT: zero-mutation and idempotency proof clear (local): **True**

## SCOPE CONFIRMATION

- No discovery/SPARQL request was made; only the 100 selected known QIDs were fetched.
- No canonical BoatModel/BoatDesign row was created or mutated.
- No FieldResolution was created.
- Existing Wikidata adapter extraction and SLICE-0004 normalization were reused, not reimplemented.
- SLICE-0027 was not created or started.

