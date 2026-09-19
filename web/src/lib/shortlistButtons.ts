// SLICE-0058: shared client-side add/remove toggle wiring for every
// `[data-shortlist-toggle]` button rendered on a Search results page or the
// public listing page (Required Behavior §I). Only an explicit click ever
// mutates membership (contract §2/§9) -- this module never infers interest
// from any other browser event.
import { addToShortlist, isInShortlist, removeFromShortlist } from "./shortlistStore.ts";

export interface ShortlistButtonText {
  saveLabel: string;
  savedLabel: string;
}

/** Pure label selection -- unit-testable without touching the DOM. */
export function shortlistButtonLabel(isSaved: boolean, text: ShortlistButtonText): string {
  return isSaved ? text.savedLabel : text.saveLabel;
}

function applyState(button: HTMLButtonElement, isSaved: boolean, text: ShortlistButtonText): void {
  button.textContent = shortlistButtonLabel(isSaved, text);
  button.setAttribute("aria-pressed", isSaved ? "true" : "false");
}

/**
 * Wires every `[data-shortlist-toggle][data-native-listing-id]` button under
 * *root* to the browser-local shortlist. Safe to call multiple times on the
 * same root only if buttons are not re-wired elsewhere; each Astro page
 * calls this once after its own content is present in the DOM.
 */
export function initShortlistButtons(root: ParentNode, text: ShortlistButtonText): void {
  const buttons = root.querySelectorAll<HTMLButtonElement>("[data-shortlist-toggle]");
  buttons.forEach((button) => {
    const id = button.dataset.nativeListingId;
    if (!id) return;
    applyState(button, isInShortlist(window.localStorage, id), text);
    button.addEventListener("click", () => {
      const currentlySaved = isInShortlist(window.localStorage, id);
      // Independent review finding 2026-09-19: derive the button's new
      // state from the *actual retained membership* the store reports
      // back, never by blindly toggling the pre-click state -- a failed
      // storage write must never be displayed as a successful Add/Remove.
      const actualMembership = currentlySaved
        ? removeFromShortlist(window.localStorage, id)
        : addToShortlist(window.localStorage, id);
      applyState(button, actualMembership.includes(id), text);
    });
  });
}
