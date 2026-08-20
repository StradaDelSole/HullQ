# HullQ Controlled Benchmark — Research Wave 06

**Date:** 2026-08-20  
**Designs:** 9  
**Cumulative active re-research:** 50 designs  
**Scope:** 50-design minimum gate; generation boundaries, rule-vs-nominal semantics, special keels, multihull board state and displacement-basis/configuration stress

Wave 06 reaches the minimum benchmark corpus size without adding easy filler. Each case was independently researched first using owner/class associations, manufacturer/builder manuals/specifications, design archives, specialist publications and community technical archives. SailboatData was consulted only afterward as QA/reference comparison. **No SailboatData field value is retained below; reference notes store outcome/structure only.**

---

## B06-001 — C&C 35 Mk I / Mk II

**Independent sources**
- Great Lakes / C&C design archive: https://www.ghcarchives.com/the-yachts/c-and-c-35-mk-ii
- Canadian Boating review: https://canadianboating.ca/boat-reviews/cac-35-mks-i-and-ii-sail-boat-review/
- SAILING Magazine: https://sailingmagazine.net/article-permalink-531.html

**Observed evidence**
- Original design lineage traces through Redwing 35 / C&C 35.
- A substantial 1973 Mk II redesign changed sheer/afterbody, rudder form, ballast/sail-plan and deck/cockpit geometry.
- Great Lakes archive ties Mk II to a specific C&C design drawing and production history.

**Benchmark problem:** here `Mk II` carries real hull/appendage/weight/sail-plan consequences, unlike Catalina 36 or HR 312. Suffix syntax cannot determine generation semantics by itself.

**Reference crosscheck:** strong structural agreement on the split/redesign. No reference scalar values retained.

---

## B06-002 — Hallberg-Rassy 312 Mk I / Mk II

**Independent sources**
- HR Club Mk I: https://hr-club.net/hr-catalogue/hr-312-mk-i/
- Boat24 historical article: https://www.boat24.com/at/blog/hallberg-rassy-312/
- De Valk archive: https://www.devalk.nl/en/model/hallberg-rassy/312.html

**Observed evidence**
- Production history identifies Mk II from the mid-1980s while preserving the same core hull/rig geometry.
- Boat24 explicitly states hull and rig are the same; Mk II changes focus on superstructure/cockpit/interior/headroom.
- HR Club again shows suspicious malformed mass-unit rendering, reinforcing a source-family parsing problem.

**Benchmark problem:** genuine Mk designation without a new underwater design; authoritative source family can also repeat systematic presentation defects.

**Reference crosscheck:** strong same-hull/sail-plan agreement. No reference values retained.

---

## B06-003 — ETAP 32s standard keel / tandem-keel option

**Independent sources**
- Owner's manual: https://manualzz.com/doc/59388526/etap-32s-owner-s-manual
- Cruising World: https://www.cruisingworld.com/sailboats/etap-32s-0/
- De Valk tandem-keel hull: https://www.devalk.nl/en/yachtbrokerage/805483/ETAP-32S.html
- Zeilersforum owner discussion: https://zeilersforum.nl/index.php/forum-125/90-ervaringen-eigenschappen-specificaties/570460-etap-32s-tandemkiel

**Observed evidence**
- Official manual exposes standard and shallow/tandem configurations with different draft, net displacement, fully-loaded displacement and keel weight.
- Cruising World identifies the shallow option as a tandem keel with fore/aft foils joined at the bottom.
- Individual-hull evidence corroborates the tandem form.

**Benchmark problem:** one keel option changes **draft, displacement and ballast together**, while the same manual also distinguishes net versus fully-loaded mass basis.

**Reference crosscheck:** partial/strong option recognition but less semantic depth than the independent evidence. No reference values retained.

---

## B06-004 — Pearson 35

**Independent source**
- Pearson 35 owner/design archive: https://pearson35.com/design-manuals/

**Observed evidence**
- Archive explicitly warns that its measurements apply specifically to a documented model year and may not represent the full production run.
- It preserves centerboard up/down draft state.
- It distinguishes Pearson-published lightship displacement from a separately constructed loaded figure.
- Published sail area and a rig-derived calculation are separate claim types.

**Benchmark problem:** evidence applicability by model year plus board state and multiple mass/calculation semantics inside one commercial design identity.

**Reference crosscheck:** strong baseline compatibility but broader whole-run scope. No reference values retained.

---

## B06-005 — Ericson 35 Mk I / 35-2 / 35-3

