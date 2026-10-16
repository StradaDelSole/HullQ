// SLICE-0088 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises the broker inventory export client's real-HTTP-status
// classification against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/inventory/export/...` routes --
// mirrors the existing `importIntakeApi.test.ts` discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  downloadExport,
  EXPORT_FORMATS,
  fetchExportPreflight,
  type ExportSelection,
} from "../brokerInventoryExportApi.ts";

async function withServer(
  handler: http.RequestListener,
  run: (baseUrl: string) => Promise<void>,
): Promise<void> {
  const server = http.createServer(handler);
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    if (address === null || typeof address === "string") {
      throw new Error("expected a bound TCP address");
    }
    await run(`http://127.0.0.1:${address.port}`);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
}

const _selection: ExportSelection = { draftIds: ["DRAFT-1"], nativeListingIds: [] };

test("EXPORT_FORMATS never includes XLSB (2026-10-16 amendment)", () => {
  assert.equal(EXPORT_FORMATS.includes("XLSB" as never), false);
  assert.equal(EXPORT_FORMATS.length, 7);
});

test("fetchExportPreflight: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          rows: [{ field_states: {}, formats: {} }],
        }),
      );
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", "hullq_session=abc", null, _selection);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") assert.equal(result.rows.length, 1);
    },
  );
});

test("fetchExportPreflight: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", null, null, _selection);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchExportPreflight: 403 publisher_role_required body is classified", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publisher_role_required" }));
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", "hullq_session=abc", null, _selection);
      assert.equal(result.kind, "publisher_role_required");
    },
  );
});

test("fetchExportPreflight: 400 unknown_item is classified (no existence oracle leak)", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "unknown_item" }));
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", "hullq_session=abc", null, _selection);
      assert.equal(result.kind, "unknown_item");
    },
  );
});

test("downloadExport: 200 bytes/content-type/filename are surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="hullq-inventory-export.csv"',
      });
      res.end("export_id,status\n");
    },
    async (baseUrl) => {
      const result = await downloadExport(baseUrl, "ORG-1", "hullq_session=abc", null, _selection, "CSV");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.contentType, "text/csv; charset=utf-8");
        assert.equal(result.filename, "hullq-inventory-export.csv");
        assert.equal(Buffer.from(result.bytes).toString("utf-8"), "export_id,status\n");
      }
    },
  );
});

test("downloadExport: 429 is surfaced as export_busy", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(429, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "export_busy" }));
    },
    async (baseUrl) => {
      const result = await downloadExport(baseUrl, "ORG-1", "hullq_session=abc", null, _selection, "CSV");
      assert.equal(result.kind, "export_busy");
    },
  );
});

test("downloadExport: 400 invalid_format is surfaced", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_format" }));
    },
    async (baseUrl) => {
      const result = await downloadExport(
        baseUrl,
        "ORG-1",
        "hullq_session=abc",
        null,
        _selection,
        // deliberately invalid at the type level too -- cast mirrors a
        // hostile/unexpected runtime value
        "XLSB" as unknown as "CSV",
      );
      assert.equal(result.kind, "invalid_format");
    },
  );
});
