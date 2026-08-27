# SLICE-0029 — Primary-Source BoatDesign Applicability & Conditional-Clearance Pilot

**Status:** measured research result, not a canonical promotion. Creates zero canonical BoatDesign/DesignOption/NamedVariant/FieldResolution/technical-value rows.

**Amendment note:** independent review of head `9227fe9199d9451f56470fe326254c2ef04dff94` found two blocking issues, both fixed on this head: (1) the positive `identity_seed`/`production_value` clearance was not mechanically tied to the retained SR-6.6 condition evaluation, so a tampered/unsatisfied condition set could coexist with an `allowed` clearance and an unaffected `READY` recommendation — fixed by deriving the clearance directly from the conditions (`derive_sr_6_6_use_clearance`) and adding a structured, mechanically validated `bounded_scope` plus a permissions-reconciliation check (`validate_permissions_bounded`), all enforced inside `verify_source_clearance_assessment_self_consistency`; (2) Catalina 30's `generation_boundary_established_for_this_pilot = true` and its three `SAFE_FOR_LATER_DESIGN_PROMOTION` field classifications overclaimed an all-production-span boundary from an uncorroborated archive label and two undated-feeling documents — re-examined under `OBSERVATION_APPLICABILITY_SCHEMA.v0.1`, recovering a positively dated (`1990-09`, print-run code) primary-source document, and narrowing the finding to an explicitly bounded `applicability_scope` (`first_year: 1974`, `last_year: null` — genuinely bounded, not all-production), mechanically required for any `SAFE` outcome. The deterministic recommendation and its Catalina 30-only scope are unchanged in substance, but are now correctly narrower and mechanically enforced rather than asserted. See `git log` on this package for the exact prior/amended diff.

## Scope

Fixed pilot identity boundary (reproduced in `pilot_identity_boundary.json`, unchanged from the accepted 1,770/1,772 SLICE-0017+0018/0028 boundary):

```text
Q5051252  Catalina 22  -> BM_WDT0_6c94b5bc9e79402bb07309289905913e
Q5051253  Catalina 30  -> BM_WDT0_3fdd058699d145c6a1b044fc90b65201
```

External research: 11 of the permitted 25 bounded, human-directed retrievals against official `catalinayachts.com` surfaces (`source_retrieval_log.json`) — robots.txt, the site's own WordPress page sitemap (used only to check for a terms/privacy page), the homepage footer, two official brochure-archive index pages, four scanned model brochure PDFs (Catalina 30 "MKI"-labelled and plain; Catalina 22 Sport; Catalina Capri 22), and the official dated company-history page. No PDF/HTML/image file was vendored into the repository; only discrete facts, citations and non-vendored SHA-256 fingerprints were retained.

## Source-rights result

`source_clearance_assessment.json` evaluates all six SR-6.6 conditions for the bounded manual use actually performed. All are positively satisfied (the sixth, "no automated extraction unless separately cleared," is satisfied for the human-directed bounded method used here specifically, and does **not** clear production automated ingestion). No Terms of Use, Privacy Policy or licence page exists anywhere in Catalina Yachts' own declared page sitemap; robots.txt disallows only `/wp-admin/`.

The `identity_seed`/`production_value` clearance is **not independently asserted**: `hullq.bootstrap.wikidata_sl0029_boatdesign_applicability_pilot.derive_sr_6_6_use_clearance` mechanically computes it from `sr_6_6_condition_evaluation.conditions_satisfied_for_bounded_manual_use` (satisfied → `allowed`; anything else → the SR-6.6 policy default `conditional`), and `verify_source_clearance_assessment_self_consistency` recomputes and compares this on every run — an unsatisfied/tampered condition set can never coexist with a retained `allowed` clearance. The clearance is additionally scoped by a structured `bounded_scope` block (exact QIDs/hullq_ids/field pointers/use kinds, mechanically checked against `pilot_identity_boundary.json`), and the broader SOURCE_SCHEMA permissions that would authorize unscoped reuse (`commercial_use`, `store_canonical_values`, `publish_derived_database`) are mechanically required to stay non-`allowed` (`validate_permissions_bounded`) so the scoped clearance can never be read as a blanket grant.

