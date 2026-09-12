// SLICE-0051: the only module allowed to talk to the outside world for the
// public Search surface. Astro obtains every Search decision (canonical
// redirect, invalid-request recovery, or confirmed/insufficient results)
// through FastAPI's `/api/search/{locale}` route only -- this module never
// touches PostgreSQL and never reimplements a Python domain/canonicalization
// rule (slice item J). `redirect: "manual"` is required here: FastAPI's own
// route returns a real HTTP 308 with a `Location` header for a non-canonical
// but valid request, and this page must reissue that exact redirect to the
// browser rather than transparently following it server-side.

export interface SearchConfirmedMatch {
  native_listing_id: string;
  resolved_draft_m: string;
  publishing_organization_id: string;
}

export interface SearchResultBody {
  locale: string;
  active_requirement: { draft_max: string } | null;
  confirmed_matches?: SearchConfirmedMatch[];
  confirmed_match_count?: number;
  insufficient_data_count?: number;
}

export interface SearchInvalidBody {
  error: string;
  message: string;
}

export interface SearchApiResponse {
  /** The real upstream FastAPI status: 200, 308, or 400. 502 on network failure. */
  status: number;
  /** Populated only when `status === 308`. */
  location: string | null;
  /** Populated only when `status === 200`. */
  result: SearchResultBody | null;
  /** Populated only when `status === 400`. */
  invalid: SearchInvalidBody | null;
}

/**
 * Call FastAPI's `/api/search/{locale}` route with *queryString* (no leading
 * `?`, may be empty) and classify the real response. A network failure or an
 * unexpected upstream status collapses to `status: 502` with no
 * result/invalid payload -- callers must treat this as a recovery case, not
 * a confirmed empty result.
 */
export async function fetchSearch(
  apiBaseUrl: string,
  locale: string,
  queryString: string,
): Promise<SearchApiResponse> {
  const base = apiBaseUrl.replace(/\/+$/, "");
  const suffix = queryString ? `?${queryString}` : "";
  const url = `${base}/api/search/${encodeURIComponent(locale)}${suffix}`;

  let response: Response;
  try {
    response = await fetch(url, { redirect: "manual" });
  } catch {
    return { status: 502, location: null, result: null, invalid: null };
  }

  if (response.status === 308) {
    return { status: 308, location: response.headers.get("location"), result: null, invalid: null };
  }
  if (response.status === 400) {
    let invalid: SearchInvalidBody | null = null;
    try {
      invalid = (await response.json()) as SearchInvalidBody;
    } catch {
      invalid = null;
    }
    return { status: 400, location: null, result: null, invalid };
  }
  if (response.status === 200) {
    let result: SearchResultBody | null = null;
    try {
      result = (await response.json()) as SearchResultBody;
    } catch {
      result = null;
    }
    if (result === null) {
      return { status: 502, location: null, result: null, invalid: null };
    }
    return { status: 200, location: null, result, invalid: null };
  }
  return { status: 502, location: null, result: null, invalid: null };
}
