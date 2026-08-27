# SLICE-0029 — Primary-Source BoatDesign Applicability & Conditional-Clearance Pilot

**Status:** measured research result, not a canonical promotion. Creates zero canonical BoatDesign/DesignOption/NamedVariant/FieldResolution/technical-value rows.

**Amendment history:**

1. Independent review of head `9227fe9199d9451f56470fe326254c2ef04dff94` found two blocking issues. Amendment 1 (head `cd0b2a72d527d4dd5badc08af8c5880acb03a83b`) closed the SR-6.6 fail-closed-coupling blocker (see below, unchanged since) but left the Catalina 30 applicability finding still overclaimed: it retained `first_year: 1974` / `last_year: null` / `unknown_or_unbounded: false` and three `SAFE_FOR_LATER_DESIGN_PROMOTION` fields, reinterpreting "one known bound" as "genuinely bounded" — a misreading of `OBSERVATION_APPLICABILITY_SCHEMA.v0.1` that this amendment corrects.
2. This amendment (current head) corrects that reinterpretation. `validate_applicability_scope_invariant` now requires BOTH `first_year` and `last_year` positively known before `unknown_or_unbounded` may read `false`. A bounded positive-path search of the two remaining official brochure-listing surfaces (retrievals 12–13) found no additional Catalina 30 document and no further dating evidence. Per the slice's explicit negative-path allowance, Catalina 30's `generation_boundary_established_for_this_pilot` and its three previously-SAFE fields are downgraded to reflect the actual evidence, and the deterministic recommendation changes from `READY_FOR_BOUNDED_CANONICAL_BOATDESIGN_PILOT` to `APPLICABILITY_EVIDENCE_INSUFFICIENT`. The `rudder` DesignOption-axis claim (inferred from one document mentioning a rudder configuration and the other not mentioning it) is removed; non-mention is not positive evidence of a concurrent factory option. See `git log` on this package for the exact per-amendment diffs.

## Source-rights result (unchanged since amendment 1 — SR-6.6 blocker remains closed)

`source_clearance_assessment.json` evaluates all six SR-6.6 conditions for the bounded manual use actually performed. All are positively satisfied (the sixth, "no automated extraction unless separately cleared," is satisfied for the human-directed bounded method used here specifically, and does **not** clear production automated ingestion). No Terms of Use, Privacy Policy or licence page exists anywhere in Catalina Yachts' own declared page sitemap; robots.txt disallows only `/wp-admin/`.

The `identity_seed`/`production_value` clearance is **not independently asserted**: `derive_sr_6_6_use_clearance` mechanically computes it from `sr_6_6_condition_evaluation.conditions_satisfied_for_bounded_manual_use` (satisfied → `allowed`; anything else → the SR-6.6 policy default `conditional`), and `verify_source_clearance_assessment_self_consistency` recomputes and compares this on every run — an unsatisfied/tampered condition set can never coexist with a retained `allowed` clearance. The clearance is additionally scoped by a structured `bounded_scope` block (exact QIDs/hullq_ids/field pointers/use kinds, mechanically checked against `pilot_identity_boundary.json`), and the broader SOURCE_SCHEMA permissions that would authorize unscoped reuse (`commercial_use`, `store_canonical_values`, `publish_derived_database`) are mechanically required to stay non-`allowed` (`validate_permissions_bounded`) so the scoped clearance can never be read as a blanket grant.

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

## External research

13 of the permitted 25 bounded, human-directed retrievals against official `catalinayachts.com` surfaces (`source_retrieval_log.json`): robots.txt, the site's own WordPress page sitemap, the homepage footer, two official brochure-archive index pages, four scanned model brochure PDFs (Catalina 30 "MKI"-labelled and plain; Catalina 22 Sport; Catalina Capri 22), the official dated company-history page, and — added in this amendment as a positive-path check for further Catalina 30 dating evidence — the two remaining official brochure-listing pages (`brochure-downloads/`, `catalina-yachts-brochure-download/`), both of which turned out to be lead-generation forms with zero brochure PDF links. No PDF/HTML/image file was vendored into the repository; only discrete facts, citations and non-vendored SHA-256 fingerprints were retained.

