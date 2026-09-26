// SLICE-0066 (independent exact-head review, PR #252, Finding B): the one
// shared strict parser for the owner-direct and professional draft editors'
// build-year form controls (`physical_boat.build_year.assertion_kind` +
// `physical_boat.build_year`), so the two Astro pages cannot drift into two
// different lenient/strict interpretations of the same three-state control.
//
// `specs/LISTING_ASSERTION_RESPONSE_CONTRACT.v0.1.md` §8 requires the browser
// to represent exactly three unambiguous states -- not answered / known year
// / explicit unknown -- and forbids inferring UNKNOWN from a blank year and
// forbids silently converting an invalid "known year" submission into
// omission. The pre-fix Astro handlers used `Number.parseInt()` and only
// emitted a VALUE_ASSERTION when parsing produced a finite value: a blank or
// malformed year (e.g. "1987junk", parsed leniently by `parseInt` as `1987`)
// therefore either silently vanished into omission or was silently
// truncated to a fabricated integer, bypassing the strict domain validator
// already implemented correctly in `hullq.domain.listing_draft_payload`.
//
// This module fails closed instead: a malformed/tampered mode value or a
// non-strict-integer year under `VALUE_ASSERTION` reports `"invalid"`, which
// the calling page must render as its existing zero-mutation invalid-save
// state (contract §10/§9: never partially accept a payload) -- it must
// never reach the FastAPI update call at all for that request.

/** The exact strict-integer year-literal shape: optional leading `-`, digits
 * only -- no leading/trailing whitespace (the caller trims first), no
 * decimal point, no exponent, no thousands separator, no trailing garbage
 * such as "1987junk". */
const STRICT_INTEGER_PATTERN = /^-?[0-9]+$/;

export type BuildYearFormControlResult =
  | { kind: "omitted" }
  | { kind: "unknown" }
  | { kind: "value_assertion"; value: number }
  | { kind: "invalid" };

/**
 * Parses the two build-year form fields into exactly one of the four
 * outcomes above. `modeRaw` and `yearRaw` are the raw `FormData.get(...)`
 * results for `physical_boat.build_year.assertion_kind` and
 * `physical_boat.build_year` respectively.
 *
 * - mode absent or `""` -> `omitted` (true unanswered state; a blank year
 *   value is never consulted or inferred as UNKNOWN);
 * - mode `"UNKNOWN"` -> `unknown` (the year field is never read: contract §8
 *   "when UNKNOWN is selected, no year value may be submitted");
 * - mode `"VALUE_ASSERTION"` -> `value_assertion` only when the year field is
 *   present and, after trimming, matches the strict integer pattern above;
 *   otherwise `invalid` -- a blank, decimal, partial-numeric or
 *   garbage-suffixed year never silently becomes omission or a truncated
 *   guess;
 * - any other mode value (a tampered/forged control submission, e.g.
 *   `"ABSENT"`) -> `invalid`.
 */
export function parseBuildYearFormControl(
  modeRaw: FormDataEntryValue | null,
  yearRaw: FormDataEntryValue | null,
): BuildYearFormControlResult {
  if (modeRaw === null || modeRaw === "") return { kind: "omitted" };
  if (typeof modeRaw !== "string") return { kind: "invalid" };
  if (modeRaw === "UNKNOWN") return { kind: "unknown" };
  if (modeRaw !== "VALUE_ASSERTION") return { kind: "invalid" };

  if (typeof yearRaw !== "string") return { kind: "invalid" };
  const trimmed = yearRaw.trim();
  if (!STRICT_INTEGER_PATTERN.test(trimmed)) return { kind: "invalid" };
  return { kind: "value_assertion", value: Number.parseInt(trimmed, 10) };
}
