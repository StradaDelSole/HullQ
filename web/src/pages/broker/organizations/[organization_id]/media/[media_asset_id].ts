// SLICE-0068: same-origin broker-workspace image proxy. A browser `<img
// src>` tag pointing directly at FastAPI's host would not reliably carry the
// SameSite=Lax host-only session cookie on a cross-site subresource request
// (only a top-level navigation gets that treatment) -- so this route lets
// Astro's own server make the authenticated, cookie-forwarding call to
// FastAPI (`fetchMediaAssetBytes`, mirrors every other `*Api.ts` module's
// identical server-to-server pattern) and stream the bytes back same-origin.
//
// This is the private broker preview surface only (contract §13): it serves
// exactly what the authenticated Organization is allowed to see of its own
// asset, never a public/indexable image URL.
export const prerender = false;

import type { APIContext } from "astro";

import { fetchMediaAssetBytes } from "../../../../../lib/mediaGalleryApi";

const NOT_FOUND_HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

export async function GET({ params, request }: APIContext): Promise<Response> {
  const organizationId = params.organization_id;
  const mediaAssetId = params.media_asset_id;
  if (!organizationId || !mediaAssetId) {
    return new Response(null, { status: 404, headers: NOT_FOUND_HEADERS });
  }

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const cookieHeader = request.headers.get("cookie");
  const result = await fetchMediaAssetBytes(apiBaseUrl, organizationId, mediaAssetId, cookieHeader);

  if (result.kind !== "ok") {
    const status =
      result.kind === "unauthenticated" ? 401 : result.kind === "not_found" ? 404 : result.kind === "mfa_required" || result.kind === "role_required" ? 403 : 502;
    return new Response(null, { status, headers: NOT_FOUND_HEADERS });
  }

  return new Response(result.data, {
    status: 200,
    headers: {
      "Content-Type": result.contentType,
      "Cache-Control": "private, no-store",
      "X-Robots-Tag": "noindex",
    },
  });
}
