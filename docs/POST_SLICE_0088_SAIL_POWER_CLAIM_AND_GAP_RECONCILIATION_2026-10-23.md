# Post-SLICE-0088 — Sail+Power Claim, Category & Evidence Reconciliation

**Date:** 2026-10-23 (Europe/Vienna)  
**Decision authority:** Owner's Sail+Power decision #366; Owner-accepted customer-first direction #364; Owner's acceptance of the validated important parts of Claude v0.9 (2026-10-23).  
**Baseline:** Canonical post-SLICE-0088 main `feb1f4af03e300b232643a021b73d9a7d9fc427b`; SLICE-0088 Owner ACCEPTED, implementation PR #368 and formal closure PR #371 both merged; local FINISH observed SUCCESS.  
**Implementation tracker:** [Issue #372](https://github.com/StradaDelSole/HullQ/issues/372).  
**Status:** OWNER-ACCEPTED FUTURE REQUIREMENTS / RECONCILIATION; **not a Power-feature acceptance or implementation**. No new slice started by this record.

## 1. Evidence authority and classification

This record selects useful findings from the Owner-supplied `REVIEW_OWNER_ENTSCHEIDUNG_SAIL_POWER_2026-10-23_v0.9.md` and independently cross-checks them on canonical post-0088 source. The external review used a generated repository text dump, **did not execute tests**, and some of its Sail claim/Search descriptions reference earlier baselines. Tag semantics:

- **CODE-VERIFIED** = personally inspected current source on the canonical main above (still requires runtime tests where applicable).
- **OWNER-ACCEPTED DIRECTION / REQUIRED** = approved future behavior; not yet implemented.
- **DESIGN PROPOSAL / VERIFY** = technically plausible suggestion, requires its own exact-head design/security/performance evidence.
- **DEFERRED / OPEN** = tracked elsewhere; not silently absorbed into 0089 or a closed slice.

Supersession: the target marketplace is **Sail and Power with separate high-quality specialist technical discovery**, sharing one truthful broker/identity/marketplace core; first external product/broker-pilot launch requires **both** domains plus all applicable technical, rights, security and production gates. Sail-first is strictly **internal**. A worldwide complete model corpus, equally many filters, arbitrary slice count or time deadline are **not** approval criteria. Voluntary independent market research is permitted; an external product preview/pilot is not.

## 2. Verified post-0088 architectural gaps

| Finding | Verified code surface | Accepted disposition / future acceptance obligation |
|---|---|---|
| Design-unresolved listings disappear from technical native search | `src/hullq/persistence/inventory_search.py`: `pb.boat_design_ref IS NOT NULL` in active-listing candidate SQL; `src/hullq/application/native_inventory_query.py` consumes `list_active_design_linked_listings`. | **REQUIRED**: evaluate a second **qualified concrete-claim** candidate path for Sail+Power; current-public eligibility, rights and Publisher/Org source remain mandatory. Design-unresolved inventory must not be falsely called confirmed design evidence. Preserve the existing nine-dimensional design-linked results and same-configuration MUST/AND behavior; fail closed on unsupported/conflicting evidence. |
| NautiX import category set is Sail-only | `src/hullq/domain/import_nautix.py` `_ACCEPTED_SAIL_BOAT_TYPES`. | **REQUIRED** in future category work: explicit source-qualified Sail/Power/motorsailer/unknown policy, documented transformation and safe reject/ambiguity handling. |
| Export 0088 NautiX category is always `sail-yacht` | `src/hullq/domain/inventory_export.py`: `_NAUTIX_CATALOG_BOAT_TYPE`. | **EXPECTED PRE-PIVOT, NOT AN 0088 BUG**. Future per-listing export must preserve true type and reject unknown/unsupported categories; protect all seven accepted authentic writer formats and transparent field-loss/rights checks. XLSB outbound remains deferred #362. Third-party schemas may not encode all Claim evidence; warn/disclose rather than invent fields. |
| Sail hard technical facets exceed the earlier description in Claude v0.9 | `src/hullq/search/criteria_registry.py`, `physical_boat_claims.py`, `native_inventory_query.py` include nine accepted dimensions through SLICE-0087. | **CORRECTION:** Claude's narrative that current concrete claims/search use “only draft and keel” is outdated. Reuse accepted criteria/claim accessors and evidence semantics where valid; do **not** build a second independent truth engine by default. |
| Import API retains synchronous work on async route | `src/hullq/api/app.py` `upload_import_route` reads stream asynchronously but invokes sync `open_connection` and `upload_import_for_organization` afterward. | **REQUIRED PRE-REAL-EXTERNAL-BROKER-DATA STOP #355:** bounded isolated parsing/DB/queueing with evidence of search/health responsiveness, cancellation, memory/CPU and adversarial archive handling. |
| DB connection lacks explicit timeout/admission | `src/hullq/persistence/connection.py`: `psycopg.connect(resolved)`; `src/hullq/domain/import_spreadsheet.py` ZIP guard trusts declared `ZipInfo.file_size` aggregate as one bound. | **REQUIRED #355:** timeouts/admission and actual process resource limits tested with malicious/truncated/bomb archives; no inference that metadata bound alone protects native calamine parser. |
| Export may compete with Search under GIL and has control-char edge cases | `src/hullq/domain/inventory_export.py`: three-job executor, formula trigger prefix set `= + - @ TAB`, ASCII control stripping; CSV/ODS/XLSX/XLS have different writer semantics. | **DESIGN PROPOSAL / VERIFY:** concurrent Search vs multiple large exports under realistic load; exercise leading CR/LF, tabs, Unicode controls and negative numeric strings per genuine writer/reimport; do not claim an established exploit or reopen 0088 without confirmed blocking evidence. |

No source-reading observation above substitutes for a real PostgreSQL18/FastAPI/built-Astro SSR or real-adversarial performance gate.

## 3. Binding future claim-search contract (Sail AND Power)

1. Distinguish **BoatDesign generation/NamedVariant/factory configuration** from **current concrete PhysicalBoat installed equipment and seller/publisher claims**. No automatic design → concrete fact promotion; no used-vessel refit details promoted into manufacturer design truth.
2. To qualify technical-search evidence from **design-unresolved** listings, require typed value + unit, independent active publishing eligibility and rights, traceable source/issuer (broker, owner-direct, evidence document, independent check), acceptance/observation time, revision/retraction, applicability and supported criterion-specific proof threshold. Source trust and verification are **not** paid upgrades.
3. **CONFIRMED_MATCH is a technical criterion classification, not necessarily independent verification of who asserted the value.** Explicitly surface “laut Brokerangabe” versus independently verified manufacturer/physical-vessel proof. A separate public verdict or evidence label may be appropriate, but the underlying accepted machine contract must be reviewed before changing it.
4. UNKNOWN is neither confirmed match nor confirmed nonmatch; a contradictory claim is **not silently erased** as absent when user-facing conflict explanation is contractually required. Preserve existing proven “insufficient evidence” semantics until explicitly revised with migration/compatibility and negative tests.
5. **Power-specific facts** need generation/propulsion variants, motor maker/model/count/power/fuel/shaft/stern/pod/outboard/waterjet/hybrid/electric and actual installed engines/refits/hours/maintenance. Operating-point speed/range/consumption claims require compatible speed/RPM, load, sea/measurement basis, usable fuel/reserve and source; bare tank ÷ burn is at most a visibly qualified derivation.
6. Both domains must prove same-configuration AND, source/time conditions, unsupported criteria fail-closed, cross-category exclusion, retraction/freshness, tenant isolation/MFA, public-versus-private rights, authentic import/export roundtrip and accessible five-locale explanations. Power Broker Search-fit **must use exactly the accepted Power truth kernel**; not a parallel ad hoc scorer.
7. The first external marketplace/pilot is **joint Sail+Power** with two genuine specialist Search paths and functioning broker owned import/edit/publish/export/lead/factual report journeys. An internal category browse is never a C-light public product.

Do **not** set made-up numbers for Search response times, matching accuracy, minimum model count, feature count or arbitrary slice limits. Derive test scenarios and acceptability thresholds from real representative benchmark data and explicit Owner review. Document genuine unknowns instead of imposing worldwide catalogue completeness.

## 4. Research, ownership, user value and dependencies

- **Power rights/source study is a separate mandatory preparatory workstream.** Examine actual manufacturer/factual/historical/rights-cleared broker sources, per-source copyright/database/contract/privacy restrictions, access rules and correction/withdrawal path. Build a representative hard-case corpus: shared model with alternative powertrains, repowered boats, missing model, disputed hours, condition-dependent consumption/range; label source type and limitations. Public facts do not justify copying protected photos, prose or entire databases.
- **Sail reference quality first, internally**, followed by category/dual-domain architecture and specialist Power Search, without a partial external Sail-only or C-light pilot. Broker workflow validation is equal in importance to buyer search.
- **Customer-first, not incumbent imitation:** Boats Group [feature ledger](governance/BOATS_GROUP_COMPETITIVE_CAPABILITY_REGISTER_2026-10-16.md) remains an evidence input; real buyer decision quality, truthful technical confidence, genuine broker freedom and lead usefulness set priorities. Broker performance reporting (#357) and controlled real-provisioning/retention (#355) retain independent P0 priority. Listings stay current, deduplicated, accurate and rights-safe; empty results should not be fabricated (consider saved search/alerts separately).
- **Pre-real-external broker data/pilot STOP:** #355 encompasses parser isolation, event-loop resource safety, ZIP limits, trusted proxy client IP, rate-limiter concurrency, bounded PostgreSQL admission/timeouts, import-expiry purge and notification delivery supervision, safe onboarding. Provider/network/HA/backup/restore/observability/rights and production readiness still apply.
- **Brand and launch:** Consumer messaging/SEO cannot imply already shipped Power Technical Search or competitor data entitlements. An independent editorial research website vs early public HullQ product is **a separate Owner/rights/SEO gate**; no blanket permission for Sail-only product pages before joint release. Customer-first/brand PR #365 must be aligned with Sail+Power PR #367; Sail-only taglines are domain-specific, not the permanent all-marketplace identity.
- **Owner local browser test:** tracked #363 around a future selected 0090; reuse local ignored `LOCAL_TEST_HULLQ.bat` / `.py` and validate real boot/SSR only when that phase is selected. Do not reserve a new slice from a tracking issue.

## 5. Explicit implementation follow-through

**This is a requirements/traceability handoff, not an implementation.**

- **Now:** Integrate reconciled Owner Sail+Power document PR #367 and customer-first PR #365; close docs review/CI; prepare separate SLICE-0089 broker **periodic factual reporting** readiness under #357. No Sail+Power code change in 0089.
- **Following independent Owner-selected slices:** rights-and-domain read-only architecture/gap proof, category-import-export/browse truth, design-unresolved concrete claim technical Search for both domains, actual Power generation/propulsion model and conditional measurement criteria, Power Buyer+Broker parity and validated corpus. Split by meaningful independently testable failure domains.
- **Pre-data, before any real broker upload:** block on #355, tested isolated runtime and genuine provider/operations/rights readiness. Full end-to-end and adversarial proof required.
- **At every relevant acceptance closure:** Update tracking issue #372 with actual slice ID and exact HEAD, accepted test/evidence links, changes to design-unresolved candidate set/claim verification or Power coverage. Do not close an obligation based on a specification alone. The outstanding unrelated XLSB export #362 remains open.
- **Queue:** SLICE-0089 remains unstarted until its independently reviewed docs-only READY contract merges and the Owner executes normal `START_SLICE.bat 0089`.

**No modification to current SLICE-0088 accepted work, its acceptance gates, the nine Sail Technical Search dimensions, other pending features or production-gate markers is authorized by this record.**
