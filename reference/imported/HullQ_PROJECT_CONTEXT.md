# HullQ — Project Context

**Tagline:** Find boats by what they are.

## 1. Product identity

**Name:** HullQ  
**Meaning:** Hull + Q for Query; short, technical, memorable, with an incidental phonetic association to “Hulk”/strength.  
**Positioning:** Sailboat search engine and market finder, not a marketplace and not a generic yacht portal.

### One-sentence product definition

HullQ lets users discover sailboat designs by their actual technical characteristics — even if they do not know the model name — and then searches the current market for matching boats for sale.

### Core user problem

Existing boat marketplaces mainly assume that the buyer already knows a make/model or provide only shallow marketplace-specific filters. HullQ reverses that workflow:

1. Define the boat by characteristics.
2. Find matching designs/models.
3. Search current sales platforms for examples of those models that are actually for sale.
4. Compare, save, and monitor searches.

**Core value proposition:** Find the right boat even if you do not know its name yet.

---

## 2. Core product flow

```text
USER REQUIREMENTS
length / draft / displacement / keel / rudder / skeg /
construction / rig / ratios / year / etc.
        ↓
HULLQ DESIGN DATABASE
independently built sailboat-design dataset
        ↓
MATCHING MODELS
        ↓
LIVE MARKET SEARCH
Boat24 / YachtWorld / Scanboat / TheYachtMarket / etc.
        ↓
NORMALIZE + DEDUPLICATE
        ↓
CURRENT BOATS FOR SALE
        ↓
COMPARE / SAVE / ALERT
```

HullQ should not become a copy of Sailboatdata and should not become another listing marketplace.

---

## 3. Vessel scope

HullQ must include from day one:

- Monohulls
- Catamarans
- Trimarans

Multihulls are first-class objects, not a later extension.

The data model must not encode multiple independent characteristics into one legacy `Hull Type` field.

---

## 4. Search taxonomy

### Hull configuration

Canonical starting values:

- monohull
- catamaran
- trimaran
- other
- unknown

Potential multihull-specific data:

- hull_count
- beam_overall
- bridgedeck_clearance
- rudder_count
- daggerboard_count
- centerboard_count

### Keel type

Keel must be independent from rudder/skeg.

Starting taxonomy:

- full
- modified_full
- long_fin
- fin
- wing
- bulb
- twin
- bilge
- centerboard
- daggerboard
- swing
- lifting
- shoal
- other
- unknown

The taxonomy should be refined against real source data.

### Rudder type

Starting taxonomy:

- keel_hung
- skeg_hung
- partial_skeg
- spade
- transom_hung
- twin
- other
- unknown

### Skeg

Skeg gets its own field:

- full
- partial
- none
- unknown

This permits combinations such as:

```text
Hull: monohull
Keel: any
Rudder: skeg_hung OR keel_hung
Skeg: full OR partial
```

instead of relying on combined source strings such as `Fin with rudder on skeg`.

### Rig

Starting categories:

- masthead_sloop
- fractional_sloop
- cutter
- ketch
- yawl
- schooner
- cat_rig
- other
- unknown

Raw source wording may be retained separately.

### Construction

Searchable fields:

- hull_material
- construction_method

Likely material values:

- GRP / fiberglass
- aluminium
- steel
- wood
- wood_composite
- carbon
- other
- unknown

Avoid over-normalizing until real source data has been evaluated.

---

## 5. Important technical search fields

### Identity

- manufacturer / brand
- model
- variant
- builder
- designer
- first_built
- last_built
- number_built

### Dimensions

- LOA
- LWL
- beam
- draft_min
- draft_max
- displacement
- ballast
- sail_area

Canonical storage should use SI units where practical. UI can convert to Imperial.

### Construction/configuration

- hull_configuration
- keel_type
- keel_subtype
- rudder_type
- skeg_type
- rudder_count
- rig_type
- hull_material
- construction_method

### Cruising/engine information

Where reliably available:

- engine_make
- engine_model
- engine_type
- engine_power
- fuel_capacity
- water_capacity
- headroom

These are lower priority than the core design/search fields.

---

## 6. Derived ratios

HullQ should calculate ratios itself from primary values using one documented, versioned methodology:

- Sail Area / Displacement
- Ballast / Displacement
- Displacement / Length
- Comfort Ratio
- Capsize Screening Formula
- Hull Speed

Do not copy derived ratios when the base parameters are available.

Reasons:

1. Independent provenance
2. Uniform methodology
3. Easier correction/versioning
4. Less external-data dependence

Each formula should later have a formula version, unit assumptions, missing-data behavior and automated tests.

---

## 7. Independent dataset strategy

