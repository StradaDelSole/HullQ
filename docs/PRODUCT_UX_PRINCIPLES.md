# HullQ — Product UX Principles

**Status:** PROPOSED PRODUCT UX BASELINE — becomes controlling for Phase E/public UI work when merged  
**Purpose:** preserve the useful product/UX lessons from Listings Port, SailboatLab and Keel Index without copying their visual design or weakening HullQ truth semantics.  
**Execution relationship:** `docs/PRODUCT_EXECUTION_PLAN.md` remains controlling for sequence; this document controls UX/product-surface decisions when a slice builds or materially changes public Search, result, BoatDesign, comparison, market, save/monitor or alert UI.

## 1. Product experience thesis

HullQ should make a technically sophisticated yacht-buying research process feel simple enough for a normal serious buyer to use without learning a database interface.

The target experience is:

> **Reference-grade truth with consumer-grade clarity.**

The product must not look or behave like a raw marine database, a developer console, or a generic AI recommendation surface.

The UI exists to expose HullQ's strongest semantics clearly:

```text
what the buyer requires
→ what HullQ applied
→ which designs/configurations qualify
→ what is proven about a physical listing
→ what remains UNKNOWN
→ why the result has that state
→ what the buyer can do next
```

## 2. Eligibility before ranking

HullQ must keep hard truth/eligibility separate from preference/recommendation scoring.

A future guided or AI-assisted search may help translate intent into structured requirements, but hard requirements remain visible and deterministic.

Example:

```text
REQUIRED
Draft <= 1.60 m
Monohull
LOA 10–12 m

PREFERRED
Skeg-supported rudder
Higher water capacity
```

Evaluation order:

```text
hard eligibility
→ TRUE / FALSE / UNKNOWN
→ only then optional preference ranking among eligible candidates
```

A preference score must never rescue a hard non-match or turn missing evidence into a probable match.

## 3. Make query semantics visible

The user must be able to understand what HullQ believes they asked for.

For interactive Search and later guided Search:

- show active requirements as human-readable controls/chips;
- distinguish **Required** from **Preferred**;
- allow the user to edit/remove interpreted criteria;
- do not silently invent technical requirements from broad intent such as `bluewater`;
- if AI helps translate natural language, show the structured interpretation before or together with results;
- exact hard constraints shown in the UI must be exactly the constraints enforced by Search.

The interface should answer within seconds:

> What did HullQ apply, and which parts are hard requirements?

## 4. Truth state must be visible, not hidden in prose

Result and listing surfaces should use clear semantic states such as:

- `CONFIRMED FIT` / `CONFIRMED MATCH`;
- `CONFIRMED NON-MATCH` where useful;
- `UNKNOWN` / `CONFIGURATION UNKNOWN` / `INSUFFICIENT DATA`.

For a result that matters to a purchase decision, expose concise reasons:

```text
✓ Draft 1.52 m — confirmed
✓ LOA 11.3 m — confirmed
? Rudder configuration — insufficient evidence
```

The UI must not present a single confidence percentage as a substitute for this evidence structure.

## 5. Separate design truth from physical-listing truth visually

Where current market inventory is shown, HullQ must make the scope boundary obvious:

```text
DESIGN / CONFIGURATION
what the BoatDesign can be

THIS OFFER
what is proven about the concrete advertised boat
```

A model-level specification must never visually appear as if it were observed on the specific advertised boat.

This distinction should survive cards, detail pages, summaries, alerts and SEO/public pages.

## 6. BoatDesign page as a decision hub

Keel Index demonstrates the usefulness of a coherent canonical model page that combines multiple buyer tasks. HullQ should eventually use the canonical BoatDesign page as a **decision hub**, not merely a specification table.

Potential modules, introduced only when supported by the Product Execution Plan and actual data:

- identity / generation / factory configurations;
- verified specifications and provenance;
- performance/derived metrics with methodology;
- current market offers;
- compare action;
- save/watch/monitor action;
- price/market context where rights permit;
- known issues / survey-oriented evidence where a future methodology supports it;
- documented operational/offshore evidence as a separate future evidence class;
- related designs and buyer-relevant comparisons.

