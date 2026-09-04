# SLICE-0044 — Marketplace Fact Contract & Gate-1 Field Registry

**ID:** SLICE-0044  
**Type:** DESIGN_RESEARCH  
**Status:** READY  
**Stage:** Native Marketplace Foundation — PhysicalBoat / Listing fact semantics before persistence/workspace  
**Depends on:** SLICE-0040 owner-accepted / DONE; SLICE-0041 owner-accepted / DONE; SLICE-0042 owner-accepted / DONE; SLICE-0043 owner-accepted / DONE; `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md` accepted/merged  
**Blocks:** PhysicalBoat/listing-fact persistence, broker listing workspace, listing read/search surfaces, structured refit/history search, sensitive-claim presentation, scalable listing intake

## Objective

Answer exactly one business-critical design question and freeze it in machine-checkable form:

> **What is the smallest Gate-1 marketplace fact/field contract that lets a professional broker describe a real yacht and current offer usefully, while preserving HullQ's strict Design-vs-PhysicalBoat truth boundary, provenance, UNKNOWN/CONFLICT semantics, non-destructive corrections and liability-safe treatment of sensitive claims?**

The slice MUST produce a normative marketplace fact contract plus a machine-readable field registry and executable owner inspection. It MUST NOT persist PhysicalBoat facts or build the broker workspace.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
This slice defines one capability boundary only: the machine-checkable semantic/field contract future native listing input must obey.

**VISIBLE-RESULT CHECK:** PASS  
The Project Owner can execute one inspection command and see the exact Gate-1 field matrix plus adversarial semantic checks for Design-vs-PhysicalBoat projection, UNKNOWN/ABSENT/no-known-history distinction, CONFLICT search behavior, sensitive-field classification, document-availability semantics and correction/supersession behavior.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
The accepted native-marketplace execution order requires physical-vessel/listing truth after durable NativeListing creation and before broad listing read/search/workspace implementation. Freezing the field semantics first avoids coupling a new DB schema/UI to an unresolved truth/liability model and remains bounded under ONE-CAPABILITY.

## Why this slice exists

SLICE-0043 proved one authorized, durable minimal NativeListing envelope. The next architectural pressure is to attach useful real-yacht and offer information.

Competitor research across major boat/yacht marketplaces and broker inventory tools showed that market-standard listing systems commonly provide extensive structured technical fields, free-text descriptions, model-data autofill, quality/completeness scoring, broker profiles and distribution tooling. HullQ should retain broker usability while improving the truth boundary:

```text
free text for narrative
+
structured observations for searchable/inspectable facts
+
explicit provenance / claim authority
+
UNKNOWN / UNRESOLVED / CONFLICT where appropriate
+
Design reference used as assistance, never silently as this-yacht truth
```

Additional owner/architecture review identified four important risks that must be solved before persistence/UI:

1. current-state `ABSENT` is not the same as historical `NO_KNOWN_HISTORY_DECLARED`;
2. release sequencing (`GATE_1_REQUIRED/OPTIONAL/LATER`) must be independent of legal/safety claim risk (`STANDARD/MATERIAL/SENSITIVE`);
3. conflicting observations must fail closed for hard search/qualification just as existing HullQ Search does;
4. a claimant correcting its own mistake needs explicit non-destructive supersession, while a different source cannot overwrite prior observations.

The accepted `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md` is now controlling and this slice must operationalize it.

## Controlling artifacts

- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`
- `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md`
- `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`
- `specs/CLAIM_SEMANTICS_SCHEMA.v0.1.json`
- `specs/FIELD_EVIDENCE_SCHEMA.v0.3.json`
- `specs/OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json`
- `specs/NATIVE_LISTING_PERSISTENCE_CONTRACT.v0.1.md`
- `docs/slices/SLICE-0043-acceptance-closure.md`
- `docs/slices/SLICE_TEMPLATE.md`

### Existing-schema alignment

`FIELD_EVIDENCE_SCHEMA.v0.3` already contains the accepted non-destructive `supersedes_evidence_id` pattern and explicitly separates producer/evidence/claim semantics. `OBSERVATION_APPLICABILITY_SCHEMA.v0.1` already treats unknown scope as unknown rather than global applicability.

SLICE-0044 MUST align with these principles but MUST NOT repurpose research-evidence schemas as a marketplace persistence model merely for convenience.

`CLAIM_SEMANTICS_SCHEMA.v0.1` remains the semantic role of an observation (for example `individual_hull_value` or `identity_or_chronology_claim`). It MUST NOT be overloaded with marketplace assertion state, resolution, provenance, delivery phase or risk classification.

## In scope

1. A normative `MARKETPLACE_FACT_CONTRACT.v0.1` defining the field/claim meta-model.
2. A machine-readable v0.1 marketplace field registry with a deliberately bounded Gate-1 core plus a few explicitly deferred sensitive/history exemplars needed to prove the risk/phase model.
3. Machine-checkable validation of every registry entry.
4. Explicit semantic distinction among observation assertion kind, cross-observation resolution state, provenance/claim authority, evidence availability, search use, delivery phase and claim-risk class.
5. Free-text description/narrative fields that remain separate from structured facts.
6. A minimal repeatable refit/upgrade observation shape suitable for Gate-1 broker entry without document upload.
7. Explicit same-authority correction/supersession semantics and cross-source conflict semantics at contract/example level.
8. An owner inspection command showing the final field matrix and required fail-closed examples.

## Explicitly out of scope

- PostgreSQL tables/migrations for PhysicalBoat facts, observations or field values;
- changing the SLICE-0040 identity model;
- modifying SLICE-0043 NativeListing persistence semantics;
- automatic PhysicalBoat/MarketEpisode identity resolution or dedup;
- actual broker listing editor/workspace UI;
- FastAPI/Astro/React endpoints/surfaces;
- public listing publication/lifecycle/freshness;
- document/PDF upload or storage;
- malware scanner implementation;
- document verification/adjudication;
- photo/media upload;
- LLM extraction implementation;
- automated free-text-to-fact promotion;
- full yacht/equipment field catalog;
- generic CRM;
- leads/referrals;
- pricing/entitlements;
- external NautiX/CSV/feed import implementation;
- legal/tax certification by HullQ;
- SLICE-0045 or later work.

## Required meta-model dimensions

Every registered field/fact topic MUST define independent values for at least the following dimensions. Do not collapse them into one status enum.

### 1. Subject / ownership

Minimum semantic classes:

```text
PHYSICAL_BOAT
LISTING_OFFER
```

`DESIGN_REFERENCE` must remain representable in examples/validation as a separate source/reference scope, but a design reference is not silently a PhysicalBoat field value.

Examples:

```text
standard design draft     -> DESIGN_REFERENCE
this yacht's actual draft -> PHYSICAL_BOAT
asking price              -> LISTING_OFFER
```

### 2. Allowed observation assertion kinds

The final v0.1 names may vary only if semantics remain mechanically distinct:

```text
VALUE_ASSERTION
PRESENT
ABSENT
NO_KNOWN_HISTORY_DECLARED
UNKNOWN
NOT_APPLICABLE
```

Each field declares an allowed subset.

Hard distinction:

```text
ABSENT
!=
NO_KNOWN_HISTORY_DECLARED
!=
UNKNOWN
```

`ABSENT` is appropriate to a current/bounded state such as equipment absence.

`NO_KNOWN_HISTORY_DECLARED` is appropriate where a claimant can only state that no relevant history is known to them. It MUST NOT be interpreted as proof an event never occurred.

### 3. Resolution state

Keep cross-observation resolution separate from assertion kind.

Minimum semantics:

```text
UNRESOLVED
RESOLVED
CONFLICT
```

### 4. Claim authority / provenance

The contract must preserve enough context to answer who/what asserted an observation. Gate-1 native input is professional-Organization/broker sourced, but the model must not hard-code that every future observation comes from the current broker.

Do not define `BROKER_CLAIM` as equivalent to `VERIFIED_FACT`.

### 5. Supporting evidence state

At minimum keep these concepts separate:

```text
supporting documentation declared available
supporting documentation attached to HullQ
supporting documentation reviewed by HullQ
claim verified / not verified
```

SLICE-0044 MUST NOT introduce an upload path.

A Gate-1 broker declaration may state documentation is available without HullQ possessing it.

### 6. Presentation

Minimum registry classification:

```text
PUBLIC
INTERNAL
```

### 7. Search use

Minimum registry classification:

```text
SEARCHABLE
DISPLAY_ONLY
```

`SEARCHABLE` means the field is intended to be usable by a future structured search capability. It does NOT implement that search in this slice.

### 8. Gate-1 requiredness

Minimum classification:

```text
REQUIRED_RESPONSE
OPTIONAL
```

`REQUIRED_RESPONSE` does not mean the value must be known. A required response may explicitly be `UNKNOWN` where the field allows it.

This avoids fake completeness by forcing guessed values.

### 9. Delivery phase

```text
GATE_1_REQUIRED
GATE_1_OPTIONAL
LATER
```

This axis answers **when** HullQ needs the field/capability.

### 10. Claim risk class

```text
STANDARD
MATERIAL
SENSITIVE
```

This axis answers **how carefully the claim must be represented**, independently of delivery phase.

A field may therefore validly be:

```text
GATE_1_OPTIONAL + SENSITIVE
```

or, where later explicitly justified:

```text
GATE_1_REQUIRED + SENSITIVE
```

## Deterministic claim-risk classification rule

The normative contract MUST include a reproducible checklist/rule rather than intuitive labels.

### SENSITIVE

Classify as `SENSITIVE` when the field's nature creates heightened risk of being relied upon as a legal, regulatory, title/ownership, tax, insurability, major-damage/history, latent-defect/history, safety-condition or warranty-like representation.

Strong triggers include:

- HIN/CIN/registration/title/ownership identity where used as legal identity evidence;
- VAT/tax-paid or equivalent tax status;
- major accident/damage/grounding history;
- insurance-loss/claim history if later introduced;
- major latent-defect/history claims such as osmosis treatment/history;
- current-condition statements that could reasonably be mistaken for a survey/certification or seaworthiness assurance;
- other claims for which false/outdated presentation could materially affect legality, insurability, safety/seaworthiness or substantial transaction economics and therefore needs special wording/evidence handling.

### MATERIAL

Use for commercially/technically important facts that can materially affect suitability/value/search decisions but do not normally imply HullQ legal/survey certification merely by being displayed, e.g. build year, draft, engine hours, key refit claims, price.

### STANDARD

Use for ordinary narrative/display metadata where inaccurate content is undesirable but does not carry the above heightened legal/history/condition implications.

### Conservative v0.1 presentation rule

Every `SENSITIVE` field in registry v0.1 MUST be `DISPLAY_ONLY` and MUST carry a field-level presentation policy requiring visible claim attribution / non-verification context. Search/filtering of sensitive claims requires a later explicit contract amendment/product/legal review.

This is intentionally conservative and may be relaxed field-by-field only by later accepted governance.

## Hard search semantics

Although SLICE-0044 does not implement listing search, the contract MUST lock future search eligibility:

```text
RESOLVED compatible value -> eligible to satisfy a future Required constraint
UNKNOWN                    -> NOT eligible
UNRESOLVED                 -> NOT eligible
CONFLICT                   -> NOT eligible
```

`CONFLICT` MUST NOT resolve by selecting the observation that happens to satisfy the buyer query.

For `Prefer`, unresolved/conflicting observations MUST NOT receive an invented positive score solely because one candidate value would match.

For history fields, `NO_KNOWN_HISTORY_DECLARED` MUST NOT satisfy a semantic predicate equivalent to "proven never occurred".

## Correction / supersession semantics

### Same-authority correction

A genuine correction of a claimant's own prior statement is represented non-destructively:

```text
new observation
+ explicit supersedes_observation_id (or accepted equivalent)
+ same authorized claim authority/context
-> old observation retained for audit/history
-> new observation becomes claimant's current statement
```

The exact field name may align with existing `supersedes_evidence_id` precedent but MUST NOT reuse an evidence ID type where marketplace observation identity requires a distinct type.

### Cross-source disagreement

```text
Broker/Org A observation
!=
Broker/Org B observation
```

Broker/Org B cannot supersede A merely by being newer.

Contradictory active observations without an accepted resolution remain `CONFLICT`.

### Unmarked contradiction from same authority

A later contradictory observation that is not explicitly identified/authorized as a correction MUST NOT silently become "latest wins". It remains conflict/unresolved until the contract's correction/resolution rules are satisfied.

## Free-text rules

Gate-1 MUST retain broker narrative capability.

Registry v0.1 must include:

```text
broker_summary
broker_description
known_history_narrative
```

Rules:

- narrative text is preserved as submitted subject to ordinary validation/safety rules;
- free text is `DISPLAY_ONLY` for structured-truth purposes;
- free text alone MUST NOT satisfy structured technical Required filters;
- important technical/commercial/history facts may also be captured as separate structured observations;
- no LLM/manual parser may auto-promote description text to verified/resolved fact in this slice.

Future extraction may produce suggestions only:

```text
source text
-> candidate extraction
-> extraction uncertainty
-> human confirm/edit/ignore
```

Hard:

```text
EXTRACTION CONFIDENCE != TRUTH CONFIDENCE
```

No LLM extraction implementation belongs in SLICE-0044.

## Minimal refit / upgrade structure

Registry/contract v0.1 MUST include one repeatable `refit_events`-equivalent PhysicalBoat claim structure, Gate-1 optional and initially display-only.

Minimum event semantics:

```text
event_kind:
  MAINTENANCE | UPGRADE_OR_REPLACEMENT | MAJOR_REFIT

