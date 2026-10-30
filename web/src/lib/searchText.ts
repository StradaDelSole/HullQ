// SLICE-0051: localized presentation text for the bounded draft_max Search
// surface (item K — technical parameter names, ids, Decimal meaning,
// provenance and Search semantics stay language-neutral; only this prose is
// translated). Covers Required Behavior §I in full for every locale: what
// requirement was applied, why a confirmed boat qualifies, what concrete
// draft HullQ used, that the value is broker-declared unless separately
// verified, whether evidence is missing/conflicting, why insufficient
// evidence is not called a match, and what action is available next.
//
// SLICE-0056: extends the same coverage to the accepted `keel_configuration`
// criterion, alone or combined with `draft_max`. `keelConfigurationValues`
// (the six accepted technical tokens, `web/src/lib/searchApi.ts`'s
// `SEARCH_KEEL_CONFIGURATION_VALUES`) stay language-neutral; only their
// display labels below are translated.

export type SupportedLocale = "en" | "de" | "fr" | "pt" | "es";

export const SUPPORTED_LOCALES: readonly SupportedLocale[] = ["en", "de", "fr", "pt", "es"];

export interface SearchText {
  title: string;
  // SLICE-0086: first-level hull form / cockpit position / deck saloon
  // structure controls, rendered before the existing numeric/detail
  // controls (Search entry hierarchy, not a second results API).
  structureControlsHeading: string;
  hullConfigurationLabel: string;
  hullConfigurationAnyOption: string;
  /** Localized display label for each accepted technical hull-form value. */
  hullConfigurationLabels: {
    MONOHULL: string;
    CATAMARAN: string;
    TRIMARAN: string;
  };
  cockpitPositionLabel: string;
  cockpitPositionAnyOption: string;
  /** Localized display label for each accepted technical cockpit-position value. */
  cockpitPositionLabels: {
    AFT: string;
    CENTER: string;
    FORWARD: string;
    MULTIPLE: string;
  };
  deckSaloonLabel: string;
  deckSaloonAnyOption: string;
  /** Localized display label for each accepted technical deck-saloon value. */
  deckSaloonLabels: {
    DECK_SALOON: string;
    PILOTHOUSE: string;
  };
  requirementPhraseHull: (hullLabel: string) => string;
  requirementPhraseCockpit: (cockpitLabel: string) => string;
  requirementPhraseDeckSaloon: (deckSaloonLabel: string) => string;
  resolvedHullText: (hullLabel: string) => string;
  resolvedCockpitText: (cockpitLabel: string) => string;
  resolvedDeckSaloonText: (deckSaloonLabel: string) => string;
  // PR #349 independent-review Finding D: design/configuration evidence
  // shown distinct from this offer's own concrete claim evidence
  // (`docs/PRODUCT_UX_PRINCIPLES.md` §15 minimum 5: "design truth separated
  // from physical-offer truth"). `designEvidenceConfigurationLabel` prefixes
  // the (language-neutral) configuration/variant identity string.
  designEvidenceHeading: string;
  designEvidenceConfigurationLabel: string;
  truthTrueLabel: string;
  truthFalseLabel: string;
  truthUnknownLabel: string;
  draftMaxLabel: string;
  draftMaxPlaceholder: string;
  keelConfigurationLabel: string;
  keelConfigurationAnyOption: string;
  /** Localized display label for each accepted technical keel value. */
  keelConfigurationLabels: {
    FIN: string;
    FIN_WITH_BULB: string;
    WING: string;
    CENTERBOARD: string;
    LIFTING_KEEL: string;
    TWIN_KEEL: string;
  };
  // SLICE-0085: LOA (length overall) min/max filter.
  loaMinLabel: string;
  loaMaxLabel: string;
  loaMinPlaceholder: string;
  loaMaxPlaceholder: string;
  // SLICE-0085: rudder/skeg configuration filter.
  rudderConfigurationLabel: string;
  rudderConfigurationAnyOption: string;
  /** Localized display label for each accepted technical rudder value. */
  rudderConfigurationLabels: {
    SKEG_HUNG: string;
    TRANSOM_HUNG: string;
    SPADE: string;
    TWIN: string;
  };
  // SLICE-0087: overall beam min/max filter.
  beamMinLabel: string;
  beamMaxLabel: string;
  beamMinPlaceholder: string;
  beamMaxPlaceholder: string;
  // SLICE-0087: hull construction material filter.
  hullMaterialLabel: string;
  hullMaterialAnyOption: string;
  /** Localized display label for each accepted technical hull-material value. */
  hullMaterialLabels: {
    GRP_FIBERGLASS: string;
    STEEL: string;
    ALUMINUM: string;
    WOOD: string;
  };
  requirementPhraseBeamMin: (beamMin: string) => string;
  requirementPhraseBeamMax: (beamMax: string) => string;
  requirementPhraseBeamRange: (beamMin: string, beamMax: string) => string;
  requirementPhraseHullMaterial: (hullMaterialLabel: string) => string;
  resolvedBeamText: (resolvedBeamM: string) => string;
  resolvedHullMaterialText: (hullMaterialLabel: string) => string;
  // SLICE-0085: per-criterion requirement-summary phrase fragments, combined
  // generically (joined with `requirementSummaryListConjunction`) by
  // `requirementSummaryGeneric` whenever any of loa_min/loa_max/
  // rudder_configuration is active. `requirementSummary`/
  // `requirementSummaryKeelOnly`/`requirementSummaryMixed` stay byte-for-byte
  // unchanged and are used only for the three originally accepted shapes
  // (draft-only, keel-only, draft+keel) -- Required Behavior non-regression.
  requirementPhraseDraftMax: (draftMax: string) => string;
  requirementPhraseKeel: (keelLabel: string) => string;
  requirementPhraseLoaMin: (loaMin: string) => string;
  requirementPhraseLoaMax: (loaMax: string) => string;
  requirementPhraseLoaRange: (loaMin: string, loaMax: string) => string;
  requirementPhraseRudder: (rudderLabel: string) => string;
  requirementSummaryListConjunction: string;
  requirementSummaryGeneric: (phrases: string) => string;
  resolvedLoaText: (resolvedLoaM: string) => string;
  resolvedRudderText: (rudderLabel: string) => string;
  submit: string;
  formInstructions: string;
  invalidTitle: string;
  invalidFallback: string;
  startOver: string;
  serviceUnavailableTitle: string;
  serviceUnavailableMessage: string;
  requirementSummary: (draftMax: string) => string;
  /** SLICE-0056 keel-only active requirement (Required Behavior §C). */
  requirementSummaryKeelOnly: (keelLabel: string) => string;
  /** SLICE-0056 draft+keel active requirement. */
  requirementSummaryMixed: (draftMax: string, keelLabel: string) => string;
  confirmedHeading: string;
  noConfirmedMatches: string;
  /**
   * SLICE-0056: the same "no confirmed matches" state for a keel-only/mixed
   * requirement -- `noConfirmedMatches` itself is left verbatim (Required
   * Behavior §D/AC4: draft-only rendering stays byte-for-byte unchanged)
   * since its wording specifically names "draft".
   */
  noConfirmedMatchesGeneric: string;
  /**
   * SLICE-0096 independent review Finding D: shown INSTEAD of
   * `noConfirmedMatches` whenever the current page is `PARTIAL` -- unlike
   * `noConfirmedMatches`, this never claims a final/exhaustive absence,
   * since unchecked candidates remain (contract: "none among candidates
   * evaluated so far", never "no matching boats").
   */
  noConfirmedMatchesPartial: string;
  /** SLICE-0096 Finding D: the `noConfirmedMatchesGeneric` PARTIAL counterpart. */
  noConfirmedMatchesGenericPartial: string;
  resolvedDraftText: (resolvedDraftM: string) => string;
  /** SLICE-0056 concrete keel evidence on a confirmed keel/mixed match. */
  resolvedKeelText: (keelLabel: string) => string;
  insufficientDataText: (count: number) => string;
  /**
   * SLICE-0056: category-level insufficient-data explanation for a keel/mixed
   * requirement (Required Behavior §E) — never names a specific listing's
   * missing field, mirroring `insufficientDataText`'s draft-only wording.
   */
  insufficientDataTextGeneric: (count: number) => string;
  /**
   * SLICE-0096: shown whenever the current bounded result page is
   * `PARTIAL` -- truthfully distinct from "no matching boats": unchecked
   * candidates remain, including the possibility of a zero-match page
   * (contract §1: "the UI MUST say the search is incomplete and allow
   * continuation. It must NEVER present that as 'no matching boats'").
   */
  partialResultsNote: string;
  /** Label for the continuation control show only while the page is PARTIAL. */
  showMoreResultsLabel: string;
  viewListing: string;
  /** SLICE-0052: badge/label text distinguishing CONFIRMED from DUE_FOR_CONFIRMATION. */
  freshnessConfirmedLabel: string;
  freshnessDueLabel: string;
  /** MUST NOT word a DUE match as if it were simply "confirmed" (contract §H). */
  freshnessDueNote: string;

  // SLICE-0092: design-UNRESOLVED publisher-claim-only matches, rendered as
  // an entirely separate results section (contract §D: public DTO/SSR must
  // convey "publisher-stated, not independently design verified" -- never
  // implying DESIGN_CONFIRMED/verified provenance).
  publisherClaimHeading: (count: number) => string;
  publisherClaimDisclaimer: string;
  noPublisherClaimMatches: string;
  /**
   * Amendment review Finding A: shown INSTEAD of `noConfirmedMatches`/
   * `noConfirmedMatchesGeneric` whenever there are zero design-confirmed
   * matches but one or more publisher-claim-only matches are shown below
   * -- the plain "no confirmed matches" wording would otherwise read as a
   * totally empty result even though matches are visible on the same
   * page.
   */
  noDesignConfirmedMatchesButPublisherClaimsExist: (publisherClaimCount: number) => string;
  /**
   * SLICE-0096 Finding D: the `noDesignConfirmedMatchesButPublisherClaimsExist`
   * PARTIAL counterpart -- never claims the design-confirmed absence is final.
   */
  noDesignConfirmedMatchesButPublisherClaimsExistPartial: (publisherClaimCount: number) => string;

