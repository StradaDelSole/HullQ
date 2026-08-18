# SLICE-0003 — Canonical JSON-Schema Contract Runtime

**Type:** IMPLEMENTATION  
**Status:** DONE  
**Stage:** 2.2 — first domain-foundation implementation slice  
**Depends on:** SLICE-0002 accepted / DONE  
**Blocks:** SLICE-0004  
**Accepted:** 2026-08-18  
**Merged PR:** #3  
**Merge commit:** `b927a6b17e204de43773c8682e36a29db037ab8a`

## Objective

Implement the smallest reusable Python runtime for loading and validating HullQ's repository-local JSON Schema contracts without introducing boat semantics, normalization, acquisition, persistence or application behavior.

## Controlling artifacts

- `specs/SCHEMA_STATUS.md`;
- accepted BoatModel / BoatDesign / ResolvedConfiguration / Source / provenance / ratio schemas;
- `specs/REQUIREMENTS.md`;
- `specs/TEST_STRATEGY.md`;
- ADR-0002, ADR-0004, ADR-0006, ADR-0008, ADR-0009;
- `docs/engineering/PYTHON_TOOLCHAIN_BASELINE.v0.1.md`.

## Implemented scope

The accepted implementation provides `ContractRegistry` under `src/hullq/contracts/` with:

1. loading JSON Schema documents from an explicitly supplied local schema directory;
2. deterministic discovery of `*_SCHEMA*.json` files;
3. Draft 2020-12 meta-schema validation;
4. lookup by repository filename;
5. unique local `$id` registration;
6. local `$id` / `$ref` resolution through an in-memory `referencing.Registry`;
7. validation through ordinary `jsonschema` validators/errors;
8. explicit failure for malformed JSON, duplicate IDs, unknown lookup and unresolved local resources;
9. no HTTP/network retrieval;
10. reuse by repository validation and contract tests instead of duplicated ad-hoc registry construction.

`referencing>=0.37,<1` was promoted to an explicit project dependency because first-party runtime code imports it directly.

## Public runtime shape

```python
from hullq.contracts import ContractRegistry

registry = ContractRegistry.from_directory(schema_dir)
validator = registry.validator_by_name("BOAT_DESIGN_SCHEMA.v0.4.json")
validator.validate(instance)
```

`schema_names` exposes the loaded schema filenames.

## Explicitly not introduced

This slice introduced no:

- measurement/unit normalization;
- displacement/sail-area interpretation;
- identity/generation normalization;
- keel/rudder/skeg/rig classification;
- provenance conflict-resolution runtime;
- derived-metric formulas;
- ResearchJob workflow;
- HTTP/source acquisition;
- persistence/ORM/database behavior;
- public API/frontend/deployment behavior;
- schema redesign/domain semantics.

DRAFT schemas may be syntactically loaded for local reference completeness, but schema status remains governed by `specs/SCHEMA_STATUS.md`; the runtime does not create a second status authority.

## Acceptance criteria

- [x] one reusable typed contract runtime exists under `src/hullq/`;
- [x] schema loading uses only an explicitly supplied local directory;
- [x] no contract-validation path performs network access;
- [x] repository schemas are meta-schema validated as Draft 2020-12;
- [x] duplicate `$id` values fail explicitly;
- [x] unknown schema lookup fails explicitly;
- [x] local `$ref` resolution works from the in-memory registry;
- [x] missing local `$ref` resources fail without HTTP retrieval;
- [x] existing valid fixtures validate through the runtime;
- [x] existing invalid provenance fixtures remain rejected;
- [x] duplicated ad-hoc registry construction was materially reduced without weakening checks;
- [x] no new HullQ boat/source/normalization semantics were introduced;
- [x] no acquisition, persistence, query, market, frontend or source-adapter code was introduced;
- [x] local repository validator, Ruff, mypy, pytest/coverage and dependency audit passed;
- [x] required remote CI was independently observed and passed.

## Validation evidence

Implementation-agent local report:

- `uv lock --check` — PASS;
- `uv sync --locked --all-groups` — PASS;
- `uv run python scripts/validate_repository.py` — PASS;
- Ruff format/check — PASS;
- mypy strict — PASS;
- pytest — 39/39 PASS;
- coverage — 98.18% branch coverage;
- pip-audit — PASS / no known vulnerabilities.

Remote PR-head CI run #45 on commit `cee3648bfab714f3e2be9c81711d654da3a06aca` was independently observed:

- quality (`ubuntu-latest`) — PASS;
- quality (`windows-latest`) — PASS;
- dependency audit — PASS.

## Independent review

Independent code/spec review completed on 2026-08-18.

**Result:** ACCEPT — no blocking findings.

The implementation matches the bounded slice: local Draft-2020-12 schemas remain authoritative, local reference resolution does not retrieve from the network, invalid fixtures remain rejected, duplicate loading logic is reduced, and no later-slice semantics were introduced.

## Project-owner acceptance

Explicit project-owner acceptance received on **2026-08-18** after remote CI and independent review.

PR #3 was then merged to `main` as squash merge commit:

```text
b927a6b17e204de43773c8682e36a29db037ab8a
```

## Final completion report

### Slice

- Slice ID: `SLICE-0003`
- Final slice state: `DONE`
- Scope completed: `YES`

### Changes

- reusable `ContractRegistry` added;
- contract tests/repository validation refactored to use the shared runtime;
- focused unit tests added;
- `referencing` promoted to direct dependency;
- no domain/application expansion.

### Validation

- Local validation: `PASS`
- Remote CI: `PASS`
- Independent review: `PASS`
- Project-owner acceptance: `ACCEPTED`

### Findings

- `jsonschema` typing remains imperfect, so the implementation uses a focused mypy override; no runtime semantic impact was found;
- no blocking schema/ADR contradiction was found;
- no scope deviation was found.

### Follow-up

SLICE-0004 may be detailed/made `READY`. No later slice is automatically authorized.
