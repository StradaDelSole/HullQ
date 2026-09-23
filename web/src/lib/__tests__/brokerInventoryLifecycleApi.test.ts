// SLICE-0064 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `publishOrganizationListing`/`withdrawOrganizationListing`/
// `reconfirmOrganizationListing`'s real-HTTP-status classification and CSRF
// header/Origin forwarding against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/inventory/{listing}/...` routes
// -- mirrors the existing `brokerInventoryApi.test.ts` /
// `professionalDraftApi.test.ts` discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  publishOrganizationListing,
  reconfirmOrganizationListing,
  withdrawOrganizationListing,
} from "../brokerApi.ts";

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

test("publishOrganizationListing: 200 body is surfaced as ok with transitionId", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "PUBLISHED", transition_id: "PT-1" }));
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "hullq_session=abc",
        "https://web.example",
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.transitionId, "PT-1");
      }
    },
  );
});

test("publishOrganizationListing: sends the fixed CSRF header and forwards Origin", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "professional-inventory-lifecycle-v1");
      assert.equal(req.headers.origin, "https://web.example");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "PUBLISHED", transition_id: "PT-1" }));
    },
    async (baseUrl) => {
      await publishOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "hullq_session=abc",
        "https://web.example",
      );
    },
  );
});

test("publishOrganizationListing: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("publishOrganizationListing: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("publishOrganizationListing: 403 with denied body is surfaced with its reason", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publishing_denied", reason: "PUBLISHER_ROLE_REQUIRED" }));
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "denied");
      if (result.kind === "denied") {
        assert.equal(result.reason, "PUBLISHER_ROLE_REQUIRED");
      }
    },
  );
});

test("publishOrganizationListing: 403 with mfa_required body is surfaced as mfa_required, not denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("publishOrganizationListing: 403 with an unrecognized body (e.g. CSRF rejection) is surfaced as service_error, never denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "csrf validation failed" }));
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("publishOrganizationListing: 403 with an unparseable body is surfaced as service_error, never denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "text/plain" });
      res.end("not json");
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("publishOrganizationListing: 422 is surfaced as incomplete_listing", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(422, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "incomplete_listing" }));
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "incomplete_listing");
    },
  );
});

test("publishOrganizationListing: 409 is surfaced as state_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "state_conflict" }));
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "state_conflict");
    },
  );
});

test("publishOrganizationListing: unexpected 500 is surfaced as service_error, not ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end();
    },
    async (baseUrl) => {
      const result = await publishOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("publishOrganizationListing: network failure collapses to service_error rather than throwing", async () => {
  // Port 1 is reserved and will refuse the connection immediately.
  const result = await publishOrganizationListing(
    "http://127.0.0.1:1",
    "ORG-1",
    "NL-1",
    null,
    null,
  );
  assert.equal(result.kind, "service_error");
});

test("withdrawOrganizationListing: 200 body is surfaced as ok with transitionId", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "WITHDRAWN", transition_id: "PT-2" }));
    },
    async (baseUrl) => {
      const result = await withdrawOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "hullq_session=abc",
        "https://web.example",
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.transitionId, "PT-2");
      }
    },
  );
});

test("withdrawOrganizationListing: sends the fixed CSRF header and forwards Origin", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "professional-inventory-lifecycle-v1");
      assert.equal(req.headers.origin, "https://web.example");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "WITHDRAWN", transition_id: "PT-2" }));
    },
    async (baseUrl) => {
      await withdrawOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "hullq_session=abc",
        "https://web.example",
      );
    },
  );
});

test("withdrawOrganizationListing: 403 with denied body is surfaced with its reason", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publishing_denied", reason: "ORGANIZATION_UNVERIFIED" }));
    },
    async (baseUrl) => {
      const result = await withdrawOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "denied");
      if (result.kind === "denied") {
        assert.equal(result.reason, "ORGANIZATION_UNVERIFIED");
      }
    },
  );
});

test("withdrawOrganizationListing: 403 with mfa_required body is surfaced as mfa_required, not denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await withdrawOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("withdrawOrganizationListing: 403 with an unrecognized body (e.g. CSRF rejection) is surfaced as service_error, never denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "csrf validation failed" }));
    },
    async (baseUrl) => {
      const result = await withdrawOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("withdrawOrganizationListing: 409 is surfaced as state_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "state_conflict" }));
    },
    async (baseUrl) => {
      const result = await withdrawOrganizationListing(baseUrl, "ORG-1", "NL-1", null, null);
      assert.equal(result.kind, "state_conflict");
    },
  );
});

test("reconfirmOrganizationListing: 200 body is surfaced as ok with occurredAt", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "RECONFIRMED", occurred_at: "2026-01-01T00:00:00+00:00" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        "hullq_session=abc",
        "https://web.example",
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.occurredAt, "2026-01-01T00:00:00+00:00");
      }
    },
  );
});

test("reconfirmOrganizationListing: sends the confirmation_id in the JSON body", async () => {
  await withServer(
    async (req, res) => {
      const chunks: Buffer[] = [];
      for await (const chunk of req) chunks.push(chunk as Buffer);
      const body = JSON.parse(Buffer.concat(chunks).toString("utf-8")) as {
        confirmation_id?: string;
      };
      assert.equal(body.confirmation_id, "11111111-1111-1111-1111-111111111111");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "RECONFIRMED", occurred_at: "2026-01-01T00:00:00+00:00" }));
    },
    async (baseUrl) => {
      await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        null,
        null,
      );
    },
  );
});

test("reconfirmOrganizationListing: 403 with denied body is surfaced with its reason", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publishing_denied", reason: "ORGANIZATION_INELIGIBLE" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        null,
        null,
      );
      assert.equal(result.kind, "denied");
      if (result.kind === "denied") {
        assert.equal(result.reason, "ORGANIZATION_INELIGIBLE");
      }
    },
  );
});

test("reconfirmOrganizationListing: 403 with mfa_required body is surfaced as mfa_required, not denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        null,
        null,
      );
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("reconfirmOrganizationListing: 403 with an unrecognized body (e.g. CSRF rejection) is surfaced as service_error, never denied", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "csrf validation failed" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        null,
        null,
      );
      assert.equal(result.kind, "service_error");
    },
  );
});

test("reconfirmOrganizationListing: 400 is surfaced as invalid_operation_id", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_operation_id" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "not-a-uuid",
        null,
        null,
      );
      assert.equal(result.kind, "invalid_operation_id");
    },
  );
});

test("reconfirmOrganizationListing: 409 with operation_id_conflict body is distinguished from state_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "operation_id_conflict" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        null,
        null,
      );
      assert.equal(result.kind, "operation_id_conflict");
    },
  );
});

test("reconfirmOrganizationListing: 409 with state_conflict body stays state_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "state_conflict" }));
    },
    async (baseUrl) => {
      const result = await reconfirmOrganizationListing(
        baseUrl,
        "ORG-1",
        "NL-1",
        "11111111-1111-1111-1111-111111111111",
        null,
        null,
      );
      assert.equal(result.kind, "state_conflict");
    },
  );
});
