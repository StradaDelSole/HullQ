# SLICE-0090 — Sail+Power Architecture and Source-Rights Feasibility Pack

**Status:** DESIGN_RESEARCH DELIVERABLE — read-only decision package, not an implemented design  
**Date:** 2026-10-26  
**Slice:** SLICE-0090 (`docs/slices/SLICE-0090-sail-power-architecture-source-rights.md`)  
**Baseline HEAD checked:** current `slice/0090-sail-power-architecture-source-rights` worktree, branched from canonical `main` per the slice contract's dependency line (post-SLICE-0089, PR #377, `531cf426f7d73ad4f0bd3cc44a383b883bc9d383`)  
**Companion artifacts:** `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`; `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`  
**Controlling decisions:** Owner decision #366 (`docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`); post-0088 reconciliation + tracker #372 (`docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md`); ADR-0005 (source rights); OQ-007 (source rights research)

This pack answers the single blocking hypothesis the slice exists to resolve: **can the accepted nine-criterion Sail kernel and truthful broker workflow extend into a joint Sail+Power system with category-aware evidence and legally usable sources, without a second contradictory truth engine?** It does not implement anything. No code, migration, Search criterion, or production source clearance is authorized by this document.

---

## 1. As-is architecture (verified on current HEAD)

### 1.1 Identity/truth graph

```
BoatDesign/generation/NamedVariant  (design-side canonical catalogue; sail-only content today)
        |
        | BoatDesignRef (optional pointer; see market_identity.py)
        v
PhysicalBoat ----------------> current PhysicalBoatClaimRevision (publisher-asserted, per-field,
  (PhysicalBoatId,                VALUE_ASSERTION | UNKNOWN | ABSENT, SLICE-0086/0087 fields)
   boat_design_ref: optional)
        |
        | 1:N
        v
MarketEpisode (one sale episode per PhysicalBoat)
        |
        | 1:N
        v
NativeListing (HullQ-hosted market appearance; lifecycle_state)
        |
        +--> current_public_eligibility.py  ("D29" evaluator — the single accepted
        |     admission rule every public-read and Search surface must reuse;
        |     ACTIVE lifecycle alone is never sufficient)
        |
        +--> inventory_search.py: list_active_design_linked_listings()
              SQL: `nl.lifecycle_state = 'ACTIVE' AND pb.boat_design_ref IS NOT NULL`
              -> native_inventory_query.run_mixed_boat_design_configuration_query()
                 -> boat_design_field_bridge.run_boat_design_configuration_query()
                    (per-criterion DesignConfigurationSet merge, MUST/AND kernel)
                 -> physical_boat_claims.list_current_physical_boat_claim_observations()
                    (publisher's current per-field claim snapshot)
                 -> configuration_engine.evaluate_configuration()
                    -> CONFIRMED_MATCH | CONFIRMED_NON_MATCH | INSUFFICIENT_DATA
                       per listing, with full ConfigurationEvidence +
                       SearchCriterionEvidence retained (never a bare boolean)
```

**Confirmed structural fact:** `boat_design_ref IS NOT NULL` is a hard SQL filter in the only candidate-selection query every accepted Search path consumes (`inventory_search.py:46`, consumed by `native_inventory_query.py`). A design-unresolved `PhysicalBoat` — including one with a complete, qualified, publisher-attested concrete claim set — is invisible to native technical Search today. This is the exact gap both the slice contract and the post-0088 reconciliation (`POST_SLICE_0088_...md` §2 row 1) already identified; this pack confirms it is unchanged on the current HEAD and sizes the fix.

### 1.2 Shared Search kernel (already generalized past "draft + keel only")

`src/hullq/search/criteria_registry.py` carries **nine** active `CriterionDefinition` entries through accepted SLICE-0087: `draft_max`, `keel_configuration`, `loa`, `rudder_configuration`, `hull_configuration`, `cockpit_position`, `deck_saloon`, `beam`, `hull_material`. Each definition is a frozen dataclass wiring:

- `kind` (CATEGORICAL | NUMERIC), `param_keys`, `projection_field`;
- `design_set_builder: (conn, boat_design) -> DesignConfigurationSet` — identical shape for every criterion regardless of whether the projection is a single field or a generation-aware derived value;
- `read_claim: (CurrentPhysicalBoatClaimObservation) -> (AssertionKind, value) | None` — identical shape whether the underlying claim wraps a `Decimal` or an enum.

