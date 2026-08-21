# HullQ SLICE-0017 Wikidata Tier-0 Bootstrap Report

**Generated:** 2026-08-21T13:45:53.809506+00:00  
**Source:** SRC_WIKIDATA_API_2026  
**Requested limit:** 1000  
**Safety ceiling:** 1500

## ACQUISITION PATH / VERSION (audit)

- SPARQL discovery query version: `SLICE-0017-bootstrap-v1`
- SPARQL endpoint: `https://query.wikidata.org/sparql`
- Entity API endpoint: `https://www.wikidata.org/w/api.php`
- Entity API version: `wbgetentities-labels-aliases-claims-v1`

## MEASURED FACT

- Unique QIDs returned by discovery: **1000**
- Target (1000) reached: **True**
- Fetched entity count: **1000**
- Candidates processed: **1000**
- Acquisition failure/throttle/malformed count: **0**
- HTTP retrieval count: **21**
- Extracted record count: **1000**

## CLASSIFICATION

- AUTO_ADMIT: **965**
- REVIEW_REQUIRED: **20**
- NOT_ADMITTED: **15**
- Retained QID->HullQ-ID crosswalk count: **967**
- ResearchObservation count: **985**
- CanonicalEvidenceLink count (expected on replay): **965**

### Reason breakdown

- `missing_label`: 15
- `name_collision`: 20
- `ok`: 965

## COLLISION CLUSTERS (10 complete cluster(s))

- `['Q10496824', 'Q106587830']` — shared key(s): `['flipper']`
- `['Q106436033', 'Q106522259']` — shared key(s): `['etap 28']`
- `['Q106453107', 'Q1931490']` — shared key(s): `['micro']`
- `['Q106489208', 'Q106489209']` — shared key(s): `['dufour 40 performance']`
- `['Q107093883', 'Q2943204']` — shared key(s): `['cavale']`
- `['Q107093951', 'Q107093955']` — shared key(s): `['malibu']`
- `['Q107093971', 'Q107093972']` — shared key(s): `['magnum nova']`
- `['Q107094005', 'Q107094007']` — shared key(s): `['cd1 d2']`
- `['Q109650429', 'Q2461915']` — shared key(s): `['j-80']`
- `['Q119149935', 'Q28162935']` — shared key(s): `['swan 55 frers']`

## INTERPRETATION

This is a first controlled broad identity bootstrap measurement, not a pre-committed admission-rate target. AUTO_ADMIT candidates become sparse Tier-0 BoatModel identities only after offline PostgreSQL replay (see REPLAY-RESULT.json / REPLAY-REPORT.md, produced by --replay).

PostgreSQL version, first-replay/re-replay counts and fresh-schema semantic mismatch count are PENDING until the retained manifest has been replayed against real PostgreSQL 18 (db-integration CI or a local --replay run).

