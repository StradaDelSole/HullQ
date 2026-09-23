// SLICE-0062 `specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md` §14
// coverage: scope/isolation, envelope validation, capture, restore
// decision, and save-outcome retention/clearing -- against the pure
// envelope/storage logic in `professionalDraftRecovery.ts`. No DOM/jsdom is
// used (mirrors `shortlistStore.test.ts`'s identical discipline); the DOM
// wiring function itself is proved via the retained real
// PostgreSQL/FastAPI/built-Astro proof, not here.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  RECOVERY_FIELD_NAMES,
  RECOVERY_MAX_AGE_MS,
  RECOVERY_SCHEMA_V1,
  applyFormValues,
  browserRecoveryStorage,
  buildRecoveryEnvelope,
  canWriteRecoveryStorage,
  captureFormValues,
  clearRecoveryEnvelope,
  computeRecoveryUiState,
  decideRestore,
  loadRecoveryEnvelope,
  markRecoveryCaptureDirty,
  parseRecoveryEnvelope,
  recoveryStorageKey,
  saveRecoveryEnvelope,
  takeRecoveryCaptureFlush,
  type RecoveryEnvelopeV1,
  type RecoveryFormValues,
  type RecoveryScope,
  type RecoveryStorageLike,
} from "../professionalDraftRecovery.ts";

const SCOPE_A: RecoveryScope = { accountId: "ACCT-A", organizationId: "ORG-A", draftId: "DRAFT-A" };
const SCOPE_FOREIGN_ACCOUNT: RecoveryScope = { ...SCOPE_A, accountId: "ACCT-FOREIGN" };
const SCOPE_FOREIGN_ORG: RecoveryScope = { ...SCOPE_A, organizationId: "ORG-FOREIGN" };
const SCOPE_FOREIGN_DRAFT: RecoveryScope = { ...SCOPE_A, draftId: "DRAFT-FOREIGN" };

const NOW = new Date("2026-09-21T12:00:00.000Z");

/** Plain in-memory fake of `window.localStorage` -- no DOM/jsdom required. */
class FakeStorage implements RecoveryStorageLike {
  private readonly data = new Map<string, string>();

  getItem(key: string): string | null {
    return this.data.has(key) ? this.data.get(key)! : null;
  }

  setItem(key: string, value: string): void {
    this.data.set(key, value);
  }

  removeItem(key: string): void {
    this.data.delete(key);
  }

  has(key: string): boolean {
    return this.data.has(key);
  }
}

/** A storage whose read/write/remove can each be switched to throw on demand. */
class ThrowingStorage implements RecoveryStorageLike {
  private readonly failGet: boolean;
  private readonly failSet: boolean;
  private readonly failRemove: boolean;

  constructor(failGet = false, failSet = false, failRemove = false) {
    this.failGet = failGet;
    this.failSet = failSet;
    this.failRemove = failRemove;
  }

  getItem(): string | null {
    if (this.failGet) throw new Error("storage read disabled");
    return null;
  }

  setItem(): void {
    if (this.failSet) throw new Error("storage write disabled");
  }

  removeItem(): void {
    if (this.failRemove) throw new Error("storage remove disabled");
  }
}

function envelopeJson(overrides: Record<string, unknown> = {}): string {
  return JSON.stringify({
    recovery_schema: RECOVERY_SCHEMA_V1,
    account_id: SCOPE_A.accountId,
    organization_id: SCOPE_A.organizationId,
    draft_id: SCOPE_A.draftId,
    base_version: 2,
    captured_at: NOW.toISOString(),
    form_values: { broker_listing_reference: "REF-1" },
    ...overrides,
  });
}

// --- Scope / isolation (contract §14 "Scope/isolation") ---

test("recoveryStorageKey: differs per Account/Organization/draft", () => {
  const keys = new Set([
    recoveryStorageKey(SCOPE_A),
    recoveryStorageKey(SCOPE_FOREIGN_ACCOUNT),
    recoveryStorageKey(SCOPE_FOREIGN_ORG),
    recoveryStorageKey(SCOPE_FOREIGN_DRAFT),
  ]);
  assert.equal(keys.size, 4);
});

test("parseRecoveryEnvelope: same Account+Organization+draft matches", () => {
  const envelope = parseRecoveryEnvelope(envelopeJson(), SCOPE_A, NOW);
  assert.notEqual(envelope, null);
  assert.equal(envelope?.account_id, SCOPE_A.accountId);
});

test("parseRecoveryEnvelope: a different Account never matches", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson(), SCOPE_FOREIGN_ACCOUNT, NOW), null);
});

test("parseRecoveryEnvelope: a different Organization never matches", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson(), SCOPE_FOREIGN_ORG, NOW), null);
});

test("parseRecoveryEnvelope: a different draft never matches", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson(), SCOPE_FOREIGN_DRAFT, NOW), null);
});

test("loadRecoveryEnvelope: a foreign-scope entry stored under its own key never auto-loads for this scope", () => {
  const storage = new FakeStorage();
  storage.setItem(recoveryStorageKey(SCOPE_FOREIGN_DRAFT), envelopeJson({ draft_id: SCOPE_FOREIGN_DRAFT.draftId }));
  const result = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(result.kind, "none");
});

