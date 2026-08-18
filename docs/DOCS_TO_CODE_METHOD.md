# HullQ — Docs-to-Code Method

**Status:** ACCEPTED project method  
**Applies to:** all product, data, research, API, market-integration and infrastructure work in the HullQ repository.

## 1. Principle

HullQ is developed **docs-to-code**. Implementation follows an explicit chain:

```text
problem / evidence
      ↓
open question (when needed)
      ↓
decision / ADR
      ↓
normative specification
      ↓
requirement IDs + acceptance criteria
      ↓
test specification / fixtures
      ↓
implementation
      ↓
automated verification
      ↓
release / changelog / evidence
```

Code MUST NOT silently define product semantics that should have been decided in documentation first.

## 2. Normative language

Normative HullQ documents use the uppercase requirement words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** in the BCP 14 sense (RFC 2119 as clarified by RFC 8174).

Lowercase words such as "should" remain ordinary prose and are not normative requirements.

## 3. Documentation classes

### 3.1 Normative

Normative documents define externally or internally observable behavior and implementation contracts.

Primary locations:

- `specs/REQUIREMENTS.md`
- versioned JSON Schemas under `specs/`
- versioned taxonomy/formula/validation specifications under `specs/`
- API contracts once introduced

If code behavior changes, the relevant normative document MUST be updated in the same logical change.

### 3.2 Decision records

Accepted ADRs under `architecture/decisions/` explain significant decisions, alternatives and consequences.

An ADR does not replace the normative spec. When an ADR changes behavior, the affected normative documents MUST be updated together with the ADR.

### 3.3 Operational protocols

`research/` and later operational runbooks define how repeatable processes are executed. They MUST conform to normative specifications.

### 3.4 Explanatory/project documents

`PROJECT_CONTEXT.md`, strategy documents and rationale explain intent and context. They do not override normative specifications.

### 3.5 Historical/reference material

`reference/` is non-normative. Imported material MUST NOT become an invisible production source.

## 4. Requirement lifecycle

Every behaviorally significant requirement receives a stable ID.

Recommended namespaces:

- `REQ-PROD-*` — product/scope
- `REQ-DATA-*` — canonical data semantics
- `REQ-ID-*` — identity/generation/variant rules
- `REQ-SEARCH-*` — query/matching semantics
- `REQ-RATIO-*` — derived formulas
- `REQ-RESEARCH-*` — research pipeline behavior
- `REQ-MARKET-*` — marketplace integration
- `REQ-ALERT-*` — saved-query/alert behavior
- `REQ-API-*` — HTTP/API behavior
- `REQ-SEC-*` — security/privacy
- `REQ-OPS-*` — operations/observability
- `REQ-GOV-*` — governance/traceability

A requirement is implementation-ready only when it has:

1. a stable ID;
2. a normative statement;
3. rationale/context where useful;
4. explicit acceptance criteria;
5. verification method;
6. dependencies or related ADR/open-question IDs where applicable;
7. no unresolved blocker.

## 5. Open questions

A material uncertainty MUST become an `OQ-*` entry rather than an implicit coding choice when it can change:

- stored data meaning;
- search results;
- public/API contracts;
- legal/commercial access assumptions;
- security/privacy behavior;
- system topology;
- substantial implementation cost;
- future migration cost.

The process is defined in `docs/governance/OPEN_QUESTION_PROCESS.md`.

## 6. Architecture decisions

Use ADRs for decisions with meaningful cost of reversal or architectural consequences. Keep one decision per ADR.

ADRs use statuses:

- `PROPOSED`
- `ACCEPTED`
- `SUPERSEDED`
- `REJECTED`
- `DEPRECATED`

Accepted ADRs are immutable except for metadata/typo corrections. A changed decision receives a new ADR that supersedes the old one.

## 7. Tests before or with code

For domain behavior, tests SHOULD be specified before implementation and MUST exist before a change is considered complete.

Test IDs use the corresponding requirement ID where practical, for example:

```text
REQ-SEARCH-004
  → TEST-REQ-SEARCH-004-A
  → TEST-REQ-SEARCH-004-B
```

Critical domain rules require boundary and regression tests in addition to happy-path tests.

## 8. Change discipline

A behavior change follows:

```text
open question / evidence if required
→ decision if required
→ spec + requirement update
→ tests
→ implementation
→ verification
→ changelog when user/data/API behavior changed
```

Do not merge a state in which documentation and implementation intentionally disagree.

## 9. AI coding-agent rule

Coding agents MUST read, in this order:

1. `CLAUDE.md`
2. `PROJECT_CONTEXT.md`
3. `docs/DOCS_TO_CODE_METHOD.md`
4. `specs/REQUIREMENTS.md`
5. relevant versioned specs
6. relevant accepted ADRs
7. relevant operational docs

If a requested implementation depends on an unresolved open question, the agent MUST surface the blocker and work on the decision/specification artifact rather than inventing the rule.

## 10. Repository rule

HullQ is a **single-repository project**. All application code, services, schemas, migrations, research tooling, tests, infrastructure-as-code and project documentation belong in the same repository unless a future accepted ADR explicitly changes this.

See `architecture/decisions/ADR-0001-single-repository.md`.

## References

- IETF BCP 14 / RFC 2119 and RFC 8174 for normative requirement language.
- JSON Schema Draft 2020-12 for JSON data contracts.
- ADR practice based on lightweight Architecture Decision Records.
- Semantic Versioning 2.0.0 for released public contracts once a stable public API exists.
