# HullQ SLICE-0017 Wikidata Tier-0 Bootstrap Report

**Generated:** 2026-08-21T12:52:49.882220+00:00  
**Source:** SRC_WIKIDATA_API_2026  
**Requested limit:** 1000  
**Safety ceiling:** 1500

## MEASURED FACT

- Unique QIDs returned by discovery: **1000**
- Target (1000) reached: **True**
- Candidates processed: **1000**
- HTTP retrieval count: **21**
- Extracted record count: **1000**

## CLASSIFICATION

- AUTO_ADMIT: **967**
- REVIEW_REQUIRED: **18**
- NOT_ADMITTED: **15**

### Reason breakdown

- `missing_label`: 15
- `name_collision`: 18
- `ok`: 967

## INTERPRETATION

This is a first controlled broad identity bootstrap measurement, not a pre-committed admission-rate target. AUTO_ADMIT candidates become sparse Tier-0 BoatModel identities only after offline PostgreSQL replay (see REPLAY-RESULT.json / REPLAY-REPORT.md).

