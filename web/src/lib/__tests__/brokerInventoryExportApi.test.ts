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

test("fetchExportPreflight: 200 body is surfaced as ok with its snapshot_fingerprint", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          snapshot_fingerprint: "abc123",
          rows: [{ field_states: {}, formats: {} }],
        }),
      );
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", "hullq_session=abc", null, _selection);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.rows.length, 1);
        assert.equal(result.snapshotFingerprint, "abc123");
      }
    },
  );
});

test("fetchExportPreflight: forwards an explicit NautixExportProfile", async () => {
  await withServer(
    (req, res) => {
      let raw = "";
      req.on("data", (chunk) => (raw += chunk));
      req.on("end", () => {
        const sent = JSON.parse(raw);
        assert.deepEqual(sent.nautix_profile, {
          account_token: "ACCT-1",
          office_id: "OFFICE-1",
          sale_classes: { "LIST-1": "used" },
        });
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ snapshot_fingerprint: "fp", rows: [] }));
      });
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", "hullq_session=abc", null, _selection, {
        accountToken: "ACCT-1",
        officeId: "OFFICE-1",
        saleClasses: { "LIST-1": "used" },
      });
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchExportPreflight: 400 invalid_nautix_profile is classified", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_nautix_profile" }));
    },
    async (baseUrl) => {
      const result = await fetchExportPreflight(baseUrl, "ORG-1", "hullq_session=abc", null, _selection);
      assert.equal(result.kind, "invalid_nautix_profile");
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

test("downloadExport: 200 bytes/content-type/filename/counts are surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, {
        "Content-Type": "text/csv; charset=utf-8",
        "Content-Disposition": 'attachment; filename="hullq-inventory-export.csv"',
        "X-HullQ-Export-Included-Count": "2",
        "X-HullQ-Export-Rejected-Count": "1",
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
        assert.equal(result.includedCount, 2);
        assert.equal(result.rejectedCount, 1);
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

test("downloadExport: 409 is surfaced as stale_selection", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "stale_selection" }));
    },
    async (baseUrl) => {
      const result = await downloadExport(baseUrl, "ORG-1", "hullq_session=abc", null, _selection, "CSV", {
        expectedSnapshotFingerprint: "stale-fp",
      });
      assert.equal(result.kind, "stale_selection");
    },
  );
});

test("downloadExport: 422 is surfaced as no_exportable_rows (never a silent empty success)", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(422, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "no_exportable_rows" }));
    },
    async (baseUrl) => {
      const result = await downloadExport(baseUrl, "ORG-1", "hullq_session=abc", null, _selection, "NAUTIX");
      assert.equal(result.kind, "no_exportable_rows");
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
