// SLICE-0078: proof that the broker logout proxy route
// (`pages/broker/logout.ts`) sets FastAPI's fixed CSRF header itself,
// forwards the browser's own Cookie/Origin unmodified, relays FastAPI's
// `Set-Cookie` back to the browser, and redirects to `/broker` -- mirrors
// `buyerLeadContactProxy.test.ts`'s identical local-http-server discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import type { APIContext } from "astro";

import { POST } from "../../pages/broker/logout.ts";

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

function fakeContext(request: Request): APIContext {
  const redirect = (url: string, status?: number) =>
    new Response(null, { status: status ?? 302, headers: { Location: url } });
  return { request, redirect } as unknown as APIContext;
}

test("POST logout: forwards Cookie/Origin and sets the fixed CSRF header, relays Set-Cookie, redirects to /broker", async () => {
  let receivedHeaders: http.IncomingHttpHeaders = {};

  await withServer(
    (req, res) => {
      receivedHeaders = req.headers;
      res.writeHead(200, {
        "Content-Type": "application/json",
        "Set-Cookie": "hullq_session=; Max-Age=0; Path=/",
      });
      res.end(JSON.stringify({ status: "logged_out" }));
    },
    async (baseUrl) => {
      process.env.HULLQ_API_BASE_URL = baseUrl;
      try {
        const request = new Request("http://web.test/broker/logout", {
          method: "POST",
          headers: { cookie: "hullq_session=abc", origin: "https://web.example" },
        });

        const response = await POST(fakeContext(request));
        assert.equal(response.status, 303);
        assert.equal(response.headers.get("location"), "/broker");
        assert.equal(
          response.headers.get("set-cookie"),
          "hullq_session=; Max-Age=0; Path=/",
        );

        assert.equal(receivedHeaders["x-hullq-requested-with"], "broker-logout-v1");
        assert.equal(receivedHeaders.origin, "https://web.example");
        assert.equal(receivedHeaders.cookie, "hullq_session=abc");
      } finally {
        delete process.env.HULLQ_API_BASE_URL;
      }
    },
  );
});

test("POST logout: forwards a request with no Cookie/Origin header without inventing one", async () => {
  let receivedHeaders: http.IncomingHttpHeaders = {};

  await withServer(
    (req, res) => {
      receivedHeaders = req.headers;
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ detail: "csrf validation failed" }));
    },
    async (baseUrl) => {
      process.env.HULLQ_API_BASE_URL = baseUrl;
      try {
        const request = new Request("http://web.test/broker/logout", { method: "POST" });
        const response = await POST(fakeContext(request));
        assert.equal(response.status, 303);
        assert.equal(response.headers.get("location"), "/broker");
        assert.equal(receivedHeaders.cookie, undefined);
        assert.equal(receivedHeaders.origin, undefined);
        assert.equal(receivedHeaders["x-hullq-requested-with"], "broker-logout-v1");
      } finally {
        delete process.env.HULLQ_API_BASE_URL;
      }
    },
  );
});

test("POST logout: an unreachable upstream is surfaced as a 502, never a thrown exception", async () => {
  const request = new Request("http://web.test/broker/logout", {
    method: "POST",
    headers: { cookie: "hullq_session=abc" },
  });
  process.env.HULLQ_API_BASE_URL = "http://127.0.0.1:1"; // reserved, always refused
  try {
    const response = await POST(fakeContext(request));
    assert.equal(response.status, 502);
  } finally {
    delete process.env.HULLQ_API_BASE_URL;
  }
});
