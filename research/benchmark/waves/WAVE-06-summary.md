# HullQ Controlled Benchmark — Research Wave 06

**Date:** 2026-08-20  
**Designs:** 9  
**Cumulative active re-research:** 50 designs  
**Scope:** 50-design minimum gate; generation boundaries, rule-vs-nominal semantics, special keels, multihull board state and displacement-basis/configuration stress

Wave 06 reaches the minimum benchmark corpus size without adding easy filler. Each case was independently researched first using owner/class associations, manufacturer/builder manuals/specifications, design archives, specialist publications and community technical archives. SailboatData was consulted only afterward as a QA/reference comparison; its field values are not HullQ evidence and are never used as fallback data.

---

## B06-001 — C&C 35 Mk I / Mk II

**Independent sources**

- Great Lakes / C&C design archive, Mk II: https://www.ghcarchives.com/the-yachts/c-and-c-35-mk-ii
- Canadian Boating Mk I / Mk II review: https://canadianboating.ca/boat-reviews/cac-35-mks-i-and-ii-sail-boat-review/
- SAILING Magazine C&C 35 review: https://sailingmagazine.net/article-permalink-531.html

**Observed evidence**

- The original design began as the Redwing 35 and became the C&C 35 after the corporate transition.
- A redesigned model appeared in 1973 and was later designated C&C 35-2 / Mk II.
- The Great Lakes archive identifies the Mk II as C&C design drawing 73-3 and reports 351 C&C 35s across the first two versions.
- The Mk II gained nearly a foot of apparent length through the raised sheer, replaced the Mk I scimitar rudder with a conventional partially balanced spade, reshaped the afterbody, added more than 50 ft² sail area and about 620 lb ballast, and changed deck/cabin/cockpit geometry.
- Independent specialist material likewise treats the 1973 change as a substantial redesign, not merely a trim/equipment package.

**Benchmark problem**

Here a `Mk II` label carries genuine hull/appendage/weight/sail-plan consequences. This is the counterexample to Catalina 36 and HR 312, where Mk changes retain much more of the technical baseline. HullQ cannot infer generation weight from suffix syntax alone.

**Reference crosscheck:** strong structural agreement: the reference independently separates C&C 35-1/Redwing 35 and C&C 35-2 and describes the same redesign. Reference-only scalar values remain comparison data, not HullQ evidence.

---

## B06-002 — Hallberg-Rassy 312 Mk I / Mk II

**Independent sources**

- Hallberg-Rassy Club Mk I catalogue: https://hr-club.net/hr-catalogue/hr-312-mk-i/
- Boat24 historical HR 312 Mk II article: https://www.boat24.com/at/blog/hallberg-rassy-312/
- De Valk Hallberg-Rassy 312 model archive: https://www.devalk.nl/en/model/hallberg-rassy/312.html

**Observed evidence**

- Production 1979–1993, total 690; De Valk reports 485 Mk I boats and Mk II from 1986.
- Core dimensions remain 9.42 m LOA, 7.70 m LWL, 3.08 m beam and 1.62 m draft across the Mk change in the independent records.
- Boat24 explicitly says **hull and rig are the same** for Mk I and Mk II.
- Mk II changed portlight placement/size, raised and shifted the superstructure/cockpit, improved headroom, galley and interior layout, and standardized the quarter berth.
- The HR Club Mk I page shows another suspicious unit-rendering issue in mass fields (`4900 t`, `2200 t` style presentation), reinforcing the earlier HR 352 parser finding.

**Benchmark problem**

This is another strong anti-over-splitting case. A genuine Mk designation and meaningful deck/interior change do not necessarily imply a new underwater design or new derived-metric baseline. It also suggests malformed mass-unit rendering is a repeatable source-family parsing problem rather than a one-off typo.

**Reference crosscheck:** very strong. The reference says Mk II introduced in 1986 with the **same hull and sail plan**, and its baseline dimensions/count align closely. That agreement is QA only.

---

## B06-003 — ETAP 32s standard keel / tandem-keel option

**Independent sources**

