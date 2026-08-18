# HullQ — Seed Research Notes

**Status:** IN PROGRESS — SLICE-0002  
**Reviewed:** 2026-08-18  
**Target:** 20–30 representative designs  
**Current checkpoint:** 20 designs researched deeply enough to expose initial source/configuration patterns.

This is not the final benchmark corpus and not production canonical data. It is an evidence sample used to discover real source shapes, missing fields, conflicts and review needs before pipeline implementation.

---

## SEED-01 — Hallberg-Rassy 36

**Candidate identity:** Hallberg-Rassy 36, Mk I and Mk II as distinct BoatDesign generations under one commercial model lineage.  
**Primary source:** Hallberg-Rassy manufacturer archive.  
**URL:** https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-36

### Observed facts

- Built 1989–2003, 602 hulls total.
- Hulls 1–256 = Mk I; 257–602 = Mk II.
- Mk II hull length 11.31 m; Mk I 10.87 m.
- LWL at rest 9.35 m; beam 3.55 m.
- Standard empty-boat draft 1.70 m; optional 25 cm shallower version.
- Empty standard displacement 7.5 t; keel weight 3.4 t.
- Keel type stated as lead with bulb.
- Working-jib sail area 65 m²; furling-genoa sail area 70.2 m².
- Manufacturer explicitly says mast, keel, rudder and underwater shape remained the same between Mk I and Mk II.
- Hallberg-Rassy's official parts archive separately exposes a `Rudder Skeg Bearing RM36`, proving that appendage evidence may live outside the model page.

### Why this is difficult/useful

- Clear generation boundary tied to hull number and year.
- Physical values differ by generation while underwater appendages remain same.
- Shallow-draft option coexists with generation.
- Multiple sail-area bases are exposed on one page.
- Appendage detail requires another official source surface.

### Likely automation

- HTML table extraction: high confidence.
- Generation boundary extraction from prose: medium confidence / review desirable.
- Rudder/skeg classification: requires cross-page evidence rather than trusting a single model page.

---

## SEED-02 — Hallberg-Rassy 42E

**Candidate identity:** Hallberg-Rassy 42E (Enderlein), explicitly distinct from later Frers-designed 42F.  
**Primary source:** Hallberg-Rassy manufacturer archive.  
**URL:** https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-42e

### Observed facts

- Built 1980–1991, 255 units.
- Ketch initially; sloop introduced later.
- Same mast position, but sloop has taller mast.
- Deep keel standard; optional 30 cm shallower version using encapsulated lead keel rather than the standard encapsulated steel keel.
- Hull length 12.93 m; LWL 10.5 m; beam 3.78 m.
- Standard empty draft 2.05 m.
- Empty standard displacement 11,500 kg; keel weight 4,500 kg.
- Working-jib sail area differs by rig: ketch 79 m², sloop 75.5 m².
- Genoa sail area also differs by rig.
- Manufacturer explains that `42E` designation was added later to distinguish the design from 42F, while both boats may simply carry `42` markings.

### Why this is difficult/useful

- Reused commercial model number with two technically unrelated design generations.
- Historical naming itself changed after production.
- Orthogonal rig and keel axes exist inside the 42E design.
- Keel material changes with shallow-draft option.

### Likely automation

- Basic table facts: high confidence.
- Identity/generation distinction: explicit but prose-dependent; medium-high with evidence.
- Option Cartesian expansion must be controlled; do not materialise unsupported combinations blindly.

---

## SEED-03 — Catalina 316

**Candidate identity:** Catalina 316 with concurrent fin-keel and shoal-bulb factory configurations.  
**Primary source:** Catalina Yachts current manufacturer page.  
**URL:** https://www.catalinayachts.com/cruiser-series/catalina-316/

### Observed facts

- LOA 33 ft; hull length 31 ft; LWL 26 ft 6 in; beam 11 ft 7 in.
- Shoal-bulb keel: draft 4 ft 9 in, ballast 4,400 lb, half-load displacement 12,400 lb.
- Fin keel: draft 6 ft 3 in, ballast 4,000 lb, half-load displacement 12,000 lb.
- Sail area stated both with 100% foretriangle and standard 135% genoa.

### Why this is difficult/useful

- Same model/configuration family has option-sensitive displacement and ballast, not merely draft.
- Displacement basis is explicitly `Half Load`, which is nonstandard for HullQ canonical derived-metric slots under current OQ-001 policy.
- Multiple sail-area bases appear on one official page.

### Likely automation

