# HullQ — Requirements Baseline

**Version:** 0.5  
**Status:** ACTIVE baseline; requirements blocked by unresolved decisions are explicitly marked.  
**Normative language:** uppercase MUST/SHOULD/MAY use BCP 14 semantics.

Every normative requirement includes an acceptance condition. Tests may refine these conditions but MUST NOT weaken or invent domain semantics.

## Product

### REQ-PROD-001 — Characteristic-first discovery
HullQ MUST allow users to discover sailboat designs from technical characteristics without requiring a make/model input.

**Acceptance:** a query containing only supported technical criteria can produce matching design identities.

### REQ-PROD-002 — Core chain
Early HullQ functionality MUST strengthen `FIND DESIGN → FIND BOAT FOR SALE → COMPARE / SAVE → ALERT` and MUST NOT expand into unrelated boating-super-app features without a scope decision.

**Acceptance:** every early product capability maps to at least one step of the core chain or has an accepted scope decision.

### REQ-PROD-003 — Vessel scope
The canonical model MUST support monohulls, catamarans and trimarans as first-class hull configurations.

**Acceptance:** contract fixtures for all three hull configurations validate without requiring an `other` workaround.

### REQ-PROD-004 — Persistent market-watch use case
HullQ MUST support users who continue to monitor the sailboat market after owning or purchasing a boat. Saved technical preferences and monitoring MUST NOT be designed solely around a one-time active-purchase session.

**Acceptance:** a SavedQuery/Monitor can remain valid independently of a purchase-state transition or active buying session.

### REQ-PROD-005 — Query as persistent product object
A technical query MUST be representable independently from a current user session so it can be saved, monitored, compared against newly observed market inventory and reused across future purchase/upgrade cycles.

**Acceptance:** the query contract can be serialized/reloaded and evaluated without reconstructing it from transient UI state.

## Data

### REQ-DATA-001 — Explicit unknown
Missing data MUST remain explicitly unknown/null and MUST NOT be inferred from probability or model memory.

**Acceptance:** a missing source value remains null/unknown after normalization unless supported evidence is added.

### REQ-DATA-002 — Provenance
Every accepted production value MUST be traceable to evidence/source provenance.

**Acceptance:** a production value cannot reach accepted state without a machine-resolvable provenance path to source evidence.

### REQ-DATA-003 — Raw vs normalized
When a source value is normalized, the system MUST preserve sufficient raw evidence to audit the transformation.

**Acceptance:** for a normalized value, an auditor can retrieve the raw source representation plus the applied normalization method/version.

### REQ-DATA-004 — Conflict preservation
Conflicting authoritative evidence MUST NOT be silently resolved; the conflict MUST be represented or routed for review.

**Acceptance:** conflicting supported candidates produce an explicit conflict/review state or an auditable adjudication retaining contradicting evidence.

### REQ-DATA-005 — SI canonical units
Canonical physical values SHOULD be stored in SI units where practical; presentation MAY convert units.

**Acceptance:** supported physical canonical fields use their documented SI unit and UI conversion does not mutate stored canonical values.

### REQ-DATA-006 — Independent technical dimensions
Keel, rudder and skeg MUST be stored/searchable as independent concepts rather than one compound legacy hull-type field.

**Acceptance:** fixtures can independently vary keel, rudder and skeg while preserving valid contracts and query predicates.

### REQ-DATA-007 — Broad coverage
The production data strategy MUST support thousands of known sailboat design identities and MUST NOT constrain the product universe to the 50–100 benchmark corpus.

**Acceptance:** architecture/pipeline contracts support progressive ingestion beyond the benchmark without a schema redesign tied to a fixed model count.

### REQ-DATA-008 — Progressive depth
A partially populated canonical design MAY exist when known values satisfy provenance/validation requirements and missing fields remain explicit.

**Acceptance:** a sparse but valid BoatDesign can pass contract validation with supported fields plus explicit unknowns.

### REQ-DATA-009 — Reference scrape isolation
The historical SailboatData scrape MUST NOT be used as an invisible production-value fallback.

