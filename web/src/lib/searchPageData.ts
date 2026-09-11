// SLICE-0051: fetch + classify one Search page's data, independent of any
// Astro rendering context. This is a plain TypeScript module (not an Astro
// component) specifically so the response-mutating calls it informs
// (`Astro.redirect`, `Astro.response.status`) can be made directly by each
// top-level `web/src/pages/{locale}/search.astro` page's own frontmatter --
// Astro only allows mutating the response before any HTML has started
// streaming, which has already happened by the time a *child* component's
// frontmatter runs. Presentation itself stays in the shared, purely
// presentational `SearchPageBody.astro` (props in, no fetch, no response
// mutation), so the actual markup is still written exactly once.
import { fetchSearch, type SearchConfirmedMatch } from "./searchApi";
import type { SupportedLocale } from "./searchText";

export type SearchPageData =
  | { kind: "redirect"; location: string }
  | { kind: "invalid"; message: string | null }
  | {
      kind: "ok";
      activeRequirement: { draft_max: string } | null;
      confirmedMatches: SearchConfirmedMatch[];
      confirmedMatchCount: number;
      insufficientDataCount: number;
    };

export async function loadSearchPageData(
  apiBaseUrl: string,
  locale: SupportedLocale,
  queryString: string,
): Promise<SearchPageData> {
  const response = await fetchSearch(apiBaseUrl, locale, queryString);

  if (response.status === 308 && response.location !== null) {
    return { kind: "redirect", location: response.location };
  }

  if (response.status === 200 && response.result !== null) {
    const result = response.result;
    return {
      kind: "ok",
      activeRequirement: result.active_requirement,
      confirmedMatches: result.confirmed_matches ?? [],
      confirmedMatchCount: result.confirmed_match_count ?? 0,
      insufficientDataCount: result.insufficient_data_count ?? 0,
    };
  }

  // A real 400 body, or an unexpected/network failure (502): both render
  // the identical localized recovery state (Required Behavior §1 — invalid/
  // ambiguous input never gets partial evaluation).
  return { kind: "invalid", message: response.invalid?.message ?? null };
}
