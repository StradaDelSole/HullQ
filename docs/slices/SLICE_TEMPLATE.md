# Slice Template

**ID:** SLICE-XXXX  
**Type:** BOOTSTRAP | DESIGN_RESEARCH | IMPLEMENTATION | VALIDATION  
**Status:** BACKLOG | READY | IN_PROGRESS | BLOCKED | REVIEW | DONE  
**Stage:**  
**Depends on:**  
**Blocks:**  

## Objective

One concrete outcome only.

## Product execution checks

For SLICE-0039 and later, both checks are mandatory before a primary slice may become `READY`.

**ONE-CAPABILITY CHECK:** PASS | FAIL  
Does this slice deliver exactly one user-visible capability OR answer exactly one business-critical hypothesis?

**VISIBLE-RESULT CHECK:** PASS | FAIL  
Can the Project Owner personally execute, observe or inspect the result at the end of this slice?

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS | FAIL  
Does the slice comply with `docs/PRODUCT_EXECUTION_PLAN.md`, including current phase ordering and explicit gates?

A `FAIL` on ONE-CAPABILITY blocks readiness. A `FAIL` on VISIBLE-RESULT blocks ordinary product work unless the slice documents a genuine prerequisite/blocker exception. A `FAIL` on PRODUCT EXECUTION PLAN ALIGNMENT blocks readiness.

## Why this slice exists

Explain the problem this slice closes and why it belongs at this point in the execution order.

## Controlling artifacts

- Requirement IDs:
- Specifications:
- Accepted ADRs:
- Governance / research protocols:
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md` for SLICE-0039 and later
- Relevant open questions:

## In scope

- ...

## Explicitly out of scope

- ...

## Required behavior / research questions

- ...

## Deliverables

- ...

## Acceptance criteria

- [ ] ...

An implementation/research agent MUST NOT check an acceptance criterion that it has not actually verified. External criteria such as GitHub Actions remain unchecked until their results have actually been observed.

## Expected touch points

Expected files/modules only; this is not permission to modify unrelated files.

## Validation

```bash
# exact commands where applicable
```

## Stop conditions

Stop and report instead of inventing a solution when:

- a required controlling decision is absent;
- accepted artifacts contradict each other materially;
- the requested behavior would violate source-rights, provenance, identity, search/SEO, product-execution, or other accepted policy;
- implementation requires scope outside this slice.

## Status handoff rule

The implementation/research agent may recommend or set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark the slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, and explicit user/project-owner acceptance as defined in `CLAUDE.md`.

A successful agent completion therefore normally hands the slice off in `REVIEW`.

## Required completion report

Use this structure exactly at the end of the assigned slice.

**Token-efficiency rule:** the structure is mandatory, but the report SHOULD be concise. Summarize command/test/CI results rather than pasting logs. Do not repeat the full slice contract, acceptance criteria, repository history, code diff, or speculative next-slice plan unless needed to explain a failure, blocker, ambiguity, or scope deviation.

### Slice

- Slice ID: `SLICE-XXXX`
- Recommended slice state: `REVIEW` | `BLOCKED`
- Scope completed: `YES` | `NO`
- Exact final branch HEAD SHA:

### Product execution checks

- ONE-CAPABILITY CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`
- VISIBLE-RESULT CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`
- PRODUCT EXECUTION PLAN ALIGNMENT: `PASS` | `FAIL` | `NOT APPLICABLE`

### Changes

- Changed files:
- Requirements implemented or researched:
- Tests/fixtures added or updated:

### Validation

- Local validation: `PASS` | `FAIL` | `PARTIAL` | `NOT APPLICABLE`
- Commands run:
- Results:

### External verification

- Remote CI: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`
- Other external gates: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`

### Findings

- Unresolved findings:
- Spec/ADR ambiguities:
- Scope deviations:

### Follow-up

- Recommended next action:

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.
