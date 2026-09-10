// SLICE-0050: pure display-text helpers for the "THIS BOAT" section of the
// public listing page.
//
// These functions only decide *which words* to show for an
// omitted/UNKNOWN/VALUE_ASSERTION PhysicalBoat claim field -- they never
// touch the DOM and never build HTML: the calling `.astro` template
// interpolates their return values through ordinary escaped `{expression}`
// text nodes, never `set:html` or equivalent, so broker-controlled text
// (`marketed_brand_claim`, `model_designation_claim`) remains inert no
// matter what it contains. Mirrors `./previewText.ts`'s shape for the
// `LISTING_OFFER` fields.
import type { OptionalBoatClaimField } from "./publicListingApi";

/**
 * Display text for one optional PhysicalBoat claim field (`loa_length`,
 * `draft`, `keel_configuration`, `rudder_configuration`, `build_year`).
 *
 * `null` means the whole field was omitted by the broker -- distinct from
 * an explicit `UNKNOWN` assertion, which renders as the word "unknown"
 * rather than collapsing to the same "not supplied" text. SLICE-0050 §11
 * requires these two states remain visually distinguishable.
 */
export function boatClaimText(claim: OptionalBoatClaimField | null): string | null {
  if (claim === null) return null;
  if (claim.assertion_kind === "VALUE_ASSERTION") return String(claim.value);
  if (claim.assertion_kind === "UNKNOWN") return "unknown";
  return null;
}

/** Same as `boatClaimText`, but renders the omitted case as "not supplied" text. */
export function boatClaimTextOrNotSupplied(claim: OptionalBoatClaimField | null): string {
  const text = boatClaimText(claim);
  return text === null ? "not supplied" : text;
}
