# HullQ — Prompt for Independent LLM Second Opinion

Copy the prompt below together with `EXTERNAL_LLM_REVIEW_BRIEF.md` into the LLM you want to consult. If the model supports file attachments, attach the brief and use only the prompt section below.

---

## Review prompt

You are acting as an independent product strategist, startup analyst and skeptical technical reviewer. I want a **genuine second opinion**, not validation of my existing thinking.

I will provide you with a project brief for **HullQ**, an early-stage sailboat technical-search and current-market-finder concept.

Your task is to evaluate the project from first principles. Treat the supplied brief as a description of the project, **not as proof that its assumptions are correct**.

### Review principles

- Be critical, concrete and commercially realistic.
- Do not praise the idea merely because the specification is detailed.
- Separate **good product documentation** from **evidence of product-market fit**.
- Do not assume user demand, marketplace access, data availability, legal safety, monetization or willingness to pay unless they are actually supported.
- Do not invent facts that are missing from the brief.
- Explicitly identify assumptions you are making.
- If you have web access, you may research current competitors, market structure, marketplace access, pricing/business models and comparable products. Clearly distinguish web findings from conclusions based only on the supplied brief and cite important sources.
- If you do not have web access, state where external validation is required instead of guessing.
- Challenge the project's current architecture and scope where appropriate; none of the proposed implementation choices should be treated as sacred.
- Look for reasons **not** to build it as currently conceived.
- Also look for a narrower or stronger version of the idea that may have better odds.

### Please analyze the following

#### 1. Restate the idea

In your own words, summarize:

- the user problem
- the proposed solution
- the core user journey
- who you think the actual early adopter is
- what the real value proposition is

If your interpretation differs materially from the brief's own framing, explain why.

#### 2. Problem quality

Assess:

- how painful the problem appears
- how frequently it occurs
- whether users are likely to actively seek a solution
- whether the current workaround is genuinely bad enough
- whether this is primarily a serious buyer problem, an enthusiast problem, a broker problem, or another category

Distinguish between “interesting” and “valuable enough to support a product.”

#### 3. Differentiation and competitive position

Evaluate whether technical-characteristic-first sailboat discovery plus current-market matching is meaningfully differentiated.

Identify likely direct, indirect and substitute competitors/categories, including:

- sailboat specification databases
- yacht marketplaces
- broker search
- enthusiast forums/communities
- general search/AI-assisted research
- saved marketplace searches

Explain what HullQ would have to do substantially better for users to switch or add it to their workflow.

#### 4. Strongest parts of the concept

Rank the **five strongest elements** of HullQ and explain why each could matter commercially or strategically.

Do not include an item merely because it is technically elegant.

#### 5. Weakest parts / failure modes

Rank the **ten most serious weaknesses, risks or failure modes**.

For each, state:

- severity: low / medium / high / existential
- likelihood: low / medium / high
- why it matters
- whether it is testable before major development
- the cheapest useful test

Pay particular attention to:

- real user demand
- independent design-data acquisition
- primary-source completeness
- taxonomy complexity
- variants/generations
- field-level provenance cost
- marketplace/API/scraping dependency
- listing deduplication
- alert freshness
- legal/platform risk
- maintenance burden
- SEO/distribution/customer acquisition
- monetization

#### 6. Data moat analysis

Assess the independent `BoatDesign` database as a potential asset.

Answer explicitly:

- Is it likely to become a defensible moat, a useful operational asset, or merely expensive table stakes?
- How much completeness is actually necessary before the product becomes useful?
- Is provenance at field level strategically valuable, or is the project overengineering it too early?
- Is the proposed 50–100 model corpus the right **research-pipeline benchmark** (not product database), and what should it measure before broad ingestion?
- What metrics should decide whether to continue, change approach or stop?
- Would you build the database breadth-first, market-demand-first, manufacturer-by-manufacturer, segment-first, or another way?

#### 7. Market integration analysis

Evaluate the live/on-request marketplace-adapter strategy.

Address:

- whether it is the right architecture for an MVP
- dependence on external platforms
- what happens if major platforms block or restrict access
- whether one marketplace is enough to prove value
- whether HullQ still has a viable standalone product if market integration is weak
- alternative integration strategies such as partnerships, feeds, outbound deep links, broker inventory, user-submitted listings, or other approaches

Do not assume a particular integration is legally or technically available without evidence.

#### 8. MVP critique

Review the current MVP and classify every major capability into:

- **must have for first validation**
- **useful but later**
- **remove unless evidence demands it**

