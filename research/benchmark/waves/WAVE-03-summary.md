# HullQ Controlled Benchmark — Research Wave 03

**Date:** 2026-08-20  
**Designs:** 8  
**Scope:** independent web research first; SailboatData only as post-hoc QA/reference comparison

This wave deliberately adds older British/Scandinavian production boats, a defunct small builder, a swing-keel/twin-rudder design, a long-lived one-design/new-build case, and a model family where apparently conflicting sail-area values are actually different measurement bases.

## Research policy applied

1. HullQ evidence is gathered independently from manufacturer/builder, class/owners archives, manuals, specialist publications, brokers and community sources.
2. Source wording, generation/variant/option/state and measurement basis are retained.
3. Missing/conflicting facts remain unresolved rather than guessed.
4. SailboatData is checked only after the independent pass.
5. SailboatData values are not copied into HullQ evidence and are never used as fallback values.
6. The reference crosscheck stores only outcomes such as match / partial / conflict / not-found.

---

## B03-001 — Hallberg-Rassy 42E

**Independent sources**

- Hallberg-Rassy Club catalogue: https://hr-club.net/hr-catalogue/hr-42-e/
- Hallberg-Rassy manufacturer URL identified by current listings: https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-42e
- Wave Train technical review: https://wavetrain.net/2012/06/11/hallberg-rassy-42-a-classic-euro-cruiser/
- De Valk historical listings for individual hull/configuration corroboration.

**Observed evidence**

- Enderlein/Rassy design, distinct from the later Frers 42F.
- Production 1980–1991; 255 boats reported by the HR catalogue.
- Hull length about 12.93 m; LWL about 10.50 m; beam about 3.78 m; standard/deep draft about 2.05 m; displacement about 11,500 kg; keel weight about 4,500 kg.
- Both ketch and sloop rigs existed.
- Deep and shoal keel configurations existed; the rig and keel axes therefore create multiple legitimate configurations rather than one scalar record.
- Secondary/individual-hull material corroborates skeg-hung rudder language.

**Benchmark problem**

A model suffix (`42E`) is identity-critical, while rig type and keel depth are orthogonal configuration axes. Individual-hull listings can also reflect refits or non-standard later equipment and must not silently redefine the design baseline.

**Reference crosscheck:** no reliable direct SailboatData record located during this pass; no reference values used.

---

## B03-002 — BENETEAU Oceanis 37

**Independent sources**

- BENETEAU heritage page: https://www.beneteau.com/oceanis-2005-2014/oceanis-37
- De Valk historical Oceanis 37 listings.
- Network Yacht Brokers / current individual-boat technical listings for keel/rudder corroboration.

**Observed evidence**

- BENETEAU gives LOA 11.48 m, beam 3.92 m, lightship displacement 6,515 kg and air draft 16.65 m.
- Designer attribution: Jean-Marie Finot / Pascal Conq; Nauta interior.
- Independent broker records repeatedly show the deep-keel form around 1.90–1.95 m draft and describe a cast-iron fin keel plus blade/spade rudder.
- Individual-boat records often quote displacement around 6,355–6,400 kg, which is not automatically the same semantic basis as BENETEAU's explicit `Lightship Displacement`.

**Benchmark problem**

The authoritative heritage page is incomplete for keel/rudder/draft details, while broker records expose those fields but may represent a specific hull. Numeric mass differences must not be treated as a simple conflict until the basis and individual-boat context are understood.

**Reference crosscheck:** partial. Ordinary dimensions align closely, but the reference record foregrounds a shallow-keel draft and places the deep-keel draft in notes; displacement is numerically closer to individual-boat listings than to the manufacturer's explicit lightship value. This is a semantic/configuration warning, not a source substitution.

---

## B03-003 — Rustler 36

**Independent sources**

- Rustler Yachts keel-design article: https://www.rustleryachts.com/keel-design-explained/
- De Valk historical Rustler 36 listing for numeric corroboration.

**Observed evidence**

- Rustler explicitly calls the 36 a traditional long-keel design with cutaway forefoot.
- Rustler explicitly says the rudder is keel-hung.
- A representative broker record reports LOA 10.78 m, beam 3.35 m, draft 1.75 m, displacement 7.5 t and ballast 3.6 t for an individual 1992 boat.

**Benchmark problem**

The primary-source appendage wording is unusually strong, but numeric production values available on the open web often come from individual hulls. Those two evidence classes should not be collapsed into one undifferentiated source-confidence score.

