# HullQ Slice Index

**Status:** ACTIVE navigation board  
**Updated:** 2026-10-28  
**Canonical current-state authority:** `docs/PROJECT_STATE.md`

This file is deliberately a **compact navigation index**, not a second historical status authority.

The previous version had drifted to SLICE-0028 while the canonical project had already advanced through SLICE-0065. To prevent that class of contradiction from recurring:

- current accepted/queue state is read from `docs/PROJECT_STATE.md`;
- final historical acceptance state is read from each slice's acceptance closure / later explicit Owner acceptance record;
- detailed slice history stays in the individual slice documents and Git history;
- this index tracks only the current execution boundary and key navigation ranges.

## Current execution boundary

```text
Latest Owner-accepted slice:       SLICE-0094 (implementation #393 merged; docs-only acceptance closure and Owner-local FINISH pending)
Current queue:                  SLICE-0095 — NOT SELECTED / NOT READY; no START authorized
Current capability:             9 Sail hard criteria + 2 qualified Power criteria (current drive and installed engine count), with same-configuration AND
Current operational restriction: No real external broker/owner-direct data or pilot (#355); no joint release (#366)
Technical native Search count:  11 accepted globally = Sail 9 / Power 2; full Power parity #372 and Search scale #355 still outstanding
Production Launch Pack:         NOT_STARTED
```

- SLICE-0088 remains Owner-accepted and local FINISH was confirmed.
- SLICE-0089 is **Owner-accepted and implementation-merged**: exact accepted implementation HEAD `f57b2433db9d3a46ea49d7a5c2eec527c1ab6884`, PR #376 squash `f6e45d13d517455fab7c07b2891f2708a559c680`, exact-HEAD CI/manufacturer successful, separate formal acceptance closure `docs/slices/SLICE-0089-acceptance-closure.md`. The factual branded HTML print/download, broker opt-in weekly/monthly persisted schedule, bounded idempotent worker and local deterministic delivery adapter close `REQ-BROKER-028` / `MVP-BROKER-008` in accepted nonproduction scope. Review findings A–G resolved; actual real email provider and supervised production delivery are NOT activated. Owner-local `FINISH_SLICE.bat 0089` confirmed SUCCESS after formal docs closure merge.
- SLICE-0090 is **Owner-accepted docs-only DESIGN_RESEARCH**, exact reviewed HEAD `847c56cde1c48ea285da87ac70c72a6cfdfde5b8`, PR #379 squash merged as `0e78f2c64c2d21e0b2fd5d8a97213b49cbdedeb8`, six-job CI/manufacturer PASS and independent Findings A–K closed. Retained architecture, nine-external-source rights matrix and 13 synthetic hard cases provide **research only**; no Power product implementation, source ingestion or public pilot is authorized. Separate `docs/slices/SLICE-0090-acceptance-closure.md` records formal Owner acceptance; Owner-local FINISH 0090 confirmed SUCCESS. #372 stays open.

- SLICE-0091 is **Owner-accepted IMPLEMENTATION**, exact reviewed HEAD `ec3fbef167812a18df60b521a8261e3f0bd8cd59`, PR #384 squash merged as `b707c8ebf00a7e40f849e49f60490327583eb74a`; independent findings A–J closed, six-job CI/manufacturer PASS. Durable category claims (SAIL/POWER/MOTORSAILER), source-qualified design/concrete current provenance, derived UNKNOWN/CONFLICT, conservative Sail-only search exclusion and broker claim round-trip implemented. Nine Sail technical criteria unchanged, no Power specialist search, external source admission or live pilot; full detail in `docs/slices/SLICE-0091-acceptance-closure.md`. Owner-local FINISH 0091 confirmed SUCCESS; #372 remains OPEN.

- SLICE-0092 is **Owner-accepted IMPLEMENTATION**, independently reviewed exact HEAD `441d6ec27b9a284321a946fa3cc4e348f77f1035`, implementation PR #387 squash merged as `c2425232967a8223b64b3a677cbad2c83c2e2336`. Category-qualified publishing-Organization claim truth for design-unresolved ACTIVE SAIL listings now participates in both Sail search paths, separate buyer sensitivity and five-locale result evidence as `PUBLISHER_CLAIM`; the nine accepted Sail criteria and legacy design-linked results remain untouched. Findings A/B/C/E closed; performance D accepted **only for internal synthetic development** with actual 0/40/200 measurements (2/169/809 SQL statements) and mandatory pre-real-data/pilot scaling hard stop in issue #355. Exact-head six-job CI/manufacturer succeeded. See `docs/slices/SLICE-0092-acceptance-closure.md`. Owner-local FINISH 0092 confirmed SUCCESS. No Power criteria, motorsailer policy or external release; #372 and #366 remain OPEN.

