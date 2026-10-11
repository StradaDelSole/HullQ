# HullQ Production Launch Checklist

**Status:** ACTIVE — Phase 1 not complete  
**Controlling procedure:** `docs/operations/PRODUCTION_LAUNCH_PACK.md`  
**Canonical launch phase:** `NOT_STARTED`  
**Started:** 2026-10-09  
**Secret rule:** this file stores secret names/status only. Never place passwords, tokens, API keys, private keys, recovery codes or secret values here.

## Current execution boundary

The active operator goal is:

```text
Phase 1 — Accounts & Ownership
```

Post-SLICE-0080 reconciliation deliberately selects this provider/account work instead of opening SLICE-0081.

No production launch phase advances until the complete Phase-1 Done-when conditions are evidenced and a reviewed repository maintenance/closure change updates `PRODUCTION_LAUNCH_PACK_PHASE`.

SLICE-0080 is Owner-accepted and merged: the repository mechanism for provider-independent broker-original media redundancy now exists. This still does not advance the launch phase; the real Backblaze account/bucket/application-key and live-provider proof remain operator work.

## Already observed

| Item | Evidence | Status |
|---|---|---|
| Canonical GitHub repository exists under `StradaDelSole/HullQ` | canonical repo/main | PASS |
| GHCR publication path is usable under the repository namespace | Deploy run #28 / run id `37868264887`, main SHA `5532cd2cc13d9e2ce8bcee90cfc7f0591f14ae9a`; API and web publish jobs SUCCESS | PASS |
| Product/security pre-pilot repository gates | Broker Workspace Launch Gate PASS; Security Hardening Gate PASS | PASS |
| Production Readiness Gate | real provider configuration still incomplete | IN_PROGRESS |

## Phase 1 — Accounts & Ownership inventory

Statuses in this table are account/ownership setup states only. They do not imply the runtime service is provisioned or production-ready.

| Service / account | Accepted HullQ purpose | Required timing | Account/ownership evidence | MFA / recovery evidence | Billing / region decision | Phase-1 status |
|---|---|---|---|---|---|---|
| GitHub / GHCR | canonical source, Actions, immutable container registry | now | repository and GHCR path proven under StradaDelSole | Microsoft Authenticator MFA and recovery codes secured (Owner-attested) | GitHub Free intended; precise billing/usage not independently checked | OWNER_SECURITY_CONFIRMED |
| HullQ domain registrar / `hullq.com` ownership | authoritative domain control before DNS/edge | before production DNS work | Namecheap domain paid, auto-renew enabled; Cloudflare nameservers active (Owner-attested) | MFA active; recovery codes secured | renewal evidence Owner-attested | OWNER_SECURITY_CONFIRMED |
| Cloudflare | DNS/proxy/edge; primary media R2; independent encrypted DB-backup R2 | before closed production infrastructure | DNS active, R2 activated (Owner-attested) | MFA and backup codes secured | production bucket/keys, EU placement and billing evidence remain | OWNER_SECURITY_CONFIRMED_DETAILS_OPEN |
| Contabo | selected replaceable application VPS; Cloudflare Tunnel intended pending proof | before closed production infrastructure | account enrollment tied to first VPS order; deliberately deferred | account MFA/recovery at purchase, not yet possible to evidence | paid VPS not yet authorized; security acceptance catalogue required before provisioning | PURCHASE_GATED_DEFERRED |
| Production PostgreSQL (accepted target: PlanetScale) | Accepted ADR-0012 selects PlanetScale Managed PostgreSQL 18, with provisional PS-5 closed → PS-10 ARM three-node HA pre-buyer-exposure sizing | before closed production infrastructure | PlanetScale account exists and automatically created organization `gerhard-hullq` (Owner-attested 2026-10-11); organization billing/ownership controls not independently evidenced; no production cluster evidenced | MFA active and recovery keys securely stored (Owner-attested 2026-10-11) | Actual plan, billing, EU region, HA, PITR, independent restore and security proof pending; no purchase authorized | OWNER_SECURITY_CONFIRMED_PROVISIONING_DEFERRED |
| Auth0 Public Cloud | EU authentication-only tenant | before real interactive broker authentication | Owner confirmed Hullq_Dev EU dev tenant | Auth0 Guardian MFA and recovery codes secured | production tenant/config and billing evidence later | DEV_ACCOUNT_SECURED_PROD_PENDING |
| Discord Free operator alerts | current Slack/Discord webhook mechanism; Owner-selected Discord Free channel | webhook delivery before Production Readiness PASS | private HullQ Operations server and #production-alerts channel confirmed | Discord account MFA and recovery codes secured | Free plan; webhook and real delivery deferred to Phase 2 | OWNER_SETUP_CONFIRMED_PHASE2_PENDING |
| Backblaze B2 EU Central | independent second copy of broker original/source media, separate from primary Cloudflare R2 | before real broker production media; mechanism accepted in SLICE-0080 | Owner confirmed EU account active; no bucket yet | MFA and recovery codes secured (Owner-attested) | usage-based billing; no billing method yet; bucket/key and proof later | ACCOUNT_SECURED_PROVIDER_PROOF_PENDING |
| Zammad Hosted Professional v2 | customer Help/Support system | before external support launch | accepted target; paid account/trial not yet activated; local license-free Community permitted for development tests only | hosted trial deferred until acceptance-ready; hosted branding/privacy validation required | explicit Owner cost/plan approval only when paid external support is due | LATER_TRIGGER |
| Transactional email provider | real external lead/account email delivery when relied upon | before real external email dependency | no accepted concrete provider yet | later | later provider decision | LATER_TRIGGER |

