# HullQ Marketplace Fact & Claim Semantics

**Date:** 2026-09-04  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** SLICE-0044 and all later PhysicalBoat / NativeListing fact, history, broker-workspace, search/filter, verification and presentation work  
**Builds on:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`, `specs/CLAIM_SEMANTICS_SCHEMA.v0.1.json`, `specs/MARKET_IDENTITY_CONTRACT.v0.1.md`, `docs/slices/SLICE-0043-acceptance-closure.md`

## 1. Purpose

HullQ must allow brokers to describe real yachts usefully without silently converting broker statements, imported feed values, design references or document availability into stronger truth than the evidence supports.

This decision freezes the marketplace fact/claim architecture before the PhysicalBoat + Listing Field Contract is written.

Fundamental representation rule:

```text
useful structured information
!=
automatic HullQ assertion of truth
```

And the existing truth boundary remains controlling:

```text
DESIGN / CONFIGURATION TRUTH
!=
PHYSICAL BOAT / LISTING TRUTH
```

Broker/seller claims about a PhysicalBoat are observations/evidence. They do not silently become canonical facts merely because HullQ stores them in a structured field or displays them in a table.

This document is an architecture/policy input. It does not itself authorize implementation of every example field mentioned below. SLICE-0044 must translate it into a bounded Gate-1 field contract and machine-checkable semantics without widening into a full broker workspace, media system, document verification system or public listing UI.

---

## 2. Liability / representation principle

HullQ must not create avoidable legal, safety or financial exposure by presenting a claim more authoritatively than its provenance and verification state justify.

For materially consequential information, the system must be able to distinguish at least:

```text
what was claimed
who / what source made the claim
when it was asserted / last confirmed
what supporting evidence is said to exist
what evidence HullQ actually possesses
whether HullQ reviewed / verified anything
whether other observations conflict
```

Hard rules:

```text
UNKNOWN != ABSENT
UNKNOWN != FALSE
BROKER_CLAIM != VERIFIED_FACT
DOCUMENT_DECLARED_AVAILABLE != DOCUMENT_ATTACHED
DOCUMENT_ATTACHED != DOCUMENT_VERIFIED
DESIGN_REFERENCE != PHYSICAL_BOAT_TRUTH
NO_KNOWN_HISTORY_DECLARED != PROVEN_NEVER_OCCURRED
CONFLICT != RESOLVED
```

A UI disclaimer may supplement these semantics but MUST NOT substitute for them. The distinction must exist in the domain model / contract itself.

---

## 3. Separate the subject of a fact from the source of a claim

Every future marketplace field/fact definition must identify what the information is actually about.

Minimum subject classes:

```text
DESIGN_REFERENCE
PHYSICAL_BOAT
LISTING_OFFER
```

Examples:

```text
BoatDesign standard draft              -> DESIGN_REFERENCE
this yacht's fitted keel/draft         -> PHYSICAL_BOAT
current asking price / POA / location  -> LISTING_OFFER
```

A field definition must not rely on UI placement to imply the subject.

Design/configuration knowledge may assist broker entry, but it may not be projected into `PHYSICAL_BOAT` truth without an explicit PhysicalBoat-specific observation/confirmation.

---

## 4. Claim assertion semantics: do not overload one generic value-state enum

A single `KNOWN / UNKNOWN / CONFLICT / NOT_APPLICABLE` list is insufficient for marketplace claims because current-state absence and historical "no known event" declarations mean different things.

Future field contracts must therefore separate the **assertion made by an observation** from the **resolution status across observations**.

### 4.1 Observation assertion kind

The exact enum names may be finalized by SLICE-0044, but the semantics must be able to represent these distinct concepts:

```text
VALUE_ASSERTION
PRESENT
ABSENT
NO_KNOWN_HISTORY_DECLARED
UNKNOWN
NOT_APPLICABLE
```

Field definitions must declare which assertion kinds are valid for that field.

#### `ABSENT`

Use only where a claimant is actually asserting a current or bounded state of absence.

Example:

```text
autopilot -> ABSENT
```

This is a claim about the yacht's current equipment state.

#### `NO_KNOWN_HISTORY_DECLARED`

Use for history-sensitive questions where the truthful statement is limited by the claimant's knowledge.

Example:

```text
grounding history -> NO_KNOWN_HISTORY_DECLARED
```

This means:

> the claimant declares no grounding history known to them.

It MUST NOT be transformed into:

```text
this yacht has never grounded
```

The same pattern is relevant to fields such as known major damage history, known osmosis treatment/history, known insurance-loss history or similar historical declarations where absence cannot normally be proven from silence.

### 4.2 Resolution status is a separate axis

Across one or more observations about the same fact topic, HullQ must preserve a separate resolution state, conceptually including:

```text
UNRESOLVED
RESOLVED
CONFLICT
```

A claim being explicit does not mean the overall fact is resolved.

Example:

```text
Broker A: standing rigging replaced 2021
Broker B: standing rigging replaced 2022