- SLICE-0093 is **Owner-accepted IMPLEMENTATION**: first source-qualified Power hard technical criterion (`power_drive=SHAFT|STERNDRIVE|POD|WATERJET|OUTBOARD`), existing shared Search kernel with own current publisher POWER category + drive and D29 gating, limited genuine v0.6 shaft/outboard bridge, separate five-locale noindex Power buyer routes, valid NautiX Sail-only export guard and unchanged nine Sail criteria. Independently reviewed exact HEAD `4b9060e7fce7ebb7a7893c87890571210f94d825` with all Findings A–K and publisher-owned-category invariant closed; full exact-head six-job CI/manufacturer SUCCESS; Owner explicitly accepted 2026-10-28. PR #390 squash merged as `c38a60d821a6e9a88fba023a0008a36a3dcd51e1`. Formal closure: `docs/slices/SLICE-0093-acceptance-closure.md`. Global accepted count **10 = Sail 9 / Power 1** in this separate docs-only closure; Owner-local FINISH 0093 confirmed SUCCESS. #355 scale/real-data STOP, #366 joint release and #372 full Power technical parity OPEN. No external pilot/public launch authorized.

- SLICE-0094 is **Owner-accepted IMPLEMENTATION** on independently reviewed exact HEAD `76f542635d3d04ae9e8c4c05c8a704912f0ba3d4` with closed findings A–F/C2/D2/F2/G3/C3. PR #393 squash merged as `9ac9705825bcc3bdab83a85c74f011eaf285d67a`. It implements source-qualified immutable current principal propulsion engine count (public exact tokens 1–8; publisher authoring 1–32), real same-current-revision and same-FieldResolution-qualified-configuration MUST/AND with the accepted Power drive criterion, five-locale buyer source-labelled evidence, strict 400/308/502 and actual browser/PG18 proof, without changing nine Sail criteria. Exact accepted-HEAD six-job CI/manufacturer and applicable Deploy workflow SUCCESS. Formal docs-only acceptance is `docs/slices/SLICE-0094-acceptance-closure.md`; **its independent review/CI/merge and Owner-local FINISH 0094 remain pending**. Accepted global count **11 = Sail 9 / Power 2** is recorded in this separate docs-only closure. No successor selected, no external inventory/pilot/public launch; #355/#366/#372 remain OPEN.

## Historical execution ranges

| Range | Operational meaning |
|---|---|
| SLICE-0001–0038 | accepted foundational research/architecture/data/product work except where an individual slice record states otherwise |
| SLICE-0039 | terminal historical `BLOCKED` exception; do not reopen |
| SLICE-0040–0089 | accepted work (0089 Owner-local FINISH SUCCESS); see acceptance closures and `PROJECT_STATE.md` |
| SLICE-0090 | Owner-accepted DESIGN_RESEARCH (not implementation); Owner-local FINISH SUCCESS |
| SLICE-0091 | Owner-accepted category IMPLEMENTATION; Owner-local FINISH SUCCESS |
| SLICE-0092 | Owner-accepted claim-only Sail Search implementation; Owner-local FINISH SUCCESS |
| SLICE-0093 | Owner-accepted Power drive-configuration Search criterion (global #10, Power-domain #1); implementation+closure merged; Owner-local FINISH SUCCESS |
| SLICE-0094 | Owner-accepted second Power criterion (current installed engine count) and conjunctive same-config Search; implementation merged; docs-only closure and Owner-local FINISH pending |

Do not infer that every numeric slice in a range has identical type or historical handoff status. Use the individual slice file / acceptance closure when exact history matters.

## Current product execution focus

Current execution priority after accepted SLICE-0079 is governed by:

- `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`
- `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`
- `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`
- `docs/PRODUCT_EXECUTION_PLAN.md`

The priority is to turn the accepted foundation into a coherent professional loop:

```text
broker creates
→ adds media
→ publishes
→ buyer contacts
→ broker handles lead
→ broker edits/maintains inventory
→ explicit outcome / scale capabilities as required by gates
```

No future slice number or exact scope is preassigned by this index.

## Navigation

- Current project state: `docs/PROJECT_STATE.md`
- Current execution focus: `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`
- Product execution policy: `docs/PRODUCT_EXECUTION_PLAN.md`
- Professional marketplace decisions: `docs/PROFESSIONAL_MARKETPLACE_WORKFLOW_DECISIONS_2026-09-26.md`
- AI slice workflow: `docs/engineering/AI_SLICE_WORKFLOW.md`
- Slice template: `docs/slices/SLICE_TEMPLATE.md`
- Broker launch gate: `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`
- Mandatory broker capability register: `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`

## Maintenance rule

When a slice acceptance closure advances `PROJECT_STATE_ACCEPTED_SLICE` or a reassessment selects a new queue capability, update only this compact boundary section if needed. Do not mirror transient READY/REVIEW/BLOCKED handoff state here.

Do **not** rebuild a duplicated full historical ledger here. The old detailed ledger model is what allowed this file to become dozens of slices stale.

No later slice starts automatically.
