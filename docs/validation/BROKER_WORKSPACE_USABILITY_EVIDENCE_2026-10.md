# Broker Workspace Usability Evidence — 2026-10

**Slice:** SLICE-0076 — Broker Workspace Launch Validation
**Normative protocol:** `specs/BROKER_WORKSPACE_LAUNCH_VALIDATION_PROTOCOL.v0.1.md`
**Candidate commit under test:** `3e306dd` on `slice/0076-broker-workspace-launch-validation`
(built on the accepted SLICE-0075 product boundary, canonical base
`253bbac52df20435e3a0d319c182d30a1fa3a2fa`)
**Run date:** 2026-10-01
**Participant:** one representative-broker session (`broker-0076-subject`), a single-member
test Organization (`ORG-0076-VALIDATION`), real JIT-provisioned HullQ Account — not a real
external broker (protocol §2/§9: pre-pilot evidence may use a representative participant).

## 1. Harness

`scripts/validate_broker_workspace_launch_readiness.py` runs the full committed vertical
against a real, disposable PostgreSQL schema and three real local HTTP servers: a
deterministic local OIDC/JWKS test issuer, real FastAPI (with a deterministic in-memory
S3-compatible object store substituted only for the absent live Cloudflare R2 credentials,
per `specs/MARKETPLACE_MEDIA_GALLERY_CONTRACT.v0.1.md` §17), and the built Astro/Node SSR
web package — the same three-real-service discipline as this package's other retained
vertical proofs (e.g. `scripts/inspect_broker_workspace_access.py`).