- Structured HTML extraction: high.
- Correct configuration binding: essential; naive scalar model would be wrong.
- Derived metrics must return `nonstandard_input` for half-load displacement where the accepted metric spec requires design/lightship basis.

---

## SEED-04 — Jeanneau Sun Odyssey 410

**Candidate identity:** Sun Odyssey 410 with standard and lifting-keel factory forms.  
**Primary sources:** Jeanneau model page + manufacturer product/news documentation.  
**URLs:**
- https://www.jeanneau.com/boats/sailboat/2-sun-odyssey/629-sun-odyssey-410
- https://www.jeanneau.com/articles/1558-news-2020-jeanneau-sailboats

### Observed facts

- LOA 12.35 m; hull length 11.99 m; beam 3.99 m.
- Displacement 8,000 kg on current page.
- Standard-keel draft 2.14 m.
- Separate official Jeanneau material documents a lifting-keel version with draft 1.37 m when raised.
- Designer: Marc Lombard design group; interior/design contribution Jean-Marc Piaton/Piaton Yacht Design.

### Why this is difficult/useful

- Option is not fully exposed in the main model summary.
- Source discovery must look beyond one canonical model URL.
- One commercial design can have materially different underwater configuration.

### Likely automation

- Main-page facts: high.
- Complete option discovery from linked/current/archival documents: medium; likely requires targeted source expansion.

---

## SEED-05 — Dragonfly 32

**Candidate identity:** Dragonfly 32 with Touring and Evolution named/performance variants.  
**Primary source:** Quorning Boats / Dragonfly manufacturer specifications.  
**URL:** https://dragonfly.dk/dragonfly-32-specifications/

### Observed facts

Touring vs Evolution:
- centre-hull LOA 9.80 m vs 9.90 m;
- sailing beam 8.00 m vs 8.25 m;
- folded beam 3.60 m vs 3.85 m;
- board-up draft 0.55 m both;
- board-down draft 1.90 m both;
- dry ready-to-sail weight 3,400 vs 3,450 kg;
- mast over deck 14.70 vs 16.70 m;
- mainsail 48 vs 58 m²;
- genoa 26 vs 29 m².

### Why this is difficult/useful

- Multihull-specific geometry includes sailing and folded beam.
- Named variant changes geometry, weight, rig and sail area.
- Centreboard produces up/down draft pair rather than one scalar.
- Strong evidence that resolved configuration values must be option/variant sensitive.

### Likely automation

- HTML table: high.
- Variant mapping: high if headings retained.
- Generic monohull-oriented field assumptions would fail.

---

## SEED-06 — Westerly Centaur

**Candidate identity:** Westerly Centaur, discontinued large-volume British twin-keeler.  
**Secondary/archival source:** Westerly Owners Association Wiki, with references to official Westerly documents and original designer press material.  
**URL:** https://wiki.westerly-owners.co.uk/index.php?title=Centaur

### Observed facts

- Designer Laurent Giles.
- Twin keel.
- LOA 26 ft; LWL 21 ft 4 in; beam 8 ft 5 in; draft 3 ft.
- Displacement 6,700 lb; ballast 2,800 lb.
- Built 1969–1980; production count around 2,440+ (page contains slightly inconsistent 2,440 / 2,444 statements).
- Sloop/ketch noted, with very few ketches.
- Historical designer press text describes a balanced skegless spade rudder.

### Why this is difficult/useful

- Manufacturer is defunct; source chain moves to owner association + archived original documents.
- The same page itself contains a small production-count inconsistency.
- Rudder type is present in prose rather than the statistics table.
- Demonstrates why field-level provenance and conflict handling matter even in strong enthusiast archives.

### Likely automation

- Statistics table: high.
- Production count resolution: needs conflict/review.
- Rudder taxonomy from historical prose: medium-high with human review.
- Prefer original linked Westerly/Laurent Giles document as final evidence where practical.

---

## SEED-07 — BENETEAU Oceanis 37

**Candidate identity:** Oceanis 37 in BENETEAU's 2005–2014 Oceanis heritage generation.  
**Primary source:** BENETEAU heritage model page.  
**URL:** https://www.beneteau.com/oceanis-2005-2014/oceanis-37

### Observed facts

- Designers Jean-Marie Finot / Pascal Conq; Nauta Design interior.
- LOA 11.48 m; beam 3.92 m.
- Lightship displacement 6,515 kg.
- Air draft 16.65 m.
- Brochure and equipment-list downloads are linked.

