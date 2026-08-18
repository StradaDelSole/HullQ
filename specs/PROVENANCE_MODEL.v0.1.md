# HullQ Provenance Model v0.1

**Status:** ACCEPTED  
**Decision:** OQ-004 / ADR-0006  
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Scope

This specification defines persistence semantics for direct source evidence, canonical field resolution and derived-value lineage.

It does not select a database product and does not define ratio formulas.

## 2. Separation of concerns

HullQ MUST keep canonical searchable values separate from provenance records.

The canonical domain subject stores the current value. Provenance is represented by:

- `FieldEvidence` — immutable source observation;
- `FieldResolution` — versioned canonical decision;
- `DerivationRecord` — lineage of calculated/inherited outputs.

Field wrappers containing `{value,evidence}` MUST NOT become the canonical BoatDesign representation.

## 3. Subject identity and field addressing

Every FieldEvidence and FieldResolution MUST identify:

```text
subject_kind
subject_id
field_pointer
```

`field_pointer` MUST use RFC 6901 JSON Pointer syntax relative to the identified subject's canonical contract.

Examples:

```text
BoatDesign BD_001      /baseline/dimensions/loa_m
BoatDesign BD_001      /generation/first_built
DesignOption OPT_004   /overrides/dimensions/draft_min_m
NamedVariant VAR_002   /overrides/configuration/rig_type
```

Stable domain IDs MUST be used for identity-bearing subentities. Numeric array positions SHOULD NOT be used as provenance identity because array order is not domain identity.

## 4. FieldEvidence

A FieldEvidence record MUST:

- have a stable immutable ID;
- identify exactly one subject field;
- reference exactly one HullQ Source record;
- preserve the raw source representation needed to audit the claim;
- preserve a normalized candidate and normalization method/version where normalization occurred;
- identify how/by whom the observation was produced;
- carry evidence-level confidence;
- carry capture/observation time;
- remain immutable after creation.

Corrections MUST create a new evidence record and MAY identify an earlier record via `supersedes_evidence_id`.

A FieldEvidence record MUST NOT itself decide the canonical value.

## 5. FieldResolution

A FieldResolution MUST represent one decision state for one subject field.

Allowed states:

- `resolved`;
- `resolved_with_conflict`;
- `unknown`;
- `needs_review`;
- `conflict`.

A resolved state MUST preserve the evidence used to support the canonical value.

A `resolved_with_conflict` state MUST also retain contradicting evidence IDs.

An unresolved `conflict`, `unknown` or `needs_review` state MUST NOT silently produce a non-null canonical value.

Resolution history MUST be retained. A new resolution MAY supersede a previous resolution but MUST NOT erase it.

The persistence implementation MUST enforce at most one current/active resolution per `(subject_kind, subject_id, field_pointer)`.

## 6. Canonical-value consistency

For a non-null source-backed production value:

```text
canonical value
== active FieldResolution.canonical_value_snapshot
```

and the active resolution MUST be either `resolved` or `resolved_with_conflict`.

This invariant MUST be covered by persistence/integration tests.

Record-level quality status MAY be materialized for convenience but MUST be derivable/auditable from field states and validation rules rather than replacing field-level provenance.

## 7. Source-rights integration

A FieldEvidence record used to support a production value MUST reference a Source allowed for `production_value` use under `SOURCE_RIGHTS_POLICY.v0.1.md`, including satisfaction of any conditional obligations.

Unknown/prohibited/legal-review-required clearance MUST NOT support automatic production acceptance.

The provenance store MUST support reverse lookup from `source_id` to affected evidence/resolutions so that rights or source-validity changes can trigger re-evaluation.

## 8. Raw and normalized values

When normalization occurs, evidence MUST retain:

- raw representation;
- raw unit if applicable;
- normalized candidate value;
- canonical unit if applicable;
- normalization method/rule identifier;
- normalization method version where behavior can change.

Example:

```text
raw:       "34 ft 7 in"
raw unit:  imperial compound length
candidate: 10.541
unit:      m
rule:      length.parse-and-convert
version:   1
```

