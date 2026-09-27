// SLICE-0061: the only module allowed to talk to FastAPI's professional
// Organization listing-draft boundary. Astro never queries PostgreSQL
// directly and never reimplements Organization authorization/PUBLISHER-role/
// version-conflict/payload-validation decisions in TypeScript -- every
// result here is exactly what FastAPI decided, forwarded verbatim.
//
// This module is also the SLICE-0061 contract §8 CSRF proxy: it is Astro's
// own server calling FastAPI server-to-server, never the browser calling
// FastAPI directly. `originHeader` must be the *browser's own* `Origin`
// header value as Astro received it on the incoming page request -- this
// module forwards it unmodified rather than substituting a trusted value
// (see `ownerDirectDraftApi.ts`'s identical rationale, and
// `hullq.api.app._require_professional_draft_csrf`). The fixed
// `X-HullQ-Requested-With` header is added here, by Astro's server, never by
// browser JavaScript -- so no CORS preflight/grant is ever needed for this
// boundary.
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie (minted by FastAPI, `HttpOnly`) reaches FastAPI on
// this server-to-server call; it is never read, parsed or stored by this
// module or exposed to browser JavaScript.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "professional-listing-draft-v1";

// SLICE-0066: `physical_boat.build_year`'s canonical structured
// required-response shape (`specs/LISTING_ASSERTION_RESPONSE_CONTRACT.v0.1.md`
// §3) -- omission is represented by the key's absence, never by a value of
// this type, so unanswered/UNKNOWN/VALUE_ASSERTION stay three distinct
// states. FastAPI also still accepts a legacy bare integer as ingress
// compatibility, but this client only ever sends/reads the canonical form.
export type BuildYearResponse =
  | { assertion_kind: "VALUE_ASSERTION"; value: number }
  | { assertion_kind: "UNKNOWN" };

// SLICE-0067: the bounded server-owned promotion readiness reason
// vocabulary (`specs/PROFESSIONAL_LISTING_PROMOTION_CONTRACT.v0.1.md` §3.3).
// Display only -- never re-derived client-side; the authoritative
// evaluation always happens server-side, both for this display value and
// for the real mutation-time re-evaluation.
export type PromotionReadinessReason =
  | "MISSING_MARKETED_BRAND"
  | "MISSING_MODEL_DESIGNATION"
  | "MISSING_BUILD_YEAR_RESPONSE"
  | "MISSING_ASKING_PRICE_MODE"
  | "MISSING_LOCATION_COUNTRY"
  | "MISSING_BROKER_DESCRIPTION"
  | "MISSING_ASKING_PRICE_AMOUNT"
  | "MISSING_CURRENCY"
  | "CURRENCY_NOT_ALLOWED_FOR_POA";

export interface PromotionReadiness {
  ready: boolean;
  reasons: PromotionReadinessReason[];
}

export type ProfessionalDraftPromotionState = "EDITABLE" | "PROMOTED";

export interface ProfessionalListingDraft {
  draft_id: string;
  owner_organization_id: string;
  version: number;
  broker_listing_reference: string | null;
  "listing_offer.broker_description": string | null;
  created_at: string;
  updated_at: string;
  promotion_state: ProfessionalDraftPromotionState;
  promotion_readiness: PromotionReadiness;
  promoted_native_listing_id?: string;
  promoted_at?: string;
  "physical_boat.marketed_brand_claim"?: string;
  "physical_boat.model_designation_claim"?: string;
  "physical_boat.build_year"?: BuildYearResponse;
  "physical_boat.boat_name"?: string;
  "listing_offer.asking_price_mode"?: "AMOUNT" | "POA";
  "listing_offer.asking_price_amount"?: string;
  "listing_offer.currency"?: string;
  "listing_offer.location_country"?: string;
  "listing_offer.location_region"?: string;
}

export type ProfessionalDraftPayloadInput = Partial<
  Omit<
    ProfessionalListingDraft,
    | "draft_id"
    | "owner_organization_id"
    | "version"
    | "created_at"
    | "updated_at"
    | "promotion_state"
    | "promotion_readiness"
    | "promoted_native_listing_id"
    | "promoted_at"
  >
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

