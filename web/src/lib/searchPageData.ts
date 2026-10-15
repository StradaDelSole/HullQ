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
import { fetchSearch, type SearchActiveRequirement, type SearchConfirmedMatch } from "./searchApi.ts";
import type { SupportedLocale } from "./searchText.ts";

export type SearchPageData =
  | { kind: "redirect"; location: string }
  | { kind: "invalid"; message: string | null }
  | { kind: "unavailable" }
  | {
      kind: "ok";
      activeRequirement: SearchActiveRequirement | null;
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

  // A real 400 body means the buyer's own request was malformed/ambiguous
  // (Required Behavior §1 — invalid/ambiguous input never gets partial
  // evaluation). Amendment review Finding 6: this must stay distinct from a
  // backend/network failure (502 here, or any other unexpected status) --
  // an unavailable service is not the same as a malformed buyer requirement
  // and must never look like either a valid empty result or "you typed
  // something wrong."
  if (response.status === 400) {
    return { kind: "invalid", message: response.invalid?.message ?? null };
  }
  return { kind: "unavailable" };
}

/**
 * Build the exact canonical `<link rel="canonical">` path for a canonical
 * (`kind: "ok"`) result -- `null` `activeRequirement` (base state) or a
 * `redirect`/`invalid`/`unavailable` page never has a canonical result
 * URL, so callers pass `null` for those.
 *
 * SLICE-0056 (extended SLICE-0085, SLICE-0086, SLICE-0087): mirrors
 * `src/hullq/application/search_read.py`'s own canonical-query-part
 * ordering exactly (`hullq.search.criteria_registry.CANONICAL_PARAM_KEY_ORDER`:
 * `beam_max`, `beam_min`, `cockpit_position`, `deck_saloon`, `draft_max`,
 * `hull_configuration`, `hull_material`, `keel_configuration`, `loa_max`,
 * `loa_min`, `rudder_configuration` -- plain lexicographic order of all
 * eleven accepted keys, contract §B "Canonical query ordering ... remain
 * backend-owned") -- this never independently decides canonicalization, it
 * only echoes back the exact sparse key set/order FastAPI already applied
 * to reach a `kind: "ok"` result in the first place.
 */
export function buildSearchCanonicalPath(
  locale: SupportedLocale,
  activeRequirement: SearchActiveRequirement | null,
): string {
  if (activeRequirement === null) {
    return `/${locale}/search`;
  }
  const parts: string[] = [];
  if (activeRequirement.beam_max !== undefined) {
    parts.push(`beam_max=${activeRequirement.beam_max}`);
  }
  if (activeRequirement.beam_min !== undefined) {
    parts.push(`beam_min=${activeRequirement.beam_min}`);
  }
  if (activeRequirement.cockpit_position !== undefined) {
    parts.push(`cockpit_position=${activeRequirement.cockpit_position}`);
  }
  if (activeRequirement.deck_saloon !== undefined) {
    parts.push(`deck_saloon=${activeRequirement.deck_saloon}`);
  }
  if (activeRequirement.draft_max !== undefined) {
    parts.push(`draft_max=${activeRequirement.draft_max}`);
  }
  if (activeRequirement.hull_configuration !== undefined) {
    parts.push(`hull_configuration=${activeRequirement.hull_configuration}`);
  }
  if (activeRequirement.hull_material !== undefined) {
    parts.push(`hull_material=${activeRequirement.hull_material}`);
  }
  if (activeRequirement.keel_configuration !== undefined) {
    parts.push(`keel_configuration=${activeRequirement.keel_configuration}`);
  }
  if (activeRequirement.loa_max !== undefined) {
    parts.push(`loa_max=${activeRequirement.loa_max}`);
  }
  if (activeRequirement.loa_min !== undefined) {
    parts.push(`loa_min=${activeRequirement.loa_min}`);
  }
  if (activeRequirement.rudder_configuration !== undefined) {
    parts.push(`rudder_configuration=${activeRequirement.rudder_configuration}`);
  }
  return `/${locale}/search?${parts.join("&")}`;
}
