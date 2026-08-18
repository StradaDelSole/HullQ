# HullQ — Quality Gates

**Status:** ACCEPTED

No phase advances because "the code basically works". Each phase has explicit exit criteria.

## Gate G0 — Documentation-ready

A coding task may begin only when:

- relevant requirement IDs exist;
- required decisions are resolved or explicitly non-blocking;
- acceptance criteria are testable;
- affected schemas/contracts are defined;
- test fixtures/examples exist for non-trivial domain behavior.

## Gate G1 — Local implementation quality

Before a change is considered complete:

- dependency lock is current and locked sync succeeds where dependencies changed;
- formatting/linting passes;
- static/type checks pass where configured;
- unit/domain tests pass;
- schema validation passes;
- no unresolved test skips hide required behavior;
- changed behavior is traceable to requirements.

## Gate G2 — Integration quality

Before merging functionality across boundaries:

- contract tests pass;
- persistence migrations are tested where relevant;
- integration tests pass using controlled data;
- error/unknown/conflict paths are tested, not only happy paths.

## Gate G3 — Data-pipeline release

Before scaling research ingestion:

- benchmark corpus passes agreed accuracy/consistency thresholds;
- automatic acceptance and review-routing behavior are measured;
- per-design cost/time is measured;
- source-rights metadata behavior and use-specific clearance gates are implemented;
- production/bulk ingestion fails closed for unknown or uncleared source rights;
- attribution/share-alike/notice obligations survive ingestion;
- raw input immutability is verified;
- reruns are idempotent or explicitly versioned;
- failures resume safely without corrupting accepted records.

## Gate G4 — Broad-ingestion readiness

Before thousands of identities are processed:

- identity/generation/variant rules are stable enough for scale;
- duplicate/near-duplicate detection exists;
- provenance is field-addressable;
- validation/review queues work;
- throughput and estimated total cost are acceptable;
- backup/recovery and dataset snapshot/version strategy exist.

## Gate G5 — Query-engine readiness

Before public technical search:

- unknown-data semantics are explicitly specified;
- confirmed match / confirmed non-match / insufficient-data behavior is tested;
- core filters are backed by enough coverage to avoid obviously misleading results;
- filter behavior is deterministic and explainable;
- ratio formula version is stable and tested;
- the technical query contract is decoupled from public URL/indexation policy so interactive search does not imply automatic indexability.

## Gate G6 — Market-integration readiness

Before a marketplace adapter is treated as production:

- access method/rights/terms are documented;
- adapter contract tests pass;
- rate limiting/cache policy is documented;
- source failure does not break core design search;
- source health is observable;
- maintenance burden is measured.

## Gate G7 — Public release readiness

Before public launch:

- automated CI gates pass on protected/default branch;
- backup/recovery is tested;
- basic security/privacy requirements are implemented;
- user-visible error states are handled;
- operational alerts are exception-based;
- key product analytics needed for validation are defined;
- legal/source-attribution requirements are satisfied;
- OQ-018 Search/SEO public-surface contract is accepted;
- canonical URL, indexation and sitemap checks pass for approved public page types;
- faceted-navigation tests show no uncontrolled combinatorial crawl/index surface;
- indexable pages expose meaningful crawlable rendered content and internal links;
- public frontend performance budgets/Core Web Vitals monitoring are configured;
- structured-data validation passes for every enabled structured-data page type.
