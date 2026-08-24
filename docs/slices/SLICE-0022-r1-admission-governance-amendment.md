# SLICE-0022 — R1 Admission Governance Amendment

**Applies to:** SLICE-0022 — Retained Alternative-Route Tier-0 Admission Safety Pilot  
**Governance status:** ACTIVE AMENDMENT  
**Reason:** independent review identified that the broader R1 `P31/P279*` discovery route does not by itself provide the same admission-authority guarantee as the accepted direct-instance route used in SLICE-0017/0018.

This document is a controlling governance amendment for the remainder of SLICE-0022. Where this amendment conflicts with the original SLICE-0022 R1 admission wording, this amendment governs. All other SLICE-0022 constraints remain unchanged.

## Review finding that triggered this amendment

The retained SLICE-0021 R1 candidate `Q232393` has:

```text
label: Zweier-Canadier
description_en: German term: a boat class in Canoeing
route_membership: R1
```

The first SLICE-0022 implementation classified it `AUTO_ADMIT / ok` because the implementation reused the SLICE-0017/0018 Tier-0 rule of usable label plus no identity collision.

That outcome demonstrates that R1 route membership is suitable as a discovery signal but is not sufficient, by itself, to authorize canonical BoatModel admission.

The correct response is not to add a keyword heuristic, QID blacklist, manufacturer-prefix rule, fuzzy classifier or ad-hoc semantic interpretation of retained descriptions/P31/P279. Those approaches would create new uncontrolled identity semantics.

## Authorized architectural rule

### R1 is discovery-authoritative, not admission-authoritative

For SLICE-0022, **R1 membership alone MUST NEVER produce `AUTO_ADMIT`.**

The 53 retained R1 candidates are processed as follows:

1. If the retained candidate has no usable source-backed label under accepted Tier-0 rules:
   - decision: `NOT_ADMITTED`;
   - reuse the accepted `missing_label` reason.

2. If the retained candidate has a usable source-backed label:
   - decision: `REVIEW_REQUIRED`;
   - reason: `r1_alternative_route_requires_review`.

3. Search-projection collision analysis against the accepted 1,829-candidate baseline and within the complete 57-candidate SLICE-0022 set MUST still be computed and retained for audit/review context.

4. A collision may add or preserve accepted collision evidence/reason semantics where the implementation model permits complete deterministic reasons, but it MUST NOT weaken the route-level `REVIEW_REQUIRED` boundary.

5. No R1 candidate may receive a new HullQ canonical BoatModel admission or canonical evidence link in SLICE-0022.

This rule is deliberately route-level and fail-closed. It makes no claim that every R1 candidate is invalid. It means only that this broader discovery route does not carry enough authority to auto-admit a canonical BoatModel without a later, separately governed promotion rule or corroborating evidence path.

## Authorized reason code

SLICE-0022 is authorized to add exactly one new R1 review reason:

```text
r1_alternative_route_requires_review
```

Meaning:

> Candidate was discovered only through the broader retained R1 alternative class-closure route. The route is useful for discovery, but is not sufficient by itself for automatic canonical BoatModel admission.

This reason MUST NOT imply that the candidate is invalid, non-sailing, duplicate, or globally novel.

The already-authorized R3 reason remains unchanged:

```text
r3_repair_signal_requires_review
```

## Expected decision boundary after this amendment

Given the currently retained SLICE-0021 facts, the expected high-level boundary is:

```text
R1 usable label      -> REVIEW_REQUIRED
R1 missing label     -> NOT_ADMITTED
R3 usable label      -> REVIEW_REQUIRED
R3 missing label     -> NOT_ADMITTED if accepted missing-label semantics apply
AUTO_ADMIT from R1   -> 0
AUTO_ADMIT from R3   -> 0
```

The exact R1 usable-label / missing-label counts must be recomputed from the immutable retained inputs rather than hard-coded from the disputed first implementation result.

`Q232393` specifically MUST NOT remain `AUTO_ADMIT`.

## What is NOT authorized

This amendment does NOT authorize:

- live Wikidata or other network acquisition;
- description keyword inclusion/exclusion rules;
- a canoe/dinghy/catamaran/ship-type blacklist;
- manual per-QID admission decisions;
- inference from P31/P279/P176/P287 into new canonical entity types or relations;
- production adoption of R1 or R3 discovery;
- Stage-3.3 technical field enrichment;
- modification of accepted SLICE-0017/0018/0021 retained artifacts;
- SLICE-0023.

## Provenance timestamp correction remains mandatory

SLICE-0022 performs zero live acquisition. Therefore implementation MUST preserve the retained SLICE-0021 source-fact acquisition/observation time for candidate `retrieved_at` / ResearchObservation `observed_at` semantics where applicable.

A later SLICE-0022 computation time MUST be represented separately as manifest generation/recomputation metadata and MUST NOT masquerade as a new source retrieval time.

Repeated offline classification MUST NOT mutate source-fact observation timestamps.

## Offline verification and replay hardening remain mandatory

The independent-review amendment requirements remain in force:

- verify complete immutable references, ordered candidate universe, candidate fields, collision records, every derived count, crosswalk preservation/bijection, usage metrics and fixed manifest semantics;
- schema validation must be part of the fail-closed verification path;
- checked-in replay evidence must itself be validated offline against the retained manifest before a fresh PostgreSQL replay may overwrite/reproduce it;
- standalone replay must verify the retained manifest before database mutation;
- deterministic non-self-referential artifact digests must be retained and verified;
- tamper-focused tests must cover the above boundaries.

Because this amendment produces zero canonical admissions from R1/R3 under the retained route-only evidence, PostgreSQL replay must prove the accepted 1,770 canonical BoatModel baseline remains unchanged after applying the SLICE-0022 research/review evidence package, unless accepted persistence semantics intentionally retain non-canonical research bundles for review candidates. In all cases, canonical BoatModel IDs/payloads must remain exactly the accepted baseline set and no new Brand/Organization/BoatDesign rows may appear.

## Completion / acceptance boundary

SLICE-0022 may return to `REVIEW` only when all of the following are true:

- the implementation obeys the R1 review-only rule above;
- `Q232393` is not auto-admitted;
- R3 remains fail-closed;
- zero live acquisition occurred;
- source-fact timestamps are corrected;
- offline verifier, artifact digests and replay safety are hardened as required;
- local validation passes;
- exact final-head remote CI passes;
- production discovery remains unchanged;
- SLICE-0023 was not created or started.

Explicit project-owner acceptance and the normal separate closure flow are still required before SLICE-0022 may become `DONE`.
