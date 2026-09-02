# HullQ Product Execution Plan Amendment — Pre-Gate-1 Full Product Proposition Validation

**Date:** 2026-09-01  
**Status:** ACCEPTED OWNER DIRECTION — proposed as controlling amendment when merged  
**Applies to:** work after SLICE-0039  
**Relationship to existing policy:** This amendment supersedes conflicting pre-Gate-1 sequencing, Seed-Corpus limits, Alpha timing and pre-Gate data restrictions in `docs/PRODUCT_EXECUTION_PLAN.md` and conflicting pre-Gate limitations in `docs/PRODUCT_UX_PRINCIPLES.md`. All non-conflicting strict-truth, provenance, fail-closed, ONE-CAPABILITY, VISIBLE-RESULT, review, slice-isolation and exact-head governance rules remain in force.  
**SLICE-0039:** unchanged. Finish and review SLICE-0039 exactly as already accepted; do not widen it to implement this amendment.

## 1. Decision

HullQ will not perform Gate 1 against a deliberately tiny Search demo or a 20–30-design corpus.

Gate 1 will evaluate a **slim but functionally complete version of HullQ's actual product proposition**:

```text
complete intended technical Search contract
→ configuration-aware deterministic truth
→ sufficiently broad real BoatDesign coverage
→ current market inventory through lawful/authorized access paths
→ listing identity / dedup / physical-listing truth
→ saved Search
→ automated recurring market acquisition
→ scheduled re-evaluation
→ real alerts
→ clear Pro/subscription proposition
```

The implementation may remain deliberately plain and operationally simple. The user-facing value loop may not be artificially reduced merely to minimize code before validation.

The controlling principle becomes:

> **Build nothing before Gate 1 that does not directly contribute to the real HullQ product, its ability to scale, its operational feasibility, or a meaningful validation of the product proposition. Build the core value loop fully enough that a realistic user can actually experience it.**

This is not permission for generic platform work, speculative infrastructure, visual polish, unrelated SEO, native apps, social features, broker admin systems, marketplace ownership or other non-essential expansion.

## 2. Product hypothesis being tested

Correctness, configuration truth, provenance and explicit `UNKNOWN` are mandatory product properties. They are not excuses to present a narrow product and call that the value proposition.

The buyer-side value hypothesis is broader:

> A serious sailboat buyer can express technical requirements that conventional boat-search products do not reliably support, receive deterministic and explainable candidate results, save that exact search, and let HullQ continuously monitor real market inventory for relevant boats instead of repeatedly checking portals manually.

Gate 1 therefore tests the experienced workflow, not only the Search kernel.

The user must be able to experience:

```text
I define my real requirements once
→ HullQ applies them exactly
→ HullQ shows what fits, what does not, and what is unknown
→ HullQ watches the market
→ HullQ tells me when something relevant appears or changes
```

## 3. Search completeness before Gate 1

Before external Gate-1 validation, HullQ must expose the **complete intended technical Search filter set defined by the accepted HullQ Search product contract**.

"Complete" means every filter class HullQ intentionally claims as part of its Search product is usable, combinable and evaluated through the same deterministic truth semantics. It does **not** mean every possible nautical fact in existence must become a filter.

The formal Search-product contract must therefore be locked before Saved-Search persistence is treated as stable, because the persisted query shape depends on it.

Expected categories include all accepted product-contract fields, for example where already authorized by requirements/specifications:

- principal dimensions;
- displacement / ballast and accepted derived ratios;
- hull configuration;
- keel / appendage configuration;
- rudder / skeg configuration;
- cockpit configuration;
- rig / sailplan / mast characteristics;
- other already accepted configuration-sensitive technical criteria.

This list is illustrative, not a silent authorization to invent new fields. The normative Search contract decides scope.

Hard requirements remain hard. `UNKNOWN` remains a first-class result. A missing fact may not be replaced by a guess, probability or favorable default.

Near-miss behavior, including any already accepted ±15% rule, must remain structurally and visually separate from confirmed eligibility. A near miss is never a `CONFIRMED_MATCH`.

