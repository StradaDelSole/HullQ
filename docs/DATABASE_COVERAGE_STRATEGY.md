# Database Coverage Strategy

## Decision

HullQ should aim from the beginning to build a **broad, SailboatData-scale sailboat design universe**. Database breadth is not a vanity metric for this product: it is necessary for the core unknown-model discovery experience to work.

A user asking for a technically constrained boat should not receive a tiny result set merely because HullQ has only researched a small sample of the real design universe.

The 50–100 design research set is therefore **not the product database or launch MVP**. It is a benchmark corpus used to validate the research pipeline, taxonomy, identity handling, provenance, automation and review economics before high-throughput ingestion.

## Breadth first, depth progressively

The preferred strategy is:

```text
BROAD DESIGN UNIVERSE
thousands of canonical sailboat identities
        ↓
BASIC SEARCHABLE COVERAGE
common dimensions / dates / hull configuration where supported
        ↓
HULLQ-CRITICAL ENRICHMENT
keel / rudder / skeg / draft / displacement / material / rig / variants
        ↓
DEEP VERIFICATION
primary sources / field evidence / conflicts / rare fields
        ↓
CONTINUOUS MARKET-DRIVEN ENRICHMENT
```

Coverage and verification depth are separate dimensions. A BoatDesign may legitimately exist in production with incomplete fields if every populated value has provenance and missing fields remain explicitly unknown.

## Coverage tiers

These tiers describe dataset maturity conceptually. They are not yet mandated persistence fields.

### Tier 0 — Identity known

At minimum:

- manufacturer/brand where known
- model
- first-built hint or verified year where available
- enough identity information to avoid obvious duplicate records

Purpose: establish the broad sailboat universe and support later enrichment.

### Tier 1 — Basic searchable

Typical fields may include:

- LOA
- LWL
- beam
- draft
- displacement
- first/last built
- hull configuration

Purpose: make a large proportion of the universe discoverable by broad technical constraints.

### Tier 2 — HullQ-critical searchable

Prioritize fields that materially improve HullQ over shallow or legacy databases:

- keel type / subtype
- rudder type
- skeg type
- hull material
- construction method where reliable
- rig type
- variants / generations
- draft range
- displacement / ballast / sail area needed for approved ratios

Purpose: support the characteristic-first query engine with useful precision.

### Tier 3 — Deep verified

Includes stronger source depth and conflict handling, such as:

- primary/manufacturer documentation where obtainable
- field-level evidence
- reconciled or explicitly retained conflicts
- less common cruising/engine/tank fields
- generation-specific documentation

Purpose: maximize trust, correction quality and long-term data value without blocking early breadth.

## Sparse data is valid

Unknown is a valid state.

```json
{
  "model": "Example 36",
  "loa_m": 10.9,
  "draft_min_m": 1.7,
  "keel_type": "fin",
  "rudder_type": null,
  "skeg_type": null
}
```

This record is preferable to pretending the design does not exist or fabricating missing configuration data.

## Search semantics for unknown data

A missing field must **never be interpreted as a negative fact**.

If a user filters for `rudder_type = skeg_hung`, then:

- confirmed `skeg_hung` records are confirmed matches;
- confirmed incompatible rudder types are non-matches;
- `rudder_type = unknown/null` records are **insufficient-data candidates**, not confirmed non-matches.

The product may later expose this transparently, for example:

```text
137 confirmed matches
82 additional designs lack sufficient rudder data
```

Exact UX and query semantics require implementation design, but false negatives caused purely by missing data are unacceptable.

## Open-data bootstrap

“Independent dataset” does **not** require rediscovering every public fact from zero.

Open or appropriately licensed structured sources may bootstrap identity and common factual fields when commercial reuse is permitted and provenance is retained. HullQ then concentrates independent research on:

- missing or weak fields;
- keel/rudder/skeg classification;
- variants and generations;
- construction details;
- conflicting values;
- fields important to HullQ search quality.

The imported Sailboatdata scrape remains reference/prototype only and must not become an invisible production source.

## Human review philosophy

The target operating model is exception-based:

```text
high-throughput automated research
        ↓
automated normalization + validation
        ↓
clear / supported records → production
        ↓
uncertain / conflicting records → human review queue
```

The desired system does not require a human to manually approve every design. Human attention should be concentrated on ambiguity, conflicts and high-value edge cases.

## Core coverage metrics

Track at least:

- known canonical design identities
- percentage with Tier-1-equivalent basic searchable coverage
- percentage with HullQ-critical searchable fields
- percentage deeply verified
- completeness by high-value field
- identity/variant ambiguity rate
- conflict rate
- human-review rate
- automated throughput and cost per design
- human minutes per reviewed design
- percentage of observed real-market listings mapped to a known BoatDesign
- percentage of observed listings mapped to sufficiently enriched BoatDesigns

The strongest product-level data KPI is **real-market identification and enrichment coverage**, but broad design-universe coverage remains necessary to make unknown-model discovery credible.

## Initial scale direction

Exact launch thresholds are not yet fixed, but the intended order of magnitude is thousands, not dozens.

A plausible first useful state may look like:

```text
Known design identities:        5,000+
Basic searchable designs:       3,000–5,000
HullQ-critical enriched:        1,500–3,000
Deeply verified:                hundreds initially
```

These are planning ranges, not committed acceptance criteria. The research benchmark and subsequent ingestion measurements should determine realistic thresholds.
