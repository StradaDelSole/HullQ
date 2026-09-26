# HullQ — Brand Core & Experience Direction

**Date:** 2026-09-14  
**Status:** OWNER-ACCEPTED BRAND / UX / UI DIRECTION  
**Purpose:** Preserve the current agreed HullQ brand core and its translation into product experience so later branding, UX and UI work does not drift into generic marketplace, generic SaaS or nautical-lifestyle conventions.

This document is product/brand direction, not an implementation specification. It should be consulted when future work touches branding, UX, UI, visual territories, design system, copy, motion, onboarding or broker/buyer experience.

---

## 1. Canonical Brand Core

HullQ is not positioned as "another boat portal" and not as a yacht-lifestyle brand.

HullQ exists to make sailboat discovery **clearer, more relevant and more trustworthy**.

It helps serious buyers find boats by what they actually are and helps professional brokers present inventory without surrendering their identity or their data.

HullQ does not manufacture certainty. It distinguishes what is known, what is inferred and what remains unknown.

### Core principles

- **Precision over persuasion.**
- **Evidence over impression.**
- **Calm over clutter.**
- **Independent by design.**

### Brand enemy

> **The opaque boat marketplace.**

The broker is not the enemy. HullQ is opposed to opaque data, shallow filtering, stale listings, unexplained search behavior, duplicated or ambiguous inventory, hidden uncertainty, artificial urgency and information asymmetry.

---

## 2. Brand Promise

Primary direction:

> **Find the boats that actually fit.**

Supporting outward-facing idea:

> Better data. Better search. Better boat decisions.

Internal quality standard:

> HullQ should bring engineering-grade discipline to sailboat discovery without presenting itself as an engineering tool for specialists only.

"Engineering-grade" is therefore an **internal quality benchmark**, not the main outward-facing brand identity.

---

## 3. Product Proof — the brand must be demonstrable

HullQ should not rely on generic claims such as "better data" or "transparent search" without concrete product mechanisms.

The brand promise is supported by product behavior such as:

- UNKNOWN remains UNKNOWN; uncertainty is not silently converted into certainty.
- Design/configuration truth remains distinct from physical-boat/listing truth.
- A stale or withdrawn listing is not treated as evidence that a boat was sold.
- Search decisions should become explainable rather than opaque.
- A broker cannot buy or override technical truth.
- Broker inventory remains portable and remains the broker's inventory.
- A listing must remain current to remain discoverable where freshness policy requires it.
- HullQ should preserve provenance and evidence where the product makes factual claims.

These product mechanisms are more important than decorative brand claims because they make **Evidence over impression** self-proving.

---

## 4. Four-layer model

Future brand and product-experience work should remain separated into four layers:

```text
1. BRAND CORE
   Why does HullQ exist?
   What does HullQ stand for?
   What does HullQ promise?
   What does HullQ oppose?

            ↓

2. PRODUCT PROOF
   How does the actual product prove the promise?

            ↓

3. EXPERIENCE PRINCIPLES
   How should HullQ feel and behave?
   Voice, tone, hierarchy, interaction behavior

            ↓

4. EXPRESSION
   Typography, color, photography, motion,
   microcopy, iconography, logo, visual details
```

Voice, tone and micro-interactions are therefore **translations of the Brand Core**, not part of the Brand Core itself.

This distinction is intentional: the Brand Core should remain stable while specific expressions may evolve.

---

## 5. Experience principles

HullQ should feel:

- precise;
- calm;
- competent;
- neutral where facts are involved;
- warm enough not to become sterile;
- transparent about uncertainty;
- information-rich without feeling crowded;
- professional without conventional luxury posturing;
- technically credible without becoming an engineering dashboard for experts only.

### Buyer experience

The buyer surface may be more spacious and editorial. It should support discovery, comparison, confidence and technical understanding.

### Broker experience

The Broker Workspace may be denser and more operational. It should optimize for speed, clarity, ownership, current state and minimum duplicate work.

The two surfaces may differ in density, but they must remain recognizably one HullQ product and one brand system.

---

## 6. Voice architecture

Two compatible voices may coexist inside one brand.

### Voice A — the examiner / surveyor

Use for:

- technical values;
- CONFIRMED / UNKNOWN / inferred states;
- broker claims;
- search explanations;
- evidence and provenance;
- authorization / status-sensitive information.

Properties:

- calm;
- exact;
- no exaggeration;
- no humor around factual truth;
- never hide uncertainty.

### Voice B — the dry, competent friend

Use selectively for:

- loading states;
- empty states;
- non-factual onboarding moments;
- generic errors;
- low-risk process feedback.

Properties:

- restrained personality;
- dry humor rather than cuteness;
- never undermine trust;
- humor about the process, never about technical truth.

### Hard rule

> **HullQ may never know more in its humor than HullQ actually knows.**

Copy must not imply physical impossibility, complete market coverage, verification or certainty unless the system genuinely has evidence for that claim.

---

## 7. Signature interaction directions

The following are **design directions/candidates**, not all automatically approved implementation requirements.

### Strong direction — UNKNOWN as a first-class visual state

A promising visual language is to represent UNKNOWN values using technical-drawing conventions such as dashed or otherwise incomplete line treatment, while CONFIRMED values use a solid treatment.

This is strategically strong because it makes epistemic state visible instead of hiding missing knowledge.

Accessibility rule: color must never be the only distinction between factual states.

### Strong direction — absence of persuasion mechanics

HullQ should generally avoid:

- artificial urgency;
- fake scarcity;
- manipulative countdowns;
- generic popularity badges;
- ungrounded social proof;
- star-rating mechanics without a genuinely valid rating model.

Their absence is itself an expression of **Precision over persuasion**.

### Candidate — restrained measurement / scan motion

A sonar/echo/measurement-inspired loading treatment may be explored, but only if it remains abstract, restrained and functional. It must not pull HullQ back into decorative nautical cliché.

### Candidate — confirmation motion

A brief settling / measuring-instrument style motion for CONFIRMED_MATCH may be explored if it improves comprehension rather than becoming decoration.

### Candidate — public build/version signature

"Hull No." as a public version/build motif is an interesting idea but is **not accepted as canonical**. Internal slice numbers are implementation/governance identifiers and may not be meaningful public version semantics. Revisit only if a durable user-facing version concept exists.

---

## 8. Explicit brand / UX no-gos

Avoid:

- anchor, compass-rose, wave, sail or pirate clichés as default brand language;
- dark-blue + turquoise + generic yacht icon as an automatic palette/logo solution;
- generic SaaS visual language with interchangeable rounded cards and decorative badges;
- luxury signaling for its own sake;
- technical severity that makes HullQ feel cold or exclusionary;
- humor where factual state, safety, identity, price or technical evidence is involved;
- red as a default visual code for UNKNOWN, because UNKNOWN is not necessarily an error;
- color-only distinction between data states;
- wording such as "verified", "guaranteed", "complete" or equivalent unless the product evidence supports it;
- copy that implies HullQ searched "everything" when it only searched known/available data.

---

## 9. Visual direction

Current strategic direction:

> **Editorial + Technical**

Desired result:

- high-quality typography;
- disciplined grids;
- strong information hierarchy;
- generous whitespace where appropriate;
- restrained color use;
- excellent sailboat / detail photography where photography adds value;
- technical diagrams, tables and evidence states where they improve understanding;
- no decorative maritime theme park.

HullQ should feel like a technical maritime product with the confidence and restraint of a good editorial design publication.

---

## 10. Recommended work sequence

To avoid premature logo work and avoid an oversized design-system project, future UI/UX/branding work should normally follow this sequence:

```text
1. Brand Core
2. Product-Proof Map
3. Three central UX flows as rough wireframes
4. Test 2–3 visual brand territories on real HullQ screens
5. Derive a minimal design system from those screens
6. Produce high-fidelity screens
7. Finalize logo / wordmark
```

### Initial central flows

Buyer:

```text
Search
→ Filter
→ Results
→ Listing detail
→ Save / Contact
```

Broker:

```text
Login
→ Workspace
→ Listing create/edit
→ Publish
→ Lead / outcome state
```

Saved Search / monitoring becomes a later buyer flow when that capability exists.

---

## 11. Scope discipline

Branding and UX work must not become an unlimited parallel workstream.

Use these guards:

- one concise Brand Core, not an expanding collection of slogans;
- 2–3 rough territories, not complete brand systems in parallel;
- use real HullQ information problems/screens as test surfaces;
- no full component library before at least one core flow is visually coherent;
- no final logo decision before the product's actual visual language is understood;
- distinguish accepted principles from exploratory interaction ideas;
- do not let aesthetic work redefine accepted domain, truth, identity, authorization or marketplace boundaries.

---

## 12. Future-use rule

When future HullQ work concerns any of the following, this document should be consulted before proposing direction:

- branding;
- logo / wordmark;
- typography;
- color;
- visual identity;
- design system;
- Buyer UI;
- Broker Workspace UI;
- interaction/motion design;
- Voice & Tone;
- microcopy;
- loading / empty / error states;
- factual state visualization;
- marketing-site/product-language alignment.

If a future proposal conflicts with this direction, the conflict should be made explicit rather than silently drifting the brand.
