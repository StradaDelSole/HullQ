// SLICE-0078: same-origin proxy for broker logout. Mirrors
// `listings/[native_listing_id]/contact.ts`'s same-origin-proxy rationale:
// the browser calls this Astro route (same host as the Broker Workspace
// page), never FastAPI's host directly, so the browser's plain `<form>`
// POST is never required to set a custom header itself -- this
// server-to-server call sets the fixed CSRF header FastAPI now requires
// (`hullq.api.app._require_logout_csrf`) and forwards the browser's own
// Cookie/Origin unmodified, then relays FastAPI's `Set-Cookie` (session
// deletion) back to the browser unmodified.
export const prerender = false;

import type { APIContext } from "astro";

import { logoutFromBroker } from "../../lib/brokerApi.ts";

const RESPONSE_HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

export async function POST({ request, redirect }: APIContext): Promise<Response> {
  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const cookieHeader = request.headers.get("cookie");
  const originHeader = request.headers.get("origin");

  let upstream: Response;
  try {
    upstream = await logoutFromBroker(apiBaseUrl, cookieHeader, originHeader);
  } catch {
    return new Response(null, { status: 502, headers: RESPONSE_HEADERS });
  }

  const response = redirect("/broker", 303);
  const setCookie = upstream.headers.get("set-cookie");
  if (setCookie) {
    response.headers.set("set-cookie", setCookie);
  }
  for (const [key, value] of Object.entries(RESPONSE_HEADERS)) {
    response.headers.set(key, value);
  }
  return response;
}
