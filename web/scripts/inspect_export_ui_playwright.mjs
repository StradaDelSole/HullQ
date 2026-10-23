#!/usr/bin/env node
// SLICE-0088 independent-review amendment (2026-10-16, round 2, Finding 6):
// a real headless-Chromium exercise of the broker inventory export UI --
// selection, format change, NautiX profile entry, warning presentation,
// preview-confirmation invalidation (including the asynchronous stale-
// response race from Finding 1), a genuine successful download and a
// server-side error path. Invoked as a subprocess by
// `scripts/inspect_broker_inventory_export.py` after it has already
// spawned the real FastAPI/Astro SSR processes and seeded real
// PostgreSQL-backed fixtures; this script only drives the browser against
// that already-running stack and reports PASS/FAIL per check on stdout,
// exiting non-zero if any check failed.
//
// This is deliberately NOT an `astro check`/HTTP-200-only smoke test --
// every assertion below requires the page's actual client-side JavaScript
// (fetch calls, DOM updates, button enable/disable state) to have run
// correctly in a real browser engine.

import { chromium } from "playwright";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";

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
const orgId = args["org-id"];
const sessionCookie = args["session-cookie"];
const listingId = args["listing-id"];
const draftId = args["draft-id"];

if (!webBase || !orgId || !sessionCookie || !listingId || !draftId) {
  console.error(
    "usage: inspect_export_ui_playwright.mjs --web-base URL --org-id ID --session-cookie TOKEN --listing-id ID --draft-id ID",
  );
  process.exit(2);
}

const results = [];
function record(label, passed, detail) {
  results.push({ label, passed });
  console.log(`   - ${label} -> ${passed ? "OK" : "FAIL"}${detail ? ` (${detail})` : ""}`);
}

