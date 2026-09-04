# SLICE-0044 — Marketplace Fact Contract & Gate-1 Field Registry

**ID:** SLICE-0044  
**Type:** DESIGN_RESEARCH  
**Status:** REVIEW  
**Stage:** Native Marketplace Foundation — fact semantics before PhysicalBoat persistence/workspace  
**Depends on:** SLICE-0040–0043 owner-accepted / DONE; `docs/MARKETPLACE_FACT_CLAIM_SEMANTICS_2026-09-04.md` accepted/merged  
**Blocks:** PhysicalBoat/listing-fact persistence, broker listing workspace, listing read/search, structured refit/history search, sensitive-claim presentation, scalable listing intake

## Objective

Answer exactly one business-critical design question and freeze it in machine-checkable form:

> **What is the smallest Gate-1 marketplace fact/field contract that lets a professional broker describe a real yacht and current offer usefully, while preserving HullQ's Design-vs-PhysicalBoat truth boundary, provenance, UNKNOWN/CONFLICT semantics, non-destructive corrections and liability-safe treatment of sensitive claims?**

The slice produces a normative contract, machine-readable registry and executable owner inspection. It does **not** persist PhysicalBoat facts or build the broker workspace.

## Product execution checks

**ONE-CAPABILITY CHECK:** PASS  
One capability only: define and mechanically validate the marketplace field/claim contract future native listing input must obey.

**VISIBLE-RESULT CHECK:** PASS  
The owner can run one inspection command and see the exact field matrix plus adversarial semantic proofs.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
SLICE-0043 created durable NativeListing identity/persistence. Before physical/listing fact persistence and broad UI/search, the fact model must be frozen so schema/UI convenience cannot weaken truth or liability boundaries.

## Why this slice exists

Competitor research showed strong broker UX patterns — structured specs, free-text description, model-data assistance, quality/completeness checks, refit narratives and inventory tooling — but also the common risk of treating manufacturer/model data or broker-entered fields as if they were inherently authoritative facts about the specific yacht.

HullQ's target is:

```text
free text for narrative
+
structured observations for facts/claims
+
explicit source/provenance
+
UNKNOWN / UNRESOLVED / CONFLICT
+
Design reference for assistance only
```

The accepted 2026-09-04 Marketplace Fact & Claim Semantics decision adds four important locks:

1. `ABSENT` is not the same as `NO_KNOWN_HISTORY_DECLARED`;
2. delivery phase and claim-risk class are independent;
3. UNKNOWN/UNRESOLVED/CONFLICT fail closed for hard search;
4. correction uses explicit non-destructive supersession; another source cannot overwrite an earlier observation by recency alone.

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

`FIELD_EVIDENCE_SCHEMA.v0.3` already provides the accepted non-destructive `supersedes_evidence_id` precedent and separates producer/evidence/claim semantics. `OBSERVATION_APPLICABILITY_SCHEMA.v0.1` already treats unknown scope as unknown rather than global applicability.

SLICE-0044 MUST align with these principles without repurposing research-evidence schemas as the marketplace persistence model.

`CLAIM_SEMANTICS_SCHEMA.v0.1` remains the semantic role of an observation. It MUST NOT be overloaded with marketplace assertion state, resolution, provenance, requiredness, delivery phase or risk class.

## In scope

1. Normative `MARKETPLACE_FACT_CONTRACT.v0.1`.
2. Machine-readable field-registry schema.
3. Machine-readable v0.1 registry containing a bounded Gate-1 core plus a few explicitly deferred sensitive/history exemplars.
4. Contract tests/validation for every registry entry.
5. Free-text listing narrative separated from structured fact truth.
6. Minimal repeatable refit/upgrade claim structure with no document upload.
7. Explicit correction/supersession and cross-source conflict examples.
8. Owner inspection showing all required invariants.

## Explicitly out of scope

