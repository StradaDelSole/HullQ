# SLICE-0003 — Canonical JSON-Schema Contract Runtime

**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 2.2 — first domain-foundation implementation slice  
**Depends on:** SLICE-0002 accepted / DONE  
**Blocks:** SLICE-0004  

## Objective

Implement the smallest reusable Python runtime for loading and validating HullQ's repository-local JSON Schema contracts.

This slice creates infrastructure for enforcing contracts already accepted in `specs/`. It MUST NOT introduce new boat semantics, normalization rules, source acquisition, persistence, or domain-model classes.

The runtime exists so later slices do not duplicate ad-hoc schema loading/registry code in tests, scripts or pipeline modules.

## Why this slice exists

SLICE-0002 established that later HullQ work will process heterogeneous real-source observations, options, conflicts and provenance. Before implementing those behaviors, the codebase needs one deterministic contract boundary that can validate repository objects against the versioned JSON Schemas that already define them.

Current repository validation and contract tests already contain similar local schema-loading logic. This slice promotes that pattern into reusable package code without changing schema meaning.

## Controlling artifacts

### Requirements supported

This slice provides validation infrastructure used to enforce, but does not itself redefine, accepted requirements including:

- `REQ-DATA-001` — explicit unknown;
- `REQ-DATA-008` — progressive depth / sparse valid records;
- `REQ-ID-003` — accepted BoatModel / BoatDesign / variant / option hierarchy;
- `REQ-ID-006` — orthogonal factory options;
- `REQ-PROV-001` — separate provenance ledger;
- `REQ-PROV-002` — standard field addressing;
- `REQ-PROV-006` — derived lineage;
- `REQ-RATIO-003` — explicit calculation basis;
- repository governance/quality requirements under the accepted OQ-010 toolchain.

### Specifications / registers

