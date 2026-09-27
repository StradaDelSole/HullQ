// SLICE-0068 independent review Finding D: proof that the streaming upload
// proxy route (`pages/.../media/upload.ts`) enforces its Content-Length
// bound *before* ever reading the request body, forwards the body/headers
// through to FastAPI unmodified, and never buffers the request via
// `arrayBuffer()`/`text()`/`json()`/`formData()` -- mirrors
// `mediaGalleryApi.test.ts`'s identical local-http-server discipline, but
// imports the real route handler directly rather than a `lib/*.ts` helper.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import type { APIContext } from "astro";

import { POST } from "../../pages/broker/organizations/[organization_id]/inventory/[native_listing_id]/media/upload.ts";

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

function streamFromBytes(bytes: Uint8Array): ReadableStream<Uint8Array> {
  let sent = false;
  return new ReadableStream({
    pull(controller) {
      if (sent) {
        controller.close();
        return;
      }
      sent = true;
      controller.enqueue(bytes);
    },
  });
}

function fakeContext(
  request: Request,
  params: Record<string, string | undefined> = { organization_id: "ORG-1", native_listing_id: "NL-1" },
): APIContext {
  return { params, request } as unknown as APIContext;
}

test("POST media/upload: missing Content-Length is rejected 411 before any body read", async () => {
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      controller.enqueue(new Uint8Array([1]));
      controller.close();
    },
  });
  const request = new Request("http://web.test/upload", {
    method: "POST",
    body: stream,
    duplex: "half",
  } as RequestInit & { duplex: "half" });

  const response = await POST(fakeContext(request));
  assert.equal(response.status, 411);
  // `bodyUsed` only flips once a body-consuming method
  // (`.text()`/`.arrayBuffer()`/`.json()`/`.formData()`/a reader `.read()`)
  // is actually invoked -- proving this route's own code never touched the
  // body before rejecting on the header alone. (Node's `Request`
  // implementation may eagerly pull the underlying stream once as part of
  // its own internal bookkeeping when constructing this test double; that
  // is an artifact of the test harness, not of this route's handler, so it
  // is not what this assertion checks.)
  assert.equal(request.bodyUsed, false);
  const body = (await response.json()) as { error?: string };
  assert.equal(body.error, "length_required");
});

test("POST media/upload: Content-Length above the bound is rejected 413 before any body read", async () => {
  const stream = new ReadableStream<Uint8Array>({
    pull(controller) {
      controller.enqueue(new Uint8Array([1]));
      controller.close();
    },
  });
  const request = new Request("http://web.test/upload", {
    method: "POST",
    headers: { "content-length": "20000000" },
    body: stream,
    duplex: "half",
  } as RequestInit & { duplex: "half" });

  const response = await POST(fakeContext(request));
  assert.equal(response.status, 413);
  assert.equal(request.bodyUsed, false);
  const body = (await response.json()) as { error?: string };
  assert.equal(body.error, "payload_too_large");
});

test("POST media/upload: missing route params is rejected 404", async () => {
  const request = new Request("http://web.test/upload", { method: "POST" });
  const response = await POST(fakeContext(request, {}));
  assert.equal(response.status, 404);
});

test("POST media/upload: streams the body through and forwards headers to FastAPI unmodified", async () => {
  const payload = new Uint8Array(64 * 1024).fill(7);
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
            outcome: "CREATED",
            media_asset_id: "MA-1",
            media_placement_id: "MP-1",
            gallery_version: 1,
          }),
        );
      });
    },
    async (baseUrl) => {
      process.env.HULLQ_API_BASE_URL = baseUrl;
      try {
        const request = new Request("http://web.test/upload", {
          method: "POST",
          headers: {
            "content-length": String(payload.byteLength),
            "content-type": "image/jpeg",
            cookie: "hullq_session=abc",
            origin: "https://web.example",
            "x-hullq-rights-confirmed": "true",
            "x-hullq-source-reference": "Photographed by ACME",
          },
          body: streamFromBytes(payload),
          duplex: "half",
        } as RequestInit & { duplex: "half" });

        const response = await POST(fakeContext(request));
        assert.equal(response.status, 201);
        const body = (await response.json()) as { media_asset_id?: string };
        assert.equal(body.media_asset_id, "MA-1");

        assert.equal(receivedBody.length, payload.byteLength);
        assert.equal(receivedHeaders["x-hullq-requested-with"], "marketplace-media-gallery-v1");
        assert.equal(receivedHeaders.origin, "https://web.example");
        assert.equal(receivedHeaders.cookie, "hullq_session=abc");
        assert.equal(receivedHeaders["x-hullq-rights-confirmed"], "true");
        assert.equal(receivedHeaders["x-hullq-source-reference"], "Photographed by ACME");
        assert.equal(receivedHeaders["content-type"], "image/jpeg");
      } finally {
        delete process.env.HULLQ_API_BASE_URL;
      }
    },
  );
});

test("POST media/upload: never calls arrayBuffer/text/json/formData on the incoming request", async () => {
  const payload = new Uint8Array([9, 9, 9]);
  await withServer(
    (_req, res) => {
      res.writeHead(201, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          outcome: "CREATED",
          media_asset_id: "MA-1",
          media_placement_id: "MP-1",
          gallery_version: 1,
        }),
      );
    },
    async (baseUrl) => {
      process.env.HULLQ_API_BASE_URL = baseUrl;
      try {
        const request = new Request("http://web.test/upload", {
          method: "POST",
          headers: { "content-length": String(payload.byteLength) },
          body: streamFromBytes(payload),
          duplex: "half",
        } as RequestInit & { duplex: "half" });

        const forbidden = () => {
          throw new Error("must not buffer the request body");
        };
        // Independent review Finding D's core proof: if the route handler
        // ever called one of these to read the body itself (rather than
        // forwarding the live `request.body` stream), this test fails hard.
        Object.assign(request, {
          arrayBuffer: forbidden,
          text: forbidden,
          json: forbidden,
          formData: forbidden,
        });

        const response = await POST(fakeContext(request));
        assert.equal(response.status, 201);
      } finally {
        delete process.env.HULLQ_API_BASE_URL;
      }
    },
  );
});

test("POST media/upload: an unreachable upstream is surfaced as a 502 service_error", async () => {
  const request = new Request("http://web.test/upload", {
    method: "POST",
    headers: { "content-length": "1" },
    body: streamFromBytes(new Uint8Array([1])),
    duplex: "half",
  } as RequestInit & { duplex: "half" });
  process.env.HULLQ_API_BASE_URL = "http://127.0.0.1:1"; // reserved, always refused
  try {
    const response = await POST(fakeContext(request));
    assert.equal(response.status, 502);
  } finally {
    delete process.env.HULLQ_API_BASE_URL;
  }
});
