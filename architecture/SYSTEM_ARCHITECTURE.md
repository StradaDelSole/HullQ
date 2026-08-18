# HullQ — System Architecture

**Status:** ACTIVE logical architecture; implementation technologies remain gated by open questions.

## Principle

HullQ is a technical query/search layer over a mostly static sailboat-design universe and, where access permits, external market inventory. Domain boundaries are intentionally more stable than framework choices.

## Logical components

```text
[Web / Search UI]
        |
        v
[HullQ Application/API Boundary]
   |                    |
   v                    v
[Design Domain]      [User / Monitoring Domain]
 BoatModel             Search
 BoatDesign             SavedQuery
 NamedVariant           Monitor
 DesignOption           Alert
 ResolvedConfiguration  SubscriptionEntitlement
   |
   v
[Technical Query Engine]
   |
   +----------------------------+
   |                            |
   v                            v
[Design results]       [Market Search Orchestrator]
                                |
                                +--> [Source Adapter A]
                                +--> [Source Adapter B]
                                +--> [Deep-link/partner paths]
                                |
                                v
                         [Normalize / Identity Match]
                                |
                                v
                         [Permitted cache/history]
```

Separately:

```text
[Research Queue]
→ [Independent Research Pipeline]
→ [Source / Evidence / Field Resolution]
→ [Validation / Conflict Review]
→ [Canonical Design Domain]
```

## Technology selection is intentionally unresolved

Earlier project discussion identified Strapi as a pragmatic possibility, but **no backend framework is accepted**. OQ-011 controls application/backend architecture. OQ-012 controls persistence/search technology. OQ-008 controls frontend technology. Implementation agents MUST NOT infer a framework from historical preferences.

## Core domain entities

Stable conceptual entities include:

- BoatModel
- BoatDesign
- NamedVariant
- DesignOption
- ResolvedConfiguration (derived)
- Source
- FieldEvidence / FieldResolution / DerivationRecord
- ResearchJob
- Search
- SavedQuery
- Monitor
- Alert
- SubscriptionEntitlement
- MarketListing
- SourcePlatform

Additional deployment/persistence entities MUST be introduced only when their governing decision is accepted.

## Design database

The design universe is mostly static and follows the accepted broad-coverage / progressive-depth strategy. Identity semantics are governed by `specs/IDENTITY_MODEL.v0.1.md` / ADR-0004.

BoatModel is the commercial lineage; BoatDesign is the technical production generation; independent factory choices are DesignOptions; NamedVariants are not automatically generations. Variant-sensitive search operates on derived ResolvedConfigurations rather than mutating canonical baselines.

## Provenance boundary

Canonical searchable values remain separate from source evidence under accepted OQ-004 / ADR-0006. `FieldEvidence` records source observations, `FieldResolution` records canonical decisions, and `DerivationRecord` records calculated/inherited lineage. Direct source claims must not be confused with derived values: ResolvedConfiguration values and ratios require derivation lineage, not fabricated source evidence.

## Search and SEO architecture

Search Architecture and SEO are first-class product architecture under ADR-0007 and `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`. The interactive technical-query surface and the public organic-discovery surface share canonical domain data but are not identical: arbitrary filter combinations MUST NOT automatically become an unbounded indexable URL space.

OQ-018 gates the exact public URL grammar, indexable page taxonomy, faceted crawl/index policy, rendering strategy, canonicalization/sitemaps and structured-data mapping before frontend implementation. Frontend technology selected under OQ-008 MUST satisfy these architectural requirements.

## Market access

No marketplace access method is assumed. OQ-013 must document official API/feed/partner/deep-link/automation, display and storage constraints per source before a production adapter is built.

The historical 15–60 minute cache idea is only a hypothesis. OQ-006 controls actual freshness/cadence/cache policy, and each source's rights/access terms may impose stricter rules.

## Market history / price intelligence

Pro price intelligence is a product direction, not yet a persistence permission. OQ-017 must define what observations HullQ may lawfully retain, how asking-price snapshots and listing lifecycle are represented, and how trends are computed. A disappeared listing MUST NOT be interpreted as a completed sale without supporting evidence.

## Source health

For integrations that exist, use exception-oriented monitoring such as:

- last successful run;
- error state;
- result count anomaly;
- latency;
- schema/parse failures;
- rights/access status change.

The business goal is minimal unplanned maintenance, so maintenance minutes per source are a first-class operational metric.

## Alert execution

A Monitor evaluates a persisted technical SavedQuery. It may resolve matching BoatDesign/ResolvedConfiguration candidates and then evaluate supported market sources. Alerts are events produced by Monitors; they are not the same object as SavedQuery state.

Background market logic must resolve listing identity only to the highest evidence-supported precision and must not invent generation/configuration specificity.

## Boundary guardrail

Do not add social, ownership-log, weather, route-planning, financing, insurance-comparison or generic boating-app domains to the early architecture unless a later accepted product-scope decision explicitly does so.
