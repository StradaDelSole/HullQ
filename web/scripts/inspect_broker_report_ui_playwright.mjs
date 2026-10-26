#!/usr/bin/env node
// SLICE-0089: a real headless-Chromium exercise of the broker periodic
// performance report UI -- the Download link produces a genuine browser
// download event with real HTML bytes, and the periodic-delivery
// subscription form genuinely saves through a real browser form POST.
// Invoked as a subprocess by
// `scripts/inspect_broker_periodic_performance_reporting.py` after it has
// already spawned the real FastAPI/Astro SSR processes and seeded real
// PostgreSQL-backed fixtures; this script only drives the browser against
// that already-running stack and reports PASS/FAIL per check on stdout,
// exiting non-zero if any check failed.

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

if (!webBase || !orgId || !sessionCookie) {
  console.error(
    "usage: inspect_broker_report_ui_playwright.mjs --web-base URL --org-id ID --session-cookie TOKEN",
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
  const downloadDir = mkdtempSync(path.join(tmpdir(), "hullq_s0089_pw_dl_"));
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

    await page.goto(`${webBase}/broker/organizations/${orgId}/performance`, {
      waitUntil: "load",
    });
    const downloadLinkVisible = await page
      .locator("#download-report-link")
      .isVisible()
      .catch(() => false);
    record("performance page renders a Download report link", downloadLinkVisible);
    if (!downloadLinkVisible) {
      throw new Error("download link never rendered; aborting remaining checks");
    }

    const [download] = await Promise.all([
      page.waitForEvent("download", { timeout: 10_000 }),
      page.locator("#download-report-link").click(),
    ]);
    const savedPath = path.join(downloadDir, "report.html");
    await download.saveAs(savedPath);
    const downloadedBytes = readFileSync(savedPath, "utf-8");
    record(
      "a real browser-triggered click produced a genuine standalone HTML report",
      downloadedBytes.startsWith("<!doctype html") && downloadedBytes.includes("<table"),
      `${downloadedBytes.length} bytes`,
    );
    record(
      "the downloaded report never embeds a script or remote resource",
      !/<script/i.test(downloadedBytes) && !/https?:\/\//i.test(downloadedBytes),
    );

    // Periodic delivery subscription form: a real browser form POST
    // (status=ACTIVE, period_kind=MONTHLY, a recipient email) actually
    // saves and the page reflects the saved confirmation on reload.
    await page.locator("#sub-status").selectOption("ACTIVE");
    await page.locator("#sub-period-kind").selectOption("MONTHLY");
    await page.locator("#sub-recipient").fill("broker-pw@example.com");
    await Promise.all([
      page.waitForLoadState("load"),
      page.locator("#subscription-save-button").click(),
    ]);
    const savedNoticeVisible = await page
      .locator("#subscription-saved-notice")
      .isVisible()
      .catch(() => false);
    record("a real browser form submit saves the periodic delivery subscription", savedNoticeVisible);
    const recipientPersisted = await page.locator("#sub-recipient").inputValue();
    record(
      "the saved recipient email is reflected back after reload",
      recipientPersisted === "broker-pw@example.com",
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
  console.error("inspect_broker_report_ui_playwright.mjs crashed:", err);
  process.exit(1);
});
