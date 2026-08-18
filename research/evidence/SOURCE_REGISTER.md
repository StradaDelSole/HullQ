# HullQ — External Evidence / Source Register

**Status:** ACTIVE  
**Last updated:** 2026-08-18  
**Purpose:** Central index of external sources used to support project decisions, research notes, standards, legal/access investigations, and future data-source evaluation.

## Evidence policy

HullQ does **not** vendor arbitrary third-party copyrighted webpages, brochures, PDFs, or databases into the repository merely because they were consulted.

For external evidence the repository MUST retain, at minimum:

- stable source ID;
- publisher/organization;
- title/subject;
- source type;
- canonical URL or document identifier;
- access/review date;
- claim/decision supported;
- relevant HullQ document(s);
- licensing/rights status when the source is considered for data ingestion rather than merely factual research.

If an external document is legally redistributable and materially required for reproducibility, it MAY be vendored under `reference/` together with its license and source metadata. Otherwise HullQ stores the citation/metadata, not an unauthorized copy.

This register is **evidence metadata**, not a production-data source whitelist. Data ingestion rights are governed by accepted OQ-007 / `specs/SOURCE_RIGHTS_POLICY.v0.1.md` / ADR-0005.

---

## OQ-003 — Model / Design Generation / Variant / Option Identity

### SRC-EVID-0001 — Hallberg-Rassy 36

- Publisher: Hallberg-Rassy
- Source type: manufacturer model archive
- URL: https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-36
- Reviewed: 2026-08-18
- Supports: documented Mk I/Mk II production split and shallow-draft option; evidence for separating generation from concurrent factory option.
- Used by: `docs/research/OQ-003_IDENTITY_RESEARCH.md`, `specs/IDENTITY_MODEL.v0.1.md`, ADR-0004.

### SRC-EVID-0002 — Hallberg-Rassy 31 Mk II

- Publisher: Hallberg-Rassy
- Source type: manufacturer model archive
- URL: https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-31-mk-ii
- Reviewed: 2026-08-18
- Supports: production number 307 / model-year boundary and documented Mark II changes; evidence for an evidence-backed BoatDesign generation boundary.
- Used by: `docs/research/OQ-003_IDENTITY_RESEARCH.md`, `specs/IDENTITY_MODEL.v0.1.md`, ADR-0004.

### SRC-EVID-0003 — Hallberg-Rassy 42E

- Publisher: Hallberg-Rassy
- Source type: manufacturer model archive
- URL: https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-42e
- Reviewed: 2026-08-18
- Supports: ketch/sloop and shallow-draft choices within the same commercial model; evidence for orthogonal option axes.
- Used by: `docs/research/OQ-003_IDENTITY_RESEARCH.md`, `specs/IDENTITY_MODEL.v0.1.md`, ADR-0004.

### SRC-EVID-0004 — Hallberg-Rassy shallow-draft FAQ

- Publisher: Hallberg-Rassy
- Source type: manufacturer FAQ
- URL: https://www.hallberg-rassy.com/resources/faq
- Reviewed: 2026-08-18
- Supports: shallow-draft versions can change keel geometry/weight while remaining factory alternatives.
- Used by: OQ-003 supporting research.

### SRC-EVID-0005 — Catalina 22 Capri

- Publisher: Catalina Yachts
- Source type: manufacturer model specifications
- URL: https://www.catalinayachts.com/sport-series/22-capri/
- Reviewed: 2026-08-18
- Supports: fin/wing keel alternatives change draft, ballast, weight and derived ratios; standard/tall mast measurements coexist.
- Used by: `docs/research/OQ-003_IDENTITY_RESEARCH.md`, `specs/IDENTITY_MODEL.v0.1.md`, ADR-0004.

### SRC-EVID-0006 — Jeanneau Sun Odyssey 410 inventory/specification document

