# SLICE-0019 new research batch 007 — Southern Europe core yards

**Scope:** bounded independent research of 8 manufacturer/yard candidates selected from the Southern-Europe coverage gap. Candidate selection may have been informed by the temporary external gap detector, but every decision in this file is based only on independent sources listed below. This file remains valid if `research/manufacturers/temporary_external_reference/` is later deleted.

**Method:** before external research, the HullQ repository was searched for the candidate names to avoid duplicating already-recovered SLICE-0019 records. No matching existing manufacturer research record was found for these eight candidates. Research then focused on manufacturer/yard identity, repeated/series sailboat production, production era, current/historical status, and brand-vs-yard relationships. No `registry.json` or canonical entity is modified by this note.

## 1. Cantiere del Pardo / Grand Soleil

**Decision:** `VERIFIED` — active Italian manufacturer/yard; counts toward the manufacturer/yard floor.

- Official Cantiere del Pardo material states the yard was established in **1973** and has launched **more than 5,000 boats**.
- The first Grand Soleil, the **GS 34**, was produced in the founding year; the company's sustainability/history material states that the GS 34 was built in **290 specimens**.
- Official heritage material documents a continuing multi-model Grand Soleil sailing-yacht range across subsequent decades.
- `Grand Soleil` should be modeled as the sailing-yacht brand/product lineage associated with the physical/legal yard, not silently treated as a separate yard.
- The yard also produces motor-yacht brands today; that does not weaken the clearly documented sailing-yacht manufacturer role.

Primary sources:
- https://cantieredelpardo.com/company/our-values/
- https://cantieredelpardo.com/it/the-yard/our-heritage/
- https://cantieredelpardo.com/app/uploads/2023/09/CantiereDelPardo_Sostenibilita%CC%8021-22_ENG.pdf

Recommended modeling:
- entity: `Cantiere del Pardo` — manufacturer/yard, Italy, active;
- production-era start: 1973 exact;
- relationship: Grand Soleil = sailing brand/product lineage of the yard;
- cumulative production figure remains company-reported rather than independently audited.

## 2. Comar Yachts / Sipla / Comet

**Decision:** `VERIFIED` — active Italian manufacturer/yard lineage; counts toward the manufacturer/yard floor.

- Comar's own history states the business began in **Forlì in 1961** under the name **Sipla**, producing fiberglass Flying Juniors.
- After roughly ten years the company changed its name to **Comar**.
- The Comet 910 alone remained in production for more than fifteen years and was produced in almost **1,000 units**.
- The official history states the inherited business already had **more than 5,000 boats** sailing when the brand/technology changed hands in 1998; another official-domain history version states more than 4,500 boats had been produced.
- Current official material says Comar continues production and presents an extensive monohull/catamaran product lineage.

Primary sources:
- https://www.comaryachts.it/en/history/
- https://www.comaryacht.com/en/history/
- https://www.comaryacht.com/en/

Recommended modeling:
- entity: `Comar Yachts` — manufacturer/yard, Italy, active;
- predecessor/former-name relationship: Sipla;
- `Comet` = model/range brand lineage, not separate manufacturer;
- production-era start: 1961 exact for the Sipla/Comar manufacturing lineage;
- treat the 4,500/5,000 cumulative figures as differing company-history approximations rather than force a false exact value.

## 3. Solaris Yachts

**Decision:** `VERIFIED` — active Italian manufacturer/yard; counts toward the manufacturer/yard floor.

- Solaris' official milestones page states that the yard was founded in **Aquileia in 1974**.
- The company documents repeated sailing-yacht production across decades, including Solaris 47, Solaris One, Solaris Zero, Solaris 48cc, Solaris 52/72 and the modern ranges.
- The official yard page describes a **26,000 m²** shipyard and explicitly identifies Solaris Yachts as the manufacturer of Solaris sailing yachts.
- The current site lists a broad active sailing range (40 through 111RS) and has current 2026 news, independently establishing active status.
- Solaris Power and the later CNB relationship should remain separate brand/group relationships rather than being collapsed into the core Solaris sailing-yard identity.

Primary sources:
- https://www.solarisyachts.com/en/milestones/
- https://www.solarisyachts.com/en/yard/
- https://www.solarisyachts.com/en/

Recommended modeling:
- entity: `Solaris Yachts` — manufacturer/yard, Italy, active;
- production-era start: 1974 exact;
- current active sailing-yacht production directly supported by official 2026 surfaces.

## 4. Alpa — Fiesco / Offanengo

**Decision:** `VERIFIED` — historical Italian series-sailboat manufacturer/yard; counts toward the manufacturer/yard floor.