- PostgreSQL/Alembic changes;
- PhysicalBoat/listing-fact persistence;
- changes to SLICE-0040 identity or SLICE-0043 persistence semantics;
- PhysicalBoat/MarketEpisode dedup/resolution;
- broker workspace UI;
- FastAPI/Astro/React surfaces;
- publication/lifecycle/freshness;
- photo/media/document upload;
- malware scanning implementation;
- document verification/adjudication;
- LLM extraction implementation;
- automatic free-text-to-fact promotion;
- complete yacht/equipment catalog;
- generic CRM, leads, referrals, pricing, transactions;
- NautiX/CSV/feed implementation;
- legal/tax certification by HullQ;
- SLICE-0045+.

## Required independent meta-model axes

Every registered field/fact topic MUST explicitly classify the following. Do not collapse them into one status enum.

### Subject

```text
PHYSICAL_BOAT
LISTING_OFFER
```

`DESIGN_REFERENCE` remains a distinct reference/source scope used in examples and later assistance; it is never silently a PhysicalBoat value.

### Allowed assertion kinds

The v0.1 names may vary only if these semantics remain mechanically distinct:

```text
VALUE_ASSERTION
PRESENT
ABSENT
NO_KNOWN_HISTORY_DECLARED
UNKNOWN
NOT_APPLICABLE
```

Each field declares an allowed subset.

Hard:

```text
ABSENT != NO_KNOWN_HISTORY_DECLARED != UNKNOWN
```

`ABSENT` is a current/bounded-state claim (for example equipment absent). `NO_KNOWN_HISTORY_DECLARED` means the claimant declares no relevant history known to them; it is not proof the event never occurred.

### Resolution state

Separate from assertion kind:

```text
UNRESOLVED
RESOLVED
CONFLICT
```

### Claim authority / provenance

The contract must preserve who/what asserted an observation. Gate-1 native input is professional-Organization/broker sourced, but the model must not assume all future observations come from the current broker.

Hard:

```text
BROKER_CLAIM != VERIFIED_FACT
```

### Supporting-evidence state

Keep distinct:

```text
supporting documentation declared available
supporting documentation attached to HullQ
supporting documentation reviewed by HullQ
claim verified / not verified
```

No file upload exists in this slice.

### Presentation

```text
PUBLIC
INTERNAL
```

### Search use

```text
SEARCHABLE
DISPLAY_ONLY
```

This classifies intended future structured-search use; it does not implement search here.

### Gate-1 requiredness

```text
REQUIRED_RESPONSE
CONDITIONAL
OPTIONAL
```

`REQUIRED_RESPONSE` means the broker/workflow must answer the field, but the answer MAY be explicit `UNKNOWN` where allowed. Never force a guessed value merely to achieve completeness.

`CONDITIONAL` MUST carry a machine-readable condition.

Price lock:

```text
price_mode = AMOUNT -> amount + currency are required
price_mode = POA    -> amount is not invented
```

### Delivery phase

```text
GATE_1_REQUIRED
GATE_1_OPTIONAL
LATER
```

### Claim risk class

```text
STANDARD
MATERIAL
SENSITIVE
```

Delivery phase and risk class are independent. A field may be `GATE_1_OPTIONAL + SENSITIVE`.

## Deterministic claim-risk rule

### SENSITIVE

Use when the claim's nature creates heightened risk of being relied on as legal, regulatory, title/ownership, tax, insurability, major-damage/history, latent-defect/history, survey/condition, safety or warranty-like representation.

Strong triggers:

- HIN/CIN/registration/title/ownership identity where used as legal identity evidence;
- VAT/tax-paid status;
- major accident/damage/grounding history;
- insurance-loss/claim history if later added;
- osmosis/major latent-defect history;
- current-condition statements that could be mistaken for a survey/certification/seaworthiness assurance;
- other statements where false/outdated presentation could materially affect legality, insurability, safety/seaworthiness or substantial transaction economics and therefore require special wording/evidence handling.

### MATERIAL

Commercially/technically important values such as price, build year, draft, engine hours and refit claims that materially affect value/suitability but do not by ordinary display imply HullQ legal/survey certification.

### STANDARD

Ordinary narrative/display metadata without the heightened implications above.

### Conservative v0.1 sensitive-field rule

Every `SENSITIVE` field in registry v0.1 MUST be `DISPLAY_ONLY`. Every public sensitive field MUST carry a machine-readable attributed/non-verified presentation policy. Sensitive filtering/search requires a later explicit contract amendment and product/legal review.

