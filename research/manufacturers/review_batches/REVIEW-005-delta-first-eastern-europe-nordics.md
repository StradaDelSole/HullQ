# SLICE-0019 manufacturer review batch 005 — delta-first Eastern Europe / Nordics

**Scope:** bounded independent review of 8 recovered `needs_review` records: 4 remaining Germanic/Eastern-Europe cases plus 4 Nordic cases.

**Method:** strict evidence-delta review. The already-preserved Claude evidence set was inspected first. New web research was used only where a concrete unresolved claim materially affected manufacturer/yard eligibility, current sailing-production status, or historical/current identity separation. No `registry.json` or canonical HullQ entity is modified by this note.

**Additional targeted web checks in this batch:**

1. Northman / Maxus — current official sailing-yacht range and manufacturer/brand relationship.
2. Balt-Yacht — whether the yard actually has series-sailboat production evidence rather than merely generic yacht/motorboat activity.
3. Schöchl Yachtbau / SUNBEAM Watersports — current official yard/legal entity and sailing-yacht range.
4. Finngulf Yachts — direct retrieval of the official history page and current-site freshness.

The remaining four records (AVAR-YACHT, Najad, Maxi, Nauticat) required no broad new research because the preserved evidence already supports adjudication once unrelated model-count/current-status uncertainty is separated from manufacturer eligibility.

## 1. Northman / Maxus Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as an active Polish manufacturer/yard; Maxus remains the sailing-yacht brand of the Northman shipyard.

- Claude had already retained the official Northman site, but the record remained `needs_review` because the manufacturer-vs-brand relationship and sailing-only product evidence were not sufficiently explicit.
- The current official Northman site resolves this directly: it calls Northman a yacht shipyard and states that it is the exclusive manufacturer of Maxus sailing yachts.
- The site currently exposes a multi-model sailing range including Maxus 31, 35, 34, 26, 24 EVO and 30, while Northman/Nexus are separately presented as motor-yacht lines.
- The official history states production activity began in 1995 and the Maxus sailing-yacht brand was launched in 2007 with the Maxus 33.
- Recommended modeling: `entity_kind=[manufacturer, yard]` for Northman; Maxus as a related sailing-yacht brand rather than a separate legal manufacturer.

Official sources:
- https://northman.pl/en/
- https://northman.pl/en/about-us/
- https://northman.pl/en/maxus-34/

## 2. Balt-Yacht

**Provisional decision:** `PROMOTE TO VERIFIED` as an active Polish production yard/manufacturer with a **historical series-sailboat production role**; do not imply that its current own-brand range is primarily sailing boats.

- The recovered record correctly identified Balt-Yacht as a substantial GRP production yard but did not adequately establish sailboat relevance because the current range is heavily motorboat/houseboat oriented.
- The current official company history confirms long-term production work for Jeanneau and X-Yachts.
- A historical article preserved on Balt-Yacht's own domain states specifically that the yard built **X-35 and X-45** sailing yachts for X-Yachts, approximately sixty units, and also marketed its own **Balt 27** sailboat.
- This is sufficient to qualify the physical yard under SLICE-0019's rule that a yard may build series sailboats sold under another brand.
- Current official material now describes Balt-Yacht primarily as a premium motorboat/houseboat producer. Therefore the sailboat-manufacturing role should be treated as historical unless later evidence establishes a current sailing contract.
- Recommended: company/yard `status=active`; sailboat-production role historical; preserve X-Yachts/Jeanneau contract relationships explicitly.

Official/current and official-domain historical sources:
- https://baltyacht.pl/en/about-us-nowa/
- https://baltyacht.pl/en/producent-jachtow-i-lodzi-z-laminatu/
- https://baltyacht.pl/wp-content/uploads/2016/10/Balt27artikelindeWaterkampioen.pdf

## 3. Schöchl Yachtbau / SUNBEAM Watersports GmbH

**Provisional decision:** `PROMOTE TO VERIFIED` as an active Austrian sailing-yacht manufacturer/yard.

