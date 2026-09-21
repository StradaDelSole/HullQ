// SLICE-0049/SLICE-0050: the only module allowed to talk to the outside
// world for the public listing page. Astro obtains listing data through
// FastAPI only -- this module never touches PostgreSQL or reimplements a
// Python domain rule; it is a thin typed HTTP client for the accepted
// public read model shape
// (`hullq.application.public_listing_read.PublicListingReadModel.to_public_dict`).
//
// No preview token is sent or accepted here: this hits the production
// public route (`/api/listings/{native_listing_id}`), never the
// SLICE-0048 bearer-capability preview route.
import type { ClaimField } from "./previewApi";

/**
 * One SLICE-0050 optional PhysicalBoat claim field (`build_year`,
 * `loa_length`, `draft`, `keel_configuration`, `rudder_configuration`).
 * `value` is always a decimal-string/integer/categorical-string, never a
 * binary float.
 */
export interface OptionalBoatClaimField {
  assertion_kind: string;
  value: string | number | null;
}

/**
 * The bounded seven-field `THIS BOAT` broker-claim projection
 * (`hullq.application.public_listing_read._physical_boat_claims_dict`).
 * `marketed_brand_claim`/`model_designation_claim` are always present
 * (`REQUIRED_RESPONSE`, VALUE_ASSERTION-only); the remaining fields may
 * individually be `null` (omitted by the broker) or an explicit
 * UNKNOWN/VALUE_ASSERTION assertion object.
 */
export interface PhysicalBoatClaims {
  marketed_brand_claim: string;
  model_designation_claim: string;
  build_year: OptionalBoatClaimField;
  loa_length: OptionalBoatClaimField | null;
  draft: OptionalBoatClaimField | null;
  keel_configuration: OptionalBoatClaimField | null;
  rudder_configuration: OptionalBoatClaimField | null;
}

export interface PublicListingData {
  asking_price_mode: "AMOUNT" | "POA";
  asking_price_amount: string | null;
  currency: string | null;
  location_country: string;
  location_region: ClaimField | null;
  broker_summary: ClaimField | null;
  broker_description: string;
  known_history_narrative: ClaimField | null;
  vat_tax_status_claim: ClaimField | null;
  publishing_organization_id: string;
  /**
   * SLICE-0063: the publishing Organization's current bounded display
   * name, always present -- independent of VAT/tax or other optional
   * claim presence. Plain text only, never trusted HTML.
   */
  publishing_organization_display_name: string;
  offer_recorded_at: string;
  hullq_vat_verification_status: string;
  /**
   * `null` when the publishing Organization has not recorded any
   * SLICE-0050 claim for this listing's PhysicalBoat -- never a
   * BoatDesign baseline fallback, and never another Organization's claim.
   */
  physical_boat_claims: PhysicalBoatClaims | null;
  /**
   * SLICE-0052: always `"CONFIRMED"` or `"DUE_FOR_CONFIRMATION"` here --
   * FastAPI's public route already resolves `STALE`/`UNKNOWN` to the
   * identical not-found response, so this page never receives them.
   */
  freshness_status: "CONFIRMED" | "DUE_FOR_CONFIRMATION";
  /** ISO-8601 timestamp of the latest admissible confirmation evidence. */
  last_confirmed_at: string | null;
}

/**
 * Fetch the public read model for `nativeListingId` from the FastAPI public
 * listing route. Returns `null` for any non-2xx response (DRAFT, WITHDRAWN,
 * missing or incomplete listing) or a network failure -- the page must
 * render the identical "not found" state for every one of those cases,
 * never distinguish them.
 */
export async function fetchPublicListing(
  apiBaseUrl: string,
  nativeListingId: string,
): Promise<PublicListingData | null> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url = `${base}/api/listings/${encodeURIComponent(nativeListingId)}`;

  let response: Response;
  try {
    response = await fetch(url, { redirect: "manual" });
  } catch {
    return null;
  }
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as PublicListingData;
}

/**
 * SLICE-0058 (`specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md` §10/§13):
 * unlike `fetchPublicListing` above, the shortlist resolver must NOT collapse
 * a genuine transport/upstream failure into the identical "not found" result
 * a DRAFT/WITHDRAWN/missing listing produces -- Required Behavior §G
 * forbids presenting an infrastructure outage as ordinary listing-state
 * truth. `"unavailable"` is reserved for the real accepted-public-read
 * not-found boundary (an actual HTTP 404 from `/api/listings/{id}`);
 * anything else that isn't a clean 2xx (network failure, malformed body, a
 * 5xx) is `"service_error"` instead, so the caller can render a bounded
 * retry state without touching local shortlist membership.
 */
export type ShortlistPublicListingResult =
  | { kind: "available"; data: PublicListingData }
  | { kind: "unavailable" }
  | { kind: "service_error" };

export async function fetchPublicListingForShortlist(
  apiBaseUrl: string,
  nativeListingId: string,
): Promise<ShortlistPublicListingResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url = `${base}/api/listings/${encodeURIComponent(nativeListingId)}`;

  let response: Response;
  try {
    response = await fetch(url, { redirect: "manual" });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 404) {
    return { kind: "unavailable" };
  }
  if (!response.ok) {
    return { kind: "service_error" };
  }
  try {
    const data = (await response.json()) as PublicListingData;
    return { kind: "available", data };
  } catch {
    return { kind: "service_error" };
  }
}
