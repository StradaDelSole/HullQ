# HullQ — Production Readiness Gate

**Status:** ACCEPTED OWNER DIRECTION
**Accepted:** 2026-09-13
**Purpose:** one canonical release/data-use gate for operational obligations that must be closed before real external broker production use

<!-- PRODUCTION_READINESS_GATE_STATUS: NOT_TRIGGERED -->
<!-- EXTERNAL_BROKER_PRODUCTION_DATA_STATUS: NOT_PRESENT -->
<!-- PRODUCTION_PILOT_STATUS: NOT_STARTED -->
<!-- PUBLIC_PRODUCTION_LAUNCH_STATUS: NOT_STARTED -->

## Trigger

The gate MUST be `PASS` before any of these becomes true:

```text
1. real external broker data is stored/relied upon as HullQ production data
2. a real external production pilot begins
3. HullQ enters public production launch
```

Whichever threshold comes first controls.

This is deliberately stricter than waiting until broker inventory is publicly visible. The older accepted architecture's HA rule remains a hard latest-allowed minimum for buyer exposure; this gate brings the broader production-readiness review forward to the first real external broker production-data boundary.

`NOT_TRIGGERED` is valid only while broker production data is `NOT_PRESENT`, the production pilot is `NOT_STARTED`, and public production launch is `NOT_STARTED`.

Allowed gate states:

```text
NOT_TRIGGERED
IN_PROGRESS
PASS
```

Allowed broker-production-data states:

```text
NOT_PRESENT
ACTIVE
```

Allowed pilot/launch states:

```text
NOT_STARTED
ACTIVE
```

If broker production data, the production pilot, or public launch is `ACTIVE`, the gate MUST be `PASS`.

This record is intentionally separate from feature prioritization. It makes operational readiness a hard production-data/release condition without forcing premature infrastructure work during local/internal development with synthetic/disposable data.

## Required PASS evidence

Before this gate becomes `PASS`, repository-backed evidence must demonstrate all applicable items below.

### 1. Controlled deployment and rollback

- production deploy uses CI-verified immutable Docker images;
- images are stored in GHCR or an explicitly superseding accepted registry;
- deployed composition/configuration is versioned;
- rollback to the previous known-good image/configuration is documented and tested;
- application hosts are stateless/replaceable with respect to canonical application data.

### 2. Database availability and recoverability

Accepted hard latest-allowed HA threshold from `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` remains preserved:

```text
before real external broker production inventory is exposed to real external buyers
→ production PostgreSQL has automatic failover with at least one standby
```

Because this production-readiness gate is now due at the earlier real-broker-production-data boundary, a PASS intended to cover continuing production use must document the current HA state and the accepted buyer-exposure trigger. If the first production-data phase is strictly internal and HA has not yet been activated, the PASS evidence must explicitly mark HA as still separately gated before any real-buyer exposure; public/pilot exposure may not start until that HA rule is satisfied.

The gate also requires:

- explicit production RTO and RPO;
- automated provider backup where available;
- independent encrypted off-provider/off-database backup, with R2 the accepted direction unless superseded;
- a tested restore proving recoverability rather than backup existence alone;
- documented recovery ownership/runbook sufficient for a solo operator to execute.

A measured RTO, operational-risk or outage-cost requirement may justify HA earlier; it cannot defer HA beyond the accepted hard buyer-exposure trigger.

### 3. Production observability and actionable alerting

- structured application logs sufficient to correlate failures across public web/API/background work;
- production error tracking or equivalent exception capture for web/API paths;
- service/database/dependency health visibility appropriate to the deployed topology;
- actionable alert delivery for failures that require operator intervention;
- no silent critical failure mode relied upon as acceptable monitoring.

Exact provider/tooling is not predetermined by this gate.

### 4. Edge abuse / bot protection

- Cloudflare or an explicitly superseding accepted edge boundary is configured for production ingress protection before public/pilot exposure;
- practical rate/abuse controls protect public Search and other costly/sensitive public endpoints before those endpoints are externally exposed;
- bot/scraping controls are proportionate to current threat/load and do not silently change Search/domain semantics;
- application-level rate limiting is added only where edge controls are insufficient or endpoint semantics require it.

For a strictly internal broker-data phase with no public ingress, external abuse controls may be evidenced as not-yet-applicable, but they become mandatory before pilot/public exposure.

### 5. Secrets and privileged access

- production secrets/credentials are not committed to the repository;
- deployment/database/Auth0/backup credentials have defined storage and rotation/recovery handling;
- least-privilege access is used where practical;
- privileged operational actions are auditable enough for incident/recovery diagnosis.

### 6. Authentication and broker-publishing controls

When real external brokers can authenticate, publish, or manage inventory:

- Auth0 Public Cloud EU tenant is the authentication-only provider unless a later accepted decision supersedes it;
- HullQ PostgreSQL remains authoritative for Account/Organization/Membership/role/listing-ownership/verification/authorization truth;
- privileged broker publishing requires MFA, preferably passkeys/WebAuthn where supported;
- high-risk account/publishing actions use step-up authentication where required by the accepted auth design;
- authorization is enforced server-side at the FastAPI/domain boundary, not trusted to UI state.

If real broker production data is initially operator-assisted and brokers cannot yet authenticate directly, these interactive broker-auth controls may be recorded as not-yet-applicable; they become mandatory before the corresponding capability is exposed.

### 7. Broker media durability, when applicable

If real broker production data contains real broker media:

- rights/use state is explicit enough for the intended production use;
- HullQ has the independently retained production copy required by the accepted architecture rather than depending solely on an external listing URL;
- backup/recovery behavior covers HullQ-owned media as applicable.

If the threshold is reached before media exists, this item may be recorded `NOT_APPLICABLE` with evidence; it is not permission to skip the requirement later when media enters production.

### 8. Release / production-data verification

- production migration procedure is controlled and forward-compatible with the accepted Alembic boundary;
- smoke/health checks exist for the production paths actually being relied upon;
- rollback/recovery behavior has a named operator path;
- production operation does not depend on undocumented local-machine state;
- any strictly internal production-data phase is explicitly distinguished from external pilot/public exposure so later exposure gates cannot be silently skipped.

## PASS record requirement

Changing `PRODUCTION_READINESS_GATE_STATUS` to `PASS` is not a prose-only edit. The same accepted execution work or controlling evidence must name concrete artifacts/tests/configuration/runbooks that satisfy each applicable section and explicitly identify any subcondition that is not yet applicable until external exposure.

Independent review must reject a PASS claim that is supported only by intention or vendor marketing rather than HullQ-controlled evidence.

## Reassessment rule

A PASS gate must be reassessed when a material production boundary changes, including:

- internal real broker production data becoming externally buyer-visible;
- a real production pilot beginning;
- public production launch;
- a major hosting/database/auth/deployment topology change;
- real broker media or direct broker authentication entering production when they were previously not applicable.

Reassessment need not reopen product decisions; it verifies that the operational evidence still satisfies the accepted production boundary.

## Relationship to post-0051 trigger gates

`docs/governance/POST_0051_TRIGGER_GATES.md` owns the trigger timing and workflow obligations. This file owns the operational PASS criteria.