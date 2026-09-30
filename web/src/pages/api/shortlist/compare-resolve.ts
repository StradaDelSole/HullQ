// SLICE-0071 independent-review Finding B: the COMPARE counterpart to
// `resolve.ts` -- identical bounded-input validation and per-id resolution,
// differing only in that *this route's own identity* mints COMPARE
// discovery tokens rather than SHORTLIST. See `resolve.ts`'s module
// docstring and `shortlistResolveServer.ts` for the shared rationale: the
// surface is never a client-suppliable value, only a function of which of
// these two purpose-bound files was called.
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

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const items = await resolveListingsForSurface(ids, "COMPARE", apiBaseUrl);
  return jsonResponse({ items }, 200);
}
