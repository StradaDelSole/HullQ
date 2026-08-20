# HullQ Controlled Benchmark — 50-Design Analysis

**Date:** 2026-08-20  
**Slice:** SLICE-0011  
**Corpus:** 50 deliberately difficult designs, Waves 01–06  
**Coding file:** `research/benchmark/BENCHMARK-50-classification.csv`

## Interpretation warning

This is a **stress benchmark**, not a random sample of all sailboats. Percentages below measure how often a problem class appeared in the deliberately difficult 50-design corpus. They MUST NOT be presented as estimated prevalence across the entire sailboat universe.

Each design was manually coded from the retained wave evidence. Flags are non-exclusive. A `1` means the problem/evidence class materially affected that design's research or canonicalization; a `0` means it was not a material issue in the retained benchmark evidence, not that the property is impossible for that design.

## Measured incidence in the stress corpus

| Problem / evidence class | Designs | Stress-corpus incidence |
|---|---:|---:|
| authoritative/original-document path found | 44 / 50 | 88% |
| appendage/configuration taxonomy complexity | 42 / 50 | 84% |
| temporal / production applicability mattered | 32 / 50 | 64% |
| identity / generation / lineage semantics mattered | 30 / 50 | 60% |
| option / variant / operating-state semantics mattered | 30 / 50 | 60% |
| secondary/community/broker evidence materially needed | 30 / 50 | 60% |
| post-hoc reference comparison exposed an anomaly/incompleteness/definition issue | 28 / 50 | 56% |
| measurement basis or field-definition semantics mattered | 22 / 50 | 44% |
| explicit conflict or unresolved question remained/materially occurred | 20 / 50 | 40% |

`reference_anomaly` includes identity ambiguity, incomplete option coverage, definition/basis differences, chronology differences and actual conflicts. It does **not** mean the reference database is wrong in 56% of records.

## What the 50 designs prove

### 1. The accepted identity architecture is directionally correct

The current `BoatModel → BoatDesign → NamedVariant / DesignOption → ResolvedConfiguration` structure is repeatedly justified by the corpus.

Examples span both sides of the split decision:

- same/reused model number but technically different design: First 35, Dehler 34, Hunter 37, Ericson 35, Swan 36 / ClubSwan 36;
- Mk/suffix change without a wholly new underwater design: Catalina 36 Mk II, Hallberg-Rassy 312 Mk II;
- suffix as configuration rather than generation: Bristol 35.5C;
- suffix as material evolution: Snowgoose 37 Elite;
- orthogonal concurrent options: HR 42E, RM 1180, Westerly Konsort, ETAP 32s, Bavaria 38.

The accepted identity classification algorithm should therefore be retained. No string-only generation rule is acceptable.

### 2. Evidence-level applicability is a real persistence requirement

`BoatDesign.generation`, NamedVariant applicability and DesignOption applicability can represent many production boundaries once the correct canonical subject exists. They do **not** fully solve evidence applicability before that canonical decision has been made.

The benchmark repeatedly contains observations that mean:

- this value applies to a 1979 example / model year only;
- this value applies after a hull-number/year boundary;
- this is a current-new-build specification within a long-lived design;
- this observation is for one individual brokered hull;
- this applies only to one keel/rig/board state;
- this is a class-rule constraint, not a nominal production value.

`FieldEvidence v0.2` currently has subject, field pointer, source locator, raw observation, source/document evidence type, observed timestamp and confidence, but no structured **claim applicability** object. Free-text `notes` is not sufficient for durable queryable persistence.

### 3. Source/document type and assertion semantics are different axes

`FieldEvidence.evidence_type` currently answers roughly **what kind of source/evidence artifact produced this observation** (`manufacturer_specification`, `manual`, `class_or_owner_association`, `narrative_text`, etc.).

The benchmark additionally requires a distinct semantic axis describing **what the observation claims**, for example:

- `nominal_design_value`;
- `factory_option_value`;
- `operating_state_value`;
- `individual_hull_value`;
- `class_rule_constraint`;
- `measurement_certificate_value`;
- `calculated_or_published_ratio`;
- `production_count_or_chronology_claim`;
- `other` / `unknown`.

A class-rule PDF may be extremely authoritative while its numeric value is still a limit/tolerance rather than a nominal BoatDesign value. Authority and assertion semantics must not be conflated.

### 4. Measurement basis handling is necessary but not yet broad enough

SLICE-0004 correctly preserves `raw_text` and `semantic_label`, and accepted structured basis vocabularies exist for derived-metric displacement and sail-area inputs.

The benchmark contains additional real labels such as:

- Half Load;
- Light displacement (EEC);
- dry ready-to-sail;
- unladen;
- light measurement trim;
- empty yacht incl. safety equipment;
- fully equipped ready for sailing with crew;
- measurement displacement versus sailing displacement;
- published sail area versus foretriangle/main-triangle calculation.

The raw semantic label must always survive. A bounded normalized interpretation may be added only where rules explicitly support it. Unsupported labels must remain explicit rather than being coerced into `design` or `lightship` merely to enable derived metrics.

### 5. Installed configuration and operating state are separate

