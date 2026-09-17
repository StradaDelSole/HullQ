# HullQ — Post-SLICE-0054 Buyer/Seller Product Reconciliation

**Date:** 2026-09-17  
**Status:** OWNER-ACCEPTED PRODUCT DIRECTION; repository reconciliation and open questions remain before any SLICE-0055 capability selection  
**Scope:** Buyer journey, Decision Tools, Discovery/Search feature paper, and Seller Workspace topology after SLICE-0054.

## 1. Purpose

This document records the product direction accepted after SLICE-0054. It does **not** select or authorize a SLICE-0055 capability. The next capability remains intentionally unselected until repository reconciliation and the remaining open questions are completed.

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

Direct Search and Buyer Requirements MUST converge on the same deterministic Search/evaluation semantics rather than creating separate search engines.

### Hard product invariant

> Buyer Requirements never silently constrain Direct Search.

Applying saved/persisted requirements to an interactive Search must be visible and buyer-controlled. A buyer may freely browse outside their saved requirements.

## 3. Buyer Requirements foundation

Structured Buyer Requirements are not merely a replacement filter UI. They are a buyer-defined requirement/intent representation that may feed Search evaluation, explainability, monitoring, sensitivity analysis, factual decision tools, shortlist comparison and qualified seller/broker contact context.

### 3.1 Discovery remains open; signup unlocks continuity

Accepted principle:

> **Signup unlocks continuity, not discovery.**

Anonymous users may experience the differentiating buyer tools before account creation. The intended initial boundary is:

**Open / anonymous-capable:**
- Direct Search;
- optional guided definition of requirements;
- requirement evaluation and Search explainability;
- basic sensitivity analysis;
- temporary/local shortlist where practical.

**Free-account continuity:**
- persisted Buyer Requirements;
- Saved Searches within the future account limits;
- persistent Shortlist;
- monitoring/alerts where implemented;
- cross-device continuity;
- later privacy-bounded sharing/history capabilities.

The exact Free/Pro boundary is not fixed here.

`BuyerRequirements` MUST NOT conceptually require an `AccountId`. Anonymous requirement state may exist before account creation and may later be persisted/account-owned after explicit signup/save. Initial implementation should prefer browser/session-local anonymous state rather than prematurely creating durable anonymous BuyerIntent records with orphaning, privacy, cleanup and abuse costs.

Where feasible, signup should preserve the buyer's explicitly created anonymous work rather than discarding it.

### 3.2 Requirement importance semantics

The guided Requirements path uses three buyer-selected importance states:

- `MUST_HAVE` — required;
- `PREFER` — desired but not exclusionary;
- `DONT_CARE` — irrelevant to this Requirements evaluation.

Direct Search remains a conventional low-friction filtering surface and does not require this three-level semantics for every filter.

For the initial model, all `PREFER` requirements are equal. There are no preference weights, high/medium/low levels, semantic ordering, or HullQ-generated importance weights. A later buyer-controlled prioritization may only be considered if real usage demonstrates a need.

### 3.3 Requirement evaluation states

The canonical product-level evaluation semantics are:

- `SATISFIED` — sufficient applicable evidence confirms the buyer-defined requirement;
- `NOT_SATISFIED` — sufficient applicable evidence confirms the requirement is not met;
- `UNKNOWN` — available evidence is insufficient or unresolved.

Hard invariant:

> **UNKNOWN is not NOT_SATISFIED, and UNKNOWN is not SATISFIED.**

Missing evidence must never be silently converted into a negative claim about the boat. Whether an `UNKNOWN` result remains visible in a particular Search-results projection is a buyer-visible Search policy/control concern, not a mutation of the underlying evaluation truth.

### 3.4 No scores, winners or hidden preference model

HullQ MUST NOT derive an overall fit percentage, recommendation score, winner, `best fit`, or implicit preference weighting from requirement evaluations.

