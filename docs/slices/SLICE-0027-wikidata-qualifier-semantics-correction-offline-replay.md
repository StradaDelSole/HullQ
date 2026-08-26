# SLICE-0027 — Wikidata Qualifier-Semantics Correction + Offline Replay

**ID:** SLICE-0027  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0026 owner-accepted / DONE  
**Blocks:** any broader Wikidata Tier-1 enrichment rollout that depends on qualifier-disambiguated measurements

## Objective

Correct the bounded Wikidata adapter qualifier-property semantics exposed by the accepted SLICE-0026 retained 100-BoatModel pilot, using **only the already-retained SLICE-0026 raw entity claims** as evidence, then replay the exact same 100-BoatModel sample offline to measure the coverage delta and prove persistence/readback again.

SLICE-0026 established a concrete adapter mismatch rather than a lack-of-data conclusion:

- beam, which does not require concept-qualifier disambiguation in the current adapter path, produced 41 normalized candidates;
- LOA/LWL/draft/displacement produced zero normalized candidates despite many retained source statements classified as unsupported;
- retained raw claims show the already-known concept QIDs under qualifier properties other than the adapter's current `P642`-only path, including `P518` for LOA/LWL/draft-shaped statements and `P3831` for displacement-shaped statements.

This slice must correct only that evidenced qualifier-property compatibility boundary. It is **not** a broad enrichment run, a new semantic-source decision, or a canonical technical-resolution rollout.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `docs/slices/SLICE-0026-acceptance-closure.md`;
- `docs/slices/SLICE-0026-bounded-wikidata-tier1-enrichment-evidence-pilot.md`;
- `research/stage3/sl0026-wikidata-tier1-enrichment/` retained package;
- `src/hullq/sources/wikidata.py`;
- accepted measurement/provenance/persistence contracts only where implementation requires them.

Do not preload unrelated product, frontend, SEO, marketplace, account, alert, pricing or later-stage documents.

## Fixed evidence boundary

### Input sample

Use exactly the accepted SLICE-0026 retained sample:

```text
100 distinct canonical BoatModels
100 retained known Wikidata QIDs
accepted identity boundary: 1,770 BoatModels / 1,772 historical QID mappings
```

The input source of truth for this slice is the already-retained SLICE-0026 raw-entity claim payload. **No live Wikidata acquisition is required or permitted for the primary correction/replay proof.**

Before deriving or replaying anything, verify the accepted SLICE-0026 retained package offline and fail closed on digest/schema/self-consistency drift.

### Allowed technical fields

Only the same five SLICE-0026 field pointers are in scope:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

Do not add ballast, year, material, rig, keel/rudder/skeg, builder/designer or any other field to the retained SLICE-0027 result merely because the adapter can extract it elsewhere.

## Required qualifier-semantics behavior

The implementation must derive the accepted correction from the retained raw claims, not from guesswork or label matching.

At minimum, independently characterize the retained claim shapes for the shared/qualified Wikidata measurement properties used by the five allowed fields and record the observed qualifier-property + qualifier-value combinations relevant to those fields.

The accepted existing concept-QID distinctions remain authoritative. This slice may add a qualifier **property** as an alternative carrier of an already-accepted concept QID only where the retained SLICE-0026 evidence demonstrates that exact shape.

Expected evidenced compatibility to test, not blindly assume:

- length concepts such as accepted LOA `Q2358152` / LWL `Q1817392` may be carried under retained `P518` claims;
- draft concept `Q244777` may be carried under retained `P518` claims;
- displacement concept `Q5636358` may be carried under retained `P3831` claims.

The existing accepted `P642` path must remain valid unless a controlling accepted contract explicitly requires its removal. Backward-compatible recognition is preferred over replacing one exact carrier with another.

### Fail-closed rules

- Do not infer field meaning from the quantity property alone when the accepted adapter requires qualifier disambiguation.
- Do not map an unfamiliar qualifier value because its English label appears plausible.
- Do not map arbitrary `P518`, `P3831` or other qualifier values to HullQ fields.
- Do not treat missing/unknown qualifiers as a field match.
- Do not broaden the accepted concept-QID vocabulary in this slice.
- If truthful correction requires a new technical concept decision rather than qualifier-property compatibility, stop `BLOCKED` and report the exact boundary.

## Required behavior

1. Offline-verify the accepted SLICE-0026 retained package before using it.
2. Reproduce the exact 100-BoatModel / 100-QID input boundary from retained artifacts.
3. Deterministically inspect only retained raw claims relevant to the five allowed measurement fields.
4. Retain a compact qualifier-shape analysis that counts the relevant qualifier-property/value combinations and distinguishes recognized vs unsupported shapes.
5. Amend the existing Wikidata extraction path by the smallest coherent change necessary to support only evidence-backed alternative qualifier-property carriers for already-accepted concept QIDs.
6. Preserve existing accepted `P642` behavior and existing unqualified beam behavior.
7. Replay the exact retained 100 entities through the amended adapter **offline**; perform no live discovery/acquisition.
8. Produce deterministic before/after per-field coverage using the same four mutually-exclusive SLICE-0026 coverage states:
   - normalized candidate present;
   - source statement present;
   - unsupported/malformed;
   - no usable value.
9. Prove that newly recognized statements still use the existing SLICE-0004 normalization path; do not implement alternate conversion formulas.
10. Preserve raw representation, source locator/QID, normalized candidate and unknown/unsupported states.
11. Persist/replay the amended exact-100 result through the existing PostgreSQL research-evidence boundary and prove first import, readback fidelity, idempotent reimport and zero canonical BoatModel/BoatDesign mutation.
12. Retain tamper-resistant artifacts and an offline verifier for the SLICE-0027 package.

## Required regressions

Tests must cover at least:

- existing accepted `P642` + LOA/LWL concept-QID extraction remains valid;
- retained-evidence-compatible `P518` + LOA concept QID extracts LOA;
- retained-evidence-compatible `P518` + LWL concept QID extracts LWL;
- retained-evidence-compatible `P518` + draft concept QID extracts draft;
- retained-evidence-compatible `P3831` + displacement concept QID extracts displacement;
- wrong/unrecognized qualifier property-value combinations remain unsupported;
- a recognized qualifier property with an unrecognized concept QID remains unsupported;
- an accepted concept QID under an unevidenced/unaccepted qualifier property is not silently accepted;
- existing unqualified beam extraction remains unchanged;
- supported units continue to normalize through the existing measurement normalizer;
- unsupported units/raw-only behavior remains explicit rather than guessed;
- exact retained 100-entity offline replay is deterministic;
- PostgreSQL replay retains exact normalized types/values and remains idempotent;
- no canonical BoatModel/BoatDesign row is created.

## Deliverables

Retain a compact package under:

```text
research/stage3/sl0027-wikidata-qualifier-semantics/
```

containing at minimum:

- deterministic qualifier-shape analysis over the accepted SLICE-0026 raw claims;
- before/after coverage result for the exact same 100-entity sample;
- compact `REPORT.md` explaining which qualifier-property carriers were evidenced and accepted;
- machine-readable schema(s) for retained JSON artifacts;
- PostgreSQL replay result/report where applicable;
- integrity digests covering every retained package file except the digest document itself.

Do **not** mutate or regenerate the accepted SLICE-0026 retained package.

## In scope

- bounded evidence-derived qualifier-property compatibility correction in the existing Wikidata adapter;
- exact retained 100-entity offline replay;
- before/after coverage measurement;
- focused unit/integration tests;
- existing research persistence/readback/idempotency proof;
- retained artifacts and offline verification;
- compact operational handoff docs.

## Explicitly out of scope

- any new live Wikidata acquisition or SPARQL discovery;
- expanding beyond the accepted 100 retained QIDs for the primary proof;
- new canonical BoatModel admission/removal;
- minting/inferencing BoatDesign generations;
- FieldResolution or canonical technical-value writes;
- broad 1,770-model enrichment rollout;
- new field/concept-QID semantics;
- ballast or other non-five-field output expansion;
- material, rig, appendage, variant/generation or derived-metric expansion;
- new external sources or source-rights decisions;
- Stage 3.2 completion / G4 passage;
- query engine, API, frontend, SEO runtime, market/listing, accounts, alerts, pricing or monetization implementation;
- creating or starting SLICE-0028.

## Acceptance criteria

- [ ] Accepted SLICE-0026 retained package verifies offline before SLICE-0027 derivation/replay.
- [ ] Exact 100-BoatModel / 100-QID retained input boundary reproduces without drift.
- [ ] Qualifier-property/value analysis is deterministic and retained.
- [ ] Every newly accepted qualifier-property carrier is evidenced by retained SLICE-0026 raw claims and maps only an already-accepted concept QID.
- [ ] Existing accepted `P642` behavior remains covered by regression tests.
- [ ] No label/fuzzy/property-only semantic inference is introduced.
- [ ] Exact retained 100 entities replay offline through the amended adapter with no network access.
- [ ] Before/after coverage is retained for exactly the five allowed fields and does not overstate unsupported/missing data.
- [ ] Existing measurement normalization is reused; no alternate conversion logic is added.
- [ ] Research persistence/readback is idempotent and exact, with zero canonical BoatModel/BoatDesign mutation.
- [ ] SLICE-0026 retained artifacts are untouched.
- [ ] SLICE-0027 retained artifacts are schema-valid, integrity-digested and offline-verifiable.
- [ ] Repository validation, Ruff, mypy and full pytest/coverage gates pass.
- [ ] Required remote CI is observed on the exact final branch HEAD before claiming PASS.
- [ ] No later slice is started automatically.

## Expected touch points

Expected only where needed:

- `src/hullq/sources/wikidata.py`;
- a small Stage-3 replay/analysis helper under `src/hullq/bootstrap/` and/or `scripts/bootstrap/`;
- `research/stage3/sl0027-wikidata-qualifier-semantics/`;
- focused unit/persistence integration tests;
- `.github/workflows/ci.yml` only if needed to make the retained SLICE-0027 offline/PostgreSQL proof externally verifiable;
- compact `PROJECT_STATE` / slice-index synchronization at handoff.

Do not redesign the Wikidata adapter, identity/provenance model or persistence architecture.

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

Also run the SLICE-0027 offline verifier and PostgreSQL replay/integration path required by the implementation.

## Stop conditions

Stop `BLOCKED` instead of inventing semantics if:

- accepted SLICE-0026 retained artifacts do not verify;
- exact retained input boundary does not reproduce;
- a proposed new qualifier-property carrier is not directly evidenced in retained raw claims;
- the retained claims require a new qualifier-value/concept decision rather than merely an alternative carrier for an already-accepted concept QID;
- truthful extraction would require property-only or label/fuzzy inference;
- implementation requires a new field/source/product decision outside this contract.

## Status handoff rule

Claude may move this slice `READY -> IN_PROGRESS -> REVIEW` or `BLOCKED`, but MUST NOT mark it `DONE`.

## Required completion report

Use the concise structure from `docs/slices/SLICE_TEMPLATE.md`. Include:

- exact final branch HEAD SHA;
- qualifier-property/value combinations evidenced and accepted;
- exact before/after coverage counts for all five fields over the retained 100 entities;
- PostgreSQL persistence/readback/idempotency result;
- local validation summary;
- exact-head remote CI state;
- unresolved findings;
- declaration that no later slice was started.
