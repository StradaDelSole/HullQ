# HullQ — Owner-Direct Listing Requirements v0.1

**Status:** OWNER-ACCEPTED NORMATIVE PRODUCT REQUIREMENTS when merged  
**Product direction:** `docs/OWNER_DIRECT_LISTING_PRODUCT_DIRECTION_2026-09-14.md`  
**Scope:** owner-direct/private seller supply, trust/fraud boundaries, Search independence, referral neutrality and coexistence with professional supply

These requirements supersede the prior current-direction statement that independent private FSBO is out of scope. They do not retroactively modify historical slice contracts or authorize implementation outside the normal slice/readiness workflow.

### REQ-PRIVATE-001 — HullQ is broker-first mixed supply
HullQ MUST allow a bounded owner-direct/private seller listing path in addition to professional broker/dealer inventory.

**Acceptance:** current product/state documentation describes the marketplace as broker-first rather than broker-only; future implementation must not require a private seller to masquerade as a professional Organization/member.

### REQ-PRIVATE-002 — Seller choice is genuine
A private seller MUST be able to choose either owner-direct self-listing or a broker-referral path without forced preselection or artificial friction designed solely to coerce one path.

**Acceptance:** seller-facing workflow exposes both choices clearly; choosing owner-direct does not silently create a broker referral, and choosing referral does not automatically publish an owner-direct listing.

### REQ-PRIVATE-003 — Organic Search commercial independence
Commercial consideration MUST NOT affect organic Search eligibility, match classification or organic ordering.

**Acceptance:** no seller/broker subscription, verification payment, referral economics, affiliate value, ad relationship or expected HullQ revenue changes those three decisions; tests/governance for any future Search monetization preserve this invariant.

### REQ-PRIVATE-004 — Payment does not buy truth
Payment MAY buy a verification/inspection/document-processing service but MUST NOT directly buy a stronger evidence/truth state, Search eligibility or organic position.

**Acceptance:** materially equivalent admissible evidence is resolved identically regardless of whether HullQ/a partner was paid to produce/process it.

### REQ-PRIVATE-005 — Trust scopes are explicit and non-collapsing
Phone reachability, strong seller identity, right-to-list attestation, documentary sale authority and technical vessel truth MUST remain distinct concepts.

**Acceptance:** domain/API/UI evidence can distinguish at least `PHONE_VERIFIED`, `IDENTITY_VERIFIED`, `RIGHT_TO_LIST_ATTESTED` and `SALE_AUTHORITY_VERIFIED` or semantically equivalent states; no generic verification state implies all of them.

### REQ-PRIVATE-006 — Baseline owner-direct publication gate is proportionate
A normal unflagged owner-direct listing MAY become public after a HullQ account, verified phone reachability, explicit right-to-list attestation and baseline anti-abuse checks, subject to the ordinary listing/truth/publication rules implemented by the owning capability.

Strong ID verification, boat-document upload and physical boat challenge MUST NOT be universal publication prerequisites absent a later explicit superseding decision.

**Acceptance:** representative normal seller flow can reach the publication boundary without mandatory identity-document/selfie or vessel-document upload while still enforcing phone, attestation and anti-abuse requirements.

### REQ-PRIVATE-007 — Right-to-list means authority, not ownership only
The seller attestation/verification model MUST support lawful authority to list/sell a vessel rather than requiring the submitter to be the sole registered owner.

**Acceptance:** the model can represent owner/co-owner and appropriately authorized representative cases without falsely describing every authorized seller as the owner.

### REQ-PRIVATE-008 — Risk-based escalation is allowed and explicit
HullQ MUST be able to require stronger identity and/or documentary sale-authority evidence when material risk signals, disputes or moderation evidence warrant escalation.

**Acceptance:** the owning implementation defines deterministic/manual/hybrid escalation responsibility and explicit outcomes; a blocked/escalated case does not silently publish while required evidence is outstanding.

### REQ-PRIVATE-009 — Early fraud controls stay bounded
Initial owner-direct anti-abuse controls SHOULD prefer low-cost observable signals such as phone reuse, abnormal account/listing velocity, suspicious listing volume, reliable price anomalies and user/moderation reports.

A conflicting MarketEpisode/representation state may be used only after that identity/conflict capability exists. Perceptual image hashing, external stolen-image matching and generalized fraud scoring are NOT implicit Day-1 requirements.

**Acceptance:** readiness distinguishes implemented low-cost signals from deferred fraud capabilities and does not claim unbuilt matching/image intelligence.

### REQ-PRIVATE-010 — Strong identity verification is data-minimizing
When strong ID-document/selfie/liveness verification is implemented, HullQ SHOULD use a provider-bounded architecture that avoids retaining raw identity/biometric material unless explicitly required by a separately reviewed legal/product decision.

**Acceptance:** architecture names the minimum HullQ-retained verification result/reference/method/timestamp data, provider/raw-data boundary, retention basis and deletion/user-rights handling before production activation.

### REQ-PRIVATE-011 — Verification badges are evidence-bounded
Seller/listing badges MUST state what was actually verified and MUST NOT imply broader technical, identity or authority assurance than the evidence supports.

**Acceptance:** a `Sale Authority Verified`-type badge cannot imply all vessel specifications are confirmed; a phone-verification marker cannot be presented as strong identity verification.

### REQ-PRIVATE-012 — Technical vessel truth remains field-/claim-level
Owner-direct listings MUST use HullQ's existing evidence/provenance/truth semantics for concrete-yacht facts. Seller verification does not upgrade vessel fields.

