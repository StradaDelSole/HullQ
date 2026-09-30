// SLICE-0072 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `fetchInventoryEditDetail`/`saveListingOffer`/
// `saveListingClaim`'s real-HTTP-status classification and CSRF header/
// Origin forwarding against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/inventory/{listing}/{edit,offer,
// claim}` routes -- mirrors `brokerInventoryLifecycleApi.test.ts`'s identical
// discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  fetchInventoryEditDetail,
  saveListingClaim,
  saveListingOffer,
} from "../inventoryEditingApi.ts";

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

test("fetchInventoryEditDetail: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          native_listing_id: "NL-1",
          organization_id: "ORG-1",
          lifecycle_state: "DRAFT",
          freshness_status: "CONFIRMED",
          last_confirmed_at: null,
          current_offer_revision_id: "REV-1",
          offer: { "listing_offer.asking_price_mode": "AMOUNT" },
          current_claim_revision_id: "CLAIM-1",
          claim: { "physical_boat.marketed_brand_claim": "Beneteau" },
        }),
      );
    },
    async (baseUrl) => {
      const result = await fetchInventoryEditDetail(baseUrl, "ORG-1", "NL-1", "hullq_session=abc");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.current_offer_revision_id, "REV-1");
        assert.equal(result.data.current_claim_revision_id, "CLAIM-1");
      }
    },
  );
});

test("fetchInventoryEditDetail: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchInventoryEditDetail(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("saveListingOffer: sends the fixed CSRF header and forwards Origin", async () => {
  await withServer(
    (req, res) => {
      assert.equal(req.headers["x-hullq-requested-with"], "professional-inventory-editing-v1");
      assert.equal(req.headers.origin, "https://web.example");
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "SAVED", current_offer_revision_id: "REV-2" }));
    },
    async (baseUrl) => {
      const result = await saveListingOffer(
        baseUrl,
        "ORG-1",
        "NL-1",
        { revision_id: "R-1" },
        "hullq_session=abc",
        "https://web.example",
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.currentOfferRevisionId, "REV-2");
      }
    },
  );
});

test("saveListingOffer: 409 stale version carries the real current revision id", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "STALE_VERSION", current_offer_revision_id: "REV-3" }));
    },
    async (baseUrl) => {
      const result = await saveListingOffer(baseUrl, "ORG-1", "NL-1", {}, null, null);
      assert.equal(result.kind, "stale_version");
      if (result.kind === "stale_version") {
        assert.equal(result.currentOfferRevisionId, "REV-3");
      }
    },
  );
});

test("saveListingOffer: 422 active invariant violation carries blockers", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(422, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          outcome: "ACTIVE_INVARIANT_VIOLATION",
          blockers: ["MARKET_EPISODE_UNRESOLVED"],
        }),
      );
    },
    async (baseUrl) => {
      const result = await saveListingOffer(baseUrl, "ORG-1", "NL-1", {}, null, null);
      assert.equal(result.kind, "active_invariant_violation");
      if (result.kind === "active_invariant_violation") {
        assert.deepEqual(result.blockers, ["MARKET_EPISODE_UNRESOLVED"]);
      }
    },
  );
});

test("saveListingOffer: 403 publishing_denied carries the real reason", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publishing_denied", reason: "PUBLISHER_ROLE_REQUIRED" }));
    },
    async (baseUrl) => {
      const result = await saveListingOffer(baseUrl, "ORG-1", "NL-1", {}, null, null);
      assert.equal(result.kind, "denied");
      if (result.kind === "denied") {
        assert.equal(result.reason, "PUBLISHER_ROLE_REQUIRED");
      }
    },
  );
});

test("saveListingClaim: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "SAVED", current_claim_revision_id: "CLAIM-2" }));
    },
    async (baseUrl) => {
      const result = await saveListingClaim(baseUrl, "ORG-1", "NL-1", {}, null, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.currentClaimRevisionId, "CLAIM-2");
      }
    },
  );
});

test("saveListingClaim: 409 chain_incomplete is distinguished from stale_version", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "chain_incomplete" }));
    },
    async (baseUrl) => {
      const result = await saveListingClaim(baseUrl, "ORG-1", "NL-1", {}, null, null);
      assert.equal(result.kind, "chain_incomplete");
    },
  );
});

test("saveListingClaim: 400 invalid_payload", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_payload" }));
    },
    async (baseUrl) => {
      const result = await saveListingClaim(baseUrl, "ORG-1", "NL-1", {}, null, null);
      assert.equal(result.kind, "invalid_payload");
    },
  );
});
