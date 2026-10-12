// SLICE-0082: the only module allowed to talk to FastAPI's broker-confirmed
// PhysicalBoat -> canonical BoatDesign first-association boundary. Astro
// never queries PostgreSQL directly and never reimplements the bounded
// selector/authorization/CAS semantics -- every result here is exactly what
// FastAPI decided, forwarded verbatim (mirrors `inventoryEditingApi.ts`'s
// identical discipline).
//
// This module is also the CSRF proxy for the one mutation it exposes: it
// always adds the fixed `X-HullQ-Requested-With: broker-design-association-v1`
// header and forwards the browser's own `Origin` header value as Astro
// received it on the incoming page request -- never a substituted trusted
// value.
//
// Independent review Finding C (2026-10-12): every `response.json()` call
// is wrapped and the parsed body is structurally validated before any field
// is trusted -- a malformed/unexpected-shape body from FastAPI degrades to
// `{kind: "service_error"}` here, never a thrown exception that could crash
// the whole inventory-editor page render or silently propagate `undefined`
// into a field a caller treats as authoritative.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "broker-design-association-v1";

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function csrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE,
  };
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

/** Parse a response body as JSON without ever throwing -- a non-JSON or
 * empty body becomes `undefined`, which every caller below treats as
 * "malformed", not as "field absent and therefore falsy". */
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

function isNullableNumber(value: unknown): value is number | null {
  return value === null || typeof value === "number";
}

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

// ---------------------------------------------------------------------------
// Read: bounded candidate search
// ---------------------------------------------------------------------------

/**
 * The recorded `BOAT_DESIGN_SCHEMA.v0.5` `generation` identity block
 * (independent review Finding B): what actually distinguishes two
 * candidates that share an identical brand, model name and even identical
 * model-level first/last-built years but are genuinely different designs.
 * Every field is `null`/`[]` only when genuinely unrecorded -- never
 * inferred.
 */
export interface GenerationIdentity {
  label: string | null;
  sequence: number | null;
  aliases: string[];
  first_built: number | null;
  last_built: number | null;
  hull_number_from: string | null;
  hull_number_to: string | null;
  boundary_confidence: string | null;
}

export interface DesignCandidate {
  boat_design_ref: string;
  boat_model_id: string;
  canonical_model_name: string;
  generation: GenerationIdentity;
  brand_names: string[];
  first_built: number | null;
  last_built: number | null;
}

function isGenerationIdentity(value: unknown): value is GenerationIdentity {
  if (!isRecord(value)) return false;
  return (
    isNullableString(value.label) &&
    isNullableNumber(value.sequence) &&
    isStringArray(value.aliases) &&
    isNullableNumber(value.first_built) &&
    isNullableNumber(value.last_built) &&
    isNullableString(value.hull_number_from) &&
    isNullableString(value.hull_number_to) &&
    isNullableString(value.boundary_confidence)
  );
}

function isDesignCandidate(value: unknown): value is DesignCandidate {
  if (!isRecord(value)) return false;
  return (
    typeof value.boat_design_ref === "string" &&
    value.boat_design_ref.length > 0 &&
    typeof value.boat_model_id === "string" &&
    typeof value.canonical_model_name === "string" &&
    isGenerationIdentity(value.generation) &&
    isStringArray(value.brand_names) &&
    isNullableNumber(value.first_built) &&
    isNullableNumber(value.last_built)
  );
}

type AuthFailure =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" };

function authFailureFromStatus(status: number): AuthFailure | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  if (status === 403) return { kind: "mfa_required" };
  return null;
}

export type DesignCandidatesResult =
  | AuthFailure
  | { kind: "invalid_query" }
  | { kind: "service_error" }
  | { kind: "ok"; candidates: DesignCandidate[] };

