// SLICE-0051: the only module allowed to talk to the outside world for the
// public Search surface. Astro obtains every Search decision (canonical
// redirect, invalid-request recovery, or confirmed/insufficient results)
// through FastAPI's `/api/search/{locale}` route only -- this module never
// touches PostgreSQL and never reimplements a Python domain/canonicalization
// rule (slice item J). `redirect: "manual"` is required here: FastAPI's own
// route returns a real HTTP 308 with a `Location` header for a non-canonical
// but valid request, and this page must reissue that exact redirect to the
// browser rather than transparently following it server-side.
//
// SLICE-0056: `active_requirement` is now sparse (`draft_max` and/or
// `keel_configuration`, mirroring `src/hullq/api/app.py`'s `get_search`
// route). Which of the two confirmed-match shapes a response carries is
// determined entirely by whether `keel_configuration` is active -- FastAPI
// only ever returns the legacy SLICE-0051 `DraftMaxConfirmedMatch` shape
// (`resolved_draft_m`) for a pure `draft_max` request, and the SLICE-0055
// typed-evidence shape (`criterion_evidence`) for any request involving
// `keel_configuration` (`src/hullq/application/search_read.py`, `if
// keel_configuration is None: ... evaluate_draft_max_requirement ... else:
// ... evaluate_native_inventory_requirements`). These two response shapes
// are never mixed within one result.

// The exact accepted public v0.1 `keel_configuration` query/display values
// (specs/TECHNICAL_NATIVE_SEARCH_CRITERION_2_KEEL_CONTRACT.v0.1.md §4,
// `hullq.search.keel_design_bridge.SEARCH_KEEL_CONFIGURATION_VALUES`).
// Technical values, language-neutral -- never localized, never remapped.
export const SEARCH_KEEL_CONFIGURATION_VALUES = [
  "FIN",
  "FIN_WITH_BULB",
  "WING",
  "CENTERBOARD",
  "LIFTING_KEEL",
  "TWIN_KEEL",
] as const;

export type SearchKeelConfigurationValue = (typeof SEARCH_KEEL_CONFIGURATION_VALUES)[number];

// Mirrors `src/hullq/application/search_read.py`'s sparse
// `active_requirement` construction: `draft_max` and/or
// `keel_configuration`, never neither (a `null` `active_requirement` is the
// base state, represented separately below).
export type SearchActiveRequirement =
  | { draft_max: string; keel_configuration?: undefined }
  | { keel_configuration: string; draft_max?: undefined }
  | { draft_max: string; keel_configuration: string };

/** SLICE-0051 draft-only confirmed match, unchanged (contract §8 non-regression). */
export interface DraftOnlyConfirmedMatch {
  native_listing_id: string;
  resolved_draft_m: string;
  publishing_organization_id: string;
  /** SLICE-0052: STALE/UNKNOWN matches never reach this response at all. */
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
}

// Mirrors `src/hullq/api/app.py::_serialize_leaf_criterion` -- the exact
// requested criterion value/comparison, never re-derived from explanation
// text.
export type SearchLeafCriterion =
  | {
      kind: "NUMERIC";
      field: string;
      comparison: "MINIMUM" | "MAXIMUM" | "RANGE";
      threshold_min: string | null;
      threshold_max: string | null;
    }
  | { kind: "CATEGORICAL"; field: string; equals: string };

// Mirrors `src/hullq/api/app.py::_serialize_criterion_evidence` /
// `hullq.application.native_inventory_query.SearchCriterionEvidence`.
// `observed_value` is `null` whenever the underlying evaluation is not a
// `CONFIRMED`-qualified value -- never fabricated by this module or a caller.
export interface SearchCriterionEvidence {
  criterion: SearchLeafCriterion;
  field: string;
  truth: "TRUE" | "FALSE" | "UNKNOWN";
  reason: string | null;
  explanation: string;
  observed_value: string | null;
}

/**
 * SLICE-0055 keel-only/mixed confirmed match
 * (`hullq.application.native_inventory_query.NativeInventoryCandidateEvaluation`).
 * Only the fields this bounded browser projection actually renders are
 * typed here -- `design_evaluation`/`design_configuration_evidence` are also
 * present on the real JSON body but are design-level evidence, out of scope
 * for this slice's buyer-facing concrete-match rendering (Required Behavior
 * §D uses `criterion_evidence`, the concrete PhysicalBoat-level evidence,
 * only).
 */
export interface NativeInventoryConfirmedMatch {
  native_listing_id: string;
  publishing_organization_id: string;
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
  criterion_evidence: SearchCriterionEvidence[];
}

export type SearchConfirmedMatch = DraftOnlyConfirmedMatch | NativeInventoryConfirmedMatch;

export interface SearchResultBody {
  locale: string;
  active_requirement: SearchActiveRequirement | null;
  confirmed_matches?: SearchConfirmedMatch[];
  confirmed_match_count?: number;
  insufficient_data_count?: number;
}

export interface SearchInvalidBody {
  error: string;
  message: string;
}

export interface SearchApiResponse {
  /** The real upstream FastAPI status: 200, 308, or 400. 502 on network failure. */
  status: number;
  /** Populated only when `status === 308`. */
  location: string | null;
  /** Populated only when `status === 200`. */
  result: SearchResultBody | null;
  /** Populated only when `status === 400`. */
  invalid: SearchInvalidBody | null;
}

/**
 * Call FastAPI's `/api/search/{locale}` route with *queryString* (no leading
 * `?`, may be empty) and classify the real response. A network failure or an
 * unexpected upstream status collapses to `status: 502` with no
 * result/invalid payload -- callers must treat this as a recovery case, not
 * a confirmed empty result.
 */
export async function fetchSearch(
  apiBaseUrl: string,
  locale: string,
  queryString: string,
): Promise<SearchApiResponse> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const suffix = queryString ? `?${queryString}` : "";
  const url = `${base}/api/search/${encodeURIComponent(locale)}${suffix}`;

  let response: Response;
  try {
    response = await fetch(url, { redirect: "manual" });
  } catch {
    return { status: 502, location: null, result: null, invalid: null };
  }

  if (response.status === 308) {
    return { status: 308, location: response.headers.get("location"), result: null, invalid: null };
  }
  if (response.status === 400) {
    let invalid: SearchInvalidBody | null = null;
    try {
      invalid = (await response.json()) as SearchInvalidBody;
    } catch {
      invalid = null;
    }
    return { status: 400, location: null, result: null, invalid };
  }
  if (response.status === 200) {
    let result: SearchResultBody | null = null;
    try {
      result = (await response.json()) as SearchResultBody;
    } catch {
      result = null;
    }
    if (result === null) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    return { status: 200, location: null, result, invalid: null };
  }
  return { status: 502, location: null, result: null, invalid: null };
}
