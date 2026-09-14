# HullQ — Owner-Direct Listing Product Direction

**Date:** 2026-09-14  
**Status:** OWNER-ACCEPTED PRODUCT DIRECTION when merged  
**Scope:** marketplace supply model, owner-direct/private seller listings, Search independence, seller trust/fraud controls, referral neutrality and mixed-supply broker value  
**Normative requirements:** `specs/OWNER_DIRECT_LISTING_REQUIREMENTS.v0.1.md`

## 1. Decision and supersession

HullQ is no longer broker-only.

The previous current-direction rule that Phase-1 public supply is limited to brokers/dealers/eligible professionals and that independent private FSBO is out of scope is explicitly superseded by this decision.

HullQ is now a **broker-first mixed-supply marketplace**:

```text
professional broker/dealer inventory
+
bounded owner-direct/private seller inventory
```

Professional supply remains strategically central. The Broker Workspace remains one of HullQ's two core product surfaces and all accepted Broker Workspace requirements, launch gates and mandatory commitments remain in force.

Owner-direct supply is an additional first-class marketplace path, not a replacement for brokers and not a hidden downgrade of the broker product.

This product-direction change does **not** itself implement private listing code, select SLICE-0054, authorize a production private-seller launch or bypass existing Production Readiness / Broker Workspace governance.

## 2. Seller choice: self-list or broker referral

A private seller must have a genuine choice:

```text
A. list directly on HullQ
OR
B. ask HullQ to refer suitable professional brokers
```

Neither path is preselected or made artificially difficult to force the other.

A seller who intentionally wants to avoid a broker must not be sent through a broker-only funnel. A seller who wants professional representation must have a clear broker-referral path.

The two paths may share accepted HullQ identity, PhysicalBoat and MarketEpisode context where semantically safe, but must not collapse representation/sales-authority truth.

## 3. Organic Search is permanently non-commercial

Commercial consideration must never influence HullQ's organic Search truth.

The following are non-commercial product invariants:

```text
organic eligibility
organic match classification
organic ordering
```

A broker subscription, private-seller payment, affiliate value, referral fee, expected commission, advertiser relationship or any other HullQ revenue opportunity MUST NOT improve or worsen those three organic Search decisions.

HullQ must never sell an organic ranking boost, hidden relevance boost, paid eligibility exception or subscription-tier Search preference.

Objective user-selected sort, objective fit to explicit requirements, location/distance, price, recency or other future non-commercial ordering logic may be introduced only through an accepted Search decision. Any such logic must remain independent of seller payment/revenue value.

This is a hard governance rule. Changing it requires an explicit later Project Owner decision that acknowledges it is superseding this principle; it may not happen through an ordinary pricing experiment.

## 4. Paid verification improves service/evidence, never truth by purchase

Payment must not buy `CONFIRMED`, Search eligibility or any stronger truth status.

HullQ may charge for a verification service, document processing, third-party inspection, identity check or other convenience. The resulting evidence is evaluated under the same rules as equivalent evidence supplied without payment.

The controlling rule is:

> **Payment may buy a verification service. Payment never buys a truth result.**

If two sellers provide materially equivalent admissible evidence, HullQ must reach the same truth/evidence outcome regardless of whether one paid HullQ or a partner to produce/process that evidence.

## 5. Truth scopes and badge hierarchy must remain separate

HullQ must not collapse different trust questions into one generic `Verified Listing` or `Verified Seller` claim.

At minimum these concepts are distinct:

```text
PHONE VERIFIED
= reachable/control-verified phone number; anti-spam/reachability signal only

IDENTITY VERIFIED
= a stronger identity check has been completed by an accepted verification process/provider

RIGHT-TO-LIST ATTESTED
= the seller explicitly states that they are authorized to offer this vessel for sale

SALE AUTHORITY VERIFIED
= documentary/third-party evidence supports the seller's authority to offer the specific vessel
```

None of those statuses establishes all technical facts about the yacht.

Technical vessel truth remains field-/claim-level under HullQ's existing marketplace truth model, for example:

```text
draft              = CONFIRMED
year                = OWNER_DECLARED
engine_hours        = OWNER_DECLARED
VAT/document status = UNKNOWN
```

A badge or label must state exactly what HullQ has evidence for and must not imply broader verification.

