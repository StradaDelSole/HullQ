# SLICE-0035 — Acceptance Closure

**ID:** SLICE-0035  
**Closure status:** OWNER_ACCEPTED  
**Owner accepted:** YES — 2026-08-30, explicitly after final exact-head ACCEPT review  
**Final independent-review verdict:** ACCEPT — implementation plus three bounded amendment rounds reviewed; no blocking findings remain  

## Effective implementation state

SLICE-0035 was implemented on PR #103.

- implementation PR: #103 — `SLICE-0035: categorical + configuration-aware search`;
- initial implementation head: `2e6b4a1f74ff359d9108cc1c31c3aaeda11807b2`;
- first independent review: review `5061056618`, verdict **CHANGES REQUIRED**;
- amendment-1 head: `4112e6110466f2c7921adb5e4bf61b0cca81607e`;
- second independent review: review `5061306361`, verdict **CHANGES REQUIRED**;
- amendment-2 head: `9813a3aece530bee7a83e0352f836d3928ca320c`;
- third independent review: review `5061417331`, verdict **CHANGES REQUIRED**;
- final amendment head: `56e7b669fbe60d6d2d4623ac281e96f5270abf98`;
- final independent review: review `5061503957`, verdict **ACCEPT**;
- implementation merge commit: `96ae38c556d61154497f5b5827a195c7b48d6a12`;
- final exact-head CI: run `33326005447`, SUCCESS;
- final exact-head Manufacturer artifact reproducibility: run `33326005320`, SUCCESS.

The Project Owner explicitly accepted SLICE-0035 after the final independent review of exact implementation head `56e7b669fbe60d6d2d4623ac281e96f5270abf98` and before implementation merge. The effective accepted implementation state is therefore main at merge commit `96ae38c556d61154497f5b5827a195c7b48d6a12`.

## Delivered increment

SLICE-0035 extends the accepted HullQ search kernel from the SLICE-0033 numeric MUST vertical to a bounded categorical + configuration-aware search capability while preserving OQ-009 fail-closed semantics.

The delivered increment includes:

- categorical MUST exact-equality leaves over already-qualified canonical strings;
- fail-closed categorical qualification with explicit sentinel handling;
- mixed numeric + categorical AND queries through versioned query contract v0.2;
- unchanged read semantics for existing serialized query v0.1;
- persistence-neutral resolved-configuration identity/projection types;
- deterministic configuration-aware BoatDesign evaluation;
- existential confirmed match: one sufficiently resolved matching configuration is enough;
- universal confirmed non-match: exclusion is allowed only when all materially applicable possibilities are sufficiently known and non-matching;
- `CONFIGURATION_AMBIGUOUS` for unresolved/incomplete configuration-space cases;
- exact matching configuration identifiers for explainability;
- explicit OptionConstraint and NamedVariantConstraint dependency/applicability boundaries;
- synthetic fixtures and deterministic Q1–Q10 capability demo only — no real benchmark BoatDesign admission.

## Review amendments

### Amendment 1 — categorical sentinels and runtime-closed configuration authority

The first independent review found two fail-closed blockers and the follow-up contract audit added the bounded NamedVariant constraint gap:

1. schema-valid categorical semantic sentinels such as `unknown` / `not_applicable` could enter ordinary CONFIRMED equality truth;
2. truth-authorizing configuration controls were not sufficiently runtime-closed against non-bool completeness values, mutable collections and constraint-key mismatch;
3. NamedVariant requires/excludes semantics were not enforced at the resolved-configuration boundary.

The amendment:

- moved reserved-sentinel rejection into `QualifiedCategoricalValue` itself;
- maps resolved `unknown` to MISSING and resolved `not_applicable` to NOT_APPLICABLE;
- requires a genuine bool for `configuration_space_complete`;
- defensively materializes configuration/constraint collections;
- validates constraint mapping-key identity;
- adds explicit `NamedVariantConstraint` requires/excludes enforcement.

### Amendment 2 — explicit applicability and runtime identifier closure

The second review found two remaining Q6-class bypasses:

1. explicit option/variant applicability was still not represented at the resolved-configuration boundary;
2. bare strings and malformed identifier collections could be iterated character-by-character and bypass dependency validation.

The amendment reused the existing `ValueQualification` vocabulary for explicitly caller-supplied OptionConstraint/NamedVariantConstraint applicability and added strict runtime identifier validation.