- Publisher: Jeanneau
- Source type: manufacturer technical document
- URL: https://app.jeanneau.com/inventory/22574
- Reviewed: 2026-08-18
- Supports: standard/deep, shoal and lifting-keel configurations with differing draft, keel weight and displacement.
- Used by: `docs/research/OQ-003_IDENTITY_RESEARCH.md`, `specs/IDENTITY_MODEL.v0.1.md`, ADR-0004.

### SRC-EVID-0007 — Beneteau Oceanis 35

- Publisher: Beneteau
- Source type: manufacturer model archive
- URL: https://www.beneteau.com/oceanis-2005-2014/oceanis-35
- Reviewed: 2026-08-18
- Supports: Daysailer / Weekender / Cruiser named versions as organization/layout variants rather than automatic new naval-architecture generations.
- Used by: `docs/research/OQ-003_IDENTITY_RESEARCH.md`, `specs/IDENTITY_MODEL.v0.1.md`, ADR-0004.

---

## Engineering / governance standards

The current standards baseline is summarized in `docs/engineering/STANDARDS_BASELINE.md`. Primary standard sources include:

### SRC-STD-0001 — RFC 2119
- Publisher: IETF / RFC Editor
- URL: https://www.rfc-editor.org/rfc/rfc2119
- Purpose: normative requirement keywords.

### SRC-STD-0002 — RFC 8174
- Publisher: IETF / RFC Editor
- URL: https://www.rfc-editor.org/rfc/rfc8174
- Purpose: BCP 14 clarification of uppercase normative keywords.

### SRC-STD-0003 — JSON Schema Draft 2020-12
- Publisher: JSON Schema
- URL: https://json-schema.org/draft/2020-12
- Purpose: JSON contract dialect.

### SRC-STD-0004 — Semantic Versioning 2.0.0
- Publisher: Semantic Versioning
- URL: https://semver.org/spec/v2.0.0/
- Purpose: released contract/component versioning.

### SRC-STD-0005 — Conventional Commits 1.0.0
- Publisher: Conventional Commits
- URL: https://www.conventionalcommits.org/en/v1.0.0/
- Purpose: repository commit-message convention.

### SRC-STD-0006 — PyPA pyproject.toml guidance
- Publisher: Python Packaging Authority
- URL: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- Purpose: Python project configuration baseline when implementation begins.

### SRC-STD-0007 — RFC 6901 JSON Pointer
- Publisher: IETF / RFC Editor
- URL: https://www.rfc-editor.org/rfc/rfc6901
- Reviewed: 2026-08-18
- Purpose: standardized field addressing for OQ-004 provenance records.

### SRC-STD-0008 — W3C PROV-DM
- Publisher: W3C
- URL: https://www.w3.org/TR/prov-dm/
- Reviewed: 2026-08-18
- Purpose: conceptual Entity / Activity / Agent provenance separation informing OQ-004 without requiring full PROV-O/RDF persistence.

### SRC-STD-0009 — RFC 8785 JSON Canonicalization Scheme
- Publisher: RFC Editor
- URL: https://www.rfc-editor.org/rfc/rfc8785
- Reviewed: 2026-08-18
- Purpose: registered as a possible future deterministic JSON fingerprinting reference; not adopted as a HullQ requirement by OQ-004.

---

## External product/business reviews

Raw reviews are preserved under `reference/external_reviews/` and are intentionally non-normative.

- `GEMINI_REVIEW_2026-08-18.md`
- `GROK_REVIEW_2026-08-18.md`
- `CLAUDE_REVIEW_2026-08-18.md`

Relevant conclusions are not considered accepted project decisions until promoted through the normal decision process.

---

## Future source classes to register

As the project advances, this register or successor machine-readable registries MUST cover at least:

- open/bootstrap datasets;
- manufacturer and designer sources;
- manuals/brochures/class-association documents;
- market-platform access/API/partner documentation;
- legal opinions and terms relevant to ingestion/display;
- formula/reference sources for OQ-001;
- toolchain standards selected under OQ-010.

---

## OQ-007 — Source rights / licensing authorities

### SRC-LEGAL-0001 — EU Database Directive 96/9/EC