## BoatDesign applicability findings

Full findings, citations and cautions: `boatdesign_applicability.json`.

**Catalina 22 (Q5051252):** unchanged. The official history page positively evidences a dated manufacturer redesign — *"January 1995 — The Catalina 22 markII is introduced with re-designed and enlarged deck and new interior."* — and a later variant, *"June 2004 — The Catalina 22 Sport is introduced to better accommodate one-design racing,"* whose own brochure states it was built to match the *original* (pre-1995) dimensions and weight. No markII-specific numeric specification was located in this bounded pass, so the retained SLICE-0028 BoatModel-scoped Wikidata value cannot be safely pinned to a specific generation. `generation_boundary_established_for_this_pilot = false`; `applicability_scope.unknown_or_unbounded = true`. "Catalina Capri 22" was confirmed (distinct hull-number series, materially different dimensions, separate current-model page) to be a related but distinct commercial product and is excluded from these findings.

**Catalina 30 (Q5051253) — downgraded in this amendment:** two independently retrieved official specification documents — one archive-labelled "MKI" (page-4 print-run date code `9 90`, read as September 1990), one plain document with **no confirmed date** (its 1970s-era styling is circumstantial only, not proof of any date) — report **identical** LOA (29'11"), LWL (25'0"), beam (10'10") and standard displacement/lead, but per the controlling slice this equality is diagnostic corroboration only, never proof of BoatDesign-generation applicability. `generation_boundary_established_for_this_pilot = false` (previously, incorrectly, `true`): the archive's "MKI" label is uncorroborated by any dated history entry; no `IDENTITY_MODEL.v0.2.md` §2.4 BoatDesign-split trigger was found, but that absence is not proof of one stable generation either; and December 1974 (the official BoatModel introduction date) is an identity fact, not positive evidence that the technical figures in the undated plain brochure applied from that year — the only positively dated technical document is the single 1990-09 MKI data point. `applicability_scope.unknown_or_unbounded = true`; `first_year` and `last_year` are both null. Positive-path retrievals 12–13 (this amendment) found no additional Catalina 30 document or dating evidence.

