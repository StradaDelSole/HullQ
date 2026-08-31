# SLICE-0037 — Oceanis 30.1 Real-Search Pilot

**ID:** SLICE-0037  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** P0 Data/Search vertical — first real BoatDesign through the existing Search kernel  
**Depends on:** SLICE-0036 owner-accepted / DONE; SLICE-0035 owner-accepted / DONE; `specs/SEARCH_BENCHMARK.v0.1.md` ACCEPTED  
**Blocks:** first real-design local owner-test gate and the later API/frontend architecture decision

## Objective

Produce a provenance-backed, non-fixture BENETEAU Oceanis 30.1 resolved configuration projection from bounded authoritative official evidence, apply the accepted Marine Technical Entailment v0.1 contract fail-closed to its in-scope facts, and run the unchanged locked Q1–Q10 benchmark queries through the existing `hullq.search.configuration_engine` via one minimal local owner-test command.

This slice succeeds only if a real Oceanis 30.1 projection reaches the existing Search kernel without synthetic fixture truth, without flattening configuration-sensitive facts, and without weakening the accepted three-valued Search semantics.

## Why this slice exists

SLICE-0035 proved categorical and configuration-aware Search semantics only against explicit synthetic fixtures. SLICE-0036 then bounded which existing marine technical facts may definitionally entail other facts, but deliberately shipped no production inference engine.

The accepted product guardrail now forbids another general schema/breadth/governance slice before at least one real BoatDesign is searchable through the existing Search kernel unless a genuine technical blocker forces it. Oceanis 30.1 is the locked `MOVABLE_APPENDAGE` diversity member of `SEARCH_BENCHMARK.v0.1.md` and is therefore the correct first practical consumer.

The repository does not currently retain Oceanis 30.1 research evidence. This slice therefore includes only the bounded, design-specific authoritative research required to create the real search projection. It is not a broad research wave or a canonical-corpus completion initiative.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `CLAUDE.md`;
- `docs/slices/SLICE-0036-acceptance-closure.md`;
- `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md`;
- `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`;
- `specs/SEARCH_QUERY_SEMANTICS.v0.1.md`;
- `specs/SEARCH_BENCHMARK.v0.1.md`;
- `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`;
- `specs/BOAT_DESIGN_SCHEMA.v0.6.json`;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- `specs/IDENTITY_MODEL.v0.2.md` only as needed to establish the Oceanis 30.1 BoatDesign/configuration scope;
- `src/hullq/search/configuration.py`;
- `src/hullq/search/configuration_engine.py`;
- `src/hullq/search/query_mixed.py`;
- `src/hullq/search/values.py`;
- `scripts/search_demo_configuration_aware.py` only as the existing fixture-demo integration example;
- `fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json` as the locked machine-readable Q1–Q10 query shapes.

### Accepted-status note

SLICE-0036 is owner-accepted and closed. If the human-readable MTE document or its JSON registry still carries stale `PROPOSED` status metadata, `docs/slices/SLICE-0036-acceptance-closure.md` and the accepted exact-head history control the acceptance state. Do not reinterpret or reopen MTE semantics because of stale status metadata. A metadata-only correction may be made in this slice if it can be done without semantic changes, but it is not a reason to broaden scope.

## Fixed target identity

The only target design is:

```text
BENETEAU Oceanis 30.1
```

This is the locked benchmark corpus member identified in `SEARCH_BENCHMARK.v0.1.md` as diversity slot `MOVABLE_APPENDAGE`.

Do not replace it with another boat merely because evidence is sparse, difficult or configuration-sensitive.

Do not infer a production-year range, design epoch, option set or configuration boundary from the model name alone. Establish only the scope positively supported by authoritative source evidence.

## Fixed search suite

Run the exact locked PRIMARY Q1–Q10 query shapes from `SEARCH_BENCHMARK.v0.1.md` / the existing Q1–Q10 machine fixture. Do not rewrite thresholds, categories or roles after observing the Oceanis results.