category:
  bounded high-level category, not an exhaustive equipment ontology

topic/item:
  non-empty text or bounded identifier

action:
  INSTALLED | REPLACED | REFURBISHED | UPGRADED | REPAIRED | OTHER

timing:
  exact year/date OR approximate timing OR UNKNOWN

description:
  optional short text

supporting_documentation_declared_available:
  YES | NO | UNKNOWN
```

Claim authority/provenance belongs to the observation envelope/context, not duplicated as uncontrolled free text inside each event.

The event is about a `PHYSICAL_BOAT`. A new broker may add another observation; it does not overwrite earlier observations merely because it is newer.

No invoice/PDF upload is allowed by this structure.

## v0.1 field registry — locked bounded set

The implementation may choose clean machine field identifiers, but the semantic topics below are locked. Do not expand into a complete yacht catalog.

### A. Listing-offer core

| Topic | Subject | Phase | Risk | Presentation | Search | Gate-1 response |
|---|---|---|---|---|---|---|
| asking price mode (`AMOUNT` / `POA`) | LISTING_OFFER | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| asking price amount | LISTING_OFFER | GATE_1_REQUIRED conditional on AMOUNT | MATERIAL | PUBLIC | SEARCHABLE | conditional |
| currency | LISTING_OFFER | GATE_1_REQUIRED conditional on AMOUNT | MATERIAL | PUBLIC | SEARCHABLE | conditional |
| current location country | LISTING_OFFER | GATE_1_REQUIRED | STANDARD | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| current location text / region | LISTING_OFFER | GATE_1_OPTIONAL | STANDARD | PUBLIC | SEARCHABLE | OPTIONAL |
| broker summary | LISTING_OFFER | GATE_1_OPTIONAL | STANDARD | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| broker description | LISTING_OFFER | GATE_1_REQUIRED | STANDARD | PUBLIC | DISPLAY_ONLY | REQUIRED_RESPONSE |
| known-history narrative | LISTING_OFFER | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| VAT/tax status claim | LISTING_OFFER | GATE_1_OPTIONAL | SENSITIVE | PUBLIC | DISPLAY_ONLY | OPTIONAL |

Price conditionality MUST enforce:

```text
AMOUNT -> amount + currency required
POA    -> amount must not be invented merely to make search easier
```

A future normalized price-search representation is a later capability.

### B. PhysicalBoat identity / basic claims

| Topic | Phase | Risk | Presentation | Search | Gate-1 response |
|---|---|---|---|---|---|
| marketed brand claim | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| builder claim | GATE_1_OPTIONAL | MATERIAL | PUBLIC | SEARCHABLE | OPTIONAL |
| model/designation claim | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| boat name | GATE_1_OPTIONAL | STANDARD | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| build year | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE; UNKNOWN allowed |
| HIN/CIN claim | GATE_1_OPTIONAL | SENSITIVE | INTERNAL | DISPLAY_ONLY | OPTIONAL |

Hard:

```text
Brand != Builder
raw broker brand/model claim != resolved BoatDesignRef
HIN/CIN claim != proof of ownership/title
```

A BoatDesign match may assist/relate identity but MUST NOT erase the raw broker claim or project design technical values into this yacht.

### C. PhysicalBoat technical core

All topics below are `PHYSICAL_BOAT` and `MATERIAL` unless a later contract explicitly reclassifies them.

| Topic | Phase | Presentation | Search | Gate-1 response |
|---|---|---|---|---|
| LOA / actual length | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| beam | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| draft | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| displacement | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| hull material | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| keel configuration | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| rudder configuration | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| rig configuration | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| engine make | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| engine model | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| engine power | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| engine hours | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| fuel type | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| cabins | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| berths | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
| heads | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |

Units/types MUST be explicit in the normative registry. Do not use ambiguous raw strings for numeric search fields where a normalized value/unit contract is required.

Design/configuration reference values may be shown alongside these facts later, but a missing PhysicalBoat value remains `UNKNOWN`; the registry MUST NOT specify "fall back to BoatDesign value" as physical truth.

### D. PhysicalBoat history / refit

| Topic | Phase | Risk | Presentation | Search | Gate-1 response |
|---|---|---|---|---|---|
| refit events | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| known previous-owner count | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL; UNKNOWN allowed |
| broad use history | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL; UNKNOWN allowed |
| grounding history | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| major damage history | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| osmosis treatment/history | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| last survey date / survey claim | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |

Known previous-owner count MUST NOT capture names/identifying details of prior private owners and MUST NOT be treated as a yacht-quality score.

Broad use history may support values such as:

```text
PRIVATE
CHARTER
SAILING_SCHOOL
RACING
LIVEABOARD
COMMERCIAL
UNKNOWN
```

No search/filter behavior for previous-owner count, use history or refit history is required in v0.1.

History-sensitive fields MUST allow `UNKNOWN` and, where logically applicable, `NO_KNOWN_HISTORY_DECLARED`; they MUST NOT model lack of reports as proven absence.

## Sensitive field presentation lock

For every v0.1 `SENSITIVE` field, the registry MUST carry a presentation-policy identifier or equivalent machine-readable rule proving that a plain unqualified display is forbidden.

Examples of forbidden output when only a broker claim exists:

```text
VAT: PAID
Grounding: NO
Damage history: NONE
HIN/CIN: VERIFIED
```

The contract must preserve enough information for later UI wording equivalent to:

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

Exact legal copy is out of scope and requires later product/legal review.

## Registry integrity rules

The machine-readable registry MUST fail validation if any of these occur:

1. field has no subject;
2. field omits allowed assertion kinds;
3. `ABSENT` and `NO_KNOWN_HISTORY_DECLARED` are represented as the same value;
4. delivery phase and risk class are encoded in one combined enum;
5. a `SENSITIVE` field is `SEARCHABLE` in v0.1;
6. a `SENSITIVE` public field lacks an explicit attributed/non-verified presentation policy;
7. free-text narrative is marked as structured `SEARCHABLE` truth;
8. `known_previous_owner_count` is marked searchable in v0.1;
9. `refit_events` claims document attachment/verification merely because documentation is declared available;
10. design reference is allowed to fill a missing PhysicalBoat field automatically;
11. a numeric technical field lacks explicit normalized type/unit semantics;
12. a required-response field forbids `UNKNOWN` where the field can truthfully be unknown and no stronger evidence is required;
13. price `AMOUNT` can exist without currency or amount;
14. POA invents an amount;
15. Brand and Builder are collapsed into one canonical identity concept.

## Required adversarial examples/tests

### A. Unknown vs absence vs no-known-history

Prove mechanically:

```text
autopilot UNKNOWN != autopilot ABSENT

