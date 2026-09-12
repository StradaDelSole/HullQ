# SLICE-0051 — Acceptance closure

**Slice:** SLICE-0051  
**Type:** IMPLEMENTATION  
**Status:** OWNER_ACCEPTED  
**Implementation PR:** #187  
**Initial reviewed implementation HEAD:** `bd3916ef6a8c8b51940f91abda51b4f66c7028a6`  
**First amendment / blocked HEAD:** `2f6d7ba4b622a82250fa2c4df62bb43fa41d7814`  
**Second amendment HEAD:** `f0c9133f120989a3e0f203bba4e08c9d3694aa98`  
**Accepted implementation HEAD:** `d9f13b9f44583604b0c6a985c4d81ea470e11718`  
**Implementation merge commit:** `599710f947d28397eb84da04af3fb8aa66dc92f7`  
**FieldResolution blocker reconciliation merge:** `ebe2cda4a10de1f5a4737d2270bf00f35fedeba1`  
**Owner acceptance:** explicitly recorded 2026-09-12

## Accepted capability

SLICE-0051 delivers HullQ's first production buyer-facing technical Requirements → Native Inventory Search vertical.

Exactly one public hard buyer requirement is accepted:

```text
draft_max=<exact decimal metres>
```

Canonical example:

```text
/de/search?draft_max=1.6
```

Accepted end-to-end path:

```text
buyer draft_max
→ deterministic BoatDesign/configuration eligibility
→ durable accepted FieldResolution for the relevant design/configuration draft fact
→ ACTIVE native professional inventory
→ NativeListing → MarketEpisode → PhysicalBoat
→ publishing Organization's current physical_boat.draft claim
→ same-PhysicalBoat current-observation contradiction guard
→ CONFIRMED_MATCH / CONFIRMED_NON_MATCH / INSUFFICIENT_DATA
→ buyer-visible locale-prefixed Astro SSR Search
→ /listings/{NativeListingId}
```

The central truth boundary remains unchanged:

```text
this design/configuration can satisfy the requirement
!=
this concrete offered boat is confirmed to satisfy it
```

A compatible BoatDesign/configuration is only a candidate-admission step. It never by itself confirms that the concrete yacht being offered satisfies the buyer requirement.

## Public Search contract

The accepted first Search surface is intentionally narrow and deterministic.

Public locale routes are:

```text
/en/search
/de/search
/fr/search
/pt/search
/es/search
```

Accepted URL/request behavior includes:

- stable language-neutral semantic query parameter `draft_max`;
- exact decimal grammar and parsing directly to `Decimal`;
- deterministic sparse canonical state;
- exact decimal canonicalization such as `01.60 → 1.6` and `1.600 → 1.6`;
- equivalent duplicate singleton values collapse to canonical state;
- conflicting duplicate singleton values are invalid;
- unknown parameters fail closed;
- the initial non-semantic parameter allowlist is empty, therefore UTM parameters are invalid;
- invalid state returns HTTP 400 without Search evaluation;
- valid non-canonical state returns HTTP 308 to the canonical URL;
- bare `/search` redirects deterministically to `/en/search` while preserving valid query state;
- unsupported locale Search routes return 404;
- the first Search surface is deliberately `noindex`;
- Astro owns SSR/web presentation while FastAPI remains the sole application/domain/Search semantic boundary.

Broader indexable SEO landing-page taxonomy, faceted sitemap expansion, broad structured-data strategy and arbitrary indexable Search combinations remain deferred.

## Design/configuration qualification and OQ-004 provenance

Implementation review exposed a missing prerequisite that the original readiness reconciliation had failed to account for: accepted OQ-004 / ADR-0006 `FieldResolution` semantics existed in the domain/specification layer, but production PostgreSQL did not yet persist current/versioned FieldResolution state.

This was reconciled deliberately on `main` in:

```text
docs/SLICE_0051_FIELD_RESOLUTION_BLOCKER_RECONCILIATION_2026-09-12.md
```

The reconciliation classified the missing persistence as:

```text
DECIDED_NOT_YET_IMPLEMENTED
```

rather than a new Project Owner decision. It authorized the minimum bounded Alembic persistence prerequisite inside the already-active SLICE-0051.

The accepted implementation now provides:

- immutable/versioned `field_resolutions` history;
- explicit `field_resolution_heads` current pointers;
- one current resolution per `(subject_kind, subject_id, field_pointer)`;
- race-safe serialization for first writes and revisions;
- exact typed historical/current readback;
- durable supporting/contradicting/considered evidence identities;
- canonical-value snapshot consistency enforced at the write boundary;
- Source record identity/schema binding before production-use rights admission;
- accepted `SourceUse.PRODUCTION_VALUE` fail-closed rights enforcement;
- exact `Decimal` preservation for the bounded draft path;
- exact-retry idempotency including supersession identity.

SLICE-0051 Search consumption remains bounded to exactly:

```text
BoatDesign
/baseline/dimensions/draft_max_m

NamedVariant
/overrides/dimensions/draft_max_m
```

