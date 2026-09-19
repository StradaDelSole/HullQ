// SLICE-0059: client-side rendering for `/{locale}/shortlist/compare`
// (`specs/ANONYMOUS_FACTUAL_SHORTLIST_COMPARE_CONTRACT.v0.1.md`). Runs
// entirely in the browser, exactly like `shortlistPageRuntime.ts`: the
// compare set is the existing local Shortlist (contract §2), so there is
// nothing for this page's own Astro frontmatter to fetch or know. Every DOM
// node is built with `document.createElement`/`textContent`, never
// `innerHTML`/`set:html`, so no stored id or resolved listing text can ever
// be interpreted as markup (contract §11).
//
// The comparison-field derivation (`buildCompareFields`) and compare-set
// classification (`compareSetState`) are kept as pure functions with no DOM
// dependency so they stay directly unit-testable, mirroring how
// `shortlistButtons.ts` separates `shortlistButtonLabel` from its DOM wiring.
import { askingPriceText, freshnessDisclosureText } from "./previewText.ts";
import type { ClaimField } from "./previewApi.ts";
import type { OptionalBoatClaimField, PublicListingData } from "./publicListingApi.ts";
import { resolveShortlistListings, type ShortlistItemResult } from "./shortlistResolutionApi.ts";
import { loadShortlistIds } from "./shortlistStore.ts";
import { shortlistCompareText, type ShortlistCompareText } from "./shortlistCompareText.ts";
import { shortlistText, type SupportedLocale } from "./shortlistText.ts";

/** Contract §3: zero / one / two-or-more saved ids render different bounded states. */
export type CompareSetState = "empty" | "need_one_more" | "ready";

export function compareSetState(ids: string[]): CompareSetState {
  if (ids.length === 0) return "empty";
  if (ids.length === 1) return "need_one_more";
  return "ready";
}

/**
 * The bounded factual comparison row set for one available shortlisted
 * listing (contract §5). Every value is already the exact localized display
 * text for its row -- `null` here means "this row has no value to show for
 * this listing" (no `physical_boat_claims` recorded at all), which is
 * visually distinct from `notSuppliedLabel`/`unknownLabel` text, which means
 * a claim snapshot exists but this one field was omitted/unknown within it.
 */
export interface CompareFields {
  identityHeading: string | null;
  price: string;
  locationCountry: string;
  locationRegion: string | null;
  buildYear: string | null;
  loa: string | null;
  draft: string | null;
  keel: string | null;
  rudder: string | null;
  freshness: string;
}

/**
 * Localized equivalent of `physicalBoatClaimText.ts`'s `boatClaimText`: that
 * module's wording is hardcoded English by design (the single public listing
 * page is deliberately English-only per its own contract), but Compare must
 * serve five locales, so this preserves the identical
 * VALUE_ASSERTION/UNKNOWN/omitted branching with locale-appropriate words
 * instead (contract §6/§13).
 */
function localizedBoatClaimText(
  claim: OptionalBoatClaimField | null,
  t: ShortlistCompareText,
): string | null {
  if (claim === null) return null;
  if (claim.assertion_kind === "VALUE_ASSERTION") return String(claim.value);
  if (claim.assertion_kind === "UNKNOWN") return t.unknownLabel;
  return null;
}

function localizedBoatClaimTextOrNotSupplied(
  claim: OptionalBoatClaimField | null,
  t: ShortlistCompareText,
): string {
  const text = localizedBoatClaimText(claim, t);
  return text === null ? t.notSuppliedLabel : text;
}

/** Localized equivalent of `previewText.ts`'s `unknownableClaimText`. */
function localizedRegionText(claim: ClaimField | null, t: ShortlistCompareText): string {
  if (claim === null) return t.notSuppliedLabel;
  if (claim.assertion_kind === "VALUE_ASSERTION") return claim.value ?? t.notSuppliedLabel;
  if (claim.assertion_kind === "UNKNOWN") return t.unknownLabel;
  return t.notSuppliedLabel;
}

/**
 * Derive the bounded factual comparison row set for one available listing.
 * Never reads BoatDesign baseline truth -- every field comes only from
 * *data*'s own accepted current public projection, and a missing
 * `physical_boat_claims` snapshot leaves every concrete-yacht row `null`
 * rather than any fallback value (contract §5/§6).
 */
