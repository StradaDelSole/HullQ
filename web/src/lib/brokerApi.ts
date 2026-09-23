// SLICE-0053: the only module allowed to talk to FastAPI's broker
// account/membership/Organization boundary. Astro never queries PostgreSQL
// directly and never reimplements tenant/MFA authorization in TypeScript --
// every result here is exactly what FastAPI decided, forwarded verbatim.
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie (minted by FastAPI, `HttpOnly`) reaches FastAPI on
// this server-to-server call; it is never read, parsed or stored by this
// module or exposed to browser JavaScript.

export interface OrganizationContext {
  organization_id: string;
  professional_category: string;
  publishing_eligibility: string;
  // SLICE-0063: bounded current presentation metadata only -- authorization
  // stays keyed exclusively by organization_id.
  public_display_name: string;
  roles: string[];
  mfa_required: boolean;
  mfa_satisfied: boolean;
}

export interface BrokerContext {
  account_id: string;
  organizations: OrganizationContext[];
}

export type BrokerContextResult =
  | { kind: "unauthenticated" }
  | { kind: "ok"; data: BrokerContext };

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

/**
 * Fetch the current Account's authorized Organization contexts. Returns
 * `{kind: "unauthenticated"}` for a missing/invalid session and for any
 * network failure -- the page renders the identical "please log in" state
 * either way.
 */
export async function fetchBrokerContext(
  apiBaseUrl: string,
  cookieHeader: string | null,
): Promise<BrokerContextResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/api/broker/context`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (!response.ok) {
    return { kind: "unauthenticated" };
  }
  const data = (await response.json()) as BrokerContext;
  return { kind: "ok", data };
}

export type OrganizationWorkspaceResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "ok"; data: OrganizationContext };

/**
 * Fetch one explicit Organization's workspace context. `not_found` covers
 * both a genuinely unknown Organization and one the current Account is not
 * an authorized member of -- FastAPI already collapses those, so this
 * client never distinguishes them either (contract §9/§E non-enumeration).
 */
export async function fetchOrganizationContext(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<OrganizationWorkspaceResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (response.status === 404) {
    return { kind: "not_found" };
  }
  if (response.status === 403) {
    return { kind: "mfa_required" };
  }
  if (!response.ok) {
    return { kind: "not_found" };
  }
  const data = (await response.json()) as OrganizationContext;
  return { kind: "ok", data };
}

// SLICE-0060: the authenticated, Organization-scoped, read-only NativeListing
// inventory overview. Every fact rendered from this response is exactly what
// FastAPI decided (contract §11) -- this module never infers lifecycle,
// offer, freshness or public-link eligibility on its own.

export interface InventoryOffer {
  kind: "AMOUNT" | "POA" | "NO_CURRENT_OFFER";
  amount: string | null;
  currency: string | null;
}

export interface InventoryItem {
  native_listing_id: string;
  lifecycle_state: "DRAFT" | "ACTIVE" | "WITHDRAWN";
  broker_listing_reference: string | null;
  created_at: string;
  offer: InventoryOffer;
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION" | "STALE" | "UNKNOWN";
  last_confirmed_at: string | null;
  is_publicly_listed: boolean;
}

export interface InventoryPage {
  items: InventoryItem[];
  next_cursor?: string;
}

export type OrganizationInventoryResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "invalid_cursor" }
  | { kind: "service_error" }
  | { kind: "ok"; data: InventoryPage };

/**
 * Fetch one page of one explicit Organization's NativeListing inventory.
 * `service_error` (any unexpected non-2xx status, or a network failure)
 * stays distinct from `ok` with an empty `items` array -- contract §12:
 * service failure must never be presented as "no listings".
 */
export async function fetchOrganizationInventory(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  options?: { cursor?: string; pageSize?: number },
): Promise<OrganizationInventoryResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (options?.cursor) {
    params.set("cursor", options.cursor);
  }
  if (options?.pageSize) {
    params.set("page_size", String(options.pageSize));
  }
  const query = params.toString();
  const url =
    `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/inventory` +
    (query ? `?${query}` : "");

  let response: Response;
  try {
    response = await fetch(url, { headers: cookieHeaders(cookieHeader), redirect: "manual" });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (response.status === 404) {
    return { kind: "not_found" };
  }
  if (response.status === 403) {
    return { kind: "mfa_required" };
  }
  if (response.status === 400) {
    return { kind: "invalid_cursor" };
  }
  if (!response.ok) {
    return { kind: "service_error" };
  }
  const data = (await response.json()) as InventoryPage;
  return { kind: "ok", data };
}

// SLICE-0064: the authenticated, Organization-scoped NativeListing lifecycle
// mutation boundary (publish/withdraw/reconfirm an already-existing
// NativeListing). Every result here is exactly what FastAPI decided -- this
// module never infers lifecycle/freshness outcome on its own.
//
// This module is also the SLICE-0064 contract §7 CSRF proxy: it is Astro's
// own server calling FastAPI server-to-server, never the browser calling
// FastAPI directly. `originHeader` must be the *browser's own* `Origin`
// header value as Astro received it on the incoming page request -- this
// module forwards it unmodified rather than substituting a trusted value
// (mirrors `professionalDraftApi.ts`'s identical rationale, and
// `hullq.api.app._require_inventory_lifecycle_csrf`). The fixed
// `X-HullQ-Requested-With` header is added here, by Astro's server, never by
// browser JavaScript.

const LIFECYCLE_CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const LIFECYCLE_CSRF_HEADER_VALUE = "professional-inventory-lifecycle-v1";

function lifecycleCsrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [LIFECYCLE_CSRF_HEADER_NAME]: LIFECYCLE_CSRF_HEADER_VALUE,
  };
}

function inventoryActionPath(
  organizationId: string,
  nativeListingId: string,
  action: "publish" | "withdraw" | "reconfirm",
): string {
  return (
    `/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/inventory/${encodeURIComponent(nativeListingId)}/${action}`
  );
}

/** Shared org-level authorization outcomes carried by every lifecycle result below. */
type InventoryActionAuthFailure =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" };

function inventoryActionAuthFailureFromStatus(
  status: number,
): { kind: "unauthenticated" } | { kind: "not_found" } | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  return null;
}

/**
 * Classify a 403 response from one of the three lifecycle mutation routes.
 * FastAPI's `_inventory_lifecycle_response`/`_inventory_reconfirm_response`
 * (`hullq.api.app`) return exactly two distinguishable 403 body shapes for
 * this boundary -- `{"error":"mfa_required"}` and
 * `{"error":"publishing_denied","reason":...}` -- plus the CSRF-rejection
 * path (`hullq.api.app._require_inventory_lifecycle_csrf`), which this
 * module's own request construction always satisfies (fixed Origin/header),
 * so a 403 that fails to parse as either known shape here is a genuine
 * unexpected condition, not a domain publishing denial (contract §14:
 * "service failure" must stay a distinct outcome, never silently folded
 * into "publishing denied").
 */
async function classifyInventoryAction403(
  response: Response,
): Promise<{ kind: "mfa_required" } | { kind: "denied"; reason: string } | { kind: "service_error" }> {
  let body: { error?: string; reason?: string } = {};
  try {
    body = (await response.json()) as { error?: string; reason?: string };
  } catch {
    return { kind: "service_error" };
  }
  if (body.error === "mfa_required") {
    return { kind: "mfa_required" };
  }
  if (body.error === "publishing_denied") {
    return { kind: "denied", reason: body.reason ?? "unknown" };
  }
  return { kind: "service_error" };
}

export type PublishListingResult =
  | InventoryActionAuthFailure
  | { kind: "denied"; reason: string }
  | { kind: "incomplete_listing" }
  | { kind: "state_conflict" }
  | { kind: "service_error" }
  | { kind: "ok"; transitionId: string };

/**
 * Publish one existing, complete, own DRAFT NativeListing to ACTIVE.
 * `not_found` covers both a genuinely unknown Organization/NativeListing and
 * one the current Account is not authorized for -- FastAPI already
 * collapses each layer, so this client never distinguishes them either.
 */
export async function publishOrganizationListing(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<PublishListingResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${inventoryActionPath(organizationId, nativeListingId, "publish")}`, {
      method: "POST",
      headers: { ...cookieHeaders(cookieHeader), ...lifecycleCsrfHeaders(originHeader) },
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = inventoryActionAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 403) return await classifyInventoryAction403(response);
  if (response.status === 422) return { kind: "incomplete_listing" };
  if (response.status === 409) return { kind: "state_conflict" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { transition_id: string };
  return { kind: "ok", transitionId: data.transition_id };
}

