// SLICE-0056 (independent review finding 1): pure, unit-testable logic for
// `SearchPageBody.astro`'s submit-time field-omission script. Pure HTML
// cannot represent "buyer left this criterion unset" as an omitted GET
// query parameter -- an untouched <select>/<input> still submits
// `name=<empty value>`, and the accepted, tested FastAPI contract treats an
// explicitly present but blank draft_max/keel_configuration value as an
// ambiguous INVALID request, not an absent criterion
// (tests/unit/test_search_read.py::test_empty_draft_max_value_is_invalid,
// test_empty_keel_configuration_value_is_invalid).
//
// Only the exact empty string counts as "untouched" -- a buyer-entered
// whitespace-only value (e.g. `"   "`) is real, non-empty browser input, not
// an untouched control, and must reach FastAPI unmodified so FastAPI's own
// validation -- not this module -- decides it is invalid (Required Behavior
// §A/§B: FastAPI owns validation/canonicalization, the browser must not
// reinterpret invalid input as an absent criterion). Deliberately does NOT
// `.trim()` or otherwise normalize the value.
export function isUntouchedFormFieldValue(value: string): boolean {
  return value === "";
}
