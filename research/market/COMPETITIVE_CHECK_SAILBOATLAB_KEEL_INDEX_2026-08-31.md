# Competitive check — SailboatLab + Keel Index

**Date:** 2026-08-31  
**Status:** bounded competitive research; non-authorizing for automated access; not a legal finding  
**Purpose:** answer three business-critical questions raised after the Listings Port review without interrupting SLICE-0038 or reopening the Product Execution Plan.

## Scope and stop rule

This check answers only:

1. Do SailboatLab or Keel Index publicly demonstrate configuration-specific **physical-listing truth**?
2. How do they treat technical constraints / matching?
3. How do they appear to acquire current listings and monetize?

This is a competitive-product check, not a rights audit or teardown. Public claims are recorded as observed; internal implementation is not inferred beyond what the public surfaces support. No new HullQ live source is authorized by this document.

---

# 1. SailboatLab

## Public product position

SailboatLab currently positions itself as **buyer-side intelligence for boats**. Its product flow is explicitly two-stage:

1. compare sailboat **models/designs** against a sailing program;
2. use a premium AI **Market Analyst** to find and evaluate individual boats currently for sale.

Its help material explicitly distinguishes:

```text
sailboat model = generic design characteristics, typically manufacturer-provided
sailboat ad    = a specific instance of the model, typically seller-described
```

This is a material competitive fact: HullQ cannot claim that the conceptual distinction between a generic design and a specific advertised boat is unique by itself.

Public surfaces reviewed:

- `https://www.sailboatlab.com/`
- `https://www.sailboatlab.com/agents/help/`
- `https://www.sailboatlab.com/agents/premium/`
- representative comparator/use-case pages and data sheets.

## Question 1 — configuration-specific physical-listing truth?

**Public finding: not established.**

SailboatLab says its Market Analyst scans broker/marketplace listings, structures them, evaluates equipment/maintenance, reconciles them with its model database, and allows user-added information such as negotiated price, broker feedback and survey findings to update the evaluation.

However, the public Premium description also says:

> each advertisement is evaluated not only by its description, but also by the known characteristics of the sailboat model.

That can be useful for contextual evaluation, but it is materially different from HullQ's intended physical-listing invariant if model facts are allowed to stand in for facts about the concrete boat. The public material reviewed does **not** demonstrate a field-level rule equivalent to:

```text
factory/design configuration exists
!=
this physical listing is confirmed to have that configuration
```

Nor was a public per-field evidence state found equivalent to:

```text
TRUE / FALSE / UNKNOWN / CONFLICT
+ concrete listing observation
+ provenance
+ configuration scope
```

This is an absence of public evidence, not a claim about SailboatLab's private implementation.

### Data-quality signal relevant to HullQ

Representative SailboatLab data sheets expose missing/unknown-looking fields as numeric zero plus `??` in several places. Examples observed on Salona 38 include `Air draft 0 ft`, `Headroom 0 ft`, `Last built 0` and `Number built 0`; other sheets show similar zero values for rig dimensions, tankage or ballast when unavailable.

The Salona 38 page also states that data comes from different sources and that a significant part is attributed to SailboatData, thanking it for encouragement/friendly collaboration.

**HullQ consequence:** zero-as-missing must never silently become physical truth or satisfy a numeric constraint. HullQ's existing reserved UNKNOWN/MISSING semantics remain a substantive product difference, not documentation ceremony.

## Question 2 — hard technical constraints?

SailboatLab's free comparison engine is primarily **fitness/scoring based**. Public documentation shows color-coded per-requirement and global scores:

- Green: 75–100%
- Blue: 50–75%
- Orange: 25–50%
- Red: 0–25%

Its predefined low-draft use case states that minimum draft must not exceed 1.5 m and presents 123 matching boats, while also ranking candidates by broader comfort/performance fit. This suggests SailboatLab can combine at least some eligibility bounds with fuzzy/relative scoring.