## Hard future-search semantics

Although this slice does not implement listing search, it MUST lock future eligibility:

```text
RESOLVED compatible value -> may satisfy Required
UNKNOWN                    -> NO
UNRESOLVED                 -> NO
CONFLICT                   -> NO
```

A conflicting observation that happens to match the buyer query MUST NOT be selected to manufacture a match.

For `Prefer`, unresolved/conflicting observations MUST NOT receive an invented positive score merely because one candidate value matches.

`NO_KNOWN_HISTORY_DECLARED` MUST NOT satisfy a predicate equivalent to "proven never occurred".

## Correction / supersession

### Same-authority correction

A genuine correction is non-destructive:

```text
new observation
+ explicit supersedes_observation_id (or accepted equivalent)
+ same authorized claim authority/context
-> old observation retained for audit/history
-> new observation becomes that claimant's current statement
```

The implementation may align with the existing `supersedes_evidence_id` pattern but MUST NOT incorrectly reuse research-evidence identity where marketplace observation identity requires its own type.

### Cross-source disagreement

A different Organization/source cannot supersede another merely by being newer.

```text
Org A: 2021
Org B: 2022
-> CONFLICT unless separately resolved
```

### Same-source contradiction without explicit correction

No silent "latest wins". A contradictory later observation that is not explicitly authorized as correction remains conflict/unresolved.

## Free-text rules

Registry v0.1 MUST include:

```text
broker_summary
broker_description
known_history_narrative
```

Rules:

- narrative remains broker text;
- narrative is `DISPLAY_ONLY` for structured truth/search;
- text alone cannot satisfy technical Required filters;
- structured facts may separately capture important claims mentioned in narrative;
- no parser/LLM may auto-promote description text into resolved/verified PhysicalBoat truth.

Future extraction flow, not implemented here:

```text
text -> candidate extraction -> uncertainty -> human confirm/edit/ignore
```

Hard:

```text
EXTRACTION CONFIDENCE != TRUTH CONFIDENCE
```

Example text such as "Rigging was done by the previous owner a few years ago" MUST NOT become an exact 2022 replacement claim automatically.

## Minimal refit / upgrade structure

Include one repeatable `refit_events`-equivalent `PHYSICAL_BOAT` claim structure. Gate-1 optional, initially display-only.

Minimum event semantics:

```text
event_kind:
  MAINTENANCE | UPGRADE_OR_REPLACEMENT | MAJOR_REFIT

category:
  bounded high-level category

topic/item:
  non-empty text or bounded identifier

action:
  INSTALLED | REPLACED | REFURBISHED | UPGRADED | REPAIRED | OTHER

timing:
  exact year/date | approximate timing | UNKNOWN

description:
  optional short text

supporting_documentation_declared_available:
  YES | NO | UNKNOWN
```

Claim authority/provenance belongs to the observation envelope/context, not uncontrolled text inside the event.

No invoice/PDF upload follows from `documentation_declared_available`.

## v0.1 bounded field registry

The implementation may choose clean machine identifiers, but the semantic topics and classifications below are locked. Do not expand into a complete yacht/equipment catalog.

### A. Listing offer

| Topic | Phase | Risk | Presentation | Search | Requiredness |
|---|---|---|---|---|---|
| asking price mode (`AMOUNT` / `POA`) | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| asking price amount | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | CONDITIONAL on `price_mode=AMOUNT` |
| currency | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | CONDITIONAL on `price_mode=AMOUNT` |
| current location country | GATE_1_REQUIRED | STANDARD | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| current location text/region | GATE_1_OPTIONAL | STANDARD | PUBLIC | SEARCHABLE | OPTIONAL |
| broker summary | GATE_1_OPTIONAL | STANDARD | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| broker description | GATE_1_REQUIRED | STANDARD | PUBLIC | DISPLAY_ONLY | REQUIRED_RESPONSE |
| known-history narrative | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| VAT/tax status claim | GATE_1_OPTIONAL | SENSITIVE | PUBLIC | DISPLAY_ONLY | OPTIONAL |

All are `LISTING_OFFER`.

`POA` MUST NOT create a synthetic asking-price amount.

