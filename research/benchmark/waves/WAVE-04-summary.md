# HullQ Controlled Benchmark — Research Wave 04

**Date:** 2026-08-20  
**Designs:** 8  
**Cumulative active re-research:** 33 designs  
**Scope:** older production cruisers + legacy multihulls + configuration/identity stress cases

This wave increases benchmark coverage rather than adding easy records. Independent evidence was gathered first across class/owners associations, specialist archives, technical reviews, manuals, historical listings and builder/designer material. SailboatData was consulted only afterward as a QA/reference crosscheck; its values are not HullQ evidence and are not used as fallback data.

---

## B04-001 — Sadler 34

**Independent sources**

- Yachtsnet archive: https://www.yachtsnet.co.uk/archives/sadler-34/sadler-34.htm
- Lucas Yachting Sadler specialist archive: https://www.lucasyachting.co.uk/sadler-and-starlight/sadler-34-yacht/
- Practical Boat Owner design comparison: https://www.pbo.co.uk/boats/draft-sadler-34-98740

**Observed evidence**

- Yachtsnet reports LOA 34 ft 9 in, LWL 27 ft 10 in, beam 10 ft 9 in, displacement 12,800 lb and ballast 5,000 lb.
- The design was offered with multiple keel configurations: deep fin, shallow fin and bilge/twin keel, plus a small number with centreboards fitted inside shallow fins.
- Yachtsnet also records later redesigned deep-fin keels and notes that older boats may have been retrofitted.
- Lucas Yachting describes four keel options and an explicitly **full-depth skeg-supported rudder**.
- `34SE` on later boats is described as an equipment/fitout upgrade with the same hull and rig, not automatically a distinct BoatDesign generation.

**Benchmark problem**

A single baseline `fin keel` record loses factory option space, rare centreboard configurations and later keel evolution. The `34SE` suffix also demonstrates that a commercial suffix need not imply a new hull/design generation.

**Reference crosscheck:** strong for deep-fin baseline dimensions/mass and generic skeg-supported rudder, but materially incomplete for the full keel-option space. Reference production count (260) is close to Yachtsnet's approximate 250, not a reason to overwrite either source wording.

---

## B04-002 — Albin Vega / Vega 27

**Independent sources**

- Deutsche Vega-Klassenvereinigung: https://www.albin-vega.de/die-albin-vega/
- Albin Vega document library: https://albinvega.directory/library/
- Albin Vega Russia document library, including handbook/manual/class-rule leads: https://www.albinvega.ru/library
- Owner/specialist construction description: https://albinvegaforsale.wordpress.com/hull-deck/

**Observed evidence**

- The German class association states the design was drawn by Per Brohäll in 1964, a wooden prototype preceded GRP production, and 3,450 examples had been built by the end of 1980.
- Class-association dimensions: LOA 8.25 m, LWL 7.00 m, beam 2.46 m, draft 1.17 m, displacement 2.3 t, ballast 0.9 t.
- Main sail 15.30 m² and jib 13.50 m² are explicitly component areas, not automatically the same basis as a `reported sail area` field elsewhere.
- Independent owner material describes a long/shallow fin with encapsulated ballast and the rudder strongly attached to the aft end of the keel.
- The community libraries expose original handbooks/manuals/class rules for later document-level verification.

**Benchmark problem**

Even a very common one-design-like production boat exposes chronology and definition drift: design year, prototype year and GRP production start are not the same event. Rudder attachment is also more informative than a flat `fin keel` taxonomy.

**Reference crosscheck:** strong on LOA/beam/displacement/count, but draft differs (class association 1.17 m vs reference 1.12 m) and chronology differs (class association narrative: designed 1964 and 3,450 built by end-1980; reference: first built 1965, last built 1979). These differences remain research questions rather than copied corrections.

---

## B04-003 — Hallberg-Rassy 35 Rasmus

**Independent sources**