- ETAP 32s owner's manual mirror: https://manualzz.com/doc/59388526/etap-32s-owner-s-manual
- Cruising World Boat of the Year review: https://www.cruisingworld.com/sailboats/etap-32s-0/
- De Valk tandem-keel individual-hull record: https://www.devalk.nl/en/yachtbrokerage/805483/ETAP-32S.html
- Zeilersforum ETAP 32s tandem-keel owner discussion: https://zeilersforum.nl/index.php/forum-125/90-ervaringen-eigenschappen-specificaties/570460-etap-32s-tandemkiel

**Observed evidence**

- The owner's manual exposes two keel-dependent configurations: maximum draft 1.80 m standard versus 1.30 m shallow keel; net displacement 3,700 kg versus 3,890 kg; fully loaded displacement 5,200 kg versus 5,390 kg; keel weight 1,100 kg versus 1,290 kg.
- Cruising World identifies the shallow option specifically as the innovative **tandem keel**, two fore/aft foils joined at the bottom, and gives the tandem-keel draft as 1.30 m.
- A De Valk tandem-keel hull independently reports 9.84 m length, 8.38 m LWL, 3.42 m beam, 1.30 m draft, 3.89 t displacement and 1.29 t cast-iron ballast.
- ETAP's double-hull/foam construction and unsinkability concept are construction semantics separate from keel taxonomy.

**Benchmark problem**

The keel option changes **draft, displacement and ballast together**. A flat baseline plus alternate draft is therefore wrong. The same official manual also distinguishes net versus fully-loaded displacement, giving HullQ both configuration and mass-basis dimensions on one design.

**Reference crosscheck:** partial/strong for the tandem-keel option: the reference notes 1.30 m tandem-keel draft. Independent evidence is richer because it preserves both standard and tandem configurations and their different mass/ballast values.

---

## B06-004 — Pearson 35

**Independent sources**

- Pearson 35 owner/design archive: https://pearson35.com/design-manuals/

**Observed evidence**

- The owner archive explicitly warns: its measurements pertain specifically to a **1979 model and may not represent all model years**.
- For that documented state it gives centerboard-up draft 3 ft 9 in and board-down draft 7 ft 6 in.
- It records Pearson-published lightship displacement 13,000 lb and separately constructs a 15,000 lb loaded figure by adding about 2,000 lb payload.
- Ballast is documented as 5,400 lb lead encapsulated in fiberglass.
- Published sail area is 550 ft² while a calculation from the documented rig yields 548.5 ft², illustrating published-versus-calculated area semantics.

**Benchmark problem**

The source itself provides an **applicability warning by model year**, plus centerboard state and multiple displacement concepts. Evidence needs a temporal/applicability scope even when the commercial BoatDesign identity remains stable.

**Reference crosscheck:** strong on baseline 13,000 lb displacement, 5,400 lb ballast, 3.75/7.50 ft centerboard draft pair and approximate sail area. The reference's whole-run 1968–1982 record must not erase the independent source's explicit 1979 applicability warning.

---

## B06-005 — Ericson 35 Mk I / 35-2 / 35-3

**Independent sources**

- Practical Sailor Ericson 35 historical review: https://www.practical-sailor.com/sailboat-reviews/ericson-35/
- EricsonYachts owner/technical archive discussion: https://ericsonyachts.org/ie/threads/e35-vs-e35-mkii-vs-e35mkiii-help.7909/
- EricsonYachts model discussion: https://ericsonyachts.org/ie/threads/ericson-35s-whats-the-difference.10305/

**Observed evidence**

- Practical Sailor describes the early 35 as an older CCA-style long-keel/attached-rudder boat, the 1969 35-2 as a new Bruce King racer/cruiser with fin keel and semi-balanced spade rudder, and the later 35-3 as a larger, more modern replacement.
- Experienced Ericson owners independently describe the 1960s, 1970s and 1980s 35-footers as successive all-new/redesigned boats.
- One experienced contributor explicitly warns there is **no direct technical lineage from 35-II to 35-III beyond occupying the same market slot**; another describes the III as a whole new redesign.
- The community also documents factory shoal/short-rig options inside later generations, demonstrating that generation and configuration remain separate axes.

**Benchmark problem**

