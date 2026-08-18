# OQ-003 Research — Model / Design Generation / Variant / Option Identity

**Status:** RESEARCH COMPLETE — OQ-003 DECIDED  
**Open question:** OQ-003  
**Date:** 2026-08-18

## Objective

Define an identity model that can ingest thousands of sailboat designs without collapsing materially different production designs or exploding every factory option into duplicated records.

The model must support:

- commercial model names and name reuse;
- manufacturer-marketed generations such as Mk I / Mk II;
- undocumented but technically material production generations;
- concurrent factory keel, rig, rudder and draft choices;
- named marketing/layout versions;
- listings that resolve only to a model or generation, not an exact configuration;
- progressive/sparse data and explicit uncertainty;
- deterministic technical search and derived-ratio calculation.

## Evidence from real production boats

### Hallberg-Rassy 36

Hallberg-Rassy documents the 36 as one commercial model with a Mk I and Mk II production split. Mk I covered hulls 1–256 / 1989–1994 and Mk II hulls 257–602 / 1994–2003. The manufacturer describes physical changes including a developed transom and wider aft geometry. It separately notes that a 25 cm shallower-draft version was available.

**Identity implication:** Mk I and Mk II are production generations; shallow draft is a concurrent configuration option, not a third generation.

### Hallberg-Rassy 31

Hallberg-Rassy states that from model year 2006 / production number 307 the HR 31 changed on thirteen points to the Mark II version.

**Identity implication:** a known production boundary plus persistent technical revision is a generation boundary even though the commercial lineage remains Hallberg-Rassy 31.

### Hallberg-Rassy 42E

The manufacturer lists both ketch and sloop rigs and also a shallower-draft keel for the same model.

**Identity implication:** rig and keel are independent configuration axes. Flattening them into one variant string would create unnecessary combinations and duplicated data.

### Catalina 22 Capri

Catalina publishes separate wing-keel and fin-keel values for draft, ballast, weight, D/L and SA/D and separately gives standard and tall mast dimensions.

**Identity implication:** option choices can change HullQ search fields and derived ratios. The query engine therefore needs an effective configuration, but the canonical source model should not pre-create every possible keel × rig combination.

### Catalina 320 Mk II / Catalina 34 Mk II

Catalina brochures identify the Mark II as a model generation while offering fin and wing keels within that generation. The published technical values differ by keel choice.

**Identity implication:** manufacturer-marketed generation and factory configuration option are distinct concepts.

### Jeanneau Sun Odyssey 410

Jeanneau documentation lists standard/deep, shoal and lifting-keel configurations with different draft, keel weight and displacement values.

**Identity implication:** alternative keel systems are technical options beneath one design generation when they share the same underlying production design.

### Beneteau Oceanis 35

Beneteau markets Daysailer, Weekender and Cruiser versions as different living-space organizations of the same Oceanis 35.

**Identity implication:** a named marketing version is not automatically a separate technical design. A named variant should become a HullQ technical entity only when it changes canonical fields or is necessary for market identity resolution.

## Core finding

A flat structure such as:

```text
manufacturer + model + variant
```

is insufficient.

It conflates at least four different phenomena:

1. a commercial product/model lineage;
2. a temporally or structurally distinct production design generation;
3. a named version/trim/package;
4. one or more orthogonal factory configuration choices.

The correct HullQ model should separate those concepts.

## Candidate models considered

### Option A — Flat BoatDesign per observed version

Every Mk, keel, rig and named version becomes its own BoatDesign record.

**Rejected direction:** simple initially but creates duplicated data, inconsistent updates and combinatorial growth such as standard-rig/fin-keel, tall-rig/fin-keel, standard-rig/wing-keel, tall-rig/wing-keel.

### Option B — Model → Generation → Variant only

All concurrent differences become one flat `Variant` entity.

**Rejected direction:** better than A but still creates Cartesian-product variants when several independent choice axes coexist.

### Option C — Model → Design Generation → Named Variant / Design Option → Resolved Configuration

A design generation owns a baseline technical profile. Orthogonal factory choices are represented as options on explicit axes. Named versions may reference/bundle options and/or supply their own overrides. Search operates on a deterministic effective configuration assembled from the baseline plus applicable choices.

**Recommended.**

## Recommended semantics

### BoatModel

A `BoatModel` is a continuous commercial model lineage sold under one canonical model identity.

Examples:

- Hallberg-Rassy 36
- Catalina 34
- Beneteau Oceanis 35

A later unrelated reuse of the same display name is a new `BoatModel` identity even if the brand and text name are identical. `first_built` is therefore useful as an identity/disambiguation hint.

### BoatDesign

A `BoatDesign` is HullQ's canonical technical production generation within a `BoatModel`.

