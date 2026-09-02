# HullQ Market Identity Contract v0.1

**Status:** ACCEPTED
**Decision:** `docs/ARCHITECTURE_REBASELINE_2026-09-02.md` §3–4 (2026-09-02), codified for implementation by SLICE-0040
**Supersedes:** none (new contract)
**Normative language:** BCP 14 semantics apply to uppercase MUST/SHOULD/MAY.

## 1. Purpose

This specification defines the runtime identity boundary between the five
marketplace-adjacent concepts the accepted 2026-09-02 architecture rebaseline
requires to remain structurally distinct:

```text
BoatDesign (canonical technical identity, referenced only)
≠ PhysicalBoat
≠ MarketEpisode
≠ NativeListing
≠ ExternalMarketObservation
```

It defines representation only. It does not define resolution, dedup,
episode-continuity policy, lifecycle, freshness, authorization, media, leads,
pricing, or referral semantics. Those remain governed by later slices and by
`docs/ARCHITECTURE_REBASELINE_2026-09-02.md` directly until implemented.

## 2. Identity kinds

Each of the following is an independent, opaque, non-empty identity value.
Two identity values of different kinds MUST NOT be considered equal or
interchangeable even when their underlying raw text is identical.

### 2.1 BoatDesignRef

A `BoatDesignRef` is a marketplace-side pointer to an existing canonical
BoatDesign. It MUST NOT mint, merge, redefine or mutate the referenced
BoatDesign. It carries no technical facts of its own.

### 2.2 PhysicalBoatId

Identifies one `PhysicalBoat` (a specific vessel, also referred to as
`MarketVessel`). Distinct from BoatDesign, MarketEpisode, NativeListing and
ExternalMarketObservation identity.

### 2.3 MarketEpisodeId

Identifies one `MarketEpisode` — one sale/market episode for exactly one
PhysicalBoat.

### 2.4 NativeListingId

Identifies one `NativeListing` — a HullQ-hosted market appearance.

### 2.5 ExternalMarketObservationId

Identifies one `ExternalMarketObservation` — a source-specific external
market appearance.

## 3. Relationship records

### 3.1 PhysicalBoat

- MUST have a `PhysicalBoatId`.
- MAY have a resolved `BoatDesignRef`, or remain design-unresolved.
- One `PhysicalBoat` MAY participate in multiple `MarketEpisode`s over time.
- This contract does not implement HIN/CIN/name/registration matching or
  ownership proof.

### 3.2 MarketEpisode

- MUST have a `MarketEpisodeId`.
- MUST hold a typed `PhysicalBoatId` reference to exactly one PhysicalBoat.
- Whether two periods are `SAME`, `NEW` or `UNRESOLVED` is a later resolution
  capability. No fixed time-gap rule is defined here.

### 3.3 NativeListing

- MUST have a `NativeListingId`.
- MUST support two states:

  ```text
  UNRESOLVED -> no MarketEpisode link
  RESOLVED   -> typed MarketEpisodeId link
  ```

- This is an identity link only. It is NOT listing lifecycle/status. An
  unresolved identity link does not imply draft/inactive/stale; a resolved
  identity link does not imply published/active.
- Does not define professional Organization ownership/publishing
  eligibility, price, status, media, contact data, persistence or public
  pages.

### 3.4 ExternalMarketObservation

- MUST have an `ExternalMarketObservationId`.
- MUST have a non-empty source identity (`source_id`) and a non-empty
  source-side record key (`source_record_key`).
- MUST support the same two states as NativeListing:

  ```text
  UNRESOLVED -> no MarketEpisode link
  RESOLVED   -> typed MarketEpisodeId link
  ```

- Does not authorize live source access, a rights decision, an adapter,
  dedup or automated resolution.

## 4. Invariants

- Equal raw text across different identity kinds MUST NOT make the
  identities equal or interchangeable.
- A relationship field typed for one identity kind MUST reject a value of
  any other identity kind at construction time (fail closed), not only at
  static type-check time.
- One `MarketEpisode` MAY be referenced by one `NativeListing` and multiple
  `ExternalMarketObservation`s without collapsing their separate identities.
- A `PhysicalBoat` referencing a `BoatDesignRef` MUST NOT cause BoatDesign
  technical facts to be treated as physical-vessel or listing truth. No
  automatic projection of BoatDesign or Configuration facts into
  PhysicalBoat, NativeListing or ExternalMarketObservation is permitted.

## 5. Non-goals

This contract explicitly excludes, and no implementation under it may add:

- HIN/CIN/name/registration matching, fuzzy similarity, or broker/location/
  year heuristics;
- cross-source dedup scoring or automatic same-vessel/same-episode merge;
- source authority/ranking or automatic resolution of NativeListing/
  ExternalMarketObservation identity links;
- listing lifecycle/status, freshness/reconfirmation, price/history/Days-on-
  Market, media, leads/contact routing, referrals, or publishing
  eligibility;
- persistence, API, authentication or UI concerns.
