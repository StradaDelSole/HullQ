# Independent Research Workflow

## Pipeline

```text
broad research_queue
→ identity resolution
→ source discovery
→ source ranking
→ data extraction
→ normalization
→ taxonomy mapping
→ derived calculations (only after approved formula spec)
→ validation
→ conflict detection
→ production record OR review queue
```

## Operating objective

The workflow must be designed for **high-throughput ingestion across thousands of designs with exception-based human review**.

The 50–100 design corpus is used to benchmark and harden this workflow. It is not the intended production scale.

## Hard AI rules

1. Never invent missing values.
2. Never silently resolve conflicting authoritative sources.
3. Use `unknown`/`null` when evidence is insufficient.
4. Store provenance.
5. Record confidence.
6. Separate source value from normalized value where necessary.
7. Flag uncertain keel/rudder/skeg classification aggressively.
8. Never use the old Sailboatdata scrape as an invisible fallback source.
9. Do not treat a missing field as evidence that the characteristic is absent.
10. Do not require human approval for every clear, well-supported record if automated validation can safely accept it.

## Source hierarchy

For deep/strong verification:

1. Manufacturer / shipyard
2. Original manufacturer brochure
3. Owner's manual / technical manual
4. Designer / naval architect
5. Class association
6. Owners' association
7. Museum / recognized archive
8. High-quality specialist documentation
9. Other secondary sources only when necessary

Appropriately licensed/open structured data may bootstrap identities and ordinary factual fields. The provenance and license/source must remain explicit.

## Job inputs

Canonical research target input contains only:

```text
manufacturer
model
first_built
```

Treat `first_built` as a disambiguation hint until verified.

Workflow metadata belongs in `ResearchJob`.

## Identity resolution

- Keep input identity unchanged.
- Build verified identity from evidence.
- Record discrepancies.
- Do not collapse ambiguous variants/generations without evidence.
- Prefer explicit ambiguity/review states over forced identity merges.

## Field extraction

For each production value:

- capture source
- capture raw wording/value
- normalize to canonical field/unit
- record confidence
- retain evidence type where helpful (spec table, manual, profile drawing, etc.)

The workflow may accept partial records. Missing fields can be enriched later.

## Classification

Keel, rudder and skeg are independent. A combined source phrase must be decomposed only to the level evidence supports.

HullQ-critical fields should receive higher enrichment priority than low-value peripheral fields.

## Automated validation and review routing

Clear, supported records should proceed automatically when validation passes. Route to human review when there is:

- conflicting authoritative evidence
- uncertain identity/generation
- ambiguous taxonomy mapping
- implausible physical values
- unit uncertainty
- duplicate/near-duplicate identity risk
- low-confidence HullQ-critical classification

The human reviewer should see exceptions, not the entire ingestion stream.

## Completion

A job ends as one of:

- `complete`
- `needs_review`
- `conflict`
- `blocked`

Unknown fields are acceptable. Fabricated completeness is not.

## Scaling metrics

Track:

- designs processed per unit time
- automated acceptance rate
- human-review rate
- human minutes per reviewed design
- cost per processed design
- conflict and identity ambiguity rates
- completeness of HullQ-critical fields
- source coverage by source class

See `research/RESEARCH_PILOT.md` and `docs/DATABASE_COVERAGE_STRATEGY.md`.
