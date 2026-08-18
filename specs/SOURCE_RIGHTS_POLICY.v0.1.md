# HullQ Source Rights Policy v0.1

**Status:** ACCEPTED — OQ-007 DECIDED  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This policy governs whether and how an external source may participate in HullQ research, canonical production data, broad bootstrap ingestion, automated extraction, and repository/source-artifact redistribution.

It is a conservative engineering policy, not a legal opinion.

## 2. Core principles

### SR-001 — Separate access from reuse

HullQ MUST model source access/automation conditions separately from copyright/database/license reuse permissions.

### SR-002 — Use-specific clearance

A source MUST have explicit HullQ clearance for each relevant use. A source being suitable for research reference MUST NOT imply that it is cleared for production values, bulk bootstrap, automated ingestion or redistribution.

### SR-003 — Default deny for production/bulk

If the relevant clearance is `unknown`, production write/bulk ingestion MUST be rejected and routed to review.

### SR-004 — Facts do not imply database extraction rights

The factual nature of an individual value MUST NOT be treated as permission to copy, systematically extract or re-utilize a protected/restricted database.

### SR-005 — No TDM shortcut

A statutory text/data-mining exception MUST NOT by itself be treated as sufficient clearance to publish/reuse extracted source content in HullQ's production database. Any reliance on a statutory exception MUST be explicitly recorded and reviewed for the intended downstream use.

### SR-006 — Rights evidence is versioned provenance

A rights determination MUST retain review date and supporting evidence references. Later source-term changes MAY change future clearance without deleting historical provenance.

### SR-007 — Minimal source copying

HullQ SHOULD store only the source evidence necessary for audit and SHOULD NOT vendor third-party copyrighted pages/documents into the repository unless redistribution rights are established.

### SR-008 — Cumulative extraction matters

For sources not cleared for bulk ingestion, automated research MUST be capable of tracking source-level extraction/request volume so that repeated per-record actions do not silently become systematic bulk extraction.

## 3. Rights basis vocabulary

A Source Rights Profile MUST use one of:

- `public_domain`
- `standard_license`
- `custom_license`
- `explicit_permission`
- `statutory_exception`
- `unlicensed_factual_reference`
- `mixed`
- `unknown`

## 4. License identifiers

When a recognized SPDX identifier/expression exists, HullQ SHOULD use it verbatim.

Examples include `CC0-1.0`, `CC-BY-4.0`, `CC-BY-SA-4.0`, `PDDL-1.0` and `ODbL-1.0`.

A non-standard/private agreement SHOULD use `LicenseRef-HullQ-*` plus a stable contract/document identifier. Confidential contract text MUST NOT be committed merely to satisfy metadata requirements.

## 5. Clearance vocabulary

Per-use clearances are:

- `allowed`
- `conditional`
- `legal_review_required`
- `prohibited`
- `unknown`

The Source record MUST support clearances for:

- research reference;
- research lead;
- identity seed;
- production value;
- bulk bootstrap;
- automated ingestion;
- artifact redistribution.

## 6. Standard source-class policy

### 6.1 CC0 / PDDL / verified public domain

These MAY be approved for commercial production values and bulk bootstrap when:

- the asserted license/public-domain status applies to the reused element;
- access conditions are separately satisfied;
- source provenance is retained.

HullQ SHOULD retain attribution/provenance internally even when the license does not require attribution.

### 6.2 CC BY

CC BY sources MAY be approved for commercial production/bulk use when:

- scope covers the reused material;
- attribution obligations are captured and can be fulfilled;
- any source-specific access conditions are satisfied.

### 6.3 Share-alike database/content licenses

CC BY-SA, ODbL and comparable share-alike sources MUST default to `legal_review_required` for bulk merge into HullQ's canonical/public database until a project licensing/compatibility decision determines how resulting obligations will be satisfied.

They MAY still be used as research references where that use is lawful and clearance permits it.

### 6.4 NonCommercial / explicit commercial prohibition

A source whose relevant licensed rights are limited to non-commercial use MUST NOT be relied upon for HullQ commercial production use unless a separate permission/legal basis is documented.

### 6.5 NoDerivatives / mixed licenses

NoDerivatives or mixed-license sources MUST default to `legal_review_required` for derived/combined database use unless the exact intended operation has been cleared.

### 6.6 Unlicensed primary factual sources

A manufacturer/designer/manual source without an explicit open license MAY support discrete factual values under `conditional` production clearance when all of the following hold:

1. the source is lawfully accessible;
2. the reused element is recorded as a discrete factual/technical value rather than copied expressive text/media;
3. provenance is recorded;
4. source terms/access restrictions do not prohibit the chosen research method;
5. the source is not used as an unreviewed systematic/bulk database extraction mechanism;
6. automated access, when used, has separate clearance.

Bulk bootstrap from such a source MUST remain prohibited or legal-review-required until source-specific clearance exists.

### 6.7 Unknown rights

Unknown rights MAY support discovery/research reference where lawful, but MUST NOT authorize production values or bulk bootstrap.

## 7. Wikidata baseline

Wikidata data under CC0 SHOULD be treated as an approved candidate for identity/common-fact bootstrap, subject to technical access rules and normal data-quality/provenance validation.

This policy does not imply that Wikidata values are authoritative; it only addresses rights/clearance.

## 8. Wikipedia baseline

Wikipedia/Wikimedia text MUST NOT be treated as equivalent to Wikidata CC0 data.

Wikipedia MAY be used as research evidence/lead material. Bulk canonical ingestion from Wikipedia text/infobox material MUST remain conditional/legal-review-required unless the exact reuse and attribution/share-alike implications are resolved.

## 9. Historical SailboatData scrape

The historical scrape MUST remain reference/prototype-only.

It MUST NOT supply canonical technical values, bulk bootstrap values, or direct canonical identity acceptance.

It MAY create a research lead only when the resulting identity/value is independently verified from cleared evidence before production acceptance.

## 10. Pipeline enforcement contract

Before any production write originating from a source, the pipeline MUST verify:

1. a rights assessment exists;
2. `production_value` clearance is `allowed` or all stated `conditional` requirements are satisfied;
3. if ingestion is automated, `automated_ingestion` is separately cleared;
4. if the source is being consumed in bulk, `bulk_bootstrap` is separately cleared;
5. required attribution/notice metadata is retained;
6. unresolved share-alike/mixed/custom obligations are routed to review.

A failed rights gate MUST be a normal deterministic pipeline outcome, not an exception that an agent works around.

## 11. Repository policy

External source files MUST NOT be committed to `reference/` merely because they were used as evidence.

A source artifact MAY be vendored only when:

- redistribution/storage rights are established;
- its license/rights metadata is recorded;
- retaining the local copy materially improves reproducibility.

Otherwise HullQ MUST store citation metadata and, where appropriate, a non-expressive fingerprint/hash rather than an unauthorized copy.

## 12. Acceptance criteria for OQ-007

OQ-007 is satisfied when:

- this policy is ACCEPTED;
- `SOURCE_SCHEMA.v0.2` represents the required rights profile;
- source-rights contract fixtures validate;
- `REQ-RESEARCH-005` is unblocked;
- broad bootstrap code is still prevented until OQ-010/code implementation and the per-source clearances exist.
