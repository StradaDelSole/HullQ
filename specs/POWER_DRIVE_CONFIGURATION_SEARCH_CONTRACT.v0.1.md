# Power Technical Search Criterion 1 — Current Drive Arrangement v0.1

**Status:** PROPOSED NORMATIVE CONTRACT for SLICE-0093 readiness; not an implemented, independently reviewed or Owner-accepted Search criterion.  
**Basis:** Owner Sail+Power decision 2026-10-22; SLICE-0090 architecture §2.2/§4 row C; accepted SLICE-0091 category claims and SLICE-0092 qualified design-unresolved publisher search; issue #372.  
**Capability:** Internal Power technical Search by one source-qualified, currently installed propulsion-drive configuration on an offered POWER boat, explicitly distinguished from independently confirmed manufacturer/design facts.

## One field, one meaning

The single proposed technical criterion is `power_drive_configuration`, the **mechanical arrangement transferring power into propulsive thrust**. It is **not** engine number/make/model, total horsepower, energy source (diesel/electric/hybrid), fuel system, hull running mode, speed, range, operating conditions or proof of maintenance.

| Canonical query token | Meaning | German buyer label | Current publisher assertion | Qualified BoatDesign v0.6 mapping |
|---|---|---|---|---|
| `SHAFT` | Conventional inboard shaft to propeller | Wellenantrieb | Admissible | `propulsion.drive_type=shaft` only |
| `STERNDRIVE` | Sterndrive, transom-mounted drive leg | Z-Antrieb / Sterndrive | Admissible | **Unavailable** in v0.6 |
| `POD` | Integrated steerable pod-drive unit | Pod-Antrieb | Admissible | **Unavailable** in v0.6 |
| `WATERJET` | Waterjet propulsor | Wasserstrahlantrieb | Admissible | **Unavailable** in v0.6 |
| `OUTBOARD` | Outboard engine/drive unit | Außenborder | Admissible | `propulsion.drive_type=outboard` only |

This is an explicit public **five-token exact whitelist** for one categorical search condition. A current publisher's durable claim may represent `MIXED`, `OTHER`, `UNKNOWN` or omitted as truthful but **not affirmative filter matches**. Mixed unlike drive types cannot be collapsed into a single accepted token, even if the vessel uses one of the types. Two identical shaft lines or identical outboards may assert their common mechanical arrangement only when currently and explicitly attested; **no engine count** follows. Electrical/hybrid fuel/energy source is orthogonal to this drive criterion. Saildrives and ambiguous `other` are not mapped to SHAFT by guesswork. Marketing names, engine manufacturers and NautiX engine-type strings alone cannot determine the drive.

**Repository-discovered schema limitation:** Canonical `specs/BOAT_DESIGN_SCHEMA.v0.6.json` `propulsion_shape.drive_type` permits only `shaft`, `saildrive`, `outboard`, `other` and `unknown`. Only `shaft → SHAFT` and `outboard → OUTBOARD` may be used as bounded design-side positive mappings **if** the exact BoatDesign/NamedVariant current FieldResolution and publisher-specific physical claim both meet existing trust gates. Neither `other` nor `saildrive` proves STERNDRIVE, POD or WATERJET. **No v0.7 BoatDesign schema/migration is granted by this criterion**. These additional values initially come exclusively from properly attributed current PhysicalBoat publisher claims, not fake factory facts.

## Request / query contract

- Exactly one Power-only public key: `power_drive=SHAFT|STERNDRIVE|POD|WATERJET|OUTBOARD`; chosen route shapes: `GET /api/search/{locale}/power?power_drive=TOKEN` and five internal noindex Astro SSR pages `/{locale}/power/search?power_drive=TOKEN` for en/de/fr/pt/es.
- New static Power `CriterionDefinition`: `criterion_id=power_drive_configuration`, categorical projection of the same name, exact whitelist above, one new field reader and the **same** `CategoricalLeafCriterion` / `evaluate_projection` / accepted MUST-AND truth mechanism. No new scorer or category-biased organic rank. This is Power domain criterion ordinal **1**, but **global accepted native technical criterion ordinal 10** (9 Sail + 1 Power). The global accepted marker is advanced only in the separately reviewed Owner-accepted closure after implementation, never in READY.
- Existing Sail `/api/search/{locale}` and `/{locale}/search`, all nine accepted Sail hard conditions, old-only sensitivity, legacy UNKNOWN Sail eligibility, discovery tokens and compare/shortlist remain exactly unchanged. Power query key on Sail path, Sail-only keys on Power path, mixed-domain filter requests, duplicates/unrecognized keys and malformed/unsupported tokens reject explicitly (bounded 400 or accepted 308 canonical redirect). No ignored tracking key.
- Power BASE (no criterion) renders a truthful non-search internal landing state, **not** unqualified generic browse, a confirmed-all results count or an early external product. Power result JSON and UI present typed Power condition and honest source-specific evidence, with no fabricated BoatDesign/NamedVariant.
- A machine `CONFIRMED_MATCH` based on `PUBLISHER_CLAIM` means *the publisher's sufficiently qualified current statement matches*, **not** independently audited boat facts. Design-evidence and claim-evidence are distinct result branches. Public responses never leak competing org/account identifiers or raw unlicensed documents.

## Qualified physical and design facts

