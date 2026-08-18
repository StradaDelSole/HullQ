# HullQ — External LLM Review Brief

**Purpose:** Give an independent LLM enough context to form an initial second opinion on HullQ without requiring access to the full repository and without priming it toward the project's current conclusions.

**Review status:** Early concept / specification / data-foundation stage. This brief describes the intended product and current working architecture; it does not claim that product-market fit, legal access to marketplaces, data acquisition economics, or monetization have been proven.

---

## 1. Concept in one sentence

**HullQ is a technical sailboat discovery engine and current-market finder:** a user describes the kind of sailboat they want by actual design characteristics, HullQ identifies matching boat designs, and then searches external marketplaces for examples of those designs currently for sale.

Tagline: **Find boats by what they are.**

HullQ is intended to be a search layer above existing boat markets, not another marketplace.

---

## 2. User problem and proposed solution

Most used-boat marketplaces are optimized for users who already know a manufacturer/model or who can work with relatively shallow listing filters. HullQ reverses that workflow.

Proposed flow:

```text
USER REQUIREMENTS
length / draft / displacement / hull / keel / rudder / skeg /
construction / rig / ratios / year / etc.
        ↓
HULLQ DESIGN DATABASE
independent sailboat-design dataset
        ↓
MATCHING DESIGNS / MODELS
        ↓
LIVE / ON-REQUEST MARKET SEARCH
external marketplace adapters
        ↓
NORMALIZE + DEDUPLICATE
        ↓
CURRENT BOATS FOR SALE
        ↓
COMPARE / SAVE / ALERT
```

Example use case: instead of searching directly for a known model, a buyer might ask for a 9–12 m monohull, moderate/heavy displacement, shallow enough draft for their needs, skeg-hung or keel-hung rudder, particular construction material, and specified ratio ranges. HullQ would first identify designs that meet those requirements and only then look for those models on the current market.

The central value proposition is:

> Find the right boat even if you do not know its name yet.

---

## 3. Product boundaries

HullQ includes from the beginning:

- monohulls
- catamarans
- trimarans

Multihulls are intended to be first-class data objects rather than a later add-on.

The MVP is deliberately narrow. A feature belongs early only if it strengthens this chain:

```text
FIND DESIGN → FIND BOAT FOR SALE → COMPARE / SAVE → ALERT
```

### MVP currently includes

1. Independent `BoatDesign` database
2. Technical design search
3. Curated hull / keel / rudder / skeg taxonomy
4. Monohull, catamaran and trimaran support
5. Matching design/model results
6. Side-by-side comparison
7. Current-market search
8. Accounts/login
9. Saved searches
10. Favorites
11. Alerts
12. Short-lived market cache
13. Basic source-health monitoring
14. Monetization hooks

### Explicitly out of scope for the MVP

- social/community features
- comments or owner reviews
- forums
- AI boat advisor
- route planning
- weather
- maintenance logs
- generic boat-ownership tools
- financing calculator
- insurance comparison

The intent is to avoid becoming a generic boating super-app.

---

## 4. Why the design database matters

The difficult query is performed against HullQ's own technical design database rather than against marketplace listings.

The planned canonical design data includes, where evidence exists:

### Identity

- manufacturer / brand
- model
- variant
- builder
- designer
- first built / last built
- number built

### Dimensions

- LOA
- LWL
- beam
- minimum / maximum draft
- displacement
- ballast
- sail area

### Configuration

- hull configuration
- hull count
- keel type / subtype
- rudder type / count
- skeg type
- rig type

### Construction

- hull material
- construction method

### Secondary cruising data

- engine data
- fuel and water capacity
- headroom
- bridgedeck clearance where relevant

Canonical physical storage is intended to use SI units where practical; the UI can convert units.

A key modelling decision is that **keel, rudder and skeg are independent dimensions**. HullQ should not inherit legacy combined labels such as “fin with rudder on skeg” as a single search field.

---

## 5. Derived ratios

HullQ intends to calculate common sailboat ratios from primary measurements rather than copying derived values where the base inputs are available.

Currently named ratios are:

- Sail Area / Displacement
- Ballast / Displacement
- Displacement / Length
- Comfort Ratio
- Capsize Screening Formula
- Hull Speed

