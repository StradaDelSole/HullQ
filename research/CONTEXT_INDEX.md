# HullQ — Research Cold-Context Index

**Status:** ACTIVE routing index — non-normative  
**Purpose:** prevent large retained research artifacts from being loaded into Claude context unless a concrete slice/question actually needs them.

## Core rule

```text
research/ = COLD CONTEXT BY DEFAULT
```

Do **not** preload the research tree for ordinary implementation, review, or orientation.

Research artifacts are demand-loaded only when:

- the assigned slice explicitly names one;
- a concrete implementation/review question depends on research evidence;
- provenance/source-rights/data-coverage/replay evidence must be verified;
- a real conflict/blocker cannot be resolved from the slice/spec/current code alone.

If none applies, do not open research artifacts.

## Read strategy

When research is required:

1. start with this index;
2. read the smallest summary/report file for the relevant domain;
3. use targeted Grep/Read ranges inside that report;
4. open raw JSON/manifests/ledgers only for the exact record/evidence needed;
5. never load a multi-megabyte evidence artifact in full merely for context;
6. prefer retained proof/replay scripts over manually reading huge generated evidence when the question is reproducibility rather than content interpretation.

A report/summary is a routing layer, not a replacement for exact evidence when exact evidence is materially required.

## Research domains

### General research workflow

**Tags:** `research-process`, `source-quality`, `provenance`

Start with:

- `research/RESEARCH_WORKFLOW.md`
- `research/RESEARCH_PILOT.md` only when the historical pilot protocol is actually relevant
- `research/MARKET_ACCESS_REGISTER.md` only for marketplace/source-access questions
- `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md` only for design-field coverage/source planning

Do not read these for ordinary marketplace UI/backend slices that do not touch research/data sourcing.

### Source register / evidence provenance

**Tags:** `sources`, `provenance`, `source-rights`, `data-ingestion`

Start with:

- `research/evidence/SOURCE_REGISTER.md`

Read only when source identity, source rights, evidence provenance, ingestion eligibility, or source-specific factual support is in scope.

Do not load for ordinary broker marketplace workflows, auth, media, leads, UI, or lifecycle work unless the slice explicitly depends on external source evidence.

### Benchmark / seed corpus

**Tags:** `benchmark`, `seed-corpus`, `coverage`, `classification`

Start with:

- `research/benchmark/BENCHMARK-50-analysis.md`
- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`
- a specific `research/benchmark/waves/*-summary.md` only when that wave matters

Cold/raw artifacts:

- `research/benchmark/SEED_RESEARCH_NOTES.md`
- `research/benchmark/persistence/manifest.json`
- `research/benchmark/legacy-observations/*`
- wave-specific raw/evidence directories

Open raw benchmark artifacts only for an exact benchmark record, replay, discrepancy, or retained-proof question.

### Bootstrap — Wikidata / Wikimedia

**Tags:** `wikidata`, `wikimedia`, `bootstrap`, `coverage`, `replay`

Start with:

- `research/bootstrap/wikidata/REPORT.md`
- the specific slice/report under `research/bootstrap/wikidata/slXXXX-*` or `research/bootstrap/wikimedia/slXXXX-*` when named by the active task

Very cold / generated:

- `research/bootstrap/wikidata/manifest.json` (~0.58 MB)
- downstream evidence manifests and raw replay inputs

Do not load large manifests in full. Use exact keys/search, report summaries, schemas, or replay scripts.

### Stage-3 evidence / applicability

**Tags:** `stage3`, `wikidata`, `boatdesign`, `applicability`, `evidence-profile`, `unit-correction`

Each directory is historical slice-scoped retained evidence. Start with its `REPORT.md`:

- `research/stage3/sl0025-breadth-enrichment-entry/REPORT.md`
- `research/stage3/sl0026-wikidata-tier1-enrichment/REPORT.md`
- `research/stage3/sl0027-wikidata-qualifier-semantics/REPORT.md`
- `research/stage3/sl0028-wikidata-tier1-full-boundary/REPORT.md`
- `research/stage3/sl0029-primary-source-boatdesign-applicability/REPORT.md`
- `research/stage3/sl0030-wikidata-mass-unit-correction/REPORT.md`
- `research/stage3/sl0031-corrected-tier1-evidence-profile/REPORT.md`
- `research/stage3/sl0032-positive-control-boatdesign-applicability/REPORT.md`

**Never load these generated artifacts in full merely for orientation:**

- `research/stage3/sl0028-wikidata-tier1-full-boundary/evidence_manifest.json` (~12.3 MB)
- `research/stage3/sl0031-corrected-tier1-evidence-profile/boatmodel_evidence_profile.json` (~1.7 MB)
- `research/stage3/sl0026-wikidata-tier1-enrichment/evidence_manifest.json` (~0.49 MB)
- `research/stage3/sl0028-wikidata-tier1-full-boundary/linkage.json` (~0.35 MB)

For exact evidence, search for the relevant identity/key and read only the bounded matching region where tooling permits. For reproducibility, prefer retained replay/proof machinery.

### Manufacturer research

**Tags:** `manufacturers`, `builders`, `coverage`, `source-yield`, `identity`

Start with:

- `research/manufacturers/REPORT.md`
- `research/manufacturers/CHECKPOINT.md`
- `research/manufacturers/consolidation/CONSOLIDATION-001-exact-floor-count.md` for exact floor-count questions
- the specific review/research batch only when its geography/source batch is relevant

Large/cold generated artifacts:

- `research/manufacturers/registry.json` (~0.50 MB)
- `research/manufacturers/source_yield_study.json`
- `research/manufacturers/checkpoint/agent-*-findings.md`
- `research/manufacturers/checkpoint/raw/*`
- archive-clearance JSON/data files

Use `registry.json` only for exact manufacturer identity/coverage lookup, not as general context.

### Market / competitor evidence

**Tags:** `market`, `competitor`, `UX`, `listing-platform`, `aggregator`

Read only when the active product decision explicitly needs competitor/market evidence.

Available focused reports include:

- `research/market/COMPETITIVE_CHECK_SAILBOATLAB_KEEL_INDEX_2026-08-31.md`
- `research/market/COMPETITIVE_UX_EVIDENCE_SAILBOATLAB_KEEL_INDEX_2026-08-31.md`
- `research/market/LISTINGS_PORT_COMPETITIVE_EVIDENCE_2026-08-31.md`
- `research/market/SL0038_PRESTART_AGGREGATOR_ASSESSMENT_2026-08-31.md`
- `research/market/sl0038-owning-oceanis-30-1/REPORT.md`

Do not preload competitor reports for ordinary execution of already-decided product behavior.

### Validation research

**Tags:** `validation`, `marine-entailment`, `real-design`

Start with:

- `research/validation/SL0036-marine-entailment-real-design-validation.md`

Only read for the specific validation/entailment boundary it documents.

## Cold-context classifications

Use these routing labels mentally; they are not normative domain states.

### WARM SUMMARY

Small report/index intended to be read first when the domain is relevant.

Examples: `REPORT.md`, `CHECKPOINT.md`, wave summaries, this index.

### COLD DETAIL

Detailed notes, review batches, ledgers, source logs, diagnostics. Read only for a concrete question.

### DEEP-COLD GENERATED EVIDENCE

Large JSON/manifests/raw observations/replay payloads. Never preload. Query narrowly or replay mechanically.

## Implementation-agent rule

For an ordinary implementation slice:

```text
slice/spec/current code sufficient
→ research reads = 0
```

A primary slice may name a specific research report in its controlling artifacts. That authorizes reading that artifact, not the entire `research/` tree.

## Reviewer rule

Exact-head review is also research-cold by default.

Only consult research when the implementation delta:

- changes a research-derived semantic;
- changes ingestion/source/provenance behavior;
- claims something contradicted by retained evidence;
- or relies on a research acceptance proof that must be independently verified.

Do not reread research solely because an older slice once used it.

## Adding new research

New research work should, where practical, produce:

1. a compact human-readable report/summary;
2. raw/generated evidence separately;
3. schemas/digests/replay artifacts where needed;
4. an entry or category update in this index when the artifact is likely to matter again.

The report should state what future tasks should read it for and what raw artifact contains exact retained evidence.

## Non-goal

This policy does not delete or externalize retained research. Large artifacts remain available for reproducibility/auditability. It changes **default context loading**, not evidence retention.
