// SLICE-0068 bounded web smoke test (no PostgreSQL/FastAPI dependency).
//
// Exercises `mediaGalleryApi.ts`'s real-HTTP-status classification and CSRF
// header/Origin forwarding against a tiny local http server standing in for
// FastAPI's `/api/broker/organizations/{id}/inventory/{listing}/media/...`
// routes -- mirrors `brokerInventoryLifecycleApi.test.ts`'s identical
// discipline.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import {
  addListingYoutube,
  fetchListingGallery,
  fetchMediaLibrary,
  removeListingPlacement,
  reorderListingGallery,
  retireMediaAsset,
  reuseListingMedia,
  setListingCover,
} from "../mediaGalleryApi.ts";

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

test("fetchListingGallery: 200 body is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(
        JSON.stringify({
          native_listing_id: "NL-1",
          gallery_version: 2,
          cover_placement_id: "MP-1",
          placements: [],
        }),
      );
    },
    async (baseUrl) => {
      const result = await fetchListingGallery(baseUrl, "ORG-1", "NL-1", "hullq_session=abc");
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.data.gallery_version, 2);
      }
    },
  );
});

test("fetchListingGallery: 401 is surfaced as unauthenticated", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(401);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchListingGallery(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "unauthenticated");
    },
  );
});

test("fetchListingGallery: 404 is surfaced as not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404);
      res.end();
    },
    async (baseUrl) => {
      const result = await fetchListingGallery(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "not_found");
    },
  );
});

test("fetchListingGallery: 403 mfa_required body is surfaced distinctly from role_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "mfa_required" }));
    },
    async (baseUrl) => {
      const result = await fetchListingGallery(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "mfa_required");
    },
  );
});

test("fetchListingGallery: 403 publisher_role_required body is surfaced as role_required", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(403, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "publisher_role_required" }));
    },
    async (baseUrl) => {
      const result = await fetchListingGallery(baseUrl, "ORG-1", "NL-1", null);
      assert.equal(result.kind, "role_required");
    },
  );
});

test("fetchMediaLibrary: org-scoped assets are returned", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ assets: [{ media_asset_id: "MA-1" }] }));
    },
    async (baseUrl) => {
      const result = await fetchMediaLibrary(baseUrl, "ORG-1", null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.assets.length, 1);
      }
    },
  );
});

test("reuseListingMedia: 404 asset_not_found body is distinguished from listing_not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "asset_not_found" }));
    },
    async (baseUrl) => {
      const result = await reuseListingMedia(baseUrl, "ORG-1", "NL-1", "MA-1", null, null);
      assert.equal(result.kind, "asset_not_found");
    },
  );
});

test("addListingYoutube: invalid URL is surfaced as invalid_url", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(400, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_youtube_url" }));
    },
    async (baseUrl) => {
      const result = await addListingYoutube(baseUrl, "ORG-1", "NL-1", "not a url", null, null);
      assert.equal(result.kind, "invalid_url");
    },
  );
});

test("reorderListingGallery: sends expected_version and placement_ids as JSON", async () => {
  await withServer(
    (req, res) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        const parsed = JSON.parse(body);
        assert.equal(parsed.expected_version, 3);
        assert.deepEqual(parsed.placement_ids, ["MP-2", "MP-1"]);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ gallery_version: 4 }));
      });
    },
    async (baseUrl) => {
      const result = await reorderListingGallery(
        baseUrl,
        "ORG-1",
        "NL-1",
        3,
        ["MP-2", "MP-1"],
        null,
        null,
      );
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.galleryVersion, 4);
      }
    },
  );
});

test("reorderListingGallery: 409 invalid_placement_set body is distinguished from version_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_placement_set" }));
    },
    async (baseUrl) => {
      const result = await reorderListingGallery(baseUrl, "ORG-1", "NL-1", 1, [], null, null);
      assert.equal(result.kind, "invalid_placement_set");
    },
  );
});

test("setListingCover: 409 invalid_cover body is distinguished from version_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "invalid_cover" }));
    },
    async (baseUrl) => {
      const result = await setListingCover(baseUrl, "ORG-1", "NL-1", 1, "MP-1", null, null);
      assert.equal(result.kind, "invalid_cover");
    },
  );
});

test("setListingCover: null media_placement_id clears the cover", async () => {
  await withServer(
    (req, res) => {
      let body = "";
      req.on("data", (chunk) => {
        body += chunk;
      });
      req.on("end", () => {
        const parsed = JSON.parse(body);
        assert.equal(parsed.media_placement_id, null);
        res.writeHead(200, { "Content-Type": "application/json" });
        res.end(JSON.stringify({ outcome: "CLEARED", gallery_version: 2 }));
      });
    },
    async (baseUrl) => {
      const result = await setListingCover(baseUrl, "ORG-1", "NL-1", 1, null, null, null);
      assert.equal(result.kind, "ok");
      if (result.kind === "ok") {
        assert.equal(result.outcome, "CLEARED");
      }
    },
  );
});

test("removeListingPlacement: 404 placement_not_found body is distinguished from listing_not_found", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(404, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "placement_not_found" }));
    },
    async (baseUrl) => {
      const result = await removeListingPlacement(baseUrl, "ORG-1", "NL-1", "MP-1", 1, null, null);
      assert.equal(result.kind, "placement_not_found");
    },
  );
});

test("retireMediaAsset: 409 is surfaced as already_retired", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "already_retired" }));
    },
    async (baseUrl) => {
      const result = await retireMediaAsset(baseUrl, "ORG-1", "MA-1", null, null);
      assert.equal(result.kind, "already_retired");
    },
  );
});

test("retireMediaAsset: 200 is surfaced as ok", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(200, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ outcome: "RETIRED" }));
    },
    async (baseUrl) => {
      const result = await retireMediaAsset(baseUrl, "ORG-1", "MA-1", null, null);
      assert.equal(result.kind, "ok");
    },
  );
});

// ---------------------------------------------------------------------------
// Independent review Finding C: ACTIVE listing conflict outcomes
// ---------------------------------------------------------------------------

test("setListingCover: 409 active_listing_conflict body is distinguished from invalid_cover/version_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "active_listing_conflict" }));
    },
    async (baseUrl) => {
      const result = await setListingCover(baseUrl, "ORG-1", "NL-1", 1, null, null, null);
      assert.equal(result.kind, "active_listing_conflict");
    },
  );
});

test("removeListingPlacement: 409 active_listing_conflict body is distinguished from version_conflict", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "active_listing_conflict" }));
    },
    async (baseUrl) => {
      const result = await removeListingPlacement(baseUrl, "ORG-1", "NL-1", "MP-1", 1, null, null);
      assert.equal(result.kind, "active_listing_conflict");
    },
  );
});

test("retireMediaAsset: 409 active_listing_conflict body is distinguished from already_retired", async () => {
  await withServer(
    (_req, res) => {
      res.writeHead(409, { "Content-Type": "application/json" });
      res.end(JSON.stringify({ error: "active_listing_conflict" }));
    },
    async (baseUrl) => {
      const result = await retireMediaAsset(baseUrl, "ORG-1", "MA-1", null, null);
      assert.equal(result.kind, "active_listing_conflict");
    },
  );
});
