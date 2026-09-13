# HullQ — Broker Workspace Mandatory Capability Register

**Status:** ACCEPTED OWNER DIRECTION when merged  
**Accepted direction date:** 2026-09-13  
**Purpose:** preserve broker-product commitments that are mandatory but may be implemented after the first launch-critical baseline because they depend on scale, telemetry or later bounded capabilities.

<!-- BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN -->
<!-- BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN -->
<!-- SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED -->
<!-- SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS: NOT_REACHED -->
<!-- POST_PILOT_REAL_BROKER_VALIDATION_STATUS: NOT_STARTED -->

<!-- REQ_BROKER_022_STATUS: PENDING -->
<!-- REQ_BROKER_023_STATUS: PENDING -->
<!-- REQ_BROKER_024_STATUS: PENDING -->
<!-- REQ_BROKER_025_STATUS: PENDING -->
<!-- REQ_BROKER_026_STATUS: PENDING -->
<!-- REQ_BROKER_027_STATUS: PENDING -->
<!-- REQ_BROKER_028_STATUS: PENDING -->
<!-- REQ_BROKER_029_STATUS: PENDING -->
<!-- REQ_BROKER_030_STATUS: IMPLEMENTED -->

## Controlling rule

`PENDING` does not mean optional.

A capability in this register remains a committed HullQ broker-product obligation until one of these is true:

1. the corresponding requirement is implemented and independently accepted with repository-backed evidence; or
2. a later explicit Project Owner decision supersedes the requirement and updates the normative requirement plus this register in the same reviewed change.

A normal post-slice reassessment may change implementation order, slice boundaries or technical approach. It may not silently delete a commitment from this register.

Allowed per-requirement states:

```text
PENDING
DUE
IMPLEMENTED
```

`BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS` may become `COMPLETE` only when every `REQ_BROKER_022_STATUS` through `REQ_BROKER_030_STATUS` is `IMPLEMENTED`.

## Mandatory capability map

| Requirement | Capability | Timing class | Current status |
|---|---|---|---|
| REQ-BROKER-022 | inventory portability / no lock-in export | mandatory before paid broker activation / broad public launch | PENDING |
| REQ-BROKER-023 | broker identity / branding preservation | launch/pilot baseline commitment | PENDING |
| REQ-BROKER-024 | connectivity-resilient draft/recovery behavior | launch/pilot baseline commitment | PENDING |
| REQ-BROKER-025 | Search exclusion explainability: why a listing was not found | search-volume-dependent mandatory capability | PENDING |
| REQ-BROKER-026 | pre-publication Search-fit diagnostics | mandatory before paid broker activation / broad public launch | PENDING |
| REQ-BROKER-027 | structured CSV/bulk onboarding/import | scale-triggered mandatory capability | PENDING |
| REQ-BROKER-028 | periodic engagement/performance reporting even without a lead | telemetry-dependent; mandatory before paid broker activation / broad public launch once supported telemetry exists | PENDING |
| REQ-BROKER-029 | privacy-safe aggregate demand insights by relevant configuration | search-volume-dependent mandatory capability | PENDING |
| REQ-BROKER-030 | validation order: coherent product before real external broker pilot | immediate governance rule | IMPLEMENTED by this governance package when merged |

## Trigger: first external broker pilot

The first real external broker self-service pilot is allowed only after `BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS` under `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`.

That first pilot is intentionally the first point at which real external broker behavior becomes required product evidence. External brokers are not a prerequisite for designing or implementing the coherent pre-pilot baseline.

The pilot must produce a repository-backed post-pilot validation record. `POST_PILOT_REAL_BROKER_VALIDATION_STATUS` may become `PASS` only when that record includes:

- observed task/friction evidence from real professional broker use;
- material failures/confusion/workarounds;
- differences from pre-pilot assumptions;
- corrective disposition for material findings;
- explicit independent review and Project Owner acceptance.

Before any of the following becomes active after the first pilot, `POST_PILOT_REAL_BROKER_VALIDATION_STATUS` MUST be `PASS`:

```text
SCALED_BROKER_ONBOARDING_STATUS = ACTIVE
PAID_BROKER_PLAN_STATUS = ACTIVE
PUBLIC_PRODUCTION_LAUNCH_STATUS = ACTIVE
```

