# Market Discoverability and Coverage Growth

## Purpose

HullQ must keep **market discoverability** separate from **canonical technical coverage**.

A sailboat model may be absent from HullQ's canonical BoatModel/BoatDesign universe and still have one or more real boats currently offered for sale. HullQ must not hide those market listings merely because technical research has not yet resolved the model.

The governing product principle is:

> **Market discoverability must not depend on canonical technical coverage.**

This is both a usability rule and a long-term data-growth mechanism.

## Three distinct layers

HullQ should treat the following as separate but connected systems:

```text
CANONICAL TECHNICAL UNIVERSE
verified/provenance-aware BoatModel + BoatDesign knowledge
        ↕ identity resolution when possible
MARKET UNIVERSE
current permitted market observations/listings
        ↕ demand and gap signals
COMMUNITY / DISCOVERY LEADS
missing-model reports, correction suggestions and source hints
```

None of these layers may silently substitute for another.

A market listing is evidence that a market offer exists under the observed listing identity. It is not, by itself, proof of HullQ's canonical technical facts.

A community report is a discovery lead. It is not, by itself, canonical evidence.

## Search behavior for unresolved market identities

A market listing must be allowed to exist in HullQ even when no canonical BoatModel has yet been resolved.

Conceptually, a later market model may support data such as:

```text
MarketListing
  source_listing_id
  raw_make
  raw_model
  raw_year
  source_market
  canonical_boat_model_id = null
  identity_status = UNRESOLVED
```

Exact implementation semantics remain subject to later market/query contracts, but the architectural rule is fixed: **a nullable/unresolved canonical relationship must not make the listing undiscoverable.**

Where source rights permit the relevant market data to be searched/displayed, users should still be able to find such boats by the available raw/observed market identity and permitted listing attributes.

Example user-facing state:

```text
XYZ 37

MARKET
3 boats currently found for sale

TECHNICAL DATA
This model has not yet been researched/resolved by HullQ.

[Request technical research]
[Report missing model / add a source]
```

This is preferable to returning `0 results` when the model is simply absent from the canonical technical universe.

## Missing-model and correction flows

HullQ should later offer at least two distinct contribution paths:

### Report a missing boat/model

Use when a user believes a model is absent from the canonical database.

Minimal useful input may include:

- manufacturer / brand as observed;
- model name;
- approximate year or generation if known;
- optional source/link;
- optional note.

The submission enters a **research/discovery queue**. It does not directly create a canonical BoatModel.

### Suggest a correction / add information

Use when a BoatModel already exists but a user believes information is missing, ambiguous or incorrect.

Again, the submission is a lead for independent verification, not an automatic canonical mutation.

## Research promotion rule

All community and market leads must pass through the same HullQ research/provenance discipline as any other discovery path:

```text
community or market lead
        ↓
research queue
        ↓
independent source discovery
        ↓
rights/access gate
        ↓
ResearchObservation / provenance
        ↓
normalization / conflict handling
        ↓
canonical resolution only when supported
```

A user statement such as `XYZ 37 has a skeg-hung rudder` must never become a canonical technical fact merely because it was submitted.

Likewise, seller-entered marketplace specifications remain source observations whose authority and rights must be evaluated; they are not automatically HullQ truth.

## Organic coverage-growth loop

This architecture allows HullQ's database to grow from actual demand rather than only from a one-time bootstrap campaign.

Three complementary discovery channels are expected:

1. **systematic manufacturer/archive research** — broad historical and structured coverage;
2. **market observations** — models that are actually being offered for sale;
3. **community reports** — long-tail and niche models noticed by users.

These signals can feed prioritization:

```text
missing/unresolved model observed repeatedly
        ↓
higher research priority
        ↓
independent research + provenance
        ↓
canonical model added/deepened
        ↓
existing unresolved listings can be linked
        ↓
future search quality improves
```

This means HullQ does not require complete 9,000+ model coverage before the product can become useful. Canonical breadth remains important, but **coverage becomes a continuous system rather than a one-time launch threshold**.

## Transparency principle

HullQ should communicate incomplete coverage directly and without apology or exaggerated completeness claims.

Preferred external posture:

> **HullQ is built independently from traceable sources.** We use permitted open data, manufacturer documentation, archives and other source-linked research. Coverage grows continuously. If a boat is missing, users can send a lead and HullQ can research it.

A stronger product-quality statement is:

> **We would rather show an honest gap than publish a technical fact we cannot support.**

Avoid defensive public language such as `we did not steal/copy the data`. The product should instead make independent provenance and visible uncertainty self-evident through its architecture and communication.

## Independence / legal-risk rationale

One strategic benefit of this approach is that HullQ can maintain a documented independent-development trail:

- production facts derive from source-linked, rights-assessed evidence;
- canonical records retain provenance;
- SailboatData remains post-hoc QA/reference only under the existing project rule;
- user reports and market observations are visibly separate discovery inputs;
- missing records remain visible rather than being silently filled from an opaque external database;
- HullQ does not need to reproduce another database's exact coverage set merely to make market search useful.

This architecture may help demonstrate independent dataset construction if HullQ's provenance is ever questioned. **It is not a guarantee against legal claims or disputes**, and legal questions remain subject to appropriate Austrian/EU legal advice.

## UX / epistemic states

The UI should make the difference between market knowledge and technical knowledge obvious.

Useful conceptual states include:

```text
MARKET PRESENCE      known / unknown
CANONICAL IDENTITY   resolved / unresolved / under review
TECHNICAL COVERAGE   verified / partial / insufficient data
```

Do not collapse those into one generic `known/unknown` badge.

This aligns with HullQ's wider design principle:

> **Visual confidence must never exceed epistemic confidence.**

A real listing can be displayed confidently as a market observation while its model-level technical data remains explicitly unresolved.

## Non-goals / guardrails

This principle does not authorize:

- scraping or retaining market data contrary to source rights/terms;
- creating canonical BoatModels directly from listing strings;
- treating seller-entered technical claims as verified HullQ facts;
- treating community submissions as canonical evidence without independent verification;
- fuzzy auto-merging unresolved listings into canonical identities without an accepted identity-resolution contract;
- claiming complete global model coverage;
- using SailboatData as a hidden fallback for missing canonical records.

## Future implementation implications

Later market/query work should explicitly design for:

- unresolved market identities;
- search over permitted raw/observed listing identity where canonical linkage is absent;
- optional canonical BoatModel linkage rather than mandatory linkage;
- missing-model reporting;
- correction/source-hint submission;
- research-priority signals from unresolved market frequency and community demand;
- retroactive linking of existing listings after canonical research succeeds;
- transparent UI separation between `market found` and `technical model researched`.

The exact schemas, moderation controls, anti-spam measures, API endpoints and ranking logic remain future implementation decisions.