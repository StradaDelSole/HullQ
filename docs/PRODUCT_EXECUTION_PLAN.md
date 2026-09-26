# HullQ Product Execution Plan

**Status:** ACCEPTED execution policy, amended by later marketplace decisions  
**Applies from:** completion of SLICE-0038 onward  
**Owner:** Project Owner  
**Execution principle:** **Strict truth. Fast product. Test the business before building the business.**

> **Current marketplace amendment (2026-09-14):** The early-plan language below predates the accepted native-marketplace implementation and the owner-direct pivot. HullQ is now a native **broker-first mixed-supply** marketplace. `docs/PRODUCT_EXECUTION_PLAN_OWNER_DIRECT_RECONCILIATION_2026-09-14.md`, `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md` and `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md` supersede any statement below that treats a native marketplace as merely possible later, limits private owners to referral-only supply, or treats independent owner-direct listings as out of scope. The execution discipline, truth principles and validation logic in this file remain controlling where non-conflicting.

> **Broker-launch execution amendment (2026-09-26):** After the accepted foundation through SLICE-0065 and READY SLICE-0066, execution priority shifts toward the shortest coherent professional `Broker → Listing → Buyer Lead → Broker Operation` loop. `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md` controls that prioritization. The ONE-CAPABILITY rule remains, but one capability means one coherent user-visible/business-critical outcome rather than one field, endpoint or technical layer. Risk-based slice sizing below explicitly permits larger vertical slices when accepted semantics already decide the material behavior and implementation is mainly composition. Strict truth, authorization, provenance, review and launch-gate requirements are unchanged.

## 1. Purpose

HullQ is no longer executed as a broad architecture-first or database-completeness program. From SLICE-0039 onward, work is prioritized by the largest unresolved product/business risk and must produce either one user-visible capability or one business-critical hypothesis result.

The product thesis is:

```text
technical buyer requirements
→ matching BoatDesigns
→ matching factory configurations
→ current market inventory where lawfully available
→ listing-level CONFIRMED / UNKNOWN / NON-MATCH
→ save / monitor / alert
```

HullQ's differentiation is not raw marketplace aggregation. It is trustworthy configuration-aware decision support that distinguishes:

```text
this design can fit
```

from:

```text
this specific offered boat is confirmed to fit
```

`UNKNOWN` is a valid product result and must never be converted to a plausible guess merely to increase apparent coverage.

The two equal business-validation risks originally framed by this plan remain useful:

```text
A. Buyer Value Risk
Does strict configuration/listing truth materially change buyer behavior?

B. Market Access / Supply Risk
Can HullQ obtain enough current inventory on sustainable legal/economic terms?
```

Later owner-accepted marketplace decisions changed the supply strategy from external-access-first uncertainty to native broker-first marketplace supply and, on 2026-09-14, to broker-first mixed professional + owner-direct supply. That evolution does not relax buyer-value validation or strict truth.

## 2. Original validation sequence and retained principles

The historical Phase A–J plan below is retained because its validation discipline still informs execution. Where a phase assumes that HullQ has no native marketplace yet, read that assumption as historical and defer to the later marketplace reconciliations.

### Phase A — SLICE-0038 core market proof

Finish SLICE-0038 as originally bounded:

```text
technical Search
→ real BoatDesign/configuration match
→ one permitted live market source
→ real listings
→ physical-listing truth assessment
```

Owning.pro was a bounded pilot source, not the long-term market-acquisition strategy.

The historical instruction not to automatically build a second marketplace adapter remains a useful anti-scope rule.

### Phase B — Seed Corpus

Build a bounded initial corpus of approximately **20–30 real, configuration-aware BoatDesigns** sufficient for real buyer tests.

Selection priority:

```text
market relevance × configuration diversity × likely buyer demand
```

Rules:

- completeness is not required; search usefulness is required;
- do not research every possible field before testing;
- prioritize fields needed by real test queries;
- retain `UNKNOWN` where evidence is insufficient;
- market sources may help prioritize which designs matter, but do not automatically become technical-fact sources;
- technical facts still follow accepted provenance/source-rights rules.

#### Pre-Gate-1 data discipline

Until Gate 1 has been classified, the future possibility of a proprietary configuration/evidence corpus is a **North-Star moat hypothesis, not a reason to expand the corpus**.

Any slice whose primary effect is technical-data/corpus growth must directly support at least one of:

1. one of the bounded approximately 20–30 Seed-Corpus BoatDesigns;
2. a concrete requirement needed by an active/planned Concierge test query; or
3. a real blocker preventing those tests from running.

If it does none of these, defer it until after Gate 1. "Building the moat", increasing headline coverage, completing unused fields, or accumulating provenance depth for future value is not sufficient justification before product value is validated.

The existing `ONE-CAPABILITY CHECK` and `VISIBLE-RESULT CHECK` apply equally to Data/Research slices; data work is not exempt merely because correct data may become defensible later.

### Phase C — Concierge Product Validation

Run standardized moderated tests with **6–8 serious prospective users**. The first three tests should happen as soon as the Seed Corpus can support their real searches; do not wait for perfect corpus completion.

#### Standard protocol

For every participant:

1. participant describes a real boat search without a HullQ explanation;
2. requirements are captured exactly;
3. show the current alternative/search reality first where practical;
4. show HullQ output second;
5. do not explain HullQ's supposed advantage yet;
6. let the participant react / think aloud;
7. ask neutral follow-up questions only after the spontaneous reaction;
8. explain truth/configuration semantics only at the end if needed.

Do not lead with statements such as "HullQ is more accurate here". Prefer neutral questions such as "What would you do based on these results?" and "Did anything change your decision?"

Where useful, compare against both a broad aggregator/search product and a buyer-intelligence/recommendation product. Current reference classes are **Listings Port** and **SailboatLab**. The purpose is not a generic three-product usability contest; it is to test whether HullQ's evidence/configuration semantics create value against both breadth-first search and personalized recommendation alternatives.

#### Gate 1 — Product Value

Primary signals:

- **Decision impact:** HullQ changes shortlist, exclusion or prioritization of a boat.
- **Monitoring pull:** participant wants the concrete search saved, monitored or alerted.
- **Trust advantage:** participant prefers HullQ's `CONFIRMED / UNKNOWN` distinction over a generic model claim and would act accordingly.

Secondary praise such as "interesting", "nice idea" or "I would look at this" does not satisfy the gate.

**Unprompted-value rule:** a primary signal counts toward GREEN only if the relevant behavior/value is visible **before** HullQ's configuration-truth/provenance advantage is explained to the participant. A participant does not need to use HullQ terminology; changing a decision, requesting monitoring, or preferring the evidence-backed result is sufficient. Benefits that appear only after the moderator explains why HullQ is supposed to be better must be recorded as prompted feedback and do **not** satisfy a primary GREEN signal.

Classification after 6–8 tests:

- **GREEN:** at least 5 of 8 (or 4 of 6 if stopped after six because the result is already clear) show at least one of `Decision impact` or `Monitoring pull`, **and at least half of all tested participants** show a real `Trust advantage`; the counted primary signals satisfy the unprompted-value rule above.
- **YELLOW:** meaningful value exists, but mainly for a narrower user group or a subset of technically constrained searches, or the value is visible but requires more explanation than expected. Continue with a narrower beachhead rather than claiming broad-market validation.
- **RED:** fewer than half show `Decision impact` or `Monitoring pull`, normal model/listing search is repeatedly judged sufficient, or the supposed configuration-truth advantage only becomes persuasive after repeated moderator explanation. Do not continue the existing product expansion by default.

If Gate 1 is RED, evaluate only these bounded fallback directions before further investment:

1. narrower serious-cruising / bluewater / technically constrained buyer segment;
2. research/comparison/reference product;
3. B2B technical-data enrichment.

If none shows credible pull, stop HullQ rather than extending the roadmap to justify sunk cost.

### Phase D — Market Access / Supply Track

The original plan treated external market-access research as a parallel risk. Later owner decisions established native HullQ supply as the strategic foundation, first professional and now broker-first mixed supply.

External APIs/feeds/partnerships remain optional coverage channels where lawful/useful; they are not prerequisites for owner-direct or professional native listings.

Relevant external target categories may still include:

- public/partner APIs;
- broker/dealer inventory feeds;
- broker CRM / MLS / XML/API systems;
- portal partnerships;
- aggregator/data-provider partnerships;
- selected brokers with direct feed capability.

External access must never become an excuse to bypass source rights or first-party marketplace truth.

### Phase E — Minimal Web Alpha

The historical Alpha principle remains: let a normal user express real requirements and see truthful results without requiring accounts/payments/broad SEO simply to prove value.