**Acceptance:** production-ingestion paths cannot source a technical value from the reference scrape without an explicit later rights/decision change and visible provenance.

## Identity

### REQ-ID-001 — Input/verified separation
Research input identity MUST remain distinguishable from verified canonical identity.

**Acceptance:** a research target's supplied manufacturer/model/year can be preserved even when verified identity differs.

### REQ-ID-002 — No forced merge
Ambiguous models/generations/variants MUST NOT be collapsed without evidence.

**Acceptance:** ambiguous identity fixtures can remain candidate-set/unresolved rather than being forced to one canonical identity.

### REQ-ID-003 — Generation/variant rule
The canonical identity model MUST distinguish commercial `BoatModel`, technical `BoatDesign` generation, named variants and orthogonal factory `DesignOption`s according to `specs/IDENTITY_MODEL.v0.1.md`.

**Acceptance:** accepted OQ-003 identity fixtures validate against this hierarchy.

### REQ-ID-004 — Stable model identity
BoatModel identifiers MUST be stable and opaque; reused human-facing model names MUST NOT force unrelated designs into the same BoatModel.

**Acceptance:** two unrelated same-name model lineages can coexist with distinct stable BoatModel IDs.

### REQ-ID-005 — Technical generation boundary
A BoatDesign MUST represent one technically coherent production generation and MUST NOT be split solely for cosmetic changes, supplier changes or builder transfers.

**Acceptance:** generation fixtures produce a new BoatDesign only where the accepted Identity Model's technical-baseline criteria are met.

### REQ-ID-006 — Orthogonal factory options
Independent factory-supported technical choices MUST be represented as DesignOptions and MUST NOT require persisted Cartesian combinations of every option axis.

**Acceptance:** a design with two keel choices and two rig choices can be modeled as four option records/choices or fewer, not four duplicated BoatDesign records.

### REQ-ID-007 — Instance modifications stay instance-level
Owner/refit modifications MUST NOT mutate canonical production BoatDesign baselines or become factory DesignOptions without supporting factory/design evidence.

**Acceptance:** an instance-level modification fixture leaves BoatDesign canonical values unchanged.

### REQ-ID-008 — Evidence-bounded resolution precision
Identity resolution MUST return only the most specific evidence-supported level and MUST NOT invent model-generation/variant/configuration specificity.

**Acceptance:** a model-only listing cannot resolve to a specific generation/configuration when required disambiguating evidence is absent.

## Provenance

### REQ-PROV-001 — Separate provenance ledger
Canonical searchable domain values MUST remain separate from provenance records; provenance MUST use the accepted FieldEvidence / FieldResolution / DerivationRecord contracts.

**Acceptance:** BoatDesign v0.3 stores plain canonical values and a production value can be traced through separate provenance records without embedding per-field evidence wrappers.

### REQ-PROV-002 — Standard field addressing
FieldEvidence and FieldResolution MUST address subject fields using RFC 6901 JSON Pointer relative to a stable subject identity.

**Acceptance:** provenance fixtures use valid JSON Pointers and identity-bearing collections are not persistently addressed by fragile array position.

### REQ-PROV-003 — Immutable source observations
FieldEvidence MUST be append/supersede oriented and MUST NOT be destructively rewritten to change what a source was observed to say.

**Acceptance:** correcting an observation creates a new evidence record linked by supersession while the earlier record remains auditable unless a legal deletion rule overrides retention.

### REQ-PROV-004 — Versioned canonical resolution
At most one current FieldResolution MAY exist per `(subject_kind, subject_id, field_pointer)`, while prior resolutions MUST remain auditable.

**Acceptance:** persistence/contract tests reject two current resolutions for the same subject field and retain superseded resolution history.

### REQ-PROV-005 — Canonical consistency
A non-null source-backed canonical value MUST equal the canonical-value snapshot of its current resolved/resolved-with-conflict FieldResolution.

**Acceptance:** a mismatch between canonical value and active resolution fails persistence/integration validation.

### REQ-PROV-006 — Derived values use lineage, not fabricated evidence
Values produced by configuration inheritance, overrides, formulas or other HullQ calculations MUST use DerivationRecord lineage and MUST NOT fabricate direct external-source evidence.

