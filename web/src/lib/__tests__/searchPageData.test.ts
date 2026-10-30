// SLICE-0051 amendment review, Finding 6: a malformed/ambiguous buyer
// requirement (400) must stay a distinct `invalid` page state from a
// backend/network failure (`unavailable`) -- the buyer must never be told
// their input was wrong when the actual problem is that the service could
// not be reached.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { buildSearchCanonicalPath, loadSearchPageData } from "../searchPageData.ts";

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

test("loadSearchPageData: a real 400 is classified as `invalid`, carrying the server message", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_search_request", message: "not a valid draft_max" }));
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1e0");
      assert.equal(data.kind, "invalid");
      if (data.kind === "invalid") {
        assert.equal(data.message, "not a valid draft_max");
      }
    },
  );
});

test("loadSearchPageData: an unreachable backend is classified as `unavailable`, never `invalid`", async () => {
  // Port 1 is reserved and nothing listens there -- a guaranteed connection failure.
  const data = await loadSearchPageData("http://127.0.0.1:1", "en", "draft_max=1.6");
  assert.equal(data.kind, "unavailable");
});

test("loadSearchPageData: an unexpected upstream status (e.g. 500) is classified as `unavailable`, never `invalid`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(500);
      res.end("internal server error");
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "unavailable");
    },
  );
});

test("loadSearchPageData: a valid 200 result is classified as `ok`, distinct from both failure states", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "ok");
    },
  );
});

// SLICE-0056: keel-only and mixed requests carry a sparse `active_requirement`
// (contract §C) -- `loadSearchPageData` must pass it through exactly as
// FastAPI returned it, never inventing/defaulting a criterion FastAPI did
// not include.
test("loadSearchPageData: a keel-only 200 result carries only keel_configuration in activeRequirement", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { keel_configuration: "FIN" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "keel_configuration=FIN");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.deepEqual(data.activeRequirement, { keel_configuration: "FIN" });
      }
    },
  );
});

test("loadSearchPageData: a mixed 200 result carries both draft_max and keel_configuration in activeRequirement", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6", keel_configuration: "FIN" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6&keel_configuration=FIN");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.deepEqual(data.activeRequirement, { draft_max: "1.6", keel_configuration: "FIN" });
      }
    },
  );
});

// SLICE-0056: `buildSearchCanonicalPath` must echo FastAPI's own canonical
// query-part ordering exactly (`src/hullq/application/search_read.py`:
// draft_max before keel_configuration) rather than independently deciding
// it.
test("buildSearchCanonicalPath: null activeRequirement is the bare locale path (base state)", () => {
  assert.equal(buildSearchCanonicalPath("en", null), "/en/search");
});

test("buildSearchCanonicalPath: draft-only", () => {
  assert.equal(buildSearchCanonicalPath("de", { draft_max: "1.6" }), "/de/search?draft_max=1.6");
});

test("buildSearchCanonicalPath: keel-only", () => {
  assert.equal(
    buildSearchCanonicalPath("de", { keel_configuration: "FIN" }),
    "/de/search?keel_configuration=FIN",
  );
});

test("buildSearchCanonicalPath: mixed puts draft_max before keel_configuration", () => {
  assert.equal(
    buildSearchCanonicalPath("de", { draft_max: "1.6", keel_configuration: "FIN" }),
    "/de/search?draft_max=1.6&keel_configuration=FIN",
  );
});

// SLICE-0092: the entirely separate, additive design-unresolved
// publisher-claim-only result surface threads through `loadSearchPageData`
// unchanged -- read verbatim from the real API body, never re-derived or
// defaulted away when actually present.
test("loadSearchPageData: a 200 result carries publisher_claim_matches through verbatim", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [
            {
              native_listing_id: "NL-CLAIM-1",
              publishing_organization_id: "ORG-1",
              freshness_status: "CONFIRMED",
              last_confirmed_at: null,
              source_basis: "PUBLISHER_CLAIM",
              criterion_evidence: [
                {
                  criterion: { kind: "NUMERIC", field: "draft_max_m", comparison: "MAXIMUM", threshold_min: null, threshold_max: "1.6" },
                  field: "draft_max_m",
                  truth: "TRUE",
                  reason: null,
                  explanation: "matched",
                  observed_value: "1.4",
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
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.publisherClaimMatchCount, 1);
        assert.equal(data.publisherClaimMatches.length, 1);
        assert.equal(data.publisherClaimMatches[0]?.native_listing_id, "NL-CLAIM-1");
        assert.equal(data.publisherClaimMatches[0]?.source_basis, "PUBLISHER_CLAIM");
      }
    },
  );
});

// SLICE-0096 independent review round 2 Finding C1: a RESULT body missing
// `publisher_claim_matches`/`publisher_claim_match_count` (or any other
// mandatory result-surface field) is a service/contract failure -- never
// silently treated as "no publisher claims" via a default. This used to
// assert the opposite (a defaulted-to-empty `ok` result); the fix for
// Finding C1 is precisely that this incomplete body must now collapse to
// `unavailable`.
test("loadSearchPageData: a 200 result missing publisher_claim_matches is `unavailable`, never a defaulted-empty `ok`", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "unavailable");
    },
  );
});

// SLICE-0085: loa_min/loa_max/rudder_configuration extend the same sparse
// activeRequirement shape and canonical key order
// (hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER: draft_max,
// keel_configuration, loa_max, loa_min, rudder_configuration).

test("buildSearchCanonicalPath: loa range puts loa_max before loa_min", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { loa_min: "10", loa_max: "15" }),
    "/en/search?loa_max=15&loa_min=10",
  );
});

