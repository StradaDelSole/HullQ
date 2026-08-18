# OQ-007 Research — Source Rights / Licensing Metadata

**Status:** COMPLETE FOR DECISION  
**Open question:** OQ-007  
**Date:** 2026-08-18  
**Purpose:** Determine the minimum source-rights model required before HullQ performs open-data bootstrap or scaled automated research.

> This document is engineering/legal-risk research, not legal advice. Source-specific commercial use can still require professional legal review.

## 1. Problem

The current `SOURCE_SCHEMA.v0.1.json` reduces source-rights state to `rights_status` plus one `license_identifier`. That is insufficient for HullQ.

A source can simultaneously have:

- an open copyright/database license;
- separate API/access conditions;
- attribution or share-alike obligations;
- machine-readable reservations against text/data mining;
- permission for individual factual reuse but no permission for bulk extraction;
- mixed licensing between database structure, database contents, text and media;
- source-specific contractual restrictions independent of IP-license scope.

HullQ therefore needs to distinguish **rights basis**, **license scope**, **access conditions**, **permissions/obligations**, and **project clearance by use case**.

## 2. Legal/risk baseline relevant to the engineering model

### 2.1 Facts and databases are different layers

Individual technical facts may not themselves be protected by copyright, while the source database, selection/arrangement, expressive text, images, drawings and database-maker investment can carry separate rights.

EU Directive 96/9/EC creates a sui-generis database right protecting qualifying substantial investment independently from copyright in the database or its contents. It also prohibits certain repeated/systematic extraction or re-utilization of insubstantial parts when that conflicts with normal exploitation or unreasonably prejudices the maker.

Austria implements database protection in §§ 76c ff UrhG. § 76c requires a substantial investment in obtaining, verifying or presenting database contents; § 76d governs database-maker rights and duration.

**Engineering consequence:** HullQ MUST NOT infer “fact is public” ⇒ “bulk source extraction is cleared.”

### 2.2 Publicly readable is not the same as cleared for automation/reuse

A webpage being reachable without authentication does not itself establish permission for bulk automated access, storage, commercial reuse or redistribution.

**Engineering consequence:** access conditions and reuse rights MUST be modeled separately.

### 2.3 Text/data-mining exceptions are not a general production-data license

Directive (EU) 2019/790 Article 4 provides an exception/limitation for reproductions and extractions of lawfully accessible material for text/data mining, subject to rights not having been expressly reserved in an appropriate manner. Copies may be retained only as long as necessary for TDM purposes.

The Directive specifically recognizes machine-readable reservation mechanisms for public online material.

**HullQ policy recommendation:** do not treat a TDM exception as blanket permission to publish/reuse extracted source content or as a substitute for source-specific production-data clearance. TDM status is evidence relevant to automated research, not the sole basis for commercial canonical-data ingestion.

### 2.4 Open licenses differ materially

Creative Commons 4.0 licenses can cover applicable sui-generis database rights. CC0 is designed to waive copyright and database rights as far as possible. CC BY requires attribution when licensed rights are exercised. CC BY-SA adds share-alike obligations to relevant adaptations/databases. Open Data Commons provides database-specific licenses including PDDL, ODC-By and ODbL.

**Engineering consequence:** an SPDX-style license identifier is useful, but the pipeline also needs obligation and clearance fields.

### 2.5 Mixed-license datasets require care

A dataset may combine database-level rights with separately licensed or third-party contents. Open Data Commons explicitly distinguishes rights in a database from rights in individual contents. Creative Commons likewise notes that a database provider may not own every content right.

**Engineering consequence:** `license_expression` MUST NOT be assumed to apply to every element unless scope is recorded.

## 3. Bootstrap-source examples

### Wikidata

Wikidata states that its data is available under CC0. It is therefore a strong candidate for broad identity/common-fact bootstrap, subject to its technical access policies and ordinary provenance/quality validation.

Recommended default project clearance:

- research reference: ALLOWED
- research lead: ALLOWED
- identity seed: ALLOWED
- production factual value: ALLOWED
- bulk bootstrap: ALLOWED
- automated ingestion: CONDITIONAL on approved access method/rate policy
- redistribution of Wikidata source artifacts: only according to the applicable source/access policy; HullQ normally stores canonical facts, not source dumps in Git

### Wikipedia text/infobox material

Wikimedia text is licensed under CC BY-SA (current Terms of Use use CC BY-SA 4.0 for new text, with legacy/history nuances), while Wikidata remains CC0. Wikipedia also contains imported and separately licensed material.

Recommended default project clearance:

- research reference: ALLOWED
- research lead: ALLOWED
- individual factual evidence: CONDITIONAL
- bulk bootstrap into HullQ canonical data: LEGAL_REVIEW_REQUIRED / source-specific review
- copied expressive text: NOT part of HullQ production-data strategy

HullQ SHOULD prefer Wikidata or primary/open sources over bulk reuse of Wikipedia text/infoboxes when equivalent factual data exists.

## 4. Required conceptual separation

### 4.1 Rights basis

Why does HullQ believe a use may be lawful/permitted?

Proposed values:

- `public_domain`
- `standard_license`
- `custom_license`
- `explicit_permission`
- `statutory_exception`
- `unlicensed_factual_reference`
- `mixed`
- `unknown`

### 4.2 License expression

When a standard identifier exists, use an SPDX license expression/identifier, for example:

- `CC0-1.0`
- `CC-BY-4.0`
- `CC-BY-SA-4.0`
- `PDDL-1.0`
- `ODbL-1.0`