  // SLICE-0057: buyer-requirement-sensitivity text. Factual and
  // decision-neutral throughout (contract §12/§19) -- never "recommended",
  // "better", "worse", "optimal", "should" or "relax this".
  /** Shown alongside each per-active-criterion sensitivity form on the Search page. */
  sensitivityFormNote: string;
  /**
   * Review amendment Finding A (SLICE-0085): shown instead of the
   * sensitivity forms whenever a length-overall or rudder-configuration
   * filter is active alongside draft_max/keel_configuration -- truthful,
   * decision-neutral, never implying the feature is temporarily broken
   * (contract §12/§19 tone).
   */
  sensitivityUnavailableWithNewCriteria: string;
  sensitivityDraftSubmitLabel: string;
  sensitivityKeelSubmitLabel: string;
  sensitivityAlternativeDraftLabel: string;
  sensitivityAlternativeKeelLabel: string;
  sensitivityPageTitle: string;
  sensitivityCurrentHeading: string;
  sensitivityAlternativeHeading: string;
  sensitivityCurrentConfirmedLabel: (count: number) => string;
  sensitivityAlternativeConfirmedLabel: (count: number) => string;
  sensitivityNewlyConfirmedLabel: (count: number) => string;
  sensitivityNoLongerConfirmedLabel: (count: number) => string;
  /**
   * Amendment review Finding A: the entirely separate, truth-source-labeled
   * design-unresolved publisher-claim-only delta -- never merged into the
   * design-confirmed counts above. Rendered only when at least one of the
   * four underlying counts is non-zero (never an empty, confusing extra
   * section).
   */
  sensitivityCurrentPublisherClaimLabel: (count: number) => string;
  sensitivityAlternativePublisherClaimLabel: (count: number) => string;
  sensitivityNewlyPublisherClaimLabel: (count: number) => string;
  sensitivityNoLongerPublisherClaimLabel: (count: number) => string;
  sensitivityCurrentInsufficientLabel: (count: number) => string;
  sensitivityAlternativeInsufficientLabel: (count: number) => string;
  sensitivityViewAlternativeSearch: string;
  sensitivityInvalidTitle: string;
  sensitivityInvalidFallback: string;
  sensitivityServiceUnavailableTitle: string;
  sensitivityServiceUnavailableMessage: string;
  /** Shown for a direct GET to the POST-only sensitivity page (contract §13). */
  sensitivityMethodNotAllowedTitle: string;
  sensitivityMethodNotAllowedMessage: string;
}

