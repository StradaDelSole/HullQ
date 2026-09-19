// SLICE-0059 contract §15 "Compare-set behavior" and "Truth-safe
// presentation" coverage: zero/one/two-or-more saved id classification, that
// VALUE_ASSERTION/UNKNOWN/omitted concrete-yacht claim states and a missing
// `physical_boat_claims` snapshot all remain visually distinguishable without
// ever falling back to a BoatDesign baseline value, and (independent review
// 2026-09-19, PR #221) that the rendered rows form a genuinely aligned
// side-by-side matrix and freshness disclosure is localized for all five
// locales rather than hardcoded English.
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  buildCompareColumn,
  buildCompareFields,
  compareRowLabels,
  compareRowValues,
  compareSetState,
  type CompareFieldLabels,
} from "../shortlistCompareRuntime.ts";
import { SUPPORTED_LOCALES, shortlistText } from "../shortlistText.ts";
import { shortlistCompareText } from "../shortlistCompareText.ts";
import type { PublicListingData } from "../publicListingApi.ts";
import type { ShortlistItemResult } from "../shortlistResolutionApi.ts";

const t = shortlistCompareText.en;
const enShortlistText = shortlistText.en;
const labels: CompareFieldLabels = {
  priceOnApplicationLabel: enShortlistText.priceOnApplicationLabel,
  freshnessConfirmedLabel: enShortlistText.freshnessConfirmedLabel,
  freshnessDueLabel: enShortlistText.freshnessDueLabel,
};

