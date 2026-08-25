# SLICE-0023 — Wikimedia Category Identity-Lead Discovery Pilot

**ID:** SLICE-0023  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** 3.2 — canonical identity breadth / alternative research-lead discovery  
**Depends on:** SLICE-0022 accepted / DONE  
**Blocks:** any production use of Wikipedia/Wikimedia category discovery for HullQ identity intake

## Objective

Measure whether a **fixed, bounded English-Wikipedia category-discovery path** can provide a materially useful set of sailboat model/class **research leads** beyond HullQ's accepted Stage-3.2 identity boundaries, while keeping Wikipedia/Wikimedia content strictly outside canonical admission and production-value ingestion.

This slice is a **research-lead yield and noise measurement**, not a Wikipedia production adapter, not a canonical bootstrap expansion, and not Stage-3.3 technical enrichment.

## Why this slice exists

HullQ's accepted Stage-3.2 state after SLICE-0022 is:

```text
retained direct Wikidata discovery candidates      1,829 QIDs
accepted canonical BoatModels                      1,770
retained historical QID -> HullQ-ID mappings       1,772
SLICE-0021 alternative-route leads                     57
SLICE-0022 new canonical admissions                     0
```

SLICE-0018 established that the accepted direct `P31 = sailboat class` Wikidata route currently tops out at 1,829 retained candidates rather than the planned 2,500 window.

SLICE-0020 then showed that a fixed manufacturer/archive sample produced **0 `ADAPTER_READY` sources**, so HullQ cannot responsibly jump straight to systematic manufacturer-archive ingestion.

SLICE-0021 found 57 additional Wikidata alternative-route signals, but SLICE-0022 proved that those broader structured routes are **discovery-authoritative, not admission-authoritative**: final accepted result **0 AUTO_ADMIT / 31 REVIEW_REQUIRED / 26 NOT_ADMITTED**.

The Stage-3 strategy still requires breadth before broad Tier-1 enrichment. `docs/DATABASE_COVERAGE_STRATEGY.md` describes thousands of known canonical identities and a plausible useful-state direction of 5,000+ known designs; Stage 3.3 should therefore not be treated as a substitute for unresolved Stage-3.2 breadth.

A new discovery rationale is required rather than simply changing the Wikidata direct-query limit to 5,000.

English Wikipedia currently exposes broad sailboat-related category surfaces. Readiness research on 2026-08-25 observed approximately:

- `Category:Keelboats`: 1,492 main-category pages;
- `Category:Catamarans`: 121 main-category pages;
- `Category:Trimarans`: 84 main-category pages.

Those category surfaces visibly contain both useful model/class names and obvious noise such as individual vessels, ferries, military craft and generic concepts. That makes them appropriate for a **bounded lead-source measurement**, but not for automatic canonical admission.

## Source-rights and access boundary

`specs/SOURCE_RIGHTS_POLICY.v0.1.md` is controlling.

Its accepted Wikipedia baseline states that Wikipedia/Wikimedia text is **not equivalent to Wikidata CC0** and may be used as research evidence/lead material, while bulk canonical ingestion from Wikipedia text/infobox material remains conditional/legal-review-required until attribution/share-alike implications are explicitly resolved.

For this slice:

- English Wikipedia is used only as a **research lead surface**;
- no Wikipedia prose, infobox values, tables, images, references or expressive article content may become HullQ canonical/provenance values;
- only minimal lead metadata needed to measure discovery is retained: category name, page ID, namespace, page title, canonical page URL and linked Wikidata QID where present;
- source/license/access evidence and attribution URLs must be retained;
- Wikimedia API access must use an informative HullQ User-Agent and respectful serial/batched requests;
- API availability does **not** authorize production/bulk canonical reuse;
- any future production use requires a separate source-rights/architecture decision and slice.

Wikimedia reference material to retain in the source assessment includes at minimum:

- `https://foundation.wikimedia.org/wiki/Terms_of_Use`;
- `https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy`;
- `https://www.mediawiki.org/wiki/API:Categorymembers`;
- `https://www.mediawiki.org/wiki/API:Licensing`.

