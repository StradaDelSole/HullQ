#!/usr/bin/env node
// SLICE-0094 independent-review amendment Finding A: a real headless-
// Chromium exercise of the Power Search form's actual GET submission
// across all five locales -- proving the submit-time field-omission
// script (`../src/lib/searchFormOmission.ts`'s `isUntouchedFormFieldValue`,
// wired into `PowerSearchPageBody.astro` exactly like the already-accepted
// Sail `SearchPageBody.astro` mechanism) genuinely excludes an untouched
// `power_drive`/`power_engine_count` control from the browser's own native
// query-string construction, rather than asserting only the pure helper
// function in isolation.
//
// Invoked as a subprocess by `scripts/inspect_power_search_form.py` after
// it has already spawned the real FastAPI/Astro SSR processes against a
// disposable (empty, migrated) PostgreSQL schema -- no seeded listing is
// required: this script only proves the actual *request URL the browser
// constructs*, never Search truth/matching itself (that is proven
// separately, against real PostgreSQL, by
// `tests/persistence/test_power_engine_count_slice_0094.py` and
// `tests/persistence/test_power_engine_count_api_slice_0094.py`).

import { chromium } from "playwright";

function parseArgs(argv) {
  const args = {};
  for (let i = 0; i < argv.length; i += 2) {
    const key = argv[i].replace(/^--/, "");
    args[key] = argv[i + 1];
  }
  return args;
}

const args = parseArgs(process.argv.slice(2));
const webBase = args["web-base"];

if (!webBase) {
  console.error("usage: inspect_power_search_form_playwright.mjs --web-base URL");
  process.exit(2);
}

const LOCALES = ["en", "de", "fr", "pt", "es"];

const results = [];
function record(label, passed, detail) {
  results.push({ label, passed });
  console.log(`   - ${label} -> ${passed ? "OK" : "FAIL"}${detail ? ` (${detail})` : ""}`);
}

async function submitAndGetSearch(page, baseUrl, { drive, count }) {
  await page.goto(`${baseUrl}/power/search`, { waitUntil: "load" });
  await page.locator('select[name="power_drive"]').selectOption(drive ?? "");
  await page.locator('select[name="power_engine_count"]').selectOption(count ?? "");
  await page.locator('button[type="submit"]').click();
  await page.waitForLoadState("load");
  return new URL(page.url());
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  try {
    const context = await browser.newContext();
    const page = await context.newPage();

    for (const locale of LOCALES) {
      const base = `${webBase}/${locale}`;

      const countOnly = await submitAndGetSearch(page, base, { count: "2" });
      record(
        `[${locale}] count-only submission omits power_drive entirely`,
        countOnly.search === "?power_engine_count=2",
        countOnly.search,
      );

      const driveOnly = await submitAndGetSearch(page, base, { drive: "SHAFT" });
      record(
        `[${locale}] drive-only submission omits power_engine_count entirely`,
        driveOnly.search === "?power_drive=SHAFT",
        driveOnly.search,
      );

      const combined = await submitAndGetSearch(page, base, { drive: "SHAFT", count: "2" });
      record(
        `[${locale}] combined submission carries both in canonical order`,
        combined.search === "?power_drive=SHAFT&power_engine_count=2",
        combined.search,
      );

      // Clearing both controls: load a RESULT page with both pre-selected
      // (via direct navigation, exactly what a buyer's browser history/
      // bookmark would carry), then reset both selects back to "Any" and
      // resubmit -- must reach the true no-param BASE, not an empty-value
      // query string.
      await page.goto(`${base}/power/search?power_drive=SHAFT&power_engine_count=2`, {
        waitUntil: "load",
      });
      await page.locator('select[name="power_drive"]').selectOption("");
      await page.locator('select[name="power_engine_count"]').selectOption("");
      await page.locator('button[type="submit"]').click();
      await page.waitForLoadState("load");
      const cleared = new URL(page.url());
      record(
        `[${locale}] clearing both controls reaches the true no-param BASE`,
        cleared.search === "" && cleared.pathname === `/${locale}/power/search`,
        `${cleared.pathname}${cleared.search}`,
      );
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((r) => !r.passed);
  console.log(`   ${results.length - failed.length}/${results.length} browser checks passed`);
  if (failed.length > 0) {
    console.error(`   FAILED: ${failed.map((f) => f.label).join("; ")}`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("inspect_power_search_form_playwright.mjs crashed:", err);
  process.exit(1);
});