=> CONFLICT until a valid resolution exists
```

The resolution mechanism must not overwrite away the existence of contradictory source observations.

---

## 5. Search/filter semantics for UNKNOWN and CONFLICT

Marketplace facts must obey the same fail-closed search principles as HullQ's existing Search architecture.

For a hard/Required filter or technical qualification:

```text
RESOLVED compatible value -> may satisfy the requirement
UNKNOWN                    -> does not satisfy the requirement
UNRESOLVED                 -> does not satisfy the requirement
CONFLICT                   -> does not satisfy the requirement
```

`CONFLICT` must never be treated as "pick whichever value matches the buyer query".

A future explicit user option such as "include unknown/conflicting" may expose those listings in a clearly separate manner, but it MUST NOT weaken the default hard-constraint semantics.

For `Prefer`/ranking behavior, unresolved/conflicting information must not receive an invented positive match score merely because one conflicting observation would have matched.

For sensitive history claims, a query must not silently translate `NO_KNOWN_HISTORY_DECLARED` into a stronger predicate such as "proven no prior grounding". Any future filter over such declarations must preserve the declaration semantics in its wording and result presentation.

---

## 6. Observation ownership, correction and supersession

A Refit/Upgrade/History statement is about a PhysicalBoat, but the observation itself belongs to the source/claimant context that asserted it.

Hard rule:

```text
PhysicalBoat fact topic
!=
mutable field that the latest broker simply overwrites
```

Multiple brokers / listings / feeds may produce multiple observations about the same PhysicalBoat fact topic.

### 6.1 Cross-source changes

A later claim by Broker B must not overwrite Broker A's earlier claim merely because it is newer.

If the observations disagree and no accepted resolution exists:

```text
=> CONFLICT
```

### 6.2 Correction by the same claim authority

A genuine correction of a claimant's own earlier statement must be representable without creating a permanent false conflict.

However, correction must not destroy audit history.

Preferred semantic direction:

```text
new observation
  explicitly supersedes prior observation
  under the same authorized claim authority / context
