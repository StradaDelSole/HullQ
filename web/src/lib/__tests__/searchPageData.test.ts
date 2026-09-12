// SLICE-0051 amendment review, Finding 6: a malformed/ambiguous buyer
// requirement (400) must stay a distinct `invalid` page state from a
// backend/network failure (`unavailable`) -- the buyer must never be told
// their input was wrong when the actual problem is that the service could
// not be reached.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { loadSearchPageData } from "../searchPageData.ts";

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

test("loadSearchPageData: a real 400 is classified as `invalid`, carrying the server message", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_search_request", message: "not a valid draft_max" }));
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1e0");
      assert.equal(data.kind, "invalid");
      if (data.kind === "invalid") {
        assert.equal(data.message, "not a valid draft_max");
      }
    },
  );
});

test("loadSearchPageData: an unreachable backend is classified as `unavailable`, never `invalid`", async () => {
  // Port 1 is reserved and nothing listens there -- a guaranteed connection failure.
  const data = await loadSearchPageData("http://127.0.0.1:1", "en", "draft_max=1.6");
  assert.equal(data.kind, "unavailable");
});

test("loadSearchPageData: an unexpected upstream status (e.g. 500) is classified as `unavailable`, never `invalid`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end("internal server error");
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "unavailable");
    },
  );
});

test("loadSearchPageData: a valid 200 result is classified as `ok`, distinct from both failure states", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "ok");
    },
  );
});
