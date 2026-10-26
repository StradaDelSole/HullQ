// SLICE-0089: the only module allowed to talk to FastAPI's broker periodic
// performance report artifact boundary (download / historical periodic
// fetch). Astro never renders the report body itself and never re-derives
// counts -- the HTML returned here is exactly what FastAPI rendered.

export type ReportLocale = "en" | "de" | "fr" | "pt" | "es";

export const SUPPORTED_REPORT_LOCALES: readonly ReportLocale[] = ["en", "de", "fr", "pt", "es"];

export type ReportFetchResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "invalid_window" }
  | { kind: "service_error" }
  | { kind: "ok"; html: string };

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function statusToResult(status: number): ReportFetchResult | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  if (status === 403) return { kind: "mfa_required" };
  if (status === 400) return { kind: "invalid_window" };
  return null;
}

export async function fetchOrganizationReportDownload(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  options: { window?: string; locale?: ReportLocale },
): Promise<ReportFetchResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (options.window) params.set("window", options.window);
  if (options.locale) params.set("locale", options.locale);
  const query = params.toString() ? `?${params.toString()}` : "";
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/report/download${query}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const mapped = statusToResult(response.status);
  if (mapped) return mapped;
  if (!response.ok) return { kind: "service_error" };
  return { kind: "ok", html: await response.text() };
}

export async function fetchOrganizationPeriodicReport(
  apiBaseUrl: string,
  organizationId: string,
  periodRunId: string,
  cookieHeader: string | null,
  options: { locale?: ReportLocale },
): Promise<ReportFetchResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (options.locale) params.set("locale", options.locale);
  const query = params.toString() ? `?${params.toString()}` : "";
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/report/periodic/${encodeURIComponent(periodRunId)}${query}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const mapped = statusToResult(response.status);
  if (mapped) return mapped;
  if (!response.ok) return { kind: "service_error" };
  return { kind: "ok", html: await response.text() };
}
