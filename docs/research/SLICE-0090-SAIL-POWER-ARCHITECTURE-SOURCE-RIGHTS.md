# SLICE-0090 — Sail+Power Architecture and Source-Rights Feasibility Pack

**Status:** DESIGN_RESEARCH DELIVERABLE — read-only decision package, not an implemented design  
**Date:** 2026-10-26  
**Slice:** SLICE-0090 (`docs/slices/SLICE-0090-sail-power-architecture-source-rights.md`)  
**Baseline HEAD checked:** current `slice/0090-sail-power-architecture-source-rights` worktree, branched from canonical `main` per the slice contract's dependency line (post-SLICE-0089, PR #377, `531cf426f7d73ad4f0bd3cc44a383b883bc9d383`)  
**Companion artifacts:** `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`; `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`  
**Controlling decisions:** Owner decision #366 (`docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md`); post-0088 reconciliation + tracker #372 (`docs/POST_SLICE_0088_SAIL_POWER_CLAIM_AND_GAP_RECONCILIATION_2026-10-23.md`); ADR-0005 (source rights); OQ-007 (source rights research)

This pack answers the single blocking hypothesis the slice exists to resolve: **can the accepted nine-criterion Sail kernel and truthful broker workflow extend into a joint Sail+Power system with category-aware evidence and legally usable sources, without a second contradictory truth engine?** It does not implement anything. No code, migration, Search criterion, or production source clearance is authorized by this document.

**Amendment note (2026-10-26):** this revision responds to independent-review findings A–G on the original REVIEW-handoff version. Corrections are marked inline at each affected section (§1.3, §1.4, §2.3–2.5, §3, §5, §6, §8) rather than presented as a separate delta document, since the primary pack is itself the artifact under review. The companion rights matrix and fixture corpus are both bumped to v0.2.

**Second amendment note (2026-10-26, findings H–J):** three remaining documentation-consistency issues from the A–G amendment itself, now corrected: (H) the NautiX `power-*` token count was miscounted as 29 in two places — directly recounted on this HEAD at 33 and fixed in §1.4/§2.5 and in the fixture corpus; (I) §3's source-family totals were internally inconsistent (an "eight families" list that omitted Family 1 while also claiming to include it) — corrected to nine external families plus the separately-tracked first-party entry, with evidence-quality distinguished per family (see §3 and the matrix's own corrected-totals section); (J) §3 and the matrix both asserted a blanket "no source cleared for bulk_bootstrap" that directly contradicted Wikidata's own `bulk_bootstrap: allowed` row — corrected to distinguish CC0 license rights from API access conditions from actual (unauthorized-by-this-document) operational ingestion.

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

### 1.3 Import/export (Sail-only today, by construction not by oversight) — corrected after direct NautiX 1.4 schema inspection (amendment finding E)

