// SLICE-0075 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `brokerPerformanceApi.ts`'s real-HTTP-status classification
// against a tiny local http server standing in for FastAPI's broker
// performance/funnel-snapshot route -- mirrors the existing
// `brokerLeadOpsApi.test.ts` discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { fetchOrganizationPerformance } from "../brokerPerformanceApi.ts";

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

test("fetchOrganizationPerformance: 200 body is surfaced as ok", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.url, "/api/broker/organizations/ORG-1/performance?window=LAST_7_DAYS");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          window: "LAST_7_DAYS",
          window_start: "2026-09-24T00:00:00+00:00",
          window_end: "2026-10-01T00:00:00+00:00",
          public_listing_views: 3,
          leads_received: 1,
          leads_contacted: 0,
          leads_closed: 0,
          sold_outcomes: 0,
          sold_outcomes_with_known_source: 0,
          sold_outcomes_with_unknown_source: 0,
          acquisition_source_breakdown: { UNKNOWN: 1 },
          first_contact_latency_known_count: 0,
          first_contact_latency_unknown_count: 1,
          median_first_contact_latency_seconds: null,
          listings: [],
        }),
      );
    },
    async (baseUrl) => {
      const result = await fetchOrganizationPerformance(baseUrl, "ORG-1", "hullq_session=abc", "LAST_7_DAYS");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.public_listing_views, 3);
        assert.equal(result.data.median_first_contact_latency_seconds, null);
      }
    },
  );
});

test("fetchOrganizationPerformance: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOrganizationPerformance(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchOrganizationPerformance: 403 is surfaced as mfa_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await fetchOrganizationPerformance(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchOrganizationPerformance: 400 is surfaced as invalid_window", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_window" }));
    },
    async (baseUrl) => {
      const result = await fetchOrganizationPerformance(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "invalid_window");
    },
  );
});

test("fetchOrganizationPerformance: network failure is surfaced as service_error", async () => {
  const result = await fetchOrganizationPerformance("http://127.0.0.1:1", "ORG-1", null);
  assert.equal(result.kind, "service_error");
});