It established that:

- CONFIRMED applicability participates normally;
- NOT_APPLICABLE referenced options/variants cannot enter a resolved configuration;
- unresolved applicability cannot enter ordinary TRUE/FALSE configuration truth;
- unresolved applicability prevents a truth-authorizing complete configuration-space claim;
- bare `str`/`bytes`, malformed elements, empty identifiers and duplicate identifier collections fail closed before validation authority is granted.

### Amendment 3 — remove implicit CONFIRMED applicability default

The third review found one final fail-closed blocker: OptionConstraint/NamedVariantConstraint applicability still defaulted to `ValueQualification.CONFIRMED`, allowing omitted applicability qualification to become truth-authorizing implicitly.

The final amendment removed that default entirely.

- `applicability` is now a required constructor argument for both constraint types;
- omission fails at the call site rather than becoming CONFIRMED;
- dependency metadata alone cannot imply applicability;
- every known-applicable call site must explicitly state `ValueQualification.CONFIRMED`;
- all previously established NOT_APPLICABLE/unresolved/completeness behavior remains unchanged.

This closed the final adversarial Q6 counterexample without adding generic applicability inference or configuration expansion.

## Exact-head validation evidence

Independent exact-head verification on `56e7b669fbe60d6d2d4623ac281e96f5270abf98` confirmed:

- CI run `33326005447`: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - dependency audit: SUCCESS;
  - PostgreSQL 18 db integration: SUCCESS;
- Manufacturer artifact reproducibility run `33326005320`: SUCCESS;
  - reproduce Ubuntu: SUCCESS;
  - reproduce Windows: SUCCESS.

The final implementation report recorded local validation of 2,673 passed / 217 pre-existing skipped tests, overall coverage 91.74%, every `hullq.search.*` module at 100%, Ruff/mypy clean, repository validator PASS, and deterministic Q1–Q10 demo distributions unchanged through all amendment rounds.

The final adversarial checklist Q1–Q10 was reported all **NO** after explicit verification that Q6 fails closed for invalid dependencies, malformed runtime identifiers, NOT_APPLICABLE, unresolved applicability, and omitted applicability.

## Retained boundaries

SLICE-0035 does not:

- admit or promote any real P0/benchmark BoatDesign;
- run Snapshot A against the real locked corpus;
- relax OQ-009 fail-closed semantics;
- implement generic option/variant configuration expansion;
- infer applicability from model years, hull numbers, labels or schema validity;
- add bounded numeric range-value representation merely to exercise `RANGE_OVERLAPS_THRESHOLD`;
- implement PREFER, ranking, public OR/NOT;
- add PostgreSQL search read-model/index work;
- add FastAPI/public API behavior;
- add frontend/SEO/geography/listing-dedup/monitoring scope.

## Audit trail

- controlling slice contract: `docs/slices/SLICE-0035-categorical-configuration-aware-search.md`;
- controlling search semantics: `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`;
- benchmark capability contract: `specs/SEARCH_BENCHMARK.v0.1.md`;
- BoatDesign contract: `specs/BOAT_DESIGN_SCHEMA.v0.6.json`;
- technical-profile requirements: `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`;
- implementation PR: #103;
- initial implementation head: `2e6b4a1f74ff359d9108cc1c31c3aaeda11807b2`;
- amendment-1 head: `4112e6110466f2c7921adb5e4bf61b0cca81607e`;
- amendment-2 head: `9813a3aece530bee7a83e0352f836d3928ca320c`;
- final implementation head: `56e7b669fbe60d6d2d4623ac281e96f5270abf98`;
- final ACCEPT review: `5061503957`;
- exact-head CI: `33326005447`, SUCCESS;
- exact-head Manufacturer: `33326005320`, SUCCESS;
- implementation merge: `96ae38c556d61154497f5b5827a195c7b48d6a12`;
- Project Owner acceptance: **YES — 2026-08-30**.

## Final disposition

SLICE-0035 has independent exact-head ACCEPT, successful exact-head CI and Manufacturer reproducibility, implementation merge, and explicit Project Owner acceptance.

Once this closure record is reviewed and merged to `main`, SLICE-0035 is DONE and may be cleaned up with the normal finish workflow. No next implementation slice is auto-started by this closure.