DesignOption-axis findings for Catalina 30, using positive within-single-document evidence only: `keel` (MKI brochure: "Wing and fin keels are available"), `draft` (both documents each independently list std + shoal draft; the two documents' shoal-draft figures disagree by 6 inches — an open `SOURCE_VALUE_CONFLICT`-class discrepancy), `other`/transom (MKI brochure: "Available walk through transom is not shown" — an option described entirely within that one document), `layout` (plain brochure: "TRADITIONAL MODEL SHOWN — ALSO AVAILABLE WITH DINETTE" — evidenced entirely within that one document). The prior amendment's `rudder` axis claim is removed: it rested on one document describing a skeg-hung spade rudder and the other simply not mentioning rudder configuration at all — non-mention is not positive evidence of a concurrent factory option, so this is now retained only as a `non_option_descriptive_differences` note.

## Field-level applicability (five fixed Tier-1 fields x two BoatModels)

Full classifications, rationale and structured `applicability_scope` (`OBSERVATION_APPLICABILITY_SCHEMA.v0.1` shape): `wikidata_candidate_applicability.json`.

| Field | Catalina 22 | Catalina 30 |
|---|---|---|
| loa_m | GENERATION_AMBIGUOUS | **INSUFFICIENT_EVIDENCE** (was SAFE_FOR_LATER_DESIGN_PROMOTION prior to this amendment) |
| lwl_m | GENERATION_AMBIGUOUS | **INSUFFICIENT_EVIDENCE** (was SAFE_FOR_LATER_DESIGN_PROMOTION prior to this amendment) |
| beam_m | GENERATION_AMBIGUOUS | **INSUFFICIENT_EVIDENCE** (was SAFE_FOR_LATER_DESIGN_PROMOTION prior to this amendment) |
| draft_min_m | OPTION_SENSITIVE | NO_NORMALIZED_WIKIDATA_CANDIDATE |
| displacement_kg | NO_NORMALIZED_WIKIDATA_CANDIDATE | NO_NORMALIZED_WIKIDATA_CANDIDATE |

Counts: **0 of 5** fields SAFE_FOR_LATER_DESIGN_PROMOTION for either BoatModel (Catalina 22: 2 GENERATION_AMBIGUOUS, 1 OPTION_SENSITIVE, 2 NO_NORMALIZED_WIKIDATA_CANDIDATE; Catalina 30: 3 INSUFFICIENT_EVIDENCE, 2 NO_NORMALIZED_WIKIDATA_CANDIDATE, with `draft_min_m` additionally having no SLICE-0028 evidence entry at all for that QID).

Per the slice's explicit rule, exact numeric equality between a Wikidata candidate and a Catalina figure is treated as diagnostic evidence only, never as sole proof of design-generation applicability. `validate_applicability_scope_invariant` now requires a production-year scope to have BOTH `first_year` and `last_year` positively known before `unknown_or_unbounded` may read `false`; a half-open range (one bound known, the other genuinely unknown) is still an unknown/unbounded scope and can never itself become "safe for promotion." `validate_wikidata_candidate_applicability` and `compute_recommendation` both mechanically refuse `SAFE_FOR_LATER_DESIGN_PROMOTION` unless that fully-bounded invariant holds. The retained SLICE-0028 Wikidata evidence remains QID/BoatModel-scoped throughout and was never retargeted onto any BoatDesign subject.

## Deterministic next-step recommendation

```text
APPLICABILITY_EVIDENCE_INSUFFICIENT
```

Recomputed by `compute_recommendation()`: rights are cleared for `identity_seed` and `production_value` (mechanically derived from the SR-6.6 conditions), but neither Catalina 22 nor Catalina 30 has a positively evidenced, genuinely bounded BoatDesign-generation/applicability boundary in this bounded pass, and no field for either BoatModel carries both a `SAFE_FOR_LATER_DESIGN_PROMOTION` outcome and a genuinely bounded `applicability_scope`. This is the slice's explicitly acceptable negative-path outcome: the bounded official-source pass could not establish sufficient positive evidence to safely scope any retained SLICE-0028 technical candidate to a BoatDesign generation/configuration. It is not a failure of the slice; it is the correctly measured result.

## Canonical mutation

Zero canonical BoatModel/BoatDesign/DesignOption/NamedVariant/FieldResolution rows or technical values were created or modified. The accepted 1,770 canonical BoatModel / 1,772 historical crosswalk boundary is unchanged.

## Offline reproduction

```bash
uv run python scripts/bootstrap/wikidata_sl0029_boatdesign_applicability_pilot_runner.py --verify
```

Requires no live Catalina or Wikidata access; reproduces the pilot identity boundary from the retained SLICE-0028 linkage and `overlap_result.json`; mechanically re-derives the SR-6.6 clearance from the retained conditions and cross-checks the bounded-scope/permissions reconciliation; recomputes the source-use gate decisions; cross-checks every field-applicability entry against the reused SLICE-0028 evidence bundle; validates every `applicability_scope` against `specs/OBSERVATION_APPLICABILITY_SCHEMA.v0.1.json` and its (corrected, both-bounds-required) no-absence-as-proof invariant; recomputes the recommendation; and verifies the retained-package artifact digests. The retained package is 13 files (5 JSON documents, 5 matching JSON Schemas, `REPORT.md`, `ARTIFACT-DIGESTS.json`, and its own `artifact_digests_schema.json`).

## Unresolved findings

- Catalina 30's draft figures disagree between the two retained documents: shoal draft **3'10" vs 4'4"** (a 6-inch discrepancy), retained as an open `SOURCE_VALUE_CONFLICT`-class disagreement, not resolved by this pilot.
- Catalina 30's true production span remains only partially evidenced: introduction December 1974 and hull #5,000 October 1987 are established; the technical-value dating anchor (the MKI brochure) is 1990-09; `last_built` and the technical values' true first/last applicable years remain unevidenced.
- Whether the "MKI" archive label corresponds to a real second Catalina 30 generation remains genuinely open; this bounded pass found neither confirming nor disconfirming evidence.
