# SLICE-0034 — Acceptance Closure

**ID:** SLICE-0034  
**Closure status:** OWNER_ACCEPTANCE_PENDING  
**Owner accepted:** PENDING  
**Final independent-review verdict:** ACCEPT — implementation plus two bounded amendments reviewed; no blocking findings remain  

## Effective implementation state

SLICE-0034 was implemented on PR #100.

- implementation PR: #100 — `SLICE-0034: BoatDesign technical-profile schema v0.6`;
- initial implementation head: `6ba3d6fe3e6e43ca741767796893146987d9b3c0`;
- first independent review: review `5059570255`, verdict **CHANGES REQUIRED**;
- amendment-1 head: `2136ab170c5a070f42d6b1e15dccbc642033e214`;
- second independent review: review `5059660217`, verdict **CHANGES REQUIRED**;
- final amendment head: `35b493da45e1ca3bc8007de52c1ec43dc0602812`;
- final independent review: review `5059809671`, verdict **ACCEPT**;
- implementation merge commit: `3207094dcf743c41b4f213a6704be1f5092106c4`;
- final exact-head CI: run `33288980505`, SUCCESS;
- final exact-head Manufacturer artifact reproducibility: run `33288980501`, SUCCESS.

The effective implementation state for Project Owner acceptance is main at merge commit `3207094dcf743c41b4f213a6704be1f5092106c4`.

## Delivered increment

SLICE-0034 adds `BOAT_DESIGN_SCHEMA.v0.6` as the next BoatDesign technical-profile contract while leaving v0.5 intact for historical payloads.

The v0.6 shape adds or decomposes:

- appendages: keel/centerboard/daggerboard/rudder/skeg as separate structures;
- rig: sailplan, masthead/fractional, mast count/step, detailed rig dimensions and sail-area facts/bases;
- deck: cockpit position/count, helm type/count, deck-saloon/pilothouse;
- propulsion: engine count, drive type, propeller configuration plus retained engine/fuel/water facts;
- accommodation: cabin/berth/head counts plus retained headroom/bridgedeck clearance;
- dimensions: LOD, beam-at-waterline, ballast type/material;
- compliance: CE/design-category representation;
- symmetric NamedVariant/DesignOption overrides for the technical families.

Four synthetic archetype fixtures prove classic aft cockpit, center cockpit, option-sensitive shallow-draft/twin-helm, and performance-rig/keel structures. No real-world BoatDesign was promoted.

## Review amendments

### Amendment 1 — conservative decomposition and bounded invariants

The first independent review found two blockers:

1. the original v0.5→v0.6 compatibility note over-inferred decomposed rig/rudder facts not guaranteed by the predecessor tokens;
2. obvious deterministic cross-field contradictions were still schema-valid.

The amendment corrected unproven mappings back to `unknown` and added bounded fail-closed invariants for hull configuration/count, skeg/rudder support, zero appendage counts with concrete descriptors, zero rudder count with concrete rudder facts, and zero cockpit/helm counts with concrete position/type.

`draft_min_m > draft_max_m` remains an explicitly documented JSON-Schema limitation because standard Draft 2020-12 cannot compare sibling numeric values without a new custom validation mechanism.

### Amendment 2 — preserve the guaranteed `twin` count fact

The second independent review found that amendment 1 had become over-conservative for `rudder_type = "twin"`: the predecessor token itself guarantees two rudders.

The final compatibility rule therefore:

- projects `twin + null count` to `rudder_count = 2`;
- preserves `twin + 2` as `2`;
- treats `twin + concrete non-2 count` as an internally inconsistent predecessor payload requiring conflict/manual resolution;
- continues to leave twin rudder position/support/balance as `unknown`;
- never synthesizes rudder count for non-twin predecessor types.

The analogous mapping audit found no further blocking information-loss case within the bounded v0.5→v0.6 decomposition.

## Exact-head validation evidence

Independent exact-head verification on `35b493da45e1ca3bc8007de52c1ec43dc0602812` confirmed:

- CI run `33288980505`: SUCCESS;
  - quality Ubuntu: SUCCESS;
  - quality Windows: SUCCESS;
  - dependency audit: SUCCESS;
  - PostgreSQL 18 db integration: SUCCESS;
- Manufacturer artifact reproducibility run `33288980501`: SUCCESS;
  - reproduce Ubuntu: SUCCESS;
  - reproduce Windows: SUCCESS.

The implementation report recorded local validation of 2,482 passed / 217 pre-existing skipped tests, overall coverage 91.30%, Ruff/mypy clean and repository validator PASS.

## Retained boundaries

SLICE-0034 does not:

- admit or promote any real BoatDesign/reference data;
- change OQ-009 fail-closed search semantics;
- wire v0.6 into production persistence/import/readback;
- implement categorical search evaluation;
- add PostgreSQL search read models;
- add API/frontend/SEO behavior;
- start the practical OQ-009 benchmark or next slice.

The disclosed repo-wide Python/jsonschema non-finite-number limitation remains non-blocking for this schema-only slice; it was not introduced by v0.6 and was not silently claimed as solved.

## Audit trail

- controlling slice contract: `docs/slices/SLICE-0034-technical-profile-schema-v06.md`;
- controlling profile requirements: `specs/TECHNICAL_PROFILE_SPEC.v0.1.md`;
- implementation PR: #100;
- final implementation head: `35b493da45e1ca3bc8007de52c1ec43dc0602812`;
- final ACCEPT review: `5059809671`;
- exact-head CI: `33288980505`, SUCCESS;
- exact-head Manufacturer: `33288980501`, SUCCESS;
- implementation merge: `3207094dcf743c41b4f213a6704be1f5092106c4`;
- Project Owner acceptance: **PENDING**.

## Next boundary

This closure records independent acceptance of SLICE-0034. It does not itself mark the slice DONE and does not authorize the next implementation slice.

Explicit Project Owner acceptance is required next. After Owner acceptance, SLICE-0034 may be treated DONE and cleaned up with the normal finish workflow. No next slice is auto-started.
