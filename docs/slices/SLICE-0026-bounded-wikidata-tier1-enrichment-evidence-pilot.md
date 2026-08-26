# SLICE-0026 — Bounded Wikidata Tier-1 Enrichment Evidence Pilot

**ID:** SLICE-0026  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0025 owner-accepted / DONE  
**Blocks:** any broader Stage-3.3 Tier-1 enrichment rollout

## Objective

Run the first bounded Stage-3.3 technical-enrichment pilot over **exactly 100 already-canonical BoatModels** that have an accepted historical Wikidata QID mapping, using only the already-cleared Wikidata adapter and already-accepted measurement/provenance/research-persistence semantics.

The pilot must measure and retain canonical-linked evidence coverage for the currently supported Tier-1-compatible fields:

- LOA;
- LWL;
- beam;
- draft;
- displacement.

This slice is an **evidence-path pilot**, not a canonical technical-resolution rollout. It MUST NOT invent BoatDesign generations, mint BoatDesign IDs, create FieldResolution decisions, or claim that the selected models are fully Tier-1 searchable.

## Why this slice exists

SLICE-0025 accepted `BEGIN_BOUNDED_STAGE_3_3_IN_PARALLEL` while Stage 3.2 remains open.

The accepted repository already provides the pieces needed for a small real enrichment-path test:

- 1,770 canonical BoatModels and 1,772 retained historical QID -> HullQ-ID mappings;
- Wikidata CC0 rights-gated acquisition;
- quantity extraction for LOA/LWL/beam/draft/displacement;
- deterministic SI normalization;
- immutable FieldEvidence / unknown/conflict semantics;
- PostgreSQL research-evidence persistence and idempotent replay.

