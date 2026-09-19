// SLICE-0059: client-side rendering for `/{locale}/shortlist/compare`
// (`specs/ANONYMOUS_FACTUAL_SHORTLIST_COMPARE_CONTRACT.v0.1.md`). Runs
// entirely in the browser, exactly like `shortlistPageRuntime.ts`: the
// compare set is the existing local Shortlist (contract §2), so there is
// nothing for this page's own Astro frontmatter to fetch or know. Every DOM
// node is built with `document.createElement`/`textContent`, never
// `innerHTML`/`set:html`, so no stored id or resolved listing text can ever
// be interpreted as markup (contract §11).
//
// Independent review 2026-09-19 (PR #221) required a genuine aligned
// side-by-side matrix rather than a vertical sequence of independent cards
// (contract §§1,5,17): the renderer below builds one `<table>` with one
// column per shortlisted entry and one row per factual field, so every
// entry's Price/Location/Build year/etc. sits directly across from every
// other entry's. `compareRowLabels`/`compareRowValues`/`buildCompareColumn`
// are kept as pure functions with no DOM dependency precisely so that
// row/column alignment itself stays directly unit-testable (every column's
// value array has the same length and row order), mirroring how
// `shortlistButtons.ts` separates `shortlistButtonLabel` from its DOM wiring.
import { askingPriceText } from "./previewText.ts";
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
 * `compareRowValues` below is the single place that maps a `null` row value
 * to its aligned-matrix placeholder text.
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

/** The localized labels `buildCompareFields` needs beyond the seven-field claim vocabulary. */
export interface CompareFieldLabels {
  priceOnApplicationLabel: string;
  freshnessConfirmedLabel: string;
  freshnessDueLabel: string;
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
 * Localized equivalent of `previewText.ts`'s `freshnessDisclosureText`.
 * Independent review 2026-09-19 (PR #221) found the original implementation
 * called that English-only helper directly, so DE/FR/PT/ES Compare routes
 * rendered English freshness prose. This reuses the already-localized
 * `shortlistText` CONFIRMED/DUE_FOR_CONFIRMATION status labels (shared with
 * `/{locale}/shortlist`, contract §5's "reuse existing localized shortlist
 * status labels") and appends the raw ISO `last_confirmed_at` timestamp --
 * language-neutral, so disclosing it needs no new per-locale sentence
 * template -- without ever wording DUE_FOR_CONFIRMATION as simply confirmed.
 */
function localizedFreshnessText(
  freshnessStatus: "CONFIRMED" | "DUE_FOR_CONFIRMATION",
  lastConfirmedAt: string | null,
  labels: Pick<CompareFieldLabels, "freshnessConfirmedLabel" | "freshnessDueLabel">,
): string {
  const statusLabel =
    freshnessStatus === "DUE_FOR_CONFIRMATION"
      ? labels.freshnessDueLabel
      : labels.freshnessConfirmedLabel;
  return lastConfirmedAt !== null ? `${statusLabel} (${lastConfirmedAt})` : statusLabel;
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
  labels: CompareFieldLabels,
): CompareFields {
  const claims = data.physical_boat_claims;
  return {
    identityHeading:
      claims !== null ? `${claims.marketed_brand_claim} ${claims.model_designation_claim}` : null,
    price:
      data.asking_price_mode === "AMOUNT" ? askingPriceText(data) : labels.priceOnApplicationLabel,
    locationCountry: data.location_country,
    locationRegion: data.location_region !== null ? localizedRegionText(data.location_region, t) : null,
    buildYear: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.build_year, t) : null,
    loa: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.loa_length, t) : null,
    draft: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.draft, t) : null,
    keel: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.keel_configuration, t) : null,
    rudder: claims !== null ? localizedBoatClaimTextOrNotSupplied(claims.rudder_configuration, t) : null,
    freshness: localizedFreshnessText(data.freshness_status, data.last_confirmed_at, labels),
  };
}

/**
 * One column of the aligned Compare matrix: either an available listing's
 * derived fields, or a neutral unavailable/service-error placeholder that
 * still occupies its own column in buyer-authored order (contract §9 -- one
 * unavailable/service-error entry must never suppress or hide the others,
 * and must never leak *why* it is unavailable).
 */
export interface CompareColumn {
  nativeListingId: string;
  state: "available" | "unavailable" | "service_error";
  headingText: string;
  headingHref: string | null;
  fields: CompareFields | null;
}

export function buildCompareColumn(
  item: ShortlistItemResult,
  t: ShortlistCompareText,
  labels: CompareFieldLabels,
  unavailableMessage: string,
  itemServiceErrorMessage: string,
): CompareColumn {
  if (item.state === "available") {
    const fields = buildCompareFields(item.data, t, labels);
    return {
      nativeListingId: item.native_listing_id,
      state: "available",
      headingText: fields.identityHeading ?? t.identityFallbackLabel,
      headingHref: `/listings/${encodeURIComponent(item.native_listing_id)}`,
      fields,
    };
  }
  return {
    nativeListingId: item.native_listing_id,
    state: item.state,
    headingText: item.state === "unavailable" ? unavailableMessage : itemServiceErrorMessage,
    headingHref: null,
    fields: null,
  };
}