Formatting/rounding for display MUST NOT overwrite the canonical normalized value.

## 9. Visual/classification evidence

A technical drawing or profile image may support a classification such as `skeg_hung` even when no source text spells out that category.

Such evidence MUST identify the observation as visual/classification evidence and MUST NOT fabricate a textual quote.

The producer/tool/model version and confidence MUST remain auditable.

## 10. DerivationRecord

A value computed from canonical HullQ inputs MUST use derivation lineage instead of FieldEvidence.

A DerivationRecord MUST identify:

- target subject and field;
- deterministic method ID/version;
- input subject/field references and, where available, resolution IDs;
- output value snapshot;
- producer/tool version;
- generation timestamp.

ResolvedConfiguration inheritance/override resolution and derived ratios are examples.

## 11. Provenance model alignment

HullQ's model is conceptually compatible with W3C PROV's Entity / Activity / Agent separation, but HullQ does not require RDF, OWL or PROV-O persistence.

The domain JSON contracts remain the normative implementation interface.

## 12. Read projections

An API/UI MAY expose convenient joined projections such as:

```json
{
  "value": 10.54,
  "confidence": "high",
  "sources": ["SRC_001", "SRC_004"]
}
```

Such a projection is derived presentation data and MUST NOT become a second canonical source of truth.

## 13. Conflict handling

Conflicting evidence MUST remain retained.

Automatic resolution MAY occur only under an accepted deterministic adjudication rule. Otherwise the field becomes `conflict` or `needs_review`.

Manual adjudication MUST record resolver identity, resolution method, policy version and contradicting evidence.

## 14. Deletion / correction

Evidence and resolution history SHOULD be append-oriented. Corrections SHOULD supersede prior records instead of destructive overwrite.

Legal deletion requirements, personal-data deletion and source-artifact retention are outside this OQ and MUST override append-history behavior where applicable law/policy requires deletion.

## 15. Contract files

This accepted contract is represented by:

- `specs/FIELD_EVIDENCE_SCHEMA.v0.1.json`;
- `specs/FIELD_RESOLUTION_SCHEMA.v0.1.json`;
- `specs/DERIVATION_RECORD_SCHEMA.v0.1.json`;
- `fixtures/provenance/`.

## 16. Proposed semantic validation rules

These validation-rule IDs are active semantic requirements of OQ-004 and MUST be implemented/tested when provenance persistence is implemented.

| ID | Severity | Rule |
|---|---|---|
| VAL-PROV-001 | error | `field_pointer` MUST be a valid RFC 6901 JSON Pointer for the declared subject contract; positional array indexes MUST NOT be used as stable identity for identity-bearing collections. |
| VAL-PROV-002 | error | FieldEvidence used by a production resolution MUST reference a Source cleared for `production_value` use with all applicable conditions satisfied. |
| VAL-PROV-003 | error | If raw and normalized representations differ materially, a normalization method ID/version MUST be recorded. |
| VAL-PROV-004 | error | Supporting and contradicting evidence IDs MUST be included in the considered evidence set for that resolution. |
| VAL-PROV-005 | error | A current resolved canonical value MUST equal the current FieldResolution canonical-value snapshot. |
| VAL-PROV-006 | error | At most one current FieldResolution may exist for one `(subject_kind, subject_id, field_pointer)`. |
| VAL-PROV-007 | error | `unknown`, `needs_review` and unresolved `conflict` states MUST NOT produce a non-null canonical value. |
| VAL-PROV-008 | error | `resolved_with_conflict` MUST preserve at least one contradicting evidence record. |
| VAL-PROV-009 | review | A Source rights/validity change MUST allow reverse lookup of every dependent evidence/resolution for re-evaluation. |
| VAL-PROV-010 | error | A DerivationRecord MUST identify a deterministic method version and at least one input; derived values MUST NOT invent direct external-source evidence. |
| VAL-PROV-011 | error | A superseding evidence/resolution record MUST address the same logical subject field as the record it supersedes unless an explicit migration links the change. |