- The Alpa Historical Club's dedicated yard history states **Alpa (Azienda lavorazioni plastiche affini)** was registered in **1956** at Fiesco, Cremona.
- Production moved into a new Offanengo factory from the end of 1962, and the yard produced a substantial series of sailing cabin boats with designers including Illingworth, Van de Stadt and Sparkman & Stephens.
- The archive states the final yard-built boat was the **Alpa A34 in 1978** and that the yard closed in **1979**.
- The club maintains model-by-model registers and technical pages covering dinghies and numerous cabin-yacht models, supporting repeated product-line production rather than a one-off/custom-only operation.
- Zuanelli's current official history independently states that in 1975 it acquired know-how from the Alpa operation in Offanengo, corroborating Alpa's real industrial sailboat-building role.

Recognized historical archive / corroborating source:
- https://www.alpahistorical.org/storia-del-cantiere.html
- https://www.alpahistorical.org/barche---schede-tecniche.html
- https://www.alpahistorical.org/cabinati-oltre-9-metri.html
- https://zuanelli.it/chi-siamo/

Recommended modeling:
- entity: `Alpa` / `Cantiere Nautico Alpa` — historical manufacturer/yard, Italy, defunct;
- production-era start: 1956 exact at company level;
- final production: 1978; closure: 1979;
- do not merge any later attempted resurrection of the Alpa name into the original Fiesco/Offanengo manufacturing entity without separate evidence.

## 5. Cantiere Zuanelli

**Decision:** `VERIFIED` — active Italian manufacturer/yard with repeated/miniseries sailing-yacht production; counts toward the manufacturer/yard floor.

- Zuanelli's official history states the company was founded by **Pietro Zuanelli in 1972**.
- In **1975** the yard acquired know-how from Alpa of Offanengo and specialized in fiberglass sailing-yacht construction.
- The current official site lists a recurring Zuanelli sailing range including **Z30, Z34, Z36, Z40, Z401, Z49/Z49S and Z52DH**.
- The company explicitly describes its work as including its own models, third-party builds, miniseries and one-offs. The presence of a long-lived named multi-model range is enough for the slice's repeated/series-production boundary; the yard is not being admitted merely because it can build custom boats.
- The current site and current collaboration activity establish an active yard in 2026.

Primary sources:
- https://zuanelli.it/chi-siamo/
- https://zuanelli.it/nuovo-serie-zuanelli/
- https://zuanelli.it/nuovo-serie-zuanelli/z40-2/
- https://zuanelli.it/

Recommended modeling:
- entity: `Cantiere Zuanelli` — manufacturer/yard, Italy, active;
- company founding: 1972;
- sailboat-construction specialization positively evidenced from 1975;
- preserve `custom/miniseries` production character rather than describing the yard as high-volume mass production.

## 6. Italia Yachts

**Decision:** `VERIFIED` — active Italian manufacturer/yard; counts toward the manufacturer/yard floor.

- Italia Yachts' official shipyard page says the company was founded in **2011 in Chioggia, Venice** as a boatyard designing and building sailing yachts.
- Its official chronology documents multiple repeated model launches from 2011 onward, including IY 10.98, 13.98, 15.98, 9.98 and 12.98.
- At the end of 2022 the company opened a dedicated production yard in which it states that every production phase is managed internally.
- The current site continues to describe active in-house yacht production. The addition of a motorboat line from 2023 does not change its established sailing-yacht manufacturer eligibility.

Primary sources:
- https://www.italiayachtsinternational.com/en_en/azienda/cantiere/
- https://www.italiayachtsinternational.com/en_en/azienda/
- https://italiayachtsinternational.com/en/shipyard/

Recommended modeling:
- entity: `Italia Yachts` — manufacturer/yard, Italy, active;
- production-era start: 2011 exact;
- later facility moves/production-site changes should be modeled as facility history, not new manufacturer identities.

## 7. North Wind Yachts — historical Barcelona series yard

**Decision:** `VERIFIED` as a historical Spanish series-sailboat manufacturer/yard; counts toward the manufacturer/yard floor. **Current legal/operating continuity remains `unknown` and must not be inferred from the surviving old domain.**

