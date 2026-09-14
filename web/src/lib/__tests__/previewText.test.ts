// SLICE-0048 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises the pure display-text helpers that decide omission/UNKNOWN/
// NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED/VALUE_ASSERTION wording. These
// functions never touch the DOM, so this test proves the *decision* is
// correct; the full escaped-rendering proof against a real broker string
// runs in the SLICE-0048 owner-visible end-to-end inspection script
// (scripts/inspect_first_visible_listing_preview.py), which exercises a
// real HTTP response body.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  askingPriceText,
  brokerSummaryText,
  freshnessDisclosureText,
  knownHistoryText,
  offerRecordedText,
  unknownableClaimText,
} from "../previewText.ts";

test("unknownableClaimText: omission stays null", () => {
  assert.equal(unknownableClaimText(null), null);
});

test("unknownableClaimText: VALUE_ASSERTION returns the value", () => {
  assert.equal(
    unknownableClaimText({ assertion_kind: "VALUE_ASSERTION", value: "Brittany" }),
    "Brittany",
  );
});

test("unknownableClaimText: UNKNOWN renders as 'unknown', never omitted", () => {
  assert.equal(unknownableClaimText({ assertion_kind: "UNKNOWN", value: null }), "unknown");
});

test("brokerSummaryText: NOT_APPLICABLE renders as absent, distinct from omission's null return shape", () => {
  assert.equal(brokerSummaryText({ assertion_kind: "NOT_APPLICABLE", value: null }), null);
  assert.equal(brokerSummaryText(null), null);
});

test("knownHistoryText: NO_KNOWN_HISTORY_DECLARED is never rendered as proof of no history", () => {
  const text = knownHistoryText({ assertion_kind: "NO_KNOWN_HISTORY_DECLARED", value: null });
  assert.match(text ?? "", /not proof/i);
});

test("knownHistoryText: UNKNOWN is distinct wording from NO_KNOWN_HISTORY_DECLARED", () => {
  const unknownText = knownHistoryText({ assertion_kind: "UNKNOWN", value: null });
  const declaredText = knownHistoryText({ assertion_kind: "NO_KNOWN_HISTORY_DECLARED", value: null });
  assert.notEqual(unknownText, declaredText);
});

test("askingPriceText: AMOUNT mode shows amount and currency, never invents a price", () => {
  assert.equal(
    askingPriceText({ asking_price_mode: "AMOUNT", asking_price_amount: "125000.00", currency: "EUR" }),
    "125000.00 EUR",
  );
});

test("askingPriceText: POA mode shows the price-on-application notice, no synthetic amount", () => {
  assert.equal(
    askingPriceText({ asking_price_mode: "POA", asking_price_amount: null, currency: null }),
    "Price on application",
  );
});

test("freshnessDisclosureText: DUE_FOR_CONFIRMATION is never worded as simply confirmed", () => {
  const dueText = freshnessDisclosureText("DUE_FOR_CONFIRMATION", "2026-01-01T00:00:00+00:00");
  const confirmedText = freshnessDisclosureText("CONFIRMED", "2026-01-01T00:00:00+00:00");
  assert.notEqual(dueText, confirmedText);
  assert.doesNotMatch(dueText, /^Confirmed current/);
});

test("freshnessDisclosureText: CONFIRMED includes the last-confirmed timestamp when present", () => {
  const text = freshnessDisclosureText("CONFIRMED", "2026-01-01T00:00:00+00:00");
  assert.match(text, /2026-01-01T00:00:00\+00:00/);
});

test("freshnessDisclosureText: handles a null last_confirmed_at without throwing", () => {
  assert.doesNotThrow(() => freshnessDisclosureText("CONFIRMED", null));
  assert.doesNotThrow(() => freshnessDisclosureText("DUE_FOR_CONFIRMATION", null));
});

// PR #193 exact-head review: `offer_recorded_at` is the LISTING_OFFER
// revision timestamp, not the SLICE-0052 freshness confirmation timestamp.
// After an authorized reconfirmation without a new offer revision,
// `last_confirmed_at` advances while `offer_recorded_at` does not -- the
// rendered page must never present `offer_recorded_at` as "last confirmed".
test("offerRecordedText: never claims freshness/last-confirmed semantics", () => {
  const text = offerRecordedText("2026-01-01T00:00:00+00:00");
  assert.doesNotMatch(text, /confirmed/i);
});

test("offerRecordedText: post-reconfirmation, a differing offer_recorded_at and last_confirmed_at are never conflated", () => {
  const offerRecordedAt = "2026-01-01T00:00:00+00:00";
  const lastConfirmedAt = "2026-02-05T00:00:00+00:00"; // advanced by reconfirmation alone
  const offerText = offerRecordedText(offerRecordedAt);
  const freshnessText = freshnessDisclosureText("CONFIRMED", lastConfirmedAt);
  assert.match(offerText, /Broker declaration recorded in HullQ/);
  assert.doesNotMatch(offerText, /last confirmed/i);
  assert.equal(offerText.includes(lastConfirmedAt), false);
  assert.equal(freshnessText.includes(offerRecordedAt), false);
  assert.notEqual(offerText, freshnessText);
});
