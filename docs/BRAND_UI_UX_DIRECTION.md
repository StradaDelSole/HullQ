# HullQ — Brand / UI / UX Direction

**Status:** ACTIVE strategic direction; implementation deferred until the relevant product/frontend slices  
**Updated:** 2026-08-22  
**Related:** `docs/PRODUCT_SCOPE.md`, `docs/ROADMAP.md`, ADR-0007, OQ-018

## 1. Core design intent

HullQ should project **strength, control, precision and authority** across brand identity, UI and UX.

The name `HullQ` supports a short, technical, system-like identity. The product should feel like a capable instrument for serious technical discovery rather than a lifestyle portal, generic classifieds site or nautical-themed brochure.

The preferred design qualities are:

- **authoritative**;
- **technical**;
- **controlled**;
- **powerful**;
- precise;
- calm;
- highly usable.

This direction is subordinate to the product's primary priorities: **quality and usability first**. Visual strength must reinforce usability, never compete with it.

## 2. Critical guardrail — strong, not aggressive

A central distinction is binding for future design work:

> **HullQ should feel strong and dominant, but not aggressive.**

Strength must come from confidence, hierarchy, precision, restraint and competence — not from visual intimidation.

HullQ must therefore avoid drifting toward:

- gaming-brand aesthetics;
- military/tactical aesthetics;
- cyberpunk visual language;
- macho or adversarial imagery;
- gratuitously sharp, threatening or weapon-like motifs;
- excessive black/red contrast used merely to imply aggression;
- loud animation, glow effects or visual noise presented as "power".

The desired feeling is closer to a highly engineered professional instrument than to a game, weapons system or action-sports brand.

## 3. Visual identity direction

Future CI/UI exploration should prefer:

- strong, highly legible typography;
- disciplined typographic hierarchy;
- geometric or technical character where appropriate, without sacrificing readability;
- precise grids and alignment;
- confident use of scale for headings, technical values and key results;
- controlled spacing rather than decorative density;
- restrained corner radii and component geometry;
- a reduced, deliberate color system with one or few strong accents;
- technical diagrams, profiles and data visualizations as legitimate brand material;
- consistency across web product, reports, dealer material, technical prints and later merchandise.

The identity should avoid generic marine-industry visual clichés such as:

- anchors;
- compass roses;
- waves used as default decoration;
- generic navy-blue "yachting" branding;
- sunset/lifestyle imagery as the main identity carrier;
- luxury-brochure styling that obscures technical information.

HullQ may look premium through execution quality, but it should not imitate a luxury-yacht brochure.

## 4. UX should express the same strength

The strongest expression of HullQ's identity should be the product behavior itself.

A technically complex search should feel controlled and understandable. Users should not need to think like database operators, and raw source metadata must not be exposed as an uncurated filter dump.

Preferred UX characteristics:

- fast comprehension of the search model;
- curated technical filters;
- strong information hierarchy;
- direct manipulation and immediate feedback where useful;
- clear distinction between confirmed fact, conflict and unknown data;
- deterministic, understandable match behavior;
- comparison as a first-class workflow;
- technical depth available without forcing every user to confront it at once;
- minimal unnecessary dialogs, animations or ornamental interaction.

Where query semantics support it, result states should be expressed confidently and consistently, for example:

```text
MATCH
NO MATCH
INSUFFICIENT DATA
```

Unknown data must not be cosmetically hidden to make the interface appear more complete.

## 5. Information presentation

BoatModel and BoatDesign surfaces should let technical values carry visual weight.

A result or detail surface may use large, disciplined data presentation such as:

```text
HALLBERG-RASSY 352

10.54 M          6,700 KG
LOA              DISPLACEMENT

1.67 M           GRP
DRAFT            HULL MATERIAL

FIN KEEL         SKEG-HUNG
KEEL             RUDDER

1977—1989
```

This is a direction, not a frozen component specification. Exact fields, labels, scores, data-coverage indicators and visual treatments remain subject to later product, query and OQ-018 work.

HullQ must not invent opaque authority signals merely for visual effect. Any displayed score, confidence indicator, coverage percentage or match percentage requires defined semantics before implementation.

## 6. Tone of voice

Product copy should be concise, competent and factual.

Prefer language that communicates:

- clarity;
- technical confidence;
- control;
- transparency;
- respect for unknown or conflicting evidence.

Avoid:

- generic aspirational copy such as "Find your dream yacht";
- exaggerated claims of certainty;
- macho language;
- artificial urgency;
- excessive nautical wordplay;
- marketing language that makes HullQ sound like a lifestyle travel brand.

The product should not need to announce that it is powerful; the quality of the information and interaction should demonstrate it.

## 7. Relationship to subjective boat categories

The strong visual identity must not turn into authoritative-looking subjective classification.

For example, HullQ should not canonically declare a boat to be a "Bluewater Boat" merely because the UI can make such a badge look convincing. Subjective suitability should remain expressible through atomically researched technical properties and user-defined query criteria wherever possible.

Visual confidence must therefore never exceed epistemic confidence.

## 8. Brand-system consistency

When a formal CI/design system is eventually created, it should govern at least:

- logo and wordmark usage;
- typography;
- color and contrast;
- spacing/grid;
- icons;
- data visualization;
- cards/tables/filter controls;
- interaction states;
- reports and exported material;
- dealer-facing surfaces;
- technical posters/prints and later merchandise where introduced.

The objective is for all HullQ touchpoints to feel as though they are generated by one coherent technical system.

## 9. Accessibility and usability guardrail

Dominance must never be achieved by reducing accessibility.

Future implementation must preserve:

- strong text/background contrast;
- legible type sizes;
- keyboard accessibility;
- clear focus states;
- understandable form/filter behavior;
- responsive layouts;
- reduced-motion support where applicable;
- semantic HTML and screen-reader compatibility.

A design that looks powerful but is difficult to operate is a failure against HullQ's priorities.

## 10. Scope rule

This document records strategic direction only.

It does **not** authorize current frontend implementation, a design-system slice, logo redesign, animation work or aesthetic scope expansion during Stage 3 data-universe work.

Detailed visual design should be developed when the technical query/search product and OQ-018 public search/SEO surface are sufficiently defined to test the identity against real workflows rather than static mockups alone.
