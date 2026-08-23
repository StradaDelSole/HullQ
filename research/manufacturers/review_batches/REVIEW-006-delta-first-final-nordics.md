# SLICE-0019 manufacturer review batch 006 — delta-first final Nordics

**Scope:** bounded independent review of the final 3 recovered `needs_review` records from the Nordic checkpoint.

**Method:** strict evidence-delta review. The already-preserved Claude evidence set was inspected first. Additional research was limited to concrete unresolved manufacturer/yard eligibility, production-era, and identity-separation questions. No `registry.json` or canonical HullQ entity is modified by this note.

This batch completes adjudication of all **43 records that were originally marked `needs_review`** across the five fully recovered checkpoint workstreams. Completion of review does **not** mean all 43 become manufacturer/yard-floor records; some have been verified only as brand/relationship context, some retain uncertainty, and some require corrected identity/status fields before mechanical integration.

## 1. Oy Fiskars Ab Boatyard / Turku Boatyard (Finnsailer)

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical Finnish production yard/manufacturer with a documented series-sailing-yacht role; correct the checkpoint's overly narrow production-era assumptions and keep the parent Fiskars company distinct from the boatyard activity.

- Claude's recovered record had only secondary/specialist evidence for the Finnsailer line and therefore remained `needs_review`.
- Fiskars' own archived annual reports now provide primary company evidence for the boatyard and yacht production:
  - the 1975 report states that a new **Finnsailer 38** had been designed and that **series production had started**;
  - the 1976 report lists **Turku Boatyard** as a Fiskars branch factory producing leisure and service boats in fiberglass;
  - the 1978 report identifies the new **Finnsailer 34** as a boatyard product;
  - the 1979 report lists the leisure-boat range as Finnsailer 30, Finnsailer 34, Finnsailer 38 and Finnfire 33 Cruising;
  - the 1980 report still describes Finnsailer 30/34 production and sales at the Fiskars boatyard.
- These are sufficient to verify that Oy Fiskars Ab operated a real production boatyard that manufactured repeated sailing/motorsailing yacht models, not merely a brand or distributor.
- The checkpoint's estimated `1970–1979` sailboat-production era should not be treated as exact: primary evidence proves the sailing/leisure yacht line was still being produced/marketed in 1980. The exact first and final years of the Finnsailer sailboat line remain to be encoded with uncertainty unless stronger primary evidence is found.
- Fiskars' 1983 annual report still shows the Turku Boatyard operating, but by then the surfaced report emphasizes patrol, lifeboat and special-vessel work rather than proving continued Finnsailer sailboat production. Therefore do **not** extend the sailing-yacht production era to 1983 solely from continued existence of the boatyard.
- Recommended modeling:
  - research entity: historical **Oy Fiskars Ab / Turku Boatyard** manufacturer/yard role;
  - Finnsailer as product/model-line context, not a separate yard identity;
  - parent Fiskars corporation remains a separate broader legal/corporate identity;
  - sailboat-series production positively evidenced at least during the mid-1970s through 1980, with exact endpoints uncertainty-preserving.

Primary company sources:
- https://fiskarsgroup.com/wp-content/uploads/2022/10/Fiskars_ENG_1975.pdf
- https://fiskarsgroup.com/wp-content/uploads/2022/10/Fiskars_ENG_1976.pdf
- https://fiskarsgroup.com/wp-content/uploads/2022/10/Fiskars_ENG_1978.pdf
- https://fiskarsgroup.com/wp-content/uploads/2022/10/Fiskars_ENG_1979.pdf
- https://fiskarsgroup.com/wp-content/uploads/2022/10/Fiskars_ENG_1980.pdf
- https://fiskarsgroup.com/wp-content/uploads/2022/10/Fiskars_ENG_1983.pdf

## 2. Bringsværd Boat Yard / BB Boatyard

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical Norwegian series-sailboat manufacturer/yard; resolve the recovered operating-span ambiguity using the direct family source.

- The checkpoint already had strong evidence for large repeated production of the BB11 but left the record `needs_review` because the readable sources appeared to conflict about whether the yard ended in 1968 or continued to 1984.
- The previously difficult BB17.org PDF is now directly readable. It is a first-person historical account by **Borge Bringsværd Jr.**, son of the builder/designer, and states:
  - Borge Bringsværd ran the boatyard at Husvikholmen, Drøbak for more than 50 years;
  - serial production of mahogany sailing boats began in 1956;
  - over a 20-year period the yard produced approximately **1,200 BB11**, **350 BB17** and **3 BB35**;
  - it later produced **2,000 Yngling sailing boats** with fiberglass hulls;
  - Borge Bringsværd died in 1982;
  - the BB boatyard closed in **1984**.
