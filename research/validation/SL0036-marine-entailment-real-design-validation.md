# SLICE-0036 — Real-design validation of the marine-technical entailment contract

**Status:** validation record only. **Not canonical admission.** No BoatDesign,
NamedVariant or DesignOption is created, promoted or made searchable by this
document. It exists solely to demonstrate that `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md`
/ `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json` behave correctly against
technically different real designs, using facts already retained in this
repository (`research/benchmark/SEED_RESEARCH_NOTES.md`), per the slice's
"Real-design validation" requirement — no new research campaign was run to
produce this record.

Four designs are used (three required, one optional per the slice). They were
chosen because their retained evidence exercises materially different rule
areas: a legacy keel-hung rudder, a legacy spade rudder plus an ambiguous rig
identity, a legacy skeg-hung rudder plus a proprietary keel term, and a
directly-stated (non-legacy) twin-rudder fact. The underlying tests that
mechanically exercise these same facts against the registry are in
`tests/contract/test_marine_technical_entailment.py` (see the "Real-design
validation" section of that file).

## 1. Rustler 36 (SEED-09)

**Source:** `research/benchmark/SEED_RESEARCH_NOTES.md` SEED-09, citing Rustler
Yachts' own technical design article (`https://www.rustleryachts.com/keel-design-explained/`).

**Retained qualified facts used:**

- "Rustler explicitly describes the 36 as having a traditional long keel with cutaway forefoot."
- "Rudder is explicitly `keel-hung`." — this is the legacy v0.5 vocabulary word, i.e. `legacy.rudder_type = keel_hung`.
- "Keel is encapsulated: the GRP keel is moulded as part of the hull and contains lead ballast."

**Rules applied:**

| Rule | Result |
|---|---|
| `MTE-LEGACY-RUD-001` (`rudder_type=keel_hung`) | `appendages.rudder_support = keel` — **concrete derived fact**. |

**Intentionally underived / UNKNOWN:**

- `appendages.rudder_position` — **UNKNOWN**. "keel-hung" names support only; the source never states where the rudder sits (which, for a long keel, is typically well aft/underhull, but that is exactly the "typical, not definitional" reasoning this contract forbids).
- `appendages.rudder_balance` — **UNKNOWN**. No legacy `rudder_type` token ever entails balance (`MTE-LEGACY-RUD-*` uniformly leaves it `unknown`).
- `appendages.keel_type` — **left to direct classification, not entailment.** "Traditional long keel with cutaway forefoot" is a prose description, not one of the fifteen controlled `keel_type` tokens by itself; asserting a specific enum value (e.g. `full` vs `modified_full`) from this prose would require an interpretive judgment call this contract does not authorize. The `keel_subtype` free-text field is the correct home for the prose description; `keel_type` remains unqualified for this validation record.
- `configuration.hull_configuration` / `hull_count` — **not exercised.** The retained SEED-09 note does not state hull configuration explicitly enough to qualify a value for this record.

**Conflicts:** none — no contradictory qualified fact exists in the retained evidence for this design.

## 2. Westerly Centaur (SEED-06)

**Source:** `research/benchmark/SEED_RESEARCH_NOTES.md` SEED-06, citing the
Westerly Owners Association wiki and historical Laurent Giles designer press
text.

**Retained qualified facts used:**

- "Twin keel." (bilge/twin keel monohull cruiser.)
- Implicit monohull configuration (a "large-volume British twin-keeler", conventional single-hull cruiser — `configuration.hull_configuration = monohull`).
- "Historical designer press text describes a balanced skegless spade rudder." — this yields two separate facts that must **not** be conflated: (a) legacy `rudder_type = spade` (the word "spade" is the controlled taxonomy token), and (b) a *directly reported* "balanced" fact from the same prose, which is not itself an output of the `spade` entailment rule.
- "Sloop/ketch noted, with very few ketches."

**Rules applied:**

| Rule | Result |
|---|---|
| `MTE-HULL-001` (`hull_configuration=monohull`) | `configuration.hull_count = 1` — **concrete derived fact**. |
| `MTE-LEGACY-RUD-004` (`rudder_type=spade`) | `appendages.rudder_support = free` — **concrete derived fact**. |

**Intentionally underived / UNKNOWN, and the direct-vs-derived distinction:**

- `appendages.rudder_balance` — the source prose directly and separately states "balanced." This is recorded as a **directly reported fact** (`DIRECT_ONLY` provenance: reported outright by the designer press text), not as an output of `MTE-LEGACY-RUD-004` (which, per the preserved SLICE-0034 conservatism, never entails balance from any legacy `rudder_type` token, spade included). The two must carry different lineage: one is "entailed by rule MTE-LEGACY-RUD-004 from the word 'spade'", the other is "directly reported by the same source sentence, independent of the rudder_type token."
- `appendages.rudder_position` — **UNKNOWN**. Neither "spade" nor the prose states where the rudder is mounted relative to the hull.
- `rig.sailplan` / `rig.masthead_fractional` / `rig.mast_count` — **UNKNOWN, and deliberately not forced to a value.** "Sloop/ketch noted, with very few ketches" describes variation *across individual boats of this one design*, not a single qualified sailplan for the BoatDesign baseline. Because no `MTE-RIG-*` rule has a single, unambiguous qualified `sailplan` token to apply to, no mast-count entailment fires. This is the expected, correct outcome for a design whose retained evidence itself reports an ambiguous/mixed rig identity — see `MARINE_TECHNICAL_ENTAILMENT.v0.1.md` mandatory rule 4 (applicability before conflict) and rule 1 (definition/necessity only).

**Conflicts:** none surfaced for this record (the sloop/ketch variation is a same-model population-level fact, not a same-scope contradiction within one qualified BoatDesign record).

## 3. Island Packet 349 (SEED-16)

**Source:** `research/benchmark/SEED_RESEARCH_NOTES.md` SEED-16, citing Island
Packet's own model, specification and customization pages.

**Retained qualified facts used:**

- "Manufacturer calls keel `Full Foil Keel®`" — a proprietary branded term.
- "Current manufacturer customization material explicitly lists `Skeg hung rudder`." — the legacy `rudder_type = skeg_hung` word.
- "Hull/keel is one-piece hand-laminated fiberglass with encapsulated lead ballast."

**Rules applied:**

| Rule | Result |
|---|---|
| `MTE-LEGACY-RUD-002` (`rudder_type=skeg_hung`) | `appendages.rudder_support = skeg` — **concrete derived fact**. |

**Intentionally underived / UNKNOWN:**

- `appendages.keel_type` — **UNKNOWN, deliberately not entailed.** "Full Foil Keel®" is a proprietary marketing term with no safe one-to-one mapping onto any of the fifteen controlled `keel_type` enum values (per `MARINE_TECHNICAL_ENTAILMENT.v0.1.md` section 8, free-text fields never authorize a concrete entailment). It is recorded as `appendages.keel_subtype` free text only; `keel_type` itself stays unqualified.
- `appendages.rudder_position` / `rudder_balance` — **UNKNOWN**, same reasoning as the other two designs: `skeg_hung` names support only.
- `appendages.skeg_type` — **UNKNOWN as an exact value.** `MTE-RUD-002`/`MTE-RUD-003` would exclude `skeg_type=none` if `rudder_support=skeg` were already independently qualified from a non-legacy source, but that exclusion is not itself an assertion of `full` vs `partial`; no controlling evidence in SEED-16 distinguishes those two for this design.

**Conflicts:** none.

## 4. Pogo 1 (SEED-11) — optional fourth design

**Source:** `research/benchmark/SEED_RESEARCH_NOTES.md` SEED-11, citing Pogo
Structures' own manufacturer archive.

**Retained qualified facts used:**

- "Twin rudders explicitly stated."

**Rules applied:** none. This is the deliberate contrast case: the design's
own evidence directly states the v0.6-native fact (`appendages.rudder_count = 2`)
outright — it is not expressed via the legacy `rudder_type = twin` token, so
there is nothing for `MTE-LEGACY-RUD-006` to project, and no entailment is
needed because the target fact is already the qualified source fact itself.
`appendages.rudder_count` is classified `DIRECT_ONLY` in the registry precisely
for cases like this: a real, usable fact that authorizes no *further*
cross-field derivation (nothing here entails `rudder_position`, `rudder_support`
or `rudder_balance`, which all remain UNKNOWN for this design).

## Summary table

| Design | Concrete derived facts | Rule IDs applied | Deliberate UNKNOWNs | Conflicts |
|---|---|---|---|---|
| Rustler 36 | `rudder_support=keel` | `MTE-LEGACY-RUD-001` | position, balance, keel_type, hull config | none |
| Westerly Centaur | `hull_count=1`; `rudder_support=free` | `MTE-HULL-001`; `MTE-LEGACY-RUD-004` | position; sailplan/masthead_fractional/mast_count (ambiguous rig identity) | none |
| Island Packet 349 | `rudder_support=skeg` | `MTE-LEGACY-RUD-002` | keel_type (proprietary term), position, balance, exact skeg_type | none |
| Pogo 1 (optional) | none (direct fact, not derived) | none | position, support-provenance, balance | none |

No validation record above was, or is intended to be, promoted to a canonical
`BoatDesign`, `NamedVariant` or `DesignOption`. Oceanis 30.1 remains out of
scope for SLICE-0036 and is not referenced by this record.