- Hallberg-Rassy Club catalogue: https://hr-club.net/hr-catalogue/hr-35-rasmus/
- Hallberg-Rassy parts archive model recognition: https://oldshop.hallberg-rassy.com/
- De Valk historical Rasmus 35 technical listings, e.g. https://www.devalk.nl/en/yachtbrokerage/22219/HALLBERG-RASSY-35-RASMUS.html

**Observed evidence**

- HR Club identifies the model as **HR 35 Rasmus**, designed by Olle Enderlein, built 1967–1978, 760 boats.
- Catalogue values: hull length 10.50 m, LWL 8.40 m, beam 3.05 m, draft 1.30 m, displacement 5.5 t, keel weight 2.5 t.
- De Valk individual-hull records corroborate the same main dimensions and describe a long/full-bilged keel plus skeg-hung rudder.
- The Rasmus lineage spans the pre- and post-Hallberg/Rassy corporate-name transition, making source naming itself historically sensitive.

**Benchmark problem**

The post-hoc reference check exposes a major identity problem rather than a simple numeric mismatch: SailboatData contains both `RASMUS 35 (HALLBERG-RASSY)`—closely matching the independent evidence—and a separate `HALLBERG-RASSY 35` record carrying the same years/count/designer but materially different LOA/LWL, keel taxonomy and ballast type.

**Reference crosscheck:** **identity/duplicate conflict**. HullQ must not choose between those reference records by string similarity. The independently evidenced identity is HR 35 Rasmus; the competing reference record is a QA lead requiring historical explanation, not HullQ evidence.

---

## B04-004 — Vancouver 27

**Independent sources**

- Historical owner/boat lineage account: https://www.seabear.uk/about-sea-bear-the-boat/
- Boatshed historical 1979 Vancouver 27 record: https://portsmouth.boatshed.com/vancouver_27-boat-247111.html
- YBW owner/community technical discussion: https://forums.ybw.com/threads/vancouver-27-maximum-prop-diameter.83917/

**Observed evidence**

- Robert Harris designed the original Vancouver 27; North American and later British production histories are intertwined.
- The owner lineage account distinguishes the original 27 from the later Vancouver 28 created after Northshore acquired Pheon and modified/lengthened the design.
- A 1979 Boatshed record gives LOA 8.23 m, GRP construction and long-keel underwater profile.
- Owner technical discussion describes a structural skeg integrated/glassed into the hull/keel extension and explicitly recommends Northshore/owners-association knowledge for production details.

**Benchmark problem**

This is a weak-primary-source/defunct-or-changed-builder case where useful design evidence survives across owner histories, broker archives and technical community knowledge. It also has a successor/lengthened model nearby enough to create identity contamination risk.

**Reference crosscheck:** broadly compatible on 8.23 m LOA, long-keel family and Robert Harris identity. The reference supplies additional scalar dimensions, ballast and a `transom-hung rudder` label that are not admitted as HullQ evidence merely because they exist there.

---

## B04-005 — F-27 Sport Cruiser / Corsair F-27

**Independent sources**

- SAILING Magazine / Robert Perry retrospective: https://sailingmagazine.net/article-1785-f-27.html
- Practical Sailor F-27 review: https://www.practical-sailor.com/sailboat-reviews/f-27/
- Farrier-history archive: https://www.multihull.nl/multihulls/used-multihulls/F-27%20General/CorsairF27History.html
- Corsair Germany documented 1991 Atlantic-crossing boat: https://www.corsair-germany.com/abenteuer_atlantik/abenteuer_atlantik.php

**Observed evidence**

- Ian Farrier design; production began in the mid-1980s and roughly 450 examples were ultimately produced.
- Perry gives LOA 27 ft 1 in, LWL 26 ft 3 in, extended beam about 19 ft 1 in, board-up draft about 1 ft 2 in, board-down about 4 ft 11 in, displacement 2,600 lb and sail area 446 ft².
- Corsair Germany independently documents an F-27 at 8.25 m LOA, 5.5 m sailing beam, 2.5 m folded beam, roughly 0.40–1.50 m board-state draft.
- The Farrier folding system makes folded beam a first-class geometry state rather than a cosmetic transport note.
- Some later secondary datasets quote 2,800 lb rather than Perry's 2,600 lb, showing that even famous designs can carry mass drift across references.

