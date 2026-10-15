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

> **Owner-accepted post-SLICE-0083 Search execution priority (2026-10-13):** The accepted structured multi-format private-draft import is now IMPLEMENTED by SLICE-0083. The Owner selected **SLICE-0084 broker pre-publication Search-fit** (`REQ-BROKER-026`/`MVP-BROKER-010`; readiness pending), and directed that technical Buyer Search coverage then receive priority in successive reviewed product slices: **LOA** first, **rudder/skeg** next, a separately justified mapping decision for **long/full keel** within the existing keel criterion, and further beam/displacement/rig/hull-material plus later qualified technical-profile fields. Before selecting any different ordinary post-0084 capability, the reassessment MUST explicitly review this owner priority and show either measurable Search progress or a concrete hard-gate/blocker reason and an explicit Owner-approved reprioritization. The full governing scope, evidence, data/truth boundaries and outstanding obligations are in `docs/POST_SLICE_0083_SEARCH_PRIORITY_REASSESSMENT_2026-10-13.md`. This creates **no automatic slice number after 0084**, does not authorize a new criterion before readiness/implementation acceptance, and preserves broker, owner-direct and production hard gates.

> **Superseding post-SLICE-0084 Owner execution decision (2026-10-13):** After the accepted SLICE-0084 Search-fit and successful local FINISH, the Owner expressly approved **SLICE-0085 bounded Multi-Criteria Technical Search Foundation with an initial actual-filter bundle** rather than a costly independent slice/review stack for every new criterion. This supersedes only the earlier implied one-at-a-time *cadence*, not the binding order or any Search-truth/production safeguards. The bundle targets exact LOA min/max/range, qualified rudder/skeg categorical coverage, and a separately independently guarded `LONG_KEEL` extension to the existing keel criterion. Public Buyer Search and private Broker Search-fit must reuse one static supported-criterion registry and existing deterministic FieldResolution/NamedVariant/current concrete-claim kernel. No unbounded all-fields-at-once refactor or automatically exposed schema fields. Governing reconciliation: `docs/POST_SLICE_0084_MULTICRITERIA_SEARCH_REASSESSMENT_2026-10-13.md`; scoped readiness: `docs/slices/SLICE-0085-multicriteria-technical-search-foundation.md` (not effective until independently accepted docs PR merge); tracking: issue #339. Only independently accepted implementation/closure can increment actual accepted technical criterion count from current **2**. Existing export/reports/owner-direct/trust/production gates remain binding.

> **SLICE-0085 Owner Acceptance Closure (2026-10-14):** Owner expressly accepted implementation PR #345 (exact implementation head `12388b18e526ac5ac1e5d9747538fff99f511518`, squash main `c006016466d6a90c9c7ff083eaa3a0b0ba03c282`; independent exact-head review `5510329645`). The shared typed finite Search registry and first bundled Buyer/Broker Search expansion are **IMPLEMENTED**: accepted public hard dimensions advance **2 → 4** (LOA min/max range = one; evidence-qualified rudder configuration = one), with private illustrative prepublication broker Search-fit parity. Conservative `LONG_KEEL`/full-keel taxonomy remains **UNSUPPORTED** by public Search; no new public dimension can be inferred from it. SLICE-0057 buyer sensitivity for new LOA/rudder-active queries is visibly unavailable rather than omitting hard constraints; pre-existing draft/keel-only comparison remains implemented. Exact gate count is advanced solely by the separately reviewed closure. Owner's scalable *bundled* future Search strategy remains binding, but **SLICE-0086 is UNSELECTED** until mandatory post-0085 reconciliation, explicit Owner selection and independent READY. No new live production data/pilot/public launch, and all broker export/reporting, buyer persistence, trust/owner-direct and production obligations remain open at their existing accepted triggers. See `docs/slices/SLICE-0085-acceptance-closure.md`.

