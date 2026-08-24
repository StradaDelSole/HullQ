# SLICE-0021 — Wikidata Alternative Sailboat-Class Discovery Semantics Pilot

**ID:** SLICE-0021
**Type:** DESIGN_RESEARCH
**Status:** READY
**Stage:** 3.2 — rights-cleared alternative identity discovery after the direct-instance Wikidata ceiling
**Depends on:** SLICE-0020 accepted / DONE
**Blocks:** any later change to the production Wikidata discovery semantics based on alternative class routes

## Objective

Measure whether fixed, rights-cleared alternative **Wikidata structured-data** discovery semantics expose meaningful sailboat-model/class identity candidates beyond HullQ's accepted direct-`P31` discovery universe, while preserving accepted identity, provenance and source-rights boundaries.

This is a bounded discovery measurement. It does **not** create or modify canonical HullQ identities, does not change the production Wikidata adapter's accepted discovery query, does not perform technical-field enrichment, and does not authorize any later production expansion by itself.

## Why this slice exists

SLICE-0018 measured **1,829** unique QIDs under HullQ's accepted deterministic direct-instance query:

```sparql
?item wdt:P31 wd:Q106179098 .
```

That measurement is a real ceiling for that accepted **direct-`P31` discovery definition**. It is not proof that all potentially relevant sailboat-class/model identities in Wikidata are exhausted.

SLICE-0019 then found manufacturer/heritage archives to be the strongest observed identity-expansion family if rights permitted systematic use. SLICE-0020 performed the required source-specific clearance test and measured **0 `ADAPTER_READY`**, **9 `RESEARCH_ONLY`/`REVIEW_REQUIRED`**, and **1 `BLOCKED`** across the fixed ten-source archive sample. HullQ therefore must not proceed directly to an automated manufacturer-archive adapter.

Wikidata remains materially different from those archive sources. The accepted source record `fixtures/sources/wikidata_source.json` classifies Wikidata structured data as CC0/public-domain and explicitly clears `identity_seed`, `production_value`, `bulk_bootstrap`, `automated_ingestion` and the other accepted HullQ source uses, subject to Wikimedia access-policy conditions. Wikipedia article text remains excluded from that source record.

The official Wikidata WikiProject Sailing materials document additional structured sailboat-class query/repair paths beyond HullQ's current direct-`P31` query. Before HullQ seeks manufacturer permissions or introduces another source, a small bounded measurement should determine whether those already-cleared Wikidata paths have real incremental identity yield.

Research references that motivate the precommitted routes:

- `https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Queries`
- `https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Data_Models/Sailboat_class`
- `https://www.wikidata.org/wiki/Wikidata:Licensing`
- `https://www.wikidata.org/wiki/Wikidata:Data_access`

These references motivate the contract only. The execution is limited to the exact routes below and may not broaden itself because another query looks interesting.

## Core semantic rules

1. **The accepted 1,829 result remains true.** SLICE-0021 does not reinterpret or overwrite the SLICE-0018 measurement. It measures different discovery semantics.
2. **Current Wikidata drift is separate from alternative-route yield.** Changes in the direct query since the retained 2026-08-21 acquisition are reported independently and never counted as alternative-route incremental yield.
3. **Source rights fail closed before network use.** The accepted Wikidata source record must pass the existing SLICE-0007 gate before the first HTTP request.
4. **Exactly four live query routes are authorized.** R0–R3 below are fixed. No additional route may be added during execution to improve yield.
5. **No canonical admission occurs in this slice.** Discovery candidates remain research measurements even where they appear promising.
6. **Identity signals are exact-only.** Case-insensitive comparison plus surrounding-whitespace trimming is the strongest allowed label/alias normalization. No fuzzy or manufacturer-prefix logic.
7. **R3 is always repair/review evidence.** A structured English description containing `sailboat class` does not itself prove that the item is correctly modeled as a HullQ BoatModel.
8. **Zero incremental yield is valid.** The slice passes by measuring correctly, not by producing a positive result.

## Fixed live query routes

