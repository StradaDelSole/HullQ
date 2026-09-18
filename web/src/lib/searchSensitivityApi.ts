// SLICE-0057: the only module allowed to talk to the outside world for the
// buyer-requirement-sensitivity surface. Mirrors `./searchApi.ts`'s own
// boundary exactly -- this module never touches PostgreSQL and never
// reimplements a Python domain/canonicalization/Search-truth rule (contract
// §4/§9/§12: "Astro/TypeScript ... MUST NOT ... compute a Search result or
// delta" / "MUST NOT build a competing canonical Search URL"). It transports
// raw current/proposed values to FastAPI's
// `POST /api/search/{locale}/sensitivity` and classifies the real response;
// every typed value below (parsed Decimal, canonical path, confirmed-match
// delta) is FastAPI's own, never re-derived here.

/** Mirrors `hullq.api.app._serialize_sensitivity_requirement` -- sparse,
 * `draft_max` and/or `keel_configuration`, never neither. */
export interface SensitivityRequirement {
  draft_max?: string;
  keel_configuration?: string;
}

/** Mirrors `hullq.application.search_sensitivity.SensitivityResult` via
 * `hullq.api.app.post_search_sensitivity`'s JSON shape (contract §10). Every
 * value here is a plain fact -- no score, winner, recommendation or advice. */
export interface SensitivityResultBody {
  locale: string;
  current_requirement: SensitivityRequirement;
  alternative_requirement: SensitivityRequirement;
  changed_criterion: "draft_max" | "keel_configuration";
  current_confirmed_match_count: number;
  alternative_confirmed_match_count: number;
  newly_confirmed_match_count: number;
  no_longer_confirmed_match_count: number;
  current_insufficient_data_count: number;
  alternative_insufficient_data_count: number;
  alternative_search_path: string;
}

export interface SensitivityInvalidBody {
  error: string;
  message: string;
}

export interface SensitivityApiResponse {
  /** The real upstream FastAPI status: 200 or 400. 502 on network/unexpected failure. */
  status: number;
  /** Populated only when `status === 200`. */
  result: SensitivityResultBody | null;
  /** Populated only when `status === 400`. */
  invalid: SensitivityInvalidBody | null;
}

/**
 * Call FastAPI's `POST /api/search/{locale}/sensitivity` with the buyer's
 * current active requirement plus exactly one changed criterion/value, and
 * classify the real response. A network failure or an unexpected upstream
 * status (including 404 -- an unsupported locale, which the calling page
 * never reaches since it validates locale support itself first) collapses to
 * `status: 502` with no result/invalid payload -- callers must treat this as
 * a recovery case, never a confirmed empty/zero delta.
 */
export async function postSearchSensitivity(
  apiBaseUrl: string,
  locale: string,
  current: Record<string, string>,
  changedCriterion: string,
  changedValue: string,
): Promise<SensitivityApiResponse> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url = `${base}/api/search/${encodeURIComponent(locale)}/sensitivity`;

  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({
        current,
        change: { criterion: changedCriterion, value: changedValue },
      }),
    });
  } catch {
    return { status: 502, result: null, invalid: null };
  }

  if (response.status === 400) {
    let invalid: SensitivityInvalidBody | null = null;
    try {
      invalid = (await response.json()) as SensitivityInvalidBody;
    } catch {
      invalid = null;
    }
    return { status: 400, result: null, invalid };
  }
  if (response.status === 200) {
    let result: SensitivityResultBody | null = null;
    try {
      result = (await response.json()) as SensitivityResultBody;
    } catch {
      result = null;
    }
    if (result === null) {
      return { status: 502, result: null, invalid: null };
    }
    return { status: 200, result, invalid: null };
  }
  return { status: 502, result: null, invalid: null };
}