export function buildCompareFields(
  data: PublicListingData,
  t: ShortlistCompareText,
  priceOnApplicationLabel: string,
): CompareFields {
  const claims = data.physical_boat_claims;
  return {
    identityHeading:
      claims !== null ? `${claims.marketed_brand_claim} ${claims.model_designation_claim}` : null,
    price: data.asking_price_mode === "AMOUNT" ? askingPriceText(data) : priceOnApplicationLabel,
    locationCountry: data.location_country,
    locationRegion: data.location_region !== null ? localizedRegionText(data.location_region, t) : null,
    buildYear: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.build_year, t) : null,
    loa: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.loa_length, t) : null,
    draft: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.draft, t) : null,
    keel: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.keel_configuration, t) : null,
    rudder: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.rudder_configuration, t) : null,
    freshness: freshnessDisclosureText(data.freshness_status, data.last_confirmed_at),
  };
}

function clearChildren(node: Element): void {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function renderMessage(root: HTMLElement, text: string): void {
  clearChildren(root);
  const p = document.createElement("p");
  p.textContent = text;
  root.appendChild(p);
}

function appendRow(dl: HTMLElement, label: string, value: string): void {
  const dt = document.createElement("dt");
  dt.textContent = label;
  const dd = document.createElement("dd");
  dd.textContent = value;
  dl.appendChild(dt);
  dl.appendChild(dd);
}

function renderAvailableCard(
  entry: HTMLElement,
  item: Extract<ShortlistItemResult, { state: "available" }>,
  t: ShortlistCompareText,
  priceOnApplicationLabel: string,
): void {
  const fields = buildCompareFields(item.data, t, priceOnApplicationLabel);

  const heading = document.createElement("h2");
  heading.textContent = fields.identityHeading ?? t.identityFallbackLabel;
  entry.appendChild(heading);

  const link = document.createElement("a");
  link.href = `/listings/${encodeURIComponent(item.native_listing_id)}`;
  link.textContent = item.native_listing_id;
  entry.appendChild(link);

  const dl = document.createElement("dl");
  appendRow(dl, t.priceLabel, fields.price);
  appendRow(
    dl,
    t.locationLabel,
    fields.locationRegion !== null
      ? `${fields.locationCountry} — ${fields.locationRegion}`
      : fields.locationCountry,
  );
  if (fields.buildYear !== null) appendRow(dl, t.buildYearLabel, fields.buildYear);
  if (fields.loa !== null) appendRow(dl, t.loaLabel, fields.loa);
  if (fields.draft !== null) appendRow(dl, t.draftLabel, fields.draft);
  if (fields.keel !== null) appendRow(dl, t.keelLabel, fields.keel);
  if (fields.rudder !== null) appendRow(dl, t.rudderLabel, fields.rudder);
  appendRow(dl, t.freshnessLabel, fields.freshness);
  entry.appendChild(dl);
}

function renderCompareSet(
  root: HTMLElement,
  items: ShortlistItemResult[],
  t: ShortlistCompareText,
  priceOnApplicationLabel: string,
  unavailableMessage: string,
  itemServiceErrorMessage: string,
): void {
  clearChildren(root);
  const list = document.createElement("ul");
  for (const item of items) {
    const entry = document.createElement("li");
    entry.setAttribute("data-native-listing-id", item.native_listing_id);

    if (item.state === "available") {
      renderAvailableCard(entry, item, t, priceOnApplicationLabel);
    } else if (item.state === "unavailable") {
      const note = document.createElement("p");
      note.textContent = `${item.native_listing_id} — ${unavailableMessage}`;
      entry.appendChild(note);
    } else {
      const note = document.createElement("p");
      note.setAttribute("aria-label", "compare item service error");
      note.textContent = `${item.native_listing_id} — ${itemServiceErrorMessage}`;
      entry.appendChild(note);
    }

    list.appendChild(entry);
  }
  root.appendChild(list);
}

export async function renderShortlistComparePage(root: HTMLElement | null): Promise<void> {
  if (root === null) return;
  const locale = (root.dataset.locale as SupportedLocale | undefined) ?? "en";
  const t = shortlistCompareText[locale];
  const st = shortlistText[locale];

  const ids = loadShortlistIds(window.localStorage);
  const state = compareSetState(ids);

  if (state === "empty") {
    renderMessage(root, t.emptyMessage);
    return;
  }
  if (state === "need_one_more") {
    renderMessage(root, t.needOneMoreMessage);
    return;
  }

  const resolution = await resolveShortlistListings(ids);
  if (resolution.kind === "service_error") {
    renderMessage(root, t.serviceErrorMessage);
    return;
  }

  renderCompareSet(
    root,
    resolution.items,
    t,
    st.priceOnApplicationLabel,
    st.unavailableMessage,
    st.itemServiceErrorMessage,
  );
}
