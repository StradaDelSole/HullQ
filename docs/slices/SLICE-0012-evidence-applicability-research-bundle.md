# SLICE-0012 — Evidence Applicability and Research Bundle Contract

**ID:** SLICE-0012  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 2.12 — benchmark-driven contract hardening before persistence  
**Depends on:** SLICE-0011 accepted / DONE  
**Blocks:** first PostgreSQL persistence/import slice

**Authorization:** READY after explicit project-owner acceptance of SLICE-0011, successful merge of PR #22, and canonical merge commit `668e91937d27dc9c70760301b92ce0ded41abb2f`.

## Objective

Close the **smallest lossless-data gaps proven by the 50-design controlled benchmark** before HullQ freezes a physical PostgreSQL schema:

1. introduce a **pre-canonical ResearchObservation** boundary because a ResearchJob target is intentionally only raw `manufacturer / model / first_built` and may not yet have a stable HullQ provenance subject;
2. distinguish the **source/document class** of an observation from the **semantic kind of claim** made by that observation;
3. preserve structured **applicability/scope** for observations/evidence that apply only to a production subset, option/variant/state or individual hull;
4. define one deterministic, machine-ingestible **ResearchEvidenceBundle** plus an explicit promotion boundary from ResearchObservation to successor FieldEvidence after canonical subject identity is known.

This slice is intentionally not PostgreSQL and not another broad domain redesign.

```text
ResearchJob.target
(raw manufacturer / model / first_built)
        ↓
independent source-linked ResearchObservation(s)
        + raw observation
        + optional normalized candidate
        + claim semantics
        + applicability/scope
        ↓
ResearchEvidenceBundle
        ↓
identity resolution / stable HullQ subject supplied explicitly
        ↓
deterministic explicit promotion
        ↓
successor FieldEvidence
        ↓
existing FieldResolution/provenance boundary later

NO canonical auto-resolution
NO database writes
NO network acquisition
```

## Why the pre-canonical boundary is mandatory

The accepted `ResearchJob` runtime deliberately defines `ResearchTarget` as only:

```text
manufacturer
model
first_built
```

and explicitly says the raw manufacturer label does **not** assert a canonical Brand or Organization role. ResearchJob also does not write canonical BoatDesign identity.

By contrast, accepted `FieldEvidence v0.2` requires a stable typed `ProvenanceSubject`.

Therefore a ResearchEvidenceBundle MUST NOT require every newly researched observation to already be FieldEvidence. Doing so would force premature BoatModel/BoatDesign identity creation exactly where the benchmark shows identity/generation ambiguity is common.

SLICE-0012 must preserve this distinction explicitly.

## Benchmark evidence for this slice

The controlling evidence is:

- `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`;
- `research/benchmark/BENCHMARK-50-classification.csv`;
- `research/benchmark/BENCHMARK-50-analysis.md`;
- Waves 01–06 under `research/benchmark/waves/`;
- retained pre-contract exports under `research/benchmark/legacy-observations/`.

The manually coded stress corpus found:

- 32/50 designs where temporal/production applicability materially mattered;
- 30/50 where identity/generation/lineage semantics materially mattered;
- 30/50 where option/variant/state semantics materially mattered;
- 22/50 where measurement/definition basis materially mattered;
- 20/50 with a material explicit conflict/unresolved issue;
- repeated cases where class-rule, individual-hull, nominal-design and operating-state values would be semantically wrong if stored as indistinguishable scalar evidence.

These are stress-corpus incidences, not population prevalence estimates.

## Controlling accepted artifacts

Preserve the accepted semantics of:

- ADR-0004 / `specs/IDENTITY_MODEL.v0.2.md`;
- ADR-0006 provenance model;
- `specs/RESEARCH_JOB_SCHEMA.v0.1.json` and `src/hullq/research/jobs.py`;
- `specs/FIELD_EVIDENCE_SCHEMA.v0.2.json`;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.2.json`;
- `specs/PROVENANCE_SUBJECT_SCHEMA.v0.1.json`;
- `src/hullq/domain/provenance.py`;
- `src/hullq/domain/measurements.py`;
- `src/hullq/domain/configuration.py`;
- accepted source-rights / ResearchJob runtime.

Existing versioned schemas MUST NOT be silently mutated. Successor contracts require new versions.

## In scope

### 1. Pre-canonical ResearchObservation

Add one immutable versioned ResearchObservation contract for a source-linked observation captured while the ResearchJob target may still be unresolved as a canonical HullQ subject.

It must preserve at least:

- stable `observation_id` supplied by caller;
- source ID and source locator;
- raw observation snapshot;
- optional normalized candidate kept separate from raw;
- existing source/document `EvidenceType` or equivalent exact vocabulary reuse;
- producer metadata and ResearchJob/activity context;
- observed/retrieved timestamp;
- confidence;
- claim semantics;
- applicability/scope;
- optional intended subject-kind hint and intended field pointer where research has enough context;
- bounded notes;
- append/supersede linkage if correction history is supported in this slice.

Rules:

- ResearchObservation MUST NOT require a canonical `ProvenanceSubject`;
- an optional subject-kind hint MUST NOT assert canonical identity;
- an intended field pointer is a research mapping candidate until promotion and MUST NOT itself write a canonical object;
- raw and normalized values remain independently snapshot-safe;
- absence of a canonical subject is normal, not an error;
- no hidden generation/identity inference is allowed.

Do not introduce a general arbitrary research property graph.

### 2. Claim semantics separate from evidence/source type

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

### 3. Observation/evidence applicability and scope

Introduce the smallest immutable structured applicability boundary needed to preserve scope before and after canonical subject promotion.

It must be able to retain, where known:

- first/last applicable production year;
- hull/build-number from/to;
- market/region when relevant;
- named-variant reference/hint;
- design-option reference/hint(s);
- operating-state reference without inventing a DesignOption;
- individual-hull/listing/build reference;
- explicit unknown/unbounded applicability.

Do not require all fields to be populated. Unknown boundaries are normal.

At minimum enforce:

- year range consistency;
- non-empty refs when a corresponding scoped dimension is asserted;
- snapshot safety for caller-owned collections;
- no implication that absent applicability metadata means `all production`;
- no conversion of an individual-hull observation into a design-wide observation;
- applicability timestamps/ranges remain independent from observation/retrieval timestamp.

A generic arbitrary property graph is out of scope.

### 4. Successor FieldEvidence contract and explicit promotion

Add a successor FieldEvidence schema version that retains every accepted v0.2 provenance property and adds the new claim/applicability semantics.

Also provide one explicit deterministic promotion boundary:

```text
ResearchObservation
+ caller-supplied stable ProvenanceSubject
+ final validated field pointer
+ caller-supplied evidence ID / promotion metadata as required
→ successor FieldEvidence
```

Promotion rules:

- canonical subject MUST be supplied explicitly by the caller after identity resolution; promotion MUST NOT invent or fuzzy-match it;
- the ResearchObservation raw snapshot, normalized candidate, source locator, producer/research context, confidence, claim semantics and applicability MUST survive promotion losslessly;
- promotion must validate any subject-kind hint / intended field mapping rather than silently ignoring a contradiction;
- promotion does not create FieldResolution and does not decide whether the candidate is canonical;
- reference crosscheck material cannot be promoted to FieldEvidence through this path.

Legacy migration rules:

- v0.2 remains immutable and valid as its own historical contract;
- no in-place mutation of v0.2 schema;
- any explicit v0.2 → successor adapter MUST map missing claim/applicability to explicit unknown/unresolved semantics, not to `nominal_design_value` or global applicability;
- raw observation and normalized candidate remain separate and snapshot-safe;
- `observed_at` remains observation/retrieval time and MUST NOT be reused as applicability time.

FieldResolution does not need a semantic redesign in this slice unless a hard compatibility contradiction is found. Existing resolved/conflict/unknown/review states should remain reusable.

### 5. ResearchEvidenceBundle contract

Define one versioned machine-ingestible bundle for research handoff.

The bundle must contain at least:

- schema/bundle version and stable bundle ID;
- exact ResearchTarget snapshot (`manufacturer`, `model`, `first_built`) or equivalent accepted research-target reference;
- research job/activity identifiers where available;
- the set of source-linked **ResearchObservation** records;
- explicit unresolved/review findings that are not yet FieldResolution;
- optional already-promoted successor FieldEvidence only if the bundle format can keep it unambiguous and without requiring promotion;
- optional **reference crosscheck outcomes** in a separate non-provenance section.

The bundle MUST NOT require canonical BoatModel/BoatDesign IDs to exist.

The bundle MUST support partial research and identity ambiguity.

### 6. Reference crosscheck boundary

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

- reference comparison MUST NOT create ResearchObservation or FieldEvidence;
- the crosscheck contract MUST NOT require or encourage storing SailboatData field values;
- it may identify the topic/field compared and contain bounded notes;
- it MUST be impossible for a crosscheck entry to be promoted to FieldEvidence or referenced as supporting evidence by FieldResolution through an evidence ID;
- this policy is specific to current benchmark/reference handling and does not replace the general source-rights model.

### 7. Runtime/value objects and validation

Add the smallest runtime/value-object support needed for the new schemas, preferably alongside the existing research/provenance boundaries rather than as a separate service.

Requirements:

- typed exact vocabularies;
- immutable/snapshot-safe collections;
- deterministic validation;
- schema/runtime enum parity tests;
- ResearchObservation remains pre-canonical;
- successor FieldEvidence integrates with existing evidence invariant checks without weakening them;
- promotion is explicit and deterministic;
- bundle validation is deterministic/offline;
- no hidden clock/UUID generation in pure validation/promotion logic.

### 8. Fixtures from real benchmark cases

Add compact fixtures/tests derived from the benchmark, without copying SailboatData values as evidence.

At minimum cover:

- unresolved ResearchTarget with observations but no canonical ProvenanceSubject;
- Pearson 35 — 1979-specific applicability;
- Catalina 316 or Bavaria 38 — configuration-sensitive mass with explicit source basis;
- J/105 — class-rule constraint distinct from nominal builder specification;
- Gemini 105Mc — operating-state evidence without creating a fake factory option;
- a broker/individual-hull observation that cannot silently become BoatDesign baseline;
- explicit promotion of one pre-canonical observation after a stable subject is supplied;
- failed/blocked promotion when subject-kind or field mapping contradicts the research observation;
- one reference crosscheck entry that remains outside both ResearchObservation and FieldEvidence.

The retained Wave 01/02 pre-contract exports may be used only as migration/research-shape fixtures; they are not canonical contracts themselves.

## Explicitly out of scope

Do not implement:

- PostgreSQL/SQLAlchemy/ORM/migrations;
- physical persistence tables;
- broad ingestion;
- autonomous web research/crawling;
- new source adapters;
- fuzzy/canonical identity resolution;
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

1. ResearchObservation can exist with the accepted raw ResearchTarget and no canonical ProvenanceSubject;
2. ResearchObservation cannot silently manufacture a canonical subject;
3. exact claim-semantics vocabulary parity between schema/runtime;
4. claim semantics remain independent of existing `EvidenceType`;
5. applicability accepts unknown/partial boundaries;
6. invalid reversed year ranges fail;
7. scoped refs required when that scope is asserted;
8. caller mutation cannot alter stored observation/applicability snapshots;
9. successor FieldEvidence retains all v0.2 raw/normalized/provenance semantics plus claim/applicability;
10. v0.2 adapter, if provided, maps absent new semantics to explicit unknown, never nominal/global defaults;
11. `observed_at` and applicability time remain independent;
12. `individual_hull_value` remains identifiable as such;
13. class-rule fixture cannot be mistaken for nominal-design claim by the contract;
14. operating-state fixture is representable without a DesignOption ID;
15. ResearchEvidenceBundle allows partial/unresolved identity research;
16. bundle observations do not require canonical subject IDs;
17. explicit promotion requires caller-supplied stable ProvenanceSubject;
18. promotion preserves the source/raw/normalized/claim/applicability snapshot losslessly;
19. promotion cannot itself produce FieldResolution or canonical mutation;
20. contradictory subject-kind/field mapping fails closed rather than silently promoting;
21. reference crosscheck entries contain no ResearchObservation/FieldEvidence identity and cannot satisfy a FieldResolution evidence reference;
22. reference crosscheck works without storing reference field values;
23. existing SLICE-0003–0010 tests remain green;
24. repository validator, Ruff, formatting, strict mypy, branch coverage >=90% and dependency audit pass.

## Expected touch points

Prefer a bounded set such as:

- new ResearchObservation / claim-semantics / applicability / successor FieldEvidence / ResearchEvidenceBundle schemas under `specs/`;
- `src/hullq/research/` for pre-canonical research bundle/runtime;
- `src/hullq/domain/provenance.py` only where successor FieldEvidence/promotion integration is needed;
- focused unit/contract tests;
- compact benchmark-derived fixtures;
- SLICE-0012 handoff docs.

Do not change BoatDesign/BoatModel/ResolvedConfiguration schemas unless a hard contradiction makes the lossless observation/promotion boundary impossible. Report such a contradiction instead.

## Acceptance criteria

- [ ] pre-canonical ResearchObservation is explicit and does not require canonical identity;
- [ ] source/document EvidenceType and observation claim semantics are separate, exact and versioned;
- [ ] applicability can preserve year/hull/market/variant/option/state/individual-hull scope without inventing canonical facts;
- [ ] successor FieldEvidence preserves all accepted provenance invariants;
- [ ] promotion to FieldEvidence requires explicit caller-supplied stable subject and does not perform identity resolution;
- [ ] legacy evidence cannot silently become nominal/global during migration;
- [ ] a versioned ResearchEvidenceBundle can carry partial source-linked research losslessly before identity resolution;
- [ ] reference crosscheck data is structurally separate from ResearchObservation and canonical evidence/provenance;
- [ ] benchmark-derived fixtures for pre-canonical research, applicability, class-rule semantics, individual hull, operating state and promotion pass;
- [ ] no PostgreSQL, autonomous acquisition, identity resolver, resolution policy or broad taxonomy work is introduced;
- [ ] existing behavior remains backward-compatible;
- [ ] local quality gates and required remote CI pass before acceptance.

## Status handoff rule

SLICE-0012 is now `READY` after SLICE-0011 owner acceptance and merge. It may be started only through the normal `START_SLICE.bat` isolated worktree workflow. The implementation agent MAY set `IN_PROGRESS`, `BLOCKED` or `REVIEW` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent master review and explicit project-owner acceptance. A successful implementation therefore normally hands the slice off in `REVIEW` with a mandatory completion report.

The implementation agent MUST NOT begin SLICE-0013 or any PostgreSQL work automatically.

After SLICE-0012 acceptance, the intended next bounded implementation is **PostgreSQL persistence + deterministic ResearchEvidenceBundle importer**, followed by explicit identity/promotion processing and execution of the same 50-design benchmark through that path to measure actual automation/review/idempotency/cost behavior.

---

## Amendment completion report — blocking-review fixes (2026-08-20)

Addresses the three blocking issues raised in independent PR #24 review.

### Slice

- Slice ID: `SLICE-0012`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Changes

- `src/hullq/domain/provenance.py` — `ObservationApplicability.__post_init__` now rejects empty strings for all six string scope dimensions: `hull_number_from`, `hull_number_to`, `market_or_region`, `named_variant_hint`, `operating_state_hint`, `individual_hull_or_listing_ref` (Issue 1 runtime fix)
- `specs/OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json` — added `"minLength": 1` to all six non-null string dimension properties; sharpened description wording to clarify null means unknown, not global/all-production (Issue 1 schema fix)
- `fixtures/research_observations/valid/obs_pearson35_1979_applicability.json` — corrected `activity_id` from `WAVE-01` to `WAVE-06` (B06-004); cleared invented source locator page/section/table (all null); updated source_id to `SRC-PEARSON35-ARCHIVE` (Issue 2)
- `fixtures/research_observations/valid/obs_j105_class_rule.json` — corrected `activity_id` from `WAVE-03` to `WAVE-06` (B06-008); cleared invented source locator section/anchor; replaced invented numeric class-rule value with explicitly synthetic text fragment; removed normalized_candidate (Issue 2)
- `fixtures/research_observations/valid/obs_gemini105mc_mast_down.json` — DELETED (invented mast-down scenario for B06-007, wrong Wave) (Issue 2)
- `fixtures/research_observations/valid/obs_gemini105mc_board_state.json` — CREATED replacing the deleted fixture; represents B06-007 Wave 06 accepted benchmark case: leeward centerboard deployment operating state; `activity_id` WAVE-06; source locator all null; no DesignOption ID invented (Issue 2)
- `fixtures/research_observations/valid/obs_broker_individual_hull.json` — corrected `activity_id` from `WAVE-05` to `WAVE-06` (B06-009 Bavaria 38); replaced invented numeric displacement value with explicit synthetic text fragment; removed normalized_candidate; updated source_id to `SRC-BROKER-LISTING-SYNTHETIC` (Issue 2)
- `fixtures/research_observations/valid/bundle_unresolved_identity.json` — removed fabricated `first_built: 2001` (now null) and fabricated 9600 lbs displacement; replaced with TWO observations using accepted B02-009 Wave 02 retained benchmark evidence: Shoal Bulb Keel 12,400 lb Half Load and Fin Keel 12,000 lb Half Load, each with correct `design_option_hints`; updated `related_observation_ids` in unresolved_finding; `activity_id` already WAVE-02 (Issue 2)
- `tests/unit/test_research_observations.py` — removed numeric SailboatData values from `test_reference_crosscheck_has_no_evidence_id` notes; added `test_reference_crosscheck_outcome_only_no_numeric_values` regression test; added 6 new runtime validation tests for empty-string rejection (one per scope dimension) plus one positive-case acceptance test (Issues 1 and 3)
- `tests/contract/test_research_bundle_contracts.py` — added 7 new JSON schema contract tests for empty-string rejection on each string scope dimension plus one positive-case test (Issue 1 schema)
- `tests/contract/test_research_observation_fixtures.py` — renamed all Gemini `mast_down` test functions to `board_state`; updated fixture filename reference and `operating_state_hint` assertion to `leeward_board_only_deployed` (Issue 2)

### Validation

- Local validation: `PASS`
- Commands run:
  - `uv run python -m coverage run -m pytest -x -q`
  - `uv run python -m coverage report --fail-under=90`
  - `uv run ruff check .`
  - `uv run ruff format --check .`
  - `uv run mypy src/ --strict`
  - `uv run pip-audit`
  - `uv run python -c "from hullq.contracts import ContractRegistry; ..."`
- Results:
  - 1080 passed, 2 skipped (14 net-new tests: 6 unit + 7 contract + 1 regression)
  - Branch coverage: 93.33% (≥90% threshold passes)
  - Ruff: all checks passed, 147 files formatted
  - mypy: no issues found in 17 source files (strict)
  - pip-audit: no known vulnerabilities found
  - ContractRegistry: 27 schemas loaded without error

### External verification

- Remote CI: `NOT VERIFIED` (branch pushed to GitHub; CI result not yet observed locally)
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none
- Spec/ADR ambiguities: none
- Scope deviations: none — only the three blocking issues from PR #24 were addressed

### Benchmark audit confirmation

All five benchmark-derived fixtures audited against `research/benchmark/waves/WAVE-02-summary.md` and `research/benchmark/waves/WAVE-06-summary.md` and `research/benchmark/CONTROLLED_BENCHMARK_LEDGER.md`:

| Fixture | Design | Correct Wave | Issues found | Resolution |
|---|---|---|---|---|
| `obs_pearson35_1979_applicability.json` | B06-004 Pearson 35 | WAVE-06 | Wrong wave (was WAVE-01), invented page/section/table | Fixed |
| `obs_j105_class_rule.json` | B06-008 J/105 | WAVE-06 | Wrong wave (was WAVE-03), invented section/anchor, invented numeric value | Fixed — value replaced with synthetic |
| `obs_gemini105mc_mast_down.json` | B06-007 Gemini 105Mc | WAVE-06 | Wrong wave (WAVE-04), wrong scenario (mast-down not in Wave 06), invented value | Deleted; replaced with `obs_gemini105mc_board_state.json` |
| `obs_broker_individual_hull.json` | B06-009 Bavaria 38 | WAVE-06 | Wrong wave (was WAVE-05), invented numeric displacement value | Fixed — value replaced with synthetic |
| `bundle_unresolved_identity.json` | B02-009 Catalina 316 | WAVE-02 | Invented `first_built: 2001`, invented 9600 lbs displacement | Fixed — uses accepted retained benchmark evidence (12,400 lb Shoal Bulb, 12,000 lb Fin Keel) |

No SailboatData field values remain in any SLICE-0012 test or fixture.

### Follow-up

- Recommended next action: independent review of PR #24 amendment; remote CI observation; project-owner acceptance if satisfied

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- SLICE-0013 was not started.
- The agent has NOT marked this slice `DONE`.

---

## Amendment completion report — provenance-integrity fixes (2026-08-20)

Addresses the provenance-integrity blocking issue raised in the second PR #24 review cycle.

### Slice

- Slice ID: `SLICE-0012`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`

