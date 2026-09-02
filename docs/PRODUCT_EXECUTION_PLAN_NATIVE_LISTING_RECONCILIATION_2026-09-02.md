# HullQ Product Execution Reconciliation — Native Listing Market

**Date:** 2026-09-02  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** all work after the terminal closure of SLICE-0039  

## Purpose

This document removes residual ambiguity between older execution planning and the final 2026-09-02 native-marketplace / trust-first architecture rebaseline.

The owner has decided that HullQ will build a **native, broker-first sailboat listing/discovery market**. Native HullQ professional listing supply is the strategic market foundation for the pre-Gate-1 product. Authorized external marketplace/API/feed integrations are optional coverage supplements and are not prerequisites for HullQ's core viability or Gate-1 execution.

This reconciliation must be read together with:

- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `docs/PRIVATE_SELLER_POLICY_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
- `docs/PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`.

Where older documents conflict with the final architecture/private-seller decisions, the newer explicit rule controls.

## Controlling precedence

For conflicting post-SLICE-0039 execution instructions, use the following precedence:

1. `ARCHITECTURE_REBASELINE_2026-09-02.md`;
2. `PRIVATE_SELLER_POLICY_2026-09-02.md` for private-owner/public-supply policy;
3. this reconciliation;
4. `PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
5. `PRODUCT_EXECUTION_PLAN_AMENDMENT_2026-09-01.md`;
6. `PRODUCT_EXECUTION_PLAN.md` and older non-normative planning language.

Non-conflicting strict-truth, provenance, fail-closed, configuration-scope, physical-listing-scope, explicit `UNKNOWN`, source/media-rights, ONE-CAPABILITY, VISIBLE-RESULT, exact-head review/gates and slice-isolation rules remain fully in force.

---

## 1. Market foundation

Any earlier wording equivalent to:

```text
current market inventory through lawful/authorized access paths
```

must be read as:

```text
native HullQ professional listings as the strategic market foundation
+
optional authorized external inventory integrations where useful
```

External marketplace permission is not a Gate-1 prerequisite.

HullQ must not depend on unauthorized scraping or a single external marketplace for core viability.

---

## 2. Public supply is professional-only in Phase 1

Any earlier wording that treats `broker/seller supply` or private and professional publishers as equivalent is superseded.

Phase-1 public NativeListing supply is:

```text
BROKER / DEALER / ELIGIBLE PROFESSIONAL ORGANIZATION ONLY
```

Private consumers may not publish public `NativeListing` records.

Private-owner sale intent is handled through a separate `BrokerageRequest` / referral domain and is not a hidden NativeListing.

The full policy is defined by `PRIVATE_SELLER_POLICY_2026-09-02.md`.

No public FSBO listing fee is part of Phase 1.

---

## 3. External recurring acquisition

Sections of the 2026-09-01 pre-Gate-1 amendment that describe identifying, authorizing, implementing and scheduling a recurring **external** market-acquisition path remain valid only when HullQ later chooses to integrate such an external source.

They are no longer a required dependency for Gate 1.

The required pre-Gate-1 operational loop is instead based on native professional supply and native listing events:

```text
native professional listing creation/import/update
→ canonical BoatDesign/configuration identity assessment
→ physical-listing truth
→ persistence/change state
→ Saved Search evaluation
→ monitoring/scheduler where needed
→ real alert
```

---

## 4. Supply acquisition

Before Gate 1, HullQ must prove realistic native professional supply rather than prove access to a third-party marketplace.

Supply capabilities should be built progressively through bounded slices, starting with the smallest real path and expanding only as justified:

```text
manual listing
→ bulk import
→ XML/JSON/API feed
→ broker inventory feed
→ CRM/DMS/syndication integration
```

This is not permission to build all supply mechanisms at once.

Broker supply should support branding, multihoming, portability and transparent lead attribution. HullQ must not require marketplace exclusivity as a condition of ordinary participation.

---

## 5. Marketplace truth model

The post-0039 marketplace implementation must preserve the domain separation defined in the Architecture Rebaseline:

```text
BoatDesign
≠ PhysicalBoat / MarketVessel
≠ MarketEpisode
≠ NativeListing
≠ ExternalMarketObservation
```

A physical boat is not a listing.

One physical boat may have multiple listing appearances and multiple market episodes.

MarketEpisode continuity is evidence-based and may resolve as `SAME`, `NEW` or `UNRESOLVED`; no universal time-gap threshold alone establishes truth.

Dedup/physical-vessel identity must prefer unresolved duplication over a false merge when evidence is insufficient.

