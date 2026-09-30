// SLICE-0058: the only module the browser uses to re-resolve current
// listing truth for saved shortlist ids. Calls the same-origin Astro proxy
// (`web/src/pages/api/shortlist/resolve.ts`) rather than FastAPI directly,
// so the browser never needs to know FastAPI's base URL and no CORS grant
// is required (specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md §10).
//
// `{kind: "service_error"}` is reserved for a genuine transport-level
// failure of this request itself (network failure, non-2xx from the proxy,
// an unparsable/malformed response body) -- distinct from any individual
// saved id resolving to `"unavailable"`, which is an ordinary accepted
// per-listing outcome (Required Behavior §G: a service failure must never
// be presented as normal listing-state truth).
import type { PublicListingData } from "./publicListingApi";

export interface ShortlistItemAvailable {
  native_listing_id: string;
  state: "available";
  data: PublicListingData;
}

export interface ShortlistItemUnavailable {
  native_listing_id: string;
  state: "unavailable";
}

export interface ShortlistItemServiceError {
  native_listing_id: string;
  state: "service_error";
}

export type ShortlistItemResult =
  | ShortlistItemAvailable
  | ShortlistItemUnavailable
  | ShortlistItemServiceError;

export type ShortlistResolution =
  | { kind: "loaded"; items: ShortlistItemResult[] }
  | { kind: "service_error" };

function isValidItem(value: unknown): value is ShortlistItemResult {
  if (typeof value !== "object" || value === null) return false;
  const candidate = value as Record<string, unknown>;
  if (typeof candidate.native_listing_id !== "string") return false;
  if (candidate.state === "unavailable" || candidate.state === "service_error") return true;
  return candidate.state === "available" && typeof candidate.data === "object" && candidate.data !== null;
}

function isValidPayload(value: unknown): value is { items: ShortlistItemResult[] } {
  if (typeof value !== "object" || value === null) return false;
  const items = (value as Record<string, unknown>).items;
  return Array.isArray(items) && items.every(isValidItem);
}

async function resolveViaEndpoint(endpoint: string, listingIds: string[]): Promise<ShortlistResolution> {
  if (listingIds.length === 0) {
    return { kind: "loaded", items: [] };
  }

  let response: Response;
  try {
    response = await fetch(endpoint, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ listing_ids: listingIds }),
    });
  } catch {
    return { kind: "service_error" };
  }
  if (!response.ok) {
    return { kind: "service_error" };
  }

  let payload: unknown;
  try {
    payload = await response.json();
  } catch {
    return { kind: "service_error" };
  }
  if (!isValidPayload(payload)) {
    return { kind: "service_error" };
  }
  return { kind: "loaded", items: payload.items };
}

/**
 * Resolve *listingIds* (buyer-authored order, already de-duplicated by the
 * caller's local store) to their current public projections, via the
 * plain-shortlist-page proxy. An empty input short-circuits without a
 * network call -- an empty shortlist is not a service failure.
 *
 * SLICE-0071 independent-review Finding B: each resolved item carries a
 * SHORTLIST discovery token because *this specific proxy route*
 * (`pages/api/shortlist/resolve.ts`) always mints one -- never because this
 * function asked for one via a parameter. Use `resolveCompareListings`
 * (a different, COMPARE-only route) for the compare page.
 */
export function resolveShortlistListings(listingIds: string[]): Promise<ShortlistResolution> {
  return resolveViaEndpoint("/api/shortlist/resolve", listingIds);
}

/**
 * Identical to `resolveShortlistListings`, but calls the COMPARE-only proxy
 * route (`pages/api/shortlist/compare-resolve.ts`), which always mints
 * COMPARE discovery tokens instead of SHORTLIST.
 */
export function resolveCompareListings(listingIds: string[]): Promise<ShortlistResolution> {
  return resolveViaEndpoint("/api/shortlist/compare-resolve", listingIds);
}
