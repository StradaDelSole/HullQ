# SLICE-0019 consolidation 001 — exact manufacturer/yard floor count

**Purpose:** mechanically consolidate the recovered checkpoint wave, independent `needs_review` adjudications, and new geographic research batches into one strict manufacturer/yard-floor count before registry integration.

**Scope:** counting and semantic reconciliation only. No new external manufacturer research is performed by this note. `registry.json` remains untouched.

## Authoritative inputs

1. Recovered checkpoint workstreams:
   - `checkpoint/agent-01-findings.md` — North America
   - `checkpoint/agent-02-findings.md` — UK & Ireland
   - `checkpoint/agent-03-findings.md` — France / Belgium / Netherlands
   - `checkpoint/agent-04-findings.md` — Germanic / Eastern Europe
   - `checkpoint/agent-05-findings.md` — Nordics
2. Independent adjudication:
   - `review_batches/REVIEW-001...REVIEW-006`
3. Independently sourced new research:
   - `new_research_batches/RESEARCH-007-southern-europe-core.md`
   - `new_research_batches/RESEARCH-008-asia-core-yards.md`
   - `new_research_batches/RESEARCH-009-australia-new-zealand-south-africa.md`

The temporary external builder reference is **not** an evidentiary input to this count. It was used only to discover possible gaps. All 24 entities in RESEARCH-007..009 were independently researched and remain valid if the temporary directory is deleted.

## Binding counting rule

The SLICE-0019 floor is:

`>=120 verified eligible manufacturer/yard research records`

Therefore:

- a verified **brand-only** record does not count;
- a designer/marketing organization whose boats are built by a separately identified physical manufacturer does not count merely because older prose calls it a manufacturer;
- a physical production yard that builds other brands does count;
- an acquired/renamed/historical physical manufacturer can count as its own historical manufacturing identity when the relationship is explicit and it is not merely a cosmetic rename of the same counted entity;
- current operating status may be `unknown` without blocking manufacturer verification when historical repeated production is independently supported;
- one company with production facilities in multiple countries is one manufacturer identity unless evidence establishes separate independently relevant manufacturing entities.

This keeps `research_status=verified` separate from `counts_toward_manufacturer_yard_floor=true`.

## A. Recovered checkpoint records already marked verified

Checkpoint status counts before the later reviews were:

| Workstream | `verified` checkpoint records | Strict floor exclusions among those verified | Floor subtotal |
|---|---:|---|---:|
| North America | 25 | J/Boats; Freedom Yachts | 23 |
| UK & Ireland | 9 | none | 9 |
| France / Benelux | 12 | none | 12 |
| Germanic / Eastern Europe | 5 | none | 5 |
| Nordics | 12 | none | 12 |
| **Total** | **63** | **2** | **61** |

### North-America corrections

#### J/Boats — verified context, not floor

The recovered record explicitly says J/Boats is the design/brand/marketing entity and that actual manufacturing was historically contracted to Tillotson-Pearson/TPI. TPI is separately represented and counts as the physical manufacturing yard. Counting both as manufacturers would violate the slice's semantic rule.

#### Freedom Yachts — verified context, not floor

The recovered record explicitly says **all Freedom boats were manufactured by TPI throughout the company's existence**. Freedom remains a useful verified brand/production-program research record, but the evidence assigns physical manufacture to TPI. It therefore does not count toward the manufacturer/yard floor.

All other checkpoint-verified North-American records retained in the subtotal have manufacturer/yard evidence sufficient for the bounded research floor.

## B. The 43 originally `needs_review` records after REVIEW-001..006

All 43 were independently adjudicated. The strict floor result is:

### North America — 7 floor records

Count:
- Marlow-Hunter — historical production manufacturer identity; current status may remain unknown.
- Pacific Seacraft.
- Performance Cruising / Gemini historical manufacturer role.
- MacGregor Yacht Corporation.
- Morgan Yachts.
- Ericson Yachts.
- Islander Yachts.

Do not count:
- **Alerion Yachts** — verified brand/production-program context, but preserved evidence identifies Holby Marine, TPI, US Watercraft and later Eastman as the successive physical builders.
- **Columbia Yachts** — remains review-bound because the recovered record collapses the original manufacturer and later revival/lineage into one unresolved identity.

North-America reviewed subtotal: **7**.

### UK & Ireland — 6 floor records

Count:
- Marine Projects (Plymouth) Ltd / later Princess legal lineage for its historical sail-production role.
- Sadler Yachts.
- Rustler Yachts.
- Northshore Yachts.
- Discovery Yachts / Discovery Shipyard historical production lineage.
- Cornish Crabbers historical manufacturer lineage.

Verified relationship/context only, not floor:
- Moody.
- Bowman Yachts.
- Southerly.

UK & Ireland reviewed subtotal: **6**.

### France / Benelux — 9 floor records

Count:
- Fountaine Pajot.
- CNB / Construction Navale Bordeaux.
- Wauquiez.
- Gibert Marine.
- Kelt Marine.
- Kirié / Feeling historical yard role.
- Fora Marine / RM historical manufacturer lineage.
- ETAP Yachting.
- Victoire Jachtbouw / Jachtwerf Victoria historical yard lineage.

Verified relationship/context only, not floor:
- Lagoon.

France / Benelux reviewed subtotal: **9**.

### Germanic / Eastern Europe — 8 floor records

Count:
- AD Boats / Salona historical/current manufacturer role, current status uncertainty preserved.
- Delphia Yachts historical manufacturer.
- Ostróda Yacht.
- Antila Yachts.
- Northman / Maxus manufacturer role.
- Balt-Yacht.
- Schöchl Yachtbau / Sunbeam Watersports.
- AVAR-YACHT.

Reviewed subtotal: **8**.

