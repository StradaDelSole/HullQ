# SLICE-0007 — ResearchJob and Source-Rights Gate

**ID:** SLICE-0007  
**Type:** IMPLEMENTATION  
**Status:** READY  
**Stage:** 2.6 — deterministic rights/use gate before real external acquisition  
**Depends on:** SLICE-0006 accepted / DONE  
**Blocks:** SLICE-0008

## Objective

Implement the minimum persistence-agnostic runtime that makes HullQ's accepted ResearchJob and Source Rights contracts executable before any real network acquisition is introduced.

This slice must make a source-use decision deterministic and fail-closed:

```text
validated Source record
        +
requested HullQ use
        +
access / permission / clearance state
        +
optional source-usage telemetry context
        ↓
SourceUseDecision
        ↓
ALLOW
or
BLOCK / REVIEW / CONDITIONAL
```

A later adapter must not be able to fetch automatically, bulk-bootstrap, or emit a production value merely because a source is public, has an open license, or was useful as a research lead.

SLICE-0008 will be the first real external adapter. SLICE-0007 itself performs no HTTP/API/PDF/HTML acquisition.

## Controlling artifacts

- `specs/REQUIREMENTS.md`:
  - `REQ-RESEARCH-001` through `REQ-RESEARCH-009`;
  - especially `REQ-RESEARCH-005` through `REQ-RESEARCH-009`;
  - `REQ-DATA-002`, `REQ-DATA-009`;
  - `REQ-PROV-007`.
- `architecture/decisions/ADR-0005-source-rights-clearance.md`.
- `specs/SOURCE_RIGHTS_POLICY.v0.1.md`.
- `specs/SOURCE_SCHEMA.v0.2.json`.
- `specs/RESEARCH_JOB_SCHEMA.v0.1.json`.
- `fixtures/sources/source_rights_cases.v0.1.json`.
- `research/RESEARCH_WORKFLOW.md`.
- `docs/research/OQ-007_SOURCE_RIGHTS_RESEARCH.md`.
- SLICE-0006 provenance runtime, especially Source → FieldEvidence → FieldResolution reverse-impact lookup.

## Core semantic rules

1. **Access is not reuse.** Public readability, API access and automated-access conditions remain independent from copyright/database/license reuse and HullQ clearance.
2. **Clearance is use-specific.** Research reference, research lead, identity seed, production value, bulk bootstrap, automated ingestion and artifact redistribution are separate decisions.
3. **Production and bulk fail closed.** `unknown`, `unassessed`, `legal_review_required`, `prohibited` or unresolved `conditional` state must never silently become permission.
4. **Conditional is not automatically allowed.** This slice MUST NOT invent a generic boolean bypass such as `conditions_satisfied=True`. If a Source record remains `conditional` for the requested use, the deterministic gate returns a non-allow outcome. A later reviewed/versioned Source decision may promote that use to `allowed` when its conditions have actually been resolved.
5. **Underlying prohibitions still matter.** A use-specific `allowed` clearance MUST NOT override an explicit incompatible access/permission prohibition in the same Source record.
6. **Open license does not override access restrictions.** For automated ingestion, technical/access automation state is checked independently.
7. **No hidden source prestige.** Rights clearance decides whether a source may participate in an operation; it does not rank factual authority or resolve evidence conflicts.
8. **Historical provenance is not deleted.** A rights change blocks/re-routes future use and can identify affected evidence/resolutions; it does not rewrite historical FieldEvidence.
9. **Cumulative extraction is explicit.** For automated use of a source that is not bulk-cleared, request/extraction volume must be measurable and compared with a caller-supplied configured threshold. No magic project-wide threshold is invented here.
10. **ResearchJob remains operational metadata.** Manufacturer/model/first-built input stays in the minimal target; workflow state does not leak into canonical identity.

## In scope

### 1. ResearchJob runtime representation

Add a focused runtime module under `src/hullq/research/` for the accepted `RESEARCH_JOB_SCHEMA.v0.1` contract.

Represent at least:

- `ResearchTarget` with exactly `manufacturer`, `model`, `first_built`;
- `ResearchJobStatus` matching the schema vocabulary:
  - `pending`
  - `researching`
  - `needs_review`
  - `conflict`
  - `complete`
  - `blocked`;
- `ResearchJob` operational metadata required by the existing schema.

The implementation must preserve caller-owned input snapshots and validate obvious contract invariants such as non-empty `job_id`, non-empty model and non-negative requested count.

Do **not** invent a broad workflow engine or undocumented transition graph. The accepted specs define the state vocabulary and completion outcomes but do not yet normatively define every legal status-to-status edge. A small helper MAY classify terminal/review states, but must not fabricate business semantics.

Do not replace or silently modify `RESEARCH_JOB_SCHEMA.v0.1.json` unless a concrete incompatibility is found and documented during implementation. Prefer runtime parity with the accepted v0.1 contract.

### 2. Source-use vocabulary and deterministic decision object

Add a focused module under `src/hullq/sources/`, preferably `rights.py`, containing only the runtime needed by the next acquisition slice.

Define source uses matching the accepted Source clearance keys exactly:

