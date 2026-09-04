# HullQ Marketplace Fact Contract v0.1

**Status:** ACCEPTED
**Decision:** SLICE-0044, codifying `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md` for implementation
**Supersedes:** none (new contract)
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This specification is the normative Gate-1 marketplace fact/field contract required
before PhysicalBoat/listing-fact persistence, the broker listing workspace, listing
read/search, structured refit/history search or sensitive-claim presentation may be
implemented.

It answers exactly one question:

> What is the smallest Gate-1 marketplace fact/field contract that lets a
> professional broker describe a real yacht and current offer usefully, while
> preserving HullQ's Design-vs-PhysicalBoat truth boundary, provenance,
> UNKNOWN/CONFLICT semantics, non-destructive corrections and liability-safe
> treatment of sensitive claims?

This document defines representation and mechanical validation only. It does not
persist any PhysicalBoat/listing fact, and it does not implement a broker workspace,
search, media, document verification or LLM extraction.

Companion machine-readable artifacts:

- `specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json` — the structural contract every
  registry entry must satisfy.
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` — the bounded Gate-1 v0.1 registry
  instance.

## 2. Fundamental representation rule

```text
useful structured information
!=
automatic HullQ assertion of truth
```

```text
DESIGN / CONFIGURATION TRUTH
!=
PHYSICAL BOAT / LISTING TRUTH
```

Broker/seller claims about a PhysicalBoat are observations/evidence. They do not
silently become canonical facts merely because HullQ stores them in a structured
field or displays them in a table.

## 3. Independent meta-model axes

Every registered field/fact topic classifies the following axes independently. No
implementation may collapse two of these into one combined enum.

### 3.1 Subject

```text
PHYSICAL_BOAT
LISTING_OFFER
```

`DESIGN_REFERENCE` is a distinct reference/source scope used for assistance and
examples. No field in the v0.1 registry has subject `DESIGN_REFERENCE`; a
`DESIGN_REFERENCE` value MUST NOT be silently treated as a `PHYSICAL_BOAT` value
(§8.2).

### 3.2 Allowed assertion kinds

```text
VALUE_ASSERTION
PRESENT
ABSENT
NO_KNOWN_HISTORY_DECLARED
UNKNOWN
NOT_APPLICABLE
```

Each field declares the subset it accepts. Hard:

```text
ABSENT != NO_KNOWN_HISTORY_DECLARED != UNKNOWN
```

`ABSENT` is a current/bounded-state claim (for example: no auxiliary engine
fitted). `NO_KNOWN_HISTORY_DECLARED` means the claimant declares no relevant
history known to them; it is not proof the event never occurred. `UNKNOWN` means
no claim was made at all.

### 3.3 Resolution state

Separate from assertion kind, and tracked across observations for a fact topic
rather than declared statically per field:

```text
UNRESOLVED
RESOLVED
CONFLICT
```

### 3.4 Claim authority / provenance

The contract preserves who/what asserted an observation. Gate-1 native input is
professional-Organization/broker sourced, but the model does not assume all future
observations come from the current broker. Hard:

```text
BROKER_CLAIM != VERIFIED_FACT
```

### 3.5 Supporting-evidence state

Kept distinct, with no file upload in this slice:

```text
supporting documentation declared available
supporting documentation attached to HullQ
supporting documentation reviewed by HullQ
claim verified / not verified
```

### 3.6 Presentation

```text
PUBLIC
INTERNAL
```

### 3.7 Search use

```text
SEARCHABLE
DISPLAY_ONLY
```

Classifies intended future structured-search use; this slice does not implement
search.

### 3.8 Gate-1 requiredness

```text
REQUIRED_RESPONSE
CONDITIONAL
OPTIONAL
```

`REQUIRED_RESPONSE` means the broker/workflow must answer the field, but the
answer MAY be explicit `UNKNOWN` where the field's `allowed_assertion_kinds`
includes `UNKNOWN`. A guessed value MUST NOT be forced merely to achieve
completeness. `CONDITIONAL` carries a machine-readable
`requiredness.condition` (`depends_on_field`, `when_value`,
`required_when_true`).

Price lock:

```text
price_mode = AMOUNT -> amount + currency are required
price_mode = POA    -> amount is not invented
```

### 3.9 Delivery phase

```text
GATE_1_REQUIRED
GATE_1_OPTIONAL
LATER
```

### 3.10 Claim risk class

```text
STANDARD
MATERIAL
SENSITIVE
```

Delivery phase and risk class are mechanically independent axes. A field may
validly be `GATE_1_OPTIONAL + SENSITIVE` (§7 proves `vat_tax_status_claim`).

## 4. Deterministic claim-risk rule

### SENSITIVE

A field is `SENSITIVE` when its nature creates a heightened risk of being relied
on as legal, regulatory, title/ownership, tax, insurability, major-damage/history,
latent-defect/history, survey/condition, safety or warranty-like representation.

Strong triggers:

- HIN/CIN/registration/title/ownership identity used as legal identity evidence;
- VAT/tax-paid status;
- major accident/damage/grounding history;
- insurance-loss/claim history if later added;
- osmosis/major latent-defect history;
- current-condition statements that could be mistaken for a survey/
  certification/seaworthiness assurance;
- other statements where false/outdated presentation could materially affect
  legality, insurability, safety/seaworthiness or substantial transaction
  economics and therefore require special wording/evidence handling.

### MATERIAL

Commercially/technically important values such as price, build year, draft,
engine hours and refit claims that materially affect value/suitability but do
not by ordinary display imply HullQ legal/survey certification.

### STANDARD

Ordinary narrative/display metadata without the heightened implications above.

### Conservative v0.1 sensitive-field rule

Every `SENSITIVE` field in registry v0.1 is `DISPLAY_ONLY`. Every `SENSITIVE`
field carries a machine-readable `presentation_policy`
(`forbids_unqualified_assertion`, `requires_attribution`,
`requires_last_confirmed_disclosure`, `requires_verification_status_disclosure`,
`verification_status_default = NONE`, `template_hint`), regardless of whether its
`presentation` is `PUBLIC` or `INTERNAL`. Sensitive filtering/search requires a
later explicit contract amendment and product/legal review.

## 5. Hard future-search semantics

This slice does not implement listing search, but it locks future eligibility:

```text
RESOLVED compatible value -> may satisfy Required
UNKNOWN                    -> NO
UNRESOLVED                 -> NO
CONFLICT                   -> NO
```

A conflicting observation that happens to match the buyer query MUST NOT be
selected to manufacture a match. For `Prefer`, unresolved/conflicting
observations MUST NOT receive an invented positive score merely because one
candidate value matches. `NO_KNOWN_HISTORY_DECLARED` MUST NOT satisfy a
predicate equivalent to "proven never occurred".

## 6. Correction / supersession

### 6.1 Same-authority correction

A genuine correction is non-destructive:

```text
new observation
+ explicit supersedes_observation_id (or accepted equivalent)
+ same authorized claim authority/context
-> old observation retained for audit/history
-> new observation becomes that claimant's current statement
```

This aligns with the existing `supersedes_evidence_id` pattern in
`specs/FIELD_EVIDENCE_SCHEMA.v0.3.json`, but marketplace observation identity is
its own type — this contract does not reuse research-evidence identity for
marketplace observations.

### 6.2 Cross-source disagreement

A different Organization/source cannot supersede another merely by being newer:

```text
Org A: 2021
Org B: 2022
-> CONFLICT unless separately resolved
```

### 6.3 Same-source contradiction without explicit correction

No silent "latest wins". A contradictory later observation that is not
explicitly authorized as correction remains conflict/unresolved.

## 7. Relationship to `CLAIM_SEMANTICS_SCHEMA.v0.1`

`specs/CLAIM_SEMANTICS_SCHEMA.v0.1.json` remains the semantic role of an
observation (e.g. `individual_hull_value`, `identity_or_chronology_claim`). This
contract does not overload that enum with marketplace assertion state,
resolution, provenance, requiredness, delivery phase or risk class. The
marketplace assertion-kind/resolution-state/risk-class concepts defined here are
separate, purpose-built enums (§3.2, §3.3, §3.10), not a repurposing of
`ClaimSemantics`.

## 8. Free-text rules

Registry v0.1 includes `listing_offer.broker_summary`,
`listing_offer.broker_description` and `listing_offer.known_history_narrative`.

- Narrative remains broker text.
- Narrative is `DISPLAY_ONLY` for structured truth/search.
- Text alone cannot satisfy technical Required filters.
- Structured facts may separately capture important claims mentioned in
  narrative.
- No parser/LLM may auto-promote description text into resolved/verified
  PhysicalBoat truth.

Future extraction flow, not implemented here:

```text
text -> candidate extraction -> uncertainty -> human confirm/edit/ignore
```

Hard:

```text
EXTRACTION CONFIDENCE != TRUTH CONFIDENCE
```

Example: "Rigging was done by the previous owner a few years ago" MUST NOT
become an exact 2022 replacement claim automatically.

## 9. Minimal refit / upgrade structure

One repeatable `PHYSICAL_BOAT` claim structure, `refit_event_v0_1`
(`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` → `event_structures`), backs the
`physical_boat.refit_events` field. Gate-1 optional, display-only.

```text
event_kind:  MAINTENANCE | UPGRADE_OR_REPLACEMENT | MAJOR_REFIT
category:    bounded Gate-1 category vocabulary (RIGGING, SAILS,
             ENGINE_PROPULSION, ELECTRICAL_ENERGY, NAVIGATION, HULL, DECK,
             PLUMBING, HVAC_COMFORT, INTERIOR, SAFETY, OTHER)
