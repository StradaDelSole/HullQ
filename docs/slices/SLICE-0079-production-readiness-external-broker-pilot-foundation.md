# SLICE-0079 — Production Readiness & External Broker Pilot Foundation

**ID:** SLICE-0079  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** pre-production operational foundation  
**Depends on:** SLICE-0078 owner-accepted / DONE  
**Blocks:** any real external marketplace production data, any real external production pilot, and public production launch until the canonical Production Readiness Gate is PASS

## Objective

Build and retain the concrete operational evidence required to move HullQ's canonical Production Readiness Gate from `IN_PROGRESS` to `PASS` for the first bounded professional-broker production boundary, without starting that pilot.

## Plain-language capability

Make HullQ operationally safe to run with real broker data.

This slice does not add a buyer or broker feature. It turns the accepted production architecture into a reproducible, operator-usable production foundation: controlled deploy/rollback, backups and restore proof, RTO/RPO, monitoring/alerts, secrets handling, edge protection, health/smoke checks, migration/release procedures and retained gate evidence.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One coherent capability: Production Readiness Gate implementation and evidence for the bounded first professional-broker production boundary.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can inspect the retained production-readiness matrix/runbooks, execute or inspect the deployment/rollback/restore/smoke proofs, and review one explicit PASS/BLOCKED gate disposition.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This slice implements the already-accepted `docs/governance/PRODUCTION_READINESS_GATE.md` and the accepted lean production architecture. It does not create a new production topology or start a pilot.

**REPOSITORY RECONCILIATION CHECK:** PASS  
Post-SLICE-0078 reconciliation confirmed the product/security launch gates are PASS and the exact remaining operational gap is the Production Readiness Gate.

**TRIGGER GATES CHECK:** PASS  
Real external production data and the production pilot remain NOT_STARTED/NOT_PRESENT. The canonical Production Readiness Gate is moved to `IN_PROGRESS` for this work and must reach `PASS` before any trigger condition becomes active.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
Production operations are now the highest-leverage hard boundary. Broker export, periodic reporting and Search-fit diagnostics are required before paid/broad public launch, while this gate is required before any real external production data or pilot.

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/POST_SLICE_0078_REASSESSMENT_2026-10-03.md`; `docs/governance/PRODUCTION_READINESS_GATE.md`; `docs/governance/POST_0051_TRIGGER_GATES.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`; `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`; SLICE-0078 acceptance/security evidence.  
**Production implementation checked:** repository root/TREE and GitHub Actions workflows (no Dockerfile, production Compose or GHCR deploy workflow currently exists); PostgreSQL/Alembic configuration and migration validation; current FastAPI/Astro configuration boundaries; Auth0/session production configuration; R2 object-storage boundary; current CI/reproducibility workflows; SLICE-0078 security/rate-limit/header evidence and tests.  
**Already implemented / not re-decided:** broker product workflow; Broker Workspace Launch Gate PASS; Security Hardening Gate PASS; accepted Astro/FastAPI/PostgreSQL/Auth0/GHCR/Compose/R2 architecture; server-side authorization; current domain/search/listing truth.  
**Exact remaining gap:** the accepted production deployment direction is not yet implemented as production packaging/deploy artifacts (no Dockerfile, production Compose or GHCR deploy workflow exists on canonical main), and repository-backed PASS evidence is also missing for rollback, recoverability, observability/alerting, edge abuse controls, secrets/privileged access and release/migration/smoke operations.  
**Accepted-but-unimplemented obligations:** Production Readiness Gate §§1–8; MVP-PROD-001..009 as applicable to the bounded first broker production boundary; buyer-contact email verification remains separately trigger-bound before real external buyer-contact; database HA remains mandatory before real external inventory is exposed to real external buyers.  
**Material classifications:** DECIDED_AND_IMPLEMENTED broker/security/architecture baseline; DECIDED_NOT_YET_IMPLEMENTED production-readiness operational evidence; EXPLICITLY_DEFERRED actual pilot/paid/public launch and unrelated feature expansion; GENUINELY_OPEN provider choice where governance intentionally does not prescribe a vendor; CONFLICT_OR_REGRESSION stale MVP-PROD-012 DUE marker corrected by readiness publication.

## Trigger gates

**Production readiness gate:** IN_PROGRESS  
**Adds technical native Search criterion:** NO  
**Technical Search criterion ordinal:** NOT_APPLICABLE  
**Second-criterion bridge comparison:** NOT_APPLICABLE  
**Third-copy abstraction guard:** NOT_APPLICABLE  
**Workflow reassessment status:** PASS  
**Broker Workspace Launch Gate:** PASS  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Security Hardening & Adversarial Validation gate:** PASS

## Why this slice exists

The professional product path is now launch-capable at the product/security level, but HullQ may not store or rely on real external seller/listing production data or begin a real external pilot until the canonical Production Readiness Gate is PASS.

Continuing feature expansion before this boundary would increase the amount of product sitting behind an unproven operational platform and would not reduce the next hard launch risk.

## Controlling artifacts

- Normative gate: `docs/governance/PRODUCTION_READINESS_GATE.md`
- Trigger governance: `docs/governance/POST_0051_TRIGGER_GATES.md`
- Architecture: `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- Execution priority: `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`
- Overall MVP register: `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`
- Security evidence: `docs/slices/SLICE-0078-acceptance-closure.md` and `docs/validation/SECURITY_HARDENING_GATE_EVIDENCE_2026-10.md`
- Requirement IDs: MVP-PROD-001 through MVP-PROD-009 as applicable; MVP-PROD-012 already implemented by SLICE-0078
- Open question in scope only where necessary: concrete observability/alerting provider/tool choice if repository evidence shows no accepted provider already exists