## 4. Corpus strategy: coverage, not an arbitrary model count

The former approximately 20–30-design Seed-Corpus ceiling is superseded for Gate-1 readiness.

HullQ must provide enough real technical coverage that realistic target-user searches are **not materially constrained by an artificially small test corpus**.

Do not make 150, 300, 1,000 or any other arbitrary design count the normative gate.

Track two distinct coverage measures:

### 4.1 Catalog Coverage

How many canonical BoatDesigns can be evaluated against the accepted Search product contract with provenance-backed values and explicit `UNKNOWN` where evidence is insufficient?

The existing approximately 1,700 identity-resolved/canonical models are a legitimate enrichment target where the existing scalable research/data pipeline can process them at acceptable marginal cost.

There is no requirement to stop at a smaller round number merely to preserve the old Seed-Corpus concept.

### 4.2 Active-Market Coverage

More important for Gate 1:

> What proportion of currently relevant sailboat inventory can HullQ map to a canonical BoatDesign and, where evidence permits, to a meaningful configuration/truth assessment?

Prioritization should follow:

```text
active-market relevance
× listing frequency
× likely buyer demand
× Search-filter relevance
```

The practical Gate-1 readiness question is:

> Can a realistic target user give HullQ a real boat search without the answer being materially determined by our artificial corpus boundary?

A numeric coverage threshold may be locked later when real acquisition/market data can support a meaningful denominator. Do not invent a percentage before that denominator exists.

## 5. Data-scaling execution rule

Scaling technical data before Gate 1 is permitted and expected when it directly produces the realistic Search corpus required by this amendment.

This is not justified by a vague future "moat" argument. It is justified because corpus breadth and field breadth are part of making the actual product testable.

Use the accepted pipeline and fail-closed semantics:

```text
canonical identity
→ admissible source/evidence discovery
→ configuration resolution where supported
→ Search-contract facts
→ derived metrics only from accepted confirmed inputs
→ provenance
→ UNKNOWN / CONFLICT / AMBIGUOUS where necessary
```

Do not manually perfect every design.

When a field/design cannot be established within the accepted evidence process, retain the correct unresolved state and continue. Aggregate exception classes and inspect systematic/high-impact failures rather than turning every individual missing value into an open-ended research project.

Preferred operating loop:

```text
build
→ ingest real data
→ execute real searches
→ list/inspect failures and conflicts
→ fix systematic problems
→ repeat
```

## 6. Market acquisition before Gate 1

Automated recurring market acquisition is part of the Gate-1 product proposition because continuous monitoring depends on it.

However, no recurring adapter/crawler/poller may be built against a source **before the intended recurring access/use path for that source has been assessed as legally/contractually usable for the contemplated operation**.

The sequence is:

```text
identify source/access path
→ assess intended recurring use / rights / terms
→ determine technical and economic usability
→ if usable: implement adapter/acquisition
→ schedule recurring runs
→ burn in under real conditions
```

"Alternative" or "workaround" means a lawful alternative source or access model, not circumvention of technical, contractual or access restrictions.

Preferred acquisition paths remain, where available:

- authorized/public/partner APIs;
- broker/dealer feeds;
- CRM / MLS / XML / API systems;
- portal/data-provider partnerships;
- direct broker inventory feeds;
- explicitly authorized crawling/polling where such use is permitted.

Do not treat unauthorized marketplace scraping as the foundational business model.

## 7. Minimal automation architecture

Once at least one suitable real recurring acquisition path is available, Gate-1 readiness requires genuine automated operation rather than a purely manual simulation.

The minimal loop may be simple:

```text
scheduler / cron / OS task
→ source adapter
→ retained raw observations
→ normalization
→ listing identity / dedup
→ physical-listing truth assessment
→ PostgreSQL persistence
→ change detection
→ saved-search evaluation
→ alert event
→ real email
```

A distributed queue, Kafka, Celery, Kubernetes or similar infrastructure is **not required by default**. Add operational complexity only when observed load/reliability requirements justify it.