topic:       non-empty text or bounded identifier
action:      INSTALLED | REPLACED | REFURBISHED | UPGRADED | REPAIRED | OTHER
timing:      precision + the actual temporal payload for that precision
             (see below)
description: optional short text
supporting_documentation_declared_available: YES | NO | UNKNOWN
```

`category` is a closed Gate-1 vocabulary, not free text; an out-of-vocabulary
category is invalid.

`timing` is a structured value, not a bare precision token, so it can
mechanically carry the actual year/date or approximate period the readiness
requires — a bare `EXACT` with no year/date is not a usable claim:

```text
precision:           EXACT | APPROXIMATE | UNKNOWN
exact_year:          integer | null
exact_date:          valid ISO 8601 calendar date | null
approximate_period:  non-empty, non-whitespace-only short text | null
```

Hard, per precision:

```text
precision = EXACT       -> exactly one of exact_year/exact_date is non-null
                            (never neither, never both)
                            AND if exact_date is given it MUST parse as a
                            real ISO 8601 calendar date, not merely any
                            string
                            AND approximate_period is null
precision = APPROXIMATE -> approximate_period is non-null and non-empty
                            after stripping whitespace (whitespace-only is
                            invalid)
                            AND exact_year and exact_date are both null
precision = UNKNOWN     -> exact_year, exact_date and approximate_period are
                            all null (no fabricated precision)
