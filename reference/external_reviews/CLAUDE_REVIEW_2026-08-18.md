# HullQ — Independent Review

*Prepared as requested: critical, commercially-oriented second opinion. Brief-only claims are marked **[Brief]**; anything checked against the live web is marked **[Web]** with a source. Where I have no way to verify something, I say so rather than guessing.*

---

## 1. Restating the idea

**Problem (as framed):** buyers who can describe what they want technically (draft, keel type, D/L ratio, construction) but don't know which models fit that description are poorly served by marketplaces built around make/model search and shallow filters.

**Solution:** an independent technical design database, searched by physical/design characteristics, that resolves to a set of matching *models* — which are then looked up live on external marketplaces to see what's currently for sale.

**Core journey:** describe hull/keel/rudder/rig/dimension criteria → get matching designs → see current listings of those designs → compare/save/alert.

**Where my reading differs from the brief's framing:** the brief treats the *design database* as the hard, valuable part and the *marketplace layer* as the thin, mechanical part ("does not plan to own... seller acquisition... payments"). I'd flip that emphasis. As **[Web]** research below shows, a free, open, technically detailed sailboat spec database with the exact same ratio set HullQ proposes **already exists in at least four independent forms** (SailboatData.com, Boat-Specs.com, sailboat-database.com, TheBoatDB, plus Good Old Boat's saildata). The database is not the differentiated part — it's table stakes that's already been built, multiple times, some of it for free on open licenses. The thing that would actually be new and hard is the *live cross-marketplace matching layer*, and that's exactly the part the brief treats as the "easy," non-owned, adapter-based piece. That inversion matters a great deal for where effort should go.

**Actual early adopter:** not "sailboat buyers" in general. It's a narrow slice: an experienced, technically literate buyer (often a repeat owner, sometimes ex-racer or engineer/naval-adjacent hobbyist) who has already rejected browsing by brand and is doing manual cross-referencing today — spreadsheets, forum threads, SailboatData tabs open in parallel — because they have a specific technical requirement (e.g., "shoal draft, encapsulated keel, skeg-hung rudder, moderate displacement, under 11m") that no marketplace filter expresses well.

**Real value proposition, if it works:** *time saved converting a technical requirement into a shortlist of buyable, currently-listed boats* — not "find the right boat," which implies more certainty than search can deliver. The honest value prop is closer to "stop manually cross-referencing spec sheets against marketplace filters."

---

## 2. Problem quality

- **Pain:** real but narrow and episodic, not chronic. It only bites during an active search, and only for buyers with strong technical priors (most buyers search by brand, price, and location first).
- **Frequency:** low at the individual level — a buyer does this search intensively for weeks/months once, then not again for years. This is a low-frequency, high-stakes search problem, structurally similar to real estate search rather than to a recurring-use product.
- **Do people actively seek a solution today?** Some do — but the workaround (SailboatData + manual marketplace tab-switching + forums) is *tolerable*, not "genuinely bad." That's an important distinction: people who dislike a workaround enough to complain about it on forums don't automatically switch tools, especially if the new tool doesn't remove a step, only adds a filtering layer in front of the same manual marketplace-checking.
- **Category:** primarily an **enthusiast/experienced-buyer problem**, with a secondary sliver of naval-architecture-adjacent professionals (surveyors, class-association members). It is *not* a broker problem (brokers already know their own inventory) and *not* a first-time-buyer problem (first-timers don't have technical criteria yet — they need education, not a filter).
- **Interesting vs. valuable:** this is the crux. The workflow described ("I know the characteristics, not the model") is intellectually clean and clearly true for *some* buyers, but the brief gives no evidence — and none is easily available — on how many buyers actually search this way versus rationalizing brand/price/location searches after the fact. This is asserted as a "real buying workflow," but it reads more like founder/developer intuition than a documented user behavior. That needs testing before the database is built, not after.

---

## 3. Differentiation and competitive position

**[Web]** This is the section where the brief's self-assessment needs the most correction. The "technical-characteristic-first" search space is **already occupied**, and some occupants use the identical ratio methodology HullQ proposes:

- **SailboatData.com** — over 9,000–9,200 production sailboat models, refine-search by dimensions, a ratio calculator, side-by-side compare, free to browse, has an iOS app with saved favorites and side-by-side compare.
- **sailboat-database.com** — explicitly computes Sail Area/Displacement, Ballast/Displacement, Displacement/Length, Comfort Ratio, and Capsize Screening Formula — **the exact ratio set HullQ lists in section 5** — sourced from Wikidata (CC0) and Wikipedia infoboxes (CC-BY-SA), openly licensed, no scraping.
- **Boat-Specs.com** — 1,605 boats, multi-criteria technical search, builder/designer/range browsing, running since 2015.
- **TheBoatDB** — full spec database, side-by-side compare, benchmarking.
- **Good Old Boat saildata** — 4,838 boats with sail dimensions and blueprints.

None of these do live marketplace matching. That is the one piece of the chain that is *not* already commoditized. Everything upstream of "find matching designs" — taxonomy, ratios, compare UI, even open-licensed data — has multiple existing, free, sometimes-open-source-adjacent implementations.

**Direct competitors:** the spec-database sites above, for the "find design" step.
**Indirect competitors:** brokers' own search tools (YachtWorld/BoatWizard, Boat24, TheYachtMarket), which are shallow-filter but have the actual inventory.
**Substitutes:** forums (Cruisers Forum, Sailing Anarchy), Facebook boat-model groups, and increasingly generic AI chat ("what boat under 11m has an encapsulated keel and skeg rudder under $80k") — which can already answer a decent first pass of exactly the query HullQ is built around, using public knowledge, without any dedicated product.
**Saved-search substitute:** YachtWorld, Boat24, TheYachtMarket, Rightboat, Apollo Duck etc. all already offer saved searches and email alerts on their own listings.

**What HullQ would need to do substantially better:** not "have a technical database" — that bar is already cleared by others, several for free. It would need to (a) match designs to *live, current, deduplicated* listings across marketplaces in a way that is measurably faster/better than opening SailboatData in one tab and YachtWorld/Boat24 in another, and (b) do it without the buyer having to already suspect which models fit (i.e., the matching quality has to be good enough that the "unknown unknowns" it surfaces are worth the switching cost). That is a real, defensible value proposition *if it can be delivered* — but it depends entirely on the marketplace-integration layer the brief treats as secondary, and which section 7/9 below shows is the highest-risk part of the whole project.

---

## 4. Strongest parts of the concept

1. **Keel/rudder/skeg as independent fields, not a combined legacy label.** This is a genuine, non-obvious modeling improvement over most existing sailboat databases (which do tend to use compound categorical fields). It's a real technical differentiator for search precision, even if small.
2. **The "notify on any design matching my criteria" alert**, as distinct from "notify on this one model." If it actually works across marketplaces, this is the single feature with no easy substitute today — existing marketplace alerts are model/keyword-based.
3. **Multihulls as first-class objects from day one.** Catamaran/trimaran buyers are underserved by search tools built primarily around monohull ratios and taxonomies; this is a legitimate, if narrow, wedge.
4. **Provenance-aware data model (verified/partial/conflict/needs_review with field-level source).** Commercially this only matters if it's *visible and trusted by users* (e.g., "confidence: verified from builder brochure" shown on a spec) — otherwise it's an internal quality process, not a product feature. As internal QA discipline it's sound engineering practice.
5. **Deliberate exclusion of two-sided-marketplace operations** (no payments, contracts, dispute resolution, seller acquisition). This keeps the operational burden lean *if* the marketplace-adapter dependency can actually be sustained — see section 7.

None of these make the idea commercially proven; they're the parts of the *design* worth keeping if the underlying thesis survives testing.

---

## 5. Weakest parts / failure modes (ranked by severity)

| # | Failure mode | Severity | Likelihood | Why it matters | Testable pre-build? | Cheapest test |
|---|---|---|---|---|---|---|
| 1 | No real recurring demand for technical-first search (most buyers search by brand/price/location) | Existential | Medium-High | If false, nothing downstream matters | Yes | Talk to 15–20 recent boat buyers about how they actually searched; landing-page + query-log test |
| 2 | Marketplace access blocked/legally restricted (no public read APIs; brokers only get *push*, not third parties *pull*) | Existential | High | Kills the one truly differentiated layer | Yes | Directly contact 3–4 target marketplaces about API/partner terms *before writing an adapter* |
| 3 | Independent design database is redundant with existing free/open competitors | High | High (already true — see §3) | Undermines the "moat" thesis and wastes the research pipeline's cost | Yes | Compare coverage/quality of sailboat-database.com's open CC0 data against a manual pilot before building parallel infrastructure |
| 4 | Cross-platform listing deduplication (same boat on 3 sites) is unsolved and hard | High | High | Bad dedup = visibly broken product ("why do I see the same boat 3 times") | Partially — can be prototyped manually on a handful of models | Manually attempt dedup across 2 marketplaces for 20 boats, measure false-positive/negative rate |
| 5 | Field-level provenance/research pipeline cost per model is uneconomical at scale | High | Medium-High | Determines whether Phase 2 (500→2000+ designs) is financially viable at all | Yes — this is literally what the 50–100 pilot is for | Run the pilot, cost the hours honestly including review/conflict time |
| 6 | Taxonomy complexity (variant/generation boundaries, multihull-specific fields) balloons scope | Medium | High | Slows the pilot, inflates schema before validation | Yes | Freeze taxonomy v0 before the pilot, log every field that had to be added mid-pilot |
| 7 | Legal risk from the existing Sailboatdata scrape leaking into "research seeds" | Medium-High | Medium | Could taint the "independent" claim and create liability | Yes, with legal counsel, cheaply | AT/EU lawyer review of the scrape's actual current use, before Phase 1 scales |
| 8 | SEO/distribution: technical long-tail pages compete against SailboatData's decade-plus domain authority and 9,000+ indexed model pages | Medium-High | High | Cheapest acquisition channel may simply not be available | Yes | Check current SERP position for 10 target model+spec queries against SailboatData/Boat-Specs before counting on SEO |
| 9 | Monetization unproven; affiliate/referral assumed but not confirmed available from major marketplaces | Medium | High | Revenue plan may not exist even if product works | Yes | Directly ask 3 marketplaces/brokers about referral/affiliate terms before building the hooks |
| 10 | Maintenance burden of N marketplace adapters (breakage, ToS changes, IP blocks) is ongoing and compounding, not a one-time cost | Medium-High | High | Threatens the "lean, exception-driven" operating thesis in §12 | Partially | Run one adapter live for 60–90 days and log actual break/fix frequency before committing to Phase 6 |

---

## 6. Data-moat analysis

**Is the independent BoatDesign database likely to become a moat, a useful operational asset, or expensive table stakes?**
Based on the competitive landscape in §3, **expensive table stakes**, not a moat — at least at the taxonomy/ratio/spec level the brief describes. A moat requires either (a) data no one else has, or (b) data assembled at a cost/quality others can't match. Right now, open, CC0/CC-BY-licensed sailboat spec data with the same ratios already exists and is legally reusable by anyone, including HullQ. Field-level provenance *could* eventually become a moat if it reaches a depth and trustworthiness no free source has — but that's a multi-year, expensive bet, not a starting asset.

**How much completeness is necessary before the product is useful?** Not full completeness — a useful MVP only needs enough designs to cover models that actually turn up used, which is a much smaller, long-tail-weighted set than "every design ever built." The brief already gestures at this ("coverage of real boats appearing on the used market, not matching another database's total design count") — that instinct is right and should be leaned into harder, faster.

**Is field-level provenance strategically valuable now, or overengineered?** At MVP stage, overengineered relative to unproven demand. It's good practice to build the schema so it *can* carry provenance later, but investing heavily in conflict-resolution workflows before anyone has confirmed they'll use the product is solving a scaling problem HullQ doesn't have yet.

**Is the 50–100 model pilot the right validation mechanism?** For *data-acquisition economics*, yes — reasonable and cheap. But it validates the wrong thing first. It tells you whether you *can* build the database economically, not whether anyone *wants* what you'd build with it. Recommend running a demand-side test (§13) in parallel or before, not after.

**Metrics to decide continue/change/stop (data side):** hours per verified model, %reaching "verified" vs "needs_review," conflict rate, and — critically — cost per model *compared to simply linking out to sailboat-database.com's already-open CC0 dataset* for the same fields. If HullQ's own pilot doesn't clearly beat "reuse the open data, add only what's missing," building a parallel database isn't justified.

**Build order recommendation:** **market-demand-first, not breadth-first.** Pick ~30–50 models that are (a) common on the current used market in HullQ's target region and (b) diverse enough to stress-test the taxonomy (mono/cat/tri, various keel/rudder types), rather than a "varied" sample chosen for data-modeling reasons. Anchor the pilot to what a first real user would actually search for.

---

## 7. Market-integration analysis

This is the section I'd push back on hardest.

**[Web]** Checked the access model for the marketplaces named in the brief's adapter list:

- **YachtWorld / Boats Group:** does not offer a publicly documented developer API for outside applications. What exists is a *broker/dealer-facing* feed (BoatWizard/Boats Group API) that lets a broker who already has a paid account push **their own** listings to **their own** website — not a general read API for a third party to pull the full marketplace. Third-party access to full listing data is done via unofficial scraper-as-a-service tools, which sit in legally uncertain territory.
- **Boat24 / the Boatvertizer network (covering scanboat, theyachtmarket, apolloduck, rightboat, dba.dk, hiswa.nl, etc.):** the available "sync" products are for dealers/sellers to *push* their own listings out to multiple portals — again not a third-party read API for pulling all current listings for meta-search. One independent technical blog explicitly documents scraping boat24.com because no accessible API exists for that purpose.
- **TheYachtMarket's "LiveFeedback" API:** lets brokers already listed on TheYachtMarket display their own listings on their own site — same pattern.

**Conclusion:** across every marketplace the brief names, the available official access model is "brokers can push their own inventory outward," not "third parties can pull the full market inward." That is the opposite of what a meta-search product needs. The realistic paths are (a) negotiate bespoke commercial data-partner agreements with each marketplace individually — slow, and marketplaces generally have little incentive to help a tool that reduces traffic to their own site — or (b) scrape, which is not per-se illegal but is contract/ToS risk that scales with how many sites you touch and how much you monetize on top of the data (courts have gone both ways on scraping-vs-ToS depending on facts; the safest reading is "possible, contested, fact-specific, and gets riskier the more commercial and the more sites are involved").

**Is live/on-request the right MVP architecture?** Directionally yes (avoids the cost of mirroring), but it doesn't remove the access problem — you still need permission or a scraping strategy per source, live or not.

**Is one marketplace enough to prove value?** For proving the *technical-search-to-listing* mechanic, yes — and this is a much smaller, faster experiment than the brief's roadmap implies. For proving the *actual* differentiated value ("finds boats you wouldn't have thought to search for, across the whole market"), no — the value proposition specifically depends on breadth, which is the hardest and riskiest part to get official access to.

**Does HullQ have a viable standalone product with weak market integration?** No. Without a working listings layer, HullQ degrades to "another free spec database," a category that's already crowded and largely given away for free (§3). The design database alone is not the product.

**Alternative integration strategies worth exploring, roughly in order of realism:** (1) outbound deep links to marketplace search results pre-filled with matched model names — no scraping, no API, weaker UX but zero legal risk and buildable in days; (2) user-submitted "I found this listing" entries to bootstrap a listings layer manually before any adapter exists; (3) formal partnership/referral conversations with smaller or regional marketplaces (e.g., Boat24) that might see co-marketing value, rather than the big established players who have no reason to cooperate; (4) broker-inventory partnerships, where a handful of brokers manually feed HullQ their stock in exchange for lead flow, sidestepping the ToS question entirely; (5) full scraping, last, and only after Austrian/EU legal review, as the brief already plans.

---

## 8. MVP critique

**Must-have for first validation:**
- Technical search against a *small, manually curated* set of designs (30–50 models, not a full pilot database)
- One working path from technical query → matching designs → outbound link or manual listing check for current examples
- A way to measure whether target users actually complete this flow and come back

**Useful but later:**
- Accounts/login, saved searches, favorites (useful for retention, irrelevant until you know anyone returns)
- Multiple marketplace adapters (one is enough to test the mechanic)
- Field-level provenance UI, conflict states
- Comparison ratios beyond the 1–2 most requested

**Remove unless evidence demands it:**
- Alerts / background matching system (a whole subsystem built on an unproven retention loop)
- Short-lived market cache and source-health monitoring (premature infrastructure for a product with no confirmed adapter yet)
- Monetization hooks (nothing to monetize until there's usage)
- The full 14-item MVP list as currently scoped — it's a v1.0 product roadmap, not an MVP

**Smallest version that tests the central hypothesis in weeks, not months:** a static or lightly-dynamic search tool over ~30–50 hand-entered designs (reuse open CC0 data from sailboat-database.com/Wikidata as a starting point rather than re-researching from scratch), with results linking out to a pre-filled marketplace search (no adapter, no scraping) for the matched models. Ship it to 20–30 people who are actively boat-shopping right now (forums, owners' associations), and measure: do they use the technical filters at all, do they click through to listings, do they come back. That is a 1–3 week build, not the multi-phase roadmap in §16 of the brief — and it tests the demand question *before* any data-acquisition or marketplace-access investment.

---

## 9. Monetization

**Critique of the proposed models:** both "restrained marine advertising" and "affiliate/referral" are stated as *hoped-for*, not confirmed, and the brief is honest about that. The bigger problem is sequencing: monetization hooks are listed as an MVP-phase item, which is premature — there's no audience or usage data yet to sell against, and (per §7) no confirmed affiliate/referral terms from the marketplaces this depends on.

**Ranked plausibility, strongest to weakest, for this kind of product:**

1. **Broker leads / referral fees** — brokers have clear ROI on qualified leads and a long history of paying for them (this is literally YachtWorld's existing business model). Who pays: brokers. Why: a lead from a technically-qualified buyer is worth more than a generic one. When: per lead or monthly. Must be true: HullQ needs enough qualified traffic to be worth a broker's attention, and brokers need to see HullQ as complementary to (not competing with) their existing listing spend.
2. **Marine-industry advertising** (insurance, surveyors, riggers, sailmakers) — plausible but low-value-per-user in a low-frequency-use product; advertisers pay for reach and intent, and HullQ's traffic will be small and episodic for a long time. Works best once there's meaningful recurring traffic, not before.
3. **Affiliate/referral to marketplaces** — plausible in theory, but per §7, none of the major marketplaces have documented public affiliate programs, and this needs source-by-source verification the brief itself flags as unverified. Treat as unconfirmed, not as a revenue line.
4. **Premium alerts / paid buyer subscription** — weak. The core user does this search once every several years; subscription only works with a much broader, more frequent-use product than "sailboat design + listing search."
5. **B2B data/API access** (selling the design database itself) — weak given §3/§6: the data isn't differentiated enough yet to sell, and there are already free/open alternatives a buyer of such an API could use instead.
6. **Sponsored placement / marketplace partnerships** — speculative; requires HullQ to have enough traffic/credibility to be worth a marketplace's attention, which is a late-stage outcome, not a starting plan.

**Direct statement:** monetization is likely weak *until* there is proven recurring usage and either (a) confirmed broker willingness to pay for leads or (b) confirmed marketplace partnership terms — neither of which currently exists. I would not build monetization hooks in the MVP; I'd validate usage first, then have direct conversations with 3–5 brokers about lead value before writing a single line of monetization code.

---

## 10. Distribution and growth

The brief is right that this is underdeveloped, and it's a serious gap given §3's finding that the SEO-obvious play (long-tail model/spec pages) is already occupied by a competitor with a decade of domain authority and 9,000+ indexed pages.

- **SEO from model/design pages:** likely expensive and slow to compound against SailboatData's existing rankings — not a reliable early channel. Possible niche wedge: pages for specific *technical combinations* (e.g., "shoal draft skeg-rudder cruisers under 11m") that no existing site targets as a page, rather than competing head-on for individual model names.
- **Sailing communities/forums, owners'/class associations:** the most plausible early channel — this is where the actual early-adopter (§1) already spends time, and it's where credibility is built cheaply. Likely to compound slowly via word of mouth among a small, tight-knit community.
- **YouTube/content:** effective for boat content generally, but production-heavy and better suited to a team with sailing-media production capability than a lean technical MVP.
- **Broker partnerships:** double-edged — could be a growth *and* revenue channel (§9) if brokers see lead value, but brokers have limited incentive to help a tool that could eventually disintermediate their own site traffic.
- **Newsletters/saved-search alerts:** this is a retention mechanic, not an acquisition channel, and depends on the alert system actually working (§7's biggest risk).
- **Paid acquisition:** unlikely to pay back given the low frequency of use and unproven monetization — avoid until unit economics are understood.

**Channels likely to compound:** community/association word-of-mouth, and possibly a narrow SEO wedge on uncontested technical-combination queries.
**Channels likely to be expensive/ineffective early:** head-on model-name SEO, paid acquisition, content/video production.

---

## 11. Target customer

**Best initial segment: the repeat/experienced cruising-sailboat buyer who has already rejected browsing by brand** — typically someone upgrading from a first boat, often 40+ years old but not necessarily, who has specific requirements from real sailing experience (draft for a home marina, a construction type they trust, a keel/rudder configuration they've decided matters to them) and who is already cross-referencing manually.

- **Situation:** actively searching, weeks to months into the process, frustrated by marketplace filters that don't express what they actually care about.
- **Current behavior:** SailboatData/Boat-Specs open in one tab, YachtWorld/Boat24/local marketplaces in another, forums for opinions, a personal spreadsheet.
- **Why HullQ helps them specifically:** it removes the manual cross-referencing step — *if* the listings layer actually works (§7).
- **Where reachable:** owners'/class associations, sailing forums (Cruisers Forum, national sailing forums), regional sailing clubs — not general boating media.
- **First-use query:** something like "shoal draft, encapsulated or long keel, skeg-hung rudder, 10–12m, moderate-to-heavy displacement, under €120k" — a multi-constraint technical query, not a brand name.
- **What brings them back:** a genuinely new listing surfacing that matches their saved criteria — which depends entirely on the alert/matching system working across enough of the market to matter.

**Secondary segments that should wait:** (1) first-time buyers (need education, not filters — wrong product); (2) brokers/dealers as a customer segment (they're a monetization target, not the initial user); (3) racing-boat buyers (different, more class-rule-driven search behavior than the cruising-technical-spec workflow this product is built around).

---

## 12. Success probability

These are judgment estimates, not statistical ones, and depend on the assumptions stated with each.

- **Problem is real enough for meaningful recurring usage:** ~30–40%. Assumption: "recurring" is doing a lot of work here — even if the problem is real, it's structurally low-frequency per user (§2), which caps "recurring usage" regardless of product quality.
- **A useful independent data foundation can be built economically:** ~55–65% *for a small, market-relevant subset*; materially lower for the full 2,000+ vision, because §3/§6 shows most of the value is already available for free/open, which undercuts the economic case for parallel independent research at scale.
- **Sufficient market integrations can be maintained:** ~20–30%. This is the weakest link given §7's finding that no target marketplace offers third-party pull access, and maintenance burden compounds with each adapter.
- **Reaching a small sustainable niche business:** ~20–25%, conditional on radically narrowing scope (§8) and getting real demand signal before building the database/adapters as currently planned.
- **Becoming a materially larger business:** ~5%. The addressable frequency-of-use ceiling (§2, §11) and the marketplace-access constraint (§7) cap this regardless of execution quality; this looks structurally like a small-niche-tool outcome at best, not a venture-scale one.

---

## 13. Falsification plan

Prioritized to spend money/time only after each prior step survives.

1. **Hypothesis:** experienced buyers actually search by technical characteristics before/instead of brand. **Method:** 15–20 structured interviews with people who bought a cruising sailboat in the last 12 months, sourced from owners' associations/forums. **Cost:** days, ~€0. **Success:** majority describe a technical-first workflow unprompted. **Failure:** majority describe brand/price/location-first behavior even when they had technical opinions. **Decision:** failure kills the core premise before any building.
2. **Hypothesis:** a technical query with no known model name is a common real search pattern. **Method:** analyze search-query data/threads on forums and, if possible, search-term data from an existing spec site (even informally, e.g. what people ask in "help me find a boat" forum threads). **Cost:** days. **Success:** frequent unprompted "I want X characteristics, don't know what model" threads. **Failure:** most requests already name candidate models. **Decision:** informs how much emphasis to put on "discovery" vs. "confirmation" search modes.
3. **Hypothesis:** a bare-bones tool (30–50 models, outbound links, no adapter) gets used and revisited. **Method:** ship the minimal MVP from §8 to the interview participants plus forum recruits. **Cost:** 1–3 weeks build + light outreach. **Success:** meaningful % return within 30 days or refer someone else. **Failure:** one-time use, no return visits. **Decision:** failure means the "notify me" retention loop is unlikely to save the product either — reconsider before building alerts.
4. **Hypothesis:** at least one marketplace will give usable partner/API/affiliate access. **Method:** directly contact Boat24, TheYachtMarket, and 1–2 regional players (small players more likely to cooperate than YachtWorld) about data-partner or affiliate terms. **Cost:** days, a handful of emails/calls. **Success:** at least one workable agreement in principle. **Failure:** universal refusal or silence. **Decision:** failure forces the outbound-deep-link-only architecture (§7 alt. #1) as the permanent model, not a stopgap.
5. **Hypothesis:** manual data research cost per model is sustainable. **Method:** the 50–100 pilot, but timed honestly. **Cost:** as already planned in the brief. **Success:** cost per verified model compares favorably to simply layering onto open CC0 data. **Failure:** cost is high and coverage low. **Decision:** failure means reuse open data instead of building parallel infrastructure.
6. **Hypothesis:** brokers will value leads from this tool enough to pay. **Method:** show 3–5 brokers a mockup/prototype and ask directly what a qualified lead is worth to them. **Cost:** days. **Success:** concrete willingness-to-pay figures. **Failure:** vague interest, no numbers. **Decision:** failure means broker-lead monetization (the strongest ranked model in §9) needs rethinking too.
7. **Hypothesis:** cross-platform dedup is tractable at small scale. **Method:** manually attempt to match the same 20 boats across 2 marketplaces, measure error rate. **Cost:** a day. **Success:** low false-positive/negative rate with simple heuristics. **Failure:** high ambiguity even by hand. **Decision:** failure signals the "current boats for sale" list will look buggy/duplicated to early users regardless of engineering effort.

If steps 1–3 don't hold up, nothing downstream (database scale, adapters, monetization) is worth building as currently scoped.

---

## 14. Improvement proposals

**Five highest-impact improvements:**
1. Run the demand-side falsification (§13, steps 1–3) *before* any database-scaling work — currently the roadmap does this in reverse.
2. Reuse open/CC0 sailboat data (Wikidata/Wikipedia via sailboat-database.com's approach) as the MVP's data source instead of independent research, at least until demand is confirmed.
3. Replace the marketplace-adapter dependency in the MVP with outbound deep links — removes the single biggest legal/access risk while still testing the core mechanic.
4. Talk to brokers about lead value *before* building monetization hooks, not after building a product with no revenue plan.
5. Narrow the taxonomy/provenance ambition to what 30–50 pilot models actually require, resisting the schema completeness that the brief's own "open decisions" list shows is still unresolved.

**Three things not to build yet:** the alert/notification system; multiple marketplace adapters; field-level provenance UI for end users.

**Three potentially overlooked ideas:**
1. A **"which of these X models fits me"** confirmation mode (user already has 2–3 candidate models, wants an objective technical comparison) may be an easier, higher-intent wedge than pure characteristic-first discovery — it matches how buyers actually seem to behave (per competitor products already offering "compare" as a headline feature) more than a from-scratch discovery flow does.
2. **Owners'/class-association partnerships as a data *and* distribution channel simultaneously** — these organizations often already maintain member-verified technical data and would reach the exact early-adopter segment in §11.
3. **A "translate this listing into ratios" tool** (paste a marketplace listing, get its D/L, SA/D, comfort ratio computed and put in context) is a smaller, immediately useful utility that could seed usage and traffic while the fuller product is validated — lower build cost than the full matching engine.

**Alternative positioning:** not "a search engine for boats" but **"a technical second opinion on a boat you're already looking at"** — anchoring to the confirmation use case (idea #1 above) rather than discovery, which is a smaller promise but a much easier one to deliver and monetize (e.g., via a broker's own listing page).

**Alternative business model:** a **licensable comparison/ratio widget** brokers or marketplaces embed on their own listing pages (B2B, sold to the marketplaces themselves rather than competing with them) — sidesteps the entire marketplace-access problem in §7 by turning marketplaces into customers instead of data sources to fight.

**Alternative MVP:** a single web page: paste or select a boat model → see its computed ratios, provenance-noted specs, and 2–3 closest technical siblings, each linking out to a marketplace search. No accounts, no alerts, no adapters. Buildable in days, tests the ratio/data-quality value proposition directly.

---

## 15. Pre-mortem

**If HullQ failed after 18–24 months, the five most likely reasons:**
1. The core "technical-first" search behavior turned out to be a minority pattern, not the primary buyer workflow — usage never grew past a small enthusiast core.
2. No marketplace ever granted usable data access; the product stayed a spec database with outbound links, indistinguishable enough from free competitors that it never got traction.
3. Independent-data research cost scaled faster than the model count, and the team either stalled at a few hundred models or quietly fell back on the "reference only" scrape, creating quality/legal problems.
4. SEO/distribution never worked against SailboatData's incumbency, and no other channel compounded enough to reach sustainable traffic.
5. No one — buyers, brokers, or advertisers — was willing to pay enough, because usage stayed too infrequent per user to build any of the ranked monetization models in §9.

**If HullQ succeeded as a durable niche product, the five most likely reasons:**
1. It found and owned the confirmation/comparison use case (not pure discovery) and became the trusted "check the numbers" step for technical buyers.
2. At least one or two marketplaces became genuine data partners (rather than scrape targets), giving a real, legally clean listings layer.
3. Owners'/class associations adopted or endorsed it, giving both credible data and a compounding, low-cost distribution channel.
4. Brokers found the leads valuable enough to pay for directly, giving a real, if modest, revenue base independent of ad/affiliate uncertainty.
5. The team resisted scope creep (no route planning, no AI advisor, no community features) and kept operating cost low enough that a small, loyal niche audience was enough to sustain it.

---

## 16. Final verdict

| Dimension | Score (0–10) |
|---|---|
| Overall idea | 4 |
| Problem | 5 |
| Differentiation | 3 |
| Technical feasibility | 6 |
| Data feasibility | 5 |
| Distribution potential | 3 |
| Monetization | 3 |
| Defensibility | 3 |
| Solo/lean execution suitability | 5 |

**Overall risk:** High.

**Recommendation:** **Validate first, and narrow substantially.** Not "build as currently scoped." The current plan invests in the two hardest, least-proven pieces (independent data at scale, multi-marketplace adapters) before testing the one assumption everything else depends on: that experienced buyers actually search this way often enough, and would use this tool for it.

**Single most important next action:** run §13 steps 1–3 (buyer interviews + a 30–50-model, adapter-free MVP with outbound links) before writing any more schema, taxonomy, or adapter code.

**Single assumption most likely to kill the project:** that "I know the characteristics but not the model" is a common, active buying workflow rather than a developer/enthusiast intuition about how buyers *should* search.

**Strongest reason to build it anyway:** the keel/rudder/skeg-as-independent-fields modeling and the cross-model alert concept are genuinely useful ideas that no incumbent currently offers well — if the demand assumption survives testing, there is a real, if narrow, product here that existing free spec databases don't deliver.

---

### If this were my own money and time

No, I would not build HullQ as currently scoped. I would not touch the independent-data pipeline, the 50–100 model research pilot, or any marketplace adapter yet — all of that is investment in the parts of the idea that are either already commoditized (§3) or blocked on access I don't control (§7).

What I would build and test first: the minimal, adapter-free version from §8/§14 — a curated 30–50 model set (reusing open CC0 sailboat data rather than researching it independently), computed ratios with source notes, side-by-side comparison, and outbound deep links to marketplace searches. I'd ship that to 20–30 real, currently-shopping buyers sourced from owners'/class associations and forums within 1–3 weeks, and I would spend equal effort on 15–20 direct interviews about how they actually searched. Only if that shows real, repeated, unprompted use of technical-first search — and only after at least one honest conversation with a marketplace or broker about data access and lead value — would I put real time into the data-scaling and adapter work the current brief treats as the starting point.
