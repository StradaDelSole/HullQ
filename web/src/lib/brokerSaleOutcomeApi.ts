// SLICE-0074: the only module allowed to talk to FastAPI's broker
// sale/outcome close-out boundary. Astro never queries PostgreSQL directly
// and never reimplements revision/concurrency/lifecycle-atomicity semantics
// -- every result here is exactly what FastAPI decided, forwarded verbatim
// (mirrors `inventoryEditingApi.ts`'s identical discipline).
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie reaches FastAPI on this server-to-server call, and
// this module is also the CSRF proxy for the mutation: it always adds the
// fixed `X-HullQ-Requested-With: broker-sale-outcome-v1` header and forwards
// the browser's own `Origin` header value as Astro received it on the
// incoming page request -- never a substituted trusted value.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "broker-sale-outcome-v1";

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

function saleOutcomePath(organizationId: string, nativeListingId: string): string {
  return (
    `/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/inventory/${encodeURIComponent(nativeListingId)}/sale-outcome`
  );
}

// ---------------------------------------------------------------------------
// Read: current SaleOutcome
// ---------------------------------------------------------------------------

export interface SaleOutcomeDetail {
  native_listing_id: string;
  organization_id: string;
  lifecycle_state: string;
  current_sale_outcome_revision_id: string | null;
  outcome_kind: string | null;
  sold_date: string | null;
  achieved_amount: string | null;
  achieved_currency: string | null;
  originating_lead_id: string | null;
  recorded_at: string | null;
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

export type SaleOutcomeDetailResult =
  | AuthFailure
  | { kind: "service_error" }
  | { kind: "ok"; data: SaleOutcomeDetail };

export async function fetchSaleOutcome(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  cookieHeader: string | null,
): Promise<SaleOutcomeDetailResult> {
  const base = trimBase(apiBaseUrl);
  let response: Response;
  try {
    response = await fetch(`${base}${saleOutcomePath(organizationId, nativeListingId)}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as SaleOutcomeDetail;
  return { kind: "ok", data };
}

// ---------------------------------------------------------------------------
// Write: close as SOLD
// ---------------------------------------------------------------------------

/**
 * Classify a 403 response. FastAPI's `_close_as_sold_response`
 * (`hullq.api.app`) returns exactly one 403 body shape for this boundary --
 * `{"error":"mfa_required"}` -- plus the CSRF-rejection path, which this
 * module's own request construction always satisfies. Contract §8
 * authorization failures (missing/inactive membership, Account/
 * Organization mismatch, missing PUBLISHER role) are never a 403 here: they
 * collapse into the identical non-enumerating 404 `not_found` already
 * handled by the caller, never a reason-bearing "publishing denied" shape
 * (independent review, amendment Finding A). A 403 that fails to parse as
 * `mfa_required` here is therefore a genuine unexpected condition.
 */
async function classifyCloseAsSold403(
  response: Response,
): Promise<{ kind: "mfa_required" } | { kind: "service_error" }> {
  let body: { error?: string } = {};
  try {
    body = (await response.json()) as { error?: string };
  } catch {
    return { kind: "service_error" };
  }
  if (body.error === "mfa_required") return { kind: "mfa_required" };
  return { kind: "service_error" };
}

export interface CloseAsSoldRequest {
  revisionId: string;
  expectedCurrentSaleOutcomeRevisionId: string | null;
  soldDate: string | null;
  achievedAmount: string | null;
  achievedCurrency: string | null;
  originatingLeadId: string | null;
}

export type CloseAsSoldResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "draft_not_eligible" }
  | { kind: "invalid_payload" }
  | { kind: "invalid_lead" }
  | { kind: "stale_version"; currentSaleOutcomeRevisionId: string | null }
  | { kind: "service_error" }
  | { kind: "ok"; currentSaleOutcomeRevisionId: string; lifecycleState: string; transitionedToWithdrawn: boolean };

/** Record one SOLD outcome for one own NativeListing (contract §6/§9). */
export async function closeListingAsSold(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  request: CloseAsSoldRequest,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<CloseAsSoldResult> {
  const base = trimBase(apiBaseUrl);
  const body = {
    revision_id: request.revisionId,
    expected_current_revision_id: request.expectedCurrentSaleOutcomeRevisionId,
    sold_date: request.soldDate,
    achieved_amount: request.achievedAmount,
    achieved_currency: request.achievedCurrency,
    originating_lead_id: request.originatingLeadId,
  };
  let response: Response;
  try {
    response = await fetch(`${base}${saleOutcomePath(organizationId, nativeListingId)}`, {
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
  if (response.status === 403) return await classifyCloseAsSold403(response);
  if (response.status === 422) return { kind: "invalid_lead" };
  if (response.status === 409) {
    const data = (await response.json()) as {
      error?: string;
      current_sale_outcome_revision_id?: string;
    };
    if (data.error === "draft_not_eligible") return { kind: "draft_not_eligible" };
    return {
      kind: "stale_version",
      currentSaleOutcomeRevisionId: data.current_sale_outcome_revision_id ?? null,
    };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as {
    current_sale_outcome_revision_id: string;
    lifecycle_state: string;
    transitioned_to_withdrawn: boolean;
  };
  return {
    kind: "ok",
    currentSaleOutcomeRevisionId: data.current_sale_outcome_revision_id,
    lifecycleState: data.lifecycle_state,
    transitionedToWithdrawn: data.transitioned_to_withdrawn,
  };
}
