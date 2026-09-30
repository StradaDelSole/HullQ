// SLICE-0071 independent-review Finding B: unit tests for the trusted
// server-side discovery-surface signing module. The cross-language test
// below is the critical one -- it proves this TypeScript implementation
// produces byte-for-byte the same signed token
// `hullq.security.discovery_surface_signing.mint_discovery_surface_token`
// would produce for the identical inputs/secret, which is what makes it
// safe for Astro to mint tokens FastAPI's contact route can verify.
import assert from "node:assert/strict";
import { test } from "node:test";

process.env.HULLQ_PREVIEW_SIGNING_SECRET = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA=";

const { classifyReferrer, mintDiscoverySurfaceToken } = await import("../discoverySurfaceSigning.ts");

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

test("mintDiscoverySurfaceToken: throws when the shared secret is not configured", () => {
  const original = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  delete process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  try {
    assert.throws(() => mintDiscoverySurfaceToken("SHORTLIST", "NL-1"));
  } finally {
    process.env.HULLQ_PREVIEW_SIGNING_SECRET = original;
  }
});

test("classifyReferrer: absent referrer classifies as NONE", () => {
  assert.equal(classifyReferrer(null, "https://hullq.test"), "NONE");
  assert.equal(classifyReferrer(undefined, "https://hullq.test"), "NONE");
});

test("classifyReferrer: same-origin referrer classifies as INTERNAL", () => {
  assert.equal(classifyReferrer("https://hullq.test/search", "https://hullq.test"), "INTERNAL");
});

test("classifyReferrer: cross-origin referrer classifies as EXTERNAL", () => {
  assert.equal(classifyReferrer("https://evil.test/", "https://hullq.test"), "EXTERNAL");
});

test("classifyReferrer: an unparseable referrer classifies as EXTERNAL, never throws", () => {
  assert.equal(classifyReferrer("not a url", "https://hullq.test"), "EXTERNAL");
});

test("classifyReferrer: a client cannot self-declare INTERNAL merely by claiming a referrer string equal to a foreign origin's own path shape", () => {
  // Even a maliciously-crafted Referer value only ever classifies against
  // the *caller-supplied* ownOrigin -- this function has no independent
  // notion of "the real HullQ origin" to be tricked about; the guarantee
  // that ownOrigin is genuine belongs to the caller (Astro.url.origin from
  // the real incoming request), not to this pure function.
  assert.equal(classifyReferrer("https://hullq.test.evil.com/", "https://hullq.test"), "EXTERNAL");
});
