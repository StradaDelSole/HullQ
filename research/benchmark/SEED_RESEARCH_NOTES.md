# HullQ — Seed Research Notes

**Status:** IN PROGRESS — SLICE-0002  
**Reviewed:** 2026-08-18  
**Target:** 20–30 representative designs  
**Current checkpoint:** 8 designs researched deeply enough to expose initial source/configuration patterns.

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

### Why this is difficult/useful

- Clear generation boundary tied to hull number and year.
- Physical values differ by generation while underwater appendages remain same.
- Shallow-draft option coexists with generation.
- Multiple sail-area bases are exposed on one page.

### Likely automation

- HTML table extraction: high confidence.
- Generation boundary extraction from prose: medium confidence / review desirable.
- Rudder classification: source confirms sameness across generations but does not provide HullQ taxonomy label directly; deeper drawing/manual evidence may be needed.

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

# Cross-sample findings after 8 designs

## Already proven

1. **One scalar per technical field is insufficient.** Draft, displacement, ballast and sail area can all be configuration/basis sensitive.
2. **Main manufacturer model pages are not complete source universes.** Option details often live in brochures, inventories, news/product documents or manuals.
3. **Generation identity can depend on prose, hull number and retrospective naming**, not just model strings.
4. **Rudder and skeg are much less consistently exposed** than LOA/beam/draft/displacement and will often require deeper documentation or diagram review.
5. **Defunct builders require archival/association source chains** and explicit evidence quality/conflict handling.
6. **Multihulls add dimensions and option semantics absent from monohull-centric databases**, such as folded/sailing beam and board-up/down draft.
7. **Source labels matter.** `empty standard boat`, `lightship`, `half load`, `dry ready to sail` and generic displacement are not interchangeable.

## Current automation hypothesis — not yet final

From this first checkpoint only:

- high-confidence automated extraction should be realistic for identity + common dimensions from structured/clean manufacturer sources;
- option binding, generation boundaries and source discovery beyond the main page will need rules plus review;
- rudder/skeg and some construction classifications are likely to drive a disproportionate share of human review.

Do not convert this into a final percentage until the full 20–30 sample is complete.

# Next seed candidates

The remaining sample should deliberately add:

- a true full/long-keel design;
- explicit skeg-hung rudder;
- partial-skeg case;
- modern twin-rudder monohull;
- bilge/twin-keel generation beyond Westerly Centaur;
- aluminium centreboard/lifting-keel design (e.g. OVNI class);
- additional catamaran with fixed keels;
- trimaran from another builder;
- reused model name across unrelated generations;
- poorly documented small builder;
- strong class-association/World Sailing one-design case;
- at least one design with conflicting displacement or LOA definitions across authoritative sources.