**Acceptance:** concrete-yacht fields can independently remain confirmed, declared, unknown or conflicting; no seller-level badge mass-promotes technical claims.

### REQ-PRIVATE-013 — Representation conflict is modeled above a naïve duplicate-listing rule
HullQ MUST NOT allow conflicting owner-direct and professional representations of the same sale to coexist merely because they are different NativeListing rows. Resolution MUST use the accepted PhysicalBoat/MarketEpisode identity boundary plus explicit representation/sale-authority semantics.

A permanent `one NativeListing per PhysicalBoat` shortcut is NOT accepted.

**Acceptance:** the eventual conflict capability covers active professional representation, ended mandate, legitimate multi-representation where permitted, uncertain boat/episode matching and disputed authority without automatic destructive overwrite.

### REQ-PRIVATE-014 — Referral starts only after seller opt-in
Broker referral MUST begin only after the private seller voluntarily chooses the referral path.

**Acceptance:** owner-direct workflow is not silently diverted into referral; referral workflow records explicit seller choice.

### REQ-PRIVATE-015 — Broker referral selection is commercially neutral
Broker subscription/payment status MUST NOT improve position in a referral shortlist.

**Acceptance:** shortlist eligibility/order is based on accepted non-commercial suitability/fairness criteria; any referral fee is downstream commercial economics, not a ranking input.

### REQ-PRIVATE-016 — Mixed-supply broker value remains a first-class obligation
Owner-direct inventory MUST NOT weaken the accepted Broker Workspace product direction, launch gate or mandatory commitments. HullQ MUST preserve a compelling professional value proposition under mixed supply.

**Acceptance:** reassessment/readiness for owner-direct work explicitly checks impact on professional supply and the still-open Broker Workspace obligations; no owner-direct capability marks broker requirements complete.

### REQ-PRIVATE-017 — Basic owner-direct self-listing is free by default direction
The current commercial direction is a free basic owner-direct listing, with monetization concentrated on optional services/partners/referrals rather than organic Search visibility.

**Acceptance:** no readiness may introduce a mandatory owner-direct listing fee or paid organic visibility as an assumed baseline without an explicit later Project Owner commercial decision.

### REQ-PRIVATE-018 — Verification monetization is service monetization
If HullQ charges for seller/technical/document verification, the fee MUST correspond to a real verification/processing/inspection service and MUST remain independent of the evidence outcome.

**Acceptance:** a failed/insufficient verification cannot be converted to a stronger truth state merely because payment succeeded.

### REQ-PRIVATE-019 — Sponsored/featured inventory is deferred and separate from organic Search
A future clearly labelled sponsored/featured advertising surface MAY be considered through a separate accepted decision, but is not part of the current baseline.

If later implemented, it MUST NOT alter organic eligibility/classification/ordering, replace an organic result, consume organic pagination positions or be represented as an organic recommendation.

**Acceptance:** current implementation contains no authorized paid featured Search surface; later readiness must prove mechanical/visual separation.

### REQ-PRIVATE-020 — HullQ is not a funds custodian by implication
A future vetted escrow/transaction-safety partner MAY be offered, but HullQ MUST NOT hold/control transaction funds unless a separate owner-accepted regulatory/legal/architecture/business decision explicitly authorizes that role.

**Acceptance:** partner/referral integration can exist without HullQ becoming payment/escrow custodian; any custodial proposal is separately gated.

### REQ-PRIVATE-021 — Buyer safety is not replaced by seller verification
Owner-direct transaction UX MUST NOT claim that seller verification guarantees transaction safety. Buyer-facing safeguards/guidance may be introduced for payment, escrow, overpayment and social-engineering risks.

**Acceptance:** trust copy distinguishes seller evidence from transaction safety; no verification badge promises fraud-free sale/payment.

### REQ-PRIVATE-022 — Professional implementation boundaries remain intact until private capability exists
Existing professional publishing eligibility, Organization/Membership authorization and broker-only write implementations MUST NOT be silently broadened or bypassed to simulate owner-direct listings.

**Acceptance:** private sellers are not seeded as fake brokers/Organizations solely to pass professional authorization; the owner-direct write boundary is introduced through an explicitly selected/readiness-reviewed capability.

### REQ-PRIVATE-023 — Current marketplace identities remain controlling
Owner-direct implementation MUST preserve:

```text
BoatDesignRef != PhysicalBoatId != MarketEpisodeId != NativeListingId != ExternalMarketObservationId
DESIGN / CONFIGURATION TRUTH != PHYSICAL BOAT / LISTING TRUTH
```

**Acceptance:** owner-direct listings do not promote design facts into concrete-yacht truth and do not collapse seller identity, PhysicalBoat identity, sale episode or listing identity.

### REQ-PRIVATE-024 — Reassessment must include the pivot
Every normal post-pivot capability reassessment MUST inspect this product direction/spec when the candidate work touches Search, listing/supply, identity/verification, marketplace monetization, referral, representation conflict or broker value.

**Acceptance:** relevant readiness records explicitly account for applicable `REQ-PRIVATE-*` obligations and do not rely on the superseded broker-only/FSBO-out-of-scope assumption.

### REQ-PRIVATE-025 — SLICE-0054 is not selected by the pivot itself
This product-direction change MUST NOT be interpreted as selecting or authorizing SLICE-0054.

**Acceptance:** canonical project state keeps `PROJECT_STATE_QUEUE_SLICE: 0054` while stating that the capability remains unselected pending post-pivot reassessment/readiness.
