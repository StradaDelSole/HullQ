# HullQ — Design Data Source Landscape

**Status:** IN PROGRESS — SLICE-0002 research checkpoint 1  
**Reviewed:** 2026-08-18  
**Purpose:** Evidence-first assessment of real sailboat-design data sources before HullQ research-pipeline implementation.

This document records observed source availability, source shape, likely HullQ usefulness, and rights/access constraints. It is not a production-source whitelist. Final clearance remains governed by `specs/SOURCE_RIGHTS_POLICY.v0.1.md` and ADR-0005.

## Current conclusion

The first research pass supports a **two-layer acquisition strategy** rather than searching for one replacement for SailboatData:

1. **broad open identity/common-field bootstrap**, with Wikidata currently the strongest serious candidate;
2. **progressive primary-source enrichment**, using manufacturer heritage pages, brochures, manuals, class/owner-association technical material and other cleared evidence for deeper fields and option/generation resolution.

No single source found so far provides SailboatData-like breadth plus HullQ-critical keel/rudder/skeg/configuration depth under clearly reusable commercial terms.

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
**Rights basis:** Wikidata main/property/lexeme structured data is CC0. Wikimedia API usage rules separately require identifiable User-Agent behaviour, rate-limit compliance and licence compliance.

### Observed sailboat data model

Wikidata has an explicit `sailboat class` data model (`Q106179098`) intended for specific sailboat designs/models. The Sailing WikiProject model includes:

- manufacturer;
- designer;
- LOA and LWL as qualified length statements;
- beam;
- draft / air draft;
- displacement and ballast as qualified mass statements;
- boat-type subclasses such as monohull/multihull, catamaran/trimaran, rig and keelboat/centerboarder concepts.

EntitySchema E297 formalises these concepts.

### Strengths

- CC0 structured-data basis is compatible with HullQ's preferred bootstrap policy.
- Machine-readable identifiers and statements are well suited to broad identity seeding.
- Existing sailing-specific modelling already overlaps with HullQ basic fields.
- Dumps can reduce dependence on high-volume per-item API calls.

### Weaknesses / unresolved

- Statement completeness is inconsistent.
- Reference quality varies by item and statement.
- The Wikidata sailboat-class model does not itself solve HullQ generation/variant/configuration identity.
- HullQ-critical rudder/skeg/construction detail appears outside the core schema and is expected to be much sparser.
- Exact current **CC0-only** count of usable sailboat-class identities still needs to be measured directly from Wikidata rather than inferred from third-party sites.

### Current recommendation

Treat Wikidata as the leading broad identity/common-field bootstrap candidate. Import should retain Wikidata item ID and statement-level provenance and must not treat CC0 as an accuracy guarantee.

**Reviewed sources:**
- https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Data_Models/Sailboat_class
- https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Data_Models/Sailboat_class/Properties
- https://www.wikidata.org/wiki/EntitySchema:E297
- https://www.wikidata.org/wiki/Wikidata:Licensing
- https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines

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

The HR 36 page is especially valuable because it states exactly what changed between Mk I and Mk II and what remained identical. The HR 42E page demonstrates late-added sloop vs ketch and shallow-vs-deep keel axes inside one design lineage.

**Reviewed sources:**
- https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-36
- https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-42e
- https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-31-mk-ii

### BENETEAU heritage

BENETEAU maintains multi-generation heritage navigation for Oceanis / First and other historic ranges. Range pages expose model lists, model grouping by production era/generation, and common dimensions. Individual pages can provide designer, LOA, beam, lightship displacement and downloadable brochures/equipment lists.

Observed example: Oceanis 37 page gives LOA, beam, lightship displacement, air draft and designers but not all HullQ-critical keel/rudder details directly in the HTML summary. This is a good example of why brochure/manual enrichment remains necessary.

**Reviewed sources:**
- https://www.beneteau.com/sailing-yacht-heritage
- https://www.beneteau.com/sailing-yacht-heritage/oceanis-2005-2014
- https://www.beneteau.com/oceanis-2005-2014/oceanis-37

### Catalina Yachts

Catalina's current model pages and official brochure archive are strong evidence sources. The archive contains brochures for many historical Catalina/Morgan designs and explicit Mk II / keel-layout variants.

Current Catalina 316 specifications demonstrate configuration-sensitive physical values: shoal-bulb and fin keels have different draft, ballast and displacement, while the page also distinguishes sail-area bases.

**Reviewed sources:**
- https://www.catalinayachts.com/brochure-archives/
- https://www.catalinayachts.com/cruiser-series/catalina-316/
- https://www.catalinayachts.com/history/

### Jeanneau

Current and archived model pages expose basic dimensions and designers. Separate product/news/inventory material may reveal factory option axes that the summary specification does not expose.

Observed Sun Odyssey 410 example: main page exposes 8,000 kg displacement and 2.14 m standard-keel draft; Jeanneau also documents a lifting-keel version with 1.37 m draft when raised. This means one model page alone is insufficient to discover all configurations.

**Reviewed sources:**
- https://www.jeanneau.com/boats/sailboat/2-sun-odyssey/629-sun-odyssey-410
- https://www.jeanneau.com/articles/1558-news-2020-jeanneau-sailboats

### Dragonfly / Quorning Boats

Dragonfly's official specifications and manuals are strong multihull evidence. Dragonfly 32 is explicitly offered as Touring and Evolution versions with different centre-hull length, beam, dry weight, mast height and sail areas while sharing other dimensions. Centreboard draft is stated both board-up and board-down.

