# HullQ — Broker Workspace Mandatory Capability Register

**Status:** ACCEPTED OWNER DIRECTION when merged  
**Accepted direction date:** 2026-09-13  
**Purpose:** preserve broker-product commitments that are mandatory but may be implemented after the first launch-critical baseline because they depend on scale, telemetry or later bounded capabilities.

<!-- BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS: OPEN -->
<!-- BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS: OPEN -->
<!-- BROKER_SALE_OUTCOME_WORKFLOW_STATUS: PENDING -->
<!-- SCALED_BROKER_ONBOARDING_STATUS: NOT_STARTED -->
<!-- SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS: NOT_REACHED -->
<!-- POST_PILOT_REAL_BROKER_VALIDATION_STATUS: NOT_STARTED -->

<!-- REQ_BROKER_022_STATUS: PENDING -->
<!-- REQ_BROKER_023_STATUS: IMPLEMENTED -->
<!-- REQ_BROKER_024_STATUS: IMPLEMENTED -->
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

`BROKER_SALE_OUTCOME_WORKFLOW_STATUS` is a dedicated status for the already-normative `REQ-BROKER-006` sales/outcome capability because the first deliberately bounded broker pilot may omit that workflow while paid/public rollout may not.

`BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS` may become `COMPLETE` only when every `REQ_BROKER_022_STATUS` through `REQ_BROKER_030_STATUS` is `IMPLEMENTED`, `BROKER_SALE_OUTCOME_WORKFLOW_STATUS = IMPLEMENTED`, and `BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS`.

## Mandatory capability map

| Requirement | Capability | Timing class | Current status |
|---|---|---|---|
| REQ-BROKER-006 | explicit sale/outcome recording | mandatory before paid broker activation / broad public launch | PENDING |
| REQ-BROKER-022 | inventory portability / no lock-in export | mandatory before paid broker activation / broad public launch | PENDING |
| REQ-BROKER-023 | broker identity / branding preservation | launch/pilot baseline commitment | IMPLEMENTED by SLICE-0063 |
| REQ-BROKER-024 | connectivity-resilient draft/recovery behavior | launch/pilot baseline commitment | IMPLEMENTED by SLICE-0062 |
| REQ-BROKER-025 | Search exclusion explainability: why a listing was not found | search-volume-dependent mandatory capability | PENDING |
| REQ-BROKER-026 | pre-publication Search-fit diagnostics | mandatory before paid broker activation / broad public launch | PENDING |
| REQ-BROKER-027 | structured CSV/bulk onboarding/import | scale-triggered mandatory capability | PENDING |
| REQ-BROKER-028 | periodic engagement/performance reporting even without a lead | mandatory before paid broker activation / broad public launch | PENDING |
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

The first deliberately bounded pilot may omit the final sales/outcome close-out UI if its pilot scope does not yet exercise completed sales. That exception ends at paid broker activation or broad public production launch.

## Trigger: paid broker activation / broad public launch

Before either `PAID_BROKER_PLAN_STATUS` or `PUBLIC_PRODUCTION_LAUNCH_STATUS` becomes `ACTIVE`, these commitments MUST be `IMPLEMENTED`:

```text
BROKER_SALE_OUTCOME_WORKFLOW_STATUS  # REQ-BROKER-006 explicit sale/outcome recording
REQ_BROKER_022_STATUS                # inventory portability / no lock-in
REQ_BROKER_026_STATUS                # pre-publication Search-fit diagnostics
REQ_BROKER_028_STATUS                # engagement/performance reporting
```

The sale/outcome workflow must preserve the accepted semantics: SOLD/closed is explicit evidence, never inferred from stale/withdrawn/disappeared inventory; unknown achieved price remains unknown rather than being forced.

If the production event model is not yet capable of supporting honest engagement reporting, HullQ is not yet ready to charge brokers for the professional workspace or broadly launch it. The remedy is to implement the required telemetry/reporting capability, not to waive the commitment silently.

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

It MUST be implemented before paid broker activation or broad public production launch. The eventual broker-facing report should make useful activity visible even when no lead was generated, while distinguishing observed facts from derived interpretation.

## Mandatory post-slice reassessment

Every normal post-slice capability reassessment after this governance package is merged MUST inspect this register before selecting the next primary capability.

The reassessment must explicitly account for:

- any requirement whose status is `DUE`;
- `BROKER_SALE_OUTCOME_WORKFLOW_STATUS` before paid/public rollout;
- any trigger that changed since the prior accepted slice;
- whether current work would destroy or complicate evidence needed by a still-`PENDING` mandatory capability;
- whether a non-broker capability still has higher product/risk leverage than the currently due broker commitment.

A `DUE` broker commitment may be deferred to another slice only with an explicit rationale in the reassessment/readiness record. It may not be omitted from consideration.

This rule does not preassign future slice numbers and does not override the one-capability workflow. Its purpose is to prevent mandatory later broker commitments from becoming invisible backlog prose.

## Product completion boundary

The Broker Workspace Launch Gate and this register answer different questions:

- `BROKER_WORKSPACE_LAUNCH_GATE_STATUS = PASS` means the external professional workspace has the accepted first pilot baseline.
- `BROKER_WORKSPACE_MANDATORY_COMMITMENTS_STATUS = OPEN` means later committed differentiators still remain.
- `BROKER_WORKSPACE_PRODUCT_COMPLETION_STATUS = COMPLETE` means the launch baseline, explicit sales/outcome workflow and every later requirement in this register have actually been implemented and accepted.