Execution MUST use exactly R0–R3. Each route:

- uses Wikidata structured data through WDQS only;
- uses `SELECT DISTINCT`;
- uses deterministic `ORDER BY ?item`;
- has hard `LIMIT 3000`;
- stores exact query text, route/version identifier and query digest;
- stores the full returned bounded QID set;
- reports `result_count == 3000` as `possibly_truncated = true` rather than silently raising the ceiling.

### R0 — current direct-`P31` control

Route ID: `current_direct_control`

```sparql
SELECT DISTINCT ?item WHERE {
  ?item wdt:P31 wd:Q106179098 .
}
ORDER BY ?item
LIMIT 3000
```

R0 is a current-state control, not a new 3,000-candidate production bootstrap.

Compare R0 directly with the retained SLICE-0017/0018 **1,829-QID direct-discovery universe** and report current Wikidata drift separately.

### R1 — sailboat-class `P31/P279*` closure

Route ID: `sailboat_class_closure`

```sparql
SELECT DISTINCT ?item WHERE {
  ?item wdt:P31/wdt:P279* wd:Q106179098 .
}
ORDER BY ?item
LIMIT 3000
```

The route's incremental yield is:

```text
R1 QIDs MINUS current R0 QIDs
```

not R1 minus only the historical 1,829 set.

### R2 — legacy sailboat-class closure

Route ID: `legacy_sailboat_class_closure`

Legacy class: `Q57303455`

```sparql
SELECT DISTINCT ?item WHERE {
  ?item wdt:P31/wdt:P279* wd:Q57303455 .
}
ORDER BY ?item
LIMIT 3000
```

The official WikiProject Sailing query material identifies this as a legacy sailboat-class route associated with migration toward the current class model. Do not assume it still has yield. A zero-result route is valid evidence.

Incremental yield is:

```text
R2 QIDs MINUS current R0 QIDs
```

### R3 — structured misclassification/repair signal

Route ID: `misclassified_sailboat_class_description`

`Q1075310` = sailboat.

```sparql
SELECT DISTINCT ?item ?desc WHERE {
  ?item wdt:P31 wd:Q1075310 .
  ?item schema:description ?desc .
  FILTER (lang(?desc) = "en")
  FILTER CONTAINS(?desc, "sailboat class")
}
ORDER BY ?item
LIMIT 3000
```

R3 follows the WikiProject's structured repair-query concept. Its items remain **review/repair signals**. R3 membership never directly authorizes canonical admission or a future production classification rule.

Incremental yield is:

```text
R3 QIDs MINUS current R0 QIDs
```

## Explicitly excluded discovery routes

SLICE-0021 MUST NOT use or acquire from:

- PetScan;
- Wikipedia category/list/article scraping;
- Wikipedia infobox/template harvesting;
- Wikimedia article text;
- manufacturer or heritage sites;
- SailboatData;
- DBpedia or another new external source;
- search-engine result pages;
- arbitrary label/text search beyond precommitted R3;
- additional SPARQL heuristics invented during execution.

The fact that WikiProject Sailing mentions other tools does not authorize them here. HullQ's retained Wikidata CC0 source record explicitly separates Wikidata structured data from Wikipedia article text.

## Rights/access gate

Before any network request, execution MUST:

1. load `fixtures/sources/wikidata_source.json`;
2. validate the retained source-rights record through the accepted source contract;
3. evaluate the existing SLICE-0007 fail-closed source-use gate;
4. require `identity_seed = allowed`;
5. require `automated_ingestion = allowed`;
6. require `bulk_bootstrap = allowed` for the bounded route acquisition;
7. perform **zero network requests** if any required decision is not allowed.

Execution must use a descriptive Wikimedia-compliant User-Agent, avoid concurrent WDQS requests, honor HTTP `429` / `Retry-After`, and keep official `wbgetentities` batching at no more than 50 QIDs/request.

This slice does not modify or relax the accepted Wikidata source-clearance record.

## Immutable historical comparison inputs

Before live acquisition, execution MUST load and fingerprint:

- `research/bootstrap/wikidata/manifest.json`
- `research/bootstrap/wikidata/sl0018-2500/manifest.json`

It MUST hard-assert the accepted historical invariants:

```text
retained direct-discovery universe = 1,829 QIDs
accepted AUTO_ADMIT universe       = 1,770 BoatModels
```

The 1,829 set is the union of the 1,000 SLICE-0017 candidate QIDs and the 829 SLICE-0018 expansion-delta QIDs.

The 1,770 accepted comparison universe is the union of 965 SLICE-0017 and 805 SLICE-0018 `AUTO_ADMIT` BoatModels.

Retain SHA256 values for both accepted input manifests before live acquisition. Do not modify, regenerate or rewrite either accepted manifest.

## Current-direct drift measurement

Because Wikidata is mutable, R0 may differ from the retained 2026-08-21 direct-discovery universe. Retain at minimum:

- `retained_direct_count` — must equal 1,829;
- `current_direct_count`;
- `retained_direct_still_present_count`;
- `retained_direct_absent_now_count`;
- `new_current_direct_since_sl0018_count`;
- exact QID lists for absent-now and new-current-direct sets;
- deterministic set digests.

These drift values MUST NOT be added to R1/R2/R3 incremental yield.

## Required per-route measurements

For each R0–R3 retain:

- route ID/version;
- exact query text;
- query SHA256;
- hard limit;
- result count;
- `possibly_truncated` flag;
- full bounded returned QID set;
- deterministic QID-list digest;
- acquisition timestamp;
- HTTP request count;
- throttle/retry/error counts;
- malformed-response count.

For R1–R3 additionally retain:

- overlap with current R0;
- incremental QIDs versus current R0;
- overlap with historical retained 1,829;
- overlap with accepted AUTO_ADMIT 1,770 by QID where applicable;
- pairwise/cross-route overlap;
- total alternative-route union;
- each route's unique contribution after alternative-route overlap is accounted for.

## Bounded entity-detail sample

Do not fetch entity details for every alternative-route result simply because Wikidata permits it.

Only incremental R1/R2/R3 QIDs are eligible for detail sampling.

Hard limits:

- maximum **75 QIDs per alternative route**;
- maximum **200 unique QIDs globally** across R1/R2/R3;
- overlapping route QIDs count once toward the global cap;
- deterministic sample selection by numeric QID order;
- retain full route membership for every sampled QID.

Entity details MUST be fetched only through official `wbgetentities` and limited to identity-relevant structured content:

- QID;
- labels;
- aliases;
- descriptions;
- `P31`;
- `P279`;
- `P176` if present;
- `P287` if present;
- route membership.

Do not collect LOA/LWL/beam/draft/displacement, keel/rudder/material/rig or other broad technical specifications in this slice.

## Exact identity-signal check

For sampled incremental candidates, compare against the accepted 1,770 universe in this order:

1. exact QID overlap;
2. only for QIDs not already accepted, exact label/retained-alias string signals.

Allowed string normalization is exactly:

```python
value.strip().casefold()
```

That means only surrounding-whitespace trimming plus case-insensitive comparison.

Forbidden normalization/resolution includes:

- internal-whitespace collapsing;
- punctuation rewriting/removal;
- manufacturer-prefix insertion or stripping;
- token reordering;
- abbreviation expansion;
- fuzzy/edit-distance matching;
- generation collapsing;
- semantic manufacturer/brand/model inference.

Retain research-only categories:

- `accepted_qid_overlap`;
- `exact_identity_signal_other_qid`;
- `no_exact_identity_signal`;
- `unresolved_exact_identity_signal`.

If an exact normalized label/alias signal maps to more than one accepted HullQ identity, classify it as `unresolved_exact_identity_signal`; never choose one.

`no_exact_identity_signal` means only that this bounded exact probe found no exact signal. It does not prove global novelty, does not prove no corresponding HullQ identity exists, and does not authorize canonical admission.

## R3 fail-closed rule

Every R3 candidate remains review-bound in SLICE-0021 regardless of label/description quality.

