// SLICE-0084: the only module allowed to talk to FastAPI's authorized
// single-target hypothetical DRAFT Search-fit preview boundary. Astro never
// queries PostgreSQL directly and never re-derives technical match/non-match/
// insufficient-data truth itself -- every result here is exactly what
// FastAPI decided, forwarded verbatim (mirrors `designAssociationApi.ts`'s
// identical discipline).
//
// This is a read-only GET boundary -- no CSRF header is required or sent
// (mirrors `fetchDesignCandidates`/`fetchDesignAssociation`, not the
// mutating `associateListingDesign`).
//
// Every `response.json()` call is wrapped and the parsed body is
// structurally validated before any field is trusted -- a malformed/
// unexpected-shape body from FastAPI degrades to `{kind: "service_error"}`
// here, never a thrown exception or a fabricated confirmed result.

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

const TRUTH_STATES = ["TRUE", "FALSE", "UNKNOWN"] as const;
type TruthState = (typeof TRUTH_STATES)[number];
function isTruthState(value: unknown): value is TruthState {
  return typeof value === "string" && (TRUTH_STATES as readonly string[]).includes(value);
}

// ---------------------------------------------------------------------------
// Typed evidence shapes -- mirror `hullq.search.criteria.CriterionEvaluation`/
// `hullq.application.native_inventory_query.{SearchCriterionEvidence,
// ConfigurationEvidence}`/`hullq.search.configuration_engine.
// DesignQueryEvaluation`, forwarded by `hullq.api.app`'s existing SLICE-0055
// `_serialize_*` functions -- never a second encoding.
// ---------------------------------------------------------------------------

export interface LeafCriterion {
  kind: "NUMERIC" | "CATEGORICAL";
  field: string;
  comparison?: string;
  threshold_min?: string | null;
  threshold_max?: string | null;
  equals?: string;
}

function isLeafCriterion(value: unknown): value is LeafCriterion {
  if (!isRecord(value)) return false;
  if (typeof value.field !== "string") return false;
  if (value.kind === "NUMERIC") return typeof value.comparison === "string";
  if (value.kind === "CATEGORICAL") return typeof value.equals === "string";
  return false;
}

export interface CriterionEvidence {
  criterion: LeafCriterion;
  field: string;
  truth: TruthState;
  reason: string | null;
  explanation: string;
  observed_value: string | null;
}

function isCriterionEvidence(value: unknown): value is CriterionEvidence {
  if (!isRecord(value)) return false;
  return (
    isLeafCriterion(value.criterion) &&
    typeof value.field === "string" &&
    isTruthState(value.truth) &&
    isNullableString(value.reason) &&
    typeof value.explanation === "string" &&
    isNullableString(value.observed_value)
  );
}

export interface ConfigurationEvidence {
  configuration_id: string;
  boat_design_id: string;
  named_variant_id: string | null;
  truth: TruthState;
  criterion_evidence: CriterionEvidence[];
}

function isConfigurationEvidence(value: unknown): value is ConfigurationEvidence {
  if (!isRecord(value)) return false;
  return (
    typeof value.configuration_id === "string" &&
    typeof value.boat_design_id === "string" &&
    isNullableString(value.named_variant_id) &&
    isTruthState(value.truth) &&
    Array.isArray(value.criterion_evidence) &&
    value.criterion_evidence.every(isCriterionEvidence)
  );
}

export interface DesignEvaluation {
  design_id: string;
  result_class: ResultClass;
  matching_configuration_ids: string[];
  reason: string | null;
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

export interface SearchFitView {
  native_listing_id: string;
  active_requirement: {
    draft_max?: string;
    keel_configuration?: string;
    loa_min?: string;
    loa_max?: string;
    rudder_configuration?: string;
    hull_configuration?: string;
    cockpit_position?: string;
    deck_saloon?: string;
  };
  result_class: ResultClass;
  design_evaluation: DesignEvaluation | null;
  design_configuration_evidence: ConfigurationEvidence[];
  criterion_evidence: CriterionEvidence[];
  blockers: string[];
}

function isSearchFitView(value: unknown): value is SearchFitView {
  if (!isRecord(value)) return false;
  if (typeof value.native_listing_id !== "string" || value.native_listing_id.length === 0) {
    return false;
  }
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
  return isStringArray(value.blockers);
}

// ---------------------------------------------------------------------------
// Read: single-target hypothetical DRAFT Search-fit preview
// ---------------------------------------------------------------------------

type AuthFailure = { kind: "unauthenticated" } | { kind: "not_found" } | { kind: "mfa_required" };

function authFailureFromStatus(status: number): AuthFailure | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  return null;
}

export interface SearchFitScenario {
  draftMax?: string;
  keelConfiguration?: string;
  loaMin?: string;
  loaMax?: string;
  rudderConfiguration?: string;
  hullConfiguration?: string;
  cockpitPosition?: string;
  deckSaloon?: string;
}

export type SearchFitResult =
  | AuthFailure
  | { kind: "publisher_role_required" }
  | { kind: "invalid_scenario"; message: string | null }
  | { kind: "not_previewable" }
  | { kind: "chain_integrity_fault" }
  | { kind: "service_error" }
  | { kind: "ok"; data: SearchFitView };

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

export async function fetchSearchFit(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  scenario: SearchFitScenario,
  cookieHeader: string | null,
): Promise<SearchFitResult> {
  const base = trimBase(apiBaseUrl);
  const params = new URLSearchParams();
  if (scenario.draftMax) params.set("draft_max", scenario.draftMax);
  if (scenario.keelConfiguration) params.set("keel_configuration", scenario.keelConfiguration);
  if (scenario.loaMin) params.set("loa_min", scenario.loaMin);
  if (scenario.loaMax) params.set("loa_max", scenario.loaMax);
  if (scenario.rudderConfiguration) params.set("rudder_configuration", scenario.rudderConfiguration);
  if (scenario.hullConfiguration) params.set("hull_configuration", scenario.hullConfiguration);
  if (scenario.cockpitPosition) params.set("cockpit_position", scenario.cockpitPosition);
  if (scenario.deckSaloon) params.set("deck_saloon", scenario.deckSaloon);
  const search = params.toString() ? `?${params.toString()}` : "";
  let response: Response;
  try {
    response = await fetch(`${base}${basePath(organizationId, nativeListingId)}/search-fit${search}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
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
  if (!isSearchFitView(body)) return { kind: "service_error" };
  return { kind: "ok", data: body };
}