### Why this is difficult/useful

- Heritage navigation clearly establishes family/era context.
- HTML summary is incomplete for HullQ-critical draft/keel/rudder fields.
- The source is authoritative but deeper documents must be traversed to build a useful technical record.

### Likely automation

- Summary facts: high.
- Critical appendage enrichment: deeper document extraction/review required.

---

## SEED-08 — CATANA Ocean Class

**Candidate identity:** CATANA Ocean Class production/semi-custom catamaran.  
**Primary source:** CATANA manufacturer page.  
**URL:** https://www.catana.com/en/catamarans/ocean-class/

### Observed facts

- Hull length 14.99 m; overall length 15.75 m.
- Overall beam approximately 7.98 m.
- Draft boards up 1.39 m; boards down 2.52 m.
- Light displacement 13.5 t.
- Designer Olivier Poncin / CATANA design context.
- Manufacturer describes carbon infusion construction and daggerboards.
- Some current dimensions/options are described as customisable.

### Why this is difficult/useful

- Catamaran + daggerboard configuration.
- Semi-customisation makes the boundary between canonical design facts and individual-build configuration important.
- Marketing/spec pages contain useful construction information not represented as tidy standard fields.

### Likely automation

- Basic dimensional table: high.
- Construction-method extraction: medium.
- Custom option semantics: review likely needed before canonicalising.

---

## SEED-09 — Rustler 36

**Candidate identity:** Rustler 36, traditional long-keel offshore cruiser.  
**Primary source:** Rustler Yachts technical design article.  
**URL:** https://www.rustleryachts.com/keel-design-explained/

### Observed facts

- Rustler explicitly describes the 36 as having a traditional long keel with cutaway forefoot.
- Rudder is explicitly `keel-hung`.
- Keel is encapsulated: the GRP keel is moulded as part of the hull and contains lead ballast.

### Why this is difficult/useful

- Provides an unusually explicit primary-source taxonomy statement for both keel and rudder.
- Current manufacturer navigation no longer exposes a normal Rustler 36 model-spec page, so deep legacy facts may require brochure/archive research despite the builder still existing.

### Likely automation

- Taxonomy extraction from technical prose: medium-high.
- Numeric enrichment: separate archived model/brochure source required.

---

## SEED-10 — OVNI 370

**Candidate identity:** OVNI 370 integral-centreboard aluminium monohull.  
**Primary source:** Alubat manufacturer page.  
**URL:** https://www.alubat.com/the-range/ovni-370/

### Observed facts

- 100% aluminium lifting/centreboard design.
- LOA and hull length 11.95 m; LWL 11.40 m; beam 3.99 m.
- Draft centreboard down 3.08 m; up 0.92 m.
- Light displacement 9,400 kg.
- Ballast 3,000 kg with a 260 kg keel stated separately.
- Upwind cutter sail area 67.5 m²; main 36 m²; Solent 31.5 m².
- Architects Mortain/Mavrikios and CBA.
- Manufacturer links brochure and technical specifications.

### Why this is difficult/useful

- Ballast and centreboard/keel values need semantic separation.
- Aluminium construction and integral-centreboard configuration are first-class differentiators.
- Up/down draft must remain paired with appendage state.

### Likely automation

- Main specification extraction: high.
- Correct interpretation of `ballast` vs separate keel/centreboard weight: review/contract-aware parsing required.

---

## SEED-11 — Pogo 1

**Candidate identity:** Pogo 1 / Mini-derived production design.  
**Primary source:** Pogo Structures manufacturer archive.  
**URL:** https://www.pogostructures.com/fiche-bateau/pogo-1/?lang=en

### Observed facts

- Built 1994–2002; 124 boats.
- Length 6.50 m; beam 2.97 m; light measurement trim 1,200 kg; draft 1.58 m.
- Twin rudders explicitly stated.
- Main 24 m²; genoa 18 m²; big spinnaker 72 m².
- Architect/designer Pierre Rolland; builder/development Pogo Structures.

### Why this is difficult/useful

- Modern twin-rudder monohull source states rudder count directly.
- `light measurement trim` is not automatically identical to HullQ's accepted displacement bases.
- Strong one-page legacy manufacturer archive despite the model being long discontinued.

### Likely automation

- Basic data/rudder count: high.
- Displacement-basis mapping: requires explicit semantic handling.

---

## SEED-12 — RM 1180