**Acceptance:** a derived configuration/ratio fixture identifies method version and input snapshots/resolution IDs and creates no false FieldEvidence claim for the derived output.

### REQ-PROV-007 — Source-rights reversibility
The provenance store MUST support reverse lookup from Source to dependent FieldEvidence and current/past resolutions so a rights or source-validity change can trigger re-evaluation.

**Acceptance:** given a Source ID, the system can enumerate every dependent evidence record and affected canonical field resolution.

### REQ-PROV-008 — Conflict preservation
Unresolved conflict MUST NOT emit a non-null canonical value; resolved-with-conflict MUST retain contradictory evidence.

**Acceptance:** the accepted negative/positive provenance fixtures enforce both cases.

## Research

### REQ-RESEARCH-001 — Minimal target input
The canonical research target input MUST contain only `manufacturer`, `model`, and `first_built`; workflow metadata belongs in ResearchJob state.

**Acceptance:** the research input template contains exactly those identity fields; workflow fields validate in ResearchJob instead.

### REQ-RESEARCH-002 — Exception-based review
The research pipeline SHOULD automatically accept clear, supported records that pass validation and MUST route uncertain/conflicting/high-risk cases to human review rather than requiring manual approval of every record.

**Acceptance:** benchmark execution records both automated-acceptance and review-queue outcomes and does not require universal manual approval.

### REQ-RESEARCH-003 — Immutable raw input
Raw imported/source artifacts used by research MUST be treated as immutable inputs; cleaning/normalization produces derived data.

**Acceptance:** normalization never overwrites the retained raw input artifact/reference.

### REQ-RESEARCH-004 — Measured scaling
Before broad ingestion, the benchmark MUST measure throughput, cost, automated-acceptance rate, review rate, conflict rate and HullQ-critical-field completeness.

**Acceptance:** benchmark output includes all mandatory metrics before the broad-ingestion gate may pass.

### REQ-RESEARCH-005 — Source rights
Reusable/open bootstrap data MUST retain explicit source and rights/license information sufficient to determine permitted production use according to `specs/SOURCE_RIGHTS_POLICY.v0.1.md`.

**Acceptance:** a reusable source cannot be approved for ingestion without a valid Source record containing the required rights fields.

### REQ-RESEARCH-006 — Access/reuse separation
Source access/automation conditions MUST remain distinguishable from copyright/database/license reuse rights.

**Acceptance:** the Source contract can represent automated access as prohibited/conditional while reuse permissions independently differ, and vice versa.

### REQ-RESEARCH-007 — Use-specific clearance
Production values, bulk bootstrap and automated ingestion MUST fail closed unless the relevant source use has explicit HullQ clearance.

**Acceptance:** unknown/unassessed clearance blocks the corresponding production/bulk/automation operation.

### REQ-RESEARCH-008 — Cumulative extraction control
For sources not cleared for bulk ingestion, automated research MUST be able to measure source-level request/extraction volume so repeated per-record access cannot silently become systematic bulk extraction.

**Acceptance:** pipeline telemetry can aggregate retrieval/extraction activity by source and trigger the configured review/block threshold.

### REQ-RESEARCH-009 — License obligations
Attribution, share-alike, notice and other source obligations MUST remain machine-addressable through ingestion and downstream publication decisions.

**Acceptance:** source obligations can be queried programmatically and block/condition a publication path.

## Derived metrics (legacy `REQ-RATIO` namespace)

### REQ-RATIO-001 — Internal calculation
Derived metrics MUST be calculated by HullQ from canonical base values when the required inputs exist rather than copied as authoritative derived values.

**Acceptance:** ratio fixtures derive outputs from base fields and do not require a source-provided ratio value.

### REQ-RATIO-002 — Versioned methodology
Each production derived-metric calculation MUST identify the accepted methodology version defining formula, units, applicability, missing-input handling and rounding policy.

**Acceptance:** every computed ratio carries/references the accepted formula version and passes golden fixtures.