```text
research_reference
research_lead
identity_seed
production_value
bulk_bootstrap
automated_ingestion
artifact_redistribution
```

Expose a deterministic decision/result object that distinguishes at least:

- allowed;
- blocked/prohibited;
- legal review required;
- conditional/unresolved;
- unknown/unassessed.

The result must provide machine-readable reason codes. Human-readable text may accompany them, but callers/tests must not parse prose to decide behavior.

### 3. Fail-closed use-specific clearance gate

Implement a pure gate over an already schema-valid Source record or a narrowly typed equivalent.

At minimum:

- `allowed` clearance may proceed only if no independently relevant access/permission field explicitly contradicts it;
- `prohibited` blocks;
- `legal_review_required` routes to review / does not allow;
- `conditional` does not allow automatically in this slice;
- `unknown` does not allow production, bulk, automation or artifact redistribution;
- an `unassessed` rights profile cannot authorize those operations;
- the gate never infers permission from `license_expression`, publisher name, source type or public accessibility alone.

Research-reference/research-lead decisions may reflect the explicit clearance recorded in the Source profile, but the runtime must still return the actual non-allow state when that clearance is conditional/unknown rather than coercing it to `allowed`.

### 4. Independent access checks for automated ingestion

For `automated_ingestion`, the gate must separately check the accepted access/automation state.

At minimum:

- explicit automated-access `prohibited` blocks;
- automated-access `unknown` does not authorize automation;
- automated-access `conditional` remains non-allow until the reviewed Source record expresses an allowed state for the concrete approved access method;
- an open/production-cleared license does not override an automation prohibition.

Do not make network requests or implement robots.txt/API-rate-limit clients here.

### 5. Relevant permission conflict checks

Use the Source Rights Profile's permissions as defensive consistency checks rather than as a second hidden policy engine.

Examples that must fail closed:

- `production_value=allowed` while `store_canonical_values=prohibited`;
- bulk bootstrap requested while `bulk_ingest=prohibited`;
- automated ingestion requested while `automated_extract=prohibited`;
- artifact redistribution requested while `redistribute_source_material=prohibited`;
- commercial production reliance where `commercial_use=prohibited`.

Do not automatically promote an operation merely because a low-level permission is `allowed`; HullQ use-specific clearance remains required.

### 6. Obligation visibility

A successful or non-successful gate result must be able to surface machine-addressable obligations already present in the Source contract, especially:

- attribution required;
- notice required;
- share-alike state;
- attribution instructions/reference where present.

This slice does not implement the eventual public attribution UI or licensing strategy.

An unresolved share-alike/mixed/legal-review condition must not be silently transformed into an allowed bulk/publication decision.

### 7. Source-level activity telemetry primitive

Implement a persistence-agnostic telemetry/value-object helper for `REQ-RESEARCH-008`.

It must support source-level aggregation of at least:

- retrieval/request count;
- extracted record/value count.

Counts must be non-negative, deterministic and attributable to a stable `source_id`.

For a source that is **not** cleared for bulk bootstrap, an automated acquisition caller must be able to provide a configured threshold/limit and ask whether the projected cumulative usage remains below it.

Rules:

- threshold is supplied explicitly by configuration/caller; do not invent a numeric default;
- crossing/equaling the configured block/review boundary must return a deterministic non-allow outcome as specified by the helper contract;
- absence of required telemetry/limit context for a non-bulk-cleared automated source must fail closed rather than silently assuming low volume;
- bulk-cleared sources may still be measured, but this slice does not impose an arbitrary low-volume cap on them.

Do not persist telemetry to PostgreSQL/SQLite in this slice.

### 8. ResearchJob + rights-gate integration helper

Provide a small pure helper showing how a source-use decision maps to ResearchJob handling without mutating canonical data.

At minimum it must be possible for a caller to distinguish:

- continue research;
- route job to `needs_review`;
- route job to `blocked`.

Do not automatically mark a job `complete` merely because a rights gate passes; factual extraction, provenance, normalization and validation happen later.

### 9. Rights-change provenance impact integration

Use the SLICE-0006 reverse lookup boundary in at least one integration test:

```text
Source rights/use becomes blocked or review-required
        ↓
source_id
        ↓
FieldEvidence
        ↓
current/past FieldResolution impact enumeration
```

The test must prove affected evidence/resolutions can be identified without deleting or mutating the historical evidence records.

The actual canonical re-resolution workflow/persistence remains out of scope.

### 10. Existing source-rights fixtures as executable policy cases

Turn the existing synthetic `fixtures/sources/source_rights_cases.v0.1.json` cases into executable runtime tests where applicable.

The gate must preserve the accepted distinctions represented by those fixtures, including:

- CC0/open data can be production/bulk usable while automation remains independently conditional;
- CC BY can carry attribution/notice obligations;
- share-alike/ODbL bulk use remains legal-review-required where recorded;
- unlicensed primary factual reference can be useful for research/discrete factual review while bulk/automation remain restricted;
- NonCommercial source is not acceptable for HullQ commercial production reliance;
- unknown-rights source fails closed for production/bulk;
- historical reference scrape does not become production/bulk input.