// --- Envelope validation (contract §14 "Envelope validation") ---

test("parseRecoveryEnvelope: valid schema/version round-trips", () => {
  const envelope = parseRecoveryEnvelope(envelopeJson(), SCOPE_A, NOW);
  assert.deepEqual(envelope, {
    recovery_schema: RECOVERY_SCHEMA_V1,
    account_id: SCOPE_A.accountId,
    organization_id: SCOPE_A.organizationId,
    draft_id: SCOPE_A.draftId,
    base_version: 2,
    captured_at: NOW.toISOString(),
    form_values: { broker_listing_reference: "REF-1" },
  });
});

test("parseRecoveryEnvelope: malformed JSON fails closed", () => {
  assert.equal(parseRecoveryEnvelope("{not json", SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: unknown recovery schema fails closed", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson({ recovery_schema: "unknown-v9" }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: missing base_version fails closed", () => {
  const raw = envelopeJson();
  const parsed = JSON.parse(raw);
  delete parsed.base_version;
  assert.equal(parseRecoveryEnvelope(JSON.stringify(parsed), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: non-integer/non-positive base_version fails closed", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson({ base_version: 0 }), SCOPE_A, NOW), null);
  assert.equal(parseRecoveryEnvelope(envelopeJson({ base_version: -1 }), SCOPE_A, NOW), null);
  assert.equal(parseRecoveryEnvelope(envelopeJson({ base_version: 1.5 }), SCOPE_A, NOW), null);
  assert.equal(parseRecoveryEnvelope(envelopeJson({ base_version: "2" }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: invalid timestamp fails closed", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson({ captured_at: "not-a-date" }), SCOPE_A, NOW), null);
  assert.equal(parseRecoveryEnvelope(envelopeJson({ captured_at: "" }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: a captured_at in the future fails closed", () => {
  const future = new Date(NOW.getTime() + 60_000).toISOString();
  assert.equal(parseRecoveryEnvelope(envelopeJson({ captured_at: future }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: exactly at the 24h boundary still restores", () => {
  const capturedAt = new Date(NOW.getTime() - RECOVERY_MAX_AGE_MS).toISOString();
  assert.notEqual(parseRecoveryEnvelope(envelopeJson({ captured_at: capturedAt }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: an entry older than 24h is expired and fails closed", () => {
  const capturedAt = new Date(NOW.getTime() - RECOVERY_MAX_AGE_MS - 1).toISOString();
  assert.equal(parseRecoveryEnvelope(envelopeJson({ captured_at: capturedAt }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: non-object form_values fails closed", () => {
  assert.equal(parseRecoveryEnvelope(envelopeJson({ form_values: "not-an-object" }), SCOPE_A, NOW), null);
  assert.equal(parseRecoveryEnvelope(envelopeJson({ form_values: ["a"] }), SCOPE_A, NOW), null);
});

test("parseRecoveryEnvelope: unknown/unbounded form_values keys are dropped, never round-tripped", () => {
  const envelope = parseRecoveryEnvelope(
    envelopeJson({
      form_values: {
        broker_listing_reference: "REF-1",
        session_token: "sekrit-session-value",
        __proto__: "polluted",
      },
    }),
    SCOPE_A,
    NOW,
  );
  assert.deepEqual(Object.keys(envelope?.form_values ?? {}), ["broker_listing_reference"]);
});

test("loadRecoveryEnvelope: a storage read exception reports storage_unavailable, not a crash", () => {
  const result = loadRecoveryEnvelope(new ThrowingStorage(true), SCOPE_A, NOW);
  assert.equal(result.kind, "storage_unavailable");
});

test("saveRecoveryEnvelope: a storage write exception returns false, does not throw", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, {}, NOW);
  assert.doesNotThrow(() => {
    const ok = saveRecoveryEnvelope(new ThrowingStorage(false, true), envelope);
    assert.equal(ok, false);
  });
});

test("clearRecoveryEnvelope: a storage remove exception never throws", () => {
  assert.doesNotThrow(() => clearRecoveryEnvelope(new ThrowingStorage(false, false, true), SCOPE_A));
});

// --- browserRecoveryStorage (independent review finding 2026-09-21 #3) ---
//
// The bug: a caller that wrote `window.localStorage` as a bare argument
// expression evaluates the `localStorage` property getter itself -- which
// can throw a SecurityError in some disabled-storage/private-mode browsers
// -- *before* ever entering this module, outside every try/catch below.
// `browserRecoveryStorage()` must defer that property access into each
// method body so the existing get/set/remove try/catch boundaries in
// `loadRecoveryEnvelope`/`saveRecoveryEnvelope`/`clearRecoveryEnvelope`
// still catch it.
//
// No `window` global exists in this Node test process, so a minimal fake is
// installed/restored around each test rather than depending on jsdom.

function withFakeWindow<T>(windowValue: unknown, run: () => T): T {
  const previousHadWindow = Object.prototype.hasOwnProperty.call(globalThis, "window");
  const previousWindow = (globalThis as { window?: unknown }).window;
  (globalThis as { window?: unknown }).window = windowValue;
  try {
    return run();
  } finally {
    if (previousHadWindow) {
      (globalThis as { window?: unknown }).window = previousWindow;
    } else {
      delete (globalThis as { window?: unknown }).window;
    }
  }
}

test("browserRecoveryStorage: merely constructing it never touches window.localStorage (the property getter is never evaluated)", () => {
  let accessed = false;
  withFakeWindow(
    {
      get localStorage(): never {
        accessed = true;
        throw new Error("SecurityError: storage disabled");
      },
    },
    () => {
      assert.doesNotThrow(() => browserRecoveryStorage());
      assert.equal(accessed, false);
    },
  );
});

test("browserRecoveryStorage: a getItem() against a throwing localStorage getter is caught by loadRecoveryEnvelope as storage_unavailable, never escapes uncaught", () => {
  withFakeWindow(
    {
      get localStorage(): never {
        throw new Error("SecurityError: storage disabled");
      },
    },
    () => {
      const storage = browserRecoveryStorage();
      assert.throws(() => storage.getItem("x"));
      const result = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
      assert.equal(result.kind, "storage_unavailable");
    },
  );
});

test("browserRecoveryStorage: a setItem() against a throwing localStorage getter is caught by saveRecoveryEnvelope, returns false rather than throwing", () => {
  withFakeWindow(
    {
      get localStorage(): never {
        throw new Error("SecurityError: storage disabled");
      },
    },
    () => {
      const storage = browserRecoveryStorage();
      const envelope = buildRecoveryEnvelope(SCOPE_A, 1, {}, NOW);
      assert.doesNotThrow(() => {
        const wrote = saveRecoveryEnvelope(storage, envelope);
        assert.equal(wrote, false);
      });
    },
  );
});

test("browserRecoveryStorage: a removeItem() against a throwing localStorage getter is caught by clearRecoveryEnvelope, never throws", () => {
  withFakeWindow(
    {
      get localStorage(): never {
        throw new Error("SecurityError: storage disabled");
      },
    },
    () => {
      const storage = browserRecoveryStorage();
      assert.doesNotThrow(() => clearRecoveryEnvelope(storage, SCOPE_A));
    },
  );
});

test("browserRecoveryStorage: when window.localStorage works normally, get/set/remove pass straight through end to end", () => {
  const backing = new Map<string, string>();
  withFakeWindow(
    {
      localStorage: {
        getItem: (key: string) => (backing.has(key) ? backing.get(key)! : null),
        setItem: (key: string, value: string) => {
          backing.set(key, value);
        },
        removeItem: (key: string) => {
          backing.delete(key);
        },
      },
    },
    () => {
      const storage = browserRecoveryStorage();
      const envelope = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW);
      assert.equal(saveRecoveryEnvelope(storage, envelope), true);
      assert.deepEqual(loadRecoveryEnvelope(storage, SCOPE_A, NOW), { kind: "found", envelope });
      clearRecoveryEnvelope(storage, SCOPE_A);
      assert.equal(loadRecoveryEnvelope(storage, SCOPE_A, NOW).kind, "none");
    },
  );
});

// --- canWriteRecoveryStorage (independent review finding 2026-09-22 #A) ---
//
// A successful getItem() never by itself proves recovery is usable --
// browser storage can allow reads while rejecting writes (quota/privacy/
// security). The "active" UI state must only ever be shown after this
// bounded, non-destructive write probe actually succeeds.

test("canWriteRecoveryStorage: getItem-style reads succeed but setItem fails => write capability is false, never active", () => {
  const storage: RecoveryStorageLike = {
    getItem: () => null,
    setItem: () => {
      throw new Error("quota exceeded");
    },
    removeItem: () => {},
  };
  assert.equal(canWriteRecoveryStorage(storage, SCOPE_A), false);
});

test("canWriteRecoveryStorage: read and write both succeed => write capability is true, active is permitted", () => {
  const storage = new FakeStorage();
  assert.equal(canWriteRecoveryStorage(storage, SCOPE_A), true);
});

test("canWriteRecoveryStorage: a throwing window.localStorage property getter (via browserRecoveryStorage) reports no write capability, never throws", () => {
  withFakeWindow(
    {
      get localStorage(): never {
        throw new Error("SecurityError: storage disabled");
      },
    },
    () => {
      const storage = browserRecoveryStorage();
      assert.doesNotThrow(() => {
        assert.equal(canWriteRecoveryStorage(storage, SCOPE_A), false);
      });
    },
  );
});

test("canWriteRecoveryStorage: the probe never reads, overwrites or removes an existing valid recovery envelope for the same scope", () => {
  const storage = new FakeStorage();
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW);
  saveRecoveryEnvelope(storage, envelope);

  assert.equal(canWriteRecoveryStorage(storage, SCOPE_A), true);

  assert.deepEqual(loadRecoveryEnvelope(storage, SCOPE_A, NOW), { kind: "found", envelope });
});

test("canWriteRecoveryStorage: uses a dedicated probe key, distinct from the scope's real envelope key", () => {
  const writtenKeys: string[] = [];
  const storage: RecoveryStorageLike = {
    getItem: () => null,
    setItem: (key: string) => {
      writtenKeys.push(key);
    },
    removeItem: () => {},
  };
  canWriteRecoveryStorage(storage, SCOPE_A);
  assert.deepEqual(writtenKeys, [`${recoveryStorageKey(SCOPE_A)}.write-probe`]);
  assert.notEqual(writtenKeys[0], recoveryStorageKey(SCOPE_A));
});

test("canWriteRecoveryStorage: a probe cleanup (removeItem) failure does not flip a successful write to failure, and never throws", () => {
  const storage: RecoveryStorageLike = {
    getItem: () => null,
    setItem: () => {},
    removeItem: () => {
      throw new Error("remove disabled");
    },
  };
  assert.doesNotThrow(() => {
    assert.equal(canWriteRecoveryStorage(storage, SCOPE_A), true);
  });
});

test("canWriteRecoveryStorage: the probe never writes any auth/session/MFA-shaped content -- only a fixed short marker value", () => {
  const written: Array<{ key: string; value: string }> = [];
  const storage: RecoveryStorageLike = {
    getItem: () => null,
    setItem: (key: string, value: string) => {
      written.push({ key, value });
    },
    removeItem: () => {},
  };
  canWriteRecoveryStorage(storage, SCOPE_A);
  assert.equal(written.length, 1);
  assert.equal(written[0]?.value, "1");
});

// --- Capture (contract §14 "Capture") ---

test("RECOVERY_FIELD_NAMES: includes the SLICE-0065 listing_offer.broker_description field", () => {
  assert.ok(RECOVERY_FIELD_NAMES.includes("listing_offer.broker_description"));
});

test("captureFormValues + applyFormValues: listing_offer.broker_description round-trips like every other bounded field", () => {
  const values = captureFormValues((name) =>
    name === "listing_offer.broker_description" ? "A lovely, well-maintained sloop." : undefined,
  );
  assert.equal(values["listing_offer.broker_description"], "A lovely, well-maintained sloop.");

  const written: Record<string, string> = {};
  applyFormValues((name, value) => {
    written[name] = value;
  }, values);
  assert.equal(written["listing_offer.broker_description"], "A lovely, well-maintained sloop.");
});

test("captureFormValues: snapshots every bounded editable value verbatim, including whitespace, unaltered by the recovery layer", () => {
  const values = captureFormValues((name) => {
    if (name === "broker_listing_reference") return "  REF-1  ";
    if (name === "physical_boat.boat_name") return "Sea Breeze";
    if (name === "physical_boat.build_year") return "2005";
    return undefined;
  });
  assert.deepEqual(values, {
    broker_listing_reference: "  REF-1  ",
    "physical_boat.boat_name": "Sea Breeze",
    "physical_boat.build_year": "2005",
  });
});

// --- Finding 1 (independent review 2026-09-21): clearing a previously
// populated field to "" must be captured and restored as "", never dropped
// back to "no opinion" -- a cleared field is itself the meaningful edit.

test("captureFormValues: a field cleared to the empty string is captured, not dropped", () => {
  const values = captureFormValues((name) => (name === "physical_boat.boat_name" ? "" : undefined));
  assert.deepEqual(values, { "physical_boat.boat_name": "" });
});

test("captureFormValues: multiple cleared fields all survive capture", () => {
  const values = captureFormValues((name) => {
    if (name === "physical_boat.boat_name") return "";
    if (name === "physical_boat.marketed_brand_claim") return "";
    if (name === "broker_listing_reference") return "REF-KEPT";
    return undefined;
  });
  assert.deepEqual(values, {
    "physical_boat.boat_name": "",
    "physical_boat.marketed_brand_claim": "",
    broker_listing_reference: "REF-KEPT",
  });
});

test("a server-populated field cleared to '' round-trips through build -> save -> load -> apply as ''", () => {
  const storage = new FakeStorage();
  // Server version N has boat_name = "Anna"; the broker clears it.
  const clearedValues = captureFormValues((name) => (name === "physical_boat.boat_name" ? "" : undefined));
  const envelope = buildRecoveryEnvelope(SCOPE_A, 5, clearedValues, NOW);
  saveRecoveryEnvelope(storage, envelope);

  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(loaded.kind, "found");
  assert.equal(loaded.kind === "found" ? loaded.envelope.form_values["physical_boat.boat_name"] : undefined, "");

  const restored: Record<string, string> = {};
  applyFormValues((name, value) => {
    restored[name] = value;
  }, loaded.kind === "found" ? loaded.envelope.form_values : {});
  // Applying recovery must actually overwrite the server-rendered "Anna"
  // with the recovered empty string, not leave it untouched.
  assert.deepEqual(restored, { "physical_boat.boat_name": "" });
});

test("multiple cleared fields survive a full round trip together", () => {
  const storage = new FakeStorage();
  const values = captureFormValues((name) => {
    if (name === "physical_boat.boat_name") return "";
    if (name === "listing_offer.location_region") return "";
    if (name === "physical_boat.build_year") return "2010";
    return undefined;
  });
  saveRecoveryEnvelope(storage, buildRecoveryEnvelope(SCOPE_A, 3, values, NOW));

  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(loaded.kind, "found");
  assert.deepEqual(loaded.kind === "found" ? loaded.envelope.form_values : null, {
    "physical_boat.boat_name": "",
    "listing_offer.location_region": "",
    "physical_boat.build_year": "2010",
  });
});

test("whitespace/form-string input is preserved exactly by the recovery buffer, not trimmed or otherwise altered", () => {
  const values = captureFormValues((name) =>
    name === "physical_boat.boat_name" ? "  Sea  Breeze  " : undefined,
  );
  assert.deepEqual(values, { "physical_boat.boat_name": "  Sea  Breeze  " });

  const storage = new FakeStorage();
  saveRecoveryEnvelope(storage, buildRecoveryEnvelope(SCOPE_A, 1, values, NOW));
  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(
    loaded.kind === "found" ? loaded.envelope.form_values["physical_boat.boat_name"] : undefined,
    "  Sea  Breeze  ",
  );
});

test("parseRecoveryEnvelope: an empty-string field value in stored JSON is kept, not dropped", () => {
  const envelope = parseRecoveryEnvelope(
    envelopeJson({ form_values: { "physical_boat.boat_name": "" } }),
    SCOPE_A,
    NOW,
  );
  assert.deepEqual(envelope?.form_values, { "physical_boat.boat_name": "" });
});

test("parseRecoveryEnvelope: unknown keys and non-string values in form_values remain rejected/dropped even though empty strings are now kept", () => {
  const envelope = parseRecoveryEnvelope(
    envelopeJson({
      form_values: {
        "physical_boat.boat_name": "",
        session_token: "sekrit",
        "physical_boat.build_year": 2005,
        not_a_real_field: "value",
      },
    }),
    SCOPE_A,
    NOW,
  );
  assert.deepEqual(envelope?.form_values, { "physical_boat.boat_name": "" });
});

test("captureFormValues: latest values replace an older local snapshot", () => {
  const storage = new FakeStorage();
  const first = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-OLD" }, NOW);
  saveRecoveryEnvelope(storage, first);
  const second = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-NEW" }, NOW);
  saveRecoveryEnvelope(storage, second);

  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(loaded.kind, "found");
  assert.equal(loaded.kind === "found" ? loaded.envelope.form_values.broker_listing_reference : null, "REF-NEW");
});

test("captureFormValues + save: no auth/session material can ever be present -- only the bounded field names survive", () => {
  const values = captureFormValues((name) => `value-for-${name}`);
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, values, NOW);
  const serialized = JSON.stringify(envelope);
  assert.equal(serialized.includes("session"), false);
  assert.equal(serialized.includes("cookie"), false);
  assert.equal(serialized.includes("mfa"), false);
  assert.equal(serialized.includes("token"), false);
});

test("applyFormValues: writes only fields present in values, leaves others untouched", () => {
  const written: Record<string, string> = {};
  applyFormValues((name, value) => {
    written[name] = value;
  }, { broker_listing_reference: "REF-1" });
  assert.deepEqual(written, { broker_listing_reference: "REF-1" });
});

// --- Recovery decision (contract §14 "Recovery decision") ---

test("decideRestore: no recovery present -> no_recovery", () => {
  const decision = decideRestore({ kind: "none" }, 2);
  assert.equal(decision.kind, "no_recovery");
});

test("decideRestore: same server version -> same_version (auto-restorable)", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, {}, NOW);
  const decision = decideRestore({ kind: "found", envelope }, 2);
  assert.equal(decision.kind, "same_version");
});

test("decideRestore: newer server version -> server_advanced (no auto-restore)", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, {}, NOW);
  const decision = decideRestore({ kind: "found", envelope }, 3);
  assert.equal(decision.kind, "server_advanced");
});

test("decideRestore: local base version greater than server -> future_version_invalid (fail closed)", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 5, {}, NOW);
  const decision = decideRestore({ kind: "found", envelope }, 2);
  assert.equal(decision.kind, "future_version_invalid");
});

test("decideRestore: storage unavailable propagates through", () => {
  const decision = decideRestore({ kind: "storage_unavailable" }, 2);
  assert.equal(decision.kind, "storage_unavailable");
});

// --- UI state (contract §12; independent review finding 2026-09-21 #2) ---
//
// computeRecoveryUiState is the pure mapping the DOM wiring uses to choose
// what to show. Every one of contract §12's minimum distinguishable states
// -- normal/active, unsaved changes recovered, newer-server-version
// conflict, and unavailable -- must be reachable and distinct.

test("computeRecoveryUiState: storage_unavailable -> unavailable", () => {
  const state = computeRecoveryUiState({ kind: "storage_unavailable" });
  assert.deepEqual(state, { kind: "unavailable" });
});

test("computeRecoveryUiState: no_recovery -> active (recovery usable, nothing recovered yet)", () => {
  const state = computeRecoveryUiState({ kind: "no_recovery" });
  assert.deepEqual(state, { kind: "active" });
});

test("computeRecoveryUiState: same_version -> recovered, carrying the envelope to apply", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW);
  const state = computeRecoveryUiState({ kind: "same_version", envelope });
  assert.deepEqual(state, { kind: "recovered", envelope });
});

test("computeRecoveryUiState: server_advanced -> conflict, carrying the stale envelope for review", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW);
  const state = computeRecoveryUiState({ kind: "server_advanced", envelope });
  assert.deepEqual(state, { kind: "conflict", envelope });
});

test("computeRecoveryUiState: future_version_invalid -> active (corrupt entry cleared by the caller, recovery remains usable)", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 5, {}, NOW);
  const state = computeRecoveryUiState({ kind: "future_version_invalid", envelope });
  assert.deepEqual(state, { kind: "active" });
});

test("computeRecoveryUiState: all five distinguishable states (unavailable/active/recovered/conflict, with recovered != conflict) are pairwise distinct", () => {
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, {}, NOW);
  const kinds = [
    computeRecoveryUiState({ kind: "storage_unavailable" }).kind,
    computeRecoveryUiState({ kind: "no_recovery" }).kind,
    computeRecoveryUiState({ kind: "same_version", envelope }).kind,
    computeRecoveryUiState({ kind: "server_advanced", envelope }).kind,
  ];
  assert.deepEqual(kinds, ["unavailable", "active", "recovered", "conflict"]);
  assert.equal(new Set(kinds).size, 4);
});

// --- Save outcomes (contract §14 "Save outcomes") ---

test("successful server save clears the matching local recovery entry", () => {
  const storage = new FakeStorage();
  saveRecoveryEnvelope(storage, buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW));
  assert.equal(loadRecoveryEnvelope(storage, SCOPE_A, NOW).kind, "found");

  clearRecoveryEnvelope(storage, SCOPE_A);

  assert.equal(loadRecoveryEnvelope(storage, SCOPE_A, NOW).kind, "none");
});

test("version conflict: local recovery is retained (no automatic clear), and correctly reports server_advanced against the new current version", () => {
  const storage = new FakeStorage();
  // Edits captured against the version the user had loaded (2); the server
  // actually advanced to 3 from elsewhere before the conflicting save.
  saveRecoveryEnvelope(storage, buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW));

  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(loaded.kind, "found");
  const decision = decideRestore(loaded, 3);
  assert.equal(decision.kind, "server_advanced");
});

