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

// Review amendment Finding J (second pass): a nonnegative *integer* --
// never a fraction, never negative, never `NaN`/`Infinity`, and never
// outside the safe-integer range. `Number.isSafeInteger` alone already
// rejects every one of those (it requires a finite integer within
// +/-2^53-1), so this is the single correct gate for every RESULT count.
function isNonNegativeSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 0;
}

function isFreshnessStatus(value: unknown): value is "CONFIRMED" | "DUE_FOR_CONFIRMATION" {
  return value === "CONFIRMED" || value === "DUE_FOR_CONFIRMATION";
}

function isValidTruthState(value: unknown): value is "TRUE" | "FALSE" | "UNKNOWN" {
  return value === "TRUE" || value === "FALSE" || value === "UNKNOWN";
}

function isValidLeafCriterion(value: unknown): value is PowerLeafCriterion {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return v.kind === "CATEGORICAL" && typeof v.field === "string" && typeof v.equals === "string";
}

// Review amendment Finding J (MEDIUM): deep-validate every nested evidence
// object, never only its enclosing array's shape (`Array.isArray(...)`
// alone proves nothing about what is actually inside it).
function isValidCriterionEvidence(value: unknown): value is PowerCriterionEvidence {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    isValidLeafCriterion(v.criterion) &&
    typeof v.field === "string" &&
    isValidTruthState(v.truth) &&
    (v.reason === null || typeof v.reason === "string") &&
    typeof v.explanation === "string" &&
    (v.observed_value === null || typeof v.observed_value === "string")
  );
}

function isValidConfigurationEvidence(value: unknown): value is PowerConfigurationEvidence {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.configuration_id === "string" &&
    typeof v.boat_design_id === "string" &&
    (v.named_variant_id === null || typeof v.named_variant_id === "string") &&
    isValidTruthState(v.truth) &&
    Array.isArray(v.criterion_evidence) &&
    v.criterion_evidence.every(isValidCriterionEvidence)
  );
}

function isValidResultClass(
  value: unknown,
): value is "CONFIRMED_MATCH" | "CONFIRMED_NON_MATCH" | "INSUFFICIENT_DATA" {
  return (
    value === "CONFIRMED_MATCH" || value === "CONFIRMED_NON_MATCH" || value === "INSUFFICIENT_DATA"
  );
}

function isValidDesignEvaluation(value: unknown): value is PowerDesignEvaluation {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.design_id === "string" &&
    isValidResultClass(v.result_class) &&
    Array.isArray(v.matching_configuration_ids) &&
    v.matching_configuration_ids.every((id) => typeof id === "string") &&
    (v.reason === null || typeof v.reason === "string")
  );
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
    v.criterion_evidence.every(isValidCriterionEvidence) &&
    Array.isArray(v.design_configuration_evidence) &&
    v.design_configuration_evidence.every(isValidConfigurationEvidence) &&
    isValidDesignEvaluation(v.design_evaluation)
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
    Array.isArray(v.criterion_evidence) &&
    v.criterion_evidence.every(isValidCriterionEvidence)
  );
}

/**
 * Strictly validate a parsed JSON value as a well-formed, internally
 * consistent `PowerSearchResultBody` that actually answers *expected*'s
 * request.
 *
 * Review amendment Finding J (MEDIUM): a syntactically well-formed body is
 * not enough -- a body that is internally consistent but answers a
 * *different* request (wrong locale, a filtered query silently served a
 * BASE/no-op response, or `active_requirement.power_drive` echoing back a
 * token other than the one actually requested) is just as misleading as a
 * malformed one, and must collapse to the same `502` service error rather
 * than being read as a genuine (if surprising) empty result. `expected`
 * carries exactly what the caller actually asked for -- the URL `locale`
 * path segment and the parsed `power_drive` query parameter (`null` when
 * absent) -- so this function can check the response actually answers
 * that request, not just that it is shaped like *some* valid response.
 *
 * Returns `null` for anything malformed -- including a syntactically valid
 * but incomplete/truncated body (e.g.
 * `{"locale":"en","active_requirement":{"power_drive":"POD"}}` with every
 * result-surface field missing), a non-array where an array is required, a
 * count that is not a nonnegative integer or does not match its own
 * array's length, a BASE payload carrying ANY key other than `locale`/
 * `active_requirement` at all (review amendment Finding J, second pass --
 * the real FastAPI BASE contract is exactly `{locale, active_requirement}`
 * and nothing else, so no malformed/negative/non-array extra field on BASE
 * is ever tolerated, regardless of its shape), an unrecognized
 * `source_basis`, or any malformed nested evidence object. Exported for
 * direct unit testing.
 */