**Reference crosscheck:** partial/conflict. Common dimensions and mass are close, but the reference taxonomy describes a `long keel w/trans. hung rudder`, which conflicts with Rustler's explicit current description of the 36 as keel-hung. The primary builder wording wins the evidence-quality comparison; the reference mismatch is only a QA trigger.

---

## B03-004 — Seafarer 26 (McCurdy & Rhodes generation)

**Independent sources**

- Good Old Boat technical article: https://goodoldboat.com/seafarer-26/
- Good Old Boat comparison article: https://goodoldboat.com/seafarer-26-2/

**Observed evidence**

- This Seafarer 26 was built 1977–1985 and designed by McCurdy & Rhodes; an earlier, different Seafarer 26 was designed by Philip Rhodes.
- The builder is defunct.
- Fin keel; displacement 4,600 lb.
- The rudder is described specifically as hung on a **partial skeg with a bottom bearing**.
- The article reports substantial hand-laid solid laminate and an integral lead-filled keel.

**Benchmark problem**

This is the explicit partial-skeg case the benchmark needed. It also proves that manufacturer + model string is insufficient identity: `Seafarer 26` refers to more than one unrelated design generation.

**Reference crosscheck:** strong for ordinary dimensions/mass and broad `rudder on skeg` classification, but the reference taxonomy loses the more precise `partial skeg` relationship. HullQ must preserve the stronger independent wording.

---

## B03-005 — Southerly 110

**Independent sources**

- Southerly 110 owner's manual mirror: https://manualzz.com/doc/28420109/southerly-110-yacht-owners-manual
- De Valk historical Southerly 110 listings, including detailed swing-keel construction descriptions.

**Observed evidence**

- Rob Humphreys design; Northshore builder context.
- Representative records give LOA about 10.82 m, LWL 9.22 m, beam 3.57 m, maximum draft about 2.18 m and minimum draft about 0.71–0.72 m.
- The owner's manual explicitly states that Southerlys are fitted with **twin rudders as standard** and documents the rudder tubes/bearings.
- Broker technical material describes the hydraulic swing keel and fixed grounding plate; another record explicitly notes a substantial centerline skeg protecting propeller and rudders when dried out.
- Published displacement/ballast numbers vary materially between individual records and reference material, requiring basis/hull-specific review rather than forced resolution.

**Benchmark problem**

A single `Swing Keel` hull label is incomplete: swing keel state, fixed grounding plate/ballast, twin rudder count and protective-skeg relationship are separate facts. Individual hulls also expose mass differences that may reflect configuration, equipment or reporting basis.

**Reference crosscheck:** good for basic geometry and swing-keel draft range, but incomplete for the twin-rudder/protective-skeg relationship and not sufficient to resolve mass discrepancies.

---

## B03-006 — Contessa 32

**Independent sources**

- Jeremy Rogers current/new-build specification: https://www.jeremyrogers.co.uk/contessa32-specification/
- Jeremy Rogers new-build context: https://www.jeremyrogers.co.uk/contessa-32-new-build/
- Contessa 32 Class Association: https://www.co32.org/racing/class-rules

**Observed evidence**

- The Contessa 32 remains a live/new-build design lineage using the same hull/deck mould concept.
- Jeremy Rogers' 2023 new-build specification gives 4,468 lb / 2,026 kg encapsulated lead ballast and total displacement 9,300 lb / 4,218.48 kg.
- The rudder has two bronze bearings and a stainless lower attachment plate at the base of the skeg.
- Class rules remain a separate authoritative source family for controlled racing dimensions/constraints and must not automatically be treated as nominal production values.

**Benchmark problem**

A long-lived design can have current new-build construction/weight specifications that differ from historical database figures without implying either source is simply wrong. HullQ needs edition/time applicability on design-level evidence.

**Reference crosscheck:** partial. Historic reference figures are about 9,500 lb displacement and 4,500 lb ballast, close but not identical to the 2023 builder specification. Treat as era/specification applicability, not an arithmetic conflict.

---

## B03-007 — AMEL Super Maramu 2000

**Independent sources**

- AMEL official history: https://amel.fr/en/the-amel-story/
- Super Maramu 2000 owner's-manual archive/index: https://www.nikimat.com/
- Owner's manual mirror/index: https://www.manualslib.com/products/Amel-Super-Maramu-2000-8825620.html

