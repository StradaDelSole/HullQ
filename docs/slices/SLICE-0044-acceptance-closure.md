# SLICE-0044 — Acceptance closure

**Slice:** SLICE-0044  
**Type:** DESIGN_RESEARCH / CONTRACT  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #140  
**Accepted implementation HEAD:** `e7b2b063b3b078c75f06494bb59518586f01618f`  
**Implementation merge commit:** `50da2de08ff1c13823e6bafd4fc0d024c88e0ca6`  
**Owner acceptance:** explicitly recorded 2026-09-04

## Accepted scope

SLICE-0044 freezes the bounded Gate-1 marketplace field/claim contract that must govern later PhysicalBoat and NativeListing fact persistence.

Accepted capability:

```text
marketplace field definition
+ subject classification
+ assertion semantics
+ provenance / resolution constraints
+ presentation / search-use classification
+ requiredness / delivery phase / risk classification
        ↓
machine-readable registry + schema
        ↓
adversarial contract tests
        ↓
owner-inspectable PASS result
```

This slice is deliberately contract-only. It does not implement PostgreSQL/Alembic persistence, FastAPI/Astro/React surfaces, broker workspace UI, media/document upload or LLM extraction runtime.

## Accepted core truth model

The accepted contract preserves the hard marketplace truth boundary:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

A BoatDesign reference may assist identification or broker workflow, but it must not silently populate a missing PhysicalBoat value.

The accepted assertion vocabulary keeps these meanings distinct:

```text
VALUE_ASSERTION
PRESENT
ABSENT
NO_KNOWN_HISTORY_DECLARED
UNKNOWN
NOT_APPLICABLE
```

Hard accepted semantics include:

```text
UNKNOWN != ABSENT
ABSENT != NO_KNOWN_HISTORY_DECLARED
```

`ABSENT` is for a bounded present-state absence claim where logically valid, such as no auxiliary engine fitted.

`NO_KNOWN_HISTORY_DECLARED` is a materially weaker history statement and must never be presented or queried as proof that an event never occurred.

## Independent metadata axes

Every registry field is classified independently along the accepted dimensions:

- subject: `PHYSICAL_BOAT` or `LISTING_OFFER`;
- allowed assertion kinds;
- normalized value type and cardinality;
- presentation: `PUBLIC` or `INTERNAL`;
- search use: `SEARCHABLE` or `DISPLAY_ONLY`;
- requiredness: `REQUIRED_RESPONSE`, `CONDITIONAL` or `OPTIONAL`;
- delivery phase: `GATE_1_REQUIRED`, `GATE_1_OPTIONAL` or `LATER`;
- claim risk class: `STANDARD`, `MATERIAL` or `SENSITIVE`.

Delivery phase and claim risk are explicitly independent. A field may therefore be required/optional at Gate 1 while still being sensitive.

## Sensitive-claim safety lock

The accepted contract classifies heightened legal/regulatory/title/tax/insurability/major-damage/latent-defect/survey/safety/warranty-like representations as `SENSITIVE`.

All `SENSITIVE` fields in v0.1 are `DISPLAY_ONLY` and carry a machine-readable presentation policy that requires attributed, non-authoritative wording and disclosure of verification status.

Examples of forbidden unqualified presentation from an unverified broker claim include:

```text
VAT: PAID
Grounding: NO
Damage history: NONE
HIN/CIN: VERIFIED
```

The contract preserves enough context for later presentation equivalent to:

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

Sensitive filtering/search requires a later explicit contract amendment and product/legal review.

## Search fail-closed semantics

SLICE-0044 does not implement search, but it locks future hard-filter eligibility:

```text
RESOLVED compatible value -> may satisfy Required
UNKNOWN                    -> NO
UNRESOLVED                 -> NO
CONFLICT                   -> NO
```

A conflicting observation that happens to match the buyer query must not be opportunistically selected to manufacture a match.

`NO_KNOWN_HISTORY_DECLARED` must not satisfy a predicate equivalent to "proven never occurred".

## Correction / supersession semantics

A genuine correction is non-destructive and requires explicit same-authority supersession:

```text
new observation
+ explicit supersedes_observation_id (or accepted equivalent)
+ same authorized claim authority/context
-> old observation retained for audit/history
-> new observation becomes that claimant's current statement
```

A different Organization/source cannot supersede another Organization's observation merely by being newer.

For ordinary single-valued fact topics, contradictory current observations remain `CONFLICT`/unresolved unless separately resolved. There is no silent "latest wins" behavior.

The accepted pattern aligns with the repository's existing non-destructive `supersedes_evidence_id` concept without reusing research-evidence identity as marketplace observation identity.