### Nordics — 6 floor records

Count:
- Najad / Najadvarvet historical/current manufacturer-yard role.
- Siltala / Nauticat historical manufacturer role.
- Finngulf historical manufacturer role.
- Oy Fiskars Ab / Turku Boatyard.
- Bringsværd Boat Yard.
- Fjord Plast historical motorsailer/sailboat manufacturer role.

Verified relationship/context only, not floor:
- Maxi.

Nordic reviewed subtotal: **6**.

### Reviewed-needs-review arithmetic

`7 + 6 + 9 + 8 + 6 = 36`

Thus the 43-record review queue contributes **36** strict manufacturer/yard-floor records.

## C. Exact recovered floor before new geographic research

`61 checkpoint-verified floor records + 36 reviewed floor records = 97`

This replaces the earlier provisional `95–99` planning range and the temporary 99-point estimate.

The difference versus the earlier provisional estimate is specifically explained by strict removal of two additional brand/program records from the floor:

- Freedom Yachts;
- Alerion Yachts.

They remain useful verified research records; they simply do not inflate the manufacturer/yard minimum.

## D. New independently researched manufacturer/yard records

### RESEARCH-007 — Southern Europe: 8

- Cantiere del Pardo.
- Comar / Sipla manufacturer lineage.
- Solaris Yachts.
- Alpa.
- Cantiere Zuanelli.
- Italia Yachts.
- North Wind Yachts historical yard.
- Belliure.

Subtotal: **8**.

### RESEARCH-008 — Asia: 8

- Cheoy Lee Shipyards.
- Ta Yang Yacht Building / Tayana manufacturer role.
- Ta Shing Yacht Building.
- Queen Long Marine / Hylas manufacturer role.
- New Japan Yacht.
- Yamaha Motor historical production-sailboat manufacturer role.
- Fuji Yacht Builders.
- Far East Yachts / Far East Boat Ltd. historical Japanese yard.

Subtotal: **8**.

### RESEARCH-009 — Australia / New Zealand / South Africa: 8

- McConaghy Boats.
- Bashford Boats / Bashford International historical Australian yard.
- Seawind Catamarans manufacturer operation.
- Robertson & Caine.
- St Francis Marine.
- Knysna Yacht Company.
- VOYAGE Yachts.
- Cavalier Yachts historical New Zealand manufacturer.

Subtotal: **8**.

The three research batches explicitly checked the repository before research and found no matching recovered SLICE-0019 manufacturer record for their selected entities. Cross-batch production relationships such as Sydney Yachts -> AD Boats are modeled as relationships and do not create duplicate yard counts.

New-research subtotal:

`8 + 8 + 8 = 24`

## E. Exact strict manufacturer/yard floor count

`97 recovered + 24 new = 121`

# Exact result: **121 verified eligible manufacturer/yard research records**

The SLICE-0019 `>=120` manufacturer/yard breadth floor is therefore **SATISFIED**, with one-record strict headroom.

No additional manufacturer should be researched merely to increase this number. If later registry integration exposes a genuinely new duplicate/identity collapse that reduces the exact count below 120, research should resume only for the number of replacement records necessary to restore the floor.

## Other breadth floors

### Country coverage

The preserved checkpoint reported 18 countries before Southern-Europe/Asia-Pacific replacement work. RESEARCH-007..009 add independently researched manufacturer identities from new countries including Italy, Spain, Hong Kong, Taiwan, Japan, Australia, South Africa and New Zealand.

Even allowing facility/origin normalization (for example Cheoy Lee Hong Kong history versus current Zhuhai production), the `>=20 countries` floor is safely satisfied.

### Macro-regions

The recovered checkpoint already covered at least five macro-regions under the slice's working geography. Southern Europe, Asia-Pacific, Australia/New Zealand and South Africa materially strengthen rather than weaken this floor. `>=5` is satisfied.

### Historical / defunct / acquired / renamed

The preserved checkpoint already reported 55 historical/defunct/acquired/renamed records before the independent review and new batches. Removing brand-only records from the manufacturer/yard floor cannot plausibly reduce that historical manufacturer subset below the required 40, and the new batches add multiple independently verified historical yards (for example Alpa, Belliure, North Wind, Ta Yang, Fuji, Far East, Bashford and Cavalier). The `>=40` floor is therefore satisfied; an exact distribution should be emitted from the final integrated registry rather than reconstructed twice here.

### Verified official or recognized model/heritage surfaces

The preservation checkpoint reported 33 official heritage/model archives before the later independent source additions. RESEARCH-007..009 add multiple strong official heritage/model surfaces. The `>=25` floor is satisfied. The final exact archive-source count belongs in the integrated registry/report.

## What this consolidation does not prove

- It does not claim global completeness.
- It does not convert brands into yards.
- It does not resolve every uncertain founding/closure/current-status date.
- It does not authorize bulk/systematic use of source websites.
- It does not create canonical HullQ Brand/Organization/BoatModel/BoatDesign identities.
- It does not modify `registry.json`.

## Next action

Broad manufacturer-universe expansion should now stop.

The correct next bounded work is:

1. integrate the retained checkpoint + REVIEW-001..006 + RESEARCH-007..009 decisions into `registry.json` under the existing research schema;
2. assign stable `RSRCH-MFR-NNNN` research IDs;
3. schema-validate and mechanically recompute all distributions from that integrated registry;
4. perform the required 20-entity source-yield study;
5. perform the exact/unambiguous overlap check against accepted SLICE-0017/0018 state;
6. write `REPORT.md` with the measured final counts, rights/access distribution, gaps and ranked next-slice recommendation;
7. retain SLICE-0019 in `REVIEW`/`IN_PROGRESS` until independent final verification and owner acceptance.