export const searchText: Record<SupportedLocale, SearchText> = {
  en: {
    title: "Search: maximum draft",
    structureControlsHeading: "What kind of sailing vessel structure interests you?",
    hullConfigurationLabel: "Hull form",
    hullConfigurationAnyOption: "Any hull form",
    hullConfigurationLabels: {
      MONOHULL: "Monohull",
      CATAMARAN: "Catamaran",
      TRIMARAN: "Trimaran",
    },
    cockpitPositionLabel: "Cockpit position",
    cockpitPositionAnyOption: "Any cockpit position",
    cockpitPositionLabels: {
      AFT: "Aft cockpit",
      CENTER: "Center cockpit",
      FORWARD: "Forward cockpit",
      MULTIPLE: "Multiple cockpits",
    },
    deckSaloonLabel: "Deck saloon / pilothouse",
    deckSaloonAnyOption: "Any deck saloon / pilothouse",
    deckSaloonLabels: {
      DECK_SALOON: "Deck saloon",
      PILOTHOUSE: "Pilothouse",
    },
    requirementPhraseHull: (hullLabel) => `a ${hullLabel} hull`,
    requirementPhraseCockpit: (cockpitLabel) => `a ${cockpitLabel}`,
    requirementPhraseDeckSaloon: (deckSaloonLabel) => `a ${deckSaloonLabel}`,
    resolvedHullText: (hullLabel) =>
      `broker-declared hull form: ${hullLabel} (not independently verified)`,
    resolvedCockpitText: (cockpitLabel) =>
      `broker-declared cockpit position: ${cockpitLabel} (not independently verified)`,
    resolvedDeckSaloonText: (deckSaloonLabel) =>
      `broker-declared deck saloon/pilothouse: ${deckSaloonLabel} (not independently verified)`,
    designEvidenceHeading: "Design/configuration specification (separate from this boat's own claim)",
    designEvidenceConfigurationLabel: "Configuration",
    truthTrueLabel: "confirmed",
    truthFalseLabel: "not met",
    truthUnknownLabel: "unknown",
    draftMaxLabel: "Maximum draft (metres)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Keel configuration",
    keelConfigurationAnyOption: "Any keel configuration",
    keelConfigurationLabels: {
      FIN: "Fin keel",
      FIN_WITH_BULB: "Fin keel with bulb",
      WING: "Wing keel",
      CENTERBOARD: "Centerboard keel",
      LIFTING_KEEL: "Lifting keel",
      TWIN_KEEL: "Twin keel",
    },
    loaMinLabel: "Minimum length overall (metres)",
    loaMaxLabel: "Maximum length overall (metres)",
    loaMinPlaceholder: "10",
    loaMaxPlaceholder: "15",
    rudderConfigurationLabel: "Rudder configuration",
    rudderConfigurationAnyOption: "Any rudder configuration",
    rudderConfigurationLabels: {
      SKEG_HUNG: "Skeg-hung rudder",
      TRANSOM_HUNG: "Transom-hung rudder",
      SPADE: "Spade rudder",
      TWIN: "Twin rudders",
    },
    beamMinLabel: "Minimum overall beam (metres)",
    beamMaxLabel: "Maximum overall beam (metres)",
    beamMinPlaceholder: "3.2",
    beamMaxPlaceholder: "4.4",
    hullMaterialLabel: "Hull construction material",
    hullMaterialAnyOption: "Any hull material",
    hullMaterialLabels: {
      GRP_FIBERGLASS: "GRP / fiberglass",
      STEEL: "Steel",
      ALUMINUM: "Aluminum",
      WOOD: "Wood",
    },
    requirementPhraseDraftMax: (draftMax) => `a draft of ${draftMax} m or less`,
    requirementPhraseKeel: (keelLabel) => `a ${keelLabel}`,
    requirementPhraseLoaMin: (loaMin) => `a length overall of at least ${loaMin} m`,
    requirementPhraseLoaMax: (loaMax) => `a length overall of ${loaMax} m or less`,
    requirementPhraseLoaRange: (loaMin, loaMax) =>
      `a length overall between ${loaMin} m and ${loaMax} m`,
    requirementPhraseRudder: (rudderLabel) => `a ${rudderLabel}`,
    requirementPhraseBeamMin: (beamMin) => `an overall beam of at least ${beamMin} m`,
    requirementPhraseBeamMax: (beamMax) => `an overall beam of ${beamMax} m or less`,
    requirementPhraseBeamRange: (beamMin, beamMax) =>
      `an overall beam between ${beamMin} m and ${beamMax} m`,
    requirementPhraseHullMaterial: (hullMaterialLabel) => `a ${hullMaterialLabel} hull`,
    requirementSummaryListConjunction: "and",
    requirementSummaryGeneric: (phrases) => `Showing boats confirmed to have ${phrases}.`,
    resolvedLoaText: (resolvedLoaM) =>
      `broker-declared length overall: ${resolvedLoaM} m (not independently verified)`,
    resolvedRudderText: (rudderLabel) =>
      `broker-declared rudder configuration: ${rudderLabel} (not independently verified)`,
    resolvedBeamText: (resolvedBeamM) =>
      `broker-declared overall beam: ${resolvedBeamM} m (not independently verified)`,
    resolvedHullMaterialText: (hullMaterialLabel) =>
      `broker-declared hull material: ${hullMaterialLabel} (not independently verified)`,
    submit: "Search",
    formInstructions:
      "Start with the structure that interests you (hull form, cockpit position, deck saloon), then optionally enter the deepest draft your boat can be, in metres, and/or choose a keel configuration. HullQ only shows boats a broker has confirmed meet these requirements.",
    invalidTitle: "This search link isn't valid",
    invalidFallback:
      "Enter a maximum draft as a plain decimal number of metres (for example 1.6) and/or choose a supported keel configuration.",
    startOver: "Start a new search",
    serviceUnavailableTitle: "Search is temporarily unavailable",
    serviceUnavailableMessage:
      "We couldn't complete this search right now. Please try again in a moment.",
    requirementSummary: (draftMax) => `Showing boats confirmed to have a draft of ${draftMax} m or less.`,
    requirementSummaryKeelOnly: (keelLabel) => `Showing boats confirmed to have a ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Showing boats confirmed to have a draft of ${draftMax} m or less and a ${keelLabel}.`,
    confirmedHeading: "Confirmed matches",
    noConfirmedMatches:
      "No listing currently has broker-confirmed evidence that its draft meets this requirement.",
    noConfirmedMatchesGeneric:
      "No listing currently has broker-confirmed evidence that it meets this requirement.",
    noConfirmedMatchesPartial:
      "No listing among those checked so far has broker-confirmed evidence that its draft meets this requirement. This is not the full result.",
    noConfirmedMatchesGenericPartial:
      "No listing among those checked so far has broker-confirmed evidence that it meets this requirement. This is not the full result.",
    resolvedDraftText: (resolvedDraftM) =>
      `broker-declared draft: ${resolvedDraftM} m (not independently verified)`,
    resolvedKeelText: (keelLabel) =>
      `broker-declared keel configuration: ${keelLabel} (not independently verified)`,
    insufficientDataText: (count) =>
      `${count} additional listing(s) could satisfy this requirement but are not shown as a match: the broker's draft is missing, unknown, or conflicts with another organization's current statement.`,
    insufficientDataTextGeneric: (count) =>
      `${count} additional listing(s) could satisfy this requirement but are not shown as a match: the broker's evidence is missing, unknown, or conflicts with another organization's current statement.`,
    partialResultsNote:
      "This search is not yet complete. More listings may still be checked -- this is not the full result.",
    showMoreResultsLabel: "Show more results",
    viewListing: "View listing",
    freshnessConfirmedLabel: "Confirmed current",
    freshnessDueLabel: "Reconfirmation due",
    freshnessDueNote:
      "The broker has not reconfirmed this listing recently; it will be hidden soon unless reconfirmed.",
    publisherClaimHeading: (count) =>
      `Additional matches based on the broker's own statement (${count})`,
    publisherClaimDisclaimer:
      "These listings are not linked to a known design. They are shown because the broker's own current statement meets this requirement -- not because HullQ has independently verified the design.",
    noPublisherClaimMatches:
      "No additional broker-stated listing currently meets this requirement.",
    noDesignConfirmedMatchesButPublisherClaimsExist: (publisherClaimCount) =>
      `No design-confirmed matches. ${publisherClaimCount} additional match(es) based on the broker's own statement are shown below.`,
    noDesignConfirmedMatchesButPublisherClaimsExistPartial: (publisherClaimCount) =>
      `No design-confirmed matches among those checked so far. ${publisherClaimCount} additional match(es) based on the broker's own statement are shown below. This is not the full result.`,
    sensitivityFormNote:
      "See how many confirmed matches change if you try a different value for one requirement. This does not change your current search.",
    sensitivityUnavailableWithNewCriteria:
      "Requirement sensitivity isn't available while a length overall, rudder configuration, hull form, cockpit position, deck saloon, overall beam or hull material filter is also active.",
    sensitivityDraftSubmitLabel: "See the effect of a different maximum draft",
    sensitivityKeelSubmitLabel: "See the effect of a different keel configuration",
    sensitivityAlternativeDraftLabel: "Alternative maximum draft (metres)",
    sensitivityAlternativeKeelLabel: "Alternative keel configuration",
    sensitivityPageTitle: "Requirement sensitivity",
    sensitivityCurrentHeading: "Current requirement",
    sensitivityAlternativeHeading: "Alternative requirement",
    sensitivityCurrentConfirmedLabel: (count) => `Currently design-confirmed matches: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Design-confirmed matches with the alternative: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) =>
      `${count} newly design-confirmed with the alternative`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} no longer design-confirmed with the alternative`,
    sensitivityCurrentPublisherClaimLabel: (count) =>
      `Currently broker-stated (not design-verified) matches: ${count}`,
    sensitivityAlternativePublisherClaimLabel: (count) =>
      `Broker-stated (not design-verified) matches with the alternative: ${count}`,
    sensitivityNewlyPublisherClaimLabel: (count) =>
      `${count} newly broker-stated with the alternative`,
    sensitivityNoLongerPublisherClaimLabel: (count) =>
      `${count} no longer broker-stated with the alternative`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} additional listing(s) have insufficient evidence under the current requirement`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} additional listing(s) have insufficient evidence under the alternative requirement`,
    sensitivityViewAlternativeSearch: "View this search",
    sensitivityInvalidTitle: "This sensitivity request isn't valid",
    sensitivityInvalidFallback:
      "Choose one currently active requirement and supply one replacement value for it.",
    sensitivityServiceUnavailableTitle: "Sensitivity is temporarily unavailable",
    sensitivityServiceUnavailableMessage:
      "We couldn't complete this comparison right now. Please try again in a moment.",
    sensitivityMethodNotAllowedTitle: "Start from a search",
    sensitivityMethodNotAllowedMessage:
      "This page only shows a result after you submit a requirement change from the search page.",
  },
  de: {
    title: "Suche: maximaler Tiefgang",
    structureControlsHeading: "Welche Art von Segelbootstruktur interessiert Sie?",
    hullConfigurationLabel: "Rumpfform",
    hullConfigurationAnyOption: "Beliebige Rumpfform",
    hullConfigurationLabels: {
      MONOHULL: "Einrumpfboot",
      CATAMARAN: "Katamaran",
      TRIMARAN: "Trimaran",
    },
    cockpitPositionLabel: "Cockpit-Position",
    cockpitPositionAnyOption: "Beliebige Cockpit-Position",
    cockpitPositionLabels: {
      AFT: "Hecknahes Cockpit",
      CENTER: "Mittiges Cockpit",
      FORWARD: "Vorderes Cockpit",
      MULTIPLE: "Mehrere Cockpits",
    },
    deckSaloonLabel: "Decksalon / Pilothouse",
    deckSaloonAnyOption: "Beliebiger Decksalon / Pilothouse",
    deckSaloonLabels: {
      DECK_SALOON: "Decksalon",
      PILOTHOUSE: "Pilothouse",
    },
    requirementPhraseHull: (hullLabel) => `einem Rumpf: ${hullLabel}`,
    requirementPhraseCockpit: (cockpitLabel) => `einem ${cockpitLabel}`,
    requirementPhraseDeckSaloon: (deckSaloonLabel) => `einem ${deckSaloonLabel}`,
    resolvedHullText: (hullLabel) =>
      `vom Makler angegebene Rumpfform: ${hullLabel} (nicht unabhängig verifiziert)`,
    resolvedCockpitText: (cockpitLabel) =>
      `vom Makler angegebene Cockpit-Position: ${cockpitLabel} (nicht unabhängig verifiziert)`,
    resolvedDeckSaloonText: (deckSaloonLabel) =>
      `vom Makler angegebener Decksalon/Pilothouse: ${deckSaloonLabel} (nicht unabhängig verifiziert)`,
    designEvidenceHeading: "Design-/Konfigurationsspezifikation (getrennt von der Angabe des Maklers)",
    designEvidenceConfigurationLabel: "Konfiguration",
    truthTrueLabel: "bestätigt",
    truthFalseLabel: "nicht erfüllt",
    truthUnknownLabel: "unbekannt",
    draftMaxLabel: "Maximaler Tiefgang (Meter)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Kielkonfiguration",
    keelConfigurationAnyOption: "Beliebige Kielkonfiguration",
    keelConfigurationLabels: {
      FIN: "Finnenkiel",
      FIN_WITH_BULB: "Finnenkiel mit Bulbe",
      WING: "Flügelkiel",
      CENTERBOARD: "Schwertkiel",
      LIFTING_KEEL: "Hubkiel",
      TWIN_KEEL: "Doppelkiel",
    },
    loaMinLabel: "Mindestlänge über alles (Meter)",
    loaMaxLabel: "Maximale Länge über alles (Meter)",
    loaMinPlaceholder: "10",
    loaMaxPlaceholder: "15",
    rudderConfigurationLabel: "Ruderkonfiguration",
    rudderConfigurationAnyOption: "Beliebige Ruderkonfiguration",
    rudderConfigurationLabels: {
      SKEG_HUNG: "Skegruder",
      TRANSOM_HUNG: "Spiegelruder (heckhängend)",
      SPADE: "Spatenruder (freistehend)",
      TWIN: "Doppelruder",
    },
    beamMinLabel: "Mindestbreite über alles (Meter)",
    beamMaxLabel: "Maximale Breite über alles (Meter)",
    beamMinPlaceholder: "3.2",
    beamMaxPlaceholder: "4.4",
    hullMaterialLabel: "Rumpfbaumaterial",
    hullMaterialAnyOption: "Beliebiges Rumpfmaterial",
    hullMaterialLabels: {
      GRP_FIBERGLASS: "GFK / Fiberglas",
      STEEL: "Stahl",
      ALUMINUM: "Aluminium",
      WOOD: "Holz",
    },
    requirementPhraseDraftMax: (draftMax) => `einem Tiefgang von ${draftMax} m oder weniger`,
    requirementPhraseKeel: (keelLabel) => `einer Kielkonfiguration: ${keelLabel}`,
    requirementPhraseLoaMin: (loaMin) => `einer Gesamtlänge von mindestens ${loaMin} m`,
    requirementPhraseLoaMax: (loaMax) => `einer Gesamtlänge von ${loaMax} m oder weniger`,
    requirementPhraseLoaRange: (loaMin, loaMax) =>
      `einer Gesamtlänge zwischen ${loaMin} m und ${loaMax} m`,
    requirementPhraseRudder: (rudderLabel) => `einer Ruderkonfiguration: ${rudderLabel}`,
    requirementPhraseBeamMin: (beamMin) => `einer Breite über alles von mindestens ${beamMin} m`,
    requirementPhraseBeamMax: (beamMax) => `einer Breite über alles von ${beamMax} m oder weniger`,
    requirementPhraseBeamRange: (beamMin, beamMax) =>
      `einer Breite über alles zwischen ${beamMin} m und ${beamMax} m`,
    requirementPhraseHullMaterial: (hullMaterialLabel) => `einem Rumpf aus ${hullMaterialLabel}`,
    requirementSummaryListConjunction: "und",
    requirementSummaryGeneric: (phrases) => `Boote mit ${phrases} (bestätigt).`,
    resolvedLoaText: (resolvedLoaM) =>
      `vom Makler angegebene Gesamtlänge: ${resolvedLoaM} m (nicht unabhängig verifiziert)`,
    resolvedRudderText: (rudderLabel) =>
      `vom Makler angegebene Ruderkonfiguration: ${rudderLabel} (nicht unabhängig verifiziert)`,
    resolvedBeamText: (resolvedBeamM) =>
      `vom Makler angegebene Breite über alles: ${resolvedBeamM} m (nicht unabhängig verifiziert)`,
    resolvedHullMaterialText: (hullMaterialLabel) =>
      `vom Makler angegebenes Rumpfmaterial: ${hullMaterialLabel} (nicht unabhängig verifiziert)`,
    submit: "Suchen",
    formInstructions:
      "Beginnen Sie mit der Struktur, die Sie interessiert (Rumpfform, Cockpit-Position, Decksalon), und geben Sie optional den größten zulässigen Tiefgang in Metern an und/oder wählen Sie eine Kielkonfiguration. HullQ zeigt nur Boote, die von einem Makler als diesen Anforderungen entsprechend bestätigt wurden.",
    invalidTitle: "Dieser Suchlink ist ungültig",
    invalidFallback:
      "Geben Sie den maximalen Tiefgang als einfache Dezimalzahl in Metern an (zum Beispiel 1.6) und/oder wählen Sie eine unterstützte Kielkonfiguration.",
    startOver: "Neue Suche beginnen",
    serviceUnavailableTitle: "Die Suche ist vorübergehend nicht verfügbar",
    serviceUnavailableMessage:
      "Diese Suche konnte gerade nicht durchgeführt werden. Bitte versuchen Sie es in Kürze erneut.",
    requirementSummary: (draftMax) => `Boote mit bestätigtem Tiefgang von ${draftMax} m oder weniger.`,
    requirementSummaryKeelOnly: (keelLabel) => `Boote mit bestätigter Kielkonfiguration: ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Boote mit bestätigtem Tiefgang von ${draftMax} m oder weniger und Kielkonfiguration: ${keelLabel}.`,
    confirmedHeading: "Bestätigte Treffer",
    noConfirmedMatches:
      "Für kein Angebot liegt derzeit eine maklerbestätigte Bestätigung vor, dass der Tiefgang diese Anforderung erfüllt.",
    noConfirmedMatchesGeneric:
      "Für kein Angebot liegt derzeit eine maklerbestätigte Bestätigung vor, dass es diese Anforderung erfüllt.",
    noConfirmedMatchesPartial:
      "Unter den bisher geprüften Angeboten erfüllt keines nachweislich diese Tiefgangsanforderung. Dies ist nicht das vollständige Ergebnis.",
    noConfirmedMatchesGenericPartial:
      "Unter den bisher geprüften Angeboten erfüllt keines nachweislich diese Anforderung. Dies ist nicht das vollständige Ergebnis.",
    resolvedDraftText: (resolvedDraftM) =>
      `vom Makler angegebener Tiefgang: ${resolvedDraftM} m (nicht unabhängig verifiziert)`,
    resolvedKeelText: (keelLabel) =>
      `vom Makler angegebene Kielkonfiguration: ${keelLabel} (nicht unabhängig verifiziert)`,
    insufficientDataText: (count) =>
      `${count} weitere(s) Angebot(e) könnten diese Anforderung erfüllen, werden aber nicht als Treffer angezeigt: Der Tiefgang fehlt, ist unbekannt oder widerspricht der aktuellen Angabe einer anderen Organisation.`,
    insufficientDataTextGeneric: (count) =>
      `${count} weitere(s) Angebot(e) könnten diese Anforderung erfüllen, werden aber nicht als Treffer angezeigt: Die Angaben des Maklers fehlen, sind unbekannt oder widersprechen der aktuellen Angabe einer anderen Organisation.`,
    partialResultsNote:
      "Diese Suche ist noch nicht abgeschlossen. Es können noch weitere Angebote geprüft werden -- dies ist nicht das vollständige Ergebnis.",
    showMoreResultsLabel: "Weitere Ergebnisse anzeigen",
    viewListing: "Angebot ansehen",
    freshnessConfirmedLabel: "Aktuell bestätigt",
    freshnessDueLabel: "Bestätigung ausstehend",
    freshnessDueNote:
      "Der Makler hat dieses Angebot kürzlich nicht erneut bestätigt; es wird bald ausgeblendet, sofern es nicht erneut bestätigt wird.",
    publisherClaimHeading: (count) => `Weitere Treffer laut Anbieterangabe (${count})`,
    publisherClaimDisclaimer:
      "Diese Angebote sind keinem bekannten Konstruktionsdatensatz zugeordnet. Sie werden angezeigt, weil die aktuelle Angabe des Anbieters diese Anforderung erfüllt -- nicht, weil HullQ die Konstruktion unabhängig geprüft hat.",
    noPublisherClaimMatches:
      "Derzeit erfüllt kein zusätzliches, laut Anbieterangabe geführtes Angebot diese Anforderung.",
    noDesignConfirmedMatchesButPublisherClaimsExist: (publisherClaimCount) =>
      `Keine konstruktionsbestätigten Treffer. ${publisherClaimCount} weitere(r) Treffer laut Anbieterangabe werden unten angezeigt.`,
    noDesignConfirmedMatchesButPublisherClaimsExistPartial: (publisherClaimCount) =>
      `Unter den bisher geprüften Angeboten keine konstruktionsbestätigten Treffer. ${publisherClaimCount} weitere(r) Treffer laut Anbieterangabe werden unten angezeigt. Dies ist nicht das vollständige Ergebnis.`,
    sensitivityFormNote:
      "Sehen Sie, wie viele bestätigte Treffer sich ändern, wenn Sie für eine Anforderung einen anderen Wert ausprobieren. Dies ändert Ihre aktuelle Suche nicht.",
    sensitivityUnavailableWithNewCriteria:
      "Die Anforderungssensitivität ist nicht verfügbar, während zusätzlich ein Filter für Gesamtlänge, Ruderkonfiguration, Rumpfform, Cockpit-Position, Decksalon, Breite über alles oder Rumpfmaterial aktiv ist.",
    sensitivityDraftSubmitLabel: "Auswirkung eines anderen maximalen Tiefgangs anzeigen",
    sensitivityKeelSubmitLabel: "Auswirkung einer anderen Kielkonfiguration anzeigen",
    sensitivityAlternativeDraftLabel: "Alternativer maximaler Tiefgang (Meter)",
    sensitivityAlternativeKeelLabel: "Alternative Kielkonfiguration",
    sensitivityPageTitle: "Anforderungssensitivität",
    sensitivityCurrentHeading: "Aktuelle Anforderung",
    sensitivityAlternativeHeading: "Alternative Anforderung",
    sensitivityCurrentConfirmedLabel: (count) =>
      `Aktuell konstruktionsbestätigte Treffer: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Konstruktionsbestätigte Treffer mit der Alternative: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) =>
      `${count} neu konstruktionsbestätigt mit der Alternative`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} nicht mehr konstruktionsbestätigt mit der Alternative`,
    sensitivityCurrentPublisherClaimLabel: (count) =>
      `Aktuell laut Anbieterangabe (nicht konstruktionsgeprüft) Treffer: ${count}`,
    sensitivityAlternativePublisherClaimLabel: (count) =>
      `Treffer laut Anbieterangabe (nicht konstruktionsgeprüft) mit der Alternative: ${count}`,
    sensitivityNewlyPublisherClaimLabel: (count) =>
      `${count} neu laut Anbieterangabe mit der Alternative`,
    sensitivityNoLongerPublisherClaimLabel: (count) =>
      `${count} nicht mehr laut Anbieterangabe mit der Alternative`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} weitere(s) Angebot(e) haben unter der aktuellen Anforderung unzureichende Nachweise`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} weitere(s) Angebot(e) haben unter der alternativen Anforderung unzureichende Nachweise`,
    sensitivityViewAlternativeSearch: "Diese Suche ansehen",
    sensitivityInvalidTitle: "Diese Sensitivitätsanfrage ist ungültig",
    sensitivityInvalidFallback:
      "Wählen Sie eine derzeit aktive Anforderung und geben Sie dafür einen Ersatzwert an.",
    sensitivityServiceUnavailableTitle: "Die Sensitivitätsanalyse ist vorübergehend nicht verfügbar",
    sensitivityServiceUnavailableMessage:
      "Dieser Vergleich konnte gerade nicht durchgeführt werden. Bitte versuchen Sie es in Kürze erneut.",
    sensitivityMethodNotAllowedTitle: "Von einer Suche aus starten",
    sensitivityMethodNotAllowedMessage:
      "Diese Seite zeigt ein Ergebnis erst, nachdem Sie über die Suchseite eine Anforderungsänderung gesendet haben.",
  },
  fr: {
    title: "Recherche : tirant d'eau maximal",
    structureControlsHeading: "Quel type de structure de voilier vous intéresse ?",
    hullConfigurationLabel: "Forme de carène",
    hullConfigurationAnyOption: "Toute forme de carène",
    hullConfigurationLabels: {
      MONOHULL: "Monocoque",
      CATAMARAN: "Catamaran",
      TRIMARAN: "Trimaran",
    },
    cockpitPositionLabel: "Position du cockpit",
    cockpitPositionAnyOption: "Toute position de cockpit",
    cockpitPositionLabels: {
      AFT: "Cockpit arrière",
      CENTER: "Cockpit central",
      FORWARD: "Cockpit avant",
      MULTIPLE: "Cockpits multiples",
    },
    deckSaloonLabel: "Salon de pont / timonerie",
    deckSaloonAnyOption: "Tout salon de pont / timonerie",
    deckSaloonLabels: {
      DECK_SALOON: "Salon de pont",
      PILOTHOUSE: "Timonerie",
    },
    requirementPhraseHull: (hullLabel) => `une carène : ${hullLabel}`,
    requirementPhraseCockpit: (cockpitLabel) => `un ${cockpitLabel}`,
    requirementPhraseDeckSaloon: (deckSaloonLabel) => `un ${deckSaloonLabel}`,
    resolvedHullText: (hullLabel) =>
      `forme de carène déclarée par le courtier : ${hullLabel} (non vérifiée de manière indépendante)`,
    resolvedCockpitText: (cockpitLabel) =>
      `position de cockpit déclarée par le courtier : ${cockpitLabel} (non vérifiée de manière indépendante)`,
    resolvedDeckSaloonText: (deckSaloonLabel) =>
      `salon de pont/timonerie déclaré par le courtier : ${deckSaloonLabel} (non vérifié de manière indépendante)`,
    designEvidenceHeading: "Spécification du design/de la configuration (distincte de la déclaration du courtier)",
    designEvidenceConfigurationLabel: "Configuration",
    truthTrueLabel: "confirmé",
    truthFalseLabel: "non satisfait",
    truthUnknownLabel: "inconnu",
    draftMaxLabel: "Tirant d'eau maximal (mètres)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Configuration de quille",
    keelConfigurationAnyOption: "Toute configuration de quille",
    keelConfigurationLabels: {
      FIN: "Quille fine",
      FIN_WITH_BULB: "Quille fine à bulbe",
      WING: "Quille à ailettes",
      CENTERBOARD: "Dérive",
      LIFTING_KEEL: "Quille relevable",
      TWIN_KEEL: "Quille double",
    },
    loaMinLabel: "Longueur hors tout minimale (mètres)",
    loaMaxLabel: "Longueur hors tout maximale (mètres)",
    loaMinPlaceholder: "10",
    loaMaxPlaceholder: "15",
    rudderConfigurationLabel: "Configuration de safran",
    rudderConfigurationAnyOption: "Toute configuration de safran",
    rudderConfigurationLabels: {
      SKEG_HUNG: "Safran sur aileron (skeg)",
      TRANSOM_HUNG: "Safran de voûte (sur tableau arrière)",
      SPADE: "Safran suspendu (spade)",
      TWIN: "Safrans jumelés",
    },
    beamMinLabel: "Largeur hors tout minimale (mètres)",
    beamMaxLabel: "Largeur hors tout maximale (mètres)",
    beamMinPlaceholder: "3.2",
    beamMaxPlaceholder: "4.4",
    hullMaterialLabel: "Matériau de construction de la coque",
    hullMaterialAnyOption: "Tout matériau de coque",
    hullMaterialLabels: {
      GRP_FIBERGLASS: "PRV / fibre de verre",
      STEEL: "Acier",
      ALUMINUM: "Aluminium",
      WOOD: "Bois",
    },
    requirementPhraseDraftMax: (draftMax) => `un tirant d'eau de ${draftMax} m ou moins`,
    requirementPhraseKeel: (keelLabel) => `une configuration de quille : ${keelLabel}`,
    requirementPhraseLoaMin: (loaMin) => `une longueur hors tout d'au moins ${loaMin} m`,
    requirementPhraseLoaMax: (loaMax) => `une longueur hors tout de ${loaMax} m ou moins`,
    requirementPhraseLoaRange: (loaMin, loaMax) =>
      `une longueur hors tout comprise entre ${loaMin} m et ${loaMax} m`,
    requirementPhraseRudder: (rudderLabel) => `une configuration de safran : ${rudderLabel}`,
    requirementPhraseBeamMin: (beamMin) => `une largeur hors tout d'au moins ${beamMin} m`,
    requirementPhraseBeamMax: (beamMax) => `une largeur hors tout de ${beamMax} m ou moins`,
    requirementPhraseBeamRange: (beamMin, beamMax) =>
      `une largeur hors tout comprise entre ${beamMin} m et ${beamMax} m`,
    requirementPhraseHullMaterial: (hullMaterialLabel) => `une coque en ${hullMaterialLabel}`,
    requirementSummaryListConjunction: "et",
    requirementSummaryGeneric: (phrases) => `Bateaux confirmés avec ${phrases}.`,
    resolvedLoaText: (resolvedLoaM) =>
      `longueur hors tout déclarée par le courtier : ${resolvedLoaM} m (non vérifiée de manière indépendante)`,
    resolvedBeamText: (resolvedBeamM) =>
      `largeur hors tout déclarée par le courtier : ${resolvedBeamM} m (non vérifiée de manière indépendante)`,
    resolvedHullMaterialText: (hullMaterialLabel) =>
      `matériau de coque déclaré par le courtier : ${hullMaterialLabel} (non vérifié de manière indépendante)`,
    resolvedRudderText: (rudderLabel) =>
      `configuration de safran déclarée par le courtier : ${rudderLabel} (non vérifiée de manière indépendante)`,
    submit: "Rechercher",
    formInstructions:
      "Commencez par la structure qui vous intéresse (forme de carène, position du cockpit, salon de pont), puis indiquez éventuellement le tirant d'eau maximal admissible, en mètres, et/ou choisissez une configuration de quille. HullQ n'affiche que les bateaux dont le courtier a confirmé qu'ils respectent ces exigences.",
    invalidTitle: "Ce lien de recherche n'est pas valide",
    invalidFallback:
      "Indiquez le tirant d'eau maximal sous forme de nombre décimal simple en mètres (par exemple 1.6) et/ou choisissez une configuration de quille prise en charge.",
    startOver: "Commencer une nouvelle recherche",
    serviceUnavailableTitle: "La recherche est temporairement indisponible",
    serviceUnavailableMessage:
      "Nous n'avons pas pu effectuer cette recherche pour le moment. Veuillez réessayer dans un instant.",
    requirementSummary: (draftMax) => `Bateaux dont le tirant d'eau confirmé est de ${draftMax} m ou moins.`,
    requirementSummaryKeelOnly: (keelLabel) =>
      `Bateaux avec configuration de quille confirmée : ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Bateaux dont le tirant d'eau confirmé est de ${draftMax} m ou moins, avec configuration de quille : ${keelLabel}.`,
    confirmedHeading: "Résultats confirmés",
    noConfirmedMatches:
      "Aucune annonce ne dispose actuellement d'une confirmation du courtier attestant que son tirant d'eau respecte cette exigence.",
    noConfirmedMatchesGeneric:
      "Aucune annonce ne dispose actuellement d'une confirmation du courtier attestant qu'elle respecte cette exigence.",
    noConfirmedMatchesPartial:
      "Parmi les annonces examinées jusqu'à présent, aucune ne dispose d'une confirmation du courtier attestant que son tirant d'eau respecte cette exigence. Ceci n'est pas le résultat complet.",
    noConfirmedMatchesGenericPartial:
      "Parmi les annonces examinées jusqu'à présent, aucune ne dispose d'une confirmation du courtier attestant qu'elle respecte cette exigence. Ceci n'est pas le résultat complet.",
    resolvedDraftText: (resolvedDraftM) =>
      `tirant d'eau déclaré par le courtier : ${resolvedDraftM} m (non vérifié de manière indépendante)`,
    resolvedKeelText: (keelLabel) =>
      `configuration de quille déclarée par le courtier : ${keelLabel} (non vérifiée de manière indépendante)`,
    insufficientDataText: (count) =>
      `${count} annonce(s) supplémentaire(s) pourraient satisfaire cette exigence mais ne sont pas affichées comme correspondance : le tirant d'eau est manquant, inconnu, ou contredit la déclaration actuelle d'une autre organisation.`,
    insufficientDataTextGeneric: (count) =>
      `${count} annonce(s) supplémentaire(s) pourraient satisfaire cette exigence mais ne sont pas affichées comme correspondance : les informations du courtier sont manquantes, inconnues, ou contredisent la déclaration actuelle d'une autre organisation.`,
    partialResultsNote:
      "Cette recherche n'est pas encore terminée. D'autres annonces peuvent encore être vérifiées -- ceci n'est pas le résultat complet.",
    showMoreResultsLabel: "Afficher plus de résultats",
    viewListing: "Voir l'annonce",
    freshnessConfirmedLabel: "Confirmé à jour",
    freshnessDueLabel: "Reconfirmation attendue",
    freshnessDueNote:
      "Le courtier n'a pas reconfirmé cette annonce récemment ; elle sera bientôt masquée si elle n'est pas reconfirmée.",
    publisherClaimHeading: (count) =>
      `Résultats supplémentaires selon la déclaration du courtier (${count})`,
    publisherClaimDisclaimer:
      "Ces annonces ne sont associées à aucun modèle de conception connu. Elles sont affichées parce que la déclaration actuelle du courtier répond à cette exigence -- et non parce que HullQ a vérifié la conception de façon indépendante.",
    noPublisherClaimMatches:
      "Aucune annonce supplémentaire déclarée par le courtier ne répond actuellement à cette exigence.",
    noDesignConfirmedMatchesButPublisherClaimsExist: (publisherClaimCount) =>
      `Aucun résultat confirmé par la conception. ${publisherClaimCount} résultat(s) supplémentaire(s) selon la déclaration du courtier sont affichés ci-dessous.`,
    noDesignConfirmedMatchesButPublisherClaimsExistPartial: (publisherClaimCount) =>
      `Parmi les annonces examinées jusqu'à présent, aucun résultat confirmé par la conception. ${publisherClaimCount} résultat(s) supplémentaire(s) selon la déclaration du courtier sont affichés ci-dessous. Ceci n'est pas le résultat complet.`,
    sensitivityFormNote:
      "Découvrez combien de résultats confirmés changent si vous essayez une valeur différente pour une exigence. Cela ne modifie pas votre recherche actuelle.",
    sensitivityUnavailableWithNewCriteria:
      "La sensibilité de l'exigence n'est pas disponible lorsqu'un filtre de longueur hors tout, de configuration de safran, de forme de carène, de position de cockpit, de salon de pont, de largeur hors tout ou de matériau de coque est également actif.",
    sensitivityDraftSubmitLabel: "Voir l'effet d'un tirant d'eau maximal différent",
    sensitivityKeelSubmitLabel: "Voir l'effet d'une configuration de quille différente",
    sensitivityAlternativeDraftLabel: "Tirant d'eau maximal alternatif (mètres)",
    sensitivityAlternativeKeelLabel: "Configuration de quille alternative",
    sensitivityPageTitle: "Sensibilité de l'exigence",
    sensitivityCurrentHeading: "Exigence actuelle",
    sensitivityAlternativeHeading: "Exigence alternative",
    sensitivityCurrentConfirmedLabel: (count) =>
      `Résultats actuellement confirmés par la conception : ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Résultats confirmés par la conception avec l'alternative : ${count}`,
    sensitivityNewlyConfirmedLabel: (count) =>
      `${count} nouvellement confirmé(s) par la conception avec l'alternative`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} n'est/ne sont plus confirmé(s) par la conception avec l'alternative`,
    sensitivityCurrentPublisherClaimLabel: (count) =>
      `Résultats actuellement selon la déclaration du courtier (non vérifiés par la conception) : ${count}`,
    sensitivityAlternativePublisherClaimLabel: (count) =>
      `Résultats selon la déclaration du courtier (non vérifiés par la conception) avec l'alternative : ${count}`,
    sensitivityNewlyPublisherClaimLabel: (count) =>
      `${count} nouvellement déclaré(s) par le courtier avec l'alternative`,
    sensitivityNoLongerPublisherClaimLabel: (count) =>
      `${count} n'est/ne sont plus déclaré(s) par le courtier avec l'alternative`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} annonce(s) supplémentaire(s) ont des preuves insuffisantes selon l'exigence actuelle`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} annonce(s) supplémentaire(s) ont des preuves insuffisantes selon l'exigence alternative`,
    sensitivityViewAlternativeSearch: "Voir cette recherche",
    sensitivityInvalidTitle: "Cette demande de sensibilité n'est pas valide",
    sensitivityInvalidFallback:
      "Choisissez une exigence actuellement active et indiquez une valeur de remplacement pour celle-ci.",
    sensitivityServiceUnavailableTitle: "La sensibilité est temporairement indisponible",
    sensitivityServiceUnavailableMessage:
      "Nous n'avons pas pu effectuer cette comparaison pour le moment. Veuillez réessayer dans un instant.",
    sensitivityMethodNotAllowedTitle: "Commencer par une recherche",
    sensitivityMethodNotAllowedMessage:
      "Cette page n'affiche un résultat qu'après l'envoi d'une modification d'exigence depuis la page de recherche.",
  },
  pt: {
    title: "Pesquisa: calado máximo",
    structureControlsHeading: "Que tipo de estrutura de veleiro lhe interessa?",
    hullConfigurationLabel: "Forma do casco",
    hullConfigurationAnyOption: "Qualquer forma de casco",
    hullConfigurationLabels: {
      MONOHULL: "Monocasco",
      CATAMARAN: "Catamarã",
      TRIMARAN: "Trimarã",
    },
    cockpitPositionLabel: "Posição do cockpit",
    cockpitPositionAnyOption: "Qualquer posição de cockpit",
    cockpitPositionLabels: {
      AFT: "Cockpit à popa",
      CENTER: "Cockpit central",
      FORWARD: "Cockpit à proa",
      MULTIPLE: "Múltiplos cockpits",
    },
    deckSaloonLabel: "Salão de convés / casa do leme",
    deckSaloonAnyOption: "Qualquer salão de convés / casa do leme",
    deckSaloonLabels: {
      DECK_SALOON: "Salão de convés",
      PILOTHOUSE: "Casa do leme",
    },
    requirementPhraseHull: (hullLabel) => `um casco: ${hullLabel}`,
    requirementPhraseCockpit: (cockpitLabel) => `um ${cockpitLabel}`,
    requirementPhraseDeckSaloon: (deckSaloonLabel) => `um ${deckSaloonLabel}`,
    resolvedHullText: (hullLabel) =>
      `forma de casco declarada pelo corretor: ${hullLabel} (não verificada de forma independente)`,
    resolvedCockpitText: (cockpitLabel) =>
      `posição de cockpit declarada pelo corretor: ${cockpitLabel} (não verificada de forma independente)`,
    resolvedDeckSaloonText: (deckSaloonLabel) =>
      `salão de convés/casa do leme declarado pelo corretor: ${deckSaloonLabel} (não verificado de forma independente)`,
    designEvidenceHeading: "Especificação do design/configuração (separada da declaração do corretor)",
    designEvidenceConfigurationLabel: "Configuração",
    truthTrueLabel: "confirmado",
    truthFalseLabel: "não cumprido",
    truthUnknownLabel: "desconhecido",
    draftMaxLabel: "Calado máximo (metros)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Configuração da quilha",
    keelConfigurationAnyOption: "Qualquer configuração de quilha",
    keelConfigurationLabels: {
      FIN: "Quilha simples",
      FIN_WITH_BULB: "Quilha com bolbo",
      WING: "Quilha com asas",
      CENTERBOARD: "Orça de deriva",
      LIFTING_KEEL: "Quilha retrátil",
      TWIN_KEEL: "Quilha dupla",
    },
    loaMinLabel: "Comprimento total mínimo (metros)",
    loaMaxLabel: "Comprimento total máximo (metros)",
    loaMinPlaceholder: "10",
    loaMaxPlaceholder: "15",
    rudderConfigurationLabel: "Configuração do leme",
    rudderConfigurationAnyOption: "Qualquer configuração de leme",
    rudderConfigurationLabels: {
      SKEG_HUNG: "Leme em skeg",
      TRANSOM_HUNG: "Leme no espelho (popa)",
      SPADE: "Leme suspenso (spade)",
      TWIN: "Lemes duplos",
    },
    beamMinLabel: "Boca mínima (metros)",
    beamMaxLabel: "Boca máxima (metros)",
    beamMinPlaceholder: "3.2",
    beamMaxPlaceholder: "4.4",
    hullMaterialLabel: "Material de construção do casco",
    hullMaterialAnyOption: "Qualquer material de casco",
    hullMaterialLabels: {
      GRP_FIBERGLASS: "PRFV / fibra de vidro",
      STEEL: "Aço",
      ALUMINUM: "Alumínio",
      WOOD: "Madeira",
    },
    requirementPhraseDraftMax: (draftMax) => `um calado de ${draftMax} m ou menos`,
    requirementPhraseKeel: (keelLabel) => `uma configuração de quilha: ${keelLabel}`,
    requirementPhraseLoaMin: (loaMin) => `um comprimento total de pelo menos ${loaMin} m`,
    requirementPhraseLoaMax: (loaMax) => `um comprimento total de ${loaMax} m ou menos`,
    requirementPhraseLoaRange: (loaMin, loaMax) =>
      `um comprimento total entre ${loaMin} m e ${loaMax} m`,
    requirementPhraseRudder: (rudderLabel) => `uma configuração de leme: ${rudderLabel}`,
    requirementPhraseBeamMin: (beamMin) => `uma boca de pelo menos ${beamMin} m`,
    requirementPhraseBeamMax: (beamMax) => `uma boca de ${beamMax} m ou menos`,
    requirementPhraseBeamRange: (beamMin, beamMax) => `uma boca entre ${beamMin} m e ${beamMax} m`,
    requirementPhraseHullMaterial: (hullMaterialLabel) => `um casco de ${hullMaterialLabel}`,
    requirementSummaryListConjunction: "e",
    requirementSummaryGeneric: (phrases) => `A mostrar barcos confirmados com ${phrases}.`,
    resolvedLoaText: (resolvedLoaM) =>
      `comprimento total declarado pelo corretor: ${resolvedLoaM} m (não verificado de forma independente)`,
    resolvedBeamText: (resolvedBeamM) =>
      `boca declarada pelo corretor: ${resolvedBeamM} m (não verificada de forma independente)`,
    resolvedHullMaterialText: (hullMaterialLabel) =>
      `material de casco declarado pelo corretor: ${hullMaterialLabel} (não verificado de forma independente)`,
    resolvedRudderText: (rudderLabel) =>
      `configuração de leme declarada pelo corretor: ${rudderLabel} (não verificada de forma independente)`,
    submit: "Pesquisar",
    formInstructions:
      "Comece pela estrutura que lhe interessa (forma do casco, posição do cockpit, salão de convés) e, opcionalmente, indique o calado máximo admissível, em metros, e/ou escolha uma configuração de quilha. A HullQ apenas apresenta barcos cujo corretor confirmou cumprirem estes requisitos.",
    invalidTitle: "Esta ligação de pesquisa não é válida",
    invalidFallback:
      "Indique o calado máximo como um número decimal simples em metros (por exemplo 1.6) e/ou escolha uma configuração de quilha suportada.",
    startOver: "Iniciar nova pesquisa",
    serviceUnavailableTitle: "A pesquisa está temporariamente indisponível",
    serviceUnavailableMessage:
      "Não foi possível concluir esta pesquisa neste momento. Tente novamente dentro de instantes.",
    requirementSummary: (draftMax) => `A mostrar barcos com calado confirmado de ${draftMax} m ou menos.`,
    requirementSummaryKeelOnly: (keelLabel) =>
      `A mostrar barcos com configuração de quilha confirmada: ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `A mostrar barcos com calado confirmado de ${draftMax} m ou menos e configuração de quilha: ${keelLabel}.`,
    confirmedHeading: "Correspondências confirmadas",
    noConfirmedMatches:
      "Nenhum anúncio tem atualmente confirmação do corretor de que o calado cumpre este requisito.",
    noConfirmedMatchesGeneric:
      "Nenhum anúncio tem atualmente confirmação do corretor de que cumpre este requisito.",
    noConfirmedMatchesPartial:
      "Entre os anúncios verificados até agora, nenhum tem confirmação do corretor de que o calado cumpre este requisito. Este não é o resultado completo.",
    noConfirmedMatchesGenericPartial:
      "Entre os anúncios verificados até agora, nenhum tem confirmação do corretor de que cumpre este requisito. Este não é o resultado completo.",
    resolvedDraftText: (resolvedDraftM) =>
      `calado declarado pelo corretor: ${resolvedDraftM} m (não verificado de forma independente)`,
    resolvedKeelText: (keelLabel) =>
      `configuração de quilha declarada pelo corretor: ${keelLabel} (não verificada de forma independente)`,
    insufficientDataText: (count) =>
      `${count} anúncio(s) adicional(is) poderiam satisfazer este requisito mas não são apresentados como correspondência: o calado está em falta, é desconhecido, ou entra em conflito com a declaração atual de outra organização.`,
    insufficientDataTextGeneric: (count) =>
      `${count} anúncio(s) adicional(is) poderiam satisfazer este requisito mas não são apresentados como correspondência: a informação do corretor está em falta, é desconhecida, ou entra em conflito com a declaração atual de outra organização.`,
    partialResultsNote:
      "Esta pesquisa ainda não está concluída. Mais anúncios podem ainda ser verificados -- este não é o resultado completo.",
    showMoreResultsLabel: "Mostrar mais resultados",
    viewListing: "Ver anúncio",
    freshnessConfirmedLabel: "Confirmado atual",
    freshnessDueLabel: "Reconfirmação pendente",
    freshnessDueNote:
      "O corretor não reconfirmou este anúncio recentemente; será ocultado em breve caso não seja reconfirmado.",
    publisherClaimHeading: (count) =>
      `Resultados adicionais com base na declaração do corretor (${count})`,
    publisherClaimDisclaimer:
      "Estes anúncios não estão associados a um projeto conhecido. São apresentados porque a declaração atual do corretor cumpre este requisito -- não porque a HullQ verificou o projeto de forma independente.",
    noPublisherClaimMatches:
      "Atualmente, nenhum anúncio adicional declarado pelo corretor cumpre este requisito.",
    noDesignConfirmedMatchesButPublisherClaimsExist: (publisherClaimCount) =>
      `Nenhuma correspondência confirmada pelo projeto. ${publisherClaimCount} correspondência(s) adicional(is) com base na declaração do corretor são mostradas abaixo.`,
    noDesignConfirmedMatchesButPublisherClaimsExistPartial: (publisherClaimCount) =>
      `Entre os anúncios verificados até agora, nenhuma correspondência confirmada pelo projeto. ${publisherClaimCount} correspondência(s) adicional(is) com base na declaração do corretor são mostradas abaixo. Este não é o resultado completo.`,
    sensitivityFormNote:
      "Veja quantas correspondências confirmadas mudam se experimentar um valor diferente para um requisito. Isto não altera a sua pesquisa atual.",
    sensitivityUnavailableWithNewCriteria:
      "A sensibilidade do requisito não está disponível enquanto um filtro de comprimento total, configuração de leme, forma do casco, posição do cockpit, salão de convés, boca máxima ou material do casco também estiver ativo.",
    sensitivityDraftSubmitLabel: "Ver o efeito de um calado máximo diferente",
    sensitivityKeelSubmitLabel: "Ver o efeito de uma configuração de quilha diferente",
    sensitivityAlternativeDraftLabel: "Calado máximo alternativo (metros)",
    sensitivityAlternativeKeelLabel: "Configuração de quilha alternativa",
    sensitivityPageTitle: "Sensibilidade do requisito",
    sensitivityCurrentHeading: "Requisito atual",
    sensitivityAlternativeHeading: "Requisito alternativo",
    sensitivityCurrentConfirmedLabel: (count) =>
      `Correspondências atualmente confirmadas pelo projeto: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Correspondências confirmadas pelo projeto com a alternativa: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) =>
      `${count} recém-confirmada(s) pelo projeto com a alternativa`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} deixou/deixaram de estar confirmada(s) pelo projeto com a alternativa`,
    sensitivityCurrentPublisherClaimLabel: (count) =>
      `Correspondências atuais segundo a declaração do corretor (não verificadas pelo projeto): ${count}`,
    sensitivityAlternativePublisherClaimLabel: (count) =>
      `Correspondências segundo a declaração do corretor (não verificadas pelo projeto) com a alternativa: ${count}`,
    sensitivityNewlyPublisherClaimLabel: (count) =>
      `${count} recém-declarada(s) pelo corretor com a alternativa`,
    sensitivityNoLongerPublisherClaimLabel: (count) =>
      `${count} deixou/deixaram de estar declarada(s) pelo corretor com a alternativa`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} anúncio(s) adicional(is) têm evidência insuficiente ao abrigo do requisito atual`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} anúncio(s) adicional(is) têm evidência insuficiente ao abrigo do requisito alternativo`,
    sensitivityViewAlternativeSearch: "Ver esta pesquisa",
    sensitivityInvalidTitle: "Este pedido de sensibilidade não é válido",
    sensitivityInvalidFallback:
      "Escolha um requisito atualmente ativo e indique um valor de substituição para o mesmo.",
    sensitivityServiceUnavailableTitle: "A sensibilidade está temporariamente indisponível",
    sensitivityServiceUnavailableMessage:
      "Não foi possível concluir esta comparação neste momento. Tente novamente dentro de instantes.",
    sensitivityMethodNotAllowedTitle: "Comece a partir de uma pesquisa",
    sensitivityMethodNotAllowedMessage:
      "Esta página só mostra um resultado depois de submeter uma alteração de requisito a partir da página de pesquisa.",
  },
  es: {
    title: "Búsqueda: calado máximo",
    structureControlsHeading: "¿Qué tipo de estructura de velero le interesa?",
    hullConfigurationLabel: "Forma del casco",
    hullConfigurationAnyOption: "Cualquier forma de casco",
    hullConfigurationLabels: {
      MONOHULL: "Monocasco",
      CATAMARAN: "Catamarán",
      TRIMARAN: "Trimarán",
    },
    cockpitPositionLabel: "Posición de la bañera",
    cockpitPositionAnyOption: "Cualquier posición de bañera",
    cockpitPositionLabels: {
      AFT: "Bañera de popa",
      CENTER: "Bañera central",
      FORWARD: "Bañera de proa",
      MULTIPLE: "Bañeras múltiples",
    },
    deckSaloonLabel: "Salón de cubierta / timonera",
    deckSaloonAnyOption: "Cualquier salón de cubierta / timonera",
    deckSaloonLabels: {
      DECK_SALOON: "Salón de cubierta",
      PILOTHOUSE: "Timonera",
    },
    requirementPhraseHull: (hullLabel) => `un casco: ${hullLabel}`,
    requirementPhraseCockpit: (cockpitLabel) => `una ${cockpitLabel}`,
    requirementPhraseDeckSaloon: (deckSaloonLabel) => `un ${deckSaloonLabel}`,
    resolvedHullText: (hullLabel) =>
      `forma de casco declarada por el bróker: ${hullLabel} (no verificada de forma independiente)`,
    resolvedCockpitText: (cockpitLabel) =>
      `posición de bañera declarada por el bróker: ${cockpitLabel} (no verificada de forma independiente)`,
    resolvedDeckSaloonText: (deckSaloonLabel) =>
      `salón de cubierta/timonera declarado por el bróker: ${deckSaloonLabel} (no verificado de forma independiente)`,
    designEvidenceHeading: "Especificación del diseño/configuración (independiente de la declaración del bróker)",
    designEvidenceConfigurationLabel: "Configuración",
    truthTrueLabel: "confirmado",
    truthFalseLabel: "no cumplido",
    truthUnknownLabel: "desconocido",
    draftMaxLabel: "Calado máximo (metros)",
    draftMaxPlaceholder: "1.6",
    keelConfigurationLabel: "Configuración de quilla",
    keelConfigurationAnyOption: "Cualquier configuración de quilla",
    keelConfigurationLabels: {
      FIN: "Quilla de aleta",
      FIN_WITH_BULB: "Quilla de aleta con bulbo",
      WING: "Quilla de alas",
      CENTERBOARD: "Orza abatible",
      LIFTING_KEEL: "Quilla retráctil",
      TWIN_KEEL: "Quilla doble",
    },
    loaMinLabel: "Eslora total mínima (metros)",
    loaMaxLabel: "Eslora total máxima (metros)",
    loaMinPlaceholder: "10",
    loaMaxPlaceholder: "15",
    rudderConfigurationLabel: "Configuración de timón",
    rudderConfigurationAnyOption: "Cualquier configuración de timón",
    rudderConfigurationLabels: {
      SKEG_HUNG: "Timón en skeg",
      TRANSOM_HUNG: "Timón en el espejo de popa",
      SPADE: "Timón suspendido (spade)",
      TWIN: "Timones gemelos",
    },
    beamMinLabel: "Manga mínima (metros)",
    beamMaxLabel: "Manga máxima (metros)",
    beamMinPlaceholder: "3.2",
    beamMaxPlaceholder: "4.4",
    hullMaterialLabel: "Material de construcción del casco",
    hullMaterialAnyOption: "Cualquier material de casco",
    hullMaterialLabels: {
      GRP_FIBERGLASS: "PRFV / fibra de vidrio",
      STEEL: "Acero",
      ALUMINUM: "Aluminio",
      WOOD: "Madera",
    },
    requirementPhraseDraftMax: (draftMax) => `un calado de ${draftMax} m o menos`,
    requirementPhraseKeel: (keelLabel) => `una configuración de quilla: ${keelLabel}`,
    requirementPhraseLoaMin: (loaMin) => `una eslora total de al menos ${loaMin} m`,
    requirementPhraseLoaMax: (loaMax) => `una eslora total de ${loaMax} m o menos`,
    requirementPhraseLoaRange: (loaMin, loaMax) =>
      `una eslora total entre ${loaMin} m y ${loaMax} m`,
    requirementPhraseRudder: (rudderLabel) => `una configuración de timón: ${rudderLabel}`,
    requirementPhraseBeamMin: (beamMin) => `una manga de al menos ${beamMin} m`,
    requirementPhraseBeamMax: (beamMax) => `una manga de ${beamMax} m o menos`,
    requirementPhraseBeamRange: (beamMin, beamMax) => `una manga entre ${beamMin} m y ${beamMax} m`,
    requirementPhraseHullMaterial: (hullMaterialLabel) => `un casco de ${hullMaterialLabel}`,
    requirementSummaryListConjunction: "y",
    requirementSummaryGeneric: (phrases) => `Mostrando barcos confirmados con ${phrases}.`,
    resolvedLoaText: (resolvedLoaM) =>
      `eslora total declarada por el bróker: ${resolvedLoaM} m (no verificada de forma independiente)`,
    resolvedBeamText: (resolvedBeamM) =>
      `manga declarada por el bróker: ${resolvedBeamM} m (no verificada de forma independiente)`,
    resolvedHullMaterialText: (hullMaterialLabel) =>
      `material de casco declarado por el bróker: ${hullMaterialLabel} (no verificado de forma independiente)`,
    resolvedRudderText: (rudderLabel) =>
      `configuración de timón declarada por el bróker: ${rudderLabel} (no verificada de forma independiente)`,
    submit: "Buscar",
    formInstructions:
      "Empiece por la estructura que le interese (forma de casco, posición de bañera, salón de cubierta) y, opcionalmente, indique el calado máximo admisible, en metros, y/o elija una configuración de quilla. HullQ solo muestra barcos cuyo bróker ha confirmado que cumplen estos requisitos.",
    invalidTitle: "Este enlace de búsqueda no es válido",
    invalidFallback:
      "Indique el calado máximo como un número decimal simple en metros (por ejemplo 1.6) y/o elija una configuración de quilla admitida.",
    startOver: "Iniciar una nueva búsqueda",
    serviceUnavailableTitle: "La búsqueda no está disponible temporalmente",
    serviceUnavailableMessage:
      "No hemos podido completar esta búsqueda en este momento. Inténtelo de nuevo en unos instantes.",
    requirementSummary: (draftMax) => `Mostrando barcos con calado confirmado de ${draftMax} m o menos.`,
    requirementSummaryKeelOnly: (keelLabel) =>
      `Mostrando barcos con configuración de quilla confirmada: ${keelLabel}.`,
    requirementSummaryMixed: (draftMax, keelLabel) =>
      `Mostrando barcos con calado confirmado de ${draftMax} m o menos y configuración de quilla: ${keelLabel}.`,
    confirmedHeading: "Coincidencias confirmadas",
    noConfirmedMatches:
      "Ningún anuncio cuenta actualmente con confirmación del bróker de que su calado cumple este requisito.",
    noConfirmedMatchesGeneric:
      "Ningún anuncio cuenta actualmente con confirmación del bróker de que cumple este requisito.",
    noConfirmedMatchesPartial:
      "Entre los anuncios revisados hasta ahora, ninguno cuenta con confirmación del bróker de que su calado cumple este requisito. Este no es el resultado completo.",
    noConfirmedMatchesGenericPartial:
      "Entre los anuncios revisados hasta ahora, ninguno cuenta con confirmación del bróker de que cumple este requisito. Este no es el resultado completo.",
    resolvedDraftText: (resolvedDraftM) =>
      `calado declarado por el bróker: ${resolvedDraftM} m (no verificado de forma independiente)`,
    resolvedKeelText: (keelLabel) =>
      `configuración de quilla declarada por el bróker: ${keelLabel} (no verificada de forma independiente)`,
    insufficientDataText: (count) =>
      `${count} anuncio(s) adicional(es) podrían cumplir este requisito pero no se muestran como coincidencia: falta el calado, es desconocido, o entra en conflicto con la declaración actual de otra organización.`,
    insufficientDataTextGeneric: (count) =>
      `${count} anuncio(s) adicional(es) podrían cumplir este requisito pero no se muestran como coincidencia: falta información del bróker, es desconocida, o entra en conflicto con la declaración actual de otra organización.`,
    partialResultsNote:
      "Esta búsqueda aún no se ha completado. Es posible que se sigan comprobando más anuncios -- este no es el resultado completo.",
    showMoreResultsLabel: "Mostrar más resultados",
    viewListing: "Ver anuncio",
    freshnessConfirmedLabel: "Confirmado vigente",
    freshnessDueLabel: "Reconfirmación pendiente",
    freshnessDueNote:
      "El bróker no ha reconfirmado este anuncio recientemente; se ocultará pronto si no se reconfirma.",
    publisherClaimHeading: (count) =>
      `Resultados adicionales según la declaración del corredor (${count})`,
    publisherClaimDisclaimer:
      "Estos anuncios no están vinculados a un diseño conocido. Se muestran porque la declaración actual del corredor cumple este requisito -- no porque HullQ haya verificado el diseño de forma independiente.",
    noPublisherClaimMatches:
      "Actualmente ningún anuncio adicional declarado por el corredor cumple este requisito.",
    noDesignConfirmedMatchesButPublisherClaimsExist: (publisherClaimCount) =>
      `Ninguna coincidencia confirmada por el diseño. Se muestran ${publisherClaimCount} coincidencia(s) adicional(es) según la declaración del corredor más abajo.`,
    noDesignConfirmedMatchesButPublisherClaimsExistPartial: (publisherClaimCount) =>
      `Entre los anuncios revisados hasta ahora, ninguna coincidencia confirmada por el diseño. Se muestran ${publisherClaimCount} coincidencia(s) adicional(es) según la declaración del corredor más abajo. Este no es el resultado completo.`,
    sensitivityFormNote:
      "Vea cuántas coincidencias confirmadas cambian si prueba un valor diferente para un requisito. Esto no modifica su búsqueda actual.",
    sensitivityUnavailableWithNewCriteria:
      "La sensibilidad del requisito no está disponible mientras también esté activo un filtro de eslora total, configuración de timón, forma de casco, posición de bañera, salón de cubierta, manga máxima o material del casco.",
    sensitivityDraftSubmitLabel: "Ver el efecto de un calado máximo diferente",
    sensitivityKeelSubmitLabel: "Ver el efecto de una configuración de quilla diferente",
    sensitivityAlternativeDraftLabel: "Calado máximo alternativo (metros)",
    sensitivityAlternativeKeelLabel: "Configuración de quilla alternativa",
    sensitivityPageTitle: "Sensibilidad del requisito",
    sensitivityCurrentHeading: "Requisito actual",
    sensitivityAlternativeHeading: "Requisito alternativo",
    sensitivityCurrentConfirmedLabel: (count) =>
      `Coincidencias actualmente confirmadas por el diseño: ${count}`,
    sensitivityAlternativeConfirmedLabel: (count) =>
      `Coincidencias confirmadas por el diseño con la alternativa: ${count}`,
    sensitivityNewlyConfirmedLabel: (count) =>
      `${count} recién confirmada(s) por el diseño con la alternativa`,
    sensitivityNoLongerConfirmedLabel: (count) =>
      `${count} ya no confirmada(s) por el diseño con la alternativa`,
    sensitivityCurrentPublisherClaimLabel: (count) =>
      `Coincidencias actuales según la declaración del corredor (no verificadas por el diseño): ${count}`,
    sensitivityAlternativePublisherClaimLabel: (count) =>
      `Coincidencias según la declaración del corredor (no verificadas por el diseño) con la alternativa: ${count}`,
    sensitivityNewlyPublisherClaimLabel: (count) =>
      `${count} recién declarada(s) por el corredor con la alternativa`,
    sensitivityNoLongerPublisherClaimLabel: (count) =>
      `${count} ya no declarada(s) por el corredor con la alternativa`,
    sensitivityCurrentInsufficientLabel: (count) =>
      `${count} anuncio(s) adicional(es) tienen evidencia insuficiente según el requisito actual`,
    sensitivityAlternativeInsufficientLabel: (count) =>
      `${count} anuncio(s) adicional(es) tienen evidencia insuficiente según el requisito alternativo`,
    sensitivityViewAlternativeSearch: "Ver esta búsqueda",
    sensitivityInvalidTitle: "Esta solicitud de sensibilidad no es válida",
    sensitivityInvalidFallback:
      "Elija un requisito actualmente activo e indique un valor de sustitución para él.",
    sensitivityServiceUnavailableTitle: "La sensibilidad no está disponible temporalmente",
    sensitivityServiceUnavailableMessage:
      "No hemos podido completar esta comparación en este momento. Inténtelo de nuevo en unos instantes.",
    sensitivityMethodNotAllowedTitle: "Comience desde una búsqueda",
    sensitivityMethodNotAllowedMessage:
      "Esta página solo muestra un resultado después de enviar un cambio de requisito desde la página de búsqueda.",
  },
};