OQ-001 now has a decision-ready draft defining formulas, input-basis semantics, units, rounding, result statuses and multihull applicability; it remains non-normative until explicit acceptance. The proposed bundle is versioned and backed by golden fixtures.

No generic opaque “Bluewater Score” is currently planned.

---

## 6. Independent-data strategy

The current preferred strategy is to build HullQ's own production dataset from independent/open/primary sources rather than depend on another commercial sailboat database.

Preferred source hierarchy:

1. Manufacturer / shipyard
2. Original manufacturer brochure
3. Owner's manual / technical manual
4. Designer / naval architect
5. Class association
6. Owners' association
7. Museum / recognized archive
8. High-quality specialist documentation
9. Secondary sources when necessary

Open structured sources may be used when their licenses permit commercial reuse.

Core rule:

> **No production value without provenance.**

AI may assist discovery, extraction, normalization and validation, but must not fill gaps from memory or probability.

Permitted data states include:

- verified
- partial
- unknown / null
- conflict
- needs_review

Input identity is kept distinct from verified identity. If an initial research seed says a boat was first built in 1986 but a stronger source says 1987, HullQ should retain the discrepancy rather than silently overwrite its history.

The planned provenance model supports evidence at field level, including source, confidence, source/raw value and normalized value.

---

## 7. Existing Sailboatdata scrape

A Sailboatdata scrape exists from the prototype phase. It was originally created because its search/filter workflow was considered insufficient.

The current project rule is:

```text
REFERENCE / PROTOTYPE ONLY
NOT PRODUCTION DATA
```

It may be useful for:

- discovering possible fields
- identifying edge cases
- taxonomy development
- UI/search prototyping
- possibly generating research-target identities, subject to legal review

It must not become an invisible fallback for production technical values. The raw scrape is to remain immutable.

This clean separation is important because the project has unresolved legal/licensing considerations around scraped database content and website terms.

---

## 8. Research pipeline and scaling thesis

The intended pipeline is:

```text
research queue
→ identity resolution
→ source discovery
→ source ranking
→ extraction
→ normalization
→ taxonomy mapping
→ derived calculations
→ validation
→ conflict detection
→ production record OR review queue
```

The minimal canonical research seed is intentionally only:

```csv
manufacturer,model,first_built
```

Operational metadata belongs in a separate `ResearchJob` object.

Before large-scale ingestion, the plan is to research a deliberately mixed set of **50–100 boat designs** and measure:

- identity-resolution success
- primary-source coverage
- field completeness
- conflict rate
- keel/rudder/skeg manual-review rate
- research time/cost per model
- proportion reaching verified / partial / needs_review / conflict

The 50–100 set is **only a research-pipeline benchmark**. If the benchmark gate passes, the project intends to move directly into broad ingestion: first thousands of canonical identities, then progressively toward SailboatData-like breadth (directionally 5,000–10,000+ where source coverage supports it), while verification depth remains progressive.

The target metric is both broad unknown-model discovery coverage and **coverage of real boats appearing on the used market**, not a vanity count of perfect records.

Unknown models observed on the market can enter an enrichment queue, so the dataset becomes progressively aligned with actual market demand.

---

## 9. Market-search architecture

The preferred approach is **live/on-request market search**, not a daily full mirror of external marketplaces.

The logic is:

1. HullQ resolves a technical query into a set of matching `BoatDesign` records.
2. Market adapters query external platforms for the corresponding make/model/generation combinations.
3. Results are mapped into one canonical listing format.
4. Listings are normalized and deduplicated.
5. Short-lived, source-dependent caching avoids unnecessary repeated requests.

Each marketplace should sit behind an isolated adapter, for example:

```text
market/
  boat24
  yachtworld
  scanboat
  theyachtmarket
  ...
```

No particular marketplace integration is considered guaranteed. Before an adapter is built, its permitted API/feed/partner/access method and terms are supposed to be checked.

A major unresolved issue is robust cross-platform deduplication of the same physical boat advertised in multiple places.

---

## 10. Saved searches and alerts

Accounts are considered part of the core use case rather than optional scope creep.

Expected functions:

- saved technical searches
- favorites
- alert settings

The intended alert differentiator is not only:

> Notify me when a Hallberg-Rassy 352 is listed.

It is also:

