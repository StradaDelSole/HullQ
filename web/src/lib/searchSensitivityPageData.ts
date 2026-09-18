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
 * criterion/value") -- an absent or empty field is omitted entirely, never
 * sent as an empty-string criterion value (mirrors
 * `SearchPageBody.astro`'s own untouched-field omission for the ordinary
 * Search form).
 */
function currentRequirementFromFormData(formData: FormData): Record<string, string> {
  const current: Record<string, string> = {};
  for (const key of _CURRENT_KEYS) {
    const raw = formData.get(`current_${key}`);
    if (typeof raw === "string" && raw !== "") {
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
