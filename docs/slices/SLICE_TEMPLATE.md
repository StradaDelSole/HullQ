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

For SLICE-0039 and later, the first three checks are mandatory before a primary slice may become `READY`.

For SLICE-0051 and later, the repository-reconciliation check is additionally mandatory before a primary slice may become `READY`.

For SLICE-0052 and later, the trigger-gates check is additionally mandatory before a primary slice may become `READY`.

**ONE-CAPABILITY CHECK:** PASS | FAIL  
Does this slice deliver exactly one user-visible capability OR answer exactly one business-critical hypothesis?

**VISIBLE-RESULT CHECK:** PASS | FAIL  
Can the Project Owner personally execute, observe or inspect the result at the end of this slice?

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS | FAIL  
Does the slice comply with the currently controlling product/architecture governance and explicit gates? For work after SLICE-0039, apply the precedence defined in `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`, including `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` and, where private-owner/public-supply policy is relevant, `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`. Older execution documents remain controlling only where they do not conflict with higher-precedence post-SLICE-0039 decisions.

**REPOSITORY RECONCILIATION CHECK:** PASS | FAIL  
Required for SLICE-0051 and later. Before this slice was proposed, were the relevant accepted CAL/decision/ADR/spec/governance/slice records and the relevant existing production code/tests/migrations checked so this slice does not re-open or duplicate behavior that HullQ has already decided and implemented? See `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`.

**TRIGGER GATES CHECK:** PASS | FAIL  
Required for SLICE-0052 and later. Were `docs/governance/POST_0051_TRIGGER_GATES.md` and `docs/governance/PRODUCTION_READINESS_GATE.md` checked and are all currently applicable architecture-reconciliation, production-readiness, technical-Search-abstraction and workflow-reassessment triggers satisfied?

A required `FAIL` on any of these checks blocks readiness. Genuine prerequisite/blocker work must still be cut so the Project Owner can inspect its concrete result and the check can honestly be `PASS`.

## Decision / implementation reconciliation

Required for SLICE-0051 and later. Fill every evidence line with concrete repository-backed content before setting the slice to `READY`; `TODO`, `TBD`, `PLACEHOLDER` and angle-bracket placeholder text are not evidence.

**Accepted records checked:**  
**Production implementation checked:**  
**Already implemented / not re-decided:**  
**Exact remaining gap:**  
**Accepted-but-unimplemented obligations:**  
**Material classifications:**  

`Accepted-but-unimplemented obligations` may be `NONE` only when the reconciliation found none. `Material classifications` must use one or more of: `DECIDED_AND_IMPLEMENTED`, `DECIDED_NOT_YET_IMPLEMENTED`, `EXPLICITLY_DEFERRED`, `GENUINELY_OPEN`, `CONFLICT_OR_REGRESSION`.

The six evidence lines are machine-checked for presence, non-empty/non-placeholder values and accepted classification tokens by `START_SLICE` and repository validation. Independent readiness review must still verify that the cited records and implementation actually support the classifications.

Classify material points using the governance states in `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md` rather than turning remembered/implemented behavior back into an open question.

## Trigger gates

Required for SLICE-0052 and later. Use exact values from the canonical gate records; do not convert a triggered gate into prose or invent a weaker local interpretation.

**Production readiness gate:** NOT_TRIGGERED | IN_PROGRESS | PASS  
**Adds technical native Search criterion:** YES | NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE | <integer>  
**Second-criterion bridge comparison:** NOT_APPLICABLE | PASS  
**Third-copy abstraction guard:** NOT_APPLICABLE | PASS  
**Workflow reassessment status:** NOT_DUE | PASS  

Rules:

- if the slice does not add a hard technical native-inventory Search criterion, use `NO` and `NOT_APPLICABLE` for ordinal/comparison/third-copy guard;
- if it adds criterion #2, the SLICE-0051 bridge/path comparison must be `PASS` and the third-copy guard is `NOT_APPLICABLE`;
- if it adds criterion #3 or later, both the bridge comparison and third-copy abstraction guard must be `PASS`; the readiness text must prove either common structure is generalized/reused or that the new path is structurally distinct and does not create a third copy;
- the ordinal must be exactly one greater than `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` in `docs/governance/POST_0051_TRIGGER_GATES.md`;
- workflow status must match the canonical marker; once the five-slice/pre-production-pilot trigger is due, `NOT_DUE` cannot make a slice startable;
- production readiness does not need to be `PASS` during internal development unless its external-broker/public-launch trigger has been reached.

Repository validation checks these deterministic relationships. Independent readiness review must verify that the substantive comparison/generalization/distinction and gate evidence are true.

## Why this slice exists

Explain the problem this slice closes and why it belongs at this point in the execution order.

## Controlling artifacts

- Requirement IDs:
- Specifications:
- Accepted ADRs:
- Governance / research protocols:
- Decision/implementation reconciliation: `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`
- Post-0051 trigger gates: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Production readiness gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Post-SLICE-0039 architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Post-SLICE-0039 execution reconciliation / precedence: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`
- Private-owner / public-supply policy where relevant: `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`
- Native listing market decision: `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`
- Pre-Gate-1 execution amendment: `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`
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
- repository reconciliation shows the proposed behavior is already decided/implemented and the slice has no distinct remaining capability;
- an accepted implementation obligation is missing and lacks a concrete owner/explicit deferral;
- a post-0051 trigger gate is due but not satisfied;
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
- REPOSITORY RECONCILIATION CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`
- TRIGGER GATES CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`

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
