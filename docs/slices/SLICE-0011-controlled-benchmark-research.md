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

### Wave 01 — complete research pass

5 designs / 58 structured observations:

- Hallberg-Rassy 36
- Westerly Centaur
- RM 1180
- Najad 34
- J/24

### Wave 02 — complete research pass

12 designs / 138 structured observations:

- Dragonfly 32
- OVNI 370
- Garcia Exploration 45
- Boréal 44.2
- Island Packet 349
- Corsair 880
- Lagoon 42 (2016 generation)
- Nauticat 33 → 331
- Catalina 316
- Jeanneau Sun Odyssey 410
- CATANA Ocean Class
- Pogo 1

Current actively researched benchmark count: **17 designs**.

## Measurements to build

Track identity-resolution success, source-discovery success, primary-source coverage, HullQ-critical-field completeness, explicit unresolved rate, conflict rate, source-internal conflict rate, generation/variant ambiguity, appendage ambiguity, measurement-basis ambiguity, dependence on community/secondary evidence, reference-comparison outcomes and estimated review reasons/rates. Add runtime repeatability and false-normalization metrics once an importer executes the corpus.

## Out of scope

This slice does not authorize broad production ingestion, production PostgreSQL schema work, persistence implementation, query/search semantics, public API/frontend work, marketplace ingestion, accounts/alerts, or treating reference comparison data as production evidence.

## Exit gate

Close SLICE-0011 only when the 50–100-design corpus covers the intended difficult classes, evidence remains reproducible and source-linked, major ambiguity/conflict classes have measured frequencies, and the next persistence/import slice can be specified from observed evidence rather than assumptions.
