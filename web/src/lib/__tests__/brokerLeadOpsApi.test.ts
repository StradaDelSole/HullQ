// SLICE-0071 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `brokerLeadOpsApi.ts`'s real-HTTP-status classification against
// a tiny local http server standing in for FastAPI's broker Lead
// operations/notification-config routes -- mirrors the existing
// `brokerInventoryApi.test.ts` discipline. Specifically covers the
// notification-config 403 disambiguation (`mfa_required` vs
// `role_required`), which both share HTTP 403 and are distinguished only by
// response body shape.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  fetchLeadDetail,
  fetchOrganizationLeadInbox,
  setLeadStatus,
  setNotificationConfig,
} from "../brokerLeadOpsApi.ts";

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

test("fetchOrganizationLeadInbox: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ items: [] }));
    },
    async (baseUrl) => {
      const result = await fetchOrganizationLeadInbox(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchLeadDetail: 404 is surfaced as lead_not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchLeadDetail(baseUrl, "ORG-1", "LEAD-1", "hullq_session=abc");
      assert.equal(result.kind, "lead_not_found");
    },
  );
});

test("setLeadStatus: 409 is surfaced as version_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "version_conflict" }));
    },
    async (baseUrl) => {
      const result = await setLeadStatus(baseUrl, "ORG-1", "LEAD-1", "IN_PROGRESS", 0, null, null);
      assert.equal(result.kind, "version_conflict");
    },
  );
});

test("setNotificationConfig: 403 role_required body is distinguished from mfa_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "role_required" }));
    },
    async (baseUrl) => {
      const result = await setNotificationConfig(baseUrl, "ORG-1", "owner@example.com", 0, null, null);
      assert.equal(result.kind, "role_required");
    },
  );
});

test("setNotificationConfig: 403 mfa_required body is distinguished from role_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await setNotificationConfig(baseUrl, "ORG-1", "owner@example.com", 0, null, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("setNotificationConfig: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ notification_email: "owner@example.com", version: 1 }));
    },
    async (baseUrl) => {
      const result = await setNotificationConfig(baseUrl, "ORG-1", "owner@example.com", 0, null, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.notification_email, "owner@example.com");
      }
    },
  );
});