```

The prior observation remains retained for audit/history and for any historical listing snapshot in which it appeared.

A correction may become the claimant's current active statement, but it does not retroactively erase what was previously published/claimed.

A contradictory later observation that is **not** explicitly identified as a correction/supersession must not be silently assumed to correct the earlier one.

Cross-source observations cannot supersede each other merely because they disagree.

SLICE-0044 must define enough identity/context semantics to prevent "same broker" from being implemented as an unsafe fuzzy concept. Organization/account/listing context must be explicit wherever correction authority matters.

---

## 7. Refit / upgrade / maintenance semantics

Refit/upgrades are PhysicalBoat-related observations/events, not generic NativeListing prose and not mutable design facts.

Gate-1 should keep the structure intentionally small. The initial contract should be able to represent, at minimum, a claim such as:

```text
category
item / topic
action
year/date or explicitly approximate/unknown timing
short description
claim provenance
```

Candidate action semantics may include examples such as:

```text
INSTALLED
REPLACED
REFURBISHED
UPGRADED
REPAIRED
```

The contract should preserve the conceptual distinction among:

```text
MAINTENANCE
UPGRADE / REPLACEMENT
MAJOR REFIT
```

but must not force a giant event taxonomy Pre-Gate-1 if that is not needed for the visible capability.

Important:

> HullQ stores observations/claims about refit events concerning a PhysicalBoat. Resolution determines what HullQ may safely present as established fact.

---

## 8. Supporting-documentation semantics do not imply upload infrastructure

The system must distinguish at least these concepts:

```text
supporting documentation declared available
supporting documentation attached to HullQ
supporting documentation reviewed by HullQ
supporting documentation supports/conflicts with the claim
```

The exact later schema may vary, but these states may not be collapsed.

Pre-Gate-1 / SLICE-0044 may support a broker declaration equivalent to:

```text
supporting_documentation_declared_available = true / false / unknown
```

without accepting any file upload.

This avoids silently activating PDF/document infrastructure.

Actual document upload remains a later capability and, when introduced, must satisfy the accepted media/security architecture including quarantine, file validation, malware scanning appropriate to accepted document types, access control, retention and safe publication rules.

Hard rule:

```text
broker says an invoice exists
!=
HullQ possesses the invoice
!=
HullQ reviewed the invoice
!=
HullQ verified the claim
```

---

## 9. Sensitive claim risk is independent of delivery phase

Do not use a combined category such as `SENSITIVE_LATER` as the sole classification.

Two independent axes are required:

```text
DELIVERY PHASE
and
CLAIM RISK CLASS
```

### 9.1 Delivery phase

Conceptually:

```text
GATE_1_REQUIRED
GATE_1_OPTIONAL
LATER
```

This answers:

> when must HullQ support this field/capability?

### 9.2 Claim risk class

The exact enum may be finalized by the field contract, but the model must distinguish ordinary marketplace facts from claims requiring heightened treatment.

Recommended direction:

```text
STANDARD
MATERIAL
SENSITIVE
```

The purpose is not to classify every technically important value as legally "sensitive" merely because a wrong value could disappoint a buyer.

A field/claim should be classified `SENSITIVE` when its nature creates a heightened risk of being relied on as a legal, regulatory, safety, insurability, title/tax, defect/history or warranty-like representation.

Strong triggers include:

- ownership/title/registration/legal status;
- VAT/tax-paid or other tax-status representations;
- known major accident/damage/grounding history;
- insurance-loss/claim history where captured;
- known major latent-defect/history representations such as osmosis treatment/history;
- safety-critical current-condition assertions where the UI could reasonably imply a verified condition rather than a broker observation;
- other claims whose false/outdated presentation could materially affect legality, insurability, seaworthiness/safety or substantial transaction economics and which require special wording/evidence handling to avoid overstatement.

`MATERIAL` may cover commercially important facts that can materially affect value or fit but do not normally carry the same warranty-like/legal-history implication.

SLICE-0044 must define a deterministic classification rule/checklist rather than leaving risk classification to intuition.

A field may therefore validly be:

```text
GATE_1_REQUIRED + SENSITIVE
```

if it is commercially necessary early but still requires heightened claim semantics/presentation.

---

## 10. Sensitive claim presentation policy

Structured presentation must preserve the underlying claim strength.

Avoid unqualified labels such as:

```text
Grounding history: NO
VAT: PAID
Damage history: NONE
```

when HullQ possesses only a broker declaration.

Preferred semantics include explicit presentation of claimant/verification context, e.g. conceptually:

```text
No known grounding history declared
Source: broker / publishing Organization
Last confirmed: <timestamp>
HullQ verification: none
```

or for VAT/tax:

```text
VAT/tax status: broker-declared <value>
HullQ legal verification: none
```

Exact user-facing wording requires later product/legal review. The domain model must preserve enough information to make non-misleading presentation possible.

Absence of a reported issue must never be converted into proven absence.

---

## 11. Free text remains, but must not become the only home of important facts

Broker narrative remains a legitimate listing capability.

Preferred conceptual separation:

```text
short broker summary
full free-text description
optional known-history narrative
```

Structured technical/commercial/history facts remain separately representable for search, comparison, completeness and provenance.

A broker may write:

> Carefully upgraded for blue-water cruising over the last four years.

while structured observations separately capture the specific claimed upgrades.

---

## 12. LLM / extraction assistance is suggestion-only

A future extraction assistant may inspect free text and suggest structured facts, but it must never auto-promote extracted text into PhysicalBoat truth.

Required conceptual flow:

```text
free text
-> candidate extraction
-> source span / text evidence retained
-> extraction uncertainty represented
-> broker confirms / edits / ignores
-> only confirmed observation enters the marketplace claim model
```

Hard distinction:

```text
EXTRACTION CONFIDENCE
!=
TRUTH CONFIDENCE
```

Extraction confidence means only how confident the extraction system is that it interpreted the text as intended.

It does not mean the extracted claim is likely true.

Partial/uncertain text must stay partial/uncertain.

Example:

```text
"Rigging was done by the previous owner a few years ago."
```

must not silently become:

```text
standing rigging replaced 2022
```

The candidate should retain unknown/approximate timing until a human supplies or confirms a more precise value.

No LLM extraction implementation is authorized merely by this architecture decision.

---

## 13. Ownership / use history

Potential future PhysicalBoat claim topics include:

- known previous-owner count;
- current-owner-since;
- broad use history such as PRIVATE / CHARTER / SAILING_SCHOOL / RACING / LIVEABOARD / COMMERCIAL / UNKNOWN;
- major refit periods;
- availability of maintenance records, invoices, manuals and logbooks.

These are optional claims, not automatic quality scores.

A previous-owner count must not be treated as a proxy for yacht quality.

Pre-Gate-1 direction:

```text
known previous-owner count -> capture/display optional
search/filter              -> not required initially
```

Do not require public names or identifying details of previous private owners merely to express owner count/history.

---

## 14. Field-contract requirements for SLICE-0044

Every field or fact topic admitted to the upcoming PhysicalBoat + Listing Field Contract must be classified across explicit independent dimensions.

At minimum:

```text
subject / ownership:
  DESIGN_REFERENCE | PHYSICAL_BOAT | LISTING_OFFER