**Required claim-only positive (design-unresolved):** active NativeListing → episode → PhysicalBoat with `boat_design_ref IS NULL`; D29 current-public eligibility, current acceptable freshness, publishing Organization's own positive `VALUE_ASSERTION(POWER)` category and exactly one positive allowed drive assertion from the **same latest current claim revision**. Retain publisher org/revision/actor/time as internal source evidence, and do not borrow another org's drive/category. Other-current-Org category or drive contradiction, insufficient unit/vocabulary/applicability, revision withdrawal, stale edit and a DB/authorization failure are nonconfirmed. Both category and technical field must be read from one coherent PostgreSQL observation snapshot; reuse accepted SLICE-0092 batching/eligibility/kernel where safe and actually profiled.

**Design-linked POWER:** original Sail design-linked query is completely untouched. A design-level positive only exists when category claims agree with POWER and the correct generation/NamedVariant/FieldResolution supplies an exact qualified mapped factory drive type, *and* the current PhysicalBoat installation is separately qualified. In v0.6 mapped `shaft`/`outboard` could qualify if actual source rights and canonical/resolution agreement pass; absence of eligible fact and `other`/`unknown` can never prove a drive. If a correct design-linked Power bridge cannot be implemented without creating a fake FieldResolution, the design-linked portion must be reported **INSUFFICIENT_DATA with a truthful limitation**, not falsely counted as a match or silently omitted as comprehensive Power inventory. The minimal mandatory positive case in this one-dimension slice is explicitly source-qualified **design-unresolved Power publisher inventory**. Future design coverage is separately tracked.

A retrofitted boat may have a different current drive than its factory design. This does **not** automatically prove an identical-time contradiction or make either value current truth; unless a revision/time/installed-equipment/refit boundary is independently qualified, **stop current-state positive classification** rather than auto-select the factory value or give a spurious conflict verdict. No inference from engine brochure, hull/model text, unaccepted catalog provenance or prior import.

**Publisher editor:** The optional `physical_boat.power_drive_configuration` wraps its typed enum with the existing distinct omitted/UNKNOWN/VALUE_ASSERTION and current immutable PhysicalBoat revision/head logic. Authoritative broker editing, save/readback, and real Astro form must round-trip it. An unrelated form save must never erase it; stale/foreign/invalid writes must mutate nothing. Accepted MFA, active membership, current PUBLISHER, Organization-owned listing and ACTIVE safety checks unchanged; no new owner-direct admission, full Power draft creator, or external import.

## Negative and retained proof

Real PostgreSQL 18 / FastAPI / built Astro SSR (five locales), unit tests and retained inspector must demonstrate:

- Qualified no-design POWER with each of the five tokens becomes exactly one source-labelled positive with no imaginary design identity. The corresponding wrong Drive criterion is an evidenced nonmatch or insufficient, not a positive.
- Explicit SAIL / MOTORSAILER / UNKNOWN / CONFLICT category with identical drive never enters Power positives. An otherwise positive POWER claim whose publisher itself has no POWER category cannot borrow another Organization's category.
- Current other-Organization contradiction, missing/retracted/UNKNOWN/OTHER/MIXED drive, unsupported `saildrive`, wrong field applicability, stale issuer, revocation and replay never produce confirmed match. A future change of current drive removes earlier match; no multi-revision torn read under two real PG18 connections.
- D29 denial, expired freshness, withdraw, invalid cover/offer, failed DB read suppress rather than positively match or turn server error into no-result success.
- BoatDesign v0.6 qualified SHAFT/OUTBOARD bridge uses **current** FieldResolution with exact variant; `other`/`unknown` and falsely conflated variants remain insufficient. Retrofitted equipment not silently converted to factory fact.
- Public source labels (`PUBLISHER_CLAIM` versus genuinely design-qualified), category and missing-evidence explanation render as escaped text in en/de/fr/pt/es; noindex and canonical query/redirect, no personally identifiable internal provenance.
- The **entire old Sail route/DTO/query/criteria regression** stays unchanged. Unknown category on the accepted Sail legacy path retains accepted 0091 semantics. Existing shortlist/compare and broker search-fit are neither silently extended to Power nor falsely advertised.
- Representative synthetic 0/40/200 mixed Sail/Power candidate runs record statement counts, query/index plan, elapsed and actual retained matches; the accepted pre-real-data hosted scaling/abuse gate #355 remains OPEN regardless of these synthetic numbers.
- Existing Sail-only NautiX exporter must never be used to emit the wrong `sail-yacht` type for a Power record. No Power export/import or third-party reuse right is granted by this slice.

## Strictly deferred / hard STOP

Power engine count, horsepower, fuel/hybrid, propeller tuning, speed, consumption, range/operating-point basis, planing/displacement class, hours/maintenance/refits as standalone filters, Power importer/exporter/category mapping, fully comparable Broker Power Search-fit, generic dual-domain browse, external sources/rights, real broker data/pilot, public product/SEO launch, and production Search-scale readiness are **not** delivered by Power criterion #1.

Keep #355 runtime/pilot STOP, #366 joint Sail+Power release, #372 remaining Power capability and owner-direct trust constraints OPEN. Independent review and Owner acceptance determine **whether the source-qualified Power dimension really works**, not whether the entire Power marketplace is ready.
