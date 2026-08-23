# SLICE-0019 manufacturer review batch 003 — delta-first UK / France

**Scope:** bounded independent review of 8 recovered `needs_review` records: the 2 remaining UK/Ireland cases plus 6 France/Western-Europe cases.

**Method:** strict evidence-delta review. The already-preserved Claude evidence set was inspected first. New web research was used only where a concrete unresolved claim materially affected identity, manufacturer/yard eligibility, or current-status modeling. No `registry.json` or canonical HullQ entity is modified by this note.

**Additional targeted web checks in this batch:**

1. Cornish Crabbers — whether post-2024 production actually resumed and what the current market-facing relationship is.
2. Fountaine Pajot — official history / current production confirmation.
3. Lagoon — official history, current status and whether it should count as a manufacturer/yard-floor entity or brand context.
4. Wauquiez — current official production status.
5. Gibert Marine / Gib'Sea — stronger historical manufacturer evidence beyond the recovered brokerage-history source.
6. Kelt Marine — resolution of the recovered 1985-vs-2009 closure conflict by separating Kelt sailboat-brand production from later activity of the physical Vannes yard.

## 1. Discovery Yachts / Discovery Shipyard

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical/defunct series-sailboat manufacturer/yard for the 1998–2021 production lineage.

- The preserved Berthon history already establishes the Discovery 55/57/58/67 and catamaran series, the Southampton production operation and the 2021 failure/closure of Discovery Shipyard.
- Berthon's later market commentary explicitly states that Discovery Shipyard finally stopped at the end of 2021. This is sufficient to establish the historical manufacturer's series-production eligibility and end-state.
- The existence of later Companies House entities with similar names does not invalidate verification of the historical yard and MUST NOT be silently treated as legal continuity.
- Recommended: retain the 1998–2021 production era for the researched historical manufacturer/yard; `status=defunct` for that production entity/lineage; preserve the 2024 similarly named legal entity as unresolved relationship context only unless explicit continuity evidence appears later.

Existing preserved sources are sufficient; no broad new research was required.

## 2. Cornish Crabbers

**Provisional decision:** `PROMOTE TO VERIFIED` for the historical manufacturer/brand lineage, while correcting the post-2024 status model; current physical manufacturer/legal producer remains unresolved.

- The preserved record already establishes Cornish Crabbers as a genuine long-running series sailboat producer beginning in 1974 and documents the 2024 insolvency event.
- Current Blue Lagoon Marine material materially changes the recovered `end_year=2024` interpretation: Blue Lagoon advertises brand-new Cornish Crabbers for the 2025 season, including a Crabber 24 explicitly marked `In Build`, and states that new boat orders are being accepted.
- Blue Lagoon describes itself as the **exclusive Cornish Crabbers representative**, not unambiguously as the physical manufacturer. Therefore HullQ should not silently relabel Blue Lagoon Marine as the yard/building legal entity without evidence.
- Recommended research modeling:
  - historical Cornish Crabbers manufacturer/brand lineage: verified;
  - 2024 insolvency/asset-transfer event: explicit relationship/transition;
  - current Cornish Crabbers brand: demonstrably active in the market with new-build orders;
  - current physical manufacturer/legal producer: `unknown` until independently identified;
  - do not encode 2024 as the final end of all Cornish Crabbers sailboat production.

New current sources:
- https://www.bluelagoonmarine.co.uk/new-boats-for-sale/cornish-crabbers-crabber-24
- https://www.bluelagoonmarine.co.uk/wp-content/uploads/2024/11/2025-Cornish_Crabbers-Crabber_24.pdf

## 3. Fountaine Pajot

**Provisional decision:** `PROMOTE TO VERIFIED` as an active series-sailboat manufacturer/yard and count as a manufacturer/yard-floor candidate.

- Claude already retained the current official Fountaine Pajot site, but had left the record `needs_review` because a stable history page was not found during the original pass.
- The current official history/expertise surface now explicitly states creation of Fountaine Pajot in 1976 by Jean-François Fountaine, Yves Pajot, Daniel Givon and Rémi Tristan, the 1978 Aigrefeuille production site, and the 1983 launch of the cruising-catamaran range.
- The official current sailing-catamaran site states that Fountaine Pajot designs and builds production catamarans and exposes a current multi-model range.
- This closes the only material verification gap in the recovered record.
- Do not mix group-level totals for Fountaine Pajot + Dufour with a Fountaine-Pajot-only model-yield figure unless explicitly labeled.

