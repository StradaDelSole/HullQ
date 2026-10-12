// SLICE-0082 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchDesignCandidates`/`fetchDesignAssociation`/
// `associateListingDesign`'s real-HTTP-status classification, CSRF header/
// Origin forwarding, and -- independent review Finding C (2026-10-12) --
// that a malformed or unexpected-shape JSON body degrades to
// `{kind: "service_error"}` rather than throwing, against a tiny local http
// server standing in for FastAPI's `/api/broker/organizations/{id}/
// inventory/{listing}/design-{candidates,association}` routes. Mirrors
// `inventoryEditingApi.test.ts`'s identical discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  associateListingDesign,
  fetchDesignAssociation,
  fetchDesignCandidates,
  type DesignCandidate,
} from "../designAssociationApi.ts";

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

const VALID_CANDIDATE: DesignCandidate = {
  boat_design_ref: "BD-1",
  boat_model_id: "BM-1",
  canonical_model_name: "Oceanis 30.1",
  generation: {
    label: "Mk2",
    sequence: 2,
    aliases: [],
    first_built: 2018,
    last_built: 2022,
    hull_number_from: null,
    hull_number_to: null,
    boundary_confidence: "high",
  },
  brand_names: ["Beneteau"],
  first_built: 2016,
  last_built: 2024,
};

// ---------------------------------------------------------------------------
// fetchDesignCandidates
// ---------------------------------------------------------------------------

test("fetchDesignCandidates: valid shape is surfaced as ok", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { candidates: [VALID_CANDIDATE] }),
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "Oceanis", null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.candidates.length, 1);
        assert.equal(result.candidates[0].generation.label, "Mk2");
      }
    },
  );
});

test("fetchDesignCandidates: malformed (non-JSON) body degrades to service_error, never throws", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("not valid json {{{");
    },
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignCandidates: valid JSON but wrong shape (missing generation fields) is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        candidates: [{ boat_design_ref: "BD-1", boat_model_id: "BM-1" }],
      }),
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignCandidates: candidates not an array is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { candidates: "not an array" }),
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignCandidates: 401/404/403/400 map to their distinct kinds", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "not_found");
    },
  );
  await withServer(
    (_req, res) => {
      res.writeHead(403);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "mfa_required");
    },
  );
  await withServer(
    (_req, res) => {
      res.writeHead(400);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchDesignCandidates(baseUrl, "ORG-1", "NL-1", "", null);
      assert.equal(result.kind, "invalid_query");
    },
  );
});

// ---------------------------------------------------------------------------
// fetchDesignAssociation
// ---------------------------------------------------------------------------

test("fetchDesignAssociation: valid UNRESOLVED shape is surfaced as ok", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "UNRESOLVED",
        boat_design_ref: null,
        candidate: null,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.link_status, "UNRESOLVED");
      }
    },
  );
});

test("fetchDesignAssociation: valid LINKED shape with candidate is surfaced as ok", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "LINKED",
        boat_design_ref: "BD-1",
        candidate: VALID_CANDIDATE,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.candidate?.generation.sequence, 2);
      }
    },
  );
});

test("fetchDesignAssociation: malformed body never throws -- degrades to service_error", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("{ not json");
    },
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: an invalid link_status value is service_error, never treated as UNRESOLVED", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "SOMETHING_ELSE",
        boat_design_ref: null,
        candidate: null,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: 409 is chain_incomplete", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "chain_incomplete");
    },
  );
});

// ---------------------------------------------------------------------------
// fetchDesignAssociation: independent review Finding C (second pass) --
// structural consistency, not just per-field shape.
// ---------------------------------------------------------------------------