For `PREFER`, HullQ may expose each factual state and may provide descriptive counts such as `3 satisfied · 1 not satisfied · 1 unknown`. Those counts are not a score and MUST NOT be converted into an overall evaluative ranking.

HullQ does not infer hidden requirements or preferences from repeated Search behavior.

## 4. Direct Search ↔ Buyer Requirements conversion

Conversion between Direct Search and Buyer Requirements is explicit and buyer-controlled.

A buyer may explicitly choose to use a Direct Search as the basis for Requirements. Compatible Direct Search hard filters may become `MUST_HAVE` requirements only as part of that visible buyer action.

In the reverse direction, `MUST_HAVE` requirements may supply hard Search constraints when the buyer explicitly chooses to Search with those requirements. `PREFER` requirements MUST NOT silently become hard Direct Search filters; they remain evaluation/explainability context unless the buyer explicitly changes their semantic meaning.

Hard invariant:

> **Conversion between Direct Search and Buyer Requirements must never silently change the meaning of a criterion.**

## 5. Decision neutrality and one evaluation truth

HullQ supports buyer agency. HullQ supplies factual evidence and tools; the buyer makes the decision.

HullQ MUST NOT turn Decision Tools into an opaque recommendation system, winner selection, best-boat ranking, purchase recommendation, or hidden preference model.

Buyer Search explainability and Buyer Decision Tools should reuse the same requirement-evaluation truth rather than independently implementing equivalent rules.

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

The factual explanation exposes the buyer's own criterion, relevant HullQ truth/evidence and resulting deterministic relationship. HullQ does not assert that a characteristic is inherently good or bad merely because it differs between boats.

## 6. Requirement Sensitivity Analysis

`Why no match?` is treated as a particularly useful projection of a broader Requirement Sensitivity Analysis, not as an isolated engine.

HullQ may show the factual consequence of a buyer-controlled requirement change, including when the current Search has zero results or still has results. It does not tell the buyer which criterion they should relax.

Initial accepted constraints:

- one requirement change at a time;
- buyer initiated;
- deterministic;
- reversible;
- no automatic optimization;
- no HullQ-generated multi-criterion relaxation strategy.

Example semantics: `If maximum draft were changed from 1.60 m to 1.70 m, three additional boats would satisfy all remaining MUST_HAVE requirements.` This is a factual delta, not advice to change the requirement.

Later comparison of multiple buyer-authored changes is not prohibited, but HullQ must not autonomously search for and recommend the combination of requirements the buyer should abandon.

## 7. Shortlist is buyer interest, not HullQ fit

A Shortlist represents boats the buyer explicitly chose to continue considering. It is distinct from Search state and from Buyer Requirements.

Hard invariant:

> **Shortlisting expresses buyer interest, not HullQ fit. Requirement evaluation must never add or remove shortlist membership automatically.**

A boat may remain shortlisted even when the currently selected Requirements produce `NOT_SATISFIED` or `UNKNOWN` states. Different Requirements may later be projected against the same Shortlist.

The initial direction is one ordinary personal Shortlist rather than prematurely introducing multiple named lists. Multiple lists may be added later if real usage supports them.

Potential future Shortlist consumers include factual comparison, requirement evaluation, private notes, explicit sharing, seller/broker contact and monitoring.

## 8. Compare

Compare is useful independently of the guided Requirements journey. A buyer may compare shortlisted boats side-by-side using factual technical, listing, market and truth/evidence data without defining Buyer Requirements.

When Requirements exist, they may add an optional evaluation layer showing `SATISFIED`, `NOT_SATISFIED` and `UNKNOWN` against each compared boat.

Compare MAY highlight factual differences. It MUST NOT, absent an explicit buyer-defined requirement, label one differing value as inherently better or worse.

Compare MUST NOT provide a winner, overall match score, `best fit`, hidden weighting or automatic fit-based ordering. Descriptive evaluation counts may be shown but remain non-evaluative summaries.

## 9. Sharing direction