This source is particularly useful for testing HullQ's `NamedVariant` / option boundaries and multihull applicability.

**Reviewed sources:**
- https://dragonfly.dk/dragonfly-32-specifications/
- https://dragonfly.dk/boats/dragonfly-32/
- https://dragonfly.dk/owners-manuals/

### CATANA

CATANA model pages expose catamaran dimensions, board-up/board-down draft, light displacement, designer and construction/feature descriptions. Current Ocean Class also explicitly marks some dimensions as customisable.

This is useful evidence that multihull technical fields can be sourceable from builders, while semi-custom configuration may need a different confidence/model treatment from fixed production options.

**Reviewed source:**
- https://www.catana.com/en/catamarans/ocean-class/

---

## 3. Owner/class association archives

**Class:** `SECONDARY_VERIFY` unless a specific underlying official document is separately identified.  
**Rights:** individual factual research useful; bulk database reuse not assumed.

### Westerly Owners Association / Westerly Wiki

The Westerly Wiki contains model statistics, brochures and references to official Westerly documents. The Centaur page provides LOA, LWL, beam, draft, displacement, ballast, rig, years, production count and explicitly describes a balanced skegless spade rudder; it also links original brochures/manual material.

This is high-value evidence for discontinued builders where manufacturer websites no longer exist, but provenance should ideally descend to the original Westerly document where practical.

**Reviewed sources:**
- https://wiki.westerly-owners.co.uk/index.php?title=Centaur
- https://wiki.westerly-owners.co.uk/index.php?title=Westerly_Brochures

---

## 4. World Sailing class documents

**Class:** `SECONDARY_VERIFY` / specialist primary rules authority for recognised racing classes.  
**Coverage:** racing/one-design classes, not a broad production-cruiser universe.

World Sailing class pages and document search expose current class rules. Class rules are structured around boat/equipment constraints and can be authoritative for dimensions/configuration in recognised classes. They are useful for benchmark edge cases and certain production/race designs but cannot serve as HullQ's broad cruising-yacht bootstrap.

Bulk/content reuse rights have not yet been cleared for HullQ and must not be assumed from public downloadability.

**Reviewed source:**
- https://www.sailing.org/inside-world-sailing/activities-services/technical-offshore/technical-services/class-rules/

---

## 5. ORC certificate / rating data

**Class:** `BLOCKED` for HullQ commercial/systematic ingestion under current published Terms unless ORC grants a separate licence/permission.

### Technical value

ORC publicly exposes active certificate data and rating files in structured formats including JSON/CSV/RMS. Current ORC materials state more than 14,000 active certificates across 45 countries and more than 208,000 historical measurement records in Sailor Services. Fields can include designer, builder, type, year, LOA, draft, beam, displacement, sailing-trim displacement and sail dimensions.

### Rights blocker

Current ORC Terms state that Certificate Data and database content are ORC property and prohibit, without prior written authorisation/licence:

- automated scraping/harvesting;
- systematic collection or aggregation, including manually;
- creation/maintenance of a database or service reproducing ORC data;
- commercial use;
- AI/ML training/prompting/instruction using ORC Content.

Therefore the mere existence of public JSON/CSV/RMS downloads **does not clear ORC data for HullQ**.

### Current recommendation

Do not use ORC certificate values in HullQ production or the seed corpus. Retain ORC as evidence of useful field semantics and as a possible future partnership/licensing lead only.

**Reviewed sources:**
- https://orc.org/offshore-racing-congress---website-terms-of-use
- https://orc.org/sailors/active-certificates-database
- https://orc.org/race-managment/rms-files
- https://data.orc.org/public/WPub.dll/RMS?dox=1

---

## 6. Third-party open/mixed data projects

### sailboat-database.com

**Class:** `REFERENCE_ONLY` for now.

The site currently reports 1,062 indexed boats and states that its data is sourced from Wikidata and enriched from Wikipedia infoboxes. This is useful evidence that open Wikimedia sources can produce a four-digit sailboat catalogue, but the site's own description mixes CC0 Wikidata with CC-BY-SA Wikipedia material.

HullQ should therefore query/ingest Wikidata directly rather than bulk-copy this derived database. The exact number and completeness of **Wikidata-only** sailboat records remains to be measured independently.

**Reviewed source:** https://sailboat-database.com/

### ORC-data GitHub projects

Third-party repositories may redistribute ORC downloads under an open-source **code** licence. That does not override ORC's current rights/Terms for the underlying Certificate Data. Do not confuse repository-code licensing with dataset clearance.

---

## Initial source hierarchy recommendation

```text
Wikidata CC0
  ↓ broad identity + common-field seed
Canonical candidate queue
  ↓
Manufacturer / designer / official archive evidence
  ↓
Association / original brochure/manual evidence where manufacturer archive is absent
  ↓
FieldEvidence + conflicts + explicit unknowns
  ↓
Human review only where source conflicts, diagrams, generation ambiguity or option semantics require it
```

### Explicit non-paths

- Do not replace SailboatData with another commercial/community database of unclear rights.
- Do not infer bulk reuse permission from public access/download buttons.
- Do not import ORC data without a separate permission/licence.
- Do not bulk-copy mixed Wikidata/Wikipedia derived datasets merely because part of their ancestry is CC0.

## Next research actions

1. measure current Wikidata sailboat-class identity count and field completeness directly;
2. add more builder/heritage archives, especially for discontinued brands and multihulls;
3. expand manual seed research to 20–30 designs;
4. quantify how often rudder/skeg/construction must come from drawings/manuals rather than structured text;
5. estimate human-review share from the complete seed sample.