Then propose the smallest version of HullQ that can test the central business hypothesis in weeks rather than becoming a long infrastructure project.

Be willing to recommend a dramatically smaller MVP.

### Important retention premise to test, not dismiss by assumption

Do not equate low per-person sailboat purchase frequency with low HullQ retention. The project hypothesis is that many sailors continue watching the market while already owning a boat and may keep persistent technical monitors active for curiosity, upgrades or rare opportunities. Critique this hypothesis and propose evidence to test it, but do not assume `boat purchased = user churn`.

Current freemium hypothesis:

- Free: search everything, save 5 searches, monitor 2
- Plus: monitor 10 technical searches across supported markets
- Pro: advanced monitoring, faster alerts, price tracking/history intelligence, larger limits (only where source rights and OQ-017 allow historical retention)

Exact prices/limits are not fixed. Evaluate whether persistence/monitoring is a credible subscription lever and what packaging would maximize useful free discovery without giving away all ongoing monitoring value. Treat asking-price history as observed listing data, not achieved sale-price data; disappearing listings are not automatically sales.

#### 9. Monetization

Critique the proposed advertising / affiliate / referral / partnership ideas.

Then rank the most plausible revenue models from strongest to weakest, considering examples such as:

- direct marine-industry advertising
- affiliate/referral
- broker leads
- paid buyer subscription
- premium alerts
- B2B data/API access
- broker/dealer tools
- sponsored placement
- marketplace partnerships
- freemium
- other models you identify

For each plausible model, explain **who pays, why they pay, when they pay, and what must be true for it to work**.

If you believe monetization is likely to be weak, say so directly.

#### 10. Distribution and growth

The current project material is stronger on product/data architecture than on acquisition. Fill that gap critically.

Assess likely acquisition channels such as:

- SEO from model/design pages
- long-tail technical search pages
- sailing communities/forums
- YouTube/content
- broker partnerships
- yacht clubs / class associations / owner associations
- newsletters and saved-search alerts
- word of mouth among serious buyers
- paid acquisition

Identify which channels could plausibly compound and which are likely to be expensive or ineffective.

#### 11. Target customer

Define the **single best initial customer/user segment**.

Do not answer “all sailboat buyers.” Give a narrow segment and explain:

- their situation
- their current behavior
- why HullQ is particularly useful to them
- where they can be reached
- what first-use query they are likely to make
- what would cause them to return

Then name 2–3 secondary segments that should wait.

#### 12. Success probability

Give your own rough probability estimates, with reasoning, for:

- probability that the problem is real enough to generate meaningful recurring usage
- probability that a useful independent data foundation can be built economically
- probability that sufficient market integrations can be maintained
- probability of reaching a small sustainable niche business
- probability of becoming a materially larger business

These are judgment estimates, not statistical claims. State the assumptions behind them.

#### 13. Falsification plan

Design a sequence of **5–10 cheap experiments** intended to prove the idea wrong as efficiently as possible before substantial coding.

For every experiment include:

- hypothesis
- method
- time/cost level
- measurable success criterion
- failure criterion
- what decision follows from either result

Prioritize evidence over building.

#### 14. Improvement proposals

Give:

- the five highest-impact improvements to the current concept
- three things you would explicitly **not** build yet
- three potentially powerful ideas the current project may be overlooking
- one alternative positioning
- one alternative business model
- one alternative MVP

Only suggest additions that improve the core economics or validation speed; avoid generic feature expansion.

#### 15. Pre-mortem

Assume HullQ was built substantially as planned and failed after 18–24 months.

Write the five most likely reasons it failed.

Then assume it succeeded as a durable niche product. Write the five most likely reasons it succeeded.

#### 16. Final verdict

End with a compact decision memo containing:

1. **Overall idea score:** 0–10
2. **Problem score:** 0–10
3. **Differentiation score:** 0–10
4. **Technical feasibility score:** 0–10
5. **Data feasibility score:** 0–10
6. **Distribution potential score:** 0–10
7. **Monetization score:** 0–10
8. **Defensibility score:** 0–10
9. **Solo/lean execution suitability:** 0–10
10. **Overall risk:** low / medium / high / very high
11. **Recommendation:** build / validate first / pivot narrower / do not pursue
12. **The single most important next action**
13. **The single assumption most likely to kill the project**
14. **The strongest reason to build it anyway**

Then give a final answer to this question:

> **If this were your own money and your own time, would you pursue HullQ now? If yes, exactly what would you build/test first; if no, what would you do instead?**

Do not soften the conclusion for politeness.