Known future dedup tests include renamed/re-registered yachts and near-identical sister ships.

---

## 6. Listing lifecycle and freshness

Lifecycle and freshness are separate state dimensions.

Hard truth rules:

```text
STALE ≠ SOLD
DISAPPEARED ≠ SOLD
ACTIVE does not automatically mean CURRENTLY CONFIRMED
```

For manual native broker listings, the initial policy direction is a configurable confirmation TTL around 30 days plus a grace period around 7 days.

Feed-driven freshness will later respect successful feed presence, source health and source semantics.

The policy is defined before implementation, but the Freshness capability remains a separate bounded slice and must not be pulled into SLICE-0040 merely because it is related to listing truth.

---

## 7. Buyer Launch Inventory Readiness Gate

External Buyer Validation may not begin while search results are materially determined by missing HullQ inventory rather than the real target market.

Do not invent a round-number threshold before real broker supply creates a defensible denominator.

Before external Gate 1, define the target pilot market and lock a quantitative readiness threshold using real supply data, considering at least:

- independent broker Organizations;
- active confirmed listings;
- geographic/vessel-category diversity;
- BoatDesign mapping rate;
- freshness rate;
- representative buyer-case coverage;
- meaningful market-reference coverage where available.

This readiness gate does not block SLICE-0040.

---

## 8. Pricing / monetization is reopened

Any older wording requiring a fixed `Pro/subscription proposition` or implying that the previous Free/Plus/Pro packaging remains controlling is superseded.

The marketplace pivot materially changes the commercial model.

Gate 1 may test credible willingness-to-pay hypotheses, but no previous price or Free/Plus/Pro package is controlling.

Separate:

- **Product Pull** — does the user want the capability/value loop?
- **Pay Pull** — will the user pay a tested amount/package?

Commercial packaging must be rebuilt around the actual marketplace actors:

```text
Buyer
Broker / Dealer / Professional Supply
Private Owner as Referral Source (not public seller)
Professional/Data Customer (possible later)
```

Architecture should use generic capabilities/entitlements rather than hard-coded plan-name branches.

Early professional inventory may rationally be free/very low-friction because supply itself creates marketplace value.

Buyer Search must not be intentionally degraded to manufacture payment pressure.

---

## 9. Trust-first leads

Lead/contact handling is part of the marketplace trust boundary.

A future `Lead` / `ContactRequest` capability should support persistent attribution, delivery/response state, safety/moderation state and auditability.

Avoid building a full messenger initially.

Preferred staged contact direction:

```text
verified buyer
→ ContactRequest
→ broker sees verified identity indicators + message
→ broker accepts contact
→ appropriate direct contact data released
→ direct communication may continue outside HullQ
```

This staged disclosure is for privacy and scam reduction, not platform lock-in.

Referral ordering and organic buyer-search ranking remain separate systems.

---

## 10. Architecture / stack decisions

The following 2026-09-02 owner decisions are controlling target architecture:

### Frontend / backend

```text
Astro
+ React for interactive surfaces
+ FastAPI / Python modular monolith
```

FastAPI is the sole application/domain API boundary. Domain rules must not be duplicated into a second frontend application backend.

### Database

```text
Development: local PostgreSQL 18
Production target: DigitalOcean Managed PostgreSQL 18, FRA1, Standard Edition
```

Approved baseline extensions where needed: `postgis`, `pg_trgm`, `pgcrypto`.

`pgaudit` is optional/deferred, not mandatory Pre-Gate-1.

### Authentication

```text
Auth0 Public Cloud, EU tenant
```

Auth0 is authentication-only. HullQ owns immutable Account IDs, Organizations, Memberships, roles, listing ownership, verification and authorization in PostgreSQL.

Privileged publishing-capable broker accounts and Organization Owner/Admin accounts require MFA, preferably Passkeys/WebAuthn. High-risk actions require step-up/fresh authentication when those actions exist.

### Deployment

Initial deployment uses:

```text
GitHub Actions
→ immutable versioned container images
→ GHCR
→ controlled deployment
→ Docker Compose on replaceable app host
```

No Coolify/Dokploy initial production control plane.

No broad self-hosted CI runner on production hosts.

No `latest` as production truth.

---

## 11. Security, backups and redundancy

Data security and redundancy/recoverability are top-level architecture requirements.

### Database

Provider PITR/backups must be supplemented by independent encrypted logical backups to Cloudflare R2 EU and regular restore tests.

Working retention direction:

```text
7 daily + 4 weekly
```

