# HullQ — Design Data Field Coverage Matrix

**Status:** IN PROGRESS — SLICE-0002 checkpoint 2  
**Reviewed:** 2026-08-18

This matrix reflects observed source behaviour from the 20-design core seed sample plus the Seafarer 26 partial-skeg supplement (`n=21`). The counts below are evidence checks, not product-wide completeness estimates.

## Quantitative checkpoint

The following counts were coded conservatively from the research notes: a field/group counts only when the reviewed source explicitly exposed it strongly enough to support that category.

| Observed condition | Count | Share | Interpretation |
|---|---:|---:|---|
| Useful common specifications directly available from the reviewed source surface | 18/21 | 86% | Identity/common dimensions are strong automation candidates. |
| Keel / board architecture explicitly classifiable | 17/21 | 81% | Keel/board class is usually sourceable, though often option-sensitive. |
| Rudder and/or rudder-support architecture explicitly described | 13/21 | 62% | Rudder architecture is materially less complete than common dimensions. |
| Skeg state explicitly described, including explicit `skegless` | 7/21 | 33% | Skeg is a high-value, low-availability HullQ field. |
| Option/variant changes at least one core technical value | 8/21 | 38% | Configuration-aware storage/normalization is not an edge feature. |
| Research already required more than one source/page/document surface | 7/21 | 33% | A single canonical model URL will not reliably complete records. |
| Explicit source conflict observed | 2/21 | 10% | Conflicts occur even in manufacturer/strong archival evidence. |
| Explicit non-generic displacement/mass basis label observed | 11/21 | 52% | Basis-preserving measurement normalization is mandatory. |

These shares are **not** forecasts for the eventual 5,000–10,000+ universe. The seed was intentionally biased toward difficult designs and source shapes. They are suitable for deciding what the research pipeline must be able to represent.

Legend:
- `COMMON` — repeatedly exposed directly in structured/model-page text.
- `SOMETIMES` — present in some serious sources but not consistently.
- `RARE` — generally requires deeper documents or specialist sources.
- `DIAGRAM/REVIEW` — often needs drawing/manual/image interpretation or explicit human review.
- `UNKNOWN` — insufficient evidence in the current sample.

