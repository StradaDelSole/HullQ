# HullQ — Buyer Requirement Sensitivity Contract v0.1

**Status:** NORMATIVE WHEN MERGED  
**Owning slice:** SLICE-0057 — Buyer Requirement Sensitivity  
**Controlling product direction:** `docs/POST_0054_BUYER_SELLER_PRODUCT_RECONCILIATION_2026-09-17.md`  
**Search foundation:** accepted SLICE-0051 / SLICE-0055 / SLICE-0056  
**Public UX baseline:** `docs/PRODUCT_UX_PRINCIPLES.md`

## 1. Purpose

This contract adds one buyer-visible decision-support capability on top of the already accepted Direct Search:

> Given one valid current Direct Search, the buyer explicitly chooses one currently active hard criterion and supplies one alternative value. HullQ evaluates the current and alternative requirements through the same accepted Search truth and reports the factual result-set delta.

This is the first bounded public projection of accepted Requirement Sensitivity / `Why no match?` semantics.

It is not BuyerRequirements persistence and is not a recommendation engine.

## 2. Hard decision-neutrality boundary

The capability is always buyer initiated.

HullQ MUST NOT:

- suggest which criterion the buyer should change;
- generate an alternative value;
- search for an "optimal" relaxation;
- change more than one requirement in one sensitivity request;
- rank alternative requirements;
- label an alternative better/worse/recommended;
- generate an overall fit score, winner or probability;
- infer hidden preferences from prior Search activity.

The allowed interaction is:

```text
current explicit hard requirement(s)
+
buyer-selected one criterion
+
buyer-supplied replacement value
→ factual deterministic delta
```

A buyer may choose a numerically looser or tighter draft value, or a different accepted categorical keel value. HullQ does not assign value judgment to that choice.

## 3. Supported v0.1 criteria

Sensitivity supports only the hard public Direct Search criteria already owner-accepted on canonical main:

```text
draft_max
keel_configuration
```

It adds no third Search criterion.

The selected criterion MUST already be active in the current Search. v0.1 does not use sensitivity to add or remove a criterion.

Examples:

```text
current: draft_max=1.6
change:  draft_max -> 1.7
→ valid

current: draft_max=1.6&keel_configuration=FIN
change:  keel_configuration -> TWIN_KEEL
→ valid; draft_max stays exactly 1.6

current: draft_max=1.6
change:  keel_configuration -> FIN
→ invalid sensitivity request in v0.1 because keel_configuration was not active
```

Submitting the same canonical value as the current value is allowed and deterministically produces a zero set delta. It is not an error and must not be reworded as a recommendation.

## 4. Input truth and parsing

FastAPI remains the sole application/domain/Search semantic boundary.

Browser/Astro code may transport raw current/proposed values but MUST NOT:

- parse Decimal truth;
- normalize a proposed draft value;
- fuzzy-map a keel value;
- decide whether the proposed value is semantically valid;
- compute a Search result or delta.

The FastAPI/application path MUST reuse the same accepted parsing/canonicalization primitives as Direct Search:

- `draft_max` -> existing exact Decimal parser + canonical decimal formatter;
- `keel_configuration` -> the exact accepted six-value vocabulary.

Accepted keel values remain exactly:

```text
FIN
FIN_WITH_BULB
WING
CENTERBOARD
LIFTING_KEEL
TWIN_KEEL
```

No new criterion/value vocabulary is introduced.

## 5. FastAPI transport

The bounded API surface is:

```text
POST /api/search/{locale}/sensitivity
```

Supported locales remain exactly:

```text
en
de
fr
pt
es
```

The request body is conceptually:

```json
{
  "current": {
    "draft_max": "1.6",
    "keel_configuration": "FIN"
  },
  "change": {
    "criterion": "draft_max",
    "value": "1.7"
  }
}
```

Rules:

- `current` contains one or both currently accepted criteria and no unknown keys;
- at least one current criterion is required;
- `change.criterion` is exactly `draft_max` or `keel_configuration`;
- the changed criterion must be present in `current`;
- `change.value` is the raw buyer-supplied replacement value;
- caller-supplied result counts, listing IDs, canonical paths, Search outcomes, advice or scores are ignored/rejected and never trusted.

Equivalent strictly typed request-object organization is acceptable if these semantics remain identical.

This endpoint is read-only computation. It persists nothing and creates no account/session state.

## 6. One Search truth, evaluated twice

The sensitivity application service MUST evaluate:

```text
CURRENT requirements
and
ALTERNATIVE requirements
```

through the same accepted production Search evaluation used by `GET /api/search/{locale}`.

No second criterion evaluator, duplicate SQL truth predicate, TypeScript Search engine, explanation-text parser or approximate result model is allowed.

The alternative is constructed by replacing exactly one active criterion value while preserving every other current criterion unchanged.

Examples:

```text
current:
draft_max=1.6
keel_configuration=FIN

change:
draft_max=1.7

alternative:
draft_max=1.7
keel_configuration=FIN
```

and:

```text
current:
keel_configuration=FIN

change:
keel_configuration=TWIN_KEEL

alternative:
keel_configuration=TWIN_KEEL
```

## 7. Consistent evaluation boundary

The current and alternative evaluations form one factual comparison and MUST NOT be assembled from materially different inventory snapshots.

The implementation MUST use:

- one explicit timezone-aware `as_of` instant for both evaluations; and
- one consistent PostgreSQL transaction/snapshot boundary for both evaluations, or an equivalently strong mechanism proven by tests.

A listing becoming active/stale/changed between the two halves must not produce a delta that never existed in one coherent evaluation state.

This requirement does not authorize a new global snapshot framework.

## 8. Delta semantics

The only primary result set remains `CONFIRMED_MATCH`.

Sensitivity compares the stable `NativeListingId` sets of current and alternative confirmed results.

Required factual values:

```text
current_confirmed_match_count
alternative_confirmed_match_count

newly_confirmed_match_count
= |alternative confirmed IDs - current confirmed IDs|

no_longer_confirmed_match_count
= |current confirmed IDs - alternative confirmed IDs|

current_insufficient_data_count
alternative_insufficient_data_count
```

Hard:

```text
newly_confirmed_match_count
!=
max(0, alternative_total - current_total)
```

The set difference must be real. If one listing enters while another leaves, totals may remain equal while both delta counts are non-zero.

`INSUFFICIENT_DATA` remains separate. It MUST NOT be counted as a confirmed match, confirmed non-match or newly confirmed listing.

v0.1 does not need to expose individual confirmed-non-match or insufficient-data listing identities to the browser.

## 9. Alternative canonical Search path

The sensitivity result MUST provide the exact canonical public Direct Search path for the buyer-selected alternative, for example:

```text
/de/search?draft_max=1.7&keel_configuration=FIN
```

The canonical path MUST be built/owned by the Python/FastAPI Search boundary using the accepted:

- decimal canonicalization;
- sparse parameter rules;
- parameter ordering;
- locale prefix.

Astro/TypeScript MUST NOT build a competing canonical Search URL for the sensitivity result.

The browser may render this path as the explicit action equivalent to:

> View this search

Following it enters the ordinary accepted Direct Search route; sensitivity does not create a second Search identity.

## 10. API result shape

The sensitivity response contains the minimum factual comparison needed by the public UI, conceptually:

```json
{
  "locale": "en",
  "current_requirement": {
    "draft_max": "1.6",
    "keel_configuration": "FIN"
  },
  "alternative_requirement": {
    "draft_max": "1.7",
    "keel_configuration": "FIN"
  },
  "changed_criterion": "draft_max",
  "current_confirmed_match_count": 1,
  "alternative_confirmed_match_count": 3,
  "newly_confirmed_match_count": 2,
  "no_longer_confirmed_match_count": 0,
  "current_insufficient_data_count": 1,
  "alternative_insufficient_data_count": 1,
  "alternative_search_path": "/en/search?draft_max=1.7&keel_configuration=FIN"
}
```

Exact property naming may be concise, but every semantic value above must be represented explicitly and typed.

Do not return advice, recommendation labels, scores, "best" values or inferred user intent.

## 11. Invalid / unavailable behavior

At minimum:

- unsupported locale -> ordinary 404;
- malformed body -> 400;
- unknown current key -> 400;
- no active current criterion -> 400;
- unsupported changed criterion -> 400;
- changed criterion not active in current -> 400;
- malformed/unsupported proposed value -> 400;
- Search/database/backend failure -> unavailable/5xx class, not "invalid search" and not a zero-result sensitivity claim.

Current/proposed invalidity must be resolved before any result delta is shown.

Localized browser recovery copy may explain the input problem without changing the underlying language-neutral parameter/value semantics.

## 12. Public Astro surface

The canonical Direct Search page remains:

```text
/{locale}/search
```

When the Search page has an active valid criterion, it may render one sensitivity form per active criterion.

Examples:

- active `draft_max` -> text input for a buyer-supplied alternative draft;
- active `keel_configuration` -> exact six-value selector for a buyer-supplied alternative keel value;
- both active -> both separate forms; each request changes exactly one criterion.

Each form submits by native browser POST to:

```text
/{locale}/search/sensitivity
```

The form transports the current canonical active values plus exactly one changed criterion/value.

The SSR sensitivity page forwards the raw form values to FastAPI and renders only FastAPI's decision/result. It does not evaluate Search truth.

The sensitivity page must visibly distinguish:

- current requirements;
- buyer-selected alternative;
- current confirmed matches;
- alternative confirmed matches;
- newly confirmed;
- no longer confirmed;
- current vs alternative insufficient-data counts;
- explicit link to the canonical alternative Direct Search.

