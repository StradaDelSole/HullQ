# HullQ Slice Index

**Status:** ACTIVE navigation board  
**Updated:** 2026-10-26  
**Canonical current-state authority:** `docs/PROJECT_STATE.md`

This file is deliberately a **compact navigation index**, not a second historical status authority.

The previous version had drifted to SLICE-0028 while the canonical project had already advanced through SLICE-0065. To prevent that class of contradiction from recurring:

- current accepted/queue state is read from `docs/PROJECT_STATE.md`;
- final historical acceptance state is read from each slice's acceptance closure / later explicit Owner acceptance record;
- detailed slice history stays in the individual slice documents and Git history;
- this index tracks only the current execution boundary and key navigation ranges.

## Current execution boundary

```text
Latest Owner-accepted implementation: SLICE-0089 (Owner-local FINISH SUCCESS)
Current queue:                  SLICE-0090 — OWNER-SELECTED / docs READY candidate, not operative
Current capability:             Read-only Sail+Power architecture and lawful source-rights feasibility
Current operational restriction: No production email/provider; no external broker upload/pilot (#355)
Technical native Search count:  9 hard Sail criteria; joint Sail+Power external release #366/#372 still outstanding
Production Launch Pack:         NOT_STARTED
```

- SLICE-0088 remains Owner-accepted and local FINISH was confirmed.
- SLICE-0089 is **Owner-accepted and implementation-merged**: exact accepted implementation HEAD `f57b2433db9d3a46ea49d7a5c2eec527c1ab6884`, PR #376 squash `f6e45d13d517455fab7c07b2891f2708a559c680`, exact-HEAD CI/manufacturer successful, separate formal acceptance closure `docs/slices/SLICE-0089-acceptance-closure.md`. The factual branded HTML print/download, broker opt-in weekly/monthly persisted schedule, bounded idempotent worker and local deterministic delivery adapter close `REQ-BROKER-028` / `MVP-BROKER-008` in accepted nonproduction scope. Review findings A–G resolved; actual real email provider and supervised production delivery are NOT activated. Owner-local `FINISH_SLICE.bat 0089` confirmed SUCCESS after formal docs closure merge.
- SLICE-0090 Owner-selected as bounded **DESIGN_RESEARCH** with separate docs-only READY contract `docs/slices/SLICE-0090-sail-power-architecture-source-rights.md`. Before Owner-local START, its readiness PR still requires independent exact-HEAD review, green CI/manufacturer and merge. Sail+Power parity, #355 operational STOP and Production Launch Pack remain unchanged. No later slice starts automatically.

## Historical execution ranges

| Range | Operational meaning |
|---|---|
| SLICE-0001–0038 | accepted foundational research/architecture/data/product work except where an individual slice record states otherwise |
| SLICE-0039 | terminal historical `BLOCKED` exception; do not reopen |
| SLICE-0040–0089 | accepted work (0089 Owner-local FINISH SUCCESS); see acceptance closures and `PROJECT_STATE.md` |
| SLICE-0090 | OWNER-SELECTED DESIGN_RESEARCH; READY contract not operative until reviewed/merged, Owner START pending |

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
