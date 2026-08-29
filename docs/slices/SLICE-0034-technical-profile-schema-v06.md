# SLICE-0034 — Technical profile schema v0.6

**ID:** SLICE-0034  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Continuous Data Track B — product-search technical profile contract  
**Depends on:** SLICE-0033 accepted / DONE; `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`; current BoatDesign v0.5 identity/configuration contracts  
**Blocks:** first bounded high-footprint canonical BoatDesign profile corpus and practical OQ-009 search benchmark

## Objective

Evolve the canonical BoatDesign contract from v0.5 to a v0.6 technical-profile schema that can represent HullQ's accepted search-relevant field breadth — especially richer rig, cockpit/helm, appendage, propulsion and accommodation structure — without promoting any research/reference data or changing search truth semantics.

This slice changes the **shape HullQ can truthfully store**, not the production dataset.

## Why this slice exists

SLICE-0033 created the first trustworthy numeric search kernel. The parallel real-boat pilot then showed that the current BoatDesign v0.5 technical shape is too compressed for the product HullQ intends to build:

- `rig_type` combines sailplan and masthead/fractional semantics that users may want to filter independently;
- `rudder_type` does not cleanly separate position/support/balance semantics;
- cockpit position, helm configuration, detailed rig dimensions and several practical buyer fields are absent or under-structured;
- modern boats require options/specification epochs to remain explicit rather than averaged into one baseline;
- classical boats demonstrate that apparently contradictory labels can describe different technical dimensions at the same time.

The Project Owner accepted SailboatData as a breadth/completeness reference while explicitly requiring HullQ to structure the data more usefully and to keep source-rights/provenance boundaries intact. The repo therefore needs one bounded schema evolution before the first serious high-footprint canonical profile corpus and practical search benchmark.

This is not a return to sequential calibration. It is a concrete implementation dependency for richer product search.

## Controlling artifacts

- `specs/TECHNICAL_PROFILE_SPEC.v0.1.md` — accepted information requirements, research priority and 6/8-eye conflict protocol.
- `specs/BOAT_DESIGN_SCHEMA.v0.5.json` — predecessor BoatDesign contract.
- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` — unchanged fail-closed search truth semantics.
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json` and provenance contracts — unchanged canonical evidence/resolution boundary.
- `specs/DERIVED_METRICS_SPEC.v1.0.md` — existing accepted derived-methodology boundary.
- ADR-0004 / ADR-0011 identity semantics and existing Brand/Organization/BoatModel relationships.
- Source Rights Policy remains controlling; SailboatData/reference breadth does not imply ingestion rights.

## In scope

1. Add `specs/BOAT_DESIGN_SCHEMA.v0.6.json` superseding v0.5 for new BoatDesign payloads while preserving accepted identity/generation/builder/designer/variant/option/quality semantics.
2. Keep the schema structurally grouped; do **not** create a flat 120-field object merely because the information catalogue is broad.
3. Extend baseline technical structure so the following information can be represented independently where applicable:
   - additional principal dimensions such as LOD and beam at waterline;
   - displacement basis/condition and ballast type/material as explicit data rather than ambiguous notes;
   - richer keel/movable-appendage representation while retaining current accepted keel semantics;
   - rudder position, support and balance/type as separately representable dimensions; retain rudder count;
   - rig sailplan, masthead/fractional character, mast count, mast step and rig variant;
   - rig dimensions I/J/P/E plus PY/EY/ISP/JP/SPL-or-TPS where applicable;
   - mast-height basis where represented;
   - reported/component/calculated sail-area semantics without confusing reported facts with HullQ derivation;
   - cockpit position/count;
   - helm/steering type/count;
   - deck-saloon/pilothouse flag/configuration where known;
   - propulsion engine count, drive type and propeller configuration while retaining basic engine fields;
   - cabins/berths/heads while retaining headroom;
   - CE/design category where applicable.
