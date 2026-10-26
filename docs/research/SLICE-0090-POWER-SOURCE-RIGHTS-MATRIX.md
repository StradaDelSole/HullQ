# SLICE-0090 — Power-Domain Source/Rights Matrix v0.2

**Status:** DESIGN_RESEARCH evidence artifact — no source below is cleared for production ingestion by this document  
**Date:** 2026-10-26 (v0.1 superseded in response to independent-review finding A: v0.1 used generic/representative descriptions rather than genuinely checked sources; v0.2 below additionally corrects findings H/I/J — a NautiX `power-*` token miscount, an internally inconsistent family-count summary, and a bulk-bootstrap/CC0 contradiction)  
**Framework:** ADR-0005 (Structured Source Rights and Use-Specific Clearance), `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`  
**Scope:** representative Power (motorboat/motoryacht) technical-data source families, assessed for lawful *reference and future clearance review*, not harvested  
**Hard constraint carried from the slice contract:** no scraping or downloading of protected bulk datasets, no bypassing access controls, no confidential keys, no account purchases, no signed legal commitments. Any `UNKNOWN`/`LEGAL_REVIEW_REQUIRED` row below stays that way until an explicit, source-specific future decision — it is not resolved by assumption here.

**Evidence-confidence labels used below:**

- **DIRECTLY VERIFIED (2026-10-26)** — this agent fetched/searched the named URL today in this session and is reporting what was actually returned.
- **INHERITED CITATION** — carried from an earlier accepted research record (OQ-007, 2026-08-18) and not independently re-checked in this session.
- **INDIRECTLY CORROBORATED** — the primary source page itself could not be fetched in this session (e.g. blocked), but its existence/content is corroborated by independent secondary sources found via search.
- **ACCESS BLOCKED / NOT LOCATED (documented limitation, not filled speculatively)** — a direct check was attempted and failed, or a specific primary source could not be found; the gap is reported, not invented.

Each row uses ADR-0005's six dimensions: **rights basis**, **license expression/scope**, **access conditions**, **permissions/obligations**, **HullQ use-specific clearance** (by use case: `research_reference`, `research_lead`, `identity_seed`, `production_value`, `bulk_bootstrap`, `automated_ingestion`, `artifact_redistribution`), and **review metadata**.

---

## Family 1 — Wikidata (structured open data; candidate propulsion/engine/manufacturer/vessel-identity entities)

