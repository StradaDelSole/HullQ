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

// SLICE-0096 independent review round 2 Finding C1: mirrors
// `web/src/lib/powerSearchApi.ts`'s `PowerDesignEvaluation` -- the complete
// design/configuration-level evaluation that admitted or failed to admit a
// listing's BoatDesign (`src/hullq/api/app.py::_serialize_design_evaluation`).
// Present on every typed-evidence confirmed match's wire body; previously
// missing from this module's own type (though already present on the real
// wire body and in existing test fixtures).
export interface SearchDesignEvaluation {
  design_id: string;
  result_class: "CONFIRMED_MATCH" | "CONFIRMED_NON_MATCH" | "INSUFFICIENT_DATA";
  matching_configuration_ids: string[];
  reason: string | null;
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
  design_evaluation: SearchDesignEvaluation;
  criterion_evidence: SearchCriterionEvidence[];
  design_configuration_evidence: SearchConfigurationEvidence[];
  /** SLICE-0071 contract §8B amendment: see `DraftOnlyConfirmedMatch.discovery_token`. */
  discovery_token: string;
}

export type SearchConfirmedMatch = DraftOnlyConfirmedMatch | NativeInventoryConfirmedMatch;

/**
 * SLICE-0092: one design-UNRESOLVED candidate's claim-only match
 * (`hullq.application.native_inventory_query.PublisherClaimCandidateEvaluation`,
 * serialized by `src/hullq/api/app.py::_serialize_claim_only_match`).
 * `source_basis` is always the literal `"PUBLISHER_CLAIM"` -- this is the
 * publishing Organization's own current claim-revision statement, never
 * independently design-verified. There is deliberately no
 * `design_evaluation`/`design_configuration_evidence` field here (unlike
 * `NativeInventoryConfirmedMatch`): there is no BoatDesign to report, never
 * a fabricated one.
 */
export interface PublisherClaimMatch {
  native_listing_id: string;
  publishing_organization_id: string;
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  last_confirmed_at: string | null;
  source_basis: "PUBLISHER_CLAIM";
  criterion_evidence: SearchCriterionEvidence[];
  discovery_token: string;
}

