# HullQ — Marine Technical Entailment Contract

**Version:** 0.1
**Status:** PROPOSED — pending independent review and explicit Project Owner acceptance (SLICE-0036)
**Scope:** what may be derived, within the existing HullQ v0.6 technical vocabulary, when already-qualified source fact(s) definitionally or technically guarantee a further in-scope fact. Nothing else.
**Companion machine-readable registry:** `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`
**Companion mechanical verification:** `tests/contract/test_marine_technical_entailment.py` — this contract intentionally ships no production inference/projection code under `src/`; the registry is validated and its declarative semantics are proven exclusively by test-only tooling (see section 8).

## 1. Purpose

SLICE-0034 established that HullQ may only decompose/assert a fact when the source token logically guarantees it, never when it is merely typical. SLICE-0035 lets qualified categorical/configuration-aware values authorize search truth (`CONFIRMED_MATCH` / `CONFIRMED_NON_MATCH`).

Those two facts together create a correctness boundary that did not previously have one finite, versioned, testable home: if ad-hoc marine "this usually implies that" reasoning were allowed to run ahead of search evaluation, it could manufacture false confirmed matches or false confirmed non-matches. This contract is that home. It is bounded to the fixed field inventory in section 2; it is not an open-ended marine ontology project, a generic inference engine, or a change to `SEARCH_QUERY_SEMANTICS.v0.1.md`.

This is a **DESIGN_RESEARCH** artifact: a declarative classification and coverage registry, proven by contract tests. It is deliberately **not** a production truth-authorizing runtime. No component under `src/` executes, projects, or authorizes any of the facts described here; a future IMPLEMENTATION slice that wires this contract into an actual search/persistence projection pipeline is a separate, later, explicitly-scoped decision.

## 2. Fixed field inventory

Exactly these existing `BOAT_DESIGN_SCHEMA.v0.6.json` paths (and their NamedVariant/DesignOption override equivalents), plus the two legacy `BOAT_DESIGN_SCHEMA.v0.5.json` enums preserved for SLICE-0034 compatibility, are in scope:

- **Hull/multihull:** `configuration.hull_configuration`, `configuration.hull_count`
- **Keel/boards:** `appendages.keel_type`, `keel_subtype`, `centerboard_count`, `centerboard_type`, `daggerboard_count`, `daggerboard_type`
- **Rudder/skeg:** `appendages.rudder_count`, `rudder_position`, `rudder_support`, `rudder_balance`, `skeg_type`
- **Rig:** `rig.sailplan`, `masthead_fractional`, `mast_count`, `mast_step`, `rig_variant`
- **Cockpit/helm:** `deck.cockpit_position`, `cockpit_count`, `helm_type`, `helm_count`
- **Legacy (SLICE-0034 compatibility only):** v0.5 `configuration.rig_type`, `configuration.rudder_type`

No other field family, enum value or taxonomy concept is introduced by this contract.

## 3. Three classifications

Every controlled enum token in the fixed inventory above, and every free-text field in that inventory, is classified as exactly one of:

- **`DEFINITIONAL_ENTAILMENT`** — the source fact, once qualified, definitionally or technically guarantees an exact cross-field output (or a bounded relation such as "at least 1" / "at least 2" / "not this one value" / "not a concrete value" — see section 7 for the exact allowed output shapes). Recorded as a full rule in the registry.
- **`DIRECT_ONLY`** — the fact is real and usable directly (e.g. for search filtering on its own field), but authorizes no cross-field derivation. No relevant rule exists because none is safe.
- **`NO_DERIVATION`** — ambiguity, source-dependent meaning, a relevant maritime exception, sentinel/free-text semantics, or absence of an accepted basis prevents any derived truth. **This includes every `unknown` token and every `other` token, in every field in the fixed inventory without exception — including the two legacy v0.5 enums.** An opaque escape value (`other`) proves nothing about any specific dimension by construction; an absent-information sentinel (`unknown`) never authorizes a cross-field fact under the "absence is not negative evidence" rule (section 4). Free-text fields (`keel_subtype`, `centerboard_type`, `daggerboard_type`, `rig_variant`) are `NO_DERIVATION` in full.