- The recovered record's only real blocker was the lack of a directly confirmed current official site/legal-manufacturer surface.
- The current official SUNBEAM site identifies **Sunbeam Watersports GmbH**, Mattsee, Austria, and explicitly describes the company as the shipyard behind SUNBEAM Yachts.
- The official site states that the yard develops, manufactures and builds sailing yachts and currently lists SUNBEAM 22.1, 28.1, 29.1/29.1 GT and 32.1.
- This removes the need to rely on Wikipedia for present operational status.
- Historical 1961/earlier Schöchl chronology may remain separately sourced; it is no longer a blocker for current manufacturer verification.
- Recommended relationship handling: former `Schöchl Yachtbau GmbH` / current `Sunbeam Watersports GmbH` legal-name transition retained explicitly rather than flattened as an alias without chronology.

Official sources:
- https://www.sunbeam-yachts.com/en/
- https://www.sunbeam-yachts.com/en/shipyard/
- https://www.sunbeam-yachts.com/en/yachts/

## 4. AVAR-YACHT, s.r.o.

**Provisional decision:** `PROMOTE TO VERIFIED` as an active Czech repeated-model sailing-yacht manufacturer; preserve the 1984-vs-2009 chronology distinction.

- The preserved official AVAR-YACHT site already lists seven named sailing-yacht models (A45, A35, A34, A32, A29, A25, A23/Costa) and offers boats at defined completion stages from hull to finished yacht.
- This is sufficient evidence of a repeated model family and manufacturer role for the bounded research registry, including small specialist/build-to-order production.
- The difference between a claimed tradition/activity dating to 1984 and the current `s.r.o.` legal entity registration in 2009 is a corporate-continuity issue, not a manufacturer-eligibility failure.
- Recommended: verified manufacturer; use an uncertainty-preserving/estimated production start for the earlier trading/manufacturing lineage, while recording 2009 separately as the current legal entity registration if retained.
- Do not invent exact legal continuity between 1984 and 2009.

Preserved official source is sufficient:
- https://www.avaryacht.cz/lode-a-cluny/plachetnice/

## 5. Najad Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as an active Swedish manufacturer/yard; remove the unrelated Maxi production-count ambiguity from the verification decision.

- The preserved official Najad site already establishes current production from Orust and a current numbered yacht range.
- A Najad-hosted 2022 press release describing the Arcona/Najad separation states that Najad builds sailing yachts on Orust, that the first Najad was produced in 1971, and that the current range consists of five models from 39–57 ft.
- The checkpoint's concern came from a secondary statement combining Najad and Maxi output. That statement is not required to verify Najad and should not be allowed to contaminate the identity/model-yield fields.
- Recommended: verified active manufacturer/yard; keep any cumulative figure that conflates Najad and Maxi out of the Najad-only model-yield field unless independently separable.
- Preserve the 2011 bankruptcy/acquisition and the 2018–2022 Arcona relationship explicitly.

Preserved/official source set is sufficient; useful Najad-hosted source:
- https://najad.se/wp-content/uploads/2022/06/press-release_arcona-and-najad_final_.pdf

## 6. Maxi Yachts

**Provisional decision:** `VERIFY AS BRAND / PRODUCTION-LINE RELATIONSHIP CONTEXT`; **do not count toward the >=120 manufacturer/yard floor** unless a distinct Maxi manufacturing-yard entity is independently established.

- The preserved evidence clearly establishes Maxi as a major Swedish production sailing-yacht marque with very large series output and a long model family.
- It also establishes that at least the Maxi 77 was physically built by **Mölnlycke Marin**, and later Maxi production/brand ownership moved through other entities including Delphia.
- Therefore the checkpoint's `[brand, manufacturer]` role is too broad unless a specific Maxi legal/yard manufacturer identity is shown.
- Recommended: `entity_kind=[brand]` (or brand relationship context) for this research record; physical builder relationships recorded separately; current production status may remain historical/acquired/unknown depending on later brand evidence.
- The 13,000–16,000 cumulative figure may remain an explicitly approximate **brand-output** figure, not a yard-output figure.
- This record is useful for model discovery but must not inflate the manufacturer/yard breadth floor.

