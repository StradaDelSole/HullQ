// SLICE-0089: the authenticated, Organization-scoped periodic report
// subscription config boundary. Mirrors `brokerLeadOpsApi.ts`'s
// notification-config CSRF-proxy discipline exactly: this module is
// Astro's own server calling FastAPI server-to-server, so `originHeader`
// must be the *browser's own* `Origin` header as Astro received it,
// forwarded unmodified. The fixed header value here must always match
// `hullq.api.app._REPORT_SUBSCRIPTION_CSRF_HEADER_VALUE` exactly.

const REPORT_SUBSCRIPTION_CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const REPORT_SUBSCRIPTION_CSRF_HEADER_VALUE = "broker-report-subscription-v1";

export type ReportPeriodKind = "WEEKLY" | "MONTHLY";
export type ReportSubscriptionStatus = "ACTIVE" | "INACTIVE";

export interface ReportSubscriptionConfig {
  status: ReportSubscriptionStatus;
  period_kind: ReportPeriodKind;
  recipient_email: string | null;
  revision: number;
}

export type ReportSubscriptionResult =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "role_required" }
  | { kind: "invalid_input" }
  | { kind: "version_conflict"; data: ReportSubscriptionConfig }
  | { kind: "service_error" }
  | { kind: "ok"; data: ReportSubscriptionConfig };

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function csrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [REPORT_SUBSCRIPTION_CSRF_HEADER_NAME]: REPORT_SUBSCRIPTION_CSRF_HEADER_VALUE,
    "Content-Type": "application/json",
  };
}

function authFailureFromStatus(status: number): ReportSubscriptionResult | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  if (status === 403) return { kind: "mfa_required" };
  return null;
}

export async function fetchReportSubscription(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<ReportSubscriptionResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/report-subscription`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as ReportSubscriptionConfig;
  return { kind: "ok", data };
}

export async function setReportSubscription(
  apiBaseUrl: string,
  organizationId: string,
  input: {
    status: ReportSubscriptionStatus;
    periodKind: ReportPeriodKind;
    recipientEmail: string | null;
    expectedRevision: number;
  },
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ReportSubscriptionResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/report-subscription`,
      {
        method: "PUT",
        headers: { ...cookieHeaders(cookieHeader), ...csrfHeaders(originHeader) },
        body: JSON.stringify({
          status: input.status,
          period_kind: input.periodKind,
          recipient_email: input.recipientEmail,
          expected_revision: input.expectedRevision,
        }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 403) {
    const body = (await response.json().catch(() => ({}))) as { error?: string };
    return body.error === "role_required" ? { kind: "role_required" } : { kind: "mfa_required" };
  }
  if (response.status === 400) return { kind: "invalid_input" };
  if (response.status === 409) {
    const data = (await response.json()) as ReportSubscriptionConfig;
    return { kind: "version_conflict", data };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as ReportSubscriptionConfig;
  return { kind: "ok", data };
}
