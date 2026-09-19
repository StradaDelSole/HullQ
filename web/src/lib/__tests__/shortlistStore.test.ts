// SLICE-0058 contract §16 "Local store" coverage: empty/missing store, valid
// v1 store, idempotent add/remove, insertion-order preservation, duplicate
// normalization, malformed JSON, wrong version, non-string/empty IDs,
// pathological oversize handling, and that no listing-truth field can ever
// be stored.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  EMPTY_SHORTLIST_STORE,
  MAX_SHORTLIST_ENTRIES,
  SHORTLIST_STORAGE_KEY,
  addListingId,
  addToShortlist,
  isInShortlist,
  loadShortlistIds,
  parseShortlistStore,
  removeFromShortlist,
  removeListingId,
  serializeShortlistStore,
  type ShortlistStorageLike,
} from "../shortlistStore.ts";

/** Plain in-memory fake of `window.localStorage` -- no DOM/jsdom required. */
class FakeStorage implements ShortlistStorageLike {
  private readonly data = new Map<string, string>();

  getItem(key: string): string | null {
    return this.data.has(key) ? this.data.get(key)! : null;
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }
}

test("parseShortlistStore: missing/empty store parses to empty", () => {
  assert.deepEqual(parseShortlistStore(null), { version: 1, listing_ids: [] });
  assert.deepEqual(parseShortlistStore(""), { version: 1, listing_ids: [] });
});

test("parseShortlistStore: valid v1 store round-trips", () => {
  const store = { version: 1 as const, listing_ids: ["NL-1", "NL-2"] };
  assert.deepEqual(parseShortlistStore(serializeShortlistStore(store)), store);
});

test("parseShortlistStore: malformed JSON recovers to empty", () => {
  assert.deepEqual(parseShortlistStore("{not json"), { version: 1, listing_ids: [] });
});

test("parseShortlistStore: wrong version recovers to empty", () => {
  assert.deepEqual(
    parseShortlistStore(JSON.stringify({ version: 2, listing_ids: ["NL-1"] })),
    { version: 1, listing_ids: [] },
  );
});

test("parseShortlistStore: non-array listing_ids recovers to empty", () => {
  assert.deepEqual(
    parseShortlistStore(JSON.stringify({ version: 1, listing_ids: "NL-1" })),
    { version: 1, listing_ids: [] },
  );
});

test("parseShortlistStore: a bare JSON array (not an object) recovers to empty", () => {
  assert.deepEqual(parseShortlistStore(JSON.stringify(["NL-1"])), { version: 1, listing_ids: [] });
});

test("parseShortlistStore: non-string/empty-string IDs are dropped, valid ones kept", () => {
  const raw = JSON.stringify({ version: 1, listing_ids: ["NL-1", 42, null, "", "NL-2"] });
  assert.deepEqual(parseShortlistStore(raw), { version: 1, listing_ids: ["NL-1", "NL-2"] });
});

test("parseShortlistStore: duplicates normalize, first-seen order preserved", () => {
  const raw = JSON.stringify({ version: 1, listing_ids: ["NL-2", "NL-1", "NL-2", "NL-1"] });
  assert.deepEqual(parseShortlistStore(raw), { version: 1, listing_ids: ["NL-2", "NL-1"] });
});

test("parseShortlistStore: pathologically oversized raw payload recovers to empty", () => {
  const huge = JSON.stringify({ version: 1, listing_ids: ["NL-1".repeat(50_000)] });
  assert.deepEqual(parseShortlistStore(huge), { version: 1, listing_ids: [] });
});

test("parseShortlistStore: entry count is bounded by the technical safety cap", () => {
  const manyIds = Array.from({ length: MAX_SHORTLIST_ENTRIES + 50 }, (_, i) => `NL-${i}`);
  const result = parseShortlistStore(JSON.stringify({ version: 1, listing_ids: manyIds }));
  assert.equal(result.listing_ids.length, MAX_SHORTLIST_ENTRIES);
  assert.deepEqual(result.listing_ids, manyIds.slice(0, MAX_SHORTLIST_ENTRIES));
});

test("parseShortlistStore: only version and listing_ids ever survive -- no listing-truth field", () => {
  const raw = JSON.stringify({
    version: 1,
    listing_ids: ["NL-1"],
    asking_price_amount: "125000.00",
    broker_summary: "great boat",
  });
  const result = parseShortlistStore(raw);
  assert.deepEqual(Object.keys(result).sort(), ["listing_ids", "version"]);
});

test("addListingId: adding a new ID appends it, preserving prior order", () => {
  const store = { version: 1 as const, listing_ids: ["NL-1"] };
  assert.deepEqual(addListingId(store, "NL-2"), { version: 1, listing_ids: ["NL-1", "NL-2"] });
});

test("addListingId: adding an existing ID is idempotent (membership unchanged)", () => {
  const store = { version: 1 as const, listing_ids: ["NL-1", "NL-2"] };
  const result = addListingId(store, "NL-1");
  assert.deepEqual(result, store);
});

test("addListingId: an empty/non-string-shaped ID is rejected", () => {
  const store = EMPTY_SHORTLIST_STORE;
  assert.deepEqual(addListingId(store, ""), store);
});

test("addListingId: respects the technical safety cap", () => {
  const full = {
    version: 1 as const,
    listing_ids: Array.from({ length: MAX_SHORTLIST_ENTRIES }, (_, i) => `NL-${i}`),
  };
  assert.deepEqual(addListingId(full, "NL-OVERFLOW"), full);
});

test("removeListingId: removing a present ID drops only that ID", () => {
  const store = { version: 1 as const, listing_ids: ["NL-1", "NL-2", "NL-3"] };
  assert.deepEqual(removeListingId(store, "NL-2"), {
    version: 1,
    listing_ids: ["NL-1", "NL-3"],
  });
});

test("removeListingId: removing an absent ID is idempotent (membership unchanged)", () => {
  const store = { version: 1 as const, listing_ids: ["NL-1"] };
  const result = removeListingId(store, "NL-absent");
  assert.deepEqual(result, store);
});

test("storage-backed helpers: add/remove/load/isInShortlist round-trip through a fake Storage", () => {
  const storage = new FakeStorage();
  assert.deepEqual(loadShortlistIds(storage), []);

  assert.deepEqual(addToShortlist(storage, "NL-1"), ["NL-1"]);
  assert.equal(isInShortlist(storage, "NL-1"), true);

  // Idempotent add.
  assert.deepEqual(addToShortlist(storage, "NL-1"), ["NL-1"]);

  assert.deepEqual(addToShortlist(storage, "NL-2"), ["NL-1", "NL-2"]);
  assert.deepEqual(loadShortlistIds(storage), ["NL-1", "NL-2"]);

  assert.deepEqual(removeFromShortlist(storage, "NL-1"), ["NL-2"]);
  assert.equal(isInShortlist(storage, "NL-1"), false);

  // Idempotent remove.
  assert.deepEqual(removeFromShortlist(storage, "NL-1"), ["NL-2"]);
});

test("storage-backed helpers: a storage read failure recovers to an empty list, page stays usable", () => {
  const throwing: ShortlistStorageLike = {
    getItem() {
      throw new Error("storage disabled");
    },
    setItem() {
      throw new Error("storage disabled");
    },
  };
  assert.deepEqual(loadShortlistIds(throwing), []);
  // A write failure during add must not throw either.
  assert.deepEqual(addToShortlist(throwing, "NL-1"), ["NL-1"]);
});

test("SHORTLIST_STORAGE_KEY is versioned", () => {
  assert.equal(SHORTLIST_STORAGE_KEY, "hullq.shortlist.v1");
});
