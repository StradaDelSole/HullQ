// SLICE-0062: the bounded browser-local recovery buffer for one existing,
// authorized `ProfessionalListingDraft` edit page
// (`specs/PROFESSIONAL_LISTING_RECOVERY_CONTRACT.v0.1.md`). This module never
// talks to FastAPI and never becomes server truth (contract §2) -- it only
// repopulates form controls so ordinary connectivity interruption does not
// silently destroy recent unsaved input.
//
// Every envelope this module writes/reads is scoped to an exact
// Account + Organization + Draft tuple, both by storage key (contract §4:
// "a different Account/Organization/draft MUST NOT auto-load the recovery")
// and, defensively, by validating the same three identifiers stored inside
// the envelope itself -- a mismatch on either axis fails closed exactly like
// malformed JSON or an expired entry (contract §6).
//
// `form_values` is hard-limited to the fixed bounded vocabulary in
// `RECOVERY_FIELD_NAMES` (contract §5): any other key present in stored
// JSON -- including anything that looks like session/auth/MFA material --
// is silently dropped during parsing, never round-tripped, never restored.
//
// Storage access goes through the small `RecoveryStorageLike` interface
// (matching `window.localStorage`'s shape) rather than a hard-coded global
// reference, so the pure envelope/storage logic below stays unit-testable
// with a plain in-memory fake -- no DOM/jsdom required (mirrors
// `shortlistStore.ts`'s identical rationale). `browserRecoveryStorage()` is
// the one blessed way browser wiring should obtain that interface: it never
// touches `window.localStorage` itself at call time, only inside each
// method, so a `SecurityError` thrown by the `localStorage` property getter
// itself -- not just by `getItem`/`setItem`/`removeItem` -- still lands
// inside this module's existing try/catch rather than escaping uncaught
// before the module is ever entered (independent review finding
// 2026-09-21 #3).
//
// `computeRecoveryUiState()` is the pure mapping from a restore decision to
// the visible recovery state contract §12 requires (normal/active,
// recovered, conflict, unavailable) and stays unit-testable the same way.
// The DOM-wiring function at the bottom of this file (`renderRecoveryBanner`
// / `initProfessionalDraftRecovery`) is the only part that touches
// `document`/`window` directly; it is exercised by the retained real
// PostgreSQL/FastAPI/built-Astro proof rather than by a unit test, mirroring
// `shortlistButtons.ts`'s identical split between pure logic and thin DOM
// wiring.
//
// `canWriteRecoveryStorage()` closes independent review finding
// 2026-09-22 #A: a successful `getItem()` never by itself proves recovery
// is usable, because browser storage can allow reads while rejecting
// writes (quota/privacy/security). The "active" UI state is only ever
// shown after this bounded, non-destructive write probe actually succeeds.
//
// `markRecoveryCaptureDirty()`/`takeRecoveryCaptureFlush()` close
// independent review finding 2026-09-22 #B: `pagehide` (and submit) must
// flush only genuine pending unsaved input, never manufacture a recovery
// envelope for a form nobody touched -- these two pure functions are the
// exact dirty-tracking primitives the DOM wiring's debounce/submit/
// pagehide handlers are composed from, and are unit-tested both directly
// and via a small DOM-free simulation of that composition.

export const RECOVERY_SCHEMA_V1 = "professional-listing-draft-recovery-v1";

/** Contract §6: 24 hours maximum from `captured_at`. */
export const RECOVERY_MAX_AGE_MS = 24 * 60 * 60 * 1000;

/** Contract §5: the exact bounded editable 0061 form vocabulary -- nothing else is ever captured or restored. */
export const RECOVERY_FIELD_NAMES = [
  "broker_listing_reference",
  "physical_boat.marketed_brand_claim",
  "physical_boat.model_designation_claim",
  "physical_boat.build_year",
  "physical_boat.boat_name",
  "listing_offer.asking_price_mode",
  "listing_offer.asking_price_amount",
  "listing_offer.currency",
  "listing_offer.location_country",
  "listing_offer.location_region",
  "listing_offer.broker_description",
] as const;

export type RecoveryFieldName = (typeof RECOVERY_FIELD_NAMES)[number];

export type RecoveryFormValues = Partial<Record<RecoveryFieldName, string>>;

export interface RecoveryScope {
  accountId: string;
  organizationId: string;
  draftId: string;
}

