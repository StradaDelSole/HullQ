# HullQ Product Execution Plan

**Status:** ACCEPTED execution policy  
**Applies from:** completion of SLICE-0038 onward  
**Owner:** Project Owner  
**Execution principle:** **Strict truth. Fast product. Test the business before building the business.**

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

The two equal business-validation risks are:

```text
A. Buyer Value Risk
Does strict configuration/listing truth materially change buyer behavior?

B. Market Access Risk
Can HullQ obtain enough current inventory on sustainable legal/economic terms?
```

Gate 1 addresses A. Gate 2 addresses B. Neither substitutes for the other.

## 2. Locked immediate sequence

### Phase A — SLICE-0038 core market proof

Finish SLICE-0038 as currently bounded:

```text
technical Search
→ real BoatDesign/configuration match
→ one permitted live market source
→ real listings
→ physical-listing truth assessment
```

Owning.pro is a bounded pilot source, not the long-term market-acquisition strategy.

After SLICE-0038, do **not** automatically build a second marketplace adapter.

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

Where useful, compare against both a broad aggregator/search product and a buyer-intelligence/recommendation product (currently Listings Port and SailboatLab are the reference classes), without teaching the participant what HullQ is supposed to do better.

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

### Phase D — Market Access Track (parallel, non-blocking)

Market access research runs in parallel with the first user tests but **must not block a positively validated Web Alpha**.

Start with **3–4 high-quality contacts**, then expand as capacity allows to a maximum of **12 qualified outbound contacts** during this validation pass.

Target categories:

- public/partner APIs;
- broker/dealer inventory feeds;
- broker CRM / MLS / XML/API systems;
- portal partnerships (including Scanboat/Open Marine where appropriate);
- aggregator/data-provider partnerships;
- selected brokers with direct feed capability.

The concrete ask is whether HullQ may consume current inventory through API/XML/feed, normalize and technically enrich it, show/route qualified buyers with attribution/deep-link, and under what commercial/storage/display terms.

#### Gate 2 — Market Access

Evaluate after **12 qualified outbound contacts OR 21 calendar days after the first qualified request, whichever occurs first**. Do not extend the research phase merely because more possible contacts exist.

- **GREEN:** at least one operationally usable path exists: suitable API rights, real pilot feed, concrete portal/aggregator API/feed/license offer, or a sufficiently repeatable direct-broker feed path.
- **YELLOW:** technically credible feed/access paths and serious discussions exist, but no usable agreement/path is yet operational. Continue product work while treating market coverage as a material risk.
- **RED:** relevant providers systematically refuse access or offer only economically/legally unusable terms. Reassess the market-connected business model, but do not retroactively invalidate a useful technical-search product.

A slow third-party response never blocks the first Web Alpha.

### Phase E — Minimal Web Alpha

Build only if Gate 1 is not RED.

The Alpha should let a normal user express real requirements and see:

```text
requirements
→ matching designs
→ matching configurations
→ available current offers / lawful outbound inventory links
→ CONFIRMED / UNKNOWN / NON-MATCH
→ why / provenance where useful
```

Do not require accounts, payments, large UI systems or broad SEO rollout for the first Alpha.

**Phase E UX binding:** every slice that creates or materially changes public Search, Search-result, BoatDesign, comparison, market, save/monitor or alert UI MUST name `docs/PRODUCT_UX_PRINCIPLES.md` as a controlling artifact. The Alpha remains deliberately small, but its truth states, requirement semantics and design-vs-physical-listing boundary must be understandable without training or a developer explanation.

### Phase F — Demand-driven Coverage

After the Alpha produces real query data, replace Seed-Corpus assumptions with observed demand.

Prioritize new technical coverage by:

```text
observed search demand × configuration importance × market availability
```

Do not optimize for headline database size. A smaller highly relevant verified corpus is preferred over a large low-confidence corpus.

### Phase G — Saved Search

Test whether users actually save complex technical searches before monetizing them.

### Phase H — Fit-confirmed Alerts

The core Pro candidate is not merely "new model listed" but:

```text
A new offered boat appeared that is confirmed to satisfy your requirements.
```

Measure actual response/use before assuming willingness to pay.

### Phase I — Monetization Validation

Only after product pull is demonstrated, test:

- Free vs Pro boundaries;
- saved-search / fit-alert pricing;
- price-change / market-intelligence value where source rights permit;
- qualified broker lead economics;
- feed/data-enrichment value.

