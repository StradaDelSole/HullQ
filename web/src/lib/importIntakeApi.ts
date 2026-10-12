// SLICE-0083: the only module allowed to talk to FastAPI's multi-format
// broker inventory import intake boundary. Astro never queries PostgreSQL
// directly and never reimplements format/mapping/classification/D26
// identity decisions in TypeScript -- every result here is exactly what
// FastAPI decided, forwarded verbatim (same discipline as
// `professionalDraftApi.ts`).
//
// This module is also the SLICE-0083 CSRF proxy: it is Astro's own server
// calling FastAPI server-to-server, never the browser calling FastAPI
// directly. `originHeader`/`cookieHeader` must be exactly what Astro
// received on the incoming browser request.

const CSRF_HEADER_NAME = "X-HullQ-Requested-With";
const CSRF_HEADER_VALUE = "broker-import-intake-v1";

export type ImportFormat = "CSV" | "TSV" | "XLSX" | "XLS" | "XLSB" | "ODS" | "JSON" | "NAUTIX_XML";

export interface ImportRow {
  row_ordinal: number;
  raw_fields: Record<string, string | null>;
  unmapped_headers: string[];
  preview_classification: "VALID" | "INVALID" | "CONFLICT_REVIEW";
  preview_reasons: string[];
  source_record_key: string | null;
  outcome: "CREATE_NEW_DRAFT" | "ALREADY_IMPORTED" | "CONFLICT_REVIEW" | "INVALID" | null;
  created_professional_listing_draft_id: string | null;
}

