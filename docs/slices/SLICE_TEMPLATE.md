# Slice Template

**ID:** SLICE-XXXX  
**Type:** BOOTSTRAP | DESIGN_RESEARCH | IMPLEMENTATION | VALIDATION  
**Status:** BACKLOG | READY | IN_PROGRESS | BLOCKED | REVIEW | DONE  
**Stage:**  
**Depends on:**  
**Blocks:**  

## Objective

One concrete outcome only.

## Why this slice exists

Explain the problem this slice closes and why it belongs at this point in the execution order.

## Controlling artifacts

- Requirement IDs:
- Specifications:
- Accepted ADRs:
- Governance / research protocols:
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
- the requested behavior would violate source-rights, provenance, identity, search/SEO, or other accepted policy;
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