`not_applicable` (the one place it exists — `rig.masthead_fractional`) is `DIRECT_ONLY`, not a sentinel: it is a legitimate, concrete negative fact when freshly and separately established by evidence, distinct from not knowing. This contract's own rules never assert it (see section 6).

Numeric count fields (`hull_count`, `centerboard_count`, `daggerboard_count`, `rudder_count`, `mast_count`, `cockpit_count`, `helm_count`) are `DIRECT_ONLY` as a general fact, with specific concrete values (chiefly `0`) carrying their own `DEFINITIONAL_ENTAILMENT` rule where a schema-level structural certainty exists (section 5.4).

### 3.1 The legacy `other`/`unknown` rows are migration facts, not MTE entailments

`BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.1/3.2 (the pre-existing, separately-tested, accepted SLICE-0034 compatibility table) records that a v0.5 `rig_type`/`rudder_type` value of `other`/`unknown` translates into a v0.6 `sailplan` (or `rudder_position`/`rudder_support`/`rudder_balance`) value of the same opaque word. That table, and its regression test (`tests/contract/test_boat_design_v05_to_v06_mapping_conservatism.py`), are **unchanged by this contract** and remain the controlling word-for-word v0.5→v0.6 field-shape/rename mapping.

This entailment contract is a different, stricter concern: it classifies whether a fact **authorizes new cross-field search truth**, not whether a value can be losslessly relabeled into the new field name. Relabeling `other` into `other` (or `unknown` into `unknown`) is a structural rename, not a substantive fact — it gains no new information a search evaluator could act on. Accordingly, `legacy.rig_type` and `legacy.rudder_type` classify `other`/`unknown` as `NO_DERIVATION` here, consistent with the universal sentinel rule applied to every other field in this registry, and no `MTE-LEGACY-RIG-*`/`MTE-LEGACY-RUD-*` rule exists for either token. This does not reopen, weaken, or contradict the accepted mapping table itself.

## 4. Mandatory epistemic rules (binding on every rule in the registry)

1. **Definition/necessity only.** A rule may exist only when the qualified input definitionally/technically guarantees the output. "Usually", "typically", "commonly", design convention, statistical correlation, visual plausibility and model-family familiarity are never a sufficient basis, full stop.
2. **No artificial UNKNOWN.** Where a qualified fact genuinely entails another in-scope fact, the entailment is recorded and used — not discarded out of excess caution. `rudder_type=twin -> rudder_count=2` is the running accepted example.
3. **Absence is not negative evidence.** Missing/null/unknown data never implies absence or an opposite category. No rule in this registry treats `unknown` as if it meant "not present."
4. **Applicability before conflict.** Every rule's `applicability` clause requires all supporting facts to belong to the same materially relevant BoatDesign/NamedVariant/DesignOption/configuration scope. A rule never combines facts qualified in different scopes into a synthetic derivation.
5. **Explicit contradiction is never overwritten.** Every rule's `conflict_behavior` requires surfacing `UNRESOLVED_CONFLICT` (per `TECHNICAL_PROFILE_SPEC.v0.1.md` sections 5–6) when a same-scope qualified explicit fact disagrees with what the rule would otherwise derive. No rule silently picks a winner.
6. **Directionality; no unsafe reverse inference.** `A -> B` never authorizes `B -> A` unless a separate, independently justified rule establishes that direction. Section 7 records every direction this contract explicitly declined to authorize.
7. **No recursive generic inference.** Every rule is a single hop from its named qualified input(s) to its output(s). Nothing in this contract chains rule outputs back into further rule inputs, and nothing here is a general-purpose or probabilistic inference runtime.
8. **Free text and sentinels cannot manufacture truth.** `keel_subtype`, `centerboard_type`, `daggerboard_type` and `rig_variant` are non-entailing in full, by construction, regardless of their string content. `unknown`/`other`/null never authorize a more concrete derived fact.
9. **Derived lineage is mandatory.** Every `DEFINITIONAL_ENTAILMENT` rule's `lineage_requirement` names the rule ID, version, the exact qualifying input fact(s) and their applicability scope, so a derived fact remains distinguishable from a directly reported one. This contract does not design a new persistence mechanism for that lineage; it states the requirement for whichever component performs the projection.

### 4.1 Guard policy: the same nine rules, as one machine-checkable structure

Rules 3–5 and 9 above are not merely prose: every rule in `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json` references a single shared, versioned `guard_policies.STANDARD_MTE_GUARD_V0_1` object with structured boolean/enum fields (`requires_source_qualified`, `forbids_provisional_source`, `forbids_unresolved_conflict_source`, `forbids_applicability_unknown_source`, `requires_single_material_scope`, `cross_scope_combination_authorized: false`, `same_scope_explicit_contradiction_behavior: "UNRESOLVED_CONFLICT"`, `requires_lineage: true`). Every rule in v0.1 references the identical policy — there is no rule-specific guard, because these nine mandatory rules are contract-wide invariants, not per-rule judgment calls.

`tests/contract/test_marine_technical_entailment.py` includes a small, explicitly TEST-ONLY reference evaluator that mechanically applies this structured guard policy against synthetic qualification states (confirmed, provisional, unresolved-conflict, applicability-unknown, missing, cross-scope, same-scope-contradictory) and proves the required outcome in each case (authorized / `UNKNOWN` / `UNRESOLVED_CONFLICT`). This evaluator exists solely to prove the declarative semantics are internally consistent; it is not shipped under `src/`, is not wired into any search/persistence path, and must not be mistaken for a production inference engine.

## 5. Authorized `DEFINITIONAL_ENTAILMENT` rules (summary)

The full normative detail (prerequisites, applicability, exceptions, conflict behavior, evidence basis, lineage requirement, guard reference) lives in `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`. This section is a human-readable index, not a substitute. v0.1 authorizes **31** rules in total.

### 5.1 Hull/multihull

| Rule | Entailment |
|---|---|
| `MTE-HULL-001` | `hull_configuration=monohull -> hull_count=1` |
| `MTE-HULL-002` | `hull_configuration=catamaran -> hull_count=2` |
| `MTE-HULL-003` | `hull_configuration=trimaran -> hull_count=3` |

These verify/preserve the existing v0.6 schema certainties. The reverse direction (`hull_count -> hull_configuration`) is explicitly **not** authorized (section 7): an allowed `other` topology can share any of these hull counts.

### 5.2 Keel/boards

| Rule | Entailment |
|---|---|
| `MTE-KEEL-001` | `keel_type=centerboard -> centerboard_count >= 1` |
| `MTE-KEEL-002` | `keel_type=daggerboard -> daggerboard_count >= 1` |
| `MTE-KEEL-003` | `centerboard_count=0 -> centerboard_type` must not carry a concrete value |
| `MTE-KEEL-004` | `daggerboard_count=0 -> daggerboard_type` must not carry a concrete value |

`MTE-KEEL-001`/`002`'s evidence basis is an **internal HullQ controlled-vocabulary identity**, not external maritime research: the v0.6 `keel_type` enum value's own literal word (`centerboard`/`daggerboard`) is the same controlled word `BOAT_DESIGN_SCHEMA.v0.6.json` uses to name the corresponding appendage-count field's subject — the same class of reasoning already accepted in SLICE-0034 for `masthead_sloop`/`fractional_sloop`. No other `keel_type` token (full, modified_full, long_fin, fin, wing, bulb, twin, bilge, swing, lifting, shoal) entails a board count of zero: keel-centerboard and other hybrid appendage constructions exist, and absence is not negative evidence.

### 5.3 Rudder/skeg

| Rule | Entailment |
|---|---|
| `MTE-RUD-001` | `rudder_count=0 -> rudder_position=unknown, rudder_support=unknown, rudder_balance=unknown` |
| `MTE-RUD-002` | `rudder_support=skeg -> skeg_type != none` |
| `MTE-RUD-003` | `skeg_type=none -> rudder_support != skeg` |

`rudder_position` and `rudder_support` remain independently structured in v0.6-native data: a transom-positioned rudder can carry keel/skeg support semantics (see `fixtures/technical_profile/valid/01_classic_aft_cockpit_masthead_sloop.json`), so no v0.6-native `rudder_position` or `rudder_support` token entails the other beyond `MTE-RUD-002`/`MTE-RUD-003`. Both of these exclusions are driven by a **positive** qualified source fact (`rudder_support` IS `skeg`; `skeg_type` IS `none`) — never by an absence — which is the distinction that keeps them from becoming the "inference from absence" the mandatory rules forbid.

### 5.4 Rig

| Rule | Entailment | Authoritative source |
|---|---|---|
| `MTE-RIG-001` | `sailplan=sloop -> mast_count=1` | Encyclopaedia Britannica, "sloop" (britannica.com/technology/sloop) |
| `MTE-RIG-002` | `sailplan=cutter -> mast_count=1` | Encyclopaedia Britannica, "cutter" (britannica.com/technology/cutter-sailing-craft) |
| `MTE-RIG-003` | `sailplan=cat -> mast_count=1` | Merriam-Webster, "catboat" (merriam-webster.com/dictionary/catboat) |
| `MTE-RIG-004` | `sailplan=ketch -> mast_count=2` | Britannica Dictionary, "ketch" (britannica.com/dictionary/ketch) |
| `MTE-RIG-005` | `sailplan=yawl -> mast_count=2` | Encyclopaedia Britannica, "Yawl" (britannica.com/technology/yawl) |
| `MTE-RIG-006` | `sailplan=schooner -> mast_count >= 2` (bound only; exact count not guaranteed) | Encyclopaedia Britannica, "schooner" (britannica.com/technology/schooner): "two or more masts" |

These six rules were the subject of bounded authoritative research performed for this amendment (not general model knowledge); the exact quoted definition, locator and retrieval context for each is recorded in the registry's `evidence_basis` field. `sailplan` never entails `masthead_fractional` in v0.6-native data — see section 6 for why `cat` is deliberately not an exception.

### 5.5 Cockpit/helm

| Rule | Entailment |
|---|---|
| `MTE-DECK-001` | `cockpit_count=0 -> cockpit_position=unknown` |
| `MTE-DECK-002` | `helm_count=0 -> helm_type=unknown` |

`helm_type` (tiller/wheel) never entails `helm_count`: twin-wheel installations exist, so a wheel or tiller helm does not guarantee a specific station count.

### 5.6 Legacy v0.5 `rig_type` (preserved SLICE-0034 semantics; `other`/`unknown` excluded — see section 3.1)

`MTE-LEGACY-RIG-001` through `MTE-LEGACY-RIG-007` reproduce `BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.1's positive rows verbatim: `masthead_sloop`/`fractional_sloop` entail both `sailplan` and `masthead_fractional`; `cutter`/`ketch`/`yawl`/`schooner`/`cat_rig` entail only `sailplan` (never `masthead_fractional`, which stays `unknown`). `other` and `unknown` are `NO_DERIVATION` in this contract (section 3.1) — no `MTE-LEGACY-RIG-008`/`009` rule exists.

