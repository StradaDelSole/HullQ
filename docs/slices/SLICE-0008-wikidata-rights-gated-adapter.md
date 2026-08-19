# SLICE-0008 — First Rights-Gated Real Adapter: Wikidata

**ID:** SLICE-0008  
**Type:** IMPLEMENTATION  
**Status:** REVIEW  
**Stage:** 2.7 — first controlled real external acquisition  
**Depends on:** SLICE-0007 accepted / DONE  
**Blocks:** SLICE-0009

## Objective

Implement HullQ's first real external acquisition adapter against Wikidata structured data, using the accepted SLICE-0007 rights/access gate before network use and the SLICE-0006 provenance boundary after extraction.

This slice proves the smallest end-to-end external-data path:

```text
reviewed Wikidata Source record
        +
ResearchJob / bounded acquisition request
        ↓
SLICE-0007 automated-ingestion rights gate
        ↓ ALLOWED only
HTTP acquisition from official Wikimedia/Wikidata endpoint(s)
        ↓
raw response preserved in memory / test fixture boundary
        ↓
Wikidata statement parsing with qualifiers retained
        ↓
FieldEvidence candidates
        ↓
NO canonical FieldResolution / BoatDesign write yet
```

The goal is not broad ingestion. The goal is to prove that HullQ can fetch a small, reproducible, rights-cleared real sample and preserve enough source semantics to inform SLICE-0009.

## Controlling artifacts

