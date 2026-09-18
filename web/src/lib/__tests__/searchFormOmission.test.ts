// SLICE-0056 independent review finding 1 regression coverage: only a
// genuinely untouched control (exact empty string) is treated as an absent
// criterion. A buyer-entered whitespace-only value is real browser input and
// must NOT be treated as untouched -- it must reach FastAPI so FastAPI's own
// validation (not this browser-side logic) decides it is invalid.
import assert from "node:assert/strict";
import { test } from "node:test";

import { isUntouchedFormFieldValue } from "../searchFormOmission.ts";

test("isUntouchedFormFieldValue: the exact empty string is untouched", () => {
  assert.equal(isUntouchedFormFieldValue(""), true);
});

test("isUntouchedFormFieldValue: a whitespace-only value is NOT untouched", () => {
  assert.equal(isUntouchedFormFieldValue("   "), false);
  assert.equal(isUntouchedFormFieldValue(" "), false);
  assert.equal(isUntouchedFormFieldValue("\t"), false);
});

test("isUntouchedFormFieldValue: any other non-empty value is NOT untouched", () => {
  assert.equal(isUntouchedFormFieldValue("1.6"), false);
  assert.equal(isUntouchedFormFieldValue("FIN"), false);
  assert.equal(isUntouchedFormFieldValue("1e0"), false);
});
