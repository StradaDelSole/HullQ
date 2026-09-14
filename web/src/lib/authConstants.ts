// SLICE-0053: values shared between the Astro Broker Workspace pages and
// FastAPI's Auth0-compatible adapter. Must stay byte-identical to
// `hullq.security.oidc.AUTH0_MFA_STEP_UP_ACR_VALUE` -- see that constant's
// docstring for the required Auth0 Post-Login Action configuration.

/**
 * The standard OIDC/PAPE ACR value ("multi-factor") requested on the
 * `/authorize` step-up redirect. Independent review (2026-09-14,
 * exact-head a7fee1a0) replaced an earlier test-only `acr_values=mfa`
 * shorthand with this Auth0-documented value so the production request
 * this page sends is exactly what a real Auth0 tenant expects.
 */
export const AUTH0_MFA_STEP_UP_ACR_VALUE =
  "http://schemas.openid.net/pape/policies/2007/06/multi-factor";