function baseListing(overrides: Partial<PublicListingData> = {}): PublicListingData {
  return {
    asking_price_mode: "AMOUNT",
    asking_price_amount: "89000.00",
    currency: "EUR",
    location_country: "FR",
    location_region: null,
    broker_summary: null,
    broker_description: "A boat.",
    known_history_narrative: null,
    vat_tax_status_claim: null,
    publishing_organization_id: "ORG-1",
    offer_recorded_at: "2026-01-01T00:00:00Z",
    hullq_vat_verification_status: "UNVERIFIED",
    physical_boat_claims: null,
    freshness_status: "CONFIRMED",
    last_confirmed_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

test("compareSetState: zero saved ids is empty", () => {
  assert.equal(compareSetState([]), "empty");
});

test("compareSetState: one saved id needs one more", () => {
  assert.equal(compareSetState(["NL-1"]), "need_one_more");
});

test("compareSetState: two saved ids are ready to compare", () => {
  assert.equal(compareSetState(["NL-1", "NL-2"]), "ready");
});

test("compareSetState: more than two saved ids are ready to compare", () => {
  assert.equal(compareSetState(["NL-1", "NL-2", "NL-3"]), "ready");
});

test("buildCompareFields: no physical_boat_claims leaves every concrete-yacht row null, never a fallback", () => {
  const fields = buildCompareFields(baseListing(), t, labels);
  assert.equal(fields.identityHeading, null);
  assert.equal(fields.buildYear, null);
  assert.equal(fields.loa, null);
  assert.equal(fields.draft, null);
  assert.equal(fields.keel, null);
  assert.equal(fields.rudder, null);
});

test("buildCompareFields: VALUE_ASSERTION renders the asserted value", () => {
  const fields = buildCompareFields(
    baseListing({
      physical_boat_claims: {
        marketed_brand_claim: "Beneteau",
        model_designation_claim: "Oceanis 30.1",
        build_year: { assertion_kind: "VALUE_ASSERTION", value: 2021 },
        loa_length: { assertion_kind: "VALUE_ASSERTION", value: "9.53" },
        draft: null,
        keel_configuration: null,
        rudder_configuration: null,
      },
    }),
    t,
    labels,
  );
  assert.equal(fields.identityHeading, "Beneteau Oceanis 30.1");
  assert.equal(fields.buildYear, "2021");
  assert.equal(fields.loa, "9.53");
});

test("buildCompareFields: explicit UNKNOWN stays 'Unknown', distinct from omitted", () => {
  const fields = buildCompareFields(
    baseListing({
      physical_boat_claims: {
        marketed_brand_claim: "Beneteau",
        model_designation_claim: "Oceanis 30.1",
        build_year: { assertion_kind: "UNKNOWN", value: null },
        loa_length: null,
        draft: null,
        keel_configuration: null,
        rudder_configuration: null,
      },
    }),
    t,
    labels,
  );
  assert.equal(fields.buildYear, "Unknown");
  assert.equal(fields.loa, "Not supplied");
});

test("buildCompareFields: omitted field is 'Not supplied', never blank or a guessed value", () => {
  const fields = buildCompareFields(
    baseListing({
      physical_boat_claims: {
        marketed_brand_claim: "Beneteau",
        model_designation_claim: "Oceanis 30.1",
        build_year: { assertion_kind: "VALUE_ASSERTION", value: 2021 },
        loa_length: null,
        draft: null,
        keel_configuration: null,
        rudder_configuration: null,
      },
    }),
    t,
    labels,
  );
  assert.equal(fields.loa, "Not supplied");
  assert.equal(fields.draft, "Not supplied");
});

test("buildCompareFields: AMOUNT price renders exact amount and currency, no conversion", () => {
  const fields = buildCompareFields(
    baseListing({ asking_price_mode: "AMOUNT", asking_price_amount: "125000.00", currency: "USD" }),
    t,
    labels,
  );
  assert.equal(fields.price, "125000.00 USD");
});

test("buildCompareFields: POA price uses the localized price-on-application label", () => {
  const fields = buildCompareFields(
    baseListing({ asking_price_mode: "POA", asking_price_amount: null, currency: null }),
    t,
    labels,
  );
  assert.equal(fields.price, labels.priceOnApplicationLabel);
});

test("buildCompareFields: location region VALUE_ASSERTION and UNKNOWN remain distinct; omitted is null", () => {
  const withRegion = buildCompareFields(
    baseListing({ location_region: { assertion_kind: "VALUE_ASSERTION", value: "Brittany" } }),
    t,
    labels,
  );
  assert.equal(withRegion.locationRegion, "Brittany");

  const unknownRegion = buildCompareFields(
    baseListing({ location_region: { assertion_kind: "UNKNOWN", value: null } }),
    t,
    labels,
  );
  assert.equal(unknownRegion.locationRegion, "Unknown");

  const omittedRegion = buildCompareFields(baseListing({ location_region: null }), t, labels);
  assert.equal(omittedRegion.locationRegion, null);
});

test("buildCompareFields: freshness disclosure distinguishes CONFIRMED from DUE_FOR_CONFIRMATION", () => {
  const confirmed = buildCompareFields(
    baseListing({ freshness_status: "CONFIRMED", last_confirmed_at: "2026-01-01T00:00:00Z" }),
    t,
    labels,
  );
  const due = buildCompareFields(
    baseListing({ freshness_status: "DUE_FOR_CONFIRMATION", last_confirmed_at: "2026-01-01T00:00:00Z" }),
    t,
    labels,
  );
  assert.notEqual(confirmed.freshness, due.freshness);
});

test("buildCompareFields: freshness disclosure never drops the last-confirmed timestamp", () => {
  const fields = buildCompareFields(
    baseListing({ freshness_status: "CONFIRMED", last_confirmed_at: "2026-03-01T00:00:00Z" }),
    t,
    labels,
  );
  assert.ok(fields.freshness.includes("2026-03-01T00:00:00Z"));
});

test("buildCompareFields: freshness disclosure is localized for every supported locale, never hardcoded English", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const localeLabels: CompareFieldLabels = {
      priceOnApplicationLabel: shortlistText[locale].priceOnApplicationLabel,
      freshnessConfirmedLabel: shortlistText[locale].freshnessConfirmedLabel,
      freshnessDueLabel: shortlistText[locale].freshnessDueLabel,
    };
    const confirmed = buildCompareFields(
      baseListing({ freshness_status: "CONFIRMED", last_confirmed_at: "2026-01-01T00:00:00Z" }),
      shortlistCompareText[locale],
      localeLabels,
    );
    const due = buildCompareFields(
      baseListing({ freshness_status: "DUE_FOR_CONFIRMATION", last_confirmed_at: "2026-01-01T00:00:00Z" }),
      shortlistCompareText[locale],
      localeLabels,
    );
    assert.ok(confirmed.freshness.startsWith(shortlistText[locale].freshnessConfirmedLabel));
    assert.ok(due.freshness.startsWith(shortlistText[locale].freshnessDueLabel));
    assert.notEqual(confirmed.freshness, due.freshness);
    if (locale !== "en") {
      // The DE/FR/PT/ES status labels are never the English word itself, so
      // this catches a regression back to the English-only helper directly.
      assert.notEqual(confirmed.freshness, `Confirmed current (2026-01-01T00:00:00Z)`);
      assert.notEqual(due.freshness, `Reconfirmation due (2026-01-01T00:00:00Z)`);
    }
  }
});

function availableItem(data: PublicListingData): Extract<ShortlistItemResult, { state: "available" }> {
  return { native_listing_id: "NL-AVAILABLE", state: "available", data };
}