- Publisher: European Union / EUR-Lex
- Source type: legislation
- URL: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:31996L0009
- Reviewed: 2026-08-18
- Supports: sui-generis database rights are distinct from copyright; extraction/re-utilization of substantial parts and repeated/systematic extraction of insubstantial parts can be restricted; lawful-user rules and eligibility/duration framework.
- Used by: `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`, `specs/SOURCE_RIGHTS_POLICY.v0.1.md`, ADR-0005.

### SRC-LEGAL-0002 — Directive (EU) 2019/790 Article 4

- Publisher: European Union / EUR-Lex
- Source type: legislation
- URL: https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32019L0790
- Reviewed: 2026-08-18
- Supports: TDM exception for lawfully accessible material; copies/extractions may be retained as necessary for TDM; rights holders can expressly reserve rights, including by machine-readable means for public online content.
- Used by: OQ-007 research/policy and TDM-reservation metadata design.

### SRC-LEGAL-0003 — Austrian Urheberrechtsgesetz, consolidated

- Publisher: Republic of Austria / RIS
- Source type: national legislation
- URL: https://www.ris.bka.gv.at/GeltendeFassung.wxe?Abfrage=Bundesnormen&Gesetzesnummer=10001848
- Reviewed: 2026-08-18
- Supports: Austrian implementation of text/data mining and database protection, including §§ 42h and 76c–76e.
- Used by: OQ-007 legal/risk baseline.

### SRC-LIC-0001 — Creative Commons FAQ: Data and databases

- Publisher: Creative Commons
- Source type: license guidance
- URL: https://creativecommons.org/faq/
- Reviewed: 2026-08-18
- Supports: CC 4.0 treatment of sui-generis database rights, CC0 for databases, attribution/share-alike/non-commercial implications, and distinction from ODC licenses.
- Used by: OQ-007 source-class policy.

### SRC-LIC-0002 — CC0 1.0 legal code

- Publisher: Creative Commons
- Source type: legal tool
- URL: https://creativecommons.org/publicdomain/zero/1.0/legalcode.en
- Reviewed: 2026-08-18
- Supports: CC0 scope includes rights protecting extraction/use/reuse of data and database rights.
- Used by: OQ-007 CC0 baseline.

### SRC-LIC-0003 — Open Database License 1.0

- Publisher: Open Data Commons / Open Knowledge Foundation
- Source type: database license
- URL: https://opendatacommons.org/licenses/odbl/1-0/
- Reviewed: 2026-08-18
- Supports: attribution/share-alike database licensing and distinction between database and individual contents.
- Used by: OQ-007 share-alike/compatibility policy.

### SRC-LIC-0004 — Public Domain Dedication and License 1.0

- Publisher: Open Data Commons / Open Knowledge Foundation
- Source type: database legal tool
- URL: https://opendatacommons.org/licenses/pddl/1-0/
- Reviewed: 2026-08-18
- Supports: public-domain-style sharing/modification/use of databases/data.
- Used by: OQ-007 open-source baseline.

### SRC-LIC-0005 — SPDX License List

- Publisher: SPDX / Linux Foundation ecosystem
- Source type: identifier registry
- URL: https://spdx.org/licenses/
- Reviewed: 2026-08-18
- Supports: stable identifiers including CC0-1.0, CC-BY variants, ODbL-1.0 and PDDL-1.0.
- Used by: Source `license_expression` convention.

### SRC-DATA-0001 — Wikidata Licensing

- Publisher: Wikimedia / Wikidata community
- Source type: dataset licensing statement
- URL: https://www.wikidata.org/wiki/Wikidata:Licensing
- Reviewed: 2026-08-18
- Supports: Wikidata requires/uses CC0 for contributed data.
- Used by: OQ-007 bootstrap-source example.

### SRC-DATA-0002 — Wikidata Data Access

- Publisher: Wikimedia / Wikidata community
- Source type: technical access guidance
- URL: https://www.wikidata.org/wiki/Wikidata:Data_access/en
- Reviewed: 2026-08-18
- Supports: Wikidata data is CC0 while access methods have separate technical/stability considerations.
- Used by: OQ-007 access-vs-reuse separation.