/** Fixed, aligned row order shared by every column of the Compare matrix (contract §5). */
export function compareRowLabels(t: ShortlistCompareText): string[] {
  return [
    t.priceLabel,
    t.locationLabel,
    t.buildYearLabel,
    t.loaLabel,
    t.draftLabel,
    t.keelLabel,
    t.rudderLabel,
    t.freshnessLabel,
  ];
}

/**
 * The exact per-row cell text for one column, in the same fixed order as
 * `compareRowLabels`. `fields === null` (an unavailable/service-error
 * column) renders every cell as the neutral em-dash placeholder -- the
 * column's heading already discloses its unavailable/service-error state,
 * so the row cells never need to repeat or enumerate a cause. A `null`
 * individual field (no PhysicalBoat claims recorded at all) renders as
 * `notSuppliedLabel`, identical to an omitted individual claim field, since
 * neither is buyer-relevant to distinguish and both are genuinely "not
 * supplied" (contract §6).
 */
export function compareRowValues(fields: CompareFields | null, t: ShortlistCompareText): string[] {
  const labelCount = compareRowLabels(t).length;
  if (fields === null) return new Array<string>(labelCount).fill("—");
  return [
    fields.price,
    fields.locationRegion !== null ? `${fields.locationCountry} — ${fields.locationRegion}` : fields.locationCountry,
    fields.buildYear ?? t.notSuppliedLabel,
    fields.loa ?? t.notSuppliedLabel,
    fields.draft ?? t.notSuppliedLabel,
    fields.keel ?? t.notSuppliedLabel,
    fields.rudder ?? t.notSuppliedLabel,
    fields.freshness,
  ];
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

/**
 * Renders the genuine aligned side-by-side Compare matrix: one `<table>`
 * with one header cell + one column per shortlisted entry, and one row per
 * `compareRowLabels()` entry, wrapped in a horizontally-scrollable container
 * for narrow screens (contract §13 -- must not assume desktop-only width).
 */
function renderCompareTable(
  root: HTMLElement,
  columns: CompareColumn[],
  t: ShortlistCompareText,
): void {
  clearChildren(root);

  const wrapper = document.createElement("div");
  wrapper.setAttribute("data-hullq-compare-wrapper", "");

  const table = document.createElement("table");
  table.setAttribute("data-hullq-compare-table", "");

  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");
  headerRow.appendChild(document.createElement("th"));
  for (const column of columns) {
    const th = document.createElement("th");
    th.scope = "col";
    th.setAttribute("data-native-listing-id", column.nativeListingId);
    if (column.state === "available" && column.headingHref !== null) {
      const heading = document.createElement("div");
      heading.textContent = column.headingText;
      th.appendChild(heading);
      const link = document.createElement("a");
      link.href = column.headingHref;
      link.textContent = column.nativeListingId;
      th.appendChild(link);
    } else {
      th.textContent = column.headingText;
    }
    headerRow.appendChild(th);
  }
  thead.appendChild(headerRow);
  table.appendChild(thead);

  const tbody = document.createElement("tbody");
  const labels = compareRowLabels(t);
  const columnValues = columns.map((column) => compareRowValues(column.fields, t));
  for (let rowIndex = 0; rowIndex < labels.length; rowIndex += 1) {
    const tr = document.createElement("tr");
    const rowHeader = document.createElement("th");
    rowHeader.scope = "row";
    rowHeader.textContent = labels[rowIndex];
    tr.appendChild(rowHeader);
    for (const values of columnValues) {
      const td = document.createElement("td");
      td.textContent = values[rowIndex];
      tr.appendChild(td);
    }
    tbody.appendChild(tr);
  }
  table.appendChild(tbody);

  wrapper.appendChild(table);
  root.appendChild(wrapper);
}

export async function renderShortlistComparePage(root: HTMLElement | null): Promise<void> {
  if (root === null) return;
  const locale = (root.dataset.locale as SupportedLocale | undefined) ?? "en";
  const t = shortlistCompareText[locale];
  const st = shortlistText[locale];
  const labels: CompareFieldLabels = {
    priceOnApplicationLabel: st.priceOnApplicationLabel,
    freshnessConfirmedLabel: st.freshnessConfirmedLabel,
    freshnessDueLabel: st.freshnessDueLabel,
  };

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

  const columns = resolution.items.map((item) =>
    buildCompareColumn(item, t, labels, st.unavailableMessage, st.itemServiceErrorMessage),
  );
  renderCompareTable(root, columns, t);
}