### Current preferred direction

Build HullQ's own independent production dataset rather than depending on a commercial Sailboatdata license.

AI can automate much of the source discovery, extraction, normalization, validation and provenance capture.

### Minimal research input

Each research target should initially contain only:

```text
manufacturer
model
first_built
```

Example:

```csv
manufacturer,model,first_built
Najad,Najad 34,1972
Hallberg-Rassy,Hallberg-Rassy 352,1978
Lagoon,Lagoon 380,1999
```

The first-built year is primarily an identity/disambiguation hint and must be independently verified.

### Identity rule

Input identity and verified identity remain distinguishable.

If the input says 1986 and an authoritative source says 1987:

- retain 1986 as research metadata
- store 1987 as verified production value
- record the discrepancy

---

## 8. Source hierarchy for independent research

Preferred order:

1. Manufacturer / shipyard
2. Original manufacturer brochure
3. Owner's manual / technical manual
4. Designer / naval architect
5. Class association
6. Owners' association
7. Museum / recognized archive
8. High-quality specialist documentation
9. Other secondary sources only when necessary

Open structured sources such as Wikidata may be used where their license permits commercial reuse.

**Rule: No production value without provenance.**

AI must not fill gaps from memory or probability.

Allowed states:

- verified value
- unknown / null
- conflict
- needs_review

---

## 9. Field-level provenance

Long-term preferred pattern:

```json
{
  "loa_m": {
    "value": 10.54,
    "source_id": "SRC_001",
    "confidence": "high"
  },
  "rudder_type": {
    "value": "skeg_hung",
    "source_id": "SRC_002",
    "confidence": "high",
    "evidence_type": "profile_drawing"
  }
}
```

A source record should capture:

- source_id
- title
- publisher/organization
- source_type
- URL or document identifier
- publication date if known
- accessed_at
- notes

This supports quality control, legal provenance, conflict resolution and later correction.

---

## 10. AI research pipeline

```text
research_queue
        ↓
identity resolution
        ↓
source discovery
        ↓
source ranking
        ↓
data extraction
        ↓
normalization
        ↓
taxonomy mapping
        ↓
derived calculations
        ↓
validation
        ↓
conflict detection
        ↓
production record OR review queue
```

### Hard AI rules

1. Never invent missing values.
2. Never silently resolve conflicting authoritative sources.
3. Use `unknown`/`null` when evidence is insufficient.
4. Store provenance.
5. Record confidence.
6. Separate source value from normalized value where necessary.
7. Flag uncertain keel/rudder/skeg classification aggressively.
8. Never use the old Sailboatdata scrape as an invisible fallback source.

### Validation examples

- LWL normally <= LOA
- ballast normally < displacement
- physical plausibility checks
- explicit units
- duplicate model/variant detection
- generation ambiguity detection
- multihull-specific consistency checks

---

## 11. Market-driven enrichment

Do not optimize for matching another database's total model count.

Optimize for:

**percentage of real sailboats currently on the used market that HullQ can identify and enrich.**

Example:

```text
Market listings observed: 18,420
Matched to BoatDesign:    17,617
Coverage:                  95.6%
```

### Enrichment loop

```text
market search
    ↓
unknown model detected
    ↓
enrichment queue
    ↓
independent AI research
    ↓
BoatDesign created
    ↓
future listings match automatically
```

Users may request missing models:

```text
Can't find your boat?
[Request this model]
```

Requests can be ranked by count.

---

## 12. Existing Sailboatdata scrape

Current prototype context:

- Sailboatdata was scraped because its search/filter workflow was considered insufficient.
- The scrape was still running when discussed.
- The uploaded test snapshot contained 4,250 records and was not the expected final ~9,000+ dataset.
- Raw records contain original fields plus automatically extracted `(Numeric)` variants.
- Some numeric extraction is semantically wrong, e.g. numbers extracted from topic URLs, related-boat labels, model strings or association names.
- Many null fields create unnecessary payload.

### Rule

Treat this as:

```text
REFERENCE / PROTOTYPE ONLY
NOT PRODUCTION DATA
```

Useful for:

- understanding possible fields
- edge cases
- taxonomy design
- UI/search testing
- potentially generating research-target identities, subject to legal review

Do not silently import its technical values into the independent production database.

Keep the raw scrape immutable. Cleaning/removing nulls happens only in derived/test copies.

---

## 13. Sailboatdata licensing/legal status — working project position

This is not legal advice. Re-check with an Austrian/EU IP/IT lawyer before commercial launch if scraped Sailboatdata content would be used.

Working conclusions from prior research:

