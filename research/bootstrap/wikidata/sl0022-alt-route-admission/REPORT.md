# HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot Report

**Manifest last written (generated_at):** 2026-08-24T23:23:13.400563+00:00  
**Retained SLICE-0021 source-fact acquisition time (acquired_at):** 2026-08-24T15:29:04.154534+00:00  
**Last offline reclassification (classification_recomputed_at):** None  
**Source:** SRC_WIKIDATA_API_2026

## ZERO LIVE NETWORK ACQUISITION

This pilot performs no WDQS/wbgetentities/manufacturer-archive/search-engine request. Every fact below is classified purely from already-committed, immutable retained inputs.

## IMMUTABLE RETAINED INPUTS (hard-asserted before classification)

- SLICE-0017 manifest: `research/bootstrap/wikidata/manifest.json` sha256=`076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`
- SLICE-0018 manifest: `research/bootstrap/wikidata/sl0018-2500/manifest.json` sha256=`41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`
- SLICE-0021 sampled_candidates.json: `research/bootstrap/wikidata/sl0021-alt-discovery/sampled_candidates.json` git_blob_sha1=`5b56851f0c719b8dcf830fcd0416471c6c60596c`
- SLICE-0021 discovery_probe.json: `research/bootstrap/wikidata/sl0021-alt-discovery/discovery_probe.json` git_blob_sha1=`16af426991214c445a3c152aacbe56b8088958d6`
- SLICE-0021 implementation head (informational): `2cf0ab437d2347a574fd5a01b3e5577ca4c6b521`
- Accepted retained direct-discovery universe: **1829** (must equal 1,829)
- Accepted AUTO_ADMIT universe: **1770** (must equal 1,770)
- Accepted historical crosswalk: **1772** (must equal 1,772)

## CANDIDATE UNIVERSE (exactly the 57 retained SLICE-0021 incremental candidates)

- total: **57** (must equal 57)
- R1: **53** (must equal 53)
- R2: **0** (must equal 0)
- R3: **4** (must equal 4)

## DECISION TOTALS

- AUTO_ADMIT: **0** (all R1: **0**; R3: **0**, must always be 0)
- REVIEW_REQUIRED: **31**
- NOT_ADMITTED: **26**

### Reason breakdown

- `missing_label`: 26
- `r1_alternative_route_requires_review`: 27
- `r3_repair_signal_requires_review`: 4

## COLLISIONS AGAINST THE ACCEPTED 1,829-CANDIDATE BASELINE (0)

- none

## WITHIN-57 COLLISION CLUSTERS (0)

- none

## HISTORICAL CROSSWALK

- Historical crosswalk entries BEFORE this run: **1772**
- Retained crosswalk entries AFTER this run: **1772**
- Newly minted HullQ-ID count (this generation pass): **0**
- Reused historical HullQ-ID count (this generation pass): **0**

## CANONICAL ADMISSION EXPECTATION

- Accepted baseline canonical BoatModel count: **1770**
- SLICE-0022 AUTO_ADMIT count: **0**
- Expected combined canonical BoatModel count after replay: **1770**

## R1/R3 ADMISSION GOVERNANCE RULE

Per the SLICE-0022 R1 admission governance amendment (`docs/slices/SLICE-0022-r1-admission-governance-amendment.md`), R1 route membership alone is discovery-authoritative but never admission-authoritative: every structurally usable R1 (sailboat-class P31/P279* closure) candidate is `REVIEW_REQUIRED` with reason `r1_alternative_route_requires_review`, regardless of its own collision status. Every structurally usable R3 (misclassified_sailboat_class_description) candidate remains `REVIEW_REQUIRED` with reason `r3_repair_signal_requires_review`. No candidate in SLICE-0022 may ever be `AUTO_ADMIT` from either route.

## INTERPRETATION

This is a bounded admission-safety pilot over retained SLICE-0021 evidence, not production adoption of R1/R3 Wikidata discovery. The production Wikidata adapter's default discovery query is unchanged, and no R1/R3 acquisition is scheduled.

## POSTGRESQL REPLAY EVIDENCE — LOCAL (this implementation session)

Evidence below was measured locally by running `scripts/bootstrap/wikidata_sl0022_alt_route_admission_runner.py --replay` against a real PostgreSQL 18 instance during implementation. Remote GitHub Actions CI independently re-runs the same `--replay` step at the exact pushed head and is the authoritative external verification.

- PostgreSQL version: `PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit`
- Expected combined bundle / admission imports: 1837 / 1770

### First-pass combined import (isolated schema)

- bundle: {'imported': 1837, 'already_present': 0, 'conflict': 0, 'error': 0, 'unexpected_status': 0}
- admission: {'imported': 1770, 'already_present': 0, 'conflict': 0, 'reference_error': 0, 'error': 0, 'unexpected_status': 0}
- expected combined imported counts match exactly: True
- prior-baseline (0017+0018) verified before 0022 applied: {'counts_match': True, 'id_set_matches': True, 'readback_mismatches': 0}
- combined readback mismatches: 0 (prior-baseline drift: 0)
- unexpected canonical rows for non-admitted candidates: 0
- combined canonical BoatModel ID set matches exactly: True
- zero stray Brand/Organization/BoatDesign rows: True ({'canonical_brands': 0, 'canonical_organizations': 0, 'canonical_boat_designs': 0})
- exact re-import (idempotency): already_imported=3607 conflict=0 error=0

### Independent fresh-schema replay (second isolated schema)

- bundle: {'imported': 1837, 'already_present': 0, 'conflict': 0, 'error': 0, 'unexpected_status': 0}
- admission: {'imported': 1770, 'already_present': 0, 'conflict': 0, 'reference_error': 0, 'error': 0, 'unexpected_status': 0}
- semantic mismatches: 0 (prior-baseline drift: 0)
- combined canonical ID set matches exactly: True
- zero stray Brand/Organization/BoatDesign rows: True ({'canonical_brands': 0, 'canonical_organizations': 0, 'canonical_boat_designs': 0})

### RESULT: all zero-tolerance conditions clear (local): **True**

## SCOPE CONFIRMATION

- No live Wikidata (or other) network request was made.
- The accepted SLICE-0017/0018/0021 retained artifacts were read-only inputs and remain byte-unchanged.
- The production Wikidata adapter's default discovery query was not changed.
- No accepted SLICE-0017/0018 review/non-admitted candidate was resolved as a side effect.
- No Brand/Organization/BoatDesign row was created.
- SLICE-0023 was not created or started.