Do not build a native marketplace merely to avoid marketplace-access constraints.

### Phase J — Founder scale decision

After Alpha + product validation + initial market-access evidence, the Project Owner explicitly chooses between:

- **Lean HullQ:** roughly €1–5k MRR ambition, solo/low-maintenance, limited partnerships; or
- **Growth HullQ:** roughly €10–20k+ MRR ambition, deliberate B2B sales, contracts, wider coverage and possibly a small team.

Growth is not an automatic continuation of Alpha validation.

## 3. Product-slice execution rules from SLICE-0039 onward

Every new primary product/research slice must answer both questions before it may become `READY`:

### ONE-CAPABILITY CHECK

**Does this slice deliver exactly one user-visible capability OR answer exactly one business-critical hypothesis?**

If `NO`, split or reduce the slice before starting.

### VISIBLE-RESULT CHECK

**Can the Project Owner personally execute, observe or inspect the result at the end of this slice?**

If `NO`, presume the slice is infrastructure-first and require an explicit blocker rationale before proceeding.

Additional rules:

- at most one new external dependency per ordinary product slice;
- do not create generic frameworks without a current consumer;
- do not combine API + persistence + auth + frontend + SEO merely because they belong to one future feature;
- a major amendment is a signal to reassess whether the slice was oversized;
- future-proofing is not a reason to widen a slice;
- strict truth/provenance/fail-closed behavior is not relaxed for speed;
- process/governance work that does not directly remove a real blocker should not interrupt the visible product sequence.

## 4. Strategic freeze

Before SLICE-0038 is complete, do not reopen the roadmap merely for additional internal analysis.

A roadmap reconsideration before then requires a **material new external fact** capable of changing the product/business premise, such as a newly discovered controlling legal restriction, a major competitor capability that invalidates the core differentiation, or decisive real-user evidence.

After SLICE-0038, decisions follow the gates in this document rather than returning automatically to architecture-first planning.

## 5. Current market/competitor conclusions retained

- Listing aggregation alone is not HullQ's moat.
- Listings Port validates demand for cross-market sailboat discovery and already covers aggregation/dedup/alerts/history-like use cases; HullQ should not try to win merely by aggregating more sources.
- SailboatLab demonstrates that buyer-side model comparison, design-vs-ad distinction, scoring and market monitoring already exist; HullQ's stronger differentiation hypothesis is field-level physical-listing evidence, configuration scope, deterministic hard constraints, explicit UNKNOWN/conflict and auditable provenance.
- Keel Index is a strong benchmark for coherent BoatDesign decision hubs, market-context presentation and product-led/data-driven SEO; HullQ should adopt the useful interaction/information patterns without copying its visual identity or relaxing truth semantics.
- The long-term composite vision — broad market coverage + strong decision-hub/SEO surfaces + guided discovery + HullQ truth/search integrity + excellent UX — is a **North Star, not an execution roadmap or feature backlog**. It may not be used to widen pre-Gate-1 scope.
- A potential defensibility path is staged: execution discipline first; only after product value is validated may a proprietary configuration/evidence corpus become an intentional moat investment; later market history, feed relationships and buyer-intent data may compound that advantage. The future moat thesis does not authorize premature corpus expansion.
- General AI assistants are both a competitive threat and a possible future distribution/API channel for HullQ's verified vertical data. They are an **additional channel, not a distribution foundation**; HullQ should retain direct product/distribution capability rather than depend on another platform's tool/API policies.
- Scanboat and broker-syndication research indicate that broker/CRM/MLS/feed relationships may be cleaner long-term inventory paths than scraping many public portals.
- Scraping multiple marketplaces is therefore not the foundational business model.
- A native marketplace is a possible later outcome only if supply relationships naturally justify it; it is not a panic pivot.

## 6. Review obligation

Independent readiness/review for every post-0038 slice must explicitly record:

```text
ONE-CAPABILITY CHECK: PASS | FAIL
VISIBLE-RESULT CHECK: PASS | FAIL
PRODUCT EXECUTION PLAN ALIGNMENT: PASS | FAIL
```

A failed One-Capability check blocks readiness. A failed Visible-Result check blocks ordinary product work unless the slice documents a genuine prerequisite/blocker exception.

Until Gate 1 has been classified, any readiness/review for a slice whose primary effect is corpus/data growth must additionally state whether it directly serves the bounded Seed Corpus, an active/planned Concierge query, or a real validation blocker. If not, the slice is not aligned with this plan and must be deferred.