4. Ensure all added technical families can also be represented in NamedVariant/DesignOption overrides where the property is option-sensitive. Avoid a schema where baseline is rich but options can only override the old v0.5 subset.
5. Preserve explicit null/unknown semantics. Sparse canonical BoatDesigns remain valid where the controlling schema permits null/unknown; no fake completeness.
6. Preserve configuration/applicability semantics: multiple valid production configurations must be representable without averages or arbitrary merged values.
7. Add/extend reusable schema definitions if this materially reduces duplication and keeps baseline/override contracts coherent.
8. Register v0.6 in the repository contract registry/validator as required by the existing schema-validation mechanism.
9. Add contract fixtures covering at minimum four structural archetypes:
   - classic aft-cockpit masthead-sloop with long/full-keel + separately modeled rudder semantics;
   - center-cockpit cruiser demonstrating cockpit filtering data;
   - modern production cruiser with standard vs shallow-draft option and single/twin helm option;
   - standard vs performance rig/keel variant demonstrating rig-dimension/option overrides.
   Fixtures MUST be explicitly synthetic unless they are independently rights/provenance-cleared; no real-world facts are needed to satisfy schema behavior.
10. Add contract/unit tests proving v0.6 validates the intended structures and rejects semantic-shape tampering.
11. Document a deterministic v0.5 -> v0.6 compatibility/mapping note for concepts that changed shape, especially combined `rig_type` and rudder semantics. This need not be a production data migration.

## Required schema semantics

### A. Rig decomposition

v0.6 MUST allow HullQ to distinguish at least:

- sailplan (`sloop`, `cutter`, `ketch`, `yawl`, `schooner`, `cat`, `other`, `unknown` or equivalent controlled vocabulary);
- masthead/fractional character independently from sailplan where meaningful;
- mast count;
- mast step;
- rig variant/specification label when it carries technical applicability;
- structured rig dimensions.

A masthead sloop and fractional sloop MUST be distinguishable without requiring opaque free-text parsing.

### B. Appendage decomposition

v0.6 MUST avoid forcing all rudder facts into one mutually-exclusive label if real designs can simultaneously be described by different dimensions such as transom position and keel/skeg support.

At minimum preserve independent representation for:

- rudder count;
- rudder position;
- rudder support;
- rudder balance/type where useful;
- skeg presence/type;
- keel type/subtype/options;
- centerboard/daggerboard counts/types where applicable.

### C. Cockpit and helm

Cockpit position is a CORE_SEARCH field. v0.6 MUST represent center-cockpit vs aft-cockpit without free-text inference.

Helm type/count MUST support production options such as one vs two wheel helms without inventing a baseline average or claiming every configuration has both.

### D. Technical basis semantics

Where a number changes meaning depending on basis/condition, v0.6 MUST provide enough structure to avoid silently comparing unlike facts. Examples include displacement basis, sail-area basis and mast-height reference/basis.

The schema need not solve every future measurement ontology in this slice, but it MUST NOT make known basis distinctions impossible to represent.

### E. Variant/option symmetry

Any newly added search-significant property that can differ by NamedVariant/DesignOption MUST be override-capable using the same semantic shape or a clearly equivalent reusable override schema.

### F. No source promotion

This slice MUST NOT:

- admit Rustler 36, Contessa 32, Bavaria Cruiser 34, Sun Odyssey 36i, Albin Vega, Rival 34 or any other real BoatDesign merely because they motivated the schema;
- treat SailboatData/reference values as canonical;
- mutate the 1,770-record research-evidence corpus;
- resolve source conflicts by schema declaration.

## Explicitly out of scope

- Categorical search evaluator implementation.
- PostgreSQL search read-model/index work.
- Practical OQ-009 benchmark execution.
- Real-world canonical priority-corpus admission.
- New source scraping/retrieval campaign.
- FastAPI/public HTTP endpoints.
- Astro/frontend/SEO.
- OQ-020 geography, OQ-005 listing dedup, market adapters, monitoring/alerts/auth/pricing.
- New derived formulas beyond already accepted methodology.
- A generic bluewater/seaworthiness score.
- Database migration solely to normalize every new technical property into dedicated SQL columns; canonical BoatDesign JSONB persistence may remain opaque if current importer/readback can round-trip v0.6 safely.

## Deliverables

- `specs/BOAT_DESIGN_SCHEMA.v0.6.json`.
- Any small reusable schema definitions required by v0.6.
- Contract-registry updates needed for validation.
- v0.6 synthetic contract fixtures covering the required archetypes/options.
- focused schema/contract/unit tests.
- concise `docs/engineering/` or schema-adjacent compatibility note describing v0.5 -> v0.6 technical-shape mapping, especially rig/rudder evolution.

