// SLICE-0072: the only module allowed to talk to FastAPI's broker
// post-promotion inventory offer/PhysicalBoat claim editor boundary. Astro
// never queries PostgreSQL directly and never reimplements revision/
// concurrency/ACTIVE-invariant semantics -- every result here is exactly
// what FastAPI decided, forwarded verbatim (mirrors `brokerApi.ts`'s and
// `mediaGalleryApi.ts`'s identical discipline).
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie reaches FastAPI on this server-to-server call, and
// this module is also the CSRF proxy for every mutation: it always adds the
// fixed `X-HullQ-Requested-With: professional-inventory-editing-v1` header
// and forwards the browser's own `Origin` header value as Astro received it
// on the incoming page request -- never a substituted trusted value.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "professional-inventory-editing-v1";

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

function editorPath(
  organizationId: string,
  nativeListingId: string,
  suffix: "edit" | "offer" | "claim",
): string {
  return (
    `/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/inventory/${encodeURIComponent(nativeListingId)}/${suffix}`
  );
}

// ---------------------------------------------------------------------------
// Read: current offer/claim detail
// ---------------------------------------------------------------------------

export interface InventoryEditDetail {
  native_listing_id: string;
  organization_id: string;
  lifecycle_state: string;
  freshness_status: string;
  last_confirmed_at: string | null;
  current_offer_revision_id: string | null;
  offer: Record<string, unknown> | null;
  current_claim_revision_id: string | null;
  claim: Record<string, unknown> | null;
  publication_readiness?: { status: string; blockers: string[] };
  current_public_status?: string;
  suppression_reasons?: string[];
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

export type InventoryEditDetailResult =
  | AuthFailure
  | { kind: "service_error" }
  | { kind: "ok"; data: InventoryEditDetail };

export async function fetchInventoryEditDetail(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  cookieHeader: string | null,
): Promise<InventoryEditDetailResult> {
  const base = trimBase(apiBaseUrl);
  let response: Response;
  try {
    response = await fetch(`${base}${editorPath(organizationId, nativeListingId, "edit")}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as InventoryEditDetail;
  return { kind: "ok", data };
}

// ---------------------------------------------------------------------------
// Write: offer / claim save
// ---------------------------------------------------------------------------

/**
 * Classify a 403 response from either save route. FastAPI's
 * `_offer_save_response`/`_claim_save_response` (`hullq.api.app`) return
 * exactly two distinguishable 403 body shapes for this boundary --
 * `{"error":"mfa_required"}` and `{"error":"publishing_denied","reason":...}`
 * -- plus the CSRF-rejection path, which this module's own request
 * construction always satisfies, so a 403 that fails to parse as either
 * known shape here is a genuine unexpected condition, never silently folded
 * into "publishing denied".
 */
async function classifySave403(
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

export type OfferSaveResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "denied"; reason: string }
  | { kind: "invalid_payload" }
  | { kind: "stale_version"; currentOfferRevisionId: string | null }
  | { kind: "active_invariant_violation"; blockers: string[] }
  | { kind: "service_error" }
  | { kind: "ok"; currentOfferRevisionId: string };

/** Save one ordinary NativeListing offer edit (contract §3/§4/§5). */
export async function saveListingOffer(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  body: Record<string, unknown>,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<OfferSaveResult> {
  const base = trimBase(apiBaseUrl);
  let response: Response;
  try {
    response = await fetch(`${base}${editorPath(organizationId, nativeListingId, "offer")}`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 400) return { kind: "invalid_payload" };
  if (response.status === 403) return await classifySave403(response);
  if (response.status === 409) {
    const data = (await response.json()) as { current_offer_revision_id?: string };
    return { kind: "stale_version", currentOfferRevisionId: data.current_offer_revision_id ?? null };
  }
  if (response.status === 422) {
    const data = (await response.json()) as { blockers?: string[] };
    return { kind: "active_invariant_violation", blockers: data.blockers ?? [] };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { current_offer_revision_id: string };
  return { kind: "ok", currentOfferRevisionId: data.current_offer_revision_id };
}

export type ClaimSaveResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "denied"; reason: string }
  | { kind: "chain_incomplete" }
  | { kind: "invalid_payload" }
  | { kind: "stale_version"; currentClaimRevisionId: string | null }
  | { kind: "active_invariant_violation"; blockers: string[] }
  | { kind: "service_error" }
  | { kind: "ok"; currentClaimRevisionId: string };

/** Save one ordinary Organization PhysicalBoat claim edit (contract §3/§4/§5). */
export async function saveListingClaim(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  body: Record<string, unknown>,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ClaimSaveResult> {
  const base = trimBase(apiBaseUrl);
  let response: Response;
  try {
    response = await fetch(`${base}${editorPath(organizationId, nativeListingId, "claim")}`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 400) return { kind: "invalid_payload" };
  if (response.status === 403) return await classifySave403(response);
  if (response.status === 409) {
    const data = (await response.json()) as {
      error?: string;
      current_claim_revision_id?: string;
    };
    if (data.error === "chain_incomplete") return { kind: "chain_incomplete" };
    return { kind: "stale_version", currentClaimRevisionId: data.current_claim_revision_id ?? null };
  }
  if (response.status === 422) {
    const data = (await response.json()) as { blockers?: string[] };
    return { kind: "active_invariant_violation", blockers: data.blockers ?? [] };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { current_claim_revision_id: string };
  return { kind: "ok", currentClaimRevisionId: data.current_claim_revision_id };
}