**Candidate identity:** RM 1180 with multiple factory appendage combinations.  
**Primary sources:** RM Yachts model page + manufacturer configurator.  
**URLs:**
- https://www.rm-yachts.com/en/rm-1180/
- https://www.rm-yachts.com/en/product/rm1180-2/

### Observed facts

- Hull length 11.80 m; beam 4.37 m; light displacement 7,700 kg.
- Single-keel draft 2.25 m; twin-keel draft 1.95 m.
- Manufacturer configurator currently exposes appendage choices including twin keel + single rudder, single keel + twin rudders, lifting keel + twin rudders, and twin keel + twin rudders.
- Plywood-epoxy construction.
- Main 46 m²; furling genoa 44 m²; asymmetric spinnaker 150 m².

### Why this is difficult/useful

- Appendage axes are explicitly combinatorial and cannot be collapsed into one `keel_type` plus one assumed rudder.
- Manufacturer's marketing specification and configurator expose different parts of the canonical option space.
- Configurator state is more volatile than stable model documentation.

### Likely automation

- Static specs: high.
- Configurator option discovery: medium/volatile; snapshot/evidence timestamp required.
- Strong evidence for independent keel and rudder option axes.

---

## SEED-13 — Nauticat 33 / transition to Nauticat 331

**Candidate identity:** Nauticat 33 historical lineage with later technically distinct Nauticat 331.  
**Primary sources:** Nauticat current heritage/history site and manufacturer-hosted pre-owned archive.  
**URLs:**
- https://nauticat.com/about_us
- https://nauticat.com/pre-owned_nauticats_old/tproduct/385449696412-nauticat-33-1983

### Observed facts

- Nauticat history states the original 33 dates to the 1960s and was designed by V. Aarnipalo.
- In 1997 the 33 was substantially modified; the 331 received a completely new hull and deck and was renamed.
- Nauticat says the 331 was offered with two keel versions/drafts: 1.48 m and 1.65 m.
- A manufacturer-hosted 1983 Nauticat 33 listing states that from 1982 a 1.60 m draft and skeg-hung rudder were available as options on the 33.

### Why this is difficult/useful

- Commercial-name continuity crosses a major new-hull boundary.
- Historical option facts may survive only in owner/broker descriptions hosted by the manufacturer and therefore carry lower factual confidence than builder-authored heritage text.
- Current Nauticat site makes broad claims about skeg-protected steering, but those must not be retroactively applied to every historic design without evidence.

### Likely automation

- History/generation boundary: medium-high.
- Manufacturer-hosted used-listing facts: extractable but should be lower-confidence evidence and flagged for corroboration.

---

## SEED-14 — Garcia Exploration 45

**Candidate identity:** Garcia Exploration 45 aluminium centreboarder with twin protected rudders.  
**Primary source:** Garcia Yachts manufacturer page.  
**URL:** https://www.garciayachts.com/en/sailsboats/exploration-45

### Observed facts

- Aluminium hull, centreboarder, twin rudders.
- Hull length 13.49 m; beam 4.44 m.
- Draft centreboard down 2.90 m; up 1.14 m.
- Displacement 14.61 t; ballast 4.54 t shown in comparison specification.
- Upwind sail area 91 m².
- Manufacturer states both aluminium rudders are preceded by protective skegs and have sacrificial composite zones.

### Why this is difficult/useful

- `twin rudder` is insufficient: each rudder also has a protective skeg relationship.
- Appendage relationship needs count + support/protection semantics.
- Marketing page mixes US and SI values and contains imperfect label/rendering quality.

### Likely automation

- Core numbers: high.
- Appendage relationship extraction from prose: medium-high.
- Unit/value sanity checks required because rendered imperial labels can be malformed.

---

## SEED-15 — Boréal 44.2

**Candidate identity:** Boréal 44.2, successor to the Boréal 44.  
**Primary source:** Boréal Yachts manufacturer page.  
**URL:** https://www.boreal-yachts.com/portfolio/le-boreal-44-2/?lang=en

### Observed facts

- Manufacturer explicitly says 44.2 succeeds the earlier 44.
- Full aluminium bluewater design.
- LOA 13.90 m; LWL 12.63 m; beam 4.39 m.
- Draft 1.02 / 2.48 m.
- Mainsail 45 m²; genoa 55 m².
- One steering wheel and one rudder explicitly stated.

### Why this is difficult/useful

- Model suffix `.2` represents a successor/evolution that must not be stripped during text normalization.
- Up/down draft again behaves as appendage-state data.
- Useful contrast to Garcia: similar aluminium/centreboard cruising domain but single-rudder architecture.