The expected query IDs are exactly:

```text
Q1 Q2 Q3 Q4 Q5 Q6 Q7 Q8 Q9 Q10
```

The existing Search kernel remains controlling. This slice does not introduce a second evaluator.

## Source and rights boundary

Positive Oceanis facts may come only from authoritative primary factual surfaces controlled by:

1. BENETEAU / the official BENETEAU site, current or official heritage/archive surfaces;
2. BENETEAU-hosted official brochures, manuals, equipment/specification material or launch/change notices;
3. Finot-Conq or another directly responsible official naval-architect source only when genuinely needed for a design-specific fact not established by BENETEAU.

Search engines may be used only for navigation to an allowed source surface. Search-result snippets are not evidence.

Do not use as positive evidence:

- SailboatData;
- Wikipedia/Wikimedia article text;
- brokers or dealers;
- owner forums/posts;
- review sites;
- general specification databases;
- copied/mirrored brochures on third-party hosts;
- AI-generated summaries.

Starting official locators, to be independently retrieved and verified by the implementation agent rather than trusted as facts merely because they are listed here:

- `https://www.beneteau.com/oceanis/oceanis-301`
- `https://www.beneteau.com/en-us/oceanis/oceanis-301`
- `https://brochures.beneteau.com/oceanis301/EN/`
- `https://www.beneteau.com/en-us/newsroom-actualite/new-oceanis-301`

Use the accepted `SOURCE_RIGHTS_POLICY.v0.1.md` without weakening it. For bounded manual use of discrete technical facts from an unlicensed public primary source, positively establish the applicable SR-6.6 conditions before treating the facts as usable.

Do not vendor third-party expressive HTML/PDF/image/layout content unless redistribution rights are independently established. Retain metadata and discrete factual observations only.

### Retrieval ceiling

```text
maximum semantic authoritative-source retrievals: 12
```

A semantic retrieval is one distinct source page/document inspected for identity, rights, configuration/applicability or technical facts. Redirects/retries that yield no distinct semantic document need not count separately.

If the required proof cannot be established within the ceiling, fail closed rather than expanding research into a campaign.

## In scope

1. Bounded authoritative research of Oceanis 30.1 identity, specification scope and the P0/Search fields needed by Q1–Q10.
2. Positive source-rights disposition for every retained source used to authorize a confirmed direct fact.
3. Retained source metadata, retrieval/accounting information and discrete factual observations sufficient for independent audit.
4. Explicit resolved configuration identity for every configuration used by Search.
5. A real `DesignConfigurationSet` with `is_fixture=False`.
6. `configuration_space_complete=False` unless the materially relevant factory configuration space is positively established as complete. Do not infer completeness from the number of discovered configurations.
7. Qualified numeric/categorical Search projections using the existing `ValueQualification`/`Qualified*Value` boundaries.
8. Explicit application/verification of any applicable SLICE-0036 MTE rule to Oceanis facts, with rule ID/version, exact source fact, evidence reference and applicability/configuration lineage retained for every materialized derived fact.
9. Explicit `UNKNOWN`/other fail-closed outcome where evidence or applicability does not authorize concrete truth.
10. The unchanged locked Q1–Q10 executed through `run_configuration_query` / the existing `hullq.search.configuration_engine`.
11. One minimal local owner-test script, normally `scripts/search_oceanis_30_1.py`, that visibly prints Oceanis 30.1 Q1–Q10 result class, reason where insufficient, per-configuration truth and matching configuration IDs.
12. Focused deterministic tests covering the retained real projection, configuration identity/applicability, direct-vs-derived lineage and Search outcomes.

## Explicitly out of scope

