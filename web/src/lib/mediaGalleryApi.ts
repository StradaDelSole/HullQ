// SLICE-0068: the only module allowed to talk to FastAPI's broker
// marketplace mixed-media gallery boundary via its normal JSON-body call
// shape. Astro never queries PostgreSQL or object storage directly and
// never reimplements processing/rights/ordering/cover semantics -- every
// result here is exactly what FastAPI decided, forwarded verbatim (mirrors
// `brokerApi.ts`'s identical discipline).
//
// Independent review Finding D: the one exception is image upload, which
// streams the request body straight through rather than materializing it as
// a `Uint8Array`/`JSON.stringify`-shaped call (see
// `media/upload.ts`'s own docstring for the full rationale). That route
// still reuses this module's exported CSRF constants and
// `MAX_IMAGE_UPLOAD_BYTES` so the two files cannot silently drift apart.
//
// The incoming request's `Cookie` header is forwarded unmodified so the
// HullQ session cookie reaches FastAPI on this server-to-server call, and
// this module is also the CSRF proxy for every mutation: it always adds the
// fixed `X-HullQ-Requested-With: marketplace-media-gallery-v1` header and
// forwards the browser's own `Origin` header value as Astro received it on
// the incoming page request -- never a substituted trusted value (mirrors
// `brokerApi.ts`'s identical rationale for the other three broker-write
// channels).

export const MEDIA_GALLERY_CSRF_HEADER_NAME = "X-HullQ-Requested-With";
export const MEDIA_GALLERY_CSRF_HEADER_VALUE = "marketplace-media-gallery-v1";
const CSRF_HEADER_NAME = MEDIA_GALLERY_CSRF_HEADER_NAME;
const CSRF_HEADER_VALUE = MEDIA_GALLERY_CSRF_HEADER_VALUE;

// Mirrors `hullq.domain.media_gallery.MAX_IMAGE_UPLOAD_BYTES` -- must stay in
// sync with that Python constant by hand; there is no shared build-time
// source of truth between the two languages.
export const MAX_IMAGE_UPLOAD_BYTES = 15_000_000;

// A finite per-request batch boundary (independent review Finding D: "impose
// a finite file-count/batch boundary") for the client-side multi-file
// upload script in `media.astro` -- an arbitrary-length file list is never
// accepted, even though each file is still uploaded one at a time.
export const MAX_FILES_PER_UPLOAD_BATCH = 20;

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
  source_kind: "BROKER_UPLOAD";
  source_reference: string | null;
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
// Upload (contract §6/§11) is deliberately NOT implemented in this module.
// Independent review Finding D: streaming the request body through requires
// passing a raw `ReadableStream` as `fetch`'s `body`, which cannot be
// expressed through this module's `Uint8Array`/`JSON.stringify` call shape
// without re-buffering it first -- exactly the resource-abuse gap Finding D
// exists to close. See `media/upload.ts` for the dedicated streaming proxy
// route, which still reuses this module's exported CSRF constants and
// `MAX_IMAGE_UPLOAD_BYTES`.
// ---------------------------------------------------------------------------

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
  | { kind: "active_listing_conflict" }
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
    if (body.error === "invalid_cover") return { kind: "invalid_cover" };
    if (body.error === "active_listing_conflict") return { kind: "active_listing_conflict" };
    return { kind: "version_conflict" };
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
  | { kind: "active_listing_conflict" }
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
  if (response.status === 409) {
    const body = (await response.json().catch(() => ({}) as Record<string, unknown>)) as {
      error?: string;
    };
    return body.error === "active_listing_conflict"
      ? { kind: "active_listing_conflict" }
      : { kind: "version_conflict" };
  }
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
  | { kind: "active_listing_conflict" }
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
  if (response.status === 409) {
    const body = (await response.json().catch(() => ({}) as Record<string, unknown>)) as {
      error?: string;
    };
    return body.error === "active_listing_conflict"
      ? { kind: "active_listing_conflict" }
      : { kind: "already_retired" };
  }
  if (!response.ok) return { kind: "service_error" };
  return { kind: "ok" };
}
