# SLICE-0039 — Seed Corpus Wave 1 Real Multi-Design Search

**ID:** SLICE-0039  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** Phase B — bounded Seed Corpus for Gate 1  
**Depends on:** SLICE-0038 owner-accepted / DONE; `docs/PRODUCT_EXECUTION_PLAN.md` controlling; accepted `specs/SEARCH_BENCHMARK.v0.1.md`  
**Blocks:** first inspectable multi-design real Seed-Corpus Search cohort and the next Gate-1 corpus/Concierge decision

## Objective

Deliver exactly one user-visible capability:

> Run the existing strict configuration-aware HullQ Search across the accepted Wave-1 real BoatDesign cohort — Bavaria Cruiser 34, Contessa 32, BENETEAU Oceanis 30.1 and Lagoon 42 — for the unchanged locked Q1, Q2 and Q10 hard-constraint queries, with real provenance-backed facts, explicit configurations where supported, and visible `CONFIRMED_MATCH` / `CONFIRMED_NON_MATCH` / `INSUFFICIENT_DATA` results.

This slice converts the first accepted benchmark wave from research evidence into an actual multi-design, non-fixture Search surface. It does not attempt to complete the entire 20–30-design Seed Corpus.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: real multi-design hard-constraint Search over the first bounded Seed-Corpus wave.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can run one local command and inspect Q1/Q2/Q10 results, exact matching configuration IDs, per-design truth class and blocking reason where insufficient.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
This is Phase B Seed Corpus work. It directly advances four of the bounded approximately 20–30 Seed-Corpus BoatDesigns and deliberately avoids broader corpus, market, UI, SEO or moat-building work before Gate 1.

## Why this slice exists

SLICE-0037 proved one real BoatDesign/configuration through Search. SLICE-0038 proved that one design result can continue to real market offers without promoting design truth into physical-listing truth.

Gate 1 now needs more than one searchable real design, but the Product Execution Plan explicitly forbids building a large corpus before testing. The accepted benchmark already fixes Wave 1 before outcomes are known:

1. Bavaria Cruiser 34;
2. Contessa 32;
3. BENETEAU Oceanis 30.1;
4. Lagoon 42.

Reusing that wave avoids a new model-selection campaign and avoids cherry-picking for favorable Search outcomes. It also gives useful structural diversity: modern production monohull, classic monohull, known configuration-sensitive production monohull, and multihull.

Only Q1, Q2 and Q10 are in scope because they use broadly useful buyer dimensions (`LOA`, `beam`, `draft`) and are sufficient to prove the first multi-design product behavior without researching every P0/P1 field before real-user demand exists.

## Controlling artifacts