The reviewed public surface does not establish a general fail-closed contract for arbitrary hard numeric/categorical constraints, exact negation, configuration scope or explicit UNKNOWN handling comparable to HullQ's intended Search kernel.

**HullQ consequence:** scoring and recommendation can later exist as a layer **after** eligibility/truth, but they must never weaken an accepted hard requirement. A future HullQ recommendation layer may rank confirmed/eligible candidates; it must not convert `1.61 m` into a match for `Draft <= 1.60 m` or turn missing evidence into a probable fit.

## Question 3 — listing acquisition and monetization?

Public SailboatLab material says its Market Analyst:

- monitors leading broker sites and marketplaces globally;
- scans the market on demand / continuously monitors new listings;
- gathers listings from dozens of broker websites into one view;
- interprets ads regardless of language;
- links back to broker listings.

The exact acquisition mechanisms, permissions, source list and contractual rights were not established in this bounded check and are deliberately not inferred.

Monetization is explicit: Market Analyst access uses **tokens**. At the reviewed beta stage:

- a scan uses 10 tokens;
- each found/analyzed ad uses 5 tokens;
- example: 10 analyzed ads = 60 tokens;
- beta was limited to 100 users and showed its quota as reached.

The actual currency price per token was not established from the reviewed public pages.

### Strategic significance

SailboatLab is functionally closer to HullQ than Listings Port because it already combines:

```text
technical model comparison
+
individual market ads
+
buyer profile
+
AI evaluation
+
monitoring
```

Therefore HullQ's defensible differentiation must be stated more strictly:

> **Evidence-backed field truth tied to the relevant BoatDesign/configuration and, where claimed, to the physical listing — with deterministic hard constraints, explicit UNKNOWN/conflict states and auditable provenance.**

`Design vs ad` alone is not a moat claim.

---

# 2. Keel Index

## Public product position

Keel Index is currently a broad sailboat reference/market/data product. Public pages observed approximately:

- 7,852+ production sailboats in its directory;
- 12,600+ documented passages;
- live sailboats-for-sale surfaces;
- market price estimates and historical tracked listings;
- model comparison and technical subpages;
- `Watch this boat` monitoring / email alerts;
- direct owner listings advertised as free/no-fee/no-commission.

Public surfaces reviewed include:

- `https://keelindex.com/`
- `https://keelindex.com/boats`
- representative model/for-sale pages;
- technical category pages such as `/for-sale/keel/full-keel`;
- data-driven articles and passage pages.

## Question 1 — configuration-specific physical-listing truth?

**Public finding: not established.**

Keel Index often represents model-level complexity better than a single naive spec. For example, its Tartan 37 page displays both minimum and maximum draft and describes the keel/centerboard arrangement plus a deep-fin option.

However, the reviewed public listing surfaces do not demonstrate field-level proof that a particular physical advertisement has a particular factory configuration. The model page and the current market listing layer remain distinct surfaces, but no public evidence contract equivalent to HullQ's physical-listing TRUE/FALSE/UNKNOWN boundary was found.

This is an absence of public evidence, not a claim about internal implementation.

## Question 2 — hard technical constraints?

Keel Index exposes useful structured discovery surfaces — for example `Full-Keel Sailboats for Sale` — and standard model/builder/length search and comparison. The full-keel page explicitly groups current listings by models classified as full/long keel.

The reviewed public product did **not** expose an arbitrary multidimensional technical query engine with the same semantics HullQ is building. Keel Index is therefore a strong reference/market/discovery competitor, but not public proof that deterministic configuration-aware hard-constraint search over arbitrary criteria has been solved.

**HullQ consequence:** Keel Index is an especially useful benchmark for page usefulness, market presentation and data studies; HullQ should not imitate it by weakening its exact Search semantics into broad category membership.

## Question 3 — listing acquisition and monetization?

Keel Index publicly identifies multiple listing sources on current market pages. Depending on the page, observed source labels include:

- Craigslist;
- eBay;
- Apollo Duck;
- SailboatListings;
- YachtWorld;
- Boat24.

