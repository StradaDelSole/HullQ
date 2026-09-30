// SLICE-0071 Finding B amendment: trusted server-side discovery-surface
// token minting. Server-only (Node runtime) -- this module reads a shared
// secret via `process.env` and must NEVER be imported from a browser-side
// `<script>` block; it is only ever used from Astro API routes
// (`export const prerender = false` files under `pages/api/`) and Astro
// page frontmatter, both of which execute exclusively in Node.
//
// This exists because an unauthenticated public client must never be able
// to choose which discovery surface gets a valid signed token merely by
// supplying a query parameter (independent-review Finding B). The fix:
// SHORTLIST/COMPARE/DIRECT_LISTING/INTERNAL_BROWSE tokens are minted only
// by this trusted server-side code, whose own route/page identity (never a
// caller-supplied parameter) determines *surface*. TECHNICAL_SEARCH tokens
// remain minted by FastAPI's own search route (genuinely server-known
// provenance there), and FastAPI's contact route remains the sole
// authoritative *verifier* for every surface -- this module only mints.
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

function loadSharedSigningSecret(): Buffer {
  const raw = process.env.HULLQ_PREVIEW_SIGNING_SECRET;
  if (!raw || !raw.trim()) {
    throw new Error(
      "HULLQ_PREVIEW_SIGNING_SECRET is not set; required to mint discovery-surface tokens",
    );
  }
  const secret = Buffer.from(raw.trim().replace(/=+$/, ""), "base64url");
  if (secret.length < 32) {
    throw new Error(
      "HULLQ_PREVIEW_SIGNING_SECRET decodes to fewer than 32 bytes; cannot mint discovery-surface tokens",
    );
  }
  return secret;
}

/**
 * Mint a signed, listing-bound discovery-surface token. Server-side only:
 * called from trusted Astro route/page code whose own identity determines
 * *surface* -- a caller of *this function* must never forward an
 * unauthenticated client-supplied value as *surface* (Finding B). The
 * wire format must stay byte-for-byte compatible with
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
): string {
  const iat = Math.floor(now / 1000);
  const exp = iat + ttlSeconds;
  const payload = Buffer.from(
    `{"exp":${exp},"iat":${iat},"nlid":${JSON.stringify(nativeListingId)},` +
      `"surface":${JSON.stringify(surface)},"typ":${JSON.stringify(TOKEN_PURPOSE)},"v":${TOKEN_VERSION}}`,
    "utf-8",
  );
  const signature = createHmac("sha256", loadSharedSigningSecret()).update(payload).digest();
  return `${payload.toString("base64url")}.${signature.toString("base64url")}`;
}

/**
 * Classify the actual incoming `Referer` header into a bounded category
 * (contract §8B amendment): never persist/forward the raw referrer, only
 * this classification. *ownOrigin* must be this exact request's own origin
 * (e.g. `Astro.url.origin`, read by the caller from its own real request,
 * never a caller-supplied value) -- this function performs no I/O and
 * trusts nothing beyond its two arguments.
 */
export function classifyReferrer(
  referer: string | null | undefined,
  ownOrigin: string,
): "NONE" | "EXTERNAL" | "INTERNAL" {
  if (!referer) return "NONE";
  try {
    return new URL(referer).origin === ownOrigin ? "INTERNAL" : "EXTERNAL";
  } catch {
    return "EXTERNAL";
  }
}
