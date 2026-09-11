// SLICE-0050 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises the pure display-text helpers that decide omitted/UNKNOWN/
// VALUE_ASSERTION wording for the "THIS BOAT" section. These functions
// never touch the DOM, so this test proves the *decision* is correct; the
// full escaped-rendering proof against a real HTTP response body runs in
// the SLICE-0050 owner-visible end-to-end inspection script.
import assert from "node:assert/strict";
import { test } from "node:test";

import { boatClaimText, boatClaimTextOrNotSupplied } from "../physicalBoatClaimText.ts";

test("boatClaimText: omission (null field) stays null", () => {
  assert.equal(boatClaimText(null), null);
});

test("boatClaimText: VALUE_ASSERTION returns the value", () => {
  assert.equal(boatClaimText({ assertion_kind: "VALUE_ASSERTION", value: "9.14" }), "9.14");
});

test("boatClaimText: VALUE_ASSERTION with a numeric value is stringified", () => {
  assert.equal(boatClaimText({ assertion_kind: "VALUE_ASSERTION", value: 2021 }), "2021");
});

test("boatClaimText: UNKNOWN renders as 'unknown', distinct from omission", () => {
  assert.equal(boatClaimText({ assertion_kind: "UNKNOWN", value: null }), "unknown");
});

test("boatClaimTextOrNotSupplied: omission renders as 'not supplied'", () => {
  assert.equal(boatClaimTextOrNotSupplied(null), "not supplied");
});

test("boatClaimTextOrNotSupplied: UNKNOWN stays distinct from omission's 'not supplied' text", () => {
  assert.equal(boatClaimTextOrNotSupplied({ assertion_kind: "UNKNOWN", value: null }), "unknown");
});

test("boatClaimTextOrNotSupplied: VALUE_ASSERTION returns the value", () => {
  assert.equal(
    boatClaimTextOrNotSupplied({ assertion_kind: "VALUE_ASSERTION", value: "FIN" }),
    "FIN",
  );
});
