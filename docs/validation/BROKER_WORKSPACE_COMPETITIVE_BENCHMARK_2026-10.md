# Broker Workspace Competitive Benchmark — 2026-10

**Slice:** SLICE-0076 — Broker Workspace Launch Validation
**Normative protocol:** `specs/BROKER_WORKSPACE_LAUNCH_VALIDATION_PROTOCOL.v0.1.md` §6
**Primary references:** BoatWizard / Boats Group, YATCO BOSS
**Supplementary reference:** YachtCloser (deal/SOLD workflow only)
**Evidence basis for HullQ:** the real-HTTP run recorded in
`docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` plus direct source reading
of the exact candidate-commit Astro/FastAPI code paths exercised by that run.
**Evidence basis for competitors:** current public vendor marketing/help-center pages,
accessed 2026-10-01 (URLs and quoted claims below). No competitor account was created; no
member-only/logged-in competitor behavior is claimed. Per protocol §6, inaccessible behavior
is classified `NOT_COMPARABLE`, never guessed.

Classification vocabulary (protocol §6): `BETTER`, `EQUIVALENT`, `DEFICIENT`,
`NOT_COMPARABLE`. No aggregate score or overall winner is produced.

## 1. Listing creation / publish workflow

**HullQ:** free-text draft fields (brand, model, build year, price, location, description) →
readiness check → promote → add minimum publishable media → publish. Verified directly: all
required fields are enforced by a single canonical `evaluate_promotion_readiness` rule set,
and publish is separately blocked until a public-usable cover image exists
(`evaluate_publication_readiness`, `COVER_MISSING`/`NO_PUBLIC_USABLE_IMAGE`). No
catalog-assisted autocomplete for brand/model.