A NamedVariant with no own draft override inherits the already-qualified BoatDesign baseline at configuration-evaluation time; no duplicate source-backed resolution is manufactured for inheritance. A variant with unapplied `requires_option_ids` remains excluded from the resolved configuration set.

No generic source winner, source-priority policy, majority/recency resolver, global all-field resolution or broad FieldResolution backfill is introduced.

## Exact Decimal boundary

The public requirement and relevant qualified technical values remain exact decimals end to end.

Accepted behavior preserves:

```text
public query spelling
→ exact Decimal parse
→ canonical decimal URL spelling
→ FieldResolution exact decimal snapshot
→ QualifiedNumericValue
→ NumericLeafCriterion
→ comparison
```

No binary-float intermediary is allowed to change an accepted `draft_max` threshold or persisted qualified draft value.

The FieldResolution snapshot for this numeric vertical is persisted losslessly and decoded back to exact `Decimal` before Search comparison.

## Concrete PhysicalBoat qualification

The only concrete candidate value is the publishing Organization's own current `physical_boat.draft` claim for the exact offered PhysicalBoat.

Accepted classification is:

```text
publisher draft <= draft_max + no current contradiction
→ CONFIRMED_MATCH

publisher draft > draft_max + no current contradiction
→ CONFIRMED_NON_MATCH

publisher draft omitted / UNKNOWN / unresolved / conflicting
→ INSUFFICIENT_DATA
```

The contradiction guard uses the current admissible same-PhysicalBoat observations across Organizations from one consistent PostgreSQL query/snapshot. Semantically equivalent current decimal values do not conflict. UNKNOWN/omitted observations do not manufacture a contradiction. Superseded claim revisions are not current contradictions.

Only `CONFIRMED_MATCH` appears in the primary result set. `INSUFFICIENT_DATA` is mechanically and visually separate and is never counted/presented as a match.

A listing without durable applicable `BoatDesignRef`, or whose design/configuration does not itself reach design-level confirmed compatibility, does not enter concrete listing classification through fuzzy inference.

## FieldResolution transactional guarantees

The accepted persistence path proves the current-head invariants against PostgreSQL 18.

Two concurrent first writes for the same logical subject field result in exactly one `CREATED` winner and one fail-closed conflict. Two concurrent revisions from the same predecessor result in exactly one `REVISED` winner; the loser cannot advance the head or leave an orphan revision.

A forced failure after the immutable resolution INSERT but before successful head advance proves:

```text
post-INSERT head failure
→ whole transaction rolls back
→ no orphan FieldResolution revision remains
→ no invalid head remains
```

Supersession identity is part of the immutable resolution fingerprint and is persisted from the resolution itself. The writer requires:

```text
resolution.supersedes_resolution_id
==
expected_current_resolution_id
```

before admitting the write, and separately compares the expected predecessor with the durable current head under the subject-field serialization boundary.

## Source-rights admission

Durable evidence existence is not sufficient to authorize a production resolution.

For supporting evidence of a resolved production value, the accepted writer requires:

```text
evidence.source_id
→ matching available Source record
→ Source record internally declares the same source_id
→ SOURCE_SCHEMA.v0.2 validation passes
→ check_source_use(SourceUse.PRODUCTION_VALUE)
→ ALLOWED
```

Missing, mismatched, malformed, prohibited, conditional/unresolved, unknown or legal-review-required production use cannot authorize the resolution.

This bounded admission mechanism does not create a new universal Source-registry architecture and does not broaden the historical SLICE-0037 pilot clearance.

## Buyer-visible result proof

The retained production proof exercises the committed path through real PostgreSQL 18, FastAPI and built Astro SSR without monkeypatching the result qualification:

```text
durable research evidence
→ durable canonical BoatDesign / NamedVariant
→ production-admitted active FieldResolution
→ exact draft_max design/configuration Search
→ ACTIVE NativeListing
→ concrete publisher PhysicalBoat draft
→ same-PhysicalBoat contradiction guard
→ FastAPI
→ Astro SSR
```

The accepted proof demonstrates:

- one genuine `CONFIRMED_MATCH` backed by a durably admitted NamedVariant FieldResolution and concrete PhysicalBoat draft;
- omitted concrete draft → `INSUFFICIENT_DATA`;
- current cross-Organization same-PhysicalBoat contradiction → `INSUFFICIENT_DATA`;
- unqualified design does not confirm;
- no durable design identity does not confirm;
- non-ACTIVE listing does not leak;
- result navigation remains `/listings/{NativeListingId}`.

## Independent review history

The slice required multiple exact-head review cycles.

Initial reviewed implementation HEAD:

```text
bd3916ef6a8c8b51940f91abda51b4f66c7028a6
```

The first independent review returned `AMEND` with six findings covering exact decimal canonicalization, Decimal preservation through the Search kernel, the absent production FieldResolution prerequisite, NamedVariant option-dependency handling, consistent same-PhysicalBoat observation reads and web 400-vs-503 behavior.

First amendment / blocked HEAD:

```text
2f6d7ba4b622a82250fa2c4df62bb43fa41d7814
```

