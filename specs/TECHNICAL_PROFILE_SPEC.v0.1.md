# HullQ — Technical Profile Contract

**Version:** 0.1  
**Status:** ACCEPTED  
**Decision basis:** Project Owner decisions accepted 2026-08-29 during the post-SLICE-0033 Product/Data parallelization work  
**Scope:** information requirements, research priority, applicability/conflict semantics, and schema-evolution direction for canonical BoatDesign technical profiles  

## 1. Product intent

HullQ SHALL aim to know at least the useful technical breadth expected from a mature sailboat reference database, while representing that information more structurally for deterministic search, configuration-aware evaluation and provenance.

SailboatData is a **reference for field breadth, taxonomy coverage and completeness expectations**. It is **not** an automatic source of HullQ canonical production values and this specification grants no right to copy, bulk extract, ingest or republish SailboatData data.

Canonical values remain governed by HullQ source-rights, provenance, applicability and FieldResolution policy.

No information-requirement category is dropped in v0.1 merely because it is currently sparse. Research priority and model breadth are separate concerns.

## 2. Core strategy

The accepted data strategy is:

> **Breadth is global. Depth follows footprint. Search-defining fields come first.**

`footprint` is an operational research concept, not a hidden search-ranking score. A model can have a high footprint through any combination of:

- **commercial footprint** — broad production and/or visible market activity;
- **community footprint** — active class/owner associations, racing/class infrastructure, specialist communities;
- **archival footprint** — manufacturer/designer archives, original brochures/manuals, class rules, measurement material, long-lived technical documentation.

A rarely traded but highly documented/legendary model can therefore be a high-priority depth candidate. Current listing count alone MUST NOT define research priority.

`number_built` remains useful profile/history information but is lower research priority than search-defining technical properties such as rig, cockpit, keel, rudder, skeg and draft configuration.

## 3. Research-priority classes

HullQ retains broad information requirements but does not spend equal research effort on every field.

### CORE_SEARCH

Actively prioritize because these properties can materially determine whether a boat is relevant to a search:

- hull configuration / hull count;
- LOA, LWL, beam, draft and displacement;
- keel and movable-appendage configuration;
- rudder and skeg configuration;
- rig/sailplan and masthead/fractional character;
- cockpit position/configuration;
- construction/material where reliably known;
- sail area where needed for search or derived metrics;
- configuration/variant/applicability boundaries that change any CORE_SEARCH value.

### TECHNICAL_DEPTH

Systematically retain when supportable, and actively research when needed for compare/derived-metric quality:

- ballast and ballast type/material;
- detailed rig dimensions;
- mast height and mast stepping;
- individual sail-area components;
- steering/helm configuration;
- propulsion/drive configuration;
- fuel and water capacities;
- accommodation dimensions and counts such as headroom/cabins/berths/heads;
- measurement/input-basis metadata needed for deterministic derivation.

### PROFILE_ENRICHMENT

Retain when available but do not block higher-priority research merely to complete these fields:

- first/last built;
- number built;
- builder/designer history beyond identity-critical needs;
- descriptive/history notes;
- associations/dealers/related-design context.

### DERIVED

HullQ-computed values remain separate from source-reported facts and MUST carry methodology/version/lineage:

- Sail Area / Displacement;
- Ballast / Displacement;
- Displacement / Length;
- Comfort Ratio;
- Capsize Screening Formula;
- Hull Speed;
- any later accepted formulas such as immersion or multihull-specific metrics.

### EVIDENCE_META

Mandatory where a value becomes canonical/qualified:

- source/source type;
- source locator;
- raw/source value and source unit;
- normalized canonical value/unit;
- applicability scope;
- resolution/qualification state;
- supporting and contradicting evidence;
- provenance/producer/method/version;
- supersession/validity metadata where applicable.

### MEDIA_RELATIONS

Retain in a separate content/relationship layer where rights permit:

- photographs;
- drawings/sail plans;
- class/sail insignia;
- rigging diagrams;
- reference links;
- designer/builder/association/dealer/related-design relationships.

There is intentionally no `DROP` priority class in v0.1.

## 4. Information-requirement catalogue

This catalogue defines desired information breadth. It does **not** require one SQL column per item; schema design may group related properties into nested structured objects.

### 4.1 Identity, design and production

1. Boat/model name
2. Description/history summary
3. First built
4. Last built
5. Number built
6. Builder/manufacturer relationships
7. Designer/naval architect relationships
8. Hull construction/material
9. Hull/configuration classification
10. Rigging classification
11. Ballast type/material
12. Design generation
13. Named variant
14. Production/design option

### 4.2 Principal dimensions and masses

15. LOA — length overall
16. LOD — length on deck
17. LWL — length waterline
18. Beam maximum
19. Beam at waterline
20. Draft minimum
21. Draft maximum
22. Displacement
23. Displacement basis/condition
24. Ballast mass
25. Mast height / mast height from design waterline where basis is known
26. Bridgedeck clearance

