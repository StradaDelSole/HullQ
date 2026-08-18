# ADR-0005 — Structured Source Rights and Use-Specific Clearance

**Status:** ACCEPTED  
**Date:** 2026-08-18  
**Related:** OQ-007, REQ-RESEARCH-005, SOURCE_RIGHTS_POLICY.v0.1

## Context

HullQ will combine open structured datasets, manufacturer/designer sources, manuals, archives and possibly licensed/permission-based sources. A single `rights_status`/`license_identifier` pair cannot safely decide whether a source may be used for research, discrete production facts, bulk bootstrap, automated extraction, or redistribution.

Legal and operational constraints also exist at different layers: data/database licensing, content copyright, API/website access terms, TDM reservations and project-specific risk decisions.

## Decision

Adopt a structured Source Rights Profile with five independent dimensions:

1. rights basis and license expression/scope;
2. access/automation conditions;
3. permissions and obligations;
4. supporting rights evidence/review metadata;
5. HullQ use-specific clearance.

Production and bulk ingestion are default-deny unless the relevant use is explicitly cleared.

Use SPDX identifiers/expressions when suitable and `LicenseRef-HullQ-*` for custom/private rights instruments.

Share-alike/mixed-license sources are quarantined from bulk canonical merge until compatibility is explicitly resolved.

Unlicensed primary factual sources may support discrete factual values conditionally, but are not automatically cleared for bulk/systematic extraction.

The TDM exception is not treated as a blanket production-data license.

## Consequences

### Positive

- rights decisions become machine-enforceable;
- open data can be bootstrapped without losing obligations;
- public-readable and automation-cleared are no longer conflated;
- share-alike/mixed sources cannot silently contaminate the publication/licensing strategy;
- source term changes can affect future ingestion while historical provenance remains intact;
- the pipeline can fail closed instead of relying on agent judgment.

### Costs

- Source records are more verbose;
- some sources require source-specific rights review;
- attribution/notice obligations need downstream support;
- source extraction telemetry becomes part of pipeline operations.

## Rejected alternatives

### One `rights_status` field

Rejected because it cannot express a source that is open for reuse but restricted in access method, or cleared for research but not bulk ingestion.

### Treat all public facts as unrestricted

Rejected because database rights, repeated/systematic extraction, content rights and contractual/access restrictions operate independently from the factual nature of individual values.

### Ban all unlicensed web sources

Rejected because authoritative primary webpages/manuals are essential factual evidence and can support carefully scoped independent research without implying bulk-copy rights.

### Rely on TDM exceptions for the pipeline

Rejected as an overly broad legal assumption and poor basis for a low-risk commercial data asset.

## Follow-up / implementation consequences

1. mark OQ-007 `DECIDED`;
2. promote `SOURCE_RIGHTS_POLICY.v0.1.md` to accepted v0.1;
3. promote/finalize Source schema v0.2;
4. unblock REQ-RESEARCH-005;
5. feed rights fields into OQ-004 provenance persistence and OQ-010 pipeline design;
6. create source-specific clearance records before any broad bootstrap ingestion.