**Benchmark problem**

HullQ needs sailing/folded geometry state, board state and historical model naming (`F-27`, `F-27 Sport Cruiser`, `Corsair F-27`) without accidentally creating duplicate identities. It also demonstrates why a single displacement figure needs source/basis/version context.

**Reference crosscheck:** very strong against Perry on LOA/LWL/sailing beam/draft/displacement/sail area and about 450 built. The reference itself notes folded-beam variation between promotional brochures, which reinforces the need to retain raw source wording rather than force one hidden scalar.

---

## B04-006 — Prout Snowgoose 37 / Snowgoose 37 Elite

**Independent sources**

- SAILING Magazine Snowgoose 37 review: https://sailingmagazine.net/article-permalink-554.html
- De Valk 1997 Prout Snowgoose 37 technical listing: https://www.devalk.nl/en/yachtbrokerage/420130/PROUT-SNOWGOOSE-37.html
- SVB Snowgoose 37 Elite owners-club metadata: https://www.svb.de/ownersclub/snowgoose-37-elite.html
- Boatshed 1996 Elite record: https://hamble.boatshed.com/prout_snowgoose_37_elite-boat-170057.html

**Observed evidence**

- Early Snowgoose 37s used molded stub keels; specialist material reports a working sail area around 570 ft² and displacement a little over 5,600 lb for the earlier form.
- The later **Elite** is a materially wider/update lineage rather than a harmless marketing suffix.
- SVB identifies Snowgoose 37 Elite production metadata around 11.30 m length and 4.95 m beam.
- A 1996 Boatshed Elite record reports 11.30 m LOA, 10.30 m LWL, 4.95 m beam, 0.85 m draft, integral low-aspect-ratio keels and skeg-hung rudders.
- A 1997 De Valk boat labelled Snowgoose 37 reports 11.28 × 4.97 × 0.85 m and 5.5 t, dimensions/mass much more consistent with the later Elite family than with the early lightweight record.

**Benchmark problem**

This case is an identity/version trap. `Snowgoose 37` records from different years can represent substantially different beam, mass and appendage forms. A late individual boat labelled simply `Snowgoose 37` cannot be safely projected onto the original design baseline without resolving whether it belongs to the Elite evolution.

**Reference crosscheck:** the reference database separates `SNOWGOOSE 37` from `SNOWGOOSE 37 ELITE`, which strongly supports treating them as distinct design/evolution records. Its earlier 37 values align with the specialist lightweight description; its Elite record (11.28 m, 4.95 m, about 5.2 t) aligns much more closely with the late-1990s individual-hull evidence. This is a useful validation of our independently discovered generation boundary, not a data source.

---

## B04-007 — Westerly Konsort

**Independent sources**

- Westerly Owners Association Wiki: https://wiki.westerly-owners.co.uk/index.php?title=Konsort
- Westerly brochure archive: https://wiki.westerly-owners.co.uk/index.php?title=Westerly_Brochures
- Yachtsnet archive: https://yachtsnet.co.uk/archives/westerly-konsort/konsort.htm
- Yachting Monthly long-term review: https://www.yachtingmonthly.com/reviews/review/westerly-konsort-review-a-re-purchase-40-years-on

**Observed evidence**

- Westerly Owners Association lists **Fin / Twin / Lifting** keel variants.
- WOA values: LOA 28 ft 10 in, LWL 25 ft 6 in, beam 10 ft 9 in; draft 5 ft 4 in fin / 3 ft 3 in twin / 3 ft 6 in–6 ft 9 in lifting.
- WOA reports displacement 8,516 lb and variant-sensitive ballast: 3,200 / 3,200 / 4,695 lb.
- WOA reports 812 built, 1979–1992; Yachtsnet says over 800.
- Yachting Monthly confirms fin, twin and lifting configurations and a transom-hung rudder.

**Benchmark problem**

The lifting-keel form changes both draft state and ballast, so it cannot be represented as just another `keel_type` label with baseline mass copied across variants. Production-count and displacement figures also differ among reputable secondary/reference sources.

