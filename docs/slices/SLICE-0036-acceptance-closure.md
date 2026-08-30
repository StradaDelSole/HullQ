# SLICE-0036 — Acceptance closure

**Slice:** SLICE-0036  
**Type:** DESIGN_RESEARCH  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #106  
**Accepted implementation HEAD:** `b523fe0263ea6db91be556cf3f7960da97af7d59`  
**Implementation merge commit:** `24452900d5b6588bd9d626e3efe0ac3c48417da0`  
**Owner acceptance:** explicitly recorded 2026-08-31

## Accepted scope

SLICE-0036 establishes the bounded v0.1 marine-technical entailment contract over the existing HullQ v0.6 technical vocabulary plus the preserved v0.5 `rig_type` / `rudder_type` compatibility vocabulary.

Accepted artifacts:

- `specs/MARINE_TECHNICAL_ENTAILMENT.v0.1.md`
- `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json`
- `tests/contract/test_marine_technical_entailment.py`
- `research/validation/SL0036-marine-entailment-real-design-validation.md`

The accepted contract contains 31 `DEFINITIONAL_ENTAILMENT` rules, a closed declarative rule grammar, fail-closed qualification/applicability/conflict guards, independent schema/vocabulary coverage checks, derived-lineage requirements, and retained-evidence validation against at least three technically different real designs.

No production marine-entailment inference/projection runtime was accepted under `src/`.

## Review history

- `81bcc22281df86e8a953a1244919b420366d1a06` — review `5061793180`: CHANGES REQUIRED.
- `91467cb23f309e79a142a6a8cef644c7784b2320` — review `5061992508`: CHANGES REQUIRED.
- `b523fe0263ea6db91be556cf3f7960da97af7d59` — review `5062048297`: ACCEPT.

The amendments closed production-runtime scope leakage, self-authorizing coverage, unsupported evidence basis, contextual fact manufacture, sentinel contradictions, non-mechanical guard semantics, rule/output-grammar closure gaps, structural-UNKNOWN/Search-truth ambiguity, orphan-rule risk, and twin-rudder conditional tamper gaps.

One cosmetic non-blocker remains: a stale test function name says `not_a_sentinel`; its assertion and the normative contract correctly treat `not_applicable` as a reserved Search semantic sentinel. No acceptance-changing commit was made solely for that name.

## Exact-head gates

On accepted HEAD `b523fe0263ea6db91be556cf3f7960da97af7d59`:

- CI run `33338465138`: SUCCESS.
- Manufacturer artifact reproducibility run `33338465122`: SUCCESS.

## Merge verification

PR #106 was merged with expected-head protection against the accepted exact HEAD.

Canonical `main` moved to merge commit `24452900d5b6588bd9d626e3efe0ac3c48417da0`, whose parents are:

- prior `main`: `b13ab2f49b47272750d686718980877aceeefc24`
- accepted SLICE-0036 HEAD: `b523fe0263ea6db91be556cf3f7960da97af7d59`

## Retained boundaries

SLICE-0036 did not add schema vocabulary, a general marine ontology, probabilistic inference, recursive inference, persistence/search/API/frontend implementation, canonical BoatDesign admission, or Oceanis 30.1 work.

The next product step remains constrained by the previously accepted guardrail: apply the accepted marine entailment semantics to real retained data and move toward at least one real BoatDesign being searchable through the existing Search kernel before another general breadth/governance expansion, unless a genuine technical blocker requires otherwise.
