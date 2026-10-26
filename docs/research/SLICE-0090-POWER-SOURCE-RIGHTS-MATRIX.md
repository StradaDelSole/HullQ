# SLICE-0090 — Power-Domain Source/Rights Matrix v0.1

**Status:** DESIGN_RESEARCH evidence artifact — no source below is cleared for production ingestion by this document  
**Date:** 2026-10-26  
**Framework:** ADR-0005 (Structured Source Rights and Use-Specific Clearance), `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`  
**Scope:** representative Power (motorboat/motoryacht) technical-data source families, assessed for lawful *reference and future clearance review*, not harvested  
**Hard constraint carried from the slice contract:** no scraping or downloading of protected bulk datasets, no bypassing access controls, no confidential keys, no account purchases, no signed legal commitments. Any `UNKNOWN`/`LEGAL_REVIEW_REQUIRED` row below stays that way until an explicit, source-specific future decision — it is not resolved by assumption here.

Each row uses ADR-0005's six dimensions: **rights basis**, **license expression/scope**, **access conditions**, **permissions/obligations**, **HullQ use-specific clearance** (by use case: `research_reference`, `research_lead`, `identity_seed`, `production_value`, `bulk_bootstrap`, `automated_ingestion`, `artifact_redistribution`), and **review metadata**.

---

## Family 1 — Wikidata (structured open data, propulsion/engine/manufacturer entities)

- **Representative access point:** `wikidata.org` SPARQL/API query surface for vessel/engine/manufacturer entities (same source already recommended for bootstrap in OQ-007 §3).
- **Rights basis:** `public_domain` (CC0 dedication, as already documented in OQ-007 §3).
- **License expression/scope:** `CC0-1.0`; covers database structure and contents per Wikidata's own stated policy.
- **Access conditions:** public API; rate-limit/etiquette rules apply at the access layer independent of the license; reviewed 2026-10-26 against the same policy OQ-007 cited 2026-08-18 (no indication of a license change).
- **Permissions/obligations:** no attribution legally required (CC0); HullQ SHOULD still record source lineage internally for provenance, not as a license obligation.
- **HullQ use-specific clearance:** `research_reference: allowed`; `research_lead: allowed`; `identity_seed: allowed`; `production_value: allowed` (for facts actually present and sourced from Wikidata, with HullQ provenance recorded); `bulk_bootstrap: allowed` (subject to access-method/rate policy, i.e. `automated_ingestion: conditional`); `artifact_redistribution: conditional` on Wikidata's own current redistribution policy at ingestion time.
- **Correction/takedown path:** standard Wikidata community edit/revert process; HullQ must re-pull on dispute rather than treat a cached value as permanently authoritative.
- **Disposition:** GREEN.

## Family 2 — Manufacturer/builder official technical specification pages (e.g. factory model/spec-sheet pages for powerboat OEMs)