> **Post-0085 Owner-selected first-level discovery priority (2026-10-14):** The Owner confirmed `FINISH_SLICE.bat` for Owner-accepted 0085 and approved HullQ's inclusive sailing-vessel market posture: recreational sailing yachts/multihulls first, with motorsailers, traditional and commercial sailing craft eligible in principle under accepted data/trust/compliance boundaries. Next selected SLICE-0086 is a **bounded structural Buyer Search first level** with combinable **hull form, cockpit position and deck saloon/pilothouse** facets, independently qualified against BoatDesign/NamedVariant AND seller's current concrete PhysicalBoat facts and mirrored in authorized private broker Search-fit. These are not a single exclusive boat-type mega-enum. Motorsailer/traditional/commercial authorization are distinct future axes and cannot be inferred from `COMMERCIAL` use-history, age, model text or photographs. This is an explicit Owner-approved product/user-navigation priority **before** the further beam/displacement/material/rig numeric/technical bundle, without cancelling that future work or the `LONG_KEEL` blocker. Governing reconciliation `docs/POST_SLICE_0085_FIRST_LEVEL_SAILING_VESSEL_DISCOVERY_REASSESSMENT_2026-10-14.md`; proposed READY `docs/slices/SLICE-0086-first-level-sailing-vessel-discovery.md`. Implementation requires independent exact-HEAD docs review/CI/repro+merge and normal Owner START. Accepted criteria-count remains **4** until independently accepted future implementation/closure; no production provider/data/pilot launch or other MVP gate is relaxed.