Authoritative current sources:
- https://www.fountaine-pajot.com/en/fountaine-pajot-half-a-century-of-history-expertise-and-ambition/
- https://www.catamarans-fountaine-pajot.com/en/

## 4. Lagoon

**Provisional decision:** `PROMOTE TO VERIFIED` as active **brand / production-program relationship context**, but do **not** count it toward the >=120 manufacturer/yard floor unless a later identity model explicitly establishes Lagoon itself as the relevant yard/legal manufacturer rather than the Groupe Bénéteau/CNB production structure.

- The recovered record correctly identified Lagoon's origin in Jeanneau Technologies Avancées and its relationship to CNB/Groupe Bénéteau, but lacked an independently fetched official history surface.
- Lagoon's current official site now directly confirms:
  - origin in 1984 inside Jeanneau's competition department/JTA;
  - continued active Lagoon production;
  - 7,000 Lagoon catamarans by 2024;
  - current status as a Groupe Beneteau brand.
- The same official surface uses manufacturer-style language (`we construct our boats`, French shipyard), but the preserved source set separately identifies CNB / Groupe Bénéteau production facilities. To preserve HullQ's brand-vs-yard semantic discipline, Lagoon should remain a verified production brand/context record rather than being automatically counted as an independent manufacturer/yard entity.

Official sources:
- https://www.catamarans-lagoon.com/dna
- https://www.catamarans-lagoon.com/lagoon-40-years

## 5. CNB (Construction Navale Bordeaux)

**Provisional decision:** `PROMOTE TO VERIFIED` as a manufacturer/yard/legal-organization record and count as a manufacturer/yard-floor candidate, with brand relationships kept separate.

- Claude's preserved Groupe Bénéteau press sources already establish CNB as the Bordeaux manufacturing entity/yard and document its role in the Lagoon multihull program.
- SLICE-0019 explicitly allows yards that build boats sold under other brands; therefore CNB does not need to be a high-volume consumer-facing brand in its own right to qualify.
- The fact that CNB-branded large yachts are semi-custom/small-series does not disqualify the yard where the evidence also supports genuine repeated production work and production for distinct series brands.
- Recommended: `entity_kind` may retain manufacturer/yard/legal_organization; make Lagoon/Excess/CNB-brand relationships explicit and do not collapse them into one identity.
- No new web research was needed for manufacturer/yard eligibility; the retained official Groupe Bénéteau evidence is sufficient.

## 6. Wauquiez

**Provisional decision:** `PROMOTE TO VERIFIED` as an active series/small-series sailboat manufacturer/yard and count toward the manufacturer/yard floor.

- The recovered record's principal unresolved issue was current operational status because its attempted official history URL returned 404.
- The current official Wauquiez site is live in 2026, identifies itself as a French shipyard/manufacturer, exposes an active sailing-yacht range and current Wauquiez 55 production/news.
- 2026 official news specifically discusses Wauquiez 55 hulls #1 and #2 and Cannes Yachting Festival display, providing strong evidence of real current production rather than a stale heritage site.
- Historical exact founding chronology may remain estimated/secondary where necessary; it no longer blocks manufacturer verification.

Official current sources:
- https://www.wauquiez.com/
- https://www.wauquiez.com/2026/

## 7. Gibert Marine / Gib'Sea

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical series-sailboat manufacturer/yard; keep the later Gib'Sea brand-under-Dufour period as relationship context rather than extending the original Gibert Marine legal/yard identity automatically to 2009.

- The recovered evidence already described Gibert Marine as a substantial French production builder, but relied mainly on specialist/brokerage history and therefore remained `needs_review`.
- A French government archive materially strengthens the manufacturer identity: an archived vessel-registration/construction dossier explicitly records a 1987 `Gib'sea 372 Master` with **Constructeur: Gibert Marine**.
- Independent specialist histories consistently place Gibert Marine in Marans, identify it as a production yacht builder, and document acquisition by Dufour in the mid-1990s.
- The key semantic correction is to avoid conflating:
  1. the original **Gibert Marine** manufacturer/yard; and
  2. later continued use of the **Gib'Sea** brand by Dufour.
