# HullQ Identity Model v0.1

**Status:** ACCEPTED  
**Decision:** OQ-003 / ADR-0004  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This specification defines canonical identity boundaries for sailboat production data.

It deliberately separates commercial naming from technical design generations and factory configuration choices so that HullQ can scale to thousands of designs without silent merges or combinatorial duplication.

## 2. Canonical concepts

### 2.1 BoatModel

A `BoatModel` MUST represent one continuous commercial model lineage.

A BoatModel MUST have a stable opaque HullQ ID independent of display name or URL slug.

The following SHOULD be associated with BoatModel identity:

- canonical model name;
- brand/manufacturer identity;
- known aliases/source spellings;
- first/last-built range when known;
- links to one or more BoatDesign generations.

If a maker reuses the same model name for a substantially unrelated later design, HullQ MUST create a distinct BoatModel ID even when the human-facing canonical name is identical.

### 2.2 BoatDesign

A `BoatDesign` MUST represent one technically coherent production generation belonging to one BoatModel lineage.

A BoatDesign SHOULD have applicability metadata when known:

- `first_built` / `last_built`;
- hull/build-number range;
- manufacturer generation label such as `Mk II`;
- aliases/source labels.

A new BoatDesign MUST be created when evidence establishes a distinct technical baseline that cannot be represented as a concurrent factory choice, including at least one of:

1. materially different hull form/tooling/geometry;
2. an evidence-backed manufacturer/designer generation redesign;
3. a persistent, non-optional production change affecting canonical HullQ search fields and having an identifiable production boundary;
4. an unrelated technical design marketed under a reused model name.

A new BoatDesign MUST NOT be created solely from a conflicting source value, builder transfer, supplier change, cosmetic change or individual-owner modification.

### 2.3 DesignOption

A `DesignOption` MUST represent a factory-supported choice available within a BoatDesign when the choice affects canonical technical data or is required for accurate identity resolution.

An option MUST belong to an explicit axis. Initial axes are:

```text
keel
rig
rudder
sailplan
draft
engine
layout
other
```

An option MAY be time/build-number bounded.

An option SHOULD store only values that differ from/invalidate the BoatDesign baseline. Unspecified option fields inherit from the BoatDesign baseline.

Typical examples include:

- fin vs wing keel;
- standard vs shallow-draft keel;
- fixed vs lifting keel;
- standard vs tall rig;
- sloop vs ketch.

Independent choices MUST NOT be flattened into a Cartesian set of persisted variant records unless a later performance ADR explicitly justifies a materialized projection.

### 2.4 NamedVariant

A `NamedVariant` represents a manufacturer- or market-recognized sub-version within one BoatDesign.

A named label MUST NOT automatically create a BoatDesign generation.

A NamedVariant MAY:

- require one or more DesignOptions;
- exclude incompatible DesignOptions;
- define technical overrides;
- exist for market/source identity even where technical differences are limited.

Named layout/trim packages that do not affect current HullQ canonical fields MAY be represented for identity purposes but SHOULD NOT create unnecessary search configurations.

### 2.5 ResolvedConfiguration

A `ResolvedConfiguration` is the deterministic effective profile produced from:

```text
BoatDesign baseline
+ NamedVariant effects, if any
+ selected DesignOptions
```

A ResolvedConfiguration is the unit against which variant-sensitive search criteria and derived ratios are evaluated.

HullQ MUST NOT require all possible configurations to be stored as canonical source records. A search/index implementation MAY materialize configurations as a derived cache/projection if it remains reproducible from versioned canonical inputs.

## 3. Classification algorithm

For any observed label/version/change, classify in this order:

1. **Is this a continuous commercial model lineage?**
   - No → separate BoatModel.
   - Yes → continue.
2. **Does evidence establish a new technical production baseline?**
   - Yes → separate BoatDesign generation.
   - No → continue.
3. **Is it a concurrent factory-supported technical choice?**
   - Yes → DesignOption.
   - No → continue.
4. **Is it a named manufacturer/market sub-version useful for identity?**
   - Yes → NamedVariant.
   - No → treat as equipment/layout metadata or instance-level modification as appropriate.

When evidence is insufficient, HullQ MUST preserve ambiguity and route the identity to `needs_review` rather than selecting the most plausible class.

## 4. Effective-value precedence

For an effective configuration, technical values MUST resolve in this order:

```text
BoatDesign baseline
→ apply NamedVariant overrides (if selected)
→ apply compatible selected DesignOption overrides
→ validate compatibility/applicability
→ produce ResolvedConfiguration
```