- The apparent contradiction is therefore resolved: **1956–~1976** describes the twenty-year BB11/17/35 serial-production phase, not the entire operating life of the yard. The yard itself continued later, including Yngling production, and closed in 1984.
- This is exceptionally strong evidence for series-sailboat manufacturer eligibility and also improves the production-yield estimate substantially.
- Recommended modeling:
  - verified historical manufacturer/yard;
  - yard closure `1984` supported by direct family historical evidence;
  - series-sailboat activity from at least 1956 through later Yngling production;
  - do not use `1968` as the yard end year merely because one BB model's major production period ended around then;
  - model-specific quantities remain separate from cumulative yard output.

Primary-adjacent family/owner archive:
- https://bb17.org/wp-content/uploads/Brief-von-BB-junior.pdf

The direct account supports approximately 1,553 BB11/BB17/BB35 boats plus 2,000 later Ynglings, i.e. more than 3,500 sailboats across the documented lines, but these figures should remain individually attributed rather than converted into a falsely exact single lifetime total if overlap/counting conventions are unclear.

## 3. Fjord Plast AS — historical sailboat/motorsailer role

**Provisional decision:** `PROMOTE TO VERIFIED` as a historical Norwegian production manufacturer/yard with a documented series motorsailer/sailboat role; keep the present-day FJORD powerboat brand separate from the historical manufacturing identity.

- Claude's checkpoint correctly identified a major continuity hazard: the original Norwegian **A/S Fjord Plast** and today's HanseYachts-owned FJORD powerboat brand are not the same physical manufacturing operation or product category.
- Current FJORD's own official history nevertheless confirms the Norwegian origin of **FJORD Plast** and names founder Alf Bjerke together with engineers Finn B. Roer and Jan Herrmann Linge.
- A recognized Norwegian boating-history article documents Fjord Plast's large multi-site production operation in the early 1970s and explicitly includes **sailboats** in its historical product categories; it also names the **Fjord MS 33** among the Fjord model program.
- Surviving original-product material reproduced by the Fjord MS 33 owner archive explicitly identifies **Fjord Plast as the manufacturer** and describes the MS 33 as a true motorsailer with a sailing rig and sailing capability.
- The owner archive has identified roughly **55 Fjord-Plast-built MS 33s**, with later boats from the same mould produced separately in Denmark after Norwegian production ceased. Exact unit count remains estimated, but repeated series production is clearly demonstrated.
- A motorsailer with documented sailing rig and sailing design is within the sailboat-relevant research universe; the fact that Fjord Plast primarily produced motorboats does not negate the qualifying historical sailboat/motorsailer production line.
- Recommended modeling:
  - verified historical Norwegian manufacturer/yard role for Fjord Plast;
  - sailboat/motorsailer production relationship anchored in the Fjord MS 33 and any other independently supported sailing models;
  - do not treat today's FJORD/HanseYachts powerboat operation as continuous manufacturer identity;
  - do not infer current sailboat production from the surviving brand;
  - retain Norwegian MS 33 production era/end as estimated unless stronger factory records establish exact dates; later Danish same-mould production belongs to a separate builder relationship.

Sources:
- Official current-brand heritage for historical origin: https://fjordboats.com/gb/history/
- Recognized Norwegian historical article: https://www.batmagasinet.no/allerbm-bm-bladarkiv-batbyggeri/as-fjord-plast--en-epoke/624346
- Original-brochure reproduction / owner archive: https://fjordms33.wordpress.com/2013/11/28/the-boat-description-page1/
- Production/fleet reconstruction: https://fjordms33.wordpress.com/2015/01/02/finding-the-fleet-part-2/

## Batch outcome

All three final recovered `needs_review` records can be promoted to verified manufacturer/yard research candidates after correction:

- **Oy Fiskars Ab / Turku Boatyard** — verified historical Finnish production yard; primary Fiskars reports directly document Finnsailer series production.
- **Bringsværd Boat Yard** — verified historical Norwegian series-sailboat yard; direct family source resolves closure and production-span ambiguity.
- **Fjord Plast AS** — verified historical Norwegian manufacturer with a genuine repeated motorsailer/sailboat product line; present FJORD powerboat brand kept separate.

## Recovered-needs-review milestone

With this file, every one of the **43 `needs_review` records recovered from checkpoint workstreams 1–5 has now received an independent bounded adjudication** across REVIEW-001 through REVIEW-006.

This milestone means:

- the original Claude `needs_review` queue has been exhausted;
- decisions and corrections are preserved in Git immediately after each bounded batch;
- some records are verified manufacturer/yard-floor candidates;
- some are verified only as brand/relationship context and must not count toward the manufacturer/yard floor;
- some fields remain deliberately `unknown`, estimated, or relationship-bound;
- the original checkpoint/raw files remain untouched as an audit trail.

It does **not** yet mean that the SLICE-0019 `>=120 verified eligible manufacturer/yard` floor is met. Exact counts require mechanical application of all review decisions, entity-kind correction, deduplication, and exclusion of brand-only/context records.

No `registry.json` counts are changed by this note. The next safe step is a bounded **review-consolidation/count pass** over the recovered 112 records plus REVIEW-001..006 before deciding how much genuinely new Southern-Europe / Asia-Pacific / Rest-of-World research is still required.