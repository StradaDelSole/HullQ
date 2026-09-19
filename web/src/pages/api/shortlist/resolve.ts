// SLICE-0058: bounded same-origin proxy that resolves buyer-supplied,
// untrusted candidate `NativeListingId` strings (read by the browser from
// its own local shortlist storage) against FastAPI's already-accepted
// public listing read boundary only
// (`specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md` §10).
//
// This route never becomes a second listing-truth layer: it does not touch
// PostgreSQL, does not evaluate lifecycle/freshness itself and does not
// accept caller-supplied listing truth -- each id is delegated verbatim to
// `fetchPublicListingForShortlist`, which calls the identical
// `GET /api/listings/{id}` route the single public listing page already
// uses. This module only validates/bounds/de-duplicates the untrusted input
// collection and aggregates the per-id results, preserving requested order
// (contract §10). It has no persistence side effect and creates no
// buyer-interest profile (contract §11) -- the ids are used for this one
// request and then forgotten.
export const prerender = false;

import type { APIContext } from "astro";

import { fetchPublicListingForShortlist } from "../../../lib/publicListingApi";

/** Mirrors `shortlistStore.ts`'s own technical safety caps (contract §3). */
const MAX_IDS_PER_REQUEST = 200;
const MAX_ID_LENGTH = 200;

const RESPONSE_HEADERS = {
  "content-type": "application/json",
  "x-robots-tag": "noindex",
  "cache-control": "private, no-store",
};

function jsonResponse(payload: unknown, status: number): Response {
  return new Response(JSON.stringify(payload), { status, headers: RESPONSE_HEADERS });
}

/**
 * Validates the untrusted request body into a bounded, de-duplicated,
 * order-preserving list of candidate ids, or `null` if the shape is not
 * even well-formed (contract §13: "invalid/tampered ID collection -> bounded
 * invalid/recovery behavior, never server error from unchecked input").
 */
function extractValidIds(body: unknown): string[] | null {
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

export async function POST({ request }: APIContext): Promise<Response> {
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: "invalid_request" }, 400);
  }

  const ids = extractValidIds(body);
  if (ids === null) {
    return jsonResponse({ error: "invalid_request" }, 400);
  }

  // `process.env`, not `import.meta.env`: matches every other server-side
  // FastAPI-base-URL read in this package (only known at server start time).
  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";

  const items = await Promise.all(
    ids.map(async (nativeListingId) => {
      const result = await fetchPublicListingForShortlist(apiBaseUrl, nativeListingId);
      if (result.kind === "available") {
        return { native_listing_id: nativeListingId, state: "available" as const, data: result.data };
      }
      if (result.kind === "unavailable") {
        return { native_listing_id: nativeListingId, state: "unavailable" as const };
      }
      return { native_listing_id: nativeListingId, state: "service_error" as const };
    }),
  );

  return jsonResponse({ items }, 200);
}
