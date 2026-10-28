// SLICE-0095: the only module allowed to talk to FastAPI's authorized
// single-target hypothetical DRAFT Power Search-fit preview boundary.
// Astro never queries PostgreSQL directly and never re-derives technical
// match/non-match/insufficient-data truth itself -- every result here is
// exactly what FastAPI decided, forwarded verbatim (mirrors
// `brokerSearchFitApi.ts`'s identical discipline for the Sail preview --
// this is a structurally separate client, never a shared one, since the
// two previews have distinct endpoints/result shapes).
//
// This is a read-only GET boundary -- no CSRF header is required or sent.
//
// Independent review amendment Finding A (round 1): a syntactically
// well-formed 200 body is not enough -- a response that answers a
// *different* listing/scenario, echoes a different active_requirement,
// carries incoherent per-leaf truth/source/category evidence, or disagrees
// with its own declared `result_class`/`blockers` is just as dangerous as
// a malformed one: it could display a fabricated match or suppress the
// required `PUBLISHER_CLAIM` disclosure. Every such case must collapse to
// `service_error`, never a displayed (if surprising) result. This module
// reuses the exact same typed per-leaf/per-configuration evidence
// consistency validators `powerSearchApi.ts` already established for the
// public Power Buyer Search surface (`isValidCriterionEvidence`,
// `hasExactActiveCriterionCoverage`, `aggregateTruthFromLeaves`,
// `isValidConfigurationEvidence`, `isValidDesignEvaluation`,
// `hasGenuineMatchingConfigurations`, `hasUniqueConfigurationIds`,
// `hasConsistentBoatDesignId`, `isValidResultClass`) rather than a second,
// independently maintained copy of that logic -- this is a response-
// shape/consistency guard, never a reimplementation of the backend Search
// evaluator (no scoring, no qualification, no FieldResolution logic).
//
// Independent review amendment Finding F (round 2): this preview's own
// `design_evaluation` can legitimately be CONFIRMED_NON_MATCH/
// INSUFFICIENT_DATA alongside real `design_configuration_evidence` --
// unlike the public buyer surface, where `design_linked_matches[]` only
// ever serializes a genuine CONFIRMED_MATCH. Every design result class
// here must still agree with its own configuration-level evidence:
// `hullq.search.configuration_engine.evaluate_design_configuration_set`
// declares CONFIRMED_MATCH iff at least one configuration is TRUE (and
// then always lists every TRUE configuration id), CONFIRMED_NON_MATCH
// only when every configuration is a genuine confirmed FALSE, and
// INSUFFICIENT_DATA whenever no configuration is TRUE but the space is
// not exhaustively FALSE either (an UNKNOWN configuration, or a
// genuinely incomplete configuration space) -- never a TRUE configuration
// or a nonempty `matching_configuration_ids` on anything but a genuine
// MATCH.

import {
  aggregateTruthFromLeaves,
  hasConsistentBoatDesignId,
  hasExactActiveCriterionCoverage,
  hasGenuineMatchingConfigurations,
  hasUniqueConfigurationIds,
  isValidConfigurationEvidence,
  isValidCriterionEvidence,
  isValidDesignEvaluation,
  isValidResultClass,
  type PowerConfigurationEvidence,
  type PowerCriterionEvidence,
  type PowerDesignEvaluation,
} from "./powerSearchApi.ts";

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function trimBase(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/+$/, "");
}

function basePath(organizationId: string, nativeListingId: string): string {
  return (
    `/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/inventory/${encodeURIComponent(nativeListingId)}`
  );
}

