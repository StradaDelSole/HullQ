// SLICE-0051 bounded web smoke test: every required public language
// (docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md) has complete, non-empty
// Search presentation text, and the buyer-facing function fields actually
// interpolate the values they are given (Required Behavior §I).
import assert from "node:assert/strict";
import { test } from "node:test";

import { SUPPORTED_LOCALES, searchText } from "../searchText.ts";

test("every supported locale has complete non-empty text", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.title.length > 0, `${locale}.title`);
    assert.ok(t.draftMaxLabel.length > 0, `${locale}.draftMaxLabel`);
    assert.ok(t.submit.length > 0, `${locale}.submit`);
    assert.ok(t.formInstructions.length > 0, `${locale}.formInstructions`);
    assert.ok(t.invalidTitle.length > 0, `${locale}.invalidTitle`);
    assert.ok(t.invalidFallback.length > 0, `${locale}.invalidFallback`);
    assert.ok(t.confirmedHeading.length > 0, `${locale}.confirmedHeading`);
    assert.ok(t.noConfirmedMatches.length > 0, `${locale}.noConfirmedMatches`);
    assert.ok(t.viewListing.length > 0, `${locale}.viewListing`);
    assert.ok(t.serviceUnavailableTitle.length > 0, `${locale}.serviceUnavailableTitle`);
    assert.ok(t.serviceUnavailableMessage.length > 0, `${locale}.serviceUnavailableMessage`);
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