- Multiple independent surviving-boat records identify North Wind Yachts, Spain, as the builder of repeated North Wind sailing-yacht models across the 1980s and 1990s.
- A preserved reproduction of the former North Wind yard's own company text states that the Industrial North Wind yard was founded in the Barcelona area in **1973**, had built more than **380 units** over an initial twenty-year period and had more than **500 North Wind boats** sailing worldwide; it describes a seven-model sailing range and average production of 6–10 units annually at that time.
- A current Barcelona brokerage/yard article describes the site as North Wind's **former** production yard and says it was once the producer of globetrotting yachts before transition toward repair/refit use.
- Critically, the old `nwvi.eu` domain now belongs to an unrelated company called **Northwind Venture International SL** providing marine fuel/bunkering and logistics. That domain must therefore not be used as evidence of continuing North Wind yacht manufacture.
- Exact closure/end year and corporate successor should remain unknown unless separately established.

Independent/supporting sources:
- https://www.networkyachtbrokersbarcelona.com/northwind-yachts-barcelona/
- https://www.devalk.nl/en/yachtbrokerage/252093/NORTH-WIND-47.html
- https://barcosnautica.com/en/embarcaciones/north-wind-47
- historical company-text reproduction: https://sailwiki.com/shipyard/north-wind-yachts-esp/
- current unrelated domain content proving non-continuity: https://nwvi.eu/

Recommended modeling:
- entity: historical `North Wind Yachts` physical manufacturer/yard, Spain;
- start year around 1973 supported by preserved company-history text;
- current status: historical/unknown rather than active;
- do not link the present Northwind Venture International fuel/logistics company as successor without explicit evidence;
- keep any later Monty North / Monty Nautic corporate relationship separate pending targeted research.

## 8. Belliure

**Decision:** `VERIFIED` — historical Spanish manufacturer/yard with strong direct series-sailboat evidence; counts toward the manufacturer/yard floor.

- Belliure's surviving official company history states the business was founded by **Vicente Belliure in Calpe in 1953** and closed definitively in **mid-2017** after 64 years.
- A recreational-boat division was established in **1974**, introducing GRP construction.
- The company states that more than **170 GRP boats** were built thereafter, including sailing yachts of 30, 35, 40, 41 and 50 feet, followed by larger 63–86 ft sailing yachts.
- The official chronology gives especially strong repeated-production evidence: the fiberglass **Endurance 35 reached 160 units**.
- The official history explicitly states that the company no longer conducts any activity, removing current-status ambiguity.

Primary sources:
- https://www.belliure.com/pa-historia-536-441.html
- https://www.belliure.com/pa-actualidad-del-astillero-536-440-es.html
- https://www.belliure.com/pa-belliure-35-endurance-536-719-es.html
- https://www.belliure.com/

Recommended modeling:
- entity: `Belliure` / Vicente Belliure shipyard — manufacturer/yard, Spain, defunct;
- company founding: 1953;
- sail/recreational-yacht production positively evidenced from 1974/1975;
- closure: mid-2017 exact at the company-history level;
- fishing-vessel, sail-yacht and later motor-yacht production remain product/activity phases of the yard, not separate yards by default.

## Batch outcome

All eight candidates independently satisfy the SLICE-0019 manufacturer/yard eligibility boundary:

1. Cantiere del Pardo — verified, active, Italy.
2. Comar Yachts / Sipla — verified, active, Italy.
3. Solaris Yachts — verified, active, Italy.
4. Alpa — verified, historical/defunct, Italy.
5. Cantiere Zuanelli — verified, active, Italy.
6. Italia Yachts — verified, active, Italy.
7. North Wind Yachts — verified historical series yard, Spain; current continuity unknown.
8. Belliure — verified, historical/defunct, Spain.

### Floor impact

This batch yields **8 new distinct manufacturer/yard-floor candidates** before the final mechanical registry deduplication.

The previous reconciliation estimated roughly **95–99** eligible recovered manufacturer/yard entities after final continuity/deduplication risk. If all eight remain distinct during integration, the planning range becomes approximately **103–107**, leaving roughly **13–17** additional verified manufacturer/yard entities to exceed the `>=120` floor safely.

This is a planning estimate only. `registry.json` is still untouched and no binding registry count is asserted by this file.

## Deferred Southern-Europe leads

The following were deliberately not researched in this batch and remain candidate leads for later bounded work if needed:

- Astilleros Gallart / ARESA lineage — preliminary evidence exists, but the available sailboat-specific historical evidence is weaker and requires careful pre-/post-1966 identity modeling.
- North Wind / Monty North corporate successor relationship — separate targeted continuity question.
- Naoglass / Puma.
- Dresport / Furia.
- Mylius Yachts.
- Olympic Yachts.
- Dromor Yachts.
- Sarch Boats.

The next highest geographic-value batch should move to **Taiwan / Hong Kong / Japan** rather than exhaust Southern Europe immediately, because the Asia-Pacific workstream was completely lost and adds both yard count and country/macro-region coverage.