## Secondary broker-original media provider decision

Accepted invariant:

```text
primary broker media = Cloudflare R2
original/source media before real broker production
→ independent second copy at a DIFFERENT storage provider
```

The secondary provider must not become MediaAsset/domain identity and should be consumed through an S3-compatible/provider-abstracted HullQ boundary.

Owner decision: **Backblaze B2 EU Central**.

The accepted choice preserves provider independence from Cloudflare, uses an EU data region, provides an S3-compatible integration surface and fits the project's highly constrained MVP budget. The provider decision is retained in `docs/BROKER_ORIGINAL_MEDIA_REDUNDANCY_PROVIDER_DECISION_2026-10-09.md`.

SLICE-0080 implementation is Owner-accepted; the real account/bucket/application key, secret-store wiring and live connectivity proof remain Phase-1/Phase-2 operator work and were not created by the slice.

## Owner hosting/security decision (2026-10-10)

The Project Owner reaffirmed **Contabo** as the intended application VPS, with **Cloudflare Tunnel as proposed ingress**, pending independent operational proof. Priorities: security, stability/availability, then total cost. **No VPS purchase or production exposure is authorized.**

Before actual VPS procurement/provisioning, prepare an explicit security/reliability acceptance catalogue with testable STOP/GO checks; run and retain the relevant evidence before any production operation. Scope includes host/admin hardening, edge/tunnel origin isolation, container boundaries, secret handling, monitoring, backups/recovery, external validation and the accepted Auth0/session and security gates.

Controlling Owner record: `docs/operations/CONTABO_CLOUDFLARE_SECURITY_DECISION_2026-10-10.md`.

The separate production PostgreSQL provider/HA decision is **not changed** by this hosting choice; Neon Free is dev/test-only. No production phase marker advances and SLICE-0081 remains unselected.

## Owner-reported Phase-1 account evidence (2026-10-10 to 2026-10-11)

The Project Owner confirmed the following facts during live setup. These are **Owner-attested account/security states**, not independent provider-admin screenshots or secret material; no recovery codes or credentials are retained here.

| Account/provider | Confirmed evidence | Remaining boundary |
|---|---|---|
| GitHub/GHCR | Account MFA via Microsoft Authenticator; recovery codes securely stored; owner intends GitHub Free; repository and GHCR build/publish previously verified | Actual billing configuration, usage caps and any plan exceptions not independently inspected |
| Namecheap / hullq.com | Registrar MFA enabled; recovery codes stored; domain paid and auto-renew enabled; Cloudflare nameservers working | Actual registrar/renewal evidence remains owner-attested |
| Cloudflare | MFA enabled; backup codes secured; authoritative DNS operational; R2 activated under existing account | R2 production buckets/keys, detailed billing/data placement and operational security proof later |
| Backblaze B2 | EU account established; MFA enabled; backup codes secured; **no billing method and no bucket yet** | Billing decision and isolated bucket/key/live proof deferred to relevant phase; no real-provider B2 proof claimed |
| Auth0 | Hullq_Dev tenant, EU Auth0 domain; MFA via Auth0 Guardian and recovery codes secured | Production tenant/configuration, recovery/ownership evidence and secrets not yet proven |
| Discord | Separate HullQ operational account created; MFA and recovery codes secured; private `HullQ Operations` server and `#production-alerts` channel created; Discord Free chosen | No webhook created or alert-delivery proof; defer to Phase 2 / Production Readiness |
| Neon Free | Development/test PostgreSQL 18.6 in Frankfurt, branch `hullq-development`; legacy baseline and Alembic head `b6f3d9a0c452`; 50 public tables, 59 FKs; read-only HullQ persistence connection test PASS | **Development only**; not an approved production PostgreSQL provider or production-readiness proof |
| Contabo | Owner retains Contabo VPS as application-host choice; account registration requires first order per provider process, so deferred until explicit purchase approval | No account or VPS created; mandatory security/reliability acceptance catalogue required before VPS provisioning |
| Production PostgreSQL / PlanetScale | **2026-10-11:** Owner confirmed an existing PlanetScale account, automatically created organization `gerhard-hullq`, active 2FA, and securely stored recovery keys. Accepted ADR-0012 selects PlanetScale Managed PostgreSQL 18, with PS-5 closed/internal and PS-10 ARM HA before buyer exposure as provisional configurations. Neon Free remains dev/test only | Account-security and organization-name owner attestation recorded; organization administration/billing ownership, sizing/pricing, EU region, HA/PITR and restore NOT PROVEN; no paid provisioning authorized |

