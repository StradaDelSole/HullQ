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

## Decision implementation status

An accepted decision that requires production behavior MUST not disappear after the decision is made.

At product/architecture reassessment and slice readiness, every material accepted decision relevant to the proposed work must be classifiable as:

```text
IMPLEMENTED
QUEUED_OR_ACTIVE
EXPLICITLY_DEFERRED
```

If none applies, the missing ownership is a traceability/governance defect and must be surfaced before unrelated new semantics are introduced.

`IMPLEMENTED` requires concrete evidence such as accepted slice closure plus relevant production code/test/migration. A statement in a decision document alone is not proof that the behavior exists in production.

`QUEUED_OR_ACTIVE` requires a concrete execution owner. `EXPLICITLY_DEFERRED` requires a controlling record that says the implementation is intentionally postponed.

The mandatory pre-decision classification and no-reopening rules are defined in `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`.

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

An accepted implementation obligation MUST NOT remain indefinitely without implementation evidence, a concrete queued/active owner, or explicit deferral.

## Current high-value mappings

- OQ-004 / ADR-0006 → `specs/PROVENANCE_MODEL.v0.1.md` → REQ-PROV-001..008 → provenance contract/semantic tests → persistence implementation.
- ADR-0007 → `architecture/SEARCH_AND_SEO_ARCHITECTURE.md` → REQ-SEO-001..007 → OQ-018 public-surface contract/tests → frontend/routing implementation.
- OQ-001 / ADR-0008 → `specs/DERIVED_METRICS_SPEC.v1.0.md` → REQ-RATIO-001..008 → `fixtures/ratios/` → derived-metric implementation.

These mappings prevent provenance or SEO semantics from being decided implicitly inside storage/frontend code.
