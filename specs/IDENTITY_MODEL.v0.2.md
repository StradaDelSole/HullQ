# HullQ Identity Model v0.2

**Status:** ACCEPTED  
**Decision:** OQ-003 / ADR-0004, refined by ADR-0011  
**Supersedes:** `specs/IDENTITY_MODEL.v0.1.md` as current normative identity semantics  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This specification defines canonical identity boundaries for sailboat production data.

It separates:

- commercial model lineage;
- technical design generation;
- market-facing brand/marque;
- productive/legal organization and builder/manufacturer roles;
- named variants;
- orthogonal factory options;
- aliases/source spellings;
- resolved technical configurations.

The objective is to let HullQ scale to thousands of designs without false merges, combinatorial duplication, or requiring users to know an exact corporate name.

## 2. Canonical identity concepts

### 2.1 Organization

An `Organization` represents a real organization such as a shipyard, manufacturer, corporate builder, or other organization participating in a production relationship.

An Organization MUST have a stable opaque HullQ ID independent of its name.

An Organization SHOULD have:

- a canonical HullQ display name;
- a verified legal name when known and useful;
- aliases/source spellings;
- provenance for source-backed identity facts.

Corporate suffixes or country annotations MUST NOT be removed destructively from evidence/source strings merely to improve search.

An Organization is not automatically a Brand.

### 2.2 Brand / Marque

A `Brand` represents the market-facing marque under which a BoatModel is identified or marketed.

A Brand MUST have a stable opaque HullQ ID independent of display spelling.

A Brand SHOULD have:

- a canonical HullQ display name;
- aliases/source spellings;
- provenance for source-backed identity facts.

A Brand is not automatically the Organization that built/manufactured its boats.

Where the same visible word legitimately names both a Brand and an Organization, HullQ MAY have two distinct canonical entities linked by evidence-supported relationships; the shared spelling MUST NOT force identity collapse.

### 2.3 BoatModel

A `BoatModel` MUST represent one continuous commercial model lineage.

A BoatModel MUST have a stable opaque HullQ ID independent of display name or URL slug.

The following SHOULD be associated with BoatModel identity:

- canonical model name;
- one or more evidence-supported Brand relationships when known;
- known aliases/source spellings;
- first/last-built range when known;
- links to one or more BoatDesign generations.

A BoatModel MUST NOT use a free-text manufacturer/brand field as its long-term canonical identity boundary.

If a maker reuses the same model name for a substantially unrelated later design, HullQ MUST create a distinct BoatModel ID even when the human-facing canonical name is identical.

### 2.4 BoatDesign

A `BoatDesign` MUST represent one technically coherent production generation belonging to one BoatModel lineage.

A BoatDesign SHOULD have applicability metadata when known:

- `first_built` / `last_built`;
- hull/build-number range;
- manufacturer generation label such as `Mk II`;
- aliases/source labels.

A BoatDesign MUST support one or more Organization relationships for builders/manufacturers when evidence requires them. These relationships MUST resolve to Organization identities rather than canonical free-text names.

A new BoatDesign MUST be created when evidence establishes a distinct technical baseline that cannot be represented as a concurrent factory choice, including at least one of:

1. materially different hull form/tooling/geometry;
2. an evidence-backed manufacturer/designer generation redesign;
3. a persistent, non-optional production change affecting canonical HullQ search fields and having an identifiable production boundary;
4. an unrelated technical design marketed under a reused model name.

A new BoatDesign MUST NOT be created solely from a conflicting source value, builder transfer, supplier change, cosmetic change, or individual-owner modification.

### 2.5 DesignOption

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

### 2.6 NamedVariant

A `NamedVariant` represents a manufacturer- or market-recognized sub-version within one BoatDesign.

A named label MUST NOT automatically create a BoatDesign generation.

A NamedVariant MAY:

- require one or more DesignOptions;
- exclude incompatible DesignOptions;
- define technical overrides;
- exist for market/source identity even where technical differences are limited.

Named layout/trim packages that do not affect current HullQ canonical fields MAY be represented for identity purposes but SHOULD NOT create unnecessary search configurations.

### 2.7 ResolvedConfiguration

A `ResolvedConfiguration` is the deterministic effective profile produced from:

```text
BoatDesign baseline
+ NamedVariant effects, if any
+ selected DesignOptions
```