A more specific accepted override supersedes the inherited baseline value only for that resolved configuration. Source/evidence handling for those values is governed by `PROVENANCE_AND_QUALITY.md`, accepted `PROVENANCE_MODEL.v0.1.md`, and ADR-0006.

`NamedVariant` and `DesignOption` MUST NOT silently mutate the BoatDesign baseline.

## 5. Production-boundary rules

Manufacturer hull/build numbers are preferred when available. Calendar years MAY be used where they are the strongest available evidence.

A boundary MAY remain approximate/uncertain; uncertainty MUST be represented rather than converted to a precise date or hull number.

A production year on a marketplace listing MUST NOT automatically be treated as a hull-build year if the source could instead be registration/model year. Resolution confidence must reflect that limitation.

## 6. Builder/designer relationships

Builder and designer MUST NOT be encoded as free-text identity boundaries.

A BoatDesign MAY have multiple time-bounded builders.

A builder change alone MUST NOT create a new BoatDesign.

A designer change is strong evidence of a redesign but MUST be evaluated with the technical baseline evidence; it is not by itself an automatic split rule.

## 7. Owner modifications

Owner/refit modifications belong to the physical boat/listing layer.

They MUST NOT:

- alter the canonical BoatDesign baseline;
- create a DesignOption;
- be generalized to all boats of the model without factory/design evidence.

A later listing model MAY expose instance-level overrides separately from design specifications.

## 8. Listing / source resolution

Identity resolution MUST support the following precision levels:

```text
model
design_generation
named_variant
configuration
candidate_set
unresolved
```

A resolver MUST return the most specific evidence-supported level and MUST NOT invent missing specificity.

Examples:

- `Hallberg-Rassy 36`, no year/hull number → model-level or candidate generation set;
- `Hallberg-Rassy 36 Mk II` → design-generation level;
- `Hallberg-Rassy 36 Mk II shallow draft` → configuration level if evidence supports the option;
- ambiguous same-name reused model → candidate set or unresolved until disambiguated.

## 9. Search semantics consequence

Technical search MUST ultimately evaluate effective configurations where a criterion depends on option-sensitive data.

A result presentation MAY group matching configurations under their BoatModel/BoatDesign to avoid duplicate UI rows.

Example:

```text
Hallberg-Rassy 40
  Match: shallow-draft configuration
  Standard-draft configuration: does not satisfy draft criterion
```

A BoatDesign with an unknown applicable option state MUST obey REQ-SEARCH-002: unknown is not a confirmed non-match.

## 10. Derived ratios consequence

Derived ratios MUST be calculated against the effective technical values of the ResolvedConfiguration whenever option choices change required inputs.

A ratio calculated from baseline values MUST NOT be presented as applying to all variants/options when a documented configuration changes displacement, ballast, sail area, LWL or another required input.

## 11. Identity aliases

Canonical IDs MUST be stable and opaque.

Human-facing names, source labels and marketplace spellings SHOULD be stored as aliases linked to the appropriate identity level.

Normalization MUST NOT destroy source spelling needed for audit/matching.

## 12. Contract migration from BoatDesign schema v0.2

`verified_identity.variant` is insufficient and MUST NOT become the long-term identity model.

OQ-003 is accepted. The next BoatDesign contract MUST:

- reference a BoatModel ID;
- encode a generation identity explicitly;
- remove the overloaded single `variant` string;
- represent options/named variants independently;
- preserve technical baseline separately from option overrides;
- use the accepted separate provenance ledger defined by OQ-004 / ADR-0006.

Schema v0.2 is retained as a historical draft. `BOAT_DESIGN_SCHEMA.v0.4.json` is the current accepted identity-aware canonical BoatDesign contract (v0.3 is historical); provenance is externalized under accepted OQ-004 / ADR-0006.

## 13. Accepted decision criteria

OQ-003 was accepted because all of the following are required and represented by this model:

1. manufacturer-marketed generations and technical generations can be represented without collapsing them;
2. independent keel/rig choices do not require pre-generating every combination;
3. same-name reused models can be distinct canonical identities;
4. a listing can resolve at model/generation/configuration precision without forced specificity;
5. builder changes do not automatically fork technical identity;
6. individual refits cannot contaminate production design data;
7. variant-sensitive ratios/search can be computed from an effective configuration;
8. representative fixtures in `fixtures/identity/oq003_cases.v0.1.json` satisfy the rules.