| HullQ field | Wikidata CC0 | Manufacturer current/heritage | Brochure/manual | Owner/class archive | Observed status | Notes |
|---|---|---|---|---|---|---|
| manufacturer / brand | COMMON | COMMON | COMMON | COMMON | COMMON | Identity distinction between brand/builder still needs source-specific handling. |
| model | COMMON | COMMON | COMMON | COMMON | COMMON | Reused model numbers/names create generation ambiguity. Seafarer 26 is an explicit example. |
| BoatDesign generation | RARE | SOMETIMES | SOMETIMES | SOMETIMES | SOMETIMES | HR 36 Mk I/Mk II and Nauticat 33→331 are explicit; many sources do not formalise generation. |
| designer | COMMON/SOMETIMES | COMMON | COMMON | COMMON | COMMON | Wikidata model expects designer but item completeness varies. |
| builder | SOMETIMES | COMMON | COMMON | COMMON | COMMON | Manufacturer may equal builder, but not always. |
| first built | SOMETIMES | SOMETIMES | SOMETIMES | COMMON | SOMETIMES | Heritage/class archives can be excellent. |
| last built | RARE/SOMETIMES | SOMETIMES | SOMETIMES | COMMON | SOMETIMES | Often implicit from archive period rather than model page. |
| number built | RARE | SOMETIMES | RARE | SOMETIMES | SOMETIMES | HR/J24 strong; Westerly/Najad demonstrate conflict risk. |
| LOA / hull length | COMMON | COMMON | COMMON | COMMON | COMMON | Preserve whether source means hull length vs overall including appendages. |
| LWL | SOMETIMES | SOMETIMES | COMMON/SOMETIMES | COMMON | SOMETIMES | Frequently absent from modern marketing summary pages. |
| beam | COMMON | COMMON | COMMON | COMMON | COMMON | Multihulls may need sailing vs folded beam distinction. |
| draft | COMMON/SOMETIMES | COMMON | COMMON | COMMON | COMMON | Often option/state-sensitive; board-up/down and shallow/deep are distinct. |
| displacement | COMMON/SOMETIMES | COMMON | COMMON | COMMON | COMMON | Basis varies: empty, lightship, half-load, measurement trim, EEC light, unspecified. |
| ballast | SOMETIMES | SOMETIMES/COMMON | COMMON | COMMON | SOMETIMES | Not applicable to many multihulls; can vary by keel option. |
| sail area | SOMETIMES | SOMETIMES | COMMON | COMMON | SOMETIMES | Basis varies widely: working sails, foretriangle, genoa, individual sails. |
| hull configuration mono/cat/tri | COMMON | COMMON | COMMON | COMMON | COMMON | Straightforward at broad class level. |
| keel type/subtype | BASIC/SOMETIMES | SOMETIMES/COMMON | COMMON | COMMON | SOMETIMES | 17/21 seed cases yielded explicit keel/board architecture. Proprietary terms must be preserved raw. |
| rudder type / architecture | RARE | RARE/SOMETIMES | SOMETIMES | SOMETIMES | RARE / DIAGRAM/REVIEW | 13/21 had explicit rudder/support architecture; exact canonical subtype is often still review work. |
| skeg state/type | RARE | RARE | RARE/SOMETIMES | SOMETIMES | RARE / DIAGRAM/REVIEW | Only 7/21 explicitly exposed skeg/skegless state. Partial-skeg case added via Seafarer 26. |
| rig | BASIC/SOMETIMES | SOMETIMES/COMMON | COMMON | COMMON | SOMETIMES | HR 42E and Corsair 880 show option/variant-sensitive rigs. |
| construction material | SOMETIMES | SOMETIMES | COMMON/SOMETIMES | SOMETIMES | SOMETIMES | Aluminium/GRP/plywood-epoxy often available. |
| construction method | RARE | SOMETIMES | SOMETIMES | RARE | RARE | Single-skin/sandwich/infusion/laminate detail requires deeper documentation. |
| shallow/deep keel options | RARE | SOMETIMES | COMMON | SOMETIMES | SOMETIMES | Catalina, Hallberg-Rassy, Jeanneau and Nauticat examples. |
| lifting/centreboard up/down draft | RARE | COMMON when applicable | COMMON | COMMON | COMMON when applicable | Requires state-paired semantics rather than one scalar draft. |
| tall/alternate rig option | RARE | SOMETIMES | COMMON | SOMETIMES | SOMETIMES | Can change sail area, mast height and derived metrics. |
| alternate rudder option | RARE | RARE/SOMETIMES | RARE | RARE | RARE | RM 1180 proves this exists as a factory option axis. |
| engine | RARE | COMMON/SOMETIMES | COMMON | COMMON | SOMETIMES | Secondary field; often easier in manuals. |
| fuel / water tanks | RARE | COMMON/SOMETIMES | COMMON | SOMETIMES | SOMETIMES | Useful cruising data, often better in manuals/brochures. |
| headroom | RARE | SOMETIMES | SOMETIMES | SOMETIMES | RARE/SOMETIMES | Not a broad bootstrap field. |
| CE category | RARE | COMMON for modern EU boats | COMMON | RARE | SOMETIMES | Not available for older designs; may vary by configuration. |

## Observed semantic hazards

### Length

Sources distinguish, depending on builder and boat type:
- overall length;
- hull length / LOD;
- centre-hull length;
- length including bowsprit/attachments;
- folded/storage geometry for multihulls.

Rustler's manufacturer guidance explicitly warns that builders do not use LOA/model-number conventions uniformly. A generic `length` parser without source semantics would silently create false comparisons.

### Draft

