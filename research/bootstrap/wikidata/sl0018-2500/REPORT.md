# HullQ SLICE-0018 Wikidata Tier-0 2,500-Window Expansion Report

**Manifest last written (generated_at):** 2026-08-21T22:55:38.451938+00:00  
**Original live acquisition (acquired_at):** 2026-08-21T20:31:34.113774+00:00  
**Last offline reclassification (classification_recomputed_at):** 2026-08-21T22:55:38.451938+00:00  
**Source:** SRC_WIKIDATA_API_2026  
**Requested limit:** 2500  
**Safety ceiling:** 3000

## BASELINE REFERENCE (immutable SLICE-0017 input)

- Baseline manifest path: `research/bootstrap/wikidata/manifest.json`
- Baseline manifest version: `0017-v4`
- Baseline sha256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`
- Baseline implementation head: `34c2de8fc99ab6babad054a4186cee168cc3a2da`
- Baseline candidate count: **1000**

## ACQUISITION PATH / VERSION (audit)

- SPARQL discovery query version: `SLICE-0017-bootstrap-v1`
- SPARQL endpoint: `https://query.wikidata.org/sparql`
- Entity API endpoint: `https://www.wikidata.org/w/api.php`
- Entity API version: `wbgetentities-labels-aliases-claims-v1`

## MEASURED FACT

- Unique QIDs returned by discovery: **1829**
- Target (2500) reached: **False**
- Overlap with accepted 1,000-QID baseline: **1000**
- Baseline QIDs absent from current discovery window: **0**
- Expansion-delta count: **829**
- Fetched entity count (delta only): **829**
- Delta candidates processed: **829**
- Acquisition failure/throttle/malformed count: **0**
- HTTP retrieval count: **18**
- Extracted record count: **829**

## CLASSIFICATION (delta only)

- AUTO_ADMIT: **805**
- REVIEW_REQUIRED: **16**
- NOT_ADMITTED: **8**
- Historical QID->HullQ-ID crosswalk count BEFORE this document's most recent (re)generation: **1772**
- Retained QID->HullQ-ID crosswalk count AFTER (baseline + delta): **1772**
- Newly minted HullQ-ID count (this generation pass): **0**
- Reused historical HullQ-ID count (this generation pass): **805**
  (Note: the minted/reused split above describes this manifest's most recent generation pass — see `acquired_at` vs `classification_recomputed_at` above. An offline `--recompute` pass legitimately reuses 100% of already-retained IDs by design/invariant; `counts.auto_admit` is the stable total of genuinely new identities this expansion introduced, independent of which pass produced this document.)
- ResearchObservation count (delta): **821**
- CanonicalEvidenceLink count (expected on replay, delta): **805**
- Expected combined canonical BoatModel count after baseline+delta replay: **1770**

### Reason breakdown

- `missing_label`: 8
- `name_collision`: 16
- `ok`: 805

## DELTA <-> BASELINE COLLISIONS (6)

- `Q4251535` collides with baseline `['Q107094022']` — shared key(s): `['l 6']`
- `Q6165346` collides with baseline `['Q1684207']` — shared key(s): `['javelin dinghy']`
- `Q6165348` collides with baseline `['Q1684207']` — shared key(s): `['javelin dinghy']`
- `Q65075596` collides with baseline `['Q106489184']` — shared key(s): `['dufour 1800']`
- `Q85744196` collides with baseline `['Q20642229']` — shared key(s): `['austral 20']`
- `Q96405967` collides with baseline `['Q104844185']` — shared key(s): `['soling world championship results']`

## DELTA <-> DELTA COLLISION CLUSTERS (6)

- `['Q5151574', 'Q5151583']` — shared key(s): `['comet']`
- `['Q60742301', 'Q60742305']` — shared key(s): `['mirage 27']`
- `['Q6165346', 'Q6165348']` — shared key(s): `['javelin dinghy']`
- `['Q96374264', 'Q96374265']` — shared key(s): `['cal 39']`
- `['Q96405963', 'Q96405965']` — shared key(s): `['soling european championship results']`
- `['Q97656865', 'Q97704143']` — shared key(s): `['phantom 14']`

## INTERPRETATION

This is the SLICE-0018 measured baseline-preserving expansion delta, not a pre-committed admission-rate target. AUTO_ADMIT delta candidates become sparse Tier-0 BoatModel identities only after offline PostgreSQL replay (see REPLAY-RESULT.json / REPLAY-REPORT.md, produced by --replay).

## POSTGRESQL REPLAY EVIDENCE — LOCAL (this implementation session)

Evidence below was measured locally by running `scripts/bootstrap/wikidata_tier0_sl0018_runner.py --replay` against a real PostgreSQL 18 instance during implementation, then embedded into this report via `--report` (offline, no network access, no PostgreSQL access performed by the report-writing step itself). Remote GitHub Actions CI independently re-runs the same `--replay` step at the exact pushed head and is the authoritative external verification — this section is local evidence, not a substitute for it.

- PostgreSQL version: `PostgreSQL 18.6 (Debian 18.6-1.pgdg13+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 14.2.0-19) 14.2.0, 64-bit`
- Baseline manifest candidates / AUTO_ADMIT: 1000 / 965
- Delta manifest candidates / AUTO_ADMIT: 829 / 805
- Expected combined bundle / admission imports: 1806 / 1770

### First-pass combined import (isolated schema)

- bundle: {'imported': 1806, 'already_present': 0, 'conflict': 0, 'error': 0, 'unexpected_status': 0}
- admission: {'imported': 1770, 'already_present': 0, 'conflict': 0, 'reference_error': 0, 'error': 0, 'unexpected_status': 0}
- expected combined imported counts match exactly: True
- baseline verified before delta applied: {'counts_match': True, 'id_set_matches': True, 'readback_mismatches': 0}
- combined readback mismatches: 0 (post-delta baseline drift: 0)
- unexpected canonical rows for non-admitted candidates: 0
- combined canonical BoatModel ID set matches exactly: True
- zero stray Brand/Organization/BoatDesign rows: True ({'canonical_brands': 0, 'canonical_organizations': 0, 'canonical_boat_designs': 0})
- exact re-import (idempotency): already_imported=3576 conflict=0 error=0

### Independent fresh-schema replay (second isolated schema)

- bundle: {'imported': 1806, 'already_present': 0, 'conflict': 0, 'error': 0, 'unexpected_status': 0}
- admission: {'imported': 1770, 'already_present': 0, 'conflict': 0, 'reference_error': 0, 'error': 0, 'unexpected_status': 0}
- baseline verified before delta applied: {'counts_match': True, 'id_set_matches': True, 'readback_mismatches': 0}
- semantic mismatches: 0 (post-delta baseline drift: 0)
- combined canonical ID set matches exactly: True
- zero stray Brand/Organization/BoatDesign rows: True ({'canonical_brands': 0, 'canonical_organizations': 0, 'canonical_boat_designs': 0})
- expected combined imported counts match exactly: True

### RESULT: all zero-tolerance conditions clear (local): **True**

Baseline drift/deletion/demotion count: 0 (post-delta baseline readback mismatches, first pass) — zero required.

## RETAINED STAGE-2 BENCHMARK

- Recommendation: **G3_PASS** (must remain exactly `G3_PASS`; measured by `scripts/benchmark/runner.py` against the same PostgreSQL instance, independent of this bootstrap manifest)

