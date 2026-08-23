# SLICE-0019 manufacturer review batch 001 — North America

**Scope:** bounded independent review of 8 `needs_review` records recovered in the SLICE-0019 checkpoint.

**Method:** current/official and reputable specialist sources were checked selectively. SailboatData may be used as post-hoc/reference context only and is not accepted as production evidence under HullQ source policy. This file records research conclusions only; it does not modify `registry.json` or canonical HullQ entities.

## 1. Marlow-Hunter

**Provisional decision:** `KEEP NEEDS_REVIEW` for current-status fields; manufacturer eligibility itself is supported historically.

- The checkpoint record's `status=active` is not supportable as written.
- Multiple current secondary references report that the Alachua manufacturing site was sold by 2020 and that Marlow-Hunter appeared no longer in business by 2024, but the clearest current statement found is on SailboatData, which HullQ does not accept as production evidence.
- Recommended correction before verification: do not retain `active`; use an uncertainty-preserving current status until a non-SailboatData source establishes closure/continuation.
- Do not merge Marlow-Hunter back into Hunter Marine; the post-2012 entity/ownership transition remains a meaningful relationship.

Reference-only current-status lead: https://sailboatdata.com/builder/hunter-marine-usa/

## 2. Pacific Seacraft

**Provisional decision:** `PROMOTE TO VERIFIED` after adding the current official source.

- The official Pacific Seacraft site is currently retrievable and explicitly describes the Crealock 37 as the basis for "all of our current models".
- The official current sailboat surface is therefore enough to resolve the checkpoint's TLS/access doubt and support `status=active`.
- Historical 2007 bankruptcy/restart details remain supported by secondary sources and do not prevent verification of the entity.

Primary current source: https://www.pacificseacraft.com/html/sailboats.html

## 3. Gemini Catamarans / Performance Cruising lineage

**Provisional decision:** `ELIGIBILITY CONFIRMED; CURRENT STATUS NEEDS CORRECTION/REVIEW`.

- Cruising World documents Gemini Catamarans as an established production company and records the 2014 move of Legacy 35 production from Marlow-Hunter to Catalina Yachts in Largo, Florida.
- The Catamaran Company documents its 2009 majority interest in Performance Cruising and the 2010 subcontracting of Gemini manufacture to Hunter Marine.
- These sources are sufficient to support historical series-production eligibility and the ownership/contract-builder relationships.
- They are not sufficient to establish that sailboat production remains active in 2026.
- Recommendation: preserve the entity, but use `status=unknown` (or the schema-equivalent uncertainty state) rather than inventing a closure year. Once corrected, the historical record can be considered verified even if present-day production status remains unknown.

Sources:
- https://www.cruisingworld.com/sailboats/gemini-catamarans-move/
- https://www.catamarans.com/who-we-are/

## 4. MacGregor Yacht Corporation

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical/defunct production manufacturer, with uncertainty retained on disputed quantitative details.

- Good Old Boat records Roger MacGregor's Stanford MBA work and states that he founded MacGregor Yacht Corporation in 1964.
- Independent historical summaries agree that production ended in 2013 when Roger MacGregor retired and the Costa Mesa factory closed.
- The checkpoint's conflicting lifetime production counts should remain explicitly estimated/conflicting; those counts are not needed to establish manufacturer eligibility.
- Recommended production era: start 1964; end 2013; historical/defunct.

Sources:
- https://goodoldboat.com/wp-content/uploads/GOBMagazine/gob90may13.pdf
- https://en.wikipedia.org/wiki/MacGregor_Yacht_Corporation (secondary corroboration only)

## 5. Alerion Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` and retain `status=active`.

- The official Alerion site is live and currently exposes model pages for the 20, 28, 30 and 33, with specifications and build/configuration information.
- Maine Boats documents Peter Eastman's acquisition of Alerion Yachts in late 2019 and the plan to continue production with the existing build team.
- Current official model surfaces remove the checkpoint's concern that activity could only be inferred from 2019–2020 ownership articles.
- Ownership/build relationships should remain explicit; do not collapse brand ownership and physical builder into one entity.

