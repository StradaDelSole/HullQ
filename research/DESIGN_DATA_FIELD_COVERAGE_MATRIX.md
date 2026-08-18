# HullQ — Design Data Field Coverage Matrix

**Status:** IN PROGRESS — SLICE-0002 checkpoint 1  
**Reviewed:** 2026-08-18

This matrix reflects **observed source behaviour from the first real-source research pass**. It is provisional until the 20–30-design seed sample is complete.

Legend:
- `COMMON` — repeatedly exposed directly in structured/model-page text.
- `SOMETIMES` — present in some serious sources but not consistently.
- `RARE` — generally requires deeper documents or specialist sources.
- `DIAGRAM/REVIEW` — often needs drawing/manual/image interpretation or explicit human review.
- `UNKNOWN` — insufficient evidence in the current sample.

| HullQ field | Wikidata CC0 | Manufacturer current/heritage | Brochure/manual | Owner/class archive | Observed status | Notes |
|---|---|---|---|---|---|---|
| manufacturer / brand | COMMON | COMMON | COMMON | COMMON | COMMON | Identity distinction between brand/builder still needs source-specific handling. |
| model | COMMON | COMMON | COMMON | COMMON | COMMON | Reused model numbers/names create generation ambiguity. |
| BoatDesign generation | RARE | SOMETIMES | SOMETIMES | SOMETIMES | SOMETIMES | HR 36 Mk I/Mk II is excellent explicit evidence; many sources do not formalise generation. |
| designer | COMMON/SOMETIMES | COMMON | COMMON | COMMON | COMMON | Wikidata model expects designer but item completeness varies. |
| builder | SOMETIMES | COMMON | COMMON | COMMON | COMMON | Manufacturer may equal builder, but not always. |
| first built | SOMETIMES | SOMETIMES | SOMETIMES | COMMON | SOMETIMES | Catalina history and HR archive can be excellent. |
| last built | RARE/SOMETIMES | SOMETIMES | SOMETIMES | COMMON | SOMETIMES | Often implicit from archive period rather than model page. |
| number built | RARE | SOMETIMES | RARE | SOMETIMES | SOMETIMES | HR and Westerly examples show it can be strong when available. |
| LOA / hull length | COMMON | COMMON | COMMON | COMMON | COMMON | Must preserve whether source means hull length vs overall including appendages. |
| LWL | SOMETIMES | SOMETIMES | COMMON/SOMETIMES | COMMON | SOMETIMES | Frequently absent from modern marketing summary pages. |
| beam | COMMON | COMMON | COMMON | COMMON | COMMON | Multihulls may need sailing vs folded beam distinction. |
| draft | COMMON/SOMETIMES | COMMON | COMMON | COMMON | COMMON | Often option-sensitive; board-up/down and shallow/deep are separate states. |
| displacement | COMMON/SOMETIMES | COMMON | COMMON | COMMON | COMMON | Basis varies: empty, lightship, half-load, sailing trim, unspecified. |
| ballast | SOMETIMES | SOMETIMES/COMMON | COMMON | COMMON | SOMETIMES | Not applicable to many multihulls; can vary by keel option. |
| sail area | SOMETIMES | SOMETIMES | COMMON | COMMON | SOMETIMES | Basis is highly variable: working jib, 100% foretriangle, genoa, actual sails, etc. |
| hull configuration mono/cat/tri | COMMON | COMMON | COMMON | COMMON | COMMON | Straightforward at broad class level. |
| keel type/subtype | BASIC/SOMETIMES | SOMETIMES/COMMON | COMMON | COMMON | SOMETIMES | Marketing pages often give draft without a canonical keel taxonomy label. |
| rudder type | RARE | RARE/SOMETIMES | SOMETIMES | SOMETIMES | RARE / DIAGRAM/REVIEW | Westerly Centaur text explicitly says skegless spade; many manufacturer pages omit rudder type. |
| skeg type | RARE | RARE | RARE/SOMETIMES | SOMETIMES | RARE / DIAGRAM/REVIEW | Likely one of HullQ's hardest high-value fields. |
| rig | BASIC/SOMETIMES | SOMETIMES/COMMON | COMMON | COMMON | SOMETIMES | HR 42E shows ketch/sloop as same design-axis option; Dragonfly shows performance rig variants. |
| construction material | SOMETIMES | SOMETIMES | COMMON/SOMETIMES | SOMETIMES | SOMETIMES | Usually easier than construction method. |
| construction method | RARE | SOMETIMES | SOMETIMES | RARE | RARE | E.g. single-skin, sandwich, infusion, aluminium details require deeper documentation. |
| shallow/deep keel options | RARE | SOMETIMES | COMMON | SOMETIMES | SOMETIMES | Catalina, Hallberg-Rassy, Jeanneau provide strong examples. |
| lifting/centreboard up/down draft | RARE | COMMON when applicable | COMMON | COMMON | COMMON when applicable | Requires paired/range semantics rather than one scalar draft. |
| tall/alternate rig option | RARE | SOMETIMES | COMMON | SOMETIMES | SOMETIMES | Can change sail area, mast height and derived metrics. |
| alternate rudder option | RARE | RARE | RARE | RARE | UNKNOWN/RARE | No strong general-purpose source found yet. |
| engine | RARE | COMMON/SOMETIMES | COMMON | COMMON | SOMETIMES | Not central to first HullQ search but useful secondary field. |
| fuel / water tanks | RARE | COMMON/SOMETIMES | COMMON | SOMETIMES | SOMETIMES | Useful cruising data, often better in manuals/brochures. |
| headroom | RARE | SOMETIMES | SOMETIMES | SOMETIMES | RARE/SOMETIMES | Not a broad bootstrap field. |
| CE category | RARE | COMMON for modern EU boats | COMMON | RARE | SOMETIMES | Not available for older designs; may vary by layout/crew configuration. |