export interface RecoveryEnvelopeV1 {
  recovery_schema: typeof RECOVERY_SCHEMA_V1;
  account_id: string;
  organization_id: string;
  draft_id: string;
  base_version: number;
  captured_at: string;
  form_values: RecoveryFormValues;
}

const RECOVERY_KEY_PREFIX = "hullq.professional-draft-recovery.v1";

/**
 * Every distinct Account/Organization/draft tuple gets its own storage key,
 * so a foreign scope simply finds nothing rather than needing a runtime
 * cross-check to refuse a match (contract §4).
 */
export function recoveryStorageKey(scope: RecoveryScope): string {
  return [
    RECOVERY_KEY_PREFIX,
    encodeURIComponent(scope.accountId),
    encodeURIComponent(scope.organizationId),
    encodeURIComponent(scope.draftId),
  ].join(".");
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

/**
 * Drops any key outside the bounded vocabulary and any non-string value
 * (contract §5/§11). An empty string is a valid, meaningful captured value
 * (independent review finding 2026-09-21 #1: clearing a previously
 * populated field is itself the edit being recovered) and is kept, not
 * dropped.
 */
function sanitizeFormValues(value: unknown): RecoveryFormValues | null {
  if (typeof value !== "object" || value === null || Array.isArray(value)) return null;
  const record = value as Record<string, unknown>;
  const result: RecoveryFormValues = {};
  for (const name of RECOVERY_FIELD_NAMES) {
    const candidate = record[name];
    if (typeof candidate === "string") {
      result[name] = candidate;
    }
  }
  return result;
}

/**
 * Validates a raw stored string against *scope* and *now*. Anything
 * malformed, mismatched, unknown-schema, non-positive-integer version,
 * unparsable/future timestamp, or expired (>24h) fails closed to `null`
 * (contract §6) -- including a scope that does not exactly match the
 * current Account/Organization/draft (contract §4).
 */
export function parseRecoveryEnvelope(
  raw: string,
  scope: RecoveryScope,
  now: Date,
): RecoveryEnvelopeV1 | null {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch {
    return null;
  }
  if (typeof parsed !== "object" || parsed === null || Array.isArray(parsed)) return null;
  const candidate = parsed as Record<string, unknown>;

  if (candidate.recovery_schema !== RECOVERY_SCHEMA_V1) return null;
  if (candidate.account_id !== scope.accountId) return null;
  if (candidate.organization_id !== scope.organizationId) return null;
  if (candidate.draft_id !== scope.draftId) return null;
  if (!isPositiveInteger(candidate.base_version)) return null;
  if (typeof candidate.captured_at !== "string" || candidate.captured_at.length === 0) return null;

  const capturedAtMs = Date.parse(candidate.captured_at);
  if (Number.isNaN(capturedAtMs)) return null;
  const ageMs = now.getTime() - capturedAtMs;
  // A negative age (captured "in the future") is as nonsensical/corrupt as
  // an expired entry -- fail closed rather than restore it.
  if (ageMs < 0) return null;
  if (ageMs > RECOVERY_MAX_AGE_MS) return null;

  const formValues = sanitizeFormValues(candidate.form_values);
  if (formValues === null) return null;

  return {
    recovery_schema: RECOVERY_SCHEMA_V1,
    account_id: scope.accountId,
    organization_id: scope.organizationId,
    draft_id: scope.draftId,
    base_version: candidate.base_version,
    captured_at: candidate.captured_at,
    form_values: formValues,
  };
}

export function buildRecoveryEnvelope(
  scope: RecoveryScope,
  baseVersion: number,
  formValues: RecoveryFormValues,
  now: Date,
): RecoveryEnvelopeV1 {
  return {
    recovery_schema: RECOVERY_SCHEMA_V1,
    account_id: scope.accountId,
    organization_id: scope.organizationId,
    draft_id: scope.draftId,
    base_version: baseVersion,
    captured_at: now.toISOString(),
    form_values: sanitizeFormValues(formValues) ?? {},
  };
}

/** The ambient `Storage`/`window.localStorage` shape this module actually needs. */
export interface RecoveryStorageLike {
  getItem(key: string): string | null;
  setItem(key: string, value: string): void;
  removeItem(key: string): void;
}

/**
 * Lazily wraps `window.localStorage` for browser wiring callers. Merely
 * *calling* this factory never touches `window.localStorage` itself -- each
 * returned method only evaluates the `localStorage` property when actually
 * invoked. That matters because the `localStorage` property getter itself
 * (not just `getItem`/`setItem`/`removeItem`) can throw a `SecurityError` in
 * some disabled-storage/private-mode browsers; a caller that instead wrote
 * `window.localStorage` as a bare argument expression would throw before
 * ever entering this module, outside every try/catch below (independent
 * review finding 2026-09-21 #3). Routed through here, that same exception
 * surfaces only inside `loadRecoveryEnvelope`/`saveRecoveryEnvelope`/
 * `clearRecoveryEnvelope`'s existing try/catch around `storage.getItem(...)`
 * /`setItem(...)`/`removeItem(...)`, which already treat it as an ordinary
 * storage failure (contract §6/§I) -- no separate try/catch is needed here.
 */
export function browserRecoveryStorage(): RecoveryStorageLike {
  return {
    getItem(key: string): string | null {
      return window.localStorage.getItem(key);
    },
    setItem(key: string, value: string): void {
      window.localStorage.setItem(key, value);
    },
    removeItem(key: string): void {
      window.localStorage.removeItem(key);
    },
  };
}

export type RecoveryLoadResult =
  | { kind: "storage_unavailable" }
  | { kind: "none" }
  | { kind: "found"; envelope: RecoveryEnvelopeV1 };

/**
 * Reads the current scope's entry. A storage-read exception (disabled
 * storage, security exception) reports `storage_unavailable` rather than
 * throwing (contract §6/§I); a missing, malformed or expired entry reports
 * `none` and is best-effort removed so it is not re-parsed on every load.
 */
export function loadRecoveryEnvelope(
  storage: RecoveryStorageLike,
  scope: RecoveryScope,
  now: Date,
): RecoveryLoadResult {
  const key = recoveryStorageKey(scope);
  let raw: string | null;
  try {
    raw = storage.getItem(key);
  } catch {
    return { kind: "storage_unavailable" };
  }
  if (raw === null) return { kind: "none" };

  const envelope = parseRecoveryEnvelope(raw, scope, now);
  if (envelope === null) {
    try {
      storage.removeItem(key);
    } catch {
      // Best-effort only -- a removal failure must not break drafting.
    }
    return { kind: "none" };
  }
  return { kind: "found", envelope };
}

/** Reports whether the write actually landed -- callers must never claim recovery is active on a failed write (contract §I). */
export function saveRecoveryEnvelope(storage: RecoveryStorageLike, envelope: RecoveryEnvelopeV1): boolean {
  const key = recoveryStorageKey({
    accountId: envelope.account_id,
    organizationId: envelope.organization_id,
    draftId: envelope.draft_id,
  });
  try {
    storage.setItem(key, JSON.stringify(envelope));
    return true;
  } catch {
    return false;
  }
}

/** Clears the current scope's entry, e.g. after a successful server save (contract §H). Never throws. */
export function clearRecoveryEnvelope(storage: RecoveryStorageLike, scope: RecoveryScope): void {
  try {
    storage.removeItem(recoveryStorageKey(scope));
  } catch {
    // Storage unavailable -- nothing further to do; never break drafting.
  }
}

/**
 * Bounded, non-destructive probe of whether *storage* can actually persist
 * data for *scope*, not just read it -- browser storage can allow reads
 * while rejecting writes (quota/privacy/security restrictions), and
 * contract §6/§I forbids claiming recovery is active on the strength of a
 * successful read alone (independent review finding 2026-09-22 #A). Uses a
 * dedicated per-scope probe key -- distinct from `recoveryStorageKey`, so
 * an existing valid recovery envelope for this scope is never read,
 * overwritten or removed by the probe -- writes a small throwaway marker,
 * then best-effort removes it. Cleanup failure does not change the
 * verdict: the write itself is what is being tested, and a stray leftover
 * probe key never carries auth/session/MFA material and never breaks
 * drafting.
 */
export function canWriteRecoveryStorage(storage: RecoveryStorageLike, scope: RecoveryScope): boolean {
  const key = `${recoveryStorageKey(scope)}.write-probe`;
  try {
    storage.setItem(key, "1");
  } catch {
    return false;
  }
  try {
    storage.removeItem(key);
  } catch {
    // Best-effort cleanup only -- never flips a successful write probe to
    // failure, and never breaks drafting.
  }
  return true;
}

export type RestoreDecision =
  | { kind: "storage_unavailable" }
  | { kind: "no_recovery" }
  | { kind: "same_version"; envelope: RecoveryEnvelopeV1 }
  | { kind: "server_advanced"; envelope: RecoveryEnvelopeV1 }
  | { kind: "future_version_invalid"; envelope: RecoveryEnvelopeV1 };

/**
 * Implements contract §8's restore decision table. `same_version` is the
 * only case that may auto-restore; `server_advanced` must never auto-apply
 * or auto-submit; `future_version_invalid` (local base_version > current
 * server version) is corrupt for v0.1 and must never auto-restore either.
 */
export function decideRestore(load: RecoveryLoadResult, serverVersion: number): RestoreDecision {
  if (load.kind === "storage_unavailable") return { kind: "storage_unavailable" };
  if (load.kind === "none") return { kind: "no_recovery" };
  const { envelope } = load;
  if (envelope.base_version === serverVersion) return { kind: "same_version", envelope };
  if (envelope.base_version < serverVersion) return { kind: "server_advanced", envelope };
  return { kind: "future_version_invalid", envelope };
}

/**
 * The minimum set of visible recovery states contract §12 requires the edit
 * page to distinguish. `active` covers both "no envelope yet, but recovery
 * is usable" and "the stale/corrupt envelope for this scope was just
 * cleared" -- in both cases local recovery capability itself remains
 * available for subsequent edits (independent review finding 2026-09-21
 * #2), which is a distinct, required state from `recovered`/`conflict`/
 * `unavailable`.
 */
export type RecoveryUiState =
  | { kind: "unavailable" }
  | { kind: "active" }
  | { kind: "recovered"; envelope: RecoveryEnvelopeV1 }
  | { kind: "conflict"; envelope: RecoveryEnvelopeV1 };

/**
 * Pure mapping from a restore decision to the visible UI state (contract
 * §12). Kept separate from `initProfessionalDraftRecovery`'s DOM rendering
 * so the state selection itself stays unit-testable without a DOM.
 */
export function computeRecoveryUiState(decision: RestoreDecision): RecoveryUiState {
  switch (decision.kind) {
    case "storage_unavailable":
      return { kind: "unavailable" };
    case "no_recovery":
      return { kind: "active" };
    case "same_version":
      return { kind: "recovered", envelope: decision.envelope };
    case "server_advanced":
      return { kind: "conflict", envelope: decision.envelope };
    case "future_version_invalid":
      // Corrupt for v0.1 (contract §8.4): never surfaced as recovered; the
      // caller clears the stale entry, after which recovery is simply
      // active again for this scope.
      return { kind: "active" };
  }
}

/**
 * Pure field-value capture: *read* is called once per bounded field name and
 * every string result is kept verbatim, including an empty string --
 * independent review finding 2026-09-21 #1: a broker clearing a previously
 * populated field (e.g. `boat_name`) is a meaningful edit that must survive
 * recovery exactly as typed, not be silently dropped back to "no opinion".
 * The recovery layer never trims/normalizes; server validation/normalization
 * remains authoritative on real Save (contract §5). Takes a plain reader
 * function rather than a form element so this stays unit-testable without a
 * DOM (the DOM-backed reader lives in `initProfessionalDraftRecovery` below).
 */
export function captureFormValues(
  read: (name: RecoveryFieldName) => string | null | undefined,
): RecoveryFormValues {
  const values: RecoveryFormValues = {};
  for (const name of RECOVERY_FIELD_NAMES) {
    const raw = read(name);
    if (typeof raw !== "string") continue;
    values[name] = raw;
  }
  return values;
}

/**
 * Pure restore application: calls *write* once per bounded field name present
 * in *values*. The DOM-backed writer in `initProfessionalDraftRecovery`
 * assigns `.value` directly (a form-control API), never `innerHTML` or any
 * other executable-string insertion (contract §J/§11).
 */
export function applyFormValues(
  write: (name: RecoveryFieldName, value: string) => void,
  values: RecoveryFormValues,
): void {
  for (const name of RECOVERY_FIELD_NAMES) {
    const value = values[name];
    if (value === undefined) continue;
    write(name, value);
  }
}

/**
 * Pure dirty-tracking state the DOM wiring's debounce/submit/pagehide
 * handlers are built from (independent review finding 2026-09-22 #B):
 * `pagehide` must flush only genuine pending unsaved input, never
 * manufacture a recovery envelope (or a fresh `captured_at`) for a form
 * nobody touched since the last successful flush.
 */
export interface RecoveryCaptureDirtyState {
  dirty: boolean;
}

export function markRecoveryCaptureDirty(state: RecoveryCaptureDirtyState): void {
  state.dirty = true;
}

/**
 * Reports whether there was pending dirty state to flush, clearing it as a
 * side effect. A caller must actually persist a capture only when this
 * returns `true` -- calling it when nothing is dirty (an untouched form,
 * or a form already flushed since its last edit) must be a no-op, so
 * `pagehide`/reload on an unedited page never creates a synthetic local
 * recovery entry.
 */
export function takeRecoveryCaptureFlush(state: RecoveryCaptureDirtyState): boolean {
  if (!state.dirty) return false;
  state.dirty = false;
  return true;
}

export interface ProfessionalDraftRecoveryText {
  activeNotice: string;
  recoveredNotice: string;
  conflictNotice: string;
  restoreForReviewLabel: string;
  discardLabel: string;
  unavailableNotice: string;
}

export const defaultProfessionalDraftRecoveryTextEn: ProfessionalDraftRecoveryText = {
  activeNotice:
    "Local recovery is active for this draft. Recent unsaved changes stay recoverable in this browser after a connectivity interruption.",
  recoveredNotice: "Unsaved local changes were recovered into this form. Nothing is saved until you press Save.",
  conflictNotice:
    "This draft changed on the server since your local unsaved copy was captured. Your local copy was not applied automatically.",
  restoreForReviewLabel: "Restore local copy for review",
  discardLabel: "Discard local copy",
  unavailableNotice: "Local recovery is unavailable in this browser. Server-saved drafting still works normally.",
};

type RecoveryFormElement = HTMLInputElement | HTMLSelectElement | HTMLTextAreaElement;

function isRecoveryFormElement(element: Element | RadioNodeList | null): element is RecoveryFormElement {
  return (
    element instanceof HTMLInputElement ||
    element instanceof HTMLSelectElement ||
    element instanceof HTMLTextAreaElement
  );
}

/** Replaces *bannerContainer*'s content with one message and zero or more action buttons (contract §12). */
function renderRecoveryBanner(
  bannerContainer: HTMLElement,
  message: string,
  actions: Array<{ label: string; onClick: () => void }> = [],
): void {
  while (bannerContainer.firstChild) bannerContainer.removeChild(bannerContainer.firstChild);
  const paragraph = document.createElement("p");
  paragraph.textContent = message;
  bannerContainer.appendChild(paragraph);
  for (const action of actions) {
    const button = document.createElement("button");
    button.type = "button";
    button.textContent = action.label;
    button.addEventListener("click", action.onClick);
    bannerContainer.appendChild(button);
  }
}

/**
 * Wires the bounded recovery buffer onto one already-rendered, authorized
 * professional draft edit *form*. Only meant to be called once per page
 * render, after the server-authoritative form has been rendered
 * (contract §7: "once an authorized edit page has rendered").
 *
 * *scope* is `null` when the current AccountId could not be established
 * (e.g. the private Broker Context lookup failed) -- recovery has no safe
 * scope to key itself on in that case, so this renders the required
 * unavailable state and never wires capture (independent review finding
 * 2026-09-21 #3), while leaving ordinary server-backed editing untouched.
 *
 * *bannerContainer* is used both to render the current recovery state
 * (contract §12) and, before this call, may already carry a
 * `data-save-outcome="saved"` marker the caller uses to clear a now-stale
 * local envelope -- see the draft edit page's inline wiring script for that
 * one-line composition; this function itself only ever computes the
 * restore decision against the envelope actually present when it runs.
 */
export function initProfessionalDraftRecovery(
  form: HTMLFormElement,
  bannerContainer: HTMLElement,
  scope: RecoveryScope | null,
  serverVersion: number,
  storage: RecoveryStorageLike,
  text: ProfessionalDraftRecoveryText = defaultProfessionalDraftRecoveryTextEn,
  now: () => Date = () => new Date(),
): void {
  if (scope === null) {
    renderRecoveryBanner(bannerContainer, text.unavailableNotice);
    return;
  }
  // TypeScript does not carry the null-narrowing above into the nested
  // function declarations below (it cannot prove a closed-over parameter is
  // never reassigned before they run) -- bind the narrowed value once so
  // every inner function sees `RecoveryScope`, not `RecoveryScope | null`.
  const resolvedScope: RecoveryScope = scope;

  function readField(name: RecoveryFieldName): string | null {
    const element = form.elements.namedItem(name);
    return isRecoveryFormElement(element) ? element.value : null;
  }

  function writeField(name: RecoveryFieldName, value: string): void {
    const element = form.elements.namedItem(name);
    if (isRecoveryFormElement(element)) {
      element.value = value;
    }
  }

  // Independent review finding 2026-09-21 #3: once a write actually fails
  // (quota/private-mode/security exception surfacing only at `setItem`
  // time, after an earlier `getItem` succeeded), stop claiming recovery is
  // active and stop attempting further writes for this page instance
  // rather than silently retrying forever.
  let recoveryUsable = true;

  function persistCapture(): void {
    if (!recoveryUsable) return;
    const values = captureFormValues(readField);
    const envelope = buildRecoveryEnvelope(resolvedScope, serverVersion, values, now());
    const wrote = saveRecoveryEnvelope(storage, envelope);
    if (!wrote) {
      recoveryUsable = false;
      renderRecoveryBanner(bannerContainer, text.unavailableNotice);
    }
  }

  function wireCapture(): void {
    // Independent review finding 2026-09-22 #B: `pagehide` (and submit)
    // must flush only genuine pending input. `dirtyState` is set by every
    // `input`/`change` and cleared by whichever flush actually runs first
    // (the debounce timer, submit, or pagehide) -- so merely opening and
    // leaving/reloading an untouched form, or a pagehide after an edit was
    // already flushed by the debounce timer, never (re)persists a capture.
    const dirtyState: RecoveryCaptureDirtyState = { dirty: false };
    let debounceHandle: ReturnType<typeof setTimeout> | undefined;

    const flushCapture = (): void => {
      if (debounceHandle !== undefined) {
        clearTimeout(debounceHandle);
        debounceHandle = undefined;
      }
      if (!takeRecoveryCaptureFlush(dirtyState)) return;
      persistCapture();
    };

    const scheduleCapture = (): void => {
      markRecoveryCaptureDirty(dirtyState);
      if (debounceHandle !== undefined) clearTimeout(debounceHandle);
      debounceHandle = setTimeout(flushCapture, 400);
    };

    form.addEventListener("input", scheduleCapture);
    form.addEventListener("change", scheduleCapture);
    // Contract §7: explicit submit must ensure the latest form state has
    // been captured before navigation -- flush synchronously rather than
    // relying on the debounce timer (a no-op if nothing is dirty).
    form.addEventListener("submit", flushCapture);
    if (typeof window !== "undefined") {
      // Contract §7: page-hide/unload SHOULD flush pending recovery --
      // "pending" is the operative word; see dirtyState above.
      window.addEventListener("pagehide", flushCapture);
    }
  }

  const decision = decideRestore(loadRecoveryEnvelope(storage, resolvedScope, now()), serverVersion);

  if (decision.kind === "future_version_invalid") {
    // Corrupt for v0.1 (contract §8.4): never auto-restore, and remove it
    // so it does not keep resurfacing.
    clearRecoveryEnvelope(storage, resolvedScope);
  }

  const uiState = computeRecoveryUiState(decision);

  switch (uiState.kind) {
    case "unavailable":
      renderRecoveryBanner(bannerContainer, text.unavailableNotice);
      return; // storage is not usable -- do not wire capture at all.
    case "active":
      // Independent review finding 2026-09-22 #A: a successful read alone
      // does not prove recovery is usable -- browser storage can allow
      // reads while rejecting writes (quota/privacy/security). Never claim
      // "active" until a bounded, non-destructive write probe actually
      // succeeds; if it does not, this is exactly the "recovery cannot be
      // maintained" case contract §6 requires to render as unavailable.
      if (!canWriteRecoveryStorage(storage, resolvedScope)) {
        renderRecoveryBanner(bannerContainer, text.unavailableNotice);
        return; // no write capability -- do not wire capture at all.
      }
      renderRecoveryBanner(bannerContainer, text.activeNotice);
      break;
    case "recovered":
      applyFormValues(writeField, uiState.envelope.form_values);
      renderRecoveryBanner(bannerContainer, text.recoveredNotice);
      break;
    case "conflict":
      renderRecoveryBanner(bannerContainer, text.conflictNotice, [
        {
          label: text.restoreForReviewLabel,
          onClick: () => {
            applyFormValues(writeField, uiState.envelope.form_values);
            renderRecoveryBanner(bannerContainer, text.recoveredNotice);
          },
        },
        {
          label: text.discardLabel,
          onClick: () => {
            clearRecoveryEnvelope(storage, resolvedScope);
            renderRecoveryBanner(bannerContainer, text.activeNotice);
          },
        },
      ]);
      break;
  }

  wireCapture();
}
