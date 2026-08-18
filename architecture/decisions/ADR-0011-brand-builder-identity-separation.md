# ADR-0011 — Brand / Builder Identity Separation

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Related:** ADR-0004, OQ-003, `specs/IDENTITY_MODEL.v0.2.md`

## Context

HullQ's accepted identity model already separates `BoatModel`, technical `BoatDesign` generations, named variants and factory options. It does not yet model a second common identity problem explicitly enough: the market-facing boat brand or marque can differ from the legal or productive organization that built/manufactured the boat.

Both names can be legitimate user discovery paths. A user may know the marque, the builder, or both. Treating one as merely an alias of the other loses real semantics; treating the builder's exact corporate name as the only searchable identity creates poor search behavior and false negatives.

The existing accepted contracts expose this debt directly:

- `BOAT_MODEL_SCHEMA.v0.1.json` stores `manufacturer_name` and `brand_name` as free-text strings;
- `BOAT_DESIGN_SCHEMA.v0.4.json` stores builder relationships by free-text `name`.

These contracts are retained for history and compatibility, but they are insufficient for the next identity runtime.

## Decision

HullQ SHALL treat **Organization/Builder** and **Brand/Marque** as separate first-class identity concepts with stable opaque IDs.

Neither concept is an alias of the other.

The canonical relationship direction is conceptually:

```text
Organization / Builder
        │
        └── builds / manufactures ──► BoatDesign

Brand / Marque
        │
        └── markets / identifies ───► BoatModel

BoatModel
        └── BoatDesign generation(s)
```

The exact persistence shape MAY use relationship records rather than embedded foreign keys, but it MUST preserve the semantics below.

### 1. Independent identity

An Organization and a Brand MUST each have:

- a stable opaque HullQ ID;
- a canonical display name;
- zero or more entity-specific aliases/source spellings;
- provenance for source-backed identity facts through the accepted provenance model.

A Brand MUST NOT be collapsed into an Organization merely because the same word is commonly used for both.

An Organization MUST NOT be collapsed into a Brand merely because users commonly search the organization name as if it were the marque.

### 2. Relationship cardinality and history

HullQ MUST be capable of representing:

- one brand associated with multiple builders over time;
- one builder producing boats for multiple brands;
- a BoatModel marketed under more than one brand where evidence requires it;
- a BoatDesign built/manufactured by more than one organization where evidence requires it;
- time-, hull-number-, or market-bounded relationships when known.

A builder change alone continues to be insufficient to create a new BoatDesign under ADR-0004.

### 3. Alias semantics

Aliases belong to the entity they name.

Examples of alias classes include:

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

An alias MUST NOT silently change canonical identity or imply that two different entity kinds are equivalent.

Source spellings required for audit/matching MUST be preserved.

### 4. Search semantics

Brand and builder/manufacturer identities MUST both be independently searchable.

Users MUST NOT be required to enter an exact legal corporate name to find a builder/manufacturer. Search/index projections MUST be capable of matching accepted user-facing forms that omit non-distinguishing corporate suffixes and source decorations such as:

```text
Ltd.
Limited
Inc.
Corp.
GmbH
Co.
country annotations such as (USA), (UK), (FRA)
```

Case and punctuation differences MUST NOT require a separate canonical entity.

Curated alternate spellings/transliterations MAY be indexed where needed. Fuzzy typo correction/ranking is a later search-implementation concern and MUST NOT be used to merge canonical identities automatically.

Search normalization MUST NOT mutate canonical names or provenance-bearing source strings.

### 5. Raw research input remains raw

A source/reference field named `manufacturer` is an input label, not proof that the string represents HullQ's canonical Organization, Brand, or both.

Research ingestion MUST preserve the supplied raw string and resolve it through evidence. It MUST NOT infer a canonical entity role solely from the source column heading or from a model-name prefix.

## Consequences

### Positive

- users can find the same boat through either familiar marque or builder/manufacturer names;
- HullQ can represent real market identity without falsifying corporate identity;
- legal suffixes and source formatting do not become search requirements;
- historical builder/brand changes do not force model or design duplication;
- source strings remain auditable while the search index stays user-friendly.

### Complexity cost

- identity resolution requires entity and relationship records rather than two free-text strings;
- search projections must index canonical names plus accepted aliases/normalized forms;
- some ambiguous historical records will require human review instead of automatic mapping.

## Migration

`specs/IDENTITY_MODEL.v0.2.md` supersedes v0.1 as the current normative identity specification.

Before the identity runtime represented by the next identity slice can be accepted:

1. the BoatModel contract MUST stop treating brand/manufacturer as authoritative free-text fields;
2. the BoatDesign builder relationship MUST stop using a free-text name as its canonical identity boundary;
3. first-class Brand and Organization identities plus relationship contracts MUST be defined;
4. aliases MUST be entity-scoped and identity-safe;
5. fixtures MUST cover brand ≠ builder, exact-name vs shortened-name search, historical/multiple relationships, and unresolved ambiguity.

Existing v0.1/v0.4 contracts MUST remain available as historical/versioned artifacts rather than being silently mutated.

## Rejected alternatives

### Treat the brand as a builder alias

Rejected because a market-facing marque and a productive/legal organization are semantically different entities even when users use the terms interchangeably.

### Store only a display manufacturer string

Rejected because it cannot represent independent brand search, historical builder relationships, or evidence-safe identity resolution.

### Strip corporate suffixes from canonical names

Rejected because search convenience must not destroy canonical/source identity. Suffix omission belongs in aliases or the search projection, not destructive normalization.