```

`exact_year` and `exact_date` are alternative ways to state the same single
exact point in time, not independent facts that may both be populated;
supplying both is invalid even though each alone would be valid.

Claim authority/provenance belongs to the observation envelope/context, not
uncontrolled text inside the event. No invoice/PDF upload follows from
`supporting_documentation_declared_available`.

## 10. v0.1 bounded field registry

`specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` contains exactly 38 field entries:

- 9 `LISTING_OFFER` fields (§10.1);
- 6 `PHYSICAL_BOAT` identity/basic-claim fields (§10.2);
- 16 `PHYSICAL_BOAT` technical-core fields (§10.3);
- 7 `PHYSICAL_BOAT` history/refit fields, of which 4 are explicitly deferred
  `LATER` sensitive-history exemplars (§10.4).

No complete yacht/equipment catalog is represented. Field identifiers use a
`physical_boat.*` / `listing_offer.*` namespace; the exact identifier strings are
implementation identifiers, the classified semantics are the locked contract.

### 10.1 Listing offer

| Field | Phase | Risk | Presentation | Search | Requiredness |
|---|---|---|---|---|---|
| `listing_offer.asking_price_mode` | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| `listing_offer.asking_price_amount` | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | CONDITIONAL on `price_mode=AMOUNT` |
| `listing_offer.currency` | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | CONDITIONAL on `price_mode=AMOUNT` |
| `listing_offer.location_country` | GATE_1_REQUIRED | STANDARD | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| `listing_offer.location_region` | GATE_1_OPTIONAL | STANDARD | PUBLIC | SEARCHABLE | OPTIONAL |
| `listing_offer.broker_summary` | GATE_1_OPTIONAL | STANDARD | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| `listing_offer.broker_description` | GATE_1_REQUIRED | STANDARD | PUBLIC | DISPLAY_ONLY | REQUIRED_RESPONSE |
| `listing_offer.known_history_narrative` | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| `listing_offer.vat_tax_status_claim` | GATE_1_OPTIONAL | SENSITIVE | PUBLIC | DISPLAY_ONLY | OPTIONAL |

`POA` MUST NOT create a synthetic asking-price amount.

### 10.2 PhysicalBoat identity/basic claims

| Field | Phase | Risk | Presentation | Search | Requiredness |
|---|---|---|---|---|---|
| `physical_boat.marketed_brand_claim` | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| `physical_boat.builder_claim` | GATE_1_OPTIONAL | MATERIAL | PUBLIC | SEARCHABLE | OPTIONAL |
| `physical_boat.model_designation_claim` | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| `physical_boat.boat_name` | GATE_1_OPTIONAL | STANDARD | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| `physical_boat.build_year` | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE; UNKNOWN allowed |
| `physical_boat.hin_cin_claim` | GATE_1_OPTIONAL | SENSITIVE | INTERNAL | DISPLAY_ONLY | OPTIONAL |

Hard:

```text
Brand != Builder
raw broker brand/model claim != resolved BoatDesignRef
HIN/CIN claim != proof of title/ownership
```

A BoatDesign match may assist identity but does not erase the raw claim or
project design specs into this yacht.

### 10.3 PhysicalBoat technical core

All are `PHYSICAL_BOAT` and `MATERIAL`, `GATE_1_OPTIONAL`, `PUBLIC`,
`SEARCHABLE`, `OPTIONAL; UNKNOWN allowed`:

`loa_length`, `beam`, `draft`, `displacement`, `hull_material`,
`keel_configuration`, `rudder_configuration`, `rig_configuration`,
`engine_make`, `engine_model`, `engine_power`, `engine_hours`, `fuel_type`,
`cabins`, `berths`, `heads`.

Every numeric field declares a normalized `value_type` (`data_type`, `unit`,
`unit_system`); no ambiguous unit-bearing strings are canonical searchable
values. Missing PhysicalBoat values remain `UNKNOWN`; no rule equivalent to
"fall back to BoatDesign value" is allowed. `engine_*`/`fuel_type` additionally
allow `ABSENT` to represent a current claim of no auxiliary engine fitted.

### 10.4 PhysicalBoat history/refit

| Field | Phase | Risk | Presentation | Search | Requiredness |
|---|---|---|---|---|---|
| `physical_boat.refit_events` | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| `physical_boat.known_previous_owner_count` | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL; UNKNOWN allowed |
| `physical_boat.broad_use_history` | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL; UNKNOWN allowed; MULTI-value |
| `physical_boat.grounding_history` | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| `physical_boat.major_damage_history` | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| `physical_boat.osmosis_treatment_history` | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| `physical_boat.last_survey_date_claim` | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |

`known_previous_owner_count` MUST NOT contain names/identifiers of prior private
owners, is not searchable in v0.1 and is not a yacht-quality score.

`broad_use_history` values are drawn from `PRIVATE`, `CHARTER`,
`SAILING_SCHOOL`, `RACING`, `LIVEABOARD`, `COMMERCIAL`. A single yacht's
lifetime use is not mutually exclusive across these categories (for example a
yacht legitimately used for both `CHARTER` and `PRIVATE` use), so this field
has `cardinality: MULTI` in `value_type`: a `VALUE_ASSERTION` observation
carries a bounded, duplicate-free, non-empty subset of the closed vocabulary,
not a single scalar token. Hard:

```text
assertion_kind = UNKNOWN          -> no values payload at all
assertion_kind = VALUE_ASSERTION  -> non-empty subset of the closed
                                      vocabulary, no duplicate members