Do not edit fixture outcomes to make tests easier.

## Explicitly out of scope

Do not implement:

- Wikidata or any other real HTTP/API adapter;
- HTTPX requests, retries, rate limiting or robots/terms fetching;
- automatic rights/legal classification from a URL/license string;
- legal advice or source-specific legal conclusions not already represented in accepted Source metadata;
- generic `conditions_satisfied=True` bypasses;
- source-authority scoring/ranking;
- evidence conflict resolution policy;
- persistence, ORM or migrations;
- broad ingestion;
- canonical BoatDesign/BoatModel writes;
- appendage/configuration normalization;
- derived metrics;
- FastAPI/frontend;
- private reference boat-list contents.

## Required synthetic fixtures/tests

Use only repository-safe synthetic/public contract fixtures.

Cover at least:

1. ResearchTarget contains only manufacturer/model/first-built identity input.
2. ResearchJob status vocabulary matches `RESEARCH_JOB_SCHEMA.v0.1`.
3. invalid empty job/model and negative requested count are rejected.
4. Source-use enum matches the seven Source clearance keys.
5. `production_value=allowed` on an assessed compatible source can allow production use.
6. `production_value=unknown` fails closed.
7. `production_value=prohibited` blocks.
8. `production_value=legal_review_required` routes to review.
9. `production_value=conditional` does not auto-allow.
10. `bulk_bootstrap=allowed` and compatible permissions can allow bulk use.
11. `bulk_bootstrap=unknown/prohibited/legal_review_required/conditional` does not auto-allow.
12. automated ingestion is blocked when automated access is prohibited even if reuse/production clearance is open.
13. automated ingestion is not allowed when automated access is unknown or unresolved conditional.
14. explicit permission conflict such as production clearance allowed + canonical-storage permission prohibited fails closed.
15. CC BY fixture exposes attribution/notice obligations.
16. share-alike fixture does not silently pass bulk/publication use.
17. NonCommercial fixture does not pass commercial production use.
18. unknown-rights fixture cannot authorize production/bulk.
19. historical reference-scrape fixture cannot authorize production/bulk/automation.
20. an allowed low-level permission without matching HullQ use-specific clearance does not allow the operation.
21. request/extraction telemetry aggregates by source ID.
22. negative telemetry values are rejected.
23. configured non-bulk extraction threshold can produce a deterministic continue vs review/block result.
24. missing required telemetry/threshold context for non-bulk-cleared automated use fails closed.
25. bulk-cleared source is not subjected to an invented low-volume cap.
26. rights-gate outcome can route a ResearchJob to continue/needs_review/blocked without marking it complete.
27. Source → FieldEvidence → FieldResolution impact lookup still enumerates historical impact after a source is newly blocked.
28. no public API in this slice performs network acquisition or automatically grants rights from source prestige/license name alone.

Property-based tests SHOULD be used for non-negative usage aggregation or gate-state matrices where they improve confidence without hiding policy semantics.

## Deliverables

Expected touch points:

- `src/hullq/research/jobs.py`;
- `src/hullq/sources/rights.py`;
- focused unit/contract tests;
- existing source-rights fixtures reused without semantic weakening;
- optional small synthetic telemetry fixture if useful;
- registry changes only if an actually necessary successor schema is introduced;
- `docs/slices/SLICE-0007-research-job-source-rights-gate.md` status update to `REVIEW` or `BLOCKED` at implementation handoff;
- `docs/slices/INDEX.md` handoff update.

Avoid unrelated files.

## Acceptance criteria

- [ ] ResearchJob runtime matches the accepted v0.1 contract without inventing an undocumented workflow engine.
- [ ] all seven use-specific Source clearances are executable through one deterministic gate boundary.
- [ ] production, bulk, automation and redistribution fail closed for unknown/unassessed/review/prohibited/unresolved-conditional states.
- [ ] automated access is checked independently from reuse/production clearance.
- [ ] explicit permission contradictions fail closed rather than being overridden by project clearance.
- [ ] obligations remain machine-visible in gate outcomes.
- [ ] source-level request/extraction telemetry supports a caller-configured cumulative extraction boundary for non-bulk-cleared automated research.
- [ ] missing required non-bulk automation telemetry context fails closed.
- [ ] rights-gate outcomes can route ResearchJob handling without falsely completing the job.
- [ ] SLICE-0006 provenance impact lookup is integrated without historical evidence mutation.
- [ ] accepted source-rights fixtures retain their semantic outcomes.
- [ ] no network acquisition, persistence, source-authority ranking or canonical write path is introduced.
- [ ] repository validator, Ruff, strict mypy, pytest/branch coverage and dependency audit pass locally.
- [ ] required remote CI is observed independently and reported truthfully before project-owner acceptance.

## Implementation-agent handoff

When implementation is complete:

1. run all required local gates;
2. push the same `slice/0007-research-job-source-rights-gate` branch;
3. leave this slice in `REVIEW` or `BLOCKED`;
4. report exact head SHA and local results truthfully;
5. do not start SLICE-0008;
6. do not merge to `main`.