The first Alpha does **not** need all these modules. The architectural lesson is one canonical identity with progressively disclosed buyer-relevant modules, rather than fragmented disconnected pages.

## 7. Action hierarchy should follow buyer intent

Primary actions should be close to the information that motivates them.

For example on a BoatDesign/result surface:

```text
Search current offers
Compare
Save / Watch
Why this matches
```

Later, after validated product pull:

```text
Alert me when a confirmed fit appears
```

Do not bury core actions in account/admin navigation.

## 8. Market statistics must communicate evidence quality

Keel Index's market presentation provides a useful pattern: price range/median, timeframe and sample-size caveats are shown together.

HullQ must go further and retain semantic precision:

- distinguish **asking price** from achieved sale price;
- show observation timeframe;
- show sample count;
- warn when sample size is small;
- state whether values include active, expired or historical listings;
- never imply a valuation precision the data does not support;
- configuration-sensitive market summaries must not mix materially different configurations without disclosure;
- any price history/Days-on-Market feature remains subject to source-rights approval.

A future `price when new` / inflation-adjusted comparison is a useful optional context feature, not a current requirement. If implemented, source and inflation method must be explicit.

## 9. Operational evidence is promising but separate from design suitability

Keel Index's documented-passages layer is a strong example of original data creating buyer value and SEO value.

HullQ may later evaluate a separate evidence class such as documented passages, race/rally participation or real-world cruising records, but:

- a passage by one physical boat does not automatically prove every sistership is `bluewater capable`;
- operational evidence must remain separate from factory/design facts and from physical-listing configuration truth;
- every record should have source/provenance;
- any derived suitability claim requires an accepted methodology.

This is a future research/product candidate, not part of the Seed Corpus or first Alpha.

## 10. Missing imagery is better than unlicensed or misleading imagery

Keel Index demonstrates a useful honest empty-state: when a model image is unavailable it can show a neutral placeholder and invite a contribution rather than fabricating a misleading photo.

HullQ should prefer:

1. authorized manufacturer/designer media where rights permit;
2. explicitly licensed partner/broker images where rights permit;
3. user-contributed media under a clear upload/license policy;
4. neutral no-image/diagram placeholder.

Do not copy third-party marketplace/reference images merely to make cards look complete. Do not generate a photorealistic boat image and present it as documentary evidence of the model or listing.

If user-contributed imagery is added later, upload rights, attribution, moderation and takedown handling must be defined before public use.

## 11. Visual design principles

Competitive review shows that visual execution materially affects perceived trust and usability.

HullQ should aim for:

- modern, calm, information-dense but not database-like presentation;
- strong typography and hierarchy;
- consistent card/grid dimensions;
- generous enough spacing without wasting viewport area;
- clear contrast and accessibility;
- responsive/mobile-first behavior;
- progressive disclosure for expert detail;
- coherent visual states for confirmed / unknown / excluded;
- strong scanability of numbers, units and provenance;
- a distinctive maritime identity without nostalgic clutter or generic SaaS styling.

Do **not** copy Keel Index's cream/navy/editorial aesthetic or SailboatLab's black/yellow interface. The lesson is coherence and hierarchy, not their brand treatment.

## 12. Avoid competitor UX failure modes

### From Listings Port

Avoid:

- a rich-looking result whose hard requirement is not actually enforced;
- model identity fuzziness hidden behind polished output;
- AI prose that makes scope/provenance harder to understand;
- technical values collapsed across configurations.

### From SailboatLab

Avoid:

- large unexplained global fit percentages as the primary decision signal;
- mixing hard constraints and preferences without obvious semantics;
- inconsistent card geometry / excessive unused space;
- developer/database-like detail presentation;
- ambiguous zero/missing values;
- a UI that requires the user to understand the scoring system before trusting results.

### From Keel Index

Avoid:

- absolute coverage claims such as `every boat` or `whole market` unless HullQ can objectively substantiate them;
- treating a generic model-level keel/draft description as sufficient when configurations differ;
- using disclaimer text as a substitute for field-level provenance/UNKNOWN semantics;
- US-default assumptions in currency, units or market framing for an international product.

