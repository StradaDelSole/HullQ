# SLICE-0019 new research batch 009 — Australia, New Zealand, South Africa

**Scope:** bounded independent research of 8 manufacturer/yard candidates selected to broaden the global manufacturer universe after the Southern-Europe and Asia core batches. Candidate selection may have been informed by the temporary external gap detector, but every decision in this file is based only on independent sources listed below. This file remains valid if `research/manufacturers/temporary_external_reference/` is later deleted.

**Method:** before external research, the HullQ repository was searched for the candidate names to avoid duplicating already-recovered SLICE-0019 records. No matching existing manufacturer research record was found for these eight candidates. Research focused on physical manufacturer/yard identity, repeated/series sailboat production, operating era, current/historical status, and brand-vs-yard relationships. No `registry.json` or canonical entity is modified by this note.

## 1. McConaghy Boats — Australia / China

**Decision:** `VERIFIED` — active physical yacht manufacturer with repeated production sailboat programs; counts toward the manufacturer/yard floor.

- McConaghy's official history states the company was founded by **John McConaghy in 1967**.
- It began with skiffs, Tornado and A-class catamarans and became an early adopter of advanced composite construction for sailing craft.
- The official build history demonstrates repeated production rather than only one-off custom work: examples include 500 WASZP foiling Moths, 156 Mach 2 Moths in one year, multiple Ker 40+/46 designs, five MC31 one-design yachts, multiple Elliott 6/7 boats and many Farr 40 one-designs.
- The current site explicitly describes McConaghy as doing **production boat building with full custom capability** and maintains active sailing multihull and race-boat ranges.
- McConaghy states it has built a fleet of more than 150 yachts of 30 ft and above and continues to build current MC sailing catamarans.
- Manufacturing facilities exist in both Australia and China; the company history states the China shipyard opened in 2006 and current contact/facility pages still identify both factories.

Primary sources:
- https://mcconaghyboats.com/our-story/
- https://mcconaghyboats.com/
- https://mcconaghyboats.com/yachts/race-boats/
- https://mcconaghyboats.com/yachts/under-25-foot-sport/
- https://mcconaghyboats.com/yachts/mc-multihulls/
- https://mcconaghyboats.com/facilities/
- https://mcconaghyboats.com/contact/

Recommended modeling:
- entity: `McConaghy Boats` — manufacturer/yard, Australian origin, active;
- start year: 1967 exact;
- current production footprint: Australia + China;
- do not create separate manufacturer identities merely because individual models were designer-branded or because production occurred at multiple facilities.

## 2. Bashford Boats / Bashford International / Sydney Yachts — Australia

**Decision:** `VERIFIED` — historical Australian production-yard lineage; counts toward the manufacturer/yard floor. Keep the later Sydney Yachts brand and Croatian production relationship explicit rather than merging them into the original Australian yard.

- Ian Bashford's original Australian factory produced repeated one-design boats including **J/24s, J/35s, Etchells and Hobie Cats**.
- Contemporary Cruising Yacht Club of Australia material documents the **Sydney 60** as built by Bashford Boatbuilders and describes the successful Bashford 41/36 lineage.
- Contemporary industry coverage identifies Bashford International's South Nowra factory and its production tooling/program for the Sydney 40; it undertook to build up to 15 Sydney AC40s for a one-design event.
- Contemporary Australian coverage describes the Sydney 38 as an Australian production yacht and identifies hull 17 coming out of the Nowra factory.
- Sydney Yachts' own company page states that since **2013** Sydney Yachts have been built at **AD Boats in Croatia**. This establishes a clear production transfer: the Australian Bashford/Sydney yard history is real, but the post-2013 physical builder is a separate Croatian yard already represented independently in SLICE-0019.

