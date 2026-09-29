// SLICE-0070: proof that the buyer contact proxy route
// (`pages/listings/[native_listing_id]/contact.ts`) enforces its
// Content-Length bound before forwarding, forwards Cookie/Origin/CSRF
// headers and the JSON body to FastAPI unmodified, and surfaces every
// bounded upstream outcome verbatim -- mirrors `mediaUploadProxy.test.ts`'s
// identical local-http-server discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import type { APIContext } from "astro";

import { POST } from "../../pages/listings/[native_listing_id]/contact.ts";

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

function fakeContext(
  request: Request,
  params: Record<string, string | undefined> = { native_listing_id: "NL-1" },
): APIContext {
  return { params, request } as unknown as APIContext;
}

test("POST contact: missing native_listing_id param is rejected 404", async () => {
  const request = new Request("http://web.test/contact", { method: "POST" });
  const response = await POST(fakeContext(request, {}));
  assert.equal(response.status, 404);
});

test("POST contact: missing Content-Length is rejected 411 before any body read", async () => {
  const request = new Request("http://web.test/contact", {
    method: "POST",
    body: JSON.stringify({ name: "A" }),
  });
  const response = await POST(fakeContext(request));
  assert.equal(response.status, 411);
  const body = (await response.json()) as { error?: string };
  assert.equal(body.error, "length_required");
});

test("POST contact: Content-Length above the bound is rejected 413", async () => {
  const request = new Request("http://web.test/contact", {
    method: "POST",
    headers: { "content-length": "20001" },
    body: JSON.stringify({ name: "A" }),
  });
  const response = await POST(fakeContext(request));
  assert.equal(response.status, 413);
  const body = (await response.json()) as { error?: string };
  assert.equal(body.error, "payload_too_large");
});

test("POST contact: forwards the body and Cookie/Origin/CSRF headers to FastAPI unmodified", async () => {
  let receivedBody = Buffer.alloc(0);
  let receivedHeaders: http.IncomingHttpHeaders = {};

  await withServer(
    (req, res) => {
      receivedHeaders = req.headers;
      const chunks: Buffer[] = [];
      req.on("data", (chunk: Buffer) => chunks.push(chunk));
      req.on("end", () => {
        receivedBody = Buffer.concat(chunks);
        res.writeHead(201, { "Content-Type": "application/json" });
        res.end(
          JSON.stringify({
            status: "CREATED",
            lead_id: "LEAD-1",
            received_at: "2026-09-29T00:00:00Z",
          }),
        );
      });
    },
    async (baseUrl) => {
      process.env.HULLQ_API_BASE_URL = baseUrl;
      try {
        const payload = JSON.stringify({
          submission_operation_id: "OP-1",
          name: "Jane Buyer",
          email: "jane@example.com",
          message: "Interested in this boat.",
        });
        const request = new Request("http://web.test/contact", {
          method: "POST",
          headers: {
            "content-length": String(Buffer.byteLength(payload)),
            cookie: "hullq_session=abc",
            origin: "https://web.example",
          },
          body: payload,
        });

        const response = await POST(fakeContext(request));
        assert.equal(response.status, 201);
        const body = (await response.json()) as { lead_id?: string };
        assert.equal(body.lead_id, "LEAD-1");

        assert.equal(receivedBody.toString("utf8"), payload);
        assert.equal(
          receivedHeaders["x-hullq-requested-with"],
          "marketplace-buyer-lead-v1",
        );
        assert.equal(receivedHeaders.origin, "https://web.example");
        assert.equal(receivedHeaders.cookie, "hullq_session=abc");
      } finally {
        delete process.env.HULLQ_API_BASE_URL;
      }
    },
  );
});

test("POST contact: forwards an anonymous request with no Cookie header", async () => {
  let receivedHeaders: http.IncomingHttpHeaders = {};

  await withServer(
    (req, res) => {
      receivedHeaders = req.headers;
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "listing_not_available" }));
    },
    async (baseUrl) => {
      process.env.HULLQ_API_BASE_URL = baseUrl;
      try {
        const payload = JSON.stringify({
          submission_operation_id: "OP-2",
          name: "Jane Buyer",
          email: "jane@example.com",
          message: "Interested in this boat.",
        });
        const request = new Request("http://web.test/contact", {
          method: "POST",
          headers: { "content-length": String(Buffer.byteLength(payload)) },
          body: payload,
        });

        const response = await POST(fakeContext(request));
        assert.equal(response.status, 404);
        assert.equal(receivedHeaders.cookie, undefined);
      } finally {
        delete process.env.HULLQ_API_BASE_URL;
      }
    },
  );
});

test("POST contact: an unreachable upstream is surfaced as a 502 service_error", async () => {
  const payload = JSON.stringify({ submission_operation_id: "OP-3" });
  const request = new Request("http://web.test/contact", {
    method: "POST",
    headers: { "content-length": String(Buffer.byteLength(payload)) },
    body: payload,
  });
  process.env.HULLQ_API_BASE_URL = "http://127.0.0.1:1"; // reserved, always refused
  try {
    const response = await POST(fakeContext(request));
    assert.equal(response.status, 502);
    const body = (await response.json()) as { error?: string };
    assert.equal(body.error, "service_error");
  } finally {
    delete process.env.HULLQ_API_BASE_URL;
  }
});