A ResolvedConfiguration is the unit against which variant-sensitive search criteria and derived ratios are evaluated.

HullQ MUST NOT require all possible configurations to be stored as canonical source records. A search/index implementation MAY materialize configurations as a derived cache/projection if it remains reproducible from versioned canonical inputs.

## 3. Brand and builder/manufacturer relationships

Brand and Organization are separate first-class identities.

The conceptual relationship model is:

```text
Organization
   └─ builds / manufactures ──► BoatDesign

Brand
   └─ markets / identifies ───► BoatModel
```

The persistence implementation MAY use separate relationship records or an equivalent normalized representation.

It MUST be capable of representing:

- one Brand associated with multiple Organizations over time;
- one Organization producing designs for multiple Brands;
- multiple Brands associated with one BoatModel where evidence requires it;
- multiple Organizations associated with one BoatDesign where evidence requires it;
- relationship validity by year, hull/build number, market, or explicit unknown where known/needed.

A change of builder/manufacturer alone MUST NOT create a new BoatDesign.

A source field labelled `manufacturer` MUST NOT be assumed to mean Brand, Organization, or both without evidence.

## 4. Alias model

Canonical IDs MUST be stable and opaque.

Human-facing names, source labels, marketplace spellings, historical names, abbreviations and accepted alternate spellings SHOULD be stored as aliases linked to the appropriate identity entity.

Aliases MUST be scoped to the entity they name. A Brand name MUST NOT be stored as an Organization alias merely to make search convenient, and vice versa.

Representative alias classes include:

```text
common_name
trade_name
abbreviation
historical_name
alternate_spelling
transliteration
source_spelling
other
```

Aliases that require independent provenance SHOULD have stable identity of their own or an equivalent provenance-safe addressing mechanism; persistent provenance MUST NOT depend on fragile array position.

Normalization MUST NOT destroy source spelling needed for audit/matching.

## 5. Classification algorithm

For any observed label/version/change, classify in this order:

1. **What kind of identity claim is present?**
   - organization/builder/manufacturer claim → resolve or retain candidate Organization identity;
   - brand/marque claim → resolve or retain candidate Brand identity;
   - model claim → resolve BoatModel lineage;
   - insufficient evidence → preserve ambiguity and route to review.
2. **Is this a continuous commercial model lineage?**
   - No → separate BoatModel.
   - Yes → continue.
3. **Does evidence establish a new technical production baseline?**
   - Yes → separate BoatDesign generation.
   - No → continue.
4. **Is it a concurrent factory-supported technical choice?**
   - Yes → DesignOption.
   - No → continue.
5. **Is it a named manufacturer/market sub-version useful for identity?**
   - Yes → NamedVariant.
   - No → treat as equipment/layout metadata or instance-level modification as appropriate.

When evidence is insufficient, HullQ MUST preserve ambiguity and route the identity to `needs_review` rather than selecting the most plausible class.

A model-name prefix MUST NOT by itself prove Brand, Organization, designer, or builder identity.

## 6. Effective-value precedence

For an effective configuration, technical values MUST resolve in this order:

```text
BoatDesign baseline
→ apply NamedVariant overrides (if selected)
→ apply compatible selected DesignOption overrides
→ validate compatibility/applicability
→ produce ResolvedConfiguration
```

A more specific accepted override supersedes the inherited baseline value only for that resolved configuration. Source/evidence handling for those values is governed by the accepted provenance specifications and ADR-0006.

`NamedVariant` and `DesignOption` MUST NOT silently mutate the BoatDesign baseline.

## 7. Production-boundary rules

Manufacturer hull/build numbers are preferred when available. Calendar years MAY be used where they are the strongest available evidence.

A boundary MAY remain approximate/uncertain; uncertainty MUST be represented rather than converted to a precise date or hull number.

A production year on a marketplace listing MUST NOT automatically be treated as a hull-build year if the source could instead be registration/model year. Resolution confidence must reflect that limitation.

Brand and builder/manufacturer relationships MAY have their own validity boundaries independently of BoatDesign generation boundaries.

## 8. Builder and designer relationships

Builder/manufacturer relationships MUST resolve through Organization identity rather than canonical free-text names.

A BoatDesign MAY have multiple time-bounded builders/manufacturers.

A builder change alone MUST NOT create a new BoatDesign.

