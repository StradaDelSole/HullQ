// SLICE-0081 PR #327 review finding A bounded web smoke test (no
// PostgreSQL/FastAPI dependency).
//
// Proves the exact defect the review flagged cannot reoccur: a successful
// (200) but malformed/unparsable JSON body from any ONE of the five
// Organization-scoped dashboard panel reads must not reject the composed
// `Promise.all` in `fetchDashboardPanels` and must not affect any sibling
// panel's own result -- each panel is independently resolved to its own
// typed `service_error`, never a thrown rejection that could take down an
// already-authorized panel rendered alongside it. Exercised at multiple
// panel positions, per the review's explicit ask.
import assert from "node:assert/strict";
import http from "node:http";
import { test } from "node:test";

import { fetchDashboardPanels } from "../brokerDashboardPanels.ts";

const ORG_ID = "ORG-1";

const VALID_BODY_BY_PATH: Record<string, unknown> = {
  "/leads/counts": { new_unread: 1, unassigned: 2, follow_up_due: 0, follow_up_overdue: 0 },
  "/leads": { items: [] },
  "/drafts": { drafts: [] },
  "/inventory": { items: [] },
  "/performance": {
    window: "LAST_30_DAYS",
    window_start: "2026-09-12T00:00:00+00:00",
    window_end: "2026-10-12T00:00:00+00:00",
    public_listing_views: 0,
    leads_received: 0,
    leads_contacted: 0,
    leads_closed: 0,
    sold_outcomes: 0,
    sold_outcomes_with_known_source: 0,
    sold_outcomes_with_unknown_source: 0,
    acquisition_source_breakdown: {},
    discovery_source_breakdown: {},
    first_contact_latency_known_count: 0,
    first_contact_latency_unknown_count: 0,
    median_first_contact_latency_seconds: null,
    listings: [],
  },
};

function pathSuffixFor(url: string): string {
  const withoutQuery = url.split("?")[0] ?? url;
  for (const suffix of Object.keys(VALID_BODY_BY_PATH)) {
    if (withoutQuery.endsWith(suffix)) return suffix;
  }
  throw new Error(`unexpected request path: ${url}`);
}

/** Runs `fetchDashboardPanels` against a tiny local server where exactly
 * one of the five routes returns a 200 with an unparsable JSON body; every
 * other route returns its own ordinary valid body. */
async function withOneMalformedPanel(
  malformedPathSuffix: string,
  run: (panels: Awaited<ReturnType<typeof fetchDashboardPanels>>) => void,
): Promise<void> {
  const server = http.createServer((req, res) => {
    const suffix = pathSuffixFor(req.url ?? "");
    res.writeHead(200, { "Content-Type": "application/json" });
    if (suffix === malformedPathSuffix) {
      // Deliberately truncated/unparsable -- a 200 response whose body
      // fails `JSON.parse`, exactly the case the review flagged
      // (`await response.json()` throwing inside the reused client).
      res.end("{not valid json");
    } else {
      res.end(JSON.stringify(VALID_BODY_BY_PATH[suffix]));
    }
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  try {
    const address = server.address();
    if (address === null || typeof address === "string") {
      throw new Error("expected a bound TCP address");
    }
    const baseUrl = `http://127.0.0.1:${address.port}`;
    const panels = await fetchDashboardPanels(baseUrl, ORG_ID, "hullq_session=abc");
    run(panels);
  } finally {
    await new Promise<void>((resolve) => server.close(() => resolve()));
  }
}

test("fetchDashboardPanels: all five routes healthy resolve to ok", async () => {
  await withOneMalformedPanel("__none__", (panels) => {
    assert.equal(panels.leadCounts.kind, "ok");
    assert.equal(panels.leadInbox.kind, "ok");
    assert.equal(panels.drafts.kind, "ok");
    assert.equal(panels.inventory.kind, "ok");
    assert.equal(panels.performance.kind, "ok");
  });
});

test("fetchDashboardPanels: malformed leadCounts body never rejects the composed fetch, never affects siblings", async () => {
  await withOneMalformedPanel("/leads/counts", (panels) => {
    assert.equal(panels.leadCounts.kind, "service_error");
    assert.equal(panels.leadInbox.kind, "ok");
    assert.equal(panels.drafts.kind, "ok");
    assert.equal(panels.inventory.kind, "ok");
    assert.equal(panels.performance.kind, "ok");
  });
});

test("fetchDashboardPanels: malformed drafts body never rejects the composed fetch, never affects siblings", async () => {
  await withOneMalformedPanel("/drafts", (panels) => {
    assert.equal(panels.leadCounts.kind, "ok");
    assert.equal(panels.leadInbox.kind, "ok");
    assert.equal(panels.drafts.kind, "service_error");
    assert.equal(panels.inventory.kind, "ok");
    assert.equal(panels.performance.kind, "ok");
  });
});

test("fetchDashboardPanels: malformed performance body (last panel position) never rejects the composed fetch, never affects siblings", async () => {
  await withOneMalformedPanel("/performance", (panels) => {
    assert.equal(panels.leadCounts.kind, "ok");
    assert.equal(panels.leadInbox.kind, "ok");
    assert.equal(panels.drafts.kind, "ok");
    assert.equal(panels.inventory.kind, "ok");
    assert.equal(panels.performance.kind, "service_error");
  });
});