- PostgreSQL persistence/read model/index work;
- FastAPI/public HTTP endpoints;
- frontend, SEO or public URL work;
- broad twelve-design benchmark research or Snapshot A;
- any boat other than Oceanis 30.1;
- new BoatDesign schema version, fields or enum tokens;
- changes to `SEARCH_QUERY_SEMANTICS.v0.1.md`;
- changes to Q1–Q10 thresholds/categories/roles;
- PREFER, OR or NOT;
- a generic MTE inference engine, recursive chaining or probabilistic inference;
- automatic Cartesian expansion of DesignOption/NamedVariant combinations;
- canonical PostgreSQL BoatDesign admission/promotion;
- market listings, listing deduplication, geography, monitoring, auth or pricing;
- broad source-adapter/crawler work;
- a general BENETEAU/Oceanis ingestion adapter.

## Required behavior

### A. Real evidence, not a renamed fixture

The retained Oceanis projection MUST be auditable back to positively cleared authoritative source facts. Merely changing an existing fixture's `design_id` or setting `is_fixture=False` does not satisfy this slice.

For each confirmed direct Search field retain at least:

- normalized field path/name used by Search;
- discrete value;
- qualification/resolution state;
- source/evidence reference;
- source applicability/configuration scope;
- direct-vs-derived classification.

A retained artifact MUST NOT self-authorize its own `CONFIRMED` state. Focused tests/verifiers must independently enforce the accepted source/qualification/scope conditions.

### B. Configuration-sensitive draft must not be flattened

Oceanis 30.1 is the locked `MOVABLE_APPENDAGE` diversity control. A manufacturer-wide/design-wide minimum or maximum draft is not by itself permission to assign that number to an arbitrary named configuration.

To use a draft value for a specific resolved configuration, authoritative evidence must positively bind the value to that configuration/appendage state or otherwise establish an equivalent unambiguous scope.

Do not silently turn a page-level `draft min/max` pair into two invented configurations.

Do not assume terms such as `lifting keel`, `swing keel`, `shallow draft`, `deep draft` or `performance draft` are interchangeable unless the authoritative evidence explicitly supports the mapping needed by the HullQ field/configuration representation.

### C. Required configuration-sensitive proof

The slice must demonstrate at least one configuration-sensitive `CONFIRMED_MATCH` through the existing Search kernel using an explicit factory-supported Oceanis 30.1 resolved configuration.

The natural candidate is Q10 (`Draft <= 1.60 m`), but the acceptance criterion is semantic rather than hardcoded to a desired result: use whichever locked query is actually established by authoritative evidence and the unchanged Q1–Q10 suite.

A confirmed configuration-sensitive match MUST identify the exact `matching_configuration_ids` and MUST NOT rely on a design-wide flattened min/max value.

If bounded authoritative research cannot establish the exact factory configuration/value applicability required for any configuration-sensitive confirmed match, STOP and report `BLOCKED`; do not weaken the requirement or manufacture a mapping.

### D. Search truth remains fail-closed

- `UNKNOWN`, missing, provisional, unresolved-conflict or applicability-unknown values never become confirmed truth.
- A known same-scope contradiction is surfaced, never overwritten.
- Different configuration/specification scopes are not merged into one synthetic configuration.
- Missing evidence does not establish negative facts.
- `configuration_space_complete=False` forbids universal confirmed non-match authority when completeness is required by the existing engine, but does not block an existential match already established by a known configuration.
- Every confirmed match identifies at least one matching configuration.

The hard semantic invariant remains:

```text
FALSE_CONFIRMED_RESULT = 0
```

### E. Apply MTE exactly, but do not build an inference subsystem

For every relevant direct Oceanis fact falling inside the SLICE-0036 fixed field inventory:

1. classify the fact using the accepted MTE registry;
2. if it is `DIRECT_ONLY`, use it only directly;
3. if it is `NO_DERIVATION`, derive nothing from it;
4. if it is a qualified `DEFINITIONAL_ENTAILMENT` source and all guard conditions are satisfied, an explicitly materialized derived fact MAY be retained only with required rule/input/scope lineage;
5. if an explicit same-scope target fact contradicts the rule output, surface `UNRESOLVED_CONFLICT` rather than choosing one;
6. do not recursively chain derived outputs into new rule inputs in v0.1.