`native_inventory_query.run_mixed_boat_design_configuration_query` calls every active definition's builder/reader uniformly and merges results through the one shared MUST/AND kernel (`configuration_engine.evaluate_configuration`). **This is the mechanism the Owner decision (§9 point 1) and the post-0088 reconciliation explicitly require reuse of** — there is one truth engine, not nine ad hoc ones, and it is already criterion-count-agnostic by construction. This is a material correction to the external v0.9 review's superseded "only draft and keel" claim.

Claim semantics (`src/hullq/domain/physical_boat_claims.py`) are uniformly three/four-state: `VALUE_ASSERTION`, `UNKNOWN`, and (field-dependent) `ABSENT`, never collapsing "not yet captured" into a guessed value. This shape is category-neutral and requires no change to extend to Power fields.

### 1.3 Import/export (Sail-only today, by construction not by oversight)

- `src/hullq/domain/import_nautix.py` `_ACCEPTED_SAIL_BOAT_TYPES` (frozenset of NautiX 1.4 sail boat-type tokens) is the only accepted category filter on import; anything outside it is rejected, not silently coerced.
- `src/hullq/domain/inventory_export.py` `_NAUTIX_CATALOG_BOAT_TYPE = "sail-yacht"` is hard-coded on every exported row. The module's own docstring states this is a deliberate structural fact of HullQ's current sail-only catalogue scope, not a per-row marketing assertion — i.e. **this is expected pre-pivot behavior, not an 0088 defect**, matching the post-0088 reconciliation's classification.
- Both modules fail closed on an unrecognized category today (reject/omit rather than guess); that fail-closed shape is the right primitive to extend, not replace.

### 1.4 Shared vs. Sail-specific — the boundary this pack must answer precisely

| Layer | Shared across Sail+Power (code-verified) | Sail-specific today (code-verified) |
|---|---|---|
| Identity (`market_identity.py`) | `PhysicalBoat`, `MarketEpisode`, `NativeListing`, `BoatDesignRef` — category-blind by construction | none |
| Public eligibility (`current_public_eligibility.py`, D29) | the single admission evaluator every surface reuses | none |
| Claim shape (`physical_boat_claims.py`) | `AssertionKind` tri/quad-state pattern, per-field claim revisioning | the nine concrete claim *fields* are sail-dimension names (keel/rudder/hull config/deck saloon/etc.) |
| Search kernel (`configuration_engine`, `criteria_registry.CriterionDefinition`, `native_inventory_query`) | the MUST/AND evaluator, the `CriterionDefinition` wiring shape, the merge/evidence-retention pattern | the nine registered *instances* and their `design_set_builder`/`read_claim` bodies, which read sail-only `BoatDesign` projections |
| Candidate selection (`inventory_search.list_active_design_linked_listings`) | the ACTIVE+D29 admission gate | the `boat_design_ref IS NOT NULL` restriction (category-blind in itself, but structurally excludes any concrete-claim-only path for either category) |
| Import (`import_nautix.py`) | XML parsing/schema plumbing, media/claim field mapping scaffolding | `_ACCEPTED_SAIL_BOAT_TYPES` category gate |
| Export (`inventory_export.py`) | seven-writer-format plumbing, formula-injection/control-char guards, concurrency model | fixed `sail-yacht` category tag |

