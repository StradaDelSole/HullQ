// SLICE-0088: the only module allowed to talk to FastAPI's broker inventory
// portability export boundary. Astro never queries PostgreSQL directly and
// never reimplements authorization/preflight/format decisions in
// TypeScript -- every result here is exactly what FastAPI decided,
// forwarded verbatim (same discipline as `importIntakeApi.ts`).
//
// This module is also the SLICE-0088 CSRF proxy: it is Astro's own server
// calling FastAPI server-to-server, never the browser calling FastAPI
// directly. `originHeader`/`cookieHeader` must be exactly what Astro
// received on the incoming browser request.
//
// Seven Owner-accepted export formats only (2026-10-16 amendment). XLSB is
// explicitly deferred (GitHub issue #362) and is never offered here.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "broker-inventory-export-v1";

export type ExportFormat = "CSV" | "TSV" | "XLSX" | "XLS" | "ODS" | "JSON" | "NAUTIX";

export const EXPORT_FORMATS: readonly ExportFormat[] = [
  "CSV",
  "TSV",
  "XLSX",
  "XLS",
  "ODS",
  "JSON",
  "NAUTIX",
];

export interface ExportSelection {
  draftIds: string[];
  nativeListingIds: string[];
}

/**
 * The broker's own confirmed NautiX export attestation for exactly one
 * download -- never read from stored HullQ data, never persisted beyond
 * this one call (see `hullq.domain.inventory_export`'s module docstring).
 * `saleClasses` is keyed by the raw selected draft/native_listing id.
 */
export interface NautixExportProfile {
  accountToken: string;
  officeId: string;
  saleClasses: Record<string, string>;
}

function nautixProfileBody(profile: NautixExportProfile | undefined): Record<string, unknown> {
  if (!profile) return {};
  return {
    nautix_profile: {
      account_token: profile.accountToken,
      office_id: profile.officeId,
      sale_classes: profile.saleClasses,
    },
  };
}

export type ExportFieldState = "PRESENT" | "UNKNOWN" | "OMITTED";

export interface ExportFormatPreflight {
  exportable: boolean;
  reasons: string[];
  warnings: string[];
}

export interface ExportRowPreflight {
  /** Stable per-Organization listing export identifier. */
  export_id: string;
  source_kind: "PRIVATE_DRAFT" | "PROMOTED_LISTING";
  field_states: Record<string, ExportFieldState>;
  formats: Record<ExportFormat, ExportFormatPreflight>;
}

function cookieHeaders(cookieHeader: string | null): Record<string, string> {
  return cookieHeader ? { Cookie: cookieHeader } : {};
}

function csrfHeaders(originHeader: string | null): Record<string, string> {
  return {
    ...(originHeader ? { Origin: originHeader } : {}),
    [CSRF_HEADER_NAME]: CSRF_HEADER_VALUE,
  };
}

function exportPath(organizationId: string, action: "preflight" | "download"): string {
  return `/api/broker/organizations/${encodeURIComponent(organizationId)}/inventory/export/${action}`;
}

function selectionBody(selection: ExportSelection): Record<string, unknown> {
  return { draft_ids: selection.draftIds, native_listing_ids: selection.nativeListingIds };
}

type OrgAuthFailure =
  | { kind: "unauthenticated" }
  | { kind: "not_found" }
  | { kind: "mfa_required" }
  | { kind: "publisher_role_required" };

async function classify403(response: Response): Promise<OrgAuthFailure> {
  let body: { error?: string } = {};
  try {
    body = (await response.json()) as { error?: string };
  } catch {
    // fall through to the generic mfa_required classification below
  }
  if (body.error === "publisher_role_required") return { kind: "publisher_role_required" };
  return { kind: "mfa_required" };
}

function orgAuthFailureFromStatus(status: number): OrgAuthFailure | null {
  if (status === 401) return { kind: "unauthenticated" };
  if (status === 404) return { kind: "not_found" };
  return null;
}

