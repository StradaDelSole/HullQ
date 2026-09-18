# HullQ — Post-SLICE-0056 Workflow Reassessment

**Date:** 2026-09-18  
**Status:** OWNER_ACCEPTANCE_READY  
**Trigger:** accepted SLICE-0056 / `WORKFLOW_REASSESSMENT_STATUS: DUE`  
**Scope:** evidence-based reassessment of readiness, exact-head implementation review, amendment re-review, owner acceptance and closure overhead after SLICE-0051 through SLICE-0056

## Purpose

This reassessment satisfies the mandatory Gate 4 review created after SLICE-0051.

It answers one process question:

> Can HullQ safely reduce review overhead after six accepted buyer/seller/search slices without weakening the invariants that independent review actually protected?

This is a workflow/governance reassessment only. It does not select SLICE-0057, does not change product/domain semantics, and does not authorize a production pilot.

## Canonical evidence examined

Repository-backed evidence was taken from the owner-accepted acceptance closures for SLICE-0051 through SLICE-0056, their exact-head review histories, accepted implementation heads and remote CI/repro verification.

Wall-clock reviewer minutes were not recorded consistently in the repository. Review effort is therefore measured by the observable repository proxies that are actually retained:

- number of exact-head review/amendment iterations before acceptance;
- number and class of documented independent-review findings;
- whether the finding crossed a semantic, persistence, security, identity, Search, browser/API or proof/CI boundary;
- whether a supposedly narrower UI/copy change still exposed a material protocol/truth defect.

## Evidence summary

| Slice | Accepted capability / dominant risk | Amendment or reconciliation iterations before final ACCEPT | Documented independent-review findings | What the review materially protected |
| --- | --- | ---: | ---: | --- |
| SLICE-0051 | first technical Search + FieldResolution persistence / concurrency / source rights | 3 | 10 | Decimal/canonicalization, missing durable prerequisite, option handling, consistent reads, 400/503 semantics, persistence invariants, source binding/rights, race/rollback proof |
| SLICE-0052 | listing freshness + buyer-visible freshness wording | 1 | 1 | prevented `offer_recorded_at` and `last_confirmed_at` from being presented as the same buyer-facing truth |
| SLICE-0053 | Auth0 / session / MFA / tenant-safe Broker Workspace boundary | 2 | 6 | cookie hardening, MFA ACR, cache control, browser-faithful proof, same-host topology and Auth0 Action guidance |
| SLICE-0054 | owner-direct private draft workspace / ownership / non-promotion | 2 | 4 | canonical persisted strings, bounded login-next, complete non-promotion evidence, retained proof wired into CI |
| SLICE-0055 | second technical Search criterion + mixed typed evidence | 2 | 4 | prevented evidence collapse/loss, misleading completion claim, discarded canonical values and invalid handoff metadata |
| SLICE-0056 | public browser/API projection of accepted two-criterion Search | 1 | 2 | prevented browser reinterpretation of invalid input and closed order-only canonical-URL 308 regression |
| **Total** | six IMPLEMENTATION slices | **11** | **27** | every accepted slice benefited from independent review |

The exact counts above are conservative counts of findings explicitly recorded in the acceptance closures. They do not count routine style/CI-only failures after acceptance-boundary review.

## Findings

### 1. Independent implementation review is producing real defect detection

All six accepted post-SLICE-0051 implementation slices had at least one material independent-review finding.

The findings were not cosmetic. They included:

- persistence and concurrency correctness;
- source-rights admission;
- authentication/session/MFA boundaries;
- ownership and redirect safety;
- Search evidence preservation;
- URL canonicalization;
- browser-vs-FastAPI validation ownership;
- buyer-facing truth wording;
- retained vertical proof completeness and CI wiring.

Therefore the repository evidence does **not** support removing independent exact-head review, explicit Owner Acceptance, or final exact-head CI from primary `IMPLEMENTATION` slices.

### 2. File type alone is not a safe risk classifier

SLICE-0052 shows that a narrow buyer-facing wording change can be reviewed cheaply and corrected in one amendment.

SLICE-0056 shows the opposite danger: work centered on Astro/TypeScript browser projection exposed both a browser validation-ownership defect and a latent backend canonicalization defect.

Therefore:

```text
"mostly UI/copy"
!=
automatically low risk
```

Risk must be classified by the invariant/boundary touched, not merely by language, framework or changed-file extension.

### 3. High-risk boundaries consistently justify the full path

The strongest review yield occurred where work touched one or more of:

- persistence / migrations / immutable history / concurrency;
- authentication / sessions / MFA / CSRF / tenant authorization;
- identity / ownership / seller trust / publication eligibility;
- Search semantics / canonicalization / evidence / truth classification;
- production-data or production-readiness boundaries;
- cross-layer browser ↔ API ↔ persistence truth.

For those areas, the current readiness → exact-head review → CI → Owner Acceptance path remains proportionate.

### 4. Re-review after a bounded amendment does not need to restart from zero

The accepted 0055/0056 review pattern demonstrates a safe efficiency gain:

```text
previous exact reviewed HEAD
→ targeted amendment
→ exact amendment diff
→ re-check impacted invariants
→ final exact-head CI
```

A full unrelated-subsystem re-audit is unnecessary when the amendment is genuinely bounded and introduces no unrelated changes.

If the amendment broadens scope, touches a new high-risk boundary, or changes code outside the reviewed area, the reviewer must expand the re-review accordingly.

### 5. Operator waiting was a separate workflow-cost problem, not evidence for weaker correctness review

Repeated Claude Code permission prompts during SLICE-0056 materially increased elapsed implementation time without improving product correctness.

