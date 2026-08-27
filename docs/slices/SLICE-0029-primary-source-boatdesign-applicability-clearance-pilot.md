# SLICE-0029 — Primary-Source BoatDesign Applicability & Conditional-Clearance Pilot

**ID:** SLICE-0029  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0028 owner-accepted / DONE (Project Owner acceptance recorded on PR #81, issue comment `5437718329`)  
**Blocks:** any trustworthy promotion of SLICE-0028 BoatModel-scoped technical evidence into canonical BoatDesign baselines / FieldResolution decisions

## Objective

Resolve the next semantic and source-rights blocker between the accepted SLICE-0028 full-boundary technical evidence and canonical searchable technical data.

SLICE-0028 established rights-cleared Wikidata technical evidence for all 1,770 canonical BoatModels, but deliberately did **not** infer BoatDesign generations, create FieldResolution decisions or write canonical technical values. Under the accepted HullQ identity model, a BoatModel is a commercial lineage while canonical technical baselines belong to technically coherent BoatDesign generations. Therefore BoatModel-scoped evidence MUST NOT be promoted blindly when generation, variant or factory-option applicability is unresolved.

This slice tests that boundary on a deliberately small, difficult, high-information primary-source sample rather than forcing early searchability.

The fixed pilot BoatModels are the two exact manufacturer-overlap cases already retained by SLICE-0019:

```text
Catalina 22  — Wikidata Q5051252
Catalina 30  — Wikidata Q5051253
```

Both are already within the accepted 1,770 canonical BoatModel boundary and therefore also within the SLICE-0028 full-boundary acquisition. Catalina's official archive is a useful stress case because the retained/current official source surface exposes generation/variant/option signals rather than one obviously flat technical profile.

The slice has two linked research questions:

1. Can the already-reviewed Catalina official primary-source surfaces be cleared, under the existing accepted Source Rights Policy, for **bounded manual use of discrete factual identity/technical facts** while automated ingestion, bulk bootstrap and source-artifact redistribution remain fail-closed?
2. If so, what can those primary-source facts establish about BoatDesign generation / option applicability for the two fixed canonical BoatModels, and which SLICE-0028 technical candidates, if any, are demonstrably safe to consider in a later canonical BoatDesign promotion slice?

This slice is **not** the canonical promotion itself. A valid result may be that zero fields / zero BoatModels are safely promotable yet.

## Why this slice exists

The accepted identity model requires:

```text
BoatModel = continuous commercial model lineage
BoatDesign = technically coherent production generation
DesignOption = concurrent factory-supported technical choice
ResolvedConfiguration = BoatDesign baseline + applicable option/variant effects
```

A technical value observed against a BoatModel-level source identity does not prove which BoatDesign generation or factory option it describes.

Examples of prohibited shortcuts include:

- treating the absence of an explicit `Mk` qualifier as proof that a BoatModel has only one generation;
- creating a new BoatDesign merely because two sources report different dimensions;
- flattening shallow/wing/fin keel choices into a single baseline scalar;
- assuming a Wikidata value applies to every production year/version of a commercial model;
- choosing the most common or most convenient value merely to make Search work sooner.

Quality and semantic correctness outrank speed-to-UI in this slice.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `CLAUDE.md`;
- `docs/slices/SLICE-0028-acceptance-closure.md` plus Project Owner acceptance on PR #81;
- `research/stage3/sl0028-wikidata-tier1-full-boundary/` only for the two fixed QIDs/BoatModels and the five existing Tier-1 fields;
- `research/manufacturers/overlap_result.json`;
- `research/manufacturers/REPORT.md` only where needed for the fixed Catalina source/pilot context;
- `research/manufacturers/archive_clearance/archive_source_clearance.json` only for the retained Catalina clearance row;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- `specs/SOURCE_SCHEMA.v0.2.json`;
- `src/hullq/sources/rights.py` only if a source-record/gate change is required by the evidence-backed clearance result;
- `specs/IDENTITY_MODEL.v0.2.md`;
- `specs/BOAT_DESIGN_SCHEMA.v0.5.json`;
- accepted OQ-003 / provenance semantics only where needed to classify BoatDesign generation, option and technical applicability.

Do not preload unrelated frontend, SEO, market, account, alert, pricing, monetization or query-engine documents.

## Evidence/reporting law

All factual completion-report claims MUST be evidence-backed by actually executed commands, retained artifacts, repository state or actually observed external checks.

- Do not report an expected or inferred result as measured fact.
- Do not mark an acceptance criterion passed unless it was actually verified.
- If an external/current source condition cannot be verified, report `NOT VERIFIED` / `BLOCKED` as appropriate.
- If source rights remain unresolved, do not reinterpret `conditional` as `allowed` merely to advance the slice.
- A negative research result can satisfy this slice if it is correctly measured, retained and reported.
- The implementation agent's report is not independent review and does not make the slice `DONE`.

## Fixed identity and evidence boundary

The pilot identity set is exactly:

```text
Q5051252  Catalina 22
Q5051253  Catalina 30
```

These exact overlaps are already retained in `research/manufacturers/overlap_result.json` and were matched by exact preferred-label equality only. Do not perform fuzzy matching, source-ID reminting, identity expansion or new BoatModel admission.

Before any source work, reproduce and retain the exact mapping from these QIDs to their accepted canonical HullQ BoatModel IDs from the accepted SLICE-0017/0018 identity artifacts / SLICE-0028 linkage.

Do not change:

- either BoatModel ID;
- any historical QID -> HullQ-ID mapping;
- the accepted 1,770 canonical BoatModel count;
- the accepted 1,772 historical registry count.

## Existing source-rights state entering the slice

The retained SLICE-0020 Catalina assessment currently establishes, in substance:

```text
research_reference     allowed
research_lead          allowed
identity_seed          conditional
production_value       conditional
automated_ingestion    unknown
bulk_bootstrap         legal_review_required
artifact_redistribution legal_review_required
```

The source is publicly accessible and official, but no explicit open licence or blanket automated/bulk reuse permission was established by the retained review.

`SOURCE_RIGHTS_POLICY.v0.1.md` section 6.6 nevertheless permits a conservative source-specific path for **discrete factual values from an unlicensed primary factual source** when all required conditions are positively established.

This slice exists to resolve that conditional path for the tightly bounded use case below. It MUST NOT generalize a positive result into automated/bulk Catalina ingestion.

## Fixed external-source boundary

External research is limited to official Catalina Yachts primary-source surfaces on the Catalina-controlled website that are necessary to resolve the two fixed BoatModels and source-use conditions.

Permitted source-surface classes:

- official Catalina brochure archive/index;
- official Catalina brochure/specification documents for the two fixed BoatModels and directly relevant named generations/options;
- official Catalina history/current model pages when directly relevant;
- official Catalina terms/privacy/copyright/access/robots or comparable policy surfaces needed to assess the intended use.

Do not use SailboatData, Wikipedia article text, broker listings, forums, owner posts, search-result snippets or third-party specification databases as evidence for a positive source-rights or BoatDesign decision in this slice.

Search engines MAY be used only to navigate to an official Catalina-controlled source surface; the search result itself is not evidence.

### Retrieval ceiling

This is bounded manual research, not an adapter or bulk ingestion campaign.

Maximum external Catalina retrievals for the whole slice:

```text
25
```

Count each independently fetched HTML page or PDF/document once. Redirects/retries caused by tooling need not be counted as a new semantic source retrieval if they do not retrieve a distinct source document, but the final retained log must make the measured boundary understandable.

Do not create a generalized Catalina crawler, scraper, HTML parser or automated archive adapter.

## Source-rights resolution rule

Evaluate the intended source uses separately. Do not collapse access and reuse rights.

For a positive **bounded manual identity_seed / production_value** clearance under SR-6.6, retain evidence addressing every required condition:

1. the source surface is lawfully/publicly accessible;
2. HullQ reuses only discrete factual/technical facts, not expressive brochure prose, photography, drawings, layout or media;
3. provenance/citation metadata is retained;
4. no identified source term/access restriction prohibits the chosen bounded manual research method;
5. the pilot is not systematic/bulk database extraction;
6. no automated extraction is used unless separately cleared.

A missing or unresolved condition means the affected use stays `conditional`, `legal_review_required`, `unknown` or `blocked` as the evidence requires.

### Positive-clearance scope guardrail

If the evidence supports promotion of Catalina `identity_seed` and/or `production_value` to `allowed`, the retained/source-record notes MUST make the scope explicit:

```text
bounded manually curated discrete factual use only
```

A positive result MUST NOT change the existing posture for:

```text
automated_ingestion
bulk_bootstrap
artifact_redistribution
```

unless this slice independently obtains explicit evidence for that exact use. Those broader uses are not an objective of SLICE-0029 and should remain fail-closed by default.

If a schema-valid production Source record is created/updated from a positive clearance result, it must pass the existing deterministic source-use gate for the uses actually approved and remain non-allowing for uses not approved.

Do not weaken `src/hullq/sources/rights.py` merely to convert `conditional` into `allowed`. A positive source record must represent an evidence-backed reviewed decision, not bypass the gate.

## Source-material retention boundary

Do not vendor Catalina brochure PDFs, screenshots, images or page HTML into the repository unless redistribution rights are independently established.

Retain only what is needed for audit and reproducibility, such as:

- canonical source URL;
- document/page title or stable identifier when available;
- access/review date;
- concise description of the discrete fact inspected;
- source fingerprint/hash only when lawfully/reliably obtainable without vendoring the content;
- non-expressive extracted factual values when the source-use clearance permits their retention;
- evidence explaining the rights decision.

Do not copy expressive source prose into retained reports beyond the minimum quotation allowed by normal review practice; prefer paraphrase and factual extraction.

## BoatDesign applicability research

For each of the two fixed BoatModels, inspect only evidence necessary to classify the relationship between the commercial BoatModel lineage and technically coherent production generations/options.

Retain, where positively evidenced:

- manufacturer generation labels (`Mk I`, `Mk II`, etc.);
- production-year or hull-number boundaries;
- explicit statements of redesign/change that establish a persistent technical baseline change;
- concurrent factory keel/draft/rig or other options relevant to the five existing Tier-1 fields;
- named variants only when they matter to technical applicability or identity;
- exact source surfaces supporting each fact.

Do not infer a generation merely from a label. OQ-003 / `IDENTITY_MODEL.v0.2.md` controls the distinction:

- persistent/non-optional redesign with an evidence-backed boundary -> BoatDesign candidate;
- concurrent factory choice -> DesignOption candidate;
- named version alone -> not proof of BoatDesign;
- measurement disagreement alone -> not proof of BoatDesign.

### No absence-as-proof rule

The absence of a discovered second generation/option MUST NOT be treated as proof that the model is single-generation or option-free.

A model/field may be classified safely only from positive evidence sufficient for the claimed applicability.

## SLICE-0028 technical-candidate applicability

For the two fixed QIDs, reuse the accepted retained SLICE-0028 raw/evidence manifest and normalized candidates. Do not reacquire Wikidata merely because the data is convenient to fetch again.

For each of the five existing field pointers:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

classify the current BoatModel-scoped SLICE-0028 evidence into an applicability outcome using positive primary-source evidence only:

```text
SAFE_FOR_LATER_DESIGN_PROMOTION
MODEL_SCOPE_ONLY_NOT_PROMOTABLE
GENERATION_AMBIGUOUS
OPTION_SENSITIVE
SOURCE_VALUE_CONFLICT
INSUFFICIENT_EVIDENCE
NO_NORMALIZED_WIKIDATA_CANDIDATE
RIGHTS_BLOCKED
```

The classifier/report may refine names if necessary, but the states must remain explicit, mutually understandable and fail-closed.

`SAFE_FOR_LATER_DESIGN_PROMOTION` means only that the evidence is sufficiently scoped for a **later separately readied canonical promotion slice**. It does not itself create a canonical value or FieldResolution.

A field MUST NOT be marked safe merely because the Wikidata value equals a Catalina value. Equality can be a useful diagnostic but is not, by itself, proof of design-generation applicability.

## Canonical mutation boundary

SLICE-0029 MUST create/mutate **zero** canonical production identities or technical values.

Specifically prohibited:

- minting a BoatDesign ID;
- inserting/updating a canonical BoatDesign row;
- modifying a BoatModel row;
- creating a FieldResolution;
- writing a canonical baseline technical value;
- creating DesignOption/NamedVariant canonical entities;
- modifying the 1,770 / 1,772 accepted identity boundary;
- implementing Search/API/frontend behavior.

The purpose is to make the next canonical promotion decision evidence-based rather than premature.

## Retained package

Retain the bounded research package under:

```text
research/stage3/sl0029-primary-source-boatdesign-applicability/
```

At minimum include:

- `pilot_identity_boundary.json` — exact two-QID -> canonical BoatModel linkage and accepted-input references;
- `source_retrieval_log.json` — bounded official-source retrieval accounting;
- `source_clearance_assessment.json` — use-specific evidence and final source-use result;
- `boatdesign_applicability.json` — generation/option/applicability findings for both fixed models;
- `wikidata_candidate_applicability.json` — five-field applicability classifications against retained SLICE-0028 candidates;
- `REPORT.md` — concise measured result and next-step recommendation;
- JSON schemas for every retained JSON artifact;
- `ARTIFACT-DIGESTS.json` + schema covering the retained package except the digest file itself.

If the implementation architecture uses different filenames, preserve equivalent machine-readable separation of identity boundary, retrieval accounting, rights decision, BoatDesign applicability and field applicability.

Do not modify accepted SLICE-0019/0020/0028 retained packages.

## Deterministic next-step recommendation

The retained report must produce exactly one top-level recommendation:

```text
READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
RIGHTS_CLEARANCE_BLOCKED
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

Use this rule:

### `READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT`

Only when:

- the source-use decision positively clears every Catalina use actually needed to support the proposed later promotion path;
- at least one of the two fixed BoatModels has a positively evidenced BoatDesign-generation/applicability boundary sufficient for canonical modeling under OQ-003 / `IDENTITY_MODEL.v0.2.md`;
- at least one of the five retained SLICE-0028 normalized technical candidates for that BoatModel is classified `SAFE_FOR_LATER_DESIGN_PROMOTION`;
- no unresolved rights/applicability condition contradicts that safe candidate.

### `RIGHTS_CLEARANCE_BLOCKED`

When the required source use cannot be positively cleared under the accepted Source Rights Policy, regardless of technical evidence quality.

### `APPLICABILITY_EVIDENCE_INSUFFICIENT`

When the necessary source use is cleared but the bounded primary-source evidence still cannot safely scope any retained SLICE-0028 technical candidate to a BoatDesign generation/configuration.

Do not invent a threshold or reinterpret a negative result to force the first recommendation.

## Required implementation behavior

1. Reproduce the exact two-QID / canonical-BoatModel pilot identity boundary from accepted retained artifacts.
2. Reuse retained SLICE-0028 technical evidence; no unnecessary Wikidata reacquisition.
3. Reassess the fixed official Catalina source only within the external-source and retrieval ceiling above.
4. Resolve source uses independently under the accepted Source Rights Policy; do not weaken the gate.
5. Preserve non-allow states for automation/bulk/redistribution unless explicit evidence genuinely supports otherwise.
6. Retain no unauthorized source artifacts.
7. Apply OQ-003 identity rules to generation vs option vs named-variant distinctions.
8. Treat absence and disagreement as uncertainty, not proof.
9. Produce field-level applicability for exactly the five existing Tier-1 fields.
10. Create/mutate zero canonical BoatModel/BoatDesign/FieldResolution/technical production values.
11. Produce exactly one deterministic next-step recommendation from the rule above.
12. Keep every measured claim reproducible from retained inputs/logs plus explicitly identified external source checks.

## Validation requirements

Run the normal repository gates required by `CLAUDE.md` plus focused validation for every new/changed deterministic artifact builder or rights/applicability classifier.

At minimum, where applicable:

```text
uv run python scripts/validate_repository.py
uv run ruff check .
uv run mypy src
uv run pytest
```

Also provide a deterministic offline verification command for the retained SLICE-0029 package that validates:

- two-QID identity boundary integrity;
- retrieval count ceiling;
- source-use decision consistency with retained inputs;
- applicability-state vocabulary/invariants;
- no unexpected field outside the five allowed pointers;
- recommendation recomputation;
- artifact digests.

The offline verifier MUST NOT require live Catalina or Wikidata access after the retained research package is created.

If a required external fact cannot lawfully be retained in sufficient form for offline verification, retain the source locator + measured decision input and make the verifier check internal package consistency without pretending to reconstruct the external page content.

## Remote verification

Before final handoff, push the implementation branch and observe the required remote CI on the **exact final HEAD SHA**.

Also observe Manufacturer artifact reproducibility on the exact final HEAD when triggered by the repository workflow.

If either required remote result is not observed, report `NOT VERIFIED` rather than PASS.

Do not commit another change merely to record a CI run unless the contract explicitly requires such a commit.

## Acceptance criteria

SLICE-0029 is ready for independent review when all of the following are truthfully satisfied or explicitly reported `BLOCKED` where the research result requires it:

- [ ] exact pilot identity boundary reproduces `Q5051252` / `Q5051253` and their accepted canonical BoatModel IDs;
- [ ] retained SLICE-0028 evidence is reused rather than silently reacquired/reinterpreted;
- [ ] Catalina external research remains within the fixed official-source boundary and <=25 retrieval ceiling;
- [ ] source-rights decision addresses all SR-6.6 conditions and each relevant use separately;
- [ ] no conditional/unknown/legal-review state is silently treated as allowed;
- [ ] no automated/bulk/redistribution scope is broadened without explicit supporting evidence;
- [ ] source material retention obeys SR-007 / repository policy;
- [ ] both fixed BoatModels receive explicit generation/option/applicability findings;
- [ ] all five existing Tier-1 fields receive a fail-closed applicability outcome per fixed BoatModel;
- [ ] no canonical BoatDesign, DesignOption, NamedVariant or FieldResolution is created;
- [ ] no canonical technical value is written;
- [ ] accepted 1,770 BoatModel / 1,772 historical mapping boundary remains unchanged;
- [ ] retained package validates offline and integrity digests pass;
- [ ] normal local repository validation passes or any failure is explicitly reported;
- [ ] exact final HEAD is reported;
- [ ] required remote exact-head CI/reproducibility is actually observed or explicitly `NOT VERIFIED`;
- [ ] exactly one next-step recommendation is mechanically reproduced;
- [ ] slice remains `REVIEW` or `BLOCKED`, never `DONE`.

## Explicit non-goals

SLICE-0029 does **not**:

- build Search;
- resolve OQ-009 query semantics;
- create API/frontend behavior;
- create canonical BoatDesigns;
- create FieldResolutions;
- expand the canonical BoatModel universe;
- run another full-boundary Wikidata crawl;
- build a generalized Catalina adapter;
- authorize manufacturer/archive bulk ingestion;
- assume that public availability equals production reuse permission;
- declare CAL-01 D2 basic-searchable coverage;
- set launch-readiness thresholds;
- start SLICE-0030.

## Handoff

At completion, leave SLICE-0029 in `REVIEW` or `BLOCKED` and return the standard concise completion report required by `docs/slices/SLICE_TEMPLATE.md`, including:

- exact final HEAD SHA;
- changed files;
- external retrieval count and exact official source surfaces used;
- final use-specific Catalina rights result;
- exact BoatDesign/applicability findings for Catalina 22 and Catalina 30;
- field-level safe/not-safe counts and reasons;
- deterministic next-step recommendation;
- local validation summary;
- exact-head remote CI / reproducibility state;
- unresolved findings / scope deviations;
- explicit confirmation of zero canonical mutation.
