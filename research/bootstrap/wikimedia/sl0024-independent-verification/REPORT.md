# HullQ SLICE-0024 Wikimedia Lead Independent Identity-Verification Pilot Report

**Generated at:** 2026-08-25T00:00:00+00:00  
**Type:** DESIGN_RESEARCH -- research-only, no canonical/production mutation

## Pinned SLICE-0023/0018 boundaries (reproduced before candidate selection)

- `quality_sample_git_blob_sha1`: e26fde36c487f54344e4392ed7f3d7e735f07abf
- `discovery_manifest_git_blob_sha1`: 9ddc5483d8b3d34e97aa36d5d72bd28fefe19c0e
- `source_assessment_git_blob_sha1`: d025ca31574d38b2bab03fd8211859c10440dd4b
- `unique_incremental_qid_lead_count`: 409
- `quality_sample_total`: 150
- `quality_tag_counts`: {'plausible_model_or_class_lead': 102, 'obvious_out_of_scope': 19, 'ambiguous': 29}
- `canonical_boat_model_count`: 1770
- `historical_crosswalk_count`: 1772

## Deterministic 18/6/6 sample

- stratum caps: {'plausible_model_or_class_lead': 18, 'ambiguous': 6, 'obvious_out_of_scope': 6}
- selected_count: **30**

## Subject outcome totals

- `in_scope_identity`: 11
- `out_of_scope`: 8
- `conflict`: 0
- `unresolved`: 11

## Evidence strength totals

- `strong_source`: 14
- `two_independent_specialist_sources`: 1
- `insufficient`: 15

## Threshold set (24 prior plausible+ambiguous candidates)

- independently supported in_scope_identity: **11** (threshold >=12)
- strong_source in_scope_identity: **10** (threshold >=8)
- median combined actions (independently supported): **2.0** (ceiling <=4)

## Research-action totals

- search_query_count_total: **50** (ceiling 60)
- source_page_evaluation_count_total: **71** (ceiling 120)
- combined_research_action_count_total: **121** (ceiling 180)
- count hitting per-candidate budget cap: 9
- access-blocked source-page count: 29
- conflicts/unresolved count: 11

## Per-candidate research-action ceiling compliance

- any_per_candidate_ceiling_exceeded: **True**
  - `Q119855214`: search_query_count=3 exceeds ceiling 2
  - `Q30681833`: search_query_count=3 exceeds ceiling 2

## Source-class distribution

- `manufacturer_shipyard`: 17
- `designer_naval_architect`: 10
- `class_association`: 1
- `owners_association`: 2
- `museum_archive`: 2
- `high_quality_specialist_documentation`: 14
- `non_qualifying`: 25

## Recommendation (precommitted, mechanical rule)

- **LOW_INDEPENDENT_VERIFICATION_YIELD**

## Process deviations

- `Q119855214`: Three discovery-search queries were actually issued for this candidate -- one more than the fixed 2-query-per-candidate ceiling in the controlling slice's external research boundary. This was not caught during original assembly (which incorrectly excluded the third query from the retained action ledger) and was corrected during independent review. All three queries are now retained and mechanically counted in this row's search_query_count/combined_action_count and in the global action totals below; this candidate's per-candidate search-query ceiling is exceeded (search_query_count=3 > 2). The third query's surfaced lead (a Finot-Conq designer-site redirect) was never fetched/evaluated and forms no part of the evidence basis for this candidate's subject_outcome/evidence_strength.
- `Q30681833`: Three discovery-search queries were actually issued for this candidate -- one more than the fixed 2-query-per-candidate ceiling in the controlling slice's external research boundary. This was not caught during original assembly (which incorrectly excluded the third query from the retained action ledger) and was corrected during independent review. All three queries are now retained and mechanically counted in this row's search_query_count/combined_action_count and in the global action totals below; this candidate's per-candidate search-query ceiling is exceeded (search_query_count=3 > 2). The third query's surfaced lead (Birdon's official site) was never fetched/evaluated and forms no part of the evidence basis for this candidate's subject_outcome/evidence_strength.

## Scope confirmation

- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified or deleted.
- No HullQ ID was minted for any candidate.
- Wikipedia/Wikidata/SailboatData/search-result/generative-summary/forum/marketplace content was used only as discovery, never as qualifying verification evidence.
- No newly evaluated external source was granted production/bulk/automation clearance.
- Stage-3.3 enrichment was not started and SLICE-0025 was not created/started.