## Trigger: launch/pilot baseline commitments

Before `BROKER_WORKSPACE_LAUNCH_GATE_STATUS` may become `PASS`, these addendum commitments must be `IMPLEMENTED`:

```text
REQ_BROKER_023_STATUS  # broker identity / branding
REQ_BROKER_024_STATUS  # connectivity-resilient draft recovery
```

These are daily usability/trust properties that do not require production Search volume and should be present before asking real external brokers to use the self-service product.

## Trigger: paid broker activation / broad public launch

Before either `PAID_BROKER_PLAN_STATUS` or `PUBLIC_PRODUCTION_LAUNCH_STATUS` becomes `ACTIVE`, these additional commitments MUST be `IMPLEMENTED`:

```text
REQ_BROKER_022_STATUS  # inventory portability / no lock-in
REQ_BROKER_026_STATUS  # pre-publication Search-fit diagnostics
REQ_BROKER_028_STATUS  # engagement/performance reporting, when underlying telemetry is part of production
```

If the production boundary at that point still does not contain the underlying telemetry needed for REQ-BROKER-028, the same reviewed activation change must explicitly prove why the requirement is not yet applicable and must leave it registered as mandatory rather than silently removing it.

## Trigger: scaled broker onboarding

`SCALED_BROKER_ONBOARDING_STATUS` represents a move beyond a deliberately small manually supportable pilot cohort into repeatable acquisition/onboarding of professional inventory providers.

Before that marker becomes `ACTIVE`, `REQ_BROKER_027_STATUS` MUST be `IMPLEMENTED`.

This does not require a bulk importer before HullQ has any external broker. It prevents HullQ from attempting scaled broker acquisition while still requiring established brokerages to manually retype large inventories.

## Trigger: sufficient Search volume

`SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS` may become `REACHED` only through a later owner-accepted evidence record defining privacy-safe and statistically useful production volume for the applicable insight.

When that marker becomes `REACHED`:

- `REQ_BROKER_025_STATUS` must move from `PENDING` to at least `DUE` in the same reviewed change unless already `IMPLEMENTED`;
- `REQ_BROKER_029_STATUS` must move from `PENDING` to at least `DUE` in the same reviewed change unless already `IMPLEMENTED`.

The trigger deliberately does not invent a numeric threshold today. The later threshold must account for privacy, re-identification risk, statistical usefulness and the actual Search/event model.

## Search diagnostics architecture obligation now

Although REQ-BROKER-025 and REQ-BROKER-029 may surface later, earlier Search/event-model work MUST NOT discard the structured information reasonably required to implement them.

In particular, future Search telemetry architecture must preserve a privacy-compatible path to structured eligibility/exclusion reason codes and aggregateable Search-demand facts without requiring retention of unnecessary raw personal query data.

This is an architecture-preservation requirement, not authorization to build a generalized analytics platform prematurely.

## Periodic engagement reporting

REQ-BROKER-028 remains mandatory even if its polished delivery is not part of the first external pilot. Once the underlying production exposure/view/Search-impression telemetry is accepted and reliable, the owning readiness reassessment must treat broker engagement reporting as `DUE` rather than silently leaving it as a vague later idea.

The eventual broker-facing report should make useful activity visible even when no lead was generated, while distinguishing observed facts from derived interpretation.

## Product completion boundary

The Broker Workspace Launch Gate and this register answer different questions:

- `BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS` means the external professional workspace has the accepted first pilot baseline.
- `BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS = OPEN` means later committed differentiators still remain.
- `BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS = COMPLETE` means every requirement in this register has actually been implemented and accepted.

Therefore the first broker pilot or public launch may occur before every volume-dependent capability is available, but HullQ must not describe the accepted broker-product workstream as complete while any registered commitment remains `PENDING` or `DUE`.

## Evidence to mark IMPLEMENTED

A requirement status may become `IMPLEMENTED` only when the repository names:

- the implementing accepted slice(s) or maintenance capability;
- applicable tests/retained proof;
- the relevant broker-facing or API behavior;
- any privacy/security constraints needed for that capability;
- independent review and explicit Project Owner acceptance.

Changing a status marker without that evidence is a governance failure.
