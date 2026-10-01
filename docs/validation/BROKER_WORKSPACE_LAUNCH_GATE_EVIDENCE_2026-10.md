# Broker Workspace Launch Gate Evidence — 2026-10

**Slice:** SLICE-0076 — Broker Workspace Launch Validation
**Normative protocol:** `specs/BROKER_WORKSPACE_LAUNCH_VALIDATION_PROTOCOL.v0.1.md`
**Governing gate:** `docs/governance/BROKER_WORKSPACE_LAUNCH_GATE.md` §§9–10
**Candidate commit under test:** `ba0e601` on `slice/0076-broker-workspace-launch-validation`
(amendment-corrected; see `docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md`'s
amendment note)
**Inputs:** `docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md`,
`docs/validation/BROKER_WORKSPACE_COMPETITIVE_BENCHMARK_2026-10.md`

This document does not itself change `BROKER_WORKSPACE_LAUNCH_GATE_STATUS`. Per the slice's
status handoff rule, it records evidence and a recommended disposition for independent
review and explicit Project Owner acceptance.

## 1. Required-behavior findings (slice §"Required behavior / research questions")

1. **Can each of the six required broker tasks complete through user-visible surfaces
   without DB/operator help?** No — five of six (Tasks 1, 2, 3, 4, 6) completed entirely
   through browser-visible surfaces. Task 5 (Lead handling) completed every sub-step except
   Assign, which cannot be completed by a representative broker because no visible surface
   ever displays a usable `AccountId` and there is no member picker.
2. **Where does the participant hesitate, fail, backtrack or need recovery?** The one
   material failure is the Assign sub-step (Task 5). The one deliberately exercised recovery
   path (an invalid YouTube URL in Task 3) produced a clear, specific, non-destructive error
   message with the existing gallery state preserved. Reorder in Task 3 is usable but
   mechanically tedious at scale (numeric position re-entry per item, no drag-and-drop).
3. **Are routine Lead filtering/search and source-context discovery sufficient in
   practice?** Source-context discovery (Task 4) is sufficient — explicit values or explicit
   `UNKNOWN`, never silent omission. Lead filtering/search is **not** demonstrated sufficient
   at realistic volume: only two boolean toggles exist, with no free-text buyer-name/email/
   listing search.
4. **Do media upload/reorder/cover and listing edit/publish flows expose understandable
   recovery when something fails?** Yes for every path actually exercised (invalid YouTube
   URL in Task 3; every edit/publish/sale-outcome action in Tasks 1/2/6 re-reads and displays
   authoritative state rather than a client-invented result).
5. **How do HullQ's launch-critical workflows compare factually with BoatWizard and YATCO
   BOSS using current official evidence?** See the competitive benchmark document; summary
   reproduced in §3 below.
6. **Does any material DEFICIENT result block Launch Gate PASS?** Yes — the Lead-handling
   `BLOCKING_DEFICIENCY` (Assign sub-step) is independently confirmed by both the real-HTTP
   usability execution and the competitive-benchmark documentation reading, and Lead handling
   is one of the four dimensions the protocol (§6) and the Launch Gate (§10) explicitly name
   as PASS-blocking.
7. **Is the correct disposition EVIDENCE_SUPPORTS_PASS_REVIEW, REMEDIATION_REQUIRED or
   VALIDATION_BLOCKED?** **REMEDIATION_REQUIRED** — see §4.

## 2. Usability disposition summary

```text
TASK_1  Create + publish listing       PASS
TASK_2  Edit price / status / details  PASS
TASK_3  Media management               PASS
TASK_4  Lead source identification     PASS
TASK_5  Lead handling                  BLOCKING_DEFICIENCY (Assign sub-step only)
TASK_6  Commercial / sale outcome      PASS
OBS_7   Performance snapshot (untimed) PASS
```

Full per-task evidence (scenario, exact interaction path, timing, friction, errors/recovery):
`docs/validation/BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md`.

## 3. Competitive disposition summary

```text
listing creation/publish        : NOT_COMPARABLE vs BoatWizard; EQUIVALENT vs YATCO BOSS
inventory edit/state management : NOT_COMPARABLE vs both
media management                 : DEFICIENT vs BoatWizard; NOT_COMPARABLE vs YATCO BOSS
Lead source visibility           : NOT_COMPARABLE vs BoatWizard; EQUIVALENT vs YATCO BOSS
Lead handling/filtering          : DEFICIENT vs BoatWizard AND YATCO BOSS  (BLOCKING)
sale/outcome close-out           : BETTER / EQUIVALENT vs YachtCloser; NOT_COMPARABLE vs others
performance reporting            : NOT_COMPARABLE vs both
```

Full evidence/sourcing: `docs/validation/BROKER_WORKSPACE_COMPETITIVE_BENCHMARK_2026-10.md`.
No aggregate score or single winner was produced, per protocol §6.

**Correction note (2026-10-01):** independent exact-head review of reviewed HEAD `28288ef`
(Finding B) found `listing creation/publish` vs. BoatWizard and `Lead source visibility` vs.
BoatWizard had been scored from adjacent competitor capabilities (syndication reach, AI
listing assistance, cross-Lead relationship/intent views) rather than each dimension's own
narrow mechanic. Both are corrected to `NOT_COMPARABLE` above; see the competitive benchmark
document's own correction note for the full rationale. This does not change §4/§5 below: the
Lead-handling finding is unaffected and remains the one genuinely blocking classification.

## 4. Material findings and remediation disposition

### Finding 1 (BLOCKING) — Lead assignment has no discoverable identifier

**Evidence:** `BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` Task 5; corroborated
independently by `BROKER_WORKSPACE_COMPETITIVE_BENCHMARK_2026-10.md` §5.

