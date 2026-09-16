// SLICE-0054 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises each ownerDirectDraftApi.ts function's real-HTTP-status
// classification against a tiny local http server standing in for
// FastAPI's `/api/owner-direct/drafts...` routes, and asserts the exact
// CSRF headers (`Origin` + `X-HullQ-Requested-With`) this module attaches
// to every state-changing (POST/PUT) call -- the SLICE-0054 contract §9
// proxy behavior this module exists to implement.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  createOwnerDirectDraft,
  fetchOwnerDirectDraft,
  fetchOwnerDirectDrafts,
  updateOwnerDirectDraft,
} from "../ownerDirectDraftApi.ts";

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

function readBody(req: http.IncomingMessage): Promise<string> {
  return new Promise((resolve) => {
    let data = "";
    req.on("data", (chunk) => {
      data += chunk;
    });
    req.on("end", () => resolve(data));
  });
}

test("fetchOwnerDirectDrafts: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ drafts: [{ draft_id: "d1", version: 1 }] }));
    },
    async (baseUrl) => {
      const result = await fetchOwnerDirectDrafts(baseUrl, "hullq_session=abc");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.length, 1);
        assert.equal(result.data[0]?.draft_id, "d1");
      }
    },
  );
});

test("fetchOwnerDirectDrafts: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOwnerDirectDrafts(baseUrl, null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchOwnerDirectDrafts: cookie header is forwarded verbatim", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers.cookie, "hullq_session=abc");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ drafts: [] }));
    },
    async (baseUrl) => {
      await fetchOwnerDirectDrafts(baseUrl, "hullq_session=abc");
    },
  );
});

test("fetchOwnerDirectDraft: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchOwnerDirectDraft(baseUrl, "unknown-id", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("createOwnerDirectDraft: sends the fixed CSRF header and forwards Origin", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "owner-direct-draft-v1");
      assert.equal(req.headers.origin, "https://hullq.example");
      res.writeHead(201, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ draft_id: "d-new", version: 1 }));
    },
    async (baseUrl) => {
      const result = await createOwnerDirectDraft(baseUrl, null, "https://hullq.example");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.draft_id, "d-new");
      }
    },
  );
});

test("createOwnerDirectDraft: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await createOwnerDirectDraft(baseUrl, null, "https://hullq.example");
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("createOwnerDirectDraft: 403 (CSRF rejection) is surfaced as invalid", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403);
      res.end();
    },
    async (baseUrl) => {
      const result = await createOwnerDirectDraft(baseUrl, null, "https://hullq.example");
      assert.equal(result.kind, "invalid");
    },
  );
});

test("updateOwnerDirectDraft: sends expected_version and payload, forwards CSRF headers", async () => {
  await withServer(
    async (req, res) => {
      assert.equal(req.method, "PUT");
      assert.equal(req.headers["x-hullq-requested-with"], "owner-direct-draft-v1");
      assert.equal(req.headers.origin, "https://hullq.example");
      const body = JSON.parse(await readBody(req)) as Record<string, unknown>;
      assert.equal(body.expected_version, 3);
      assert.equal(body["physical_boat.boat_name"], "Sea Breeze");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ draft_id: "d1", version: 4 }));
    },
    async (baseUrl) => {
      const result = await updateOwnerDirectDraft(baseUrl, "d1", null, "https://hullq.example", 3, {
        "physical_boat.boat_name": "Sea Breeze",
      });
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.version, 4);
      }
    },
  );
});

test("updateOwnerDirectDraft: 409 is surfaced as conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409);
      res.end();
    },
    async (baseUrl) => {
      const result = await updateOwnerDirectDraft(baseUrl, "d1", null, "https://hullq.example", 1, {});
      assert.equal(result.kind, "conflict");
    },
  );
});

test("updateOwnerDirectDraft: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await updateOwnerDirectDraft(baseUrl, "d1", null, "https://hullq.example", 1, {});
      assert.equal(result.kind, "not_found");
    },
  );
});

test("updateOwnerDirectDraft: 400 is surfaced as invalid", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400);
      res.end();
    },
    async (baseUrl) => {
      const result = await updateOwnerDirectDraft(baseUrl, "d1", null, "https://hullq.example", 1, {});
      assert.equal(result.kind, "invalid");
    },
  );
});

test("network failure collapses to unauthenticated rather than throwing", async () => {
  // Port 1 is reserved and will refuse the connection immediately.
  const result = await fetchOwnerDirectDrafts("http://127.0.0.1:1", null);
  assert.equal(result.kind, "unauthenticated");
});
