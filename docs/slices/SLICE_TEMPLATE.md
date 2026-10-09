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

For slices selected after SLICE-0072, the overall-MVP capability-register check is additionally mandatory before a primary slice may become `READY`.

For SLICE-0080 and later, the mechanical-invariants / failure-modes check is additionally mandatory before a primary slice may become `READY`. This incorporates the production-readiness lessons from SLICE-0079: high-risk behavior must be specified as mechanical invariants and adversarial failure cases before implementation, not discovered one review amendment at a time.

**ONE-CAPABILITY CHECK:** PASS | FAIL  
Does this slice deliver exactly one coherent user-visible capability OR answer exactly one business-critical hypothesis?

For work governed by the 2026-09-26 broker-launch execution amendment, one coherent capability may span persistence/domain/API/frontend/tests when those layers are inseparable parts of the same outcome and introduce no second independent product/domain policy. Do not interpret this check as a requirement for one-field/one-endpoint micro-slices.

**VISIBLE-RESULT CHECK:** PASS | FAIL  
Can the Project Owner personally execute, observe or inspect the result at the end of this slice?

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS | FAIL  
Does the slice comply with the currently controlling product/architecture governance and explicit gates? For work after SLICE-0039, apply the precedence defined in `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`, including `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` plus later explicit owner-accepted product directions. From the 2026-09-14 marketplace pivot onward, `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md` and `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md` supersede the older broker-only/private-FSBO-out-of-scope current direction where relevant. From the 2026-09-26 execution recalibration onward, professional marketplace readiness must also apply `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md` where relevant. Historical policy records remain history, not current authority where superseded.

**REPOSITORY RECONCILIATION CHECK:** PASS | FAIL  
Required for SLICE-0051 and later. Before this slice was proposed, were the relevant accepted CAL/decision/ADR/spec/governance/slice records and the relevant existing production code/tests/migrations checked so this slice does not re-open or duplicate behavior that HullQ has already decided and implemented? See `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`. For SLICE-0054 and later, work touching listing/supply, seller identity/verification, representation conflict, referral, marketplace monetization or Search MUST include the owner-direct product direction/requirements in this reconciliation.

**TRIGGER GATES CHECK:** PASS | FAIL  
Required for SLICE-0052 and later. Were `docs/governance/POST_0051_TRIGGER_GATES.md` and `docs/governance/PRODUCTION_READINESS_GATE.md` checked and are all currently applicable architecture-reconciliation, production-readiness, technical-Search-abstraction and workflow-reassessment triggers satisfied? Owner-direct production data/pilots are not exempt from Production Readiness merely because older trigger wording was broker-specific.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS | FAIL | NOT_APPLICABLE  
Required for every primary slice selected after SLICE-0072. Was `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` inspected, were newly DUE/open capabilities accounted for, and does the readiness state why this capability is selected ahead of any higher-risk or higher-leverage due gap? This check prevents support, trust/safety, privacy/legal, admin/operations, communications, accessibility, i18n, monetization and production/data-operations obligations from disappearing from the execution path.

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS | NOT_APPLICABLE  
Required for every primary slice from SLICE-0080 onward. Use `PASS` whenever the slice touches a high-risk boundary such as authentication/authorization/privileged access, persistence or migrations, identity/provenance/truth, concurrency/idempotency/replay, payments/settlement, deployment/release/CI supply chain, backup/restore/durability, production data/operations, destructive or irreversible state, or another boundary where a fail-open bug can silently corrupt trust or recoverability. Use `NOT_APPLICABLE` only for genuinely ordinary low-risk work and explain why in `## Mechanical invariants / failure modes`. A gate-closing or infrastructure label does not exempt a slice from the one-capability check or this failure-mode analysis.

A required `FAIL` on any of these checks blocks readiness. `SPLIT_REQUIRED` in the mechanical-invariants section also blocks readiness. Genuine prerequisite/blocker work must still be cut so the Project Owner can inspect its concrete result and the check can honestly be `PASS`.

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

## Production phase transition check

Required when this slice provisions production services, changes production operational boundaries, introduces real production data, begins/expands an external pilot, enables buyer/public exposure, or otherwise advances HullQ toward a later go-live phase.

**Launch-pack phase before this slice:** NOT_APPLICABLE | NOT_STARTED | 1 | 2 | 3 | 4 | 5 | 6  
**Launch-pack phase after this slice:** NOT_APPLICABLE | 1 | 2 | 3 | 4 | 5 | 6 | 7  
**PRODUCTION LAUNCH PACK CHECK:** PASS | NOT_APPLICABLE  