Its data-story notes explicitly describe snapshots/aggregation from public marketplace listings and distinguish asking prices from achieved sale prices. Pages state that listings refresh daily and link users to the original ad.

This bounded competitive check does **not** determine the contractual/automated-access rights for those sources and does not authorize HullQ to copy Keel Index's acquisition approach.

Visible monetization is comparatively light:

- direct boat listings are advertised as free/no fees/no commission;
- the site describes itself as free/no-paywall;
- its book library discloses Amazon Associate affiliate earnings.

No dominant paid subscription comparable to SailboatLab's Market Analyst was established from the public surfaces reviewed.

## Keel Index as SEO benchmark

Keel Index is the strongest useful SEO benchmark found in this pass because its best pages are built from **unique datasets rather than generic prose**.

A representative article, `The Cheapest Sailboats That Have Actually Crossed Oceans`, crosses:

```text
12,000+ documented passages
+
current asking-price/listing observations
=
original buyer-relevant data story
```

and cites passage evidence while showing listing counts and warning where sample size is small.

Other public surfaces combine model identity, market observations, prices, passage records, current listings and related technical categories. This supports a HullQ principle:

> **unique HullQ data -> unique insight -> useful indexable page**

rather than:

> keyword -> generic AI article -> loosely related results

### Market/SEO flywheel lesson

As HullQ later gains lawful market observations, high-value organic pages can arise from the product itself, for example:

- configuration-aware shallow-draft designs with current offers;
- designs with verified skeg-supported rudders currently on market;
- market price/Days-on-Market studies by canonical design/configuration;
- technical design trends based on HullQ's provenance-aware corpus;
- comparisons promoted from observed search demand.

These are later-phase opportunities; they do not justify building market-history or SEO infrastructure before the accepted Product Execution Plan reaches those capabilities.

---

# 3. Competitive result

## What is no longer a safe moat claim

Do **not** position HullQ's uniqueness merely as:

> `design-level data vs a specific advertised boat`

SailboatLab publicly makes that conceptual distinction already.

## Stronger working differentiation hypothesis

The current, testable HullQ differentiation is:

```text
broad lawful market coverage
+
exact canonical BoatDesign identity
+
configuration-aware facts
+
physical-listing field proof when making listing claims
+
deterministic hard constraints
+
explicit UNKNOWN / conflict states
+
auditable provenance
+
clear UX explaining what was applied and why
+
saved search / fit-confirmed monitoring
```

This remains a **hypothesis to validate with real buyers**, not a marketing claim to publish before Gate 1.

## Competitive roles

- **Listings Port:** benchmark for breadth, aggregation, dedup/history and observed Search/identity/configuration failure cases.
- **SailboatLab:** closest benchmark for buyer-side design-to-market intelligence, AI listing evaluation and monitoring.
- **Keel Index:** strongest benchmark for data-driven SEO, model/market presentation and original dataset-derived content.

None of the reviewed public surfaces establish HullQ's intended strict per-field physical-listing evidence boundary.

---

# 4. Consequences for accepted Product Execution Plan

No phase is inserted and SLICE-0038 remains untouched.

After SLICE-0038:

- Seed Corpus selection should deliberately include multi-configuration designs and hard-constraint stress cases;
- Concierge Validation should neutrally test the user value of strict evidence/truth against existing alternatives;
- the strongest benchmark classes are now:
  1. broad aggregator/search behavior (Listings Port),
  2. personalized AI buyer scoring / design-to-ad workflow (SailboatLab),
  3. deterministic evidence-backed HullQ results;
- Keel Index informs later public/SEO execution rather than requiring a separate product phase.

Market Access research remains separate and bounded. Competitor behavior does not authorize HullQ acquisition methods.

---

# 5. Research stop

The competitive check requested during active SLICE-0038 is complete for current decision purposes.

Do not extend it into another broad competitor survey before the next Product Execution Plan gate. Reopen only if a material external fact can change the product thesis, market-access posture or validation design.