export interface SearchResultBody {
  locale: string;
  active_requirement: SearchActiveRequirement | null;
  confirmed_matches?: SearchConfirmedMatch[];
  confirmed_match_count?: number;
  insufficient_data_count?: number;
  /** SLICE-0092: entirely separate, additive result surface -- see `PublisherClaimMatch`. */
  publisher_claim_matches?: PublisherClaimMatch[];
  publisher_claim_match_count?: number;
  /**
   * SLICE-0096 bounded-page envelope. `confirmed_match_count`/
   * `insufficient_data_count`/`publisher_claim_match_count` above are now
   * page-local, never a global total. `evaluation_state` is `"PARTIAL"`
   * (unchecked candidates may remain, even with zero matches on this exact
   * page) or `"COMPLETE"` (boundedly proven exhausted). `next_cursor` is
   * the opaque continuation token for the next page -- present if and only
   * if `evaluation_state === "PARTIAL"`, never decoded/interpreted here.
   */
  page_size?: number;
  evaluation_state?: "PARTIAL" | "COMPLETE";
  next_cursor?: string | null;
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

// ---------------------------------------------------------------------------
// SLICE-0096 independent review round 2 Finding C1: `fetchSearch` previously
// accepted almost any non-null HTTP-200 JSON body through a bare TypeScript
// cast, with no runtime validation at all -- mirrors the exact discipline
// `web/src/lib/powerSearchApi.ts`'s `validatePowerSearchResultBody` already
// applies to the entirely separate Power surface, adapted to the Sail
// surface's own wider shape: up to eleven sparse active criteria (vs.
// Power's two), two mutually exclusive confirmed-match wire shapes (the
// legacy `resolved_draft_m` shape for a pure `draft_max` request vs. the
// typed-evidence shape for any other combination -- `src/hullq/application/
// search_read.py`'s identical `is_pure_draft_only` branch), and `loa_m`/
// `beam_m`'s own two-independent-leaves-on-one-field rule (`loa_min`/
// `loa_max` -- and `beam_min`/`beam_max` -- each contribute their OWN
// `criterion_evidence` entry against the shared field, never merged into
// one RANGE leaf; `hullq.application.native_inventory_query
// ._build_mixed_query`'s identical construction). These guards validate the
// *entire* shape before any caller ever sees it; a genuinely valid BASE or
// empty RESULT response is unaffected -- this is a *shape*/*consistency*
// check, never a "results must be non-empty" check.
// ---------------------------------------------------------------------------

export function isSearchKeelConfigurationValue(value: unknown): value is SearchKeelConfigurationValue {
  return (
    typeof value === "string" && (SEARCH_KEEL_CONFIGURATION_VALUES as readonly string[]).includes(value)
  );
}

export function isSearchRudderConfigurationValue(
  value: unknown,
): value is SearchRudderConfigurationValue {
  return (
    typeof value === "string" &&
    (SEARCH_RUDDER_CONFIGURATION_VALUES as readonly string[]).includes(value)
  );
}

export function isSearchHullConfigurationValue(value: unknown): value is SearchHullConfigurationValue {
  return (
    typeof value === "string" && (SEARCH_HULL_CONFIGURATION_VALUES as readonly string[]).includes(value)
  );
}

export function isSearchCockpitPositionValue(value: unknown): value is SearchCockpitPositionValue {
  return (
    typeof value === "string" && (SEARCH_COCKPIT_POSITION_VALUES as readonly string[]).includes(value)
  );
}

export function isSearchDeckSaloonValue(value: unknown): value is SearchDeckSaloonValue {
  return typeof value === "string" && (SEARCH_DECK_SALOON_VALUES as readonly string[]).includes(value);
}

export function isSearchHullMaterialValue(value: unknown): value is SearchHullMaterialValue {
  return typeof value === "string" && (SEARCH_HULL_MATERIAL_VALUES as readonly string[]).includes(value);
}

// The exact canonical ASCII decimal form `hullq.search.draft_max_request
// .canonical_draft_max_str` (and its loa_m/beam_m siblings) ever produces:
// a positive value, no leading zero in the integer part (except a bare
// "0" when the value is < 1), and -- when a fractional part is present --
// no trailing zero (canonical examples: "1.600" -> "1.6", "10.0" -> "10",
// "01.60" -> "1.6"). Never accepts a sign, exponent or grouping separator.
const _CANONICAL_POSITIVE_DECIMAL_RE = /^(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$/;

export function isCanonicalPositiveDecimalString(value: unknown): value is string {
  return (
    typeof value === "string" && value !== "0" && _CANONICAL_POSITIVE_DECIMAL_RE.test(value)
  );
}

// Exact digit-string comparison of two already-canonical positive decimal
// strings -- never `Number(...)`/binary-float parsing (this codebase's
// own exact-Decimal discipline, mirrored client-side only for this
// consistency check, never a reimplementation of Search truth itself).
// Both inputs must already be `isCanonicalPositiveDecimalString`-valid.
export function compareCanonicalDecimalStrings(a: string, b: string): number {
  const [aInt, aFrac = ""] = a.split(".");
  const [bInt, bFrac = ""] = b.split(".");
  if (aInt.length !== bInt.length) return aInt.length - bInt.length;
  if (aInt !== bInt) return aInt < bInt ? -1 : 1;
  const fracLen = Math.max(aFrac.length, bFrac.length);
  const aFracPadded = aFrac.padEnd(fracLen, "0");
  const bFracPadded = bFrac.padEnd(fracLen, "0");
  if (aFracPadded === bFracPadded) return 0;
  return aFracPadded < bFracPadded ? -1 : 1;
}

function isNonNegativeSafeInteger(value: unknown): value is number {
  return Number.isSafeInteger(value) && (value as number) >= 0;
}

function isFreshnessStatus(value: unknown): value is "CONFIRMED" | "DUE_FOR_CONFIRMATION" {
  return value === "CONFIRMED" || value === "DUE_FOR_CONFIRMATION";
}

function isValidTruthState(value: unknown): value is "TRUE" | "FALSE" | "UNKNOWN" {
  return value === "TRUE" || value === "FALSE" || value === "UNKNOWN";
}

// Sparse 1-11-key `active_requirement` -- any other key, an empty object,
// a malformed value for a present key, or `loa_min > loa_max`/
// `beam_min > beam_max` (the real backend only ever returns a RESULT after
// rejecting that combination as INVALID -- `src/hullq/application
// .search_read.py`'s identical ordering checks) is never genuine.
const _ACTIVE_REQUIREMENT_KEYS = new Set([
  "draft_max",
  "keel_configuration",
  "loa_min",
  "loa_max",
  "rudder_configuration",
  "hull_configuration",
  "cockpit_position",
  "deck_saloon",
  "beam_min",
  "beam_max",
  "hull_material",
]);

function isValidActiveRequirement(value: unknown): value is SearchActiveRequirement | null {
  if (value === null) return true;
  if (typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  const keys = Object.keys(v);
  if (keys.length === 0 || keys.some((key) => !_ACTIVE_REQUIREMENT_KEYS.has(key))) return false;
  if ("draft_max" in v && !isCanonicalPositiveDecimalString(v.draft_max)) return false;
  if ("keel_configuration" in v && !isSearchKeelConfigurationValue(v.keel_configuration)) return false;
  if ("loa_min" in v && !isCanonicalPositiveDecimalString(v.loa_min)) return false;
  if ("loa_max" in v && !isCanonicalPositiveDecimalString(v.loa_max)) return false;
  if ("rudder_configuration" in v && !isSearchRudderConfigurationValue(v.rudder_configuration)) {
    return false;
  }
  if ("hull_configuration" in v && !isSearchHullConfigurationValue(v.hull_configuration)) return false;
  if ("cockpit_position" in v && !isSearchCockpitPositionValue(v.cockpit_position)) return false;
  if ("deck_saloon" in v && !isSearchDeckSaloonValue(v.deck_saloon)) return false;
  if ("beam_min" in v && !isCanonicalPositiveDecimalString(v.beam_min)) return false;
  if ("beam_max" in v && !isCanonicalPositiveDecimalString(v.beam_max)) return false;
  if ("hull_material" in v && !isSearchHullMaterialValue(v.hull_material)) return false;
  if (
    "loa_min" in v &&
    "loa_max" in v &&
    compareCanonicalDecimalStrings(v.loa_min as string, v.loa_max as string) > 0
  ) {
    return false;
  }
  if (
    "beam_min" in v &&
    "beam_max" in v &&
    compareCanonicalDecimalStrings(v.beam_min as string, v.beam_max as string) > 0
  ) {
    return false;
  }
  return true;
}

// Whether *active* has, on its own, at least one of the three LOA/beam/
// draft_max-style bounds active, used only to size the expected
// `criterion_evidence` length -- never to decide a shape/kind.
function activeLeafCount(active: SearchActiveRequirement): number {
  let count = 0;
  if (active.draft_max !== undefined) count += 1;
  if (active.keel_configuration !== undefined) count += 1;
  if (active.loa_min !== undefined) count += 1;
  if (active.loa_max !== undefined) count += 1;
  if (active.rudder_configuration !== undefined) count += 1;
  if (active.hull_configuration !== undefined) count += 1;
  if (active.cockpit_position !== undefined) count += 1;
  if (active.deck_saloon !== undefined) count += 1;
  if (active.beam_min !== undefined) count += 1;
  if (active.beam_max !== undefined) count += 1;
  if (active.hull_material !== undefined) count += 1;
  return count;
}

function leafKey(criterion: SearchLeafCriterion): string {
  if (criterion.kind === "CATEGORICAL") return `CATEGORICAL:${criterion.field}`;
  return `NUMERIC:${criterion.field}:${criterion.comparison}`;
}

// A leaf criterion is genuine only if it names an ACTUALLY active field
// (never a field the current request never requested) with the EXACT
// requested comparison/threshold -- `loa_m`/`beam_m` may legitimately
// carry a MINIMUM leaf, a MAXIMUM leaf, or both (one each, never a RANGE
// leaf), depending on which of `loa_min`/`loa_max` (`beam_min`/`beam_max`)
// are active.
function isValidLeafCriterion(
  value: unknown,
  active: SearchActiveRequirement,
): value is SearchLeafCriterion {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (v.kind === "CATEGORICAL") {
    if (typeof v.equals !== "string") return false;
    if (v.field === "keel_configuration") {
      return active.keel_configuration !== undefined && v.equals === active.keel_configuration;
    }
    if (v.field === "rudder_configuration") {
      return active.rudder_configuration !== undefined && v.equals === active.rudder_configuration;
    }
    if (v.field === "hull_configuration") {
      return active.hull_configuration !== undefined && v.equals === active.hull_configuration;
    }
    if (v.field === "cockpit_position") {
      return active.cockpit_position !== undefined && v.equals === active.cockpit_position;
    }
    if (v.field === "deck_saloon") {
      return active.deck_saloon !== undefined && v.equals === active.deck_saloon;
    }
    if (v.field === "hull_material") {
      return active.hull_material !== undefined && v.equals === active.hull_material;
    }
    return false;
  }
  if (v.kind === "NUMERIC") {
    if (v.field === "draft_max_m") {
      return (
        active.draft_max !== undefined &&
        v.comparison === "MAXIMUM" &&
        v.threshold_min === null &&
        v.threshold_max === active.draft_max
      );
    }
    if (v.field === "loa_m") {
      if (v.comparison === "MINIMUM") {
        return active.loa_min !== undefined && v.threshold_max === null && v.threshold_min === active.loa_min;
      }
      if (v.comparison === "MAXIMUM") {
        return active.loa_max !== undefined && v.threshold_min === null && v.threshold_max === active.loa_max;
      }
      return false;
    }
    if (v.field === "beam_m") {
      if (v.comparison === "MINIMUM") {
        return (
          active.beam_min !== undefined && v.threshold_max === null && v.threshold_min === active.beam_min
        );
      }
      if (v.comparison === "MAXIMUM") {
        return (
          active.beam_max !== undefined && v.threshold_min === null && v.threshold_max === active.beam_max
        );
      }
      return false;
    }
    return false;
  }
  return false;
}

function hasExactActiveCriterionCoverage(
  evidence: readonly SearchCriterionEvidence[],
  active: SearchActiveRequirement,
): boolean {
  if (evidence.length !== activeLeafCount(active)) return false;
  const seen = new Set<string>();
  for (const item of evidence) {
    const key = leafKey(item.criterion);
    if (seen.has(key)) return false;
    seen.add(key);
  }
  return true;
}

// A `MAXIMUM` leaf is TRUE whenever the observed value is <= its
// threshold (a "no more than" requirement, never exact equality --
// `draft_max`/`loa_max`/`beam_max`'s real semantics); a `MINIMUM` leaf is
// TRUE whenever observed >= threshold; a `CATEGORICAL` leaf is TRUE only
// on exact equality. This deliberately differs from `powerSearchApi.ts`'s
// `observedValueMatchesRequestedValue` (Power's NUMERIC leaf is an exact-
// match RANGE, never an inequality).
function observedValueSatisfiesCriterion(criterion: SearchLeafCriterion, observedValue: string): boolean {
  if (criterion.kind === "CATEGORICAL") return observedValue === criterion.equals;
  if (!isCanonicalPositiveDecimalString(observedValue)) return false;
  if (criterion.comparison === "MAXIMUM") {
    return criterion.threshold_max !== null && compareCanonicalDecimalStrings(observedValue, criterion.threshold_max) <= 0;
  }
  if (criterion.comparison === "MINIMUM") {
    return criterion.threshold_min !== null && compareCanonicalDecimalStrings(observedValue, criterion.threshold_min) >= 0;
  }
  return false;
}

function isValidCriterionEvidence(
  value: unknown,
  active: SearchActiveRequirement,
): value is SearchCriterionEvidence {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (!isValidLeafCriterion(v.criterion, active)) return false;
  const criterion = v.criterion as SearchLeafCriterion;
  if (v.field !== criterion.field) return false;
  if (!isValidTruthState(v.truth)) return false;
  if (!(v.reason === null || typeof v.reason === "string")) return false;
  if (typeof v.explanation !== "string") return false;
  if (!(v.observed_value === null || typeof v.observed_value === "string")) return false;
  const observedValue = v.observed_value;
  if (v.truth === "UNKNOWN" && observedValue !== null) return false;
  if (v.truth === "TRUE") {
    if (observedValue === null || !observedValueSatisfiesCriterion(criterion, observedValue)) {
      return false;
    }
  }
  if (
    v.truth === "FALSE" &&
    observedValue !== null &&
    observedValueSatisfiesCriterion(criterion, observedValue)
  ) {
    return false;
  }
  return true;
}

// A positive match surface (a `confirmed_matches[]`/`publisher_claim_matches[]`
// entry's own concrete `criterion_evidence`) must have every active-
// criterion leaf confirmed TRUE -- mirrors `powerSearchApi.ts`'s identical
// `isValidPositiveCriterionEvidence` rationale. Never applies to
// `design_configuration_evidence` (a legitimate non-matching configuration's
// evidence still needs only the generic truth/value consistency above).
function isValidPositiveCriterionEvidence(
  value: unknown,
  active: SearchActiveRequirement,
): value is SearchCriterionEvidence {
  return isValidCriterionEvidence(value, active) && (value as SearchCriterionEvidence).truth === "TRUE";
}

function aggregateTruthFromLeaves(
  leaves: readonly SearchCriterionEvidence[],
): "TRUE" | "FALSE" | "UNKNOWN" {
  if (leaves.some((leaf) => leaf.truth === "FALSE")) return "FALSE";
  if (leaves.every((leaf) => leaf.truth === "TRUE")) return "TRUE";
  return "UNKNOWN";
}

function isValidConfigurationEvidence(
  value: unknown,
  active: SearchActiveRequirement,
): value is SearchConfigurationEvidence {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (
    !(
      typeof v.configuration_id === "string" &&
      typeof v.boat_design_id === "string" &&
      (v.named_variant_id === null || typeof v.named_variant_id === "string") &&
      isValidTruthState(v.truth) &&
      Array.isArray(v.criterion_evidence) &&
      v.criterion_evidence.every((evidence: unknown) => isValidCriterionEvidence(evidence, active)) &&
      hasExactActiveCriterionCoverage(v.criterion_evidence as SearchCriterionEvidence[], active)
    )
  ) {
    return false;
  }
  return v.truth === aggregateTruthFromLeaves(v.criterion_evidence as SearchCriterionEvidence[]);
}

function isValidResultClass(
  value: unknown,
): value is "CONFIRMED_MATCH" | "CONFIRMED_NON_MATCH" | "INSUFFICIENT_DATA" {
  return (
    value === "CONFIRMED_MATCH" || value === "CONFIRMED_NON_MATCH" || value === "INSUFFICIENT_DATA"
  );
}

function isValidDesignEvaluation(value: unknown): value is SearchDesignEvaluation {
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

function hasGenuineMatchingConfigurations(
  designEvaluation: SearchDesignEvaluation,
  configurationEvidence: readonly SearchConfigurationEvidence[],
): boolean {
  if (designEvaluation.result_class !== "CONFIRMED_MATCH") return false;
  const matchingIds = designEvaluation.matching_configuration_ids;
  if (matchingIds.length === 0) return false;
  const uniqueMatchingIds = new Set(matchingIds);
  if (uniqueMatchingIds.size !== matchingIds.length) return false;
  const trueConfigurationIds = new Set(
    configurationEvidence
      .filter((configuration) => configuration.truth === "TRUE")
      .map((configuration) => configuration.configuration_id),
  );
  if (trueConfigurationIds.size !== uniqueMatchingIds.size) return false;
  return matchingIds.every((id) => trueConfigurationIds.has(id));
}

function hasUniqueConfigurationIds(configurationEvidence: readonly SearchConfigurationEvidence[]): boolean {
  const ids = configurationEvidence.map((configuration) => configuration.configuration_id);
  return new Set(ids).size === ids.length;
}

function hasConsistentBoatDesignId(
  designId: string,
  configurationEvidence: readonly SearchConfigurationEvidence[],
): boolean {
  return configurationEvidence.every((configuration) => configuration.boat_design_id === designId);
}

// SLICE-0051 non-regression: a pure `draft_max`-only match keeps the legacy
// `resolved_draft_m` shape -- `resolved_draft_m` must itself be a canonical
// positive decimal that genuinely satisfies the requested MAXIMUM bound
// (never a fabricated/stale value that would silently contradict its own
// CONFIRMED-match status).
function isValidDraftOnlyConfirmedMatch(
  value: unknown,
  active: SearchActiveRequirement,
): value is DraftOnlyConfirmedMatch {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (active.draft_max === undefined) return false;
  return (
    typeof v.native_listing_id === "string" &&
    typeof v.resolved_draft_m === "string" &&
    isCanonicalPositiveDecimalString(v.resolved_draft_m) &&
    compareCanonicalDecimalStrings(v.resolved_draft_m, active.draft_max) <= 0 &&
    typeof v.publishing_organization_id === "string" &&
    isFreshnessStatus(v.freshness_status) &&
    (v.last_confirmed_at === null || typeof v.last_confirmed_at === "string") &&
    typeof v.discovery_token === "string"
  );
}

function isValidTypedConfirmedMatch(
  value: unknown,
  active: SearchActiveRequirement,
): value is NativeInventoryConfirmedMatch {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.native_listing_id === "string" &&
    typeof v.publishing_organization_id === "string" &&
    isFreshnessStatus(v.freshness_status) &&
    (v.last_confirmed_at === null || typeof v.last_confirmed_at === "string") &&
    typeof v.discovery_token === "string" &&
    Array.isArray(v.criterion_evidence) &&
    v.criterion_evidence.every((evidence: unknown) => isValidPositiveCriterionEvidence(evidence, active)) &&
    hasExactActiveCriterionCoverage(v.criterion_evidence as SearchCriterionEvidence[], active) &&
    Array.isArray(v.design_configuration_evidence) &&
    v.design_configuration_evidence.every((evidence: unknown) =>
      isValidConfigurationEvidence(evidence, active),
    ) &&
    hasUniqueConfigurationIds(v.design_configuration_evidence as SearchConfigurationEvidence[]) &&
    isValidDesignEvaluation(v.design_evaluation) &&
    hasConsistentBoatDesignId(
      (v.design_evaluation as SearchDesignEvaluation).design_id,
      v.design_configuration_evidence as SearchConfigurationEvidence[],
    ) &&
    hasGenuineMatchingConfigurations(
      v.design_evaluation as SearchDesignEvaluation,
      v.design_configuration_evidence as SearchConfigurationEvidence[],
    )
  );
}

function isValidClaimOnlyMatch(
  value: unknown,
  active: SearchActiveRequirement,
): value is PublisherClaimMatch {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.native_listing_id === "string" &&
    typeof v.publishing_organization_id === "string" &&
    isFreshnessStatus(v.freshness_status) &&
    (v.last_confirmed_at === null || typeof v.last_confirmed_at === "string") &&
    v.source_basis === "PUBLISHER_CLAIM" &&
    typeof v.discovery_token === "string" &&
    Array.isArray(v.criterion_evidence) &&
    v.criterion_evidence.every((evidence: unknown) => isValidPositiveCriterionEvidence(evidence, active)) &&
    hasExactActiveCriterionCoverage(v.criterion_evidence as SearchCriterionEvidence[], active)
  );
}

/**
 * Strictly validate a parsed JSON value as a well-formed, internally
 * consistent `SearchResultBody`. Returns `null` for anything malformed --
 * including a syntactically valid but incomplete/truncated body, a
 * non-array where an array is required, a count that is not a nonnegative
 * integer or does not match its own array's length, a BASE payload carrying
 * any key other than `locale`/`active_requirement`, a confirmed match in the
 * wrong shape for its own active requirement (legacy vs. typed-evidence), a
 * malformed/missing/inconsistent `page_size`/`evaluation_state`/
 * `next_cursor` bounded-page envelope, or any malformed nested evidence
 * object. Exported for direct unit testing.
 */
export function validateSearchResultBody(
  value: unknown,
  expected: { locale: string },
): SearchResultBody | null {
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;
  if (typeof v.locale !== "string" || v.locale !== expected.locale) return null;
  if (!("active_requirement" in v) || !isValidActiveRequirement(v.active_requirement)) {
    return null;
  }
  const activeRequirement = v.active_requirement as SearchActiveRequirement | null;

  if (activeRequirement === null) {
    // BASE state: the real FastAPI BASE contract returns exactly
    // `{locale, active_requirement}` and nothing else.
    const keys = Object.keys(v);
    if (keys.length !== 2 || !keys.includes("active_requirement")) return null;
    return { locale: v.locale, active_requirement: null };
  }

  // SLICE-0051 non-regression: a pure draft_max-only active requirement
  // keeps the legacy wire shape; every other combination uses the
  // SLICE-0055 typed-evidence shape -- mirrors `src/hullq/api/app.py`'s
  // `is_pure_draft_only` branch exactly.
  const isLegacyShape =
    activeRequirement.keel_configuration === undefined &&
    activeRequirement.loa_min === undefined &&
    activeRequirement.loa_max === undefined &&
    activeRequirement.rudder_configuration === undefined &&
    activeRequirement.hull_configuration === undefined &&
    activeRequirement.cockpit_position === undefined &&
    activeRequirement.deck_saloon === undefined &&
    activeRequirement.beam_min === undefined &&
    activeRequirement.beam_max === undefined &&
    activeRequirement.hull_material === undefined;

  if (
    !Array.isArray(v.confirmed_matches) ||
    !v.confirmed_matches.every((match: unknown) =>
      isLegacyShape
        ? isValidDraftOnlyConfirmedMatch(match, activeRequirement)
        : isValidTypedConfirmedMatch(match, activeRequirement),
    )
  ) {
    return null;
  }
  if (
    !isNonNegativeSafeInteger(v.confirmed_match_count) ||
    v.confirmed_match_count !== v.confirmed_matches.length
  ) {
    return null;
  }
  if (!isNonNegativeSafeInteger(v.insufficient_data_count)) return null;

  if (
    !Array.isArray(v.publisher_claim_matches) ||
    !v.publisher_claim_matches.every((match: unknown) => isValidClaimOnlyMatch(match, activeRequirement))
  ) {
    return null;
  }
  if (
    !isNonNegativeSafeInteger(v.publisher_claim_match_count) ||
    v.publisher_claim_match_count !== v.publisher_claim_matches.length
  ) {
    return null;
  }

  // SLICE-0096 bounded-page envelope (independent review Finding C,
  // closed round 1 for Power; closed here for Sail -- Finding C1): mandatory
  // on every genuine RESULT response, mirroring the identical hard
  // invariant `hullq.application.native_inventory_query
  // .NativeInventorySearchResultPage.__post_init__`/`DraftMaxSearchResultPage
  // .__post_init__` already enforce server-side.
  if (
    !isNonNegativeSafeInteger(v.page_size) ||
    (v.page_size as number) < 1 ||
    (v.page_size as number) > 50
  ) {
    return null;
  }
  if (v.evaluation_state !== "PARTIAL" && v.evaluation_state !== "COMPLETE") {
    return null;
  }
  if (!("next_cursor" in v) || !(v.next_cursor === null || typeof v.next_cursor === "string")) {
    return null;
  }
  if (v.evaluation_state === "PARTIAL" && (v.next_cursor === null || v.next_cursor === "")) {
    return null;
  }
  if (v.evaluation_state === "COMPLETE" && v.next_cursor !== null) {
    return null;
  }

  return {
    locale: v.locale,
    active_requirement: activeRequirement,
    confirmed_matches: v.confirmed_matches as SearchConfirmedMatch[],
    confirmed_match_count: v.confirmed_match_count,
    insufficient_data_count: v.insufficient_data_count,
    publisher_claim_matches: v.publisher_claim_matches as PublisherClaimMatch[],
    publisher_claim_match_count: v.publisher_claim_match_count,
    page_size: v.page_size as number,
    evaluation_state: v.evaluation_state as "PARTIAL" | "COMPLETE",
    next_cursor: v.next_cursor as string | null,
  };
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
    let parsed: unknown;
    try {
      parsed = await response.json();
    } catch {
      parsed = null;
    }
    // SLICE-0096 independent review round 2 Finding C1: a truncated,
    // structurally invalid or internally inconsistent HTTP-200 body is a
    // service/contract failure, never a successful empty Search -- see
    // `validateSearchResultBody`'s own docstring above.
    const result = parsed === null ? null : validateSearchResultBody(parsed, { locale });
    if (result === null) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    return { status: 200, location: null, result, invalid: null };
  }
  return { status: 502, location: null, result: null, invalid: null };
}