- Product execution plan: `docs/PRODUCT_EXECUTION_PLAN.md`
- Search benchmark: `specs/SEARCH_BENCHMARK.v0.1.md`
- Search semantics: `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`
- Technical profile/admission rules: `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`
- Source-rights policy: `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- Source schema: `specs/SOURCE_SCHEMA.v0.2.json`
- Marine technical entailment: `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md` and accepted rule registry
- Accepted Oceanis 30.1 proof: `research/benchmark/waves/sl0037-oceanis-30-1/` and `scripts/search_oceanis_30_1.py`
- Existing research leads: `research/benchmark/SEED_RESEARCH_NOTES.md` and retained benchmark-wave evidence from prior slices

Existing research notes are leads/evidence context, not self-authorizing canonical Search truth. The historical SailboatData scrape remains reference/prototype-only.

## Locked cohort and queries

### Cohort

Exactly these four BoatDesigns:

- Bavaria Cruiser 34
- Contessa 32
- BENETEAU Oceanis 30.1
- Lagoon 42

Do not substitute another design because evidence is inconvenient. If a design has a genuine hard exclusion under the accepted benchmark replacement rule, stop and report the exact condition before changing the cohort.

### Queries

Invoke the unchanged accepted query definitions for exactly:

- **Q1:** `LOA 8–11 m AND Draft <= 1.80 m`
- **Q2:** `LOA 9–12 m AND Beam <= 3.60 m AND Draft <= 2.00 m`
- **Q10:** `Draft <= 1.60 m`

Do not retype or locally redefine thresholds if the accepted benchmark/query fixture already provides them. No new SECONDARY query is authorized in this slice.

## In scope

- reuse the accepted SLICE-0037 Oceanis 30.1 real projection unchanged;
- create the smallest real, provenance-backed configuration projections needed for Bavaria Cruiser 34, Contessa 32 and Lagoon 42;
- resolve only the facts needed by Q1/Q2/Q10: relevant identity/configuration scope, LOA, beam and draft;
- retain explicit `UNKNOWN` / conflict/applicability states when evidence is insufficient;
- represent factory-supported draft/configuration alternatives explicitly when admissible evidence proves them;
- use the existing configuration-aware Search kernel unchanged;
- add a deterministic owner-test script for the four-design cohort;
- add focused offline tests and retained compact evidence sufficient to reproduce the admitted projections.

## Explicitly out of scope

- Seed Corpus designs outside the locked four-design Wave 1;
- researching cockpit, rig, rudder, keel taxonomy, displacement, sail area or other fields merely for completeness when Q1/Q2/Q10 do not need them;
- Q3–Q9;
- adding new Search operators or changing Search semantics;
- generic corpus/admission frameworks without a current Wave-1 consumer;
- PostgreSQL persistence for these projections;
- market listings / additional Owning queries / new marketplace adapters;
- deduplication, monitoring, alerts or price history;
- frontend, public API, auth, SEO or product pages;
- AI recommendation/scoring;
- expanding the corpus because a future data moat may be valuable.

## Source and research discipline

For the three new BoatDesign projections:

1. Prefer current/archival manufacturer, designer or clearly authoritative primary technical material.
2. Reuse already retained evidence only when its applicability, provenance and rights state still satisfy current accepted policy.
3. Marketplaces and competitor/reference databases may identify a research lead but may not self-authorize technical Search facts.
4. The historical SailboatData scrape must not provide canonical values or identity acceptance.
5. No fact is admitted merely because it improves Q1/Q2/Q10 evaluability.
6. Different generation/configuration scopes must remain separate rather than averaged or collapsed.

### Hard research cap

The implementation agent may inspect at most **12 distinct external technical-evidence surfaces total** for the three new designs, with at most **5 for any one design**, excluding source-rights/legal-policy pages needed solely to assess access/reuse.

If that cap cannot establish a useful Wave-1 projection, stop with the exact unresolved evidence gap rather than opening a broad research campaign.

## Required behavior A — preserve the accepted Oceanis proof

The SLICE-0037 Oceanis 30.1 projection is consumed, not rewritten.

For Q10 it must still produce:

- design result `CONFIRMED_MATCH`;
- exact matching configuration `oceanis-30-1-shallow-keel`;
- existing deep-keel configuration FALSE;
- existing retractable/hydraulic-swing configuration UNKNOWN.

Any regression is a blocker; do not work around it in the new cohort code/data.

## Required behavior B — fail-closed real projections for three new designs

Each new BoatDesign must be `is_fixture=False` and independently admitted from retained evidence rather than self-authorized by the projection file.

At minimum, admission must bind:

- exact BoatDesign identity;
- exact configuration IDs represented by this slice;
- fact field/value/qualification;
- configuration/design scope;
- evidence reference(s);
- direct/derived classification where applicable.

A projection must not be able to change one of those values in its own JSON and thereby authorize a different confirmed Search result without a test/admission failure.

Use the smallest slice-local mechanism that satisfies this requirement. Do not generalize the SLICE-0037 pilot validator into a large framework unless an independently demonstrated blocker requires it.

## Required behavior C — configuration scope

Where an authoritative source establishes multiple factory configurations that materially alter draft or another Q1/Q2/Q10 field, represent those resolved configurations explicitly.

Do not:

- average draft values;
- select whichever factory option makes the query match;
- treat a named option as present on every boat;
- generate unsupported Cartesian combinations;
- infer configuration from marketing terminology alone.

If the configuration space cannot be shown complete, retain `configuration_space_complete=False` or the accepted equivalent and keep unresolved cases UNKNOWN.

## Required behavior D — actual multi-design Search

The owner-test must build the four-design `DesignConfigurationSet` cohort and pass it to the unchanged Search kernel for Q1, Q2 and Q10.

It must not hardcode expected result classes instead of executing Search.

For each query, visibly report:

- query ID and human-readable criteria;
- corpus size = 4;
- confirmed matches;
- confirmed non-matches;
- insufficient-data designs;
- matching configuration IDs for confirmed matches;
- concise insufficient reason/blocking field where available.

The output must make clear that a design-level confirmed match means at least one resolved configuration satisfies the query, not that every factory configuration does.

## Required behavior E — utility without truth relaxation

This wave must be useful enough to inspect, but result distribution is not a target to optimize.

Minimum utility gate:

- Q1, Q2 and Q10 must each be evaluable (`CONFIRMED_MATCH` or `CONFIRMED_NON_MATCH`) for at least **3 of the 4** designs;
- `FALSE_CONFIRMED_RESULT = 0` remains mandatory.

If a query is evaluable for fewer than three designs under the bounded evidence cap, report `BLOCKED` / exact evidence gap rather than guessing values, replacing the design, widening fields, or relaxing Search semantics.

Zero matches is allowed if the designs are correctly confirmed non-matches.

## Minimal owner-test surface

Provide one deterministic local command, normally:

```text
uv run python scripts/search_seed_corpus_wave1.py
```

It must run entirely offline after retained evidence is committed. Network access is not required for ordinary replay/CI.

Expected visible shape:

```text
SEED CORPUS WAVE 1 — 4 real BoatDesigns

Q1  LOA 8–11 m AND Draft <= 1.80 m
CONFIRMED_MATCH: ...
CONFIRMED_NON_MATCH: ...
INSUFFICIENT_DATA: ...

Q2  ...
...