**Phase-1 evaluation:** `IN_PROGRESS`. The accounts already accessible have owner-attested MFA/recovery evidence, but Contabo enrollment is purchase-gated, production DB provider is accepted via ADR-0012 but provisioning remains blocked by price/HA/provider proof, and some billing/ownership evidence is still outstanding. These explicit deferrals are not equivalent to phase PASS. `PRODUCTION_LAUNCH_PACK_PHASE` remains `NOT_STARTED`.

## Current Phase-1 execution order

To minimize recurring spend and avoid provisioning resources before their ownership/recovery boundary is ready:

```text
1. GitHub / GHCR evidence
2. hullq.com registrar ownership
3. Cloudflare account / zone / R2 ownership
4. Backblaze B2 EU Central account
5. Auth0 EU tenant/account
6. PlanetScale Managed PostgreSQL 18 — ADR-0012 Owner-accepted; account + organization `gerhard-hullq` + MFA + recovery Owner-attested (2026-10-11)
   → verify organization administration/billing ownership and before any purchase verify region, package, HA, backups/PITR, R2 restore, security and all-in spend
7. Contabo account
   → account created during first purchase, so defer until VPS order expressly approved and security acceptance catalogue prepared
8. Discord Free operator-alert destination: Owner-selected, MFA/recovery complete, private operations server and channel established
   → webhook secret and delivery proof deferred to Phase 2
```

Historical DigitalOcean provider-plan watch, verified 2026-10-09 (relevant only to legacy architecture reconciliation): DigitalOcean announces that beginning 2026-10-15 for accounts that have never created PostgreSQL/MySQL and beginning 2026-11-30 generally, new Standard Edition clusters no longer support standby/read-only nodes; existing clusters are not affected. This creates a time-sensitive conflict risk with HullQ's accepted low-cost Standard→later-standby HA path. The legacy DigitalOcean account path is no longer in the active Phase-1 sequence; no database cluster may be provisioned without explicit Owner approval.

Official references:
- https://docs.digitalocean.com/products/databases/
- https://docs.digitalocean.com/products/databases/postgresql/details/pricing/

## PlanetScale production provider — Owner-accepted ADR-0012 (2026-10-10)

Accepted decision: `architecture/decisions/ADR-0012-planetscale-managed-postgresql.md` (Owner accepted 2026-10-10, independent review PASS); provider-specific clauses are reconciled through this reviewed maintenance PR. No production provisioning or spend is authorized.

**Status: DECIDED_NOT_YET_IMPLEMENTED.** PlanetScale Managed PostgreSQL 18 is the accepted provider target, with tentative PS-5 Single Node for closed/internal production and PS-10 ARM three-node HA before real external buyer exposure. These are **unverified sizing hypotheses, not selected purchased packages or accepted pricing**. The Owner has not authorized an account/cluster purchase.

The controlling provider-specific references in `architecture/SYSTEM_ARCHITECTURE.md`, `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` and `docs/PROJECT_STATE.md` are updated together through the reviewed ADR-0012 reconciliation PR. The historical DigitalOcean plan/HA conflict explains the decision but is not itself technical acceptance evidence.

The candidate backup design discussed by the Owner is two independent layers: provider-managed backups and PITR (actual features/retention must be verified), plus HullQ-controlled encrypted PostgreSQL exports to independent Cloudflare R2 storage, with integrity and isolated restore drills. The accepted independent backup/restore requirements and existing HA-before-external-buyer-exposure gate continue unchanged regardless of provider.

Before any paid provisioning: confirm provider compatibility and all applicable phase-gate evidence; verify PostgreSQL 18, EU region, data protection, network security, expected application compatibility, actual compute/storage/backup/transfer costs, HA topology/failover and restore evidence. **Neon Free remains development/testing only.**

## Phase 1 Done-when

Phase 1 may move from `NOT_STARTED` to `1` only when all services required for the next production boundary have:

- a deliberate owner/account identity;
- MFA enabled where supported;
- a documented recovery method;
- billing/plan/region choice where applicable;
- timing classification (required now / before pilot / before public launch / later);
- no secret values stored in repository documentation.

Services explicitly marked `LATER_TRIGGER` do not block Phase 1 for a strictly closed/internal production boundary, but their trigger remains binding.

## Next operator sequence after Phase 1

Only after Phase 1 is complete:

```text
Phase 2 — Secrets & Connections
→ Phase 3 — Closed Production Infrastructure
→ Phase 4 — Closed HullQ Production Deploy
→ Phase 5 — Internal Real Operation
→ explicit bounded-pilot reassessment
```

No step above authorizes external production data, buyer exposure or public launch by itself.
