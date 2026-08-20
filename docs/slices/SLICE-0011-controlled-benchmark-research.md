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
| Wave 06 | 9 | 50 | Mk counterexamples, rule semantics, twin-board deployment state, special/tandem keel, configuration × mass-basis interaction |

**Minimum corpus gate reached: 50 designs.**

Corpus expansion now pauses unless measurement shows a material missing problem class. SLICE-0011 remains `IN_PROGRESS` because the benchmark measurements and follow-on persistence/import specification are still required.

Detailed wave evidence:

- `research/benchmark/waves/WAVE-01-summary.md`
- `research/benchmark/waves/WAVE-02-summary.md`
- `research/benchmark/waves/WAVE-03-summary.md`
- `research/benchmark/waves/WAVE-04-summary.md`
- `research/benchmark/waves/WAVE-05-summary.md`
- `research/benchmark/waves/WAVE-06-summary.md`
- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`

## Measurements now required

Track and record at least:

- identity-resolution / generation-ambiguity incidence;
- source-discovery success and primary/authoritative-source coverage;
- dependence on owners/community/broker/secondary evidence;
- HullQ-critical-field completeness at useful confidence;
- explicit unresolved/conflict frequency;
- source-internal conflict frequency;
- option/variant/state incidence;
- appendage ambiguity and relationship complexity;
- displacement/sail-area/other measurement-basis ambiguity;
- temporal/applicability-scope incidence;
- reference-comparison outcomes and anomaly classes;
- likely human-review reasons and estimated review routing.

Runtime repeatability, automated-acceptance rate, false-normalization rate, processing cost and actual human minutes per review require an executable importer and therefore belong to the next implementation/benchmark-execution wave rather than being invented from manual research.

## Findings already forcing architecture attention

The 50-design corpus repeatedly demonstrates that:

- one scalar per physical concept is insufficient;
- generation identity cannot be inferred from model strings alone;
- model number + builder is not globally unique over time;
- suffixes may mean fitout-only changes, design evolution, configuration, or identity-critical unrelated generations;
- both under-splitting and over-splitting are real identity risks;
- manufacturer marketing lineage must remain distinct from technical BoatDesign lineage;
- configuration options can change displacement/ballast/sail area as well as draft;
- rudder, skeg, keel and board axes must remain independent;
- installed appendage count and deployed operating state are different concepts;
- multihull folded/sailing geometry and board state are first-class data;
- source measurement basis must survive normalization;
- nominal specification, class-rule constraint/tolerance, as-measured value and individual-hull observation are different evidence semantics;
- current and historical design-level facts need applicability/era context;
- source authority does not guarantee that every observation is syntactically/semantically valid;
- reference datasets can contain identity duplication/anomalies as well as useful QA agreement;
- weak/defunct-builder records can be researched, but confidence depends more heavily on archival/community corroboration.

## Out of scope

This slice does not authorize broad production ingestion, production PostgreSQL schema work, persistence implementation, query/search semantics, public API/frontend work, marketplace ingestion, accounts/alerts, or treating reference comparison data as production evidence.

## Exit gate

Close SLICE-0011 only when:

1. the corpus covers the intended difficult classes — **minimum size reached**;
2. evidence remains reproducible and source-linked;
3. major ambiguity/conflict classes have measured frequencies;
4. the minimum persistence/import semantics demanded by the evidence are explicitly derived;
5. the next bounded implementation slice can be specified from observed evidence rather than assumptions.
