# SLICE-0012 — Evidence Applicability and Research Bundle Contract

**ID:** SLICE-0012  
**Type:** IMPLEMENTATION  
**Status:** BLOCKED  
**Stage:** 2.12 — benchmark-driven contract hardening before persistence  
**Depends on:** SLICE-0011 accepted / DONE  
**Blocks:** first PostgreSQL persistence/import slice

## Objective

Close the **smallest three lossless-data gaps proven by the 50-design controlled benchmark** before HullQ freezes a physical PostgreSQL schema:

1. distinguish the **source/document class** of FieldEvidence from the **semantic kind of claim** made by that observation;
2. preserve structured **applicability/scope** for evidence that applies only to a production subset, option/variant/state or individual hull;
3. define one deterministic, machine-ingestible **ResearchEvidenceBundle** boundary through which master/ChatGPT web research can be handed to later import/persistence code without turning narrative notes into canonical facts.

This slice is intentionally not PostgreSQL and not another broad domain redesign.

```text
independent web research
        ↓
source-linked raw observations
        + claim semantics
        + applicability/scope
        + explicit reference crosscheck metadata
        ↓
ResearchEvidenceBundle
        ↓
existing provenance validation boundary
        ↓
NO canonical auto-resolution
NO database writes
NO network acquisition
```

## Benchmark evidence for this slice

The controlling evidence is:

- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`;
- `research/benchmark/BENCHMARK-50-classification.csv`;
- `research/benchmark/BENCHMARK-50-analysis.md`;
- Waves 01–06 under `research/benchmark/waves/`.

The manually coded stress corpus found:

- 32/50 designs where temporal/production applicability materially mattered;
- 30/50 where option/variant/state semantics materially mattered;
- 22/50 where measurement/definition basis materially mattered;
- 20/50 with a material explicit conflict/unresolved issue;
- repeated cases where class-rule, individual-hull, nominal-design and operating-state values would be semantically wrong if stored as indistinguishable scalar evidence.

These are stress-corpus incidences, not population prevalence estimates.

## Controlling accepted artifacts

Preserve the accepted semantics of:

- ADR-0004 / `specs/IDENTITY_MODEL.v0.2.md`;
- ADR-0006 provenance model;
- `specs/FIELD_EVIDENCE_SCHEMA.v0.2.json`;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.2.json`;
- `specs/PROVENANCE_SUBJECT_SCHEMA.v0.1.json`;
- `src/hullq/domain/provenance.py`;
- `src/hullq/domain/measurements.py`;
- `src/hullq/domain/configuration.py`;
- accepted source-rights / ResearchJob runtime.

Existing versioned schemas MUST NOT be silently mutated. Successor contracts require new versions.

## In scope

### 1. Claim semantics separate from evidence/source type

Introduce one bounded versioned vocabulary for the **semantic role of a source observation**, separate from existing `EvidenceType`.

The vocabulary must support at least:

```text
nominal_design_value
factory_option_value
operating_state_value
individual_hull_value
class_rule_constraint
measurement_certificate_value
published_calculation
identity_or_chronology_claim
other
unknown
```

Names may be refined if one materially clearer exact vocabulary is chosen, but the distinctions above MUST remain representable.

Rules:

- existing `EvidenceType` remains the source/document/evidence-artifact classification;
- claim semantics MUST NOT encode source authority/confidence;
- `unknown` MUST remain valid and fail closed;
- a `class_rule_constraint` MUST NOT become a nominal design value merely because the source is authoritative;
- an `individual_hull_value` MUST NOT silently project to BoatDesign baseline;
- a `published_calculation` MUST NOT pretend to be a directly observed source dimension.

### 2. Evidence applicability / scope

Introduce the smallest immutable structured applicability boundary needed to preserve evidence scope before canonical resolution.

It must be able to retain, where known:

- first/last applicable production year;
- hull/build-number from/to;
- market/region when relevant;
- named-variant scope/reference;
- design-option scope/reference(s);
- operating-state scope/reference without inventing a DesignOption;
- individual-hull/listing/build reference;
- explicit unknown/unbounded applicability.

Do not require all fields to be populated. Unknown boundaries are normal.

At minimum enforce:

- year range consistency;
- non-empty IDs/refs when a corresponding scoped dimension is asserted;
- snapshot safety for caller-owned collections;
- no implication that absent applicability metadata means `all production`;
- no conversion of an individual-hull observation into a design-wide observation.

A generic arbitrary property graph is out of scope.

### 3. FieldEvidence successor contract

Add a successor FieldEvidence schema version that retains every accepted v0.2 provenance property and adds the new claim/applicability semantics.

Migration rules:

- v0.2 remains immutable and valid as its own historical contract;
- no in-place mutation of v0.2 schema;
- any explicit v0.2 → successor adapter MUST map missing claim/applicability to explicit unknown/unresolved semantics, not to `nominal_design_value` or global applicability;
- raw observation and normalized candidate remain separate and snapshot-safe;
- `observed_at` remains observation/retrieval time and MUST NOT be reused as the applicability date.

FieldResolution does not need a semantic redesign in this slice unless a hard compatibility contradiction is found. Existing resolved/conflict/unknown/review states should remain reusable.

### 4. ResearchEvidenceBundle contract

Define one versioned machine-ingestible bundle for research handoff.

The bundle must contain at least:

- schema/bundle version and stable bundle ID;
- research target identity input/candidate information sufficient to link the research job;
- research job/activity identifiers where available;
- the set of source-linked successor FieldEvidence records produced by the research;
- explicit unresolved/review notes/findings that are not yet canonical FieldResolution;
- optional **reference crosscheck outcomes** in a separate non-provenance section.

