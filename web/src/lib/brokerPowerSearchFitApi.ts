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
// Every `response.json()` call is wrapped and the parsed body is
// structurally validated before any field is trusted -- a malformed/
// unexpected-shape body from FastAPI degrades to `{kind: "service_error"}`
// here, never a thrown exception or a fabricated confirmed result.

import type { ConfigurationEvidence, CriterionEvidence, DesignEvaluation } from "./brokerSearchFitApi";

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

function isNullableString(value: unknown): value is string | null {
  return value === null || typeof value === "string";
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

const RESULT_CLASSES = ["CONFIRMED_MATCH", "CONFIRMED_NON_MATCH", "INSUFFICIENT_DATA"] as const;
type ResultClass = (typeof RESULT_CLASSES)[number];
function isResultClass(value: unknown): value is ResultClass {
  return typeof value === "string" && (RESULT_CLASSES as readonly string[]).includes(value);
}

function isLeafCriterion(value: unknown): boolean {
  if (!isRecord(value)) return false;
  if (typeof value.field !== "string") return false;
  if (value.kind === "NUMERIC") return typeof value.comparison === "string";
  if (value.kind === "CATEGORICAL") return typeof value.equals === "string";
  return false;
}

function isCriterionEvidence(value: unknown): value is CriterionEvidence {
  if (!isRecord(value)) return false;
  const TRUTH_STATES = ["TRUE", "FALSE", "UNKNOWN"];
  return (
    isLeafCriterion(value.criterion) &&
    typeof value.field === "string" &&
    typeof value.truth === "string" &&
    TRUTH_STATES.includes(value.truth) &&
    isNullableString(value.reason) &&
    typeof value.explanation === "string" &&
    isNullableString(value.observed_value)
  );
}

function isConfigurationEvidence(value: unknown): value is ConfigurationEvidence {
  if (!isRecord(value)) return false;
  return (
    typeof value.configuration_id === "string" &&
    typeof value.boat_design_id === "string" &&
    isNullableString(value.named_variant_id) &&
    typeof value.truth === "string" &&
    Array.isArray(value.criterion_evidence) &&
    value.criterion_evidence.every(isCriterionEvidence)
  );
}

function isDesignEvaluation(value: unknown): value is DesignEvaluation {
  if (!isRecord(value)) return false;
  return (
    typeof value.design_id === "string" &&
    isResultClass(value.result_class) &&
    isStringArray(value.matching_configuration_ids) &&
    isNullableString(value.reason)
  );
}

export interface PowerSearchFitView {
  native_listing_id: string;
  domain: "POWER";
  active_requirement: {
    power_drive?: string;
    power_engine_count?: string;
  };
  result_class: ResultClass;
  design_evaluation: DesignEvaluation | null;
  design_configuration_evidence: ConfigurationEvidence[];
  criterion_evidence: CriterionEvidence[];
  vessel_category_exclusion: { resolution: string; reason: string } | null;
  source_basis: "PUBLISHER_CLAIM" | null;
  blockers: string[];
}

function isVesselCategoryExclusion(value: unknown): value is { resolution: string; reason: string } {
  if (!isRecord(value)) return false;
  return typeof value.resolution === "string" && typeof value.reason === "string";
}

function isPowerSearchFitView(value: unknown): value is PowerSearchFitView {
  if (!isRecord(value)) return false;
  if (typeof value.native_listing_id !== "string" || value.native_listing_id.length === 0) {
    return false;
  }
  if (value.domain !== "POWER") return false;
  if (!isRecord(value.active_requirement)) return false;
  if (!isResultClass(value.result_class)) return false;
  if (value.design_evaluation !== null && !isDesignEvaluation(value.design_evaluation)) {
    return false;
  }
  if (
    !Array.isArray(value.design_configuration_evidence) ||
    !value.design_configuration_evidence.every(isConfigurationEvidence)
  ) {
    return false;
  }
  if (!Array.isArray(value.criterion_evidence) || !value.criterion_evidence.every(isCriterionEvidence)) {
    return false;
  }
  if (value.vessel_category_exclusion !== null && !isVesselCategoryExclusion(value.vessel_category_exclusion)) {
    return false;
  }
  if (value.source_basis !== null && value.source_basis !== "PUBLISHER_CLAIM") return false;
  return isStringArray(value.blockers);
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
  if (!isPowerSearchFitView(body)) return { kind: "service_error" };
  return { kind: "ok", data: body };
}