Sources:
- https://alerionyachts.com/
- https://alerionyachts.com/model/30/
- https://maineboats.com/blog/2020/new-owner-alerion-yachts

## 6. Morgan Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical manufacturer/acquired lineage, while retaining uncertainty on disputed founding-year detail if present in the record.

- Catalina's official history states that Catalina acquired Morgan Yachts in Largo, Florida in May 1984.
- It explicitly says the operation became the Morgan Division of Catalina and continued building cruising/charter boats and many Catalina models.
- The same official history records later Morgan Division production activity, including Procyon in 1991 and introduction of a new Morgan 38 in 1992.
- This is strong primary evidence for Morgan's separate historical manufacturer identity and its later acquisition/relationship to Catalina.

Primary source: https://www.catalinayachts.com/history/

## 7. Ericson Yachts

**Provisional decision:** `PROMOTE TO VERIFIED` as historical/defunct, but do not encode the disputed founding chronology as an exact fact.

- Multiple independent specialist histories agree that Ericson was a genuine high-volume/series production sailboat builder and that original Ericson operations ceased in 1990.
- Practical Sailor and Good Old Boat histories support transfer of selected Ericson molds to Pacific Seacraft around 1990/1991 and subsequent Pacific Seacraft production of some Ericson-derived models.
- Sources differ on the exact earliest founding narrative (Handy/Jenkins vs. Don/Gene Kohlmann involvement and 1963/1964/1965 milestones). HullQ should preserve that uncertainty rather than choose one unsupported exact start year.
- Recommended: verified entity; `status=defunct`; end year 1990; start-year basis approximate/uncertain unless stronger evidence is later found.

Sources:
- https://www.practical-sailor.com/sailboat-reviews/used_sailboats/ericson-32/
- https://goodoldboat.com/ericson-34/
- https://ericsonyachts.org/ie/threads/a-partial-armchair-history-of-ericson-yachts.17568/ (owners-association/history corroboration)

## 8. Columbia Yachts

**Provisional decision:** `KEEP NEEDS_REVIEW`; likely an identity/lineage modeling issue rather than a simple missing-source issue.

- The recovered record appears to span the original Columbia lineage beginning in 1958, later Hughes/Aura transitions, and a separate 2001 Columbia Yacht Corporation revival.
- Historical sources support the original Columbia production lineage and later transfer of Columbia production to Hughes Boat Works in 1979, but the 2001 revival had different corporate formation/leadership and should not automatically be flattened into the original entity.
- This conflicts with HullQ's rule that acquisitions, revivals and ownership changes must be represented as relationships rather than silent equivalence.
- Recommendation: do not promote the current single combined record. First decide whether the original Columbia manufacturer lineage and the 2001 revival need separate research entities connected by a brand/revival relationship.

Useful sources:
- https://en.wikipedia.org/wiki/Columbia_Yachts (secondary chronology; not sufficient alone for final identity decision)
- historical Hughes/Columbia production chronology should be independently sourced before final adjudication.

## Batch outcome

Of 8 reviewed records:

- **4 recommended for promotion to VERIFIED:** Pacific Seacraft, MacGregor Yacht Corporation, Alerion Yachts, Morgan Yachts.
- **1 recommended for VERIFIED with explicit chronology uncertainty:** Ericson Yachts.
- **1 historical eligibility confirmed but current status must be corrected before final verification:** Gemini Catamarans / Performance Cruising lineage.
- **1 remains NEEDS_REVIEW because current operational status lacks acceptable non-reference evidence:** Marlow-Hunter.
- **1 remains NEEDS_REVIEW because the recovered record likely collapses distinct Columbia lineages:** Columbia Yachts.

No registry counts should be changed from this note alone. Mechanical application to `registry.json` is deferred until the research batches are complete and reviewed.