```

`UNKNOWN` (nothing declared) remains semantically distinct from any declared
non-empty set; there is no "empty declared set" representation, so an asserted
value with zero members is invalid, not a synonym for `UNKNOWN`.

`broad_use_history` categories are lifetime, non-exclusive, **open-world
positive** facts, not a single closed-world value under the generic §6
same-topic resolution model. A source declaring `{PRIVATE}` states only what
that source positively knows; it does not implicitly claim `CHARTER`,
`RACING` or any other category never occurred. Consequently:

```text
Org A: {PRIVATE}
Org B: {PRIVATE, CHARTER}
-> NOT CONFLICT (Org B simply knows more than Org A declared)

Org A: {PRIVATE}
Org B: {CHARTER}
-> NOT CONFLICT merely because the declared sets differ

Org A: {PRIVATE, CHARTER}
Org B: {CHARTER, PRIVATE}
-> the same claim (member order is not significant)
```

Resolution for this field is additive, not equality-based, and additive both
**across** sources and **within** one source. Two still-active observations
from the same claim authority that declare different categories, with no
explicit `supersedes_observation_id` link between them, are **not** a
contradiction: both are simultaneously-true positive facts, so they union
into that authority's current set rather than being discarded as ambiguous.
Only an explicit same-authority supersession retracts/replaces a prior
observation exactly as §6.1 requires — a superseded observation is excluded
from the union (a real correction, not an automatic merge with what it
replaced):

```text
Org A #1: {PRIVATE}
Org A #2: {CHARTER}        (no supersession link)
-> Org A current set = {PRIVATE, CHARTER}     (both true, unioned)

