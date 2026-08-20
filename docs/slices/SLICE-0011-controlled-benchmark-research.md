# SLICE-0011 — Controlled Real-Web Benchmark Research

**ID:** SLICE-0011  
**Type:** DESIGN_RESEARCH  
**Status:** IN_PROGRESS  
**Stage:** 2.10–2.11  
**Depends on:** SLICE-0010 accepted / DONE  
**Research owner:** project owner + ChatGPT/master research

## Objective

Build a controlled 50–100-design benchmark from independently researched web evidence. Use the corpus to test HullQ's accepted identity, provenance, measurement, configuration and derived-metric foundations against real sailboat-data conditions before persistence and broad ingestion are frozen.

This is a research slice. Claude Code is not the web-research agent; it remains the implementation agent for later bounded import, persistence and processing work.

## Research method

```text
selected difficult design
→ broad independent web research
→ source ranking
→ raw observation and context capture
→ corroboration / conflict detection
→ post-hoc reference comparison
→ structured benchmark evidence
→ benchmark measurements and architecture findings
```

Search broadly across manufacturer/shipyard pages, original brochures and manuals, designers, class and owners associations, archives, specialist publications/databases, reputable broker documentation, sailing forums, owners groups, refit/restoration material and other useful web leads.

**Source breadth is intentionally broad; canonical confidence is intentionally strict.**

For every useful observation preserve source identity, URL/document identity, retrieval date, raw value or wording, unit, measurement basis, generation/variant/option/state context, confidence and unresolved/conflict status where relevant. Partial records are valid; invented completeness is not.

Individual-hull/broker records may be used for discovery and corroboration, but they remain hull-specific unless independent evidence supports projection to design level.

## Reference comparison rule

SailboatData is used only after independent HullQ research as a QA/reference comparison.

- no SailboatData value becomes HullQ evidence;
- no missing HullQ field is filled from SailboatData;
- no FieldEvidence is created from SailboatData;
- SailboatData does not resolve conflicts;
- comparison output stores only outcomes such as `match`, `partial_match`, `conflict`, `basis_difference`, `identity_disambiguation_required` or `no_reference_record_found`;
- a mismatch is a trigger for further independent research where useful.

## Benchmark selection

Cover deliberately difficult cases across monohulls/catamarans/trimarans, reused model names, generations and named variants, keel/centreboard/daggerboard options, single/twin rudders, skeg relationships, old or defunct builders, modern configurators, measurement-basis differences, internal source contradictions, cross-source conflicts and semi-custom configurations.

The SLICE-0002 seed sample is a selection aid only. Benchmark records are re-researched in the current wave.

## Current progress

| Wave | Designs | Cumulative | Main focus |
|---|---:|---:|---|
| Wave 01 | 5 | 5 | generation/options/conflicts/basis |
| Wave 02 | 12 | 17 | multihulls, board state, named variants, appendage relationships |
| Wave 03 | 8 | 25 | partial skeg, chronology, era applicability, sail-area basis |
| Wave 04 | 8 | 33 | identity split, suffix semantics, legacy multihull generations, rare keel options |
| Wave 05 | 8 | 41 | model-family reuse, under/over-splitting risk, technical lineage vs marketing lineage, malformed authoritative observations |

Current actively re-researched benchmark count: **41 designs**.

Detailed wave evidence:

- `research/benchmark/waves/WAVE-01-summary.md`
- `research/benchmark/waves/WAVE-02-summary.md`
- `research/benchmark/waves/WAVE-03-summary.md`
- `research/benchmark/waves/WAVE-04-summary.md`
- `research/benchmark/waves/WAVE-05-summary.md`
- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`

### Wave 01

Hallberg-Rassy 36; Westerly Centaur; RM 1180; Najad 34; J/24.

### Wave 02

Dragonfly 32; OVNI 370; Garcia Exploration 45; Boréal 44.2; Island Packet 349; Corsair 880; Lagoon 42 (2016); Nauticat 33 → 331; Catalina 316; Jeanneau Sun Odyssey 410; CATANA Ocean Class; Pogo 1.

### Wave 03

Hallberg-Rassy 42E; BENETEAU Oceanis 37; Rustler 36; Seafarer 26 (McCurdy & Rhodes); Southerly 110; Contessa 32; AMEL Super Maramu 2000; Moody 33 Mk I / Mk II.

### Wave 04

Sadler 34; Albin Vega / Vega 27; Hallberg-Rassy 35 Rasmus; Vancouver 27; F-27 Sport Cruiser / Corsair F-27; Prout Snowgoose 37 / Snowgoose 37 Elite; Westerly Konsort; Heavenly Twins 26 → New 27 lineage.

### Wave 05

MacGregor 26 D/S/X/M family; BENETEAU First 35 family; Moody 36 families; Hallberg-Rassy 352; Swan 36 versus ClubSwan 36; Catalina 36 Mk I/Mk II; Dehler 34 lineage; Hunter 37/Hunter 37 Legend.

## Measurements to build

Track identity-resolution success, source-discovery success, primary-source coverage, HullQ-critical-field completeness, explicit unresolved rate, conflict rate, source-internal conflict rate, generation/variant ambiguity, appendage ambiguity, measurement-basis ambiguity, dependence on community/secondary evidence, reference-comparison outcomes and estimated review reasons/rates. Add runtime repeatability and false-normalization metrics once an importer executes the corpus.

## Findings already forcing architecture attention

The first 41 designs repeatedly demonstrate that:

- one scalar per physical concept is insufficient;
- generation identity cannot be inferred from model strings alone;
- model number + builder is not globally unique over time;
- suffixes may mean fitout-only changes, design evolution or identity-critical unrelated generations;
- both under-splitting and over-splitting are real identity risks;
- manufacturer marketing lineage must remain distinct from technical BoatDesign lineage;
- configuration options can change displacement/ballast as well as draft;
- rudder, skeg, keel and board axes must remain independent;
- multihull folded/sailing geometry and board state are first-class data;
- source measurement basis must survive normalization;
- current and historical design-level facts need applicability/era context;
- source authority does not guarantee that every observation is syntactically/semantically valid;
- reference datasets can contain identity duplication/anomalies as well as useful QA agreement;
- weak/defunct-builder records can be researched, but confidence depends more heavily on archival/community corroboration.

## Out of scope

This slice does not authorize broad production ingestion, production PostgreSQL schema work, persistence implementation, query/search semantics, public API/frontend work, marketplace ingestion, accounts/alerts, or treating reference comparison data as production evidence.

## Exit gate

Close SLICE-0011 only when the 50–100-design corpus covers the intended difficult classes, evidence remains reproducible and source-linked, major ambiguity/conflict classes have measured frequencies, and the next persistence/import slice can be specified from observed evidence rather than assumptions.