The slice may use **Wikidata CC0** only for the bounded quality sample described below. Wikidata does not convert the Wikipedia category membership itself into canonical evidence.

## Controlling artifacts

Read and obey at minimum:

- `CLAUDE.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3.1 / 3.2 / 3.3 ordering;
- `docs/DATABASE_COVERAGE_STRATEGY.md`;
- `docs/DATA_STRATEGY.md` where relevant;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- ADR-0005 source-rights decision;
- `docs/slices/SLICE-0017-controlled-wikidata-tier0-identity-bootstrap.md` + closure;
- `docs/slices/SLICE-0018-controlled-wikidata-tier0-2500-window-expansion.md` + closure;
- `docs/slices/SLICE-0021-wikidata-alternative-sailboat-class-discovery-pilot.md` + closure;
- `docs/slices/SLICE-0022-retained-alternative-route-tier0-admission-safety-pilot.md` + R1 governance amendment + closure;
- `research/bootstrap/wikidata/manifest.json`;
- `research/bootstrap/wikidata/sl0018-2500/manifest.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/discovery_probe.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/sampled_candidates.json`;
- accepted HullQ search-key/search-projection semantics from `src/hullq/domain/identity.py`.

## Immutable comparison boundaries

Before live acquisition, verify fail-closed:

```text
accepted direct-discovery candidate universe:    1,829 QIDs
accepted canonical BoatModel universe:           1,770
accepted historical QID -> HullQ-ID mappings:    1,772
accepted SLICE-0021 alternative-route union:         57 QIDs

SLICE-0017 manifest raw SHA256:
076b0d64441973c4d5b71cf467cd9cdbf46242babb9cb44f788c97a0f33e5845

SLICE-0018 manifest raw SHA256:
41ef238c217e31cfbe03329e226a1a3dfff849061df93b8f2523a1e72493821f

SLICE-0021 sampled_candidates.json Git blob:
5b56851f0c719b8dcf830fcd0416471c6c60596c