The bundle MUST NOT require canonical values to exist.

The bundle MUST support partial research.

### 5. Reference crosscheck boundary

The bundle's reference-comparison section exists specifically so QA comparison cannot leak into source provenance.

For the current SailboatData policy it must be capable of storing outcomes such as:

```text
match
partial_match
conflict
definition_or_basis_difference
identity_disambiguation_required
reference_incomplete
no_reference_record_found
not_checked
```

Rules:

- reference comparison MUST NOT create FieldEvidence;
- the crosscheck contract MUST NOT require or encourage storing SailboatData field values;
- it may identify the topic/field compared and contain bounded notes;
- it MUST be impossible for a crosscheck entry to be referenced as supporting evidence by FieldResolution through an evidence ID;
- this policy is specific to current benchmark/reference handling and does not replace the general source-rights model.

### 6. Runtime/value objects and validation

Add the smallest runtime/value-object support needed for the new schemas, preferably alongside the existing provenance boundary rather than as a separate service.

Requirements:

- typed exact vocabularies;
- immutable/snapshot-safe collections;
- deterministic validation;
- schema/runtime enum parity tests;
- successor FieldEvidence integrates with existing evidence invariant checks without weakening them;
- bundle validation is deterministic/offline;
- no hidden clock/UUID generation in pure validation logic.

### 7. Fixtures from real benchmark cases

Add compact fixtures/tests derived from the benchmark, without copying SailboatData values as evidence.

At minimum cover:

- Pearson 35 — 1979-specific evidence applicability;
- Catalina 316 or Bavaria 38 — configuration-sensitive mass with explicit source basis;
- J/105 — class-rule constraint distinct from nominal builder specification;
- Gemini 105Mc — operating-state evidence without creating a fake factory option;
- a broker/individual-hull observation that cannot silently become BoatDesign baseline;
- one reference crosscheck entry that remains outside FieldEvidence/FieldResolution provenance.

## Explicitly out of scope

Do not implement:

- PostgreSQL/SQLAlchemy/ORM/migrations;
- physical persistence tables;
- broad ingestion;
- autonomous web research/crawling;
- new source adapters;
- source authority ranking;
- automatic FieldResolution/canonical-value selection;
- full ResolvedConfiguration builder;
- a general operating-state engine;
- full folded/sailing geometry redesign;
- a general lineage graph;
- new search/query semantics;
- API/frontend;
- marketplace/listing ingestion;
- SailboatData extraction or use as HullQ evidence.

If implementation would require one of these, stop and report rather than expanding scope.

## Required tests

Cover at least:

1. exact claim-semantics vocabulary parity between schema/runtime;
2. claim semantics remain independent of existing `EvidenceType`;
3. applicability accepts unknown/partial boundaries;
4. invalid reversed year ranges fail;
5. scoped refs required when that scope is asserted;
6. caller mutation cannot alter stored applicability snapshots;
7. successor FieldEvidence retains all v0.2 raw/normalized/provenance semantics;
8. v0.2 adapter, if provided, maps absent new semantics to explicit unknown, never nominal/global defaults;
9. `observed_at` and applicability time remain independent;
10. `individual_hull_value` remains identifiable as such;
11. class-rule fixture cannot be mistaken for nominal-design claim by the contract;
12. operating-state fixture is representable without a DesignOption ID;
13. ResearchEvidenceBundle allows partial/unresolved research;
14. bundle evidence validates against successor FieldEvidence schema;
15. reference crosscheck entries contain no FieldEvidence identity and cannot satisfy a FieldResolution evidence reference;
16. reference crosscheck works without storing reference field values;
17. existing SLICE-0003–0010 tests remain green;
18. repository validator, Ruff, formatting, strict mypy, branch coverage >=90% and dependency audit pass.

## Expected touch points

Prefer a bounded set such as:

- new successor FieldEvidence / evidence-applicability / research-bundle schemas under `specs/`;
- `src/hullq/domain/provenance.py` or one tightly scoped adjacent module;
- focused unit/contract tests;
- compact benchmark-derived fixtures;
- SLICE-0012 handoff docs.

Do not change BoatDesign/BoatModel/ResolvedConfiguration schemas unless a hard contradiction makes the lossless evidence bundle impossible. Report such a contradiction instead.

## Acceptance criteria

- [ ] source/document EvidenceType and observation claim semantics are separate, exact and versioned;
- [ ] evidence applicability can preserve year/hull/market/variant/option/state/individual-hull scope without inventing canonical facts;
- [ ] successor FieldEvidence preserves all accepted provenance invariants;
- [ ] legacy evidence cannot silently become nominal/global during migration;
- [ ] a versioned ResearchEvidenceBundle can carry partial source-linked research losslessly;
- [ ] reference crosscheck data is structurally separate from canonical evidence/provenance;
- [ ] benchmark-derived fixtures for applicability, class-rule semantics, individual hull and operating state pass;
- [ ] no PostgreSQL, autonomous acquisition, resolution policy or broad taxonomy work is introduced;
- [ ] existing behavior remains backward-compatible;
- [ ] local quality gates and required remote CI pass before acceptance.

## Status handoff rule

This slice remains `BLOCKED` until SLICE-0011 is accepted/DONE. Once unblocked it may be set `READY` by the master/owner. The implementation agent MUST NOT start it from this draft branch and MUST NOT mark it `DONE`.

After SLICE-0012 acceptance, the intended next bounded implementation is **PostgreSQL persistence + deterministic ResearchEvidenceBundle importer**, followed by executing the same 50-design benchmark through that path to measure actual automation/review/idempotency/cost behavior.
