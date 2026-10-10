# Owner decision — HullQ application hosting and security acceptance (2026-10-10)

**Status:** OWNER-DECIDED — operator planning; deployment evidence NOT YET PROVEN.
**Boundary:** Production Launch Pack Phase 1 (Accounts & Ownership). No VPS purchase, hosting migration, secret provision, pilot or launch authorized.

## Decision

The Project Owner retains **Contabo as the intended initial replaceable Linux application VPS** for HullQ's existing containerized **Astro SSR + FastAPI** stack. Cloudflare DNS/edge remains accepted; **Cloudflare Tunnel is the intended origin ingress topology, subject to technical/security validation before go-live**, not a claim that the tunnel is already deployed or that all risk is eliminated. The existing Docker Compose / GHCR production mechanism remains authoritative unless a future reviewed implementation explicitly changes it.

Owner priorities, in order: **(1) security, (2) operational stability/availability, (3) total recurring costs.** Cloudflare-only or other hosting alternatives were considered but are not selected now. Contabo provisioning and any recurring spend require separate explicit Owner authorization.

**Database boundary:** Neon Free PostgreSQL 18 is development/integration-test only. No production PostgreSQL provider is newly approved by this hosting decision. The existing canonical DigitalOcean production direction / HA constraints remain recorded until separately reconciled through the decision workflow; discussion of alternatives is not an automatic replacement.

## Mandatory operational security acceptance — before purchasing/provisioning the application VPS

Prepare a **testable, evidence-backed, security and reliability acceptance checklist** before VPS provisioning, and use it as a STOP/GO gate before production use. Requirements should include at least:

1. **Threat model / network:** inventory public and internal routes; Cloudflare Tunnel design and authentication of connector; deny-by-default inbound policy; no public Astro/FastAPI/admin/DB ports; no bypass path to origin; deliberate administrative/break-glass path; trust/proxy-header/IP handling.
2. **Host/admin:** supported OS and patch policy; SSH key-only, password/root login restrictions; named privileged access with MFA where supported; logging/time sync; host firewall; recovery from lockout.
3. **Docker/workloads:** unprivileged/minimal images, drop unnecessary capabilities, no privileged containers or exposed Docker socket, resource limits, scoped networks, pinned and scanned release images; preserve accepted session/callback same-host invariant.
4. **Secrets and data:** secret injection/rotation/revocation, least-privilege R2/B2/Auth0/DB credentials, PostgreSQL TLS and network restrictions, controlled egress as needed, no secrets in source/CI logs.
5. **Availability and operations:** deploy/rollback/health checks, restart behavior, monitoring/real alert delivery, patch cadence, independent encrypted backup and restore proof, provider/Cloudflare outage and Tunnel-recovery procedures.
6. **Verification evidence:** actual external reachability/port tests (including IPv6), tunnel/origin-bypass attempts, authorization/cross-tenant and session regressions, dependency/image checks, restore/rollback drills, exact configuration hashes and redacted records.

All applicable critical checks must be **PASS with retained non-secret evidence** before closed production readiness is claimed; identified unresolved security/reliability risks block progression or require the existing explicit risk-acceptance governance. No "bulletproof" security guarantee is asserted. The existing SLICE-0078 adversarial/security acceptance and Production Readiness Gate remain binding; this host-specific checklist supplements them and cannot waive them.

## Reconciliation and status

- **DECIDED_AND_IMPLEMENTED:** Existing Docker/Compose/GHCR deployment foundation; previously accepted Cloudflare edge and Contabo application-host direction.
- **DECIDED_NOT_YET_IMPLEMENTED/PROVEN:** Cloudflare Tunnel deployment/edge-to-origin security posture; host-level hardening/verification; VPS real-provider evidence; mandatory pre-provisioning operational acceptance checklist.
- **EXPLICITLY_DEFERRED:** VPS purchase, secret provisioning, real provider tests and any launch exposure.
- **GENUINELY_OPEN:** Exact VPS size/region/billing, host hardening implementation, final production PostgreSQL provider/HA path, alert destination.
- **CONFLICT_OR_REGRESSION:** None established by this decision; implementation feasibility must still be tested.

Production Launch Pack completed-phase marker remains `NOT_STARTED`; Production Readiness remains `IN_PROGRESS`. SLICE-0081 remains `UNSELECTED`; this record is documentation-only and does not release a code slice.