`PASS` requires reconciliation with `docs/operations/PRODUCTION_LAUNCH_PACK.md`: the slice may not skip a prior phase, must preserve the Production Readiness Gate and buyer-exposure prerequisites, and must define the done-when evidence for any production phase transition. A deployment or provider configuration step must not silently authorize external data, pilot or public launch.

## Trigger gates

Required for SLICE-0052 and later. Use exact values from the canonical gate records; do not convert a triggered gate into prose or invent a weaker local interpretation.

**Production readiness gate:** NOT_TRIGGERED | IN_PROGRESS | PASS  
**Adds technical native Search criterion:** YES | NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE | <integer>  
**Second-criterion bridge comparison:** NOT_APPLICABLE | PASS  
**Third-copy abstraction guard:** NOT_APPLICABLE | PASS  
**Workflow reassessment status:** NOT_DUE | DUE | PASS  

Rules:

- `Production readiness gate` must exactly match `PRODUCTION_READINESS_GATE_STATUS` in `docs/governance/PRODUCTION_READINESS_GATE.md`;
- if the slice does not add a hard technical native-inventory Search criterion, use `NO` and `NOT_APPLICABLE` for ordinal/comparison/third-copy guard;
- if it adds criterion #2, the SLICE-0051 bridge/path comparison must be `PASS` and the third-copy guard is `NOT_APPLICABLE`;
- if it adds criterion #3 or later, both the bridge comparison and third-copy abstraction guard must be `PASS`; the readiness text must prove either common structure is generalized/reused or that the new path is structurally distinct and does not create a third copy;
- the ordinal must be exactly one greater than `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT` in `docs/governance/POST_0051_TRIGGER_GATES.md`;
- workflow status must exactly match the canonical marker;
- after accepted SLICE-0056 the canonical workflow state may temporarily be `DUE`, but `DUE` blocks SLICE-0057 readiness/start until the evidence-based reassessment is owner-accepted and the state becomes `PASS`;
- Production Readiness must become `PASS` before real external broker OR owner-direct seller/listing data is stored/relied upon as HullQ production data, before a real external production pilot, or before public production launch, whichever comes first;
- any Search capability must preserve the accepted non-commercial organic Search invariant: seller/broker payments or HullQ revenue opportunity may not affect organic eligibility, match classification or organic ordering.

Repository validation checks deterministic relationships it knows about. Independent readiness review must verify substantive comparison/generalization/distinction, owner-direct alignment and gate evidence are true.

## Mechanical invariants / failure modes

Required for SLICE-0080 and later. This section is a readiness contract, not implementation commentary. It must be completed before `READY` so the implementation agent and independent reviewer share the same failure model.

**Risk classification:** HIGH_RISK | ORDINARY  
**Why this classification:**  
**Must-never-change invariant:**  
**Durable source of truth / loss boundary:**  
**Retry / replay / partial-failure behavior:**  
**Absence-vs-error / fail-closed behavior:**  
**Executable adversarial proof:**  
**Slice sizing assessment:** COHERENT | SPLIT_REQUIRED  

Rules:

- `HIGH_RISK` requires `**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS` and concrete repository/domain-specific evidence on every line above. If one dimension genuinely does not apply, say why; bare `N/A`, `TODO`, `TBD` or equivalent is not evidence.
- `ORDINARY` may use `NOT_APPLICABLE`, but `Why this classification` and `Slice sizing assessment` still require concrete content. Do not use `ORDINARY` merely because the change is small in line count or lives in docs/config/scripts.
- State the invariant mechanically. Prefer forms such as: “once X is established, retry/rerun/host loss cannot silently make X mean Y”; “failed B never advances current state”; “unknown/error is never treated as absent”; “rollback restores the exact prior identity/configuration.” Avoid vague goals such as “robust”, “secure” or “works reliably”.
- Name the authoritative durable state and what happens when replaceable process/host/cache/local files are lost. If no durable state is required, explain why that is safe.
- Distinguish confirmed absence from lookup/transport/auth/timeout/parse failure wherever an external dependency or registry/API lookup controls mutation. Error paths must fail closed unless an accepted contract explicitly requires another behavior.
- Define retry, rerun, replay, duplicate request, partial success, rollback and concurrency semantics wherever they can affect identity or mutation. Include stale-state/version races when relevant.
- `Executable adversarial proof` must name the negative/failure scenarios that require real execution, not only static review or documentation. External/provider criteria remain unverified until actually observed; do not turn vendor documentation or intended configuration into execution evidence.
- The implementation agent must trace every high-risk invariant to code plus proof before handoff, and the independent reviewer must re-run the reasoning adversarially on the exact HEAD.
- `Slice sizing assessment` is `SPLIT_REQUIRED` when the proposed slice bundles multiple independently useful/testable failure domains or subsystems that can be accepted separately. A shared umbrella such as “production readiness”, “security” or “launch gate” is not by itself one coherent capability. Keep one slice only when the parts are inseparable for one observable outcome and one acceptance boundary.
- When a slice contains deploy + recovery + observability + another independent operational subsystem, default to splitting unless readiness explains why separation would make the result unusable or unsafe.

