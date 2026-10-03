// SLICE-0078: baseline security headers applied to every response, since no
// centralized enforcement point existed before this (each page only ever
// set its own Cache-Control/X-Robots-Tag privacy headers individually).
//
// This middleware only ADDS headers that were previously absent everywhere
// -- it never touches Cache-Control/X-Robots-Tag, which stay exactly as
// each page already sets them per its own public/private-page policy.
//
// `script-src`/`style-src` must allow `'unsafe-inline'`: several pages ship
// small per-page `<script>` blocks (e.g. shortlist buttons, the buyer
// contact form) that Astro inlines as processed module scripts with no
// nonce/hash machinery configured. Every template in this package renders
// user-controlled text through Astro's auto-escaped `{expression}` syntax
// only (confirmed: no `set:html` anywhere in `web/src`), so this is a
// measured relaxation, not a known-open XSS hole -- `object-src 'none'`,
// `frame-ancestors 'none'` and `base-uri 'none'` remain strict throughout.
import { defineMiddleware } from "astro:middleware";

const CONTENT_SECURITY_POLICY = [
  "default-src 'self'",
  "script-src 'self' 'unsafe-inline'",
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' data:",
  "object-src 'none'",
  "frame-ancestors 'none'",
  "base-uri 'none'",
].join("; ");

export const onRequest = defineMiddleware(async (context, next) => {
  const response = await next();
  response.headers.set("X-Content-Type-Options", "nosniff");
  response.headers.set("X-Frame-Options", "DENY");
  response.headers.set("Content-Security-Policy", CONTENT_SECURITY_POLICY);
  response.headers.set(
    "Permissions-Policy",
    "geolocation=(), camera=(), microphone=(), payment=(), usb=()",
  );
  if (context.url.protocol === "https:") {
    response.headers.set(
      "Strict-Transport-Security",
      "max-age=63072000; includeSubDomains",
    );
  }
  return response;
});