Sources:
- https://www.performanceboating.com.au/about/
- https://s3.ap-southeast-2.amazonaws.com/media.prod.cyca/media/3440173/1996-shyr-program-web.pdf
- https://cyca.com.au/wp-content/uploads/2020/05/Offshore-October-November-1998.pdf
- https://www.boatsales.com.au/editorial/details/sydney-38-9141/
- https://www.practical-sailor.com/sailboat-reviews/used_sailboats/sydney-yachts-36cr/
- https://www.sydneyyachts.com/company/sydney-yachts.html
- https://www.poslovni.hr/vijesti/dobar-posao-u-splitu-proizvodit-ce-jedrilice-za-australce-215097

Recommended modeling:
- historical physical manufacturer/yard lineage: `Bashford Boats` / `Bashford International`, Australia;
- `Sydney Yachts` as the later brand/marketing/product-line identity;
- Australian production active from early 1980s through the pre-2013 era;
- production transferred to AD Boats, Croatia, from 2013;
- do not count AD Boats again through the Sydney Yachts brand relationship.

## 3. Seawind Catamarans — Australia / Vietnam / Türkiye

**Decision:** `VERIFIED` — active series-sailboat manufacturer with Australian origin and current multinational manufacturing footprint; counts toward the manufacturer/yard floor.

- Seawind's official history states founder **Richard Ward** started the company in **1982** in a small Sydney factory.
- The company progressed through repeated cruising-catamaran series including Seawind 33, 24, 1000, 850, 1200, 1160, 1250, 1600, 1190 Sport, 1260 and 1370.
- The official history states **more than 350 Seawind 24 hulls** were built, independently satisfying the repeated-production boundary on a single model line.
- The company later moved to larger Australian premises at Wollongong/Bellambi.
- Seawind's current official history identifies its **Saigon Shipyard in Vietnam as the primary production facility**, employing over 600 people, and a further production facility in Türkiye opened in 2021.
- A 2026 official production article documents the Seawind 1170 construction process at the Izmir facility, proving current physical sailboat production.

Primary sources:
- https://www.seawindcats.com/about-us/
- https://www.seawindcats.com/blog/seawind-catamarans-40-years-of-sailing-excellence/
- https://www.seawindcats.com/blog/inside-the-seawind-1170-production-process/

Recommended modeling:
- entity: `Seawind Catamarans` — manufacturer/brand with real manufacturing operation, active;
- origin country: Australia;
- start: 1982 exact;
- current primary manufacturing: Vietnam, plus Türkiye production;
- preserve historical Australian production and current foreign facilities as production relationships, not separate brand entities.

## 4. Robertson & Caine — South Africa

**Decision:** `VERIFIED` — active large-scale South African series-catamaran manufacturer; counts toward the manufacturer/yard floor.

- Robertson & Caine's official overview states the company was founded by **John Robertson and Jerry Caine in 1991**.
- The current official manufacturing page states that it manufactures **three sailing catamarans and three power catamarans** in Cape Town.
- The company's official achievements page records **more than 3,132 catamarans launched from 1997 through April 2026**, with a pedigree of 24 sailing-catamaran models and seven powercat models.
- The current sailing range includes Leopard 43, 46 and 52.
- The company operates a large physical manufacturing footprint in Cape Town and employs more than 2,400 people.
- Ownership by Vox Ventures/PPF is a corporate ownership relationship and does not alter the distinct physical manufacturer identity.

Primary sources:
- https://www.robertsonandcaine.com/overview.html
- https://www.robertsonandcaine.com/manufacturing.html
- https://www.robertsonandcaine.com/achievements.html
- https://www.robertsonandcaine.com/

Recommended modeling:
- entity: `Robertson & Caine (Pty) Ltd` — manufacturer/yard, South Africa, active;
- start: 1991 exact at company-history level;
- Leopard / Moorings / Sunsail product-brand relationships modeled separately;
- current owner PPF/Vox Ventures as ownership relationship only.

## 5. St Francis Marine — South Africa

**Decision:** `VERIFIED` — active South African small-series catamaran manufacturer/yard; counts toward the manufacturer/yard floor.