An R3 item may be measured as overlapping an already accepted QID or as carrying an exact identity signal, but the slice MUST NOT create a new admission rule from the description text and MUST NOT treat `description contains "sailboat class"` as proof of correct class modeling.

## No canonical mutation or production-query change

SLICE-0021 MUST NOT:

- create canonical BoatModel/BoatDesign/Brand/Organization rows;
- update or delete canonical rows;
- mint HullQ IDs for incremental candidates;
- modify the retained SLICE-0017/0018 QID→HullQ-ID crosswalk;
- modify accepted SLICE-0017/0018 manifests;
- import R1/R2/R3 candidates into canonical PostgreSQL tables;
- modify the accepted production adapter's default discovery query;
- promote R1/R2/R3 to production behavior;
- resolve the existing SLICE-0017/0018 review queues.

## Required retained package

Create a dedicated package, for example:

```text
research/bootstrap/wikidata/sl0021-alt-discovery/
    discovery_probe_schema.json
    discovery_probe.json
    sampled_candidates_schema.json
    sampled_candidates.json
    REPORT.md
```

A small deterministic acquisition/analysis runner and focused tests are allowed and expected where they improve auditability and offline reproducibility.

Do not write new outputs into the accepted SLICE-0017 or SLICE-0018 retained artifact directories.

## Reproducibility requirements

The retained result must support offline validation after the one bounded live acquisition.

At minimum provide:

- fixed route definitions and version IDs;
- exact query text/digests;
- immutable-input manifest fingerprints;
- full bounded QID sets;
- deterministic QID-list digests;
- deterministic detail-sample selection;
- retained sampled entity facts sufficient to recompute identity signals offline;
- an offline regeneration/report-validation path;
- tests pinning historical 1,829 and accepted 1,770 universes;
- tests proving direct-source drift is separate from alternative-route yield;
- tests proving sample caps are hard;
- tests proving R3 never directly authorizes canonical admission;
- tests proving internal-whitespace/punctuation/prefix/fuzzy transformations cannot manufacture a match.

Normal CI MUST NOT perform live Wikidata requests. It validates/recomputes from committed retained acquisition results.

## Result/disposition vocabulary

Each alternative route resolves to one evidence-derived disposition:

- `NO_INCREMENTAL_YIELD` — no QID outside current R0;
- `RESEARCH_ONLY_SIGNAL` — incremental QIDs exist but retained evidence does not justify a later production discovery route;
- `FOLLOWUP_DISCOVERY_CANDIDATE` — measured incremental identity signal is sufficient to justify considering a separate future bounded production-discovery contract.

`FOLLOWUP_DISCOVERY_CANDIDATE` is a recommendation only. It is not production authorization.

No minimum positive yield is required. A result of zero incremental QIDs across R1/R2/R3 is fully acceptable if measured and retained correctly.

## Execution ownership

For SLICE-0021 execution:

- **Claude Code** MAY perform the strictly bounded live Wikidata acquisition defined by R0–R3 because the source is already cleared and the live query shapes are fixed by this accepted contract.
- Claude Code MUST NOT broaden the external acquisition/research beyond R0–R3.
- Claude Code owns repository implementation/integration, retained artifacts, deterministic computation, tests and local validation in its assigned slice branch/worktree.
- **ChatGPT** performs independent review/orchestration of the retained route results, source-rights gate behavior, identity-signal semantics, scope/reproducibility and exact-head CI.
- **The project owner** alone provides explicit final acceptance.

The normal single-writer slice-worktree rule remains in force.

## Explicitly out of scope

- manufacturer permission/partnership outreach;
- manufacturer archive adapter work;
- another external source family;
- Wikipedia/PetScan/DBpedia acquisition;
- SailboatData acquisition/evidence;
- broad Tier-1/Tier-2 technical enrichment;
- keel/rudder/skeg/material/rig enrichment;
- review-queue resolution campaigns;
- canonical identity admission/correction;
- production Wikidata discovery-query changes;
- query engine/API/frontend;
- marketplace/listing ingestion;
- accounts/saved queries/alerts/monitoring;
- price-history work;
- SLICE-0022 creation or start.