The configuration runtime already preserves observation scopes including `board_up` / `board_down`, which was validated by real evidence.

The 50-design corpus goes further:

- Gemini 105Mc has two centerboards installed but legitimate states with 0, 1 or 2 deployed;
- folding trimarans have sailing versus folded beam;
- centerboard/daggerboard/lifting-keel boats have state-dependent draft;
- some state changes alter geometry without changing factory configuration identity.

The current canonical `ResolvedConfiguration v0.2` stores installed board counts and one effective `beam_m` plus min/max draft, but it does not represent a general operating-state projection. Persistence must not fake an operating state as a DesignOption.

### 6. Appendage relationships need more than flat labels in some cases

The current independent keel/rudder/skeg axes are strongly supported. However, real evidence also expresses relationships such as:

- each of two rudders preceded by its own protective skeg;
- rudder hung on partial skeg;
- rudder attached to the aft end of keel;
- grounding/protective centerline skeg protecting propeller/rudders;
- keel-hung rudder versus transom-hung reference disagreement.

The accepted vocabulary captures several categories, including `partial_skeg`, but some protection/support relationships may ultimately need a bounded relationship representation rather than additional flat taxonomy strings. This should be introduced only where search/product requirements justify it.

### 7. Reference comparison is useful specifically because it is not provenance

The post-hoc SailboatData comparison found many strong matches, but also:

- model-generation/identity splits;
- missing factory option space;
- chronology differences;
- different field definitions/bases;
- taxonomy granularity differences;
- occasional apparent duplicate/identity anomalies.

That validates the agreed policy: reference comparison is a QA trigger only. It should remain outside HullQ's canonical FieldEvidence chain unless a future explicit rights/licence decision changes policy.

## Existing contracts: keep versus extend

### Keep

- stable BoatModel / BoatDesign identity separation;
- same-name reused models may have distinct BoatModel IDs;
- generation boundaries with year/hull-number confidence;
- NamedVariant and independent DesignOption model;
- separate raw observation and normalized candidate;
- FieldResolution states `resolved`, `resolved_with_conflict`, `unknown`, `needs_review`, `conflict`;
- independent keel/rudder/skeg/board axes;
- ratio-input basis and nonstandard/provisional derived-metric behavior;
- no forced completeness.

### Extend before physical production persistence

1. **FieldEvidence claim semantics** — separate the source/document class from assertion role.
2. **FieldEvidence applicability** — structured year/hull-number/market/variant/option/state/individual-hull scope where known.
3. **Research target / individual-hull scope** — avoid projecting broker/listing observations onto a design by default.
4. **Operating-state representation** — at least enough to distinguish installed appendages from deployed state and folded/sailing geometry without manufacturing fake DesignOptions.
5. **Evidence-safe identity lineage links** — explicit relationship between predecessor/successor/derivative/marketing-heritage entities is useful, but the relation must be evidence-backed and allow `unknown/uncertain`; marketing lineage must not imply technical inheritance.

### Do not generalize yet

- do not create a universal arbitrary property graph;
- do not create a huge keel/rudder ontology from every phrase observed;
- do not model every individual yacht as a full production entity merely because broker evidence exists;
- do not freeze a physical PostgreSQL schema around free-text notes that carry critical applicability semantics;
- do not start broad ingestion before these bounded evidence/persistence semantics are frozen and tested.

## Human-review implication

At least **20/50 (40%)** of the deliberately hard designs contained a material explicit conflict or unresolved question in the retained research. Because this is a stress sample, it is not a production review-rate estimate.

The most common review triggers are:

1. generation/model identity ambiguity;
2. evidence applies only to a subset of years/hulls/configurations;
3. source basis/definition differs despite similar numbers;
4. appendage support/protection relationship is ambiguous or source-dependent;
5. individual-hull value risks being generalized to the design;
6. two reputable sources disagree;
7. authoritative source contains malformed/internally contradictory data.

The future pipeline should therefore optimize for **exception-based review**, not manual approval of every record.

## What is not yet measured

The manual benchmark cannot honestly measure:

- automated acceptance rate;
- false-normalization rate;
- deterministic rerun/idempotency rate;
- machine processing time;
- cost per automatically processed design;
- actual human minutes per reviewed record;
- physical PostgreSQL write/read/replay behavior.

Those require an executable benchmark importer/persistence path. Inventing them now would defeat the purpose of the benchmark.

## Decision from the 50-design gate

The corpus is sufficiently diverse to stop expanding by default and move to the next bounded implementation preparation.

**Recommended sequence:**

```text
SLICE-0011 benchmark research + measured requirements       DONE after closure review
        ↓
SLICE-0012 evidence/applicability + research-bundle contract
        ↓
SLICE-0013 PostgreSQL persistence + deterministic importer
        ↓
execute same 50-design corpus through importer/DB
        ↓
measure automation/review/idempotency/cost
        ↓
then authorize broader 1,000-design bootstrap if Gate G3 passes
```

This adds one small contract-hardening step before PostgreSQL because the benchmark found concrete semantics that would otherwise be frozen incorrectly into the physical schema. It is not a new abstract architecture phase; each required extension is directly evidenced by multiple boats in the 50-design corpus.
