# HullQ — Design Data Source Landscape

**Status:** IN PROGRESS — SLICE-0002 research checkpoint 2  
**Reviewed:** 2026-08-18  
**Purpose:** Evidence-first assessment of real sailboat-design data sources before HullQ research-pipeline implementation.

This document records observed source availability, source shape, likely HullQ usefulness, and rights/access constraints. It is not a production-source whitelist. Final clearance remains governed by `specs/SOURCE_RIGHTS_POLICY.v0.1.md` and ADR-0005.

## Current conclusion

The research supports a **two-layer acquisition strategy** rather than searching for one replacement for SailboatData:

1. **broad open identity/common-field bootstrap**, with Wikidata the strongest currently identified candidate;
2. **progressive primary-source enrichment**, using manufacturer heritage pages, brochures, manuals, class/owner-association technical material and other cleared evidence for deeper fields and option/generation resolution.

No single source found provides SailboatData-like breadth plus HullQ-critical keel/rudder/skeg/configuration depth under clearly reusable commercial terms.

## Broad-bootstrap feasibility checkpoint

The evidence is sufficient to treat a Wikidata-first bootstrap as technically plausible at a **four-digit** starting scale:

- Wikidata maintains an explicit `sailboat class` model (`Q106179098`) and EntitySchema E297 with structured manufacturer/designer and qualified LOA/LWL/beam/draft/displacement/ballast concepts.
- The official WikiProject Sailing publishes SPARQL queries specifically for listing sailboat-class items and checking field coverage.
- A historical Wikimedia diagnostic output indexed `Q106179098` at **1,471 items**; this is not used as a current exact count, only as order-of-magnitude evidence.
- A currently indexed third-party catalogue built from Wikidata plus Wikipedia reports **1,062 production sailboats**. Because it mixes CC0 and CC-BY-SA inputs, HullQ must not bulk-copy it; it is used only as a current independent signal that Wikimedia-derived coverage is already four-digit.

Therefore the current planning assumption is **approximately 1,000–1,500 directly useful sailboat-class identity candidates before additional open-source expansion/deduplication**, not a guaranteed exact current Wikidata count. Exact WDQS count and per-field completeness should be measured reproducibly by the future Wikidata acquisition adapter and stored as benchmark evidence.

This is enough for a first bootstrap path, but not enough for HullQ's eventual 5,000–10,000+ design-universe target. Multiple identity sources and market-driven discovery/enrichment will still be required.

## Source assessment legend

- `BOOTSTRAP_CANDIDATE` — plausible for broad structured seeding, subject to implementation/access controls.
- `PRIMARY_VERIFY` — strong source for individual factual verification; no blanket bulk-ingestion permission assumed.
- `SECONDARY_VERIFY` — useful factual/archival source; individual provenance required and bulk rights must be separately resolved.
- `REFERENCE_ONLY` — useful as a lead/comparison/edge-case source, not cleared for HullQ production-value ingestion.
- `BLOCKED` — current terms conflict with HullQ's intended commercial/systematic use unless separate permission/licence is obtained.

---

## 1. Wikidata structured data

**Operator:** Wikimedia / Wikidata community  
**Class:** `BOOTSTRAP_CANDIDATE`  
**Access:** SPARQL, APIs, dumps / structured exports  
**Rights basis:** Wikidata main/property/lexeme structured data is CC0. Wikimedia API usage rules separately require identifiable User-Agent behaviour, rate-limit compliance, robot-policy compliance at scale and licence compliance.

### Observed sailboat data model

Wikidata has an explicit `sailboat class` data model (`Q106179098`) intended for specific sailboat designs/models. The Sailing WikiProject model includes:

- manufacturer;
- designer;
- LOA and LWL as qualified length statements;
- beam;
- draft / air draft;
- displacement and ballast as qualified mass statements;
- total produced as an optional property;
- boat-type subclasses such as monohull/multihull, catamaran/trimaran, rig and keelboat/centerboarder concepts.

EntitySchema E297 formalises the core concepts.

### Strengths

- CC0 structured-data basis is compatible with HullQ's preferred bootstrap policy.
- Machine-readable QIDs and statements are well suited to broad identity seeding.
- Existing sailing-specific modelling overlaps strongly with HullQ basic fields.
- Official query examples already demonstrate SI conversion and qualified LOA/LWL querying.
- Dumps can reduce dependence on high-volume per-item API calls.

### Weaknesses

- Statement completeness is inconsistent.
- Reference quality varies by item and statement.
- The Wikidata sailboat-class model does not solve HullQ generation/variant/configuration identity.
- Rudder/skeg/construction depth is not part of the strong core model and is expected to be much sparser.
- Exact current direct-instance count should be measured by HullQ itself rather than copied from a stale report or mixed third-party catalogue.

### Current recommendation

