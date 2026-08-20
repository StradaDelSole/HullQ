# SLICE-0011 — Controlled Real-Web Benchmark Research

**ID:** SLICE-0011  
**Type:** DESIGN_RESEARCH  
**Status:** DONE  
**Stage:** 2.10–2.11  
**Depends on:** SLICE-0010 accepted / DONE  
**Research owner:** project owner + ChatGPT/master research

## Final acceptance

SLICE-0011 was explicitly accepted by the project owner after independent closure review and exact-head CI verification.

Acceptance evidence:

- final accepted PR head: `9f1859fe9762e05bd2a5be57c550f255be302c9b`;
- GitHub Actions CI run #151: PASS on that exact head;
- Ubuntu quality: PASS;
- Windows quality: PASS;
- dependency audit: PASS;
- changed-file scope at acceptance: 18 files, all under `docs/` or `research/`;
- independent closure review found no remaining blocking scope/data-governance issue after the documented pre-canonical ResearchObservation and reference-crosscheck corrections;
- explicit project-owner acceptance: 2026-08-20;
- PR #22 merged on 2026-08-20;
- merge commit: `668e91937d27dc9c70760301b92ce0ded41abb2f`.

SLICE-0012 is unblocked by this acceptance but still requires a separate READY status before implementation starts.

## Objective

Build a controlled 50–100-design benchmark from independently researched web evidence. Use the corpus to test HullQ's accepted identity, provenance, measurement, configuration and derived-metric foundations against real sailboat-data conditions before persistence and broad ingestion are frozen.

This was a research slice. Claude Code was not the web-research agent; it remains the implementation agent for later bounded import, persistence and processing work.

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

Search covered manufacturer/shipyard pages, original brochures and manuals, designers, class and owners associations, archives, specialist publications/databases, reputable broker documentation, sailing forums, owners groups, refit/restoration material and other useful web leads.

**Source breadth was intentionally broad; canonical confidence remained strict.**

For every useful observation, the research preserved source identity, URL/document identity, retrieval date, raw value or wording, unit, measurement basis, generation/variant/option/state context, confidence and unresolved/conflict status where relevant. Partial records were valid; invented completeness was not.

Individual-hull/broker records were used for discovery and corroboration only and remained hull-specific unless independent evidence supported projection to design level.

## Reference comparison rule

SailboatData was used only after independent HullQ research as a QA/reference comparison.

- no SailboatData value became HullQ evidence;
- no missing HullQ field was filled from SailboatData;
- no FieldEvidence was created from SailboatData;
- SailboatData did not resolve conflicts;
- retained comparison output stores outcome/anomaly classes rather than SailboatData field values;
- a mismatch was a trigger for further independent research where useful.

## Completed research corpus

| Wave | Designs | Cumulative | Main focus |
|---|---:|---:|---|
| Wave 01 | 5 | 5 | generation/options/conflicts/basis |
| Wave 02 | 12 | 17 | multihulls, board state, named variants, appendage relationships |
| Wave 03 | 8 | 25 | partial skeg, chronology, era applicability, sail-area basis |
| Wave 04 | 8 | 33 | identity split, suffix semantics, legacy multihull generations, rare keel options |
| Wave 05 | 8 | 41 | model-family reuse, under/over-splitting risk, technical lineage vs marketing lineage, malformed authoritative observations |
| Wave 06 | 9 | 50 | Mk counterexamples, rule semantics, twin-board deployment state, special/tandem keel, configuration × mass-basis interaction |

**Minimum corpus gate reached: 50 designs.** Corpus expansion is paused unless later executable benchmark work exposes a materially missing problem class.

Detailed retained evidence:

- `research/benchmark/waves/WAVE-01-summary.md`
- `research/benchmark/waves/WAVE-02-summary.md`
- `research/benchmark/waves/WAVE-03-summary.md`
- `research/benchmark/waves/WAVE-04-summary.md`
- `research/benchmark/waves/WAVE-05-summary.md`
- `research/benchmark/waves/WAVE-06-summary.md`
- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`
- `research/benchmark/legacy-observations/`

## Benchmark measurement completed

The coded corpus and analysis are retained in:

- `research/benchmark/BENCHMARK-50-classification.csv`;
- `research/benchmark/BENCHMARK-50-analysis.md`;
- `research/benchmark/BENCHMARK-50-closure-review.md`.

The intentionally difficult stress corpus measured:

- authoritative/original-document path found: 44/50 (88%);
- appendage/configuration taxonomy complexity: 42/50 (84%);
- temporal/production applicability materially relevant: 32/50 (64%);
- identity/generation/lineage semantics materially relevant: 30/50 (60%);
- option/variant/operating-state semantics materially relevant: 30/50 (60%);
- secondary/community/broker evidence materially needed: 30/50 (60%);
- post-hoc reference anomaly/incompleteness/definition issue: 28/50 (56%);
- measurement-basis/field-definition semantics materially relevant: 22/50 (44%);
- explicit material conflict or unresolved question: 20/50 (40%).

These are **stress-corpus incidences, not population prevalence estimates**.

Runtime repeatability, automated-acceptance rate, false-normalization rate, processing cost and actual human minutes per review cannot be measured honestly from manual research. They require the executable importer/persistence benchmark and were deliberately deferred rather than invented.

## Findings forcing the next bounded contract

The 50-design corpus repeatedly demonstrated that:

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

The independent closure review added one critical precision: accepted ResearchJob targets are deliberately pre-canonical, while FieldEvidence requires a stable ProvenanceSubject. The next bounded implementation must therefore use:

```text
ResearchObservation
→ ResearchEvidenceBundle
→ explicit caller-supplied stable ProvenanceSubject
→ deterministic promotion to successor FieldEvidence
```

rather than forcing canonical identity during web research.

## Out of scope

This slice did not authorize broad production ingestion, production PostgreSQL schema work, persistence implementation, query/search semantics, public API/frontend work, marketplace ingestion, accounts/alerts, or treating reference comparison data as production evidence.

## Exit gate status

- [x] minimum 50-design difficult corpus reached;
- [x] evidence remains source-linked and reproducible at research-summary level;
- [x] major ambiguity/conflict classes have measured stress-corpus frequencies;
- [x] minimum pre-persistence semantics have been derived from real evidence;
- [x] next bounded implementation slice drafted from observed evidence;
- [x] exact accepted PR head `9f1859fe9762e05bd2a5be57c550f255be302c9b` passed GitHub Actions CI run #151;
- [x] independent closure review found no remaining blocking scope/data-governance issue;
- [x] explicit project-owner acceptance;
- [x] PR #22 merged to canonical `main` as `668e91937d27dc9c70760301b92ce0ded41abb2f`.

SLICE-0011 is `DONE`. No later slice was started automatically.