### SRC-DATA-0003 — Wikimedia Foundation Terms of Use

- Publisher: Wikimedia Foundation
- Source type: platform terms/licensing statement
- URL: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use
- Reviewed: 2026-08-18
- Supports: Wikimedia text licensing/attribution/share-alike rules and distinction from Wikidata's CC0 project.
- Used by: OQ-007 Wikipedia/Wikidata distinction.

---

## Search / SEO architecture authorities

### SRC-SEO-0001 — URL Structure Best Practices / faceted-navigation guidance
- Publisher: Google Search Central
- Source type: official search-engine technical documentation
- URL: https://developers.google.com/search/docs/crawling-indexing/url-structure
- Reviewed: 2026-08-18
- Supports: intentional URL design and need to control crawlable faceted/dynamic URL spaces.
- Used by: ADR-0007, `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, REQ-SEO-003/004.

### SRC-SEO-0002 — JavaScript SEO Basics
- Publisher: Google Search Central
- Source type: official search-engine technical documentation
- URL: https://developers.google.com/search/docs/crawling-indexing/javascript/javascript-seo-basics
- Reviewed: 2026-08-18
- Supports: crawl/render constraints for JavaScript applications and requirement that frontend architecture consider search rendering from the outset.
- Used by: ADR-0007, REQ-SEO-005.

### SRC-SEO-0003 — Canonicalization
- Publisher: Google Search Central
- Source type: official search-engine technical documentation
- URL: https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
- Reviewed: 2026-08-18
- Supports: preferred canonical URLs and duplicate consolidation.
- Used by: `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, REQ-SEO-004.

### SRC-SEO-0004 — Build and submit a sitemap
- Publisher: Google Search Central
- Source type: official search-engine technical documentation
- URL: https://developers.google.com/search/docs/crawling-indexing/sitemaps/build-sitemap
- Reviewed: 2026-08-18
- Supports: sitemaps should expose preferred canonical URLs.
- Used by: `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, REQ-SEO-004.

### SRC-SEO-0005 — Structured data introduction
- Publisher: Google Search Central
- Source type: official search-engine technical documentation
- URL: https://developers.google.com/search/docs/appearance/structured-data/intro-structured-data
- Reviewed: 2026-08-18
- Supports: structured data as a machine-readable representation of page content.
- Used by: `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, REQ-SEO-006.

### SRC-SEO-0006 — Core Web Vitals
- Publisher: web.dev / Google Chrome team
- Source type: official web performance guidance
- URL: https://web.dev/explore/learn-core-web-vitals
- Reviewed: 2026-08-18
- Supports: performance quality monitoring for public UX/search surfaces.
- Used by: `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`, REQ-SEO-007.

---

## OQ-001 — Derived metric authorities

### SRC-RATIO-0001 — Rustler Yachts: 3 useful formulas to help you choose a boat
- Publisher: Rustler Yachts
- Source type: manufacturer technical article
- URL: https://www.rustleryachts.com/useful-formulas-to-help-you-choose-a-boat/
- Reviewed: 2026-08-18
- Supports: Ballast/Displacement scope/caveats; D/L formula; SA/D formula; displacement-load and sail-area-basis cautions.
- Used by: OQ-001 research/spec/fixtures.

### SRC-RATIO-0002 — Ted Brewer Yacht Design
- Publisher/author: Ted Brewer
- Source type: naval architect technical reference
- URL: https://www.tedbrewer.com/yachtdesign.html
- Reviewed: 2026-08-18
- Supports: Brewer Comfort Ratio formula/caveat and CCA Capsize Screening Formula definition.
- Used by: OQ-001 research/spec.

### SRC-RATIO-0003 — U.S. Naval Academy EN400 hull-speed course material
- Publisher: U.S. Naval Academy, Department of Naval Architecture and Ocean Engineering
- Source type: official educational material
- URL: https://www.usna.edu/NAOE/_files/documents/Courses/EN400/02.07b%20Ch7%20PPT%20Slides.pptx
- Reviewed: 2026-08-18
- Supports: legacy displacement-hull speed/length relationship and hull-speed definition.
- Used by: OQ-001 research/spec.

