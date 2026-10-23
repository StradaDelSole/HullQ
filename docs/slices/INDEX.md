# HullQ Slice Index

**Status:** ACTIVE navigation board  
**Updated:** 2026-10-23  
**Canonical current-state authority:** `docs/PROJECT_STATE.md`

This file is deliberately a **compact navigation index**, not a second historical status authority.

The previous version had drifted to SLICE-0028 while the canonical project had already advanced through SLICE-0065. To prevent that class of contradiction from recurring:

- current accepted/queue state is read from `docs/PROJECT_STATE.md`;
- final historical acceptance state is read from each slice's acceptance closure / later explicit Owner acceptance record;
- detailed slice history stays in the individual slice documents and Git history;
- this index tracks only the current execution boundary and key navigation ranges.

## Current execution boundary

```text
Latest owner-accepted slice: SLICE-0088 (local FINISH confirmed SUCCESS)
Current queue:               SLICE-0089 — OWNER-SELECTED / docs READY candidate, NOT STARTABLE
Current capability:          Periodic factual broker reporting from accepted 0075 telemetry, scoped #357
Current readiness:           Owner START forbidden until docs READY review + green CI/repro merge; accepted security #373 remediation and exact-head CI
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
- SLICE-0085 is **Owner-accepted, fully remotely closed and locally finished**: bounded typed registry plus LOA range and qualified rudder configuration added as hard Buyer Search dimensions #3/#4, private broker Search-fit parity, five-locale real SSR proof; implementation PR #345, final review #5510329645, formal closure PR #346 and Owner-confirmed local `FINISH_SLICE.bat` 0085 on 2026-10-14. Exactly **4** public hard dimensions were accepted at 0085 closure, prior to accepted 0086's three-dimensional extension. `LONG_KEEL` remains unsupported; no new production authorization;
- SLICE-0086 is **Owner-accepted, independently reviewed, implementation + separate closure merged and locally finished**: independent hull configuration, cockpit position and deck saloon/pilothouse structural Buyer filters, private authorized Broker Search-fit parity and durable current offered-boat claims; implementation PR #349, formal closure PR #350, Owner-confirmed local `FINISH_SLICE.bat 0086`. Exactly **7** public hard technical Search dimensions are accepted. Public subtype/legal-use categories for motorsailer, traditional and commercial sailing vessels remain deferred; no real production/pilot authorization.
- SLICE-0087 is **Owner-accepted and implementation-merged**, exact reviewed final HEAD `88c8baa3e8451f9b0afaca776766b1f5a450f354` (PR #352, squash `e6d30f1671e6834d097068a7318a4d84c8f96e04`). Additional Buyer and private Broker Search-fit facets are inclusive overall beam min/max (one semantic dimension) and safely qualified GFK/steel/aluminium/wood hull material (one), with immutable claim revision/editor and retained real PostgreSQL18/FastAPI/built SSR proof. Both initial review Findings A/B closed; exact-head CI and manufacturer successful, Owner explicitly accepted. **9** public hard dimensions are recorded by the separate formal acceptance closure `docs/slices/SLICE-0087-acceptance-closure.md`; Owner-confirmed local `FINISH_SLICE.bat 0087` SUCCESS after the separate closure PR #353 merged;. No real provider/pilot/launch authorization;
- SLICE-0088 is **Owner-accepted and implementation-merged**: exact reconciled final HEAD `5dbcccd61d5be8bbc5b448444d778b96ee5a0541`, implementation PR #368 squash `4cb5ec3ca03190575df1f8e753668c89d6d597f4`, all-green CI/manufacturer, separate closure `docs/slices/SLICE-0088-acceptance-closure.md`. Broker-owned Select→Preview→Download outputs seven genuine formats CSV/TSV/XLSX/XLS/ODS/JSON/NautiX 1.4. XLSB export is explicitly deferred to #362, import unchanged. `REQ-BROKER-022`/`MVP-BROKER-009` implemented in bounded portable-download scope; real broker upload, feeds, external pilot and launch remain blocked by separate gates. Owner-confirmed local `FINISH_SLICE.bat 0088` SUCCESS; canonical `main` updated to closure HEAD and implementation worktree/branch removed.
- SLICE-0089 was subsequently Owner-selected in the post-0088 reassessment as factual periodic broker reporting, but is **not implemented and NOT STARTABLE** until exact-head independent docs-only READY/CI/repro+merge, closed security #373 and normal Owner START. No later slice is selected automatically.
- no subsequent slice is authorized automatically.

## Historical execution ranges

| Range | Operational meaning |
|---|---|
| SLICE-0001–0038 | accepted foundational research/architecture/data/product work except where an individual slice record states otherwise |
| SLICE-0039 | terminal historical `BLOCKED` exception; do not reopen |
| SLICE-0040–0088 | accepted work; see acceptance closures and `PROJECT_STATE.md` |
| SLICE-0089 | OWNER-SELECTED factual periodic Broker Report; docs-only READY candidate awaiting review/CI/security merge; implementation NOT_STARTED |

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