**Conclusion:** the shared kernel is already structurally criterion/category-agnostic (constraint 1 of the registry's own "Shared foundation" contract, re-verified above). The gap is entirely in (a) the candidate-selection SQL predicate, (b) the absence of any Power `CriterionDefinition` instances/claim fields/design projections, and (c) the import/export category vocabulary. No evidence supports building a second, parallel Power truth engine — doing so would violate the Owner decision (§4 point 6, §9 point 1) and the post-0088 contract (§2 row "Sail hard technical facets").

---

## 2. To-be design proposal (DRAFT — not an accepted ADR)

This section is a **proposal for future Owner/ADR review**, not an accepted decision. It identifies minimal, backward-compatible extension points; it authorizes nothing by itself.

### 2.1 Category as a first-class, explicit value — never inferred from hull/model name

Add an explicit `VesselCategory` claim dimension with values `SAIL | POWER | MOTORSAILER | UNKNOWN | CONFLICT`, following the exact `AssertionKind` pattern already used for every other claim field (`VALUE_ASSERTION | UNKNOWN`; `CONFLICT` arises from cross-source corroboration disagreement, not a fifth assertion kind). Category must be:

- attached to `BoatDesign` (design-level canonical category, where a design record exists) **and independently** to `PhysicalBoat` (publisher-asserted category of the concrete offered vessel), mirroring the existing design/concrete separation;
- never inferred from free-text hull or model-name strings — motorsailer and mixed-propulsion vessels are explicitly named as a case the Owner decision (§1, "Nicht entschieden") forbids guessing on;
- a hard pre-filter for every category-specific `CriterionDefinition` set, so a Power listing can never enter Sail's nine-criterion evaluation and vice versa (cross-category exclusion is an acceptance test obligation per the post-0088 contract §3.6).

### 2.2 A second, independently reviewed `CriterionDefinition` family for Power — same kernel, new instances

Power gets its own `design_set_builder`/`read_claim` implementations registered through the **same** `CriterionDefinition` dataclass and consumed by the **same** `evaluate_configuration` MUST/AND kernel and the **same** `NativeInventorySearchOutcome` evidence shape. This satisfies the slice contract's bridge/third-copy guard framing even though it is formally `NOT_APPLICABLE` for this docs-only slice (no criterion is added here) — any future slice that adds Power criterion #1 will be that domain's *first* criterion (fresh ordinal under `POST_0051_TRIGGER_GATES.md`'s Power-domain counting, to be confirmed at that slice's readiness, not assumed here), while criterion #2+ must satisfy the existing bridge/third-copy comparisons against both Sail's and Power's own prior criteria.

Candidate Power dimensions (from the Owner decision §5 table; **naming/field contract is NOT decided here**, only the proposal that it fits the existing `CriterionDefinition` shape): hull planing/displacement/semi-displacement classification, propulsion configuration (shaft/pod/waterjet/outboard/hybrid/electric count+type), installed engine power/fuel type, and condition-qualified operating-point claims (speed/consumption/range at a stated load/sea-state/measurement basis — see §2.4).

### 2.3 A second, qualified-concrete-claim candidate path — not a design-truth shortcut

`inventory_search.list_active_design_linked_listings` stays exactly as-is (it is the accepted, already-tested design-linked path — regression-protecting it is a hard constraint). A **second**, independently named and independently tested query/function is proposed: it admits a `NativeListing` whose `PhysicalBoat` is design-unresolved (`boat_design_ref IS NULL`) *only* when:

1. the listing independently passes the same D29 current-public-eligibility gate (no weaker admission rule for design-unresolved inventory);
2. the publishing Organization's current claim snapshot carries a `VALUE_ASSERTION` (not `UNKNOWN`/absent) for every criterion field the search request actually constrains;
3. the claim is attributed, dated, and revision-tracked exactly as today's `PhysicalBoatClaimRevision` already requires — no new weaker claim type;
4. the result is classified through a label that is visibly distinct from design-confirmed evidence (e.g. a `source_basis: PUBLISHER_CLAIM` vs `source_basis: DESIGN_CONFIRMED` tag on the existing evidence objects) so that a UI or API consumer can never conflate "broker said so" with "HullQ independently verified against a BoatDesign record" — this directly implements the post-0088 contract §3 point 3's "laut Brokerangabe" vs. independently-verified-manufacturer-truth distinction.

This is an additive path. It must never downgrade or bypass the existing nine-dimension design-linked MUST/AND evaluation; a listing that has *both* a resolved design and a conflicting concrete claim must surface `CONFLICT`, never silently prefer one source.

### 2.4 Conditional/operating-point measurement — a typed value object, not a bare scalar

Speed/consumption/range claims require a dedicated value shape (proposal, not a committed schema): `OperatingPointClaim { speed_or_load_basis, sea_state_or_test_standard, fuel_reserve_margin, measurement_source, observed_at }` alongside the scalar. A bare `range_nm` field with no recorded basis must remain `INSUFFICIENT_DATA` for any Search criterion that claims a specific operating condition — tank-capacity-divided-by-burn-rate arithmetic is, at most, a visibly labeled derived estimate, never a confirmed operating-point fact (Owner decision §5 table row 4; post-0088 contract §3 point 5).

### 2.5 Import/export category vocabulary

- Import: replace the single Sail allow-list with an explicit per-source category mapping table (`source token -> {SAIL, POWER, MOTORSAILER, UNKNOWN}`), reusing the existing fail-closed-on-unrecognized-token behavior for any token absent from the table, rather than silently defaulting it to Sail.
- Export: emit the listing's actual category tag per format where the target schema supports it; where a third-party schema (e.g. the pinned NautiX XSD's boat-type enumeration) cannot represent a real category or a true concrete fact, the writer must warn/disclose the loss rather than invent a nearest-fit value — this is the "import→export category loss" adversarial case in the fixture corpus (§5 of this pack).

### 2.6 What this proposal explicitly does not decide

- the final Power field names/units/enum vocabulary;
- whether `MOTORSAILER` gets its own criterion set or a documented subset-union of both;
- the exact SQL/ORM shape of the second candidate path;
- any UI/API wording for `source_basis` labeling;
- criterion ordinal numbers or bridge/third-copy evidence for any specific future slice.

