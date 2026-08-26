# HullQ SLICE-0027 Wikidata Qualifier-Semantics Correction + Offline Replay Report

**Qualifier shape analysis generated_at:** 2026-08-26T19:32:56.161392+00:00  
**Coverage before/after generated_at:** 2026-08-26T19:32:56.436160+00:00  
**Source:** SRC_WIKIDATA_API_2026

## SCOPE

Bounded qualifier-property compatibility correction and offline replay only. Uses exclusively the already-retained, unmodified SLICE-0026 100-BoatModel raw-entity claim payload. No live Wikidata acquisition. Does not expand beyond the five allowed field pointers, does not mutate the SLICE-0026 retained package, and does not create/mutate canonical BoatModel/BoatDesign identity.

## QUALIFIER-SHAPE ANALYSIS

Every (statement property, qualifier property, qualifier-value QID) combination observed on the retained SLICE-0026 raw claims for the three shared/qualified properties (P2043 length, P2048 height, P2067 mass). Beam (P2049) needs no qualifier disambiguation and is excluded.

| statement property | qualifier property | qualifier value QID | count | recognized | mapped field |
|---|---|---|---:|---|---|
| P2043 | P1013 | Q2358152 | 2 | False | — |
| P2043 | P518 | Q1817392 | 42 | True | lwl |
| P2043 | P518 | Q2358152 | 41 | True | loa |
| P2048 | P518 | Q244777 | 28 | True | draft |
| P2048 | P518 | Q331744 | 1 | False | — |
| P2067 | P3831 | Q5636358 | 37 | True | displacement |

Evidenced and accepted as alternative carriers of an already-accepted concept QID (added by this slice): P518 for LOA (Q2358152), P518 for LWL (Q1817392), P518 for draft (Q244777), P3831 for displacement (Q5636358). The existing accepted P642 path remains valid unchanged (see hullq.sources.wikidata.QUALIFIER_CARRIERS_BY_VERSION). P1013 and any unrecognized concept QID under P518 (e.g. Q331744) remain unsupported — not evidenced/accepted carriers.

## PER-FIELD COVERAGE — BEFORE / AFTER (exact retained 100-entity sample)

Four mutually exclusive, exhaustive states per (BoatModel, field); counts sum to the sample size for every field, in both before and after.

| field | state | before | after |
|---|---|---:|---:|
| loa | normalized_candidate_present | 0 | 41 |
| loa | source_statement_present | 0 | 0 |
| loa | unsupported_or_malformed | 64 | 16 |
| loa | no_usable_value | 36 | 43 |
| lwl | normalized_candidate_present | 0 | 42 |
| lwl | source_statement_present | 0 | 0 |
| lwl | unsupported_or_malformed | 64 | 16 |
| lwl | no_usable_value | 36 | 42 |
| beam | normalized_candidate_present | 41 | 41 |
| beam | source_statement_present | 0 | 0 |
| beam | unsupported_or_malformed | 0 | 0 |
| beam | no_usable_value | 59 | 59 |
| draft | normalized_candidate_present | 0 | 28 |
| draft | source_statement_present | 0 | 0 |
| draft | unsupported_or_malformed | 29 | 1 |
| draft | no_usable_value | 71 | 71 |
| displacement | normalized_candidate_present | 0 | 5 |
| displacement | source_statement_present | 0 | 32 |
| displacement | unsupported_or_malformed | 51 | 14 |
| displacement | no_usable_value | 49 | 49 |

## POSTGRESQL PERSISTENCE EVIDENCE — LOCAL (this implementation session)

Evidence below was measured locally by running `scripts/bootstrap/wikidata_sl0027_qualifier_semantics_correction_runner.py --persist` against a real PostgreSQL instance during implementation. Remote GitHub Actions CI independently re-runs the same step at the exact pushed head and is the authoritative external verification.

- PostgreSQL version: `PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit`
- bundles imported (first pass): 100
- bundles already-present (first pass): 0
- bundles conflict (first pass): 0
- readback mismatches: 0
- re-import (idempotency) already_imported: 100
- re-import conflict: 0
- canonical_boat_models row count after both passes: 0 (must be 0)
- canonical_boat_designs row count after both passes: 0 (must be 0)

### RESULT: zero-mutation and idempotency proof clear (local): **True**

## SCOPE CONFIRMATION

- No live Wikidata acquisition or discovery request was made; only the already-retained SLICE-0026 raw-entity claim payload was used.
- SLICE-0026 retained package files are unmodified (offline-verified before use).
- No canonical BoatModel/BoatDesign row was created or mutated.
- No FieldResolution was created.
- Existing Wikidata extraction and SLICE-0004 normalization were reused, not reimplemented; the amendment adds only evidence-backed alternative qualifier-property carriers for already-accepted concept QIDs.
- SLICE-0028 was not created or started.

