# SLICE-0086 — First-Level Sailing-Vessel Buyer Discovery (Hull Form + Cockpit + Deck)

**ID:** SLICE-0086  
**Type:** IMPLEMENTATION  
**Status:** READY — **NOT YET OPERATIVE** until independent exact-HEAD docs review ACCEPT, GitHub CI + manufacturer reproducibility SUCCESS, and docs-only READY PR merge to `origin/main`  
**Risk:** HIGH_RISK — public hard-filter classification, new concrete PhysicalBoat fact/writer contract and cross-Organization evidence, generation-specific BoatDesign/NamedVariant qualification, public/private rights and multilingual browser truth  
**Previous accepted:** SLICE-0085 (Owner-accepted and remote/local closed; `FINISH_SLICE.bat` owner-confirmed).  
**Current Owner selection:** 2026-10-14: broad sailing-vessel inclusion in principle, recreational sailing yacht/multihull first launch focus; foundational independent hull/cockpit/deck facets **before** another beam/displacement/material filter bundle.  
**Governing reconciliation:** `docs/POST_SLICE_0085_FIRST_LEVEL_SAILING_VESSEL_DISCOVERY_REASSESSMENT_2026-10-14.md`.  
**Canonical baseline:** `f2fd17168c348eaf821f938c551347775472b60d` (post-0085 acceptance closure, accepted Search criteria count **4**).

## Mandatory readiness checks

**ONE-CAPABILITY CHECK:** PASS  
**ONE USER WORKFLOW:** A buyer chooses what kind of **sailing vessel structure** is interesting using the first-level Rumpfform/Cockpit/Aufbau choices, then optionally adds existing technical constraints; a broker maintains the real offered boat's corresponding structural claims and sees a read-only Search-fit preview of precisely the same independently qualified constraints. This is one end-to-end classified discovery upgrade, not separate taxonomies/search engines/pilot features.

**VISIBLE-RESULT CHECK:** PASS  
A buyer selects `hull_configuration=CATAMARAN` and optionally `cockpit_position=CENTER`, `deck_saloon=DECK_SALOON`, `loa_min=10`, then sees **only** current-public listings for which the **same qualified BoatDesign/NamedVariant configuration** and **the actual current PhysicalBoat's independently asserted, non-conflicting concrete values** confirm all chosen facets. EN/DE/FR/PT/ES buyer labels and concrete-vs-design evidence are visible. A broker on an owned promoted lifecycle-DRAFT listing can enter or explicitly mark unknown these concrete attributes using the existing authorized claim-edit process, save/reopen the retained state and preview the same query without changing public listing state.

**PRODUCT EXECUTION PLAN ALIGNMENT:** PASS  
Directly follows Owner-selected product-first, user-meaningful Search priority; enables understandable first-level discoverability before the next detail-filter bundle, maintains accepted multiple-criterion Search and first pilot/paid/broad-public prerequisites. No commercial-ship legal claims or extra marketplace supply flow.

**REPOSITORY RECONCILIATION CHECK:** PASS  
`BoatDesign v0.5/v0.6` has hull form+count in configuration; `v0.6` only has `deck.cockpit_position` and `deck.deck_saloon`. Current `PhysicalBoatClaimSnapshot`, registry, persistence observations, broker claim UI and 0085 Search registry do NOT support these as accepted actual-boat claims or filters. The accepted query/FieldProjectionSpec/FieldResolution/variant/current-claim/MUST-AND kernel and localized buyer/broker web surfaces already exist and MUST be reused. The new bounded static facet data and concrete claim persistence/write/read are the genuine missing vertical.

**TRIGGER GATES CHECK:** PASS  
**Third-copy structural determination:** `COMMON STRUCTURE GENERALIZED / REUSED`; add statically whitelisted `CriterionDefinition` adapters/qualifiers to the accepted Search registry and **one** shared current-claim reader/classifier; no parallel Search evaluator or direct DB schema→UI schema crawler. Current `TECHNICAL_NATIVE_SEARCH_CRITERIA_COUNT=4` before implementation. The three candidate facets may raise it to **7 only on explicit accepted implementation closure**, when all three distinct end-to-end public dimensions are proven. Until then, do NOT change count or markers.

