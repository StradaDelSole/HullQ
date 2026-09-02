# SLICE-0039 — Seed Corpus Wave 1 real multi-design search research record

**Status:** implementation research record. Feeds `scripts/search_seed_corpus_wave1.py`
and the three new retained projections in this directory. Not canonical
BoatDesign admission; not the twelve-design `SEARCH_BENCHMARK.v0.1.md`
corpus; not a general ingestion adapter for any of the three manufacturers/
class associations involved.

**REVIEW amendment (this revision):** independent review found that the
original submission's Lagoon 42 `configuration_space_complete=True` was not
supported by sufficient authoritative evidence (see §5). Research was
extended within the remaining per-design cap; no sufficient evidence was
found, so the flag is corrected to `False`. This removes Lagoon's Q1/Q2
`CONFIRMED_NON_MATCH` results, which were the only thing keeping Q1 and Q2
at the required 3/4 evaluability gate. **Q1 and Q2 now evaluate at 2/4,
below the minimum utility gate; SLICE-0039 is therefore reported `BLOCKED`**
per the slice's explicit stop condition, not silently patched by
manufacturing another route to `CONFIRMED_NON_MATCH`. See §5 and §6 for the
corrected evidence and result distribution, and the slice document for the
formal `BLOCKED` report. A separate typo in §3 (Bavaria's standard-draught
value) is also corrected in this revision.

This wave converts the accepted Wave-1 benchmark cohort (Bavaria Cruiser 34,
Contessa 32, BENETEAU Oceanis 30.1, Lagoon 42) into a real, non-fixture,
multi-design Search cohort for exactly Q1, Q2 and Q10. The BENETEAU Oceanis
30.1 projection is the unchanged SLICE-0037 pilot; see
`research/benchmark/waves/sl0037-oceanis-30-1/REPORT.md` for its full
research basis. This report covers only the three new designs.

## 1. Cohort and scope

Locked cohort (unchanged from `specs/SEARCH_BENCHMARK.v0.1.md` §7 Wave 1):

1. Bavaria Cruiser 34
2. Contessa 32
3. BENETEAU Oceanis 30.1 (reused unchanged from SLICE-0037)
4. Lagoon 42

Locked queries (unchanged shapes from
`fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json`):
Q1 (`LOA 8–11 m AND Draft ≤ 1.80 m`), Q2 (`LOA 9–12 m AND Beam ≤ 3.60 m AND
Draft ≤ 2.00 m`), Q10 (`Draft ≤ 1.60 m`). Q3–Q9 are explicitly out of scope.

## 2. Research cap accounting

Hard cap: 12 distinct external technical-evidence surfaces total, 5 per
design (excluding source-rights/legal-policy pages assessed solely for
access/reuse). Actual usage (`source_retrieval_log.json`
`external_evidence_surface_count`):

| Design | Surfaces used | Cap |
|---|---|---|
| Bavaria Cruiser 34 | 1 (BAV-1) | 5 |
| Contessa 32 | 5 (CON-1..CON-5) | 5 |
| Lagoon 42 | 3 (LAG-1..LAG-3) | 5 |
| **Total** | **9** | **12** |

Neither the 12-total nor the 5-per-design cap was exceeded. Contessa 32
reached its per-design cap without establishing LOA/beam/draft (see §4).
Lagoon 42's count reflects the REVIEW-amendment research extension (LAG-2,
LAG-3) undertaken specifically to seek configuration-space-completeness
evidence; see §5.
Legal/terms pages checked to assess source-rights disposition
(bavariayachts.com Imprint, jeremyrogers.co.uk Privacy Policy,
catamarans-lagoon.com Terms of Use, and BENETEAU's already-reviewed
Legal Notices reused by reference for the Oceanis pilot) are excluded from
this count per the slice's explicit carve-out.

## 3. Bavaria Cruiser 34 — real, two-configuration draft-sensitive design