Therefore the first broker pilot or public launch may occur before every volume-dependent capability is available, but HullQ must not describe the accepted broker-product workstream as complete while any registered commitment remains `PENDING` or `DUE` or the sale/outcome workflow remains unimplemented.

## Implemented evidence — REQ-BROKER-024

SLICE-0062 is the accepted implementation evidence for REQ-BROKER-024.

Accepted evidence:

- implementation slice: `docs/slices/SLICE-0062-professional-draft-connectivity-recovery.md`;
- normative contract: `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`;
- accepted exact implementation HEAD: `5f7d73e0392136ce260f4e7423a22e51d67a53ff`;
- implementation PR: #234;
- implementation merge commit: `0a48c1d24f0ef98be0793273438ab22cb48f46b4`;
- focused web test coverage for scope isolation, malformed/expired envelopes, exact form-string recovery including cleared fields, storage-unavailable/write-probe behavior, stale-server handling, dirty/pagehide capture behavior and simulated connectivity loss;
- retained real PostgreSQL 18 + FastAPI + built Astro proof through `scripts/inspect_professional_listing_draft_workspace.py`, including recovery wiring, scope data, successful-save marker and no session-cookie leakage;
- independent exact-head ACCEPT review after two targeted amendments;
- exact-head CI run #845 / `35614771938`: SUCCESS;
- exact-head Manufacturer artifact reproducibility run #567 / `35614771811`: SUCCESS;
- explicit Project Owner acceptance recorded 2026-09-21.

Accepted v0.1 behavior is deliberately bounded:

```text
authorized existing ProfessionalListingDraft
+ current server version
+ current browser form edits
→ short-lived Account/Organization/Draft-scoped local recovery
→ connectivity interruption does not silently destroy recent input
→ stale/newer-server recovery never silently overwrites server truth
→ explicit Save remains the only server mutation
```

Browser-local recovery remains convenience state only; FastAPI/PostgreSQL authorization, validation, persistence and optimistic concurrency remain authoritative.

REQ-BROKER-023 remains `PENDING`, therefore the Broker Workspace Launch Gate remains `NOT_READY`.

## Implemented evidence — REQ-BROKER-023

SLICE-0063 is the accepted implementation evidence for REQ-BROKER-023.

Accepted evidence:

- implementation slice: `docs/slices/SLICE-0063-publishing-organization-public-identity.md`;
- normative contract: `specs/PUBLISHING_ORGANIZATION_PUBLIC_IDENTITY_CONTRACT.v0.1.md`;
- accepted exact implementation HEAD: `32077952b3b921c95b506615e1c1a947fbec7ef9`;
- implementation PR: #238;
- implementation merge commit: `7f009564fd8acdbd1e4da1545deb1bde49632fff`;
- Alembic migration `1a6de411f835_publishing_organization_public_display_name.py` adds one bounded non-null `public_display_name` to the existing `marketplace_organizations` row and deterministically backfills existing rows to exact `organization_id`;
- focused unit/persistence/API/web coverage proves bounded normalization, exact punctuation/corporate-suffix preservation, empty/over-limit/control-character rejection, broker-context projection, VAT-independent public publisher identity, legacy exact-ID fallback and non-regression of authorization/listing/Search semantics;
- retained real PostgreSQL 18 + local OIDC/JWKS + FastAPI + built Astro proof: `scripts/inspect_publishing_organization_public_identity.py`;
- retained proof verifies current publisher display identity on Broker Workspace and public listing surfaces, safe escaped rendering, display-name-only rename without NativeListing mutation, legacy unresolved Organization fallback, and unchanged DRAFT/WITHDRAWN/unknown public behavior;
- independent exact-head review initially requested two bounded validation amendments and then returned ACCEPT on the amended head;
- exact-head CI run #855 / `35691401135`: SUCCESS;
- exact-head Manufacturer artifact reproducibility run #577 / `35691401134`: SUCCESS;
- explicit Project Owner acceptance recorded 2026-09-22.

Accepted v0.1 behavior is deliberately bounded:

```text
existing MarketplaceOrganizationId
+ bounded current public_display_name
→ clear current publisher identity in Broker Workspace
→ clear current publisher identity on every readable public NativeListing
→ no dependency on optional VAT/tax claims
→ no second Organization identity
→ no listing/lifecycle/Search/auth mutation
```

`public_display_name` is presentation metadata only: it is not legal/KYB verification, not a Brand/Marque identity and never an authorization selector.

SLICE-0063 does not implement logo/media upload, a public broker profile or Organization self-service administration. Future media handling remains bound by the accepted rule that compliant broker logos/watermarks are not removed solely because they are broker branding; security, privacy, rights and accepted media-normalization rules remain controlling.

REQ-BROKER-023 and REQ-BROKER-024 are now both `IMPLEMENTED`. This satisfies the two addendum launch/pilot-baseline commitment statuses, but it does **not** by itself make the Broker Workspace Launch Gate `PASS`; the remaining launch-gate capability/evidence checklist remains controlling.

## Evidence to mark IMPLEMENTED

A requirement status may become `IMPLEMENTED` only when the repository names:

- the implementing accepted slice(s) or maintenance capability;
- applicable tests/retained proof;
- the relevant broker-facing or API behavior;
- any privacy/security constraints needed for that capability;
- independent review and explicit Project Owner acceptance.

Changing a status marker without that evidence is a governance failure.
