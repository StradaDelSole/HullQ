# SLICE-0025 — Stage-3.2 Breadth Sufficiency / Stage-3.3 Parallel-Entry Decision

**ID:** SLICE-0025  
**Type:** VALIDATION  
**Status:** READY  
**Stage:** 3.2 → 3.3 decision boundary  
**Depends on:** SLICE-0024 owner-accepted / DONE  
**Blocks:** first Stage-3.3 basic-enrichment implementation slice; any claim that Stage 3.2 is complete

## Objective

Using only already accepted and retained Stage-3 evidence, make one reproducible governance decision on whether HullQ should:

1. remain **Stage-3.2-only** and continue identity-breadth work before any basic enrichment; or
2. begin a **bounded Stage-3.3 basic-enrichment pilot in parallel** while keeping Stage 3.2 breadth work explicitly open.

This slice does **not** declare Stage 3.2 complete and does not perform enrichment, new discovery or canonical admission.

## Why this slice exists

HullQ currently has **1,770 accepted canonical BoatModels**, below the longer-term breadth direction of several thousand identities. However, the accepted Stage-3.2 evidence now also shows diminishing returns across several additional breadth paths:

- SLICE-0018: the direct Wikidata discovery strategy returned **1,829 unique QIDs** against a requested <=2,500 window and established **1,770 canonical BoatModels**; the accepted closure explicitly states that simply increasing the limit is not evidence that further direct-instance candidates exist;
- SLICE-0020: ten manufacturer/archive surfaces produced **0 ADAPTER_READY** sources under the accepted production/bulk rights gate;
- SLICE-0021: alternative Wikidata discovery routes retained **57** additional candidate signals;
- SLICE-0022: those 57 yielded **0 AUTO_ADMIT / 31 REVIEW_REQUIRED / 26 NOT_ADMITTED**, leaving the canonical count unchanged;
- SLICE-0023: bounded Wikimedia categories produced **409 incremental QID research leads** but no canonical admission;
- SLICE-0024: the independent-verification pilot over those leads closed with accepted recommendation **LOW_INDEPENDENT_VERIFICATION_YIELD**; only **11 of 24** threshold candidates were independently supported in-scope against a required >=12, and a full 409-lead campaign is not justified by that pilot.

The project therefore needs an explicit boundary decision instead of either:

- endlessly testing weaker breadth sources before enriching any of the 1,770 accepted identities; or
- silently starting Stage 3.3 as though Stage 3.2 breadth were complete.

## Controlling artifacts

Read only as needed under the token-efficient workflow.

- `CLAUDE.md`
- `docs/engineering/AI_TOKEN_EFFICIENCY.md`
- `docs/EXECUTION_PLAN.md` — Stage 3.2 and Stage 3.3
- `docs/DATABASE_COVERAGE_STRATEGY.md`
- `docs/slices/SLICE-0018-acceptance-closure.md`
- `docs/slices/SLICE-0020-acceptance-closure.md`
- `docs/slices/SLICE-0021-acceptance-closure.md`
- `docs/slices/SLICE-0022-acceptance-closure.md`
- `docs/slices/SLICE-0023-acceptance-closure.md`
- `docs/slices/SLICE-0024-acceptance-closure.md`
- retained manifests/reports referenced by those closures only where needed to mechanically reproduce an accepted count

Do **not** preload unrelated specs, product docs, SEO docs, frontend architecture or prior slice history.

## Fixed accepted evidence boundary

Before making the decision, reproduce or fail closed on the following accepted facts:

```text
accepted canonical BoatModels                         1,770
historical QID -> HullQ-ID mappings                   1,772
SLICE-0018 direct-discovery unique QIDs                1,829
SLICE-0018 requested direct-discovery limit            2,500
SLICE-0020 ADAPTER_READY archive sources                   0
SLICE-0021 alternative-route candidate union              57
SLICE-0022 AUTO_ADMIT from those 57                        0
SLICE-0022 REVIEW_REQUIRED                                31
SLICE-0022 NOT_ADMITTED                                   26
SLICE-0023 incremental Wikimedia QID leads               409
SLICE-0024 threshold-set independently-supported in-scope 11
SLICE-0024 threshold required                             12
SLICE-0024 final recommendation  LOW_INDEPENDENT_VERIFICATION_YIELD
```

The 409 Wikimedia leads remain research leads only and are not part of the canonical count.

If these accepted boundaries cannot be reproduced consistently from accepted artifacts, stop `BLOCKED`.

## Decision vocabulary

Produce exactly one recommendation:

- `CONTINUE_STAGE_3_2_ONLY`
- `BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL`
- `BLOCKED_ON_ACCEPTED_STATE`

This slice MUST NOT output or imply `STAGE_3_2_COMPLETE`, `G4_PASS`, broad enrichment authorization, or production readiness.

## Precommitted decision rule

Apply in this exact order.

### 1. Accepted-state integrity

If any fixed accepted evidence boundary above cannot be reproduced without contradicting an accepted closure/retained artifact:

```text
BLOCKED_ON_ACCEPTED_STATE
```

### 2. Known executable high-yield breadth path

Return:

```text
CONTINUE_STAGE_3_2_ONLY
```

if the accepted evidence already identifies a **specific unexecuted breadth mechanism** that simultaneously satisfies all of these conditions:

- production/bulk use is already cleared under the accepted source-rights model where such clearance is required;
- the mechanism is materially different from the exhausted SLICE-0018 direct-instance strategy;
- accepted retained evidence supports a likely incremental identity yield of at least **100** candidates rather than an unquantified hope;
- it does not depend on a full 409-lead Wikimedia verification campaign rejected by the accepted SLICE-0024 result;
- it does not require resolving an open upstream governance/spec question first.

Do not invent a source or expected yield to make this condition pass.

### 3. Parallel-enrichment readiness

Otherwise return:

```text
BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL
```

only if all of these accepted conditions are true:

- canonical identity persistence/replay has an accepted zero-tolerance foundation from SLICE-0016–0018;
- at least **1,000** canonical BoatModels are accepted, so the proposed work is enrichment of a genuinely broad corpus rather than a benchmark sample;
- the current canonical count remains at least **1,770**;
- no accepted high-yield/cleared breadth path from rule 2 remains waiting to be executed first;
- SLICE-0022 established zero automatic admissions from its 57-candidate alternative route;
- SLICE-0024 ended below its independent-verification yield threshold and therefore does not justify a full Wikimedia-lead campaign;
- the proposed next work can be bounded to a deterministic subset and can preserve unknown/conflict/provenance semantics without mutating Stage-3.2 breadth claims.

If these conditions are not all met, return `CONTINUE_STAGE_3_2_ONLY`.

## Interpretation of `BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL`

If this recommendation results, it means only:

- a later, separately readied slice may pilot **Stage-3.3 Tier-1/basic searchable enrichment** on a deterministic bounded subset of already canonical BoatModels;
- Stage 3.2 remains open and its long-term breadth objective is not waived;
- later breadth sources may still be researched when there is concrete evidence of likely value;
- the canonical identity count of 1,770 is **not** declared launch-complete or SailboatData-scale;
- no G4/Stage-3 exit is implied.

It does not authorize Stage-3.4 critical-field enrichment, derived metrics expansion, query engine, API, frontend, SEO runtime, marketplace, accounts, alerts or price-history work.

## Required analysis

The retained decision package must explicitly answer, from accepted evidence only:

1. Is the SLICE-0018 direct Wikidata path an unexecuted route to more identities?  
   Expected accepted fact: no; that exact strategy measured a 1,829-QID source result, and a larger limit alone is not an evidence-backed new route.
2. Did SLICE-0020 establish an already-cleared manufacturer/archive bulk-bootstrap path?  
   Expected accepted fact: no; 0/10 assessed sources were `ADAPTER_READY`.
3. Did SLICE-0021/0022 establish a productive automatic-admission route?  
   Expected accepted fact: no; 57 signals produced 0 `AUTO_ADMIT`.
4. Did SLICE-0023/0024 justify a full 409-lead independent-verification campaign?  
   Expected accepted fact: no; accepted SLICE-0024 recommendation is `LOW_INDEPENDENT_VERIFICATION_YIELD`.
5. Does accepted identity persistence/replay provide a stable corpus large enough for a **bounded enrichment pilot**, without claiming breadth completion?  
   Determine this mechanically from the accepted canonical/replay boundary and the rule above.

The first four expected facts are accepted historical inputs, not invitations to reinterpret their prior outcomes.

## Deliverables

Create a compact retained package, preferably:

```text
research/stage3/sl0025-breadth-enrichment-entry/
    decision_input.json
    decision_input_schema.json
    decision_result.json
    decision_result_schema.json
    REPORT.md
    ARTIFACT-DIGESTS.json
    ARTIFACT-DIGESTS.schema.json
```

Add only the smallest pure helper/runner needed to:

- validate the fixed accepted counts;
- mechanically apply the decision rule;
- reproduce the result offline;
- verify artifact digests.

Do not build a general workflow engine for this one decision.

## Offline verification / tamper resistance