Shareable buyer shortlists/decision views are a useful future capability for collaboration with a partner, family member, surveyor or other buyer-selected participant.

Sharing must be explicit and privacy-bounded. A later Share Boundary Contract must decide at least data projection, privacy, notes inclusion, revocation, expiry, non-indexability and unguessable access semantics. No exact token/security design is accepted here.

## 10. Discovery/Search working-paper reconciliation

| Working-paper idea | Product/architecture interpretation |
| --- | --- |
| Buyer `Why no match?` | buyer-facing Requirement Sensitivity / Evaluation projection |
| Structured Requirements | optional Buyer Requirements foundation; not a replacement for Direct Search |
| Rare Match | Search-derived evidence; requires a truthful bounded denominator |
| Saved Search reactivation | monitoring/retention; must avoid manipulative urgency |
| Sister/comparable boats — buyer | BoatDesign/configuration comparability + organic buyer discovery |
| Sister/comparable boats — broker | private professional market-context/intelligence surface |
| Broker Search exclusion | already represented by REQ-BROKER-025; depends on sufficient Search volume and privacy-safe aggregation |

`Rare Match` must never imply worldwide/global rarity unless the denominator genuinely supports that claim. The relevant population must be explicit and defensible.

Technical comparability and market/price context are related but separate concerns and must not be collapsed into one unsupported similarity score.

## 11. Seller Platform topology

HullQ should not build two unrelated seller-dashboard architectures. The accepted direction is a shared Seller Platform foundation with scoped Owner-Direct and Professional surfaces.

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

## 12. Telemetry and seller intelligence

Buyer Search and Decision surfaces may later share privacy/aggregation infrastructure, but their events and semantics must remain distinguishishable.

A Search exclusion because a field is `UNKNOWN` is not the same signal as a shortlisted boat having unresolved evidence during buyer comparison. Professional intelligence must not collapse these into one metric.

Any seller-facing aggregation requires explicit privacy, minimum-volume and abuse boundaries. Existing trigger gates, including REQ-BROKER-025 timing, remain authoritative.

## 13. Existing Search architecture remains authoritative

This direction preserves the accepted Search architecture:

- arbitrary interactive technical Search remains first-class;
- public organic discovery remains a separate intentionally governed surface;
- FastAPI remains the sole application/domain API boundary;
- the same truth/Search semantics must back product and eligible public discovery projections;
- organic Search eligibility, match classification and ordering remain commercially independent.

The optional guided buyer journey does not authorize a second Search implementation or a second truth engine.

## 14. Explicit remaining non-decisions / open questions

The following remain intentionally unresolved rather than forgotten:

1. final `BuyerRequirements` domain name, identity, schema, operators, versioning and lifecycle;
2. exact anonymous-state transport/lifetime and explicit migration into an authenticated account;
3. exact Search policy/control for visibility of `UNKNOWN` MUST_HAVE results;
4. Shortlist identity/persistence/account limits and anonymous local behavior;
5. Share Boundary Contract details;
6. Rare Match denominator/threshold semantics;
7. technical comparable-vessel rules and separate market-comparison semantics;
8. Saved Search persistence/alert/reactivation semantics and eventual Free/Pro limits;
9. telemetry event model, privacy thresholds and aggregation retention;
10. exact shared Seller infrastructure versus channel-specific modules;
11. Owner-Direct publication/admission, evidence, verification, enquiries, media and sale-outcome contracts;
12. which of these gaps, if any, should become SLICE-0055.

## 15. Required repository reconciliation before SLICE-0055 selection

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

## 16. Working product model

```text
BUYER

Direct Search ---------------------------+
                                        |
Optional Buyer Requirements ------------+--> deterministic Search/evaluation
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

The implementation principle is: **preserve low-friction Direct Search, expose HullQ's differentiating discovery/evaluation tools before signup, make persistence the account reward, reuse one deterministic truth/evaluation engine, and keep the buyer in control of the decision.**
