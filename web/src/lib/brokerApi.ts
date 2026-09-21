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
