# SLICE-0024 — Wikimedia Lead Independent Identity-Verification Pilot

**ID:** SLICE-0024  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** 3.2 — canonical identity breadth / independent lead verification economics  
**Depends on:** SLICE-0023 accepted / DONE  
**Blocks:** any full verification/admission campaign over the 409 SLICE-0023 incremental Wikimedia QID leads

## Objective

Determine, on a **fixed deterministic 30-QID sample** from the accepted SLICE-0023 quality sample, whether Wikimedia-discovered leads can be independently verified as in-scope sailboat model/class/design-family identities from sufficiently strong non-Wikipedia sources at a research cost low enough to justify a later full verification campaign.

This is a **verification-source/yield/economics pilot**. It does not admit any identity, mint HullQ IDs, approve production use of Wikipedia/Wikimedia, or begin Stage 3.3 enrichment.

## Why this slice exists

Stage 3.2 targets thousands of Tier-0 identities; current canonical BoatModels remain 1,770. SLICE-0023 found 409 incremental QID research leads and its deterministic 150-QID quality review ended at:

```text
plausible_model_or_class_lead   102  (68.00%)
obvious_out_of_scope             19  (12.67%)
ambiguous                        29  (19.33%)
recommendation  FOLLOWUP_VERIFICATION_CANDIDATE
```

Those tags were based only on retained lead identity + minimal Wikidata context and are not canonical verification. A full 409-candidate manual campaign would be premature and unnecessarily expensive. The next smallest useful step is therefore to measure independent verification yield, source strength and research effort on a deterministic sample before authorizing broader work.

## Controlling artifacts

Read only as needed under the token-efficient workflow.