grounding UNKNOWN
!=
grounding NO_KNOWN_HISTORY_DECLARED
!=
proven never grounded (unsupported state)
```

### B. Design projection

Given:

```text
BoatDesign draft = 1.65 m
PhysicalBoat draft = UNKNOWN
```

result MUST remain:

```text
PhysicalBoat draft = UNKNOWN
```

No registry/default rule may synthesize 1.65 m as this yacht's draft.

### C. Conflicting refit observations

```text
Org A: standing rigging replaced 2021
Org B: standing rigging replaced 2022
```

Without accepted resolution:

```text
CONFLICT
hard-search eligibility -> NO
```

### D. Same-authority correction

```text
Org A observation #1: replaced 2021
Org A observation #2: explicitly supersedes #1, corrected to 2022
```

Expected semantic result:

```text
#1 retained for audit/history
#2 current statement for Org A
not an automatic permanent conflict solely because #1 existed
```

The example MUST prove explicit same-authority/context validation. A different Organization cannot use supersession to erase Org A's claim.

### E. Documentation availability

```text
supporting_documentation_declared_available = YES
```

MUST NOT imply:

```text
document attached
reviewed
verified
```

### F. Sensitive + early phase independence

Use VAT/tax status or accepted equivalent to prove:

```text
phase = GATE_1_OPTIONAL
risk  = SENSITIVE
```

No `SENSITIVE_LATER` combined shortcut.

### G. Free-text extraction

Given narrative:

```text
"Rigging was done by the previous owner a few years ago."
```

The contract/example MUST reject any deterministic promotion to exact year 2022.

If candidate extraction metadata is represented at all, exact timing stays unknown/approximate and extraction confidence remains separate from truth/provenance.

## Normative deliverables

Normally:

1. `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
2. `specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json`
3. `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
4. focused contract/registry tests
5. `scripts/inspect_marketplace_field_contract.py`
6. this slice doc moved to `REVIEW` at handoff

A small fixture file for adversarial examples is allowed if it makes the contract clearer/reproducible.

Changes to runtime marketplace identity or persistence modules should normally be unnecessary. If a runtime implementation change appears necessary merely to define this contract, STOP and report.

## Owner inspection

Required command, normally:

```text
uv run python scripts/inspect_marketplace_field_contract.py
```

Expected visible result must be generated from the real registry/contract validation, not hard-coded PASS text.

Illustrative output:

```text
MARKETPLACE FACT CONTRACT