Recomputing the retained Source record through the unmodified `hullq.sources.rights.check_source_use` gate for all seven use keys yields:

| Use | Outcome |
|---|---|
| research_reference | allowed |
| research_lead | allowed |
| **identity_seed** | **allowed** |
| **production_value** | **allowed** |
| bulk_bootstrap | legal_review_required |
| automated_ingestion | unknown_unassessed |
| artifact_redistribution | legal_review_required |

`identity_seed` and `production_value` are positively cleared under SR-6.6 for **bounded manually curated discrete factual use only**, scoped exactly to the two fixed pilot BoatModels and five field pointers. `bulk_bootstrap`, `automated_ingestion` and `artifact_redistribution` remain unchanged, non-allow, fail-closed — this result must not be generalized into automated/bulk Catalina ingestion.

## BoatDesign applicability findings

Full findings, citations and cautions: `boatdesign_applicability.json`.

**Catalina 22 (Q5051252):** the official history page positively evidences a dated manufacturer redesign — *"January 1995 — The Catalina 22 markII is introduced with re-designed and enlarged deck and new interior."* — and a later variant, *"June 2004 — The Catalina 22 Sport is introduced to better accommodate one-design racing,"* whose own brochure states it was built to match the *original* (pre-1995) dimensions and weight. No markII-specific numeric specification was located in this bounded pass, so the retained SLICE-0028 BoatModel-scoped Wikidata value cannot be safely pinned to a specific generation. `generation_boundary_established_for_this_pilot = false`. "Catalina Capri 22" was confirmed (distinct hull-number series, materially different dimensions, separate current-model page) to be a related but distinct commercial product and is excluded from these findings.

**Catalina 30 (Q5051253):** two independently retrieved official specification documents — one archive-labelled "MKI" (page-4 print-run date code `9 90`, read as September 1990), one plain document with no confirmed date (circumstantial 1970s-era stylistic signals only) — differ in keel (fin/wing), rudder (skeg + spade vs. unspecified), transom (optional walk-through vs. none) and interior layout (traditional/dinette choice), all DesignOption-axis differences under `IDENTITY_MODEL.v0.2.md` 2.5, yet report **identical** LOA (29'11"), LWL (25'0"), beam (10'10") and standard displacement/lead. No Catalina-30 generation label appears anywhere in the official dated history timeline, in contrast to four sibling models (Catalina 22, 28, 34, 36) for which the same timeline explicitly logs a dated Mark II redesign — treated as weak supporting context, not proof. `generation_boundary_established_for_this_pilot = true`, but the finding is deliberately **narrow, not all-production**: `applicability_scope` states `first_year: 1974` (official introduction), `last_year: null` (explicitly unknown upper bound — this bounded pass did not verify the dimensions held for the remainder of production), `unknown_or_unbounded: false`.

## Field-level applicability (five fixed Tier-1 fields x two BoatModels)

Full classifications, rationale and structured `applicability_scope` (`OBSERVATION_APPLICABILITY_SCHEMA.v0.1` shape): `wikidata_candidate_applicability.json`.

| Field | Catalina 22 | Catalina 30 |
|---|---|---|
| loa_m | GENERATION_AMBIGUOUS | **SAFE_FOR_LATER_DESIGN_PROMOTION** (production_year >= 1974, upper bound unknown) |
| lwl_m | GENERATION_AMBIGUOUS | **SAFE_FOR_LATER_DESIGN_PROMOTION** (production_year >= 1974, upper bound unknown) |
| beam_m | GENERATION_AMBIGUOUS | **SAFE_FOR_LATER_DESIGN_PROMOTION** (production_year >= 1974, upper bound unknown) |
| draft_min_m | OPTION_SENSITIVE | NO_NORMALIZED_WIKIDATA_CANDIDATE |
| displacement_kg | NO_NORMALIZED_WIKIDATA_CANDIDATE | NO_NORMALIZED_WIKIDATA_CANDIDATE |