- `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md` — Wikidata is the strongest current broad bootstrap candidate.
- `architecture/decisions/ADR-0005-source-rights-clearance.md`.
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`.
- `specs/SOURCE_SCHEMA.v0.2.json`.
- SLICE-0007 runtime in `src/hullq/sources/rights.py`.
- SLICE-0007 ResearchJob runtime in `src/hullq/research/jobs.py`.
- SLICE-0006 provenance runtime in `src/hullq/domain/provenance.py`.
- SLICE-0004 measurement normalization boundary.
- accepted identity contracts from SLICE-0005.

External source facts already established by reviewed HullQ research and rechecked during preparation:

- Wikidata structured data is CC0.
- official Wikimedia API use requires a descriptive User-Agent/contact and compliance with throttling/rate-limit instructions.
- Wikidata's sailboat-class model uses `Q106179098` and structured properties including manufacturer `P176`, designer `P287`, length `P2043`, width `P2049`, height `P2048`, mass `P2067`, with `P642` qualifiers distinguishing concepts such as LOA/LWL, draft/air-draft, displacement/ballast.

## Core rules

1. **Rights gate before network.** No adapter HTTP request may be sent until `check_source_use(..., SourceUse.AUTOMATED_INGESTION, ...)` returns `ALLOWED` for the reviewed Wikidata Source record.
2. **No license inference in code.** The adapter must not grant itself permission because a URL contains `wikidata.org` or because a payload says CC0. Permission comes from the reviewed Source record.
3. **Controlled, not broad.** SLICE-0008 is a bounded probe/acquisition slice. It must not become a production crawler or full Wikidata dump importer.
4. **Descriptive User-Agent.** Requests must send an explicit HullQ User-Agent containing a contact identifier supplied by configuration. Generic HTTPX/Python user agents are not acceptable.
5. **Respect API pressure signals.** HTTP 429 / Retry-After and explicit service throttling must result in a deterministic non-success acquisition outcome; no aggressive concurrent retry loop.
6. **Preserve statement semantics.** Do not flatten qualified Wikidata values into unlabeled canonical facts. Raw claim/value/unit/qualifier identity must remain recoverable.
7. **Unknown stays unknown.** Missing properties produce absence/unknown, never fabricated values.
8. **No authority shortcut.** Wikidata being open/structured does not make every statement correct and does not resolve conflicts automatically.
9. **Evidence before canonical.** This slice may create `FieldEvidence` / normalized candidates where mappings are deterministic, but must not create accepted `FieldResolution` or mutate BoatModel/BoatDesign canonical records.
10. **No private boat-list content.** The private 9,277-row reference universe must not be committed or used as a source payload.

## In scope

### 1. Reviewed Wikidata Source record

Add a repository-safe Source record for the exact Wikidata access path used by this adapter, validated against `SOURCE_SCHEMA.v0.2.json`.

It must document at least:

- stable HullQ `source_id`;
- publisher/operator;
- API access method and endpoint family;
- CC0 structured-data rights basis;
- reviewed automated-access state for this concrete access path;
- use-specific HullQ clearances;
- API/User-Agent/rate-limit operational conditions in structured notes/evidence;
- review date and rights evidence URLs.

Do not weaken the existing generic CC0 fixture. This is a source-specific reviewed record for Wikidata.

### 2. Bounded adapter configuration

Add a small immutable configuration/value-object boundary containing at least:

- descriptive User-Agent/contact string;
- request timeout;
- explicit item/query limit for this controlled slice;
- optional language preference with deterministic fallback.

The caller must explicitly bound the acquisition. This slice must refuse an unbounded request. A hard implementation safety ceiling for the controlled probe is acceptable, but it must be documented as a SLICE-0008 operational cap, not a rights/licence rule.

### 3. Rights-gated HTTP boundary

Use HTTPX from the accepted toolchain.

The adapter must:

- accept the reviewed Source record or source-id-resolved equivalent;
- call the SLICE-0007 automated-ingestion gate before any request;
- refuse acquisition on BLOCKED / CONDITIONAL / UNKNOWN / LEGAL_REVIEW outcomes;
- keep request counting attributable to the same `source_id`;
- use the configured User-Agent;
- avoid uncontrolled concurrency;
- expose deterministic error/result types for timeout, HTTP error, throttling and malformed JSON.

Do not build a generic scraping framework.

### 4. Sailboat-class discovery probe

Provide a bounded official-Wikidata discovery operation for items that are direct instances of sailboat class `Q106179098`.

Preferred approach: a narrowly scoped WDQS/SPARQL query equivalent to:

```sparql
?sailboat_class wdt:P31 wd:Q106179098
```

Requirements:

- deterministic query text/version in code;
- explicit caller limit;
- deterministic extraction of QIDs;
- no silent deduplication beyond exact QID identity;
- preserve query/access metadata sufficient to reproduce the probe.

If implementation evidence shows WDQS is unsuitable for the controlled adapter, stop and report rather than silently switching to a different acquisition strategy.

### 5. Entity acquisition

Fetch structured Wikidata entity data for a bounded QID set using an official Wikidata/Wikibase API surface.

Requirements:

- validate QID syntax before network use;
- batch only within documented/controlled limits;
- preserve entity QID, labels/aliases requested, claims, statement IDs/ranks where present, mainsnak value/unit and qualifiers required for HullQ field interpretation;
- do not fetch Wikipedia article text or mixed CC-BY-SA content in this slice.

### 6. Minimal deterministic field extraction

Implement only the common fields strongly justified by the reviewed Wikidata sailboat-class model:

- label / source identity name;
- manufacturer statement(s) `P176` as raw identity evidence only — do not infer Brand vs Organization role solely from the property label;
- designer statement(s) `P287` as evidence/reference identity values;
- qualified length `P2043`:
  - LOA qualifier `Q2358152`;
  - LWL qualifier `Q1817392`;
- qualified width/beam from the accepted Wikidata model, preserving qualifiers;
- qualified height/draft `P2048` with draft qualifier `Q244777` where present;
- qualified mass `P2067` with displacement qualifier `Q5636358` and ballast qualifier `Q5461048` where present;
- optional `P1092` total produced as raw evidence if present.

Do not add keel/rudder/skeg taxonomy in this slice. Do not infer configuration from free text, subclasses or unlabeled values unless explicitly specified in the slice.

### 7. Provenance integration

For mapped scalar observations, produce SLICE-0006-compatible evidence with:

- Wikidata Source `source_id`;
- locator identifying QID + property + statement ID/index as available;
- raw source representation preserved separately from normalized candidate;
- qualifiers retained sufficiently to explain semantic basis;
- observed/retrieved timestamp;
- deterministic producer metadata/version.

Where SLICE-0004 unit normalization applies, reuse it; do not duplicate conversion logic.

No evidence item may pretend to be a canonical resolution.

### 8. Reproducible source-quality report

The slice must emit a deterministic in-memory/report object for the controlled sample containing at least:

- requested/discovered QID count;
- successfully fetched entity count;
- per-field presence counts for the mapped fields;
- malformed/unsupported statement counts;
- statements routed to review/unsupported because qualifiers or semantics cannot be mapped safely;
- retrieval count attributed to the Wikidata `source_id`.

A small checked-in Markdown/JSON result from an explicitly run live probe MAY be committed only if it contains CC0 Wikidata structured data or aggregate metrics and no unrelated third-party content. Tests must not require live network access.

## Live-network test policy

Normal CI/unit/contract tests MUST be deterministic and offline using synthetic or minimal CC0-safe recorded payloads.

A real network smoke/integration test may exist only as an explicit opt-in test/command and must:

- be skipped by default in CI;
- use the same rights gate and User-Agent requirements as production adapter code;
- remain tightly bounded;
- report the exact endpoint/query/QIDs used;
- fail clearly on network unavailability rather than weakening offline tests.

## Required tests

Cover at least:

1. reviewed Wikidata Source record validates against SOURCE_SCHEMA.v0.2.
2. adapter performs zero HTTP calls when the rights gate is non-allow.
3. descriptive User-Agent/contact is mandatory.
4. unbounded/invalid requested item limit is rejected.
5. malformed QIDs are rejected before network.
6. controlled discovery parses exact QIDs deterministically.
7. duplicate identical QIDs are handled deterministically without inventing identity merges.
8. HTTP 429 / Retry-After yields explicit throttled/non-success result and no busy retry loop.
9. timeout/5xx/malformed JSON are explicit acquisition failures.
10. manufacturer/designer statements remain source observations; no Brand/Organization role inference is made automatically.
11. LOA vs LWL are distinguished only from explicit qualifier semantics.
12. draft vs unrelated height is not conflated.
13. displacement vs ballast are distinguished only from explicit qualifier semantics.
14. missing qualifier/unsupported qualifier is retained/routed unsupported rather than guessed.
15. raw Wikidata quantity/unit survives separately from normalized candidate.
16. SLICE-0004 normalization is reused for supported quantity units.
17. generated FieldEvidence carries source/QID/property locator and immutable raw observation.
18. no FieldResolution/canonical BoatModel/BoatDesign write occurs.
19. quality report counts requested/fetched/present/unsupported deterministically.
20. normal test suite performs no live network access.
21. optional live smoke is explicitly opt-in and bounded.
22. private boat-list content is absent from fixtures and repository changes.

## Explicitly out of scope

Do not implement:

- full Wikidata dump ingestion;
- unbounded WDQS crawling;
- Wikipedia text/infobox ingestion;
- mixed Wikimedia-derived third-party datasets;
- manufacturer website crawling;
- ORC ingestion;
- source-authority ranking;
- fuzzy identity resolution;
- automatic Brand/Organization merging;
- canonical FieldResolution policy;
- canonical BoatModel/BoatDesign persistence;
- PostgreSQL/SQLite persistence;
- keel/rudder/skeg/configuration normalization (SLICE-0009);
- derived metrics (SLICE-0010);
- FastAPI/frontend/query engine;
- background scheduler/worker orchestration;
- broad production ingestion;
- private reference boat-list rows.

## Expected touch points

Prefer a small bounded structure such as:

- `src/hullq/sources/wikidata.py`;
- `src/hullq/research/` only where a small adapter result/report type belongs;
- one reviewed Wikidata Source fixture/record under `fixtures/sources/`;
- focused offline tests under `tests/unit/` and `tests/contract/`;
- optional explicit opt-in integration smoke test;
- this slice document + index handoff update.

Do not introduce a generic plugin framework or persistence layer.

## Acceptance criteria

- [ ] Wikidata access is represented by a schema-valid reviewed Source record.
- [ ] every network request is preceded by an ALLOWED automated-ingestion rights decision.
- [ ] adapter sends a descriptive configured User-Agent/contact and has bounded request behavior.
- [ ] direct sailboat-class discovery is bounded and reproducible.
- [ ] entity acquisition preserves QIDs, statement semantics and relevant qualifiers.
- [ ] minimal field extraction is qualifier-aware and does not invent missing semantics.
- [ ] raw observation and normalized candidate remain separate.
- [ ] SLICE-0004 normalization and SLICE-0006 evidence primitives are reused rather than duplicated.
- [ ] no canonical resolution/write, broad ingestion or appendage normalization is introduced.
- [ ] deterministic quality/coverage metrics are produced for the controlled sample.
- [ ] normal CI remains offline and deterministic; any live smoke is explicit opt-in only.
- [ ] repository validator, formatting, Ruff, strict mypy, pytest branch coverage >=90% and dependency audit pass.
- [ ] required remote CI is independently observed before owner acceptance.

## Claude stop conditions

Stop and report rather than broadening scope if:

- the reviewed Wikidata Source record cannot legitimately reach `ALLOWED` for the concrete automated access method under SLICE-0007;
- official endpoint behavior materially conflicts with the prepared access assumptions;
- WDQS requires a broader crawler/retry/orchestration system to be usable;
- a Wikidata field cannot be mapped without inventing semantic rules;
- implementation would require canonical identity resolution, persistence, appendage taxonomy or broad ingestion;
- external terms/access policy appear materially changed from the reviewed record.

## Implementation-agent handoff

When implementation is complete:

1. run all required local gates;
2. push the same `slice/0008-wikidata-rights-gated-adapter` branch;
3. leave SLICE-0008 in `REVIEW` or `BLOCKED`;
4. report exact head SHA and local results truthfully;
5. report whether the optional real network smoke was executed and, if so, its bounded parameters/results;
6. do not merge to `main`;
7. do not start SLICE-0009.

---

## Completion Report

### Slice

- Slice ID: `SLICE-0008`
- Recommended slice state: `REVIEW`
- Scope completed: `YES`
- **Amendment:** PR #19 review findings addressed (see Review Amendment below)

### Changes

- Changed files:
  - `docs/slices/SLICE-0008-wikidata-rights-gated-adapter.md` — status IN_PROGRESS → REVIEW; completion report appended
  - `docs/slices/INDEX.md` — SLICE-0008 status READY → REVIEW; execution rule updated
  - `docs/PROJECT_STATE.md` — stage updated to 2.7 REVIEW; operational position section updated
- New files:
  - `fixtures/sources/wikidata_source.json` — reviewed Wikidata Source record, CC0-1.0, all clearances allowed, schema-valid against `SOURCE_SCHEMA.v0.2.json`
  - `src/hullq/sources/wikidata.py` — complete Wikidata CC0 rights-gated adapter (403 statements)
  - `tests/unit/test_wikidata_adapter.py` — 70 offline unit tests covering scenarios 2–22
  - `tests/contract/test_wikidata_source_record.py` — 17 contract tests covering scenario 1
  - `tests/integration/conftest.py` — `--run-live` pytest option for opt-in live smoke
  - `tests/integration/test_wikidata_live.py` — 2 opt-in live smoke tests (skipped in normal CI)
- Requirements implemented: all in-scope behaviors from sections 1–8 of the slice

### Validation

- Local validation: `PASS`
- Commands run:
  ```
  uv run ruff check src/ tests/
  uv run ruff format --check src/ tests/
  uv run mypy src/hullq/sources/wikidata.py tests/unit/test_wikidata_adapter.py tests/contract/test_wikidata_source_record.py tests/integration/test_wikidata_live.py tests/integration/conftest.py
  uv run coverage run -m pytest tests/unit/ tests/contract/ -q
  uv run coverage report
  uv run pip-audit
  ```
- Results:
  - ruff check: `All checks passed!`
  - ruff format: `30 files already formatted`
  - mypy (new SLICE-0008 files): `Success: no issues found in 5 source files`
  - pytest: `567 passed in 22.04s`
  - coverage total: `90.13%` (≥90% required; `wikidata.py` alone is 81.62% — the requirement is the overall suite threshold)
  - pip-audit: `No known vulnerabilities found`

### External verification

- Remote CI: `NOT VERIFIED` — branch pushed to GitHub; GitHub Actions results were not observed during this session
- Other external gates: `NOT APPLICABLE`

### Findings

- Unresolved findings: none
- Spec/ADR ambiguities: none
- Scope deviations: none
- Live network smoke: NOT executed — the opt-in smoke tests exist and are bounded (`_LIVE_DISCOVERY_LIMIT = 5`) but were not run in this session; they are skipped by default in CI and require `--run-live`
- Pre-existing mypy errors in non-SLICE-0008 files (`test_source_rights_fixtures.py`, `test_provenance.py`, `test_measurements.py`, `test_identity.py`, `test_identity_contracts.py`) were not introduced by this slice and were not modified

### Follow-up

- Recommended next action: independent review of the PR on branch `slice/0008-wikidata-rights-gated-adapter`; if all acceptance criteria are verified including remote CI, project-owner may mark `DONE` and start `FINISH_SLICE.bat`

### Agent declaration

- No work outside the assigned slice was started.
- No unverified acceptance criterion was marked as passed.
- The next slice (SLICE-0009) was not started automatically.
- The agent has NOT marked this slice `DONE`.

---

## Review Amendment (PR #19 findings)

**HEAD after amendment:** `b277714c…` (pushed to `slice/0008-wikidata-rights-gated-adapter`)

### Finding 1 resolved — requested_qid_count is now independent of fetched count

`extract_field_evidence()` now requires an explicit `requested_qid_count: int` keyword argument (the distinct QID count after deduplication, as submitted to `fetch_entities`). This is tracked in `run_controlled_probe()` before the API call so partial-return cases (absent or non-item entities) are correctly represented in the quality report. 5 new tests added covering all required scenarios.

Semantic choice documented: `requested_qid_count` counts post-deduplication distinct QIDs submitted to the Wikidata API. Duplicate handling is deterministic (exact-QID identity, not fuzzy).

### Finding 2 resolved — User-Agent requires HullQ identity + contact identifier

`WikidataAdapterConfig.__post_init__` now validates:
1. `"hullq"` present in user_agent (case-insensitive) — project identifier;
2. a contact identifier present — email address pattern (`user@domain.tld`) or URL (`http://…` or `https://…`).

