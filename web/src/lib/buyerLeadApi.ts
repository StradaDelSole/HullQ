// SLICE-0070: shared constants for the anonymous-capable buyer contact /
// Lead creation proxy route (`pages/listings/[native_listing_id]/contact.ts`)
// and its client-side form script. Mirrors `mediaGalleryApi.ts`'s exported
// CSRF-constant discipline so the proxy route and any future caller cannot
// silently drift apart -- the fixed header name/value here must always
// match `hullq.api.app._BUYER_LEAD_CSRF_HEADER_VALUE` exactly.

export const BUYER_LEAD_CSRF_HEADER_NAME = "X-HullQ-Requested-With";
export const BUYER_LEAD_CSRF_HEADER_VALUE = "marketplace-buyer-lead-v1";

// Mirrors `hullq.api.app._MAX_BUYER_LEAD_BODY_BYTES` -- must stay in sync
// with that Python constant by hand; there is no shared build-time source
// of truth between the two languages.
export const MAX_BUYER_LEAD_BODY_BYTES = 20_000;

export interface BuyerLeadContactRequest {
  submission_operation_id: string;
  name: string;
  email: string;
  message: string;
}

/**
 * The bounded public creation-result vocabulary
 * (`hullq.application.buyer_lead_creation.CreateBuyerLeadOutcome`).
 */
export type BuyerLeadContactOutcome =
  | { kind: "created" | "already_exists"; leadId: string; receivedAt: string }
  | { kind: "invalid_input" }
  | { kind: "listing_not_available" }
  | { kind: "submission_conflict" }
  | { kind: "service_error" };
