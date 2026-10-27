// SLICE-0051 bounded web smoke test: every required public language
// (docs/PRODUCT_LANGUAGE_AND_I18N_REQUIREMENT.md) has complete, non-empty
// Search presentation text, and the buyer-facing function fields actually
// interpolate the values they are given (Required Behavior §I).
import assert from "node:assert/strict";
import { test } from "node:test";

import {
  SEARCH_COCKPIT_POSITION_VALUES,
  SEARCH_DECK_SALOON_VALUES,
  SEARCH_HULL_CONFIGURATION_VALUES,
  SEARCH_HULL_MATERIAL_VALUES,
  SEARCH_KEEL_CONFIGURATION_VALUES,
  SEARCH_RUDDER_CONFIGURATION_VALUES,
} from "../searchApi.ts";
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
    // SLICE-0092: design-unresolved publisher-claim-only result text.
    assert.ok(
      t.publisherClaimHeading(2).length > 0,
      `${locale}.publisherClaimHeading`,
    );
    assert.ok(t.publisherClaimDisclaimer.length > 0, `${locale}.publisherClaimDisclaimer`);
    assert.ok(t.noPublisherClaimMatches.length > 0, `${locale}.noPublisherClaimMatches`);
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
    assert.ok(
      t.publisherClaimHeading(5).includes("5"),
      `${locale}.publisherClaimHeading must interpolate its count`,
    );
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

// SLICE-0085: LOA/rudder presentation text -- every supported locale has
// complete non-empty labels/placeholders, a complete rudderConfigurationLabels
// mapping, and every new interpolating function actually interpolates.
test("every supported locale has complete non-empty LOA/rudder text", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.loaMinLabel.length > 0, `${locale}.loaMinLabel`);
    assert.ok(t.loaMaxLabel.length > 0, `${locale}.loaMaxLabel`);
    assert.ok(t.loaMinPlaceholder.length > 0, `${locale}.loaMinPlaceholder`);
    assert.ok(t.loaMaxPlaceholder.length > 0, `${locale}.loaMaxPlaceholder`);
    assert.ok(t.rudderConfigurationLabel.length > 0, `${locale}.rudderConfigurationLabel`);
    assert.ok(
      t.rudderConfigurationAnyOption.length > 0,
      `${locale}.rudderConfigurationAnyOption`,
    );
    assert.ok(t.requirementSummaryListConjunction.length > 0, `${locale}.requirementSummaryListConjunction`);
    // Review amendment Finding A: the truthful explanation shown instead of
    // the sensitivity forms whenever a new criterion is also active.
    assert.ok(
      t.sensitivityUnavailableWithNewCriteria.length > 0,
      `${locale}.sensitivityUnavailableWithNewCriteria`,
    );
  }
});

test("every supported locale has a complete rudderConfigurationLabels mapping", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const labels = searchText[locale].rudderConfigurationLabels;
    for (const value of SEARCH_RUDDER_CONFIGURATION_VALUES) {
      assert.ok(labels[value].length > 0, `${locale}.rudderConfigurationLabels.${value}`);
    }
  }
});

test("LOA/rudder requirement phrases and resolved-evidence text interpolate their arguments", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.requirementPhraseDraftMax("1.6").includes("1.6"), `${locale}.requirementPhraseDraftMax`);
    assert.ok(t.requirementPhraseKeel("Fin keel").includes("Fin keel"), `${locale}.requirementPhraseKeel`);
    assert.ok(t.requirementPhraseLoaMin("10").includes("10"), `${locale}.requirementPhraseLoaMin`);
    assert.ok(t.requirementPhraseLoaMax("15").includes("15"), `${locale}.requirementPhraseLoaMax`);
    const range = t.requirementPhraseLoaRange("10", "15");
    assert.ok(range.includes("10"), `${locale}.requirementPhraseLoaRange (min)`);
    assert.ok(range.includes("15"), `${locale}.requirementPhraseLoaRange (max)`);
    assert.ok(
      t.requirementPhraseRudder("Skeg-hung rudder").includes("Skeg-hung rudder"),
      `${locale}.requirementPhraseRudder`,
    );
    assert.ok(
      t.requirementSummaryGeneric("X").includes("X"),
      `${locale}.requirementSummaryGeneric`,
    );
    assert.ok(t.resolvedLoaText("10.50").includes("10.50"), `${locale}.resolvedLoaText`);
    assert.ok(
      t.resolvedRudderText("Skeg-hung rudder").includes("Skeg-hung rudder"),
      `${locale}.resolvedRudderText`,
    );
  }
});

