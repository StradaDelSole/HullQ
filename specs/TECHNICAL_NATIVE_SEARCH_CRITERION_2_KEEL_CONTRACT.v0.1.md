# HullQ — Technical Native Search Criterion #2: Keel Configuration Contract v0.1

**Status:** READY FOR IMPLEMENTATION REVIEW  
**Slice:** SLICE-0055  
**Depends on:** accepted SLICE-0035 configuration-aware categorical Search; accepted SLICE-0051 production native Search

## 1. Purpose

Add `keel_configuration` as HullQ's second public hard technical native-inventory Search criterion and prove that the accepted production Search path supports a mixed numeric + categorical MUST query without duplicating the SLICE-0051 field-specific bridge architecture.

The public Direct Search remains primary. This contract does not implement BuyerRequirements persistence or guided Search.

## 2. Required query semantics

The production Search MUST support:

```text
draft_max=<exact positive decimal metres>
keel_configuration=<accepted canonical search value>
```

Each criterion MAY be used alone. When both are supplied they are MUST leaves combined by deterministic AND semantics already defined by `SEARCH_QUERY_SEMANTICS.v0.1` and the accepted mixed configuration Search kernel.

Criterion-level evaluation evidence MUST be preserved through the production application outcome for `CONFIRMED_MATCH`, `CONFIRMED_NON_MATCH`, and `INSUFFICIENT_DATA`; the implementation MUST NOT reduce non-match/unknown evidence to counts only.

No score, ranking, preference weighting, recommendation, fuzzy matching, synonym matching at evaluator time, OR/NOT, or PREFER semantics is introduced.

## 3. Keel truth boundary

BoatDesign/configuration truth and PhysicalBoat truth remain separate.

Design-side source field is the accepted BoatDesign v0.6 appendage meaning `appendages.keel_type`, including explicit NamedVariant overrides where safely resolvable. Mere schema-valid JSON presence is not confirmed Search truth; the same FieldResolution/current-resolution discipline proven by SLICE-0051 applies.

PhysicalBoat-side source is the accepted marketplace `keel_configuration` claim. Concrete-yacht truth may confirm or contradict design/configuration eligibility. A contradiction MUST prevent a confirmed listing match. Missing, provisional, conflicting, stale, or otherwise unresolved evidence MUST fail closed and MUST NOT be guessed.

## 4. Normative taxonomy mapping

Design taxonomy and PhysicalBoat marketplace taxonomy are not assumed identical. Implementation MUST use one explicit, reviewed mapping table owned by this contract/its implementation, never string similarity or ad-hoc inference.

The minimum accepted direct mappings are:

| BoatDesign `keel_type` | Search / PhysicalBoat `keel_configuration` |
| --- | --- |
| `full` | `LONG_KEEL` |
| `fin` | `FIN` |
| `wing` | `WING` |
| `bulb` | `FIN_WITH_BULB` |
| `centerboard` | `CENTERBOARD` |
| `lifting` | `LIFTING_KEEL` |
| `twin` | `TWIN_KEEL` |
| `bilge` | `TWIN_KEEL` |

The following BoatDesign values are NOT authorized by v0.1 for an inferred marketplace mapping and therefore fail closed unless a future reviewed contract adds an explicit rule: `modified_full`, `long_fin`, `daggerboard`, `swing`, `shoal`, `other`, `unknown`.

An explicit canonical marketplace value remains usable as PhysicalBoat truth according to the existing claim contract; this table only governs BoatDesign/configuration eligibility projection.

## 5. Configuration scope

The production bridge MAY project:

- BoatDesign baseline;
- NamedVariants whose keel override/inheritance and dependencies can be resolved under the existing accepted configuration boundary.

It MUST NOT automatically enumerate or invent `design_options` combinations. A NamedVariant with unresolved required DesignOptions cannot be promoted into the trusted resolved set merely to make keel Search work.

`configuration_space_complete` MUST NOT be asserted unless the existing configuration contract's proof conditions are genuinely met. No new completeness inference is authorized.

## 6. Abstraction requirement

SLICE-0055 is criterion #2 and therefore MUST satisfy the accepted post-0051 second-criterion bridge comparison.

The implementation MUST identify and reuse/generalize the common production responsibilities currently embedded in the `draft_max` path, including where applicable:

- canonical subject lookup;
- FieldResolution qualification/current-snapshot agreement;
- baseline + safely resolvable NamedVariant projection;
- configuration identity preservation;
- mixed criterion evaluation;
- design eligibility feeding concrete native inventory evaluation;
- criterion-level evidence projection.

A second structurally copied `keel_*_design_bridge.py` implementing the same lifecycle independently is not acceptable. Criterion-specific field pointers, decoding, taxonomy mapping and value construction may remain criterion adapters behind a shared boundary.

The implementation MUST preserve existing `draft_max` behavior and exact Decimal semantics.

## 7. Result/evidence contract

For every evaluated criterion the production outcome MUST retain enough typed information to identify at least:

- criterion/field identity;
- requested value/comparison;
- resulting truth (`TRUE`, `FALSE`, `UNKNOWN` or equivalent accepted typed state);
- reason code where applicable;
- resolved/observed canonical value when safely available;
- relevant resolved configuration identity where design/configuration evaluation is involved.

This is an evidence foundation, not a buyer-facing recommendation. A later explainability projection may consume it without re-evaluating Search truth.

## 8. Public/API behavior

Invalid `keel_configuration` values fail closed as a client validation error and never silently normalize to another category.

A request containing only `draft_max` MUST retain accepted SLICE-0051 behavior. A request containing only `keel_configuration` MUST use the same native-inventory truth funnel. A request containing both MUST require both criteria to be confirmed satisfied for a primary confirmed match.

Unknown/insufficient data never enters the primary confirmed-match result set.

## 9. Explicitly out of scope

- automatic DesignOption combination expansion;
- BuyerRequirements domain/persistence;
- `PREFER` / `DONT_CARE`;
- guided buyer journey;
- sensitivity analysis or `Why no match?` UI;
- shortlist, Compare or sharing;
- Saved Search, alerts or monitoring;
- Rare Match;
- comparable/sister-vessel logic;
- Broker Search Intelligence;
- ranking or recommendation;
- owner-direct publication/admission;
- new production pilot or external production data.

## 10. Acceptance proof

Retained PostgreSQL-backed proof MUST demonstrate at least:

1. `draft_max` alone remains correct;
2. `keel_configuration` alone yields confirmed match/non-match/insufficient-data cases;
3. mixed `draft_max AND keel_configuration` evaluates both leaves and admits only confirmed joint matches;
4. a PhysicalBoat keel contradiction blocks a design-eligible listing;
5. missing/unresolved design or PhysicalBoat keel truth does not become a false claim or confirmed match;
6. an unsupported BoatDesign keel mapping fails closed;
7. a NamedVariant inheritance/override case is deterministic and evidence-qualified;
8. unresolved DesignOption dependency is not automatically expanded;
9. criterion-level evidence survives the production application boundary for match, non-match and insufficient-data outcomes;
10. existing SLICE-0051 retained behavior and tests remain green.