- St Francis Marine's official current site states the company was founded in **1988 in St Francis Bay, South Africa**.
- Founder-history material describes how Duncan Lethbridge commissioned Angelo Lavranos to design the first St Francis 43; demand led directly to a factory being created to manufacture the boats.
- The official site states the company has built **more than 120 boats** and remains owned by the original founders.
- Current models include the St Francis 460 and 500, and the site continues to describe current custom build operations.
- The company operates a dedicated roughly 4,000 m² production facility at St Francis Bay.

Primary sources:
- https://stfranciscatamarans.com/
- https://www.stfranciscatamarans.com/a-brief-history
- https://www.stfranciscatamarans.com/our-history
- https://www.stfranciscatamarans.com/the-team
- https://www.stfranciscatamarans.com/contact

Recommended modeling:
- entity: `St Francis Marine` — manufacturer/yard, South Africa, active;
- start: 1988 exact;
- current production remains small-series/bespoke but repeated-production eligibility is unambiguous from >120 completed boats and recurring models.

## 6. Knysna Yacht Company — South Africa

**Decision:** `VERIFIED` — active South African boutique series/small-series catamaran manufacturer; counts toward the manufacturer/yard floor.

- Local historical reporting states **Kevin Fouché and partners opened Knysna Yacht Company in 2002** specifically to build performance long-range cruising catamarans.
- The yard developed repeated models including the Knysna 440, 480, 500 and 500SE; by 2015 it had launched its 40th vessel.
- The current official company site describes **25 years and more than 100 builds**, confirming substantial repeated production rather than one-off custom construction.
- Current official build-slot listings show scheduled 2025-2026 production for both the 550 and 500SE families, and the company continues to operate its own boatyard in Knysna.
- South African marine-industry material independently lists Knysna Yacht Company as a recreational boat builder established in 2002.

Sources:
- https://www.knysnayachtco.com/
- https://www.knysnayachtco.com/about-knysna-yacht-company/
- https://www.knysnayachtco.com/the-craft-behind-knysna-yacht-companys-catamarans/
- https://www.visitknysna.co.za/experiences/arts-culture/a-boat-building-legacy/
- https://www.knysnaplettherald.com/News/Article/Local-News/technology-advances-boat-building-tradition-20170711
- https://boatingsouthafrica.co.za/wp-content/uploads/2022/02/sabbexguidefeb2022_compressed.pdf

Recommended modeling:
- entity: `Knysna Yacht Company` — manufacturer/yard, South Africa, active;
- start: 2002 exact;
- repeated production clearly supported despite boutique/limited-volume positioning.

## 7. VOYAGE Yachts — South Africa

**Decision:** `VERIFIED` — active South African small-series sailing-catamaran manufacturer; counts toward the manufacturer/yard floor.

- VOYAGE's current official site states its yachts have been **designed, developed and manufactured in Cape Town since 1994**.
- Current production/marketing includes the VOYAGE 510 and VOYAGE 590 sailing catamarans.
- The current company history describes a more-than-three-decade building lineage and identifies the 510 as purpose-built in a new Cape Town production facility.
- A South African boatbuilding-industry guide records the company as established in 1994 and states that it had already built **well over 150 catamarans** by the mid-2010s, across models including the DC45, 480, 520 and 600.
- The current official site continues to describe VOYAGE as manufacturing luxury performance-oriented cruising catamarans in Cape Town.

Primary/industry sources:
- https://www.voyageyachts.com/
- https://www.voyageyachts.com/about-us
- https://www.voyageyachts.com/catamarans
- https://www.voyageyachts.com/catamarans/voyage-510
- https://www.voyageyachts.com/catamarans/voyage-590
- https://boatingsouthafrica.co.za/wp-content/uploads/2018/03/BSA-Guide-2016-Standard.pdf

Recommended modeling:
- entity: `VOYAGE Yachts` — manufacturer/yard, South Africa, active;
- start: 1994 exact;
- current Cape Town production confirmed;
- charter/sales operations remain relationships, not manufacturer identity substitutes.

