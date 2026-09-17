# HullQ — Post-SLICE-0054 Buyer/Seller Product Reconciliation

**Date:** 2026-09-17  
**Status:** OWNER-ACCEPTED PRODUCT DIRECTION; open questions remain before any SLICE-0055 capability selection  
**Scope:** Buyer journey, Decision Tools, Discovery/Search feature paper, and Seller Workspace topology after SLICE-0054.  

## 1. Purpose

This document records the product direction accepted after SLICE-0054. It does **not** select or authorize a SLICE-0055 capability. The next capability remains intentionally unselected until the remaining open questions and repository gap analysis are completed.

Source working papers reconciled here:

- `HullQ — Dreifach-validierte Feature-Ideen (Käufer × Broker × HullQ) — v2` (2026-09-17)
- `HullQ — Buyer Decision Tools — v1` (2026-09-17)
- accepted Broker Workspace direction/requirements
- accepted owner-direct marketplace direction and SLICE-0054 Owner-Direct Listing Draft Workspace
- accepted Search & SEO architecture

## 2. Direct Search remains the primary buyer entry point

HullQ MUST preserve the originally planned interactive technical Search as a first-class, low-friction primary entry point.

A buyer who already knows what they want MUST be able to search directly without completing onboarding, a questionnaire, a guided flow, or a persisted requirements profile.

The new guided buyer journey is **optional**. It supplements Search; it does not replace it.

Conceptually:

```text
                         HULLQ BUYER

                    +------ START ------+
                    |                   |
              DIRECT SEARCH       OPTIONAL GUIDED PATH
                    |                   |
          filters / criteria      define requirements
                    |                   |
                    |            Buyer Requirements
                    |                   |
                    +---------+---------+
                              |
                    deterministic Search
                              |
                       Search Results
```

Direct Search and Buyer Requirements MUST converge on the same deterministic Search/evaluation semantics rather than creating separate search engines.

### Hard product invariant

> Buyer Requirements never silently constrain Direct Search.

Applying saved/persisted requirements to an interactive Search must be visible and buyer-controlled. A buyer may freely browse outside their saved requirements.

## 3. Optional Buyer Requirements foundation

The structured-requirements idea is no longer treated merely as a replacement filter UI or gamified configurator. Its strategically important output is a structured, potentially persistable representation of buyer-defined requirements/intent.

Potential downstream consumers include:

```text
Buyer Requirements
        |
        +--> deterministic Search evaluation
        +--> buyer Search explainability / near-miss reasons
        +--> Saved Search / monitoring
        +--> sensitivity analysis
        +--> factual per-boat requirement fit
        +--> shortlist comparison
        +--> qualified seller/broker contact context
```

This is a product-direction statement, not yet an accepted persistence schema or implementation contract.

## 4. Decision neutrality

HullQ supports buyer agency. HullQ supplies factual evidence and tools; the buyer makes the decision.

HullQ MUST NOT turn Decision Tools into an opaque recommendation system, winner selection, best-boat ranking, purchase recommendation, or hidden preference model.

The earlier working label `Pro/Contra` should therefore not become the canonical product semantics. The preferred conceptual projection is buyer-defined requirement evaluation, for example:

- `MATCHES` / meets the buyer-defined requirement;
- `DOES_NOT_MATCH` / does not meet the buyer-defined requirement;
- `UNKNOWN` / evidence is insufficient or unresolved.

The factual explanation should expose the buyer's own criterion, the relevant HullQ truth/evidence, and the resulting deterministic relationship. Example: the buyer defined maximum draft 1.50 m; confirmed draft is 1.55 m; therefore that requirement does not match. HullQ does not assert that 1.55 m draft is inherently good or bad.

## 5. One evaluation truth, multiple projections

Buyer Search explainability and Buyer Decision Tools should not independently reimplement the same rule.

Conceptually:

```text
Buyer-defined Requirement
          x
HullQ technical/listing truth
          |
          v
Requirement Evaluation + Evidence
          |
          +--> Search exclusion / near-miss explanation
          +--> per-boat factual fit view
          +--> shortlist comparison
          +--> sensitivity delta
```

