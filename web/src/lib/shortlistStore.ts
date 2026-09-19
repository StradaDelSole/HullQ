// SLICE-0058: the only module that reads/writes the anonymous browser-local
// shortlist representation (specs/ANONYMOUS_LOCAL_SHORTLIST_CONTRACT.v0.1.md
// §3/§4). Persists nothing but a versioned list of stable `NativeListingId`
// strings -- no asking price, freshness, broker text or any other listing
// truth ever passes through this module (contract §3).
//
// Client-controlled storage is untrusted input (contract §3): malformed
// JSON, a wrong `version`, non-string/empty entries, duplicates and a
// pathologically large raw payload must all fail safely back to an empty
// store rather than throwing or corrupting the page. `MAX_SHORTLIST_ENTRIES`
// is a technical safety cap only -- never a Free/Pro/account entitlement
// limit (contract §3).
//
// Storage access goes through the small `ShortlistStorageLike` interface
// (matching the ambient `Storage`/`window.localStorage` shape) rather than a
// hard-coded `window.localStorage` reference, so this module has no hidden
// global dependency and stays unit-testable with a plain in-memory fake --
// no DOM/jsdom required.

export const SHORTLIST_STORAGE_KEY = "hullq.shortlist.v1";

/** Technical safety cap on stored entries -- not a commercial limit (contract §3). */
export const MAX_SHORTLIST_ENTRIES = 200;

const MAX_ID_LENGTH = 200;

/** Guards against a pathologically large raw payload before it is even parsed. */
const MAX_RAW_LENGTH = 100_000;

export interface ShortlistStoreV1 {
  version: 1;
  listing_ids: string[];
}

export const EMPTY_SHORTLIST_STORE: ShortlistStoreV1 = Object.freeze({
  version: 1,
  listing_ids: [],
}) as ShortlistStoreV1;

function isValidId(value: unknown): value is string {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_ID_LENGTH;
}

/** De-duplicates while preserving first-seen (buyer-authored) order, bounded by the safety cap. */
function normalizeIds(candidateIds: unknown[]): string[] {
  const seen = new Set<string>();
  const ids: string[] = [];
  for (const candidate of candidateIds) {
    if (!isValidId(candidate)) continue;
    if (seen.has(candidate)) continue;
    seen.add(candidate);
    ids.push(candidate);
    if (ids.length >= MAX_SHORTLIST_ENTRIES) break;
  }
  return ids;
}

/**
 * Parse a raw stored string into a safe, normalized v1 store. Anything that
 * is not exactly a well-formed `{version: 1, listing_ids: string[]}` object
 * (missing, malformed JSON, wrong version, non-array, oversize) recovers to
 * an empty store rather than throwing (contract §3/§13).
 */
export function parseShortlistStore(raw: string | null): ShortlistStoreV1 {
  if (raw === null || raw.length === 0) {
    return { version: 1, listing_ids: [] };
  }
  if (raw.length > MAX_RAW_LENGTH) {
    return { version: 1, listing_ids: [] };
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return { version: 1, listing_ids: [] };
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) {
    return { version: 1, listing_ids: [] };
  }
  const candidate = parsed as Record<string, unknown>;
  if (candidate.version !== 1 || !Array.isArray(candidate.listing_ids)) {
    return { version: 1, listing_ids: [] };
  }
  return { version: 1, listing_ids: normalizeIds(candidate.listing_ids) };
}

export function serializeShortlistStore(store: ShortlistStoreV1): string {
  return JSON.stringify(store);
}

/** `add(existing ID)` is a no-op (contract §4). Buyer-authored insertion order is preserved. */
export function addListingId(store: ShortlistStoreV1, id: string): ShortlistStoreV1 {
  if (!isValidId(id)) return store;
  if (store.listing_ids.includes(id)) return store;
  if (store.listing_ids.length >= MAX_SHORTLIST_ENTRIES) return store;
  return { version: 1, listing_ids: [...store.listing_ids, id] };
}

/** `remove(absent ID)` is a no-op (contract §4). */
export function removeListingId(store: ShortlistStoreV1, id: string): ShortlistStoreV1 {
  if (!store.listing_ids.includes(id)) return store;
  return { version: 1, listing_ids: store.listing_ids.filter((existing) => existing !== id) };
}

/** The ambient `Storage`/`window.localStorage` shape this module actually needs. */
export interface ShortlistStorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
}

/**
 * Read current membership. A storage access failure (disabled storage,
 * private-mode restrictions) recovers to an empty list rather than throwing
 * -- the page must remain usable (contract §13).
 */
export function loadShortlistIds(storage: ShortlistStorageLike): string[] {
  let raw: string | null;
  try {
    raw = storage.getItem(SHORTLIST_STORAGE_KEY);
  } catch {
    return [];
  }
  return parseShortlistStore(raw).listing_ids;
}

function writeShortlistIds(storage: ShortlistStorageLike, ids: string[]): void {
  try {
    storage.setItem(SHORTLIST_STORAGE_KEY, serializeShortlistStore({ version: 1, listing_ids: ids }));
  } catch {
    // Storage unavailable/full/disabled: membership simply doesn't persist
    // for this action. Never crash the page over a storage write failure.
  }
}

export function addToShortlist(storage: ShortlistStorageLike, id: string): string[] {
  const next = addListingId({ version: 1, listing_ids: loadShortlistIds(storage) }, id);
  writeShortlistIds(storage, next.listing_ids);
  return next.listing_ids;
}

export function removeFromShortlist(storage: ShortlistStorageLike, id: string): string[] {
  const next = removeListingId({ version: 1, listing_ids: loadShortlistIds(storage) }, id);
  writeShortlistIds(storage, next.listing_ids);
  return next.listing_ids;
}

export function isInShortlist(storage: ShortlistStorageLike, id: string): boolean {
  return loadShortlistIds(storage).includes(id);
}