Existing item_limit/timeout tests that used bare `"HullQ/0.1"` updated to use valid contact-bearing strings. 7 new tests added (4 negative, 3 positive including case-insensitive check).

### Finding 3 resolved — P642 qualifier identity preserved in raw observation

`_build_quantity_evidence()` now accepts `qualifier_qid: str | None` keyword argument. When supplied (by `_process_qualified_quantity` passing the matched qualifier), the `RawObservation.value` dict includes:
- `"qualifier_property": "P642"` — the qualifier property;
- `"qualifier_value_id": "<qual_QID>"` — the matched qualifier value (e.g., `"Q2358152"` for LOA).

Unqualified fields (beam, number_built) receive no qualifier keys. Unsupported qualifiers continue to route to `unsupported_qualifier_count` without producing evidence. 8 new tests added.

### Validation after amendment

- ruff check: clean
- ruff format: clean
- mypy (SLICE-0008 files): clean
- pytest: **587 passed** (20 new tests from review fixes)
- branch coverage: **90.99%** (≥90% required)
- pip-audit: no known vulnerabilities
- Remote CI (PR #19): **NOT VERIFIED** — branch pushed; GitHub Actions result not yet observed
- Live smoke: not executed

---

## Review Amendment 2 (PR #19 findings 4–6)

**HEAD after amendment:** `c460493` (pushed to `slice/0008-wikidata-rights-gated-adapter`)

### Finding 4 resolved — Cross-dimension normalization prevented

`_build_quantity_evidence()` now accepts `expected_quantity: Quantity | None = None`. When a recognized unit resolves to a different physical dimension than expected (e.g., kg on a length field), normalization is skipped: the raw observation is still preserved but no `NormalizedCandidate` is produced.

`_process_unqualified_quantity` and `_process_qualified_quantity` forward `expected_quantity` to `_build_quantity_evidence`. `_extract_entity_evidence` passes `expected_quantity=Quantity.LENGTH` for P2043/P2048/P2049 and `expected_quantity=Quantity.MASS` for P2067.

New `_process_count_quantity` method handles P1092 (total produced): only the dimensionless sentinel unit "1" is accepted; any recognized dimensional unit (kg, m, …) increments `unsupported_qualifier_count` without producing evidence or a malformed count. `test_total_produced_evidence_from_p1092` corrected (kg unit now correctly yields unsupported). 11 new dimension-check tests added.

### Finding 5 resolved — Language fallback is real at the API boundary

`fetch_entities` now sends `languages=lang|en` when `config.language` is non-English, and `languages=en` when it is English (avoiding `en|en`). `_parse_entity` alias fallback changed to `aliases_raw.get(lang, []) or aliases_raw.get("en", [])` so that when the preferred language has no aliases, English aliases are used. 5 new offline tests cover both the API parameter and the alias-fallback behaviour.

### Finding 6 resolved — Live smoke uses real contact path

`test_wikidata_live.py` `_LIVE_USER_AGENT` updated to use `https://github.com/StradaDelSole/HullQ` as the contact path. The unit test `test_user_agent_with_hullq_and_email_is_accepted` now uses `contact@example.invalid` instead of a real email address.

### Validation after amendment 2

- ruff check: clean
- ruff format: clean
- mypy (SLICE-0008 files, strict): clean
- pytest: **602 passed** (15 new tests from review fixes 4–6)
- branch coverage total: **90.59%** (≥90% required)
- pip-audit: no known vulnerabilities
- Remote CI (PR #19): **NOT VERIFIED** — branch pushed to `c460493`; GitHub Actions result not yet observed
- Live smoke: not executed

---

## Review Amendment 3 (PR #19 blockers 4A and 4B)

**HEAD after amendment:** `96ad4de` (pushed to `slice/0008-wikidata-rights-gated-adapter`)

### Blocker 4A resolved — Cross-dimension evidence eliminated entirely

A recognised Wikidata unit of the wrong physical dimension no longer produces any `FieldEvidence` for the incompatible HullQ field.

New module-level helper `_claim_unit_qid(claim)` extracts the unit QID from a claim without constructing evidence.

`_process_unqualified_quantity`: when `expected_quantity` is set and the claim's unit resolves to a recognised QID of the wrong dimension, `unsupported_qualifier_count` is incremented and no evidence is created. Unrecognised/unknown units are not rejected — they pass through to `_build_quantity_evidence` as before (raw evidence, no normalization), preserving the existing unknown-unit contract.

`_process_qualified_quantity`: same pre-check applied inside the qualifier-match block before calling `_build_quantity_evidence`.

`_build_quantity_evidence` retains its normalization guard as defense in depth but is no longer the primary routing control for cross-dimension statements.

### Blocker 4B resolved — P1092 strictly requires dimensionless sentinel

`_process_count_quantity` now uses `_claim_unit_qid(claim)` to determine the unit. If any Wikidata entity QID is returned — whether recognised (kg, m, metric tonne, …) or unknown (Q999999, …) — `unsupported_qualifier_count` is incremented and no evidence is produced. Only claims where the unit URI does not resolve to a QID (the literal API sentinel `"1"` or a non-QID URL) produce count `FieldEvidence`. This closes the gap where an unknown unit QID could previously slip through as evidence.

### Test changes

- `test_kg_unit_on_length_field_produces_no_normalized_candidate` → renamed `test_kg_unit_on_length_field_produces_no_field_evidence`; asserts `len(beam_ev) == 0` and `unsupported == 1`.
- `test_kg_unit_on_length_field_preserves_raw_observation` → repurposed as `test_unknown_unit_on_length_field_still_produces_raw_evidence`; explicitly verifies that unrecognised units (Q999999) still produce raw evidence without incrementing unsupported.
- `test_metre_unit_on_mass_field_produces_no_normalized_candidate` → renamed `…_no_field_evidence`; asserts zero displacement evidence + unsupported count = 1.
- `test_kg_on_loa_field_produces_no_normalized_candidate` → renamed `…_no_field_evidence`; asserts zero LOA evidence + unsupported count = 1.
- `test_metre_on_ballast_field_produces_no_normalized_candidate` → renamed `…_no_field_evidence`; asserts zero ballast evidence + unsupported count = 1.
- New `test_p1092_with_literal_sentinel_unit_produces_evidence`: builds claim with `unit="1"` (literal Wikidata API form) and asserts evidence produced with no normalization.
- New `test_p1092_with_unknown_qid_unit_is_unsupported`: Q999999 → zero evidence, unsupported count = 1.

### Validation after amendment 3

- ruff check: clean
- ruff format: clean
- mypy (SLICE-0008 files, strict): clean
- pytest: **604 passed** (2 new tests, 5 renamed/rewritten)
- branch coverage total: **90.63%** (≥90% required)
- pip-audit: no known vulnerabilities
- Remote CI (PR #19): **NOT VERIFIED** — branch pushed to `96ad4de`; GitHub Actions result not yet observed
- Live smoke: not executed

---

## Review Amendment 4 (final blocker 4B — literal sentinel enforcement)

**HEAD after amendment:** `12afd0e` (pushed to `slice/0008-wikidata-rights-gated-adapter`)

### Implementation

New module-level helper `_get_claim_raw_unit(claim)` returns the raw `unit` string exactly as it appears in the Wikidata API response, or `None` for absent/non-string unit. This is explicitly distinct from `_claim_unit_qid()`, which returns `None` for both the sentinel `"1"` and for non-QID URLs — making those two cases indistinguishable.

`_process_count_quantity` now uses `_get_claim_raw_unit()` for an explicit three-way dispatch:

- `unit == "1"` → raw count `FieldEvidence` (no `NormalizedCandidate`)
- `unit` is any other string → `unsupported_qualifier_count += 1`, zero evidence
- `unit` absent or non-string → `malformed_count += 1`, zero evidence

The docstring names the reason `_claim_unit_qid()` is intentionally not used here.

### Test changes

- `test_total_produced_evidence_from_p1092`: the `entity_ok` case now uses a hand-built raw claim with literal `"unit": "1"` instead of the `_quantity_claim` helper (which builds the URL form).
- `test_p1092_with_dimensionless_unit_produces_evidence_without_normalization` → renamed `test_p1092_with_url_form_of_1_is_unsupported`; asserts zero evidence + `unsupported == 1` (the URL form `"http://…/entity/1"` is not the sentinel).
- `test_p1092_with_literal_sentinel_unit_produces_evidence`: unchanged ✓
- `test_p1092_with_unknown_qid_unit_is_unsupported`: unchanged ✓
- New `test_p1092_with_non_qid_url_is_unsupported`: `http://example.com/unit/count` → zero evidence, unsupported increments.
- New `test_p1092_with_missing_unit_is_malformed`: absent `unit` key → zero evidence, malformed increments (not unsupported).

### Validation after amendment 4

- ruff check: clean
- ruff format: clean
- mypy (SLICE-0008 files, strict): clean
- pytest: **606 passed** (2 new tests, 2 renamed/rewritten)
- branch coverage total: **90.42%** (≥90% required)
- pip-audit: no known vulnerabilities
- Remote CI (PR #19): **NOT VERIFIED** — branch pushed to `12afd0e`; GitHub Actions result not yet observed
- Live smoke: not executed