> Notify me when **any boat design matching my technical criteria** appears for sale.

The background system would resolve saved technical criteria to matching designs, group overlapping model lookups, query required market sources and notify only on genuinely new matches.

Alert cadence and exact cache/freshness rules are not yet finalized.

---

## 11. Current technical direction

The current architecture separates the mostly static design-data domain from current-market retrieval.

Logical components:

```text
Frontend / Search UI
        ↓
HullQ Application/API Boundary
   ↙                         ↘
Design Domain             User / Monitoring Domain
BoatModel / BoatDesign    Search / SavedQuery / Monitor
Options / ResolvedConfig  Alert / SubscriptionEntitlement
   ↓
Technical Query Engine
   ↓
Market Search Orchestrator
   ↓
Permitted API/feed/deep-link/adapter paths
   ↓
Normalize + identity match
   ↓
Source-permitted cache/history
```

Separately:

```text
Research Queue
→ Independent Research Pipeline
→ Validation / Conflict Review
→ BoatDesign DB
```

Strapi was an earlier pragmatic backend candidate, but no backend framework is accepted; OQ-011 and OQ-012 intentionally keep application and persistence choices open.

The final frontend framework has not yet been chosen. An existing Tabulator/HTML prototype was useful for testing but generated too many filters directly from raw fields; the intended production UX uses curated filters against the canonical schema.

---

## 12. Business and maintenance thesis

HullQ is intended to avoid the operational burden of a two-sided marketplace.

It does **not** plan to own:

- seller acquisition
- listing creation workflows
- buyer/seller messaging
- payments
- contracts
- dispute resolution
- marketplace moderation

The thesis is that sailboat design data changes slowly, while current listing data can remain at its original source and be queried when needed.

The desired operational model is therefore relatively lean and exception-driven once the independent dataset and source adapters are working.

---

## 13. Monetization hypotheses

No monetization model is considered validated yet.

Current possibilities include:

### Marine-industry advertising

Potential categories include yacht insurance, surveyors, riggers, sailmakers, yacht transport, marine electronics, energy systems, watermakers, communications, marinas, brokers and financing providers.

The preference is restrained, domain-relevant advertising rather than a generic ad-heavy portal.

### Affiliate / referral / lead generation

Possible structures include affiliate links, referral fees, lead generation and commercial partnerships with brokers or platforms.

The project explicitly does **not** assume that major marketplaces offer usable public affiliate programs. This has to be verified source by source.

Monetization is therefore an open business question rather than a proven part of the thesis.

---

## 14. Legal / dependency issues already recognized

The project has deliberately identified rather than hidden the following risks:

- rights and terms around scraped database content
- marketplace terms and automated access
- possible database-right / contract / unfair-competition questions
- source licensing and provenance
- dependence on external marketplace access methods

The current baseline is to build an independently sourced production dataset and obtain targeted Austrian/EU legal advice before any commercial use of scraped Sailboatdata values.

This brief does not claim a final legal conclusion.

---

## 15. Open decisions

The following remain unresolved and should not be treated as settled facts:

1. OQ-001 — exact derived-ratio formulas and versioned methodology
3. OQ-002 — taxonomy refinements after benchmark evidence
4. OQ-005 — cross-platform physical-listing deduplication
5. OQ-006 — alert cadence and source-specific freshness/cache policy
6. OQ-008 — final frontend technology
7. OQ-009 — exact three-state/unknown search semantics
8. OQ-010 — Python/research toolchain
9. OQ-011/OQ-012 — application/backend and persistence/search technology
10. OQ-013 — source-by-source market access
11. OQ-016 — final pricing/entitlement defaults
12. OQ-017 — historical market-observation / price-intelligence persistence and lifecycle semantics

Already decided and **not open**: model/generation/variant/option identity (OQ-003), field-level provenance persistence (OQ-004), and source-rights/licensing metadata/clearance (OQ-007). Search Architecture + SEO as first-class product architecture is accepted under ADR-0007; exact public-surface details remain OQ-018.

---

## 16. Current roadmap

### Foundation now

- freeze OQ-001 ratio methodology
- choose OQ-010 research/data toolchain
- bootstrap real single-repo CI/tooling only after those decisions

### Research-pipeline benchmark

