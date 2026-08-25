# SLICE-0023 — Wikimedia Category Identity-Lead Discovery Pilot

**ID:** SLICE-0023  
**Type:** DESIGN_RESEARCH  
**Status:** REVIEW  
**Stage:** 3.2 — canonical identity breadth / alternative research-lead discovery  
**Depends on:** SLICE-0022 accepted / DONE  
**Blocks:** any production use of Wikipedia/Wikimedia category discovery for HullQ identity intake

## Objective

Measure whether a **fixed, bounded English-Wikipedia category-discovery path** can provide a materially useful set of sailboat model/class **research leads** beyond HullQ's accepted Stage-3.2 identity boundaries, while keeping Wikipedia/Wikimedia content strictly outside canonical admission and production-value ingestion.

This is a **research-lead yield and noise measurement**, not a Wikipedia production adapter, not a canonical bootstrap expansion and not Stage-3.3 technical enrichment.

## Why this slice exists

Accepted Stage-3.2 state after SLICE-0022:

```text
retained direct Wikidata discovery candidates      1,829 QIDs
accepted canonical BoatModels                      1,770
retained historical QID -> HullQ-ID mappings       1,772
SLICE-0021 alternative-route leads                     57
SLICE-0022 new canonical admissions                     0
```

SLICE-0018 measured the accepted direct `P31 = sailboat class` Wikidata route at 1,829 candidates rather than the planned 2,500 window. SLICE-0020 found **0 `ADAPTER_READY`** manufacturer/archive sources in its fixed sample. SLICE-0021 found 57 additional Wikidata route signals, but SLICE-0022 proved those broader routes are **discovery-authoritative, not admission-authoritative**: final result **0 AUTO_ADMIT / 31 REVIEW_REQUIRED / 26 NOT_ADMITTED**.

Stage 3.2 therefore still needs a new breadth rationale rather than simply increasing the old Wikidata query limit or prematurely substituting Stage-3.3 enrichment. `docs/DATABASE_COVERAGE_STRATEGY.md` explicitly prefers breadth first and describes a plausible useful-state direction of 5,000+ known designs.

Readiness research on 2026-08-25 observed broad English-Wikipedia category surfaces of approximately 1,492 pages in `Category:Keelboats`, 121 in `Category:Catamarans` and 84 in `Category:Trimarans`. They visibly contain both useful model/class identities and obvious noise, making them suitable for a bounded **lead-source measurement**, not automatic canonical admission.

## Controlling artifacts

Read and obey at minimum:

- `CLAUDE.md`;
- `docs/EXECUTION_PLAN.md` — Stage 3.1 / 3.2 / 3.3 ordering;
- `docs/DATABASE_COVERAGE_STRATEGY.md`;
- `docs/DATA_STRATEGY.md` where relevant;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md` and ADR-0005;
- SLICE-0017, SLICE-0018, SLICE-0021 and SLICE-0022 controlling documents + closures;
- `docs/slices/SLICE-0022-r1-admission-governance-amendment.md`;
- `research/bootstrap/wikidata/manifest.json`;
- `research/bootstrap/wikidata/sl0018-2500/manifest.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/discovery_probe.json`;
- `research/bootstrap/wikidata/sl0021-alt-discovery/sampled_candidates.json`;
- accepted HullQ search-key/search-projection semantics from `src/hullq/domain/identity.py`.

## Source-rights and access boundary

`specs/SOURCE_RIGHTS_POLICY.v0.1.md` is controlling. Its accepted Wikipedia baseline says Wikipedia/Wikimedia text is **not equivalent to Wikidata CC0**. Wikipedia may be used as research evidence/lead material; bulk canonical ingestion from Wikipedia text/infobox material remains conditional/legal-review-required until reuse/attribution/share-alike implications are explicitly resolved.

For SLICE-0023:

- English Wikipedia is a **research-lead surface only**;
- no Wikipedia prose, infobox values, tables, images, references or expressive article content may become HullQ canonical/provenance values;
- retain only minimal lead metadata needed for the measurement: category name, page ID, namespace, page title, canonical page URL and linked Wikidata QID where present;
- retain source/license/access evidence and review date;
- use an informative HullQ User-Agent and respectful serial/conservatively batched requests;
- API availability does not authorize production/bulk canonical reuse;
- any future production use requires its own rights/architecture decision and slice.

Source-assessment evidence must include at minimum:

- `https://foundation.wikimedia.org/wiki/Terms_of_Use`;
- `https://www.mediawiki.org/wiki/Wikimedia_APIs/Access_policy`;
- `https://www.mediawiki.org/wiki/API:Categorymembers`;
- `https://www.mediawiki.org/wiki/API:Licensing`.

