# HullQ SLICE-0021 Alternative Wikidata Discovery-Semantics Pilot Report

**Generated at:** 2026-08-24T15:29:04.154534+00:00  
**Source:** SRC_WIKIDATA_API_2026  
**Rights gate:** {'automated_ingestion': 'allowed', 'bulk_bootstrap': 'allowed'}

## IMMUTABLE HISTORICAL INPUTS (hard-asserted before live acquisition)

- Retained direct-discovery universe (SLICE-0017+0018): **1829** (must equal 1,829)
- Accepted AUTO_ADMIT universe (SLICE-0017+0018): **1770** (must equal 1,770)
- SLICE-0017 manifest: `research/bootstrap/wikidata/manifest.json` sha256=`076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845`
- SLICE-0018 manifest: `research/bootstrap/wikidata/sl0018-2500/manifest.json` sha256=`41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f`

## ROUTES (R0-R3, exactly four, hard-capped at 3,000 each)

- **R0** (`current_direct_control`, version `SLICE-0021-R0-v1`): result_count=1829 possibly_truncated=False query_sha256=`c5bbc65236deddc4...` qid_list_digest=`5cb4e85a62427bdd...` http_request_count=1
- **R1** (`sailboat_class_closure`, version `SLICE-0021-R1-v1`): result_count=1882 possibly_truncated=False query_sha256=`aa243361faa95d63...` qid_list_digest=`6d4fadf5960ab47f...` http_request_count=1
- **R2** (`legacy_sailboat_class_closure`, version `SLICE-0021-R2-v1`): result_count=0 possibly_truncated=False query_sha256=`bf1d92f4be9cf112...` qid_list_digest=`e3b0c44298fc1c14...` http_request_count=1
- **R3** (`misclassified_sailboat_class_description`, version `SLICE-0021-R3-v1`): result_count=4 possibly_truncated=False query_sha256=`9e88224c425d232d...` qid_list_digest=`f602ea97de4bdb95...` http_request_count=1

## CURRENT-R0 DRIFT (separate from alternative-route incremental yield)

- retained_direct_count: **1829**
- current_direct_count: **1829**
- retained_direct_still_present_count: **1829**
- retained_direct_absent_now_count: **0**
- new_current_direct_since_sl0018_count: **0**

## ALTERNATIVE-ROUTE INCREMENTAL YIELD (vs CURRENT R0, not merely the historical 1,829)

- R1 incremental_count: **53**
- R2 incremental_count: **0**
- R3 incremental_count: **4**

## CROSS-ROUTE OVERLAP

- total_union_count: **57**
- R1 unique_contribution_count: **53**
- R2 unique_contribution_count: **0**
- R3 unique_contribution_count: **4**
- R1 ∩ R2: 0
- R1 ∩ R3: 0
- R2 ∩ R3: 0

## ENTITY-DETAIL SAMPLE (hard-capped, deterministic)

- cap_per_route: 75, cap_global: 200
- selected_count: **57**

## IDENTITY-SIGNAL CATEGORY TOTALS (exact QID/label/alias probe only)

- `accepted_qid_overlap`: 0
- `exact_identity_signal_other_qid`: 0
- `no_exact_identity_signal`: 57
- `unresolved_exact_identity_signal`: 0

- no_exact_identity_signal means only that this bounded exact probe found no exact QID/label/alias signal. It does not prove global novelty, does not prove no corresponding HullQ identity exists, and does not authorize canonical admission.

## ROUTE DISPOSITIONS (evidence-derived recommendation only, not production authorization)

- R1: **FOLLOWUP_DISCOVERY_CANDIDATE**
- R2: **NO_INCREMENTAL_YIELD**
- R3: **FOLLOWUP_DISCOVERY_CANDIDATE**

- Every R3 (misclassified_sailboat_class_description) candidate remains a review/repair signal only in SLICE-0021 regardless of its identity-signal category or description quality. R3 membership never directly authorizes canonical admission or a production classification rule; a structured English description containing 'sailboat class' does not itself prove the item is correctly modeled as a HullQ BoatModel.

## SCOPE CONFIRMATION

- No canonical HullQ Brand/Organization/BoatModel/BoatDesign row was created, modified or deleted.
- No HullQ ID was minted for any incremental candidate.
- The accepted SLICE-0017/0018 retained manifests were read-only inputs and remain byte-unchanged.
- The production Wikidata adapter's default discovery query was not changed.
- SLICE-0022 was not created or started.

