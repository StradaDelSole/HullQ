// SLICE-0093: localized presentation text for the bounded Power-only
// `power_drive_configuration` Search surface (item K -- technical parameter
// names/values and Search semantics stay language-neutral; only this prose
// is translated). German labels are the normative ones from
// `specs/POWER_DRIVE_CONFIGURATION_SEARCH_CONTRACT.v0.1.md`'s own table.
//
// SLICE-0094 adds `power_engine_count` (contract: "Current count:" ... the
// second Power criterion). Mirrors `searchText.ts`'s own established
// multi-criterion summary pattern: `requirementSummary` stays byte-for-byte
// unchanged and is used only for the drive-only shape (non-regression);
// a request involving `power_engine_count` (alone or combined) builds its
// phrase(s) via `requirementPhraseDrive`/`requirementPhraseCount` and joins
// them with `requirementSummaryListConjunction` through
// `requirementSummaryGeneric` -- never a third, independently-worded
// summary function per combination.

import type { SupportedLocale } from "./searchText";

export interface PowerSearchText {
  title: string;
  formInstructions: string;
  powerDriveLabel: string;
  powerDriveAnyOption: string;
  powerDriveLabels: {
    SHAFT: string;
    STERNDRIVE: string;
    POD: string;
    WATERJET: string;
    OUTBOARD: string;
  };
  /** SLICE-0094 candidate facet #2. */
  powerEngineCountLabel: string;
  powerEngineCountAnyOption: string;
  submit: string;
  invalidTitle: string;
  invalidFallback: string;
  startOver: string;
  serviceUnavailableTitle: string;
  serviceUnavailableMessage: string;
  /** Drive-only active requirement (SLICE-0093, unchanged). */
  requirementSummary: (driveLabel: string) => string;
  /** SLICE-0094: one criterion's own phrase, joined generically below. */
  requirementPhraseDrive: (driveLabel: string) => string;
  requirementPhraseCount: (count: string) => string;
  requirementSummaryListConjunction: string;
  requirementSummaryGeneric: (phrases: string) => string;
  designLinkedHeading: (count: number) => string;
  noDesignLinkedMatches: string;
  noDesignLinkedMatchesButPublisherClaimsExist: (count: number) => string;
  /**
   * SLICE-0096 independent review Finding D -- see `SearchText.
   * noConfirmedMatchesPartial` in `searchText.ts` for the identical
   * discipline: never claim a final/exhaustive absence while this page is
   * PARTIAL.
   */
  noDesignLinkedMatchesPartial: string;
  noDesignLinkedMatchesButPublisherClaimsExistPartial: (count: number) => string;
  insufficientDataText: (count: number) => string;
  /** SLICE-0096 -- see `SearchText.partialResultsNote` in `searchText.ts`. */
  partialResultsNote: string;
  showMoreResultsLabel: string;
  publisherClaimHeading: (count: number) => string;
  publisherClaimDisclaimer: string;
  viewListing: string;
  freshnessConfirmedLabel: string;
  freshnessDueLabel: string;
  freshnessDueNote: string;
  designEvidenceHeading: string;
  designEvidenceConfigurationLabel: string;
  truthTrueLabel: string;
  truthFalseLabel: string;
  truthUnknownLabel: string;
  /**
   * SLICE-0094 independent-review amendment Finding D: per-leaf criterion
   * evidence -- requested value, observed truth, reason/explanation and an
   * explicit source distinction (design-qualified vs. publisher-asserted),
   * rendered for both design-linked and publisher-claim-only matches.
   */
  criterionEvidenceHeading: string;
  criterionRequestedLabel: (fieldLabel: string, requestedValue: string) => string;
  criterionObservedLabel: (truthLabel: string) => string;
  sourcePublisherClaimLabel: string;
  sourceDesignQualifiedLabel: string;
  /**
   * Round 2 Finding D2: the per-leaf `evidence.reason` the backend's
   * `hullq.search.types.ReasonCode` can carry (never `null` for an
   * `UNKNOWN`/fail-closed truth) was previously parsed only from free-text
   * `explanation` prose, never rendered as its own labeled, localized
   * reason. `CONFIGURATION_AMBIGUOUS` is design-evaluation-level only
   * (never a per-criterion leaf reason) and is deliberately absent here.
   */
  criterionReasonLabel: (reasonLabel: string) => string;
  reasonLabels: {
    VALUE_MISSING: string;
    UNRESOLVED_CONFLICT: string;
    PROVISIONAL_VALUE: string;
    APPLICABILITY_UNKNOWN: string;
    NOT_APPLICABLE: string;
  };
}