- **Representative access point:** individual OEM model-line specification pages (e.g. hull dimensions, engine options, fuel capacity) reachable without authentication.
- **Rights basis:** `unlicensed_factual_reference` — no explicit open license observed; page content is manufacturer-owned copyrighted expression even where underlying facts (a dimension, a capacity) are not independently copyrightable.
- **License expression/scope:** none asserted; `scope: unknown/mixed` (text and imagery are the manufacturer's own content; database-right status of the spec-sheet collection as a whole is unassessed).
- **Access conditions:** publicly reachable; ToS/robots status not yet reviewed per-OEM in this pass; **no automated bulk crawl has been performed or authorized**.
- **Permissions/obligations:** none granted; discrete factual reuse (a single numeric spec, with provenance) sits in OQ-007's "primary factual reference with no explicit open license" default class, not a blanket permission.
- **HullQ use-specific clearance:** `research_reference: allowed`; `research_lead: allowed`; `production_value: conditional` (discrete factual values only, with provenance recorded, no expressive copying, no bulk extraction); `bulk_bootstrap: prohibited` until source-specific review; `automated_ingestion: unknown/prohibited` until terms/robots/TDM-reservation are assessed per OEM; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** none established; any dispute defaults to removing the specific claimed fact and marking it `UNKNOWN` pending re-verification.
- **Disposition:** AMBER (per-OEM review required before any claim derived from this family backs a production Search criterion at scale).

## Family 3 — Classification-society / technical-standard documents (e.g. recognized marine certification body technical guidance referenced by manufacturers for stability/load-line-adjacent facts)

- **Representative access point:** publicly published standard summaries or certification-scheme descriptions.
- **Rights basis:** `standard_license` or `custom_license` depending on the issuing body; many standards bodies publish summaries openly but gate the full standard text behind purchase or membership.
- **License expression/scope:** varies by body; **not assumed uniform** — each specific document needs its own `LicenseRef-HullQ-*` entry if used.
- **Access conditions:** summaries often free; full normative text frequently requires purchase/license — HullQ has not purchased or obtained any such license.
- **Permissions/obligations:** citing that a vessel claims compliance with a named standard is a factual/attribution-style statement; reproducing the standard's own text/tables is not permitted without the body's license.
- **HullQ use-specific clearance:** `research_reference: allowed` (citation only); `research_lead: allowed`; `production_value: conditional` (only for the fact "manufacturer asserts compliance with standard X," never for reproduced normative content); `bulk_bootstrap: prohibited`; `automated_ingestion: prohibited`; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** N/A at reference-only clearance; escalates to `legal_review_required` before any deeper use.
- **Disposition:** AMBER, leaning toward `legal_review_required` for anything beyond a bare compliance-claim citation.

## Family 4 — Broker-owned concrete vessel claims (the publisher's own attested data about the specific offered PhysicalBoat)

- **Representative access point:** HullQ's own first-party broker intake (not a third-party source at all).
- **Rights basis:** `explicit_permission` — the publishing Organization is the asserting party under HullQ's existing broker agreement/terms, not a scraped third party.
- **License expression/scope:** N/A (not a license question); this is a **provenance/trust** question, governed by the claim `AssertionKind`/revision model already accepted (`physical_boat_claims.py`), not by ADR-0005's external-source dimensions.
- **Access conditions:** first-party intake only (import formats 0083, broker UI editing); no automated third-party scraping involved.
- **Permissions/obligations:** HullQ may store and search this data under the broker's own publishing agreement; HullQ must never represent it as independently manufacturer-verified (post-0088 contract §3 point 3 — "laut Brokerangabe" vs. independent verification).
- **HullQ use-specific clearance:** `research_reference: allowed`; `production_value: allowed` **as a publisher-attested claim**, explicitly labeled as such (never promoted to design-confirmed truth without independent corroboration); `bulk_bootstrap: not applicable` (this is operational intake, not a bootstrap source); `automated_ingestion: not applicable`; `artifact_redistribution: prohibited` beyond the broker's own export rights already governed by the 0088 export contract.
- **Correction/takedown path:** existing claim-revision/retraction mechanism (`PhysicalBoatClaimRevisionId`), already accepted.
- **Disposition:** GREEN for its *trust-labeled* use (not a "verified" use); this family is the primary input to the qualified-concrete-claim candidate path proposed in the architecture pack §2.3.

## Family 5 — Existing third-party boat-market aggregator/compiled spec databases (e.g. a commercial listings portal's own "specs" database distinct from live listings)

- **Representative access point:** a competitor/aggregator's compiled technical-spec database pages, distinct from their live classified listings.
- **Rights basis:** `unlicensed_factual_reference` at best, likely `custom_license`/ToS-restricted; these are exactly the "sui-generis database right" case OQ-007 §2.1 and ADR-0005 flag — substantial compiled investment in a spec database is independently protectable from the underlying facts.
- **License expression/scope:** none observed as open; ToS for most such portals explicitly restrict automated extraction/reuse.
- **Access conditions:** publicly browsable, **not** authorized for automated/bulk extraction per typical ToS language (not individually re-verified per portal in this pass — treated conservatively).
- **Permissions/obligations:** none established; systematic/repeated extraction of this kind of compiled database is precisely what EU Directive 96/9/EC Art. 7 is designed to restrict even when individual facts are not separately copyrightable.
- **HullQ use-specific clearance:** `research_reference: allowed` (a human reading one page to understand the domain); `research_lead: conditional`; `production_value: prohibited` until a specific portal's ToS/rights are individually reviewed and found to permit it; `bulk_bootstrap: prohibited`; `automated_ingestion: prohibited`; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** N/A — not in use.
- **Disposition:** RED for any current production use; this is the family the slice's "no false license claims" stop condition is most directly protecting against.

## Family 6 — Open-government / registry datasets (e.g. a national small-craft or recreational-vessel registry publishing open data extracts)

- **Representative access point:** a government open-data portal's vessel-registry dataset, where one exists with a stated open license.
- **Rights basis:** depends entirely on the specific portal's stated terms — `public_domain`, `standard_license` (e.g. a national Open Government Licence), or `unknown` if no explicit statement is found.
- **License expression/scope:** must be read per-dataset; no blanket assumption that "government data" implies an open license in every jurisdiction.
- **Access conditions:** typically open download/API; some registries restrict personal/owner information distinct from vessel technical facts — **personal/owner data is out of scope for HullQ regardless of license** (core guardrail: no real buyer/owner PII).
- **Permissions/obligations:** attribution is common under open-government licenses; HullQ must track this per dataset.
- **HullQ use-specific clearance:** `research_reference: allowed`; `production_value: conditional` on the specific dataset's confirmed open-license status and strict exclusion of personal/owner fields; `bulk_bootstrap: conditional` on the same; `automated_ingestion: conditional` on the portal's own API terms; `artifact_redistribution: conditional` on the license's attribution/share-alike terms.
- **Correction/takedown path:** registry's own data-correction process; HullQ re-syncs rather than treating a snapshot as permanently authoritative.
- **Disposition:** AMBER/GREEN depending on jurisdiction — **no specific registry has been verified in this pass**; each candidate registry needs its own dated rights-review row before use, consistent with ADR-0005's default-deny posture.

## Family 7 — Historical/out-of-print manufacturer archives (e.g. a discontinued OEM's historical brochure/spec archive with no currently reachable rights statement)

- **Representative access point:** archived historical brochures/spec sheets, often mirrored by third-party enthusiast sites rather than the (possibly defunct) original manufacturer.
- **Rights basis:** `unknown` — copyright in historical manufacturer material typically survives corporate dissolution and transfers to a successor/estate that HullQ has not identified.
- **License expression/scope:** unknown/unknown.
- **Access conditions:** unknown; the hosting enthusiast site's own rights to mirror the material are themselves unverified.
- **Permissions/obligations:** none established.
- **HullQ use-specific clearance:** `research_reference: allowed` strictly as a research lead (e.g., "this model generation appears to have existed with this engine option, verify independently"); every other use case: `unknown`.
- **Correction/takedown path:** N/A.
- **Disposition:** UNKNOWN — explicitly not resolved by this pack. This is the deliberate "document unavailability rather than invent a source" case the slice contract requires (§2 of the primary slice contract).

## Family 8 — Independent engine/propulsion manufacturer technical documentation (distinct from the hull/boat OEM — e.g. a diesel/outboard engine maker's own published power-curve/fuel-consumption documents)

- **Representative access point:** engine manufacturer's own published technical data sheets (rated power, fuel-consumption curves at stated RPM/load).
- **Rights basis:** `unlicensed_factual_reference`, same class as Family 2, but a materially distinct source family because it is the *propulsion* source of truth, not the *hull* OEM, and is often the only place a condition-qualified operating-point basis (RPM, load, test standard) is actually documented.
- **License expression/scope:** none asserted; own copyrighted document, factual data points inside it not independently protectable.
- **Access conditions:** publicly reachable technical-data-sheet pages/PDFs; no bulk download authorized.
- **Permissions/obligations:** none granted beyond ordinary reading/citation.
- **HullQ use-specific clearance:** `research_reference: allowed`; `production_value: conditional` (discrete rated-power/fuel-curve data points, with the document's own stated test basis preserved as the `OperatingPointClaim` basis field proposed in the architecture pack §2.4 — never divorced from its measurement conditions); `bulk_bootstrap: prohibited`; `automated_ingestion: prohibited`; `artifact_redistribution: prohibited`.
- **Correction/takedown path:** manufacturer document revision; HullQ must track document version/date as part of the claim's `observed_at`/revision metadata.
- **Disposition:** AMBER — this family is specifically called out because it is the most promising lawful path to real operating-point *basis* data (test standard, RPM, load), which Family 2 (hull OEM pages) usually omits.

---

## Summary table

| # | Family | Rights basis | Disposition | Bulk bootstrap | Automated ingestion |
|---|---|---|---|---|---|
| 1 | Wikidata | public_domain (CC0) | GREEN | allowed | conditional |
| 2 | Hull OEM spec pages | unlicensed_factual_reference | AMBER | prohibited | unknown/prohibited |
| 3 | Classification/standard documents | standard/custom_license | AMBER→legal_review | prohibited | prohibited |
| 4 | Broker-owned concrete claims | explicit_permission (first-party) | GREEN (trust-labeled) | n/a | n/a |
| 5 | Third-party aggregator spec DBs | unlicensed/custom, ToS-restricted | RED | prohibited | prohibited |
| 6 | Open-government vessel registries | varies, must verify per dataset | AMBER/GREEN (unverified) | conditional | conditional |
| 7 | Historical/out-of-print archives | unknown | UNKNOWN | unknown | unknown |
| 8 | Engine/propulsion manufacturer docs | unlicensed_factual_reference | AMBER | prohibited | prohibited |

**Eight distinct source families are registered, exceeding the six-family minimum.** No family above is cleared for `bulk_bootstrap` or `automated_ingestion` without a further source-specific review; none of this matrix's rows constitute a production-data decision. Family 4 (broker-owned claims) is the only family cleared for `production_value: allowed` today, and only in its explicitly trust-labeled form — it is first-party intake under HullQ's own existing terms, not a third-party rights question at all.

## Review metadata

- Review date: 2026-10-26.
- Reviewer: SLICE-0090 implementation agent, desk review only (no account creation, no bulk download, no ToS circumvention performed).
- Re-review trigger: any ingestion-code proposal against any row above must re-verify that row's rights statement at the time of that future slice, not rely on this date.