No production generic rule interpreter is required or authorized. A small test/offline verifier may validate explicitly materialized derived facts against the declarative registry. If implementing correct MTE application requires a general production inference engine, STOP and report instead.

### F. Minimal owner-test surface

Provide a deterministic local command:

```text
uv run python scripts/search_oceanis_30_1.py
```

It must make the real-vs-fixture distinction visible and output, for each Q1–Q10:

- query ID/role/description;
- Oceanis 30.1 result class;
- insufficient reason where applicable;
- per-configuration truth;
- exact matching configuration IDs where matched.

The script must use the retained real projection and the existing Search kernel, not duplicate the evaluator in presentation code.

## Deliverables

Expected bounded deliverables:

1. `research/benchmark/waves/sl0037-oceanis-30-1/` containing retained source/rights/retrieval metadata and the deterministic real search projection package. Use compact JSON/Markdown artifacts as appropriate; do not retain expressive source content without rights.
2. `scripts/search_oceanis_30_1.py`.
3. Focused tests, normally `tests/unit/test_search_oceanis_30_1.py` and/or one bounded contract test for the retained projection package.
4. Any tiny test/offline verification helper needed to validate explicitly materialized MTE-derived facts; prefer test/script code over production `src/` expansion.
5. This slice document moved to `REVIEW` on successful implementation handoff.

Do not create a new generic JSON-schema subsystem solely for this one retained pilot unless the existing repository validator genuinely requires it.

## Acceptance criteria

- [ ] Only the fixed Oceanis 30.1 target was researched/implemented.
- [ ] Every positive technical fact used for Search comes from positively rights-cleared authoritative source evidence within the retrieval ceiling.
- [ ] The retained package records source URL/identifier, access timestamp, source class, concise discrete fact basis and rights disposition without vendoring unauthorized expressive content.
- [ ] The target identity/specification scope is positively stated; no unsupported production-year/design-epoch boundary is invented.
- [ ] At least one explicit factory-supported resolved configuration is represented and `DesignConfigurationSet.is_fixture` is exactly `False`.
- [ ] `configuration_space_complete` is `False` unless completeness is independently established.
- [ ] Configuration-sensitive numeric/category facts are bound only to the configuration/applicability scope actually supported by evidence; page-level min/max values are not flattened into invented configurations.
- [ ] At least one locked Q1–Q10 query returns `CONFIRMED_MATCH` from the real Oceanis data.
- [ ] At least one locked Q1–Q10 query returns a configuration-sensitive `CONFIRMED_MATCH` tied to an explicit factory-supported Oceanis configuration; if this cannot be established from bounded authoritative evidence, the slice is `BLOCKED`, not weakened.
- [ ] All exact locked Q1–Q10 are executed through the existing configuration-aware Search kernel without threshold/category/role changes.
- [ ] Every confirmed match reports at least one exact `matching_configuration_id`.
- [ ] Known UNKNOWN/provisional/conflict/applicability-unknown cases remain `INSUFFICIENT_DATA` where existing Search semantics require it.
- [ ] No known false confirmed match or false confirmed non-match exists (`FALSE_CONFIRMED_RESULT = 0`).
- [ ] Every relevant Oceanis MTE source fact is classified against the accepted registry and every retained derived fact, if any, carries rule ID/version + exact input/evidence + material scope lineage.
- [ ] No generic/recursive/probabilistic production MTE inference engine was added.
- [ ] `uv run python scripts/search_oceanis_30_1.py` runs deterministically and visibly reports the real Oceanis Q1–Q10 outcomes.
- [ ] Focused adversarial tests prove a missing/weak/applicability-ambiguous fact cannot be promoted to confirmed Search truth merely by editing the retained projection artifact.
- [ ] Full local validation passes and repository coverage remains at or above the existing required threshold.
- [ ] Remote CI is observed SUCCESS on the exact final branch HEAD.
- [ ] Manufacturer artifact reproducibility is observed SUCCESS on the exact final branch HEAD.