Automation must be idempotent enough to avoid duplicate state/alerts and observable enough to diagnose failed runs.

## 8. Saved Search and Alerts before Gate 1

Saved Search and real alerts move from post-Gate-1 phases into the pre-Gate-1 validation product.

Required:

- persist an exact accepted HullQ Search query;
- associate it with a prepared validation identity/test account;
- re-evaluate it against new/changed market observations;
- emit a real notification when the accepted alert condition is satisfied;
- preserve truth semantics in the alert;
- prevent a near miss or unresolved listing from being silently represented as a confirmed fit.

Full consumer account infrastructure is not required before Gate 1.

Acceptable validation access includes prepared test users / fixed credentials / invitation codes. Do not build OAuth, public self-signup, password-recovery systems or broad account administration merely for the pilot unless a concrete security/operational blocker requires it.

## 9. Validation UI

Gate 1 requires a browser-based Validation UI that exposes the full product proposition without requiring Python, Git or developer knowledge.

It should be clearly marked as a validation/beta interface and may be visually simple.

It must nevertheless make the relevant product behavior usable and understandable:

- complete accepted Search filter contract;
- multi-constraint Search;
- design/configuration identity;
- confirmed match / confirmed non-match / unknown states;
- clearly separated near misses where applicable;
- concise reason/evidence path;
- current offers where lawfully available;
- saved Search;
- monitoring/alert status;
- clear Pro/subscription proposition.

"Slim" means minimal polish and minimal supporting infrastructure. It does **not** mean removing core value-producing functionality from the test.

## 10. Subscription / Pay Pull

HullQ should expose a credible Pro/subscription proposition before or during Gate 1 so willingness-to-pay can be tested against the experienced monitoring benefit.

Do **not** build a large subscription/billing platform before Gate 1.

A thin commercial surface and, if useful, a hosted/external checkout or equivalent real commitment mechanism are sufficient.

Measure separately:

- **Product Pull:** does the user want HullQ to keep monitoring the search?
- **Pay Pull:** is the user willing to pay the tested price for that value?

A weak response to one price point must not automatically convert otherwise strong Product Pull into a RED product verdict.

## 11. Burn-in before external validation

Before real external Gate-1 participants depend on alerts, run the acquisition/monitoring pipeline through enough real scheduled cycles to expose operational failure modes.

Inspect, at minimum where observable:

- source outages / empty responses;
- listing creation/disappearance/reappearance;
- price or attribute changes;
- duplicate listings across observations/sources;
- listing-ID churn;
- unresolved configuration identity;
- repeated alert suppression/idempotency;
- scheduler failures/retries;
- saved-search re-evaluation behavior;
- false confirmed results.

The burn-in exists to avoid testing obvious system instability instead of product value. It is not an excuse for indefinite pre-user perfection.

## 12. External validation design

Gate 1 should use real, unconstrained target-user searches against the realistic corpus and functioning monitoring loop.

The existing standardized neutral protocol and unprompted-value rule remain useful. Do not teach users why HullQ is supposed to be better before observing their behavior.

A high-quality bank of real buyer cases, including cases gathered through advisors/brokers/experienced buyers, is valuable for coverage and regression testing. However, twenty customer profiles operated by two advisors are **twenty cases, not twenty independent users**.

Where practical combine:

- approximately 6–8 direct serious prospective users; and
- a larger set of real-world buyer/search profiles to stress the filter/corpus/monitoring system.

Do not require a named external partner for Gate 1. Any sufficiently relevant real-user source is acceptable.

## 13. Gate 1 interpretation

Gate 1 becomes **End-to-End Product Proposition Validation**, not merely Search-kernel validation.

Primary observed signals remain useful:

- **Decision impact:** HullQ changes shortlist/exclusion/prioritization;
- **Monitoring pull:** user wants the exact Search continuously monitored / alerted;
- **Trust advantage:** user prefers acting on explicit evidence/UNKNOWN instead of unsupported certainty.

Retain the existing unprompted-value discipline and current GREEN/YELLOW/RED thresholds unless a later explicit owner-approved amendment changes them.