Custom agreements use a HullQ `LicenseRef-*` identifier plus a contract/document reference; confidential agreements themselves need not be stored in the repository.

### 4.3 License scope

Track what the asserted license actually covers:

- database structure
- database contents
- individual content
- text
- media
- unknown/mixed

### 4.4 Access conditions

Track separately:

- access method;
- terms URL/review date;
- automated-access state;
- machine-readable TDM reservation state;
- rate/access notes.

### 4.5 Permissions / obligations

Tri-state/quad-state permissions are required because “not checked” is different from “prohibited.”

Relevant permissions:

- commercial use;
- extracting factual values;
- normalization/transformation;
- storing canonical values;
- bulk ingestion;
- automated extraction;
- redistributing source material;
- publishing a derived/combined database.

Relevant obligations:

- attribution;
- share-alike;
- notice/license-link;
- source-specific conditions.

### 4.6 HullQ clearance by use case

Legal/license facts are not the same thing as a HullQ engineering decision. Each source therefore needs a project clearance for:

- `research_reference`
- `research_lead`
- `identity_seed`
- `production_value`
- `bulk_bootstrap`
- `automated_ingestion`
- `artifact_redistribution`

Clearance values:

- `allowed`
- `conditional`
- `legal_review_required`
- `prohibited`
- `unknown`

## 5. Conservative default policy by source class

### Green / generally production-usable after ordinary validation

- verified `CC0-1.0`;
- verified `PDDL-1.0`;
- verified public-domain source where the relevant status/scope is documented;
- explicit commercial permission/license that grants the needed operations.

Access/API rules still apply independently.

### Green-with-obligations

- `CC-BY-4.0` or equivalent attribution license, **only** when scope covers the reused material and HullQ's attribution mechanism can satisfy the obligation.

### Amber / compatibility review before bulk merge

- `CC-BY-SA-4.0`;
- `ODbL-1.0`;
- ODC attribution/share-alike combinations;
- mixed-license datasets;
- NoDerivatives licensing where an adaptation/derived database may be implicated;
- custom/open-government licenses not yet mapped to HullQ use cases.

These are not “bad” sources. They are sources whose obligations can affect the licensing or publication of a combined HullQ database and therefore MUST NOT be silently merged at scale.

### Red for commercial production reliance

- NonCommercial licensing when HullQ's use relies on the licensed rights;
- explicit commercial-reuse prohibition;
- explicit prohibited automated access for an automated ingestion path;
- expired/revoked permission;
- unknown rights for bulk bootstrap;
- sources explicitly classified as project-reference-only.

### Primary factual reference with no explicit open license

Manufacturer/designer/manual pages often sit here.

Default:

- research reference: allowed;
- research lead: allowed;
- discrete factual production values: conditional, provided HullQ records provenance, avoids expressive copying, and does not use the source as an unreviewed bulk database extraction mechanism;
- bulk bootstrap: prohibited until source-specific rights/access review;
- automated ingestion: unknown/prohibited until terms/access/TDM reservation are assessed.

This is deliberately stricter than “anything public can be scraped” and less restrictive than “an unlicensed webpage can never support a factual value.”

## 6. SailboatData reference scrape

The historical scrape remains:

```text
REFERENCE / PROTOTYPE ONLY
NOT PRODUCTION DATA
```

Under OQ-007 it SHOULD receive explicit clearances:

- research reference: allowed
- research lead: conditional
- identity seed directly into canonical production: prohibited
- production technical value: prohibited
- bulk bootstrap: prohibited
- automated re-extraction: prohibited unless a later explicit legal/license decision supersedes this

A model identity discovered there MAY create a research lead, but canonical identity/value acceptance MUST be independently supported by cleared sources.

## 7. Automation rules

The future pipeline SHOULD be default-deny for production ingestion:

1. Source has no rights assessment → may be evidence/research only.
2. Required use clearance is not `allowed` or satisfied `conditional` → production write rejected.
3. Share-alike/mixed/custom source without resolved compatibility → quarantine/review.
4. Automated access not cleared → no automated fetch even if reuse license is open.
5. Source extraction volume SHOULD be measurable by source so that a low-volume factual-reference workflow cannot silently become bulk/systematic extraction.
6. Rights/terms changes MUST be able to invalidate future ingestion without deleting historical provenance.

## 8. Recommended decision

Adopt:

1. a structured Source Rights Profile;
2. use-specific HullQ clearance;
3. default-deny production/bulk behavior;
4. SPDX identifiers where suitable, plus `LicenseRef-*` for custom terms;
5. separate access and reuse assessments;
6. conditional factual use of unlicensed primary sources, but no unreviewed bulk extraction;
7. share-alike/mixed-license quarantine until compatibility is explicitly decided;
8. no reliance on TDM exceptions as the sole production-data legal basis;
9. source-level extraction telemetry for non-open sources;
10. preservation of rights-evidence metadata and review date.

## 9. External authorities consulted

See `research/evidence/SOURCE_REGISTER.md` for registered URLs and review dates, including:

- Directive 96/9/EC (EU Database Directive);
- Directive (EU) 2019/790 Article 4 (TDM);
- Austrian UrhG §§ 42h, 76c–76e;
- Creative Commons database/data guidance and CC0/CC BY 4.0 legal material;
- Open Data Commons ODbL/PDDL materials;
- SPDX License List;
- Wikidata licensing/data-access documentation;
- Wikimedia Terms of Use.