FIELD REGISTRY
Gate-1 required          -> <count>
Gate-1 optional          -> <count>
Later                    -> <count>
Sensitive                -> <count>

asking price             -> LISTING_OFFER / MATERIAL / SEARCHABLE
broker description       -> LISTING_OFFER / STANDARD / DISPLAY_ONLY
draft                    -> PHYSICAL_BOAT / MATERIAL / SEARCHABLE
known previous owners    -> PHYSICAL_BOAT / MATERIAL / DISPLAY_ONLY
refit events              -> PHYSICAL_BOAT / MATERIAL / DISPLAY_ONLY
VAT/tax status           -> LISTING_OFFER / SENSITIVE / DISPLAY_ONLY / GATE_1_OPTIONAL
grounding history        -> PHYSICAL_BOAT / SENSITIVE / DISPLAY_ONLY / LATER

UNKNOWN vs ABSENT                    -> DISTINCT
ABSENT vs NO_KNOWN_HISTORY_DECLARED -> DISTINCT
DESIGN -> PHYSICAL AUTO-PROJECTION   -> FORBIDDEN
CONFLICT satisfies hard search       -> NO
same-authority correction            -> EXPLICIT SUPERSESSION
cross-source overwrite               -> FORBIDDEN
document declared available          -> NOT ATTACHED / NOT VERIFIED
sensitive field plain assertion      -> FORBIDDEN
free-text auto promotion             -> FORBIDDEN