Exact evaluation states, evidence payloads, persistence boundaries and API contracts remain open for later specification.

## 6. Shortlist is a distinct buyer concept

A Shortlist represents boats the buyer chose to continue considering. It is not equivalent to Search state and does not assert that every shortlisted boat satisfies every requirement.

HullQ MUST NOT silently remove or demote a buyer-selected shortlist item because a requirement fails. The buyer owns the decision.

Potential future Shortlist consumers:

- side-by-side factual comparison;
- requirement evaluation;
- private notes;
- explicit sharing;
- seller/broker contact;
- monitoring.

No Shortlist persistence or sharing contract is accepted by this document.

## 7. Sharing direction

Shareable buyer shortlists/decision views are a useful future capability for collaboration with a partner, family member, surveyor or other buyer-selected participant.

Sharing must be explicit and privacy-bounded. The conceptual boundary is:

```text
Private Shortlist
      |
      | explicit share
      v
Sanitized Share Projection
      |
      v
Shared Decision View
```

A later Share Boundary Contract must decide at least data projection, privacy, notes inclusion, revocation, expiry, non-indexability and unguessable access semantics. No exact token/security design is accepted here.

## 8. Sensitivity analysis

The `what if I relax one criterion?` idea should be treated as deterministic re-evaluation of buyer-defined requirements, not as a recommendation engine.

It may show the factual consequence of a buyer-controlled criterion change, such as how the eligible/near-miss set changes. HullQ does not tell the buyer which criterion they should relax.

## 9. Discovery/Search working-paper reconciliation

The current feature ideas map conceptually as follows:

| Working-paper idea | Product/architecture interpretation |
| --- | --- |
| Buyer `Why no match?` | buyer-facing Requirement Evaluation projection |
| Structured Requirements | optional Buyer Requirements foundation; not a replacement for Direct Search |
| Rare Match | Search-derived evidence; requires a truthful bounded denominator |
| Saved Search reactivation | monitoring/retention; must avoid manipulative urgency |
| Sister/comparable boats — buyer | BoatDesign/configuration comparability + organic buyer discovery |
| Sister/comparable boats — broker | private professional market-context/intelligence surface |
| Broker Search exclusion | already represented by REQ-BROKER-025; depends on sufficient Search volume and privacy-safe aggregation |

`Rare Match` must never imply worldwide/global rarity unless the denominator genuinely supports that claim. The relevant population must be explicit and defensible.

Technical comparability and market/price context are related but separate concerns and must not be collapsed into one unsupported similarity score.

## 10. Seller Platform topology

HullQ should not build two unrelated seller-dashboard architectures. The accepted direction is a shared Seller Platform foundation with scoped Owner-Direct and Professional surfaces.

```text
                     HULLQ SELLER PLATFORM
                            |
             +--------------+--------------+
             |                             |
      Owner-Direct                    Professional
       Workspace                       Workspace
             |                             |
       My Boat(s)                     Inventory
       Draft/Edit                     Team / Org
       Evidence                       Bulk tools
       Verification                   Branding
       Enquiries                      Leads / CRM
       Listing status                 Intelligence
       Basic insights                 Portfolio analytics
       Sale outcome                   Sale outcomes
             |                             |
             +--------- shared ------------+
                    Account / Auth
                    Listing truth
                    Media/Documents
                    Verification
                    Enquiries
                    Search integration
                    Notifications
```

SLICE-0054 `/sell/direct` is the first accepted seed of the Owner-Direct Workspace. It should evolve as part of this Seller Platform direction rather than becoming a disconnected second dashboard implementation.

### Candidate shared Seller infrastructure

- Account/authentication primitives where applicable;
- listing editing/lifecycle infrastructure after explicit admission/publication contracts exist;
- field-level truth and evidence;
- media/documents;
- verification primitives/results;
- enquiries;
- Search integration/explainability;
- notifications;
- sale outcome primitives where semantics genuinely overlap.

### Professional-only concerns

