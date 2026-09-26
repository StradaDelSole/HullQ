// SLICE-0066 (independent exact-head review, PR #252, Finding B) coverage
// for the shared strict build-year form-control parser used by both the
// owner-direct and professional Astro draft editors.
import assert from "node:assert/strict";
import { test } from "node:test";

import { parseBuildYearFormControl } from "../buildYearFormControl.ts";

test("mode absent (null) -> omitted", () => {
  assert.deepEqual(parseBuildYearFormControl(null, null), { kind: "omitted" });
});

test('mode "" -> omitted, even when a year value is somehow present', () => {
  assert.deepEqual(parseBuildYearFormControl("", "1987"), { kind: "omitted" });
});

test('mode "UNKNOWN" -> unknown, year value is never consulted', () => {
  assert.deepEqual(parseBuildYearFormControl("UNKNOWN", null), { kind: "unknown" });
  assert.deepEqual(parseBuildYearFormControl("UNKNOWN", "1987"), { kind: "unknown" });
  assert.deepEqual(parseBuildYearFormControl("UNKNOWN", "garbage"), { kind: "unknown" });
});

test('mode "VALUE_ASSERTION" + a strict integer year -> value_assertion', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "1987"), {
    kind: "value_assertion",
    value: 1987,
  });
});

test('mode "VALUE_ASSERTION" + a year with surrounding whitespace is trimmed then accepted', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "  1987  "), {
    kind: "value_assertion",
    value: 1987,
  });
});

test('mode "VALUE_ASSERTION" + a negative integer year is still a strict integer, accepted', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "-1"), {
    kind: "value_assertion",
    value: -1,
  });
});

test('mode "VALUE_ASSERTION" + blank year -> invalid, never omitted', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", ""), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + whitespace-only year -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "   "), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + absent year field (null) -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", null), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + a garbage-suffixed year ("1987junk") -> invalid, never leniently truncated', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "1987junk"), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + a garbage-prefixed year ("junk1987") -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "junk1987"), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + a decimal year ("1987.5") -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "1987.5"), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + a partial numeric year ("1987 ") with internal whitespace -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "19 87"), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + scientific-notation year ("1e3") -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "1e3"), { kind: "invalid" });
});

test('mode "VALUE_ASSERTION" + a thousands-separator year ("1,987") -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("VALUE_ASSERTION", "1,987"), { kind: "invalid" });
});

test('an unrecognized/tampered mode value ("ABSENT") -> invalid', () => {
  assert.deepEqual(parseBuildYearFormControl("ABSENT", "1987"), { kind: "invalid" });
});

test("a case-mismatched mode value is not leniently accepted", () => {
  assert.deepEqual(parseBuildYearFormControl("unknown", null), { kind: "invalid" });
  assert.deepEqual(parseBuildYearFormControl("value_assertion", "1987"), { kind: "invalid" });
});

test("a File-typed mode value (unexpected form-field shape) -> invalid", () => {
  const fileLike = new File(["x"], "x.txt");
  assert.deepEqual(parseBuildYearFormControl(fileLike, "1987"), { kind: "invalid" });
});