**Statement:** the Lead detail page's only Assign control is a free-text `AccountId` input.
No Broker Workspace page displays the signed-in broker's own `AccountId`, any other member's
`AccountId`, or any Organization member directory/picker. A representative broker cannot
discover a valid value and cannot complete Lead assignment without operator/API assistance.

**Classification:** material, `BLOCKING_DEFICIENCY` under protocol §5 ("task cannot be
completed through accepted user-visible surfaces"); falls within one of the four
protocol-§6/Launch-Gate-§10 PASS-blocking dimensions (Lead handling).

**Remediation disposition:** `REMEDIATION_REQUIRED`, bounded. The fix is scoped and does not
require new domain modeling: render a per-member-visible identity (e.g. each active
member's display name/email alongside its `AccountId`, or a `<select>` populated from the
Organization's current active membership roster) on the Lead detail Assign control, and/or
surface the signed-in broker's own identity somewhere in the workspace chrome. This is
explicitly out of scope for SLICE-0076 itself (protocol §10 "product fixes discovered during
validation unless separately authorized as a bounded amendment"); it requires a dedicated
follow-up slice or an explicit review-amendment authorization before it is implemented.

### Finding 2 (material, non-blocking) — Media reorder has no bulk/drag-and-drop mechanic

**Evidence:** `BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` Task 3;
`BROKER_WORKSPACE_COMPETITIVE_BENCHMARK_2026-10.md` §3.

**Statement:** gallery reorder is one plain `<form>` per placement with a numeric position
input; no drag-and-drop, no multi-select. BoatWizard's documented February 2026 update
provides bulk multi-select drag-and-drop reorder. Media management is not one of the four
protocol-blocking dimensions, but the mechanic does not scale well past a handful of images.

**Remediation disposition:** `REMEDIATION_REQUIRED`, non-blocking — may be scheduled as
ordinary product-quality follow-up work rather than a pre-pilot gate blocker; does not by
itself prevent a Launch Gate PASS once Finding 1 is corrected.

### Finding 3 (material, non-blocking) — Lead inbox has no free-text search

**Evidence:** `BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` Task 5 (required-behavior
question 3); `BROKER_WORKSPACE_COMPETITIVE_BENCHMARK_2026-10.md` §5.

**Statement:** only two boolean toggles (`unread_only`, `follow_up_due`) exist; no free-text
buyer-name/email/listing search; BoatWizard's October 2025 update documents filtering by
Portal/Office/Sales Rep. Sufficient at the single-Lead volume exercised in this run; not
demonstrated sufficient at realistic multi-Lead volume.

**Remediation disposition:** `REMEDIATION_REQUIRED`, non-blocking for the first bounded
pilot (a small early self-service cohort will not yet have realistic Lead volume), but should
be tracked as a pre-scale commitment alongside the already-DUE REQ_BROKER obligations in
`docs/governance/BROKER_WORKSPACE_MANDATORY_CAPABILITY_REGISTER.md`.

### Finding 4 (minor, non-blocking) — No design/configuration catalog reuse on the draft form

**Evidence:** `BROKER_WORKSPACE_USABILITY_EVIDENCE_2026-10.md` Task 1.

**Statement:** draft fields are plain free text with no autocomplete against any HullQ
design/configuration catalog; every fact must be retyped even when HullQ may already hold
it. Not tied to any currently-DUE Mandatory-Capability-Register obligation (REQ_BROKER_023/
024 concern branding and connectivity-resilient recovery, not catalog-assisted entry).

**Remediation disposition:** `REMEDIATION_REQUIRED` only if a future product decision adds
this as an explicit requirement; no action required for this validation cycle.

No finding in this validation required silently downgrading a blocking result to polish
(protocol §5: "validation must never silently downgrade it to polish") — Finding 1 is
reported as blocking because it is blocking.

## 5. Recommended disposition

```text
EVIDENCE_SUPPORTS_PASS_REVIEW
REMEDIATION_REQUIRED               <-- recommended
VALIDATION_BLOCKED
```

**Recommendation: `REMEDIATION_REQUIRED`.**

Rationale: five of six launch-critical tasks, plus the untimed performance observation,
passed cleanly through real browser-visible surfaces with authoritative re-reads and no
operator intervention. The one blocking finding (Lead assignment) is narrow, well-evidenced,
corroborated by two independent evidence paths, and has a bounded, scoped remediation — it
does not indicate a systemic product-quality problem, but it does concretely fail one of the
four dimensions the Launch Gate explicitly treats as PASS-blocking, so this evidence cannot
itself recommend `EVIDENCE_SUPPORTS_PASS_REVIEW`. Nor does anything found here rise to
`VALIDATION_BLOCKED` (no external competitor evidence was unobtainable in a way that
undermines the whole exercise, and no security defect was discovered — a security defect
would in any case be an immediate Security Hardening Gate concern, not a usability-validation
one).

## 6. Status reaffirmation

```text
BROKER_WORKSPACE_LAUNCH_GATE_STATUS: NOT_READY   (reaffirmed; this document does not change it)
BROKER_SELF_SERVICE_PILOT_STATUS:    NOT_STARTED (reaffirmed)
PAID_BROKER_PLAN_STATUS:             NOT_STARTED (reaffirmed)
SECURITY_HARDENING_GATE:             remains mandatory and unaddressed by this validation;
                                      still required before any real external broker
                                      self-service pilot regardless of this gate's status
```

Any transition of `BROKER_WORKSPACE_LAUNCH_GATE_STATUS` remains subject to independent
exact-head review and explicit Project Owner acceptance, per the Launch Gate document and
this slice's status handoff rule. This evidence record does not authorize Finding 1/2/3's
remediation to be implemented under SLICE-0076; that requires a dedicated follow-up slice or
an explicit review-amendment.