## Free-text contract

The accepted Gate-1 registry retains broker narrative fields:

```text
listing_offer.broker_summary
listing_offer.broker_description
listing_offer.known_history_narrative
```

Narrative remains useful broker text but is `DISPLAY_ONLY` for structured truth/search.

Hard accepted rule:

```text
free text != structured searchable fact
```

Future extraction may only follow:

```text
text -> candidate extraction -> uncertainty -> human confirm/edit/ignore
```

Never:

```text
text -> automatic resolved/verified PhysicalBoat truth
```

And:

```text
EXTRACTION CONFIDENCE != TRUTH CONFIDENCE
```

## Price / POA conditionality

The accepted requiredness contract has an explicit `CONDITIONAL` state.

For price:

```text
price_mode = AMOUNT -> amount + currency required
price_mode = POA    -> amount must not be invented
```

A guessed price must never be created merely to satisfy completeness.

## Accepted Gate-1 field registry

The accepted registry contains exactly 38 field entries:

- 9 `LISTING_OFFER` fields;
- 6 `PHYSICAL_BOAT` identity/basic-claim fields;
- 16 `PHYSICAL_BOAT` technical-core fields;
- 7 `PHYSICAL_BOAT` history/refit fields, including 4 explicitly deferred `LATER` sensitive-history exemplars.

The bounded registry includes the agreed commercial/identity/technical/history core without becoming a complete yacht/equipment catalog.

Representative accepted fields include:

```text
asking price mode / amount / currency
location country / region
broker summary / description / history narrative
VAT/tax claim
marketed brand claim / builder claim / model designation claim
boat name / build year / internal HIN-CIN claim
LOA / beam / draft / displacement
hull material / keel / rudder / rig
engine make / model / power / hours / fuel type
cabins / berths / heads
refit events
known previous-owner count
broad use history
```

Deferred sensitive exemplars include grounding history, major damage history, osmosis treatment/history and last survey claim/date.

`Brand != Builder`, raw broker brand/model claims do not equal a resolved BoatDesignRef, and an HIN/CIN claim is not proof of title/ownership.

## Minimal refit / upgrade structure

The accepted repeatable `physical_boat.refit_events` structure contains only the Gate-1 minimum:

```text
event_kind
category
topic
action
timing
description
supporting_documentation_declared_available
```

Accepted bounded category vocabulary:

```text
RIGGING
SAILS
ENGINE_PROPULSION
ELECTRICAL_ENERGY
NAVIGATION
HULL
DECK
PLUMBING
HVAC_COMFORT
INTERIOR
SAFETY
OTHER
```

Accepted event kinds:

```text
MAINTENANCE
UPGRADE_OR_REPLACEMENT
MAJOR_REFIT
```

Accepted actions:

```text
INSTALLED
REPLACED
REFURBISHED
UPGRADED
REPAIRED
OTHER
```

### Refit timing

The final accepted timing structure carries the actual temporal value rather than a bare precision token:

```text
precision:          EXACT | APPROXIMATE | UNKNOWN
exact_year:         integer | null
exact_date:         valid ISO 8601 calendar date | null
approximate_period: non-empty, non-whitespace-only short text | null
```

Hard accepted rules:

```text
EXACT
-> exactly one of exact_year / exact_date
-> never neither, never both
-> exact_date must be a real parseable ISO calendar date
-> no approximate_period

APPROXIMATE
-> non-empty, non-whitespace approximate_period
-> no exact_year / exact_date

UNKNOWN
-> no temporal payload at all
```

## Documentation availability boundary

The accepted refit structure intentionally distinguishes declaration from evidence ingestion:

```text
documentation declared available
!= document attached to HullQ
!= document reviewed
!= claim verified
```

No PDF/document upload path, malware scanning requirement or document verification runtime is introduced by this slice.

## Ownership / use-history semantics

`known_previous_owner_count` is optional, display-only, not a yacht-quality score and must not contain names/identifiers of prior private owners.

`broad_use_history` is accepted as a bounded `MULTI` field with values:

```text
PRIVATE
CHARTER
SAILING_SCHOOL
RACING
LIVEABOARD
COMMERCIAL
```

The field is lifetime, non-exclusive and open-world positive.

A source declaring `{PRIVATE}` does not implicitly claim that charter, racing or another use never occurred.

Positive declarations are additive both across authorities and within the same authority unless an explicit same-authority supersession retracts/replaces a prior observation.

Accepted examples:

```text
Org A: {PRIVATE}
Org B: {CHARTER}
-> NOT CONFLICT
-> convenience union {PRIVATE, CHARTER}

Org A #1: {PRIVATE}
Org A #2: {CHARTER}
(no supersession)
-> Org A current positive set {PRIVATE, CHARTER}

Org A #1: {PRIVATE}
Org A #2: {CHARTER} supersedes #1
-> Org A current positive set {CHARTER}
```

`UNKNOWN` contributes no positive category but does not erase active positive declarations from the same or another authority.

The per-authority and cross-authority unions are resolution/presentation conveniences only. They do not upgrade provenance or verification strength and do not claim completeness.

Cross-authority supersession remains impossible.

## Independent exact-head review history

Independent review was repeated after every material implementation HEAD change.

Initial implementation HEAD:

```text
1ef609a7aec49cabfab60b64aa078a62f2d55953
```

Verdict: **AMEND**.

Findings:

- refit timing carried only `EXACT | APPROXIMATE | UNKNOWN` without an actual year/date/approximate payload;
- refit category was unbounded despite the readiness requiring a bounded category;
- `broad_use_history` was incorrectly single-valued.

First amended HEAD:

```text
9d6e18a70738d428a100c992f90771ff506e7a04
```

Verdict: **AMEND**.

Findings:

- differing positive `broad_use_history` sets were still treated as conflicts despite non-exclusive lifetime semantics;
- EXACT timing allowed both `exact_year` and `exact_date` simultaneously and lacked sufficient real-date/whitespace validation.

Second amended HEAD:

```text
ead2a3c38521167760df24bf24e89210463ccf1e
```

Verdict: **AMEND**.

Finding:

- same-authority active positive use-history observations were still discarded as ambiguous rather than unioned under the newly accepted open-world semantics.

Final amended HEAD:

```text
e7b2b063b3b078c75f06494bb59518586f01618f
```

Final verdict: **ACCEPT**.

No blocker, high or medium finding remained on the accepted exact HEAD.

## Exact-head validation gates

On accepted HEAD `e7b2b063b3b078c75f06494bb59518586f01618f`:

- owner inspection: `MARKETPLACE FACT CONTRACT RESULT -> PASS`;
- contract test file: 440 tests;
- full local suite reported: `3953 passed / 254 skipped`;
- project coverage reported: `90.93%`;
- ruff format/check: PASS;
- mypy: PASS;
- repository validation: PASS (`29 active schemas`, `88/88 requirements/acceptance`);
- `uv lock --check`: PASS;
- dependency audit / `pip-audit`: no known vulnerabilities;
- CI run `33901561305`: SUCCESS;
  - quality / Ubuntu: SUCCESS;
  - quality / Windows: SUCCESS;
  - PostgreSQL 18 DB integration: SUCCESS;
  - dependency audit: SUCCESS;
- Manufacturer artifact reproducibility run `33901561293`: SUCCESS;
  - Ubuntu reproduction: SUCCESS;
  - Windows reproduction: SUCCESS.

Remote CI and Manufacturer reproducibility were independently verified on the exact accepted HEAD before owner acceptance.

## Merge verification

PR #140 was merged with expected-head protection against accepted implementation HEAD:

```text
e7b2b063b3b078c75f06494bb59518586f01618f
```

Canonical implementation merge commit:

```text
50da2de08ff1c13823e6bafd4fc0d024c88e0ca6
```

## Retained scope boundaries

SLICE-0044 does **not** implement or authorize:

- PhysicalBoat persistence;
- marketplace fact/observation persistence;
- NativeListing field persistence beyond the existing SLICE-0043 immutable envelope;
- Alembic changes;
- runtime claim resolution under `src/hullq`;
- public listing publication;
- lifecycle/freshness;
- FastAPI endpoints;
- Astro/React UI;
- broker listing workspace/inventory management;
- media/photo/document upload;
- malware scanning;
- document review/verification/adjudication;
- LLM extraction runtime;
- automatic free-text-to-fact promotion;
- complete yacht/equipment catalog;
- bulk/CSV/XML/JSON/API/feed intake;
- NautiX implementation;
- broker public profile/contact surface;
- Saved Search/monitoring/alerts;
- leads/ContactRequest;
- private-owner BrokerageRequest workflow;
- legal/tax/survey certification by HullQ;
- SLICE-0045 or later implementation.

## Operational result

SLICE-0044 is owner-accepted and operationally complete under the HullQ slice workflow.

The accepted contract is the controlling input for the next bounded implementation work on PhysicalBoat / marketplace fact persistence. This closure does not itself create, authorize or start SLICE-0045; the next capability requires separate architectural reassessment/readiness under the ONE-CAPABILITY and VISIBLE-RESULT rules.
