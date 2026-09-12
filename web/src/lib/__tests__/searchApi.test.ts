// SLICE-0051 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchSearch`'s real-HTTP-status classification against a tiny
// local http server standing in for FastAPI's `/api/search/{locale}` route:
// a 308 with a Location header must be surfaced (not silently followed), a
// 400 body must be parsed as `invalid`, a 200 body as `result`, and a
// connection failure must collapse to `status: 502` rather than throwing.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { fetchSearch } from "../searchApi.ts";

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

test("fetchSearch: 200 result body is surfaced as `result`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ locale: "en", active_requirement: null }));
    },
    async (baseUrl) => {
      const response = await fetchSearch(baseUrl, "en", "");
      assert.equal(response.status, 200);
      assert.deepEqual(response.result, { locale: "en", active_requirement: null });
      assert.equal(response.location, null);
      assert.equal(response.invalid, null);
    },
  );
});

test("fetchSearch: 308 is not followed and Location is readable", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(308, { Location: "/de/search?draft_max=1.6" });
      res.end();
    },
    async (baseUrl) => {
      const response = await fetchSearch(baseUrl, "de", "draft_max=1.600");
      assert.equal(response.status, 308);
      assert.equal(response.location, "/de/search?draft_max=1.6");
      assert.equal(response.result, null);
    },
  );
});

test("fetchSearch: 400 body is surfaced as `invalid`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_search_request", message: "nope" }));
    },
    async (baseUrl) => {
      const response = await fetchSearch(baseUrl, "de", "draft_max=1e0");
      assert.equal(response.status, 400);
      assert.deepEqual(response.invalid, { error: "invalid_search_request", message: "nope" });
      assert.equal(response.result, null);
    },
  );
});

test("fetchSearch: network failure collapses to status 502, never throws", async () => {
  // Port 1 is reserved and nothing listens there.
  const response = await fetchSearch("http://127.0.0.1:1", "en", "");
  assert.equal(response.status, 502);
  assert.equal(response.result, null);
  assert.equal(response.invalid, null);
  assert.equal(response.location, null);
});
