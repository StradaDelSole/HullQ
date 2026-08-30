# HullQ — Marine Technical Entailment Contract

**Version:** 0.1
**Status:** PROPOSED — pending independent review and explicit Project Owner acceptance (SLICE-0036)
**Scope:** what may be derived, within the existing HullQ v0.6 technical vocabulary, when already-qualified source fact(s) definitionally or technically guarantee a further in-scope fact. Nothing else.
**Companion machine-readable registry:** `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`

## 1. Purpose

SLICE-0034 established that HullQ may only decompose/assert a fact when the source token logically guarantees it, never when it is merely typical. SLICE-0035 lets qualified categorical/configuration-aware values authorize search truth (`CONFIRMED_MATCH` / `CONFIRMED_NON_MATCH`).

Those two facts together create a correctness boundary that did not previously have one finite, versioned, testable home: if ad-hoc marine "this usually implies that" reasoning were allowed to run ahead of search evaluation, it could manufacture false confirmed matches or false confirmed non-matches. This contract is that home. It is bounded to the fixed field inventory in section 2; it is not an open-ended marine ontology project, a generic inference engine, or a change to `SEARCH_QUERY_SEMANTICS.v0.1.md`.

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

- **`DEFINITIONAL_ENTAILMENT`** — the source fact, once qualified, definitionally or technically guarantees an exact cross-field output (or a bounded count relation such as "at least 1" / "at least 2"). Recorded as a full rule in the registry.
- **`DIRECT_ONLY`** — the fact is real and usable directly (e.g. for search filtering on its own field), but authorizes no cross-field derivation. No relevant rule exists because none is safe.
- **`NO_DERIVATION`** — ambiguity, source-dependent meaning, a relevant maritime exception, sentinel/free-text semantics, or absence of an accepted basis prevents any derived truth. This includes every `unknown` token (absence of information) and every `other` token (an opaque escape value that, by construction, proves nothing about any specific dimension) across every field in the inventory, and every free-text field (`keel_subtype`, `centerboard_type`, `daggerboard_type`, `rig_variant`) in full.

`not_applicable` (the one place it exists — `rig.masthead_fractional`) is `DIRECT_ONLY`, not a sentinel: it is a legitimate, concrete negative fact when freshly and separately established by evidence, distinct from not knowing. This contract's own rules never assert it (see section 6).

Numeric count fields (`hull_count`, `centerboard_count`, `daggerboard_count`, `rudder_count`, `mast_count`, `cockpit_count`, `helm_count`) are `DIRECT_ONLY` as a general fact, with specific concrete values (chiefly `0`) carrying their own `DEFINITIONAL_ENTAILMENT` rule where a schema-level structural certainty exists (section 5.4).

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

## 5. Authorized `DEFINITIONAL_ENTAILMENT` rules (summary)

The full normative detail (prerequisites, applicability, exceptions, conflict behavior, evidence basis, lineage requirement) lives in `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`. This section is a human-readable index, not a substitute.

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
| `MTE-KEEL-003` | `centerboard_count=0 -> centerboard_type` cannot be concrete |
| `MTE-KEEL-004` | `daggerboard_count=0 -> daggerboard_type` cannot be concrete |

No other `keel_type` token (full, modified_full, long_fin, fin, wing, bulb, twin, bilge, swing, lifting, shoal) entails a board count of zero: keel-centerboard and other hybrid appendage constructions exist, and absence is not negative evidence.

### 5.3 Rudder/skeg

| Rule | Entailment |
|---|---|
| `MTE-RUD-001` | `rudder_count=0 -> rudder_position=unknown, rudder_support=unknown, rudder_balance=unknown` |
| `MTE-RUD-002` | `rudder_support=skeg -> skeg_type != none` |
| `MTE-RUD-003` | `skeg_type=none -> rudder_support != skeg` |