- Organization/Membership/team roles;
- portfolio inventory;
- bulk onboarding/import/export;
- broker branding;
- professional CRM/lead management;
- aggregate demand/Search intelligence;
- portfolio reporting.

### Owner-Direct-specific concerns

- personal listing ownership;
- right-to-list attestation;
- personal identity verification where required;
- Sale Authority Verification;
- optional broker referral.

The exact shared-service boundaries remain to be validated against the repository before new implementation.

## 11. Telemetry and seller intelligence

Buyer Search and Decision surfaces may later share privacy/aggregation infrastructure, but their events and semantics must remain distinguishable.

For example, a Search exclusion because a field is `UNKNOWN` is not the same signal as a shortlisted boat having unresolved evidence during buyer comparison. Professional intelligence must not collapse these into one metric.

Any seller-facing aggregation requires explicit privacy, minimum-volume and abuse boundaries. Existing trigger gates, including REQ-BROKER-025 timing, remain authoritative.

## 12. Existing Search architecture remains authoritative

This direction preserves the accepted Search architecture:

- arbitrary interactive technical Search remains first-class;
- public organic discovery remains a separate intentionally governed surface;
- FastAPI remains the sole application/domain API boundary;
- the same truth/Search semantics must back product and eligible public discovery projections;
- organic Search eligibility, match classification and ordering remain commercially independent.

The optional guided buyer journey does not authorize a second Search implementation or a second truth engine.

## 13. Explicit non-decisions / open questions

This reconciliation intentionally does **not** yet decide:

1. whether `BuyerRequirements` is the final domain name or identity model;
2. whether anonymous requirements exist, authenticated persistence is required, or both;
3. exact requirement schema, operators, versioning and lifecycle;
4. exact evaluation result/state model beyond the product-level neutral semantics above;
5. whether and how an interactive Direct Search can be converted into saved Buyer Requirements;
6. Shortlist identity, persistence, maximum scope and anonymous/authenticated behavior;
7. Share Boundary Contract details;
8. sensitivity-analysis UX and computational contract;
9. Rare Match denominator/threshold semantics;
10. technical comparable-vessel rules and separate market-comparison semantics;
11. Saved Search persistence/alert/reactivation semantics;
12. telemetry event model, privacy thresholds and aggregation retention;
13. exact shared Seller infrastructure versus channel-specific modules;
14. Owner-Direct publication/admission, evidence, verification, enquiries, media and sale-outcome contracts;
15. which of these gaps should become SLICE-0055.

## 14. Required repository reconciliation before SLICE-0055 selection

Before selecting SLICE-0055, inspect actual accepted code/specs/docs for:

1. existing Search criterion/query representation and whether it can be reused by optional Buyer Requirements;
2. existing Search evaluation/explainability primitives;
3. existing Saved Search/monitoring concepts;
4. any existing buyer persistence/shortlist concepts;
5. accepted Broker requirements that already cover working-paper ideas;
6. current Seller components that can genuinely be shared versus professional-only or owner-direct-only;
7. dependencies and trigger gates that make some ideas premature;
8. the smallest high-leverage capability that advances the buyer/seller product architecture without reopening accepted decisions.

Only after that reconciliation may one capability be proposed for SLICE-0055 readiness.

## 15. Working product model

The accepted working model is therefore:

```text
BUYER

Direct Search ---------------------------+
                                        |
Optional Buyer Requirements ------------+--> deterministic Search
                                                |
                                         explain / discover
                                                |
                                            Shortlist
                                                |
                                   optional Decision Tools
                                    compare / sensitivity
                                      share / monitor
                                                |
                                      buyer chooses action
                                                |
                                      seller/broker contact

SELLER

Shared Seller Platform
        |
        +--> Owner-Direct Workspace
        +--> Professional Workspace

FOUNDATION

BoatDesign / Configuration truth
PhysicalBoat / Listing truth
Field-level truth + evidence
Deterministic Search / evaluation semantics
```

The implementation principle is: **preserve low-friction Direct Search, make the guided journey optional, reuse one deterministic truth/evaluation engine, and keep the buyer in control of the decision.**
