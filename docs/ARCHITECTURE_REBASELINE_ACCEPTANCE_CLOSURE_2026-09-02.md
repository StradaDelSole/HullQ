# HullQ Architecture Rebaseline — Acceptance Closure

**Date:** 2026-09-02  
**Status:** ACCEPTED / MERGED  
**Applies to:** PR #122 and the post-SLICE-0039 architecture/governance rebaseline

## Accepted exact head

The Project Owner explicitly accepted PR #122 on exact reviewed HEAD:

```text
cb67f47f171b44b6a52c737c4e04ded6babc2b05
```

The final exact-head review found one governance-enforcement defect before acceptance: `docs/slices/SLICE_TEMPLATE.md` still pointed future slices only at older execution-plan artifacts. That defect was amended before the accepted HEAD so post-SLICE-0039 slices are now required to apply the controlling precedence defined by the 2026-09-02 reconciliation, architecture rebaseline and private-seller policy.

No further material review findings remained on the accepted HEAD.

## Merge

PR #122 was merged with expected-head protection against the accepted HEAD above.

Canonical merge commit:

```text
fe96bd537819c6f0e61d7c420828a6eeb3496658
```

## Controlling result

The merged rebaseline establishes, among other things:

- native HullQ professional inventory as the strategic marketplace foundation;
- Phase-1 public supply restricted to broker/dealer/eligible-professional Organizations;
- private owners handled through a separate `BrokerageRequest` / referral path, with no public FSBO fallback;
- strict separation of `BoatDesign`, `PhysicalBoat`, `MarketEpisode`, `NativeListing` and `ExternalMarketObservation`;
- evidence-based MarketEpisode continuity;
- lifecycle/freshness separation, including `STALE != SOLD` and `DISAPPEARED != SOLD`;
- Buyer Launch Inventory Readiness Gate before external Gate 1;
- old Free/Plus/Pro packaging superseded and marketplace pricing reopened;
- Astro + React frontend with FastAPI as the sole application/domain API boundary;
- PostgreSQL 18 with DigitalOcean Managed PostgreSQL FRA1 as the production target;
- mandatory PostgreSQL HA before real external broker production inventory is exposed to real external buyers;
- provider backup/PITR plus independent encrypted logical backups and restore testing;
- Auth0 EU as authentication-only, with HullQ-owned Accounts, Organizations, Memberships, verification and authorization;
- mandatory MFA for privileged broker accounts, with Passkeys/WebAuthn preferred and future step-up for high-risk actions;
- R2 media quarantine/validation/re-encoding/metadata stripping plus an independent second-provider copy of original broker media before real broker production;
- immutable CI-built containers, GHCR and Docker Compose on stateless/replaceable application hosts, without Coolify/Dokploy as the initial production control plane;
- concise GDPR/security incident-response governance before real broker/buyer personal data is handled in production;
- continued ONE-CAPABILITY, VISIBLE-RESULT, strict-truth, provenance, fail-closed, source-rights and exact-head governance.

## Scope boundaries retained

This closure does **not**:

- create SLICE-0040;
- implement marketplace domain objects;
- integrate Auth0;
- provision DigitalOcean production infrastructure;
- implement Freshness, dedup, media, leads or referral automation;
- reinstate any superseded Free/Plus/Pro packaging;
- authorize public private-seller listings;
- authorize transaction/escrow/closing scope.

## Next authorized planning action

After this closure is merged, the next planning step is to define a narrowly bounded SLICE-0040 around the Marketplace Identity / Truth Boundary.

The exact executable acceptance criterion must still be cut under the ONE-CAPABILITY rule before SLICE-0040 may become READY.

No later implementation capability is started by this closure.
