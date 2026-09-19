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

// The exact accepted browser POST field names (contract §12) -- any other
// submitted field name is itself a malformed/tampered request.
const _ACCEPTED_FIELD_NAMES = new Set([
  "current_draft_max",
  "current_keel_configuration",
  "changed_criterion",
  "changed_value",
]);

type ParsedSensitivityForm =
  | { kind: "invalid" }
  | {
      kind: "ok";
      current: Record<string, string>;
      changedCriterion: string;
      changedValue: string;
    };

/**
 * Validate and parse the posted sensitivity form's raw *structural* shape
 * -- field names, occurrence counts and value types only. Never validates
 * Search semantics (Decimal syntax, keel vocabulary, whether a criterion is
 * genuinely active): that stays exclusively FastAPI/application's job
 * (contract §4/§9).
 *
 * Independent review Finding 2 (2026-09-19): unlike the *ordinary* Search
 * form's untouched-`<select>`/`<input>` omission (`SearchPageBody.astro`'s
 * own `isUntouchedFormFieldValue` disabling, which applies only to that
 * GET-query-building form), the sensitivity form's `current_*` hidden
 * fields are never buyer-editable -- `SearchPageBody.astro` only ever
 * renders one for a criterion that is genuinely active, always with its
 * exact canonical value. So there is no legitimate "buyer left it blank"
 * state to interpret here: a *present* `current_draft_max`/
 * `current_keel_configuration` field, even `""`, can only mean tampered or
 * malformed current state, and must reach FastAPI exactly as posted so the
 * accepted application/domain validation
 * (`hullq.application.search_sensitivity.evaluate_requirement_sensitivity`)
 * can fail closed with 400 -- never silently reinterpreted as "criterion
 * inactive," which would narrow the current requirement into a different,
 * unintended sensitivity comparison. Only a field's true *absence* means
 * "this criterion was not active."
 *
 * Independent review Finding 5 (2026-09-19): `FormData.get(...)` alone
 * silently resolves ambiguity that must instead fail closed --
 * `FormData.get` returns only the *first* value for a repeated key
 * (dropping a duplicate/conflicting submission rather than rejecting it),
 * and iterating only the known field names would silently drop an unknown
 * field (e.g. a tampered `current_foo`) instead of treating its presence as
 * malformed. This function instead walks every posted `[name, value]` pair
 * via `FormData.entries()` once, so an unknown field name, a non-string
 * value (a `File`), or a field occurring an unexpected number of times all
 * fail closed as `{ kind: "invalid" }` -- before any network access, and
 * before `current`'s sparse shape is even built.
 */
function parseSensitivityFormData(formData: FormData): ParsedSensitivityForm {
  const counts = new Map<string, number>();
  const values = new Map<string, string>();

  for (const [name, value] of formData.entries()) {
    if (!_ACCEPTED_FIELD_NAMES.has(name)) {
      return { kind: "invalid" };
    }
    if (typeof value !== "string") {
      return { kind: "invalid" };
    }
    counts.set(name, (counts.get(name) ?? 0) + 1);
    values.set(name, value);
  }

  if ((counts.get("current_draft_max") ?? 0) > 1) {
    return { kind: "invalid" };
  }
  if ((counts.get("current_keel_configuration") ?? 0) > 1) {
    return { kind: "invalid" };
  }
  if ((counts.get("changed_criterion") ?? 0) !== 1) {
    return { kind: "invalid" };
  }
  if ((counts.get("changed_value") ?? 0) !== 1) {
    return { kind: "invalid" };
  }

  const current: Record<string, string> = {};
  const currentDraftMax = values.get("current_draft_max");
  if (currentDraftMax !== undefined) {
    current.draft_max = currentDraftMax;
  }
  const currentKeelConfiguration = values.get("current_keel_configuration");
  if (currentKeelConfiguration !== undefined) {
    current.keel_configuration = currentKeelConfiguration;
  }

  // Both guaranteed present-exactly-once by the count checks above.
  const changedCriterion = values.get("changed_criterion");
  const changedValue = values.get("changed_value");
  if (changedCriterion === undefined || changedValue === undefined) {
    return { kind: "invalid" };
  }

  return { kind: "ok", current, changedCriterion, changedValue };
}

export async function loadSearchSensitivityPageData(
  apiBaseUrl: string,
  locale: SupportedLocale,
  formData: FormData,
): Promise<SearchSensitivityPageData> {
  const parsed = parseSensitivityFormData(formData);

  // A structurally malformed post (unknown field, duplicated field, a
  // non-string value) never reaches FastAPI at all -- it is exactly as
  // invalid as a body FastAPI itself would reject with 400, so it
  // collapses to the same `"invalid"` kind rather than fabricating any
  // sensitivity result (contract §11).
  if (parsed.kind === "invalid") {
    return { kind: "invalid", message: null };
  }

  const response = await postSearchSensitivity(
    apiBaseUrl,
    locale,
    parsed.current,
    parsed.changedCriterion,
    parsed.changedValue,
  );

  if (response.status === 200 && response.result !== null) {
    return { kind: "ok", result: response.result };
  }
  if (response.status === 400) {
    return { kind: "invalid", message: response.invalid?.message ?? null };
  }
  return { kind: "unavailable" };
}