allowed assertion kinds:
  field-specific subset of VALUE_ASSERTION / PRESENT / ABSENT /
  NO_KNOWN_HISTORY_DECLARED / UNKNOWN / NOT_APPLICABLE

provenance / claimant:
  explicit, not inferred from display location

resolution behavior:
  including UNKNOWN / UNRESOLVED / CONFLICT handling

presentation:
  PUBLIC | INTERNAL or equivalent

search use:
  SEARCHABLE | DISPLAY_ONLY or equivalent

requiredness:
  required / optional under the relevant workflow

delivery phase:
  GATE_1_REQUIRED | GATE_1_OPTIONAL | LATER

claim risk class:
  STANDARD | MATERIAL | SENSITIVE or accepted equivalent
```

For any `SENSITIVE` field the contract must additionally define:

- permitted assertion semantics;
- minimum provenance required;
- whether broker declaration alone is allowed;
- whether search/filtering is allowed and with what wording/semantics;
- minimum visible attribution/verification context;
- whether a later evidence/verification capability is required before stronger presentation is allowed.

The field contract must not use one overloaded enum to answer all these dimensions.

---

## 15. Gate-1 sequencing principle

Architectural foresight must not become implementation scope inflation.

Use three layers:

```text
DOMAIN MODEL DIRECTION
what HullQ must eventually be able to express safely

GATE-1 FIELD SET
what first real broker listings need to capture/use

