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

// SLICE-0056: keel-only/mixed 200 result bodies carry the SLICE-0055 typed
// `criterion_evidence` shape (contract §D) rather than `resolved_draft_m` --
// `fetchSearch` classifies the real HTTP status only and must pass this
// shape through unmodified, exactly as it already does for the draft-only
// shape above.
test("fetchSearch: keel-only 200 result body (SLICE-0055 typed-evidence shape) is surfaced as `result`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { keel_configuration: "FIN" },
          confirmed_matches: [
            {
              native_listing_id: "NL-1",
              publishing_organization_id: "ORG-1",
              freshness_status: "CONFIRMED",
              last_confirmed_at: null,
              design_evaluation: { design_id: "BD-1", result_class: "CONFIRMED_MATCH", matching_configuration_ids: ["BD-1::baseline"], reason: null },
              design_configuration_evidence: [],
              criterion_evidence: [
                {
                  criterion: { kind: "CATEGORICAL", field: "keel_configuration", equals: "FIN" },
                  field: "keel_configuration",
                  truth: "TRUE",
                  reason: null,
                  explanation: "matched",
                  observed_value: "FIN",
                },
              ],
            },
          ],
          confirmed_match_count: 1,
          insufficient_data_count: 0,
        }),
      );
    },
    async (baseUrl) => {
      const response = await fetchSearch(baseUrl, "en", "keel_configuration=FIN");
      assert.equal(response.status, 200);
      assert.deepEqual(response.result?.active_requirement, { keel_configuration: "FIN" });
      const matches = response.result?.confirmed_matches ?? [];
      assert.equal(matches.length, 1);
      assert.deepEqual((matches[0] as { criterion_evidence: unknown }).criterion_evidence, [
        {
          criterion: { kind: "CATEGORICAL", field: "keel_configuration", equals: "FIN" },
          field: "keel_configuration",
          truth: "TRUE",
          reason: null,
          explanation: "matched",
          observed_value: "FIN",
        },
      ]);
    },
  );
});