### REQ-RATIO-003 — Explicit calculation basis
BoatDesign/ResolvedConfiguration MUST preserve displacement and sail-area basis metadata required by the accepted derived-metric methodology.

**Acceptance:** contract fixtures cannot represent a ratio-capable configuration without explicit `displacement_basis` and `sail_area_basis` values, including `unknown` where evidence is insufficient.

### REQ-RATIO-004 — Provisional uncertainty is machine-visible
A derived metric calculated from unknown/source-unspecified permitted bases MUST be distinguishable from a standard-basis result.

**Acceptance:** the OQ-001 provisional golden fixture produces `computed_provisional` rather than `computed`.

### REQ-RATIO-005 — Applicability by hull configuration
The calculation engine MUST enforce the accepted hull-configuration applicability policy per metric and MUST NOT emit a numeric value for a known non-applicable metric.

**Acceptance:** the multihull golden fixture computes SA/D and D/L while monohull-only metrics remain `null` with `not_applicable`.

### REQ-RATIO-006 — Deterministic canonical precision
Identical canonical inputs and method version MUST reproduce identical 6-decimal derived values under the accepted rounding policy.

**Acceptance:** every golden numeric fixture matches exactly at the six-decimal canonical boundary.

### REQ-RATIO-007 — Derived lineage
Every populated derived metric MUST have derivation lineage identifying the method version and effective inputs; source-published ratios MUST NOT masquerade as HullQ-calculated outputs.

**Acceptance:** a derived-metric fixture maps to a DerivationRecord and creates no FieldEvidence claim for the calculated output itself.

### REQ-RATIO-008 — No safety-score implication
HullQ MUST NOT infer opaque seaworthiness, stability certification or generic “bluewater” status solely from these derived metrics.

**Acceptance:** product/search specifications contain no automatic safety certification or hidden composite score derived from the OQ-001 metrics.

## Search

### REQ-SEARCH-001 — Curated canonical filters
Search filters MUST use HullQ canonical fields/taxonomy and MUST NOT be dynamically coupled to arbitrary raw-source fields.

**Acceptance:** adding/removing a raw research field does not automatically create/remove a public search filter.

### REQ-SEARCH-002 — Unknown is not negative
A record with unknown data for an active criterion MUST NOT be classified as a confirmed non-match solely because that field is missing.

**Acceptance:** an unknown-field fixture returns an insufficient-data state rather than confirmed false for that criterion.

### REQ-SEARCH-003 — Three-state semantics
**BLOCKED by OQ-009.** Query semantics MUST distinguish at least confirmed match, confirmed non-match and insufficient-data/unknown outcome where relevant.

**Acceptance:** OQ-009 fixtures cover and distinguish all three states for the same criterion type.

### REQ-SEARCH-004 — Explainable matching
For each returned design, HullQ SHOULD be able to identify which query criteria were confirmed and which depend on missing/uncertain data.

**Acceptance:** a match result can expose criterion-level outcome metadata without recomputing from UI state.

### REQ-SEARCH-005 — Determinism
Given the same dataset version, query specification and formula/taxonomy versions, search results MUST be deterministic.

**Acceptance:** repeated execution against identical versioned inputs produces the same ordered/qualified result set subject to an explicitly versioned ranking rule.

### REQ-SEARCH-006 — Configuration-aware evaluation
Where a criterion depends on option-sensitive values, search MUST evaluate a ResolvedConfiguration rather than assuming the BoatDesign baseline applies to every factory configuration.

**Acceptance:** a shallow-draft option can match a draft criterion while the standard configuration of the same BoatDesign does not, without duplicating the BoatDesign identity.

## SEO / public search architecture

### REQ-SEO-001 — SEO is product architecture
Search Architecture and SEO MUST be treated as part of HullQ product architecture from the beginning, not as a post-launch marketing retrofit.

**Acceptance:** frontend/search architecture reviews include crawl/index, URL, canonicalization, rendering, internal-linking, sitemap and performance consequences before public implementation is approved.

### REQ-SEO-002 — Stable crawlable public entities
Public indexable BoatModel/BoatDesign and other approved discovery surfaces MUST have stable, crawlable URLs and meaningful content that does not depend on reconstructing transient client-only filter state.

