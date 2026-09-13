# HullQ — Broker Workspace Product Direction

**Date:** 2026-09-13  
**Status:** ACCEPTED OWNER DIRECTION  
**Scope:** broker/dealer/professional supply-side product, excluding visual-design implementation details  

## 1. Product thesis

HullQ is not allowed to treat the broker workspace as a secondary admin panel.

The broker workspace is one of HullQ's two core product surfaces:

```text
Buyer side  -> best-in-class technical discovery / trustworthy inventory
Broker side -> best-in-class inventory, lead and sales operating workspace
```

The strategic objective is that a professional broker should prefer working in HullQ because common work is faster, clearer and more informative than in incumbent broker platforms.

The operating principle is:

> A broker should never have to enter information twice, search for information HullQ already knows, or wonder what happened to a lead.

This is a product requirement, not merely a UI aspiration.

## 2. Competitive standard

HullQ must explicitly benchmark the broker workflow against leading broker-marketplace products, including Boats Group / YachtWorld / BoatWizard where accessible and relevant, and against direct feedback from real brokers.

The objective is not feature parity for its own sake. HullQ must be materially better on the jobs brokers repeat every day:

- create a listing;
- complete missing yacht-specific facts without retyping known design data;
- upload/reorder/replace media;
- change price and availability/status;
- duplicate/relist/reuse prior inventory where semantically valid;
- find, qualify, assign and follow up a lead;
- understand exactly where a lead came from;
- see listing and lead performance;
- record an offer/sale outcome;
- trace source -> lead -> broker action -> outcome.

Before the Broker Workspace Launch Gate may become PASS, HullQ must have repository-backed usability evidence for these core tasks and an explicit comparison against the selected incumbent benchmark set.

## 3. Friction budget: listing creation must be exceptionally fast

Listing creation is a primary acquisition surface. Excess friction directly reduces inventory quality and broker willingness to participate.

Required direction:

```text
known BoatDesign/configuration data
        +
broker's concrete-yacht facts
        +
offer facts / media
        v
publishable NativeListing
```

HullQ must reuse trustworthy data already known at BoatDesign/configuration level while preserving the hard rule that design truth is not concrete-yacht truth. Known design information may pre-populate/reference the workflow; concrete-yacht facts that require broker assertion must remain explicit broker claims.

The workspace must ultimately support, where applicable:

- intelligent prefill from accepted HullQ design/configuration data;
- clear distinction between inherited/reference data and yacht-specific asserted facts;
- autosave and resume without data loss;
- progressive completion rather than one giant blocking form;
- keyboard-efficient desktop operation;
- responsive/mobile-friendly editing for practical broker use;
- drag/drop and bulk media upload;
- rapid media ordering and cover-image selection;
- duplicate/clone/relist workflows without unsafe identity copying;
- reusable broker/office defaults;
- bulk operations where they reduce repetitive work without weakening truth;
- import/feed paths later, without making manual workflow second-class.

A later usability benchmark must measure real task time and interaction count. The gate must not PASS solely because all fields technically exist.

## 4. No duplicate work

If HullQ already possesses a value or relationship that can be safely reused, the broker should not be asked to type it again.

This does not authorize silent truth-scope collapse.

Examples:

- canonical design dimensions may be displayed or reused as design context;
- a broker must explicitly assert a concrete yacht's field where concrete-yacht truth is required;
- Organization details and contact defaults should be reusable across listings;
- previous listing content may be cloned only where identity/lifecycle rules make reuse safe;
- media, equipment and descriptive content should support deliberate reuse when rights and identity allow it.

The system should optimize for minimum repeated human input while keeping provenance, ownership and truth boundaries explicit.

## 5. State model: publication, freshness, deal state and sales outcome are separate

HullQ must not overload one `status` field with unrelated meanings.

At minimum the eventual broker product must distinguish:

```text
publication/lifecycle state
freshness/reconfirmation state
commercial/deal pipeline state
sale/outcome state
```

Examples of future commercial states may include enquiry, qualified, viewing, offer/negotiation, under offer/pending and closed/lost, but exact taxonomy must be specified in the owning slice rather than silently invented by UI code.

Likewise, future sale completion must support explicit outcome information without inferring a sale merely from disappearance or withdrawal.

Important future sales information includes, where lawful/applicable and explicitly provided:

- sold/closed date;
- asking price at relevant points;
- achieved sale price when available and permitted;
- currency;
- responsible broker/office;
- originating lead/source when attribution is supportable;
- outcome reason / lost reason where useful;
- Days on Market and price-change history derived from valid events rather than manual guesswork.

`STALE`, `WITHDRAWN`, `SOLD`, `UNDER_OFFER` and `ARCHIVED` must never be treated as synonyms.

## 6. Lead is a first-class HullQ product object

A lead must not be reduced to an email notification.

The target domain relationship is conceptually:

```text
Lead / ContactRequest
  -> buyer / contact identity where available
  -> NativeListing
  -> PhysicalBoat / MarketEpisode context
  -> publishing Organization
  -> assigned broker/account
  -> acquisition source / channel / campaign context
  -> event timeline
  -> pipeline/status
  -> eventual outcome where known
```

A lead record must be durable enough to support attribution, assignment, follow-up, response-time analytics and later sales/outcome analysis.

The first implementation may be intentionally bounded, but the architecture must not throw away information required for later attribution or outcome analysis.

## 7. Lead attribution is launch-critical

HullQ must preserve where a lead came from.

