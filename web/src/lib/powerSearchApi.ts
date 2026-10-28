// SLICE-0093, extended SLICE-0094: the only module allowed to talk to the
// outside world for the public Power-only Search surface. Mirrors
// `searchApi.ts`'s identical discipline (`redirect: "manual"`, no
// PostgreSQL/Python-rule reimplementation), but talks to the entirely
// separate `/api/search/{locale}/power` route -- never the Sail
// `/api/search/{locale}` route, and never shares a response shape with it.

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

// SLICE-0094: the exact accepted public eight-token exact whitelist
// (`specs/POWER_ENGINE_COUNT_SEARCH_CONTRACT.v0.1.md` "One field, one
// meaning", `hullq.search.power_criteria_registry
// .SEARCH_POWER_ENGINE_COUNT_VALUES`). A current publisher's durable claim
// may truthfully assert 9-32, but 9 and above are never public Search
// filter tokens in this slice.
export const SEARCH_POWER_ENGINE_COUNT_VALUES = [
  "1",
  "2",
  "3",
  "4",
  "5",
  "6",
  "7",
  "8",
] as const;

export type SearchPowerEngineCountValue = (typeof SEARCH_POWER_ENGINE_COUNT_VALUES)[number];

// SLICE-0094: now sparse -- `power_drive` and/or `power_engine_count`,
// never neither (mirrors `searchApi.ts`'s own `SearchActiveRequirement`
// sparse-subset shape; FastAPI is the actual source of truth for "at least
// one" -- TypeScript cannot mechanically enforce that any more cheaply than
// at runtime).
export interface PowerActiveRequirement {
  power_drive?: SearchPowerDriveValue;
  power_engine_count?: SearchPowerEngineCountValue;
}

// Mirrors `src/hullq/api/app.py::_serialize_leaf_criterion` -- shared shape
// with the Sail surface's own `SearchLeafCriterion`. SLICE-0094 adds the
// NUMERIC variant (`power_engine_count`'s own RANGE leaf with
// threshold_min == threshold_max).
export type PowerLeafCriterion =
  | {
      kind: "NUMERIC";
      field: string;
      comparison: "MINIMUM" | "MAXIMUM" | "RANGE";
      threshold_min: string | null;
      threshold_max: string | null;
    }
  | { kind: "CATEGORICAL"; field: string; equals: string };

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

export function isSearchPowerDriveValue(value: unknown): value is SearchPowerDriveValue {
  return (
    typeof value === "string" &&
    (SEARCH_POWER_DRIVE_VALUES as readonly string[]).includes(value)
  );
}

export function isSearchPowerEngineCountValue(value: unknown): value is SearchPowerEngineCountValue {
  return (
    typeof value === "string" &&
    (SEARCH_POWER_ENGINE_COUNT_VALUES as readonly string[]).includes(value)
  );
}

// SLICE-0094: `active_requirement` is now sparse -- any non-empty subset of
// `power_drive`/`power_engine_count`, never neither and never any other
// key. Mirrors `searchApi.ts`'s own multi-key sparse validation.
const _ACTIVE_REQUIREMENT_KEYS = new Set(["power_drive", "power_engine_count"]);