That overhead has already been addressed independently by PR #209, now canonical on `main`:

- project-level `PreToolUse` guard;
- project-level `PermissionRequest` guard;
- approval-free diagnostic helper;
- shared command discipline;
- repository validation preventing regression.

This is the preferred pattern for workflow optimization:

```text
remove mechanical waiting / duplicated operator work
while preserving
semantic review / exact-head evidence / owner decision gates
```

### 6. Full runtime CI on docs-only closure changes may be redundant, but changing required-check topology is not justified inside this reassessment

Acceptance closures are mechanically narrow, but current branch/ruleset behavior depends on stable required check contexts.

Changing GitHub Actions path filtering or required-check topology can itself create merge-gate failure modes.

Therefore docs-only CI specialization is:

```text
EXPLICITLY_DEFERRED
```

It may be addressed later by a dedicated workflow-maintenance change with exact ruleset/check-context proof. It is not silently folded into this reassessment.

## Accepted workflow result proposed by this reassessment

If the Project Owner accepts this exact reassessment head, the controlling result is:

### A. Primary IMPLEMENTATION slices keep the mandatory gates

For primary `IMPLEMENTATION` work, retain:

```text
repository reconciliation
→ readiness preparation
→ independent readiness review
→ READY on main
→ START_SLICE
→ implementation
→ independent exact-head implementation review
→ exact-head remote gates
→ explicit Owner Acceptance
→ implementation merge
→ acceptance closure
→ FINISH_SLICE
```

No generic lighter implementation path is authorized by the current evidence.

### B. Review depth becomes explicitly boundary/risk focused

The reviewer should classify review focus from the touched invariant:

**Critical boundary focus**
- persistence, migration, concurrency, immutable history;
- auth/session/MFA/CSRF/authorization;
- identity/ownership/trust/publication;
- Search semantics/evidence/canonicalization/ranking;
- payments, production operations, production data.

These require cross-boundary inspection and retained proof appropriate to the slice.

**Boundary-facing presentation focus**
- browser/API projection;
- public validation/error behavior;
- URL/canonical/indexability behavior;
- buyer/seller copy that assigns truth or lifecycle semantics.

These still require exact-head review, but the reviewer may remain tightly focused on the changed vertical plus the pre-existing invariant it projects.

**Pure non-runtime maintenance**
- documentation or mechanical repository maintenance with no product/runtime/security/CI semantic change.

This may use a targeted exact-head review rather than a domain-wide implementation review. A change to workflow hooks, CI behavior, security policy or required-check behavior is **not** pure non-runtime maintenance merely because it lives in docs/config/scripts.

### C. Amendment re-reviews are delta-first

For a targeted same-slice amendment:

1. compare the previous reviewed exact HEAD to the new HEAD;
2. review every amendment change;
3. re-check all invariants materially affected by those changes;
4. verify no unrelated scope entered the branch;
5. require final exact-head remote gates.

Do not repeat an unrelated whole-repository review unless the amendment's actual scope requires it.

### D. Reviewer continuation remains autonomous

After a clean material exact-head review, the reviewer continues through PR creation/verification, remote-gate observation and mergeability to `OWNER ACCEPTANCE READY`.

After explicit Owner Acceptance, the reviewer continues through merge and acceptance closure.

The Project Owner is not interrupted for queued CI, routine PR handling or reviewer-controlled mechanics.

### E. Approval-autonomy hardening remains mandatory

The PR #209 command/permission guard is now part of the workflow baseline.

Routine implementation/inspection/testing should proceed without operator watching. Destructive, privileged and policy-sensitive actions remain operator-gated.

### F. No workflow gate is weakened merely because a slice was fast or UI-heavy

A lighter treatment requires the change itself to be demonstrably outside production/runtime/security/domain semantics.

When uncertain, use the stronger review focus.

## Decision / implementation reconciliation

**DECIDED_AND_IMPLEMENTED**
- independent readiness and exact-head implementation review exist and have caught material defects;
- explicit Owner Acceptance remains mandatory;
- reviewer continuation to the owner-acceptance boundary is already canonical;
- approval-autonomy guard is already canonical through PR #209;
- delta-focused amendment review is compatible with existing exact-head semantics and has already been used safely.

**EXPLICITLY_DEFERRED**
- path-filtered or reduced GitHub Actions topology for docs-only closure/readiness PRs;
- removal of any mandatory implementation-review or Owner Acceptance gate;
- a separate lighter primary IMPLEMENTATION lifecycle.

**GENUINELY_OPEN**
- none required to satisfy this reassessment.

**CONFLICT_OR_REGRESSION**
- none found in the current canonical workflow after PR #209 and SLICE-0056 closure.

## Trigger result

This reassessment satisfies the evidence requirements of Gate 4.

Upon explicit Owner Acceptance and merge of this exact reassessment:

```text
WORKFLOW_REASSESSMENT_STATUS: DUE
→
WORKFLOW_REASSESSMENT_STATUS: PASS
```

That transition removes the workflow-gate block on SLICE-0057 readiness/start.

It does **not** select SLICE-0057 and does **not** bypass the normal post-slice repository/product reassessment required before capability selection.

## Owner decision required

The Project Owner is asked to accept or reject this exact workflow result.

Acceptance means:

- the current implementation review/owner-acceptance gates remain;
- review effort is explicitly risk/boundary focused;
- bounded amendments use delta-first re-review;
- autonomous reviewer continuation and approval-autonomy remain standard;
- no separate lighter primary implementation lifecycle is authorized at this time;
- the canonical workflow reassessment marker becomes `PASS`.

No SLICE-0057 capability is selected by this decision.
