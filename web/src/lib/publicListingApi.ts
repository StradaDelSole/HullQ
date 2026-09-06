// SLICE-0049: the only module allowed to talk to the outside world for the
// public listing page. Astro obtains listing data through FastAPI only --
// this module never touches PostgreSQL or reimplements a Python domain
// rule; it is a thin typed HTTP client for the accepted public read model
// shape (`hullq.application.public_listing_read.PublicListingReadModel.to_public_dict`).
//
// No preview token is sent or accepted here: this hits the production
// public route (`/api/listings/{native_listing_id}`), never the
// SLICE-0048 bearer-capability preview route.
import type { ClaimField } from "./previewApi";

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