function isValidActiveRequirement(value: unknown): value is PowerActiveRequirement | null {
  if (value === null) return true;
  if (typeof value !== "object") return false;
  const v = value as Record<string, unknown>;
  const keys = Object.keys(v);
  if (keys.length === 0 || keys.some((key) => !_ACTIVE_REQUIREMENT_KEYS.has(key))) {
    return false;
  }
  if ("power_drive" in v && !isSearchPowerDriveValue(v.power_drive)) return false;
  if ("power_engine_count" in v && !isSearchPowerEngineCountValue(v.power_engine_count)) {
    return false;
  }
  return true;
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

export function isValidTruthState(value: unknown): value is "TRUE" | "FALSE" | "UNKNOWN" {
  return value === "TRUE" || value === "FALSE" || value === "UNKNOWN";
}

// SLICE-0094 independent-review amendment Finding F: this surface has
// exactly two possible leaf criteria -- `power_drive_configuration`
// (CATEGORICAL) and `power_engine_count` (NUMERIC) -- so this validator is
// deliberately as strict as the real backend contract for *each*, never a
// generically loose "any NUMERIC/CATEGORICAL shape" acceptance that could
// let a malformed or wrong-request body slip through as if it were a
// genuine evidence object. A CATEGORICAL leaf's `equals` must be one of
// the five accepted drive tokens; a NUMERIC leaf must be `power_engine_count`
// with a RANGE comparison and identical lower/upper thresholds (the
// contract's own words: "The count filter uses an exact numeric RANGE with
// threshold_min=threshold_max"), each an exact canonical 1-8 token -- never
// MINIMUM/MAXIMUM, never differing thresholds, never a non-canonical
// numeric spelling.
export function isValidLeafCriterion(value: unknown): value is PowerLeafCriterion {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (v.kind === "CATEGORICAL") {
    return v.field === "power_drive_configuration" && isSearchPowerDriveValue(v.equals);
  }
  if (v.kind === "NUMERIC") {
    return (
      v.field === "power_engine_count" &&
      v.comparison === "RANGE" &&
      typeof v.threshold_min === "string" &&
      v.threshold_min === v.threshold_max &&
      isSearchPowerEngineCountValue(v.threshold_min)
    );
  }
  return false;
}

// SLICE-0094 independent-review amendment Finding F: "compatibility with
// the requested active requirement" -- an evidence leaf's own requested
// value must match the *same* field's value in the top-level
// `active_requirement` this response already claims to answer. Without
// this, a body could echo a consistent-looking `active_requirement` while
// every nested evidence object silently evaluated a *different* request --
// structurally well-formed per leaf, but misleading about what was
// actually requested. `expectedPowerDrive`/`expectedPowerEngineCount` are
// `null` when that criterion was not part of the request at all, in which
// case no evidence leaf for that field may legitimately appear.
export function criterionMatchesActiveRequirement(
  criterion: PowerLeafCriterion,
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): boolean {
  if (criterion.kind === "CATEGORICAL") {
    return expectedPowerDrive !== null && criterion.equals === expectedPowerDrive;
  }
  return expectedPowerEngineCount !== null && criterion.threshold_min === expectedPowerEngineCount;
}

// SLICE-0094 independent-review amendment Round 2, Finding F2: the backend
// never fabricates an `observed_value` for a leaf it did not actually
// resolve to the requested canonical value -- `TRUE` is only ever produced
// by `evaluate_numeric_leaf`/`evaluate_categorical_leaf`
// (`hullq.search.criteria`) when the observed concrete value equals the
// requested one exactly (RANGE with threshold_min==threshold_max for
// NUMERIC, strict `==` for CATEGORICAL). A `TRUE` leaf whose own
// `observed_value` differs from its own requested value is never genuine.
export function observedValueMatchesRequestedValue(
  criterion: PowerLeafCriterion,
  observedValue: string,
): boolean {
  if (criterion.kind === "CATEGORICAL") return observedValue === criterion.equals;
  return observedValue === criterion.threshold_min;
}

// Review amendment Finding J (MEDIUM): deep-validate every nested evidence
// object, never only its enclosing array's shape (`Array.isArray(...)`
// alone proves nothing about what is actually inside it).
//
// Round 2 Finding F2: also enforce (a) the evidence's own top-level `field`
// names the exact same field as its nested `criterion` -- the backend's
// `CriterionEvaluation.field` is always `criterion.field` by construction,
// so a mismatch is never genuine -- and (b) `truth`/`observed_value`
// consistency: the backend's `SearchCriterionEvidence` invariant is that
// `observed_value` is `None` whenever `truth` is not derived from a
// `CONFIRMED` qualified value (never present alongside `UNKNOWN`), and
// `TRUE` is only ever produced when the observed value equals the exact
// requested one. `FALSE` legitimately carries either a differing concrete
// observed value or `null` (e.g. a `NOT_APPLICABLE` confirmed exclusion
// never compares a concrete value) -- never suppressed here.
export function isValidCriterionEvidence(
  value: unknown,
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): value is PowerCriterionEvidence {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (!isValidLeafCriterion(v.criterion)) return false;
  const criterion = v.criterion;
  if (!criterionMatchesActiveRequirement(criterion, expectedPowerDrive, expectedPowerEngineCount)) {
    return false;
  }
  if (v.field !== criterion.field) return false;
  if (!isValidTruthState(v.truth)) return false;
  if (!(v.reason === null || typeof v.reason === "string")) return false;
  if (typeof v.explanation !== "string") return false;
  if (!(v.observed_value === null || typeof v.observed_value === "string")) return false;
  const observedValue = v.observed_value;
  if (v.truth === "UNKNOWN" && observedValue !== null) return false;
  if (v.truth === "TRUE") {
    if (observedValue === null || !observedValueMatchesRequestedValue(criterion, observedValue)) {
      return false;
    }
  }
  if (
    v.truth === "FALSE" &&
    observedValue !== null &&
    observedValueMatchesRequestedValue(criterion, observedValue)
  ) {
    return false;
  }
  return true;
}

// SLICE-0094 independent-review amendment Round 2, Finding F2: the backend
// always zips the full active-criteria tuple against one evaluation per
// criterion with `strict=True`
// (`hullq.application.native_inventory_query.classify_concrete_candidate`/
// `classify_claim_only_candidate`/`build_configuration_evidence`), so a
// genuine evidence array -- on a match's top-level `criterion_evidence` or
// on a per-configuration `criterion_evidence` -- always contains EXACTLY
// one entry per currently active criterion: never missing one (an empty
// array or a drive-only leaf set on a combined drive+count request is
// never genuine), never an extra/unrequested field, never a duplicate.
// This does not constrain each leaf's own `truth` -- a non-matching or
// `UNKNOWN` configuration's evidence still legitimately covers every
// active criterion, just not all `TRUE`.
export function hasExactActiveCriterionCoverage(
  evidence: readonly PowerCriterionEvidence[],
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): boolean {
  const expectedFields = new Set<string>();
  if (expectedPowerDrive !== null) expectedFields.add("power_drive_configuration");
  if (expectedPowerEngineCount !== null) expectedFields.add("power_engine_count");
  if (evidence.length !== expectedFields.size) return false;
  const seenFields = new Set<string>();
  for (const item of evidence) {
    if (!expectedFields.has(item.field) || seenFields.has(item.field)) return false;
    seenFields.add(item.field);
  }
  return true;
}

// SLICE-0094 independent-review amendment Round 3, Finding G3: the shared
// MUST-AND reduction every configuration's own aggregate `truth` must
// equal, given its already-validated leaves -- `hullq.search.query
// .and_reduce`'s identical semantics: FALSE dominates (any FALSE leaf
// means the whole configuration is FALSE), TRUE only when every leaf is
// TRUE, UNKNOWN otherwise. A configuration whose declared `truth` field
// disagrees with this reduction of its own leaves is never genuine --
// this is a generic response-contract consistency guard, never a
// reimplementation of the backend Search evaluator (no scoring, no
// qualification, no FieldResolution logic).
export function aggregateTruthFromLeaves(
  leaves: readonly PowerCriterionEvidence[],
): "TRUE" | "FALSE" | "UNKNOWN" {
  if (leaves.some((leaf) => leaf.truth === "FALSE")) return "FALSE";
  if (leaves.every((leaf) => leaf.truth === "TRUE")) return "TRUE";
  return "UNKNOWN";
}

export function isValidConfigurationEvidence(
  value: unknown,
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): value is PowerConfigurationEvidence {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  if (
    !(
      typeof v.configuration_id === "string" &&
      typeof v.boat_design_id === "string" &&
      (v.named_variant_id === null || typeof v.named_variant_id === "string") &&
      isValidTruthState(v.truth) &&
      Array.isArray(v.criterion_evidence) &&
      v.criterion_evidence.every((evidence: unknown) =>
        isValidCriterionEvidence(evidence, expectedPowerDrive, expectedPowerEngineCount),
      ) &&
      hasExactActiveCriterionCoverage(
        v.criterion_evidence as PowerCriterionEvidence[],
        expectedPowerDrive,
        expectedPowerEngineCount,
      )
    )
  ) {
    return false;
  }
  return v.truth === aggregateTruthFromLeaves(v.criterion_evidence as PowerCriterionEvidence[]);
}

// SLICE-0094 independent-review amendment Round 3, Finding G3: a positive
// match surface (a `publisher_claim_matches[]` entry, or a design-linked
// match's own concrete `criterion_evidence`) must have every active-
// criterion leaf confirmed TRUE -- the backend's
// `classify_claim_only_candidate`/`classify_concrete_candidate` only ever
// produce a `ResultClass.CONFIRMED_MATCH` (the only result class
// serialized into these arrays) when every active criterion's evaluation
// is TRUE, so a FALSE or UNKNOWN leaf here directly contradicts that
// invariant. This deliberately does NOT apply to per-configuration
// `design_configuration_evidence` -- a legitimate OTHER, nonmatching
// configuration's evidence still needs `isValidCriterionEvidence`'s
// generic truth/value consistency, never an all-TRUE requirement (see
// `isValidConfigurationEvidence` above instead, which checks internal
// aggregate-vs-leaf consistency rather than forcing TRUE).
function isValidPositiveCriterionEvidence(
  value: unknown,
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): value is PowerCriterionEvidence {
  return (
    isValidCriterionEvidence(value, expectedPowerDrive, expectedPowerEngineCount) &&
    (value as PowerCriterionEvidence).truth === "TRUE"
  );
}

// SLICE-0094 independent-review amendment Round 3, Finding G3: a design-
// linked match's own `design_evaluation.result_class` must genuinely be
// CONFIRMED_MATCH (the only result class this array ever serializes), and
// EVERY id it lists in `matching_configuration_ids` must correspond to an
// actually-present configuration in `design_configuration_evidence` whose
// own (already aggregate-validated) `truth` is TRUE -- a fabricated or
// stale matching-configuration id, or one naming a configuration that
// is not itself genuinely TRUE, is never genuine.
export function hasGenuineMatchingConfigurations(
  designEvaluation: PowerDesignEvaluation,
  configurationEvidence: readonly PowerConfigurationEvidence[],
): boolean {
  if (designEvaluation.result_class !== "CONFIRMED_MATCH") return false;
  if (designEvaluation.matching_configuration_ids.length === 0) return false;
  const trueConfigurationIds = new Set(
    configurationEvidence
      .filter((configuration) => configuration.truth === "TRUE")
      .map((configuration) => configuration.configuration_id),
  );
  return designEvaluation.matching_configuration_ids.every((id) => trueConfigurationIds.has(id));
}

export function isValidResultClass(
  value: unknown,
): value is "CONFIRMED_MATCH" | "CONFIRMED_NON_MATCH" | "INSUFFICIENT_DATA" {
  return (
    value === "CONFIRMED_MATCH" || value === "CONFIRMED_NON_MATCH" || value === "INSUFFICIENT_DATA"
  );
}

export function isValidDesignEvaluation(value: unknown): value is PowerDesignEvaluation {
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

function isValidDesignLinkedMatch(
  value: unknown,
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): value is PowerDesignLinkedMatch {
  if (typeof value !== "object" || value === null) return false;
  const v = value as Record<string, unknown>;
  return (
    typeof v.native_listing_id === "string" &&
    typeof v.publishing_organization_id === "string" &&
    isFreshnessStatus(v.freshness_status) &&
    (v.last_confirmed_at === null || typeof v.last_confirmed_at === "string") &&
    typeof v.discovery_token === "string" &&
    Array.isArray(v.criterion_evidence) &&
    v.criterion_evidence.every((evidence: unknown) =>
      isValidPositiveCriterionEvidence(evidence, expectedPowerDrive, expectedPowerEngineCount),
    ) &&
    hasExactActiveCriterionCoverage(
      v.criterion_evidence as PowerCriterionEvidence[],
      expectedPowerDrive,
      expectedPowerEngineCount,
    ) &&
    Array.isArray(v.design_configuration_evidence) &&
    v.design_configuration_evidence.every((evidence: unknown) =>
      isValidConfigurationEvidence(evidence, expectedPowerDrive, expectedPowerEngineCount),
    ) &&
    isValidDesignEvaluation(v.design_evaluation) &&
    hasGenuineMatchingConfigurations(
      v.design_evaluation as PowerDesignEvaluation,
      v.design_configuration_evidence as PowerConfigurationEvidence[],
    )
  );
}

function isValidClaimOnlyMatch(
  value: unknown,
  expectedPowerDrive: string | null,
  expectedPowerEngineCount: string | null,
): value is PowerClaimOnlyMatch {
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
    v.criterion_evidence.every((evidence: unknown) =>
      isValidPositiveCriterionEvidence(evidence, expectedPowerDrive, expectedPowerEngineCount),
    ) &&
    hasExactActiveCriterionCoverage(
      v.criterion_evidence as PowerCriterionEvidence[],
      expectedPowerDrive,
      expectedPowerEngineCount,
    )
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
 * BASE/no-op response, or `active_requirement.power_drive`/
 * `active_requirement.power_engine_count` echoing back a token other than
 * the one actually requested) is just as misleading as a malformed one,
 * and must collapse to the same `502` service error rather than being read
 * as a genuine (if surprising) empty result. `expected` carries exactly
 * what the caller actually asked for -- the URL `locale` path segment and
 * the parsed `power_drive`/`power_engine_count` query parameters (each
 * `null` when absent; `powerEngineCount` may be omitted entirely for a
 * drive-only caller) -- so this function can check the response actually
 * answers that request, not just that it is shaped like *some* valid
 * response.
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
  expected: {
    locale: string;
    powerDrive: SearchPowerDriveValue | null;
    powerEngineCount?: SearchPowerEngineCountValue | null;
  },
): PowerSearchResultBody | null {
  const expectedPowerEngineCount = expected.powerEngineCount ?? null;
  if (typeof value !== "object" || value === null) return null;
  const v = value as Record<string, unknown>;
  if (typeof v.locale !== "string" || v.locale !== expected.locale) return null;
  if (!("active_requirement" in v) || !isValidActiveRequirement(v.active_requirement)) {
    return null;
  }
  const activeRequirement = v.active_requirement as PowerActiveRequirement | null;

  if (expected.powerDrive === null && expectedPowerEngineCount === null) {
    // An unfiltered request must never come back as an active RESULT --
    // there is no requested criterion for it to have confirmed/excluded.
    if (activeRequirement !== null) return null;
  } else {
    // A filtered request must never come back as a no-op BASE response,
    // and must never echo back a different criterion value than the one
    // actually requested (wrong locale/criterion dispatch, never silently
    // accepted) -- and must never silently drop a requested criterion
    // (undefined) nor add one that was not requested at all.
    if (activeRequirement === null) return null;
    const echoedPowerDrive = activeRequirement.power_drive ?? null;
    const echoedPowerEngineCount = activeRequirement.power_engine_count ?? null;
    if (echoedPowerDrive !== expected.powerDrive) return null;
    if (echoedPowerEngineCount !== expectedPowerEngineCount) return null;
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
    !v.design_linked_matches.every((match: unknown) =>
      isValidDesignLinkedMatch(match, expected.powerDrive, expectedPowerEngineCount),
    )
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
    !v.publisher_claim_matches.every((match: unknown) =>
      isValidClaimOnlyMatch(match, expected.powerDrive, expectedPowerEngineCount),
    )
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
 * recognized keys at all) or "exactly one `power_drive` filter and/or
 * exactly one `power_engine_count` filter, each with exactly one value
 * that is one of its own accepted tokens" -- `{ ok: false }` for every
 * other shape: an invalid token value, duplicate keys (even with identical
 * values), or any unrecognized/extra query key alongside or instead of
 * `power_drive`/`power_engine_count`.
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
):
  | {
      ok: true;
      powerDrive: SearchPowerDriveValue | null;
      powerEngineCount: SearchPowerEngineCountValue | null;
    }
  | { ok: false } {
  const params = new URLSearchParams(queryString);
  const keys = new Set(params.keys());
  if (keys.size === 0) {
    return { ok: true, powerDrive: null, powerEngineCount: null };
  }
  for (const key of keys) {
    if (key !== "power_drive" && key !== "power_engine_count") {
      return { ok: false };
    }
  }

  let powerDrive: SearchPowerDriveValue | null = null;
  if (keys.has("power_drive")) {
    const values = params.getAll("power_drive");
    if (values.length !== 1 || !isSearchPowerDriveValue(values[0])) {
      return { ok: false };
    }
    powerDrive = values[0];
  }

  let powerEngineCount: SearchPowerEngineCountValue | null = null;
  if (keys.has("power_engine_count")) {
    const values = params.getAll("power_engine_count");
    if (values.length !== 1 || !isSearchPowerEngineCountValue(values[0])) {
      return { ok: false };
    }
    powerEngineCount = values[0];
  }

  return { ok: true, powerDrive, powerEngineCount };
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
    const expected = {
      locale,
      powerDrive: canonicalQuery.powerDrive,
      powerEngineCount: canonicalQuery.powerEngineCount,
    };
    const result = parsed === null ? null : validatePowerSearchResultBody(parsed, expected);
    if (result === null) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    return { status: 200, location: null, result, invalid: null };
  }
  return { status: 502, location: null, result: null, invalid: null };
}