Copy must be factual. Avoid terms such as:

- recommended;
- better;
- worse;
- optimal;
- should;
- relax this;
- best fit.

## 13. URL / SEO boundary

SLICE-0057 MUST NOT expand the accepted canonical Direct Search GET query grammar.

The sensitivity transport is a POST companion tool, not another Search URL identity.

For `/{locale}/search/sensitivity`:

- POST result pages are deliberately `noindex`;
- do not add them to sitemaps;
- do not create hreflang/indexable sensitivity permutations;
- do not claim a separate canonical Search identity for the comparison state;
- the only canonical actionable Search state is the `alternative_search_path` returned by FastAPI.

A direct GET to the sensitivity page may return a bounded "start from Search" state or an ordinary method/not-found class; it must not manufacture a sensitivity result without posted input.

No broad/indexable SEO decision is made by this slice.

## 14. No persistence / account boundary

SLICE-0057 creates no:

- BuyerRequirements row;
- Saved Search;
- Monitor;
- Alert;
- Shortlist;
- buyer profile;
- anonymous durable intent object;
- account requirement.

Anonymous buyers may use the capability.

Signup remains a continuity boundary, not a discovery prerequisite.

## 15. Commercial independence

Sensitivity uses exactly the accepted organic Search evaluation.

Seller/broker payment, verification fees, subscription status, referral economics, advertising value or expected HullQ revenue MUST NOT affect:

- current Search eligibility;
- alternative Search eligibility;
- confirmed-match delta;
- ordering.

This preserves `REQ-PRIVATE-003`.

## 16. Retained real vertical proof

Retain one deterministic PostgreSQL 18 -> FastAPI -> built Astro SSR proof.

It must demonstrate at minimum:

1. a canonical current Search state using one or both accepted criteria;
2. a buyer-authored `draft_max` replacement changes the confirmed set;
3. unchanged active criterion(s) are preserved exactly;
4. the response's `newly_confirmed_match_count` is based on set difference rather than total-count arithmetic;
5. at least one same-total/different-membership case or equivalent focused test proves set-difference semantics;
6. a buyer-authored keel replacement works through the same capability;
7. insufficient-data count remains separate and never becomes a match;
8. same-value replacement yields a deterministic zero delta;
9. malformed draft replacement returns 400 and no sensitivity claim;
10. unsupported/tampered keel replacement returns 400;
11. changed criterion absent from current Search returns 400;
12. `alternative_search_path` is exact/canonical;
13. posting through a built locale Astro sensitivity page renders the factual delta and alternative Search link;
14. ordinary Direct Search behavior remains unchanged;
15. end with:

```text
BUYER REQUIREMENT SENSITIVITY RESULT -> PASS
```

CI must execute this proof in the normal PostgreSQL 18 integration path.

## 17. Tests

At minimum cover:

### Application/domain boundary

- exactly one current active criterion;
- mixed current requirements;
- draft change preserves keel;
- keel change preserves draft;
- same-value zero delta;
- newly confirmed set difference;
- no-longer-confirmed set difference;
- equal total with changed membership;
- insufficient-data separate;
- one `as_of` for both evaluations;
- consistent transaction/snapshot boundary;
- no persistence side effect.

### FastAPI

- supported locales;
- unsupported locale 404;
- valid body;
- malformed/unknown body 400;
- changed criterion not active 400;
- invalid draft 400;
- invalid keel 400;
- exact canonical alternative path;
- backend failure remains unavailable/5xx.

### Web

- sensitivity affordance only for active criteria;
- mixed Search shows two independent one-change forms;
- raw values are transported rather than re-evaluated;
- factual localized copy in all five locales;
- visible UNKNOWN/insufficient-data separation;
- no recommendation/score language;
- alternative Search link comes from FastAPI response;
- POST result is noindex;
- direct Search URL/canonicalization behavior remains unchanged.

## 18. Explicitly deferred

Not part of v0.1 / SLICE-0057:

- automatic "best relaxation";
- automatic suggested values;
- multi-criterion change;
- persisted BuyerRequirements;
- MUST_HAVE/PREFER/DONT_CARE authoring;
- preference scoring;
- saved sensitivity history;
- Shortlist/Compare;
- sharing;
- Saved Search/Monitor/alerts;
- personalized recommendations;
- Rare Match;
- third Search criterion;
- seller/broker sensitivity analytics;
- broad/indexable SEO;
- production pilot or real external production data.

Each remains subject to normal later reconciliation/readiness.

## 19. Acceptance summary

The accepted boundary is:

```text
buyer chooses one active criterion + one replacement value
→ same Search truth evaluated for current and alternative
→ same coherent inventory state
→ factual confirmed-set delta
→ UNKNOWN remains separate
→ canonical link to buyer-selected alternative Search
```

and never:

```text
HullQ chooses what to relax
or
HullQ recommends the alternative
or
HullQ creates a second Search engine
```.
