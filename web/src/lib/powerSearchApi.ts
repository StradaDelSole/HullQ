// SLICE-0093: the only module allowed to talk to the outside world for the
// public Power-only Search surface. Mirrors `searchApi.ts`'s identical
// discipline (`redirect: "manual"`, no PostgreSQL/Python-rule
// reimplementation), but talks to the entirely separate
// `/api/search/{locale}/power` route -- never the Sail `/api/search/{locale}`
// route, and never shares a response shape with it.

// The exact accepted public five-token exact whitelist
// (`specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md` "One field, one
// meaning", `hullq.search.power_criteria_registry.SEARCH_POWER_DRIVE_VALUES`).
// Technical values, language-neutral -- never localized, never remapped. A
// current publisher's durable claim may also represent `MIXED`/`OTHER`/
// `UNKNOWN`, but neither of those is ever a public Search filter value.
export const SEARCH_POWER_DRIVE_VALUES = [
  "SHAFT",
  "STERNDRIVE",
  "POD",
  "WATERJET",
  "OUTBOARD",
] as const;

export type SearchPowerDriveValue = (typeof SEARCH_POWER_DRIVE_VALUES)[number];

export interface PowerActiveRequirement {
  power_drive: SearchPowerDriveValue;
}

// Mirrors `src/hullq/api/app.py::_serialize_leaf_criterion` -- shared shape
// with the Sail surface's own `SearchLeafCriterion`.
export type PowerLeafCriterion = { kind: "CATEGORICAL"; field: string; equals: string };

export interface PowerCriterionEvidence {
  criterion: PowerLeafCriterion;
  field: string;
  truth: "TRUE" | "FALSE" | "UNKNOWN";
  reason: string | null;
  explanation: string;
  observed_value: string | null;
}

export interface PowerConfigurationEvidence {
  configuration_id: string;
  boat_design_id: string;
  named_variant_id: string | null;
  truth: "TRUE" | "FALSE" | "UNKNOWN";
  criterion_evidence: PowerCriterionEvidence[];
}

export interface PowerDesignEvaluation {
  design_id: string;
  result_class: "CONFIRMED_MATCH" | "CONFIRMED_NON_MATCH" | "INSUFFICIENT_DATA";
  matching_configuration_ids: string[];
  reason: string | null;
}

/**
 * One design-linked Power match
 * (`hullq.application.power_inventory_query.PowerDesignLinkedMatch`,
 * serialized by `src/hullq/api/app.py::_serialize_power_design_linked_match`).
 */
export interface PowerDesignLinkedMatch {
  native_listing_id: string;
  publishing_organization_id: string;
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
  design_evaluation: PowerDesignEvaluation;
  design_configuration_evidence: PowerConfigurationEvidence[];
  criterion_evidence: PowerCriterionEvidence[];
  discovery_token: string;
}

/**
 * One design-UNRESOLVED candidate's claim-only Power match
 * (`hullq.application.power_inventory_query.PowerClaimOnlyMatch`, serialized
 * by `src/hullq/api/app.py::_serialize_power_claim_only_match`).
 * `source_basis` is always the literal `"PUBLISHER_CLAIM"` -- this is the
 * publishing Organization's own current claim-revision statement, never
 * independently design-verified.
 */
export interface PowerClaimOnlyMatch {
  native_listing_id: string;
  publishing_organization_id: string;
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
  source_basis: "PUBLISHER_CLAIM";
  criterion_evidence: PowerCriterionEvidence[];
  discovery_token: string;
}

export interface PowerSearchResultBody {
  locale: string;
  active_requirement: PowerActiveRequirement | null;
  design_linked_matches?: PowerDesignLinkedMatch[];
  design_linked_match_count?: number;
  design_linked_insufficient_data_count?: number;
  publisher_claim_matches?: PowerClaimOnlyMatch[];
  publisher_claim_match_count?: number;
}

export interface PowerSearchInvalidBody {
  error: string;
  message: string;
}

export interface PowerSearchApiResponse {
  /** The real upstream FastAPI status: 200, 308, or 400. 502 on network failure. */
  status: number;
  /** Populated only when `status === 308`. */
  location: string | null;
  /** Populated only when `status === 200`. */
  result: PowerSearchResultBody | null;
  /** Populated only when `status === 400`. */
  invalid: PowerSearchInvalidBody | null;
}

// ---------------------------------------------------------------------------
// Review amendment Finding E: a truncated, structurally invalid or
// contradictory HTTP-200 body must never be silently treated as a genuine
// empty/zero result -- it is a service/contract failure. These guards
// validate the *entire* shape before any caller ever sees it; an upstream
// that cannot produce a well-formed, internally-consistent body is
// indistinguishable here from an unreachable backend (both become `502`).
// A genuinely valid BASE (`active_requirement: null`) or empty RESULT
// (every array `[]`, every count `0`) response is unaffected -- this is a
// *shape*/*consistency* check, never a "results must be non-empty" check.
// ---------------------------------------------------------------------------

function isSearchPowerDriveValue(value: unknown): value is SearchPowerDriveValue {
  return (
    typeof value === "string" &&
    (SEARCH_POWER_DRIVE_VALUES as readonly string[]).includes(value)
  );
}

function isValidActiveRequirement(value: unknown): value is PowerActiveRequirement | null {
  if (value === null) return true;
  if (typeof value !== "object") return false;
  const keys = Object.keys(value as Record<string, unknown>);
  if (keys.length !== 1 || keys[0] !== "power_drive") return false;
  return isSearchPowerDriveValue((value as { power_drive: unknown }).power_drive);
}

