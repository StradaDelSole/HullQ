// SLICE-0058: client-side rendering for `/{locale}/shortlist`. Runs entirely
// in the browser because shortlist membership is inherently client-owned
// (contract §9) -- the page's own Astro frontmatter fetches nothing and
// knows no membership. Every node below is built with
// `document.createElement`/`textContent`, never `innerHTML`/`set:html`, so
// no stored id or returned listing text can ever be interpreted as markup
// (contract §9/§16: "no unsafe HTML injection from local storage").
import { askingPriceText } from "./previewText.ts";
import { resolveShortlistListings, type ShortlistItemResult } from "./shortlistResolutionApi.ts";
import { loadShortlistIds, removeFromShortlist } from "./shortlistStore.ts";
import { shortlistText, type ShortlistText, type SupportedLocale } from "./shortlistText.ts";

function freshnessLabel(item: ShortlistItemResult, t: ShortlistText): string {
  if (item.state !== "available") return "";
  return item.data.freshness_status === "DUE_FOR_CONFIRMATION"
    ? t.freshnessDueLabel
    : t.freshnessConfirmedLabel;
}

function priceLabel(item: ShortlistItemResult, t: ShortlistText): string {
  if (item.state !== "available") return "";
  return item.data.asking_price_mode === "AMOUNT" ? askingPriceText(item.data) : t.priceOnApplicationLabel;
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

function renderList(
  root: HTMLElement,
  items: ShortlistItemResult[],
  t: ShortlistText,
  onRemove: (nativeListingId: string) => void,
): void {
  clearChildren(root);
  const list = document.createElement("ul");
  for (const item of items) {
    const entry = document.createElement("li");
    entry.setAttribute("data-native-listing-id", item.native_listing_id);

    if (item.state === "available") {
      const link = document.createElement("a");
      link.href = `/listings/${encodeURIComponent(item.native_listing_id)}`;
      link.textContent = `${t.viewListing}: ${item.native_listing_id}`;
      entry.appendChild(link);

      const price = document.createElement("span");
      price.textContent = ` — ${priceLabel(item, t)}`;
      entry.appendChild(price);

      const freshness = document.createElement("span");
      freshness.setAttribute("aria-label", "freshness status");
      freshness.textContent = ` — ${freshnessLabel(item, t)}`;
      entry.appendChild(freshness);
    } else if (item.state === "unavailable") {
      const note = document.createElement("span");
      note.textContent = `${item.native_listing_id} — ${t.unavailableMessage}`;
      entry.appendChild(note);
    } else {
      const note = document.createElement("span");
      note.setAttribute("aria-label", "shortlist item service error");
      note.textContent = `${item.native_listing_id} — ${t.itemServiceErrorMessage}`;
      entry.appendChild(note);
    }

    const removeButton = document.createElement("button");
    removeButton.type = "button";
    removeButton.textContent = t.removeLabel;
    removeButton.addEventListener("click", () => {
      onRemove(item.native_listing_id);
      entry.remove();
      if (list.children.length === 0) {
        renderMessage(root, t.emptyMessage);
      }
    });
    entry.appendChild(removeButton);

    list.appendChild(entry);
  }
  root.appendChild(list);
}

export async function renderShortlistPage(root: HTMLElement | null): Promise<void> {
  if (root === null) return;
  const locale = (root.dataset.locale as SupportedLocale | undefined) ?? "en";
  const t = shortlistText[locale];

  const ids = loadShortlistIds(window.localStorage);
  if (ids.length === 0) {
    renderMessage(root, t.emptyMessage);
    return;
  }

  const resolution = await resolveShortlistListings(ids);
  if (resolution.kind === "service_error") {
    renderMessage(root, t.serviceErrorMessage);
    return;
  }

  renderList(root, resolution.items, t, (nativeListingId) => {
    removeFromShortlist(window.localStorage, nativeListingId);
  });
}