**Reference crosscheck:** partial. Reference dimensions and fin/twin notes broadly align, but its main record reports 9,211 lb displacement, 704 built and only foregrounds fin/twin configuration; independent WOA evidence says 8,516 lb, 812 built and includes the lifting variant with distinct ballast. This is a high-value conflict requiring original brochures/production records before canonical resolution.

---

## B04-008 — Heavenly Twins 26 → New 27 lineage

**Independent sources**

- Heavenly Twins & Cruising Catamaran Association model history: https://htcca.co.uk/ht-26-27/
- HTCCA technical description: https://htcca.co.uk/ht-description/

**Observed evidence**

- The owners association preserves a long sequence of meaningful changes rather than one timeless model: Mk1, Mk2, Mk2A, Mk3, Mk4 and later `New 27`/HT27.
- Mk2A introduced a **new hull mould**, longer keels and a full-length central nacelle; Mk3 retained that hull but introduced a new deck mould; Mk4 changed foredeck/interior details.
- The later 27 raised the hull/deck join and changed deck moulding/headroom/access geometry.
- HTCCA gives New 27 dimensions around LOA 27 ft / 8.2 m, LWL 21 ft 6 in / 6.6 m, beam 13 ft 9 in / 4.2 m, draft 2 ft 3 in / 0.7 m and unladen weight 2,851 kg.
- Sail components are explicitly separated: main 140 ft², genoa 240 ft², staysail/storm jib 32 ft², cruising chute 550 ft².

**Benchmark problem**

This is a strong test of generation granularity: not every Mk label is necessarily a new BoatDesign, but `new hull mould`, keel geometry change and later hull/deck dimensional change are much stronger generation signals than interior-only updates. HullQ must represent that evidence without mechanically creating one design per suffix or flattening all versions into one record.

**Reference crosscheck:** unusually informative and broadly consistent; the reference itself lists Mk1/Mk2/Mk2A/Mk3/Mk4/HT27 distinctions. That agreement validates the need for generation-aware modelling but the HullQ evidence remains the independent HTCCA material.

---

# Wave 04 findings

1. **Reference-database duplicate/identity conflicts are real.** HR 35/Rasmus 35 shows two competing reference records with the same period/count/designer but materially different geometry/taxonomy.
2. **Commercial suffixes have different semantic strength.** Sadler `34SE` is fitout/equipment, while Snowgoose `Elite` reflects material hull/beam evolution.
3. **Keel option space often affects more than draft.** Westerly Konsort's lifting version carries different ballast; Sadler 34 includes rare centreboard configurations and later keel redesigns.
4. **Long-running models require generation evidence, not suffix heuristics.** Heavenly Twins has hull-mould, deck-mould, keel and accommodation changes distributed across multiple Mk labels.
5. **Legacy multihull geometry is strongly stateful.** F-27 folded/sailing beam and board-up/down draft are first-class facts.
6. **Late individual hulls can masquerade as baseline design records.** A 1997 `Snowgoose 37` listing is physically much closer to the Elite evolution than to the early Snowgoose 37 baseline.
7. **Chronology needs explicit event semantics.** Albin Vega design/prototype/GRP-production dates differ by source without necessarily being mutually exclusive.
8. **Weak-primary-source designs are still researchable.** Vancouver 27 demonstrates how owner histories, broker archives and technical forums can establish useful leads while remaining lower-confidence than original builder documentation.

## Cumulative benchmark position

After Waves 01–04, **33 designs** have been actively re-researched. The controlled sample now covers monohulls, catamarans and trimarans; fixed, twin, long, lifting, swing, centreboard and daggerboard configurations; folded/sailing geometry; keel-hung, transom-hung, skeg, partial-skeg and protective-skeg relationships; named variants; reused model names; current-vs-historical specs; source-internal conflicts; source-basis conflicts; and reference-database identity anomalies.

The benchmark remains research evidence. It does not authorize production broad ingestion, PostgreSQL persistence or autonomous web crawling.
