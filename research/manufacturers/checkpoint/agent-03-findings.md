# SLICE-0019 checkpoint findings — France, Belgium, Netherlands

Workstream status: **fully recovered** (24 records: 12 verified, 10 needs_review, 2 excluded).
Raw structured JSON preserved losslessly at `research/manufacturers/checkpoint/raw/batch_c_france_benelux.json`.
This markdown is a mechanical transcription of that JSON for human readability; the JSON file is the authoritative copy.

### 1. Bénéteau

- Aliases: Beneteau, Chantiers Bénéteau
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1884 end=None basis=exact
- Relationships:
  - other -> Groupe Bénéteau: Bénéteau is the founding shipyard/brand and namesake of the publicly listed Groupe Bénéteau, which separately owns Jeanneau, Lagoon, CNB and other distinct brands; the group is not the same entity as this yard/brand. (source: https://www.beneteau.com/history)
  - other -> CNB (Construction Navale Bordeaux): Official history page states CNB acquisition in 1992 was Bénéteau's first external growth acquisition. (source: https://www.beneteau.com/history)
  - other -> Jeanneau: Official history describes 1995 as 'the coming together of two Vendée families' (Bénéteau and Jeanneau) forming what became Groupe Bénéteau; Jeanneau remains a distinct brand/manufacturer. (source: https://www.beneteau.com/history)
- Series-production evidence: Official company history documents transition from wooden fishing-boat construction to polyester recreational sailboats in 1963-64 (Guppy, Flétan, Ombrine models), continuing through current First/Oceanis lines; widely reported (secondary sources) as producing over 10,000 hulls/year across the group.
- Official current site: https://www.beneteau.com/
- Official heritage archive: https://www.beneteau.com/history
- Other archive sources: https://en.wikipedia.org/wiki/Beneteau
- Sources:
  - [official_heritage_archive] History | BENETEAU — https://www.beneteau.com/history (retrieved 2026-08-22T00:00:00Z)
  - [specialist_secondary] Beneteau - Wikipedia — https://en.wikipedia.org/wiki/Beneteau (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.beneteau.com/history: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://en.wikipedia.org/wiki/Beneteau: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=Secondary sources describe Bénéteau/Groupe Bénéteau as the world's largest producer of pleasure boats by volume; no single authoritative cumulative model count for the Bénéteau brand alone was found.
- Review status: **verified**
- Ambiguity notes: Founded 1884 as a wooden fishing-trawler builder in Saint-Gilles-Croix-de-Vie; pivoted to fiberglass recreational sailboats in the 1960s under third-generation leadership (André Bénéteau, Annette Bénéteau Roux). This record is for the Bénéteau brand/yard itself, kept distinct from the parent 'Groupe Bénéteau' holding company per the semantic rule that a manufacturer/brand and its owning group are separate entities.

### 2. Jeanneau

- Aliases: Chantiers Jeanneau, Jeanneau Technologies Avancées (JTA, racing/multihull division)
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1957 end=None basis=exact
- Relationships:
  - brand_owned_by -> Groupe Bénéteau: Official Jeanneau history states 'Chantiers Jeanneau joins Bénéteau' in 1995, the same year Lagoon joined the group. (source: https://www.jeanneau.com/en-us/jeanneau/history)
  - other -> Lagoon: Lagoon originated in 1984 as JTA, Jeanneau's multihull/racing division, before later being spun into CNB. (source: https://en.wikipedia.org/wiki/Lagoon_catamaran)
- Series-production evidence: Official history documents first fiberglass hull (1957-58), first sailboat (Alizé, 1964), and the Sangria (1970) reaching 3,000 units sold; company describes itself as operating the world's largest series-boat production shipyard footprint (40 hectares in Les Herbiers).
- Official current site: https://www.jeanneau.com/
- Official heritage archive: https://www.jeanneau.com/en-us/jeanneau/history
- Other archive sources: https://en.wikipedia.org/wiki/Jeanneau
- Sources:
  - [official_heritage_archive] JEANNEAU, the History of a Shipyard — https://www.jeanneau.com/en-us/jeanneau/history (retrieved 2026-08-22T00:00:00Z)
  - [specialist_secondary] Jeanneau - Wikipedia — https://en.wikipedia.org/wiki/Jeanneau (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.jeanneau.com/en-us/jeanneau/history: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://en.wikipedia.org/wiki/Jeanneau: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No single authoritative cumulative hull count found; Sangria alone reported at ~3,000 units by 1970s per official history.
- Review status: **verified**
- Ambiguity notes: Founded by Henri (Henry) Jeanneau in 1957 in Les Herbiers as a powerboat/runabout builder; first sailboat 1964. Kept distinct from Groupe Bénéteau (owner since 1995) and from Lagoon (a separate brand that originated as Jeanneau's multihull division but is now organized under CNB).

### 3. Dufour Yachts

- Aliases: Le Stratifié Industriel, Dufour
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1964 end=None basis=exact
- Relationships:
  - acquired_by -> Fountaine Pajot: Fountaine Pajot purchased Dufour Yachts in 2018; Dufour continues as a separate brand within the resulting group. (source: https://en.wikipedia.org/wiki/Dufour_Yachts)
  - other -> Gibert Marine / Gib'Sea: Dufour acquired Gibert Marine (Gib'Sea) in 1996, becoming France's second-largest sailboat builder at the time; Gib'Sea production continued as a separate brand until 2009. (source: https://murrayyachtsales.com/a-brief-history-of-gibsea/)
  - other -> Nautitech: Nautitech was created in 1994 in partnership with / under the Dufour Yachts Group before being sold off independently in 2002. (source: https://www.nautitechcatamarans.com/en/brand)
- Series-production evidence: Founded to build the transportable 6.5m 'Sylphe' design in 1964 (production entity originally named Stratifié Industriel); official history credits Michel Dufour with pioneering polyester, balsa-sandwich construction and structural liners for series-built yachts; brand still in active current production today.
- Official current site: https://www.dufour-yachts.com/
- Official heritage archive: https://www.dufour-yachts.com/en/our-expertise/our-history/
- Other archive sources: https://en.wikipedia.org/wiki/Dufour_Yachts
- Sources:
  - [specialist_secondary] Dufour Yachts - Wikipedia — https://en.wikipedia.org/wiki/Dufour_Yachts (retrieved 2026-08-22T00:00:00Z)
  - [official_heritage_archive] Dufour History & Sailing Heritage Since 1964 — https://www.dufour-yachts.com/en/our-expertise/our-history/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://en.wikipedia.org/wiki/Dufour_Yachts: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
  - https://www.dufour-yachts.com/en/our-expertise/our-history/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No authoritative cumulative hull count found.
- Review status: **verified**
- Ambiguity notes: Founded by Michel Dufour in 1964 under the original name 'Stratifié Industriel' / 'Le Stratifié Industriel'; the Dufour brand also briefly owned Gibert Marine's Gib'Sea line (1996-2009) and co-founded Nautitech (1994-2002) as separate brands, illustrating the manufacturer/brand distinction the registry must preserve.

### 4. Amel (Chantiers Amel)

- Aliases: Chantiers Amel, ARPIN (Ateliers Rochelais de Polyester Industriel et Naval, predecessor workshop taken over by Henri Amel)
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1964 end=None basis=exact
- Relationships:
  - predecessor -> ARPIN (Ateliers Rochelais de Polyester Industriel et Naval): Henri Amel took over the ARPIN shipyard workshop in La Rochelle in 1964, from which Chantiers Amel developed; a fire destroyed the original ARPIN workshops in 1968, prompting the move to a new Périgny facility in 1969. (source: https://amel.fr/en/the-amel-story/)
- Series-production evidence: Official heritage page documents continuous series production of ocean-cruising monohulls from the 1960s onward (models historically named after winds/islands, later simply 'AMEL' after founder's 2005 death); secondary sources report over 2,000 yachts produced.
- Official current site: https://amel.fr/
- Official heritage archive: https://amel.fr/en/the-amel-story/
- Other archive sources: https://en.wikipedia.org/wiki/Amel_Yachts
- Sources:
  - [official_heritage_archive] The AMEL story - AMEL — https://amel.fr/en/the-amel-story/ (retrieved 2026-08-22T00:00:00Z)
  - [specialist_secondary] Amel Yachts - Wikipedia — https://en.wikipedia.org/wiki/Amel_Yachts (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://amel.fr/en/the-amel-story/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://en.wikipedia.org/wiki/Amel_Yachts: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
- Model yield estimate: value=2000 basis=estimated notes=Secondary/official-adjacent sources state 'over 2,000 yachts' produced across the shipyard's history; not independently itemized by model.
- Review status: **verified**
- Ambiguity notes: Founder Henri Amel (born Henri Tonet) took over the ARPIN workshop in La Rochelle in 1964; some secondary sources cite 1965 as the formal shipyard founding date. Located in Périgny (La Rochelle) since 1969.

### 5. Alubat

- Aliases: Chantier Alubat, Ovni (product line name sometimes used loosely for the yard)
- Entity kind: manufacturer, yard
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1973 end=None basis=exact
- Relationships:
  - other -> Employee/local investor consortium: Reported acquisition of the shipyard in 2014 by a group described as fourteen Vendée-based manufacturers, and a further management takeover in October 2023 led by Luc Jurien. (source: https://www.alubat.com/about-alubat/)
- Series-production evidence: Founded by Yves Roucher specifically to build series aluminum sailboats; official site documents the OVNI 25 prototype (1974) and OVNI 28 (1978) as founding the OVNI range, with over 1,600 aluminum boats built to date across OVNI and CIGALE lines.
- Official current site: https://www.alubat.com/
- Official heritage archive: https://www.alubat.com/about-alubat/
- Sources:
  - [official_site] About Alubat - Homepage — https://www.alubat.com/about-alubat/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.alubat.com/about-alubat/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=1600 basis=estimated notes=Official site states 'over 1,600 aluminum vessels' built since 1973, not broken out by individual model.
- Review status: **verified**
- Ambiguity notes: Founder identified in secondary sources as Yves Roucher (not confirmed directly on the official site during this research pass). 'Ovni' and 'Cigale' are product-line names under the Alubat yard, not separate legal entities.

### 6. Fountaine Pajot

- Aliases: Chantiers Fountaine Pajot
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1976 end=None basis=exact
- Relationships:
  - other -> Dufour Yachts: Fountaine Pajot acquired Dufour Yachts in 2018; Dufour continues as a separate brand under the resulting group. (source: https://en.wikipedia.org/wiki/Dufour_Yachts)
- Series-production evidence: Official site states the company has been 'designers and boat builders since 1976'; founded by Jean-François Fountaine and Yves Pajot, moved to Aigrefeuille-d'Aunis in 1978, entered production cruising catamarans in 1983; secondary sources report nearly 5,000 catamarans built across 60+ models over five decades.
- Official current site: https://www.fountaine-pajot.com/en
- Official heritage archive: None
- Sources:
  - [official_site] Fountaine Pajot official site — https://www.fountaine-pajot.com/en (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.fountaine-pajot.com/en: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=5000 basis=estimated notes=Secondary sources (industry press) report 'nearly 5,000 catamarans' and '60+ models' over five decades; not confirmed on an official page during this pass.
- Review status: **needs_review**
- Ambiguity notes: Official dedicated heritage/history page could not be located at a stable URL during this research pass (404 on attempted path); founding year and founder names are corroborated by multiple secondary industry-press sources but should be re-verified against an official Fountaine Pajot history page in a follow-up pass.

### 7. Lagoon

- Aliases: Lagoon Catamarans, JTA (Jeanneau Technologies Avancées, originating division)
- Entity kind: brand, manufacturer
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1984 end=None basis=exact
- Relationships:
  - formerly_known_as -> Jeanneau Technologies Avancées (JTA): Lagoon began in 1984 as JTA, Jeanneau's multihull/racing division. (source: https://en.wikipedia.org/wiki/Lagoon_catamaran)
  - brand_owned_by -> CNB (Construction Navale Bordeaux): Jeanneau's multihull division was transferred to CNB; larger Lagoon models are built at CNB's Bordeaux facility, smaller ones at Belleville-sur-Vie. (source: https://en.wikipedia.org/wiki/Lagoon_catamaran)
  - brand_owned_by -> Groupe Bénéteau: CNB (and by extension Lagoon) came under Groupe Bénéteau ownership following Bénéteau's 1992/1995-era acquisitions. (source: https://en.wikipedia.org/wiki/Lagoon_catamaran)
- Series-production evidence: Wikipedia and industry press document a first generation of series catamarans (Lagoon 55/47/57/67) built 1987-1996, continuous model lines since, and a reported 7,000th catamaran launched in 2024.
- Official current site: https://www.cata-lagoon.com/en/
- Official heritage archive: None
- Other archive sources: https://en.wikipedia.org/wiki/Lagoon_catamaran, https://www.nautipedia.it/index.php/LAGOON_HISTORY
- Sources:
  - [specialist_secondary] Lagoon catamaran - Wikipedia — https://en.wikipedia.org/wiki/Lagoon_catamaran (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://en.wikipedia.org/wiki/Lagoon_catamaran: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
- Model yield estimate: value=7000 basis=estimated notes=Industry press reported the 7,000th Lagoon catamaran launch in 2024 (figure discovered via search summary, not independently fetched from a primary source this pass).
- Review status: **needs_review**
- Ambiguity notes: Official current site and heritage-archive URL were not independently fetched/confirmed this pass (only discovered via search); Lagoon is a brand manufactured within CNB/Groupe Bénéteau facilities rather than an independently incorporated yard, per the semantic rule distinguishing brand from yard.

### 8. Nautitech

- Aliases: Nautitech Catamarans
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1994 end=None basis=exact
- Relationships:
  - other -> Dufour Yachts Group: Official brand page states Nautitech was created in 1994 in partnership with the Dufour Yachts Group. (source: https://www.nautitechcatamarans.com/en/brand)
  - acquired_by -> Bavaria Yachts: Official page states Bavaria Yachts acquired Nautitech in 2014. (source: https://www.nautitechcatamarans.com/en/brand)
  - acquired_by -> Capital Management-Partners: Official/secondary sources indicate a further ownership change to Capital Management-Partners in 2018. (source: https://www.nautitechcatamarans.com/en/brand)
- Series-production evidence: Official brand page documents founding in Rochefort in 1994, relocation through La Rochelle (2004-2006) back to Rochefort (2008), and current output of approximately 50 catamarans/year with 150 employees.
- Official current site: https://www.nautitechcatamarans.com/
- Official heritage archive: https://www.nautitechcatamarans.com/en/brand
- Sources:
  - [official_heritage_archive] The NAUTITECH CATAMARANS brand — https://www.nautitechcatamarans.com/en/brand (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.nautitechcatamarans.com/en/brand: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative total found; current rate stated as ~50 catamarans/year.
- Review status: **verified**
- Ambiguity notes: Founder Bruno Voisard is named in secondary sources as the project lead but the official page does not itemize a single named founder; sold by Dufour to Voisard in 2002 before the 2014 Bavaria acquisition.

### 9. CNB (Construction Navale Bordeaux)

- Aliases: Construction Navale Bordeaux
- Entity kind: manufacturer, yard, legal_organization
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1987 end=None basis=exact
- Relationships:
  - brand_owned_by -> Groupe Bénéteau: CNB joined the Bénéteau Group in 1992, per Bénéteau's official history and press materials. (source: https://www.beneteau.com/history)
  - other -> Lagoon: CNB now houses development/production of the Lagoon cruising-catamaran brand as a legacy of Bénéteau's Jeanneau acquisition. (source: https://en.wikipedia.org/wiki/Lagoon_catamaran)
- Series-production evidence: Founded 1987 by Dieter Gust with partner Olivier Lafourcade; began as a custom/luxury sailing-yacht builder, joined Bénéteau Group in 1992, and pivoted toward pleasure sailing boat and catamaran series production (Lagoon, Excess) alongside continued CNB-brand semi-custom yachts.
- Official current site: https://press.beneteau-group.com/construction-navale-bordeaux.html
- Official heritage archive: None
- Sources:
  - [official_site] Construction Navale Bordeaux - Groupe Beneteau — https://press.beneteau-group.com/construction-navale-bordeaux.html (retrieved 2026-08-22T00:00:00Z)
  - [official_site] Groupe Beneteau pays tribute to Dieter Gust, founder of CNB — https://press.beneteau-group.com/news/groupe-beneteau-pays-tribute-to-dieter-gust-founder-of-construction-navale-bordeaux-cnb-and-a-key-contributor-to-the-development-of-lagoon-multihulls-58d64-49529.html (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://press.beneteau-group.com/construction-navale-bordeaux.html: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://press.beneteau-group.com/news/groupe-beneteau-pays-tribute-to-dieter-gust-founder-of-construction-navale-bordeaux-cnb-and-a-key-contributor-to-the-development-of-lagoon-multihulls-58d64-49529.html: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=CNB builds both semi-custom CNB-brand yachts and series Lagoon/Excess catamarans; no single combined figure found and mixing them would conflate distinct brands.
- Review status: **needs_review**
- Ambiguity notes: CNB is best understood as a manufacturing legal entity/yard housing multiple distinct brands (CNB yachts, Lagoon, Excess) rather than a single-brand series producer; the CNB-branded product line itself leans toward semi-custom/small-series large sailing yachts (60-100ft) rather than high-volume series production, which is why this entity kind includes 'legal_organization' and is flagged needs_review for eligibility-boundary judgment.

### 10. Wauquiez

- Aliases: Chantier Wauquiez, Chantiers Wauquiez
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: unknown
- Production era: start=1964 end=None basis=exact
- Relationships: none recorded
- Series-production evidence: Secondary/official-adjacent sources (Wauquiez company site and 'Wauquiez Forever' heritage association) document founder Henri Wauquiez producing the licensed Elizabethan 29 from a converted family tannery in Neuville-en-Ferrain from 1964, followed by the in-house Centurion 32 (1968, 380 units built), and a long subsequent run of series cruising sailboats (Pretorien, Gladiateur, Hood, Amphitrite, PS models).
- Official current site: https://www.wauquiez.com/
- Official heritage archive: None
- Other archive sources: http://www.wauquiezforever.com/WauquiezForever/en/qui-sommes-nous/, http://www.wauquiezforever.com/WauquiezForever/en/henri-wauquiez/
- Sources:
  - [class_or_owners_association] Henri Wauquiez - Wauquiez Forever — http://www.wauquiezforever.com/WauquiezForever/en/henri-wauquiez/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - http://www.wauquiezforever.com/WauquiezForever/en/henri-wauquiez/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=380 basis=exact notes=Figure of 380 units applies only to the Centurion 32 model specifically, not the whole shipyard's output.
- Review status: **needs_review**
- Ambiguity notes: Attempted fetches of both wauquiez.com's official history page and a fountaine-pajot-style history path returned HTTP 404 during this research pass; current operating status (active production vs. dormant/defunct brand) could not be confirmed directly from an official current source this pass and is marked 'unknown' pending re-verification. A dedicated 'Wauquiez Forever' heritage/appreciation association exists, which is itself circumstantial evidence the brand may not be in ordinary active production, but this was not confirmed.

### 11. Gibert Marine (Gib'Sea)

- Aliases: Gib'Sea, Gib Sea
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: defunct
- Production era: start=1972 end=2009 basis=estimated
- Relationships:
  - acquired_by -> Dufour Yachts: Dufour acquired Gibert Marine in Marans in 1996; the Gib'Sea brand continued production under Dufour ownership until the line ended in 2009. (source: https://murrayyachtsales.com/a-brief-history-of-gibsea/)
- Series-production evidence: Founded 1972 in Marans (Charente-Maritime) by Olivier Gibert; secondary source reports over five thousand boats launched across forty-one models over roughly three decades; production of the Gib'Sea line ceased in 2009.
- Official current site: None
- Official heritage archive: None
- Other archive sources: https://www.gibsea-club.net/, https://murrayyachtsales.com/a-brief-history-of-gibsea/
- Sources:
  - [specialist_secondary] A Brief History of Gib'Sea - Murray Yacht Sales — https://murrayyachtsales.com/a-brief-history-of-gibsea/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://murrayyachtsales.com/a-brief-history-of-gibsea/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=5000 basis=estimated notes='Over five thousand boats across forty-one models' per a secondary brokerage-history source; not independently confirmed on a primary/official record.
- Review status: **needs_review**
- Ambiguity notes: No official current or archival site was locatable (yard is defunct); relies on secondary brokerage/enthusiast history sources (Murray Yacht Sales, gibsea-club.net) rather than an official or class-association primary source, so flagged needs_review. Founder co-credited in one source to Olivier Gibert together with in-laws connected to Dufour; exact founder attribution should be re-verified.

### 12. Kelt (Kelt Marine)

- Aliases: Kelt Marine, Chantier Kelt
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: historical
- Production era: start=1974 end=None basis=estimated
- Relationships:
  - other -> Marine Chaufour Poncin / Kirié: One secondary source states Kelt was bought several times, including by the Marine Chaufour Poncin group, owner of the Kirié shipyards. (source: None)
- Series-production evidence: Founder Gilles Le Baud established the shipyard in Vannes (Morbihan); the Kelt 7.6 won 'Boat of the Year' in 1980 (~250 units sold that year); over 4,000 sailboats reportedly built across the shipyard's lifetime.
- Official current site: None
- Official heritage archive: None
- Other archive sources: https://www.boat-specs.com/sailing/builders/kelt, https://en.wikipedia.org/wiki/Kelt_7.6
- Sources:
  - [specialist_secondary] Kelt - Sailboat builder - Boat-Specs.com — https://www.boat-specs.com/sailing/builders/kelt (retrieved 2026-08-22T00:00:00Z)
  - [specialist_secondary] Kelt 7.6 - Wikipedia — https://en.wikipedia.org/wiki/Kelt_7.6 (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.boat-specs.com/sailing/builders/kelt: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://en.wikipedia.org/wiki/Kelt_7.6: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
- Model yield estimate: value=4000 basis=estimated notes=One secondary source states 'over 4,000 sailboats' across the shipyard's lifetime; another (boat-specs.com) states only seven models totaling far fewer units and gives a much earlier closure date. Both cannot be fully reconciled from sources gathered this pass.
- Review status: **needs_review**
- Ambiguity notes: CONFLICT NOT RESOLVED: boat-specs.com states the shipyard 'stopped activities in 1985' after ~7 models, while other secondary sources describe a 35-year run to a 2009 closure and 4,000+ boats built. Founding year is also given as both 1974 and 1976 by different sources. Recorded here as status 'historical' with an estimated era and the conflict flagged per the rule against silently resolving conflicting sources; needs a class-association or trade-press primary source to resolve.

### 13. Kirié (Feeling brand)

- Aliases: Feeling, Chantier Kirié
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: defunct
- Production era: start=1980 end=2017 basis=estimated
- Relationships:
  - acquired_by -> Alliaura Marine: Alliaura Marine took over the Kirié shipyard in 2000 and continued building Feeling yachts (7 models, 32-55ft) until 2012. (source: None)
  - acquired_by -> Privilège Marine: Kirié was integrated into Privilège Marine in 2008. (source: https://mersetbateaux.com/en/introducing-the-feeling-sailboats-from-the-kirie-shipyard/)
  - acquired_by -> Aurelius (German investment group): Aurelius acquired the operation in 2017, refocusing on Privilège catamarans; the Feeling range was discontinued shortly after. (source: https://mersetbateaux.com/en/introducing-the-feeling-sailboats-from-the-kirie-shipyard/)
- Series-production evidence: The Kirié shipyard (based in Les Sables-d'Olonne) launched the 'Feeling' range of cruising sailboats in the early 1980s; a 13.5m Feeling won the Route du Rhum standard-boat category in 1986 and a 10.9m Feeling was voted 'Boat of the Year' in 1987, evidencing an established series-production model line.
- Official current site: None
- Official heritage archive: None
- Sources:
  - [specialist_secondary] Introducing the Feeling sailboats from the Kirié shipyard — https://mersetbateaux.com/en/introducing-the-feeling-sailboats-from-the-kirie-shipyard/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://mersetbateaux.com/en/introducing-the-feeling-sailboats-from-the-kirie-shipyard/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative production figure found; only individual model award/race results located.
- Review status: **needs_review**
- Ambiguity notes: One source traces the Kirié family shipyard itself back to 1912 (as a general boatbuilder before the Feeling range existed), while the 'Feeling' series-production line specifically dates from ~1980; this record's production_era start_year (1980) reflects the series-production evidence requested rather than the older general boatbuilding founding date, which should be re-verified and possibly split into a predecessor relationship in a follow-up pass. Relies only on a single specialist secondary source (mersetbateaux.com); an official Privilège Marine or class-association source was not located this pass.

### 14. Fora Marine (RM Yachts)

- Aliases: RM Yachts, Sysba Marine (disputed alternate origin name, unresolved)
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1980 end=None basis=estimated
- Relationships:
  - acquired_by -> Grand Large Yachting: Grand Large Yachting acquired RM Yachts out of Fora Marine's 2019 receivership in 2020. (source: https://www.yachtingart.com/2019/12/sailing-the-french-shipyard-fora-marine-rm-yachts-in-the-storm.html)
- Series-production evidence: La Rochelle-based yard building a continuous series of fast, light-displacement epoxy-plywood cruising sailboats (RM design line) since founding, exclusively designed by naval architect Marc Lombard for over two decades per secondary sources.
- Official current site: https://www.grandlargeyachting.com/
- Official heritage archive: None
- Other archive sources: https://www.sailboat-cruising.com/RM-Sailboats.html
- Sources:
  - [specialist_secondary] The French shipyard Fora Marine RM Yachts in the storm — https://www.yachtingart.com/2019/12/sailing-the-french-shipyard-fora-marine-rm-yachts-in-the-storm.html (retrieved 2026-08-22T00:00:00Z)
  - [official_site] About us - Grand Large Yachting — https://www.grandlargeyachting.com/en/about-us/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.yachtingart.com/2019/12/sailing-the-french-shipyard-fora-marine-rm-yachts-in-the-storm.html: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://www.grandlargeyachting.com/en/about-us/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative figure found; described in secondary sources as 'small-series, quality builds'.
- Review status: **needs_review**
- Ambiguity notes: CONFLICT NOT RESOLVED: sources disagree on the shipyard's founder and origin name/date — one secondary source credits Martin Lepoutre founding 'Fora Marine' in the 1980s in La Rochelle, another states the yard was founded in 1989 by Jean-Claude Audrey under the original name 'Sysba Marine'. Both accounts agree on the La Rochelle location, the Marc Lombard design partnership, the 2016 Lepoutre sale, the 2019 receivership, and the 2020 Grand Large Yachting acquisition. Founding year/founder recorded as estimated pending resolution.

### 15. Pogo Structures

- Aliases: none recorded
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1987 end=None basis=exact
- Relationships: none recorded
- Series-production evidence: Official site documents founding by Christian Bouroullec in 1987 (Quimper, relocated to Combrit Sainte-Marine in 1990), first production boat Pogo 6.50 launched 1995, generalized vacuum-infusion construction from ~2004, and over 300 Mini 6.50/Class40 racing-cruising yachts built to date.
- Official current site: https://www.pogostructures.com/
- Official heritage archive: https://www.pogostructures.com/le-chantier-structures/?lang=en
- Other archive sources: https://en.wikipedia.org/wiki/Pogo_Structures
- Sources:
  - [official_heritage_archive] Le chantier naval - POGO STRUCTURES — https://www.pogostructures.com/le-chantier-structures/?lang=en (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.pogostructures.com/le-chantier-structures/?lang=en: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=300 basis=estimated notes=Official site states 'over 300' Mini 6.50 and Class40 yachts built; broader cruising-line totals not separately given.
- Review status: **verified**
- Ambiguity notes: None

### 16. JPK Composites

- Aliases: none recorded
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1992 end=None basis=exact
- Relationships: none recorded
- Series-production evidence: Official site documents founding by Jean-Pierre Kelbert in 1992 (initially windsurf boards), pivot into sailboat manufacturing in 2002-2003 with the JPK 960 (naval architect Jacques Valer), and a continuous subsequent model series (JPK 1010, 38 FC, 1080, 45 FC, 1180, 1030, 39 FC, 1050) through 2025; based in Larmor-Plage, ~50 employees.
- Official current site: https://www.jpk.fr/en/
- Official heritage archive: https://www.jpk.fr/en/le-chantier/histoire-du-chantier/
- Sources:
  - [official_heritage_archive] Histoire du chantier - JPK Composites — https://www.jpk.fr/en/le-chantier/histoire-du-chantier/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.jpk.fr/en/le-chantier/histoire-du-chantier/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=250 basis=estimated notes=A separate secondary source (boatindustry.com, discovered via search but not independently fetched this pass) states 'nearly 250 units' launched since sailboat production began; not confirmed on the official history page itself.
- Review status: **verified**
- Ambiguity notes: None

### 17. Allures Yachting

- Aliases: none recorded
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=2003 end=None basis=exact
- Relationships:
  - other -> Garcia Yachts: Allures took over Garcia Yachts in 2010, gaining aluminum-fabrication infrastructure; Garcia continues as a separate brand. (source: https://www.allures.com/en/spirit-allures/history)
  - other -> Grand Large Yachting: Allures is described as the founding shipyard of the Grand Large Yachting group (founded 2003 by the same two founders, Xavier Desmarest and Stéphan Constance), which subsequently acquired Outremer (2007), Garcia (2010), Alumarine (2013), Ocean Voyageur (2015), Gunboat (2016) and RM Yachts (2020) as separate brands. (source: https://www.grandlargeyachting.com/en/about-us/)
- Series-production evidence: Official heritage page documents founding in 2003 by engineers Stéphan Constance and Xavier Desmarest, first model Allures 44 (2003), a dedicated Cherbourg production facility since 2010, and a current series (40.9, 45.9, 51.9, Horizon 47) of aluminum-hull/composite-deck centreboard cruising yachts.
- Official current site: https://www.allures.com/en
- Official heritage archive: https://www.allures.com/en/spirit-allures/history
- Sources:
  - [official_heritage_archive] History - Allures Yachting — https://www.allures.com/en/spirit-allures/history (retrieved 2026-08-22T00:00:00Z)
  - [official_site] About us - Grand Large Yachting — https://www.grandlargeyachting.com/en/about-us/ (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.allures.com/en/spirit-allures/history: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://www.grandlargeyachting.com/en/about-us/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative hull count found.
- Review status: **verified**
- Ambiguity notes: Note the founders' names appear spelled 'Desmarest' (Grand Large Yachting page) vs 'Desmaret' in the Allures history summary; likely the same person (Xavier Desmarest), spelling should be reconciled against an official source.

### 18. Garcia Yachts

- Aliases: none recorded
- Entity kind: manufacturer, yard, brand
- Country: France
- Region: Western Europe
- Status: active
- Production era: start=1974 end=None basis=exact
- Relationships:
  - acquired_by -> Allures Yachting / Grand Large Yachting: Garcia joined the Grand Large Yachting group (via Allures) in 2010, gaining Allures' composite-deck/production infrastructure while contributing its own aluminum-fabrication expertise. (source: https://www.garciayachts.com/en/garcia-spirit/history)
- Series-production evidence: Official heritage page documents founding by brothers Jean-Pierre and Jean-Louis Garcia in 1974 in Normandy, an early series of ~60 steel vessels, a 1980s transition to aluminum with naval architect Philippe Harlé (Maracuja, Volnay, Malibu models), and the Jimmy Cornell-driven Exploration 45 (2011) and Exploration 60 lines; secondary sources cite over 300 ocean-cruising boats built across four decades.
- Official current site: https://www.garciayachts.com/en
- Official heritage archive: https://www.garciayachts.com/en/garcia-spirit/history
- Other archive sources: https://www.nautipedia.it/index.php/HISTORY_OF_GARCIA_SHIPYARD
- Sources:
  - [official_heritage_archive] Our History - The Evolution of Garcia Yachts — https://www.garciayachts.com/en/garcia-spirit/history (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.garciayachts.com/en/garcia-spirit/history: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=300 basis=estimated notes=Official/near-official phrasing: 'more than three hundred ocean cruising boats' produced over forty years.
- Review status: **verified**
- Ambiguity notes: None

### 19. ETAP Yachting

- Aliases: Etap, Etap Yachts
- Entity kind: manufacturer, yard, brand
- Country: Belgium
- Region: Western Europe
- Status: unknown
- Production era: start=1970 end=2012 basis=estimated
- Relationships:
  - acquired_by -> Dehler Yachts: Dehler Yachts acquired the financially struggling company in 2008; Dehler Deutschland itself filed for bankruptcy later the same year. (source: https://en.wikipedia.org/wiki/ETAP_Yachting)
  - acquired_by -> MIC Industries: MIC Industries purchased the ETAP brand and moulds in March 2009 after the January 2009 insolvency. (source: https://en.wikipedia.org/wiki/ETAP_Yachting)
- Series-production evidence: Founded by Norbert Joris in 1970 (Mol/Malle area, Belgium), originally an aluminium/fibreglass/lighting manufacturer; first sailboat design ETAP 22 (1974), followed by ETAP 20 (1975); noted for unsinkable foam-sandwich construction; series production of models such as the ETAP 37s continued through the 2000s.
- Official current site: None
- Official heritage archive: None
- Other archive sources: https://en.wikipedia.org/wiki/ETAP_37s
- Sources:
  - [specialist_secondary] ETAP Yachting - Wikipedia — https://en.wikipedia.org/wiki/ETAP_Yachting (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://en.wikipedia.org/wiki/ETAP_Yachting: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative hull count found.
- Review status: **needs_review**
- Ambiguity notes: CONFLICT NOT RESOLVED: the Wikipedia article marks the company defunct as of a November 2010 date-flag, yet also references boat-design advertising activity resuming by 2021 under the post-2009 ownership (MIC Industries), so current operating status is recorded as 'unknown' rather than a firm 'defunct' pending a primary-source check of whether any entity is presently marketing ETAP-branded boats.

### 20. Contest Yachts (Conyplex)

- Aliases: Conyplex, Conyplex B.V.
- Entity kind: manufacturer, yard, brand
- Country: Netherlands
- Region: Western Europe
- Status: active
- Production era: start=1959 end=None basis=exact
- Relationships: none recorded
- Series-production evidence: Founded by Ed Conijn in 1959 in Medemblik; began with the Flying Dutchman dinghy (600+ built, basis of an Olympic racing class) before moving into the Contest 25/27/29/31 keelboat series in the 1960s-70s; three generations of family ownership (Ed, Fritz, Arjen Conijn) have continued series/semi-custom production up to current 42-85ft models, ~12-15 vessels/year.
- Official current site: https://www.contestyachts.com
- Official heritage archive: None
- Other archive sources: https://www.sailboat-cruising.com/Contest-Yachts.html, https://www.jorvikrose.com/about-contest-yachts
- Sources:
  - [specialist_secondary] Behind the Scenes at Contest Yachts — https://www.cruisingworld.com/behind-scenes-at-contest-yachts/ (retrieved 2026-08-22T00:00:00Z)
  - [specialist_secondary] Contest Yachts: Dutch Luxury Sailboats for Bluewater Cruising — https://www.sailboat-cruising.com/Contest-Yachts.html (retrieved 2026-08-22T00:00:00Z)
  - [official_site] Contest Yachts official site — https://www.contestyachts.com (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.cruisingworld.com/behind-scenes-at-contest-yachts/: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://www.contestyachts.com: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative hull count found; current rate ~12-15 boats/year, ~50/year at points in company history per differing secondary sources.
- Review status: **verified**
- Ambiguity notes: One low-quality automated fetch of a De Valk brokerage page incorrectly attributed founding to designer Jan van de Stadt in Zaandam; this is contradicted by three independent sources (Cruising World, sailboat-cruising.com, jorvikrose.com) that consistently credit Ed Conijn founding in Medemblik in 1959, so the De Valk claim is treated as an error and not used.

### 21. Trintella (Jachtwerf Anne Wever / Trintella Shipyard B.V.)

- Aliases: Jachtwerf Anne Wever, Trintella Shipyard B.V., Trintella Ship Yards
- Entity kind: manufacturer, yard, brand
- Country: Netherlands
- Region: Western Europe
- Status: historical
- Production era: start=1959 end=2002 basis=exact
- Relationships:
  - renamed -> Trintella Shipyard B.V.: Anne Wever sold the yard in 1992 (renamed Trintella Ship Yards); it went bankrupt in July 1993 and restarted within three months under Irish ownership. (source: https://trintella.org/en/yachts/documentation-yard)
  - other -> Doomernik Yachts: Brand trademark rights returned to Dutch ownership in 2017; Doomernik Yachts presented a 'Trintella 2.0' concept in 2018. (source: https://trintella.org/en/yachts/history)
- Series-production evidence: Founded by Anne Wever (harbourmaster turned boatbuilder) in 's-Hertogenbosch; first GRP construction in Europe by 1961; the Trintella name/series began with a Van de Stadt-designed 8.5m yacht in 1964; celebrated its 1000th yacht in 1978; series grew up to the Trintella 53 (1980) before closure of the original shipyard in 2002.
- Official current site: None
- Official heritage archive: https://trintella.org/en/yachts/history
- Other archive sources: https://trintella.org/en/yachts/documentation-yard, https://www.nautipedia.it/index.php/TRINTELLA_HISTORY_1
- Sources:
  - [class_or_owners_association] Brand History - Trintella Vriendenkring — https://trintella.org/en/yachts/history (retrieved 2026-08-22T00:00:00Z)
  - [class_or_owners_association] History and documentation Trintella Shipyard - Trintella Vriendenkring — https://trintella.org/en/yachts/documentation-yard (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://trintella.org/en/yachts/history: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
  - https://trintella.org/en/yachts/documentation-yard: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=1000 basis=exact notes=Owners'-association source states the 1000th yacht was celebrated in 1978; total lifetime production beyond that point not itemized in sources gathered this pass.
- Review status: **verified**
- Ambiguity notes: Brand rights changed hands multiple times after the original shipyard's 2002 closure (to an English shipyard, then an Italian owner, then back to Dutch trademark ownership in 2017); no confirmed current production entity was found, so this record covers the original historical shipyard (1959-2002) rather than any later trademark holder.

### 22. Victoire Jachtbouw

- Aliases: Victoire Yachts
- Entity kind: manufacturer, yard, brand
- Country: Netherlands
- Region: Western Europe
- Status: defunct
- Production era: start=1961 end=2018 basis=exact
- Relationships: none recorded
- Series-production evidence: Founded in 1961 by Dick Koopmans Sr. and Frans Maas in Alkmaar (yard traced back further to 1934 canoe-building by Cor Vader); moved into GRP series production with the Victoire 22 in the 1960s and continued a numbered model series (22, 25, 28, 32, 34, 40, 42) designed largely by Dick Koopmans Sr./Jr. and later André Hoek, closing in 2018 after roughly six decades.
- Official current site: None
- Official heritage archive: None
- Other archive sources: https://www.doevemakelaar.nl/en/ships-by-brand-and-type/victoire, https://www.devalk.nl/en/brand/victoire.html
- Sources:
  - [specialist_secondary] Victoire - DoeveMakelaar — https://www.doevemakelaar.nl/en/ships-by-brand-and-type/victoire (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://www.doevemakelaar.nl/en/ships-by-brand-and-type/victoire: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No cumulative hull count found.
- Review status: **needs_review**
- Ambiguity notes: Relies only on a brokerage-site secondary source rather than an official company or class-association archive (the yard is defunct and no dedicated heritage site was located this pass); founder date '1961' for the formal Victoire Jachtbouw entity should be reconciled against the separately reported 1934 Cor Vader canoe-building origin, which this record treats as a predecessor activity rather than the same production_era start.

### 23. Koopmans

- Aliases: Koopmans Yachtbuilders, Dick Koopmans Yacht Design
- Entity kind: brand
- Country: Netherlands
- Region: Western Europe
- Status: unknown
- Production era: start=1961 end=None basis=unknown
- Relationships:
  - other -> Victoire Jachtbouw: Dick Koopmans Sr. co-founded Victoire Jachtbouw in 1961 and designed its Victoire model series; Koopmans-designed boats have historically been built by multiple different contracted yards rather than a single dedicated Koopmans-branded production yard. (source: https://www.doevemakelaar.nl/en/ships-by-brand-and-type/victoire)
- Series-production evidence: Named model series (Koopmans 33, 36, 39, 40, 42, 43, 48, 50) are marketed and sold under the 'Koopmans' name across brokerage sites, suggesting brand-level recognition, but the evidence gathered this pass could not confirm a single manufacturing/marketing organization (as opposed to a naval-architecture design office whose designs are built to order by varying yards) actually operating as the series producer.
- Official current site: None
- Official heritage archive: None
- Other archive sources: https://yachts.apolloduck.com/boats/koopmans, https://www.yachtfocus.com/en/boats/make-koopmans/
- Sources:
  - [specialist_secondary] All Koopmans Sailing Yachts for sale — https://yachts.apolloduck.com/boats/koopmans (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://yachts.apolloduck.com/boats/koopmans: access=public, systematic_use_status=UNKNOWN, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No production entity or cumulative count identified; models appear to be built to a common design by varying yards/owners rather than by one series manufacturer.
- Review status: **excluded**
- Ambiguity notes: EXCLUDED per the task's exclusion rule for 'designers/naval architects who never themselves manufactured/marketed a series boat.' Evidence gathered this pass (including an attempted fetch that returned only unrelated information about the separately-founded 'Zeelander Yachts') indicates 'Koopmans' functions primarily as the identity of the Dick Koopmans Sr./Jr. naval-architecture design office, whose designs were built by separate, independently operating yards (e.g. Victoire Jachtbouw). No evidence was found this pass of Koopmans itself operating as a manufacturing yard or as a legal/marketing organization that itself produced or sold a Koopmans-branded series independent of the individual builder yards. Retained in this registry (rather than dropped) so the exclusion decision and its evidence are auditable.

### 24. Bruynzeel (yacht-design sponsorship activity)

- Aliases: Bruynzeel Fabrieken, Bruynzeel Jachtwerf (unconfirmed)
- Entity kind: brand, legal_organization
- Country: Netherlands
- Region: Western Europe
- Status: unknown
- Production era: start=1939 end=1956 basis=estimated
- Relationships:
  - other -> E.G. van de Stadt: Bruynzeel (timber/plywood manufacturer) commissioned naval architect Ricus van de Stadt to design the Valk (1939), Zeevalk (1949/1951) and Zeeslang (1956) to showcase Bruynzeel's 'hechthout' marine plywood; sources do not establish that Bruynzeel itself operated the shipyard(s) that physically built these designs. (source: https://en.wikipedia.org/wiki/E._G._van_de_Stadt)
- Series-production evidence: The Valk and related designs became recognized one-design/series sailboat classes still sailed today, and Bruynzeel is the commissioning/sponsoring name consistently associated with their creation as a demonstration of its plywood product; however, no source located this pass confirms Bruynzeel itself (as opposed to van de Stadt's own yard or other licensed builders) as the manufacturing entity.
- Official current site: None
- Official heritage archive: None
- Other archive sources: http://stadtdesign.com/pages/history
- Sources:
  - [specialist_secondary] E. G. van de Stadt - Wikipedia — https://en.wikipedia.org/wiki/E._G._van_de_Stadt (retrieved 2026-08-22T00:00:00Z)
  - [designer_archive] History - Stadt Design — http://stadtdesign.com/pages/history (retrieved 2026-08-22T00:00:00Z)
  - [specialist_secondary] Kees Bruynzeel - Wikipedia — https://en.wikipedia.org/wiki/Kees_Bruynzeel (retrieved 2026-08-22T00:00:00Z)
- Rights assessment:
  - https://en.wikipedia.org/wiki/E._G._van_de_Stadt: access=public, systematic_use_status=CLEARED, license_evidence=Wikipedia text is CC BY-SA licensed, reviewed=2026-08-22
  - http://stadtdesign.com/pages/history: access=public, systematic_use_status=REQUIRES_REVIEW, license_evidence=None, reviewed=2026-08-22
- Model yield estimate: value=None basis=unknown notes=No production entity or cumulative count confirmed as belonging to Bruynzeel itself rather than to the designer's own yard or third-party licensed builders.
- Review status: **excluded**
- Ambiguity notes: EXCLUDED: evidence gathered this pass consistently describes Bruynzeel as a door/plywood manufacturer that commissioned and marketed showcase yacht designs (Valk, Zeevalk, Zeeslang) through naval architect E.G. van de Stadt, rather than as an entity that itself operated a shipyard/manufactured the boats. This falls on the excluded side of the manufacturer/brand vs. materials-supplier-plus-designer-collaboration line per the task's semantic rule; retained here (excluded, not dropped) so the boundary judgment and its evidence are auditable. A genuine 'Bruynzeel Jachtwerf' production yard may exist and would justify re-inclusion if located with direct evidence in a follow-up pass.