### B. PhysicalBoat identity/basic claims

| Topic | Phase | Risk | Presentation | Search | Requiredness |
|---|---|---|---|---|---|
| marketed brand claim | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| builder claim | GATE_1_OPTIONAL | MATERIAL | PUBLIC | SEARCHABLE | OPTIONAL |
| model/designation claim | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE |
| boat name | GATE_1_OPTIONAL | STANDARD | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| build year | GATE_1_REQUIRED | MATERIAL | PUBLIC | SEARCHABLE | REQUIRED_RESPONSE; UNKNOWN allowed |
| HIN/CIN claim | GATE_1_OPTIONAL | SENSITIVE | INTERNAL | DISPLAY_ONLY | OPTIONAL |

All are `PHYSICAL_BOAT`.

Hard:

```text
Brand != Builder
raw broker brand/model claim != resolved BoatDesignRef
HIN/CIN claim != proof of title/ownership
```

A BoatDesign match may assist identity but does not erase the raw claim or project design specs into this yacht.

### C. PhysicalBoat technical core

All are `PHYSICAL_BOAT` and `MATERIAL`.

| Topic | Phase | Presentation | Search | Requiredness |
|---|---|---|---|---|
| actual LOA/length | GATE_1_OPTIONAL | PUBLIC | SEARCHABLE | OPTIONAL; UNKNOWN allowed |
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

Numeric search fields MUST define normalized type/unit semantics; no ambiguous unit-bearing strings as canonical searchable values.

Missing PhysicalBoat values remain UNKNOWN. No rule equivalent to "fall back to BoatDesign value" is allowed.

### D. PhysicalBoat history/refit

| Topic | Phase | Risk | Presentation | Search | Requiredness |
|---|---|---|---|---|---|
| refit events | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL |
| known previous-owner count | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL; UNKNOWN allowed |
| broad use history | GATE_1_OPTIONAL | MATERIAL | PUBLIC | DISPLAY_ONLY | OPTIONAL; UNKNOWN allowed |
| grounding history | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| major damage history | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| osmosis treatment/history | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |
| last survey date/survey claim | LATER | SENSITIVE | PUBLIC | DISPLAY_ONLY | not Gate-1 |

Known previous-owner count MUST NOT contain names/identifiers of prior private owners, is not searchable in v0.1 and is not a yacht-quality score.

Broad use-history values may include:

```text
PRIVATE
CHARTER
SAILING_SCHOOL
RACING
LIVEABOARD
COMMERCIAL
UNKNOWN
```

History-sensitive topics MUST allow `UNKNOWN` and, where logically appropriate, `NO_KNOWN_HISTORY_DECLARED`; silence cannot become proven absence.

## Sensitive presentation lock

Every v0.1 `SENSITIVE` field MUST carry a machine-readable presentation policy that forbids unqualified authoritative wording when HullQ has only a broker claim.

Forbidden examples under an unverified broker claim:

```text
VAT: PAID
Grounding: NO
Damage history: NONE
HIN/CIN: VERIFIED
```

The contract must preserve enough context for later UI wording equivalent to:

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

## Registry integrity rules

Machine validation MUST fail if any of these occur:

1. field lacks subject;
2. field lacks allowed assertion kinds;
3. `ABSENT`, `NO_KNOWN_HISTORY_DECLARED` and `UNKNOWN` collapse;
4. delivery phase and risk class share one combined enum;
5. `CONDITIONAL` requiredness lacks a machine-readable condition;
6. any `SENSITIVE` field is `SEARCHABLE` in v0.1;
7. public `SENSITIVE` field lacks attributed/non-verified presentation policy;
8. free-text narrative is structured-search truth;
9. previous-owner count is searchable in v0.1;
10. declared documentation availability implies attachment/review/verification;
11. Design reference may fill a missing PhysicalBoat value;
12. numeric searchable technical field lacks normalized type/unit semantics;
13. required-response field forces guessed value where UNKNOWN is legitimate;
14. `price_mode=AMOUNT` can pass without amount+currency;
15. `price_mode=POA` invents an amount;
16. Brand and Builder collapse;
17. a different source can supersede another source by recency alone.

## Required adversarial examples/tests

