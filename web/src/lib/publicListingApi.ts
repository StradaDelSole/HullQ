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

/**
 * SLICE-0069 contract §14/§21: one bounded public gallery entry.
 * `media_placement_id` is the only identity exposed for an `IMAGE` entry --
 * exactly what is needed to build the listing-scoped public derivative URL
 * (`GET /api/listings/{native_listing_id}/media/{media_placement_id}`); no
 * MediaAssetId/object key/uploader identity ever appears here.
 * `youtube_video_id` is present iff `kind` is `"YOUTUBE"` -- the normalized
 * 11-character id only, never broker-supplied embed HTML.
 */
export interface PublicGalleryItem {
  kind: "IMAGE" | "YOUTUBE";
  media_placement_id: string;
  youtube_video_id?: string;
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
  /**
   * SLICE-0069 contract §14: the bounded public mixed-media gallery, ordered
   * by the same persisted placement ordering the Broker Workspace gallery
   * uses. Always an array (possibly empty) -- D22 requires at least one
   * public-usable image to publish at all, so an empty array here would only
   * ever reflect a later, already-suppressed state this route would not
   * otherwise be serving.
   */
  gallery: PublicGalleryItem[];
  /** The exact `media_placement_id` of the explicit cover image, if any. */
  cover_media_placement_id: string | null;
  /**
   * SLICE-0071 contract §8B amendment: an opaque, HMAC-signed discovery-
   * surface token bound to this exact listing, present only when a
   * *trusted server-side caller* minted one for it (the shortlist/compare
   * resolution routes -- see `shortlistResolveServer.ts`). The plain
   * `GET /api/listings/{id}` route this function calls never mints or
   * accepts any discovery-surface parameter itself (independent-review
   * Finding B), so this field is absent here; it is added afterward, only
   * by trusted code, in `fetchPublicListingForShortlist`'s caller.
   */
  discovery_token?: string;
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

export type PublicListingMediaBytesResult =
  | { kind: "not_found" }
  | { kind: "service_error" }
  | { kind: "ok"; data: ArrayBuffer; contentType: string };

/**
 * SLICE-0069 contract §15/§21: fetch one listing-scoped public derivative
 * image from FastAPI's public, non-enumerating, fail-closed media route.
 * `not_found` covers every rejection reason that route can produce (unknown/
 * foreign listing, unknown/foreign placement, a non-IMAGE placement, a
 * non-public-usable asset, an object-storage retrieval failure) -- this
 * client never distinguishes them either.
 */
export async function fetchPublicListingMediaBytes(
  apiBaseUrl: string,
  nativeListingId: string,
  mediaPlacementId: string,
): Promise<PublicListingMediaBytesResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const url =
    `${base}/api/listings/${encodeURIComponent(nativeListingId)}` +
    `/media/${encodeURIComponent(mediaPlacementId)}`;

  let response: Response;
  try {
    response = await fetch(url, { redirect: "manual" });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 404) {
    return { kind: "not_found" };
  }
  if (!response.ok) {
    return { kind: "service_error" };
  }
  const data = await response.arrayBuffer();
  const contentType = response.headers.get("content-type") ?? "application/octet-stream";
  return { kind: "ok", data, contentType };
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
