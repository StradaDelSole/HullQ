// SLICE-0089: same-origin proxy for a historical periodic report artifact.
// Mirrors `../report.ts`'s identical same-origin-proxy rationale.
export const prerender = false;

import type { APIContext } from "astro";

import {
  fetchOrganizationPeriodicReport,
  SUPPORTED_REPORT_LOCALES,
  type ReportLocale,
} from "../../../../../../lib/brokerReportApi";

const PRIVATE_HEADERS = { "Cache-Control": "private, no-store", "X-Robots-Tag": "noindex" };

function statusForKind(kind: string): number {
  switch (kind) {
    case "unauthenticated":
      return 401;
    case "not_found":
      return 404;
    case "mfa_required":
      return 403;
    default:
      return 502;
  }
}

export async function GET({ params, request, url }: APIContext): Promise<Response> {
  const organizationId = params.organization_id;
  const periodRunId = params.period_run_id;
  if (!organizationId || !periodRunId) {
    return new Response(null, { status: 404, headers: PRIVATE_HEADERS });
  }

  const apiBaseUrl = process.env.HULLQ_API_BASE_URL ?? "http://127.0.0.1:8000";
  const cookieHeader = request.headers.get("cookie");
  const rawLocale = url.searchParams.get("locale");
  const locale: ReportLocale | undefined = SUPPORTED_REPORT_LOCALES.includes(
    rawLocale as ReportLocale,
  )
    ? (rawLocale as ReportLocale)
    : undefined;

  const result = await fetchOrganizationPeriodicReport(
    apiBaseUrl,
    organizationId,
    periodRunId,
    cookieHeader,
    { locale },
  );

  if (result.kind !== "ok") {
    return new Response(null, { status: statusForKind(result.kind), headers: PRIVATE_HEADERS });
  }

  const inline = url.searchParams.get("inline") === "1";
  const disposition = inline
    ? "inline"
    : `attachment; filename="hullq-performance-report-${organizationId}-${periodRunId}.html"`;

  return new Response(result.html, {
    status: 200,
    headers: {
      "Content-Type": "text/html; charset=utf-8",
      "Content-Disposition": disposition,
      ...PRIVATE_HEADERS,
    },
  });
}