### UNKNOWN vs absence/history

```text
autopilot UNKNOWN != autopilot ABSENT

grounding UNKNOWN
!= grounding NO_KNOWN_HISTORY_DECLARED
!= unsupported "proven never grounded"
```

### Design projection

```text
BoatDesign draft = 1.65 m
PhysicalBoat draft = UNKNOWN
-> PhysicalBoat draft remains UNKNOWN
```

### Conflicting refit claims

```text
Org A: standing rigging replaced 2021
Org B: standing rigging replaced 2022
-> CONFLICT
-> hard-search eligibility NO
```

### Same-authority correction

```text
Org A #1: 2021
Org A #2: explicitly supersedes #1 -> 2022
```

Expected:

```text
#1 retained
#2 current statement for Org A
no automatic permanent conflict solely because #1 existed
```

A different Organization cannot use supersession to erase Org A's claim.

### Documentation availability

```text
documentation_declared_available = YES
!= attached
!= reviewed
!= verified
```

### Risk/phase independence

VAT/tax status must prove:

```text
phase = GATE_1_OPTIONAL
risk  = SENSITIVE
```

No `SENSITIVE_LATER` shortcut.

### Conditional price requiredness

Prove:

```text
AMOUNT + missing amount -> invalid
AMOUNT + missing currency -> invalid
AMOUNT + amount + currency -> valid
POA + no amount -> valid
POA + synthetic/invented amount -> invalid
```

### Free-text extraction

`"Rigging was done by the previous owner a few years ago"` MUST NOT become an exact-year structured claim automatically.

If candidate extraction metadata is modeled at all, timing remains approximate/unknown and extraction confidence remains separate from truth/provenance.

## Normative deliverables

Normally:

1. `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
2. `specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json`
3. `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
4. focused contract/registry tests
5. `scripts/inspect_marketplace_field_contract.py`
6. this slice doc -> `REVIEW` at handoff

A small adversarial fixture is allowed if useful.

Runtime identity/persistence changes should normally be unnecessary. If runtime implementation seems necessary merely to define the contract, STOP.

## Owner inspection

Normally:

```text
uv run python scripts/inspect_marketplace_field_contract.py
```

The output MUST derive from real registry validation/assertions, not hard-coded PASS text.

Expected semantics:

```text
MARKETPLACE FACT CONTRACT

Gate-1 required          -> <count>
Gate-1 optional          -> <count>
Later                    -> <count>
Sensitive                -> <count>

price                     -> LISTING_OFFER / MATERIAL / SEARCHABLE
broker description        -> LISTING_OFFER / STANDARD / DISPLAY_ONLY
draft                     -> PHYSICAL_BOAT / MATERIAL / SEARCHABLE
previous-owner count      -> PHYSICAL_BOAT / MATERIAL / DISPLAY_ONLY
refit events               -> PHYSICAL_BOAT / MATERIAL / DISPLAY_ONLY
VAT/tax status            -> LISTING_OFFER / SENSITIVE / DISPLAY_ONLY / GATE_1_OPTIONAL
grounding history         -> PHYSICAL_BOAT / SENSITIVE / DISPLAY_ONLY / LATER

UNKNOWN vs ABSENT                    -> DISTINCT
ABSENT vs NO_KNOWN_HISTORY_DECLARED -> DISTINCT
DESIGN -> PHYSICAL AUTO-PROJECTION   -> FORBIDDEN
CONFLICT satisfies hard search       -> NO
same-authority correction            -> EXPLICIT SUPERSESSION
cross-source overwrite               -> FORBIDDEN
document declared available          -> NOT ATTACHED / NOT VERIFIED
sensitive plain assertion            -> FORBIDDEN
free-text auto promotion             -> FORBIDDEN
conditional price requiredness       -> PASS

MARKETPLACE FACT CONTRACT RESULT -> PASS
```

## Acceptance criteria

