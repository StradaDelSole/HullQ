// SLICE-0093: fetch + classify one Power Search page's data, independent of
// any Astro rendering context -- mirrors `searchPageData.ts`'s identical
// rationale (response-mutating decisions must happen in the top-level
// page's own frontmatter, before any HTML starts streaming).
import {
  fetchPowerSearch,
  type PowerClaimOnlyMatch,
  type PowerActiveRequirement,
  type PowerDesignLinkedMatch,
} from "./powerSearchApi.ts";
import type { SupportedLocale } from "./searchText.ts";

export type PowerSearchPageData =
  | { kind: "redirect"; location: string }
  | { kind: "invalid"; message: string | null }
  | { kind: "unavailable" }
  | {
      kind: "ok";
      activeRequirement: PowerActiveRequirement | null;
      designLinkedMatches: PowerDesignLinkedMatch[];
      designLinkedMatchCount: number;
      designLinkedInsufficientDataCount: number;
      publisherClaimMatches: PowerClaimOnlyMatch[];
      publisherClaimMatchCount: number;
      /** SLICE-0096 -- see `SearchPageData`'s identical fields in `searchPageData.ts`. */
      evaluationState: "PARTIAL" | "COMPLETE";
      nextPageQueryString: string | null;
    };

export async function loadPowerSearchPageData(
  apiBaseUrl: string,
  locale: SupportedLocale,
  queryString: string,
): Promise<PowerSearchPageData> {
  const response = await fetchPowerSearch(apiBaseUrl, locale, queryString);

  if (response.status === 308 && response.location !== null) {
    return { kind: "redirect", location: response.location };
  }

  if (response.status === 200 && response.result !== null) {
    const result = response.result;
    const nextCursor = result.next_cursor ?? null;
    let nextPageQueryString: string | null = null;
    if (nextCursor !== null) {
      const params = new URLSearchParams(queryString);
      params.delete("page_after");
      params.set("page_after", nextCursor);
      nextPageQueryString = params.toString();
    }
    return {
      kind: "ok",
      activeRequirement: result.active_requirement,
      designLinkedMatches: result.design_linked_matches ?? [],
      designLinkedMatchCount: result.design_linked_match_count ?? 0,
      designLinkedInsufficientDataCount: result.design_linked_insufficient_data_count ?? 0,
      publisherClaimMatches: result.publisher_claim_matches ?? [],
      publisherClaimMatchCount: result.publisher_claim_match_count ?? 0,
      evaluationState: result.evaluation_state ?? "PARTIAL",
      nextPageQueryString,
    };
  }

  // Amendment-review-equivalent discipline mirrored from `searchPageData.ts`:
  // a real 400 body means the buyer's own request was malformed, distinct
  // from a backend/network failure (which must never look like either a
  // valid empty result or "you typed something wrong").
  if (response.status === 400) {
    return { kind: "invalid", message: response.invalid?.message ?? null };
  }
  return { kind: "unavailable" };
}

/**
 * Build the exact canonical `<link rel="canonical">` path for a canonical
 * (`kind: "ok"`) result -- `null` `activeRequirement` (base state) or a
 * `redirect`/`invalid`/`unavailable` page never has a canonical result URL.
 *
 * SLICE-0094: `activeRequirement` is now sparse -- only the criteria it
 * actually carries are rendered, in the accepted canonical key order
 * (`power_drive` then `power_engine_count`).
 */
export function buildPowerSearchCanonicalPath(
  locale: SupportedLocale,
  activeRequirement: PowerActiveRequirement | null,
): string {
  if (activeRequirement === null) {
    return `/${locale}/power/search`;
  }
  const parts: string[] = [];
  if (activeRequirement.power_drive !== undefined) {
    parts.push(`power_drive=${activeRequirement.power_drive}`);
  }
  if (activeRequirement.power_engine_count !== undefined) {
    parts.push(`power_engine_count=${activeRequirement.power_engine_count}`);
  }
  if (parts.length === 0) {
    return `/${locale}/power/search`;
  }
  return `/${locale}/power/search?${parts.join("&")}`;
}