export type ExportPreflightResult =
  | OrgAuthFailure
  | { kind: "empty_selection" }
  | { kind: "oversize_selection" }
  | { kind: "unknown_item" }
  | { kind: "invalid_selection" }
  | { kind: "invalid_nautix_profile" }
  | { kind: "export_busy" }
  | { kind: "service_error" }
  | { kind: "ok"; rows: ExportRowPreflight[]; snapshotFingerprint: string };

export async function fetchExportPreflight(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  selection: ExportSelection,
  nautixProfile?: NautixExportProfile,
): Promise<ExportPreflightResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${exportPath(organizationId, "preflight")}`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ ...selectionBody(selection), ...nautixProfileBody(nautixProfile) }),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 429) return { kind: "export_busy" };

  let body: { error?: string; rows?: ExportRowPreflight[]; snapshot_fingerprint?: string } = {};
  try {
    body = await response.json();
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 200 && body.rows && body.snapshot_fingerprint) {
    return { kind: "ok", rows: body.rows, snapshotFingerprint: body.snapshot_fingerprint };
  }
  if (body.error === "empty_selection") return { kind: "empty_selection" };
  if (body.error === "oversize_selection") return { kind: "oversize_selection" };
  if (body.error === "unknown_item") return { kind: "unknown_item" };
  if (body.error === "invalid_selection") return { kind: "invalid_selection" };
  if (body.error === "invalid_nautix_profile") return { kind: "invalid_nautix_profile" };
  return { kind: "service_error" };
}

export type ExportDownloadResult =
  | OrgAuthFailure
  | { kind: "empty_selection" }
  | { kind: "oversize_selection" }
  | { kind: "unknown_item" }
  | { kind: "invalid_selection" }
  | { kind: "invalid_format" }
  | { kind: "invalid_nautix_profile" }
  | { kind: "stale_selection" }
  | { kind: "no_exportable_rows" }
  | { kind: "export_busy" }
  | { kind: "export_write_failed" }
  | { kind: "service_error" }
  | {
      kind: "ok";
      bytes: ArrayBuffer;
      contentType: string;
      filename: string;
      includedCount: number;
      rejectedCount: number;
    };

function filenameFromContentDisposition(value: string | null): string {
  if (!value) return "hullq-inventory-export";
  const match = /filename="([^"]+)"/.exec(value);
  return match ? match[1] : "hullq-inventory-export";
}

export async function downloadExport(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  selection: ExportSelection,
  format: ExportFormat,
  options?: { nautixProfile?: NautixExportProfile; expectedSnapshotFingerprint?: string },
): Promise<ExportDownloadResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${exportPath(organizationId, "download")}`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        ...selectionBody(selection),
        format,
        ...nautixProfileBody(options?.nautixProfile),
        ...(options?.expectedSnapshotFingerprint
          ? { expected_snapshot_fingerprint: options.expectedSnapshotFingerprint }
          : {}),
      }),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 429) return { kind: "export_busy" };
  if (response.status === 500) return { kind: "export_write_failed" };
  if (response.status === 409) return { kind: "stale_selection" };
  if (response.status === 422) return { kind: "no_exportable_rows" };

  if (response.status === 200) {
    const bytes = await response.arrayBuffer();
    return {
      kind: "ok",
      bytes,
      contentType: response.headers.get("content-type") ?? "application/octet-stream",
      filename: filenameFromContentDisposition(response.headers.get("content-disposition")),
      includedCount: Number(response.headers.get("x-hullq-export-included-count") ?? "0"),
      rejectedCount: Number(response.headers.get("x-hullq-export-rejected-count") ?? "0"),
    };
  }

  let body: { error?: string } = {};
  try {
    body = await response.json();
  } catch {
    return { kind: "service_error" };
  }
  if (body.error === "empty_selection") return { kind: "empty_selection" };
  if (body.error === "oversize_selection") return { kind: "oversize_selection" };
  if (body.error === "unknown_item") return { kind: "unknown_item" };
  if (body.error === "invalid_selection") return { kind: "invalid_selection" };
  if (body.error === "invalid_format") return { kind: "invalid_format" };
  if (body.error === "invalid_nautix_profile") return { kind: "invalid_nautix_profile" };
  return { kind: "service_error" };
}
