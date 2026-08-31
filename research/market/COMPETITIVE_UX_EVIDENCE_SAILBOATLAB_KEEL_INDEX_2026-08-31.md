# Competitive UX evidence — SailboatLab + Keel Index

**Date:** 2026-08-31  
**Status:** bounded visual/product research; no competitor screenshots retained in repository  
**Input:** Project Owner supplied contemporaneous screenshots of SailboatLab and Keel Index public surfaces; selected public claims were cross-checked against live public pages.  
**Purpose:** preserve product/UX lessons that should influence HullQ's future Web Alpha and public product surfaces without copying competitor branding or expanding current SLICE-0038 scope.

## 1. Scope discipline

This document records only:

- visible information architecture and interaction patterns;
- useful product modules exposed in the screenshots/public pages;
- competitor failure modes relevant to HullQ UX;
- concrete implementation consequences already captured in `docs/PRODUCT_UX_PRINCIPLES.md`.

It does **not**:

- evaluate competitor source rights;
- authorize HullQ to use competitor data or imagery;
- add a new Product Execution Plan phase;
- require any of the later feature candidates to be built now.

The combined long-term picture of competitor strengths plus HullQ truth/search integrity is a **North Star, not an execution roadmap or feature backlog**. It may not be used to widen pre-Gate-1 scope.

---

# 2. SailboatLab visual/product evidence

## Visible strengths

The screenshots confirm several product ideas worth retaining:

1. **Use-case entry points.** SailboatLab offers intent-led starting points such as low-draft cruisers, high-latitude boats, long-keel production boats and large cruising catamarans. This can reduce the blank-filter problem for users who know the mission but not the exact technical fields.
2. **Editable requirement chips.** Requirements are exposed as removable criteria rather than being hidden entirely inside an AI answer.
3. **Model comparison before market analysis.** The product treats design selection as a distinct step from later market/ad analysis.
4. **Relative preference scoring.** Ranking can help when the user has several soft goals rather than only hard limits.

## Visible weaknesses / risks

The screenshots also show why HullQ should not copy the presentation model:

- extensive unused viewport space;
- inconsistent card/image dimensions;
- dense black UI with weak hierarchy for a consumer research product;
- database-like detail tables;
- cryptic chips such as `Draft: lowest`, `Sail area / displ.: highest`, or approximate ratio targets;
- primary reliance on global fit percentages that do not immediately explain eligibility;
- hard requirements and preferences are not visually distinguished strongly enough;
- a user must understand the scoring model before understanding why a boat ranks where it does;
- cookie/overlay elements materially intrude on content in the reviewed screenshots;
- numeric missing-value behavior elsewhere in the public product reinforces the risk of an interface showing a number before its epistemic status.

## HullQ consequence

Keep the useful idea:

```text
I know my mission
→ guided requirement suggestion
```

but make the interpretation explicit:

```text
REQUIRED
Draft <= 1.60 m
Monohull

PREFERRED
Skeg-supported rudder
Higher water capacity
```

Then:

```text
eligibility / truth first
→ optional preference ranking second
```

A global score must never hide a failed hard constraint or UNKNOWN.

---

# 3. Keel Index visual/product evidence

## Market orientation

The visible product is **North-America-first rather than U.S.-only**:

- homepage/listing examples emphasize U.S. boats, USD, Craigslist and U.S. events;
- inflation examples use U.S. CPI context;
- many popular boats and editorial examples are North-American classics;
- however, the public homepage explicitly states that its market search covers **North America and Europe**.

HullQ should therefore treat Keel Index as a strong North-American market/reference benchmark, not as proof that Europe is unserved.

## 3.1 Strong coherent brand and information hierarchy

The screenshots show a much more coherent product than SailboatLab:

- consistent cream/navy/gold palette;
- predictable typography and spacing;
- clear navigation;
- obvious separation of editorial, database and market modules;
- cards and call-to-actions have stable visual treatment;
- the homepage communicates the value proposition immediately through a direct search field plus proof metrics.

The transferable lesson is **coherence and hierarchy**, not the visual theme itself. HullQ should not imitate the traditional/editorial styling.

## 3.2 Search and proof metrics above the fold

The homepage pairs a large search box with visible product proof such as:

- boats indexed;
- boats for sale;
- documented passages;
- ORC rating certificates.

