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
  offer_recorded_at: string;
  hullq_vat_verification_status: string;
  /**
   * `null` when the publishing Organization has not recorded any
   * SLICE-0050 claim for this listing's PhysicalBoat -- never a
   * BoatDesign baseline fallback, and never another Organization's claim.
   */
  physical_boat_claims: PhysicalBoatClaims | null;
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
