# HullQ SLICE-0023 Wikimedia Category Identity-Lead Discovery Pilot Report

**Generated at:** 2026-08-25T14:08:19.962511+00:00  
**Source:** SRC_WIKIPEDIA_API_2026  
**Rights gate:** {'wikipedia_research_lead': 'allowed', 'wikipedia_automated_ingestion_clearance': 'allowed', 'wikidata_bulk_bootstrap': 'allowed', 'wikidata_automated_ingestion': 'allowed'}

## IMMUTABLE COMPARISON BOUNDARIES (hard-asserted before live acquisition)

- accepted direct-discovery candidate universe: **1829** (must equal 1,829)
- accepted canonical BoatModel universe: **1770** (must equal 1,770)
- accepted historical QID -> HullQ-ID mappings: **1772** (must equal 1,772)
- accepted SLICE-0021 alternative-route union: **57** (must equal 57)
- SLICE-0017 manifest sha256: `076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`
- SLICE-0018 manifest sha256: `41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`
- SLICE-0021 discovery_probe.json Git blob sha1: `16af426991214c445a3c152aacbe56b8088958d6`
- SLICE-0021 sampled_candidates.json Git blob sha1: `5b56851f0c719b8dcf830fcd0416471c6c60596c`

## FIXED CATEGORY ROUTES (exactly three, no recursion/expansion)

- **Keelboats**: member_count=930 hard_cap=2000 complete=True request_count=2 continuation_count=1
- **Catamarans**: member_count=116 hard_cap=250 complete=True request_count=1 continuation_count=0
- **Trimarans**: member_count=86 hard_cap=200 complete=True request_count=1 continuation_count=0

- combined pre-dedup membership: **1132** (cap 2,450)
- unique page count: **1131**
- cross-category duplicate page IDs: **1**
- duplicate QIDs (same QID via >1 page): **0**

## OVERLAP CATEGORIES

- accepted_direct_qid_overlap: **717**
- retained_alternative_qid_overlap: **4**
- incremental_qid_lead: **409**
- no_wikidata_qid: **1**

## EXACT IDENTITY-SIGNAL TOTALS (trim+casefold-only probe)

- `exact_signal_other_qid`: 0
- `no_exact_signal`: 414
- `unresolved_structural`: 0

## DETERMINISTIC QUALITY SAMPLE (SHA256-ordered, no cross-stratum backfill)

- cap_by_stratum: {'Trimarans': 30, 'Catamarans': 30, 'Keelboats': 90}, total_cap: 150
- selected_count: **150**

## QUALITY REVIEW TOTALS

- `ambiguous`: 29 (19.3333%)
- `obvious_out_of_scope`: 19 (12.6667%)
- `plausible_model_or_class_lead`: 102 (68.0%)

- total_sampled: **150**

## REQUEST CEILINGS

- wikipedia_request_count: **27** (ceiling 75)
- wikidata_request_count: **3** (ceiling 10)
- total_request_count: **30** (ceiling 85)

## RECOMMENDATION (precommitted, mechanical rule)

- **FOLLOWUP_VERIFICATION_CANDIDATE**

## SOURCE-RIGHTS / ACCESS CONFIRMATION

- Wikipedia is used strictly as a research-lead surface: category name, page ID, namespace, page title, canonical URL and linked Wikidata QID only.
- No Wikipedia article prose, infobox value, table, image or reference content became HullQ evidence.
- Wikidata CC0 quality-sample context is bounded to the deterministic <=150-QID sample; no broad WDQS/SPARQL discovery was run.
- Rights evidence URLs reviewed: ['https://foundation.wikimedia.org/wiki/Terms_of_Use', 'https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy', 'https://www.mediawiki.org/wiki/API:Categorymembers', 'https://www.mediawiki.org/wiki/API:Licensing']

## SCOPE CONFIRMATION

- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified or deleted.
- No HullQ ID was minted for any lead.
- The accepted SLICE-0017/0018/0021 retained manifests were read-only inputs and remain byte-unchanged.
- The production Wikidata adapter's default discovery query was not changed and Wikipedia/Wikimedia was not added to production discovery.
- No prior SLICE-0017/0018/0021/0022 review queue was resolved as a side effect.
- Stage-3.3 was not started and SLICE-0024 was not created/started.