Treat Wikidata as the leading broad identity/common-field bootstrap candidate. Import should retain Wikidata QID, statement semantics/qualifiers and source provenance. CC0 clearance is not an accuracy guarantee.

Automated access must use a descriptive HullQ User-Agent/contact, honor throttling/backoff and avoid API abuse; bulk dumps should be preferred where they are operationally cheaper and more reproducible.

**Reviewed sources:**
- https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Data_Models/Sailboat_class
- https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Data_Models/Sailboat_class/Properties
- https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Queries
- https://www.wikidata.org/wiki/EntitySchema:E297
- https://www.wikidata.org/wiki/Wikidata:Licensing
- https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines
- https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy

---

## 2. Manufacturer heritage/model archives

**Class:** `PRIMARY_VERIFY`  
**Rights:** excellent factual evidence for individual production values; no automatic bulk-crawl/republication clearance assumed.

### Hallberg-Rassy

Hallberg-Rassy's previous-model pages are exceptionally useful. The reviewed HR 36 and HR 42E pages expose:

- build years and hull counts;
- explicit generation boundaries / hull-number boundaries;
- designer;
- hull length / waterline / beam / draft;
- displacement and keel weight;
- keel type;
- multiple sail-area definitions;
- factory shallow-draft options;
- rig options;
- engine/tank data;
- brochures, specifications, drawings and other archival documents.

The HR 36 page is especially valuable because it states exactly what changed between Mk I and Mk II and what remained identical. Official Hallberg-Rassy parts pages additionally show that rudder/skeg evidence can exist outside the model archive itself.

**Reviewed sources:**
- https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-36
- https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-42e
- https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-31-mk-ii

### BENETEAU heritage

BENETEAU maintains multi-generation heritage navigation for Oceanis / First and other historic ranges. Range pages expose model lists, model grouping by production era/generation, and common dimensions. Individual pages can provide designer, LOA, beam, lightship displacement and downloadable brochures/equipment lists.

Observed example: Oceanis 37 provides authoritative common facts but not all HullQ-critical keel/rudder details directly in the HTML summary. This validates brochure/manual enrichment rather than assuming one canonical page is complete.

**Reviewed sources:**
- https://www.beneteau.com/sailing-yacht-heritage
- https://www.beneteau.com/sailing-yacht-heritage/oceanis-2005-2014
- https://www.beneteau.com/oceanis-2005-2014/oceanis-37

### Catalina Yachts

Catalina's current model pages and official brochure archive are strong evidence sources. Current Catalina 316 specifications demonstrate configuration-sensitive physical values: shoal-bulb and fin keels have different draft, ballast and half-load displacement, while the page also distinguishes sail-area bases.

**Reviewed sources:**
- https://www.catalinayachts.com/brochure-archives/
- https://www.catalinayachts.com/cruiser-series/catalina-316/
- https://www.catalinayachts.com/history/

### Jeanneau

Current and archived model pages expose basic dimensions and designers. Separate product/news/inventory material may reveal factory option axes that the summary specification does not expose.

Observed Sun Odyssey 410 example: standard-keel information is on the model page, while official Jeanneau material separately documents a lifting-keel form. Source discovery therefore needs bounded link/document expansion beyond one URL.

**Reviewed sources:**
- https://www.jeanneau.com/boats/sailboat/2-sun-odyssey/629-sun-odyssey-410
- https://www.jeanneau.com/articles/1558-news-2020-jeanneau-sailboats

### Dragonfly / Quorning Boats

Dragonfly's official specifications and manuals are strong multihull evidence. Dragonfly 32 Touring vs Evolution changes centre-hull length, sailing/folded beam, dry weight, mast height and sail area. Centreboard draft is stated board-up and board-down.

### Specialist manufacturer evidence added by the seed

The seed expanded the serious manufacturer source set to include:

- Alubat / OVNI — aluminium centreboarders and board-state measurements;
- Pogo Structures — legacy performance designs and twin-rudder evidence;
- RM Yachts — live configurator proving independent keel/rudder option axes;
- Garcia — twin rudders each protected by a skeg;
- Boréal — aluminium centreboarder successor identity and single-rudder contrast;
- Island Packet — proprietary keel terminology plus skeg-hung rudder;
- Corsair — trimaran folding-state geometry and Sport rig variant;
- Lagoon — strong current common specs but sparse rudder/keel taxonomy;
- Najad — official legacy PDF with an internal translation conflict;
- Rustler — explicit long-keel / keel-hung taxonomy plus unusually strong manufacturer guidance about measurement-basis ambiguity.

This breadth makes it unlikely that a generic scraper can safely map all manufacturers to one flat record without source-specific observation semantics and review paths.

---

## 3. Owner/class/specialist archives

**Class:** generally `SECONDARY_VERIFY` unless an underlying official document is separately identified.

### Westerly Owners Association / Westerly Wiki

Useful for a defunct builder and original-document discovery. The Centaur case exposed both detailed appendage prose and an internal production-count discrepancy.