## 13. International-by-design presentation

Keel Index's visible surface is North-America-first in several places (USD, U.S. CPI context, many U.S. models/sources/events), although it publicly states market coverage in North America **and Europe**. HullQ should not assume a U.S.-only or EU-only buyer.

UI requirements must therefore support:

- metric and imperial units without changing underlying truth;
- explicit currency and conversion context;
- location/region semantics suitable for international inventory;
- language/i18n rules from `docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md`;
- no hard-coded U.S. price, date or unit conventions in domain semantics.

## 14. Product-led content and UX should reinforce each other

Public model, comparison and technical-discovery pages should not become a separate marketing site detached from Search.

The user should be able to move naturally:

```text
Google / external discovery
→ useful HullQ data page
→ inspect why the facts are trusted
→ refine/execute technical Search
→ inspect current offers
→ compare/save/monitor
```

The same canonical identity and truth read model should drive all of these surfaces.

## 15. Phase E implementation obligation

When Phase E / Web Alpha begins, every slice that creates or materially changes a public Search/result/BoatDesign/market UI **must name this document as a controlling artifact**.

The first Alpha is intentionally small, but must demonstrate these minimum UX semantics:

1. visible hard requirements;
2. exact Search execution behind those requirements;
3. clear design/configuration result identity;
4. visible `CONFIRMED` vs `UNKNOWN` state;
5. design truth separated from physical-offer truth;
6. concise `why`/evidence path;
7. clear next action into available offers/outbound inventory.

Anything beyond those seven minimums is optional until demand validates it.

## 16. Later candidates — not current scope

Useful competitive ideas retained for later evaluation, **not authorized for immediate build**:

- market-value cards with robust sample-size handling;
- price-when-new / inflation-adjusted context;
- documented passage/offshore-record dataset;
- survey guides / known-issues evidence;
- owner reviews;
- curated books/video/affiliate library;
- direct free seller listings;
- user-contributed model imagery;
- preference scoring after deterministic eligibility;
- guided natural-language use cases;
- richer comparison dashboards;
- possible AI-assistant/API distribution as a secondary channel.

These candidates enter the roadmap only through observed demand, the one-capability rule and the accepted Product Execution Plan.

## 17. North Star is not a backlog

The long-term opportunity may combine competitor-proven strengths such as broad aggregation, guided discovery, coherent decision hubs, market context, monitoring and data-driven SEO with HullQ's stricter Search/truth semantics.

That composite vision is a **North Star only**. It must not become a pre-Gate-1 feature checklist, corpus-expansion argument or multi-capability slice.

The Product Execution Plan and Gate 1 determine what may actually be built next.

## 18. AI assistants are a secondary channel hypothesis

General AI assistants may become both competitors for top-level discovery and future distribution surfaces for HullQ's verified vertical data/search.

Treat such integrations as:

> **additional channel, not distribution foundation.**

HullQ should retain direct product/distribution capability and avoid structural dependence on third-party tool-call economics, ranking decisions, plugin/tool policies or access changes.

No AI-assistant/API distribution work is justified before the Product Execution Plan reaches a relevant validated phase.

## 19. Pre-Gate-1 value must survive without explanation

The first Concierge tests are not demos in which the moderator teaches the participant why HullQ is superior.

A primary value signal counts only when the participant's behavior or preference reveals the benefit **before** the moderator explains HullQ's configuration/provenance advantage.

The participant does not need to say `configuration truth`. Observable evidence includes:

- changing a shortlist or decision;
- requesting monitoring/alerts;
- preferring an evidence-backed `CONFIRMED / UNKNOWN` result.

If the supposed advantage becomes compelling only after explanation, record it as prompted feedback rather than spontaneous product pull.

The possibility that a proprietary configuration/evidence corpus becomes defensible later is likewise not permission to expand pre-Gate-1 data work beyond the bounded Seed Corpus, active/planned Concierge queries or real validation blockers.
