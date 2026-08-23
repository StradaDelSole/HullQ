# SLICE-0019 new research batch 008 — Asia core yards

**Scope:** bounded independent research of 8 manufacturer/yard candidates selected to replace part of the completely lost Asia-Pacific workstream. Candidate selection may have been informed by the temporary external gap detector, but every decision in this file is based only on independent sources listed below. This file remains valid if `research/manufacturers/temporary_external_reference/` is later deleted.

**Method:** before external research, the HullQ repository was searched for the candidate names to avoid duplicating already-recovered SLICE-0019 records. No matching existing manufacturer research record was found for these eight candidates. Research focused on physical manufacturer/yard identity, repeated/series sailboat production, operating era, current/historical status, and brand-vs-yard relationships. No `registry.json` or canonical entity is modified by this note.

## 1. Cheoy Lee Shipyards — Hong Kong / China

**Decision:** `VERIFIED` — long-running physical shipyard with a major historical series-sailboat production role; counts toward the manufacturer/yard floor.

- Cheoy Lee's own heritage states that the Lo-family shipbuilding business traces to Shanghai in the late 1800s and moved to Hong Kong in 1936.
- By the mid-1950s the yard was producing teak sailing and motor yachts for export. The official history identifies the **Lion 35** as its first production yacht in 1957, with more than 70 built in wood and a further 27 in fiberglass.
- The official heritage states that in 1964 alone **252 vessels** entered the order book, driven mainly by yacht sales into the US market.
- The yard later moved its full construction operation to the Hin Lee (Zhuhai) facility in mainland China. The present-day company remains active, but current production is primarily large motor yachts and commercial vessels.
- A recognized Cheoy Lee owners' archive places the end of the classic sailboat-production era at roughly 1990; that end year should remain estimated unless a stronger company record is found.

Primary/recognized sources:
- https://cheoylee.com/heritage/
- https://cheoyleeyachts.com/en/shipyard/ourstory/
- https://cheoyleeyachts.com/en/shipyard/
- recognized owner archive: https://www.cheoyleeassociation.com/a_entrance.htm

Recommended modeling:
- entity: `Cheoy Lee Shipyards` — manufacturer/yard;
- country for the qualifying historical sail-production record: Hong Kong;
- current construction relationship: Hin Lee (Zhuhai), China;
- corporate/yard status: active;
- series-sailboat production: positively evidenced from the 1950s to approximately 1990;
- do not treat present motor/commercial-vessel production as evidence of current sailboat production.

## 2. Ta Yang Yacht Building Co., Ltd. / Tayana — Taiwan

**Decision:** `VERIFIED` — historical Taiwanese series-sailboat manufacturer/yard; counts toward the manufacturer/yard floor.

- Taiwan company-registration material identifies **TA YANG YACHT BUILDING CO., LTD.** as the legal company, registered 2 November 1972.
- The Taiwan Yacht Industry Association listed Ta Yang as a professional yacht manufacturer and explicitly listed a broad sailboat range: 37, 42, 47, 48, 52, 54, 55, 58, 64, 72 and V460.
- The Tayana 37 became a major repeated-production cruising design; independent historical sources report roughly 600 of that model and more than 1,400 Ta Yang/Tayana bluewater cruisers overall.
- The legal company was formally dissolved on **30 September 2020**, removing current-status ambiguity.
- `Tayana` should be modeled as the product/brand lineage of the Ta Yang physical manufacturer, not as a separate yard.

Primary/association/register sources:
- Taiwan company record: https://www.findcompany.com.tw/index.php/en/%E5%A4%A7%E6%B4%8B%E9%81%8A%E8%89%87%E4%BC%81%E6%A5%AD%E8%82%A1%E4%BB%BD%E6%9C%89%E9%99%90%E5%85%AC%E5%8F%B8
- Taiwan Yacht Industry Association member material: https://www.taiwan-yacht.com.tw/en-members.html
- historical association list PDF: https://www.taiwan-yacht.com.tw/108member.pdf

Recommended modeling:
- entity: `Ta Yang Yacht Building Co., Ltd.` — manufacturer/yard, Taiwan, defunct;
- legal registration: 1972-11-02;
- closure/dissolution: 2020-09-30 exact at company-record level;
- relationship: Tayana = brand/product family;
- repeated sailboat production independently well established.

