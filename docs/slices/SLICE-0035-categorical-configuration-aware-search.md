# SLICE-0035 — Categorical + configuration-aware search

**ID:** SLICE-0035  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** Product Track A — benchmark-capable technical search  
**Depends on:** SLICE-0034 accepted / DONE; `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`; `specs/SEARCH_BENCHMARK.v0.1.md`; `specs/BOAT_DESIGN_SCHEMA.v0.6.json`  
**Blocks:** first real P0 practical search benchmark Snapshot A over the locked 12-BoatDesign corpus

## Objective

Extend the SLICE-0033 search kernel just enough to execute the locked TB-01 benchmark truthfully: add categorical MUST criteria and explicit configuration-aware evaluation over qualified technical projections, while preserving OQ-009 fail-closed semantics and the existing numeric-MUST behavior.

This slice makes the search engine **benchmark-capable**. It does not admit the real benchmark corpus, build public APIs/UI, add ranking, or weaken truth semantics.

## Why this slice exists

SLICE-0033 implemented numeric MUST + AND over one design-level projection. SLICE-0034 introduced BoatDesign v0.6 with independently structured search dimensions such as sailplan, masthead/fractional character, cockpit position, keel type, rudder support and option/variant-capable technical families.

The locked practical benchmark now includes queries such as:

- `Masthead rig AND Draft <= 1.80 m`;
- `Aft cockpit AND Fin keel AND Draft <= 1.70 m`;
- `Skeg-supported rudder AND LOA 9–12 m`;
- `Center cockpit AND Cutter AND Skeg-supported rudder AND Draft <= 1.80 m`;
- configuration-aware `Draft <= 1.60 m`.

Those cannot be evaluated by the current numeric-only, one-projection-per-design kernel. The next Product Track increment must therefore add categorical equality and explicit resolved-configuration semantics before the real P0 benchmark is run.

## Controlling artifacts

- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md` — binding truth semantics, especially §§1–4, §6, §7, §10 and §12.
- `specs/SEARCH_BENCHMARK.v0.1.md` — locked Q1–Q10, roles, corpus and benchmark metrics.
- `specs/BOAT_DESIGN_SCHEMA.v0.6.json` — technical profile shape and option/variant families.
- `specs/TECHNICAL_PROFILE_SPEC.v0.1.md` — canonical/applicability/conflict boundary.
- Existing `src/hullq/search/` from SLICE-0033 — numeric MUST, AND, qualification and deterministic result surfaces.

If implementation would require weakening any controlling artifact, stop and report rather than reinterpret it.

## In scope

1. Add a typed **categorical MUST leaf** supporting deterministic exact equality against a controlled canonical string value.
2. Reuse the existing three-valued truth semantics and qualification boundary for categorical values:
   - confirmed + equal => TRUE;
   - confirmed + unequal => FALSE;
   - missing/conflict/provisional/applicability-unknown => UNKNOWN with the existing reason where applicable;
   - confirmed NOT_APPLICABLE => FALSE.
3. Add the missing accepted reason codes needed by configuration-aware evaluation, at minimum:
   - `CONFIGURATION_AMBIGUOUS`;
   - `RANGE_OVERLAPS_THRESHOLD` only if the implemented bounded numeric representation actually needs it in this slice. Do not invent a fake range mechanism solely to exercise the enum.
4. Evolve the serializable query contract explicitly so mixed numeric + categorical AND queries can round-trip without silently changing schema-version semantics.
   - Existing serialized query version `0.1` MUST remain readable with identical meaning.
   - A new explicit version (expected `0.2` unless a repository convention requires another value) SHOULD represent categorical leaves without adding silent optional keys to v0.1.
   - Unknown keys/types/versions continue to fail closed.
5. Introduce a persistence-neutral **resolved configuration projection** boundary. Search MUST consume already-qualified technical values; schema-valid raw BoatDesign JSON or raw research evidence MUST NOT become confirmed truth merely because it can be structurally projected.
6. Represent configuration identity/explainability explicitly enough to return which configuration(s) matched. A configuration result SHOULD carry stable identifiers for the BoatDesign plus applicable NamedVariant/DesignOption identifiers (or an equivalent deterministic identity contract).
7. Implement deterministic configuration-aware BoatDesign evaluation:
   - evaluate MUST criteria against explicit resolved configurations;
   - a BoatDesign is `CONFIRMED_MATCH` when at least one verified/resolved configuration satisfies all MUST criteria;
   - matching configuration IDs MUST be returned;
   - do not imply that every configuration matches;
   - if no configuration is a confirmed match and at least one materially possible configuration remains unresolved/ambiguous in a way that could change membership, return `INSUFFICIENT_DATA`, not confirmed non-match;
   - return `CONFIRMED_NON_MATCH` only when all materially applicable resolved possibilities are sufficiently known and none can satisfy the query.
8. Preserve option-sensitive draft semantics. A shallow-draft option may make a design discoverable without changing the baseline/deep configuration. No averaging or arbitrary baseline substitution.
9. Keep configuration composition bounded to information explicitly represented by the qualified input. The resolver/evaluator MUST respect NamedVariant/DesignOption applicability plus `requires_option_ids` / `excludes_option_ids` when those are part of the input contract. It MUST NOT invent combinations the input cannot support.
10. Add synthetic fixtures/tests that exercise all locked benchmark operator shapes needed by Q1–Q10, but do not use the real 12-BoatDesign corpus as canonical data in this slice.
11. Add a small deterministic demo that includes at least:
    - categorical confirmed match/non-match/unknown;
    - a design where only a shallow-draft configuration matches;
    - a design with one matching and one non-matching configuration;
    - a genuinely configuration-ambiguous design that remains insufficient;
    - a mixed categorical + numeric AND query.
12. Preserve SLICE-0033 numeric behavior and its public/internal imports unless an explicit versioned extension is necessary.

## Required behavior

### A. Categorical leaf truth

For a fully qualified categorical value:

- exact canonical equality => TRUE;
- exact canonical inequality => FALSE;
- no fuzzy synonym matching at evaluator time;
- no case-folding/normalization hidden inside truth evaluation unless the projection contract has already canonicalized the value.

For unqualified values:

- `MISSING` => UNKNOWN / `VALUE_MISSING`;
- `UNRESOLVED_CONFLICT` => UNKNOWN / `UNRESOLVED_CONFLICT`;
- `PROVISIONAL` => UNKNOWN / `PROVISIONAL_VALUE`;
- `APPLICABILITY_UNKNOWN` => UNKNOWN / `APPLICABILITY_UNKNOWN`;
- `NOT_APPLICABLE` => FALSE / `NOT_APPLICABLE`.

### B. Mixed AND truth

Numeric and categorical leaves reduce through the same accepted AND rule:

- any FALSE => FALSE;
- all TRUE => TRUE;
- otherwise UNKNOWN.

Criterion ordering may affect explanation order but MUST NOT affect truth.

### C. Configuration truth

Configuration-aware evaluation is existential for confirmed design discovery and universal for confirmed design exclusion:

- **MATCH:** at least one explicit, sufficiently resolved configuration is TRUE for the complete MUST query;
- **NON_MATCH:** every materially applicable configuration that could affect query membership is sufficiently resolved and evaluates FALSE;
- **INSUFFICIENT:** otherwise, including a materially possible unresolved configuration that could still match.

A FALSE configuration does not erase another TRUE configuration. An UNKNOWN configuration cannot be ignored merely to manufacture a design-level NON_MATCH.

### D. Matching configuration identity

For each confirmed BoatDesign match, result metadata MUST identify at least one exact matching resolved configuration. If several match, return them deterministically or return a deterministic complete identity set; do not choose an arbitrary favorite.

### E. Qualification boundary

The configuration layer MUST NOT upgrade data qualification. In particular:

- schema validity != canonical truth;
- whole-profile `quality.status` != field-level search truth;
- provisional/reference evidence != confirmed truth;
- a NamedVariant/DesignOption label alone does not prove every overridden or inherited field.

### F. Compatibility

All existing SLICE-0033 tests for numeric queries and v0.1 serialization MUST continue to pass. Existing numeric results MUST not drift due to the new categorical/configuration code path.

## Benchmark capability target

At slice completion the engine must be able to represent and execute the operator/field shapes of all locked PRIMARY benchmark queries Q1–Q10 on synthetic qualified projections:

- numeric range/min/max for LOA, Beam, Draft, Displacement;
- categorical equality for `rig.masthead_fractional=masthead`;
- `deck.cockpit_position=aft|center`;
- `appendages.keel_type=fin`;
- `appendages.rudder_support=skeg`;
- `rig.sailplan=cutter`;
- mixed categorical + numeric AND;
- configuration-aware draft option cases.

This acceptance target concerns **search capability**, not real benchmark results. The real locked corpus remains a separate Data Track admission/research activity.

## Explicitly out of scope

- Running Snapshot A against the real 12-BoatDesign corpus.
- Canonical admission/research of Rustler 36, Contessa 32, Bavaria Cruiser 34, Sun Odyssey 36i, Albin Vega, Rival 34, Najad 451 CC, Lagoon 42, Oceanis 30.1, AMEL Super Maramu, Hallberg-Rassy 400 or Sirius 35 DS.
- PostgreSQL search read model/index work.
- FastAPI/public HTTP endpoints.
- Astro/React frontend or SEO/OQ-018.
- PREFER ranking.
- Public arbitrary OR/NOT query support.
- Geography/OQ-020.
- Listing dedup/OQ-005 or market adapters.
- Accounts, save/monitor, alerts, pricing or history.
- Any relaxation of `SEARCH_QUERY_SEMANTICS.v0.1.md`.
- A generic vessel completeness/quality/seaworthiness score.

## Deliverables

- versioned mixed numeric/categorical query representation under `src/hullq/search/`;
- categorical qualified-value/evaluator support;
- resolved-configuration projection/result identity types;
- configuration-aware BoatDesign evaluator;
- focused unit/contract/property tests;
- synthetic search/configuration fixtures;
- small local demo exercising the new path;
- any concise engineering note needed to explain query-contract v0.1→v0.2 compatibility.

Avoid persistence migrations. If correctness requires one, stop and report rather than widening the slice.

## Acceptance criteria

- [ ] Categorical MUST exact-equality criteria produce TRUE/FALSE/UNKNOWN under the same fail-closed qualification rules as numeric leaves.
- [ ] Mixed numeric + categorical AND queries evaluate deterministically.
- [ ] Existing serialized query v0.1 remains readable with identical semantics.
- [ ] The new serialized query version round-trips mixed criterion types without semantic drift and rejects unknown keys/types/versions.
- [ ] `CONFIGURATION_AMBIGUOUS` exists and is used when configuration uncertainty can change design-level membership.
- [ ] A design with one confirmed matching configuration is a confirmed match and returns the matching configuration identity.
- [ ] A design with matching and non-matching confirmed configurations remains a confirmed match; no false universal claim is made.
- [ ] A design with no matching resolved configuration but a materially possible UNKNOWN configuration is insufficient, not confirmed non-match.
- [ ] A confirmed non-match requires sufficient knowledge that every materially applicable configuration that could affect membership is non-matching.
- [ ] Standard vs shallow-draft synthetic fixture proves one option may match `Draft <= threshold` while another does not.
- [ ] Option/variant identifiers and requires/excludes/applicability are not silently discarded where they affect resolved-configuration identity or validity.
- [ ] No raw schema-valid BoatDesign or research evidence is automatically upgraded to confirmed search truth.
- [ ] All Q1–Q10 operator/field shapes are executable on synthetic qualified test data.
- [ ] Existing SLICE-0033 numeric truth, reason-code and primary/insufficient separation tests remain green.
- [ ] No real benchmark BoatDesign is promoted or admitted by this slice.
- [ ] No PREFER, public OR/NOT, API, frontend, persistence, geography, listings or monitoring scope is introduced.
- [ ] Ruff format/check, mypy, repository validator, full pytest and coverage >=90% pass.
- [ ] Exact-head CI and Manufacturer artifact reproducibility pass.

## Adversarial review checklist

Before recommending REVIEW, explicitly test or inspect at least:

1. Can a design with one FALSE config and one UNKNOWN config be incorrectly classified `CONFIRMED_NON_MATCH`?
2. Can a design with one TRUE config and one FALSE/UNKNOWN config fail to return `CONFIRMED_MATCH` or lose the exact matching config identity?
3. Can a provisional/conflicting categorical value become TRUE/FALSE through equality comparison?
4. Can `NOT_APPLICABLE` become TRUE through a comparison or negation loophole in the implemented subset?
5. Can an option override be flattened into baseline so every configuration appears to have shallow draft / center cockpit / cutter / etc.?
6. Can an unresolved/invalid option dependency or applicability combination be silently ignored to improve evaluability?
7. Can query v0.2 accept unknown semantic keys or criterion kinds and silently discard them?
8. Can editing a fixture alter the normative set of supported query fields/enums used by the verifier?
9. Did any real benchmark BoatDesign/reference value become canonical merely because it motivated a synthetic fixture?
10. Did existing numeric v0.1 queries change truth or serialization behavior?

Any YES is blocking unless the controlling contract explicitly requires that behavior.

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

Run the new local search/configuration demo and report its query plus design/configuration outcome summary.

## Stop conditions

Stop and report instead of inventing a solution if:

- implementation would need schema-valid raw values to count as confirmed without field qualification;
- a generic configuration expansion rule would require guessing whether options are combinable/applicable;
- a new public query language/OR/NOT/PREFER decision becomes necessary;
- real benchmark data admission becomes necessary to prove the synthetic capability;
- a database migration, public API or frontend becomes necessary;
- accepted OQ-009 semantics would have to be weakened.

## Status handoff rule

The implementation agent may leave `IN_PROGRESS`, `BLOCKED` or `REVIEW`, but MUST NOT mark SLICE-0035 DONE and MUST NOT merge its implementation PR.

## Required completion report

Use `docs/slices/SLICE_TEMPLATE.md` concisely. Additionally report:

- exact query-contract versions supported and compatibility behavior;
- exact categorical criterion/value types and reason mappings;
- exact resolved-configuration identity and design-level aggregation rule;
- exact synthetic configuration cases exercised;
- explicit results for all ten adversarial checklist questions;
- confirmation that no raw/reference value was upgraded to confirmed truth;
- confirmation that no real benchmark BoatDesign was promoted;
- exact final HEAD and exact-head CI/Manufacturer state;
- no next slice started.
