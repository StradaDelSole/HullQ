# HullQ Product Success & Customer Priority

**Date:** 2026-09-11  
**Status:** ACCEPTED OWNER DIRECTION  
**Applies to:** post-SLICE-0050 product/architecture reassessment and all subsequent native-marketplace capability selection, readiness, implementation review and product-surface work  
**Preserves:** strict truth/provenance/UNKNOWN/CONFLICT semantics, one-capability slicing, visible-result discipline and accepted architecture boundaries

## Purpose

HullQ is not being built merely to reach feature parity with existing boat marketplaces. Product execution must optimize for a materially better experience for both serious buyers and professional brokers, create a defensible advantage over generic marketplaces, maximize the probability of commercial success and maintain exceptional implementation quality.

These are first-order product constraints, not later polish.

## Controlling priority

When two technically valid execution paths compete, prefer the path that best satisfies:

```text
truth-safe
+ materially easier for the serious buyer
+ materially easier for the professional broker
+ meaningfully differentiated from generic boat marketplaces
+ visible / actionable product value
+ evidence that the primary marketplace loop advances
+ exceptional implementation quality
```

A commodity marketplace-parity capability MUST NOT outrank a differentiated HullQ capability unless the commodity capability is a demonstrated prerequisite for the buyer/broker loop, supply acquisition or safe operation.

## Buyer standard

HullQ should reduce research effort, uncertainty and false confidence.

A serious buyer should be able to understand quickly:

```text
what I required
what HullQ applied
why this design/configuration qualifies
what is actually known about this concrete boat
what remains UNKNOWN or CONFLICTING
why this listing is or is not a confirmed fit
what useful action I can take next
```

Technical sophistication belongs in the system; database complexity must not be pushed onto the customer.

Customer friendliness MUST NOT be achieved by weakening hard requirements, hiding missing evidence or turning UNKNOWN/CONFLICT into convenient matches.

## Broker standard

Professional supply is a strategic marketplace input, so broker usability is a product requirement.

HullQ should minimize unnecessary work for brokers while preserving durable truth and auditability:

- avoid duplicate data entry where an accepted safe reuse path exists;
- make correction/update flows simple and non-destructive;
- preserve claim attribution and never silently overwrite one Organization with another;
- make missing/conflicting information understandable and remediable;
- provide transparent lead/listing value rather than artificial lock-in;
- avoid unnecessary exclusivity or workflow friction;
- progressively support practical broker supply paths rather than forcing all integration sophistication at once.

Strict truth is not an excuse for hostile broker UX. Broker friendliness is achieved through good workflow design, not by weakening provenance or conflict semantics.

## Competitive-advantage standard

HullQ's accepted core advantage is the combination of:

```text
technical requirements
→ deterministic configuration-aware Search
→ native professional inventory
→ concrete PhysicalBoat/listing truth
→ explicit UNKNOWN/CONFLICT semantics
→ save / monitor / alert
→ qualified broker action
```

Capability selection should strengthen this loop before cloning generic filters, generic listing chrome or other commodity features that competitors already provide adequately, unless those features are required to make the differentiated loop usable.

## Success orientation

Architecture and slice decisions should optimize for evidence of real product progress, not volume of implemented infrastructure.

Prefer bounded capabilities that:

- produce an inspectable buyer/broker outcome;
- reduce a real task or uncertainty;
- test or strengthen HullQ-specific product advantage;
- improve native inventory usefulness or broker participation;
- create a clear bridge to the next marketplace action;
- generate evidence that can inform the next product decision.

Do not treat market demand for online boat search as the unresolved hypothesis. Existing category demand and the marketplace model are already validated. The remaining commercial questions are HullQ-specific advantage, buyer behavior/adoption, native inventory acquisition, broker participation and sustainable unit economics.

## Exceptional-quality standard

"Fast" does not mean disposable implementation.

Every production capability must remain:

- semantically correct against accepted domain/search contracts;
- deterministic and explainable where truth/eligibility is involved;
- fail-closed where evidence is insufficient;
- auditable and provenance-preserving;
- tested at the behavior boundary that matters;
- reliable under persistence/concurrency/error conditions relevant to the slice;
- clear and usable on the customer-facing surface;
- international-by-design where public product semantics are involved;
- secure and privacy-conscious where identity/contact/publishing is involved;
- simple enough architecturally that unnecessary infrastructure does not slow future product iteration.

Quality is measured by correctness and customer usefulness together. A technically elegant capability that creates little buyer/broker value is not automatically high quality, and a polished UX that weakens truth semantics is unacceptable.

## Requirement for future reassessment/readiness

From the current post-SLICE-0050 reassessment onward, every proposed primary native-marketplace capability must be challenged with these questions before readiness:

1. **Buyer:** what serious-buyer task becomes materially easier or safer?
2. **Broker:** what is the effect on professional supply friction/value?
3. **Advantage:** why is this better or more distinctive than generic marketplace behavior?
4. **Success evidence:** what inspectable evidence will tell us the capability advanced the marketplace loop?
5. **Quality:** which accepted truth/architecture/UX boundaries must the implementation prove it preserved?

A proposal that cannot answer these questions requires stronger justification before it outranks a capability that can.

## Relationship to existing accepted direction

This document reinforces rather than replaces:

- `docs/ARCHITECTURE_REBASELINE_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md`;
- `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_MARKET_DECISION_2026-09-01.md`;
- `docs/PRODUCT_UX_PRINCIPLES.md`;
- `docs/governance/DECISION_IMPLEMENTATION_RECONCILIATION.md`;
- accepted Search and marketplace-fact semantics.

Where customer convenience conflicts with truth, safety, authorization or provenance, those hard boundaries remain controlling. The product goal is to make strict truth dramatically easier to use, not to relax it.

## Controlling principle

> **HullQ should win by making rigorous technical yacht discovery and trustworthy native inventory substantially easier for buyers and brokers than generic marketplaces do, while maintaining exceptional product and engineering quality.**