- Individual factual specifications are not automatically protected merely because they are facts.
- EU law also provides a separate sui-generis database right for qualifying investment in obtaining/verifying/presenting data.
- Repeated systematic extraction of small portions can also be relevant.
- Normalizing copied data does not create independent provenance retroactively.
- Attribution alone does not replace permission.
- Real-time meta-search is not automatically safe simply because foreign data is not permanently copied.
- Sailboatdata's published terms restrict automated access and commercial reuse without permission/license.
- Sailboatdata publicly presents itself as US-based. Article 11 of the EU Database Directive creates a potentially important eligibility issue for non-EU database makers, but this should be professionally checked rather than assumed.

### Legal paths

#### A. License

If commercially attractive, negotiate a narrow factual-data license.

Desired rights:

- machine-readable access
- local storage
- commercial use
- normalization
- own taxonomy
- derived calculations
- filtering/comparison
- model landing pages
- market matching
- caching
- periodic updates
- advertising/referral/affiliate monetization

Prefer to exclude photos, drawings, brochures, editorial text, forums and other third-party copyrighted material.

Because startup cash is limited, preferred structure:

- no substantial upfront fee
- pilot/startup period
- deferred fixed fee
- revenue share
- small minimum + revenue share

#### B. Independent database

Current preferred route.

Build production values from independent/open/primary sources with provenance.

#### C. Targeted legal opinion

If needed, ask an Austrian IP/IT lawyer specifically about:

- US database maker
- Article 11 Database Directive
- Austrian §§ 76c/76d UrhG
- public factual data
- website terms
- scraping
- UWG/unfair competition
- clean-room strategy

---

## 14. Market search architecture

Preferred architecture: **live/on-request market search**, not a daily full mirror.

```text
HullQ filters
    ↓
matching BoatDesigns
    ↓
market adapters query matching make/model/generation
    ↓
normalize
    ↓
deduplicate
    ↓
display current market
```

The difficult search happens in HullQ's own technical design database. External sources only need to answer simpler make/model queries.

### Short-lived cache

Use a source-dependent cache, e.g. roughly 15–60 minutes, to avoid unnecessary repeat requests.

### Source adapters

Each marketplace is isolated behind its own adapter:

```text
market/
  boat24
  yachtworld
  scanboat
  theyachtmarket
  rightboat
  ...
```

All adapters return one canonical listing format.

Before implementing each adapter, verify the platform's permitted API/feed/partner/access method and terms.

---

## 15. Saved searches and alerts

Accounts are in scope from the beginning because they directly support the core use case and are technically cheap with a backend such as Strapi.

Core user functions:

- login/account
- saved searches
- favorites
- alert settings

### Major alert differentiator

Not merely:

> Notify me when a Corbin 35 is listed.

But:

> Notify me when **any design matching my technical criteria** appears on the market.

Background logic should resolve saved technical searches into relevant BoatDesigns, group identical model lookups, query only needed sources and notify on genuinely new matches.

---

## 16. Backend direction

Strapi is the preferred pragmatic backend.

Likely entities:

- User
- SavedSearch
- Favorite
- AlertSettings
- BoatDesign
- Manufacturer
- Builder
- Designer
- Source
- ResearchJob
- ResearchConflict
- MarketSearchCache
- SourcePlatform

Avoid overengineering before real usage requires it.

---

## 17. Frontend/Search UX

The first HTML prototype uses Tabulator and dynamically creates filters from raw JSON metadata.

Useful as a test, but not final UX.

### Final direction

Use curated filters based on the canonical taxonomy.

Primary filters:

- LOA / length
- year
- hull configuration
- keel
- rudder/skeg
- draft
- displacement
- material

Advanced sections:

- Dimensions
- Hull & Construction
- Keel / Rudder / Skeg
- Rig
- Ratios
- Engine / Tanks
- Designer / Builder

### Compare

Comparison is core. Users should select several designs and compare normalized values side by side.

### Presets

Potential transparent filter presets:

- Classic Offshore Cruiser
- Fast Offshore Cruiser
- Shallow Draft Cruiser
- Heavy Displacement
- Full/Long Keel
- Skeg Rudder
- Under 12 m

Avoid an opaque generic “Bluewater Score” unless a rigorous methodology is later justified.

---

## 18. Current HTML technical findings

Prototype behavior:

- automatic raw-field classification
- dynamically generated filters
- immediate filtering on each input/change
- Imperial/Metric toggle
- Tabulator results

Issues identified:

1. Too many filters from raw schema.
2. Invalid numeric columns from generic number extraction.
3. Every input triggers a full filter pass.
4. Per-row filtering repeatedly performs DOM lookups.
5. This is inefficient at ~9,000 records × many fields.
6. Unit switching rebuilds controls and can lose filter values.
7. Raw payload contains many redundant nulls.