However, the accepted SLICE-0018 replay intentionally contains **zero canonical BoatDesign rows**. Under `IDENTITY_MODEL.v0.1`, a BoatDesign represents an evidence-supported technical generation and MUST NOT be invented merely because a BoatModel exists. Therefore this first Stage-3.3 slice proves the technical-evidence path without silently manufacturing a 1:1 BoatModel -> BoatDesign generation model.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `docs/slices/SLICE-0025-acceptance-closure.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3.3 only;
- `docs/DATABASE_COVERAGE_STRATEGY.md` — Tier 1 and sparse-data rules;
- `specs/IDENTITY_MODEL.v0.1.md` — BoatModel / BoatDesign boundary;
- `specs/PROVENANCE_MODEL.v0.1.md` and accepted provenance schemas only where implementation requires them;
- `src/hullq/sources/wikidata.py`;
- accepted SLICE-0018 crosswalk/manifest artifacts;
- existing research-evidence persistence/import/readback modules used by SLICE-0013/0014.

Do not preload unrelated product, frontend, SEO, marketplace, query-engine or prior-slice history.

## Fixed pilot boundary

### Candidate universe

Use only already-accepted SLICE-0018 canonical identity state.

Select exactly 100 **distinct canonical BoatModel IDs** that have at least one retained accepted QID -> HullQ-ID mapping.

Selection must be deterministic and reproducible offline from accepted retained artifacts. Define one stable ordering in code and retain the resulting selection in the pilot manifest. Multiple historical QIDs mapping to one BoatModel MUST NOT make that BoatModel appear twice.

No discovery query is permitted in this slice.

### Source

Use only:

```text
SRC_WIKIDATA_API_2026
```

Use the existing rights-gated `wbgetentities` acquisition path. The accepted source-use gate must pass before every request. Do not add or reinterpret source rights.

### Allowed field pointers

Only the existing adapter mappings for:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

Do not add year, hull-configuration, material, rig, keel/rudder/skeg, ballast, sail-area, builder/designer or other field semantics in this slice.

## Required behavior

1. Reproduce the accepted 1,770 BoatModel / 1,772 historical-crosswalk boundary before selecting the pilot set. Fail closed on drift.
2. Deterministically select the exact 100 distinct canonical BoatModels and their accepted source QIDs.
3. Fetch only those known QIDs through the existing Wikidata entity API path; perform no SPARQL/discovery expansion.
4. Reuse the existing adapter extraction and measurement normalization for the five allowed fields. Do not create alternate parsers/formulas.
5. Preserve raw source representation, source locator, source QID, normalized candidate and unsupported/missing states.
6. Preserve the distinction between source technical subject (`BoatDesign`-shaped evidence keyed by Wikidata QID) and accepted canonical BoatModel identity. Do not rewrite a source-QID subject into a fabricated canonical BoatDesign ID.
7. Retain an explicit, deterministic link in the pilot artifact between each accepted BoatModel ID and the source QID(s) from which technical evidence was gathered.
8. Persist the resulting research evidence/bundle through the existing PostgreSQL research persistence boundary where schema-compatible. Do not add canonical BoatDesign/FieldResolution rows merely to make persistence convenient.
9. Prove first import, exact re-import/idempotency, offline readback/reproduction, and zero mutation of the accepted canonical identity state.
10. Measure per-field coverage separately for:
   - source statement present;
   - normalized candidate present;
   - unsupported/malformed statement;
   - no usable value.
11. Unknown/missing MUST remain unknown; absence is never converted to a negative or zero value.

If the existing persistence contract cannot retain the evidence truthfully without changing accepted subject semantics, stop `BLOCKED` and report the exact boundary instead of adding a new persistence model inside this slice.

## Deliverables

Retain a compact package under:

```text
research/stage3/sl0026-wikidata-tier1-enrichment/
```

containing at minimum:

- deterministic pilot selection / canonical-QID links;
- normalized evidence/result manifest;
- JSON schema(s) for retained machine-readable artifacts;
- compact `REPORT.md` with field coverage and request counts;
- integrity digests covering every retained package file except the digest document itself.

Add only the smallest runner/helper changes needed to assemble, verify, persist/replay and report the pilot.

## In scope

- deterministic 100-BoatModel selection from accepted identity artifacts;
- existing Wikidata entity acquisition for those known QIDs;
- existing five-field extraction/normalization path;
- retained canonical-QID linkage without identity mutation;
- research evidence persistence/replay where already supported;
- coverage metrics and tamper-resistant retained artifacts;
- focused tests;
- compact `PROJECT_STATE` / slice-index synchronization at handoff.

## Explicitly out of scope

- new identity discovery or canonical BoatModel admission/removal;
- minting or inferring canonical BoatDesign generations;
- FieldResolution/canonical technical-value rollout;
- claiming the pilot models are fully Tier-1 searchable;
- Stage 3.2 completion or G4 pass;
- more than 100 BoatModels;
- new external sources or source-rights decisions;
- manufacturer/Wikipedia research;
- first/last-built extraction;
- hull configuration, material or rig extraction;
- Tier-2 keel/rudder/skeg/variant work;
- derived-metric expansion;
- query engine, API, frontend, SEO runtime, market/listing, account, alert or price-history work;
- creating or starting SLICE-0027.

## Acceptance criteria

- [ ] Accepted identity boundary reproduces exactly at 1,770 BoatModels / 1,772 historical mappings before pilot selection.
- [ ] Exactly 100 distinct accepted canonical BoatModels are selected deterministically and retained with source-QID links.
- [ ] No discovery request is issued; only known accepted QIDs are fetched.
- [ ] Existing source-rights gate is enforced before every network request.
- [ ] Only the five allowed field pointers are admitted to the pilot output.
- [ ] Existing Wikidata extraction and SLICE-0004 normalization are reused rather than reimplemented.
- [ ] Raw representation and provenance remain recoverable for every retained evidence item.
- [ ] Missing/unsupported/conflicting evidence remains explicit and is not guessed.
- [ ] No canonical BoatModel identity/crosswalk row changes and no canonical BoatDesign is invented.
- [ ] Research persistence/replay is idempotent where applicable, or the slice stops BLOCKED on an accepted persistence-boundary conflict.
- [ ] Retained artifacts are schema-valid, integrity-digested and offline-verifiable.
- [ ] Report measures field coverage and request/record counts without converting coverage into a launch-readiness claim.
- [ ] Repository validation, Ruff, mypy and full pytest/coverage gates pass.
- [ ] Required remote CI is observed on the exact final branch HEAD before claiming PASS.
- [ ] No later slice is started automatically.

## Expected touch points

Expected only where needed:

- `src/hullq/bootstrap/` and/or a small Stage-3 enrichment helper;
- `scripts/` runner for the bounded pilot;
- `research/stage3/sl0026-wikidata-tier1-enrichment/`;
- focused unit/integration tests;
- compact operational docs at handoff.

Do not redesign the accepted Wikidata adapter, provenance model, identity model or persistence architecture.

## Validation

At final handoff run the normal repository gates once:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Also run the slice-specific offline verifier and PostgreSQL replay/integration path required by the implementation.

## Stop conditions

Stop `BLOCKED` instead of inventing semantics if:

- the accepted identity/crosswalk boundary does not reproduce;
- source rights do not allow the bounded acquisition;
- a technical statement cannot be mapped by the already-accepted adapter semantics;
- truthful persistence requires inventing a canonical BoatDesign or changing accepted subject semantics;
- implementation requires a new field/source/query/product decision outside this contract.

## Status handoff rule

Claude may move this slice `READY -> IN_PROGRESS -> REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

## Required completion report

Use the concise structure from `docs/slices/SLICE_TEMPLATE.md`. Include the exact final branch HEAD SHA, local validation summary, exact-head remote CI state, retained pilot counts/coverage, unresolved findings and a declaration that no later slice was started.