Every material invariant above should map to at least one acceptance criterion and, where executable, one validation/proof step. The readiness reviewer should reject a `PASS` that merely restates architecture nouns without specifying failure semantics.

## Why this slice exists

Explain the problem this slice closes and why it belongs at this point in the execution order.

## Controlling artifacts

List only artifacts that materially control this slice. Do not mechanically copy the project's full governance/history stack into every slice.

- Normative spec(s):
- Accepted decision/ADR/governance record(s) directly controlling this capability:
- Requirement IDs, if any:
- Relevant current implementation/tests/migrations already inspected:
- Relevant open question(s), only if actually in scope:

The readiness reconciliation and trigger-gate sections above remain mandatory where applicable; they are the compact evidence that broader governance was checked. Once READY, the implementation agent should not have to reread every historical artifact used during readiness unless this section explicitly names it or a real conflict/blocker arises.

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
- a post-SLICE-0072 readiness ignores an applicable DUE/open obligation in `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` or silently drops it from the launch boundary;
- a SLICE-0080+ readiness leaves a high-risk mechanical invariant/failure mode unspecified, treats dependency error as confirmed absence without proof, relies on replaceable local state as the sole durable truth, or has `Slice sizing assessment: SPLIT_REQUIRED`;
- the requested behavior would violate source-rights, provenance, identity, search/SEO, product-execution, owner-direct/private-seller or other accepted policy;
- implementation requires scope outside this slice.

## Status handoff rule

The implementation/research agent may recommend or set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark the slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, and explicit user/project-owner acceptance as defined in `CLAUDE.md`.

A successful agent completion therefore normally hands the slice off in `REVIEW`.

## Required completion report

Use this structure exactly at the end of the assigned slice.

**Token-efficiency rule:** the structure is mandatory, but the normal report SHOULD fit roughly one screen/page. Evidence belongs here; project history and contract restatement do not. Summarize command/test/CI results rather than pasting logs. Do not repeat the full slice contract, acceptance criteria, repository history, code diff, or speculative next-slice plan unless needed to explain a failure, blocker, ambiguity, or scope deviation.

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
- OVERALL MVP CAPABILITY REGISTER CHECK: `PASS` | `FAIL` | `NOT APPLICABLE`
- MECHANICAL INVARIANTS / FAILURE MODES CHECK: `PASS` | `NOT APPLICABLE`

### Changes

- Changed files: concise paths/groups only
- Acceptance work completed: concise mapping to the slice's material requirements
- Tests/fixtures added or updated: concise groups/counts

### Validation

- Local validation: `PASS` | `FAIL` | `PARTIAL` | `NOT APPLICABLE`
- Commands/results: one compact line/grouped summary; no logs
- Mechanical/adversarial validation: `PASS` | `FAIL` | `PARTIAL` | `NOT APPLICABLE`

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


## Amendment completion report

For a review amendment on an already-running slice, do **not** repeat the full primary completion report unless the reviewer explicitly requests it.

Use this compact delta report:

### Amendment

- Previous reviewed HEAD:
- Exact new HEAD:
- Findings addressed:
- Changed files:
- Focused validation:
- Final/full validation state: `PASS` | `PENDING FINAL CANDIDATE` | `NOT APPLICABLE`
- Remote CI: `PASS` | `FAIL` | `NOT VERIFIED` | `NOT APPLICABLE`
- Remaining unresolved point(s):

The amendment report should describe only `previous reviewed HEAD → new HEAD`. Do not recap the entire slice, original readiness, or unaffected acceptance criteria.