**Acceptance:** an indexable entity page can be fetched at a stable URL and exposes its primary content/metadata to a crawler without requiring an authenticated or ephemeral UI session.

### REQ-SEO-003 — Faceted crawl-space control
The technical filter system MUST NOT automatically expose every combinatorial query/filter state as an indexable URL space.

**Acceptance:** OQ-018 defines an explicit allow/index policy for curated search landing pages and a prevention strategy for unbounded/duplicate faceted URLs before public launch.

### REQ-SEO-004 — Canonical URL and sitemap consistency
Indexable pages MUST have a defined canonical-URL policy and generated sitemaps MUST list preferred canonical URLs rather than arbitrary duplicate/filter variants.

**Acceptance:** SEO contract tests can map every approved indexable page type to one preferred canonical URL and sitemap behavior.

### REQ-SEO-005 — Crawlable rendering
Primary content on approved indexable pages MUST be reliably available to search crawlers; bot-specific dynamic rendering MUST NOT be the foundational strategy.

**Acceptance:** rendered-output tests demonstrate discoverable primary text, links and metadata for indexable page fixtures under the accepted frontend/rendering architecture.

### REQ-SEO-006 — Truthful structured data
Structured data MAY be emitted only when it accurately represents visible HullQ content and a supported schema/use case; it MUST NOT invent ratings, sale prices or other unavailable facts.

**Acceptance:** structured-data fixtures validate for approved page types and map only to canonical/visible domain data.

### REQ-SEO-007 — Search-performance quality
Public search/discovery pages MUST include measurable performance budgets and Core Web Vitals monitoring as release-quality concerns.

**Acceptance:** G7 defines and verifies performance monitoring/budgets for the public frontend before launch.

## Market

### REQ-MARKET-001 — Adapter isolation
Every marketplace integration MUST be isolated behind a source-specific adapter returning the canonical HullQ listing contract.

**Acceptance:** source-specific parsing/access code does not leak source-specific fields into the query/design domain contract.

### REQ-MARKET-002 — Access verification
A production adapter MUST NOT be implemented/operated until its access method, relevant terms/rights, caching and display constraints are documented.

**Acceptance:** each enabled production source has a current OQ-013 access/register decision covering these dimensions.

### REQ-MARKET-003 — Source failure isolation
Failure of a market source MUST NOT corrupt or disable the core BoatDesign database/search.

**Acceptance:** simulated adapter failure leaves technical design search operational and returns an isolated source-status failure.

### REQ-MARKET-004 — No unnecessary mirroring
HullQ SHOULD avoid persistent full-market mirroring unless a documented access agreement and product need justify it.

**Acceptance:** persistent mirroring requires an explicit source-access decision and architecture justification rather than being the default adapter behavior.

### REQ-MARKET-005 — Asking price is not sale price
A listing's observed asking price MUST NOT be represented as an achieved sale price, and a listing disappearing from a source MUST NOT by itself be interpreted as sold.

**Acceptance:** lifecycle fixtures can represent `listing_removed/unknown_outcome` without generating a sale event or achieved price.

### REQ-MARKET-006 — Historical observation rights
HullQ MUST NOT retain longitudinal listing/price observations beyond what the applicable source rights/access decision permits.

**Acceptance:** a source without historical-retention clearance cannot create durable price-history snapshots even if live display/search is allowed.

## Alerts

### REQ-ALERT-001 — Technical-query alert
HullQ MUST be capable of representing a saved technical query independently of any named boat model.

**Acceptance:** a Monitor can reference a SavedQuery containing only technical criteria.

### REQ-ALERT-002 — Any matching design
The alert model MUST support notifying when a newly observed listing belongs to any design satisfying the saved technical query.

**Acceptance:** one Monitor can emit alerts for listings belonging to different BoatModels when each satisfies the same SavedQuery.

## Subscription / entitlements

### REQ-SUB-001 — Open discovery core
The initial freemium product model MUST keep core technical search available on the Free tier; monetization SHOULD primarily attach to persistence, monitoring cadence/capacity and advanced market-watch features rather than basic discovery.