**OVERALL MVP CAPABILITY REGISTER CHECK:** PASS  
Current `MVP-BUY-001` remains IMPLEMENTED/PARTIAL; `MVP-BUY-002` remains PARTIAL; Broker `MVP-BROKER-010` remains IMPLEMENTED within illustrative prepublication Search-fit. No broker export/report, buyer persistence/alerts, trust/safety, owner-direct admission or production provider obligation is waived or represented as completed. External production-data pilot and public launch remain NOT_STARTED; Production Readiness IN_PROGRESS; Launch Pack NOT_STARTED. UI accessibility/form truth is functional scope, not visual polish.

## Normative classification axes — do NOT conflate them

### Marketplace inclusion boundary

HullQ addresses **sail-powered vessels broadly**: single/multiple hulls, sailing yachts, motorsailers, traditional sail craft and commercial sailing craft as relevant, without treating the current 0086 public filter set as an exclusionary marketplace admission gate. Recreational sailing yachts and cruising multihulls are the launch-focused supply/use cases. No separate compliance statement, inspected classification, commercial registration or charter suitability is inferred from naming or styling.

Accepted conceptual dimensions are distinct:
- **Hull form** `hull_configuration`: physically one/two/three hulls and potentially other/unknown.
- **Cockpit position** `cockpit_position`: aft/center/forward/multiple, other/unknown.
- **Deck saloon / pilothouse structure** `deck_saloon`: none, deck_saloon, pilothouse, unknown.
- **Propulsion/rig concept** (motorsailer vs conventional, traditional rigs): distinct, **not** flattened into one hull category; later explicitly governed.
- **Commercial or private use**: current/historical use, legally attested vessel status and yacht form are DIFFERENT facts. Existing registry `physical_boat.broad_use_history` has `COMMERCIAL` but is DISPLAY_ONLY, open-world positive-known **history**, not certification or boat type. No `COMMERCIAL_SAILBOAT` hard predicate in 0086.
- **Classic/traditional** style, use, age and historical design: NOT interchangeable, no age/name/material guess; follow separate future contract.

Examples that MUST be representable without category conflict: MONOHULL+CENTER+DECK_SALOON; MONOHULL+AFT+PILOTHOUSE; CATAMARAN+AFT+NONE; a motorsailer with two hulls in later ontology; a commercial-operated monohull which remains a monohull. The buyer sees three **combinable facets**, never a single mutually exclusive "boat type" enum containing `catamaran`, `center cockpit`, `commercial` as peers.

### Public accepted candidate facet #5 — hull form

- **Public key:** `hull_configuration`, one value per request: `MONOHULL`, `CATAMARAN`, `TRIMARAN`. Exact ASCII canonical tokens; absent filter = all eligible supported sailing vessels **not filtered by hull form**. No empty canonical value, unsupported `OTHER`/`UNKNOWN` public predicate or silently selected default.
- **BoatDesign v0.5:** `/baseline/configuration/hull_configuration`, NamedVariant `/overrides/configuration/hull_configuration`; v0.6 **same** pointers. Qualify actual FieldResolution+NamedVariant applicability before use. Source design lowercase `monohull` → MONOHULL etc. `hull_count` where separately qualified and incompatible (`monohull=1`, `catamaran=2`, `trimaran=3`) MUST fail closed, never prove a contradictory category. Missing/unknown count does not fabricate count and does not silently reject an otherwise independently fully qualified hull form unless an explicit accepted dependency policy proves count mandatory; preserve source semantics and document resolution test.
- **Concrete** `physical_boat.hull_configuration`: new accepted bounded current publisher claim `VALUE_ASSERTION` or `UNKNOWN`, optional and omission distinct from UNKNOWN; accepted concrete `MONOHULL`, `CATAMARAN`, `TRIMARAN`, with `OTHER` permitted as actual descriptive claim ONLY if explicitly justified but NEVER a supported hard search value. No source design value is copied into actual claim.
- **Truth:** one positive hard criterion, same-boat competing Org assertion conflict => UNKNOWN. Actual physical seller claim must independently confirm value. Hull label not itself vessel registration/flag/class/owner status.