## 8. Cavalier Yachts — New Zealand

**Decision:** `VERIFIED` — historical New Zealand production-yacht manufacturer; counts toward the manufacturer/yard floor.

- Co-founder **Peter Smith's own biography** states that he co-founded and developed Cavalier Yachts for more than 15 years and that it became the largest yacht-building company in the Southern Hemisphere at the time.
- His account states the company produced a range of craft from **23 to 47 ft**, and identifies the Cavalier 39 `Apteryx` as one of the final boats of the original Cavalier period.
- Current Boating New Zealand historical coverage traces Cavalier to the partnership of Peter K. Smith and John Salthouse and describes the company as the largest production boat builder in the Southern Hemisphere during its 1970s peak.
- Recognized Cavalier owner-history material states the yard had **11 designs simultaneously in production** at peak and records more than 20 Cavalier 36s alone.
- Historical summaries record around **170 Cavalier 32s** and 84 Cavalier 39s; exact lifetime total remains uncertain and need not be made falsely precise.
- The original company was damaged by the 1979 New Zealand sales-tax shock and later entered receivership; subsequent `Export Yachts Ltd` activity should be represented as a successor/continuation relationship rather than silently treated as the same legal entity.

Sources:
- https://www.petersmith.net.nz/about/peter.php
- https://www.boatingnz.co.nz/2026/05/the-iconic-cavalier-39-bluewater-legend-now-for-sale/
- https://cav36.com/
- https://www.cavalier28.com/history
- https://www.rolexsydneyhobart.com/the-yachts/1974/cavelieri/

Recommended modeling:
- entity: historical `Cavalier Yachts` manufacturer/yard, New Zealand;
- production era: 1970s through approximately 1979/early receiver era, exact endpoint to remain uncertainty-preserving;
- `Export Yachts Ltd` as successor/continuation relationship rather than alias;
- do not merge designer names, Salthouse Brothers or Australian licensed Cavalier production into this single physical-yard record.

## Batch outcome

All eight candidates independently satisfy the SLICE-0019 manufacturer/yard eligibility boundary:

1. McConaghy Boats — verified active manufacturer/yard, Australian origin with Australia/China production.
2. Bashford Boats / Bashford International — verified historical Australian production yard; Sydney Yachts later transferred production to AD Boats in Croatia.
3. Seawind Catamarans — verified active manufacturer, Australian origin with current Vietnam/Türkiye production.
4. Robertson & Caine — verified active large-scale South African series-catamaran manufacturer.
5. St Francis Marine — verified active South African small-series catamaran yard.
6. Knysna Yacht Company — verified active South African boutique series/small-series yard.
7. VOYAGE Yachts — verified active South African series/small-series catamaran yard.
8. Cavalier Yachts — verified historical New Zealand production-yacht manufacturer.

### Floor impact

This batch yields **8 new distinct manufacturer/yard-floor candidates** before final mechanical registry deduplication.

The previous planning range after RESEARCH-008 was approximately **111–115** eligible manufacturer/yard entities. If all eight remain distinct during integration, the planning range becomes approximately **119–123**.

This means the research universe is now very close to — and may already exceed — the SLICE-0019 `>=120` manufacturer/yard floor, but the floor must **not** yet be declared satisfied. The lower bound of the conservative planning range is still 119 and exact deduplication/continuity treatment can move the count.

The next correct step is therefore **mechanical consolidation and exact counting**, not another broad research wave. Only if that exact pass lands below 120 should one or two additional independently verified yards be researched to create safe headroom.

### Geographic effect

This batch materially improves global coverage by adding strong manufacturer/yard records from:

- Australia;
- New Zealand;
- South Africa;

and complements the already-added Southern-Europe and Asian records. Country and macro-region floors still require final normalized registry counting rather than arithmetic over research notes.

`registry.json` remains untouched by this file.