The current product has advanced beyond the original Alpha assumptions, but any new public surface still follows the same constraint: small, truthful and understandable before broad expansion.

**UX binding:** every slice that creates or materially changes public Search, Search-result, BoatDesign, comparison, market, save/monitor or alert UI MUST name `docs/PRODUCT_UX_PRINCIPLES.md` as a controlling artifact.

### Phase F — Demand-driven Coverage

Prioritize technical coverage by:

```text
observed search demand × configuration importance × market availability
```

Do not optimize for headline database size. A smaller highly relevant verified corpus is preferred over a large low-confidence corpus.

### Phase G — Saved Search

Test whether users actually save complex technical searches before monetizing them.

### Phase H — Fit-confirmed Alerts

The core Pro candidate remains stronger when it means:

```text
A new offered boat appeared that is confirmed to satisfy your requirements.
```

Measure actual response/use before assuming willingness to pay.

### Phase I — Monetization Validation

Test commercial value only after the corresponding product value exists.

Potential surfaces include:

- Free vs Pro buyer boundaries;
- saved-search / fit-alert pricing;
- price-change / market-intelligence value where source rights permit;
- qualified broker lead economics;
- professional workflow/analytics value;
- optional owner-direct verification/processing services;
- neutral seller-to-broker referral economics;
- relevant later transaction/insurance/finance/title partner economics.

The historical instruction `do not build a native marketplace merely to avoid marketplace-access constraints` has been overtaken by explicit owner decisions and accepted native-marketplace implementation. It remains useful only as a warning against panic-driven scope changes. The current owner-direct pivot is an explicit owner-accepted product decision, not an access-workaround.

Organic Search is now a hard non-commercial invariant: monetization may not affect organic eligibility, match classification or organic ordering.

### Phase J — Founder scale decision

The original ambition framing remains a useful planning lens:

- **Lean HullQ:** roughly €1–5k MRR ambition, solo/low-maintenance, limited partnerships; or
- **Growth HullQ:** roughly €10–20k+ MRR ambition, deliberate B2B sales, contracts, wider coverage and possibly a small team.

Growth is not an automatic continuation of product validation and never authorizes pay-to-rank organic Search.

## 3. Product-slice execution rules from SLICE-0039 onward

Every new primary product/research slice must answer both questions before it may become `READY`:

### ONE-CAPABILITY CHECK

**Does this slice deliver exactly one user-visible capability OR answer exactly one business-critical hypothesis?**

If `NO`, split or reduce the slice before starting.

### VISIBLE-RESULT CHECK

**Can the Project Owner personally execute, observe or inspect the result at the end of this slice?**

If `NO`, presume the slice is infrastructure-first and require an explicit blocker rationale before proceeding.

### RISK-BASED SLICE SIZING

The ONE-CAPABILITY rule is a product-boundary rule, not a micro-slicing rule.

A single slice MAY span persistence, domain/application logic, API, frontend and tests when all of those layers are mechanically necessary to deliver one coherent capability and no second independent product/domain policy is being introduced.

Keep a slice deliberately narrow when it introduces a material independent risk, including:

- identity allocation/resolution or deduplication authority;
- truth/provenance semantics;
- authorization, tenant isolation or MFA/step-up policy;
- money/payment;
- destructive or difficult-to-reverse migration;
- cross-Organization ownership/rights;
- concurrency/idempotency authority;
- media rights/privacy/security;
- lifecycle/outcome semantics;
- a new Search eligibility/classification rule.

Permit a larger vertical slice when:

1. accepted decisions/specifications already settle the material semantics;
2. remaining work is mainly composition across layers;
3. the result is one end-to-end user-visible capability;
4. rollback/review is still tractable;
5. focused and full-system validation can prove the boundary.

If implementation discovers a new material policy decision or ambiguity, stop and split/reassess rather than hiding it inside a larger slice.

Additional rules:

- at most one new external dependency per ordinary product slice;
- do not create generic frameworks without a current consumer;
- do not combine unrelated API + persistence + auth + frontend + SEO work merely because the pieces belong to the same future roadmap area; combining layers is permitted only when they are inseparable parts of the one selected vertical capability;
- a major amendment is a signal to reassess whether the slice was oversized or contained an undiscovered policy boundary;
- future-proofing is not a reason to widen a slice;
- strict truth/provenance/fail-closed behavior is not relaxed for speed;
- process/governance work that does not directly remove a real blocker, correct a real contradiction or satisfy a triggered gate should not interrupt the visible product sequence.