### 4.3 Hull and appendages

27. Hull configuration — monohull/catamaran/trimaran/other
28. Hull count
29. Keel type
30. Keel subtype/configuration
31. Standard/deep/shallow/lifting/swing/other keel option applicability
32. Centerboard presence/type/count
33. Daggerboard presence/type/count
34. Rudder count
35. Rudder position
36. Rudder support — keel/skeg/free/transom relationship as independently structured semantics
37. Rudder balance/type where supportable
38. Skeg presence/type

A compound label such as `long keel with transom-hung rudder` MUST NOT force HullQ to collapse independent keel/rudder/support facts into one opaque string when they can be represented separately.

### 4.4 Rig and sail plan

39. Sailplan — sloop/cutter/ketch/yawl/schooner/cat/etc.
40. Masthead/fractional character
41. Mast count
42. Mast step — deck/keel/other/unknown
43. Rig variant — standard/performance/etc.
44. I
45. J
46. P
47. E
48. PY
49. EY
50. ISP
51. JP
52. SPL / TPS as source definition permits
53. Estimated/reported forestay length with basis
54. Reported sail area
55. Sail-area basis
56. Main sail area
57. Fore/foretriangle/headsail area with source semantics preserved
58. Geometrically calculated total/upwind sail area
59. Other explicitly identified sail-plan areas where useful

Rig MUST NOT be limited to one opaque `rig_type` string if the underlying attributes can be represented independently.

## 4.5 Deck, cockpit and steering

60. Cockpit position — aft/center/forward/multiple/other/unknown
61. Cockpit count
62. Helm/steering type — tiller/wheel/other/unknown
63. Helm count
64. Deck-saloon/pilothouse configuration

Cockpit position is a CORE_SEARCH field even though it is not universally structured in external reference databases.

## 4.6 Propulsion and capacities

65. Original/standard auxiliary engine make
66. Engine model
67. Engine type/fuel
68. Engine power
69. Engine count
70. Drive type — shaft/saildrive/outboard/other
71. Propeller configuration where useful
72. Fuel capacity
73. Water capacity
74. Holding/other capacities where supportable and product-relevant

Source-published propulsion data MUST retain applicability/model-year/options semantics because engines are frequently changed by owners.

## 4.7 Accommodation and practical configuration

75. Headroom
76. Cabin count
77. Berth count
78. Head/toilet compartment count
79. Layout/accommodation variant where it materially changes the preceding values

## 4.8 Compliance and contextual technical data

80. CE/design category where applicable
81. Source-defined design/class measurement category where useful
82. Class/association relationship
83. Relevant measurement/certificate regime

## 4.9 Derived metrics and calculated outputs

84. Sail Area / Displacement
85. Ballast / Displacement
86. Displacement / Length
87. Comfort Ratio
88. Capsize Screening Formula
89. S# if later formally accepted
90. Hull Speed
91. Pounds per Inch Immersion if later formally accepted
92. Calculated sail area from rig dimensions
93. Multihull KSP if later formally accepted
94. Multihull BN if later formally accepted

Existing accepted HullQ derived-metric methodology remains controlling; this catalogue does not silently authorize new formulas.

## 4.10 Relations and media/content

95. Designers relation
96. Builders relation
97. Associations relation
98. Dealers relation where product policy permits
99. Market listings relation
100. Related BoatModels/BoatDesigns
101. Notes/history
102. Sailboat photo
103. Drawing / sail-plan image
104. Class/sail insignia
105. Rigging diagram
106. External/reference URL

## 4.11 HullQ evidence/applicability extensions

107. Source record and source type
108. Raw/source value and unit
109. Canonical normalized value and unit
110. Qualification/resolution state
111. Conflict state and dissenting evidence
112. Provenance/producer/method
113. Applicability subject — BoatModel/BoatDesign/NamedVariant/DesignOption/configuration
114. Applicability time/specification epoch
115. Hull-number applicability where known
116. Market/region applicability where genuinely technical
117. Measurement definition/basis
118. Derived-vs-reported distinction
119. Supersession/current-resolution lineage
120. Confidence/quality metadata without converting confidence into search truth

## 5. Applicability before conflict

Different reported values are **not automatically conflicts**.

Before declaring `UNRESOLVED_CONFLICT`, HullQ MUST test whether the observations can legitimately belong to different scopes, including:

- BoatDesign generation;
- NamedVariant;
- DesignOption/configuration;
- model year / specification epoch;
- hull-number range;
- market-specific specification;
- measurement definition or basis;
- operating/loading condition.

Examples such as standard-vs-shallow draft, standard-vs-performance rig, or lightship-vs-sailing displacement are separate applicable values, not numbers to average.