This is useful because the product proposition is understandable without reading an essay.

**HullQ implication:** the eventual homepage should lead with the actual decision task and measurable product capability. If HullQ shows coverage metrics, they must be mechanically supportable and not absolute marketing claims.

Do not publish claims equivalent to `every sailboat` or `whole market` unless coverage can be substantiated.

## 3.3 Canonical BoatDesign page as a buyer decision hub

The Dufour Classic 35 screenshots show a particularly useful architecture:

- canonical identity/header;
- summary specifications;
- price range / median asking price;
- unit switch;
- `Compare`;
- `Watch this boat`;
- price estimate;
- tabs for `Overview`, `Sails`, `Performance`, `Survey Guide`, `For Sale`, `Reviews`;
- long-form model context;
- full specification table;
- performance ratios;
- current market context.

This is the strongest UX lesson from Keel Index.

**HullQ implication:** one canonical BoatDesign identity should eventually act as a decision hub, with progressively disclosed modules rather than many disconnected mini-tools. HullQ's differentiator on that page must be configuration scope, provenance and physical-listing truth.

## 3.4 Action placement

`Compare`, `Watch this boat`, valuation and market actions are placed adjacent to model facts rather than buried in account navigation.

**HullQ implication:** buyer actions should be context-adjacent:

```text
Compare
Search current offers
Save / Watch
Why this matches
Alert me when a confirmed fit appears   # later, after validation
```

## 3.5 Honest no-image state

A reviewed Dufour Classic 35 page shows a neutral missing-photo panel plus an invitation to add a photo instead of fabricating documentary imagery.

This is directly useful to HullQ because image rights are a real product constraint.

**HullQ implication:** no image is preferable to unlicensed media or a generated image presented as factual model/listing evidence. Authorized, licensed or clearly user-contributed imagery can be added later under explicit rights rules.

## 3.6 Market statistics communicate uncertainty better than a single price

The screenshots/public page show:

- typical asking-price range;
- median asking price;
- observation window;
- explicit small-sample warning;
- count of listings used;
- distinction between asking prices and achieved sale prices;
- original list price and inflation-adjusted context as a separate reference.

This is a useful presentation pattern.

**HullQ implication:** future market intelligence should always expose sample count, timeframe, observation class and asking-vs-sale semantics. Configuration-sensitive boats must not be pooled blindly if configurations materially affect value.

## 3.7 `Price when new` creates useful historical context

Keel Index shows original list price, inflation-adjusted equivalent and current median asking price together.

Potential HullQ value:

- helps a buyer understand depreciation/context;
- creates unique model-page content;
- can support SEO/editorial stories.

But this is not current scope. If later implemented, HullQ must retain the original-price source, currency/date basis and inflation method.

## 3.8 Documented passages are a strong original-data product

Keel Index prominently uses documented passages/races/rallies and exposes model-level passage history. Public pages state that passage entries are backed by published sources and typically avoid publishing crew identities.

This is valuable because it turns a proprietary research dataset into both:

- buyer evidence/context;
- high-value indexable content.

However:

```text
one sistership completed an ocean passage
!=
all boats of this design are proven suitable for every bluewater use
```

**HullQ implication:** documented operational history is a promising future evidence class, but it must remain distinct from design facts, physical-listing facts and any derived suitability label unless a methodology is accepted.

## 3.9 Data-driven editorial is tightly connected to the product

The screenshots show articles such as:

- best boats under a price threshold;
- bluewater boats under a price threshold;
- singlehanded boats;
- engine field guide;
- trailerable sailboats.

Public examples tie articles to active listing/price data and documented usage data.

This reinforces the already accepted HullQ SEO principle:

```text
unique product data
→ unique buyer insight
→ indexable page
→ continue into the product
```

not:

```text
keyword
→ generic AI article
→ unrelated search experience
```

## 3.10 Books/videos/library is a retention + affiliate pattern, not core product

Keel Index links books to the boats/design histories they feature and exposes a library as part of the research journey.

Potential later value for HullQ:

- useful research adjacency;
- affiliate revenue;
- stronger model/entity pages;
- internal linking.

Do not prioritize before Search/market/monitoring validation.

## 3.11 Direct free listings are a supply-acquisition tactic

Keel Index advertises `List your boat — free` and shows direct listings/SOLD state.

