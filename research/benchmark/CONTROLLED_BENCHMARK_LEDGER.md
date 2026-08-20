# HullQ Controlled Benchmark Ledger

**Status:** ACTIVE — SLICE-0011  
**Updated:** 2026-08-20  
**Target:** 50–100 deliberately difficult designs  
**Active re-researched designs:** 50  
**Minimum corpus gate:** REACHED — benchmark measurement still required

This ledger tracks the controlled benchmark research waves. It is not a production canonical dataset.

## Research policy

- independent web research first;
- broad source discovery with strict evidence assessment;
- preserve generation, variant, option, operating state and measurement basis;
- explicit unknown/conflict is preferable to guessed completeness;
- individual-hull listings remain hull-specific unless corroborated at design level;
- the SailboatData check happens only after independent research;
- SailboatData is a QA/reference comparison only: never HullQ evidence, never a fallback value source.

## Wave progress

| Wave | Designs | Cumulative | Main coverage added |
|---|---:|---:|---|
| 01 | 5 | 5 | generation boundaries, option-sensitive values, source-internal conflicts, configuration combinatorics, measurement basis |
| 02 | 12 | 17 | multihull geometry, board state, twin/protective-skeg relationships, named variants, successor identity, Half Load and other mass bases |
| 03 | 8 | 25 | partial skeg, era applicability, official chronology conflict, swing-keel/twin-rudder relationships, sail-area basis ambiguity |
| 04 | 8 | 33 | reference identity split, legacy multihull generations, rare centreboard/keel options, suffix semantics, weak-primary-source reconstruction |
| 05 | 8 | 41 | model-family reuse, under-split vs over-split generation risk, manufacturer heritage vs technical identity, malformed authoritative-source units |
| 06 | 9 | 50 | Mk counterexamples, class-rule semantics, twin-board deployment state, configuration × mass-basis interaction, special/tandem keel |

Detailed evidence summaries are under `research/benchmark/waves/`.

## Wave 01

- B01-001 Hallberg-Rassy 36
- B01-002 Westerly Centaur
- B01-003 RM 1180
- B01-004 Najad 34
- B01-005 J/24

## Wave 02

- B02-001 Dragonfly 32
- B02-002 OVNI 370
- B02-003 Garcia Exploration 45
- B02-004 Boréal 44.2
- B02-005 Island Packet 349
- B02-006 Corsair 880
- B02-007 Lagoon 42 (2016)
- B02-008 Nauticat 33 → 331
- B02-009 Catalina 316
- B02-010 Jeanneau Sun Odyssey 410
- B02-011 CATANA Ocean Class
- B02-012 Pogo 1

## Wave 03

- B03-001 Hallberg-Rassy 42E
- B03-002 BENETEAU Oceanis 37
- B03-003 Rustler 36
- B03-004 Seafarer 26 (McCurdy & Rhodes generation)
- B03-005 Southerly 110
- B03-006 Contessa 32
- B03-007 AMEL Super Maramu 2000
- B03-008 Moody 33 Mk I / Mk II

## Wave 04

- B04-001 Sadler 34
- B04-002 Albin Vega / Vega 27
- B04-003 Hallberg-Rassy 35 Rasmus
- B04-004 Vancouver 27
- B04-005 F-27 Sport Cruiser / Corsair F-27
- B04-006 Prout Snowgoose 37 / Snowgoose 37 Elite
- B04-007 Westerly Konsort
- B04-008 Heavenly Twins 26 → New 27 lineage

## Wave 05

- B05-001 MacGregor 26 D/S/X/M family
- B05-002 BENETEAU First 35 family
- B05-003 Moody 36 families
- B05-004 Hallberg-Rassy 352
- B05-005 Swan 36 (1967) versus ClubSwan 36
- B05-006 Catalina 36 Mk I / Mk II
- B05-007 Dehler 34 lineage
- B05-008 Hunter 37 / Hunter 37 Legend

## Wave 06

- B06-001 C&C 35 Mk I / Mk II
- B06-002 Hallberg-Rassy 312 Mk I / Mk II
- B06-003 ETAP 32s standard/tandem-keel configurations
- B06-004 Pearson 35
- B06-005 Ericson 35 Mk I / 35-2 / 35-3
- B06-006 Bristol 35.5 / 35.5C
- B06-007 Gemini 105Mc
- B06-008 J/105 builder specification versus class rules
- B06-009 Bavaria 38 and neighboring 38 identities

## Current recurring problem classes

1. generation/model-name reuse;
2. named variants with distinct physical or rig values;
3. option-sensitive displacement, ballast and draft;
4. board-up/down state;
5. folded/sailing multihull geometry;
6. proprietary/source-specific appendage terminology;
7. rudder↔skeg support/protection relationships;
8. partial-skeg evidence versus generic skeg labels;
9. primary-source internal contradiction;
10. cross-source appendage conflict;
11. design-level versus individual-hull values;
12. displacement and sail-area measurement-basis differences;
13. current-new-build versus historical values in one long-lived lineage;
14. builder chronology versus secondary/reference chronology;
15. commercial suffixes that mean anything from fitout package to material hull evolution;
16. reference-database duplicate/identity anomalies;
17. rare configurations hidden by a single baseline reference record;
18. weak/defunct-builder source chains requiring archival/community corroboration;
19. under-splitting distinct technical designs that reuse a model number;
20. over-splitting Mk/suffix evolutions that retain the same core hull/rig;
21. manufacturer marketing heritage that links technically unrelated designs;
22. authoritative-source observations with malformed unit labels;
23. reference-specific synthetic model names that must not leak into canonical naming;
24. authoritative class/rule constraints that are not nominal design values;
25. installed appendage count versus deployed appendage state;
26. configuration and measurement basis forming independent dimensions of the same physical field.

## 50-design gate

The minimum corpus size is reached. Corpus expansion now pauses unless benchmark analysis reveals a missing problem class.

Next work inside SLICE-0011:

1. measure source coverage and source-class dependence;
2. classify each design by ambiguity/conflict/review reason;
3. measure recurring identity/configuration/basis problem frequencies;
4. identify the minimum persistence/import semantics demanded repeatedly by the corpus;
5. specify the next bounded implementation slice from these findings.

Broad production ingestion remains unauthorized until that analysis and follow-on implementation gate are complete.