## 3. Ta Shing Yacht Building Co., Ltd. — Taiwan

**Decision:** `VERIFIED` — active Taiwanese physical yacht manufacturer with extensive historical series-sailboat production; counts toward the manufacturer/yard floor.

- Taiwan Ministry of Economic Affairs company data identifies **TA SHING YACHT BUILDING CO., LTD.**, active/approved, with the present legal entity registered in 1977 and two approved factories.
- The official business-purpose registration explicitly includes manufacturing/export of fiberglass yachts and vessels.
- Taiwan Yacht Industry Association material lists Ta Shing and records a motorsailer product in the later product mix.
- Historical manufacturer evidence is much broader: Ta Shing built the **Taswell**, **Tashiba**, Mason and multiple OEM sailing-yacht lines. Contemporary/reproduced Mason material explicitly names Ta Shing as the builder, and recognized historical sources document multiple repeated models.
- A predecessor boatbuilding lineage under Shing Sheng is commonly traced to 1957. This predecessor history should be modeled separately from the current legal entity start rather than backdating the 1977 company registration.

Primary/recognized sources:
- Taiwan Ministry company record: https://findbiz.nat.gov.tw/fts/company/69559634?fhl=en
- Taiwan Yacht Industry Association: https://www.taiwan-yacht.com.tw/108member.pdf
- Mason owner/archive reproduction of production material: https://mason-sailboats.org/wp-content/uploads/2018/03/Mason-43-and-44-Review.pdf
- Mason 63 original specification material: https://mason-sailboats.org/wp-content/uploads/2018/03/Mason-63-Specifications-Drawings.pdf

Recommended modeling:
- entity: `Ta Shing Yacht Building Co., Ltd.` — manufacturer/yard, Taiwan, active;
- legal-entity production era start: 1977 exact;
- predecessor relationship: Shing Sheng boatyard, with older lineage handled separately if retained;
- historical sailing brands/OEM relationships must remain explicit rather than merged into the yard identity.

## 4. Queen Long Marine Co., Ltd. / Hylas — Taiwan

**Decision:** `VERIFIED` — active Taiwanese series-sailboat manufacturer/yard; counts toward the manufacturer/yard floor.

- Hylas' own company material states that **Queen Long Marine** is the shipyard, founder and owner of the Hylas brand and has produced sailboats for over 40 years.
- The current Hylas site identifies multiple sailing-yacht designs and explicitly states they are built by Queen Long Marine.
- Taiwan company data lists Queen Long Marine as an approved/active company in Kaohsiung.
- Taiwan Yacht Industry Association material lists the yard and a repeated Hylas sailing range including 46, 48, 49, 56, 57, 60, 63 and 70.
- A June **2026** Ship and Ocean Industries R&D Center award identifies the builder of a Hylas 48 as Queen Long Marine, providing very fresh direct evidence of continued current production.
- Historical sources vary between 1978 and 1979 for the very beginning of the business/legal registration. Preserve that distinction rather than forcing a single founding date.

Primary sources:
- https://www.hylasyachts.com/about/
- https://www.hylasyachts.com/
- https://www.hylasyachts.com/media/posts/news/news-from-the-hylas-yard-september-2020/
- Taiwan company record: https://findbiz.nat.gov.tw/fts/company/85848604
- 2026 industry award: https://www.soic.org.tw/en/2026%E3%80%8C%E7%89%B9%E8%89%B2%E9%81%8A%E8%89%87%E7%8D%8E%E3%80%8D-%E3%80%8Chylas-48%E3%80%8D/
- association range evidence: https://www.taiwan-yacht.com.tw/108member.pdf

Recommended modeling:
- entity: `Queen Long Marine Co., Ltd.` — manufacturer/yard, Taiwan, active;
- relationship: Hylas = yard-owned brand/product family;
- present production verified in 2026;
- founding/business-origin and formal-registration dates should be uncertainty-preserving if both are retained.

## 5. New Japan Yacht Co., Ltd. — Japan