export type WithdrawListingResult =
  | InventoryActionAuthFailure
  | { kind: "denied"; reason: string }
  | { kind: "state_conflict" }
  | { kind: "service_error" }
  | { kind: "ok"; transitionId: string };

/** Withdraw one existing own ACTIVE NativeListing to WITHDRAWN. */
export async function withdrawOrganizationListing(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<WithdrawListingResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${inventoryActionPath(organizationId, nativeListingId, "withdraw")}`, {
      method: "POST",
      headers: { ...cookieHeaders(cookieHeader), ...lifecycleCsrfHeaders(originHeader) },
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = inventoryActionAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 403) return await classifyInventoryAction403(response);
  if (response.status === 409) return { kind: "state_conflict" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { transition_id: string };
  return { kind: "ok", transitionId: data.transition_id };
}

export type ReconfirmListingResult =
  | InventoryActionAuthFailure
  | { kind: "denied"; reason: string }
  | { kind: "invalid_operation_id" }
  | { kind: "state_conflict" }
  | { kind: "operation_id_conflict" }
  | { kind: "service_error" }
  | { kind: "ok"; occurredAt: string };

/**
 * Reconfirm one existing own ACTIVE NativeListing's freshness.
 * `confirmationId` MUST be a stable, caller-generated canonical UUID string
 * so a genuine browser retry (e.g. a double form submit) is idempotent
 * rather than creating two events (contract §11).
 */
export async function reconfirmOrganizationListing(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  confirmationId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ReconfirmListingResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}${inventoryActionPath(organizationId, nativeListingId, "reconfirm")}`,
      {
        method: "POST",
        headers: {
          ...cookieHeaders(cookieHeader),
          ...lifecycleCsrfHeaders(originHeader),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ confirmation_id: confirmationId }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = inventoryActionAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 403) return await classifyInventoryAction403(response);
  if (response.status === 400) return { kind: "invalid_operation_id" };
  if (response.status === 409) {
    const body = (await response.json()) as { error?: string };
    return body.error === "operation_id_conflict"
      ? { kind: "operation_id_conflict" }
      : { kind: "state_conflict" };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { occurred_at: string };
  return { kind: "ok", occurredAt: data.occurred_at };
}
