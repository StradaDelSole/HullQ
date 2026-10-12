// SLICE-0083: same-origin streaming proxy for one broker inventory import
// file upload, mirroring `inventory/[native_listing_id]/media/upload.ts`'s
// identical rationale (independent review Finding D on that route): the
// browser streams its selected `File` straight through this route's own
// `request.body` to FastAPI's bounded import route, so neither Astro/Node
// nor this handler ever buffers the whole upload into memory.
//
// Same-origin only: the browser calls this Astro route (same host as the
// page), never FastAPI's host directly.
export const prerender = false;

import type { APIContext } from "astro";

const MAX_IMPORT_FILE_BYTES = 20_000_000;
const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "broker-import-intake-v1";

const PRIVATE_HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

function jsonError(error: string, status: number): Response {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "Content-Type": "application/json", ...PRIVATE_HEADERS },
  });
}

export async function POST({ params, request }: APIContext): Promise<Response> {
  const organizationId = params.organization_id;
  if (!organizationId) {
    return new Response(null, { status: 404, headers: PRIVATE_HEADERS });
  }

  const rawContentLength = request.headers.get("content-length");
  if (rawContentLength === null) return jsonError("length_required", 411);
  const contentLength = Number.parseInt(rawContentLength, 10);
  if (!Number.isFinite(contentLength) || contentLength < 0) {
    return jsonError("invalid_content_length", 400);
  }
  if (contentLength > MAX_IMPORT_FILE_BYTES) return jsonError("payload_too_large", 413);
  if (request.body === null) return jsonError("invalid_content_length", 400);

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const upstreamUrl =
    `${apiBaseUrl.replace(/\/+$/, "")}/api/broker/organizations/${encodeURIComponent(organizationId)}/imports`;

  const cookieHeader = request.headers.get("cookie");
  const originHeader = request.headers.get("origin");
  const declaredFormat = request.headers.get("x-hullq-import-format");
  const importSource = request.headers.get("x-hullq-import-source");
  const worksheetName = request.headers.get("x-hullq-worksheet");
  const nautixTokens = request.headers.get("x-hullq-nautix-account-tokens");
  if (!declaredFormat || !importSource) {
    return jsonError("invalid_request", 400);
  }

  const upstreamHeaders: Record<string, string> = {
    "Content-Type": "application/octet-stream",
    "Content-Length": rawContentLength,
    [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE,
    "X-HullQ-Import-Format": declaredFormat,
    "X-HullQ-Import-Source": importSource,
  };
  if (cookieHeader) upstreamHeaders.Cookie = cookieHeader;
  if (originHeader) upstreamHeaders.Origin = originHeader;
  if (worksheetName) upstreamHeaders["X-HullQ-Worksheet"] = worksheetName;
  if (nautixTokens) upstreamHeaders["X-HullQ-Nautix-Account-Tokens"] = nautixTokens;

  let upstream: Response;
  try {
    upstream = await fetch(upstreamUrl, {
      method: "POST",
      headers: upstreamHeaders,
      body: request.body,
      redirect: "manual",
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
