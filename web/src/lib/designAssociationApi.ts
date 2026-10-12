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

// ---------------------------------------------------------------------------
// Read: bounded candidate search
// ---------------------------------------------------------------------------

export interface DesignCandidate {
  boat_design_ref: string;
  boat_model_id: string;
  canonical_model_name: string;
  generation: unknown;
  brand_names: string[];
  first_built: number | null;
  last_built: number | null;
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
  const data = (await response.json()) as { candidates: DesignCandidate[] };
  return { kind: "ok", candidates: data.candidates };
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
  const data = (await response.json()) as DesignAssociationView;
  return { kind: "ok", data };
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
  let body: { error?: string; reason?: string } = {};
  try {
    body = (await response.json()) as { error?: string; reason?: string };
  } catch {
    return { kind: "service_error" };
  }
  if (body.error === "mfa_required") return { kind: "mfa_required" };
  if (body.error === "publishing_denied") return { kind: "denied", reason: body.reason ?? "unknown" };
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
    const data = (await response.json()) as {
      error?: string;
      boat_design_ref?: string;
    };
    if (data.error === "chain_incomplete") return { kind: "chain_incomplete" };
    if (data.error === "shared_boat_conflict") return { kind: "shared_boat_conflict" };
    return { kind: "conflict", storedBoatDesignRef: data.boat_design_ref ?? null };
  }
  if (response.status === 422) {
    const data = (await response.json()) as { error?: string };
    if (data.error === "design_not_found") return { kind: "design_not_found" };
    return { kind: "service_error" };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { outcome: string; boat_design_ref: string };
  if (data.outcome === "LINKED") {
    return { kind: "ok", outcome: "linked", storedBoatDesignRef: data.boat_design_ref };
  }
  if (data.outcome === "ALREADY_LINKED") {
    return { kind: "ok", outcome: "already_linked", storedBoatDesignRef: data.boat_design_ref };
  }
  return { kind: "service_error" };
}