- research 50–100 deliberately difficult designs as a **pipeline benchmark only**
- measure throughput, cost, automated acceptance, review rate, conflict rate, identity ambiguity and HullQ-critical-field completeness
- do **not** treat this corpus as a product/MVP database

### Broad design-universe ingestion

- scale quickly toward thousands of canonical sailboat identities after the benchmark gate
- directionally target SailboatData-like breadth (potentially 5,000–10,000+ identities) with progressive/sparse verification depth
- use cleared open data for common bootstrap fields where useful and concentrate independent research on HullQ-critical fields, conflicts, generations/options and gaps

### Technical query engine + compare

Build unknown-model discovery only once the database is broad enough that missing-universe bias does not invalidate the experience.

### Market-access validation + one permitted end-to-end source

Prove the complete loop without assuming a specific marketplace access method:

```text
technical search
→ matching designs
→ permitted market lookup/deep-link/feed/API path
→ normalized listings
→ current boats for sale
```

### SavedQuery / Monitor / Alert / subscriptions

Add persistent technical monitoring, owner-watcher retention, Free/Plus/Pro entitlements, and later price intelligence only where OQ-017/source rights permit history.

---


## Owner-watcher retention hypothesis

A prior simplistic assumption that a sailboat-search user disappears after purchasing a boat should **not** be treated as established. HullQ's founder hypothesis is that many sailors continue watching the used-boat market while already owning a boat: for curiosity, emotional engagement, upgrades and rare-opportunity discovery. HullQ therefore targets both active buyers and long-lived owner-watchers/opportunity hunters. This hypothesis is not yet empirically validated and should be tested, but reviewers should not infer low retention directly from low individual boat-purchase frequency.

## Freemium / subscription hypothesis

The preferred initial commercial direction is to keep core technical discovery open and monetize persistent monitoring:

- **HullQ Free — Search everything. Save 5 searches. Monitor 2.**
- **HullQ Plus — Monitor 10 technical searches across supported markets.**
- **HullQ Pro — Advanced monitoring, faster alerts, price tracking, larger limits.**

Exact prices and limits are hypotheses, not fixed commitments. Reviewers should assess whether this monitoring-based freemium model can work for active buyers *and* owner-watchers, and what evidence would validate/refute it.

## 17. What has and has not been validated

### Already defined at project level

- product problem and intended workflow
- narrow MVP boundary
- independent-data/provenance principle
- initial technical taxonomy and schemas
- research-pilot approach
- high-level market-adapter architecture
- account/saved-search/alert concept

### Not yet demonstrated

- actual user demand or willingness to pay
- customer acquisition economics
- size and behavior of the reachable market
- sustained independent-data research cost per model
- achievable primary-source completeness at scale
- legal/commercial access to enough marketplace data
- reliability and maintenance cost of market adapters
- effectiveness of cross-platform deduplication
- monetization performance
- owner-watcher retention, monitor survival, subscription conversion and alert usage
- product-market fit

An external review should therefore assess the **idea and execution thesis**, not mistake the current documentation quality for evidence that the business itself is validated.

---

## 18. What an independent reviewer should challenge

A useful second opinion should actively test, among other things:

- Is the underlying search problem important and frequent enough?
- Is “I know the characteristics but not the model” a real buying workflow or mainly an enthusiast/developer intuition?
- Is technical-design search sufficiently differentiated from existing boat databases, brokers, forums and marketplaces?
- Is the jump from matching designs to finding current listings genuinely valuable?
- Are saved technical alerts a strong retention loop?
- Can a sufficiently complete and trustworthy independent design database be built at acceptable cost?
- Is field-level provenance a competitive asset or unnecessary complexity at MVP stage?
- How damaging is dependence on third-party marketplace access?
- Can live meta-search work legally, technically and economically across enough sources?
- Is the product commercially useful without marketplace partnerships?
- Who is most likely to pay: buyers, brokers, advertisers, platforms, marine suppliers, or nobody directly?
- Is the proposed MVP still too broad?
- Which feature should be the first proof of value?
- What is the strongest alternative product shape if the current model is wrong?
- What could make this a small but durable niche business versus a hobby project with weak economics?
- What evidence would most efficiently falsify the concept before substantial development?

The reviewer should feel free to reject the current thesis if the evidence or reasoning points that way.
