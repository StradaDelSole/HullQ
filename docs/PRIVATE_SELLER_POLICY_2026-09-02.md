# HullQ Private Seller Policy — Broker-Only Public Supply

**Date:** 2026-09-02  
**Status:** ACCEPTED OWNER DIRECTION — controlling when merged  
**Applies to:** native marketplace public supply and private-owner intake

## 1. Phase-1 public supply rule

HullQ Phase 1 is strictly **broker/dealer/eligible-professional-only** on the public listing supply side.

Private consumers may not publish independent public `NativeListing` records that compete with professional broker inventory.

This is a domain authorization rule, not only a UI policy.

Invariant:

> Every publicly published `NativeListing` must have an eligible professional Organization as its publishing principal.

Private accounts do not receive a public NativeListing publishing capability.

## 2. Rationale

HullQ intentionally avoids the broker-channel conflict created when a marketplace asks brokers to pay/integrate supply while simultaneously selling equivalent public exposure directly to their potential seller customers.

Additional reasons:

- private-sale fraud, impersonation, fake escrow, overpayment and ownership-verification risk;
- materially greater moderation/identity/ownership-verification burden;
- weaker professional accountability layer;
- unnecessary Phase-1 regulatory/product complexity from mixing professional traders and private sellers;
- preservation of broker trust as a strategic supply-acquisition requirement.

Professional supply is not treated as automatically truthful; HullQ truth/provenance rules still apply to broker claims.

## 3. Private owner path

Private owners may submit a separate `BrokerageRequest` / referral request.

Conceptual flow:

```text
private owner
→ BrokerageRequest
→ deterministic eligible broker shortlist
→ broker responses
→ owner chooses broker
→ possible brokerage mandate
```

A BrokerageRequest is **not** a NativeListing and must not be silently transformed into one.

## 4. Initial broker eligibility

Initial shortlist eligibility should use simple explainable criteria:

```text
service/geographic area
AND
vessel specialization
AND
accepted deal segment
```

The accepted deal segment may include vessel-length and/or value ranges declared by the broker.

No ML-based matching is required initially.

## 5. Referral waves

A request may be broadcast to a short deterministic group of eligible brokers, for example 3–5 at a time.

The private owner chooses which responding broker to engage.

HullQ does not secretly award the seller to a favored broker.

Initial response window direction:

```text
approximately two business days
```

rather than a blind literal 48-hour timer across weekends.

Meaningful response states may include:

```text
INTERESTED
DECLINED
NEED_MORE_INFORMATION
```

Opening an email is not a response.

If response is insufficient, the next eligible broker wave may be invited.

## 6. Referral exhaustion

A request must have an explicit terminal state if no eligible/interested broker remains:

```text
EXHAUSTED
```

The private owner receives an honest status and may be offered actions such as:

```text
REQUEST_UPDATE
RETRY_LATER
CLOSE_REQUEST
```

The request must not silently disappear.

HullQ must not create a public FSBO listing as fallback.

## 7. Anti-gaming / response quality

A broker clicking `INTERESTED` does not by itself prove meaningful engagement and must not automatically create a positive referral-performance signal.

A later bounded capability may collect lightweight outcome evidence such as:

```text
broker INTERESTED
→ owner confirms whether real contact occurred
→ optional owner confirmation whether broker was selected
```

Referral-quality signals remain internal unless a separate explicit product decision authorizes public presentation.

## 8. Referral ordering vs buyer search ranking

Hard separation:

```text
seller-referral broker ordering
≠
organic buyer listing/search relevance
```

A broker's referral response speed or referral outcome must never improve organic buyer-search ranking.

The referral system is non-pay-to-win.

## 9. Transparency

HullQ should publicly document the factual principles used to distribute private-owner referral opportunities.

The purpose is to avoid black-box favoritism and create a clear broker trust promise.

## 10. Phase-1 monetization rule

HullQ does not introduce public FSBO listing fees in Phase 1 because public private listings are not part of the Phase-1 marketplace model.

A future referral/success-fee model may be evaluated separately, but no such monetization is currently controlling.

## 11. Pre-Gate-1 implementation scope

The architecture and authorization boundary must be correct before Gate 1:

```text
private consumer
cannot publish public NativeListing

private-owner sale intent
→ BrokerageRequest
≠ NativeListing
```

The complete automated referral workflow does not need to be implemented inside the first marketplace slice and may remain post-Gate-1 if not required for the core buyer-marketplace validation.

The ONE-CAPABILITY rule remains controlling.

## 12. Known later extension

Co-brokerage / buyer-broker vs seller-broker relationships are known future domain concerns.

They are not part of the Phase-1 private-owner referral implementation and must not expand the current scope.