Preserved sources are sufficient; no new web research required.

## 7. Nauticat Yachts / Siltala Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as the historical Finnish manufacturer/yard for the 1961–2018 lineage; keep the 2022 Latvian revival as a distinct successor.

- The checkpoint already contains sufficient evidence for a real Finnish series manufacturer: Siltala/Nauticat built more than 3,000 yachts across multiple models over more than five decades.
- The original Finnish Nauticat Yachts Oy bankruptcy in 2018 is a meaningful end to that manufacturing entity/yard lineage.
- The current `NAUTICAT YACHTS SIA` production operation in Latvia is a later revival/successor and must not be silently treated as the same Finnish manufacturer.
- The uncertain 2005 naming/renaming date is secondary and does not prevent verification of the historical manufacturer.
- Recommended: verified Finnish historical manufacturer/yard, 1961–2018; explicit successor/revival relationship to the Latvian entity from 2022.

Preserved sources are sufficient; no new web research required.

## 8. Finngulf Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as a Finnish series-sailboat manufacturer/yard; set **current operational status to `unknown`** rather than interpreting the surviving website as proof of 2026 activity.

- The original Claude pass could not directly fetch Finngulf's official history page; this was the main reason for `needs_review`.
- The official page is now directly retrievable and states that Finngulf Yachts Ltd was established in **1981 by Stig Nordblad**, began with the Finngulf 34 and moved into repeated production after the first orders.
- The official history documents the FG39/391's 23-year production run, subcontract production under the Inferno brand, cooperation with Saare Paat in Estonia, and states that **900 yachts** were built by the Finngulf yard.
- This is strong primary evidence for manufacturer/yard eligibility.
- The website's latest surfaced news is from 2014–2015 despite a `Present Day` section describing future model updates. That is not sufficient evidence of active 2026 production.
- Recommended: verified manufacturer/yard; historical series start 1981; current status `unknown` pending a fresh operational source.

Official sources:
- https://www.finngulf.fi/en/oy-finngulf-tresjord-ab/history
- https://www.finngulf.fi/en/

## Batch outcome

Of 8 reviewed records:

### Verified manufacturer/yard-floor candidates after correction

- **Northman** — verified active Polish manufacturer/yard; Maxus is its sailing brand.
- **Balt-Yacht** — verified active Polish production yard with historical series-sailboat/contract-builder role; current own range mainly power/houseboat.
- **Schöchl / SUNBEAM Watersports** — verified active Austrian sailing-yacht manufacturer/yard.
- **AVAR-YACHT** — verified active Czech repeated-model sailing-yacht manufacturer; legal chronology remains uncertainty-preserving.
- **Najad Yachts** — verified active Swedish manufacturer/yard; Maxi ambiguity removed from Najad-specific evidence.
- **Nauticat / Siltala** — verified historical Finnish manufacturer/yard, distinct from the later Latvian successor.
- **Finngulf Yachts** — verified Finnish manufacturer/yard from official history; current 2026 operational status remains unknown.

### Verified relationship-context record, NOT independently counted toward manufacturer/yard floor

- **Maxi Yachts** — verified major production sailing brand/model lineage, but physical builders are separate entities; do not count as a manufacturer/yard record without a distinct yard identity.

## Research-efficiency note

This batch again used the checkpoint as an evidence cache rather than repeating Claude's work. Four records required no new web research. The additional checks were limited to specific open questions and materially strengthened or corrected the existing records: Northman's brand/yard separation, Balt-Yacht's real X-Yachts/own-sailboat production history, SUNBEAM's current legal/yard identity, and Finngulf's directly retrievable official production history.

No registry counts should be mechanically changed from this note alone. Final application to `registry.json`, stable research IDs, deduplication, exact manufacturer/yard-floor counting and report totals remain deferred until the bounded review batches are complete.