# Product Scope

> **Superseding Owner product-scope direction — 2026-10-22:** HullQ's long-term product is a **single native marketplace for Sail + Power**, with **full category-specific technical discovery for both** (Sail first as validated reference; Power subsequently developed to equivalent epistemic quality) and equally important category-neutral Broker Excellence. Statements below that define HullQ permanently as Sail-only or not a native marketplace are historical; current accepted native-marketplace direction and [this new explicit Owner decision](HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md) control those narrow conflicts. The present Sail-first *implementation* scope remains in effect internally until reviewed Power implementations are accepted; **there is no Sail-only external prelaunch**. The Owner expressly requires a **joint Sail+Power initial product launch** with both substantive technical-search experiences ready. Market research and internal testing remain allowed; complete global design-model coverage is not required, and attributed broker facts about specific listed boats may inform honest search outcomes under separately approved evidence rules. No new release, slice, provider right or external broker upload is authorized.

## Product identity

HullQ is a technical sailboat discovery engine and market finder. It is neither a Sailboatdata clone nor another listing marketplace.

### User problem

Existing marketplaces usually assume the buyer already knows a make/model or expose shallow marketplace-specific filters. HullQ reverses this:

1. Define the boat by characteristics.
2. Find matching designs/models.
3. Search current sales platforms for those designs.
4. Compare, save and monitor.

### Value proposition

**Find the right boat even if you do not know its name yet.**


## Database breadth requirement

HullQ's unknown-model discovery experience requires a broad sailboat design universe. A 50–100 model dataset is only suitable for research-pipeline benchmarking and is not considered a valid product MVP dataset.

The production dataset may be progressively enriched: broad identity/basic coverage comes first, HullQ-critical fields are prioritized next, and deep primary-source verification grows over time. Sparse records are acceptable; unknown fields must remain explicitly unknown and must not be treated as negative facts during search.

## MVP

### In scope

1. Independent broad BoatModel/BoatDesign design universe
2. Technical search
3. Curated keel/rudder/skeg taxonomy
4. Monohull + catamaran + trimaran support
5. Model results
6. Compare
7. Current-market search
8. Accounts/login
9. Saved technical queries
10. Favorites
11. Alerts
12. Source-permitted market caching where required for performance/reliability (policy gated by OQ-006/OQ-013)
13. Basic source-health monitoring
14. Configurable freemium/subscription entitlement hooks

### Out of scope

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

## UX direction

Do not generate filters automatically from raw source metadata. Build a curated filter UI against the canonical schema.

Primary filters: LOA, year, hull configuration, keel, rudder/skeg, draft, displacement and material.

Advanced groups: Dimensions; Hull & Construction; Keel / Rudder / Skeg; Rig; Ratios; Engine / Tanks; Designer / Builder.

Comparison is a first-class workflow. Transparent presets are acceptable; an opaque generic “Bluewater Score” is not part of the current product.


## Persistent market watch and monetization

HullQ explicitly serves not only active buyers but also owner-watchers and opportunity hunters who continue following the market after a purchase. Purchase frequency MUST NOT be used as a direct proxy for product retention without evidence.

The preferred monetization direction is freemium: keep core technical search open, limit saved-query/monitor capacity on Free, and monetize larger/faster/more capable monitoring through Plus/Pro. See `docs/PRODUCT_RETENTION_AND_MONETIZATION.md`.
