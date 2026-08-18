# OQ-004 Research — Field-Level Provenance Persistence

**Status:** DECIDED / decision evidence retained  
**Question:** How should HullQ persist field-level evidence, canonical resolution decisions and derivation lineage without degrading the canonical search model?

## 1. Problem

HullQ requires all accepted production values to remain traceable to evidence while also supporting thousands of designs and efficient characteristic-first search.

Earlier drafts embedded an `evidence[]` collection inside each BoatDesign and addressed fields with ad-hoc dot paths. That proves the concept but is not the strongest long-term persistence model.

The persistence shape must support at least:

- one source supporting many fields;
- many sources supporting one field;
- raw source representation and normalized SI/canonical candidate;
- conflicts and later adjudication without deleting contradictory evidence;
- visual classification evidence for keel/rudder/skeg;
- option-/variant-specific values;
- reverse lookup from a Source to every production value it influences;
- AI/parser/human extraction provenance;
- later re-evaluation if a source becomes invalid or rights status changes;
- derived values such as ResolvedConfiguration projections and ratios without pretending they came directly from an external source.

## 2. Standards considered

### RFC 6901 — JSON Pointer

HullQ should use RFC 6901 JSON Pointer instead of project-specific dot paths to address a field inside a subject document. Example:

```text
/baseline/dimensions/loa_m
```

This gives a standardized machine-readable field address and avoids inventing escaping/path semantics.

Identity-bearing nested objects such as NamedVariant and DesignOption already possess stable IDs. Evidence therefore targets the subentity ID plus a JSON Pointer relative to that subentity instead of fragile array indexes.

**Rule:** numeric array-index paths SHOULD NOT be used as stable provenance identity for order-independent domain collections.

### W3C PROV-DM

W3C PROV separates provenance concepts into Entities, Activities and Agents. HullQ should preserve the useful conceptual separation without implementing the full PROV RDF/ontology stack:

- Source/source material and canonical data are provenance **entities**;
- extraction, normalization, adjudication and calculation are **activities**;
- humans, parsers and LLM/tool versions are **agents**.

The HullQ model remains domain-specific JSON and MAY later export/marshal to a broader provenance representation if that ever becomes useful.

### JSON Schema Draft 2020-12

All provenance contracts remain JSON Schema Draft 2020-12, consistent with the repository standards baseline.

## 3. Persistence alternatives

### Option A — Value wrapper per canonical field

Example concept:

```json
"loa_m": {
  "value": 10.54,
  "evidence": [...]
}
```

**Advantages**
- provenance visually adjacent to the value;
- easy local inspection.

**Problems**
- every search predicate must traverse wrappers;
- canonical domain schemas become extremely repetitive;
- difficult reverse lookup from source → influenced fields;
- nested options/variants create deep duplicated structures;
- API/search projection becomes coupled to audit metadata.

**Decision:** reject.

### Option B — Embedded BoatDesign `evidence[]` ledger

Canonical fields stay plain values; one evidence array is embedded in each BoatDesign and keyed by field path.

**Advantages**
- better search model than wrappers;
- simple document export;
- preserves multiple evidence records.

**Problems**
- BoatDesign documents grow with every evidence observation;
- one source used across many designs requires expensive reverse lookup/indexing;
- provenance writes create contention on canonical domain records;
- evidence for BoatModel / DesignOption / NamedVariant requires increasingly complex embedded addressing;
- derived values still need a different lineage concept.

**Decision:** reject as canonical persistence; MAY exist as an export/read projection.

### Option C — Separate provenance ledger + canonical value projection — RECOMMENDED

Persist three distinct provenance concepts:

1. **FieldEvidence** — immutable observation of what a source supports for one field;
2. **FieldResolution** — versioned decision about the current canonical state of that field;
3. **DerivationRecord** — lineage for a value calculated/inherited from other canonical values rather than read directly from a source.

Canonical BoatModel/BoatDesign values remain plain queryable values.

This creates:

```text
Source
  ↓
FieldEvidence (immutable source observation)
  ↓
FieldResolution (current/auditable canonical decision)
  ↓
BoatDesign / BoatModel canonical value

BoatDesign baseline + DesignOptions + method version
  ↓
DerivationRecord
  ↓
ResolvedConfiguration / ratio / other derived projection
```

**Advantages**
- canonical search objects remain simple and fast;
- provenance can scale independently;
- source → evidence → affected values is naturally queryable;
- conflicts and adjudication remain explicit;
- evidence history does not disappear when canonical decisions change;
- derived lineage is not confused with external evidence;
- implementation remains database-agnostic until OQ-012.