### 5.7 Legacy v0.5 `rudder_type` (preserved SLICE-0034 semantics; `other`/`unknown` excluded — see section 3.1)

`MTE-LEGACY-RUD-001` through `MTE-LEGACY-RUD-006` reproduce `BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.2's positive rows verbatim, including:

- `keel_hung -> rudder_support=keel`; `skeg_hung`/`partial_skeg -> rudder_support=skeg`; `spade -> rudder_support=free`; `transom_hung -> rudder_position=transom, rudder_support=transom`;
- `rudder_balance` is never entailed by any legacy `rudder_type` token (always `unknown`);
- `twin` entails `rudder_count`: a `null` source count projects to `2` (the guaranteed reading of the word itself); a source count already `2` stays `2`; any other concrete source count (`0`, `1`, `3`, `4`, ...) is an internally inconsistent predecessor payload and is flagged for conflict resolution rather than silently resolved either way — the accepted `RudderCountMappingConflict` behavior. This is the one rule in v0.1 using the closed, single-purpose `conditional` output shape (section 7).

`other` and `unknown` are `NO_DERIVATION` in this contract (section 3.1) — no `MTE-LEGACY-RUD-007`/`008` rule exists.

## 6. Deliberate non-entailments (maritime-exception / definitional-uncertainty cases)

These were specifically considered and rejected, to make the boundary auditable rather than merely absent:

1. **`sailplan=cat -> masthead_fractional=not_applicable` — declined.** An unstayed cat rig is a textbook example of where `not_applicable` is legitimate, and `BOAT_DESIGN_V05_TO_V06_MAPPING.md` names it as such. But whether every `sailplan=cat` record is truly unstayed is a maritime-exception judgment call (cat-ketch and other hybrid unstayed/stayed constructions exist) that lies outside the plain meaning of the controlled `cat` token itself. Consistent with the mapping doc's own hedge on this exact point, this contract does not assert it. A future slice may authorize it explicitly if a controlling artifact establishes the basis.
2. **`rudder_position -> rudder_support` (or the reverse), in v0.6-native data — declined.** The whole point of the v0.6 decomposition is that a transom-positioned rudder can independently carry keel/skeg support semantics. Treating position as a proxy for support (or vice versa) would silently re-collapse a distinction v0.6 exists to preserve.
3. **`keel_type` (non-board values) -> `centerboard_count=0` / `daggerboard_count=0` — declined.** Hybrid keel-plus-centerboard and similar constructions exist; a fin or full keel does not prove the absence of an auxiliary board, and absence is never negative evidence.
4. **`skeg_type∈{full,partial}` -> `rudder_support=skeg` — declined.** A skeg-equipped hull can still carry a rudder the skeg does not structurally support (e.g. an unrelated outboard/transom rudder on a hull with a shaft-protecting skeg). Only the reverse exclusion (`rudder_support=skeg -> skeg_type != none`, `MTE-RUD-002`/`MTE-RUD-003`) is safe.
5. **`rudder_type=skeg_hung`/`partial_skeg` -> `skeg_type=full`/`partial` — declined**, reusing `BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.4's own reasoning: reading `skeg_hung` as "full skeg" depends on contrast with its sibling enum value `partial_skeg`, not on `skeg_hung` taken in isolation — the same enum-sibling-exclusivity reasoning already rejected for `rudder_position=underhull`.
6. **`helm_type` (tiller/wheel) -> `helm_count` — declined.** Twin-wheel and twin-tiller installations exist; the steering mechanism type does not guarantee a station count.
7. **`sailplan=schooner` -> an exact `mast_count` — declined beyond the `>=2` bound.** Two-masted schooners are typical but three-or-more-masted schooners exist (Britannica's own "schooner" definition says "two or more"); only the lower bound is definitionally guaranteed.
8. **`legacy.rig_type=other`/`unknown` and `legacy.rudder_type=other`/`unknown` as MTE entailments — declined** (see section 3.1). These remain valid v0.5→v0.6 shape-migration facts in the pre-existing, unchanged `BOAT_DESIGN_V05_TO_V06_MAPPING.md` compatibility table, but a structural field rename of an opaque/absent-information word is not a substantive cross-field truth entailment, so this contract classifies both as `NO_DERIVATION` and defines no rule for them.

## 7. Rule output grammar (bounded, closed)

Every `DEFINITIONAL_ENTAILMENT` rule's `output` entries use exactly one of five closed shapes, defined in `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`'s top-level `output_operators` object. No other key/operator is permitted; an unrecognized shape is a contract violation, not a silent no-op.

| Operator | Meaning | Authorizes |
|---|---|---|
| `value` | Exact positive value assertion: the target field's true value IS this literal (enum token, integer, or the sentinel string `unknown`). | Positive truth |
| `relation` (`>=1`, `>=2`; integer fields only) | Inclusive lower-bound assertion. The target's true value is at least N; the exact value is not asserted and must not be silently upgraded to one. | Positive bound truth |
| `excludes_value` (enum fields only) | Negative assertion: the target's true value is NOT this one specific token. No other value is positively asserted. | Negative truth (single exclusion) |
| `not_concrete` (free-text fields only) | Negative assertion: the target must not carry any concrete (non-null) value. Used only when a paired qualified count fact structurally forecloses any concrete descriptor existing — a positive qualified fact driving a negative conclusion, never an inference from the free-text field's own absence. | Negative truth (no concrete value) |
| `conditional` | A closed, single-purpose piecewise output reserved exclusively for `MTE-LEGACY-RUD-006` (the accepted SLICE-0034 twin/rudder_count case). v0.1 does **not** generalize this into a reusable conditional-output mechanism; a second rule wishing to use it requires an explicit accepted decision, not a routine registry edit. |Single documented exception (`RAISE_CONFLICT` on a contradictory co-input) |

`excludes_value` is retained in v0.1 (`MTE-RUD-002`/`MTE-RUD-003`) because in both cases the exclusion is derived from a **stated positive fact** (`rudder_support` IS `skeg`; `skeg_type` IS `none`) — never from silence or a missing value — and both directions are independently declared and independently tested (`tests/contract/test_marine_technical_entailment.py`), including the same-scope-contradiction and reverse-direction cases. If a future proposed rule cannot make this same positive-fact-driven distinction, it must be downgraded to `NO_DERIVATION` rather than stretching this operator.

## 8. Relationship to existing structural invariants

`BOAT_DESIGN_SCHEMA.v0.6.json` already enforces several of the relations in section 5 as `allOf`/`if`/`then` schema invariants (`hull_configuration`/`hull_count` agreement when both are concretely present; `skeg_type=none` vs `rudder_support=skeg` mutual exclusion; a zero appendage count vs a concrete descriptor of that appendage; `rudder_count=0`/`cockpit_count=0`/`helm_count=0` forcing their sibling fields to `unknown`). This contract does not change or duplicate that schema. It exists because the schema invariants only *reject invalid combinations when both fields are already concretely present* — they do not *populate* a missing field. A search-projection consumer that needs `hull_count` before schema validation runs, or that receives a partial qualified-fact stream rather than a complete schema instance, needs the same certainty stated as an explicit, testable derivation rule. Sections 5.1–5.5 state exactly that, no more.

This contract, and its companion test module, deliberately contain **no production inference/projection runtime**. `tests/contract/test_marine_technical_entailment.py` loads and validates the JSON registry directly (no shared `src/` loader module exists for it), and any function that *applies* a rule to a synthetic input (e.g. the twin/rudder_count reference projection, or the guard-policy reference evaluator in section 4.1) is explicitly TEST-ONLY, is not exported from any `src/` package, and is not reachable from search/persistence runtime code.

## 9. Non-goals

This contract does not: add taxonomy or enum values; build a generic or recursive inference engine; ship a production truth-projection/inference runtime under `src/`; admit any real BoatDesign; change `SEARCH_QUERY_SEMANTICS.v0.1.md` truth semantics; convert confidence/likelihood into truth; resolve any `OQ-*` question; or authorize Oceanis 30.1 research/admission (explicitly out of scope for SLICE-0036).