This is relevant as a future marketplace/supply-side tactic, but **does not change HullQ's current decision not to panic-pivot into a native marketplace**.

If direct supply later emerges naturally, a low-friction/free seller listing could be evaluated at that time.

## 3.12 Strong internal linking / product graph

The screenshots show repeated links among:

- popular boats;
- builders;
- compare;
- listings;
- articles/guides;
- books;
- model tabs/modules.

This is good product navigation and good crawl architecture because the same graph supports users and search engines.

HullQ should preserve the same principle but derive links from canonical identity and deterministic Search relationships.

---

# 4. Where HullQ should deliberately differ from Keel Index

Keel Index is a strong benchmark, but not the target design.

HullQ should be more explicit about:

1. **Configuration scope** — no universal single draft/keel value where factory configurations differ.
2. **Physical listing proof** — design facts do not masquerade as facts about the concrete advertised boat.
3. **UNKNOWN** — not a general disclaimer at the bottom of a page, but a field/result state.
4. **Hard requirement execution** — user constraints are enforced exactly.
5. **International defaults** — units, currency and geography are not U.S.-centric domain assumptions.
6. **Modern search UX** — faster, cleaner, more task-oriented than a traditional reference publication.
7. **Coverage claims** — measurable, qualified and source-aware rather than `every boat`/`whole market` style absolutes.
8. **Provenance** — relevant evidence should be inspectable near the claim, not replaced by a generic `verify independently` disclaimer.

---

# 5. Implementation matrix

## Must influence first Web Alpha

- clear visible requirements;
- Required vs Preferred semantic distinction when preferences exist;
- deterministic eligibility before ranking;
- clear CONFIRMED / UNKNOWN states;
- design/configuration vs concrete listing scope visible;
- concise `why` path;
- strong visual hierarchy and consistent result-card geometry;
- current-offer action close to the result;
- no fabricated/unlicensed documentary imagery.

These are captured in `docs/PRODUCT_UX_PRINCIPLES.md` and are required controlling input for Phase E UI slices after that baseline is merged.

## Retain for later validation

- BoatDesign decision-hub expansion;
- Compare;
- Watch/monitor;
- market-value cards;
- sample-size-aware price history;
- price-when-new/inflation context;
- guided mission/use-case search;
- preference ranking after eligibility;
- documented passages / offshore operational evidence;
- survey/known-issues evidence;
- books/videos/affiliate library;
- user-contributed imagery;
- direct seller listings;
- possible AI-assistant/API distribution as a secondary channel.

## Explicitly do not copy

- SailboatLab's unexplained global-fit-score-first experience;
- competitor brand palettes/layouts;
- U.S.-centric units/currency as the domain default;
- absolute market-coverage claims without proof;
- generic model disclaimers as a substitute for field-level truth;
- direct marketplace expansion before the Product Execution Plan justifies it.

---

# 6. AI assistants: threat and possible channel

General AI assistants can increasingly answer the user's top-level discovery question directly, which creates a distribution threat to specialist search products.

HullQ may later expose verified vertical search/data through such assistants, but this must remain:

> **an additional channel, not a distribution foundation.**

HullQ should retain direct product/distribution capability and avoid structural dependence on third-party tool-call economics, rankings, plugin/tool policies or access changes.

This is a later channel hypothesis, not a current build item.

---

# 7. Pre-Gate-1 validation discipline

The possibility that a proprietary configuration/evidence corpus becomes a real moat later is not a reason to expand the Seed Corpus now.

Before Gate 1, Data/Research work should directly support:

- one of the bounded Seed-Corpus BoatDesigns;
- an active/planned Concierge query; or
- a real validation blocker.

The Concierge test must also avoid moderator-created value: if participants only appreciate HullQ's configuration/provenance advantage after it is explained, that is prompted feedback rather than evidence of spontaneous product pull.

---

# 8. Research stop

The screenshots materially improve the UX/product benchmark but do not require another competitor phase.

Keel Index is retained as:

> **strong benchmark for coherent model/market UX + data-driven SEO**

SailboatLab is retained as:

> **benchmark for guided use cases, scoring and design-to-ad buyer intelligence, with clear UX failure modes to avoid**

Further competitor browsing should resume only when a concrete future capability requires a benchmark or a material external fact changes the HullQ thesis.
