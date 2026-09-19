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

// Independent review Finding 5 (2026-09-19): `FormData.set` cannot produce a
// duplicated field (it overwrites), so the duplicate/unknown-field tests
// below need `.append` to construct the exact ambiguous/tampered raw form
// shapes `FormData.get` alone would silently resolve.
function formDataAppending(pairs: [string, string][]): FormData {
  const data = new FormData();
  for (const [key, value] of pairs) {
    data.append(key, value);
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

// Independent review Finding 2 (2026-09-19): the sensitivity form's
// `current_*` hidden fields are never buyer-editable -- SearchPageBody.astro
// only ever renders one for a genuinely active criterion, always with its
// exact canonical value. A *present* empty value can therefore only be
// tampered/malformed current state, never "criterion inactive", and MUST
// reach FastAPI unchanged so the accepted application boundary rejects it
// with 400 -- silently omitting it would instead narrow the comparison to a
// different, unintended current requirement.
test("loadSearchSensitivityPageData: a present empty current_keel_configuration field is forwarded unchanged, never omitted", async () => {
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
  assert.deepEqual(parsed.current, { draft_max: "1.6", keel_configuration: "" });
});

test("loadSearchSensitivityPageData: an absent current_keel_configuration field stays absent (genuine 'criterion inactive')", async () => {
  let capturedRaw = "";
  await withServer(
    (req, res) => {
      req.on("data", (chunk) => {
        capturedRaw += chunk;
      });
      req.on("end", () => {
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            locale: "en",
            current_requirement: { draft_max: "1.6" },
            alternative_requirement: { draft_max: "1.7" },
            changed_criterion: "draft_max",
            current_confirmed_match_count: 0,
            alternative_confirmed_match_count: 0,
            newly_confirmed_match_count: 0,
            no_longer_confirmed_match_count: 0,
            current_insufficient_data_count: 0,
            alternative_insufficient_data_count: 0,
            alternative_search_path: "/en/search?draft_max=1.7",
          }),
        );
      });
    },
    async (baseUrl) => {
      await loadSearchSensitivityPageData(
        baseUrl,
        "en",
        formData({
          current_draft_max: "1.6",
          changed_criterion: "draft_max",
          changed_value: "1.7",
        }),
      );
    },
  );
  const parsed = JSON.parse(capturedRaw) as { current: Record<string, string> };
  assert.deepEqual(parsed.current, { draft_max: "1.6" });
  assert.ok(!("keel_configuration" in parsed.current));
});

// ---------------------------------------------------------------------------
// Independent review Finding 5 (2026-09-19): structural form-shape
// validation. `FormData.get(...)` alone silently resolves a duplicated field
// to its first value and silently drops an unknown field -- both must
// instead fail closed as `invalid`, before any network access.
// ---------------------------------------------------------------------------

async function assertMalformedNeverCallsBackend(fields: [string, string][]): Promise<void> {
  let calls = 0;
  await withServer(
    (_req, res) => {
      calls += 1;
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("{}");
    },
    async (baseUrl) => {
      const data = await loadSearchSensitivityPageData(baseUrl, "en", formDataAppending(fields));
      assert.equal(data.kind, "invalid");
      if (data.kind === "invalid") {
        assert.equal(data.message, null);
      }
      assert.equal(calls, 0, "a structurally malformed post must never call FastAPI");
    },
  );
}

test("loadSearchSensitivityPageData: duplicate current_draft_max is invalid, FastAPI not called", async () => {
  await assertMalformedNeverCallsBackend([
    ["current_draft_max", "1.6"],
    ["current_draft_max", "1.2"],
    ["changed_criterion", "draft_max"],
    ["changed_value", "1.7"],
  ]);
});

test("loadSearchSensitivityPageData: duplicate current_keel_configuration is invalid, FastAPI not called", async () => {
  await assertMalformedNeverCallsBackend([
    ["current_keel_configuration", "FIN"],
    ["current_keel_configuration", "TWIN_KEEL"],
    ["changed_criterion", "keel_configuration"],
    ["changed_value", "FIN"],
  ]);
});

test("loadSearchSensitivityPageData: duplicate changed_criterion is invalid, FastAPI not called", async () => {
  await assertMalformedNeverCallsBackend([
    ["current_draft_max", "1.6"],
    ["changed_criterion", "draft_max"],
    ["changed_criterion", "keel_configuration"],
    ["changed_value", "1.7"],
  ]);
});

test("loadSearchSensitivityPageData: duplicate changed_value is invalid, FastAPI not called", async () => {
  await assertMalformedNeverCallsBackend([
    ["current_draft_max", "1.6"],
    ["changed_criterion", "draft_max"],
    ["changed_value", "1.7"],
    ["changed_value", "1.2"],
  ]);
});

test("loadSearchSensitivityPageData: an unknown field (current_foo) is invalid, FastAPI not called", async () => {
  await assertMalformedNeverCallsBackend([
    ["current_draft_max", "1.6"],
    ["current_foo", "bar"],
    ["changed_criterion", "draft_max"],
    ["changed_value", "1.7"],
  ]);
});
