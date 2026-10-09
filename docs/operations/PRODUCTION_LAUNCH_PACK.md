# HullQ Production Launch Pack

**Status:** OWNER-ACCEPTED OPERATING PROCEDURE  
**Accepted:** 2026-10-08  
**Purpose:** deterministic solo-operator path from production-account provisioning to public HullQ launch without a big-bang cutover

## Operating invariant

HullQ MUST NOT be taken from local/development state directly to public production in one cutover.

The production path is deliberately staged:

```text
1. Accounts & Ownership
2. Secrets & Connections
3. Closed Production Infrastructure
4. Closed HullQ Production Deploy
5. Internal Real Operation
6. Bounded External Broker Pilot
7. Public Production Launch
```

A later phase may begin only when the prior phase's required evidence is complete and the controlling Production Readiness / workflow gates permit it.

No phase transition is implied by infrastructure merely existing. Creating an account, database, VPS, DNS record, production image or deployment does not by itself authorize external data, a pilot, buyer exposure or public launch.

## Canonical phase state

The current completed launch phase is recorded in `docs/PROJECT_STATE.md` as:

```text
PRODUCTION_LAUNCH_PACK_PHASE: NOT_STARTED | 1 | 2 | 3 | 4 | 5 | 6 | 7
```

This marker is authoritative for sequencing. A future production-phase slice must declare the same current value as its before-phase and may hold it or advance by at most one phase. Self-declaring a later before-phase is invalid even when the slice's own before/after pair looks sequential.

The marker advances only after the current phase's **Done when** evidence is complete. When a slice owns that completion, its acceptance closure updates the marker atomically. When the work is pure provider-console provisioning outside a slice, a separately reviewed repository maintenance change records the evidence and advances the marker. Merely creating an account, resource, DNS record or deployment never advances the phase by itself.

Current state after SLICE-0079 acceptance:

```text
PRODUCTION_LAUNCH_PACK_PHASE = NOT_STARTED
```

## Operator rule

Production setup is executed one service and one verified dependency at a time.

For each step:

```text
provision/configure
→ record where ownership/recovery lives
→ place secrets only in the designated secret store
→ run the defined done-when verification
→ record PASS/BLOCKED
→ only then continue
```

Do not open/configure a batch of unrelated production accounts and rely on memory to reconcile them later.

The Project Owner should not need to infer the next infrastructure action. The active launch checklist/runbook must state the exact next step, required inputs, expected result and stop condition.

## Secret-handling invariant

This pack records only:

- secret/credential NAME;
- owning service/account;
- intended secret store/destination;
- purpose;
- rotation/recovery requirement where applicable.

It MUST NOT contain actual passwords, API keys, tokens, private keys, recovery codes or other secret values.

Examples of acceptable notation:

```text
AUTH0_CLIENT_SECRET
→ GitHub Environment: production
→ used by HullQ production auth integration

DEPLOY_SSH_KNOWN_HOSTS
→ GitHub Environment: production
→ pinned production host identity
```

Actual values stay in the applicable provider/secret store.

## Phase 1 — Accounts & Ownership

### Goal

Every required production service has a deliberate account owner, billing owner and recovery path before runtime configuration begins.

### Launch-pack inventory

For every service required by the accepted architecture or current production boundary, record:

| Field | Required |
|---|---|
| Service/provider | YES |
| HullQ purpose | YES |
| Account/organization owner | YES |
| Login email / ownership identity description | YES, but no secret |
| MFA enabled | YES where supported |
| Recovery method documented | YES |
| Billing owner / tariff | YES where applicable |
| Region/data-residency choice | YES where applicable |
| Required before pilot / before public launch / later | YES |
| Status | NOT_STARTED / IN_PROGRESS / PASS / BLOCKED |

The inventory includes all actually required providers at launch time, for example GitHub/GHCR, DigitalOcean, Cloudflare/R2, Auth0 and any then-accepted production mail/helpdesk/monitoring providers. The list must be reconciled against canonical repository decisions at execution time rather than treated as permanently frozen here.

### Done when

- no required production service has unknown ownership;
- MFA/recovery is configured where available;
- billing/plan/region choices needed for the next phase are explicit;
- no production secret values have been copied into repository documentation.

## Phase 2 — Secrets & Connections

### Goal

Every production dependency can authenticate/connect using least-privilege credentials stored in the correct secret boundary.

### Required mapping

For each production credential, record:

| Field | Required |
|---|---|
| Secret name | YES |
| Source service | YES |
| Destination secret store | YES |
| Runtime consumer | YES |
| Least-privilege scope | YES where applicable |
| Rotation/recovery procedure | YES where applicable |
| Connectivity test | YES |
| Status | NOT_STARTED / IN_PROGRESS / PASS / BLOCKED |

Expected destinations may include the GitHub `production` Environment, provider-native secret storage or another accepted runtime boundary. Do not create a second informal secret store.

### Done when

- required credentials exist in the accepted secret store;
- connectivity/authentication tests succeed without exposing secret values;
- production SSH host identity is independently pinned before automated SSH;
- missing/invalid credentials fail closed.

## Phase 3 — Closed Production Infrastructure

### Goal

Create production infrastructure without external users, external production data or public launch.

This phase includes the infrastructure actually required by the accepted architecture, such as:

- production PostgreSQL;
- application host/VPS;
- production ingress/DNS/edge boundary;
- independent backup destination;
- monitoring/alert delivery;
- durable image registry;
- required network/access restrictions.

### Done when

- infrastructure exists in the accepted region/topology;
- backup and restore mechanisms are configured and verified as required by the Production Readiness Gate;
- health/observability paths work;
- DNS/edge configuration can be tested without opening the marketplace to users;
- applicable HA threshold is satisfied before any buyer exposure;
- no real external broker/owner-direct production data or pilot has begun unless the gate already explicitly permits it.

## Phase 4 — Closed HullQ Production Deploy

### Goal

Run the real production deployment while HullQ remains closed to external use.

Required verification includes, as applicable:

- exact CI-approved immutable images;
- exact release/image identity;
- production migration;
- smoke checks;
- authentication boundary;
- rollback;
- alert delivery;
- backup/recovery path;
- host replacement/recovery assumptions;
- DNS/TLS/edge behavior;
- secrets and privileged access.

### Done when

- the exact deployed release is known;
- smoke/health checks pass;
- rollback path is operationally verified at the required level;
- monitoring/alert delivery is actionable;
- deployment does not imply pilot/public authorization;
- unresolved production-provider evidence is recorded as BLOCKED rather than inferred PASS.

## Phase 5 — Internal Real Operation

### Goal

Operate the real production stack under a strictly internal boundary before inviting external brokers.

This phase is not a shortcut around the Production Readiness Gate. Any real-production-data use must satisfy the canonical gate state applicable at that time.

Run through the actual operator paths needed for the upcoming pilot, including:

- login/MFA/privileged access;
- broker/admin workflows needed for support;
- listing lifecycle;
- media path where applicable;
- lead/contact path where applicable;
- monitoring/alerts;
- backup/restore/recovery ownership;
- incident/rollback procedure.

### Done when

- the intended pilot path has been exercised end to end;
- no critical operator step depends on undocumented knowledge;
- all applicable readiness gates are PASS;
- any separately gated buyer-exposure requirement, including PostgreSQL HA, is satisfied before buyer exposure.

## Phase 6 — Bounded External Broker Pilot

### Goal

Invite a deliberately small number of real external brokers only after the required production gates permit it.

Pilot controls must define:

- named/bounded participant scope;
- allowed features/data;
- support/contact path;
- incident/rollback stop criteria;
- monitoring cadence;
- feedback capture;
- explicit prohibition on silently expanding into public launch.

### Done when

- pilot participants can complete the intended workflow;
- operational failures are understood and resolved or explicitly accepted;
- support/recovery procedures work in practice;
- the Project Owner has enough evidence to make a separate public-launch decision.

## Phase 7 — Public Production Launch

### Goal

Open HullQ publicly only after a separate readiness/reassessment confirms that pilot evidence, buyer-exposure requirements and all public-edge obligations are satisfied.

Public launch MUST NOT be inferred from a successful pilot.

Before launch, explicitly verify at least:

- Production Readiness Gate PASS;
- public/buyer exposure prerequisites, including the accepted PostgreSQL HA threshold;
- public DNS/edge protection;
- abuse/rate controls;
- authentication/authorization/trust boundaries;
- support/helpdesk path;
- privacy/legal obligations due at public launch;
- monitoring/alerts;
- backup/restore;
- rollback/incident procedure;
- billing/cost guardrails for enabled providers.

## Central launch checklist structure

When the real production setup begins, maintain one active operator checklist derived from this pack.

Each checklist row should contain:

| Field | Meaning |
|---|---|
| Phase | 1–7 above |
| Step | concrete operator action |
| Service | provider/component |
| Owner | account/operational owner |
| Required input | non-secret description |
| Secret names/destinations | names only, never values |
| Exact action | what to configure |
| Done-when verification | executable/observable PASS condition |
| Cost/tariff | current operational cost where applicable |
| Required before | pilot / buyer exposure / public launch |
| Status | NOT_STARTED / IN_PROGRESS / PASS / BLOCKED |
| Evidence | repository/runbook/provider evidence reference |

The checklist should be executed sequentially unless an accepted runbook explicitly marks two steps independent.

## Stop conditions

Stop rather than improvise when:

- account ownership or recovery is unclear;
- a required provider plan/region choice would change accepted architecture or cost materially;
- a secret destination is unclear;
- a credential would need to be placed in source control;
- provider behavior differs materially from retained readiness assumptions;
- a required production proof cannot be executed;
- a prior phase is not PASS;
- a gate required for external data, pilot, buyer exposure or public launch is not PASS;
- completing the step would silently broaden external exposure.

A stop condition becomes a normal HullQ blocker/reconciliation item. It is not permission to bypass the phase order.

## Relationship to SLICE workflow

This operator procedure does not replace the HullQ slice lifecycle.

Repository/product/architecture changes discovered during launch still follow the normal workflow:

```text
reconciliation
→ capability/readiness
→ independent review
→ implementation
→ exact-head review
→ Owner Acceptance
→ merge/closure
```

Pure provider-console provisioning that implements an already-accepted configuration may be executed from this operator checklist without inventing a new product decision, but its required evidence must still be captured where the controlling readiness/runbook expects it.

No next slice, external pilot or public launch is automatically authorized by completing a production-setup step.