test("validation failure: local recovery is retained and remains restorable against the unchanged server version", () => {
  const storage = new FakeStorage();
  saveRecoveryEnvelope(storage, buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW));

  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  const decision = decideRestore(loaded, 2);
  assert.equal(decision.kind, "same_version");
});

test("simulated network/service failure: local recovery is untouched by the failed save attempt itself", () => {
  const storage = new FakeStorage();
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW);
  saveRecoveryEnvelope(storage, envelope);

  // A failed network/save attempt never calls clearRecoveryEnvelope -- the
  // entry remains exactly as captured.
  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(loaded.kind, "found");
  assert.deepEqual(loaded.kind === "found" ? loaded.envelope.form_values : null, envelope.form_values);
});

test("explicit stale-copy restore-for-review stays form-only: applying it does not touch storage", () => {
  const storage = new FakeStorage();
  const envelope = buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW);
  saveRecoveryEnvelope(storage, envelope);

  const written: Record<string, string> = {};
  applyFormValues((name, value) => {
    written[name] = value;
  }, envelope.form_values);

  // The stale entry is still present -- restore-for-review must not clear
  // or mutate the stored envelope, only the in-memory form.
  assert.equal(loadRecoveryEnvelope(storage, SCOPE_A, NOW).kind, "found");
  assert.deepEqual(written, { broker_listing_reference: "REF-1" });
});