function draftsPath(organizationId: string): string {
  return `/api/broker/organizations/${encodeURIComponent(organizationId)}/drafts`;
}

/** Shared org-level authorization outcomes carried by every result below. */
type OrgAuthFailure =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "publisher_role_required" };

function orgAuthFailureFromStatus(status: number): OrgAuthFailure | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  if (status === 403) {
    // Distinguished only by response body below (mfa_required vs
    // publisher_role_required); callers pass the parsed body in.
    return null;
  }
  return null;
}

async function classify403(response: Response): Promise<OrgAuthFailure> {
  let body: { error?: string } = {};
  try {
    body = (await response.json()) as { error?: string };
  } catch {
    // fall through to the generic mfa_required classification below
  }
  if (body.error === "publisher_role_required") {
    return { kind: "publisher_role_required" };
  }
  return { kind: "mfa_required" };
}

export interface ProfessionalDraftListPage {
  drafts: ProfessionalListingDraft[];
  next_cursor?: string;
}

export type ProfessionalDraftListResult =
  | OrgAuthFailure
  | { kind: "invalid_cursor" }
  | { kind: "service_error" }
  | { kind: "ok"; data: ProfessionalDraftListPage };

/**
 * List one Organization's own drafts, newest-updated first. `not_found`
 * covers both a genuinely unknown Organization and one the current Account
 * is not an authorized `PUBLISHER` member of -- FastAPI already collapses
 * those, so this client never distinguishes them either.
 */
export async function fetchProfessionalDrafts(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  options?: { cursor?: string; pageSize?: number },
): Promise<ProfessionalDraftListResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (options?.cursor) params.set("cursor", options.cursor);
  if (options?.pageSize) params.set("page_size", String(options.pageSize));
  const query = params.toString();
  const url = `${base}${draftsPath(organizationId)}` + (query ? `?${query}` : "");

  let response: Response;
  try {
    response = await fetch(url, { headers: cookieHeaders(cookieHeader), redirect: "manual" });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 400) return { kind: "invalid_cursor" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as ProfessionalDraftListPage;
  return { kind: "ok", data };
}

export type ProfessionalDraftReadResult = OrgAuthFailure | { kind: "ok"; data: ProfessionalListingDraft };

/**
 * Read one draft. `not_found` covers an unknown Organization, an
 * unauthorized Organization and a foreign/unknown draft_id alike -- all
 * three collapse to the identical FastAPI 404 (contract §3.3/§7).
 */
export async function fetchProfessionalDraft(
  apiBaseUrl: string,
  organizationId: string,
  draftId: string,
  cookieHeader: string | null,
): Promise<ProfessionalDraftReadResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}${draftsPath(organizationId)}/${encodeURIComponent(draftId)}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "not_found" };
  const data = (await response.json()) as ProfessionalListingDraft;
  return { kind: "ok", data };
}

export type ProfessionalDraftCreateResult =
  | OrgAuthFailure
  | { kind: "invalid" }
  | { kind: "ok"; data: ProfessionalListingDraft };

/**
 * Create one new empty/partial draft owned by *organizationId*.
 * `originHeader` and `cookieHeader` must be exactly what Astro received on
 * the incoming browser request (see module docstring).
 */