### SRC-RATIO-0004 — NIST Guide to SI, Appendix B conversion factors
- Publisher: National Institute of Standards and Technology
- Source type: official metrology guidance
- URL: https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors
- Reviewed: 2026-08-18
- Supports: deterministic SI/non-SI conversion constants and conversion practice.
- Used by: OQ-001 research/spec.

---

## OQ-010 — Python/data-pipeline toolchain

### SRC-TOOL-0001 — Python 3.14 documentation
- Publisher: Python Software Foundation
- URL: https://docs.python.org/3.14/
- Reviewed: 2026-08-18
- Supports: Python 3.14 stable runtime baseline and stdlib capabilities.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0002 — uv project/workspace/locking documentation
- Publisher: Astral
- URL: https://docs.astral.sh/uv/concepts/projects/
- Reviewed: 2026-08-18
- Supports: pyproject workflow, uv.lock, dependency groups, managed environments and optional future workspaces.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0003 — Ruff documentation
- Publisher: Astral
- URL: https://docs.astral.sh/ruff/
- Reviewed: 2026-08-18
- Supports: Python 3.14-compatible formatter/linter baseline.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0004 — mypy documentation/release notes
- Publisher: mypy project
- URL: https://mypy.readthedocs.io/en/stable/
- Reviewed: 2026-08-18
- Supports: mature Python static type checking and Python 3.14 features/support.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0005 — pytest documentation
- Publisher: pytest project
- URL: https://docs.pytest.org/en/stable/
- Reviewed: 2026-08-18
- Supports: pytest 9.x and official Python 3.14 support.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0006 — coverage.py documentation
- Publisher: coverage.py project
- URL: https://coverage.readthedocs.io/
- Reviewed: 2026-08-18
- Supports: branch coverage and Python 3.14 support.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0007 — Hypothesis documentation
- Publisher: Hypothesis project
- URL: https://hypothesis.readthedocs.io/
- Reviewed: 2026-08-18
- Supports: property-based testing and Python 3.14 wheels/support.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0008 — python-jsonschema documentation
- Publisher: jsonschema project
- URL: https://python-jsonschema.readthedocs.io/en/stable/
- Reviewed: 2026-08-18
- Supports: Draft202012Validator / `$schema`-selected validation.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0009 — HTTPX documentation
- Publisher: Encode / HTTPX project
- URL: https://www.python-httpx.org/
- Reviewed: 2026-08-18
- Supports: typed sync/async HTTP, connection pooling, timeouts and resource limits.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0010 — Python sqlite3 documentation
- Publisher: Python Software Foundation
- URL: https://docs.python.org/3.14/library/sqlite3.html
- Reviewed: 2026-08-18
- Supports: lightweight serverless durable Stage-2 state and explicit transaction semantics.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0011 — Python asyncio TaskGroup documentation
- Publisher: Python Software Foundation
- URL: https://docs.python.org/3.14/library/asyncio-task.html
- Reviewed: 2026-08-18
- Supports: structured concurrency and TaskGroup safety semantics.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0012 — PyPA src-layout and dependency-groups guidance
- Publisher: Python Packaging Authority
- URL: https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/
- Reviewed: 2026-08-18
- Supports: src-layout rationale; standardized dependency groups are separately specified under PyPA.
- Used by: OQ-010 research / ADR-0009.

### SRC-TOOL-0013 — pip-audit
- Publisher: PyPA project
- URL: https://github.com/pypa/pip-audit
- Reviewed: 2026-08-18
- Supports: known-vulnerability auditing of Python dependencies, with documented security limitations.
- Used by: OQ-010 dependency-security baseline.

---

## SLICE-0002 — Design-data source research

