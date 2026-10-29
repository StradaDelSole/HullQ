# HullQ — Buyer Demand → Broker Supply & Qualified Enquiry: Implementation Obligation Register

**Status:** OWNER-ACCEPTED PRODUCT DIRECTION / TECHNICAL IMPLEMENTATION PENDING (2026-10-29).  
**Scope:** first-party buyer Saved Searches, truthful newly matching listing alerts, buyer-controlled contact, privacy-bounded broker demand and pilot measurement.  
**Execution:** **FUTURE CAPABILITY TRACKER ONLY**, not `SLICE-0096` readiness, not authority to start coding or a live-data pilot.  
**Tracking:** [owner-accepted umbrella #406](https://github.com/StradaDelSole/HullQ/issues/406), linked implementable tracks #407–#411.  
**Privacy boundary:** This public product register contains **no private investor, acquisition, exit, competitive targeting or valuation strategy**.

## Buyer and broker jobs

1. A buyer can save one supported current technical Sail or Power Search with the actual semantic criteria version, view/edit/disable/delete it and explicitly opt in for new-match alerts.
2. HullQ can **reliably and honestly** notify when newly published or updated public listings **newly satisfy** the saved technical requirements. A partially scanned collection never becomes an asserted complete no-match; stale/suppressed/withdrawn listings may never be promoted to eligible current match.
3. A buyer's private watch is **not** a broker contact Lead. Only a distinct deliberate enquiry creates the previously accepted immutable authorized Lead, optionally with first-party consented source metadata.
4. Once actual valid traffic reaches a defensible privacy volume threshold, an authorized broker may inspect **coarse, non-reconstructable first-party demand** rather than any individual buyer profile or false market-wide representativeness.
5. An operator can compare a bounded authorized pilot cohort on actual source-backed outcomes: currently eligible listings, broker work, truthful match/result states, alerts, opt-outs and broker-confirmed qualified enquiries. Never fabricate metrics from absent provider, tracking or real data.

This product direction is complementary to the two accepted coequal pillars: effective buyer matching and time-saving professional broker tools. It does not change fair organic ordering, charge per normal Lead or assume new entitlement/pricing policy.

## Existing implementation — preserve / reuse

| Obligation or implementation | Source truth as of 2026-10-29 | Classification |
|---|---|---|
| Technical Sail / Power MUST conjunction + source-qualified truth | accepted SLICE-0051–0087 Sail, SLICE-0091–0094 Sail/Power; immutable D29/current publisher/FieldResolution | DECIDED_AND_IMPLEMENTED in existing specific criteria |
| Scalable public candidate traversal | SLICE-0096 source-reviewed READY contract, **implementation not accepted** | DECIDED_NOT_YET_IMPLEMENTED — ACTIVE/OWNER-SELECTED `0096`, do not expand |
| Explicit buyer→broker Lead | SLICE-0070 durable per-listing idempotent Lead, 0071 broker operations/outbox | DECIDED_AND_IMPLEMENTED in bounded scope; no Watch-generated Lead |
| Lead funnel + truthful performance | SLICE-0075 and 0089 | DECIDED_AND_IMPLEMENTED in accepted scope; not first-party buyer Saved Search/alert delivery |
| BuyerRequirement account continuity | `MVP-BUY-005` | DECIDED_NOT_YET_IMPLEMENTED; owning future #407 |
| Saved Search/Monitor/Alert | `MVP-BUY-007`; existing BG-25 | DECIDED_NOT_YET_IMPLEMENTED; owning future #407 |
| Price change alert with qualified price history | `MVP-BUY-008` | EXPLICITLY_DEFERRED to separate acceptance; #407 must not pretend it already works |
| Buyer contact verification & anti-abuse | `MVP-BUY-009/010` | DECIDED_NOT_YET_IMPLEMENTED; admission depends on future review |
| Notification preferences, transaction/optional classification, delivery suppression | `MVP-COMMS-003/004/005`; broker outbox is **not** a buyer provider | DECIDED_NOT_YET_IMPLEMENTED; #407 |
| Broker Search exclusion and aggregate demand | `MVP-BROKER-012`, `REQ-BROKER-025/029`, BG-08; volume marker `SUFFICIENT_SEARCH_VOLUME_FOR_BROKER_INSIGHTS_STATUS=NOT_REACHED` | DECIDED_NOT_YET_IMPLEMENTED; gated future #408 |
| Optional Saved Search → explicit Lead attribution | existing provenance/UTM/discovery token from SLICE-0071 | DECIDED_NOT_YET_IMPLEMENTED for this new source; future #409 |
| Source-backed cohort/retention and low-friction authorized pilot | broker workspace/register and runtime safety #355 | DECIDED_NOT_YET_IMPLEMENTED; future #410/#411 and pre-pilot gate |

**Relevant accepted records:** `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md`, `docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`, `docs/governance/BOATS_GROUP_COMPETITIVE_CAPABILITY_REGISTER_2026-10-16.md`, `docs/HULLQ_OWNER_DECISION_BROKER_PRODUCTIVITY_EXCELLENCE_2026-10-29.md`, `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`, `docs/governance/PRODUCTION_READINESS_GATE.md`, `docs/engineering/AI_SLICE_WORKFLOW.md`, `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`, `specs/NATIVE_TECHNICAL_SEARCH_BOUNDED_PAGING_CONTRACT.v0.1.md`.  
**Source code checked:** `src/hullq/application/{search_read,power_search_read,buyer_lead_creation,lead_notification_delivery}.py`, `src/hullq/domain/buyer_lead.py`, `src/hullq/persistence/inventory_search.py`, `specs/MARKETPLACE_BUYER_LEAD_CREATION_CONTRACT.v0.1.md`, `specs/BROKER_LEAD_OPERATIONS_NOTIFICATION_CONTRACT.v0.1.md`. Repo contains no accepted buyer SavedSearch/notification delivery engine.

## Required bounded implementation tracks and observable acceptance

| ID | Issue | Necessary result | Gate / sequence | Status |
|---|---|---|---|---|
| DMD-01 | [#407](https://github.com/StradaDelSole/HullQ/issues/407) | Saved canonical Sail/Power Search, buyer ownership, opt-in, actual newly matching notifications with safe deduped delivery/disable | After 0096 + buyer account/comms decisions, provider readiness; no live mail before gates | PENDING |
| DMD-02 | [#408](https://github.com/StradaDelSole/HullQ/issues/408) | Conservatively privacy-protected broker aggregate qualified demand / Search exclusion explanation | Real sufficient first-party traffic, consent/legal & threshold proof; `REQ-BROKER-025/029` | PENDING / VOLUME-GATED |
| DMD-03 | [#409](https://github.com/StradaDelSole/HullQ/issues/409) | Separate explicitly buyer-approved contact with truthful Saved Search / alert source attribution, no silent transfer of watch profiles | After actual #407 product and existing Lead correctness; privacy/verification gates | PENDING |
| DMD-04 | [#410](https://github.com/StradaDelSole/HullQ/issues/410) | Minimal first-party non-vanity buyer/broker engagement and liquidity scorecard | Data/purpose definitions, bot/privacy controls, actual source and honest missingness | PENDING |
| DMD-05 | [#411](https://github.com/StradaDelSole/HullQ/issues/411) | Bounded authorized broker cohort onboarding/operations without raw test seeding | #355 plus Production Readiness + staged Launch Pack before external real data/pilot | PENDING / PRE-PILOT |
| DMD-06 | [#413](https://github.com/StradaDelSole/HullQ/issues/413) | Small set of rights-safe, manually curated technical SEO/entry pages linking to actual supported canonical Sail/Power Search and optionally Saved Search | Existing `MVP-SEO-001/002`, `MVP-I18N-005` and noindex OQ-018 decision; do not expose arbitrary facet combinatorics | PENDING / PRE-ORGANIC-LAUNCH |
| DMD-07 | [#414](https://github.com/StradaDelSole/HullQ/issues/414) | Honest reproducible **NativeListing buyer-job** correctness/usability benchmark and, only if permitted, separate fair third-party comparison evidence | Retain locked `specs/SEARCH_BENCHMARK.v0.1.md`; independently verified rights/methodology before any comparative public claim | PENDING / VALIDATION |

## Additional product-paper reconciliation (2026-10-29)

An additional source-based review of buyer acquisition, pilot and partner product needs against `docs/HULLQ_CUSTOMER_ACQUISITION_AND_DIFFERENTIATION_2026-10-21.md`, OQ-018 SEO decisions and the MVP/Professional Broker registers identified **two new separately deliverable product gaps**, tracked as DMD-06 and DMD-07. This public register contains no confidential acquisition thesis, partner contact shortlist, investor targets, negotiation terms, or private strategy paper contents.

**Already tracked; no redundant feature:** #411 and #355 own authorized real broker onboarding and pilot restrictions; #400 owns broker time saving/feeds and lead performance; #358 is the listing optimizer; #359 is legally contracted partner syndication/feed acknowledgements; #356 assesses other vendor capabilities. #410 also has to establish **measured economic efficiency** of the pilot (cost per truly active broker and broker-confirmed qualified enquiry) instead of equating traffic with positive unit economics; define denominators, allocation and actual running/provider cost. #407 must make it practical to save an unmatched or insufficient-result Search while clearly distinguishing partial evaluation from a completed no-match. First-party attribution existing under 0071 never implies tracking or sharing rights without consent.

**Non-technical tasks:** human outreach/interviews, private contact records, offers/negotiation, PR/editorial creation, legal advice and simple synthetic demonstration materials should not be forced into the application repo. Broker and partner contact identities are kept outside this public document and new user-facing features remain Owner-approved bounded future work.

### Mandatory DMD-01 failure model

- **Identity/source:** A saved Search belongs to exactly one authorized buyer, has stable versioned technical criteria/category/locale and cannot be modified or read across accounts. Query changes cannot continue a stale watch's previous match watermark as if identical.
- **Match consistency:** same current qualified Sail/Power D29 evidence and conjunction as current public result truth; current public recheck before sending; no old withdrawn listing resurrected by notification; no cross-Organization publisher facts, no non-commercial ordering changes.
- **Budget/completion:** a bounded Search `PARTIAL` cannot mean no match or end of work; a restartable watcher must exhaust correctly within bounded steps and explicitly represent timeout/dependency failure vs true no-match.
- **Durability/idempotency:** lease/fence or equivalent safe concurrency; immutable delivery identity per buyer-query-revision/listing-qualification transition; no duplicate sending merely due to retries, cursor shifts, mail-provider timeout, worker restart or concurrent edits. Distinguish provider accepted/unknown/failed; no false delivered state.
- **Consent/abuse:** real lawful alert opt-in, verified destination before send, unsubscribe and suppression (plus provider bounce/complaint handling), buyer erasure/retention, bounded/watch quotas, alert frequency control and per-user failure isolation; no invisible third-party marketing or sale of personal criteria.
- **Proof:** PG18 + real API + built Astro five-locale positive/negative, fake provider failures, current data edits/withdrawn races, sparse/empty pages, duplicate schedule and false-complete regression.

## Operational performance targets and limits

Hypothetical early learning cohort **8–12 active professional brokers and 150–300 current rights-valid listings**; **not** a release gate, promised result, market projection or verified number. Prioritize qualified enquiries per active broker, return buyer activity (only if legitimate to measure), matched-vs-insufficient results, time to publish/update, buyer opt-in and unsubscribe rates, stale/withdrawn correctness and infrastructure cost. Do not claim cross-market demand, broad cohort representativeness or a transaction sale merely from an email open/click.

**Explicit non-goals:** automatic buyer lead resale, buyer-detail alerts to brokers, unlicensed syndication, scrape-based inventories, automatically paid match boosts, any disclosure of an individual account's saved technical profiles without separate explicit contact, and developing all five tracks as a single oversized slice.

## Sequencing / governance to ensure future delivery

1. **Current active work remains SLICE-0096 only.** No modification of its branch, scope, implementation prompt, `PROJECT_STATE_QUEUE_SLICE`, accepted-criteria count 11 or existing production gate.
2. This docs-only planning artifact may be prepared/reviewed on a **separate draft PR** while 0096 is active. **Do not merge to `main` while Claude implements 0096**; it must be rebased/reconciled on actual future main after exact-head Owner acceptance and formal slice closure.
3. The next post-0096 reassessment must enumerate **DMD-01–05** and compare buyer usability M1a, #355 pre-pilot safety, #366 joint Sail/Power parity, #400 broker productivity and overall MVP register. This owner direction makes **DMD-01 a mandatory tracked product obligation** but does **not** silently predetermine SLICE-0097 or justify bypassing a more urgent launch gate.
4. Each selected coherent technical slice follows `AI_SLICE_WORKFLOW.md`: project-master source-based readiness and merge → Owner local START → Claude code only → project-master independent exact-HEAD implementation review/amendments, remote CI and Owner acceptance → project-master merge/closure → Owner local FINISH. No fake IMPLEMENTED status before running actual proof.
5. Update this register and owning preexisting `MVP-*` / `REQ-BROKER-*` statuses in the **accepted implementation closure**, not when creating an issue. This owner-accepted umbrella #406 remains OPEN while its concrete obligations remain unimplemented or unambiguously Owner-deferred.

**Protection:** `#355` pre-real-data, `#366` joint Sail+Power release, `#372` specialist parity and Launch Pack `NOT_STARTED` are unchanged; no live provider procurement, real broker pilot, public Launch authorization or marketing campaign is implied.
