# HullQ Repository Audit — 2026-08-18

**Status:** COMPLETED
**Scope:** pre-OQ-004 docs-to-code consistency audit

## Objective

Check whether the current repository can safely serve as the specification source for later code generation without relying on chat-only assumptions or stale contracts.

## Findings and resolutions

### A-001 — Duplicate decision authority / D-009 collision — RESOLVED

`docs/DECISIONS_REQUIRED.md` duplicated the canonical Open Questions register and had acquired an invalid D-009 subscription entry while `OQ-009` already means unknown-data search semantics.

**Resolution:** the file is now a historical compatibility index only. `docs/governance/OPEN_QUESTIONS.md` is the sole canonical unresolved-decision register.

### A-002 — Historical drafts mixed with active specs — RESOLVED

Superseded BoatDesign v0.2, Source v0.1 and the pre-acceptance Identity Model draft were still physically located under `specs/`, increasing the chance an AI/code agent could use the wrong contract.

**Resolution:** moved to `reference/history/`; `specs/` is reserved for active accepted or explicitly current draft contracts.

### A-003 — Architecture document overstated unresolved implementation choices — RESOLVED

`SYSTEM_ARCHITECTURE.md` described Strapi and a 15–60 minute cache as if selected, despite OQ-011/OQ-006 remaining open. It also used legacy `SavedSearch/AlertSettings` concepts after the accepted product split into Search / SavedQuery / Monitor / Alert / SubscriptionEntitlement.

**Resolution:** architecture language made explicitly provisional and domain concepts updated.

### A-004 — Accepted identity requirements missing from Requirements baseline — RESOLVED

The changelog recorded REQ-ID-004..008 and REQ-SEARCH-006, but they were absent from `specs/REQUIREMENTS.md`.

**Resolution:** requirements restored from accepted Identity Model semantics.

### A-005 — Acceptance criteria coverage incomplete — RESOLVED

Only a subset of requirements had explicit acceptance criteria, weakening docs-to-code traceability.

**Resolution:** Requirements baseline upgraded so every normative requirement has an explicit acceptance condition; blocked requirements remain clearly gated by their OQ.

### A-006 — Price intelligence existed only partly in product notes — RESOLVED

Price development was identified as a strong Pro concept, but historical asking-price semantics, source-retention rights and listing lifecycle interpretation had no explicit gate.

**Resolution:** OQ-017 added for historical market observations / price intelligence, with requirements prohibiting asking-price/sale-price conflation and unapproved historical retention.

### A-007 — Provenance field addressing used ad-hoc dot paths — RESOLVED IN OQ-004 DRAFT

Earlier provenance examples used strings such as `dimensions.loa_m`.

**Resolution:** OQ-004 proposal adopts RFC 6901 JSON Pointer for machine-stable field addressing and separates source observations, canonical resolutions and derived lineage.

## No critical structural gap found

The audit found documentation drift rather than a broken project architecture. The current sequencing remains valid:

`OQ-004 → OQ-001 → OQ-010 → repo/CI bootstrap → research pipeline benchmark → broad ingestion`.

## Follow-up gates intentionally not resolved by this audit

- OQ-009 search/unknown semantics;
- OQ-011 backend architecture;
- OQ-012 persistence/search technology;
- OQ-013 market access;
- OQ-016 pricing/limits;
- OQ-017 market history/price intelligence persistence semantics.