### Likely automation

- Structured page: high.
- Identity normalization must preserve punctuation/suffix significance.

---

## SEED-16 — Island Packet 349

**Candidate identity:** Island Packet 349 with proprietary Full Foil Keel and protected skeg-hung rudder.  
**Primary sources:** Island Packet model/specification/construction pages.  
**URLs:**
- https://ipy.com/yachts/ip-349/
- https://ipy.com/yachts/ip-349/specifications/
- https://ipy.com/customization/

### Observed facts

- LOA 38 ft 3 in; LWL 31 ft 5 in; beam 12 ft 6 in; draft 4 ft.
- Displacement 20,000 lb; ballast 7,500 lb; sail area 774 sq ft.
- Manufacturer calls keel `Full Foil Keel®` and says cruising models use protected prop/rudder architecture.
- Current manufacturer customization material explicitly lists `Skeg hung rudder`.
- Hull/keel is one-piece hand-laminated fiberglass with encapsulated lead ballast.

### Why this is difficult/useful

- Manufacturer uses a proprietary branded keel term that needs mapping without losing source wording.
- `full keel`/`long keel`/proprietary Full Foil Keel are not safe string synonyms without taxonomy rules.
- Very strong primary source for skeg-hung classification.

### Likely automation

- Numbers: high.
- Proprietary taxonomy mapping: review/rule required.

---

## SEED-17 — Corsair 880

**Candidate identity:** Corsair 880 folding trailerable trimaran, distinct from 880 Sport rig variant.  
**Primary source:** Corsair Marine manufacturer specifications.  
**URL:** https://corsairmarine.com/corsair-880/specifications/

### Observed facts

- LOA 8.8 m.
- Sailing beam 6.8 m; folded beam 2.5 m.
- Daggerboard-up draft 0.45 m; down 1.6 m.
- Unladen weight 1,660 kg.
- Standard upwind sail area 51.5 m².
- Composite rudder blade/case and daggerboard explicitly stated.
- 880 Sport uses the same main geometry/weight but a taller carbon mast and 62.9 m² upwind sail area.

### Why this is difficult/useful

- Folding-state geometry is first-class rather than mere marketing data.
- Standard vs Sport could be a NamedVariant/rig option; canonical boundary needs evidence rather than string stripping.
- `unladen weight` is a source-specific mass basis.

### Likely automation

- Table/spec extraction: high.
- Variant mapping: high with page identity retained.

---

## SEED-18 — Lagoon 42

**Candidate identity:** Lagoon 42 production catamaran.  
**Primary source:** Lagoon manufacturer page.  
**URL:** https://www.catamarans-lagoon.com/boats/lagoon-42

### Observed facts

- Hull length 12.79 m; LOA 13.22 m; beam 7.68 m.
- Draft 1.26 m; air draft 20.6 m.
- Light displacement (EEC) 12.1 t.
- Upwind sail area 94 m².
- Main-sail alternatives and optional Code 0 are separately stated.
- Manufacturer page does not directly classify keel or rudder type in the summary.

### Why this is difficult/useful

- Strong authoritative common-field source but weak appendage taxonomy exposure.
- Demonstrates that even current high-volume manufacturers may require manual/brochure enrichment for HullQ's differentiating fields.
- `Light displacement (EEC)` should retain the source basis label.

### Likely automation

- Common dimensions: high.
- Keel/rudder classification: unresolved from summary; deeper manual/drawing evidence needed.

---

## SEED-19 — Najad 34

**Candidate identity:** original Najad 34, Olle Enderlein design / early Najad lineage.  
**Primary source:** Najad official previous-model PDF.  
**URL:** https://najad.se/wp-content/uploads/2018/04/n34_productinformation-all-languages.pdf

### Observed facts

- Design settled at approximately 10.30 m length and 3.10 m beam.
- First boat delivered in 1972.
- English/Swedish text says 354 examples were built; German text in the same official PDF says 352.
- Official English brochure text describes a long keel and a separate skeg and rudder.

### Why this is difficult/useful

- **Primary-source internal conflict:** one PDF disagrees with itself across translations on number built.
- Key appendage information exists in brochure prose/image layout, not a structured spec table.
- Demonstrates why `manufacturer` must not be treated as automatic conflict-free truth.

### Likely automation

- PDF text extraction: medium-high.
- Cross-language conflict detection: required.
- Appendage taxonomy from brochure prose: medium-high; image/diagram review may add confidence.

---

