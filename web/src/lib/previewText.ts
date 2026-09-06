// SLICE-0048: pure display-text helpers for the preview page.
//
// These functions only decide *which words* to show for an
// omission/UNKNOWN/NOT_APPLICABLE/NO_KNOWN_HISTORY_DECLARED/VALUE_ASSERTION
// claim shape (`hullq.domain.native_listing_offer` §AssertionKind mirrored
// here as plain strings). They never touch the DOM and never build HTML:
// the calling `.astro` template interpolates their return values through
// ordinary escaped `{expression}` text nodes, never `set:html` or
// equivalent -- broker-controlled text remains inert no matter what it
// contains.
import type { ClaimField } from "./previewApi";

/** Display text for a claim whose only non-VALUE_ASSERTION kind is UNKNOWN. */
export function unknownableClaimText(claim: ClaimField | null): string | null {
  if (claim === null) return null;
  if (claim.assertion_kind === "VALUE_ASSERTION") return claim.value;
  if (claim.assertion_kind === "UNKNOWN") return "unknown";
  return null;
}

/** Display text for `listing_offer.broker_summary` (VALUE_ASSERTION or NOT_APPLICABLE). */
export function brokerSummaryText(claim: ClaimField | null): string | null {
  if (claim === null) return null;
  if (claim.assertion_kind === "VALUE_ASSERTION") return claim.value;
  return null;
}

/**
 * Display text for `listing_offer.known_history_narrative`.
 *
 * `NO_KNOWN_HISTORY_DECLARED` is rendered as an explicit broker declaration,
 * never as proof no such history exists -- the wording below preserves that
 * qualification instead of flattening it to silence or a bare boolean.
 */
export function knownHistoryText(claim: ClaimField | null): string | null {
  if (claim === null) return null;
  if (claim.assertion_kind === "VALUE_ASSERTION") return claim.value;
  if (claim.assertion_kind === "NO_KNOWN_HISTORY_DECLARED") {
    return "No known history declared by the broker. This is not proof that no such history exists.";
  }
  if (claim.assertion_kind === "UNKNOWN") return "Known history: unknown.";
  return null;
}

/** Asking-price headline text: an amount + currency, or the POA notice. */
export function askingPriceText(data: {
  asking_price_mode: "AMOUNT" | "POA";
  asking_price_amount: string | null;
  currency: string | null;
}): string {
  if (data.asking_price_mode === "AMOUNT") {
    return `${data.asking_price_amount} ${data.currency}`;
  }
  return "Price on application";
}
