// SLICE-0057: parse one posted sensitivity form + classify FastAPI's
// response, independent of any Astro rendering context -- mirrors
// `./searchPageData.ts`'s own separation (a plain TypeScript module so the
// top-level `web/src/pages/{locale}/search/sensitivity.astro` page's own
// frontmatter can make any response-mutating call, while presentation itself
// stays in the shared, purely presentational `SearchSensitivityBody.astro`).
import {
  postSearchSensitivity,
  type SensitivityResultBody,
} from "./searchSensitivityApi.ts";
import type { SupportedLocale } from "./searchText.ts";

export type SearchSensitivityPageData =
  | { kind: "invalid"; message: string | null }
  | { kind: "unavailable" }
  | { kind: "ok"; result: SensitivityResultBody };

const _CURRENT_KEYS = ["draft_max", "keel_configuration"] as const;

/**
 * Build the raw `current` map FastAPI expects from the posted form's hidden
 * `current_draft_max`/`current_keel_configuration` fields (contract §12:
 * "transports the current canonical active values plus exactly one changed
 * criterion/value").
 *
 * Independent review Finding 2 (2026-09-19): unlike the *ordinary* Search
 * form's untouched-`<select>`/`<input>` omission (`SearchPageBody.astro`'s
 * own `isUntouchedFormFieldValue` disabling, which applies only to that
 * GET-query-building form), the sensitivity form's `current_*` hidden
 * fields are never buyer-editable -- `SearchPageBody.astro` only ever
 * renders one for a criterion that is genuinely active, always with its
 * exact canonical value. So on this transport there is no legitimate
 * "buyer left it blank" state to interpret: a *present* `current_draft_max`/
 * `current_keel_configuration` field, even `""`, can only mean tampered or
 * malformed current state, and must reach FastAPI exactly as posted so the
 * accepted application/domain validation (`hullq.application.
 * search_sensitivity.evaluate_requirement_sensitivity`) can fail closed
 * with 400 -- never silently reinterpreted here as "criterion inactive",
 * which would narrow the current requirement into a different, unintended
 * sensitivity comparison. Only a field's true *absence* (`formData.get`
 * returning `null`) means "this criterion was not active"; this function
 * remains a raw-value carrier, never a second Search/current-requirement
 * parser (contract §4/§9).
 */
function currentRequirementFromFormData(formData: FormData): Record<string, string> {
  const current: Record<string, string> = {};
  for (const key of _CURRENT_KEYS) {
    const raw = formData.get(`current_${key}`);
    if (typeof raw === "string") {
      current[key] = raw;
    }
  }
  return current;
}

export async function loadSearchSensitivityPageData(
  apiBaseUrl: string,
  locale: SupportedLocale,
  formData: FormData,
): Promise<SearchSensitivityPageData> {
  const current = currentRequirementFromFormData(formData);
  const changedCriterion = formData.get("changed_criterion");
  const changedValue = formData.get("changed_value");

  // A malformed post (missing/non-string required fields) never reaches
  // FastAPI at all -- it is exactly as invalid as a body FastAPI itself
  // would reject with 400, so it collapses to the same `"invalid"` kind
  // rather than fabricating any sensitivity result (contract §11).
  if (typeof changedCriterion !== "string" || typeof changedValue !== "string") {
    return { kind: "invalid", message: null };
  }

  const response = await postSearchSensitivity(
    apiBaseUrl,
    locale,
    current,
    changedCriterion,
    changedValue,
  );

  if (response.status === 200 && response.result !== null) {
    return { kind: "ok", result: response.result };
  }
  if (response.status === 400) {
    return { kind: "invalid", message: response.invalid?.message ?? null };
  }
  return { kind: "unavailable" };
}