Q10 Draft <= 1.60 m
...
```

Exact outcomes are evidence-driven and must not be prescribed by this readiness contract.

## Required tests

Focused tests must cover at least:

- exact cohort contains only the four locked Wave-1 BoatDesigns;
- all four Search projections are real/non-fixture;
- accepted Oceanis 30.1 projection is reused unchanged and Q10 regression-checked;
- each new projection fails admission if design identity is tampered;
- each new projection fails admission if a confirmed LOA/beam/draft value is tampered;
- configuration ID/scope tampering fails admission;
- evidence-reference tampering fails admission;
- missing/unresolved source evidence remains UNKNOWN rather than a guessed numeric value;
- factory configuration alternatives do not collapse into one arbitrary design-wide draft;
- Q1/Q2/Q10 are loaded from the accepted locked query source and executed through `run_configuration_query`;
- result partition contains every design exactly once per query;
- any confirmed match identifies at least one matching configuration;
- minimum 3/4 evaluability for each of Q1/Q2/Q10;
- `FALSE_CONFIRMED_RESULT = 0` under independent expected controls;
- owner-test output is deterministic offline.

## Deliverables

Expected bounded deliverables:

1. `research/benchmark/waves/sl0039-seed-corpus-wave1/REPORT.md`;
2. compact source/evidence record(s) for the three new designs;
3. three new real configuration projections, or an equally compact retained representation consumed by the owner test;
4. `scripts/search_seed_corpus_wave1.py`;
5. focused tests, normally `tests/unit/test_search_seed_corpus_wave1.py`;
6. this slice document moved to `REVIEW` on successful handoff.

Do not duplicate the accepted Oceanis 30.1 evidence/projection into the new folder merely to make the package look self-contained; reference and reuse it.

## Acceptance criteria

- [x] Exactly Bavaria Cruiser 34, Contessa 32, Oceanis 30.1 and Lagoon 42 form the Wave-1 Search cohort.
- [x] Product execution checks remain PASS with no scope expansion.
- [x] Existing Oceanis 30.1 accepted projection is reused unchanged.
- [x] Bavaria Cruiser 34, Contessa 32 and Lagoon 42 are represented by real `is_fixture=False` provenance-backed projections.
- [x] Only facts required by Q1/Q2/Q10 are researched/admitted except where a minimal identity/configuration prerequisite is unavoidable.
- [x] External technical-evidence research stays within the 12-surface / 5-per-design cap.
- [x] No marketplace/competitor/reference result self-authorizes technical Search truth.
- [x] No historical SailboatData scrape value becomes canonical Search truth.
- [x] Multiple material factory configurations are explicit where proven and are not collapsed.
- [x] Q1, Q2 and Q10 are invoked unchanged through the existing configuration-aware Search kernel.
- [x] Every query partitions all four designs into confirmed match / confirmed non-match / insufficient data exactly once.
- [x] Every confirmed match exposes at least one matching configuration ID.
- [x] Q1, Q2 and Q10 each achieve at least 3/4 evaluability without truth relaxation.
- [x] `FALSE_CONFIRMED_RESULT = 0`.
- [x] Owner command visibly prints the four-design real Search results and reasons.
- [x] Offline tests are deterministic and require no live network.
- [x] Repository validation, ruff, mypy and full test suite pass; project coverage remains >=90%.
- [ ] Exact-head CI and Manufacturer artifact reproducibility are green before review acceptance. **NOT VERIFIED locally** — requires remote CI observation on the exact final pushed HEAD SHA; see completion report.
- [x] No next Seed-Corpus wave, Concierge test, market-access implementation or Phase-E work is started automatically.

## Expected touch points

Expected new/modified paths are limited to:

- `docs/slices/SLICE-0039-seed-corpus-wave1-real-multi-design-search.md`;
- `research/benchmark/waves/sl0039-seed-corpus-wave1/**`;
- `scripts/search_seed_corpus_wave1.py`;
- `tests/unit/test_search_seed_corpus_wave1.py`;
- only the smallest additional test/support helper if existing accepted boundaries make it unavoidable.

Production `src/hullq/search/**` should remain unchanged unless a concrete bug in the accepted Search kernel prevents this exact capability. If such a bug is found, STOP and report before widening scope.

## Validation

```text
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
uv run python scripts/search_seed_corpus_wave1.py
```

## Stop conditions

Stop and report instead of inventing a solution when:

- a locked Wave-1 design cannot be identified/admitted under accepted rules;
- source access/reuse cannot support the intended retained factual evidence;
- the research cap is exhausted before the minimum utility gate can be proven;
- an accepted Search/Oceanis semantic regresses;
- Q1/Q2/Q10 require a Search-semantic/schema change rather than data work;
- meeting the utility gate would require replacing a design, guessing a value, weakening UNKNOWN, or widening the slice.

## Status handoff rule

The implementation/research agent may set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark the slice `DONE` or merge it.

## Required completion report

Use the repository Slice Template completion-report structure exactly.

The report must additionally state:

- exact Wave-1 result distribution for Q1/Q2/Q10;
- evaluability rate per query;
- configuration count per design;
- external evidence-surface count per new design and total;
- any retained UNKNOWN/conflict/applicability limitation;
- confirmation that no work on the next corpus wave or Concierge execution was started.
