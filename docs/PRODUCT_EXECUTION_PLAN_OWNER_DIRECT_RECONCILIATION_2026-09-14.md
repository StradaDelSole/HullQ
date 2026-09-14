# HullQ Product Execution Reconciliation — Broker-First Mixed Supply

**Date:** 2026-09-14  
**Status:** OWNER-ACCEPTED EXECUTION RECONCILIATION when merged  
**Applies to:** all work after the SLICE-0053 acceptance closure  
**Purpose:** reconcile the owner-direct/private-listing pivot with earlier broker-only marketplace execution records without rewriting historical decisions

## Controlling decision

HullQ now builds a **broker-first mixed-supply** marketplace:

```text
professional broker/dealer inventory
+
bounded owner-direct/private seller inventory
```

The previous current-direction rule that independent private FSBO is prohibited is superseded.

This reconciliation does not erase why HullQ originally chose broker-only supply. It replaces the solution to those risks: Search commercial independence, explicit seller trust scopes, proportionate anti-fraud controls with risk escalation, representation-conflict semantics, neutral referral and a stronger mixed-supply broker value proposition.

## Precedence after 2026-09-14

For conflicting current product/execution instructions, use this precedence:

1. explicit later Project Owner decisions / accepted slice closures;
2. `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md` for mixed-supply/private-seller/Search-commercial-independence policy;
3. `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md` for normative owner-direct requirements;
4. `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` for non-superseded application/infrastructure architecture;
5. this 2026-09-14 reconciliation;
6. `docs/PRODUCT_EXECUTION_PLAN_NATIVE_LISTING_RECONCILIATION_2026-09-02.md` for non-conflicting historical marketplace/truth/execution rules;
7. older execution plans/ADRs where not superseded.

`docs/PRIVATE_SELLER_POLICY_2026-09-02.md` is historical decision context after this pivot and is no longer current supply authority.

Non-conflicting strict-truth, provenance, fail-closed, configuration-scope, physical-listing-scope, explicit `UNKNOWN`, source/media-rights, ONE-CAPABILITY, VISIBLE-RESULT, exact-head review/gates and slice-isolation rules remain fully in force.

## 1. What is superseded

The following older current-direction statements are superseded:

```text
public NativeListing supply is professional-only
private consumers may never publish public owner-direct listings
private-owner sale intent must use BrokerageRequest/referral only
private owner is only a referral source, not a public seller
no public FSBO path is part of the marketplace model
```

The earlier implementation remains professional-only until a bounded owner-direct capability is built. Product direction changed; code did not change automatically.

## 2. What remains valid from the native-marketplace pivot

The core native marketplace strategy remains intact:

```text
native HullQ inventory as strategic market foundation
+ optional rights-cleared external integrations
+ deterministic technical Search
+ strict physical-boat/listing truth
+ provenance
+ monitoring / alerts
+ trust-first contact/lead handling
```

External marketplace scraping/access is not restored as a foundational dependency by owner-direct supply.

## 3. Marketplace identity / truth remains unchanged

The accepted identity boundary remains:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
```

and:

```text
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

Owner-direct seller verification does not change those rules.

Additional seller trust scopes are separate from vessel truth:

```text
PHONE VERIFIED
IDENTITY VERIFIED
RIGHT-TO-LIST ATTESTED
SALE AUTHORITY VERIFIED
```

No seller-level trust status mass-promotes technical fields.

## 4. Organic Search commercial independence is a hard execution invariant

From this pivot onward, every Search/readiness/monetization decision must preserve:

```text
commercial consideration MUST NOT affect
organic eligibility
organic match classification
organic ordering
```

This applies equally to professional and owner-direct inventory.

Broker plan tier, private-seller payment, verification fee, referral economics, affiliate value, expected commission and advertising relationship are not organic Search inputs.

Payment may purchase a real verification/inspection/document-processing service; equivalent admissible evidence must resolve equivalently regardless of payment source.

## 5. Private seller entry is low-friction but evidence-bounded

The accepted normal future publication baseline is:

```text
HullQ account
+ verified phone reachability
+ explicit right-to-list attestation
+ baseline anti-abuse checks
```

The following are not universal Day-1/publication requirements:

- ID-document + selfie/liveness verification;
- vessel ownership-document upload;
- physical presence at the boat;
- physical code/photo challenge.

Stronger identity or documentary sale-authority evidence may be required on structured risk escalation or dispute.

The exact implementation owner for escalation may initially be manual at low volume; later rules/hybrid automation must be justified by observed need.

## 6. Fraud controls must not become speculative infrastructure

Initial controls should use low-cost evidence available in the active system, such as:

- phone/account reuse patterns;
- account/listing velocity;
- suspicious volume for a private seller;
- reliable price anomalies where data supports them;
- user reports/moderation evidence.

A conflicting HullQ MarketEpisode/representation state is usable only once identity/representation conflict resolution exists.

Perceptual image hashing, external stolen-image matching and generalized fraud scoring are later bounded capabilities, not implicit prerequisites for the first owner-direct slice.