export function validatePowerSearchResultBody(
  value: unknown,
  expected: { locale: string; powerDrive: SearchPowerDriveValue | null },
): PowerSearchResultBody | null {
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;
  if (typeof v.locale !== "string" || v.locale !== expected.locale) return null;
  if (!("active_requirement" in v) || !isValidActiveRequirement(v.active_requirement)) {
    return null;
  }
  const activeRequirement = v.active_requirement as PowerActiveRequirement | null;

  if (expected.powerDrive === null) {
    // An unfiltered request must never come back as an active RESULT --
    // there is no requested token for it to have confirmed/excluded.
    if (activeRequirement !== null) return null;
  } else {
    // A filtered request must never come back as a no-op BASE response,
    // and must never echo back a drive token other than the one actually
    // requested (wrong locale/drive dispatch, never silently accepted).
    if (activeRequirement === null) return null;
    if (activeRequirement.power_drive !== expected.powerDrive) return null;
  }

  if (activeRequirement === null) {
    // BASE state (review amendment Finding J, second pass): the real
    // FastAPI BASE contract returns *exactly* `{locale, active_requirement}`
    // and nothing else -- so instead of selectively tolerating some
    // malformed/negative/non-array extra field, reject the presence of ANY
    // other key whatsoever, regardless of its value or type. This is
    // strictly simpler than enumerating every possible malformed shape and
    // is exactly compatible with the real backend's own BASE response.
    const keys = Object.keys(v);
    if (keys.length !== 2 || !keys.includes("active_requirement")) return null;
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
    !isNonNegativeSafeInteger(v.design_linked_match_count) ||
    v.design_linked_match_count !== v.design_linked_matches.length
  ) {
    return null;
  }
  if (!isNonNegativeSafeInteger(v.design_linked_insufficient_data_count)) {
    return null;
  }
  if (
    !Array.isArray(v.publisher_claim_matches) ||
    !v.publisher_claim_matches.every(isValidClaimOnlyMatch)
  ) {
    return null;
  }
  if (
    !isNonNegativeSafeInteger(v.publisher_claim_match_count) ||
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
 * A query string that unambiguously means either "no filter" (zero
 * recognized keys at all) or "exactly one `power_drive` filter, with
 * exactly one value, that is one of the five accepted tokens" --
 * `{ ok: false }` for every other shape: an invalid token value, duplicate
 * `power_drive` keys (even with identical values), or any unrecognized/
 * extra query key alongside or instead of `power_drive`.
 *
 * Review amendment Finding J (second pass): `URLSearchParams.get(...)`
 * alone cannot distinguish "the filter is genuinely absent" from "the
 * filter is present but invalid/duplicated/accompanied by unknown keys" --
 * it silently returns `null` for an invalid value and the *first* value
 * for duplicates, either of which this module's caller must never treat
 * as "no filter was requested" or "the filter was requested and must be
 * matched against the first duplicate". Exported for direct unit testing.
 */
export function parseCanonicalPowerSearchQuery(
  queryString: string,
): { ok: true; powerDrive: SearchPowerDriveValue | null } | { ok: false } {
  const params = new URLSearchParams(queryString);
  const keys = new Set(params.keys());
  if (keys.size === 0) {
    return { ok: true, powerDrive: null };
  }
  if (keys.size !== 1 || !keys.has("power_drive")) {
    return { ok: false };
  }
  const values = params.getAll("power_drive");
  if (values.length !== 1) {
    return { ok: false };
  }
  const [value] = values;
  if (!isSearchPowerDriveValue(value)) {
    return { ok: false };
  }
  return { ok: true, powerDrive: value };
}

/**
 * Call FastAPI's `/api/search/{locale}/power` route with *queryString* (no
 * leading `?`, may be empty) and classify the real response. A network
 * failure, an unparseable body, a non-canonical request query (invalid,
 * duplicated or unrecognized `power_drive` keys -- `parseCanonicalPowerSearchQuery`),
 * or a body that fails `validatePowerSearchResultBody` all collapse to
 * `status: 502` with no result/invalid payload -- callers must treat this
 * as a recovery case, not a confirmed empty result. Real upstream 400/308
 * handling (the normal response to an invalid/unrecognized query) is
 * unaffected -- this 502 path only ever fires for an HTTP-200 response
 * that does not actually answer a canonical request.
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
    // Review amendment Finding J (second pass): a non-canonical request
    // query (invalid/duplicated/unrecognized `power_drive` keys) must
    // never be treated as "no filter" -- no HTTP-200 body can ever be a
    // valid answer to an ambiguous request, regardless of its own shape.
    const canonicalQuery = parseCanonicalPowerSearchQuery(queryString);
    if (!canonicalQuery.ok) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    let parsed: unknown;
    try {
      parsed = await response.json();
    } catch {
      parsed = null;
    }
    const expected = { locale, powerDrive: canonicalQuery.powerDrive };
    const result = parsed === null ? null : validatePowerSearchResultBody(parsed, expected);
    if (result === null) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    return { status: 200, location: null, result, invalid: null };
  }
  return { status: 502, location: null, result: null, invalid: null };
}