**Acceptance:** Free entitlement permits core technical search without a paid entitlement check on query semantics.

### REQ-SUB-002 — Separate domain concepts
`Search`, `SavedQuery`, `Monitor`, `Alert` and `SubscriptionEntitlement` MUST be modeled as distinct concepts rather than collapsed into one saved-search flag.

**Acceptance:** contracts/domain model can create a SavedQuery without an active Monitor and an Alert only as an event from monitoring logic.

### REQ-SUB-003 — Configurable entitlement limits
Saved-query limits, active-monitor limits, monitoring frequency and premium capabilities MUST be configuration/data-driven and MUST NOT be hard-coded into domain logic.

**Acceptance:** changing a tier limit does not require changing/recompiling SavedQuery or Monitor domain behavior.

### REQ-SUB-004 — Freemium tier capability
The entitlement model MUST support at least Free, Plus and Pro tiers with increasing monitoring capacity and capabilities. Exact limits/prices remain product hypotheses until OQ-016 is resolved.

**Acceptance:** entitlement fixtures can express Free/Plus/Pro with different limits/capabilities without changing the underlying query schema.

### REQ-SUB-005 — Premium monitoring capabilities
The entitlement model MUST be capable of differentiating active-monitor count, alert speed/frequency, supported-market breadth, price-change tracking and higher/larger limits without changing SavedQuery semantics.

**Acceptance:** two entitlements can run the same SavedQuery with different monitoring capabilities/cadence.

### REQ-SUB-006 — Price-intelligence capability
HullQ Pro MUST be capable of offering advanced market-watch intelligence such as observed asking-price history, price-change alerts and model/configuration trend summaries where OQ-017 and source rights permit the required history.

**Acceptance:** entitlement/domain contracts can enable price-intelligence capabilities independently of core search, while data generation remains blocked when history is not lawfully/technically available.

## Governance / engineering

### REQ-GOV-001 — Single repository
All first-party HullQ code, docs, specs, tests and infrastructure MUST remain in one repository unless superseded by an accepted ADR.

**Acceptance:** repository inventory contains all first-party implementation/spec/test assets or an accepted ADR documents an exception.

### REQ-GOV-002 — Docs-to-code
Behaviorally significant implementation MUST trace to an accepted requirement/specification and verification artifact.

**Acceptance:** no behaviorally significant code change can pass its quality gate without requirement/spec and test linkage.

### REQ-GOV-003 — No unresolved semantic coding
An implementation agent MUST NOT silently resolve an open question that changes domain semantics or a public/persisted contract.

**Acceptance:** any such unresolved semantic choice blocks implementation and points to an OQ/ADR rather than appearing only in code.

### REQ-GOV-004 — Versioned contracts
Persisted/public contract semantics MUST use explicit versions and MUST NOT be silently mutated after release.

**Acceptance:** a semantic contract change produces a new version plus migration/release evidence where consumers or persisted data are affected.

### REQ-GOV-005 — Reproducible Python toolchain
The Stage-2 Python implementation MUST use the accepted OQ-010 toolchain baseline with a committed project configuration, pinned Python major/minor line and committed dependency lock before pipeline code is treated as mergeable.

**Acceptance:** root `pyproject.toml`, `.python-version` and `uv.lock` exist; `uv lock --check` and `uv sync --locked --all-groups` succeed on supported CI platforms.

### REQ-GOV-006 — Automated quality gates
Mergeable Python changes MUST pass automated repository/schema validation, formatting, linting, strict type checking, tests and the configured branch-coverage floor on the accepted CI platforms.

**Acceptance:** CI executes the accepted G1 checks on Linux and Windows and a deliberately failing check blocks the quality job.

### REQ-GOV-007 — Supply-chain update and audit baseline
The repository MUST maintain automated dependency update visibility and MUST run a dependency-vulnerability audit in CI/release flows with network access.

**Acceptance:** repository configuration tracks both uv dependencies and GitHub Actions updates, and CI contains a blocking dependency-audit job.
