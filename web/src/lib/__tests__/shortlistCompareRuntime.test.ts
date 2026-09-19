// SLICE-0059 contract §15 "Compare-set behavior" and "Truth-safe
// presentation" coverage: zero/one/two-or-more saved id classification, and
// that VALUE_ASSERTION/UNKNOWN/omitted concrete-yacht claim states and a
// missing `physical_boat_claims` snapshot all remain visually distinguishable
// without ever falling back to a BoatDesign baseline value.
import assert from "node:assert/strict";
import { test } from "node:test";

import { buildCompareFields, compareSetState } from "../shortlistCompareRuntime.ts";
import { shortlistCompareText } from "../shortlistCompareText.ts";
import type { PublicListingData } from "../publicListingApi.ts";

const t = shortlistCompareText.en;
const priceOnApplicationLabel = "Price on application";

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
  const fields = buildCompareFields(baseListing(), t, priceOnApplicationLabel);
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
    priceOnApplicationLabel,
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
    priceOnApplicationLabel,
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
    priceOnApplicationLabel,
  );
  assert.equal(fields.loa, "Not supplied");
  assert.equal(fields.draft, "Not supplied");
});

test("buildCompareFields: AMOUNT price renders exact amount and currency, no conversion", () => {
  const fields = buildCompareFields(
    baseListing({ asking_price_mode: "AMOUNT", asking_price_amount: "125000.00", currency: "USD" }),
    t,
    priceOnApplicationLabel,
  );
  assert.equal(fields.price, "125000.00 USD");
});

test("buildCompareFields: POA price uses the localized price-on-application label", () => {
  const fields = buildCompareFields(
    baseListing({ asking_price_mode: "POA", asking_price_amount: null, currency: null }),
    t,
    priceOnApplicationLabel,
  );
  assert.equal(fields.price, priceOnApplicationLabel);
});

test("buildCompareFields: location region VALUE_ASSERTION and UNKNOWN remain distinct; omitted is null", () => {
  const withRegion = buildCompareFields(
    baseListing({ location_region: { assertion_kind: "VALUE_ASSERTION", value: "Brittany" } }),
    t,
    priceOnApplicationLabel,
  );
  assert.equal(withRegion.locationRegion, "Brittany");

  const unknownRegion = buildCompareFields(
    baseListing({ location_region: { assertion_kind: "UNKNOWN", value: null } }),
    t,
    priceOnApplicationLabel,
  );
  assert.equal(unknownRegion.locationRegion, "Unknown");

  const omittedRegion = buildCompareFields(baseListing({ location_region: null }), t, priceOnApplicationLabel);
  assert.equal(omittedRegion.locationRegion, null);
});

test("buildCompareFields: freshness disclosure distinguishes CONFIRMED from DUE_FOR_CONFIRMATION", () => {
  const confirmed = buildCompareFields(
    baseListing({ freshness_status: "CONFIRMED", last_confirmed_at: "2026-01-01T00:00:00Z" }),
    t,
    priceOnApplicationLabel,
  );
  const due = buildCompareFields(
    baseListing({ freshness_status: "DUE_FOR_CONFIRMATION", last_confirmed_at: "2026-01-01T00:00:00Z" }),
    t,
    priceOnApplicationLabel,
  );
  assert.notEqual(confirmed.freshness, due.freshness);
});
