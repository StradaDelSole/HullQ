// SLICE-0075: the only module allowed to talk to FastAPI's broker
// performance/funnel snapshot read boundary. Astro never queries PostgreSQL
// directly and never re-derives counts/latency/source-attribution in
// TypeScript -- every value here is exactly what FastAPI decided, forwarded
// verbatim (mirrors `brokerSaleOutcomeApi.ts`'s identical discipline).
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie reaches FastAPI on this server-to-server,
// read-only call. No CSRF header is needed here: this boundary never
// mutates anything.

export type PerformanceWindow = "LAST_7_DAYS" | "LAST_30_DAYS" | "LAST_90_DAYS" | "ALL_TIME";

export interface ListingPerformance {
  native_listing_id: string;
  public_listing_views: number;
  leads_received: number;
  leads_contacted: number;
  leads_closed: number;
  first_contact_latency_known_count: number;
  first_contact_latency_unknown_count: number;
  sold_outcome_recorded_at: string | null;
  sold_outcome_source_known: boolean | null;
}

export interface OrganizationPerformanceSnapshot {
  window: PerformanceWindow;
  window_start: string;
  window_end: string;
  public_listing_views: number;
  leads_received: number;
  leads_contacted: number;
  leads_closed: number;
  sold_outcomes: number;
  sold_outcomes_with_known_source: number;
  sold_outcomes_with_unknown_source: number;
  // Two mechanically independent evidence dimensions (contract §8B) --
  // never collapsed into one source field, and never one inferred from the
  // other.
  acquisition_source_breakdown: Record<string, number>;
  discovery_source_breakdown: Record<string, number>;
  first_contact_latency_known_count: number;
  first_contact_latency_unknown_count: number;
  median_first_contact_latency_seconds: number | null;
  listings: ListingPerformance[];
}

export type OrganizationPerformanceResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "invalid_window" }
  | { kind: "service_error" }
  | { kind: "ok"; data: OrganizationPerformanceSnapshot };

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

/**
 * Fetch one Organization's bounded performance/funnel snapshot for *window*
 * (or FastAPI's own accepted default when omitted). `not_found` covers both
 * a genuinely unknown Organization and one the current Account is not an
 * authorized member of (contract §10 non-enumeration).
 */
export async function fetchOrganizationPerformance(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  window?: PerformanceWindow,
): Promise<OrganizationPerformanceResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const query = window ? `?window=${encodeURIComponent(window)}` : "";
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/performance${query}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 403) return { kind: "mfa_required" };
  if (response.status === 400) return { kind: "invalid_window" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as OrganizationPerformanceSnapshot;
  return { kind: "ok", data };
}