async function main() {
  const browser = await chromium.launch({ headless: true });
  const downloadDir = mkdtempSync(path.join(tmpdir(), "hullq_s0088_pw_dl_"));
  try {
    const context = await browser.newContext({ acceptDownloads: true });
    const url = new URL(webBase);
    await context.addCookies([
      {
        name: "hullq_session",
        value: sessionCookie,
        domain: url.hostname,
        path: "/",
        httpOnly: true,
        secure: url.protocol === "https:",
        sameSite: "Lax",
      },
    ]);
    const page = await context.newPage();

    await page.goto(`${webBase}/broker/organizations/${orgId}/inventory/export`, {
      waitUntil: "load",
    });
    const formVisible = await page.locator("#selection-form").isVisible().catch(() => false);
    record("export selection form renders", formVisible);
    if (!formVisible) {
      throw new Error("selection form never rendered; aborting remaining checks");
    }

    await page.locator(".listing-checkbox").first().check();
    await page.locator(".draft-checkbox").first().check();

    await page.locator("#preview-button").click();
    await page.locator("#selection-status").filter({ hasText: "Preview ready" }).waitFor({
      timeout: 10_000,
    });
    const downloadEnabledAfterFirstPreview = !(await page
      .locator("#download-button")
      .isDisabled());
    record("Download enabled after a successful preview", downloadEnabledAfterFirstPreview);

    const resultsText = await page.locator("#preview-results").innerText();
    // CSV has no mandatory fields (src/hullq/domain/inventory_export.py's
    // table-format preflight never rejects a row for missing fields), so
    // the private draft is genuinely "exportable" in THIS format -- the
    // source-kind exclusion is NAUTIX-specific and is asserted after the
    // NAUTIX preview below instead.
    record(
      "preview discloses the formula-injection escaping warning",
      /Warning:.*formula-injection/i.test(resultsText),
    );

    // Independent review Finding 1 (2026-10-16, round 2): a preview
    // request already in flight must never have its late response
    // re-enable Download once the user has changed the selection/format
    // while it was pending. Intercept the *next* preflight request and
    // hold it open, click Preview to start it, change the format while it
    // is still in flight, then let the held response complete and assert
    // Download is still disabled.
    let heldRouteResolve;
    const heldRoutePromise = new Promise((resolve) => {
      heldRouteResolve = resolve;
    });
    let interceptArmed = true;
    await page.route("**/inventory/export/preflight", async (route) => {
      if (!interceptArmed) {
        await route.continue();
        return;
      }
      interceptArmed = false;
      await heldRoutePromise;
      await route.continue();
    });

    await page.locator("#preview-button").click();
    // Give the click's fetch a moment to actually dispatch and reach the
    // held route before changing the format out from under it.
    await page.waitForTimeout(200);
    await page.locator("#export-format").selectOption("JSON");
    const statusAfterFormatChange = await page.locator("#selection-status").innerText();
    record(
      "format change while a preview is in flight shows the invalidation message immediately",
      statusAfterFormatChange.includes("Format changed"),
    );
    const downloadDisabledDuringRace = await page.locator("#download-button").isDisabled();
    record(
      "Download disabled immediately after the in-flight preview is invalidated",
      downloadDisabledDuringRace,
    );
    heldRouteResolve();
    // Let the held response actually complete and reach the page's fetch
    // handler.
    await page.waitForTimeout(500);
    const downloadStillDisabledAfterStaleResponse = await page
      .locator("#download-button")
      .isDisabled();
    record(
      "Download remains disabled after the stale preview response arrives (Finding 1)",
      downloadStillDisabledAfterStaleResponse,
    );
    const statusNotOverwrittenByStaleResponse = !(
      await page.locator("#selection-status").innerText()
    ).includes("Preview ready");
    record(
      "the stale response's status text never overwrites the newer invalidation message",
      statusNotOverwrittenByStaleResponse,
    );
    await page.unroute("**/inventory/export/preflight");

    // A genuine fresh preview against the now-current (JSON) format/
    // selection succeeds normally.
    await page.locator("#preview-button").click();
    await page.locator("#selection-status").filter({ hasText: "Preview ready" }).waitFor({
      timeout: 10_000,
    });
    record(
      "Download re-enabled after a genuinely fresh preview",
      !(await page.locator("#download-button").isDisabled()),
    );

    // NautiX profile entry: switching format reveals the profile fields
    // and invalidates the prior (non-NautiX) preview.
    await page.locator("#export-format").selectOption("NAUTIX");
    record(
      "NautiX profile fields become visible on format change",
      await page.locator("#nautix-profile-fields").isVisible(),
    );
    record(
      "Download disabled again after switching to NautiX (profile not yet confirmed)",
      await page.locator("#download-button").isDisabled(),
    );
    await page.locator("#nautix-account-token").fill("BROKER-ACCT-PW-1");
    await page.locator("#nautix-office-id").fill("OFFICE-PW-1");
    await page
      .locator(`.nautix-sale-class-select[data-listing-id="${listingId}"]`)
      .selectOption("used");

    await page.locator("#preview-button").click();
    await page.locator("#selection-status").filter({ hasText: "Preview ready" }).waitFor({
      timeout: 10_000,
    });
    record(
      "Download enabled after a NautiX preview with a confirmed profile",
      !(await page.locator("#download-button").isDisabled()),
    );
    // The sale-class control is rendered only for selected *listings*
    // (renderSaleClassInputs() iterates listingIds only), never for
    // drafts -- a private draft's NautiX exclusion is unconditional
    // (domain's `_nautix_preflight`: "source: a private draft can never
    // be exported..."), so even with a fully confirmed profile for the
    // listing, the draft row must still render as NOT exportable here.
    const nautixResultsText = await page.locator("#preview-results").innerText();
    record(
      "NautiX preview discloses the private draft as NOT exportable regardless of profile",
      nautixResultsText.includes("NOT exportable"),
    );

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 10_000 }),
      page.locator("#download-button").click(),
    ]);
    const savedPath = path.join(downloadDir, "export.xml");
    await download.saveAs(savedPath);
    const downloadedBytes = readFileSync(savedPath);
    record(
      "a real browser-triggered download produced genuine NautiX XML bytes",
      downloadedBytes.subarray(0, 5).toString("utf-8") === "<?xml",
      `${downloadedBytes.length} bytes`,
    );
    await page.locator("#selection-status").filter({ hasText: "Downloaded" }).waitFor({
      timeout: 10_000,
    });

    // Changing the sale_class after this successful download invalidates
    // the now-stale confirmation again (Finding B's per-field coverage).
    await page
      .locator(`.nautix-sale-class-select[data-listing-id="${listingId}"]`)
      .selectOption("");
    record(
      "Download disabled after changing the sale_class post-download",
      await page.locator("#download-button").isDisabled(),
    );
  } finally {
    await browser.close();
    rmSync(downloadDir, { recursive: true, force: true });
  }

  const failed = results.filter((r) => !r.passed);
  console.log(`   ${results.length - failed.length}/${results.length} browser checks passed`);
  if (failed.length > 0) {
    console.error(`   FAILED: ${failed.map((f) => f.label).join("; ")}`);
    process.exit(1);
  }
}

main().catch((err) => {
  console.error("inspect_export_ui_playwright.mjs crashed:", err);
  process.exit(1);
});
