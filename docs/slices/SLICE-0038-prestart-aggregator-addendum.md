# SLICE-0038 — binding pre-start aggregator addendum

**Status:** BINDING ADDENDUM TO `SLICE-0038-owning-real-sales-offer-pilot.md`  
**Date:** 2026-08-31  
**No `Type:` header by design:** this is not a second primary slice document.

This addendum records Project Owner-directed pre-start research on Scanboat and Listings Port. It narrows/strengthens SLICE-0038 evidence handling without adding scope.

Read together with:

- `docs/slices/SLICE-0038-owning-real-sales-offer-pilot.md`
- `research/market/SL0038_PRESTART_AGGREGATOR_ASSESSMENT_2026-08-31.md`

If this addendum is stricter than the primary contract on the points below, this addendum controls for SLICE-0038.

## Source scope remains unchanged

Owning.pro remains the **only** live market source authorized for SLICE-0038.

Do not fetch, crawl, scrape or implement adapters for:

- Scanboat;
- Listings Port;
- YachtWorld;
- Boat24;
- boats.com;
- Apollo Duck;
- Yachtr;
- TheYachtMarket;
- or any other upstream marketplace.

Scanboat is explicitly excluded because its published Impressum prohibits commercial crawling/copying without permission. Listings Port is excluded because no public HullQ-usable API or sufficiently positive automated/commercial-access disposition was established in the bounded pre-start assessment.

If Owning returns an upstream source/platform name or URL, treat that as provenance metadata only. Do not follow it for enrichment in this slice.

## Additional listing-truth invariants

### 1. Nonphysical/placeholder draft must fail closed

For this Oceanis 30.1 pilot, a listing-specific numeric draft that is:

- `0`;
- negative;
- boolean;
- NaN/infinite;
- otherwise malformed/non-finite;

must **not** be passed as a confirmed numeric value to the existing Search comparator.

Result: listing-level `TruthState.UNKNOWN` with an explicit reason such as nonphysical/invalid/placeholder listing draft.

A value of `0` must never become `0 <= 1.60 -> TRUE`.

This rule is pilot-scoped to the physical Oceanis 30.1 draft criterion; do not generalize it into a new marine ontology or global numeric rule.

### 2. Model/design truth is not physical-listing truth

Neither of these may authorize listing-level TRUE/FALSE:

- the accepted SLICE-0037 BoatDesign/configuration facts;
- a market aggregator's model-level canonical draft/keel/configuration fact.

They may explain why the design is relevant, but the concrete offered boat remains `UNKNOWN` unless the concrete listing carries admissible listing-specific evidence.

Required visible distinction remains:

```text
DESIGN MATCH: Oceanis 30.1 has a Q10-matching factory configuration
LISTING CONFIG: independently assessed from this physical listing only
```

### 3. Conflicting listing evidence must fail closed

If more than one listing-specific draft observation is available and they materially conflict, do not choose whichever value produces a desired Search outcome.

At minimum:

- values on opposite sides of the locked `1.60 m` boundary -> `UNKNOWN` / unresolved conflict;
- a structured placeholder/nonphysical value plus a different plausible textual/structured value -> do not use the placeholder; if the admissible remaining observation is independently clear and uniquely controlling, it may be evaluated; otherwise `UNKNOWN`;
- contradictory ambiguous range/configuration semantics -> `UNKNOWN`.

Do not create a general conflict-resolution engine in this slice.

### 4. Evidence origin must be explicit

Every listing-level TRUE/FALSE must identify the concrete listing observation that supplied the numeric draft.

The owner-test/result must not imply that a value came from the physical listing when it actually came from a model/design database.

### 5. No automatic configuration synonym table

Do not infer listing configuration from standalone words such as:

- `deep`;
- `standard`;
- `short`;
- `shoal`;
- `shallow`;
- `lifting`;
- `swing`.

The external pre-start research strengthened the Project Owner's terminology concern: Listings Port itself currently describes the Oceanis 30.1 as a **standard** ~1.88 m keel plus ~1.3 m **shoal-draught** option and lifting-keel range. That is useful later data-quality evidence, but not permission to rename SLICE-0037 or infer a concrete listing configuration here.

Prefer a single unambiguous physical-listing numeric draft. Otherwise UNKNOWN.

## Required adversarial test additions

In addition to the primary SLICE-0038 tests, focused tests must prove:

1. listing draft `0` -> `UNKNOWN`, never TRUE;
2. negative listing draft -> `UNKNOWN`;
3. model/design-level draft present but physical-listing draft absent -> listing `UNKNOWN`;
4. two listing-specific draft observations on opposite sides of 1.60 m -> `UNKNOWN`;
5. an unrelated/placeholder structured `0` cannot override or manufacture truth;
6. upstream marketplace/source attribution alone does not authorize fetching that upstream source;
7. no configuration TRUE/FALSE is produced merely from the words `deep`, `standard`, `short`, `shoal`, `shallow`, `lifting` or `swing`;
8. multiple identical, unambiguous, listing-specific numeric observations may remain eligible for normal numeric evaluation if all other admission rules pass.

## Dedup / market-history observations remain follow-up only

The pre-start research confirms that:

- the same physical boat can be syndicated to multiple portals;
- Listings Port already groups duplicates across markets;
- Listings Port already exposes asking-price history, trend and reduction analytics.

These validate the importance of OQ-005 and OQ-017 but do **not** authorize dedup, historical price persistence or additional source collection in SLICE-0038.

## Completion-report addition

The SLICE-0038 completion report must additionally state:

- whether any live Owning candidate exposed zero/negative/placeholder draft data;
- whether any candidate exposed conflicting listing-specific draft observations;
- whether any model-level fact was deliberately prevented from becoming listing-level truth;
- whether Owning exposed upstream source attribution and, if so, confirmation that no upstream source was fetched;
- results of the addendum adversarial tests.

All other primary slice boundaries remain unchanged.