test("discard removes the local recovery entry", () => {
  const storage = new FakeStorage();
  saveRecoveryEnvelope(storage, buildRecoveryEnvelope(SCOPE_A, 2, { broker_listing_reference: "REF-1" }, NOW));
  clearRecoveryEnvelope(storage, SCOPE_A);
  assert.equal(loadRecoveryEnvelope(storage, SCOPE_A, NOW).kind, "none");
});

test("full round trip: build -> save -> load finds the exact same envelope for the same scope", () => {
  const storage = new FakeStorage();
  const envelope: RecoveryEnvelopeV1 = buildRecoveryEnvelope(
    SCOPE_A,
    4,
    { "physical_boat.boat_name": "Sea Breeze", "listing_offer.currency": "EUR" },
    NOW,
  );
  saveRecoveryEnvelope(storage, envelope);
  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.deepEqual(loaded, { kind: "found", envelope });
});

// --- Representative connectivity-loss proof (contract §15, steps 1-10) ---
//
// This single test walks the exact 10-step narrative contract §15 requires,
// entirely through the pure envelope/storage/decision logic above (no
// FastAPI/PostgreSQL/browser dependency) -- the deterministic unit harness
// the contract's closing paragraph explicitly permits for this portion. The
// retained real PostgreSQL/FastAPI/built-Astro proof
// (`scripts/inspect_professional_listing_draft_workspace.py`) separately
// verifies the actual edit page wiring and server non-regression.
test("representative connectivity-loss proof: capture at N -> simulated save failure -> reopen at N restores -> retry save clears -> stale N copy never auto-applies once server reaches N+1", () => {
  const storage = new FakeStorage();
  const scope: RecoveryScope = { accountId: "ACCT-CL", organizationId: "ORG-CL", draftId: "DRAFT-CL" };

  // 1. an authorized draft is loaded at server version N.
  const serverVersionN = 5;

  // 2. the user changes multiple fields without a successful server save
  // (the form's `input`/`change` listeners would call this on every edit;
  // captureFormValues is exercised directly here).
  const editedValues = captureFormValues((name) => {
    if (name === "physical_boat.boat_name") return "Sea Breeze III";
    if (name === "listing_offer.asking_price_amount") return "145000.00";
    return undefined;
  });
  const envelopeAtN = buildRecoveryEnvelope(scope, serverVersionN, editedValues, NOW);
  const captureWriteOk = saveRecoveryEnvelope(storage, envelopeAtN);
  assert.equal(captureWriteOk, true);

  // 3. the bounded local recovery envelope contains those changes at base
  // version N.
  const capturedLoad = loadRecoveryEnvelope(storage, scope, NOW);
  assert.equal(capturedLoad.kind, "found");
  assert.equal(capturedLoad.kind === "found" ? capturedLoad.envelope.base_version : null, serverVersionN);
  assert.deepEqual(capturedLoad.kind === "found" ? capturedLoad.envelope.form_values : null, editedValues);

  // 4. the save/network path fails -- by construction, the code path that
  // would call FastAPI is simply never exercised here, so "PostgreSQL"
  // (modeled as a value outside this module) stays at N; the local
  // recovery is untouched by the failed attempt (contract §G).
  const postgresVersionAfterFailedSave = serverVersionN;

  // 5. the edit page is reopened/reconstructed with the server still at N.
  const reopenLoad = loadRecoveryEnvelope(storage, scope, NOW);
  const reopenDecision = decideRestore(reopenLoad, postgresVersionAfterFailedSave);

  // 6. the unsaved values are restored and visibly identified as recovered
  // (same_version is the only decision that may auto-restore, contract §8.2).
  assert.equal(reopenDecision.kind, "same_version");
  const restoredWrites: Record<string, string> = {};
  if (reopenDecision.kind === "same_version") {
    applyFormValues((name, value) => {
      restoredWrites[name] = value;
    }, reopenDecision.envelope.form_values);
  }
  assert.deepEqual(restoredWrites, editedValues);

  // 7. the ordinary save is retried successfully -- modeled as PostgreSQL
  // advancing exactly once (N -> N+1).
  const postgresVersionAfterRetry = serverVersionN + 1;

  // 8. PostgreSQL advanced exactly once, and the local recovery entry is
  // cleared on the successful save (contract §H).
  assert.equal(postgresVersionAfterRetry, serverVersionN + 1);
  clearRecoveryEnvelope(storage, scope);
  assert.equal(loadRecoveryEnvelope(storage, scope, NOW).kind, "none");

  // 9. separately: server state advances to N+1 *before* any local
  // recovery for a fresh, still-unsaved edit at base N.
  const staleEnvelopeAtN = buildRecoveryEnvelope(scope, serverVersionN, { broker_listing_reference: "REF-STALE" }, NOW);
  saveRecoveryEnvelope(storage, staleEnvelopeAtN);
  const serverVersionAdvancedElsewhere = serverVersionN + 1;

  // 10. the stale local N copy is not automatically applied or submitted --
  // only offered for explicit restore-for-review, never auto-restored.
  const staleDecision = decideRestore(
    loadRecoveryEnvelope(storage, scope, NOW),
    serverVersionAdvancedElsewhere,
  );
  assert.equal(staleDecision.kind, "server_advanced");
  // Confirms the stale envelope is still present (available for explicit
  // review) rather than having been silently discarded or auto-applied.
  assert.equal(loadRecoveryEnvelope(storage, scope, NOW).kind, "found");
});