### Public accepted candidate facet #6 — cockpit position

- **Public key:** `cockpit_position`, supported `AFT`, `CENTER`, `FORWARD`, `MULTIPLE`; no `OTHER`/`UNKNOWN` filter.
- **v0.6:** exact qualified `/baseline/deck/cockpit_position`, `/overrides/deck/cockpit_position`; no legacy v0.5 deck path or inferred equivalence (older designs remain design UNKNOWN for this facet). Any v0.6 `cockpit_count=0` with a non-unknown position is contradictory and MUST NOT produce a positive match; avoid relying solely on schema validation of old persisted payloads.
- **Concrete** optional `physical_boat.cockpit_position` `VALUE_ASSERTION` or `UNKNOWN`, exact supported canonical value and approved other case if necessary. Public Match only if both qualified design/configuration and uncontradicted current concrete assertion confirm the selected location. CENTER = cockpit located centrally/aft of mainmast convention subject to independently corroborated source, NOT inferred from aft-cabin marketing name; do not derive from photo/image.

### Public accepted candidate facet #7 — deck saloon / pilothouse

- **Public key:** `deck_saloon`, supported `DECK_SALOON`, `PILOTHOUSE`; optionally `NONE` **only if** reviewer substantiates a real positive recorded absence value and identical current publisher claim in executable test. `NONE` is explicit "not deck saloon/pilothouse", never missing data. No inferred `PILOTHOUSE` from `DECK_SALOON`; these are separately accepted v0.6 tokens and must not be merged.
- **v0.6:** exact qualified `/baseline/deck/deck_saloon`, `/overrides/deck/deck_saloon`. v0.5 missing/unknown design stays UNKNOWN. No reliance on a hull/cockpit form or generic `raised saloon` string to populate this facet.
- **Concrete** optional `physical_boat.deck_saloon` `VALUE_ASSERTION` or `UNKNOWN`, with accepted canonical values as above and truthful optional UNKNOWN vs omission. Same current publisher and cross-Org conflict rules as all other criteria.
- Before implementation sign-off decide `NONE` as an explicit qualified negative or defer it from public supported vocabulary, and record exact supported values in final evidence. Both DECK_SALOON and PILOTHOUSE must be real end-to-end positive filters for this dimension to count.

## Shared implementation boundary