test("buildSearchCanonicalPath: rudder-only", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { rudder_configuration: "SKEG_HUNG" }),
    "/en/search?rudder_configuration=SKEG_HUNG",
  );
});

test("buildSearchCanonicalPath: all five originally accepted keys in canonical order", () => {
  assert.equal(
    buildSearchCanonicalPath("en", {
      draft_max: "1.6",
      keel_configuration: "FIN",
      loa_min: "10",
      loa_max: "15",
      rudder_configuration: "SKEG_HUNG",
    }),
    "/en/search?draft_max=1.6&keel_configuration=FIN&loa_max=15&loa_min=10&rudder_configuration=SKEG_HUNG",
  );
});

// SLICE-0086: hull_configuration/cockpit_position/deck_saloon.

test("buildSearchCanonicalPath: hull-only", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { hull_configuration: "CATAMARAN" }),
    "/en/search?hull_configuration=CATAMARAN",
  );
});

test("buildSearchCanonicalPath: cockpit-only", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { cockpit_position: "CENTER" }),
    "/en/search?cockpit_position=CENTER",
  );
});

test("buildSearchCanonicalPath: deck-saloon-only", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { deck_saloon: "DECK_SALOON" }),
    "/en/search?deck_saloon=DECK_SALOON",
  );
});

test("buildSearchCanonicalPath: deck_saloon before hull_configuration (canonical key order)", () => {
  assert.equal(
    buildSearchCanonicalPath("en", {
      hull_configuration: "CATAMARAN",
      deck_saloon: "DECK_SALOON",
    }),
    "/en/search?deck_saloon=DECK_SALOON&hull_configuration=CATAMARAN",
  );
});

test("buildSearchCanonicalPath: all eight accepted keys in canonical order", () => {
  assert.equal(
    buildSearchCanonicalPath("en", {
      draft_max: "1.6",
      keel_configuration: "FIN",
      loa_min: "10",
      loa_max: "15",
      rudder_configuration: "SKEG_HUNG",
      hull_configuration: "CATAMARAN",
      cockpit_position: "CENTER",
      deck_saloon: "DECK_SALOON",
    }),
    "/en/search?cockpit_position=CENTER&deck_saloon=DECK_SALOON&draft_max=1.6" +
      "&hull_configuration=CATAMARAN&keel_configuration=FIN&loa_max=15&loa_min=10" +
      "&rudder_configuration=SKEG_HUNG",
  );
});

// SLICE-0087: beam_min/beam_max/hull_material.

test("buildSearchCanonicalPath: beam range puts beam_max before beam_min", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { beam_min: "3.2", beam_max: "4.4" }),
    "/en/search?beam_max=4.4&beam_min=3.2",
  );
});

test("buildSearchCanonicalPath: hull-material-only", () => {
  assert.equal(
    buildSearchCanonicalPath("en", { hull_material: "WOOD" }),
    "/en/search?hull_material=WOOD",
  );
});

test("buildSearchCanonicalPath: hull_material before keel_configuration (canonical key order)", () => {
  assert.equal(
    buildSearchCanonicalPath("en", {
      keel_configuration: "FIN",
      hull_material: "WOOD",
    }),
    "/en/search?hull_material=WOOD&keel_configuration=FIN",
  );
});

test("buildSearchCanonicalPath: all eleven accepted keys in canonical order", () => {
  assert.equal(
    buildSearchCanonicalPath("en", {
      draft_max: "1.6",
      keel_configuration: "FIN",
      loa_min: "10",
      loa_max: "15",
      rudder_configuration: "SKEG_HUNG",
      hull_configuration: "CATAMARAN",
      cockpit_position: "CENTER",
      deck_saloon: "DECK_SALOON",
      beam_min: "3.2",
      beam_max: "4.4",
      hull_material: "WOOD",
    }),
    "/en/search?beam_max=4.4&beam_min=3.2&cockpit_position=CENTER&deck_saloon=DECK_SALOON" +
      "&draft_max=1.6&hull_configuration=CATAMARAN&hull_material=WOOD&keel_configuration=FIN" +
      "&loa_max=15&loa_min=10&rudder_configuration=SKEG_HUNG",
  );
});

// SLICE-0096: the bounded-page envelope (evaluation_state/next_cursor)
// threads through into evaluationState/nextPageQueryString.
test("loadSearchPageData: a PARTIAL result builds a nextPageQueryString carrying the real cursor", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 1,
          evaluation_state: "PARTIAL",
          next_cursor: "opaque-cursor-token",
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6&page_size=1");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.evaluationState, "PARTIAL");
        assert.equal(
          data.nextPageQueryString,
          "draft_max=1.6&page_size=1&page_after=opaque-cursor-token",
        );
      }
    },
  );
});

test("loadSearchPageData: a COMPLETE result has no nextPageQueryString", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { draft_max: "1.6" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "draft_max=1.6");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.equal(data.evaluationState, "COMPLETE");
        assert.equal(data.nextPageQueryString, null);
      }
    },
  );
});

test("loadSearchPageData: a loa-only 200 result carries only loa_min/loa_max in activeRequirement", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          locale: "en",
          active_requirement: { loa_min: "10", loa_max: "15" },
          confirmed_matches: [],
          confirmed_match_count: 0,
          insufficient_data_count: 0,
          publisher_claim_matches: [],
          publisher_claim_match_count: 0,
          page_size: 20,
          evaluation_state: "COMPLETE",
          next_cursor: null,
        }),
      );
    },
    async (baseUrl) => {
      const data = await loadSearchPageData(baseUrl, "en", "loa_max=15&loa_min=10");
      assert.equal(data.kind, "ok");
      if (data.kind === "ok") {
        assert.deepEqual(data.activeRequirement, { loa_min: "10", loa_max: "15" });
      }
    },
  );
});
