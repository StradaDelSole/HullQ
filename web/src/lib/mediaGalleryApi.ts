// SLICE-0068: the only module allowed to talk to FastAPI's broker
// marketplace mixed-media gallery boundary. Astro never queries PostgreSQL
// or object storage directly and never reimplements processing/rights/
// ordering/cover semantics -- every result here is exactly what FastAPI
// decided, forwarded verbatim (mirrors `brokerApi.ts`'s identical
// discipline).
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie reaches FastAPI on this server-to-server call, and
// this module is also the CSRF proxy for every mutation: it always adds the
// fixed `X-HullQ-Requested-With: marketplace-media-gallery-v1` header and
// forwards the browser's own `Origin` header value as Astro received it on
// the incoming page request -- never a substituted trusted value (mirrors
// `brokerApi.ts`'s identical rationale for the other three broker-write
// channels).

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "marketplace-media-gallery-v1";

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function csrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE,
  };
}

function trimBase(apiBaseUrl: string): string {
  return apiBaseUrl.replace(/\/+$/, "");
}

function galleryPath(organizationId: string, nativeListingId: string): string {
  return (
    `/api/broker/organizations/${encodeURIComponent(organizationId)}` +
    `/inventory/${encodeURIComponent(nativeListingId)}/media`
  );
}

// ---------------------------------------------------------------------------
// Gallery state read
// ---------------------------------------------------------------------------

export interface MediaAssetView {
  media_asset_id: string;
  processing_state: "APPROVED" | "REJECTED";
  rights_state: "UNKNOWN" | "DECLARED";
  rejection_reason: string | null;
  mime_type: string | null;
  width: number | null;
  height: number | null;
  byte_size: number | null;
  retired: boolean;
  is_public_usable: boolean;
  created_at: string;
}

export interface MediaPlacementView {
  media_placement_id: string;
  kind: "IMAGE" | "YOUTUBE";
  position: number;
  created_at: string;
  media_asset?: MediaAssetView;
  youtube_video_id?: string;
  youtube_source_url?: string;
}

export interface GalleryState {
  native_listing_id: string;
  gallery_version: number;
  cover_placement_id: string | null;
  placements: MediaPlacementView[];
}

/** Shared org-level authorization outcomes carried by every result below. */
type AuthFailure =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "role_required" };

// Deliberately excludes 404: its body shape (and therefore its meaning --
// a foreign/unknown Organization vs. a foreign/unknown listing/asset/
// placement) differs per route, so each function below classifies its own
// 404 rather than this shared helper collapsing all of them to one generic
// `not_found` before route-specific logic ever runs.
function simpleAuthFailureFromStatus(status: number): { kind: "unauthenticated" } | null {
  if (status === 401) return { kind: "unauthenticated" };
  return null;
}

/**
 * Classify a 403 from any media gallery route: FastAPI's
 * `_media_actor_authorization_error` (`hullq.api.app`) returns exactly two
 * distinguishable body shapes for this boundary --
 * `{"error":"mfa_required"}` and `{"error":"publisher_role_required"}` --
 * plus the CSRF-rejection path, which this module's own request
 * construction always satisfies (fixed Origin/header), so any other 403
 * body is a genuine unexpected condition (contract: "service failure" must
 * stay distinct, never silently folded into an authorization outcome).
 */
async function classifyAuthorization403(
  response: Response,
): Promise<{ kind: "mfa_required" } | { kind: "role_required" } | { kind: "service_error" }> {
  let body: { error?: string } = {};
  try {
    body = (await response.json()) as { error?: string };
  } catch {
    return { kind: "service_error" };
  }
  if (body.error === "mfa_required") return { kind: "mfa_required" };
  if (body.error === "publisher_role_required") return { kind: "role_required" };
  return { kind: "service_error" };
}

async function authFailureFromResponse(
  response: Response,
): Promise<AuthFailure | { kind: "service_error" } | null> {
  const simple = simpleAuthFailureFromStatus(response.status);
  if (simple) return simple;
  if (response.status === 403) return await classifyAuthorization403(response);
  return null;
}

export type GalleryReadResult = AuthFailure | { kind: "service_error" } | { kind: "ok"; data: GalleryState };

