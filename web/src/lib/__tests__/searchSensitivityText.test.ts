// SLICE-0057 bounded web smoke test: every required public language has
// complete, non-empty buyer-requirement-sensitivity presentation text
// (contract §12), the interpolating functions actually interpolate, and no
// locale's copy uses recommendation/score/winner language (contract §12/§19
// hard decision-neutrality boundary).
import assert from "node:assert/strict";
import { test } from "node:test";

import { SUPPORTED_LOCALES, searchText } from "../searchText.ts";

test("every supported locale has complete non-empty sensitivity text", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.sensitivityFormNote.length > 0, `${locale}.sensitivityFormNote`);
    assert.ok(t.sensitivityDraftSubmitLabel.length > 0, `${locale}.sensitivityDraftSubmitLabel`);
    assert.ok(t.sensitivityKeelSubmitLabel.length > 0, `${locale}.sensitivityKeelSubmitLabel`);
    assert.ok(
      t.sensitivityAlternativeDraftLabel.length > 0,
      `${locale}.sensitivityAlternativeDraftLabel`,
    );
    assert.ok(
      t.sensitivityAlternativeKeelLabel.length > 0,
      `${locale}.sensitivityAlternativeKeelLabel`,
    );
    assert.ok(t.sensitivityPageTitle.length > 0, `${locale}.sensitivityPageTitle`);
    assert.ok(t.sensitivityCurrentHeading.length > 0, `${locale}.sensitivityCurrentHeading`);
    assert.ok(t.sensitivityAlternativeHeading.length > 0, `${locale}.sensitivityAlternativeHeading`);
    assert.ok(t.sensitivityViewAlternativeSearch.length > 0, `${locale}.sensitivityViewAlternativeSearch`);
    assert.ok(t.sensitivityInvalidTitle.length > 0, `${locale}.sensitivityInvalidTitle`);
    assert.ok(t.sensitivityInvalidFallback.length > 0, `${locale}.sensitivityInvalidFallback`);
    assert.ok(
      t.sensitivityServiceUnavailableTitle.length > 0,
      `${locale}.sensitivityServiceUnavailableTitle`,
    );
    assert.ok(
      t.sensitivityServiceUnavailableMessage.length > 0,
      `${locale}.sensitivityServiceUnavailableMessage`,
    );
    assert.ok(
      t.sensitivityMethodNotAllowedTitle.length > 0,
      `${locale}.sensitivityMethodNotAllowedTitle`,
    );
    assert.ok(
      t.sensitivityMethodNotAllowedMessage.length > 0,
      `${locale}.sensitivityMethodNotAllowedMessage`,
    );
  }
});

test("sensitivity count functions interpolate their arguments", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(
      t.sensitivityCurrentConfirmedLabel(7).includes("7"),
      `${locale}.sensitivityCurrentConfirmedLabel`,
    );
    assert.ok(
      t.sensitivityAlternativeConfirmedLabel(9).includes("9"),
      `${locale}.sensitivityAlternativeConfirmedLabel`,
    );
    assert.ok(
      t.sensitivityNewlyConfirmedLabel(2).includes("2"),
      `${locale}.sensitivityNewlyConfirmedLabel`,
    );
    assert.ok(
      t.sensitivityNoLongerConfirmedLabel(4).includes("4"),
      `${locale}.sensitivityNoLongerConfirmedLabel`,
    );
    assert.ok(
      t.sensitivityCurrentInsufficientLabel(1).includes("1"),
      `${locale}.sensitivityCurrentInsufficientLabel`,
    );
    assert.ok(
      t.sensitivityAlternativeInsufficientLabel(5).includes("5"),
      `${locale}.sensitivityAlternativeInsufficientLabel`,
    );
  }
});

// Contract §12/§19 hard decision-neutrality boundary: no sensitivity copy
// may use recommendation/score/winner language in any supported locale.
// English-language markers are the ones the contract itself names; this
// check is necessarily English-specific (the other locales are translated
// prose, not machine-checked against an equivalent banned-word list).
test("English sensitivity copy avoids recommendation/score/winner language", () => {
  const banned = ["recommend", "better", "worse", "optimal", "should", "relax this", "best fit"];
  const t = searchText.en;
  const haystacks = [
    t.sensitivityFormNote,
    t.sensitivityDraftSubmitLabel,
    t.sensitivityKeelSubmitLabel,
    t.sensitivityAlternativeDraftLabel,
    t.sensitivityAlternativeKeelLabel,
    t.sensitivityPageTitle,
    t.sensitivityCurrentHeading,
    t.sensitivityAlternativeHeading,
    t.sensitivityCurrentConfirmedLabel(1),
    t.sensitivityAlternativeConfirmedLabel(1),
    t.sensitivityNewlyConfirmedLabel(1),
    t.sensitivityNoLongerConfirmedLabel(1),
    t.sensitivityCurrentInsufficientLabel(1),
    t.sensitivityAlternativeInsufficientLabel(1),
    t.sensitivityViewAlternativeSearch,
    t.sensitivityInvalidTitle,
    t.sensitivityInvalidFallback,
    t.sensitivityServiceUnavailableTitle,
    t.sensitivityServiceUnavailableMessage,
    t.sensitivityMethodNotAllowedTitle,
    t.sensitivityMethodNotAllowedMessage,
  ].join(" \n ");
  const lower = haystacks.toLowerCase();
  for (const word of banned) {
    assert.ok(!lower.includes(word), `unexpected recommendation language: ${word}`);
  }
});