Wikidata CC0 may be used only for the bounded quality sample below. It does not convert Wikipedia category membership into canonical evidence.

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

SLICE-0022 created no new canonical identities and must not be reinterpreted as an expanded baseline. If any accepted hash/count/set boundary does not reproduce, stop `BLOCKED`; do not refresh/rewrite prior retained evidence.

## Fixed live discovery surfaces

Exactly these three English-Wikipedia category roots are authorized:

```text
Category:Keelboats
Category:Catamarans
Category:Trimarans
```

Use only the English Wikipedia MediaWiki Action API:

```text
https://en.wikipedia.org/w/api.php
```

Category acquisition MUST use `list=categorymembers`, `cmnamespace=0`, main-namespace pages only.

Required behavior:

- no files;
- no subcategory recursion;
- no category expansion beyond the three fixed roots;
- follow continuation only until the complete fixed root is enumerated or its hard cap is exceeded;
- preserve source ordering/page IDs exactly as returned while also computing deterministic sorted/set views;
- retain request/continuation counts.

Hard caps:

```text
Category:Keelboats     <= 2,000 main-namespace pages
Category:Catamarans    <=   250 main-namespace pages
Category:Trimarans     <=   200 main-namespace pages
combined memberships   <= 2,450 rows before cross-route deduplication
```

If a category exceeds its cap, mark that route `CAP_EXCEEDED` and stop the slice `BLOCKED`; do not silently truncate an incomplete route into a complete measurement.

## Page-to-Wikidata mapping and overlap categories

For every acquired page, use MediaWiki page properties to retain the linked `wikibase_item` QID when present. Do not parse article bodies or infoboxes to infer a QID.

Each unique page/QID lead must be categorized deterministically against accepted retained boundaries:

- `accepted_direct_qid_overlap` — QID belongs to accepted 1,829 direct universe;
- `retained_alternative_qid_overlap` — QID belongs to accepted 57 SLICE-0021 alternative union but not direct universe;
- `incremental_qid_lead` — QID belongs to neither accepted retained set;
- `no_wikidata_qid` — page has no linked QID.

Cross-surface duplicate page IDs and duplicate QIDs MUST be retained/measured explicitly and must not inflate unique-lead counts.

`incremental_qid_lead` means only **not present in the accepted retained 1,829 + 57 comparison sets**. It does not prove global novelty, valid BoatModel identity or admission eligibility.

## Exact identity-signal comparison

For QIDs outside the accepted direct universe, compare Wikipedia page title against accepted canonical BoatModel preferred labels / retained safe aliases using exactly the SLICE-0021 rule:

```python
value.strip().casefold()
```

No internal-whitespace collapse, punctuation rewriting, manufacturer-prefix manipulation, token reordering, fuzzy matching, generation collapsing or semantic inference.

Retain at minimum:

- exact signal to accepted canonical identity under another QID;
- no exact signal;
- unresolved structural condition if encountered.

An exact title signal remains research-only and cannot resolve identity automatically.

## Deterministic Wikidata CC0 quality sample

Create a deterministic sample of at most **150 unique `incremental_qid_lead` QIDs**.

Sampling strata and caps:

```text
Keelboats      up to 90 unique incremental QIDs
Catamarans     up to 30 unique incremental QIDs
Trimarans      up to 30 unique incremental QIDs
TOTAL          <= 150 unique QIDs
```

### Multi-category precedence — binding

For **sampling only**, assign each incremental QID to exactly one primary stratum using this fixed precedence:

```text
Trimarans > Catamarans > Keelboats
```

