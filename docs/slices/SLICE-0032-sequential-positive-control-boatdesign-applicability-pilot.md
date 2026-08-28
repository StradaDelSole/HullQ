# SLICE-0032 — Sequential Positive-Control BoatDesign Applicability Pilot

**ID:** SLICE-0032  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** 3.3 in parallel with still-open Stage 3.2  
**Depends on:** SLICE-0031 owner-accepted / DONE (final closure merged as `673a7216f3222de5913671406a33f5ac7fb9cdb2`; Project Owner acceptance recorded on PR #92, issue comment `5451173464`)  
**Blocks:** the first evidence-backed bounded canonical BoatDesign promotion pilot and any claim that the corrected Tier-1 positive-control pool has demonstrated design-level applicability

## Objective

Use the accepted SLICE-0031 positive-control pool to run one tightly bounded, sequential primary-source applicability pilot whose sole purpose is to determine whether at least one technically strong BoatModel can be scoped safely enough to a BoatDesign generation/configuration for a later separately readied canonical-promotion slice.

SLICE-0031 established that the corrected full-boundary evidence contains 784 eligible positive-control BoatModels and retained a deterministic top-20 pool. The first three retained candidates are:

```text
rank 1  Q104861437  Buzzards Bay 14  -> BM_WDT0_003ba28d4cd143d68c28e57899a3ed73
rank 2  Q104829866  Suspens          -> BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb
rank 3  Q60521258   Hunter 340       -> BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60
```

All three retained SLICE-0031 rows have:

- all five fixed Tier-1 normalized candidates;
- both draft and displacement normalized;
- LWL normalized;
- no retained disagreement/unsupported-coexistence diagnostic;
- corrected precursor satisfied.

These candidates are selected **only because they are ranks 1–3 under the already-accepted SLICE-0031 deterministic ranking**. They are not selected for fame, convenience, presumed source quality, or agent preference.

The pilot is sequential and stop-on-first-positive:

1. assess rank 1;
2. only if rank 1 does not satisfy the fixed positive-control success rule, assess rank 2;
3. only if ranks 1 and 2 do not satisfy it, assess rank 3;
4. stop immediately once one candidate satisfies the positive-control success rule.

A valid final result may still be negative. Do not weaken rights, identity, generation, option, or applicability rules to force a positive result.

This slice does **not** mint a BoatDesign, create a FieldResolution, write canonical technical values, or implement Search/API/frontend behavior.

## Why this slice is next

SLICE-0029 proved on Catalina 22 / Catalina 30 that BoatModel-scoped technical evidence cannot be promoted merely because values exist. Its accepted negative result was:

```text
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

SLICE-0031 then measured the corrected full-boundary Tier-1 evidence profile and produced a deterministic technically strong positive-control pool, explicitly preserving that the pool was evidence-selection only and required a later separately readied BoatDesign/applicability pilot.

The next highest-information step is therefore not another arbitrary model choice and not canonical promotion. It is a bounded attempt to establish a genuine positive design/applicability case from the strongest deterministic candidates while preserving the exact fail-closed lessons of SLICE-0029.

## Controlling artifacts

Read only as needed under `CLAUDE.md` token-efficiency rules:

- `CLAUDE.md`;
- `docs/slices/SLICE-0031-acceptance-closure.md` plus Project Owner acceptance on PR #92;
- `research/stage3/sl0031-corrected-tier1-evidence-profile/positive_control_candidates.json` + schema + digests;
- `research/stage3/sl0031-corrected-tier1-evidence-profile/boatmodel_evidence_profile.json` only for the three fixed candidate rows;
- `research/stage3/sl0028-wikidata-tier1-full-boundary/linkage.json` only to reproduce exact QID -> BoatModel identity and preferred labels;
- `research/stage3/sl0028-wikidata-tier1-full-boundary/evidence_manifest.json` only for retained raw claims for the attempted candidates;
- `research/stage3/sl0030-wikidata-mass-unit-correction/` and current accepted Wikidata extraction semantics to reproduce corrected/current normalized evidence;
- `docs/slices/SLICE-0029-primary-source-boatdesign-applicability-clearance-pilot.md` and `docs/slices/SLICE-0029-acceptance-closure.md` for the accepted applicability/right guardrails and negative-path lessons;
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`;
- `specs/SOURCE_SCHEMA.v0.2.json` only if a source-record representation is actually required;
- `specs/IDENTITY_MODEL.v0.2.md`;
- `specs/BOAT_DESIGN_SCHEMA.v0.5.json`;
- accepted OQ-003 / provenance semantics only as necessary.

Do not preload unrelated frontend, SEO, market, account, alert, pricing, monetization or query-engine documents.

## Evidence/reporting law

All completion-report claims MUST be backed by executed deterministic computation, retained artifacts, repository state, or actually observed bounded source checks.

- Do not infer a BoatDesign generation from a model name, a `Mk`/variant label alone, or measurement disagreement.
- Do not treat absence of a discovered redesign/option as proof of a single-generation or option-free lineage.
- Do not treat equality between a primary-source value and a Wikidata candidate as proof of applicability by itself.
- Do not convert `conditional`, `unknown`, or `legal_review_required` source use into `allowed` without satisfying the accepted policy.
- Do not report source evidence from search-result snippets.
- Do not silently continue to a lower-ranked candidate after a higher-ranked candidate already satisfies the fixed success rule.
- Do not mark the slice DONE; implementation-agent completion only advances to REVIEW.

## Fixed candidate identity boundary

The candidate sequence is a normative constant for this slice and MUST NOT be taken from a mutable/tamperable retained output at runtime as if the artifact could redefine the slice contract.

Exact ordered pilot sequence:

```text
1  Q104861437  Buzzards Bay 14  BM_WDT0_003ba28d4cd143d68c28e57899a3ed73
2  Q104829866  Suspens          BM_WDT0_0040159e704c49d0a0b7bc7c6224ecfb
3  Q60521258   Hunter 340       BM_WDT0_00f6a6f678474a14ab5ec1b078cf6d60
```

Before any external research:

1. offline-verify the accepted SLICE-0031 retained package;
2. reproduce the exact 1,770 canonical / 1,772 historical identity boundary;
3. independently verify that the three exact QIDs/HullQ IDs above are ranks 1–3 of the accepted candidate pool under the fixed SLICE-0031 ranking;
4. independently verify all three still satisfy the fixed positive-control eligibility rule;
5. derive their current corrected five-field normalized technical candidates from accepted retained raw evidence using the accepted SLICE-0030/current unit-map semantics;
6. fail `BLOCKED` on identity drift, candidate-order drift, eligibility drift, or inability to reproduce corrected evidence.

No discovery query and no Wikidata reacquisition are permitted.

## Fixed technical field boundary

Applicability assessment is limited to exactly:

```text
/baseline/dimensions/loa_m
/baseline/dimensions/lwl_m
/baseline/dimensions/beam_m
/baseline/dimensions/draft_min_m
/baseline/dimensions/displacement_kg
```

Do not add ballast, sail area, rig, keel/rudder/skeg taxonomy, material, engine, tanks, or unrelated fields to make a candidate easier to prove.

Generation/option facts outside these five fields MAY be inspected only when necessary to establish the scope that controls applicability of the five fixed fields.

## Sequential research algorithm

Candidate order is fixed as rank 1 -> rank 2 -> rank 3.

For each candidate:

1. establish an allowed primary-source identity surface within the fixed external-source classes below;
2. assess the exact source use under `SOURCE_RIGHTS_POLICY.v0.1.md`, including SR-6.6 when applicable;
3. if the required bounded manual `identity_seed` / `production_value` use cannot be positively cleared, classify that candidate `RIGHTS_CLEARANCE_BLOCKED` and move to the next candidate;
4. if source use is cleared, assess positive evidence for BoatDesign generation / configuration / option boundaries;
5. classify each of the five corrected/current retained technical candidates using the fixed field-applicability states below;
6. compute the candidate-level result mechanically;
7. if the candidate result is `READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT`, STOP. Do not research any later candidate;
8. otherwise continue to the next candidate until rank 3 is exhausted.

The retained retrieval log MUST make it mechanically verifiable that no later-ranked candidate was accessed after a positive stop condition was reached.

## Fixed external-source boundary

Positive technical/applicability evidence may come only from an authoritative primary factual surface directly controlled by one of these source classes:

1. the boat manufacturer / builder / brand owner responsible for the design or its official successor archive;
2. the designer / naval-architect office or its official estate/archive where it publishes design-specific technical facts;
3. an official class association for a one-design/class boat when the association is the authoritative publisher of class/design technical rules or specifications.

Permitted source-surface types within those classes:

- official model/specification pages;
- official brochures/manuals/specification sheets;
- official historical/archive pages;
- official class rules/specifications where applicable;
- official history/redesign/change notices;
- official terms/privacy/copyright/access/robots or comparable policy surfaces needed for rights assessment.

Search engines MAY be used only as navigation to an allowed source surface. Search results and snippets are not evidence.

The following MUST NOT support a positive rights, generation, applicability, or technical-value decision:

- SailboatData;
- Wikipedia/Wikimedia article text;
- broker/dealer listing pages not controlled by the authoritative source class above;
- owner forums/posts;
- review sites;
- general specification databases;
- copied/mirrored brochures on third-party hosts;
- Internet Archive captures as positive production-value evidence;
- AI-generated summaries.

Those sources should normally not be retrieved at all in this slice. If encountered incidentally during navigation, they are research leads only and MUST NOT enter positive evidence.

## Retrieval ceiling

This is bounded manual research, not an adapter, crawler, or broad source-ingestion exercise.

Normative constants:

```text
maximum attempted candidates          3
maximum semantic source retrievals   36 total
maximum retrievals per candidate     12
```

The implementation/verifier MUST treat these as fixed contract constants, not trust values supplied by a retained artifact as normative verification inputs.

A semantic retrieval is one independently fetched source page/document used or inspected for source identity, rights, generation, option, applicability, or technical facts. Tool redirects/retries that retrieve no distinct semantic document need not count separately, but the retained log must make accounting auditable.

No generalized scraper, crawler, automated archive adapter, or recursive link harvester may be built.

If the evidence cannot be resolved within the fixed ceiling, classify fail-closed and stop that candidate rather than expanding the ceiling.

## Source-rights rule

Use the accepted `SOURCE_RIGHTS_POLICY.v0.1.md` without weakening it.

For an unlicensed primary factual source, bounded manual use of discrete identity/technical facts may be positively cleared only when all SR-6.6 conditions are positively established:

1. source lawfully/publicly accessible;
2. only discrete factual/technical facts reused, not expressive text/media/layout;
3. provenance retained;
4. no identified terms/access restriction prohibits the chosen bounded manual research method;
5. not systematic/bulk database extraction;
6. automated access, if any, separately cleared.

This slice's target method is bounded manual research. A positive result MUST NOT silently clear:

```text
automated_ingestion
bulk_bootstrap
artifact_redistribution
```

Those uses remain non-allow unless separately evidenced for the exact source.

Do not weaken `src/hullq/sources/rights.py` to make a source pass.

If a reusable generic SR-6.6 helper is introduced, it must preserve the accepted SLICE-0029 behavior and include negative regressions demonstrating that scope, use kinds, and required conditions cannot be controlled by a tampered retained artifact.

## Source-material retention boundary

Unless redistribution rights are independently established, do not vendor third-party PDFs, HTML, screenshots, images, drawings, brochure prose, or other expressive source material.

Retain only auditable factual metadata such as:

- canonical source URL;
- source class and controlled-domain evidence;
- page/document title or identifier;
- access/review timestamp;
- concise non-expressive description of the fact inspected;
- discrete factual values where source-use clearance permits;
- source fingerprint/hash when obtainable without retaining redistributed content;
- evidence references supporting the rights decision.

## BoatDesign / applicability semantics

Apply the accepted identity model exactly:

```text
BoatModel = continuous commercial lineage
BoatDesign = technically coherent production generation
DesignOption = concurrent factory-supported technical choice
ResolvedConfiguration = BoatDesign baseline + applicable option/variant effects
```

Positive evidence may establish, where supported:

- persistent redesign boundaries;
- production-year ranges when both ends needed for the claimed scope are positively known;
- hull-number or other genuinely closed design boundaries;
- concurrent factory options;
- named variants that carry actual technical applicability significance;
- explicit class-rule revision boundaries where relevant.

Do not infer a generation from a label alone.

### Closed-boundary rule

A claimed year-based applicability scope is not bounded when only one endpoint is positively established.

The following are fail-closed / not sufficient as a bounded year range:

```text
first_year known, last_year unknown
first_year unknown, last_year known
```

A genuinely independent non-year boundary may establish scope only when positive evidence defines it sufficiently for the field being classified.

### Option rule

A concurrent factory choice affecting a field is a DesignOption/configuration issue, not a reason to flatten multiple values into one BoatDesign baseline.

A technical candidate whose value is option-sensitive MUST NOT be marked safe for a single canonical baseline unless the candidate is positively scoped to one specific baseline/option context that a later canonical model can represent correctly.

### Equality rule

Numeric equality between retained Wikidata evidence and a primary-source value is necessary/useful evidence in some cases but NEVER sufficient by itself to prove that the retained BoatModel-scoped candidate applies to a specific BoatDesign generation/configuration.

## Fixed field-applicability states

For each attempted candidate and each of the five fixed fields, classify the corrected/current retained evidence into exactly one of:

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

Given the SLICE-0031 eligibility invariant, `NO_NORMALIZED_WIKIDATA_CANDIDATE` should not occur for an untampered attempted candidate; if it does, treat it as input/evidence drift and fail closed rather than silently accepting a changed candidate.

`SAFE_FOR_LATER_DESIGN_PROMOTION` means only that a later separately readied canonical-promotion slice may consider the exact field under the positively established design/configuration scope. It does not itself create a canonical field value or FieldResolution.

## Candidate-level result

Each attempted candidate receives exactly one candidate result:

```text
READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
RIGHTS_CLEARANCE_BLOCKED
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

### `READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT`

Only when ALL are true:

- the exact primary-source use needed for the later proposed canonical path is positively cleared;
- a BoatDesign generation/configuration applicability boundary is positively established and not unknown/unbounded;
- at least one of the five corrected/current retained normalized technical candidates is `SAFE_FOR_LATER_DESIGN_PROMOTION` under that same scope;
- no unresolved source-rights, generation, option, or value conflict contradicts the safe classification;
- the retained evidence identifies the exact candidate, field(s), source(s), and proposed later design scope without minting a canonical BoatDesign.

### `RIGHTS_CLEARANCE_BLOCKED`

Use when the source use required to support positive production facts cannot be positively cleared, such that technical applicability cannot be relied upon for the intended later path.

### `APPLICABILITY_EVIDENCE_INSUFFICIENT`

Use when required source use is cleared sufficiently for the attempted research, but positive evidence still cannot safely scope any retained corrected technical candidate to a bounded BoatDesign generation/configuration.

## Top-level result

The slice produces exactly one top-level result using this deterministic rule:

1. if any candidate reaches `READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT`, the top-level result is `READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT`, identifies that first successful rank, and later candidates MUST be `NOT_ATTEMPTED_AFTER_SUCCESS`;
2. otherwise, if at least one attempted candidate had source use sufficiently cleared for applicability research but none reached READY, top-level result is `APPLICABILITY_EVIDENCE_INSUFFICIENT`;
3. otherwise, when every attempted candidate is blocked at the required source-rights step, top-level result is `RIGHTS_CLEARANCE_BLOCKED`.

Do not invent a fourth positive state or lower the READY conditions.

## Canonical mutation boundary

SLICE-0032 MUST create/mutate zero canonical production identities or technical values.

Specifically prohibited:

- minting a BoatDesign ID;
- inserting/updating a canonical BoatDesign row;
- modifying any canonical BoatModel row;
- creating a FieldResolution;
- writing a canonical baseline technical value;
- creating a DesignOption or NamedVariant canonical entity;
- altering any historical QID -> HullQ-ID mapping;
- changing the 1,770 / 1,772 accepted identity boundary;
- changing accepted Wikidata qualifier/unit semantics;
- changing Search/API/frontend behavior;
- starting SLICE-0033.

If the top-level result is READY, the exact canonical mutation remains the responsibility of a later separately readied slice.

## Retained package

Retain the bounded deterministic result under:

```text
research/stage3/sl0032-positive-control-boatdesign-applicability/
```

At minimum include schema-validated machine-readable artifacts equivalent to:

- `pilot_candidates.json` — fixed rank 1–3 candidate constants, accepted identity/evidence references, and independent reproduction result;
- `corrected_candidate_evidence.json` — exact corrected/current five-field normalized candidate values and provenance for attempted candidates, derived offline from accepted retained inputs;
- `source_retrieval_log.json` — ordered candidate-by-candidate retrieval accounting, source class, locator, purpose, and stop-on-first-positive evidence;
- `source_clearance_assessment.json` — per-source/use SR-6.6 or other applicable rights evidence and outcomes;
- `boatdesign_applicability.json` — positive generation/option/scope findings and unresolved boundaries for each attempted candidate;
- `field_applicability.json` — five-field states for each attempted candidate;
- `result.json` — per-candidate result, top-level result, successful rank if any, and mechanically derived stop state;
- `REPORT.md` — concise human-readable result with no unsupported claims;
- JSON schemas for every retained JSON artifact;
- `ARTIFACT-DIGESTS.json` + schema covering every retained package file except the digest manifest itself.

Filenames may differ only if the same separation and machine-verifiable semantics are preserved.

Do not modify accepted SLICE-0028/0029/0030/0031 retained packages.

## Fail-closed verifier requirements

The offline verifier must independently reconstruct every eligibility- or recommendation-relevant invariant from trusted code constants and accepted fixed inputs.

It MUST NOT treat values inside the retained SLICE-0032 package as normative inputs for verifying themselves, including at minimum:

- candidate order;
- maximum candidate count;
- retrieval ceilings;
- stop-on-first-positive rule;
- allowed field pointers;
- candidate/result state vocabulary;
- READY conditions;
- top-level result derivation.

The verifier must answer the adversarial question:

> Can a coherently falsified retained artifact change a governing limit, candidate sequence, stop condition, state, or threshold and still make the verifier rebuild against that falsified value?

The answer must be no.

Tampering with a retained artifact, schema, source decision, candidate order, retrieval count, applicability state, top-level result, or digest must cause deterministic verification failure where it contradicts the fixed contract or independently reconstructed evidence.

## Required implementation behavior

1. Offline-verify accepted SLICE-0031 inputs before any external source research.
2. Reproduce exact fixed ranks 1–3 and exact QID/HullQ IDs from accepted retained artifacts.
3. Reproduce corrected/current five-field candidate evidence using accepted SLICE-0030 semantics and retained SLICE-0028 raw entities; no Wikidata reacquisition.
4. Research candidates strictly in rank order.
5. Enforce max 3 candidates, max 12 semantic retrievals per candidate, max 36 total.
6. Stop external research immediately after the first candidate reaches READY.
7. Use only the fixed primary-source classes for positive evidence.
8. Resolve source uses independently under the accepted Source Rights Policy; preserve non-allow states for automation/bulk/redistribution absent explicit evidence.
9. Do not vendor unauthorized source materials.
10. Apply accepted BoatModel / BoatDesign / DesignOption semantics and closed-boundary rules.
11. Classify exactly the five fixed technical fields for each attempted candidate.
12. Produce each candidate result and the top-level result mechanically.
13. Create/mutate zero canonical BoatModel/BoatDesign/FieldResolution/technical production data.
14. Add schema validation, digest protection, deterministic offline verification, and adversarial tamper tests.
15. Do not modify accepted prior retained packages.
16. Do not start SLICE-0033.

## Required regressions

Tests must cover at least:

- fixed candidate sequence is exactly ranks 1–3 above;
- candidate-order tamper fails verification;
- an ineligible or non-top-three replacement candidate fails verification;
- corrected/current evidence is derived with accepted SLICE-0030/current unit semantics rather than the legacy mass-unit map;
- all five normalized-candidate invariants reproduce for every attempted candidate;
- retrieval limit >12 for one candidate fails;
- total retrieval count >36 fails;
- a retained artifact attempting to change either retrieval ceiling cannot redefine verifier behavior;
- candidate 2 cannot be attempted after candidate 1 is READY;
- candidate 3 cannot be attempted after candidate 1 or 2 is READY;
- candidate 2 is permitted after candidate 1 returns RIGHTS_BLOCKED or APPLICABILITY_EVIDENCE_INSUFFICIENT;
- source outside the fixed authoritative primary-source classes cannot support a positive decision;
- search-result snippet cannot support a positive decision;
- SR-6.6 condition missing -> required use is not positively cleared;
- positive bounded manual clearance cannot silently clear automated_ingestion/bulk_bootstrap/artifact_redistribution;
- half-open year range cannot establish a bounded design scope;
- named variant/`Mk` label alone cannot establish a BoatDesign;
- numeric equality alone cannot produce `SAFE_FOR_LATER_DESIGN_PROMOTION`;
- option-sensitive evidence cannot be flattened into a single safe baseline;
- READY requires both a bounded applicability scope and at least one SAFE field on the same candidate;
- rights blocked candidate cannot be READY;
- top-level result is first READY rank when one exists;
- top-level result is APPLICABILITY_EVIDENCE_INSUFFICIENT when at least one rights-cleared attempted candidate exists but none is READY;
- top-level result is RIGHTS_CLEARANCE_BLOCKED only when all attempted candidates are rights-blocked;
- artifact/digest tampering fails offline verification;
- no canonical persistence mutation occurs;
- no live Wikidata request is required for the fixed corrected candidate evidence.

## Acceptance criteria

SLICE-0032 is ready for independent review only when all applicable items are truthfully satisfied or explicitly reported `BLOCKED`:

- [ ] accepted SLICE-0031 retained package verifies offline;
- [ ] exact 1,770 canonical / 1,772 historical identity boundary reproduces;
- [ ] fixed candidate sequence reproduces exactly as ranks 1–3;
- [ ] each attempted candidate still satisfies accepted SLICE-0031 eligibility;
- [ ] corrected/current five-field normalized evidence is reproduced offline for attempted candidates using accepted SLICE-0030 semantics;
- [ ] external research follows rank order and stop-on-first-positive semantics;
- [ ] no more than 3 candidates are attempted;
- [ ] no attempted candidate exceeds 12 semantic source retrievals;
- [ ] total semantic source retrievals do not exceed 36;
- [ ] every positive evidence locator belongs to a permitted authoritative primary-source class;
- [ ] source-use decisions are explicit and use-specific under the accepted Source Rights Policy;
- [ ] no unauthorized source content is vendored;
- [ ] every attempted candidate has a machine-readable BoatDesign/applicability assessment;
- [ ] every attempted candidate has exactly five field-applicability outcomes;
- [ ] closed-boundary, option, absence-as-proof, and equality guardrails are enforced;
- [ ] every attempted candidate has exactly one mechanically valid candidate result;
- [ ] top-level result is derived exactly from the fixed deterministic rule;
- [ ] if READY, later candidates are not researched and are represented as `NOT_ATTEMPTED_AFTER_SUCCESS`;
- [ ] zero canonical BoatModel/BoatDesign/FieldResolution/technical mutations occur;
- [ ] retained package schemas validate;
- [ ] artifact digests cover every retained package file except the digest manifest itself;
- [ ] deterministic offline verifier independently reconstructs fixed contract invariants rather than trusting retained control values;
- [ ] focused adversarial/tamper regressions pass;
- [ ] repository governance validation passes;
- [ ] Ruff format/lint pass;
- [ ] mypy passes;
- [ ] full test suite passes with repository coverage gate >=90%;
- [ ] exact final PR head has remote CI SUCCESS;
- [ ] exact same final PR head has Manufacturer artifact reproducibility SUCCESS on Ubuntu and Windows;
- [ ] completion report lists exact final head SHA, changed files, attempted candidates, retrieval counts, source-rights outcomes, field/applicability results, top-level result, test results, exact-head workflow IDs, unresolved findings, and scope deviations;
- [ ] recommended slice state is `REVIEW` or `BLOCKED`, never `DONE`;
- [ ] SLICE-0033 was not started automatically.

## Out of scope

Explicitly out of scope:

- canonical BoatDesign creation;
- canonical FieldResolution creation;
- canonical technical-value promotion;
- broader candidate-pool research beyond ranks 1–3;
- researching later-ranked candidates after a READY result;
- Wikidata reacquisition;
- generalized manufacturer/class-association crawling;
- broad source-rights clearance;
- SailboatData/Wikipedia/broker/forum evidence as positive technical/applicability evidence;
- new Tier-1/Tier-2 fields;
- Search/query/API/frontend/SEO;
- market listings, listing dedup, monitoring, pricing, ads, subscriptions;
- CAL-01 threshold declaration or G4 pass;
- SLICE-0033 readiness or implementation.

## Completion-report template

The implementation agent must report:

```text
SLICE-0032 Completion Report

Slice
- Slice ID: SLICE-0032
- Recommended state: REVIEW | BLOCKED
- Exact final branch HEAD SHA:
- Scope completed: YES | NO

Fixed boundary verification
- canonical BoatModels:
- historical mappings:
- fixed candidate ranks/QIDs/HullQ IDs reproduced:
- corrected/current five-field evidence reproduced:

Sequential research
- rank 1: attempted/result/retrieval count
- rank 2: attempted | NOT_ATTEMPTED_AFTER_SUCCESS / result / retrieval count
- rank 3: attempted | NOT_ATTEMPTED_AFTER_SUCCESS / result / retrieval count
- total semantic source retrievals:
- stop-on-first-positive invariant: PASS | FAIL

Source rights
- source(s) per attempted candidate:
- source class(es):
- bounded manual identity_seed result:
- bounded manual production_value result:
- automated_ingestion:
- bulk_bootstrap:
- artifact_redistribution:

BoatDesign/applicability
- positively established generation/configuration boundaries:
- unresolved boundaries/options:
- five field outcomes per attempted candidate:
- SAFE field(s), if any:

Top-level result
- READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT |
  APPLICABILITY_EVIDENCE_INSUFFICIENT |
  RIGHTS_CLEARANCE_BLOCKED
- successful candidate rank/QID/HullQ ID, if READY:

Validation
- local validation commands/results:
- total tests passed/skipped:
- coverage:
- offline verifier result:
- adversarial/tamper tests:
- exact-head CI run ID/result:
- exact-head Manufacturer run ID/result:

Findings
- unresolved findings:
- scope deviations:
- canonical mutation count:
- prior retained-package mutations:

Agent declaration
- no work outside assigned slice started
- no unverified criterion marked passed
- SLICE-0033 not started
- slice not marked DONE
```

## Independent-review requirement

Claude/implementation-agent completion is not acceptance.

Before Project Owner acceptance, independent review must perform at least:

1. contract-matrix review against every acceptance criterion;
2. exact diff/scope review;
3. adversarial verifier review, especially artifact-controlled limits/order/results;
4. source-rights fail-closed review;
5. generation/applicability/option semantics review;
6. stop-on-first-positive audit against the retrieval log;
7. retained-artifact/digest review;
8. exact-head CI and Manufacturer reproducibility confirmation;
9. explicit ACCEPT or CHANGES REQUIRED verdict.

Only after accepted implementation merge, acceptance-closure review/merge, and explicit Project Owner acceptance may SLICE-0032 become DONE.