Findings 1, 2, 4, 5 and 6 were corrected. Finding 3 correctly failed closed because no durable production FieldResolution persistence existed. The deliberate blocker-reconciliation workflow then established that this was an accepted-but-unimplemented OQ-004 prerequisite rather than a new semantic decision.

Second amendment HEAD:

```text
f0c9133f120989a3e0f203bba4e08c9d3694aa98
```

The new FieldResolution persistence/bridge closed the original blocker but the next exact-head review returned `AMEND` for four persistence-hardening findings:

1. canonical-value consistency needed enforcement at write/current-head admission, not only Search read-time defense;
2. supersession identity could not be silently substituted and had to participate in the immutable fingerprint;
3. supporting Source records needed explicit identity binding plus `SOURCE_SCHEMA.v0.2` validation before rights admission;
4. race safety and post-INSERT rollback required real PostgreSQL adversarial proof.

Final accepted implementation HEAD:

```text
d9f13b9f44583604b0c6a985c4d81ea470e11718
```

All ten findings were independently rechecked and closed. No material finding remained, so the final exact-head review result was:

```text
ACCEPT
```

The Project Owner then explicitly accepted that exact implementation head on 2026-09-12.

## Exact-head verification

Exact accepted implementation HEAD:

```text
d9f13b9f44583604b0c6a985c4d81ea470e11718
```

Remote verification on that exact SHA:

```text
CI run 34715044273
→ SUCCESS
→ quality ubuntu: SUCCESS
→ quality windows: SUCCESS
→ web quality (Astro/Node): SUCCESS
→ dependency audit: SUCCESS
→ PostgreSQL 18 integration/full-suite gate: SUCCESS
→ repository validation: SUCCESS

Manufacturer artifact reproducibility run 34715045510
→ SUCCESS
```

Implementation-agent final local validation reported:

```text
ruff format --check: PASS
ruff check: PASS
mypy src: PASS
pytest: 4811 passed, 3 skipped, 0 failed
repository validation: PASS
web check: PASS
web tests: 25/25 passed
web build: PASS
retained first native inventory Search proof: PASS
```

Implementation PR #187 merged the exact owner-accepted head to `main` as:

```text
599710f947d28397eb84da04af3fb8aa66dc92f7
```

## Scope retained / explicitly deferred

SLICE-0051 deliberately does not add:

- another public technical Search criterion;
- generic all-field native-inventory Search;
- ranking/recommendation logic beyond the bounded deterministic result surface;
- a generic/global canonical-fact resolver;
- automatic source-ranking/winner policy;
- broad BoatDesign FieldResolution backfill;
- independent verification of broker PhysicalBoat claims;
- authenticated Auth0 broker workspace;
- media upload/storage/presentation;
- saved Search persistence, monitoring or alerts;
- listing price-history intelligence;
- lead/contact workflow;
- republish, SOLD/ARCHIVED or freshness lifecycle semantics;
- indexable faceted SEO/search landing pages, sitemap expansion or broad structured data;
- a second backend or dedicated external Search engine.

These items remain future product/architecture work subject to normal repository reconciliation and capability selection.

## PROJECT_STATE freshness closure

This closure advances the highest owner-accepted slice from 0050 to 0051.

In the same closure change, `docs/PROJECT_STATE.md` advances atomically to:

```text
PROJECT_STATE_ACCEPTED_SLICE: 0051
PROJECT_STATE_QUEUE_SLICE:    0052
```

`SLICE-0052` is only the next queue number. **This closure does not select its capability and does not authorize implementation.** The capability must be chosen through the required post-SLICE-0051 product/architecture reassessment and repository reconciliation, followed by the normal readiness process before `START_SLICE.bat` can be used.

The completed product threshold is now:

```text
PERSISTED REAL LISTING
→ PRODUCTION PUBLIC LISTING
→ CONCRETE-YACHT BROKER TRUTH
→ FIRST PRODUCTION BUYER TECHNICAL SEARCH
= BUILT
```

Remaining slice distance to the first externally visible listing is:

```text
0
```

That threshold was already reached by SLICE-0049; SLICE-0051 adds the first buyer-facing technical Search path into that public native inventory.

Repository validation must fail this closure if the `PROJECT_STATE_ACCEPTED_SLICE` marker and highest acceptance-closure filename are not identical.

## Product execution checkpoint

With SLICE-0051 accepted, HullQ has crossed an important product boundary: a public buyer can express a real technical requirement and receive only concrete native listings that survive both qualified design/configuration eligibility and exact offered-boat truth checks.

The next post-slice reassessment should therefore select the smallest highest-leverage continuation of the buyer/broker loop from the now-built Search → listing path. It must begin with repository reconciliation and must not assume that broader Search, Saved Search, broker acquisition tooling, contact/leads, media, authentication or another technical criterion is automatically next.

No foundation-only slice should be selected unless the reassessment proves it cannot safely be deferred behind a more externally valuable vertical.

## Closure decision

```text
SLICE-0051 = OWNER_ACCEPTED
```

Implementation is merged. Closure becomes canonical only after this closure PR itself passes exact-head repository validation/CI, independent closure review and guarded merge.
