// SLICE-0071: the authenticated, Organization-scoped broker Lead operations
// + notification-recipient configuration boundary. Every fact/result here is
// exactly what FastAPI decided (`hullq.application.lead_operations`,
// `hullq.api.app`) -- this module never infers tenancy, operational status,
// concurrency conflicts or role authorization on its own.
//
// Also the CSRF proxy for every mutation below (mirrors
// `brokerApi.ts`'s `lifecycleCsrfHeaders` rationale): this module is Astro's
// own server calling FastAPI server-to-server, so `originHeader` must be the
// *browser's own* `Origin` header value as Astro received it on the incoming
// page request, forwarded unmodified. The fixed `X-HullQ-Requested-With`
// header value here must always match
// `hullq.api.app._BROKER_LEAD_OPS_CSRF_HEADER_VALUE` exactly.

const LEAD_OPS_CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const LEAD_OPS_CSRF_HEADER_VALUE = "broker-lead-operations-v1";

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function csrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [LEAD_OPS_CSRF_HEADER_NAME]: LEAD_OPS_CSRF_HEADER_VALUE,
    "Content-Type": "application/json",
  };
}

export interface LeadOperationalState {
  operational_status: "NEW" | "IN_PROGRESS" | "WAITING_FOR_BUYER" | "CLOSED";
  is_unread: boolean;
  assigned_account_id: string | null;
  follow_up_due_at: string | null;
  close_reason: string | null;
  version: number;
}

export interface LeadInboxItem {
  lead_id: string;
  native_listing_id: string;
  buyer_name: string;
  buyer_email: string;
  contact_email_verification_state: string;
  received_at: string;
  source_channel: string;
  operational_state: LeadOperationalState;
}

export interface LeadTimelineEvent {
  event_id: string;
  event_type: string;
  actor_account_id: string;
  occurred_at: string;
  note_text: string | null;
  contact_channel: string | null;
  close_reason: string | null;
}

export interface LeadDetail {
  lead_id: string;
  native_listing_id: string;
  publishing_organization_id: string;
  buyer_name: string;
  buyer_email: string;
  contact_email_verification_state: string;
  buyer_message: string;
  source_channel: string;
  received_at: string;
  operational_state: LeadOperationalState;
  notification_delivery: { status: string; attempt_count: number; delivered_at: string | null } | null;
  acquisition_provenance: {
    acquisition_channel: string;
    utm_source: string | null;
    utm_medium: string | null;
    utm_campaign: string | null;
    utm_term: string | null;
    utm_content: string | null;
    discovery_surface: string;
  } | null;
  timeline: LeadTimelineEvent[];
}

export interface LeadOrganizationCounts {
  new_unread: number;
  unassigned: number;
  follow_up_due: number;
  follow_up_overdue: number;
}

// SLICE-0077: current-ACTIVE-member candidates for the Lead assignment
// picker. `label` is presentation-only; the browser always submits
// `account_id` as the assignment value.
export interface LeadAssignmentCandidate {
  account_id: string;
  roles: string[];
  label: string;
}

/** Shared org-level tenancy/auth outcomes carried by every read/mutation below. */
type AuthFailure = { kind: "unauthenticated" } | { kind: "not_found" } | { kind: "mfa_required" };

function authFailureFromStatus(status: number): AuthFailure | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  if (status === 403) return { kind: "mfa_required" };
  return null;
}

export type LeadInboxResult =
  | AuthFailure
  | { kind: "invalid_page_size" }
  | { kind: "invalid_cursor" }
  | { kind: "invalid_input" }
  | { kind: "service_error" }
  | { kind: "ok"; data: { items: LeadInboxItem[]; next_cursor?: string } };

export interface LeadInboxFilterOptions {
  cursor?: string;
  pageSize?: number;
  status?: string;
  assigneeAccountId?: string;
  unreadOnly?: boolean;
  followUpDue?: boolean;
}

export async function fetchOrganizationLeadInbox(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  options?: LeadInboxFilterOptions,
): Promise<LeadInboxResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const params = new URLSearchParams();
  if (options?.cursor) params.set("cursor", options.cursor);
  if (options?.pageSize) params.set("page_size", String(options.pageSize));
  if (options?.status) params.set("status", options.status);
  if (options?.assigneeAccountId) params.set("assignee_account_id", options.assigneeAccountId);
  if (options?.unreadOnly) params.set("unread_only", "true");
  if (options?.followUpDue) params.set("follow_up_due", "true");
  const query = params.toString();
  const url =
    `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/leads` +
    (query ? `?${query}` : "");

  let response: Response;
  try {
    response = await fetch(url, { headers: cookieHeaders(cookieHeader), redirect: "manual" });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 400) {
    const body = (await response.json().catch(() => null)) as { error?: string } | null;
    if (body?.error === "invalid_cursor") return { kind: "invalid_cursor" };
    if (body?.error === "invalid_page_size") return { kind: "invalid_page_size" };
    return { kind: "invalid_input" };
  }
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { items: LeadInboxItem[]; next_cursor?: string };
  return { kind: "ok", data };
}

export type LeadCountsResult = AuthFailure | { kind: "service_error" } | { kind: "ok"; data: LeadOrganizationCounts };