Only differing values that assert the **same materially relevant applicability scope and measurement definition** are a true source conflict.

## 6. Conflict Confirmation Protocol — 6/8-eye principle

HullQ uses evidence convergence, not source voting.

### 6.1 No detected conflict

A single sufficiently authoritative, rights-cleared, applicability-matched source MAY be enough to support a value under the existing FieldResolution policy. This specification does not require four sources for every ordinary fact.

### 6.2 Conflict detected

When two material sources disagree:

1. preserve both raw observations;
2. resolve applicability/measurement-basis differences first;
3. if the same scope still conflicts, mark the value unresolved and seek an **independent confirming source** — the 6-eye stage;
4. for CORE_SEARCH/high-impact values or continuing uncertainty, seek a second independent confirming line — the 8-eye stage;
5. if evidence does not converge sufficiently, retain `UNRESOLVED_CONFLICT` rather than guessing, averaging or selecting the convenient value.

### 6.3 Authority, independence and scope

Conflict resolution MUST consider all three:

- **authority** — e.g. builder/manufacturer, designer/naval architect, official class/measurement material, original specification/manual, specialist archive, contemporary technical test, secondary database, broker/user material;
- **independence** — multiple pages copying one originating specification are not multiple independent evidence lines;
- **applicability** — sources must address the same technical scope before their numeric/string values are treated as competing claims.

Four copied broker records do not automatically outweigh one original drawing or class measurement. Source count alone MUST NOT resolve a conflict.

### 6.4 Resolution state

A conflict-resolved canonical value SHOULD preserve both supporting and dissenting evidence. A useful semantic distinction is:

- agreed/no material conflict;
- applicability split (not a conflict);
- representation/rounding variance when explicitly demonstrated;
- unresolved conflict;
- resolved/confirmed after conflict with retained dissent.

Existing `FieldResolution` vocabulary remains controlling until explicitly versioned; this section defines required semantics, not an unreviewed enum migration.

## 7. Coverage reporting

A single flat `X/Y fields complete` score is insufficient because low-value enrichment fields can hide missing search-defining information.

HullQ SHOULD distinguish at least:

- **Search Coverage** — CORE_SEARCH readiness;
- **Technical Coverage** — CORE_SEARCH + TECHNICAL_DEPTH;
- **Full Profile Coverage** — all applicable retained profile families.

Coverage may describe data readiness; it MUST NOT become an opaque boat-quality ranking signal.

## 8. Canonical/search boundary

- Research evidence, scraped/reference values and external-database values remain non-canonical until admitted through accepted HullQ provenance/resolution rules.
- Unknown stays explicit; absence is not a negative fact.
- `computed_provisional` remains non-truth-final.
- Configuration-dependent values MUST NOT be flattened into averages or arbitrary baseline numbers merely to make search easier.
- Search consumes canonical/resolved/accepted derived values and follows `SEARCH_QUERY_SEMANTICS.v0.1.md`.

## 9. Schema evolution direction

`BOAT_DESIGN_SCHEMA.v0.5` already captures a useful subset: principal dimensions, hull configuration, keel/rudder/skeg summary, a combined rig type, construction, basic cruising values, variants/options and quality.

A later schema version SHALL extend the contract rather than discarding accepted v0.5 semantics. In particular it needs structured support for the additional search/product dimensions above, including cockpit/helm, richer rig decomposition and dimensions, richer rudder semantics, propulsion/drive, accommodation counts and explicit measurement/applicability bases where appropriate.

This specification is an **information-requirement contract**, not a mandate to create 120 SQL columns. Nested objects, reusable definitions and normalized relationships are preferred when they preserve deterministic meaning.

## 10. Initial reference corpus

The first bounded real-world profile/schema pilot SHOULD continue to use the already selected high-footprint set because it spans materially different technical problems:

- Rustler 36 — traditional design, strong archival footprint, rudder-taxonomy/source-value issues;
- Contessa 32 — strong class/measurement control and specification evolution;
- Bavaria Cruiser 34 — modern production options and spec editions;
- Sun Odyssey 36i — standard/shallow/performance option structure;
- Albin Vega — strong class/community evidence plus conflict/independence case;
- Rival 34 — deep/shallow design variants with incomplete higher-authority P0 evidence.

These names define a pilot set, not privileged search ranking and not automatic canonical admission.

## 11. Explicit non-goals

This spec does not:

- authorize bulk copying from SailboatData or any other reference site;
- promote the 1,770 research-evidence BoatModels into canonical BoatDesigns;
- change OQ-009 fail-closed search semantics;
- create a generic seaworthiness/bluewater score;
- imply that every information requirement must be mandatory/non-null;
- authorize hidden completeness/popularity ranking;
- settle market-listing geography, dedup, auth, public API or SEO questions.