The following entries support `docs/research/DESIGN_DATA_SOURCE_LANDSCAPE.md`, `research/DESIGN_DATA_FIELD_COVERAGE_MATRIX.md`, and `research/benchmark/SEED_RESEARCH_NOTES.md`. Classification here is research-oriented evidence metadata; it does not override `SOURCE_RIGHTS_POLICY.v0.1.md`.

### SRC-DSRC-0001 — Wikidata Sailboat Class data model / EntitySchema E297

- Publisher: Wikimedia / Wikidata community
- Source type: open structured-data model
- URLs: https://www.wikidata.org/wiki/Q106179098 ; https://www.wikidata.org/wiki/EntitySchema:E297 ; https://www.wikidata.org/wiki/Wikidata:WikiProject_Sailing/Data_Models/Sailboat_class
- Reviewed: 2026-08-18
- Rights/access: structured Wikidata data is CC0; API access remains subject to Wikimedia API/User-Agent/rate-limit rules.
- HullQ research classification: `BOOTSTRAP_CANDIDATE`.
- Supports: direct model/class identity; manufacturer/designer; qualified LOA/LWL/beam/draft/air-draft/displacement/ballast model; open four-digit bootstrap feasibility.
- Caveat: completeness/reference quality varies; generation/rudder/skeg depth is not solved by the schema.

### SRC-DSRC-0002 — Wikimedia Foundation API Usage Guidelines / User-Agent Policy

- Publisher: Wikimedia Foundation
- Source type: platform access policy
- URLs: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_API_Usage_Guidelines ; https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy
- Reviewed: 2026-08-18
- Supports: identifiable User-Agent, rate-limit/backoff, robot-policy and content-license compliance requirements for automated Wikimedia access.
- Used by: SLICE-0002 bootstrap-access assessment; future Wikidata adapter requirements.

### SRC-DSRC-0003 — Hallberg-Rassy previous-model and parts archives

- Publisher: Hallberg-Rassy
- Source type: manufacturer heritage / parts evidence
- URLs: https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-36 ; https://www.hallberg-rassy.com/yachts/previous-models/hallberg-rassy-42e
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: hull-number generation boundary, shallow-draft/rig options, displacement/sail-area source bases, retrospective model naming and cross-surface rudder/skeg evidence.
- Rights/access: factual verification permitted as research evidence; no blanket bulk crawl/redistribution clearance inferred.

### SRC-DSRC-0004 — Rustler Yachts design/measurement technical articles

- Publisher: Rustler Yachts
- Source type: manufacturer technical articles
- URLs: https://www.rustleryachts.com/keel-design-explained/ ; https://www.rustleryachts.com/yacht-measurements-explained/
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: explicit long-keel + keel-hung-rudder taxonomy; LOA/LWL ambiguity; lightship/half-load/full-load displacement distinction; differing sail-area conventions.
- Rights/access: no blanket bulk use assumed.

### SRC-DSRC-0005 — Alubat OVNI 370

- Publisher: Alubat
- Source type: manufacturer model specification
- URL: https://www.alubat.com/the-range/ovni-370/
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: aluminium construction, centreboard up/down draft, ballast vs keel/board mass semantics, mixed sail-area values.

### SRC-DSRC-0006 — Pogo Structures Pogo 1 archive

- Publisher: Pogo Structures
- Source type: manufacturer previous-model archive
- URL: https://www.pogostructures.com/fiche-bateau/pogo-1/?lang=en
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: twin rudders, historical build range/count, `light measurement trim` mass-basis terminology.

### SRC-DSRC-0007 — RM 1180 specification + configurator

- Publisher: RM Yachts
- Source type: manufacturer model page / live configurator
- URLs: https://www.rm-yachts.com/en/rm-1180/ ; https://www.rm-yachts.com/en/product/rm1180-2/
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: independent keel/rudder option axes; single/twin/lifting-keel and single/twin-rudder combinations; plywood-epoxy construction.
- Caveat: configurator state is volatile and requires timestamped evidence.

### SRC-DSRC-0008 — Garcia Exploration 45