## In scope

1. Controlled deploy/rollback implementation and evidence:
   - create the missing repository-owned production container/package/deploy artifacts required by the accepted architecture rather than assuming they already exist;
   - CI-verified immutable image path;
   - GHCR/versioned Compose or accepted equivalent;
   - documented/tested rollback to previous known-good version;
   - stateless application-host assumptions made explicit and mechanically checked where feasible.

2. Database recoverability:
   - production PostgreSQL target/configuration evidence;
   - explicit RTO/RPO;
   - provider backup assumptions documented;
   - independent encrypted backup mechanism using accepted off-database storage direction;
   - actual restore test against a disposable target;
   - solo-operator recovery runbook;
   - HA state explicitly recorded, including the hard buyer-exposure trigger if HA is not yet active.

3. Observability/alerting:
   - structured application logs;
   - exception/error capture or equivalent;
   - service/database/dependency health visibility;
   - actionable operator alert path;
   - retained evidence that critical failure does not rely on silent manual discovery.

4. Edge/public abuse readiness:
   - production ingress/Cloudflare boundary configuration evidence;
   - practical rate/abuse controls for public Search and costly/sensitive endpoints appropriate to the first bounded broker production boundary;
   - explicit distinction between internal real-data readiness and later public/buyer exposure requirements.

5. Secrets and privileged access:
   - production secret sources and non-repository handling;
   - rotation/recovery handling for deployment/database/Auth0/backup credentials where applicable;
   - least-privilege roles where practical;
   - auditable privileged operational actions sufficient for recovery/incident diagnosis.

6. Release/data verification:
   - production migration procedure;
   - health/smoke checks for relied-upon production paths;
   - release/rollback/recovery runbook;
   - no undocumented local-machine dependency;
   - retained proof naming the exact supply/exposure boundary covered by PASS.

7. Canonical Production Readiness Gate evidence and status transition to PASS only if every applicable criterion is actually proven.

## Explicitly out of scope

- starting or recruiting the external broker pilot;
- storing real external broker/seller/listing production data during this slice;
- public production launch;
- paid broker-plan activation;
- owner-direct admission/publication;
- new Search criteria or buyer-facing ranking logic;
- broker inventory export;
- periodic analytics delivery;
- Search-fit diagnostics;
- structured bulk import/onboarding;
- broad redesign to Kubernetes, Coolify/Dokploy, distributed services or a new auth/database architecture;
- pretending a provider capability exists when it has not been configured/tested.

## Required behavior

### Production gate truth

The slice MUST NOT set `PRODUCTION_READINESS_GATE_STATUS = PASS` based only on plans, vendor marketing or documentation.

For every applicable gate subsection, retained evidence must identify:

`requirement → concrete artifact/configuration → executed proof/test → result → residual trigger/limitation`.

Any condition deferred because the first boundary remains strictly internal must be stated as such and must retain its later hard trigger.

### Database HA boundary

If automatic failover/standby is not actually active by the end of this slice, the gate evidence may only PASS a strictly internal production-data phase if the canonical gate permits it and the retained evidence states:

`NO REAL EXTERNAL BUYER EXPOSURE UNTIL HA REQUIREMENT IS SATISFIED`.

This slice must not weaken that accepted rule.

### Security carry-forward

SLICE-0078 controls remain required. SEC-0078-07 re-review triggers remain in force. Production-readiness work must not bypass or silently disable the accepted security controls.

