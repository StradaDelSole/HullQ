# SLICE-0029 — Primary-Source BoatDesign Applicability & Conditional-Clearance Pilot

**Status:** measured research result, not a canonical promotion. Creates zero canonical BoatDesign/DesignOption/NamedVariant/FieldResolution/technical-value rows.

## Scope

Fixed pilot identity boundary (reproduced in `pilot_identity_boundary.json`, unchanged from the accepted 1,770/1,772 SLICE-0017+0018/0028 boundary):

```text
Q5051252  Catalina 22  -> BM_WDT0_6c94b5bc9e79402bb07309289905913e
Q5051253  Catalina 30  -> BM_WDT0_3fdd058699d145c6a1b044fc90b65201
```

External research: 11 of the permitted 25 bounded, human-directed retrievals against official `catalinayachts.com` surfaces (`source_retrieval_log.json`) — robots.txt, the site's own WordPress page sitemap (used only to check for a terms/privacy page), the homepage footer, two official brochure-archive index pages, four scanned model brochure PDFs (Catalina 30 "MKI"-labelled and plain; Catalina 22 Sport; Catalina Capri 22), and the official dated company-history page. No PDF/HTML/image file was vendored into the repository; only discrete facts, citations and non-vendored SHA-256 fingerprints were retained.

## Source-rights result

`source_clearance_assessment.json` evaluates all six SR-6.6 conditions for the bounded manual use actually performed. All are positively satisfied (the sixth, "no automated extraction unless separately cleared," is satisfied for the human-directed bounded method used here specifically, and does **not** clear production automated ingestion). No Terms of Use, Privacy Policy or licence page exists anywhere in Catalina Yachts' own declared page sitemap; robots.txt disallows only `/wp-admin/`.

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

`identity_seed` and `production_value` are positively cleared under SR-6.6 for **bounded manually curated discrete factual use only**. `bulk_bootstrap`, `automated_ingestion` and `artifact_redistribution` remain unchanged, non-allow, fail-closed — this result must not be generalized into automated/bulk Catalina ingestion.

## BoatDesign applicability findings

Full findings, citations and cautions: `boatdesign_applicability.json`.

**Catalina 22 (Q5051252):** the official history page positively evidences a dated manufacturer redesign — *"January 1995 — The Catalina 22 markII is introduced with re-designed and enlarged deck and new interior."* — and a later variant, *"June 2004 — The Catalina 22 Sport is introduced to better accommodate one-design racing,"* whose own brochure states it was built to match the *original* (pre-1995) dimensions and weight. No markII-specific numeric specification was located in this bounded pass, so the retained SLICE-0028 BoatModel-scoped Wikidata value cannot be safely pinned to a specific generation. `generation_boundary_established_for_this_pilot = false`. "Catalina Capri 22" was confirmed (distinct hull-number series, materially different dimensions, separate current-model page) to be a related but distinct commercial product and is excluded from these findings.

**Catalina 30 (Q5051253):** two independently retrieved official specification documents — one archive-labelled "MKI," one plain and undated — differ in keel (fin/wing), rudder (skeg + spade vs. unspecified), transom (optional walk-through vs. none) and interior layout (traditional/dinette choice), all DesignOption-axis differences under `IDENTITY_MODEL.v0.2.md` 2.5, yet report **identical** LOA (29'11"), LWL (25'0"), beam (10'10") and standard displacement/lead. No Catalina-30 generation label appears anywhere in the official dated history timeline. `generation_boundary_established_for_this_pilot = true`: the evidence supports one stable, cross-validated hull-baseline BoatDesign spanning the documented production span, with keel/rudder/transom/layout varying as concurrent factory options.

## Field-level applicability (five fixed Tier-1 fields x two BoatModels)

Full classifications and rationale: `wikidata_candidate_applicability.json`.

| Field | Catalina 22 | Catalina 30 |
|---|---|---|
| loa_m | GENERATION_AMBIGUOUS | **SAFE_FOR_LATER_DESIGN_PROMOTION** |
| lwl_m | GENERATION_AMBIGUOUS | **SAFE_FOR_LATER_DESIGN_PROMOTION** |
| beam_m | GENERATION_AMBIGUOUS | **SAFE_FOR_LATER_DESIGN_PROMOTION** |
| draft_min_m | OPTION_SENSITIVE | NO_NORMALIZED_WIKIDATA_CANDIDATE |
| displacement_kg | NO_NORMALIZED_WIKIDATA_CANDIDATE | NO_NORMALIZED_WIKIDATA_CANDIDATE |

Counts: **3 of 5** Catalina 30 fields SAFE_FOR_LATER_DESIGN_PROMOTION; **0 of 5** Catalina 22 fields safe (2 GENERATION_AMBIGUOUS, 1 OPTION_SENSITIVE, 2 NO_NORMALIZED_WIKIDATA_CANDIDATE, with one field pointer, Catalina 30 `draft_min_m`, additionally having no SLICE-0028 evidence entry at all for that QID).

Per the slice's explicit rule, exact numeric equality between a Wikidata candidate and a Catalina figure is treated as diagnostic evidence only, never as sole proof of design-generation applicability — this is why Catalina 22's near-exact matches are still classified GENERATION_AMBIGUOUS (a confirmed but numerically un-evidenced 1995 redesign exists), while Catalina 30's matches are classified safe only because they are independently cross-validated across two option-differing documents *and* paired with a positively evidenced single-generation applicability boundary.

## Deterministic next-step recommendation

```text
READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT
```

Recomputed by `compute_recommendation()`: rights are cleared for `identity_seed` and `production_value`; Catalina 30 (Q5051253) has a positively evidenced generation/applicability boundary; at least one of its five Tier-1 fields (in fact three: `loa_m`, `lwl_m`, `beam_m`) is classified `SAFE_FOR_LATER_DESIGN_PROMOTION`; no unresolved rights/applicability condition contradicts those three fields.

This recommendation names **Catalina 30's `loa_m`/`lwl_m`/`beam_m` only** as the evidence-backed scope for a later, separately readied canonical promotion slice. It does **not** itself create a BoatDesign, DesignOption, FieldResolution or canonical value, and it does **not** extend to Catalina 22, to Catalina 30's `draft_min_m`/`displacement_kg`, or to any automated/bulk/redistribution use.

## Canonical mutation

Zero canonical BoatModel/BoatDesign/DesignOption/NamedVariant/FieldResolution rows or technical values were created or modified. The accepted 1,770 canonical BoatModel / 1,772 historical crosswalk boundary is unchanged.

## Offline reproduction

```bash
uv run python scripts/bootstrap/wikidata_sl0029_boatdesign_applicability_pilot_runner.py --verify
```

Requires no live Catalina or Wikidata access; reproduces the pilot identity boundary from the retained SLICE-0028 linkage and `overlap_result.json`, recomputes the source-use gate decisions and SR-6.6 boolean, cross-checks every field-applicability entry against the reused SLICE-0028 evidence bundle, recomputes the recommendation, and verifies the retained-package artifact digests.