Before real external broker production inventory is exposed to real external buyers, PostgreSQL HA with at least one standby must be active.

### Media

Broker media follows:

```text
upload
→ private quarantine
→ validate
→ decode/re-encode
→ strip EXIF/GPS
→ generate derivatives
→ publish
```

Before real broker production, original/source media requires an independent second copy at a different storage provider. Reproducible derivatives need not be duplicated if they can be regenerated from preserved originals.

### App hosts

Critical durable production state must not exist only on the application VPS.

App hosts should be stateless/replaceable enough to rebuild from code/config/images.

A later second app host at an independent provider is the preferred compute-redundancy path when marketplace availability warrants it.

---

## 12. DSGVO / incident response

Before real external broker/buyer personal data is handled in production, HullQ must have a concise documented incident-response runbook covering detection, containment, evidence preservation, affected-data/risk assessment, notification decisions, required authority/data-subject notifications, remediation and postmortem.

This is required operational governance and should remain proportionate to the early-stage system.

---

## 13. Referral completion and anti-gaming

The private-owner referral design must include an explicit terminal `EXHAUSTED` state if no eligible/interested broker remains.

The owner must receive an honest status and options such as retry/update/close rather than silent failure.

A broker clicking `INTERESTED` must not automatically create a positive performance signal. Future bounded logic may verify actual contact/outcome through the owner.

These rules belong to the referral policy/domain but do not require the complete automated referral workflow before Gate 1 unless separately justified.

---

## 14. Post-0039 sequencing

The earlier sequence is reconciled as follows.

Approximate capability order:

1. lock/formalize the complete HullQ Search Product Contract;
2. implement remaining Search-contract semantics/filters in bounded slices;
3. scale Search-contract data coverage;
4. expose the full Search contract through a simple Validation UI;
5. reconcile/freeze the final architecture and marketplace governance — this PR;
6. define the first native marketplace capability (`SLICE-0040`) narrowly around the marketplace identity/truth boundary;
7. add professional publishing eligibility in its own bounded capability if combining it with #6 would violate ONE-CAPABILITY;
8. create/persist one native professional listing end-to-end;
9. attach physical-vessel/configuration identity without collapsing truth scopes;
10. add listing read/search surfaces;
11. add listing lifecycle/status handling;
12. add freshness/reconfirmation handling as its own bounded capability;
13. add broker Organization/authorization capabilities as dependencies require;
14. add media handling only after quarantine/storage/redundancy rules are implemented;
15. add scalable bulk/feed intake;
16. add/expand physical-vessel dedup/identity handling as multiple intake paths require it;
17. persist exact Saved Searches;
18. connect native listing events to Saved-Search evaluation;
19. send real alerts;
20. establish a credible pricing/WTP test surface without assuming old Free/Plus/Pro packaging;
21. run internal burn-in;
22. establish and satisfy the Buyer Launch Inventory Readiness Gate;
23. run external Gate-1 validation.

Private-owner referral automation is a separate capability track and must not be pulled into this buyer-marketplace sequence unless a concrete dependency justifies it.

Dependencies may justify bounded reordering, but later capabilities may not be pulled into an earlier slice merely for convenience.

---

## 15. SLICE-0040 boundary

No SLICE-0040 exists yet.

Current preferred direction:

> **Marketplace Identity / Truth Boundary**

Its purpose is to prove that:

```text
BoatDesign
≠ PhysicalBoat
≠ MarketEpisode
≠ NativeListing
≠ ExternalMarketObservation
```

The exact executable acceptance criterion must still be narrowed before the slice is created.

Do not add Freshness implementation, dedup implementation, Auth0 integration, media, leads, referral automation or broker UI merely because they are related to marketplace architecture.

The ONE-CAPABILITY rule remains controlling.

---

## 16. SLICE-0039 terminal outcome

SLICE-0039 remains terminally accepted as `BLOCKED` because its locked evaluability gate was not met under strict truth.

That historical gate is not reopened, relaxed or repaired.

No further work is authorized under SLICE-0039.

---

## Controlling one-sentence direction

> **HullQ will build a native, broker-only-public-supply sailboat listing/discovery market whose core advantage is deterministic configuration-aware technical Search, strict physical-vessel/listing truth, monitoring and trust-first leads; native professional inventory is the strategic supply foundation, private owners use a separate transparent broker-referral path, external sources are optional rights-cleared supplements, and implementation follows the trust-first Astro/React + FastAPI + PostgreSQL architecture frozen on 2026-09-02.**
