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
  // SLICE-0071 contract §8B: optional, bounded, evidence-only acquisition
  // attribution -- present only when the buyer actually arrived with these
  // query parameters. Never a raw referrer/full query string.
  utm_source?: string;
  utm_medium?: string;
  utm_campaign?: string;
  utm_term?: string;
  utm_content?: string;
  // SLICE-0071 contract §8B amendment: an opaque, HMAC-signed, server-
  // verified discovery-surface token minted by whichever HullQ surface (or
  // the listing page itself) resolved it -- never a plain client-supplied
  // discovery-surface string. FastAPI independently re-verifies this; an
  // absent/invalid/expired/mismatched-listing token resolves to UNKNOWN,
  // never a guess.
  discovery_token?: string;
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