SLICE-0021 discovery_probe.json Git blob:
16af426991214c445a3c152aacbe56b8088958d6
```

SLICE-0022 created no new canonical identities and must not be reinterpreted as an expanded baseline.

If any accepted hash/count/set boundary does not reproduce, stop `BLOCKED` rather than refreshing or rewriting prior retained evidence.

## Fixed live discovery surfaces

Exactly these three English-Wikipedia category roots are authorized:

```text
Category:Keelboats
Category:Catamarans
Category:Trimarans
```

Use the English Wikipedia MediaWiki Action API only:

```text
https://en.wikipedia.org/w/api.php
```

Category acquisition MUST use `list=categorymembers` with main namespace pages only.

Required behavior:

- `cmnamespace=0`;
- pages only; no files;
- no subcategory recursion;
- no category expansion beyond the three fixed roots;
- follow API continuation only until the complete fixed root is enumerated or the hard cap is reached;
- preserve source ordering/page IDs exactly as returned while also computing deterministic sorted/set views for verification;
- retain request/continuation counts.

Hard caps:

```text
Category:Keelboats     <= 2,000 main-namespace pages
Category:Catamarans    <=   250 main-namespace pages
Category:Trimarans     <=   200 main-namespace pages
combined memberships   <= 2,450 rows before cross-route deduplication
```

If a category exceeds its hard cap, stop that route as `CAP_EXCEEDED` and do not silently truncate it into a complete measurement.

## Page-to-Wikidata mapping

For every acquired Wikipedia page inside the hard caps, use the MediaWiki API's page properties to retain the linked `wikibase_item` QID when present.

Do not parse article body text or infoboxes to infer a QID.

Each unique page/QID lead must be categorized deterministically against accepted retained boundaries:

- `accepted_direct_qid_overlap` — QID belongs to the accepted 1,829 direct-discovery universe;
- `retained_alternative_qid_overlap` — QID belongs to the accepted 57 SLICE-0021 alternative-route union but not the direct universe;
- `incremental_qid_lead` — QID belongs to neither accepted retained set;
- `no_wikidata_qid` — Wikipedia page has no linked QID.

Cross-surface duplicate page IDs and duplicate QIDs MUST be retained/measured explicitly and must not inflate unique-lead counts.

`incremental_qid_lead` means only **not present in the accepted retained 1,829 + 57 comparison sets**. It does not prove current global novelty, valid BoatModel identity, or admission eligibility.

## Exact identity-signal comparison

For QIDs outside the accepted direct universe, compare the Wikipedia page title against accepted canonical BoatModel preferred labels / retained safe aliases using the same narrow exact identity-signal semantics accepted in SLICE-0021:

```python
value.strip().casefold()
```

Do not introduce:

- internal-whitespace collapse;
- punctuation rewriting;
- manufacturer-prefix manipulation;
- token reordering;
- fuzzy matching;
- generation collapsing;
- semantic inference.

Retain at minimum:

- exact signal to accepted canonical identity under another QID;
- no exact signal;
- unresolved structural condition if encountered.

An exact title signal is still only a research signal and cannot resolve identity automatically.

## Bounded Wikidata CC0 quality sample

To estimate how noisy the incremental Wikipedia lead route is without copying Wikipedia article text, create a deterministic sample of at most **150 unique `incremental_qid_lead` QIDs**.

Target stratification where enough candidates exist:

```text
Keelboats      up to 90 unique incremental QIDs
Catamarans     up to 30 unique incremental QIDs
Trimarans      up to 30 unique incremental QIDs
TOTAL          <= 150 unique QIDs
```

If one candidate belongs to multiple fixed categories, count it once globally and retain all memberships.

Within each stratum choose candidates deterministically by ascending SHA256 of the QID string. Do not hand-pick appealing names.

For only this sample, use Wikidata `wbgetentities` to retain the minimal CC0 quality context:

- QID;
- English label;
- English description;
- direct `P31` values;
- direct `P176` / `P287` values only if already available in the returned entity payload and useful as review context.

Do not run a new broad WDQS discovery query as part of this slice.

No sampled Wikidata fact may create Brand, Organization, BoatDesign or BoatModel rows.

## Research-only quality review

Each sampled incremental QID must receive exactly one **research-only** review tag:

- `plausible_model_or_class_lead`;
- `obvious_out_of_scope`;
- `ambiguous`.

Definitions:

### `plausible_model_or_class_lead`

Retained page identity plus minimal Wikidata CC0 label/description/context explicitly supports that the subject is a named sailboat model, production series, racing class or design-family identity potentially relevant to HullQ.

This does **not** prove canonical identity or authorize admission.

### `obvious_out_of_scope`

Retained context explicitly shows an individual named vessel, ferry, military craft, person, organization, event, generic naval-architecture concept, non-sailing craft or another clearly non-HullQ model/class subject.

### `ambiguous`

The retained minimal facts are insufficient to place the lead safely in either category above.

Every manual/research tag must retain a short factual rationale tied only to the retained lead/Wikidata context.

Do not create an automated semantic classifier from these tags in this slice.

## Source-level recommendation vocabulary

After measurement, give exactly one recommendation for this category-discovery route:

- `FOLLOWUP_VERIFICATION_CANDIDATE`;
- `LOW_INCREMENTAL_YIELD`;
- `TOO_NOISY_FOR_FOLLOWUP`;
- `RIGHTS_OR_ACCESS_BLOCKED`.

Precommitted recommendation rule:

1. if rights/access conditions were violated or cannot be retained truthfully -> `RIGHTS_OR_ACCESS_BLOCKED`;
2. else if unique `incremental_qid_lead` count is below **100** -> `LOW_INCREMENTAL_YIELD`;
3. else if fewer than **50%** of the deterministic quality sample are `plausible_model_or_class_lead` -> `TOO_NOISY_FOR_FOLLOWUP`;
4. otherwise -> `FOLLOWUP_VERIFICATION_CANDIDATE`.

`ambiguous` is conservative and does not count as plausible for the 50% rule.

This recommendation is research-only. Even `FOLLOWUP_VERIFICATION_CANDIDATE` does not authorize production acquisition or canonical admission.

## Network and request boundary

The one retained live measurement may contact only:

- `en.wikipedia.org` MediaWiki Action API for the three fixed category roots and pageprops/QID mapping;
- `www.wikidata.org` `wbgetentities` for the deterministic <=150-QID quality sample.

MUST NOT contact:

- WDQS/SPARQL for a new broad discovery query;
- Wikimedia Commons;
- PetScan;
- DBpedia;
- manufacturer/archive sites;
- SailboatData;
- search engines;
- marketplace/listing sources;
- any other external source.

Requests must be serial or conservatively batched and use an informative HullQ User-Agent. Retain per-host request counts and retrieval timestamps.

Hard request ceiling for the retained acquisition:

```text
Wikipedia/MediaWiki HTTP requests <= 75
Wikidata wbgetentities requests    <= 10
TOTAL external HTTP requests       <= 85
```

If the complete fixed measurement cannot be produced inside those ceilings, stop `BLOCKED` or report route incompleteness; do not silently exceed the cap.

## One-shot retained acquisition rule

The slice is expected to perform **one bounded retained live acquisition**.

After the retained artifacts are committed:

- amendments should operate offline against those retained artifacts;
- do not rerun live acquisition merely because code/tests/reporting need correction;
- a second live acquisition requires an explicit independent-review finding that the first measurement itself is invalid and must be replaced.

Normal CI MUST perform zero external Wikipedia/Wikidata acquisition.

## Required retained package

Create an isolated package, for example:

```text
research/bootstrap/wikimedia/sl0023-category-leads/
    source_assessment_schema.json
    source_assessment.json
    discovery_manifest_schema.json
    discovery_manifest.json
    quality_sample_schema.json
    quality_sample.json
    REPORT.md
    ARTIFACT-DIGESTS.json