Preferred pattern:

```text
filter UI event
      ↓
read active filters once
      ↓
build compact activeFilter object
      ↓
filter dataset against activeFilter
```

---

## 19. Data maintenance philosophy

### Boat design database

Mostly static.

Likely cadence:

- quarterly review/update
- continuous market-driven enrichment for unknown models
- corrections as needed

### Market

Live/on-request.

### Source health

Exception-based maintenance:

- last successful run
- error state
- result count
- latency
- schema/parse failures

Goal: normal days require no human intervention.

---

## 20. Monetization

### Advertising

Potentially relevant advertisers:

- yacht insurance
- surveyors
- riggers
- sailmakers
- yacht transport
- marine electronics
- solar/energy equipment
- watermakers
- communications
- marinas
- brokers
- financing providers

Keep ads restrained and non-spammy. Direct marine-industry advertising may eventually be more valuable than generic display ads.

### Affiliate/referral

Potentially useful but do **not** assume major marketplaces offer public affiliate programs. Verify source by source.

Possible models:

- affiliate links
- referral fees
- lead generation
- commercial partnerships
- broker/platform partnerships

Affiliate is a bonus until verified.

---

## 21. MVP scope

### In scope

1. Independent BoatDesign database
2. Technical search
3. Curated keel/rudder/skeg taxonomy
4. Monohull + catamaran + trimaran support
5. Model results
6. Compare
7. Current-market search
8. Accounts/login
9. Saved searches
10. Favorites
11. Alerts
12. Short-lived market cache
13. Basic source health monitoring
14. Monetization hooks

### Explicitly out of scope

- social features
- comments
- owner reviews
- forums
- AI boat advisor
- route planning
- weather
- maintenance logs
- generic boat ownership app
- financing calculator
- insurance comparison

These are separate products and must not dilute HullQ.

---

## 22. Scope guardrail

A feature belongs in early HullQ only if it directly strengthens:

```text
FIND DESIGN
    ↓
FIND BOAT FOR SALE
    ↓
COMPARE / SAVE
    ↓
ALERT
```

---

## 23. Business/maintenance thesis

HullQ is attractive because:

- technical design data is largely static
- marketplace data can remain at source
- no seller acquisition
- no listing creation workflow
- no buyer/seller messaging
- no payments
- no contract handling
- no dispute resolution
- no marketplace moderation

HullQ is a search layer above existing markets.

---

## 24. Brand

**HullQ**

Preferred tagline:

> **Find boats by what they are.**

Alternative explanatory line:

> Find the right boat — even if you don't know its name yet.

Brand character:

- short
- technical
- strong
- international
- not yacht-lifestyle cliché
- suitable for web/app/icon
- Q naturally implies Query
- incidental phonetic similarity to “Hulk”

The preferred matching domain was reported as available during naming. Domain ownership and trademark checks should still be completed before public launch.

---

## 25. Immediate next steps

### Data foundation

1. Freeze this project context.
2. Define `BoatDesign` schema v0.1.
3. Define keel/rudder/skeg taxonomy v0.1.
4. Define source/provenance schema.
5. Define ratio formulas and tests.
6. Extract research queue containing only:
   - manufacturer
   - model
   - first_built

### Research pilot

Start with 50–100 models.

Measure:

- identity-resolution success
- primary-source coverage
- field completeness
- conflict rate
- keel/rudder manual-review rate
- research time/cost per model

Then scale to 500 / 2,000+.

### Frontend

Replace raw auto-generated filters with curated filters based on canonical schema.

### Backend

Set up Strapi with users, saved searches, favorites, alerts and relevant data models.

### Market adapters

Implement one source first and prove:

```text
technical search
→ model set
→ live marketplace lookup
→ normalized current listings
```

Then add additional sources behind the same adapter interface.

### Legal

In parallel:

- optionally ask Sailboatdata about commercial licensing terms
- do not depend on a license for the independent-data route
- get targeted Austrian/EU IP advice before commercial use of scraped Sailboatdata values

---

## 26. Project principles

1. Independent data is an asset.
2. Provenance over completeness.
3. Unknown is better than invented.
4. Keel, rudder and skeg are independent dimensions.
5. Multihulls are first-class.
6. Ratios are calculated internally.
7. Optimize for real-market coverage, not raw model count.
8. Live market search beats unnecessary full-market mirroring.
9. Accounts/saved searches/alerts are core, not scope creep.
10. No unrelated boating super-app.
11. Keep source integrations modular.
12. Aim for exception-based maintenance.
13. Build the smallest complete chain from technical requirement to actual boat for sale.