Each of these is named explicitly in the implementation decision map (§4) as a separate future slice's own readiness obligation.

---

## 3. Source-rights register

See `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md` for the full per-source-family register (eight families, each with live URL, retrieval date, rights basis, license scope, access conditions, HullQ use-specific clearance per ADR-0005/OQ-007's framework, and correction/takedown path). Summary disposition:

| Clearance class | Count | Representative families |
|---|---|---|
| GREEN / green-with-obligations | 2 | Wikidata (CC0, reused from OQ-007), applicable open-government vessel-registry datasets where verified |
| AMBER — conditional / review required | 3 | manufacturer brochure/spec pages (primary factual reference, no explicit open license), classification-society/standard technical documents, broker-owned concrete claims (not a license question — a provenance/trust question) |
| RED / blocked pending explicit review | 2 | third-party aggregator databases (e.g. existing boat-market listing aggregators' own compiled spec databases), any source with an active anti-scraping ToS or unresolved TDM reservation |
| UNKNOWN — insufficient evidence | 1 | a long-tail historical/out-of-print manufacturer archive with no reachable current rights statement |

No source in this register is marked cleared for `bulk_bootstrap` or `automated_ingestion` in this slice. This slice performs **zero** scraping, downloading, or bulk retrieval; every row is a desk-review citation with a retrieval date for the *rights statement itself*, not a data harvest.

---

## 4. Future implementation decision map

Each row is a proposed future slice boundary with one independently testable failure domain. **No slice number is assigned here** — ordering and selection remain an explicit Owner act per the slice contract and `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md` §6's phase guardrails.

| # | Proposed scope | Prerequisites | Primary code touchpoints | Acceptance test shape | STOP threshold |
|---|---|---|---|---|---|
| A | Explicit `VesselCategory` claim (design + concrete), fail-closed unknown/conflict, cross-category Search exclusion test | None beyond this pack | `physical_boat_claims.py`, new migration, `criteria_registry.py` (category pre-filter wiring only) | Sail design cannot match Power query and vice versa; `UNKNOWN`/`CONFLICT` never silently resolve | Any attempt to infer category from hull/model text |
| B | Qualified concrete-claim candidate path for design-unresolved listings (§2.3), both categories | A (category must exist to scope the new path safely) | new `inventory_search` function (additive, existing function untouched), `native_inventory_query.py`, evidence `source_basis` tagging | Existing nine-dimension design-linked regression suite unchanged; new path admits only fully-qualified `VALUE_ASSERTION` claims; conflicting design+claim surfaces `CONFLICT` | Any regression in the existing design-linked result set; any silent claim-as-design-truth promotion |
| C | Power `CriterionDefinition` family #1 (one coherent dimension, e.g. propulsion configuration) | A, B | `criteria_registry.py` new definitions, `configuration_engine` reuse (no fork), new Power claim fields/migration | Fresh Power criterion ordinal evidence per `POST_0051_TRIGGER_GATES.md`; no second truth engine; Sail criteria/tests unaffected | Any Power-specific bypass of `evaluate_configuration` |
| D | `OperatingPointClaim` conditional measurement model (§2.4) | C (needs at least one Power numeric criterion to anchor against) | new value object + claim field, criterion read_claim extension | Range/speed/consumption claim without basis stays `INSUFFICIENT_DATA`; no tank÷burn auto-derivation treated as confirmed | Any confirmed match derived from an unlabeled scalar |
| E | Import/export category vocabulary (§2.5) | A | `import_nautix.py` mapping table, `inventory_export.py` per-row tag + loss disclosure | Unrecognized source token rejected, not defaulted to Sail; export loss for unsupported target schema is visible, not silent | Any silent category coercion on import or export |
| F | Power source-rights-cleared data acquisition (per `SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`, source-by-source) | None (can run in parallel with A–E as a research track) | no code — source rights review + `research/evidence/SOURCE_REGISTER.md` entries | Each source has an explicit use-specific clearance before any ingestion code is written | Any ingestion code written against an UNKNOWN/RED-cleared source |
| G | Power Buyer/Broker Search-fit parity using the exact Power truth kernel (no parallel scorer) | C, D | `broker_search_fit.py` extension, reuse only | Power Search-fit score traces to the same `evaluate_configuration` evidence Buyer search uses | Any Power-only scoring heuristic bypassing the shared kernel |
| H | #355 pre-real-external-data runtime hardening (parser isolation, admission/timeouts, archive-bomb guards) | None (independent of Sail/Power category work; already a standing P0 gate) | `api/app.py` import route, `persistence/connection.py`, `domain/import_spreadsheet.py` | Adversarial archive/timeout/resource tests pass under real execution, not static review | Any real external broker data accepted before this gate passes |

Rows F and H are pre-existing standing obligations (source rights, #355) restated here only to keep the dependency graph legible; they are **not new scope invented by this slice**.

---

## 5. Hard-case evidence corpus

See `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md` for the full reproducible corpus (eleven labeled synthetic cases, exceeding the eight-case minimum) covering: mono-hull Sail baseline, Sail multihull, motorsailer, Power planing/displacement, two model-generation/engine variants, a re-powered used boat, a design-unresolved but typed issuer-owned current claim, disputed/retracted engine hours, operating-condition-dependent range, unknown category, and category conflict. Each case records its expected classification outcome and the specific invariant it exercises; none use real buyer PII or real brokers.

---

## 6. Owner-ready decision and risk register

### DECIDED_AND_IMPLEMENTED

- Nine Sail hard technical dimensions, shared MUST/AND kernel, `CriterionDefinition` registry shape, D29 public eligibility, claim tri/quad-state semantics, 0083 eight-format import, 0088 seven-format export (XLSB deferred #362), 0089 factual broker reporting. **Not re-opened by this slice.**

### DECIDED_NOT_YET_IMPLEMENTED

- Joint Sail+Power category model; qualified concrete-claim candidate path for design-unresolved listings (either category); Power `CriterionDefinition` family; conditional operating-point measurement model; category-aware import/export vocabulary; Power Broker Search-fit parity. All require their own Owner-selected slice per §4.

### GENUINELY_OPEN

- **Which specific Power source families are actually rights-cleared for production value/bulk ingestion** — this is a source-by-source legal/risk determination, not an engineering choice; see the source-rights matrix. Several families are AMBER/RED/UNKNOWN pending explicit review or a licensing agreement.
- The exact Power field vocabulary, units, and enum set (proposal only in §2.2/§2.4).
- Whether `MOTORSAILER` warrants its own criterion set or a defined subset-union — needs Owner/product input, not a unilateral engineering default.
- Minimum usable Power model-identity universe breadth for a credible internal Power milestone — explicitly not a "complete catalogue" requirement per the Owner decision §5, but no numeric threshold exists today and none is invented here.

### RIGHTS_BLOCKED

- Any source in the matrix's RED class, and any AMBER source until its source-specific compatibility/contract review is explicit (per ADR-0005's default-deny for bulk/automated use).

### DEFERRED

- Real external broker data / production pilot (blocked on #355 regardless of category); XLSB outbound (#362); Saved Search/alerts, owner-direct admission/trust, broker scaled onboarding, support/privacy/legal and operations gaps tracked in `docs/governance/OVERALL_MVP_CAPABILITY_REGISTER.md` — none of these are this slice's scope and none are silently resolved here.

### CONFLICT_OR_REGRESSION

- None found. Old Sail-only wording in `import_nautix.py`/`inventory_export.py` docstrings is historically accurate for pre-pivot HEAD and does not misstate the current joint-product Owner decision; §1.3 above records this explicitly so a future reader does not mistake accurate historical commentary for a stale policy claim.

---

## 7. Tracker update (proposed — requires explicit Owner/operator action)

Issue #372 should receive a comment linking to this pack and its two companion artifacts, **tracking-only, not closing #372**. Posting a GitHub comment is a shared-visibility action outside this agent's unilateral authority in this slice; the exact comment text is prepared for Owner review rather than posted automatically:

> SLICE-0090 (docs-only, REVIEW pending) delivered the read-only architecture/source-rights feasibility pack this tracker anticipated: `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md`, `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`, `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`. Confirms the design-linked-only candidate-selection gap, the Sail-only import/export category gate, and proposes (not decides) a qualified concrete-claim candidate path, a Power `CriterionDefinition` family reusing the existing kernel, and a conditional operating-point measurement model. No code changed; #372 stays open pending Owner-selected follow-on slices per the decision map in §4 of the architecture pack.

---

## 8. Validation performed on this pack

- Manual re-verification of every file/line citation in §1 against the current slice-branch HEAD (not a historical baseline) — see inline file:symbol references.
- Internal consistency check: every proposal in §2 is traced to an existing, unmodified shared primitive (no proposal requires forking `evaluate_configuration`, `current_public_eligibility`, or the claim `AssertionKind` shape).
- Governance validator run: see slice completion report for `scripts/validate_repository.py` result.
- No PostgreSQL/API/browser runtime execution is claimed anywhere in this pack; all findings above the fixture corpus are static source/documentation review, consistent with this slice's DESIGN_RESEARCH type.
