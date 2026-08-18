# HullQ — Market Source Access Register

**Status:** ACTIVE RESEARCH TEMPLATE  
**Related:** OQ-013, REQ-MARKET-002

This register records verified market-source access constraints. A production adapter cannot rely on assumptions from memory or old documentation.

## Required fields per source

- platform/source name
- region/market relevance
- date last verified
- official API existence
- API scope (public / broker / own inventory / co-brokerage / full-market / unknown)
- feed/export options
- partner/commercial access route
- deep-link/search URL capability
- automated retrieval terms
- caching/storage constraints
- display/attribution constraints
- rate limits if documented
- pricing/account prerequisites
- contact/support route
- evidence links/references
- HullQ candidate integration mode
- status: `UNRESEARCHED | RESEARCHING | VIABLE | LIMITED | BLOCKED | LEGAL_REVIEW`
- notes / unresolved questions

## Source table

| Source | Status | Last verified | Candidate mode | Notes |
|---|---|---|---|---|
| YachtWorld / Boats Group | RESEARCHING | — | TBD | Require official/current access review before implementation. |
| Boat24 | RESEARCHING | — | TBD | Require official/current access review before implementation. |
| Scanboat | UNRESEARCHED | — | TBD | — |
| TheYachtMarket | RESEARCHING | — | TBD | Require official/current access review before implementation. |
| Rightboat | UNRESEARCHED | — | TBD | — |

## Decision rule

For each source, choose the least brittle permitted integration mode that still provides useful product value. Maintenance burden is a first-class acceptance criterion, not merely an engineering inconvenience.