**BoatWizard:** "the industry's leading inventory management and marketing platform... allows
users to easily manage and update listings across multiple marketplaces, including
YachtWorld, Boat Trader, and boats.com" (Boats Group, [BoatWizard product
page](https://www.boatsgroup.com/boatwizard/), accessed 2026-10-01, via indexed content —
the live page itself returned HTTP 403 to automated fetch at access time). Boats Group also
operates an AI "Listing Optimizer" that evaluates listings and recommends changes to improve
search visibility ([Boats Group Launches AI Listing
Optimizer](https://techedgeai.com/boats-group-adds-ai-to-optimize-boat-listings/), accessed
2026-10-01).

**YATCO BOSS:** Fleet Manager lets a broker "upload, organize, and manage data for each yacht
in their fleet" and "add and update yacht details, from specifications to availability"
through a drag-and-drop interface ([What is the YATCO BOSS Fleet
Manager?](https://blog.yatco.com/what-is-fleet-manager/), accessed 2026-10-01).

**Classification:**

- vs. BoatWizard: **DEFICIENT.** BoatWizard's documented one-platform-to-multiple-marketplace
  syndication (YachtWorld/Boat Trader/boats.com) and AI listing-quality assistance have no
  HullQ equivalent; HullQ publishes only to its own native Search. This is expected at this
  product stage (HullQ is a native-first marketplace, not a syndication hub) and is not one
  of the four protocol-blocking dimensions, but it is a genuine, material functional gap
  broader distribution-minded brokers will notice.
- vs. YATCO BOSS: **EQUIVALENT.** Both are a plain structured-field data-entry workflow for
  core vessel/listing facts; neither vendor's publicly documented material shows a
  materially richer or poorer single-listing creation mechanic than the other.

## 2. Inventory edit / state management

**HullQ:** verified directly — explicit `DRAFT → ACTIVE → WITHDRAWN` lifecycle plus a
separate freshness/reconfirmation axis (`last confirmed` timestamp) and a separate explicit
`SaleOutcome` axis, never overloading one status field (Launch Gate §4 requirement,
demonstrated live in Task 2/Task 6 of the usability evidence: reconfirm updates freshness
only; close-as-SOLD transitions lifecycle to WITHDRAWN and records outcome separately).

**YATCO BOSS:** Fleet Manager offers "Automated Availability Tracking" (available /
under maintenance / booked) and "Visual Timelines" for charter/maintenance scheduling
([What is the YATCO BOSS Fleet
Manager?](https://blog.yatco.com/what-is-fleet-manager/), accessed 2026-10-01).

**Classification:**

- vs. BoatWizard: **NOT_COMPARABLE.** No accessible public material describes BoatWizard's
  specific inventory lifecycle/state model in enough mechanical detail to compare against
  HullQ's explicit multi-axis model; guessing would violate protocol §6.
- vs. YATCO BOSS: **NOT_COMPARABLE.** YATCO's documented availability tracking is oriented
  toward charter-fleet scheduling (available/maintenance/booked), a different domain than a
  brokerage sale-listing lifecycle; the two are not measuring the same thing and a
  BETTER/DEFICIENT call would not be evidence-backed.

## 3. Media management

**HullQ:** verified directly in the Task 1/Task 3 real run — multi-file image upload in one
workflow (same-origin streaming proxy, one request per file), per-placement reorder via a
plain numeric-position `<form>` (no drag-and-drop, no multi-select), explicit cover
set/clear, same-Organization reuse, YouTube add with an explicit rejection message on an
invalid URL, up to 15,000,000 bytes (15 MB) per image.

**BoatWizard:** February 2026 update added "Manage Photos in Bulk," letting users "select
multiple photos at once and drag and drop them into their preferred order," including
checkbox multi-select followed by dragging the whole selected group to reorder at once
([BoatWizard Update: February
2026](https://www.boatsgroup.com/boatwizard-update-february-2026/), accessed 2026-10-01, via
indexed content). Supported formats JPG/PNG/HEIC, up to 15 MB per photo and 50 MB combined
per listing (same source).

**YATCO BOSS:** no photo/media-management detail is present in the Fleet Manager material
accessed for this benchmark.

**Classification:**

- vs. BoatWizard: **DEFICIENT.** BoatWizard's documented bulk multi-select drag-and-drop
  reorder is a materially more efficient mechanic than HullQ's current one-row-at-a-time
  numeric-position form, which becomes increasingly tedious as gallery size grows (observed
  directly reordering 3 images in the real run; the mechanic does not scale). This is a
  real, material, non-blocking (media management is not one of the four protocol-blocking
  dimensions) finding with a clear, bounded remediation target: add drag-and-drop/multi-select
  reorder to `media.astro`.
- vs. YATCO BOSS: **NOT_COMPARABLE** (no accessible detail to compare against).

## 4. Lead source visibility

**HullQ:** verified directly — Lead detail always shows the contacted listing and explicit
`acquisition_channel` / `discovery_surface` values, falling back to the explicit `UNKNOWN`
value (never silently omitted) when no UTM/discovery-token evidence is present, demonstrated
live in Task 4.

**BoatWizard:** the October 2025 Leads-page refresh lets a user "quickly search and filter
leads by Portal, Office, or Sales Rep," "click into a Contact to view other listings they've
inquired about," and "view buyer intent details within the Contact section" ([BoatWizard
Update: October 2025](https://www.boatsgroup.com/boatwizard-update-october-2025/), accessed
2026-10-01, via indexed content).

**YATCO BOSS:** the CRM lets a company "Create Lead Sources suitable for your own company to
differentiate and better evaluate the channels your quality leads come from," and maintains
"a complete list of all interactions you have had with a contact, including tasks, emails,
and website activity" ([CRM Sales Manager](https://www.yatco.com/yatco-boss/crm-lead-manager/),
accessed 2026-10-01).

**Classification:**

- vs. BoatWizard: **DEFICIENT.** BoatWizard's cross-listing "other listings this Contact has
  inquired about" and "buyer intent" views have no HullQ equivalent; HullQ's Lead detail is
  scoped to the single contacted listing only. HullQ's per-field explicit-UNKNOWN provenance
  discipline is a genuine strength but does not offset this missing cross-listing/intent
  context, which real brokers managing repeat inquirers would notice. Non-blocking on its own
  (source *identification* for the single Lead itself — the protocol-blocking dimension —
  works correctly and was demonstrated PASS in Task 4), but material and worth a bounded
  remediation target.
- vs. YATCO BOSS: **EQUIVALENT.** Both expose a per-Lead source/channel value and a durable
  interaction history; YATCO's company-custom source taxonomy vs. HullQ's fixed acquisition/
  discovery vocabulary are different designs without a clear quality delta from the
  accessible material.

## 5. Lead handling / filtering / follow-up

**HullQ:** verified directly in the Task 5 real run — mark read, status update, follow-up
due-date, free-text notes, and contact-attempt recording all completed cleanly with
authoritative re-reads. **Assignment did not complete**: the only Assign control requires an
opaque `AccountId` that is displayed nowhere in the Broker Workspace, with no member
directory/picker, so a representative broker cannot discover a valid value and cannot
complete assignment without operator/API assistance (`BROKER_WORKSPACE_USABILITY_EVIDENCE_
2026-10.md` Task 5). Inbox filtering is limited to two boolean toggles (unread-only,
follow-up-due); there is no free-text buyer-name/email/listing search.

**BoatWizard:** the same October 2025 update lets a broker "search and filter leads by
Portal, Office, or Sales Rep," with bulk comment-expand and per-Contact history
([BoatWizard Update: October 2025](https://www.boatsgroup.com/boatwizard-update-october-2025/),
accessed 2026-10-01, via indexed content) — implying Leads are routinely assignable/attributed
to a named Sales Rep in a way the broker can filter by, which HullQ's current Assign control
cannot even be completed to establish.

**YATCO BOSS:** "Email & Tasks" lets a user "Assign them tasks and receive email reminders for
completion" against named contacts organized into custom Lists ([What is the YATCO CRM Lead
Manager](https://blog.yatco.com/what-is-crm-lead-manager/), accessed 2026-10-01).

**Classification:**

- vs. BoatWizard: **DEFICIENT.** BoatWizard's multi-dimension (Portal/Office/Sales Rep)
  filtering is materially richer than HullQ's two-toggle filter, and — more materially —
  BoatWizard's filterable "Sales Rep" implies a working, discoverable assignment mechanic,
  which HullQ's current Assign control lacks entirely for a representative broker. **This is
  a material finding in one of the four protocol/Launch-Gate-blocking dimensions
  (protocol §6, Launch Gate §10: "a material DEFICIENT result in... Lead handling... blocks
  PASS").**
- vs. YATCO BOSS: **DEFICIENT**, for the identical reason: YATCO's documented task-assignment
  mechanic against named contacts implies a discoverable assignee identity that HullQ's
  current UI does not provide.

## 6. Explicit sale / outcome close-out

**HullQ:** verified directly in the Task 6 real run — a single explicit "Close as SOLD" form
on the listing's edit page accepts sold date, achieved price (optional — left blank in the
real run and the resulting state correctly showed no achieved-price text rather than a
fabricated value), achieved currency, and an explicitly-selected originating Lead id; the
re-read confirmed the linkage and the lifecycle transition to WITHDRAWN.

**YachtCloser (supplementary reference):** "Finalize as SOLD" requires the broker to "Enter
two pieces of information and submit": "Date Sold or Closed Date" and "Final Sale Price"
([How to Mark Inventory as
Sold](https://support.yachtcloser.com/article/199-how-to-mark-inventory-as-sold), accessed
2026-10-01). The documented flow does not describe an option to leave the sale price blank
or unknown; if a deal was created from the inventory record, marking the deal SOLD
auto-transitions the linked inventory record (same source).

**Classification:**

- vs. YachtCloser: **BETTER**, specifically on unknown-price preservation. YachtCloser's
  documented close-out flow asks for Final Sale Price as one of exactly two fields to
  "Enter... and submit," with no documented unknown/blank option, whereas HullQ's close-out
  explicitly supports and correctly preserves an unknown achieved price — a direct
  demonstration of HullQ's strict-truth/no-invented-value discipline (`docs/PRODUCT_
  EXECUTION_PLAN.md` principle) against a real competitor's documented, more rigid
  requirement. On the base mechanic (one short explicit close-out flow, SOLD driving the
  listing's own state), the two are otherwise **EQUIVALENT**.
- vs. BoatWizard / YATCO BOSS: **NOT_COMPARABLE.** No accessible public material for either
  vendor documents an explicit sale/outcome close-out flow distinct from general inventory
  status changes.

## 7. Listing / performance reporting

**HullQ:** verified directly — a factual, non-vanity snapshot (views → Leads → contacted →
closed → SOLD, with a Lead acquisition/discovery source breakdown and per-listing table,
plus a median first-contact-latency figure), windowed and immediately reflecting the real
run's activity (Observation 7).

**BoatWizard:** "new and enhanced Performance Insights Reports in BoatWizard... provide
exclusive, real-time visibility into how inventory is discovered, viewed, and engaged with
online" ([Boats Group Announces New Performance Insights
Reports](https://www.boatsgroup.com/new-performance-insights-reports/), accessed 2026-10-01,
via indexed content; the live page itself returned HTTP 403 to automated fetch at access
time, so only the publicly indexed summary, not the full page, was read).

**YATCO BOSS:** no performance-reporting detail is present in the material accessed for this
benchmark.

**Classification:**

- vs. BoatWizard: **NOT_COMPARABLE.** The only accessible description of BoatWizard's
  Performance Insights is a short indexed summary ("real-time visibility into how inventory
  is discovered, viewed, and engaged with online") without enough mechanical detail (exact
  metrics, funnel stages, source/office/rep breakdown) to responsibly classify
  BETTER/EQUIVALENT/DEFICIENT against HullQ's documented funnel; a direct page fetch was
  blocked (HTTP 403) at access time. Guessing the missing detail would violate protocol §6.
- vs. YATCO BOSS: **NOT_COMPARABLE** (no accessible detail to compare against).

## 8. Source list (all accessed 2026-10-01)

- Boats Group, [BoatWizard product page](https://www.boatsgroup.com/boatwizard/) — direct
  fetch returned HTTP 403; content read via indexed search summary only.
- Boats Group, [BoatWizard Update: October
  2025](https://www.boatsgroup.com/boatwizard-update-october-2025/) — indexed summary only
  (direct fetch blocked for this domain at access time).
- Boats Group, [BoatWizard Update: February
  2026](https://www.boatsgroup.com/boatwizard-update-february-2026/) — indexed summary only.
- Boats Group, [Boats Group Announces New Performance Insights
  Reports](https://www.boatsgroup.com/new-performance-insights-reports/) — direct fetch
  returned HTTP 403; indexed summary only.
- Boats Group, [Boats Group Launches AI Listing
  Optimizer](https://techedgeai.com/boats-group-adds-ai-to-optimize-boat-listings/)
  (third-party coverage) — indexed summary only.
- BoatWizard Help Center, [Lead Response - Timing Is
  Everything](https://support.boatwizard.com/article/511-lead-response-timing-is-everything)
  — fetched directly; last updated 2024-03-18 per the article itself (contains no
  BoatWizard-specific response-time reporting feature detail, only general best-practice
  advice).
- YATCO, [What is the YATCO BOSS Fleet
  Manager?](https://blog.yatco.com/what-is-fleet-manager/) — fetched directly.
- YATCO, [CRM Sales Manager](https://www.yatco.com/yatco-boss/crm-lead-manager/) — fetched
  directly.
- YATCO, [What is the YATCO CRM Lead
  Manager](https://blog.yatco.com/what-is-crm-lead-manager/) — indexed summary only.
- YachtCloser Help Center, [How to Mark Inventory as
  Sold](https://support.yachtcloser.com/article/199-how-to-mark-inventory-as-sold) — fetched
  directly.

## 9. Summary of material classifications

```text
listing creation/publish        : DEFICIENT vs BoatWizard (no syndication/AI optimizer);
                                   EQUIVALENT vs YATCO BOSS
inventory edit/state management : NOT_COMPARABLE vs both (insufficient public detail)
media management                 : DEFICIENT vs BoatWizard (no bulk/drag reorder);
                                   NOT_COMPARABLE vs YATCO BOSS
Lead source visibility           : DEFICIENT vs BoatWizard (no cross-listing/intent view);
                                   EQUIVALENT vs YATCO BOSS
Lead handling/filtering          : DEFICIENT vs BoatWizard AND vs YATCO BOSS
                                   (BLOCKING — one of the four protocol-named dimensions)
sale/outcome close-out           : BETTER vs YachtCloser (unknown-price preservation);
                                   EQUIVALENT vs YachtCloser (base mechanic);
                                   NOT_COMPARABLE vs BoatWizard/YATCO BOSS
performance reporting            : NOT_COMPARABLE vs both (insufficient public detail)
```

No overall numeric score or single winner is produced, per protocol §6. The one blocking
competitive finding (Lead handling) corresponds exactly to the independently-discovered
usability `BLOCKING_DEFICIENCY` in `BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` Task 5 —
two independent evidence paths (direct real-HTTP usability execution, and competitor
documentation reading) converge on the same gap.
