// SLICE-0081 PR #327 review finding A: the four reused read clients
// (`brokerLeadOpsApi.ts`, `professionalDraftApi.ts`, `brokerApi.ts`'s
// inventory read, `brokerPerformanceApi.ts`) already catch a network
// `fetch()` failure and return their own typed `service_error`, but their
// success path still calls a bare `await response.json()` -- a 200 response
// with a malformed/truncated body, or a body-read failure, throws there
// instead of returning a typed result. Composing five such calls with a
// bare `Promise.all([...])` means one panel's bad body rejects the whole
// `Promise.all`, taking down every other already-authorized panel on the
// page -- exactly the HIGH_RISK invariant SLICE-0081 forbids ("a partial
// read-path outage is a section-specific unavailable result ... never
// erase healthy authorized panels").
//
// This module is the one place that composes the five calls, so each one
// gets its own bounded fail-closed `.catch()`: an unexpected rejection from
// any single call becomes that same call's existing `service_error` result
// (every one of the five result unions already has that variant), and
// never propagates to reject the overall `Promise.all`. This changes no
// shared API client contract and introduces no new result shape.
import {
  fetchOrganizationInventory,
  type OrganizationInventoryResult,
} from "./brokerApi.ts";
import { fetchOrganizationLeadCounts, fetchOrganizationLeadInbox } from "./brokerLeadOpsApi.ts";
import type { LeadCountsResult, LeadInboxResult } from "./brokerLeadOpsApi.ts";
import { fetchProfessionalDrafts } from "./professionalDraftApi.ts";
import type { ProfessionalDraftListResult } from "./professionalDraftApi.ts";
import { fetchOrganizationPerformance } from "./brokerPerformanceApi.ts";
import type { OrganizationPerformanceResult } from "./brokerPerformanceApi.ts";

export interface DashboardPanels {
  leadCounts: LeadCountsResult;
  leadInbox: LeadInboxResult;
  drafts: ProfessionalDraftListResult;
  inventory: OrganizationInventoryResult;
  performance: OrganizationPerformanceResult;
}

/**
 * Resolve a single panel call to its typed result, converting any
 * unexpected rejection (bad JSON, a body-read failure, or anything else
 * that isn't already handled inside the client itself) into that same
 * panel's own `service_error` outcome -- never a rejection that could take
 * down a sibling panel composed alongside it.
 */
function toPanelResult<T extends { kind: string }>(promise: Promise<T>): Promise<T> {
  return promise.catch(() => ({ kind: "service_error" }) as T);
}

/**
 * Fetch all five Organization-scoped dashboard panels independently and
 * concurrently. Every one of the five calls below is wrapped by
 * `toPanelResult` individually -- the returned `Promise.all` therefore only
 * ever resolves, never rejects, regardless of how many (zero to five) of
 * the underlying calls individually fail.
 */
export async function fetchDashboardPanels(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<DashboardPanels> {
  const [leadCounts, leadInbox, drafts, inventory, performance] = await Promise.all([
    toPanelResult(fetchOrganizationLeadCounts(apiBaseUrl, organizationId, cookieHeader)),
    toPanelResult(fetchOrganizationLeadInbox(apiBaseUrl, organizationId, cookieHeader, { pageSize: 5 })),
    toPanelResult(fetchProfessionalDrafts(apiBaseUrl, organizationId, cookieHeader, { pageSize: 5 })),
    toPanelResult(fetchOrganizationInventory(apiBaseUrl, organizationId, cookieHeader, { pageSize: 5 })),
    toPanelResult(fetchOrganizationPerformance(apiBaseUrl, organizationId, cookieHeader, "LAST_30_DAYS")),
  ]);
  return { leadCounts, leadInbox, drafts, inventory, performance };
}