### Buyer-contact trigger

The existing buyer-contact email-verification trigger remains separate. A Production Readiness PASS does not authorize real external buyer-contact exposure while `BUYER_CONTACT_EMAIL_VERIFICATION_STATUS` remains PENDING.

## Required outputs

At minimum:

```text
docs/validation/PRODUCTION_READINESS_EVIDENCE_2026-10.md
docs/operations/PRODUCTION_DEPLOY_ROLLBACK_RUNBOOK.md
docs/operations/PRODUCTION_BACKUP_RESTORE_RUNBOOK.md
docs/operations/PRODUCTION_RELEASE_MIGRATION_RUNBOOK.md
docs/operations/PRODUCTION_INCIDENT_OBSERVABILITY_RUNBOOK.md
```

Add or update executable scripts/tests/configuration needed to prove the gate. Evidence-only prose is insufficient where an executable proof is feasible.

## Acceptance criteria

- [ ] controlled production deploy path is repository-defined and uses CI-verified immutable images;
- [ ] rollback to a previous known-good release is documented and mechanically/procedurally proven;
- [ ] application-host statelessness assumptions are explicit;
- [ ] RTO and RPO are explicit and consistent with the tested recovery path;
- [ ] independent encrypted backup mechanism exists and a restore to a disposable target is successfully executed;
- [ ] PostgreSQL HA state and hard buyer-exposure trigger are explicit;
- [ ] production logs/error capture/health visibility/actionable alert path are configured or reproducibly evidenced for the covered boundary;
- [ ] production ingress/edge abuse controls are configured/evidenced for the covered boundary;
- [ ] production secrets/privileged-access handling is documented and no secret is committed;
- [ ] production migration, smoke, rollback and recovery operator procedures are retained;
- [ ] evidence explicitly states which supply/exposure boundary the PASS covers;
- [ ] no real external production data or pilot is started by this slice;
- [ ] `MVP-PROD-012` stale status is reconciled to SLICE-0078 IMPLEMENTED/PASS;
- [ ] canonical Production Readiness Gate is changed to PASS only after all applicable evidence is verified;
- [ ] repository validation passes;
- [ ] exact-head GitHub Actions CI succeeds;
- [ ] Manufacturer artifact reproducibility succeeds;
- [ ] independent exact-head implementation review accepts the final candidate;
- [ ] explicit Project Owner acceptance occurs before implementation merge.

## Expected touch points

Expected areas include:

```text
.github/workflows/
Dockerfile* / docker-compose*.yml / new production deployment configuration
scripts/
src/hullq/ operational/config/logging/health boundaries as necessary
docs/operations/
docs/validation/
docs/governance/PRODUCTION_READINESS_GATE.md
docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md
docs/PROJECT_STATE.md only through normal closure/state workflow
tests/
```

Do not introduce an unrelated deployment platform or product feature.

## Validation

Implementation must run the repository's normal validation plus focused production-readiness proofs. At minimum:

```bash
uv run python scripts/validate_repository.py
uv run pytest <focused production-readiness / configuration tests>
```

Where Docker/database/backup/restore tooling is added, run the actual executable proof against disposable/non-production resources. Never claim a restore/deploy/rollback PASS from static inspection alone.

Remote exact-head requirements remain:

```text
GitHub Actions CI = SUCCESS
Manufacturer artifact reproducibility = SUCCESS
```

## Stop conditions

Stop and report instead of inventing a PASS when:

- production credentials/provider access required for a mandatory proof are unavailable;
- an accepted production architecture decision materially conflicts with the implementation required for PASS;
- backup exists but restore cannot be demonstrated;
- required observability/alert delivery cannot be demonstrated;
- the implementation would require storing real external production data merely to prove readiness;
- a gate subsection is neither proven nor validly NOT_APPLICABLE for the bounded first production phase;
- automatic failover is absent while the proposed PASS would expose real external inventory to buyers;
- buyer-contact verification is still pending but the proposed boundary would expose real external buyer-contact;
- implementation would silently start a pilot, public launch or paid plan;
- a new material production/privacy/security policy decision is required.

A stopped slice should recommend `BLOCKED` with the exact missing evidence/provider dependency, not weaken the gate.

## Status handoff rule

The implementation agent may recommend `REVIEW` or `BLOCKED`, but MUST NOT mark this slice `DONE`.

## Required completion report

Use the repository-standard completion report in `docs/slices/SLICE_TEMPLATE.md`. Keep it compact, identify the exact final branch HEAD and distinguish local proof from externally observed CI/provider evidence.