`rudder_position` and `rudder_support` remain independently structured in v0.6-native data: a transom-positioned rudder can carry keel/skeg support semantics (see `fixtures/technical_profile/valid/01_classic_aft_cockpit_masthead_sloop.json`), so no v0.6-native `rudder_position` or `rudder_support` token entails the other beyond `MTE-RUD-002`/`MTE-RUD-003`.

### 5.4 Rig

| Rule | Entailment |
|---|---|
| `MTE-RIG-001` | `sailplan=sloop -> mast_count=1` |
| `MTE-RIG-002` | `sailplan=cutter -> mast_count=1` |
| `MTE-RIG-003` | `sailplan=cat -> mast_count=1` |
| `MTE-RIG-004` | `sailplan=ketch -> mast_count=2` |
| `MTE-RIG-005` | `sailplan=yawl -> mast_count=2` |
| `MTE-RIG-006` | `sailplan=schooner -> mast_count >= 2` (bound only; exact count not guaranteed) |

`sailplan` never entails `masthead_fractional` in v0.6-native data — see section 6 for why `cat` is deliberately not an exception.

### 5.5 Cockpit/helm

| Rule | Entailment |
|---|---|
| `MTE-DECK-001` | `cockpit_count=0 -> cockpit_position=unknown` |
| `MTE-DECK-002` | `helm_count=0 -> helm_type=unknown` |

`helm_type` (tiller/wheel) never entails `helm_count`: twin-wheel installations exist, so a wheel or tiller helm does not guarantee a specific station count.

### 5.6 Legacy v0.5 `rig_type` (preserved SLICE-0034 semantics)

`MTE-LEGACY-RIG-001` through `MTE-LEGACY-RIG-009` reproduce `BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.1 verbatim: `masthead_sloop`/`fractional_sloop` entail both `sailplan` and `masthead_fractional`; `cutter`/`ketch`/`yawl`/`schooner`/`cat_rig` entail only `sailplan` (never `masthead_fractional`, which stays `unknown`); `other`/`unknown` project the same opaque word into `sailplan` with no new information gained.

### 5.7 Legacy v0.5 `rudder_type` (preserved SLICE-0034 semantics)

`MTE-LEGACY-RUD-001` through `MTE-LEGACY-RUD-008` reproduce `BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.2 verbatim, including:

- `keel_hung -> rudder_support=keel`; `skeg_hung`/`partial_skeg -> rudder_support=skeg`; `spade -> rudder_support=free`; `transom_hung -> rudder_position=transom, rudder_support=transom`;
- `rudder_balance` is never entailed by any legacy `rudder_type` token (always `unknown`);
- `twin` entails `rudder_count`: a `null` source count projects to `2` (the guaranteed reading of the word itself); a source count already `2` stays `2`; any other concrete source count (`0`, `1`, `3`, `4`, ...) is an internally inconsistent predecessor payload and is flagged for conflict resolution rather than silently resolved either way — the accepted `RudderCountMappingConflict` behavior.

## 6. Deliberate non-entailments (maritime-exception / definitional-uncertainty cases)

These were specifically considered and rejected, to make the boundary auditable rather than merely absent:

1. **`sailplan=cat -> masthead_fractional=not_applicable` — declined.** An unstayed cat rig is a textbook example of where `not_applicable` is legitimate, and `BOAT_DESIGN_V05_TO_V06_MAPPING.md` names it as such. But whether every `sailplan=cat` record is truly unstayed is a maritime-exception judgment call (cat-ketch and other hybrid unstayed/stayed constructions exist) that lies outside the plain meaning of the controlled `cat` token itself. Consistent with the mapping doc's own hedge on this exact point, this contract does not assert it. A future slice may authorize it explicitly if a controlling artifact establishes the basis.
2. **`rudder_position -> rudder_support` (or the reverse), in v0.6-native data — declined.** The whole point of the v0.6 decomposition is that a transom-positioned rudder can independently carry keel/skeg support semantics. Treating position as a proxy for support (or vice versa) would silently re-collapse a distinction v0.6 exists to preserve.
3. **`keel_type` (non-board values) -> `centerboard_count=0` / `daggerboard_count=0` — declined.** Hybrid keel-plus-centerboard and similar constructions exist; a fin or full keel does not prove the absence of an auxiliary board, and absence is never negative evidence.
4. **`skeg_type∈{full,partial}` -> `rudder_support=skeg` — declined.** A skeg-equipped hull can still carry a rudder the skeg does not structurally support (e.g. an unrelated outboard/transom rudder on a hull with a shaft-protecting skeg). Only the reverse exclusion (`rudder_support=skeg -> skeg_type != none`, `MTE-RUD-002`/`MTE-RUD-003`) is safe.
5. **`rudder_type=skeg_hung`/`partial_skeg` -> `skeg_type=full`/`partial` — declined**, reusing `BOAT_DESIGN_V05_TO_V06_MAPPING.md` section 3.4's own reasoning: reading `skeg_hung` as "full skeg" depends on contrast with its sibling enum value `partial_skeg`, not on `skeg_hung` taken in isolation — the same enum-sibling-exclusivity reasoning already rejected for `rudder_position=underhull`.
6. **`helm_type` (tiller/wheel) -> `helm_count` — declined.** Twin-wheel and twin-tiller installations exist; the steering mechanism type does not guarantee a station count.
7. **`sailplan=schooner` -> an exact `mast_count` — declined beyond the `>=2` bound.** Two-masted schooners are typical but three-or-more-masted schooners exist; only the lower bound is definitionally guaranteed.

## 7. Directions explicitly not authorized (reverse-inference safety)

| Forward rule(s) | Reverse direction | Why unsafe |
|---|---|---|
| `MTE-HULL-001..003` | `hull_count -> hull_configuration` | An allowed `other` topology can share any concrete hull count with monohull/catamaran/trimaran; hull count alone never uniquely identifies the named topology. |
| `MTE-RIG-001..006` | `mast_count -> sailplan` | `mast_count=1` does not uniquely identify sloop/cutter/cat; `mast_count=2` does not uniquely identify ketch/yawl/a two-masted schooner. |
| `MTE-KEEL-001`/`002` | `centerboard_count>=1` / `daggerboard_count>=1 -> keel_type=centerboard`/`daggerboard` | A boat can carry an auxiliary centerboard/daggerboard alongside a different primary keel type (hybrid construction); a positive board count does not prove the board IS the primary keel-equivalent appendage. |

## 8. Free-text fields (full non-entailment)

`appendages.keel_subtype`, `appendages.centerboard_type`, `appendages.daggerboard_type` and `rig.rig_variant` are unstructured strings with no closed vocabulary in any controlling artifact. No arbitrary string value in any of these fields authorizes a derived fact in v0.1, regardless of its content. They remain directly reportable/searchable as free text; they are simply never an entailment source.

## 9. Relationship to existing structural invariants

`BOAT_DESIGN_SCHEMA.v0.6.json` already enforces several of the relations in section 5 as `allOf`/`if`/`then` schema invariants (`hull_configuration`/`hull_count` agreement when both are concretely present; `skeg_type=none` vs `rudder_support=skeg` mutual exclusion; a zero appendage count vs a concrete descriptor of that appendage; `rudder_count=0`/`cockpit_count=0`/`helm_count=0` forcing their sibling fields to `unknown`). This contract does not change or duplicate that schema. It exists because the schema invariants only *reject invalid combinations when both fields are already concretely present* — they do not *populate* a missing field. A search-projection consumer that needs `hull_count` before schema validation runs, or that receives a partial qualified-fact stream rather than a complete schema instance, needs the same certainty stated as an explicit, testable derivation rule. Sections 5.1–5.5 state exactly that, no more.

## 10. Non-goals

This contract does not: add taxonomy or enum values; build a generic or recursive inference engine; admit any real BoatDesign; change `SEARCH_QUERY_SEMANTICS.v0.1.md` truth semantics; convert confidence/likelihood into truth; resolve any `OQ-*` question; or authorize Oceanis 30.1 research/admission (explicitly out of scope for SLICE-0036).
