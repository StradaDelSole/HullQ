# HullQ — Product Language and Internationalization Requirement

**Status:** ACCEPTED PRODUCT REQUIREMENT  
**Date:** 2026-08-25  
**Applies to:** public HullQ web/search experience and Product-Led SEO architecture  
**Detailed implementation gate:** OQ-018

## Required language set

HullQ's public product MUST support the following languages:

- English;
- German;
- French;
- Portuguese;
- Spanish.

These languages are product scope, not optional marketing experiments.

The exact rollout order may be staged if necessary, but architecture and public-surface contracts MUST NOT assume an English-only product or require a later structural rewrite to add the other required languages.

## Core architecture rule

HullQ MUST maintain **one language-neutral canonical domain/data identity layer**.

Language variants MUST NOT create separate canonical BoatModel/BoatDesign/Brand/Organization identities merely because labels, slugs, descriptions or UI terminology differ by language.

Stable opaque HullQ IDs, technical values, provenance, query semantics, taxonomy identity and derived-metric semantics remain language-neutral.

Localization applies to presentation and public-discovery surfaces such as:

- UI labels and navigation;
- field/taxonomy display labels;
- methodology/explanatory copy;
- public-page titles and metadata;
- technical-discovery page copy;
- comparison explanatory copy;
- user-facing units/formatting where applicable;
- human-readable slugs where OQ-018 permits localized slugs;
- accessibility text and other user-facing language.

## SEO / hreflang requirements

OQ-018 MUST define a deterministic multilingual public-URL and indexation model covering all five required languages.

It must decide and test at minimum:

1. default-language behavior;
2. URL language structure;
3. localized vs shared slugs;
4. canonical behavior within each language version;
5. reciprocal `hreflang` relationships;
6. `x-default` policy if used;
7. localized sitemap behavior;
8. language-switcher crawlability;
9. redirect behavior based on explicit user choice vs automatic locale detection;
10. duplicate/thin translation prevention;
11. localized title/meta generation;
12. localized structured-data text where appropriate;
13. translation fallback behavior for missing localized copy;
14. 404/redirect behavior when one language variant is unavailable;
15. Search Console / Bing measurement by language and page class.

Search engines and users MUST be able to reach each supported localized page through stable crawlable URLs. Locale selection MUST NOT depend solely on client-side JavaScript or mandatory geolocation/language redirects.

## Translation quality doctrine

HullQ MUST NOT create thin multilingual index inventory merely by mechanically translating boilerplate while the meaningful main content remains untranslated or low quality.

Programmatic translation MAY assist production, but published indexable localized pages must preserve:

- factual equivalence with canonical HullQ data;
- technical terminology consistency;
- explicit unknown/conflict semantics;
- methodology meaning;
- page-specific usefulness;
- no invented specifications or qualitative claims.

Technical terms should use a controlled localization glossary so concepts such as keel, skeg, rudder, displacement basis, rig, draft and configuration retain consistent meaning across languages.

## Locale decisions deliberately left open

The required **languages** are fixed, but the exact regional locale variants remain an OQ-018 implementation decision where not explicitly specified by product requirements.

In particular OQ-018 must decide whether Portuguese initially maps to, for example, `pt`, `pt-PT`, `pt-BR`, or a supported combination, and whether Spanish/English/French require later regional variants.

This decision must be based on target users, terminology, search demand and maintainability rather than creating unnecessary duplicate locale surfaces.

## Product-Led SEO consequence

Product-Led SEO applies independently in every supported language, but HullQ should not blindly multiply every English landing page by five.

A localized public page should pass the same indexability-quality gate as the source-language page and provide genuine localized value.

Search demand should be measured by language because useful technical intents can differ in terminology and volume across markets.

The multilingual organic loop is therefore:

```text
one canonical HullQ data/query layer
            ↓
localized public representations
            ↓
EN / DE / FR / PT / ES organic demand
            ↓
language-specific intent and terminology signals
            ↓
localization + data/enrichment priorities
            ↓
same canonical HullQ product
```

## Relationship to existing strategy

This requirement supplements and constrains:

- `docs/PRODUCT_LED_SEO_STRATEGY.md`;
- `architecture/SEARCH_AND_SEO_ARCHITECTURE.md`;
- ADR-0007;
- OQ-018;
- REQ-SEO-001 through REQ-SEO-007.

Where earlier strategy text described launch language as still wholly undecided, this document supersedes that point: **English, German, French, Portuguese and Spanish are required HullQ product languages.** Exact locale codes, URL grammar and rollout sequencing remain for OQ-018.