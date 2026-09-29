import assert from "node:assert/strict";
import { test } from "node:test";

import {
  contactResultText,
  parseContactResponse,
  shouldRotateSubmissionOperationId,
} from "../buyerLeadForm.ts";

const text = {
  submittingLabel: "Sending...",
  successLabel: "Sent",
  invalidInputLabel: "Check your details",
  listingNotAvailableLabel: "No longer available",
  serviceErrorLabel: "Try again",
};

test("parseContactResponse: 201 CREATED with a well-shaped body is created", () => {
  const outcome = parseContactResponse(201, {
    status: "CREATED",
    lead_id: "LEAD-1",
    received_at: "2026-09-29T00:00:00Z",
  });
  assert.deepEqual(outcome, {
    kind: "created",
    leadId: "LEAD-1",
    receivedAt: "2026-09-29T00:00:00Z",
  });
});

test("parseContactResponse: 200 ALREADY_EXISTS with a well-shaped body is already_exists", () => {
  const outcome = parseContactResponse(200, {
    status: "ALREADY_EXISTS",
    lead_id: "LEAD-1",
    received_at: "2026-09-29T00:00:00Z",
  });
  assert.deepEqual(outcome, {
    kind: "already_exists",
    leadId: "LEAD-1",
    receivedAt: "2026-09-29T00:00:00Z",
  });
});

test("parseContactResponse: a 2xx with a malformed body is a service_error, never a crash", () => {
  assert.deepEqual(parseContactResponse(201, { unexpected: true }), { kind: "service_error" });
  assert.deepEqual(parseContactResponse(201, null), { kind: "service_error" });
});

test("parseContactResponse: 400/404/409 map to their bounded outcomes", () => {
  assert.deepEqual(parseContactResponse(400, { error: "invalid_input" }), {
    kind: "invalid_input",
  });
  assert.deepEqual(parseContactResponse(404, { error: "listing_not_available" }), {
    kind: "listing_not_available",
  });
  assert.deepEqual(parseContactResponse(409, { error: "submission_conflict" }), {
    kind: "submission_conflict",
  });
});

test("parseContactResponse: any other status collapses to service_error", () => {
  assert.deepEqual(parseContactResponse(500, null), { kind: "service_error" });
  assert.deepEqual(parseContactResponse(403, null), { kind: "service_error" });
});

test("contactResultText: every outcome kind maps to its label without throwing", () => {
  assert.equal(contactResultText({ kind: "invalid_input" }, text), text.invalidInputLabel);
  assert.equal(
    contactResultText({ kind: "listing_not_available" }, text),
    text.listingNotAvailableLabel,
  );
  assert.equal(contactResultText({ kind: "submission_conflict" }, text), text.serviceErrorLabel);
  assert.equal(contactResultText({ kind: "service_error" }, text), text.serviceErrorLabel);
  assert.equal(
    contactResultText({ kind: "created", leadId: "L-1", receivedAt: "t" }, text),
    text.successLabel,
  );
  assert.equal(
    contactResultText({ kind: "already_exists", leadId: "L-1", receivedAt: "t" }, text),
    text.successLabel,
  );
});

test("shouldRotateSubmissionOperationId: rotates after success or a conflict", () => {
  assert.equal(
    shouldRotateSubmissionOperationId({ kind: "created", leadId: "L-1", receivedAt: "t" }),
    true,
  );
  assert.equal(
    shouldRotateSubmissionOperationId({ kind: "already_exists", leadId: "L-1", receivedAt: "t" }),
    true,
  );
  assert.equal(shouldRotateSubmissionOperationId({ kind: "submission_conflict" }), true);
});

test("shouldRotateSubmissionOperationId: keeps the identity for a retry-safe failure", () => {
  assert.equal(shouldRotateSubmissionOperationId({ kind: "invalid_input" }), false);
  assert.equal(shouldRotateSubmissionOperationId({ kind: "listing_not_available" }), false);
  assert.equal(shouldRotateSubmissionOperationId({ kind: "service_error" }), false);
});
