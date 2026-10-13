// SLICE-0083 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises the multi-format import intake client's real-HTTP-status
// classification against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/imports...` routes -- mirrors
// the existing `professionalDraftApi.test.ts` discipline. Independent
// review amendment Finding H: focused frontend regressions for this
// client, which previously had none.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  confirmImportBatch,
  fetchImportBatch,
  fetchImportBatches,
  setImportMapping,
  uploadImport,
} from "../importIntakeApi.ts";

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

const _sampleBatch = {
  import_batch_id: "BATCH-1",
  import_format: "CSV",
  import_source: "Feed1",
  worksheet_name: null,
  snapshot_mode: false,
  status: "AWAITING_MAPPING",
  row_count: 2,
  created_at: "2026-01-01T00:00:00+00:00",
  expires_at: "2026-01-02T00:00:00+00:00",
  rows: [],
};

test("fetchImportBatches: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ batches: [_sampleBatch] }));
    },
    async (baseUrl) => {
      const result = await fetchImportBatches(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.batches.length, 1);
        assert.equal(result.batches[0]?.import_batch_id, "BATCH-1");
      }
    },
  );
});

test("fetchImportBatches: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchImportBatches(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchImportBatches: 403 mfa_required body is classified correctly", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await fetchImportBatches(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchImportBatches: 403 publisher_role_required body is classified correctly", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publisher_role_required" }));
    },
    async (baseUrl) => {
      const result = await fetchImportBatches(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "publisher_role_required");
    },
  );
});

test("fetchImportBatch: 404 is surfaced as not_found (non-enumerating: an unknown Organization and an unknown batch_id are indistinguishable)", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchImportBatch(baseUrl, "ORG-1", "BATCH-UNKNOWN", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("uploadImport: 201 body is surfaced as ok and sets declared headers", async () => {
  let seenHeaders: http.IncomingHttpHeaders = {};
  await withServer(
    (req, res) => {
      seenHeaders = req.headers;
      res.writeHead(201, { "Content-Type": "application/json" });
      res.end(JSON.stringify(_sampleBatch));
    },
    async (baseUrl) => {
      const result = await uploadImport(baseUrl, "ORG-1", "hullq_session=abc", "http://web.test", {
        fileBytes: new TextEncoder().encode("a,b\n1,2\n").buffer,
        declaredFormat: "CSV",
        importSource: "Feed1",
        csvDelimiter: "SEMICOLON",
      });
      assert.equal(result.kind, "ok");
      assert.equal(seenHeaders["x-hullq-import-format"], "CSV");
      assert.equal(seenHeaders["x-hullq-import-source"], "Feed1");
      assert.equal(seenHeaders["x-hullq-csv-delimiter"], "SEMICOLON");
    },
  );
});

test("uploadImport: worksheet_choice_required body is surfaced with worksheet list", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "worksheet_choice_required", worksheets: ["Sheet1", "Sheet2"] }));
    },
    async (baseUrl) => {
      const result = await uploadImport(baseUrl, "ORG-1", "hullq_session=abc", "http://web.test", {
        fileBytes: new ArrayBuffer(0),
        declaredFormat: "XLSX",
        importSource: "Feed1",
      });
      assert.equal(result.kind, "worksheet_choice_required");
      if (result.kind === "worksheet_choice_required") {
        assert.deepEqual(result.worksheets, ["Sheet1", "Sheet2"]);
      }
    },
  );
});

test("setImportMapping: 409 wrong_state is classified correctly", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409);
      res.end();
    },
    async (baseUrl) => {
      const result = await setImportMapping(
        baseUrl,
        "ORG-1",
        "BATCH-1",
        "hullq_session=abc",
        "http://web.test",
        { a: "__ignore__" },
        false,
      );
      assert.equal(result.kind, "wrong_state");
    },
  );
});

test("confirmImportBatch: sends expected_row_count and surfaces stale_confirmation", async () => {
  let seenBody = "";
  await withServer(
    (req, res) => {
      let data = "";
      req.on("data", (chunk) => {
        data += chunk;
      });
      req.on("end", () => {
        seenBody = data;
        res.writeHead(409, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "stale_confirmation" }));
      });
    },
    async (baseUrl) => {
      const result = await confirmImportBatch(
        baseUrl,
        "ORG-1",
        "BATCH-1",
        "hullq_session=abc",
        "http://web.test",
        2,
      );
      assert.equal(result.kind, "stale_confirmation");
      assert.equal(JSON.parse(seenBody).expected_row_count, 2);
    },
  );
});

test("confirmImportBatch: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ ..._sampleBatch, status: "CONFIRMED" }));
    },
    async (baseUrl) => {
      const result = await confirmImportBatch(
        baseUrl,
        "ORG-1",
        "BATCH-1",
        "hullq_session=abc",
        "http://web.test",
        2,
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.batch.status, "CONFIRMED");
      }
    },
  );
});