## Acceptance criteria

- [ ] `BOAT_DESIGN_SCHEMA.v0.6.json` validates and is registered by the repo validator.
- [ ] v0.6 preserves stable BoatDesign identity/generation/relationship semantics from v0.5 rather than minting new identity rules.
- [ ] LOA/LWL/beam/draft/displacement/ballast/sail-area predecessor fields remain representable without loss.
- [ ] LOD and beam-at-waterline are representable as optional technical dimensions.
- [ ] Sailplan and masthead/fractional character are independently representable.
- [ ] Mast count, mast step and detailed rig dimensions are structurally representable.
- [ ] Rudder position and rudder support are independently representable; a test proves a transom-positioned rudder can also carry keel/skeg-support semantics without contradiction.
- [ ] Keel/skeg/centerboard/daggerboard data remain independently representable.
- [ ] Cockpit position/count and helm type/count are structurally representable and override-capable.
- [ ] Propulsion drive/engine-count/propeller and accommodation cabin/berth/head fields are representable without breaking existing cruising fields.
- [ ] Measurement/input-basis distinctions needed by current accepted derived/search semantics are not lost.
- [ ] Newly added search-significant technical properties that may vary by option/variant are override-capable.
- [ ] Synthetic fixtures cover classic aft-cockpit, center-cockpit, modern shallow-draft/single-vs-twin-helm and performance-rig archetypes.
- [ ] Tests reject unknown extra properties where the schema claims a closed object; malformed enum/count/range/basis shapes fail closed.
- [ ] Existing v0.5 fixtures/contracts continue to validate under their own schema; no silent historical contract rewrite.
- [ ] No real-world BoatDesign data is admitted or promoted in this slice.
- [ ] No OQ-009 search semantics are weakened or changed.
- [ ] Ruff format/check, mypy, repository validator, full pytest and repo coverage >=90% pass.
- [ ] Exact-head CI and Manufacturer artifact reproducibility pass.

## Adversarial review checklist

Before recommending REVIEW, explicitly test or inspect:

1. Can a field added to baseline be impossible to express in a NamedVariant/DesignOption override even though it is naturally option-sensitive?
2. Can `rig` or `rudder` still require an opaque compound label for one of the required archetypes?
3. Can a malformed enum/count/non-finite number enter because JSON Schema treats it unexpectedly?
4. Can a fixture control a normative enum/key set used by its own verifier?
5. Did any real-world reference fact silently become canonical because it motivated a fixture?
6. Did v0.6 accidentally redefine BoatDesign identity, builder-change semantics or OQ-009 truth rules?

Any YES requires repair or an explicit stop/report.

## Expected touch points

- `specs/BOAT_DESIGN_SCHEMA.v0.6.json`
- optional new reusable schema file(s) under `specs/`
- `src/hullq/contracts/registry.py` if required
- `fixtures/identity/` and/or a new explicit `fixtures/technical_profile/`
- `tests/contract/` and focused `tests/unit/`
- one small compatibility note under `docs/engineering/` or `specs/`

Do not modify search engine behavior, persistence migrations, market code or frontend code unless an unavoidable contract break is found; stop and report instead of widening scope.

## Validation

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python -m pytest
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run python scripts/validate_repository.py
```

Run any focused schema-validation command/test added by the slice.

## Stop conditions

Stop and report instead of inventing a solution if:

- v0.6 requires redefining stable BoatDesign identity semantics;
- a required field needs a normative taxonomy decision that cannot be safely bounded from `TECHNICAL_PROFILE_SPEC.v0.1.md` and predecessor vocabularies;
- implementing the schema would require bulk/reference data ingestion or real-world canonical promotion;
- a database migration becomes necessary for correctness rather than optional optimization;
- search/public API/frontend behavior becomes necessary to satisfy the schema contract.

## Status handoff rule

The implementation agent may leave `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark the slice DONE or merge it.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md` concisely. In addition report:

- exact v0.6 technical families added/changed;
- exact predecessor fields preserved or mapped;
- fixture archetypes added;
- explicit answer to all six adversarial checklist questions;
- confirmation that no real-world BoatDesign/reference value was promoted;
- exact final HEAD and exact-head CI/Manufacturer state;
- no next slice started.
