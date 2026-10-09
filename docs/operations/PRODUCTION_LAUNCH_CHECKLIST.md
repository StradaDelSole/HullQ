# HullQ Production Launch Checklist

**Status:** ACTIVE — Phase 1 not complete  
**Controlling procedure:** `docs/operations/PRODUCTION_LAUNCH_PACK.md`  
**Canonical launch phase:** `NOT_STARTED`  
**Started:** 2026-10-09  
**Secret rule:** this file stores secret names/status only. Never place passwords, tokens, API keys, private keys, recovery codes or secret values here.

## Current execution boundary

The next operator goal is:

```text
Phase 1 — Accounts & Ownership
```

No production launch phase advances until the complete Phase-1 Done-when conditions are evidenced and a reviewed repository maintenance/closure change updates `PRODUCTION_LAUNCH_PACK_PHASE`.

SLICE-0080 is a separate repository implementation capability for provider-independent broker-original media redundancy. It does not itself advance this launch phase.

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
| GitHub / GHCR | canonical source, Actions, immutable container registry | now | repository/package namespace proven under `StradaDelSole` | not yet retained in launch evidence | current GitHub plan/package billing not yet retained | IN_PROGRESS |
| HullQ domain registrar / `hullq.com` ownership | authoritative domain control before DNS/edge | before production DNS work | registrar/account owner not yet retained | not yet retained | registrar/renewal state not yet retained | OWNER_INPUT_REQUIRED |
| Cloudflare | DNS/proxy/edge; primary marketplace-media R2; independent encrypted DB-backup R2 | before closed production infrastructure; edge before external exposure | account/zone/R2 ownership not yet retained | not yet retained | EU/data-location/billing configuration not yet retained | OWNER_INPUT_REQUIRED |
| Contabo | selected initial replaceable Linux application VPS | before closed production infrastructure | account ownership not yet retained | not yet retained | VPS plan/region not yet provisioned | OWNER_INPUT_REQUIRED |
| DigitalOcean | Managed PostgreSQL 18 FRA1 Standard | before closed production infrastructure | account/team ownership not yet retained | not yet retained | DB plan/region FRA1 accepted; actual subscription not yet provisioned | OWNER_INPUT_REQUIRED |
| Auth0 Public Cloud | EU tenant, authentication-only | before real interactive broker authentication | account/tenant ownership not yet retained | tenant/admin recovery not yet retained | EU tenant accepted; actual production tenant state not yet retained | OWNER_INPUT_REQUIRED |
| Operator alert destination | actionable production alert webhook; current implementation accepts Slack or Discord webhook | before Production Readiness PASS when operator relies on alert delivery | provider/account/channel not yet selected/retained | provider-dependent | provider choice open | OWNER_DECISION_REQUIRED |
| Backblaze B2 EU Central | independent second copy of broker original/source media, separate from primary Cloudflare R2 | before real broker production media; implementation selected for SLICE-0080 | provider owner-decided; real account not yet provisioned | MFA/recovery evidence required in Phase 1 | EU Central / Amsterdam accepted; usage-based billing; real account/billing not yet retained | OWNER_ACCOUNT_SETUP_REQUIRED |
| Zammad Hosted Professional v2 | customer Help/Support system | before external support launch | accepted product choice; account not yet provisioned | later | later | LATER_TRIGGER |
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

SLICE-0080 readiness is READY; the real account/bucket/application key remains Phase-1/Phase-2 operator work and is not created by the slice.

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