Org A #1: {PRIVATE}
Org A #2: {CHARTER}        (#2 explicitly supersedes #1)
-> Org A current set = {CHARTER}              (a real retraction, not a union)
```

Each authority's own current set (after applying its own supersession) is
independently retained, and a convenience aggregate may union the current
positive sets across authorities for display. That union — at both the
per-authority and cross-authority level — is presentation/resolution
convenience only. It does **not** upgrade provenance or verification
strength beyond what each source individually asserted, and it never implies
"this is the complete list of all uses"; a category absent from the
aggregate is simply not positively known by any current source, not proven
absent. `UNKNOWN` from one source (or one observation) contributes no
category but never erases another already-active positive observation, from
the same authority or a different one. Cross-authority supersession remains
structurally impossible: a different Organization's observation can never
retract another Organization's active claim, no matter what
`supersedes_observation_id` it declares.

This field never produces a `CONFLICT` in v0.1, cross-source or
same-authority: there is no negative/exclusion signal in the Gate-1
vocabulary (no way to declare "used only for X, never Y"), so two positive
declarations are never competing claims about the same value — they simply
union.

History-sensitive topics allow `UNKNOWN` and, where logically appropriate,
`NO_KNOWN_HISTORY_DECLARED`; silence cannot become proven absence.

## 11. Sensitive presentation lock

Every v0.1 `SENSITIVE` field carries a `presentation_policy` that forbids
unqualified authoritative wording when HullQ has only a broker claim.

Forbidden examples under an unverified broker claim:

```text
VAT: PAID
Grounding: NO
Damage history: NONE
HIN/CIN: VERIFIED
```

The contract preserves enough context for later UI wording equivalent to:

```text
broker-declared <value>
last confirmed <timestamp>
HullQ verification: none
```

or:

```text
No known grounding history declared by broker
HullQ verification: none
```

Exact legal copy remains later product/legal review.

## 12. Registry integrity rules

Machine validation fails if any of the following occur (enforced by
`specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json` and/or
`tests/contract/test_marketplace_fact_contract.py`):

1. a field lacks a subject;
2. a field lacks allowed assertion kinds;
3. `ABSENT`, `NO_KNOWN_HISTORY_DECLARED` and `UNKNOWN` collapse;
4. delivery phase and risk class share one combined enum;
5. `CONDITIONAL` requiredness lacks a machine-readable condition;
6. any `SENSITIVE` field is `SEARCHABLE` in v0.1;
7. a `SENSITIVE` field lacks an attributed/non-verified `presentation_policy`;
8. free-text narrative is treated as structured-search truth;
9. `known_previous_owner_count` is searchable in v0.1;
10. declared documentation availability implies attachment/review/verification;
11. a Design reference fills a missing PhysicalBoat value;
12. a numeric searchable technical field lacks normalized type/unit semantics;
13. a required-response field forces a guessed value where UNKNOWN is
    legitimate;
14. `price_mode=AMOUNT` passes without amount + currency;
15. `price_mode=POA` invents an amount;
16. Brand and Builder collapse;
17. a different source supersedes another source by recency alone;
18. a refit event's `timing.precision` does not match its own temporal
    payload (`EXACT` without exactly one of `exact_year`/`exact_date`, or
    with both, or with a malformed/impossible `exact_date`; `APPROXIMATE`
    without a non-empty, non-whitespace-only `approximate_period`; `UNKNOWN`
    with any fabricated `exact_year`/`exact_date`/`approximate_period`);
19. a refit event's `category` is outside the closed Gate-1 vocabulary;
20. `broad_use_history` is treated as single-valued, allows a duplicate
    member, allows an empty declared set distinct from `UNKNOWN`, treats
    differing (including non-overlapping) positive sets as a `CONFLICT`
    (cross-source or same-authority), discards a same-authority
    non-superseded observation as "ambiguous" instead of unioning it, lets
    `UNKNOWN` erase an already-active positive observation, or lets an
    explicit same-authority supersession automatically union with the
    observation it retracts instead of replacing it.

## 13. Required adversarial examples

`tests/contract/test_marketplace_fact_contract.py` and
`scripts/inspect_marketplace_field_contract.py` mechanically prove, using
TEST-ONLY reference evaluators over the registry data (no production runtime is
introduced by this contract):

- `UNKNOWN` vs `ABSENT` vs `NO_KNOWN_HISTORY_DECLARED` remain distinct
  (autopilot-style equipment absence vs grounding history declaration);
- a BoatDesign reference value never auto-projects into a missing PhysicalBoat
  value;
- conflicting cross-source refit claims resolve to `CONFLICT`, and `CONFLICT`
  never satisfies hard search;
- a same-authority explicit supersession retains the prior observation for
  audit/history and becomes the claimant's current statement, without a
  different Organization being able to use supersession to erase another
  Organization's claim;
- `supporting_documentation_declared_available = YES` never implies attached,
  reviewed or verified;
- `vat_tax_status_claim` proves `GATE_1_OPTIONAL + SENSITIVE` coexist, with no
  `SENSITIVE_LATER` shortcut;
- conditional price requiredness: `AMOUNT` + missing amount/currency is
  invalid; `AMOUNT` + amount + currency is valid; `POA` + no amount is valid;
  `POA` + a synthetic/invented amount is invalid;
- free-text extraction of "Rigging was done by the previous owner a few years
  ago" does not become an exact-year structured claim;
- refit `timing` validity: `EXACT` with neither `exact_year` nor
  `exact_date` is invalid; `EXACT` with a valid year only is valid; `EXACT`
  with a valid date only is valid; `EXACT` with both is invalid; `EXACT`
  with a malformed/impossible date (e.g. `2022-13-40`) is invalid;
  `APPROXIMATE` with a whitespace-only period is invalid; `APPROXIMATE`
  with a real period is valid; `UNKNOWN` with any timing payload at all is
  invalid; `UNKNOWN` with no payload is valid;
- an out-of-vocabulary refit `category` (e.g. a token outside the closed
  Gate-1 list) is rejected;
- `broad_use_history` accepts a legitimate multi-category declaration (e.g.
  `{CHARTER, PRIVATE}` or `{RACING, PRIVATE}`); rejects a duplicate member,
  an empty declared set, and an out-of-vocabulary member; Org A `{PRIVATE}`
  vs. Org B `{PRIVATE, CHARTER}` is NOT a conflict; Org A `{PRIVATE}` vs.
  Org B `{CHARTER}` is NOT a conflict merely because the sets differ; the
  same categories in different member order are the same claim; two
  still-active same-authority observations with no supersession link (e.g.
  Org A #1 `{PRIVATE}`, Org A #2 `{CHARTER}`) union to that authority's
  current set rather than being discarded as ambiguous; an `UNKNOWN`
  observation does not erase an already-active positive observation, from
  the same authority or a different one; a same-authority explicit
  supersession (e.g. `{CHARTER}` supersedes `{PRIVATE}`) is a real
  retraction that replaces the superseded set rather than automatically
  unioning with it; and a cross-source supersession attempt still cannot
  erase another authority's active positive claim.

## 14. Non-goals

This contract does not itself implement or authorize: PostgreSQL/Alembic
changes; PhysicalBoat/listing-fact persistence; SLICE-0040 identity or
SLICE-0043 persistence semantics changes; PhysicalBoat/MarketEpisode dedup/
resolution; broker workspace UI; FastAPI/Astro/React surfaces; publication/
lifecycle/freshness; photo/media/document upload; malware scanning
implementation; document verification/adjudication; LLM extraction
implementation; automatic free-text-to-fact promotion; a complete yacht/
equipment catalog; generic CRM/leads/referrals/pricing/transactions; NautiX/
CSV/feed implementation; legal/tax certification by HullQ; or SLICE-0045+.