export async function fetchDesignCandidates(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  query: string,
  cookieHeader: string | null,
): Promise<DesignCandidatesResult> {
  const base = trimBase(apiBaseUrl);
  const search = query ? `?q=${encodeURIComponent(query)}` : "";
  let response: Response;
  try {
    response = await fetch(
      `${base}${basePath(organizationId, nativeListingId)}/design-candidates${search}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 400) return { kind: "invalid_query" };
  if (!response.ok) return { kind: "service_error" };
  const parsed = await safeJson(response);
  if (
    !isRecord(parsed) ||
    !Array.isArray(parsed.candidates) ||
    !parsed.candidates.every(isDesignCandidate)
  ) {
    return { kind: "service_error" };
  }
  return { kind: "ok", candidates: parsed.candidates as DesignCandidate[] };
}

// ---------------------------------------------------------------------------
// Read: current link status
// ---------------------------------------------------------------------------

export interface DesignAssociationView {
  native_listing_id: string;
  link_status: "UNRESOLVED" | "LINKED";
  boat_design_ref: string | null;
  candidate: DesignCandidate | null;
}

function isDesignAssociationView(value: unknown): value is DesignAssociationView {
  if (!isRecord(value)) return false;
  return (
    typeof value.native_listing_id === "string" &&
    (value.link_status === "UNRESOLVED" || value.link_status === "LINKED") &&
    isNullableString(value.boat_design_ref) &&
    (value.candidate === null || isDesignCandidate(value.candidate))
  );
}

export type DesignAssociationReadResult =
  | AuthFailure
  | { kind: "chain_incomplete" }
  | { kind: "service_error" }
  | { kind: "ok"; data: DesignAssociationView };

export async function fetchDesignAssociation(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  cookieHeader: string | null,
): Promise<DesignAssociationReadResult> {
  const base = trimBase(apiBaseUrl);
  let response: Response;
  try {
    response = await fetch(
      `${base}${basePath(organizationId, nativeListingId)}/design-association`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 409) return { kind: "chain_incomplete" };
  if (!response.ok) return { kind: "service_error" };
  const parsed = await safeJson(response);
  if (!isDesignAssociationView(parsed)) return { kind: "service_error" };
  return { kind: "ok", data: parsed };
}

// ---------------------------------------------------------------------------
// Write: explicit confirmed first-time association
// ---------------------------------------------------------------------------

/**
 * Classify a 403 response. FastAPI's `_design_association_write_response`
 * (`hullq.api.app`) returns exactly two distinguishable 403 body shapes for
 * this boundary -- `{"error":"mfa_required"}` and
 * `{"error":"publishing_denied","reason":...}` -- plus the CSRF-rejection
 * path, which this module's own request construction always satisfies, so a
 * 403 that fails to parse as either known shape here is a genuine unexpected
 * condition, never silently folded into "publishing denied".
 */
async function classifyAssociate403(
  response: Response,
): Promise<{ kind: "mfa_required" } | { kind: "denied"; reason: string } | { kind: "service_error" }> {
  const body = await safeJson(response);
  if (!isRecord(body)) return { kind: "service_error" };
  if (body.error === "mfa_required") return { kind: "mfa_required" };
  if (body.error === "publishing_denied" && typeof body.reason === "string") {
    return { kind: "denied", reason: body.reason };
  }
  return { kind: "service_error" };
}

export type AssociateDesignResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "denied"; reason: string }
  | { kind: "chain_incomplete" }
  | { kind: "invalid_payload" }
  | { kind: "design_not_found" }
  | { kind: "shared_boat_conflict" }
  | { kind: "conflict"; storedBoatDesignRef: string | null }
  | { kind: "service_error" }
  | { kind: "ok"; outcome: "linked" | "already_linked"; storedBoatDesignRef: string };

export async function associateListingDesign(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  boatDesignRef: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<AssociateDesignResult> {
  const base = trimBase(apiBaseUrl);
  let response: Response;
  try {
    response = await fetch(
      `${base}${basePath(organizationId, nativeListingId)}/design-association`,
      {
        method: "POST",
        headers: {
          ...cookieHeaders(cookieHeader),
          ...csrfHeaders(originHeader),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ boat_design_ref: boatDesignRef }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 400) return { kind: "invalid_payload" };
  if (response.status === 403) return await classifyAssociate403(response);
  if (response.status === 409) {
    const body = await safeJson(response);
    if (!isRecord(body)) return { kind: "service_error" };
    if (body.error === "chain_incomplete") return { kind: "chain_incomplete" };
    if (body.error === "shared_boat_conflict") return { kind: "shared_boat_conflict" };
    const storedBoatDesignRef = typeof body.boat_design_ref === "string" ? body.boat_design_ref : null;
    return { kind: "conflict", storedBoatDesignRef };
  }
  if (response.status === 422) {
    const body = await safeJson(response);
    if (isRecord(body) && body.error === "design_not_found") return { kind: "design_not_found" };
    return { kind: "service_error" };
  }
  if (!response.ok) return { kind: "service_error" };
  const body = await safeJson(response);
  if (!isRecord(body) || typeof body.boat_design_ref !== "string") {
    return { kind: "service_error" };
  }
  if (body.outcome === "LINKED") {
    return { kind: "ok", outcome: "linked", storedBoatDesignRef: body.boat_design_ref };
  }
  if (body.outcome === "ALREADY_LINKED") {
    return { kind: "ok", outcome: "already_linked", storedBoatDesignRef: body.boat_design_ref };
  }
  return { kind: "service_error" };
}
