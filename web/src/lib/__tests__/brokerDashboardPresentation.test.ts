// SLICE-0081 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises the pure presentation helpers used by the Organization
// workspace operational dashboard. These functions never decide
// tenancy/readiness themselves; this test proves the *display* decision is
// correct and, critically, that no denial/outage kind is ever worded like a
// successful empty/zero result (mirrors `previewText.test.ts`'s discipline).
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  draftPreviewLabel,
  draftReadinessLabel,
  inventoryReadinessLabel,
  panelUnavailableText,
} from "../brokerDashboardPresentation.ts";

const DENIAL_KINDS = [
  "unauthenticated",
  "mfa_required",
  "publisher_role_required",
  "not_found",
  "invalid_cursor",
  "invalid_window",
  "invalid_page_size",
  "invalid_input",
  "service_error",
  "some_future_unrecognized_kind",
];

for (const kind of DENIAL_KINDS) {
  test(`panelUnavailableText: "${kind}" never reads as a successful empty/zero result`, () => {
    const text = panelUnavailableText(kind);
    assert.ok(text.length > 0);
    assert.doesNotMatch(text, /no (leads?|drafts?|listings?|activity)/i);
    assert.doesNotMatch(text, /\b0\b/);
  });
}

test("panelUnavailableText: distinct denial kinds get distinct wording", () => {
  const unauthenticated = panelUnavailableText("unauthenticated");
  const mfaRequired = panelUnavailableText("mfa_required");
  const publisherRoleRequired = panelUnavailableText("publisher_role_required");
  const notFound = panelUnavailableText("not_found");
  const serviceError = panelUnavailableText("service_error");
  const all = [unauthenticated, mfaRequired, publisherRoleRequired, notFound, serviceError];
  assert.equal(new Set(all).size, all.length);
});

test("inventoryReadinessLabel: DRAFT READY renders as ready to publish", () => {
  assert.equal(
    inventoryReadinessLabel({
      lifecycle_state: "DRAFT",
      publication_readiness: { status: "READY", blockers: [] },
    }),
    "Ready to publish",
  );
});

test("inventoryReadinessLabel: DRAFT BLOCKED discloses the exact blockers", () => {
  const text = inventoryReadinessLabel({
    lifecycle_state: "DRAFT",
    publication_readiness: { status: "BLOCKED", blockers: ["MISSING_BUILD_YEAR_RESPONSE"] },
  });
  assert.match(text, /Blocked/);
  assert.match(text, /MISSING_BUILD_YEAR_RESPONSE/);
});

test("inventoryReadinessLabel: ACTIVE ELIGIBLE renders as live", () => {
  assert.equal(
    inventoryReadinessLabel({ lifecycle_state: "ACTIVE", current_public_status: "ELIGIBLE" }),
    "Live",
  );
});

test("inventoryReadinessLabel: ACTIVE SUPPRESSED discloses the exact suppression reasons", () => {
  const text = inventoryReadinessLabel({
    lifecycle_state: "ACTIVE",
    current_public_status: "SUPPRESSED",
    suppression_reasons: ["OWNER_WITHDRAWN"],
  });
  assert.match(text, /Suppressed/);
  assert.match(text, /OWNER_WITHDRAWN/);
});

test("inventoryReadinessLabel: WITHDRAWN with neither field falls back to the bare lifecycle state", () => {
  assert.equal(inventoryReadinessLabel({ lifecycle_state: "WITHDRAWN" }), "WITHDRAWN");
});

test("draftReadinessLabel: ready true never discloses stale blocker reasons", () => {
  assert.equal(draftReadinessLabel({ ready: true, reasons: [] }), "Ready to promote");
});

test("draftReadinessLabel: ready false discloses the exact server-evaluated reasons", () => {
  const text = draftReadinessLabel({ ready: false, reasons: ["MISSING_ASKING_PRICE_AMOUNT"] });
  assert.match(text, /Not ready/);
  assert.match(text, /MISSING_ASKING_PRICE_AMOUNT/);
});

test("draftPreviewLabel: prefers the boat name claim when present", () => {
  assert.equal(
    draftPreviewLabel({
      draft_id: "DRAFT-1",
      broker_listing_reference: "REF-1",
      "physical_boat.boat_name": "Serenity",
    }),
    "Serenity",
  );
});

test("draftPreviewLabel: falls back to broker_listing_reference, then draft_id", () => {
  assert.equal(
    draftPreviewLabel({ draft_id: "DRAFT-1", broker_listing_reference: "REF-1" }),
    "REF-1",
  );
  assert.equal(draftPreviewLabel({ draft_id: "DRAFT-1", broker_listing_reference: null }), "DRAFT-1");
});
