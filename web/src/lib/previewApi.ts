// SLICE-0048: the only module allowed to talk to the outside world for the
// preview page. Astro obtains listing data through FastAPI only -- this
// module never touches PostgreSQL or reimplements a Python domain rule; it
// is a thin typed HTTP client for the one accepted preview read model shape
// (`hullq.application.preview_read.PreviewReadModel.to_public_dict`).

export interface ClaimField {
  assertion_kind: string;
  value: string | null;
}

export interface ListingPreviewData {
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
  preview_expires_at: string;
}

/**
 * Fetch the preview read model for `previewToken` from the FastAPI preview
 * route. Returns `null` for any non-2xx response (invalid/tampered/expired
 * token, missing listing, incomplete chain) or a network failure -- the
 * page must render the identical "not found" state for every one of those
 * cases, never distinguish them.
 */
export async function fetchListingPreview(
  apiBaseUrl: string,
  previewToken: string,
): Promise<ListingPreviewData | null> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url = `${base}/api/_preview/listings/${encodeURIComponent(previewToken)}`;

  let response: Response;
  try {
    response = await fetch(url, { redirect: "manual" });
  } catch {
    return null;
  }
  if (!response.ok) {
    return null;
  }
  return (await response.json()) as ListingPreviewData;
}