**Cost**
- persistence layer must maintain consistency between active FieldResolution and the current canonical field value;
- reads requiring full provenance need joins/lookups.

For HullQ's quality goals this is the better trade-off.

## 4. Proposed concepts

### 4.1 FieldEvidence

An immutable observation associated with exactly one source and one canonical subject field.

Contains:

- stable `evidence_id`;
- `subject_kind` + `subject_id`;
- RFC-6901 `field_pointer`;
- `source_id`;
- source locator metadata (page/section/figure/record key etc.);
- raw source representation;
- normalized candidate representation where applicable;
- evidence type;
- extraction/observation producer and tool/model version;
- research job/activity linkage when known;
- confidence;
- timestamp;
- optional `supersedes_evidence_id` when a later extraction corrects a prior observation.

Evidence is append-only. A later correction does not erase the original historical observation.

### 4.2 FieldResolution

A versioned canonical decision for one field.

States:

- `resolved`;
- `resolved_with_conflict`;
- `unknown`;
- `needs_review`;
- `conflict`.

A resolution records:

- supporting evidence IDs;
- contradicting evidence IDs;
- all considered evidence IDs where useful;
- canonical value snapshot when resolved;
- resolution method;
- policy version;
- resolver identity/tool;
- timestamp;
- optional previous resolution it supersedes.

There MUST be at most one active/current resolution per subject+field in the persistence model. Historical resolutions remain retained.

### 4.3 DerivationRecord

Derived values do not get fake source evidence. A DerivationRecord captures:

- target subject/field;
- method ID/version;
- input field/resolution references;
- output value snapshot;
- producing tool/version;
- timestamp.

Examples:

- effective shallow-draft configuration value inherited from a DesignOption;
- SA/D generated under formula version X;
- a later materialized search projection.

OQ-001 will define formula semantics; OQ-004 only establishes generic lineage.

## 5. Canonical-value invariants

1. A non-null accepted production value MUST have a current `FieldResolution` in `resolved` or `resolved_with_conflict` state.
2. The active resolution's canonical value snapshot MUST equal the canonical subject value.
3. `unknown`, unresolved `conflict` or `needs_review` resolution states require the canonical subject field to remain null/unknown unless another accepted rule explicitly governs a partial structure.
4. `resolved_with_conflict` MUST retain contradicting evidence rather than hiding it.
5. Every production-supporting evidence record MUST reference a Source whose `production_value` clearance is allowed or whose conditional requirements are satisfied.
6. If source rights/validity changes, reverse provenance lookup MUST allow affected FieldResolutions to be re-evaluated.
7. Derived values MUST trace to versioned derivation inputs/method rather than an external source claim.

## 6. Confidence semantics

Evidence confidence means confidence in the extraction/classification/interpretation represented by that evidence record. It MUST NOT silently encode an overall publisher/source-prestige ranking.

Source hierarchy and adjudication policy are separate concerns.

## 7. Raw material / copyright guardrail

FieldEvidence should store the minimum raw representation needed to audit a value. Full copyrighted source artifacts or long passages MUST NOT be copied merely for convenience.

Source locators, structured raw values and optional short excerpts can be stored subject to source rights policy. A source artifact may be metadata-only when redistribution/storage is not cleared.

## 8. Storage technology

This decision deliberately does **not** choose PostgreSQL, document storage, Strapi, Elasticsearch/OpenSearch or another technology. OQ-012 controls persistence/search implementation.

A relational implementation is likely natural for reverse provenance lookup, but the normative contract is persistence-technology independent.

## 9. Acceptance criteria for OQ-004

The proposal is decision-ready if fixtures demonstrate:

1. one source supporting multiple independent fields;
2. two sources agreeing on one normalized field;
3. raw imperial value normalized to SI while retaining raw representation;
4. unresolved conflict leaves canonical value unknown;
5. manually/explicitly resolved conflict retains contradicting evidence;
6. visual keel/rudder/skeg classification can be represented without fabricating source text;
7. DesignOption-specific evidence uses a stable subject ID rather than a BoatDesign array index;
8. a ResolvedConfiguration/ratio-like output can carry derivation lineage separate from source evidence;
9. invalid pointers/state combinations are rejected by contract/validation fixtures where structurally expressible.

## 10. Recommendation

Accept **Option C: separate provenance ledger + canonical value projection**, using RFC 6901 JSON Pointer for field addressing and a lightweight W3C-PROV-aligned conceptual separation of entity/activity/agent.