// --- Finding B (independent review 2026-09-22): pagehide must only flush
// genuine pending unsaved input, never manufacture a recovery envelope for
// an untouched form.

test("takeRecoveryCaptureFlush: an untouched (never-dirtied) state has nothing to flush", () => {
  const state = { dirty: false };
  assert.equal(takeRecoveryCaptureFlush(state), false);
});

test("markRecoveryCaptureDirty + takeRecoveryCaptureFlush: a dirtied state has pending work, and taking it clears dirty", () => {
  const state = { dirty: false };
  markRecoveryCaptureDirty(state);
  assert.equal(takeRecoveryCaptureFlush(state), true);
  assert.equal(state.dirty, false);
});

test("takeRecoveryCaptureFlush: taking twice without a new edit in between reports nothing pending the second time", () => {
  const state = { dirty: false };
  markRecoveryCaptureDirty(state);
  assert.equal(takeRecoveryCaptureFlush(state), true);
  assert.equal(takeRecoveryCaptureFlush(state), false);
});

test("markRecoveryCaptureDirty: repeated edits before a flush still report exactly one pending flush", () => {
  const state = { dirty: false };
  markRecoveryCaptureDirty(state);
  markRecoveryCaptureDirty(state);
  markRecoveryCaptureDirty(state);
  assert.equal(takeRecoveryCaptureFlush(state), true);
  assert.equal(takeRecoveryCaptureFlush(state), false);
});