Correctness/provenance remain mandatory baselines. A false-confirmed result is a product defect, not evidence that users do not value correctness.

Record Pay Pull separately from Gate-1 Product Pull.

## 14. Relationship to Market Access / Gate 2

Buyer Value Risk and Market Access Risk remain distinct.

This amendment changes their sequencing interaction:

- market-access research begins early enough to identify a lawful recurring acquisition path before that adapter is automated;
- at least one real recurring usable acquisition path is required for the full pre-Gate-1 monitoring experience;
- broader Market Access / Gate-2 classification still evaluates whether enough sustainable inventory access exists for the intended business, not merely whether one technical pilot path works.

A source-rights blocker may block that source adapter. It does not authorize circumventing the blocker and does not automatically invalidate technical Search/data work.

## 15. Slice sequencing after SLICE-0039

Do not widen SLICE-0039. After it is accepted/closed, re-plan subsequent slices around the following dependency order.

This is a sequence of capabilities, **not permission to combine them into one oversized slice**:

1. lock/formalize the complete HullQ Search product contract;
2. implement remaining Search-contract semantics/filters in bounded slices;
3. scale Search-contract data coverage through the existing data/research pipeline;
4. add accepted derived metrics where confirmed inputs allow them;
5. measure catalog and active-market coverage;
6. expose full Search contract through a simple Validation UI;
7. persist exact Saved Searches;
8. resolve at least one legally/contractually usable recurring market-acquisition path;
9. automate that acquisition path;
10. schedule recurring acquisition and retain run/observation state;
11. implement listing identity/dedup/change detection needed by monitoring;
12. connect changed/new market observations to Saved-Search evaluation;
13. send real alerts;
14. expose the slim Pro/subscription proposition;
15. run internal burn-in;
16. run external Gate-1 validation.

Dependencies may cause limited reordering, but later-slice scope may not be pulled into an earlier slice merely for convenience.

## 16. ONE-CAPABILITY / VISIBLE-RESULT rules remain mandatory

Every ordinary slice still delivers exactly one user-visible capability or answers one business-critical hypothesis.

Examples of valid individual capabilities include:

- one bounded new Search filter family;
- one deterministic derived-metric family;
- one bounded corpus-enrichment wave with a measurable Search-coverage result;
- one Saved-Search persistence capability;
- one lawful source adapter;
- one scheduler/run-history capability;
- one listing dedup/change-detection capability;
- one alert-delivery capability;
- one Validation-UI capability.

A full pipeline is a **program outcome composed of bounded slices**, not one giant implementation slice.

Every slice must remain personally executable/observable/inspectable by the Project Owner at completion.

## 17. Anti-scope-creep rule after this amendment

The previous shorthand "do not build much before Gate 1" is no longer sufficiently precise.

Use this test instead:

> **Does this work directly improve the real HullQ Search/monitoring proposition, the data/market coverage required to test it realistically, the operational feasibility of that proposition, or the validity of Gate 1?**

If `NO`, defer it.

If `YES`, it is eligible for prioritization but must still obey dependency order, source rights, the one-capability rule, visible-result rule and strict-truth requirements.

Examples normally deferred before Gate 1:

- native mobile app;
- broad SEO rollout;
- elaborate design system/animations;
- full OAuth/self-service account lifecycle;
- custom subscription/billing platform;
- broker admin suite;
- generic recommendation AI;
- large distributed infrastructure without observed need;
- speculative market-history systems not required by the validation proposition.

## 18. Working philosophy

HullQ should now bias toward executing the actual product rather than repeatedly debating hypothetical edge cases.

Preferred loop:

> **Build → run on real data → inspect concrete failures → fix systematic/high-impact problems → repeat.**

This does not relax truth discipline. The existing provenance, configuration, explicit-UNKNOWN and fail-closed architecture is what makes this faster loop safe enough to use.

Operational convenience may remain manual where appropriate. Mechanisms fundamental to the product promise should be exercised for real before Gate 1.