## SEED-20 — J/24

**Candidate identity:** International J/24 one-design class.  
**Primary/official class sources:** International J/24 Class Association + World Sailing-approved class rules.  
**URLs:**
- https://j24class.org/about-the-j24/history/
- https://j24class.org/rules-regulations/class-rules/
- https://j24class.org/about-the-j24/915-2/

### Observed facts

- Class association reports more than 5,400 boats in 27 countries and emphasises strict one-design continuity.
- Current 2026 J/24 class rules are approved by World Sailing and linked by the class association.
- Class technical/measurement documentation is a dedicated source family rather than a normal manufacturer product page.
- Class buyer/maintenance guidance documents fixed keel attachment/keel bolts and a rudder attached via pintles, and identifies construction changes around 1980 while retaining one-design eligibility.

### Why this is difficult/useful

- Demonstrates a source hierarchy where the class association and World Sailing rule set may be more authoritative for canonical dimensional constraints than a commercial product page.
- Construction changes can occur inside one one-design class without automatically creating a new BoatDesign generation.
- Rules specify allowed/toleranced geometry, not necessarily every individual boat's as-built value.

### Likely automation

- Source discovery from class document indexes: high.
- Class-rule PDF interpretation: medium; requires distinguishing design limits from canonical nominal values.

---

# Cross-sample findings after 20 designs

## Strongly supported findings

1. **One scalar per technical concept is insufficient.** Draft, displacement, ballast, beam and sail area can depend on configuration, operating state, variant and measurement basis.
2. **Appendages must be modelled independently.** Real manufacturer evidence includes long keel + keel-hung rudder, fin/twin/lifting keel choices, single/twin rudders, skeg-hung rudders, twin rudders each preceded by a protective skeg, daggerboards and centreboards.
3. **Main manufacturer model pages are not complete source universes.** Option and appendage details often live in configurators, brochures, parts systems, manuals, news/product documents or technical articles.
4. **Generation identity can depend on prose, hull number, major new hull/deck, and retrospective naming**, not only model strings.
5. **Primary sources can conflict internally.** Najad's own multilingual N34 PDF gives two different production counts.
6. **Rudder/skeg remain much less consistently exposed than LOA/beam/draft/displacement.** They often require prose, parts catalogues, class documents or diagrams.
7. **Defunct builders require archival/association source chains** and explicit evidence-quality handling.
8. **Multihulls introduce geometry states absent from monohull-centric datasets**, including folded/sailing beam, centre-hull length and board-up/down draft.
9. **Source labels/bases must survive normalization.** Observed examples include empty standard boat, lightship, half load, unladen, dry ready-to-sail, light measurement trim, EEC light displacement and generic displacement.
10. **A source's authority is field-specific, not global.** Manufacturer, class association, official parts archive and owner-association archive can each be strongest for different facts.
11. **Proprietary vocabulary cannot be blindly normalized.** Examples include Island Packet `Full Foil Keel®` and builder-specific appendage terminology.
12. **Rules/measurement documents express constraints differently from product specs.** A rule maximum/minimum is not automatically a nominal production value.

## Interim automation vs review hypothesis

The 20-design sample supports a layered approach:

### High automation potential

- identity candidates from cleared structured datasets;
- LOA/LWL/beam/basic draft/displacement from clean manufacturer tables;
- unit conversion where source semantics are explicit;
- direct option tables where labels and values are structurally paired;
- source metadata/provenance capture.

### Medium automation + review

- generation boundaries expressed in prose;
- option discovery across multiple pages/documents;
- displacement and sail-area basis classification;
- proprietary keel/appendage terminology;
- manufacturer configurators;
- class-rule constraints vs nominal design values.

### Human-review-heavy

- rudder/skeg taxonomy when only drawings, parts or prose imply geometry;
- source-internal or cross-source conflicts;
- ambiguous historical model boundaries;
- semi-custom configuration distinctions;
- diagram/image-assisted classification.

A numeric human-review percentage is deliberately deferred until all seed records are scored consistently against the same field checklist.

# Remaining work before SLICE-0002 review

- measure broad bootstrap feasibility directly, especially Wikidata item count/field completeness;
- update central Source Register with the sources actually used here;
- turn the field matrix into an observed completeness score across the seed sample;
- explicitly score each seed record's auto-extractable vs review-required fields;
- derive/refine SLICE-0003+ boundaries from those measurements;
- investigate at least one stronger partial-skeg example and one poorly documented small-builder case if they materially change the findings.