A designer change is strong evidence of a redesign but MUST be evaluated with the technical baseline evidence; it is not by itself an automatic split rule.

Designer identity modeling may be further refined separately; this specification does not force a person/organization designer schema beyond preserving the existing no-silent-merge rules.

## 9. Owner modifications

Owner/refit modifications belong to the physical boat/listing layer.

They MUST NOT:

- alter the canonical BoatDesign baseline;
- create a DesignOption;
- be generalized to all boats of the model without factory/design evidence.

A later listing model MAY expose instance-level overrides separately from design specifications.

## 10. Listing / source resolution

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

Organization and Brand resolution are separate axes from BoatModel/BoatDesign precision. A source/listing MAY resolve the model while leaving the exact builder relationship uncertain, or vice versa.

## 11. Search semantics

Brand and builder/manufacturer identity MUST both be independently searchable.

A user MUST NOT need to enter an exact legal corporate form to find an accepted Organization identity.

Search/index projections MUST support accepted user-facing variants that omit non-distinguishing corporate suffixes and source decorations, including where relevant:

```text
Ltd. / Limited
Inc.
Corp. / Corporation
GmbH
Co. / Company
country annotations such as (USA), (UK), (FRA)
```

Case and punctuation normalization MAY occur in the search projection and MUST NOT mutate canonical names.

Curated transliteration/alternate spelling aliases MAY support names whose common user spelling differs from the canonical spelling.

Fuzzy typo correction MAY be introduced by the later search implementation, but it MUST NOT automatically merge canonical entities.

Technical search MUST ultimately evaluate effective configurations where a criterion depends on option-sensitive data.

A result presentation MAY group matching configurations under their BoatModel/BoatDesign to avoid duplicate UI rows.

## 12. Derived ratios consequence

Derived ratios MUST be calculated against the effective technical values of the ResolvedConfiguration whenever option choices change required inputs.

A ratio calculated from baseline values MUST NOT be presented as applying to all variants/options when a documented configuration changes displacement, ballast, sail area, LWL or another required input.

## 13. Research-input consequence

The canonical minimal research input remains a source/reference target containing `manufacturer`, `model`, and `first_built` where those are the available source fields.

`manufacturer` in that raw target is deliberately a **source-supplied label**, not a canonical HullQ relationship assertion.

The pipeline MUST preserve it unchanged as raw identity input and MAY resolve it to:

- an Organization candidate;
- a Brand candidate;
- both as separate evidence-supported entities;
- unresolved/candidate state.

It MUST NOT infer the canonical role from the column heading alone.

## 14. Contract migration

The following accepted contracts predate ADR-0011 and are migration inputs, not the target shape for the identity runtime:

- `BOAT_MODEL_SCHEMA.v0.1.json` stores `manufacturer_name` and `brand_name` as free-text strings;
- `BOAT_DESIGN_SCHEMA.v0.4.json` stores builders with free-text `name`.

The next identity contract revision MUST:

- define first-class Organization and Brand identities;
- replace canonical free-text manufacturer/brand identity boundaries with stable IDs/relationships;
- keep BoatModel and BoatDesign IDs stable/opaque;
- support historically bounded/multiple relationships without forcing a new BoatDesign;
- provide entity-scoped alias semantics;
- preserve raw/source names through provenance;
- retain the accepted BoatModel → BoatDesign → NamedVariant/DesignOption structure;
- retain ResolvedConfiguration semantics.

Existing versioned schemas MUST NOT be silently mutated; migration requires new schema versions.

## 15. Accepted decision criteria

The current model is accepted because it can represent all of the following without semantic collapse:

1. manufacturer-marketed generations and technical generations;
2. independent keel/rig choices without pre-generating every combination;
3. same-name reused models as distinct canonical identities;
4. listing resolution at model/generation/configuration precision without forced specificity;
5. builder changes without automatically forking technical identity;
6. individual refits outside canonical production data;
7. variant-sensitive ratios/search from effective configurations;
8. Brand and Organization as distinct identities even when users commonly conflate their names;
9. both Brand and builder/manufacturer as valid search paths;
10. shortened/common corporate-name search without destructive canonical-name normalization;
11. one-to-many/many-to-many historical brand/builder relationships;
12. raw research `manufacturer` strings that can remain unresolved instead of being misclassified.
