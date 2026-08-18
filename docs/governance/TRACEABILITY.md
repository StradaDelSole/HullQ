# HullQ — Requirements Traceability

**Status:** ACCEPTED

## Objective

Every important domain behavior must be traceable from intent to verification.

```text
Requirement
  ↕
Spec / Schema
  ↕
ADR or Open Question (when relevant)
  ↕
Automated Test(s)
  ↕
Implementation
  ↕
Release / Migration evidence
```

## Minimum traceability

For behaviorally significant code, the repository MUST make it possible to answer:

1. Which requirement authorizes this behavior?
2. Which spec defines the data/algorithm semantics?
3. Which test proves the requirement?
4. If the behavior was a significant choice, which ADR explains why?
5. If persisted/public semantics changed, what migration/version change accompanied it?

## ID conventions

- Requirement: `REQ-<NAMESPACE>-NNN`
- Test: `TEST-<REQ-ID>-<LETTER/NN>`
- Open question: `OQ-NNN`
- ADR: `ADR-NNNN`
- Validation rule: existing `VAL-*` IDs may continue where already defined

## Traceability matrix

During early development the matrix may live in `specs/REQUIREMENTS.md`. Once code volume makes manual maintenance error-prone, generate a machine-readable matrix from test metadata and requirement annotations rather than duplicating mappings manually.

## No orphan rules

A new normative rule MUST NOT exist only in source code comments or tests. It belongs in a spec/requirement first.

A requirement MUST NOT be marked implemented until at least one verification artifact exists.

## Current high-value mappings

- OQ-004 / ADR-0006 → `specs/PROVENANCE_MODEL.v0.1.md` → REQ-PROV-001..008 → provenance contract/semantic tests → persistence implementation.
- ADR-0007 → `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` → REQ-SEO-001..007 → OQ-018 public-surface contract/tests → frontend/routing implementation.
- OQ-001 / ADR-0008 → `specs/DERIVED_METRICS_SPEC.v1.0.md` → REQ-RATIO-001..008 → `fixtures/ratios/` → derived-metric implementation.

These mappings prevent provenance or SEO semantics from being decided implicitly inside storage/frontend code.
