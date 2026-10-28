// SLICE-0093 review amendment Finding E: a truncated, structurally invalid
// or contradictory HTTP-200 Search payload must be rejected as a
// service/contract failure (status 502), never silently rendered as a
// genuine empty/zero result. Mirrors the exact truncated example from the
// review: `{"locale":"en","active_requirement":{"power_drive":"POD"}}`
// with every result-surface field missing.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  fetchPowerSearch,
  parseCanonicalPowerSearchQuery,
  validatePowerSearchResultBody,
} from "../powerSearchApi.ts";

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

const _BASE_EXPECTED = { locale: "en", powerDrive: null } as const;
const _POD_EXPECTED = { locale: "en", powerDrive: "POD" } as const;

test("validatePowerSearchResultBody: a genuine BASE body (null active_requirement) is valid", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null },
    _BASE_EXPECTED,
  );
  assert.notEqual(result, null);
  assert.equal(result?.active_requirement, null);
});

test("validatePowerSearchResultBody: a genuine empty RESULT body (all zero/empty) is valid", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.notEqual(result, null);
  assert.equal(result?.design_linked_match_count, 0);
});

test("validatePowerSearchResultBody: the exact truncated review example is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: { power_drive: "POD" } },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a missing locale is rejected", () => {
  const result = validatePowerSearchResultBody({ active_requirement: null }, _BASE_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an invalid power_drive token is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "DIESEL_ELECTRIC" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: active_requirement with extra keys is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD", extra: "x" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a count contradicting its own array length is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 3,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a non-array design_linked_matches is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: "not-an-array",
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an unrecognized source_basis is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
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
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a valid non-empty result with a genuine PUBLISHER_CLAIM match is accepted", () => {
  const result = validatePowerSearchResultBody(
    {
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
          // Round 2 Finding F2: a genuine positive match always carries
          // exactly one real leaf per active criterion -- never an empty
          // array, even for a single-criterion drive-only request.
          criterion_evidence: [
            {
              criterion: { kind: "CATEGORICAL", field: "power_drive_configuration", equals: "POD" },
              field: "power_drive_configuration",
              truth: "TRUE",
              reason: null,
              explanation: "power_drive_configuration='POD' equals required value 'POD'",
              observed_value: "POD",
            },
          ],
          discovery_token: "tok",
        },
      ],
      publisher_claim_match_count: 1,
    },
    _POD_EXPECTED,
  );
  assert.notEqual(result, null);
  assert.equal(result?.publisher_claim_matches?.length, 1);
});

test("validatePowerSearchResultBody: a missing freshness_status in a match is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
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
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a bare array (not an object) is rejected", () => {
  assert.equal(validatePowerSearchResultBody([], _BASE_EXPECTED), null);
});

test("validatePowerSearchResultBody: null is rejected", () => {
  assert.equal(validatePowerSearchResultBody(null, _BASE_EXPECTED), null);
});

// ---------------------------------------------------------------------------
// Review amendment Finding J (MEDIUM): request/response consistency and
// deep nested-evidence validation.
// ---------------------------------------------------------------------------

test("validatePowerSearchResultBody: a filtered request silently served a BASE response is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an unfiltered request served an active RESULT is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a response echoing the wrong drive token is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "SHAFT" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a response for a different locale than requested is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "de", active_requirement: null },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a contradictory BASE body with non-empty matches is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: null,
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
    },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a contradictory BASE body with a positive count is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null, publisher_claim_match_count: 1 },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

// ---------------------------------------------------------------------------
// Review amendment Finding J (second pass): the real FastAPI BASE contract
// is exactly `{locale, active_requirement}` -- ANY other key at all is
// rejected on BASE, regardless of its own value/type (never selectively
// tolerating a malformed array, an empty array, or a zero-valued count).
// RESULT counts must be nonnegative integers, not merely `>= 0` numbers.
// Request canonicalization must reject invalid/duplicate/unrecognized
// query keys rather than silently treating them as "no filter".
// ---------------------------------------------------------------------------

test("validatePowerSearchResultBody: the exact review example -- BASE with a malformed (non-array) field -- is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null, publisher_claim_matches: "corrupted" },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: the exact review example -- BASE with a negative count -- is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null, publisher_claim_match_count: -1 },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: BASE with an empty (genuinely zero-valued) extra array is still rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null, publisher_claim_matches: [] },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: BASE with an extra zero-valued count field is still rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null, design_linked_match_count: 0 },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: BASE with any unrecognized extra key is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null, extra: "unexpected" },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a genuinely minimal BASE body (only locale + active_requirement) is still accepted", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: null },
    _BASE_EXPECTED,
  );
  assert.notEqual(result, null);
  assert.equal(result?.active_requirement, null);
});