// SLICE-0086: hull_configuration/cockpit_position/deck_saloon presentation
// text -- every supported locale has complete non-empty labels, complete
// value-label mappings, and every new interpolating function interpolates.
test("every supported locale has complete non-empty SLICE-0086 structure text", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.structureControlsHeading.length > 0, `${locale}.structureControlsHeading`);
    assert.ok(t.hullConfigurationLabel.length > 0, `${locale}.hullConfigurationLabel`);
    assert.ok(t.hullConfigurationAnyOption.length > 0, `${locale}.hullConfigurationAnyOption`);
    assert.ok(t.cockpitPositionLabel.length > 0, `${locale}.cockpitPositionLabel`);
    assert.ok(t.cockpitPositionAnyOption.length > 0, `${locale}.cockpitPositionAnyOption`);
    assert.ok(t.deckSaloonLabel.length > 0, `${locale}.deckSaloonLabel`);
    assert.ok(t.deckSaloonAnyOption.length > 0, `${locale}.deckSaloonAnyOption`);
  }
});

test("every supported locale has complete hull/cockpit/deckSaloon label mappings", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    for (const value of SEARCH_HULL_CONFIGURATION_VALUES) {
      assert.ok(t.hullConfigurationLabels[value].length > 0, `${locale}.hullConfigurationLabels.${value}`);
    }
    for (const value of SEARCH_COCKPIT_POSITION_VALUES) {
      assert.ok(
        t.cockpitPositionLabels[value].length > 0,
        `${locale}.cockpitPositionLabels.${value}`,
      );
    }
    for (const value of SEARCH_DECK_SALOON_VALUES) {
      assert.ok(t.deckSaloonLabels[value].length > 0, `${locale}.deckSaloonLabels.${value}`);
    }
  }
});

test("SLICE-0086 requirement phrases and resolved-evidence text interpolate their arguments", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.requirementPhraseHull("Catamaran").includes("Catamaran"), `${locale}.requirementPhraseHull`);
    assert.ok(
      t.requirementPhraseCockpit("Center cockpit").includes("Center cockpit"),
      `${locale}.requirementPhraseCockpit`,
    );
    assert.ok(
      t.requirementPhraseDeckSaloon("Deck saloon").includes("Deck saloon"),
      `${locale}.requirementPhraseDeckSaloon`,
    );
    assert.ok(t.resolvedHullText("Catamaran").includes("Catamaran"), `${locale}.resolvedHullText`);
    assert.ok(
      t.resolvedCockpitText("Center cockpit").includes("Center cockpit"),
      `${locale}.resolvedCockpitText`,
    );
    assert.ok(
      t.resolvedDeckSaloonText("Deck saloon").includes("Deck saloon"),
      `${locale}.resolvedDeckSaloonText`,
    );
  }
});

// SLICE-0087: beam (min/max) + hull_material presentation text -- every
// supported locale has complete non-empty labels, complete value-label
// mappings, and every new interpolating function interpolates.
test("every supported locale has complete non-empty SLICE-0087 beam/hull-material text", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.beamMinLabel.length > 0, `${locale}.beamMinLabel`);
    assert.ok(t.beamMaxLabel.length > 0, `${locale}.beamMaxLabel`);
    assert.ok(t.beamMinPlaceholder.length > 0, `${locale}.beamMinPlaceholder`);
    assert.ok(t.beamMaxPlaceholder.length > 0, `${locale}.beamMaxPlaceholder`);
    assert.ok(t.hullMaterialLabel.length > 0, `${locale}.hullMaterialLabel`);
    assert.ok(t.hullMaterialAnyOption.length > 0, `${locale}.hullMaterialAnyOption`);
  }
});

test("every supported locale has a complete hullMaterialLabels mapping", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    for (const value of SEARCH_HULL_MATERIAL_VALUES) {
      assert.ok(t.hullMaterialLabels[value].length > 0, `${locale}.hullMaterialLabels.${value}`);
    }
  }
});

test("SLICE-0087 beam/hull-material requirement phrases and resolved-evidence text interpolate their arguments", () => {
  for (const locale of SUPPORTED_LOCALES) {
    const t = searchText[locale];
    assert.ok(t.requirementPhraseBeamMin("3.2").includes("3.2"), `${locale}.requirementPhraseBeamMin`);
    assert.ok(t.requirementPhraseBeamMax("4.4").includes("4.4"), `${locale}.requirementPhraseBeamMax`);
    assert.ok(
      t.requirementPhraseBeamRange("3.2", "4.4").includes("3.2") &&
        t.requirementPhraseBeamRange("3.2", "4.4").includes("4.4"),
      `${locale}.requirementPhraseBeamRange`,
    );
    assert.ok(
      t.requirementPhraseHullMaterial("Wood").includes("Wood"),
      `${locale}.requirementPhraseHullMaterial`,
    );
    assert.ok(t.resolvedBeamText("3.80").includes("3.80"), `${locale}.resolvedBeamText`);
    assert.ok(
      t.resolvedHullMaterialText("Wood").includes("Wood"),
      `${locale}.resolvedHullMaterialText`,
    );
  }
});