**Decision:** `VERIFIED` — active Japanese series-sailboat manufacturer; counts toward the manufacturer/yard floor.

- The company's current official site states it was established **4 November 1969** in Shizuoka and is one of the few remaining domestic Japanese yacht manufacturers.
- The company states cumulative production has exceeded **800 yachts**.
- It explicitly says it continues to design and manufacture yachts in-house.
- The current manufacturing page lists active sailing-oriented products including **Lune de Mai 550**, **Libeccio 26**, and the Loup de Mer power-sailer, while the heritage list includes older repeated models.
- The official site states the **Vent de Fete 300**, introduced in 1981, exceeded **200 launched units**, independently demonstrating repeated production.

Primary sources:
- https://www.njy.co.jp/company/
- https://www.njy.co.jp/yacht-manufacturing/

Recommended modeling:
- entity: `New Japan Yacht Co., Ltd.` — manufacturer/yard, Japan, active;
- production-era start: 1969 exact at company level;
- cumulative >800 yachts = company-reported production figure;
- current active sailboat manufacturing positively evidenced in 2026.

## 6. Yamaha Motor — historical sailboat-manufacturing role, Japan

**Decision:** `VERIFIED` — historical major series-sailboat manufacturer role within Yamaha's marine business; counts toward the manufacturer/yard floor, with corporate scope carefully bounded.

- Yamaha Motor's own 60-year marine history explicitly documents repeated production and sale of sailing yachts, not merely engines or race sponsorship.
- Official chronology states that Yamaha restarted sales of full sailing cruisers in **1970** with multiple YAMAHA models and continued broad model releases through the 1970s, 1980s and 1990s.
- In 1976 the official history records the **Y-25 Mark II selling 100 boats in roughly five months**.
- The 1978 history identifies a Yamaha production yacht winning the Quarter Ton World Championship and lists several production yacht models for that year.
- Official 1980s and 1990s chronologies continue to list numerous Yamaha sailing-yacht models, including Y-34CK, Y-36 variants, Y-45, Y-31 and others.
- Current Yamaha marine operations remain active but the surfaced official 2000s/2010s product chronologies no longer show a comparable production sailboat range. Therefore current sailboat production should **not** be inferred.

Primary sources:
- https://www.yamaha-motor.co.jp/marine/history/
- https://www.yamaha-motor.co.jp/marine/history/products-history/1970/
- https://www.yamaha-motor.co.jp/marine/history/products-history/1980/
- https://www.yamaha-motor.co.jp/marine/history/products-history/1990/

Recommended modeling:
- entity: `Yamaha Motor` / bounded marine yacht-manufacturing activity — manufacturer/legal organization, Japan;
- historical series-sailboat production positively evidenced from at least 1970 through the 1990s;
- corporate status remains active, but sailboat-production status = historical;
- do not count racing-only custom projects as the basis for eligibility; eligibility rests on the repeated production yacht catalog.

## 7. Fuji Yacht Builders Ltd. — Japan

**Decision:** `VERIFIED` — historical Japanese series-sailboat manufacturer/yard; counts toward the manufacturer/yard floor.

- A recognized historical article documents that former Far East/TOA personnel established **Fuji Yacht Builders** at Yokosuka and launched the Fuji production-yacht line beginning with the Fuji 35 and Fuji 45 in the early 1970s.
- The same historical account states that more than **200 Fuji boats** were eventually built across the product line.
- The surviving Fuji owners' archive preserves original sales brochure material and identifies John G. Alden's office as designer of the Fuji 35 for Fuji Yacht Builders.
- The owner reconstruction lists substantial surviving hull numbers and reports roughly 128 Fuji 35s, while other models included the Fuji 32, 40 and 45.
- Historical sources indicate the yard ceased operations around the turn of the 1980s. Exact closure year varies slightly by secondary archive; retain the end year as estimated unless a formal Japanese corporate record is found.

Recognized historical/owner sources:
- https://goodoldboat.com/made-in-japan/
- https://www.fujiyachts.net/fuji35_spec/fuji35_original_brochure/fuji35_brochure_org.html
- https://www.fujiyachts.net/owners/fuji35owners.html
- direct historical recollection preserved at https://www.fujiyachts.net/history/hirokuni.html