- `CLAUDE.md`
- `docs/engineering/AI_TOKEN_EFFICIENCY.md`
- `docs/EXECUTION_PLAN.md` — Stage 3.2 before 3.3
- `docs/DATABASE_COVERAGE_STRATEGY.md`
- `research/RESEARCH_WORKFLOW.md`
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`
- `specs/IDENTITY_MODEL.v0.2.md` where identity precision matters
- `specs/REQUIREMENTS.md`: REQ-DATA-007/008, REQ-ID-001/002/008, REQ-RESEARCH-002/004/005/006/007/008/009
- SLICE-0023 primary contract + `docs/slices/SLICE-0023-acceptance-closure.md`
- accepted SLICE-0023 retained package under `research/bootstrap/wikimedia/sl0023-category-leads/`

## Immutable accepted input boundary

Before selecting/researching candidates, fail closed unless all accepted SLICE-0023 boundaries reproduce:

```text
incremental_qid_lead                  409
quality sample                        150
plausible_model_or_class_lead         102
obvious_out_of_scope                   19
ambiguous                              29
canonical BoatModels                1,770
historical QID -> HullQ-ID mappings 1,772
```

Pin and verify these retained Git blobs:

```text
quality_sample.json      e26fde36c487f54344e4392ed7f3d7e735f07abf
discovery_manifest.json  9ddc5483d8b3d34e97aa36d5d72bd28fefe19c0e
source_assessment.json    d025ca31574d38b2bab03fd8211859c10440dd4b
```

Do not refresh, rewrite or rerun SLICE-0023 acquisition to satisfy this slice.

## Fixed deterministic verification sample

Select exactly 30 unique QIDs from the final accepted `quality_sample.json` manual-review strata:

```text
plausible_model_or_class_lead   18
ambiguous                         6
obvious_out_of_scope              6
TOTAL                            30
```

Within each prior-tag stratum:

1. calculate SHA256 over the UTF-8 QID string;
2. sort ascending by the hex digest;
3. take the first N shown above;
4. do not hand-pick, replace or backfill candidates.

The prior SLICE-0023 tag is **sampling/calibration metadata only**. It is not evidence and MUST NOT control the new verification outcome.

Retain each selected QID's SLICE-0023 page title/category memberships and prior tag for audit/calibration.

## External research boundary

The goal is independent verification, not another broad data extraction system.

For each of the 30 candidates:

- maximum **2 web/search discovery queries**;
- maximum **4 distinct source-page evaluations**;
- maximum **6 research actions** total under those two categories;
- stop early once sufficient qualifying evidence determines the research outcome;
- if the budget is exhausted, record `unresolved` and move on.

Global ceilings:

```text
search/discovery queries       <= 60
source-page evaluations        <= 120
combined research actions      <= 180
```

Do not build a search-engine scraper, crawler, recursive site walker or broad source adapter in this slice.

Normal CI and the offline verifier perform **zero external web acquisition**.

## Discovery material vs verification evidence

May be used as discovery/context only, never as qualifying verification evidence:

- the retained SLICE-0023 Wikipedia page title/URL/category membership;
- retained SLICE-0023 Wikidata label/description/properties;
- search-engine result pages/snippets;
- Wikipedia article text/infobox/tables/references;
- SailboatData/reference scrape or live SailboatData pages;
- generative summaries;
- forum/social/marketplace/listing content.

A discovery source may lead to a qualifying external source, but its own claims do not verify the candidate.

## Qualifying source hierarchy

Use the accepted `research/RESEARCH_WORKFLOW.md` hierarchy.

### Strong source classes

One accessible source in any of these classes may constitute strong identity evidence when it directly and unambiguously identifies the candidate subject:

1. manufacturer / shipyard;
2. original manufacturer brochure;
3. owner's / technical manual;
4. designer / naval architect;
5. class association;
6. owners' association;
7. museum / recognized archive.

### Specialist-secondary class

`high_quality_specialist_documentation` is secondary evidence. It can support an independently supported identity only when **two genuinely independent specialist sources** agree. Two mirrors, copies, syndications or sources obviously deriving from the same root do not count as independent.

Other source classes may be recorded as discovery/noise but MUST NOT qualify an identity outcome.

## Research outcome model

For every sampled candidate retain exactly one `subject_outcome`:

- `in_scope_identity`
- `out_of_scope`
- `conflict`
- `unresolved`

and exactly one `evidence_strength`:

- `strong_source`
- `two_independent_specialist_sources`
- `insufficient`

Rules:

### `in_scope_identity`

Use only when qualifying evidence explicitly supports a named sailboat model, production series, racing class or design-family identity potentially relevant to HullQ.

- `strong_source`: at least one strong source directly supports that identity;
- `two_independent_specialist_sources`: no strong source was found within budget, but two independent high-quality specialist sources directly support the same identity.

### `out_of_scope`

Use only when qualifying evidence explicitly supports a non-HullQ subject such as an individual vessel, ferry, military craft, person, organization, event, generic concept, or non-sailing craft.

### `conflict`

Use when qualifying evidence materially disagrees about the subject identity/scope at a level that cannot be resolved within the slice budget.

### `unresolved`

Use when the bounded search finds insufficient qualifying evidence. `unresolved` is not a negative identity fact.

`evidence_strength = insufficient` is mandatory for `conflict` or `unresolved` and whenever the qualifying rules above are not satisfied.

## Minimal retained evidence

For every evaluated external source retain only what is needed for audit:

- candidate QID;
- source URL and domain;
- source class;
- access/review timestamp;
- whether the page was accessible;
- the discrete identity fact(s) used for the research judgment, paraphrased rather than copied as expressive text;
- optional minimal builder/designer/year identity hints only when needed to disambiguate the subject;
- whether the source is independent of another retained source;
- research-reference-only / production-clearance-not-assessed marker.

Do **not** retain article/page copies, images, large quotations, full brochures/manuals, or unrelated technical specifications merely because they are visible.

No external source evaluated here becomes production-cleared merely by appearing in the research package.

## Rights/access behavior

`specs/SOURCE_RIGHTS_POLICY.v0.1.md` controls.

- This slice uses external pages only as bounded research references.
- Do not bypass authentication, paywalls, robots/access controls, rate limits or explicit restrictions.
- If a source cannot be lawfully/ordinarily accessed, record that and move on.
- Do not infer production-value, bulk-bootstrap or automated-ingestion clearance.
- Do not add source-specific production clearances or build production adapters.
- Store minimal citation/provenance metadata; avoid vendoring third-party content.

If the bounded research method itself cannot be performed consistently with accepted rights/access policy, stop `BLOCKED`.

## Required metrics

Recompute and retain at minimum:

- sample counts by prior SLICE-0023 tag;
- `subject_outcome` counts overall and by prior tag;
- `evidence_strength` counts overall and by prior tag;
- independently supported in-scope count (`strong_source` + `two_independent_specialist_sources`);
- strong-source in-scope count;
- prior-tag agreement/disagreement matrix;
- source-class counts;
- search-query count;
- source-page-evaluation count;
- combined research-action count;
- per-candidate research-action count;
- median combined research actions among independently supported in-scope candidates;
- count hitting the per-candidate research budget;
- access-blocked source-page count;
- conflicts/unresolved count.

Do not interpret prior SLICE-0023 tags as ground truth when computing agreement/disagreement.

## Precommitted recommendation rule

Give exactly one research-only recommendation, in this order:

1. if accepted rights/access boundaries were violated or cannot be truthfully retained -> `RIGHTS_OR_ACCESS_BLOCKED`;
2. else consider only the **24 candidates from the prior plausible + ambiguous strata**; if fewer than **12** are independently supported `in_scope_identity` -> `LOW_INDEPENDENT_VERIFICATION_YIELD`;
3. else if fewer than **8** of those 24 are `in_scope_identity` with `strong_source` -> `STRONG_SOURCE_COVERAGE_TOO_WEAK`;
4. else if the median combined research actions per independently supported in-scope candidate is greater than **4**, or any research-action ceiling was exceeded -> `TOO_EXPENSIVE_FOR_FULL_CAMPAIGN`;
5. otherwise -> `FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE`.

The six prior `obvious_out_of_scope` candidates are calibration/negative-control cases and do not enter the yield threshold.

Any recommendation remains research-only. Even `FULL_409_VERIFICATION_CAMPAIGN_CANDIDATE` does not authorize canonical admission or the next slice.

## Required retained package

Create an isolated package, preferably:

```text
research/bootstrap/wikimedia/sl0024-independent-verification/
    verification_sample_schema.json
    verification_sample.json
    verification_results_schema.json
    verification_results.json
    REPORT.md
    ARTIFACT-DIGESTS.schema.json
    ARTIFACT-DIGESTS.json