- Publisher: Garcia Yachts
- Source type: manufacturer model specification / technical prose
- URL: https://www.garciayachts.com/en/sailsboats/exploration-45
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: aluminium centreboarder; twin rudders; each rudder preceded by a protective skeg; board-up/down draft and ballast.

### SRC-DSRC-0009 — Island Packet 349

- Publisher: Island Packet Yachts
- Source type: manufacturer specifications / construction / customization
- URLs: https://ipy.com/yachts/ip-349/ ; https://ipy.com/yachts/ip-349/specifications/ ; https://ipy.com/customization/
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: proprietary `Full Foil Keel®`, skeg-hung rudder, encapsulated lead ballast, branded terminology requiring lossless raw-term preservation.

### SRC-DSRC-0010 — Najad 34 official previous-model PDF

- Publisher: Najad
- Source type: manufacturer heritage PDF
- URL: https://najad.se/wp-content/uploads/2018/04/n34_productinformation-all-languages.pdf
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY`.
- Supports: long keel + separate skeg/rudder; production/history narrative.
- Critical finding: the same official multilingual PDF gives conflicting production counts (English/Swedish 354 vs German 352), proving primary-source internal conflicts require evidence-level resolution.

### SRC-DSRC-0011 — International J/24 Class / World Sailing class rules

- Publisher: International J/24 Class Association / World Sailing
- Source type: official class technical/rules documents
- URLs: https://j24class.org/about-the-j24/history/ ; https://j24class.org/rules-regulations/class-rules/
- Reviewed: 2026-08-18
- HullQ research classification: `PRIMARY_VERIFY` for class-rule constraints; not a broad bootstrap source.
- Supports: one-design identity, production breadth, class-rule/tolerance source shape and distinction between allowed geometry and nominal production value.

### SRC-DSRC-0012 — Westerly Owners Association / Westerly Wiki

- Publisher: Westerly Owners Association
- Source type: owner-association archive with historical manufacturer/designer material
- URL: https://wiki.westerly-owners.co.uk/index.php?title=Centaur
- Reviewed: 2026-08-18
- HullQ research classification: `SECONDARY_VERIFY` unless an underlying original document is separately cited.
- Supports: defunct-builder research path, twin-keel data, skegless spade-rudder prose, and a small internal production-count conflict.
- Rights/access: no bulk database reuse assumed.

### SRC-DSRC-0013 — Seafarer 26 technical review

- Publisher: Good Old Boat
- Source type: specialist technical secondary source
- URL: https://goodoldboat.com/seafarer-26/
- Reviewed: 2026-08-18
- HullQ research classification: `SECONDARY_VERIFY`.
- Supports: fin keel + rudder hung on partial skeg; defunct-builder construction detail; explicit warning that an earlier, different Seafarer 26 design existed.
- Rights/access: factual lead/verification only; no bulk reuse assumed.

### SRC-DSRC-0014 — ORC certificate database / published access surface

- Publisher: Offshore Racing Congress
- Source type: rating/certificate database
- URLs: https://orc.org/sailors/active-certificates-database ; https://data.orc.org/active
- Reviewed: 2026-08-18
- HullQ research classification: `BLOCKED` for systematic commercial HullQ ingestion under the terms reviewed during SLICE-0002 unless separate ORC permission/licence is obtained.
- Technical value: large structured measurement/certificate corpus with 14,000+ active certificates across 45 countries reported by ORC.
- Policy rule: public accessibility is not treated as production clearance.

### SRC-DSRC-0015 — sailboat-database.com

- Publisher: independent open-data web project
- Source type: mixed-source derived sailboat catalogue
- URL: https://sailboat-database.com/
- Reviewed: 2026-08-18
- HullQ research classification: `REFERENCE_ONLY`.
- Supports: current evidence that Wikimedia-derived sailboat data can produce a four-digit catalogue (1,062 indexed boats at review time).
- Rights caveat: site states data is sourced from Wikidata (CC0) and enriched from Wikipedia infoboxes (CC-BY-SA); HullQ should consume cleared Wikidata directly rather than bulk-copy the mixed derived database.
