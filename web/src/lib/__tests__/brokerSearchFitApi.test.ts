// SLICE-0084 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchSearchFit`'s real-HTTP-status classification and -- like
// `designAssociationApi.test.ts`'s identical discipline -- that a malformed
// or unexpected-shape JSON body degrades to `{kind: "service_error"}` rather
// than throwing, against a tiny local http server standing in for FastAPI's
// `/api/broker/organizations/{id}/inventory/{listing}/search-fit` route.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { fetchSearchFit, type SearchFitView } from "../brokerSearchFitApi.ts";

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

function jsonResponse(res: http.ServerResponse, status: number, body: unknown): void {
  res.writeHead(status, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}

const VALID_VIEW: SearchFitView = {
  native_listing_id: "NL-1",
  active_requirement: { draft_max: "1.5", keel_configuration: "FIN" },
  result_class: "CONFIRMED_MATCH",
  design_evaluation: {
    design_id: "BD-1",
    result_class: "CONFIRMED_MATCH",
    matching_configuration_ids: ["BD-1::baseline"],
    reason: null,
  },
  design_configuration_evidence: [
    {
      configuration_id: "BD-1::baseline",
      boat_design_id: "BD-1",
      named_variant_id: null,
      truth: "TRUE",
      criterion_evidence: [
        {
          criterion: { kind: "NUMERIC", field: "draft_max_m", comparison: "MAXIMUM" },
          field: "draft_max_m",
          truth: "TRUE",
          reason: null,
          explanation: "draft_max_m=1.30 satisfies MAXIMUM",
          observed_value: "1.30",
        },
      ],
    },
  ],
  criterion_evidence: [
    {
      criterion: { kind: "NUMERIC", field: "draft_max_m", comparison: "MAXIMUM" },
      field: "draft_max_m",
      truth: "TRUE",
      reason: null,
      explanation: "draft_max_m=1.20 satisfies MAXIMUM",
      observed_value: "1.20",
    },
  ],
  blockers: [],
};

test("fetchSearchFit: valid shape is surfaced as ok", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_VIEW),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.result_class, "CONFIRMED_MATCH");
        assert.equal(result.data.criterion_evidence.length, 1);
      }
    },
  );
});

test("fetchSearchFit: malformed (non-JSON) body degrades to service_error, never throws", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("not valid json {{{");
    },
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchSearchFit: a well-formed but structurally wrong-shaped body is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { native_listing_id: "NL-1" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchSearchFit: only the supplied scenario fields are forwarded as query params", async () => {
  await withServer(
    (req, res) => {
      const url = new URL(req.url ?? "", "http://localhost");
      assert.equal(url.searchParams.get("draft_max"), "1.6");
      assert.equal(url.searchParams.has("keel_configuration"), false);
      jsonResponse(res, 200, VALID_VIEW);
    },
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.6" }, null);
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchSearchFit: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 401, { detail: "authentication required" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchSearchFit: 404 is surfaced as not_found (non-enumerating)", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 404, { detail: "organization not found" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchSearchFit: 403 mfa_required body is distinguished from publisher_role_required", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 403, { error: "mfa_required" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchSearchFit: 403 publishing_denied/PUBLISHER_ROLE_REQUIRED body is surfaced distinctly", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 403, { error: "publishing_denied", reason: "PUBLISHER_ROLE_REQUIRED" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "publisher_role_required");
    },
  );
});

test("fetchSearchFit: an unrecognized 403 body is service_error, never silently a known denial", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 403, { error: "something_else" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchSearchFit: 400 invalid_scenario carries the server message", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 400, { error: "invalid_scenario", message: "draft_max must be supplied exactly once" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "invalid_scenario");
      if (result.kind === "invalid_scenario") {
        assert.equal(result.message, "draft_max must be supplied exactly once");
      }
    },
  );
});

test("fetchSearchFit: 409 is surfaced as not_previewable", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { error: "not_previewable" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "not_previewable");
    },
  );
});

test("fetchSearchFit: 503 is surfaced as chain_integrity_fault, never a false technical result", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 503, { error: "chain_integrity_fault" }),
    async (baseUrl) => {
      const result = await fetchSearchFit(baseUrl, "ORG-1", "NL-1", { draftMax: "1.5" }, null);
      assert.equal(result.kind, "chain_integrity_fault");
    },
  );
});

test("fetchSearchFit: network failure collapses to service_error rather than throwing", async () => {
  const result = await fetchSearchFit(
    "http://127.0.0.1:1",
    "ORG-1",
    "NL-1",
    { draftMax: "1.5" },
    null,
  );
  assert.equal(result.kind, "service_error");
});

// SLICE-0085: loa_min/loa_max/rudder_configuration extend the same bounded
// scenario forwarding -- only the supplied fields become query params.
test("fetchSearchFit: loa/rudder scenario fields are forwarded as query params", async () => {
  await withServer(
    (req, res) => {
      const url = new URL(req.url ?? "", "http://localhost");
      assert.equal(url.searchParams.get("loa_min"), "10");
      assert.equal(url.searchParams.get("loa_max"), "15");
      assert.equal(url.searchParams.get("rudder_configuration"), "SKEG_HUNG");
      assert.equal(url.searchParams.has("draft_max"), false);
      jsonResponse(res, 200, VALID_VIEW);
    },
    async (baseUrl) => {
      const result = await fetchSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { loaMin: "10", loaMax: "15", rudderConfiguration: "SKEG_HUNG" },
        null,
      );
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchSearchFit: cookie header is forwarded verbatim", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers.cookie, "hullq_session=abc");
      jsonResponse(res, 200, VALID_VIEW);
    },
    async (baseUrl) => {
      const result = await fetchSearchFit(
        baseUrl,
        "ORG-1",
        "NL-1",
        { draftMax: "1.5" },
        "hullq_session=abc",
      );
      assert.equal(result.kind, "ok");
    },
  );
});
