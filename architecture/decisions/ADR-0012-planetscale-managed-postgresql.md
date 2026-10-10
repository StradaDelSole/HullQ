# ADR-0012 — PlanetScale Managed PostgreSQL as the Planned Production Provider

**Status:** PROPOSED — Project Owner preference, subject to independent review and explicit acceptance.
**Date:** 2026-10-10
**Decision scope:** Production PostgreSQL provider substitution only, with staged capacity and mandatory HA/backup gates.
**Reconciles:** `architecture/SYSTEM_ARCHITECTURE.md`; `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §§19–21; `docs/PROJECT_STATE.md`; `docs/operations/PRODUCTION_LAUNCH_CHECKLIST.md`; `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`.

## Context and authority

The accepted September 2 infrastructure rebaseline explicitly chose **DigitalOcean Managed PostgreSQL 18 FRA1** for production. `architecture/SYSTEM_ARCHITECTURE.md` and `docs/PROJECT_STATE.md` still repeat that direction. This is not an implementation accident. Replacing the provider is a significant architecture change and cannot be effected by editing the Phase-1 operator checklist alone.

The Owner subsequently explored the competing PlanetScale PostgreSQL managed offering and explicitly preferred a staged, low-cost rollout. The reason for reopening the provider choice is **material change to DigitalOcean's Standby/Standard plan availability**, threatening the accepted inexpensive single-node-to-standby HA upgrade path; also security, stability and ongoing cost priorities. PlanetScale may offer a more suitable managed HA progression, but exact plan entitlement, regional availability and billing must be proven before any purchase. There is no production cluster at either provider. Neon Free PostgreSQL 18 has passed HullQ legacy/Alembic setup and a read-only Python persistence integration test, strictly for **development/testing**.

## Proposed decision (not effective until independently reviewed and Owner accepted)

Subject to the prerequisites below, adopt **PlanetScale Managed PostgreSQL 18** as HullQ's production-database provider **instead of DigitalOcean Managed PostgreSQL 18**. Do **not** change application/domain/authorization boundaries or the requirement for external managed durable PostgreSQL, and do not replace the existing development database arrangement.

Suggested cost-staging targets (product labels are a hypothesis, NOT a purchase authorization, current quote or capability certification):

1. **Closed/internal production:** start with the smallest verified production-capable single-node PlanetScale PostgreSQL configuration, historically referred to in discussion as **PS-5 Single Node**, if measured CPU/RAM/connection requirements and security/recovery requirements are satisfied.
2. **Before any real external marketplace inventory is exposed to real external buyers:** enable and independently validate automatic failover/HA with **at least one standby**, preferably the discussed **PS-10 ARM three-node HA** topology *if actually offered and suitable*; package names, ARM economics, available regions and replica architecture require current provider proof.
3. **Scale only with measurement**, without implying that either package is sufficient for unknown traffic.

Any model in which broker/owner-direct external buyer exposure bypasses the accepted PostgreSQL HA boundary is prohibited. Changing provider does not relax the Phase-1/Production Readiness or owner-direct/broker exposure gates.

## Non-negotiable security, availability and recoverability criteria

- Managed **PostgreSQL 18**, compatible with actual HullQ SQL, psycopg, SQLAlchemy, Alembic baseline/upgrade, and current test suite. Dedicated private or tightly restricted network access, TLS, account MFA/recovery, least-privilege app/backup/admin principals, rotated credentials and auditability appropriate to production.
- Approved EU data location plus review of processor agreement, backups/WAL locality, disaster-recovery handling, provider sub-processors, cross-border transfers and support access.
- Before external buyer exposure: measured automatic failover with surviving availability zone(s), documented recovery time/data loss characteristics, application reconnect behavior, and retained live-provider HA proof.
- **Two independent recovery layers:** managed provider backup / PITR with verified retention, costs and isolated test restore; PLUS encrypted application-owned logical backups to Cloudflare R2 in a separate restricted bucket, independent credential boundary, retention/integrity validation and isolated restore tests. A replica is not a backup; backup success without a tested restore is not accepted.
- Contabo app host to managed database must have validated latency, TLS and safe connection-pooling/limit behavior, without exposing sensitive DB services to the Internet unnecessarily.
- Release tooling (migrations, rollback, encrypted backup schedule, monitoring, incident response, alerts to Discord only after phase-2 webhook setup) must be validated on real provider configuration; existing SLICE-0079 deployment/recovery mechanisms remain authoritative.
- Document latest all-in EU-region spend scenarios: node/HA usage, compute, disk/storage, WAL/PITR/backup retention, connections, egress, taxes, scaling, and failure-mode bill exposure; no unsupported fixed $5 or $30 total-cost guarantees.

## Alternatives explicitly assessed

- **Keep DigitalOcean:** current accepted baseline and existing documentation fit, but the Standard standby path faces a documented provider-plan discontinuity; a future Advanced-tier migration could alter cost materially. It remains canonical while this ADR is Proposed.
- **PlanetScale:** possible managed PostgreSQL 18 and explicit HA staging with low initial consumption; requires rigorous provider proof for pricing, security, features, availability and restore.
- **Neon Free / paid Neon:** demonstrated compatible with baseline/read-only test for development; Free is not authorized as production. Paid Neon remains a comparison candidate but its precise HA guarantees and pricing are unproven for HullQ.
- **Self-managed PostgreSQL on Contabo:** apparent low line-item cost, but increases operational/security responsibility and does not satisfy the accepted independent managed production database direction without further major rebaseline.

## Decision / implementation reconciliation

- `DECIDED_AND_IMPLEMENTED`: current production stack/managed PostgreSQL 18 architecture as documented; local/Neon dev database and accepted migration mechanisms; provider-independent encrypted backup architecture direction.
- `DECIDED_NOT_YET_IMPLEMENTED`: conditional PlanetScale provider preference, provider access, production resources, real backup/restore and HA, cost and security evidence.
- `EXPLICITLY_DEFERRED`: paid provider account/cluster provision, secrets, live tests, external data and pilot until relevant gates permit them.
- `GENUINELY_OPEN`: current product-region-plan suitability, detailed HA/PITR/retention, EU/legal controls and binding costs.
- `CONFLICT_OR_REGRESSION`: the older DigitalOcean-only accepted provider direction vs the Owner-preferred PlanetScale route; formal replacement requires accepting this ADR and synchronizing the higher-authority architecture references explicitly.

## Acceptance and execution protocol

This draft **does not supersede** the September 2 architecture rebaseline while PROPOSED. Before acceptance: independent exact-HEAD ADR review, explicit Owner acceptance, and a reviewed follow-up amendment to `architecture/SYSTEM_ARCHITECTURE.md`, `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`, `docs/PROJECT_STATE.md` and Launch Checklist, replacing ONLY the provider-specific clauses and preserving HA/security/backup invariants. Any changed implementation capability must follow the normal slice workflow. No provider resources or recurring fees are authorized by this document.

`PRODUCTION_LAUNCH_PACK_PHASE = NOT_STARTED`, `PRODUCTION_READINESS_GATE_STATUS = IN_PROGRESS`, and `SLICE-0081 = UNSELECTED` remain unchanged.
