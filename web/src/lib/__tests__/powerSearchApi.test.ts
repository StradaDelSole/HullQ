// SLICE-0093 review amendment Finding E: a truncated, structurally invalid
// or contradictory HTTP-200 Search payload must be rejected as a
// service/contract failure (status 502), never silently rendered as a
// genuine empty/zero result. Mirrors the exact truncated example from the
// review: `{"locale":"en","active_requirement":{"power_drive":"POD"}}`
// with every result-surface field missing.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { fetchPowerSearch, validatePowerSearchResultBody } from "../powerSearchApi.ts";

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

function respondJson(res: http.ServerResponse, body: unknown): void {
  res.writeHead(200, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

// ---------------------------------------------------------------------------
// validatePowerSearchResultBody: direct unit coverage
// ---------------------------------------------------------------------------

test("validatePowerSearchResultBody: a genuine BASE body (null active_requirement) is valid", () => {
  const result = validatePowerSearchResultBody({ locale: "en", active_requirement: null });
  assert.notEqual(result, null);
  assert.equal(result?.active_requirement, null);
});

test("validatePowerSearchResultBody: a genuine empty RESULT body (all zero/empty) is valid", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
    design_linked_matches: [],
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [],
    publisher_claim_match_count: 0,
  });
  assert.notEqual(result, null);
  assert.equal(result?.design_linked_match_count, 0);
});

test("validatePowerSearchResultBody: the exact truncated review example is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a missing locale is rejected", () => {
  const result = validatePowerSearchResultBody({ active_requirement: null });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an invalid power_drive token is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "DIESEL_ELECTRIC" },
    design_linked_matches: [],
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [],
    publisher_claim_match_count: 0,
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: active_requirement with extra keys is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD", extra: "x" },
    design_linked_matches: [],
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [],
    publisher_claim_match_count: 0,
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a count contradicting its own array length is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
    design_linked_matches: [],
    design_linked_match_count: 3,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [],
    publisher_claim_match_count: 0,
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a non-array design_linked_matches is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
    design_linked_matches: "not-an-array",
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [],
    publisher_claim_match_count: 0,
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an unrecognized source_basis is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
    design_linked_matches: [],
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [
      {
        native_listing_id: "NL-1",
        publishing_organization_id: "ORG-1",
        freshness_status: "CONFIRMED",
        last_confirmed_at: null,
        source_basis: "DESIGN_CONFIRMED",
        criterion_evidence: [],
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a valid non-empty result with a genuine PUBLISHER_CLAIM match is accepted", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
    design_linked_matches: [],
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [
      {
        native_listing_id: "NL-1",
        publishing_organization_id: "ORG-1",
        freshness_status: "CONFIRMED",
        last_confirmed_at: null,
        source_basis: "PUBLISHER_CLAIM",
        criterion_evidence: [],
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  });
  assert.notEqual(result, null);
  assert.equal(result?.publisher_claim_matches?.length, 1);
});

test("validatePowerSearchResultBody: a missing freshness_status in a match is rejected", () => {
  const result = validatePowerSearchResultBody({
    locale: "en",
    active_requirement: { power_drive: "POD" },
    design_linked_matches: [],
    design_linked_match_count: 0,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [
      {
        native_listing_id: "NL-1",
        publishing_organization_id: "ORG-1",
        last_confirmed_at: null,
        source_basis: "PUBLISHER_CLAIM",
        criterion_evidence: [],
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a bare array (not an object) is rejected", () => {
  assert.equal(validatePowerSearchResultBody([]), null);
});

test("validatePowerSearchResultBody: null is rejected", () => {
  assert.equal(validatePowerSearchResultBody(null), null);
});

// ---------------------------------------------------------------------------
// fetchPowerSearch: contract-corruption over real HTTP
// ---------------------------------------------------------------------------

test("fetchPowerSearch: a genuine valid 200 result is surfaced as `result`", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, {
        locale: "en",
        active_requirement: { power_drive: "POD" },
        design_linked_matches: [],
        design_linked_match_count: 0,
        design_linked_insufficient_data_count: 0,
        publisher_claim_matches: [],
        publisher_claim_match_count: 0,
      }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD");
      assert.equal(response.status, 200);
      assert.notEqual(response.result, null);
    },
  );
});

test("fetchPowerSearch: a truncated 200 body collapses to 502, never a false empty result", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, { locale: "en", active_requirement: { power_drive: "POD" } }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a contradictory count/array 200 body collapses to 502", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, {
        locale: "en",
        active_requirement: { power_drive: "POD" },
        design_linked_matches: [],
        design_linked_match_count: 5,
        design_linked_insufficient_data_count: 0,
        publisher_claim_matches: [],
        publisher_claim_match_count: 0,
      }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: genuine BASE state (null active_requirement) is still surfaced as result", async () => {
  await withServer(
    (_req, res) => respondJson(res, { locale: "en", active_requirement: null }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "");
      assert.equal(response.status, 200);
      assert.notEqual(response.result, null);
      assert.equal(response.result?.active_requirement, null);
    },
  );
});

test("fetchPowerSearch: a malformed (non-JSON) 200 body collapses to 502", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("not json");
    },
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD");
      assert.equal(response.status, 502);
    },
  );
});