A QID present in more than one fixed category therefore belongs to the highest-precedence matching stratum for sample selection, while **all original category memberships remain retained in the discovery evidence**. This primary-stratum assignment must be recomputable offline.

Within each primary stratum, sort candidates by ascending SHA256 of the UTF-8 QID string and select the first N up to the stratum cap. Do not hand-pick names. Do not backfill unused capacity from another stratum; total sample size may therefore be below 150.

For only this deterministic sample, use Wikidata `wbgetentities` to retain minimal CC0 context:

- QID;
- English label;
- English description;
- direct `P31` values;
- direct `P176` / `P287` values only if already present and useful as review context.

Do not run a new broad WDQS/SPARQL discovery query. No sampled Wikidata fact may create Brand, Organization, BoatDesign or BoatModel rows.

## Research-only quality review

Each sampled incremental QID receives exactly one tag:

- `plausible_model_or_class_lead`;
- `obvious_out_of_scope`;
- `ambiguous`.

Definitions:

- `plausible_model_or_class_lead`: retained page identity + minimal Wikidata context explicitly supports a named sailboat model, production series, racing class or design-family identity potentially relevant to HullQ; this does not authorize admission.
- `obvious_out_of_scope`: retained context explicitly shows an individual vessel, ferry, military craft, person, organization, event, generic concept, non-sailing craft or other clearly non-HullQ model/class subject.
- `ambiguous`: minimal retained facts are insufficient for either category above.

Every tag must carry a short factual rationale tied only to retained lead/Wikidata context. Do not create an automated semantic classifier from these tags.

## Source-level recommendation

Give exactly one research-only recommendation:

- `FOLLOWUP_VERIFICATION_CANDIDATE`;
- `LOW_INCREMENTAL_YIELD`;
- `TOO_NOISY_FOR_FOLLOWUP`;
- `RIGHTS_OR_ACCESS_BLOCKED`.

Precommitted rule, in order:

1. if rights/access conditions were violated or cannot be retained truthfully -> `RIGHTS_OR_ACCESS_BLOCKED`;
2. else if unique `incremental_qid_lead` count is below **100** -> `LOW_INCREMENTAL_YIELD`;
3. else if fewer than **50%** of the deterministic quality sample are `plausible_model_or_class_lead` -> `TOO_NOISY_FOR_FOLLOWUP`;
4. otherwise -> `FOLLOWUP_VERIFICATION_CANDIDATE`.

`ambiguous` does not count as plausible. A follow-up recommendation never authorizes production acquisition or canonical admission.

## Network/request boundary and one-shot acquisition

The retained live measurement may contact only:

- `en.wikipedia.org` MediaWiki Action API for the fixed categories and pageprops/QID mapping;
- `www.wikidata.org` `wbgetentities` for the deterministic <=150-QID quality sample.

MUST NOT contact WDQS/SPARQL for broad discovery, Commons, PetScan, DBpedia, manufacturer/archive sites, SailboatData, search engines, marketplaces or any other source.

Hard request ceilings:

```text
Wikipedia/MediaWiki HTTP requests <= 75
Wikidata wbgetentities requests    <= 10
TOTAL external HTTP requests       <= 85
```

Retain per-host request counts and retrieval timestamps. If a complete measurement cannot fit the ceilings, stop `BLOCKED`; do not exceed them silently.

Perform **one bounded retained live acquisition**. After retained artifacts are committed, amendments operate offline. Do not rerun live acquisition merely to fix code/tests/reporting. A second live acquisition requires an explicit independent-review finding that the first measurement itself is invalid and must be replaced. Normal CI performs zero external Wikipedia/Wikidata acquisition.

## Required retained package

Create an isolated package, preferably:

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

Exact filenames may vary only where repository conventions materially justify it.

Retained evidence must include at minimum:

- slice/schema versions and acquisition timestamp;
- fixed category names/API endpoint;
- source-rights/access assessment, evidence URLs, review date, User-Agent;
- request/continuation counts;
- per-category membership counts and completeness/cap status;
- exact page IDs/titles/memberships/canonical URLs and linked QIDs;
- duplicate-page / duplicate-QID cross-surface memberships;
- exact direct-QID overlap, 57-alternative-QID overlap, incremental-QID and no-QID sets;
- exact title-signal results;
- deterministic primary-stratum assignment + sample selection proof;
- minimal Wikidata CC0 sample context;
- quality tag/rationale per sample;
- quality totals/percentages;
- final recommendation from the precommitted rule;
- deterministic artifact digests.

Do not retain article prose, infobox fields, images or third-party quoted text merely to ease review.

## Offline verification

Provide a strict offline verifier that fails closed on inconsistent retained output.

At minimum independently verify/recompute:

- 1,829 / 1,770 / 1,772 accepted counts and accepted SLICE-0017/0018 digests;
- accepted 57-QID alternative set;
- fixed routes, hard caps and completeness;
- unique page IDs/QIDs and cross-route duplicates;
- all overlap/incremental/no-QID sets;
- exact identity-signal categories;
- multi-category primary-stratum assignment under `Trimarans > Catamarans > Keelboats`;
- deterministic SHA256 sample selection and <=150 bound;
- allowed manual-review vocabulary and non-empty rationales;
- totals/percentages and recommendation rule;
- request ceilings;
- artifact digests.

Tamper tests must reject manipulated category membership/page IDs, QID mappings, baseline overlap/incremental sets, duplicate memberships, primary-stratum/sample selection, quality tags/totals, recommendation, request counts/caps, immutable hashes/counts and artifact digests.

The verifier need not reproduce subjective semantic judgment from scratch, but independent review must assess whether retained manual judgments are defensible.

## No canonical / production mutation

SLICE-0023 MUST NOT:

- create/modify/delete canonical Brand/Organization/BoatModel/BoatDesign rows;
- mint HullQ IDs or alter the accepted 1,772-entry crosswalk;
- change `WikidataAdapter.discover_sailboat_qids`;
- add Wikipedia/Wikimedia to production discovery;
- promote category membership to canonical evidence;
- ingest Wikipedia article/infobox technical values;
- resolve SLICE-0017/0018 review queues or the 31 SLICE-0022 review candidates;
- begin Tier-1/Tier-2 enrichment;
- begin query-engine/API/frontend/search work.

## Explicitly out of scope

- recursive Wikipedia categories;
- non-English Wikipedia expansion;
- Wikimedia Commons category discovery;
- list-article parsing;
- article-text/infobox extraction;
- Wikipedia production-value use or a legal compatibility determination for CC BY-SA;
- production adapter or canonical admission from new leads;
- manual verification of all incremental leads;
- manufacturer/archive ingestion;
- marketplace sources;
- Stage-3.3 field enrichment;
- OQ-009/query-engine/FastAPI/Astro/auth/monitoring/price-history work;
- SLICE-0024 creation/start.

## Expected touch points

Likely/allowed:

- focused acquisition/verification logic under an existing repository-conventional `src/hullq/...` location;
- one bounded runner under `scripts/research/` or `scripts/bootstrap/`;
- focused unit tests;
- retained package under `research/bootstrap/wikimedia/sl0023-category-leads/`;
- `.github/workflows/ci.yml` only if needed for offline schema/verify gates;
- this primary slice document;
- `docs/slices/INDEX.md` and `docs/PROJECT_STATE.md` for normal `REVIEW` handoff.

Do not modify accepted SLICE-0017/0018/0021/0022 retained artifacts.

## Acceptance criteria