export async function createProfessionalDraft(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ProfessionalDraftCreateResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${draftsPath(organizationId)}`, {
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
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "invalid" };
  const data = (await response.json()) as ProfessionalListingDraft;
  return { kind: "ok", data };
}

export type ProfessionalDraftUpdateResult =
  | OrgAuthFailure
  | { kind: "conflict" }
  | { kind: "promoted_immutable" }
  | { kind: "invalid" }
  | { kind: "ok"; data: ProfessionalListingDraft };

/**
 * Save the full bounded draft payload iff `expectedVersion` still matches
 * the currently persisted version (contract §7). A stale version returns
 * `conflict` -- the caller must never silently retry with a newer expected
 * version behind the user's back. SLICE-0067: a PROMOTED draft returns the
 * distinct `promoted_immutable` outcome instead, since that draft can never
 * become editable again no matter what expected_version is supplied.
 */
export async function updateProfessionalDraft(
  apiBaseUrl: string,
  organizationId: string,
  draftId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  expectedVersion: number,
  payload: ProfessionalDraftPayloadInput,
): Promise<ProfessionalDraftUpdateResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}${draftsPath(organizationId)}/${encodeURIComponent(draftId)}`,
      {
        method: "PUT",
        headers: {
          ...cookieHeaders(cookieHeader),
          ...csrfHeaders(originHeader),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ expected_version: expectedVersion, ...payload }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 409) {
    let body: { error?: string } = {};
    try {
      body = (await response.json()) as { error?: string };
    } catch {
      // fall through to the generic conflict classification below
    }
    if (body.error === "promoted_immutable") return { kind: "promoted_immutable" };
    return { kind: "conflict" };
  }
  if (!response.ok) return { kind: "invalid" };
  const data = (await response.json()) as ProfessionalListingDraft;
  return { kind: "ok", data };
}

// ---------------------------------------------------------------------------
// SLICE-0067: promote
// ---------------------------------------------------------------------------

export type ProfessionalDraftPromoteResult =
  | OrgAuthFailure
  | { kind: "invalid_request" }
  | { kind: "draft_not_found" }
  | { kind: "denied"; reason: string }
  | { kind: "not_ready"; reasons: PromotionReadinessReason[] }
  | { kind: "version_conflict" }
  | { kind: "duplicate_episode" }
  | { kind: "service_error" }
  | { kind: "ok"; outcome: "PROMOTED" | "ALREADY_PROMOTED"; nativeListingId: string };

/**
 * Promote one exact, content-ready draft version into a real marketplace
 * NativeListing (contract §6). Sends exactly the current draft version --
 * never a marketplace identity/resolution hint (contract §2). `originHeader`
 * and `cookieHeader` must be exactly what Astro received on the incoming
 * browser request (see module docstring) -- this reuses the identical
 * accepted professional draft CSRF boundary, not a new header value.
 */
export async function promoteProfessionalDraft(
  apiBaseUrl: string,
  organizationId: string,
  draftId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  expectedVersion: number,
): Promise<ProfessionalDraftPromoteResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}${draftsPath(organizationId)}/${encodeURIComponent(draftId)}/promote`,
      {
        method: "POST",
        headers: {
          ...cookieHeaders(cookieHeader),
          ...csrfHeaders(originHeader),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ expected_version: expectedVersion }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "unauthenticated" };
  }

  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "draft_not_found" };
  if (response.status === 400) return { kind: "invalid_request" };
  if (response.status === 403) {
    let body: { error?: string; reason?: string } = {};
    try {
      body = (await response.json()) as { error?: string; reason?: string };
    } catch {
      // fall through to the generic service_error classification below
    }
    if (body.error === "mfa_required") return { kind: "mfa_required" };
    if (body.error === "publishing_denied") return { kind: "denied", reason: body.reason ?? "" };
    return { kind: "service_error" };
  }
  if (response.status === 409) {
    let body: { error?: string; reasons?: PromotionReadinessReason[] } = {};
    try {
      body = (await response.json()) as { error?: string; reasons?: PromotionReadinessReason[] };
    } catch {
      // fall through to the generic service_error classification below
    }
    if (body.error === "not_ready") return { kind: "not_ready", reasons: body.reasons ?? [] };
    if (body.error === "version_conflict") return { kind: "version_conflict" };
    if (body.error === "duplicate_episode") return { kind: "duplicate_episode" };
    return { kind: "service_error" };
  }
  if (!response.ok) return { kind: "service_error" };

  const data = (await response.json()) as {
    outcome: "PROMOTED" | "ALREADY_PROMOTED";
    native_listing_id: string;
  };
  return { kind: "ok", outcome: data.outcome, nativeListingId: data.native_listing_id };
}
