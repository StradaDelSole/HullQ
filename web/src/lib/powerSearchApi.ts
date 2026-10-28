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

/**
 * Call FastAPI's `/api/search/{locale}/power` route with *queryString* (no
 * leading `?`, may be empty) and classify the real response. A network
 * failure or an unexpected upstream status collapses to `status: 502` with
 * no result/invalid payload -- callers must treat this as a recovery case,
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
    let result: PowerSearchResultBody | null = null;
    try {
      result = (await response.json()) as PowerSearchResultBody;
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