export interface ImportBatch {
  import_batch_id: string;
  import_format: ImportFormat;
  import_source: string;
  worksheet_name: string | null;
  snapshot_mode: boolean;
  status: "AWAITING_MAPPING" | "MAPPED" | "CONFIRMING" | "CONFIRMED" | "EXPIRED";
  row_count: number;
  created_at: string;
  expires_at: string;
  headers?: string[];
  preview_rows?: (string | null)[][];
  column_mapping?: Record<string, string>;
  mapped_at?: string;
  confirmed_at?: string;
  rows: ImportRow[];
  summary?: Record<string, number>;
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

function importsPath(organizationId: string): string {
  return `/api/broker/organizations/${encodeURIComponent(organizationId)}/imports`;
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

export type ImportListResult = OrgAuthFailure | { kind: "service_error" } | { kind: "ok"; batches: ImportBatch[] };

export async function fetchImportBatches(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
): Promise<ImportListResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${importsPath(organizationId)}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "service_error" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (!response.ok) return { kind: "service_error" };
  const data = (await response.json()) as { batches: ImportBatch[] };
  return { kind: "ok", batches: data.batches };
}

export type ImportGetResult = OrgAuthFailure | { kind: "batch_not_found" } | { kind: "ok"; batch: ImportBatch };

export async function fetchImportBatch(
  apiBaseUrl: string,
  organizationId: string,
  batchId: string,
  cookieHeader: string | null,
): Promise<ImportGetResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${importsPath(organizationId)}/${encodeURIComponent(batchId)}`, {
      headers: cookieHeaders(cookieHeader),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "batch_not_found" };
  if (!response.ok) return { kind: "batch_not_found" };
  const data = (await response.json()) as ImportBatch;
  return { kind: "ok", batch: data };
}

export type ImportUploadResult =
  | OrgAuthFailure
  | { kind: "parse_failed"; kindOfError: string | null; message: string | null }
  | { kind: "worksheet_choice_required"; worksheets: string[] }
  | { kind: "invalid" }
  | { kind: "ok"; batch: ImportBatch };

export async function uploadImport(
  apiBaseUrl: string,
  organizationId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  options: {
    fileBytes: ArrayBuffer;
    declaredFormat: ImportFormat;
    importSource: string;
    worksheetName?: string;
    nautixAccountTokens?: string[];
  },
): Promise<ImportUploadResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const headers: Record<string, string> = {
    ...cookieHeaders(cookieHeader),
    ...csrfHeaders(originHeader),
    "Content-Type": "application/octet-stream",
    "X-HullQ-Import-Format": options.declaredFormat,
    "X-HullQ-Import-Source": options.importSource,
  };
  if (options.worksheetName) headers["X-HullQ-Worksheet"] = options.worksheetName;
  if (options.nautixAccountTokens?.length) {
    headers["X-HullQ-Nautix-Account-Tokens"] = options.nautixAccountTokens.join(",");
  }

  let response: Response;
  try {
    response = await fetch(`${base}${importsPath(organizationId)}`, {
      method: "POST",
      headers,
      body: options.fileBytes,
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;

  let body: {
    error?: string;
    kind?: string | null;
    message?: string | null;
    worksheets?: string[];
  } & Partial<ImportBatch> = {};
  try {
    body = await response.json();
  } catch {
    return { kind: "invalid" };
  }
  if (response.status === 201) return { kind: "ok", batch: body as ImportBatch };
  if (body.error === "worksheet_choice_required") {
    return { kind: "worksheet_choice_required", worksheets: body.worksheets ?? [] };
  }
  if (body.error === "parse_failed" || body.error === "unsupported_format") {
    return { kind: "parse_failed", kindOfError: body.kind ?? null, message: body.message ?? null };
  }
  return { kind: "invalid" };
}

export type ImportSetMappingResult =
  | OrgAuthFailure
  | { kind: "batch_not_found" }
  | { kind: "wrong_state" }
  | { kind: "invalid_mapping"; message: string | null }
  | { kind: "ok"; batch: ImportBatch };

export async function setImportMapping(
  apiBaseUrl: string,
  organizationId: string,
  batchId: string,
  cookieHeader: string | null,
  originHeader: string | null,
  columnMapping: Record<string, string>,
  snapshotMode: boolean,
): Promise<ImportSetMappingResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${importsPath(organizationId)}/${encodeURIComponent(batchId)}/mapping`, {
      method: "PUT",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ column_mapping: columnMapping, snapshot_mode: snapshotMode }),
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "batch_not_found" };
  if (response.status === 409) return { kind: "wrong_state" };
  let body: { error?: string; message?: string | null } & Partial<ImportBatch> = {};
  try {
    body = await response.json();
  } catch {
    return { kind: "invalid_mapping", message: null };
  }
  if (response.status === 200) return { kind: "ok", batch: body as ImportBatch };
  return { kind: "invalid_mapping", message: body.message ?? null };
}

export type ImportConfirmResult =
  | OrgAuthFailure
  | { kind: "batch_not_found" }
  | { kind: "wrong_state" }
  | { kind: "staging_expired" }
  | { kind: "ok"; batch: ImportBatch };

export async function confirmImportBatch(
  apiBaseUrl: string,
  organizationId: string,
  batchId: string,
  cookieHeader: string | null,
  originHeader: string | null,
): Promise<ImportConfirmResult> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  let response: Response;
  try {
    response = await fetch(`${base}${importsPath(organizationId)}/${encodeURIComponent(batchId)}/confirm`, {
      method: "POST",
      headers: {
        ...cookieHeaders(cookieHeader),
        ...csrfHeaders(originHeader),
        "Content-Type": "application/json",
      },
      body: "{}",
      redirect: "manual",
    });
  } catch {
    return { kind: "unauthenticated" };
  }
  if (response.status === 403) return await classify403(response);
  const authFailure = orgAuthFailureFromStatus(response.status);
  if (authFailure) return authFailure;
  if (response.status === 404) return { kind: "batch_not_found" };
  let body: { error?: string } & Partial<ImportBatch> = {};
  try {
    body = await response.json();
  } catch {
    return { kind: "wrong_state" };
  }
  if (response.status === 200) return { kind: "ok", batch: body as ImportBatch };
  if (body.error === "staging_expired") return { kind: "staging_expired" };
  return { kind: "wrong_state" };
}