## Expected touch points

Expected only as needed:

- `research/benchmark/waves/sl0037-oceanis-30-1/**`
- `scripts/search_oceanis_30_1.py`
- `tests/unit/test_search_oceanis_30_1.py`
- possibly one focused `tests/contract/**` file if needed for retained-package/MTE validation
- `docs/slices/SLICE-0037-oceanis-30-1-real-search-pilot.md`
- metadata-only MTE status correction if performed without semantic changes

Production `src/hullq/search/**` should normally remain unchanged. If a tiny reusable bridge from retained qualified data to the existing `DesignConfigurationSet` is genuinely necessary, keep it persistence-neutral and truth-neutral; STOP if the correct solution requires redesigning Search semantics or building a generalized ingestion/inference layer.

## Validation

Run at minimum:

```bash
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
uv run python -m pytest
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run python scripts/search_oceanis_30_1.py
```

Run any focused SLICE-0037 tests separately as useful.

External gates on the exact final branch HEAD:

- CI
- Manufacturer artifact reproducibility

Do not commit merely to record external gate results.

## Stop conditions

STOP and report `BLOCKED` rather than inventing a solution if any of the following occurs:

- required BENETEAU/official source use cannot be positively cleared under the accepted rights policy;
- no authoritative evidence within the fixed retrieval ceiling can positively bind a qualifying draft/technical value to an explicit factory-supported configuration strongly enough to demonstrate the required configuration-sensitive match;
- authoritative evidence establishes a material same-scope conflict that cannot be resolved under accepted rules;
- correct implementation requires a new BoatDesign schema field/enum/version;
- correct implementation requires changing Search truth semantics or the locked Q1–Q10 suite;
- correct implementation requires a generic/recursive MTE inference engine;
- correct implementation requires automatic unsupported configuration Cartesian expansion;
- fulfilling the slice would require PostgreSQL, API or frontend architecture work;
- the target would need to be replaced merely because Oceanis 30.1 research is inconvenient or sparse.

## Product guardrail after this slice

If SLICE-0037 succeeds, HullQ has crossed the accepted first-real-search gate. The next decision may then evaluate the thinnest useful owner/product surface (for example read-model/HTTP/UI sequencing) based on what this real vertical exposed.

If SLICE-0037 is blocked for a genuine technical reason, escalate that concrete blocker to the Project Owner. Do not insert an unrelated general schema/breadth/governance slice.

## Status handoff rule

The implementation/research agent may recommend or set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, explicit Project Owner acceptance, exact reviewed-head merge, compact acceptance closure and successful local `FINISH_SLICE` cleanup.

A successful implementation-agent completion therefore hands the slice off in `REVIEW`.

## Required completion report

Use the exact completion-report structure from `docs/slices/SLICE_TEMPLATE.md`.

Additionally report concisely:

- exact final branch HEAD SHA;
- exact retained Oceanis source list + semantic retrieval count;
- source-rights disposition;
- identity/specification scope actually established;
- explicit resolved configuration IDs and why each is evidence-supported;
- `configuration_space_complete` value and basis;
- direct confirmed Search fields and their evidence refs;
- Oceanis MTE classifications/rules actually used and derived-lineage records, if any;
- exact Q1–Q10 outcome summary;
- which query supplied the required configuration-sensitive confirmed match and exact matching configuration ID(s);
- any deliberate UNKNOWN/INSUFFICIENT outcomes and why they remain unresolved;
- `FALSE_CONFIRMED_RESULT` assessment;
- local owner-test command result;
- local validation results;
- exact-head CI and Manufacturer artifact reproducibility states;
- unresolved findings/ambiguities/scope deviations.