## Acceptance criteria

- [ ] exactly four fixed live query routes R0–R3 are implemented and no additional discovery route is executed;
- [ ] the existing Wikidata source-rights gate passes before the first network request, or the slice performs zero requests and becomes `BLOCKED`;
- [ ] no source other than Wikidata structured data is acquired;
- [ ] every route is hard-capped at 3,000 results and a ceiling hit is explicitly marked possibly truncated;
- [ ] accepted SLICE-0017/0018 manifests are fingerprinted before acquisition and remain byte-unchanged;
- [ ] the retained historical direct-discovery universe is hard-asserted at exactly 1,829 QIDs;
- [ ] the accepted AUTO_ADMIT comparison universe is hard-asserted at exactly 1,770 BoatModels;
- [ ] current R0 drift versus the historical 1,829 set is measured and reported separately;
- [ ] R1/R2/R3 incremental yield is computed against **current R0**, not merely the historical 1,829 set;
- [ ] full bounded QID sets are retained for R0–R3 with deterministic digests;
- [ ] exact query text/version/digests and acquisition/access telemetry are retained;
- [ ] pairwise/cross-route overlap and unique alternative-route contributions are measured;
- [ ] entity-detail acquisition is deterministic and capped at <=75/alternative route and <=200 unique QIDs globally;
- [ ] sampled entity acquisition contains identity-relevant structured fields only;
- [ ] identity-signal matching uses QID first, then exact retained labels/aliases only;
- [ ] string normalization is exactly surrounding-whitespace trim + casefold;
- [ ] no fuzzy matching, internal-whitespace collapsing, punctuation rewriting, manufacturer-prefix manipulation, token reordering or generation collapsing occurs;
- [ ] ambiguous exact signals remain unresolved rather than forced;
- [ ] `no_exact_identity_signal` is explicitly documented as not proving global novelty/admission safety;
- [ ] every R3 candidate remains repair/review-bound in this slice;
- [ ] no canonical HullQ row is created/modified/deleted and no HullQ ID is minted for incremental candidates;
- [ ] no accepted SLICE-0017/0018 crosswalk or retained artifact is modified;
- [ ] the production Wikidata adapter's accepted default discovery query remains unchanged;
- [ ] normal CI performs no live Wikidata acquisition;
- [ ] retained live results can be validated/recomputed offline;
- [ ] zero incremental yield is explicitly accepted as a valid result;
- [ ] the completion report distinguishes current-direct drift from alternative-route yield and gives an evidence-derived disposition for R1–R3;
- [ ] independent review is completed before owner acceptance;
- [ ] the slice remains `REVIEW`, `BLOCKED` or `IN_PROGRESS` at implementation handoff and is never self-marked `DONE`;
- [ ] explicit project-owner acceptance is required before closure to `DONE`;
- [ ] SLICE-0022 is not created or started.

## Mandatory completion report

At handoff, report at minimum:

1. exact branch HEAD SHA and changed files;
2. confirmation of rights-gate outcome before first request;
3. immutable input-manifest SHA256 values and asserted 1,829 / 1,770 counts;
4. R0 current-direct count and drift breakdown;
5. R1/R2/R3 result counts, ceiling flags and incremental counts versus current R0;
6. cross-route overlap/unique-contribution metrics;
7. detail-sample counts and cap proof;
8. sampled identity-signal category totals;
9. retained artifact paths and deterministic digests;
10. confirmation accepted 0017/0018 artifacts and canonical data were not modified;
11. local validation/tests and coverage where applicable;
12. remote CI status on the exact pushed head;
13. evidence-derived R1/R2/R3 dispositions;
14. explicit confirmation no production discovery rule was changed and SLICE-0022 was not created/started.

## Handoff rule

Claude Code may hand SLICE-0021 back only as `REVIEW`, `BLOCKED` or `IN_PROGRESS`.

It MUST NOT merge its own PR, mark the slice `DONE`, create/start SLICE-0022, or begin a later production expansion automatically.
