# Import Notes — 2026-08-18

The three uploaded files are preserved unchanged under `reference/imported/`.

## What was extracted

### `HullQ_PROJECT_CONTEXT.md`

This was the main source of product identity, scope, data doctrine, taxonomy starting points, provenance requirements, research pipeline, legal working position, live-market strategy, accounts/alerts, Strapi direction, MVP scope and roadmap.

### `HullQ_BOAT_SCHEMA.json`

This was treated as `BoatDesign` schema v0.1. It is a useful type sketch, not a formal JSON Schema.

### `HullQ_RESEARCH_QUEUE_TEMPLATE.csv`

This contains example research targets and operational columns.

## Gaps / inconsistencies found

1. **Minimal queue mismatch.** Project context says the initial research target should contain only `manufacturer`, `model`, `first_built`, while the CSV also contains `hull_configuration_hint`, `research_status`, and `notes`.
   - Resolution: `research/RESEARCH_QUEUE_INPUT_TEMPLATE.csv` is now the canonical minimal ingestion template.
   - Workflow metadata moves to `ResearchJob`.

2. **Field-level provenance missing from v0.1 schema.** The context explicitly prefers provenance per value, but v0.1 only has a global `sources` array.
   - Resolution: v0.2 adds `source_ids`, `evidence[]` keyed by `field_path`, and `conflicts[]`.

3. **Taxonomy values were unversioned and partly free-form.**
   - Resolution: `specs/TAXONOMY.v0.1.md` centralizes the current starting values and labels them DRAFT.

4. **Ratio names existed without a formula contract.**
   - Resolution: `specs/DERIVED_METRICS_SPEC.v1.0.md` defines the required contract and deliberately blocks silent implementation until formulas are approved.

5. **Canonical market listing shape was missing.**
   - Resolution: `specs/MARKET_LISTING_SCHEMA.v0.1.json` provides a DRAFT adapter output contract.

6. **Research/source entities were described but not formalized.**
   - Resolution: added Source and ResearchJob JSON schemas plus research workflow documentation.

7. **Implementation guardrails were scattered through context.**
   - Resolution: root `CLAUDE.md` centralizes instructions for coding/research agents.