MARKETPLACE FACT CONTRACT RESULT -> PASS
```

Exact formatting may differ, but all semantics above must be observable.

## Acceptance criteria

- [ ] ONE-CAPABILITY, VISIBLE-RESULT and Product Execution Plan checks remain PASS.
- [ ] Normative `MARKETPLACE_FACT_CONTRACT.v0.1` exists and is consistent with all controlling artifacts.
- [ ] Machine-readable field-registry schema exists.
- [ ] Machine-readable v0.1 registry contains exactly the bounded semantic topics locked by this readiness; no full yacht/equipment catalog is invented.
- [ ] Every registry field explicitly classifies subject, assertion kinds, presentation, search use, Gate-1 requiredness, delivery phase and claim-risk class.
- [ ] Delivery phase and risk class are mechanically independent.
- [ ] `ABSENT`, `NO_KNOWN_HISTORY_DECLARED` and `UNKNOWN` are mechanically distinct where applicable.
- [ ] Observation assertion kind and cross-observation resolution state are distinct concepts.
- [ ] `UNKNOWN`, `UNRESOLVED` and `CONFLICT` cannot satisfy a future hard Required search predicate.
- [ ] Design-reference values cannot be projected into missing PhysicalBoat fields.
- [ ] Brand and Builder remain distinct.
- [ ] Raw broker brand/model claims remain distinct from resolved BoatDesign identity.
- [ ] Same-authority correction requires explicit non-destructive supersession and preserves audit/history.
- [ ] Cross-source disagreement cannot overwrite or supersede another source by recency alone.
- [ ] Supporting-documentation declaration is distinct from attachment/review/verification and no upload path is introduced.
- [ ] All SENSITIVE v0.1 fields are DISPLAY_ONLY and carry explicit attributed/non-verified presentation policy.
- [ ] VAT/tax status proves `GATE_1_OPTIONAL + SENSITIVE` can coexist.
- [ ] Grounding/damage/known-history semantics never convert silence/unknown into proven absence.
- [ ] Broker summary/description/history narrative remain free text and DISPLAY_ONLY for structured-truth purposes.
- [ ] Free-text/LLM extraction cannot auto-promote structured truth; extraction confidence is not truth confidence.
- [ ] Minimal refit-event structure supports exact/approximate/unknown timing and declared-document availability without file upload.
- [ ] Known previous-owner count is optional/display-only, includes no prior private-owner identity, and is not a quality score.
- [ ] Owner inspection reports PASS only after real registry validation/adversarial assertions succeed.
- [ ] No PostgreSQL/Alembic change is introduced.
- [ ] No PhysicalBoat fact persistence, broker UI, publication/lifecycle/freshness, document/media upload, LLM extraction, dedup or later-slice capability is introduced.
- [ ] Repository validation, format/lint/type checks and full relevant test suite pass; project coverage remains >=90% where coverage applies.
- [ ] Exact-head CI and Manufacturer artifact reproducibility are green before acceptance where applicable.
- [ ] No SLICE-0045 or later work starts automatically.

## Expected touch points

Expected only:

- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- `specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json`
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- focused tests under `tests/unit/` or an existing contract-test area
- `scripts/inspect_marketplace_field_contract.py`
- optional small adversarial fixture
- `docs/slices/SLICE-0044-gate1-marketplace-field-contract.md`

Normally do NOT change:

- `src/hullq/domain/market_identity.py`
- `src/hullq/persistence/native_listing.py`
- Alembic revisions
- legacy SQL migrations
- Search evaluator production code
- FastAPI/frontend/media modules

If a controlling semantic defect in an existing accepted schema is discovered, STOP rather than silently amending it inside this slice.

## Validation

At minimum:

```text
uv run python scripts/inspect_marketplace_field_contract.py
uv run python -m coverage run -m pytest
uv run python -m coverage report
uv run ruff format --check .
uv run ruff check .
uv run mypy src
uv run python scripts/validate_repository.py
uv lock --check
uv run pip-audit
```

No database environment is required for the owner result because this slice does not persist marketplace facts.

## Stop conditions

STOP and report instead of inventing a workaround if:

- a required field can only be represented by collapsing BoatDesign and PhysicalBoat truth;
- `UNKNOWN`, `ABSENT`, `NO_KNOWN_HISTORY_DECLARED` or `CONFLICT` would need to be conflated to fit an existing convenience type;
- claim-risk and delivery-phase classifications cannot remain independent;
- a sensitive field would require unqualified "verified" presentation without evidence/verification capability;
- a required Gate-1 claim would force document/PDF upload;
- proper correction semantics would require destructive overwrite;
- cross-source corrections cannot be distinguished from same-authority corrections;
- the slice would need to rewrite existing accepted `CLAIM_SEMANTICS_SCHEMA.v0.1`, `FIELD_EVIDENCE_SCHEMA.v0.3` or Market Identity semantics without a separate accepted architecture decision;
- a full yacht/equipment catalog, persistence schema, broker GUI, search implementation, lifecycle/freshness, media, dedup, LLM extraction or other later capability becomes necessary to make the owner inspection PASS.

## Status handoff rule

The implementing/research agent may set/recommend `IN_PROGRESS`, `BLOCKED`, or `REVIEW`, but MUST NOT mark SLICE-0044 `DONE`.

Any amendment changes HEAD and resets independent exact-head review.

No later slice starts automatically.

## Required completion report

Use the exact completion-report structure in `docs/slices/SLICE_TEMPLATE.md`.

Do not substitute a generic Summary/Test plan response.