After the final handoff, STOP.

---

## Implementation completion report

### Slice

- Slice ID: `SLICE-0037`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`
- Exact final branch HEAD SHA: recorded in the conversation completion report
  (a file cannot self-reference its own content hash at commit time); see
  `git log -1` on `slice/0037-oceanis-30-1-real-search-pilot`.

### Changes

- Changed files: `research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md`,
  `research/benchmark/waves/sl0037-oceanis-30-1/source_retrieval_log.json`,
  `research/benchmark/waves/sl0037-oceanis-30-1/oceanis_30_1_projection.v1.json`,
  `scripts/search_oceanis_30_1.py`, `tests/unit/test_search_oceanis_30_1.py`,
  this slice document (status only).
- Requirements implemented or researched: real, provenance-backed, non-fixture
  BENETEAU Oceanis 30.1 projection researched from bounded authoritative
  official sources; explicit resolved-configuration set
  (`DesignConfigurationSet.is_fixture=False`) built and run through the
  unchanged `hullq.search.configuration_engine` for the exact locked Q1-Q10
  suite; SLICE-0036 MTE registry classification applied to every relevant
  qualified fact (zero derived facts materialized — see REPORT.md section 6).
- Tests/fixtures added or updated: `tests/unit/test_search_oceanis_30_1.py`
  (26 focused tests, including adversarial FALSE_CONFIRMED_RESULT coverage).
  No existing fixture/spec file was modified.

### Validation

- Local validation: `PASS`
- Commands run: `uv run ruff format --check .`; `uv run ruff check .`;
  `uv run mypy src`; `uv run python scripts/validate_repository.py`;
  `uv run python -m coverage run -m pytest`; `uv run python -m coverage report`;
  `uv run python scripts/search_oceanis_30_1.py`.
- Results: ruff format/check clean; mypy strict clean (56 source files);
  repository validator PASS (88/88 requirements); 3284 passed / 217 skipped
  (pre-existing DB/live-network gaps, unrelated to this slice); coverage
  91.74% total (>= repository's required threshold), `src/hullq/search/**`
  100% (unchanged, no production Search code was modified); the owner-test
  script runs deterministically and produces the outcome distribution in
  `REPORT.md` section 8 (CONFIRMED_MATCH: Q1, Q2, Q10; INSUFFICIENT_DATA:
  Q3-Q9; CONFIRMED_NON_MATCH: none).

### External verification

- Remote CI: `NOT VERIFIED` (to be observed on the exact final pushed HEAD)
- Other external gates: `NOT VERIFIED` (Manufacturer artifact reproducibility,
  to be observed on the exact final pushed HEAD)

### Findings

- Unresolved findings: none blocking.
- Spec/ADR ambiguities: none encountered beyond the documented, deliberate
  fail-closed treatment of the displacement cross-source discrepancy and the
  rig/rudder/cockpit fields left unresolved (REPORT.md section 5).
- Scope deviations: a mid-research `robots.txt` finding
  (`pro.beneteauusa.com`: `Disallow: /`) required excluding the single most
  detailed source document from the evidence basis after it had already been
  read; this narrowed the confirmed field set materially (no displacement,
  rig, keel-shape, rudder-support or cockpit-position facts could be
  confirmed from the remaining robots.txt-clear sources) but did not change
  scope, target identity, or any locked query/threshold — see REPORT.md
  section 2 for the full account. This is disclosed as a research-basis
  narrowing, not a scope deviation from the slice contract itself.

### Follow-up

- Recommended next action: independent review of this REVIEW-state slice;
  no further action by this agent until review findings return.

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE`.

---

## Amendment 1 completion report (review 5067543634 — CHANGES REQUIRED)

Bounded amendment to the exact same branch/worktree/PR #110, in response to
independent review `5067543634` on prior head
`707bb6805e61d5de06afb767a176aa5ff15ffb44`. No new Oceanis technical research
was performed; the configuration-sensitive technical result was already
accepted as directionally sound. Two blockers were closed: (1) the retained
projection could self-authorize its own CONFIRMED state, and (2) the
automated-access clearance for the positive-evidence sources was recorded as
"manual-style" rather than honestly as programmatic/agent-mediated access
under the accepted `SOURCE_SCHEMA.v0.2` vocabulary.

### Slice

- Slice ID: `SLICE-0037`
- Recommended slice state: `REVIEW`
- Scope completed: `YES` (bounded amendment scope only)
- New exact final branch HEAD SHA: recorded in the conversation completion
  report (see `git log -1` on `slice/0037-oceanis-30-1-real-search-pilot`).

### Changes

- Changed files: `scripts/search_oceanis_30_1.py` (independent admission
  oracle + `validate_oceanis_30_1_projection`, wired into
  `load_oceanis_30_1_configuration_set`),
  `tests/unit/test_search_oceanis_30_1.py` (+17 admission-boundary
  adversarial tests, +5 rights-bookkeeping tests, replaced the
  Q10-dependent completeness test's role with a direct
  admission-layer test),
  `research/benchmark/waves/sl0037-oceanis-30-1/oceanis_30_1_projection.v1.json`
  (`configuration_evidence_refs` added per configuration; a
  `self_authorization_boundary_note` added; no fact value changed),
  `research/benchmark/waves/sl0037-oceanis-30-1/source_retrieval_log.json`
  (SRC-1/SRC-5/SRC-6 `rights` rewritten in full `SOURCE_SCHEMA.v0.2` shape;
  SRC-7 — BENETEAU Legal Notices/Terms — added; retrieval count 6 -> 7),
  `research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md` (section 11
  added), this slice document (this report).
- No production `src/hullq/search/**` code changed. No Search semantics
  changed. No Q1-Q10 threshold/category/role changed. No other boat
  researched. No new PR opened; no merge; not marked DONE.
- Requirements implemented: SLICE-0037 Required Behavior A's
  self-authorization prohibition, independently enforced at code level for
  the first time; SR-6.6(6) automated-access clearance recorded accurately.
- Tests/fixtures added or updated: `tests/unit/test_search_oceanis_30_1.py`
  grew from 26 to 52 tests (26 new).

### Validation

- Local validation: `PASS`
- Commands run: `uv run ruff format --check .`; `uv run ruff check .`;
  `uv run mypy src`; `uv run python scripts/validate_repository.py`;
  `uv run python -m coverage run -m pytest`; `uv run python -m coverage report`;
  `uv run python scripts/search_oceanis_30_1.py`.
- Results: ruff/mypy clean; repository validator PASS (88/88); 3310 passed /
  217 skipped (pre-existing DB/live-network gaps, +26 vs. the prior head);
  coverage 91.74% total (unchanged — `src/hullq/search/**` remains 100%,
  untouched); owner-test script deterministic, Q1/Q2/Q10 CONFIRMED_MATCH,
  Q3-Q9 INSUFFICIENT_DATA, zero CONFIRMED_NON_MATCH — byte-identical outcome
  distribution to the prior reviewed head.

### External verification

- Remote CI: `NOT VERIFIED` (to be observed on the new exact final pushed
  HEAD, same PR #110)
- Other external gates: `NOT VERIFIED` (Manufacturer artifact
  reproducibility, same PR #110)

### Findings

- Unresolved findings: none blocking.
- Scope deviations: none. Both amendment items were explicitly requested by
  the review; no additional research, no new boat, no Search semantics
  change.

### Follow-up

- Recommended next action: independent re-review of PR #110 on the new head.

### Agent declaration

- No work outside the two requested amendment items was started.
- No unverified acceptance criterion was marked as passed.
- No new PR was created; PR #110 was updated in place.
- The next slice was not started automatically.
- The agent has NOT marked this slice `DONE` and has NOT merged.