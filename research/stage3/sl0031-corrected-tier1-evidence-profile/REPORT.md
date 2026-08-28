# HullQ SLICE-0031 Corrected Tier-1 Evidence Profile Report

**generated_at:** 2026-08-28T08:11:40.928631+00:00  
**boat_model_count:** 1770  

## SCOPE

Validation/selection slice only, over the exact fixed accepted 1,770-canonical-BoatModel boundary. Creates zero canonical BoatModel/BoatDesign/FieldResolution/technical-value mutation. Does not reacquire the 1,770-entity dataset, does not resolve BoatDesign applicability, and does not reinterpret the SLICE-0029 negative-control result.

## PER-FIELD CORRECTED COVERAGE (reproduces accepted SLICE-0030 result)

| field | normalized_candidate_present |
|---|---:|
| loa | 888 |
| lwl | 848 |
| beam | 891 |
| draft | 691 |
| displacement | 858 |

## NORMALIZED-FIELD-COUNT DISTRIBUTION

| fields | boat_models |
|---:|---:|
| 0 | 787 |
| 1 | 28 |
| 2 | 65 |
| 3 | 53 |
| 4 | 326 |
| 5 | 511 |

cumulative: >=3: 890, >=4: 837, all 5: 511

## PREDECESSOR / CORRECTED PRECURSOR (LOA + beam + (draft OR displacement))

- predecessor (pre-SLICE-0030): 607 / 1770 = 34.2938%
- corrected (post-SLICE-0030): 817 / 1770 = 46.1582%
- delta: 210 BoatModels (11.8644 percentage points)
- overlap decomposition: {'draft_only': 55, 'displacement_only': 213, 'both': 549}

## STRONG TECHNICAL-EVIDENCE SUBSETS

- LOA+beam+draft+displacement: 549
- LOA+LWL+beam+(draft OR displacement): 753
- all five fixed fields: 511
- >=4/5 normalized, no disagreement diagnostic: 831

## POSITIVE-CONTROL CANDIDATE POOL

- eligible candidates: 784
- retained pool size: 20 (limit 20)
- pool result: **POSITIVE_CONTROL_POOL_AVAILABLE**
- excluded SLICE-0029 negative-control QIDs: ['Q5051252', 'Q5051253']

| rank | hullq_id | qids | normalized_field_count | draft+displacement | LWL |
|---:|---|---|---:|:---:|:---:|
| 1 | BM_WDT0_003ba28d4cd143d68c28e57899a3ed73 | Q104861437 | 5 | True | True |
| 2 | BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb | Q104829866 | 5 | True | True |
| 3 | BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60 | Q60521258 | 5 | True | True |
| 4 | BM_WDT0_041b206a55fe490785620b29a2af443a | Q85753944 | 5 | True | True |
| 5 | BM_WDT0_074f8ccc869342d2b392e9a315709b1b | Q85753415 | 5 | True | True |
| 6 | BM_WDT0_0773da973b2c47dd84dc1e271b3c16fd | Q60755809 | 5 | True | True |
| 7 | BM_WDT0_07e7ebd154244b9cb8ccaa61589af3e4 | Q105742651 | 5 | True | True |
| 8 | BM_WDT0_08f47683f0b9435ca508cc7cc7e1e602 | Q60521277 | 5 | True | True |
| 9 | BM_WDT0_090a42a1e08641da98a840cd97b671ce | Q55071986 | 5 | True | True |
| 10 | BM_WDT0_0aeb784a1cef4706982266379b9cc1e0 | Q5463514 | 5 | True | True |
| 11 | BM_WDT0_0b14fb0af9f643d993fc30f395cb32d8 | Q105474389 | 5 | True | True |
| 12 | BM_WDT0_0bd15dbd17cf44eea09203f4a6bac262 | Q7321000 | 5 | True | True |
| 13 | BM_WDT0_0c19ffaccdae401180f2d6ebeae99c39 | Q65076969 | 5 | True | True |
| 14 | BM_WDT0_0cdf302bff774223b68cf610ea754ea8 | Q105753294 | 5 | True | True |
| 15 | BM_WDT0_0d3dc025a4f64baea4f61b644fb94722 | Q60521224 | 5 | True | True |
| 16 | BM_WDT0_0d7b18ff7c14471e8dbc17ae665dcfaf | Q104902894 | 5 | True | True |
| 17 | BM_WDT0_0e8528d46b5b44caa5e2eae217215c8a | Q106075875 | 5 | True | True |
| 18 | BM_WDT0_10717b8f0c114505aed1bd2011f7f38e | Q60740478 | 5 | True | True |
| 19 | BM_WDT0_11226d16987e4d86bf35fbcced51fc0f | Q66737997 | 5 | True | True |
| 20 | BM_WDT0_1184b9a1439c42689b3147977632c75f | Q60743939 | 5 | True | True |

A positive pool means only that technically strong BoatModel-scoped source evidence exists for later applicability research; it is not authorization to research all listed candidates externally and does not establish a BoatDesign generation boundary, cleared primary source, or promotable canonical value for any listed BoatModel.

## CAL-01 / LAUNCH-THRESHOLD BOUNDARY

This report retains the corrected evidence measurements as a calibration input only. It does not relabel research evidence as canonical basic-searchable coverage, does not declare the D2/D2b launch threshold met, and does not declare G4 passed.

## SCOPE CONFIRMATION

- No discovery/SPARQL/live acquisition request was made; only the fixed accepted SLICE-0028/0030 retained raw claims were replayed offline.
- No canonical BoatModel/BoatDesign row was created or mutated.
- No FieldResolution was created.
- SLICE-0026/0027/0028/0029/0030 retained artifacts were not modified.
- SLICE-0032 was not created or started.
