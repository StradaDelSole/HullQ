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
//
// SLICE-0071 independent-review Finding B: this route's own identity is
// what makes every item it returns carry a SHORTLIST discovery token
// (`shortlistResolveServer.ts`) -- it is never a value the request body can
// choose. The plain-shortlist-page-vs-compare-page distinction that a
// removed `context` request field used to express is now expressed by
// which of these two purpose-bound route files was called; see the sibling
// `compare-resolve.ts` for the COMPARE counterpart.
export const prerender = false;

import type { APIContext } from "astro";

import { extractValidIds, jsonResponse, resolveListingsForSurface } from "../../../lib/shortlistResolveServer";

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
  const items = await resolveListingsForSurface(ids, "SHORTLIST", apiBaseUrl);
  return jsonResponse({ items }, 200);
}
