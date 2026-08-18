# Market Adapter Contract

**Status: DRAFT.**

Each external sales source is isolated behind an adapter. The source-specific implementation may change without changing the HullQ domain contract.

## Required behavior

An adapter should accept a simple resolved design query such as make/model/variant/generation hints and return zero or more records conforming to `specs/MARKET_LISTING_SCHEMA.v0.1.json`.

Conceptual interface:

```text
search(design_query, request_context) -> CanonicalMarketListing[]
```

## Adapter responsibilities

- use only the source's permitted API/feed/partner/access method
- execute source-specific query syntax
- parse source response
- normalize into the canonical listing schema
- preserve source listing ID and URL where available
- report errors without crashing other adapters
- expose health telemetry (success, latency, result count, parse failure)

## Orchestrator responsibilities

- choose which adapters to query
- apply source-dependent short-lived cache policy
- merge results
- match/retain BoatDesign identity
- deduplicate listings across sources
- determine genuinely new matches for alerts

## Explicit non-goal

The adapter layer is not a permanent full-market mirror by default.

## Before implementing a source

Verify the platform's current permitted access mechanism and terms. Do not assume that a public website implies permitted automated commercial access.