- Recommended: verify the original manufacturer entity with an end/transition around the Dufour acquisition (1996/1997 uncertainty retained); represent post-acquisition Gib'Sea production as brand/owner relationship context. Do not use `2009` as if Gibert Marine itself necessarily remained the same manufacturer entity until then.

New stronger evidence:
- French government archive: https://www.archives.developpement-durable.gouv.fr/IMG/pdf/19960047.pdf

Useful secondary corroboration:
- https://www.yachtsnet.co.uk/archives/gibsea-43/gibsea-43.htm
- preserved Murray Yacht Sales history

SailboatData remains reference-only and is not used as production evidence.

## 8. Kelt Marine

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical series-sailboat manufacturer/yard, with a corrected production-era model that separates Kelt sailboat production from the later life of the Vannes physical yard/business.

- Claude correctly identified a real conflict: some sources said Kelt ended around 1985, while others extended the shipyard story to 2009 and attributed 4,000+ boats to the longer period.
- The conflict becomes coherent once the identities/activities are separated:
  - Kelt Marine was founded by Gilles Le Baud in Vannes in 1974 and produced the Kelt sailboat range through the mid-1980s;
  - Kirié took over Kelt in 1986 and retained/rebadged several Kelt models under the Feeling name;
  - later activity at the Vannes yard continued under other ownership/products, including powerboats, until much later.
- A dedicated Kelt owner-club history states Kelt Marine produced sailboats from 1974–1986 and that no new boats under the Kelt name were produced after 1989; a detailed French sailing-history source likewise places the Kirié takeover in 1986 and describes the subsequent Feeling rebranding.
- Therefore the 2009 date must NOT be used as the end of the Kelt sailboat manufacturer/brand production era merely because the physical yard/business site continued in other forms.
- Recommended: verified historical manufacturer/yard; start 1974; transition/acquisition 1986; Kelt-branded residual production/continuation may extend to approximately 1987–1989 depending on model/license evidence; later yard activity represented separately.

Sources:
- https://kelt-club.nl/over/kelt-marine/
- https://mersetbateaux.com/histoire-chantier-kelt/

Reference-only SailboatData was not used to resolve the production-era decision.

## Batch outcome

Of 8 reviewed records:

### Verified manufacturer/yard-floor candidates after correction

- **Discovery Yachts / Discovery Shipyard** — verified historical/defunct manufacturer/yard, 1998–2021 production lineage.
- **Cornish Crabbers historical manufacturer lineage** — verified historical production manufacturer; current new-build brand is active, but present physical producer remains unresolved.
- **Fountaine Pajot** — verified active manufacturer/yard.
- **CNB (Construction Navale Bordeaux)** — verified manufacturer/yard/legal organization with distinct production-brand relationships.
- **Wauquiez** — verified active manufacturer/yard.
- **Gibert Marine** — verified historical manufacturer/yard; separate from later Dufour-owned Gib'Sea brand period.
- **Kelt Marine** — verified historical manufacturer/yard; Kelt sailboat-production era separated from later physical-yard activity.

### Verified relationship-context record, not independently counted toward manufacturer/yard floor

- **Lagoon** — verified active Groupe Bénéteau production brand with well-supported history and production evidence; keep distinct from CNB/Groupe Bénéteau yard/legal-manufacturer identity.

## Research-efficiency note

This batch again confirms that the checkpoint material should be treated as an evidence cache, not as a list of prompts to research from scratch. The majority of the eligibility decisions were already supportable from the preserved evidence once exact-date/current-status uncertainty was allowed to remain explicit. New web checks were limited to gaps that could materially alter identity or status, and several of those checks corrected rather than merely repeated Claude's original conclusions.

No registry counts should be mechanically changed from this note alone. Final application to `registry.json`, stable research IDs, deduplication, exact manufacturer/yard-floor counting and report totals remain deferred until the bounded review batches are complete.