// SLICE-0081: tiny pure presentation helpers for the Organization workspace
// operational dashboard. These functions only format facts FastAPI already
// decided -- they never decide readiness, lifecycle, tenancy or
// authorization themselves, and a denial/outage string here must never read
// like a successful empty/zero result (contract: "Must-never-change
// invariant" -- never translate a denied, expired-session, MFA or
// role-required result into a public/empty/zero metric).

/**
 * Text for one dashboard panel that could not be loaded. Every possible
 * non-"ok" `kind` from the four reused read clients (`brokerLeadOpsApi.ts`,
 * `professionalDraftApi.ts`, `brokerApi.ts`'s inventory read,
 * `brokerPerformanceApi.ts`) is covered by one of these distinct denial/
 * outage states; an unrecognized kind still falls through to the generic
 * outage wording rather than throwing or rendering nothing.
 */
export function panelUnavailableText(kind: string): string {
  switch (kind) {
    case "unauthenticated":
      return "Please log in again to view this section.";
    case "mfa_required":
      return "Additional verification is required to view this section.";
    case "publisher_role_required":
      return "Your current membership role does not include permission to view this section.";
    case "not_found":
      return "This section is not available for this Organization.";
    default:
      // invalid_cursor / invalid_window / invalid_page_size / invalid_input /
      // service_error / any unrecognized kind: a genuine outage, never
      // presented as "no activity".
      return "Temporarily unavailable. Please try again.";
  }
}

export interface InventoryReadinessItem {
  lifecycle_state: "DRAFT" | "ACTIVE" | "WITHDRAWN";
  publication_readiness?: { status: "READY" | "BLOCKED"; blockers: string[] };
  current_public_status?: "ELIGIBLE" | "SUPPRESSED";
  suppression_reasons?: string[];
}

/**
 * Mirrors the canonical server-evaluated readiness/status already shown on
 * the full inventory page (`inventory.astro`) -- never a second,
 * independently computed readiness rule.
 */
export function inventoryReadinessLabel(item: InventoryReadinessItem): string {
  if (item.publication_readiness) {
    return item.publication_readiness.status === "READY"
      ? "Ready to publish"
      : `Blocked: ${item.publication_readiness.blockers.join(", ")}`;
  }
  if (item.current_public_status) {
    return item.current_public_status === "ELIGIBLE"
      ? "Live"
      : `Suppressed: ${(item.suppression_reasons ?? []).join(", ")}`;
  }
  return item.lifecycle_state;
}

export function draftReadinessLabel(readiness: { ready: boolean; reasons: readonly string[] }): string {
  return readiness.ready ? "Ready to promote" : `Not ready: ${readiness.reasons.join(", ")}`;
}

export interface DraftPreviewFields {
  draft_id: string;
  broker_listing_reference: string | null;
  "physical_boat.boat_name"?: string;
}

export function draftPreviewLabel(draft: DraftPreviewFields): string {
  return draft["physical_boat.boat_name"] ?? draft.broker_listing_reference ?? draft.draft_id;
}
