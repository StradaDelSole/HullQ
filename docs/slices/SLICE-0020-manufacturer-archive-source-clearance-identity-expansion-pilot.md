# SLICE-0020 — Manufacturer Archive Source Clearance & Identity-Expansion Pilot

**ID:** SLICE-0020
**Type:** DESIGN_RESEARCH
**Status:** READY
**Stage:** 3.3 — post-manufacturer-universe source clearance / bounded identity-yield pilot
**Depends on:** SLICE-0019 accepted / DONE
**Blocks:** any later controlled manufacturer-archive identity-expansion adapter slice (not yet authorized; a later slice must use this pilot's measured result as evidence)

## Objective

Determine, with retained evidence and no invented clearance, **which of a fixed sample of manufacturer/heritage archive surfaces are actually eligible for a later production adapter slice**, and measure — through a small bounded research-only pilot — what identity yield and overlap characteristics those surfaces show against the accepted SLICE-0017/0018 Tier-0 BoatModel universe.

This is a **source-clearance and identity-yield research slice**. It does **not** build, authorize or stage a production scraper/adapter, does not perform automated/bulk acquisition, and does not create or modify any canonical Brand, Organization, BoatModel or BoatDesign row.

## Why this slice exists

SLICE-0019 measured that manufacturer/heritage archives are the strongest evidenced route beyond the accepted 1,770 sparse canonical BoatModels / 1,829 direct-instance Wikidata ceiling (`docs/slices/SLICE-0019-acceptance-closure.md`; `research/manufacturers/REPORT.md`, "Recommendation for the next bounded slice", option 1: controlled manufacturer-archive identity expansion). That same report also recorded that rights/access confidence for automated commercial reuse of those archive surfaces is only **medium at best**, and typically **REQUIRES_REVIEW**, pending source-specific terms/licence review.

`specs/SOURCE_RIGHTS_POLICY.v0.1.md` (SR-002, SR-003) and the SLICE-0007 rights gate (`src/hullq/sources/rights.py`) already require **use-specific, fail-closed clearance** before any source may be used for production values, bulk bootstrap or automated ingestion. Public readability of an archive page is not, by itself, evidence of any of those clearances.

HullQ therefore needs a bounded, evidence-first slice that:

1. actually assesses rights/access for a fixed, representative sample of the highest-yield archive surfaces named by SLICE-0019, using HullQ's existing use-specific clearance vocabulary; and
2. runs a strictly bounded, research-only identity-yield pilot against those same surfaces to measure real overlap/novelty characteristics,

before any later slice is allowed to propose an actual production adapter.

## Core semantic rules

1. **Access is not reuse.** Public/manual readability, robots/API/automation posture and copyright/licence/database reuse rights are recorded and judged **separately**, exactly as required by `SOURCE_RIGHTS_POLICY.v0.1` SR-001 and the SLICE-0007 gate.
2. **Clearance is use-specific.** Each source gets an independent judgment for each relevant use in the accepted vocabulary: `research_reference`, `research_lead`, `identity_seed`, `production_value` (where relevant), `automated_ingestion`, `bulk_bootstrap`, `artifact_redistribution`. A source being fine for `research_reference` does not imply anything about `bulk_bootstrap` or `automated_ingestion`.
3. **Fail closed.** Absent, thin or ambiguous evidence for any use MUST be recorded as `unknown` / `REQUIRES_REVIEW`, never rounded up to an allowed/cleared state. This mirrors SLICE-0007's fail-closed gate semantics for `unknown`/`unassessed`/unresolved-`conditional` states.
4. **No invented legal clearance.** This slice records engineering-grade rights/access evidence and a conservative use-specific judgment. It is **not** legal advice and MUST NOT be presented as a legal determination or as a substitute for the source-specific review SLICE-0019 already flagged as outstanding.
5. **Public readability alone never implies systematic-use permission.** A page being viewable in a browser without login is `public_access` evidence only; it says nothing about `automated_ingestion` or `bulk_bootstrap`.
6. **Identity hazards stay explicit, never silently resolved.** Reused model numbers/names across manufacturers or across a manufacturer's own history, generation/lineage ambiguity and brand-vs-yard relationships (the same hazards SLICE-0019 already documented) remain open review hazards. They are never force-collapsed to produce a cleaner-looking overlap number.
7. **No subjective suitability labels.** No `bluewater` / `offshore` / `luxury` or comparable marketing/suitability classification may be introduced anywhere in this slice's outputs, consistent with the SLICE-0019 exclusion.

## Precommitted fixed source sample

Assess exactly this fixed sample of ten manufacturer/yard archive surfaces:

1. Catalina Yachts
2. Pearson Yachts
3. Oyster Yachts
4. Westerly Marine
5. Bénéteau
6. Wauquiez
7. Elan
8. Cantiere del Pardo / Grand Soleil
9. Hallberg-Rassy
10. Seawind Catamarans

This list is fixed for the slice. A named target may be substituted **only** if repository evidence (e.g. an existing SLICE-0019 registry record showing the entity is not eligible, defunct with no recoverable archive, or otherwise unusable) proves the named source is unavailable, and the substitution and its justification are explicitly documented in the retained report. Substitution is not permitted merely because a source looks harder to assess.

Where a target from this list already has a SLICE-0019 `research/manufacturers/registry.json` record, that record MAY be used as background/cross-check context but does not itself satisfy this slice's rights/access or identity-pilot requirements — SLICE-0019 did not perform this slice's use-specific clearance assessment or bounded per-source identity pilot.

## Required rights/access research per source

For **each** of the ten (or explicitly justified substitute) sources, retain:

- the exact target archive/index/model-heritage surface(s) assessed (URL(s));
- access/public-readability evidence (public / registration-required / paywalled / unknown, plus supporting note);
- terms-of-service / licence evidence where identifiable (or explicitly `unknown` if none was found);
- robots.txt / API / automation-relevant evidence where applicable (or explicitly `unknown`/`not_applicable`);
- review date;
- evidence URL(s) supporting each claim above;
- a **use-specific decision** for each of the seven accepted HullQ source-use keys (`research_reference`, `research_lead`, `identity_seed`, `production_value` where relevant, `automated_ingestion`, `bulk_bootstrap`, `artifact_redistribution`), using the accepted clearance vocabulary from `SOURCE_RIGHTS_POLICY.v0.1` §5 (`allowed`, `conditional`, `legal_review_required`, `prohibited`, `unknown`);
- an overall `systematic_use_status` classification for the surface using the SLICE-0019 vocabulary (`CLEARED`, `REQUIRES_REVIEW`, `BLOCKED`, `UNKNOWN`), which MUST NOT be set to `CLEARED` merely because a page is publicly viewable.

Access/automation evidence and reuse/rights evidence MUST be recorded as visibly separate fields, not merged into one combined judgment, so that a later reviewer can see exactly which half of the assessment (technical access vs legal reuse) is the actual blocker for any non-cleared use.

## Bounded identity-yield pilot

This is a **research-only measurement**, not production ingestion, and does not read, resolve or write any canonical HullQ table.

For each of the ten sources:

- retain **at most 20** representative model identities discoverable on that source's archive/index surface (a hard per-source cap; do not exceed it even if the surface lists more);
- for each retained model identity, keep only: model name (as the source presents it), the source surface it was found on, and the **minimum** additional factual context needed to discriminate identity (e.g. approximate production era, hull type, or an explicit model-number/generation marker actually present on the source) — do not harvest broader technical specifications;
- run **exact/unambiguous-first overlap only** against the accepted SLICE-0017/0018 union of 1,770 AUTO_ADMIT BoatModels: a match counts only when the retained model name matches an accepted preferred label or an already-recorded alias exactly (case-insensitive exact match is acceptable; nothing fuzzier);
- do **not** perform fuzzy matching, manufacturer-name-prefix stripping, token reordering, or any other normalization that would manufacture a match the exact string comparison does not support;
- do **not** silently collapse reused model numbers/names, generations, or ambiguous brand-vs-yard production relationships to force a cleaner-looking match or non-match — record them as explicit review hazards instead;
- report, per source and in total: identities retained, exact overlaps found, clearly-new candidates, and unresolved-possible-overlap cases requiring later identity resolution (mirroring the SLICE-0019 overlap-reporting categories).

At most 200 model identities are retained across the whole pilot (10 sources × 20 cap). This pilot does not attempt to be exhaustive for any source.

## Required retained outputs

Create a dedicated retained package, for example under `research/manufacturers/archive_clearance/`:

```text
research/manufacturers/archive_clearance/
    archive_source_clearance_schema.json
    archive_source_clearance.json
    archive_identity_pilot.json
    ARCHIVE_SOURCE_CLEARANCE_REPORT.md
```

The exact filenames/directory MAY be adjusted if repository schema/registry conventions (e.g. the `research/manufacturers/registry_schema.json` pattern) support a clearer structure, provided the four required categories of content (clearance schema, clearance results, identity-pilot results, human-readable report) are all present and separately validatable. A small additional identity-pilot schema file is allowed if it materially improves validation rigor. Do not place new files inside or overwrite any existing SLICE-0019 retained artifact (`research/manufacturers/registry.json`, `registry_schema.json`, `source_yield_study.json`, `REPORT.md`, etc.) — those remain the accepted SLICE-0019 closure record and MUST NOT change.

### `archive_source_clearance_schema.json` / `archive_source_clearance.json`

A strict schema and matching data file recording, per assessed source, the fields listed under "Required rights/access research per source" above. Follow the `research/manufacturers/registry_schema.json` pattern (draft 2020-12 JSON Schema, `additionalProperties: false`, explicit enums for status/vocabulary fields) for consistency.

### `archive_identity_pilot.json`

Per-source retained model-identity records (name, source surface, minimal discriminating context) plus the overlap classification for each, and an aggregate summary block (totals retained / exact overlap / clearly new / unresolved-possible-overlap), consistent with the bounded pilot rules above.

### `ARCHIVE_SOURCE_CLEARANCE_REPORT.md`

Must summarize at least:

- methodology (how each source was assessed, what counts as evidence);
- the ten (or justified-substitute) sources and, for each, its access evidence, rights evidence and use-specific clearance decisions;
- the resulting classification of each source into `ADAPTER_READY`, `RESEARCH_ONLY` / `REVIEW_REQUIRED`, or `BLOCKED`;
- the bounded identity-pilot results (per source and aggregate);
- identity hazards observed (reused names/numbers, generation ambiguity, brand-vs-yard relationships) and which sources they affect;
- an explicit statement of how many sources (possibly zero) are `ADAPTER_READY`, without padding or manufacturing clearance to avoid a zero result;
- a bounded, evidence-derived recommendation for the next slice, which may only recommend building a production adapter over sources whose `identity_seed` + `automated_ingestion` + relevant `bulk_bootstrap`/volume conditions are demonstrably compatible with `SOURCE_RIGHTS_POLICY.v0.1`; the recommendation must not start that next slice.

## Classification vocabulary

Each assessed source resolves to exactly one of:

- **`ADAPTER_READY`** — `identity_seed` (and, if applicable to the recommended next use, `automated_ingestion`/`bulk_bootstrap`) are `allowed` with retained supporting evidence, and no independently relevant access/permission field contradicts that clearance.
- **`RESEARCH_ONLY` / `REVIEW_REQUIRED`** — usable for `research_reference`/`research_lead`/bounded discovery, but `identity_seed`, `automated_ingestion` or `bulk_bootstrap` remain `conditional`, `legal_review_required`, or otherwise not demonstrably cleared.
- **`BLOCKED`** — an explicit `prohibited` clearance, or an access/automation prohibition, blocks the relevant use outright.

A truthful result of **zero `ADAPTER_READY` sources is a fully valid, acceptable outcome** of this slice. This slice imposes no minimum-cleared-source acceptance floor, and the agent MUST NOT manufacture or round up clearance to avoid reporting that outcome.

## Explicitly out of scope

This slice does **not** authorize:

- any automated fetch, scrape, crawl or bulk request against any assessed source;
- building, staging or testing a production adapter for any of these sources;
- broad Tier-1/Tier-2 technical-field enrichment;
- resolving or remapping the SLICE-0017/0018 review queues;
- canonical Brand/Organization/BoatModel/BoatDesign creation, mutation or admission of any kind;
- treating SailboatData as production evidence anywhere in this slice's outputs;
- subjective `bluewater`/offshore/luxury suitability classification;
- modifying `research/manufacturers/registry.json`, `registry_schema.json`, `source_yield_study.json`, `overlap_result.json` or `REPORT.md` (the accepted SLICE-0019 closure artifacts);
- query-engine/API/frontend/marketplace/accounts/alerts/monitoring/price-history work;
- automatically starting or creating SLICE-0021.

## Acceptance criteria

- [ ] all 10 fixed targets are assessed, or an unavailable target is explicitly substituted with documented repository-evidence justification.
- [ ] rights/access evidence (access status, terms/licence evidence, robots/API/automation evidence, review date, evidence URLs) is retained per target.
- [ ] use-specific clearance decisions use exactly the accepted HullQ vocabulary (`research_reference`, `research_lead`, `identity_seed`, `production_value` where relevant, `automated_ingestion`, `bulk_bootstrap`, `artifact_redistribution`) and clearance states (`allowed`, `conditional`, `legal_review_required`, `prohibited`, `unknown`).
- [ ] access/automation evidence and reuse/rights evidence are recorded and assessed as visibly separate fields, never merged into one judgment.
- [ ] unknown or ambiguous rights fail closed (never rounded up to `allowed`/`CLEARED`).
- [ ] the bounded identity pilot stays within the precommitted cap (<=20 retained model identities per source, <=200 total).
- [ ] overlap measurement against the accepted 1,770 AUTO_ADMIT BoatModel universe uses exact/unambiguous-first matching only — no fuzzy matching, manufacturer-prefix stripping, or silent generation collapsing.
- [ ] reused model numbers/generations and brand-vs-yard relationship hazards are preserved as explicit review notes, not silently resolved.
- [ ] no canonical Brand/Organization/BoatModel/BoatDesign row is created, modified or admitted.
- [ ] no production adapter, automated fetch, or broad automated ingestion is built, staged or executed.
- [ ] no SailboatData value is used as production/identity evidence anywhere in this slice's outputs.
- [ ] no subjective `bluewater`/offshore/luxury suitability classification appears in any retained output.
- [ ] the report's next-slice recommendation is evidence-derived from this slice's own measured results and is explicitly bounded (it does not start that next slice).
- [ ] repository validation/quality gates applicable to retained structured artifacts (schema validation, `scripts/validate_repository.py`, formatting/lint where applicable) pass.
- [ ] the agent hands the slice off in `REVIEW`, `BLOCKED` or `IN_PROGRESS` and never self-marks it `DONE`.
- [ ] SLICE-0021 is not automatically created or started.

An implementation/research agent MUST NOT check any of the above before it has actually been verified.

## Expected touch points

- `research/manufacturers/archive_clearance/` (new directory; see "Required retained outputs") — or an equivalently clear alternative structure under `research/manufacturers/`, provided existing SLICE-0019 artifacts are left untouched;
- `docs/slices/SLICE-0020-manufacturer-archive-source-clearance-identity-expansion-pilot.md` status update at handoff;
- `docs/slices/INDEX.md` handoff update;
- `docs/PROJECT_STATE.md` handoff update if the research materially changes the recommended next step.

Avoid unrelated files. Do not touch runtime/domain/persistence code (`src/hullq/**`), migrations, or any other slice's retained artifacts.

## Validation

```bash
# schema validation for the new retained package (exact invocation depends on the
# final file layout chosen under research/manufacturers/archive_clearance/)
uv run python -c "import json, jsonschema, pathlib; \
  base = pathlib.Path('research/manufacturers/archive_clearance'); \
  schema = json.loads((base / 'archive_source_clearance_schema.json').read_text(encoding='utf-8')); \
  data = json.loads((base / 'archive_source_clearance.json').read_text(encoding='utf-8')); \
  jsonschema.validate(instance=data, schema=schema); \
  print('archive_source_clearance.json validates against archive_source_clearance_schema.json')"

# repository governance validation
uv run python scripts/validate_repository.py

# normal repository quality gates
uv run ruff check src/ tests/
uv run ruff format --check src/ tests/
uv run mypy src/
uv run coverage run -m pytest
uv run coverage report
```

## Stop conditions

Stop and report instead of inventing a solution when:

- a named source's rights/access/terms evidence cannot be found or is materially ambiguous — record it as `unknown`/`REQUIRES_REVIEW`, do not guess;
- a source appears genuinely unavailable and no repository evidence supports a defensible substitute;
- the exact-first overlap check would require fuzzy resolution to produce a result — leave the case as `unresolved_possible_overlap` instead;
- any part of this slice would require touching `src/hullq/**`, persistence, or the accepted SLICE-0017/0018/0019 artifacts.

## Status handoff rule

The implementation/research agent may recommend or set `IN_PROGRESS`, `BLOCKED`, or `REVIEW` as appropriate, but MUST NOT mark this slice `DONE`.

`DONE` requires verified acceptance criteria, required remote/external checks, independent review, and explicit project-owner acceptance as defined in `CLAUDE.md`.

A successful agent completion normally hands the slice off in `REVIEW`.

## Agent execution note

Run this slice through the normal isolated `START_SLICE.bat` / `FINISH_SLICE.bat` worktree workflow once it is accepted as `READY`. Preserve exact source URLs and retrieval/review dates for every rights/access claim. Prefer a truthful, possibly disappointing clearance result over a padded one — a slice that finds zero `ADAPTER_READY` sources has still done its job if the evidence is real and the report says so plainly.

The completion report must state the exact pushed HEAD SHA, changed files, validation/test results, the ten-source clearance classification, the bounded identity-pilot totals (retained / exact overlap / clearly new / unresolved), unresolved findings, and the recommended next bounded slice — without starting it.
