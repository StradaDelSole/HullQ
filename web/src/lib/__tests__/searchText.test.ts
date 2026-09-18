// SLICE-0051 bounded web smoke test: every required public language
// (docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md) has complete, non-empty
// Search presentation text, and the buyer-facing function fields actually
// interpolate the values they are given (Required Behavior §I).
import assert from "node:assert/strict";
import { test } from "node:test";

import { SEARCH_KEEL_CONFIGURATION_VALUES } from "../searchApi.ts";
import { SUPPORTED_LOCALES, searchText } from "../searchText.ts";

test("every supported locale has complete non-empty text", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.title.length > 0, `${locale}.title`);
    assert.ok(t.draftMaxLabel.length > 0, `${locale}.draftMaxLabel`);
    assert.ok(t.keelConfigurationLabel.length > 0, `${locale}.keelConfigurationLabel`);
    assert.ok(t.keelConfigurationAnyOption.length > 0, `${locale}.keelConfigurationAnyOption`);
    assert.ok(t.submit.length > 0, `${locale}.submit`);
    assert.ok(t.formInstructions.length > 0, `${locale}.formInstructions`);
    assert.ok(t.invalidTitle.length > 0, `${locale}.invalidTitle`);
    assert.ok(t.invalidFallback.length > 0, `${locale}.invalidFallback`);
    assert.ok(t.confirmedHeading.length > 0, `${locale}.confirmedHeading`);
    assert.ok(t.noConfirmedMatches.length > 0, `${locale}.noConfirmedMatches`);
    assert.ok(t.noConfirmedMatchesGeneric.length > 0, `${locale}.noConfirmedMatchesGeneric`);
    assert.ok(t.viewListing.length > 0, `${locale}.viewListing`);
    assert.ok(t.serviceUnavailableTitle.length > 0, `${locale}.serviceUnavailableTitle`);
    assert.ok(t.serviceUnavailableMessage.length > 0, `${locale}.serviceUnavailableMessage`);
    assert.ok(t.freshnessConfirmedLabel.length > 0, `${locale}.freshnessConfirmedLabel`);
    assert.ok(t.freshnessDueLabel.length > 0, `${locale}.freshnessDueLabel`);
    assert.ok(t.freshnessDueNote.length > 0, `${locale}.freshnessDueNote`);
    assert.notEqual(
      t.freshnessConfirmedLabel,
      t.freshnessDueLabel,
      `${locale}: DUE must be visibly distinct from CONFIRMED`,
    );
    assert.notEqual(
      t.noConfirmedMatches,
      t.noConfirmedMatchesGeneric,
      `${locale}: the draft-only wording must stay verbatim, distinct from the generic keel/mixed wording`,
    );
  }
});

test("requirementSummary/resolvedDraftText/insufficientDataText interpolate their arguments", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.requirementSummary("1.6").includes("1.6"), `${locale}.requirementSummary`);
    assert.ok(t.resolvedDraftText("1.40").includes("1.40"), `${locale}.resolvedDraftText`);
    assert.ok(t.insufficientDataText(3).includes("3"), `${locale}.insufficientDataText`);
  }
});

// SLICE-0056: every supported locale has a non-empty display label for each
// of the six accepted technical keel values, and the keel-specific
// interpolating functions actually interpolate.
test("every supported locale has a complete keelConfigurationLabels mapping", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const labels = searchText[locale].keelConfigurationLabels;
    for (const value of SEARCH_KEEL_CONFIGURATION_VALUES) {
      assert.ok(labels[value].length > 0, `${locale}.keelConfigurationLabels.${value}`);
    }
  }
});

test("requirementSummaryKeelOnly/requirementSummaryMixed/resolvedKeelText/insufficientDataTextGeneric interpolate their arguments", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(
      t.requirementSummaryKeelOnly("Fin keel").includes("Fin keel"),
      `${locale}.requirementSummaryKeelOnly`,
    );
    const mixed = t.requirementSummaryMixed("1.6", "Fin keel");
    assert.ok(mixed.includes("1.6"), `${locale}.requirementSummaryMixed (draft)`);
    assert.ok(mixed.includes("Fin keel"), `${locale}.requirementSummaryMixed (keel)`);
    assert.ok(t.resolvedKeelText("Fin keel").includes("Fin keel"), `${locale}.resolvedKeelText`);
    assert.ok(
      t.insufficientDataTextGeneric(3).includes("3"),
      `${locale}.insufficientDataTextGeneric`,
    );
  }
});