## Observed semantic hazards

### Length

Sources may distinguish:
- overall length;
- hull length;
- centre-hull length;
- length including rudder/bowsprit;
- folded/storage length for multihulls.

A single generic `length` parser is insufficient without source semantics.

### Draft

Observed forms include:
- fixed standard draft;
- shallow/deep factory alternatives;
- keel/board up and down values;
- customisable draft;
- draft measured on an empty standard boat.

Draft must be attached to configuration and basis where relevant.

### Displacement

Observed labels include:
- empty standard boat;
- lightship displacement;
- dry boat ready to sail;
- half-load displacement;
- sailing-trim displacement;
- generic/unspecified displacement.

HullQ must retain the source label/basis rather than normalising these to one semantic value silently.

### Sail area

Observed forms include:
- working jib;
- furling genoa;
- 100% foretriangle;
- standard 135% genoa;
- separate main/genoa;
- Code 0 / asymmetric spinnaker;
- Touring vs Evolution rig areas.

This directly validates the need for the accepted `sail_area_basis` model.

### Options / variants

The first sample already contains several different shapes:
- HR 36 Mk I vs Mk II generation, plus shallow-draft option;
- HR 42E ketch/sloop plus shallow/deep draft combinations;
- Catalina 316 fin vs shoal keel with different ballast/displacement;
- Jeanneau Sun Odyssey 410 standard vs lifting keel;
- Dragonfly 32 Touring vs Evolution with geometry/rig/weight changes;
- CATANA semi-custom dimensions/options.

An ingestion pipeline must not flatten these into one arbitrary scalar set.

## Interim pipeline implications proven by evidence

The later implementation will need to support at least:

1. structured Wikidata/RDF/API-style statements and qualifiers;
2. manufacturer HTML specification tables;
3. linked brochures/manuals/PDFs as deeper evidence;
4. mixed metric/imperial units;
5. field-semantic labels retained alongside numeric values;
6. multiple concurrent factory configurations/options;
7. generation boundaries by year/hull number when explicitly documented;
8. source conflicts and explicit unknowns;
9. manual/diagram review path for rudder/skeg and some construction fields;
10. provenance from every accepted canonical value back to the exact source observation.