### BROKER-LAUNCH PRIORITY

From the accepted SLICE-0066 boundary onward, post-slice reassessment should strongly prefer work that advances:

```text
broker creates
→ adds media
→ publishes
→ buyer contacts
→ broker handles lead
→ broker edits/maintains inventory
→ explicit outcome / scale capabilities as required
```

A capability outside this sequence may still take priority when it removes a real truth/security/legal blocker, satisfies a triggered mandatory commitment, or has demonstrably higher business leverage. Otherwise the reassessment must state why it should interrupt the launch path.

Structured import remains strategically important but must feed the normal draft/marketplace workflow rather than become a second truth pipeline. It should move forward aggressively once the coherent create/publish/operate path exists and must be implemented before scaled broker onboarding under REQ-BROKER-027.

After the 2026-09-14 pivot, any slice touching listing/supply, seller identity/verification, representation conflict, referral, marketplace monetization or Search must reconcile against the owner-direct product direction/spec and the mixed-supply execution reconciliation. After the 2026-09-26 execution amendment, relevant reassessment/readiness must also reconcile against `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`.

## 4. Strategic freeze / explicit pivots

The historical strategic freeze prevented casual roadmap reopening. The principle remains valid: do not pivot merely because another feature looks attractive.

The 2026-09-14 owner-direct decision is an explicit Project Owner pivot based on a substantive strategy review (broker channel conflict, Search-ranking economics, private-seller choice, monetization and fraud/trust design). It therefore legitimately supersedes the earlier broker-only public-supply assumption.

Further material pivots require the same explicit treatment rather than implementation-by-drift.

## 5. Current market/competitor conclusions retained and amended

- Listing aggregation alone is not HullQ's moat.
- Listings Port validates demand for cross-market sailboat discovery and already covers aggregation/dedup/alerts/history-like use cases; HullQ should not try to win merely by aggregating more sources.
- SailboatLab demonstrates that buyer-side model comparison, design-vs-ad distinction, scoring and market monitoring already exist; HullQ's stronger differentiation hypothesis is field-level physical-listing evidence, configuration scope, deterministic hard constraints, explicit UNKNOWN/conflict and auditable provenance.
- Keel Index is a strong benchmark for coherent BoatDesign decision hubs, market-context presentation and product-led/data-driven SEO; HullQ should adopt useful interaction/information patterns without copying visual identity or relaxing truth semantics.
- The long-term composite vision — broad market coverage + strong decision-hub/SEO surfaces + guided discovery + HullQ truth/search integrity + excellent UX — remains a North Star, not permission to widen one slice.
- A defensibility path can compound through configuration/evidence quality, PhysicalBoat/MarketEpisode identity, market history, professional workflows, owner-direct workflows, buyer-intent data, marketplace liquidity and trust.
- General AI assistants are both competitive threat and possible future distribution/API channel; HullQ should retain direct product/distribution capability.
- Broker/CRM/MLS/feed relationships may remain cleaner external inventory paths than scraping public portals.
- Scraping multiple marketplaces is not the foundational business model.
- The native marketplace is no longer a speculative possible-later outcome: it is accepted and partially implemented. Current supply direction is broker-first mixed professional + owner-direct inventory.
- A meaningful early business-model asymmetry exists where incumbents depend on paid visibility or restrictive supply rules; HullQ's durable moat, however, must come from product/data/network quality rather than incumbent constraints alone.

## 6. Review obligation

Independent readiness/review for every post-0038 slice must explicitly record:

```text
ONE-CAPABILITY CHECK: PASS | FAIL
VISIBLE-RESULT CHECK: PASS | FAIL
PRODUCT EXECUTION PLAN ALIGNMENT: PASS | FAIL
```

A failed One-Capability check blocks readiness. A failed Visible-Result check blocks ordinary product work unless the slice documents a genuine prerequisite/blocker exception.

For SLICE-0051 and later, decision/implementation reconciliation remains mandatory under the current slice template. For SLICE-0052 and later, trigger-gate evidence remains mandatory.

From the owner-direct pivot onward, relevant readiness/review must additionally verify that it does not rely on the superseded broker-only/private-FSBO-out-of-scope assumption and that it preserves organic Search commercial independence where Search is affected.