1. Extend `specs/MARKETPLACE_FIELD_REGISTRY.v0.1.json` with exactly three explicit `PHYSICAL_BOAT` categorical OPTIONAL `PUBLIC`/`SEARCHABLE` entries (other existing enum tokens only with explicit grounding); do NOT change accepted fields or phases via a sweeping registry edit. Extend corresponding `src/hullq/domain/physical_boat_claims.py` frozen types and `PhysicalBoatClaimSnapshot`, source-specific wire serializer/parser, durable immutable revisions, Postgres current-claim observations and broker inventory editor; compatibility with old revisions and old exact retries is mandatory. A migration is authorized **only if** proven necessary to retain valid historical bytes/schema; no gratuitous structural data rewrite.
2. Use existing `src/hullq/search/criteria_registry.py` typed `CriterionDefinition` and current per-criterion FieldProjectionSpec/qualified FieldResolution/variant set construction. Extend public `search_read.py`, API `app.py` parsing/serialization and private `broker_search_fit.py` from the same registry, not duplicated client-only matching. New enums have explicit static Python/TS parity tests. The six/seven/eight URL param keys count is not the hard dimension count; canonical lexicographic URL key ordering remains backend-owned, and duplicate/unsupported token handling remains fail-closed.
3. Anonymous buyer Search: first-level prominently labeled hull/cockpit/deck controls before existing numeric/detail controls on **all five locales**; accessible `label`/radio or select forms, `All sailing vessels` not a hidden model filter, selected choices preserved on refresh, canonical link and localized reason/evidence displayed. This is a Search **entry hierarchy**, not a second dynamic results API. If user has selected no criterion, existing empty-search behavior remains the simple landing/form; **do NOT** silently create unrestricted global browse/query endpoint, auto-select Monohull or return matches without a supported filter. Avoid duplicative first-level buttons with separate unreviewed URL generation.
4. Broker: same three options in existing authorized editor's current-PhysicalBoat **claim editing** plus its existing illustrative single-target DRAFT Search-fit UI, private `no-store`/`noindex` and PUBLISHER/MFA authorization. No extra origin/CSRF exposure, no automatic claim from BoatDesign; no new lead/contact/publishing operation. NativeListing DRAFT remains absent from public Search until current-public rules genuinely pass.
5. Reuse existing `MixedAndQuery`/one configuration engine and `classify_concrete_candidate`/current claim observation snapshot, preserving true/false/unknown and same-configuration coupling even when mixing hull/cockpit/deck with `draft_max`, `keel_configuration`, `loa`, `rudder_configuration`. Cross-Organization conflicts are not overwritten, false or unknown never counts as `CONFIRMED_MATCH`. Preserve count and legacy drafts, URL aliases, shortlist/Compare/discovery provenance and current-public D29 eligibility.
6. `search_sensitivity`: accepted legacy draft/keel-only forms continue; *any* new facet active must suppress or safely reject sensitivity before backend incomplete-current evaluation. Do not use 0085's existing guard hardcoded only for LOA/rudder without extending to 0086 facets. Original and new combos must be tested against real SSR to catch plausible but wrong deltas.
7. No uncontrolled admission: a class token cannot be a legal `COMMERCIAL` claim, a fact about past use, a rigging style or an arbitrary label inferred from brand/model. External real commercial sailing-vessel acceptance continues under existing publication/trust/data-rights and eventual legal governance, never by a new Search enum.

## Required tests and retained real-user proof

**MECHANICAL INVARIANTS / FAILURE MODES CHECK:** PASS — contract specifies executable adversarial proof.  
**Risk category:** HIGH_RISK; concrete yacht fact revision semantics, classification search truth, authenticated private write/read vs public disclosure.

**Must never change:** Every confirmed public Search result satisfies all selected hull/cockpit/deck + prior constraints on the SAME qualified applicable BoatDesign/NamedVariant configuration and the **actual** currently and independently asserted PhysicalBoat facts, no conflicting other-Org claims, no unqualified Design v0.5 deck inference, no DRAFT eligibility bypass and no payment-dependent organic truth. Specialty sailing vessels remain eligible in principle; unknown class not falsely coded as monohull.

**Loss/partial failure:** immutable current PhysicalBoat revisions and D29 public eligibility are the durable source; a failed mutation does not partially persist new claims or clear previous ones. Omitted/UNKNOWN/VALUE_ASSERTION (and explicitly justified `OTHER`) are different. Exact old request retries are stable and retained old evidence reopens; authorized new edits are transactional/optimistic under existing version/idempotency rules. Missing design/variant/actual evidence => typed UNKNOWN; contradictory => FALSE or UNKNOWN per accepted source policy; DB/authz errors => typed 401/403/404/409/503, not fake zero matches. Cross-tenant foreign access non-enumerating.