During every timed task the harness, acting as the participant, calls only the exact
browser-visible page URLs and `<form method="POST">` actions a signed-in browser would use
(plus the one documented same-origin streaming upload proxy `media/upload.ts`, mirroring the
page's own client-side upload script byte-for-byte). It never calls FastAPI directly, never
touches SQL, and never uses an operator/admin shortcut during a timed task. Environment
setup (real OIDC login, seeding the test Organization/PUBLISHER membership, MFA step-up) is
untimed, per protocol §2.

Reproduce:

```bash
uv run python scripts/workflow/claude_diag.py run-local-test-db-compact scripts/validate_broker_workspace_launch_readiness.py
```

## 2. Setup time vs. task time

Untimed environment setup (real login, seed Organization/membership, MFA step-up): **1.00s**
(final retained run). This is explicitly excluded from every task's measured duration below,
per protocol §4 ("the evidence must distinguish product-task time from environment setup
time").

## 3. Per-task evidence

Disposition vocabulary per protocol §5: `PASS`, `PASS_WITH_FRICTION`, `BLOCKING_DEFICIENCY`,
`NOT_COMPLETED_ENVIRONMENT`.

### Task 1 — Create + publish listing — **PASS**

**Scenario:** authenticated broker, already knows the vessel's brand/model/build
year/price/location/description, starts and completes a new listing from the ordinary
Organization workspace.

**Duration:** 2.39s. **Material step count:** 12 browser-visible interactions (list drafts →
start draft → fill/save required fields → promote → open media gallery → upload cover image
→ set cover → open inventory → publish).

**Interaction path (exact, from the retained run):**

```text
GET  /broker/organizations/ORG-0076-VALIDATION/drafts            -> 200
POST /broker/organizations/ORG-0076-VALIDATION/drafts             -> 303 (start a draft)
GET  .../drafts/<draft_id>                                        -> 200
POST .../drafts/<draft_id>  (intent=save, required fields)        -> 200 "Saved." + "ready to promote"
POST .../drafts/<draft_id>  (intent=promote)                      -> 200 "Promotion succeeded."
GET  .../inventory/<listing_id>/media                              -> 200 (empty gallery)
POST .../inventory/<listing_id>/media/upload (streamed JPEG)       -> 201 Uploaded
GET  .../inventory/<listing_id>/media                              -> 200 (1 image)
POST .../inventory/<listing_id>/media (action=set_cover)          -> 200 "Cover updated."
GET  .../inventory                                                 -> 200 "Ready to publish"
POST .../inventory (action=publish)                                -> 200 "Published." (ACTIVE)
```

**Friction:** none material. The draft form is plain free-text fields (brand, model, build
year, price, location, description) with no autocomplete/typeahead against any HullQ
design/configuration catalog — every fact the broker "already knows" must still be typed by
hand. This is a minor efficiency observation, not a completion blocker, and is not tied to
any DUE Mandatory-Capability-Register obligation (REQ_BROKER_023/024 concern branding and
recovery, not catalog-assisted entry).

**Errors/recovery exercised:** none in this task (covered in Task 3).

**Operator/admin assistance required:** no.

### Task 2 — Edit price / status / details — **PASS**

**Scenario:** same broker revisits the just-published ACTIVE listing to correct the asking
price and a PhysicalBoat fact, then reconfirms freshness.

**Duration:** 1.24s. **Material step count:** 5 interactions.

```text
GET  .../inventory/<listing_id>/edit                               -> 200
POST .../inventory/<listing_id>/edit (action=save_offer, 87900.00) -> 200 "Saved."; re-read shows 87900.00
POST .../inventory/<listing_id>/edit (action=save_claim, model)    -> 200 "Saved."; re-read shows edited model
GET  .../inventory                                                 -> 200 (Reconfirm control present)
POST .../inventory (action=reconfirm)                               -> 200 "Reconfirmed."; shows "last confirmed"
```

Every edit is followed by an authoritative server re-read showing the actual persisted
value, not a client-invented echo (contract discipline verified directly, not assumed).

**Friction:** none material. **Errors/recovery exercised:** none in this task. **Operator
assistance required:** no.

### Task 3 — Media management — **PASS**

**Scenario:** same broker adds two more photos in one workflow, reorders the gallery, changes
the cover image, and deliberately submits an invalid YouTube link to observe recovery.

**Duration:** 1.42s. **Material step count:** 6 interactions, including one deliberate
invalid-input submission.

```text
POST .../media/upload (image 1)                      -> 201 Uploaded
POST .../media/upload (image 2)                       -> 201 Uploaded
GET  .../media                                        -> 200 (3 images)
POST .../media (action=reorder, swap first two)       -> 200 "Order saved."
POST .../media (action=set_cover, different image)    -> 200 "Cover updated."
POST .../media (action=youtube_add, "not-a-real-url") -> 200 "That YouTube link isn't supported."
```

**Errors/recovery exercised (protocol §3.3 requirement):** the deliberately invalid YouTube
URL produced an explicit, specific, non-crashing message ("That YouTube link isn't
supported.") and the existing gallery/cover state remained fully intact and visible on the
same response — a clear, understandable, recoverable error path.

**Friction:** reordering is one `<form>` per placement with a plain numeric position input
(no drag-and-drop, no multi-select); workable for the 3-image gallery exercised here, but a
real broker reordering a larger gallery would re-key several numeric positions by hand. See
the competitive benchmark for a directly comparable incumbent capability. This is a usability
observation, not a completion blocker.

**Operator assistance required:** no.

### Task 4 — Lead source identification — **PASS**

**Scenario:** an anonymous buyer contacts the Task-1 listing through the ordinary public
contact route (untimed setup, acting as the buyer, not the timed broker-participant); the
broker then opens the Lead inbox to identify the contacted listing and its source.

**Duration:** 0.38s. **Material step count:** 2 interactions.

```text
GET .../leads        -> 200 (new Lead visible)
GET .../leads/<id>    -> 200 (contacted listing id shown; "Acquisition channel: UNKNOWN";
                              "Discovery surface: UNKNOWN")
```

The buyer in this run arrived with no UTM/discovery token (an ordinary direct contact), so
both acquisition channel and discovery surface resolved to the explicit `UNKNOWN` value — an
accepted, explicit outcome per protocol §3/§5 ("identify acquisition/discovery evidence **or
explicit UNKNOWN**"), not a failure. The contacted listing itself is identified unambiguously
and immediately.

**Friction:** none material. **Operator assistance required:** no.

### Task 5 — Lead handling — **BLOCKING_DEFICIENCY**

**Scenario:** same broker marks the Lead read, assigns it, updates its status, sets a
follow-up, adds a note, records a contact attempt, and re-finds it via the inbox filters.

**Duration:** 1.67s (every sub-step below still completed in real HTTP time; the blocking
finding is a completability defect, not a performance one).

```text
POST .../leads/<id> (action=mark_read)                              -> 200 "Done."; now Read
POST .../leads/<id> (action=assign, assignee_account_id=<own email>) -> 200; REJECTED
                      ("not a current active member"/invalid)
POST .../leads/<id> (action=set_status, IN_PROGRESS)                -> 200 "Done."
POST .../leads/<id> (action=set_follow_up, overdue due_at)           -> 200 "Done."
POST .../leads/<id> (action=add_note)                                -> 200 "Done."; note visible
POST .../leads/<id> (action=add_contact_attempt, PHONE)              -> 200 "Done."; visible in timeline
GET  .../leads?follow_up_due=true                                    -> 200 (Lead re-found)
```

**Material finding (BLOCKING_DEFICIENCY, protocol §5 "task cannot be completed through
accepted user-visible surfaces"):** the only Assign control on the Lead detail page is a
free-text "Assign to Account ID" input. No page anywhere in the Broker Workspace — not the
workspace landing, not the draft/inventory/media/Lead/notification/performance pages —
displays the signed-in broker's own `AccountId`, any other member's `AccountId`, or any
Organization member directory/picker. The only value a representative broker could plausibly
try (their own email address, since that is literally the only identifier they know about
themselves) is rejected, because the field requires the opaque internal `AccountId`, not an
email. A representative broker therefore cannot discover any valid value through any visible
surface and cannot complete Lead assignment without operator/API assistance — exactly the
condition protocol §5 defines as blocking. This is independently significant because **Lead
handling** is one of the four dimensions whose material `DEFICIENT`/blocking result the
protocol (§6) and the Launch Gate (§10) name as blocking PASS.

Every other sub-step of Task 5 (mark read, status, follow-up, note, contact attempt,
re-finding via filter) completed cleanly through the visible UI with authoritative re-reads.

**Lead filtering/search sufficiency (required behavior question 3, evaluated explicitly, not
assumed):** the inbox exposes exactly two boolean toggle filters (`unread_only`,
`follow_up_due`) plus an undocumented `status` query parameter with no corresponding UI
control. There is no free-text buyer-name/email/listing search box and no assignee filter.
The follow-up-due toggle did successfully re-find the one Lead in this run once its
follow-up was set overdue — sufficient at this volume — but the inbox provides no mechanism
to search a realistic multi-Lead volume by buyer identity, which is a secondary (non-blocking
on its own, but material) friction finding.

**Operator/admin assistance required:** **yes**, for the Assign sub-step only.

### Task 6 — Commercial / sale outcome — **PASS**

**Scenario:** same broker closes the Task-1 listing as SOLD, explicitly linking the Task-4/5
Lead as the originating Lead, while leaving the achieved price unknown.

**Duration:** 0.81s. **Material step count:** 3 interactions.

```text
GET  .../inventory/<listing_id>/edit                                          -> 200
POST .../inventory/<listing_id>/edit (action=close_as_sold, achieved_amount="",
       originating_lead_id=<Task-4/5 Lead id>)                                -> 200 "Recorded."
       re-read shows: "Current outcome: SOLD ... via Lead <id> (recorded ...)"
       with no achieved-price text rendered (preserved as unknown, not forced to 0/blank-as-zero)
GET  .../inventory                                                            -> 200 (WITHDRAWN)
```

Both governance-required behaviors are directly demonstrated in one real run: the unknown
achieved price is preserved rather than forced to a fabricated value, and the originating
Lead is linked only because it was explicitly selected by the broker (never inferred). The
resulting lifecycle transition (ACTIVE → WITHDRAWN on SOLD close-out) is visible on the
authoritative inventory re-read.

**Friction:** none material. **Operator assistance required:** no.

### Observation 7 — Factual performance / funnel snapshot (untimed) — **PASS**

**Scenario:** same broker locates the Organization's performance snapshot after the above
activity.

```text
GET .../performance?window=ALL_TIME -> 200
    "Leads received: 1"
    "Explicit SOLD outcomes recorded in window: 1"
```

The broker can locate the snapshot from the workspace landing (one link) and the window
immediately reflects this run's real activity — a genuine, understandable, non-vanity
factual snapshot, consistent with SLICE-0075's accepted scope.

## 4. Consolidated disposition inputs

```text
TASK_1  PASS
TASK_2  PASS
TASK_3  PASS
TASK_4  PASS
TASK_5  BLOCKING_DEFICIENCY  (Assign-to-AccountId sub-step only; all other sub-steps PASS)
TASK_6  PASS
OBS_7   PASS (untimed)
```

One material `BLOCKING_DEFICIENCY` was found, in Lead handling — one of the four dimensions
the protocol and Launch Gate name as blocking PASS. See
`docs/validation/BROKER_WORKSPACE_LAUNCH_GATE_EVIDENCE_2026-10.md` for the consolidated
disposition and remediation recommendation.
