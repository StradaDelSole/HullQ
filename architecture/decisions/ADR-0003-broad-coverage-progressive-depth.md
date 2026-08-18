# ADR-0003 — Broad Coverage with Progressive Verification Depth

**Status:** ACCEPTED  
**Date:** 2026-08-18

## Context

HullQ's core discovery behavior asks users to find boat designs whose names they may not know. A tiny, perfectly verified database creates severe missing-universe bias: few results may mean either "few designs match" or merely "HullQ does not know the rest".

At the same time, deeply researching every field of thousands of boats before product work would be slow and expensive.

## Decision

HullQ MUST pursue broad SailboatData-like design identity coverage early while allowing progressive verification/enrichment depth.

The 50–100 design corpus is a benchmark for the research pipeline, not the launch/product database.

Sparse canonical records MAY enter the production dataset when their known values have provenance and unresolved fields remain explicitly unknown.

Unknown MUST NOT be interpreted as false/non-matching evidence.

Appropriately licensed/open data MAY bootstrap common facts; HullQ research prioritizes identity ambiguities, critical search fields, conflicts, variants/generations and provenance quality.

## Consequences

### Positive

- makes unknown-model discovery meaningful;
- separates coverage growth from costly deep verification;
- focuses research cost on differentiated/high-value fields;
- supports continuous market-driven enrichment.

### Negative

- search must explicitly handle incomplete records;
- quality/completeness metrics become part of core semantics;
- broad ingestion requires strong identity and provenance controls before scale.
