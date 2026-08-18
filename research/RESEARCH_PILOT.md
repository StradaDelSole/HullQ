# Research Benchmark Corpus — 50–100 Models

## Purpose

Validate and benchmark the independent-data research pipeline **before running it at high throughput across thousands of sailboat designs**.

This 50–100 design corpus is **not the HullQ product database, launch dataset or a valid standalone test of the unknown-model discovery experience**. HullQ requires broad database coverage for characteristic-first discovery to be meaningful.

## Sample design

Use a deliberately difficult and representative set of 50–100 boats covering:

- monohulls, catamarans and trimarans
- older and newer designs
- common and obscure manufacturers
- multiple keel/rudder/skeg arrangements
- models with known variants/generations
- reused model names across generations where possible
- centerboard / daggerboard / lifting / swing / bilge / twin-keel cases
- twin-rudder and unusual rudder arrangements
- boats currently visible on the used market where possible

The corpus should stress the pipeline rather than merely maximize easy completions.

## Metrics

Track at least:

- identity-resolution success rate
- variant/generation ambiguity rate
- primary-source coverage
- open/licensed-source usefulness
- field completeness by field
- HullQ-critical field completeness
- conflict rate
- keel/rudder/skeg manual-review rate
- percentage automatically accepted without human review
- human-review rate
- research time/cost per model
- human minutes per reviewed model
- percentage of records reaching `verified` / `partial` / `needs_review` / `conflict`

## Exit criteria before high-throughput scaling

Do not scale merely because the corpus has been processed. First confirm that:

- identity handling is stable enough for variants/generations;
- source capture is reproducible;
- taxonomy covers encountered data without excessive `other` or forced classifications;
- provenance can answer “where did this value come from?”;
- validation catches obvious extraction and unit errors;
- automated acceptance is safe for clear cases;
- human-review volume is operationally acceptable;
- open/licensed bootstrap data can be used without weakening provenance or rights tracking;
- throughput and cost are compatible with reaching thousands of identities.

## What happens after the benchmark

After a successful benchmark, switch from sample-sized research to **broad high-throughput ingestion**.

Conceptually:

```text
50–100 benchmark corpus
        ↓
5,000–10,000+ identity universe / broad ingestion target
        ↓
progressive basic searchable coverage
        ↓
HullQ-critical enrichment
        ↓
deep verification where valuable
        ↓
continuous market-driven enrichment and correction
```

Do not require every record to reach deep verification before broader ingestion proceeds. Breadth and depth advance in parallel at different speeds.

See `docs/DATABASE_COVERAGE_STRATEGY.md`.