async function safeJson(response: Response): Promise<unknown> {
  try {
    return await response.json();
  } catch {
    return undefined;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

type ResultClass = "CONFIRMED_MATCH" | "CONFIRMED_NON_MATCH" | "INSUFFICIENT_DATA";

const POWER_SEARCH_FIT_BLOCKERS = [
  "BOATDESIGN_CONFIGURATION_UNRESOLVED",
  "POWER_CATEGORY_UNCONFIRMED",
  "POWER_DRIVE_UNCONFIRMED",
  "POWER_ENGINE_COUNT_UNCONFIRMED",
] as const;
type PowerSearchFitBlocker = (typeof POWER_SEARCH_FIT_BLOCKERS)[number];
function isPowerSearchFitBlocker(value: unknown): value is PowerSearchFitBlocker {
  return typeof value === "string" && (POWER_SEARCH_FIT_BLOCKERS as readonly string[]).includes(value);
}

// Mirrors `hullq.application.power_inventory_query.PowerCategoryExclusionEvidence`'s
// own validated invariant: `resolution` is one of the *explicit*
// non-POWER/conflicted resolutions, and `reason` is only ever one of the
// positive-evidence reasons for SAIL/MOTORSAILER or a conflict reason for
// CONFLICT -- never any other combination.
const _NON_POWER_RESOLUTIONS = ["SAIL", "MOTORSAILER", "CONFLICT"] as const;
const _POSITIVE_REASONS = ["DESIGN_ONLY", "CONCRETE_ONLY", "SOURCES_AGREE"] as const;
const _CONFLICT_REASONS = ["DESIGN_CONCRETE_DISAGREEMENT", "CROSS_ORGANIZATION_DISAGREEMENT"] as const;

interface VesselCategoryExclusion {
  resolution: (typeof _NON_POWER_RESOLUTIONS)[number];
  reason: string;
}

function isValidVesselCategoryExclusion(value: unknown): value is VesselCategoryExclusion {
  if (!isRecord(value)) return false;
  if (!(_NON_POWER_RESOLUTIONS as readonly string[]).includes(value.resolution as string)) {
    return false;
  }
  if (typeof value.reason !== "string") return false;
  if (value.resolution === "CONFLICT") {
    return (_CONFLICT_REASONS as readonly string[]).includes(value.reason);
  }
  return (_POSITIVE_REASONS as readonly string[]).includes(value.reason);
}

function sameBlockerSet(actual: readonly string[], expected: readonly string[]): boolean {
  if (actual.length !== expected.length) return false;
  const actualSet = new Set(actual);
  if (actualSet.size !== actual.length) return false; // no duplicates
  return expected.every((b) => actualSet.has(b));
}

export interface PowerSearchFitView {
  native_listing_id: string;
  domain: "POWER";
  active_requirement: {
    power_drive?: string;
    power_engine_count?: string;
  };
  result_class: ResultClass;
  design_evaluation: PowerDesignEvaluation | null;
  design_configuration_evidence: PowerConfigurationEvidence[];
  criterion_evidence: PowerCriterionEvidence[];
  vessel_category_exclusion: VesselCategoryExclusion | null;
  source_basis: "PUBLISHER_CLAIM" | null;
  blockers: PowerSearchFitBlocker[];
}

/**
 * Strictly validate a parsed JSON value as a well-formed, internally
 * consistent `PowerSearchFitView` that actually answers *expected*'s own
 * request against *expected*'s own listing.
 *
 * `expected` carries exactly what this preview was actually asked for:
 * the target `nativeListingId` and the sent `powerDrive`/`powerEngineCount`
 * scenario values (each `null`/absent when that criterion was not part of
 * the request). A response naming a different listing, echoing a
 * different/extra/missing active-requirement key, carrying an evidence
 * leaf for an unrequested field, disagreeing between its own declared
 * `result_class` and its evidence/blockers, or mixing a design-plane
 * result with an inconsistent `source_basis` is never genuine and must
 * never be displayed.
 */
function isPowerSearchFitView(
  value: unknown,
  expected: { nativeListingId: string; powerDrive: string | null; powerEngineCount: string | null },
): value is PowerSearchFitView {
  if (!isRecord(value)) return false;
  if (value.native_listing_id !== expected.nativeListingId) return false;
  if (value.domain !== "POWER") return false;

  if (!isRecord(value.active_requirement)) return false;
  const activeRequirement = value.active_requirement;
  const expectedKeys: string[] = [];
  if (expected.powerDrive !== null) expectedKeys.push("power_drive");
  if (expected.powerEngineCount !== null) expectedKeys.push("power_engine_count");
  const actualKeys = Object.keys(activeRequirement);
  if (actualKeys.length !== expectedKeys.length || !expectedKeys.every((k) => actualKeys.includes(k))) {
    return false;
  }
  if (expected.powerDrive !== null && activeRequirement.power_drive !== expected.powerDrive) {
    return false;
  }
  if (
    expected.powerEngineCount !== null &&
    activeRequirement.power_engine_count !== expected.powerEngineCount
  ) {
    return false;
  }

  if (!isValidResultClass(value.result_class)) return false;

  const hasDesignEvaluation = value.design_evaluation !== null;
  if (hasDesignEvaluation && !isValidDesignEvaluation(value.design_evaluation)) return false;
  // Design-plane/source-basis consistency: a design-linked evaluation is
  // never also a publisher-claim-only one, and vice versa -- there is no
  // third state.
  if (hasDesignEvaluation && value.source_basis !== null) return false;
  if (!hasDesignEvaluation && value.source_basis !== "PUBLISHER_CLAIM") return false;

  if (!Array.isArray(value.design_configuration_evidence)) return false;
  if (!hasDesignEvaluation && value.design_configuration_evidence.length !== 0) return false;
  if (hasDesignEvaluation && value.design_configuration_evidence.length === 0) return false;
  if (
    !value.design_configuration_evidence.every((c: unknown) =>
      isValidConfigurationEvidence(c, expected.powerDrive, expected.powerEngineCount),
    )
  ) {
    return false;
  }

  if (!Array.isArray(value.criterion_evidence)) return false;
  if (!isStringArray(value.blockers) || !value.blockers.every(isPowerSearchFitBlocker)) return false;
  const blockers = value.blockers as PowerSearchFitBlocker[];
  if (new Set(blockers).size !== blockers.length) return false; // no duplicate blockers

  if (
    value.vessel_category_exclusion !== null &&
    !isValidVesselCategoryExclusion(value.vessel_category_exclusion)
  ) {
    return false;
  }

  const designEvaluation = value.design_evaluation as PowerDesignEvaluation | null;
  const designConfigurationEvidence = value.design_configuration_evidence as PowerConfigurationEvidence[];
  const criterionEvidence = value.criterion_evidence as PowerCriterionEvidence[];

  if (hasDesignEvaluation) {
    // Independent review amendment Finding F (round 2): every listed
    // configuration must genuinely belong to this same design, be
    // uniquely identified, and the design-level result class must agree
    // with the configuration-level truth/matching-id evidence it is
    // supposedly summarizing -- for every result class, not only
    // CONFIRMED_MATCH.
    if (!hasUniqueConfigurationIds(designConfigurationEvidence)) return false;
    if (!hasConsistentBoatDesignId(designEvaluation!.design_id, designConfigurationEvidence)) {
      return false;
    }
    const matchingIds = designEvaluation!.matching_configuration_ids;
    if (new Set(matchingIds).size !== matchingIds.length) return false; // no duplicate matching ids
    const trueConfigurationIds = designConfigurationEvidence
      .filter((c) => c.truth === "TRUE")
      .map((c) => c.configuration_id);

    if (designEvaluation!.result_class === "CONFIRMED_MATCH") {
      if (!hasGenuineMatchingConfigurations(designEvaluation!, designConfigurationEvidence)) {
        return false;
      }
    } else if (designEvaluation!.result_class === "CONFIRMED_NON_MATCH") {
      // Every configuration must be a genuine confirmed FALSE (never a
      // TRUE or UNKNOWN configuration hiding behind a declared
      // non-match), and no configuration can be listed as matching.
      if (trueConfigurationIds.length !== 0) return false;
      if (matchingIds.length !== 0) return false;
      if (!designConfigurationEvidence.every((c) => c.truth === "FALSE")) return false;
    } else {
      // INSUFFICIENT_DATA: no configuration may be TRUE and none may be
      // listed as matching -- an UNKNOWN configuration, or a genuinely
      // incomplete configuration space, is legitimate and never required
      // to look any particular way beyond that.
      if (trueConfigurationIds.length !== 0) return false;
      if (matchingIds.length !== 0) return false;
    }
  }

  if (hasDesignEvaluation && designEvaluation!.result_class !== "CONFIRMED_MATCH") {
    // Design/configuration eligibility never admitted this design to the
    // concrete funnel -- classified directly from the design-level
    // result, never consulting the concrete claim.
    if (criterionEvidence.length !== 0) return false;
    if (value.vessel_category_exclusion !== null) return false;
    if (value.result_class !== designEvaluation!.result_class) return false;
    const expectedBlockers: PowerSearchFitBlocker[] =
      designEvaluation!.result_class === "INSUFFICIENT_DATA"
        ? ["BOATDESIGN_CONFIGURATION_UNRESOLVED"]
        : [];
    return sameBlockerSet(blockers, expectedBlockers);
  }

  // From here: either design-unresolved (claim-only) or a genuine
  // design-level CONFIRMED_MATCH -- the category-admission/concrete-
  // classification three-way split applies identically to both planes.
  if (value.vessel_category_exclusion !== null) {
    // Explicit SAIL/MOTORSAILER/CONFLICT category exclusion.
    if (value.result_class !== "CONFIRMED_NON_MATCH") return false;
    if (criterionEvidence.length !== 0) return false;
    return blockers.length === 0;
  }

  if (criterionEvidence.length === 0) {
    // Category admission itself was insufficient (missing/UNKNOWN,
    // design-only, or another Organization's claim alone) -- never a
    // false exclusion and never a false match.
    if (value.result_class !== "INSUFFICIENT_DATA") return false;
    return sameBlockerSet(blockers, ["POWER_CATEGORY_UNCONFIRMED"]);
  }

  // Ordinary technical classification (claim-only or concrete).
  if (
    !criterionEvidence.every((e) => isValidCriterionEvidence(e, expected.powerDrive, expected.powerEngineCount))
  ) {
    return false;
  }
  if (!hasExactActiveCriterionCoverage(criterionEvidence, expected.powerDrive, expected.powerEngineCount)) {
    return false;
  }
  const aggregate = aggregateTruthFromLeaves(criterionEvidence);
  const expectedResultClass: ResultClass =
    aggregate === "TRUE"
      ? "CONFIRMED_MATCH"
      : aggregate === "FALSE"
        ? "CONFIRMED_NON_MATCH"
        : "INSUFFICIENT_DATA";
  if (value.result_class !== expectedResultClass) return false;

  if (expectedResultClass !== "INSUFFICIENT_DATA") {
    return blockers.length === 0;
  }
  const expectedBlockers: PowerSearchFitBlocker[] = [];
  for (const leaf of criterionEvidence) {
    if (leaf.truth !== "UNKNOWN") continue;
    if (leaf.field === "power_drive_configuration") expectedBlockers.push("POWER_DRIVE_UNCONFIRMED");
    if (leaf.field === "power_engine_count") expectedBlockers.push("POWER_ENGINE_COUNT_UNCONFIRMED");
  }
  return sameBlockerSet(blockers, [...new Set(expectedBlockers)]);
}

// ---------------------------------------------------------------------------
// Read: single-target hypothetical DRAFT Power Search-fit preview
// ---------------------------------------------------------------------------

type AuthFailure = { kind: "unauthenticated" } | { kind: "not_found" } | { kind: "mfa_required" };

function authFailureFromStatus(status: number): AuthFailure | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  return null;
}

export interface PowerSearchFitScenario {
  powerDrive?: string;
  powerEngineCount?: string;
}

export type PowerSearchFitResult =
  | AuthFailure
  | { kind: "publisher_role_required" }
  | { kind: "invalid_scenario"; message: string | null }
  | { kind: "not_previewable" }
  | { kind: "chain_integrity_fault" }
  | { kind: "service_error" }
  | { kind: "ok"; data: PowerSearchFitView };

async function classify403(
  response: Response,
): Promise<{ kind: "mfa_required" } | { kind: "publisher_role_required" } | { kind: "service_error" }> {
  const body = await safeJson(response);
  if (!isRecord(body)) return { kind: "service_error" };
  if (body.error === "mfa_required") return { kind: "mfa_required" };
  if (body.error === "publishing_denied" && body.reason === "PUBLISHER_ROLE_REQUIRED") {
    return { kind: "publisher_role_required" };
  }
  return { kind: "service_error" };
}

export async function fetchPowerSearchFit(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  scenario: PowerSearchFitScenario,
  cookieHeader: string | null,
): Promise<PowerSearchFitResult> {
  const base = trimBase(apiBaseUrl);
  const params = new URLSearchParams();
  if (scenario.powerDrive) params.set("power_drive", scenario.powerDrive);
  if (scenario.powerEngineCount) params.set("power_engine_count", scenario.powerEngineCount);
  const search = params.toString() ? `?${params.toString()}` : "";
  let response: Response;
  try {
    response = await fetch(
      `${base}${basePath(organizationId, nativeListingId)}/power-search-fit${search}`,
      {
        headers: cookieHeaders(cookieHeader),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 403) return await classify403(response);
  if (response.status === 400) {
    const body = await safeJson(response);
    const message = isRecord(body) && typeof body.message === "string" ? body.message : null;
    return { kind: "invalid_scenario", message };
  }
  if (response.status === 409) return { kind: "not_previewable" };
  if (response.status === 503) return { kind: "chain_integrity_fault" };
  if (!response.ok) return { kind: "service_error" };
  const body = await safeJson(response);
  const expected = {
    nativeListingId,
    powerDrive: scenario.powerDrive ?? null,
    powerEngineCount: scenario.powerEngineCount ?? null,
  };
  if (!isPowerSearchFitView(body, expected)) return { kind: "service_error" };
  return { kind: "ok", data: body };
}
