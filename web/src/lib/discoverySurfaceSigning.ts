// SLICE-0071 Finding B/C/D amendments: trusted server-side discovery-
// surface token minting. Server-only (Node runtime) -- this module reads a
// shared secret via `process.env` and must NEVER be imported from a
// browser-side `<script>` block; it is only ever used from Astro API
// routes (`export const prerender = false` files under `pages/api/`) and
// Astro page frontmatter, both of which execute exclusively in Node.
//
// This exists because an unauthenticated public client must never be able
// to choose which discovery surface gets a valid signed token merely by
// supplying a query parameter (Finding B). SHORTLIST/COMPARE tokens are
// minted only by trusted server-side code whose own route identity (never
// a caller-supplied parameter) determines *surface*. TECHNICAL_SEARCH
// tokens remain minted by FastAPI's own search route (genuinely
// server-known provenance there), and FastAPI's contact route remains the
// sole authoritative *verifier* for every surface -- this module only
// mints.
//
// Finding C: an HTTP `Referer` header is not an authenticated first-party
// navigation capability -- any direct HTTP client can send an arbitrary
// same-origin `Referer` value with no browser involved at all. This module
// therefore exposes no Referer-classification-to-token path of any kind:
// DIRECT_LISTING/INTERNAL_BROWSE are only ever mintable by the same trusted
// mechanism as SHORTLIST/COMPARE (a genuine internal HullQ surface calling
// `mintDiscoverySurfaceToken` directly with a surface its own route
// identity determines) -- there is deliberately no wiring for either
// surface in this slice, so an ordinary direct listing visit persists
// UNKNOWN rather than a guessed value. `UNKNOWN` is always the correct
// answer when no genuinely trusted evidence exists.
//
// Finding D: discovery attribution is auxiliary CRM telemetry, never a
// hard availability dependency for public listing rendering. Every mint
// call therefore fails closed to `undefined` (never throws) when the
// shared secret is absent or malformed -- a caller simply omits the
// `discovery_token` field, and the eventual contact submission resolves to
// UNKNOWN, exactly as if no discovery evidence had ever existed.
//
// Reuses `HULLQ_PREVIEW_SIGNING_SECRET` (already required, already
// deployed to FastAPI) rather than introducing a new secret -- acceptable
// per the accepted amendment because cryptographic domain separation is
// explicit: the signed payload's own `typ` claim ties every token to this
// one purpose, so a token minted here can never be replayed as, or
// confused with, a SLICE-0048 preview-capability token even though both
// happen to be signed under the same key.
import { createHmac } from "node:crypto";

const TOKEN_VERSION = 1;
const TOKEN_PURPOSE = "hullq_discovery_surface_v1";

//: Mirrors `hullq.security.discovery_surface_signing.DEFAULT_DISCOVERY_TOKEN_TTL_SECONDS`.
const DEFAULT_TTL_SECONDS = 3600;

export type DiscoverySurface =
  | "DIRECT_LISTING"
  | "TECHNICAL_SEARCH"
  | "INTERNAL_BROWSE"
  | "SHORTLIST"
  | "COMPARE"
  | "UNKNOWN";

/**
 * Load the shared signing secret, or `null` for any absent/malformed
 * configuration -- never throws (Finding D). Callers must treat `null` as
 * "minting is unavailable right now", not as a fatal error.
 */
function loadSharedSigningSecret(): Buffer | null {
  const raw = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  if (!raw || !raw.trim()) return null;
  let secret: Buffer;
  try {
    secret = Buffer.from(raw.trim().replace(/=+$/, ""), "base64url");
  } catch {
    return null;
  }
  if (secret.length < 32) return null;
  return secret;
}

/**
 * Mint a signed, listing-bound discovery-surface token, or `undefined` if
 * the shared secret is currently unavailable/malformed (Finding D: this
 * never throws -- discovery attribution must never be able to break public
 * listing rendering or shortlist/compare resolution). Server-side only:
 * called from trusted Astro route/page code whose own identity determines
 * *surface* -- a caller of *this function* must never forward an
 * unauthenticated client-supplied value as *surface* (Finding B), and must
 * never derive *surface* from a spoofable signal such as a `Referer`
 * header (Finding C).
 *
 * The wire format must stay byte-for-byte compatible with
 * `hullq.security.discovery_surface_signing.mint_discovery_surface_token`:
 * canonical JSON with keys in the exact alphabetical order that Python's
 * `json.dumps(claims, sort_keys=True, separators=(",", ":"))` produces
 * (exp, iat, nlid, surface, typ, v). Native-listing ids and surface labels
 * are always plain ASCII identifiers in this system, so `JSON.stringify`'s
 * escaping matches Python's `ensure_ascii` default exactly for every value
 * this ever actually carries.
 */
export function mintDiscoverySurfaceToken(
  surface: DiscoverySurface,
  nativeListingId: string,
  ttlSeconds: number = DEFAULT_TTL_SECONDS,
  now: number = Date.now(),
): string | undefined {
  const secret = loadSharedSigningSecret();
  if (secret === null) return undefined;
  const iat = Math.floor(now / 1000);
  const exp = iat + ttlSeconds;
  const payload = Buffer.from(
    `{"exp":${exp},"iat":${iat},"nlid":${JSON.stringify(nativeListingId)},` +
      `"surface":${JSON.stringify(surface)},"typ":${JSON.stringify(TOKEN_PURPOSE)},"v":${TOKEN_VERSION}}`,
    "utf-8",
  );
  const signature = createHmac("sha256", secret).update(payload).digest();
  return `${payload.toString("base64url")}.${signature.toString("base64url")}`;
}
