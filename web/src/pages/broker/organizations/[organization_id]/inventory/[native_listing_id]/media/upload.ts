// SLICE-0068 independent review Finding D: a same-origin *streaming* proxy
// for exactly one image upload.
//
// The page's previous upload path (`Astro.request.formData()` in
// `media.astro`, calling `mediaGalleryApi.ts`'s `uploadListingImage()`
// helper) buffered the *entire* multipart body -- and then the whole file a
// second time via `file.arrayBuffer()` -- into memory before FastAPI's
// `Content-Length` bound was ever consulted. That is exactly the resource-
// abuse gap contract §11 warns against ("should avoid proxying large media
// bodies through Astro"): an attacker could exhaust the Astro/Node process's
// memory with a single request, long before FastAPI's own bound applied.
//
// This route instead forwards the incoming request's raw body straight
// through as a `ReadableStream` (`body: request.body`, `duplex: "half"` --
// required by Node 18+/undici whenever a stream is passed as a fetch body)
// to FastAPI's existing bounded
// `/api/broker/organizations/{id}/inventory/{id}/media/images` route.
// Neither Astro nor Node ever materializes the full byte array: the browser
// streams directly from the selected `File` object (see the inline upload
// script in `media.astro`), Node's HTTP server hands this route a live
// stream, and this handler passes that same stream on to `fetch` without
// calling `.text()`/`.json()`/`.formData()`/`.arrayBuffer()` anywhere.
//
// This intentionally does not go through `mediaGalleryApi.ts`'s normal
// JSON-body helper pattern (that module's own docstring calls it "the only
// module allowed to talk to FastAPI's... boundary") -- a raw stream proxy
// cannot be expressed through that helper's `Uint8Array`/`JSON.stringify`
// call shapes without re-buffering the body, which is exactly what this
// route exists to avoid. It reuses that module's exported constants
// (`MAX_IMAGE_UPLOAD_BYTES`, the fixed CSRF header name/value) so the two
// files cannot silently drift apart, and it preserves the identical
// Cookie-forwarding / exact-Origin + fixed-header CSRF discipline every
// other broker-write channel uses.
//
// Same-origin only, deliberately: the browser calls *this* Astro route
// (same host as the page, so the SLICE-0053 host-only session cookie is
// attached normally), never FastAPI's host directly -- introducing
// `CORSMiddleware` on FastAPI to allow a direct browser-to-FastAPI upload
// would widen that hardened same-hostname trust boundary for no benefit,
// since Astro can stream the body through without buffering it anyway.
export const prerender = false;

import type { APIContext } from "astro";

import {
  MAX_IMAGE_UPLOAD_BYTES,
  MEDIA_GALLERY_CSRF_HEADER_NAME,
  MEDIA_GALLERY_CSRF_HEADER_VALUE,
} from "../../../../../../../lib/mediaGalleryApi.ts";

const PRIVATE_HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

function jsonError(error: string, status: number): Response {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "Content-Type": "application/json", ...PRIVATE_HEADERS },
  });
}

export async function POST({ params, request }: APIContext): Promise<Response> {
  const organizationId = params.organization_id;
  const nativeListingId = params.native_listing_id;
  if (!organizationId || !nativeListingId) {
    return new Response(null, { status: 404, headers: PRIVATE_HEADERS });
  }

  // Mirrors FastAPI's own identical Content-Length check (contract §6.1):
  // read only the header, never the body, before deciding whether this
  // upload is even worth streaming onward.
  const rawContentLength = request.headers.get("content-length");
  if (rawContentLength === null) {
    return jsonError("length_required", 411);
  }
  const contentLength = Number.parseInt(rawContentLength, 10);
  if (!Number.isFinite(contentLength) || contentLength < 0) {
    return jsonError("invalid_content_length", 400);
  }
  if (contentLength > MAX_IMAGE_UPLOAD_BYTES) {
    return jsonError("payload_too_large", 413);
  }
  if (request.body === null) {
    return jsonError("invalid_content_length", 400);
  }

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const upstreamUrl =
    `${apiBaseUrl.replace(/\/+$/, "")}/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/inventory/${encodeURIComponent(nativeListingId)}/media/images`;

  const cookieHeader = request.headers.get("cookie");
  const originHeader = request.headers.get("origin");
  const rightsConfirmedHeader = request.headers.get("x-hullq-rights-confirmed");
  const sourceReferenceHeader = request.headers.get("x-hullq-source-reference");

  const upstreamHeaders: Record<string, string> = {
    "Content-Type": request.headers.get("content-type") ?? "application/octet-stream",
    "Content-Length": rawContentLength,
    [MEDIA_GALLERY_CSRF_HEADER_NAME]: MEDIA_GALLERY_CSRF_HEADER_VALUE,
    "X-HullQ-Rights-Confirmed": rightsConfirmedHeader === "true" ? "true" : "false",
  };
  if (cookieHeader) upstreamHeaders.Cookie = cookieHeader;
  if (originHeader) upstreamHeaders.Origin = originHeader;
  if (sourceReferenceHeader) upstreamHeaders["X-HullQ-Source-Reference"] = sourceReferenceHeader;

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers: upstreamHeaders,
      body: request.body,
      redirect: "manual",
      // Required by Node 18+/undici whenever a stream is passed as `body`.
      duplex: "half",
    } as RequestInit & { duplex: "half" });
  } catch {
    return jsonError("service_error", 502);
  }

  const upstreamBody = await upstream.arrayBuffer();
  return new Response(upstreamBody, {
    status: upstream.status,
    headers: {
      "Content-Type": upstream.headers.get("content-type") ?? "application/json",
      ...PRIVATE_HEADERS,
    },
  });
}