### Changes

- `fixtures/research_observations/valid/obs_pearson35_1979_applicability.json` — producer changed to `deterministic_tool / slice-0012-fixture-builder / model:null`; source_id prefixed `SYNTHETIC-SRC-`; research_job_id prefixed `SYNTHETIC-JOB-`; observation_id prefixed `SYNTHETIC-OBS-`; notes clearly distinguish benchmark fact from synthetic scaffolding
- `fixtures/research_observations/valid/obs_j105_class_rule.json` — same producer/source/job/obs-id corrections as above
- `fixtures/research_observations/valid/obs_gemini105mc_board_state.json` — same producer/source/job/obs-id corrections as above
- `fixtures/research_observations/valid/obs_broker_individual_hull.json` — same producer/source/job/obs-id corrections as above; source_id renamed from `SRC-BROKER-LISTING-SYNTHETIC` to `SYNTHETIC-SRC-BROKER-LISTING-REF`
- `fixtures/research_observations/valid/bundle_unresolved_identity.json` — both observations updated with synthetic producer; bundle_id, research_job_id, crosscheck_id, finding_id all prefixed `SYNTHETIC-`; unresolved_finding description completely rewritten to be explicitly synthetic contract scaffolding; retained benchmark facts (Shoal Bulb Keel 12,400 lb / Fin Keel 12,000 lb) preserved with `BENCHMARK FACT:` prefix in notes
- `tests/contract/test_research_observation_fixtures.py` — added 4 new regression tests: `test_no_observation_fixture_claims_claude_as_producer`, `test_all_observation_fixtures_use_synthetic_fixture_producer`, `test_bundle_fixture_observations_use_synthetic_fixture_producer`, `test_catalina_unresolved_finding_is_explicitly_synthetic`

### Validation

- Local validation: `PASS`
- Commands run: `uv run python -m coverage run -m pytest -x -q`, `uv run python -m coverage report --fail-under=90`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy src/ --strict`, `uv run pip-audit`, ContractRegistry load check
- Results: (see gate output below)

### External verification

- Remote CI: `NOT VERIFIED` (branch pushed to GitHub; CI result not yet observed locally)
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none
- Spec/ADR ambiguities: none
- Scope deviations: none — only fixture provenance-integrity issues addressed

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- SLICE-0013 was not started.
- The agent has NOT marked this slice `DONE`.
- No fixture falsely attributes benchmark research to Claude.
- No synthetic provenance metadata is presented as historical fact.
