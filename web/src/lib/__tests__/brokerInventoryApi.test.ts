// SLICE-0060 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchOrganizationInventory`'s real-HTTP-status classification
// against a tiny local http server standing in for FastAPI's
// `/api/broker/organizations/{id}/inventory` route -- mirrors the existing
// `ownerDirectDraftApi.test.ts` discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { fetchOrganizationInventory } from "../brokerApi.ts";

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

test("fetchOrganizationInventory: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          items: [
            {
              native_listing_id: "NL-1",
              lifecycle_state: "ACTIVE",
              broker_listing_reference: null,
              created_at: "2026-01-01T00:00:00+00:00",
              offer: { kind: "POA", amount: null, currency: null },
              freshness_status: "CONFIRMED",
              last_confirmed_at: "2026-01-01T00:00:00+00:00",
              is_publicly_listed: true,
            },
          ],
        }),
      );
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.items.length, 1);
        assert.equal(result.data.items[0]?.native_listing_id, "NL-1");
        assert.equal(result.data.next_cursor, undefined);
      }
    },
  );
});

test("fetchOrganizationInventory: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchOrganizationInventory: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-UNKNOWN", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchOrganizationInventory: 403 is surfaced as mfa_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchOrganizationInventory: 400 is surfaced as invalid_cursor", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-1", null, {
        cursor: "garbage",
      });
      assert.equal(result.kind, "invalid_cursor");
    },
  );
});

test("fetchOrganizationInventory: unexpected 500 is surfaced as service_error, not ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchOrganizationInventory: cursor and page_size are forwarded as query params", async () => {
  await withServer(
    (req, res) => {
      const url = new URL(req.url ?? "", "http://localhost");
      assert.equal(url.searchParams.get("cursor"), "abc123");
      assert.equal(url.searchParams.get("page_size"), "10");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ items: [] }));
    },
    async (baseUrl) => {
      const result = await fetchOrganizationInventory(baseUrl, "ORG-1", null, {
        cursor: "abc123",
        pageSize: 10,
      });
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchOrganizationInventory: cookie header is forwarded verbatim", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers.cookie, "hullq_session=abc");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ items: [] }));
    },
    async (baseUrl) => {
      await fetchOrganizationInventory(baseUrl, "ORG-1", "hullq_session=abc");
    },
  );
});

test("network failure collapses to service_error rather than throwing", async () => {
  // Port 1 is reserved and will refuse the connection immediately.
  const result = await fetchOrganizationInventory("http://127.0.0.1:1", "ORG-1", null);
  assert.equal(result.kind, "service_error");
});