A new BoatDesign is created when evidence establishes a new technical baseline, for example:

- materially different hull form/tooling/geometry;
- manufacturer/designer-defined Mk/generation accompanied by technical redesign;
- a persistent, non-optional production change affecting HullQ canonical search fields;
- a redesign with identifiable year, hull-number or other production boundary;
- the same commercial model name being attached to a substantially different naval-architecture design.

A new BoatDesign is **not** created solely because:

- the builder changes while the underlying design remains the same;
- equipment/engine supplier changes;
- interior upholstery/finish changes;
- an optional keel/rig choice exists;
- a source reports a conflicting measurement without evidence of a real design change;
- an owner later modifies an individual boat.

### DesignOption

A `DesignOption` is a factory-supported, potentially concurrent choice within one BoatDesign that changes one or more canonical values or is required for accurate market identity.

Typical axes:

- `keel`
- `rig`
- `rudder`
- `sailplan`
- `draft`
- `engine`
- `layout`
- `other`

Examples:

- standard vs shallow-draft keel;
- fin vs wing keel;
- standard vs tall rig;
- sloop vs ketch;
- fixed vs lifting keel.

Options store only their technical overrides. Unchanged fields inherit from the parent design.

### NamedVariant

A `NamedVariant` is a manufacturer/market-recognized sub-version under one BoatDesign, such as a trim, package or named layout version.

A marketing label alone does not create a BoatDesign generation.

A NamedVariant MAY:

- select required DesignOptions;
- restrict allowed DesignOptions;
- provide additional technical overrides;
- exist only to improve source/listing identity resolution.

### ResolvedConfiguration

A `ResolvedConfiguration` is the effective technical configuration used by search, comparison and ratio calculation:

```text
BoatDesign baseline
+ optional NamedVariant effects
+ selected DesignOptions
= effective technical profile
```

It is a **derived logical object**. HullQ SHOULD NOT persist every possible combination merely to create a complete Cartesian product. A configuration MAY be materialized/cached later for search performance, but the source of truth remains the baseline plus options/variant rules.

## Deterministic boundary rules

### Rule 1 — Commercial lineage first

Resolve a research target to a BoatModel before deciding generation/options.

### Rule 2 — Fundamental or persistent redesign → BoatDesign

If a change establishes a new non-optional technical baseline with an evidence-backed production boundary, create a new BoatDesign generation.

### Rule 3 — Concurrent factory choice → DesignOption

If alternatives coexist within the same underlying production design, represent them as options rather than generations.

### Rule 4 — Named version is evidence, not proof of generation

`Mk II`, `S`, `Performance`, `Cruiser`, `Daysailer` or similar wording does not by itself determine entity type. Classify by the actual production/design relationship.

### Rule 5 — Same name does not guarantee same BoatModel

If a maker reuses a model name for an unrelated later design, create a distinct BoatModel identity and retain the same human-facing name as an alias/display value.

### Rule 6 — Builder change alone does not split identity

A licensed/new builder MAY be attached through a time-bounded builder relationship. Split only when the design itself changes according to the other rules.

### Rule 7 — Owner modifications are instance data

Aftermarket changes belong to the physical boat/listing/instance layer. They MUST NOT mutate the canonical production design or create a factory DesignOption without evidence.

### Rule 8 — No forced precision

A source/listing that identifies only the BoatModel MUST remain resolved at BoatModel level. If generation is known but keel/rig is not, resolve to BoatDesign generation and preserve option uncertainty. Never guess the most likely configuration.

### Rule 9 — Measurement conflict is not a generation

Different LOA/displacement/etc. values from sources remain evidence/conflict unless there is evidence that they represent distinct production configurations or generations.

### Rule 10 — Search works on effective configurations

A technical query evaluates applicable ResolvedConfigurations. The UI MAY collapse multiple matching configurations into one model/design result while explaining which configuration(s) satisfy the query.

## Identity resolution precision

Recommended resolution levels:

- `model`
- `design_generation`
- `named_variant`
- `configuration`
- `candidate_set`
- `unresolved`

Resolution must include confidence/evidence under the normal HullQ provenance rules.

## Important implementation consequence

The current v0.2 schema's single `verified_identity.variant` string is insufficient. It should be superseded by an identity graph that separates:

- BoatModel;
- BoatDesign generation;
- DesignOption;
- optional NamedVariant;
- derived ResolvedConfiguration.

The exact provenance/storage representation remains subject to OQ-004; OQ-003 should define semantics, not prematurely select database tables.

## Recommendation

Adopt Option C.

This provides enough normalization to avoid variant explosion while preserving the precision HullQ needs for technical search, ratios, compare and listing resolution.
