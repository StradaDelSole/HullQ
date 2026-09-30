// SLICE-0058/SLICE-0071: shared server-only logic behind
// `pages/api/shortlist/resolve.ts` (SHORTLIST) and
// `pages/api/shortlist/compare-resolve.ts` (COMPARE) -- factored out so
// both purpose-bound routes share the identical bounded-input-validation
// and per-id resolution behavior, differing only in which fixed
// `DiscoverySurface` each route's own identity mints (independent-review
// Finding B: the surface is never a request parameter, only which route
// was called).
import { mintDiscoverySurfaceToken, type DiscoverySurface } from "./discoverySurfaceSigning.ts";
import { fetchPublicListingForShortlist } from "./publicListingApi.ts";

/** Mirrors `shortlistStore.ts`'s own technical safety caps (contract §3). */
export const MAX_IDS_PER_REQUEST = 200;
export const MAX_ID_LENGTH = 200;

export const SHORTLIST_RESOLVE_RESPONSE_HEADERS = {
  "content-type": "application/json",
  "x-robots-tag": "noindex",
  "cache-control": "private, no-store",
};

export function jsonResponse(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), { status, headers: SHORTLIST_RESOLVE_RESPONSE_HEADERS });
}

/**
 * Validates the untrusted request body into a bounded, de-duplicated,
 * order-preserving list of candidate ids, or `null` if the shape is not
 * even well-formed (contract §13: "invalid/tampered ID collection -> bounded
 * invalid/recovery behavior, never server error from unchecked input").
 */
export function extractValidIds(body: unknown): string[] | null {
  if (typeof body !== "object" || body === null || Array.isArray(body)) return null;
  const raw = (body as Record<string, unknown>).listing_ids;
  if (!Array.isArray(raw) || raw.length > MAX_IDS_PER_REQUEST) return null;

  const seen = new Set<string>();
  const ids: string[] = [];
  for (const item of raw) {
    if (typeof item !== "string" || item.length === 0 || item.length > MAX_ID_LENGTH) {
      return null;
    }
    if (seen.has(item)) continue;
    seen.add(item);
    ids.push(item);
  }
  return ids;
}

export type ResolvedShortlistItem =
  | { native_listing_id: string; state: "available"; data: unknown }
  | { native_listing_id: string; state: "unavailable" }
  | { native_listing_id: string; state: "service_error" };

/**
 * Resolve *ids* against FastAPI's public listing route and mint a
 * *fixedSurface* discovery token (bound to each item's own
 * `native_listing_id`) for every available item. *fixedSurface* is always
 * a literal the caller (one specific route file) hardcodes -- never a
 * value taken from the request.
 *
 * Finding D: `mintDiscoverySurfaceToken` fails closed to `undefined` when
 * the shared signing secret is unavailable/malformed -- `JSON.stringify`
 * drops an `undefined`-valued property entirely, so an available item's
 * `data` simply carries no `discovery_token` field at all in that case
 * (the eventual contact submission resolves to UNKNOWN). Shortlist/compare
 * resolution itself never fails because discovery signing is unavailable.
 */
export async function resolveListingsForSurface(
  ids: string[],
  fixedSurface: DiscoverySurface,
  apiBaseUrl: string,
): Promise<ResolvedShortlistItem[]> {
  return Promise.all(
    ids.map(async (nativeListingId): Promise<ResolvedShortlistItem> => {
      const result = await fetchPublicListingForShortlist(apiBaseUrl, nativeListingId);
      if (result.kind === "available") {
        return {
          native_listing_id: nativeListingId,
          state: "available",
          data: { ...result.data, discovery_token: mintDiscoverySurfaceToken(fixedSurface, nativeListingId) },
        };
      }
      if (result.kind === "unavailable") {
        return { native_listing_id: nativeListingId, state: "unavailable" };
      }
      return { native_listing_id: nativeListingId, state: "service_error" };
    }),
  );
}