> **SLICE-0086 Owner Acceptance Closure (2026-10-15):** The Owner expressly accepted SLICE-0086 ("0086 akzeptiert") after independent exact-HEAD implementation review ACCEPT (`4337463fde821e8fd5da78e1db718f43d776ccc6`, PR #349 comment `6193304146`), successful same-HEAD CI `38742683649` and Ubuntu/Windows reproducibility `38742684089`; implementation squash-merged as `a2bb532a5a7b7d15a51caf71c82c46763796f6f4`. This implements the approved **three independent first-level positive Buyer Search facets** `hull_configuration` (MONOHULL/CATAMARAN/TRIMARAN), `cockpit_position` (AFT/CENTER/FORWARD/MULTIPLE) and `deck_saloon` (DECK_SALOON/PILOTHOUSE) alongside the four existing qualified native Search dimensions, raising the accepted hard dimension count **4 → 7 only through the independently reviewed formal closure**. The same static typed FieldResolution/NamedVariant + current independently asserted concrete PhysicalBoat MUST/AND kernel powers public EN/DE/FR/PT/ES Buyer Search and private authorized Broker Search-fit. Third-party class labels, image/model naming and ambiguous layout cannot become verified/current facts by inference; public `OTHER` or `NONE` options are not introduced, known design absence differs from UNKNOWN, and impossible MULTIPLE/cockpit_count=1 fails closed. The real PG18/FastAPI/**built Astro SSR** vertical proof and separate design/configuration versus actual offered-boat evidence were independently source reviewed; reviewer does not claim to have rerun the implementer's local inspector. This is **not** new seller supply, buyer Saved Search, full boat-type/legal/commercial taxonomy, an owner-direct launch, a production deploy or real customer pilot. **SLICE-0087 remains UNSELECTED** pending post-0086 reconciliation and Owner approval. The next selection must estimate the safe remaining slice distance to the first externally visible real listing and compare additional technical Search fields versus broker-portability/reporting, owner-direct safety/trust/privacy and production/provider gates. `LONG_KEEL` still requires independent taxonomy proof. See `docs/slices/SLICE-0086-acceptance-closure.md`.

> **SLICE-0087 Owner Acceptance Closure (2026-10-15):** The Owner expressly accepted `SLICE-0087` (“0087 akzeptiert”) after independent exact-HEAD ACCEPT on amended implementation `88c8baa3e8451f9b0afaca776766b1f5a450f354` (PR #352 review comment `6202278022`, explicit Owner acceptance comment `6202366086`), all green exact-HEAD CI `38803674528` and manufacturer reproducibility `38803674483`. The implementation merged to `main` as `e6d30f1671e6834d097068a7318a4d84c8f96e04`. The two newly accepted Buyer Search dimensions are exact overall **beam** (`beam_min`/`beam_max` one inclusive SI-metre range dimension) and conservative positive `hull_material` (GRP_FIBERGLASS/STEEL/ALUMINUM/WOOD one category dimension), mirrored by authorized private Broker Search-fit and optional immutable current PhysicalBoat claim editing. Valid broader PhysicalBoat materials do not become public hard Search values; neither design `wood_composite` nor `carbon` yields an unproved mapping. Nine public hard technical dimensions are accepted **7 → 9 solely in the separately reviewed formal closure**. Shared one-configuration AND, D29, FieldResolution+NamedVariant, independently current publisher claims and five-language truthful evidence remain unchanged. Two initial review findings (real built SSR positive material/mixed old+new proof; individual broker editor labels) were closed before acceptance. `LONG_KEEL`/displacement/rig, buyer Saved Search/sensitivity, broker export/periodic reporting, owner-direct trust/publication, production provider configuration and real broker pilot remain separately governed. **SLICE-0088 is UNSELECTED** until post-0087 reconciliation, explicit Owner selection and independent READY. Actual first real external listing still requires applicable Production Readiness/Launch Pack gates and automatic PostgreSQL standby/failover before buyer exposure. Governing closure: `docs/slices/SLICE-0087-acceptance-closure.md`.

> **Post-SLICE-0087 Owner-selected interoperability priority (2026-10-15):** After SLICE-0087 was Owner-accepted, implementation/closure merged and local `FINISH_SLICE.bat 0087` confirmed SUCCESS, the Owner selected **SLICE-0088 Broker Inventory Portability & Syndication-Ready Export Foundation**. Broker-controlled inventory should be authorable **first in HullQ** and then downloadable in all **eight accepted 0083 import format families** (CSV, TSV, XLSX, XLS, XLSB, ODS, structured JSON, pinned NautiX 1.4 XML) as actual genuine format bytes — subject to independent exact-header/roundtrip proof and secure writer dependency validation, never renamed extensions. The user-visible action is one authorized Select→Completeness/Rights Preview→Download workflow with stable Organization-scoped listing references, source/current-state/rights truth and bounded error/omission details. This aims to fulfill `REQ-BROKER-022`/`MVP-BROKER-009` only after independent implementation and separate Owner-accepted closure; until then they remain PENDING. No automatic upload/feed, YachtWorld/BoatWizard agreement, target platform import entitlement, background publish/update/withdrawal/ack or co-brokerage rights are conferred; later real destination profiles/integration need independent approval. Public Boats Group EU subscription/BoatWizard feature research is retained in `docs/research/BOATS_GROUP_EU_BROKER_FEATURE_BENCHMARK_2026-10-15.md`; relevant later gaps include factual Listing Optimizer-style completeness feedback (only narrow per-export preflight in 0088), `REQ-BROKER-028` periodic performance/engagement reports before paid/broad broker launch, volume-gated privacy-safe Search Demand, verified broker profiles and licensed market comps/LeadFlow interoperability. Do not turn competitor marketing into acceptance, proprietary-data rights or organic paid Search influence. `SLICE-0088` needs independently reviewed docs-only READY/CI/manufacturer/merge and normal Owner `START_SLICE.bat` before implementation. Canonical Search count stays **9**, Production Readiness `IN_PROGRESS`, Launch Pack `NOT_STARTED`, no real external data or pilot authorized. Governing reconciliation: `docs/POST_SLICE_0087_BROKER_EXPORT_REASSESSMENT_2026-10-15.md`; readiness contract: `docs/slices/SLICE-0088-broker-inventory-portability-export.md`.

> **Before SLICE-0088 START — 2026-10-16 external code-review and Boats Group feature adoption reconciliation:** The Project Owner submitted an independent Claude LLM technical review v0.3 (reads repo dumps, explicitly executes zero tests) and instructed HullQ to retain and systematically utilize **all relevant** studied YachtWorld/Boats Group features, including functionality HullQ currently lacks. The canonical exact-main counterreview is in `docs/POST_SLICE_0087_EXTERNAL_CODE_REVIEW_RECONCILIATION_2026-10-16.md`, GitHub issue [#355](https://github.com/StradaDelSole/HullQ/issues/355): confirmed single-worker API event-loop blocking on 0083 async import with sync parsing/DB, unproven actual ZIP/decompression memory bound, absent deployed scheduler/email provider and unfinished trusted-proxy/client-IP, connection/timeouts, concurrency and onboarding proof. **Before any real external broker upload/pilot**, separately verify/close applicable runtime, operational, rights and Production Readiness/Launch Pack STOP/GO; do not infer that every CR rating or exploit has been independently proven. The Owner-selected **0088 eight-format portable export remains READY** on synthetic data and is not replaced by the external reviewer’s proposed bundled runtime-hardening 0088; its contract now explicitly prohibits repeating event-loop-blocking serializer work and requires real concurrent bounded-output proof. The entire dated Boats Group/BoatWizard competitive benchmark is tracked in `docs/governance/BOATS_GROUP_COMPETITIVE_CAPABILITY_REGISTER_2026-10-16.md`, issue [#356](https://github.com/StradaDelSole/HullQ/issues/356): each external feature explicitly reconciled as implemented/partial/gap and ADOPT/CONDITIONAL/REJECT-AS-IS with trigger and future standalone testable deliverable. Highest-leverage accepted gaps remain `REQ-BROKER-022` export (0088) and `REQ-BROKER-028` periodic honest zero-lead reporting before paid/broad launch; listing optimization, verified broker profile, owner-optional FSBO referral, lead/CRM delivery, anonymous demand, comparable sales/market analytics, broker-site feed, electronic contracts, call/SMS and finance are **later separate scoped choices**, source rights and privacy/regulatory gated. No blanket immediate implementation or illicit YachtWorld feed permission. Accepted Search count stays 9, Production Readiness IN_PROGRESS, Launch Pack NOT_STARTED, no 0089 preselected and **no new Owner START gate** introduced beyond the normal reviewed readiness merge.

After the 2026-09-14 pivot, any slice touching listing/supply, seller identity/verification, representation conflict, referral, marketplace monetization or Search must reconcile against the owner-direct product direction/spec and the mixed-supply execution reconciliation. After the 2026-09-26 execution amendment, relevant reassessment/readiness must also reconcile against `docs/BROKER_LAUNCH_EXECUTION_FOCUS_2026-09-26.md`.

> **Post-0086 Owner-selected SLICE-0087 (2026-10-15):** After the Owner confirmed local `FINISH_SLICE.bat 0086` and examined the no-gain Ponytail experiment, the Owner expressly selected the next bounded qualified technical Buyer Search bundle: **Beam (overall width) min/max/range** plus **Hull Material** with mirrored current actual-boat publisher claim editing and private illustrative Broker Search-fit. This follows the Owner's remaining technical Search priority after 0086 first-level hull/cockpit/deck. Public material tokens are initially limited to exact, meaning-preserving v0.5/v0.6 design-to-actual mappings GRP_FIBERGLASS/STEEL/ALUMINUM/WOOD; other existing concrete claim vocabulary is not automatically a public Search value. Two new public criteria can increase accepted count **7 → 9 only after actual Owner-accepted implementation and separate formal closure**. Full source/evidence/launch-gate comparison: `docs/POST_SLICE_0086_BEAM_HULL_MATERIAL_REASSESSMENT_2026-10-15.md`. Readiness draft: `docs/slices/SLICE-0087-qualified-beam-hull-material-search.md`. **Until independently exact-HEAD reviewed, CI/manufacturer verified and merged, 0087 is NOT STARTABLE**. Search work does not close Production Readiness/first real-listing exposure, broker export/report, owner-direct/public safety or any other MVP obligation. No 0088 product direction automatically follows.

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