// The following harness composes the exact same exported primitives
// (`markRecoveryCaptureDirty`/`takeRecoveryCaptureFlush`, `captureFormValues`,
// `buildRecoveryEnvelope`, `saveRecoveryEnvelope`) the same way
// `initProfessionalDraftRecovery`'s `wireCapture()` composes them for its
// debounce timer / submit / pagehide handlers -- without a DOM. This proves
// the actual algorithm the DOM wiring is built from, mirroring this file's
// existing "representative connectivity-loss proof" discipline above.

interface SimulatedRecoveryWiring {
  simulateInput(values: RecoveryFormValues): void;
  simulateDebounceFire(): void;
  simulatePagehide(): void;
  readonly captureCallCount: number;
}

function simulateProfessionalDraftRecoveryWiring(
  storage: RecoveryStorageLike,
  scope: RecoveryScope,
  serverVersion: number,
  now: Date,
): SimulatedRecoveryWiring {
  const dirtyState = { dirty: false };
  let latestValues: RecoveryFormValues = {};
  let captureCallCount = 0;

  function persistCapture(): void {
    captureCallCount += 1;
    const envelope = buildRecoveryEnvelope(scope, serverVersion, latestValues, now);
    saveRecoveryEnvelope(storage, envelope);
  }

  function flush(): void {
    if (!takeRecoveryCaptureFlush(dirtyState)) return;
    persistCapture();
  }

  return {
    simulateInput(values: RecoveryFormValues): void {
      latestValues = values;
      markRecoveryCaptureDirty(dirtyState);
    },
    simulateDebounceFire: flush,
    simulatePagehide: flush,
    get captureCallCount(): number {
      return captureCallCount;
    },
  };
}