- [ ] accepted baseline hashes/counts reproduce fail-closed before acquisition;
- [ ] exactly the three fixed English-Wikipedia category roots are used, without recursion/expansion;
- [ ] only main-namespace page membership is retained;
- [ ] all hard caps/request ceilings are enforced fail-closed;
- [ ] Wikipedia/API rights/access evidence is retained truthfully under accepted policy;
- [ ] no Wikipedia prose/infobox/image/article technical field becomes canonical evidence/value;
- [ ] page -> linked Wikidata QID mapping is explicit and complete within the bounded measurement;
- [ ] direct-overlap / retained-alt-overlap / incremental-QID / no-QID sets are exact and independently verifiable;
- [ ] cross-surface duplicates are measured and do not inflate unique counts;
- [ ] exact identity comparison reuses trim+casefold-only semantics, with no fuzzy/semantic matching;
- [ ] multi-category primary-stratum assignment follows `Trimarans > Catamarans > Keelboats` exactly;
- [ ] deterministic sample is <=150 unique incremental QIDs and follows the precommitted SHA256 rule without cross-stratum backfill;
- [ ] Wikidata CC0 quality acquisition is bounded to that sample and uses no broad WDQS discovery;
- [ ] every sample has exactly one allowed quality tag + factual rationale;
- [ ] the recommendation rule is applied mechanically;
- [ ] one-shot retained acquisition is preserved and normal CI is fully offline;
- [ ] strict retained schemas, digests, offline verifier and required tamper tests are present;
- [ ] no canonical row/ID/crosswalk mapping changes;
- [ ] production Wikidata discovery unchanged and Wikimedia not productionized;
- [ ] no prior review queue is resolved as a side effect;
- [ ] Stage-3.3 not started and SLICE-0024 not created/started;
- [ ] repository validation/tests/coverage pass;
- [ ] required remote CI is observed on the exact final pushed head;
- [ ] independent review occurs before owner acceptance;
- [ ] explicit project-owner acceptance is required before `DONE`.

## Validation

At minimum:

```bash
uv run python scripts/validate_repository.py
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run coverage run -m pytest
uv run coverage report
```

Also run retained schema validation and the new offline verifier. Final validation/CI must not require external Wikipedia/Wikidata access.

## Stop conditions

Stop `BLOCKED` instead of inventing a solution if:

- accepted 1,829 / 1,770 / 1,772 / 57 boundaries do not reproduce;
- a fixed category cannot be enumerated truthfully inside cap/request ceilings;
- Wikimedia rights/access conditions cannot be represented truthfully;
- measurement requires article text/infobox extraction, recursive crawling, another discovery source or heuristic page-to-QID inference;
- prior retained artifacts cannot remain unchanged;
- work would require canonical admission, production-adapter changes or any scope outside this slice.

## Status handoff rule

Claude Code may hand SLICE-0023 back only as `REVIEW`, `BLOCKED` or `IN_PROGRESS`.

It MUST NOT merge its own PR, mark the slice `DONE`, create/start SLICE-0024, begin Stage-3.3 enrichment or productionize the Wikimedia route automatically.

## Mandatory completion report additions

In addition to the exact `docs/slices/SLICE_TEMPLATE.md` completion-report structure required by the hardened `START_SLICE` workflow, the final operator-facing response must explicitly include:

1. exact final branch HEAD and complete changed-file list;
2. exact live hosts and total/per-host request counts;
3. fixed category routes + per-route counts/completeness/cap status;
4. immutable input checks (1,829 / 1,770 / 1,772 / 57 + pinned hashes/blobs);
5. unique page/QID counts and cross-route duplicate counts;
6. direct-overlap / retained-alt-overlap / incremental-QID / no-QID totals overall and per route;
7. exact identity-signal totals;
8. quality-sample size, deterministic primary-stratum composition and selection proof;
9. plausible / out-of-scope / ambiguous totals and percentages;
10. source-rights/access assessment and confirmation no Wikipedia article/infobox content became canonical evidence;
11. final recommendation and proof it follows the precommitted rule;
12. retained artifact paths/digests;
13. offline verifier/tamper-test results;
14. local tests/coverage/tooling results;
15. exact-head remote CI result;
16. confirmation of zero canonical mutations, unchanged production Wikidata discovery, no Stage-3.3 work and no SLICE-0024.

The complete report must be returned directly in Claude's final chat response. A repository report or PR body does not substitute for the operator-facing handoff.

## Readiness authority note

This primary slice contract is the specific authorization for SLICE-0023 once its readiness PR is merged to `main`.

`docs/slices/INDEX.md` is the canonical operational queue and should be updated during normal slice handoff. If a generic operational-summary sentence elsewhere still says no SLICE-0023 is ready, that sentence predates this specific readiness decision and does not authorize broader scope than this contract.