The same builder repeatedly reused `35` with Mk/conventional suffixes for technically different hulls. This is a strong under-splitting risk, but community disagreement about whether II→III is `evolution` versus `entirely new` also demonstrates why HullQ should record evidence for lineage relation rather than infer a categorical relationship from naming alone.

**Reference crosscheck:** strong structural confirmation. The reference has separate 35-1, 35-2 and 35-3 records and explicitly states 35-3 is a different design from 35-2. Reference-specific numeric records remain QA only.

---

## B06-006 — Bristol 35.5 / Bristol 35.5C

**Independent sources**

- Practical Sailor Bristol 35.5C review: https://www.practical-sailor.com/sailboat-reviews/bristol-35-5c/
- Current/historical individual-hull corroboration, e.g. boats.com Bristol 35.5C listings

**Observed evidence**

- Practical Sailor identifies the 35.5C as Ted Hood's centerboard cruiser and says the centerboard version debuted in 1977.
- The `C` identifies the centerboard configuration in common usage; it does not by itself prove a wholly unrelated hull design.
- The centerboard is mechanically controlled by a coachroof winch and enclosed cable system.
- Independent listings identify both Bristol 35.5 and 35.5C usage and attribute the design to Ted Hood.
- Available secondary/reference material also reports a fixed-keel form and centerboard draft pair, confirming configuration choice inside the broader model family.

**Benchmark problem**

A suffix can be a **configuration marker** rather than a new generation. Canonical identity must preserve `35.5C` as a meaningful commercial/configuration designation without automatically creating a technically unrelated BoatDesign.

**Reference crosscheck:** compatible. The reference explicitly notes a keel/centerboard version sometimes called Bristol 35.5C and supplies board-up/down details. Those values are not used to fill HullQ evidence; they only confirm that the suffix maps to configuration rather than arbitrary naming.

---

## B06-007 — Gemini 105Mc

**Independent sources**

- Performance Cruising Gemini 105Mc owner's manual mirror: https://manualzz.com/doc/23718176/gemini-105mc-catamaran-owner-s-manual
- Independent manual mirror: https://doczz.net/doc/285736/gemini-105mc-owners-manual

**Observed evidence**

- The manufacturer's manual states there is **one centerboard in each hull**.
- The boards are pivoting/kick-up designs; fully down they extend about 4 ft below the keel.
- The manual explicitly recommends operating states in which both boards, only the leeward board, or no boards are deployed depending on point of sail/offshore conditions.
- It states Gemini's rudders are spade rudders and describes the twin-rudder bearing/stock system.
- The source therefore describes a multihull whose appendage configuration is not just `twin centerboards`: the effective board state can be 0/1/2 deployed while the physical installed count remains two.

**Benchmark problem**

Installed appendage count and **operating-state count** are different concepts. The later resolved-configuration layer must distinguish `two boards installed` from `one board deployed` rather than mutating the underlying design taxonomy.

**Reference crosscheck:** strong on broad geometry and twin-centerboard identity: reference LOA about 10.21 m, LWL 9.68 m, beam 4.27 m and draft 0.46–1.68 m. The independent manual provides much richer appendage-state semantics and remains HullQ evidence.

---

## B06-008 — J/105: builder nominal specification versus class rules

**Independent sources**

- J/Boats technical specifications: https://jboats.com/j105-tech-specs
- J/105 Class Association rule index/current 2026 rules: https://j105.org/rules/

**Observed evidence**

- J/Boats publishes nominal technical values: LOA 10.51 m, LWL 8.99 m, beam 3.35 m, standard draft 1.98 m, standard ballast 1,542 kg, displacement 3,515 kg and 100% sail area 53.60 m².
- The class association maintains current 2026 Class Rules plus official keel and rudder offsets.
- The class rules exist to preserve one-design equality and require competing boats to comply with both J/Boats standard specifications and the class rules.
- Rule documents therefore encode **limits, permitted variation, measurement procedures and compliance geometry**, not automatically the nominal production value of every field.

**Benchmark problem**

A rule maximum/minimum/tolerance or official offset must not be ingested as a nominal BoatDesign scalar merely because it is highly authoritative. HullQ needs evidence semantics for `nominal`, `constraint`, `tolerance`, `measurement procedure` and possibly `as-measured` values.

