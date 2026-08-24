# SLICE-0020 — Manufacturer Archive Source Clearance & Identity-Expansion Pilot Report

**Review date:** 2026-08-24
**Slice status at handoff:** REVIEW

## Research ownership boundary

This slice splits research and repository work across two explicit roles, per
`docs/slices/SLICE-0020-manufacturer-archive-source-clearance-identity-expansion-pilot.md`
("Research ownership and orchestration boundary"):

- **ChatGPT-led external research pass** — visited the ten fixed-sample manufacturer/heritage
  archive surfaces, read terms-of-service/legal-notice/robots evidence where retrievable, and
  discovered the bounded model-identity sample. All source-clearance findings, evidence URLs,
  and the 100 source-presented model names in this report and its retained artifacts originate
  from that external pass, supplied into this repository integration workflow.
- **Claude repository integration** — transcribed the supplied findings into the accepted
  schema/data structure (`archive_source_clearance_schema.json` / `archive_source_clearance.json`),
  wrote and ran a deterministic, repository-local overlap computation
  (`compute_overlap.py`) against the accepted SLICE-0017/0018 AUTO_ADMIT union, validated both
  retained JSON documents against strict Draft 2020-12 schemas, wrote and ran the pytest
  reproducibility/invariant suite (`tests/unit/test_slice_0020_archive_clearance.py`), and wrote
  this report. **Claude performed no independent external web research for this slice** — it did
  not browse the ten sources, and did not invent, upgrade, or replace any supplied rights finding.

## Executive result

| Classification | Count |
| --- | --- |
| `ADAPTER_READY` | **0** |
| `RESEARCH_ONLY` / `REVIEW_REQUIRED` | **9** |
| `BLOCKED` | **1** (Bénéteau) |

A truthful result of zero `ADAPTER_READY` sources is a fully valid, expected outcome of this
slice per the slice's own "Classification vocabulary" section. It is **not** characterized as a
failure here, and it was not padded to avoid reporting it: none of the ten sources had both
`identity_seed = allowed` and `automated_ingestion = allowed`, which is the minimum gate for
`ADAPTER_READY` under the slice's hardened test. Nine sources remain usable for
research-reference/research-lead/bounded-discovery purposes only, and one source (Bénéteau) is
`BLOCKED` outright.

**Bénéteau is `BLOCKED`** because its retained Terms of Use (`www.beneteau.com/pt-br/condicoes-de-uso`)
explicitly state that no element of the site may be used, reproduced, represented, distributed,
decompiled, indexed or extracted by any technical protocol without prior written consent, and
separately prohibit permanent or temporary extraction of all or a qualitatively/quantitatively
substantial portion of the site's databases. This is explicit negative evidence directly on point
for the contemplated automated archive-adapter use, distinct from ordinary copyright-notice
language, and is recorded here as `automated_ingestion = prohibited`, `bulk_bootstrap = prohibited`.

## Methodology

For each of the ten fixed-sample sources, the external research pass recorded, separately:

1. **access evidence** — public-readability status (public / registration-required / paywalled /
   unknown) plus the evidence surface(s) it was observed on;
2. **rights evidence** — terms-of-service / licence / copyright-notice evidence where identifiable,
   or explicitly `null`/unknown where none was found;
3. **automation evidence** — robots.txt / API / automation-relevant evidence. Per the general
   rights rule supplied with this pass, individual robots.txt contents were **not retained** as
   reliable evidence during the ChatGPT pass, so this field defaults to
   `unknown_unretrieved` for every source except Bénéteau, whose Terms of Use explicitly name
   "technical protocol" indexing/extraction as prohibited (`explicit_prohibition_via_terms`).
   No source's automated/API posture was inferred from search-engine indexing, sitemap presence,
   public HTML availability, or manufacturer prestige.

Access/automation evidence and rights/reuse evidence are recorded in visibly separate JSON object
fields (`access_evidence`, `rights_evidence`, `automation_evidence`) in
`archive_source_clearance.json`, per SR-001 and the slice's explicit separation requirement, so a
later reviewer can see which half of the assessment is the actual blocker for any non-cleared use.

Each source then received a **use-specific decision** for all seven accepted HullQ clearance keys
(`research_reference`, `research_lead`, `identity_seed`, `production_value`,
`automated_ingestion`, `bulk_bootstrap`, `artifact_redistribution`), using the
`SOURCE_RIGHTS_POLICY.v0.1` §5 vocabulary (`allowed`, `conditional`, `legal_review_required`,
`prohibited`, `unknown`), and an overall `systematic_use_status`
(`CLEARED`/`REQUIRES_REVIEW`/`BLOCKED`/`UNKNOWN`). No source's `systematic_use_status` was set to
`CLEARED` merely because a page was publicly viewable — none of the ten reached `CLEARED`.

