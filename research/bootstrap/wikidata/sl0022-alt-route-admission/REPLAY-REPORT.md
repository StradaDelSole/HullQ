# HullQ SLICE-0022 Retained Alternative-Route Tier-0 Admission Safety Pilot Replay Report

**Run timestamp:** 2026-08-24T23:01:06.726289+00:00  
**PostgreSQL version:** PostgreSQL 18.6 on x86_64-windows, compiled by msvc-19.44.35228, 64-bit  
**Prior baseline (0017+0018) candidates/auto_admit:** 1829/1770  
**SLICE-0022 candidates/auto_admit:** 57/0  
**Expected combined bundle/admission imports:** 1837/1770

Both passes below import the accepted SLICE-0017 baseline then the accepted SLICE-0018 delta first, verify that combined prior baseline, then import the retained SLICE-0022 delta second, in their own newly-created, migrated-from-zero, isolated PostgreSQL schema.

## PASS 1 — FIRST-PASS COMBINED IMPORT (isolated schema)

- bundle (combined): {'imported': 1837, 'already_present': 0, 'conflict': 0, 'error': 0, 'unexpected_status': 0}
- admission (combined): {'imported': 1770, 'already_present': 0, 'conflict': 0, 'reference_error': 0, 'error': 0, 'unexpected_status': 0}
- expected combined imported counts match exactly: True
- prior baseline (0017+0018) verified before 0022 applied: {'counts_match': True, 'id_set_matches': True, 'readback_mismatches': 0}
- wall clock: 9.1264s

## DEEP READBACK VERIFICATION (same isolated schema as pass 1)

- semantic mismatches (prior baseline + 0022): 0
- prior-baseline drift mismatches: 0
- unexpected canonical rows for non-admitted candidates: 0
- combined canonical BoatModel ID set matches exactly: True
- zero stray Brand/Organization/BoatDesign rows: True ({'canonical_brands': 0, 'canonical_organizations': 0, 'canonical_boat_designs': 0})

## EXACT RE-REPLAY (IDEMPOTENCY, same isolated schema)

- already_imported/conflict/error: 3607/0/0
- wall clock: 9.0625s

## PASS 2 — INDEPENDENT FRESH-SCHEMA REPLAY (second isolated schema, full combined semantic graph equality)

- bundle (combined): {'imported': 1837, 'already_present': 0, 'conflict': 0, 'error': 0, 'unexpected_status': 0}
- admission (combined): {'imported': 1770, 'already_present': 0, 'conflict': 0, 'reference_error': 0, 'error': 0, 'unexpected_status': 0}
- prior baseline verified before 0022 applied: {'counts_match': True, 'id_set_matches': True, 'readback_mismatches': 0}
- semantic mismatches: 0
- prior-baseline drift mismatches: 0
- combined canonical ID set matches exactly: True
- zero stray Brand/Organization/BoatDesign rows: True ({'canonical_brands': 0, 'canonical_organizations': 0, 'canonical_boat_designs': 0})
- expected combined imported counts match exactly: True

## RESULT: all zero-tolerance conditions clear: **True**