test("validatePowerSearchResultBody: a fractional RESULT count is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 0.5,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a negative RESULT count is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: -1,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a non-finite RESULT count (Infinity) is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: Number.POSITIVE_INFINITY,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a NaN RESULT count is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: Number.NaN,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a string RESULT count is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: "0",
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a genuine empty RESULT with integer-typed zero counts is still accepted", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "POD" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _POD_EXPECTED,
  );
  assert.notEqual(result, null);
});

// ---------------------------------------------------------------------------
// parseCanonicalPowerSearchQuery: direct unit coverage
// ---------------------------------------------------------------------------

test("parseCanonicalPowerSearchQuery: a truly empty query string is canonical (no filter)", () => {
  assert.deepEqual(parseCanonicalPowerSearchQuery(""), {
    ok: true,
    powerDrive: null,
    powerEngineCount: null,
  });
});

test("parseCanonicalPowerSearchQuery: exactly one valid power_drive token is canonical", () => {
  assert.deepEqual(parseCanonicalPowerSearchQuery("power_drive=POD"), {
    ok: true,
    powerDrive: "POD",
    powerEngineCount: null,
  });
});

test("parseCanonicalPowerSearchQuery: an invalid power_drive value is rejected, never read as absent", () => {
  assert.equal(parseCanonicalPowerSearchQuery("power_drive=BOGUS").ok, false);
});

test("parseCanonicalPowerSearchQuery: duplicate power_drive keys are rejected even with identical values", () => {
  assert.equal(parseCanonicalPowerSearchQuery("power_drive=POD&power_drive=POD").ok, false);
});

test("parseCanonicalPowerSearchQuery: duplicate power_drive keys with differing values are rejected", () => {
  assert.equal(parseCanonicalPowerSearchQuery("power_drive=POD&power_drive=SHAFT").ok, false);
});

test("parseCanonicalPowerSearchQuery: an unrecognized query key alone is rejected", () => {
  assert.equal(parseCanonicalPowerSearchQuery("utm_source=test").ok, false);
});

test("parseCanonicalPowerSearchQuery: a mixed valid power_drive plus an unrecognized key is rejected", () => {
  assert.equal(parseCanonicalPowerSearchQuery("power_drive=POD&utm_source=test").ok, false);
});

test("validatePowerSearchResultBody: malformed nested criterion_evidence is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
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
          // Missing `truth`/`explanation`/`criterion` -- a structurally
          // present array whose *contents* are malformed.
          criterion_evidence: [{ field: "power_drive_configuration", observed_value: "POD" }],
          discovery_token: "tok",
        },
      ],
      publisher_claim_match_count: 1,
    },
    _POD_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: malformed nested design_evaluation on a design-linked match is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "SHAFT" },
      design_linked_matches: [
        {
          native_listing_id: "NL-1",
          publishing_organization_id: "ORG-1",
          freshness_status: "CONFIRMED",
          last_confirmed_at: null,
          discovery_token: "tok",
          criterion_evidence: [],
          design_configuration_evidence: [],
          // Missing `result_class`/`matching_configuration_ids` entirely.
          design_evaluation: { design_id: "BD-1" },
        },
      ],
      design_linked_match_count: 1,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    { locale: "en", powerDrive: "SHAFT" } as const,
  );
  assert.equal(result, null);
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

