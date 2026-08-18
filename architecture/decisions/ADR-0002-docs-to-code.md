# ADR-0002 — Adopt Docs-to-Code as the Development Method

**Status:** ACCEPTED  
**Date:** 2026-08-18

## Context

HullQ contains non-trivial domain semantics: sailboat identity, sparse/unknown data, provenance, taxonomy, derived ratios, technical search and external-source behavior. AI-assisted implementation increases the risk that plausible but unintended rules are silently introduced into code.

## Decision

HullQ MUST use a docs-to-code workflow:

```text
decision → normative spec → requirement/acceptance criteria → tests → code → verification
```

Material unresolved choices MUST be captured as open questions and, where architecturally significant, ADRs before implementation.

Behavioral implementation MUST trace to stable requirement IDs.

## Consequences

### Positive

- reduces accidental AI interpretation of domain rules;
- makes changes auditable and testable;
- supports reliable handoff across coding agents/models;
- keeps long-lived project knowledge outside chat history.

### Negative

- small upfront documentation cost;
- requires discipline to update specs and tests with code;
- low-value implementation details should not be over-specified.

## Guardrail

Docs-to-code does not mean documentation for every line of code. It applies to decisions, contracts, domain behavior and acceptance criteria. Normal internal implementation details remain implementation choices.