Attribution should support, as applicable:

- HullQ listing and listing ID;
- technical Search/query context that led to the listing;
- landing/referring surface;
- channel/request type;
- first-touch source;
- lead-creation/conversion source;
- UTM/campaign parameters where present;
- referrer where privacy/security policy permits;
- timestamp;
- locale/device class when useful and privacy-compatible;
- future email/phone/call-tracking provider identifiers where such channels are introduced.

Attribution must distinguish immutable captured acquisition facts from later interpretation/reporting.

The broker should be able to answer, without external spreadsheet work:

```text
Where did this lead come from?
Which listing generated it?
Which campaign/search/referrer produced it?
Who handled it?
How quickly did we respond?
What happened afterwards?
Did it become an offer or sale?
```

## 8. Broker lead workspace / lightweight CRM

HullQ should not attempt to become a universal enterprise CRM at launch, but the broker workspace must provide the core workflow needed to act on HullQ-generated demand.

Launch-critical direction includes:

- lead inbox/queue;
- lead detail with complete source context;
- assignment to broker/team member;
- status/stage;
- notes/timeline;
- follow-up indicator/task support sufficient to avoid forgotten leads;
- response-state and response-time measurement;
- qualified/unqualified and lost-reason handling where useful;
- filtering/searching by listing, source, broker, office and status;
- auditability of important state changes.

Direct communication may still move outside HullQ where appropriate; HullQ must nevertheless retain enough event/outcome truth to show what happened to the lead.

## 9. Broker analytics must answer business questions, not just show vanity metrics

The broker dashboard must evolve toward an understandable funnel such as:

```text
inventory exposure
-> listing views
-> leads/contact requests
-> qualified leads
-> viewings / negotiations / offers where recorded
-> sold/closed outcomes
```

The exact event model will be specified in bounded implementation slices, but the product must ultimately support analysis by:

- listing;
- broker/account;
- office/Organization;
- source/channel/campaign;
- time period;
- model/design/category where useful;
- outcome.

Useful operational measures include:

- listing views and contact conversion;
- lead volume and lead quality indicators;
- lead source mix;
- response time;
- assignment/follow-up backlog;
- Days on Market;
- price changes;
- under-offer / sold outcomes;
- source-to-sale conversion where evidence exists.

HullQ must clearly distinguish observed facts from inferred analytics.

## 10. Sales completion is strategically valuable data

The broker workflow should make closing a listing properly easier than abandoning it.

A completed sale/outcome creates value for:

- inventory accuracy;
- broker reporting;
- attribution;
- future pricing intelligence;
- market-trend products;
- Days-on-Market analysis;
- conversion measurement.

The UX should therefore encourage explicit close-out through a short, useful workflow rather than an administrative burden.

HullQ must not require an achieved sale price when the broker cannot or will not provide it. Missing sales data remains explicit unknown.

## 11. Authentication, authorization and Organization context

The accepted architecture remains controlling:

- Auth0 Public Cloud EU is authentication-only;
- HullQ owns Account IDs, Organizations, Memberships, roles, listing ownership, verification and authorization;
- privileged publishing requires MFA, preferably passkeys/WebAuthn where available;
- high-risk changes use step-up authentication where required;
- authorization is enforced server-side, not trusted to dashboard UI state.

The dashboard must support multi-user broker Organizations and eventually office/team-level workflows rather than assuming one account equals one brokerage.

## 12. Payments and entitlements

Payments/subscriptions may monetize broker capabilities later, but payment implementation must not be used to justify a weak broker product.

Before HullQ activates a paid broker plan, the Broker Workspace Launch Gate must be PASS.

Entitlements should be capability/data-driven and must not fragment core inventory management into unusable artificial restrictions.

Commercial packaging remains a separate product decision; this direction only requires that the broker workspace be sufficiently strong to justify professional use and, where chosen, payment.

## 13. Implementation workstream

This direction is expected to require multiple bounded slices rather than one oversized "broker dashboard" slice.

Likely capability families include, subject to normal post-slice reassessment:

1. Auth0 login/session + HullQ Account bridge;
2. persistent Organization/Membership/role/authorization workflow;
3. broker inventory workspace and low-friction create/edit/publish operations;
4. media workflow;
5. expanded publication/deal/sales/outcome state model;
6. lead/contact persistence and delivery;
7. lead attribution/source context;
8. lead assignment/pipeline/follow-up;
9. broker analytics/performance reporting;
10. payment/subscription/entitlement capability where monetization is activated;
11. usability/performance hardening against the broker benchmark.

This list is a workstream map, not authorization to combine all capabilities or preassign future slice numbers. The ONE-CAPABILITY rule and normal readiness review remain controlling.

## 14. Hard launch position

HullQ must not publicly launch a professional broker marketplace while the supply-side product is merely an internal/admin CRUD screen.

The separate `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md` is a hard product gate.

It must be PASS before:

- first real external broker self-service production pilot;
- activation of a paid broker plan/subscription;
- public production launch;

whichever occurs first.

The gate is intended to ensure that authentication, inventory workflow, state/outcome handling, lead attribution/management and evidence-backed usability quality are actually delivered rather than remaining roadmap prose.

## 15. Controlling product principle

> **HullQ wins professional supply only if brokers can list faster, understand every lead, manage follow-up and outcomes with less friction, and see clearer source-to-sale performance than they can in incumbent marketplace tooling. The broker workspace is therefore a core HullQ product and a launch condition, not back-office software.**