- **Source:** Wikidata, `https://www.wikidata.org/wiki/Wikidata:Licensing` (the project's own licensing policy page).
- **Evidence confidence:** DIRECTLY VERIFIED (2026-10-26, via live fetch).
- **Exact finding:** "all structured data in Wikidata's main, Property, Lexeme, and EntitySchema namespaces is released into the public domain under Creative Commons Zero (CC0)." The policy page does not itself resolve database-right/sui-generis status and explicitly notes community practice avoids hosting non-CC0 claims, which is a policy statement, not an independent legal confirmation.
- **Concrete identity evidence:** representative entities exist for the domain this slice needs — `motorboat` (`https://www.wikidata.org/wiki/Q622416`, "a boat which is powered by an engine") and `sailboat` (`https://www.wikidata.org/wiki/Q1075310`) were located via live search on 2026-10-26, confirming Wikidata already models boat-category identity, not merely a theoretical candidate.
- **Rights basis:** `public_domain` (CC0 dedication).
- **License expression/scope:** `CC0-1.0`; covers database structure and contents per Wikidata's own stated policy.
- **Access conditions:** public API/SPARQL; rate-limit/etiquette rules apply at the access layer independent of the license.
- **Permissions/obligations:** no attribution legally required (CC0); HullQ SHOULD still record source lineage internally for provenance, not as a license obligation.
- **HullQ use-specific clearance:** `research_reference: allowed`; `research_lead: allowed`; `identity_seed: allowed`; `production_value: allowed` (for facts actually present and sourced from Wikidata, with HullQ provenance recorded); `bulk_bootstrap: allowed` (subject to access-method/rate policy, i.e. `automated_ingestion: conditional`); `artifact_redistribution: conditional` on Wikidata's own current redistribution policy at ingestion time.
- **Correction/takedown path:** standard Wikidata community edit/revert process; HullQ must re-pull on dispute rather than treat a cached value as permanently authoritative.
- **Disposition:** GREEN.

## Family 2 — Manufacturer/builder official technical specification pages (hull OEM model/spec-sheet pages)

- **Source class:** individual powerboat OEM model-line specification pages (hull dimensions, engine options, fuel capacity).
- **Evidence confidence:** rights-posture pattern is INHERITED CITATION (OQ-007 §5's "primary factual reference with no explicit open license" default class, 2026-08-18) applied to this new domain; **no specific powerboat OEM's page was fetched and individually verified in this session** — this is reported honestly as a gap rather than naming a specific manufacturer's terms without having checked them.
- **Rights basis:** `unlicensed_factual_reference` — no explicit open license is typically present on manufacturer pages (consistent with OQ-007's general finding, not independently re-confirmed per-manufacturer here); the page's text/imagery is the manufacturer's own copyrighted content, independent of whether a given numeric spec is itself copyrightable.
- **License expression/scope:** none asserted; `scope: unknown/mixed`.
- **Access conditions:** typically publicly reachable; ToS/robots status not reviewed per-OEM in this pass; **no automated bulk crawl has been performed or authorized.**
- **Permissions/obligations:** none granted; discrete factual reuse (a single numeric spec, with provenance) sits in OQ-007's conditional class, not a blanket permission.
- **HullQ use-specific clearance:** `research_reference: allowed`; `research_lead: allowed`; `production_value: conditional` (discrete factual values only, with provenance recorded, no expressive copying, no bulk extraction); `bulk_bootstrap: prohibited` until source-specific review; `automated_ingestion: unknown/prohibited` until terms/robots/TDM-reservation are assessed per OEM; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** none established; any dispute defaults to removing the specific claimed fact and marking it `UNKNOWN` pending re-verification.
- **Disposition:** AMBER (per-OEM review required; this row is explicitly a pattern, not a verified specific-manufacturer clearance).

## Family 3a — EUR-Lex / Directive 2013/53/EU (Recreational Craft and Personal Watercraft Directive, "RCD")

- **Source:** `https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32013L0053` (official EU legislative text).
- **Evidence confidence:** DIRECTLY VERIFIED (2026-10-26, via live search returning the official EUR-Lex record and its reuse basis).
- **Exact finding:** the Directive defines design categories A/B/C/D by wind force and significant wave height (the same four values already present in HullQ's own pinned NautiX `CEType` enumeration — i.e. this is a real, directly relevant regulatory source for a field HullQ's import/export pipeline already carries). Reuse of EU documents, including EUR-Lex content, is governed by **Commission Decision 2011/833/EU**, confirmed via search: "all documents should be available for reuse either for commercial or for non-commercial purposes, without charge," and current EU digital-portal editorial content is licensed `CC BY 4.0`. Attribution is required.
- **Rights basis:** `statutory_exception`/`standard_license` — official legislative text with an explicit, confirmed EU reuse decision.
- **License expression/scope:** `CC-BY-4.0`-equivalent reuse per Commission Decision 2011/833/EU; covers the editorial/legislative text itself.
- **Access conditions:** free public access via EUR-Lex; no automation restriction identified for this specific legislative text.
- **Permissions/obligations:** attribution required; this is citing/relying on a regulatory *classification scheme*, not reproducing a manufacturer's proprietary data.
- **HullQ use-specific clearance:** `research_reference: allowed`; `production_value: allowed` for the fact "this design category is the regulatory A/B/C/D classification defined by Directive 2013/53/EU," with attribution; `bulk_bootstrap: not applicable` (this is a fixed four-value regulatory enumeration, not a bulk dataset); `automated_ingestion: not applicable`; `artifact_redistribution: conditional` on attribution.
- **Correction/takedown path:** N/A — stable legislative text; future amendments would be a new directive/consolidated-text citation.
- **Disposition:** GREEN, directly verified — the strongest-grounded AMBER-adjacent family in this matrix, recorded separately from Family 3b because its rights posture is materially better than a paywalled technical standard.

## Family 3b — ISO 8666 ("Small craft — Principal data") international standard

- **Source:** `https://www.iso.org/standard/65424.html` (ISO 8666:2016/2020 catalog record).
- **Evidence confidence:** INDIRECTLY CORROBORATED (2026-10-26). A direct fetch of the iso.org page returned **HTTP 403 Forbidden** in this session — documented as an access limitation, not filled speculatively. Search results independently corroborate the standard's existence, number, and scope via secondary listings (ANSI webstore, standards.iteh.ai, scribd mirror of the 2002 edition): it "establishes definitions of main dimensions and related data and of mass specifications and loading conditions," applying to small craft up to 24 m LH, maintained by ISO/TC 188.
- **Rights basis:** `standard_license`/`custom_license` — ISO standards are, as a matter of general, well-established ISO practice, sold/licensed documents, not freely reproducible; this general practice was not independently re-confirmed by a direct iso.org fetch in this session (blocked), so it is reported as the standards body's generally known posture rather than a directly quoted term.
- **License expression/scope:** not independently obtained in this session; **no purchase was made and no full standard text was accessed.**
- **Access conditions:** catalog/summary browsing appears public; full normative text access is blocked for automated fetch in this session and is understood (general ISO practice) to require purchase.
- **Permissions/obligations:** citing that a vessel claims compliance with ISO 8666 is a factual/attribution-style statement; reproducing the standard's own text/tables is not permitted without ISO's license.
- **HullQ use-specific clearance:** `research_reference: allowed` (citation only, via the catalog record); `production_value: conditional` (only for the fact "manufacturer/claim asserts compliance with ISO 8666," never for reproduced normative content); `bulk_bootstrap: prohibited`; `automated_ingestion: prohibited`; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** N/A at reference-only clearance.
- **Disposition:** AMBER, leaning `legal_review_required` for anything beyond a bare compliance-claim citation; direct iso.org terms were not independently obtained in this session.

## Family 4 — Broker-owned concrete vessel claims (first-party HullQ intake — not a license question)

- **Source:** HullQ's own first-party broker intake (0083 import formats, broker UI editing) — not a third-party web source.
- **Evidence confidence:** governed by existing accepted HullQ code/contract (`physical_boat_claims.py`), not a web-research citation.
- **Rights basis:** `explicit_permission` — the publishing Organization is the asserting party under HullQ's existing broker agreement/terms.
- **Corrected scope (amendment finding B):** being the first-party publisher establishes that HullQ may lawfully store and search the *broker's own factual assertion about the broker's own offered vessel*. It does **not** by itself establish (a) independent factual accuracy of the claim, (b) that the broker holds reproduction/redistribution rights over any attached third-party document/photo/manufacturer material used to support the claim, or (c) any clearance for HullQ to syndicate that supporting material onward. Those remain separate, already-governed content-rights and verification questions that this family does not resolve or widen.
- **License expression/scope:** N/A — this is a provenance/trust question, governed by the claim `AssertionKind`/revision model already accepted, not by ADR-0005's external-source dimensions.
- **Access conditions:** first-party intake only (import formats 0083, broker UI editing); no automated third-party scraping involved.
- **Permissions/obligations:** HullQ may store and search this data under the broker's own publishing agreement; HullQ must never represent it as independently manufacturer-verified (post-0088 contract §3 point 3).
- **HullQ use-specific clearance:** `research_reference: allowed`; `production_value: allowed` **as a publisher-attested claim**, explicitly labeled `source_basis: PUBLISHER_CLAIM` and never promoted to design-confirmed truth without independent corroboration, and only after the full evidence-threshold test in the architecture pack §2.3 (not from mere `VALUE_ASSERTION` presence); `bulk_bootstrap: not_applicable`; `automated_ingestion: not_applicable`; `artifact_redistribution: prohibited` beyond the broker's own export rights already governed by the 0088 export contract.
- **Correction/takedown path:** existing claim-revision/retraction mechanism (`PhysicalBoatClaimRevisionId`), already accepted.
- **Disposition:** GREEN for its *trust-labeled* first-party use only — explicitly not counted toward the "six distinct external source families" requirement, since it is not a third-party rights question at all (recorded here per amendment finding B's instruction to apply default-deny discipline consistently, including making this distinction explicit).

## Family 5 — Boats Group (YachtWorld / boats.com / boatwizard.com / soldboats.com) — third-party aggregator, confirmed restricted

- **Source:** `https://www.yachtworld.com/robots.txt`, `https://www.boattrader.com/robots.txt`, and the Boats Group terms of use referenced from them.
- **Evidence confidence:** DIRECTLY VERIFIED (2026-10-26) for the robots.txt/ToS clause content, via live search returning the quoted restriction. A direct fetch of `https://www.boatsgroup.com/terms-of-use-eu/` was attempted and returned **HTTP 403 Forbidden** — documented as an access limitation; the clause below is corroborated through the robots.txt directive and indexed ToS summary rather than a direct full-page fetch.
- **Exact finding (quoted):** "The use of robots, crawlers, spiders, rovers, scrapers or other automated means to access or mine data from any Boats Group hosted web sites ... without the express written permission of Boats Group is strictly prohibited." A limited exception exists for non-marine-specific public search-engine indexing only.
- **Rights basis:** `custom_license`/ToS-restricted; this is exactly the sui-generis compiled-database case ADR-0005 and OQ-007 §2.1 flag.
- **License expression/scope:** none open; explicit automated-extraction prohibition.
- **Access conditions:** publicly browsable by a human visitor; automated/bulk extraction is explicitly prohibited without written permission.
- **Permissions/obligations:** none established for HullQ; no permission has been sought or granted.
- **HullQ use-specific clearance:** `research_reference: allowed` (a human reading one page to understand the domain); `production_value: prohibited`; `bulk_bootstrap: prohibited`; `automated_ingestion: prohibited`; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** N/A — not in use.
- **Disposition:** RED. This is the family the slice's "no false license claims" stop condition is most directly protecting against, and it is now backed by an actually-quoted restriction rather than a generic assumption.

## Family 6 — Third-party engine fuel-consumption aggregator mirror sites (distinct from the engine OEM itself)

- **Source:** representative real examples located via live search on 2026-10-26: `https://www.boatgph.com/` and `https://www.boat-fuel-economy.com/` (both independent, non-manufacturer sites compiling engine fuel-consumption-vs-RPM tables, e.g. for Volvo Penta models).
- **Evidence confidence:** DIRECTLY VERIFIED as to existence/URL/content description (2026-10-26, via search); their own underlying rights/sourcing were **not** further investigated (out of scope — HullQ has performed no extraction from them).
- **Rights basis:** `unknown` — these sites appear to compile manufacturer-sourced figures into their own presentation with no stated license found in this pass; their own right to republish manufacturer figures is itself unverified.
- **License expression/scope:** unknown/unknown.
- **Access conditions:** publicly browsable; no automated extraction authorized or performed.
- **Permissions/obligations:** none established.
- **HullQ use-specific clearance:** `research_reference: allowed` only as a pointer to "an engine of this model exists with roughly this consumption profile, verify independently against the OEM"; every other use case: `unknown`/`prohibited`.
- **Correction/takedown path:** N/A.
- **Disposition:** RED/UNKNOWN — a second, distinct aggregator family from Family 5, specifically because it illustrates that even technically-oriented compiled data (not just classified-ad listings) carries the same unresolved-rights problem.

## Family 7 — Official engine/propulsion-manufacturer technical documentation (the primary source Family 6 is a shadow of)

- **Source class:** an engine manufacturer's own published technical data sheets (e.g. Volvo Penta, as named in the original v0.1 draft).
- **Evidence confidence:** **ACCESS BLOCKED / NOT LOCATED (documented limitation, not filled speculatively) — amendment correction.** Live search on 2026-10-26 for Volvo Penta's own official specification/ToS page did **not** surface it directly; results surfaced only the third-party mirrors already listed as Family 6. The original v0.1 draft of this matrix implicitly treated this family as reviewable (AMBER) without having actually located or fetched any official OEM page — that was an overstatement this amendment corrects. No specific engine OEM's rights posture is asserted here until a future pass actually locates and fetches the official page.
- **Rights basis:** unknown — not established in this session.
- **License expression/scope:** unknown.
- **Access conditions:** unknown.
- **Permissions/obligations:** unknown.
- **HullQ use-specific clearance:** `research_reference: unknown`; every other use case: `unknown`, pending an actual located-and-fetched official source.
- **Correction/takedown path:** N/A.
- **Disposition:** UNKNOWN. This family is retained specifically to record the gap honestly rather than deleting it or quietly reverting to an unverified AMBER claim — it is the clearest illustration of the amendment's instruction "if any research source is inaccessible, document the limitation rather than filling the gap speculatively." It also directly grounds the architecture pack's §2.4 correction (finding G): even once an official OEM source is located, its engine-level data alone would still not establish a vessel-specific range/consumption fact.

## Family 8 — Historical/discontinued-manufacturer brochure archives

- **Source:** real examples located via live search on 2026-10-26: `https://boatbrochure.com/` ("SailInfo" brochure archive), `https://chris-craft.org/historic-archive/` (Chris-Craft Antique Boat Club's historic archive of brochures/specifications), and an active enthusiast discussion thread at `https://www.trawlerforum.com/threads/old-boat-brochures-marine-trading-international-grand-banks-32-albin-36.77561/`.
- **Evidence confidence:** DIRECTLY VERIFIED as to existence/URL/general content (2026-10-26, via search); no rights statement was found or fetched from any of them, and none is assumed.
- **Rights basis:** `unknown` — copyright in historical manufacturer material typically survives corporate dissolution and transfers to a successor/estate HullQ has not identified; the hosting enthusiast/club sites' own right to mirror the material is itself unverified.
- **License expression/scope:** unknown/unknown.
- **Access conditions:** unknown; no bulk extraction performed or authorized.
- **Permissions/obligations:** none established.
- **HullQ use-specific clearance:** `research_reference: allowed` strictly as a research lead (e.g. "this model generation appears to have existed with this engine option, verify independently"); every other use case: `unknown`.
- **Correction/takedown path:** N/A.
- **Disposition:** UNKNOWN — directly mirrors the already-accepted SailboatData disposition in OQ-007 §6 (reference/prototype only, not production data), now with real Power-domain example URLs instead of a generic placeholder.

## Family 9 — EU Open Data Portal: Community Fishing Fleet Register (verified open-government example — scope caveat)

- **Source:** `https://data.europa.eu/data/datasets/nuqbfrdzl3j02bdtxxlsw` (Fishing Fleet, Number of Vessels dataset) and the parent EU Open Data Portal.
- **Evidence confidence:** DIRECTLY VERIFIED (2026-10-26, via search) — the dataset is confirmed licensed `CC BY 4.0`.
- **Scope caveat (amendment finding B):** this register covers **commercial fishing vessels**, not recreational/private power craft. It is cited here as a **verified precedent that a government vessel registry can carry a genuinely open license**, not as a usable Power-recreational-craft data source. No equivalent, rights-verified recreational/private-power-vessel open-government registry was located in this session; that remains a GENUINELY_OPEN gap in the architecture pack, not resolved by this row.
- **Rights basis:** `standard_license` (confirmed for this specific dataset only).
- **License expression/scope:** `CC-BY-4.0`.
- **Access conditions:** open download via the EU Open Data Portal.
- **Permissions/obligations:** attribution required.
- **HullQ use-specific clearance:** `production_value: not_applicable_to_power_recreational_domain` (wrong vessel class for HullQ's Power scope); retained for its methodological precedent only. No clearance values are asserted for any *other* country's vessel registry — each would need its own dated, source-specific row before any use, per ADR-0005's default-deny posture.
- **Correction/takedown path:** registry's own data-correction process.
- **Disposition:** GREEN for this specific dataset's own narrow scope; NOT a cleared Family for HullQ's actual Power-recreational-craft need.

---

## Summary table

| # | Family | Rights basis | Evidence confidence | Disposition | Bulk bootstrap | Automated ingestion |
|---|---|---|---|---|---|---|
| 1 | Wikidata | public_domain (CC0) | DIRECTLY VERIFIED | GREEN | allowed | conditional |
| 2 | Hull OEM spec pages (pattern, not a specific manufacturer) | unlicensed_factual_reference | INHERITED CITATION (pattern) | AMBER | prohibited | unknown/prohibited |
| 3a | EUR-Lex Directive 2013/53/EU (RCD) | statutory/standard, CC BY 4.0 reuse | DIRECTLY VERIFIED | GREEN | not applicable | not applicable |
| 3b | ISO 8666 standard | standard/custom_license | INDIRECTLY CORROBORATED (iso.org blocked 403) | AMBER→legal_review | prohibited | prohibited |
| 4 | Broker-owned concrete claims (first-party, not a license question) | explicit_permission | N/A — internal | GREEN (trust-labeled, scope-corrected) | n/a | n/a |
| 5 | Boats Group / YachtWorld / boats.com | custom_license, ToS-restricted | DIRECTLY VERIFIED (quoted clause) | RED | prohibited | prohibited |
| 6 | Third-party fuel-consumption aggregator mirrors | unknown | DIRECTLY VERIFIED (existence only) | RED/UNKNOWN | prohibited | prohibited |
| 7 | Official engine/propulsion OEM documentation | unknown | **ACCESS BLOCKED / NOT LOCATED** | UNKNOWN | unknown | unknown |
| 8 | Historical/discontinued-manufacturer archives | unknown | DIRECTLY VERIFIED (existence only) | UNKNOWN | unknown | unknown |
| 9 | EU Fishing Fleet Register (precedent only, wrong vessel class) | standard_license, CC BY 4.0 | DIRECTLY VERIFIED | GREEN (scope-limited) | n/a to Power domain | n/a to Power domain |

**Corrected totals (amendment finding I — the previous revision's count/list were internally inconsistent):**

- **Ten lettered/numbered entries total** in this matrix: 1, 2, 3a, 3b, 4, 5, 6, 7, 8, 9.
- **Nine genuinely distinct *external* source families** — 1, 2, 3a, 3b, 5, 6, 7, 8, 9 — exceeding the six-family minimum. Family 4 (first-party broker-attested claims) is deliberately **excluded** from this external-family count, per amendment finding B: it is not a third-party rights question at all, and counting it toward "external source families" would overstate how many genuinely independent rights determinations this matrix has made.
- **Of those nine external families, evidence quality is not uniform — do not read any family as equally verified:**
  - **Six families have at least one directly fetched/searched piece of real evidence obtained in this session (2026-10-26):** 1 (Wikidata licensing page, directly fetched), 3a (EUR-Lex/Commission Decision 2011/833/EU, directly confirmed via search), 5 (Boats Group robots.txt/ToS clause, directly quoted via search — note the full ToS *page* fetch itself was blocked, see Family 5's own entry), 6 (aggregator mirror sites, existence/URLs directly confirmed), 8 (historical-archive sites, existence/URLs directly confirmed), 9 (EU Fishing Fleet Register license, directly confirmed).
  - **One family (3b, ISO 8666) is corroborated only indirectly** — the primary iso.org page itself returned HTTP 403 in this session; its existence, number and scope summary rest on independent secondary listings, not a direct primary-source read.
  - **One family (2, hull-OEM spec pages) carries no specific-source evidence from this session at all** — it restates OQ-007's general 2026-08-18 pattern for "primary factual reference with no explicit open license" applied to the Power domain, with **no individual manufacturer page identified or fetched**. It should be read as a documented rights *pattern*, not a verified citation.
  - **One family (7, official engine/propulsion OEM documentation) has zero evidence obtained** — a direct search for an official source was attempted and failed to surface one; this is recorded as an honest gap (`ACCESS BLOCKED / NOT LOCATED`), not populated with an assumed rights posture.
- No family above is cleared for `bulk_bootstrap` or `automated_ingestion` **except where a row's own clearance line explicitly states otherwise** — see the correction immediately below (amendment finding J) for Family 1/Wikidata, which is the one deliberate exception, not a contradiction.

### Correction — Wikidata bulk-bootstrap clearance vs. the blanket no-bulk statement (amendment finding J)

An earlier revision of this matrix asserted a blanket "no source in this register is marked cleared for `bulk_bootstrap`" immediately below this table, while Family 1's own row states `bulk_bootstrap: allowed`. That was a genuine internal contradiction, not a deliberate exception — corrected here:

- **CC0 reuse rights** (the license question): Wikidata's CC0 dedication places no copyright/database-right restriction on bulk reuse of its structured data. On the license dimension alone, `bulk_bootstrap: allowed` for Wikidata is accurate and is **not** revised.
- **API access conditions** (a separate, operational dimension): Wikidata's own access layer (SPARQL endpoint/API rate limits, query-service etiquette) still governs *how* any bulk pull may be performed — this is why Family 1's `automated_ingestion` is marked `conditional`, not `allowed`, even though the license itself is unconditionally open.
- **Actual operational ingestion approval** (a third, HullQ-internal dimension, and the one this matrix does **not** grant): a license being `allowed` and an access method being technically `conditional`-but-satisfiable does **not** by itself authorize anyone to actually run a production bootstrap job against Wikidata. That requires a future implementation slice (decision-map row F) to specify the concrete query/rate/retry/provenance-recording mechanism and pass its own readiness review — this research pack performs **zero** ingestion, bulk or otherwise, and authorizes none.

**Corrected statement replacing the prior blanket claim:** of the nine external families, **only Family 1 (Wikidata) has its `bulk_bootstrap` license dimension marked `allowed`**, and even there, `automated_ingestion` remains `conditional` and no operational ingestion is authorized by this document. Every other external family's `bulk_bootstrap` is `prohibited`, `unknown`, or `not applicable` as stated in its own row above. This document performs and authorizes **no actual ingestion of any kind** against any source, Wikidata included.

## Review metadata

- Review date: 2026-10-26 (v0.2 amendment; v0.1 superseded; second correction pass same date for findings H/I/J).
- Reviewer: SLICE-0090 implementation agent. v0.2 used live `WebSearch`/`WebFetch` against the real URLs cited above; no account creation, no bulk download, no ToS circumvention performed. Three fetch attempts (ISO standard page, Boats Group EU ToS page) returned HTTP 403 and are reported as such rather than reconstructed from memory or invented.
- Second-pass corrections (findings H/I/J, same date): the NautiX `power-*` enumeration was recounted directly against the pinned XSD (33, not 29); the external-family count/list was reconciled to nine (1, 2, 3a, 3b, 5, 6, 7, 8, 9) with Family 4 kept explicitly separate; the blanket bulk-bootstrap denial was corrected to acknowledge Wikidata's own `allowed` license-dimension row while clarifying no ingestion is actually authorized.
- Re-review trigger: any ingestion-code proposal against any row above must re-verify that row's rights statement at the time of that future slice, not rely on this date — web sources can and do change their terms.