**Before FIRST implementation REVIEW, require:**
- Unit: fixed normalized hull/cockpit/deck token maps, v0.5 vs v0.6 qualified pointers, explicit NONE if supported, hull_count contradiction, cockpit_count contradiction, parser duplicates/unsupported/empty/noncanonical, Python↔real TS exported categories parity (including divergence fixture), enum labels all five locales.
- Real PostgreSQL 18 + FastAPI: saved/edit/reopen concrete boat claim optionality and immutable revision provenance, old historical revision and exact retry regression, publish preflight still valid with omitted optional new fields; cross-Organization conflicting and same value head behavior; missing/unqualified FieldResolution and NamedVariant inheritance/conflicts; one configuration AND rather than cross-configuration mixing; no DRAFT leak/no partial write.
- Broker HTTP + built Astro SSR: private listing form contains editable new claims and saved reopened values; current published/draft/full roles, MFA and cross-org failure, new three-facet Search-fit private evidence, missing claim correctly UNKNOWN, zero preview writes and no buyer demand claim.
- Public real PG18 + FastAPI + built Astro SSR: independent positive filter for each of the three categories, mixed 0085 legacy+new 5+ filters, no false inclusion on older v0.5 design lacking deck facts, conflict/UNKNOWN, canonical redirect and negative/duplicate, actual per-criterion current boat evidence, all five locale routes `en/de/fr/pt/es` including canonical `<link>`; product first-level controls appear before detail filters and no empty-input implicit broad response.
- 0085 regression: draft-only legacy schema and result, keel/LOA/rudder standalone+combined, shortlist, Compare, discovery tokens, current-public D29 and owner-direct equal Search treatment, sensitivity old-only still works and *mixed any new facet* never silently drops active conditions, publish rights, broker Search-fit concurrency.
- Quality: Ruff format/check, mypy, repository validator (accepted criteria marker STILL 4 during implementation), complete unit and real PG18 persistence suites, Web Node tests and Astro build/check, retained two-sided real HTTP+built SSR script, manufacturer reproducibility and CI on exact final branch HEAD. Script must NOT claim coverage from a mocked UI. Adversarial full-diff self-review before first handoff; no hidden gap simply because old suite green.

**Second-criterion bridge comparison:** PASS — historical SLICE-0055 guard retained; the new facets use the shared current registry/FieldResolution/variant bridge rather than a fifth bespoke qualification pipeline.  
**Third-copy abstraction guard:** PASS — `COMMON STRUCTURE GENERALIZED / REUSED`; reviewed implementation must demonstrate actual reuse in source/tests.  
**Adds technical native Search criterion:** YES (up to **three** distinct candidate dimensions).  
**Technical Search criterion ordinal:** 5 (candidate #5–#7, acceptance pending).  
**Production readiness gate:** IN_PROGRESS  
**PRODUCTION LAUNCH PACK CHECK:** NOT_APPLICABLE — no launch/production work authorized.  
**Launch-pack phase before this slice:** NOT_APPLICABLE  
**Launch-pack phase after this slice:** NOT_APPLICABLE  
**OVERALL MVP CAPABILITY REGISTER STATUS:** OPEN; no capability marker preemptively upgraded.

## Delivery and workflow

**Slice sizing assessment:** COHERENT ONLY AS THIS BOUNDED THREE-FACET FIRST-LEVEL BUNDLE; if the concrete-claim changes expose fundamental source/portability blockers, STOP and report them before dropping the product-bearing part. Do not swap in a registry-only cosmetic classification screen. No 0087 automatically selected.

**Implementer handoff:** A single exact-HEAD completion report with scope completed, actual code/doc/DB changes, source of each physical/design field and language token, exact concrete claims write/read tests, minimum real PG18+FastAPI+built Astro SSR evidence, counted criteria (candidate 5/6/7 but canonical accepted count still 4), legacy no-regression, remote CI observed separately (no unverified claim), known functional taxonomy exclusions and any owner-required semantic decision. Never self-approve or mark DONE.

**Lifecycle:** Owner `START_SLICE.bat` for 0086 **only after** this docs-only READY PR passes separate independent exact-HEAD review and remote CI/repro and merges. The independent reviewer later examines implementation HEAD and any amendments, Owner explicitly accepts, implementation merges, distinct acceptance closure advances `PROJECT_STATE_ACCEPTED_SLICE`/criteria count if proven, and Owner finally runs `FINISH_SLICE.bat`. Production gates remain NOT_STARTED/IN_PROGRESS, no live pilot, no new paid provider.