test("buildCompareColumn: available item carries its derived fields and a listing link", () => {
  const column = buildCompareColumn(
    availableItem(
      baseListing({
        physical_boat_claims: {
          marketed_brand_claim: "Beneteau",
          model_designation_claim: "Oceanis 30.1",
          build_year: { assertion_kind: "VALUE_ASSERTION", value: 2021 },
          loa_length: null,
          draft: null,
          keel_configuration: null,
          rudder_configuration: null,
        },
      }),
    ),
    t,
    labels,
    "unavailable",
    "service error",
  );
  assert.equal(column.state, "available");
  assert.equal(column.headingText, "Beneteau Oceanis 30.1");
  assert.equal(column.headingHref, "/listings/NL-AVAILABLE");
  assert.notEqual(column.fields, null);
});

test("buildCompareColumn: unavailable/service-error items carry no fields and no link, but stay in the column set", () => {
  const unavailable = buildCompareColumn(
    { native_listing_id: "NL-UNAVAILABLE", state: "unavailable" },
    t,
    labels,
    "unavailable message",
    "service error message",
  );
  assert.equal(unavailable.state, "unavailable");
  assert.equal(unavailable.headingText, "unavailable message");
  assert.equal(unavailable.headingHref, null);
  assert.equal(unavailable.fields, null);

  const serviceError = buildCompareColumn(
    { native_listing_id: "NL-ERROR", state: "service_error" },
    t,
    labels,
    "unavailable message",
    "service error message",
  );
  assert.equal(serviceError.state, "service_error");
  assert.equal(serviceError.headingText, "service error message");
  assert.equal(serviceError.fields, null);
});

test("compareRowValues: an available column's row values align 1:1 with compareRowLabels", () => {
  const fields = buildCompareFields(
    baseListing({
      physical_boat_claims: {
        marketed_brand_claim: "Beneteau",
        model_designation_claim: "Oceanis 30.1",
        build_year: { assertion_kind: "VALUE_ASSERTION", value: 2021 },
        loa_length: { assertion_kind: "VALUE_ASSERTION", value: "9.53" },
        draft: { assertion_kind: "UNKNOWN", value: null },
        keel_configuration: null,
        rudder_configuration: null,
      },
    }),
    t,
    labels,
  );
  const rowLabels = compareRowLabels(t);
  const rowValues = compareRowValues(fields, t);
  assert.equal(rowValues.length, rowLabels.length);
  assert.equal(rowValues[rowLabels.indexOf(t.priceLabel)], fields.price);
  assert.equal(rowValues[rowLabels.indexOf(t.buildYearLabel)], "2021");
  assert.equal(rowValues[rowLabels.indexOf(t.loaLabel)], "9.53");
  assert.equal(rowValues[rowLabels.indexOf(t.draftLabel)], "Unknown");
  assert.equal(rowValues[rowLabels.indexOf(t.keelLabel)], "Not supplied");
});

test("compareRowValues: an unavailable/service-error column (fields === null) fills every aligned row with the neutral placeholder, same length as an available column", () => {
  const rowLabels = compareRowLabels(t);
  const placeholderValues = compareRowValues(null, t);
  assert.equal(placeholderValues.length, rowLabels.length);
  assert.ok(placeholderValues.every((value) => value === "—"));

  const availableValues = compareRowValues(buildCompareFields(baseListing(), t, labels), t);
  assert.equal(placeholderValues.length, availableValues.length);
});

test("compareRowLabels/compareRowValues: identical row order for every column enables genuine side-by-side alignment", () => {
  const columnA = compareRowValues(
    buildCompareFields(baseListing({ asking_price_amount: "10000.00" }), t, labels),
    t,
  );
  const columnB = compareRowValues(null, t);
  const columnC = compareRowValues(
    buildCompareFields(baseListing({ asking_price_amount: "20000.00" }), t, labels),
    t,
  );
  // Every column has the exact same number of rows in the exact same
  // order, so row index N always means the same factual field across the
  // whole matrix -- the defining property of an aligned side-by-side
  // comparison rather than independent, differently-shaped cards.
  assert.equal(columnA.length, columnB.length);
  assert.equal(columnB.length, columnC.length);
  const priceRowIndex = compareRowLabels(t).indexOf(t.priceLabel);
  assert.equal(columnA[priceRowIndex], "10000.00 EUR");
  assert.equal(columnB[priceRowIndex], "—");
  assert.equal(columnC[priceRowIndex], "20000.00 EUR");
});