test("fetchDesignAssociation: UNRESOLVED carrying a non-null boat_design_ref is inconsistent -> service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "UNRESOLVED",
        boat_design_ref: "BD-1",
        candidate: null,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: UNRESOLVED carrying a non-null candidate is inconsistent -> service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "UNRESOLVED",
        boat_design_ref: null,
        candidate: VALID_CANDIDATE,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: LINKED with an empty-string boat_design_ref is service_error, never authoritative presence", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "LINKED",
        boat_design_ref: "",
        candidate: null,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: LINKED with a null boat_design_ref is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "LINKED",
        boat_design_ref: null,
        candidate: null,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: LINKED whose candidate names a *different* design than boat_design_ref is service_error", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "LINKED",
        boat_design_ref: "BD-1",
        candidate: { ...VALID_CANDIDATE, boat_design_ref: "BD-DIFFERENT" },
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("fetchDesignAssociation: LINKED with a matching candidate and LINKED with no candidate are both ok", async () => {
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "LINKED",
        boat_design_ref: "BD-1",
        candidate: VALID_CANDIDATE,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "ok");
    },
  );
  await withServer(
    (_req, res) =>
      jsonResponse(res, 200, {
        native_listing_id: "NL-1",
        link_status: "LINKED",
        boat_design_ref: "BD-1",
        candidate: null,
      }),
    async (baseUrl) => {
      const result = await fetchDesignAssociation(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "ok");
    },
  );
});

// ---------------------------------------------------------------------------
// associateListingDesign
// ---------------------------------------------------------------------------

test("associateListingDesign: sends the fixed CSRF header and forwards Origin", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "broker-design-association-v1");
      assert.equal(req.headers.origin, "https://web.example");
      jsonResponse(res, 201, { outcome: "LINKED", boat_design_ref: "BD-1" });
    },
    async (baseUrl) => {
      const result = await associateListingDesign(
        baseUrl,
        "ORG-1",
        "NL-1",
        "BD-1",
        null,
        "https://web.example",
      );
      assert.equal(result.kind, "ok");
    },
  );
});

test("associateListingDesign: 201 LINKED is surfaced as ok/linked", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 201, { outcome: "LINKED", boat_design_ref: "BD-1" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.outcome, "linked");
        assert.equal(result.storedBoatDesignRef, "BD-1");
      }
    },
  );
});

test("associateListingDesign: 200 ALREADY_LINKED is surfaced as ok/already_linked", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { outcome: "ALREADY_LINKED", boat_design_ref: "BD-1" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") assert.equal(result.outcome, "already_linked");
    },
  );
});

test("associateListingDesign: a 200 body missing boat_design_ref is service_error, never a fabricated ok", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 200, { outcome: "LINKED" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("associateListingDesign: malformed 200 body never throws -- degrades to service_error", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end("not json");
    },
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("associateListingDesign: 409 conflict carries the stored design ref", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { outcome: "CONFLICT", boat_design_ref: "BD-EXISTING" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "conflict");
      if (result.kind === "conflict") assert.equal(result.storedBoatDesignRef, "BD-EXISTING");
    },
  );
});

test("associateListingDesign: an unrecognized 409 body is service_error, never a fabricated conflict", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { surprising: "shape" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("associateListingDesign: a 409 CONFLICT body missing boat_design_ref is service_error, never a conflict with a guessed ref", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { outcome: "CONFLICT" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("associateListingDesign: a 409 CONFLICT body with an empty-string boat_design_ref is service_error", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { outcome: "CONFLICT", boat_design_ref: "" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("associateListingDesign: a malformed (non-JSON) 409 body is service_error, never throws", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end("not json");
    },
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});

test("associateListingDesign: 409 chain_incomplete/shared_boat_conflict error codes are distinguished", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 409, { error: "chain_incomplete" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "chain_incomplete");
    },
  );
  await withServer(
    (_req, res) => jsonResponse(res, 409, { error: "shared_boat_conflict" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "shared_boat_conflict");
    },
  );
});

test("associateListingDesign: 422 design_not_found is surfaced distinctly", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 422, { error: "design_not_found" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "design_not_found");
    },
  );
});

test("associateListingDesign: 403 mfa_required vs publishing_denied are distinguished", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 403, { error: "mfa_required" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "mfa_required");
    },
  );
  await withServer(
    (_req, res) =>
      jsonResponse(res, 403, { error: "publishing_denied", reason: "PUBLISHER_ROLE_REQUIRED" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "denied");
      if (result.kind === "denied") assert.equal(result.reason, "PUBLISHER_ROLE_REQUIRED");
    },
  );
});

test("associateListingDesign: an unrecognized 403 body is service_error, never silently 'denied'", async () => {
  await withServer(
    (_req, res) => jsonResponse(res, 403, { surprising: "shape" }),
    async (baseUrl) => {
      const result = await associateListingDesign(baseUrl, "ORG-1", "NL-1", "BD-1", null, null);
      assert.equal(result.kind, "service_error");
    },
  );
});
