// SLICE-0057: buyer-requirement-sensitivity page-data boundary. Mirrors
// searchPageData.test.ts's own real-local-HTTP-server style (Finding 6's
// invalid/unavailable distinction applies identically here, contract §11).
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { loadSearchSensitivityPageData } from "../searchSensitivityPageData.ts";

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

function formData(fields: Record<string, string>): FormData {
  const data = new FormData();
  for (const [key, value] of Object.entries(fields)) {
    data.set(key, value);
  }
  return data;
}

test("loadSearchSensitivityPageData: a real 200 result is classified as `ok`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          current_requirement: { draft_max: "1.6" },
          alternative_requirement: { draft_max: "1.7" },
          changed_criterion: "draft_max",
          current_confirmed_match_count: 1,
          alternative_confirmed_match_count: 3,
          newly_confirmed_match_count: 2,
          no_longer_confirmed_match_count: 0,
          current_insufficient_data_count: 0,
          alternative_insufficient_data_count: 0,
          alternative_search_path: "/en/search?draft_max=1.7",
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchSensitivityPageData(
        baseUrl,
        "en",
        formData({ current_draft_max: "1.6", changed_criterion: "draft_max", changed_value: "1.7" }),
      );
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.result.alternative_search_path, "/en/search?draft_max=1.7");
      }
    },
  );
});

test("loadSearchSensitivityPageData: a real 400 is classified as `invalid`, carrying the server message", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({ error: "invalid_sensitivity_request", message: "not a valid request" }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchSensitivityPageData(
        baseUrl,
        "en",
        formData({ current_draft_max: "1.6", changed_criterion: "draft_max", changed_value: "x" }),
      );
      assert.equal(data.kind, "invalid");
      if (data.kind === "invalid") {
        assert.equal(data.message, "not a valid request");
      }
    },
  );
});

test("loadSearchSensitivityPageData: an unreachable backend is classified as `unavailable`, never `invalid`", async () => {
  const data = await loadSearchSensitivityPageData(
    "http://127.0.0.1:1",
    "en",
    formData({ current_draft_max: "1.6", changed_criterion: "draft_max", changed_value: "1.7" }),
  );
  assert.equal(data.kind, "unavailable");
});

test("loadSearchSensitivityPageData: an unexpected upstream status (e.g. 500) is classified as `unavailable`, never `invalid`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end("internal server error");
    },
    async (baseUrl) => {
      const data = await loadSearchSensitivityPageData(
        baseUrl,
        "en",
        formData({ current_draft_max: "1.6", changed_criterion: "draft_max", changed_value: "1.7" }),
      );
      assert.equal(data.kind, "unavailable");
    },
  );
});

test("loadSearchSensitivityPageData: a missing changed_value never reaches the network and is `invalid`", async () => {
  let calls = 0;
  await withServer(
    (_req, res) => {
      calls += 1;
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("{}");
    },
    async (baseUrl) => {
      const data = await loadSearchSensitivityPageData(
        baseUrl,
        "en",
        formData({ current_draft_max: "1.6", changed_criterion: "draft_max" }),
      );
      assert.equal(data.kind, "invalid");
      if (data.kind === "invalid") {
        assert.equal(data.message, null);
      }
      assert.equal(calls, 0, "a malformed post must never call FastAPI");
    },
  );
});

test("loadSearchSensitivityPageData: an empty current_keel_configuration field is omitted, never sent as an empty value", async () => {
  let capturedRaw = "";
  await withServer(
    (req, res) => {
      req.on("data", (chunk) => {
        capturedRaw += chunk;
      });
      req.on("end", () => {
        res.writeHead(400, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ error: "invalid_sensitivity_request", message: "x" }));
      });
    },
    async (baseUrl) => {
      await loadSearchSensitivityPageData(
        baseUrl,
        "en",
        formData({
          current_draft_max: "1.6",
          current_keel_configuration: "",
          changed_criterion: "draft_max",
          changed_value: "1.7",
        }),
      );
    },
  );
  const parsed = JSON.parse(capturedRaw) as { current: Record<string, string> };
  assert.deepEqual(parsed.current, { draft_max: "1.6" });
});