- `specs/SCHEMA_STATUS.md`
- `specs/BOAT_MODEL_SCHEMA.v0.1.json`
- `specs/BOAT_DESIGN_SCHEMA.v0.4.json`
- `specs/RESOLVED_CONFIGURATION_SCHEMA.v0.2.json`
- `specs/SOURCE_SCHEMA.v0.2.json`
- `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json`
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json`
- `specs/RATIO_INPUT_BASIS_SCHEMA.v0.1.json`
- `specs/DERIVED_METRICS_SCHEMA.v1.0.json`
- `specs/REQUIREMENTS.md`
- `specs/TEST_STRATEGY.md`

### Accepted decisions / engineering baseline

- ADR-0002 — docs-to-code;
- ADR-0004 — identity model;
- ADR-0006 — provenance ledger;
- ADR-0008 — derived-metric methodology;
- ADR-0009 — Python research toolchain;
- `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md`.

## In scope

Implement a small package boundary under `src/hullq/` for repository-local contract validation.

The implementation MUST support:

1. loading JSON Schema documents from an explicitly supplied schema directory;
2. deterministic discovery of `*_SCHEMA*.json` files in that directory only;
3. JSON object/type validation for loaded schema documents;
4. Draft 2020-12 meta-schema validation via `Draft202012Validator.check_schema`;
5. unique schema lookup by repository filename;
6. unique local resource registration by schema `$id` where present;
7. local `$id` / `$ref` resolution through an in-memory `referencing.Registry` or the supported equivalent in the accepted `jsonschema` stack;
8. validation of an arbitrary Python/JSON-compatible instance against an explicitly selected schema;
9. preservation of normal `jsonschema.ValidationError` detail for invalid instances;
10. deterministic, explicit failure for malformed schema JSON, duplicate filenames/IDs, unknown schema lookup, or unavailable local reference resources;
11. no network retrieval during contract loading or validation.

The caller MUST explicitly select the schema to validate against. This slice MUST NOT invent a second machine-readable definition of which schema versions are `ACCEPTED`; status authority remains `specs/SCHEMA_STATUS.md` and the controlling slice/spec. Draft schemas may exist in the local directory but MUST NOT silently become production contracts merely because they can be syntactically loaded.

## Minimal API expectation

Keep the public API small. A single registry/loader abstraction is preferred over many helper layers.

A reasonable shape is conceptually:

```python
registry = ContractRegistry.from_directory(schema_dir)
validator = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json")
validator.validate(instance)
```

Equivalent naming is acceptable if it remains simple, typed, deterministic and well tested.

The abstraction SHOULD expose lookup by schema filename. Lookup by `$id` MAY also be exposed if it does not complicate the API.

Do not create Pydantic/domain models or code generation from JSON Schema.

## Dependency rule

No new runtime dependency is expected beyond the accepted `jsonschema` ecosystem.

If implementation imports the `referencing` package directly, promote `referencing` to an explicit project dependency and regenerate `uv.lock`; do not rely on an undeclared transitive import. Do not add any other dependency without stopping and reporting why it is required.

## Required refactor

Where practical within this slice, remove duplicate local registry-building logic from:

- `scripts/validate_repository.py`;
- `tests/contract/test_contract_fixtures.py`.

Both SHOULD consume the new package runtime rather than maintain separate schema-loading implementations.

Do not weaken any existing repository validation while refactoring.

## Explicitly out of scope

Do **not** implement:

- measurement/unit normalization;
- displacement/sail-area basis interpretation;
- manufacturer/model/generation normalization;
- keel/rudder/skeg/rig classification;
- provenance conflict-resolution behavior;
- derived-metric formulas;
- ResearchJob state machine;
- HTTP/network access;
- Wikidata or any other source adapter;
- source-rights decision logic;
- persistence / SQLite tables / ORM;
- production database/search technology;
- API/frontend behavior;
- schema redesign unless an actual contradiction prevents implementation.

Do not package/copy `specs/` into the Python wheel in this slice. The schema directory is supplied explicitly by the repository/application caller.

## Required tests

Add focused tests covering at least:

1. repository schemas load deterministically from `specs/`;
2. every discovered schema is a JSON object and passes Draft 2020-12 schema validation;
3. current accepted identity, ratio, source-rights and provenance fixtures still validate through the new runtime;
4. existing negative provenance fixtures are still rejected;
5. unknown schema-name lookup fails explicitly;
6. duplicate `$id` registration fails explicitly using temporary synthetic schemas;
7. malformed JSON / non-object schema input fails explicitly using temporary synthetic schemas;
8. a synthetic local cross-schema `$ref` resolves from the in-memory local registry without network access;
9. a missing referenced local resource fails rather than attempting an HTTP fetch.

Tests MUST NOT depend on internet access.

## Expected touch points

Expected files/modules include only what is necessary, likely:

- `src/hullq/contracts/__init__.py`;
- `src/hullq/contracts/registry.py` (or one equivalently small module);
- `tests/unit/test_contract_registry.py`;
- `tests/contract/test_contract_fixtures.py`;
- `scripts/validate_repository.py`;
- `pyproject.toml` and `uv.lock` only if `referencing` becomes an explicit direct dependency;
- this slice / `docs/slices/INDEX.md` / `docs/PROJECT_STATE.md` for handoff status only.

Do not touch unrelated domain or research files merely for cleanup.

## Acceptance criteria

- [x] one reusable typed contract runtime exists under `src/hullq/` (`src/hullq/contracts/registry.py`, `ContractRegistry`);
- [x] schema loading uses only an explicitly supplied local directory (`from_directory(schema_dir)` parameter);
- [x] no contract-validation path performs network access (local `referencing.Registry` only; test 9 verifies missing ref raises `Unresolvable` not HTTP);
- [x] repository schema documents are meta-schema validated as Draft 2020-12 (`Draft202012Validator.check_schema` in `from_directory`);
- [x] duplicate schema `$id` values fail explicitly (`ValueError` — test 6 verifies);
- [x] unknown schema lookup fails explicitly (`KeyError` — test 5 verifies);
- [x] local `$ref` resolution works from the in-memory registry (test 8 verifies with synthetic cross-schema `$ref`);
- [x] missing local `$ref` resources fail without HTTP retrieval (`Unresolvable` — test 9 verifies);
- [x] existing valid contract fixtures validate through the runtime (all contract tests pass — 12/12 parametrized cases);
- [x] existing invalid provenance fixtures remain rejected (6/6 negative cases still raise `ValidationError`);
- [x] duplicate ad-hoc registry construction in repository script/tests is removed or materially reduced without weakening checks (`validate_repository.py` and `test_contract_fixtures.py` refactored to use `ContractRegistry`; `test_repository_governance.py` updated; no check weakened);
- [x] no new HullQ boat/source/normalization semantics were introduced;
- [x] no acquisition, persistence, query, market, frontend or source-adapter code was introduced;
- [x] repository validator, Ruff, mypy, pytest/coverage and dependency audit pass locally (see completion report);
- [ ] required remote CI is reported truthfully as `PASS`, `FAIL`, or `NOT VERIFIED` and is not guessed. → **NOT VERIFIED** (branch pushed; see completion report)

## Validation

Run at minimum:

```bash
uv lock --check
uv sync --locked --all-groups
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
uv run pip-audit
```

If formatting is the only failing gate, apply the repository formatter and rerun the full relevant gate set.

## Stop conditions

Stop and report instead of inventing a solution if:

- an accepted schema is internally invalid or cannot be loaded under Draft 2020-12;
- accepted schemas require contradictory local resource identities;
- implementing the runtime requires changing BoatDesign/identity/provenance/ratio semantics;
- a second schema-status authority appears necessary;
- implementation appears to require network schema retrieval;
- a new dependency beyond `jsonschema` / direct `referencing` declaration appears necessary;
- scope would expand into normalization, acquisition, persistence or other later slices.

A schema defect discovered here is a specification finding, not permission to silently patch the schema around the code.

## Status handoff rule

Claude Code / the implementation agent may move this slice to `IN_PROGRESS`, `BLOCKED`, or `REVIEW`, but MUST NOT mark it `DONE`.

Successful implementation normally hands the slice off in `REVIEW`. Final `DONE` requires independent review and explicit project-owner acceptance under `CLAUDE.md`.

## Required completion report

Use the exact completion-report structure required by `docs/slices/SLICE_TEMPLATE.md`.

In addition, explicitly report:

- the final public contract-runtime API;
- whether `referencing` was promoted to a direct dependency;
- which duplicated schema-loading code was removed/refactored;
- evidence that validation performs no network retrieval;
- any schema/spec defect encountered.

Do not begin SLICE-0004.
