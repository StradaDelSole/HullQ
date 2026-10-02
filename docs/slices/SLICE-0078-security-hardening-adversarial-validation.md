# SLICE-0078 — Holistic Security Hardening & Adversarial Validation

**Type:** VALIDATION  
**Status:** READY  
**Stage:** mandatory pre-pilot security gate  
**Depends on:** SLICE-0077 owner-accepted / DONE  
**Normative gate:** `docs/governance/SECURITY_HARDENING_GATE.md`

## Plain-language capability

Treat the coherent broker marketplace as a hostile target before any real external broker is allowed in.

The slice must build and execute a repository-backed attack-surface matrix, adversarially exercise the real buyer/broker flows, fix any Critical/High findings and any Medium findings that are not explicitly risk-accepted by the Project Owner, then retain reproducible proof.

This is not a scanner-only audit and not general cleanup.

## Capability

```text
accepted broker/public attack surface
→ explicit threat matrix
→ adversarial E2E tests
→ severity-classified findings
→ bounded remediation
→ mandatory retest
→ gate disposition
```

## Decision / implementation reconciliation

**Accepted records checked:** `docs/PROJECT_STATE.md`; `docs/slices/SLICE-0077-acceptance-closure.md`; `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md`; `docs/governance/SECURITY_HARDENING_GATE.md`; `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`; `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`; retained SLICE-0076/0077 validation evidence.  
**Already implemented / not re-decided:** accepted auth, tenant, listing, media, Lead, SaleOutcome, performance and broker workflow semantics.  
**Exact remaining gap:** no dedicated holistic adversarial proof yet exists for the coherent pre-pilot product boundary.  
**Accepted-but-unimplemented obligation:** MVP-PROD-012 / mandatory pre-pilot Security Hardening gate.  
**Material classifications:** DECIDED_AND_IMPLEMENTED product foundations; DECIDED_NOT_YET_IMPLEMENTED holistic security gate; EXPLICITLY_DEFERRED external pilot/paid/public launch; GENUINELY_OPEN only security findings/remediation discovered during this slice; CONFLICT_OR_REGRESSION none.

## Trigger gates

**Production readiness gate:** independently controlled / no pilot activation here  
**Broker Workspace Launch Gate:** PASS  
**Broker self-service pilot:** NOT_STARTED  
**Paid broker plan:** NOT_STARTED  
**Security Hardening & Adversarial Validation gate:** DUE / owning slice = 0078  
**Adds technical native Search criterion:** NO  
**Workflow reassessment status:** PASS

## Required work

1. retain an explicit attack-surface matrix using:
   `asset → attacker/trust level → attack path → expected control → adversarial test/proof → finding/disposition`;
2. cover buyer/public, authenticated ordinary Account, broker member, privileged publisher/admin/owner, cross-Organization attacker, hostile browser input, and infrastructure/supply-chain boundaries;
3. adversarially exercise the actual accepted flows:
   - public listing;
   - buyer contact / Lead;
   - broker login / Organization access;
   - listing create/edit/publish/withdraw/reconfirm;
   - media;
   - Lead handling including assignment;
   - SaleOutcome;
   - performance snapshot;
4. test the canonical security-gate domains:
   - auth/session/MFA;
   - multi-tenant/IDOR/enumeration;
   - CSRF/Origin/browser headers/XSS/framing/private-cache behavior;
   - malformed/oversized/input abuse;
   - PostgreSQL/concurrency/idempotency/rollback;
   - media/object-storage boundary;
   - abuse/rate protection;
   - secrets/config/supply-chain;
   - privacy/PII/logging;
   - deployment/infrastructure configuration;
5. classify every finding as CRITICAL / HIGH / MEDIUM / LOW / INFO with evidence and disposition;
6. fix all Critical and High findings inside this slice and retest;
7. fix Medium findings unless explicitly retained for Project Owner risk acceptance;
8. do not expand into unrelated product features;
9. produce reproducible retained proof and exact-head remote verification.

## Required outputs

At minimum:

```text
docs/validation/SECURITY_ATTACK_SURFACE_MATRIX_2026-10.md
docs/validation/SECURITY_ADVERSARIAL_EVIDENCE_2026-10.md
docs/validation/SECURITY_FINDINGS_REGISTER_2026-10.md
docs/validation/SECURITY_HARDENING_GATE_EVIDENCE_2026-10.md
```

Test/harness code must live with the normal repository test/validation tooling, not as prose-only evidence.

## Acceptance threshold

The slice may recommend PASS only when:

```text
open CRITICAL = 0
open HIGH = 0

material MEDIUM =
  fixed
  OR explicitly Project-Owner risk-accepted

cross-tenant adversarial suite = PASS
authentication/MFA adversarial suite = PASS
media/privacy adversarial suite = PASS
dependency/supply-chain review = PASS
production-security configuration review = PASS
required retained proof = PASS
repository validation = PASS
exact-head CI = SUCCESS
Manufacturer artifact reproducibility = SUCCESS
```

Scanner-only evidence is insufficient.

## Stop / escalation rules

Do not silently weaken accepted security or product semantics to make tests pass.

If a finding requires a material new architecture/domain/privacy/product decision, stop that finding and report it for independent decision rather than inventing policy.

If a Critical/High issue cannot be safely fixed within this slice, recommended state must be BLOCKED and the external pilot remains prohibited.

## Non-goals

- external broker pilot;
- production launch;
- paid subscriptions;
- broad visual UX polish;
- unrelated broker feature work;
- owner-direct expansion;
- new Search criteria;
- generalized security platform unrelated to HullQ's current attack surface.

## Status handoff

Agent may recommend `REVIEW` / `BLOCKED`; must not mark DONE, activate a pilot or start another slice.

Initial execution prompt comes only from `START_SLICE.bat` after readiness review/gates/merge.