test("fetchPowerSearch: a filtered query silently served a BASE 200 body collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, { locale: "en", active_requirement: null }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a response echoing the wrong drive token collapses to 502", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, {
        locale: "en",
        active_requirement: { power_drive: "SHAFT" },
        design_linked_matches: [],
        design_linked_match_count: 0,
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

test("fetchPowerSearch: a response for a different locale than requested collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, { locale: "de", active_requirement: null }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: BASE with a malformed extra field collapses to 502 (never discarded)", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, { locale: "en", active_requirement: null, publisher_claim_matches: "corrupted" }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: BASE with a negative extra count collapses to 502", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, { locale: "en", active_requirement: null, publisher_claim_match_count: -1 }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a fractional RESULT count collapses to 502", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, {
        locale: "en",
        active_requirement: { power_drive: "POD" },
        design_linked_matches: [],
        design_linked_match_count: 0.5,
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

test("fetchPowerSearch: an invalid power_drive request value never reaches the validator as unfiltered, collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, { locale: "en", active_requirement: null }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=BOGUS");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: duplicate power_drive query keys collapse to 502 even when the body looks like a valid RESULT", async () => {
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
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD&power_drive=POD");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: an unrecognized query key collapses to 502 even when the body looks like a valid BASE", async () => {
  await withServer(
    (_req, res) => respondJson(res, { locale: "en", active_requirement: null }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "utm_source=test");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a mixed valid power_drive plus an unrecognized key collapses to 502", async () => {
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
      const response = await fetchPowerSearch(baseUrl, "en", "power_drive=POD&utm_source=test");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a genuinely valid BASE response (empty query string) is still accepted", async () => {
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

test("fetchPowerSearch: a genuinely valid empty RESULT response is still accepted", async () => {
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
      assert.equal(response.result?.design_linked_match_count, 0);
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

// ---------------------------------------------------------------------------
// SLICE-0094: power_engine_count -- count-only and combined drive+count.
// ---------------------------------------------------------------------------

const _COUNT_EXPECTED = { locale: "en", powerDrive: null, powerEngineCount: "2" } as const;
const _COMBINED_EXPECTED = { locale: "en", powerDrive: "SHAFT", powerEngineCount: "2" } as const;

test("validatePowerSearchResultBody: a count-only active_requirement is valid", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_engine_count: "2" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _COUNT_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("validatePowerSearchResultBody: a combined drive+count active_requirement is valid", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _COMBINED_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("validatePowerSearchResultBody: an invalid power_engine_count token is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_engine_count: "9" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _COUNT_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a combined request silently missing the count leaf in the echo is rejected", () => {
  const result = validatePowerSearchResultBody(
    {
      locale: "en",
      active_requirement: { power_drive: "SHAFT" },
      design_linked_matches: [],
      design_linked_match_count: 0,
      design_linked_insufficient_data_count: 0,
      publisher_claim_matches: [],
      publisher_claim_match_count: 0,
    },
    _COMBINED_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: active_requirement with an empty object (neither criterion) is rejected", () => {
  const result = validatePowerSearchResultBody(
    { locale: "en", active_requirement: {} },
    _BASE_EXPECTED,
  );
  assert.equal(result, null);
});

test("parseCanonicalPowerSearchQuery: exactly one valid power_engine_count token is canonical", () => {
  assert.deepEqual(parseCanonicalPowerSearchQuery("power_engine_count=2"), {
    ok: true,
    powerDrive: null,
    powerEngineCount: "2",
  });
});

test("parseCanonicalPowerSearchQuery: combined power_drive and power_engine_count is canonical", () => {
  assert.deepEqual(parseCanonicalPowerSearchQuery("power_drive=SHAFT&power_engine_count=2"), {
    ok: true,
    powerDrive: "SHAFT",
    powerEngineCount: "2",
  });
});

test("parseCanonicalPowerSearchQuery: power_engine_count=9 is rejected, never read as absent", () => {
  assert.equal(parseCanonicalPowerSearchQuery("power_engine_count=9").ok, false);
});

test("parseCanonicalPowerSearchQuery: power_engine_count=0 is rejected", () => {
  assert.equal(parseCanonicalPowerSearchQuery("power_engine_count=0").ok, false);
});

test("parseCanonicalPowerSearchQuery: duplicate power_engine_count keys are rejected", () => {
  assert.equal(
    parseCanonicalPowerSearchQuery("power_engine_count=2&power_engine_count=2").ok,
    false,
  );
});

test("fetchPowerSearch: a genuine count-only 200 result is surfaced as result", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, {
        locale: "en",
        active_requirement: { power_engine_count: "2" },
        design_linked_matches: [],
        design_linked_match_count: 0,
        design_linked_insufficient_data_count: 0,
        publisher_claim_matches: [],
        publisher_claim_match_count: 0,
      }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_engine_count=2");
      assert.equal(response.status, 200);
      assert.notEqual(response.result, null);
    },
  );
});

test("fetchPowerSearch: a genuine combined drive+count 200 result is surfaced as result", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, {
        locale: "en",
        active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
        design_linked_matches: [],
        design_linked_match_count: 0,
        design_linked_insufficient_data_count: 0,
        publisher_claim_matches: [],
        publisher_claim_match_count: 0,
      }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(
        baseUrl,
        "en",
        "power_drive=SHAFT&power_engine_count=2",
      );
      assert.equal(response.status, 200);
      assert.notEqual(response.result, null);
    },
  );
});

test("fetchPowerSearch: an invalid power_engine_count request value collapses to 502, never a false BASE", async () => {
  await withServer(
    (_req, res) => respondJson(res, { locale: "en", active_requirement: null }),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_engine_count=9");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

// ---------------------------------------------------------------------------
// SLICE-0094 independent-review amendment Finding F: tightened NUMERIC leaf
// evidence validation -- correct field, RANGE comparison, identical
// thresholds, canonical token, and consistency with the active requirement.
// ---------------------------------------------------------------------------

function engineCountEvidence(requestedValue: string, observedValue: string | null, truth: string) {
  return {
    criterion: {
      kind: "NUMERIC",
      field: "power_engine_count",
      comparison: "RANGE",
      threshold_min: requestedValue,
      threshold_max: requestedValue,
    },
    field: "power_engine_count",
    truth,
    reason: null,
    explanation: "test explanation",
    observed_value: observedValue,
  };
}

function countOnlyBody(evidence: unknown) {
  return {
    locale: "en",
    active_requirement: { power_engine_count: "2" },
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
        criterion_evidence: [evidence],
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  };
}

test("validatePowerSearchResultBody: a well-formed NUMERIC power_engine_count evidence leaf is accepted", () => {
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("2", "2", "TRUE")),
    _COUNT_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("validatePowerSearchResultBody: a NUMERIC evidence leaf with MAXIMUM instead of RANGE is rejected", () => {
  const evidence = engineCountEvidence("2", "2", "TRUE");
  evidence.criterion.comparison = "MAXIMUM";
  const result = validatePowerSearchResultBody(countOnlyBody(evidence), _COUNT_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a NUMERIC evidence leaf with differing thresholds is rejected", () => {
  const evidence = engineCountEvidence("2", "2", "TRUE");
  evidence.criterion.threshold_max = "3";
  const result = validatePowerSearchResultBody(countOnlyBody(evidence), _COUNT_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a NUMERIC evidence leaf with a non-canonical threshold (0) is rejected", () => {
  const evidence = engineCountEvidence("2", "2", "TRUE");
  evidence.criterion.threshold_min = "0";
  evidence.criterion.threshold_max = "0";
  const result = validatePowerSearchResultBody(countOnlyBody(evidence), _COUNT_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a NUMERIC evidence leaf with the wrong field name is rejected", () => {
  const evidence = engineCountEvidence("2", "2", "TRUE");
  evidence.criterion.field = "power_engine_count_bogus";
  const result = validatePowerSearchResultBody(countOnlyBody(evidence), _COUNT_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a CATEGORICAL evidence leaf with a non-whitelisted drive value is rejected", () => {
  const body = {
    locale: "en",
    active_requirement: { power_drive: "SHAFT" },
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
        criterion_evidence: [
          {
            criterion: {
              kind: "CATEGORICAL",
              field: "power_drive_configuration",
              equals: "DIESEL_ELECTRIC",
            },
            field: "power_drive_configuration",
            truth: "TRUE",
            reason: null,
            explanation: "test",
            observed_value: "MIXED",
          },
        ],
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  };
  const result = validatePowerSearchResultBody(body, {
    locale: "en",
    powerDrive: "SHAFT",
  });
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an evidence leaf requesting a value other than the active requirement is rejected", () => {
  // active_requirement says "2", but the nested evidence leaf's own
  // threshold claims it evaluated "3" -- structurally well-formed per
  // leaf, but inconsistent with what the response claims to answer.
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("3", "3", "FALSE")),
    _COUNT_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a power_engine_count evidence leaf appearing on a drive-only request is rejected", () => {
  // No power_engine_count was requested at all (powerEngineCount is
  // omitted from `expected`), so no NUMERIC evidence leaf for it may
  // legitimately appear.
  const body = {
    locale: "en",
    active_requirement: { power_drive: "SHAFT" },
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
        criterion_evidence: [engineCountEvidence("2", "2", "TRUE")],
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  };
  const result = validatePowerSearchResultBody(body, { locale: "en", powerDrive: "SHAFT" });
  assert.equal(result, null);
});

test("fetchPowerSearch: a malformed NUMERIC evidence shape in an otherwise-valid 200 body collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, countOnlyBody(engineCountEvidence("3", "3", "FALSE"))),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_engine_count=2");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

// ---------------------------------------------------------------------------
// SLICE-0094 independent-review amendment Round 2, Finding F2: a positive
// result surface (a match, or an applicable configuration's evidence) must
// carry EXACTLY one correct leaf per currently active criterion -- never
// missing one, never an extra/duplicate, never a leaf whose own `field`
// disagrees with its nested `criterion`, and never a `truth` paired with an
// `observed_value` the backend could never actually have produced for it.
// Legitimate non-matching/UNKNOWN evidence on an OTHER configuration must
// never be suppressed, as long as its own coverage is still complete.
// ---------------------------------------------------------------------------

function driveEvidence(observedValue: string | null, truth: string, requestedValue = "SHAFT") {
  return {
    criterion: { kind: "CATEGORICAL", field: "power_drive_configuration", equals: requestedValue },
    field: "power_drive_configuration",
    truth,
    reason: null,
    explanation: "test explanation",
    observed_value: observedValue,
  };
}

function combinedBody(evidenceList: unknown[]) {
  return {
    locale: "en",
    active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
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
        criterion_evidence: evidenceList,
        discovery_token: "tok",
      },
    ],
    publisher_claim_match_count: 1,
  };
}

function designLinkedMatchBody(criterionEvidence: unknown[], configEvidence: unknown[]) {
  return {
    locale: "en",
    active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
    design_linked_matches: [
      {
        native_listing_id: "NL-1",
        publishing_organization_id: "ORG-1",
        freshness_status: "CONFIRMED",
        last_confirmed_at: null,
        discovery_token: "tok",
        criterion_evidence: criterionEvidence,
        design_configuration_evidence: configEvidence,
        design_evaluation: {
          design_id: "BD-1",
          result_class: "CONFIRMED_MATCH",
          matching_configuration_ids: ["CFG-1"],
          reason: null,
        },
      },
    ],
    design_linked_match_count: 1,
    design_linked_insufficient_data_count: 0,
    publisher_claim_matches: [],
    publisher_claim_match_count: 0,
  };
}

function configurationEvidence(id: string, truth: string, evidenceList: unknown[]) {
  return {
    configuration_id: id,
    boat_design_id: "BD-1",
    named_variant_id: null,
    truth,
    criterion_evidence: evidenceList,
  };
}

test("validatePowerSearchResultBody: a combined-request match with exactly one correct leaf per active criterion is accepted", () => {
  const result = validatePowerSearchResultBody(
    combinedBody([driveEvidence("SHAFT", "TRUE"), engineCountEvidence("2", "2", "TRUE")]),
    _COMBINED_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("validatePowerSearchResultBody: a combined-request match missing the count leaf is rejected", () => {
  const result = validatePowerSearchResultBody(
    combinedBody([driveEvidence("SHAFT", "TRUE")]),
    _COMBINED_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a combined-request match with an empty criterion_evidence array is rejected", () => {
  const result = validatePowerSearchResultBody(combinedBody([]), _COMBINED_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a combined-request match with a duplicated drive leaf (missing count) is rejected", () => {
  const result = validatePowerSearchResultBody(
    combinedBody([driveEvidence("SHAFT", "TRUE"), driveEvidence("SHAFT", "TRUE")]),
    _COMBINED_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an evidence leaf whose top-level field does not name its own nested criterion is rejected", () => {
  const evidence = engineCountEvidence("2", "2", "TRUE");
  evidence.field = "power_drive_configuration";
  const result = validatePowerSearchResultBody(countOnlyBody(evidence), _COUNT_EXPECTED);
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a TRUE leaf whose observed_value differs from the requested value is rejected", () => {
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("2", "3", "TRUE")),
    _COUNT_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a TRUE leaf with a null observed_value is rejected", () => {
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("2", null, "TRUE")),
    _COUNT_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: an UNKNOWN leaf carrying a non-null observed_value is rejected", () => {
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("2", "2", "UNKNOWN")),
    _COUNT_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a FALSE leaf whose observed_value equals the requested value is rejected (contradiction)", () => {
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("2", "2", "FALSE")),
    _COUNT_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a FALSE leaf with a null observed_value (confirmed-exclusion shape) is still accepted, never suppressed", () => {
  const result = validatePowerSearchResultBody(
    countOnlyBody(engineCountEvidence("2", null, "FALSE")),
    _COUNT_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("validatePowerSearchResultBody: a design-linked combined match with full top-level and configuration criterion coverage is accepted", () => {
  const result = validatePowerSearchResultBody(
    designLinkedMatchBody(
      [driveEvidence("SHAFT", "TRUE"), engineCountEvidence("2", "2", "TRUE")],
      [
        configurationEvidence("CFG-1", "TRUE", [
          driveEvidence("SHAFT", "TRUE"),
          engineCountEvidence("2", "2", "TRUE"),
        ]),
      ],
    ),
    _COMBINED_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("validatePowerSearchResultBody: a design-linked combined match missing the top-level count leaf is rejected", () => {
  const result = validatePowerSearchResultBody(
    designLinkedMatchBody(
      [driveEvidence("SHAFT", "TRUE")],
      [
        configurationEvidence("CFG-1", "TRUE", [
          driveEvidence("SHAFT", "TRUE"),
          engineCountEvidence("2", "2", "TRUE"),
        ]),
      ],
    ),
    _COMBINED_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a design-linked match whose configuration evidence is missing a leaf is rejected", () => {
  const result = validatePowerSearchResultBody(
    designLinkedMatchBody(
      [driveEvidence("SHAFT", "TRUE"), engineCountEvidence("2", "2", "TRUE")],
      [configurationEvidence("CFG-1", "TRUE", [driveEvidence("SHAFT", "TRUE")])],
    ),
    _COMBINED_EXPECTED,
  );
  assert.equal(result, null);
});

test("validatePowerSearchResultBody: a design-linked match retains a legitimate non-matching OTHER configuration's full-coverage UNKNOWN evidence, never suppressed", () => {
  const result = validatePowerSearchResultBody(
    designLinkedMatchBody(
      [driveEvidence("SHAFT", "TRUE"), engineCountEvidence("2", "2", "TRUE")],
      [
        configurationEvidence("CFG-1", "TRUE", [
          driveEvidence("SHAFT", "TRUE"),
          engineCountEvidence("2", "2", "TRUE"),
        ]),
        configurationEvidence("CFG-2", "UNKNOWN", [
          driveEvidence(null, "UNKNOWN"),
          engineCountEvidence("2", null, "UNKNOWN"),
        ]),
      ],
    ),
    _COMBINED_EXPECTED,
  );
  assert.notEqual(result, null);
});

test("fetchPowerSearch: a genuine combined-request match with full leaf coverage is accepted", async () => {
  await withServer(
    (_req, res) =>
      respondJson(
        res,
        combinedBody([driveEvidence("SHAFT", "TRUE"), engineCountEvidence("2", "2", "TRUE")]),
      ),
    async (baseUrl) => {
      const response = await fetchPowerSearch(
        baseUrl,
        "en",
        "power_drive=SHAFT&power_engine_count=2",
      );
      assert.equal(response.status, 200);
      assert.notEqual(response.result, null);
    },
  );
});

test("fetchPowerSearch: a combined-request match missing a leaf collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, combinedBody([driveEvidence("SHAFT", "TRUE")])),
    async (baseUrl) => {
      const response = await fetchPowerSearch(
        baseUrl,
        "en",
        "power_drive=SHAFT&power_engine_count=2",
      );
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a match with an empty criterion_evidence array collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, combinedBody([])),
    async (baseUrl) => {
      const response = await fetchPowerSearch(
        baseUrl,
        "en",
        "power_drive=SHAFT&power_engine_count=2",
      );
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a match with a duplicated leaf collapses to 502", async () => {
  await withServer(
    (_req, res) =>
      respondJson(res, combinedBody([driveEvidence("SHAFT", "TRUE"), driveEvidence("SHAFT", "TRUE")])),
    async (baseUrl) => {
      const response = await fetchPowerSearch(
        baseUrl,
        "en",
        "power_drive=SHAFT&power_engine_count=2",
      );
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});

test("fetchPowerSearch: a TRUE leaf with an incompatible observed_value collapses to 502", async () => {
  await withServer(
    (_req, res) => respondJson(res, countOnlyBody(engineCountEvidence("2", "3", "TRUE"))),
    async (baseUrl) => {
      const response = await fetchPowerSearch(baseUrl, "en", "power_engine_count=2");
      assert.equal(response.status, 502);
      assert.equal(response.result, null);
    },
  );
});
