# SLICE-0037 — BENETEAU Oceanis 30.1 real-search pilot research record

**Status:** implementation research record. Feeds `scripts/search_oceanis_30_1.py`
and `research/benchmark/waves/sl0037-oceanis-30-1/oceanis_30_1_projection.v1.json`.
Not canonical BoatDesign admission; not the twelve-design `SEARCH_BENCHMARK.v0.1.md`
corpus; not a general BENETEAU ingestion adapter.

## 1. Target identity and scope

**BENETEAU Oceanis 30.1** — introduced 2019-01-14 per the official BENETEAU
press release (SRC-5); hull designed by Finot-Conq (Pascal Conq), confirmed by
both SRC-5 and the naval architect's own site (SRC-6). As of this research
(2026-08-31) the model is still listed on BENETEAU's live current Oceanis
range (SRC-1), alongside Oceanis 34.1/37.1/40.1/42/47/52. No production-end
date is asserted, and no production-year range/design-epoch boundary beyond
"introduced 2019, still current as of retrieval" is invented, per the slice's
explicit instruction not to infer a boundary from the model name alone.

## 2. Source basis and the robots.txt finding

Six distinct documents were retrieved (see `source_retrieval_log.json` for
full detail); the retrieval ceiling was 12 and was not approached.

A significant mid-research finding: `pro.beneteauusa.com` (SRC-4, the most
detailed single document retrieved — an official BENETEAU America equipment
list PDF with a per-keel-option draft/ballast breakdown and an explicit "9/10"
mast-fraction statement) publishes a site-wide `robots.txt` of
`User-agent: * / Disallow: /`. Per `SOURCE_RIGHTS_POLICY.v0.1.md` SR-6.6
condition 4 ("source terms/access restrictions do not prohibit the chosen
research method"), this is an explicit, unqualified prohibition on automated
access to that entire domain. The document had already been fetched and read
by the time this was checked; rather than silently keep using it, it was
struck from the evidence basis entirely, and every fact it uniquely supplied
(the exact deep-keel draft to two decimal places, per-keel ballast weights,
the "9/10" mast-fraction statement, and the specific "affixed with stainless
steel stock" rudder construction wording) is **not** used anywhere in the
retained projection, the Search input, or any claim below. This is recorded
transparently as SRC-4 in the retrieval log (`used_as_positive_evidence:
false`, `sr_6_6_disposition: "EXCLUDED_robots_txt_disallow"`) rather than
silently omitted, so the exclusion is auditable.

`www.beneteau.com` (SRC-1, SRC-5) and `en.finot-conq.com` (SRC-6) both publish
`robots.txt` files that do not disallow the specific pages fetched, and were
retrieved by direct raw-HTML fetch (not WebFetch's AI-summarization step) so
that every fact used below is a literal quoted string from the page, not a
paraphrase. `brochures.beneteau.com` (SRC-3) has no `robots.txt` at all (404)
and yielded no extractable content (client-side JS viewer). One additional
WebFetch of `www.beneteau.com/oceanis/oceanis-301` (SRC-2, the AI-summarized
pass that preceded the raw re-fetch as SRC-1) is retained for audit but not
relied upon, since every fact it reported was independently re-obtained from
SRC-1's raw text.

Source-rights disposition for every source actually relied upon (SRC-1,
SRC-5, SRC-6): `unlicensed_factual_reference` rights basis, SR-6.6
`conditional` production clearance — lawfully accessible, reused as discrete
factual/technical values only (not vendored expressive text), provenance
recorded, source terms do not prohibit the method used, not a bulk-extraction
mechanism (six documents total for one design), and this bounded single-pilot
manual-style retrieval is not claimed as a separately-cleared
`automated_ingestion` pipeline.

Web search (not counted toward the retrieval ceiling) was used only to locate
`en.finot-conq.com`'s Oceanis 30.1 URL; no search-result snippet (including
third-party aggregator/broker snippets that surfaced incidentally, e.g.
boat-specs.com, sailingmagazine.net) was used as evidence anywhere in this
package, per the slice's source boundary.

## 3. Identity/specification scope actually established

Design-wide (does not vary by keel option), from SRC-1 corroborated by SRC-6:

- `loa_m = 9.53` — SRC-1 "Length Overall 31'3'' / 9.53 m"; SRC-6 "Lenght OA :
  9,53 m".
- `beam_m = 2.99` — SRC-1 "Beam overall 9'10'' / 2.99 m"; SRC-6 "Beam : 2,99 m".

Three named factory ballast/keel options are positively evidenced by SRC-1
("There are 3 ballasts available, so you can sail in your configuration of
choice. Deep draft / Shallow draft / Performance draft (hydraulic swing
keel)"):

- **Deep draft** (fixed keel) — `draft_max_m = 1.85`, from SRC-6's "Draft long
  : 1,85 m".
- **Shallow draft** (fixed keel) — `draft_max_m = 1.30`, from SRC-6's "Draft
  short : 1,30 m", independently corroborated by SRC-1's design-wide "Draft
  Min 4'3'' / 1.3 m".
- **Performance draft (hydraulic swing keel)** — the movable-appendage
  configuration (this is the locked `MOVABLE_APPENDAGE` diversity control per
  `SEARCH_BENCHMARK.v0.1.md`). Draft is operator-adjustable; SRC-1's
  design-wide "Draft Max 7'7'' / 2.3 m" is consistent with this configuration
  fully lowered, but no source states one single factory-resolved draft value
  for it. Per Required Behavior §B ("Do not silently turn a page-level draft
  min/max pair into two invented configurations"), this configuration's
  `draft_max_m` is left unresolved rather than assigned an invented endpoint
  value — see section 5.

## 4. Configuration-sensitive draft — not flattened

The two fixed-keel configurations are genuinely different, independently
factory-named and independently sourced (deep = 1.85 m from SRC-6's "Draft
long"; shallow = 1.30 m from SRC-6's "Draft short", corroborated by SRC-1's
design-wide minimum). Neither value is derived by splitting a single
page-level min/max pair — SRC-6 names the two variants explicitly ("Draft
short" / "Draft long") as two separate rows in its own characteristics table,
and SRC-1 independently confirms "Deep draft" / "Shallow draft" as two
separate named ballast options. This is the exact configuration-sensitivity
the slice requires: `1.85 m` and `1.30 m` sit on opposite sides of four of the
five Q1-Q10 draft thresholds (`1.60`, `1.70`, `1.80`; both clear `2.00`).

## 5. Deliberately unresolved fields (fail-closed)

Every field below was considered and is explicitly left `MISSING` rather than
guessed. Full reasoning for each is in
`oceanis_30_1_projection.v1.json`'s `fields_deliberately_left_unresolved_*`
sections; summarized here:

| Field | Why left unresolved |
|---|---|
| `displacement_kg` | SRC-1's spec-table figure (4,120 kg) and its own separate marketing-prose figure (a rounded "8,000 lbs" ≈ 3,629 kg on the same page) disagree, and SRC-6 separately states 3,990 kg — on the **opposite side** of the Q3 threshold (4,000 kg) from 4,120 kg. None of the three figures is stated as applying to one specific named keel option, so applicability cannot be established as shared, and the discrepancy cannot responsibly be forced into either a single value or a same-scope conflict. |
| `rig.sailplan` | Single-headsail-position architecture (self-tacking jib / genoa as alternatives, never combined) is consistent with a sloop rig but is not a literal source statement of "sloop". Holding this to the same literal-statement standard the SLICE-0036 real-design validation record used for cross-field entailment (not inferring "obviously a monohull"/etc. from context) rather than a looser standard for direct field research. |
| `rig.masthead_fractional` | The one clean piece of evidence for this (SRC-4's "9/10" mast statement) is exactly the fact excluded by the robots.txt finding (section 2). No remaining cleared source states a fraction or masthead/fractional designation. |
| `appendages.keel_type` | No cleared source names a controlled `keel_type` token (fin/bulb/etc.); sources name the options by draft, not shape. |
| `appendages.rudder_support` | SRC-1/SRC-5 both confirm "twin rudders" (a real, directly usable `rudder_count = 2` fact, not itself needed by any locked query and therefore not projected into Search), but neither states skeg-supported vs. free-standing. Absence of a skeg mention is never treated as evidence the skeg is absent (core provenance guardrail). |
| `deck.cockpit_position` | Cockpit layout/seating is described, but no source states the controlled `cockpit_position` token outright. |

## 6. MTE application

Every Oceanis fact this research qualified or considered is classified
against `specs/MARINE_TECHNICAL_ENTAILMENT_RULES.v0.1.json` in
`oceanis_30_1_projection.v1.json`'s `mte_classification` section (mirroring
the style of `research/validation/SL0036-marine-entailment-real-design-validation.md`).

**Result: zero derived facts were materialized.** The one fact that would
have fired a rule — `rig.sailplan = sloop`, which would satisfy
`MTE-RIG-001`'s prerequisite and entail `rig.mast_count = 1` — was never
qualified to `CONFIRMED` in the first place (section 5), so the rule's
prerequisite is not met and it does not fire. `appendages.rudder_count = 2`
is a real, directly confirmed fact (`DIRECT_ONLY` per the registry: no rule
exists for any non-zero rudder count) but is not projected into Search
because no locked Q1-Q10 criterion reads it. `loa_m`/`beam_m`/`draft_max_m`/
`displacement_kg` are `BOAT_DESIGN_SCHEMA.v0.6` principal-dimension fields,
outside the MTE fixed field inventory entirely (which covers only
hull/keel/rudder/rig/cockpit-helm classification fields) — no classification
applies to them by design. No generic/recursive/probabilistic MTE inference
engine was added; this is a research-time classification record only.

## 7. Direct confirmed Search fields and evidence

| Field | Configuration | Value | Evidence |
|---|---|---|---|
| `loa_m` | all three | 9.53 | SRC-1, SRC-6 |
| `beam_m` | all three | 2.99 | SRC-1, SRC-6 |
| `draft_max_m` | deep-keel | 1.85 | SRC-6 |
| `draft_max_m` | shallow-keel | 1.30 | SRC-6, corroborated SRC-1 |
| `draft_max_m` | retractable-keel | *(unresolved — section 3)* | — |

All are `direct` (source-reported), not `derived`. See section 6 for why no
derived fact exists.

## 8. Exact Q1-Q10 outcome summary

Produced by `uv run python scripts/search_oceanis_30_1.py`, which runs the
unchanged locked query shapes from
`fixtures/search/query_mixed.q1_q10_benchmark_shapes.fixture.v0.2.json`
through the unmodified `hullq.search.configuration_engine.run_configuration_query`.

| Query | Result | Detail |
|---|---|---|
| Q1 (LOA 8-11 AND Draft<=1.80) | **CONFIRMED_MATCH** | matching=[shallow-keel]; deep-keel=FALSE (1.85>1.80); retractable=UNKNOWN |
| Q2 (LOA 9-12 AND Beam<=3.60 AND Draft<=2.00) | **CONFIRMED_MATCH** | matching=[deep-keel, shallow-keel] (both clear 2.00 m); retractable=UNKNOWN |
| Q3 (Displacement>=4000 AND LOA<=12) | INSUFFICIENT_DATA | displacement unresolved on every configuration (section 5) |
| Q4 (Masthead AND Draft<=1.80) | INSUFFICIENT_DATA | masthead_fractional unresolved; deep-keel still evaluates FALSE on draft alone but configuration_space_complete=False blocks a design-level non-match |
| Q5 (Aft cockpit AND Fin keel AND Draft<=1.70) | INSUFFICIENT_DATA | cockpit_position and keel_type both unresolved |
| Q6 (Skeg rudder AND LOA 9-12) | INSUFFICIENT_DATA | rudder_support unresolved |
| Q7 (Center cockpit AND Draft<=1.80) | INSUFFICIENT_DATA | cockpit_position unresolved |
| Q8 (Cutter AND Skeg rudder) | INSUFFICIENT_DATA | sailplan and rudder_support both unresolved |
| Q9 (Center cockpit AND Cutter AND Skeg rudder AND Draft<=1.80) | INSUFFICIENT_DATA | three of four criteria unresolved |
| Q10 (Draft<=1.60) | **CONFIRMED_MATCH** | matching=[shallow-keel]; deep-keel=FALSE (1.85>1.60); retractable=UNKNOWN |

**Required configuration-sensitive proof:** Q10 (and, corroborating it, Q1)
supply the required configuration-sensitive `CONFIRMED_MATCH`: the deep-keel
configuration is a confirmed `FALSE` (1.85 m > 1.60 m), the shallow-keel
configuration is a confirmed `TRUE` (1.30 m <= 1.60 m), and
`matching_configuration_ids = ("oceanis-30-1-shallow-keel",)` exactly — not a
flattened design-wide value, not every configuration, and not an invented
range endpoint.

Zero `CONFIRMED_NON_MATCH` results occur, because `configuration_space_complete
= False` is set for the whole design (not independently established as
complete — three named options are evidenced, but no source states this is
the exhaustive factory configuration space) and this uniformly blocks a
design-level non-match even where every *listed* configuration happens to be
FALSE or UNKNOWN for a given query (Q4, Q8, Q9). This is expected, correct,
existing-engine behavior (`hullq.search.configuration_engine.evaluate_design_configuration_set`),
not a defect of this research.

## 9. `FALSE_CONFIRMED_RESULT` assessment

**Zero.** No result above asserts a `CONFIRMED_MATCH` or `CONFIRMED_NON_MATCH`
that is not directly traceable to a specific, rights-cleared, cited source
figure for that exact configuration. Every field left unresolved in section 5
remains `INSUFFICIENT_DATA`/`UNKNOWN` rather than being guessed toward either
truth value. `tests/unit/test_search_oceanis_30_1.py` includes adversarial
coverage proving a stray "value" alongside a non-resolved "state" in the
retained JSON is discarded by the existing `values.py` choke point rather
than leaking into confirmed truth, and that even a tampered
`configuration_space_complete=True` cannot manufacture a false result from
this retained data.

## 10. Local owner-test command result

```text
uv run python scripts/search_oceanis_30_1.py
```

Runs deterministically; prints, for each Q1-Q10, the query id/role/
description, `result_class` (+ reason where applicable), each configuration's
id/truth with per-criterion explanation, and `matching_configuration_ids`
where matched; ends with a CONFIRMED_MATCH / CONFIRMED_NON_MATCH /
INSUFFICIENT_DATA summary. Output matches section 8 exactly.