**Observed evidence**

- AMEL's current official history places the Super Maramu 2000 at 16 m and production from **1998 to 2006**.
- AMEL explicitly distinguishes it from the preceding Super Maramu, produced 1988–1998.
- Owner-manual material exists and is a stronger route for systems/technical facts than generic secondary summaries.
- Independent secondary technical datasets commonly describe the design as a ketch with about 16,000 kg displacement, ~4.60 m beam, ~2.03–2.07 m draft and a skeg-supported rudder, but those numeric/appendage details require document-level corroboration before canonical acceptance.

**Benchmark problem**

The exact generation boundary is important: `Super Maramu` and `Super Maramu 2000` are related but distinct production identities. Even a widely used reference database disagrees with the builder's official chronology by roughly one year at each end.

**Reference crosscheck:** chronology conflict. SailboatData reports 1999–2005 for the 2000 model while AMEL's official history says 1998–2006. HullQ should retain the official chronology and use the mismatch to trigger deeper hull-number/year research, not average the dates.

---

## B03-008 — Moody 33 Mk I / Mk II

**Independent sources**

- Moody Owners archive Mk I: https://www.moodyowners.org/Moody_Archives/17_boat.htm
- Moody Owners archive Mk II: https://www.moodyowners.org/Moody_Archives/18_boat.htm
- Moody Owners technical discussion: https://www.moodyowners.info/threads/moody-33-mk1-vs-mk2.22269/

**Observed evidence**

- Mk I: introduced September 1973, ceased September 1978, 242 boats reported.
- Mk II: introduced September 1978, ceased June 1981, 121 boats reported.
- Both are Angus Primrose designs with broadly the same principal dimensions; the Mk II primarily changed accommodation/cockpit details.
- Owners-archive figures give LOA 10.06 m, LWL about 8.69 m, beam about 3.51 m, fin-keel draft 1.35 m and displacement around 4.77 t.
- The Mk II archive lists main 205 sq ft, working jib 176 sq ft and No.1 genoa 375 sq ft.
- A detailed owners discussion explains an apparent Mk I/Mk II sail-area discrepancy: one source page used a rating-style main + foretriangle measure (~452 sq ft) while another used the actual large genoa + main (~580 sq ft). The rigs were not necessarily physically different.

**Benchmark problem**

This is a particularly strong sail-area-basis case: two numbers that look like generation changes can actually be two definitions of sail area. HullQ must preserve the raw basis before interpreting a numeric difference as a variant or design change.

**Reference crosscheck:** partial. The Mk II reference record aligns closely on dimensions/mass and publishes 580 sq ft reported sail area; this agrees with the owners' explanation that the larger value is an actual-sail basis rather than proof of a different rig.

---

# Wave 03 findings

1. **Partial skeg must remain distinct from generic skeg support.** Seafarer 26 proves the distinction is available in credible prose even when flat databases lose it.
2. **Era applicability matters at design level.** Contessa 32 historical values and current 2023 new-build values are both plausible for the same long-lived design lineage.
3. **Rig/keel axes can be orthogonal.** HR 42E has ketch/sloop plus deep/shoal configurations.
4. **Swing-keel is not a complete appendage model.** Southerly 110 combines swing keel, grounding plate/fixed ballast, twin rudders and a protective skeg relationship.
5. **Builder chronology can outperform reference chronology.** AMEL's own history disagrees with the reference database for Super Maramu 2000 production years.
6. **Sail-area conflicts may be definition conflicts.** Moody 33 shows that foretriangle/rating-style area and actual large-genoa area can make the same rig appear different by more than 100 sq ft.
7. **Reference taxonomies can be less precise than independent evidence.** Rustler 36 and Seafarer 26 both expose this in rudder/skeg classification.
8. **Individual-boat listings are useful but scope-limited.** They are valuable for discovering options and physical details, but must remain hull-specific unless corroborated as design-level facts.

## Cumulative benchmark position

After Waves 01–03, **25 designs** have been actively re-researched. The sample now repeatedly exercises identity generations, option/state scope, measurement-basis preservation, source-internal conflicts, cross-source conflicts, multihull geometry, partial/full skeg distinctions, twin rudders, long-keel/keel-hung rudders, current-vs-historical design evidence and weak/defunct-builder source chains.

The benchmark remains research evidence, not production canonical data, and does not authorize broad ingestion or PostgreSQL persistence by itself.
