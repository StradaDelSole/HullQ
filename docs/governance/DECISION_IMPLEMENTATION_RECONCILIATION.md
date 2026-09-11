# HullQ — Decision / Implementation Reconciliation

**Status:** ACCEPTED OWNER DIRECTION  
**Accepted:** 2026-09-11  
**Applies to:** project-master/product/architecture reassessment, open-question creation, slice readiness, implementation/research handoff, independent review and closure

## Purpose

HullQ must not re-open, re-decide or re-propose behavior that has already been accepted, and it must not lose accepted decisions between documentation and production code.

The repository is the durable project memory. Before a new product/architecture question is presented to the Project Owner, before a new capability/slice is proposed, or before an existing decision is challenged, the current canonical repository state MUST be reconciled against both accepted records and production implementation.

## Mandatory pre-decision repository reconciliation

Before any new product/domain/data/architecture decision, open question, capability recommendation or slice selection is presented, the project master/reviewer MUST:

1. verify the current canonical `origin/main` state;
2. search relevant accepted decision records, including applicable CAL/decision logs, ADRs, normative specs, governance docs, product/architecture decisions, open-question records and acceptance closures;
3. inspect the relevant current production code, persistence/migrations and automated tests when the question could already be implemented;
4. compare the proposed question/capability with prior accepted behavior and actual implementation;
5. classify each material point as exactly one of:

```text
DECIDED_AND_IMPLEMENTED
DECIDED_NOT_YET_IMPLEMENTED
EXPLICITLY_DEFERRED
GENUINELY_OPEN
CONFLICT_OR_REGRESSION
```

Only `GENUINELY_OPEN` and `CONFLICT_OR_REGRESSION` may be presented as needing a new owner decision.

Hard:

```text
DECIDED_AND_IMPLEMENTED
!= open question

DECIDED_NOT_YET_IMPLEMENTED
!= reason to re-decide the accepted behavior
```

A decided-but-unimplemented point is an implementation/traceability gap. It must be routed into execution planning, not presented as a fresh product choice.

## No silent reopening

An accepted decision MUST NOT be reopened merely because it is inconvenient, forgotten, not immediately visible in one document, or absent from the current discussion context.

Reopening requires at least one explicit reason:

- the Project Owner asks to reconsider it;
- new evidence demonstrates that the accepted decision is materially unsafe, impossible or internally inconsistent;
- current production behavior conflicts with the accepted contract;
- a higher-authority accepted artifact supersedes it.

When reopening is justified, the prior decision and the reason for reconsideration MUST be named explicitly.

## Immediate owner-decision capture

A material decision accepted by the Project Owner during chat, reassessment or review MUST NOT remain only in conversation history or model memory.

Before the project master/reviewer moves on to another material product/domain/data/architecture decision, the accepted decision MUST be promoted into the repository in the smallest appropriate durable artifact, for example:

- an accepted decision/governance/specification document;
- an ADR when architecturally significant;
- an updated open-question disposition;
- or the current slice-readiness reconciliation when that slice is the concrete execution owner.

The durable record MUST state enough to distinguish:

```text
what was decided
what prior rule it preserves/supersedes, if any
whether implementation already exists
where any remaining implementation is owned or explicitly deferred
```

Hard:

```text
owner accepted in chat
+ no durable repository record / execution owner
→ capture is incomplete
→ do not rely on memory and continue making dependent decisions
```

This rule is specifically intended to prevent accepted decisions from being repeatedly re-asked or silently omitted from later production planning.

## Decision-to-code closure rule

Every accepted decision that requires implementation MUST remain in one of these traceable states:

```text
IMPLEMENTED
→ named production code/test/migration or accepted slice closure proves it

QUEUED / ACTIVE
→ a concrete slice or other accepted execution item owns the remaining work

EXPLICITLY DEFERRED
→ the controlling record states why it is not currently implemented
```

An accepted implementation obligation MUST NOT silently disappear from planning.

If reconciliation finds an accepted decision with no implementation evidence, no owning queued work and no explicit deferral, that is a governance defect and must be surfaced as an implementation gap before unrelated new semantics are added.

## Slice-readiness requirement from SLICE-0051 onward

Every primary slice from `SLICE-0051` onward MUST contain:

```text
**REPOSITORY RECONCILIATION CHECK:** PASS
```

and a section exactly titled:

```text
## Decision / implementation reconciliation
```

That section MUST contain all of these machine-checkable, non-empty evidence lines:

```text
**Accepted records checked:** <specific accepted records>
**Production implementation checked:** <specific code/tests/migrations, or a precise reason none can exist>
**Already implemented / not re-decided:** <specific behavior>
**Exact remaining gap:** <single bounded gap owned by this slice>
**Accepted-but-unimplemented obligations:** <specific owner/deferral, or NONE>
**Material classifications:** <one or more governance classification tokens>
```

`Material classifications` MUST use one or more of the exact tokens:

```text
DECIDED_AND_IMPLEMENTED
DECIDED_NOT_YET_IMPLEMENTED
EXPLICITLY_DEFERRED
GENUINELY_OPEN
CONFLICT_OR_REGRESSION
```

The evidence lines are deliberately concise and machine-visible; the surrounding section may add detail where needed. `START_SLICE` and repository validation check their presence and non-empty values. Independent readiness review remains responsible for verifying that the cited records/code actually support the claims; a syntactically complete but false reconciliation is still a review defect.

A slice cannot become `READY` merely because its proposed capability sounds useful. It must demonstrate that it is not duplicating or reopening accepted/implemented work.

## Review obligation

Independent readiness review MUST reject a slice if:

- a material accepted decision was missed;
- already-existing production capability is being proposed as new work;
- an existing accepted semantic is being re-opened without a valid reason;
- an accepted implementation obligation is known to be missing but is neither owned nor explicitly deferred;
- the reconciliation claims `PASS` without checking the relevant implementation surface;
- any required reconciliation evidence line is vague, empty or unsupported by the cited repository state.

Implementation review MUST also treat regression from an accepted decision as a defect even when the new code is internally consistent.

## Relationship to token-efficient reading

This rule does not require every implementation agent to preload the whole repository.

The broad reconciliation happens during product/architecture reassessment and slice readiness. Once a slice is `READY`, its primary contract names the controlling artifacts and relevant existing implementation that the implementation agent must read.

Targeted repository search is preferred over indiscriminate full-repository loading.

## Controlling principle

> **Before asking whether HullQ should decide something, first prove that HullQ has not already decided and implemented it. Before moving on from an accepted decision, prove where its implementation lives or where the remaining work is explicitly owned.**
