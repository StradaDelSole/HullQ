// SLICE-0054: the only module allowed to talk to FastAPI's owner-direct
// draft boundary. Astro never queries PostgreSQL directly and never
// reimplements ownership/version-conflict/payload-validation decisions in
// TypeScript -- every result here is exactly what FastAPI decided, forwarded
// verbatim.
//
// This module is also the SLICE-0054 contract §9 CSRF proxy: it is Astro's
// own server calling FastAPI server-to-server, never the browser calling
// FastAPI directly. `originHeader` must be the *browser's own* `Origin`
// header value as Astro received it on the incoming page request -- this
// module forwards it unmodified rather than substituting a trusted value, so
// FastAPI's Origin check still reflects what the browser actually sent (see
// `hullq.api.app._require_owner_direct_csrf`). The fixed
// `X-HullQ-Requested-With` header is added here, by Astro's server, never by
// browser JavaScript -- so no CORS preflight/grant is ever needed for this
// boundary.
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie (minted by FastAPI, `HttpOnly`) reaches FastAPI on
// this server-to-server call; it is never read, parsed or stored by this
// module or exposed to browser JavaScript.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "owner-direct-draft-v1";

export interface OwnerDirectDraft {
  draft_id: string;
  version: number;
  created_at: string;
  updated_at: string;
  "physical_boat.marketed_brand_claim"?: string;
  "physical_boat.model_designation_claim"?: string;
  "physical_boat.build_year"?: number;
  "physical_boat.boat_name"?: string;
  "listing_offer.asking_price_mode"?: "AMOUNT" | "POA";
  "listing_offer.asking_price_amount"?: string;
  "listing_offer.currency"?: string;
  "listing_offer.location_country"?: string;
  "listing_offer.location_region"?: string;
}

export type OwnerDirectDraftPayloadInput = Omit<
  OwnerDirectDraft,
  "draft_id" | "version" | "created_at" | "updated_at"
>;

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function csrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE,
  };
}

export type OwnerDirectDraftListResult =
  | { kind: "unauthenticated" }
  | { kind: "ok"; data: OwnerDirectDraft[] };

/**
 * List the current Account's own drafts, newest first. Returns
 * `{kind: "unauthenticated"}` for a missing/invalid session and for any
 * network failure -- the page renders the identical "please log in" state
 * either way.
 */
export async function fetchOwnerDirectDrafts(
  apiBaseUrl: string,
  cookieHeader: string | null,
): Promise<OwnerDirectDraftListResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/api/owner-direct/drafts`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (!response.ok) {
    return { kind: "unauthenticated" };
  }
  const data = (await response.json()) as { drafts: OwnerDirectDraft[] };
  return { kind: "ok", data: data.drafts };
}

export type OwnerDirectDraftReadResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "ok"; data: OwnerDirectDraft };

/**
 * Read one draft. `not_found` covers both a genuinely unknown draft_id and
 * one owned by a different Account -- FastAPI already collapses those, so
 * this client never distinguishes them either (contract §3/§9 non-enumeration).
 */
export async function fetchOwnerDirectDraft(
  apiBaseUrl: string,
  draftId: string,
  cookieHeader: string | null,
): Promise<OwnerDirectDraftReadResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/api/owner-direct/drafts/${encodeURIComponent(draftId)}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (response.status === 404) {
    return { kind: "not_found" };
  }
  if (!response.ok) {
    return { kind: "not_found" };
  }
  const data = (await response.json()) as OwnerDirectDraft;
  return { kind: "ok", data };
}

export type OwnerDirectDraftCreateResult =
  | { kind: "unauthenticated" }
  | { kind: "invalid" }
  | { kind: "ok"; data: OwnerDirectDraft };

/**
 * Create one new empty/partial draft owned by the current Account.
 * `originHeader` and `cookieHeader` must be exactly what Astro received on
 * the incoming browser request (see module docstring).
 */
export async function createOwnerDirectDraft(
  apiBaseUrl: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<OwnerDirectDraftCreateResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/api/owner-direct/drafts`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({}),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (!response.ok) {
    return { kind: "invalid" };
  }
  const data = (await response.json()) as OwnerDirectDraft;
  return { kind: "ok", data };
}

export type OwnerDirectDraftUpdateResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "conflict" }
  | { kind: "invalid" }
  | { kind: "ok"; data: OwnerDirectDraft };

/**
 * Save the full bounded draft payload iff `expectedVersion` still matches
 * the currently persisted version (contract §7). A stale version returns
 * `conflict` -- the caller must never silently retry with a newer expected
 * version behind the user's back.
 */
export async function updateOwnerDirectDraft(
  apiBaseUrl: string,
  draftId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  expectedVersion: number,
  payload: OwnerDirectDraftPayloadInput,
): Promise<OwnerDirectDraftUpdateResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}/api/owner-direct/drafts/${encodeURIComponent(draftId)}`, {
      method: "PUT",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ expected_version: expectedVersion, ...payload }),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 401) {
    return { kind: "unauthenticated" };
  }
  if (response.status === 404) {
    return { kind: "not_found" };
  }
  if (response.status === 409) {
    return { kind: "conflict" };
  }
  if (!response.ok) {
    return { kind: "invalid" };
  }
  const data = (await response.json()) as OwnerDirectDraft;
  return { kind: "ok", data };
}
