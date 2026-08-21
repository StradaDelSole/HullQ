# HullQ SLICE-0018 Wikidata Tier-0 2,500-Window Expansion Report

**Manifest last written (generated_at):** 2026-08-21T21:09:23.210095+00:00  
**Original live acquisition (acquired_at):** 2026-08-21T20:31:34.113774+00:00  
**Last offline reclassification (classification_recomputed_at):** 2026-08-21T21:09:23.210095+00:00  
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
- Retained QID->HullQ-ID crosswalk count (baseline + delta): **1772**
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

PostgreSQL version, combined baseline+delta replay counts and fresh-schema semantic mismatch count are PENDING until the retained manifest has been replayed against real PostgreSQL 18 (db-integration CI or a local --replay run).

