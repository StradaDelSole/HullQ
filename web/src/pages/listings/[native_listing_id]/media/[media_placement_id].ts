// SLICE-0069: same-origin public gallery image proxy. Routes the browser's
// `<img src>` request through Astro's own server to FastAPI's public,
// listing-scoped, fail-closed derivative route
// (`fetchPublicListingMediaBytes`, mirrors the SLICE-0068 broker-workspace
// media proxy's identical same-origin rationale) rather than pointing the
// public page directly at a separate API host.
//
// This route is itself public and non-enumerating: every rejection reason
// FastAPI's route can produce collapses to the identical bounded 404 here.
export const prerender = false;

import type { APIContext } from "astro";

import { fetchPublicListingMediaBytes } from "../../../../lib/publicListingApi";

const NOT_FOUND_HEADERS = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex" };

export async function GET({ params }: APIContext): Promise<Response> {
  const nativeListingId = params.native_listing_id;
  const mediaPlacementId = params.media_placement_id;
  if (!nativeListingId || !mediaPlacementId) {
    return new Response(null, { status: 404, headers: NOT_FOUND_HEADERS });
  }

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const result = await fetchPublicListingMediaBytes(apiBaseUrl, nativeListingId, mediaPlacementId);

  if (result.kind !== "ok") {
    return new Response(null, { status: result.kind === "not_found" ? 404 : 502, headers: NOT_FOUND_HEADERS });
  }

  return new Response(result.data, {
    status: 200,
    headers: {
      "Content-Type": result.contentType,
      // Public derivative bytes are immutable once served under a given
      // placement id (a revision always mints a new placement), so this is
      // safe to cache -- unlike the private broker-workspace proxy above.
      "Cache-Control": "public, max-age=3600",
    },
  });
}