Recommended modeling:
- entity: `Fuji Yacht Builders Ltd.` — historical manufacturer/yard, Japan, defunct;
- production era: early 1970s to approximately 1980/1982, end uncertainty-preserving;
- do not merge with predecessor Far East Yachts even though personnel, site and mould relationships overlap.

## 8. Far East Yachts / Far East Boat Ltd. — Japan

**Decision:** `VERIFIED` — historical Japanese series-sailboat manufacturer/yard; counts toward the manufacturer/yard floor.

- The Mariner Owners Association historical archive states that Clair Oberly founded the Japanese operation in Yokosuka in 1957/1958, initially building wooden H-28s and then Mariner series yachts.
- Multiple repeated models are directly documented: Mariner 31, 32, 35, 36 and 40 plus an S&S 40.
- The archive documents the transition to fiberglass Mariner production in the late 1960s.
- Particularly strong evidence comes from a preserved first-person historical letter by **Takao Sato**, the former chief engineer. He describes the 1958 establishment, subsequent relationship with Kawasaki Heavy Industries, mould production, repeated Mariner construction and the closure/reorganization around the 1971 currency shock.
- A separate first-person recollection by Hirokuni Ijuin corroborates the physical Yokosuka yard and later Fuji/Clair & Kato succession relationships.
- Far East Yachts must remain distinct from later **Clair & Kato Yachts**, Clair Yachts in California and Fuji Yacht Builders.

Owner/direct historical sources:
- https://www.marineryachts.com/
- https://www.marineryachts.com/fey/fey.htm
- https://www.fujiyachts.net/history/takao.html
- https://www.fujiyachts.net/history/hirokuni.html
- historical synthesis: https://www.fujiyachts.net/history/history.html

Recommended modeling:
- entity: `Far East Yachts` / `Far East Boat Ltd.` — historical manufacturer/yard, Japan;
- establishment: 1958 is best supported for the formal operation, with 1957 precursor construction activity;
- end of original Far East/KHI production around 1971;
- successor/reorganization relationships modeled explicitly, not as aliases.

## Batch outcome

All eight candidates independently satisfy the SLICE-0019 manufacturer/yard eligibility boundary:

1. Cheoy Lee Shipyards — verified physical yard; historical sailboat production, Hong Kong, active company with current China production.
2. Ta Yang Yacht Building / Tayana — verified historical series sailboat yard, Taiwan, dissolved 2020.
3. Ta Shing Yacht Building — verified active physical yard, Taiwan, extensive historical sailboat/OEM production.
4. Queen Long Marine / Hylas — verified active series sailboat yard, Taiwan, current production confirmed in 2026.
5. New Japan Yacht — verified active series sailboat manufacturer, Japan, >800 cumulative yachts claimed by company.
6. Yamaha Motor marine yacht activity — verified major historical Japanese production-sailboat manufacturer role.
7. Fuji Yacht Builders — verified historical Japanese production yard.
8. Far East Yachts — verified historical Japanese production yard.

### Floor impact

This batch yields **8 new distinct manufacturer/yard-floor candidates** before final mechanical registry deduplication.

The previous planning range after RESEARCH-007 was approximately **103–107** eligible manufacturer/yard entities. If all eight remain distinct during integration, the planning range becomes approximately **111–115**, leaving roughly **5–9** additional verified manufacturer/yard entities to clear the `>=120` floor safely.

This batch also materially improves geographic coverage with strong Asian production history across **Hong Kong, Taiwan and Japan**. Country-floor counting remains subject to final registry normalization, especially for Cheoy Lee's Hong Kong legal/history identity versus its current Zhuhai construction facility.

`registry.json` remains untouched; these are independent research conclusions only.

## Next recommended batch

Do not over-research Japan/Taiwan merely to inflate the count. The next highest-value batch should combine **Australia / New Zealand / South Africa**, prioritizing physical builders such as McConaghy, Sydney/Bashford, Seawind, Robertson & Caine, St Francis Marine, Knysna Yacht Company, Voyage Yachts and one strong New Zealand historical builder. This should provide enough headroom above 120 while further improving macro-region and country coverage.