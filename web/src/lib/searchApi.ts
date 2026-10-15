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

// SLICE-0085: the exact accepted public `rudder_configuration` query/display
// values (`hullq.search.rudder_design_bridge.SEARCH_RUDDER_CONFIGURATION_VALUES`).
// Technical values, language-neutral -- never localized, never remapped.
export const SEARCH_RUDDER_CONFIGURATION_VALUES = [
  "SKEG_HUNG",
  "TRANSOM_HUNG",
  "SPADE",
  "TWIN",
] as const;

export type SearchRudderConfigurationValue = (typeof SEARCH_RUDDER_CONFIGURATION_VALUES)[number];

// SLICE-0086: the exact accepted public `hull_configuration` query/display
// values (`hullq.search.hull_design_bridge.SEARCH_HULL_CONFIGURATION_VALUES`).
// Technical values, language-neutral -- never localized, never remapped.
export const SEARCH_HULL_CONFIGURATION_VALUES = ["MONOHULL", "CATAMARAN", "TRIMARAN"] as const;

export type SearchHullConfigurationValue = (typeof SEARCH_HULL_CONFIGURATION_VALUES)[number];

// SLICE-0086: the exact accepted public `cockpit_position` query/display
// values (`hullq.search.cockpit_design_bridge.SEARCH_COCKPIT_POSITION_VALUES`).
export const SEARCH_COCKPIT_POSITION_VALUES = ["AFT", "CENTER", "FORWARD", "MULTIPLE"] as const;

export type SearchCockpitPositionValue = (typeof SEARCH_COCKPIT_POSITION_VALUES)[number];

// SLICE-0086: the exact accepted public `deck_saloon` query/display values
// (`hullq.search.deck_saloon_design_bridge.SEARCH_DECK_SALOON_VALUES`). `NONE`
// is a real PhysicalBoat claim value but never a public Search filter value
// in this slice.
export const SEARCH_DECK_SALOON_VALUES = ["DECK_SALOON", "PILOTHOUSE"] as const;

export type SearchDeckSaloonValue = (typeof SEARCH_DECK_SALOON_VALUES)[number];

// SLICE-0087: the exact accepted public `hull_material` query/display values
// (`hullq.search.hull_material_design_bridge.SEARCH_HULL_MATERIAL_VALUES`).
// Technical values, language-neutral -- never localized, never remapped.
// `FERROCEMENT`/`CARBON_COMPOSITE`/`OTHER` are real PhysicalBoat claim
// values but never public Search filter values in this slice.
export const SEARCH_HULL_MATERIAL_VALUES = [
  "GRP_FIBERGLASS",
  "STEEL",
  "ALUMINUM",
  "WOOD",
] as const;

export type SearchHullMaterialValue = (typeof SEARCH_HULL_MATERIAL_VALUES)[number];

// Mirrors `src/hullq/application/search_read.py`'s sparse
// `active_requirement` construction (SLICE-0051/0056, extended SLICE-0085/
// SLICE-0086/SLICE-0087): any non-empty subset of `draft_max`/
// `keel_configuration`/`loa_min`/`loa_max`/`rudder_configuration`/
// `hull_configuration`/`cockpit_position`/`deck_saloon`/`beam_min`/
// `beam_max`/`hull_material`, never none (a `null` `active_requirement` is
// the base state, represented separately below). TypeScript cannot
// mechanically enforce "at least one of eleven" any more cheaply than at
// runtime -- FastAPI is the actual source of truth for that invariant.
export interface SearchActiveRequirement {
  draft_max?: string;
  keel_configuration?: string;
  loa_min?: string;
  loa_max?: string;
  rudder_configuration?: string;
  hull_configuration?: string;
  cockpit_position?: string;
  deck_saloon?: string;
  beam_min?: string;
  beam_max?: string;
  hull_material?: string;
}

/** SLICE-0051 draft-only confirmed match, unchanged (contract §8 non-regression). */
export interface DraftOnlyConfirmedMatch {
  native_listing_id: string;
  resolved_draft_m: string;
  publishing_organization_id: string;
  /** SLICE-0052: STALE/UNKNOWN matches never reach this response at all. */
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
  /**
   * SLICE-0071 contract §8B amendment: opaque, HMAC-signed, FastAPI-minted
   * TECHNICAL_SEARCH discovery token bound to this exact result's own
   * `native_listing_id`. Never decoded/interpreted here -- only carried
   * through into the listing link's `?ds=` query parameter.
   */
  discovery_token: string;
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

// PR #349 independent-review Finding D: mirrors
// `src/hullq/api/app.py::_serialize_configuration_evidence` /
// `hullq.application.native_inventory_query.ConfigurationEvidence` -- one
// resolved BoatDesign/NamedVariant configuration's own truth plus its
// per-criterion design-side evidence. `truth` is this configuration's own
// aggregate truth (never implied to be TRUE for every variant merely
// because the listing overall confirmed match via a different one) -- a
// design with multiple NamedVariants may legitimately carry several
// entries here, each with its own independent truth/evidence, exactly
// mirroring the already-reviewed private broker Search-fit rendering
// (`web/src/lib/brokerSearchFitApi.ts`'s `ConfigurationEvidence`).
export interface SearchConfigurationEvidence {
  configuration_id: string;
  boat_design_id: string;
  named_variant_id: string | null;
  truth: "TRUE" | "FALSE" | "UNKNOWN";
  criterion_evidence: SearchCriterionEvidence[];
}

/**
 * SLICE-0055 keel-only/mixed confirmed match
 * (`hullq.application.native_inventory_query.NativeInventoryCandidateEvaluation`).
 * `criterion_evidence` is the concrete PhysicalBoat-level evidence
 * (Required Behavior §D). `design_configuration_evidence` (PR #349 Finding
 * D) is the separate design/configuration-level evidence for the exact same
 * active criteria -- design truth kept visibly distinct from physical-offer
 * truth, per `docs/PRODUCT_UX_PRINCIPLES.md` §15 minimum 5. Both are read
 * verbatim from the real API body; neither is re-derived or re-evaluated
 * client-side.
 */
export interface NativeInventoryConfirmedMatch {
  native_listing_id: string;
  publishing_organization_id: string;
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
  criterion_evidence: SearchCriterionEvidence[];
  design_configuration_evidence: SearchConfigurationEvidence[];
  /** SLICE-0071 contract §8B amendment: see `DraftOnlyConfirmedMatch.discovery_token`. */
  discovery_token: string;
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
