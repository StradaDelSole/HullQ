// SLICE-0071 independent-review Finding B/D: unit tests for the trusted
// server-side discovery-surface signing module. The cross-language test
// below is the critical one -- it proves this TypeScript implementation
// produces byte-for-byte the same signed token
// `hullq.security.discovery_surface_signing.mint_discovery_surface_token`
// would produce for the identical inputs/secret, which is what makes it
// safe for Astro to mint tokens FastAPI's contact route can verify.
//
// Note: `classifyReferrer` was removed in the Finding C amendment -- an
// HTTP `Referer` header is not an authenticated first-party navigation
// capability, so this module no longer exposes any Referer-to-surface
// classification at all (see `discoverySurfaceSigning.ts`'s docstring).
import assert from "node:assert/strict";
import { test } from "node:test";

process.env.HULLQ_PREVIEW_SIGNING_SECRET = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=";

const { mintDiscoverySurfaceToken } = await import("../discoverySurfaceSigning.ts");

test("mintDiscoverySurfaceToken: byte-for-byte matches the Python implementation for identical inputs", () => {
  // Generated via: hullq.security.discovery_surface_signing.mint_discovery_surface_token(
  //   DiscoverySurface.SHORTLIST, "NL-CROSSLANG", secret=b"0"*32,
  //   now=datetime(2026, 1, 1, tzinfo=UTC))
  const expected =
    "eyJleHAiOjE3NjcyMjkyMDAsImlhdCI6MTc2NzIyNTYwMCwibmxpZCI6Ik5MLUNST1NTTEFORyIsInN1cmZhY2UiOiJTSE9SVExJU1QiLCJ0eXAiOiJodWxscV9kaXNjb3Zlcnlfc3VyZmFjZV92MSIsInYiOjF9.npZ6hkJ6XJ86qkAA0zlsSdJ1X1IC_aXo0YZy6pMdMuc";
  const token = mintDiscoverySurfaceToken("SHORTLIST", "NL-CROSSLANG", 3600, 1767225600000);
  assert.equal(token, expected);
});

test("mintDiscoverySurfaceToken: produces a two-segment base64url token for every bounded surface", () => {
  for (const surface of [
    "DIRECT_LISTING",
    "TECHNICAL_SEARCH",
    "INTERNAL_BROWSE",
    "SHORTLIST",
    "COMPARE",
  ] as const) {
    const token = mintDiscoverySurfaceToken(surface, "NL-1");
    assert.ok(token);
    const parts = token.split(".");
    assert.equal(parts.length, 2);
    assert.match(parts[0]!, /^[A-Za-z0-9_-]+$/);
    assert.match(parts[1]!, /^[A-Za-z0-9_-]+$/);
  }
});

test("mintDiscoverySurfaceToken: different listing ids produce different tokens", () => {
  const a = mintDiscoverySurfaceToken("SHORTLIST", "NL-A", 3600, 0);
  const b = mintDiscoverySurfaceToken("SHORTLIST", "NL-B", 3600, 0);
  assert.notEqual(a, b);
});

// Finding D: discovery attribution is auxiliary CRM telemetry and must
// never become a hard availability dependency -- minting fails closed to
// `undefined`, it never throws, regardless of why the secret is
// unavailable.

test("mintDiscoverySurfaceToken: returns undefined (never throws) when the shared secret is absent", () => {
  const original = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  delete process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  try {
    assert.doesNotThrow(() => mintDiscoverySurfaceToken("SHORTLIST", "NL-1"));
    assert.equal(mintDiscoverySurfaceToken("SHORTLIST", "NL-1"), undefined);
  } finally {
    process.env.HULLQ_PREVIEW_SIGNING_SECRET = original;
  }
});

test("mintDiscoverySurfaceToken: returns undefined (never throws) when the secret is too short", () => {
  const original = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  process.env.HULLQ_PREVIEW_SIGNING_SECRET = Buffer.from("too-short").toString("base64url");
  try {
    assert.doesNotThrow(() => mintDiscoverySurfaceToken("SHORTLIST", "NL-1"));
    assert.equal(mintDiscoverySurfaceToken("SHORTLIST", "NL-1"), undefined);
  } finally {
    process.env.HULLQ_PREVIEW_SIGNING_SECRET = original;
  }
});

test("mintDiscoverySurfaceToken: returns undefined (never throws) when the secret is empty/whitespace", () => {
  const original = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  process.env.HULLQ_PREVIEW_SIGNING_SECRET = "   ";
  try {
    assert.doesNotThrow(() => mintDiscoverySurfaceToken("SHORTLIST", "NL-1"));
    assert.equal(mintDiscoverySurfaceToken("SHORTLIST", "NL-1"), undefined);
  } finally {
    process.env.HULLQ_PREVIEW_SIGNING_SECRET = original;
  }
});
