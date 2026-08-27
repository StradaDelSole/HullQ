# HullQ SLICE-0030 Wikidata Mass-Unit QID Correction Report

**generated_at:** 2026-08-27T21:01:39.800270+00:00  
**fixed SLICE-0028 input qid_count:** 1770  

## SCOPE

Mass-unit-identity correction + offline full-boundary replay only. Does not reacquire the 1,770-QID dataset, does not create/mutate canonical BoatModel/BoatDesign identity, does not create a FieldResolution, and does not reinterpret the SLICE-0029 applicability result.

## CORRECTED MASS-UNIT MAP

| QID | intended unit | before (legacy) | after (default) |
|---|---|---|---|
| Q11570 | kilogram | recognized | recognized (unchanged) |
| Q41803 | gram | not recognized | recognized |
| Q191118 | tonne/metric tonne | not recognized | recognized |
| Q100995 | pound | not recognized | recognized |
| Q12152 | (not a unit — myocardial infarction) | recognized (bug) | not recognized |
| Q11369 | (not a unit — molecule) | recognized (bug) | not recognized |
| Q37795 | (not a unit — Romanian Raven Shepherd Dog) | recognized (bug) | not recognized |

See `unit_qid_assessment.json` for the positively-verified identity evidence.

## BEFORE/AFTER COVERAGE (fixed SLICE-0028 full-boundary entities)

| field | before normalized | after normalized | before source_only | after source_only |
|---|---|---|---|---|
| loa | 888 | 888 | 0 | 0 |
| lwl | 848 | 848 | 0 | 0 |
| beam | 891 | 891 | 1 | 1 |
| draft | 691 | 691 | 0 | 0 |
| displacement | 66 | 858 | 792 | 0 |

**displacement_normalized_candidate_delta:** 792  
**non_displacement_fields_unchanged:** True  

## SCOPE CONFIRMATION

- No discovery/SPARQL request was made; only the fixed accepted SLICE-0028 retained raw claims were replayed offline.
- No canonical BoatModel/BoatDesign row was created or mutated.
- No FieldResolution was created.
- SLICE-0026/0027/0028/0029 retained artifacts were not modified.
- SLICE-0031 was not created or started.