export async function fetchListingGallery(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  cookieHeader: string | null,
): Promise<GalleryReadResult> {
  let response: Response;
  try {
    response = await fetch(`${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "not_found" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as GalleryState;
  return { kind: "ok", data };
}

// ---------------------------------------------------------------------------
// Media library read
// ---------------------------------------------------------------------------

export type LibraryReadResult =
  | AuthFailure
  | { kind: "service_error" }
  | { kind: "ok"; assets: MediaAssetView[] };

export async function fetchMediaLibrary(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<LibraryReadResult> {
  let response: Response;
  try {
    response = await fetch(
      `${trimBase(apiBaseUrl)}/api/broker/organizations/${encodeURIComponent(organizationId)}/media/library`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "not_found" };
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { assets: MediaAssetView[] };
  return { kind: "ok", assets: data.assets };
}

// ---------------------------------------------------------------------------
// Broker-only asset bytes preview (used by the same-origin image proxy route)
// ---------------------------------------------------------------------------

export type AssetBytesResult =
  | AuthFailure
  | { kind: "not_found" }
  | { kind: "service_error" }
  | { kind: "ok"; data: ArrayBuffer; contentType: string };

export async function fetchMediaAssetBytes(
  apiBaseUrl: string,
  organizationId: string,
  mediaAssetId: string,
  cookieHeader: string | null,
): Promise<AssetBytesResult> {
  let response: Response;
  try {
    response = await fetch(
      `${trimBase(apiBaseUrl)}/api/broker/organizations/${encodeURIComponent(organizationId)}` +
        `/media/assets/${encodeURIComponent(mediaAssetId)}`,
      { headers: cookieHeaders(cookieHeader), redirect: "manual" },
    );
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 401) return { kind: "unauthenticated" };
  if (response.status === 404) return { kind: "not_found" };
  if (response.status === 403) return { kind: "mfa_required" };
  if (!response.ok) return { kind: "service_error" };
  const data = await response.arrayBuffer();
  const contentType = response.headers.get("content-type") ?? "application/octet-stream";
  return { kind: "ok", data, contentType };
}

// ---------------------------------------------------------------------------
// Upload (contract §6/§11) -- one call per file; the browser-visible
// "multi-file" behavior is one page action that issues several of these
// (see the gallery workspace page), never a multipart body parsed here.
// ---------------------------------------------------------------------------

export type UploadImageResult =
  | AuthFailure
  | { kind: "listing_not_found" }
  | { kind: "payload_too_large" }
  | { kind: "rejected"; reason: string }
  | { kind: "service_error" }
  | { kind: "ok"; mediaAssetId: string; mediaPlacementId: string; galleryVersion: number };

export async function uploadListingImage(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  imageBytes: Uint8Array,
  contentType: string,
  rightsConfirmed: boolean,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<UploadImageResult> {
  let response: Response;
  try {
    response = await fetch(`${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}/images`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": contentType,
        "X-HullQ-Rights-Confirmed": rightsConfirmed ? "true" : "false",
      },
      body: Buffer.from(imageBytes),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "listing_not_found" };
  if (response.status === 413) return { kind: "payload_too_large" };
  if (response.status === 422) {
    const body = (await response.json()) as { reason?: string };
    return { kind: "rejected", reason: body.reason ?? "unknown" };
  }
  if (!response.ok) return { kind: "service_error" };
  const body = (await response.json()) as {
    media_asset_id: string;
    media_placement_id: string;
    gallery_version: number;
  };
  return {
    kind: "ok",
    mediaAssetId: body.media_asset_id,
    mediaPlacementId: body.media_placement_id,
    galleryVersion: body.gallery_version,
  };
}

// ---------------------------------------------------------------------------
// Same-Organization reuse (contract §9)
// ---------------------------------------------------------------------------

export type ReuseAssetResult =
  | AuthFailure
  | { kind: "listing_not_found" }
  | { kind: "asset_not_found" }
  | { kind: "service_error" }
  | { kind: "ok"; mediaPlacementId: string; galleryVersion: number };

export async function reuseListingMedia(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  mediaAssetId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ReuseAssetResult> {
  let response: Response;
  try {
    response = await fetch(`${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}/reuse`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ media_asset_id: mediaAssetId }),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 404) {
    const body = (await response.json().catch(() => ({}) as Record<string, unknown>)) as {
      error?: string;
    };
    return body.error === "asset_not_found" ? { kind: "asset_not_found" } : { kind: "listing_not_found" };
  }
  if (!response.ok) return { kind: "service_error" };
  const body = (await response.json()) as { media_placement_id: string; gallery_version: number };
  return { kind: "ok", mediaPlacementId: body.media_placement_id, galleryVersion: body.gallery_version };
}

// ---------------------------------------------------------------------------
// YouTube add (contract §10)
// ---------------------------------------------------------------------------

export type AddYoutubeResult =
  | AuthFailure
  | { kind: "listing_not_found" }
  | { kind: "invalid_url" }
  | { kind: "service_error" }
  | { kind: "ok"; mediaPlacementId: string; galleryVersion: number };

export async function addListingYoutube(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  url: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<AddYoutubeResult> {
  let response: Response;
  try {
    response = await fetch(`${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}/youtube`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ url }),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "listing_not_found" };
  if (response.status === 400) return { kind: "invalid_url" };
  if (!response.ok) return { kind: "service_error" };
  const body = (await response.json()) as { media_placement_id: string; gallery_version: number };
  return { kind: "ok", mediaPlacementId: body.media_placement_id, galleryVersion: body.gallery_version };
}

// ---------------------------------------------------------------------------
// Reorder (contract §8/§16)
// ---------------------------------------------------------------------------

export type ReorderGalleryResult =
  | AuthFailure
  | { kind: "invalid_payload" }
  | { kind: "listing_not_found" }
  | { kind: "version_conflict" }
  | { kind: "invalid_placement_set" }
  | { kind: "service_error" }
  | { kind: "ok"; galleryVersion: number };

export async function reorderListingGallery(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  expectedVersion: number,
  placementIds: string[],
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ReorderGalleryResult> {
  let response: Response;
  try {
    response = await fetch(`${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}/reorder`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ expected_version: expectedVersion, placement_ids: placementIds }),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 400) return { kind: "invalid_payload" };
  if (response.status === 404) return { kind: "listing_not_found" };
  if (response.status === 409) {
    const body = (await response.json().catch(() => ({}) as Record<string, unknown>)) as {
      error?: string;
    };
    return body.error === "invalid_placement_set"
      ? { kind: "invalid_placement_set" }
      : { kind: "version_conflict" };
  }
  if (!response.ok) return { kind: "service_error" };
  const body = (await response.json()) as { gallery_version: number };
  return { kind: "ok", galleryVersion: body.gallery_version };
}

// ---------------------------------------------------------------------------
// Cover (contract §8)
// ---------------------------------------------------------------------------

export type SetCoverResult =
  | AuthFailure
  | { kind: "invalid_payload" }
  | { kind: "listing_not_found" }
  | { kind: "version_conflict" }
  | { kind: "invalid_cover" }
  | { kind: "service_error" }
  | { kind: "ok"; outcome: "SET" | "CLEARED"; galleryVersion: number };

export async function setListingCover(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  expectedVersion: number,
  mediaPlacementId: string | null,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<SetCoverResult> {
  let response: Response;
  try {
    response = await fetch(`${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}/cover`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ expected_version: expectedVersion, media_placement_id: mediaPlacementId }),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 400) return { kind: "invalid_payload" };
  if (response.status === 404) return { kind: "listing_not_found" };
  if (response.status === 409) {
    const body = (await response.json().catch(() => ({}) as Record<string, unknown>)) as {
      error?: string;
    };
    return body.error === "invalid_cover" ? { kind: "invalid_cover" } : { kind: "version_conflict" };
  }
  if (!response.ok) return { kind: "service_error" };
  const body = (await response.json()) as { outcome: "SET" | "CLEARED"; gallery_version: number };
  return { kind: "ok", outcome: body.outcome, galleryVersion: body.gallery_version };
}

// ---------------------------------------------------------------------------
// Remove placement (contract §12)
// ---------------------------------------------------------------------------

export type RemovePlacementResult =
  | AuthFailure
  | { kind: "invalid_payload" }
  | { kind: "listing_not_found" }
  | { kind: "placement_not_found" }
  | { kind: "version_conflict" }
  | { kind: "service_error" }
  | { kind: "ok"; galleryVersion: number };

export async function removeListingPlacement(
  apiBaseUrl: string,
  organizationId: string,
  nativeListingId: string,
  mediaPlacementId: string,
  expectedVersion: number,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<RemovePlacementResult> {
  let response: Response;
  try {
    response = await fetch(
      `${trimBase(apiBaseUrl)}${galleryPath(organizationId, nativeListingId)}` +
        `/placements/${encodeURIComponent(mediaPlacementId)}/remove`,
      {
        method: "POST",
        headers: {
          ...cookieHeaders(cookieHeader),
          ...csrfHeaders(originHeader),
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ expected_version: expectedVersion }),
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 400) return { kind: "invalid_payload" };
  if (response.status === 404) {
    const body = (await response.json().catch(() => ({}) as Record<string, unknown>)) as {
      error?: string;
    };
    return body.error === "placement_not_found"
      ? { kind: "placement_not_found" }
      : { kind: "listing_not_found" };
  }
  if (response.status === 409) return { kind: "version_conflict" };
  if (!response.ok) return { kind: "service_error" };
  const body = (await response.json()) as { gallery_version: number };
  return { kind: "ok", galleryVersion: body.gallery_version };
}

// ---------------------------------------------------------------------------
// Retire asset (contract §12) -- Organization-scoped, not listing-scoped.
// ---------------------------------------------------------------------------

export type RetireAssetResult =
  | AuthFailure
  | { kind: "asset_not_found" }
  | { kind: "already_retired" }
  | { kind: "service_error" }
  | { kind: "ok" };

export async function retireMediaAsset(
  apiBaseUrl: string,
  organizationId: string,
  mediaAssetId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<RetireAssetResult> {
  let response: Response;
  try {
    response = await fetch(
      `${trimBase(apiBaseUrl)}/api/broker/organizations/${encodeURIComponent(organizationId)}` +
        `/media/assets/${encodeURIComponent(mediaAssetId)}/retire`,
      {
        method: "POST",
        headers: { ...cookieHeaders(cookieHeader), ...csrfHeaders(originHeader) },
        redirect: "manual",
      },
    );
  } catch {
    return { kind: "service_error" };
  }
  const authFailure = await authFailureFromResponse(response);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "asset_not_found" };
  if (response.status === 409) return { kind: "already_retired" };
  if (!response.ok) return { kind: "service_error" };
  return { kind: "ok" };
}