Counts: **3 of 5** Catalina 30 fields SAFE_FOR_LATER_DESIGN_PROMOTION (each carrying a genuinely bounded, not all-production, `applicability_scope`); **0 of 5** Catalina 22 fields safe (2 GENERATION_AMBIGUOUS, 1 OPTION_SENSITIVE, 2 NO_NORMALIZED_WIKIDATA_CANDIDATE, with one field pointer, Catalina 30 `draft_min_m`, additionally having no SLICE-0028 evidence entry at all for that QID).

Per the slice's explicit rule, exact numeric equality between a Wikidata candidate and a Catalina figure is treated as diagnostic evidence only, never as sole proof of design-generation applicability — this is why Catalina 22's near-exact matches are still classified GENERATION_AMBIGUOUS (a confirmed but numerically un-evidenced 1995 redesign exists), while Catalina 30's matches are classified safe only because they are independently cross-validated across two option-differing, one positively dated (1990-09), documents, paired with a positively evidenced (if narrowly bounded) applicability scope. `validate_wikidata_candidate_applicability` and `compute_recommendation` both mechanically refuse `SAFE_FOR_LATER_DESIGN_PROMOTION` unless `applicability_scope.unknown_or_unbounded == false` — an unknown/unbounded scope can never itself become "safe." The retained SLICE-0028 Wikidata evidence remains QID/BoatModel-scoped throughout and is treated as corroborating, not defining, this bounded scope; a later canonical promotion slice must create its own BoatDesign-scoped FieldEvidence/FieldResolution, not retarget the QID-scoped evidence_id.

## Deterministic next-step recommendation

```text
READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
```

Recomputed by `compute_recommendation()`: rights are cleared for `identity_seed` and `production_value` (mechanically derived from the SR-6.6 conditions, not independently asserted); Catalina 30 (Q5051253) has a positively evidenced, narrowly bounded generation/applicability boundary; at least one of its five Tier-1 fields (in fact three: `loa_m`, `lwl_m`, `beam_m`) is classified `SAFE_FOR_LATER_DESIGN_PROMOTION` with a genuinely bounded `applicability_scope`; no unresolved rights/applicability condition contradicts those three fields.

This recommendation names **Catalina 30's `loa_m`/`lwl_m`/`beam_m` only**, bounded to `production_year >= 1974` with an explicitly unknown upper bound, as the evidence-backed scope for a later, separately readied canonical promotion slice. It does **not** itself create a BoatDesign, DesignOption, FieldResolution or canonical value; it does **not** extend to Catalina 22, to Catalina 30's `draft_min_m`/`displacement_kg`, to any production year outside the stated bound, or to any automated/bulk/redistribution use.

## Canonical mutation

Zero canonical BoatModel/BoatDesign/DesignOption/NamedVariant/FieldResolution rows or technical values were created or modified. The accepted 1,770 canonical BoatModel / 1,772 historical crosswalk boundary is unchanged.

## Offline reproduction

```bash
uv run python scripts/bootstrap/wikidata_sl0029_boatdesign_applicability_pilot_runner.py --verify
```

Requires no live Catalina or Wikidata access; reproduces the pilot identity boundary from the retained SLICE-0028 linkage and `overlap_result.json`; mechanically re-derives the SR-6.6 clearance from the retained conditions and cross-checks the bounded-scope/permissions reconciliation; recomputes the source-use gate decisions; cross-checks every field-applicability entry against the reused SLICE-0028 evidence bundle; validates every `applicability_scope` against `specs/OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json` and its no-absence-as-proof invariant; recomputes the recommendation; and verifies the retained-package artifact digests. The retained package is 13 files (5 JSON documents, 5 matching JSON Schemas, `REPORT.md`, `ARTIFACT-DIGESTS.json`, and its own `artifact_digests_schema.json`).
