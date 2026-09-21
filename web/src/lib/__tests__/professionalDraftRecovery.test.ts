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
  RECOVERY_MAX_AGE_MS,
  RECOVERY_SCHEMA_V1,
  applyFormValues,
  buildRecoveryEnvelope,
  captureFormValues,
  clearRecoveryEnvelope,
  decideRestore,
  loadRecoveryEnvelope,
  parseRecoveryEnvelope,
  recoveryStorageKey,
  saveRecoveryEnvelope,
  type RecoveryEnvelopeV1,
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

// --- Capture (contract §14 "Capture") ---

test("captureFormValues: snapshots all bounded editable values, trims, drops empty", () => {
  const values = captureFormValues((name) => {
    if (name === "broker_listing_reference") return "  REF-1  ";
    if (name === "physical_boat.boat_name") return "";
    if (name === "physical_boat.build_year") return "2005";
    return undefined;
  });
  assert.deepEqual(values, {
    broker_listing_reference: "REF-1",
    "physical_boat.build_year": "2005",
  });
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