```

A small pure helper/runner may be added for deterministic sample selection, metrics/recommendation assembly and offline verification. **Do not automate external web search/browsing in repository code.**

## Offline verification

Provide a strict offline verifier that independently recomputes/fails closed on at least:

- pinned SLICE-0023 blob/count boundaries;
- exact deterministic 18/6/6 sample selection;
- QID uniqueness and exact prior-tag membership;
- allowed outcome/evidence/source-class vocabulary;
- evidence-strength rule consistency;
- two-specialist independence requirement;
- per-candidate and global research-action ceilings;
- all required aggregate metrics and prior-tag matrix;
- precommitted recommendation;
- artifact digests.

The verifier need not reproduce subjective web-page interpretation from scratch. Independent review must inspect the retained manual judgments/evidence citations for defensibility.

Tamper tests must reject at minimum changed sample membership/prior tags, duplicated QIDs, invalid source classes, evidence-strength/outcome inconsistencies, fake two-source independence, action-count/cap manipulation, aggregate-metric drift, recommendation drift and artifact-digest tampering.

## No canonical / production mutation

SLICE-0024 MUST NOT:

- create/modify/delete canonical Brand, Organization, BoatModel or BoatDesign rows;
- mint HullQ IDs;
- alter the accepted 1,772-entry historical crosswalk;
- auto-admit any of the 409 Wikimedia leads;
- change production Wikidata discovery;
- add Wikipedia/Wikimedia to production discovery;
- promote Wikipedia content to canonical evidence;
- grant production/bulk/automation clearance to newly evaluated external sources;
- ingest technical fields beyond minimal identity-disambiguation research notes;
- begin Tier-1/Tier-2 / Stage-3.3 enrichment;
- begin OQ-009/query-engine/API/frontend/SEO implementation;
- create/start SLICE-0025.

## Expected touch points

Expected only where needed:

- `research/bootstrap/wikimedia/sl0024-independent-verification/`
- a small `src/hullq/bootstrap/` pure helper for sample/metric verification
- a small `scripts/bootstrap/` assemble/verify runner
- focused unit/contract tests
- SLICE-0024 status handoff + compact operational state update

Do not modify unrelated product/domain semantics.

## Validation

At handoff run the repository's normal required validation once, including:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Run the SLICE-0024 offline verifier explicitly. Normal CI must use zero external research requests and remote CI must be observed on the exact final branch HEAD before claiming it passed.

## Acceptance criteria

- [ ] Accepted SLICE-0023 pins/counts reproduce exactly before work begins.
- [ ] Deterministic sample is exactly 18 plausible + 6 ambiguous + 6 prior out-of-scope QIDs with no hand-picking/backfill.
- [ ] All 30 candidates receive a bounded research result without exceeding per-candidate/global action ceilings.
- [ ] Search/Wikipedia/Wikidata/SailboatData/discovery material is never treated as qualifying verification evidence.
- [ ] Qualifying evidence follows the fixed strong/specialist hierarchy and retained judgments are minimally auditable.
- [ ] Required yield/source/effort/calibration metrics are retained and mechanically recomputed.
- [ ] Exactly one recommendation is derived from the precommitted rule.
- [ ] Strict offline verification and tamper tests pass.
- [ ] Zero canonical/production mutation and zero new production source clearance occurred.
- [ ] Repository validator, formatting, lint, mypy, tests and coverage gate pass.
- [ ] Exact-head GitHub CI and required reproducibility workflow are observed SUCCESS.
- [ ] Slice is handed off as `REVIEW`, not `DONE`; SLICE-0025 is not created/started.

## Stop conditions

Stop `BLOCKED` rather than improvising if:

- any pinned SLICE-0023 input/count does not reproduce;
- deterministic sample cannot be reproduced exactly;
- external research would require bypassing access/rights restrictions;
- the research budget/ceiling model cannot be measured truthfully;
- accepted identity/source-rights semantics conflict materially;
- completing the objective would require canonical writes, Stage-3.3 work, or another slice.

## Status handoff rule

Successful completion hands SLICE-0024 to `REVIEW`. The agent MUST NOT mark it `DONE`, merge it, infer owner acceptance, or start SLICE-0025.

Use the concise mandatory completion-report structure from `docs/slices/SLICE_TEMPLATE.md`. In addition report only these slice-specific deltas: final 30-sample composition, outcome/evidence-strength totals, supported/strong in-scope counts for the 24 threshold candidates, source-class distribution, research-action totals/median, final recommendation, exact retained-package path, exact final HEAD and exact-head CI IDs.
