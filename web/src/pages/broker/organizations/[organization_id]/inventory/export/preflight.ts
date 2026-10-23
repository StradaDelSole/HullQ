// SLICE-0088: same-origin proxy for the broker inventory export preflight.
// The browser calls this Astro route (same host as the page), never
// FastAPI's host directly -- mirrors `imports/upload.ts`'s identical
// same-origin-proxy rationale.
export const prerender = false;

import type { APIContext } from "astro";
import { fetchExportPreflight, type ExportSelection, type NautixExportProfile } from "../../../../../../lib/brokerInventoryExportApi";

const PRIVATE_HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

function jsonError(error: string, status: number): Response {
  return new Response(JSON.stringify({ error }), {
    status,
    headers: { "Content-Type": "application/json", ...PRIVATE_HEADERS },
  });
}

function statusForKind(kind: string): number {
  switch (kind) {
    case "unauthenticated":
      return 401;
    case "not_found":
      return 404;
    case "mfa_required":
    case "publisher_role_required":
      return 403;
    case "export_busy":
      return 429;
    case "empty_selection":
    case "oversize_selection":
    case "unknown_item":
    case "invalid_selection":
    case "invalid_nautix_profile":
      return 400;
    default:
      return 502;
  }
}

export async function POST({ params, request }: APIContext): Promise<Response> {
  const organizationId = params.organization_id;
  if (!organizationId) {
    return new Response(null, { status: 404, headers: PRIVATE_HEADERS });
  }

  let raw: Record<string, unknown>;
  try {
    raw = await request.json();
  } catch {
    return jsonError("invalid_selection", 400);
  }
  const draftIds = raw.draft_ids;
  const nativeListingIds = raw.native_listing_ids;
  if (!Array.isArray(draftIds) || !Array.isArray(nativeListingIds)) {
    return jsonError("invalid_selection", 400);
  }
  const selection: ExportSelection = { draftIds, nativeListingIds };
  let nautixProfile: NautixExportProfile | undefined;
  const rawProfile = raw.nautix_profile as Record<string, unknown> | undefined;
  if (rawProfile) {
    nautixProfile = {
      accountToken: String(rawProfile.account_token ?? ""),
      officeId: String(rawProfile.office_id ?? ""),
      saleClasses: (rawProfile.sale_classes as Record<string, string>) ?? {},
    };
  }

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const cookieHeader = request.headers.get("cookie");
  const originHeader = request.headers.get("origin");

  const result = await fetchExportPreflight(
    apiBaseUrl,
    organizationId,
    cookieHeader,
    originHeader,
    selection,
    nautixProfile,
  );

  if (result.kind !== "ok") {
    return jsonError(result.kind, statusForKind(result.kind));
  }
  return new Response(
    JSON.stringify({ snapshot_fingerprint: result.snapshotFingerprint, rows: result.rows }),
    { status: 200, headers: { "Content-Type": "application/json", ...PRIVATE_HEADERS } },
  );
}
