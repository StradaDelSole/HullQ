// SLICE-0071 independent-review Finding D: proves shortlist/compare
// resolution never fails just because discovery-surface signing is
// currently unavailable -- resolution itself must remain a pure listing-
// truth read, with discovery attribution as a best-effort addition only.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { resolveListingsForSurface } from "../shortlistResolveServer.ts";

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

function fakeListingHandler(_req: http.IncomingMessage, res: http.ServerResponse): void {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify({ asking_price_mode: "POA", gallery: [] }));
}

test("resolveListingsForSurface: mints a discovery_token when the shared secret is configured", async () => {
  const original = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  process.env.HULLQ_PREVIEW_SIGNING_SECRET = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=";
  try {
    await withServer(fakeListingHandler, async (baseUrl) => {
      const items = await resolveListingsForSurface(["NL-1"], "SHORTLIST", baseUrl);
      assert.equal(items[0]?.state, "available");
      if (items[0]?.state === "available") {
        assert.equal(typeof (items[0].data as { discovery_token?: string }).discovery_token, "string");
      }
    });
  } finally {
    process.env.HULLQ_PREVIEW_SIGNING_SECRET = original;
  }
});

test("resolveListingsForSurface: still resolves listing truth (never fails) when the shared secret is absent, just without a discovery_token", async () => {
  const original = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  delete process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  try {
    await withServer(fakeListingHandler, async (baseUrl) => {
      const items = await resolveListingsForSurface(["NL-1"], "SHORTLIST", baseUrl);
      assert.equal(items[0]?.state, "available");
      if (items[0]?.state === "available") {
        const data = items[0].data as { discovery_token?: string; asking_price_mode?: string };
        assert.equal(data.discovery_token, undefined);
        // The real over-the-wire JSON response drops an undefined-valued
        // key entirely (JSON.stringify semantics), so no client ever
        // observes a `discovery_token` field at all in this case.
        assert.equal(JSON.stringify(data).includes("discovery_token"), false);
        // Real listing truth is still returned untouched.
        assert.equal(data.asking_price_mode, "POA");
      }
    });
  } finally {
    process.env.HULLQ_PREVIEW_SIGNING_SECRET = original;
  }
});