export const powerSearchText: Record<SupportedLocale, PowerSearchText> = {
  en: {
    title: "Power drive configuration search (internal)",
    formInstructions: "Choose one current drive arrangement.",
    powerDriveLabel: "Current drive arrangement",
    powerDriveAnyOption: "Choose a drive arrangement",
    powerDriveLabels: {
      SHAFT: "Shaft drive",
      STERNDRIVE: "Sterndrive",
      POD: "Pod drive",
      WATERJET: "Waterjet",
      OUTBOARD: "Outboard",
    },
    powerEngineCountLabel: "Number of installed engines",
    powerEngineCountAnyOption: "Choose a number of engines",
    submit: "Search",
    invalidTitle: "Invalid search",
    invalidFallback: "This search link isn't valid.",
    startOver: "Start over",
    serviceUnavailableTitle: "Search temporarily unavailable",
    serviceUnavailableMessage: "Please try again shortly.",
    requirementSummary: (driveLabel) => `Current drive arrangement: ${driveLabel}`,
    requirementPhraseDrive: (driveLabel) => `a current drive arrangement of ${driveLabel}`,
    requirementPhraseCount: (count) => `${count} installed engine(s)`,
    requirementSummaryListConjunction: "and",
    requirementSummaryGeneric: (phrases) => `Showing boats confirmed to have ${phrases}.`,
    designLinkedHeading: (count) => `Design-confirmed matches (${count})`,
    noDesignLinkedMatches: "No design-confirmed matches for this drive arrangement.",
    noDesignLinkedMatchesButPublisherClaimsExist: (count) =>
      `No design-confirmed matches, but ${count} publisher-claimed listing(s) below.`,
    noDesignLinkedMatchesPartial:
      "No design-confirmed matches among those checked so far for this drive arrangement. This is not the full result.",
    noDesignLinkedMatchesButPublisherClaimsExistPartial: (count) =>
      `No design-confirmed matches among those checked so far, but ${count} publisher-claimed listing(s) below. This is not the full result.`,
    insufficientDataText: (count) =>
      `${count} listing(s) have insufficient data to confirm or exclude this drive arrangement.`,
    partialResultsNote:
      "This search is not yet complete. More listings may still be checked -- this is not the full result.",
    showMoreResultsLabel: "Show more results",
    publisherClaimHeading: (count) => `Publisher-claimed matches (${count})`,
    publisherClaimDisclaimer:
      "These listings are shown on the publishing broker's own current statement, not independently verified.",
    viewListing: "View listing",
    freshnessConfirmedLabel: "confirmed current",
    freshnessDueLabel: "confirmation due",
    freshnessDueNote: "This listing's current data is due for reconfirmation.",
    designEvidenceHeading: "Design/configuration evidence",
    designEvidenceConfigurationLabel: "Configuration",
    truthTrueLabel: "TRUE",
    truthFalseLabel: "FALSE",
    truthUnknownLabel: "UNKNOWN",
    criterionEvidenceHeading: "Criterion evidence",
    criterionRequestedLabel: (fieldLabel, requestedValue) =>
      `Requested — ${fieldLabel}: ${requestedValue}`,
    criterionObservedLabel: (truthLabel) => `Observed: ${truthLabel}`,
    sourcePublisherClaimLabel: "publisher-asserted, not independently verified",
    sourceDesignQualifiedLabel: "design-qualified (BoatDesign/FieldResolution)",
    criterionReasonLabel: (reasonLabel) => `Reason: ${reasonLabel}`,
    reasonLabels: {
      VALUE_MISSING: "value missing",
      UNRESOLVED_CONFLICT: "unresolved conflicting evidence",
      PROVISIONAL_VALUE: "provisional (unverified) value",
      APPLICABILITY_UNKNOWN: "applicability unknown",
      NOT_APPLICABLE: "not applicable (confirmed exclusion)",
    },
  },
  de: {
    title: "Antriebsart-Suche (intern)",
    formInstructions: "Wählen Sie eine aktuelle Antriebsart.",
    powerDriveLabel: "Aktuelle Antriebsart",
    powerDriveAnyOption: "Antriebsart wählen",
    powerDriveLabels: {
      SHAFT: "Wellenantrieb",
      STERNDRIVE: "Z-Antrieb / Sterndrive",
      POD: "Pod-Antrieb",
      WATERJET: "Wasserstrahlantrieb",
      OUTBOARD: "Außenborder",
    },
    powerEngineCountLabel: "Anzahl der installierten Motoren",
    powerEngineCountAnyOption: "Anzahl der Motoren wählen",
    submit: "Suchen",
    invalidTitle: "Ungültige Suche",
    invalidFallback: "Dieser Suchlink ist ungültig.",
    startOver: "Neu beginnen",
    serviceUnavailableTitle: "Suche vorübergehend nicht verfügbar",
    serviceUnavailableMessage: "Bitte versuchen Sie es in Kürze erneut.",
    requirementSummary: (driveLabel) => `Aktuelle Antriebsart: ${driveLabel}`,
    requirementPhraseDrive: (driveLabel) => `aktuelle Antriebsart: ${driveLabel}`,
    requirementPhraseCount: (count) => `${count} installierte Motor(en)`,
    requirementSummaryListConjunction: "und",
    requirementSummaryGeneric: (phrases) => `Boote mit ${phrases} (bestätigt).`,
    designLinkedHeading: (count) => `Design-bestätigte Treffer (${count})`,
    noDesignLinkedMatches: "Keine design-bestätigten Treffer für diese Antriebsart.",
    noDesignLinkedMatchesButPublisherClaimsExist: (count) =>
      `Keine design-bestätigten Treffer, aber ${count} Angebot(e) laut Anbieterangabe unten.`,
    noDesignLinkedMatchesPartial:
      "Unter den bisher geprüften Angeboten keine design-bestätigten Treffer für diese Antriebsart. Dies ist nicht das vollständige Ergebnis.",
    noDesignLinkedMatchesButPublisherClaimsExistPartial: (count) =>
      `Unter den bisher geprüften Angeboten keine design-bestätigten Treffer, aber ${count} Angebot(e) laut Anbieterangabe unten. Dies ist nicht das vollständige Ergebnis.`,
    insufficientDataText: (count) =>
      `${count} Angebot(e) haben keine ausreichenden Daten, um diese Antriebsart zu bestätigen oder auszuschließen.`,
    partialResultsNote:
      "Diese Suche ist noch nicht abgeschlossen. Es können noch weitere Angebote geprüft werden -- dies ist nicht das vollständige Ergebnis.",
    showMoreResultsLabel: "Weitere Ergebnisse anzeigen",
    publisherClaimHeading: (count) => `Treffer laut Anbieterangabe (${count})`,
    publisherClaimDisclaimer:
      "Diese Angebote beruhen auf der aktuellen Angabe des anbietenden Maklers, nicht auf unabhängiger Prüfung.",
    viewListing: "Angebot ansehen",
    freshnessConfirmedLabel: "aktuell bestätigt",
    freshnessDueLabel: "Bestätigung fällig",
    freshnessDueNote: "Die aktuellen Daten dieses Angebots müssen erneut bestätigt werden.",
    designEvidenceHeading: "Design-/Konfigurationsnachweis",
    designEvidenceConfigurationLabel: "Konfiguration",
    truthTrueLabel: "WAHR",
    truthFalseLabel: "FALSCH",
    truthUnknownLabel: "UNBEKANNT",
    criterionEvidenceHeading: "Kriteriennachweis",
    criterionRequestedLabel: (fieldLabel, requestedValue) =>
      `Angefordert — ${fieldLabel}: ${requestedValue}`,
    criterionObservedLabel: (truthLabel) => `Beobachtet: ${truthLabel}`,
    sourcePublisherClaimLabel: "Angabe des Anbieters, nicht unabhängig geprüft",
    sourceDesignQualifiedLabel: "design-qualifiziert (BoatDesign/FieldResolution)",
    criterionReasonLabel: (reasonLabel) => `Grund: ${reasonLabel}`,
    reasonLabels: {
      VALUE_MISSING: "Wert fehlt",
      UNRESOLVED_CONFLICT: "ungelöster Widerspruch in den Nachweisen",
      PROVISIONAL_VALUE: "vorläufiger (ungeprüfter) Wert",
      APPLICABILITY_UNKNOWN: "Anwendbarkeit unbekannt",
      NOT_APPLICABLE: "nicht anwendbar (bestätigter Ausschluss)",
    },
  },
  fr: {
    title: "Recherche de configuration de propulsion (interne)",
    formInstructions: "Choisissez une configuration de propulsion actuelle.",
    powerDriveLabel: "Configuration de propulsion actuelle",
    powerDriveAnyOption: "Choisir une configuration",
    powerDriveLabels: {
      SHAFT: "Ligne d'arbre",
      STERNDRIVE: "Z-drive",
      POD: "Pod de propulsion",
      WATERJET: "Hydrojet",
      OUTBOARD: "Hors-bord",
    },
    powerEngineCountLabel: "Nombre de moteurs installés",
    powerEngineCountAnyOption: "Choisir un nombre de moteurs",
    submit: "Rechercher",
    invalidTitle: "Recherche invalide",
    invalidFallback: "Ce lien de recherche n'est pas valide.",
    startOver: "Recommencer",
    serviceUnavailableTitle: "Recherche temporairement indisponible",
    serviceUnavailableMessage: "Veuillez réessayer sous peu.",
    requirementSummary: (driveLabel) => `Configuration de propulsion actuelle : ${driveLabel}`,
    requirementPhraseDrive: (driveLabel) => `une configuration de propulsion actuelle de ${driveLabel}`,
    requirementPhraseCount: (count) => `${count} moteur(s) installé(s)`,
    requirementSummaryListConjunction: "et",
    requirementSummaryGeneric: (phrases) => `Bateaux confirmés avec ${phrases}.`,
    designLinkedHeading: (count) => `Résultats confirmés par le design (${count})`,
    noDesignLinkedMatches: "Aucun résultat confirmé par le design pour cette configuration.",
    noDesignLinkedMatchesButPublisherClaimsExist: (count) =>
      `Aucun résultat confirmé par le design, mais ${count} annonce(s) ci-dessous selon le vendeur.`,
    noDesignLinkedMatchesPartial:
      "Parmi les annonces examinées jusqu'à présent, aucun résultat confirmé par le design pour cette configuration. Ceci n'est pas le résultat complet.",
    noDesignLinkedMatchesButPublisherClaimsExistPartial: (count) =>
      `Parmi les annonces examinées jusqu'à présent, aucun résultat confirmé par le design, mais ${count} annonce(s) ci-dessous selon le vendeur. Ceci n'est pas le résultat complet.`,
    insufficientDataText: (count) =>
      `${count} annonce(s) ne disposent pas de données suffisantes pour confirmer ou exclure cette configuration.`,
    partialResultsNote:
      "Cette recherche n'est pas encore terminée. D'autres annonces peuvent encore être vérifiées -- ceci n'est pas le résultat complet.",
    showMoreResultsLabel: "Afficher plus de résultats",
    publisherClaimHeading: (count) => `Résultats selon le vendeur (${count})`,
    publisherClaimDisclaimer:
      "Ces annonces reposent sur la déclaration actuelle du courtier vendeur, non vérifiée indépendamment.",
    viewListing: "Voir l'annonce",
    freshnessConfirmedLabel: "confirmé à jour",
    freshnessDueLabel: "confirmation requise",
    freshnessDueNote: "Les données actuelles de cette annonce doivent être reconfirmées.",
    designEvidenceHeading: "Preuve de design/configuration",
    designEvidenceConfigurationLabel: "Configuration",
    truthTrueLabel: "VRAI",
    truthFalseLabel: "FAUX",
    truthUnknownLabel: "INCONNU",
    criterionEvidenceHeading: "Preuve par critère",
    criterionRequestedLabel: (fieldLabel, requestedValue) =>
      `Demandé — ${fieldLabel} : ${requestedValue}`,
    criterionObservedLabel: (truthLabel) => `Observé : ${truthLabel}`,
    sourcePublisherClaimLabel: "déclaration du vendeur, non vérifiée de manière indépendante",
    sourceDesignQualifiedLabel: "qualifié par le design (BoatDesign/FieldResolution)",
    criterionReasonLabel: (reasonLabel) => `Raison : ${reasonLabel}`,
    reasonLabels: {
      VALUE_MISSING: "valeur manquante",
      UNRESOLVED_CONFLICT: "conflit de preuves non résolu",
      PROVISIONAL_VALUE: "valeur provisoire (non vérifiée)",
      APPLICABILITY_UNKNOWN: "applicabilité inconnue",
      NOT_APPLICABLE: "non applicable (exclusion confirmée)",
    },
  },
  pt: {
    title: "Pesquisa de configuração de propulsão (interna)",
    formInstructions: "Escolha uma configuração de propulsão atual.",
    powerDriveLabel: "Configuração de propulsão atual",
    powerDriveAnyOption: "Escolher uma configuração",
    powerDriveLabels: {
      SHAFT: "Veio",
      STERNDRIVE: "Sterndrive",
      POD: "Pod",
      WATERJET: "Hidrojato",
      OUTBOARD: "Motor de popa",
    },
    powerEngineCountLabel: "Número de motores instalados",
    powerEngineCountAnyOption: "Escolher um número de motores",
    submit: "Pesquisar",
    invalidTitle: "Pesquisa inválida",
    invalidFallback: "Esta ligação de pesquisa não é válida.",
    startOver: "Recomeçar",
    serviceUnavailableTitle: "Pesquisa temporariamente indisponível",
    serviceUnavailableMessage: "Tente novamente em breve.",
    requirementSummary: (driveLabel) => `Configuração de propulsão atual: ${driveLabel}`,
    requirementPhraseDrive: (driveLabel) => `configuração de propulsão atual: ${driveLabel}`,
    requirementPhraseCount: (count) => `${count} motor(es) instalado(s)`,
    requirementSummaryListConjunction: "e",
    requirementSummaryGeneric: (phrases) => `A mostrar barcos confirmados com ${phrases}.`,
    designLinkedHeading: (count) => `Resultados confirmados pelo design (${count})`,
    noDesignLinkedMatches: "Sem resultados confirmados pelo design para esta configuração.",
    noDesignLinkedMatchesButPublisherClaimsExist: (count) =>
      `Sem resultados confirmados pelo design, mas ${count} anúncio(s) abaixo segundo o vendedor.`,
    noDesignLinkedMatchesPartial:
      "Entre os anúncios verificados até agora, nenhum resultado confirmado pelo design para esta configuração. Este não é o resultado completo.",
    noDesignLinkedMatchesButPublisherClaimsExistPartial: (count) =>
      `Entre os anúncios verificados até agora, nenhum resultado confirmado pelo design, mas ${count} anúncio(s) abaixo segundo o vendedor. Este não é o resultado completo.`,
    insufficientDataText: (count) =>
      `${count} anúncio(s) não têm dados suficientes para confirmar ou excluir esta configuração.`,
    partialResultsNote:
      "Esta pesquisa ainda não está concluída. Mais anúncios podem ainda ser verificados -- este não é o resultado completo.",
    showMoreResultsLabel: "Mostrar mais resultados",
    publisherClaimHeading: (count) => `Resultados segundo o vendedor (${count})`,
    publisherClaimDisclaimer:
      "Estes anúncios baseiam-se na declaração atual do corretor anunciante, não verificada de forma independente.",
    viewListing: "Ver anúncio",
    freshnessConfirmedLabel: "confirmado atual",
    freshnessDueLabel: "confirmação pendente",
    freshnessDueNote: "Os dados atuais deste anúncio precisam de ser reconfirmados.",
    designEvidenceHeading: "Evidência de design/configuração",
    designEvidenceConfigurationLabel: "Configuração",
    truthTrueLabel: "VERDADEIRO",
    truthFalseLabel: "FALSO",
    truthUnknownLabel: "DESCONHECIDO",
    criterionEvidenceHeading: "Evidência por critério",
    criterionRequestedLabel: (fieldLabel, requestedValue) =>
      `Solicitado — ${fieldLabel}: ${requestedValue}`,
    criterionObservedLabel: (truthLabel) => `Observado: ${truthLabel}`,
    sourcePublisherClaimLabel: "declaração do vendedor, não verificada de forma independente",
    sourceDesignQualifiedLabel: "qualificado pelo design (BoatDesign/FieldResolution)",
    criterionReasonLabel: (reasonLabel) => `Motivo: ${reasonLabel}`,
    reasonLabels: {
      VALUE_MISSING: "valor em falta",
      UNRESOLVED_CONFLICT: "conflito de evidências não resolvido",
      PROVISIONAL_VALUE: "valor provisório (não verificado)",
      APPLICABILITY_UNKNOWN: "aplicabilidade desconhecida",
      NOT_APPLICABLE: "não aplicável (exclusão confirmada)",
    },
  },
  es: {
    title: "Búsqueda de configuración de propulsión (interna)",
    formInstructions: "Elija una configuración de propulsión actual.",
    powerDriveLabel: "Configuración de propulsión actual",
    powerDriveAnyOption: "Elegir una configuración",
    powerDriveLabels: {
      SHAFT: "Eje",
      STERNDRIVE: "Sterndrive",
      POD: "Pod",
      WATERJET: "Hidrojet",
      OUTBOARD: "Fueraborda",
    },
    powerEngineCountLabel: "Número de motores instalados",
    powerEngineCountAnyOption: "Elegir un número de motores",
    submit: "Buscar",
    invalidTitle: "Búsqueda inválida",
    invalidFallback: "Este enlace de búsqueda no es válido.",
    startOver: "Empezar de nuevo",
    serviceUnavailableTitle: "Búsqueda temporalmente no disponible",
    serviceUnavailableMessage: "Inténtelo de nuevo en breve.",
    requirementSummary: (driveLabel) => `Configuración de propulsión actual: ${driveLabel}`,
    requirementPhraseDrive: (driveLabel) => `configuración de propulsión actual: ${driveLabel}`,
    requirementPhraseCount: (count) => `${count} motor(es) instalado(s)`,
    requirementSummaryListConjunction: "y",
    requirementSummaryGeneric: (phrases) => `Mostrando barcos confirmados con ${phrases}.`,
    designLinkedHeading: (count) => `Resultados confirmados por diseño (${count})`,
    noDesignLinkedMatches: "No hay resultados confirmados por diseño para esta configuración.",
    noDesignLinkedMatchesButPublisherClaimsExist: (count) =>
      `No hay resultados confirmados por diseño, pero ${count} anuncio(s) a continuación según el vendedor.`,
    noDesignLinkedMatchesPartial:
      "Entre los anuncios revisados hasta ahora, no hay resultados confirmados por diseño para esta configuración. Este no es el resultado completo.",
    noDesignLinkedMatchesButPublisherClaimsExistPartial: (count) =>
      `Entre los anuncios revisados hasta ahora, no hay resultados confirmados por diseño, pero ${count} anuncio(s) a continuación según el vendedor. Este no es el resultado completo.`,
    insufficientDataText: (count) =>
      `${count} anuncio(s) no tienen datos suficientes para confirmar o excluir esta configuración.`,
    partialResultsNote:
      "Esta búsqueda aún no se ha completado. Es posible que se sigan comprobando más anuncios -- este no es el resultado completo.",
    showMoreResultsLabel: "Mostrar más resultados",
    publisherClaimHeading: (count) => `Resultados según el vendedor (${count})`,
    publisherClaimDisclaimer:
      "Estos anuncios se basan en la declaración actual del corredor anunciante, no verificada de forma independiente.",
    viewListing: "Ver anuncio",
    freshnessConfirmedLabel: "confirmado actual",
    freshnessDueLabel: "confirmación pendiente",
    freshnessDueNote: "Los datos actuales de este anuncio deben reconfirmarse.",
    designEvidenceHeading: "Evidencia de diseño/configuración",
    designEvidenceConfigurationLabel: "Configuración",
    truthTrueLabel: "VERDADERO",
    truthFalseLabel: "FALSO",
    truthUnknownLabel: "DESCONOCIDO",
    criterionEvidenceHeading: "Evidencia por criterio",
    criterionRequestedLabel: (fieldLabel, requestedValue) =>
      `Solicitado — ${fieldLabel}: ${requestedValue}`,
    criterionObservedLabel: (truthLabel) => `Observado: ${truthLabel}`,
    sourcePublisherClaimLabel: "declaración del vendedor, no verificada de forma independiente",
    sourceDesignQualifiedLabel: "calificado por el diseño (BoatDesign/FieldResolution)",
    criterionReasonLabel: (reasonLabel) => `Motivo: ${reasonLabel}`,
    reasonLabels: {
      VALUE_MISSING: "valor faltante",
      UNRESOLVED_CONFLICT: "conflicto de evidencias sin resolver",
      PROVISIONAL_VALUE: "valor provisional (no verificado)",
      APPLICABILITY_UNKNOWN: "aplicabilidad desconocida",
      NOT_APPLICABLE: "no aplicable (exclusión confirmada)",
    },
  },
};