**Independent sources**
- Practical Sailor: https://www.practical-sailor.com/sailboat-reviews/ericson-35/
- EricsonYachts discussion: https://ericsonyachts.org/ie/threads/e35-vs-e35-mkii-vs-e35mkiii-help.7909/
- Additional owner discussion: https://ericsonyachts.org/ie/threads/ericson-35s-whats-the-difference.10305/

**Observed evidence**
- Practical Sailor distinguishes an early CCA-style long-keel/attached-rudder boat, a later Bruce King fin/spade design and another larger replacement generation.
- Experienced owners independently describe successive redesigns but differ in how directly II→III should be described as evolutionary lineage.
- Factory shoal/short-rig options also exist inside later generations.

**Benchmark problem:** same builder/model number reused across technically distinct designs; even the lineage relation between generations can itself remain uncertain evidence.

**Reference crosscheck:** strong structural confirmation of separate identities. No reference values retained.

---

## B06-006 — Bristol 35.5 / Bristol 35.5C

**Independent sources**
- Practical Sailor: https://www.practical-sailor.com/sailboat-reviews/bristol-35-5c/
- Historical individual-hull corroboration.

**Observed evidence**
- Ted Hood centerboard cruiser; `C` is used for the centerboard configuration rather than proving a wholly unrelated hull.
- Centerboard control/mechanics are documented independently.

**Benchmark problem:** a suffix can encode **configuration** rather than generation.

**Reference crosscheck:** compatible configuration interpretation. No reference board values retained.

---

## B06-007 — Gemini 105Mc

**Independent sources**
- Manufacturer owner's manual mirror: https://manualzz.com/doc/23718176/gemini-105mc-catamaran-owner-s-manual
- Independent manual mirror: https://doczz.net/doc/285736/gemini-105mc-owners-manual

**Observed evidence**
- Manual states one centerboard is installed in each hull.
- Boards are pivoting/kick-up designs and legitimate sailing procedures include both boards, leeward-only board or no boards deployed depending on conditions.
- Manual describes twin spade rudders.

**Benchmark problem:** **installed appendage count and deployed-state count are different concepts**. Effective operating state must not mutate the underlying design taxonomy.

**Reference crosscheck:** strong broad-identity/geometry compatibility. No reference dimensions retained.

---

## B06-008 — J/105: builder nominal specification versus class rules

**Independent sources**
- J/Boats tech specs: https://jboats.com/j105-tech-specs
- J/105 Class Association current rules: https://j105.org/rules/

**Observed evidence**
- J/Boats publishes nominal design geometry/mass/sail information.
- Class association maintains current class rules plus official keel/rudder offsets.
- Rules encode compliance limits, permitted variation, geometry and measurement procedure rather than automatically nominal production values.

**Benchmark problem:** highly authoritative `class_rule_constraint` is not the same claim type as a nominal builder specification.

**Reference crosscheck:** ordinary-field agreement; benchmark issue is semantic, not numeric. No reference values retained.

---

## B06-009 — Bavaria 38 and neighboring 38 identities

**Independent sources**
- Bavaria 38 owner's manual mirror: https://www.emanualonline.com/marines/boats/bavaria/38/bavaria-38-2002-2003-owners-manual-emo-488088
- Bavaria manual archive: https://www.boatfreemanuals.com/yachts/bavaria/

**Observed evidence**
- Owner's manual exposes normal-keel versus lead-keel configurations with different draft, ballast and ready-for-sailing mass.
- It also distinguishes empty-yacht mass from fully-equipped/crew mass.
- Neighboring commercial identities include plain Bavaria 38, Ocean 38, later 38 Cruiser and Match 38; flattening them into one alias would be destructive.

**Benchmark problem:** measurement basis × keel configuration is a two-dimensional physical-data problem, while neighboring model names create identity risk.

**Reference crosscheck:** matching reference identity is structurally compatible with one configuration, while separate neighboring reference records reinforce the need for identity disambiguation. No reference field values retained.

---

# Wave 06 findings

1. Mk syntax has no universal identity meaning.
2. Configuration can change several physical fields simultaneously.
3. Evidence needs explicit applicability scope.
4. Lineage relation itself can remain uncertain evidence.
5. Commercial suffixes can encode configuration.
6. Installed appendage count differs from deployed operating state.
7. Class-rule constraints are not nominal specifications.
8. Measurement basis and configuration are orthogonal.
9. Family/marketing names must be identity-safe.

## 50-design gate reached

After Waves 01–06, **50 deliberately difficult designs** had been actively re-researched. Corpus expansion pauses by default. The next step is benchmark measurement and a bounded evidence/applicability + research-bundle contract before persistence, not broad ingestion.