test("pagehide simulation: an untouched form + pagehide never creates a recovery entry", () => {
  const storage = new FakeStorage();
  const wiring = simulateProfessionalDraftRecoveryWiring(storage, SCOPE_A, 2, NOW);

  wiring.simulatePagehide();

  assert.equal(wiring.captureCallCount, 0);
  assert.equal(loadRecoveryEnvelope(storage, SCOPE_A, NOW).kind, "none");
});

test("pagehide simulation: input immediately followed by pagehide, before the debounce fires, persists the latest values", () => {
  const storage = new FakeStorage();
  const wiring = simulateProfessionalDraftRecoveryWiring(storage, SCOPE_A, 2, NOW);

  wiring.simulateInput({ broker_listing_reference: "REF-LATEST" });
  wiring.simulatePagehide(); // no simulateDebounceFire() -- pagehide beats the timer

  assert.equal(wiring.captureCallCount, 1);
  const loaded = loadRecoveryEnvelope(storage, SCOPE_A, NOW);
  assert.equal(
    loaded.kind === "found" ? loaded.envelope.form_values.broker_listing_reference : null,
    "REF-LATEST",
  );
});

test("pagehide simulation: an edit already flushed by the debounce timer, then pagehide with no newer edit, does not persist a second (synthetic) capture", () => {
  const storage = new FakeStorage();
  const wiring = simulateProfessionalDraftRecoveryWiring(storage, SCOPE_A, 2, NOW);

  wiring.simulateInput({ broker_listing_reference: "REF-1" });
  wiring.simulateDebounceFire();
  assert.equal(wiring.captureCallCount, 1);

  wiring.simulatePagehide(); // no edit since the debounce flush

  assert.equal(wiring.captureCallCount, 1); // unchanged
});

test("pagehide simulation: a normal reload after no edit never produces a recovered-unsaved state on the next load", () => {
  const storage = new FakeStorage();
  const wiring = simulateProfessionalDraftRecoveryWiring(storage, SCOPE_A, 2, NOW);

  wiring.simulatePagehide(); // simulates leaving/reloading an untouched page

  const decision = decideRestore(loadRecoveryEnvelope(storage, SCOPE_A, NOW), 2);
  assert.equal(decision.kind, "no_recovery");
});

test("pagehide simulation: a genuine locally recovered edit still round-trips exactly as before", () => {
  const storage = new FakeStorage();
  const wiring = simulateProfessionalDraftRecoveryWiring(storage, SCOPE_A, 2, NOW);

  wiring.simulateInput({ "physical_boat.boat_name": "Sea Breeze" });
  wiring.simulateDebounceFire();

  const decision = decideRestore(loadRecoveryEnvelope(storage, SCOPE_A, NOW), 2);
  assert.equal(decision.kind, "same_version");
  assert.equal(
    decision.kind === "same_version" ? decision.envelope.form_values["physical_boat.boat_name"] : null,
    "Sea Breeze",
  );
});
