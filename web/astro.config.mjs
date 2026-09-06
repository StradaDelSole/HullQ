// SLICE-0048: HullQ's first bounded Astro + TypeScript web package.
//
// `output: "server"` + the Node adapter in standalone mode gives one real
// SSR HTTP server for the single `/_preview/listings/{preview_token}` route
// required by this slice. No React/other UI framework integration is added:
// this page needs none.
import node from "@astrojs/node";
import { defineConfig } from "astro/config";

// Astro's file-based `src/pages` router silently excludes any path segment
// starting with "_" (it treats it as a private/non-route file, the same
// convention as `_utils.ts`). SLICE-0048 §7 requires the literal route
// `/_preview/listings/{preview_token}`, so the real component lives outside
// `src/pages` (at `src/routes/preview_listing.astro`) and is wired to that
// exact pattern with `injectRoute` instead -- this is the only way to keep
// both the required underscore-prefixed URL and normal Astro routing.
function previewRouteIntegration() {
  return {
    name: "hullq-preview-route",
    hooks: {
      "astro:config:setup": ({ injectRoute }) => {
        injectRoute({
          pattern: "/_preview/listings/[preview_token]",
          entrypoint: "./src/routes/preview_listing.astro",
          prerender: false,
        });
      },
    },
  };
}

export default defineConfig({
  output: "server",
  adapter: node({ mode: "standalone" }),
  integrations: [previewRouteIntegration()],
  server: {
    host: "127.0.0.1",
  },
});