**Source:** BAV-1, `https://www.bavariayachts.com/sailing-yachts/cruiser-34/data-and-options/`
(official current manufacturer product page; `robots.txt` allows the fetched
path; retrieved by raw HTTP GET + HTML tag-stripping, read directly, not
AI-summarized). Rights disposition: `unlicensed_factual_reference`,
`automated_access: conditional` (bounded, non-recurring, discrete-fact-only,
same disposition class as the Oceanis 30.1 pilot's beneteau.com sources).

**Design-wide facts** (identical across both configurations, from BAV-1's
"Technical data" table): `loa_m = 9.99` ("Length over all"; the separate
"Length over all (incl. bowsprit) 10.67 m" row is not used — see the
projection's scope note), `beam_m = 3.42` ("Beam of hull").

**Two named factory draught rows**, positively evidenced by the same table
(labelled "Draught standard" and "Draught option", each paired with its own
ballast/displacement figure on the source page):

- **Standard draught** — `draft_max_m = 2.04` m.
- **Shoal draught option** — `draft_max_m = 1.58` m.

BAV-1 separately captions a VPP (velocity prediction program) performance
chart with "deep keel 2.02 m" — a marketing-prose figure that disagrees
slightly with the structured table's "Draught standard 2.04 m". This
discrepancy is recorded for audit but is **not used**: the structured
spec-table figure is preferred as the more literal, direct statement (same
preference the Oceanis 30.1 pilot applied to structured vs. marketing-prose
figures), and the discrepancy does not cross any Q1/Q2/Q10 threshold either
way (both 2.02 m and 2.04 m exceed all three draft limits identically).

`configuration_space_complete = False`: BAV-1 names exactly two draught
rows but does not state this exhausts the factory-relevant configuration
space, so completeness is not inferred merely from the number of discovered
options — the same discipline the Oceanis 30.1 pilot applied to its three
named ballast options.

**Q1/Q2/Q10 outcome:** `CONFIRMED_MATCH` on all three, via the shoal-draught
configuration (`1.58 m` clears every draft threshold; `9.99 m` LOA and
`3.42 m` beam clear every range/maximum). The standard-draught configuration
is a confirmed `FALSE` on all three (`2.04 m` exceeds `1.80`, `2.00` and
`1.60` alike).

## 4. Contessa 32 — genuine, honestly-reported evidence gap

Five surfaces were inspected within the per-design cap:

- **CON-1** — `jeremyrogers.co.uk/contessa32-specification/`, the current
  builder's own "New Build Contessa 32 Specification, 2023" page. Documents
  construction, equipment, certification (RINA RCD 2 Category A) and total
  displacement (9300 lb / 4218.48 kg) in detail, and confirms the rudder is
  skeg-supported ("stainless steel lower attachment plate at the base of the
  skeg" — a real direct fact, not needed by Q1/Q2/Q10 and not projected).
  **No LOA, beam or draft figure appears anywhere on the page**, confirmed
  independently by both a raw-text extraction and a follow-up WebFetch
  AI-summarized re-check specifically for any dimension in an image/diagram/
  caption.
- **CON-2** — `jeremyrogers.co.uk/all-about-contessa/`, the builder's own
  history page (David Sadler, 1970; moulds bought back in 1996). Identity
  evidence only; no dimensions.
- **CON-3** — `jeremyrogers.co.uk/contessa-32-new-build/`, a marketing
  landing page. No new facts.
- **CON-4** — `co32.org` (Contessa 32 Class Association homepage). Confirms
  the class is actively administered; no dimensions.
- **CON-5** — the Contessa 32 Class Racing Rules (v3.3, 15 March 2015),
  retrieved via an Internet Archive Wayback Machine mirror after the live
  `co32.org` document path returned HTTP 406 under every request pattern
  tried (a genuine, honest access-limitation finding for that specific path,
  not routed around — the same publicly-issued document was instead read
  from a third-party public archive). Part 2 (Yacht Specification) confirms
  every class-legal hull is "standard mouldings from the original J C Rogers
  moulds" — corroborating a single one-design hull configuration — and Parts
  2–3 specify mast/boom/sail/rigging measurement limits in detail. **No hull
  LOA/beam/draft figure appears anywhere in the 11-page document.**

Third-party reference/encyclopedia/aggregator sources (Wikipedia,
goodoldboat.com, sailboat.guide, canadianboating.ca, pbo.co.uk) do state a
commonly-repeated LOA/beam/draft figure for this design (32′0″ / 9′6″ / 5′6″).
Per this slice's source discipline (`SLICE-0039` "Source and research
discipline" item 3), a reference database or encyclopedia may identify a
research lead but may not self-authorize a Search technical fact; none of
these figures is used here. Wikipedia was fetched once (not counted against
the per-design surface cap, treated as pure lead-navigation exactly like the
Oceanis 30.1 pilot's non-evidentiary web-search convention) solely to
identify the Contessa 32 Class Association as a candidate authoritative
source; its own figures are not relied upon anywhere in this package.

**Resolution:** `loa_m`, `beam_m` and `draft_max_m` are left `MISSING`
design-wide. This design's one baseline configuration
(`contessa-32-baseline`) therefore evaluates `UNKNOWN` on every Q1/Q2/Q10
criterion, and the design-level result is `INSUFFICIENT_DATA` (reason
`CONFIGURATION_AMBIGUOUS`, since `configuration_space_complete = False`)
for all three queries. This is a real, bounded, honestly-reported evidence
gap, not a guessed value and not a cohort substitution (`SEARCH_BENCHMARK.v0.1.md`
§4 forbids replacing a locked corpus member merely because research becomes
difficult or sparse).

## 5. Lagoon 42 — real single-configuration design; configuration-space completeness NOT established

**Sources:**

- **LAG-1** — `https://www.catamarans-lagoon.com/boats/lagoon-42` (official
  current manufacturer product page; `robots.txt` is a blanket `Allow: /`;
  retrieved by raw HTTP GET + HTML tag-stripping). The page explicitly
  labels this as the **previous** model relative to a newer "Lagoon 42
  Millennium" refresh — confirming the projection is correctly scoped to
  the same original Lagoon 42 generation named in
  `research/benchmark/SEED_RESEARCH_NOTES.md` SEED-18, not conflated with
  the newer Millennium variant, nor (as a REVIEW-amendment cross-check
  against a Wikipedia lead confirmed) with an unrelated, much older c.1990
  Van Peteghem/Lauriot-Prevost "Lagoon 42" built by Jeanneau/TPI
  Composites/CNB.
- **LAG-2** — `https://www.lagoon-catamaran.de/en/lagoon-models/lagoon-42-catamaran/technical-specifications.html`
  (an authorized German regional dealer's technical-specification page).
  Independently corroborates LAG-1's length/beam/draught/displacement
  figures exactly and adds the naval architect (VPLP Design) and CE
  certification category. No keel/draft option language.
- **LAG-3** — `https://www.lagoon-catamaran.de/fileadmin/L42_Benutzerhandbuch_en.pdf`
  ("189199 RCD-2, Index G, LAGOON 42 OWNER'S MANUAL"), the official
  homologation-adjacent RCD technical manual (~50 pages: general
  dimensions, design categories/displacement, electricity, capacities,
  sails/rigging, safety). Retrieved as the strongest available primary
  document, specifically to seek configuration-space-completeness evidence
  per independent review's instruction.

**Facts:** `loa_m = 12.92` (LAG-3's "L.O.A (Lmax): standard"; **REVIEW
amendment correction** — the value originally retained, 13.22 m from LAG-1's
unqualified "Length overall" row, is now understood via LAG-3 to be the
spinnaker-pole-inclusive maximum LOA, not the standard figure; this does not
change any Q1/Q2/Q10 result, since 12.92 m still exceeds both the `8–11 m`
and `9–12 m` range upper bounds), `beam_m = 7.68` (corroborated by all three
sources), `draft_max_m = 1.26` (corroborated by all three sources).

**`configuration_space_complete` — corrected to `False`.** The original
submission set this `True` on the reasoning that LAG-1 named only one
hull/keel configuration while explicitly marking other optional equipment
(mainsail/Code 0) with `(opt.)` and leaving draught unmarked. Independent
review correctly rejected this: absence of a stated second keel/draft option
on one product page does not prove the factory-relevant configuration space
is exhaustive, and general reasoning about how production catamarans of this
class are typically built ("one fixed, hull-integral keel per mould") is not
admissible proof either.

Research was extended to LAG-2 and LAG-3 specifically to look for stronger
evidence. **LAG-3 is the strongest document obtained**: it explicitly tags
several genuinely optional items throughout ("Auxiliary switch (option)",
"Fresh water tank - Port/Starboard (option)") yet states exactly one
draught figure and no second keel configuration anywhere in the document,
including its dedicated design-category/displacement chapter. This is
materially stronger than a single marketing page, but it remains, in
substance, an absence-of-mention — no source obtained, including LAG-3,
contains an affirmative statement that the documented configuration is the
complete factory-relevant configuration space. Per CLAUDE.md's core
guardrail ("Missing/unknown is not evidence that a characteristic is
absent") and the review's explicit standard, this is not sufficient to
license `configuration_space_complete=True`. The flag is therefore reverted
to the conservative `False` default — the same treatment already applied to
Oceanis 30.1 and Bavaria Cruiser 34 in this wave, both of which have
*explicitly enumerated multiple* named options and are still held to
`False`, an even stronger evidentiary position than Lagoon 42's single,
undifferentiated configuration. The admission oracle fixes this exact
boolean in both directions: a tampered flip to `True` fails admission
exactly like a tampered flip away from `False` would for Bavaria/Contessa
(see `tests/unit/test_search_seed_corpus_wave1.py`).

**Q1/Q2/Q10 outcome (corrected):** Lagoon's single configuration is a
confirmed `FALSE` on Q1 and Q2 (LOA `12.92 m` exceeds both the `8–11 m` and
`9–12 m` ranges; beam `7.68 m` also exceeds Q2's `3.60 m` maximum), but with
`configuration_space_complete=False` the unchanged engine cannot license a
design-level `CONFIRMED_NON_MATCH` from that alone — it yields
`INSUFFICIENT_DATA` (reason `CONFIGURATION_AMBIGUOUS`), exactly the same
engine behaviour already documented for the Oceanis 30.1 pilot's Q4/Q8/Q9.
Q10 remains `CONFIRMED_MATCH` (`1.26 m ≤ 1.60 m`), since an existential match
never depends on completeness. **This wave therefore has zero genuine
`CONFIRMED_NON_MATCH` results** — the same situation the Oceanis 30.1 pilot
already documented as "expected, correct, existing-engine behaviour" for its
own configuration-incomplete design.

## 6. Exact Wave-1 Q1/Q2/Q10 result distribution (corrected)

Produced by `uv run python scripts/search_seed_corpus_wave1.py`, which runs
the unchanged locked Q1/Q2/Q10 shapes through the unmodified
`hullq.search.configuration_engine.run_configuration_query`.

| Query | CONFIRMED_MATCH | CONFIRMED_NON_MATCH | INSUFFICIENT_DATA | Evaluable |
|---|---|---|---|---|
| Q1 (LOA 8–11 AND Draft≤1.80) | Oceanis 30.1, Bavaria Cruiser 34 | — | Contessa 32, Lagoon 42 | **2/4** |
| Q2 (LOA 9–12 AND Beam≤3.60 AND Draft≤2.00) | Oceanis 30.1, Bavaria Cruiser 34 | — | Contessa 32, Lagoon 42 | **2/4** |
| Q10 (Draft≤1.60) | Oceanis 30.1, Bavaria Cruiser 34, Lagoon 42 | — | Contessa 32 | 3/4 |

**Q1 and Q2 now fall below the slice's required 3/4 minimum evaluability
gate.** Only Q10 meets it. Per SLICE-0039's explicit stop condition
("meeting the utility gate would require replacing a design, guessing a
value, weakening UNKNOWN, or widening the slice" → stop and report rather
than invent a solution), this wave is reported **`BLOCKED`**, not `REVIEW`.
No design was replaced, no value was guessed, and no alternate route to
`CONFIRMED_NON_MATCH` was manufactured to avoid this outcome.

**Matching configuration IDs** — every confirmed match identifies its exact
matching configuration(s), never a design-wide flattened value:

- Q1: Oceanis 30.1 → `oceanis-30-1-shallow-keel`; Bavaria → `bavaria-cruiser-34-shoal-draft-option`.
- Q2: Oceanis 30.1 → `oceanis-30-1-deep-keel`, `oceanis-30-1-shallow-keel` (both fixed keels clear 2.00 m); Bavaria → `bavaria-cruiser-34-shoal-draft-option`.
- Q10: Oceanis 30.1 → `oceanis-30-1-shallow-keel`; Bavaria → `bavaria-cruiser-34-shoal-draft-option`; Lagoon 42 → `lagoon-42-standard`.

## 7. Configuration count per design

| Design | Configurations | Configuration-sensitive? |
|---|---|---|
| Oceanis 30.1 (reused) | 3 (deep-keel, shallow-keel, retractable-keel) | Yes — draft varies by keel |
| Bavaria Cruiser 34 | 2 (standard-draft, shoal-draft-option) | Yes — draft varies by keel |
| Contessa 32 | 1 (baseline; one-design class hull) | No known configuration sensitivity within researched evidence |
| Lagoon 42 | 1 (standard) | No documented configuration sensitivity; configuration-space completeness not established (§5) |

## 8. `FALSE_CONFIRMED_RESULT` assessment

**Zero.** Every `CONFIRMED_MATCH` above is directly traceable to a specific,
rights-cleared, cited source figure for that exact configuration:

- Bavaria's match traces to BAV-1's "Draught option 1.58 m" row (and design-wide LOA/beam).
- Lagoon's Q10 match traces to LAG-1/LAG-2/LAG-3's corroborated "1.26 m" draught figure.
- Every Oceanis result is unchanged from the SLICE-0037 pilot's own assessment.

This wave produces **zero `CONFIRMED_NON_MATCH` results** (§5/§6) — the
correction removed the one design that previously produced one (Lagoon),
because `configuration_space_complete=False` uniformly blocks non-match for
every design in this wave, exactly as it already did for the Oceanis 30.1
pilot. Both Contessa 32's and Lagoon's `INSUFFICIENT_DATA` results are never
converted to a guessed match or non-match. `tests/unit/test_search_seed_corpus_wave1.py`
includes adversarial coverage proving: design identity tampering,
confirmed-value tampering (including same-threshold-side edits that would
not change the Search outcome), configuration-ID/scope tampering,
evidence-reference tampering (including an allowed-but-wrong source
substitution), unauthorized extra fields, unexpected extra/missing
configurations, and `configuration_space_complete` tampering in **both
directions for every design** (Bavaria/Contessa reject a tampered `True`;
Lagoon now also rejects a tampered `True`, matching its corrected
authorized value of `False`) all fail admission before any of it can reach
the Search kernel — including an adversarial attempt to inject the
well-known but non-authorized Contessa 32 LOA figure (`9.75` m), which is
rejected purely because it is not in the independently authorized (empty)
fact set for this design, regardless of its real-world plausibility.

## 9. Local owner-test command result

```text
uv run python scripts/search_seed_corpus_wave1.py
```

Runs deterministically offline (no network access required after the
retained JSON/log files are committed); prints, for each of Q1/Q2/Q10, the
query id/description, corpus size (4), and every design's result class,
per-configuration truth, and matching configuration IDs where applicable;
ends with a per-query evaluable/4 summary. Output matches §6 exactly.

## 10. Confirmation of scope discipline

No work was started on the next Seed-Corpus wave (Wave 2: Sun Odyssey 36i,
Hallberg-Rassy 400, Najad 451 CC, Sirius 35 DS), no Concierge test execution
was started, and no market/listing/frontend/API/SEO work was touched. Only
the four locked Wave-1 designs and only Q1/Q2/Q10 were addressed, per the
slice's explicit scope boundary.
