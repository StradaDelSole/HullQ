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

export type ExportFieldState = "PRESENT" | "UNKNOWN" | "OMITTED";

export interface ExportFormatPreflight {
  exportable: boolean;
  reasons: string[];
  warnings: string[];
}

export interface ExportRowPreflight {
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
  | { kind: "service_error" }
  | { kind: "ok"; rows: ExportRowPreflight[] };

export async function fetchExportPreflight(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  selection: ExportSelection,
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
      body: JSON.stringify(selectionBody(selection)),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;

  let body: { error?: string; rows?: ExportRowPreflight[] } = {};
  try {
    body = await response.json();
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 200 && body.rows) return { kind: "ok", rows: body.rows };
  if (body.error === "empty_selection") return { kind: "empty_selection" };
  if (body.error === "oversize_selection") return { kind: "oversize_selection" };
  if (body.error === "unknown_item") return { kind: "unknown_item" };
  if (body.error === "invalid_selection") return { kind: "invalid_selection" };
  return { kind: "service_error" };
}

export type ExportDownloadResult =
  | OrgAuthFailure
  | { kind: "empty_selection" }
  | { kind: "oversize_selection" }
  | { kind: "unknown_item" }
  | { kind: "invalid_selection" }
  | { kind: "invalid_format" }
  | { kind: "export_busy" }
  | { kind: "export_write_failed" }
  | { kind: "service_error" }
  | { kind: "ok"; bytes: ArrayBuffer; contentType: string; filename: string };

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
      body: JSON.stringify({ ...selectionBody(selection), format }),
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

  if (response.status === 200) {
    const bytes = await response.arrayBuffer();
    return {
      kind: "ok",
      bytes,
      contentType: response.headers.get("content-type") ?? "application/octet-stream",
      filename: filenameFromContentDisposition(response.headers.get("content-disposition")),
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
  return { kind: "service_error" };
}