The `adapter_classification` for every source is additionally accompanied by a recomputed,
machine-checkable `adapter_ready_test` object (see `archive_source_clearance.json`) recording
whether `identity_seed = allowed`, whether `automated_ingestion = allowed`, whether any
independently relevant access/permission field contradicts either clearance, and whether
`bulk_bootstrap = allowed` (or bounded/non-bulk conditions are documented) — so
`ADAPTER_READY` is never asserted without a checkable basis, consistent with the SLICE-0007
permission-conflict style of check.

## The ten fixed-sample sources

Cross-check: all ten targets already have a SLICE-0019 `research/manufacturers/registry.json`
background record (Catalina Yachts, Pearson Yachts, Oyster Yachts, Westerly Marine, Bénéteau,
Wauquiez, Elan d.o.o., Cantiere del Pardo, Hallberg-Rassy, Seawind Catamarans). Those records were
used only as background/cross-check context, consistent with the slice's rule that a SLICE-0019
record does not itself satisfy this slice's use-specific clearance or identity-pilot
requirements — this slice performed its own use-specific assessment for all ten.

### 1. Catalina Yachts — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `www.catalinayachts.com/brochure-archives/`, `/history/`, `/sport-series/`
- Access: public. Rights: no explicit open licence or bulk-reuse permission found. Automation:
  `unknown_unretrieved`.
- `identity_seed = conditional`, `production_value = conditional`, `automated_ingestion = unknown`,
  `bulk_bootstrap = legal_review_required`, `artifact_redistribution = legal_review_required`.

### 2. Pearson Yachts — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `www.pearsonyachts.org/`, `/pearson-sailboats.html`, `/models/pearson-26od.html`
- Volunteer/non-profit owners archive for the defunct Pearson Yachts Corporation; mixed
  original-factory/owner-contributed material (footer: Copyright ©2020 All Rights Reserved) means
  factory documents and owner material must not be treated as one open-licensed dataset.
- `identity_seed = conditional`, `production_value = legal_review_required`,
  `automated_ingestion = unknown`, `bulk_bootstrap = legal_review_required`,
  `artifact_redistribution = legal_review_required`.

### 3. Oyster Yachts — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `oysteryachts.com/heritage-yachts/`, `/heritage-yachts/oyster-46/`,
  `/heritage-yachts/oyster-545/`
- Official heritage catalogue explicitly describing 46 heritage models; current footer © 2026
  OYSTER YACHTS; no open data licence or automated/bulk permission found.
- `identity_seed = conditional`, `production_value = conditional`, `automated_ingestion = unknown`,
  `bulk_bootstrap = legal_review_required`, `artifact_redistribution = legal_review_required`.

### 4. Westerly Marine / Westerly Owners Association — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `wiki.westerly-owners.co.uk/index.php?title=Main_Page`,
  `westerly-owners.co.uk/terms-and-conditions/`
- Owners-association-sponsored wiki; WOA Terms state contributions are published for members'
  interest and are **not validated by WOA**; mixed original-factory/association/contributor
  rights remain material.
- `identity_seed = conditional`, `production_value = legal_review_required`,
  `automated_ingestion = unknown`, `bulk_bootstrap = legal_review_required`,
  `artifact_redistribution = legal_review_required`.

### 5. Bénéteau — `BLOCKED`

- Evidence surfaces: `www.beneteau.com/pt-br/condicoes-de-uso`,
  `/en-us/heritage-sailing-yachts/first-1977-1983`, `/en-us/first-1977-1983/first-18`
- Retained Terms of Use explicitly prohibit technical-protocol indexing/extraction and
  substantial-portion database extraction without prior written consent. Manual research-reference
  use remains distinct from automated production acquisition and stays `allowed`; every
  automated/bulk use is `prohibited`.
- `identity_seed = legal_review_required`, `production_value = legal_review_required`,
  `automated_ingestion = prohibited`, `bulk_bootstrap = prohibited`,
  `artifact_redistribution = prohibited`.