LATER ENRICHMENT
what waits for later bounded capabilities
```

SLICE-0044 must define a deliberately small Gate-1 set rather than implementing every potentially useful yacht-history field.

Likely Gate-1 candidates include:

- core listing/commercial facts needed to make an offer intelligible;
- core PhysicalBoat identity/configuration facts needed for HullQ technical evaluation;
- broker narrative description;
- minimal refit/upgrade observation structure where it materially improves buyer evaluation;
- explicit UNKNOWN / provenance semantics.

Examples of capabilities that should remain later unless a separate readiness decision proves them necessary:

- PDF/document upload;
- document verification/adjudication;
- comprehensive insurance/damage-history workflows;
- full ownership timeline;
- logbook upload/analysis;
- automatic LLM extraction;
- complex historical-resolution UI;
- broker CRM functionality.

---

## 16. Interoperability

External marketplace/feed standards may be mapped into HullQ later, including NautiX where commercially useful.

Hard rule:

> An external feed schema is an interchange format, not HullQ's internal truth model.

If an external standard cannot distinguish `UNKNOWN`, explicit absence, no-known-history declaration, provenance or conflict at HullQ's required precision, the importer/exporter must preserve HullQ semantics internally and map conservatively rather than weakening the internal model.

---

## 17. Implementation enforcement

This decision must not remain documentation-only guidance.

Before SLICE-0044 becomes READY, its readiness contract must explicitly reference this document as controlling and must require tests/inspection proving at least:

1. design-reference facts cannot silently become PhysicalBoat facts;
2. `UNKNOWN`, explicit `ABSENT` and `NO_KNOWN_HISTORY_DECLARED` remain mechanically distinct where applicable;
3. `CONFLICT`/UNRESOLVED values cannot satisfy hard search requirements;
4. claim-risk classification is independent from delivery phase;
5. same-authority correction uses explicit supersession/audit semantics rather than destructive overwrite;
6. cross-source disagreement cannot be silently treated as correction;
7. declared documentation availability does not imply attachment or verification;
8. sensitive broker claims retain broker/provenance/verification context and cannot be rendered as HullQ-certified fact by default;
9. free-text extraction, if represented at all, remains suggestion-only and cannot auto-promote truth;
10. the Gate-1 field set is bounded and does not silently pull document upload, full broker workspace, media, CRM, lifecycle/freshness or later history adjudication into the slice.

Any implementation that requires weakening these rules must STOP and request an explicit architecture decision rather than inventing a convenience shortcut.

---

## 18. Relationship to existing `CLAIM_SEMANTICS_SCHEMA.v0.1`

The existing `specs/CLAIM_SEMANTICS_SCHEMA.v0.1.json` describes the semantic role of a source observation (for example `nominal_design_value`, `individual_hull_value`, `identity_or_chronology_claim`) and explicitly does not encode source authority or confidence.

This marketplace decision does not silently repurpose that schema into a universal marketplace claim-state enum.

SLICE-0044 must decide explicitly whether to:

- reuse that schema only for its existing semantic-role purpose;
- extend it through a properly versioned successor where appropriate; or
- introduce separate marketplace assertion/resolution/risk concepts.

It must not overload the existing enum with unrelated provenance, verification, delivery-phase or resolution meanings merely for implementation convenience.

---

## 19. Non-goals of this decision

This document does not itself implement or authorize:

- PhysicalBoat persistence;
- a complete yacht/listing field catalog;
- public listing publication/lifecycle/freshness;
- broker workspace UI;
- FastAPI/Astro/React surfaces;
- media/document upload;
- malware scanning implementation;
- document verification or legal adjudication;
- LLM extraction;
- physical-vessel dedup/resolution;
- broker CRM;
- leads/referrals;
- pricing/entitlements;
- transactions/escrow/closing.

Those require separately bounded readiness and implementation.

---

## 20. Owner direction

The marketplace field architecture must optimize simultaneously for:

```text
useful broker input
buyer decision quality
searchability
truth/provenance integrity
non-destructive history
legal/safety representation discipline
bounded Gate-1 execution
```

HullQ's product advantage is not merely a longer listing form.

The intended differentiator is a marketplace where users can distinguish:

```text
what the design says
what a broker says about this yacht
what other sources say
what is actually resolved
what is still unknown
what conflicts
what evidence exists
what HullQ has and has not verified
```

without losing the practical free-text narrative and workflow efficiency brokers expect.
