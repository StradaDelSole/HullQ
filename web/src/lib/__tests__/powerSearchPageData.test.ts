// SLICE-0093: mirrors searchPageData.test.ts's identical discipline for the
// entirely separate Power-only Search surface -- a real 400 stays distinct
// from a backend/network failure, and the two separate result surfaces
// (design_linked_matches / publisher_claim_matches) thread through
// verbatim.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { buildPowerSearchCanonicalPath, loadPowerSearchPageData } from "../powerSearchPageData.ts";

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

test("loadPowerSearchPageData: a real 400 is classified as `invalid`, carrying the server message", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({ error: "invalid_power_search_request", message: "not a valid power_drive" }),
      );
    },
    async (baseUrl) => {
      const data = await loadPowerSearchPageData(baseUrl, "en", "power_drive=DIESEL_ELECTRIC");
      assert.equal(data.kind, "invalid");
      if (data.kind === "invalid") {
        assert.equal(data.message, "not a valid power_drive");
      }
    },
  );
});

test("loadPowerSearchPageData: an unreachable backend is classified as `unavailable`, never `invalid`", async () => {
  const data = await loadPowerSearchPageData("http://127.0.0.1:1", "en", "power_drive=POD");
  assert.equal(data.kind, "unavailable");
});

test("loadPowerSearchPageData: an unexpected upstream status is classified as `unavailable`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end("internal server error");
    },
    async (baseUrl) => {
      const data = await loadPowerSearchPageData(baseUrl, "en", "power_drive=POD");
      assert.equal(data.kind, "unavailable");
    },
  );
});

test("loadPowerSearchPageData: a 200 result carries design_linked_matches and publisher_claim_matches separately", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { power_drive: "POD" },
          design_linked_matches: [],
          design_linked_match_count: 0,
          design_linked_insufficient_data_count: 0,
          publisher_claim_matches: [
            {
              native_listing_id: "NL-POD-1",
              publishing_organization_id: "ORG-1",
              freshness_status: "CONFIRMED",
              last_confirmed_at: null,
              source_basis: "PUBLISHER_CLAIM",
              // Round 2 Finding F2: a genuine positive match always
              // carries exactly one real leaf per active criterion.
              criterion_evidence: [
                {
                  criterion: {
                    kind: "CATEGORICAL",
                    field: "power_drive_configuration",
                    equals: "POD",
                  },
                  field: "power_drive_configuration",
                  truth: "TRUE",
                  reason: null,
                  explanation: "power_drive_configuration='POD' equals required value 'POD'",
                  observed_value: "POD",
                },
              ],
              discovery_token: "token-1",
            },
          ],
          publisher_claim_match_count: 1,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadPowerSearchPageData(baseUrl, "en", "power_drive=POD");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.deepEqual(data.activeRequirement, { power_drive: "POD" });
        assert.equal(data.designLinkedMatchCount, 0);
        assert.equal(data.publisherClaimMatchCount, 1);
        assert.equal(data.publisherClaimMatches[0]?.native_listing_id, "NL-POD-1");
        assert.equal(data.publisherClaimMatches[0]?.source_basis, "PUBLISHER_CLAIM");
      }
    },
  );
});

test("loadPowerSearchPageData: base state has null activeRequirement", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ locale: "en", active_requirement: null }));
    },
    async (baseUrl) => {
      const data = await loadPowerSearchPageData(baseUrl, "en", "");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.activeRequirement, null);
      }
    },
  );
});

test("loadPowerSearchPageData: a PARTIAL result builds a nextPageQueryString carrying the real cursor", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { power_drive: "POD" },
          design_linked_matches: [],
          design_linked_match_count: 0,
          design_linked_insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 1,
          evaluation_state: "PARTIAL",
          next_cursor: "opaque-cursor-token",
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadPowerSearchPageData(baseUrl, "en", "power_drive=POD&page_size=1");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.evaluationState, "PARTIAL");
        assert.equal(
          data.nextPageQueryString,
          "power_drive=POD&page_size=1&page_after=opaque-cursor-token",
        );
      }
    },
  );
});

test("loadPowerSearchPageData: a COMPLETE result has no nextPageQueryString", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { power_drive: "POD" },
          design_linked_matches: [],
          design_linked_match_count: 0,
          design_linked_insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadPowerSearchPageData(baseUrl, "en", "power_drive=POD");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.evaluationState, "COMPLETE");
        assert.equal(data.nextPageQueryString, null);
      }
    },
  );
});

test("buildPowerSearchCanonicalPath: null activeRequirement is the bare locale path", () => {
  assert.equal(buildPowerSearchCanonicalPath("en", null), "/en/power/search");
});

test("buildPowerSearchCanonicalPath: one active token", () => {
  assert.equal(
    buildPowerSearchCanonicalPath("de", { power_drive: "OUTBOARD" }),
    "/de/power/search?power_drive=OUTBOARD",
  );
});

test("buildPowerSearchCanonicalPath: SLICE-0094 count-only active token", () => {
  assert.equal(
    buildPowerSearchCanonicalPath("de", { power_engine_count: "2" }),
    "/de/power/search?power_engine_count=2",
  );
});

test("buildPowerSearchCanonicalPath: SLICE-0094 combined drive+count in canonical order", () => {
  assert.equal(
    buildPowerSearchCanonicalPath("de", { power_drive: "SHAFT", power_engine_count: "2" }),
    "/de/power/search?power_drive=SHAFT&power_engine_count=2",
  );
});
