# HullQ Private Seller Policy — Broker-Only Public Supply

**Date:** 2026-09-02  
**Status:** HISTORICAL — SUPERSEDED AS CURRENT SUPPLY POLICY on 2026-09-14  
**Superseded by:** `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md` and `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`  
**Historical scope:** native marketplace public supply and private-owner intake as decided on 2026-09-02

> **Current-direction warning:** the broker-only / no-public-FSBO rules below are retained as decision history. They MUST NOT be used as current authority after the 2026-09-14 owner-accepted broker-first mixed-supply pivot. Current direction allows bounded owner-direct/private listings while preserving the referral path, non-commercial organic Search, seller-trust boundaries and the still-mandatory Broker Workspace commitments.

## 1. Phase-1 public supply rule — historical decision

HullQ Phase 1 was originally decided as strictly **broker/dealer/eligible-professional-only** on the public listing supply side.

Private consumers were not permitted to publish independent public `NativeListing` records that compete with professional broker inventory.

This was a domain authorization rule, not only a UI policy.

Historical invariant:

> Every publicly published `NativeListing` must have an eligible professional Organization as its publishing principal.

Private accounts did not receive a public NativeListing publishing capability under this 2026-09-02 direction.

## 2. Rationale at the time

HullQ intentionally sought to avoid the broker-channel conflict created when a marketplace asks brokers to pay/integrate supply while simultaneously selling equivalent public exposure directly to their potential seller customers.

Additional reasons recorded at the time:

- private-sale fraud, impersonation, fake escrow, overpayment and ownership-verification risk;
- materially greater moderation/identity/ownership-verification burden;
- weaker professional accountability layer;
- unnecessary Phase-1 regulatory/product complexity from mixing professional traders and private sellers;
- preservation of broker trust as a strategic supply-acquisition requirement.

Professional supply was not treated as automatically truthful; HullQ truth/provenance rules still applied to broker claims.

The 2026-09-14 pivot did not erase these risks; it adopted a different solution: broker-first mixed supply, non-commercial organic Search, explicit seller trust scopes, low-friction baseline controls plus risk escalation, and a stronger mixed-supply broker value proposition.

## 3. Private owner path — historical referral-only direction

Private owners were originally limited to a separate `BrokerageRequest` / referral request.

Conceptual flow:

```text
private owner
→ BrokerageRequest
→ deterministic eligible broker shortlist
→ broker responses
→ owner chooses broker
→ possible brokerage mandate
```

A BrokerageRequest was **not** a NativeListing and was not to be silently transformed into one.

Under the current 2026-09-14 direction this referral path remains valid, but it is now one voluntary option alongside owner-direct self-listing.

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

Current direction additionally requires referral selection/order to remain commercially neutral; broker payment/subscription tier cannot buy shortlist preference.

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

The former statement that HullQ must never create/publicize owner-direct inventory as an alternative is superseded; current direction allows the seller to choose owner-direct independently of referral exhaustion.

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

Hard separation remains valid and is strengthened by the 2026-09-14 pivot:

```text
seller-referral broker ordering
≠
organic buyer listing/search relevance
```

A broker's referral response speed, referral outcome or payment must never improve organic buyer-search ranking.

The referral system is non-pay-to-win.

## 9. Transparency

HullQ should publicly document the factual principles used to distribute private-owner referral opportunities.

The purpose is to avoid black-box favoritism and create a clear broker trust promise.

## 10. Historical Phase-1 monetization rule

The 2026-09-02 policy did not introduce public FSBO listing fees because public private listings were outside that model.

Current 2026-09-14 direction instead sets free basic owner-direct self-listing as the baseline and permits optional verification/processing services, neutral later referral economics and relevant partner services without paid organic ranking.

## 11. Historical Pre-Gate-1 implementation scope

The prior architecture/authorization boundary was:

```text
private consumer
cannot publish public NativeListing

private-owner sale intent
→ BrokerageRequest
≠ NativeListing
```

That remains an accurate description of the **currently implemented professional-only write path**, but it is no longer the target product policy. A future bounded owner-direct capability must add the correct private-seller authorization/trust path rather than bypassing or faking professional eligibility.

The ONE-CAPABILITY rule remains controlling.

## 12. Known later extension

Co-brokerage / buyer-broker vs seller-broker relationships remain known domain concerns.

The 2026-09-14 pivot additionally makes professional-vs-owner-direct representation conflict a current accepted design obligation: resolution belongs around `PhysicalBoat → MarketEpisode → representation/sale-authority context`, not a naïve permanent one-listing-per-boat rule.
