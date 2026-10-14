# HullQ Slice Index

**Status:** ACTIVE navigation board  
**Updated:** 2026-10-13  
**Canonical current-state authority:** `docs/PROJECT_STATE.md`

This file is deliberately a **compact navigation index**, not a second historical status authority.

The previous version had drifted to SLICE-0028 while the canonical project had already advanced through SLICE-0065. To prevent that class of contradiction from recurring:

- current accepted/queue state is read from `docs/PROJECT_STATE.md`;
- final historical acceptance state is read from each slice's acceptance closure / later explicit Owner acceptance record;
- detailed slice history stays in the individual slice documents and Git history;
- this index tracks only the current execution boundary and key navigation ranges.

## Current execution boundary

```text
Latest owner-accepted slice: SLICE-0085
Current queue:               SLICE-0086
Current capability:          OWNER-SELECTED First-Level Sailing-Vessel Discovery (hull form + cockpit + deck/saloon)
Current readiness:           READY contract proposed; independent review/CI/repro/docs merge PENDING; implementation NOT_STARTED
```

Current boundary:

- SLICE-0082 is Owner-accepted; final implementation/review history is retained in `docs/slices/SLICE-0082-acceptance-closure.md` (implementation PR #331 and separate closure PR);
- `docs/PROJECT_STATE.md` remains the canonical accepted/queue boundary;
- Production Launch Pack phase remains `NOT_STARTED`;
- post-SLICE-0080 reassessment selected Production Launch Pack Phase 1 for the limited pilot, but the Owner explicitly reprioritized unfinished product development on 2026-10-12;
- SLICE-0081 Operational Dashboard remains accepted; Phase-1 operator provisioning is paused in priority, not completed;
- SLICE-0082 closes the normal broker→canonical BoatDesign→native technical Search bridge with accepted auditable first-time association and real synthetic end-to-end proof; no production/pilot launch was authorized;
- SLICE-0083 is Owner-accepted and merged (implementation PR #335), providing D26-governed CSV/TSV/XLSX/XLS/XLSB/ODS/JSON/NautiX 1.4 intake into private drafts only; see `docs/slices/SLICE-0083-acceptance-closure.md`;
- SLICE-0084 Broker pre-publication Search-fit is Owner-accepted and merged (implementation PR #342, independent exact-head ACCEPT); closure at `docs/slices/SLICE-0084-acceptance-closure.md`. The accepted technical Search expansion priority (LOA first candidate, then rudder/skeg; separate long-keel taxonomy review) remains binding for the post-0084 reassessment under `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md` / issue #339;
- SLICE-0085 is **Owner-accepted, implementation-merged and closing**: bounded typed registry plus LOA range and qualified rudder configuration added as hard Buyer Search dimensions #3/#4 with private broker Search-fit parity, five-locale SSR and real PG18 proof; accepted implementation PR #345, final review #5510329645, closure `docs/slices/SLICE-0085-acceptance-closure.md`. Exactly **4** technical hard dimensions are accepted after closure. `LONG_KEEL` remains unsupported; no new production authorization. Post-0085 reconciliation/choice is required before any 0086 readiness/start;
- SLICE-0086 Owner-selected after confirmed local 0085 FINISH: broad sail-vessel market allowed in principle; first live Buyer/Broker Search bundle is hull form, cockpit position and deck saloon/pilothouse over newly declared independent concrete claims, while motorsailer/traditional/commercial *subtype filters* remain deferred. Reconciliation: `docs/POST_SLICE_0085_FIRST_LEVEL_SAILING_VESSEL_DISCOVERY_REASSESSMENT_2026-10-14.md`; proposed READY: `docs/slices/SLICE-0086-first-level-sailing-vessel-discovery.md`. No implementation until independently reviewed docs-only READY merge and normal Owner `START_SLICE.bat`;
- no subsequent slice is authorized automatically.

## Historical execution ranges

| Range | Operational meaning |
|---|---|
| SLICE-0001–0038 | accepted foundational research/architecture/data/product work except where an individual slice record states otherwise |
| SLICE-0039 | terminal historical `BLOCKED` exception; do not reopen |
| SLICE-0040–0085 | accepted work; see acceptance closures and `PROJECT_STATE.md` |
| SLICE-0086 | OWNER-SELECTED first-level structural Buyer Search; readiness subject to independent review/CI/repro/merge, NOT_STARTED implementation |

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