- [x] Product execution checks remain PASS.
- [x] `MARKETPLACE_FACT_CONTRACT.v0.1` exists and matches all controlling artifacts.
- [x] Machine-readable registry schema and v0.1 registry exist.
- [x] Registry contains exactly the bounded semantic topics locked here; no complete yacht/equipment catalog is invented.
- [x] Every field classifies subject, allowed assertion kinds, presentation, search use, requiredness, phase and risk.
- [x] `REQUIRED_RESPONSE`, `CONDITIONAL` and `OPTIONAL` are distinct; conditional fields carry machine-readable conditions.
- [x] Phase and risk are mechanically independent.
- [x] `ABSENT`, `NO_KNOWN_HISTORY_DECLARED` and `UNKNOWN` remain distinct.
- [x] Assertion kind and resolution state remain distinct.
- [x] UNKNOWN/UNRESOLVED/CONFLICT cannot satisfy future hard Required search.
- [x] Design values cannot auto-project into missing PhysicalBoat values.
- [x] Brand and Builder remain distinct; broker brand/model claims remain distinct from resolved BoatDesign identity.
- [x] Same-authority correction uses explicit non-destructive supersession and preserves audit/history.
- [x] Cross-source disagreement cannot overwrite/supersede by recency alone.
- [x] Documentation declaration is separate from attachment/review/verification; no upload path exists.
- [x] Every SENSITIVE v0.1 field is DISPLAY_ONLY and has explicit attributed/non-verified presentation policy.
- [x] VAT/tax status proves `GATE_1_OPTIONAL + SENSITIVE` coexist.
- [x] Grounding/damage/history semantics never convert silence/unknown into proven absence.
- [x] Broker summary/description/history narrative remain free text and DISPLAY_ONLY for structured truth.
- [x] LLM/free-text extraction cannot auto-promote truth; extraction confidence is not truth confidence.
- [x] Minimal refit structure supports exact/approximate/unknown timing and declared-document availability with no upload.
- [x] Previous-owner count is optional/display-only, contains no prior-owner identity and is not a quality score.
- [x] Conditional price rules are mechanically enforced.
- [x] Owner inspection reports PASS only after real registry/adversarial assertions succeed.
- [x] No PostgreSQL/Alembic/runtime marketplace persistence change is introduced.
- [x] No broker UI, publication/lifecycle/freshness, document/media upload, LLM extraction, dedup or later capability is introduced.
- [x] Repository validation, format/lint/type checks and relevant full suite pass; coverage remains >=90% where applicable.
- [ ] Exact-head CI and Manufacturer reproducibility are green before acceptance where applicable.
- [x] SLICE-0045+ is not started automatically.

## Expected touch points

Expected only:

- `specs/MARKETPLACE_FACT_CONTRACT.v0.1.md`
- `specs/MARKETPLACE_FIELD_REGISTRY_SCHEMA.v0.1.json`
- `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json`
- focused contract tests
- `scripts/inspect_marketplace_field_contract.py`
- optional small fixture
- this slice document

Normally do not change:

- `src/hullq/domain/market_identity.py`
- `src/hullq/persistence/native_listing.py`
- Alembic / legacy SQL
- production Search evaluator
- FastAPI/frontend/media code

If an accepted schema itself appears semantically defective, STOP rather than changing it inside this slice.

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

No PostgreSQL environment is required for this owner result because this slice does not persist marketplace facts.

## Stop conditions

STOP if:

- representing a field would require collapsing Design and PhysicalBoat truth;
- UNKNOWN/ABSENT/NO_KNOWN_HISTORY_DECLARED/CONFLICT must be conflated;
- phase/risk cannot remain independent;
- sensitive fields require unqualified verified presentation without evidence capability;
- Gate-1 would require document/PDF upload;
- correction requires destructive overwrite;
- cross-source and same-authority correction cannot be distinguished;
- accepted ClaimSemantics/FieldEvidence/MarketIdentity semantics would need rewriting;
- complete yacht/equipment catalog, persistence, broker GUI, search implementation, lifecycle/freshness, media, dedup, LLM extraction or later work becomes necessary for PASS.

## Status handoff rule

The agent may set/recommend `IN_PROGRESS`, `BLOCKED` or `REVIEW`, never `DONE`.

Any amendment changes HEAD and resets exact-head review. No later slice starts automatically.

## Required completion report

Use the exact structure from `docs/slices/SLICE_TEMPLATE.md`. Do not substitute a generic Summary/Test plan response.