Observed forms include:
- fixed standard draft;
- shallow/deep factory alternatives;
- centreboard/daggerboard up and down values;
- lifting-keel states;
- customisable draft;
- draft tied to an empty-standard configuration.

Draft must be attached to configuration/state where relevant.

### Displacement

Observed labels include:
- empty standard boat;
- lightship displacement;
- dry boat ready to sail;
- half-load displacement;
- light measurement trim;
- unladen weight;
- EEC light displacement;
- generic/unspecified displacement.

Rustler's own technical guidance separately distinguishes lightship, half-load/sailing-load and full-load displacement. HullQ must preserve the source basis rather than normalising these to one semantic value silently.

### Sail area

Observed forms include:
- working jib;
- furling genoa;
- 100% foretriangle;
- standard 135% genoa;
- separate main/genoa/staysail;
- Code 0 / asymmetric spinnaker;
- variant-specific Touring/Evolution/Sport rig areas.

This directly validates the accepted `sail_area_basis` model.

### Options / variants / appendages

Observed real shapes include:
- HR 36 Mk I vs Mk II generation plus shallow-draft option;
- HR 42E ketch/sloop plus shallow/deep draft combinations;
- Catalina 316 fin vs shoal keel with different ballast/displacement;
- Jeanneau Sun Odyssey 410 standard vs lifting keel;
- Dragonfly 32 Touring vs Evolution with geometry/rig/weight changes;
- RM 1180 independent keel and rudder option axes;
- Corsair 880 vs 880 Sport rig/performance variant;
- Nauticat 33→331 new-hull generation boundary;
- Seafarer 26 reused name across distinct designs;
- Garcia twin rudders each protected by a skeg;
- Island Packet proprietary Full Foil Keel + skeg-hung rudder;
- Rustler long keel + keel-hung rudder;
- Najad long keel + separate skeg/rudder;
- Seafarer 26 fin keel + partial-skeg-hung rudder.

An ingestion pipeline must not flatten these into one arbitrary scalar set or infer appendage relationships from one legacy `hull_type` label.

## Automation / human-review estimate from the seed

The evidence supports a **layered**, not single-percentage, automation expectation:

### High automation potential

- CC0 structured identity/common-field acquisition;
- clean manufacturer HTML tables;
- deterministic metric/imperial conversion when the source semantic is explicit;
- structurally paired option values;
- raw-source and provenance capture.

### Medium automation + targeted review

- generation boundaries in prose/hull-number history;
- option discovery across multiple official pages/documents;
- displacement/sail-area basis classification;
- proprietary keel terms;
- configurator-derived option axes;
- class-rule limits vs nominal values.

### Human-review-heavy

- rudder/skeg subtype when drawings/prose/parts imply geometry rather than state it canonically;
- source-internal and cross-source conflicts;
- reused historical model names;
- semi-custom configuration boundaries;
- image/diagram-assisted appendage classification.

At the record level, common specifications were directly obtainable for 86% of this intentionally difficult seed, but explicit skeg state for only 33%. This is the clearest current signal that HullQ can automate **breadth** much more aggressively than **deep appendage verification**.

## Pipeline implications proven by evidence

The later implementation needs to support at least:

1. structured Wikidata/RDF/API-style statements and qualifiers;
2. manufacturer HTML specification tables;
3. linked brochures/manuals/PDFs as deeper evidence;
4. mixed metric/imperial units;
5. raw field-semantic labels retained alongside normalized numeric values;
6. multiple concurrent factory configurations/options;
7. independent keel/rudder/skeg relationships and counts;
8. generation boundaries by year/hull number/new-hull evidence;
9. source conflicts, including conflict inside one primary document;
10. explicit `unknown` without converting absence into false;
11. manual/diagram review path for appendages and some construction fields;
12. provenance from every accepted canonical value to exact source observation;
13. access-policy enforcement distinct from content licence/rights clearance;
14. timestamped handling for volatile source surfaces such as configurators.