### 6. Wauquiez — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `www.wauquiez.com/une-grande-histoire/`, `/mention-legales/`
- Official legal notice prohibits reproduction/distribution/modification/adaptation/
  retransmission/publication without express written consent; this is ordinary copyright
  reproduction language, not an explicit technical-indexing prohibition, so it is recorded as
  `artifact_redistribution = prohibited` while automated ingestion remains `unknown` rather than
  `prohibited` (contrast with Bénéteau's explicit technical-protocol language).
- `identity_seed = conditional`, `production_value = legal_review_required`,
  `automated_ingestion = unknown`, `bulk_bootstrap = legal_review_required`,
  `artifact_redistribution = prohibited`.

### 7. Elan — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `www.elan-yachts.com/en/previous-models`, `/en/carbon/history`
- Official Previous Models and company-history surfaces; no open data licence or automated/bulk
  permission found.
- `identity_seed = conditional`, `production_value = conditional`, `automated_ingestion = unknown`,
  `bulk_bootstrap = legal_review_required`, `artifact_redistribution = legal_review_required`.

### 8. Cantiere del Pardo / Grand Soleil — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `old2.grandsoleil.net/history/`, `www.grandsoleil.net/it/privacy-policy/`,
  `/blogs/sailing-stories/sara-nocella-blu-grand-soleil-34`
- Official heritage history (from 1973) identifies successive model ranges; current Privacy Policy
  identifies Cantiere del Pardo as controller but is not a content-reuse licence.
- `identity_seed = conditional`, `production_value = conditional`, `automated_ingestion = unknown`,
  `bulk_bootstrap = legal_review_required`, `artifact_redistribution = legal_review_required`.

### 9. Hallberg-Rassy — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `oldshop.hallberg-rassy.com/contents/en-us/d291_...html`,
  `/contents/en-us/p1378_...html`, `www.hallberg-rassy.com/`
- Official manufacturer/parts surfaces expose a broad historical/current model list; historical
  newsletters grant a narrow permission to quote the newsletter with attribution — **this narrow
  permission is not generalized into an open licence for the whole manufacturer site/database**.
- `identity_seed = conditional`, `production_value = conditional`, `automated_ingestion = unknown`,
  `bulk_bootstrap = legal_review_required`, `artifact_redistribution = legal_review_required`.

### 10. Seawind Catamarans — `RESEARCH_ONLY` / `REVIEW_REQUIRED`

- Evidence surfaces: `www.seawindcats.com/our-catamarans`,
  `/blog/seawind-catamarans-40-years-of-sailing-excellence/`, `/benefits-of-a-catamaran/`,
  `/?terms-and-privacy=yes`
- Official current catalogue and 40-year history page are public; a "Terms & Privacy" link exists
  but its content **could not be reliably retrieved** during the external pass, so it is recorded
  as `unknown` rather than guessed in either direction.
- `identity_seed = conditional`, `production_value = conditional`, `automated_ingestion = unknown`,
  `bulk_bootstrap = legal_review_required`, `artifact_redistribution = legal_review_required`.

## Bounded identity-pilot results

Exactly 10 source-presented model identities were retained per source (100 total), within the
20-per-source / 200-total contract cap. Matching used exact/unambiguous-first comparison only
(case-insensitive, whitespace-normalized) against the accepted SLICE-0017/0018 union of
**1,770** AUTO_ADMIT BoatModel candidates (965 from `research/bootstrap/wikidata/manifest.json` +
805 from `research/bootstrap/wikidata/sl0018-2500/manifest.json`, verified disjoint by
`hullq_id`). No fuzzy matching, manufacturer-prefix insertion/removal, token reordering,
punctuation rewriting, or generation collapsing was performed.

| Source | Retained | `exact_overlap` | `no_exact_overlap_signal` | `unresolved_possible_overlap` |
| --- | --- | --- | --- | --- |
| Catalina Yachts | 10 | 5 | 5 | 0 |
| Pearson Yachts | 10 | 3 | 7 | 0 |
| Oyster Yachts | 10 | 0 | 10 | 0 |
| Westerly Marine | 10 | 0 | 10 | 0 |
| Bénéteau | 10 | 0 | 10 | 0 |
| Wauquiez | 10 | 0 | 10 | 0 |
| Elan | 10 | 0 | 10 | 0 |
| Cantiere del Pardo / Grand Soleil | 10 | 0 | 10 | 0 |
| Hallberg-Rassy | 10 | 1 | 9 | 0 |
| Seawind Catamarans | 10 | 0 | 10 | 0 |
| **Total** | **100** | **9** | **91** | **0** |

Exact overlaps found: Catalina 16.5, Catalina 18, Catalina 25, Catalina 27, Catalina 28, Pearson
26, Pearson 30, Pearson 303, Hallberg-Rassy 40 — each resolved unambiguously to exactly one
accepted `preferred_label`.

### `no_exact_overlap_signal` — narrow definition (repeated per slice requirement)

Per the slice's exact required wording: **"No exact/unambiguous overlap signal was found against
the accepted comparison universe under this slice's exact-match rules."** This category MUST NOT
be interpreted as: the model identity being globally novel; the identity being safe for canonical
admission; proof that no matching HullQ BoatModel exists (only that this bounded exact-match probe
did not find one); or permission to mint or create a canonical identity. The remaining uses of the
phrase "clearly new" in the SLICE-0019 report's prose style are deliberately **not** reused
unqualified anywhere in this document — this report uses `no_exact_overlap_signal` throughout.

### Overlap guard regression: Bénéteau "First 26"

The accepted SLICE-0018 manifest contains a preferred label `Beneteau First 26` (ASCII, with the
manufacturer name prepended). The source-presented pilot identity is `First 26` (no manufacturer
prefix, as Bénéteau's own heritage archive presents it). These two strings are **not** exactly
equal, so — per the slice's explicit overlap-guard instruction — `First 26` is correctly classified
`no_exact_overlap_signal`, not `exact_overlap`. No manufacturer-prefix insertion was performed to
manufacture a match. This is verified by
`tests/unit/test_slice_0020_archive_clearance.py::test_manufacturer_prefix_overlap_guard_not_upgraded`.

### Zero unresolved cases

This bounded pilot happened to find zero `unresolved_possible_overlap` cases — no source-presented
name's exact-match signal (via preferred label or alias) resolved to more than one distinct
accepted identity. This is a property of the specific 100-name sample, not a general guarantee;
a larger or differently sampled pilot could surface ambiguous cases.

## Identity hazards observed (preserved, not silently resolved)

- **Bénéteau "First N" reused numbering vs. manufacturer-prefixed accepted labels** — the accepted
  universe already contains manufacturer-prefixed forms (e.g. `Beneteau First 26`,
  `Beneteau First 260 Spirit`, `Beneteau First 265`) that are exact strings distinct from the
  source-presented `First 26`. Any future non-exact resolution of "First N" identities against
  the accepted universe would need explicit generation/prefix disambiguation, not silent
  collapsing.
- **Grand Soleil "GS N" abbreviation** — Cantiere del Pardo's own heritage page presents its
  post-Grand-Soleil-34 models as `GS 35`, `GS 41`, `GS 39`, etc., not `Grand Soleil 35` etc. This
  slice preserved the abbreviated form exactly as presented and did not expand `GS` to
  `Grand Soleil` during matching, per the slice's explicit instruction. Any future identity
  resolution work would need to treat `GS N` as a distinct string from any `Grand Soleil N` label
  in the accepted universe.
- **Westerly model names without a "Westerly" prefix** — the Westerly Owners Association wiki
  presents model names (`Berwick`, `Centaur`, `Chieftain`, ...) without a manufacturer prefix. This
  slice did not insert one. Several of these are short common words (`Cirrus`, `Fulmar`) that
  could collide with unrelated non-sailboat Wikidata entries in a differently scoped comparison;
  no such collision was found in this bounded exact-match probe against the accepted universe, but
  the hazard (name genericity) is noted for any future broader resolution pass.
- **Elan "E3" on the "Previous Models" archive surface** — the retained pilot item `Elan E3` was
  found on Elan's "Previous Models" archive page, despite an "E3" designation that plausibly
  denotes a more recent/different production line than the surrounding historical models on that
  same page. This is flagged as an explicit timeline/identity hazard in the retained record's
  `discriminating_context` rather than silently treated as either historical or current.
- **Bénéteau "First 32" / "First 38" era-label mismatch** — these two pilot items were listed
  alongside Bénéteau's heritage index page labeled "First 1977-1983", but their hull sizes are
  larger than the other First-1977-1983-era boats in the sample; per-model era was not
  independently confirmed beyond the page label, and this is recorded explicitly rather than
  assumed.
- **Pearson mixed-rightsholder archive** — `pearsonyachts.org` explicitly blends original factory
  documentation with owner-contributed research; this slice's `production_value` clearance for
  Pearson is `legal_review_required` (not merely `conditional`) specifically because of this
  mixed-provenance hazard.
- **Hallberg-Rassy narrow newsletter permission** — the historical-newsletter quote-with-attribution
  permission is explicitly scoped to that newsletter content and is not generalized to the whole
  manufacturer site/database anywhere in this slice's outputs.

## Repository-local overlap computation (Claude integration work)

The accepted comparison universe was built deterministically by Claude from the two already-
accepted repository manifests, per the slice's required procedure:

```
research/bootstrap/wikidata/manifest.json          -> 965 auto_admit candidates
research/bootstrap/wikidata/sl0018-2500/manifest.json -> 805 auto_admit candidates
union by hullq_id (verified disjoint)              -> 1,770 accepted BoatModels
```

This 1,770 figure is asserted with a hard `assert` in `compute_overlap.py` and re-verified by
`tests/unit/test_slice_0020_archive_clearance.py::test_accepted_comparison_universe_exactly_1770`.
No canonical row was read, created, modified, or admitted anywhere in this process — the union was
computed only in-memory from the two already-committed manifest files for the purpose of this
bounded string-comparison probe.

## Coverage / scope notes

- This slice did not perform, stage, or test any automated fetch, scrape, or bulk request against
  any of the ten sources.
- No SailboatData value was used as production/identity evidence anywhere in this slice's outputs.
- No `bluewater`/`offshore`/`luxury` suitability classification field or value was introduced by
  HullQ anywhere in the retained schemas or the identity-pilot's own `discriminating_context`/
  `classification` fields. (A supplied research finding for Oyster Yachts truthfully quotes that
  manufacturer's own marketing self-description as "46 luxury sailboat models" — a factual report
  of what the source says about itself, not a HullQ-authored suitability classification; SLICE-0019's
  already-accepted `registry.json` contains comparable quoted source-description language.)
- No `research/manufacturers/registry.json`, `registry_schema.json`, `source_yield_study.json`,
  `overlap_result.json`, or `REPORT.md` (accepted SLICE-0019 closure artifacts) was modified.
- No canonical Brand/Organization/BoatModel/BoatDesign row was created, modified, or admitted.

## Recommendation for the next bounded slice (evidence-derived, not started)

Given a measured **zero-`ADAPTER_READY`** result across this fixed ten-source sample, the next
slice must **not** assume a manufacturer-archive production adapter is ready to build. The
evidence supports, instead, one of:

1. **A bounded permission/partnership outreach step** — for one or two of the nine
   `RESEARCH_ONLY`/`REVIEW_REQUIRED` sources with the thinnest actual prohibition (e.g. Catalina,
   Oyster, or Elan, none of which have an explicit technical-extraction prohibition on record,
   unlike Bénéteau or Wauquiez's copyright-reproduction language), seek explicit written
   automated-ingestion/bulk-bootstrap permission and re-run this slice's clearance assessment for
   that source only, before any adapter work is authorized for it.
2. **An alternative-cleared-source Stage-3 direction** — revisit sources whose rights basis is
   already `public_domain`/`CC0`/`CC-BY` under `SOURCE_RIGHTS_POLICY.v0.1` §6.1–6.2 (e.g. further
   Wikidata-adjacent structured sources), rather than manufacturer archives with unresolved
   commercial-reuse terms.

This recommendation is evidence-derived from this slice's own measured 0/9/1 classification
result and from the observed identity-yield/overlap characteristics above. It does **not** start,
authorize, or stage either option; SLICE-0021 is not created.

## Reproducibility and validation

- `research/manufacturers/archive_clearance/build_clearance_data.py` deterministically
  regenerates `archive_source_clearance.json` from the transcribed external-research findings.
- `research/manufacturers/archive_clearance/compute_overlap.py` deterministically regenerates
  `archive_identity_pilot.json` from `archive_identity_pilot_input.py` and the two accepted
  wikidata manifests, with no network access.
- `tests/unit/test_slice_0020_archive_clearance.py` proves the generator chain reproduces the
  committed artifacts byte-for-byte (modulo line-ending style) and pins every numeric/structural
  invariant required by this slice's acceptance criteria (10 sources, 10×10=100 pilot identities,
  1,770 accepted universe, 0/9/1 classification totals, the manufacturer-prefix overlap guard, the
  `GS` non-expansion guard, the Westerly no-prefix guard, zero forced `unresolved_possible_overlap`,
  and aggregate counts matching record-level classifications).
- Both retained JSON documents validate against their Draft 2020-12 `additionalProperties: false`
  schemas.

## Slice disposition

- `ADAPTER_READY = 0`, `RESEARCH_ONLY / REVIEW_REQUIRED = 9`, `BLOCKED = 1` — the true, unpadded
  result of this bounded pilot.
- No production adapter, automated fetch, or broad ingestion was built, staged, or executed.
- No canonical Brand/Organization/BoatModel/BoatDesign row was created, modified, or admitted.
- SLICE-0021 was not created or started.
- This slice hands off in `REVIEW`. It is not marked `DONE` — that requires independent review and
  explicit project-owner acceptance per `CLAUDE.md`.
