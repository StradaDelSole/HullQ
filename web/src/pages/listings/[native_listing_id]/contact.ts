// SLICE-0070: same-origin JSON proxy for the anonymous-capable buyer
// contact / Lead creation route. Mirrors `broker/.../media/upload.ts`'s
// same-origin-proxy rationale: the browser calls *this* Astro route (same
// host as the public listing page), never FastAPI's host directly, so no
// CORSMiddleware is needed on FastAPI -- this server-to-server call forwards
// the browser's own `Origin`/`Cookie` headers unmodified, exactly like
// `mediaGalleryApi.ts`'s gallery proxy does for broker-write channels.
//
// Unlike the media-upload stream proxy, the buyer contact payload is small
// and bounded (`MAX_BUYER_LEAD_BODY_BYTES`), so this route buffers it as
// JSON via `Astro.request.json()`-equivalent rather than streaming.
//
// The optional `Cookie` header is forwarded so an already-logged-in buyer's
// session is still readable by FastAPI for AccountId attribution (contract
// §3) -- but a session is never required: an anonymous request with no
// `Cookie` header proceeds identically.
export const prerender = false;

import type { APIContext } from "astro";

import {
  BUYER_LEAD_CSRF_HEADER_NAME,
  BUYER_LEAD_CSRF_HEADER_VALUE,
  MAX_BUYER_LEAD_BODY_BYTES,
} from "../../../lib/buyerLeadApi.ts";

// Public buyer-facing surface, not a private broker workspace: mirrors the
// public listing page's own `X-Robots-Tag: noindex` convention (this is a
// mutation response, never cached either way).
const RESPONSE_HEADERS = { "X-Robots-Tag": "noindex" };

function jsonError(error: string, status: number): Response {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "Content-Type": "application/json", ...RESPONSE_HEADERS },
  });
}

export async function POST({ params, request }: APIContext): Promise<Response> {
  const nativeListingId = params.native_listing_id;
  if (!nativeListingId) {
    return new Response(null, { status: 404, headers: RESPONSE_HEADERS });
  }

  // Mirrors FastAPI's own identical Content-Length check (contract §9):
  // read only the header, never the body, before deciding whether this
  // request is even worth forwarding.
  const rawContentLength = request.headers.get("content-length");
  if (rawContentLength === null) {
    return jsonError("length_required", 411);
  }
  const contentLength = Number.parseInt(rawContentLength, 10);
  if (!Number.isFinite(contentLength) || contentLength < 0) {
    return jsonError("invalid_content_length", 400);
  }
  if (contentLength > MAX_BUYER_LEAD_BODY_BYTES) {
    return jsonError("payload_too_large", 413);
  }

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const upstreamUrl =
    `${apiBaseUrl.replace(/\/+$/, "")}/api/listings/${encodeURIComponent(nativeListingId)}/contact`;

  const cookieHeader = request.headers.get("cookie");
  const originHeader = request.headers.get("origin");

  const upstreamHeaders: Record<string, string> = {
    "Content-Type": "application/json",
    "Content-Length": rawContentLength,
    [BUYER_LEAD_CSRF_HEADER_NAME]: BUYER_LEAD_CSRF_HEADER_VALUE,
  };
  if (cookieHeader) upstreamHeaders.Cookie = cookieHeader;
  if (originHeader) upstreamHeaders.Origin = originHeader;

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
      ...RESPONSE_HEADERS,
    },
  });
}