function isFreshnessStatus(value: unknown): value is "CONFIRMED" | "DUE_FOR_CONFIRMATION" {
  return value === "CONFIRMED" || value === "DUE_FOR_CONFIRMATION";
}

function isValidDesignLinkedMatch(value: unknown): value is PowerDesignLinkedMatch {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.native_listing_id === "string" &&
    typeof v.publishing_organization_id === "string" &&
    isFreshnessStatus(v.freshness_status) &&
    (v.last_confirmed_at === null || typeof v.last_confirmed_at === "string") &&
    typeof v.discovery_token === "string" &&
    Array.isArray(v.criterion_evidence) &&
    Array.isArray(v.design_configuration_evidence) &&
    typeof v.design_evaluation === "object" &&
    v.design_evaluation !== null
  );
}

function isValidClaimOnlyMatch(value: unknown): value is PowerClaimOnlyMatch {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.native_listing_id === "string" &&
    typeof v.publishing_organization_id === "string" &&
    isFreshnessStatus(v.freshness_status) &&
    (v.last_confirmed_at === null || typeof v.last_confirmed_at === "string") &&
    // Never leniently accept any other source-basis literal -- a buyer
    // must never be told something is independently verified when the
    // backend's own typed discriminator says otherwise.
    v.source_basis === "PUBLISHER_CLAIM" &&
    typeof v.discovery_token === "string" &&
    Array.isArray(v.criterion_evidence)
  );
}

/**
 * Strictly validate a parsed JSON value as a well-formed, internally
 * consistent `PowerSearchResultBody`. Returns `null` for anything
 * malformed -- including a syntactically valid but incomplete/truncated
 * body (e.g. `{"locale":"en","active_requirement":{"power_drive":"POD"}}`
 * with every result-surface field missing), a non-array where an array is
 * required, a count that does not match its own array's length, or an
 * unrecognized `source_basis`. Exported for direct unit testing.
 */
export function validatePowerSearchResultBody(value: unknown): PowerSearchResultBody | null {
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;
  if (typeof v.locale !== "string") return null;
  if (!("active_requirement" in v) || !isValidActiveRequirement(v.active_requirement)) {
    return null;
  }
  const activeRequirement = v.active_requirement as PowerActiveRequirement | null;

  if (activeRequirement === null) {
    // BASE state: no result surface is required (and none is read by any
    // caller for this state) -- a backend that nonetheless includes stray
    // extra fields here is not itself treated as a contract violation.
    return { locale: v.locale, active_requirement: null };
  }

  // RESULT state: every result-surface field is mandatory and must be
  // internally consistent -- never defaulted to empty/zero by this
  // module when genuinely absent from the wire body.
  if (
    !Array.isArray(v.design_linked_matches) ||
    !v.design_linked_matches.every(isValidDesignLinkedMatch)
  ) {
    return null;
  }
  if (
    typeof v.design_linked_match_count !== "number" ||
    v.design_linked_match_count !== v.design_linked_matches.length
  ) {
    return null;
  }
  if (
    typeof v.design_linked_insufficient_data_count !== "number" ||
    v.design_linked_insufficient_data_count < 0
  ) {
    return null;
  }
  if (
    !Array.isArray(v.publisher_claim_matches) ||
    !v.publisher_claim_matches.every(isValidClaimOnlyMatch)
  ) {
    return null;
  }
  if (
    typeof v.publisher_claim_match_count !== "number" ||
    v.publisher_claim_match_count !== v.publisher_claim_matches.length
  ) {
    return null;
  }

  return {
    locale: v.locale,
    active_requirement: activeRequirement,
    design_linked_matches: v.design_linked_matches as PowerDesignLinkedMatch[],
    design_linked_match_count: v.design_linked_match_count,
    design_linked_insufficient_data_count: v.design_linked_insufficient_data_count,
    publisher_claim_matches: v.publisher_claim_matches as PowerClaimOnlyMatch[],
    publisher_claim_match_count: v.publisher_claim_match_count,
  };
}

/**
 * Call FastAPI's `/api/search/{locale}/power` route with *queryString* (no
 * leading `?`, may be empty) and classify the real response. A network
 * failure, an unparseable body, or a body that fails
 * `validatePowerSearchResultBody` all collapse to `status: 502` with no
 * result/invalid payload -- callers must treat this as a recovery case,
 * not a confirmed empty result.
 */
export async function fetchPowerSearch(
  apiBaseUrl: string,
  locale: string,
  queryString: string,
): Promise<PowerSearchApiResponse> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const suffix = queryString ? `?${queryString}` : "";
  const url = `${base}/api/search/${encodeURIComponent(locale)}/power${suffix}`;

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
    let invalid: PowerSearchInvalidBody | null = null;
    try {
      invalid = (await response.json()) as PowerSearchInvalidBody;
    } catch {
      invalid = null;
    }
    return { status: 400, location: null, result: null, invalid };
  }
  if (response.status === 200) {
    let parsed: unknown;
    try {
      parsed = await response.json();
    } catch {
      parsed = null;
    }
    const result = parsed === null ? null : validatePowerSearchResultBody(parsed);
    if (result === null) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    return { status: 200, location: null, result, invalid: null };
  }
  return { status: 502, location: null, result: null, invalid: null };
}
