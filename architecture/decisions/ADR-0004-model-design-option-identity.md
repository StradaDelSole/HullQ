# ADR-0004 — Model / Design Generation / Option Identity

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Related:** OQ-003, REQ-ID-001..003, REQ-SEARCH-002..005

## Context

HullQ needs broad sailboat coverage while preserving technically meaningful distinctions. A flat `model + variant` identity cannot distinguish commercial lineages, temporal design generations, named versions and orthogonal factory choices without either false merges or combinatorial duplication.

Real manufacturer documentation demonstrates both sequential generations (for example Mk I / Mk II with production boundaries) and concurrent independent choices such as shallow/deep keel and sloop/ketch rigs.

## Decision

Adopt the following semantic model:

```text
BoatModel
  └─ BoatDesign (technical production generation)
       ├─ NamedVariant (optional named sub-version)
       ├─ DesignOption axis: keel
       ├─ DesignOption axis: rig
       ├─ DesignOption axis: rudder / other when needed
       └─ ResolvedConfiguration (derived, not necessarily persisted)
```

`BoatDesign` remains the canonical technical generation concept. It is not synonymous with every marketed variant.

Concurrent independent factory choices are modeled as DesignOptions with technical overrides rather than duplicated full BoatDesign records.

ResolvedConfiguration is the effective profile used for variant-sensitive search, comparison and derived ratios.

## Why

This model:

- prevents false merges between real generations;
- prevents Cartesian variant explosion;
- supports sparse/progressive research;
- allows precise technical search;
- preserves uncertainty in listing/model resolution;
- allows the UI to group configurations under familiar model names;
- keeps owner modifications outside canonical production data.

## Consequences

### Positive

- HullQ can model real-world factory choices without duplicating common specifications.
- Generation-sensitive and option-sensitive search becomes deterministic.
- Ratios can be configuration-correct.
- Market listings can resolve to the highest evidence-supported identity level.

### Negative / complexity cost

- Identity ingestion is more complex than a flat `model + variant` record.
- Search needs an effective-profile resolver or derived search projection.
- Option compatibility may eventually require constraints (`requires` / `excludes`).
- Existing BoatDesign schema v0.2 requires revision.

## Rejected alternatives

### Flat BoatDesign per version

Rejected because it duplicates baseline data and grows combinatorially across independent option axes.

### BoatModel → flat Variant only

Rejected because it still conflates temporal generations with concurrent choices and does not solve multi-axis combinations.

### Ignore options until later

Rejected because keel/rig/draft choices directly affect HullQ's primary search fields and derived ratios.

## Follow-up

Accepted follow-up:

1. mark OQ-003 DECIDED;
2. unblock REQ-ID-003;
3. create the next identity-aware BoatDesign contract;
4. create fixtures/tests from `fixtures/identity/oq003_cases.v0.1.json`;
5. update research workflow to resolve BoatModel before generation/options;
6. proceed to OQ-007.
