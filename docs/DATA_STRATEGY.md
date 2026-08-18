# Independent Data Strategy

## Objective

Build HullQ's own production dataset from independent/open/primary sources rather than depending on a commercial Sailboatdata license.

The strategic objective is a **broad, SailboatData-scale design universe with progressive verification depth**, not a tiny set of perfectly researched records.

See `DATABASE_COVERAGE_STRATEGY.md`.

## Research input

The canonical ingestion input is intentionally minimal:

```csv
manufacturer,model,first_built
```

`first_built` is an identity/disambiguation hint, not trusted production truth.

Operational fields such as status, notes and hull hints belong to `ResearchJob`, not to the minimal identity input. See `specs/RESEARCH_JOB_SCHEMA.v0.1.json`.

## Identity rule

Input identity and verified identity remain separate. A discrepancy is recorded, not overwritten invisibly.

Example:

- input `first_built`: 1986
- verified `first_built`: 1987
- result: preserve both and record the discrepancy/evidence

## Breadth and depth are separate

HullQ needs broad design coverage early because the core user journey discovers boats whose names the user may not know.

A small 50–100 design dataset is suitable for benchmarking the research system but **not** for validating the product's unknown-model search quality. With a tiny corpus, a sparse result set cannot distinguish “few real matches exist” from “HullQ simply does not know most matching designs.”

Therefore:

- build thousands of canonical identities early;
- allow legitimate sparse/partial BoatDesign records;
- progressively enrich search-critical fields;
- deepen primary-source verification over time;
- never trade breadth for fabricated completeness.

## Source hierarchy

Preferred order for strong verification:

1. Manufacturer / shipyard
2. Original manufacturer brochure
3. Owner's manual / technical manual
4. Designer / naval architect
5. Class association
6. Owners' association
7. Museum / recognized archive
8. High-quality specialist documentation
9. Other secondary sources only when necessary

Open structured sources such as Wikidata and other appropriately licensed datasets may be used where their licenses permit commercial reuse.

## Open-data bootstrap rule

“Independent” means HullQ controls its production dataset, methodology and provenance and does not silently depend on a restricted proprietary database. It does **not** require rediscovering every common public fact from scratch.

Appropriately licensed/open sources may bootstrap:

- design identity
- manufacturer/model relationships
- common dimensions
- production years
- other factual fields supported by the source

HullQ-specific research should prioritize weak/missing/high-value fields such as:

- keel type/subtype
- rudder type
- skeg type
- variants/generations
- construction details
- conflicting specifications
- fields required for reliable technical matching

Every imported production value still requires provenance and rights-compatible sourcing.

Before broad bootstrap ingestion, each source must satisfy the OQ-007 source-rights policy: source access conditions, license/database rights and HullQ use-specific clearance are evaluated separately. Public readability alone is not bulk-ingestion clearance.

## Production rule

**No production value without provenance.**

Allowed outcome states include:

- verified value
- unknown / null
- conflict
- needs_review

AI may assist source discovery, extraction, normalization and validation, but it may not fill gaps from memory or probability.

Unknown is not failure. Sparse data is acceptable when missingness is explicit.

## Unknown-data search rule

Missing data must not become a false negative.

If a technical filter requires a value that a design does not yet have, that design is an **insufficient-data candidate**, not a confirmed non-match. Product/search implementation must preserve the distinction between:

- confirmed match
- confirmed non-match
- unknown / insufficient evidence

## Research operating model

Target exception-based human review:

```text
broad research queue
→ automated discovery/extraction
→ normalization/taxonomy
→ validation/conflict checks
→ clear supported record → production
→ ambiguous/conflicting record → review queue
```

Human review should focus on exceptions rather than every design.

## Coverage strategy

Track both breadth and depth:

- total canonical identities
- basic searchable coverage
- HullQ-critical field coverage
- deeply verified records
- completeness by important field
- real-market listing-to-design match coverage

The project should not chase another database's model count for vanity. However, broad identity coverage is a product requirement because characteristic-first discovery is unreliable over a tiny universe.

## Market-driven enrichment

Market observations remain a major prioritization signal for enrichment and correction:

```text
market listing with unknown or weakly enriched model
→ enrichment queue
→ independent/open/primary research
→ BoatDesign created or deepened
→ future listings match better
```

Missing-model requests can also be ranked by demand count.

## Sailboatdata scrape

The existing scrape is:

```text
REFERENCE / PROTOTYPE ONLY
NOT PRODUCTION DATA
```

It may inform field discovery, edge cases, taxonomy design and UI testing. It must never be an invisible fallback source for production values. Keep the raw scrape immutable; clean only derived/test copies.