The UI may use a visually strongest / gold-level badge treatment for `SALE AUTHORITY VERIFIED`, because it represents the strongest seller-authority evidence tier, but the visible label and explanatory copy must remain evidence-specific. Gold styling never means that the entire listing, vessel identity or technical specification set has been independently verified.

`Sale Authority Verified` is preferred over `Ownership Verified` because a legitimate seller may be an owner, co-owner, authorized company representative, estate representative or another properly authorized party.

## 6. Normal owner-direct publication gate

The normal unflagged owner-direct publish path must be low-friction.

A future public owner-direct listing may become publishable after at least:

```text
HullQ account
+ verified phone reachability
+ explicit right-to-list attestation
+ baseline anti-abuse checks
```

A documentary ownership/right-to-list check, strong ID/selfie verification or physical visit to the yacht is **not** a universal publication prerequisite.

This explicitly supersedes earlier discussion variants that would have required boat documents or a physical boat challenge for every seller before publication.

The attestation must cover authority to list/sell, not merely legal ownership, so legitimate authorized representatives are not incorrectly excluded.

Exact legal wording/jurisdictional effect of that attestation must be reviewed before production; product documentation must not overstate its legal effect.

## 7. Risk-based escalation

HullQ may require stronger verification when structured risk signals, disputes or moderation evidence warrant it.

The intended proportional model is:

```text
normal/unflagged
→ phone verification + right-to-list attestation

material risk signal
→ stronger identity verification may be required

strong conflict / fraud report / disputed authority
→ documentary sale-authority evidence may be required
```

Early low-volume operation may use manual review. A later rules engine or hybrid process is optional and must be justified by observed scale/risk rather than built prematurely.

Low-cost early signals may include:

- repeated phone use across suspicious accounts/listings;
- abnormal account/listing velocity;
- unusual numbers/patterns of listings for a private seller;
- strongly implausible price deviation where reliable comparison data exists;
- user reports or moderation evidence.

A conflicting HullQ MarketEpisode/representation state may become a strong signal only after the representation-conflict/boat-identity path is actually implemented; it must not be treated as a trivial Day-1 lookup before that capability exists.

Perceptual-image hashing, external stolen-image matching and generalized fraud scoring are later capabilities, not implicit MVP requirements.

## 8. Data minimization for strong identity verification

If HullQ later uses ID-document/selfie/liveness verification, the preferred architecture is provider-bounded and data-minimizing.

Where feasible:

```text
verification provider performs raw document/biometric processing
→ HullQ receives bounded result/reference/method/timestamp
→ HullQ stores only data necessary for the product/security/legal purpose
```

HullQ should avoid becoming the long-term store for raw identity documents, selfies or biometric material unless a separately reviewed requirement and legal basis explicitly require it.

Provider selection, lawful basis, retention, user rights and regional constraints must be reviewed before production activation.

## 9. Representation conflict: one sales episode cannot be flattened into duplicate channels

HullQ must prevent a private owner-direct path and professional-representation path from becoming conflicting duplicate truth for the same sale merely because two NativeListings exist.

The rule must be modeled through HullQ's accepted identity boundaries:

```text
PhysicalBoat
→ MarketEpisode
→ representation / sale authority context
→ NativeListing(s) only where semantically legitimate
```

A simplistic permanent `one listing per PhysicalBoat` constraint is not accepted because legitimate situations can include changed mandates, stale broker inventory, multiple authorized professional representatives or identity uncertainty.

Future implementation must define fail-closed handling for at least:

- active professional representation versus attempted owner-direct publication;
- a professional mandate that has ended;
- legitimate multi-broker representation where permitted;
- uncertain PhysicalBoat/MarketEpisode matching;
- disputed authority and moderation resolution.

No automatic delete/overwrite is authorized by this direction.

## 10. Broker referral neutrality

Broker referral begins only after the seller voluntarily chooses the broker path.

HullQ must not use a broker's payment/subscription tier to improve its position in a referral shortlist.

Referral suitability/fairness must be based on accepted non-commercial criteria relevant to the seller's needs. Commercial arrangements may fund HullQ, but they may not secretly select the broker for the seller.

Any success-based referral fee is future commercial implementation and must preserve this neutrality.

## 11. Mixed-supply broker value proposition