## 7. Verification privacy boundary

If strong identity verification is later implemented, prefer provider-bounded verification rather than HullQ retaining raw ID/selfie/biometric artifacts.

The owning capability must explicitly define:

- provider/raw-data boundary;
- HullQ-retained result/reference/method/timestamp data;
- lawful basis / consent or other legal basis as applicable;
- retention/deletion;
- user-rights handling;
- security/incident implications.

No current decision authorizes indefinite raw identity-document/biometric storage by HullQ.

## 8. Representation conflict is a domain problem, not a UI dedup trick

The earlier concern about duplicate owner/broker listings remains real but is no longer solved by prohibiting owner-direct supply.

Future logic must reason through:

```text
PhysicalBoat
→ MarketEpisode
→ representation / sale authority context
→ NativeListing(s) where legitimate
```

Do not introduce a blanket `one NativeListing per PhysicalBoat` invariant.

The eventual capability must distinguish active mandate, ended mandate, legitimate multi-representation where allowed, uncertain boat/episode identity and disputed authority. Fail closed rather than silently deleting/overwriting one side.

## 9. Referral remains a first-class voluntary path

The useful parts of the 2026-09-02 referral policy remain valid after the pivot:

```text
seller explicitly chooses referral
→ deterministic eligible shortlist
→ transparent waves/status
→ seller chooses broker
```

Referral ordering remains separate from buyer Search ranking and must remain non-pay-to-win. A broker subscription/payment cannot buy shortlist priority.

Referral exhaustion no longer forbids an owner-direct alternative; seller choice exists independently.

## 10. Broker-first still means strong broker product

The mixed-supply pivot does not reduce professional commitments.

The Broker Workspace must continue toward a product brokers prefer to use because it provides:

- technically qualified demand;
- preserved broker/Organization branding;
- excellent inventory operations;
- no duplicate data entry where safe reuse exists;
- durable lead attribution/workflow;
- performance analytics;
- seller-to-broker referral opportunities;
- no paid organic ranking.

`docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`, `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`, the Broker Workspace Launch Gate and Mandatory Capability Register remain controlling.

## 11. Monetization reconciliation

The former assumption `Private Owner as Referral Source (not public seller)` is superseded.

Current actor set includes:

```text
Buyer
Professional Broker / Dealer / Supply Organization
Private / Owner-Direct Seller
Professional/Data Customer (possible later)
```

Current owner-direct commercial direction:

```text
basic self-listing -> free
optional verification/processing service -> may be paid
voluntary broker referral -> later success/referral economics possible
relevant transaction partners -> later affiliate/partner economics possible
```

Organic Search remains non-commercial regardless of pricing model.

A sponsored/featured ad surface is deferred, not categorically prohibited. If later authorized, it must be separate from organic results and cannot consume/manipulate organic positions.

## 12. Transaction safety opportunity

A vetted third-party escrow/transaction-safety partner is a later opportunity, not part of the current implementation baseline.

HullQ does not become custodian of transaction funds without a separate owner-accepted regulatory/legal/architecture/business decision.

Seller verification and buyer transaction safety remain distinct product concerns.

## 13. Production-readiness reconciliation

Earlier Production Readiness / HA wording that named only `broker` data/inventory must now be interpreted and amended supply-neutrally.

Before real external professional OR owner-direct seller/listing data is relied upon as production data, the Production Readiness trigger applies.

Before real external marketplace inventory of either supply type is exposed to real external buyers, the accepted HA threshold applies.

No owner-direct path may use legacy broker-specific wording to bypass production/security/abuse controls.

## 14. Execution sequencing after SLICE-0053

SLICE-0053 is accepted and closed.

Current queue is:

```text
SLICE-0054
```

The pivot does **not** select 0054.

Before selecting 0054, reassess actual repository state across three product perspectives:

```text
Buyer value / technical discovery
Professional broker value / mandatory commitments
Private seller value / owner-direct requirements
```

Then choose the smallest highest-leverage visible capability under the ONE-CAPABILITY rule.

Possible capabilities mentioned in strategy discussion are not allocated to slice numbers merely by appearing here or in product direction.

## 15. Readiness obligation

For SLICE-0054 and later, any work touching listing/supply, seller identity/verification, representation conflict, referral, marketplace monetization or Search must include the owner-direct direction/spec in its decision/implementation reconciliation.

Readiness must explicitly distinguish:

```text
accepted direction
already implemented behavior
accepted-but-unimplemented obligations
exact new gap
```

It must not reinterpret current professional-only implementation as evidence that owner-direct remains prohibited.

## Controlling one-sentence direction

> **HullQ will build a native broker-first mixed-supply sailboat marketplace whose core advantage is deterministic configuration-aware Search, strict PhysicalBoat/MarketEpisode/listing truth and evidence-bounded trust: professional inventory and the Broker Workspace remain strategically central, private sellers may choose owner-direct listing or neutral broker referral, organic Search is permanently non-commercial, and every new capability follows the accepted truth, security, production-readiness and one-capability workflow.**
