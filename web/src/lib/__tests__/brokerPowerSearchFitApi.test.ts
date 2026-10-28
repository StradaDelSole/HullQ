// SLICE-0095 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchPowerSearchFit`'s real-HTTP-status classification and --
// like `brokerSearchFitApi.test.ts`'s identical discipline for the
// structurally separate Sail preview -- that a malformed or
// unexpected-shape JSON body degrades to `{kind: "service_error"}` rather
// than throwing, against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/inventory/{listing}/power-search-fit`
// route.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  fetchPowerSearchFit,
  type PowerSearchFitView,
} from "../brokerPowerSearchFitApi.ts";

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

const VALID_CLAIM_ONLY_VIEW: PowerSearchFitView = {
  native_listing_id: "NL-1",
  domain: "POWER",
  active_requirement: { power_drive: "SHAFT", power_engine_count: "2" },
  result_class: "CONFIRMED_MATCH",
  design_evaluation: null,
  design_configuration_evidence: [],
  criterion_evidence: [
    {
      criterion: { kind: "CATEGORICAL", field: "power_drive_configuration", equals: "SHAFT" },
      field: "power_drive_configuration",
      truth: "TRUE",
      reason: null,
      explanation: "power_drive_configuration=SHAFT satisfies SHAFT",
      observed_value: "SHAFT",
    },
  ],
  vessel_category_exclusion: null,
  source_basis: "PUBLISHER_CLAIM",
  blockers: [],
};

test("fetchPowerSearchFit: valid claim-only shape is surfaced as ok", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, VALID_CLAIM_ONLY_VIEW),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.result_class, "CONFIRMED_MATCH");
        assert.equal(result.data.source_basis, "PUBLISHER_CLAIM");
        assert.equal(result.data.design_evaluation, null);
      }
    },
  );
});

test("fetchPowerSearchFit: malformed (non-JSON) body degrades to service_error, never throws", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("not valid json {{{");
    },
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a well-formed but structurally wrong-shaped body is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { native_listing_id: "NL-1" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: a body with domain != POWER is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { ...VALID_CLAIM_ONLY_VIEW, domain: "SAIL" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchPowerSearchFit: only the supplied scenario fields are forwarded as query params", async () => {
  await withServer(
    (req, res) => {
      const url = new URL(req.url ?? "", "http://localhost");
      assert.equal(url.searchParams.get("power_drive"), "SHAFT");
      assert.equal(url.searchParams.has("power_engine_count"), false);
      jsonResponse(res, 200, VALID_CLAIM_ONLY_VIEW);
    },
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "ok");
    },
  );
});

test("fetchPowerSearchFit: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 401, { detail: "authentication required" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchPowerSearchFit: 404 is surfaced as not_found (non-enumerating)", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 404, { detail: "organization not found" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchPowerSearchFit: 403 mfa_required body is distinguished from publisher_role_required", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 403, { error: "mfa_required" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchPowerSearchFit: 403 publishing_denied/PUBLISHER_ROLE_REQUIRED body is surfaced distinctly", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 403, { error: "publishing_denied", reason: "PUBLISHER_ROLE_REQUIRED" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "publisher_role_required");
    },
  );
});

test("fetchPowerSearchFit: 400 invalid_scenario carries the message", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 400, { error: "invalid_scenario", message: "bad value" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "invalid_scenario");
      if (result.kind === "invalid_scenario") {
        assert.equal(result.message, "bad value");
      }
    },
  );
});

test("fetchPowerSearchFit: 409 is not_previewable", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { error: "not_previewable" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "not_previewable");
    },
  );
});

test("fetchPowerSearchFit: 503 is chain_integrity_fault", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 503, { error: "chain_integrity_fault" }),
    async (baseUrl) => {
      const result = await fetchPowerSearchFit(baseUrl, "ORG-1", "NL-1", { powerDrive: "SHAFT" }, null);
      assert.equal(result.kind, "chain_integrity_fault");
    },
  );
});