export async function fetchOrganizationLeadCounts(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<LeadCountsResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/leads/counts`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as LeadOrganizationCounts;
  return { kind: "ok", data };
}

export type LeadAssignmentCandidatesResult =
  | AuthFailure
  | { kind: "service_error" }
  | { kind: "ok"; data: { candidates: LeadAssignmentCandidate[] } };

export async function fetchLeadAssignmentCandidates(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<LeadAssignmentCandidatesResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/leads/assignment-candidates`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { candidates: LeadAssignmentCandidate[] };
  return { kind: "ok", data };
}

export type LeadDetailResult =
  | { kind: "unauthenticated" }
  | { kind: "mfa_required" }
  | { kind: "lead_not_found" }
  | { kind: "service_error" }
  | { kind: "ok"; data: LeadDetail };

export async function fetchLeadDetail(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  cookieHeader: string | null,
): Promise<LeadDetailResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/leads/${encodeURIComponent(leadId)}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  // Contract §2: an unknown Organization/unauthorized membership and a
  // foreign-Organization Lead both surface as 404 -- FastAPI already
  // collapses them into the same shape, and so does this client (a caller
  // that already knows it's authorized for the Organization can treat 404
  // here as "lead not found").
  if (response.status === 404) return { kind: "lead_not_found" };
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 403) return { kind: "mfa_required" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as LeadDetail;
  return { kind: "ok", data };
}

export type LeadMutationResult =
  | AuthFailure
  | { kind: "lead_not_found" }
  | { kind: "invalid_input" }
  | { kind: "version_conflict" }
  | { kind: "assignee_not_active_member" }
  | { kind: "service_error" }
  | { kind: "ok"; data: { operational_state?: LeadOperationalState } };

async function postLeadMutation(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  action: string,
  body: Record<string, unknown> | undefined,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url =
    `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/leads/${encodeURIComponent(leadId)}/${action}`;
  let response: Response;
  try {
    response = await fetch(url, {
      method: "POST",
      headers: { ...cookieHeaders(cookieHeader), ...csrfHeaders(originHeader) },
      body: JSON.stringify(body ?? {}),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 404) return { kind: "lead_not_found" };
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 400) return { kind: "invalid_input" };
  if (response.status === 409) return { kind: "version_conflict" };
  if (response.status === 422) return { kind: "assignee_not_active_member" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { operational_state?: LeadOperationalState };
  return { kind: "ok", data };
}

export function markLeadRead(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(apiBaseUrl, organizationId, leadId, "read", undefined, cookieHeader, originHeader);
}

export function setLeadAssignment(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  assigneeAccountId: string | null,
  expectedVersion: number,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(
    apiBaseUrl,
    organizationId,
    leadId,
    "assignment",
    { assignee_account_id: assigneeAccountId, expected_version: expectedVersion },
    cookieHeader,
    originHeader,
  );
}

export function setLeadStatus(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  status: string,
  expectedVersion: number,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(
    apiBaseUrl,
    organizationId,
    leadId,
    "status",
    { status, expected_version: expectedVersion },
    cookieHeader,
    originHeader,
  );
}

export function closeLead(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  closeReason: string,
  expectedVersion: number,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(
    apiBaseUrl,
    organizationId,
    leadId,
    "close",
    { close_reason: closeReason, expected_version: expectedVersion },
    cookieHeader,
    originHeader,
  );
}

export function setLeadFollowUp(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  dueAtIso: string | null,
  expectedVersion: number,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(
    apiBaseUrl,
    organizationId,
    leadId,
    "follow-up",
    { due_at: dueAtIso, expected_version: expectedVersion },
    cookieHeader,
    originHeader,
  );
}

export function appendLeadNote(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  text: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(apiBaseUrl, organizationId, leadId, "notes", { text }, cookieHeader, originHeader);
}

export function appendLeadContactAttempt(
  apiBaseUrl: string,
  organizationId: string,
  leadId: string,
  channel: string,
  note: string | null,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<LeadMutationResult> {
  return postLeadMutation(
    apiBaseUrl,
    organizationId,
    leadId,
    "contact-attempts",
    { channel, note },
    cookieHeader,
    originHeader,
  );
}

// ---------------------------------------------------------------------------
// Notification-recipient configuration (contract §9) — OWNER/ADMIN-only write
// ---------------------------------------------------------------------------

export interface NotificationConfig {
  notification_email: string | null;
  version: number;
}

export type NotificationConfigResult =
  | AuthFailure
  | { kind: "role_required" }
  | { kind: "invalid_input" }
  | { kind: "version_conflict" }
  | { kind: "service_error" }
  | { kind: "ok"; data: NotificationConfig };

export async function fetchNotificationConfig(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<NotificationConfigResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/notification-config`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = authFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as NotificationConfig;
  return { kind: "ok", data };
}

export async function setNotificationConfig(
  apiBaseUrl: string,
  organizationId: string,
  notificationEmail: string | null,
  expectedVersion: number,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<NotificationConfigResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(
      `${base}/api/broker/organizations/${encodeURIComponent(organizationId)}/notification-config`,
      {
        method: "PUT",
        headers: { ...cookieHeaders(cookieHeader), ...csrfHeaders(originHeader) },
        body: JSON.stringify({ notification_email: notificationEmail, expected_version: expectedVersion }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 403) {
    const body = (await response.json().catch(() => null)) as { error?: string } | null;
    return body?.error === "role_required" ? { kind: "role_required" } : { kind: "mfa_required" };
  }
  if (response.status === 400) return { kind: "invalid_input" };
  if (response.status === 409) return { kind: "version_conflict" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as NotificationConfig;
  return { kind: "ok", data };
}