The verifier must fail closed on at least:

- drift in any fixed accepted boundary;
- fabricated `ADAPTER_READY` source count;
- fabricated SLICE-0022 `AUTO_ADMIT` count;
- fabricated SLICE-0024 threshold/recommendation;
- changing the canonical count or crosswalk count;
- changing the final decision without changing mechanically relevant inputs;
- artifact-digest tampering.

Tests should demonstrate the major decision branches:

- accepted-state inconsistency -> `BLOCKED_ON_ACCEPTED_STATE`;
- a synthetic qualifying already-cleared >=100-yield breadth path -> `CONTINUE_STAGE_3_2_ONLY`;
- current accepted facts with no such path -> whatever the precommitted rule mechanically yields;
- insufficient canonical corpus -> `CONTINUE_STAGE_3_2_ONLY`.

Synthetic branch tests are logic tests only and must not be represented as real project evidence.

## In scope

- reproduce accepted Stage-3.2 planning facts;
- build a small deterministic decision input/result package;
- make the precommitted recommendation;
- add focused pure tests/verifier;
- update compact operational state at handoff so SLICE-0024 is shown owner-accepted / `DONE` and SLICE-0025 is shown `REVIEW` or `BLOCKED` as appropriate.

## Explicitly out of scope

- any new external web/search research;
- any live Wikidata/Wikipedia/manufacturer acquisition;
- any new source-rights decision;
- any canonical identity admission/removal;
- any full 409-lead verification campaign;
- any Tier-1/Tier-2 field enrichment;
- Stage-3.4 critical-field enrichment;
- changing the accepted identity model, provenance model, source-rights model or derived-metric methodology;
- OQ-009 query-engine implementation;
- API/frontend/SEO runtime implementation;
- marketplace/listings/accounts/alerts/monitoring/price history;
- creating or starting SLICE-0026.

## Expected touch points

Expected only where needed:

- `research/stage3/sl0025-breadth-enrichment-entry/`
- one small pure decision helper under `src/hullq/` if justified
- one small assemble/verify runner under `scripts/` if justified
- focused tests
- `docs/slices/SLICE-0025-*.md` status handoff
- compact `docs/PROJECT_STATE.md` / `docs/slices/INDEX.md` state sync

Do not modify unrelated domain/product semantics.

## Acceptance criteria

- [ ] All fixed accepted evidence boundaries reproduce from accepted repository artifacts.
- [ ] No new external research/network acquisition is performed.
- [ ] Exactly one allowed recommendation is produced by the precommitted rule.
- [ ] The result does not declare Stage 3.2 complete or G4 passed.
- [ ] The result does not fabricate an unexecuted source/yield opportunity.
- [ ] The decision input/result are schema-valid and retained with integrity digests.
- [ ] Offline verification independently reproduces the decision and fails closed on required tamper cases.
- [ ] Focused tests cover all three recommendation states and the key rule branches.
- [ ] No canonical Brand/Organization/BoatModel/BoatDesign row or historical crosswalk entry is changed.
- [ ] No Tier-1/Tier-2 enrichment is performed.
- [ ] Compact operational docs truthfully show SLICE-0024 accepted / `DONE` and SLICE-0025 handoff state.
- [ ] Repository validation, Ruff, mypy and full pytest/coverage gates pass.
- [ ] Required remote CI is observed on the exact final branch HEAD before claiming PASS.
- [ ] No later slice is started automatically.

## Validation

At final handoff run the normal repository validation once:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Run the SLICE-0025 offline verifier explicitly. Normal CI must perform zero external research requests.

## Stop conditions

Stop `BLOCKED` rather than inventing a result if:

- an accepted closure/artifact materially contradicts another accepted boundary;
- the current canonical count/crosswalk cannot be reproduced;
- applying the precommitted rule would require guessing an unmeasured source yield or source clearance;
- implementation would require external research, enrichment or canonical mutation;
- a new upstream governance decision is required to make the recommendation.

## Status handoff rule

The implementation/validation agent may set `REVIEW` or `BLOCKED` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, independent review, required remote checks and explicit project-owner acceptance.

## Required completion report

Use the mandatory concise completion-report structure in `docs/slices/SLICE_TEMPLATE.md`.

The final report must additionally state:

- the mechanically derived decision;
- whether any qualifying already-cleared >=100-yield breadth path was found in accepted evidence;
- the exact accepted canonical/crosswalk boundary reproduced;
- confirmation that Stage 3.2 remains open;
- exact final branch HEAD and exact-head CI state.

Do not speculate about SLICE-0026 beyond naming the class of work the decision would permit or block.