### Good Old Boat / Seafarer 26

The Seafarer 26 case provides a high-value secondary edge case: fin keel, rudder hung on a partial skeg, and an explicit note that an earlier different Seafarer 26 existed. It demonstrates why reputable specialist secondary sources remain necessary for defunct/small builders, while still requiring provenance and ideally primary corroboration.

### World Sailing / International class associations

World Sailing-recognised class rules can be authoritative for class constraints. The J/24 case demonstrates that class rules and measurement documents are a distinct source shape: they describe permitted/toleranced geometry, which must not automatically be treated as nominal production values.

---

## 4. ORC certificate / rating data

**Class:** `BLOCKED` for HullQ commercial/systematic ingestion under the published terms reviewed during SLICE-0002 unless ORC grants a separate licence/permission.

### Technical value

ORC currently reports more than 14,000 active certificates across 45 countries and exposes active certificates through public data surfaces. The data is extremely attractive for measurement semantics and racing-yacht coverage.

### Rights blocker

The terms reviewed for SLICE-0002 prohibit the systematic/commercial database-building use needed by HullQ without separate authorisation. Therefore public transparency/downloadability is **not** treated as production clearance.

### Current recommendation

Do not ingest ORC certificate values into HullQ production or use them as seed facts. Retain ORC as:

- evidence of real measurement-field semantics;
- a possible future commercial partnership/licensing lead;
- a reminder that technical accessibility and reuse rights are separate gates.

**Reviewed sources:**
- https://orc.org/offshore-racing-congress---website-terms-of-use
- https://orc.org/sailors/active-certificates-database
- https://data.orc.org/active

---

## 5. Third-party open/mixed data projects

### sailboat-database.com

**Class:** `REFERENCE_ONLY`.

At review time the site reports 1,062 indexed production sailboats and says its data is sourced from Wikidata and enriched from Wikipedia infoboxes. This is strong evidence of practical four-digit Wikimedia-derived coverage but is **not** a HullQ bootstrap dataset because the site mixes CC0 Wikidata and CC-BY-SA Wikipedia ancestry.

HullQ should consume cleared Wikidata directly and independently enrich it.

### Third-party ORC-data repositories

Open-source licensing of repository **code** does not override rights or terms governing underlying ORC Certificate Data.

---

## Recommended acquisition hierarchy

```text
Wikidata CC0
  ↓ broad identity + common-field seed
Canonical candidate queue
  ↓
Manufacturer / designer / official archive evidence
  ↓
Association / class / specialist archive evidence where primary material is absent
  ↓
FieldEvidence + conflicts + explicit unknowns
  ↓
Human review where source conflicts, generation ambiguity, proprietary taxonomy,
configurator state, diagrams or appendage semantics require it
```

## What the 21-case evidence sample says about automation

- Useful common specs directly available: 18/21 (86%).
- Explicit keel/board architecture: 17/21 (81%).
- Explicit rudder/support architecture: 13/21 (62%).
- Explicit skeg/skegless state: 7/21 (33%).
- Option-sensitive core values: 8/21 (38%).
- Multiple source surfaces already required: 7/21 (33%).
- Explicit source conflicts: 2/21 (10%).
- Explicit non-generic mass/displacement basis labels: 11/21 (52%).

The sample is intentionally difficult, so these are not fleet-wide completeness estimates. The operational conclusion is nevertheless strong: **breadth can be automated much more aggressively than deep appendage verification.**

### Explicit non-paths

- Do not replace SailboatData with another commercial/community database of unclear rights.
- Do not infer bulk reuse permission from public access/download buttons.
- Do not import ORC data without separate permission/licence.
- Do not bulk-copy mixed Wikidata/Wikipedia derived datasets merely because part of their ancestry is CC0.
- Do not make `manufacturer source` a global trust override: authority is field-specific and primary sources can conflict internally.

## Evidence-derived requirements for later implementation

The source research proves the later pipeline needs distinct capabilities for:

1. structured open bootstrap acquisition with qualifiers and source IDs;
2. rights/access gate before any automated source use;
3. immutable raw observation preservation;
4. semantic measurement normalization preserving source basis;
5. generation/variant/option-aware values;
6. independent keel/rudder/skeg relationships and counts;
7. source expansion from model page to linked brochure/manual/parts/configurator surfaces;
8. explicit conflicts and unknowns;
9. PDF/document extraction separated from canonical resolution;
10. diagram/manual human-review path for hard appendage/construction facts;
11. volatile-source timestamps for configurators;
12. field-specific evidence resolution rather than whole-source precedence.

## Remaining SLICE-0002 work

The source landscape itself is sufficiently developed for handoff. Remaining work is to:

- finalize the seed/coverage research package and completion report;
- refine the immediate implementation slice boundaries from the evidence;
- move SLICE-0002 to `REVIEW`, not `DONE`.