**Reference crosscheck:** ordinary reference dimensions align closely with J/Boats. The important benchmark finding is semantic rather than numeric: class-rule authority does not make every rule number a nominal design specification.

---

## B06-009 — Bavaria 38 (2002/2003 manual) and neighboring 38 identities

**Independent sources**

- Bavaria Yachtbau 38 owner's manual mirror: https://www.emanualonline.com/marines/boats/bavaria/38/bavaria-38-2002-2003-owners-manual-emo-488088
- Bavaria manual archive index: https://www.boatfreemanuals.com/yachts/bavaria/

**Observed evidence**

- The actual Bavaria 38 owner's manual gives LOA 12.33 m, hull length 11.91 m, LWL 10.25 m and beam 3.87 m.
- It provides two keel configurations: normal keel draft about 1.70 m versus lead keel about 2.00 m.
- **Empty yacht including safety equipment:** 7,000 kg.
- **Fully equipped ready-for-sailing with crew:** 8,533 kg normal keel versus 8,303 kg lead keel.
- Ballast is configuration-specific: 2,050 kg normal keel versus 1,820 kg lead keel.
- The same builder/market period contains distinct `Bavaria 38`, `Bavaria Ocean 38`, later `Bavaria 38 Cruiser`, and `Bavaria Match 38` identities; string-normalizing all to `Bavaria 38` would be destructive.

**Benchmark problem**

This is a compact demonstration of why persistence must attach mass to **both measurement basis and configuration**. The heavier ballast option is not the deeper lead keel; the fully-equipped mass also changes by keel option. At identity level, `Ocean`, `Cruiser` and `Match` are not decorative aliases.

**Reference crosscheck:** the matching J&J-era reference record is labelled `Bavaria Cruiser 38` and closely matches the manual's 1.70 m draft, ~7,000 kg empty displacement and ~2,050 kg ballast, but the manual contains richer basis/configuration semantics. Separate reference records also exist for Bavaria Ocean 38, later 38 Cruiser and Match 38, supporting the need for identity disambiguation rather than name flattening.

---

# Wave 06 findings

1. **Mk syntax has no universal identity meaning.** C&C 35 Mk II is a material redesign; HR 312 Mk II retains hull and rig.
2. **Configuration can change several physical fields simultaneously.** ETAP 32s and Bavaria 38 change draft, ballast and displacement together by keel option.
3. **Evidence needs applicability scope.** Pearson 35's own archive explicitly warns that its measurements are for a 1979 model and may not cover all production years.
4. **Lineage relation itself can be uncertain evidence.** Ericson owners agree on separate technical designs but differ in how directly II→III should be described as evolutionary lineage.
5. **Commercial suffixes can encode configuration.** Bristol `35.5C` is a centerboard designation, not automatically a separate unrelated hull.
6. **Installed appendage count differs from deployed-state count.** Gemini 105Mc has two centerboards installed but valid sailing states with zero, one or two boards deployed.
7. **Highly authoritative rules do not equal nominal specs.** J/105 class-rule limits/offsets/measurement procedures must remain semantically distinct from J/Boats nominal design values.
8. **Measurement basis and configuration are orthogonal.** Bavaria's empty/full-sailing mass and normal/lead-keel options form a 2-D semantic problem, not one `displacement` scalar.
9. **Family/marketing names must be identity-safe.** Bavaria `Ocean`, `Cruiser`, `Match` and plain 38 records demonstrate destructive alias risk.

## 50-design gate reached

After Waves 01–06, **50 deliberately difficult designs** have been actively re-researched. The minimum corpus size in SLICE-0011 is therefore reached.

The next action is **not** to start broad ingestion. The next action is to measure this 50-design corpus: source coverage, unresolved/conflict frequency, generation/variant ambiguity, measurement-basis ambiguity, appendage/configuration ambiguity, likely human-review reasons and the persistence/import requirements repeatedly demanded by real evidence.

SLICE-0011 remains `IN_PROGRESS` until that benchmark analysis is recorded and the next bounded persistence/import implementation slice can be specified from evidence rather than assumption.