- `src/hullq/domain/import_nautix.py` `_ACCEPTED_SAIL_BOAT_TYPES` (frozenset of NautiX 1.4 sail boat-type tokens) is the only accepted category filter on import. Re-verified against the actual importer logic (`_first_sail_boat_type`, consumed at `import_nautix.py:348`): when every `<type>` token on an advert falls outside this allow-list, the row's `boat_type` resolves to `None` and the row is staged with an explicit rejection reason, `"boat is not within HullQ's currently accepted sailboat supply domain"` — **import genuinely fails closed** on a Power/inflatable/small-craft/PWC advert today; it is rejected, never silently coerced into a Sail row.
- `src/hullq/domain/inventory_export.py` `_NAUTIX_CATALOG_BOAT_TYPE = "sail-yacht"` is hard-coded and written **unconditionally** on every exported row, with **no category check of any kind** at the export call site. This is *not* a fail-closed mechanism — it is an unguarded constant that is only currently correct because every exportable row today is, in fact, a sail yacht (HullQ's present supply domain). **Correction to the original pack's §1.3/§1.4:** describing import and export as symmetrically "fail closed" was wrong; only import fails closed. If a Power-category row ever reached this exporter unchanged, it would silently emit a factually false `sail-yacht` tag — this is the real defect-in-waiting, not a schema limitation (see the corrected §2.5 below, informed by direct inspection of the pinned XSD, which shows the schema itself has no difficulty representing a true category).
- The module's own docstring states the fixed tag is a deliberate structural fact of HullQ's current sail-only catalogue scope, not a per-row marketing assertion — i.e. **this is expected pre-pivot behavior, not an 0088 defect**, matching the post-0088 reconciliation's classification. It remains correct only as long as the exporter's actual input rows remain Sail-only.

### 1.4 Shared vs. Sail-specific — the boundary this pack must answer precisely

| Layer | Shared across Sail+Power (code-verified) | Sail-specific today (code-verified) |
|---|---|---|
| Identity (`market_identity.py`) | `PhysicalBoat`, `MarketEpisode`, `NativeListing`, `BoatDesignRef` — category-blind by construction | none |
| Public eligibility (`current_public_eligibility.py`, D29) | the single admission evaluator every surface reuses | none |
| Claim shape (`physical_boat_claims.py`) | `AssertionKind` tri/quad-state pattern, per-field claim revisioning | the nine concrete claim *fields* are sail-dimension names (keel/rudder/hull config/deck saloon/etc.) |
| Search kernel (`configuration_engine`, `criteria_registry.CriterionDefinition`, `native_inventory_query`) | the MUST/AND evaluator, the `CriterionDefinition` wiring shape, the merge/evidence-retention pattern | the nine registered *instances* and their `design_set_builder`/`read_claim` bodies, which read sail-only `BoatDesign` projections |
| Candidate selection (`inventory_search.list_active_design_linked_listings`) | the ACTIVE+D29 admission gate | the `boat_design_ref IS NOT NULL` restriction (category-blind in itself, but structurally excludes any concrete-claim-only path for either category) |
| Import (`import_nautix.py`) | XML parsing/schema plumbing, media/claim field mapping scaffolding | `_ACCEPTED_SAIL_BOAT_TYPES` category gate — **genuinely fail-closed** (verified §1.3) |
| Export (`inventory_export.py`) | seven-writer-format plumbing, formula-injection/control-char guards, concurrency model | fixed, **unguarded** `sail-yacht` category tag — not fail-closed, merely currently-correct-by-input-constraint (corrected §1.3) |

**Conclusion:** the shared kernel is already structurally criterion/category-agnostic (constraint 1 of the registry's own "Shared foundation" contract, re-verified above). The gap is entirely in (a) the candidate-selection SQL predicate, (b) the absence of any Power `CriterionDefinition` instances/claim fields/design projections, and (c) HullQ's own import/export category gate — **not** the external NautiX schema, which (§2.5 below) already carries a substantially richer boat-type and engine/propulsion vocabulary than HullQ currently consumes. No evidence supports building a second, parallel Power truth engine — doing so would violate the Owner decision (§4 point 6, §9 point 1) and the post-0088 contract (§2 row "Sail hard technical facets").

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

### 2.3 A second, qualified-concrete-claim candidate path — not a design-truth shortcut, and never an automatic-verification shortcut (amendment findings C, D)

`inventory_search.list_active_design_linked_listings` stays exactly as-is (it is the accepted, already-tested design-linked path — regression-protecting it is a hard constraint). A **second**, independently named and independently tested query/function is proposed: it admits a `NativeListing` whose `PhysicalBoat` is design-unresolved (`boat_design_ref IS NULL`) *only* when every one of the following evidence-threshold dimensions is satisfied for **each** criterion field the search request actually constrains — `VALUE_ASSERTION` completeness alone is explicitly **not** sufficient (correcting the original proposal's understatement):

1. **Current public eligibility:** the listing independently passes the same D29 gate (no weaker admission rule for design-unresolved inventory).
2. **Assertion kind:** the publishing Organization's current claim snapshot carries a `VALUE_ASSERTION` (not `UNKNOWN`/absent) for the field.
3. **Issuer provenance:** the claim records *who* is asserting it (the publishing Organization/broker, a named surveyor/inspection document, a manufacturer plate reading, etc.) — an anonymous or unattributed value is not usable evidence.
4. **Valid, criterion-matching unit:** the claim's unit matches the criterion's declared unit contract; a unit mismatch or missing unit is `INSUFFICIENT_DATA`, never silently coerced.
5. **Applicability:** the criterion must genuinely apply to this vessel's actual configuration (e.g. a keel-configuration claim on a vessel the same claim set describes as having no keel at all is inapplicable, not a value).
6. **Freshness / non-retraction:** the claim is the Organization's **current** revision; a retracted or superseded prior revision is never re-surfaced as current (see FIX-0090-09, FIX-0090-13).
7. **Contradiction check:** no unresolved conflicting claim exists for the same field from another authorized source (e.g. a corroborating inspection document that disagrees with the broker's own claim) — an unresolved contradiction is `CONFLICT`, not a tie-broken pick.
8. **Compatible measurement basis** (criterion-dependent, see §2.4): for any condition-qualified criterion, the request's stated condition must be compatible with the claim's own recorded basis.

Only when **all** applicable dimensions are satisfied may the claim back a `CONFIRMED_MATCH` for that criterion; failing any one dimension yields `INSUFFICIENT_DATA` (or `CONFLICT` for dimension 7), never a best-effort `CONFIRMED_MATCH`. The exact per-criterion evidence-threshold contract (which dimensions are mandatory for which field, and what counts as an acceptable issuer) is **not decided by this pack** — it is named here as an explicit obligation for whichever future slice (row B/C in §4) implements this path.

**Correction on evidentiary weight (amendment finding C):** a qualifying claim must be labeled `source_basis: PUBLISHER_CLAIM` and must **never** be rendered, stored, or returned to any consumer as `source_basis: DESIGN_CONFIRMED` or any other "independently verified" label — this directly implements the post-0088 contract §3 point 3's "laut Brokerangabe" vs. independently-verified-manufacturer-truth distinction (post-0088 contract §3 point 3). `PUBLISHER_CLAIM` is a statement that HullQ's evidence-threshold checks above passed, **not** a statement that HullQ (or anyone other than the publisher) has independently confirmed the fact is true. A publisher asserting a fact under HullQ's existing broker terms also does **not** by itself establish that the publisher holds reproduction/syndication rights over any attached third-party document or photograph used to support the claim (e.g. a scanned manufacturer plate image, a surveyor's PDF) — that is a separate, already-governed content-rights question under HullQ's existing broker/media terms, not resolved or widened by this proposal (amendment finding B).

This is an additive path. It must never downgrade or bypass the existing nine-dimension design-linked MUST/AND evaluation; a listing that has *both* a resolved design and a conflicting concrete claim must surface `CONFLICT`, never silently prefer one source. A *refit* claim (current engine differs from the design's original/factory engine) is not automatically a "conflict" with the design record at all — the two describe different temporal questions (originally-built-as vs. currently-equipped-as) — but the refit claim only governs *current-state* Search classification once it independently passes every threshold dimension above; absent that qualification it stays `INSUFFICIENT_DATA`, it is never presumed current merely because it exists (see the corrected FIX-0090-07 in the fixture corpus).

### 2.4 Conditional/operating-point measurement — a typed value object, not a bare scalar, and never sufficient from engine data alone (amendment finding G)

Speed/consumption/range claims require a dedicated value shape (proposal, not a committed schema): `OperatingPointClaim { speed_or_load_basis, sea_state_or_test_standard, fuel_reserve_margin, measurement_source, observed_at }` alongside the scalar. A bare `range_nm` field with no recorded basis must remain `INSUFFICIENT_DATA` for any Search criterion that claims a specific operating condition — tank-capacity-divided-by-burn-rate arithmetic is, at most, a visibly labeled derived estimate, never a confirmed operating-point fact (Owner decision §5 table row 4; post-0088 contract §3 point 5).

**Correction (amendment finding G):** an engine manufacturer's own published fuel-consumption/power curve (source-rights matrix Family 8) documents the *engine's* performance at a stated RPM/load on the manufacturer's own test setup — it is **not**, by itself, evidence of any specific vessel's actual range or consumption. A vessel-specific range/consumption claim additionally requires: (a) confirmation that this specific engine model/configuration is actually the one currently installed on *this* `PhysicalBoat` (a separate, independently qualified installed-equipment claim, not assumed from a design/brochure match); (b) the hull's actual displacement/loading and propeller/drivetrain configuration, which the engine manufacturer's curve does not know and cannot supply; and (c) a usable-fuel/reserve margin specific to the vessel's tankage. Engine-sheet data alone — even when fully basis-qualified for the engine itself — can at most support a visibly labeled, non-match-eligible *estimate* for this proposed model; it must **never** classify a vessel-specific conditional range/consumption criterion as `CONFIRMED_MATCH`. A `CONFIRMED_MATCH` on such a criterion requires a vessel-specific measurement or a vessel-specific documented test (see FIX-0090-10, corrected).

### 2.5 Import/export category vocabulary — corrected after direct inspection of the pinned NautiX 1.4 XSD (amendment finding E)

Direct inspection of `src/hullq/domain/nautix_schema/NautiX_v1.4.xsd` (the exact pinned asset `import_nautix.py` validates against, provenance `src/hullq/domain/nautix_schema/PROVENANCE.md`: retrieved 2026-10-12, SHA-256 `249fd6693fd032dc71d5138b64a39a3b018ffdf8e3c733101e95f6e4a2ddb91f`) shows the schema is **far richer than the original pack assumed**:

- the `BoatType` enumeration (XSD lines 182–264) already defines 14 `sail-*` tokens (including `sail-motorsailer`), **33** `power-*` tokens (`power-yacht`, `power-cabin`, `power-trawler`, `power-cruiser`, etc. — directly recounted on this HEAD, line 202–234), plus `inflatable-*`, `small-*` and `pwc-*` families;
- `engine_data/engine` (XSD lines ~2144–2170) supports up to ten engines per boat with `engine_type`, `fuel` (`FuelType` includes `electric`/`hybrid`), and power/capacity fields;
- `cruising_speed` and `max_speed` (XSD lines 1969–1994) each already carry `unit`, `range`, `range_unit`, `fuel_consumption` and `consumption_unit` attributes alongside the scalar speed value.

**The schema is not the bottleneck for category representation.** HullQ's own `_ACCEPTED_SAIL_BOAT_TYPES` import allow-list and the unconditional `_NAUTIX_CATALOG_BOAT_TYPE = "sail-yacht"` export constant are both HullQ-side scope decisions, not schema limitations — once HullQ has a real internal category value, mapping it to the *correct* existing `power-*`/`sail-*` token is fully representable today.

**The schema's genuine, source-proven limitation is narrower and different:**

1. `boat_types/type` is **mandatory** (`boat_types` itself has no `minOccurs="0"` inside `boat_data`, and `type` has no `minOccurs="0"` either; both default to required) and its value **must** be one of the fixed `BoatType` enumeration members — there is **no `unknown`/`conflict` member**. A listing whose `VesselCategory` is `UNKNOWN` or `CONFLICT` (the proposed §2.1 values) **cannot be represented in a schema-valid NautiX document at all** — there is no legal token to write. A future exporter must omit such a listing from NautiX output with an explicit warning, never invent a token (any token, including `sail-yacht`) to force validation to pass.
2. `cruising_speed`/`max_speed` carry only `range`/`range_unit`/`fuel_consumption`/`consumption_unit` — the schema has **no attribute for sea-state, test standard, load condition, or fuel-reserve margin**. The richer `OperatingPointClaim` basis metadata proposed in §2.4 therefore cannot be fully round-tripped through this exact writer: a future export must either drop that basis metadata (with a disclosed, visible warning that the condition qualification was not preserved) or wait for a future NautiX revision that can carry it — it must never emit the bare numeric speed/range/consumption values as if they still carried their original basis once written through this schema.

This replaces the original (incorrect, unverified) framing that the schema itself "cannot represent a real category." The export writer's true obligations are: (a) map every representable real category to its correct existing token, never a hardcoded placeholder; (b) refuse to emit any listing whose category is not legally representable (`UNKNOWN`/`CONFLICT`), with a disclosed warning, rather than guessing; (c) disclose the loss of operating-point basis metadata on export, since the schema has no field to carry it.

- Import: replace the single Sail allow-list with an explicit per-source category mapping table (`source token -> {SAIL, POWER, MOTORSAILER, UNKNOWN}`) that can now trivially cover the schema's already-existing `power-*`/`inflatable-*`/`small-*`/`pwc-*` tokens once HullQ's own supply-scope decision authorizes consuming them; tokens absent from the table (or outside whatever supply scope is accepted) stay rejected, exactly as today's fail-closed behavior already does.

### 2.6 What this proposal explicitly does not decide

- the final Power field names/units/enum vocabulary;
- whether `MOTORSAILER` gets its own criterion set or a documented subset-union of both;
- the exact SQL/ORM shape of the second candidate path;
- any UI/API wording for `source_basis` labeling;
- criterion ordinal numbers or bridge/third-copy evidence for any specific future slice.

Each of these is named explicitly in the implementation decision map (§4) as a separate future slice's own readiness obligation.

---

## 3. Source-rights register

See `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md` v0.2 for the full per-source-family register: **nine externally-sourced families (Wikidata, hull-OEM spec pages, EUR-Lex/RCD, ISO 8666, Boats Group/YachtWorld, fuel-consumption aggregators, engine-OEM documentation, historical archives, EU Fishing Fleet Register) plus the separately-tracked first-party broker-claim entry** (the latter is explicitly not a copyright/license question — see amendment finding B below and matrix Family 4; it is not counted toward the nine). Evidence quality across the nine is **not uniform** — six carry at least one directly fetched/searched piece of real evidence from this session, one (ISO 8666) is only indirectly corroborated, one (hull-OEM spec pages) restates a general pattern with no specific manufacturer source checked, and one (engine-OEM documentation) has zero evidence located at all (amendment finding I; see the matrix's own corrected-totals section for the exact breakdown). Each family carries a real, named source, an exact URL, an explicit access/review date, directly-checked vs. inherited-citation vs. access-blocked-in-this-session labeling, the actual license/terms text found (quoted where retrieved), an evidence-confidence note, and HullQ use-specific clearance per ADR-0005/OQ-007's framework. Summary disposition:

| Clearance class | Count | Representative families |
|---|---|---|
| GREEN | 1 | Wikidata (CC0-1.0, directly re-verified 2026-10-26) |
| GREEN, scope-limited precedent only | 1 | EU Open Data Portal Community Fishing Fleet Register (CC BY 4.0, directly verified) — a confirmed open-government vessel dataset, but scope is commercial fishing vessels, not recreational power craft; cited as a verified *pattern*, not a Power production source |
| AMBER / legal-review-leaning | 3 | manufacturer/OEM spec pages (no explicit license, directly inspected example scope); EUR-Lex/Directive 2013/53/EU text (CC BY 4.0 under Commission Decision 2011/833/EU, directly verified) distinguished from the ISO 8666 standard itself (paywalled, direct iso.org access blocked HTTP 403 in this session, indirectly corroborated only); engine/propulsion-manufacturer technical data sheets (official OEM page not located/verified in this session — see UNKNOWN row) |
| RED | 2 | Boats Group/YachtWorld/boats.com (directly confirmed robots.txt + ToS clause prohibiting automated access/data mining); third-party fuel-consumption aggregator mirror sites (directly found, no established license, unverified upstream rights) |
| UNKNOWN — access or rights not established in this session | 2 | historical/discontinued-manufacturer brochure archives (real URLs found, no reachable rights statement); official engine-OEM (e.g. Volvo Penta) terms of use — **searched for but not located/verified in this session; documented as a limitation, not filled speculatively** |
| N/A — not a license question, governed separately | 1 | first-party broker-attested concrete claims (HullQ's own existing intake/terms govern this, corrected per finding B below) |

**Correction (amendment finding J):** an earlier revision of this pack stated a blanket "no source is marked cleared for `bulk_bootstrap`," which directly contradicted the matrix's own Wikidata row (`bulk_bootstrap: allowed`, on the strength of its unconditional CC0 license). The accurate statement, distinguishing license rights from access conditions from actual ingestion approval, is: **Wikidata's `bulk_bootstrap` license dimension is `allowed`** because CC0 places no reuse restriction on it; its `automated_ingestion` dimension remains `conditional` on Wikidata's own API/rate-limit access rules, a separate and still-unsatisfied dimension; and **no actual ingestion job — bulk or otherwise, against Wikidata or any other source — is authorized or performed by this document.** Every other external family's `bulk_bootstrap` is `prohibited`, `unknown`, or `not applicable`, as stated in its own matrix row. This slice performs **zero** scraping, downloading, or bulk retrieval of any kind; every row is a desk-review citation with a retrieval date for the *rights statement itself*, not a data harvest, and Wikidata's favorable license status is not an exception to that — it is a license-dimension fact, not a performed or authorized action. Several rows in this amendment were checked live via web search/fetch on 2026-10-26 specifically to replace the original pack's generic, unverified family descriptions (amendment finding A) — see the matrix for exact URLs and quoted findings.

**Correction on broker-claim clearance (amendment finding B):** the original pack's Family 4 and §2.3 both understated what a broker's own attestation actually proves. Being the first-party publisher under HullQ's existing terms establishes that HullQ may lawfully store and search the *broker's own factual assertion* about *that broker's own offered vessel* — it does **not** by itself establish (a) that the asserted fact is independently accurate, (b) that the broker holds reproduction/redistribution rights over any third-party document, photograph, or manufacturer material attached in support of the claim, or (c) any clearance for HullQ to syndicate that supporting material onward. These remain separate, already-governed content-rights and factual-verification questions; this pack does not widen clearance for any of them. Likewise, "publicly accessible" government material (e.g. a national or EU open-data portal) is **not** automatically open-licensed — the EU Fishing Fleet Register row above is GREEN only because its specific CC BY 4.0 statement was directly verified; no other government registry is assumed to share that status, and a genuinely recreational/private-power-craft registry with an equivalent verified license has **not** been located in this pass (documented as a gap, not filled).

---

## 4. Future implementation decision map

Each row is a proposed future slice boundary with one independently testable failure domain. **No slice number is assigned here** — ordering and selection remain an explicit Owner act per the slice contract and `docs/HULLQ_OWNER_DECISION_SAIL_AND_POWER_FULL_TECHNICAL_PLATFORM_2026-10-22.md` §6's phase guardrails.

| # | Proposed scope | Prerequisites | Primary code touchpoints | Acceptance test shape | STOP threshold |
|---|---|---|---|---|---|
| A | Explicit `VesselCategory` claim (design + concrete), fail-closed unknown/conflict, cross-category Search exclusion test | None beyond this pack | `physical_boat_claims.py`, new migration, `criteria_registry.py` (category pre-filter wiring only) | Sail design cannot match Power query and vice versa; `UNKNOWN`/`CONFLICT` never silently resolve | Any attempt to infer category from hull/model text |
| B | Qualified concrete-claim candidate path for design-unresolved listings (§2.3), both categories | A (category must exist to scope the new path safely) | new `inventory_search` function (additive, existing function untouched), `native_inventory_query.py`, evidence `source_basis` tagging | Existing nine-dimension design-linked regression suite unchanged; new path admits only fully-qualified `VALUE_ASSERTION` claims; conflicting design+claim surfaces `CONFLICT` | Any regression in the existing design-linked result set; any silent claim-as-design-truth promotion |
| C | Power `CriterionDefinition` family #1 (one coherent dimension, e.g. propulsion configuration) | A, B | `criteria_registry.py` new definitions, `configuration_engine` reuse (no fork), new Power claim fields/migration | Fresh Power criterion ordinal evidence per `POST_0051_TRIGGER_GATES.md`; no second truth engine; Sail criteria/tests unaffected | Any Power-specific bypass of `evaluate_configuration` |
| D | `OperatingPointClaim` conditional measurement model (§2.4) | C (needs at least one Power numeric criterion to anchor against) | new value object + claim field, criterion read_claim extension | Range/speed/consumption claim without basis stays `INSUFFICIENT_DATA`; no tank÷burn auto-derivation treated as confirmed | Any confirmed match derived from an unlabeled scalar |
| E | Import/export category vocabulary (§2.5) | A | `import_nautix.py` mapping table, `inventory_export.py` per-row category-correct tag + mandatory `UNKNOWN`/`CONFLICT` omission-with-warning + operating-point-basis loss disclosure | Unrecognized source token rejected, not defaulted to Sail; export never writes a hardcoded placeholder tag; `UNKNOWN`/`CONFLICT` category is never exported through this writer (no legal schema token exists); `OperatingPointClaim` basis loss is visible, not silent | Any category coercion/placeholder tag on export; any silent operating-point basis loss |
| F | Power source-rights-cleared data acquisition (per `SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`, source-by-source) | None (can run in parallel with A–E as a research track) | no code — source rights review + `research/evidence/SOURCE_REGISTER.md` entries | Each source has an explicit use-specific clearance before any ingestion code is written | Any ingestion code written against an UNKNOWN/RED-cleared source |
| G | Power Buyer/Broker Search-fit parity using the exact Power truth kernel (no parallel scorer) | C, D | `broker_search_fit.py` extension, reuse only | Power Search-fit score traces to the same `evaluate_configuration` evidence Buyer search uses | Any Power-only scoring heuristic bypassing the shared kernel |
| H | #355 pre-real-external-data runtime hardening (parser isolation, admission/timeouts, archive-bomb guards) | None (independent of Sail/Power category work; already a standing P0 gate) | `api/app.py` import route, `persistence/connection.py`, `domain/import_spreadsheet.py` | Adversarial archive/timeout/resource tests pass under real execution, not static review | Any real external broker data accepted before this gate passes |

Rows F and H are pre-existing standing obligations (source rights, #355) restated here only to keep the dependency graph legible; they are **not new scope invented by this slice**.

---

## 5. Hard-case evidence corpus

See `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md` v0.2 for the full reproducible corpus (**thirteen** labeled synthetic cases, `FIX-0090-01` through `FIX-0090-13`, exceeding the eight-case minimum) covering: mono-hull Sail baseline, Sail multihull, motorsailer, Power planing/displacement, two model-generation/engine variants, a re-powered used boat (corrected per amendment finding C — the current claim governs only after passing the full evidence-threshold test in §2.3, never by automatic precedence), a design-unresolved but typed issuer-owned current claim, disputed/retracted engine hours, operating-condition-dependent range (corrected per amendment finding G — engine-sheet data alone can never back a vessel-specific `CONFIRMED_MATCH`), unknown category, category conflict, import→export category loss (corrected per amendment finding E to reflect the schema's actual, narrower limitation — see §2.5), and publisher retraction after publication. Each case records its expected classification outcome and the specific invariant it exercises; none use real buyer PII or real brokers.

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

- None found in the current repository's accepted code/docs. Old Sail-only wording in `import_nautix.py`/`inventory_export.py` docstrings is historically accurate for pre-pivot HEAD and does not misstate the current joint-product Owner decision; §1.3 above records this explicitly so a future reader does not mistake accurate historical commentary for a stale policy claim.
- **Self-correction (amendment, this revision):** the primary pack's own first-pass draft understated/mischaracterized three things, now corrected in place: (a) export was wrongly described as symmetrically "fail closed" with import — only import fails closed; export's fixed tag is unguarded, merely currently-correct-by-input-constraint (§1.3); (b) the NautiX 1.4 schema was assumed, without inspection, to lack Power category tokens — direct inspection shows it already has 33 `power-*` tokens (recounted; an earlier amendment pass of this same pack had miscounted 29) and rich engine/propulsion/hull-type vocabulary; the real schema limitation is narrower (no `UNKNOWN`/`CONFLICT` category token, no operating-point basis attributes) (§2.5); (c) the qualified-concrete-claim proposal originally implied `VALUE_ASSERTION` completeness alone was a sufficient evidence threshold — corrected to the eight-dimension threshold in §2.3.

---

## 7. Tracker update (proposed — requires explicit Owner/operator action)

Issue #372 should receive a comment linking to this pack and its two companion artifacts, **tracking-only, not closing #372**. Posting a GitHub comment is a shared-visibility action outside this agent's unilateral authority in this slice; the exact comment text is prepared for Owner review rather than posted automatically:

> SLICE-0090 (docs-only, REVIEW pending) delivered the read-only architecture/source-rights feasibility pack this tracker anticipated: `docs/research/SLICE-0090-SAIL-POWER-ARCHITECTURE-SOURCE-RIGHTS.md`, `docs/research/SLICE-0090-POWER-SOURCE-RIGHTS-MATRIX.md`, `docs/validation/SLICE-0090-HARD-CASE-FIXTURE-CORPUS.md`. Confirms the design-linked-only candidate-selection gap, the Sail-only import/export category gate, and proposes (not decides) a qualified concrete-claim candidate path, a Power `CriterionDefinition` family reusing the existing kernel, and a conditional operating-point measurement model. No code changed; #372 stays open pending Owner-selected follow-on slices per the decision map in §4 of the architecture pack.

---

## 8. Validation performed on this pack

- Manual re-verification of every file/line citation in §1 against the current slice-branch HEAD (not a historical baseline) — see inline file:symbol references.
- Internal consistency check: every proposal in §2 is traced to an existing, unmodified shared primitive (no proposal requires forking `evaluate_configuration`, `current_public_eligibility`, or the claim `AssertionKind` shape).
- **Amendment (2026-10-26, independent review response):** direct inspection of the pinned `NautiX_v1.4.xsd` (line-cited in §2.5) replacing an unverified assumption; direct live web search/fetch against named real sources for the rights matrix (Wikidata, EU Open Data Portal, EUR-Lex, Boats Group/YachtWorld robots.txt+ToS, third-party fuel-consumption aggregators, historical-archive mirrors) on 2026-10-26, with inaccessible sources (ISO 8666 full page, Boats Group EU ToS page, an official engine-OEM ToS) explicitly logged as access-blocked/not-located rather than filled speculatively — see matrix v0.2 review metadata for the per-source access log.
- Governance validator run: see slice completion report for `scripts/validate_repository.py` result.
- No PostgreSQL/API/browser runtime execution is claimed anywhere in this pack; all findings above the fixture corpus are static source/documentation review, consistent with this slice's DESIGN_RESEARCH type.