```

Exact filenames may vary only when repository conventions materially justify it.

Retained evidence must include at minimum:

- slice/schema versions;
- acquisition timestamp;
- fixed category names and exact API endpoint;
- source-rights/access assessment and supporting URLs/review date;
- User-Agent identifier used;
- request counts and continuation counts;
- per-category raw membership count within scope;
- per-category cap/completeness status;
- exact retained page IDs/titles/category memberships/canonical page URLs;
- linked Wikidata QID where present;
- duplicate-page / duplicate-QID cross-surface memberships;
- exact overlap with accepted 1,829 direct QIDs;
- exact overlap with accepted 57 alternative-route QIDs;
- unique incremental QID set;
- no-QID count;
- exact title-signal comparison result where applicable;
- deterministic quality-sample selection proof;
- minimal retained Wikidata CC0 sample context;
- per-sample research-only quality tag + rationale;
- quality-tag totals and percentages;
- final source-level recommendation from the precommitted rule;
- deterministic digests for retained artifacts.

Do not retain article prose, infobox fields, images or third-party quoted text merely to make the review easier.

## Offline verification

Provide a strict offline verifier that fails closed if retained outputs do not reproduce from committed evidence and accepted immutable inputs.

At minimum independently verify/recompute:

- accepted 1,829 / 1,770 / 1,772 baseline counts;
- accepted SLICE-0017/0018 manifest digests;
- accepted 57-QID alternative-route set;
- exact fixed category route names;
- hard caps and completeness flags;
- unique page IDs and QIDs;
- cross-route duplicate memberships;
- every overlap/incremental/no-QID set;
- exact identity-signal categories;
- deterministic <=150 sample selection;
- sample stratum membership;
- allowed manual review vocabulary and required rationale presence;
- all totals/percentages;
- source-level recommendation against the precommitted rule;
- request-count ceilings;
- artifact digests.

Tamper tests must prove rejection of manipulated:

- category membership/page IDs;
- QID mappings;
- baseline overlap sets;
- incremental QID sets;
- duplicate memberships;
- sample selection;
- quality tags/totals;
- recommendation;
- request counts/caps;
- immutable input hashes/counts;
- artifact digests.

The verifier does not need to reproduce subjective semantic judgment from scratch, but it must verify that every retained manual tag belongs to the allowed vocabulary, references an actual deterministic sample record and carries a non-empty rationale. Independent review evaluates whether those judgments are defensible.

## No canonical / production mutation

SLICE-0023 MUST NOT:

- create, modify or delete canonical Brand/Organization/BoatModel/BoatDesign rows;
- mint HullQ IDs;
- modify the accepted 1,772-entry crosswalk;
- change `WikidataAdapter.discover_sailboat_qids`;
- add Wikipedia/Wikimedia to a production discovery adapter;
- promote category membership to canonical evidence;
- ingest Wikipedia article/infobox technical values;
- resolve the SLICE-0017/0018 review queues;
- resolve/admit the 31 SLICE-0022 review-required candidates;
- begin Tier-1/Tier-2 enrichment;
- begin query-engine/API/frontend/search work.

## Explicitly out of scope

- recursive Wikipedia category crawling;
- German/French/other-language Wikipedia expansion;
- Wikimedia Commons category discovery;
- parsing `List of sailing boat types` or other list articles;
- Wikipedia article-text/infobox extraction;
- Wikipedia production-value use;
- legal determination that CC BY-SA is compatible with HullQ's future public database;
- production adapter implementation;
- canonical admission from the new leads;
- manual verification campaign over all incremental leads;
- manufacturer archive ingestion;
- new marketplace sources;
- Stage-3.3 field enrichment;
- OQ-009 query-semantics implementation;
- FastAPI/Astro/auth/monitoring/price-history work;
- SLICE-0024 creation/start.

## Expected touch points

Likely/allowed touch points:

- focused research acquisition/verification logic under `src/hullq/research/`, `src/hullq/bootstrap/` or another existing repository-conventional location;
- one bounded runner under `scripts/research/` or `scripts/bootstrap/`;
- focused unit tests;
- retained package under `research/bootstrap/wikimedia/sl0023-category-leads/`;
- `.github/workflows/ci.yml` only if needed to add the offline verifier/schema gate;
- this controlling slice document;
- `docs/slices/INDEX.md` and `docs/PROJECT_STATE.md` for normal `REVIEW` handoff.

Do not modify accepted SLICE-0017/0018/0021/0022 retained artifacts.

## Acceptance criteria

- [ ] accepted baseline hashes/counts reproduce fail-closed before acquisition;
- [ ] acquisition uses exactly the three fixed English-Wikipedia category roots and no recursive expansion;
- [ ] only main-namespace page membership is retained from Wikipedia;
- [ ] per-category and global hard caps are enforced before silent overrun;
- [ ] Wikipedia/API source-rights/access evidence is retained truthfully under accepted policy;
- [ ] no Wikipedia prose, infobox value, image or article technical field becomes canonical evidence/value;
- [ ] category page -> Wikidata QID mapping is explicit and complete within the retained bounded measurement;
- [ ] accepted direct-QID overlap / accepted alternative-QID overlap / incremental-QID / no-QID sets are exact and independently verifiable;
- [ ] cross-surface duplicate pages/QIDs are measured and do not inflate unique-lead counts;
- [ ] exact identity-signal comparison reuses the accepted SLICE-0021 trim+casefold-only rule with no fuzzy/semantic identity matching;
- [ ] deterministic quality sample is <=150 unique incremental QIDs and follows the precommitted stratum/hash rule;
- [ ] Wikidata CC0 quality acquisition is bounded to that sample and does not run broad WDQS discovery;
- [ ] every sampled lead has exactly one allowed research-only quality tag and factual rationale;
- [ ] precommitted source-level recommendation rule is applied mechanically to the measured counts;
- [ ] total external request count remains <=85 and per-host ceilings are retained/verified;
- [ ] one-shot retained acquisition is preserved; normal CI is fully offline;
- [ ] strict retained schemas and deterministic artifact digests are provided;
- [ ] offline verifier recomputes all structurally derivable sets/totals/recommendation and tamper tests cover the required fields;
- [ ] no canonical row, HullQ ID or historical crosswalk mapping is created/changed;
- [ ] production Wikidata discovery remains unchanged;
- [ ] Wikipedia/Wikimedia is not promoted to a production adapter or production-value source;
- [ ] no SLICE-0017/0018/0022 review candidate is resolved as a side effect;
- [ ] Stage-3.3 enrichment is not started;
- [ ] SLICE-0024 is not created or started;
- [ ] local repository validation/tests/coverage pass;
- [ ] required remote CI is actually observed on the exact final pushed head;
- [ ] independent review occurs before owner acceptance;
- [ ] explicit project-owner acceptance is required before closure to `DONE`.

## Validation

At minimum run:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Also run the new retained schema validation and offline verification path.

The final validation/CI pass must not require external Wikipedia or Wikidata access.

## Stop conditions

Stop and report `BLOCKED` instead of inventing a solution if:

- accepted 1,829 / 1,770 / 1,772 / 57 boundaries do not reproduce;
- the required fixed Wikipedia category root does not exist or cannot be enumerated truthfully;
- category completeness cannot be achieved inside the hard cap/request ceiling;
- Wikimedia access/terms cannot be represented truthfully under the accepted source-rights vocabulary;
- the implementation would need Wikipedia article text/infobox extraction to produce the measurement;
- the implementation would need recursive category crawling or another discovery source;
- page-to-QID mapping requires heuristic identity inference;
- preserving prior retained artifacts is impossible;
- implementation requires canonical admission or production adapter changes;
- implementation requires scope outside this slice.

## Status handoff rule

Claude Code may hand SLICE-0023 back only as `REVIEW`, `BLOCKED` or `IN_PROGRESS`.

It MUST NOT merge its own PR, mark the slice `DONE`, create/start SLICE-0024, begin Stage-3.3 enrichment or productionize the Wikimedia route automatically.

## Mandatory completion report additions

In addition to the exact `docs/slices/SLICE_TEMPLATE.md` completion report structure required by the hardened `START_SLICE` workflow, the final operator-facing response must explicitly include:

1. exact final branch HEAD SHA and complete changed-file list;
2. exact live hosts contacted and total/per-host HTTP request counts;
3. exact fixed category routes and per-route acquired counts/completeness/cap status;
4. accepted immutable input hash/count checks (1,829 / 1,770 / 1,772 / 57);
5. unique page count, unique QID count and cross-route duplicate counts;
6. direct-QID overlap / retained-alt-QID overlap / incremental-QID / no-QID totals overall and per route;
7. exact identity-signal category totals;
8. deterministic quality-sample size and per-route/stratum composition;
9. quality review totals/percentages for plausible / out-of-scope / ambiguous;
10. source-rights/access assessment and confirmation no Wikipedia article/infobox content became canonical evidence;
11. final source-level recommendation and proof it follows the precommitted rule;
12. retained artifact paths and digests;
13. offline verifier/tamper-test results;
14. local test/coverage/tooling results;
15. exact-head remote CI result;
16. explicit confirmation: zero canonical mutations, production Wikidata discovery unchanged, no Stage-3.3 work, no SLICE-0024.

The complete report must be returned directly in Claude's final chat response. A committed report or PR body does not substitute for the operator-facing handoff.

## Readiness authority note

This primary slice contract is the specific authorization for SLICE-0023 once its readiness PR is merged to `main`.

`docs/slices/INDEX.md` is the canonical operational queue and should be updated during normal slice handoff. If a generic operational-summary sentence elsewhere still says that no SLICE-0023 is ready, that sentence predates this specific readiness decision and does not authorize broader scope than this contract.
