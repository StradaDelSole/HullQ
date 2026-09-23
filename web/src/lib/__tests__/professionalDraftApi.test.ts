// SLICE-0061 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises the professional listing draft client's real-HTTP-status
// classification against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/drafts...` routes -- mirrors
// the existing `brokerInventoryApi.test.ts` / `ownerDirectDraftApi.test.ts`
// discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  createProfessionalDraft,
  fetchProfessionalDraft,
  fetchProfessionalDrafts,
  updateProfessionalDraft,
} from "../professionalDraftApi.ts";

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

const _sampleDraft = {
  draft_id: "DRAFT-1",
  owner_organization_id: "ORG-1",
  version: 1,
  broker_listing_reference: null,
  "listing_offer.broker_description": null,
  created_at: "2026-01-01T00:00:00+00:00",
  updated_at: "2026-01-01T00:00:00+00:00",
};

test("fetchProfessionalDrafts: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ drafts: [_sampleDraft] }));
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", "hullq_session=abc");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.drafts.length, 1);
        assert.equal(result.data.drafts[0]?.draft_id, "DRAFT-1");
        assert.equal(result.data.next_cursor, undefined);
      }
    },
  );
});

test("fetchProfessionalDrafts: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchProfessionalDrafts: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-UNKNOWN", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchProfessionalDrafts: 403 with mfa_required body is surfaced as mfa_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchProfessionalDrafts: 403 with publisher_role_required body is distinguished from mfa_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publisher_role_required" }));
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "publisher_role_required");
    },
  );
});

test("fetchProfessionalDrafts: 400 is surfaced as invalid_cursor", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", null, { cursor: "garbage" });
      assert.equal(result.kind, "invalid_cursor");
    },
  );
});

test("fetchProfessionalDrafts: unexpected 500 is surfaced as service_error, not ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchProfessionalDrafts: cursor and page_size are forwarded as query params", async () => {
  await withServer(
    (req, res) => {
      const url = new URL(req.url ?? "", "http://localhost");
      assert.equal(url.searchParams.get("cursor"), "abc123");
      assert.equal(url.searchParams.get("page_size"), "10");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ drafts: [] }));
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDrafts(baseUrl, "ORG-1", null, {
        cursor: "abc123",
        pageSize: 10,
      });
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchProfessionalDrafts: cookie header is forwarded verbatim", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers.cookie, "hullq_session=abc");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ drafts: [] }));
    },
    async (baseUrl) => {
      await fetchProfessionalDrafts(baseUrl, "ORG-1", "hullq_session=abc");
    },
  );
});

test("network failure collapses to service_error rather than throwing", async () => {
  // Port 1 is reserved and will refuse the connection immediately.
  const result = await fetchProfessionalDrafts("http://127.0.0.1:1", "ORG-1", null);
  assert.equal(result.kind, "service_error");
});

test("fetchProfessionalDraft: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify(_sampleDraft));
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDraft(baseUrl, "ORG-1", "DRAFT-1", null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.draft_id, "DRAFT-1");
      }
    },
  );
});

test("fetchProfessionalDraft: 404 (foreign or unknown draft) is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchProfessionalDraft(baseUrl, "ORG-1", "DRAFT-UNKNOWN", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("createProfessionalDraft: sends the fixed CSRF header and forwards Origin", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "professional-listing-draft-v1");
      assert.equal(req.headers.origin, "https://web.example");
      res.writeHead(201, { "Content-Type": "application/json" });
      res.end(JSON.stringify(_sampleDraft));
    },
    async (baseUrl) => {
      const result = await createProfessionalDraft(
        baseUrl,
        "ORG-1",
        null,
        "https://web.example",
      );
      assert.equal(result.kind, "ok");
    },
  );
});

test("createProfessionalDraft: 403 CSRF rejection with no body is surfaced as mfa_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403);
      res.end();
    },
    async (baseUrl) => {
      const result = await createProfessionalDraft(baseUrl, "ORG-1", null, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("createProfessionalDraft: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await createProfessionalDraft(baseUrl, "ORG-1", null, null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("createProfessionalDraft: 400 invalid payload is surfaced as invalid", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400);
      res.end();
    },
    async (baseUrl) => {
      const result = await createProfessionalDraft(baseUrl, "ORG-1", null, null);
      assert.equal(result.kind, "invalid");
    },
  );
});

test("updateProfessionalDraft: sends expected_version and payload, forwards CSRF headers", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "professional-listing-draft-v1");
      let raw = "";
      req.on("data", (chunk) => {
        raw += chunk;
      });
      req.on("end", () => {
        const body = JSON.parse(raw);
        assert.equal(body.expected_version, 1);
        assert.equal(body["physical_boat.boat_name"], "Sea Breeze");
        assert.equal(body.broker_listing_reference, "REF-1");
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ ..._sampleDraft, version: 2 }));
      });
    },
    async (baseUrl) => {
      const result = await updateProfessionalDraft(
        baseUrl,
        "ORG-1",
        "DRAFT-1",
        null,
        "https://web.example",
        1,
        { "physical_boat.boat_name": "Sea Breeze", broker_listing_reference: "REF-1" },
      );
      assert.equal(result.kind, "ok");
    },
  );
});

test("updateProfessionalDraft: 409 is surfaced as conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409);
      res.end();
    },
    async (baseUrl) => {
      const result = await updateProfessionalDraft(
        baseUrl,
        "ORG-1",
        "DRAFT-1",
        null,
        null,
        1,
        {},
      );
      assert.equal(result.kind, "conflict");
    },
  );
});

test("updateProfessionalDraft: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await updateProfessionalDraft(
        baseUrl,
        "ORG-1",
        "DRAFT-UNKNOWN",
        null,
        null,
        1,
        {},
      );
      assert.equal(result.kind, "not_found");
    },
  );
});

test("updateProfessionalDraft: 400 is surfaced as invalid", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400);
      res.end();
    },
    async (baseUrl) => {
      const result = await updateProfessionalDraft(
        baseUrl,
        "ORG-1",
        "DRAFT-1",
        null,
        null,
        1,
        {},
      );
      assert.equal(result.kind, "invalid");
    },
  );
});