Owner-direct inventory creates real channel tension even when organic Search is fair. HullQ must therefore maintain a positive broker value proposition rather than relying on the statement that private listings are ranked fairly.

The accepted broker value direction includes:

- technically qualified buyer demand;
- deterministic Search and trustworthy inventory truth;
- legitimate broker identity/branding preservation;
- a low-friction professional inventory workspace;
- lead source attribution and workflow;
- analytics/performance insight;
- explicit seller-to-broker referral opportunity;
- no paid organic ranking.

Private listings must not become an excuse to weaken `docs/BROKER_WORKSPACE_PRODUCT_DIRECTION_2026-09-13.md`, `specs/BROKER_WORKSPACE_REQUIREMENTS.v0.1.md`, the Broker Workspace Launch Gate or its Mandatory Capability Register.

## 12. Private-seller monetization

The preferred owner-direct commercial model is:

1. **free basic self-listing** as the default direction;
2. optional paid verification/inspection/document-processing services where payment buys the service, never the truth result or ranking;
3. optional success-based broker-referral revenue when the seller voluntarily chooses professional representation and the later commercial contract supports it;
4. later relevant partner/affiliate services around a transaction where useful and lawful.

Verification should be treated primarily as a marketplace trust/data-quality engine, not assumed to be a major standalone revenue pillar without evidence.

## 13. Advertising / featured placement is deferred, not forbidden

The permanent rule is **no paid organic ranking**.

A separately labelled sponsored/featured advertising surface is not categorically forbidden, but it is deliberately deferred and is not part of the current monetization baseline.

If reconsidered later, it must be visually and mechanically separate from organic results: it must not alter organic eligibility/classification/ordering, replace an organic result, consume organic pagination slots or be presented as an organic recommendation.

That later decision must explicitly evaluate the trust cost of attention purchase against its revenue value.

## 14. Transaction safety / escrow opportunity

A vetted third-party transaction/escrow path is a future product opportunity for owner-direct sales, not a current core requirement.

It may later complement seller verification by protecting the money-transfer stage and may support partner/affiliate economics.

HullQ must not become custodian of buyer/seller funds merely by adding this opportunity. HullQ holding/controlling transaction funds would require a separate regulatory, legal, architecture and business decision.

## 15. Buyer safety remains separate from seller verification

Seller verification cannot prevent every fraud type. Later owner-direct contact/transaction UX should include proportionate buyer safety guidance and safeguards against payment/escrow/overpayment/social-engineering fraud without falsely promising that HullQ verification guarantees a safe transaction.

## 16. Business-model asymmetry and durable moat

The broker-first mixed-supply/no-pay-to-rank model can create an early strategic asymmetry against incumbents whose revenue depends heavily on paid visibility or restrictive supply rules.

That is an early competitive opening, not the complete durable moat.

Longer-term defensibility must compound through HullQ's actual product/data assets:

- evidence/provenance quality;
- technical Search;
- PhysicalBoat / MarketEpisode identity;
- accumulated market history;
- strong broker workflow;
- strong seller workflow;
- marketplace liquidity/network effects;
- brand trust built by truth-preserving behavior.

## 17. Consequences for current implementation

At the time of this decision, accepted implementation through SLICE-0053 remains professional-only on the write side. Existing professional publishing eligibility and Broker Workspace authorization code is not silently broadened to private sellers.

Owner-direct publishing requires its own bounded implementation/readiness path that reuses the stable identity/truth architecture without bypassing professional authorization rules.

No existing professional actor role is to be faked or reused to make a private seller appear to be a broker.

SLICE-0054 remains unselected until post-pivot reassessment evaluates the new owner-direct direction together with the still-mandatory Broker Workspace commitments and existing trigger gates.

## 18. Reassessment obligation

From this decision onward, every normal capability reassessment must account for this owner-direct direction when relevant.

In particular:

- Search changes must preserve the non-commercial organic Search invariant;
- monetization changes must preserve payment/evidence independence;
- marketplace identity/listing changes must consider professional/owner-direct representation conflicts;
- seller-facing work must preserve the explicit trust scopes and escalation model;
- broker-facing work must account for the mixed-supply value proposition;
- Production Readiness and existing broker launch gates remain independent hard constraints at their existing triggers.

The Project Owner may supersede this direction only through an explicit reviewed decision; it must not drift through implementation convenience.
